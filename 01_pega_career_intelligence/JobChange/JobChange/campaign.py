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
import random
import re
import threading
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

from quality import canonical_url, employer_matches, broad_target, job_identity, normalized_name

BASE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = BASE / "research" / "preloaded_search.json"
ROLE_QUERY = '(Pega OR PRPC)'
COMPLETED = {"results", "no_matches", "blocked", "error"}
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]
def _random_ua():
    return USER_AGENT
USER_AGENT = USER_AGENTS[0]  # backward compat for any external references


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


def _description_excluded(node):
    """Exclude navigation and unrelated recommendation/branding panels from a JD."""
    if node.tag in ("script", "style", "noscript", "nav", "aside", "footer", "header", "button"):
        return True
    marker = " ".join((node.attrs.get("class", ""), node.attrs.get("id", "")))
    return bool(re.search(r"(?:similar|related|recommended|suggested|other)[-_ ]jobs|jobs[-_ ](?:similar|related|recommended|suggested)|company[-_ ](?:overview|branding)|employer[-_ ]branding", marker, re.I))


def readable_description(node):
    """Plain text with paragraphs, line breaks and list items kept for reading."""
    block_tags = {"p", "div", "section", "article", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "table", "tr", "blockquote", "pre"}
    def render(value):
        if not isinstance(value, Node):
            # HTML whitespace between inline elements is not a paragraph break.
            return re.sub(r"\s+", " ", value)
        if _description_excluded(value):
            return ""
        if value.tag == "br":
            return "\n"
        body = "".join(render(child) for child in value.children)
        if value.tag == "li":
            return "\n- " + body.strip() + "\n"
        if value.tag in block_tags:
            return "\n\n" + body.strip() + "\n\n"
        return body
    rendered = render(node).replace("\xa0", " ")
    rendered = re.sub(r"[ \t]+", " ", rendered)
    rendered = re.sub(r" *\n *", "\n", rendered)
    return re.sub(r"\n{3,}", "\n\n", rendered).strip()


def role_description(html):
    root = Document(html).root
    postings = structured_jobs(root)
    if len(postings) == 1 and isinstance(postings[0].get("description"), str):
        raw = postings[0]["description"]
        # JSON-LD can carry plain paragraphs as well as HTML markup.
        text = readable_description(Document(raw).root) if re.search(r"<[a-z][^>]*>", raw, re.I) else raw.strip()
        return text, postings[0]
    if len(postings) > 1:
        return "", None
    candidates = []
    def collect(node):
        if _description_excluded(node):
            return
        if node.attrs.get("id") == "jobDescriptionText" or node.has_class(
                "show-more-less-html__markup", "description__text", "job-description", "jobsearch-jobDescriptionText"):
            # A supported outer description may contain a more precise inner
            # markup container. Prefer that text, never the whole page.
            def precise_markup(item):
                if _description_excluded(item):
                    return None
                if item.has_class("show-more-less-html__markup"):
                    return item
                for child in item.children:
                    if isinstance(child, Node):
                        found = precise_markup(child)
                        if found:
                            return found
                return None
            candidates.append(precise_markup(node) or node)
            return
        for child in node.children:
            if isinstance(child, Node):
                collect(child)
    collect(root)
    if len(candidates) != 1:
        return "", None
    return readable_description(candidates[0]), None


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
    implementation_evidence = r"\b(workflow automation|business process management|Pega|PRPC|BPM|case lifecycle|case management|decision hub|CDH|decisioning|Pega Blueprint|Pega Cloud|Pega Platform|Connect[- ]REST|Service[- ]REST|Connect[- ]SQL|Kafka|REST(?:ful)? APIs?|SOAP|enterprise integration|platform integration|data migration|configuration management)\b"
    if re.search(adjacent, title, re.I):
        if description and re.search(r"\bapplication engineer\b", title, re.I) and not re.search(implementation_evidence, description, re.I):
            return None
        return "adjacent"
    # Generic analyst, advisory, cloud, and migration titles must have actual implementation requirements in the JD.
    if re.search(r"\b(engineer|developer|architect|application|automation|analyst|consultant|associate|manager|configuration|migration|cloud solutions?)\b", title, re.I) and re.search(implementation_evidence, description, re.I):
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
    years = experience_signals(description, title)
    experience_min = max((item["minimum_years"] for item in years), default=None)
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
            "evidence_scope": "role_description" if description else "public_job_card",
            "description_text": description, "description_complete": bool(description),
            "description_source_url": url if description else None,
            "description_checked_at": checked_at if description else None}


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

    def wait(self, url, stop_event, blocked=None):
        """Reserve one host slot without holding a connection or mutex while waiting."""
        host = urllib.parse.urlparse(url).hostname or ""
        with self.lock:
            scheduled = max(time.monotonic(), self.next_at.get(host, 0))
            self.next_at[host] = scheduled + self.spacing
        while time.monotonic() < scheduled:
            if blocked is not None and blocked():
                return False
            if stop_event.wait(min(0.1, max(0, scheduled - time.monotonic()))):
                raise Cancelled()
        if stop_event.is_set():
            raise Cancelled()
        return not (blocked is not None and blocked())


