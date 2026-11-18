"""Tests for radar/server.py. Everything runs on 127.0.0.1 with an ephemeral port and a fake store."""

import contextlib
import csv
import http.client
import io
import json
import re
import shutil
import socket
import subprocess
import sys
import threading
import types
import unittest
from pathlib import Path
from unittest import mock

from radar import server
from radar.store import COVERAGE_COLUMNS

TOKEN = 'test-token-0123456789'
WEB_DIR = Path(__file__).resolve().parent.parent / 'web'
JOB = {
    'id': 'job-1', 'title': 'Pega Developer', 'company': 'Acme', 'employer_type': 'product', 'city': 'Bengaluru',
    'location': 'Bengaluru, Karnataka', 'is_bengaluru': True, 'url': 'https://example.invalid/job-1',
    'apply_url': None, 'experience_min': 3, 'experience_max': 6, 'salary_min_lpa': None, 'salary_max_lpa': None,
    'posted_at': '2026-11-10', 'first_seen_at': '2026-11-13T02:00:00+00:00',
    'last_seen_at': '2026-11-14T02:00:00+00:00', 'score': 88,
    'fit': {'reasons': ['Pega in title'], 'labels': {'employer_type': 'product', 'bengaluru': True}},
    'pega_title': True, 'pega_duty': True, 'saved': False, 'status': 'new', 'notes': '',
    'hidden': False, 'seen': False, 'sources': ['LinkedIn'], 'is_new': True,
}
COVERAGE_ROWS = [
    {'canonical': '=Booking.com', 'original_names': ['Booking.com India', '+Booking'], 'type': 'product', 'bengaluru': True,
     'career_url': 'https://example.invalid/careers',
     'portals': [{'kind': 'icims', 'state': 'candidate', 'scope': 'global', 'note': 'unverified'},
                 {'kind': 'workday', 'state': 'wrong_scope', 'scope': 'unknown'}],
     'linkedin_query': True, 'inventory_state': 'configured', 'last_attempt_at': '2026-11-15T02:00:00+00:00',
     'last_success_at': None, 'latest_status': 'blocked', 'latest_reason': 'http_4xx', 'latest_error': '-HTTP 403',
     'run_id': 'run-1', 'pages_complete': False, 'details_complete': None, 'jobs_total': 4, 'jobs_open': 3,
     'sources': [{'task': 'ats:icims:booking', 'status': 'blocked', 'reason': 'http_4xx', 'at': '2026-11-15T02:00:00+00:00',
                  'run_id': 'run-1'}],
     'next_action': '@Run verify'},
    {'canonical': None, 'original_names': ['Mystery Corp'], 'type': None, 'bengaluru': None, 'career_url': None,
     'portals': [], 'linkedin_query': False, 'inventory_state': 'identity unresolved', 'last_attempt_at': None,
     'last_success_at': None, 'latest_status': None, 'latest_reason': None, 'latest_error': None, 'run_id': None,
     'pages_complete': None, 'details_complete': None, 'jobs_total': 0, 'jobs_open': 0, 'sources': [],
     'next_action': 'Decide which employer this row means'},
]
VIEW_TOTALS = {'new': 1, 'all': 4, 'saved': 2, 'applied': 3, 'hidden': 5}


class FakeStore:
    path = Path('data-dir') / 'radar.sqlite3'

    def __init__(self):
        self.jobs_calls = []
        self.state_calls = []
        self.marked_all_seen = 0
        self.progress = None
        self.fail_jobs = False

    def jobs(self, **kwargs):
        if self.fail_jobs:
            raise RuntimeError('database is on fire')
        self.jobs_calls.append(kwargs)
        return [dict(JOB)], VIEW_TOTALS[kwargs['view']]

    def job(self, job_id):
        if job_id != JOB['id']:
            return None
        return dict(JOB, description='Build Pega case types.', sightings=[])

    def set_state(self, job_id, **changes):
        if job_id != JOB['id']:
            return None
        self.state_calls.append(changes)
        return {'saved': False, 'status': 'new', 'notes': '', 'hidden': False, 'seen': False, **changes}

    def mark_all_seen(self):
        self.marked_all_seen += 1
        return 7

    def latest_run(self):
        return {'id': 'run-1', 'started_at': '2026-11-14T02:00:00+00:00', 'finished_at': '2026-11-14T02:04:00+00:00',
                'status': 'partial', 'summary': {'new': 1},
                'health': [{'source': 'linkedin', 'label': 'LinkedIn', 'kind': 'linkedin', 'status': 'partial',
                            'found': 40, 'kept': 12, 'requests': 30, 'error': 'rate limited'}],
                'last_attempt': {'id': 'run-2', 'status': 'failed', 'finished_at': '2026-11-14T08:00:00+00:00',
                                 'error': 'no sources are configured'}}

    def latest_coverage_run(self):
        return {**self.latest_run(), 'later_runs': ['run-3']}

    def stats(self):
        return {'total': 1, 'new': 1, 'new_bengaluru': 1, 'new_product_gcc': 1, 'saved': 0, 'applied': 0, 'hidden': 0}

    def kv_get(self, key, default=None):
        return self.progress if key == 'scan_progress' else default

    def export_rows(self):
        return [
            {'title': '=HYPERLINK("http://evil.invalid")', 'company': '+1', 'notes': '-2', 'status': '@x',
             'city': '\tTab', 'location': '\rCR', 'score': -5, 'saved': True, 'sources': ['LinkedIn', 'Hirist']},
            {'title': 'Pega Developer – Bengaluru', 'company': 'Acme', 'notes': None, 'status': 'new',
             'city': 'Bengaluru', 'location': 'Bengaluru', 'score': 88, 'saved': False, 'sources': []},
        ]


class FakeScanController:
    def __init__(self):
        self.running = False
        self.modes = []

    def start(self, mode='full'):
        if self.running:
            return False
        self.running = True
        self.modes.append(mode)
        return True

    def status(self):
        return {'running': self.running, 'mode': self.modes[-1] if self.modes else None, 'progress': None,
                'last_summary': None, 'error': None}


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.store = FakeStore()
        self.controller = FakeScanController()
        handler = server.make_handler(self.store, {'profile': {'name': 'Tester'}}, TOKEN, self.controller)
        self.httpd = server.LoopbackServer((server.BIND_HOST, 0), handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)

    def call(self, method, path, *, headers=None, body=None, host=None):
        """One raw request. Returns (status, headers, body bytes)."""
        conn = http.client.HTTPConnection(server.BIND_HOST, self.port, timeout=5)
        try:
            conn.putrequest(method, path, skip_host=True)
            conn.putheader('Host', host if host is not None else f'127.0.0.1:{self.port}')
            for name, value in (headers or {}).items():
                conn.putheader(name, value)
            if body is not None:
                conn.putheader('Content-Length', str(len(body)))
            conn.endheaders(body)
            response = conn.getresponse()
            return response.status, response.headers, response.read()
        finally:
            conn.close()

    def get_json(self, path, **kwargs):
        status, _, body = self.call('GET', path, **kwargs)
        return status, json.loads(body)

    def post(self, path, payload, *, raw=None, **overrides):
        headers = {'X-Radar-Token': TOKEN, 'Content-Type': 'application/json'}
        for name, value in overrides.items():
            name = name.replace('_', '-')
            if value is None:
                headers.pop(name, None)
            else:
                headers[name] = value
        body = raw if raw is not None else json.dumps(payload).encode('utf-8')
        status, _, response = self.call('POST', path, headers=headers, body=body)
        return status, json.loads(response)


class BindingTests(ServerTestCase):
    def test_bind_address_is_loopback_constant(self):
        self.assertEqual(server.BIND_HOST, '127.0.0.1')
        self.assertEqual(self.httpd.server_address[0], '127.0.0.1')

    def test_serve_has_no_host_parameter(self):
        names = server.serve.__code__.co_varnames[:server.serve.__code__.co_argcount
                                                  + server.serve.__code__.co_kwonlyargcount]
        self.assertEqual(names, ('store', 'config', 'port', 'open_browser'))

    def test_bind_server_moves_to_next_free_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
            busy.bind((server.BIND_HOST, 0))
            busy.listen(1)
            taken = busy.getsockname()[1]
            httpd = server.bind_server(self.httpd.RequestHandlerClass, taken)
            try:
                host, port = httpd.server_address
            finally:
                httpd.server_close()
        self.assertEqual(host, '127.0.0.1')
        self.assertNotEqual(port, taken)
        self.assertLessEqual(port, taken + server.PORT_ATTEMPTS - 1)


class HostTests(ServerTestCase):
    def test_foreign_host_is_refused(self):
        for host in ('evil.example', f'evil.example:{self.port}', f'127.0.0.1.evil.example:{self.port}',
                     '127.0.0.1:1', f'[::1]:{self.port}', ''):
            for path in ('/', '/api/bootstrap', '/static/app.js'):
                with self.subTest(host=host, path=path):
                    status, _, body = self.call('GET', path, host=host)
                    self.assertEqual(status, 403)
                    self.assertNotIn(TOKEN.encode(), body)

    def test_foreign_host_is_refused_for_mutations(self):
        status, _, _ = self.call('POST', '/api/jobs/job-1/state', host='evil.example', body=b'{"saved": true}',
                                 headers={'X-Radar-Token': TOKEN, 'Content-Type': 'application/json'})
        self.assertEqual(status, 403)
        self.assertEqual(self.store.state_calls, [])

    def test_localhost_and_loopback_hosts_are_accepted(self):
        for host in (f'127.0.0.1:{self.port}', f'localhost:{self.port}', f'LOCALHOST:{self.port}'):
            with self.subTest(host=host):
                self.assertEqual(self.call('GET', '/api/bootstrap', host=host)[0], 200)


