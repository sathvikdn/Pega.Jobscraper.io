"""Offline tests for the job sources. Every response comes from a fixture; nothing touches the network."""
import json
import tempfile
import unittest
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from radar.model import STATUSES, company_key, load_config, outside_india
from radar.scan import run_scan
from radar.sources import FALLBACK_TITLE, Meter, Task, ats, boards, build_tasks, linkedin
from radar.store import Store

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / 'fixtures'
BENGALURU_QUERY = 'pega|Bengaluru, Karnataka, India'
INDIA_QUERY = 'pega|India'


def fixture(name):
    return (FIXTURES / name).read_text(encoding='utf-8')


class FakeResponse:
    def __init__(self, status, text='', url='', error=''):
        self.status, self.text, self.url, self.error = status, text, url, error

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
    """The `radar.net.Http` interface, answering from `route(url, payload)` and recording every call.

    The route may return a FakeResponse, a dict or list (served as JSON), an int (that HTTP
    status with an empty body) or a str (served as a 200 page). `breaker_after` opens the
    circuit breaker for every host once that many requests have been made.
    """

    def __init__(self, route, breaker_after=None, expired=False):
        self.route, self.breaker_after, self._expired = route, breaker_after, expired
        self.calls = []
        self.requests = 0

    def _answer(self, url, payload, headers, accept):
        self.calls.append({'url': url, 'payload': payload, 'headers': headers or {}, 'accept': accept})
        self.requests += 1
        result = self.route(url, payload)
        if isinstance(result, FakeResponse):
            return result
        if isinstance(result, (dict, list)):
            return FakeResponse(200, json.dumps(result), url)
        if isinstance(result, int):
            return FakeResponse(result, '', url, f'HTTP {result}')
        return FakeResponse(200, result, url)

    def get(self, url, *, headers=None, accept='application/json', retries=2):
        return self._answer(url, None, headers, accept)

    def post_json(self, url, payload, *, headers=None, retries=2):
        return self._answer(url, payload, headers, None)

    def expired(self):
        return self._expired

    def host_open(self, url_or_host):
        return self.breaker_after is None or self.requests < self.breaker_after

    @property
    def urls(self):
        return [call['url'] for call in self.calls]


class FakeStore:
    def __init__(self, kv=None, known=()):
        self.kv, self.known = dict(kv or {}), set(known)

    def kv_get(self, key, default=None):
        return self.kv.get(key, default)

    def kv_set(self, key, value):
        self.kv[key] = json.loads(json.dumps(value))   # what is stored must survive JSON

    def known_ids(self, source, *, with_description=True):
        return set(self.known) if source == 'LinkedIn' else set()


# ───────────────────────────── LinkedIn ─────────────────────────────

def card(job_id, title, company='Acme Bank', location='Bengaluru, Karnataka, India'):
    return (f'<li><div class="base-card" data-entity-urn="urn:li:jobPosting:{job_id}">'
            f'<a class="base-card__full-link" href="https://in.linkedin.com/jobs/view/x-{job_id}?position=1"></a>'
            f'<h3 class="base-search-card__title"> {title} </h3>'
            f'<h4 class="base-search-card__subtitle"><a href="#"> {company} </a></h4>'
            f'<span class="job-search-card__location"> {location} </span>'
            f'<time class="job-search-card__listdate" datetime="2026-11-12">2 days ago</time></div></li>')


def detail(description, closed=False, location='Bengaluru, Karnataka, India'):
    return (f'<h2 class="topcard__title">T</h2><span class="topcard__flavor topcard__flavor--bullet">{location}</span>'
            '<code id="applyUrl"><!--"https://www.linkedin.com/jobs/view/externalApply/1'
            '?url=https%3A%2F%2Fcareers.acme.example%2Fjob%2F9"--></code>'
            '<figcaption class="num-applicants__caption">Over 200 applicants</figcaption>'
            f'<div class="show-more-less-html__markup">{description}</div><button>Show more</button>'
            + ('<p>No longer accepting applications</p>' if closed else ''))


def search_route(pages, details=None):
    """LinkedIn answers: `pages[(location, start)]` for searches, `details[id]` for postings (404 otherwise)."""
    def route(url, payload):
        if 'seeMoreJobPostings' in url:
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            return pages.get((query['location'][0], int(query['start'][0])), '')
        return (details or {}).get(url.rsplit('/', 1)[1], 404)
    return route


def searched(http):
    """`(location, start)` of every search request, in order."""
    found = []
    for url in http.urls:
        if 'seeMoreJobPostings' in url:
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            found.append((query['location'][0], int(query['start'][0])))
    return found


def detailed(http):
    """Posting ids whose description was requested, in order."""
    return [url.rsplit('/', 1)[1] for url in http.urls if '/jobPosting/' in url]


def sweep(http, store=None, companies=(), window_days=3, profile=None, commit=True, **settings):
    """One LinkedIn run. `commit=False` models a run whose jobs were never saved."""
    store = store if store is not None else FakeStore()
    config = {'linkedin': {'keywords': ['pega'], 'other_cities': [], **settings}, 'profile': profile or {}}
    result, save_state = linkedin.run(Meter(http), {'window_days': window_days, 'store': store, 'config': config},
                                      companies)
    if commit:
        save_state()
    return result


class LinkedInParsingTests(unittest.TestCase):
    def test_cards_are_parsed(self):
        cards = linkedin.parse_cards(card('101', 'Senior Pega Developer') + card('102', 'Java Engineer') + '<li>ad</li>')
        self.assertEqual([c['id'] for c in cards], ['101', '102'])
        self.assertEqual((cards[0]['title'], cards[0]['company'], cards[0]['location'], cards[0]['posted_at']),
                         ('Senior Pega Developer', 'Acme Bank', 'Bengaluru, Karnataka, India', '2026-11-12'))

    def test_detail_is_parsed(self):
        parsed = linkedin.parse_detail(detail('<p>Build Pega case types.</p><ul><li>4+ years</li></ul>'))
        self.assertIn('Build Pega case types.', parsed['description'])
        self.assertIn('4+ years', parsed['description'])
        self.assertEqual(parsed['apply_url'], 'https://careers.acme.example/job/9')
        self.assertEqual(parsed['applicants'], 'Over 200 applicants')
        self.assertEqual(parsed['location'], 'Bengaluru, Karnataka, India')
        self.assertFalse(parsed['closed'])
        self.assertTrue(linkedin.parse_detail(detail('x', closed=True))['closed'])

    def test_apply_link_must_be_http(self):
        page = '<code id="applyUrl"><!--"https://www.linkedin.com/x?url=javascript%3Aalert(1)"--></code>'
        self.assertIsNone(linkedin.parse_detail(page)['apply_url'])


class LinkedInPlanTests(unittest.TestCase):
    def test_plan_is_bengaluru_first_then_india_then_cities_then_employers(self):
        companies = [{'name': 'Mega Services', 'type': 'services', 'bengaluru': True, 'linkedin_query': True},
                     {'name': 'Acme Bank', 'type': 'gcc', 'bengaluru': True, 'linkedin_query': True},
                     {'name': 'Quiet Corp', 'type': 'gcc', 'bengaluru': True, 'linkedin_query': False}]
        plan = linkedin.query_plan({'keywords': ['pega', 'pega developer'],
                                    'other_cities': ['Pune, Maharashtra, India']}, companies)
        self.assertEqual([(query.keywords, query.location) for query in plan], [
            ('pega', 'Bengaluru, Karnataka, India'), ('pega developer', 'Bengaluru, Karnataka, India'),
            ('pega', 'India'), ('pega developer', 'India'),
            ('pega', 'Pune, Maharashtra, India'), ('pega developer', 'Pune, Maharashtra, India'),
            ('pega Acme Bank', 'India'), ('pega Mega Services', 'India')])
        self.assertEqual(len({query.id for query in plan}), len(plan))
        # Employer queries are short: one quiet page ends them.
        self.assertEqual((plan[0].quiet_pages, plan[-1].quiet_pages), (3, 1))

    def test_the_users_own_employer_is_not_searched(self):
        companies = [{'name': 'Mercedes-Benz Research and Development India', 'aliases': ['MBRDI'], 'type': 'gcc',
                      'bengaluru': True, 'linkedin_query': True},
                     {'name': 'Acme Bank', 'type': 'gcc', 'bengaluru': True, 'linkedin_query': True},
                     {'name': 'Home Corp', 'type': 'gcc', 'bengaluru': True, 'linkedin_query': True,
                      'current_employer': True}]
        plan = linkedin.query_plan({'keywords': ['pega'], 'other_cities': []}, companies, 'Mercedes-Benz')
        self.assertEqual([query.keywords for query in plan], ['pega', 'pega', 'pega Acme Bank'])
        # A name that merely starts with the same letters is a different employer.
        plan = linkedin.query_plan({'keywords': ['pega'], 'other_cities': []}, companies[1:2], 'Acme')
        self.assertEqual(len(plan), 2)
        plan = linkedin.query_plan({'keywords': ['pega'], 'other_cities': []}, companies[1:2], 'Ac')
        self.assertEqual(len(plan), 3)

    def test_default_plan_covers_every_keyword_and_city_without_bare_prpc(self):
        plan = linkedin.query_plan({}, [])
        self.assertEqual(len(plan), len(linkedin.DEFAULT_KEYWORDS) * (2 + len(linkedin.DEFAULT_OTHER_CITIES)))
        self.assertTrue(all(query.location == linkedin.BENGALURU for query in plan[:len(linkedin.DEFAULT_KEYWORDS)]))
        self.assertNotIn('prpc', [keyword.lower() for keyword in linkedin.DEFAULT_KEYWORDS])

    def test_queries_are_sent_in_plan_order_with_the_look_back_window(self):
        http = FakeHttp(search_route({}))
        result = sweep(http, window_days=5)
        self.assertEqual(searched(http), [('Bengaluru, Karnataka, India', 0), ('India', 0)])
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(http.urls[0]).query)
        self.assertEqual((query['f_TPR'], query['sortBy'], query['keywords']), (['r432000'], ['DD'], ['pega']))
        self.assertEqual((result['status'], result['kind'], result['source'], result['requests']),
                         ('empty', 'linkedin', 'LinkedIn', 2))