class PublicClient:
    # Responses live only for this client run. The byte budget conservatively
    # allows four bytes per decoded character, including non-ASCII descriptions.
    CACHE_ENTRIES = 128
    CACHE_BYTES = 12 * 1024 * 1024
    MAX_BODY_BYTES = 3_000_000
    MAX_BACKOFF = 300

    def __init__(self, stop_event=None, spacing=2.0, timeout=10):
        self.stop_event, self.limiter, self.timeout = stop_event or threading.Event(), RateLimiter(spacing), timeout
        self._lock = threading.Lock()
        self._cache, self._inflight, self._circuits = OrderedDict(), {}, {}
        self._cache_bytes = 0
        self._backoffs = {}
        self._stats = dict(requests=0, cache_hits=0, shared_waits=0, active_requests=0,
                           peak_active_requests=0, queued_requests=0, circuit_skips=0)
        self._platform_stats = {}  # per-platform: {ok, blocked, error, pages}

    @staticmethod
    def _classify_platform(url):
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
        if "linkedin.com" in host:
            return "LinkedIn"
        if "naukri.com" in host:
            return "Naukri"
        if "indeed." in host:
            return "Indeed"
        if "glassdoor." in host:
            return "Glassdoor"
        if "google." in host:
            return "Google"
        return "Employer"

    def _record_platform(self, url, status, skipped=False):
        """Track per-platform request outcomes."""
        platform = self._classify_platform(url)
        with self._lock:
            entry = self._platform_stats.setdefault(platform, {"ok": 0, "blocked": 0, "error": 0, "pages": 0})
            if skipped:
                entry['skipped']=entry.get('skipped',0)+1
                return
            entry["pages"] += 1
            if status is None:
                entry["error"] += 1
            elif 200 <= status < 400:
                entry["ok"] += 1
            elif status in (403, 429):
                entry["blocked"] += 1
            else:
                entry["error"] += 1

    @staticmethod
    def _key(url):
        # Do not use job canonical_url here: search query strings and pagination
        # are essential request identity, and their order can matter to servers.
        parts = urllib.parse.urlsplit(url)
        return urllib.parse.urlunsplit((parts.scheme.lower(), parts.netloc.lower(),
                                       parts.path, parts.query, ""))

    def snapshot_stats(self):
        with self._lock:
            import copy as _copy
            return {**self._stats, "cached_responses": len(self._cache),
                    "cache_bytes": self._cache_bytes, "inflight_urls": len(self._inflight),
                    "platforms": _copy.deepcopy(self._platform_stats)}

    def _host_block(self, url):
        host = urllib.parse.urlsplit(url).hostname or ""
        with self._lock:
            circuit = self._circuits.get(host)
            if not circuit:
                return None
            remaining = circuit["until"] - time.monotonic()
            if remaining <= 0:
                self._circuits.pop(host, None)
                return None
            diagnostic = dict(circuit["diagnostic"])
        diagnostic.update(url=url, blocked_source_url=diagnostic["url"],
                          request_skipped=True, circuit_open=True)
        if remaining != float("inf"):
            diagnostic["retry_after_seconds"] = max(1, int(remaining + 0.999))
        else:
            diagnostic["blocked_for_run"] = True
        return diagnostic

    def _reject_host(self, url, status, headers, diagnostic):
        if status not in (403, 429):
            return
        host = urllib.parse.urlsplit(url).hostname or ""
        retry_after = None
        if headers:
            raw = headers.get("Retry-After", "")
            try:
                retry_after = max(0.0, float(raw))
            except (ValueError, TypeError):
                try:
                    date = parsedate_to_datetime(raw)
                    if date.tzinfo is None:
                        date = date.replace(tzinfo=timezone.utc)
                    retry_after = max(0.0, (date - datetime.now(timezone.utc)).total_seconds())
                except (ValueError, TypeError, OverflowError):
                    pass
        with self._lock:
            attempt = self._backoffs.get(host, 0) + 1
            self._backoffs[host] = attempt
            delay = min(self.MAX_BACKOFF, 30 * 2 ** min(attempt - 1, 4) + random.uniform(0, 1))
            # Access denial is not a transient rate-limit response.
            # Stop this host for the run rather than changing clients to retry.
            # Rate limits below retain the server's Retry-After deadline.
            if status == 403:
                until = float("inf")
            elif retry_after is not None and retry_after > self.MAX_BACKOFF:
                until = float("inf")
            else:
                delay = max(delay, retry_after or 0, self.limiter.spacing)
                until = time.monotonic() + delay
            prior = self._circuits.get(host)
            if prior:
                until = max(until, prior["until"])
            self._circuits[host] = {"until": until, "diagnostic": dict(diagnostic)}

    def _remember(self, key, result):
        html, diagnostic = result
        # Temporary network/server failures can recover later in the same run.
        # Host-level denial/rate-limit circuits are tracked separately.
        if html is None or not (200 <= (diagnostic.get("http_status") or 0) < 300):
            return
        size = len(html) * 4 + 1024
        if size > self.CACHE_BYTES:
            return
        with self._lock:
            while self._cache and (len(self._cache) >= self.CACHE_ENTRIES or self._cache_bytes + size > self.CACHE_BYTES):
                _, (_, _, old_size) = self._cache.popitem(last=False)
                self._cache_bytes -= old_size
            self._cache[key] = (html, dict(diagnostic), size)
            self._cache_bytes += size

    def get(self, url):
        if self.stop_event.is_set():
            raise Cancelled()
        key = self._key(url)
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                self._cache.move_to_end(key)
                self._stats["cache_hits"] += 1
                return cached[0], {**cached[1], "url": url, "cache_hit": True, "cache_mode": "run_cache"}
            flight = self._inflight.get(key)
            owner = flight is None
            if owner:
                flight = {"event": threading.Event()}
                self._inflight[key] = flight
            else:
                self._stats["shared_waits"] += 1
        if not owner:
            while not flight["event"].wait(0.1):
                if self.stop_event.is_set():
                    raise Cancelled()
            if self.stop_event.is_set():
                raise Cancelled()
            if "exception" in flight:
                raise flight["exception"]
            html, diagnostic = flight["result"]
            return html, {**diagnostic, "url": url, "cache_hit": True, "cache_mode": "inflight"}
        try:
            result = self._fetch(url)
            self._remember(key, result)
            flight["result"] = result
            return result
        except BaseException as error:
            # Wake duplicate callers even after cancellation or unexpected errors.
            flight["exception"] = error
            raise
        finally:
            with self._lock:
                self._inflight.pop(key, None)
                flight["event"].set()

    def _fetch(self, url):
        blocked = self._host_block(url)
        if blocked is None:
            with self._lock:
                self._stats["queued_requests"] += 1
            try:
                self.limiter.wait(url, self.stop_event, lambda: self._host_block(url))
            finally:
                with self._lock:
                    self._stats["queued_requests"] -= 1
            blocked = self._host_block(url)
        if self.stop_event.is_set():
            raise Cancelled()
        if blocked is not None:
            with self._lock:
                self._stats["circuit_skips"] += 1
            self._record_platform(url, blocked.get('http_status'), skipped=True)
            return None, blocked
        checked = now()
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json"})
        with self._lock:
            self._stats["requests"] += 1
            self._stats["active_requests"] += 1
            self._stats["peak_active_requests"] = max(self._stats["peak_active_requests"], self._stats["active_requests"])
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read(self.MAX_BODY_BYTES + 1)
                html = raw[:self.MAX_BODY_BYTES].decode("utf-8", errors="replace")
                diagnostic = {"url": url, "final_url": response.url, "http_status": response.status, "checked_at": checked}
                if len(raw) > self.MAX_BODY_BYTES:
                    diagnostic["content_truncated"] = True
                self._record_platform(url, response.status)
                return html, diagnostic
        except urllib.error.HTTPError as error:
            diagnostic = {"url": url, "http_status": error.code, "checked_at": checked, "error": "HTTP request rejected"}
            self._record_platform(url, error.code)
            try:
                self._reject_host(url, error.code, error.headers, diagnostic)
            finally:
                error.close()
            return None, diagnostic
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            self._record_platform(url, None)
            return None, {"url": url, "http_status": None, "checked_at": checked, "error": str(error)[:220]}
        finally:
            with self._lock:
                self._stats["active_requests"] -= 1


