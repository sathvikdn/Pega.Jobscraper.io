import contextlib
import io
import json
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / '.deps'))
sys.path.insert(0, str(BASE))
import app
import campaign
import job_runner
import portal_scan


def target(identifier, category='gcc', priority='top30', location='India'):
    return {'target_id': str(identifier), 'name': 'Employer ' + str(identifier),
            'category': category, 'priority': priority, 'location': location,
            'keywords': ['Employer ' + str(identifier)]}


class JobRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.research = self.root / 'research'
        self.research.mkdir()
        self.records = [target(i) for i in range(25)] + [target('si', 'services', 'si_top'), target('us', 'global', 'remote_top', 'United States')]
        self.write('directory.json', {'records': self.records})
        company = {'id': 'fresh-company', 'name': 'Fresh Company', 'category': 'gcc',
                   'aliases': [], 'flags': {}, 'claims': [], 'people': [], 'hiring_signals': []}
        self.write('independent_map.json', {'companies': [company], 'people': [], 'stats': {}})
        restored = {**company, 'id': 'restored-company', 'name': 'Restored Company'}
        self.write('master_catalog.json', {'companies': [company, restored], 'people': [], 'stats': {}})
        self.application = app.create_app(self.root / 'data', self.research)
        self.calls = []

    def write(self, name, data):
        (self.research / name).write_text(json.dumps(data), encoding='utf-8')

    def scan(self, targets, records, output_path, progress, stop_event, force=True):
        self.calls.append((targets, records, force))
        document = {'targets': [{**row, 'status': 'no_matches', 'jobs': []} for row in targets]}
        campaign.save_campaign(document, output_path)
        progress({'target_id': targets[0]['target_id'], 'current_company': targets[0]['name']})

    def run_job(self, **kwargs):
        return job_runner.run_job(self.application, self.research, poll_seconds=0.01, **kwargs)

    def test_every_mode_has_exact_ui_counts_and_dry_run_starts_nothing(self):
        options = self.application.test_client().get('/api/scan-options').get_json()
        expected = {row['mode']: row['count'] for rows in options['categories'].values() for row in rows}
        self.assertEqual(options['total_targets'], 29)
        with patch.object(portal_scan, 'run_scan') as scan:
            for mode in portal_scan.MODE_CATEGORY:
                result = self.run_job(mode=mode, dry_run=True)
                self.assertEqual(result.exit_code, 0)
                self.assertEqual(result.summary['selected_targets'], expected[mode])
                self.assertEqual(result.summary['catalogue_targets'], options['total_targets'])
            scan.assert_not_called()
        self.assertIsNone(self.application.extensions['store'].get('meta', 'scanner_selection'))
        self.assertFalse((self.research / 'preloaded_search.json').exists())

    def test_completion_uses_current_and_restored_catalogue_and_persists_selection(self):
        with patch.object(portal_scan, 'run_scan', side_effect=self.scan):
            result = self.run_job(mode='gcc_all')
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.summary['selected_targets'], 27)
        selected, records, force = self.calls[0]
        self.assertTrue(force)
        self.assertIn('fresh-company', {row['target_id'] for row in selected})
        self.assertIn('restored-company', {row['target_id'] for row in selected})
        self.assertEqual(len(records), 29)
        self.assertEqual(result.summary['retained_job_candidates'], 0)
        saved = self.application.extensions['store'].get('meta', 'scanner_selection')
        self.assertEqual(saved['status'], 'complete')
        self.assertEqual(saved['mode'], 'gcc_all')
        self.assertIn('baseline_ids', saved)

    def test_resume_keeps_saved_selection_and_baseline_even_when_catalogue_changes(self):
        with patch.object(portal_scan, 'run_scan', side_effect=self.scan):
            first = self.run_job(mode='gcc_top10')
            self.assertEqual(first.exit_code, 0)
            store = self.application.extensions['store']
            saved = store.get('meta', 'scanner_selection')
            saved['baseline_ids'] = ['preserve-my-baseline']
            store.put('meta', 'scanner_selection', saved)
            self.write('directory.json', {'records': list(reversed(self.records))})
            preview = self.run_job(mode='all', resume=True, dry_run=True)
            result = self.run_job(mode='all', resume=True)
        self.assertEqual(preview.summary['mode'], 'gcc_top10')
        self.assertEqual(preview.summary['selected_targets'], 10)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(self.calls[1][0], self.calls[0][0])
        self.assertFalse(self.calls[1][2])
        self.assertEqual(store.get('meta', 'scanner_selection')['baseline_ids'], ['preserve-my-baseline'])

    def test_worker_exception_is_nonzero_with_saved_failure(self):
        with patch.object(portal_scan, 'run_scan', side_effect=OSError('Checkpoint unavailable')):
            result = self.run_job()
        self.assertEqual(result.exit_code, 1)
        self.assertIn('Checkpoint unavailable', result.summary['error'])
        self.assertEqual(self.application.extensions['store'].get('meta', 'scanner_selection')['status'], 'failed')

    def test_limited_pagination_is_reported_as_partial_not_success(self):
        rows=[{**self.records[0],'status':'no_matches','partial':True,'jobs':[]}]
        result=job_runner.selected_summary({'targets':rows},rows)
        self.assertEqual(result.exit_code,2)
        self.assertEqual(result.summary['partial_queries'],1)
        self.assertEqual(result.summary['outcome'],'partial')

    def test_all_blocked_is_failure_and_mixed_checks_are_partial(self):
        for statuses, expected in [(['blocked'] * 10, 3), (['error'] * 10, 3), (['blocked'] + ['no_matches'] * 9, 2)]:
            with self.subTest(statuses=statuses):
                def scan(targets, records, output_path, progress, stop_event, force=True):
                    document = {'targets': [{**row, 'status': status, 'jobs': []} for row, status in zip(targets, statuses)]}
                    campaign.save_campaign(document, output_path)
                with patch.object(portal_scan, 'run_scan', side_effect=scan):
                    result = self.run_job()
                self.assertEqual(result.exit_code, expected)
                self.assertNotEqual(result.summary['outcome'], 'completed')

    def test_description_gaps_and_missing_target_are_partial(self):
        targets = [target(1), target(2)]
        doc = {'targets': [{**targets[0], 'status': 'results', 'jobs': [{'url': 'https://example.com/jobs/1', 'job_detail_status': 'unavailable'}]}]}
        result = job_runner.selected_summary(doc, targets)
        self.assertEqual(result.exit_code, 2)
        self.assertEqual(result.summary['incomplete_queries'], 1)
        self.assertEqual(result.summary['description_outcomes'], {'unavailable': 1})

    def test_unselected_historical_failures_do_not_fail_current_job(self):
        targets = [target(1)]
        doc = {'targets': [{**targets[0], 'status': 'no_matches', 'jobs': []}, {**target('old'), 'status': 'blocked', 'jobs': []}]}
        self.assertEqual(job_runner.selected_summary(doc, targets).exit_code, 0)

    def test_signal_requests_pause_and_waits_for_saved_checkpoint(self):
        stop = job_runner.StopRequest()
        def scan(targets, records, output_path, progress, stop_event, force=True):
            stop.request(signal.SIGTERM)
            if not stop_event.wait(3):
                raise AssertionError('Pause did not reach the scanner')
            campaign.save_campaign({'targets': [{**row, 'status': 'pending', 'jobs': []} for row in targets]}, output_path)
        with patch.object(portal_scan, 'run_scan', side_effect=scan):
            result = self.run_job(stop=stop)
        self.assertEqual(result.exit_code, 143)
        self.assertEqual(result.summary['outcome'], 'paused')
        self.assertEqual(self.application.extensions['store'].get('meta', 'scanner_selection')['status'], 'paused')
        self.assertTrue((self.research / 'preloaded_search.json').exists())
        self.assertFalse(self.application.extensions['scan_state']['running'])

    def test_active_campaign_is_rejected_without_starting_a_second_worker(self):
        with campaign.campaign_lock(self.research / 'preloaded_search.json'):
            with patch.object(portal_scan, 'run_scan') as scan:
                with self.assertRaisesRegex(RuntimeError, 'already running'):
                    self.run_job()
                scan.assert_not_called()

    def test_resume_without_selection_is_actionable_error(self):
        with self.assertRaisesRegex(RuntimeError, 'No saved scan selection'):
            self.run_job(resume=True)

    def test_cli_dry_run_default_and_json_output_use_only_temporary_paths(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(portal_scan, 'run_scan') as scan:
            code = job_runner.main(['--research-dir', str(self.research), '--data-dir', str(self.root / 'cli-data'), '--dry-run'])
            scan.assert_not_called()
        last = json.loads(output.getvalue().splitlines()[-1])
        self.assertEqual(code, 0)
        self.assertEqual(last['mode'], 'gcc_top10')
        self.assertEqual(last['selected_targets'], 10)
        self.assertEqual(last['outcome'], 'dry_run')
        self.assertNotIn('token', output.getvalue())


if __name__ == '__main__':
    unittest.main()