class LinkedInSweepTests(unittest.TestCase):
    def test_title_and_description_matches_are_kept_and_paging_stops_on_filler(self):
        # The offset advances by the number of cards each page actually returned.
        pages = {('India', 0): card('1', 'Pega Developer') + card('2', 'Software Engineer III'),
                 ('India', 2): card('3', 'Java Developer'), ('India', 3): card('4', 'Python Developer'),
                 ('India', 4): card('5', 'Go Developer'), ('India', 5): card('6', 'Pega Architect')}
        details = {'1': detail('Develop Pega applications. 4-6 years.'),
                   '2': detail('You will implement Pega PRPC workflows.'), '3': detail('Java only.')}
        http, store = FakeHttp(search_route(pages, details)), FakeStore()
        result = sweep(http, store)
        self.assertEqual(sorted(job['title'] for job in result['jobs']), ['Pega Developer', 'Software Engineer III'])
        # Three filler pages in a row end the query, so the page at offset 5 is never requested.
        self.assertEqual(searched(http)[1:], [('India', 0), ('India', 2), ('India', 3), ('India', 4)])
        self.assertEqual((result['status'], result['found'], result['kept'], result['error']), ('ok', 5, 2, None))
        described = next(job for job in result['jobs'] if job['title'] == 'Software Engineer III')
        self.assertEqual((described['source'], described['source_id'], described['url']),
                         ('LinkedIn', '2', 'https://www.linkedin.com/jobs/view/2'))
        self.assertIn('Pega PRPC workflows', described['description'])
        self.assertEqual(described['apply_url'], 'https://careers.acme.example/job/9')
        self.assertEqual(described['extra'], {'applicants': 'Over 200 applicants', 'title_match': False})
        self.assertEqual(described['posted_at'], '2026-11-12')
        # Posting 3 sat inside the relevant zone, was read and is remembered as not Pega;
        # posting 4 was already in the filler and is not read at all.
        self.assertEqual(detailed(http), ['1', '2', '3'])
        self.assertEqual(store.kv['linkedin_rejected'], {'3': date.today().isoformat()})
        self.assertIsNone(store.kv['linkedin_checkpoint'])

    def test_a_400_past_the_last_result_ends_the_query_normally(self):
        def route(url, payload):
            if 'seeMoreJobPostings' in url:
                return card('1', 'Pega Developer') if url.endswith('start=0') else 400
            return detail('Pega work')
        store = FakeStore()
        result = sweep(FakeHttp(route), store)
        self.assertEqual((result['status'], result['kept']), ('ok', 1))
        self.assertIsNone(store.kv['linkedin_checkpoint'])

    def test_closed_and_foreign_postings_are_dropped_and_known_ids_not_refetched(self):
        pages = {('India', 0): card('1', 'Pega Developer') + card('2', 'Pega Lead', location='Whitefield')
                 + card('3', 'Pega Engineer') + card('4', 'Pega Analyst', location='India')
                 + card('5', 'Pega Tester', location='London Area')}
        details = {'1': detail('Pega work', closed=True), '2': detail('Pega work', location=''),
                   '4': detail('Pega work', location='Dublin, Ireland'), '5': detail('Pega work', location='Remote')}
        http, store = FakeHttp(search_route(pages, details)), FakeStore(known={'3'})
        result = sweep(http, store)
        # 1 is closed and 4 is abroad on its own page. 3 is already stored with its description.
        # 2 and 5 stay: the search was scoped to India, so odd card text is no reason to drop them.
        self.assertEqual([job['title'] for job in result['jobs']], ['Pega Lead', 'Pega Engineer', 'Pega Tester'])
        self.assertEqual([job['location'] for job in result['jobs']], ['Whitefield', 'Bengaluru, Karnataka, India', 'Remote'])
        self.assertEqual(result['jobs'][1]['description'], '')
        self.assertEqual(detailed(http), ['1', '2', '4', '5'])
        self.assertEqual(set(store.kv['linkedin_rejected']), {'1', '4'})
        self.assertEqual(result['status'], 'ok')

    def test_descriptions_are_read_bengaluru_first_within_the_budget(self):
        pages = {('India', 0): card('11', 'Pega Developer', location='Pune, Maharashtra, India')
                 + card('12', 'Software Engineer')
                 + card('13', 'Pega Lead')
                 + card('14', 'Pega Architect', company='PayPal', location='Hyderabad, Telangana, India')
                 + card('15', 'Pega Consultant', company='PayPal')}
        companies = [{'name': 'PayPal', 'type': 'product', 'bengaluru': True, 'linkedin_query': False}]
        route = search_route(pages, {str(key): detail('Pega work') for key in range(11, 16)})
        http = FakeHttp(route)
        result = sweep(http, companies=companies)
        # Pega titles in Bengaluru (product employer first), Pega titles elsewhere, then untitled candidates.
        self.assertEqual(detailed(http), ['15', '13', '14', '11', '12'])
        self.assertEqual(result['status'], 'ok')

        http, store = FakeHttp(route), FakeStore()
        result = sweep(http, store, companies=companies, detail_budget=3)
        self.assertEqual(detailed(http), ['15', '13', '14'])
        self.assertEqual(result['status'], 'partial')
        self.assertIn('2 descriptions not read yet', result['error'])
        # The unread Pega title is still reported from its card; the unread untitled candidate is not guessed at.
        self.assertEqual(sorted(job['source_id'] for job in result['jobs']), ['11', '13', '14', '15'])
        self.assertEqual(store.kv['linkedin_rejected'], {})
        # Both unread postings wait in the backlog and are read before anything else next time.
        self.assertEqual(sorted(store.kv['linkedin_backlog']), ['11', '12'])
        http = FakeHttp(search_route({('India', 0): card('20', 'Pega Developer')},
                                     {'11': detail('Pega work'), '12': detail('Our Pega team'), '20': detail('Pega')}))
        result = sweep(http, store, companies=companies)
        self.assertEqual(detailed(http), ['11', '12', '20'])
        self.assertEqual((result['status'], sorted(job['source_id'] for job in result['jobs'])), ('ok', ['11', '12', '20']))
        self.assertTrue(all(job['description'] for job in result['jobs']))
        self.assertEqual(store.kv['linkedin_backlog'], {})

    def test_rejected_postings_are_not_read_again_until_they_expire(self):
        old = (date.today() - timedelta(days=60)).isoformat()
        store = FakeStore(kv={'linkedin_rejected': {'7': date.today().isoformat(), '8': old}})
        pages = {('India', 0): card('7', 'Pega Developer') + card('8', 'Pega Lead')}
        http = FakeHttp(search_route(pages, {'8': detail('Pega work')}))
        result = sweep(http, store)
        self.assertEqual(detailed(http), ['8'])
        self.assertEqual([job['source_id'] for job in result['jobs']], ['8'])
        self.assertEqual(set(store.kv['linkedin_rejected']), {'7'})

    def test_an_unparsed_description_is_not_remembered_as_not_pega(self):
        pages = {('India', 0): card('1', 'Pega Developer') + card('2', 'Software Engineer')}
        store = FakeStore()
        result = sweep(FakeHttp(search_route(pages, {'1': detail('Pega'), '2': '<html>new layout</html>'})), store)
        self.assertEqual([job['source_id'] for job in result['jobs']], ['1'])
        self.assertEqual(store.kv['linkedin_rejected'], {})
        # It is not dropped either: it waits in the backlog for another try.
        self.assertEqual(list(store.kv['linkedin_backlog']), ['2'])
        self.assertEqual((result['status'], result['error']), ('ok', None))

    def test_a_description_that_fails_to_load_is_retried_then_counted_but_not_stored(self):
        pages = {('India', 0): card('1', 'Pega Developer') + card('2', 'Software Engineer')}
        store = FakeStore()
        for attempt in (1, 2, 3):
            http = FakeHttp(search_route(pages if attempt == 1 else {}, {'1': detail('Pega work'), '2': 500}))
            result = sweep(http, store)
            self.assertEqual(result['status'], 'partial', attempt)
            self.assertIn('1 descriptions failed to load', result['error'])
            self.assertIn('2', detailed(http))
            self.assertEqual(list(store.kv['linkedin_backlog']), ['2'] if attempt < 3 else [], attempt)
            # Its title does not name Pega, so without a description it is never stored as a job;
            # when it is given up the result says so.
            self.assertNotIn('2', [job['source_id'] for job in result['jobs']])
            self.assertEqual('1 description-only candidates could not be read and were not kept' in result['error'],
                             attempt == 3, attempt)
        self.assertEqual(list(store.kv['linkedin_unreadable']), ['2'])
        http = FakeHttp(search_route(pages, {'1': detail('Pega work'), '2': 500}))
        result = sweep(http, store)
        self.assertEqual((result['status'], [job['source_id'] for job in result['jobs']], detailed(http)),
                         ('ok', ['1'], ['1']))

    def test_dead_description_pages_of_other_roles_store_no_job(self):
        pages = {('India', 0): card('1', 'Pega Developer') + card('2', 'Java Developer') + card('3', 'SAP Consultant')}
        store = FakeStore()
        result = sweep(FakeHttp(search_route(pages, {'1': 404, '2': 404, '3': 410})), store)
        self.assertEqual([job['title'] for job in result['jobs']], ['Pega Developer'])
        # The run is not partial for pages that will never load, but the count is not hidden either.
        self.assertEqual((result['status'], result['error']),
                         ('ok', '2 description-only candidates could not be read and were not kept'))
        self.assertEqual(sorted(store.kv['linkedin_unreadable']), ['1', '2', '3'])
        http = FakeHttp(search_route(pages))
        result = sweep(http, store)
        self.assertEqual(([job['title'] for job in result['jobs']], result['error'], detailed(http)),
                         (['Pega Developer'], None, []))

    def test_a_removed_posting_never_keeps_the_sweep_partial(self):
        # Eight daily runs; the description of posting 1 answers 404 forever, posting 2 has lost its markup.
        pages = {('India', 0): card('1', 'Pega Developer') + card('2', 'Pega Lead') + card('3', 'Pega Architect')}
        details = {'2': '<html>no description here</html>', '3': detail('Pega work')}
        store = FakeStore()
        requested = []
        for run in range(1, 9):
            http = FakeHttp(search_route(pages, details))
            result = sweep(http, store)
            store.known.add('3')   # the scan saved it with its description
            requested += detailed(http)
            self.assertEqual((result['status'], result['error'], result['sweep_complete']), ('ok', None, True), run)
            # Both are still handed over from their cards on every run.
            self.assertEqual(sorted((job['source_id'], job['description']) for job in result['jobs']),
                             [('1', ''), ('2', ''), ('3', 'Pega work' if run == 1 else '')], run)
        self.assertEqual(sorted(requested), ['1', '2', '2', '2', '3'])
        self.assertEqual((sorted(store.kv['linkedin_unreadable']), store.kv['linkedin_backlog'],
                          store.kv['linkedin_rejected'], store.kv['linkedin_checkpoint']), (['1', '2'], {}, {}, None))

    def test_the_backlog_stays_bounded_when_descriptions_are_refused_every_run(self):
        store = FakeStore()
        returned = []
        with mock.patch.object(linkedin, 'BACKLOG_SIZE', 5):
            for run in range(6):
                pages = {('India', 0): ''.join(card(f'{run}{n}', 'Software Engineer') for n in range(3))
                         + card(f'{run}9', 'Pega Developer')}
                result = sweep(FakeHttp(search_route(pages, {f'{r}{n}': 429 for r in range(6) for n in (0, 1, 2, 9)})), store)
                self.assertEqual(result['status'], 'partial', run)
                self.assertLessEqual(len(store.kv['linkedin_backlog']), 5, run)
                returned += [job['source_id'] for job in result['jobs']]
                self.assertTrue(all(job['extra']['title_match'] for job in result['jobs']), run)
        # Whatever was pushed out is not queued again. Only postings with a Pega title were ever
        # returned: the "Software Engineer" cards were counted, not stored.
        self.assertEqual(len(store.kv['linkedin_backlog']), 5)
        pushed_out = set(store.kv['linkedin_unreadable'])
        self.assertEqual(len(pushed_out), 6 * 4 - 5)
        self.assertEqual(set(returned), {f'{run}9' for run in range(6)})
        self.assertFalse(pushed_out & set(store.kv['linkedin_backlog']))
        self.assertIn('description-only candidates could not be read and were not kept', result['error'])

    def test_a_large_backlog_overflow_stores_no_unverified_job(self):
        entry = {'company': 'Acme', 'location': 'Pune', 'posted_at': None, 'tries': 0, 'since': date.today().isoformat()}
        backlog = {str(1000 + n): dict(entry, title='BPM Engineer', title_match=False) for n in range(690)}
        backlog.update({str(5000 + n): dict(entry, title='Pega Developer', title_match=True) for n in range(10)})
        store = FakeStore(kv={'linkedin_backlog': backlog})
        result = sweep(FakeHttp(lambda url, payload: 429 if '/jobPosting/' in url else ''), store)
        # 700 waiting, room for 500: every Pega title is returned, no "BPM Engineer" is.
        self.assertEqual(sorted(job['title'] for job in result['jobs']), ['Pega Developer'] * 10)
        self.assertEqual(len(store.kv['linkedin_backlog']), 500)
        self.assertIn('description-only candidates could not be read and were not kept', result['error'])

    def test_backlog_entries_older_than_three_weeks_are_handed_over_and_dropped(self):
        old = (date.today() - timedelta(days=30)).isoformat()
        recent = (date.today() - timedelta(days=3)).isoformat()
        entry = {'title': 'Software Engineer', 'company': 'Acme', 'location': 'Pune', 'posted_at': None,
                 'title_match': False, 'tries': 0}
        store = FakeStore(kv={'linkedin_backlog': {'70': dict(entry, since=old), '71': dict(entry, since=recent)}})
        http = FakeHttp(search_route({}, {'71': detail('Pega PRPC')}))
        result = sweep(http, store)
        self.assertEqual(detailed(http), ['71'])
        # 70 has no Pega title and was never read: it is dropped and counted, not stored.
        self.assertEqual([(job['source_id'], bool(job['description'])) for job in result['jobs']], [('71', True)])
        self.assertEqual((result['status'], result['error']),
                         ('ok', '1 description-only candidates could not be read and were not kept'))
        self.assertEqual((store.kv['linkedin_backlog'], list(store.kv['linkedin_unreadable'])), ({}, ['70']))
        self.assertEqual(sweep(FakeHttp(search_route({})), store)['jobs'], [])
        # An aged-out posting that does name Pega is still handed over from its card.
        store = FakeStore(kv={'linkedin_backlog': {'72': dict(entry, title='Pega Developer', title_match=True, since=old)}})
        http = FakeHttp(search_route({}))
        result = sweep(http, store)
        self.assertEqual(([job['source_id'] for job in result['jobs']], result['error'], detailed(http)), (['72'], None, []))

    def test_a_card_without_a_title_is_judged_by_its_description(self):
        untitled = card('9', 'X').replace('<h3 class="base-search-card__title"> X </h3>', '')
        pages = {('India', 0): card('1', 'Pega Developer') + untitled}
        result = sweep(FakeHttp(search_route(pages, {'1': detail('Pega'), '9': detail('Pega CSSA needed')})))
        self.assertEqual([(job['source_id'], job['title']) for job in result['jobs']],
                         [('1', 'Pega Developer'), ('9', FALLBACK_TITLE)])

    def test_saved_state_of_the_wrong_type_and_a_bad_budget_are_ignored(self):
        pages = {('India', 0): card('1', 'Pega Developer')}
        for junk in ('text', [1, 2], 7, {'1': 5}, {'1': ['x']}):
            store = FakeStore(kv={'linkedin_rejected': junk, 'linkedin_checkpoint': junk, 'linkedin_backlog': junk,
                                  'linkedin_unreadable': junk})
            result = sweep(FakeHttp(search_route(pages, {'1': detail('Pega')})), store, detail_budget='plenty')
            self.assertEqual((result['status'], result['kept']), ('ok', 1), junk)
        ctx = {'window_days': None, 'store': FakeStore(), 'config': {'linkedin': 'x', 'profile': ['y']}}
        http = FakeHttp(lambda url, payload: '')
        self.assertEqual(linkedin.run(Meter(http), ctx, [])[0]['status'], 'empty')
        self.assertEqual(len(http.urls), len(linkedin.query_plan({}, [])))