def query_url(target, expanded=False, start=0):
    keyword = target.get("keywords", [target["name"]])[0]
    keywords = ROLE_QUERY if broad_target(target) else f'("{keyword}") AND {ROLE_QUERY}' if expanded else f"pega {keyword}"
    return "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?" + urllib.parse.urlencode({"keywords": keywords, "location": target.get("location", "India"), "start": start})


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
        individual_url = canonical_url(urllib.parse.urljoin(page_url, raw.get("url", ""))) if raw.get("url") else None
        if not individual_url:
            continue
        raw_description = raw.get("description", "")
        description = readable_description(Document(raw_description).root) if re.search(r"<[a-z][^>]*>", raw_description, re.I) else raw_description.strip()
        job = make_job(raw.get("title", ""), employer, location, individual_url, "Employer career page", checked_at, description, raw.get("datePosted"))
        if job and job.get("track") == "pega":
            job["closing_at"] = raw.get("validThrough")
            result.append(job)
    return result


def check_target(target, client):
    checked_at, url = now(), query_url(target)
    record = {"target_id": target["target_id"], "name": target["name"], "category": target.get("category", "gcc"), "location": target.get("location", "India"),
              "status": "pending", "checked_at": None, "source_url": url, "diagnostics": [], "jobs": []}
    cards = {}
    generic_checked = set()
    cancelled = False
    access_rejected = False

    def keep_title_candidates(found):
        for card in found:
            cards[card["url"]] = card
            job = make_job(**card, source="LinkedIn public jobs", checked_at=checked_at)
            if job and job.get("track") == "pega":
                record["jobs"].append(job)

    def generic_candidates():
        return [card for card in cards.values()
                if classify_track(card["title"]) != "pega"
                and re.search(r"engineer|developer|architect|automation|application", card["title"], re.I)]

    def check_generic_descriptions():
        # Titles such as Software Engineer may still describe real Pega work.
        # Keep that route, with one shared budget across both query formats.
        nonlocal cancelled, access_rejected
        for card in generic_candidates():
            if cancelled or access_rejected or len(generic_checked) >= 5:
                break
            if card["url"] in generic_checked:
                continue
            seed = {**card, "id": job_identity(card["title"], card["company"], card["url"]),
                    "source": "LinkedIn public jobs", "checked_at": checked_at,
                    "status": "uncertain", "verification_status": "candidate",
                    "experience_min": None, "fit": "possible", "requirements_unknown": []}
            try:
                candidate = enrich_job(seed, client)
            except Cancelled:
                cancelled = True
                record["diagnostics"].append({"url": card["url"], "error": "Description checks paused; earlier results retained"})
                break
            generic_checked.add(card["url"])
            audit = candidate.get("job_detail_diagnostic", {})
            record["diagnostics"].append(audit)
            if audit.get("http_status") in (401, 403, 429, 999):
                access_rejected = True
                break
            if candidate.get("job_detail_status") == "read" and candidate.get("relevance") == "pega":
                record["jobs"].append(candidate)

    # Simple Pega-plus-employer search first. The Boolean format remains a
    # fallback because either public search can return unrelated suggestions.
    for expanded in (False, True):
        if expanded and (cancelled or access_rejected or record["jobs"] or broad_target(target)
                         or record["status"] in ("blocked", "error")):
            break
        offset, page_keys, query_pega_signal = 0, set(), False
        for page in range(5):
            page_url = query_url(target, expanded=expanded, start=offset)
            try:
                html, diagnostic = client.get(page_url)
            except Cancelled:
                cancelled = True
                record["diagnostics"].append({"url": page_url, "error": "Search paused; earlier pages retained", "pagination_interrupted": True})
                break
            diagnostic.update(page_offset=offset, query_scope="Pega/PRPC Boolean fallback after no retained Pega roles" if expanded else "Pega plus employer first pass")
            record["diagnostics"].append(diagnostic)
            record["checked_at"] = checked_at
            if html is None:
                access_rejected = diagnostic.get("http_status") in (401, 403, 429, 999)
                record["status"] = "blocked" if access_rejected else "error"
                break
            try:
                found, raw_count = parse_cards(html, target)
                fingerprint = tuple(sorted(set(canonical_url(n.attrs.get("href", "")) for n in Document(html).root.walk()
                                               if n.tag == "a" and n.has_class("base-card__full-link")))) or html.strip()
            except Exception as error:
                diagnostic["error"] = "Listing parse failed: " + str(error)[:180]
                record["status"] = "error"
                break
            title_signals = sum(classify_track(card["title"]) == "pega" for card in found)
            diagnostic.update(raw_cards=raw_count, employer_matches=len(found), matching_pega_title_cards=title_signals)
            if fingerprint in page_keys:
                diagnostic["pagination_stop"] = "Repeated public result page"
                diagnostic["pagination_incomplete"] = True
                break
            page_keys.add(fingerprint)
            keep_title_candidates(found)
            if raw_count or len(html.strip()) < 40 or re.search(r"no (?:matching )?jobs found|no results found", html, re.I):
                record["status"] = "no_matches"
            else:
                record["status"] = "blocked"
                diagnostic["error"] = "No recognizable job cards or empty-result marker; page may be blocked or changed"
                break
            query_pega_signal = query_pega_signal or bool(title_signals)
            if raw_count < 10:
                diagnostic["pagination_stop"] = "Empty or short public result page"
                break
            if not query_pega_signal:
                before = len(record["jobs"])
                check_generic_descriptions()
                query_pega_signal = len(record["jobs"]) > before
                if cancelled or access_rejected:
                    diagnostic["pagination_incomplete"] = True
                    break
            if not query_pega_signal:
                diagnostic.update(pagination_stop="Stopped after a full page without matching Pega evidence; later pages were not checked",
                                  pagination_incomplete=True, relevance_early_stop=True)
                break
            offset += raw_count
            if page == 4:
                diagnostic["pagination_stop"] = "Five-page query cap reached; further results may exist"
                diagnostic["pagination_capped"] = True
        # A short result page can include a generic title with a genuine Pega JD.
        # Verify it before deciding whether the alternate query is still needed.
        check_generic_descriptions()

    unchecked = sum(card["url"] not in generic_checked for card in generic_candidates())
    if unchecked:
        record["diagnostics"].append({"url": url, "generic_jds_not_checked": unchecked,
                                      "note": "Matching-employer generic roles remain unverified after the five-description budget or interruption"})
    # Career portal scraping with Playwright runs after the parallel scan
    # completes, not here inside a ThreadPoolExecutor worker thread.
    # Playwright's greenlet-based sync API cannot be called from pool threads.
    if record["jobs"]:
        record["status"] = "results"
    record["jobs"] = list({job["id"]: job for job in record["jobs"]}.values())
    record["partial"] = any(d.get("error") or d.get("generic_jds_not_checked") or d.get("pagination_capped") or d.get("pagination_incomplete")
                            for d in record["diagnostics"])
    if any(d.get("relevance_early_stop") for d in record["diagnostics"]):
        record["coverage_note"] = "Only pages with matching Pega evidence were explored further; no retained matches does not establish that this employer has no openings."
    if cancelled:
        record["status"] = "pending"
        record["partial"] = True
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


