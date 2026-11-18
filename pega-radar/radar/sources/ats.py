"""Employer career sites, read through the public JSON feeds of their applicant-tracking systems.

Workday CXS, Oracle Recruiting Cloud, Greenhouse and Lever. Each adapter searches one employer's
official board and keeps postings whose title or description names Pega, unless the posting is
positively located outside India. Endpoint shapes were verified against live responses on
14 November 2026.
"""
from __future__ import annotations

import html
import re
import urllib.parse
from collections import namedtuple
from datetime import date, timedelta

from ..model import is_india, is_pega, make_job, make_result, outside_india, strip_html
from . import FALLBACK_TITLE, WRONG_SHAPE, day, failure, records

SOURCE = 'Employer site'
JSON = {'Accept': 'application/json'}
# Workday lists a multi-site posting as "2 Locations"; only its detail says whether India is one.
MULTI_LOCATION = re.compile(r'\b\d+\s+locations\b', re.I)
WORKDAY_PAGE = 20
WORKDAY_CAP = 1000
ORACLE_PAGE = 50
ORACLE_CAP = 1000
OUT_OF_TIME = 'the time budget ran out'
UNREAD = ('blocked', 'error', 'maintenance')   # outcomes in which nothing was read
WRONG_SITE = 'the career site answered but lists no jobs at all; check the site name'

# One board's outcome. `status` is None when it was read in full, else 'partial', 'blocked', 'error'
# or 'maintenance'. `reason` classifies the trouble for coverage reports (timeout, tls, dns, refused,
# rate_limited, http_4xx, http_5xx, shape, cap, budget, maintenance). `pages` is True only when the
# whole keyword listing AND every wanted description were read: only then does a posting's absence
# mean it is no longer listed. `details` is True when every wanted description was read.
Outcome = namedtuple('Outcome', 'jobs found status error reason pages details')


IDENTITY_KEYS = ('tenant', 'datacentre', 'site', 'host', 'board', 'company_id', 'org', 'org_id', 'api', 'channel',
                 'domain', 'path', 'locale_path')


def identity(portal):
    """What makes a board unique: its kind and every identity key it carries."""
    return (portal.get('kind'), *(str(portal[key]) for key in IDENTITY_KEYS if portal.get(key) not in (None, '')))


def task_name(portal):
    """Stable task id for a registry portal, e.g. 'ats:workday:cba.wd3/CommBank_Careers'.

    It names the whole board, not just its owner: run history, retry and coverage are keyed by
    task name, so a portal whose site or datacentre is edited must start again as a new task
    instead of inheriting the outcomes of a board that is no longer read.
    """
    kind = portal.get('kind')
    if kind == 'workday':
        sites = '+'.join(str(site) for site in (portal.get('site'), *(portal.get('more_sites') or [])))
        return f"ats:workday:{portal.get('tenant')}.{portal.get('datacentre')}/{sites}"
    if kind == 'oracle':
        return f"ats:oracle:{portal.get('host')}/{portal.get('site')}"
    return f"ats:{kind}:{portal.get('board')}"


def run(http, company, block, ctx=None):
    """Read one employer's board(s) as described by its registry portal.

    With a `ctx` (the scan's context) a Workday or Oracle board remembers what it has already read,
    and the return value is `(result, commit)`: `commit` stores that memory once the jobs are saved.
    """
    kind = block.get('kind')
    if kind in REMEMBERING:
        outcomes, commit = REMEMBERING[kind](http, company, block, ctx if isinstance(ctx, dict) else {})
        result = _result(company, outcomes, http.count)
        return (result, commit) if commit else result
    adapter = ADAPTERS.get(kind)
    if adapter is None:
        return make_result(SOURCE, company, 'ats', status='error', error=f'unknown ATS kind {kind!r}', reason='shape',
                           pages_complete=False, details_complete=False)
    return _result(company, adapter(http, company, block), http.count)


