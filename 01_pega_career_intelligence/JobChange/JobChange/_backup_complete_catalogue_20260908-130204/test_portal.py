"""Offline regression tests for job evidence, local persistence and API contracts.

Run from portal with the bundled Python: python -B -m unittest test_portal -v
All API data is temporary. No scanner module or real network request is used.
"""
import copy
import csv
import io
import json
import sys
import tempfile
import types
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / '.deps'))
sys.path.insert(0, str(BASE))

import app as portal_app
from quality import canonical_url, effective_status, employer_matches, job_identity
from verification import classify_page


TODAY = date(2026, 9, 7)
TITLE = 'Senior Pega Developer'


def job_page(jobs=None, heading=TITLE, controls='<a href="/apply/123">Apply now</a>', body='Pega and PRPC delivery'):
    structured = '' if jobs is None else '<script type="application/ld+json">' + json.dumps(jobs) + '</script>'
    return f'<html><h1>{heading}</h1><p>{body}</p>{structured}{controls}</html>'


class IdentityAndStatusTests(unittest.TestCase):
    def test_linkedin_slug_and_selected_search_job_have_one_identity(self):
        variants = [
            'https://in.linkedin.com/jobs/view/senior-pega-developer-at-example-1234567890?trk=public_jobs',
            'https://www.linkedin.com/jobs/view/1234567890/',
            'https://www.linkedin.com/jobs/search/?keywords=pega&currentJobId=1234567890',
        ]
        self.assertEqual({canonical_url(url) for url in variants}, {'https://www.linkedin.com/jobs/view/1234567890'})
        self.assertEqual(len({job_identity(TITLE, 'Example', url) for url in variants}), 1)

    def test_distinct_linkedin_selected_jobs_do_not_merge(self):
        first = 'https://www.linkedin.com/jobs/search/?currentJobId=123'
        second = 'https://www.linkedin.com/jobs/search/?currentJobId=456'
        self.assertNotEqual(job_identity(TITLE, 'Example', first), job_identity(TITLE, 'Example', second))

    def test_identity_bearing_query_parameters_survive_tracking_cleanup(self):
        self.assertEqual(canonical_url('https://jobs.example.com/job?ref=123&utm_source=email&trk=feed'), 'https://jobs.example.com/job?ref=123')
        self.assertNotEqual(canonical_url('https://jobs.example.com/job?ref=123'), canonical_url('https://jobs.example.com/job?ref=456'))
        self.assertEqual(canonical_url('https://in.indeed.com/viewjob?utm_campaign=x&jk=abc123'), 'https://in.indeed.com/viewjob?jk=abc123')

    def test_untrusted_url_schemes_and_credentials_are_rejected(self):
        for value in ('javascript:alert(1)', 'file:///C:/secret', 'https://user:pass@example.com/job', None):
            with self.subTest(value=value):
                self.assertEqual(canonical_url(value), '')
        self.assertTrue(canonical_url('https://linkedin.com.example.org/jobs/view/123').startswith('https://linkedin.com.example.org/'))

    def test_citi_does_not_match_first_citizens(self):
        company = {'name': 'Citi India', 'keywords': ['citi', 'citibank']}
        self.assertFalse(employer_matches('First Citizens Bank', company))
        self.assertTrue(employer_matches('Citi', company))
        self.assertTrue(employer_matches('Citibank India', company))

    def test_pega_product_keyword_does_not_identify_employer(self):
        company = {'name': 'Pegasystems', 'keywords': ['pegasystems', 'pega']}
        self.assertFalse(employer_matches('Expert Pega Consulting', company))
        self.assertTrue(employer_matches('Pegasystems India', company))

    def test_expired_deadline_overrides_even_an_open_recheck(self):
        record = {'status': 'open', 'closing_at': '2026-09-06T23:59:00Z'}
        self.assertEqual(effective_status(record, {'status': 'open', 'checked_at': '2026-09-07'}, TODAY), 'closed')

    def test_closing_today_is_not_prematurely_closed(self):
        self.assertEqual(effective_status({'status': 'open', 'closing_at': '2026-09-07'}, today=TODAY), 'open')

    def test_failed_recheck_does_not_prove_closure(self):
        self.assertEqual(effective_status({'status': 'open'}, {'status': 'unavailable'}, TODAY), 'uncertain')


