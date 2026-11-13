"""Run the original portal scanner unattended, using the same routes and saved state.

Exit codes: 0 = selected checks completed without access errors; 1 = execution or
configuration failure; 2 = partial checks/detail access; 3 = all selected queries
blocked or failed; 128 + signal = paused after SIGINT/SIGTERM. Zero results can be
a successful query, but no return code means a vacancy or salary is confirmed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
import json
import os
from pathlib import Path
import signal
import sys
import threading
from typing import Callable

from app import BASE, create_app
from campaign import load_campaign
from portal_scan import MODE_CATEGORY


@dataclass
class JobResult:
    exit_code: int
    summary: dict


class StopRequest:
    """The signal handler only records intent; the polling loop requests pause."""
    def __init__(self):
        self.event = threading.Event()
        self.signum = None

    def request(self, signum=signal.SIGTERM, frame=None):
        if self.signum is None:
            self.signum = signum
        self.event.set()


@contextmanager
def signal_handlers(stop):
    previous = {}
    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, stop.request)
        yield
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def json_request(client, method, url, **kwargs):
    response = getattr(client, method)(url, **kwargs)
    payload = response.get_json(silent=True)
    if response.status_code >= 400:
        message = payload.get('error') if isinstance(payload, dict) else None
        raise RuntimeError(message or f'{url}: HTTP {response.status_code}')
    if not isinstance(payload, dict):
        raise RuntimeError(f'{url} did not return a JSON object')
    return payload


def selected_summary(document, targets):
    wanted = {target['target_id'] for target in targets}
    indexed = {row.get('target_id'): row for row in document.get('targets', [])}
    records = [indexed.get(target_id, {'status': 'pending', 'jobs': []}) for target_id in wanted]
    counts = Counter(row.get('status', 'pending') for row in records)
    successful = counts['results'] + counts['no_matches']
    failed = counts['blocked'] + counts['error']
    incomplete = len(records) - successful - failed
    partial_queries = sum(bool(record.get('partial')) for record in records)
    jobs = {}
    for record in records:
        for job in record.get('jobs', []):
            if job.get('url'):
                prior = jobs.get(job['url'])
                # A failed duplicate must not be hidden behind a successful copy.
                if prior is None or job.get('job_detail_status') in ('unavailable', 'identity_unconfirmed', 'description_missing'):
                    jobs[job['url']] = job
    details = Counter(job.get('job_detail_status', 'not_checked') for job in jobs.values())
    detail_gaps = sum(details[key] for key in ('unavailable', 'identity_unconfirmed', 'description_missing', 'not_checked'))
    if wanted and failed == len(wanted):
        code, outcome = 3, 'all_queries_blocked_or_failed'
    elif incomplete or failed or detail_gaps or partial_queries:
        code, outcome = 2, 'partial'
    else:
        code, outcome = 0, 'completed'
    return JobResult(code, {
        'outcome': outcome,
        'selected_targets': len(wanted),
        'query_outcomes': dict(counts),
        'successful_queries': successful,
        'incomplete_queries': incomplete,
        'partial_queries': partial_queries,
        'retained_job_candidates': len(jobs),
        'description_outcomes': dict(details),
        'checkpoint_updated_at': document.get('updated_at'),
        'meaning': 'Counts describe public-source checks and retained candidates, not confirmed vacancies or salary budgets.',
    })


def run_job(application, research_dir, *, mode='gcc_top10', resume=False,
            dry_run=False, stop=None, poll_seconds=1.0, emit: Callable | None = None):
    """Use an isolated Flask client; no listening server or cloud credentials."""
    if mode not in MODE_CATEGORY:
        raise ValueError('Choose a supported scanner mode.')
    if poll_seconds <= 0:
        raise ValueError('The polling interval must be positive.')
    stop = stop or StopRequest()
    emit = emit or (lambda event: None)
    client = application.test_client()
    store = application.extensions['store']
    previous = store.get('meta', 'scanner_selection', {}) if resume else {}
    if resume and not previous.get('targets'):
        raise RuntimeError('No saved scan selection to resume. Start a scan with --mode first.')
    options = json_request(client, 'get', '/api/scan-options')
    choices = {row['mode']: row for rows in options['categories'].values() for row in rows}
    effective_mode = previous.get('mode', mode)
    count = len(previous['targets']) if resume else choices[mode]['count']
    if dry_run:
        return JobResult(0, {
            'outcome': 'dry_run', 'mode': effective_mode, 'resume': resume,
            'selected_targets': count, 'catalogue_targets': options['total_targets'],
            'meaning': 'Selection only. No queries were sent and no scan was started.',
        })
    if stop.event.is_set():
        return JobResult(128 + int(stop.signum or signal.SIGTERM), {'outcome': 'cancelled_before_start'})
    bootstrap = json_request(client, 'get', '/api/bootstrap')
    headers = {'X-Career-Token': bootstrap['token']}
    started = json_request(client, 'post', '/api/scan',
                           json={'mode': mode, 'resume': resume}, headers=headers)
    emit({'event': 'started', 'mode': started['mode'], 'selected_targets': started['total'], 'resume': resume})
    pause_sent = False
    latest = None
    while True:
        status = json_request(client, 'get', '/api/status')
        progress = {key: status.get(key) for key in ('running', 'phase', 'progress', 'total', 'current_company', 'error')}
        if progress != latest:
            emit({'event': 'progress', **progress})
            latest = progress
        if not status.get('running'):
            break
        if stop.event.is_set() and not pause_sent:
            # The worker can finish between status and pause. Only ignore that
            # precise race after reading a fresh, non-running status.
            response = client.post('/api/search/pause', json={}, headers=headers)
            if response.status_code >= 400:
                current = json_request(client, 'get', '/api/status')
                if current.get('running'):
                    payload = response.get_json(silent=True) or {}
                    raise RuntimeError(payload.get('error', 'Could not pause the scan.'))
            pause_sent = True
            emit({'event': 'pausing', 'signal': int(stop.signum or signal.SIGTERM),
                  'meaning': 'Finishing in-flight requests and saving completed results.'})
        # Wait on a fresh Event after cancellation so a set event does not busy-spin.
        if pause_sent:
            threading.Event().wait(poll_seconds)
        else:
            stop.event.wait(poll_seconds)
    selection = store.get('meta', 'scanner_selection', {})
    if status.get('error') or selection.get('status') == 'failed':
        return JobResult(1, {'outcome': 'failed', 'mode': effective_mode,
                            'error': status.get('error') or selection.get('error') or 'Scanner failed.',
                            'meaning': 'Previously saved results remain available; use --resume to retry pending work.'})
    if stop.event.is_set() or selection.get('status') == 'paused':
        return JobResult(128 + int(stop.signum or signal.SIGTERM), {
            'outcome': 'paused', 'mode': effective_mode, 'selected_targets': len(selection.get('targets', [])),
            'meaning': 'Completed work is saved. Use --resume with the same data and research directories.',
        })
    if selection.get('status') != 'complete':
        return JobResult(1, {'outcome': 'interrupted', 'mode': effective_mode,
                            'error': 'Scanner stopped without completing its saved selection.'})
    document = load_campaign(Path(research_dir) / 'preloaded_search.json')
    result = selected_summary(document, selection['targets'])
    result.summary.update(mode=selection['mode'], resume=resume)
    return result


def positive_float(value):
    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError('must be positive')
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=sorted(MODE_CATEGORY), default='gcc_top10')
    parser.add_argument('--research-dir', type=Path, default=Path(os.environ.get('PEGA_RESEARCH_DIR', BASE / 'research')))
    parser.add_argument('--data-dir', type=Path, default=Path(os.environ.get('PEGA_DATA_DIR', BASE / 'data')))
    parser.add_argument('--resume', action='store_true', help='Resume the saved mode, frozen target selection and baseline.')
    parser.add_argument('--dry-run', action='store_true', help='Report the same selection counts as the portal without network queries.')
    parser.add_argument('--poll-seconds', type=positive_float, default=1.0)
    args = parser.parse_args(argv)
    stop = StopRequest()
    def emit(event):
        print(json.dumps(event, ensure_ascii=True), flush=True)
    try:
        with signal_handlers(stop):
            application = create_app(data_dir=args.data_dir, research_dir=args.research_dir)
            result = run_job(application, args.research_dir, mode=args.mode, resume=args.resume,
                             dry_run=args.dry_run, stop=stop, poll_seconds=args.poll_seconds, emit=emit)
    except Exception as error:
        result = JobResult(1, {'outcome': 'failed', 'error': str(error)})
    emit({'event': 'finished', 'exit_code': result.exit_code, **result.summary})
    return result.exit_code


if __name__ == '__main__':
    raise SystemExit(main())