class ReadApiTests(ServerTestCase):
    def test_bootstrap_returns_token_and_overview(self):
        status, data = self.get_json('/api/bootstrap')
        self.assertEqual(status, 200)
        self.assertEqual(data['token'], TOKEN)
        self.assertEqual(data['profile'], {'name': 'Tester'})
        self.assertEqual(data['stats']['new_bengaluru'], 1)
        self.assertEqual(data['latest_run']['health'][0]['status'], 'partial')
        self.assertEqual(data['latest_run']['last_attempt']['status'], 'failed')
        self.assertEqual(data['scan']['running'], False)
        self.assertEqual(data['coverage_run']['later_runs'], ['run-3'])     # last full run merged with later retries
        self.assertEqual(set(data), {'token', 'profile', 'stats', 'latest_run', 'coverage_run', 'scan'})

    def test_jobs_defaults(self):
        status, data = self.get_json('/api/jobs')
        self.assertEqual(status, 200)
        self.assertEqual(data['total'], 4)
        self.assertEqual(data['jobs'][0]['id'], 'job-1')
        self.assertEqual(self.store.jobs_calls[0], {'view': 'all', 'city': 'all', 'types': None, 'q': '',
                                                    'min_score': 0, 'sort': 'score', 'limit': 100, 'offset': 0})

    def test_jobs_returns_tab_counts_under_the_same_filters(self):
        _, data = self.get_json('/api/jobs?view=saved&city=bengaluru&types=product,gcc&q=pega&min_score=60'
                                '&sort=posted&limit=50&offset=100')
        self.assertEqual(data['counts'], VIEW_TOTALS)
        self.assertEqual(data['total'], VIEW_TOTALS['saved'])
        page, *counting = self.store.jobs_calls
        self.assertEqual((page['view'], page['limit'], page['offset']), ('saved', 50, 100))
        self.assertEqual([call['view'] for call in counting], ['new', 'all', 'applied', 'hidden'])
        for call in counting:
            self.assertEqual({key: call[key] for key in ('city', 'types', 'q', 'min_score', 'limit', 'offset')},
                             {'city': 'bengaluru', 'types': ['product', 'gcc'], 'q': 'pega', 'min_score': 60,
                              'limit': 1, 'offset': 0})

    def test_jobs_params_are_parsed_and_passed_to_the_store(self):
        self.get_json('/api/jobs?view=new&city=bengaluru&types=gcc,enterprise,product,bogus&q=%20pega%20dev%20'
                      '&min_score=60&sort=posted&limit=50&offset=100')
        self.assertEqual(self.store.jobs_calls[0], {'view': 'new', 'city': 'bengaluru', 'types': ['product', 'gcc', 'enterprise'],
                                                    'q': 'pega dev', 'min_score': 60, 'sort': 'posted',
                                                    'limit': 50, 'offset': 100})

    def test_jobs_numeric_params_are_clamped(self):
        self.get_json('/api/jobs?limit=99999&offset=-7&min_score=250')
        call = self.store.jobs_calls[-len(server.VIEWS)]
        self.assertEqual((call['limit'], call['offset'], call['min_score']), (500, 0, 100))
        self.get_json('/api/jobs?limit=0&offset=abc&min_score=-3')
        call = self.store.jobs_calls[-len(server.VIEWS)]
        self.assertEqual((call['limit'], call['offset'], call['min_score']), (1, 0, 0))
        self.get_json('/api/jobs?limit=abc&q=' + 'x' * 900)
        call = self.store.jobs_calls[-len(server.VIEWS)]
        self.assertEqual((call['limit'], len(call['q'])), (100, server.MAX_QUERY_CHARS))

    def test_jobs_rejects_unknown_view_and_sort(self):
        self.assertEqual(self.get_json('/api/jobs?view=everything')[0], 400)
        self.assertEqual(self.get_json('/api/jobs?sort=company;drop')[0], 400)
        self.assertEqual(self.store.jobs_calls, [])

    def test_job_detail(self):
        status, data = self.get_json('/api/jobs/job-1')
        self.assertEqual(status, 200)
        self.assertEqual(data['description'], 'Build Pega case types.')
        self.assertEqual(data['sightings'], [])

    def test_unknown_job_is_404(self):
        for path in ('/api/jobs/nope', '/api/jobs/', '/api/jobs/job-1/extra', '/api/nothing'):
            with self.subTest(path=path):
                self.assertEqual(self.get_json(path)[0], 404)

    def test_scan_status(self):
        status, data = self.get_json('/api/scan/status')
        self.assertEqual(status, 200)
        self.assertEqual(set(data), {'running', 'mode', 'progress', 'last_summary', 'error'})

    def test_unhandled_error_is_a_500_with_a_readable_traceback_on_stderr(self):
        self.store.fail_jobs = True
        captured = io.StringIO()
        with contextlib.redirect_stderr(captured):
            status, data = self.get_json('/api/jobs')
        self.assertEqual(status, 500)
        self.assertEqual(data, {'error': 'internal error'})
        log = captured.getvalue()
        self.assertIn('Traceback (most recent call last):\n', log)
        self.assertIn('RuntimeError: database is on fire\n', log)
        self.assertNotIn('\\n', log)


class TimeoutTests(ServerTestCase):
    def test_handler_has_a_socket_timeout(self):
        self.assertEqual(self.httpd.RequestHandlerClass.timeout, server.SOCKET_TIMEOUT_SECONDS)
        self.assertLessEqual(server.SOCKET_TIMEOUT_SECONDS, 30)

    def test_stalled_connection_is_dropped(self):
        captured = io.StringIO()
        with mock.patch.object(self.httpd.RequestHandlerClass, 'timeout', 0.2), contextlib.redirect_stderr(captured):
            with socket.create_connection((server.BIND_HOST, self.port), timeout=5) as stalled:
                stalled.sendall(b'POST /api/scan HTTP/1.1\r\nHost: x\r\n')    # headers never finish
                self.assertEqual(stalled.recv(1024), b'')


class MutationTests(ServerTestCase):
    path = '/api/jobs/job-1/state'

    def test_state_update(self):
        status, data = self.post(self.path, {'saved': True, 'status': 'applied', 'notes': 'Called recruiter'})
        self.assertEqual(status, 200)
        self.assertEqual(data, {'saved': True, 'status': 'applied', 'notes': 'Called recruiter',
                                'hidden': False, 'seen': False})
        self.assertEqual(self.store.state_calls, [{'saved': True, 'status': 'applied', 'notes': 'Called recruiter'}])

    def test_hidden_and_seen_are_separate_flags(self):
        self.assertEqual(self.post(self.path, {'hidden': True})[0], 200)
        self.assertEqual(self.post(self.path, {'seen': True})[0], 200)
        self.assertEqual(self.post(self.path, {'hidden': False, 'seen': False})[0], 200)
        self.assertEqual(self.store.state_calls, [{'hidden': True}, {'seen': True}, {'hidden': False, 'seen': False}])

    def test_mark_all_seen(self):
        status, data = self.post('/api/jobs/seen-all', {})
        self.assertEqual((status, data), (200, {'marked': 7}))
        self.assertEqual(self.store.marked_all_seen, 1)

    def test_mark_all_seen_needs_the_token_and_post(self):
        self.assertEqual(self.post('/api/jobs/seen-all', {}, X_Radar_Token=None)[0], 403)
        self.assertEqual(self.post('/api/jobs/seen-all', {}, Origin='http://evil.example')[0], 403)
        self.assertEqual(self.get_json('/api/jobs/seen-all')[0], 404)
        self.assertEqual(self.store.marked_all_seen, 0)

    def test_same_origin_header_is_accepted(self):
        for origin in (f'http://127.0.0.1:{self.port}', f'http://localhost:{self.port}'):
            with self.subTest(origin=origin):
                self.assertEqual(self.post(self.path, {'saved': True}, Origin=origin)[0], 200)

    def test_every_status_is_accepted(self):
        for status_name in server.USER_STATUSES:
            with self.subTest(status=status_name):
                self.assertEqual(self.post(self.path, {'status': status_name})[0], 200)

    def test_unknown_job_is_404(self):
        self.assertEqual(self.post('/api/jobs/nope/state', {'saved': True})[0], 404)

    def test_unknown_post_route_is_404(self):
        self.assertEqual(self.post('/api/jobs/job-1', {'saved': True})[0], 404)

    def assert_rejected(self, expected, payload=None, **kwargs):
        status, data = self.post(self.path, payload if payload is not None else {'saved': True}, **kwargs)
        self.assertEqual(status, expected)
        self.assertIn('error', data)
        self.assertEqual(self.store.state_calls, [])

    def test_rejected_without_token(self):
        self.assert_rejected(403, X_Radar_Token=None)

    def test_rejected_with_wrong_token(self):
        self.assert_rejected(403, X_Radar_Token=TOKEN + 'x')
        self.assert_rejected(403, X_Radar_Token='')
        self.assert_rejected(403, X_Radar_Token='tökén')

    def test_rejected_with_wrong_content_type(self):
        self.assert_rejected(415, Content_Type='text/plain')
        self.assert_rejected(415, Content_Type='application/x-www-form-urlencoded')
        self.assert_rejected(415, Content_Type=None)

    def test_rejected_with_foreign_origin(self):
        for origin in ('http://evil.example', f'https://127.0.0.1:{self.port}', 'http://127.0.0.1:1', 'null'):
            with self.subTest(origin=origin):
                self.assert_rejected(403, Origin=origin)

    def test_rejected_when_body_is_not_an_object(self):
        deep = b'[' * 30000 + b']' * 30000          # parses only by recursing past the interpreter limit
        for raw in (b'[1, 2]', b'"saved"', b'null', b'7', b'{not json', b'', b'\xff\xfe', deep,
                    b'{"notes": ' + deep + b'}'):
            with self.subTest(raw=raw):
                self.assert_rejected(400, raw=raw)

    def test_rejected_when_body_is_oversized(self):
        raw = json.dumps({'notes': 'x' * (server.MAX_BODY_BYTES + 1)}).encode('utf-8')
        self.assert_rejected(413, raw=raw)

    def test_rejected_without_content_length(self):
        status, _, _ = self.call('POST', self.path, headers={'X-Radar-Token': TOKEN, 'Content-Type': 'application/json'})
        self.assertEqual(status, 411)

    def test_rejected_with_invalid_status(self):
        self.assert_rejected(400, {'status': 'archived'})
        self.assert_rejected(400, {'status': 'hidden'})
        self.assert_rejected(400, {'status': None})
        self.assert_rejected(400, {'status': ['new']})

    def test_rejected_with_too_long_notes(self):
        self.assert_rejected(400, {'notes': 'x' * (server.MAX_NOTES_CHARS + 1)})
        self.assert_rejected(400, {'notes': 5})

    def test_notes_at_the_limit_are_accepted(self):
        self.assertEqual(self.post(self.path, {'notes': 'x' * server.MAX_NOTES_CHARS})[0], 200)

    def test_rejected_with_non_boolean_flags(self):
        for flag in ('saved', 'hidden', 'seen'):
            for value in ('yes', 1, None):
                with self.subTest(flag=flag, value=value):
                    self.assert_rejected(400, {flag: value})

    def test_rejected_with_unknown_or_missing_fields(self):
        self.assert_rejected(400, {'saved': True, 'score': 100})
        self.assert_rejected(400, {})


class ScanTests(ServerTestCase):
    def test_scan_starts_then_conflicts_while_running(self):
        status, data = self.post('/api/scan', {})
        self.assertEqual(status, 202)
        self.assertTrue(data['scan']['running'])
        status, data = self.post('/api/scan', {})
        self.assertEqual(status, 409)
        self.assertIn('error', data)
        self.assertEqual(self.controller.modes, ['full'])           # {} means a full scan

    def test_scan_mode_is_passed_to_the_controller(self):
        for mode in server.SCAN_MODES:
            with self.subTest(mode=mode):
                self.controller.running = False
                status, data = self.post('/api/scan', {'mode': mode})
                self.assertEqual((status, data['scan']['mode']), (202, mode))
        self.assertEqual(self.controller.modes, ['full', 'retry'])

    def test_invalid_scan_requests_are_rejected_before_anything_starts(self):
        for payload in ({'mode': 'partial'}, {'mode': 'FULL'}, {'mode': ''}, {'mode': None}, {'mode': ['full']},
                        {'mode': {'full': 1}}, {'mode': 1}, {'only': 'Acme'}, {'mode': 'full', 'minutes': 999}):
            with self.subTest(payload=payload):
                status, data = self.post('/api/scan', payload)
                self.assertEqual(status, 400)
                self.assertIn('error', data)
        self.assertEqual(self.controller.modes, [])
        self.assertFalse(self.controller.running)

    def test_scan_requires_token(self):
        self.assertEqual(self.post('/api/scan', {}, X_Radar_Token=None)[0], 403)
        self.assertFalse(self.controller.running)

    def test_scan_cannot_be_started_with_get(self):
        self.assertEqual(self.get_json('/api/scan')[0], 404)
        self.assertFalse(self.controller.running)


