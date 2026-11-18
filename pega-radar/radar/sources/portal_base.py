"""Shared machinery for the career-portal adapters (`portal_api.py`, `portal_pages.py`).

A *family* knows one platform: how to ask for one page of search results, how to read one
posting's detail, and how to tell a real board from a wrong host. `collect` does everything
else the same way for every platform: pages are merged by stable posting id, caps and later
failures make the result `partial`, a first-page failure keeps its own status (a refusal is
`blocked`), an empty search is `empty` only after a broad query proves the board is real, and
postings are dropped for their location only on positive foreign evidence.

Every field access on a platform answer is defensive: a missing or wrongly typed field turns
into `error` ("unexpected response shape") or an unread posting, never a crash or a wrong job.
"""
from __future__ import annotations

import html
import json
import re
from collections import namedtuple
from datetime import date, datetime, timedelta, timezone

from ..model import is_india, is_pega, make_job, make_result, outside_india, strip_html
from . import FALLBACK_TITLE, WRONG_SHAPE, day, failure

SOURCE = 'Employer site'
HTML = 'text/html,application/xhtml+xml'
OUT_OF_TIME = 'the time budget ran out'
WRONG_SITE = 'the career site answered but lists no jobs at all; check the portal settings'
PAGE_CAP = 500          # postings per query before the result is reported as capped
DETAIL_CAP = 150        # detail reads per board per run
REPEATED = 'the site returned the same page twice; paging stopped'

# One search page: `rows` are normalised postings, `total` the platform's count (None when it
# does not say), `next` the cursor of the following page (None when this is the last one), and
# `note` a non-fatal problem with this page (it makes the result partial).
Page = namedtuple('Page', 'rows total next note', defaults=(None,))

# ISO country codes that may close a location string ("Docklands, AU"). Codes that are also
# Indian state abbreviations (TN, GA, HR, MH, MP, TG, CH for Chandigarh ...) are left out, and
# so is IN: such a code proves nothing on its own.
FOREIGN_CODES = frozenset((
    'US', 'GB', 'UK', 'AU', 'NZ', 'CA', 'IE', 'DE', 'FR', 'NL', 'BE', 'LU', 'ES', 'PT', 'IT', 'AT', 'SE', 'NO',
    'DK', 'FI', 'PL', 'CZ', 'SK', 'HU', 'RO', 'BG', 'RS', 'SI', 'LT', 'LV', 'EE', 'UA', 'TR', 'IL', 'EG', 'MA',
    'ZA', 'KE', 'NG', 'AE', 'SA', 'QA', 'KW', 'BH', 'OM', 'SG', 'MY', 'PH', 'ID', 'TH', 'VN', 'JP', 'CN', 'HK',
    'TW', 'KR', 'LK', 'BD', 'PK', 'MX', 'BR', 'AR', 'CO', 'CL', 'PE', 'CR', 'PR', 'UY', 'GR', 'CY', 'IS',
))
_DATE_FORMATS = ('%d %b %Y', '%b %d, %Y', '%d %B %Y', '%B %d, %Y', '%d-%b-%Y', '%d.%m.%Y', '%d/%m/%Y', '%Y/%m/%d')
_ATTR_RE = re.compile(r'([\w:.-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')')


