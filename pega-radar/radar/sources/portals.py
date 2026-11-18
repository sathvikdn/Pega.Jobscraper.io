"""Every career-portal kind behind one interface: registry keys, task names, scanning and probing.

`companies.json` portals name a `kind` plus that kind's keys (`REQUIRED`, `OPTIONAL`).
`run(http, company, portal)` reads one portal and returns a `make_result()` dict; the four
original kinds (workday, oracle, greenhouse, lever) are delegated unchanged to `ats.py`, the
others to the families in `portal_api.py` and `portal_pages.py`. `probe(http, portal)` is the
bounded live check behind `radar.py verify`; it never raises.

Kinds with no standard-library adapter are listed in `UNSUPPORTED` with the reason. A portal of
such a kind is configured with `state: "unsupported"` and is not scanned; if it is run anyway
the result is an `error` naming the reason, never `empty`.
"""
from __future__ import annotations

import re
import urllib.parse

from ..model import is_pega, make_result, outside_india, strip_html
from . import ats, records
from .portal_api import FAMILIES as API_FAMILIES
from .portal_base import (SOURCE, Memory, abroad, collect, memory_key, problem_reason, requests_of,
                          response_reason, result)
from .portal_pages import FAMILIES as PAGE_FAMILIES

FAMILIES = {**API_FAMILIES, **PAGE_FAMILIES}

REQUIRED = {
    'workday': ('tenant', 'datacentre', 'site'),
    'oracle': ('host', 'site'),
    'greenhouse': ('board',),
    'lever': ('board',),
    'smartrecruiters': ('company_id',),
    'ashby': ('org',),
    'eightfold': ('host', 'domain'),
    'successfactors': ('host',),
    'phenom': ('host',),
    'talentbrew': ('host', 'org_id'),
    'icims': ('host',),
    'avature': ('host', 'path'),
    'beesite': ('api',),
}
OPTIONAL = {
    'workday': ('more_sites',),
    'eightfold': ('api',),            # 'pcsx' (default) or 'v2'
    'successfactors': ('path',),      # prefix before /search/
    'phenom': ('locale_path',),       # e.g. 'global/en'
    'talentbrew': ('locale_path',),   # e.g. 'en'
    'icims': ('path',),               # job URL prefix, e.g. 'booking'
    'avature': ('search_param',),     # e.g. 'q' when the site searches by query parameter
    'beesite': ('channel',),          # PublicationChannel.Code
}
# Keys every portal may carry whatever its kind (registry bookkeeping, not adapter settings).
COMMON_KEYS = ('kind', 'state', 'scope', 'note', 'business_unit', 'career_url')

UNSUPPORTED = {
    'peoplestrong': ('PeopleStrong candidate portals are Angular apps (<app-root>) that load jobs through an '
                     'undocumented API from JavaScript; supporting them needs a JavaScript runtime or a '
                     'published feed'),
    'ripplehire': ('RippleHire portals are opened with a per-portal ?token= and load listings by AJAX with it; '
                   'supporting them needs session/token handling, which this project does not do'),
    'icims_classic': ('classic iCIMS portals (careers-*.icims.com/jobs/search) render results in an iframe '
                      'flow with session parameters; only iCIMS Jibe sites (kind "icims") are supported'),
    'paradox': ('Paradox career sites render jobs from JavaScript; no public feed is known'),
    'taleo': ('Taleo career sections need a session-bound search; not supported'),
    'brassring': ('BrassRing (Kenexa) searches need a session-bound partner/site token; not supported'),
    'custom': ('an employer-specific site with no adapter; the careers page is listed for the user to check by hand'),
}

KINDS = tuple(REQUIRED)


def missing_keys(portal):
    """The required keys a portal lacks for its kind (all of them for an unknown kind)."""
    kind = (portal or {}).get('kind')
    if kind not in REQUIRED:
        return ['kind']
    return [key for key in REQUIRED[kind] if not portal.get(key)]


def identity(portal):
    """The board identity: the same (kind, identity) is the same board, whoever configured it."""
    kind = portal.get('kind')
    if kind in FAMILIES:
        return FAMILIES[kind].identity(portal)
    if kind == 'workday':
        # One tenant can publish several sites (Bank of America: lateral-apac and lateral-us).
        return f"{portal.get('tenant')}.{portal.get('datacentre')}/{portal.get('site')}"
    if kind == 'oracle':
        return f"{portal.get('host')}/{portal.get('site')}"
    return str(portal.get('host') or portal.get('board') or portal.get('tenant') or portal.get('url') or '')


def task_name(portal):
    """Stable task id, e.g. 'ats:phenom:careers.abb/global/en'. Matches ats.task_name for old kinds."""
    if portal.get('kind') in ats.ADAPTERS:
        return ats.task_name(portal)
    return f"ats:{portal.get('kind')}:{identity(portal)}"


