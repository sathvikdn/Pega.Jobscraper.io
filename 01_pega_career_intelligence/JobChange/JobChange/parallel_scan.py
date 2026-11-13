"""Bounded streaming discovery and description checks with one checkpoint writer.

The coordinator alone mutates saved rows. Network workers share PublicClient,
including its per-host pacing and response cache, and never write the checkpoint.
"""
from __future__ import annotations

import copy
import threading
from collections import OrderedDict, deque
from concurrent.futures import CancelledError, FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from datetime import datetime

import campaign
from quality import canonical_url, employer_matches, normalized_name

DETAIL_FIELDS = (
    "job_detail_checked_at", "job_detail_diagnostic", "job_detail_status",
    "evidence_scope", "description_identity", "description_text", "description_source_url",
    "description_checked_at", "description_complete", "skills", "experience_evidence",
    "experience_min", "experience_max", "salary", "pay_bucket", "remote_eligibility",
    "fit", "fit_reasons", "required_certifications", "certification_evidence",
    "requirements_unknown", "track", "relevance", "summary", "evidence",
    "closing_at", "verification_status",
)
OUTCOMES = ("read", "unavailable", "identity_unconfirmed", "description_missing")


def _same_identity(left, right):
    return (
        normalized_name(left.get("title", "")) == normalized_name(right.get("title", ""))
        and employer_matches(left.get("company", ""), {"name": right.get("company", "")})
    )


def _copy_facts(saved, enriched):
    """Match identities; retain per-copy provenance, IDs, user fields and old salary."""
    if not _same_identity(saved, enriched):
        return False
    if enriched.get("job_detail_status") != "read":
        for key in ("job_detail_checked_at", "job_detail_diagnostic", "job_detail_status"):
            if key in enriched:
                saved[key] = copy.deepcopy(enriched[key])
        return True
    previous_salary = copy.deepcopy(saved.get("salary"))
    for key in DETAIL_FIELDS:
        if key in enriched:
            saved[key] = copy.deepcopy(enriched[key])
    if previous_salary and not saved.get("salary"):
        previous_salary.setdefault("source_url", saved.get("url"))
        previous_salary.setdefault("evidence_checked_at", saved.get("checked_at"))
        previous_salary["latest_presence"] = "not_rediscovered"
        saved["salary"] = previous_salary
        saved["pay_bucket"] = campaign.pay_bucket(previous_salary)
        saved["requirements_unknown"] = list(dict.fromkeys(saved.get("requirements_unknown", []) + [
            "Previous salary evidence retained for this saved copy; latest selected description did not publish an annual INR figure. Confirm the budget."
        ]))
    return True


def _complete_read(job, since=None):
    if not (job.get("job_detail_status") == "read" and job.get("description_complete")
            and job.get("description_text")
            and canonical_url(job.get("description_source_url", "")) == canonical_url(job.get("url", ""))):
        return False
    if since:
        try:
            checked = datetime.fromisoformat((job.get("job_detail_checked_at") or job.get("description_checked_at") or "").replace("Z", "+00:00"))
            started = datetime.fromisoformat(since.replace("Z", "+00:00"))
            if checked < started:
                return False
        except (TypeError, ValueError):
            return False
    return True


def _eligible(job):
    return bool(canonical_url(job.get("url", ""))) and job.get("search_presence") != "not_rediscovered"


