"""Headless browser scraper for employer career portals.

Uses Playwright to render JavaScript-heavy career sites, search for Pega
roles, and extract job listings that plain HTTP cannot see.
Every scrape attempt is logged with full diagnostics for post-run analysis.
"""
from __future__ import annotations

import json
import re
import logging
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from normalizer import from_jobposting, jsonld_jobs

logger = logging.getLogger(__name__)

# Scrape log: every attempt is recorded for post-run root cause analysis
_scrape_log = []


def get_scrape_log():
    """Return a copy of the full scrape log for analysis."""
    return list(_scrape_log)


def clear_scrape_log():
    """Reset the scrape log for a new run."""
    _scrape_log.clear()


def save_scrape_log(path=None):
    """Write the scrape log to a JSON file for review."""
    if path is None:
        path = Path(__file__).resolve().parent / "data" / "career_scrape_log.json"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = analyze_scrape_log()
    payload = {"log": _scrape_log, "summary": summary,
               "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def analyze_scrape_log():
    """Root cause analysis of scrape failures."""
    if not _scrape_log:
        return {"total": 0}
    total = len(_scrape_log)
    successes = [e for e in _scrape_log if e.get("jobs_found", 0) > 0]
    failures = [e for e in _scrape_log if e.get("jobs_found", 0) == 0]

    # Categorize failure reasons
    reasons = {}
    for entry in failures:
        reason = entry.get("failure_reason", "unknown")
        reasons.setdefault(reason, []).append(entry.get("company", entry.get("source", "?")))

    return {
        "total": total,
        "success": len(successes),
        "failed": len(failures),
        "success_rate": f"{len(successes)/total*100:.1f}%" if total else "0%",
        "total_jobs_found": sum(e.get("jobs_found", 0) for e in _scrape_log),
        "avg_time_seconds": round(sum(e.get("elapsed_s", 0) for e in _scrape_log) / total, 1) if total else 0,
        "failure_reasons": {reason: {"count": len(companies), "examples": companies[:5]}
                           for reason, companies in sorted(reasons.items(), key=lambda x: -len(x[1]))},
    }

# Lazy-init: Playwright is heavy, only start when first needed
_browser_context = None
_playwright_instance = None

import threading
from scan_coordinator import DomainBudget
_domain_budget = DomainBudget()
_browser_stop = threading.Event()


def configure_run(stop_event):
    global _domain_budget, _browser_stop
    _domain_budget = DomainBudget()
    _browser_stop = stop_event


def _navigate(page, url, timeout, wait_until='domcontentloaded'):
    _domain_budget.wait(url,_browser_stop)
    response=page.goto(url,timeout=timeout,wait_until=wait_until)
    if response and response.status>=400:
        retry_after=response.headers.get('retry-after','0')
        try:delay=max(0,float(retry_after))
        except ValueError:delay=300
        _domain_budget.reject(url,response.status,retry_after=delay)
        raise RuntimeError('Source returned HTTP '+str(response.status))
    if _browser_stop.is_set():raise InterruptedError('Scan cancelled')
    return response


def _get_browser():
    """Start a shared headless Chromium instance (lazy, reused across calls)."""
    global _browser_context, _playwright_instance
    if _browser_context is None:
        from playwright.sync_api import sync_playwright
        _playwright_instance = sync_playwright().start()
        browser = _playwright_instance.chromium.launch(headless=True)
        _browser_context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            java_script_enabled=True,
        )
    return _browser_context


def shutdown():
    """Close the shared browser. Safe to call if never started."""
    global _browser_context, _playwright_instance
    try:
        if _browser_context:
            _browser_context.close()
        if _playwright_instance:
            _playwright_instance.stop()
    except Exception:
        pass
    _browser_context = None
    _playwright_instance = None


