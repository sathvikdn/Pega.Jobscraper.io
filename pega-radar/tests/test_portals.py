"""Offline tests for the career-portal adapters (radar/sources/portals.py and its families).

Every answer comes from tests/fixtures/portals (trimmed from the 15 November 2026 captures) or
is rendered here in the platform's own format; nothing touches the network.
"""
import html
import json
import re
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

from radar.model import STATUSES
from radar.sources import Meter, ats, portals
from radar.sources import portal_api
from radar.sources.portal_base import OUT_OF_TIME, WRONG_SITE, abroad, code_from_location, when

FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'portals'
PAGE = 3          # SmartRecruiters' and Jibe's fixed page sizes, made small so scenarios page
_PATCHES = [mock.patch.object(portal_api, 'SR_PAGE', PAGE), mock.patch.object(portal_api, 'JIBE_PAGE', PAGE)]


def setUpModule():
    for patch in _PATCHES:
        patch.start()


def tearDownModule():
    for patch in _PATCHES:
        patch.stop()
SHAPE = 'unexpected response shape'


def fixture(name):
    return (FIXTURES / name).read_text(encoding='utf-8')


class Reply:
    def __init__(self, status, text='', url=''):
        self.status, self.text, self.url = status, text, url
        self.error = '' if 200 <= status < 300 else f'HTTP {status}'

    @property
    def ok(self):
        return 200 <= self.status < 300

    @property
    def blocked(self):
        return self.status in (401, 403, 406, 429, 999)

    def json(self):
        try:
            return json.loads(self.text)
        except (ValueError, TypeError):
            return None

    def header(self, name):
        return None


class FakeHttp:
    """The `radar.net.Http` interface answering from `route(url, payload)`; records every call.

    The route may return a Reply, a dict/list (JSON), an int (that status, empty body) or a str (a page).
    """

    def __init__(self, route, expired=False):
        self.route, self._expired, self.calls, self.requests = route, expired, [], 0

    def _answer(self, url, payload):
        self.calls.append(url)
        self.requests += 1
        answer = self.route(url, payload)
        if isinstance(answer, Reply):
            return answer
        if isinstance(answer, (dict, list)):
            return Reply(200, json.dumps(answer), url)
        if isinstance(answer, int):
            return Reply(answer, '', url)
        return Reply(200, answer, url)

    def get(self, url, *, headers=None, accept='application/json', retries=2):
        return self._answer(url, None)

    def post_json(self, url, payload, *, headers=None, retries=2):
        return self._answer(url, payload)

    def expired(self):
        return self._expired

    def host_open(self, host):
        return True


def params(url):
    return {key: values[0] for key, values in urllib.parse.parse_qs(urllib.parse.urlsplit(url).query,
                                                                     keep_blank_values=True).items()}


# Postings every scenario renders in its platform's format.
P_TITLE = {'id': '101', 'title': 'Pega Developer', 'city': 'Bengaluru', 'country': 'India', 'code': 'IN',
           'desc': 'Build case types in Pega Infinity.'}
P_DESC = {'id': '102', 'title': 'Senior Software Engineer', 'city': 'Hyderabad', 'country': 'India', 'code': 'IN',
          'desc': 'Experience with PRPC and Pega CSSA certification.'}
P_ABROAD = {'id': '103', 'title': 'Pega Architect', 'city': 'London', 'country': 'United Kingdom', 'code': 'GB',
            'desc': 'Pega architecture.'}
P_OTHER = {'id': '104', 'title': 'Java Developer', 'city': 'Pune', 'country': 'India', 'code': 'IN',
           'desc': 'Spring Boot microservices.'}
P_BLANK = {'id': '105', 'title': 'Pega Lead', 'city': '', 'country': '', 'code': '', 'desc': 'Lead a Pega team.'}
ALL = [P_TITLE, P_DESC, P_ABROAD, P_OTHER, P_BLANK]
KEPT = {'101', '102', '105'}


def place(posting):
    return ', '.join(part for part in (posting['city'], posting['country']) if part)


# ───────────────────────────── per-platform renderers ─────────────────────────────

class Scenario:
    """Serves one platform from `pages` (lists of postings) for the Pega query.

    `prpc` pages answer the PRPC query (none by default), `board` is the broad query's size,
    `detail` the status for detail pages (200 renders the posting), `override(url)` may answer first.
    """

    kind = ''
    portal = {}
    reads_details = True
    whole_board = False

    def __init__(self, pages=None, *, total=None, board=40, prpc=(), detail=200, override=None):
        self.pages = [list(page) for page in (pages if pages is not None else [ALL])]
        self.total = total if total is not None else sum(len(page) for page in self.pages)
        self.board, self.prpc, self.detail_status, self.override = board, list(prpc), detail, override
        self.by_id = {posting['id']: posting for page in self.pages for posting in page}
        self.by_id.update({posting['id']: posting for posting in self.prpc})

    def route(self, url, payload):
        if self.override:
            answer = self.override(url)
            if answer is not None:
                return answer
        identifier = self.detail_id(url)
        if identifier is not None:
            if self.detail_status != 200:
                return self.detail_status
            return self.render_detail(self.by_id[identifier])
        query, cursor = self.query(url)
        if query == '':
            return self.render([], self.board, None, broad=True)
        if query and query.lower() == 'prpc':
            return self.render(self.prpc, len(self.prpc), self.prpc_cursor(cursor)) if self.prpc else \
                self.render([], 0, None)
        index = self.page_index(cursor)
        rows = self.pages[index] if index < len(self.pages) else []
        return self.render(rows, self.total, index)

    def prpc_cursor(self, cursor):
        return 0

    def offset_index(self, offset):
        """Page index for an offset cursor, from the cumulative page sizes."""
        running = 0
        for index, page in enumerate(self.pages):
            if offset <= running:
                return index
            running += len(page)
        return len(self.pages)

    def source_id(self, identifier):
        if self.kind == 'phenom':
            identifier = f'ACME{identifier}EXT'
        return f'{self.kind}:{portals.identity(self.portal)}:{identifier}'


class SR(Scenario):
    kind = 'smartrecruiters'
    portal = {'kind': 'smartrecruiters', 'company_id': 'AcmeCorp'}


    def detail_id(self, url):
        match = re.search(r'/postings/([^/?]+)$', urllib.parse.urlsplit(url).path)
        return match.group(1) if match else None

    def query(self, url):
        query = params(url)
        return query.get('q', ''), int(query.get('offset', 0))

    def page_index(self, offset):
        return offset // PAGE           # SmartRecruiters' page size is patched to PAGE for these tests

    def render(self, rows, total, index, broad=False):
        return {'offset': 0, 'limit': 100, 'totalFound': total, 'content': [
            {'id': posting['id'], 'name': posting['title'], 'refNumber': 'REF' + posting['id'],
             'releasedDate': '2026-11-10T08:00:00.000Z', 'department': {'label': 'IT'},
             'location': {'city': posting['city'], 'country': posting['code'].lower()}} for posting in rows]}

    def render_detail(self, posting):
        return {'id': posting['id'], 'postingUrl': f"https://jobs.smartrecruiters.com/AcmeCorp/{posting['id']}",
                'jobAd': {'sections': {'jobDescription': {'title': 'Job', 'text': f"<p>{posting['desc']}</p>"}}}}


class AshbyScenario(Scenario):
    kind = 'ashby'
    portal = {'kind': 'ashby', 'org': 'acme'}
    reads_details = False
    whole_board = True

    def detail_id(self, url):
        return None

    def query(self, url):
        return None, None

    def page_index(self, cursor):
        return 0

    def render(self, rows, total, index, broad=False):
        rows = [posting for page in self.pages for posting in page]
        return {'apiVersion': '1', 'jobs': [
            {'id': posting['id'], 'title': posting['title'], 'location': posting['city'] or 'Remote',
             'address': {'postalAddress': {'addressCountry': posting['country']}}, 'isListed': True,
             'publishedAt': '2026-11-09T10:00:00.000+00:00', 'descriptionPlain': posting['desc'],
             'jobUrl': f"https://jobs.ashbyhq.com/acme/{posting['id']}"} for posting in rows]}


class EightfoldScenario(Scenario):
    kind = 'eightfold'
    portal = {'kind': 'eightfold', 'host': 'acme.eightfold.ai', 'domain': 'acme.com'}

    def detail_id(self, url):
        return params(url).get('position_id') if '/position_details' in url else None

    def query(self, url):
        query = params(url)
        return query.get('query', ''), int(query.get('start', 0))

    def page_index(self, start):
        return self.offset_index(start)

    def render(self, rows, total, index, broad=False):
        return {'status': 200, 'data': {'count': total, 'positions': [
            {'id': int(posting['id']), 'name': posting['title'], 'locations': [place(posting)] if place(posting) else [],
             'postedTs': 1762761600, 'department': 'Technology', 'positionUrl': f"/careers/job/{posting['id']}"}
            for posting in rows]}}

    def render_detail(self, posting):
        return {'status': 200, 'data': {'id': int(posting['id']), 'name': posting['title'],
                                        'jobDescription': f"<div>{posting['desc']}</div>"}}