def run(http, company, portal, ctx=None):
    """Read one portal. `http` is the task's request meter; the result never says `empty` for a failure.

    With a scan `ctx` that holds a store, a board of the new kinds remembers what it has read
    (see `portal_base.Memory`) and the return value is `(result, commit)`; `commit` stores that
    memory and is called by the scan once the jobs are saved. Without one the result alone is returned.
    """
    kind = (portal or {}).get('kind')
    if kind in ats.ADAPTERS:
        return ats.run(http, company, portal, ctx) if ctx is not None else ats.run(http, company, portal)
    if kind in UNSUPPORTED:
        return make_result(SOURCE, company, 'ats', status='error', error=f'unsupported portal: {UNSUPPORTED[kind]}')
    family = FAMILIES.get(kind)
    if family is None:
        return make_result(SOURCE, company, 'ats', status='error', error=f'unknown portal kind {kind!r}')
    missing = missing_keys(portal)
    if missing:
        return make_result(SOURCE, company, 'ats', status='error',
                           error=f"portal settings lack {', '.join(missing)} for kind {kind}")
    memory = Memory(ctx, memory_key(family, portal))
    outcome = result(company, collect(http, company, family, portal, memory), requests_of(http))
    return (outcome, memory.commit) if memory.store is not None else outcome


def _words(text):
    """Lower-case words of a name; punctuation (hyphens, dots, commas) only separates them."""
    return re.findall(r'[^\W_]+', str(text or '').lower())


def _names_unit(words, wanted):
    """True when the phrase `wanted` (a word list) occurs in `words` as consecutive whole words."""
    size = len(wanted)
    return bool(size) and any(words[start:start + size] == wanted for start in range(len(words) - size + 1))


def attribute(outcome, units):
    """Re-attribute the jobs of a shared board to the employers whose `business_unit` they name.

    `units` is [(employer name, business_unit text)] for the other employers on the board. A job
    goes to the employer whose business unit appears, as a run of whole words and ignoring case and
    punctuation, in the posting's own unit field (`extra['unit']`: department, organisation or
    brand): "Mobility" matches "Mercedes-Benz Mobility AG" but not "Automobility GmbH". The longest
    unit is tried first. Anything unmatched stays with the board's primary employer, the company
    the board was read for. Returns the same result dict.
    """
    pairs = [(str(name), _words(unit)) for name, unit in units or () if name and _words(unit)]
    # Longest unit first, so "Mercedes-Benz Research and Development India" wins over "Mercedes-Benz".
    pairs.sort(key=lambda pair: len(pair[1]), reverse=True)
    for job in outcome.get('jobs') or ():
        extra = job.get('extra') if isinstance(job.get('extra'), dict) else {}
        words = _words(extra.get('unit'))
        match = next((name for name, wanted in pairs if _names_unit(words, wanted)), None)
        if match:
            job['company'] = match
    return outcome


# ───────────────────────────── probes for `radar.py verify` ─────────────────────────────

def _blank():
    return {'board_ok': False, 'board_size': None, 'pega_total': None, 'india_in_first_page': 0,
            'page2_ok': None, 'detail_ok': None, 'notes': [], 'status': 'error', 'rows_parsed': 0,
            'inconclusive': False, 'passed': False, '_detail_needed': False}


def _note_problem(report, what, problem, http=None):
    report['notes'].append(f'{what}: {problem[0]}: {problem[1]}')
    if not report.get('reason'):
        reason = problem_reason(problem)
        last = getattr(http, 'last', None)
        if not reason and last is not None and not last.ok:
            reason = response_reason(last)      # ats.py's helpers return (status, message) only
        report['reason'] = reason
    if problem[0] == 'blocked':
        report['status'] = 'blocked'


def _aliases(report):
    """Fill the keys `radar/acceptance.py` records besides the brief's: `reason` and `error`."""
    report.pop('_detail_needed', None)
    report['reason'] = report.get('reason', '')
    report['error'] = None if report['status'] in ('ok', 'empty') else '; '.join(report['notes']) or report['status']
    return report


class _Recorder:
    """Passes requests through and remembers the last answer, so a probe can report its reason class."""

    def __init__(self, http):
        self._http, self.last = http, None

    def get(self, url, **options):
        self.last = self._http.get(url, **options)
        return self.last

    def post_json(self, url, payload, **options):
        self.last = self._http.post_json(url, payload, **options)
        return self.last

    def expired(self):
        return self._http.expired()


