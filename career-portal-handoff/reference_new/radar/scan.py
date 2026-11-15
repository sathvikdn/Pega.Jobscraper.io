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

from .model import EMPLOYER_SOURCE, KINDS, STATUSES, make_result, needs_attention, now_iso
from .net import Http
from .rank import load_registry, make_ranker

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


def _error_result(task, message):
    kind = getattr(task, 'kind', None)
    kind = kind if kind in KINDS else 'board'
    label = getattr(task, 'label', None) or getattr(task, 'name', None) or 'source'
    return make_result(EMPLOYER_SOURCE if kind == 'ats' else label, label, kind, status='error', error=message)


def _run_task(task, http, ctx):
    """Run one source. Whatever happens inside it, a well-formed result comes back."""
    if http.expired():
        return _error_result(task, 'not run: the time budget was used up before this source started')
    try:
        result = task.run(http, ctx)
    except Exception as error:   # a source bug must cost that source only
        logger.exception('%s raised', getattr(task, 'label', task))
        return _error_result(task, f'{type(error).__name__}: {str(error)[:200]}')
    if (not isinstance(result, dict) or any(key not in result for key in _RESULT_KEYS)
            or result['status'] not in STATUSES):
        return _error_result(task, 'the source returned a malformed result')
    return result


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

    def __init__(self, store, callback, run_id, started_at):
        self._store, self._callback, self._lock = store, callback, threading.Lock()
        self._state = {'run_id': run_id, 'state': 'running', 'status': 'running', 'started_at': started_at,
                       'total': 0, 'done': 0, 'running': [], 'new': 0, 'attention': [], 'updated_at': started_at}
        self.update()   # replace the previous run's finished snapshot before anything else can be polled

    def update(self, *, total=None, started=None, finished=None, new=0, attention=None, final_status=None):
        with self._lock:
            state = self._state
            if total is not None:
                state['total'] = total
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
            snapshot = {**state, 'running': list(state['running']), 'attention': list(state['attention'])}
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

def run_scan(config, store, *, http=None, tasks=None, progress=None, minutes=None) -> dict:
    """Run one scan and return its summary. A run that breaks part-way is recorded and returned as 'failed'.

    Callers that must not overlap with another scan wrap this in `scan_lock(data_dir)`.
    """
    with _log_file(store.path.parent / 'logs'):
        return _scan(config, store, http, tasks, progress, minutes)


