"""Job sources: LinkedIn guest search, employer applicant-tracking systems and India job boards.

`build_tasks` turns the configuration and the employer registry into `Task` objects for the
orchestrator. Every task returns a `make_result()` dict and never raises; a source that could
not be read is reported as `blocked`, `maintenance`, `partial` or `error` - never as `empty`.

Naukri and Foundit are deliberately absent: both refuse automated clients, and that refusal is
respected rather than worked around. Their own e-mail alerts cover them.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from ..model import company_key, make_result

LINKEDIN_PRIORITY = 0
ATS_FOCUS_PRIORITY = 10      # product companies and captive centres with a known Bengaluru team
ATS_PRIORITY = 20
BOARD_PRIORITY = 30
FOCUS_TYPES = ('product', 'gcc')

FALLBACK_TITLE = 'Pega role (title not given)'
WRONG_SHAPE = ('error', 'unexpected response shape')

_ISO_DAY = re.compile(r'\d{4}-\d{2}-\d{2}')


class Meter:
    """Counts one source's requests; `Http.requests` on the shared client is the whole run's total."""

    def __init__(self, http):
        self._http = http
        self.count = 0

    def get(self, url, **options):
        self.count += 1
        return self._http.get(url, **options)

    def post_json(self, url, payload, **options):
        self.count += 1
        return self._http.post_json(url, payload, **options)

    def expired(self):
        return self._http.expired()

    def host_open(self, host):
        return self._http.host_open(host)


class Task:
    """One independently runnable source.

    `adapter(meter, ctx)` does the work and returns a result, or `(result, commit)` when the
    source keeps state between runs: `commit()` stores that state and is called by the
    orchestrator only once the result's jobs are safely saved.
    """

    def __init__(self, name, label, kind, priority, adapter, source=None):
        self.name, self.label, self.kind, self.priority = name, label, kind, priority
        self.source = source or label
        self._adapter = adapter
        self._pending = None

    def run(self, http, ctx):
        self._pending = None
        try:
            if http.expired():
                return make_result(self.source, self.label, self.kind, status='skipped',
                                   error='the time budget ran out before this source started')
            outcome = self._adapter(Meter(http), ctx)
            if isinstance(outcome, tuple):
                outcome, self._pending = outcome
            return outcome
        except Exception as error:  # a bug in one adapter must not stop the other sources
            log = ctx.get('log') if isinstance(ctx, dict) else None
            if log is not None:
                log.exception('source %s failed', self.name)
            return make_result(self.source, self.label, self.kind, status='error',
                               error=f'{type(error).__name__}: {str(error)[:160]}')

    def commit(self):
        """Store what the last `run` learned. Safe to call for any task, and at most once per run."""
        pending, self._pending = self._pending, None
        if pending is not None:
            pending()


def failure(response):
    """`(status, message)` for a response that did not succeed: a refusal is `blocked`, the rest `error`."""
    return ('blocked' if response.blocked else 'error'), (response.error or f'HTTP {response.status}')


def settle(source, label, kind, jobs, *, found, requests, problem=None, read_any=False):
    """Build the result. `problem` is the `(status, message)` of a failure, or None.

    A failure after part of the source was read (`read_any`) is `partial`; otherwise the
    failure's own status stands, so an unread source can never look like one with no openings.
    """
    if problem is None:
        status, error = ('ok' if jobs else 'empty'), None
    elif read_any:
        status, error = 'partial', problem[1]
    else:
        status, error = problem
    return make_result(source, label, kind, status=status, jobs=jobs, found=found, requests=requests, error=error)


def day(value):
    """'YYYY-MM-DD' from an ISO date or datetime string or from epoch milliseconds; None for anything else."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(value / 1000, timezone.utc).date().isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    match = _ISO_DAY.match(value) if isinstance(value, str) else None
    return match.group(0) if match else None


def records(value):
    """The dict rows of a feed list; anything else in the list is ignored."""
    return [row for row in value if isinstance(row, dict)]


def number(value):
    """The value when it is a real number, else None (feeds mix numbers, strings and nulls)."""
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def is_focus(company):
    """A product company or captive centre whose Bengaluru Pega team is established by the research."""
    return company.get('type') in FOCUS_TYPES and company.get('bengaluru') is True


def registry_companies(registry):
    """The companies.json entries held by a `rank.Registry` (its `entries`), or a plain list of them."""
    for attribute in ('entries', 'companies'):
        if hasattr(registry, attribute):
            return list(getattr(registry, attribute) or [])
    return list(registry or [])


def build_tasks(config, registry, store):
    """All tasks for one scan, lowest `priority` first: LinkedIn, employer sites, then job boards.

    `store` is not needed to build the tasks (adapters receive it through `ctx`); the parameter
    is part of the agreed signature.
    """
    # Imported here because these modules import the helpers above from this package.
    from . import ats, boards, linkedin

    companies = registry_companies(registry)
    tasks = [Task('linkedin', 'LinkedIn', 'linkedin', LINKEDIN_PRIORITY,
                  lambda http, ctx: linkedin.run(http, ctx, companies))]
    for company in companies:
        block = company.get('ats')
        if block:
            tasks.append(Task(ats.task_name(block), company['name'], 'ats',
                              ATS_FOCUS_PRIORITY if is_focus(company) else ATS_PRIORITY,
                              lambda http, ctx, company=company: ats.run(http, company['name'], company['ats']),
                              source=ats.SOURCE))
    for name, adapter in boards.BOARDS.items():
        tasks.append(Task('board:' + company_key(name), name, 'board', BOARD_PRIORITY,
                          lambda http, ctx, adapter=adapter: adapter(http)))
    return sorted(tasks, key=lambda task: task.priority)