def retain_previous_jobs(record, previous, keep_missing=True):
    """Keep evidence on failed checks; fresh successful searches can replace missing roles.

    Dropping an old role from the current search is not a claim that it closed.
    Matching rediscovered roles retain their last description until refreshed.
    """
    current = {canonical_url(job.get("url", "")) or job["id"]: job for job in record.get("jobs", [])}
    record["fresh_job_count"] = len(current)
    retained = 0
    for old in previous.get("jobs", []):
        key = canonical_url(old.get("url", "")) or old["id"]
        if key in current:
            fresh = current[key]
            if (old.get("description_complete") and not fresh.get("description_complete")
                    and normalized_name(old.get("title", "")) == normalized_name(fresh.get("title", ""))
                    and employer_matches(old.get("company", ""), {"name": fresh.get("company", "")})):
                for field in ("description_text", "description_source_url", "description_checked_at", "description_complete",
                              "description_identity", "experience_min", "experience_max", "experience_evidence", "skills",
                              "required_certifications", "certification_evidence"):
                    if field in old:
                        fresh[field] = copy.deepcopy(old[field])
            continue
        if not keep_missing:
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


# Python's regular Windows readers can deny delete-sharing. Coordinate our
# own dashboard reads, and retry short external reader / antivirus holds.
_CHECKPOINT_IO_LOCK = threading.RLock()
SAVE_RETRY_DELAYS = (0.05, 0.1, 0.2, 0.4, 0.8, 1.0, 1.0, 1.0, 1.0)