class IcimsScenario(Scenario):
    kind = 'icims'
    portal = {'kind': 'icims', 'host': 'jobs.acme.com', 'path': 'acme'}
    reads_details = False


    def detail_id(self, url):
        return None

    def query(self, url):
        query = params(url)
        return query.get('keywords', ''), int(query.get('page', 1))

    def page_index(self, number):
        return number - 1

    def render(self, rows, total, index, broad=False):
        return {'totalCount': total, 'count': len(rows), 'jobs': [{'data': {
            'slug': posting['id'], 'req_id': posting['id'], 'title': posting['title'],
            'description': f"<p>{posting['desc']}</p>", 'city': posting['city'], 'country': posting['country'],
            'country_code': posting['code'], 'full_location': place(posting), 'posted_date': '2026-11-08T00:00:00+0000',
            'categories': [{'name': 'Technology'}]}} for posting in rows]}


class BeeSiteScenario(Scenario):
    kind = 'beesite'
    portal = {'kind': 'beesite', 'api': 'https://jobs-api.acme.example/search/', 'channel': '12'}
    reads_details = False

    def detail_id(self, url):
        return None

    def query(self, url):
        data = json.loads(params(url)['data'])
        keyword = next((criterion['CriterionValue'][0] for criterion in data['SearchCriteria']
                        if criterion['CriterionName'] == 'PositionFormattedDescription.Content'), '')
        return keyword, data['SearchParameters']['FirstItem'] - 1

    def page_index(self, offset):
        return self.offset_index(offset)

    def render(self, rows, total, index, broad=False):
        return {'SearchResult': {'SearchResultCount': len(rows), 'SearchResultCountAll': total, 'SearchResultItems': [
            {'MatchedObjectId': posting['id'], 'MatchedObjectDescriptor': {
                'ID': posting['id'], 'PositionID': 'R' + posting['id'], 'PositionTitle': posting['title'],
                'PositionURI': f"https://jobs.acme.example/job/{posting['id']}",
                'PositionLocation': [{'CityName': posting['city'], 'CountryName': posting['country'],
                                      'Country': posting['code']}] if posting['city'] else [],
                'PositionFormattedDescription': [{'Content': posting['desc']}],
                'PublicationStartDate': '2026-11-07'}} for posting in rows]}}


SF_SEARCH = fixture('sf_search.html')
SF_ROW = re.search(r'(?s)<tr class="data-row">.*?</tr>', SF_SEARCH).group(0)


class SFScenario(Scenario):
    kind = 'successfactors'
    portal = {'kind': 'successfactors', 'host': 'careers.acme.com'}

    def detail_id(self, url):
        match = re.search(r'/job/[^/]+/(\d+)/$', urllib.parse.urlsplit(url).path)
        return match.group(1) if match else None

    def query(self, url):
        query = params(url)
        return query.get('q', ''), int(query.get('startrow', 0))

    def page_index(self, startrow):
        return self.offset_index(startrow)

    def render(self, rows, total, index, broad=False):
        if not rows and not broad:
            return fixture('sf_noresults.html')
        if broad:
            return fixture('sf_broad.html').replace('<b>347</b>', f'<b>{total}</b>')
        body = ''.join(SF_ROW.replace('/job/Docklands-Decisioning-Lead/1370184566/', f"/job/Acme-{posting['id']}/{posting['id']}/")
                       .replace('Decisioning Lead', html.escape(posting['title']))
                       .replace('Docklands, AU', html.escape(f"{posting['city']}, {posting['code']}" if posting['city']
                                                             else '')) for posting in rows)
        page = re.sub(r'(?s)<tr class="data-row">.*?</tr>', '', SF_SEARCH)
        page = re.sub(r'(<tbody>)', r'\1' + body.replace('\\', r'\\'), page, count=1)
        return page.replace('<b>1 – 2</b> of <b>2</b>', f'<b>1 – {len(rows)}</b> of <b>{total}</b>')

    def render_detail(self, posting):
        page = fixture('sf_detail.html')
        start = page.index('itemprop="description"')
        start = page.index('>', start) + 1
        end = page.index('</div></body>')
        return page[:start] + f"<p>{html.escape(posting['desc'])}</p></span>" + page[end:]


PHENOM_SEARCH = fixture('phenom_search.html')


def phenom_page(template, jobs, total):
    start = template.index('phApp.ddo = ') + len('phApp.ddo = ')
    data, end = json.JSONDecoder().raw_decode(template, start)
    found = data['eagerLoadRefineSearch']
    found['hits'], found['totalHits'], found['data']['jobs'] = len(jobs), total, jobs
    return template[:start] + json.dumps(data) + template[end:]


class PhenomScenario(Scenario):
    kind = 'phenom'
    portal = {'kind': 'phenom', 'host': 'careers.acme.com', 'locale_path': 'global/en'}
    template = json.loads(re.search(r'"jobs": \[(\{.*?\})\], "aggregations"', PHENOM_SEARCH).group(1))

    def detail_id(self, url):
        match = re.search(r'/job/ACME(\d+)EXT/', url)
        return match.group(1) if match else None

    def query(self, url):
        query = params(url)
        return query.get('keywords', ''), int(query.get('from', 0))

    def page_index(self, offset):
        return self.offset_index(offset)

    def render(self, rows, total, index, broad=False):
        jobs = []
        for posting in rows:
            job = dict(self.template)
            location = place(posting)
            job.update({'jobSeqNo': f"ACME{posting['id']}EXT", 'jobId': 'R-' + posting['id'], 'reqId': 'R-' + posting['id'],
                        'title': posting['title'], 'country': posting['country'], 'city': posting['city'],
                        'location': location, 'cityStateCountry': location,
                        'multi_location': [location] if location else []})
            jobs.append(job)
        return phenom_page(PHENOM_SEARCH, jobs, total)

    def render_detail(self, posting):
        ddo = {'jobDetail': {'status': 200, 'data': {'job': {'title': posting['title'],
                                                             'description': f"<p>{posting['desc']}</p>"}}}}
        return f'<html><head><script>var phApp = phApp || {{}}; phApp.ddo = {json.dumps(ddo)};</script></head></html>'


TB_SEARCH = fixture('talentbrew_search.html')
TB_ITEMS = re.findall(r'(?s)<li class="search-results-list__item ">.*?</li>\s*</ul>\s*</div>\s*</li>', TB_SEARCH)


def tb_page(rows, total, page_number, pages, org='159'):
    body = ''.join(TB_ITEMS[0].replace('102794058464', posting['id'])
                   .replace('/en/job/irvine/manager-apm-business-process-and-data-lead-ats/159/',
                            f'/en/job/x/{re.sub(r"[^a-z]+", "-", posting["title"].lower())}/{org}/')
                   .replace('Manager, APM Business Process and Data Lead, ATS', html.escape(posting['title']))
                   .replace(' Irvine, CA ', ' ' + html.escape(place(posting)) + ' ') for posting in rows)
    page = TB_SEARCH
    for item in TB_ITEMS:
        page = page.replace(item, '')
    page = page.replace('data-results-count="3">', 'data-results-count="%d">' % len(rows) + body, 1)
    page = re.sub(r'data-total-results="\d+"', f'data-total-results="{total}"', page)
    page = re.sub(r'data-total-job-results="\d+"', f'data-total-job-results="{total}"', page)
    page = re.sub(r'data-total-pages="\d+"', f'data-total-pages="{pages}"', page)
    page = re.sub(r'data-current-page="\d+"', f'data-current-page="{page_number}"', page)
    return page.replace('data-organization-ids="159"', f'data-organization-ids="{org}"')


def ld_page(posting, location=None):
    data = {'@context': 'https://schema.org', '@type': 'JobPosting', 'title': posting['title'],
            'description': f"<p>{posting['desc']}</p>", 'datePosted': '2026-11-05',
            'jobLocation': {'@type': 'Place', 'address': {'addressLocality': location or posting['city'],
                                                          'addressCountry': posting['country']}}}
    return f'<html><head><script type="application/ld+json">{json.dumps(data)}</script></head><body></body></html>'


class TBScenario(Scenario):
    kind = 'talentbrew'
    portal = {'kind': 'talentbrew', 'host': 'jobs.acme.com', 'org_id': '159', 'locale_path': 'en'}

    def detail_id(self, url):
        match = re.search(r'/en/job/x/[^/]+/159/(\d+)$', url)
        return match.group(1) if match else None

    def query(self, url):
        match = re.search(r'/search-jobs/([^/]*)/159/(\d+)$', urllib.parse.urlsplit(url).path)
        return urllib.parse.unquote(match.group(1)), int(match.group(2))

    def page_index(self, number):
        return number - 1

    def render(self, rows, total, index, broad=False):
        if not rows:
            return tb_page([], 0, 1, 1)
        return tb_page(rows, total, (index or 0) + 1, len(self.pages))

    def render_detail(self, posting):
        return ld_page(posting)