class LinkedInResilienceTests(unittest.TestCase):
    def test_finished_queries_are_skipped_when_a_run_resumes(self):
        recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(timespec='seconds')
        store = FakeStore(kv={'linkedin_checkpoint': {'window_started': recent, 'done': [BENGALURU_QUERY]}})
        http = FakeHttp(search_route({}))
        result = sweep(http, store)
        self.assertEqual(searched(http), [('India', 0)])
        self.assertEqual(result['status'], 'empty')
        # Every query is now finished, so the next run starts a fresh sweep.
        self.assertIsNone(store.kv['linkedin_checkpoint'])

    def test_a_checkpoint_from_yesterday_is_ignored(self):
        stale = (datetime.now(timezone.utc) - timedelta(hours=21)).isoformat(timespec='seconds')
        for saved in ({'window_started': stale, 'done': [BENGALURU_QUERY]}, {'done': 'corrupt'}, 'corrupt'):
            http = FakeHttp(search_route({}))
            sweep(http, FakeStore(kv={'linkedin_checkpoint': saved}))
            self.assertEqual(searched(http), [('Bengaluru, Karnataka, India', 0), ('India', 0)])

    def test_an_open_breaker_stops_the_sweep_and_the_run_is_partial(self):
        pages = {('Bengaluru, Karnataka, India', 0): card('1', 'Pega Developer')}
        # Two requests finish the Bengaluru query; then LinkedIn's breaker opens.
        http, store = FakeHttp(search_route(pages, {'1': detail('Pega work')}), breaker_after=2), FakeStore()
        result = sweep(http, store)
        self.assertEqual(searched(http), [('Bengaluru, Karnataka, India', 0), ('Bengaluru, Karnataka, India', 1)])
        self.assertEqual(detailed(http), [])
        self.assertEqual(result['status'], 'partial')
        self.assertIn('1 of 2 searches not finished', result['error'])
        self.assertEqual([job['source_id'] for job in result['jobs']], ['1'])
        self.assertEqual(store.kv['linkedin_checkpoint']['done'], [BENGALURU_QUERY])

        self.assertEqual(list(store.kv['linkedin_backlog']), ['1'])

        # The resumed run only does what is left, starting with the description it still owes.
        resumed = FakeHttp(search_route(pages, {'1': detail('Pega work')}))
        result = sweep(resumed, store)
        self.assertEqual(searched(resumed), [('India', 0)])
        self.assertEqual(detailed(resumed), ['1'])
        self.assertEqual((result['status'], [job['description'] for job in result['jobs']]), ('ok', ['Pega work']))
        self.assertIsNone(store.kv['linkedin_checkpoint'])

    def test_a_run_whose_jobs_were_not_saved_leaves_no_trace_and_is_repeated_in_full(self):
        pages = {('Bengaluru, Karnataka, India', 0): card('1', 'Pega Developer') + card('2', 'Java Developer'),
                 ('India', 0): 503}
        details = {'1': detail('Pega'), '2': detail('Java only')}
        store = FakeStore()
        first = FakeHttp(search_route(pages, details))
        result = sweep(first, store, commit=False)      # killed, or the save failed: commit never happens
        self.assertEqual((result['status'], result['kept'], result['sweep_complete']), ('partial', 1, False))
        self.assertEqual(store.kv, {})
        second = FakeHttp(search_route(pages, details))
        self.assertEqual(sweep(second, store)['kept'], 1)
        self.assertEqual(second.urls, first.urls)       # nothing was believed done, so everything is read again
        self.assertEqual(sorted(store.kv), ['linkedin_backlog', 'linkedin_checkpoint', 'linkedin_rejected',
                                            'linkedin_unreadable'])
        self.assertEqual((store.kv['linkedin_checkpoint']['done'], list(store.kv['linkedin_rejected'])),
                         ([BENGALURU_QUERY], ['2']))

    def test_pages_without_cards_are_a_failure_not_the_end_of_the_results(self):
        wall = '<html><body><form class="login">Sign in to view more jobs</form></body></html>'
        store = FakeStore()
        result = sweep(FakeHttp(lambda url, payload: wall), store)
        self.assertEqual((result['status'], result['jobs']), ('error', []))
        self.assertIn('no job cards; markup changed or sign-in wall', result['error'])
        self.assertEqual(store.kv['linkedin_checkpoint']['done'], [])

        pages = {('Bengaluru, Karnataka, India', 0): card('1', 'Pega Developer'), ('India', 0): wall}
        result = sweep(FakeHttp(search_route(pages, {'1': detail('Pega')})), store)
        self.assertEqual((result['status'], result['kept']), ('partial', 1))
        self.assertIn('1 of 2 searches not finished', result['error'])
        self.assertEqual(store.kv['linkedin_checkpoint']['done'], [BENGALURU_QUERY])

    def test_a_query_cut_off_by_the_page_limit_is_partial_and_not_checkpointed(self):
        def route(url, payload):
            if 'seeMoreJobPostings' not in url:
                return detail('Pega')
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            start = query['start'][0]
            return card('7' + start, 'Pega Developer') if query['location'][0] == 'India' else ''
        store = FakeStore()
        with mock.patch.object(linkedin, 'MAX_PAGES', 2):
            http = FakeHttp(route)
            result = sweep(http, store)
        self.assertEqual(searched(http)[1:], [('India', 0), ('India', 1)])
        self.assertEqual((result['status'], result['kept']), ('partial', 2))
        self.assertIn('1 searches stopped at the page limit', result['error'])
        # Everything LinkedIn would serve was read, so the sweep counts as complete and is not repeated.
        self.assertTrue(result['sweep_complete'])
        self.assertIsNone(store.kv['linkedin_checkpoint'])

        # The limit is reported even when the last page read was filler: a Pega role may lie beyond it.
        pages = {('India', 0): card('1', 'Pega Developer'), ('India', 1): card('2', 'Java Developer'),
                 ('Bengaluru, Karnataka, India', 0): 503}
        details = {'1': detail('Pega'), '2': detail('Java')}
        with mock.patch.object(linkedin, 'MAX_PAGES', 2):
            result = sweep(FakeHttp(search_route(pages, details)), store)
        self.assertEqual((result['status'], result['sweep_complete']), ('partial', False))
        self.assertEqual((store.kv['linkedin_checkpoint']['done'], store.kv['linkedin_checkpoint']['capped']),
                         ([INDIA_QUERY], [INDIA_QUERY]))
        # The capped query is finished: the resumed run does not page through it again or report it twice.
        resumed = FakeHttp(search_route({}, details))
        result = sweep(resumed, store)
        self.assertEqual(searched(resumed), [('Bengaluru, Karnataka, India', 0)])
        self.assertEqual((result['status'], result['error'], result['sweep_complete']), ('empty', None, True))

    def test_a_refused_search_is_blocked_and_never_empty(self):
        store = FakeStore()
        result = sweep(FakeHttp(lambda url, payload: 429), store)
        self.assertEqual((result['status'], result['jobs']), ('blocked', []))
        self.assertIn('2 of 2 searches not finished', result['error'])
        self.assertEqual(store.kv['linkedin_checkpoint']['done'], [])

    def test_a_breaker_opened_by_failures_is_an_error_not_blocked(self):
        http = FakeHttp(lambda url, payload: FakeResponse(0, '', url, 'timed out'), breaker_after=1)
        result = sweep(http)
        self.assertEqual((result['status'], http.requests), ('error', 1))
        self.assertIn('timed out', result['error'])
        result = sweep(FakeHttp(lambda url, payload: 429, breaker_after=0))
        self.assertEqual(result['status'], 'error')
        self.assertIn('LinkedIn stopped answering', result['error'])

    def test_a_server_error_is_an_error_and_a_later_failure_is_partial(self):
        result = sweep(FakeHttp(lambda url, payload: 503))
        self.assertEqual(result['status'], 'error')
        self.assertIn('HTTP 503', result['error'])

        pages = {('Bengaluru, Karnataka, India', 0): card('1', 'Pega Developer'), ('India', 0): 503}
        store = FakeStore()
        result = sweep(FakeHttp(search_route(pages, {'1': detail('Pega work')})), store)
        self.assertEqual((result['status'], result['kept']), ('partial', 1))
        self.assertEqual(store.kv['linkedin_checkpoint']['done'], [BENGALURU_QUERY])

    def test_refused_descriptions_make_the_run_partial(self):
        pages = {('India', 0): card('1', 'Pega Developer')}
        result = sweep(FakeHttp(search_route(pages, {'1': 429})))
        self.assertEqual((result['status'], result['kept']), ('partial', 1))