class ScanControllerTests(unittest.TestCase):
    def controller_with(self, run_scan):
        self.locked_dirs = []

        @contextlib.contextmanager
        def scan_lock(data_dir):
            self.locked_dirs.append(data_dir)
            yield

        module = types.ModuleType('radar.scan')
        module.run_scan = run_scan
        module.scan_lock = scan_lock
        patcher = mock.patch.dict(sys.modules, {'radar.scan': module})
        patcher.start()
        self.addCleanup(patcher.stop)
        return server.ScanController(FakeStore(), {'profile': {}})

    def wait_until_idle(self, controller):
        for thread in threading.enumerate():
            if thread.name == 'radar-scan':
                thread.join(timeout=5)
        self.assertFalse(controller.status()['running'])

    def test_one_scan_at_a_time_and_summary_is_kept(self):
        release = threading.Event()
        calls = []

        def run_scan(config, store, *, mode):
            calls.append(mode)
            release.wait(timeout=5)
            return {'new': 3, 'status': 'complete', 'mode': mode}

        controller = self.controller_with(run_scan)
        self.assertEqual(controller.status(), {'running': False, 'mode': None, 'progress': None,
                                               'last_summary': None, 'error': None})
        self.assertTrue(controller.start('retry'))
        self.assertFalse(controller.start('full'))
        self.assertEqual((controller.status()['running'], controller.status()['mode']), (True, 'retry'))
        release.set()
        self.wait_until_idle(controller)
        self.assertEqual(calls, ['retry'])                           # the refused start never ran
        self.assertEqual(self.locked_dirs, [Path('data-dir')])
        self.assertEqual(controller.status(), {
            'running': False, 'mode': 'retry', 'progress': None,
            'last_summary': {'new': 3, 'status': 'complete', 'mode': 'retry'}, 'error': None})
        self.assertTrue(controller.start())
        self.wait_until_idle(controller)
        self.assertEqual(calls, ['retry', 'full'])

    def test_progress_is_shown_only_for_the_scan_now_running(self):
        release = threading.Event()
        controller = self.controller_with(lambda config, store, mode: release.wait(timeout=5) and {})
        store = controller._store
        live = {'state': 'running', 'started_at': '9999-01-01T00:00:00+00:00', 'done': 2, 'total': 9}
        store.progress = live
        self.assertIsNone(controller.status()['progress'])             # nothing running: never shown
        self.assertTrue(controller.start())
        self.assertEqual(controller.status()['progress'], live)
        for stale in ({**live, 'state': 'finished', 'done': 9},                       # the previous run's 100%
                      {**live, 'started_at': '2020-01-01T00:00:00+00:00'},            # a run that died mid-way
                      {'done': 2, 'total': 9}, 'running', None):
            with self.subTest(stale=stale):
                store.progress = stale
                self.assertIsNone(controller.status()['progress'])
                self.assertTrue(controller.status()['running'])
        release.set()
        self.wait_until_idle(controller)

    def test_failed_scan_is_reported_and_does_not_stick(self):
        def run_scan(config, store, mode):
            raise RuntimeError('another scan holds the lock')

        controller = self.controller_with(run_scan)
        with mock.patch('traceback.print_exc'):
            self.assertTrue(controller.start())
            self.wait_until_idle(controller)
        self.assertEqual(controller.status()['error'], 'RuntimeError: another scan holds the lock')
        self.assertIsNone(controller.status()['last_summary'])


class CoverageTests(ServerTestCase):
    def setUp(self):
        super().setUp()
        self.calls = []
        summary = {'original_rows': 286, 'employers': 240, 'configured': 150}
        module = types.ModuleType('radar.scan')
        module.load_coverage = lambda store, config: self.calls.append((store, config)) or (
            [dict(row) for row in COVERAGE_ROWS], summary)
        patcher = mock.patch.dict(sys.modules, {'radar.scan': module})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_coverage_returns_summary_and_rows_from_the_scan_inventory(self):
        status, data = self.get_json('/api/coverage')
        self.assertEqual(status, 200)
        self.assertEqual(data, {'summary': {'original_rows': 286, 'employers': 240, 'configured': 150},
                                'rows': COVERAGE_ROWS})
        self.assertEqual(self.calls, [(self.store, {'profile': {'name': 'Tester'}})])   # the scan's own function

    def test_coverage_is_built_again_on_every_request(self):
        self.get_json('/api/coverage')
        self.call('GET', '/api/coverage.csv')
        self.assertEqual(len(self.calls), 2)

    def test_server_has_no_inventory_loader_or_paths_of_its_own(self):
        source = Path(server.__file__).read_text(encoding='utf-8')
        for name in ('load_registry', 'load_targets', 'load_inventory', 'companies.json', 'targets.json', 'companies_path',
                     'targets_path', 'store.coverage(', 'coverage_summary'):
            with self.subTest(name=name):
                self.assertNotIn(name, source)

    def test_coverage_csv_has_bom_flat_portals_and_neutralised_formulas(self):
        status, headers, body = self.call('GET', '/api/coverage.csv')
        self.assertEqual(status, 200)
        self.assertTrue(headers['Content-Type'].startswith('text/csv'))
        self.assertRegex(headers['Content-Disposition'], r'^attachment; filename="pega-radar-coverage-[\d-]+\.csv"$')
        self.assertTrue(body.startswith(b'\xef\xbb\xbf'))
        text = body[3:].decode('utf-8')
        self.assertTrue(text.endswith('\r\n'))
        header, first, second = csv.reader(io.StringIO(text, newline=''))
        self.assertEqual(header, list(COVERAGE_COLUMNS))             # the shared helper's columns, in its order
        blocked, unresolved = dict(zip(header, first)), dict(zip(header, second))
        self.assertEqual(blocked['canonical'], "'=Booking.com")
        self.assertEqual(blocked['latest_error'], "'-HTTP 403")
        self.assertEqual(blocked['next_action'], "'@Run verify")
        self.assertEqual((blocked['latest_status'], blocked['inventory_state']), ('blocked', 'configured'))
        for nested in ('portals', 'sources', 'original_names'):
            self.assertNotIn('{', blocked[nested])                   # flattened to text, not a Python repr
        self.assertIn('icims', blocked['portals'])
        self.assertIn('candidate', blocked['portals'])
        self.assertEqual((unresolved['canonical'], unresolved['inventory_state'], unresolved['latest_status']),
                         ('', 'identity unresolved', ''))

    def test_coverage_routes_are_read_only_host_checked_and_carry_security_headers(self):
        for path in ('/api/coverage', '/api/coverage.csv'):
            with self.subTest(path=path):
                self.assertEqual(self.call('GET', path, host='evil.example')[0], 403)
                self.assertEqual(self.post(path, {})[0], 404)
                _, headers, _ = self.call('GET', path)
                for name, value in server.SECURITY_HEADERS.items():
                    self.assertEqual(headers[name], value)
                self.assertIsNone(headers['Access-Control-Allow-Origin'])
        self.assertEqual(self.get_json('/api/coverage/extra')[0], 404)


class StaticTests(ServerTestCase):
    def test_allow_listed_files_are_served(self):
        for path, content_type in (('/', 'text/html'), ('/static/index.html', 'text/html'),
                                   ('/static/app.js', 'text/javascript'), ('/static/app.css', 'text/css')):
            with self.subTest(path=path):
                status, headers, body = self.call('GET', path)
                self.assertEqual(status, 200)
                self.assertTrue(headers['Content-Type'].startswith(content_type))
                self.assertTrue(body)

    def test_traversal_and_unlisted_files_are_404(self):
        secret = b'BIND_HOST'
        for path in ('/static/../radar.py', '/static/../radar/server.py', '/static/%2e%2e/radar/server.py',
                     '/static/..%2fradar%2fserver.py', '/static/%2e%2e%2fradar.py', '/static/..%5cradar.py',
                     '/static/app.js/../../radar/server.py', '/static/./app.js', '/static//app.js',
                     '/static/app.js%00', '/static/APP.JS', '/static/', '/static', '/static/app.js.map',
                     '/radar/server.py', '/../radar/server.py', '/index.html', '/web/index.html',
                     '/static/../ARCHITECTURE.md', '/static/%252e%252e/radar.py'):
            with self.subTest(path=path):
                status, _, body = self.call('GET', path)
                self.assertEqual(status, 404)
                self.assertNotIn(secret, body)


