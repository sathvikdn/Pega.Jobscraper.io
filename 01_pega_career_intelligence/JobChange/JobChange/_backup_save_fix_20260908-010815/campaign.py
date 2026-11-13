"""Resumable public discovery across the complete company directory.

Results are discovery evidence, not confirmed offers or recruiter verification.
No accounts, application submission, outreach or hidden/private endpoints are used.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
import re
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from quality import canonical_url, employer_matches, broad_target, job_identity, normalized_name

BASE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = BASE / "research" / "preloaded_search.json"
ROLE_QUERY = '(Pega OR PRPC OR "workflow automation" OR BPM OR "integration engineer" OR "application engineer")'
COMPLETED = {"results", "no_matches", "blocked", "error"}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def target_id(category, name):
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return category + "-" + re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def load_targets(base_dir=None):
    base = Path(base_dir or BASE)
    path = base / "research" / "directory.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        records = data.get("records", data.get("targets", [])) if isinstance(data, dict) else data
        if records:
            return records
    tree = ast.parse((base / "pega_job_hunter.py").read_text(encoding="utf-8-sig"))
    groups = {"COMPANIES": "gcc", "CONSULTING_COMPANIES": "services", "REMOTE_GLOBAL_COMPANIES": "global"}
    records = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for name in node.targets:
                if isinstance(name, ast.Name) and name.id in groups:
                    category = groups[name.id]
                    for company in ast.literal_eval(node.value):
                        records.append({**company, "category": category, "location": company.get("location", "India"),
                                        "target_id": target_id(category, company["name"])})
    return records


class Node:
    def __init__(self, tag="root", attrs=()):
        self.tag, self.attrs, self.children = tag, {key: value or "" for key, value in attrs}, []

    def text(self, scripts=False):
        if self.tag in ("script", "style") and not scripts:
            return ""
        return " ".join(x.text(scripts) if isinstance(x, Node) else x for x in self.children).strip()

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()

    def has_class(self, *names):
        return bool(set(self.attrs.get("class", "").split()) & set(names))

    def first(self, predicate):
        return next((n for n in self.walk() if predicate(n)), None)


class Document(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, text):
        self.stack[-1].children.append(text)


def structured_jobs(root):
    jobs = []

    def collect(value):
        if isinstance(value, list):
            for child in value:
                collect(child)
        elif isinstance(value, dict):
            kinds = value.get("@type", [])
            if "JobPosting" in ([kinds] if isinstance(kinds, str) else kinds):
                jobs.append(value)
            if "@graph" in value:
                collect(value["@graph"])
            if "itemListElement" in value:
                for child in value["itemListElement"]:
                    collect(child.get("item", child) if isinstance(child, dict) else child)

    for node in root.walk():
        if node.tag == "script" and node.attrs.get("type", "").lower() == "application/ld+json":
            try:
                collect(json.loads(node.text(scripts=True)))
            except (ValueError, TypeError):
                continue
    return jobs


def role_description(html):
    root = Document(html).root
    postings = structured_jobs(root)
    if len(postings) == 1 and isinstance(postings[0].get("description"), str):
        return Document(postings[0]["description"]).root.text(), postings[0]
    if len(postings) > 1:
        return "", None
    element = root.first(lambda n: n.attrs.get("id") == "jobDescriptionText" or n.has_class(
        "show-more-less-html__markup", "description__text", "job-description", "jobsearch-jobDescriptionText"))
    return (element.text(), None) if element else ("", None)


def classify_track(title, description=""):
    title = title or ""
    # Exclude obvious nonengineering and industrial roles even if employer branding says Pega.
    if re.search(r"\b(sales|account executive|recruiter|legal|finance manager|PLC|SCADA|mechanical|electrical)\b", title, re.I):
        return None
    if description and re.search(r"\b(semiconductor|FPGA|ASIC|VLSI|microcontroller|RTL|PCB|oscilloscope|signal integrity|electronic design automation|radio frequency)\b", description, re.I) and not re.search(r"\b(Pega|PRPC|OpenSpan)\b", title + " " + description, re.I):
        return None
    if re.search(r"\b(pega|prpc|cssa|clsa|openspan)\b", title, re.I):
        return "pega"
    if re.search(r"\b(pega|prpc|openspan)\b", description, re.I):
        return "pega"
    adjacent = r"\b(workflow|BPM|business process (?:management|automation)|process automation|intelligent automation|integration (?:engineer|developer|specialist)|application engineer|RPA developer)\b"
    if re.search(adjacent, title, re.I):
        if description and re.search(r"\bapplication engineer\b", title, re.I) and not re.search(r"\b(workflow automation|business process management|Pega|PRPC|BPM|Kafka|REST(?:ful)? APIs?|SOAP|enterprise integration)\b", description, re.I):
            return None
        return "adjacent"
    # A generic software title must have actual implementation requirements in its JD.
    if re.search(r"\b(engineer|developer|architect|application|automation)\b", title, re.I) and re.search(
            r"\b(workflow automation|business process management|Pega|PRPC|BPM|Kafka|REST(?:ful)? APIs?|SOAP|enterprise integration)\b", description, re.I):
        return "adjacent"
    return None


def salary_evidence(text):
    """Read explicit lakh-per-year INR figures only; never infer CTC or exchange rates."""
    pattern = re.compile(r"(?P<prefix>CTC\s*[:\-]?\s*)?(?P<currency>INR|Rs\.?|₹)?\s*(?P<lo>\d+(?:\.\d+)?)\s*(?:[-–—]|to)?\s*(?P<hi>\d+(?:\.\d+)?)?\s*(?P<unit>LPA|lakhs?\s+(?:per\s+annum|per\s+year|p\.?a\.?))\b", re.I)
    for match in pattern.finditer(text or ""):
        start, end = match.span()
        nearby = text[max(0, start - 35):min(len(text), end + 35)]
        if re.search(r"\b(?:USD|SGD|AED|GBP|AUD|EUR)\b|\$|€|£", nearby):
            continue
        if not match.group("currency") and not re.search(r"\b(CTC|salary|compensation|package|pay)\b", nearby, re.I):
            continue
        low = float(match.group("lo")) * 100000
        high = float(match.group("hi")) * 100000 if match.group("hi") else low
        if not (0 < low <= high <= 100000000):
            continue
        # CTC elsewhere in the paragraph must not relabel a nearby fixed-pay figure.
        explicitly_ctc = bool(match.group("prefix")) or bool(re.match(r"\s*(?:CTC|total compensation|cost to company)\b", text[end:], re.I))
        basis = "total_compensation" if explicitly_ctc else "fixed" if re.search(r"\bfixed\b|base salary", nearby, re.I) else "reported_salary"
        return {"amount_min": round(low), "amount_max": round(high), "currency": "INR", "period": "annual", "basis": basis,
                "source_text": nearby.strip()}
    return None


def pay_bucket(salary):
    if not salary or salary.get("currency") != "INR" or salary.get("period") != "annual" or salary.get("basis") != "total_compensation":
        return "unknown"
    if salary["amount_min"] >= 2000000:
        return "at_least_20"
    if salary["amount_max"] >= 2000000:
        return "overlaps_20"
    return "below_20"


def remote_eligibility(location, description=""):
    text = f"{location} {description}"
    foreign = r"(?:United States|USA|US\b|United Kingdom|UK\b|Australia|Canada|Germany|Netherlands|Singapore|Switzerland|France|Japan|Brazil|Mexico)"
    if re.search(r"(?:must|required to)\s+(?:currently\s+)?(?:reside|live|be (?:based|located))\s+in\s+(?:the\s+)?" + foreign, description, re.I) or re.search(foreign + r"[ -]*only", text, re.I):
        return "country_restricted"
    if (re.search(r"remote", location, re.I) and re.search(r"worldwide", location, re.I)) or re.search(r"(?:role|position|job)\s*(?:is|:)?\s*(?:fully )?remote\s*(?:[-,:]\s*)?worldwide|(?:applicants|candidates) (?:from|based) anywhere (?:in the world|worldwide)", description, re.I):
        return "worldwide"
    if (re.search(r"remote", location, re.I) and re.search(r"\bindia\b", location, re.I)) or re.search(r"work (?:remotely|remote) (?:from|within|in) (?:anywhere in )?India|(?:role|position|job)\s*(?:is|:)?\s*(?:fully )?remote\s*(?:[-,:]\s*)?India", description, re.I):
        return "india_remote"
    if re.search(r"must (?:reside|be (?:based|located)) in|(?:US|UK|USA|United States|United Kingdom|Australia|Canada)[ -]*only", text, re.I):
        return "country_restricted"
    if re.search(r"remote", text, re.I) and re.search(r"\b(United States|USA|United Kingdom|Australia|Canada|Germany|Netherlands)\b", location, re.I):
        return "country_restricted"
    return "unknown"


def make_job(title, company, location, url, source, checked_at, description="", posted_at=None):
    url = canonical_url(url)
    track = classify_track(title, description)
    if not url or not track:
        return None
    years = re.search(r"\b(\d{1,2})\s*(?:[-–]\s*(\d{1,2})|\+)??\s*years?\s+(?:of\s+)?(?:relevant\s+|professional\s+|hands.on\s+)?experience", description, re.I)
    experience_min = int(years.group(1)) if years else None
    if experience_min is not None and experience_min > 8:
        return None
    if re.search(r"\b(vice president|VP|director|head of|principal)\b", title, re.I):
        return None
    salary = salary_evidence(description)
    unknown = ["Recruiter acceptance and current application status", "Joining timeline"]
    if not description:
        unknown += ["Full role requirements not fetched", "Experience threshold", "Published compensation"]
    elif experience_min is None:
        unknown.append("Explicit experience threshold not identified")
    if not salary:
        unknown.append("No explicit annual INR compensation extracted")
    reasons = ["Pega/PRPC experience aligns with the known profile."] if track == "pega" else ["Adjacent workflow, BPM, integration or application-engineering work may use the existing enterprise automation experience.", "Match is provisional; review actual stack and coding depth before applying."]
    if description and re.search(r"Kafka|REST|SOAP|SQL", description, re.I):
        reasons.append("The role description includes an integration or database skill from the known profile.")
    if experience_min and experience_min > 4:
        unknown.append(f"Stated minimum {experience_min} years exceeds the known four years")
    return {"id": job_identity(title, company, url), "company": company, "title": title, "location": location or "Not stated", "url": url,
            "source": source, "checked_at": checked_at, "posted_at": posted_at, "track": track, "fit": "stretch" if experience_min and experience_min > 4 else "possible",
            "fit_reasons": reasons, "requirements_unknown": list(dict.fromkeys(unknown)), "experience_min": experience_min,
            "salary": salary, "pay_bucket": pay_bucket(salary), "remote_eligibility": remote_eligibility(location or "", description),
            "status": "uncertain", "verification_status": "candidate", "search_presence": "found", "last_seen_at": checked_at,
            "evidence_scope": "role_description" if description else "public_job_card"}


def parse_cards(html, target):
    root = Document(html).root
    cards, seen, card_count = [], set(), 0
    for node in root.walk():
        if not (node.tag == "li" or node.has_class("base-card", "job-search-card")):
            continue
        title = node.first(lambda n: n.has_class("base-search-card__title", "result-card__title"))
        company = node.first(lambda n: n.has_class("base-search-card__subtitle", "result-card__subtitle"))
        link = node.first(lambda n: n.tag == "a" and n.has_class("base-card__full-link"))
        if not (title and company and link):
            continue
        url = canonical_url(link.attrs.get("href", ""))
        if not url or url in seen:
            continue
        seen.add(url)
        card_count += 1
        if not employer_matches(company.text(), target):
            continue
        location = node.first(lambda n: n.has_class("job-search-card__location"))
        posted = node.first(lambda n: n.tag == "time")
        cards.append({"title": title.text(), "company": company.text(), "location": location.text() if location else "Not stated", "url": url,
                      "posted_at": posted.attrs.get("datetime") if posted else None})
    return cards, card_count


class Cancelled(Exception):
    pass


class RateLimiter:
    def __init__(self, spacing=2.5):
        self.spacing, self.next_at, self.lock = spacing, {}, threading.Lock()

    def wait(self, url, stop_event):
        host = urllib.parse.urlparse(url).hostname or ""
        with self.lock:
            scheduled = max(time.monotonic(), self.next_at.get(host, 0))
            self.next_at[host] = scheduled + self.spacing
        while time.monotonic() < scheduled:
            if stop_event.wait(min(0.25, max(0, scheduled - time.monotonic()))):
                raise Cancelled()
        if stop_event.is_set():
            raise Cancelled()


class PublicClient:
    def __init__(self, stop_event=None, spacing=2.5, timeout=10):
        self.stop_event, self.limiter, self.timeout = stop_event or threading.Event(), RateLimiter(spacing), timeout

    def get(self, url):
        self.limiter.wait(url, self.stop_event)
        checked = now()
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                html = response.read(3_000_000).decode("utf-8", errors="replace")
                return html, {"url": url, "final_url": response.url, "http_status": response.status, "checked_at": checked}
        except urllib.error.HTTPError as error:
            return None, {"url": url, "http_status": error.code, "checked_at": checked, "error": "HTTP request rejected"}
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            return None, {"url": url, "http_status": None, "checked_at": checked, "error": str(error)[:220]}


def query_url(target, expanded=True):
    keyword = target.get("keywords", [target["name"]])[0]
    keywords = ROLE_QUERY if broad_target(target) else f'("{keyword}") AND {ROLE_QUERY}' if expanded else f"pega {keyword}"
    return "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?" + urllib.parse.urlencode({"keywords": keywords, "location": target.get("location", "India"), "start": 0})


def employer_structured(html, target, page_url, checked_at):
    result = []
    for raw in structured_jobs(Document(html).root):
        employer = raw.get("hiringOrganization", {})
        employer = employer.get("name", "") if isinstance(employer, dict) else ""
        if not employer_matches(employer, target):
            continue
        locations = raw.get("jobLocation", [])
        locations = locations if isinstance(locations, list) else [locations]
        labels = []
        for item in locations:
            address = item.get("address", {}) if isinstance(item, dict) else {}
            if isinstance(address, dict):
                labels.append(", ".join(str(address[key]) for key in ("addressLocality", "addressRegion", "addressCountry") if address.get(key)))
        location = "; ".join(labels)
        if raw.get("jobLocationType") == "TELECOMMUTE":
            location += "; Remote"
        description = Document(raw.get("description", "")).root.text()
        job = make_job(raw.get("title", ""), employer, location, raw.get("url") or page_url, "Employer career page", checked_at, description, raw.get("datePosted"))
        if job:
            job["closing_at"] = raw.get("validThrough")
            result.append(job)
    return result


def check_target(target, client):
    checked_at, url = now(), query_url(target)
    record = {"target_id": target["target_id"], "name": target["name"], "category": target.get("category", "gcc"), "location": target.get("location", "India"),
              "status": "pending", "checked_at": None, "source_url": url, "diagnostics": [], "jobs": []}
    html, diagnostic = client.get(url)
    record["diagnostics"].append(diagnostic)
    record["checked_at"] = checked_at
    if html is not None:
        try:
            cards, raw_count = parse_cards(html, target)
        except Exception as error:
            diagnostic["error"] = "Listing parse failed: " + str(error)[:180]
            record["status"] = "error"
            return record
        diagnostic.update({"raw_cards": raw_count, "employer_matches": len(cards)})
        # Some public search responses interpret the Boolean expansion loosely.
        # Try a simpler company-specific query before reporting zero matches.
        if not cards and not broad_target(target):
            fallback_url = query_url(target, expanded=False)
            fallback_html, fallback_audit = client.get(fallback_url)
            fallback_audit["query_scope"] = "Simpler Pega plus employer fallback after zero employer matches"
            record["diagnostics"].append(fallback_audit)
            if fallback_html is not None:
                try:
                    cards, raw_count = parse_cards(fallback_html, target)
                except Exception as error:
                    fallback_audit["error"] = "Listing parse failed: " + str(error)[:180]
                else:
                    fallback_audit.update({"raw_cards": raw_count, "employer_matches": len(cards)})
                    html, diagnostic = fallback_html, fallback_audit
        if raw_count or len(html.strip()) < 40 or re.search(r"no (?:matching )?jobs found|no results found", html, re.I):
            record["status"] = "no_matches"
        else:
            record["status"] = "blocked"
            diagnostic["error"] = "No recognizable job cards or empty-result marker; page may be blocked or changed"
        generic = []
        for card in cards:
            job = make_job(**card, source="LinkedIn public jobs", checked_at=checked_at)
            if job:
                record["jobs"].append(job)
            elif re.search(r"engineer|developer|architect|automation", card["title"], re.I):
                generic.append(card)
        # At most one additional request per target, only for the correctly listed employer.
        # Direct Pega/adjacent cards already carry an honest unknown-requirements flag.
        for card in generic[:1]:
            number = card["url"].rstrip("/").rsplit("/", 1)[-1]
            jd_url = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/" + number if number.isdigit() else card["url"]
            jd_html, jd_audit = client.get(jd_url)
            record["diagnostics"].append(jd_audit)
            if jd_html:
                description, _ = role_description(jd_html)
                if description:
                    job = make_job(**card, source="LinkedIn public jobs", checked_at=checked_at, description=description)
                    if job:
                        record["jobs"].append(job)
                else:
                    jd_audit["error"] = "Supported individual role description was not present"
        if len(generic) > 1:
            diagnostic["generic_jds_not_checked"] = len(generic) - 1
    else:
        record["status"] = "blocked" if diagnostic.get("http_status") in (401, 403, 429, 999) else "error"
    # If the public board was unavailable, also attempt the configured employer URL.
    career = canonical_url(target.get("career_url", ""))
    if record["status"] in ("blocked", "error") and career:
        career_html, career_audit = client.get(career)
        record["diagnostics"].append(career_audit)
        if career_html:
            direct = employer_structured(career_html, target, career_audit.get("final_url", career), checked_at)
            record["jobs"].extend(direct)
            if not direct:
                career_audit["note"] = "No matching structured JobPosting extracted; employer site is not a complete vacancy inventory"
    if record["jobs"]:
        record["status"] = "results"
    record["jobs"] = list({job["id"]: job for job in record["jobs"]}.values())
    record["partial"] = any(d.get("error") or d.get("generic_jds_not_checked") for d in record["diagnostics"])
    return record


def coverage(records):
    result = {"total": len(records), "checked": 0, "pending": 0, "with_results": 0, "blocked": 0, "no_matches": 0, "errors": 0, "jobs": 0}
    for record in records:
        status = record.get("status", "pending")
        result["checked" if status in COMPLETED else "pending"] += 1
        key = {"results": "with_results", "error": "errors"}.get(status, status)
        if key in ("with_results", "blocked", "no_matches", "errors"):
            result[key] += 1
        result["jobs"] += len(record.get("jobs", []))
    return result


def retain_previous_jobs(record, previous):
    """A failed/empty query is not evidence that a previously discovered role closed."""
    current = {canonical_url(job.get("url", "")) or job["id"]: job for job in record.get("jobs", [])}
    record["fresh_job_count"] = len(current)
    retained = 0
    for old in previous.get("jobs", []):
        key = canonical_url(old.get("url", "")) or old["id"]
        if key in current:
            continue
        job = copy.deepcopy(old)
        job.update(status="uncertain", verification_status="candidate", search_presence="not_rediscovered",
                   last_seen_at=old.get("last_seen_at") or old.get("checked_at"), latest_search_at=record.get("checked_at"))
        note = "Not rediscovered by latest query; manual check needed"
        if record.get("status") in ("blocked", "error"):
            note += "; latest search was blocked or failed"
        job["requirements_unknown"] = list(dict.fromkeys(job.get("requirements_unknown", []) + [note]))
        current[key] = job
        retained += 1
    record["jobs"] = list(current.values())
    record["retained_job_count"] = retained
    return record


def load_campaign(output_path=None):
    path = Path(output_path or DEFAULT_OUTPUT)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8-sig"))
    return {"schema_version": 1, "status": "not_started", "targets": [], "coverage": coverage([])}


def save_campaign(data, output_path):
    data["updated_at"] = now()
    data["coverage"] = coverage(data["targets"])
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


@contextmanager
def campaign_lock(output_path):
    lock_path = Path(output_path).with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        # Reading the locked byte can itself fail on Windows before we can emit
        # the useful already-running error. File metadata is safe to inspect.
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise RuntimeError("A discovery campaign is already running for this output") from error
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def campaign_is_locked(output_path=None):
    """Probe the operating-system lock, so stale JSON cannot disable Resume."""
    try:
        with campaign_lock(output_path or DEFAULT_OUTPUT):
            return False
    except (RuntimeError, BlockingIOError):
        return True


def detail_url(job):
    url = canonical_url(job.get("url", ""))
    match = re.fullmatch(r"https://www\.linkedin\.com/jobs/view/(\d+)", url)
    return "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/" + match.group(1) if match else url


def experience_signals(description):
    """Keep explicit experience wording; a title alone never establishes years."""
    pattern = re.compile(r"\b(?:minimum(?:\s+of)?\s+|at\s+least\s+)?(\d{1,2})\s*(?:[-–—]|to)?\s*(\d{1,2})?\s*\+?\s*(?:years?|yrs?)['’]?\s*(?:of\s+)?(?:[a-z][a-z /,-]*?\s+)?experience\b", re.I)
    found = []
    for match in pattern.finditer(description or ""):
        if len(match.group(0)) > 170:
            continue
        low, high = int(match.group(1)), int(match.group(2) or match.group(1))
        if not 0 <= low <= high <= 35:
            continue
        lead = description[max(0, match.start() - 50):match.start()]
        if re.search(r"company|founded|established|our\s+business|organization", lead, re.I):
            continue
        found.append({"minimum_years": low, "maximum_years": high, "source_text": match.group(0)[:150]})
    return found[:6]


SKILL_PATTERNS = {
    "Pega": r"\bPega\b|\bPRPC\b", "CSSA": r"\bCSSA\b", "CLSA": r"\bCLSA\b|certified lead system architect",
    "Constellation": r"\bConstellation\b", "Pega CDH": r"\bCDH\b|customer decision hub", "Kafka": r"\bKafka\b",
    "REST APIs": r"\bREST(?:ful)?\b", "SOAP": r"\bSOAP\b", "SQL": r"\bSQL\b", "Java": r"\bJava\b",
    "Spring": r"\bSpring(?: Boot)?\b", "JavaScript": r"\bJavaScript\b", "Python": r"\bPython\b",
    "AWS": r"\bAWS\b|Amazon Web Services", "Azure": r"\bAzure\b", "Kubernetes": r"\bKubernetes\b|\bK8s\b",
    "Camunda": r"\bCamunda\b", "Appian": r"\bAppian\b", "ServiceNow": r"\bServiceNow\b",
    "UiPath": r"\bUiPath\b", "Boomi": r"\bBoomi\b", "MuleSoft": r"\bMuleSoft\b",
    "Ruby": r"\bRuby\b", "Go": r"\bGolang\b", "C++": r"\bC\+\+", "SmartDX / Thunderhead": r"\bSmartDX\b|\bThunderhead\b",
}


def enrich_job(job, client):
    """Inspect one public JD; preserve a candidate when availability cannot be proven."""
    updated = copy.deepcopy(job)
    url = detail_url(job)
    html, diagnostic = client.get(url)
    updated["job_detail_checked_at"] = diagnostic.get("checked_at", now())
    updated["job_detail_diagnostic"] = diagnostic
    updated["job_detail_status"] = "unavailable"
    if html is None:
        updated["requirements_unknown"] = list(dict.fromkeys(updated.get("requirements_unknown", []) + ["Individual role page could not be read; this does not establish closure"]))
        return updated
    final_url = diagnostic.get("final_url", url)
    if canonical_url(final_url) not in {canonical_url(url), canonical_url(job["url"])}:
        updated["job_detail_status"] = "identity_unconfirmed"
        diagnostic["error"] = "Role URL redirected to a different address; saved candidate retained"
        return updated
    description, structured = role_description(html)
    if not description:
        updated["job_detail_status"] = "description_missing"
        diagnostic["error"] = "No supported individual role-description section found"
        return updated
    root = Document(html).root
    if structured:
        title = structured.get("title", "")
        employer = structured.get("hiringOrganization", {})
        employer = employer.get("name", "") if isinstance(employer, dict) else ""
    else:
        title_node = root.first(lambda n: n.has_class("top-card-layout__title", "topcard__title"))
        employer_node = root.first(lambda n: n.has_class("topcard__org-name-link", "topcard__flavor--black-link"))
        title, employer = title_node.text() if title_node else "", employer_node.text() if employer_node else ""
    if title and normalized_name(title) != normalized_name(job["title"]):
        updated["job_detail_status"] = "identity_unconfirmed"
        diagnostic["error"] = "Returned role title differs from the saved listing"
        return updated
    if employer and not employer_matches(employer, {"name": job["company"]}):
        updated["job_detail_status"] = "identity_unconfirmed"
        diagnostic["error"] = "Returned employer differs from the saved listing"
        return updated
    updated["job_detail_status"] = "read"
    updated["evidence_scope"] = "role_description"
    updated["description_identity"] = "title_and_endpoint" if title else "exact_endpoint_only"
    updated["skills"] = [label for label, pattern in SKILL_PATTERNS.items() if re.search(pattern, description, re.I)]
    signals = experience_signals(description)
    updated["experience_evidence"] = signals
    if signals:
        # A secondary skill can have fewer years than the overall role: do not use
        # the smallest extracted number to claim the whole vacancy is a four-year fit.
        updated["experience_min"] = max(item["minimum_years"] for item in signals)
    salary = salary_evidence(description)
    # A changed or incomplete description cannot erase a previously sourced
    # salary figure. Preserve its original provenance until an explicit update.
    if salary is not None:
        salary.update(source_url=job["url"], evidence_checked_at=updated["job_detail_checked_at"])
        updated["salary"] = salary
    elif updated.get("salary"):
        updated["salary"].setdefault("source_url", job["url"])
        updated["salary"].setdefault("evidence_checked_at", job.get("checked_at"))
        updated["salary"]["latest_presence"] = "not_rediscovered"
    updated["pay_bucket"] = pay_bucket(updated.get("salary"))
    updated["remote_eligibility"] = remote_eligibility(job.get("location", ""), description)
    unknown = [x for x in updated.get("requirements_unknown", []) if x not in (
        "Full role requirements not fetched", "Experience threshold", "Published compensation", "Explicit experience threshold not identified", "No explicit annual INR compensation extracted") and not x.startswith("Stated minimum ")]
    if not signals:
        unknown.append("Explicit experience threshold not identified")
    elif updated["experience_min"] > 4:
        updated["fit"] = "stretch"
        unknown.append(f"Experience wording includes {updated['experience_min']}+ years; exceeds the known four years. Check whether mandatory or preferred.")
    if not salary:
        unknown.append("Previous salary evidence retained; latest description did not publish an annual INR figure. Confirm the budget." if updated.get("salary") else "No explicit annual INR compensation extracted")
    if "CLSA" in updated["skills"]:
        unknown.append("CLSA appears in the description; current known certification is CSSA. Check whether CLSA is required.")
    if updated["remote_eligibility"] == "country_restricted":
        unknown.append("Country or residency restrictions require review; not established as India-eligible remote work")
    new_track = classify_track(job["title"], description)
    if new_track:
        updated["track"] = new_track
        updated["relevance"] = new_track
    else:
        updated["relevance"] = "unrelated"
        updated["fit"] = "stretch"
        unknown.append("Detailed description did not establish the intended Pega or enterprise workflow/integration scope; excluded from relevant leads")
    updated["requirements_unknown"] = list(dict.fromkeys(unknown))
    updated["summary"] = "Individual public role description read. " + ("Technologies mentioned: " + ", ".join(updated["skills"]) + ". " if updated["skills"] else "") + "Skill mentions are evidence of role content, not proof every item is mandatory. Application availability still needs confirmation."
    updated["evidence"] = [{"url": job["url"], "title": job["company"] + " — " + job["title"], "source_type": "Public individual job description", "checked_at": updated["job_detail_checked_at"], "excerpt": updated["summary"], "status": "candidate"}]
    if structured and structured.get("validThrough"):
        updated["closing_at"] = structured["validThrough"]
    # Remain a candidate: reading a public description does not prove an employer
    # is still accepting applications or would accept this applicant's experience.
    updated["verification_status"] = "candidate"
    return updated


def enrich_campaign(output_path=None, progress=None, stop_event=None, force=False, workers=6):
    """Resumable, one-request-per-distinct-role evidence pass after target discovery."""
    path = Path(output_path or DEFAULT_OUTPUT)
    stop_event = stop_event or threading.Event()
    with campaign_lock(path):
        document = load_campaign(path)
        jobs_by_url = {}
        for target in document.get("targets", []):
            for job in target.get("jobs", []):
                jobs_by_url.setdefault(canonical_url(job["url"]), []).append(job)
        detail = {"status": "running", "started_at": now(), "total": len(jobs_by_url), "checked": 0, "read": 0, "unavailable": 0, "identity_unconfirmed": 0, "description_missing": 0, "cached": 0}
        document["detail_enrichment"] = detail
        document.setdefault("query_policy", {}).update(pagination="First public result page per expanded query and optional simpler fallback; not an exhaustive vacancy inventory", detail_policy="One public description check per distinct retained role; preserves candidates when unavailable")
        save_campaign(document, path)
        client = PublicClient(stop_event)

        def inspect(prior):
            if stop_event.is_set():
                raise Cancelled()
            if prior.get("job_detail_status") and not force:
                return copy.deepcopy(prior)
            try:
                return enrich_job(prior, client)
            except Cancelled:
                raise
            except Exception as error:
                enriched = copy.deepcopy(prior)
                enriched.update(job_detail_status="unavailable", job_detail_checked_at=now(), job_detail_diagnostic={"url": detail_url(prior), "error": "Detail check failed: " + str(error)[:180]})
                return enriched

        with ThreadPoolExecutor(max_workers=max(1, min(6, workers))) as executor:
            pending = {executor.submit(inspect, copy.deepcopy(copies[0])): (copies, bool(copies[0].get("job_detail_status")) and not force) for copies in jobs_by_url.values()}
            for future in as_completed(pending):
                try:
                    enriched = future.result()
                except Cancelled:
                    continue
                copies, cached = pending[future]
                detail["cached"] += int(cached)
                for saved in copies:
                    saved.clear()
                    saved.update(copy.deepcopy(enriched))
                outcome = enriched.get("job_detail_status", "unavailable")
                detail["checked"] += 1
                detail[outcome if outcome in detail else "unavailable"] += 1
                save_campaign(document, path)
                if progress:
                    progress({"phase": "job_details", "detail_enrichment": detail, "current_company": enriched.get("company")})
        detail["status"] = "cancelled" if stop_event.is_set() else "complete"
        detail["completed_at"] = now() if detail["status"] == "complete" else None
        save_campaign(document, path)
        return document


def run_campaign(target_ids=None, force=False, progress=None, workers=6, output_path=None, data=None, stop_event=None):
    """Run/resume checks; progress receives one dict after each atomic checkpoint.

    data optionally supplies an in-memory target list for offline tests. All directory
    targets are included by default, including new records added during the run.
    A checked blocked target is a completed attempt, not a successful vacancy search.
    """
    output_path = Path(output_path or DEFAULT_OUTPUT)
    stop_event = stop_event or threading.Event()
    with campaign_lock(output_path):
        catalog = list(data) if data is not None else load_targets()
        wanted = set(target_ids) if target_ids is not None else None
        if wanted is not None and not wanted.issubset({t["target_id"] for t in catalog}):
            raise ValueError("An unknown target_id was requested")
        previous = load_campaign(output_path)
        rows = {t["target_id"]: t for t in previous.get("targets", [])}
        document = {"schema_version": 1, "started_at": now() if force else previous.get("started_at", now()), "status": "running",
                    "threshold_annual_inr": 2000000, "query_policy": {"roles": ROLE_QUERY, "source": "Public LinkedIn guest job search; employer structured fallback if blocked", "per_domain_spacing_seconds": 2.5, "request_timeout_seconds": 10,
                    "generic_jd_limit_per_target": 1, "pagination": "First public result page per expanded query and optional simpler fallback; not an exhaustive vacancy inventory", "detail_policy": "Optional resumable public description check for every distinct retained role", "salary_policy": "Only explicit annual INR CTC establishes the 20 lakh threshold; fixed or unspecified salary remains unknown", "no_matches_meaning": "This query returned no retained profile/employer matches; not proof the employer has no openings"}, "targets": []}

        def enroll(targets, reset=False):
            for target in targets:
                key = target["target_id"]
                if reset or key not in rows:
                    prior_jobs = copy.deepcopy(rows.get(key, {}).get("jobs", []))
                    rows[key] = {"target_id": key, "name": target["name"], "category": target.get("category", "gcc"), "location": target.get("location", "India"), "status": "pending", "checked_at": None, "source_url": query_url(target), "diagnostics": [], "jobs": prior_jobs}

        enroll(catalog)
        if force:
            enroll([t for t in catalog if wanted is None or t["target_id"] in wanted], reset=True)
        client = PublicClient(stop_event)
        while True:
            active_ids = {t["target_id"] for t in catalog}
            document["targets"] = [rows[t["target_id"]] for t in catalog]
            save_campaign(document, output_path)
            pending = [t for t in catalog if (wanted is None or t["target_id"] in wanted) and rows[t["target_id"]].get("status") not in COMPLETED]
            if not pending or stop_event.is_set():
                break
            with ThreadPoolExecutor(max_workers=max(1, min(6, workers))) as executor:
                future_targets = {executor.submit(check_target, target, client): target for target in pending}
                for future in as_completed(future_targets):
                    target = future_targets[future]
                    try:
                        record = future.result()
                    except Cancelled:
                        continue
                    except Exception as error:
                        record = {**rows[target["target_id"]], "status": "error", "checked_at": now(), "diagnostics": [{"url": query_url(target), "error": "Check failed: " + str(error)[:220]}], "jobs": []}
                    rows[target["target_id"]] = retain_previous_jobs(record, rows[target["target_id"]])
                    document["targets"] = [rows[t["target_id"]] for t in catalog]
                    save_campaign(document, output_path)
                    if progress:
                        progress({"coverage": document["coverage"], "current_target": target["name"], "current_company": target["name"], "target_id": target["target_id"], "target_status": record["status"], "status": "running"})
            if data is None and wanted is None and not stop_event.is_set():
                latest = load_targets()
                additions = [target for target in latest if target["target_id"] not in active_ids]
                if additions:
                    catalog = latest
                    enroll(additions)
                    continue
            break
        document["status"] = "cancelled" if stop_event.is_set() else "complete" if coverage(document["targets"])["pending"] == 0 else "partial"
        document["completed_at"] = now() if document["status"] == "complete" else None
        save_campaign(document, output_path)
        if progress:
            progress({"coverage": document["coverage"], "current_target": None, "status": document["status"]})
        return document


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Recheck all targets instead of resuming completed attempts")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--enrich", action="store_true", help="Read individual public descriptions for saved role candidates after discovery")
    args = parser.parse_args()
    if args.enrich:
        enrich_campaign(force=args.force, output_path=args.output, progress=lambda event: print(json.dumps(event), flush=True))
    else:
        run_campaign(force=args.force, output_path=args.output, progress=lambda event: print(json.dumps(event), flush=True))