def _finish(report):
    if report['status'] != 'blocked' and report['status'] != 'unsupported':
        if not report['board_ok']:
            report['status'] = 'error'
        elif report['pega_total'] == 0:
            report['status'] = 'empty'
        else:
            report['status'] = 'ok'
    # Honest verdicts: a total without one parsed posting, or a first page with no posting that
    # could be in India, proves nothing about this adapter's India coverage.
    if report['pega_total'] and not report['rows_parsed']:
        report['inconclusive'] = True
        report['notes'].append('the site reports Pega matches but no posting could be parsed')
    elif report['rows_parsed'] and not report['india_in_first_page']:
        report['inconclusive'] = True
        report['notes'].append('no posting on the first page can be in India; the board may not cover India')
    details = report['detail_ok'] is True if report['_detail_needed'] else report['detail_ok'] is not False
    report['passed'] = bool(report['board_ok'] and report['pega_total'] is not None and report['rows_parsed']
                            and report['page2_ok'] is not False and details and not report['inconclusive'])
    return _aliases(report)


def probe(http, portal):
    """Bounded live check of one portal (at most about six requests). Never raises.

    Returns {'board_ok', 'board_size', 'pega_total', 'india_in_first_page', 'page2_ok',
    'detail_ok', 'notes', 'status', 'rows_parsed', 'inconclusive', 'passed', 'reason', 'error'};
    `status` is ok | empty | blocked | error | unsupported. `rows_parsed` counts Pega-query postings
    the adapter itself parsed from the first page. `inconclusive` is True when the site reports
    matches but none parsed, or when no first-page posting can be in India (a US-only board).
    `passed` = board_ok, a Pega total, at least one parsed posting, page 2 not failing, a successful
    detail read when descriptions must be read, and not inconclusive.
    """
    report = _blank()
    try:
        kind = (portal or {}).get('kind')
        if kind in UNSUPPORTED:
            report['status'] = 'unsupported'
            report['notes'].append(f'unsupported: {UNSUPPORTED[kind]}')
            return _aliases(report)
        missing = missing_keys(portal or {})
        if missing:
            report['notes'].append(f"portal settings lack {', '.join(missing)}")
            return _aliases(report)
        recorder = _Recorder(http)
        if kind in FAMILIES:
            _probe_family(recorder, FAMILIES[kind], portal, report)
        else:
            _ATS_PROBES[kind](recorder, portal, report)
    except Exception as error:   # a probe must never stop `verify`
        report['notes'].append(f'probe failed: {type(error).__name__}: {str(error)[:160]}')
        report['board_ok'] = False
        if report['status'] not in ('blocked', 'unsupported'):
            report['status'] = 'error'
        return _aliases(report)
    return _finish(report)


def _probe_family(http, family, portal, report):
    whole = family.queries == (None,)
    size, problem = family.board_size(http, portal)
    if problem is not None:
        _note_problem(report, 'board', problem, http)
        return
    report['board_size'] = size
    if size == 0:
        report['notes'].append('the broad search lists no jobs: wrong host, tenant or site?')
    page, problem = family.search(http, portal, None if whole else family.queries[0], None)
    if page is None:
        _note_problem(report, 'pega search', problem, http)
        return
    # A board that cannot report its size (TalentBrew) is proven by its own search page.
    report['board_ok'] = bool(size) or (size is None)
    rows = page.rows
    if whole:
        rows = [row for row in rows if is_pega(f"{row.get('title') or ''}\n{row.get('description') or ''}")]
        report['pega_total'] = len(rows)
    else:
        report['pega_total'] = page.total if page.total is not None else len(rows)
    report['rows_parsed'] = len(rows)
    report['india_in_first_page'] = sum(1 for row in rows if not abroad(row))
    if page.next is not None and not whole:
        second, problem = family.search(http, portal, family.queries[0], page.next)
        report['page2_ok'] = second is not None
        if problem is not None:
            _note_problem(report, 'page 2', problem, http)
    target = next((row for row in rows if not abroad(row)), rows[0] if rows else None)
    if target is not None and not target.get('description'):
        report['_detail_needed'] = True
        if family.reads_details:
            report['detail_ok'] = isinstance(family.detail(http, portal, target), dict)
            if not report['detail_ok']:
                report['notes'].append(f"detail of {target.get('id')} could not be read")
        else:
            report['detail_ok'] = False
            report['notes'].append(f"posting {target.get('id')} carries no description and has no detail to read")
    report['notes'].extend(family.board_notes(page.rows))


# The original kinds, probed through ats.py's own request helpers.