def _result(company, outcomes, requests):
    jobs = list({job['source_id']: job for outcome in outcomes for job in outcome.jobs}.values())
    statuses = [outcome.status for outcome in outcomes]
    if not any(statuses):
        status = 'ok' if jobs else 'empty'
    elif all(status in UNREAD for status in statuses):
        status = statuses[0] if len(set(statuses)) == 1 else 'error'
    else:
        status = 'partial'
    return make_result(SOURCE, company, 'ats', status=status, jobs=jobs, found=sum(outcome.found for outcome in outcomes),
                       requests=requests, error='; '.join(outcome.error for outcome in outcomes if outcome.error) or None,
                       reason=next((outcome.reason for outcome in outcomes if outcome.reason), ''),
                       pages_complete=all(outcome.pages for outcome in outcomes),
                       details_complete=all(outcome.details for outcome in outcomes))


def _unread(count):
    return f'{count} posting{"s" if count != 1 else ""} could not be read' if count else None


def _capped(read, total):
    return f'stopped at {read} of {total}; raise the cap'


def _problem(response):
    """`(status, error, reason)` for an unusable answer: the HTTP failure, or a 200 that is not the expected JSON."""
    if response.ok:
        return (*WRONG_SHAPE, 'shape')
    return (*failure(response), getattr(response, 'reason', '') or '')


def _unreadable(status, error, reason):
    """The outcome of a board of which nothing could be read."""
    return Outcome([], 0, status, error, reason, False, False)


def _read(jobs, found, troubles, listing_complete, details_complete):
    """The outcome of a board that was read. `troubles` are `(text, reason)` pairs; empty texts are ignored."""
    troubles = [(text, reason) for text, reason in troubles if text]
    return Outcome(jobs, found, 'partial' if troubles else None, '; '.join(text for text, _ in troubles) or None,
                   next((reason for _, reason in troubles if reason), ''),
                   listing_complete and details_complete, details_complete)


# ───────────────────────────── what a board has already read ─────────────────────────────
#
# Some boards answer a search for "Pega" with most of their postings. Reading every description
# every day would cost hundreds of requests, so each Workday or Oracle site keeps a small memory
# in kv: postings read and found irrelevant (not re-read for 45 days), postings still waiting for
# a read (taken first next time) and, where the stored id cannot be told from the listing, the id
# each kept posting was saved under. Postings already stored are returned from the listing.
#
# Only positive evidence goes into the 45-day memory: a description that was read and does not
# name Pega, or a location that is plainly abroad. A blank or failed description proves nothing,
# so that posting is retried first on the next run.

DETAIL_BUDGET = 120          # new descriptions read per board per run (config portals.detail_budget_per_board)
REJECTED_DAYS = 45           # how long a posting read and found not to be an India Pega role is not re-read
BACKLOG_DAYS = 21
BACKLOG_SIZE = 500


def _detail_budget(config):
    settings = config.get('portals') if isinstance(config, dict) else None
    try:
        return max(0, int(settings['detail_budget_per_board']))
    except (TypeError, KeyError, ValueError):
        return DETAIL_BUDGET


def _load_memory(saved):
    """`{'kept': {posting: source id}, 'rejected': {posting: day}, 'backlog': {posting: day}}`, expired entries dropped."""
    saved = saved if isinstance(saved, dict) else {}

    def section(name, days=None):
        cutoff = (date.today() - timedelta(days=days)).isoformat() if days else ''
        values = saved.get(name) if isinstance(saved.get(name), dict) else {}
        return {str(posting): value for posting, value in values.items() if isinstance(value, str) and value >= cutoff}
    return {'kept': section('kept'), 'rejected': section('rejected', REJECTED_DAYS),
            'backlog': section('backlog', BACKLOG_DAYS)}


def _remembering(ctx, sites, read_site):
    """Run `read_site(site, memory, known, budget)` for each `(kv key, site)` and return the outcomes
    with the `commit` that stores the memories (None when there is no store to keep them in)."""
    store = ctx.get('store')
    known = set(store.known_ids(SOURCE)) if store is not None else set()
    budget = _detail_budget(ctx.get('config'))
    outcomes, memories = [], {}
    for key, site in sites:
        memories[key] = _load_memory(store.kv_get(key) if store is not None else None)
        outcomes.append(read_site(site, memories[key], known, budget))

    def commit():
        for key, memory in memories.items():
            store.kv_set(key, memory)
    return outcomes, (commit if store is not None else None)