class CheckpointSaveError(RuntimeError):
    def __init__(self, recovery_path):
        self.recovery_path = Path(recovery_path)
        super().__init__(
            "Windows kept the results file locked, so this search stopped safely. "
            "The last saved results are intact. The newer recovery copy is at "
            + str(self.recovery_path)
        )


def load_campaign(output_path=None):
    path = Path(output_path or DEFAULT_OUTPUT)
    with _CHECKPOINT_IO_LOCK:
        try:
            raw = path.read_text(encoding="utf-8-sig")
        except FileNotFoundError:
            return {"schema_version": 1, "status": "not_started", "targets": [], "coverage": coverage([])}
    return json.loads(raw)


def _replace_checkpoint(temporary, path):
    for attempt in range(len(SAVE_RETRY_DELAYS) + 1):
        try:
            temporary.replace(path)
            return
        except OSError as error:
            transient = isinstance(error, PermissionError) or getattr(error, "winerror", None) in (5, 32, 33)
            if not transient:
                raise
            if attempt == len(SAVE_RETRY_DELAYS):
                raise CheckpointSaveError(temporary) from error
            time.sleep(SAVE_RETRY_DELAYS[attempt])


def save_campaign(data, output_path):
    data["updated_at"] = now()
    data["coverage"] = coverage(data["targets"])
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Stage a complete durable document beside its destination. Never truncate
    # the active checkpoint, and retain the staged copy if replacement fails.
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix="." + path.name + ".", suffix=".tmp", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    with _CHECKPOINT_IO_LOCK:
        _replace_checkpoint(temporary, path)


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


