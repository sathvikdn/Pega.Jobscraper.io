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

# One board's outcome is `(jobs, found, status, error)`; status is None when it was read in full,
# else 'partial', 'blocked', 'error' or 'maintenance'.


def task_name(block):
    """Stable task id for a registry `ats` block, e.g. 'ats:workday:cba'."""
    kind = block.get('kind')
    return f"ats:{kind}:{block.get('tenant') or block.get('host') or block.get('board')}"


def run(http, company, block):
    """Read one employer's board(s) as described by its registry `ats` block."""
    adapter = ADAPTERS.get(block.get('kind'))
    if adapter is None:
        return make_result(SOURCE, company, 'ats', status='error', error=f"unknown ATS kind {block.get('kind')!r}")
    return _result(company, adapter(http, company, block), http.count)


def _result(company, outcomes, requests):
    jobs = list({job['source_id']: job for outcome in outcomes for job in outcome[0]}.values())
    statuses = [outcome[2] for outcome in outcomes]
    if not any(statuses):
        status = 'ok' if jobs else 'empty'
    elif all(status in UNREAD for status in statuses):
        status = statuses[0] if len(set(statuses)) == 1 else 'error'
    else:
        status = 'partial'
    return make_result(SOURCE, company, 'ats', status=status, jobs=jobs, found=sum(outcome[1] for outcome in outcomes),
                       requests=requests, error='; '.join(outcome[3] for outcome in outcomes if outcome[3]) or None)


def _unread(count):
    return f'{count} posting{"s" if count != 1 else ""} could not be read' if count else None


def _capped(read, total):
    return f'stopped at {read} of {total}; raise the cap'


def _problem(response):
    """Why a search answer is unusable: the HTTP failure, or a 200 that is not the expected JSON."""
    return failure(response) if not response.ok else WRONG_SHAPE


def _partial(jobs, found, *troubles):
    trouble = '; '.join(text for text in troubles if text)
    return jobs, found, ('partial' if trouble else None), trouble or None


# ───────────────────────────── Workday (CXS public JSON) ─────────────────────────────

def _workday(http, company, block):
    # A few employers publish two career sites on one tenant (`more_sites`); both are searched.
    sites = [block['site'], *(block.get('more_sites') or [])]
    return [_workday_site(http, company, block['tenant'], block['datacentre'], site) for site in sites]


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


def _workday_site(http, company, tenant, datacentre, site):
    host = f'https://{tenant}.{datacentre}.myworkdayjobs.com'
    base = f'{host}/wday/cxs/{tenant}/{site}'
    postings, offset, total, trouble = {}, 0, 0, None
    while True:
        response = _workday_search(http, base, 'Pega', offset=offset)
        if 'maintenance-page' in (response.url or ''):
            # Workday takes whole data centres offline weekly (Saturday afternoon IST).
            return [], 0, 'maintenance', 'Workday maintenance window; this board is read again on the next run'
        page = _workday_page(response)
        if page is None:
            if not offset:
                return [], 0, *_problem(response)
            trouble = _problem(response)[1]
            break
        batch, reported = page
        total = max(total, reported)   # later pages often report a total of 0
        postings.update({posting['externalPath']: posting for posting in batch if posting.get('externalPath')})
        offset += WORKDAY_PAGE
        if not batch or offset >= total:
            break
        if offset >= WORKDAY_CAP:
            trouble = _capped(len(postings), total)
            break
    if not postings and not trouble:
        # A wrong site name still answers with zero rows, so an empty board means misconfiguration.
        probe = _workday_search(http, base, '', limit=1)
        board = _workday_page(probe)
        if board is None:
            return [], 0, *_problem(probe)
        return [], 0, *(('error', WRONG_SITE) if not board[1] and not board[0] else (None, None))

    jobs, unread = [], 0
    for path, posting in postings.items():
        listed = posting.get('locationsText') or ''
        # The list text is a summary; a posting is skipped unread only when it is plainly abroad.
        if outside_india(listed) and not MULTI_LOCATION.search(listed):
            continue
        if http.expired():
            trouble = trouble or OUT_OF_TIME
            break
        detail = http.get(base + path)
        info = (detail.json() or {}).get('jobPostingInfo') if detail.ok else None
        if not isinstance(info, dict):
            unread += 1
            continue
        country = info['country'].get('descriptor') if isinstance(info.get('country'), dict) else None
        places = [info.get('location'), *(info.get('additionalLocations') or []), country]
        location = ' · '.join(dict.fromkeys(str(place) for place in places if place)) or listed
        title = info.get('title') or posting.get('title') or ''
        description = strip_html(info.get('jobDescription') or '')
        # A stated country settles it: abroad unless an Indian site is listed too. Without one,
        # only a plainly foreign place name excludes.
        others = ' '.join(str(place) for place in info.get('additionalLocations') or [])
        abroad = not is_india(f'{country} {others}') if country else outside_india(location)
        if not is_pega(title + ' ' + description) or abroad:
            continue
        requisition = info.get('jobReqId')
        jobs.append(make_job(SOURCE, f'workday:{tenant}:{requisition or path}', title or FALLBACK_TITLE, company,
                             info.get('externalUrl') or f'{host}/en-US/{site}{path}', location or 'India',
                             posted_at=day(info.get('startDate')), description=description,
                             requisition_id=requisition, employment_type=info.get('timeType')))
    return _partial(jobs, len(postings), trouble, _unread(unread))