class Family:
    """One platform. Subclasses set `kind` and implement `identity`, `search` and, when the
    listing carries no description, `detail`.

    `queries` are searched in turn; a `None` query means the platform has no search and the
    whole board is one feed. The query `''` is the broad (unfiltered) search used to prove a
    board real.
    """

    kind = ''
    queries = ('pega', 'prpc')
    page_cap = PAGE_CAP
    detail_cap = DETAIL_CAP

    def identity(self, portal) -> str:
        raise NotImplementedError

    def search(self, http, portal, query, cursor):
        """`(Page, None)` or `(None, (status, message))`. `cursor` is None for the first page,
        then whatever the previous page gave as `next` (an offset, a page number ...)."""
        raise NotImplementedError

    def detail(self, http, portal, row):
        """A dict of fields learnt from the posting's own page (at least 'description'), or None."""
        return None

    def board_size(self, http, portal):
        """`(size, None)` from the broad query, `(None, None)` when the platform cannot say,
        or `(None, problem)` when the broad query itself failed."""
        page, problem = self.search(http, portal, None if self.queries == (None,) else '', None)
        if page is None:
            return None, problem
        return (page.total if page.total is not None else len(page.rows)), None

    def board_notes(self, rows):
        """Remarks about the whole board for the result and the probe (e.g. a field every posting lacks)."""
        return []

    @property
    def reads_details(self) -> bool:
        """True when the family can read a posting's own page (it overrides `detail`)."""
        return type(self).detail is not Family.detail

    def url(self, portal, row):
        return row.get('url') or portal.get('career_url') or ''


# ───────────────────────────── small parsing helpers ─────────────────────────────

def text(value) -> str:
    """A scalar as stripped text; containers and None become ''."""
    if value is None or isinstance(value, (dict, list, tuple, set, bool)):
        return ''
    return str(value).strip()


def integer(value):
    """An int from an int or a numeric string; None otherwise."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def when(value):
    """'YYYY-MM-DD' from ISO text, epoch seconds or milliseconds, or dates such as '10 Nov 2026'."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = value / 1000 if value > 1e11 else value
        try:
            return datetime.fromtimestamp(seconds, timezone.utc).date().isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    iso = day(value)
    if iso or not isinstance(value, str):
        return iso
    cleaned = re.sub(r'\s+', ' ', value).strip()
    for pattern in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, pattern).date().isoformat()
        except ValueError:
            continue
    return None


def attributes(tag) -> dict:
    """The attributes of one HTML start tag, entity-decoded."""
    return {m.group(1).lower(): html.unescape(m.group(2) if m.group(2) is not None else m.group(3) or '')
            for m in _ATTR_RE.finditer(tag)}


def inner_html(page, start):
    """Inner HTML of the element whose start tag begins at `start`, honouring nesting of the same tag."""
    opening = re.compile(r'<([A-Za-z][\w-]*)\b[^>]*>').match(page, start)
    if not opening:
        return ''
    name = opening.group(1)
    if opening.group(0).endswith('/>'):
        return ''
    depth, pos = 1, opening.end()
    for match in re.compile(r'<(/?)' + re.escape(name) + r'\b[^>]*?(/?)>', re.I).finditer(page, pos):
        if match.group(1):
            depth -= 1
        elif not match.group(2):
            depth += 1
        if depth == 0:
            return page[pos:match.start()]
    return page[pos:]


def element(page, attribute, value, *, contains=False):
    """Inner HTML of the first element whose `attribute` equals (or, with `contains`, includes as a
    class-like word) `value`; None when there is none."""
    for match in re.finditer(r'<[A-Za-z][\w-]*\b[^>]*>', page):
        found = attributes(match.group(0)).get(attribute)
        if found is None:
            continue
        if (value in found.split()) if contains else found == value:
            return inner_html(page, match.start())
    return None


def json_after(page, marker):
    """The JSON object that follows `marker =` in a page script, or None."""
    at = page.find(marker)
    if at < 0:
        return None
    brace = page.find('{', at + len(marker))
    if brace < 0 or page[at + len(marker):brace].strip(' \t\r\n=') != '':
        return None
    try:
        value, _ = json.JSONDecoder().raw_decode(page, brace)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def job_posting_ld(page):
    """The first schema.org JobPosting object in the page's JSON-LD blocks, or None."""
    for match in re.finditer(r'(?is)<script[^>]*application/ld\+json[^>]*>(.*?)</script>', page or ''):
        try:
            data = json.loads(match.group(1).strip())
        except ValueError:
            continue
        stack = [data]
        while stack:
            item = stack.pop()
            if isinstance(item, list):
                stack.extend(item)
            elif isinstance(item, dict):
                kind = item.get('@type')
                if kind == 'JobPosting' or (isinstance(kind, list) and 'JobPosting' in kind):
                    return item
                if isinstance(item.get('@graph'), list):
                    stack.extend(item['@graph'])
    return None