# ───────────────────────────── employer sites ─────────────────────────────

WORKDAY = {'kind': 'workday', 'tenant': 'acme', 'datacentre': 'wd3', 'site': 'Careers'}
WORKDAY_BASE = 'https://acme.wd3.myworkdayjobs.com/wday/cxs/acme/Careers'


def workday_route(url, payload):
    if url.endswith('/jobs'):
        return {'total': 3, 'jobPostings': [
            {'title': 'Senior Software Engineer - Pega', 'externalPath': '/job/Bangalore/a_R1', 'locationsText': 'Bangalore'},
            {'title': 'Pega Developer', 'externalPath': '/job/Sydney/b_R2', 'locationsText': 'Sydney'},
            {'title': 'Ops Analyst', 'externalPath': '/job/x/c_R3', 'locationsText': '2 Locations'}]}
    if url.endswith('a_R1'):
        return {'jobPostingInfo': {
            'title': 'Senior Software Engineer - Pega', 'location': 'Bangalore', 'country': {'descriptor': 'India'},
            'jobDescription': '<p>Design Pega case types</p>', 'jobReqId': 'R1', 'startDate': '2026-11-14',
            'timeType': 'Full time', 'externalUrl': 'https://acme.wd3.myworkdayjobs.com/Careers/job/Bangalore/a_R1'}}
    if url.endswith('c_R3'):
        return {'jobPostingInfo': {'title': 'Ops Analyst', 'location': 'Pune', 'additionalLocations': ['Chennai'],
                                   'country': {'descriptor': 'India'}, 'jobDescription': 'Excel reporting'}}
    return 404


def run_ats(route, block, company='Acme'):
    http = FakeHttp(route)
    return ats.run(Meter(http), company, block), http


class WorkdayTests(unittest.TestCase):
    def test_india_pega_roles_are_kept_with_their_full_description(self):
        result, http = run_ats(workday_route, WORKDAY)
        self.assertEqual((result['source'], result['label'], result['kind'], result['status']),
                         ('Employer site', 'Acme', 'ats', 'ok'))
        self.assertEqual((result['found'], result['kept'], result['requests']), (3, 1, 3))
        job = result['jobs'][0]
        self.assertEqual((job['source'], job['source_id'], job['requisition_id'], job['company']),
                         ('Employer site', 'workday:acme:R1', 'R1', 'Acme'))
        self.assertEqual((job['location'], job['posted_at'], job['description'], job['employment_type']),
                         ('Bangalore · India', '2026-11-14', 'Design Pega case types', 'Full time'))
        self.assertEqual(job['url'], 'https://acme.wd3.myworkdayjobs.com/Careers/job/Bangalore/a_R1')
        # The search is the verified CXS request, and asks for JSON.
        self.assertEqual(http.calls[0]['url'], WORKDAY_BASE + '/jobs')
        self.assertEqual(http.calls[0]['payload'], {'appliedFacets': {}, 'limit': 20, 'offset': 0, 'searchText': 'Pega'})
        self.assertEqual(http.calls[0]['headers'].get('Accept'), 'application/json')
        # Sydney is skipped without a request; "2 Locations" needs the detail to decide.
        self.assertEqual(http.urls[1:], [WORKDAY_BASE + '/job/Bangalore/a_R1', WORKDAY_BASE + '/job/x/c_R3'])

    def test_search_results_are_paged(self):
        def route(url, payload):
            index = payload['offset'] // 20
            return {'total': 45, 'jobPostings': [{'title': 'x', 'externalPath': f'/job/{index}', 'locationsText': 'Paris'}]}
        result, http = run_ats(route, WORKDAY)
        self.assertEqual([call['payload']['offset'] for call in http.calls], [0, 20, 40])
        self.assertEqual((result['status'], result['found']), ('empty', 3))

    def test_later_pages_reporting_no_total_do_not_end_paging(self):
        def route(url, payload):
            index = payload['offset'] // 20
            rows = [{'title': 'x', 'externalPath': f'/job/{index}', 'locationsText': 'Paris'}] if index < 3 else []
            return {'total': 80 if index == 0 else 0, 'jobPostings': rows}
        result, http = run_ats(route, WORKDAY)
        self.assertEqual([call['payload']['offset'] for call in http.calls], [0, 20, 40, 60])
        self.assertEqual((result['status'], result['found']), ('empty', 3))

    def test_stopping_at_the_cap_is_partial(self):
        def route(url, payload):
            return {'total': 100, 'jobPostings': [{'title': 'x', 'externalPath': f"/job/{payload['offset']}",
                                                   'locationsText': 'Paris'}]}
        with mock.patch.object(ats, 'WORKDAY_CAP', 40):
            result, http = run_ats(route, WORKDAY)
        self.assertEqual(len(http.calls), 2)
        self.assertEqual((result['status'], result['error']), ('partial', 'stopped at 2 of 100; raise the cap'))

    def test_only_a_plainly_foreign_posting_is_skipped(self):
        def route(url, payload):
            if url.endswith('/jobs'):
                return {'total': 4, 'jobPostings': [
                    {'title': 'Pega Developer', 'externalPath': '/job/a', 'locationsText': 'Manyata Campus'},
                    {'title': 'Pega Developer', 'externalPath': '/job/b'},
                    {'externalPath': '/job/c', 'locationsText': 'Remote'},
                    {'title': 'Pega Developer', 'externalPath': '/job/d', 'locationsText': 'London'}]}
            if url.endswith('/job/c'):
                return {'jobPostingInfo': {'jobDescription': 'Pega PRPC', 'jobReqId': 'C'}}
            return {'jobPostingInfo': {'title': 'Pega Developer', 'jobDescription': 'x', 'jobReqId': url[-1].upper()}}
        result, http = run_ats(route, WORKDAY)
        self.assertEqual([(job['requisition_id'], job['title'], job['location']) for job in result['jobs']],
                         [('A', 'Pega Developer', 'Manyata Campus'), ('B', 'Pega Developer', 'India'),
                          ('C', FALLBACK_TITLE, 'Remote')])
        self.assertFalse(any(url.endswith('/job/d') for url in http.urls))

    def test_a_stated_country_decides_even_when_its_name_is_not_a_known_foreign_place(self):
        cases = {'a': ('Bratislava', [], 'Slovakia'), 'b': ('Seoul', [], 'Korea, Republic of'),
                 'c': ('Vilnius', ['Hyderabad'], 'Lithuania'), 'd': ('Luxembourg', [], 'Luxembourg'),
                 'e': ('Manyata Campus', [], 'India'), 'f': ('Technology Centre', [], None)}

        def route(url, payload):
            if url.endswith('/jobs'):
                # As on the live site, a posting with several sites is listed as "2 Locations".
                return {'total': 6, 'jobPostings': [
                    {'title': 'Pega Developer', 'externalPath': '/job/' + key,
                     'locationsText': '2 Locations' if others else place}
                    for key, (place, others, _) in cases.items()]}
            place, others, country = cases[url[-1]]
            info = {'title': 'Pega Developer', 'location': place, 'additionalLocations': others,
                    'jobDescription': 'Pega', 'jobReqId': url[-1]}
            return {'jobPostingInfo': dict(info, country={'descriptor': country}) if country else info}
        result, _ = run_ats(route, WORKDAY)
        # c lists an Indian site as well; e is in India; f names no country at all.
        self.assertEqual([job['requisition_id'] for job in result['jobs']], ['c', 'e', 'f'])

    def test_maintenance_window_is_reported_as_maintenance(self):
        page = FakeResponse(200, '<html>Workday is currently unavailable.</html>',
                            'https://static.community.workday.com/maintenance-page.html')
        result, _ = run_ats(lambda url, payload: page, WORKDAY)
        self.assertEqual((result['status'], result['jobs']), ('maintenance', []))
        self.assertIn('maintenance', result['error'])

    def test_a_wrong_site_name_is_an_error_but_a_real_board_without_pega_is_empty(self):
        nothing = {'total': 0, 'jobPostings': []}
        result, http = run_ats(lambda url, payload: nothing, WORKDAY)
        self.assertEqual(result['status'], 'error')
        self.assertIn('site name', result['error'])
        self.assertEqual(http.calls[-1]['payload'], {'appliedFacets': {}, 'limit': 1, 'offset': 0, 'searchText': ''})
        result, _ = run_ats(lambda url, payload: nothing if payload['searchText'] else {'total': 50, 'jobPostings': []},
                            WORKDAY)
        self.assertEqual((result['status'], result['error']), ('empty', None))

    def test_refusals_and_server_errors_are_never_empty(self):
        self.assertEqual(run_ats(lambda url, payload: 403, WORKDAY)[0]['status'], 'blocked')
        result, _ = run_ats(lambda url, payload: 503, WORKDAY)
        self.assertEqual((result['status'], result['error']), ('error', 'HTTP 503'))
        for wrong in ('<html>not json</html>', {}, {'total': 0}, {'jobPostings': None}, []):
            result, _ = run_ats(lambda url, payload: wrong, WORKDAY)
            self.assertEqual((result['status'], result['error']), ('error', 'unexpected response shape'), wrong)
        # A refused or broken site check is not proof of an empty board either.
        result, _ = run_ats(lambda url, payload: {'total': 0, 'jobPostings': []} if payload['searchText'] else 403, WORKDAY)
        self.assertEqual(result['status'], 'blocked')

    def test_an_unreadable_posting_makes_the_board_partial(self):
        result, _ = run_ats(lambda url, payload: 500 if url.endswith('c_R3') else workday_route(url, payload), WORKDAY)
        self.assertEqual((result['status'], result['kept'], result['error']), ('partial', 1, '1 posting could not be read'))

    def test_a_second_site_on_the_same_tenant_is_searched_too(self):
        def route(url, payload):
            if '/Careers/' in url:
                return workday_route(url, payload)
            if url.endswith('/jobs'):
                return {'total': 1, 'jobPostings': [{'title': 'Pega CSSA', 'externalPath': '/job/Hyd/z_R9',
                                                     'locationsText': 'Hyderabad'}]}
            return {'jobPostingInfo': {'title': 'Pega CSSA', 'location': 'Hyderabad', 'jobReqId': 'R9',
                                       'jobDescription': 'Pega'}}
        result, _ = run_ats(route, dict(WORKDAY, more_sites=['India']))
        self.assertEqual(sorted(job['requisition_id'] for job in result['jobs']), ['R1', 'R9'])
        self.assertEqual((result['status'], result['found']), ('ok', 4))
        # One site failing must not hide the other, and must not pass as a clean result.
        result, _ = run_ats(lambda url, payload: 503 if '/India/' in url else workday_route(url, payload),
                            dict(WORKDAY, more_sites=['India']))
        self.assertEqual((result['status'], result['kept']), ('partial', 1))