AV_ZERO = fixture('avature_zero.html')


def av_page(rows, total):
    articles = ''.join(
        f'<article class="article article--result"><div class="article__header"><div class="article__header__text">'
        f'<h3 class="article__header__text__title title title--04"><a class="link" '
        f'href="https://careers.acme.com/careers/JobDetail/{re.sub(r"[^A-Za-z]+", "-", posting["title"])}/{posting["id"]}">'
        f'{html.escape(posting["title"])}</a></h3><div class="article__header__text__subtitle">'
        f'<span class="list-item-location">{html.escape(place(posting))}</span></div></div></div></article>'
        for posting in rows)
    page = AV_ZERO.replace('aria-label="0  results"', f'aria-label="{total} results"')
    if rows:
        page = re.sub(r'(?s)<article class="article article--result">.*?</article>', lambda _: articles, page)
    return page


class AvatureScenario(Scenario):
    kind = 'avature'
    portal = {'kind': 'avature', 'host': 'careers.acme.com', 'path': 'careers'}

    def detail_id(self, url):
        match = re.search(r'/JobDetail/[^/]+/(\d+)$', url)
        return match.group(1) if match else None

    def query(self, url):
        parts = urllib.parse.urlsplit(url)
        match = re.search(r'/SearchJobs(?:/([^/?]*))?$', parts.path)
        return urllib.parse.unquote(match.group(1) or ''), int(params(url).get('jobOffset', 0))

    def page_index(self, offset):
        return self.offset_index(offset)

    def render(self, rows, total, index, broad=False):
        if broad:
            return av_page(ALL[:1], total)
        return av_page(rows, total)

    def render_detail(self, posting):
        return (f'<html><body><div class="article__content__view__field"><div class="article__content__view__field__value">'
                f'<p>{html.escape(posting["desc"])}</p></div></div></body></html>')


SCENARIOS = [SR, AshbyScenario, EightfoldScenario, IcimsScenario, BeeSiteScenario, SFScenario, PhenomScenario,
             TBScenario, AvatureScenario]


def scan(scenario, portal=None, http=None):
    fake = http or FakeHttp(scenario.route)
    meter = Meter(fake)
    return portals.run(meter, 'Acme', portal or scenario.portal), fake


def ids(result):
    """The scenario posting ids kept (Phenom wraps them in a jobSeqNo such as ACME101EXT)."""
    return {re.sub(r'^ACME(\d+)EXT$', r'\1', job['source_id'].rsplit(':', 1)[1]) for job in result['jobs']}


# ───────────────────────────── behaviour every family shares ─────────────────────────────

class EveryFamilyTests(unittest.TestCase):
    def test_pega_roles_in_india_blank_or_unknown_places_are_kept(self):
        for cls in SCENARIOS:
            with self.subTest(kind=cls.kind):
                result, fake = scan(cls())
                self.assertEqual(result['status'], 'ok', result['error'])
                self.assertEqual(ids(result), KEPT)
                self.assertEqual(result['source'], 'Employer site')
                self.assertEqual(result['kind'], 'ats')
                self.assertEqual(result['label'], 'Acme')
                self.assertEqual(result['found'], 5)
                self.assertEqual(result['requests'], len(fake.calls))
                described = {re.sub(r'^ACME(\d+)EXT$', r'\1', job['source_id'].rsplit(':', 1)[1]): job
                             for job in result['jobs']}
                self.assertIn('PRPC', described['102']['description'])
                self.assertIn('Bengaluru', described['101']['location'])
                self.assertTrue(all(job['url'].startswith('https://') for job in result['jobs']))
                self.assertEqual(described['101']['company'], 'Acme')

    def test_results_carry_reason_and_completeness(self):
        for cls in SCENARIOS:
            with self.subTest(kind=cls.kind):
                result, _ = scan(cls())
                self.assertEqual((result['reason'], result['pages_complete'], result['details_complete']),
                                 ('', True, True))
                result, _ = scan(cls(override=lambda url: 503))
                self.assertEqual((result['reason'], result['pages_complete']), ('http_5xx', False))
                result, _ = scan(cls(override=lambda url: {'unexpected': True}))
                self.assertEqual(result['reason'], 'shape')
                result, _ = scan(cls([[]], total=0, board=40 if cls is not AshbyScenario else 0))
                self.assertEqual(result['pages_complete'], cls is not AshbyScenario)
                if cls.reads_details:
                    result, _ = scan(cls(detail=500))
                    self.assertEqual((result['pages_complete'], result['details_complete']), (False, False))
                if not cls.whole_board:
                    with mock.patch.object(portals.FAMILIES[cls.kind], 'page_cap', 3):
                        result, _ = scan(cls([[P_TITLE, P_DESC, P_ABROAD], [P_OTHER, P_BLANK]], total=None))
                    self.assertEqual((result['reason'], result['pages_complete']), ('cap', False))

    def test_source_ids_are_stable_and_name_the_kind_and_board(self):
        for cls in SCENARIOS:
            with self.subTest(kind=cls.kind):
                first, _ = scan(cls())
                second, _ = scan(cls())
                self.assertEqual(sorted(job['source_id'] for job in first['jobs']),
                                 sorted(job['source_id'] for job in second['jobs']))
                self.assertIn(cls().source_id('101'), {job['source_id'] for job in first['jobs']})

    def test_foreign_postings_are_not_read_in_detail(self):
        for cls in SCENARIOS:
            with self.subTest(kind=cls.kind):
                scenario = cls()
                result, fake = scan(scenario)
                details = [url for url in fake.calls if scenario.detail_id(url)]
                self.assertNotIn('103', {scenario.detail_id(url) for url in details})
                if cls.reads_details:
                    self.assertEqual({scenario.detail_id(url) for url in details}, {'101', '102', '104', '105'})

    def test_result_pages_are_merged_by_id(self):
        for cls in SCENARIOS:
            if cls.whole_board:
                continue
            with self.subTest(kind=cls.kind):
                scenario = cls([[P_TITLE, P_DESC, P_ABROAD], [P_OTHER, P_BLANK, P_TITLE]], total=None)
                result, fake = scan(scenario)
                self.assertEqual(result['status'], 'ok', result['error'])
                self.assertEqual(ids(result), KEPT)
                self.assertEqual(result['found'], 5)

    def test_stopping_at_the_cap_is_partial(self):
        for cls in SCENARIOS:
            if cls.whole_board:
                continue
            with self.subTest(kind=cls.kind):
                scenario = cls([[P_TITLE, P_DESC, P_ABROAD], [P_OTHER, P_BLANK]], total=None)
                with mock.patch.object(portals.FAMILIES[cls.kind], 'page_cap', 3):
                    result, _ = scan(scenario)
                self.assertEqual(result['status'], 'partial')
                self.assertIn('raise the cap', result['error'])
                self.assertEqual(ids(result), {'101', '102'})

    def test_a_failing_second_page_is_partial(self):
        for cls in SCENARIOS:
            if cls.whole_board:
                continue
            with self.subTest(kind=cls.kind):
                scenario = cls([[P_TITLE, P_DESC, P_ABROAD], [P_OTHER, P_BLANK]], total=None)
                calls = {'search': 0}

                def override(url, scenario=scenario):
                    if scenario.detail_id(url) is None and scenario.query(url)[0] not in ('prpc', 'PRPC'):
                        calls['search'] += 1
                        if calls['search'] == 2:
                            return 503
                    return None
                scenario.override = override
                result, _ = scan(scenario)
                self.assertEqual(result['status'], 'partial')
                self.assertEqual(ids(result), {'101', '102'})

    def test_unreadable_details_are_partial_and_only_pega_titles_survive(self):
        for cls in SCENARIOS:
            if not cls.reads_details:
                continue
            with self.subTest(kind=cls.kind):
                result, _ = scan(cls(detail=500))
                self.assertEqual(result['status'], 'partial')
                self.assertIn('4 postings could not be read', result['error'])
                self.assertEqual(ids(result), {'101', '105'})
                self.assertTrue(all(job['description'] == '' for job in result['jobs']))

    def test_the_detail_budget_is_bounded_and_reported(self):
        for cls in SCENARIOS:
            if not cls.reads_details:
                continue
            with self.subTest(kind=cls.kind):
                scenario = cls()
                with mock.patch.object(portals.FAMILIES[cls.kind], 'detail_cap', 2):
                    result, fake = scan(scenario)
                self.assertEqual(len([url for url in fake.calls if scenario.detail_id(url)]), 2)
                self.assertEqual(result['status'], 'partial')
                self.assertIn('not read yet', result['error'])
                self.assertEqual(result['reason'], 'budget')

    def test_a_refusal_is_blocked(self):
        for cls in SCENARIOS:
            with self.subTest(kind=cls.kind):
                result, fake = scan(cls(override=lambda url: 403))
                self.assertEqual(result['status'], 'blocked')
                self.assertEqual(result['jobs'], [])
                self.assertEqual(len(fake.calls), 1)

    def test_a_server_error_is_an_error(self):
        for cls in SCENARIOS:
            with self.subTest(kind=cls.kind):
                result, _ = scan(cls(override=lambda url: 503))
                self.assertEqual(result['status'], 'error')
                self.assertEqual(result['error'], 'HTTP 503')

    def test_a_200_of_the_wrong_shape_is_an_error(self):
        for cls in SCENARIOS:
            for body in ({'unexpected': True}, '<html><body><h1>Welcome</h1></body></html>', [1, 2], 'null'):
                with self.subTest(kind=cls.kind, body=str(body)[:20]):
                    result, _ = scan(cls(override=lambda url, body=body: body))
                    self.assertEqual(result['status'], 'error')
                    self.assertEqual(result['error'], SHAPE)

    def test_a_valid_search_without_matches_is_empty(self):
        for cls in SCENARIOS:
            if cls.whole_board:
                continue
            with self.subTest(kind=cls.kind):
                result, fake = scan(cls([[]], total=0, board=40))
                self.assertEqual(result['status'], 'empty', result['error'])
                self.assertEqual(result['found'], 0)

    def test_a_board_without_any_job_is_a_wrong_site_not_empty(self):
        for cls in SCENARIOS:
            if cls is TBScenario:
                continue      # TalentBrew proves its site by organisation id instead (below)
            with self.subTest(kind=cls.kind):
                result, _ = scan(cls([[]], total=0, board=0))
                self.assertEqual(result['status'], 'error')
                self.assertEqual(result['error'], WRONG_SITE)

    def test_the_prpc_query_adds_postings_where_the_search_is_literal(self):
        extra = {'id': '106', 'title': 'PRPC Engineer', 'city': 'Chennai', 'country': 'India', 'code': 'IN',
                 'desc': 'PRPC 7 upgrades.'}
        for cls in SCENARIOS:
            if cls.whole_board or portals.FAMILIES[cls.kind].queries == ('pega',):
                continue
            with self.subTest(kind=cls.kind):
                result, _ = scan(cls(prpc=[extra, P_TITLE]))
                self.assertEqual(ids(result), KEPT | {'106'})
                self.assertEqual(result['found'], 6)

    def test_running_out_of_time_mid_board_is_partial(self):
        for cls in SCENARIOS:
            if cls.whole_board:
                continue
            with self.subTest(kind=cls.kind):
                scenario = cls([[P_TITLE, P_DESC], [P_BLANK]], total=None)
                fake = FakeHttp(scenario.route)
                original = fake.route

                def route(url, payload, fake=fake):
                    answer = original(url, payload)
                    fake._expired = True       # the budget ends after the first answer
                    return answer
                fake.route = route
                result, _ = scan(scenario, http=fake)
                self.assertEqual(result['status'], 'partial')
                self.assertIn(OUT_OF_TIME, result['error'])

    def test_every_result_uses_a_known_status_and_never_raises(self):
        answers = [lambda url: 0, lambda url: 404, lambda url: '', lambda url: {'content': 'x', 'totalFound': 'x'},
                   lambda url: {'jobs': [{'data': None}], 'totalCount': 1}, lambda url: Reply(200, '{', url)]
        for cls in SCENARIOS:
            for answer in answers:
                with self.subTest(kind=cls.kind):
                    result, _ = scan(cls(override=answer))
                    self.assertIn(result['status'], STATUSES)
                    self.assertNotEqual(result['status'], 'empty')


