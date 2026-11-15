"""Tests for radar/server.py. Everything runs on 127.0.0.1 with an ephemeral port and a fake store."""

import contextlib
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

    def start(self):
        if self.running:
            return False
        self.running = True
        return True

    def status(self):
        return {'running': self.running, 'progress': None, 'last_summary': None, 'error': None}


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
        self.assertEqual(set(data), {'token', 'profile', 'stats', 'latest_run', 'scan'})

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
        self.assertEqual(set(data), {'running', 'progress', 'last_summary', 'error'})

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

        def run_scan(config, store):
            calls.append((config, store))
            release.wait(timeout=5)
            return {'new': 3, 'status': 'complete'}

        controller = self.controller_with(run_scan)
        self.assertEqual(controller.status(), {'running': False, 'progress': None, 'last_summary': None, 'error': None})
        self.assertTrue(controller.start())
        self.assertFalse(controller.start())
        self.assertTrue(controller.status()['running'])
        release.set()
        self.wait_until_idle(controller)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.locked_dirs, [Path('data-dir')])
        self.assertEqual(controller.status(), {'running': False, 'progress': None,
                                               'last_summary': {'new': 3, 'status': 'complete'}, 'error': None})
        self.assertTrue(controller.start())
        self.wait_until_idle(controller)

    def test_progress_is_shown_only_for_the_scan_now_running(self):
        release = threading.Event()
        controller = self.controller_with(lambda config, store: release.wait(timeout=5) and {})
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
        def run_scan(config, store):
            raise RuntimeError('another scan holds the lock')

        controller = self.controller_with(run_scan)
        with mock.patch('traceback.print_exc'):
            self.assertTrue(controller.start())
            self.wait_until_idle(controller)
        self.assertEqual(controller.status()['error'], 'RuntimeError: another scan holds the lock')
        self.assertIsNone(controller.status()['last_summary'])


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
        self.assertRegex(small, r'\.segmented button \{\s*min-height: 40px;')


JS_HARNESS = r"""
// Runs web/app.js against a minimal fake DOM, fake timers and a fake server. No network, no browser.
const fs = require('fs'), vm = require('vm');
const source = fs.readFileSync(process.argv[2], 'utf8');
const tick = () => new Promise((resolve) => setImmediate(resolve));
const settle = async () => { for (let i = 0; i < 20; i++) await tick(); };
const failures = [];
const check = (ok, name, detail) => { if (!ok) failures.push(`${name}${detail === undefined ? '' : ': ' + JSON.stringify(detail)}`); };

function boot(server) {
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
      if (key.startsWith('data-')) this.dataset[key.slice(5)] = String(value);
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
    'drawer-body', 'help', 'help-button', 'help-close', 'theme-button', 'toasts']) {
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
    const reply = server(path, body);
    if (reply === 'down') throw new TypeError('Failed to fetch');
    const [status, data] = reply;
    return {ok: status < 400, status, json: async () => data};
  };
  const context = vm.createContext({document, location, fetch, console, Date, URLSearchParams,
    window: {matchMedia: () => ({matches: false, addEventListener() {}}), addEventListener() {}, scrollY: 0, scrollTo() {}},
    localStorage: {getItem: () => null, setItem() {}}, history: {replaceState() { location.hash = ''; }},
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
  return {ids, document, location, timers, requests, run, elapse, posts, jobRequests};
}

function fakeServer(overrides = {}) {
  const rows = [1, 2, 3].map((n) => ({id: `j${n}`, title: `Pega Developer ${n}`, company: 'Acme', employer_type: 'gcc', location: 'Bengaluru',
    is_bengaluru: 1, url: `https://example.invalid/${n}`, score: 90 - n, fit: {reasons: ['Pega in title']}, saved: 0, hidden: 0, seen: 0,
    is_new: 1, status: 'new', notes: '', sources: ['LinkedIn'], first_seen_at: '2026-11-13T02:00:00+00:00'}));
  const server = {rows, down: false, failNotes: false, latestRun: {id: 'r1', started_at: '2026-11-14T02:00:00+00:00',
    finished_at: '2026-11-14T02:04:00+00:00', status: 'partial', last_attempt: {id: 'r1', status: 'partial'}, health: [
      {source: 'board:shine', label: 'Shine', kind: 'board', status: 'skipped', found: 0, kept: 0, error: 'out of time'},
      {source: 'Employer site', label: 'CBA', kind: 'ats', status: 'ok', found: 3, kept: 2, error: null},
      {source: 'Employer site', label: 'HDFC', kind: 'ats', status: 'skipped', found: 0, kept: 0, error: 'out of time'},
      {source: 'Employer site', label: 'ANZ', kind: 'ats', status: 'blocked', found: 0, kept: 0, error: 'HTTP 403'}]}, ...overrides};
  server.handle = (path, body) => {
    if (server.down) return 'down';
    if (path === '/api/bootstrap') return [200, {token: 't', stats: {total: rows.length, new: 3}, latest_run: server.latestRun, scan: {running: false}}];
    if (path === '/api/scan/status') return [200, {running: true, progress: null, last_summary: null, error: null}];
    if (path === '/api/scan') return [202, {scan: {running: true}}];
    if (path === '/api/jobs/seen-all') { rows.forEach((row) => { row.seen = 1; row.is_new = 0; }); return [200, {marked: 3}]; }
    if (path.startsWith('/api/jobs?')) {
      const query = new URLSearchParams(path.split('?')[1]);
      const inView = rows.filter((row) => (query.get('view') === 'hidden' ? row.hidden : !row.hidden) && (query.get('view') !== 'new' || row.is_new));
      const offset = Number(query.get('offset'));
      return [200, {jobs: inView.slice(offset, offset + Number(query.get('limit'))).map((row) => ({...row})), total: inView.length,
        counts: {new: 3, all: 8, saved: 1, applied: 2, hidden: rows.filter((row) => row.hidden).length}}];
    }
    const row = rows.find((item) => path.startsWith(`/api/jobs/${item.id}`));
    if (!row) return [404, {error: 'no such job'}];
    if (body === undefined) return [200, {...row, description: 'Pega work', sightings: []}];
    if ('notes' in body && server.failNotes) return [500, {error: 'disk full'}];
    Object.assign(row, body);
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
  check(tabs.includes('New3') && tabs.includes('All8') && tabs.includes('Pipeline2') && tabs.includes('Hidden0'), 'tab counts come from the filtered list reply', tabs);
  check(/Bengaluru×Product \+ GCC×Clear all/.test(app.ids['filter-chips'].textContent), 'default filters are shown as removable chips', app.ids['filter-chips'].textContent);
  check(app.ids.readout.textContent.includes('New (unread)'), 'tile is renamed');
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
  app.ids['seen-all'].fire('click');
  await settle();
  check(app.posts().at(-1).path === '/api/jobs/seen-all' && app.ids.list.children.length === 0 && app.ids.empty.textContent.includes('Inbox clear'), 'mark all as seen empties the inbox');

  // ---- disconnect after five failed polls ---------------------------------------------------------
  app.run('watchScan()');
  await settle();
  check(app.ids['scan-button'].disabled === true, 'scan button is disabled while scanning');
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
