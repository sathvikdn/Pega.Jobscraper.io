"""Offline integration regressions for the complete directory and saved search results."""
import copy
import csv
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / '.deps'))
sys.path.insert(0, str(BASE))

import app as portal_app
from opportunity_data import normalize_opportunity, salary_bucket


class SalaryClassificationTests(unittest.TestCase):
    def test_explicit_annual_inr_ctc_threshold_boundaries(self):
        for minimum, maximum, expected in (
            (2000000, 2500000, 'meets_target'),
            (1500000, 2000000, 'overlaps_target'),
            (1500000, 1999999, 'below_target'),
        ):
            with self.subTest(minimum=minimum, maximum=maximum):
                salary = {'currency': 'INR', 'period': 'annual', 'basis': 'total_compensation', 'amount_min': minimum, 'amount_max': maximum}
                self.assertEqual(salary_bucket(salary, 20), expected)
        self.assertEqual(salary_bucket({'currency': 'INR', 'period': 'annual', 'basis': 'ctc', 'amount_min': 2400000, 'amount_max': 2700000}, 25), 'overlaps_target')

    def test_fixed_or_ambiguous_pay_does_not_claim_confirmed_ctc(self):
        for basis in ('fixed', 'reported_salary', 'unknown', None):
            with self.subTest(basis=basis):
                self.assertEqual(salary_bucket({'currency': 'INR', 'period': 'annual', 'basis': basis, 'amount_min': 2500000, 'amount_max': 3000000}), 'basis_unknown')
        self.assertEqual(salary_bucket(None), 'undisclosed')
        self.assertEqual(salary_bucket({'currency': 'INR', 'period': 'annual', 'basis': 'ctc', 'amount_min': None, 'amount_max': None}), 'undisclosed')

    def test_missing_period_does_not_imply_annual_ctc(self):
        self.assertEqual(salary_bucket({'currency': 'INR', 'basis': 'ctc', 'amount_min': 2500000, 'amount_max': 3000000}), 'basis_unknown')

    def test_foreign_or_missing_currency_is_not_assumed_to_be_rupees(self):
        salary = {'basis': 'ctc', 'period': 'annual', 'amount_min': 2500000, 'amount_max': 3000000}
        self.assertEqual(salary_bucket(dict(salary, currency='USD')), 'foreign_currency')
        self.assertEqual(salary_bucket(salary), 'basis_unknown')

    def test_monthly_or_reversed_amounts_do_not_meet_annual_target(self):
        self.assertEqual(salary_bucket({'currency': 'INR', 'period': 'monthly', 'basis': 'ctc', 'amount_min': 2500000, 'amount_max': 3000000}), 'basis_unknown')
        self.assertEqual(salary_bucket({'currency': 'INR', 'period': 'annual', 'basis': 'ctc', 'amount_min': 3000000, 'amount_max': 2000000}), 'basis_unknown')

    def test_normalized_candidate_does_not_invent_pay_or_remote_eligibility(self):
        original = {'title': 'Senior Pega Developer', 'url': 'https://www.linkedin.com/jobs/view/333?trk=feed'}
        target = {'target_id': 'global-example', 'name': 'Example', 'category': 'global', 'location': 'United States'}
        normalized = normalize_opportunity(original, 'campaign', target)
        self.assertIsNone(normalized['salary'])
        self.assertEqual(normalized['pay_bucket'], 'undisclosed')
        self.assertEqual(normalized['remote_eligibility'], 'unknown')
        self.assertEqual(normalized['status'], 'candidate')
        self.assertEqual(normalized['company'], 'Example')
        self.assertNotIn('company', original)


class ImmediateThread:
    def __init__(self, target, args=(), daemon=None):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)


class ExpandedPortalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use every actual target and member array, not a fabricated category count.
        cls.directory_fixture_text = (BASE / 'research' / 'directory.json').read_text(encoding='utf-8')
        cls.directory_fixture = json.loads(cls.directory_fixture_text)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='pega-expanded-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.research, self.data = self.root / 'research', self.root / 'data'
        self.research.mkdir()
        (self.research / 'directory.json').write_text(self.directory_fixture_text, encoding='utf-8')
        self.curated = {
            'id': 'curated-111', 'title': 'Senior Pega Developer', 'company': 'Curated Employer',
            'url': 'https://www.linkedin.com/jobs/view/111', 'location': 'Bengaluru',
            'status': 'open', 'checked_at': '2026-09-07', 'fit': 'strong',
            'summary': 'Employer-reviewed original description',
            'salary': {'currency': 'INR', 'period': 'annual', 'basis': 'total_compensation', 'amount_min': 2400000, 'amount_max': 2700000},
        }
        self.expanded = {
            'id': 'expanded-222', 'title': 'Integration Engineer', 'company': 'Expanded Employer',
            'url': 'https://jobs.example.com/roles/222', 'location': 'Bengaluru',
            'status': 'indexed_only', 'checked_at': '2026-09-07',
        }
        self.candidate = {'title': 'Pega Developer', 'url': 'https://www.linkedin.com/jobs/search/?currentJobId=333&keywords=pega', 'source': 'LinkedIn'}
        self.target = {
            'target_id': 'gcc-wells-fargo', 'name': 'Wells Fargo', 'category': 'gcc', 'location': 'India',
            'status': 'completed', 'checked_at': '2026-09-08T10:00:00Z',
            'source_url': 'https://www.linkedin.com/jobs/search/?keywords=pega+wells+fargo',
            'diagnostics': [{'source': 'LinkedIn', 'status': 'collected'}],
            'jobs': [dict(self.curated, id='campaign-duplicate', company='Wrong search attribution', url='https://in.linkedin.com/jobs/view/pega-role-111?trk=feed'), self.candidate],
        }
        self.write_json('openings.json', {'opportunities': [self.curated]})
        self.write_json('expanded_openings.json', {'opportunities': [dict(self.curated, id='expanded-duplicate', summary='Weaker duplicated description', url='https://www.linkedin.com/jobs/search/?currentJobId=111'), self.expanded]})
        self.write_json('preloaded_search.json', {'status': 'completed', 'coverage': {'total': 313, 'checked': 1}, 'targets': [self.target]})
        self.application = self.new_app()
        self.client = self.application.test_client()
        self.headers = {'X-Career-Token': self.client.get('/api/bootstrap').get_json()['token']}
        network = patch('requests.sessions.Session.request', side_effect=AssertionError('Regression tests must not access the network'))
        network.start()
        self.addCleanup(network.stop)
        dns = patch('socket.getaddrinfo', side_effect=AssertionError('Regression tests must not resolve network hosts'))
        dns.start()
        self.addCleanup(dns.stop)
        self.fake_campaign = types.ModuleType('campaign')
        self.fake_campaign.run_campaign = Mock(return_value=None)
        campaign_patch = patch.dict(sys.modules, {'campaign': self.fake_campaign})
        campaign_patch.start()
        self.addCleanup(campaign_patch.stop)

    def new_app(self):
        application = portal_app.create_app(data_dir=self.data, research_dir=self.research)
        application.config['TESTING'] = True
        return application

    def write_json(self, name, data):
        (self.research / name).write_text(json.dumps(data), encoding='utf-8')

    def post(self, path, payload):
        return self.client.post(path, json=payload, headers=self.headers)

    def jobs(self, client=None):
        return (client or self.client).get('/api/opportunities').get_json()['opportunities']

    def test_merge_keeps_curated_record_for_duplicate_canonical_url(self):
        jobs = self.jobs()
        self.assertEqual(len(jobs), 3)
        by_url = {job['url']: job for job in jobs}
        curated = by_url[self.curated['url']]
        self.assertEqual(curated['id'], 'curated-111')
        self.assertEqual(curated['company'], 'Curated Employer')
        self.assertEqual(curated['summary'], self.curated['summary'])
        self.assertEqual(curated['salary'], self.curated['salary'])
        self.assertEqual(curated['status'], 'open')
        self.assertEqual(by_url[self.expanded['url']]['id'], 'expanded-222')
        campaign = by_url['https://www.linkedin.com/jobs/view/333']
        self.assertEqual(campaign['origin'], 'campaign')
        self.assertEqual(campaign['target_id'], 'gcc-wells-fargo')
        self.assertEqual(campaign['status'], 'candidate')

    def test_campaign_candidate_pipeline_survives_restart_and_is_exported(self):
        candidate = next(job for job in self.jobs() if job['origin'] == 'campaign')
        notes = '=SUM(1,2)\nAsk about integration ownership'
        response = self.post('/api/pipeline/' + candidate['id'], {'stage': 'shortlisted', 'notes': notes})
        self.assertEqual(response.status_code, 200)
        restarted = self.new_app().test_client()
        saved = next(job for job in self.jobs(restarted) if job['id'] == candidate['id'])
        self.assertEqual(saved['pipeline']['stage'], 'shortlisted')
        self.assertEqual(saved['pipeline']['notes'], notes)
        exported = list(csv.DictReader(io.StringIO(restarted.get('/api/export').data.decode('utf-8-sig'), newline='')))
        row = next(row for row in exported if row['Employer URL'] == candidate['url'])
        self.assertEqual(row['Pipeline'], 'shortlisted')
        self.assertEqual(row['Notes'], "'" + notes)
        self.assertEqual(row['Checked'], self.target['checked_at'])

    def test_directory_preserves_every_target_member_array_and_size_estimate(self):
        response = self.client.get('/api/directory')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        actual = {record['target_id']: record for record in data['records']}
        expected = {record['target_id']: record for record in self.directory_fixture['records']}
        self.assertEqual(set(actual), set(expected))
        self.assertEqual(len(actual), 313)
        self.assertNotIn('historical_snapshots', data)
        for key, original in expected.items():
            with self.subTest(target_id=key):
                self.assertEqual(actual[key]['keywords'], original['keywords'])
                snapshot = original.get('team_snapshot')
                if snapshot:
                    returned = actual[key]['team_snapshot']
                    self.assertEqual(returned['team_members'], snapshot['team_members'])
                    self.assertEqual(returned['team_size'], snapshot['team_size'])
                    self.assertEqual(returned['_provenance'], snapshot['_provenance'])
                    self.assertNotIn('_source_records', returned)
        # API projection must not delete full provenance from the saved artifact.
        source = json.loads((self.research / 'directory.json').read_text(encoding='utf-8'))
        self.assertIn('historical_snapshots', source)
        self.assertTrue(any('_source_records' in row.get('team_snapshot', {}) for row in source['records'] if row.get('team_snapshot')))

    def test_directory_exposes_latest_check_and_keeps_unchecked_targets_pending(self):
        records = self.client.get('/api/directory').get_json()['records']
        checked = next(r for r in records if r['target_id'] == self.target['target_id'])
        self.assertEqual(checked['latest_search']['checked_at'], self.target['checked_at'])
        self.assertEqual(checked['latest_search']['diagnostics'], self.target['diagnostics'])
        self.assertEqual(checked['opportunity_count'], len(self.target['jobs']))
        for record in records:
            if record['target_id'] != self.target['target_id']:
                self.assertEqual(record['latest_search']['status'], 'pending')

    def test_campaign_endpoint_summarizes_jobs_without_dropping_targets(self):
        campaign = self.client.get('/api/campaign').get_json()
        self.assertEqual(campaign['targets'][0]['target_id'], self.target['target_id'])
        self.assertEqual(campaign['targets'][0]['job_count'], len(self.target['jobs']))
        self.assertNotIn('jobs', campaign['targets'][0])
        self.assertEqual(campaign['coverage'], {'total': 313, 'checked': 1})

    def test_search_sends_all_exact_category_target_ids_and_returns_matching_total(self):
        for category in ('all', 'gcc', 'services', 'global'):
            expected = [r['target_id'] for r in self.directory_fixture['records'] if category == 'all' or r['category'] == category]
            with self.subTest(category=category), patch.object(portal_app.threading, 'Thread', ImmediateThread):
                self.fake_campaign.run_campaign.reset_mock()
                response = self.post('/api/search', {'category': category, 'minimum_ctc_lpa': 24, 'role_scope': 'broad'})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json()['total'], len(expected))
                kwargs = self.fake_campaign.run_campaign.call_args.kwargs
                self.assertEqual(kwargs['target_ids'], expected)
                self.assertTrue(kwargs['force'])
                self.assertFalse(kwargs['stop_event'].is_set())

    def test_resume_passes_force_false_and_search_preferences_persist(self):
        with patch.object(portal_app.threading, 'Thread', ImmediateThread):
            response = self.post('/api/search', {'category': 'global', 'minimum_ctc_lpa': 25.5, 'role_scope': 'pega', 'resume': True})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.fake_campaign.run_campaign.call_args.kwargs['force'])
        restarted = self.new_app().test_client()
        self.assertEqual(restarted.get('/api/bootstrap').get_json()['search_preferences'], {'category': 'global', 'minimum_ctc_lpa': 25.5, 'role_scope': 'pega'})

    def test_search_rejects_invalid_scope_and_ctc_without_starting_worker(self):
        invalid = [
            {'category': 'unknown'}, {'category': []}, {'role_scope': 'only-management'},
            {'minimum_ctc_lpa': True}, {'minimum_ctc_lpa': '24'}, {'minimum_ctc_lpa': -1},
            {'minimum_ctc_lpa': 201}, {'minimum_ctc_lpa': float('nan')}, {'minimum_ctc_lpa': float('inf')},
        ]
        with patch.object(portal_app.threading, 'Thread') as thread:
            for payload in invalid:
                with self.subTest(payload=payload):
                    self.assertEqual(self.post('/api/search', payload).status_code, 400)
            thread.assert_not_called()
        self.assertFalse(self.client.get('/api/status').get_json()['running'])

    def test_search_requires_a_directory_and_valid_json_object(self):
        for body in ('null', '[]', '{broken'):
            with self.subTest(body=body):
                self.assertEqual(self.client.post('/api/search', data=body, content_type='application/json', headers=self.headers).status_code, 400)
        self.write_json('directory.json', {'records': [], 'stats': {}})
        with patch.object(portal_app.threading, 'Thread') as thread:
            self.assertEqual(self.post('/api/search', {'category': 'all'}).status_code, 400)
            thread.assert_not_called()

    def test_search_lock_and_pause_reach_mocked_campaign_stop_event(self):
        self.assertEqual(self.post('/api/search/pause', {}).status_code, 409)
        with patch.object(portal_app.threading, 'Thread') as thread:
            self.assertEqual(self.post('/api/search', {'category': 'all'}).status_code, 200)
            self.assertEqual(self.post('/api/search', {'category': 'gcc'}).status_code, 409)
            self.assertEqual(self.post('/api/recheck', {'ids': ['curated-111']}).status_code, 409)
            self.assertEqual(self.post('/api/search/pause', {}).status_code, 200)
            target = thread.call_args.kwargs['target']
            arguments = thread.call_args.kwargs['args']
        target(*arguments)
        kwargs = self.fake_campaign.run_campaign.call_args.kwargs
        self.assertTrue(kwargs['stop_event'].is_set())
        self.assertFalse(self.client.get('/api/status').get_json()['running'])
        self.assertEqual(self.post('/api/search/pause', {}).status_code, 409)

    def test_campaign_progress_and_failures_are_visible_and_release_task_lock(self):
        def campaign(**kwargs):
            kwargs['progress']({'coverage': {'checked': 7, 'total': len(kwargs['target_ids'])}, 'current_company': 'Example'})
            raise RuntimeError('mock campaign failure')
        self.fake_campaign.run_campaign.side_effect = campaign
        with patch.object(portal_app.threading, 'Thread', ImmediateThread):
            self.assertEqual(self.post('/api/search', {'category': 'all'}).status_code, 200)
        status = self.client.get('/api/status').get_json()
        self.assertEqual(status['progress'], 7)
        self.assertEqual(status['total'], len(self.directory_fixture['records']))
        self.assertFalse(status['running'])
        self.assertIn('mock campaign failure', status['error'])


if __name__ == '__main__':
    unittest.main()