def experience_signals(description, title=""):
    """Read explicit numeric experience in a JD or title, not a seniority guess."""
    # Keep one-character substitutions so excerpts retain the original wording.
    translation = str.maketrans({chr(c): "-" for c in (0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2212)})
    pattern = re.compile(
        r"(?<![\w.])(?:minimum(?:\s+of)?\s+|at\s+least\s+)?(\d{1,2})"
        r"(?:\s*(?:-|to)\s*(\d{1,2}))?\s*(?:\+|plus)?\s*(?:years?|yrs?)['’]?"
        r"\s*(?:\([^)]{0,70}\)\s*)?(?:of\s+)?(?:[a-z][a-z0-9 /,'()\-]*?\s+)?experience\b", re.I)
    found, seen = [], set()
    for original, scope in ((description or "", "description"), (title or "", "title")):
        normalized = original.translate(translation)
        for match in pattern.finditer(normalized):
            if len(match.group(0)) > 170:
                continue
            low, high = int(match.group(1)), int(match.group(2) or match.group(1))
            if not 0 <= low <= high <= 35:
                continue
            lead = normalized[max(0, match.start() - 50):match.start()]
            if re.search(r"company|founded|established|our\s+business|organization", lead, re.I):
                continue
            excerpt = original[match.start():match.end()][:150]
            if (low, high, excerpt) in seen:
                continue
            seen.add((low, high, excerpt))
            found.append({"minimum_years": low, "maximum_years": high, "source_text": excerpt, "source_scope": scope})
    return found[:8]


def mandatory_clsa_evidence(description):
    """Only explicit lead-architect certification requirements create a known gap."""
    credential = r"(?:\bCLSA\b|\bPega\s+LSA\b|\bcertified lead system architect\b)"
    found = []
    for clause in re.split(r"[.;\n]", description or ""):
        if not re.search(credential, clause, re.I):
            continue
        if re.search(r"\b(preferred|optional|desirable)\b|not\s+(?:mandatory|required)|\bCSSA\b.*\bor\b", clause, re.I):
            continue
        explicit = re.search(r"\b(?:must|required|mandatory)\b.{0,90}" + credential, clause, re.I) or re.search(
            credential + r".{0,65}\b(?:must|required|mandatory)\b", clause, re.I)
        # This is an affirmative qualification, unlike a generic mention of LSA work.
        affirmative = re.search(r"^\s*(?:qualifications?\s*:\s*)?Pega\s+(?:CLSA|LSA)\s+certified\b", clause, re.I)
        if explicit or affirmative:
            found.append({"certification": "CLSA", "source_text": clause.strip()[:200]})
    return found[:3]


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
    if diagnostic.get("content_truncated"):
        updated["job_detail_status"] = "description_missing"
        diagnostic["error"] = "Individual role response exceeded the download limit; a complete description cannot be established"
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
        posting_url = canonical_url(structured.get("url", ""))
        if posting_url and posting_url != canonical_url(job["url"]):
            updated["job_detail_status"] = "identity_unconfirmed"
            diagnostic["error"] = "Structured job identity differs from the saved listing URL"
            return updated
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
    updated.update(description_text=description, description_complete=True,
                   description_source_url=canonical_url(job["url"]),
                   description_checked_at=updated["job_detail_checked_at"])
    # The refreshed role is authoritative for current requirements. Clear facts
    # inferred from an older JD before deriving the new ones.
    updated.update(experience_min=None, experience_max=None, required_certifications=[],
                   certification_evidence=[], fit="possible", fit_reasons=[])
    updated["evidence_scope"] = "role_description"
    updated["description_identity"] = "title_and_endpoint" if title else "exact_endpoint_only"
    updated["skills"] = [label for label, pattern in SKILL_PATTERNS.items() if re.search(pattern, description, re.I)]
    signals = experience_signals(description, job.get("title", ""))
    updated["experience_evidence"] = signals
    if signals:
        # A secondary skill can have fewer years than the overall role: do not use
        # the smallest extracted number to claim the whole vacancy is a four-year fit.
        updated["experience_min"] = max(item["minimum_years"] for item in signals)
        updated["experience_max"] = max(item["maximum_years"] for item in signals if item["minimum_years"] == updated["experience_min"])
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
        "Full role requirements not fetched", "Experience threshold", "Published compensation", "Explicit experience threshold not identified", "No explicit annual INR compensation extracted") and not x.startswith(("Stated minimum ", "Experience wording includes ", "The description explicitly requires ",
            "CLSA appears in the description;", "Country or residency restrictions require review;",
            "Detailed description did not establish ", "Previous salary evidence retained", "Individual role page could not be read;"))]
    if not signals:
        unknown.append("Explicit experience threshold not identified")
    elif updated["experience_min"] > 4:
        updated["fit"] = "stretch"
        unknown.append(f"Experience wording includes {updated['experience_min']}+ years; exceeds the known four years. Check whether mandatory or preferred.")
    if not salary:
        unknown.append("Previous salary evidence retained; latest description did not publish an annual INR figure. Confirm the budget." if updated.get("salary") else "No explicit annual INR compensation extracted")
    certification_evidence = mandatory_clsa_evidence(description)
    if certification_evidence:
        updated["required_certifications"] = ["CLSA"]
        updated["certification_evidence"] = certification_evidence
        updated["fit"] = "stretch"
        unknown.append("The description explicitly requires lead architect certification (CLSA); the known certification is CSSA.")
    elif "CLSA" in updated["skills"]:
        unknown.append("CLSA appears in the description; current known certification is CSSA. Check whether CLSA is required.")
    if updated["remote_eligibility"] == "country_restricted":
        unknown.append("Country or residency restrictions require review; not established as India-eligible remote work")
    # A Pega title or employer alone must not supply Pega evidence for the JD.
    new_track = classify_track("", description) if re.search(r"\b(Pega|PRPC|OpenSpan)\b", description, re.I) else classify_track(job["title"], description)
    if new_track == "pega" and not re.search(r"\b(Pega|PRPC|OpenSpan)\b", description, re.I):
        new_track = None
    if new_track:
        updated["track"] = new_track
        updated["relevance"] = new_track
        updated["fit_reasons"] = ["The saved role description explicitly mentions Pega/PRPC."] if new_track == "pega" else []
    else:
        updated["track"] = "unrelated"
        updated["relevance"] = "unrelated"
        updated["fit"] = "stretch"
        unknown.append("Detailed description did not establish Pega/PRPC role requirements; excluded from Pega recommendations")
    updated["requirements_unknown"] = list(dict.fromkeys(unknown))
    updated["summary"] = "Individual public role description read. " + ("Technologies mentioned: " + ", ".join(updated["skills"]) + ". " if updated["skills"] else "") + "Skill mentions are evidence of role content, not proof every item is mandatory. Application availability still needs confirmation."
    updated["evidence"] = [{"url": job["url"], "title": job["company"] + " — " + job["title"], "source_type": "Public individual job description", "checked_at": updated["job_detail_checked_at"], "excerpt": updated["summary"], "status": "candidate"}]
    if structured and structured.get("validThrough"):
        updated["closing_at"] = structured["validThrough"]
    # Remain a candidate: reading a public description does not prove an employer
    # is still accepting applications or would accept this applicant's experience.
    updated["verification_status"] = "candidate"
    return updated