def _strip_html(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


def _greenhouse_board_token(career_url):
    parsed = urllib.parse.urlsplit(career_url)
    host = parsed.hostname or ""
    parts = [part for part in parsed.path.split("/") if part]
    if "job-boards.greenhouse.io" in host and parts:
        return parts[0]
    if "boards.greenhouse.io" in host and parts:
        return parts[0]
    if "boards-api.greenhouse.io" in host:
        try:
            index = parts.index("boards")
            return parts[index + 1]
        except (ValueError, IndexError):
            return None
    return None


def scrape_greenhouse_board(career_url, company_name, keyword="pega", checked_at=None, limit=100):
    board = _greenhouse_board_token(career_url)
    if not board:
        return [], {"greenhouse": False}
    checked_at = checked_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
    diagnostics = {"greenhouse": True, "source": "greenhouse_board_api", "board": board, "api_url": api_url}
    jobs = []
    try:
        data = _workday_api_json(api_url)
    except Exception as exc:
        diagnostics["error"] = str(exc)[:160]
        return jobs, diagnostics
    postings = data.get("jobs") or []
    diagnostics["returned"] = len(postings)
    for posting in postings[:limit]:
        title = posting.get("title") or ""
        location = ((posting.get("location") or {}).get("name") or "Location unconfirmed") if isinstance(posting.get("location"), dict) else "Location unconfirmed"
        description_text = _strip_html(posting.get("content") or "")
        evidence_text = " ".join([title, location, description_text])
        if not _is_pega_related(evidence_text) or not _is_india_scope(evidence_text):
            continue
        jobs.append({
            "title": title,
            "company": posting.get("company_name") or company_name,
            "url": posting.get("absolute_url") or career_url,
            "location": location,
            "source": "Employer career page",
            "checked_at": checked_at,
            "description": description_text[:500],
            "description_text": description_text,
            "description_complete": bool(description_text),
            "description_source_url": api_url,
            "job_detail_status": "read" if description_text else "unavailable",
            "requisition_id": posting.get("requisition_id") or str(posting.get("id") or "") or None,
            "posted_at": posting.get("first_published") or posting.get("updated_at"),
        })
    diagnostics["jobs_found"] = len(jobs)
    return jobs, diagnostics


def _workday_context(career_url):
    parsed = urllib.parse.urlsplit(career_url)
    host = parsed.hostname or ""
    if "myworkdayjobs.com" not in host:
        return None
    tenant = host.split(".")[0]
    parts = [part for part in parsed.path.split("/") if part]
    if parts and re.match(r"^[a-z]{2}-[A-Z]{2}$", parts[0]):
        parts = parts[1:]
    if not tenant or not parts:
        return None
    site = parts[0]
    if site == "job":
        return None
    base_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
    return {"base_url": base_url, "tenant": tenant, "site": site}


def _workday_api_json(url, payload=None, timeout=20):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method="POST" if payload is not None else "GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def scrape_workday_cxs(career_url, company_name, keyword="pega", checked_at=None, limit=20, detail_limit=10):
    context = _workday_context(career_url)
    if not context:
        return [], {"workday": False}
    checked_at = checked_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    jobs = []
    diagnostics = {"workday": True, "source": "workday_cxs", "tenant": context["tenant"], "site": context["site"]}
    search_url = f'{context["base_url"]}/wday/cxs/{context["tenant"]}/{context["site"]}/jobs'
    try:
        payload = {"appliedFacets": {}, "limit": limit, "offset": 0, "searchText": keyword}
        results = _workday_api_json(search_url, payload=payload)
    except Exception as exc:
        diagnostics["error"] = str(exc)[:160]
        return jobs, diagnostics
    postings = results.get("jobPostings") or []
    diagnostics.update(search_url=search_url, total=results.get("total"), returned=len(postings))
    for posting in postings[:detail_limit]:
        external_path = posting.get("externalPath") or ""
        title = posting.get("title") or ""
        location = posting.get("locationsText") or "Location unconfirmed"
        if not external_path:
            continue
        detail_url = f'{context["base_url"]}/wday/cxs/{context["tenant"]}/{context["site"]}{external_path}'
        public_url = urllib.parse.urljoin(f'{context["base_url"]}/{context["site"]}', external_path)
        try:
            detail = _workday_api_json(detail_url)
        except Exception:
            detail = {}
        info = detail.get("jobPostingInfo") if isinstance(detail, dict) else {}
        if isinstance(info, dict):
            title = info.get("title") or title
            location = info.get("location") or info.get("locationText") or location
            description_text = _strip_html(info.get("jobDescription") or "")
            public_url = urllib.parse.urljoin(context["base_url"], info.get("externalUrl") or external_path)
            posted_at = info.get("postedOn") or posting.get("postedOn")
        else:
            description_text = ""
            posted_at = posting.get("postedOn")
        evidence_text = " ".join([title, location, description_text])
        if not _is_pega_related(evidence_text) or not _is_india_scope(evidence_text):
            continue
        bullet_fields = posting.get("bulletFields") or []
        jobs.append({
            "title": title,
            "company": company_name,
            "url": public_url,
            "location": location,
            "source": "Employer career page",
            "checked_at": checked_at,
            "description": description_text[:500],
            "description_text": description_text,
            "description_complete": bool(description_text),
            "description_source_url": detail_url,
            "job_detail_status": "read" if description_text else "unavailable",
            "requisition_id": bullet_fields[0] if bullet_fields else None,
            "posted_at": posted_at,
        })
    diagnostics["jobs_found"] = len(jobs)
    return jobs, diagnostics


def _build_search_url(career_url, keyword="pega"):
    """Append search query to career URL using common parameter patterns."""
    parsed = urllib.parse.urlsplit(career_url)
    params = urllib.parse.parse_qs(parsed.query)

    # If URL already has a search keyword param, replace it
    for key in ("q", "keyword", "keywords", "search", "k", "query"):
        if key in params:
            params[key] = [keyword]
            new_query = urllib.parse.urlencode(params, doseq=True)
            return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, new_query, ""))

    # Otherwise append the most common search param
    sep = "&" if parsed.query else "?"
    return career_url + sep + "keyword=" + urllib.parse.quote(keyword)


def _is_pega_related(text):
    """Check if text mentions Pega/PRPC responsibilities or adjacent implementation evidence."""
    return bool(re.search(
        r"\b(pega|PRPC|CSSA|CLSA|OpenSpan|Pega\s+Platform|Pega\s+Cloud|Pega\s+Blueprint|case\s+lifecycle|Customer\s+Decision\s+Hub|CDH|Pega\s+Decision\s+Hub|Connect[- ]REST|Service[- ]REST|Connect[- ]SQL)\b",
        text, re.I))


def _is_india_scope(text):
    return bool(re.search(r"\b(India|Bengaluru|Bangalore|Hyderabad|Pune|Chennai|Mumbai|Delhi|Gurgaon|Gurugram|Noida|Kolkata|Kochi|Remote)\b", text or "", re.I))


def _is_search_or_listing_page(url, title=""):
    # URL patterns: English + localized career search pages
    url_hit = bool(re.search(
        r"/search-jobs/|/search(?:[/?#]|$)|/jobs/search|/job-search|/careers/search"
        r"|/jobsuche/|/jobsuche(?:[?#]|$)"        # German
        r"|/recherche(?:-emploi)?/"                 # French
        r"|/busqueda/"                              # Spanish
        r"|jobsearch[?#]"                           # querystring-style (Accenture)
        r"|/job-results[/?#]"
        r"|/jobs\?.*\b(?:keyword|q|search)=",       # /jobs?keyword=pega
        url or "", re.I))
    # Title patterns: page headings that clearly describe a search/listing, not a single job
    title_hit = bool(re.search(
        r"^search\s+jobs|^job\s+openings?$|^search\s+results?"
        r"|jobs?\s+durchsuchen"                     # German "browse jobs"
        r"|career(s)?$"                             # bare "Careers" page title
        r"|job\s+listing|find\s+(a\s+)?job|explore\s+opportunities"
        r"|helfen\s+sie\s+.*arbeiten"               # Cargill-style German tagline
        r"|browse\s+jobs|all\s+jobs|open\s+positions$"
        r"|^search\s+job|^find\s+.*career",
        title or "", re.I))
    return bool(url_hit or title_hit)