# ───────────────────────────── platform specifics on captured pages ─────────────────────────────

class SuccessFactorsCaptureTests(unittest.TestCase):
    PORTAL = {'kind': 'successfactors', 'host': 'careers.anz.com'}

    def test_captured_matches_abroad_are_dropped_without_reading_them(self):
        def route(url, payload):
            return fixture('sf_search.html') if 'q=pega' in url else fixture('sf_noresults.html')
        result, fake = scan(None, self.PORTAL, FakeHttp(route))
        self.assertEqual(result['status'], 'empty')
        self.assertEqual(result['found'], 2)        # "Decisioning Lead", Docklands, AU and one more
        self.assertFalse([url for url in fake.calls if '/job/' in url])

    def test_the_newest_jobs_shown_under_no_results_are_not_matches(self):
        def route(url, payload):
            return fixture('sf_broad.html') if 'q=&' in url else fixture('sf_noresults.html')
        result, fake = scan(None, self.PORTAL, FakeHttp(route))
        self.assertEqual(result['status'], 'empty')
        self.assertEqual(result['found'], 0)
        self.assertFalse([url for url in fake.calls if '/job/' in url])

    def test_broad_capture_reports_the_board_size_and_india_rows(self):
        family = portals.FAMILIES['successfactors']
        page, problem = family.search(FakeHttp(lambda url, payload: fixture('sf_broad.html')), self.PORTAL, '', None)
        self.assertIsNone(problem)
        self.assertEqual(page.total, 347)
        self.assertEqual(len(page.rows), 7)
        self.assertEqual(page.next, 7)              # the site shows 7 rows a page
        self.assertEqual(page.rows[0]['location'], 'Mumbai, Maharashtra, IN')
        self.assertEqual(page.rows[0]['posted'], '2026-11-13')
        self.assertFalse(any(abroad(row) for row in page.rows))
        self.assertEqual(page.rows[0]['url'], 'https://careers.anz.com/job/Mumbai-Manager-247-Desk-Maha/1447895833/')

    def test_captured_detail_page_gives_the_description(self):
        family = portals.FAMILIES['successfactors']
        learnt = family.detail(FakeHttp(lambda url, payload: fixture('sf_detail.html')), self.PORTAL,
                               {'id': '1', 'url': 'https://jobs.example.com/job/x/1/'})
        self.assertIn('About the Role', learnt['description'])
        self.assertNotIn('<', learnt['description'])

    def test_a_path_prefix_is_used(self):
        fake = FakeHttp(lambda url, payload: fixture('sf_noresults.html'))
        scan(None, {'kind': 'successfactors', 'host': 'jobs.example.com', 'path': 'en_GB'}, fake)
        self.assertTrue(fake.calls[0].startswith('https://jobs.example.com/en_GB/search/?q=pega&startrow=0'))


class PhenomCaptureTests(unittest.TestCase):
    PORTAL = {'kind': 'phenom', 'host': 'career.lpl.com'}

    def test_the_captured_hit_abroad_is_dropped_and_not_read(self):
        result, fake = scan(None, self.PORTAL, FakeHttp(lambda url, payload: fixture('phenom_search.html')))
        self.assertEqual(result['status'], 'empty')
        self.assertEqual(result['found'], 1)
        self.assertEqual(fake.calls, ['https://career.lpl.com/search-results?keywords=pega&from=0'])

    def test_a_captured_zero_is_empty_once_the_board_is_proven(self):
        def route(url, payload):
            return fixture('phenom_zero.html') if 'keywords=' in url else phenom_page(PHENOM_SEARCH, [], 812)
        result, fake = scan(None, {'kind': 'phenom', 'host': 'careers.abb', 'locale_path': 'global/en'}, FakeHttp(route))
        self.assertEqual(result['status'], 'empty')
        self.assertEqual(fake.calls[-1], 'https://careers.abb/global/en/search-results?from=0')

    def test_job_urls_follow_the_sites_url_map(self):
        family = portals.FAMILIES['phenom']
        page, _ = family.search(FakeHttp(lambda url, payload: fixture('phenom_search.html')), self.PORTAL, 'pega', None)
        row = page.rows[0]
        self.assertEqual(row['url'], 'https://career.lpl.com/job/LFMLFFUSR054599EXTERNALENUS/svp-agent-support-enablement')
        self.assertEqual(row['requisition'], 'R-054599')
        self.assertEqual(row['posted'], '2026-11-06')
        self.assertIn('Fort Mill, South Carolina', row['location'])
        self.assertTrue(abroad(row))

    def test_an_error_status_inside_the_page_is_an_error(self):
        page = fixture('phenom_zero.html').replace('"status": 200', '"status": 500')
        result, _ = scan(None, self.PORTAL, FakeHttp(lambda url, payload: page))
        self.assertEqual((result['status'], result['error']), ('error', SHAPE))