class SecurityHeaderTests(ServerTestCase):
    def test_headers_on_every_kind_of_response(self):
        json_headers = {'X-Radar-Token': TOKEN, 'Content-Type': 'application/json'}
        requests = [
            ('GET', '/', {}), ('GET', '/static/app.js', {}), ('GET', '/static/app.css', {}),
            ('GET', '/api/bootstrap', {}), ('GET', '/api/jobs', {}), ('GET', '/api/jobs/job-1', {}),
            ('GET', '/api/export.csv', {}), ('GET', '/api/scan/status', {}),
            ('GET', '/nope', {}), ('GET', '/api/jobs?view=bad', {}), ('GET', '/', {'host': 'evil.example'}),
            ('POST', '/api/jobs/job-1/state', {'headers': json_headers, 'body': b'{"saved": true}'}),
            ('POST', '/api/jobs/job-1/state', {'body': b'{}'}),
            ('POST', '/api/scan', {'headers': json_headers, 'body': b'{}'}),
            ('PUT', '/api/jobs/job-1/state', {}), ('DELETE', '/api/jobs/job-1', {}), ('HEAD', '/', {}),
        ]
        for method, path, kwargs in requests:
            with self.subTest(method=method, path=path):
                _, headers, _ = self.call(method, path, **kwargs)
                for name, value in server.SECURITY_HEADERS.items():
                    self.assertEqual(headers[name], value)

    def test_policy_values(self):
        self.assertEqual(server.SECURITY_HEADERS['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(server.SECURITY_HEADERS['Referrer-Policy'], 'no-referrer')
        self.assertEqual(server.SECURITY_HEADERS['Cache-Control'], 'no-store')
        self.assertEqual(server.SECURITY_HEADERS['X-Frame-Options'], 'DENY')
        self.assertEqual(server.SECURITY_HEADERS['Cross-Origin-Resource-Policy'], 'same-origin')
        self.assertEqual(
            server.SECURITY_HEADERS['Content-Security-Policy'],
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; "
            "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")

    def test_no_cors_headers_and_unsupported_methods_are_refused(self):
        status, headers, _ = self.call('OPTIONS', '/api/jobs/job-1/state', headers={'Origin': 'http://evil.example'})
        self.assertEqual(status, 501)
        self.assertIsNone(headers['Access-Control-Allow-Origin'])
        _, headers, _ = self.call('GET', '/api/bootstrap', headers={'Origin': 'http://evil.example'})
        self.assertIsNone(headers['Access-Control-Allow-Origin'])


class CsvTests(ServerTestCase):
    def test_export_has_bom_and_neutralises_formulas(self):
        status, headers, body = self.call('GET', '/api/export.csv')
        self.assertEqual(status, 200)
        self.assertTrue(headers['Content-Type'].startswith('text/csv'))
        self.assertIn('attachment', headers['Content-Disposition'])
        self.assertTrue(body.startswith(b'\xef\xbb\xbf'))
        lines = body[3:].decode('utf-8').split('\r\n')
        self.assertEqual(lines[0], 'title,company,notes,status,city,location,score,saved,sources')
        self.assertEqual(
            lines[1],
            '"\'=HYPERLINK(""http://evil.invalid"")",\'+1,\'-2,\'@x,\'\tTab,"\'\rCR",-5,yes,LinkedIn; Hirist')
        self.assertEqual(lines[2], 'Pega Developer – Bengaluru,Acme,,new,Bengaluru,Bengaluru,88,no,')

    def test_csv_cell(self):
        for prefix in ('=', '+', '-', '@', '\t', '\r'):
            with self.subTest(prefix=prefix):
                self.assertEqual(server.csv_cell(prefix + 'cmd'), "'" + prefix + 'cmd')
        for padded in (' =cmd', '\n+cmd', ' \t -cmd', '\u00a0@cmd', '  \r=cmd'):
            with self.subTest(padded=padded):
                self.assertEqual(server.csv_cell(padded), "'" + padded)
        self.assertEqual(server.csv_cell(' plain - text'), ' plain - text')
        self.assertEqual(server.csv_cell(['=a', 'b']), "'=a; b")
        self.assertEqual(server.csv_cell('plain'), 'plain')
        self.assertEqual(server.csv_cell(None), '')
        self.assertEqual(server.csv_cell(-3.5), '-3.5')

    def test_empty_export(self):
        self.assertEqual(server.export_csv([]), b'\xef\xbb\xbf\r\n')


class FrontendStaticChecks(unittest.TestCase):
    def read(self, name):
        return (WEB_DIR / name).read_text(encoding='utf-8')

    def test_index_has_no_inline_code_or_remote_resources(self):
        html = self.read('index.html')
        scripts = re.findall(r'<script\b([^>]*)>(.*?)</script>', html, flags=re.S | re.I)
        self.assertTrue(scripts)
        for attributes, body in scripts:
            self.assertIn('src="/static/', attributes)
            self.assertEqual(body.strip(), '')
        self.assertIsNone(re.search(r'<style\b', html, flags=re.I))
        self.assertIsNone(re.search(r'\son[a-z]+\s*=', html, flags=re.I))
        self.assertIsNone(re.search(r'\sstyle\s*=', html, flags=re.I))
        self.assertIsNone(re.search(r'https?://', html, flags=re.I))
        self.assertIsNone(re.search(r'(?:src|href)\s*=\s*["\']?//', html, flags=re.I))
        self.assertNotIn('javascript:', html.lower())

    def test_index_only_references_allow_listed_static_files(self):
        references = re.findall(r'(?:src|href)="(/static/[^"]*)"', self.read('index.html'))
        self.assertEqual(sorted(references), ['/static/app.css', '/static/app.js'])
        for reference in references:
            self.assertIn(reference[len('/static/'):], server.STATIC_FILES)

    def test_app_js_never_builds_html_from_strings(self):
        script = self.read('app.js')
        for banned in ('innerHTML', 'outerHTML', 'insertAdjacentHTML', 'document.write', 'eval(',
                       'new Function', 'srcdoc', 'createContextualFragment', 'DOMParser'):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, script)

    def test_app_js_and_css_make_no_remote_requests(self):
        script = self.read('app.js')
        self.assertEqual(set(re.findall(r'https?://[^\s\'"`)]+', script)), {'http://www.w3.org/2000/svg'})
        css = self.read('app.css')
        self.assertIsNone(re.search(r'https?://|@import|url\(', css, flags=re.I))


def css_themes():
    """{'light': {...}, 'dark': {...}} custom properties from app.css; dark inherits what it does not override."""
    css = (WEB_DIR / 'app.css').read_text(encoding='utf-8')
    light = dict(re.findall(r'(--[\w-]+):\s*(#[0-9a-fA-F]{6})\s*;', re.search(r':root\s*\{(.*?)\}', css, re.S).group(1)))
    dark = dict(re.findall(r'(--[\w-]+):\s*(#[0-9a-fA-F]{6})\s*;',
                           re.search(r':root\[data-theme="dark"\]\s*\{(.*?)\}', css, re.S).group(1)))
    return {'light': light, 'dark': {**light, **dark}}


def contrast(first, second):
    """WCAG 2 contrast ratio of two #rrggbb colours."""
    def luminance(colour):
        channels = [int(colour[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


class ContrastTests(unittest.TestCase):
    SURFACES = ('--bg', '--surface', '--surface-2', '--accent-soft')

    def assert_contrast(self, minimum, foreground, backgrounds):
        for theme, colours in css_themes().items():
            for background in backgrounds:
                with self.subTest(theme=theme, foreground=foreground, background=background):
                    self.assertGreaterEqual(contrast(colours[foreground], colours[background]), minimum)

    def test_control_borders_reach_3_to_1(self):
        self.assert_contrast(3, '--control', self.SURFACES)

    def test_text_colours_reach_4_5_to_1_on_every_row_background(self):
        for ink in ('--ink', '--ink-2', '--ink-3'):
            self.assert_contrast(4.5, ink, self.SURFACES)        # hovered and cursor rows included

    def test_coloured_text_reaches_4_5_to_1(self):
        self.assert_contrast(4.5, '--accent-ink', ('--accent',))
        self.assert_contrast(4.5, '--accent', ('--surface', '--accent-soft'))
        self.assert_contrast(4.5, '--warn', ('--warn-soft',))
        self.assert_contrast(4.5, '--bad', ('--bad-soft',))
        self.assert_contrast(4.5, '--ink-2', ('--surface-2',))   # the disabled "Scanning…" button

    def test_controls_use_the_control_border_and_disabled_buttons_stay_opaque(self):
        css = (WEB_DIR / 'app.css').read_text(encoding='utf-8')
        for selector in ('.btn', 'select', '.segmented', '.search', '#notes', '.chip'):
            with self.subTest(selector=selector):
                rule = re.search(r'(?:^|\n)' + re.escape(selector) + r' \{(.*?)\}', css, re.S).group(1)
                self.assertIn('border: 1px solid var(--control)', rule)
        disabled = re.search(r'\.btn:disabled \{(.*?)\}', css, re.S).group(1)
        self.assertNotIn('opacity', disabled)
        self.assertIn('color: var(--ink-2)', disabled)
        small = css[css.index('@media (max-width: 760px)'):]
        self.assertRegex(small, r'\.segmented button,\s*select \{\s*min-height: 40px;')    # touch targets on phones
        self.assertIn('border-color: var(--control)', re.search(r'button\.tile \{(.*?)\}', css, re.S).group(1))


JS_HARNESS = r"""
// Runs web/app.js against a minimal fake DOM, fake timers and a fake server. No network, no browser.
const fs = require('fs'), vm = require('vm');
const source = fs.readFileSync(process.argv[2], 'utf8');
const tick = () => new Promise((resolve) => setImmediate(resolve));
const settle = async () => { for (let i = 0; i < 20; i++) await tick(); };
const failures = [];
const check = (ok, name, detail) => { if (!ok) failures.push(`${name}${detail === undefined ? '' : ': ' + JSON.stringify(detail)}`); };

function boot(server, storage = {}) {
  const ids = {};
  class Node {
    constructor(tag) {
      Object.assign(this, {tagName: String(tag).toUpperCase(), children: [], attrs: {}, listeners: {}, dataset: {}, style: {},
        parentNode: null, hidden: false, open: false, disabled: false, value: '', scrollTop: 0});
      const names = new Set();
      this.classList = {add: (c) => names.add(c), remove: (c) => names.delete(c), contains: (c) => names.has(c),
        toggle: (c, on) => (on ? names.add(c) : names.delete(c))};
    }
    setAttribute(key, value) {
      this.attrs[key] = String(value);
      if (key === 'id') ids[value] = this;
      if (key === 'class') String(value).split(/\s+/).filter(Boolean).forEach((name) => this.classList.add(name));
      if (key.startsWith('data-')) this.dataset[key.slice(5).replace(/-(\w)/g, (_, letter) => letter.toUpperCase())] = String(value);
    }
    removeAttribute(key) { delete this.attrs[key]; }
    addEventListener(type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); }
    fire(type, event = {}) { (this.listeners[type] || []).forEach((fn) => fn({target: this, preventDefault() {}, ...event})); }
    append(...kids) {
      for (const kid of kids) {
        if (!(kid instanceof Node)) { this.children.push(String(kid)); continue; }
        if (kid.isFragment) { this.append(...kid.children); continue; }
        kid.remove();
        kid.parentNode = this;
        this.children.push(kid);
      }
    }
    replaceChildren(...kids) { this.children.slice().forEach((kid) => kid instanceof Node && kid.remove()); this.children = []; this.append(...kids); }
    remove() { if (this.parentNode) { this.parentNode.children = this.parentNode.children.filter((kid) => kid !== this); this.parentNode = null; } }
    replaceWith(node) { const parent = this.parentNode; parent.children[parent.children.indexOf(this)] = node; node.parentNode = parent; this.parentNode = null; }
    contains(node) { for (let at = node; at; at = at.parentNode) if (at === this) return true; return false; }
    closest() { return null; }
    all(test, out = []) { for (const kid of this.children) if (kid instanceof Node) { if (test(kid)) out.push(kid); kid.all(test, out); } return out; }
    querySelectorAll(selector) { const m = /^\[data-(\w+)(?:="([^"]*)")?\]$/.exec(selector); return this.all((n) => m && n.dataset[m[1]] !== undefined && (m[2] === undefined || n.dataset[m[1]] === m[2])); }
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
    button(text) { return this.all((n) => n.tagName === 'BUTTON' && n.textContent.includes(text))[0]; }
    focus() { document.activeElement = this; }
    blur() { if (document.activeElement === this) document.activeElement = null; }
    scrollIntoView() {}
    showModal() { this.open = true; }
    close() { if (this.open) { this.open = false; this.fire('close'); } }
    set textContent(value) { this.replaceChildren(String(value)); }
    get textContent() { return this.children.map((kid) => (kid instanceof Node ? kid.textContent : kid)).join(''); }
    set title(value) { this.attrs.title = value; }
  }
  const document = {documentElement: new Node('html'), body: new Node('body'), activeElement: null, listeners: {},
    getElementById: (id) => (ids[id] && (ids[id].isRoot || ids[id].parentNode) ? ids[id] : null),
    createElement: (tag) => new Node(tag), createElementNS: (_, tag) => new Node(tag),
    createDocumentFragment: () => Object.assign(new Node('#fragment'), {isFragment: true}),
    addEventListener(type, fn) { this.listeners[type] = fn; }};
  for (const id of ['scanned-at', 'scan-button', 'scan-button-label', 'scan-progress', 'scan-progress-fill', 'scan-progress-text',
    'readout', 'offline-strip', 'offline-retry', 'attention-strip', 'tabs', 'jobs-view', 'filters', 'filter-chips', 'search',
    'min-score', 'min-score-value', 'sort', 'result-line', 'seen-all', 'list', 'empty', 'load-more', 'sources-view', 'drawer',
    'drawer-body', 'help', 'help-button', 'help-close', 'theme-button', 'toasts', 'retry-button', 'coverage-view',
    'coverage-tiles', 'coverage-filters', 'coverage-search', 'coverage-line', 'coverage-table', 'coverage-rows', 'coverage-empty',
    'view-title', 'view-description', 'profile-focus', 'scan-detail']) {
    const node = new Node('div');
    node.isRoot = true;
    node.setAttribute('id', id);
  }
  ids['offline-strip'].hidden = true;
  const timers = [];
  let nextTimer = 1;
  const location = {hash: '', pathname: '/', search: '', replaced: [], replace(hash) { this.replaced.push(hash); this.hash = hash; }};
  const requests = [];
  const fetch = async (path, options) => {
    const body = options && options.body ? JSON.parse(options.body) : undefined;
    requests.push({path, body});
    const reply = await server(path, body);
    if (reply === 'down') throw new TypeError('Failed to fetch');
    const [status, data] = reply;
    return {ok: status < 400, status, json: async () => data};
  };
  const context = vm.createContext({document, location, fetch, console, Date, URLSearchParams,
    window: {matchMedia: () => ({matches: false, addEventListener() {}}), addEventListener() {}, scrollY: 0, scrollTo() {}},
    localStorage: {getItem: (key) => Object.hasOwn(storage, key) ? storage[key] : null,
      setItem: (key, value) => { storage[key] = String(value); }, removeItem: (key) => { delete storage[key]; }},
    history: {replaceState() { location.hash = ''; }},
    navigator: {clipboard: {writeText: async () => {}}}, IntersectionObserver: class { observe() {} },
    setTimeout: (fn, ms) => { timers.push({id: nextTimer, fn, ms}); return nextTimer++; },
    clearTimeout: (id) => { const at = timers.findIndex((timer) => timer.id === id); if (at >= 0) timers.splice(at, 1); },
    setInterval: () => nextTimer++, clearInterval() {}});
  vm.runInContext(source, context);
  const run = (code) => vm.runInContext(code, context);
  // Fire every pending timer whose delay is at most `ms`, then let promises settle.
  const elapse = async (ms) => { timers.filter((timer) => timer.ms <= ms).forEach((timer) => { timers.splice(timers.indexOf(timer), 1); timer.fn(); }); await settle(); };
  const posts = () => requests.filter((request) => request.body !== undefined);
  const jobRequests = () => requests.filter((request) => request.path.startsWith('/api/jobs?')).map((request) => new URLSearchParams(request.path.split('?')[1]));
  return {ids, document, location, timers, requests, run, elapse, posts, jobRequests, storage};
}

function fakeServer(overrides = {}) {
  const rows = [1, 2, 3].map((n) => ({id: `j${n}`, title: `Pega Developer ${n}`, company: 'Acme', employer_type: 'gcc', location: 'Bengaluru',
    is_bengaluru: 1, url: `https://example.invalid/${n}`, score: 90 - n, fit: {reasons: ['Pega in title']}, saved: 0, hidden: 0, seen: 0,
    is_new: 1, status: 'new', notes: '', sources: ['LinkedIn'], first_seen_at: '2026-11-13T02:00:00+00:00'}));
  const server = {rows, down: false, failNotes: false, latestRun: {id: 'r1', started_at: '2026-11-14T02:00:00+00:00',
    finished_at: '2026-11-14T02:04:00+00:00', status: 'partial', last_attempt: {id: 'r1', status: 'partial'},
    summary: {mode: 'full', requested: 40, attempted: 38, completed: 35}, health: [
      {source: 'board:shine', label: 'Shine', kind: 'board', status: 'skipped', found: 0, kept: 0, error: 'out of time'},
      {source: 'Employer site', label: 'CBA', kind: 'ats', status: 'ok', found: 3, kept: 2, error: null},
      {source: 'Employer site', label: 'HDFC', kind: 'ats', status: 'skipped', found: 0, kept: 0, error: 'out of time'},
      {source: 'Employer site', label: 'ANZ', kind: 'ats', status: 'blocked', found: 0, kept: 0, error: 'HTTP 403'}]}, ...overrides};
  server.handle = (path, body) => {
    if (server.down) return 'down';
    if (path === '/api/bootstrap') return [200, {token: 't', stats: {
      total: rows.filter((row) => !row.hidden && row.status !== 'rejected').length,
      new: rows.filter((row) => !row.hidden && row.is_new).length,
      saved: rows.filter((row) => !row.hidden && row.saved).length,
      applied: rows.filter((row) => !row.hidden && ['applied', 'interviewing', 'offer', 'rejected'].includes(row.status)).length,
      hidden: rows.filter((row) => row.hidden).length}, latest_run: server.latestRun,
      coverage_run: server.coverageRun || server.latestRun, scan: {running: false}}];
    if (path === '/api/scan/status') return [200, server.scanStatus || {running: true, mode: 'retry', error: null, last_summary: null,
      progress: {state: 'running', mode: 'retry', requested: 12, attempted: 5, completed: 4, not_attempted: 2, done: 5, total: 12, running: ['Hirist']}}];
    if (path === '/api/coverage') return server.coverage ? [200, server.coverage] : [500, {error: 'inventory missing'}];
    if (path === '/api/scan') return [202, {scan: {running: true}}];
    if (path === '/api/jobs/seen-all') { rows.forEach((row) => { row.seen = 1; row.is_new = 0; }); return [200, {marked: 3}]; }
    if (path.startsWith('/api/jobs?')) {
      const query = new URLSearchParams(path.split('?')[1]);
      const view = query.get('view');
      const inView = rows.filter((row) => {
        if (view === 'hidden') return row.hidden;
        if (row.hidden) return false;
        if (view === 'new') return row.is_new && row.status === 'new';
        if (view === 'saved') return row.saved;
        if (view === 'applied') return ['applied', 'interviewing', 'offer', 'rejected'].includes(row.status);
        return row.status !== 'rejected';
      });
      const offset = Number(query.get('offset'));
      return [200, {jobs: inView.slice(offset, offset + Number(query.get('limit'))).map((row) => ({...row})), total: inView.length,
        counts: {new: 3, all: 8, saved: 1, applied: 2, hidden: rows.filter((row) => row.hidden).length}}];
    }
    const row = rows.find((item) => path.startsWith(`/api/jobs/${item.id}`));
    if (!row) return [404, {error: 'no such job'}];
    if (body === undefined) return [200, {...row, description: 'Pega work', sightings: []}];
    if ('notes' in body && server.failNotes) return [500, {error: 'disk full'}];
    if (body.seen && (server.failSeenIds || []).includes(row.id)) return [500, {error: 'could not save read state'}];
    Object.assign(row, body);
    if (body.seen) row.is_new = 0;
    return [200, body];
  };
  return server;
}

(async () => {
  // ---- list, tabs, chips, search --------------------------------------------------------------
  let server = fakeServer();
  let app = boot(server.handle);
  await app.run('init()');
  await settle();
  check(app.ids.list.children.length === 3, 'three cards are rendered');
  const tabs = app.ids.tabs.textContent;
  check(tabs.includes('New roles3') && tabs.includes('All roles3') && tabs.includes('Pipeline0') && tabs.includes('Hidden0'),
    'navigation counts come from the global overview, not the filtered list reply', tabs);
  check(/Bengaluru×Product \+ GCC×Clear all/.test(app.ids['filter-chips'].textContent), 'default filters are shown as removable chips', app.ids['filter-chips'].textContent);
  check(app.ids.readout.textContent.includes('Unread'), 'readout identifies unread roles');
  check(app.ids['attention-strip'].textContent.includes('Shine (skipped) and 2 employer sites'), 'skipped sources need attention', app.ids['attention-strip'].textContent);
  app.run('state.jobs[0].employer_type = "enterprise"; refreshJob("j1")');
  check(app.ids.list.children[0].textContent.includes('Enterprise'), 'enterprise employers get their own badge');
  app.run('state.view = "sources"; renderSources()');
  const sources = app.ids['sources-view'].textContent;
  check(sources.includes('1 of 3 answered') && sources.includes('Employer sites that did not answer (2)') && sources.includes('HDFCskipped — out of time'), 'sources table counts skipped sites as unanswered', sources);
  app.run('state.view = "new"');

  app.ids['filter-chips'].button('Bengaluru').fire('click');
  await settle();
  check(app.jobRequests().at(-2).get('city') === 'all' && app.jobRequests().at(-2).get('types') === 'product,gcc', 'a chip removes only its own filter');
  check(!app.ids['filter-chips'].textContent.includes('Bengaluru'), 'removed chip is gone');

  const search = app.ids.search;
  search.focus();
  search.value = 'pega ';
  search.fire('input');
  app.ids['min-score'].value = '60';
  app.ids['min-score'].fire('input');
  await app.elapse(250);
  check(search.value === 'pega ', 'the focused search box is never rewritten', search.value);
  check(app.run('state.filters.q') === 'pega ', 'the stored query keeps its trailing space');
  check(app.jobRequests().at(-2).get('q') === 'pega', 'the request is trimmed', app.jobRequests().at(-2).get('q'));
  check(app.jobRequests().at(-2).get('min_score') === '60', 'slider and search have separate debounce timers');
  search.value = 'pega developer';
  search.fire('input');
  await app.elapse(250);
  check(app.jobRequests().at(-2).get('q') === 'pega developer' && search.value === 'pega developer', 'typing after a pause keeps the space');

  // ---- Sources view makes no list requests -----------------------------------------------------
  app.run('setView("sources")');
  await settle();
  let before = app.requests.length;
  app.run('changeFilters({focus: false})');
  await settle();
  check(app.requests.length === before && !app.ids.toasts.textContent, 'filter changes on Sources make no request and no toast', app.ids.toasts.textContent);
  app.run('changeFilters({q: "", minScore: 0}); setView("all")');
  await settle();

  // ---- hide is a flag, reload from the top, undo for 10 s ------------------------------------
  before = app.posts().length;
  await app.run('setHidden(state.jobs[0], true)');
  await settle();
  check(JSON.stringify(app.posts()[before].body) === '{"hidden":true}', 'hide sends only the hidden flag', app.posts()[before].body);
  check(server.rows[0].status === 'new', 'hide never touches the status');
  const reload = app.jobRequests().filter((query) => query.get('limit') !== '1').at(-1);
  check(reload.get('offset') === '0' && Number(reload.get('limit')) >= 3, 'after a row leaves, the list is re-read from offset 0', reload.toString());
  check(app.ids.list.children.length === 2 && !app.ids.list.textContent.includes('Developer 1'), 'the hidden row left the list');
  check(app.ids.toasts.textContent.includes('Hidden: Pega Developer 1') && app.timers.some((timer) => timer.ms === 10000), 'undo toast lasts 10 s');
  const undoToast = app.ids.toasts.children[0];
  undoToast.fire('mouseenter');
  check(!app.timers.some((timer) => timer.ms === 10000), 'hovering pauses the undo toast');
  undoToast.fire('mouseleave');
  check(app.timers.some((timer) => timer.ms === 10000), 'leaving restarts it');
  undoToast.button('Undo').fire('click');
  await settle();
  check(server.rows[0].hidden === false && app.ids.list.children.length === 3, 'undo restores the row');
  app.run('setView("hidden")');
  await settle();
  server.rows[1].hidden = 1;
  await app.run('loadJobs()');
  check(app.ids.list.children.length === 1 && app.ids.list.all((n) => n.attrs.title === 'Restore (x)').length === 1, 'Hidden tab offers Restore');
  await app.run('toggleHidden(state.jobs[0])');
  await settle();
  check(JSON.stringify(app.posts().at(-1).body) === '{"hidden":false}' && server.rows[1].status === 'new', 'restore clears the flag only');
  app.run('setView("new")');
  await settle();

  // ---- opening marks seen, focuses the title, replaces history while open ---------------------
  check(app.ids.list.children[0].textContent.includes('New') && !app.ids['seen-all'].hidden, 'unread rows carry the marker and the New tab offers mark-all');
  app.location.hash = '#job=j1';
  await app.run('syncDrawer()');
  await settle();
  check(app.posts().some((post) => post.path === '/api/jobs/j1/state' && JSON.stringify(post.body) === '{"seen":true}'), 'opening a role marks it seen');
  check(app.ids.list.children.length === 3 && !app.ids.list.children[0].all((n) => n.classList.contains('new-mark')).length, 'the card stays but loses NEW');
  check(app.document.activeElement && app.document.activeElement.attrs.id === 'drawer-title' && app.document.activeElement.attrs.tabindex === '-1', 'focus moves to the drawer title');
  app.run('openJob("j2")');
  check(app.location.replaced.join() === '#job=j2', 'moving on inside the drawer replaces the history entry', app.location.replaced);
  await app.run('syncDrawer()');
  await settle();

  // ---- notes: a failed save stays queued and is retried ----------------------------------------
  server.failNotes = true;
  app.run('queueNotes("j2", "call back\\uD83D")');
  await app.elapse(700);
  check(JSON.stringify(app.posts().at(-1).body) === '{"notes":"call back"}', 'a trailing lone surrogate is not sent', app.posts().at(-1).body);
  check(app.run('pendingNotes.has("j2")') && app.ids['notes-status'].textContent === 'Not saved — retrying', 'a failed save stays queued');
  check(app.timers.some((timer) => timer.ms === 3000), 'a retry is scheduled');
  app.ids.drawer.close();
  await settle();
  check(app.run('pendingNotes.get("j2").value') === 'call back\uD83D', 'closing the drawer does not drop the text');
  app.location.hash = '#job=j2';
  await app.run('syncDrawer()');
  check(app.ids.notes.value === 'call back\uD83D', 'reopening shows the unsaved text, not the server copy');
  app.run('queueNotes("j2", "call back tomorrow")');
  server.failNotes = false;
  await app.elapse(700);
  check(server.rows[1].notes === 'call back tomorrow' && !app.run('pendingNotes.size') && app.ids['notes-status'].textContent === 'Saved', 'the next keystroke retries and clears the queue');
  app.ids.drawer.close();

  // ---- mark all as seen ---------------------------------------------------------------------------
  const seenBefore = app.posts().length;
  app.ids['seen-all'].fire('click');
  await settle();
  const seenPosts = app.posts().slice(seenBefore);
  check(seenPosts.length === 1 && seenPosts[0].path === '/api/jobs/j3/state' && seenPosts[0].body.seen === true
    && app.ids.list.children.length === 0 && app.ids.empty.textContent.includes('Inbox clear'),
    'mark these as read changes only the remaining loaded unread role', seenPosts);

  // ---- scan modes, counts, possibly closed -----------------------------------------------------------
  check(app.ids['scan-detail'].textContent.includes('Full scan: 40 requested · 38 attempted · 35 completed'),
    'About scans shows the detailed last-run counts', app.ids['scan-detail'].textContent);
  server.rows[2].possibly_closed = 1;
  server.rows[2].last_confirmed_at = '2026-11-10T02:00:00+00:00';
  app.run('setView("all")');
  await settle();
  const closed = app.ids.list.all((n) => n.classList.contains('closed-mark'));
  check(closed.length === 1 && closed[0].textContent === 'Possibly closed' && closed[0].attrs.title.includes('has re-read its full listing and no longer shows it. Roles seen only on LinkedIn are never flagged.') && closed[0].attrs.title.includes('Last confirmed'), 'possibly closed marker explains itself');
  app.location.hash = '#job=j3';
  await app.run('syncDrawer()');
  check(app.ids['drawer-body'].textContent.includes('Possibly closed. Every employer site or job board that listed this role has re-read its full listing and no longer shows it. Roles seen only on LinkedIn are never flagged.') && app.ids['drawer-body'].textContent.includes('Last confirmed'), 'drawer explains possibly closed in visible text');
  app.ids.drawer.close();
  app.ids['retry-button'].fire('click');
  await settle();
  check(JSON.stringify(app.posts().at(-1)) === '{"path":"/api/scan","body":{"mode":"retry"}}', 'Retry incomplete sends mode retry', app.posts().at(-1));
  check(app.ids['scan-button'].disabled === true && app.ids['retry-button'].disabled === true, 'both scan buttons are disabled while scanning');
  check(app.ids['scan-progress-text'].textContent === 'Retry of incomplete sources · 12 requested · 5 attempted · 4 completed · 2 not reached · Hirist', 'progress shows requested, attempted, completed and a not-reached count given as a number', app.ids['scan-progress-text'].textContent);
  app.run('stopScanWatch()');
  app.ids['scan-button'].fire('click');
  await settle();
  check(JSON.stringify(app.posts().at(-1).body) === '{"mode":"full"}', 'Full scan sends mode full');

  // ---- disconnect after five failed polls ---------------------------------------------------------
  server.down = true;
  for (let i = 0; i < 4; i++) await app.run('pollScan()');
  check(app.ids['offline-strip'].hidden === true && app.run('state.scanTimer') !== null, 'four failures are tolerated');
  await app.run('pollScan()');
  check(app.ids['offline-strip'].hidden === false && app.run('state.scanTimer') === null && app.ids['scan-button'].disabled === false, 'the fifth failure stops polling and shows Disconnected');
  server.down = false;
  app.ids['offline-retry'].fire('click');
  await settle();
  check(app.ids['offline-strip'].hidden === true, 'the banner clears on the next successful request');

  // ---- first load fails: error state with Retry ---------------------------------------------------
  server = fakeServer({down: true});
  app = boot(server.handle);
  await app.run('init()');
  check(app.ids.empty.hidden === false && app.ids.empty.textContent.includes('Cannot reach Pega Radar') && Boolean(app.ids.empty.button('Retry')), 'a failed first load shows an error with Retry', app.ids.empty.textContent);
  server.down = false;
  app.ids.empty.button('Retry').fire('click');
  await settle();
  check(app.ids.list.children.length === 3 && app.ids.empty.hidden === true, 'Retry loads the page');

  // ---- a failed last attempt is reported next to the previous coverage --------------------------
  server = fakeServer({latestRun: {id: 'r1', started_at: '2026-11-13T02:00:00+00:00', finished_at: '2026-11-13T02:04:00+00:00', status: 'complete', health: [],
    last_attempt: {id: 'r2', status: 'failed', finished_at: '2026-11-14T02:00:00+00:00', error: 'no sources are configured'}}});
  app = boot(server.handle);
  await app.run('init()');
  const strip = app.ids['attention-strip'];
  check(strip.hidden === false && /The last scan at .+ failed: no sources are configured — showing coverage from the previous scan\./.test(strip.textContent), 'failed last attempt strip', strip.textContent);
  server = fakeServer({latestRun: {id: null, started_at: null, finished_at: null, status: null, health: [], last_attempt: {id: 'r2', status: 'failed', finished_at: '2026-11-14T02:00:00+00:00', error: null}}});
  app = boot(server.handle);
  await app.run('init()');
  check(app.ids['scanned-at'].textContent === 'No completed scan yet' && app.ids['attention-strip'].textContent.includes('No scan has completed yet'), 'only failed scans so far', app.ids['attention-strip'].textContent);

  // ---- coverage table ----------------------------------------------------------------------------------
  const portal = (kind, state, scope) => ({kind, state, scope});
  const cov = (canonical, inventory_state, latest_status, extra = {}) => ({canonical, original_names: [canonical], type: 'gcc', bengaluru: true,
    career_url: 'https://example.invalid/careers', portals: [portal('workday', 'verified', 'india')], linkedin_query: true, inventory_state,
    last_attempt_at: latest_status ? '2026-11-15T02:00:00+00:00' : null, last_success_at: null, latest_status, latest_reason: null,
    latest_error: null, pages_complete: latest_status ? true : null, details_complete: null, jobs_total: 0, jobs_open: 0, next_action: 'Nothing to do', ...extra});
  server = fakeServer();
  server.coverage = {summary: {original_rows: 286, employers: 240, ok: 0}, rows: [
    cov('Healthy Co', 'configured', 'ok', {jobs_total: 5, jobs_open: 4, last_success_at: '2026-11-15T02:00:00+00:00', parent: 'Healthy Group',
      inventory_note: 'Shares a board', portals: [{...portal('workday', 'verified', 'india'), business_unit: 'Cards'}],
      sources: [{task: 'ats:workday:a', status: 'ok', reason: null}, {task: 'ats:workday:b', status: 'empty', reason: null},
        {task: 'ats:workday:c', status: null, reason: null}, {task: 'ats:workday:d', status: 'not_reached', reason: 'budget'}]}),
    cov('Quiet Co', 'configured', 'empty'),
    cov('Refused Co', 'configured', 'blocked', {latest_reason: 'http_4xx', latest_error: 'HTTP 403 <b>denied</b>', pages_complete: false,
      portals: [{...portal('icims', 'candidate', 'global'), note: 'iCIMS markers seen on 15 Nov'}], career_url: 'javascript:alert(1)'}),
    cov('Untried Co', 'configured', null),
    cov('Bare Co', 'not configured', null, {portals: [], bengaluru: null, linkedin_query: false, type: 'enterprise'}),
    cov('Browser Co', 'unsupported', null, {portals: [portal('custom', 'unsupported', 'unknown')], bengaluru: false}),
    cov('Abroad Co', 'wrong scope only', null, {portals: [portal('workday', 'wrong_scope', 'global')]}),
    cov(null, 'identity unresolved', null, {original_names: ['<img src=x onerror=alert(1)>', 'Mystery'], portals: [], type: null, career_url: null,
      next_action: 'Decide which employer <script>alert(2)</script> means'}),
  ]};
  app = boot(server.handle);
  await app.run('init()');
  check(app.ids.tabs.textContent.includes('Employer coverage') && app.ids.tabs.textContent.includes('Scan sources'),
    'coverage and source navigation explain their purpose');
  before = app.jobRequests().length;
  app.run('setView("coverage")');
  await settle();
  const table = app.ids['coverage-rows'];
  const names = () => table.children.map((row) => row.children[0].all((n) => n.classList.contains('company'))[0].textContent);
  const pillOf = (name) => table.children[names().indexOf(name)].all((n) => n.classList.contains('pill'))[0];
  check(table.children.length === 8 && app.ids['coverage-line'].textContent === '8 rows' && app.ids['jobs-view'].hidden === true && app.jobRequests().length === before, 'coverage lists every row without loading jobs', app.ids['coverage-line'].textContent);
  const tiles = app.ids['coverage-tiles'];
  check(tiles.children.map((group) => group.children[0].textContent).join() === 'Inventory,Last scan,Latest outcome', 'tiles are in three labelled groups');
  check(['286Original targets', '–Attempted', '4Configured', '1Unverified portal', '1Not configured', '1Identity unresolved', '1Never attempted',
    '1OK', '1Empty', '1Blocked', '0Error', '0Skipped'].every((part) => tiles.textContent.includes(part)), 'tiles: OK and Empty, Error and Skipped are separate; a missing figure is a dash', tiles.textContent);
  const tile = (label) => app.ids['coverage-tiles'].all((n) => n.classList.contains('tile') && n.textContent.endsWith(label))[0];
  check(tile('Original targets').tagName === 'DIV' && tile('Empty').tagName === 'BUTTON', 'only tiles with a matching filter are buttons');
  tile('Empty').fire('click');
  check(names().join() === 'Quiet Co' && tile('Empty').attrs['aria-pressed'] === 'true' && app.run('coverage.filters.status') === 'empty', 'clicking a tile applies its filter, and the tile count equals the rows shown', names());
  tile('Not configured').fire('click');
  check(names().join() === 'Bare Co' && app.run('coverage.filters.status') === '' && tile('Empty').attrs['aria-pressed'] === 'false', 'a tile replaces the previous tile filter');
  tile('Not configured').fire('click');
  check(names().length === 8, 'clicking the active tile shows everything again');
  check(names()[0] === 'Refused Co' && names().at(-1) === 'Healthy Co' && names().indexOf('Untried Co') < names().indexOf('Bare Co') && names().indexOf('Bare Co') < names().indexOf('Quiet Co'), 'needs-attention order', names());
  const text = table.textContent;
  check(text.includes('<img src=x onerror=alert(1)>') && text.includes('<script>alert(2)</script>') && text.includes('HTTP 403 <b>denied</b>')
    && table.all((n) => ['IMG', 'SCRIPT', 'B'].includes(n.tagName)).length === 0, 'untrusted text is shown as text, never as markup');
  const links = table.all((n) => n.tagName === 'A').map((n) => n.attrs.href);
  check(links.length === 6 && links.every((href) => href === 'https://example.invalid/careers') && !text.includes('javascript:'), 'only http(s) career links are rendered', links);
  const classes = (name) => ['pill-gap', 'pill-quiet', 'pill-good', 'pill-bad', 'gap-none', 'gap-unsupported', 'gap-scope', 'gap-identity', 'gap-never'].filter((c) => pillOf(name).classList.contains(c)).join(' ');
  const looks = {empty: classes('Quiet Co'), ok: classes('Healthy Co'), blocked: classes('Refused Co'), never: classes('Untried Co'), none: classes('Bare Co'),
    unsupported: classes('Browser Co'), scope: classes('Abroad Co'), identity: classes('<img src=x onerror=alert(1)>')};
  check(JSON.stringify(looks) === JSON.stringify({empty: 'pill-quiet', ok: 'pill-good', blocked: 'pill-bad', never: 'pill-gap gap-never', none: 'pill-gap gap-none',
    unsupported: 'pill-gap gap-unsupported', scope: 'pill-gap gap-scope', identity: 'pill-gap gap-identity'}), 'inventory gaps look different from empty and from failures', looks);
  check(pillOf('Bare Co').textContent === 'Not configured' && pillOf('Abroad Co').textContent === 'Wrong scope' && pillOf('Browser Co').textContent === 'Unsupported portal'
    && pillOf('<img src=x onerror=alert(1)>').textContent === 'Identity unresolved' && pillOf('Untried Co').textContent === 'Never attempted' && !text.includes('Bare Coempty'), 'gap labels are spelled out and never say empty');
  check(text.includes('icims · unverified · global scope') && text.includes('workday · verified · india scope') && text.includes('LinkedIn keyword query: yes'), 'portal state, scope and the keyword query are labelled');
  check(text.includes('Part of Healthy Group') && text.includes('Shares a board') && text.includes('india scope · Cards') && text.includes('ats:workday:b: empty')
    && text.includes('ats:workday:c: never attempted') && text.includes('ats:workday:d: not reached, budget'), 'parent, note, business unit and per-portal outcomes are shown');
  check(text.includes('http_4xx — HTTP 403') && text.includes('Pages incomplete') && text.includes('never succeeded'), 'result details and completeness');
  const healthy = table.children[names().indexOf('Healthy Co')].children[3];
  check(healthy.attrs['data-label'] === 'Roles on file' && healthy.textContent === '54 seen in last 30 days, not flagged closed', 'roles on file, with the recent open count explained', healthy.textContent);
  const note = table.all((n) => n.textContent === 'iCIMS markers seen on 15 Nov');
  check(note.length === 1 && note[0].tagName === 'P' && table.all((n) => n.attrs.title === 'iCIMS markers seen on 15 Nov').length === 0, 'portal notes are visible text, not a hover title');
  const choose = async (key, value) => { app.ids['coverage-filters'].fire('change', {target: {dataset: {coverageFilter: key}, value}}); await settle(); return names(); };
  check((await choose('inventory', 'not configured')).join() === 'Bare Co' && app.ids['coverage-line'].textContent === '1 of 8 rows match', 'inventory filter');
  await choose('inventory', '');
  check((await choose('status', 'never')).join() === 'Untried Co', 'never attempted excludes unconfigured employers', names());
  check((await choose('status', 'empty')).join() === 'Quiet Co', 'latest result filter');
  await choose('status', '');
  check((await choose('portal', 'candidate')).join() === 'Refused Co', 'portal state filter');
  await choose('portal', '');
  check((await choose('type', 'enterprise')).join() === 'Bare Co', 'type filter');
  await choose('type', '');
  check((await choose('bengaluru', 'no')).join() === 'Browser Co' && (await choose('bengaluru', 'unknown')).join() === 'Bare Co', 'Bengaluru filter');
  await choose('bengaluru', '');
  app.ids['coverage-search'].value = 'mystery';
  app.ids['coverage-search'].fire('input');
  check(names().length === 1 && table.textContent.includes('Listed as: Mystery'), 'search matches original names');
  app.ids['coverage-search'].value = 'zzz';
  app.ids['coverage-search'].fire('input');
  check(app.ids['coverage-table'].hidden === true && app.ids['coverage-empty'].textContent.includes('No employer matches'), 'no match shows an empty state');
  app.ids['coverage-empty'].button('Clear filters').fire('click');
  check(names().length === 8, 'clear filters restores every row');
  app.ids['coverage-filters'].fire('change', {target: {dataset: {}, id: 'coverage-sort', value: 'jobs'}});
  check(names()[0] === 'Healthy Co', 'sort by roles on file');
  app.ids['coverage-filters'].fire('change', {target: {dataset: {}, id: 'coverage-sort', value: 'stale'}});
  check(names().slice(0, 4).join() === 'Quiet Co,Refused Co,Untried Co,Healthy Co' && names().slice(4).every((name) => /Bare|Browser|Abroad|<img/.test(name)), 'longest without success: inventory gaps come after every attempted row', names());
  // ---- not reached, nothing to retry, merged Sources ---------------------------------------------------
  check(app.ids['retry-button'].disabled === false, 'Retry is offered while something is incomplete');
  server.coverage.rows.push(cov('Late Co', 'configured', 'not_reached', {latest_reason: 'budget'}));
  await app.run('loadCoverage()');
  check(pillOf('Late Co').textContent === 'Not reached (time budget)' && pillOf('Late Co').classList.contains('gap-unreached') && !pillOf('Late Co').classList.contains('pill-bad')
    && !pillOf('Late Co').classList.contains('pill-warn'), 'not reached has its own pill, not an error or a skip');
  check(tile('Not reached (time budget)').textContent.startsWith('1') && tile('Error').textContent.startsWith('0') && tile('Skipped').textContent.startsWith('0'), 'not reached has its own tile outside Error and Skipped');
  tile('Not reached (time budget)').fire('click');
  check(names().join() === 'Late Co', 'the not-reached tile filters to those rows');
  tile('Not reached (time budget)').fire('click');
  server.coverage.rows = server.coverage.rows.filter((row) => ['ok', 'empty'].includes(row.latest_status) || row.inventory_state !== 'configured');
  await app.run('loadCoverage()');
  check(app.ids['retry-button'].disabled === true && app.ids['retry-button'].attrs.title.startsWith('Nothing to retry') && app.ids['scan-button'].disabled === false, 'Retry is disabled when nothing is incomplete; gaps and healthy rows do not count');
  server.scanStatus = {running: false, mode: 'retry', error: null, progress: null, last_summary: {mode: 'retry', requested: 0, status: 'nothing_to_retry', run_id: null, new: 0}};
  app.run('setView("sources")');
  const sourcesBefore = app.ids['sources-view'].textContent;
  app.run('watchScan("retry")');
  await settle();
  before = app.requests.length;
  await settle();
  check(app.ids.toasts.textContent.includes('Nothing to retry — every configured source answered in the latest scan') && !app.ids.toasts.textContent.includes('Scan finished'), 'an empty retry says there was nothing to retry', app.ids.toasts.textContent);
  check(app.ids['sources-view'].textContent === sourcesBefore && app.requests.length === before && !app.requests.slice(-2).some((r) => r.path === '/api/bootstrap'), 'and leaves the Sources tab alone');
  server.coverageRun = {...server.latestRun, later_runs: ['r2', 'r3'], health: [
    {source: 'board:shine', label: 'Shine', kind: 'board', status: 'skipped', reason: 'budget', found: 0, kept: 0, error: 'not started before the time budget ended'},
    {source: 'Employer site', label: 'CBA', kind: 'ats', status: 'skipped', reason: 'budget', found: 0, kept: 0, error: null}]};
  await app.run('refreshOverview()');
  const sourcesText = app.ids['sources-view'].textContent;
  check(sourcesText.includes('newer result from 2 later retry runs') && sourcesText.includes('ShineNot reached (time budget)') && sourcesText.includes('CBAnot reached') && !sourcesText.includes('Shineskipped'), 'Sources shows the merged run and names budget cut-offs as not reached', sourcesText);
  check(app.ids['attention-strip'].textContent.includes('Shine (not reached)'), 'the attention strip says not reached too', app.ids['attention-strip'].textContent);
  server.latestRun = {id: 'r9', started_at: '2026-11-15T03:00:00+00:00', finished_at: '2026-11-15T03:00:00+00:00', status: 'complete', health: [],
    summary: {mode: 'retry', requested: 0, attempted: 0, completed: 0}, last_attempt: {id: 'r9', status: 'complete'}};
  await app.run('refreshOverview()');
  check(app.ids['scan-detail'].textContent.includes('Full scan: 40 requested · 38 attempted · 35 completed')
    && !app.ids['scan-detail'].textContent.includes('retry'),
    'scan details ignore a stored empty retry and keep the last scan that attempted something', app.ids['scan-detail'].textContent);
  app.run('setView("coverage")');
  await settle();

  server.coverage = null;
  await app.run('loadCoverage()');
  check(app.ids['coverage-empty'].textContent.includes('Coverage could not be loaded') && Boolean(app.ids['coverage-empty'].button('Retry')), 'a failed coverage load offers Retry');

  // ---- collection filters and keyboard focus survive navigation ---------------------------------------
  server = fakeServer();
  app = boot(server.handle);
  await app.run('init()');
  app.run('changeFilters({q: "bank", minScore: 80})');
  await settle();
  const savedTab = app.ids.tabs.querySelector('[data-view="saved"]');
  savedTab.focus();
  savedTab.fire('click');
  await settle();
  let currentQuery = app.jobRequests().filter((query) => query.get('limit') !== '1').at(-1);
  check(currentQuery.get('view') === 'saved' && currentQuery.get('city') === 'all'
    && !currentQuery.get('types') && !currentQuery.get('q') && currentQuery.get('min_score') === '0',
    'Saved starts without discovery filters', currentQuery.toString());
  check(app.document.activeElement === app.ids.tabs.querySelector('[data-view="saved"]')
    && app.document.activeElement.parentNode === app.ids.tabs,
    'keyboard focus follows the replacement navigation button after the response');
  app.run('changeFilters({bengaluru: true, q: "saved query"}); setView("applied")');
  await settle();
  currentQuery = app.jobRequests().filter((query) => query.get('limit') !== '1').at(-1);
  check(currentQuery.get('city') === 'all' && !currentQuery.get('types') && !currentQuery.get('q'),
    'Pipeline has independent broad filters', currentQuery.toString());
  app.run('setView("new")');
  await settle();
  currentQuery = app.jobRequests().filter((query) => query.get('limit') !== '1').at(-1);
  check(currentQuery.get('city') === 'bengaluru' && currentQuery.get('types') === 'product,gcc'
    && currentQuery.get('q') === 'bank' && currentQuery.get('min_score') === '80',
    'returning to discovery restores its filters', currentQuery.toString());
  app.run('setView("saved")');
  await settle();
  check(app.run('state.filters.bengaluru') === true && app.run('state.filters.q') === 'saved query',
    'a collection remembers its own filters within the session');

  // ---- collection membership changes are visible immediately ------------------------------------------
  server = fakeServer();
  server.rows[0].saved = true;
  server.rows[1].status = 'interviewing';
  server.rows[1].is_new = false;
  app = boot(server.handle);
  await app.run('init()');
  app.run('setView("saved")');
  await settle();
  check(app.ids.list.children.length === 1, 'Saved initially contains the saved role');
  app.ids.list.children[0].querySelector('[data-role="save"]').fire('click');
  await settle();
  check(!server.rows[0].saved && app.ids.list.children.length === 0 && !app.ids.empty.hidden && Boolean(app.ids.empty.button('Explore roles')),
    'removing the last saved role updates the collection without a manual refresh');
  app.run('setView("applied")');
  await settle();
  check(app.ids.list.children.length === 1, 'Pipeline initially contains the interviewing role');
  const applicationStatus = app.ids.list.children[0].querySelector('[data-role="status"]');
  applicationStatus.value = 'interested';
  applicationStatus.fire('change');
  await settle();
  check(server.rows[1].status === 'interested' && app.ids.list.children.length === 0
    && !app.ids.empty.hidden && Boolean(app.ids.empty.button('Explore roles')),
    'a role leaves Pipeline after changing to a status outside the pipeline');

  // ---- visible loading and recoverable failure after changing filters ---------------------------------
  server = fakeServer();
  let holdJobs = false;
  const waitingJobs = [];
  app = boot((path, body) => holdJobs && path.startsWith('/api/jobs?')
    ? new Promise((resolve) => waitingJobs.push(() => resolve(server.handle(path, body))))
    : server.handle(path, body));
  await app.run('init()');
  holdJobs = true;
  const loading = app.run('loadJobs()');
  await settle();
  check(app.ids['jobs-view'].attrs['aria-busy'] === 'true'
    && /Loading|Updating/.test(app.ids['result-line'].textContent) && app.ids['seen-all'].disabled,
    'pending requests announce loading and disable bulk actions');
  holdJobs = false;
  waitingJobs.splice(0).forEach((resolve) => resolve());
  await loading;
  check(app.ids['jobs-view'].attrs['aria-busy'] === 'false' && app.ids.list.children.length === 3,
    'completed requests clear the loading state');
  server.down = true;
  app.run('changeFilters({q: "changed query"})');
  await settle();
  check(app.ids.list.children.length === 0 && app.ids['jobs-view'].attrs['aria-busy'] === 'false'
    && app.ids.empty.textContent.includes('Could not load these roles') && Boolean(app.ids.empty.button('Try again')),
    'a failed filter request does not present stale rows as matching results');
  server.down = false;
  app.ids.empty.button('Try again').fire('click');
  await settle();
  check(app.ids.list.children.length === 3 && app.ids.empty.hidden, 'the failed-filter recovery reloads the current view');

  // ---- drafts survive a reload while the server cannot save them --------------------------------------
  server = fakeServer({failNotes: true});
  const draftStorage = {};
  app = boot(server.handle, draftStorage);
  await app.run('init()');
  app.run('queueNotes("j1", "Sample draft that must survive a reload")');
  check(JSON.parse(draftStorage['radar.note-drafts']).j1 === 'Sample draft that must survive a reload',
    'notes are durable before the debounce timer fires');
  app = boot(server.handle, draftStorage);
  await app.run('init()');
  await settle();
  app.location.hash = '#job=j1';
  await app.run('syncDrawer()');
  check(app.ids.notes.value === 'Sample draft that must survive a reload'
    && JSON.parse(draftStorage['radar.note-drafts']).j1 === app.ids.notes.value,
    'a new page restores the draft even if the first save retry fails');
  server.failNotes = false;
  await app.run('flushNotes()');
  check(server.rows[0].notes === 'Sample draft that must survive a reload'
    && Object.keys(JSON.parse(draftStorage['radar.note-drafts'])).length === 0,
    'only a successful save removes the durable draft');

  // ---- bulk read is restricted to visible rows and reports partial failure -----------------------------
  server = fakeServer({failSeenIds: ['j2']});
  app = boot((path, body) => {
    if (path.startsWith('/api/jobs?')) {
      const query = new URLSearchParams(path.split('?')[1]);
      if (query.get('city') !== 'all') {
        const visible = server.rows.filter((row) => ['j1', 'j2'].includes(row.id) && row.is_new);
        return [200, {jobs: visible.map((row) => ({...row})), total: visible.length, counts: {new: visible.length}}];
      }
    }
    return server.handle(path, body);
  });
  await app.run('init()');
  check(app.ids.list.children.length === 2, 'bulk-read fixture has one unread role outside the filters');
  await app.run('markAllSeen()');
  await settle();
  const markedPaths = app.posts().filter((post) => post.body.seen).map((post) => post.path).sort();
  check(markedPaths.join() === '/api/jobs/j1/state,/api/jobs/j2/state' && !app.posts().some((post) => post.path === '/api/jobs/seen-all')
    && !server.rows[0].is_new && server.rows[1].is_new && server.rows[2].is_new,
    'bulk read leaves outside and failed roles unread', markedPaths);
  check(app.ids.list.children.length === 1 && app.ids.toasts.textContent.includes('1 of 2 marked as read'),
    'partial bulk failure leaves its role visible and explains recovery');

  // ---- opening a role keeps the visible unread action accurate ----------------------------------------
  server = fakeServer();
  app = boot(server.handle);
  await app.run('init()');
  app.location.hash = '#job=j1';
  await app.run('syncDrawer()');
  check(app.ids['seen-all'].textContent.includes('2') && !app.ids['seen-all'].hidden,
    'opening a role immediately updates the number in the bulk-read action', app.ids['seen-all'].textContent);
  for (const id of ['j2', 'j3']) {
    app.location.hash = `#job=${id}`;
    await app.run('syncDrawer()');
  }
  check(app.ids['seen-all'].hidden, 'the bulk-read action disappears when every loaded role has been read');

  // ---- decision caveats remain visible when card space is limited -------------------------------------
  server = fakeServer();
  const rankedReasons = ['Pega developer role', 'Bengaluru location', 'Product or GCC employer',
    'Salary not stated', 'Experience is a stretch'];
  server.rows[0].fit = {reasons: rankedReasons.slice()};
  server.rows[0].salary_min_lpa = null;
  server.rows[0].salary_max_lpa = null;
  server.rows[1].salary_min_lpa = 30;
  server.rows[1].salary_max_lpa = 38;
  server.rows[1].fit = {reasons: ['Pega developer role', 'Bengaluru location']};
  app = boot(server.handle);
  await app.run('init()');
  const firstCard = app.ids.list.children[0];
  const visibleReasons = firstCard.all((node) => node.classList.contains('job-reasons'))[0];
  check(visibleReasons && visibleReasons.children.map((node) => node.textContent).join('|')
    === 'Salary not stated|Experience is a stretch|Pega developer role',
    'salary and experience caveats precede positives without exceeding three visible reasons',
    visibleReasons && visibleReasons.textContent);
  check(firstCard.textContent.includes('Salary') && firstCard.textContent.includes('Not listed'),
    'a missing salary has an explicit label and does not disappear from the card', firstCard.textContent);
  const paidCard = app.ids.list.children[1];
  check(paidCard.textContent.includes('Salary') && paidCard.textContent.includes('₹')
    && paidCard.textContent.includes('30') && paidCard.textContent.includes('38')
    && !paidCard.textContent.includes('Not listed'),
    'an advertised salary is shown instead of the missing-salary label', paidCard.textContent);
  check(JSON.stringify(app.run('state.jobs[0].fit.reasons')) === JSON.stringify(rankedReasons),
    'card prioritization does not reorder or remove the underlying fit evidence');
  app.location.hash = '#job=j1';
  await app.run('syncDrawer()');
  check(rankedReasons.every((reason) => app.ids['drawer-body'].textContent.includes(reason)),
    'the role drawer retains every fit reason, including those omitted from the card');

  // ---- first use stays actionable without inventing jobs or application history -----------------------
  server = fakeServer({latestRun: null});
  server.rows.length = 0;
  server.coverage = {summary: {original_rows: 0, employers: 0}, rows: []};
  app = boot((path, body) => {
    const reply = server.handle(path, body);
    if (path === '/api/bootstrap') reply[1].profile = {city: 'Pune', certifications: ['CSSA'], target_lpa: 35};
    return reply;
  });
  await app.run('init()');
  const welcomeHeadings = app.ids.empty.all((node) => node.tagName === 'H1');
  check(app.ids.list.children.length === 0 && app.ids.empty.classList.contains('welcome')
    && welcomeHeadings.length === 1 && welcomeHeadings[0].textContent.includes('Pega roles.')
    && Boolean(app.ids.empty.button('Run your first scan')),
    'an unseeded workspace offers the first scan in a dedicated welcome state');
  check(app.ids.empty.textContent.includes('Pune') && app.ids.empty.textContent.includes('CSSA')
    && app.ids.empty.textContent.includes('₹35 LPA+') && app.ids.empty.textContent.includes('40 minutes'),
    'the welcome brief reflects the configured profile and realistic scan duration');
  check(app.ids['retry-button'].hidden && app.ids['seen-all'].hidden,
    'first use does not offer retry or mark-read actions before there are results');
  app.ids.empty.button('Explore coverage').fire('click');
  await settle();
  check(app.ids['jobs-view'].hidden && !app.ids['coverage-view'].hidden && app.run('state.view') === 'coverage',
    'first-use coverage action opens employer coverage without running a scan');
  for (const collection of ['saved', 'applied', 'hidden']) {
    app.run(`setView("${collection}")`);
    await settle();
    check(!app.ids.empty.classList.contains('welcome') && app.ids.list.children.length === 0
      && Boolean(app.ids.empty.button('Explore roles')) && !app.ids.empty.button('Run your first scan'),
      `${collection} has its own empty state before the first scan`);
  }
  app.run('setView("new")');
  await settle();
  app.ids.empty.button('Run your first scan').fire('click');
  await settle();
  check(app.posts().filter((post) => post.path === '/api/scan').length === 1
    && app.posts().find((post) => post.path === '/api/scan').body.mode === 'full',
    'the welcome action requests exactly one full scan');
  check(app.ids.empty.textContent.includes('Your radar is searching')
    && !app.ids.empty.button('Run your first scan') && Boolean(app.ids.empty.button('View scan sources'))
    && app.ids['scan-button'].disabled,
    'the welcome state reflects a running scan instead of inviting a duplicate scan');
  app.run('stopScanWatch()');

  if (failures.length) { console.error(failures.join('\n')); process.exit(1); }
})().catch((error) => { console.error(error); process.exit(1); });
"""


@unittest.skipUnless(shutil.which('node'), 'node is not installed; the browser logic is only checked where it is')
class FrontendLogicTests(unittest.TestCase):
    def test_app_js_behaviour_against_a_fake_dom(self):
        done = subprocess.run([shutil.which('node'), '-', str(WEB_DIR / 'app.js')], input=JS_HARNESS, text=True,
                              encoding='utf-8', capture_output=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr or done.stdout)


if __name__ == '__main__':
    unittest.main()