def enrich_campaign(output_path=None, progress=None, stop_event=None, force=False, workers=6, target_ids=None):
    """Enrich selected target URLs, propagating facts without replacing saved identities."""
    path = Path(output_path or DEFAULT_OUTPUT)
    stop_event = stop_event or threading.Event()
    def checkpoint(document):
        try:
            save_campaign(document, path)
        except Exception:
            # Stop queued requests before ThreadPoolExecutor waits for teardown.
            stop_event.set()
            raise

    with campaign_lock(path):
        document = load_campaign(path)
        targets = document.get("targets", [])
        wanted = set(target_ids) if target_ids is not None else None
        if wanted is not None and not wanted.issubset({t.get("target_id") for t in targets}):
            raise ValueError("An unknown target_id was requested for enrichment")
        all_copies, selected_copies = {}, {}
        for target in targets:
            selected = wanted is None or target.get("target_id") in wanted
            for job in target.get("jobs", []):
                url = canonical_url(job["url"])
                all_copies.setdefault(url, []).append(job)
                if selected:
                    selected_copies.setdefault(url, []).append(job)
        jobs_by_url = {}
        for url, selected in selected_copies.items():
            # An unchecked selected copy must not inherit another target's cache.
            # Prioritize it even when several selected targets share this URL.
            ordered = sorted(selected, key=lambda job: bool(job.get("job_detail_status")))
            selected_objects = {id(job) for job in selected}
            jobs_by_url[url] = ordered + [job for job in all_copies[url] if id(job) not in selected_objects]
        detail = {"status": "running", "started_at": now(), "total": len(jobs_by_url), "checked": 0, "read": 0, "unavailable": 0, "identity_unconfirmed": 0, "description_missing": 0, "cached": 0}
        if wanted is not None:
            detail["target_ids"] = sorted(wanted)
        document["detail_enrichment"] = detail
        document.setdefault("query_policy", {}).update(pagination="Up to five public pages per query; stops on empty/short/repeated pages or access rejection; optional simpler fallback; not exhaustive", detail_policy="One public description check per distinct retained role; preserves candidates when unavailable")
        checkpoint(document)
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
                # Propagate only description-derived facts. IDs, original card
                # identity/provenance and user pipeline fields belong to each copy.
                fact_fields = (
                    "job_detail_checked_at", "job_detail_diagnostic", "job_detail_status",
                    "evidence_scope", "description_identity", "description_text", "description_source_url",
                    "description_checked_at", "description_complete", "skills", "experience_evidence",
                    "experience_min", "experience_max", "salary", "pay_bucket", "remote_eligibility", "fit", "fit_reasons",
                    "required_certifications", "certification_evidence", "requirements_unknown",
                    "track", "relevance", "summary", "evidence", "closing_at", "verification_status",
                )
                for saved in copies:
                    if normalized_name(saved.get("title", "")) != normalized_name(enriched.get("title", "")) or not employer_matches(saved.get("company", ""), {"name": enriched.get("company", "")}):
                        # Reused URLs do not establish identical vacancies.
                        continue
                    if enriched.get("job_detail_status") != "read":
                        # A failed attempt can update diagnostics for every copy,
                        # but cannot replace each copy's last successful JD.
                        for key in ("job_detail_checked_at", "job_detail_diagnostic", "job_detail_status"):
                            if key in enriched:
                                saved[key] = copy.deepcopy(enriched[key])
                        continue
                    prior_salary = copy.deepcopy(saved.get("salary"))
                    for key in fact_fields:
                        if key in enriched:
                            saved[key] = copy.deepcopy(enriched[key])
                    # A fresh copy with no salary must not erase an older copy's
                    # independently sourced salary, or import it into fresh copies.
                    if prior_salary and not saved.get("salary"):
                        prior_salary.setdefault("source_url", saved.get("url"))
                        prior_salary.setdefault("evidence_checked_at", saved.get("checked_at"))
                        prior_salary["latest_presence"] = "not_rediscovered"
                        saved["salary"] = prior_salary
                        saved["pay_bucket"] = pay_bucket(prior_salary)
                        saved["requirements_unknown"] = list(dict.fromkeys(saved.get("requirements_unknown", []) + ["Previous salary evidence retained for this saved copy; latest selected description did not publish an annual INR figure. Confirm the budget."]))
                outcome = enriched.get("job_detail_status", "unavailable")
                detail["checked"] += 1
                detail[outcome if outcome in detail else "unavailable"] += 1
                checkpoint(document)
                if progress:
                    progress({"phase": "job_details", "detail_enrichment": detail, "current_company": enriched.get("company")})
        detail["status"] = "cancelled" if stop_event.is_set() else "complete"
        detail["completed_at"] = now() if detail["status"] == "complete" else None
        checkpoint(document)
        return document