class TalentBrewCaptureTests(unittest.TestCase):
    def test_captured_optum_results_keep_india_and_drop_california(self):
        portal = {'kind': 'talentbrew', 'host': 'careers.unitedhealthgroup.com', 'org_id': '34088'}
        posting = {'title': 'Senior Capacity-Technology Performance Management Consultant', 'city': 'Noida',
                   'country': 'India', 'desc': 'Monitor Pega and PRPC platform capacity.'}

        def route(url, payload):
            if '/search-jobs/pega/' in url:
                return fixture('talentbrew_optum.html')
            if '/search-jobs/prpc/' in url:
                return fixture('talentbrew_zero.html').replace('22908', '34088')
            return ld_page(posting, 'Noida')
        result, fake = scan(None, portal, FakeHttp(route))
        self.assertEqual(result['status'], 'ok', result['error'])
        self.assertEqual(result['found'], 2)
        [job] = result['jobs']
        self.assertEqual(job['source_id'], 'talentbrew:careers.unitedhealthgroup.com:103062906352')
        self.assertEqual(job['url'], 'https://careers.unitedhealthgroup.com/job/noida/senior-capacity-technology-'
                                     'performance-management-consultant/34088/103062906352')
        self.assertIn('Noida', job['location'])
        self.assertEqual(job['requisition_id'], '2391768')
        self.assertEqual(job['posted_at'], '2026-11-05')
        self.assertEqual(len([url for url in fake.calls if '/job/' in url]), 1)   # Cypress, California not read

    def test_captured_bd_results_abroad_are_not_read(self):
        portal = {'kind': 'talentbrew', 'host': 'jobs.bd.com', 'org_id': '159', 'locale_path': 'en'}
        family = portals.FAMILIES['talentbrew']
        page, problem = family.search(FakeHttp(lambda url, payload: fixture('talentbrew_search.html')), portal, 'pega', None)
        self.assertIsNone(problem)
        self.assertEqual(page.total, 3)
        self.assertIsNone(page.next)
        self.assertEqual([row['location'] for row in page.rows][0], 'Irvine, CA')
        self.assertTrue(abroad(page.rows[0]))

    def test_a_captured_zero_is_empty_and_a_wrong_organisation_is_an_error(self):
        zero = fixture('talentbrew_zero.html')
        result, _ = scan(None, {'kind': 'talentbrew', 'host': 'jobs.ikea.com', 'org_id': '22908', 'locale_path': 'en'},
                         FakeHttp(lambda url, payload: zero))
        self.assertEqual(result['status'], 'empty')
        result, _ = scan(None, {'kind': 'talentbrew', 'host': 'jobs.ikea.com', 'org_id': '999'},
                         FakeHttp(lambda url, payload: zero))
        self.assertEqual(result['status'], 'error')
        self.assertIn('organisation 999', result['error'])


class AvatureCaptureTests(unittest.TestCase):
    def test_a_captured_zero_is_empty_once_the_board_lists_jobs(self):
        portal = {'kind': 'avature', 'host': 'maximus.avature.net', 'path': 'careers'}

        def route(url, payload):
            if '/SearchJobs?' in url:
                return av_page([P_OTHER], 812)
            return fixture('avature_zero.html')
        result, fake = scan(None, portal, FakeHttp(route))
        self.assertEqual(result['status'], 'empty')
        self.assertEqual(fake.calls[0], 'https://maximus.avature.net/careers/SearchJobs/pega?listFilterMode=1&'
                                        'jobRecordsPerPage=50&jobOffset=0')

    def test_a_query_parameter_site_is_searched_by_parameter(self):
        fake = FakeHttp(lambda url, payload: fixture('avature_zero.html'))
        scan(None, {'kind': 'avature', 'host': 'careers.tesco.com', 'path': 'en_GB/careers',
                    'search_param': 'semanticSearch'}, fake)
        self.assertTrue(fake.calls[0].startswith('https://careers.tesco.com/en_GB/careers/SearchJobs/?semanticSearch=pega&'))


class SmartRecruitersCaptureTests(unittest.TestCase):
    def test_the_captured_zero_needs_a_live_board_to_be_empty(self):
        zero = fixture('smartrecruiters_zero.json')
        portal = {'kind': 'smartrecruiters', 'company_id': 'BoschGroup'}
        result, fake = scan(None, portal, FakeHttp(lambda url, payload: zero))
        self.assertEqual((result['status'], result['error']), ('error', WRONG_SITE))
        self.assertEqual(fake.calls[0], 'https://api.smartrecruiters.com/v1/companies/BoschGroup/postings?q=pega&'
                                        f'limit={portal_api.SR_PAGE}&offset=0')
        live = json.dumps({'offset': 0, 'limit': 100, 'totalFound': 5120, 'content': []})
        result, _ = scan(None, portal, FakeHttp(lambda url, payload: zero if 'q=' in url else live))
        self.assertEqual(result['status'], 'empty')


class EightfoldV2Tests(unittest.TestCase):
    def test_the_v2_api_is_used_when_configured(self):
        portal = {'kind': 'eightfold', 'host': 'https://careers.acme.com/careers', 'domain': 'acme.com', 'api': 'v2'}

        def route(url, payload):
            if '/api/apply/v2/jobs/7' in url:
                return {'id': 7, 'job_description': '<p>Pega CDH decisioning</p>'}
            query = params(url)
            if query.get('query') == '':
                return {'positions': [], 'count': 90}
            return {'count': 1, 'positions': [{'id': 7, 'name': 'Decisioning Engineer', 'locations': ['Bengaluru, India'],
                                               'canonicalPositionUrl': 'https://careers.acme.com/careers/job/7',
                                               't_create': 1762761600}]}
        result, fake = scan(None, portal, FakeHttp(route))
        self.assertEqual(result['status'], 'ok', result['error'])
        [job] = result['jobs']
        self.assertEqual(job['source_id'], 'eightfold:careers.acme.com:7')
        self.assertEqual(job['posted_at'], '2025-11-10')
        self.assertTrue(fake.calls[0].startswith('https://careers.acme.com/api/apply/v2/jobs?domain=acme.com&query=pega'))


# ───────────────────────────── registry, dispatch and probes ─────────────────────────────

