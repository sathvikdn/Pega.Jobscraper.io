"""Local web server and JSON API for Pega Radar.

Loopback only: the bind address is a constant, every request must carry a loopback Host header,
and every mutation needs the per-process token, a JSON body and (when sent) a same-origin Origin.
"""

import csv
import hmac
import io
import json
import os
import secrets
import sys
import threading
import traceback
import webbrowser
from datetime import date, datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from radar.model import csv_cell

BIND_HOST = '127.0.0.1'          # never configurable: this server is for the local user only
HOST_NAMES = ('127.0.0.1', 'localhost')
PORT_ATTEMPTS = 21               # the requested port and the 20 after it

WEB_DIR = Path(__file__).resolve().parent.parent / 'web'
STATIC_FILES = {
    'index.html': 'text/html; charset=utf-8',
    'app.js': 'text/javascript; charset=utf-8',
    'app.css': 'text/css; charset=utf-8',
}

VIEWS = ('new', 'all', 'saved', 'applied', 'hidden')
SORTS = ('score', 'posted', 'first_seen')
EMPLOYER_TYPES = ('product', 'gcc', 'enterprise', 'services', 'staffing', 'unknown')
USER_STATUSES = ('new', 'interested', 'applied', 'interviewing', 'offer', 'rejected')
STATE_FLAGS = ('saved', 'hidden', 'seen')

MAX_BODY_BYTES = 64 * 1024
MAX_DRAIN_BYTES = 1024 * 1024
MAX_NOTES_CHARS = 5000
MAX_QUERY_CHARS = 200
MAX_CITY_CHARS = 60
DEFAULT_LIMIT = 100
SOCKET_TIMEOUT_SECONDS = 15
MAX_LIMIT = 500
MAX_OFFSET = 1_000_000

SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer',
    'Cache-Control': 'no-store',
    'X-Frame-Options': 'DENY',
    'Cross-Origin-Resource-Policy': 'same-origin',
    'Content-Security-Policy': (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    ),
}