def run_parallel_scan(targets, records, output_path, progress=None, stop_event=None,
                      force=True, workers=16, detail_workers=8):
    """Run exactly selected targets, streaming JDs before all discovery finishes.

    A fresh run demotes old selected results until rediscovered. Resume retains
    completed query and detail attempts, including honest blocked outcomes.
    At most workers + detail_workers futures are submitted at once.
    """
    path = Path(output_path)
    stop_event = stop_event or threading.Event()
    workers = max(1, min(20, int(workers)))
    detail_workers = max(1, min(10, int(detail_workers)))
    selected = list(targets)
    wanted = {target["target_id"] for target in selected}
    if len(wanted) != len(selected):
        raise ValueError("Duplicate selected target IDs")

    with campaign.campaign_lock(path):
        previous = campaign.load_campaign(path)
        catalog = OrderedDict(
            (row["target_id"], copy.deepcopy(row))
            for row in previous.get("targets", []) if row.get("target_id") and row.get("name")
        )
        catalog.update((row["target_id"], copy.deepcopy(row)) for row in records)
        catalog.update((row["target_id"], copy.deepcopy(row)) for row in selected)
        rows = {row["target_id"]: copy.deepcopy(row) for row in previous.get("targets", [])}
        for key, target in catalog.items():
            reset = force and key in wanted
            if key not in rows or reset:
                old_jobs = copy.deepcopy(rows.get(key, {}).get("jobs", []))
                if reset:
                    for job in old_jobs:
                        job.update(search_presence="not_rediscovered", status="uncertain",
                                   verification_status="candidate", latest_search_at=campaign.now())
                rows[key] = {
                    "target_id": key, "name": target["name"],
                    "category": target.get("category", "gcc"),
                    "location": target.get("location", "India"), "status": "pending",
                    "checked_at": None, "source_url": campaign.query_url(target),
                    "diagnostics": [], "jobs": old_jobs,
                    "replace_previous_on_success": bool(reset),
                }

        document = copy.deepcopy(previous)
        document.update(
            schema_version=1, started_at=campaign.now() if force else previous.get("started_at", campaign.now()),
            status="running", completed_at=None, threshold_annual_inr=2000000,
            selected_target_ids=sorted(wanted),
        )
        policy = document.setdefault("query_policy", {})
        policy.update(
            roles=campaign.ROLE_QUERY,
            source="Public LinkedIn guest job search; employer structured fallback if blocked",
            per_domain_spacing_seconds=2.0, request_timeout_seconds=10,
            generic_jd_limit_per_target=5,
            pagination="Simple employer/Pega query first; adaptive pagination up to five public pages while matches continue; stops on empty/short/repeated pages or access rejection, with skipped/capped pages reported as partial; not exhaustive",
            detail_policy="Descriptions stream alongside discovery; one selected URL attempt per run; completed attempts are retained on resume",
            salary_policy="Only explicit annual INR CTC establishes the 20 lakh threshold; fixed or unspecified salary remains unknown",
            no_matches_meaning="This query returned no retained profile/employer matches; not proof the employer has no openings",
        )
        detail = {
            "status": "running", "started_at": campaign.now(),
            "total": 0, "checked": 0, "pending": 0, "cached": 0,
            **{outcome: 0 for outcome in OUTCOMES},
            "identity_conflicts": 0, "target_ids": sorted(wanted),
        }
        document["detail_enrichment"] = detail
        discovery_queue = deque(target for target in selected if rows[target["target_id"]].get("status") not in campaign.COMPLETED)
        description_queue = OrderedDict()
        known_urls, completed_details, cached_urls = set(), {}, set()
        discovery_futures, detail_futures = {}, {}
        identity_conflicts = set()
        url_copies, row_urls, applied_copies = {}, {}, {}
        client = campaign.PublicClient(stop_event)

        def index_row(key):
            # Replace only this row's entries. Keep strong references for applied
            # objects, then discard them with the row so Python object-ID reuse
            # can never suppress enrichment of a newly discovered copy.
            for url in row_urls.get(key, ()):
                previous_copies = url_copies.get(url, [])
                for previous_key, saved in previous_copies:
                    if previous_key == key:
                        applied_copies.get(url, {}).pop((key, id(saved)), None)
                remaining = [(other, saved) for other, saved in previous_copies if other != key]
                if remaining:
                    url_copies[url] = remaining
                else:
                    url_copies.pop(url, None)
            row_urls[key] = set()
            for job in rows[key].get("jobs", []):
                url = canonical_url(job.get("url", ""))
                if url:
                    url_copies.setdefault(url, []).append((key, job))
                    row_urls[key].add(url)

        def propagate(url, enriched):
            applied = applied_copies.setdefault(url, {})
            for key, saved in url_copies.get(url, ()):
                copy_key = (key, id(saved))
                if applied.get(copy_key) is saved:
                    continue
                applied[copy_key] = saved
                if _copy_facts(saved, enriched):
                    continue
                # A reused URL is not evidence of the same title/employer.
                if key in wanted and _eligible(saved):
                    identity_conflicts.add((key, saved.get("id"), url))
                    saved.update(
                        job_detail_status="identity_unconfirmed",
                        job_detail_checked_at=enriched.get("job_detail_checked_at", campaign.now()),
                        job_detail_diagnostic={
                            "url": url,
                            "error": "This URL also represents a different saved title or employer; description facts were not copied",
                        },
                    )
            detail["identity_conflicts"] = len(identity_conflicts)

        def finish_detail(url, enriched, cached=False):
            completed_details[url] = copy.deepcopy(enriched)
            if cached:
                cached_urls.add(url)
            propagate(url, enriched)
            detail["checked"] = len(completed_details)
            detail["cached"] = len(cached_urls)
            for outcome in OUTCOMES:
                detail[outcome] = sum(
                    result.get("job_detail_status", "unavailable") == outcome
                    for result in completed_details.values()
                )

        def enroll_details(initial=False, changed_target_id=None):
            candidates = OrderedDict()
            for key in (catalog if changed_target_id is None else (changed_target_id,)):
                if key not in wanted:
                    continue
                for job in rows[key].get("jobs", []):
                    if _eligible(job):
                        candidates.setdefault(canonical_url(job["url"]), []).append(job)
            for url, copies in candidates.items():
                if url in completed_details:
                    propagate(url, completed_details[url])
                    continue
                if url in known_urls:
                    continue
                # An unchecked selected copy takes precedence over another
                # target's old cache. No unselected URL starts a request.
                representative = min(copies, key=lambda job: bool(job.get("job_detail_status")))
                known_urls.add(url)
                detail["total"] = len(known_urls)
                resume_completed = initial and not force and all(
                    job.get("job_detail_status") in OUTCOMES
                    and (job.get("job_detail_status") != "read" or _complete_read(job))
                    for job in copies
                )
                cached = resume_completed or _complete_read(representative, document["started_at"])
                if cached:
                    finish_detail(url, representative, cached=True)
                else:
                    description_queue[url] = copy.deepcopy(representative)
            detail["pending"] = detail["total"] - detail["checked"]

        def checkpoint(current=None, event_kind="progress", target_status=None, target_id=None):
            document["targets"] = [rows[key] for key in catalog]
            document["selected_coverage"] = campaign.coverage([rows[target["target_id"]] for target in selected])
            detail["pending"] = detail["total"] - detail["checked"]
            document["parallel"] = {
                "discovery_active": len(discovery_futures),
                "descriptions_active": len(detail_futures),
                "discovery_workers": workers, "description_workers": detail_workers,
                "discovery_pending": len(discovery_queue),
                "descriptions_pending": len(description_queue),
            }
            stats = getattr(client, "snapshot_stats", None)
            if callable(stats):
                try:
                    document["parallel"]["requests"] = stats()
                except Exception:
                    # Telemetry must never interrupt a saved research run.
                    document["parallel"]["requests"] = {"metrics_unavailable": True}
            try:
                campaign.save_campaign(document, path)
                if progress:
                    progress({
                        "phase": "parallel_scan", "status": document["status"],
                        "event_kind": event_kind, "target_status": target_status, "target_id": target_id,
                        "target_diagnostics": copy.deepcopy(rows.get(target_id,{}).get('diagnostics',[])),
                        "target_partial": rows.get(target_id,{}).get('partial',False),
                        "target_job_count": sum(job.get('search_presence')!='not_rediscovered' for job in rows.get(target_id,{}).get('jobs',[])),
                        "coverage": copy.deepcopy(document["coverage"]),
                        "selected_coverage": copy.deepcopy(document["selected_coverage"]),
                        "detail_enrichment": copy.deepcopy(detail),
                        "parallel": copy.deepcopy(document["parallel"]),
                        "current_target": current, "current_company": current,
                    })
            except BaseException:
                stop_event.set()
                raise

        def inspect(job):
            if stop_event.is_set():
                raise campaign.Cancelled()
            try:
                return campaign.enrich_job(job, client)
            except campaign.Cancelled:
                raise
            except Exception as error:
                enriched = copy.deepcopy(job)
                enriched.update(
                    job_detail_status="unavailable", job_detail_checked_at=campaign.now(),
                    job_detail_diagnostic={
                        "url": campaign.detail_url(job), "error": "Detail check failed: " + str(error)[:180],
                    },
                )
                return enriched

        for key in rows:
            index_row(key)
        enroll_details(initial=True)
        checkpoint()
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="pega-discovery") as discovery_pool, \
             ThreadPoolExecutor(max_workers=detail_workers, thread_name_prefix="pega-description") as detail_pool:
            try:
                while True:
                    added = False
                    if not stop_event.is_set():
                        # Submit descriptions first so each newly found role can
                        # be verified while company searches are still running.
                        while description_queue and len(detail_futures) < detail_workers:
                            url, job = description_queue.popitem(last=False)
                            detail_futures[detail_pool.submit(inspect, job)] = url
                            added = True
                        while discovery_queue and len(discovery_futures) < workers:
                            target = discovery_queue.popleft()
                            discovery_futures[discovery_pool.submit(campaign.check_target, target, client)] = target
                            added = True
                    else:
                        for future in list(discovery_futures) + list(detail_futures):
                            future.cancel()
                    if added:
                        checkpoint()
                    futures = set(discovery_futures) | set(detail_futures)
                    if not futures:
                        break
                    finished, _ = wait(futures, timeout=0.25, return_when=FIRST_COMPLETED)
                    for future in finished:
                        if future in discovery_futures:
                            target = discovery_futures.pop(future)
                            key = target["target_id"]
                            try:
                                record = future.result()
                            except (campaign.Cancelled, CancelledError):
                                continue
                            except Exception as error:
                                record = {
                                    **copy.deepcopy(rows[key]), "status": "error",
                                    "checked_at": campaign.now(), "jobs": [],
                                    "diagnostics": [{"url": campaign.query_url(target), "error": "Check failed: " + str(error)[:220]}],
                                }
                            previous_row = rows[key]
                            replace_missing = previous_row.get("replace_previous_on_success", False) and record.get("status") in ("results", "no_matches")
                            rows[key] = campaign.retain_previous_jobs(record, previous_row, keep_missing=not replace_missing)
                            # A paused refresh must still replace stale missing
                            # roles after its successful resumed discovery.
                            if previous_row.get("replace_previous_on_success") and record.get("status") == "pending":
                                rows[key]["replace_previous_on_success"] = True
                            index_row(key)
                            enroll_details(changed_target_id=key)
                            checkpoint(target["name"], "target", record.get("status"), key)
                        else:
                            url = detail_futures.pop(future)
                            try:
                                enriched = future.result()
                            except (campaign.Cancelled, CancelledError):
                                continue
                            finish_detail(url, enriched)
                            checkpoint(enriched.get("company"), "detail")
            except BaseException:
                stop_event.set()
                for future in list(discovery_futures) + list(detail_futures):
                    future.cancel()
                raise

        selected_coverage = campaign.coverage([rows[target["target_id"]] for target in selected])
        completed = selected_coverage["pending"] == 0 and detail["checked"] == detail["total"]
        document["status"] = "cancelled" if stop_event.is_set() else "complete" if completed else "partial"
        document["completed_at"] = campaign.now() if document["status"] == "complete" else None
        detail["status"] = "cancelled" if stop_event.is_set() else "complete" if detail["checked"] == detail["total"] else "partial"
        detail["completed_at"] = campaign.now() if detail["status"] == "complete" else None
        checkpoint()
        # Shut down the headless browser if it was started
        try:
            import career_scraper
            career_scraper.shutdown()
        except Exception:
            pass
        return document

