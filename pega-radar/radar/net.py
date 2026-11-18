"""A small, polite HTTP client shared by every source.

Resilient, not evasive: it spaces requests per host, honours
`Retry-After`, slows down when a host says "too many requests" and stops calling a host
that keeps refusing. It never raises for a network problem; the caller reads the outcome
from the returned `Response`.
"""
from __future__ import annotations

import email.utils
import json
import random
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

# The browser string the source endpoints were verified with; config.json's http.user_agent overrides it.
# It is the only browser-like header sent: no cookies, no sign-in, no other imitation.
USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36')
BLOCK_STATUSES = (401, 403, 406, 429, 999)
THROTTLE_STATUSES = (429, 999)
PACING_CAP = 8.0             # seconds; ceiling for a host's pacing after repeated throttling
BREAKER_THRESHOLD = 5        # consecutive blocked/failed responses before a host is given up
DECAY_AFTER = 3              # consecutive successes before a raised pacing is halved again
RETRY_AFTER_CAP = 600.0      # never trust a Retry-After longer than this many seconds
JITTER = 0.25                # up to +25 % on every gap so requests are not metronomic
MAX_BODY = 20 * 1024 * 1024  # bytes; a larger reply (also after gzip) is refused, never held in memory
TOO_LARGE = 'response too large'
BUDGET_SPENT = 'time budget exhausted'
CIRCUIT_OPEN = 'circuit open'
# Why a call failed, for coverage reports: timeout | tls | dns | refused (the site said no) |
# unreachable (no connection could be made or kept) | rate_limited | http_4xx | http_5xx, plus budget
# (time ran out), cap (reply too large) and shape (not a usable request or reply). '' means it did not fail.
REASONS = ('timeout', 'tls', 'dns', 'refused', 'unreachable', 'rate_limited', 'http_4xx', 'http_5xx', 'budget',
           'cap', 'shape')


def _status_reason(status) -> str:
    if status in THROTTLE_STATUSES:
        return 'rate_limited'
    if status in BLOCK_STATUSES:
        return 'refused'
    if status >= 500:
        return 'http_5xx'
    return 'http_4xx' if status >= 400 else ''


def _network_failure(error, host, timeout):
    """(reason, readable message) for an exception raised while talking to `host`.

    Certificate and name-resolution trouble is the user's network (proxy, antivirus, DNS), not the
    site refusing, so each gets its own reason and a message that says what to check.
    """
    cause = error.reason if isinstance(getattr(error, 'reason', None), BaseException) else error
    detail = f'{type(cause).__name__}: {str(cause)[:140]}'
    if isinstance(cause, ssl.SSLCertVerificationError):
        return 'tls', f'TLS certificate could not be verified — check proxy/antivirus certificate ({host})'
    if isinstance(cause, ssl.SSLError):
        return 'tls', f'TLS connection to {host} failed ({detail})'
    if isinstance(cause, socket.gaierror):
        return 'dns', f'DNS lookup failed for {host}'
    if isinstance(cause, TimeoutError) or 'timed out' in str(cause).lower():
        return 'timeout', f'Timed out after {timeout:g} s waiting for {host}'
    if isinstance(cause, ConnectionRefusedError):
        return 'refused', f'Connection refused by {host}'
    if isinstance(cause, OSError):
        # Reset, network down, no route, proxy trouble: nothing says the site itself refused.
        return 'unreachable', f'Could not reach {host} ({detail})'
    return 'shape', f'Unusable reply from {host} ({detail})'


class Response:
    """The outcome of one call. `status` is 0 when no HTTP answer was received.

    `reason` classifies a failure (see REASONS) and is '' for a success; `error` is the readable text.
    """

    def __init__(self, status, text, url, error='', headers=None, reason=None):
        self.status, self.text, self.url, self.error = status, text, url, error
        self.reason = _status_reason(status) if reason is None else reason
        self._headers = {str(key).lower(): value for key, value in (headers or {}).items()}

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    @property
    def blocked(self) -> bool:
        return self.status in BLOCK_STATUSES

    def json(self):
        try:
            return json.loads(self.text)
        except (ValueError, TypeError):
            return None

    def header(self, name):
        return self._headers.get(str(name).lower())

    def __repr__(self):
        return f'Response(status={self.status}, url={self.url!r}, error={self.error!r}, reason={self.reason!r})'