def _forget_delisted(memory, listed):
    """After a complete listing, drop what is remembered about postings that are no longer on the board."""
    for section in memory.values():
        for posting in [posting for posting in section if posting not in listed]:
            del section[posting]


def _reading_order(candidates, memory, title_of):
    """`(posting key, row)` pairs in the order their descriptions are read: Pega titles first,
    then postings an earlier run left waiting."""
    return sorted(candidates, key=lambda item: (not is_pega(str(title_of(item[1]) or '')), item[0] not in memory['backlog']))


def _still_waiting(memory, waiting, retry, attempted, budget):
    """Record the postings to read first next time and say how many were left unread; None when none were.

    `waiting` were not attempted (budget or time); `retry` were attempted but gave no usable description.
    """
    today = date.today().isoformat()
    # A waiting posting keeps the day it first waited, so the oldest are read first; the list is bounded.
    oldest_first = sorted([*waiting, *retry], key=lambda posting: memory['backlog'].get(posting, today))
    memory['backlog'] = {posting: memory['backlog'].get(posting, today) for posting in oldest_first[:BACKLOG_SIZE]}
    if not waiting:
        return None
    reason = OUT_OF_TIME if attempted < budget else f'limit of {budget} new descriptions per board per run'
    return f'{len(waiting)} postings not read yet ({reason}); the next run reads them first'


def _detail_reason(response):
    """Why a description could not be used: the request's failure, or an answer without the content."""
    return (getattr(response, 'reason', '') or '') if not response.ok else 'shape'


# ───────────────────────────── Workday (CXS public JSON) ─────────────────────────────

def _workday(http, company, block):
    return _workday_board(http, company, block, {})[0]


def _workday_board(http, company, block, ctx):
    # A few employers publish two career sites on one tenant (`more_sites`); both are searched.
    tenant, datacentre = block['tenant'], block['datacentre']
    sites = [(f'workday_state:{tenant}:{datacentre}:{site}', site) for site in [block['site'], *(block.get('more_sites') or [])]]
    return _remembering(ctx, sites, lambda site, memory, known, budget: _workday_site(
        http, company, tenant, datacentre, site, memory, known, budget))


def _workday_search(http, base, text, limit=WORKDAY_PAGE, offset=0):
    return http.post_json(base + '/jobs', {'appliedFacets': {}, 'limit': limit, 'offset': offset, 'searchText': text},
                          headers=JSON)


def _workday_page(response):
    """`(postings, total)` from a search answer, or None when it does not have the expected shape."""
    page = response.json() if response.ok else None
    if not isinstance(page, dict) or not isinstance(page.get('jobPostings'), list):
        return None
    total = page.get('total')
    return records(page['jobPostings']), total if isinstance(total, int) else 0