def _probe_workday(http, portal, report):
    tenant, datacentre, site = portal['tenant'], portal['datacentre'], portal['site']
    base = f'https://{tenant}.{datacentre}.myworkdayjobs.com/wday/cxs/{tenant}/{site}'
    response = ats._workday_search(http, base, '', limit=1)
    board = ats._workday_page(response)
    if 'maintenance-page' in (response.url or ''):
        report['notes'].append('Workday maintenance window')
        return
    if board is None:
        _note_problem(report, 'board', ats._problem(response), http)
        return
    report['board_size'] = board[1]
    report['board_ok'] = bool(board[1] or board[0])
    response = ats._workday_search(http, base, 'Pega')
    page = ats._workday_page(response)
    if page is None:
        _note_problem(report, 'pega search', ats._problem(response), http)
        return
    postings, total = page
    report['pega_total'] = total
    report['rows_parsed'] = sum(1 for posting in postings if posting.get('externalPath'))
    report['india_in_first_page'] = sum(1 for posting in postings if not outside_india(posting.get('locationsText') or ''))
    if total > ats.WORKDAY_PAGE:
        report['page2_ok'] = ats._workday_page(ats._workday_search(http, base, 'Pega', offset=ats.WORKDAY_PAGE)) is not None
    path = next((posting.get('externalPath') for posting in postings if posting.get('externalPath')), None)
    if path:
        report['_detail_needed'] = True
        detail = http.get(base + path)
        report['detail_ok'] = bool(detail.ok and isinstance((detail.json() or {}).get('jobPostingInfo'), dict))


def _probe_oracle(http, portal, report):
    host, site = portal['host'], portal['site']
    base = f'https://{host}/hcmRestApi/resources/latest'
    board, problem = ats._oracle_search(http, base, site, '', 1, 0)
    if board is None:
        _note_problem(report, 'board', problem, http)
        return
    report['board_size'] = board[1]
    report['board_ok'] = bool(board[1] or board[0])
    page, problem = ats._oracle_search(http, base, site, 'pega', ats.ORACLE_PAGE, 0)
    if page is None:
        _note_problem(report, 'pega search', problem, http)
        return
    rows, total = page
    report['pega_total'] = total
    report['rows_parsed'] = sum(1 for row in rows if row.get('Id'))
    report['india_in_first_page'] = sum(1 for row in rows if row.get('PrimaryLocationCountry') in ('IN', None, '')
                                        or any(item.get('CountryCode') == 'IN'
                                               for item in records(row.get('secondaryLocations') or [])))
    if total > ats.ORACLE_PAGE:
        report['page2_ok'] = ats._oracle_search(http, base, site, 'pega', ats.ORACLE_PAGE, ats.ORACLE_PAGE)[0] is not None
    if rows:
        report['_detail_needed'] = True
        identifier = str(rows[0].get('Id') or '')
        detail = http.get(ats._oracle_url(base, 'recruitingCEJobRequisitionDetails', 'expand=all&onlyData=true',
                                          f'ById;Id="{identifier}",siteNumber={site}'))
        items = (detail.json() or {}).get('items') if detail.ok else None
        report['detail_ok'] = bool(items) and isinstance(items[0], dict)


def _probe_feed(http, report, url, rows_of, text_of, place_of):
    response = http.get(url)
    data = response.json() if response.ok else None
    rows = rows_of(data)
    if rows is None:
        _note_problem(report, 'board', ats._problem(response), http)
        return
    report['board_size'] = len(rows)
    report['board_ok'] = bool(rows)
    pega = [row for row in rows if is_pega(text_of(row))]
    report['pega_total'] = len(pega)
    report['rows_parsed'] = len(pega)
    report['india_in_first_page'] = sum(1 for row in pega if not outside_india(place_of(row)))


def _probe_greenhouse(http, portal, report):
    _probe_feed(http, report, f"https://boards-api.greenhouse.io/v1/boards/{urllib.parse.quote(str(portal['board']))}"
                              "/jobs?content=true",
                lambda data: records(data['jobs']) if isinstance(data, dict) and isinstance(data.get('jobs'), list)
                else None,
                lambda row: f"{row.get('title') or ''} {strip_html(row.get('content') or '')}",
                lambda row: (row.get('location') or {}).get('name') or '' if isinstance(row.get('location'), dict)
                else '')


def _probe_lever(http, portal, report):
    _probe_feed(http, report, f"https://api.lever.co/v0/postings/{urllib.parse.quote(str(portal['board']))}?mode=json",
                lambda data: records(data) if isinstance(data, list) else None,
                lambda row: f"{row.get('text') or ''} {row.get('descriptionPlain') or ''}",
                lambda row: (row.get('categories') or {}).get('location') or ''
                if isinstance(row.get('categories'), dict) else '')


_ATS_PROBES = {'workday': _probe_workday, 'oracle': _probe_oracle, 'greenhouse': _probe_greenhouse,
               'lever': _probe_lever}
assert set(_ATS_PROBES) == set(ats.ADAPTERS), 'every ats.py kind needs a probe'
assert not set(FAMILIES) & set(ats.ADAPTERS)