class OracleTests(unittest.TestCase):
    BLOCK = {'kind': 'oracle', 'host': 'bank.fa.oraclecloud.com', 'site': 'CX_1'}

    @staticmethod
    def route(url, payload):
        if 'recruitingCEJobRequisitions?' in url:
            return {'items': [{'TotalJobsCount': 3, 'requisitionList': [
                {'Id': '1', 'Title': 'Software Engineer III', 'PrimaryLocation': 'Bengaluru, Karnataka, India',
                 'PrimaryLocationCountry': 'IN', 'PostedDate': '2026-11-10'},
                {'Id': '2', 'Title': 'Pega Developer', 'PrimaryLocation': 'Plano, TX, United States',
                 'PrimaryLocationCountry': 'US'},
                {'Id': '3', 'Title': 'Pega Lead', 'PrimaryLocation': 'London', 'PrimaryLocationCountry': 'GB',
                 'secondaryLocations': [{'Name': 'Hyderabad, Telangana, India', 'CountryCode': 'IN'}]}]}]}
        if 'Id="1"' in urllib.parse.unquote(url):
            return {'items': [{'ExternalDescriptionStr': '<p>Hands-on Pega PRPC development</p>',
                               'ExternalQualificationsStr': '<ul><li>CSSA</li></ul>'}]}
        return {'items': [{'ExternalDescriptionStr': 'Lead the team'}]}

    def test_india_is_decided_by_country_code_or_secondary_location(self):
        result, http = run_ats(self.route, self.BLOCK, company='Bank')
        self.assertEqual((result['status'], result['found'], result['kept']), ('ok', 3, 2))
        first, second = result['jobs']
        self.assertEqual((first['source_id'], first['requisition_id'], first['posted_at']),
                         ('oracle:bank.fa.oraclecloud.com:1', '1', '2026-11-10'))
        self.assertEqual(first['url'], 'https://bank.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/1')
        self.assertEqual(first['description'], 'Hands-on Pega PRPC development\nCSSA')
        self.assertEqual(second['location'], 'London · Hyderabad, Telangana, India')
        # The verified finder and expand strings, and no detail request for the US posting.
        self.assertEqual(http.urls[0], 'https://bank.fa.oraclecloud.com/hcmRestApi/resources/latest/'
                         'recruitingCEJobRequisitions?onlyData=true&expand=requisitionList.secondaryLocations&finder='
                         'findReqs;siteNumber=CX_1,keyword=%22pega%22,limit=50,offset=0,sortBy=POSTING_DATES_DESC')
        self.assertEqual(http.urls[1], 'https://bank.fa.oraclecloud.com/hcmRestApi/resources/latest/'
                         'recruitingCEJobRequisitionDetails?expand=all&onlyData=true&finder='
                         'ById;Id=%221%22,siteNumber=CX_1')
        self.assertEqual(len(http.urls), 3)

    def test_outcomes_other_than_ok(self):
        def nothing(count):
            return {'items': [{'TotalJobsCount': count, 'requisitionList': []}]}
        # No Pega requisitions on a site that does list jobs is empty; a site with no jobs at all is misconfigured.
        result, http = run_ats(lambda url, payload: nothing(0) if 'keyword' in url else nothing(900), self.BLOCK)
        self.assertEqual((result['status'], len(http.urls)), ('empty', 2))
        self.assertIn('findReqs;siteNumber=CX_1,limit=1,offset=0', http.urls[1])
        for answer in (nothing(0), {'items': []}):
            result, _ = run_ats(lambda url, payload: answer, self.BLOCK)
            self.assertEqual(result['status'], 'error', answer)
            self.assertIn('site name', result['error'])
        for wrong in ({}, {'items': None}, {'items': [{'TotalJobsCount': 3}]}, '<html>', [1]):
            result, _ = run_ats(lambda url, payload: wrong, self.BLOCK)
            self.assertEqual((result['status'], result['error']), ('error', 'unexpected response shape'), wrong)
        self.assertEqual(run_ats(lambda url, payload: 401, self.BLOCK)[0]['status'], 'blocked')
        self.assertEqual(run_ats(lambda url, payload: 500, self.BLOCK)[0]['status'], 'error')
        result, _ = run_ats(lambda url, payload: self.route(url, payload) if 'Requisitions?' in url else 502, self.BLOCK)
        self.assertEqual((result['status'], result['error']), ('partial', '2 postings could not be read'))

    def test_a_country_code_outranks_the_place_text(self):
        def row(identifier, place, code, secondary=()):
            return {'Id': identifier, 'Title': 'Pega Developer', 'PrimaryLocation': place,
                    'PrimaryLocationCountry': code, 'secondaryLocations': list(secondary)}

        def route(url, payload):
            if 'Requisitions?' in url:
                return {'items': [{'TotalJobsCount': 5, 'requisitionList': [
                    row('1', 'Indianapolis, IN, United States', 'US'),
                    row('2', 'Indianapolis, IN', 'US'),
                    row('3', 'Bratislava', 'SK', [{'Name': 'Pune, Maharashtra, India', 'CountryCode': 'IN'}]),
                    row('4', 'Vilnius', 'LT', [{'Name': 'Hyderabad'}]),
                    row('5', 'Bengaluru', None)]}]}
            return {'items': [{'ExternalDescriptionStr': 'Pega'}]}
        result, _ = run_ats(route, self.BLOCK)
        self.assertEqual([job['requisition_id'] for job in result['jobs']], ['3', '4', '5'])

    def test_stopping_at_the_cap_is_partial_and_unknown_places_are_kept(self):
        def route(url, payload):
            if 'Requisitions?' in url:
                offset = int(urllib.parse.unquote(url).split('offset=')[1].split(',')[0])
                return {'items': [{'TotalJobsCount': 500, 'requisitionList': [
                    {'Id': str(offset), 'Title': 'Pega Developer', 'PrimaryLocation': 'Global Technology Centre'}]}]}
            return {'items': [{'ExternalDescriptionStr': 'Pega'}]}
        with mock.patch.object(ats, 'ORACLE_CAP', 100):
            result, _ = run_ats(route, self.BLOCK)
        self.assertEqual((result['status'], result['kept'], result['error']),
                         ('partial', 2, 'stopped at 2 of 500; raise the cap'))
        self.assertEqual(result['jobs'][0]['location'], 'Global Technology Centre')


class GreenhouseLeverTests(unittest.TestCase):
    def test_greenhouse_unescapes_content_and_filters_by_office(self):
        feed = {'jobs': [
            {'id': 11, 'title': 'Platform Engineer', 'absolute_url': 'https://job-boards.greenhouse.io/acme/jobs/11',
             'location': {'name': 'Bengaluru'}, 'content': '&lt;p&gt;Own our Pega platform &amp;amp; APIs&lt;/p&gt;',
             'first_published': '2026-11-01T09:00:00-04:00', 'requisition_id': 'REQ-7'},
            {'id': 12, 'title': 'Pega Developer', 'absolute_url': 'https://x/12', 'location': {'name': 'Remote'},
             'offices': [{'name': 'Pune', 'location': 'Pune, India'}], 'content': ''},
            {'id': 13, 'title': 'Pega Developer', 'absolute_url': 'https://x/13', 'location': {'name': 'Boston'}},
            {'id': 14, 'title': 'Pegasus Pilot', 'absolute_url': 'https://x/14', 'location': {'name': 'Chennai'}}]}
        result, http = run_ats(lambda url, payload: feed, {'kind': 'greenhouse', 'board': 'acme'})
        self.assertEqual(http.urls, ['https://boards-api.greenhouse.io/v1/boards/acme/jobs?content=true'])
        self.assertEqual((result['status'], result['found']), ('ok', 4))
        self.assertEqual([job['source_id'] for job in result['jobs']], ['greenhouse:acme:11', 'greenhouse:acme:12'])
        job = result['jobs'][0]
        self.assertEqual((job['description'], job['posted_at'], job['requisition_id']),
                         ('Own our Pega platform & APIs', '2026-11-01', 'REQ-7'))

    def test_lever_joins_the_description_parts(self):
        feed = [{'id': 'abc', 'text': 'Senior Engineer', 'hostedUrl': 'https://jobs.lever.co/acme/abc',
                 'categories': {'location': 'Bengaluru', 'allLocations': ['Bengaluru', 'Pune'], 'commitment': 'Full-time'},
                 'descriptionPlain': 'Join us.', 'lists': [{'text': 'Must have', 'content': '<li>Pega CSSA</li>'}],
                 'additionalPlain': 'Equal opportunity.', 'createdAt': 1794479644806},
                {'id': 'def', 'text': 'Pega Developer', 'hostedUrl': 'https://jobs.lever.co/acme/def',
                 'categories': {'location': 'Toronto'}, 'country': 'CA'},
                {'id': 'ghi', 'text': 'Pega Developer', 'hostedUrl': 'https://jobs.lever.co/acme/ghi',
                 'categories': {'location': 'Remote'}, 'country': 'IN'},
                {'id': 'jkl', 'text': '', 'hostedUrl': 'https://jobs.lever.co/acme/jkl', 'descriptionPlain': 'Pega',
                 'categories': {'location': 'Remote'}},
                {'id': 'mno', 'text': 'Pega Developer', 'hostedUrl': 'https://jobs.lever.co/acme/mno',
                 'categories': {'location': 'Remote'}, 'country': 'US'}]
        result, http = run_ats(lambda url, payload: feed, {'kind': 'lever', 'board': 'acme'})
        self.assertEqual(http.urls, ['https://api.lever.co/v0/postings/acme?mode=json'])
        # Country IN is India whatever the place says; no country and no foreign place is kept too.
        self.assertEqual([(job['source_id'], job['title']) for job in result['jobs']],
                         [('lever:acme:abc', 'Senior Engineer'), ('lever:acme:ghi', 'Pega Developer'),
                          ('lever:acme:jkl', FALLBACK_TITLE)])
        job = result['jobs'][0]
        self.assertEqual((job['location'], job['employment_type']), ('Bengaluru / Pune', 'Full-time'))
        self.assertEqual(job['description'], 'Join us.\nMust have\nPega CSSA\nEqual opportunity.')
        self.assertEqual(job['posted_at'], datetime.fromtimestamp(1794479644.806, timezone.utc).date().isoformat())

    def test_outcomes_other_than_ok(self):
        for block, nothing in (({'kind': 'greenhouse', 'board': 'acme'}, {'jobs': []}), ({'kind': 'lever', 'board': 'acme'}, [])):
            self.assertEqual(run_ats(lambda url, payload: nothing, block)[0]['status'], 'empty', block['kind'])
            self.assertEqual(run_ats(lambda url, payload: 403, block)[0]['status'], 'blocked', block['kind'])
            self.assertEqual(run_ats(lambda url, payload: 404, block)[0]['status'], 'error', block['kind'])
            for wrong in ({'error': 'x'}, {}, {'jobs': {}}, 'x'):
                result, _ = run_ats(lambda url, payload: wrong, block)
                self.assertEqual((result['status'], result['error']), ('error', 'unexpected response shape'), wrong)

    def test_an_unknown_ats_kind_is_an_error(self):
        result, http = run_ats(lambda url, payload: 200, {'kind': 'taleo', 'board': 'x'})
        self.assertEqual((result['status'], http.requests), ('error', 0))


# ───────────────────────────── job boards ─────────────────────────────

def run_board(name, route):
    http = FakeHttp(route)
    return boards.BOARDS[name](Meter(http)), http


