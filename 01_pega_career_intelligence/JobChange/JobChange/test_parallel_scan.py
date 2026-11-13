"""Offline behavioral checks for the streaming scan coordinator."""
import copy
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor as RealExecutor
from pathlib import Path
from unittest.mock import patch

import campaign
import parallel_scan

TARGET = {"target_id": "gcc-acme", "name": "Acme", "category": "gcc", "location": "India", "keywords": ["Acme"]}


def target(number):
    return {**TARGET, "target_id": "gcc-acme-" + str(number)}


def job(number=1, title="Pega Developer", company="Acme"):
    return campaign.make_job(title, company, "India", "https://www.linkedin.com/jobs/view/" + str(number),
                             "LinkedIn public jobs", "2026-09-08T00:00:00+00:00")


def record(item, jobs=None, status=None):
    return {**item, "status": status or ("results" if jobs else "no_matches"),
            "checked_at": "2026-09-08T00:00:00+00:00", "diagnostics": [], "jobs": jobs or []}


def read(candidate):
    result = copy.deepcopy(candidate)
    result.update(job_detail_status="read", description_complete=True, description_text="Pega PRPC. 4 years of experience.",
                  description_source_url=candidate["url"], description_checked_at=campaign.now(),
                  job_detail_checked_at=campaign.now(), skills=["Pega"], salary=None)
    return result


class ParallelScanTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "research.json"
        self.stop = threading.Event()

    def run_scan(self, selected=None, records=None, **options):
        selected = selected or [TARGET]
        return parallel_scan.run_parallel_scan(selected, records or selected, self.path,
                                               stop_event=self.stop, **options)

    def seed(self, records):
        campaign.save_campaign({"targets": records, "started_at": "2026-09-08T00:00:00+00:00"}, self.path)

    def test_descriptions_start_before_all_company_searches_finish_and_share_client(self):
        started = threading.Event()
        checked_clients, detail_clients, events = [], [], []
        shared = object()
        def discover(item, client):
            checked_clients.append(client)
            if item["target_id"] == TARGET["target_id"]:
                return record(item, [job()])
            self.assertTrue(started.wait(3), "Description waited until all discovery completed")
            return record(item)
        def inspect(candidate, client):
            detail_clients.append(client)
            started.set()
            return read(candidate)
        with patch.object(campaign, "PublicClient", return_value=shared) as constructor, \
             patch.object(campaign, "check_target", side_effect=discover), \
             patch.object(campaign, "enrich_job", side_effect=inspect):
            result = self.run_scan([TARGET, target(2)], progress=events.append, workers=2, detail_workers=1)
        self.assertEqual(result["detail_enrichment"]["read"], 1)
        self.assertTrue(all(client is shared for client in checked_clients + detail_clients))
        constructor.assert_called_once()
        self.assertTrue(any(event["parallel"]["discovery_active"] and event["parallel"]["descriptions_active"] for event in events))

    def test_futures_are_bounded_not_enqueued_for_entire_directory(self):
        release = threading.Event()
        maxima = {}
        class CountingExecutor:
            def __init__(self, max_workers, thread_name_prefix):
                self.label = thread_name_prefix
                self.actual = RealExecutor(max_workers=max_workers)
                self.pending = 0
                self.lock = threading.Lock()
            def submit(self, *args, **kwargs):
                with self.lock:
                    self.pending += 1
                    maxima[self.label] = max(maxima.get(self.label, 0), self.pending)
                future = self.actual.submit(*args, **kwargs)
                def completed(_):
                    with self.lock:
                        self.pending -= 1
                future.add_done_callback(completed)
                return future
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return self.actual.__exit__(*args)
        def discover(item, client):
            release.wait(2)
            return record(item)
        timer = threading.Timer(0.12, release.set)
        timer.start()
        self.addCleanup(timer.cancel)
        with patch.object(parallel_scan, "ThreadPoolExecutor", CountingExecutor), \
             patch.object(campaign, "check_target", side_effect=discover):
            self.run_scan([target(number) for number in range(30)], workers=2)
        self.assertLessEqual(maxima["pega-discovery"], 2)

    def test_one_description_per_canonical_url_and_late_copies_receive_facts(self):
        first_done = threading.Event()
        def discover(item, client):
            if item["target_id"] != TARGET["target_id"]:
                self.assertTrue(first_done.wait(3))
            found = job()
            if item["target_id"] != TARGET["target_id"]:
                found["url"] += "?tracking=late"
                found["id"] = "other-saved-identity"
            return record(item, [found])
        def inspect(candidate, client):
            first_done.set()
            return read(candidate)
        with patch.object(campaign, "check_target", side_effect=discover), \
             patch.object(campaign, "enrich_job", side_effect=inspect) as enrichment:
            result = self.run_scan([TARGET, target(2)], workers=2)
        enrichment.assert_called_once()
        copies = [row["jobs"][0] for row in result["targets"]]
        self.assertTrue(all(item["job_detail_status"] == "read" for item in copies))
        self.assertEqual(copies[1]["id"], "other-saved-identity")
        self.assertEqual(result["detail_enrichment"]["total"], 1)

    def test_resume_does_not_repeat_completed_query_or_detail_attempts(self):
        checked = read(job())
        failed = job(2)
        failed["job_detail_status"] = "unavailable"
        third = target(3)
        self.seed([record(TARGET, [checked, failed]), record(target(2), status="blocked"), record(third, status="pending")])
        with patch.object(campaign, "check_target", side_effect=lambda item, client: record(item)) as discovery, \
             patch.object(campaign, "enrich_job") as enrichment:
            result = self.run_scan([TARGET, target(2), third], force=False)
        self.assertEqual([call.args[0]["target_id"] for call in discovery.call_args_list], [third["target_id"]])
        enrichment.assert_not_called()
        self.assertEqual(result["detail_enrichment"]["checked"], 2)
        self.assertEqual(result["detail_enrichment"]["unavailable"], 1)
        self.assertEqual(result["selected_coverage"]["blocked"], 1)

    def test_resume_checks_pending_description_and_keeps_fresh_pending_query_jobs(self):
        self.seed([record(TARGET, [job()]), record(target(2), [job(2)], status="pending")])
        with patch.object(campaign, "check_target", side_effect=lambda item, client: record(item, [job(2)])), \
             patch.object(campaign, "enrich_job", side_effect=lambda item, client: read(item)) as enrichment:
            result = self.run_scan([TARGET, target(2)], force=False)
        self.assertEqual(enrichment.call_count, 2)
        self.assertEqual(result["detail_enrichment"]["read"], 2)

    def test_force_excludes_stale_roles_and_replaces_missing_only_after_success(self):
        self.seed([record(TARGET, [read(job(99))]), record(target(2), [read(job(22))])])
        with patch.object(campaign, "check_target", side_effect=lambda item, client: record(item, [job(1)])), \
             patch.object(campaign, "enrich_job", side_effect=lambda item, client: read(item)) as enrichment:
            result = self.run_scan([TARGET], records=[TARGET, target(2)], force=True)
        self.assertEqual([item["id"] for item in result["targets"][0]["jobs"]], [job(1)["id"]])
        self.assertEqual(result["targets"][1]["jobs"][0]["id"], job(22)["id"])
        self.assertEqual(enrichment.call_count, 1)

    def test_failed_fresh_query_demotes_old_result_and_does_not_fetch_old_jd(self):
        self.seed([record(TARGET, [read(job(99))])])
        with patch.object(campaign, "check_target", side_effect=lambda item, client: record(item, status="blocked")), \
             patch.object(campaign, "enrich_job") as enrichment:
            result = self.run_scan()
        enrichment.assert_not_called()
        self.assertEqual(result["targets"][0]["status"], "blocked")
        self.assertEqual(result["targets"][0]["jobs"][0]["search_presence"], "not_rediscovered")
        self.assertEqual(result["detail_enrichment"]["total"], 0)

    def test_cancel_keeps_completed_results_and_resume_finishes_descriptions(self):
        def on_progress(event):
            if event["selected_coverage"]["checked"]:
                self.stop.set()
        with patch.object(campaign, "check_target", side_effect=lambda item, client: record(item, [job()])), \
             patch.object(campaign, "enrich_job") as enrichment:
            cancelled = self.run_scan(progress=on_progress, workers=1)
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(cancelled["targets"][0]["jobs"][0]["id"], job()["id"])
        enrichment.assert_not_called()
        self.stop.clear()
        with patch.object(campaign, "check_target") as discovery, \
             patch.object(campaign, "enrich_job", side_effect=lambda item, client: read(item)):
            resumed = self.run_scan(force=False)
        discovery.assert_not_called()
        self.assertEqual(resumed["detail_enrichment"]["read"], 1)

    def test_current_discovery_full_description_is_reused_but_previous_force_cache_is_not(self):
        self.seed([record(TARGET, [read(job(1))])])
        fresh = read(job(2))
        with patch.object(campaign, "check_target", return_value=record(TARGET, [job(1), fresh])), \
             patch.object(campaign, "enrich_job", side_effect=lambda item, client: read(item)) as enrichment:
            result = self.run_scan()
        self.assertEqual([call.args[0]["url"] for call in enrichment.call_args_list], [job(1)["url"]])
        self.assertEqual(result["detail_enrichment"]["cached"], 1)

    def test_mismatched_identity_does_not_receive_description_or_lose_user_fields(self):
        one, two = target(1), target(2)
        saved = read(job())
        saved["id"] = "saved-id"
        saved["pipeline_status"] = "shortlisted"
        saved["notes"] = "My own note"
        different = job(title="Pega Architect", company="Other")
        self.seed([record(one, [saved]), record(two, [different])])
        with patch.object(campaign, "check_target"), \
             patch.object(campaign, "enrich_job", side_effect=lambda item, client: read(item)):
            result = self.run_scan([two], records=[one, two], force=False)
        original = result["targets"][0]["jobs"][0]
        self.assertEqual(original, saved)
        self.assertEqual(result["targets"][1]["jobs"][0]["company"], "Other")

    def test_saved_matching_copy_keeps_identity_notes_and_independent_salary(self):
        unrelated = target(2)
        saved = job()
        saved.update(id="saved-id", notes="Contact later", pipeline_status="shortlisted",
                     salary={"amount_min": 2500000, "amount_max": 2500000, "currency": "INR",
                             "period": "annual", "basis": "total_compensation"})
        self.seed([record(TARGET), record(unrelated, [saved])])
        with patch.object(campaign, "check_target", return_value=record(TARGET, [job()])), \
             patch.object(campaign, "enrich_job", side_effect=lambda item, client: read(item)):
            result = self.run_scan([TARGET], records=[TARGET, unrelated])
        copy_result = result["targets"][1]["jobs"][0]
        self.assertEqual((copy_result["id"], copy_result["notes"], copy_result["pipeline_status"]),
                         ("saved-id", "Contact later", "shortlisted"))
        self.assertEqual(copy_result["salary"]["amount_min"], 2500000)
        self.assertIsNone(result["targets"][0]["jobs"][0].get("salary"))

    def test_network_error_is_saved_as_unavailable_and_query_error_stays_error(self):
        with patch.object(campaign, "check_target", side_effect=lambda item, client: record(item, [job()])), \
             patch.object(campaign, "enrich_job", side_effect=RuntimeError("request failed")):
            result = self.run_scan()
        self.assertEqual(result["detail_enrichment"]["unavailable"], 1)
        self.assertIn("request failed", result["targets"][0]["jobs"][0]["job_detail_diagnostic"]["error"])
        with patch.object(campaign, "check_target", side_effect=RuntimeError("blocked source")):
            failed = self.run_scan()
        self.assertEqual(failed["targets"][0]["status"], "error")
        self.assertEqual(failed["selected_coverage"]["no_matches"], 0)

    def test_checkpoint_failure_stops_workers_and_preserves_previous_file(self):
        self.seed([record(TARGET)])
        previous = self.path.read_bytes()
        with patch.object(campaign, "save_campaign", side_effect=OSError("disk full")), \
             patch.object(campaign, "check_target") as discovery:
            with self.assertRaisesRegex(OSError, "disk full"):
                self.run_scan()
        self.assertTrue(self.stop.is_set())
        discovery.assert_not_called()
        self.assertEqual(self.path.read_bytes(), previous)

    def test_incomplete_read_status_is_not_accepted_as_resume_cache(self):
        incomplete = job()
        incomplete["job_detail_status"] = "read"
        self.seed([record(TARGET, [incomplete])])
        with patch.object(campaign, "check_target") as discovery, \
             patch.object(campaign, "enrich_job", side_effect=lambda item, client: read(item)) as enrichment:
            result = self.run_scan(force=False)
        discovery.assert_not_called()
        enrichment.assert_called_once()
        self.assertEqual(result["detail_enrichment"]["cached"], 0)

    def test_stale_full_description_returned_by_discovery_is_refetched_on_force(self):
        old = read(job())
        old["job_detail_checked_at"] = "2020-01-01T00:00:00+00:00"
        old["description_checked_at"] = old["job_detail_checked_at"]
        with patch.object(campaign, "check_target", return_value=record(TARGET, [old])), \
             patch.object(campaign, "enrich_job", side_effect=lambda item, client: read(item)) as enrichment:
            self.run_scan(force=True)
        enrichment.assert_called_once()

    def test_progress_includes_checkpointed_outcomes_and_client_stats(self):
        class Client:
            def snapshot_stats(self):
                return {"network_requests": 3}
        events = []
        with patch.object(campaign, "PublicClient", return_value=Client()), \
             patch.object(campaign, "check_target", return_value=record(TARGET)):
            self.run_scan(progress=events.append)
        event = next(item for item in events if item["event_kind"] == "target")
        self.assertEqual(event["target_status"], "no_matches")
        self.assertEqual(event["target_id"], TARGET["target_id"])
        self.assertEqual(event["parallel"]["requests"]["network_requests"], 3)

    def test_cached_fact_copy_work_is_linear_when_empty_targets_finish(self):
        pending = [target(number) for number in range(24)]
        self.seed([record(TARGET, [read(job(100 + number)) for number in range(40)])]
                  + [record(item, status="pending") for item in pending])
        with patch.object(campaign, "check_target", side_effect=lambda item, client: record(item)), \
             patch.object(campaign, "enrich_job") as enrichment, \
             patch.object(parallel_scan, "_copy_facts", wraps=parallel_scan._copy_facts) as copy_facts:
            result = self.run_scan([TARGET, *pending], force=False)
        enrichment.assert_not_called()
        self.assertEqual(result["detail_enrichment"]["read"], 40)
        self.assertEqual(copy_facts.call_count, 40)

    def test_lock_prevents_competing_coordinators(self):
        with campaign.campaign_lock(self.path), patch.object(campaign, "check_target") as discovery:
            with self.assertRaises((RuntimeError, BlockingIOError)):
                self.run_scan()
        discovery.assert_not_called()


if __name__ == "__main__":
    unittest.main()