# ───────────────────────────── Oracle Recruiting Cloud ─────────────────────────────

def _oracle_url(base, resource, expand, finder):
    return f'{base}/{resource}?{expand}&finder=' + urllib.parse.quote(finder, safe=';=,')


def _oracle_search(http, base, site, keyword, limit, offset):
    """One search page as `((requisitions, total), None)`, or `(None, (status, error))` when unusable."""
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
        return None, WRONG_SHAPE
    total = result.get('TotalJobsCount')
    return (records(result['requisitionList']), total if isinstance(total, int) else 0), None


def _oracle(http, company, block):
    host, site = block['host'], block['site']
    base = f'https://{host}/hcmRestApi/resources/latest'
    public = f'https://{host}/hcmUI/CandidateExperience/en/sites/{site}'
    rows, offset, trouble = [], 0, None
    while True:
        page, problem = _oracle_search(http, base, site, 'pega', ORACLE_PAGE, offset)
        if page is None:
            if not offset:
                return [([], 0, *problem)]
            trouble = problem[1]
            break
        batch, total = page
        rows.extend(batch)
        offset += ORACLE_PAGE
        if not batch or len(rows) >= total:
            break
        if offset >= ORACLE_CAP:
            trouble = _capped(len(rows), total)
            break
    if not rows and not trouble:
        # As with Workday, a wrong site number answers politely with nothing.
        board, problem = _oracle_search(http, base, site, '', 1, 0)
        if board is None:
            return [([], 0, *problem)]
        return [([], 0, *(('error', WRONG_SITE) if not board[1] and not board[0] else (None, None)))]

    jobs, unread = [], 0
    for row in rows:
        secondary = records(row.get('secondaryLocations') or [])
        sites = [(row.get('PrimaryLocation'), row.get('PrimaryLocationCountry')),
                 *((item.get('Name'), item.get('CountryCode')) for item in secondary)]
        location = ' · '.join(str(name) for name, code in sites if name)
        # A country code is decisive for its site ("Indianapolis, IN" with code US is not India);
        # a site without one is judged by its name, and only a plainly foreign name excludes.
        india = any(code == 'IN' or (not code and is_india(name)) for name, code in sites)
        if not india and (any(code for name, code in sites) or outside_india(location)):
            continue
        if http.expired():
            trouble = trouble or OUT_OF_TIME
            break
        identifier = str(row.get('Id') or '')
        detail = http.get(_oracle_url(base, 'recruitingCEJobRequisitionDetails', 'expand=all&onlyData=true',
                                      f'ById;Id="{identifier}",siteNumber={site}'))
        items = (detail.json() or {}).get('items') if detail.ok else None
        if not items or not isinstance(items[0], dict):
            unread += 1
            continue
        description = strip_html('\n'.join(str(items[0].get(part) or '') for part in (
            'ExternalDescriptionStr', 'ExternalResponsibilitiesStr', 'ExternalQualificationsStr')))
        title = row.get('Title') or ''
        if not is_pega(f"{title} {description} {row.get('ShortDescriptionStr') or ''}"):
            continue
        jobs.append(make_job(SOURCE, f'oracle:{host}:{identifier}', title or FALLBACK_TITLE, company,
                             f'{public}/job/{identifier}', location or 'India', posted_at=day(row.get('PostedDate')),
                             description=description, requisition_id=identifier))
    return [_partial(jobs, len(rows), trouble, _unread(unread))]


# ───────────────────────────── Greenhouse / Lever ─────────────────────────────

def _greenhouse(http, company, block):
    board = block['board']
    response = http.get(f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true')
    data = response.json() if response.ok else None
    if not isinstance(data, dict) or not isinstance(data.get('jobs'), list):
        return [([], 0, *_problem(response))]
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
    return [(jobs, len(postings), None, None)]


def _lever(http, company, block):
    board = block['board']
    response = http.get(f'https://api.lever.co/v0/postings/{board}?mode=json')
    data = response.json() if response.ok else None
    if not isinstance(data, list):
        return [([], 0, *_problem(response))]
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
    return [(jobs, len(postings), None, None)]


ADAPTERS = {'workday': _workday, 'oracle': _oracle, 'greenhouse': _greenhouse, 'lever': _lever}
