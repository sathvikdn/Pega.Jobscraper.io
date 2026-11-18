"""The scan orchestrator: run every source, save what each one finds as it arrives, report coverage.

A source that fails, raises or runs out of time is recorded as such; it never stops the
other sources and is never reported as "nothing found".
"""
from __future__ import annotations

import logging
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .model import EMPLOYER_SOURCE, KINDS, STATUSES, company_key, make_result, needs_attention, now_iso
from .net import Http
from .rank import load_registry, load_targets, make_ranker
from .store import unreached

PROJECT_DIR = Path(__file__).resolve().parent.parent
LINKEDIN_HOST = 'www.linkedin.com'
LOCK_NAME = 'scan.lock'
LOCK_STALE_HOURS = 3          # longer than the scheduled task's 2 hour limit
FIRST_RUN_WINDOW = 30
DEFAULT_MINUTES = 40
DEFAULT_WORKERS = 6
KV_PROGRESS = 'scan_progress'
KV_LAST_COMPLETE = 'last_complete_at'
KV_LINKEDIN_OK = 'linkedin_last_ok_at'
KV_MATRIX = 'coverage_matrix'
MODES = ('full', 'retry', 'only')
_RESULT_KEYS = ('source', 'label', 'kind', 'status', 'found', 'kept', 'requests', 'error', 'jobs')

logger = logging.getLogger('radar')


class ScanLocked(RuntimeError):
    """Another scan already holds the lock."""


# ───────────────────────────── single-scan lock ─────────────────────────────

def process_alive(pid) -> bool:
    """True when `pid` is a running process (Windows and POSIX)."""
    if pid <= 0:
        return False
    if os.name == 'nt':
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel32.CloseHandle(handle)
        return code.value == 259                            # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True                                         # exists, owned by another user


def _lock_is_live(path) -> bool:
    """A lock counts while its owner process is running and it is younger than LOCK_STALE_HOURS."""
    try:
        owner = int(path.read_text(encoding='utf-8').split()[0])
        age = time.time() - path.stat().st_mtime
    except (OSError, ValueError, IndexError):
        return False
    return age < LOCK_STALE_HOURS * 3600 and process_alive(owner)


@contextmanager
def scan_lock(data_dir):
    """Hold the one-scan-at-a-time lock for `data_dir`. Raises ScanLocked while another scan runs.

    The lock file records the owning process, so a lock left by a crash, a reboot or the
    Task Scheduler time limit is taken over instead of blocking every later scan.
    """
    path = Path(data_dir) / LOCK_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            # Exclusive create: two scans starting together cannot both get the lock.
            with open(path, 'x', encoding='utf-8') as handle:
                handle.write(f'{os.getpid()} {now_iso()}')
            break
        except FileExistsError:
            if _lock_is_live(path):
                raise ScanLocked('Another scan is already running. Wait for it to finish.') from None
            try:
                path.unlink()
            except OSError:
                pass
    else:
        raise ScanLocked('The scan lock could not be taken over; try again in a moment.')
    try:
        yield path
    finally:
        try:
            path.unlink()
        except OSError:
            pass


# ───────────────────────────── helpers ─────────────────────────────

def window_days(last_complete_at, now=None) -> int:
    """Look-back for time-windowed searches: days since the last good sweep + 2 (3 to 30).

    `last_complete_at` is when the time-windowed source (LinkedIn) last answered in full.
    """
    if not last_complete_at:
        return FIRST_RUN_WINDOW
    try:
        last = datetime.fromisoformat(str(last_complete_at))
    except ValueError:
        return FIRST_RUN_WINDOW
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    gap = ((now or datetime.now(timezone.utc)) - last).total_seconds() / 86400
    return min(FIRST_RUN_WINDOW, max(3, int(gap) + 2))