class InstahyreTests(unittest.TestCase):
    def test_pages_until_the_feed_has_no_next_link(self):
        def route(url, payload):
            if url.endswith('offset=0'):
                return {'meta': {'next': '/api/v1/job_search?offset=2'}, 'objects': [
                    {'id': 1, 'title': 'Pega Developer', 'keywords': ['Java'], 'locations': 'Bangalore,Pune',
                     'public_url': 'https://www.instahyre.com/job-1', 'employer': {'company_name': 'Acme'}},
                    {'id': 2, 'title': 'Backend Engineer', 'keywords': ['Go'], 'locations': 'Bangalore',
                     'public_url': 'https://www.instahyre.com/job-2'}]}
            return {'meta': {'next': None}, 'objects': [
                {'id': 3, 'candidate_title': 'Engineer', 'keywords': ['PRPC'], 'locations': 'Work From Home',
                 'public_url': 'https://www.instahyre.com/job-3', 'employer': {'company_name': 'Globex'}},
                {'id': 4, 'title': 'Pega Lead', 'keywords': [], 'locations': 'Singapore',
                 'public_url': 'https://www.instahyre.com/job-4'}]}
        result, http = run_board('Instahyre', route)
        self.assertEqual(http.urls, ['https://www.instahyre.com/api/v1/job_search?skills=pega&offset=0',
                                     'https://www.instahyre.com/api/v1/job_search?skills=pega&offset=2'])
        self.assertEqual((result['source'], result['label'], result['kind'], result['status'], result['found']),
                         ('Instahyre', 'Instahyre', 'board', 'ok', 4))
        self.assertEqual([(job['source_id'], job['company'], job['location']) for job in result['jobs']],
                         [('1', 'Acme', 'Bangalore, Pune'), ('3', 'Globex', 'Work From Home')])


class CutshortTests(unittest.TestCase):
    def test_jobs_are_read_from_the_embedded_page_data(self):
        result, http = run_board('Cutshort', lambda url, payload: fixture('cutshort.html'))
        self.assertEqual((http.urls, http.calls[0]['accept']), (['https://cutshort.io/jobs/pega-jobs'], 'text/html'))
        self.assertEqual((result['status'], result['found']), ('ok', 4))
        self.assertEqual([job['source_id'] for job in result['jobs']], ['c1', 'c4'])
        first, second = result['jobs']
        self.assertEqual((first['company'], first['location'], first['description']),
                         ('Acme Labs', 'Bengaluru (Bangalore)', 'Build Pega case types & integrations.'))
        self.assertEqual((first['experience_min'], first['experience_max'], first['salary_min_lpa'], first['salary_max_lpa']),
                         (3, 6, 12, 20))
        self.assertEqual((second['location'], second['salary_min_lpa'], second['salary_max_lpa']), ('India', None, 35))

    def test_a_changed_page_is_an_error_and_an_empty_list_is_empty(self):
        self.assertEqual(run_board('Cutshort', lambda url, payload: '<html>redesigned</html>')[0]['status'], 'error')
        page = fixture('cutshort.html')
        emptied = page[:page.index('"jobs":[') + len('"jobs":[')] + page[page.index(']}}}}}]}}}}'):]
        self.assertEqual(run_board('Cutshort', lambda url, payload: emptied)[0]['status'], 'empty')

    def test_more_live_jobs_than_the_page_embeds_is_partial(self):
        page = fixture('cutshort.html').replace('{"jobs":[', '{"liveJobCount":57,"jobs":[')
        result, _ = run_board('Cutshort', lambda url, payload: page)
        self.assertEqual((result['status'], result['kept'], result['found']), ('partial', 2, 57))
        self.assertIn('stopped at 4 of 57', result['error'])

    def test_a_pega_row_without_a_headline_gets_a_fallback_title(self):
        page = fixture('cutshort.html').replace('"headline":"Senior Engineer"', '"headline":""')
        result, _ = run_board('Cutshort', lambda url, payload: page)
        self.assertEqual([job['title'] for job in result['jobs']], ['Pega Developer', FALLBACK_TITLE])


class ShineTests(unittest.TestCase):
    @staticmethod
    def route(url, payload):
        if url.endswith('/pega-jobs'):
            return fixture('shine_page1.html')
        return fixture('shine_page2.html') if url.endswith('/pega-jobs-2') else '<html><body>No more jobs</body></html>'

    def test_cards_are_parsed_without_a_third_party_parser(self):
        rows = boards.parse_shine(fixture('shine_page1.html'))
        self.assertEqual([row[:6] for row in rows], [
            ('/jobs/senior-pega-developer/acme-bank/17012345', 'Senior Pega Developer', 'Acme Bank & Co',
             'Bangalore, Hyderabad', 4, 7),
            ('/jobs/java-developer/other-corp/17012346', 'Java Developer', 'Other Corp', 'Pune', 2, 4),
            # No employer element in this card: the name comes from the link.
            ('/jobs/pega-lead-system-architect/globex-technologies/17012347', 'Pega Lead System Architect',
             'Globex Technologies', 'Chennai', 10, 14)])
        # Script and style text never leaks into a card.
        self.assertNotIn('var pega', rows[0][6])

    def test_pages_are_followed_until_one_brings_nothing_new(self):
        result, http = run_board('Shine', self.route)
        self.assertEqual(http.urls, ['https://www.shine.com/job-search/pega-jobs',
                                     'https://www.shine.com/job-search/pega-jobs-2',
                                     'https://www.shine.com/job-search/pega-jobs-3'])
        self.assertEqual((result['source'], result['status'], result['found']), ('Shine', 'ok', 4))
        self.assertEqual([(job['source_id'], job['title']) for job in result['jobs']],
                         [('17012345', 'Senior Pega Developer'), ('17012347', 'Pega Lead System Architect'),
                          ('17012399', 'Pega CSSA Developer')])
        job = result['jobs'][0]
        self.assertEqual((job['url'], job['experience_min'], job['experience_max']),
                         ('https://www.shine.com/jobs/senior-pega-developer/acme-bank/17012345', 4, 7))

    def test_an_intermittent_500_is_partial_after_the_first_page_and_an_error_on_it(self):
        result, _ = run_board('Shine', lambda url, payload: 500 if url.endswith('-2') else self.route(url, payload))
        self.assertEqual((result['status'], result['kept'], result['error']), ('partial', 2, 'HTTP 500'))
        self.assertEqual(run_board('Shine', lambda url, payload: 500)[0]['status'], 'error')
        self.assertEqual(run_board('Shine', lambda url, payload: 403)[0]['status'], 'blocked')

    def test_stopping_at_the_page_cap_is_partial(self):
        def route(url, payload):
            page = url.rsplit('-', 1)[1] if url[-1].isdigit() else '1'
            return f'<div class="result-card_card"><a href="/jobs/pega-developer/acme/{page}00">Pega Developer</a></div>'
        with mock.patch.object(boards, 'SHINE_PAGES', 3):
            result, http = run_board('Shine', route)
        self.assertEqual((len(http.urls), result['status'], result['kept']), (3, 'partial', 3))
        self.assertIn('stopped at page 3', result['error'])

    def test_a_page_without_job_links_is_an_error_not_empty(self):
        self.assertEqual(run_board('Shine', lambda url, payload: '<html><body>Welcome</body></html>')[0]['status'], 'error')


class HiristTests(unittest.TestCase):
    ROWS = [{'id': 1, 'title': 'Pega Senior Developer', 'min': 4, 'max': 7, 'minSal': 25, 'maxSal': 35, 'hideSal': 0,
             'jobDetailUrl': 'https://www.hirist.tech/j/pega-1', 'locations': [{'name': 'Bangalore'}],
             'tags': [{'name': 'Pega'}], 'companyData': {'companyName': 'Acme'}, 'createdTimeMs': 1794479644806,
             'applyUrl': 'https://www.hirist.tech/apply/1'},
            {'id': 2, 'title': 'Java Developer', 'jobDetailUrl': 'https://www.hirist.tech/j/java-2',
             'tags': [{'name': 'Java'}], 'locations': []},
            {'id': 3, 'title': 'Architect', 'jobDetailUrl': 'https://www.hirist.tech/j/arch-3', 'tags': [{'name': 'PRPC'}],
             'locations': [], 'minSal': 40, 'maxSal': 60, 'hideSal': 1},
            {'id': 4, 'title': 'Pega Developer', 'jobDetailUrl': 'https://www.hirist.tech/j/pega-4',
             'locations': [{'name': 'Dubai'}], 'tags': []},
            {'id': 5, 'title': 'Pega Developer', 'jobDetailUrl': 'https://www.hirist.tech/j/pega-5',
             'locations': [{'name': 'Remote'}], 'tags': []}]

    def test_salary_and_experience_are_numbers_in_lpa_and_years(self):
        result, http = run_board('Hirist', lambda url, payload: {'data': self.ROWS, 'totalPages': 1})
        self.assertEqual(http.urls,
                         ['https://gladiator.hirist.tech/job/search?query=Pega&page=0&posting=0&industry=&size=20'])
        self.assertEqual(http.calls[0]['headers'],
                         {'Origin': 'https://www.hirist.tech', 'Referer': 'https://www.hirist.tech/'})
        self.assertEqual((result['status'], result['found']), ('ok', 5))
        first, hidden, remote = result['jobs']
        self.assertEqual(remote['location'], 'Remote')   # not in an Indian city, but not abroad either
        self.assertEqual((first['source_id'], first['company'], first['location'], first['apply_url']),
                         ('1', 'Acme', 'Bangalore', 'https://www.hirist.tech/apply/1'))
        self.assertEqual((first['experience_min'], first['experience_max'], first['salary_min_lpa'], first['salary_max_lpa']),
                         (4, 7, 25, 35))
        self.assertEqual(first['posted_at'], datetime.fromtimestamp(1794479644.806, timezone.utc).date().isoformat())
        # A hidden salary band is not reported; a missing location defaults to India.
        self.assertEqual((hidden['location'], hidden['salary_min_lpa'], hidden['salary_max_lpa']), ('India', None, None))

    def test_full_pages_are_followed(self):
        def route(url, payload):
            page = int(urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['page'][0])
            rows = [dict(self.ROWS[0], id=page * 100 + n, jobDetailUrl=f'https://www.hirist.tech/j/{page}-{n}')
                    for n in range(20 if page == 0 else 5)]
            return {'data': rows, 'totalPages': 3}
        result, http = run_board('Hirist', route)
        self.assertEqual((len(http.urls), result['kept']), (2, 25))

    def test_stopping_at_the_page_cap_is_partial(self):
        def route(url, payload):
            page = int(urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['page'][0])
            return {'totalPages': 99, 'data': [dict(self.ROWS[0], id=page * 100 + n,
                                                    jobDetailUrl=f'https://www.hirist.tech/j/{page}-{n}')
                                               for n in range(20)]}
        with mock.patch.object(boards, 'FEED_PAGES', 2):
            result, http = run_board('Hirist', route)
        self.assertEqual((len(http.urls), result['status'], result['kept']), (2, 'partial', 40))
        self.assertEqual(result['error'], 'stopped at page 2 of 99; raise the cap')