def run_campaign(target_ids=None, force=False, progress=None, workers=6, output_path=None, data=None, stop_event=None):
    """Run/resume checks; progress receives one dict after each atomic checkpoint.

    data optionally supplies an in-memory target list for offline tests. All directory
    targets are included by default, including new records added during the run.
    A checked blocked target is a completed attempt, not a successful vacancy search.
    """
    output_path = Path(output_path or DEFAULT_OUTPUT)
    stop_event = stop_event or threading.Event()
    def checkpoint(document):
        try:
            save_campaign(document, output_path)
        except Exception:
            stop_event.set()
            raise

    with campaign_lock(output_path):
        catalog = list(data) if data is not None else load_targets()
        wanted = set(target_ids) if target_ids is not None else None
        if wanted is not None and not wanted.issubset({t["target_id"] for t in catalog}):
            raise ValueError("An unknown target_id was requested")
        previous = load_campaign(output_path)
        rows = {t["target_id"]: t for t in previous.get("targets", [])}
        document = {"schema_version": 1, "started_at": now() if force else previous.get("started_at", now()), "status": "running",
                    "threshold_annual_inr": 2000000, "query_policy": {"roles": ROLE_QUERY, "source": "Public LinkedIn guest job search; employer structured fallback if blocked", "per_domain_spacing_seconds": 2.0, "request_timeout_seconds": 10,
                    "generic_jd_limit_per_target": 5, "pagination": "Up to five public pages per query; stops on empty/short/repeated pages or access rejection; optional simpler fallback; not exhaustive", "detail_policy": "Optional resumable public description check for every distinct retained role", "salary_policy": "Only explicit annual INR CTC establishes the 20 lakh threshold; fixed or unspecified salary remains unknown", "no_matches_meaning": "This query returned no retained profile/employer matches; not proof the employer has no openings"}, "targets": []}

        def enroll(targets, reset=False):
            for target in targets:
                key = target["target_id"]
                if reset or key not in rows:
                    prior_jobs = copy.deepcopy(rows.get(key, {}).get("jobs", []))
                    if reset:
                        # Fresh search results replace these rows when checked.
                        # A pending or blocked refresh must not promote old roles.
                        for job in prior_jobs:
                            job.update(search_presence="not_rediscovered", status="uncertain",
                                       verification_status="candidate", latest_search_at=now())
                    rows[key] = {"target_id": key, "name": target["name"], "category": target.get("category", "gcc"), "location": target.get("location", "India"), "status": "pending", "checked_at": None, "source_url": query_url(target), "diagnostics": [], "jobs": prior_jobs, "replace_previous_on_success": bool(reset)}

        enroll(catalog)
        if force:
            enroll([t for t in catalog if wanted is None or t["target_id"] in wanted], reset=True)
        client = PublicClient(stop_event)
        while True:
            active_ids = {t["target_id"] for t in catalog}
            document["targets"] = [rows[t["target_id"]] for t in catalog]
            checkpoint(document)
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
                    previous_target = rows[target["target_id"]]
                    replace_missing = previous_target.get("replace_previous_on_success", False) and record.get("status") in ("results", "no_matches")
                    rows[target["target_id"]] = retain_previous_jobs(record, previous_target, keep_missing=not replace_missing)
                    document["targets"] = [rows[t["target_id"]] for t in catalog]
                    checkpoint(document)
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
        checkpoint(document)
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