def plain(fragment) -> str:
    return strip_html(fragment or '')


def code_from_location(location):
    """A foreign ISO country code closing a 'City, ST, CC, 12345' location, or ''."""
    parts = [part.strip() for part in str(location or '').split(',')]
    parts = [part for part in parts if part and not any(ch.isdigit() for ch in part)]
    if len(parts) < 2:
        return ''
    last = parts[-1]
    return last if re.fullmatch(r'[A-Z]{2}', last) and last in FOREIGN_CODES else ''


def abroad(row) -> bool:
    """True only on positive foreign evidence. A country code decides unless an Indian place is named."""
    location = row.get('location') or ''
    code = (row.get('country_code') or '').strip().upper()
    if code:
        return code != 'IN' and not is_india(location)
    return outside_india(location)


def response_reason(response):
    """The net client's failure class (timeout, tls, dns, refused, rate_limited, http_4xx, http_5xx ...)."""
    reason = getattr(response, 'reason', None)
    if isinstance(reason, str) and reason:
        return reason
    status = getattr(response, 'status', 0) or 0
    if status == 429:
        return 'rate_limited'
    return 'http_5xx' if status >= 500 else 'http_4xx' if status >= 400 else 'refused' if not status else ''


def http_problem(response):
    """`(status, message, reason)` for a response that did not succeed."""
    return (*failure(response), response_reason(response))


def problem_reason(problem):
    """The reason class of a problem tuple; a wrong-shape answer is 'shape'."""
    if len(problem) > 2 and problem[2]:
        return problem[2]
    return 'shape' if problem[1] in (WRONG_SHAPE[1], WRONG_SITE) else ''


def page_get(http, url, accept=HTML):
    """GET an HTML page; `(page_text, None)` or `(None, (status, message, reason))`."""
    response = http.get(url, accept=accept)
    if not response.ok:
        return None, http_problem(response)
    return response.text or '', None


def json_get(http, url):
    """GET a JSON document; `(value, response)` where value is None for a failed or non-JSON answer."""
    response = http.get(url)
    return (response.json() if response.ok else None), response


def problem_of(response):
    """Why an answer is unusable: the HTTP failure, or a 200 that is not the expected shape."""
    return http_problem(response) if not response.ok else WRONG_SHAPE


def count_note(count, what='posting'):
    return f'{count} {what}{"s" if count != 1 else ""}'


# ───────────────────────────── the shared driver ─────────────────────────────

def requests_of(http):
    return int(getattr(http, 'count', None) or getattr(http, 'requests', 0) or 0)


Outcome = namedtuple('Outcome', 'jobs found status error reason pages_complete details_complete notes',
                     defaults=((),))


def _unread_outcome(problem):
    return Outcome([], 0, problem[0], problem[1], problem_reason(problem), False, None)