class RegistryTests(unittest.TestCase):
    def test_every_kind_has_keys_a_family_or_an_ats_adapter(self):
        for kind in portals.REQUIRED:
            self.assertTrue(kind in portals.FAMILIES or kind in ats.ADAPTERS, kind)
        self.assertFalse(set(portals.UNSUPPORTED) & set(portals.REQUIRED))

    def test_old_kinds_keep_their_task_names_and_are_delegated(self):
        block = {'kind': 'greenhouse', 'board': 'acme'}
        self.assertEqual(portals.task_name(block), ats.task_name(block))
        fake = FakeHttp(lambda url, payload: {'jobs': []})
        result = portals.run(Meter(fake), 'Acme', block)
        self.assertEqual(result, ats.run(Meter(FakeHttp(lambda url, payload: {'jobs': []})), 'Acme', block))

    def test_task_names_and_identities(self):
        self.assertEqual(portals.task_name({'kind': 'phenom', 'host': 'careers.abb', 'locale_path': '/global/en/'}),
                         'ats:phenom:careers.abb/global/en')
        self.assertEqual(portals.identity({'kind': 'eightfold', 'host': 'https://Eaton.eightfold.ai/careers',
                                           'domain': 'eaton.com'}), 'eaton.eightfold.ai')
        self.assertEqual(portals.identity({'kind': 'beesite', 'api': 'https://api.example.com/search/'}),
                         'api.example.com')

    def test_unsupported_unknown_and_incomplete_portals_are_errors(self):
        for portal, text in (({'kind': 'peoplestrong', 'host': 'x.peoplestrong.com'}, 'unsupported portal'),
                             ({'kind': 'ripplehire'}, 'unsupported portal'),
                             ({'kind': 'nosuch'}, 'unknown portal kind'),
                             ({'kind': 'talentbrew', 'host': 'jobs.example.com'}, 'lack org_id')):
            with self.subTest(portal=portal):
                fake = FakeHttp(lambda url, payload: 200)
                result = portals.run(Meter(fake), 'Acme', portal)
                self.assertEqual(result['status'], 'error')
                self.assertIn(text, result['error'])
                self.assertEqual(fake.calls, [])

    def test_workday_and_oracle_identities_include_the_site(self):
        apac = {'kind': 'workday', 'tenant': 'ghr', 'datacentre': 'wd1', 'site': 'lateral-apac'}
        us = {**apac, 'site': 'lateral-us'}
        self.assertNotEqual(portals.identity(apac), portals.identity(us))
        self.assertEqual(portals.identity(apac), 'ghr.wd1/lateral-apac')
        self.assertEqual(portals.identity({'kind': 'oracle', 'host': 'h.oraclecloud.com', 'site': 'CX_1'}),
                         'h.oraclecloud.com/CX_1')
        # Task names follow the board (acceptance O1): editing a site gives the task a new name.
        self.assertEqual(portals.task_name(apac), 'ats:workday:ghr.wd1/lateral-apac')
        self.assertEqual(portals.task_name({**apac, 'more_sites': ['lateral-us']}),
                         'ats:workday:ghr.wd1/lateral-apac+lateral-us')
        self.assertEqual(portals.task_name({'kind': 'oracle', 'host': 'h.oraclecloud.com', 'site': 'CX_1'}),
                         'ats:oracle:h.oraclecloud.com/CX_1')
        self.assertEqual(portals.task_name(apac), ats.task_name(apac))

    def test_custom_portals_are_unsupported_and_probe_explains(self):
        portal = {'kind': 'custom', 'url': 'https://careers.example.com', 'state': 'unsupported'}
        result = portals.run(Meter(FakeHttp(lambda url, payload: 200)), 'Acme', portal)
        self.assertIn('unsupported portal', result['error'])
        report = portals.probe(FakeHttp(lambda url, payload: 200), portal)
        self.assertEqual(report['status'], 'unsupported')

    def test_shared_board_jobs_are_attributed_by_business_unit(self):
        jobs = [{'company': 'Mercedes-Benz Group', 'extra': {'unit': 'Mercedes-Benz Research and Development India'}},
                {'company': 'Mercedes-Benz Group', 'extra': {'unit': 'Mercedes-Benz Mobility AG'}},
                {'company': 'Mercedes-Benz Group', 'extra': {'unit': 'Mercedes-Benz AG'}},
                {'company': 'Mercedes-Benz Group', 'extra': {}}]
        portals.attribute({'jobs': jobs}, [('Mercedes-Benz Research and Development India',
                                            'Research and Development India'),
                                           ('Mercedes-Benz Mobility', 'Mobility'), ('Ignored', '')])
        self.assertEqual([job['company'] for job in jobs],
                         ['Mercedes-Benz Research and Development India', 'Mercedes-Benz Mobility',
                          'Mercedes-Benz Group', 'Mercedes-Benz Group'])

    def test_a_business_unit_matches_only_as_whole_words(self):
        units = [('Mercedes-Benz Research and Development India', 'Mercedes-Benz Research and Development India'),
                 ('Mercedes-Benz Mobility', 'Mercedes-Benz Mobility'), ('Mobility Co', 'Mobility')]
        cases = {'Mercedes-Benz Research and Development India Private Limited':
                 'Mercedes-Benz Research and Development India',
                 'MERCEDES BENZ RESEARCH AND DEVELOPMENT INDIA PVT. LTD.': 'Mercedes-Benz Research and Development India',
                 'Mercedes-Benz Mobility AG': 'Mercedes-Benz Mobility',
                 'Mobility Services GmbH': 'Mobility Co',
                 'Automobility GmbH': 'Primary', 'Mobilityplus AG': 'Primary', 'Mercedes-Benz AG': 'Primary',
                 'Mercedes-Benz Research India': 'Primary', '': 'Primary'}
        jobs = [{'company': 'Primary', 'extra': {'unit': unit}} for unit in cases]
        portals.attribute({'jobs': jobs}, units)
        self.assertEqual({job['extra']['unit']: job['company'] for job in jobs}, cases)

    def test_shared_board_jobs_without_a_matching_or_any_unit_stay_with_the_primary(self):
        jobs = [{'company': 'Mercedes-Benz Group', 'extra': {'unit': 'Daimler Buses GmbH'}},
                {'company': 'Mercedes-Benz Group', 'extra': {'unit': ''}},
                {'company': 'Mercedes-Benz Group', 'extra': {}},
                {'company': 'Mercedes-Benz Group', 'extra': None},
                {'company': 'Mercedes-Benz Group'}]
        result = portals.attribute({'jobs': jobs}, [('Mercedes-Benz Mobility', 'Mobility')])
        self.assertEqual({job['company'] for job in result['jobs']}, {'Mercedes-Benz Group'})
        self.assertEqual(portals.attribute({'jobs': []}, [('X', 'Y')]), {'jobs': []})
        self.assertEqual(portals.attribute({'status': 'error'}, None), {'status': 'error'})

    def test_missing_keys(self):
        self.assertEqual(portals.missing_keys({'kind': 'eightfold', 'host': 'h'}), ['domain'])
        self.assertEqual(portals.missing_keys({'kind': 'x'}), ['kind'])
        self.assertEqual(portals.missing_keys({'kind': 'lever', 'board': 'acme'}), [])


class HelperTests(unittest.TestCase):
    def test_country_codes_close_a_location_only_when_unambiguous(self):
        self.assertEqual(code_from_location('Docklands, AU'), 'AU')
        self.assertEqual(code_from_location('Curitiba, PR, BR, 80420-000'), 'BR')
        self.assertEqual(code_from_location('Mumbai, Maharashtra, IN'), '')
        self.assertEqual(code_from_location('Hosur, TN'), '')          # Tamil Nadu, not Tunisia
        self.assertEqual(code_from_location('Chandigarh, CH'), '')
        self.assertEqual(code_from_location('AU'), '')

    def test_location_evidence(self):
        self.assertTrue(abroad({'location': 'Docklands', 'country_code': 'AU'}))
        self.assertFalse(abroad({'location': 'Bengaluru · Sydney', 'country_code': 'AU'}))
        self.assertFalse(abroad({'location': '', 'country_code': ''}))
        self.assertFalse(abroad({'location': 'Remote'}))
        self.assertTrue(abroad({'location': 'Austin, Texas, United States of America'}))

    def test_dates(self):
        self.assertEqual(when('10 Nov 2026'), '2026-11-10')
        self.assertEqual(when('Nov 14, 2026'), '2026-11-14')
        self.assertEqual(when('2026-11-06T00:00:00.000+0000'), '2026-11-06')
        self.assertEqual(when(1762761600), '2025-11-10')
        self.assertEqual(when(1762761600000), '2025-11-10')
        self.assertIsNone(when('soon'))


PROBE_KEYS = {'board_ok', 'board_size', 'pega_total', 'india_in_first_page', 'page2_ok', 'detail_ok', 'notes', 'status',
              'reason', 'error', 'rows_parsed', 'inconclusive', 'passed'}