class VerificationTests(unittest.TestCase):
    def status(self, html):
        return classify_page(html, TITLE, TODAY)[0]

    def test_exact_structured_role_and_apply_control_are_open(self):
        self.assertEqual(self.status(job_page({'@type': 'JobPosting', 'title': TITLE, 'validThrough': '2026-09-30'})), 'open')

    def test_matching_structured_expiry_is_closed(self):
        self.assertEqual(self.status(job_page({'@type': 'JobPosting', 'title': TITLE, 'validThrough': '2026-09-06'})), 'closed')

    def test_unrelated_structured_job_cannot_open_or_close_saved_role(self):
        for expiry in ('2026-09-30', '2026-09-01'):
            with self.subTest(expiry=expiry):
                html = job_page({'@type': 'JobPosting', 'title': 'Finance Manager', 'validThrough': expiry})
                self.assertEqual(self.status(html), 'uncertain')

    def test_multiple_jobs_are_uncertain_even_when_one_matches(self):
        html = job_page({'@graph': [
            {'@type': 'JobPosting', 'title': 'Finance Manager', 'validThrough': '2026-09-01'},
            {'@type': 'JobPosting', 'title': TITLE, 'validThrough': '2026-09-30'},
        ]})
        self.assertEqual(self.status(html), 'uncertain')

    def test_apply_text_without_an_application_control_is_insufficient(self):
        html = job_page({'@type': 'JobPosting', 'title': TITLE}, controls='', body='Pega candidates may apply after a role opens.')
        self.assertEqual(self.status(html), 'uncertain')

    def test_exact_unstructured_heading_and_submit_control_can_confirm_role(self):
        self.assertEqual(self.status(job_page(controls='<input type="submit" value="Apply now">')), 'open')

    def test_search_body_mention_does_not_match_a_different_heading(self):
        self.assertEqual(self.status(job_page(heading='Search jobs', body=TITLE)), 'uncertain')

    def test_explicit_vacancy_closure_is_closed(self):
        self.assertEqual(self.status(job_page(body='This job is no longer available.')), 'closed')


class ImmediateThread:
    """Run a mocked worker synchronously so completion assertions are deterministic."""
    def __init__(self, target, args=(), daemon=None):
        self.target = target
        self.args = args

    def start(self):
        self.target(*self.args)


class PortalApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pega-portal-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.research = self.root / 'research'
        self.research.mkdir()
        self.data = self.root / 'data'
        self.rows = [{
            'id': 'example-123', 'company': 'Example', 'title': TITLE,
            'location': 'Bengaluru', 'url': 'https://www.linkedin.com/jobs/view/123',
            'status': 'open', 'checked_at': '2026-09-07', 'closing_at': None,
            'experience_min': 4, 'fit': 'strong',
        }]
        self.write_research(self.rows)
        self.app = self.new_app()
        self.client = self.app.test_client()
        self.headers = {'X-Career-Token': self.client.get('/api/bootstrap').get_json()['token']}
        # Catch accidental network use instead of silently reaching public sites.
        self.addCleanup(patch.stopall)
        patch('requests.sessions.Session.request', side_effect=AssertionError('Tests must not use the network')).start()
        patch('socket.getaddrinfo', side_effect=AssertionError('Tests must not resolve network hosts')).start()
        hunter = types.ModuleType('pega_job_hunter')
        hunter.COMPANIES = [{'name': 'Example', 'keywords': ['example']}]
        hunter.CONSULTING_COMPANIES = []
        hunter.REMOTE_GLOBAL_COMPANIES = []
        patch.dict(sys.modules, {'pega_job_hunter': hunter}).start()

    def new_app(self):
        application = portal_app.create_app(data_dir=self.data, research_dir=self.research)
        application.config['TESTING'] = True
        return application

    def write_research(self, rows):
        (self.research / 'openings.json').write_text(json.dumps({'opportunities': rows}), encoding='utf-8')

    def post(self, path, payload):
        return self.client.post(path, json=payload, headers=self.headers)

    def opportunities(self, client=None):
        return (client or self.client).get('/api/opportunities').get_json()['opportunities']

    def test_non_object_and_malformed_json_are_400_on_all_mutation_routes(self):
        for path in ('/api/pipeline/example-123', '/api/recheck', '/api/scan'):
            for body in ('null', '[]', '"text"', '42', '{broken'):
                with self.subTest(path=path, body=body):
                    response = self.client.post(path, data=body, content_type='application/json', headers=self.headers)
                    self.assertEqual(response.status_code, 400)
                    self.assertIn('error', response.get_json())
        self.assertEqual(self.opportunities()[0]['pipeline']['stage'], 'unreviewed')

    def test_invalid_stages_and_notes_are_400(self):
        for stage in ([], {}, None, 42, 'invented'):
            with self.subTest(stage=stage):
                self.assertEqual(self.post('/api/pipeline/example-123', {'stage': stage}).status_code, 400)
        for notes in ([], None, 'x' * 4001):
            with self.subTest(notes_type=type(notes).__name__):
                self.assertEqual(self.post('/api/pipeline/example-123', {'stage': 'applied', 'notes': notes}).status_code, 400)

    def test_unknown_opportunity_cannot_be_saved(self):
        self.assertEqual(self.post('/api/pipeline/missing', {'stage': 'applied'}).status_code, 404)

    def test_mutations_require_token_json_and_same_origin(self):
        self.assertEqual(self.client.post('/api/recheck', json={'ids': ['example-123']}).status_code, 403)
        self.assertEqual(self.client.post('/api/recheck', data='ids=example-123', headers=self.headers).status_code, 415)
        headers = dict(self.headers, Origin='https://unrelated.example')
        self.assertEqual(self.client.post('/api/recheck', json={'ids': ['example-123']}, headers=headers).status_code, 403)

    def test_pipeline_survives_a_new_application_instance(self):
        notes = 'Discuss integration ownership.\nSalary expectation: 24–27 LPA.'
        self.assertEqual(self.post('/api/pipeline/example-123', {'stage': 'shortlisted', 'notes': notes}).status_code, 200)
        restarted = self.new_app().test_client()
        saved = self.opportunities(restarted)[0]['pipeline']
        self.assertEqual((saved['stage'], saved['notes']), ('shortlisted', notes))
        self.assertTrue(saved['updated_at'])
        self.assertEqual(restarted.post('/api/pipeline/example-123', json={'stage': 'applied'}, headers=self.headers).status_code, 403)

    def test_api_deduplicates_tracking_variants_but_retains_distinct_jobs(self):
        duplicate = dict(self.rows[0], id='duplicate', url='https://in.linkedin.com/jobs/view/senior-pega-123?trk=feed')
        selected = dict(self.rows[0], id='selected-456', url='https://www.linkedin.com/jobs/search/?currentJobId=456')
        self.write_research(self.rows + [duplicate, selected])
        rows = self.opportunities()
        self.assertEqual(len(rows), 2)
        self.assertEqual({row['url'] for row in rows}, {'https://www.linkedin.com/jobs/view/123', 'https://www.linkedin.com/jobs/view/456'})

    def test_csv_escapes_formula_prefixes_without_altering_stored_notes(self):
        for prefix in ('=', '+', '-', '@', '\t', '\r'):
            notes = prefix + 'SUM(1,2)\nsecond line'
            with self.subTest(prefix=repr(prefix)):
                self.assertEqual(self.post('/api/pipeline/example-123', {'stage': 'shortlisted', 'notes': notes}).status_code, 200)
                response = self.client.get('/api/export')
                self.assertEqual(response.status_code, 200)
                self.assertIn('attachment', response.headers['Content-Disposition'])
                rows = list(csv.DictReader(io.StringIO(response.data.decode('utf-8-sig'), newline='')))
                self.assertEqual(rows[0]['Notes'], "'" + notes)
                self.assertEqual(self.opportunities()[0]['pipeline']['notes'], notes)

    def test_csv_also_escapes_untrusted_source_fields(self):
        self.write_research([dict(self.rows[0], company='=HYPERLINK("https://example.org")', title='@SUM(1,2)')])
        rows = list(csv.DictReader(io.StringIO(self.client.get('/api/export').data.decode('utf-8-sig'))))
        self.assertTrue(rows[0]['Company'].startswith("'="))
        self.assertTrue(rows[0]['Role'].startswith("'@"))

    def test_recheck_lock_blocks_another_recheck_and_a_discovery_scan(self):
        with patch.object(portal_app.threading, 'Thread') as thread:
            self.assertEqual(self.post('/api/recheck', {'ids': ['example-123']}).status_code, 200)
            self.assertEqual(self.post('/api/recheck', {'ids': ['example-123']}).status_code, 409)
            self.assertEqual(self.post('/api/scan', {'companies': ['Example']}).status_code, 409)
            thread.assert_called_once()
            thread.return_value.start.assert_called_once()
        self.assertTrue(self.client.get('/api/status').get_json()['running'])

    def test_discovery_lock_also_blocks_rechecks(self):
        with patch.object(portal_app.threading, 'Thread') as thread:
            self.assertEqual(self.post('/api/scan', {'companies': ['Example']}).status_code, 200)
            self.assertEqual(self.post('/api/recheck', {'ids': ['example-123']}).status_code, 409)
            thread.assert_called_once()

    def test_recheck_completion_persists_result_and_releases_lock(self):
        result = {'status': 'unavailable', 'checked_at': '2026-09-07T12:00:00Z', 'detail': 'Mock source unavailable'}
        with patch.object(portal_app, 'recheck', return_value=result) as recheck, patch.object(portal_app.threading, 'Thread', ImmediateThread):
            self.assertEqual(self.post('/api/recheck', {'ids': ['example-123']}).status_code, 200)
            recheck.assert_called_once()
        state = self.client.get('/api/status').get_json()
        self.assertFalse(state['running'])
        self.assertEqual(state['progress'], 1)
        self.assertIsNone(state['error'])
        reopened = self.new_app().test_client()
        row = self.opportunities(reopened)[0]
        self.assertEqual(row['verification'], result)
        self.assertEqual(row['status'], 'uncertain')
        self.assertFalse(reopened.get('/api/status').get_json()['running'])

    def test_recheck_worker_exception_releases_lock_and_records_failure(self):
        with patch.object(portal_app, 'recheck', side_effect=RuntimeError('mock parser failure')), patch.object(portal_app.threading, 'Thread', ImmediateThread):
            self.assertEqual(self.post('/api/recheck', {'ids': ['example-123']}).status_code, 200)
        state = self.client.get('/api/status').get_json()
        self.assertFalse(state['running'])
        self.assertIn('mock parser failure', state['error'])
        with patch.object(portal_app.threading, 'Thread'):
            self.assertEqual(self.post('/api/recheck', {'ids': ['example-123']}).status_code, 200)


if __name__ == '__main__':
    unittest.main()