class Memory:
    """What one board has already read, kept in kv between runs (the same rules as ats.py's boards).

    `kept` maps a posting to the source id it was saved under (returned from the listing while the
    store has it), `rejected` holds postings whose *description* showed they are not India Pega roles
    (not re-read for REJECTED_DAYS), `backlog` postings left unread or whose read failed (read first
    next run; kept BACKLOG_DAYS, at most BACKLOG_SIZE). Without a store the memory starts empty every
    run and nothing is committed. The limits and the per-board budget setting are ats.py's.
    """

    def __init__(self, ctx, key):
        from . import ats
        self.limits = ats
        ctx = ctx if isinstance(ctx, dict) else {}
        self.store, self.key = ctx.get('store'), key
        self.state = self._load(self.store.kv_get(key) if self.store is not None else None)
        self.known = set(self.store.known_ids(SOURCE)) if self.store is not None else set()
        self.budget = ats._detail_budget(ctx['config']) if ctx.get('config') is not None else None

    def _load(self, saved):
        saved = saved if isinstance(saved, dict) else {}

        def section(name, days=None):
            cutoff = (date.today() - timedelta(days=days)).isoformat() if days else ''
            values = saved.get(name) if isinstance(saved.get(name), dict) else {}
            return {str(key): value for key, value in values.items() if isinstance(value, str) and value >= cutoff}
        return {'kept': section('kept'), 'rejected': section('rejected', self.limits.REJECTED_DAYS),
                'backlog': section('backlog', self.limits.BACKLOG_DAYS)}

    def forget_delisted(self, listed):
        """After a complete listing, forget postings that are no longer on the board."""
        for section in self.state.values():
            for key in [key for key in section if key not in listed]:
                del section[key]

    def wait(self, keys):
        """Make `keys` the backlog (oldest first, bounded); a key keeps the day it first waited."""
        today = date.today().isoformat()
        backlog = self.state['backlog']
        # The backlog is exactly what is still waiting now; what was read since leaves it.
        waiting = {key: backlog.get(key, today) for key in keys}
        self.state['backlog'] = dict(sorted(waiting.items(), key=lambda item: item[1])[:self.limits.BACKLOG_SIZE])

    def commit(self):
        if self.store is not None:
            self.store.kv_set(self.key, self.state)


def memory_key(family, portal):
    return f'portal_state:{family.kind}:{family.identity(portal)}'