def _workday_site(http, company, tenant, datacentre, site, memory, known, budget):
    """One site's outcome. `memory` (see `_load_memory`) is updated in place."""
    host = f'https://{tenant}.{datacentre}.myworkdayjobs.com'
    base = f'{host}/wday/cxs/{tenant}/{site}'
    postings, offset, total, troubles = {}, 0, 0, []
    while True:
        response = _workday_search(http, base, 'Pega', offset=offset)
        if 'maintenance-page' in (response.url or ''):
            # Workday takes whole data centres offline weekly (Saturday afternoon IST).
            return _unreadable('maintenance', 'Workday maintenance window; this board is read again on the next run',
                               'maintenance')
        page = _workday_page(response)
        if page is None:
            if not offset:
                return _unreadable(*_problem(response))
            troubles.append(_problem(response)[1:])
            break
        batch, reported = page
        total = max(total, reported)   # later pages often report a total of 0
        postings.update({posting['externalPath']: posting for posting in batch if posting.get('externalPath')})
        offset += WORKDAY_PAGE
        if not batch or offset >= total:
            break
        if offset >= WORKDAY_CAP:
            troubles.append((_capped(len(postings), total), 'cap'))
            break
    listing_complete = not troubles
    if not postings and listing_complete:
        # A wrong site name still answers with zero rows, so an empty board means misconfiguration.
        probe = _workday_search(http, base, '', limit=1)
        board = _workday_page(probe)
        if board is None:
            return _unreadable(*_problem(probe))
        return _unreadable('error', WRONG_SITE, 'shape') if not board[1] and not board[0] else _read([], 0, [], True, True)
    if listing_complete:
        _forget_delisted(memory, postings)

    today = date.today().isoformat()
    jobs, to_read = [], []
    for path, posting in postings.items():
        listed = posting.get('locationsText') or ''
        # The list text is a summary; a posting is skipped unread only when it is plainly abroad.
        if (outside_india(listed) and not MULTI_LOCATION.search(listed)) or path in memory['rejected']:
            continue
        stored = memory['kept'].get(path)
        if stored in known:
            # Already saved with its description: returned from the listing so it stays current.
            requisition = stored.split(':', 2)[2]
            jobs.append(make_job(SOURCE, stored, posting.get('title') or FALLBACK_TITLE, company,
                                 f'{host}/en-US/{site}{path}', listed or 'India',
                                 requisition_id=None if requisition == path else requisition))
        else:
            to_read.append((path, posting))
    to_read = _reading_order(to_read, memory, lambda posting: posting.get('title'))

    waiting, retry, retry_reason = [], [], ''
    for position, (path, posting) in enumerate(to_read):
        if position >= budget or http.expired():
            waiting.append(path)
            continue
        listed = posting.get('locationsText') or ''
        detail = http.get(base + path)
        info = (detail.json() or {}).get('jobPostingInfo') if detail.ok else None
        if not isinstance(info, dict):
            retry.append(path)
            retry_reason = retry_reason or _detail_reason(detail)
            continue
        country = info['country'].get('descriptor') if isinstance(info.get('country'), dict) else None
        others = [str(place) for place in info.get('additionalLocations') or [] if place]
        location = ' · '.join(dict.fromkeys(str(place) for place in (info.get('location'), *others, country) if place)) or listed
        title = info.get('title') or posting.get('title') or ''
        description = strip_html(info.get('jobDescription') or '')
        if _workday_abroad(country, others, location):
            memory['rejected'][path] = today
            continue
        if not is_pega(title + ' ' + description):
            if description:
                memory['rejected'][path] = today
            else:
                # A blank description proves nothing: retried next run, never remembered as "not Pega".
                retry.append(path)
                retry_reason = retry_reason or 'shape'
            continue
        requisition = info.get('jobReqId')
        job = make_job(SOURCE, f'workday:{tenant}:{requisition or path}', title or FALLBACK_TITLE, company,
                       info.get('externalUrl') or f'{host}/en-US/{site}{path}', location or 'India',
                       posted_at=day(info.get('startDate')), description=description,
                       requisition_id=requisition, employment_type=info.get('timeType'))
        jobs.append(job)
        memory['kept'][path] = job['source_id']
    troubles.append((_still_waiting(memory, waiting, retry, len(to_read) - len(waiting), budget), 'budget'))
    troubles.append((_unread(len(retry)), retry_reason))
    return _read(jobs, len(postings), troubles, listing_complete, not waiting and not retry)


def _workday_abroad(country, others, location):
    """True only when the posting is positively outside India.

    A stated country settles it, unless another listed site is in India - or is a name this
    program does not recognise ("RMZ Ecoworld", "Embassy Tech Village"), which leaves the
    location unconfirmed and the posting kept. Without a country only a plainly foreign place
    name excludes.
    """
    if not country:
        return outside_india(location)
    if is_india(' '.join((country, *others))):
        return False
    return all(outside_india(place) for place in others)


# ───────────────────────────── Oracle Recruiting Cloud ─────────────────────────────

def _oracle_url(base, resource, expand, finder):
    return f'{base}/{resource}?{expand}&finder=' + urllib.parse.quote(finder, safe=';=,')


def _oracle_search(http, base, site, keyword, limit, offset):
    """One search page as `((requisitions, total), None)`, or `(None, (status, error, reason))` when unusable."""
    criteria = f'keyword="{keyword}",' if keyword else ''
    finder = f'findReqs;siteNumber={site},{criteria}limit={limit},offset={offset},sortBy=POSTING_DATES_DESC'
    response = http.get(_oracle_url(base, 'recruitingCEJobRequisitions',
                                    'onlyData=true&expand=requisitionList.secondaryLocations', finder))
    data = response.json() if response.ok else None
    items = data.get('items') if isinstance(data, dict) else None
    if not isinstance(items, list):
        return None, _problem(response)
    if not items:
        return ([], 0), None
    result = items[0] if isinstance(items[0], dict) else {}
    if not isinstance(result.get('requisitionList'), list):
        return None, (*WRONG_SHAPE, 'shape')
    total = result.get('TotalJobsCount')
    return (records(result['requisitionList']), total if isinstance(total, int) else 0), None


