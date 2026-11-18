"""Offline tests for the core: model, net, store, rank, scan and the CLI.

No test touches the network: the HTTP client runs against a scripted opener on a fake
clock, and the scan runs fake tasks.
"""
from __future__ import annotations

import contextlib
import csv
import gzip
import importlib.util
import io
import json
import socket
import ssl
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from radar import acceptance, model, net, rank, scan  # noqa: E402
from radar import store as radar_store  # noqa: E402
from radar.store import Store, title_key  # noqa: E402

TODAY = date(2026, 11, 14)


# ───────────────────────────── model ─────────────────────────────

class ModelTextTest(unittest.TestCase):
    def test_pega_is_matched_as_a_whole_word(self):
        for text in ('Pega Developer', 'Senior PRPC engineer', 'pegasystems', 'PegaRULES', 'Lead (PEGA)', 'Pega-CDH'):
            self.assertTrue(model.is_pega(text), text)
        for text in ('Pegasus Airlines', 'Pegatron hardware engineer', 'Project Pegasus', '', None, 'Java developer',
                     'Pegasus', 'Pegatron', 'PEGASUS_ENGINEER', 'Omega developer', 'Spegatti',
                     'Pegaso', 'Pegasi', 'Pegasos', 'Pegasis', 'Pegah Rahimi', 'Pegadaian', 'Pegatec', 'PEGASO', 'PEGASUS',
                     'PRPCS', 'prpcx'):
            self.assertFalse(model.is_pega(text), text)

    def test_pega_glued_to_its_neighbours_still_matches(self):
        for text in ('Pega_Developer_Bangalore', 'PRPC_Dev', 'Pega8 Developer', 'Pega7.4 SSA', 'PegaDeveloper',
                     'Sr.Pega Architect', '#pega', 'PegaRULES Process Commander', 'Pegasystems Inc', 'PEGA', 'pega',
                     'PRPC8', 'PegaPRPC', 'pegasystems', 'PegaCSSA'):
            self.assertTrue(model.is_pega(text), text)

    def test_all_caps_pega_needs_a_known_word_after_it(self):
        # "PEGADEVELOPER" cannot be told from "PEGASO" by capitals alone, so glued upper- or lower-case text
        # matches only when a role or product word follows.
        for text in ('PEGADEVELOPER', 'PEGAARCHITECT', 'pegadeveloper', 'PEGACSSA', 'PEGA_DEVELOPER', 'PEGA8'):
            self.assertTrue(model.is_pega(text), text)
        for text in ('PEGAXYZ', 'pegadevil', 'PEGALEADERSHIP'):
            self.assertFalse(model.is_pega(text), text)
        for text in ('PEGADECISIONING', 'pegarobotics', 'Pegasystem', 'PEGASYSTEM', 'pegacdh', 'PEGACSSA', 'pegaclsa',
                     'PEGALSA', 'pegacsa', 'PEGASSA', 'pegabpm', 'PEGACRM', 'pegaplatform', 'PEGAINFINITY',
                     'pegaconstellation', 'PEGACONSULTANT', 'pegaengineer', 'PEGAARCHITECT', 'pegalead', 'PEGAADMIN',
                     'pegatester', 'PEGATESTING', 'pegasupport', 'PEGAANALYST', 'pegaspecialist'):
            self.assertTrue(model.is_pega(text), text)

    def test_camel_case_does_not_rescue_the_look_alikes(self):
        for text in ('PegaSus', 'PegaTron', 'PegaSo', 'PegaSi', 'PegaSos', 'PegaSis', 'PegaH', 'PegaDaian', 'PegaTec',
                     'PegaSUS Airlines', 'pegaTRON'):
            self.assertFalse(model.is_pega(text), text)
        for text in ('PegaSolutions', 'PegaHealthcare', 'PegaTechLead', 'PegaDeveloper', 'PegaSSA'):
            self.assertTrue(model.is_pega(text), text)

    def test_codes_shared_with_indian_states_are_not_foreign_on_their_own(self):
        for text in ('Siruseri, TN', 'Hosur, TN', 'Panaji, GA', 'Rourkela, OR', 'Itanagar, AR', 'Raipur, CT', 'Imphal, MN',
                     'Dehradun, UK', 'Leh, LA', 'Remote, KA', 'Nagar, MH', 'Guntur, AP', 'Siddipet, TS', 'Kannur, KL',
                     'Durgapur, WB', 'Dwarka, DL', 'Hisar, HR', 'Agra, UP', 'Rajkot, GJ', 'Kota, RJ', 'Gwalior, MP',
                     'Ludhiana, PB', 'Gaya, BR', 'Ranchi, JH', 'Dispur, AS', 'Shimla, HP', 'Bilaspur, CG'):
            self.assertFalse(model.outside_india(text), text)
        for text in ('Nashville, TN, United States', 'Atlanta, GA, USA', 'Portland, OR, US', 'Little Rock, AR, United States',
                     'Stamford, CT, USA', 'St. Paul, MN, United States', 'Reading, UK, United Kingdom', 'London, UK'):
            self.assertTrue(model.outside_india(text), text)

    def test_in_is_indiana_when_the_text_is_american(self):
        for text in ('Indianapolis, IN, United States', 'Fort Wayne, IN, USA', 'Carmel, IN, U.S.', 'Evansville, IN 47708, US'):
            self.assertFalse(model.is_india(text), text)
            self.assertTrue(model.outside_india(text), text)
        for text in ('Bengaluru, IN', 'IN-KA-BLR', 'IN-KA', 'IN', 'Remote, IN', 'Pune, MH, IN'):
            self.assertTrue(model.is_india(text), text)
            self.assertFalse(model.outside_india(text), text)

    def test_bengaluru_localities_yield_to_a_named_city_or_country(self):
        cases = {'Ecospace Business Park, New Town, Kolkata': ['Kolkata'],
                 'Outer Ring Road, Gachibowli, Hyderabad': ['Hyderabad'],
                 'Electronic City, Sector 62, Noida': ['Noida'],
                 'Hebbal Industrial Area, Mysuru': ['Mysuru'],
                 'Whitefield, New Hampshire, United States': [],
                 'Manyata Tech Park': ['Bengaluru'],
                 'Whitefield, Bengaluru': ['Bengaluru'],
                 'Whitefield, Karnataka, India': ['Bengaluru'],
                 'Bagmane Tech Park, Bangalore / Hyderabad': ['Bengaluru', 'Hyderabad']}
        for text, expected in cases.items():
            self.assertEqual(model.cities(text), expected, text)
            self.assertEqual(model.is_bengaluru(text), 'Bengaluru' in expected, text)
        self.assertFalse(model.is_india('Whitefield, New Hampshire, United States'))
        self.assertTrue(model.outside_india('Whitefield, New Hampshire, United States'))

    def test_outside_india_knows_countries_and_us_city_state_pairs(self):
        for text in ('Bratislava, Slovakia', 'Vilnius, Lithuania', 'Luxembourg', 'Korea, Republic of', 'Krakow, Poland',
                     'Cork, Ireland', 'Eindhoven, Netherlands', 'Manila, Philippines', 'Cyberjaya, Malaysia',
                     'Guadalajara, Mexico', 'São Paulo, Brazil', 'Dubai, UAE', 'Columbus, OH', 'Plano, TX',
                     'Charlotte, NC 28202', 'Remote, FL', 'Hartford, CT, US', 'Ontario, Canada'):
            self.assertTrue(model.outside_india(text), text)
            self.assertFalse(model.is_india(text), text)
        for text in ('Chennai, TN', 'Bhubaneswar, OR', 'Hyderabad, Telangana / Plano, TX', 'Goa', 'Noida, UP'):
            self.assertFalse(model.outside_india(text), text)

    def test_csv_cell_neutralises_formulas_after_leading_whitespace(self):
        for text in ('=1+1', ' =1+1', '\n@SUM(1)', ' +1', '\t=cmd', '  -2+3', '@x', '\r=1', '-called HR'):
            self.assertEqual(model.csv_cell(text), "'" + text, repr(text))
        for value, expected in (('Pega Developer', 'Pega Developer'), ('a = b', 'a = b'), (None, ''), (True, 'yes'),
                                (False, 'no'), (-4.5, '-4.5'), (30, '30'), (['LinkedIn', 'Hirist'], 'LinkedIn; Hirist'),
                                (['=x'], "'=x"), ({'b': 1, 'a': '₹'}, '{"a": "₹", "b": 1}'), ('', '')):
            self.assertEqual(model.csv_cell(value), expected, repr(value))

    def test_states_misspellings_localities_and_codes(self):
        bengaluru = ('Banglore', 'Bangaluru', 'Bengalore', 'Bengalooru', 'BLR', 'Manyata Tech Park', 'Whitefield',
                     'Electronic City Phase 1', 'Embassy Golf Links', 'Bagmane Tech Park', 'RMZ Ecospace',
                     'Outer Ring Road', 'Koramangala', 'Marathahalli', 'Bellandur', 'Hebbal', 'Yelahanka', 'IN-KA-BLR')
        for text in bengaluru:
            self.assertEqual(model.cities(text), ['Bengaluru'], text)
            self.assertTrue(model.is_bengaluru(text) and model.is_india(text), text)
        others = {'Hydrabad': 'Hyderabad', 'Hyd': 'Hyderabad', 'Gurgoan': 'Gurugram', 'Chenai': 'Chennai',
                  'Mumabi': 'Mumbai', 'Navi Mumbai': 'Mumbai', 'Thane': 'Thane', 'Mangalore': 'Mangaluru',
                  'Mangaluru': 'Mangaluru', 'Madurai': 'Madurai', 'Gandhinagar': 'Gandhinagar', 'Vijayawada': 'Vijayawada',
                  'Nashik': 'Nashik', 'Surat': 'Surat', 'Hubli': 'Hubballi', 'Hubballi': 'Hubballi', 'Belagavi': 'Belagavi',
                  'Bhopal': 'Bhopal', 'Patna': 'Patna', 'Guwahati': 'Guwahati', 'Trichy': 'Tiruchirappalli',
                  'Tiruchirappalli': 'Tiruchirappalli', 'Salem': 'Salem', 'Warangal': 'Warangal',
                  'Greater Noida': 'Noida', 'Faridabad': 'Faridabad', 'Ghaziabad': 'Ghaziabad'}
        for text, city in others.items():
            self.assertEqual(model.cities(text), [city], text)
        for state in model.INDIAN_STATES + ('IN-KA', 'IN', ' IN ', 'Remote, IN', 'Karnataka, IN'):
            self.assertTrue(model.is_india(state), state)
            self.assertEqual(model.cities(state), [], state)                # a state is India, not a city
            self.assertFalse(model.is_bengaluru(state), state)
        for text in ('Join in our team', 'IN-HOUSE role', 'Remote', 'Work From Home', '2 Locations', ''):
            self.assertFalse(model.is_india(text), text)

    def test_outside_india_needs_a_positive_foreign_place(self):
        for text in ('London, United Kingdom', 'New York, NY', 'Austin, TX, USA', 'Sydney', 'Singapore', 'Dubai, UAE',
                     'Remote - US', 'Toronto, Canada', 'Krakow, Poland', 'Indiana, US'):
            self.assertTrue(model.outside_india(text), text)
        for text in ('', None, 'Remote', 'Work From Home', '2 Locations', 'Multiple locations', 'Hybrid', 'Bengaluru',
                     'Hyderabad or London', 'India / Singapore', 'IN-KA-BLR', 'Karnataka', 'Pune, IN', 'Anywhere',
                     'Usability Lab, Floor 3', 'Salem, Tamil Nadu'):
            self.assertFalse(model.outside_india(text), text)

    def test_salary_lpa_ignores_foreign_currency(self):
        self.assertEqual(model.salary_lpa('20-35 Lacs PA'), (20.0, 35.0))
        self.assertEqual(model.salary_lpa('₹12L - ₹20L / yr'), (12.0, 20.0))
        self.assertEqual(model.salary_lpa('Up to 32 LPA'), (None, 32.0))
        self.assertEqual(model.salary_lpa('32 LPA'), (32.0, 32.0))
        self.assertEqual(model.salary_lpa('24 Lacs P.A.'), (24.0, 24.0))             # per annum is not per month
        self.assertEqual(model.salary_lpa('18.5 lakhs to 24 lakhs'), (18.5, 24.0))
        self.assertEqual(model.salary_lpa('₹8.5L - ₹1.2Cr / yr'), (8.5, 120.0))     # crore amounts count
        self.assertEqual(model.salary_lpa('80 Lacs - 1 Crore'), (80.0, 100.0))
        self.assertEqual(model.salary_lpa('Upto ₹20L'), (None, 20.0))               # a ceiling says nothing of the floor
        self.assertEqual(model.salary_lpa('Max 25 LPA'), (None, 25.0))
        self.assertEqual(model.salary_lpa('INR 15,00,000'), (None, None))
        self.assertEqual(model.salary_lpa('5000 L of fuel'), (None, None))
        for text in ('$120k - $150k', 'USD 30L', '£60,000', '€55L', '90,000 USD per year', 'Not disclosed', '', None,
                     '₹1.5L - ₹2L / mo', '₹90K - ₹1.5L / mo', '2 Lakhs per month', '1.8L monthly', '2L pm', '1.5 L p.m.'):
            self.assertEqual(model.salary_lpa(text), (None, None), text)

    def test_city_aliases_fold_to_canonical_names(self):
        self.assertEqual(model.cities('Bangalore Urban, Karnataka'), ['Bengaluru'])
        self.assertEqual(model.cities('Gurgaon / Gurugram / New Delhi'), ['Gurugram', 'Delhi'])
        self.assertEqual(model.cities('Hyderabad, Bengaluru, bangalore, Navi Mumbai'), ['Hyderabad', 'Bengaluru', 'Mumbai'])
        self.assertEqual(model.cities('Trivandrum; Cochin; Mysore; Vizag'),
                         ['Thiruvananthapuram', 'Kochi', 'Mysuru', 'Visakhapatnam'])
        self.assertEqual(model.cities('London, United Kingdom'), [])
        self.assertEqual(model.cities(None), [])

    def test_city_must_be_a_whole_word(self):
        self.assertEqual(model.cities('Punearea Chennaiside'), [])

    def test_is_india_and_is_bengaluru(self):
        self.assertTrue(model.is_india('Pune, Maharashtra'))
        self.assertTrue(model.is_india('Remote - India'))
        self.assertFalse(model.is_india('Indiana, United States'))
        self.assertTrue(model.is_bengaluru('Bangalore, India'))
        self.assertTrue(model.is_bengaluru('Hyderabad or Bengaluru'))
        self.assertFalse(model.is_bengaluru('Hyderabad'))

    def test_strip_html(self):
        html = ('<style>p{color:red}</style><p>Design &amp; build <b>Pega</b>&nbsp;apps</p>'
                '<ul><li>Case&#39;s</li><li>Rules</li></ul><script>alert(1)</script><!-- note -->Done<br/>End')
        self.assertEqual(model.strip_html(html), "Design & build Pega apps\nCase's\nRules\nDone\nEnd")
        self.assertEqual(model.strip_html(None), '')

    def test_now_iso_is_utc_to_the_second(self):
        stamp = model.now_iso()
        self.assertRegex(stamp, r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$')
        self.assertEqual(datetime.fromisoformat(stamp).tzinfo, timezone.utc)

    def test_company_key_drops_legal_suffixes(self):
        self.assertEqual(model.company_key('Acme Technologies India Pvt. Ltd.'), 'acmetechnologies')
        self.assertEqual(model.company_key('ACME Technologies Private Limited'), 'acmetechnologies')
        self.assertEqual(model.company_key('Mercedes-Benz Research and Development India'), 'mercedesbenzresearchanddevelopment')
        self.assertEqual(model.company_key('IndiaMART InterMESH Ltd'), 'indiamartintermesh')
        self.assertEqual(model.company_key('India Ltd'), 'indialtd')   # nothing left otherwise
        self.assertEqual(model.company_key(None), '')


class ModelShapeTest(unittest.TestCase):
    def test_make_job_has_exactly_the_contract_keys(self):
        job = model.make_job('LinkedIn', 4211, '  Pega Developer ', 'Acme', 'https://x.test/1', 'Bengaluru')
        self.assertEqual(set(job), {'source', 'source_id', 'title', 'company', 'url', 'location', 'posted_at',
                                    'description', 'experience_min', 'experience_max', 'salary_min_lpa',
                                    'salary_max_lpa', 'apply_url', 'requisition_id', 'employment_type', 'extra'})
        self.assertEqual(job['source_id'], '4211')
        self.assertEqual(job['title'], 'Pega Developer')
        self.assertEqual(job['description'], '')
        self.assertIsNone(job['posted_at'])
        self.assertEqual(job['extra'], {})

    def test_make_job_normalises_values(self):
        job = model.make_job('Hirist', 'h1', 'T', 'C', 'u', 'L', posted_at='2026-11-02T08:00:00Z', experience_min='4',
                             experience_max=7, salary_max_lpa='32.5', requisition_id=' R-9 ', apply_url='')
        self.assertEqual(job['posted_at'], '2026-11-02')
        self.assertEqual((job['experience_min'], job['experience_max'], job['salary_max_lpa']), (4.0, 7.0, 32.5))
        self.assertEqual(job['requisition_id'], 'R-9')
        self.assertIsNone(job['apply_url'])
        self.assertIsNone(model.make_job('s', '1', 't', 'c', 'u', 'l', posted_at='3 days ago')['posted_at'])

    def test_make_result(self):
        jobs = [model.make_job('Hirist', '1', 'Pega Developer', 'Acme', 'u', 'Pune')]
        result = model.make_result('Hirist', 'Hirist', 'board', jobs=jobs, found=40, requests=3)
        self.assertEqual(set(result), {'source', 'label', 'kind', 'status', 'found', 'kept', 'requests', 'error',
                                       'reason', 'jobs'})
        self.assertEqual(result['reason'], '')
        self.assertEqual((result['status'], result['found'], result['kept'], result['requests']), ('ok', 40, 1, 3))
        self.assertIsNone(result['error'])
        self.assertEqual(model.make_result('s', 'l', 'ats', jobs=jobs)['found'], 1)   # never fewer seen than kept
        with self.assertRaises(ValueError):
            model.make_result('s', 'l', 'board', status='fine')
        with self.assertRaises(ValueError):
            model.make_result('s', 'l', 'forum')
        self.assertNotIn('sweep_complete', result)                     # present only when the source says so
        swept = model.make_result('LinkedIn', 'LinkedIn', 'linkedin', status='partial', sweep_complete=True)
        self.assertIs(swept['sweep_complete'], True)
        self.assertIs(model.make_result('LinkedIn', 'LinkedIn', 'linkedin', sweep_complete=False)['sweep_complete'], False)

    def test_make_result_passes_through_the_optional_coverage_keys(self):
        result = model.make_result('Employer site', 'Acme', 'ats', status='partial', reason='timeout', elapsed_s=12.345,
                                   pages_complete=False, details_complete=1, employer='Acme', error='page 3 timed out')
        self.assertEqual((result['reason'], result['elapsed_s'], result['pages_complete'], result['details_complete'],
                          result['employer']), ('timeout', 12.3, False, True, 'Acme'))
        plain = model.make_result('Hirist', 'Hirist', 'board')
        for key in ('elapsed_s', 'pages_complete', 'details_complete', 'employer', 'sweep_complete'):
            self.assertNotIn(key, plain)

    def test_needs_attention(self):
        flagged = {status: model.needs_attention({'status': status}) for status in model.STATUSES}
        self.assertEqual(flagged, {'ok': False, 'empty': False, 'partial': True, 'blocked': True,
                                   'maintenance': True, 'skipped': True, 'error': True})


class ConfigTest(unittest.TestCase):
    def test_missing_file_gives_defaults(self):
        config = model.load_config(Path(tempfile.gettempdir()) / 'pega-radar-no-such-config.json')
        self.assertEqual(config, model.DEFAULT_CONFIG)
        config['scan']['minutes'] = 1
        self.assertEqual(model.DEFAULT_CONFIG['scan']['minutes'], 40)   # a copy, not the shared defaults

    def test_missing_keys_fall_back_and_given_keys_win(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'config.json'
            path.write_text('﻿' + json.dumps({'profile': {'target_lpa': 36}, 'scan': {'minutes': 15},
                                                   'linkedin': {'keywords': ['pega']}}), encoding='utf-8')
            config = model.load_config(path)
            self.assertEqual(config['profile']['target_lpa'], 36)
            self.assertEqual(config['profile']['career_start'], '2022-08-01')
            self.assertEqual(config['scan'], {'minutes': 15, 'workers': 6})
            self.assertEqual(config['linkedin']['keywords'], ['pega'])
            self.assertEqual(config['linkedin']['detail_budget'], 300)
            path.write_text('{not json', encoding='utf-8')
            self.assertEqual(model.load_config(path), model.DEFAULT_CONFIG)

    def test_shipped_config_matches_the_defaults(self):
        shipped = json.loads((PROJECT / 'config.json').read_text(encoding='utf-8'))
        self.assertEqual(shipped, model.DEFAULT_CONFIG)
        self.assertFalse(any('Bengaluru' in city for city in shipped['linkedin']['other_cities']))


# ───────────────────────────── net ─────────────────────────────

class FakeClock:
    def __init__(self):
        self.now = 1000.0
        self.sleeps = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(round(seconds, 3))
        self.now += seconds


class FakeReply:
    def __init__(self, status=200, body=b'{}', headers=None, url=None):
        self.status, self._body, self.headers, self._url = status, body, headers or {}, url
        self.closed = False

    def read(self, size=-1):
        return self._body if size < 0 else self._body[:size]

    def geturl(self):
        return self._url or 'https://final.test/'

    def close(self):
        self.closed = True


class ScriptedOpener:
    """Plays back replies in order; the last one repeats. Statuses >= 400 are raised like urllib does."""

    def __init__(self, *script):
        self.script = list(script)
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append(request)
        item = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(item, BaseException):
            raise item
        if item.status >= 400:
            raise urllib.error.HTTPError(request.full_url, item.status, 'refused', item.headers, io.BytesIO(item._body))
        return item


class NetTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch('radar.net.random.uniform', return_value=0.0)   # no jitter: exact waits
        patcher.start()
        self.addCleanup(patcher.stop)
        self.clock = FakeClock()

    def client(self, *script, **options):
        self.opener = ScriptedOpener(*script)
        http = net.Http(opener=self.opener, **options)
        http._clock, http._sleep = self.clock.clock, self.clock.sleep
        return http

    def test_get_returns_the_body_and_headers(self):
        http = self.client(FakeReply(body=b'{"jobs": [1]}', headers={'X-Total': '7'}, url='https://a.test/final'))
        response = http.get('https://a.test/jobs', headers={'X-Extra': '1'})
        self.assertTrue(response.ok)
        self.assertFalse(response.blocked)
        self.assertEqual(response.json(), {'jobs': [1]})
        self.assertEqual(response.header('x-total'), '7')
        self.assertIsNone(response.header('missing'))
        self.assertEqual((response.url, response.error, http.requests), ('https://a.test/final', '', 1))
        request = self.opener.calls[0]
        self.assertEqual(request.get_header('X-extra'), '1')
        self.assertEqual(request.get_header('Accept'), 'application/json')
        self.assertEqual(request.get_header('User-agent'), net.USER_AGENT)
        self.assertEqual(sorted(request.headers), ['Accept', 'Accept-encoding', 'Accept-language', 'User-agent',
                                                   'X-extra'])   # nothing else is sent: no cookies, no referer

    def test_user_agent_is_a_setting(self):
        http = self.client(FakeReply(), user_agent='ExampleAgent/2.0')
        http.get('https://a.test/x')
        http.post_json('https://a.test/y', {})
        self.assertEqual([request.get_header('User-agent') for request in self.opener.calls], ['ExampleAgent/2.0'] * 2)
        self.assertEqual(net.Http().user_agent, model.DEFAULT_CONFIG['http']['user_agent'])

    def test_pacing_is_honoured_per_host(self):
        http = self.client(FakeReply(), pacing={'slow.test': 2.0}, default_pacing=0.5)
        for _ in range(3):
            http.get('https://slow.test/a')
        self.assertEqual(self.clock.sleeps, [2.0, 2.0])
        http.get('https://other.test/a')            # a different host does not wait for slow.test
        http.get('https://other.test/b')
        self.assertEqual(self.clock.sleeps, [2.0, 2.0, 0.5])
        self.assertEqual(http.host_report()['slow.test'], {'requests': 3, 'blocked': 0, 'errors': 0, 'pacing': 2.0})

    def test_jitter_only_ever_lengthens_the_gap(self):
        with mock.patch('radar.net.random.uniform', return_value=net.JITTER):
            http = self.client(FakeReply(), default_pacing=4.0)
            http.get('https://a.test/1')
            http.get('https://a.test/2')
        self.assertEqual(self.clock.sleeps, [5.0])

    def test_retry_after_is_honoured(self):
        http = self.client(FakeReply(503, headers={'Retry-After': '7'}), FakeReply(body=b'ok'), default_pacing=0)
        response = http.get('https://a.test/x')
        self.assertTrue(response.ok)
        self.assertEqual(self.clock.sleeps, [7.0])
        self.assertEqual(http.requests, 2)

    def test_429_backs_off_then_succeeds_and_slows_the_host(self):
        http = self.client(FakeReply(429), FakeReply(body=b'fine'), default_pacing=1.0)
        response = http.get('https://a.test/x')
        self.assertEqual((response.status, response.text), (200, 'fine'))
        self.assertEqual(self.clock.sleeps, [4.0])                       # backoff before the retry
        report = http.host_report()['a.test']
        self.assertEqual((report['requests'], report['blocked'], report['pacing']), (2, 1, 2.0))

    def test_pacing_doubles_to_a_cap_and_decays_after_successes(self):
        http = self.client(FakeReply(429), default_pacing=1.0)
        http.get('https://a.test/x', retries=3)                          # four 429s: 2, 4, 8, 8
        self.assertEqual(http.host_report()['a.test']['pacing'], net.PACING_CAP)
        self.opener.script = [FakeReply()]
        for _ in range(net.DECAY_AFTER * 3):
            http.get('https://a.test/x')
        self.assertEqual(http.host_report()['a.test']['pacing'], 1.0)    # back at its base, never below

    def test_429_that_never_clears_is_reported_as_blocked(self):
        http = self.client(FakeReply(429), default_pacing=0)
        response = http.get('https://a.test/x', retries=1)
        self.assertEqual((response.status, response.error), (429, 'HTTP 429'))
        self.assertTrue(response.blocked)
        self.assertEqual(len(self.opener.calls), 2)

    def test_a_reply_object_with_status_429_is_treated_like_a_raised_one(self):
        class Unraised(ScriptedOpener):
            def __call__(self, request, timeout):
                self.calls.append(request)
                return self.script.pop(0) if len(self.script) > 1 else self.script[0]
        http = self.client(default_pacing=0)
        http._opener = opener = Unraised(FakeReply(429, headers={'retry-after': '3'}), FakeReply())
        self.assertTrue(http.get('https://a.test/x').ok)
        self.assertEqual((len(opener.calls), self.clock.sleeps), (2, [3.0]))

    def test_refusals_are_returned_at_once(self):
        for status in (401, 403, 406):
            http = self.client(FakeReply(status, body=b'denied'), default_pacing=0)
            response = http.get('https://a.test/x')
            self.assertTrue(response.blocked)
            self.assertEqual((response.status, response.text, len(self.opener.calls)), (status, 'denied', 1))

    def test_circuit_breaker_opens_after_five_failures(self):
        http = self.client(urllib.error.URLError('connection refused'), default_pacing=0)
        first = http.get('https://down.test/a')                          # attempts 1-3
        self.assertEqual(first.status, 0)
        self.assertIn('URLError', first.error)
        self.assertTrue(http.host_open('https://down.test/a'))
        second = http.get('https://down.test/b')                         # attempts 4-5 trip the breaker
        self.assertIn('URLError', second.error)
        self.assertEqual(len(self.opener.calls), net.BREAKER_THRESHOLD)
        self.assertFalse(http.host_open('https://down.test/anything'))
        self.assertFalse(http.host_open('down.test'))
        third = http.get('https://down.test/c')
        self.assertEqual((third.status, third.error), (0, 'circuit open'))
        self.assertEqual(len(self.opener.calls), net.BREAKER_THRESHOLD)  # nothing more was sent
        self.assertEqual(http.requests, net.BREAKER_THRESHOLD)
        self.assertTrue(http.host_open('https://up.test/'))              # the breaker is per host
        self.assertEqual(http.host_report()['down.test']['errors'], net.BREAKER_THRESHOLD)

    def test_breaker_counts_refusals_and_a_success_resets_it(self):
        http = self.client(FakeReply(403), default_pacing=0)
        for _ in range(4):
            http.get('https://a.test/x')
        self.opener.script = [FakeReply()]
        http.get('https://a.test/x')                                     # streak broken
        self.opener.script = [FakeReply(403)]
        for _ in range(4):
            http.get('https://a.test/x')
        self.assertTrue(http.host_open('a.test'))
        http.get('https://a.test/x')
        self.assertFalse(http.host_open('a.test'))

    def test_a_404_is_an_answer_not_a_failure(self):
        http = self.client(FakeReply(404), default_pacing=0)
        for _ in range(8):
            response = http.get('https://a.test/missing')
        self.assertEqual((response.status, response.ok, response.blocked), (404, False, False))
        self.assertTrue(http.host_open('a.test'))
        self.assertEqual(len(self.opener.calls), 8)                      # no retries either

    def test_gzip_bodies_are_decoded(self):
        packed = gzip.compress('{"title": "Pega ₹ role"}'.encode('utf-8'))
        http = self.client(FakeReply(body=packed, headers={'Content-Encoding': 'gzip'}))
        self.assertEqual(http.get('https://a.test/x').json(), {'title': 'Pega ₹ role'})
        http = self.client(FakeReply(body=b'plain text', headers={'Content-Encoding': 'gzip'}))
        self.assertEqual(http.get('https://a.test/x').text, 'plain text')   # mislabelled, still readable

    def test_oversized_bodies_are_refused_without_a_retry(self):
        with mock.patch.object(net, 'MAX_BODY', 1000):
            http = self.client(FakeReply(body=b'x' * 1001), default_pacing=0)
            response = http.get('https://a.test/huge')
            self.assertEqual((response.status, response.text, response.error, response.ok), (0, '', net.TOO_LARGE, False))
            self.assertEqual(len(self.opener.calls), 1)
            self.assertTrue(self.client(FakeReply(body=b'x' * 1000)).get('https://a.test/just-fits').ok)
            bomb = gzip.compress(b'0' * 50000)                           # 50 kB that travels as a few dozen bytes
            self.assertLess(len(bomb), 1000)
            http = self.client(FakeReply(body=bomb, headers={'Content-Encoding': 'gzip'}), default_pacing=0)
            self.assertEqual(http.get('https://a.test/bomb').error, net.TOO_LARGE)
            http = self.client(FakeReply(500, body=b'x' * 5000), default_pacing=0)
            self.assertEqual(http.get('https://a.test/huge-error').error, net.TOO_LARGE)
        self.assertEqual(net.MAX_BODY, 20 * 1024 * 1024)

    def test_json_is_none_for_non_json(self):
        http = self.client(FakeReply(body=b'<html>'))
        self.assertIsNone(http.get('https://a.test/x', accept='text/html').json())
        self.assertEqual(self.opener.calls[0].get_header('Accept'), 'text/html')

    def test_deadline_expiry_stops_requests(self):
        http = self.client(FakeReply(), deadline=self.clock.now + 5, default_pacing=10)
        self.assertFalse(http.expired())
        self.assertTrue(http.get('https://a.test/1').ok)
        late = http.get('https://a.test/2')                              # next slot is after the deadline
        self.assertEqual((late.status, late.error), (0, 'time budget exhausted'))
        self.assertEqual((len(self.opener.calls), self.clock.sleeps), (1, []))   # and it did not wait for it
        self.clock.now += 6
        self.assertTrue(http.expired())
        self.assertEqual(http.get('https://b.test/1').error, 'time budget exhausted')

    def test_stop_event_stops_requests(self):
        stop = threading.Event()
        http = self.client(FakeReply(), stop=stop)
        stop.set()
        self.assertTrue(http.expired())
        self.assertEqual(http.get('https://a.test/1').error, 'time budget exhausted')
        self.assertEqual(self.opener.calls, [])

    def test_never_raises(self):
        for failure in (TimeoutError('timed out'), ConnectionResetError('reset'), ValueError('bad reply'),
                        urllib.error.URLError('unknown trouble')):
            http = self.client(failure, default_pacing=0)
            response = http.get('https://a.test/x', retries=0)
            self.assertEqual(response.status, 0)
            self.assertTrue(response.error and response.reason, failure)
            self.assertFalse(response.ok or response.blocked)
            self.assertIsNone(response.json())

    def test_network_failures_are_classified_with_readable_text(self):
        cases = (
            (TimeoutError('timed out'), 'timeout', 'Timed out after 25 s waiting for a.test'),
            (urllib.error.URLError(TimeoutError('timed out')), 'timeout', 'Timed out after 25 s waiting for a.test'),
            (urllib.error.URLError(socket.timeout('The read operation timed out')), 'timeout', 'Timed out'),
            (urllib.error.URLError(ssl.SSLCertVerificationError(1, 'certificate verify failed: unable to get local issuer')),
             'tls', 'TLS certificate could not be verified — check proxy/antivirus certificate'),
            (ssl.SSLError(1, 'wrong version number'), 'tls', 'TLS connection to a.test failed'),
            (urllib.error.URLError(socket.gaierror(11001, 'getaddrinfo failed')), 'dns', 'DNS lookup failed for a.test'),
            (urllib.error.URLError(ConnectionRefusedError(10061, 'actively refused')), 'refused', 'Connection refused by a.test'),
            (ConnectionResetError('reset by peer'), 'unreachable', 'Could not reach a.test (ConnectionResetError'),
            (OSError(101, 'Network is unreachable'), 'unreachable', 'Could not reach a.test (OSError'),
            (urllib.error.URLError('no route to host'), 'unreachable', 'Could not reach a.test (URLError'),
            (ValueError('bad chunk'), 'shape', 'Unusable reply from a.test (ValueError: bad chunk)'),
        )
        for failure, reason, text in cases:
            response = self.client(failure, default_pacing=0).get('https://a.test/x', retries=0)
            self.assertEqual(response.reason, reason, failure)
            self.assertIn(text, response.error, failure)

    def test_http_statuses_have_reasons(self):
        for status, reason in ((200, ''), (204, ''), (429, 'rate_limited'), (999, 'rate_limited'), (401, 'refused'),
                               (403, 'refused'), (406, 'refused'), (400, 'http_4xx'), (404, 'http_4xx'), (410, 'http_4xx'),
                               (500, 'http_5xx'), (503, 'http_5xx')):
            response = self.client(FakeReply(status), default_pacing=0).get('https://a.test/x', retries=0)
            self.assertEqual((response.status, response.reason), (status, reason))

    def test_calls_that_were_never_sent_have_reasons_too(self):
        http = self.client(urllib.error.URLError(socket.gaierror(11001, 'getaddrinfo failed')), default_pacing=0)
        http.get('https://down.test/a')
        http.get('https://down.test/b')                                  # the breaker opens on DNS failures
        blocked = http.get('https://down.test/c')
        self.assertEqual((blocked.error, blocked.reason), (net.CIRCUIT_OPEN, 'dns'))   # why the host was given up
        http = self.client(FakeReply(), deadline=self.clock.now - 1)
        late = http.get('https://a.test/x')
        self.assertEqual((late.error, late.reason), (net.BUDGET_SPENT, 'budget'))
        self.assertEqual(self.client(FakeReply()).get('file:///etc/passwd').reason, 'shape')
        with mock.patch.object(net, 'MAX_BODY', 10):
            self.assertEqual(self.client(FakeReply(body=b'x' * 11)).get('https://a.test/x').reason, 'cap')

    def test_tls_verification_is_never_switched_off(self):
        source = (PROJECT / 'radar' / 'net.py').read_text(encoding='utf-8')
        for forbidden in ('CERT_NONE', '_create_unverified_context', 'check_hostname = False', 'verify=False'):
            self.assertNotIn(forbidden, source)

    def test_only_http_urls_are_requested(self):
        http = self.client(FakeReply())
        for url in ('file:///etc/passwd', 'ftp://a.test/x', 'not a url', ''):
            self.assertEqual(http.get(url).error, 'unsupported URL')
        self.assertEqual(self.opener.calls, [])

    def test_post_json_sends_a_json_body(self):
        http = self.client(FakeReply(body=b'{"total": 2}'))
        response = http.post_json('https://a.test/search', {'searchText': 'pega', 'limit': 20})
        self.assertEqual(response.json(), {'total': 2})
        request = self.opener.calls[0]
        self.assertEqual(json.loads(request.data), {'searchText': 'pega', 'limit': 20})
        self.assertEqual(request.get_header('Content-type'), 'application/json')
        self.assertEqual(request.get_method(), 'POST')

    def test_server_errors_are_retried(self):
        http = self.client(FakeReply(500), FakeReply(502), FakeReply(body=b'up'), default_pacing=0)
        self.assertEqual(http.get('https://a.test/x').text, 'up')
        self.assertEqual(self.clock.sleeps, [2.0, 4.0])

    def test_threads_share_one_host_queue(self):
        http = self.client(FakeReply(), default_pacing=1.0)
        threads = [threading.Thread(target=http.get, args=('https://a.test/x',)) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual((http.requests, http.host_report()['a.test']['requests']), (8, 8))


# ───────────────────────────── store ─────────────────────────────

def plain_ranker(job):
    """A ranker with no opinions, for tests that are about storage."""
    return {'employer_type': 'unknown', 'score': 50, 'fit': {'reasons': [], 'labels': {}},
            'pega_title': True, 'pega_duty': bool(job.get('description'))}


class StoreCase(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.store = Store(self.folder / 'data' / 'radar.sqlite3')
        self.run_id = self.store.start_run()

    def save(self, *jobs, source='LinkedIn', label=None, kind='linkedin', ranker=plain_ranker, run_id=None, **extra):
        result = model.make_result(source, label or source, kind, jobs=jobs, **extra)
        return self.store.save_result(run_id or self.run_id, result, ranker)

    @staticmethod
    def linkedin(source_id, title='Pega Developer', company='Acme', location='Bengaluru, Karnataka, India', **extra):
        return model.make_job('LinkedIn', source_id, title, company, f'https://www.linkedin.com/jobs/view/{source_id}',
                              location, **extra)

    @staticmethod
    def employer(source_id, title='Pega Developer', company='Acme', location='Bengaluru', **extra):
        return model.make_job(model.EMPLOYER_SOURCE, source_id, title, company,
                              f'https://careers.acme.test/job/{source_id}', location, **extra)


class StoreSaveTest(StoreCase):
    def test_new_then_updated(self):
        first = self.save(self.linkedin('1'), self.linkedin('2', title='Pega Architect'))
        self.assertEqual((len(first['new']), first['updated']), (2, []))
        second_run = self.store.start_run()
        second = self.save(self.linkedin('1'), self.linkedin('3', title='Pega Lead'), run_id=second_run)
        self.assertEqual(second['updated'], [first['new'][0]])
        self.assertEqual(len(second['new']), 1)
        job = self.store.job(first['new'][0])
        self.assertEqual((job['first_run_id'], job['last_run_id']), (self.run_id, second_run))
        self.assertEqual(self.store.jobs()[1], 3)

    def test_identity_1_same_sighting_is_the_same_job(self):
        first = self.save(self.linkedin('77', title='Pega Developer'))
        again = self.save(self.linkedin('77', title='Pega Developer II', company='Acme Global', location='Pune'))
        self.assertEqual(again, {'new': [], 'updated': first['new'], 'kept': 1})
        self.assertEqual(self.store.jobs()[1], 1)

    def test_identity_2_same_company_and_requisition(self):
        first = self.save(self.linkedin('1', title='Pega Developer', company='Acme India Pvt Ltd', requisition_id='R-100'))
        second = self.save(self.employer('R-100', title='Senior System Architect - Pega', company='ACME',
                                         location='Hyderabad', requisition_id='R-100'),
                           source=model.EMPLOYER_SOURCE, label='Acme', kind='ats')
        self.assertEqual(second, {'new': [], 'updated': first['new'], 'kept': 1})
        other = self.save(self.employer('R-200', company='Globex', requisition_id='R-100'),
                          source=model.EMPLOYER_SOURCE, label='Globex', kind='ats')
        self.assertEqual(len(other['new']), 1)                 # the same number at another employer is another job

    def test_identity_3_cross_source_title_and_city(self):
        first = self.save(self.linkedin('1', title='Sr. Pega Developer - Bangalore', company='Acme Pvt Ltd'))
        merged = self.save(self.employer('e1', title='Senior Pega Developer', company='Acme', location='Bengaluru'),
                           source=model.EMPLOYER_SOURCE, label='Acme', kind='ats')
        self.assertEqual(merged, {'new': [], 'updated': first['new'], 'kept': 1})
        self.assertEqual(self.store.job(first['new'][0])['sources'], ['LinkedIn', model.EMPLOYER_SOURCE])

    def test_identity_3_needs_the_same_city_title_and_company(self):
        self.save(self.linkedin('1'))
        for job in (self.employer('e1', location='Hyderabad'), self.employer('e2', title='Pega Architect'),
                    self.employer('e3', company='Globex')):
            saved = self.save(job, source=model.EMPLOYER_SOURCE, label='x', kind='ats')
            self.assertEqual(len(saved['new']), 1, job['source_id'])
        self.assertEqual(self.store.jobs()[1], 4)

    def test_identity_3_keeps_two_listings_from_one_site_apart(self):
        saved = self.save(self.linkedin('1'), self.linkedin('2'))
        self.assertEqual(len(saved['new']), 2)

    def test_identity_3_keeps_different_requisitions_apart(self):
        self.save(self.linkedin('1', requisition_id='R-1'))
        saved = self.save(self.employer('e1', requisition_id='R-2'), source=model.EMPLOYER_SOURCE, label='Acme', kind='ats')
        self.assertEqual(len(saved['new']), 1)

    def test_jobs_without_an_employer_are_never_merged(self):
        self.save(self.linkedin('1', company=''))
        saved = self.save(model.make_job('Hirist', 'h1', 'Pega Developer', '', 'https://hirist.test/1', 'Bengaluru'),
                          source='Hirist', kind='board')
        self.assertEqual(len(saved['new']), 1)

    def test_title_key(self):
        self.assertEqual(title_key('Sr. Pega Developer - Bangalore (Hybrid)'), title_key('Senior Pega Developer'))
        self.assertNotEqual(title_key('Pega Developer'), title_key('Pega Architect'))

    def test_merge_keeps_the_best_of_each_field(self):
        first = self.save(self.linkedin('1', posted_at='2026-11-10', description='Short text.', salary_max_lpa=32,
                                        experience_min=4))
        job_id = first['new'][0]
        long_text = 'Design and build Pega case types. ' * 5
        self.save(self.employer('e1', posted_at='2026-11-03', description=long_text, apply_url='https://careers.acme.test/apply/e1',
                                requisition_id='R-7'), source=model.EMPLOYER_SOURCE, label='Acme', kind='ats')
        self.save(model.make_job('Hirist', 'h1', 'Pega Developer', 'Acme', 'https://hirist.test/h1', 'Bengaluru',
                                 posted_at='2026-11-12', description='Tiny.', experience_min=9, salary_max_lpa=10),
                  source='Hirist', kind='board')
        job = self.store.job(job_id)
        self.assertEqual(job['description'], long_text.strip())           # longest description
        self.assertEqual(job['posted_at'], '2026-11-03')                  # earliest date
        self.assertEqual(job['url'], 'https://careers.acme.test/job/e1')  # employer site beats both boards
        self.assertEqual(job['apply_url'], 'https://careers.acme.test/apply/e1')
        self.assertEqual((job['salary_max_lpa'], job['experience_min'], job['requisition_id']), (32.0, 4.0, 'R-7'))
        self.assertEqual(job['sources'], ['LinkedIn', model.EMPLOYER_SOURCE, 'Hirist'])
        self.assertEqual(len(job['sightings']), 3)
        self.assertTrue(job['pega_duty'])                                 # re-ranked with the merged text

    def test_merge_never_clears_a_field_with_an_empty_value(self):
        first = self.save(self.linkedin('1', description='Full description of the Pega work.', posted_at='2026-11-01',
                                        apply_url='https://acme.test/apply', salary_min_lpa=28))
        self.save(self.linkedin('1'))                                     # the same card later, with nothing read
        job = self.store.job(first['new'][0])
        self.assertEqual(job['description'], 'Full description of the Pega work.')
        self.assertEqual((job['posted_at'], job['apply_url'], job['salary_min_lpa']),
                         ('2026-11-01', 'https://acme.test/apply', 28.0))

    def test_cities_accumulate_across_sightings(self):
        first = self.save(self.linkedin('1', location='Hyderabad', requisition_id='R-1'))
        self.save(self.employer('e1', location='Hyderabad, Bangalore', requisition_id='R-1'),
                  source=model.EMPLOYER_SOURCE, label='Acme', kind='ats')
        job = self.store.job(first['new'][0])
        self.assertEqual((job['city'], job['cities'], job['is_bengaluru']), ('Hyderabad', ['Hyderabad', 'Bengaluru'], True))

    def test_the_sighting_stores_the_result_label(self):
        saved = self.save(self.employer('e1'), source=model.EMPLOYER_SOURCE, label='Acme Careers', kind='ats')
        sighting = self.store.job(saved['new'][0])['sightings'][0]
        self.assertEqual((sighting['source'], sighting['source_id'], sighting['label'], sighting['url']),
                         (model.EMPLOYER_SOURCE, 'e1', 'Acme Careers', 'https://careers.acme.test/job/e1'))

    def test_ranker_verdict_is_stored(self):
        def ranker(job):
            self.assertEqual(job['cities'], ['Bengaluru'])
            return {'employer_type': 'gcc', 'score': 81.6, 'fit': {'reasons': ['Bengaluru'], 'labels': {'bengaluru': True}},
                    'pega_title': True, 'pega_duty': False}
        saved = self.save(self.linkedin('1'), ranker=ranker)
        job = self.store.job(saved['new'][0])
        self.assertEqual((job['employer_type'], job['score'], job['pega_title'], job['pega_duty']), ('gcc', 82, True, False))
        self.assertEqual(job['fit'], {'reasons': ['Bengaluru'], 'labels': {'bengaluru': True}})

    def test_a_posting_without_a_title_or_id_is_still_stored(self):
        jobs = [{'source': 'LinkedIn', 'source_id': '9', 'title': '', 'company': 'Acme', 'location': 'Pune'},
                {'source': 'LinkedIn', 'source_id': '', 'title': 'Pega Developer', 'company': 'Globex',
                 'url': 'https://x.test/a', 'location': 'Chennai'},
                'not a job']
        result = {**model.make_result('LinkedIn', 'LinkedIn', 'linkedin'), 'jobs': jobs, 'found': 3, 'kept': 3}
        saved = self.store.save_result(self.run_id, result, plain_ranker)
        self.assertEqual((len(saved['new']), saved['kept']), (2, 2))
        self.assertEqual(self.store.job(saved['new'][0])['title'], 'Pega role (title not given)')
        again = self.store.save_result(self.run_id, result, plain_ranker)
        self.assertEqual((again['new'], again['updated'], again['kept']), ([], saved['new'], 2))   # the made-up id is stable
        self.store.finish_run(self.run_id, 'complete', {})
        health = self.store.latest_run()['health'][0]
        self.assertEqual((health['found'], health['kept']), (3, 2))       # what was stored, not what was claimed

    def test_identity_3_does_not_merge_a_later_opening_into_an_old_job(self):
        long_ago = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat(timespec='seconds')
        with mock.patch('radar.store.now_iso', return_value=long_ago):
            stale = self.save(self.linkedin('old', company='Stale Corp'))['new'][0]
        dated = self.save(self.linkedin('d1', company='Dated Corp', posted_at='2026-06-01'))['new'][0]
        live = self.save(self.linkedin('l1', company='Live Corp', posted_at='2026-10-20'))['new'][0]

        def reopen(company, **extra):
            return self.save(self.employer('e-' + company, company=company, **extra),
                             source=model.EMPLOYER_SOURCE, label=company, kind='ats')
        for company, extra in (('Stale Corp', {}), ('Dated Corp', {'posted_at': '2026-08-15'})):
            saved = reopen(company, **extra)
            self.assertEqual((len(saved['new']), saved['updated']), (1, []), company)   # a new opening, shown as new
        self.assertEqual(reopen('Live Corp', posted_at='2026-11-10'), {'new': [], 'updated': [live], 'kept': 1})
        self.assertEqual((self.store.job(stale)['sources'], self.store.job(dated)['sources']), (['LinkedIn'], ['LinkedIn']))

    def test_a_dismissed_job_does_not_resurface_when_another_site_lists_it(self):
        hidden = self.save(self.linkedin('h1', company='Hidden Corp', posted_at='2026-11-01'))['new'][0]
        rejected = self.save(self.linkedin('r1', company='Rejected Corp'))['new'][0]
        self.store.set_state(hidden, hidden=True, notes='not for me')
        self.store.set_state(rejected, status='rejected')
        for company, job_id, extra in (('Hidden Corp', hidden, {'posted_at': '2026-11-05'}), ('Rejected Corp', rejected, {})):
            saved = self.save(self.employer('e-' + company, company=company, **extra),
                              source=model.EMPLOYER_SOURCE, label=company, kind='ats')
            self.assertEqual(saved, {'new': [], 'updated': [job_id], 'kept': 1}, company)   # the same posting, elsewhere
            self.assertEqual(self.store.job(job_id)['sources'], ['LinkedIn', model.EMPLOYER_SOURCE])
        state = self.store.job(hidden)
        self.assertEqual((state['hidden'], state['notes'], state['is_new']), (True, 'not for me', False))
        self.assertEqual(self.store.job(rejected)['status'], 'rejected')
        self.assertEqual(self.store.jobs(view='new')[1], 0)
        # A genuinely later opening at the same employer is a new job, and the old one stays dismissed.
        later = self.save(model.make_job('Hirist', 'h9', 'Pega Developer', 'Hidden Corp', 'https://hirist.test/h9',
                                         'Bengaluru', posted_at='2026-12-20'), source='Hirist', kind='board')
        self.assertEqual((len(later['new']), later['updated']), (1, []))
        self.assertTrue(self.store.job(hidden)['hidden'])
        self.assertEqual(self.store.jobs(view='new')[1], 1)

    def test_a_later_sighting_joins_the_newest_matching_job(self):
        long_ago = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat(timespec='seconds')
        with mock.patch('radar.store.now_iso', return_value=long_ago):
            self.save(self.linkedin('old'))
        reopened = self.save(self.employer('e1'), source=model.EMPLOYER_SOURCE, label='Acme', kind='ats')['new'][0]
        board = self.save(model.make_job('Hirist', 'h1', 'Pega Developer', 'Acme', 'https://hirist.test/h1', 'Bengaluru'),
                          source='Hirist', kind='board')
        self.assertEqual(board['updated'], [reopened])

    def test_the_registry_name_keys_the_company(self):
        registry = rank.Registry([{'name': 'Commonwealth Bank', 'aliases': ['CBA', 'CommBank'], 'type': 'gcc'}])
        ranker = rank.make_ranker(model.load_config(), registry, today=TODAY)
        first = self.save(self.linkedin('1', company='Commonwealth Bank of Australia'), ranker=ranker)
        merged = self.save(self.employer('e1', company='CommBank'), source=model.EMPLOYER_SOURCE, label='CBA', kind='ats',
                           ranker=ranker)
        self.assertEqual(merged, {'new': [], 'updated': first['new'], 'kept': 1})
        self.assertEqual(self.store.job(first['new'][0])['company_key'], 'commonwealthbank')
        apart = self.save(self.linkedin('2', company='Commonwealth Bank of Australia'),
                          model.make_job('Hirist', 'h1', 'Pega Developer', 'CommBank', 'u', 'Bengaluru'))
        self.assertEqual(len(apart['new']), 2)                            # a ranker without a registry still works

    def test_rescore_refreshes_company_keys(self):
        job_id = self.save(self.linkedin('1', company='Commonwealth Bank of Australia'))['new'][0]
        self.assertEqual(self.store.job(job_id)['company_key'], 'commonwealthbankofaustralia')
        registry = rank.Registry([{'name': 'Commonwealth Bank', 'type': 'gcc'}])
        self.store.rescore(rank.make_ranker(model.load_config(), registry, today=TODAY))
        job = self.store.job(job_id)
        self.assertEqual((job['company_key'], job['employer_type']), ('commonwealthbank', 'gcc'))

    def test_concurrent_saves_from_threads(self):
        def work(index):
            self.save(*[self.linkedin(f'{index}-{n}', title=f'Pega Developer {index}-{n}') for n in range(10)])
        threads = [threading.Thread(target=work, args=(index,)) for index in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(self.store.jobs()[1], 60)


class StoreStateTest(StoreCase):
    def test_user_state_survives_rescans(self):
        job_id = self.save(self.linkedin('1'))['new'][0]
        state = self.store.set_state(job_id, saved=True, status='applied', notes='Spoke to the recruiter.')
        self.assertEqual((state['saved'], state['status'], state['notes']), (True, 'applied', 'Spoke to the recruiter.'))
        self.save(self.linkedin('1', description='Now with a description.'), run_id=self.store.start_run())
        self.store.rescore(plain_ranker)
        job = self.store.job(job_id)
        self.assertEqual((job['saved'], job['status'], job['notes']), (True, 'applied', 'Spoke to the recruiter.'))

    def test_set_state_changes_only_what_is_given(self):
        job_id = self.save(self.linkedin('1'))['new'][0]
        self.store.set_state(job_id, saved=True, notes='first')
        state = self.store.set_state(job_id, status='interested')
        self.assertEqual((state['saved'], state['status'], state['notes']), (True, 'interested', 'first'))
        state = self.store.set_state(job_id, saved=False, notes='')
        self.assertEqual((state['saved'], state['status'], state['notes']), (False, 'interested', ''))

    def test_set_state_rejects_unknown_jobs_and_statuses(self):
        self.assertIsNone(self.store.set_state('no-such-job', saved=True))
        job_id = self.save(self.linkedin('1'))['new'][0]
        for status in ('dismissed', 'hidden'):                      # hiding is a flag now, not a status
            with self.assertRaises(ValueError):
                self.store.set_state(job_id, status=status)

    def test_hiding_keeps_the_pipeline_status(self):
        job_id = self.save(self.linkedin('1'))['new'][0]
        self.store.set_state(job_id, status='interviewing', notes='round 2 on Friday')
        state = self.store.set_state(job_id, hidden=True)
        self.assertEqual((state['hidden'], state['status'], state['notes']), (True, 'interviewing', 'round 2 on Friday'))
        self.assertEqual(self.store.jobs(view='hidden')[1], 1)
        self.assertEqual(self.store.jobs(view='applied')[1], 0)
        state = self.store.set_state(job_id, hidden=False)
        self.assertEqual((state['hidden'], state['status']), (False, 'interviewing'))
        self.assertEqual(self.store.jobs(view='applied')[1], 1)

    def test_seen_is_stamped_by_looking_saving_or_acting(self):
        ids = self.save(*[self.linkedin(str(n), title=f'Pega Developer {n}') for n in range(5)])['new']
        self.assertEqual(self.store.set_state(ids[0], notes='just a note')['seen'], False)
        looked = self.store.set_state(ids[0], seen=True)
        self.assertTrue(looked['seen'])
        with mock.patch('radar.store.now_iso', return_value='2099-01-01T00:00:00+00:00'):
            self.assertEqual(self.store.set_state(ids[0], seen=True)['seen_at'], looked['seen_at'])   # first look is kept
        self.assertTrue(self.store.set_state(ids[1], saved=True)['seen'])
        self.assertTrue(self.store.set_state(ids[2], status='interested')['seen'])
        self.assertFalse(self.store.set_state(ids[3], status='new', saved=False)['seen'])
        self.assertFalse(self.store.set_state(ids[4], hidden=True)['seen'])
        cleared = self.store.set_state(ids[1], seen=False)
        self.assertEqual((cleared['seen'], cleared['seen_at'], cleared['saved']), (False, None, True))
        self.assertFalse(self.store.set_state(ids[2], status='applied', seen=False)['seen'])        # explicit wins
        job = self.store.job(ids[0])
        self.assertEqual((job['seen'], job['seen_at'], job['hidden'], job['is_new']), (True, looked['seen_at'], False, False))

    def test_notes_sqlite_cannot_encode_do_not_raise(self):
        job_id = self.save(self.linkedin('1'))['new'][0]
        state = self.store.set_state(job_id, notes='call back \ud83d tomorrow ₹')
        self.assertEqual(state['notes'], 'call back ? tomorrow ₹')
        self.assertEqual(self.store.job(job_id)['notes'], 'call back ? tomorrow ₹')
        self.assertEqual(self.store.jobs(q='pega \udc00')[1], 0)             # the same holds for a search

    def test_a_database_from_before_hidden_and_seen_is_migrated(self):
        path = self.folder / 'old' / 'radar.sqlite3'
        Store(path)
        db = sqlite3.connect(path)
        db.executescript('''
            DROP TABLE user_state;
            CREATE TABLE user_state(job_id TEXT PRIMARY KEY, saved INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'new', notes TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL);
            INSERT INTO user_state VALUES ('gone', 1, 'hidden', 'not for me', '2026-11-01T00:00:00+00:00');
            INSERT INTO user_state VALUES ('kept', 0, 'applied', 'sent CV', '2026-11-02T00:00:00+00:00');''')
        db.close()
        old = Store(path)
        Store(path)                                                          # opening again changes nothing
        db = sqlite3.connect(path)
        rows = {row[0]: row[1:] for row in db.execute('SELECT job_id, saved, status, notes, hidden, seen_at FROM user_state')}
        db.close()
        self.assertEqual(rows, {'gone': (1, 'new', 'not for me', 1, '2026-11-01T00:00:00+00:00'),
                                'kept': (0, 'applied', 'sent CV', 0, None)})
        run_id = old.start_run()
        job_id = old.save_result(run_id, model.make_result('LinkedIn', 'LinkedIn', 'linkedin', jobs=[self.linkedin('1')]),
                                 plain_ranker)['new'][0]
        self.assertTrue(old.set_state(job_id, hidden=True, seen=True)['hidden'])

    def test_a_job_defaults_to_status_new(self):
        job = self.store.job(self.save(self.linkedin('1'))['new'][0])
        self.assertEqual((job['saved'], job['status'], job['notes'], job['hidden'], job['seen'], job['is_new']),
                         (False, 'new', '', False, False, True))
        self.assertIsNone(self.store.job('no-such-job'))


class StoreViewTest(StoreCase):
    def setUp(self):
        super().setUp()

        def ranker(job):
            kind = {'Acme': 'product', 'Globex': 'gcc', 'Initech': 'services'}.get(job['company'], 'unknown')
            return {'employer_type': kind, 'score': int(job['salary_max_lpa'] or 0), 'fit': {}, 'pega_title': True,
                    'pega_duty': False}
        self.ranker = ranker
        rows = [('a', 'Pega Developer', 'Acme', 'Bengaluru', 90, '2026-11-01'),
                ('b', 'Pega Architect', 'Globex', 'Hyderabad', 70, '2026-11-10'),
                ('c', 'Pega Tester', 'Initech', 'Pune, Bengaluru', 30, None),
                ('d', 'PRPC Engineer', 'Umbrella', 'Chennai', 55, '2026-11-05')]
        self.ids = {}
        for source_id, title, company, location, score, posted in rows:
            saved = self.save(self.linkedin(source_id, title=title, company=company, location=location,
                                            salary_max_lpa=score, posted_at=posted, description='Text.'), ranker=ranker)
            self.ids[source_id] = saved['new'][0]
        self.store.finish_run(self.run_id, 'complete', {})

    def titles(self, **filters):
        rows, total = self.store.jobs(**filters)
        self.assertGreaterEqual(total, len(rows))
        return [row['title'] for row in rows]

    def test_rows_carry_state_sources_and_no_description(self):
        rows, total = self.store.jobs()
        self.assertEqual(total, 4)
        row = rows[0]
        self.assertNotIn('description', row)
        self.assertTrue(row['has_description'])
        self.assertEqual((row['saved'], row['status'], row['notes'], row['sources'], row['is_new'], row['hidden'],
                          row['seen']), (False, 'new', '', ['LinkedIn'], True, False, False))
        self.assertEqual((row['cities'], row['is_bengaluru'], row['fit']), (['Bengaluru'], True, {}))

    def test_sorts(self):
        self.assertEqual(self.titles(sort='score'), ['Pega Developer', 'Pega Architect', 'PRPC Engineer', 'Pega Tester'])
        self.assertEqual(self.titles(sort='posted'), ['Pega Architect', 'PRPC Engineer', 'Pega Developer', 'Pega Tester'])
        later = self.store.start_run()
        with mock.patch('radar.store.now_iso', return_value='2099-01-01T00:00:00+00:00'):
            self.save(self.linkedin('e', title='Pega Lead', salary_max_lpa=1), ranker=self.ranker, run_id=later)
        by_first_seen = self.titles(sort='first_seen')
        self.assertEqual((by_first_seen[0], by_first_seen[-1]), ('Pega Lead', 'Pega Tester'))   # ties broken by score
        self.assertEqual(self.titles(sort='no-such-sort')[0], 'Pega Developer')

    def test_city_filter(self):
        self.assertEqual(self.titles(city='bengaluru'), ['Pega Developer', 'Pega Tester'])
        self.assertEqual(self.titles(city='Bangalore'), ['Pega Developer', 'Pega Tester'])
        self.assertEqual(self.titles(city='Pune'), ['Pega Tester'])
        self.assertEqual(self.titles(city='hyderabad'), ['Pega Architect'])
        self.assertEqual(len(self.titles(city='all')), 4)
        self.assertEqual(self.titles(city='Kolkata'), [])

    def test_type_search_and_score_filters(self):
        self.assertEqual(self.titles(types=['product', 'gcc']), ['Pega Developer', 'Pega Architect'])
        self.assertEqual(self.titles(types=('services',)), ['Pega Tester'])
        self.assertEqual(len(self.titles(types=[])), 4)
        self.assertEqual(self.titles(q='pega arch'), ['Pega Architect'])
        self.assertEqual(self.titles(q='GLOBEX'), ['Pega Architect'])
        self.assertEqual(self.titles(q='chennai'), ['PRPC Engineer'])
        self.store.save_result(self.run_id, model.make_result('LinkedIn', 'LinkedIn', 'linkedin', jobs=[
            self.linkedin('b', location='Hyderabad', description='Build decisioning strategies in Customer Decision Hub.')]), self.ranker)
        self.assertEqual(self.titles(q='decision hub'), ['Pega Architect'])    # the description is searched too
        self.assertEqual(self.titles(q='decision_hub'), [])
        self.assertEqual(self.titles(q='100%'), [])                       # wildcards in the query are literal
        self.assertEqual(self.titles(min_score=60), ['Pega Developer', 'Pega Architect'])
        self.assertEqual(self.titles(city='bengaluru', types=['product', 'gcc'], min_score=50), ['Pega Developer'])

    def test_pagination(self):
        first, total = self.store.jobs(limit=3)
        rest, _ = self.store.jobs(limit=3, offset=3)
        self.assertEqual((total, len(first), len(rest)), (4, 3, 1))
        self.assertEqual({row['id'] for row in first + rest}, set(self.ids.values()))
        self.assertEqual(len(self.store.jobs(limit=0)[0]), 1)             # limit is clamped, never an error
        self.assertEqual(self.store.jobs(limit=10, offset=50), ([], 4))

    def test_new_is_an_inbox_that_later_runs_do_not_empty(self):
        self.assertEqual(len(self.titles(view='new')), 4)
        second = self.store.start_run()
        self.save(self.linkedin('a'), self.linkedin('z', title='Pega Lead', company='Hooli'), ranker=self.ranker, run_id=second)
        self.store.finish_run(second, 'partial', {})
        self.assertEqual(len(self.titles(view='new')), 5)                 # a second scan the same morning
        self.store.finish_run(self.store.start_run(), 'failed', {'error': 'boom'})
        self.assertEqual(len(self.titles(view='new')), 5)                 # nor does a failed one
        self.assertEqual(self.store.stats()['new'], 5)

    def test_new_leaves_the_inbox_when_seen_acted_on_or_hidden(self):
        self.store.set_state(self.ids['a'], seen=True)
        self.store.set_state(self.ids['b'], status='applied')
        self.store.set_state(self.ids['c'], hidden=True)
        self.assertEqual(self.titles(view='new'), ['PRPC Engineer'])
        rows, _ = self.store.jobs(view='all')
        self.assertEqual({row['title']: row['is_new'] for row in rows},
                         {'Pega Developer': False, 'Pega Architect': False, 'PRPC Engineer': True})
        stats = self.store.stats()
        self.assertEqual((stats['new'], stats['new_bengaluru'], stats['new_product_gcc']), (1, 0, 0))
        self.store.set_state(self.ids['a'], seen=False)
        self.assertEqual(self.titles(view='new'), ['Pega Developer', 'PRPC Engineer'])

    def test_new_expires_after_fourteen_days(self):
        early = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat(timespec='seconds')
        recent = (datetime.now(timezone.utc) - timedelta(days=13)).isoformat(timespec='seconds')
        with mock.patch('radar.store.now_iso', return_value=early):
            self.save(self.linkedin('old', title='Pega Old'), ranker=self.ranker)
        with mock.patch('radar.store.now_iso', return_value=recent):
            self.save(self.linkedin('recent', title='Pega Recent'), ranker=self.ranker)
        new = self.titles(view='new')
        self.assertIn('Pega Recent', new)
        self.assertNotIn('Pega Old', new)
        self.assertIn('Pega Old', self.titles(view='all'))
        self.assertEqual(self.store.stats()['new'], 5)

    def test_mark_all_seen_empties_the_inbox(self):
        self.store.set_state(self.ids['a'], saved=False, notes='keep me')    # a state row that is still new
        self.store.set_state(self.ids['d'], hidden=True)
        self.assertEqual(self.store.mark_all_seen(), 3)
        self.assertEqual(self.titles(view='new'), [])
        self.assertEqual(self.store.stats()['new'], 0)
        self.assertEqual(self.store.mark_all_seen(), 0)
        kept = self.store.job(self.ids['a'])
        self.assertEqual((kept['notes'], kept['seen'], kept['status']), ('keep me', True, 'new'))
        self.assertFalse(self.store.job(self.ids['d'])['seen'])           # hidden jobs were not in the inbox
        self.assertEqual(len(self.titles(view='all')), 3)                 # seen is not hidden
        self.save(self.linkedin('fresh', title='Pega Fresh'), ranker=self.ranker)
        self.assertEqual(self.titles(view='new'), ['Pega Fresh'])

    def test_saved_applied_and_hidden_views(self):
        self.store.set_state(self.ids['a'], saved=True)
        self.store.set_state(self.ids['b'], status='interviewing')
        self.store.set_state(self.ids['c'], hidden=True, saved=True, status='applied')
        self.store.set_state(self.ids['d'], status='rejected')
        self.assertEqual(self.titles(view='saved'), ['Pega Developer'])   # the hidden one is saved but stays out
        self.assertEqual(self.titles(view='applied'), ['Pega Architect', 'PRPC Engineer'])   # rejected is pipeline history
        self.assertEqual(self.titles(view='all'), ['Pega Developer', 'Pega Architect'])
        self.assertEqual(self.titles(view='no-such-view'), ['Pega Developer', 'Pega Architect'])
        self.assertEqual(self.titles(view='new'), [])
        self.assertEqual(self.titles(view='hidden'), ['Pega Tester'])
        self.store.set_state(self.ids['c'], hidden=False)
        self.assertIn('Pega Tester', self.titles(view='all'))
        self.assertEqual(self.titles(view='hidden'), [])

    def test_stats(self):
        self.store.set_state(self.ids['a'], saved=True, status='applied')
        self.store.set_state(self.ids['b'], status='rejected')
        self.store.set_state(self.ids['d'], hidden=True)
        stats = self.store.stats()
        self.assertEqual((stats['total'], stats['new'], stats['new_bengaluru'], stats['new_product_gcc']), (2, 1, 1, 0))
        self.assertEqual((stats['bengaluru'], stats['product_gcc'], stats['bengaluru_product_gcc']), (2, 1, 1))
        self.assertEqual((stats['saved'], stats['applied'], stats['hidden']), (1, 2, 1))
        self.assertEqual(stats['by_type'], {'product': 1, 'services': 1})
        for key, view in (('total', 'all'), ('new', 'new'), ('saved', 'saved'), ('applied', 'applied'), ('hidden', 'hidden')):
            self.assertEqual(stats[key], self.store.jobs(view=view)[1], key)   # a tile and its view always agree
        self.assertEqual(stats['last_scan_status'], 'complete')
        self.assertIsNotNone(stats['last_scan_at'])

    def test_stats_on_an_empty_store(self):
        stats = Store(self.folder / 'empty.sqlite3').stats()
        self.assertEqual((stats['total'], stats['new'], stats['new_bengaluru'], stats['new_product_gcc'],
                          stats['saved'], stats['hidden'], stats['last_scan_at']), (0, 0, 0, 0, 0, 0, None))

    def test_export_rows_include_hidden_jobs_and_state(self):
        self.store.set_state(self.ids['c'], hidden=True, notes='not for me')
        seen_at = self.store.set_state(self.ids['a'], seen=True)['seen_at']
        rows = self.store.export_rows()
        self.assertEqual([row['title'] for row in rows], ['Pega Developer', 'Pega Architect', 'PRPC Engineer', 'Pega Tester'])
        self.assertEqual((rows[-1]['status'], rows[-1]['hidden'], rows[-1]['notes'], rows[-1]['sources'], rows[-1]['saved'],
                          rows[-1]['seen_at']), ('new', True, 'not for me', 'LinkedIn', False, None))
        self.assertEqual((rows[0]['hidden'], rows[0]['seen_at']), (False, seen_at))
        self.assertNotIn('description', rows[0])

    def test_run_counts(self):
        self.assertEqual(self.store.run_counts(self.run_id), {'new': 4, 'new_bengaluru': 2, 'new_product_gcc': 2})
        self.assertEqual(self.store.run_counts('no-such-run'), {'new': 0, 'new_bengaluru': 0, 'new_product_gcc': 0})


class StoreRunTest(StoreCase):
    def test_latest_run_reports_health(self):
        self.assertIsNone(self.store.latest_run())                        # nothing has finished yet
        self.save(self.linkedin('1'), found=25, requests=4)
        self.store.save_result(self.run_id, model.make_result('Shine', 'Shine', 'board', status='blocked',
                                                              requests=1, error='HTTP 403'), plain_ranker)
        self.store.finish_run(self.run_id, 'partial', {'new': 1, 'attention': ['Shine']})
        run = self.store.latest_run()
        self.assertEqual((run['id'], run['status'], run['summary']), (self.run_id, 'partial', {'new': 1, 'attention': ['Shine']}))
        self.assertLessEqual(run['started_at'], run['finished_at'])
        basics = ('source', 'label', 'kind', 'status', 'found', 'kept', 'requests', 'error')
        self.assertEqual([{key: row[key] for key in basics} for row in run['health']], [
            {'source': 'LinkedIn', 'label': 'LinkedIn', 'kind': 'linkedin', 'status': 'ok', 'found': 25, 'kept': 1,
             'requests': 4, 'error': None},
            {'source': 'Shine', 'label': 'Shine', 'kind': 'board', 'status': 'blocked', 'found': 0, 'kept': 0,
             'requests': 1, 'error': 'HTTP 403'}])
        self.assertEqual(set(run['health'][0]) - set(basics),
                         {'elapsed_s', 'reason', 'pages_complete', 'details_complete', 'employer', 'task', 'at'})
        self.assertEqual((run['health'][0]['reason'], run['health'][0]['pages_complete']), ('', None))
        self.assertEqual(run['last_attempt'], {'id': self.run_id, 'status': 'partial', 'finished_at': run['finished_at'],
                                               'error': None})

    def test_a_failed_run_does_not_blank_the_last_good_coverage(self):
        self.save(self.linkedin('1'))
        self.store.finish_run(self.run_id, 'complete', {'new': 1})
        failed = self.store.start_run()
        with mock.patch('radar.store.now_iso', return_value='2099-01-01T09:00:00+00:00'):
            self.store.finish_run(failed, 'failed', {'error': 'RuntimeError: no sources'})
        run = self.store.latest_run()
        self.assertEqual((run['id'], run['status'], len(run['health'])), (self.run_id, 'complete', 1))
        self.assertEqual(run['last_attempt'], {'id': failed, 'status': 'failed', 'finished_at': '2099-01-01T09:00:00+00:00',
                                               'error': 'RuntimeError: no sources'})
        self.assertEqual(self.store.stats()['last_scan_status'], 'complete')

    def test_only_failed_runs_so_far(self):
        self.store.finish_run(self.run_id, 'failed', {'error': 'boom'})
        run = self.store.latest_run()
        self.assertEqual((run['id'], run['status'], run['finished_at'], run['summary'], run['health']),
                         (None, None, None, {}, []))
        self.assertEqual((run['last_attempt']['status'], run['last_attempt']['error']), ('failed', 'boom'))
        self.assertIsNone(self.store.stats()['last_scan_at'])

    def test_known_ids(self):
        self.save(self.linkedin('1', description='Read.'), self.linkedin('2'))
        self.save(model.make_job('Hirist', 'h1', 'Pega Lead', 'Globex', 'u', 'Pune', description='Read.'),
                  source='Hirist', kind='board')
        self.assertEqual(self.store.known_ids('LinkedIn'), {'1'})
        self.assertEqual(self.store.known_ids('LinkedIn', with_description=False), {'1', '2'})
        self.assertEqual(self.store.known_ids('Shine'), set())

    def test_kv_round_trip(self):
        self.assertIsNone(self.store.kv_get('missing'))
        self.assertEqual(self.store.kv_get('missing', []), [])
        self.store.kv_set('checkpoint', {'done': ['pega|Bengaluru'], 'at': 3})
        self.store.kv_set('checkpoint', {'done': ['pega|Bengaluru', 'pega|India'], 'at': 4})
        self.assertEqual(self.store.kv_get('checkpoint'), {'done': ['pega|Bengaluru', 'pega|India'], 'at': 4})
        self.store.kv_set('checkpoint', None)
        self.assertIsNone(self.store.kv_get('checkpoint', 'default'))     # a stored null is a value

    def test_rescore_applies_a_new_ranker_to_every_job(self):
        ids = self.save(self.linkedin('1'), self.linkedin('2', title='Pega Lead'))['new']
        count = self.store.rescore(lambda job: {'employer_type': 'gcc', 'score': 12, 'fit': {'reasons': ['again']},
                                                'pega_title': False, 'pega_duty': True})
        self.assertEqual(count, 2)
        job = self.store.job(ids[1])
        self.assertEqual((job['employer_type'], job['score'], job['fit'], job['pega_title'], job['pega_duty']),
                         ('gcc', 12, {'reasons': ['again']}, False, True))

    def test_reopening_the_database_keeps_everything(self):
        job_id = self.save(self.linkedin('1'))['new'][0]
        self.store.set_state(job_id, saved=True)
        reopened = Store(self.store.path)
        self.assertTrue(reopened.job(job_id)['saved'])


# ───────────────────────────── rank ─────────────────────────────

REGISTRY = rank.Registry([
    {'name': 'Commonwealth Bank', 'aliases': ['CBA', 'CommBank'], 'type': 'gcc', 'bengaluru': True},
    {'name': 'Pegasystems', 'aliases': ['Pega'], 'type': 'product', 'bengaluru': True},
    {'name': 'Initech Consulting', 'type': 'services', 'bengaluru': None},
    {'name': 'Oddball', 'type': 'conglomerate'},
])


class RegistryTest(unittest.TestCase):
    def test_exact_and_alias_matches(self):
        kind, entry = REGISTRY.classify('Commonwealth Bank of Australia')
        self.assertEqual((kind, entry['name']), ('gcc', 'Commonwealth Bank'))
        self.assertEqual(REGISTRY.classify('CBA')[0], 'gcc')
        self.assertEqual(REGISTRY.classify('commbank india pvt ltd')[0], 'gcc')
        self.assertEqual(REGISTRY.classify('Pegasystems Worldwide India Pvt. Ltd.')[0], 'product')
        self.assertEqual(REGISTRY.classify('Initech Consulting Limited'), ('services', REGISTRY.entries[2]))

    def test_short_keys_match_exactly_only(self):
        self.assertEqual(REGISTRY.classify('CBA Tech Hub'), ('unknown', None))     # "cba" is too short to match inside
        self.assertEqual(REGISTRY.classify('Pega'), ('product', REGISTRY.entries[1]))

    def test_look_alike_names_are_not_matched(self):
        registry = rank.Registry([{'name': 'Intel', 'type': 'product'}, {'name': 'Cisco', 'type': 'product'},
                                  {'name': 'Roche', 'type': 'gcc'}, {'name': 'Empower', 'type': 'gcc'},
                                  {'name': 'Shell', 'type': 'gcc'}, {'name': 'Wells Fargo', 'type': 'gcc'},
                                  {'name': 'Commonwealth Bank of Australia', 'type': 'gcc'}])
        for company in ('Intellect Design Arena', 'Intelliswift', 'San Francisco Health', 'Rochester Systems',
                        'Empower HR Services', 'Shell Infotech', 'Wells Staffing', 'Commonwealth Recruiters'):
            self.assertIsNone(registry.find(company), company)
        for company, name in (('Intel Corporation', 'Intel'), ('Intel Technology India Pvt Ltd', 'Intel'),
                              ('Shell India Markets', 'Shell'), ('Cisco Systems', 'Cisco'),
                              ('Wells Fargo International Solutions', 'Wells Fargo'),
                              ('Commonwealth Bank', 'Commonwealth Bank of Australia')):
            self.assertEqual(registry.find(company)['name'], name, company)

    @unittest.skipUnless((PROJECT / 'companies.json').exists(), 'companies.json is not present')
    def test_real_registry_regressions(self):
        registry = rank.load_registry(PROJECT / 'companies.json')
        for company in ('Intelliswift', 'Intellect Design Arena', 'San Francisco Health', 'Shell Infotech'):
            self.assertIsNone(registry.find(company), company)
            self.assertNotIn(registry.classify(company)[0], ('product', 'gcc'), company)
        expected = {'Intel Technology India Pvt Ltd': 'Intel', 'Shell Business Operations': 'Shell',
                    'Wells Fargo India Solutions': 'Wells Fargo', 'JPMorgan Chase & Co.': 'JPMorganChase',
                    'Commonwealth Bank of Australia': 'Commonwealth Bank'}
        for company, name in expected.items():
            kind, entry = registry.classify(company)
            self.assertIsNotNone(entry, company)
            self.assertEqual((entry['name'], kind), (name, entry['type']), company)

    def test_unknown_type_in_the_file_is_unknown(self):
        self.assertEqual(REGISTRY.classify('Oddball')[0], 'unknown')

    def test_pattern_fallback(self):
        empty = rank.Registry()
        cases = {'Tata Consultancy Services': 'services', 'Infosys Limited': 'services', 'UST': 'services',
                 'Wells Fargo International Solutions': 'gcc', 'Northern Trust': 'gcc', 'JPMorgan Chase & Co.': 'gcc',
                 'Mercedes-Benz Research and Development India': 'gcc', 'ING': 'gcc',
                 'Salesforce': 'product', 'Pegasystems': 'product',
                 'ABC Staffing Solutions': 'staffing', 'Careernet': 'staffing',
                 'Blue Kite Labs': 'unknown', '': 'unknown', None: 'unknown'}
        for company, expected in cases.items():
            self.assertEqual(empty.classify(company), (expected, None), company)

    def test_patterns_need_whole_words_for_short_names(self):
        empty = rank.Registry()
        self.assertEqual(empty.classify('Trust Bank')[0], 'unknown')               # not UST
        self.assertEqual(empty.classify('Sterling Engineering Works')[0], 'unknown')   # not ING
        self.assertEqual(empty.classify('San Francisco Health')[0], 'unknown')     # not Cisco
        self.assertEqual(empty.classify('Cisco Systems')[0], 'product')

    def test_load_registry_tolerates_missing_empty_and_broken_files(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'companies.json'
            self.assertEqual(len(rank.load_registry(path)), 0)                     # missing
            for text in ('', '{not json', '[]', '{"companies": null}', '{"companies": []}'):
                path.write_text(text, encoding='utf-8')
                registry = rank.load_registry(path)
                self.assertEqual(len(registry), 0, text)
                self.assertEqual(registry.classify('Infosys')[0], 'services')      # patterns still work
            path.write_text('﻿' + json.dumps({'companies': [{'name': 'Globex', 'type': 'gcc'}, 'junk', {}]}),
                            encoding='utf-8')
            registry = rank.load_registry(path)
            self.assertEqual((len(registry), registry.classify('Globex Corp')[0]), (1, 'gcc'))


class ExperienceTest(unittest.TestCase):
    def test_parse_experience(self):
        cases = {
            '4-7 years': (4, 7), '4 - 7 Yrs': (4, 7), '4 to 7 years of experience': (4, 7), '3–5 yrs': (3, 5),
            'between 3 and 5 years': (3, 5), '5+ yrs': (5, None), '5+ years of experience in Pega': (5, None),
            'minimum 6 years': (6, None), 'Minimum of 6 years of experience': (6, None),
            'at least 3 years experience': (3, None), 'up to 3 years of experience': (None, 3),
            'less than 2 years experience': (None, 2), 'Five years of hands-on Pega experience': (5, None),
            '18 months of experience': (1.5, None), '0-2 years': (0, 2), '8+ Years': (8, None),
            '': (None, None), None: (None, None), 'Pega Developer': (None, None),
        }
        for text, expected in cases.items():
            self.assertEqual(rank.parse_experience(text), expected, text)

    def test_contract_lengths_are_not_experience(self):
        for text in ('6 Months Contract', 'Pega Developer - 6 Months Contract', 'Pega Developer (12 months extendable)',
                     'contract of 12 months', 'Contract duration: 2 years', 'Notice period 3 months', '2 years contract',
                     'Pega Architect 6 months'):
            self.assertEqual(rank.parse_experience(text), (None, None), text)
        self.assertEqual(rank.parse_experience('Experience: 3 years; contract duration 6 months'), (3, None))
        self.assertEqual(rank.parse_experience('6 months contract. 5+ years of Pega experience needed.'), (5, None))
        self.assertEqual(rank.parse_experience('18 months of experience'), (1.5, None))

    def test_the_highest_minimum_wins(self):
        text = ('Responsibilities:\nBuild Pega applications for retail banking customers every day.\n'
                'Requirements:\n5+ years of overall IT experience.\n3+ years of experience in Pega PRPC.')
        self.assertEqual(rank.parse_experience(text), (5, None))

    def test_years_that_are_not_requirements_are_ignored(self):
        text = ('Our company has 25 years of experience serving banks around the world with great care.\n'
                'Founded 12 years ago, we now employ 4000 people. You get 20 days of leave each year.')
        self.assertEqual(rank.parse_experience(text), (None, None))
        text += '\nYou bring 4-6 years of experience building Pega applications.'
        self.assertEqual(rank.parse_experience(text), (4, 6))


class PegaDutyTest(unittest.TestCase):
    def test_duty_sentences_count(self):
        for text in ('Design and develop Pega case management applications.',
                     'Requirements:\n4+ years of hands-on experience in Pega PRPC.',
                     'CSSA certification in Pega is mandatory.',
                     'We are looking for a Pega Developer with 4+ years of hands-on experience in Pega PRPC',
                     'We are hiring a Senior Pega Developer to design and build Pega applications',
                     'Build case types on Pega8 and PRPC_7 with hands-on development.'):
            self.assertTrue(rank.has_pega_duty(text), text)

    def test_boilerplate_and_passing_mentions_do_not(self):
        for text in ('', 'About Us\nWe are a certified partner of Pega and deliver digital transformation.',
                     'Pegasystems is the leader in workflow automation software.',
                     'Pega Developer', 'Experience with Pega or Appian is a plus.',
                     'Good to have: Pega knowledge would be an added advantage.',
                     'No Pega experience is needed; this is a Java role with Spring Boot development.',
                     'Develop Java services for the Pegasus platform.'):
            self.assertFalse(rank.has_pega_duty(text), text)


class RankerTest(unittest.TestCase):
    def setUp(self):
        self.ranker = rank.make_ranker(model.load_config(), REGISTRY, today=TODAY)

    def score(self, title='Pega Developer', company='Commonwealth Bank', location='Bengaluru', **extra):
        return self.ranker(model.make_job('LinkedIn', '1', title, company, 'https://x.test', location, **extra))

    def test_shape(self):
        verdict = self.score(description='Design and build Pega applications.', posted_at='2026-11-12')
        self.assertEqual(set(verdict), {'employer_type', 'score', 'fit', 'pega_title', 'pega_duty'})
        self.assertEqual(set(verdict['fit']), {'reasons', 'labels'})
        self.assertEqual(set(verdict['fit']['labels']), {'employer_type', 'pay', 'experience', 'bengaluru',
                                                         'current_employer'})
        self.assertIs(verdict['fit']['labels']['current_employer'], False)
        self.assertIsInstance(verdict['score'], int)
        self.assertTrue(0 <= verdict['score'] <= 100)
        self.assertEqual((verdict['employer_type'], verdict['pega_title'], verdict['pega_duty']), ('gcc', True, True))
        self.assertIs(verdict['fit']['labels']['bengaluru'], True)
        self.assertTrue(all(isinstance(reason, str) for reason in verdict['fit']['reasons']))

    def test_bengaluru_product_role_outranks_hyderabad_services_lead(self):
        best = self.score('Pega Developer', 'Pegasystems', 'Bengaluru, Karnataka')
        worst = self.score('Pega Lead', 'Tata Consultancy Services', 'Hyderabad')
        self.assertEqual((best['employer_type'], worst['employer_type']), ('product', 'services'))
        self.assertGreater(best['score'], worst['score'] + 40)
        self.assertGreaterEqual(best['score'], 70)

    def test_weight_order_role_then_bengaluru_then_employer(self):
        blr_gcc = self.score()['score']
        blr_services = self.score(company='Infosys')['score']
        hyd_gcc = self.score(location='Hyderabad')['score']
        hyd_services = self.score(company='Infosys', location='Hyderabad')['score']
        blr_gcc_tester = self.score(title='Pega Tester')['score']
        self.assertGreater(blr_gcc, blr_services)
        self.assertGreater(blr_services, hyd_gcc)          # Bengaluru outweighs the employer type
        self.assertGreater(hyd_gcc, hyd_services)
        self.assertGreater(hyd_services, blr_gcc_tester)   # being a developer role outweighs both

    def test_support_and_testing_roles_rank_low(self):
        developer = self.score('Pega Developer')['score']
        for title in ('Pega Tester', 'Pega QA Engineer', 'Pega Support Engineer', 'Pega Business Analyst',
                      'Pega Production Support', 'Pega Administrator', 'Pega Business Architect'):
            verdict = self.score(title)
            self.assertLess(verdict['score'], developer - 40, title)
            self.assertLess(verdict['score'], 40, title)
            self.assertIn('Not a developer role', verdict['fit']['reasons'], title)
        for title in ('Pega Developer (L3 support rota)', 'Senior System Architect - Pega', 'Pega CSSA'):
            self.assertNotIn('Not a developer role', self.score(title)['fit']['reasons'], title)

    def test_lead_and_architect_only_titles_are_penalised(self):
        developer = self.score('Senior Pega Developer')['score']
        for title in ('Pega Lead System Architect', 'Pega Architect', 'Pega Technical Lead', 'Principal Pega Engineer',
                      'Pega Delivery Manager'):
            self.assertLess(self.score(title)['score'], developer, title)
        for title in ('Pega Senior System Architect', 'Pega System Architect', 'Sr. System Architect (Pega)'):
            self.assertEqual(self.score(title)['score'], developer, title)

    def test_junior_titles_are_penalised(self):
        verdict = self.score('Pega Developer Intern')
        self.assertLess(verdict['score'], self.score()['score'])
        self.assertIn('Junior title', verdict['fit']['reasons'])

    def test_experience_fit(self):
        # Career start 2022-08-01 and today 2026-11-14: about 4.3 years.
        base = self.score()['score']
        fits = self.score(experience_min=3, experience_max=6)
        stretch = self.score(experience_min=5.5)
        over = self.score(experience_min=7)
        senior = self.score(experience_min=10, experience_max=14)
        capped = self.score(experience_min=0, experience_max=2)
        self.assertGreater(fits['score'], stretch['score'])
        self.assertGreater(stretch['score'], base)
        self.assertGreater(base, over['score'])
        self.assertGreater(over['score'], senior['score'])
        self.assertLess(capped['score'], base)
        self.assertEqual(fits['fit']['labels']['experience'], '3-6 yrs')
        self.assertEqual(stretch['fit']['labels']['experience'], '5.5+ yrs')
        self.assertEqual(self.score()['fit']['labels']['experience'], 'not stated')
        self.assertIn('Experience range fits', fits['fit']['reasons'])
        self.assertIn('Asks 10+ years', senior['fit']['reasons'])
        self.assertIn('Capped at 2 years', capped['fit']['reasons'])

    def test_experience_is_read_from_the_text_when_not_given(self):
        verdict = self.score(description='Requirements:\n8+ years of experience building Pega applications.')
        self.assertEqual(verdict['fit']['labels']['experience'], '8+ yrs')
        self.assertIn('Asks 8+ years', verdict['fit']['reasons'])
        self.assertEqual(self.score('Pega Developer (4-6 yrs)')['fit']['labels']['experience'], '4-6 yrs')

    def test_zero_experience_from_a_board_means_not_stated(self):
        base = self.score()
        for low, high in ((0, 0), (0, None), (None, 0), (0.0, 0.0)):
            verdict = self.score(experience_min=low, experience_max=high)
            self.assertEqual((verdict['score'], verdict['fit']['labels']['experience']), (base['score'], 'not stated'))
            self.assertFalse(any('Capped' in reason for reason in verdict['fit']['reasons']))
        from_text = self.score(experience_min=0, experience_max=0, description='Requirements:\n5+ years of Pega experience.')
        self.assertEqual(from_text['fit']['labels']['experience'], '5+ yrs')
        open_ended = self.score(experience_min=3, experience_max=0)
        self.assertEqual(open_ended['fit']['labels']['experience'], '3+ yrs')

    def test_a_contract_length_in_the_title_is_not_a_cap(self):
        verdict = self.score('Pega Developer - 6 Months Contract')
        self.assertEqual((verdict['score'], verdict['fit']['labels']['experience']), (self.score()['score'], 'not stated'))

    def test_a_title_range_does_not_hide_a_stricter_description(self):
        verdict = self.score('Pega Developer (3-5 yrs)', description='Requirements:\nMinimum 9 years of experience in Pega.')
        self.assertEqual(verdict['fit']['labels']['experience'], '9+ yrs')
        self.assertIn('Asks 9+ years', verdict['fit']['reasons'])
        title_only = self.score('Pega Developer (3-5 yrs)', description='Build Pega applications with the team.')
        self.assertEqual(title_only['fit']['labels']['experience'], '3-5 yrs')
        stricter_title = self.score('Pega Lead 10+ years', description='At least 2 years of experience with Agile.')
        self.assertEqual(stricter_title['fit']['labels']['experience'], '10+ yrs')

    def test_stated_experience_overrides_title_guesswork(self):
        lead = self.score('Pega Lead', experience_min=4, experience_max=7)
        self.assertNotIn('Lead or architect title; likely 8+ years', lead['fit']['reasons'])
        self.assertGreater(lead['score'], self.score('Pega Lead')['score'])

    def test_salary_against_the_target(self):
        base = self.score()
        high = self.score(salary_min_lpa=28, salary_max_lpa=38)
        low = self.score(salary_max_lpa=14)
        middle = self.score(salary_max_lpa=24)
        self.assertGreater(high['score'], base['score'])
        self.assertLess(low['score'], base['score'])
        self.assertEqual(middle['score'], base['score'])
        self.assertEqual((base['fit']['labels']['pay'], high['fit']['labels']['pay']), ('30+ plausible', 'up to 38 LPA'))
        self.assertEqual(self.score(company='Infosys')['fit']['labels']['pay'], '30+ unlikely')
        self.assertEqual(self.score(company='Blue Kite Labs')['fit']['labels']['pay'], 'pay unknown')

    def test_a_figure_that_cannot_be_lpa_is_ignored(self):
        base = self.score()
        for extra in ({'salary_min_lpa': 90000, 'salary_max_lpa': 120000}, {'salary_max_lpa': 0}, {'salary_max_lpa': 450}):
            verdict = self.score(**extra)
            self.assertEqual((verdict['score'], verdict['fit']['labels']['pay']), (base['score'], '30+ plausible'), extra)

    def test_enterprise_employers_sit_between_unknown_and_gcc(self):
        registry = rank.Registry([{'name': 'Kotak Mahindra Bank', 'type': 'enterprise'},
                                  {'name': 'Commonwealth Bank', 'type': 'gcc'}])
        ranker = rank.make_ranker(model.load_config(), registry, today=TODAY)

        def verdict(company):
            return ranker(model.make_job('s', '1', 'Pega Developer', company, 'u', 'Bengaluru'))
        enterprise, gcc, unknown = verdict('Kotak Mahindra Bank'), verdict('Commonwealth Bank'), verdict('Blue Kite Labs')
        self.assertEqual((enterprise['employer_type'], enterprise['fit']['labels']['pay']), ('enterprise', 'pay unknown'))
        self.assertGreater(gcc['score'], enterprise['score'])
        self.assertGreater(enterprise['score'], unknown['score'])
        self.assertIn('enterprise', rank.EMPLOYER_TYPES)
        for company in ('HDFC Bank', 'ICICI Lombard', 'ITC Limited', 'Kotak Securities'):
            self.assertEqual(rank.Registry().classify(company)[0], 'enterprise', company)
        self.assertEqual(rank.Registry().classify('Tech Mahindra')[0], 'services')

    def test_the_current_employer_is_kept_but_sorted_last(self):
        for company in ('Mercedes-Benz Research and Development India', 'Mercedes-Benz', 'Mercedes-Benz R&D India Pvt Ltd'):
            verdict = self.score(company=company, description='Design and build Pega applications.')
            self.assertEqual((verdict['score'], verdict['fit']['reasons'][0], verdict['fit']['labels']['current_employer']),
                             (0, 'Current employer', True), company)
            self.assertEqual((verdict['employer_type'], verdict['pega_title'], verdict['pega_duty']), ('gcc', True, True))
        other = self.score(company='Mercedes Motors Dealership')
        self.assertFalse(other['fit']['labels']['current_employer'])

    def test_a_registry_flag_keeps_sister_companies_and_the_parent_group_apart(self):
        registry = rank.Registry([
            {'name': 'Mercedes-Benz Research and Development India', 'type': 'gcc', 'current_employer': True},
            {'name': 'Mercedes-Benz Group', 'type': 'gcc'}, {'name': 'Mercedes-Benz Mobility', 'type': 'gcc'}])
        ranker = rank.make_ranker(model.load_config(), registry, today=TODAY)     # config still says "Mercedes-Benz"

        def current(company):
            return ranker(model.make_job('s', '1', 'Pega Developer', company, 'u', 'Bengaluru'))['fit']['labels']['current_employer']
        self.assertTrue(current('Mercedes-Benz Research and Development India'))
        self.assertFalse(current('Mercedes-Benz Group'))
        self.assertFalse(current('Mercedes-Benz Mobility'))
        self.assertTrue(current('Mercedes-Benz Trucks Unlisted'))             # not in the registry: the config name decides

    def test_the_current_employer_can_be_flagged_in_the_registry(self):
        registry = rank.Registry([{'name': 'MBRDI', 'aliases': ['Mercedes-Benz Research and Development India'],
                                   'type': 'gcc', 'current_employer': True},
                                  {'name': 'Globex', 'type': 'gcc', 'current_employer': False}])
        config = model.load_config()
        config['profile']['current_employer'] = ''
        ranker = rank.make_ranker(config, registry, today=TODAY)
        flagged = ranker(model.make_job('s', '1', 'Pega Developer', 'MBRDI', 'u', 'Bengaluru'))
        self.assertEqual((flagged['score'], flagged['fit']['labels']['current_employer']), (0, True))
        plain = ranker(model.make_job('s', '1', 'Pega Developer', 'Globex', 'u', 'Bengaluru'))
        self.assertFalse(plain['fit']['labels']['current_employer'])
        self.assertGreater(plain['score'], 60)

    def test_recency(self):
        fresh = self.score(posted_at='2026-11-12')['score']
        recent = self.score(posted_at='2026-10-25')['score']
        undated = self.score()['score']
        stale = self.score(posted_at='2026-08-01')
        self.assertGreater(fresh, recent)
        self.assertGreater(recent, undated)
        self.assertLess(stale['score'], undated)
        self.assertIn('Posted over 60 days ago; may be stale', stale['fit']['reasons'])

    def test_pega_evidence(self):
        confirmed = self.score(description='Design and build Pega case types and integrations.')
        unread = self.score()
        passing = self.score('Java Developer', description='About Us\nWe are a certified partner of Pega.\n'
                                                           'Role\nBuild Spring Boot services in Java.')
        by_duty = self.score('Senior System Engineer', description='You will design and develop Pega PRPC applications.')
        self.assertGreater(confirmed['score'], unread['score'])
        self.assertIn('Description not read yet', unread['fit']['reasons'])
        self.assertEqual((passing['pega_title'], passing['pega_duty']), (False, False))
        self.assertIn('Pega is only mentioned in passing', passing['fit']['reasons'])
        self.assertEqual((by_duty['pega_title'], by_duty['pega_duty']), (False, True))
        self.assertGreater(by_duty['score'], passing['score'] + 25)
        self.assertGreater(unread['score'], by_duty['score'])          # Pega in the title still ranks first

    def test_city_handling(self):
        multi = self.score(location='Hyderabad / Bengaluru / Pune')
        self.assertEqual(multi['score'], self.score()['score'])
        self.assertTrue(multi['fit']['labels']['bengaluru'])
        nowhere = self.score(location='India')
        self.assertIn('City not stated', nowhere['fit']['reasons'])
        self.assertFalse(nowhere['fit']['labels']['bengaluru'])
        self.assertGreater(self.score()['score'], nowhere['score'])
        self.assertGreater(nowhere['score'], self.score(location='Chennai')['score'])

    def test_stored_rows_use_their_merged_cities(self):
        row = {'title': 'Pega Developer', 'company': 'Commonwealth Bank', 'location': 'Hyderabad',
               'cities': ['Hyderabad', 'Bengaluru'], 'description': '', 'posted_at': None}
        self.assertEqual(self.ranker(row)['score'], self.score()['score'])

    def test_scores_stay_between_0_and_100(self):
        top = self.score('Pega CSSA Developer', 'Pegasystems', 'Bengaluru', posted_at='2026-11-13', salary_max_lpa=45,
                         experience_min=3, experience_max=6,
                         description='Design and develop Pega applications. CSSA certification is required.')
        bottom = self.score('QA Tester Intern', 'ABC Staffing', 'Kolkata', posted_at='2026-01-01', salary_max_lpa=3,
                            experience_min=12, description='Manual testing of web pages.')
        self.assertEqual((top['score'], bottom['score']), (100, 0))

    def test_focus_comes_from_the_config(self):
        config = model.load_config()
        config['focus'] = {'cities_first': ['Pune'], 'employer_types_first': ['services']}
        config['profile']['target_lpa'] = 20
        ranker = rank.make_ranker(config, REGISTRY, today=TODAY)
        pune = ranker(model.make_job('s', '1', 'Pega Developer', 'Globex', 'u', 'Pune'))
        bengaluru = ranker(model.make_job('s', '1', 'Pega Developer', 'Globex', 'u', 'Bengaluru'))
        self.assertGreater(pune['score'], bengaluru['score'])
        self.assertTrue(bengaluru['fit']['labels']['bengaluru'])       # the label is literal
        gcc = ranker(model.make_job('s', '1', 'Pega Developer', 'Commonwealth Bank', 'u', 'Pune'))
        self.assertEqual((gcc['employer_type'], gcc['fit']['labels']['pay']), ('gcc', '20+ plausible'))
        self.assertEqual(gcc['score'], pune['score'])                  # no longer a preferred employer type

    def test_a_sparse_config_still_ranks(self):
        verdict = rank.make_ranker({}, rank.Registry())(model.make_job('s', '1', 'Pega Developer', 'Acme', 'u', 'Bengaluru'))
        self.assertGreater(verdict['score'], 0)


# ───────────────────────────── scan ─────────────────────────────

class FakeTask:
    def __init__(self, name, kind='board', priority=10, status='ok', jobs=(), raises=None, found=0, requests=1,
                 error=None, returns=None, journal=None, reason=''):
        self.name, self.label, self.kind, self.priority = name, name, kind, priority
        self._outcome = dict(status=status, jobs=jobs, found=found, requests=requests, error=error, reason=reason)
        self._raises, self._returns, self._journal = raises, returns, journal
        self.ctx = None

    def run(self, http, ctx):
        self.ctx = ctx
        if self._journal is not None:
            self._journal.append(self.name)
        if self._raises:
            raise self._raises
        if self._returns is not None:
            return self._returns
        source = model.EMPLOYER_SOURCE if self.kind == 'ats' else self.name
        return model.make_result(source, self.label, self.kind, **self._outcome)


class FakeHttp:
    requests = 17

    def __init__(self, expired=False):
        self._expired = expired

    def expired(self):
        return self._expired


def board_job(source, source_id, title='Pega Developer', company='Globex', location='Bengaluru'):
    return model.make_job(source, source_id, title, company, f'https://{source.lower()}.test/{source_id}', location)


class ScanCase(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.data = Path(folder.name) / 'data'
        self.store = Store(self.data / 'radar.sqlite3')
        self.config = model.load_config()
        self.config['companies_path'] = str(self.data / 'no-companies.json')   # pattern fallback only
        self.config['scan']['workers'] = 3

    def run_scan(self, tasks, **options):
        options.setdefault('http', FakeHttp())
        return scan.run_scan(self.config, self.store, tasks=tasks, **options)


class ScanTest(ScanCase):
    def mixed_tasks(self):
        return [
            FakeTask('LinkedIn', kind='linkedin', priority=1, found=120, requests=30, jobs=[
                board_job('LinkedIn', 'l1', company='Wells Fargo'),
                board_job('LinkedIn', 'l2', company='Infosys', location='Hyderabad'),
                board_job('LinkedIn', 'l3', company='Blue Kite Labs', location='Bengaluru')]),
            FakeTask('Hirist', priority=5, jobs=[board_job('Hirist', 'h1', company='Salesforce', location='Pune')]),
            FakeTask('Cutshort', priority=5, status='empty'),
            FakeTask('Shine', priority=5, status='blocked', error='HTTP 403'),
            FakeTask('Instahyre', priority=5, raises=RuntimeError('markup changed')),
            FakeTask('Naukri', priority=9, status='skipped', error='refuses automated access'),
        ]

    def test_summary_counts_and_partial_status(self):
        summary = self.run_scan(self.mixed_tasks())
        self.assertEqual(set(summary) - {'window_days'},
                         {'run_id', 'started_at', 'finished_at', 'minutes', 'status', 'new', 'new_bengaluru',
                          'new_product_gcc', 'requests', 'sources', 'attention', 'mode', 'configured', 'requested',
                          'attempted', 'completed', 'not_attempted', 'reasons', 'unmatched'})
        self.assertEqual((summary['mode'], summary['configured'], summary['requested'], summary['attempted'],
                          summary['completed'], summary['not_attempted'], summary['unmatched']),
                         ('full', 6, 6, 6, 3, [], []))
        self.assertEqual(summary['reasons'], {'refused': 1, 'unknown': 2})
        self.assertEqual(summary['status'], 'partial')
        self.assertEqual((summary['new'], summary['new_bengaluru'], summary['new_product_gcc']), (4, 2, 2))
        self.assertEqual(summary['requests'], 17)
        self.assertEqual(sorted(summary['attention']), ['Instahyre', 'Naukri', 'Shine'])   # skipped is lost coverage too
        self.assertEqual(summary['window_days'], 30)
        statuses = {source['label']: source['status'] for source in summary['sources']}
        self.assertEqual(statuses, {'LinkedIn': 'ok', 'Hirist': 'ok', 'Cutshort': 'empty', 'Shine': 'blocked',
                                    'Instahyre': 'error', 'Naukri': 'skipped'})
        self.assertTrue(all('jobs' not in source for source in summary['sources']))
        linkedin = next(source for source in summary['sources'] if source['label'] == 'LinkedIn')
        self.assertEqual((linkedin['found'], linkedin['kept'], linkedin['new']), (120, 3, 3))

    def test_a_raising_task_is_an_error_result_not_a_crash(self):
        summary = self.run_scan([FakeTask('Instahyre', raises=KeyError('items')),
                                 FakeTask('Acme', kind='ats', raises=ValueError('bad json'))])
        by_label = {source['label']: source for source in summary['sources']}
        self.assertEqual(by_label['Instahyre']['status'], 'error')
        self.assertIn('KeyError', by_label['Instahyre']['error'])
        self.assertEqual((by_label['Acme']['source'], by_label['Acme']['kind']), (model.EMPLOYER_SOURCE, 'ats'))
        self.assertEqual(summary['status'], 'partial')

    def test_a_malformed_result_is_an_error(self):
        summary = self.run_scan([FakeTask('Odd', returns={'status': 'ok'}), FakeTask('Text', returns='not a result'),
                                 FakeTask('Typo', returns={**model.make_result('Typo', 'Typo', 'board'), 'status': 'fine'})])
        self.assertEqual([source['status'] for source in summary['sources']], ['error'] * 3)
        self.assertEqual(len(summary['attention']), 3)

    def test_the_run_and_health_are_stored(self):
        summary = self.run_scan(self.mixed_tasks())
        run = self.store.latest_run()
        self.assertEqual((run['id'], run['status']), (summary['run_id'], 'partial'))
        self.assertEqual(run['summary']['new'], 4)
        self.assertEqual({row['label']: row['status'] for row in run['health']},
                         {source['label']: source['status'] for source in summary['sources']})
        rows, total = self.store.jobs(view='new', city='bengaluru', types=['product', 'gcc'])
        self.assertEqual((total, rows[0]['company'], rows[0]['employer_type']), (1, 'Wells Fargo', 'gcc'))
        self.assertGreater(rows[0]['score'], 60)                       # ranked with the real ranker

    def test_complete_status_and_second_scan_finds_nothing_new(self):
        tasks = [FakeTask('Hirist', jobs=[board_job('Hirist', 'h1')]), FakeTask('Cutshort', status='empty'),
                 ]
        first = self.run_scan(tasks)
        self.assertEqual((first['status'], first['new'], first['attention']), ('complete', 1, []))
        second = self.run_scan(tasks)
        self.assertEqual((second['status'], second['new'], second['window_days']), ('complete', 0, 3))
        self.assertEqual(self.store.jobs(view='new')[1], 1)             # still in the inbox until it is looked at

    def test_a_partial_run_does_not_shorten_the_next_window(self):
        self.run_scan([FakeTask('Shine', status='blocked')])
        self.assertIsNone(self.store.kv_get(scan.KV_LAST_COMPLETE))
        self.assertEqual(self.run_scan([FakeTask('Shine', status='empty')])['window_days'], 30)

    def test_a_partial_run_with_linkedin_ok_shortens_the_window(self):
        for outcome in ({'status': 'ok', 'jobs': [board_job('LinkedIn', 'l1')]}, {'status': 'empty', 'found': 40}):
            self.store.kv_set(scan.KV_LINKEDIN_OK, None)
            self.store.kv_set(scan.KV_LAST_COMPLETE, None)
            first = self.run_scan([FakeTask('LinkedIn', kind='linkedin', **outcome),
                                   FakeTask('Acme', kind='ats', status='maintenance', error='HTTP 503')])
            self.assertEqual((first['status'], first['window_days']), ('partial', 30))
            self.assertEqual(self.store.kv_get(scan.KV_LINKEDIN_OK), first['finished_at'])
            task = FakeTask('LinkedIn', kind='linkedin', status='empty')
            self.assertEqual(self.run_scan([task])['window_days'], 3)
            self.assertEqual(task.ctx['window_days'], 3)

    def test_sweep_complete_decides_the_stamp_when_a_source_reports_it(self):
        def linkedin(**outcome):
            task = FakeTask('LinkedIn', kind='linkedin')
            task._returns = model.make_result('LinkedIn', 'LinkedIn', 'linkedin', **outcome)
            return task
        jobs = [board_job('LinkedIn', 'l1')]
        # One description that 404s leaves the result partial, yet every day of the window was searched.
        first = self.run_scan([linkedin(status='partial', jobs=jobs, found=30, sweep_complete=True, error='1 unread')])
        self.assertEqual((first['status'], first['sources'][0]['sweep_complete']), ('partial', True))
        self.assertEqual(self.store.kv_get(scan.KV_LINKEDIN_OK), first['finished_at'])
        self.assertEqual(self.run_scan([linkedin(status='partial', sweep_complete=True)])['window_days'], 3)

        self.store.kv_set(scan.KV_LINKEDIN_OK, None)
        for outcome in ({'status': 'ok', 'jobs': jobs, 'sweep_complete': False},           # cut short, whatever the status
                        {'status': 'partial', 'jobs': jobs},                                # no flag: the old ok/empty rule
                        {'status': 'empty', 'found': 0, 'sweep_complete': True}):           # first ever and nothing listed
            self.run_scan([linkedin(**outcome)])
            self.assertIsNone(self.store.kv_get(scan.KV_LINKEDIN_OK), outcome)
        self.assertEqual(self.run_scan([linkedin(status='ok', jobs=jobs)])['window_days'], 30)
        self.assertIsNotNone(self.store.kv_get(scan.KV_LINKEDIN_OK))

    def test_commit_is_called_only_after_a_successful_save(self):
        calls = []

        class Checkpointed(FakeTask):
            def commit(self):
                calls.append(self.name)
                if self.name == 'Cutshort':
                    raise RuntimeError('kv write failed')
        real = self.store.save_result

        def fails_for_linkedin(run_id, result, ranker):
            if result['label'] == 'LinkedIn' and result['status'] != 'error':
                raise RuntimeError('disk full')
            return real(run_id, result, ranker)
        tasks = [Checkpointed('LinkedIn', kind='linkedin', priority=1, jobs=[board_job('LinkedIn', 'l1')]),
                 Checkpointed('Hirist', priority=2, jobs=[board_job('Hirist', 'h1', company='Initech')]),
                 Checkpointed('Cutshort', priority=3, status='empty'),
                 Checkpointed('Shine', priority=4, raises=RuntimeError('markup changed')),
                 FakeTask('Instahyre', priority=5, status='empty')]             # a task without commit is fine
        with mock.patch.object(self.store, 'save_result', side_effect=fails_for_linkedin), \
                self.assertLogs('radar', level='ERROR'):
            summary = self.run_scan(tasks)
        # LinkedIn's results were lost, so its checkpoint must not move; a task that raised still gets its
        # (error) result stored and may record what it did.
        self.assertEqual(sorted(calls), ['Cutshort', 'Hirist', 'Shine'])
        statuses = {source['label']: source['status'] for source in summary['sources']}
        self.assertEqual(statuses, {'LinkedIn': 'error', 'Hirist': 'ok', 'Cutshort': 'empty', 'Shine': 'error',
                                    'Instahyre': 'empty'})                        # a failing commit changes nothing
        self.assertIsNone(self.store.kv_get(scan.KV_LINKEDIN_OK))

    def test_a_first_ever_empty_linkedin_does_not_shorten_the_window(self):
        nothing_listed = FakeTask('LinkedIn', kind='linkedin', status='empty', found=0, requests=12)
        first = self.run_scan([nothing_listed, FakeTask('Hirist', status='empty')])
        self.assertEqual(first['status'], 'complete')
        self.assertIsNone(self.store.kv_get(scan.KV_LINKEDIN_OK))
        self.assertIsNone(self.store.kv_get(scan.KV_LAST_COMPLETE))
        self.assertEqual(self.run_scan([nothing_listed])['window_days'], 30)
        good = self.run_scan([FakeTask('LinkedIn', kind='linkedin', jobs=[board_job('LinkedIn', 'l1')])])
        self.assertEqual(self.store.kv_get(scan.KV_LINKEDIN_OK), good['finished_at'])
        quiet = self.run_scan([nothing_listed])                        # after a good sweep, a quiet day is believable
        self.assertEqual((quiet['window_days'], self.store.kv_get(scan.KV_LINKEDIN_OK)), (3, quiet['finished_at']))

    def test_linkedin_trouble_keeps_the_long_window(self):
        for status in ('partial', 'blocked', 'error', 'maintenance', 'skipped'):
            self.run_scan([FakeTask('LinkedIn', kind='linkedin', status=status), FakeTask('Hirist', status='empty')])
            self.assertIsNone(self.store.kv_get(scan.KV_LINKEDIN_OK), status)
        self.run_scan([FakeTask('LinkedIn', kind='linkedin', raises=RuntimeError('markup changed'))])
        self.assertIsNone(self.store.kv_get(scan.KV_LINKEDIN_OK))
        self.assertEqual(self.run_scan([FakeTask('LinkedIn', kind='linkedin', status='empty')])['window_days'], 30)

    def test_the_linkedin_date_wins_over_the_older_complete_run_key(self):
        now = datetime.now(timezone.utc)
        self.store.kv_set(scan.KV_LAST_COMPLETE, (now - timedelta(days=20)).isoformat(timespec='seconds'))
        self.assertEqual(self.run_scan([FakeTask('Hirist', status='blocked')])['window_days'], 22)   # fallback
        self.store.kv_set(scan.KV_LINKEDIN_OK, (now - timedelta(days=4)).isoformat(timespec='seconds'))
        self.assertEqual(self.run_scan([FakeTask('Hirist', status='blocked')])['window_days'], 6)

    def test_tasks_run_in_priority_order_with_the_context(self):
        self.config['scan']['workers'] = 1
        journal = []
        tasks = [FakeTask('boards', priority=30, journal=journal), FakeTask('linkedin', priority=1, journal=journal),
                 FakeTask('ats', priority=20, journal=journal)]
        self.run_scan(tasks)
        self.assertEqual(journal, ['linkedin', 'ats', 'boards'])
        ctx = tasks[0].ctx
        self.assertEqual(set(ctx), {'window_days', 'store', 'config', 'log'})
        self.assertIs(ctx['store'], self.store)
        self.assertIs(ctx['config'], self.config)
        self.assertEqual(ctx['window_days'], 30)
        ctx['log'].info('sources can log through the context')

    def test_progress_is_recorded_in_kv_and_sent_to_the_callback(self):
        seen = []
        summary = self.run_scan(self.mixed_tasks(), progress=seen.append)
        final = self.store.kv_get(scan.KV_PROGRESS)
        self.assertEqual((final['run_id'], final['state'], final['status']), (summary['run_id'], 'finished', 'partial'))
        self.assertEqual((final['total'], final['done'], final['new'], final['running']), (6, 6, 4, []))
        self.assertEqual((final['mode'], final['requested'], final['attempted'], final['completed'],
                          final['not_attempted']), ('full', 6, 6, 3, []))
        for key in ('requested', 'attempted', 'completed'):
            self.assertEqual(final[key], summary[key], key)             # the live counts end equal to the summary's
        self.assertEqual((seen[0]['requested'], seen[0]['attempted'], seen[0]['completed']), (0, 0, 0))
        self.assertEqual([snapshot['attempted'] for snapshot in seen], sorted(snapshot['attempted'] for snapshot in seen))
        self.assertEqual(sorted(final['attention']), ['Instahyre', 'Naukri', 'Shine'])
        self.assertEqual(seen[-1], final)
        self.assertEqual(seen[0]['state'], 'running')
        self.assertEqual([snapshot['done'] for snapshot in seen], sorted(snapshot['done'] for snapshot in seen))
        self.assertTrue(any(snapshot['running'] for snapshot in seen))

    def test_progress_is_reset_before_any_source_runs(self):
        first = self.run_scan([FakeTask('Hirist', status='empty')])
        self.assertEqual(self.store.kv_get(scan.KV_PROGRESS)['state'], 'finished')
        polled, seen = [], []

        class Poll(FakeTask):
            def run(task, http, ctx):
                polled.append(ctx['store'].kv_get(scan.KV_PROGRESS))
                return super().run(http, ctx)
        second = self.run_scan([Poll('Hirist', status='empty')], progress=seen.append)
        self.assertEqual((polled[0]['run_id'], polled[0]['state']), (second['run_id'], 'running'))
        self.assertNotEqual(polled[0]['run_id'], first['run_id'])
        # The very first snapshot replaces the old one before the run even has an id.
        self.assertEqual((seen[0]['run_id'], seen[0]['state'], seen[0]['total'], seen[0]['done'], seen[0]['new']),
                         (None, 'running', 0, 0, 0))
        self.assertEqual(seen[1]['run_id'], second['run_id'])

    def test_the_fresh_snapshot_is_written_before_sources_are_built(self):
        self.run_scan([FakeTask('Hirist', status='empty')])
        snapshots = []

        def build_tasks(config, registry, store):
            snapshots.append(store.kv_get(scan.KV_PROGRESS))
            return [FakeTask('Hirist', status='empty')]
        fake_sources = mock.MagicMock(build_tasks=build_tasks)
        with mock.patch.dict(sys.modules, {'radar.sources': fake_sources}):
            summary = scan.run_scan(self.config, self.store, http=FakeHttp())
        self.assertEqual((snapshots[0]['run_id'], snapshots[0]['state']), (None, 'running'))   # not the old finished one
        self.assertEqual(self.store.kv_get(scan.KV_PROGRESS)['run_id'], summary['run_id'])

    def test_a_failing_progress_callback_does_not_stop_the_scan(self):
        def broken(_snapshot):
            raise RuntimeError('ui went away')
        with self.assertLogs('radar', level='WARNING'):
            summary = self.run_scan([FakeTask('Hirist', status='empty')], progress=broken)
        self.assertEqual(summary['status'], 'complete')

    def test_sources_not_started_before_the_deadline_are_reported(self):
        task = FakeTask('Hirist', jobs=[board_job('Hirist', 'h1')])
        summary = self.run_scan([task], http=FakeHttp(expired=True))
        self.assertIsNone(task.ctx)                                    # it never ran
        self.assertEqual((summary['status'], summary['sources'][0]['status'], summary['attention']),
                         ('partial', 'error', ['Hirist']))
        self.assertIn('time budget', summary['sources'][0]['error'])

    def test_no_sources_is_a_failed_run(self):
        summary = self.run_scan([])
        self.assertEqual(summary['status'], 'failed')
        self.assertIn('no sources', summary['error'])
        run = self.store.latest_run()
        self.assertEqual((run['status'], run['last_attempt']['status']), (None, 'failed'))
        self.assertIn('no sources', run['last_attempt']['error'])
        self.assertEqual(self.store.kv_get(scan.KV_PROGRESS)['state'], 'finished')

    def test_a_save_failure_is_lost_coverage(self):
        calls = []
        real = self.store.save_result

        def flaky(run_id, result, ranker):
            calls.append(result['status'])
            if len(calls) == 1:
                raise RuntimeError('disk full')
            return real(run_id, result, ranker)
        with mock.patch.object(self.store, 'save_result', side_effect=flaky):
            summary = self.run_scan([FakeTask('Hirist', jobs=[board_job('Hirist', 'h1')])])
        self.assertEqual((calls, summary['status'], summary['new']), (['ok', 'error'], 'partial', 0))
        self.assertIn('could not be saved', summary['sources'][0]['error'])

    def test_one_unsavable_source_does_not_discard_the_others(self):
        real = self.store.save_result

        def broken_for_hirist(run_id, result, ranker):
            if result['label'] == 'Hirist':
                raise RuntimeError('database is locked')               # the jobs and then the error record both fail
            return real(run_id, result, ranker)
        tasks = [FakeTask('Hirist', priority=1, jobs=[board_job('Hirist', 'h1')]),
                 FakeTask('Cutshort', priority=2, jobs=[board_job('Cutshort', 'c1', company='Initech')]),
                 FakeTask('Shine', priority=3, status='empty')]
        with mock.patch.object(self.store, 'save_result', side_effect=broken_for_hirist):
            summary = self.run_scan(tasks)
        by_label = {source['label']: source for source in summary['sources']}
        self.assertEqual({label: source['status'] for label, source in by_label.items()},
                         {'Hirist': 'error', 'Cutshort': 'ok', 'Shine': 'empty'})
        self.assertEqual((summary['status'], summary['new'], summary['attention']), ('partial', 1, ['Hirist']))
        self.assertEqual(self.store.jobs()[0][0]['company'], 'Initech')

    def test_reported_kept_is_what_was_stored(self):
        result = {**model.make_result('Hirist', 'Hirist', 'board'), 'found': 2, 'kept': 2,
                  'jobs': [board_job('Hirist', 'h1'), None]}
        summary = self.run_scan([FakeTask('Hirist', returns=result)])
        self.assertEqual((summary['sources'][0]['kept'], summary['sources'][0]['found'], summary['new']), (1, 2, 1))

    def test_malformed_scan_settings_fall_back_to_defaults(self):
        for broken in ({'minutes': 'forty', 'workers': None}, {'minutes': -5, 'workers': 0}, 'not a dict', None):
            self.config['scan'] = broken
            self.config['linkedin']['pacing_seconds'] = 'fast'
            captured = {}

            class Probe(FakeTask):
                def run(self, http, ctx):
                    captured['http'] = http
                    return super().run(http, ctx)
            before = scan.time.monotonic()
            summary = scan.run_scan(self.config, self.store, tasks=[Probe('Hirist', status='empty')])
            self.assertEqual(summary['status'], 'complete', broken)
            budget = captured['http'].deadline - before
            self.assertTrue(scan.DEFAULT_MINUTES * 60 - 5 < budget <= scan.DEFAULT_MINUTES * 60 + 5, broken)
            self.assertEqual(captured['http']._pacing, {'www.linkedin.com': 1.0})

    def test_a_log_file_is_written(self):
        self.run_scan([FakeTask('Hirist', status='blocked', error='HTTP 403')])
        logs = list((self.data / 'logs').glob('scan-*.log'))
        self.assertEqual(len(logs), 1)
        self.assertRegex(logs[0].name, r'^scan-\d{8}-\d{6}\.log$')
        text = logs[0].read_text(encoding='utf-8')
        self.assertIn('Hirist', text)
        self.assertIn('blocked', text)

    def test_default_http_uses_the_linkedin_pacing_from_the_config(self):
        self.config['linkedin']['pacing_seconds'] = 2.5
        captured = {}

        class Probe(FakeTask):
            def run(self, http, ctx):
                captured['http'] = http
                return super().run(http, ctx)
        scan.run_scan(self.config, self.store, tasks=[Probe('Hirist', status='empty')], minutes=1)
        http = captured['http']
        self.assertIsInstance(http, net.Http)
        self.assertEqual(http._pacing, {'www.linkedin.com': 2.5})
        self.assertIsNotNone(http.deadline)

    def test_the_configured_user_agent_reaches_the_request(self):
        self.config['http']['user_agent'] = 'ConfiguredAgent/9'
        sent = []

        class Fetch(FakeTask):
            def run(self, http, ctx):
                http._opener = lambda request, timeout: sent.append(request) or FakeReply()
                http.get('https://a.test/jobs')
                return super().run(http, ctx)
        scan.run_scan(self.config, self.store, tasks=[Fetch('Hirist', status='empty')], minutes=1)
        self.assertEqual(sent[0].get_header('User-agent'), 'ConfiguredAgent/9')
        del self.config['http']
        scan.run_scan(self.config, self.store, tasks=[Fetch('Hirist', status='empty')], minutes=1)
        self.assertEqual(sent[1].get_header('User-agent'), net.USER_AGENT)

    def test_console_logging_survives_a_cp1252_console(self):
        stream = io.TextIOWrapper(io.BytesIO(), encoding='cp1252', errors='strict')
        with mock.patch.object(sys, 'stdout', stream), mock.patch.object(sys, 'stderr', stream):
            scan.setup_console_logging()
            self.addCleanup(lambda: [scan.logger.removeHandler(handler) for handler in list(scan.logger.handlers)
                                     if getattr(handler, '_radar_console', False)])
            scan.logger.info('Kept ₹30 LPA role at 株式会社')
            print('₹ printed directly')
        stream.flush()
        self.assertIn(b'?', stream.buffer.getvalue())


class WindowTest(unittest.TestCase):
    NOW = datetime(2026, 11, 14, 2, 0, tzinfo=timezone.utc)

    def window(self, **ago):
        return scan.window_days((self.NOW - timedelta(**ago)).isoformat(timespec='seconds'), now=self.NOW)

    def test_window_days(self):
        self.assertEqual(scan.window_days(None, now=self.NOW), 30)     # first run
        self.assertEqual(scan.window_days('', now=self.NOW), 30)
        self.assertEqual(scan.window_days('garbage', now=self.NOW), 30)
        self.assertEqual(self.window(hours=2), 3)                      # minimum
        self.assertEqual(self.window(days=1), 3)
        self.assertEqual(self.window(days=1, hours=12), 3)
        self.assertEqual(self.window(days=2), 4)
        self.assertEqual(self.window(days=9, hours=5), 11)
        self.assertEqual(self.window(days=28), 30)
        self.assertEqual(self.window(days=200), 30)                    # maximum
        self.assertEqual(scan.window_days('2026-11-12T02:00:00', now=self.NOW), 4)   # naive stamps are UTC


class LockTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.data = Path(folder.name) / 'data'
        self.lock = self.data / scan.LOCK_NAME

    @staticmethod
    def dead_pid():
        process = subprocess.Popen([sys.executable, '-c', 'pass'])
        process.wait()
        return process.pid

    def test_lock_is_created_and_removed(self):
        with scan.scan_lock(self.data) as path:
            self.assertEqual(path, self.lock)
            self.assertEqual(int(self.lock.read_text(encoding='utf-8').split()[0]), os.getpid())
        self.assertFalse(self.lock.exists())

    def test_lock_is_removed_when_the_scan_raises(self):
        with self.assertRaises(KeyError):
            with scan.scan_lock(self.data):
                raise KeyError('boom')
        self.assertFalse(self.lock.exists())

    def test_a_live_pid_blocks(self):
        self.data.mkdir(parents=True)
        self.lock.write_text(f'{os.getpid()} {model.now_iso()}', encoding='utf-8')
        with self.assertRaises(scan.ScanLocked):
            with scan.scan_lock(self.data):
                self.fail('the lock must not be taken')
        self.assertTrue(self.lock.exists())                            # the owner's lock is left alone

    def test_a_second_scan_in_the_same_process_is_blocked(self):
        with scan.scan_lock(self.data):
            with self.assertRaises(scan.ScanLocked):
                with scan.scan_lock(self.data):
                    self.fail('the lock must not be taken twice')
            self.assertTrue(self.lock.exists())

    def test_a_dead_pid_is_taken_over(self):
        self.data.mkdir(parents=True)
        self.lock.write_text(f'{self.dead_pid()} {model.now_iso()}', encoding='utf-8')
        with scan.scan_lock(self.data):
            self.assertEqual(int(self.lock.read_text(encoding='utf-8').split()[0]), os.getpid())
        self.assertFalse(self.lock.exists())

    def test_an_old_or_unreadable_lock_is_taken_over(self):
        self.data.mkdir(parents=True)
        self.lock.write_text(f'{os.getpid()} long ago', encoding='utf-8')
        old = self.lock.stat().st_mtime - (scan.LOCK_STALE_HOURS * 3600 + 60)
        os.utime(self.lock, (old, old))
        with scan.scan_lock(self.data):
            pass
        self.lock.write_text('not a pid', encoding='utf-8')
        with scan.scan_lock(self.data):
            pass
        self.assertFalse(self.lock.exists())

    def test_process_alive(self):
        self.assertTrue(scan.process_alive(os.getpid()))
        self.assertFalse(scan.process_alive(self.dead_pid()))
        self.assertFalse(scan.process_alive(0))
        self.assertFalse(scan.process_alive(-5))


# ───────────────────────────── CLI and launchers ─────────────────────────────

def load_cli():
    # radar.py shares its name with the radar package, so it is loaded by path.
    spec = importlib.util.spec_from_file_location('radar_cli', PROJECT / 'radar.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CliCase(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.data = Path(folder.name) / 'radar data'
        patcher = mock.patch.dict(os.environ, {'PEGA_RADAR_DATA': str(self.data)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.cli = load_cli()

    def invoke(self, *argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = self.cli.main(list(argv))
        return code, output.getvalue()

    def seed(self):
        store = Store(self.data / 'radar.sqlite3')
        run_id = store.start_run()
        jobs = [board_job('Hirist', 'h1', title='=HYPERLINK("http://evil.test")', company='Wells Fargo'),
                board_job('Hirist', 'h2', title='Pega Developer', company='Infosys', location='Pune'),
                {**board_job('Hirist', 'h3', company='Globex'), 'title': ' =1+1', 'location': '\n@SUM(1)'}]
        ids = store.save_result(run_id, model.make_result('Hirist', 'Hirist', 'board', jobs=jobs), plain_ranker)['new']
        store.set_state(ids[1], saved=True, status='applied', notes='-called HR')
        store.set_state(ids[0], hidden=True)
        return store

class CliTest(CliCase):
    def test_data_dir_follows_the_environment(self):
        self.assertEqual(self.cli.data_dir(), self.data)
        with mock.patch.dict(os.environ, {'PEGA_RADAR_DATA': ''}):
            self.assertEqual(self.cli.data_dir(), PROJECT / 'data')

    def test_export_writes_a_csv_that_cannot_run_formulas(self):
        self.seed()
        target = self.data / 'out' / 'jobs.csv'
        code, output = self.invoke('export', str(target))
        self.assertEqual(code, 0)
        self.assertIn('3 jobs written', output)
        with open(target, encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(list(rows[0]), list(self.cli.EXPORT_COLUMNS))
        by_company = {row['company']: row for row in rows}
        self.assertEqual(by_company['Wells Fargo']['title'], '\'=HYPERLINK("http://evil.test")')
        self.assertEqual((by_company['Infosys']['status'], by_company['Infosys']['saved'], by_company['Infosys']['notes'],
                          by_company['Infosys']['sources']), ('applied', 'yes', "'-called HR", 'Hirist'))
        self.assertEqual((by_company['Globex']['title'], by_company['Globex']['location']), ("'=1+1", "'\n@SUM(1)"))
        self.assertEqual((by_company['Wells Fargo']['hidden'], by_company['Infosys']['hidden']), ('yes', 'no'))
        self.assertTrue(by_company['Infosys']['seen_at'])

    def test_export_has_a_default_path(self):
        self.seed()
        code, _ = self.invoke('export')
        self.assertEqual(code, 0)
        self.assertEqual(len(list(self.data.glob('pega-radar-jobs-*.csv'))), 1)

    def test_rescore_uses_the_real_ranker(self):
        store = self.seed()
        code, output = self.invoke('rescore')
        self.assertEqual((code, output.strip()), (0, '3 jobs re-ranked'))
        types = {row['company']: row['employer_type'] for row in store.jobs()[0]}
        self.assertEqual(types['Infosys'], 'services')

    def test_scan_exit_codes(self):
        from radar import scan as scan_module
        for status, expected in (('complete', 0), ('partial', 2), ('failed', 1)):
            summary = {'status': status, 'attention': ['Shine'] if status == 'partial' else [], 'mode': 'full',
                       'attempted': 3, 'requested': 3, 'completed': 2, 'new': 1, 'unmatched': [], 'not_attempted': []}
            with mock.patch.object(scan_module, 'run_scan', return_value=summary) as run, \
                    mock.patch.object(scan_module, 'setup_console_logging'):
                code, output = self.invoke('scan', '--minutes', '5')
            self.assertEqual(code, expected, status)
            self.assertEqual(run.call_args.kwargs, {'minutes': 5, 'only': None, 'mode': 'full'})
            self.assertEqual('Shine' in output, status == 'partial')
        self.assertFalse((self.data / scan_module.LOCK_NAME).exists())

    def test_scan_refuses_to_overlap_another_scan(self):
        from radar import scan as scan_module
        with scan_module.scan_lock(self.data), mock.patch.object(scan_module, 'run_scan') as run, \
                mock.patch.object(scan_module, 'setup_console_logging'):
            code, output = self.invoke('scan')
        self.assertEqual(code, 1)
        self.assertIn('already running', output)
        run.assert_not_called()

    def test_a_command_is_required(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.cli.main([])


class LauncherFilesTest(unittest.TestCase):
    def read(self, name):
        raw = (PROJECT / name).read_bytes()
        return raw, raw.decode('ascii')                                # raises if not pure ASCII

    def test_cmd_files(self):
        for name, command in (('START.cmd', 'radar.py serve'), ('SCAN.cmd', 'radar.py scan')):
            raw, text = self.read(name)
            self.assertIn(command, text)
            self.assertIn('-B', text)
            self.assertIn('cd /d "%~dp0"', text)
            self.assertEqual(raw.count(b'\n'), raw.count(b'\r\n'), name)   # CRLF throughout
        self.assertIn('pause', self.read('SCAN.cmd')[1])

    def test_schedule_script(self):
        _, text = self.read('setup_schedule.ps1')
        for needle in ('PegaRadarDailyScan', "'07:30'", '$SecondTime', '[switch]$Remove', '-B radar.py scan',
                       'New-TimeSpan -Hours 2', '-MultipleInstances IgnoreNew', '-StartWhenAvailable',
                       '-LogonType Interactive', '-WorkingDirectory $ProjectDir', 'Unregister-ScheduledTask'):
            self.assertIn(needle, text)


# ───────────────────────────── v2: registry and targets ─────────────────────────────

V2_COMPANIES = [
    {'name': 'Acme', 'aliases': ['Acme Corp'], 'type': 'product', 'bengaluru': True, 'linkedin_query': True,
     'career_url': 'https://careers.acme.test', 'parent': 'Acme Holdings',
     'portals': [{'kind': 'workday', 'tenant': 'acme', 'datacentre': 'wd503', 'site': 'Careers', 'state': 'verified',
                  'scope': 'india'}]},
    {'name': 'Booking.com', 'type': 'product', 'bengaluru': True,
     'portals': [{'kind': 'icims', 'host': 'jobs.booking.test', 'state': 'candidate', 'scope': 'global', 'note': 'research'}]},
    {'name': 'Legacy Bank', 'type': 'gcc', 'ats': {'kind': 'greenhouse', 'board': 'legacybank'}},
    {'name': 'Toyota', 'type': 'gcc', 'bengaluru': None,
     'portals': [{'kind': 'workday', 'tenant': 'tmna', 'state': 'wrong_scope', 'scope': 'global', 'note': 'TMNA is US only'}]},
    {'name': 'HDFC Bank', 'type': 'enterprise',
     'portals': [{'kind': 'ripplehire', 'state': 'unsupported', 'scope': 'unknown', 'note': 'needs a browser session'}],
     'inventory_note': 'RippleHire front end'},
    {'name': 'Nothing Configured', 'type': 'gcc'},
]
V2_TARGETS = {'rows': [
    {'row': 1, 'original_name': 'ACME Corporation', 'original_url': 'https://acme.test', 'employer': 'Acme',
     'resolution': 'matched', 'note': 'naming variant'},
    {'row': 2, 'original_name': 'Acme India', 'employer': 'Acme', 'resolution': 'related', 'note': 'business unit'},
    {'row': 3, 'original_name': 'Booking', 'employer': 'Booking.com', 'resolution': 'added'},
    {'row': 4, 'original_name': 'Mystery Systems', 'original_url': 'https://mystery.test/careers', 'employer': None,
     'resolution': 'unresolved', 'note': 'two companies share this name'},
    {'row': 5, 'original_name': 'Ghost Ltd', 'employer': 'Ghost', 'resolution': 'matched'},
    {'row': 6, 'original_name': 'Toyota Motor', 'employer': 'Toyota', 'resolution': 'matched'},
]}


def v2_registry():
    return rank.Registry(V2_COMPANIES)


# The task names radar.sources builds for the scannable portals above, whatever its naming scheme.
V2_TASKS = {employer: names[0] for employer, names in scan.portal_tasks(v2_registry()).items()}


def v2_targets(folder):
    path = Path(folder) / 'targets.json'
    path.write_text(json.dumps(V2_TARGETS), encoding='utf-8')
    return rank.load_targets(path)


class RegistryV2Test(unittest.TestCase):
    def test_employers_have_a_uniform_shape(self):
        employers = {employer['name']: employer for employer in v2_registry().employers}
        self.assertEqual(set(employers['Acme']), {'name', 'aliases', 'type', 'bengaluru', 'linkedin_query', 'parent',
                                                  'career_url', 'portals', 'inventory_note', 'current_employer'})
        acme = employers['Acme']
        self.assertEqual((acme['parent'], acme['career_url'], acme['linkedin_query'], acme['bengaluru']),
                         ('Acme Holdings', 'https://careers.acme.test', True, True))
        self.assertEqual(acme['portals'][0]['datacentre'], 'wd503')           # any Workday datacentre is kept as given
        bare = employers['Nothing Configured']
        self.assertEqual((bare['portals'], bare['parent'], bare['career_url'], bare['bengaluru'], bare['linkedin_query']),
                         ([], None, None, None, False))

    def test_a_legacy_ats_block_becomes_one_verified_portal(self):
        legacy = next(employer for employer in v2_registry().employers if employer['name'] == 'Legacy Bank')
        self.assertEqual(legacy['portals'], [{'kind': 'greenhouse', 'board': 'legacybank', 'state': 'verified',
                                              'scope': 'unknown'}])
        both = rank.employer_portals({'name': 'X', 'ats': {'kind': 'lever', 'board': 'old'},
                                      'portals': [{'kind': 'ashby', 'board': 'new', 'state': 'candidate', 'scope': 'india'}]})
        self.assertEqual([portal['kind'] for portal in both], ['ashby'])       # portals replaces ats

    def test_an_unknown_state_is_never_trusted_as_verified(self):
        portals = rank.employer_portals({'name': 'X', 'portals': [{'kind': 'lever', 'board': 'x', 'state': 'trusted'},
                                                                  'junk', {'kind': 'ashby', 'scope': 'mars'}]})
        self.assertEqual([(portal['kind'], portal['state'], portal['scope']) for portal in portals],
                         [('lever', 'candidate', 'unknown'), ('ashby', 'candidate', 'unknown')])

    def test_load_targets(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(rank.load_targets(Path(folder) / 'missing.json'), [])   # an empty inventory, not a crash
            targets = v2_targets(folder)
            self.assertEqual(len(targets), 6)
            self.assertEqual(targets[0], {'row': 1, 'original_name': 'ACME Corporation', 'original_url': 'https://acme.test',
                                          'employer': 'Acme', 'resolution': 'matched', 'note': 'naming variant'})
            self.assertEqual((targets[3]['employer'], targets[3]['resolution']), (None, 'unresolved'))
            path = Path(folder) / 'targets.json'
            for text in ('', '{broken', '[]', '{"rows": null}'):
                path.write_text(text, encoding='utf-8')
                self.assertEqual(rank.load_targets(path), [], text)
            path.write_text(json.dumps({'rows': [{'original_name': 'A', 'resolution': 'guessed'}, {'row': 2}, 'junk']}),
                            encoding='utf-8')
            self.assertEqual(rank.load_targets(path), [{'row': None, 'original_name': 'A', 'original_url': None,
                                                       'employer': None, 'resolution': 'unresolved', 'note': None}])


# ───────────────────────────── v2: store ─────────────────────────────

V1_SCHEMA = """
CREATE TABLE jobs(
    id TEXT PRIMARY KEY, title TEXT NOT NULL, company TEXT NOT NULL DEFAULT '', company_key TEXT NOT NULL DEFAULT '',
    employer_type TEXT NOT NULL DEFAULT 'unknown', city TEXT NOT NULL DEFAULT '', cities_json TEXT NOT NULL DEFAULT '[]',
    location TEXT NOT NULL DEFAULT '', is_bengaluru INTEGER NOT NULL DEFAULT 0,
    url TEXT NOT NULL DEFAULT '', apply_url TEXT, description TEXT NOT NULL DEFAULT '',
    experience_min REAL, experience_max REAL, salary_min_lpa REAL, salary_max_lpa REAL,
    posted_at TEXT, requisition_id TEXT, first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
    first_run_id TEXT, last_run_id TEXT, score INTEGER NOT NULL DEFAULT 0, fit_json TEXT NOT NULL DEFAULT '{}',
    pega_title INTEGER NOT NULL DEFAULT 0, pega_duty INTEGER NOT NULL DEFAULT 0);
CREATE TABLE sightings(
    source TEXT NOT NULL, source_id TEXT NOT NULL, job_id TEXT NOT NULL, url TEXT NOT NULL DEFAULT '',
    label TEXT NOT NULL DEFAULT '', first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
    PRIMARY KEY(source, source_id));
CREATE TABLE user_state(
    job_id TEXT PRIMARY KEY, saved INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'new',
    notes TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL, hidden INTEGER NOT NULL DEFAULT 0, seen_at TEXT);
CREATE TABLE runs(id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL, summary_json TEXT);
CREATE TABLE source_health(
    run_id TEXT NOT NULL, source TEXT, label TEXT, kind TEXT, status TEXT, found INTEGER, kept INTEGER,
    requests INTEGER, error TEXT);
CREATE TABLE kv(key TEXT PRIMARY KEY, value_json TEXT NOT NULL);
INSERT INTO jobs(id, title, company, company_key, city, cities_json, location, is_bengaluru, url, description,
                 first_seen_at, last_seen_at, first_run_id, last_run_id, score)
    VALUES ('job1', 'Pega Developer', 'Acme', 'acme', 'Bengaluru', '["Bengaluru"]', 'Bengaluru', 1,
            'https://careers.acme.test/1', 'Build Pega applications.', '2026-11-14T02:00:00+00:00',
            '2026-11-14T02:00:00+00:00', 'run-old', 'run-old', 77),
           ('job2', 'Pega Architect', 'Globex', 'globex', 'Pune', '["Pune"]', 'Pune', 0, 'https://x.test/2', '',
            '2026-11-14T02:00:00+00:00', '2026-11-14T02:00:00+00:00', 'run-old', 'run-old', 40);
INSERT INTO sightings VALUES ('Employer site', 'R1', 'job1', 'https://careers.acme.test/1', 'Acme',
                              '2026-11-14T02:00:00+00:00', '2026-11-14T02:00:00+00:00'),
                             ('LinkedIn', '42', 'job1', 'https://www.linkedin.com/jobs/view/42', 'LinkedIn',
                              '2026-11-14T02:00:00+00:00', '2026-11-14T02:00:00+00:00');
INSERT INTO user_state VALUES ('job1', 1, 'applied', 'Spoke to the recruiter on Friday.', '2026-11-14T03:00:00+00:00', 0,
                               '2026-11-14T03:00:00+00:00'),
                              ('job2', 0, 'new', '', '2026-11-14T03:00:00+00:00', 1, NULL);
INSERT INTO runs VALUES ('run-old', '2026-11-14T01:30:00+00:00', '2026-11-14T02:05:00+00:00', 'partial', '{"new": 2}');
INSERT INTO source_health VALUES ('run-old', 'Employer site', 'Acme', 'ats', 'ok', 12, 1, 3, NULL),
                                 ('run-old', 'Shine', 'Shine', 'board', 'blocked', 0, 0, 1, 'HTTP 403');
INSERT INTO kv VALUES ('linkedin_checkpoint', '{"done": ["pega|Bengaluru"]}');
"""


class MigrationTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.data = Path(folder.name) / 'data'
        self.data.mkdir()
        self.path = self.data / 'radar.sqlite3'

    def v1_database(self):
        db = sqlite3.connect(self.path)
        db.executescript(V1_SCHEMA)
        db.close()

    def backups(self):
        return sorted(path.name for path in (self.data / 'backups').glob('radar-*.sqlite3')) \
            if (self.data / 'backups').exists() else []

    def test_a_new_database_needs_no_backup(self):
        Store(self.path)
        Store(self.path)
        self.assertEqual(self.backups(), [])

    def test_a_v1_database_is_backed_up_then_migrated_with_everything_intact(self):
        self.v1_database()
        store = Store(self.path)
        self.assertEqual(len(self.backups()), 1)
        self.assertRegex(self.backups()[0], r'^radar-\d{8}T\d{6}Z\.sqlite3$')
        backup = sqlite3.connect(self.data / 'backups' / self.backups()[0])
        self.assertEqual(backup.execute('SELECT COUNT(*) FROM jobs').fetchone()[0], 2)        # the copy is the old data
        self.assertNotIn('possibly_closed', {row[1] for row in backup.execute('PRAGMA table_info(jobs)')})
        backup.close()

        job = store.job('job1')
        self.assertEqual((job['title'], job['company'], job['score'], job['description'], job['is_bengaluru']),
                         ('Pega Developer', 'Acme', 77, 'Build Pega applications.', True))
        self.assertEqual((job['saved'], job['status'], job['notes'], job['seen']),
                         (True, 'applied', 'Spoke to the recruiter on Friday.', True))
        self.assertEqual((job['possibly_closed'], job['last_confirmed_at']), (False, None))
        self.assertEqual([sighting['source'] for sighting in job['sightings']], ['Employer site', 'LinkedIn'])
        self.assertTrue(store.job('job2')['hidden'])
        self.assertEqual(store.kv_get('linkedin_checkpoint'), {'done': ['pega|Bengaluru']})
        run = store.latest_run()
        self.assertEqual((run['id'], run['summary'], len(run['health'])), ('run-old', {'new': 2}, 2))
        self.assertEqual((run['health'][0]['reason'], run['health'][0]['task'], run['health'][0]['pages_complete']),
                         ('', None, None))
        self.assertEqual(store.known_ids('LinkedIn'), {'42'})

        # The identity links still work: the same sighting updates the same job, with its state untouched.
        saved = store.save_result(store.start_run(), model.make_result(
            'LinkedIn', 'LinkedIn', 'linkedin', jobs=[model.make_job('LinkedIn', '42', 'Pega Developer', 'Acme', 'u',
                                                                     'Bengaluru')]), plain_ranker)
        self.assertEqual(saved['updated'], ['job1'])
        self.assertEqual(store.job('job1')['notes'], 'Spoke to the recruiter on Friday.')

    def test_migration_is_repeatable(self):
        self.v1_database()
        Store(self.path)
        Store(self.path)
        Store(self.path)
        self.assertEqual(len(self.backups()), 1)                             # nothing left to migrate, so no new copy
        db = sqlite3.connect(self.path)
        columns = [row[1] for row in db.execute('PRAGMA table_info(source_health)')]
        db.close()
        self.assertEqual(len(columns), len(set(columns)))
        for column in ('elapsed_s', 'reason', 'pages_complete', 'details_complete', 'employer'):
            self.assertIn(column, columns)

    def test_a_half_migrated_database_is_finished(self):
        self.v1_database()
        db = sqlite3.connect(self.path)
        db.execute('ALTER TABLE jobs ADD COLUMN last_confirmed_at TEXT')
        db.execute("ALTER TABLE source_health ADD COLUMN reason TEXT NOT NULL DEFAULT ''")
        db.close()
        store = Store(self.path)
        self.assertFalse(store.job('job1')['possibly_closed'])
        self.assertEqual(len(self.backups()), 1)

    def test_only_the_five_newest_backups_are_kept(self):
        store = Store(self.path)
        folder = self.data / 'backups'
        folder.mkdir()
        for day in range(1, 8):
            (folder / f'radar-2026010{day}T000000Z.sqlite3').write_bytes(b'old')
        (folder / 'companies-20260101T000000Z.json').write_text('{}', encoding='utf-8')
        made = store.backup()
        names = self.backups()
        self.assertEqual(len(names), 5)
        self.assertIn(made.name, names)
        self.assertNotIn('radar-20260101T000000Z.sqlite3', names)
        self.assertTrue((folder / 'companies-20260101T000000Z.json').exists())   # other backups are not touched
        again = store.backup()                                               # the same second gets its own file
        self.assertNotEqual(again.name, made.name)


class ClosureTest(StoreCase):
    def board(self, *ids, task='ats:workday:acme', status='ok', pages_complete=True, label='Acme', run_id=None, **extra):
        jobs = [self.employer(source_id, title=f'Pega Developer {source_id}') for source_id in ids]
        if not ids and status == 'ok':
            status = 'empty'
        result = model.make_result(model.EMPLOYER_SOURCE, label, 'ats', status=status, jobs=jobs,
                                   pages_complete=pages_complete, employer=label, **extra)
        result['task'] = task
        return self.store.save_result(run_id or self.run_id, result, plain_ranker)

    def state(self, job_id):
        job = self.store.job(job_id)
        return job['possibly_closed'], job['last_confirmed_at'] is not None

    def test_a_complete_run_confirms_what_it_lists_and_flags_what_it_dropped(self):
        first, second = self.board('1', '2')['new']
        self.assertEqual((self.state(first), self.state(second)), ((False, True), (False, True)))
        self.board('1')                                                    # a complete read no longer lists 2
        self.assertEqual((self.state(first), self.state(second)), ((False, True), (True, True)))
        self.assertEqual(self.store.jobs()[1], 2)                          # flagged, never deleted
        rows = {row['id']: row for row in self.store.jobs()[0]}
        self.assertTrue(rows[second]['possibly_closed'])
        self.assertIn('last_confirmed_at', rows[second])
        self.board('1', '2')                                               # listed again: cleared
        self.assertEqual(self.state(second), (False, True))

    def test_an_empty_complete_run_flags_everything_it_used_to_list(self):
        ids = self.board('1', '2')['new']
        self.board()
        self.assertEqual([self.state(job_id)[0] for job_id in ids], [True, True])

    def test_a_mass_drop_is_only_believed_on_a_second_complete_read(self):
        ids = self.board('1', '2', '3', '4', '5', '6')['new']
        first = self.board('1', '2')                                       # 4 of 6 vanish in one read
        self.assertEqual(first['note'], 'listing dropped 4 of 6 jobs at once; not treated as closures')
        self.assertEqual([self.state(job_id)[0] for job_id in ids], [False] * 6)
        self.store.finish_run(self.run_id, 'complete', {})
        health = self.store.latest_run()['health'][-1]
        self.assertEqual((health['status'], health['error']),
                         ('ok', 'listing dropped 4 of 6 jobs at once; not treated as closures'))
        second = self.board('1', '2')                                      # the next complete read still lacks them
        self.assertEqual(second['note'], '4 closures confirmed on a second complete read')
        self.assertEqual([self.state(job_id)[0] for job_id in ids], [False, False, True, True, True, True])
        self.assertNotIn('note', self.board('1', '2'))                     # nothing further to say

    def test_a_mass_drop_that_comes_back_flags_nothing(self):
        ids = self.board('1', '2', '3', '4', '5', '6')['new']
        self.assertIn('dropped 4 of 6', self.board('1', '2')['note'])
        self.assertNotIn('note', self.board('1', '2', '3', '4', '5', '6'))   # the site recovered: all six are back
        self.assertEqual([self.state(job_id)[0] for job_id in ids], [False] * 6)
        self.assertIn('dropped 4 of 6', self.board('1', '2')['note'])      # a new drop starts from scratch
        self.assertEqual([self.state(job_id)[0] for job_id in ids], [False] * 6)

    def test_an_incomplete_read_between_does_not_confirm_a_mass_drop(self):
        ids = self.board('1', '2', '3', '4', '5', '6')['new']
        self.board('1', '2')
        self.board('1', status='partial')                                  # proves nothing either way
        self.board(status='error', reason='timeout')
        self.assertEqual([self.state(job_id)[0] for job_id in ids], [False] * 6)
        self.assertIn('4 closures confirmed', self.board('1', '2')['note'])

    def test_a_growing_mass_drop_confirms_the_old_part_and_suspects_the_new(self):
        ids = self.board('1', '2', '3', '4', '5', '6', '7', '8')['new']
        self.assertIn('dropped 5 of 8', self.board('1', '2', '3')['note'])
        saved = self.board()                                               # now everything is gone
        self.assertEqual(saved['note'], 'listing dropped 3 of 8 jobs at once; not treated as closures; '
                                        '5 closures confirmed on a second complete read')
        self.assertEqual([self.state(job_id)[0] for job_id in ids], [False] * 3 + [True] * 5)
        self.assertNotIn('dropped', self.board()['note'])                  # and the last three on the read after that
        self.assertEqual([self.state(job_id)[0] for job_id in ids], [True] * 8)

    def test_exactly_half_or_fewer_than_three_is_believed(self):
        ids = self.board('1', '2', '3', '4')['new']
        self.assertNotIn('note', self.board('1', '2'))                     # 2 of 4: under the minimum of three
        self.assertEqual([self.state(job_id)[0] for job_id in ids], [False, False, True, True])
        more = self.board('1', '2', '5', '6', '7', '8')['new']
        self.assertNotIn('note', self.board('1', '2', '5'))                # 3 of 6: half, not more than half
        self.assertEqual([self.state(job_id)[0] for job_id in more], [False, True, True, True])

    def test_incomplete_or_failed_runs_never_flag(self):
        job_id = self.board('1', '2')['new'][1]
        for outcome in ({'status': 'partial'}, {'status': 'error', 'reason': 'timeout'}, {'status': 'blocked'},
                        {'status': 'maintenance'}, {'status': 'ok', 'pages_complete': False},
                        {'status': 'ok', 'pages_complete': None}, {'status': 'empty', 'pages_complete': None}):
            ids = () if outcome['status'] != 'ok' else ('1',)
            self.board(*ids, **outcome)
            self.assertFalse(self.state(job_id)[0], outcome)

    def test_a_run_that_did_not_read_every_page_does_not_confirm(self):
        job_id = self.board('1', pages_complete=None)['new'][0]
        self.assertEqual(self.state(job_id), (False, False))
        self.board('1', status='partial')
        self.assertEqual(self.state(job_id), (False, False))

    def test_only_the_task_that_listed_a_job_can_drop_it(self):
        mine = self.board('1')['new'][0]
        other = self.store.save_result(self.run_id, {**model.make_result(
            model.EMPLOYER_SOURCE, 'Globex', 'ats', jobs=[self.employer('g1', company='Globex')], pages_complete=True),
            'task': 'ats:lever:globex'}, plain_ranker)['new'][0]
        self.board('1')
        self.assertFalse(self.state(other)[0])                             # Acme's board says nothing about Globex
        self.board(task='ats:lever:globex', label='Globex')
        self.assertEqual((self.state(mine)[0], self.state(other)[0]), (False, True))

    def test_a_job_on_two_boards_is_flagged_only_when_both_drop_it(self):
        job_id = self.board('1')['new'][0]
        board = model.make_result('Hirist', 'Hirist', 'board', pages_complete=True, jobs=[
            model.make_job('Hirist', 'h1', 'Pega Developer 1', 'Acme', 'https://hirist.test/h1', 'Bengaluru')])
        board['task'] = 'board:hirist'
        self.assertEqual(self.store.save_result(self.run_id, board, plain_ranker)['updated'], [job_id])
        self.board()                                                       # the employer site drops it
        self.assertFalse(self.state(job_id)[0])                            # Hirist still lists it
        gone = model.make_result('Hirist', 'Hirist', 'board', status='empty', pages_complete=True)
        gone['task'] = 'board:hirist'
        self.store.save_result(self.run_id, gone, plain_ranker)
        self.assertTrue(self.state(job_id)[0])

    def test_linkedin_neither_proves_absence_nor_is_ignored_when_it_still_lists_the_job(self):
        job_id = self.board('1')['new'][0]
        card = model.make_result('LinkedIn', 'LinkedIn', 'linkedin', pages_complete=True,
                                 jobs=[self.linkedin('77', title='Pega Developer 1')])
        card['task'] = 'linkedin'
        self.assertEqual(self.store.save_result(self.run_id, card, plain_ranker)['updated'], [job_id])
        quiet = model.make_result('LinkedIn', 'LinkedIn', 'linkedin', status='empty', pages_complete=True)
        quiet['task'] = 'linkedin'
        self.store.save_result(self.run_id, quiet, plain_ranker)           # a time-windowed search proves nothing
        self.assertFalse(self.state(job_id)[0])
        with mock.patch('radar.store.now_iso', return_value='2099-01-01T00:00:00+00:00'):
            self.board()                                                   # the employer site drops it
        self.assertTrue(self.state(job_id)[0])
        with mock.patch('radar.store.now_iso', return_value='2099-01-02T00:00:00+00:00'):
            self.store.save_result(self.run_id, card, plain_ranker)        # LinkedIn lists it after that: open again
        self.assertFalse(self.state(job_id)[0])

    def test_sightings_from_before_tasks_were_recorded_are_never_flagged(self):
        legacy = self.save(self.employer('old'), source=model.EMPLOYER_SOURCE, label='Acme', kind='ats')['new'][0]
        self.board()
        self.assertFalse(self.state(legacy)[0])

    def test_user_state_and_export_survive_a_closure(self):
        job_id = self.board('1')['new'][0]
        self.store.set_state(job_id, status='applied', notes='sent CV')
        self.board()
        job = self.store.job(job_id)
        self.assertEqual((job['possibly_closed'], job['status'], job['notes']), (True, 'applied', 'sent CV'))
        exported = self.store.export_rows()[0]
        self.assertEqual((exported['possibly_closed'], exported['last_confirmed_at'] is not None), (True, True))


class HealthAndHistoryTest(StoreCase):
    def test_health_rows_carry_the_new_columns(self):
        result = model.make_result(model.EMPLOYER_SOURCE, 'Acme', 'ats', status='partial', reason='timeout', elapsed_s=41.26,
                                   pages_complete=False, details_complete=True, employer='Acme', error='page 3 timed out')
        result['task'] = 'ats:workday:acme'
        self.store.save_result(self.run_id, result, plain_ranker)
        self.store.record_health(self.run_id, {'source': model.EMPLOYER_SOURCE, 'label': 'Acme India', 'kind': 'ats',
                                               'status': 'partial', 'found': 9, 'kept': 2, 'reason': 'timeout',
                                               'employer': 'Acme India', 'task': 'ats:workday:acme-india'})
        self.store.finish_run(self.run_id, 'partial', {})
        first, second = self.store.latest_run()['health']
        self.assertEqual((first['reason'], first['elapsed_s'], first['pages_complete'], first['details_complete'],
                          first['employer'], first['task']), ('timeout', 41.3, False, True, 'Acme', 'ats:workday:acme'))
        self.assertIsNotNone(first['at'])
        self.assertEqual((second['label'], second['kept'], second['found'], second['requests'], second['pages_complete']),
                         ('Acme India', 2, 9, 0, None))
        self.assertEqual(self.store.jobs()[1], 0)                          # record_health touches no job

    def test_task_history_is_the_latest_row_per_task(self):
        def outcome(task, status, run_id):
            result = model.make_result('Hirist', task, 'board', status=status)
            result['task'] = task
            self.store.save_result(run_id, result, plain_ranker)
        outcome('board:a', 'error', self.run_id)
        outcome('board:b', 'empty', self.run_id)
        second = self.store.start_run()
        outcome('board:a', 'empty', second)
        self.store.save_result(second, model.make_result('Old', 'Old', 'board'), plain_ranker)   # no task name
        history = self.store.task_history()
        self.assertEqual(set(history), {'board:a', 'board:b'})
        self.assertEqual((history['board:a']['status'], history['board:a']['run_id']), ('empty', second))
        self.assertEqual(history['board:b']['run_id'], self.run_id)
        self.assertTrue(history['board:a']['run_started_at'])
        self.assertEqual(history['board:a']['run_seq'], history['board:b']['run_seq'] + 1)   # runs are numbered in order

    def test_latest_coverage_run_merges_later_narrow_runs_into_the_last_full_one(self):
        def outcome(task, status, run_id, **extra):
            result = model.make_result('Hirist', task, 'board', status=status, **extra)
            result['task'] = task
            self.store.save_result(run_id, result, plain_ranker)
        self.assertIsNone(self.store.latest_coverage_run())
        for task, status in (('board:a', 'empty'), ('board:b', 'blocked'), ('board:c', 'error')):
            outcome(task, status, self.run_id)
        self.store.finish_run(self.run_id, 'partial', {'mode': 'full', 'requested': 3})
        retry = self.store.start_run()
        outcome('board:b', 'empty', retry)
        outcome('board:c', 'error', retry, reason='budget')                # cut off again: keeps its real outcome
        with mock.patch('radar.store.now_iso', return_value='2099-01-01T00:00:00+00:00'):
            self.store.finish_run(retry, 'partial', {'mode': 'retry', 'requested': 2})
        failed = self.store.start_run()
        outcome('board:a', 'error', failed)
        with mock.patch('radar.store.now_iso', return_value='2099-01-02T00:00:00+00:00'):
            self.store.finish_run(failed, 'failed', {'mode': 'full', 'error': 'boom'})

        self.assertEqual((self.store.latest_run()['id'], len(self.store.latest_run()['health'])), (retry, 2))   # the narrow run
        run = self.store.latest_coverage_run()
        self.assertEqual((run['id'], run['summary'], run['later_runs'], run['last_attempt']['status']),
                         (self.run_id, {'mode': 'full', 'requested': 3}, [retry], 'failed'))
        self.assertEqual({row['task']: (row['status'], row['reason'], row['run_id']) for row in run['health']},
                         {'board:a': ('empty', '', self.run_id), 'board:b': ('empty', '', retry),
                          'board:c': ('error', '', self.run_id)})

    def test_latest_coverage_run_without_a_full_run(self):
        result = model.make_result('Hirist', 'Hirist', 'board', status='empty')
        result['task'] = 'board:hirist'
        self.store.save_result(self.run_id, result, plain_ranker)
        self.store.finish_run(self.run_id, 'complete', {'mode': 'only'})
        run = self.store.latest_coverage_run()
        self.assertEqual((run['id'], run['later_runs'], [row['task'] for row in run['health']]),
                         (self.run_id, [], ['board:hirist']))

    def test_latest_full_run_seq(self):
        # Every run here starts and finishes within the same second: the order still has to be exact.
        self.assertIsNone(self.store.latest_full_run_seq())
        self.store.finish_run(self.run_id, 'complete', {'mode': 'full'})
        first = self.store.latest_full_run_seq()
        self.store.finish_run(self.store.start_run(), 'partial', {'mode': 'retry'})
        self.store.finish_run(self.store.start_run(), 'failed', {'mode': 'full'})
        self.store.start_run()                                             # still running
        self.assertEqual(self.store.latest_full_run_seq(), first)          # retry, failed and unfinished runs do not count
        self.store.finish_run(self.store.start_run(), 'partial', {})       # a summary without a mode is a full scan
        self.assertEqual(self.store.latest_full_run_seq(), first + 4)


class CoverageTest(StoreCase):
    def setUp(self):
        super().setUp()
        self.registry = v2_registry()
        self.targets = v2_targets(self.folder)

    def attempt(self, employer, status='ok', task=None, run_id=None, jobs=(), **extra):
        result = model.make_result(model.EMPLOYER_SOURCE, employer, 'ats', status=status, jobs=jobs, employer=employer,
                                   **extra)
        result['task'] = task or V2_TASKS[employer]
        ranker = rank.make_ranker(model.load_config(), self.registry, today=TODAY)
        return self.store.save_result(run_id or self.run_id, result, ranker)

    def rows(self):
        return {row['canonical'] or 'target: ' + row['original_names'][0]: row
                for row in self.store.coverage(self.registry, self.targets)}

    def test_every_employer_and_every_unresolved_target_has_a_row(self):
        rows = self.rows()
        self.assertEqual(set(rows), {'Acme', 'Booking.com', 'Legacy Bank', 'Toyota', 'HDFC Bank', 'Nothing Configured',
                                     'target: Mystery Systems', 'target: Ghost Ltd'})
        for row in rows.values():
            self.assertEqual(tuple(row), radar_store.COVERAGE_COLUMNS)
            self.assertTrue(row['next_action'])

    def test_identity_configuration_and_inventory_states(self):
        rows = self.rows()
        acme = rows['Acme']
        self.assertEqual((acme['original_names'], acme['original_rows'], acme['type'], acme['bengaluru'], acme['parent'],
                          acme['career_url'], acme['linkedin_query']),
                         (['ACME Corporation', 'Acme India'], [1, 2], 'product', True, 'Acme Holdings',
                          'https://careers.acme.test', True))
        self.assertEqual(acme['portals'], [{'kind': 'workday', 'state': 'verified', 'scope': 'india', 'note': None,
                                            'business_unit': None}])
        self.assertEqual({name: row['inventory_state'] for name, row in rows.items()}, {
            'Acme': 'configured', 'Booking.com': 'configured', 'Legacy Bank': 'configured',
            'Toyota': 'wrong scope only', 'HDFC Bank': 'unsupported', 'Nothing Configured': 'not configured',
            'target: Mystery Systems': 'identity unresolved', 'target: Ghost Ltd': 'identity unresolved'})
        self.assertEqual((rows['Booking.com']['unverified'], rows['Acme']['unverified']), (True, False))
        unresolved = rows['target: Mystery Systems']
        self.assertEqual((unresolved['canonical'], unresolved['career_url'], unresolved['inventory_note'], unresolved['portals']),
                         (None, 'https://mystery.test/careers', 'two companies share this name', []))
        self.assertIn("'Ghost' is not in companies.json", rows['target: Ghost Ltd']['inventory_note'])
        self.assertEqual(rows['HDFC Bank']['inventory_note'], 'RippleHire front end')

    def test_the_task_names_come_from_the_portals_configured_today(self):
        self.assertEqual(sorted(V2_TASKS), ['Acme', 'Booking.com', 'Legacy Bank'])   # only scannable portals get a task
        self.assertEqual(len(set(V2_TASKS.values())), 3)
        self.assertEqual(scan.portal_tasks(rank.Registry()), {})

    def test_nothing_unattempted_is_ever_shown_as_empty(self):
        for name, row in self.rows().items():
            self.assertIsNone(row['latest_status'], name)
            self.assertIsNone(row['last_attempt_at'])
            self.assertEqual((row['jobs_total'], row['jobs_on_file'], row['jobs_open']), (0, 0, 0))
            self.assertEqual([source['task'] for source in row['sources']], [V2_TASKS[name]] if name in V2_TASKS else [])
            self.assertTrue(all(source['status'] is None for source in row['sources']))
        self.attempt('Acme', status='empty', pages_complete=True)
        rows = self.rows()
        self.assertEqual(rows['Acme']['latest_status'], 'empty')            # attempted and really empty
        for name in ('Booking.com', 'Toyota', 'HDFC Bank', 'Nothing Configured', 'target: Mystery Systems'):
            self.assertIsNone(rows[name]['latest_status'], name)

    def test_latest_outcome_success_time_and_completeness(self):
        self.attempt('Acme', jobs=[self.employer('1'), self.employer('2', title='Pega Lead')], pages_complete=True,
                     details_complete=True)
        first = self.rows()['Acme']
        self.assertEqual((first['latest_status'], first['latest_reason'], first['pages_complete'], first['details_complete'],
                          first['jobs_total'], first['jobs_open'], first['run_id']), ('ok', None, True, True, 2, 2, self.run_id))
        self.assertEqual(first['last_success_at'], first['last_attempt_at'])
        second_run = self.store.start_run()
        with mock.patch('radar.store.now_iso', return_value='2099-01-01T00:00:00+00:00'):
            self.attempt('Acme', status='partial', reason='timeout', error='page 2 timed out', pages_complete=False,
                         run_id=second_run)
        row = self.rows()['Acme']
        self.assertEqual((row['latest_status'], row['latest_reason'], row['latest_error'], row['pages_complete'],
                          row['run_id'], row['last_attempt_at']),
                         ('partial', 'timeout', 'page 2 timed out', False, second_run, '2099-01-01T00:00:00+00:00'))
        self.assertEqual(row['last_success_at'], first['last_success_at'])  # the earlier success is still remembered
        self.assertEqual(row['sources'], [{'task': V2_TASKS['Acme'], 'status': 'partial', 'reason': 'timeout',
                                           'at': '2099-01-01T00:00:00+00:00', 'run_id': second_run}])

    def test_several_portals_are_summarised_by_the_worst_latest_outcome(self):
        tasks = {'Acme': ['ats:workday:acme', 'ats:icims:acme']}
        self.attempt('Acme', task='ats:workday:acme', pages_complete=True, jobs=[self.employer('1')])
        row = {item['canonical']: item for item in self.store.coverage(self.registry, self.targets, tasks)}['Acme']
        # One board read, the other never tried: nothing is known about half of this employer.
        self.assertEqual((row['latest_status'], row['pages_complete'], [source['status'] for source in row['sources']]),
                         (None, None, ['ok', None]))
        self.assertIn('Not attempted yet', row['next_action'])
        self.assertIsNotNone(row['last_success_at'])
        self.attempt('Acme', task='ats:icims:acme', status='blocked', reason='refused', error='HTTP 403')
        row = {item['canonical']: item for item in self.store.coverage(self.registry, self.targets, tasks)}['Acme']
        self.assertEqual((row['latest_status'], row['latest_reason'], row['latest_error'], len(row['sources'])),
                         ('blocked', 'refused', 'HTTP 403', 2))
        self.attempt('Acme', task='ats:icims:acme', status='empty', pages_complete=True)
        row = {item['canonical']: item for item in self.store.coverage(self.registry, self.targets, tasks)}['Acme']
        self.assertEqual((row['latest_status'], row['pages_complete']), ('ok', True))

    def test_outcomes_of_portals_no_longer_configured_are_ignored(self):
        # 1. A corrected board: the old tenant's error must not stick to the employer.
        self.attempt('Acme', task='ats:workday:acme-old-tenant', status='error', reason='http_4xx', error='HTTP 404')
        # 2. An edited portal: the old board's success says nothing about the new one.
        self.attempt('Booking.com', task='ats:icims:old.booking.test', pages_complete=True)
        # 3. An employer whose portal was removed, and one that never had a scannable one.
        self.attempt('Nothing Configured', task='ats:lever:nothing', pages_complete=True)
        self.attempt('Toyota', task='ats:workday:tmna', pages_complete=True)
        self.store.save_result(self.run_id, model.make_result(model.EMPLOYER_SOURCE, 'Legacy Bank', 'ats', status='error',
                                                              error='HTTP 500'), plain_ranker)   # a v1 row, no task name
        rows = self.rows()
        for name in ('Acme', 'Booking.com', 'Legacy Bank', 'Nothing Configured', 'Toyota'):
            row = rows[name]
            self.assertEqual((row['latest_status'], row['last_attempt_at'], row['last_success_at'], row['run_id']),
                             (None, None, None, None), name)
        self.assertIn('Not attempted yet', rows['Acme']['next_action'])
        self.assertIn('Not attempted yet', rows['Booking.com']['next_action'])
        self.assertEqual(rows['Nothing Configured']['sources'], [])
        exported = {line['canonical']: line for line in csv.DictReader(io.StringIO(acceptance.coverage_csv(rows.values())))}
        self.assertEqual((exported['Nothing Configured']['latest_status'], exported['Toyota']['latest_status'],
                          exported['Booking.com']['latest_status']), ('', '', ''))
        summary = self.store.coverage_summary(list(rows.values()))
        self.assertEqual((summary['ok'], summary['error'], summary['never_attempted'], summary['attempted']), (0, 0, 3, 0))

    def test_a_source_the_budget_cut_off_is_not_reached_not_attempted(self):
        self.attempt('Acme', pages_complete=True)
        good = self.rows()['Acme']
        later = self.store.start_run()
        with mock.patch('radar.store.now_iso', return_value='2099-01-01T00:00:00+00:00'):
            self.attempt('Acme', status='error', reason='budget', error='not run: the time budget was used up', run_id=later)
            self.attempt('Booking.com', status='error', reason='budget', error='not run', run_id=later)
            self.store.finish_run(later, 'partial', {})
        rows = self.rows()
        acme, booking = rows['Acme'], rows['Booking.com']
        self.assertEqual((acme['latest_status'], acme['latest_reason']), ('not_reached', 'budget'))
        self.assertEqual((acme['last_attempt_at'], acme['run_id'], acme['last_success_at']),
                         (good['last_attempt_at'], self.run_id, good['last_success_at']))   # its last real attempt
        self.assertEqual((booking['latest_status'], booking['last_attempt_at'], booking['run_id']), ('not_reached', None, None))
        self.assertIn('time budget', booking['next_action'])
        summary = self.store.coverage_summary(list(rows.values()))
        self.assertEqual((summary['attempted'], summary['not_reached'], summary['error'], summary['ok'],
                          summary['never_attempted'], summary['run_id']), (0, 2, 0, 0, 1, later))

    def test_job_counts(self):
        ids = self.attempt('Acme', jobs=[self.employer(str(n), title=f'Pega Developer {n}') for n in range(5)],
                           pages_complete=True)['new']
        self.store.set_state(ids[0], hidden=True)
        self.store.set_state(ids[1], status='rejected')
        self.attempt('Acme', jobs=[self.employer(str(n), title=f'Pega Developer {n}') for n in (0, 1, 2, 3)],
                     pages_complete=True)                                    # posting 4 is gone: possibly closed
        row = self.rows()['Acme']
        self.assertEqual((row['jobs_total'], row['jobs_on_file'], row['jobs_open']), (5, 3, 2))
        old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(timespec='seconds')
        db = sqlite3.connect(self.store.path)
        db.execute('UPDATE jobs SET last_seen_at=? WHERE id=?', (old, ids[2]))
        db.commit()
        db.close()
        row = self.rows()['Acme']
        self.assertEqual((row['jobs_total'], row['jobs_on_file'], row['jobs_open']), (5, 3, 1))   # not listed for 30 days

    def test_reading_coverage_writes_nothing(self):
        self.attempt('Acme', pages_complete=True)
        self.store.finish_run(self.run_id, 'complete', {})

        def snapshot():
            db = sqlite3.connect(self.store.path)
            try:
                return {table: db.execute(f'SELECT * FROM {table} ORDER BY 1').fetchall()
                        for table in ('kv', 'jobs', 'sightings', 'source_health', 'runs', 'user_state')}
            finally:
                db.close()
        before = snapshot()
        rows = self.store.coverage(self.registry, self.targets)
        self.store.coverage_summary(rows)
        self.store.latest_coverage_run()
        self.assertEqual(snapshot(), before)
        self.assertEqual(before['kv'], [])

    def test_possibly_closed_jobs_are_not_counted_as_open(self):
        self.attempt('Acme', jobs=[self.employer('1'), self.employer('2', title='Pega Lead')], pages_complete=True)
        self.attempt('Acme', jobs=[self.employer('1')], pages_complete=True)
        row = self.rows()['Acme']
        self.assertEqual((row['jobs_total'], row['jobs_open']), (2, 1))

    def test_next_action_says_what_to_do(self):
        self.attempt('Acme', pages_complete=True)
        self.attempt('Booking.com', pages_complete=True)
        self.attempt('Legacy Bank', status='error', reason='tls', error='TLS certificate could not be verified')
        rows = self.rows()
        self.assertIn('Nothing to do', rows['Acme']['next_action'])
        self.assertIn('radar.py verify', rows['Booking.com']['next_action'])
        self.assertIn('certificate', rows['Legacy Bank']['next_action'])
        self.assertIn('TMNA is US only', rows['Toyota']['next_action'])
        self.assertIn('needs a browser session', rows['HDFC Bank']['next_action'])
        self.assertIn('No career portal is configured', rows['Nothing Configured']['next_action'])
        self.assertIn('two companies share this name', rows['target: Mystery Systems']['next_action'])
        self.attempt('Legacy Bank', status='error', reason='unreachable')
        self.assertIn('could not be reached; check the network or VPN', self.rows()['Legacy Bank']['next_action'])
        for reason in ('dns', 'timeout', 'refused', 'unreachable', 'rate_limited', 'http_4xx', 'http_5xx', 'shape', 'cap',
                       'maintenance'):
            self.attempt('Legacy Bank', status='error', reason=reason)
            self.assertNotIn('incomplete; run', self.rows()['Legacy Bank']['next_action'], reason)   # a specific sentence

    def test_summary_counts(self):
        self.attempt('Acme', pages_complete=True)
        self.attempt('Booking.com', status='partial', reason='cap')
        self.store.finish_run(self.run_id, 'partial', {})
        rows = self.store.coverage(self.registry, self.targets)
        summary = self.store.coverage_summary(rows)
        expected = {'original_rows': 6, 'employers': 6, 'configured': 3, 'attempted': 2, 'never_attempted': 1,
                    'not_reached': 0, 'ok': 1, 'partial': 1, 'blocked': 0, 'maintenance': 0, 'error': 0, 'unverified': 1,
                    'not_configured': 1, 'unsupported': 1, 'wrong_scope': 1, 'unresolved': 2, 'run_id': self.run_id}
        self.assertEqual({key: summary[key] for key in expected}, expected)
        self.assertEqual(set(summary), set(expected) | {'generated_at'})
        # Every configured employer is in exactly one outcome group.
        self.assertEqual(sum(summary[key] for key in ('ok', 'partial', 'blocked', 'maintenance', 'error', 'not_reached',
                                                      'never_attempted')), summary['configured'])
        # A later run that attempts only one employer: outcomes keep each employer's latest attempt.
        later = self.store.start_run()
        self.attempt('Legacy Bank', status='blocked', reason='refused', run_id=later)
        with mock.patch('radar.store.now_iso', return_value='2099-01-01T00:00:00+00:00'):
            self.store.finish_run(later, 'partial', {'mode': 'only'})
        summary = self.store.coverage_summary(self.store.coverage(self.registry, self.targets))
        self.assertEqual((summary['attempted'], summary['ok'], summary['partial'], summary['blocked'],
                          summary['never_attempted'], summary['run_id']), (1, 1, 1, 1, 0, later))

    def test_load_inventory_uses_the_configured_paths(self):
        companies = self.folder / 'companies.json'
        companies.write_text(json.dumps({'companies': V2_COMPANIES}), encoding='utf-8')
        registry, targets = scan.load_inventory({'companies_path': str(companies),
                                                 'targets_path': str(self.folder / 'targets.json')})
        self.assertEqual((len(registry), len(targets)), (6, 6))
        registry, targets = scan.load_inventory({'companies_path': str(self.folder / 'none.json'),
                                                 'targets_path': str(self.folder / 'none-either.json')})
        self.assertEqual((len(registry), targets), (0, []))

    def test_coverage_works_without_targets_or_employers(self):
        rows = self.store.coverage(self.registry, [])
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(row['original_names'] == [] for row in rows))
        only_targets = self.store.coverage(rank.Registry(), self.targets)
        self.assertEqual({row['inventory_state'] for row in only_targets}, {'identity unresolved'})
        self.assertEqual(len(only_targets), 6)
        self.assertEqual(self.store.coverage(rank.Registry(), []), [])


# ───────────────────────────── v2: scan modes, fairness, shared boards ─────────────────────────────

class PortalTask(FakeTask):
    def __init__(self, name, employer=None, board=None, **options):
        options.setdefault('kind', 'ats')
        super().__init__(name, **options)
        self.label = employer or name
        self.employer, self.board = employer, board


class ScanModesTest(ScanCase):
    def setUp(self):
        super().setUp()
        self.config['targets_path'] = str(self.data / 'no-targets.json')

    def tasks(self, **statuses):
        return [PortalTask('ats:a', 'Alpha', status=statuses.get('a', 'empty')),
                PortalTask('ats:b', 'Beta Pvt Ltd', status=statuses.get('b', 'empty')),
                PortalTask('ats:c', 'Gamma', status=statuses.get('c', 'empty')),
                FakeTask('board:hirist', status=statuses.get('hirist', 'empty'))]

    def ran(self, tasks):
        return [task.name for task in tasks if task.ctx is not None]

    def test_full_mode_is_the_default_and_is_recorded(self):
        tasks = self.tasks(b='blocked')
        summary = self.run_scan(tasks)
        self.assertEqual((summary['mode'], summary['configured'], summary['requested'], summary['attempted'],
                          summary['completed']), ('full', 4, 4, 4, 3))
        self.assertEqual(self.store.latest_run()['summary']['mode'], 'full')
        self.assertEqual(self.store.kv_get(scan.KV_PROGRESS)['mode'], 'full')
        by_label = {source['label']: source for source in summary['sources']}
        self.assertEqual((by_label['Alpha']['task'], by_label['Alpha']['employer'], by_label['Beta Pvt Ltd']['reason']),
                         ('ats:a', 'Alpha', 'refused'))
        self.assertIsInstance(by_label['Alpha']['elapsed_s'], float)
        health = {row['task']: row for row in self.store.latest_run()['health']}
        self.assertEqual((health['ats:b']['employer'], health['ats:b']['reason']), ('Beta Pvt Ltd', 'refused'))
        self.assertIsNotNone(health['ats:a']['elapsed_s'])

    def test_retry_runs_only_what_needs_attention(self):
        self.run_scan(self.tasks(b='blocked', hirist='error'))
        tasks = self.tasks()
        summary = self.run_scan(tasks, mode='retry')
        self.assertEqual(sorted(self.ran(tasks)), ['ats:b', 'board:hirist'])
        self.assertEqual((summary['mode'], summary['configured'], summary['requested'], summary['attempted'],
                          summary['status']), ('retry', 4, 2, 2, 'complete'))
        latest = self.store.latest_run()

        def run_rows():
            db = sqlite3.connect(self.store.path)
            try:
                return db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]
            finally:
                db.close()
        runs, seen, tasks = run_rows(), [], self.tasks()
        nothing = self.run_scan(tasks, mode='retry', progress=seen.append)   # everything is fine now
        self.assertEqual((self.ran(tasks), nothing['requested'], nothing['status'], nothing['sources'], nothing['run_id'],
                          nothing['mode'], nothing['configured']), ([], 0, 'nothing_to_retry', [], None, 'retry', 4))
        self.assertEqual(run_rows(), runs)                                 # no run was recorded
        self.assertEqual(self.store.latest_run(), latest)                  # so the last real run is still the latest
        progress = self.store.kv_get(scan.KV_PROGRESS)
        self.assertEqual((progress['state'], progress['status'], progress['run_id']), ('finished', 'nothing_to_retry', None))
        self.assertEqual(seen[-1], progress)
        self.assertEqual(self.run_scan(self.tasks(b='error'), mode='retry-incomplete')['mode'], 'retry')   # the CLI spelling

    def test_retry_includes_sources_never_attempted_or_missed_by_the_last_full_run(self):
        self.run_scan(self.tasks()[:2])                                    # Gamma and Hirist did not exist yet
        tasks = self.tasks()
        self.run_scan(tasks, mode='retry')
        self.assertEqual(sorted(self.ran(tasks)), ['ats:c', 'board:hirist'])
        self.run_scan(self.tasks()[:3])                                    # a later full run without Hirist
        tasks = self.tasks()
        self.run_scan(tasks, mode='retry')
        self.assertEqual(self.ran(tasks), ['board:hirist'])                # not attempted since that full run started

    def test_only_selects_by_employer_task_or_label(self):
        tasks = self.tasks()
        summary = self.run_scan(tasks, only=['beta', 'ats:c', 'Nobody Inc'])
        self.assertEqual(sorted(self.ran(tasks)), ['ats:b', 'ats:c'])       # "beta" matches "Beta Pvt Ltd"
        self.assertEqual((summary['mode'], summary['requested'], summary['unmatched']), ('only', 2, ['Nobody Inc']))
        tasks = self.tasks()
        self.assertEqual(self.run_scan(tasks, only=['board:hirist'])['requested'], 1)

    def test_only_accepts_an_alias_from_the_registry(self):
        companies = self.data / 'companies.json'
        companies.write_text(json.dumps({'companies': [{'name': 'Alpha', 'aliases': ['ALP', 'Alpha Global'], 'type': 'gcc'}]}),
                             encoding='utf-8')
        self.config['companies_path'] = str(companies)
        tasks = self.tasks()
        summary = self.run_scan(tasks, only=['ALP'])
        self.assertEqual((self.ran(tasks), summary['unmatched']), (['ats:a'], []))

    def test_only_with_no_match_is_a_failed_run_that_runs_nothing(self):
        tasks = self.tasks()
        summary = self.run_scan(tasks, only=['Nobody Inc'])
        self.assertEqual((summary['status'], self.ran(tasks)), ('failed', []))
        self.assertIn('Nobody Inc', summary['error'])

    def test_an_only_or_retry_run_does_not_shorten_the_look_back_fallback(self):
        self.run_scan(self.tasks(), only=['Alpha'])
        self.assertIsNone(self.store.kv_get(scan.KV_LAST_COMPLETE))

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            self.run_scan(self.tasks(), mode='everything')

    def test_sources_cut_by_the_budget_are_recorded_with_reason_budget(self):
        tasks = self.tasks()
        summary = self.run_scan(tasks, http=FakeHttp(expired=True))
        self.assertEqual(self.ran(tasks), [])
        self.assertEqual((summary['requested'], summary['attempted'], summary['completed'], len(summary['not_attempted']),
                          summary['reasons'], summary['status']), (4, 0, 0, 4, {'budget': 4}, 'partial'))
        self.assertTrue(all(source['status'] == 'error' and source['reason'] == 'budget' for source in summary['sources']))
        self.assertEqual({row['reason'] for row in self.store.latest_run()['health']}, {'budget'})
        progress = self.store.kv_get(scan.KV_PROGRESS)
        self.assertEqual((progress['requested'], progress['attempted'], progress['completed'], progress['done']), (4, 0, 0, 4))
        self.assertEqual(sorted(progress['not_attempted']), sorted(summary['not_attempted']))   # the same labels, as a list
        tasks = self.tasks()
        self.run_scan(tasks, mode='retry')
        self.assertEqual(len(self.ran(tasks)), 4)                          # all of them are retried

    def test_the_scan_summary_and_coverage_agree_about_a_budget_cut(self):
        companies = self.data / 'companies.json'
        companies.write_text(json.dumps({'companies': V2_COMPANIES}), encoding='utf-8')
        self.config['companies_path'] = str(companies)
        tasks = [PortalTask(name, employer, status='empty') for employer, name in V2_TASKS.items()]
        summary = self.run_scan(tasks, http=FakeHttp(expired=True))
        rows, counts = scan.load_coverage(self.store, self.config)
        self.assertEqual((summary['attempted'], len(summary['not_attempted'])), (0, 3))
        self.assertEqual((counts['attempted'], counts['not_reached'], counts['error'], counts['ok']), (0, 3, 0, 0))
        self.assertTrue(all(row['last_attempt_at'] is None for row in rows))
        matrix = self.store.kv_get(scan.KV_MATRIX)
        self.assertEqual((matrix['before']['Acme'], matrix['after']['Acme']), ('never attempted', 'not_reached'))

    def test_never_attempted_and_longest_waiting_sources_start_first(self):
        self.config['scan']['workers'] = 1
        journal = []

        def tasks():
            return [PortalTask('ats:a', 'Alpha', priority=10, status='empty', journal=journal),
                    PortalTask('ats:b', 'Beta', priority=20, status='empty', journal=journal),
                    PortalTask('ats:c', 'Gamma', priority=30, status='empty', journal=journal),
                    PortalTask('ats:d', 'Delta', priority=40, status='empty', journal=journal)]
        self.run_scan(tasks()[:2])                                         # run 1 reaches only Alpha and Beta
        del journal[:]
        self.run_scan(tasks()[:3], only=['Alpha'])                         # run 2, in the same second, attempts Alpha again
        del journal[:]
        history = self.store.task_history()
        self.assertEqual(history['ats:a']['attempted_run_seq'], history['ats:a']['attempted_full_run_seq'] + 1)
        self.assertEqual(history['ats:a']['attempted_full_run_seq'], history['ats:b']['attempted_full_run_seq'])
        self.run_scan(list(reversed(tasks())))                             # the order the tasks arrive in is irrelevant
        # Never read by a full scan first (Gamma, Delta), then the first full scan's cohort by priority. Alpha's
        # hand-run `only` scan does not send it to the back.
        self.assertEqual(journal, ['ats:c', 'ats:d', 'ats:a', 'ats:b'])

    def test_a_backlog_rotates_so_every_portal_is_attempted(self):
        # Ten portals and time for four per run: nothing may be starved, however many runs it takes.
        self.config['scan']['workers'] = 1
        names = [f'ats:p{number:02d}' for number in range(10)]
        attempted_in = {}
        for run in range(1, 4):
            journal = []

            class Budget(FakeHttp):
                def expired(self):
                    return len(journal) >= 4
            tasks = [PortalTask(name, f'Employer {index:02d}', priority=10 + index, status='empty', journal=journal)
                     for index, name in enumerate(names)]
            summary = self.run_scan(list(reversed(tasks)), http=Budget())   # no clock involved, and any input order
            self.assertEqual((len(journal), summary['attempted'], len(summary['not_attempted'])), (4, 4, 6), run)
            for name in journal:
                attempted_in.setdefault(name, run)
            if run == 1:
                self.assertEqual(journal, names[:4])                       # priority order while nothing has a history
            elif run == 2:
                self.assertEqual(journal, names[4:8])                      # the ones cut off go first
            else:
                self.assertEqual(journal, names[8:] + names[:2])           # then the last two, then the longest-waiting
        self.assertEqual(sorted(attempted_in), names)                      # all ten within ceil(10 / 4) = 3 full runs
        history = self.store.task_history()
        last = history['ats:p09']['run_seq']
        self.assertEqual((history['ats:p09']['reason'], history['ats:p09']['attempted_full_run_seq']), ('', last))
        self.assertEqual((history['ats:p04']['reason'], history['ats:p04']['attempted_full_run_seq']),
                         ('budget', last - 1))                             # cut off in run 3; last really ran in run 2

    def test_equal_priority_and_history_is_ordered_by_task_name(self):
        self.config['scan']['workers'] = 1
        names = ['ats:delta', 'ats:alpha', 'ats:charlie', 'ats:bravo']
        for arrival in (names, list(reversed(names)), sorted(names)):
            journal = []
            self.run_scan([PortalTask(name, name, priority=20, status='empty', journal=journal) for name in arrival])
            self.assertEqual(journal, sorted(names), arrival)

    def test_linkedin_has_its_own_worker(self):
        self.config['scan']['workers'] = 1
        portal_started, release = threading.Event(), threading.Event()
        order = []

        class SlowPortal(PortalTask):
            def run(self, http, ctx):
                portal_started.set()
                release.wait(5)
                order.append(self.name)
                return super().run(http, ctx)

        class LinkedIn(FakeTask):
            def run(self, http, ctx):
                portal_started.wait(5)                                     # the portal is busy on the only portal worker
                order.append(self.name)
                release.set()
                return super().run(http, ctx)
        summary = self.run_scan([SlowPortal('ats:slow', 'Slow', priority=10, status='empty'),
                                 LinkedIn('linkedin', kind='linkedin', priority=0, status='empty', found=3)])
        self.assertEqual(order, ['linkedin', 'ats:slow'])                  # LinkedIn ran while the portal was still busy
        self.assertEqual((summary['attempted'], summary['status']), (2, 'complete'))

    def test_a_shared_board_is_fetched_once_and_recorded_for_each_employer(self):
        registry_path = self.data / 'companies.json'
        registry_path.write_text(json.dumps({'companies': [{'name': 'Parent Group', 'type': 'gcc'},
                                                           {'name': 'Unit India', 'type': 'gcc'},
                                                           {'name': 'Quiet Unit', 'type': 'gcc'}]}), encoding='utf-8')
        self.config['companies_path'] = str(registry_path)
        jobs = [board_job(model.EMPLOYER_SOURCE, 'w1', company='Parent Group'),
                board_job(model.EMPLOYER_SOURCE, 'w2', company='Unit India Pvt Ltd', title='Pega Lead'),
                board_job(model.EMPLOYER_SOURCE, 'w3', company='Unit India', title='Pega Architect')]
        primary = PortalTask('ats:workday:parent', 'Parent Group', board='workday:parent.wd3:Careers', priority=10)
        primary._returns = {**model.make_result(model.EMPLOYER_SOURCE, 'Parent Group', 'ats', jobs=jobs, found=40,
                                                pages_complete=True, details_complete=True), }
        unit = PortalTask('ats:workday:unit', 'Unit India', board='workday:parent.wd3:Careers', priority=20)
        quiet = PortalTask('ats:workday:quiet', 'Quiet Unit', board='workday:parent.wd3:Careers', priority=30)
        other = PortalTask('ats:lever:other', 'Other Co', board='lever:other', status='empty')
        summary = self.run_scan([quiet, unit, other, primary])
        self.assertEqual(self.ran([primary, unit, quiet, other]), ['ats:workday:parent', 'ats:lever:other'])
        by_label = {source['label']: source for source in summary['sources']}
        self.assertEqual({label: (source['status'], source['kept']) for label, source in by_label.items()},
                         {'Parent Group': ('ok', 1), 'Unit India': ('ok', 2), 'Quiet Unit': ('empty', 0),
                          'Other Co': ('empty', 0)})                        # each employer is credited with its own jobs
        self.assertEqual(sum(source['kept'] for source in summary['sources']), 3)   # which add up to what was stored
        self.assertEqual((by_label['Unit India']['shared_with'], by_label['Unit India']['employer'],
                          by_label['Unit India']['pages_complete'], by_label['Unit India']['task']),
                         ('ats:workday:parent', 'Unit India', True, 'ats:workday:unit'))
        self.assertNotIn('shared_with', by_label['Parent Group'])
        self.assertEqual((summary['requested'], summary['attempted'], summary['completed'], summary['new']), (4, 4, 4, 3))
        health = {row['task']: row for row in self.store.latest_run()['health']}
        self.assertEqual((health['ats:workday:unit']['status'], health['ats:workday:unit']['kept'],
                          health['ats:workday:unit']['employer']), ('ok', 2, 'Unit India'))
        self.assertEqual((health['ats:workday:parent']['kept'], health['ats:workday:parent']['found']), (1, 40))
        self.assertEqual(self.store.jobs()[1], 3)
        # Each sighting is filed under the task and label of the employer the posting belongs to.
        filed = {row['company']: [(sighting['label'], sighting['source_id']) for sighting in self.store.job(row['id'])['sightings']]
                 for row in self.store.jobs()[0]}
        self.assertEqual(filed['Parent Group'], [('Parent Group', 'w1')])
        self.assertEqual(sorted(label for sightings in filed.values() for label, _ in sightings),
                         ['Parent Group', 'Unit India', 'Unit India'])
        db = sqlite3.connect(self.store.path)
        self.assertEqual(dict(db.execute('SELECT source_id, task FROM sightings')),
                         {'w1': 'ats:workday:parent', 'w2': 'ats:workday:unit', 'w3': 'ats:workday:unit'})
        db.close()
        self.assertEqual(self.store.kv_get(scan.KV_PROGRESS)['done'], 4)

    def test_a_follower_can_be_the_reader_and_closures_cover_the_whole_shared_board(self):
        companies = self.data / 'companies.json'
        companies.write_text(json.dumps({'companies': [{'name': 'Group', 'type': 'gcc'},
                                                       {'name': 'Group Research India', 'type': 'gcc'}]}), encoding='utf-8')
        self.config['companies_path'] = str(companies)

        def scan_board(*ids):
            jobs = [board_job(model.EMPLOYER_SOURCE, source_id, title=f'Pega Developer {source_id}',
                              company='Group' if source_id.startswith('g') else 'Group Research India') for source_id in ids]
            # The Bengaluru unit has the higher priority, so its task reads the board for the group too.
            unit = PortalTask('ats:beesite:unit', 'Group Research India', board='beesite:group', priority=10)
            unit._returns = {**model.make_result(model.EMPLOYER_SOURCE, 'Group Research India', 'ats', jobs=jobs,
                                                 pages_complete=True), 'employer': 'Group'}
            group = PortalTask('ats:beesite:group', 'Group', board='beesite:group', priority=20)
            summary = self.run_scan([group, unit])
            self.assertEqual(self.ran([unit, group]), ['ats:beesite:unit'])
            return {source['label']: source['kept'] for source in summary['sources']}
        self.assertEqual(scan_board('g1', 'g2', 'r1', 'r2', 'r3', 'r4'), {'Group Research India': 4, 'Group': 2})
        self.assertEqual(scan_board('g1', 'r1', 'r2', 'r3', 'r4'), {'Group Research India': 4, 'Group': 1})
        # g2 was filed under the group's task, not the reader's, and is still noticed as gone.
        state = {job['title']: job['possibly_closed'] for job in self.store.jobs()[0]}
        self.assertEqual((state['Pega Developer g2'], state['Pega Developer g1'], state['Pega Developer r1']), (True, False, False))
        health = {row['task']: row for row in self.store.latest_run()['health']}
        self.assertEqual((health['ats:beesite:group']['kept'], health['ats:beesite:group']['employer'],
                          health['ats:beesite:unit']['kept']), (1, 'Group', 4))

    def test_a_shared_board_is_always_read_by_the_same_task(self):
        def tasks():
            jobs = [board_job(model.EMPLOYER_SOURCE, 'w1', company='Parent Group'),
                    board_job(model.EMPLOYER_SOURCE, 'w2', company='Unit India', title='Pega Lead')]
            primary = PortalTask('ats:workday:parent', 'Parent Group', board='b1', priority=10)
            primary._returns = model.make_result(model.EMPLOYER_SOURCE, 'Parent Group', 'ats', jobs=jobs, pages_complete=True)
            unit = PortalTask('ats:workday:unit', 'Unit India', board='b1', priority=20)
            return primary, unit, PortalTask('ats:lever:other', 'Other Co', status='empty')
        primary, unit, other = tasks()
        summary = self.run_scan([primary, unit, other], only=['Unit India'])   # only the second employer was asked for
        self.assertEqual(self.ran([primary, unit, other]), ['ats:workday:parent'])   # the board's owner reads it
        self.assertEqual((summary['requested'], summary['attempted'], summary['unmatched']), (2, 2, []))
        self.assertEqual({source['label']: source['kept'] for source in summary['sources']}, {'Parent Group': 1, 'Unit India': 1})
        # A later run in which the unit's task waited longer still has the owner read the board.
        later = '2099-01-01T00:00:00+00:00'
        with mock.patch('radar.store.now_iso', return_value=later), mock.patch('radar.scan.now_iso', return_value=later):
            self.run_scan([tasks()[0]], only=['Parent Group'])
        primary, unit, other = tasks()
        self.run_scan([unit, other, primary])
        self.assertEqual(sorted(self.ran([primary, unit, other])), ['ats:lever:other', 'ats:workday:parent'])
        db = sqlite3.connect(self.store.path)
        self.assertEqual(dict(db.execute('SELECT source_id, task FROM sightings')),
                         {'w1': 'ats:workday:parent', 'w2': 'ats:workday:unit'})   # filed by employer, read by one task
        db.close()

    def test_attribution_on_a_shared_board_is_the_same_whatever_is_selected(self):
        companies = self.data / 'companies.json'
        companies.write_text(json.dumps({'companies': [{'name': 'Group', 'type': 'gcc'}, {'name': 'Group Mobility', 'type': 'gcc'},
                                                       {'name': 'Group Research India', 'type': 'gcc'}]}), encoding='utf-8')
        self.config['companies_path'] = str(companies)

        def scan_board(**options):
            jobs = [board_job(model.EMPLOYER_SOURCE, source_id, title=f'Pega Developer {source_id}', company=company)
                    for source_id, company in (('g1', 'Group'), ('g2', 'Group'), ('m1', 'Group Mobility'),
                                               ('r1', 'Group Research India'), ('r2', 'Group Research India'))]
            unit = PortalTask('ats:beesite:unit', 'Group Research India', board='beesite:group', priority=10)
            unit._returns = model.make_result(model.EMPLOYER_SOURCE, 'Group Research India', 'ats', jobs=jobs,
                                              pages_complete=True)
            members = [unit, PortalTask('ats:beesite:group', 'Group', board='beesite:group', priority=20),
                       PortalTask('ats:beesite:mobility', 'Group Mobility', board='beesite:group', priority=20),
                       PortalTask('ats:lever:other', 'Other Co', status='empty')]
            summary = self.run_scan(members, **options)
            db = sqlite3.connect(self.store.path)
            filed = dict(db.execute('SELECT source_id, task FROM sightings'))
            labels = dict(db.execute('SELECT source_id, label FROM sightings'))
            db.close()
            return ({source['label']: (source['status'], source['kept']) for source in summary['sources']}, filed, labels,
                    summary)
        expected_counts = {'Group Research India': ('ok', 2), 'Group': ('ok', 2), 'Group Mobility': ('ok', 1)}
        expected_filed = {'g1': 'ats:beesite:group', 'g2': 'ats:beesite:group', 'm1': 'ats:beesite:mobility',
                          'r1': 'ats:beesite:unit', 'r2': 'ats:beesite:unit'}
        for options in ({'only': ['Group Research India']}, {'only': ['Group Mobility']}, {'only': ['Group']}, {}):
            counts, filed, labels, summary = scan_board(**options)
            counts.pop('Other Co', None)
            self.assertEqual((counts, filed), (expected_counts, expected_filed), options)
            self.assertEqual(labels['g1'], 'Group', options)               # never relabelled to the reader
            if 'only' in options:
                self.assertEqual((summary['requested'], summary['attempted']), (3, 3), options)   # the whole board
        self.assertEqual(self.store.jobs()[1], 5)

    def test_a_source_that_started_as_the_budget_ended_is_not_reached_everywhere(self):
        companies = self.data / 'companies.json'
        companies.write_text(json.dumps({'companies': V2_COMPANIES}), encoding='utf-8')
        self.config['companies_path'] = str(companies)
        # Acme started but its first request met the deadline: no answer at all. Booking.com read one
        # page before the time ran out: that is a real, partial attempt.
        tasks = [PortalTask(V2_TASKS['Acme'], 'Acme', status='error', reason='budget', error='the time budget ran out',
                            requests=0),
                 PortalTask(V2_TASKS['Booking.com'], 'Booking.com', status='partial', reason='budget', found=10,
                            error='stopped at page 2: the time budget ran out'),
                 PortalTask(V2_TASKS['Legacy Bank'], 'Legacy Bank', status='empty')]
        summary = self.run_scan(tasks)
        self.assertEqual(self.ran(tasks), list(V2_TASKS.values()))         # all three did start
        self.assertEqual((summary['attempted'], summary['not_attempted'], summary['completed']), (2, ['Acme'], 1))
        progress = self.store.kv_get(scan.KV_PROGRESS)
        self.assertEqual((progress['attempted'], progress['not_attempted']), (2, ['Acme']))
        rows, counts = scan.load_coverage(self.store, self.config)
        by_name = {row['canonical']: row for row in rows}
        self.assertEqual((by_name['Acme']['latest_status'], by_name['Acme']['last_attempt_at']), ('not_reached', None))
        self.assertEqual(by_name['Booking.com']['latest_status'], 'partial')
        self.assertIsNotNone(by_name['Booking.com']['last_attempt_at'])
        self.assertEqual((counts['attempted'], counts['not_reached'], counts['partial'], counts['ok'], counts['error']),
                         (2, 1, 1, 1, 0))                                   # the same split as the scan summary
        history = self.store.task_history()
        self.assertIsNone(history[V2_TASKS['Acme']]['attempted_run_seq'])
        self.assertIsNotNone(history[V2_TASKS['Booking.com']]['attempted_run_seq'])

    def test_a_failed_shared_board_fails_for_every_employer_on_it(self):
        primary = PortalTask('ats:workday:parent', 'Parent Group', board='b1', status='blocked', error='HTTP 403',
                             priority=1)
        unit = PortalTask('ats:workday:unit', 'Unit India', board='b1', priority=2)
        summary = self.run_scan([primary, unit])
        self.assertEqual({source['label']: (source['status'], source['reason']) for source in summary['sources']},
                         {'Parent Group': ('blocked', 'refused'), 'Unit India': ('blocked', 'refused')})
        self.assertEqual(sorted(summary['attention']), ['Parent Group', 'Unit India'])
        retry = [PortalTask('ats:workday:parent', 'Parent Group', board='b1', status='empty', priority=1),
                 PortalTask('ats:workday:unit', 'Unit India', board='b1', priority=2)]
        self.assertEqual(self.run_scan(retry, mode='retry')['requested'], 2)   # both are retried together

    def test_the_coverage_matrix_and_summary_are_refreshed_by_a_scan(self):
        companies = self.data / 'companies.json'
        companies.write_text(json.dumps({'companies': V2_COMPANIES}), encoding='utf-8')
        self.config['companies_path'] = str(companies)
        (self.data / 'targets.json').write_text(json.dumps(V2_TARGETS), encoding='utf-8')
        self.config['targets_path'] = str(self.data / 'targets.json')
        summary = self.run_scan([PortalTask(V2_TASKS['Acme'], 'Acme', status='empty'),
                                 PortalTask(V2_TASKS['Booking.com'], 'Booking.com', status='blocked'),
                                 PortalTask(V2_TASKS['Legacy Bank'], 'Legacy Bank', status='empty')], only=['Acme', 'Booking.com'])
        matrix = self.store.kv_get(scan.KV_MATRIX)
        self.assertEqual(matrix['run_id'], summary['run_id'])
        self.assertEqual((matrix['before']['Acme'], matrix['after']['Acme']), ('never attempted', 'empty'))
        self.assertEqual((matrix['before']['Booking.com'], matrix['after']['Booking.com']), ('never attempted', 'blocked'))
        self.assertEqual(matrix['after']['Legacy Bank'], 'never attempted')
        self.assertEqual((matrix['after']['Toyota'], matrix['after']['target: Mystery Systems']),
                         ('wrong scope only', 'identity unresolved'))
        rows, counts = scan.load_coverage(self.store, self.config)
        self.assertEqual((counts['original_rows'], counts['attempted'], counts['ok'], counts['blocked'],
                          counts['never_attempted'], counts['run_id']), (6, 2, 1, 1, 1, summary['run_id']))
        self.assertIsNone(self.store.kv_get('coverage_summary'))           # nothing is cached any more


# ───────────────────────────── v2: verify, coverage export, report ─────────────────────────────

GOOD_PROBE = {'board_ok': True, 'board_size': 412, 'pega_total': 3, 'india_in_first_page': 2, 'page2_ok': None,
              'detail_ok': True, 'rows_parsed': 20, 'inconclusive': False, 'notes': ['India filtered'], 'status': 'ok',
              'requests': 4}


class VerifyTest(StoreCase):
    def setUp(self):
        super().setUp()
        self.registry = v2_registry()
        self.calls = []

    def probe(self, outcomes=None):
        def run(http, employer, portal):
            self.calls.append((employer['name'], portal['kind']))
            outcome = (outcomes or {}).get(employer['name'], GOOD_PROBE)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        return run

    def test_outcome_is_exactly_the_agreed_rule(self):
        cases = (({}, 'passed'), ({'page2_ok': True}, 'passed'), ({'page2_ok': None, 'detail_ok': None}, 'passed'),
                 ({'pega_total': 0}, 'passed'),                             # a readable search with rows parsed and no Pega today
                 ({'rows_parsed': 1}, 'passed'),
                 ({'board_ok': False}, 'failed'), ({'board_ok': None}, 'failed'), ({'pega_total': None}, 'failed'),
                 ({'page2_ok': False}, 'failed'), ({'detail_ok': False}, 'failed'),
                 ({'detail_ok': False, 'inconclusive': True}, 'failed'),    # a failure is a failure
                 ({'rows_parsed': 0}, 'inconclusive'),                      # the board answered with rows nobody could parse
                 ({'rows_parsed': None}, 'inconclusive'), ({'rows_parsed': True}, 'inconclusive'),
                 ({'inconclusive': True}, 'inconclusive'),                  # e.g. a global board with no India posting
                 ({'inconclusive': True, 'rows_parsed': 50, 'india_in_first_page': 0}, 'inconclusive'),
                 ({'probe_passed': False}, 'inconclusive'),                # the adapter's own verdict can only tighten ours
                 ({'probe_passed': True}, 'passed'), ({'probe_passed': True, 'rows_parsed': 0}, 'inconclusive'),
                 ({'probe_passed': True, 'board_ok': False}, 'failed'))
        for change, expected in cases:
            record = {**GOOD_PROBE, **change}
            self.assertEqual(acceptance.outcome(record), expected, change)
            self.assertIs(acceptance.passed(record), expected == 'passed', change)
        without_count = {key: value for key, value in GOOD_PROBE.items() if key != 'rows_parsed'}
        self.assertEqual(acceptance.outcome(without_count), 'inconclusive')   # no proof that anything was parsed
        self.assertEqual(acceptance.outcome({}), 'failed')

    def test_the_report_has_three_buckets(self):
        outcomes = {'Acme': GOOD_PROBE, 'Booking.com': {**GOOD_PROBE, 'inconclusive': True, 'india_in_first_page': 0,
                                                        'notes': ['no India posting on the first page']},
                    'Legacy Bank': {**GOOD_PROBE, 'board_ok': False, 'status': 'error', 'notes': ['board: HTTP 404']}}
        report = acceptance.run_verify(self.store, self.registry, FakeHttp(), probe=self.probe(outcomes), state='all')
        by_name = {record['employer']: record for record in report['results']}
        self.assertEqual({name: (record['outcome'], record['passed']) for name, record in by_name.items()},
                         {'Acme': ('passed', True), 'Booking.com': ('inconclusive', False), 'Legacy Bank': ('failed', False)})
        self.assertEqual((report['passed'], report['inconclusive'], report['failed']),
                         ([by_name['Acme']['key']], [by_name['Booking.com']['key']], [by_name['Legacy Bank']['key']]))
        text = acceptance.verify_markdown(report)
        self.assertIn('Passed: 1. Inconclusive: 1. Failed: 1.', text)
        passed_at, inconclusive_at, failed_at = (text.index(heading) for heading in
                                                 ('## Passed (1)', '## Inconclusive (1)', '## Failed (1)'))
        self.assertTrue(passed_at < text.index('| Acme |') < inconclusive_at < text.index('| Booking.com |') < failed_at
                        < text.index('| Legacy Bank |'))
        self.assertNotIn('--promote', text)                                # the only pass is already verified
        empty = acceptance.verify_markdown({**report, 'results': []})
        self.assertEqual(empty.count('None.'), 3)

    def test_candidates_are_probed_and_results_stored(self):
        report = acceptance.run_verify(self.store, self.registry, FakeHttp(), probe=self.probe())
        self.assertEqual(self.calls, [('Booking.com', 'icims')])            # verified, wrong-scope and unsupported are skipped
        self.assertEqual((report['state'], report['checked'], len(report['passed']), report['inconclusive'],
                          report['failed']), ('candidate', 1, 1, [], []))
        record = report['results'][0]
        self.assertEqual((record['employer'], record['kind'], record['state'], record['scope'], record['portal_index'],
                          record['passed'], record['pega_total'], record['notes'], record['board_size'],
                          record['india_in_first_page'], record['status'], record['requests'], record['outcome'],
                          record['rows_parsed']),
                         ('Booking.com', 'icims', 'candidate', 'global', 0, True, 3, ['India filtered'], 412, 2, 'ok', 4,
                          'passed', 20))
        self.assertTrue(set(acceptance.PROBE_KEYS) <= set(record))
        self.assertEqual(self.store.kv_get(acceptance.KV_VERIFICATION), {record['key']: record})

    def test_a_real_adapter_probe_result_reaches_the_report_whole(self):
        # The adapters' own probe, run offline against canned replies: every field it returns must
        # arrive in the record and the report, under the adapters' names.
        from radar.sources import probe_portal
        board = json.dumps({'jobs': [
            {'id': 1, 'title': 'Pega Developer', 'absolute_url': 'https://boards.greenhouse.io/acme/jobs/1',
             'location': {'name': 'Bengaluru, India'}, 'content': 'Build Pega applications', 'updated_at': '2026-11-10T00:00:00Z'},
            {'id': 2, 'title': 'Java Developer', 'absolute_url': 'https://boards.greenhouse.io/acme/jobs/2',
             'location': {'name': 'Pune'}, 'content': 'Spring'}], 'meta': {'total': 2}})

        class Canned:
            def __init__(self, body):
                self.body = body

            def expired(self):
                return False

            def host_open(self, host):
                return True

            def get(self, url, **options):
                if self.body is None:
                    return net.Response(0, '', url, 'DNS lookup failed for boards-api.greenhouse.io', reason='dns')
                return net.Response(200, self.body, url)

            def post_json(self, url, payload, **options):
                return self.get(url)
        registry = rank.Registry([
            {'name': 'Acme', 'type': 'product', 'portals': [{'kind': 'greenhouse', 'board': 'acme', 'state': 'candidate',
                                                             'scope': 'global'}]},
            {'name': 'Broken', 'type': 'gcc', 'portals': [{'kind': 'workday', 'tenant': 'x', 'state': 'candidate',
                                                           'scope': 'india'}]}])
        employer = registry.entries[0]
        direct = probe_portal(Canned(board), employer, rank.employer_portals(employer)[0])
        report = acceptance.run_verify(self.store, registry, Canned(board), only=['Acme'])   # the default, real probe
        record = report['results'][0]
        kept = {key for key in direct if not key.startswith('_')} - {'board_total', 'india_first_page', 'passed'}
        self.assertEqual({key: record[key] for key in kept}, {key: direct[key] for key in kept})
        self.assertEqual((record['board_ok'], record['board_size'], record['pega_total'], record['india_in_first_page'],
                          record['status']), (True, 2, 1, 1, 'ok'))
        self.assertEqual(record['outcome'], acceptance.outcome(direct))      # judged from the adapter's own figures
        self.assertGreaterEqual(record['requests'], 1)
        self.assertRegex(acceptance.verify_markdown(report), r'\| Acme \| greenhouse \| candidate \| ok \| 2 \| \d* ?\| 1 \| 1 \|')

        failed = acceptance.run_verify(self.store, registry, Canned(None), state='all')
        by_name = {item['employer']: item for item in failed['results']}
        self.assertEqual((by_name['Acme']['outcome'], by_name['Acme']['status'], by_name['Acme']['pega_total']),
                         ('failed', 'error', None))
        self.assertIn('DNS lookup failed', ' '.join(by_name['Acme']['notes']))
        self.assertIn('portal settings lack', ' '.join(by_name['Broken']['notes']))   # a mis-configured portal is reported
        self.assertIn('DNS lookup failed', acceptance.verify_markdown(failed))

    def test_a_probe_cannot_overwrite_which_portal_a_record_is_about(self):
        report = acceptance.run_verify(self.store, self.registry, FakeHttp(), probe=lambda http, employer, portal: {
            **GOOD_PROBE, 'employer': 'Someone Else', 'kind': 'lever', 'passed': False, 'outcome': 'failed',
            'future_field': 7, '_working': 1})
        record = report['results'][0]
        self.assertEqual((record['employer'], record['kind'], record['passed'], record['future_field']),
                         ('Booking.com', 'icims', False, 7))
        self.assertEqual((record['outcome'], record['probe_passed']), ('inconclusive', False))   # its verdict only tightens
        self.assertNotIn('_working', record)

    def test_state_all_includes_verified_portals_and_only_filters_by_name(self):
        acceptance.run_verify(self.store, self.registry, FakeHttp(), probe=self.probe(), state='all')
        self.assertEqual(self.calls, [('Acme', 'workday'), ('Booking.com', 'icims'), ('Legacy Bank', 'greenhouse')])
        del self.calls[:]
        acceptance.run_verify(self.store, self.registry, FakeHttp(), probe=self.probe(), state='all',
                              only=['acme corp', 'Toyota'])
        self.assertEqual(self.calls, [('Acme', 'workday')])                 # an alias matches; wrong scope is never probed

    def test_a_failing_or_raising_probe_is_recorded_not_fatal(self):
        outcomes = {'Acme': RuntimeError('adapter bug'),
                    'Booking.com': {**GOOD_PROBE, 'board_ok': False, 'reason': 'http_4xx', 'error': 'HTTP 404'},
                    'Legacy Bank': 'not a dict'}
        report = acceptance.run_verify(self.store, self.registry, FakeHttp(), probe=self.probe(outcomes), state='all')
        by_name = {record['employer']: record for record in report['results']}
        self.assertEqual(report['passed'], [])
        self.assertIn('RuntimeError: adapter bug', by_name['Acme']['error'])
        self.assertEqual((by_name['Booking.com']['passed'], by_name['Booking.com']['reason']), (False, 'http_4xx'))
        self.assertIn('TypeError', by_name['Legacy Bank']['error'])

    def test_nothing_is_probed_after_the_budget(self):
        report = acceptance.run_verify(self.store, self.registry, FakeHttp(expired=True), probe=self.probe(), state='all')
        self.assertEqual(self.calls, [])
        self.assertEqual({record['reason'] for record in report['results']}, {'budget'})
        self.assertEqual(report['passed'], [])

    def test_later_checks_merge_into_the_stored_results(self):
        acceptance.run_verify(self.store, self.registry, FakeHttp(), probe=self.probe())
        acceptance.run_verify(self.store, self.registry, FakeHttp(), probe=self.probe(), state='all', only=['Acme'])
        self.assertEqual(sorted(record['employer'] for record in self.store.kv_get(acceptance.KV_VERIFICATION).values()),
                         ['Acme', 'Booking.com'])

    def test_reports_are_written_as_json_and_markdown(self):
        report = acceptance.run_verify(self.store, self.registry, FakeHttp(), probe=self.probe(
            {'Booking.com': {**GOOD_PROBE, 'notes': ['a | pipe', 'second\nline']}}))
        json_path, md_path = acceptance.write_verify(report, self.folder / 'data' / 'acceptance')
        self.assertRegex(json_path.name, r'^verify-\d{8}-\d{6}\.json$')
        self.assertEqual(md_path.name, json_path.with_suffix('.md').name)
        self.assertEqual(json.loads(json_path.read_text(encoding='utf-8'))['results'][0]['employer'], 'Booking.com')
        text = md_path.read_text(encoding='utf-8')
        self.assertIn('| Booking.com | icims | candidate | ok | 412 | 20 | 3 | 2 |', text)
        self.assertIn('radar.py verify --promote', text)
        self.assertIn('a \\| pipe; second line', text)                      # table cells cannot break the table

    def test_portal_key_follows_the_board_not_its_state(self):
        portal = {'kind': 'icims', 'host': 'jobs.booking.test', 'state': 'candidate', 'scope': 'global', 'note': 'x'}
        key = acceptance.portal_key('Booking.com', portal)
        self.assertEqual(key, acceptance.portal_key('Booking.com', {**portal, 'state': 'verified', 'note': 'checked'}))
        self.assertNotEqual(key, acceptance.portal_key('Booking.com', {**portal, 'host': 'careers.booking.test'}))
        self.assertNotEqual(key, acceptance.portal_key('Agoda', portal))


class PromoteTest(StoreCase):
    def setUp(self):
        super().setUp()
        self.companies = self.folder / 'companies.json'
        self.companies.write_text(json.dumps({'companies': V2_COMPANIES}, indent=1), encoding='utf-8')
        self.backups = self.folder / 'data' / 'backups'

    def verify(self, outcome=GOOD_PROBE):
        acceptance.run_verify(self.store, rank.load_registry(self.companies), FakeHttp(),
                              probe=lambda http, employer, portal: outcome)

    def states(self):
        return {entry['name']: [portal['state'] for portal in entry.get('portals', [])]
                for entry in json.loads(self.companies.read_text(encoding='utf-8'))['companies']}

    def test_promote_marks_passed_candidates_and_backs_the_file_up(self):
        before = self.companies.read_text(encoding='utf-8')
        self.verify()
        self.assertEqual(self.states()['Booking.com'], ['candidate'])       # verify alone changes nothing
        promoted = acceptance.promote(self.companies, self.store, self.backups)
        self.assertEqual(promoted, [{'employer': 'Booking.com', 'kind': 'icims'}])
        states = self.states()
        self.assertEqual((states['Booking.com'], states['Toyota'], states['HDFC Bank'], states['Acme']),
                         (['verified'], ['wrong_scope'], ['unsupported'], ['verified']))
        copies = list(self.backups.glob('companies-*.json'))
        self.assertEqual(len(copies), 1)
        self.assertEqual(copies[0].read_text(encoding='utf-8'), before)
        self.assertFalse(self.companies.with_suffix('.json.tmp').exists())
        after = json.loads(self.companies.read_text(encoding='utf-8'))['companies']
        self.assertEqual(after[2], V2_COMPANIES[2])                         # untouched entries are unchanged
        self.assertEqual(len(rank.load_registry(self.companies)), 6)
        self.assertEqual(acceptance.promote(self.companies, self.store, self.backups), [])   # nothing left to promote
        self.assertEqual(len(list(self.backups.glob('companies-*.json'))), 1)

    def test_a_portal_that_did_not_pass_is_not_promoted(self):
        self.verify({**GOOD_PROBE, 'detail_ok': False})
        self.assertEqual(acceptance.promote(self.companies, self.store, self.backups), [])
        self.assertEqual(self.states()['Booking.com'], ['candidate'])
        self.assertFalse(self.backups.exists())                             # no change, so no backup either

    def test_a_board_edited_after_verification_is_not_promoted(self):
        self.verify()
        document = json.loads(self.companies.read_text(encoding='utf-8'))
        document['companies'][1]['portals'][0]['host'] = 'other.booking.test'
        self.companies.write_text(json.dumps(document), encoding='utf-8')
        self.assertEqual(acceptance.promote(self.companies, self.store, self.backups), [])

    def test_nothing_verified_yet(self):
        self.assertEqual(acceptance.promote(self.companies, self.store, self.backups), [])

    def test_an_inconclusive_check_is_not_promoted(self):
        for change in ({'inconclusive': True}, {'rows_parsed': 0}):
            self.verify({**GOOD_PROBE, **change})
            self.assertEqual(acceptance.promote(self.companies, self.store, self.backups), [], change)
        self.assertEqual(self.states()['Booking.com'], ['candidate'])

    def test_a_check_older_than_thirty_days_is_not_promoted(self):
        old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(timespec='seconds')
        with mock.patch('radar.acceptance.now_iso', return_value=old):
            self.verify()
        self.assertEqual(acceptance.promote(self.companies, self.store, self.backups), [])
        recent = (datetime.now(timezone.utc) - timedelta(days=29)).isoformat(timespec='seconds')
        with mock.patch('radar.acceptance.now_iso', return_value=recent):
            self.verify()
        self.assertEqual(len(acceptance.promote(self.companies, self.store, self.backups)), 1)

    def test_a_record_stored_under_the_old_rule_is_judged_again(self):
        self.verify()
        records = self.store.kv_get(acceptance.KV_VERIFICATION)
        for record in records.values():
            del record['rows_parsed']                                       # as written before parsing was required
            record['passed'] = True
        self.store.kv_set(acceptance.KV_VERIFICATION, {**records, 'junk': 'not a record'})
        self.assertEqual(acceptance.promote(self.companies, self.store, self.backups), [])


class CoverageExportTest(StoreCase):
    def setUp(self):
        super().setUp()
        result = model.make_result(model.EMPLOYER_SOURCE, 'Acme', 'ats', status='partial', reason='timeout',
                                   error='=cmd|page 2 timed out', employer='Acme', pages_complete=False)
        result['task'] = V2_TASKS['Acme']
        self.store.save_result(self.run_id, result, plain_ranker)
        self.rows = self.store.coverage(v2_registry(), v2_targets(self.folder))
        self.summary = self.store.coverage_summary(self.rows)

    def test_csv_has_every_column_and_every_row(self):
        table = list(csv.DictReader(io.StringIO(acceptance.coverage_csv(self.rows))))
        self.assertEqual(list(table[0]), list(radar_store.COVERAGE_COLUMNS))
        self.assertEqual(len(table), 8)
        by_name = {row['canonical'] or row['original_names']: row for row in table}
        acme = by_name['Acme']
        self.assertEqual((acme['original_names'], acme['portals'], acme['latest_status'], acme['latest_reason'],
                          acme['pages_complete'], acme['sources'], acme['inventory_state']),
                         ('ACME Corporation; Acme India', 'workday (verified, india)', 'partial', 'timeout', 'no',
                          V2_TASKS['Acme'] + ': partial [timeout]', 'configured'))
        self.assertEqual(acme['latest_error'], "'=cmd|page 2 timed out")     # untrusted text cannot run as a formula
        self.assertEqual((by_name['Nothing Configured']['latest_status'], by_name['Nothing Configured']['inventory_state']),
                         ('', 'not configured'))
        self.assertEqual(by_name['Mystery Systems']['inventory_state'], 'identity unresolved')

    def test_markdown_and_files(self):
        csv_path, md_path = acceptance.write_coverage(self.rows, self.summary, self.folder / 'out' / 'coverage')
        self.assertEqual((csv_path.name, md_path.name), ('coverage.csv', 'coverage.md'))
        self.assertTrue(csv_path.read_bytes().startswith(b'\xef\xbb\xbf'))
        text = md_path.read_text(encoding='utf-8')
        for needle in ('Original target rows: 6', 'Canonical employers: 6', 'identity unresolved: 2',
                       '| Acme | ACME Corporation; Acme India | product | yes | workday (verified, india) |',
                       '| (unresolved) | Mystery Systems |', 'never shown as empty', '=cmd\\|page 2'):
            self.assertIn(needle, text)
        again, _ = acceptance.write_coverage(self.rows, self.summary, self.folder / 'out' / 'named.csv')
        self.assertEqual(again.name, 'named.csv')


class ReportTest(ScanCase):
    def report(self):
        rows, summary = scan.load_coverage(self.store, self.config)
        return acceptance.report_markdown(self.store, rows, summary)

    def setUp(self):
        super().setUp()
        companies = self.data / 'companies.json'
        companies.write_text(json.dumps({'companies': V2_COMPANIES}), encoding='utf-8')
        (self.data / 'targets.json').write_text(json.dumps(V2_TARGETS), encoding='utf-8')
        self.config['companies_path'], self.config['targets_path'] = str(companies), str(self.data / 'targets.json')

    def test_before_any_scan(self):
        self.assertIn('No scan has finished yet', self.report())

    def test_report_of_a_run(self):
        summary = self.run_scan([
            PortalTask(V2_TASKS['Acme'], 'Acme', jobs=[board_job(model.EMPLOYER_SOURCE, 'a1', company='Acme')]),
            PortalTask(V2_TASKS['Booking.com'], 'Booking.com', status='error', reason='dns',
                       error='DNS lookup failed for jobs.booking.test'),
            PortalTask(V2_TASKS['Legacy Bank'], 'Legacy Bank', status='empty')])
        text = self.report()
        for needle in (f'Run `{summary["run_id"]}`: mode **full**, status **partial**',
                       'Scannable sources configured: 3', 'Requested in this run: 3', 'Attempted (actually started): 3',
                       'Completed without needing attention: 2', 'New jobs: 1 (1 in Bengaluru, 1 at product or GCC',
                       '| error | 1 |', '| Booking.com | error |', 'DNS lookup failed for jobs.booking.test',
                       '## Coverage before and after', '| Acme | never attempted | ok | yes |',
                       '| Booking.com | never attempted | error | yes |', '| Legacy Bank | never attempted | empty | yes |',
                       '| dns | 1 |', 'Attempted in the latest run: 3', 'Never attempted: 0; not reached within the time budget: 0',
                       'Latest outcome ok or empty: 2; partial: 0; blocked: 0; maintenance: 0; error: 1',
                       '| Toyota | wrong scope only | wrong scope only | no |',
                       '| target: Mystery Systems | identity unresolved | identity unresolved | no |',
                       'Original target rows: 6', 'still a gap, not coverage'):
            self.assertIn(needle, text)

    def test_a_failed_latest_attempt_is_stated_above_the_last_good_run(self):
        good = self.run_scan([PortalTask('ats:workday:acme', 'Acme', status='empty')])
        later = '2099-01-01T00:00:00+00:00'
        with mock.patch('radar.store.now_iso', return_value=later), mock.patch('radar.scan.now_iso', return_value=later):
            self.run_scan([PortalTask('ats:workday:acme', 'Acme')], only=['Nobody'])
        text = self.report()
        self.assertIn('failed', text.split('\n')[2])
        self.assertIn(f'Run `{good["run_id"]}`', text)


class CliV2Test(CliCase):
    def setUp(self):
        super().setUp()
        self.companies = self.data.parent / 'companies.json'
        self.targets = self.data.parent / 'targets.json'
        self.companies.write_text(json.dumps({'companies': V2_COMPANIES}), encoding='utf-8')
        self.targets.write_text(json.dumps(V2_TARGETS), encoding='utf-8')
        for name, path in (('COMPANIES_PATH', self.companies), ('TARGETS_PATH', self.targets)):
            patcher = mock.patch.object(self.cli, name, path)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_scan_flags_reach_run_scan(self):
        from radar import scan as scan_module
        summary = {'status': 'complete', 'attention': [], 'mode': 'retry', 'attempted': 1, 'requested': 2, 'completed': 1,
                   'new': 0, 'unmatched': ['Nobody'], 'not_attempted': ['Gamma']}
        for argv, expected in ((['scan', '--retry-incomplete'], {'minutes': None, 'only': None, 'mode': 'retry'}),
                               (['scan', '--only', 'Acme, Booking.com ,'],
                                {'minutes': None, 'only': ['Acme', 'Booking.com'], 'mode': 'full'})):
            with mock.patch.object(scan_module, 'run_scan', return_value=summary) as run, \
                    mock.patch.object(scan_module, 'setup_console_logging'):
                code, output = self.invoke(*argv)
            self.assertEqual((code, run.call_args.kwargs), (0, expected))
            self.assertIn('1 of 2 requested sources attempted', output)
            self.assertIn('No source matches: Nobody', output)
            self.assertIn('--retry-incomplete', output)

    def test_verify_writes_reports_and_promote_updates_the_registry(self):
        from radar import acceptance as module
        probes = []

        def probe(http, employer, portal):
            probes.append((employer['name'], http.user_agent))
            return GOOD_PROBE
        fake_sources = mock.MagicMock(probe_portal=probe)
        with mock.patch.dict(sys.modules, {'radar.sources': fake_sources}):
            code, output = self.invoke('verify', '--minutes', '1')
        self.assertEqual(code, 0)
        self.assertEqual(probes, [('Booking.com', model.DEFAULT_CONFIG['http']['user_agent'])])
        self.assertIn('1 portals checked: 1 passed, 0 inconclusive, 0 failed', output)
        self.assertEqual(len(list((self.data / 'acceptance').glob('verify-*.json'))), 1)
        self.assertEqual(len(list((self.data / 'acceptance').glob('verify-*.md'))), 1)
        self.assertEqual(len(Store(self.data / 'radar.sqlite3').kv_get(module.KV_VERIFICATION)), 1)
        self.assertEqual(json.loads(self.companies.read_text(encoding='utf-8'))['companies'][1]['portals'][0]['state'],
                         'candidate')

        code, output = self.invoke('verify', '--promote')                  # no network: reads the stored results
        self.assertEqual(code, 0)
        self.assertIn('verified: Booking.com (icims)', output)
        self.assertEqual(json.loads(self.companies.read_text(encoding='utf-8'))['companies'][1]['portals'][0]['state'],
                         'verified')
        self.assertEqual(len(list((self.data / 'backups').glob('companies-*.json'))), 1)
        code, output = self.invoke('verify', '--promote')
        self.assertIn('0 portals marked verified', output)

    def test_verify_with_nothing_to_check_exits_1(self):
        with mock.patch.dict(sys.modules, {'radar.sources': mock.MagicMock(probe_portal=lambda *args: GOOD_PROBE)}):
            code, output = self.invoke('verify', '--only', 'Nobody Inc')
        self.assertEqual(code, 1)
        self.assertIn('0 portals checked', output)

    def test_coverage_command(self):
        code, output = self.invoke('coverage')
        self.assertEqual(code, 0)
        self.assertIn('8 rows: 6 employers, 3 with a scannable portal', output)
        written = sorted(path.suffix for path in (self.data / 'acceptance').glob('coverage-*'))
        self.assertEqual(written, ['.csv', '.md'])
        target = self.data / 'mine' / 'table.csv'
        self.assertEqual(self.invoke('coverage', str(target))[0], 0)
        with open(target, encoding='utf-8-sig', newline='') as handle:
            self.assertEqual(len(list(csv.DictReader(handle))), 8)
        self.assertTrue(target.with_suffix('.md').exists())

    def test_report_command(self):
        code, output = self.invoke('report')
        self.assertEqual(code, 0)
        reports = list((self.data / 'acceptance').glob('report-*.md'))
        self.assertEqual(len(reports), 1)
        self.assertIn('No scan has finished yet', reports[0].read_text(encoding='utf-8'))
        target = self.data / 'r.md'
        self.invoke('report', str(target))
        self.assertTrue(target.exists())

    def doctor(self):
        with mock.patch.object(self.cli, 'MODULES', ('radar.model', 'radar.acceptance')), \
                mock.patch.object(self.cli, 'BASE', PROJECT):
            return self.invoke('doctor')

    def test_doctor_accepts_valid_portals_and_targets(self):
        document = json.loads(self.targets.read_text(encoding='utf-8'))
        document['rows'] = [row for row in document['rows'] if row['row'] != 5]      # row 5 names an unknown employer
        self.targets.write_text(json.dumps(document), encoding='utf-8')
        code, output = self.doctor()
        self.assertEqual(code, 0, output)
        self.assertIn('companies.json: 6 employers', output)
        self.assertIn('portals: 1 candidate, 1 unsupported, 2 verified, 1 wrong_scope', output)
        self.assertIn('targets.json: 5 original rows (1 added, 2 matched, 1 related, 1 unresolved)', output)

    def test_doctor_reports_bad_portals_and_targets(self):
        companies = [{'name': 'A', 'type': 'gcc', 'portals': [{'state': 'verified', 'scope': 'india'}]},
                     {'name': 'B', 'type': 'gcc', 'portals': [{'kind': 'lever', 'state': 'trusted', 'scope': 'india'}]},
                     {'name': 'C', 'type': 'gcc', 'portals': [{'kind': 'lever', 'state': 'verified', 'scope': 'mars'}]},
                     {'name': 'D', 'type': 'gcc', 'portals': [{'kind': 'lever', 'state': 'unsupported', 'scope': 'unknown'}]},
                     {'name': 'E', 'type': 'gcc', 'portals': 'workday'},
                     {'name': 'F', 'type': 'bank'}, 'junk']
        self.companies.write_text(json.dumps({'companies': companies}), encoding='utf-8')
        self.targets.write_text(json.dumps({'rows': [
            {'row': 1, 'original_name': 'A Ltd', 'employer': 'A', 'resolution': 'matched'},
            {'row': 2, 'original_name': 'X', 'employer': 'Missing', 'resolution': 'matched'},
            {'row': 3, 'original_name': 'Y', 'resolution': 'unresolved'},
            {'row': 4, 'original_name': 'Z', 'employer': 'A', 'resolution': 'guess'},
            {'row': 5}]}), encoding='utf-8')
        code, output = self.doctor()
        self.assertEqual(code, 1)
        for needle in ('a portal of A has no "kind"', "portal lever of B has an unknown state 'trusted'",
                       "portal lever of C has an unknown scope 'mars'", 'portal lever of D is unsupported and must say why',
                       '"portals" of E must be a list', "F has an unknown type 'bank'", '1 entries are not objects',
                       "employer 'Missing' is not in companies.json", 'an unresolved target must give its reason',
                       "unknown resolution 'guess'", 'every row needs an "original_name"'):
            self.assertIn(needle, output)

    def test_doctor_validates_the_detail_budget(self):
        config = self.data.parent / 'config.json'
        with mock.patch.object(self.cli, 'CONFIG_PATH', config):
            for value, good in ((120, True), (40.0, True), (0, False), (-5, False), ('many', False), (True, False), (None, False)):
                config.write_text(json.dumps({'portals': {'detail_budget_per_board': value}}), encoding='utf-8')
                code, output = self.doctor()
                self.assertEqual('detail_budget_per_board must be a positive number' in output, not good, value)
            config.write_text(json.dumps({'portals': 'lots'}), encoding='utf-8')
            self.assertIn('detail_budget_per_board must be a positive number', self.doctor()[1])
            config.write_text('{}', encoding='utf-8')                       # absent: the default of 120 applies
            self.assertIn('at most 120 new descriptions per run', self.doctor()[1])
        self.assertEqual(model.load_config(PROJECT / 'config.json')['portals'], {'detail_budget_per_board': 120})
        self.assertEqual(model.DEFAULT_CONFIG['portals'], {'detail_budget_per_board': 120})

    def test_doctor_without_targets_file(self):
        self.targets.unlink()
        code, output = self.doctor()
        self.assertEqual(code, 0, output)
        self.assertIn('targets.json is missing', output)
        self.targets.write_text('{"rows": 5}', encoding='utf-8')
        self.assertIn('targets.json must contain {"rows": [...]}', self.doctor()[1])



if __name__ == '__main__':
    unittest.main()