def _scan(config, store, http, tasks, progress, minutes):
    began = time.monotonic()
    run_id = store.start_run()
    started_at = now_iso()
    summary = {'run_id': run_id, 'started_at': started_at, 'finished_at': None, 'minutes': 0.0, 'status': 'failed',
               'new': 0, 'new_bengaluru': 0, 'new_product_gcc': 0, 'requests': 0, 'sources': [], 'attention': []}
    tracker = _Progress(store, progress, run_id, started_at)
    try:
        scan_config = config.get('scan') if isinstance(config.get('scan'), dict) else {}
        budget = _positive(minutes, _positive(scan_config.get('minutes'), DEFAULT_MINUTES))
        workers = int(_positive(scan_config.get('workers'), DEFAULT_WORKERS))
        registry = load_registry(config.get('companies_path') or PROJECT_DIR / 'companies.json')
        ranker = make_ranker(config, registry)
        if http is None:
            pacing = _positive((config.get('linkedin') or {}).get('pacing_seconds'), 1.0)
            http = Http(deadline=began + budget * 60, pacing={LINKEDIN_HOST: pacing},
                        user_agent=(config.get('http') or {}).get('user_agent'))
        if tasks is None:
            from .sources import build_tasks   # imported lazily: tests inject fake tasks instead
            tasks = build_tasks(config, registry, store)
        tasks = sorted(tasks, key=lambda task: getattr(task, 'priority', 100))
        if not tasks:
            raise RuntimeError('no sources are configured, so nothing was searched')
        window = window_days(store.kv_get(KV_LINKEDIN_OK) or store.kv_get(KV_LAST_COMPLETE))
        summary['window_days'] = window
        ctx = {'window_days': window, 'store': store, 'config': config, 'log': logger}
        tracker.update(total=len(tasks))
        logger.info('Scan %s: %d sources, look-back %d days, budget %g minutes', run_id, len(tasks), window, budget)

        def work(task):
            tracker.update(started=task.label)
            return _run_task(task, http, ctx)

        with ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix='radar') as pool:
            pending = {pool.submit(work, task): task for task in tasks}
            for future in as_completed(pending):
                task, result = pending[future], future.result()
                try:
                    saved = store.save_result(run_id, result, ranker)
                except Exception as error:
                    # The source answered but its jobs could not be stored: that is lost coverage too.
                    logger.exception('%s: saving failed', task.label)
                    result = _error_result(task, f'could not be saved: {type(error).__name__}: {str(error)[:200]}')
                    try:
                        saved = store.save_result(run_id, result, ranker)
                    except Exception:
                        # Even the health row failed. This source is reported from memory; the others carry on.
                        logger.exception('%s: the failure could not be recorded either', task.label)
                        saved = {'new': [], 'updated': [], 'kept': 0}
                else:
                    _commit(task)
                public = {key: value for key, value in result.items() if key != 'jobs'}
                public.update(new=len(saved['new']), kept=saved.get('kept', result['kept']))
                public['found'] = max(public['found'], public['kept'])
                summary['sources'].append(public)
                flagged = needs_attention(result)
                if flagged:
                    summary['attention'].append(result['label'])
                logger.log(logging.WARNING if flagged else logging.INFO, '%-28s %-11s kept %3d of %4d, %d new%s',
                           str(result['label'])[:28], result['status'], public['kept'], public['found'],
                           len(saved['new']), f' ({result["error"]})' if result.get('error') else '')
                tracker.update(finished=task.label, new=len(saved['new']),
                               attention=result['label'] if flagged else None)
        summary['status'] = 'partial' if summary['attention'] else 'complete'
    except Exception as error:
        logger.exception('The scan failed')
        summary['error'] = f'{type(error).__name__}: {str(error)[:300]}'

    summary.update(store.run_counts(run_id))
    summary['requests'] = getattr(http, 'requests', None) or sum(source['requests'] for source in summary['sources'])
    summary['minutes'] = round((time.monotonic() - began) / 60, 1)
    summary['finished_at'] = now_iso()
    store.finish_run(run_id, summary['status'], summary)
    # The look-back only matters to the time-windowed LinkedIn search, so it follows LinkedIn's own
    # outcome: one employer site in maintenance must not force a 30-day sweep the next morning.
    # An "empty" LinkedIn with no earlier good sweep is more likely a changed page than a country
    # with no Pega jobs, so it does not shorten the window either.
    linkedin = [source for source in summary['sources'] if source['kind'] == 'linkedin']
    swept = (bool(linkedin) and all(_sweep_complete(source) for source in linkedin)
             and (any(source['found'] > 0 for source in linkedin) or bool(store.kv_get(KV_LINKEDIN_OK))))
    if swept:
        store.kv_set(KV_LINKEDIN_OK, summary['finished_at'])
    if summary['status'] == 'complete' and (swept or not linkedin):
        store.kv_set(KV_LAST_COMPLETE, summary['finished_at'])   # the fallback when LinkedIn has never run
    tracker.update(final_status=summary['status'])
    logger.info('Scan %s %s: %d new (%d Bengaluru, %d product/GCC), %d requests, %g minutes%s',
                run_id, summary['status'], summary['new'], summary['new_bengaluru'], summary['new_product_gcc'],
                summary['requests'], summary['minutes'],
                '; needs attention: ' + ', '.join(summary['attention']) if summary['attention'] else '')
    return summary