def _positive(value, default) -> float:
    """`value` as a positive number, or `default` when it is missing, malformed or not positive."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def setup_console_logging():
    """Send the radar log to the console; a cp1252 console must not crash on a company name."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors='replace')
        except (AttributeError, ValueError):
            pass
    if not any(getattr(handler, '_radar_console', False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s  %(levelname)-7s  %(message)s', '%H:%M:%S'))
        handler._radar_console = True
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)


@contextmanager
def _log_file(directory):
    """Write this scan's log to <data>/logs/scan-YYYYMMDD-HHMMSS.log. Logging trouble never stops a scan."""
    handler = None
    try:
        directory.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(directory / f'scan-{datetime.now().strftime("%Y%m%d-%H%M%S")}.log', encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s  %(levelname)-7s  %(message)s'))
        logger.addHandler(handler)
        if logger.level == logging.NOTSET or logger.level > logging.INFO:
            logger.setLevel(logging.INFO)
    except OSError:
        handler = None
    try:
        yield
    finally:
        if handler is not None:
            logger.removeHandler(handler)
            handler.close()


def _error_result(task, message, reason=''):
    kind = getattr(task, 'kind', None)
    kind = kind if kind in KINDS else 'board'
    label = getattr(task, 'label', None) or getattr(task, 'name', None) or 'source'
    return make_result(EMPLOYER_SOURCE if kind == 'ats' else label, label, kind, status='error', error=message,
                       reason=reason)


def _run_task(task, http, ctx):
    """Run one source and return `(result, started)`. Whatever happens inside it, a well-formed
    result comes back, stamped with the task's name, its employer and how long it took."""
    if http.expired():
        result, started = _error_result(task, 'not run: the time budget was used up before this source started',
                                        'budget'), False
    else:
        started, began = True, time.monotonic()
        try:
            result = task.run(http, ctx)
        except Exception as error:   # a source bug must cost that source only
            logger.exception('%s raised', getattr(task, 'label', task))
            result = _error_result(task, f'{type(error).__name__}: {str(error)[:200]}')
        if (not isinstance(result, dict) or any(key not in result for key in _RESULT_KEYS)
                or result['status'] not in STATUSES):
            result = _error_result(task, 'the source returned a malformed result', 'shape')
        result.setdefault('elapsed_s', round(time.monotonic() - began, 1))
        if result.get('reason') == 'budget' and unreached(result) and not result.get('jobs'):
            # It started as the time ran out and got no answer at all: that is not an attempt either.
            started = False
    result['task'] = getattr(task, 'name', None) or result['label']
    if getattr(task, 'employer', None):
        result.setdefault('employer', task.employer)
    if not result.get('reason'):
        # Sources written before reasons existed still say enough through their status.
        result['reason'] = {'maintenance': 'maintenance', 'blocked': 'refused'}.get(result['status'], '')
    return result, started


def _name_key(name) -> str:
    return company_key(name) or str(name or '').strip().lower()


def _select(tasks, mode, only, history, full_run_seq, registry=None):
    """The tasks this run should attempt, and any `only` names that matched nothing."""
    if mode == 'only':
        wanted = {_name_key(name): name for name in only or () if str(name).strip()}
        # An alias ("CBA") selects the employer it belongs to in companies.json.
        canonical = {key: registry.canonical_key(name) if registry is not None else key for key, name in wanted.items()}
        chosen, matched = [], set()
        for task in tasks:
            keys = {_name_key(getattr(task, attribute, None)) for attribute in ('name', 'label', 'employer')} - {''}
            hits = {key for key in wanted if key in keys or canonical[key] in keys}
            if hits:
                chosen.append(task)
                matched |= hits
        return chosen, [name for key, name in wanted.items() if key not in matched]
    if mode == 'retry':
        def incomplete(task):
            last = history.get(getattr(task, 'name', None))
            # Never attempted, left out of the latest full run (budget, crash), or it needs attention.
            return (last is None or needs_attention(last)
                    or (full_run_seq is not None and last['run_seq'] < full_run_seq))
        return [task for task in tasks if incomplete(task)], []
    return list(tasks), []


def _fair_order(tasks, history):
    """Portals and boards in the order they should start: those never read by a full scan first,
    then those whose last read in a full scan is oldest. A source the budget cut off was not read,
    so it goes to the front next time and a backlog rotates through instead of the same sources
    being cut off every day. Narrow `only` and retry runs do not count, so trying one employer by
    hand does not send it to the back. Within one full scan's cohort the configured priority decides."""
    def key(task):
        last = history.get(getattr(task, 'name', None))
        # Run numbers, not timestamps: exact even for two runs in the same second. The task name
        # settles what is left, so the order never depends on how the task list happened to arrive.
        return ((last or {}).get('attempted_full_run_seq') or 0, getattr(task, 'priority', 100),
                str(getattr(task, 'name', '')))
    return sorted(tasks, key=key)


def _board_owners(tasks) -> dict:
    """{board: the task that fetches it}. Always the same task for a board, whatever is selected or
    whichever waited longest: "possibly closed" compares a board's listing with what that same task
    listed before, so the reader must not change from run to run."""
    owners = {}
    for task in sorted(tasks, key=lambda item: (getattr(item, 'priority', 100), str(getattr(item, 'name', '')))):
        board = getattr(task, 'board', None)
        if board:
            owners.setdefault(board, task)
    return owners


def _split_shared(ordered, owners):
    """Tasks to run, and {task name: [tasks whose board that task fetches for them]}.

    A board several employers share is read once, by its owner, at the place in the order of the
    first of them.
    """
    runners, followers, placed = [], {}, set()
    for task in ordered:
        owner = owners.get(getattr(task, 'board', None)) or task
        if owner is not task:
            followers.setdefault(owner.name, []).append(task)
        if id(owner) not in placed:
            placed.add(id(owner))
            runners.append(owner)
    return runners, followers


def _own_share(task, result, canonical) -> int:
    """How many of a result's jobs belong to the task's own employer."""
    employer = getattr(task, 'employer', None) or task.label
    return sum(1 for job in result.get('jobs') or () if isinstance(job, dict)
               and canonical(job.get('company')) == canonical(employer))


def _shared_outcome(follower, primary, result, canonical):
    """The outcome for an employer whose shared board was fetched by `primary`: the same status and
    reason, with the jobs that the board attributed to this employer."""
    employer = getattr(follower, 'employer', None) or follower.label
    mine = _own_share(follower, result, canonical)
    status = result['status'] if result['status'] not in ('ok', 'empty') else ('ok' if mine else 'empty')
    outcome = make_result(result['source'], follower.label, follower.kind if follower.kind in KINDS else 'ats',
                          status=status, found=result['found'], error=result.get('error'), reason=result.get('reason'),
                          pages_complete=result.get('pages_complete'), details_complete=result.get('details_complete'),
                          employer=employer, elapsed_s=0)
    outcome.update(task=follower.name, kept=mine, shared_with=primary.name)
    del outcome['jobs']
    return outcome


def load_inventory(config):
    """`(registry, targets)` from companies.json and targets.json, at the paths the scan itself uses:
    `config['companies_path']` and `config['targets_path']`, defaulting to the project folder."""
    return (load_registry(config.get('companies_path') or PROJECT_DIR / 'companies.json'),
            load_targets(config.get('targets_path') or PROJECT_DIR / 'targets.json'))


def _task_names(tasks) -> dict:
    """{employer: [names of its portal tasks]} for a list of tasks."""
    names = {}
    for task in tasks:
        if getattr(task, 'employer', None) and getattr(task, 'name', None):
            names.setdefault(task.employer, []).append(task.name)
    return names


def portal_tasks(registry, config=None) -> dict:
    """{employer: [task names]} for the portals configured today, as the scan would build them.

    Coverage reads outcomes through this, so only what is configured now counts. Builds the task
    objects without running them; no network and no store access.
    """
    try:
        from .sources import build_tasks
        return _task_names(build_tasks(config or {}, registry, None))
    except Exception:
        logger.exception('The configured portal tasks could not be listed')
        return {}


def load_coverage(store, config):
    """`(rows, summary)` for the Coverage view and exports, from the same files and task names the scan uses."""
    registry, targets = load_inventory(config)
    rows = store.coverage(registry, targets, portal_tasks(registry, config))
    return rows, store.coverage_summary(rows)


def _coverage_states(store, registry, targets, task_names) -> dict:
    """{employer or original target: where it stands}: its latest outcome, 'never attempted' for a
    configured employer with none, otherwise its inventory state."""
    def state(row):
        if row['inventory_state'] != 'configured':
            return row['inventory_state']
        return row['latest_status'] or 'never attempted'
    return {row['canonical'] or 'target: ' + row['original_names'][0]: state(row)
            for row in store.coverage(registry, targets, task_names)}


def _commit(task):
    """Let a source record its own progress (checkpoints) now that its result is safely stored.

    Never called when the save failed, so the next run searches again instead of believing
    work is done whose results were lost.
    """
    commit = getattr(task, 'commit', None)
    if callable(commit):
        try:
            commit()
        except Exception:
            logger.exception('%s: its progress could not be recorded', getattr(task, 'label', task))


def _sweep_complete(result) -> bool:
    """Did a time-windowed source cover its whole look-back window?

    A source that reports `sweep_complete` is believed, whatever its status: one unreadable
    description makes a sweep `partial` without leaving any day unsearched. Otherwise only an
    ok or empty result counts.
    """
    if result.get('sweep_complete') is not None:
        return result['sweep_complete'] is True
    return result['status'] in ('ok', 'empty')


class _Progress:
    """Live scan state, mirrored to kv['scan_progress'] and to the optional callback."""

    def __init__(self, store, callback, run_id, started_at, mode='full'):
        self._store, self._callback, self._lock = store, callback, threading.Lock()
        self._state = {'run_id': run_id, 'state': 'running', 'status': 'running', 'started_at': started_at,
                       'total': 0, 'done': 0, 'running': [], 'new': 0, 'attention': [], 'updated_at': started_at,
                       'mode': mode, 'requested': 0, 'attempted': 0, 'completed': 0, 'not_attempted': []}
        self.update()   # replace the previous run's finished snapshot before anything else can be polled

    def update(self, *, run_id=None, total=None, started=None, finished=None, new=0, attention=None, final_status=None,
               attempted=False, completed=False, not_attempted=None):
        with self._lock:
            state = self._state
            if run_id is not None:
                state['run_id'] = run_id
            if total is not None:
                state['total'] = state['requested'] = total
            state['attempted'] += bool(attempted)
            if not_attempted:
                state['not_attempted'].append(not_attempted)
            state['completed'] += bool(completed)
            if started:
                state['running'].append(started)
            if finished:
                state['done'] += 1
                if finished in state['running']:
                    state['running'].remove(finished)
            state['new'] += new
            if attention:
                state['attention'].append(attention)
            if final_status:
                state.update(state='finished', status=final_status, running=[])
            state['updated_at'] = now_iso()
            snapshot = {**state, 'running': list(state['running']), 'attention': list(state['attention']),
                        'not_attempted': list(state['not_attempted'])}
            try:
                self._store.kv_set(KV_PROGRESS, snapshot)
            except Exception:
                logger.warning('Scan progress could not be saved', exc_info=True)
        if self._callback:
            try:
                self._callback(snapshot)
            except Exception:
                logger.warning('The progress callback failed', exc_info=True)


# ───────────────────────────── the scan ─────────────────────────────

def run_scan(config, store, *, http=None, tasks=None, progress=None, minutes=None, mode='full', only=None) -> dict:
    """Run one scan and return its summary. A run that breaks part-way is recorded and returned as 'failed'.

    `mode` is 'full' (every scannable source), 'retry' (only sources whose latest outcome needs
    attention or that the latest full run never reached) or 'only' (the employers or task names
    in `only`; giving `only` implies it). Callers that must not overlap with another scan wrap
    this in `scan_lock(data_dir)`.
    """
    mode = 'only' if only else {'retry-incomplete': 'retry'}.get(mode, mode)
    if mode not in MODES:
        raise ValueError(f'unknown scan mode {mode!r}')
    with _log_file(store.path.parent / 'logs'):
        return _scan(config, store, http, tasks, progress, minutes, mode, only)


def _plan(config, store, http, tasks, minutes, mode, only, began) -> dict:
    """Everything a run needs before it starts: settings, inventory, the tasks and which of them to
    attempt. Reads only; a run row is created afterwards, and only if there is something to do."""
    scan_config = config.get('scan') if isinstance(config.get('scan'), dict) else {}
    budget = _positive(minutes, _positive(scan_config.get('minutes'), DEFAULT_MINUTES))
    registry, targets = load_inventory(config)
    if http is None:
        pacing = _positive((config.get('linkedin') or {}).get('pacing_seconds'), 1.0)
        http = Http(deadline=began + budget * 60, pacing={LINKEDIN_HOST: pacing},
                    user_agent=(config.get('http') or {}).get('user_agent'))
    if tasks is None:
        from .sources import build_tasks   # imported lazily: tests inject fake tasks instead
        tasks = build_tasks(config, registry, store)
    tasks = sorted(tasks, key=lambda task: (getattr(task, 'priority', 100), str(getattr(task, 'name', ''))))
    history = store.task_history()
    selected, unmatched = _select(tasks, mode, only, history, store.latest_full_run_seq(), registry)
    return {'budget': budget, 'workers': int(_positive(scan_config.get('workers'), DEFAULT_WORKERS)),
            'registry': registry, 'targets': targets, 'ranker': make_ranker(config, registry), 'http': http,
            'tasks': tasks, 'history': history, 'selected': selected, 'unmatched': unmatched,
            'task_names': _task_names(tasks)}


def _scan(config, store, http, tasks, progress, minutes, mode, only):
    began = time.monotonic()
    started_at = now_iso()
    # Published before anything else, so a poll never mistakes the previous run's finished snapshot
    # for this one. The run id follows once it is known that there is something to do.
    tracker = _Progress(store, progress, None, started_at, mode)
    plan = problem = None
    try:
        plan = _plan(config, store, http, tasks, minutes, mode, only, began)
    except Exception as error:   # recorded below as a failed run, like any other breakage
        problem = error
    summary = {'run_id': None, 'started_at': started_at, 'finished_at': None, 'minutes': 0.0, 'status': 'failed',
               'mode': mode, 'new': 0, 'new_bengaluru': 0, 'new_product_gcc': 0, 'requests': 0,
               'configured': len(plan['tasks']) if plan else 0, 'requested': 0, 'attempted': 0, 'completed': 0,
               'not_attempted': [], 'reasons': {}, 'unmatched': plan['unmatched'] if plan else [], 'sources': [],
               'attention': []}
    if plan and mode == 'retry' and plan['tasks'] and not plan['selected']:
        # Nothing is incomplete. This is not a scan: no run is recorded, so the last real run stays
        # the latest one and its coverage is not replaced by an empty one.
        logger.info('Nothing to retry: every source was read in full at its latest attempt')
        summary.update(status='nothing_to_retry', finished_at=now_iso())
        tracker.update(final_status='nothing_to_retry')
        return summary
    run_id = summary['run_id'] = store.start_run()
    tracker.update(run_id=run_id)
    registry = targets = before = task_names = None
    try:
        if problem is not None:
            raise problem
        budget, workers, registry, targets = plan['budget'], plan['workers'], plan['registry'], plan['targets']
        ranker, http, tasks, history, selected = plan['ranker'], plan['http'], plan['tasks'], plan['history'], plan['selected']
        task_names = plan['task_names']
        before = _coverage_states(store, registry, targets, task_names)
        if not tasks:
            raise RuntimeError('no sources are configured, so nothing was searched')
        if mode == 'only' and not selected:
            raise RuntimeError('none of the names given matches a source: ' + ', '.join(summary['unmatched']))
        # A board several employers share is read for all of them or not at all: whatever was selected,
        # every employer on it gets its outcome, its own job count and its own postings.
        boards = {getattr(task, 'board', None) for task in selected} - {None}
        selected = selected + [task for task in tasks if getattr(task, 'board', None) in boards and task not in selected]
        # LinkedIn's long sweep gets a worker of its own, so it neither waits behind the portals nor
        # holds one of their workers for the whole run.
        linkedin = [task for task in selected if getattr(task, 'kind', None) == 'linkedin']
        runners, followers = _split_shared(_fair_order([task for task in selected if task not in linkedin], history),
                                           _board_owners(tasks))
        summary['requested'] = len(selected)
        window = window_days(store.kv_get(KV_LINKEDIN_OK) or store.kv_get(KV_LAST_COMPLETE))
        summary['window_days'] = window
        ctx = {'window_days': window, 'store': store, 'config': config, 'log': logger}
        tracker.update(total=len(selected))
        logger.info('Scan %s (%s): %d of %d sources, look-back %d days, budget %g minutes',
                    run_id, mode, len(selected), len(tasks), window, budget)

        def work(task):
            tracker.update(started=task.label)
            return _run_task(task, http, ctx)

        def note(public, new, started):
            summary['sources'].append(public)
            flagged = needs_attention(public)
            if flagged:
                summary['attention'].append(public['label'])
                reason = public.get('reason') or 'unknown'
                summary['reasons'][reason] = summary['reasons'].get(reason, 0) + 1
            logger.log(logging.WARNING if flagged else logging.INFO, '%-28s %-11s kept %3d of %4d, %d new%s',
                       str(public['label'])[:28], public['status'], public['kept'], public['found'], new,
                       f' ({public["error"]})' if public.get('error') else '')
            tracker.update(finished=public['label'], new=new, attention=public['label'] if flagged else None,
                           attempted=started, completed=started and not flagged,
                           not_attempted=None if started else public['label'])

        with ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix='radar') as pool, \
                ThreadPoolExecutor(max_workers=1, thread_name_prefix='radar-linkedin') as linkedin_pool:
            pending = {linkedin_pool.submit(work, task): task for task in linkedin}
            pending.update({pool.submit(work, task): task for task in runners})
            for future in as_completed(pending):
                task, (result, started) = pending[future], future.result()
                sharing = followers.get(getattr(task, 'name', None), ())
                if sharing:
                    # The board's jobs are stored once, here; each employer on it is credited with its own,
                    # and each sighting is filed under the task of the employer the posting belongs to.
                    result['own_kept'] = _own_share(task, result, ranker.canonical)
                    result['shared_tasks'] = {
                        ranker.canonical(getattr(member, 'employer', None) or member.label): (member.name, member.label)
                        for member in (task, *sharing)}
                try:
                    saved = store.save_result(run_id, result, ranker)
                except Exception as error:
                    # The source answered but its jobs could not be stored: that is lost coverage too.
                    logger.exception('%s: saving failed', task.label)
                    failed = _error_result(task, f'could not be saved: {type(error).__name__}: {str(error)[:200]}')
                    failed.update({key: result[key] for key in ('task', 'employer', 'elapsed_s') if key in result})
                    result = failed
                    try:
                        saved = store.save_result(run_id, result, ranker)
                    except Exception:
                        # Even the health row failed. This source is reported from memory; the others carry on.
                        logger.exception('%s: the failure could not be recorded either', task.label)
                        saved = {'new': [], 'updated': [], 'kept': 0}
                else:
                    _commit(task)
                public = {key: value for key, value in result.items() if key not in ('jobs', 'own_kept', 'shared_tasks')}
                public.update(new=len(saved['new']), kept=result.get('own_kept', saved.get('kept', result['kept'])))
                if saved.get('note'):
                    public['note'] = saved['note']       # e.g. a mass drop that was not treated as closures
                public['found'] = max(public['found'], public['kept'])
                if started:
                    summary['attempted'] += 1
                else:
                    summary['not_attempted'].append(public['label'])
                note(public, len(saved['new']), started)
                for follower in sharing:
                    # Its board was just read by `task`: record the same outcome for this employer.
                    shared = _shared_outcome(follower, task, result, ranker.canonical)
                    try:
                        store.record_health(run_id, shared)
                    except Exception:
                        logger.exception('%s: its shared outcome could not be recorded', follower.label)
                    shared['new'] = 0
                    if started:
                        summary['attempted'] += 1
                    else:
                        summary['not_attempted'].append(shared['label'])
                    tracker.update(started=shared['label'])
                    note(shared, 0, started)
        summary['completed'] = sum(1 for source in summary['sources']
                                   if not needs_attention(source) and source['label'] not in summary['not_attempted'])
        summary['status'] = 'partial' if summary['attention'] else 'complete'
    except Exception as error:
        logger.exception('The scan failed')
        summary['error'] = f'{type(error).__name__}: {str(error)[:300]}'

    summary.update(store.run_counts(run_id))
    http = plan['http'] if plan else http
    summary['requests'] = getattr(http, 'requests', None) or sum(source['requests'] for source in summary['sources'])
    summary['minutes'] = round((time.monotonic() - began) / 60, 1)
    summary['finished_at'] = now_iso()
    store.finish_run(run_id, summary['status'], summary)
    # The look-back only matters to the time-windowed LinkedIn search, so it follows LinkedIn's own
    # outcome: one employer site in maintenance must not force a 30-day sweep the next morning.
    # An "empty" LinkedIn with no earlier good sweep is more likely a changed page than a country
    # with no Pega jobs, so it does not shorten the window either.
    linkedin_results = [source for source in summary['sources'] if source['kind'] == 'linkedin']
    swept = (bool(linkedin_results) and all(_sweep_complete(source) for source in linkedin_results)
             and (any(source['found'] > 0 for source in linkedin_results) or bool(store.kv_get(KV_LINKEDIN_OK))))
    if swept:
        store.kv_set(KV_LINKEDIN_OK, summary['finished_at'])
    if summary['status'] == 'complete' and mode == 'full' and (swept or not linkedin_results):
        store.kv_set(KV_LAST_COMPLETE, summary['finished_at'])   # the fallback when LinkedIn has never run
    if before is not None:
        try:
            # The before/after matrix for `radar.py report`.
            store.kv_set(KV_MATRIX, {'run_id': run_id, 'before': before,
                                     'after': _coverage_states(store, registry, targets, task_names)})
        except Exception:
            logger.exception('The coverage matrix could not be recorded')
    tracker.update(final_status=summary['status'])
    logger.info('Scan %s %s: %d new (%d Bengaluru, %d product/GCC), %d of %d sources attempted, %d requests, %g minutes%s',
                run_id, summary['status'], summary['new'], summary['new_bengaluru'], summary['new_product_gcc'],
                summary['attempted'], summary['requested'], summary['requests'], summary['minutes'],
                '; needs attention: ' + ', '.join(summary['attention']) if summary['attention'] else '')
    return summary