class ProbeTests(unittest.TestCase):
    def test_probe_reports_a_healthy_board(self):
        for cls in SCENARIOS:
            with self.subTest(kind=cls.kind):
                scenario = cls([[P_TITLE, P_DESC, P_ABROAD], [P_OTHER, P_BLANK]], total=None)
                fake = FakeHttp(scenario.route)
                report = portals.probe(fake, scenario.portal)
                self.assertEqual(set(report), PROBE_KEYS)
                self.assertTrue(report['board_ok'], report['notes'])
                self.assertEqual(report['status'], 'ok', report['notes'])
                self.assertTrue(report['passed'], report['notes'])
                self.assertFalse(report['inconclusive'])
                self.assertGreater(report['rows_parsed'], 0)
                self.assertLessEqual(len(fake.calls), 6)
                if cls.whole_board:
                    self.assertEqual(report['pega_total'], 4)            # 101, 102, 103 and 105 name Pega
                    self.assertEqual(report['india_in_first_page'], 3)
                    self.assertIsNone(report['page2_ok'])
                else:
                    self.assertEqual(report['india_in_first_page'], 2)   # 101 and 102; 103 is London
                    self.assertTrue(report['page2_ok'])
                if cls.reads_details:
                    self.assertTrue(report['detail_ok'])
                else:
                    self.assertIsNone(report['detail_ok'])
                if cls is not TBScenario:
                    self.assertEqual(report['board_size'], 5 if cls.whole_board else 40)

    def test_probe_never_raises_and_reports_refusals(self):
        for cls in SCENARIOS:
            with self.subTest(kind=cls.kind):
                report = portals.probe(FakeHttp(lambda url, payload: 403), cls.portal)
                self.assertEqual(report['status'], 'blocked')
                self.assertEqual(report['reason'], 'http_4xx')
                self.assertTrue(report['error'])
                self.assertFalse(report['board_ok'])
                self.assertTrue(report['notes'])

                def explode(url, payload):
                    raise RuntimeError('boom')
                report = portals.probe(FakeHttp(explode), cls.portal)
                self.assertEqual(report['status'], 'error')
                self.assertIn('probe failed', report['notes'][-1])

    def test_every_probe_failure_carries_the_reason_class(self):
        """DNS, server, refusal and wrong-shape failures keep their category for every kind."""
        every = [cls.portal for cls in SCENARIOS] + [
            {'kind': 'workday', 'tenant': 'acme', 'datacentre': 'wd3', 'site': 'External'},
            {'kind': 'oracle', 'host': 'x.fa.oraclecloud.com', 'site': 'CX_1'},
            {'kind': 'greenhouse', 'board': 'acme'}, {'kind': 'lever', 'board': 'acme'}]
        self.assertEqual({portal['kind'] for portal in every}, set(portals.REQUIRED))

        def dns(url, payload):
            reply = Reply(0, '', url)
            reply.error, reply.reason = 'URLError: [Errno 8] nodename nor servname provided', 'dns'
            return reply

        def server(url, payload):
            reply = Reply(503, '', url)
            reply.reason = 'http_5xx'
            return reply
        cases = ((dns, 'dns', 'error'), (server, 'http_5xx', 'error'), (lambda url, payload: 503, 'http_5xx', 'error'),
                 (lambda url, payload: 403, 'http_4xx', 'blocked'),
                 (lambda url, payload: '<html><body>not a career site</body></html>', 'shape', 'error'))
        for portal in every:
            for route, reason, status in cases:
                with self.subTest(kind=portal['kind'], reason=reason):
                    report = portals.probe(FakeHttp(route), portal)
                    self.assertEqual((report['reason'], report['status']), (reason, status), report['notes'])
                    self.assertFalse(report['board_ok'])
                    self.assertTrue(report['error'])

    def test_run_results_carry_the_reason_class_too(self):
        def dns(url, payload):
            reply = Reply(0, '', url)
            reply.error, reply.reason = 'URLError: name not resolved', 'dns'
            return reply
        for cls in SCENARIOS:
            with self.subTest(kind=cls.kind):
                result, _ = scan(cls(override=lambda url: dns(url, None)))
                self.assertEqual((result['status'], result['reason']), ('error', 'dns'))

    def test_probe_flags_a_wrong_site_and_an_unsupported_kind(self):
        report = portals.probe(FakeHttp(SR([[]], total=0, board=0).route), SR.portal)
        self.assertFalse(report['board_ok'])
        self.assertEqual(report['board_size'], 0)
        self.assertEqual(report['status'], 'error')
        report = portals.probe(FakeHttp(lambda url, payload: 200), {'kind': 'peoplestrong'})
        self.assertEqual(report['status'], 'unsupported')
        report = portals.probe(FakeHttp(lambda url, payload: 200), {'kind': 'oracle', 'host': 'h'})
        self.assertEqual(report['status'], 'error')
        self.assertIn('lack site', report['notes'][0])

    def test_probe_on_captured_pages(self):
        report = portals.probe(FakeHttp(lambda url, payload: fixture('sf_broad.html') if 'q=&' in url
                                        else fixture('sf_noresults.html')),
                               {'kind': 'successfactors', 'host': 'careers.vodafoneidea.com'})
        self.assertEqual((report['board_size'], report['pega_total'], report['status']), (347, 0, 'empty'))
        report = portals.probe(FakeHttp(lambda url, payload: fixture('phenom_search.html')),
                               {'kind': 'phenom', 'host': 'career.lpl.com'})
        self.assertEqual((report['pega_total'], report['india_in_first_page']), (1, 0))

    def test_probe_for_the_original_kinds(self):
        def workday(url, payload):
            if url.endswith('/job/Bengaluru/Pega-Dev_R1'):
                return {'jobPostingInfo': {'title': 'Pega Developer'}}
            if payload['searchText'] == '':
                return {'total': 900, 'jobPostings': [{'title': 'x'}]}
            postings = [{'title': 'Pega Developer', 'externalPath': '/job/Bengaluru/Pega-Dev_R1',
                         'locationsText': 'Bengaluru, India'},
                        {'title': 'Pega Lead', 'externalPath': '/job/London/Pega-Lead_R2', 'locationsText': 'London'}]
            return {'total': 25 if payload['offset'] == 0 else 0, 'jobPostings': postings}
        report = portals.probe(FakeHttp(workday), {'kind': 'workday', 'tenant': 'acme', 'datacentre': 'wd3',
                                                   'site': 'External'})
        self.assertEqual((report['board_size'], report['pega_total'], report['india_in_first_page'],
                          report['page2_ok'], report['detail_ok'], report['status']), (900, 25, 1, True, True, 'ok'))

        def oracle(url, payload):
            if 'recruitingCEJobRequisitionDetails' in url:
                return {'items': [{'ExternalDescriptionStr': 'Pega'}]}
            if 'keyword=' in urllib.parse.unquote(url):
                return {'items': [{'TotalJobsCount': 2, 'requisitionList': [
                    {'Id': '1', 'Title': 'Pega Dev', 'PrimaryLocationCountry': 'IN'},
                    {'Id': '2', 'Title': 'Pega Dev', 'PrimaryLocationCountry': 'US'}]}]}
            return {'items': [{'TotalJobsCount': 300, 'requisitionList': [{'Id': '9'}]}]}
        report = portals.probe(FakeHttp(oracle), {'kind': 'oracle', 'host': 'x.fa.oraclecloud.com', 'site': 'CX_1'})
        self.assertEqual((report['board_size'], report['pega_total'], report['india_in_first_page'],
                          report['page2_ok'], report['detail_ok']), (300, 2, 1, None, True))

        greenhouse = {'jobs': [{'title': 'Pega Developer', 'location': {'name': 'Bengaluru'}, 'content': ''},
                               {'title': 'Designer', 'location': {'name': 'Bengaluru'}, 'content': ''}]}
        report = portals.probe(FakeHttp(lambda url, payload: greenhouse), {'kind': 'greenhouse', 'board': 'acme'})
        self.assertEqual((report['board_size'], report['pega_total'], report['india_in_first_page'], report['status']),
                         (2, 1, 1, 'ok'))
        report = portals.probe(FakeHttp(lambda url, payload: []), {'kind': 'lever', 'board': 'acme'})
        self.assertEqual((report['board_ok'], report['status']), (False, 'error'))


if __name__ == '__main__':
    unittest.main()


# ───────────────────────────── engine review: completeness, memory, honesty ─────────────────────────────

class FakeStore:
    def __init__(self, known=()):
        self.kv, self.known = {}, set(known)

    def kv_get(self, key, default=None):
        return self.kv.get(key, default)

    def kv_set(self, key, value):
        self.kv[key] = json.loads(json.dumps(value))

    def known_ids(self, source, *, with_description=True):
        return set(self.known)


def posting(number, desc='Java and Spring.', title='Software Engineer', city='Bengaluru'):
    return {'id': str(200 + number), 'title': title, 'city': city, 'country': 'India', 'code': 'IN', 'desc': desc}


class CompletenessTests(unittest.TestCase):
    def test_paging_that_ends_before_the_reported_total_is_partial_cap(self):
        for cls in SCENARIOS:
            if cls.whole_board:
                continue
            with self.subTest(kind=cls.kind):
                result, _ = scan(cls([[P_TITLE, P_DESC, P_ABROAD]], total=9))
                self.assertEqual((result['status'], result['reason'], result['pages_complete']),
                                 ('partial', 'cap', False), result['error'])
                self.assertIn('read 3 of 9 listed', result['error'])
                self.assertEqual(ids(result), {'101', '102'})

    def test_icims_reading_ten_of_thirty_five_is_never_complete(self):
        class Short(IcimsScenario):
            def render(self, rows, total, index, broad=False):
                answer = super().render(rows, total, index, broad)
                answer['totalCount'] = 35 if not broad else total     # the site ignores `limit`
                return answer
        result, _ = scan(Short([[P_TITLE, P_DESC], [P_BLANK]]))
        self.assertEqual((result['status'], result['reason'], result['pages_complete']), ('partial', 'cap', False))

    def test_icims_postings_without_a_description_are_not_complete(self):
        class Bare(IcimsScenario):
            def render(self, rows, total, index, broad=False):
                answer = super().render(rows, total, index, broad)
                for job in answer['jobs']:
                    job['data']['description'] = ''
                return answer
        result, _ = scan(Bare())
        self.assertEqual(result['status'], 'partial')
        self.assertFalse(result['details_complete'])
        self.assertFalse(result['pages_complete'])
        self.assertIn('judged by title only', result['error'])
        self.assertEqual(ids(result), {'101', '105'})       # Pega titles kept; 102 needed its description
        report = portals.probe(FakeHttp(Bare().route), IcimsScenario.portal)
        self.assertEqual((report['detail_ok'], report['passed']), (False, False))

    def test_a_prpc_page_identical_to_a_pega_page_does_not_stop_the_prpc_query(self):
        from radar.sources.portal_base import Family, Page, collect

        def row(identifier):
            return {'id': identifier, 'title': 'Pega Developer', 'location': 'Pune', 'description': 'Pega'}
        pages = {('pega', None): Page([row('a'), row('b')], 3, 1), ('pega', 1): Page([row('c')], 3, None),
                 ('prpc', None): Page([row('a'), row('b')], 3, 1), ('prpc', 1): Page([row('d')], 3, None)}

        class Toy(Family):
            kind = 'toy'

            def identity(self, portal):
                return 'toy'

            def search(self, http, portal, query, cursor):
                return pages[(query, cursor)], None
        outcome = collect(FakeHttp(lambda url, payload: 200), 'Acme', Toy(), {})
        self.assertIsNone(outcome.status, outcome.error)
        self.assertEqual({job['source_id'] for job in outcome.jobs}, {'toy:toy:a', 'toy:toy:b', 'toy:toy:c', 'toy:toy:d'})
        pages[('pega', 1)] = Page([row('a'), row('b')], 3, None)    # a page repeated within one query
        outcome = collect(FakeHttp(lambda url, payload: 200), 'Acme', Toy(), {})
        self.assertEqual(outcome.status, 'partial')
        self.assertIn('same page twice', outcome.error)

    def test_beesite_without_any_organisation_says_attribution_is_unavailable(self):
        result, _ = scan(BeeSiteScenario())
        self.assertIn('organisation missing; business-unit attribution unavailable', result['notes'])
        report = portals.probe(FakeHttp(BeeSiteScenario().route), BeeSiteScenario.portal)
        self.assertIn('organisation missing; business-unit attribution unavailable', report['notes'])

        class Named(BeeSiteScenario):
            def render(self, rows, total, index, broad=False):
                answer = super().render(rows, total, index, broad)
                for item in answer['SearchResult']['SearchResultItems']:
                    item['MatchedObjectDescriptor']['OrganizationName'] = 'Acme Research India'
                return answer
        result, _ = scan(Named())
        self.assertNotIn('notes', result)
        self.assertEqual({job['extra'].get('unit') for job in result['jobs']}, {'Acme Research India'})