def _oracle(http, company, block):
    return _oracle_board(http, company, block, {})[0]


def _oracle_board(http, company, block, ctx):
    key = f"oracle_state:{block['host']}:{block['site']}"
    return _remembering(ctx, [(key, block['site'])], lambda site, memory, known, budget: _oracle_site(
        http, company, block['host'], site, memory, known, budget))


def _oracle_site(http, company, host, site, memory, known, budget):
    base = f'https://{host}/hcmRestApi/resources/latest'
    public = f'https://{host}/hcmUI/CandidateExperience/en/sites/{site}'
    rows, offset, troubles = [], 0, []
    while True:
        page, problem = _oracle_search(http, base, site, 'pega', ORACLE_PAGE, offset)
        if page is None:
            if not offset:
                return _unreadable(*problem)
            troubles.append(problem[1:])
            break
        batch, total = page
        rows.extend(batch)
        offset += ORACLE_PAGE
        if not batch or len(rows) >= total:
            break
        if offset >= ORACLE_CAP:
            troubles.append((_capped(len(rows), total), 'cap'))
            break
    listing_complete = not troubles
    if not rows and listing_complete:
        # As with Workday, a wrong site number answers politely with nothing.
        board, problem = _oracle_search(http, base, site, '', 1, 0)
        if board is None:
            return _unreadable(*problem)
        return _unreadable('error', WRONG_SITE, 'shape') if not board[1] and not board[0] else _read([], 0, [], True, True)
    if listing_complete:
        _forget_delisted(memory, {str(row.get('Id') or '') for row in rows})

    today = date.today().isoformat()
    jobs, to_read = [], []
    for row in rows:
        secondary = records(row.get('secondaryLocations') or [])
        sites = [(row.get('PrimaryLocation'), row.get('PrimaryLocationCountry')),
                 *((item.get('Name'), item.get('CountryCode')) for item in secondary)]
        location = ' · '.join(str(name) for name, code in sites if name)
        # A country code is decisive for its site ("Indianapolis, IN" with code US is not India).
        # A site without one is judged by its name: an Indian place keeps the posting, and so does
        # a name this program does not recognise ("RMZ Ecoworld"), which leaves the location
        # unconfirmed. The posting is skipped only when every site is positively abroad.
        india = any(code == 'IN' or (not code and is_india(name)) for name, code in sites)
        unconfirmed = any(name and not code and not outside_india(name) for name, code in sites)
        identifier = str(row.get('Id') or '')
        if (not india and not unconfirmed) or identifier in memory['rejected']:
            continue
        if f'oracle:{host}:{identifier}' in known:
            # Already saved with its description: returned from the listing so it stays current.
            jobs.append(_oracle_job(host, public, company, row, location, ''))
        else:
            to_read.append((identifier, (row, location)))
    to_read = _reading_order(to_read, memory, lambda item: item[0].get('Title'))

    waiting, retry, retry_reason = [], [], ''
    for position, (identifier, (row, location)) in enumerate(to_read):
        if position >= budget or http.expired():
            waiting.append(identifier)
            continue
        detail = http.get(_oracle_url(base, 'recruitingCEJobRequisitionDetails', 'expand=all&onlyData=true',
                                      f'ById;Id="{identifier}",siteNumber={site}'))
        items = (detail.json() or {}).get('items') if detail.ok else None
        if not items or not isinstance(items[0], dict):
            retry.append(identifier)
            retry_reason = retry_reason or _detail_reason(detail)
            continue
        description = strip_html('\n'.join(str(items[0].get(part) or '') for part in (
            'ExternalDescriptionStr', 'ExternalResponsibilitiesStr', 'ExternalQualificationsStr')))
        if not is_pega(f"{row.get('Title') or ''} {description} {row.get('ShortDescriptionStr') or ''}"):
            if description:
                memory['rejected'][identifier] = today
            else:
                # A blank description proves nothing: retried next run, never remembered as "not Pega".
                retry.append(identifier)
                retry_reason = retry_reason or 'shape'
            continue
        jobs.append(_oracle_job(host, public, company, row, location, description))
    troubles.append((_still_waiting(memory, waiting, retry, len(to_read) - len(waiting), budget), 'budget'))
    troubles.append((_unread(len(retry)), retry_reason))
    return _read(jobs, len(rows), troubles, listing_complete, not waiting and not retry)