def collect(http, company, family, portal, memory=None):
    """Search one board and return an `Outcome`; its status is None when the board was read in full.

    `pages_complete` is True only when every result page of every query was read and every posting
    that needed a description got one, so a posting absent from the jobs is really gone from the
    board; `details_complete` is True when every description that was needed was read.
    """
    memory = memory or Memory(None, memory_key(family, portal))
    identity = family.identity(portal)
    rows, troubles, reasons, notes, first = {}, [], [], [], True
    for query in family.queries:
        cursor, fetched, seen, listed = None, 0, set(), 0
        while True:
            if http.expired() and not first:
                troubles.append(OUT_OF_TIME)
                reasons.append('budget')
                break
            page, problem = family.search(http, portal, query, cursor)
            if page is None:
                if first:
                    return _unread_outcome(problem)
                troubles.append(problem[1])
                reasons.append(problem_reason(problem))
                break
            if cursor is None and page.total and not page.rows:
                # The platform reports matches but not one posting could be read from its answer.
                if first:
                    return _unread_outcome(WRONG_SHAPE)
                troubles.append(WRONG_SHAPE[1])
                reasons.append('shape')
                break
            first = False
            if page.note:
                troubles.append(page.note)
                reasons.append('shape')
            ids = [row['id'] for row in page.rows if row.get('id')]
            repeated = bool(ids) and set(ids) <= seen      # the same page again within this query
            seen.update(ids)
            for row in page.rows:
                if row.get('id') and row['id'] not in rows:   # a PRPC page may repeat Pega rows: skipped
                    rows[row['id']] = row
            fetched += len(page.rows)
            listed = max(listed, page.total or 0)     # later pages may report a smaller total, or none
            cursor = page.next
            if repeated:
                troubles.append(REPEATED)
                reasons.append('shape')
                break
            if cursor is None or not page.rows:
                if fetched < listed:
                    # The site stopped handing out pages before its own count was reached.
                    troubles.append(f'read {fetched} of {listed} listed; the site stopped paging early')
                    reasons.append('cap')
                break
            if fetched >= family.page_cap:
                troubles.append(f'stopped at {fetched} of {page.total if page.total is not None else "more"}; '
                                'raise the cap')
                reasons.append('cap')
                break
        if OUT_OF_TIME in troubles:
            break

    if not rows and not troubles:
        size, problem = family.board_size(http, portal)
        if problem is not None:
            return _unread_outcome(problem)
        if size == 0:
            return Outcome([], 0, 'error', WRONG_SITE, 'shape', False, None)
        return Outcome([], 0, None, None, '', True, True)

    pages_read = not troubles
    state = memory.state
    if pages_read:
        memory.forget_delisted(rows)
    notes.extend(family.board_notes(list(rows.values())))
    today = date.today().isoformat()

    def job_of(row, source_id=None):
        extra = {'unit': row['unit']} if row.get('unit') else None
        return make_job(SOURCE, source_id or f'{family.kind}:{identity}:{row["id"]}', row.get('title') or FALLBACK_TITLE,
                        company, family.url(portal, row), row.get('location') or '', posted_at=row.get('posted'),
                        description=row.get('description') or '', apply_url=row.get('apply_url'),
                        requisition_id=row.get('requisition') or None, employment_type=row.get('employment_type'),
                        extra=extra)

    jobs, to_read, undescribed = [], [], 0
    for row in rows.values():
        if abroad(row) or row['id'] in state['rejected']:
            continue
        stored = state['kept'].get(row['id'])
        if row.get('description'):
            if is_pega(f"{row.get('title') or ''}\n{row['description']}"):
                jobs.append(job_of(row))
        elif stored and stored in memory.known:
            jobs.append(job_of(row, stored))      # already saved with its description: kept current
        elif family.reads_details:
            to_read.append((row['id'], row))
        else:
            # No description and nothing to read it from: judged by its title, but not complete.
            undescribed += 1
            if is_pega(row.get('title') or ''):
                jobs.append(job_of(row))
    # Pega titles first, then postings an earlier run left waiting, then Indian places first.
    to_read.sort(key=lambda item: (not is_pega(item[1].get('title') or ''), item[0] not in state['backlog'],
                                   not is_india(item[1].get('location') or '')))
    budget = family.detail_cap if memory.budget is None else min(family.detail_cap, memory.budget)
    unread, waiting, retry, attempted = 0, [], [], 0
    for key, row in to_read:
        if attempted >= budget or http.expired():
            waiting.append(key)
            continue
        attempted += 1
        learnt = family.detail(http, portal, row)
        if not isinstance(learnt, dict):
            unread += 1
            retry.append(key)
            if is_pega(row.get('title') or ''):
                jobs.append(job_of(row))          # the title alone says Pega: kept without a description
            continue
        listed = row.get('location') or ''
        row = {**row, **{name: value for name, value in learnt.items() if value}}
        now = row.get('location') or ''
        if listed and now and now not in listed:
            row['location'] = f'{listed} · {now}'   # a detail naming one site must not hide the others
        if abroad(row) or not is_pega(f"{row.get('title') or ''}\n{row.get('description') or ''}"):
            state['rejected'][key] = today      # rejected for what its own page says
            continue
        job = job_of(row)
        jobs.append(job)
        state['kept'][key] = job['source_id']
        state['backlog'].pop(key, None)
    memory.wait([*waiting, *retry])
    if waiting:
        why = OUT_OF_TIME if attempted < budget else f'limit of {budget} new descriptions per board per run'
        troubles.append(f'{count_note(len(waiting))} not read yet ({why}); the next run reads them first')
        reasons.append('budget')
    if unread:
        troubles.append(f'{count_note(unread)} could not be read')
        reasons.append('')
    if undescribed:
        troubles.append(f'{count_note(undescribed)} carried no description and were judged by title only')
        reasons.append('')
    trouble = '; '.join(dict.fromkeys(troubles))
    complete_details = not (unread or waiting or undescribed)
    return Outcome(jobs, len(rows), ('partial' if trouble else None), trouble or None,
                   next((reason for reason in reasons if reason), ''), pages_read and complete_details,
                   complete_details, tuple(notes))


def result(company, outcome, requests):
    """A `make_result` dict from one `collect` outcome."""
    status = outcome.status or ('ok' if outcome.jobs else 'empty')
    made = make_result(SOURCE, company, 'ats', status=status, jobs=outcome.jobs, found=outcome.found,
                       requests=requests, error=outcome.error, reason=outcome.reason,
                       pages_complete=outcome.pages_complete, details_complete=outcome.details_complete)
    if outcome.notes:
        made['notes'] = list(outcome.notes)
    return made