class _Host:
    """Pacing, counters and breaker state for one hostname. Guarded by Http._lock."""

    __slots__ = ('base', 'pacing', 'next_at', 'requests', 'blocked', 'errors', 'failures', 'successes', 'open', 'reason')

    def __init__(self, base):
        self.base = self.pacing = max(0.0, float(base))
        self.next_at = 0.0
        self.requests = self.blocked = self.errors = 0
        self.failures = self.successes = 0   # consecutive counts
        self.open = False
        self.reason = ''                     # why the last failure happened; reported while the breaker is open


def _default_opener(request, timeout):
    return urllib.request.urlopen(request, timeout=timeout)


def _retry_after(value, now_wall):
    """Seconds requested by a Retry-After header (delta-seconds or HTTP date), or None."""
    if not value:
        return None
    value = str(value).strip()
    try:
        seconds = float(value)
    except ValueError:
        try:
            seconds = email.utils.parsedate_to_datetime(value).timestamp() - now_wall
        except (TypeError, ValueError, OverflowError):
            return None
    return min(RETRY_AFTER_CAP, max(0.0, seconds))


class Http:
    def __init__(self, *, deadline=None, stop=None, pacing=None, default_pacing=0.5, timeout=25, opener=None,
                 user_agent=None):
        self.deadline = deadline                      # a time.monotonic() value, or None
        self.stop = stop or threading.Event()
        self.default_pacing = default_pacing
        self.timeout = timeout
        self.user_agent = user_agent or USER_AGENT
        self.requests = 0                             # total attempts actually sent
        self._pacing = {str(host).lower(): seconds for host, seconds in (pacing or {}).items()}
        self._opener = opener or _default_opener
        self._hosts = {}
        self._lock = threading.Lock()
        # Indirections so tests can run on a fake clock without real waiting.
        self._clock = time.monotonic
        self._sleep = self.stop.wait

    # ── public API ──

    def get(self, url, *, headers=None, accept='application/json', retries=2) -> Response:
        return self._send(url, None, headers, accept, retries)

    def post_json(self, url, payload, *, headers=None, retries=2) -> Response:
        body = json.dumps(payload).encode('utf-8')
        merged = {'Content-Type': 'application/json', **(headers or {})}
        return self._send(url, body, merged, 'application/json', retries)

    def expired(self) -> bool:
        return self.stop.is_set() or (self.deadline is not None and self._clock() >= self.deadline)

    def host_open(self, url_or_host) -> bool:
        """False while that host's circuit breaker is open."""
        text = str(url_or_host or '')
        host = (urllib.parse.urlsplit(text).hostname if '://' in text else text) or ''
        with self._lock:
            state = self._hosts.get(host.lower())
            return not (state and state.open)

    def host_report(self) -> dict:
        with self._lock:
            return {host: {'requests': state.requests, 'blocked': state.blocked, 'errors': state.errors,
                           'pacing': round(state.pacing, 2)}
                    for host, state in self._hosts.items()}

    # ── internals ──

    def _send(self, url, data, headers, accept, retries):
        parts = urllib.parse.urlsplit(str(url))
        host = (parts.hostname or '').lower()
        if parts.scheme not in ('http', 'https') or not host:
            return Response(0, '', url, 'unsupported URL', reason='shape')
        merged = {'User-Agent': self.user_agent, 'Accept': accept, 'Accept-Language': 'en-US,en;q=0.9',
                  'Accept-Encoding': 'gzip'}
        merged.update(headers or {})
        last = Response(0, '', url, 'not attempted')
        for attempt in range(max(0, int(retries)) + 1):
            refusal = self._take_turn(host)
            if refusal:
                # Keep the real failure visible when the budget runs out between retries.
                if attempt and refusal == BUDGET_SPENT:
                    return last
                return Response(0, '', url, refusal, reason='budget' if refusal == BUDGET_SPENT else self._last_reason(host))
            last = self._attempt(url, data, merged, host)
            if last.error == TOO_LARGE:
                return last                      # asking again would only download it again
            if not self._record(host, last, attempt):
                return last
        return last

    def _last_reason(self, host):
        with self._lock:
            state = self._hosts.get(host)
            return (state.reason if state else '') or 'unreachable'

    def _take_turn(self, host):
        """Wait for this host's next free slot. Returns a reason string when the call must not be made."""
        if self.expired():
            return BUDGET_SPENT
        with self._lock:
            state = self._hosts.get(host)
            if state is None:
                state = self._hosts[host] = _Host(self._pacing.get(host, self.default_pacing))
            if state.open:
                return CIRCUIT_OPEN
            now = self._clock()
            slot = max(now, state.next_at)
            if self.deadline is not None and slot >= self.deadline:
                return BUDGET_SPENT   # the slot is past the budget: do not sleep for nothing
            state.next_at = slot + state.pacing * (1 + random.uniform(0, JITTER))
        if slot > now:
            self._sleep(slot - now)
            if self.expired():
                return BUDGET_SPENT
        with self._lock:
            if state.open:                       # another thread tripped the breaker while we waited
                return CIRCUIT_OPEN
            state.requests += 1
            self.requests += 1
        return None

    def _attempt(self, url, data, headers, host):
        try:
            request = urllib.request.Request(url, data=data, headers=headers)
            reply = self._opener(request, self.timeout)
            try:
                status = getattr(reply, 'status', None) or reply.getcode()
                reply_headers = dict(reply.headers.items())
                final_url = reply.geturl() if hasattr(reply, 'geturl') else url
                body = reply.read(MAX_BODY + 1)
            finally:
                close = getattr(reply, 'close', None)
                if close:
                    close()
        except urllib.error.HTTPError as error:
            reply_headers = dict(error.headers.items()) if error.headers else {}
            try:
                body = error.read(MAX_BODY + 1)
            except Exception:
                body = b''
            status, final_url = error.code, url
        except Exception as error:   # URLError, timeout, TLS, connection reset, malformed reply
            reason, message = _network_failure(error, host, self.timeout)
            return Response(0, '', url, message, reason=reason)
        text = self._decode(body, reply_headers)
        if text is None:
            return Response(0, '', url, TOO_LARGE, reason='cap')
        return Response(status, text, final_url, '' if 200 <= status < 300 else f'HTTP {status}', reply_headers)

    @staticmethod
    def _decode(body, headers):
        """The reply as text, or None when it is larger than MAX_BODY before or after decompression."""
        if isinstance(body, str):
            body = body.encode('utf-8', errors='replace')
        body = body or b''
        if len(body) > MAX_BODY:
            return None
        encoding = next((value for key, value in headers.items() if key.lower() == 'content-encoding'), '')
        if 'gzip' in str(encoding).lower():
            try:
                inflater = zlib.decompressobj(wbits=31)
                inflated = inflater.decompress(body, MAX_BODY + 1)   # bounded: a small reply cannot expand without limit
                if len(inflated) > MAX_BODY or inflater.unconsumed_tail:
                    return None
                body = inflated
            except zlib.error:
                pass   # mislabelled body: fall through with the raw bytes
        return body.decode('utf-8', errors='replace')

    def _record(self, host, response, attempt):
        """Update the host's state from one response. Returns True when the call should be retried."""
        status = response.status
        throttled = status in THROTTLE_STATUSES
        failed = status == 0 or status >= 500
        with self._lock:
            state = self._hosts[host]
            if not (throttled or failed or response.blocked):
                state.failures = 0
                if status < 400:
                    state.successes += 1
                    if state.successes >= DECAY_AFTER and state.pacing > state.base:
                        state.pacing = max(state.base, state.pacing / 2)
                        state.successes = 0
                return False
            state.successes = 0
            state.failures += 1
            state.reason = response.reason
            if response.blocked:
                state.blocked += 1
            else:
                state.errors += 1
            if state.failures >= BREAKER_THRESHOLD:
                state.open = True
                return False
            if not (throttled or failed):
                return False                     # 401/403/406: a refusal is an answer, not a glitch
            pause = _retry_after(response.header('Retry-After'), time.time())
            if throttled:
                state.pacing = min(max(PACING_CAP, state.base), state.pacing * 2)
                if pause is None:
                    pause = min(60.0, 4.0 * 2 ** attempt)
            elif pause is None:
                pause = 2.0 * (attempt + 1)
            # Back off this host only; every thread using it waits, other hosts keep going.
            state.next_at = max(state.next_at, self._clock() + pause)
            return True