def _is_zero_result_page(body_text):
    """Detect search result pages that returned zero matching jobs."""
    snippet = (body_text or "")[:3000].lower()
    return bool(re.search(
        r"\b0\s+results?\b|\bno\s+(jobs?|results?|positions?|openings?|matches?)\s+(found|available|match)"
        r"|\bkeine\s+(ergebnisse?|stellen)"          # German
        r"|\baucun\s+r[eé]sultat"                     # French
        r"|\bsin\s+resultados"                         # Spanish
        r"|didn.?t\s+find\s+any|sorry.{0,30}no\s+(results?|jobs?)"
        r"|your\s+search\s+(did\s+not|didn.?t)\s+(return|match|find)"
        r"|try\s+(different|other|new)\s+(keywords?|search|criteria)"
        r"|0\s+jobs?\s+found"
        r"|showing\s+0\s+of|results?\s*:\s*0",
        snippet))


def _extract_current_job_page(page, company_name, checked_at):
    jobs = []
    try:
        html = page.content()
    except Exception:
        return jobs
    for posting in jsonld_jobs(html):
        try:
            structured = from_jobposting(posting, page.url)
            text = str(structured.get("title", "")) + " " + str(structured.get("description_text", ""))
            if not _is_pega_related(text):
                continue
            location = structured.get("location", "")
            if _is_search_or_listing_page(structured.get("url") or page.url, structured.get("title", "")) or (location and location != "Location unconfirmed" and not _is_india_scope(location)):
                continue
            structured.update(company=structured.get("company") or company_name,
                              source="Employer career page", checked_at=checked_at,
                              description=structured.get("description_text", "")[:500])
            jobs.append(structured)
        except Exception:
            continue
    if jobs:
        return jobs
    try:
        body_text = page.inner_text("body")
    except Exception:
        return jobs
    if not _is_pega_related(body_text):
        return jobs
    # Reject zero-result search pages early — keyword "pega" appears because
    # it is echoed in the search bar / breadcrumb, not in an actual posting.
    if _is_zero_result_page(body_text):
        return jobs
    job_like_page = re.search(r"/job/|/jobs/|/career/|/careers/|/opening/|/position/|/posting/|/requisition/", page.url, re.I)
    job_like_text = re.search(r"\b(job|role|position|opening|apply|responsibilities|requirements|qualifications|experience)\b", body_text[:2500], re.I)
    if not job_like_page and not job_like_text:
        return jobs
    try:
        title = page.locator("h1").first.inner_text(timeout=1500).strip()
    except Exception:
        title = "Pega role"
    if not title or len(title) > 160:
        title = "Pega role"
    if _is_search_or_listing_page(page.url, title):
        return jobs
    location_match = re.search(r"(Bengaluru|Bangalore|Hyderabad|Pune|Chennai|Mumbai|Delhi|Gurgaon|Gurugram|Noida|India|Remote)(?:,\s*[^\n]+)?", body_text, re.I)
    if not location_match and not _is_india_scope(body_text[:4000]):
        return jobs
    jobs.append({"title": title, "company": company_name, "url": page.url,
                 "location": location_match.group(0) if location_match else "Location unconfirmed",
                 "source": "Employer career page", "checked_at": checked_at,
                 "description": body_text[:500], "description_text": body_text,
                 "description_complete": True, "job_detail_status": "read",
                 "description_source_url": page.url})
    return jobs


def _collect_candidate_detail_urls(page, limit=12):
    selectors = [
        'a[href*="/job"]', 'a[href*="/jobs"]', 'a[href*="/career"]', 'a[href*="/careers"]',
        'a[href*="/opening"]', 'a[href*="/position"]', 'a[href*="/posting"]', 'a[href*="/requisition"]',
        'a[href*="myworkdayjobs.com"]', 'a[href*="greenhouse.io"]', 'a[href*="lever.co"]',
        '[class*="job"] a', '[class*="role"] a', '[class*="opening"] a', '[class*="position"] a',
        'li a', 'article a', 'tr a',
    ]
    deny_text = re.compile(r"^(back|home|search|sign|log|privacy|terms|cookie|save|share|menu|close|accept|reject|learn more|view all)$", re.I)
    deny_url = re.compile(r"/(privacy|terms|cookie|login|signin|sign-in|saved-jobs|job-alert|talent-community|locations?)(?:[/?#]|$)", re.I)
    urls = []
    seen = set()
    for selector in selectors:
        try:
            elements = page.query_selector_all(selector)
        except Exception:
            continue
        for element in elements:
            try:
                href = element.get_attribute("href") or ""
                text = element.inner_text().strip()
                if not href or deny_text.match(text[:80]):
                    continue
                full_url = urllib.parse.urljoin(page.url, href)
                if deny_url.search(full_url) or full_url in seen:
                    continue
                # Skip links that point back to a search/listing page
                if _is_search_or_listing_page(full_url, text):
                    continue
                surrounding_text = ""
                try:
                    surrounding_text = element.evaluate(
                        "el => (el.closest('li, tr, article, div[class*=list-item], div[class*=card], div[class*=job], div[class*=role], div[class*=opening]') || el.parentElement)?.innerText || ''"
                    )[:800]
                except Exception:
                    pass
                candidate_text = (text + " " + surrounding_text).strip()
                looks_like_job = re.search(r"\b(job|role|position|opening|apply|engineer|developer|architect|analyst|consultant|manager|specialist|lead)\b", candidate_text, re.I)
                looks_like_url = re.search(r"/job|/career|/opening|/position|/posting|/requisition|myworkdayjobs|greenhouse|lever", full_url, re.I)
                if not looks_like_job and not looks_like_url:
                    continue
                seen.add(full_url)
                urls.append(full_url)
                if len(urls) >= limit:
                    return urls
            except Exception:
                continue
    return urls


def _follow_candidate_detail_urls(page, company_name, checked_at, timeout_ms, limit=8):
    detail_urls = _collect_candidate_detail_urls(page, limit=limit)
    jobs = []
    checked = 0
    for detail_url in detail_urls:
        try:
            _navigate(page, detail_url, timeout=timeout_ms, wait_until="domcontentloaded")
            page.wait_for_timeout(1000)
            checked += 1
            jobs.extend(_extract_current_job_page(page, company_name, checked_at))
        except Exception:
            continue
    return jobs, checked, len(detail_urls)