class TimesJobsTests(unittest.TestCase):
    @staticmethod
    def route(url, payload):
        page = payload['page']
        return {'totalPages': 2, 'jobs': [
            {'title': 'Pega Developer ' + page, 'company': 'Acme', 'location': 'Pune', 'skills': 'Pega, Java',
             'jobDetailUrl': f'https://www.timesjobs.com/job-detail/x-jobid-{page}==&source=srp',
             'description': '<b>Pega</b> workflows', 'experienceFrom': 3, 'experienceTo': 6, 'postDate': '2026-11-11',
             'jobId': 'tj' + page, 'lowSalary': 1200000 if page == '1' else 18, 'highSalary': 2000000 if page == '1' else 30},
            {'title': 'Tester', 'company': 'Other', 'location': 'Pune', 'skills': 'Selenium',
             'jobDetailUrl': 'https://www.timesjobs.com/job-detail/t', 'jobId': 'other' + page}]}

    def test_pages_are_read_tracking_is_stripped_and_rupees_become_lpa(self):
        result, http = run_board('TimesJobs', self.route)
        self.assertEqual([call['url'] for call in http.calls],
                         ['https://tjapi.timesjobs.com/search/api/v1/search/jobs/list'] * 2)
        self.assertEqual(http.calls[0]['payload'], {
            'keyword': 'pega', 'location': '', 'experience': '', 'page': '1', 'size': '25', 'jobFunctions': [],
            'company': '', 'industry': '', 'functionAreaId': '', 'jobFunction': ''})
        self.assertEqual(http.calls[0]['headers'],
                         {'Origin': 'https://www.timesjobs.com', 'Referer': 'https://www.timesjobs.com/'})
        self.assertEqual((result['status'], result['found']), ('ok', 4))
        self.assertEqual([job['url'] for job in result['jobs']],
                         ['https://www.timesjobs.com/job-detail/x-jobid-1==', 'https://www.timesjobs.com/job-detail/x-jobid-2=='])
        rupees, lakhs = result['jobs']
        self.assertEqual((rupees['salary_min_lpa'], rupees['salary_max_lpa']), (12, 20))
        self.assertEqual((lakhs['salary_min_lpa'], lakhs['salary_max_lpa']), (18, 30))
        self.assertEqual((rupees['source_id'], rupees['experience_min'], rupees['experience_max'], rupees['posted_at']),
                         ('tj1', 3, 6, '2026-11-11'))

    def test_remote_and_blank_locations_are_kept_and_the_cap_is_reported(self):
        def route(url, payload):
            page = payload['page']
            return {'totalPages': 9, 'jobs': [{'title': 'Pega Developer', 'jobId': page, 'skills': '',
                                               'location': {'1': 'Work From Home', '2': '', '3': 'Sydney'}[page],
                                               'jobDetailUrl': 'https://www.timesjobs.com/job-detail/' + page}]}
        with mock.patch.object(boards, 'FEED_PAGES', 3):
            result, _ = run_board('TimesJobs', route)
        self.assertEqual([job['location'] for job in result['jobs']], ['Work From Home', 'India'])
        self.assertEqual((result['status'], result['error']), ('partial', 'stopped at page 3 of 9; raise the cap'))

    def test_a_failure_on_a_later_page_is_partial(self):
        result, _ = run_board('TimesJobs', lambda url, payload: self.route(url, payload) if payload['page'] == '1' else 503)
        self.assertEqual((result['status'], result['kept'], result['error']), ('partial', 1, 'HTTP 503'))


class BoardOutcomeTests(unittest.TestCase):
    EMPTY = {'Instahyre': {'meta': {}, 'objects': []}, 'Hirist': {'data': [], 'totalPages': 0},
             'TimesJobs': {'jobs': [], 'totalPages': 0}}

    def test_a_failed_board_is_never_empty(self):
        for name in boards.BOARDS:
            result, _ = run_board(name, lambda url, payload: 503)
            self.assertEqual((result['status'], result['jobs'], result['error']), ('error', [], 'HTTP 503'), name)
            self.assertEqual(run_board(name, lambda url, payload: 403)[0]['status'], 'blocked', name)
            self.assertEqual(run_board(name, lambda url, payload: FakeResponse(0, '', url, 'circuit open'))[0]['status'],
                             'error', name)

    def test_a_feed_that_answers_with_no_rows_is_empty(self):
        for name, answer in self.EMPTY.items():
            result, _ = run_board(name, lambda url, payload: answer)
            self.assertEqual((result['status'], result['error'], result['requests']), ('empty', None, 1), name)

    def test_a_200_answer_of_the_wrong_shape_is_an_error(self):
        for name in boards.BOARDS:
            for wrong in ('<html>Sign in</html>', {}, {'objects': None, 'data': 'x', 'jobs': {}}, [], 'null'):
                result, _ = run_board(name, lambda url, payload: wrong)
                self.assertEqual((result['status'], result['jobs']), ('error', []), (name, wrong))
                self.assertTrue(result['error'], name)

    def test_instahyre_reports_the_page_cap(self):
        def route(url, payload):
            offset = url.rsplit('=', 1)[1]
            return {'meta': {'next': 'more'}, 'objects': [{'id': offset, 'title': 'Pega Developer', 'locations': '',
                                                           'public_url': 'https://www.instahyre.com/job-' + offset}]}
        with mock.patch.object(boards, 'INSTAHYRE_PAGES', 2):
            result, _ = run_board('Instahyre', route)
        self.assertEqual((result['status'], result['kept'], result['error']),
                         ('partial', 2, 'stopped at page 2 of more; raise the cap'))


class LocationEvidenceTests(unittest.TestCase):
    def test_only_positive_evidence_puts_a_posting_abroad(self):
        for text in ('London, United Kingdom', 'Plano, TX, United States', 'Sydney', 'Dubai'):
            self.assertTrue(outside_india(text), text)
        for text in ('', None, 'Remote', 'Work From Home', '2 Locations', 'Whitefield', 'Manyata Tech Park',
                     'Bengaluru / London', 'India', 'Hyderabad, Telangana'):
            self.assertFalse(outside_india(text), text)


# ───────────────────────────── tasks and registry ─────────────────────────────

class Registry:
    """Stands in for `radar.rank.Registry`, which exposes the companies.json entries as `entries`."""

    def __init__(self, entries):
        self.entries = entries


class BuildTasksTests(unittest.TestCase):
    COMPANIES = [
        {'name': 'Mega Services', 'aliases': [], 'type': 'services', 'bengaluru': True, 'linkedin_query': False,
         'ats': {'kind': 'lever', 'board': 'mega'}},
        {'name': 'Quiet GCC', 'aliases': [], 'type': 'gcc', 'bengaluru': None, 'linkedin_query': False,
         'ats': {'kind': 'greenhouse', 'board': 'quiet'}},
        {'name': 'Acme Bank', 'aliases': [], 'type': 'gcc', 'bengaluru': True, 'linkedin_query': True,
         'ats': {'kind': 'workday', 'tenant': 'acme', 'datacentre': 'wd3', 'site': 'Careers'}},
        {'name': 'Pegasystems', 'aliases': ['Pega'], 'type': 'product', 'bengaluru': True, 'linkedin_query': True},
        {'name': 'Oracle Bank', 'aliases': [], 'type': 'product', 'bengaluru': True, 'linkedin_query': False,
         'ats': {'kind': 'oracle', 'host': 'bank.fa.oraclecloud.com', 'site': 'CX_1'}}]

    def test_linkedin_first_then_focus_employers_then_other_employers_then_boards(self):
        tasks = build_tasks({}, Registry(self.COMPANIES), FakeStore())
        self.assertEqual([(task.name, task.priority) for task in tasks], [
            ('linkedin', 0),
            ('ats:workday:acme', 10), ('ats:oracle:bank.fa.oraclecloud.com', 10),
            ('ats:lever:mega', 20), ('ats:greenhouse:quiet', 20),
            ('board:instahyre', 30), ('board:cutshort', 30), ('board:shine', 30), ('board:hirist', 30),
            ('board:timesjobs', 30)])
        self.assertEqual([(task.label, task.kind) for task in tasks[:3]],
                         [('LinkedIn', 'linkedin'), ('Acme Bank', 'ats'), ('Oracle Bank', 'ats')])
        # Naukri and Foundit refuse automated clients and are deliberately not sources.
        self.assertFalse([task.name for task in tasks if 'naukri' in task.name or 'foundit' in task.name])
        # A plain list of entries works as well as a Registry.
        self.assertEqual([task.name for task in build_tasks({}, self.COMPANIES, None)], [task.name for task in tasks])

    def test_tasks_run_their_adapter_and_count_their_own_requests(self):
        tasks = {task.name: task for task in build_tasks({}, Registry(self.COMPANIES), FakeStore())}
        http = FakeHttp(workday_route)
        http.requests = 40     # the shared client has already served other sources
        result = tasks['ats:workday:acme'].run(http, {})
        self.assertEqual((result['label'], result['status'], result['kept'], result['requests']), ('Acme Bank', 'ok', 1, 3))
        result = tasks['board:hirist'].run(FakeHttp(lambda url, payload: {'data': HiristTests.ROWS, 'totalPages': 1}), {})
        self.assertEqual((result['source'], result['kind'], result['kept']), ('Hirist', 'board', 3))
        http = FakeHttp(search_route({('India', 0): card('1', 'Pega Developer', company='Pega')}, {'1': detail('Pega')}))
        ctx = {'window_days': 3, 'store': FakeStore(), 'config': {'linkedin': {'keywords': ['pega'], 'other_cities': []}}}
        result = tasks['linkedin'].run(http, ctx)
        self.assertEqual((result['status'], result['kept']), ('ok', 1))
        # The two flagged employers each get a `pega <name>` query after the keyword queries.
        self.assertEqual(sorted({urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['keywords'][0]
                                 for url in http.urls if 'seeMore' in url}),
                         ['pega', 'pega Acme Bank', 'pega Pegasystems'])

    def test_commit_stores_linkedin_state_once_and_is_harmless_elsewhere(self):
        tasks = {task.name: task for task in build_tasks({}, [], None)}
        store = FakeStore()
        ctx = {'window_days': 3, 'store': store, 'config': {'linkedin': {'keywords': ['pega'], 'other_cities': []}}}
        pages = {('India', 0): card('1', 'Pega Developer'), ('Bengaluru, Karnataka, India', 0): 503}
        tasks['linkedin'].commit()                       # before any run: nothing to store
        result = tasks['linkedin'].run(FakeHttp(search_route(pages, {'1': detail('Pega')})), ctx)
        self.assertEqual((result['kept'], result['sweep_complete'], store.kv), (1, False, {}))
        tasks['linkedin'].commit()
        self.assertEqual(store.kv['linkedin_checkpoint']['done'], [INDIA_QUERY])
        store.kv.clear()
        tasks['linkedin'].commit()                       # a second call has nothing left to store
        self.assertEqual(store.kv, {})
        # A run that raised leaves nothing to commit, and sources without state accept the call.
        tasks['linkedin'].run(FakeHttp(search_route(pages)), {'store': None})
        for task in tasks.values():
            task.commit()
        self.assertEqual(store.kv, {})
        # Nor can an earlier run's state fire after a later run that was skipped for lack of time.
        tasks['linkedin'].run(FakeHttp(search_route(pages, {'1': detail('Pega')})), ctx)
        skipped = tasks['linkedin'].run(FakeHttp(search_route(pages), expired=True), ctx)
        tasks['linkedin'].commit()
        self.assertEqual((skipped['status'], store.kv), ('skipped', {}))

    def test_a_raising_adapter_yields_an_error_result(self):
        def explode(url, payload):
            raise RuntimeError('boom')
        for task in build_tasks({}, Registry(self.COMPANIES), FakeStore()):
            result = task.run(FakeHttp(explode), {'window_days': 3, 'store': FakeStore(), 'config': {}})
            self.assertEqual((result['status'], result['jobs'], result['label'], result['kind']),
                             ('error', [], task.label, task.kind), task.name)
            self.assertIn('RuntimeError: boom', result['error'])
            self.assertEqual(result['source'], 'Employer site' if task.kind == 'ats' else task.label)
        result = Task('board:x', 'X', 'board', 30, lambda http, ctx: 1 / 0).run(FakeHttp(lambda url, payload: 200), {})
        self.assertEqual((result['status'], result['source']), ('error', 'X'))
        self.assertIn('ZeroDivisionError', result['error'])

    def test_a_broken_registry_entry_is_an_error_for_that_employer_only(self):
        tasks = build_tasks({}, [{'name': 'Typo Corp', 'type': 'gcc', 'bengaluru': None, 'ats': {'kind': 'workday'}},
                                 {'name': 'Odd Corp', 'type': 'gcc', 'bengaluru': None, 'ats': {'kind': 'taleo'}}], None)
        for task in tasks[1:3]:
            result = task.run(FakeHttp(lambda url, payload: 200), {})
            self.assertEqual((result['status'], result['source'], result['label']), ('error', 'Employer site', task.label))

    def test_a_task_started_after_the_time_budget_is_skipped(self):
        http = FakeHttp(lambda url, payload: 200, expired=True)
        for task in build_tasks({}, self.COMPANIES, None):
            result = task.run(http, {'store': FakeStore()})
            self.assertEqual(result['status'], 'skipped', task.name)
        self.assertEqual(http.requests, 0)

    def test_every_result_uses_a_known_status(self):
        for route in (lambda url, payload: 200, lambda url, payload: 429, lambda url, payload: {}):
            for task in build_tasks({}, self.COMPANIES, None):
                result = task.run(FakeHttp(route), {'window_days': 3, 'store': FakeStore(), 'config': {
                    'linkedin': {'keywords': ['pega'], 'other_cities': []}}})
                self.assertIn(result['status'], STATUSES, task.name)
                self.assertNotEqual(result['status'] in ('ok', 'empty'), bool(result['error']), task.name)

    def test_answers_that_carry_no_listing_never_pass_as_no_openings(self):
        # `{}` is what a changed API, a consent page or a soft block looks like to a JSON client.
        for route in (lambda url, payload: {}, lambda url, payload: '<html>Please sign in</html>',
                      lambda url, payload: 429, lambda url, payload: 503):
            for task in build_tasks({}, self.COMPANIES, None):
                result = task.run(FakeHttp(route), {'window_days': 3, 'store': FakeStore(), 'config': {
                    'linkedin': {'keywords': ['pega'], 'other_cities': []}}})
                self.assertIn(result['status'], ('error', 'blocked'), task.name)
                self.assertEqual(result['jobs'], [], task.name)