def _oracle_job(host, public, company, row, location, description):
    identifier = str(row.get('Id') or '')
    return make_job(SOURCE, f'oracle:{host}:{identifier}', row.get('Title') or FALLBACK_TITLE, company,
                    f'{public}/job/{identifier}', location or 'India', posted_at=day(row.get('PostedDate')),
                    description=description, requisition_id=identifier)


# ───────────────────────────── Greenhouse / Lever ─────────────────────────────

def _greenhouse(http, company, block):
    board = block['board']
    response = http.get(f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true')
    data = response.json() if response.ok else None
    if not isinstance(data, dict) or not isinstance(data.get('jobs'), list):
        return [_unreadable(*_problem(response))]
    postings = records(data['jobs'])
    jobs = []
    for posting in postings:
        location = posting['location'].get('name') or '' if isinstance(posting.get('location'), dict) else ''
        offices = ' '.join(f"{office.get('name') or ''} {office.get('location') or ''}"
                           for office in records(posting.get('offices') or []))
        title = posting.get('title') or ''
        # Greenhouse delivers the description as HTML that is itself entity-escaped.
        description = strip_html(html.unescape(posting.get('content') or ''))
        if not is_pega(title + ' ' + description) or outside_india(location + ' ' + offices):
            continue
        identifier = str(posting.get('id') or '')
        jobs.append(make_job(SOURCE, f'greenhouse:{board}:{identifier}', title or FALLBACK_TITLE, company,
                             posting.get('absolute_url'), location or offices.strip() or 'India',
                             description=description,
                             posted_at=day(posting.get('first_published') or posting.get('updated_at')),
                             requisition_id=str(posting.get('requisition_id') or identifier)))
    return [_read(jobs, len(postings), [], True, True)]


def _lever(http, company, block):
    board = block['board']
    response = http.get(f'https://api.lever.co/v0/postings/{board}?mode=json')
    data = response.json() if response.ok else None
    if not isinstance(data, list):
        return [_unreadable(*_problem(response))]
    postings = records(data)
    jobs = []
    for posting in postings:
        categories = posting.get('categories') if isinstance(posting.get('categories'), dict) else {}
        places = [categories.get('location'), *(categories.get('allLocations') or [])]
        location = ' / '.join(dict.fromkeys(str(place) for place in places if place))
        lists = '\n'.join(strip_html(f"{item.get('text') or ''}\n{item.get('content') or ''}")
                          for item in records(posting.get('lists') or []))
        opening = posting.get('descriptionPlain') or strip_html(posting.get('description') or '')
        description = '\n'.join(part for part in (opening, lists, posting.get('additionalPlain')) if part).strip()
        title = posting.get('text') or ''
        # `country` is an ISO code: IN is India whatever the location text says, another code is abroad
        # unless the text names an Indian city.
        country = str(posting.get('country') or '').upper()
        abroad = country != 'IN' and not is_india(location) and (bool(country) or outside_india(location))
        if not is_pega(title + ' ' + description) or abroad:
            continue
        identifier = str(posting.get('id') or '')
        jobs.append(make_job(SOURCE, f'lever:{board}:{identifier}', title or FALLBACK_TITLE, company,
                             posting.get('hostedUrl'), location or 'India', posted_at=day(posting.get('createdAt')),
                             description=description, requisition_id=identifier,
                             employment_type=categories.get('commitment')))
    return [_read(jobs, len(postings), [], True, True)]


ADAPTERS = {'workday': _workday, 'oracle': _oracle, 'greenhouse': _greenhouse, 'lever': _lever}
# Kinds that keep a memory of what they read; called with the scan context.
REMEMBERING = {'workday': _workday_board, 'oracle': _oracle_board}