def scrape_career_page(career_url, company_name, keyword="pega", timeout_ms=12000):
    """
    Scrape a career portal for Pega jobs using a headless browser.

    Returns a list of job dicts with: title, company, url, location, source, checked_at
    """
    start_time = time.perf_counter()
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    jobs = []
    diagnostic = {"url": career_url, "source": "career_portal_playwright", "checked_at": checked_at}
    log_entry = {"company": company_name, "url": career_url, "checked_at": checked_at,
                 "type": "career_portal", "jobs_found": 0, "failure_reason": None}

    workday_jobs, workday_diag = scrape_workday_cxs(career_url, company_name, keyword=keyword, checked_at=checked_at)
    if workday_diag.get("workday"):
        diagnostic["workday_cxs"] = workday_diag
        if workday_jobs:
            jobs.extend(workday_jobs)
            diagnostic.update(jobs_found=len(jobs), searched=True, final_url=career_url, method="workday_cxs")
            log_entry.update(jobs_found=len(jobs), elapsed_s=round(time.perf_counter() - start_time, 1), method="workday_cxs")
            _scrape_log.append(log_entry)
            return jobs, diagnostic

    greenhouse_jobs, greenhouse_diag = scrape_greenhouse_board(career_url, company_name, keyword=keyword, checked_at=checked_at)
    if greenhouse_diag.get("greenhouse"):
        diagnostic["greenhouse_board_api"] = greenhouse_diag
        if greenhouse_jobs:
            jobs.extend(greenhouse_jobs)
            diagnostic.update(jobs_found=len(jobs), searched=True, final_url=career_url, method="greenhouse_board_api")
            log_entry.update(jobs_found=len(jobs), elapsed_s=round(time.perf_counter() - start_time, 1), method="greenhouse_board_api")
            _scrape_log.append(log_entry)
            return jobs, diagnostic

    try:
        ctx = _get_browser()
        page = ctx.new_page()
        page.set_default_timeout(min(timeout_ms,5000))

        # Navigate to the career page
        try:
            _navigate(page, career_url, timeout=timeout_ms, wait_until="domcontentloaded")
        except Exception as nav_err:
            diagnostic["error"] = f"Navigation failed: {str(nav_err)[:120]}"
            log_entry.update(failure_reason="navigation_failed", error=str(nav_err)[:120],
                             elapsed_s=round(time.perf_counter() - start_time, 1))
            _scrape_log.append(log_entry)
            page.close()
            return jobs, diagnostic

        page.wait_for_timeout(2000)
        jobs.extend(_extract_current_job_page(page, company_name, checked_at))
        if jobs:
            diagnostic.update(jobs_found=len(jobs), searched=False, final_url=page.url, method="job_detail")
            log_entry.update(jobs_found=len(jobs), elapsed_s=round(time.perf_counter() - start_time, 1))
            page.close()
            _scrape_log.append(log_entry)
            return jobs, diagnostic

        # Dismiss cookie banners, popups, overlays that block interaction
        for dismiss_sel in [
            'button:has-text("Accept")', 'button:has-text("Accept All")',
            'button:has-text("Agree")', 'button:has-text("OK")',
            'button:has-text("Got it")', 'button:has-text("Close")',
            'button:has-text("Dismiss")', 'button:has-text("Continue")',
            '[id*="cookie"] button', '[class*="cookie"] button',
            '[id*="consent"] button', '[class*="consent"] button',
            '[id*="alert"] button', '[class*="alert"] button',
            '[class*="overlay"] button', '[class*="modal"] button',
            '.system-ialert-close-button',
        ]:
            try:
                btn = page.query_selector(dismiss_sel)
                if btn and btn.is_visible():
                    btn.click(timeout=2000)
                    page.wait_for_timeout(500)
                    break
            except Exception:
                continue

        # Strategy A: Find a search box and type the keyword like a real user
        searched = False
        search_selectors = [
            # Standard HTML
            'input[type="search"]',
            # By name/id
            'input[name*="search" i]', 'input[name*="keyword" i]', 'input[name*="query" i]',
            'input[id*="search" i]', 'input[id*="keyword" i]', 'input[id*="query" i]',
            # By placeholder
            'input[placeholder*="search" i]', 'input[placeholder*="keyword" i]',
            'input[placeholder*="job" i]', 'input[placeholder*="role" i]',
            'input[placeholder*="title" i]', 'input[placeholder*="position" i]',
            'input[placeholder*="what" i]',
            # By aria
            'input[aria-label*="search" i]', 'input[aria-label*="keyword" i]',
            'input[aria-label*="job" i]',
            # By class
            'input[class*="search" i]', 'input[class*="keyword" i]',
            # Platform-specific: Oracle Cloud / Taleo
            'input[data-automation-id*="search" i]', 'input[data-automation-id*="keyword" i]',
            # Workday
            'input[data-uxi-widget-type="search"]',
            # Phenom
            '[data-ph-id] input[type="text"]',
            # Generic visible text inputs
            'form input[type="text"][aria-label*="keyword" i]',
        ]
        for sel in search_selectors:
            try:
                inputs = page.query_selector_all(sel)
                for search_input in inputs:
                    if not search_input.is_visible():
                        continue
                    # Skip tiny inputs (likely not a search box)
                    box = search_input.bounding_box()
                    if box and box.get("width", 0) < 80:
                        continue
                    try:
                        search_input.click(force=True, timeout=3000)
                        search_input.fill("")
                        search_input.type(keyword, delay=50)
                        search_input.press("Enter")
                        page.wait_for_timeout(4000)
                        result_container=page.query_selector('[id*="search-results"], [data-testid="search-results"], [class*="search-results"]')
                        result_text=page.inner_text('body')
                        searched=bool(result_container and re.search(r'\b(?:results?|jobs?|positions?)\b',result_text,re.I) and keyword.casefold() in result_text.casefold())
                        diagnostic['search_submitted']=True
                        diagnostic['search_verified']=searched
                        if searched:break
                    except Exception:
                        continue
                if searched:
                    break
            except Exception:
                continue

        # Strategy B: If no search box worked, try URL manipulation patterns
        # Covers Oracle Cloud, Workday, iCIMS, Phenom, and generic patterns
        if not searched:
            parsed = urllib.parse.urlsplit(career_url)
            host = parsed.hostname or ""
            base = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
            # Detect org ID from current page URL or HTML for /search-jobs/{keyword}/{orgId}/1 pattern
            # TalentBrew sites embed the org ID in asset URLs like company/34088/
            current_url = page.url
            page_html = page.content()[:15000]
            org_match = re.search(r'/search-jobs/[^/]*/(\d{4,})/', current_url)
            if not org_match:
                org_match = re.search(r'/search-jobs/[^/]*/(\d{4,})/', page_html)
            if not org_match:
                org_match = re.search(r'talentbrew\.com/company/(\d{4,})/', page_html)
            if not org_match:
                org_match = re.search(r'/company/(\d{4,})/', page_html)
            org_id = org_match.group(1) if org_match else ""
            org_suffix = "/" + org_id + "/1" if org_id else ""
            search_variants = [
                _build_search_url(career_url, keyword),
                # Path-based search with org ID (UHG, Barclays, Citi pattern)
                base + "/search-jobs/" + keyword + org_suffix,
                base + "/search-jobs/" + keyword,
                base + "/jobs?q=" + keyword,
                base + "/jobs?keyword=" + keyword,
                base + "/jobs?search=" + keyword,
                base + "/careers/search?q=" + keyword,
                base + "/search?q=" + keyword + "+jobs",
            ]
            # Oracle Cloud / Taleo
            if "oraclecloud.com" in host:
                search_variants.append(career_url + ("&" if "?" in career_url else "?") + "keyword=" + keyword)
            # Workday
            if "myworkdayjobs.com" in host or "wd" in host:
                search_variants.append(career_url.rstrip("/") + "?q=" + keyword)
            for variant in search_variants:
                if variant == career_url:
                    continue
                try:
                    _navigate(page, variant, timeout=timeout_ms, wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)
                    body_text = page.inner_text("body")[:1000].lower()
                    # Accept if the page mentions pega AND has job-related content
                    if keyword.lower() in body_text and any(w in body_text for w in ("result", "job", "found", "position", "opening", "match", "showing", "career")):
                        searched = True
                        break
                except Exception:
                    continue

        # TalentBrew fix: if we detected an org ID, go directly to the
        # /search-jobs/{keyword}/{orgId}/1 URL which is the only format that works
        if not searched and org_id:
            try:
                tb_url = base + "/search-jobs/" + keyword + "/" + org_id + "/1"
                _navigate(page, tb_url, timeout=timeout_ms, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)
                body_text = page.inner_text("body")[:1000].lower()
                if keyword.lower() in body_text:
                    searched = True
            except Exception:
                pass
        # Also fix if search box navigated to /search-jobs/{keyword}/{orgId} without /1
        current = page.url
        tb_match = re.match(r"(https?://[^/]+/search-jobs/[^/]+/\d+)$", current)
        if tb_match:
            try:
                _navigate(page, current + "/1", timeout=timeout_ms, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                searched = True
            except Exception:
                pass

        diagnostic["searched"] = searched
        diagnostic["final_url"] = page.url

        # Strategy 1: Extract from LD+JSON structured data
        ld_scripts = page.query_selector_all('script[type="application/ld+json"]')
        for script in ld_scripts:
            try:
                import json
                data = json.loads(script.inner_text())
                items = []
                if isinstance(data, dict):
                    if data.get("@type") == "JobPosting":
                        items = [data]
                    elif data.get("@type") == "ItemList":
                        items = [el.get("item", el) for el in data.get("itemListElement", [])
                                 if isinstance(el, dict)]
                elif isinstance(data, list):
                    items = [d for d in data if isinstance(d, dict) and d.get("@type") == "JobPosting"]

                for item in items:
                    title = item.get("title", "")
                    if not _is_pega_related(title + " " + item.get("description", "")[:500]):
                        continue
                    org = item.get("hiringOrganization", {})
                    org_name = org.get("name", "") if isinstance(org, dict) else ""
                    locs = item.get("jobLocation", [])
                    if not isinstance(locs, list):
                        locs = [locs]
                    location_parts = []
                    for loc in locs:
                        addr = loc.get("address", {}) if isinstance(loc, dict) else {}
                        if isinstance(addr, dict):
                            location_parts.append(", ".join(
                                str(addr[k]) for k in ("addressLocality", "addressRegion", "addressCountry") if addr.get(k)
                            ))
                    location = "; ".join(location_parts) or "Location unconfirmed"
                    job_url = item.get("url", "")
                    if job_url:
                        job_url = urllib.parse.urljoin(page.url, job_url)
                    if _is_search_or_listing_page(job_url or page.url, title) or (location != "Location unconfirmed" and not _is_india_scope(location)):
                        continue

                    jobs.append({
                        "title": title,
                        "company": org_name or company_name,
                        "url": job_url,
                        "location": location,
                        "source": "Employer career page",
                        "checked_at": checked_at,
                        "description": item.get("description", "")[:500],
                        "posted_at": item.get("datePosted"),
                    })
            except Exception:
                continue

        # Strategy 2: Extract from visible HTML job cards
        # Search result containers vary by site, so cast a wide net for
        # any link inside a card/list-item that points to a job page.
        if not jobs:
            card_selectors = [
                # Search result cards (common across many ATS platforms)
                '[class*="search-results"] a[href*="/job"]',
                '[class*="search-results"] a[href*="/position"]',
                '[class*="search-results"] a[href*="/requisition"]',
                '[id*="search-results"] a',
                # Common job card/list patterns
                '[class*="job-title"] a', 'a[class*="job-title"]',
                '[class*="job-card"] a', '[class*="job-list"] a[href*="/job"]',
                '[class*="list-item"] a[href*="/job"]',
                'a[data-job-id]',
                # Broad fallback for any link in a list that looks like a job
                'li a[href*="/job/"]', 'li a[href*="/jobs/"]',
                'li a[href*="/position/"]', 'li a[href*="/opening/"]',
                'li a[href*="/vacancy/"]', 'li a[href*="/posting/"]',
                'tr a[href*="/job"]', 'article a[href*="/job"]',
            ]

            seen_urls = set()
            for selector in card_selectors:
                try:
                    elements = page.query_selector_all(selector)
                except Exception:
                    continue
                for el in elements:
                    try:
                        href = el.get_attribute("href") or ""
                        text = el.inner_text().strip()
                        if not text or len(text) < 3 or len(text) > 200:
                            continue
                        if re.match(r"^(back|home|search|sign|log|privacy|terms|cookie|save|share|menu|close|accept|reject)", text, re.I):
                            continue
                        full_url = urllib.parse.urljoin(page.url, href)
                        if full_url in seen_urls:
                            continue
                        seen_urls.add(full_url)

                        # Get the surrounding card text for context
                        parent_text = ""
                        try:
                            parent_text = el.evaluate(
                                "el => (el.closest('li, tr, article, div[class*=list-item], div[class*=card], div[class*=job]') || el.parentElement)?.innerText || ''"
                            )[:500]
                        except Exception:
                            pass

                        if not _is_pega_related(text):
                            continue

                        # Extract location from the card
                        location = "Location unconfirmed"
                        loc_match = re.search(
                            r"(Bengaluru|Bangalore|Hyderabad|Pune|Chennai|Mumbai|Delhi|Gurgaon|Gurugram|Noida|"
                            r"Kolkata|Kochi|India|Remote|London|New York|Singapore|Worldwide|United States|"
                            r"[A-Z][a-z]+,\s*[A-Z][a-z]+)",
                            parent_text
                        )
                        if loc_match:
                            location = loc_match.group(0)

                        jobs.append({
                            "title": text[:120],
                            "company": company_name,
                            "url": full_url,
                            "location": location,
                            "source": "Employer career page",
                            "checked_at": checked_at,
                        })
                    except Exception:
                        continue

        if not jobs:
            detail_jobs, detail_checked, detail_candidates = _follow_candidate_detail_urls(page, company_name, checked_at, timeout_ms)
            jobs.extend(detail_jobs)
            if detail_candidates:
                diagnostic["detail_links_found"] = detail_candidates
                diagnostic["detail_links_checked"] = detail_checked

        diagnostic["jobs_found"] = len(jobs)
        diagnostic["searched"] = searched
        diagnostic["method"] = "ld+json" if any(j.get("posted_at") for j in jobs) else "html_links" if jobs else "none"
        page.close()

        # Determine failure reason if no jobs found
        if not jobs:
            if not searched:
                log_entry["failure_reason"] = "no_search_executed"
            else:
                log_entry["failure_reason"] = "no_pega_results"

    except Exception as exc:
        diagnostic["error"] = f"Browser scrape failed: {str(exc)[:150]}"
        log_entry["failure_reason"] = "exception"
        log_entry["error"] = str(exc)[:150]
        logger.warning("Career scrape failed for %s: %s", company_name, exc)

    # Log every attempt
    elapsed = round(time.perf_counter() - start_time, 1)
    log_entry.update(jobs_found=len(jobs), elapsed_s=elapsed,
                     final_url=diagnostic.get("final_url", ""),
                     searched=diagnostic.get("searched", False),
                     method=diagnostic.get("method", "none"))
    _scrape_log.append(log_entry)

    return jobs, diagnostic


# ======== JOB BOARD SCRAPERS ========

# ======== LINKEDIN PLAYWRIGHT SCRAPER ========

def scrape_linkedin_target(target_name, target_keywords=None, location="India", timeout_ms=12000):
    """Scrape LinkedIn job search for a company using Playwright.

    Used as a retry for targets that got blocked via the HTTP API.
    Returns (jobs_list, diagnostic_dict).
    """
    start_time = time.perf_counter()
    keyword = (target_keywords or [target_name])[0]
    search_query = f"pega {keyword}"
    url = f"https://www.linkedin.com/jobs/search/?keywords={urllib.parse.quote(search_query)}&location={urllib.parse.quote(location)}"

    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    jobs = []
    diagnostic = {"url": url, "source": "LinkedIn (Playwright)", "checked_at": checked_at}
    log_entry = {"company": target_name, "url": url, "checked_at": checked_at,
                 "type": "linkedin_retry", "jobs_found": 0, "failure_reason": None}

    try:
        ctx = _get_browser()
        page = ctx.new_page()
        page.set_default_timeout(min(timeout_ms,5000))

        try:
            _navigate(page, url, timeout=timeout_ms, wait_until="domcontentloaded")
        except Exception as nav_err:
            diagnostic["error"] = f"Navigation failed: {str(nav_err)[:120]}"
            log_entry.update(failure_reason="navigation_failed", error=str(nav_err)[:120],
                             elapsed_s=round(time.perf_counter() - start_time, 1))
            _scrape_log.append(log_entry)
            page.close()
            return jobs, diagnostic

        page.wait_for_timeout(3000)

        # Extract job cards from LinkedIn's rendered HTML
        seen_urls = set()
        cards = page.query_selector_all(".base-card, .job-search-card")
        for card in cards:
            try:
                link = card.query_selector("a.base-card__full-link") or card.query_selector("a[href*='/jobs/view/']")
                if not link:
                    continue
                href = link.get_attribute("href") or ""
                if not href or "/jobs/view/" not in href:
                    continue
                # Clean tracking params
                clean_url = href.split("?")[0]
                if clean_url in seen_urls:
                    continue
                seen_urls.add(clean_url)

                title_el = card.query_selector(".base-search-card__title")
                company_el = card.query_selector(".base-search-card__subtitle")
                location_el = card.query_selector(".job-search-card__location")

                title = title_el.inner_text().strip() if title_el else ""
                company = company_el.inner_text().strip() if company_el else target_name
                job_location = location_el.inner_text().strip() if location_el else "Location unconfirmed"

                if not title:
                    continue

                # Only keep jobs where the title or card text mentions Pega
                card_text = card.inner_text() if card else ""
                if not _is_pega_related(title + " " + card_text):
                    continue

                jobs.append({
                    "title": title[:120],
                    "company": company,
                    "url": clean_url,
                    "location": job_location,
                    "source": "LinkedIn",
                    "checked_at": checked_at,
                    "status": "uncertain",
                    "verification_status": "candidate",
                })
            except Exception:
                continue

        diagnostic["jobs_found"] = len(jobs)
        diagnostic["final_url"] = page.url
        page.close()

        if not jobs:
            log_entry["failure_reason"] = "no_pega_results"

    except Exception as exc:
        diagnostic["error"] = f"LinkedIn Playwright scrape failed: {str(exc)[:150]}"
        log_entry.update(failure_reason="exception", error=str(exc)[:150])

    elapsed = round(time.perf_counter() - start_time, 1)
    log_entry.update(jobs_found=len(jobs), elapsed_s=elapsed)
    _scrape_log.append(log_entry)
    return jobs, diagnostic


def retry_blocked_linkedin(blocked_targets, stop_event=None):
    """Retry all blocked LinkedIn targets using Playwright.

    blocked_targets: list of dicts with target_id, name, keywords, location.
    Returns (all_jobs, all_diagnostics).
    """
    all_jobs = []
    all_diagnostics = []
    for i, target in enumerate(blocked_targets):
        if stop_event and stop_event.is_set():
            break
        name = target.get("name", "?")
        keywords = target.get("keywords", [name])
        location = target.get("location", "India")
        logger.info("LinkedIn retry %d/%d: %s", i + 1, len(blocked_targets), name)

        jobs, diag = scrape_linkedin_target(name, keywords, location)
        all_jobs.extend(jobs)
        all_diagnostics.append(diag)

        # Small delay between targets to be respectful
        time.sleep(1.0)

    return all_jobs, all_diagnostics


JOB_BOARDS = [
    {
        "name": "Indeed India",
        "url": "https://in.indeed.com/jobs?q=pega+developer&l=India",
        "link_selector": 'a[data-jk], h2.jobTitle a, a[class*="jcs-JobTitle"], a[href*="clk?jk="], h2 a[id*="jobTitle"]',
        "max_pages": 3,
    },
    {
        "name": "Indeed US",
        "url": "https://www.indeed.com/jobs?q=pega+developer",
        "link_selector": 'a[data-jk], h2.jobTitle a, a[class*="jcs-JobTitle"], a[href*="clk?jk="], h2 a[id*="jobTitle"]',
        "max_pages": 3,
    },
    {
        "name": "Shine.com",
        "url": "https://www.shine.com/job-search/pega-jobs",
        "link_selector": 'a[href*="/jobs/pega"], a[href*="/jobs/"][title]',
        "max_pages": 3,
    },
    {
        "name": "Dice",
        "url": "https://www.dice.com/jobs?q=pega&countryCode=US&radius=30&radiusUnit=mi&page=1&pageSize=20",
        "link_selector": 'a[href*="job-detail"], a[data-cy="card-title-link"]',
        "max_pages": 5,
    },
    {
        "name": "Glassdoor",
        "url": "https://www.glassdoor.co.in/Job/pega-developer-jobs-SRCH_KO0,14.htm",
        "link_selector": 'a[href*="job-listing"], a[data-test="job-link"]',
        "max_pages": 3,
    },
    {
        "name": "SimplyHired",
        "url": "https://www.simplyhired.co.in/search?q=pega+developer",
        "link_selector": 'a[href*="/job/"], h2 a, a[data-testid="job-title"]',
        "max_pages": 3,
    },
]


def _extract_location(text):
    """Pull a location from card text."""
    match = re.search(
        r"(Bengaluru|Bangalore|Hyderabad|Pune|Chennai|Mumbai|Delhi|Gurgaon|Gurugram|"
        r"Noida|Kolkata|Kochi|India|Remote|London|New York|Singapore|Dallas|"
        r"Jersey City|Vienna|United States|Worldwide|[A-Z][a-z]+,\s*[A-Z]{2}\b|"
        r"[A-Z][a-z]+,\s*[A-Z][a-z]+(?:,\s*India)?)",
        text
    )
    return match.group(0) if match else "Location unconfirmed"


def _extract_company(text):
    """Accept an isolated employer field, never infer it from a mixed card."""
    from normalizer import clean_company
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    # Mixed title, company, location and rating text cannot establish identity.
    if len(lines)!=1:return ''
    return clean_company(lines[0])  # source-specific selectors supply the field


def _is_valid_board_job(title, company):
    """Filter out garbage results from job boards."""
    t = (title or "").lower().strip()
    # Shine location pages: "Pega jobs in Delhi"
    if re.match(r"^pega\s+jobs?\s+in\s+", t):
        return False
    # Generic category pages
    if re.match(r"^pega\s+(jobs?|openings?|vacancies|careers?|salary|salaries)\s*$", t):
        return False
    # Indeed salary links
    if "salaries" in t and ("pega" in t or "developer" in t):
        return False
    # Nav/UI elements picked up as titles
    if re.match(r"^(date|sort|filter|page|next|prev|show|sign|log|menu|close|back|home|upload|post)", t):
        return False
    # Too short to be a real title
    if len(t) < 4:
        return False
    # Company is a board name or empty
    bad_companies = {"", "easily apply", "easy apply", "new", "active", "sponsored",
                     "indeed india", "indeed us", "shine.com", "dice", "glassdoor", "simplyhired",
                     "sort by:", "sort by", "?", "unknown"}
    if (company or "").lower().strip() in bad_companies:
        return False
    return True


def scrape_job_board(board, timeout_ms=12000):
    """Scrape a single job board for Pega listings."""
    start_time = time.perf_counter()
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    jobs = []
    diagnostic = {"url": board["url"], "source": board["name"], "checked_at": checked_at}
    log_entry = {"source": board["name"], "url": board["url"], "checked_at": checked_at,
                 "type": "job_board", "jobs_found": 0, "failure_reason": None}

    try:
        ctx = _get_browser()
        page = ctx.new_page()
        page.set_default_timeout(min(timeout_ms,5000))

        try:
            _navigate(page, board["url"], timeout=timeout_ms, wait_until="domcontentloaded")
        except Exception as nav_err:
            diagnostic["error"] = f"Navigation failed: {str(nav_err)[:120]}"
            log_entry.update(failure_reason="navigation_failed", error=str(nav_err)[:120],
                             elapsed_s=round(time.perf_counter() - start_time, 1))
            _scrape_log.append(log_entry)
            page.close()
            return jobs, diagnostic

        page.wait_for_timeout(3000)

        # Dismiss popups
        for sel in ['button:has-text("Accept")', 'button:has-text("Accept All")',
                    'button:has-text("Close")', 'button:has-text("OK")',
                    '[class*="cookie"] button', '[id*="consent"] button',
                    'button:has-text("No thanks")', 'button[aria-label="Close"]']:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click(force=True, timeout=2000)
                    page.wait_for_timeout(500)
                    break
            except Exception:
                continue

        page.wait_for_timeout(2000)
        from normalizer import jsonld_jobs, from_jobposting
        seen_urls = set()
        max_pages = board.get("max_pages", 3)

        for page_num in range(max_pages):
         if page_num > 0:
            # Try to go to next page: scroll down and click Next/pagination
            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1000)
                next_btn = page.query_selector('a[aria-label="Next"], a:has-text("Next"), button:has-text("Next"), a[data-testid="pagination-page-next"], li.next a, a.next')
                if next_btn and next_btn.is_visible():
                    next_btn.click(force=True, timeout=5000)
                    page.wait_for_timeout(3000)
                else:
                    break  # no more pages
            except Exception:
                break

         before_count = len(jobs)
         for posting in jsonld_jobs(page.content()):
            if not posting.get('url'):continue
            structured=from_jobposting(posting,page.url)
            if structured['url'] in seen_urls:continue
            if not _is_pega_related(str(structured.get('title',''))+' '+structured['description_text']):continue
            structured.update(source=board['name'],checked_at=checked_at)
            jobs.append(structured);seen_urls.add(structured['url'])
         selectors = [board["link_selector"]]

         for selector in selectors:
            try:
                elements = page.query_selector_all(selector)
            except Exception:
                continue
            for el in elements:
                try:
                    href = el.get_attribute("href") or ""
                    text = el.inner_text().strip()
                    if not text or len(text) < 4 or len(text) > 200:
                        continue
                    if re.match(r"^(back|home|search|sign|log|privacy|terms|cookie|save|share|menu|close|accept|salary|career/)", text, re.I):
                        continue
                    full_url = urllib.parse.urljoin(page.url, href)
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)

                    # Get parent card text first -- Pega may be in the card body, not the title
                    parent_text = ""
                    try:
                        parent_text = el.evaluate(
                            "el => (el.closest('li, tr, article, div[class*=card], div[class*=job], td[class*=result]') || el.parentElement)?.innerText || ''"
                        )[:500]
                    except Exception:
                        pass

                    # Check Pega relevance in title OR card body
                    if not _is_pega_related(text + " " + parent_text):
                        continue

                    from normalizer import clean_company
                    fields = el.evaluate("""el => {
                        const card = el.closest('li, article, .job_seen_beacon, .resultContent, [data-job-id], dhi-search-card') || el.parentElement;
                        const value = selector => card?.querySelector(selector)?.textContent?.trim() || '';
                        return {company: value('[data-testid="company-name"], [data-test="employer-name"], [data-testid="companyName"], .companyName, .company-name, [itemprop="hiringOrganization"]'),
                                location: value('[data-testid="text-location"], [data-testid="job-location"], .companyLocation, [itemprop="jobLocation"]')};
                    }""")
                    location = fields['location'] or 'Location unconfirmed'
                    company = clean_company(fields['company'],title=text) or 'Employer unconfirmed'

                    # Skip garbage: location pages, salary links, missing company
                    if not _is_valid_board_job(text, company):
                        continue

                    jobs.append({
                        "title": text[:120],
                        "company": company,
                        "url": full_url,
                        "location": location,
                        "source": board["name"],
                        "checked_at": checked_at,
                    })
                except Exception:
                    continue

         # Stop paginating if this page added nothing new
         if len(jobs) == before_count and page_num > 0:
            break

        diagnostic["jobs_found"] = len(jobs)
        if not jobs:
            log_entry["failure_reason"] = "no_pega_links"
        page.close()

    except Exception as exc:
        diagnostic["error"] = f"Board scrape failed: {str(exc)[:150]}"
        log_entry.update(failure_reason="exception", error=str(exc)[:150])
        logger.warning("Board scrape failed for %s: %s", board["name"], exc)

    elapsed = round(time.perf_counter() - start_time, 1)
    log_entry.update(jobs_found=len(jobs), elapsed_s=elapsed)
    _scrape_log.append(log_entry)

    return jobs, diagnostic


def scrape_all_job_boards(stop_event=None, on_result=None, on_start=None):
    """Scrape all configured job boards. Returns combined jobs + diagnostics."""
    all_jobs = []
    all_diagnostics = []
    for board in JOB_BOARDS:
        if stop_event is not None and stop_event.is_set():break
        if board['name'] in ('Indeed US','Dice'):continue
        if on_start is not None:on_start(board['name'])
        try:
            jobs, diag = scrape_job_board(board)
            if on_result is not None:on_result(board['name'],jobs,diag)
            all_jobs.extend(jobs)
            all_diagnostics.append(diag)
            logger.info("Board %s: %d pega jobs found", board["name"], len(jobs))
        except Exception as exc:
            all_diagnostics.append({"url": board["url"], "source": board["name"],
                                    "error": str(exc)[:120]})
    return all_jobs, all_diagnostics