class CompaniesFileTests(unittest.TestCase):
    ATS_KEYS = {'workday': {'kind', 'tenant', 'datacentre', 'site'}, 'oracle': {'kind', 'host', 'site'},
                'greenhouse': {'kind', 'board'}, 'lever': {'kind', 'board'}}

    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / 'companies.json').read_text(encoding='utf-8')
        cls.companies = json.loads(cls.text)['companies']

    def test_every_entry_follows_the_schema(self):
        self.assertGreater(len(self.companies), 150)
        for company in self.companies:
            name = company.get('name')
            self.assertEqual(set(company) - {'ats', 'current_employer'},
                             {'name', 'aliases', 'type', 'bengaluru', 'linkedin_query'}, name)
            self.assertTrue(isinstance(name, str) and name.strip() == name and name, name)
            self.assertIn(company['type'], ('product', 'gcc', 'services', 'staffing', 'enterprise'), name)
            self.assertIn(company['bengaluru'], (True, False, None), name)
            self.assertIsInstance(company['linkedin_query'], bool, name)
            self.assertIsInstance(company['aliases'], list, name)
            self.assertTrue(all(isinstance(alias, str) and alias.strip() for alias in company['aliases']), name)

    def test_names_and_aliases_identify_one_employer_each(self):
        owners = {}
        for company in self.companies:
            for label in {company_key(text) for text in (company['name'], *company['aliases'])}:
                self.assertTrue(label, company['name'])
                self.assertNotIn(label, owners, f"{company['name']} and {owners.get(label)} share {label!r}")
                owners[label] = company['name']

    def test_the_file_is_sorted_by_name(self):
        names = [company['name'] for company in self.companies]
        self.assertEqual(names, sorted(names, key=str.casefold))

    def test_every_ats_block_has_the_keys_its_kind_needs(self):
        blocks = [company['ats'] for company in self.companies if 'ats' in company]
        self.assertGreater(len(blocks), 70)
        for company in self.companies:
            block = company.get('ats')
            if block is None:
                continue
            self.assertIn(block.get('kind'), self.ATS_KEYS, company['name'])
            self.assertEqual(set(block) - {'more_sites'}, self.ATS_KEYS[block['kind']], company['name'])
            sites = block.get('more_sites', [])
            self.assertTrue(block['kind'] == 'workday' or not sites, company['name'])
            for value in [*(block[key] for key in self.ATS_KEYS[block['kind']]), *sites]:
                self.assertRegex(value, r'^[A-Za-z0-9._-]+$', company['name'])
        endpoints = [json.dumps(block, sort_keys=True) for block in blocks]
        self.assertEqual(len(endpoints), len(set(endpoints)))

    def test_linkedin_queries_are_for_bengaluru_product_and_captive_employers(self):
        flagged = [company for company in self.companies if company['linkedin_query']]
        self.assertTrue(20 <= len(flagged) <= 60, len(flagged))
        for company in flagged:
            self.assertIn(company['type'], ('product', 'gcc'), company['name'])
            self.assertIs(company['bengaluru'], True, company['name'])

    def test_research_corrections_are_in_place(self):
        by_name = {company['name']: company for company in self.companies}
        # "No Pega team found" is unknown, not a researched absence.
        for name in ('Target', "Lowe's", 'Capital One', 'Philips', 'Visa', 'Bosch', 'Fidelity Investments',
                     'State Street', 'Maersk', 'BNY', 'John Deere', 'Ford', 'ING'):
            self.assertIsNone(by_name[name]['bengaluru'], name)
        # Boards that are not this employer's India careers site are not searched.
        for name in ('NTT DATA', 'BD', 'Toyota'):
            self.assertNotIn('ats', by_name[name], name)
        for name in ('HDFC Bank', 'ICICI Bank', 'Kotak Mahindra Bank', 'IFFCO Tokio', 'ITC Limited'):
            self.assertEqual(by_name[name]['type'], 'enterprise', name)
        self.assertEqual(by_name['Horizontal']['type'], 'staffing')
        current = [company for company in self.companies if company.get('current_employer')]
        self.assertEqual([company['name'] for company in current], ['Mercedes-Benz Research and Development India'])
        self.assertIs(current[0]['current_employer'], True)
        self.assertFalse(current[0]['linkedin_query'])

    def test_the_real_registry_builds_uniquely_named_tasks(self):
        tasks = build_tasks({}, self.companies, None)
        names = [task.name for task in tasks]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(names[0], 'linkedin')
        self.assertEqual(len(tasks), 1 + sum('ats' in company for company in self.companies) + len(boards.BOARDS))
        self.assertEqual([task.priority for task in tasks], sorted(task.priority for task in tasks))


class EndToEndTests(unittest.TestCase):
    """Real build_tasks, real orchestrator and a real Store on disk; only the HTTP client is fake."""

    COMPANIES = {'companies': [
        {'name': 'Acme', 'aliases': [], 'type': 'gcc', 'bengaluru': True, 'linkedin_query': True, 'ats': WORKDAY},
        {'name': 'Bank', 'aliases': [], 'type': 'gcc', 'bengaluru': None, 'linkedin_query': False,
         'ats': OracleTests.BLOCK},
        {'name': 'Leverco', 'aliases': [], 'type': 'product', 'bengaluru': None, 'linkedin_query': False,
         'ats': {'kind': 'lever', 'board': 'leverco'}},
        {'name': 'Greenco', 'aliases': [], 'type': 'services', 'bengaluru': None, 'linkedin_query': False,
         'ats': {'kind': 'greenhouse', 'board': 'greenco'}}]}

    @staticmethod
    def live(url, payload):
        host = urllib.parse.urlsplit(url).hostname
        if host == 'www.linkedin.com':
            return search_route({('Bengaluru, Karnataka, India', 0): card('501', 'Pega Developer', company='Initech')
                                 + card('502', 'Software Engineer', company='Initech')},
                                {'501': detail('Build Pega applications.'), '502': detail('Our Pega PRPC platform.')})(url, payload)
        if host.endswith('myworkdayjobs.com'):
            return workday_route(url, payload)
        if host.endswith('oraclecloud.com'):
            return OracleTests.route(url, payload)
        if host == 'api.lever.co':
            return [{'id': 'l1', 'text': 'Pega Engineer', 'hostedUrl': 'https://jobs.lever.co/leverco/l1',
                     'categories': {'location': 'Bengaluru'}, 'descriptionPlain': 'Pega', 'createdAt': 1794479644806}]
        if host == 'boards-api.greenhouse.io':
            return {'jobs': []}
        if host == 'www.instahyre.com':
            return {'meta': {'next': None}, 'objects': [{'id': 1, 'title': 'Pega Developer', 'locations': 'Bangalore',
                                                         'public_url': 'https://www.instahyre.com/job-1',
                                                         'employer': {'company_name': 'Hooli'}}]}
        if host == 'cutshort.io':
            return fixture('cutshort.html')
        if host == 'www.shine.com':
            return ShineTests.route(url, payload)
        if host == 'gladiator.hirist.tech':
            return {'data': HiristTests.ROWS, 'totalPages': 1}
        if host == 'tjapi.timesjobs.com':
            return TimesJobsTests.route(url, payload)
        raise AssertionError('unexpected request to ' + url)

    def scan(self, route):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            companies = Path(folder) / 'companies.json'
            companies.write_text(json.dumps(self.COMPANIES), encoding='utf-8')
            config = load_config()
            config['companies_path'] = str(companies)
            config['linkedin'].update(keywords=['pega'], other_cities=[])
            store = Store(Path(folder) / 'data' / 'radar.sqlite3')
            summary = run_scan(config, store, http=FakeHttp(route), minutes=5)
            rows, total = store.jobs(view='all', limit=200)
            return summary, rows, total, store.kv_get('linkedin_checkpoint')

    def test_a_scan_over_every_source_stores_the_jobs(self):
        summary, rows, total, checkpoint = self.scan(self.live)
        statuses = {source['label']: source['status'] for source in summary['sources']}
        self.assertEqual(statuses, {'LinkedIn': 'ok', 'Acme': 'ok', 'Bank': 'ok', 'Leverco': 'ok', 'Greenco': 'empty',
                                    'Instahyre': 'ok', 'Cutshort': 'ok', 'Shine': 'ok', 'Hirist': 'ok',
                                    'TimesJobs': 'ok'})
        self.assertEqual((summary['status'], summary['attention']), ('complete', []))
        kept = sum(source['kept'] for source in summary['sources'])
        self.assertEqual(kept, 2 + 1 + 2 + 1 + 1 + 2 + 3 + 3 + 2)
        # Nothing a source returned was discarded on the way into the database.
        self.assertEqual(summary['new'], total)
        self.assertGreaterEqual(total, 14)
        titles = {row['title'] for row in rows}
        self.assertLessEqual({'Pega Developer', 'Software Engineer', 'Senior Software Engineer - Pega',
                              'Software Engineer III', 'Pega Engineer', 'Pega Lead System Architect'}, titles)
        self.assertIsNone(checkpoint)

    def test_a_scan_in_which_every_answer_is_an_empty_object_reports_no_source_as_read(self):
        summary, rows, total, checkpoint = self.scan(lambda url, payload: {})
        self.assertEqual(len(summary['sources']), 10)
        for source in summary['sources']:
            self.assertEqual(source['status'], 'error', source['label'])
            self.assertTrue(source['error'], source['label'])
        self.assertEqual((summary['status'], total), ('partial', 0))
        self.assertEqual(sorted(summary['attention']), sorted(source['label'] for source in summary['sources']))
        # The orchestrator committed LinkedIn's state after saving its (empty) result: nothing is marked done.
        self.assertEqual(checkpoint['done'], [])


if __name__ == '__main__':
    unittest.main()