class TalentBrewPagingTests(unittest.TestCase):
    PORTAL = {'kind': 'talentbrew', 'host': 'jobs.bd.com', 'org_id': '159', 'locale_path': 'en'}
    PAGED = fixture('talentbrew_paged.html')
    NEXT = 'https://jobs.bd.com/en/location/india-jobs/159/1269750/2/2'

    def second_page(self):
        page = re.sub(r'(?<=/)1(\d{11})\b|(?<=data-job-id=")1(\d{11})', lambda m: '9' + (m.group(1) or m.group(2)),
                      self.PAGED)
        return re.sub(r'data-current-page="1"', 'data-current-page="3"', page)

    def test_the_next_page_is_the_pages_own_next_link(self):
        def route(url, payload):
            if url == self.NEXT:
                return self.second_page()
            if '/search-jobs/' in url:
                return self.PAGED if '/pega/' in url else fixture('talentbrew_zero.html').replace('22908', '159')
            return 404
        result, fake = scan(None, self.PORTAL, FakeHttp(route))
        self.assertEqual(fake.calls[:2], ['https://jobs.bd.com/en/search-jobs/pega/159/1', self.NEXT])
        self.assertFalse([url for url in fake.calls if '/search-jobs/pega/159/2' in url])
        self.assertGreater(result['found'], 15)          # page 2's postings were read too

    def test_an_unreadable_next_link_falls_back_and_is_partial(self):
        broken = self.PAGED.replace(f'href="{self.NEXT[len("https://jobs.bd.com"):]}"', 'href="#"')
        self.assertNotEqual(broken, self.PAGED)

        def route(url, payload):
            if url.endswith('/search-jobs/pega/159/1'):
                return broken
            if url.endswith('/search-jobs/pega/159/2'):
                return self.second_page()
            if '/search-jobs/' in url:
                return fixture('talentbrew_zero.html').replace('22908', '159')
            return 404
        result, fake = scan(None, self.PORTAL, FakeHttp(route))
        self.assertIn('https://jobs.bd.com/en/search-jobs/pega/159/2', fake.calls)
        self.assertEqual(result['status'], 'partial')
        self.assertIn('next-page link could not be read', result['error'])
        self.assertFalse(result['pages_complete'])

    def test_without_any_next_link_the_documented_pattern_is_used(self):
        pages = {1: tb_page([P_TITLE, P_DESC, P_ABROAD], 5, 1, 2), 2: tb_page([P_OTHER, P_BLANK], 5, 2, 2)}

        def route(url, payload):
            match = re.search(r'/search-jobs/pega/159/(\d+)$', url)
            if match:
                return pages[int(match.group(1))]
            if '/search-jobs/' in url:
                return tb_page([], 0, 1, 1)
            return ld_page(next(posting for posting in ALL if url.endswith('/' + posting['id'])))
        result, fake = scan(None, TBScenario.portal, FakeHttp(route))
        self.assertEqual(result['status'], 'ok', result['error'])
        self.assertIn('https://jobs.acme.com/en/search-jobs/pega/159/2', fake.calls)


class DetailMemoryTests(unittest.TestCase):
    CONFIG = {'portals': {'detail_budget_per_board': 4}}

    def run_once(self, scenario, store):
        outcome = portals.run(Meter(FakeHttp(scenario.route)), 'Acme', scenario.portal,
                              {'store': store, 'config': self.CONFIG})
        self.assertIsInstance(outcome, tuple)
        result, commit = outcome
        return result, commit

    def test_a_late_pega_role_is_reached_across_runs_without_rereading(self):
        board = [posting(number) for number in range(11)] + [posting(11, desc='Pega Constellation case design.')]
        store, read = FakeStore(), []
        for run in range(3):
            scenario = SR([board[i:i + PAGE] for i in range(0, len(board), PAGE)])
            fake = FakeHttp(scenario.route)
            result, commit = portals.run(Meter(fake), 'Acme', scenario.portal, {'store': store, 'config': self.CONFIG})
            details = [scenario.detail_id(url) for url in fake.calls if scenario.detail_id(url)]
            self.assertEqual(len(details), 4)
            self.assertFalse(set(details) & set(read), f'run {run} re-read {set(details) & set(read)}')
            read += details
            commit()
            if run < 2:
                self.assertEqual((result['status'], result['reason'], result['pages_complete']),
                                 ('partial', 'budget', False))
                self.assertIn('not read yet', result['error'])
        self.assertEqual(ids(result), {'211'})
        self.assertEqual(result['status'], 'ok', result['error'])
        self.assertTrue(result['pages_complete'])
        memory = store.kv['portal_state:smartrecruiters:AcmeCorp']
        self.assertEqual(len(memory['rejected']), 11)
        self.assertEqual(memory['kept'], {'211': 'smartrecruiters:AcmeCorp:211'})
        self.assertEqual(memory['backlog'], {})

    def test_stored_postings_are_returned_from_the_listing_and_titles_are_read_first(self):
        store = FakeStore(known={'smartrecruiters:AcmeCorp:101'})
        store.kv['portal_state:smartrecruiters:AcmeCorp'] = {'kept': {'101': 'smartrecruiters:AcmeCorp:101'},
                                                              'rejected': {}, 'backlog': {}}
        scenario = SR()
        fake = FakeHttp(scenario.route)
        result, commit = portals.run(Meter(fake), 'Acme', scenario.portal, {'store': store, 'config': {}})
        details = [scenario.detail_id(url) for url in fake.calls if scenario.detail_id(url)]
        self.assertNotIn('101', details)
        self.assertEqual(details[0], '105')                  # the other Pega title before the rest
        self.assertEqual(ids(result), KEPT)

    def test_rejections_come_only_from_descriptions_and_failed_reads_wait(self):
        store = FakeStore()
        result, commit = self.run_once(SR(detail=500), store)
        commit()
        memory = store.kv['portal_state:smartrecruiters:AcmeCorp']
        self.assertEqual(memory['rejected'], {})            # nothing was read, so nothing is judged
        self.assertEqual(set(memory['backlog']), {'101', '102', '104', '105'})
        result, commit = self.run_once(SR(), store)
        commit()
        memory = store.kv['portal_state:smartrecruiters:AcmeCorp']
        self.assertEqual(set(memory['rejected']), {'104'})  # Java Developer, rejected for its description
        self.assertEqual(memory['backlog'], {})
        self.assertEqual(ids(result), KEPT)

    def test_without_a_store_the_plain_result_is_returned(self):
        self.assertIsInstance(portals.run(Meter(FakeHttp(SR().route)), 'Acme', SR.portal, {}), dict)
        self.assertIsInstance(portals.run(Meter(FakeHttp(SR().route)), 'Acme', SR.portal), dict)


class ProbeHonestyTests(unittest.TestCase):
    def test_a_us_only_board_is_inconclusive_and_does_not_pass(self):
        for cls in SCENARIOS:
            with self.subTest(kind=cls.kind):
                report = portals.probe(FakeHttp(cls([[P_ABROAD]]).route), cls.portal)
                self.assertTrue(report['inconclusive'], report)
                self.assertFalse(report['passed'])

    def test_a_total_without_parsed_rows_is_inconclusive(self):
        answer = {'offset': 0, 'limit': 3, 'totalFound': 5, 'content': [{'name': 'no id'}]}
        report = portals.probe(FakeHttp(lambda url, payload: answer), SR.portal)
        self.assertEqual((report['pega_total'], report['rows_parsed'], report['inconclusive'], report['passed']),
                         (5, 0, True, False))

    def test_a_failed_detail_read_fails_the_probe_when_descriptions_are_needed(self):
        for cls in SCENARIOS:
            if not cls.reads_details:
                continue
            with self.subTest(kind=cls.kind):
                report = portals.probe(FakeHttp(cls(detail=500).route), cls.portal)
                self.assertEqual((report['detail_ok'], report['passed']), (False, False))

    def test_a_board_with_no_pega_match_does_not_pass(self):
        report = portals.probe(FakeHttp(SR([[]], total=0, board=40).route), SR.portal)
        self.assertEqual((report['status'], report['rows_parsed'], report['passed']), ('empty', 0, False))