class ApiError(Exception):
    """An error with an HTTP status that is safe to show to the client."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


class ScanController:
    """Runs at most one scan at a time in a background thread."""

    def __init__(self, store, config):
        self._store = store
        self._config = config
        self._lock = threading.Lock()
        self._running = False
        self._started_at = ''
        self._last_summary = None
        self._error = None

    def start(self):
        """Start a scan. Returns False when one is already running."""
        with self._lock:
            if self._running:
                return False
            self._running = True
            self._started_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
            self._error = None
        threading.Thread(target=self._run, name='radar-scan', daemon=True).start()
        return True

    def _run(self):
        summary, error = None, None
        try:
            from radar.scan import run_scan, scan_lock   # lazy: the server starts even if a scan cannot
            with scan_lock(self._store.path.parent):     # never overlap a scheduled or command-line scan
                summary = run_scan(self._config, self._store)
        except Exception as exc:              # a failed scan must be reported, never kill the server
            traceback.print_exc()
            error = f'{type(exc).__name__}: {exc}'
        with self._lock:
            self._running = False
            self._error = error
            if summary is not None:
                self._last_summary = summary

    def status(self):
        with self._lock:
            running, started_at = self._running, self._started_at
            summary, error = self._last_summary, self._error
        progress = self._store.kv_get('scan_progress') if running else None
        return {'running': running, 'progress': progress if self._is_live(progress, started_at) else None,
                'last_summary': summary, 'error': error}

    @staticmethod
    def _is_live(progress, started_at):
        """True only for progress written by the scan this controller is running now.

        The stored value outlives its scan, so an earlier run's finished (or abandoned) progress
        is never shown as the current one. Timestamps are same-format UTC strings.
        """
        return (isinstance(progress, dict) and progress.get('state') == 'running'
                and str(progress.get('started_at') or '') >= started_at)


def clamp_int(raw, default, low, high):
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, value))


def parse_jobs_query(query):
    """Turn the /api/jobs query string into validated keyword arguments for Store.jobs()."""
    params = {key: values[-1] for key, values in parse_qs(query, keep_blank_values=True).items()}
    view = params.get('view') or 'all'
    if view not in VIEWS:
        raise ApiError(HTTPStatus.BAD_REQUEST, f'view must be one of {", ".join(VIEWS)}')
    sort = params.get('sort') or 'score'
    if sort not in SORTS:
        raise ApiError(HTTPStatus.BAD_REQUEST, f'sort must be one of {", ".join(SORTS)}')
    wanted = {part.strip().lower() for part in params.get('types', '').split(',')}
    types = [name for name in EMPLOYER_TYPES if name in wanted]
    return {
        'view': view,
        'city': (params.get('city') or 'all').strip()[:MAX_CITY_CHARS] or 'all',
        'types': types or None,
        'q': params.get('q', '').strip()[:MAX_QUERY_CHARS],
        'min_score': clamp_int(params.get('min_score'), 0, 0, 100),
        'sort': sort,
        'limit': clamp_int(params.get('limit'), DEFAULT_LIMIT, 1, MAX_LIMIT),
        'offset': clamp_int(params.get('offset'), 0, 0, MAX_OFFSET),
    }


def parse_state_update(body):
    """Validate the body of POST /api/jobs/<id>/state."""
    unknown = sorted(set(body) - {'status', 'notes', *STATE_FLAGS})
    if unknown:
        raise ApiError(HTTPStatus.BAD_REQUEST, f'unknown field: {unknown[0]}')
    if not body:
        raise ApiError(HTTPStatus.BAD_REQUEST, 'send at least one of saved, hidden, seen, status, notes')
    for flag in STATE_FLAGS:
        if flag in body and not isinstance(body[flag], bool):
            raise ApiError(HTTPStatus.BAD_REQUEST, f'{flag} must be true or false')
    if 'status' in body and body['status'] not in USER_STATUSES:
        raise ApiError(HTTPStatus.BAD_REQUEST, f'status must be one of {", ".join(USER_STATUSES)}')
    if 'notes' in body:
        if not isinstance(body['notes'], str):
            raise ApiError(HTTPStatus.BAD_REQUEST, 'notes must be text')
        if len(body['notes']) > MAX_NOTES_CHARS:
            raise ApiError(HTTPStatus.BAD_REQUEST, f'notes must be at most {MAX_NOTES_CHARS} characters')
    return body


def export_csv(rows):
    """All rows as CSV bytes with a UTF-8 BOM so Excel reads the encoding correctly."""
    columns = list(dict.fromkeys(key for row in rows for key in row))
    out = io.StringIO(newline='')
    writer = csv.writer(out, lineterminator='\r\n')
    writer.writerow(csv_cell(name) for name in columns)
    for row in rows:
        writer.writerow(csv_cell(row.get(name)) for name in columns)
    return b'\xef\xbb\xbf' + out.getvalue().encode('utf-8')


def make_handler(store, config, token, scan_controller):
    """Build the request handler class. Exposed so tests can inject a fake store and controller."""

    class Handler(BaseHTTPRequestHandler):
        server_version = 'PegaRadar'
        sys_version = ''
        timeout = SOCKET_TIMEOUT_SECONDS      # a stalled client cannot hold a thread for ever

        # ---- plumbing -------------------------------------------------------------------

        def log_request(self, code='-', size='-'):
            """Successful requests are not logged; errors still reach stderr through log_error."""

        def end_headers(self):
            for name, value in SECURITY_HEADERS.items():
                self.send_header(name, value)
            super().end_headers()

        def send_body(self, status, content_type, body, extra_headers=()):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            for name, value in extra_headers:
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            self.send_body(status, 'application/json; charset=utf-8', body)

        def dispatch(self, route):
            try:
                self.require_loopback_host()
                route()
            except ApiError as exc:
                self.send_json(exc.status, {'error': exc.message})
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                self.close_connection = True          # the browser went away or stalled mid-request
            except Exception:
                # Written directly: log_error() escapes newlines, which makes a traceback unreadable.
                print(f'Pega Radar: unhandled error for {self.command} {self.path!r}\n{traceback.format_exc()}',
                      file=sys.stderr, flush=True)
                self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {'error': 'internal error'})

        def own_hosts(self):
            port = self.server.server_address[1]
            return {f'{name}:{port}' for name in HOST_NAMES}

        def require_loopback_host(self):
            """Refuse any Host that is not this server on loopback (stops DNS rebinding)."""
            if self.headers.get('Host', '').strip().lower() not in self.own_hosts():
                raise ApiError(HTTPStatus.FORBIDDEN, 'this server only answers on 127.0.0.1')

        # ---- GET ------------------------------------------------------------------------

        def do_GET(self):
            self.dispatch(self.route_get)

        def route_get(self):
            url = urlsplit(self.path)
            path = url.path
            if path == '/':
                self.send_static('index.html')
            elif path.startswith('/static/'):
                self.send_static(path[len('/static/'):])
            elif path == '/api/bootstrap':
                self.send_json(HTTPStatus.OK, self.bootstrap())
            elif path == '/api/jobs':
                query = parse_jobs_query(url.query)
                jobs, total = store.jobs(**query)
                counts = {view: total if view == query['view'] else
                          store.jobs(**{**query, 'view': view, 'limit': 1, 'offset': 0})[1] for view in VIEWS}
                self.send_json(HTTPStatus.OK, {'jobs': jobs, 'total': total, 'counts': counts})
            elif path.startswith('/api/jobs/'):
                self.send_json(HTTPStatus.OK, self.find_job(path[len('/api/jobs/'):]))
            elif path == '/api/scan/status':
                self.send_json(HTTPStatus.OK, scan_controller.status())
            elif path == '/api/export.csv':
                filename = f'pega-radar-{date.today().isoformat()}.csv'
                self.send_body(HTTPStatus.OK, 'text/csv; charset=utf-8', export_csv(store.export_rows()),
                               [('Content-Disposition', f'attachment; filename="{filename}"')])
            else:
                raise ApiError(HTTPStatus.NOT_FOUND, 'not found')

        def send_static(self, name):
            """Serve one of the allow-listed files; the request path never reaches the filesystem."""
            content_type = STATIC_FILES.get(name)
            if content_type is None:
                raise ApiError(HTTPStatus.NOT_FOUND, 'not found')
            self.send_body(HTTPStatus.OK, content_type, (WEB_DIR / name).read_bytes())

        def bootstrap(self):
            return {
                'token': token,
                'profile': config.get('profile', {}),
                'stats': store.stats(),
                'latest_run': store.latest_run(),
                'scan': scan_controller.status(),
            }

        def find_job(self, raw_id):
            job = store.job(unquote(raw_id)) if raw_id and '/' not in raw_id else None
            if job is None:
                raise ApiError(HTTPStatus.NOT_FOUND, 'no such job')
            return job

        # ---- POST -----------------------------------------------------------------------

        def do_POST(self):
            self.dispatch(self.route_post)

        def route_post(self):
            body = self.read_mutation()
            path = urlsplit(self.path).path
            parts = path.split('/')
            if path == '/api/jobs/seen-all':
                self.send_json(HTTPStatus.OK, {'marked': store.mark_all_seen()})
            elif path == '/api/scan':
                if not scan_controller.start():
                    self.send_json(HTTPStatus.CONFLICT, {'error': 'a scan is already running',
                                                         'scan': scan_controller.status()})
                else:
                    self.send_json(HTTPStatus.ACCEPTED, {'scan': scan_controller.status()})
            elif len(parts) == 5 and parts[:3] == ['', 'api', 'jobs'] and parts[3] and parts[4] == 'state':
                state = store.set_state(unquote(parts[3]), **parse_state_update(body))
                if state is None:
                    raise ApiError(HTTPStatus.NOT_FOUND, 'no such job')
                self.send_json(HTTPStatus.OK, state)
            else:
                raise ApiError(HTTPStatus.NOT_FOUND, 'not found')

        def read_mutation(self):
            """Read and authorise a mutation: token, same origin, JSON content type, small object body."""
            raw = self.read_body()
            supplied = self.headers.get('X-Radar-Token', '')
            if not hmac.compare_digest(supplied.encode('utf-8'), token.encode('utf-8')):
                raise ApiError(HTTPStatus.FORBIDDEN, 'missing or wrong X-Radar-Token')
            origin = self.headers.get('Origin')
            if origin is not None and origin.strip().lower() not in {f'http://{host}' for host in self.own_hosts()}:
                raise ApiError(HTTPStatus.FORBIDDEN, 'cross-origin requests are not allowed')
            if self.headers.get_content_type() != 'application/json':
                raise ApiError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, 'Content-Type must be application/json')
            try:
                body = json.loads(raw.decode('utf-8'))
            except Exception:                         # bad UTF-8, bad JSON, or nesting deep enough to recurse out
                raise ApiError(HTTPStatus.BAD_REQUEST, 'body must be valid JSON') from None
            if not isinstance(body, dict):
                raise ApiError(HTTPStatus.BAD_REQUEST, 'body must be a JSON object')
            return body

        def read_body(self):
            try:
                length = int(self.headers.get('Content-Length', ''))
            except ValueError:
                raise ApiError(HTTPStatus.LENGTH_REQUIRED, 'Content-Length is required') from None
            if length < 0:
                raise ApiError(HTTPStatus.BAD_REQUEST, 'bad Content-Length')
            if length > MAX_BODY_BYTES:
                self.close_connection = True
                if length <= MAX_DRAIN_BYTES:
                    self.rfile.read(length)       # drain so the client can read the refusal
                raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, 'body too large')
            return self.rfile.read(length)

    return Handler


class LoopbackServer(ThreadingHTTPServer):
    daemon_threads = True
    # On Windows SO_REUSEADDR would let a second process bind the same port, so only reuse on POSIX.
    allow_reuse_address = os.name != 'nt'


def bind_server(handler, port):
    """Bind 127.0.0.1 on `port`, or the next free port after it."""
    last_error = None
    for candidate in range(port, port + PORT_ATTEMPTS):
        try:
            return LoopbackServer((BIND_HOST, candidate), handler)
        except OSError as exc:
            last_error = exc
    raise OSError(f'no free port between {port} and {port + PORT_ATTEMPTS - 1}') from last_error


def serve(store, config, *, port=8765, open_browser=True):
    """Serve the website on 127.0.0.1 until Ctrl+C."""
    token = secrets.token_urlsafe(32)
    handler = make_handler(store, config, token, ScanController(store, config))
    httpd = bind_server(handler, port)
    url = f'http://{BIND_HOST}:{httpd.server_address[1]}/'
    print(f'Pega Radar is running at {url}  (Ctrl+C to stop)', flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('Stopped.', file=sys.stderr)
    finally:
        httpd.server_close()
