"""SQLite persistence: jobs, where they were sighted, the user's own state, runs and source health.

One connection per call (WAL mode), so the scanner's threads and the web server can use
the same Store, or the same file from two processes, without sharing a connection.
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .model import CITY_ALIASES, EMPLOYER_SOURCE, cities, company_key, now_iso
from .rank import SCANNABLE_STATES

USER_STATUSES = ('new', 'interested', 'applied', 'interviewing', 'offer', 'rejected')
NEW_DAYS = 14             # a job nobody has looked at stops counting as new after this long
MAX_PAGE = 500
UNTITLED = 'Pega role (title not given)'
BACKUPS_KEPT = 5
OPEN_DAYS = 30            # a job counts as open while it was listed within this many days
MASS_DROP_MINIMUM = 3     # a complete read that drops this many postings, and over half the board, needs a second read
NOT_REACHED = 'not_reached'   # coverage outcome of a source the time budget cut off; not an attempt
MERGE_DAYS = 30           # beyond this gap a same-titled posting is a new opening, not the old one again
MAX_NOTES = 20000

_SCHEMA = '''
CREATE TABLE IF NOT EXISTS jobs(
    id TEXT PRIMARY KEY, title TEXT NOT NULL, company TEXT NOT NULL DEFAULT '', company_key TEXT NOT NULL DEFAULT '',
    employer_type TEXT NOT NULL DEFAULT 'unknown', city TEXT NOT NULL DEFAULT '', cities_json TEXT NOT NULL DEFAULT '[]',
    location TEXT NOT NULL DEFAULT '', is_bengaluru INTEGER NOT NULL DEFAULT 0,
    url TEXT NOT NULL DEFAULT '', apply_url TEXT, description TEXT NOT NULL DEFAULT '',
    experience_min REAL, experience_max REAL, salary_min_lpa REAL, salary_max_lpa REAL,
    posted_at TEXT, requisition_id TEXT, first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
    first_run_id TEXT, last_run_id TEXT, score INTEGER NOT NULL DEFAULT 0, fit_json TEXT NOT NULL DEFAULT '{}',
    pega_title INTEGER NOT NULL DEFAULT 0, pega_duty INTEGER NOT NULL DEFAULT 0,
    last_confirmed_at TEXT, possibly_closed INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS jobs_company ON jobs(company_key);
CREATE INDEX IF NOT EXISTS jobs_first_run ON jobs(first_run_id);
CREATE TABLE IF NOT EXISTS sightings(
    source TEXT NOT NULL, source_id TEXT NOT NULL, job_id TEXT NOT NULL, url TEXT NOT NULL DEFAULT '',
    label TEXT NOT NULL DEFAULT '', first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
    task TEXT, kind TEXT, missing_since TEXT, suspect_since TEXT,
    PRIMARY KEY(source, source_id));
CREATE INDEX IF NOT EXISTS sightings_job ON sightings(job_id);
CREATE TABLE IF NOT EXISTS user_state(
    job_id TEXT PRIMARY KEY, saved INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'new',
    notes TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL, hidden INTEGER NOT NULL DEFAULT 0, seen_at TEXT);
CREATE TABLE IF NOT EXISTS runs(
    id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL, summary_json TEXT);
CREATE TABLE IF NOT EXISTS source_health(
    run_id TEXT NOT NULL, source TEXT, label TEXT, kind TEXT, status TEXT, found INTEGER, kept INTEGER,
    requests INTEGER, error TEXT, elapsed_s REAL, reason TEXT NOT NULL DEFAULT '', pages_complete INTEGER,
    details_complete INTEGER, employer TEXT, task TEXT, at TEXT);
CREATE INDEX IF NOT EXISTS source_health_run ON source_health(run_id);
CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value_json TEXT NOT NULL);
'''

# Columns added after the first release, as (table, column, definition). A database created by an
# older version gets them through ALTER TABLE; the list only ever grows, so applying it is repeatable.
_ADDED_COLUMNS = (
    ('user_state', 'hidden', 'INTEGER NOT NULL DEFAULT 0'), ('user_state', 'seen_at', 'TEXT'),
    ('source_health', 'elapsed_s', 'REAL'), ('source_health', 'reason', "TEXT NOT NULL DEFAULT ''"),
    ('source_health', 'pages_complete', 'INTEGER'), ('source_health', 'details_complete', 'INTEGER'),
    ('source_health', 'employer', 'TEXT'), ('source_health', 'task', 'TEXT'), ('source_health', 'at', 'TEXT'),
    ('jobs', 'last_confirmed_at', 'TEXT'), ('jobs', 'possibly_closed', 'INTEGER NOT NULL DEFAULT 0'),
    ('sightings', 'task', 'TEXT'), ('sightings', 'kind', 'TEXT'), ('sightings', 'missing_since', 'TEXT'),
    ('sightings', 'suspect_since', 'TEXT'),
)
# Indexes on added columns are created after the columns exist.
_ADDED_INDEXES = ('CREATE INDEX IF NOT EXISTS sightings_task ON sightings(task)',
                  'CREATE INDEX IF NOT EXISTS source_health_task ON source_health(task)')
_HEALTH_COLUMNS = ('source', 'label', 'kind', 'status', 'found', 'kept', 'requests', 'error', 'elapsed_s', 'reason',
                   'pages_complete', 'details_complete', 'employer', 'task', 'at')
# Worst first: an employer with several portals is summarised by its worst latest outcome.
# None stands for a portal that was never attempted: worse than a board that was read, since nothing is known.
_SEVERITY = ('error', 'blocked', 'maintenance', 'partial', 'skipped', NOT_REACHED, None, 'ok', 'empty')

def unreached(row) -> bool:
    """True for an outcome that records a source was NOT read because the time budget ended before
    any answer came. A source that was partly read before the budget ended is `partial`, a real attempt."""
    return row['reason'] == 'budget' and row['status'] in ('error', 'skipped')


_JOB_COLUMNS = ('id', 'title', 'company', 'company_key', 'employer_type', 'city', 'cities_json', 'location',
                'is_bengaluru', 'url', 'apply_url', 'description', 'experience_min', 'experience_max',
                'salary_min_lpa', 'salary_max_lpa', 'posted_at', 'requisition_id', 'first_seen_at', 'last_seen_at',
                'first_run_id', 'last_run_id', 'score', 'fit_json', 'pega_title', 'pega_duty',
                'last_confirmed_at', 'possibly_closed')
# Filled from a later sighting only while still empty ("never clear a field with an empty value").
_FILL_IF_EMPTY = ('company', 'location', 'apply_url', 'requisition_id', 'experience_min', 'experience_max',
                  'salary_min_lpa', 'salary_max_lpa')
_LIST_SELECT = ', '.join('j.' + column for column in _JOB_COLUMNS if column != 'description')
_STATE_SELECT = ("COALESCE(u.saved, 0) AS saved, COALESCE(u.status, 'new') AS status, "
                 "COALESCE(u.notes, '') AS notes, COALESCE(u.hidden, 0) AS hidden, u.seen_at AS seen_at")
_SORTS = {'score': 'j.score DESC, j.posted_at IS NULL, j.posted_at DESC, j.first_seen_at DESC, j.id',
          'posted': 'j.posted_at IS NULL, j.posted_at DESC, j.score DESC, j.id',
          'first_seen': 'j.first_seen_at DESC, j.score DESC, j.id'}
_FROM = 'FROM jobs j LEFT JOIN user_state u ON u.job_id = j.id'
_NOT_HIDDEN = 'COALESCE(u.hidden, 0) = 0'
# "New" is an inbox, not a property of a run: a recent job the user has not looked at, acted on or
# hidden. A second scan the same morning, or a failed one, therefore cannot empty it. Takes one
# parameter, the first_seen_at cutoff.
_NEW = f"({_NOT_HIDDEN} AND COALESCE(u.status, 'new') = 'new' AND u.seen_at IS NULL AND j.first_seen_at >= ?)"
_VIEWS = {'all': f"{_NOT_HIDDEN} AND COALESCE(u.status, 'new') <> 'rejected'",
          'saved': f'COALESCE(u.saved, 0) = 1 AND {_NOT_HIDDEN}',
          'applied': f"u.status IN ('applied', 'interviewing', 'offer', 'rejected') AND {_NOT_HIDDEN}",
          'hidden': 'u.hidden = 1'}

_TITLE_NOISE = re.compile(r'\b(?:india|remote|hybrid|onsite|wfo|wfh|' + '|'.join(
    re.escape(alias) for alias in sorted(CITY_ALIASES, key=len, reverse=True)) + r')\b')
_TITLE_SYNONYMS = ((re.compile(r'\bsr\b'), 'senior'), (re.compile(r'\bjr\b'), 'junior'),
                   (re.compile(r'\bdev\b'), 'developer'), (re.compile(r'\bengg?\b'), 'engineer'))


def title_key(title) -> str:
    """Normalised title for cross-source matching: case, punctuation, city names and Sr/Jr spelling ignored."""
    text = re.sub(r'[^a-z0-9]+', ' ', str(title or '').lower())
    for pattern, word in _TITLE_SYNONYMS:
        text = pattern.sub(word, text)
    return ' '.join(_TITLE_NOISE.sub(' ', text).split())


def _empty(value) -> bool:
    return value is None or value == ''


def _clean(text) -> str:
    """Text SQLite can store: characters that cannot be encoded (lone surrogates) become '?'."""
    return str(text).encode('utf-8', 'replace').decode('utf-8')


def _new_cutoff() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=NEW_DAYS)).isoformat(timespec='seconds')


def _like(text) -> str:
    return '%' + text.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.execute('PRAGMA journal_mode=WAL')
            missing = self._missing_columns(db)
        if missing:
            self.backup()                     # an older database is about to change: keep a copy first
        with self._db() as db:
            db.executescript(_SCHEMA)
        if missing:
            self._migrate()
        with self._db() as db:
            for statement in _ADDED_INDEXES:
                db.execute(statement)

    @staticmethod
    def _missing_columns(db):
        """Added columns that existing tables lack. Empty for a new database and for a current one."""
        missing = []
        for table in dict.fromkeys(table for table, _, _ in _ADDED_COLUMNS):
            present = {row['name'] for row in db.execute(f'PRAGMA table_info({table})')}
            if present:
                missing += [(table, column, definition) for owner, column, definition in _ADDED_COLUMNS
                            if owner == table and column not in present]
        return missing

    def _migrate(self):
        """Add whatever columns this database lacks. Additive only: no row is removed or rewritten,
        except that the old `hidden` status becomes the `hidden` flag."""
        with self._db(write=True) as db:
            missing = self._missing_columns(db)   # read again under the write lock: another process may have won
            for table, column, definition in missing:
                db.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')
            if ('user_state', 'hidden') in {(table, column) for table, column, _ in missing}:
                # Hiding used to be a status, which overwrote where the job stood in the pipeline.
                db.execute("UPDATE user_state SET hidden = 1, status = 'new', seen_at = COALESCE(seen_at, updated_at) "
                           "WHERE status = 'hidden'")

    def backup(self) -> Path:
        """Copy the database to <data>/backups/radar-<UTC time>.sqlite3 and keep the newest few."""
        folder = self.path.parent / 'backups'
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        target = folder / f'radar-{stamp}.sqlite3'
        serial = 1
        while target.exists():
            serial += 1
            target = folder / f'radar-{stamp}-{serial}.sqlite3'
        source = sqlite3.connect(str(self.path), timeout=30)
        try:
            copy = sqlite3.connect(str(target))
            try:
                source.backup(copy)           # consistent even while the write-ahead log holds changes
            finally:
                copy.close()
        finally:
            source.close()
        for old in sorted(folder.glob('radar-*.sqlite3'), key=lambda item: item.name, reverse=True)[BACKUPS_KEPT:]:
            try:
                old.unlink()
            except OSError:
                pass
        return target

    @contextmanager
    def _db(self, write=False):
        """A short-lived connection. `write=True` takes the write lock up front so a
        read-then-update sequence cannot interleave with another writer."""
        db = sqlite3.connect(str(self.path), timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            if write:
                db.execute('BEGIN IMMEDIATE')
            yield db
            if write:
                db.execute('COMMIT')
        except BaseException:
            if db.in_transaction:
                db.execute('ROLLBACK')
            raise
        finally:
            db.close()

    # ── runs ──

    def start_run(self) -> str:
        started = now_iso()
        run_id = 'run-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(3)
        with self._db(write=True) as db:
            db.execute('INSERT INTO runs(id, started_at, status) VALUES (?,?,?)', (run_id, started, 'running'))
        return run_id

    def finish_run(self, run_id, status, summary: dict):
        with self._db(write=True) as db:
            db.execute('UPDATE runs SET finished_at=?, status=?, summary_json=? WHERE id=?',
                       (now_iso(), status, json.dumps(summary, ensure_ascii=False, default=str), run_id))

    def latest_run(self) -> dict | None:
        """The latest run that produced coverage (complete or partial) with its per-source health rows.

        `last_attempt` describes the most recent finished run of any status, so a failed scan can be
        reported without losing the last good coverage table. When only failed runs exist the run
        fields are None and `health` is empty. Returns None when no run has ever finished.
        """
        with self._db() as db:
            attempt = db.execute('SELECT * FROM runs WHERE finished_at IS NOT NULL '
                                 'ORDER BY finished_at DESC, rowid DESC LIMIT 1').fetchone()
            if attempt is None:
                return None
            row = db.execute("SELECT * FROM runs WHERE finished_at IS NOT NULL AND status IN ('complete', 'partial') "
                             'ORDER BY finished_at DESC, rowid DESC LIMIT 1').fetchone()
            health = [self._health(item) for item in db.execute(
                f'SELECT {", ".join(_HEALTH_COLUMNS)} FROM source_health WHERE run_id=? ORDER BY rowid',
                (row['id'],))] if row else []
        return {'id': row['id'] if row else None, 'started_at': row['started_at'] if row else None,
                'finished_at': row['finished_at'] if row else None, 'status': row['status'] if row else None,
                'summary': json.loads(row['summary_json'] or '{}') if row else {}, 'health': health,
                'last_attempt': {'id': attempt['id'], 'status': attempt['status'], 'finished_at': attempt['finished_at'],
                                 'error': json.loads(attempt['summary_json'] or '{}').get('error')}}

    def latest_coverage_run(self) -> dict | None:
        """The state of every source as of now: the last full run, with each source's outcome replaced
        by its newest one from any later retry or `only` run.

        `latest_run()` describes the most recent run by itself, which after a narrow retry is a handful
        of sources; this is the one for a "Sources" table. Same shape as `latest_run()`, each health row
        also carrying `run_id`, plus `later_runs` (ids of the runs merged in). A source the budget cut
        off in a later run keeps its earlier real outcome. Falls back to the newest good run when no
        full run exists; None when no run has ever finished.
        """
        base = self.latest_run()
        if base is None or base['id'] is None:
            return base
        with self._db() as db:
            good = db.execute("SELECT id, summary_json FROM runs WHERE finished_at IS NOT NULL "
                              "AND status IN ('complete', 'partial') ORDER BY finished_at, rowid").fetchall()
            full = [row['id'] for row in good if json.loads(row['summary_json'] or '{}').get('mode', 'full') == 'full']
            ids = [row['id'] for row in good]
            chain = ids[ids.index(full[-1]):] if full else ids[-1:]
            merged = {}
            for run_id in chain:
                for row in db.execute(f'SELECT run_id, {", ".join(_HEALTH_COLUMNS)} FROM source_health '
                                      'WHERE run_id=? ORDER BY rowid', (run_id,)):
                    key = row['task'] or (row['kind'], row['label'])
                    if unreached(row) and key in merged:
                        continue
                    merged[key] = self._health(row)
            first = db.execute('SELECT * FROM runs WHERE id=?', (chain[0],)).fetchone()
        return {**base, 'id': first['id'], 'started_at': first['started_at'], 'finished_at': first['finished_at'],
                'status': first['status'], 'summary': json.loads(first['summary_json'] or '{}'),
                'health': list(merged.values()), 'later_runs': chain[1:]}

    @staticmethod
    def _health(row) -> dict:
        item = dict(row)
        for flag in ('pages_complete', 'details_complete'):
            item[flag] = None if item[flag] is None else bool(item[flag])
        return item

    def task_history(self) -> dict:
        """{task name: its latest health row plus `run_id`, `run_started_at` and three run numbers}.

        Runs are numbered in the order they were started (`run_seq`), which is exact where a
        timestamp to the second is not: two runs in the same second still have an order.
        `run_seq` is the run of the latest row. `attempted_run_seq` is the run of the latest row
        in which the source was actually read (see `unreached`), and `attempted_full_run_seq` the
        same counting full scans only; each is None when there is no such row. Fair ordering uses
        the last one: a narrow `only` or retry run must not send a source to the back of the next
        full scan.
        """
        with self._db() as db:
            rows = db.execute(
                f'SELECT {", ".join("h." + column for column in _HEALTH_COLUMNS)}, h.run_id, r.rowid AS run_seq, '
                'r.started_at AS run_started_at, r.summary_json FROM source_health h JOIN runs r ON r.id = h.run_id '
                'WHERE h.task IS NOT NULL ORDER BY h.rowid').fetchall()
        history, attempted, attempted_full, modes = {}, {}, {}, {}
        for row in rows:
            item = self._health(row)
            summary = item.pop('summary_json')
            history[row['task']] = item
            if unreached(row):
                continue
            attempted[row['task']] = row['run_seq']
            if row['run_id'] not in modes:
                # A run that never finished has no summary; its mode is unknown, so it is not counted as full.
                modes[row['run_id']] = json.loads(summary).get('mode', 'full') if summary else None
            if modes[row['run_id']] == 'full':
                attempted_full[row['task']] = row['run_seq']
        for task, item in history.items():
            item['attempted_run_seq'] = attempted.get(task)
            item['attempted_full_run_seq'] = attempted_full.get(task)
        return history

    def latest_full_run_seq(self):
        """The run number (see `task_history`) of the most recent full scan that finished as complete
        or partial, or None."""
        with self._db() as db:
            for row in db.execute("SELECT rowid AS seq, summary_json FROM runs WHERE finished_at IS NOT NULL "
                                  "AND status IN ('complete', 'partial') ORDER BY rowid DESC"):
                if json.loads(row['summary_json'] or '{}').get('mode', 'full') == 'full':
                    return row['seq']
        return None

    def run_counts(self, run_id) -> dict:
        """How many jobs a run saw for the first time, in total and in the two focus groups."""
        with self._db() as db:
            row = db.execute(
                'SELECT COUNT(*) AS new, COALESCE(SUM(is_bengaluru), 0) AS new_bengaluru, '
                "COALESCE(SUM(employer_type IN ('product', 'gcc')), 0) AS new_product_gcc "
                'FROM jobs WHERE first_run_id=?', (run_id,)).fetchone()
        return dict(row)

    # ── saving ──

    def save_result(self, run_id, result, ranker) -> dict:
        """Upsert every job of one source result and record the source's health for the run.

        Returns {'new': [job ids], 'updated': [job ids], 'kept': n}. `kept` is how many of the
        result's jobs were actually stored, and is what the health row records. A `note` key is
        added when a suspicious mass drop was not treated as closures; the health row says so too.

        A result that read its whole board (status ok or empty with `pages_complete`) also confirms
        the jobs it lists and notes which of its earlier postings are gone; see `_note_absences`.
        """
        now = now_iso()
        new, updated, kept, listed = [], [], 0, set()
        authoritative = result.get('status') in ('ok', 'empty') and result.get('pages_complete') is True
        with self._db(write=True) as db:
            for job in result.get('jobs') or ():
                if not isinstance(job, dict):
                    continue                      # nothing to store; `kept` will show the shortfall
                job = self._complete(job)
                job_id, created = self._upsert(db, run_id, result, job, ranker, now, authoritative)
                listed.add((job.get('source') or result.get('source') or '', job['source_id']))
                kept += 1
                if created:
                    new.append(job_id)
                elif job_id not in new and job_id not in updated:
                    updated.append(job_id)
            note = self._note_absences(db, result, listed, now) if authoritative else None
            # On a board shared by several employers the caller says how many of the stored jobs
            # are this employer's own (`own_kept`); the others are credited to their employers' rows.
            recorded = {**result, 'found': max(result.get('found') or 0, kept), 'kept': result.get('own_kept', kept)}
            if note:
                recorded['error'] = '; '.join(filter(None, [result.get('error'), note]))
            self._write_health(db, run_id, recorded, now)
        return {'new': new, 'updated': updated, 'kept': kept, **({'note': note} if note else {})}

    def record_health(self, run_id, result):
        """Record a source outcome without touching any job, e.g. for an employer whose shared board
        was fetched by another task."""
        with self._db(write=True) as db:
            self._write_health(db, run_id, result, now_iso())

    @staticmethod
    def _write_health(db, run_id, result, now):
        values = {column: result.get(column) for column in _HEALTH_COLUMNS}
        values.update(reason=result.get('reason') or '', at=now, found=result.get('found') or 0,
                      kept=result.get('kept') or 0, requests=result.get('requests') or 0)
        for flag in ('pages_complete', 'details_complete'):
            values[flag] = None if values[flag] is None else int(bool(values[flag]))
        db.execute(f'INSERT INTO source_health(run_id, {", ".join(_HEALTH_COLUMNS)}) '
                   f'VALUES (?, {", ".join("?" * len(_HEALTH_COLUMNS))})',
                   [run_id, *(values[column] for column in _HEALTH_COLUMNS)])

    def _note_absences(self, db, result, listed, now):
        """After a complete read of a board, mark its earlier postings that are no longer listed.

        A job becomes "possibly closed" only when every board that can prove absence has dropped it
        and nothing has listed it since. LinkedIn is a time-windowed search, so a posting missing
        from it proves nothing; partial, blocked and failed runs never get here. Nothing is deleted.
        """
        task = result.get('task')
        if not task or result.get('kind') == 'linkedin':
            return None
        # On a shared board the sightings are filed under each employer's own task; together they
        # are the board's listing.
        tasks = sorted({task, *(name for name, _ in (result.get('shared_tasks') or {}).values())})
        current = db.execute('SELECT source, source_id, job_id, suspect_since FROM sightings '
                             f"WHERE missing_since IS NULL AND task IN ({', '.join('?' * len(tasks))})", tasks).fetchall()
        gone = [row for row in current if (row['source'], row['source_id']) not in listed]
        notes = []
        if len(gone) >= MASS_DROP_MINIMUM and len(gone) * 2 > len(current):
            # Most of a board vanishing in one read is far more often a changed site or a narrowed
            # search than that many roles closing together. Those postings are only remembered as
            # suspects; if the next complete read still lacks them, the closure is believed.
            fresh = [row for row in gone if row['suspect_since'] is None]
            gone = [row for row in gone if row['suspect_since'] is not None]
            for row in fresh:
                db.execute('UPDATE sightings SET suspect_since=? WHERE source=? AND source_id=?',
                           (now, row['source'], row['source_id']))
            if fresh:
                notes.append(f'listing dropped {len(fresh)} of {len(current)} jobs at once; not treated as closures')
            if gone:
                notes.append(f'{len(gone)} closures confirmed on a second complete read')
        for row in gone:
            db.execute('UPDATE sightings SET missing_since=?, suspect_since=NULL WHERE source=? AND source_id=?',
                       (now, row['source'], row['source_id']))
        for job_id in {row['job_id'] for row in gone}:
            sightings = db.execute('SELECT task, kind, missing_since, last_seen_at FROM sightings WHERE job_id=?',
                                   (job_id,)).fetchall()
            provable = [item for item in sightings if item['task'] and item['kind'] != 'linkedin']
            if any(item['missing_since'] is None for item in provable):
                continue                          # another board still lists it
            dropped = max(item['missing_since'] for item in provable)
            if not any(item['last_seen_at'] > dropped for item in sightings):
                db.execute('UPDATE jobs SET possibly_closed=1 WHERE id=?', (job_id,))
        return '; '.join(notes) or None

    @staticmethod
    def _complete(job):
        """A posting is never dropped for a missing title or id: it gets a placeholder title and a stable id."""
        title = str(job.get('title') or '').strip() or UNTITLED
        source_id = job.get('source_id')
        if _empty(source_id):
            basis = '|'.join(str(job.get(field) or '') for field in ('url', 'title', 'company', 'location'))
            source_id = 'auto-' + hashlib.sha1(basis.encode('utf-8', 'replace')).hexdigest()[:16]
        return {**job, 'title': title, 'source_id': str(source_id)}

    def _find(self, db, source, source_id, key, requisition, job, city, now):
        """Identity rules, first match wins. Returns an existing job id or None."""
        row = db.execute('SELECT job_id FROM sightings WHERE source=? AND source_id=?', (source, source_id)).fetchone()
        if row:
            return row['job_id']
        if not key:
            return None   # without an employer there is nothing safe to merge on
        if requisition:
            row = db.execute('SELECT id FROM jobs WHERE company_key=? AND requisition_id=?', (key, requisition)).fetchone()
            if row:
                return row['id']
        wanted = title_key(job['title'])
        stale = (datetime.fromisoformat(now) - timedelta(days=MERGE_DAYS)).isoformat(timespec='seconds')
        posted = job.get('posted_at')
        for row in db.execute(
                'SELECT id, title, requisition_id, last_seen_at, posted_at FROM jobs '
                'WHERE company_key=? AND city=? ORDER BY first_seen_at DESC, id', (key, city)):
            if title_key(row['title']) != wanted:
                continue
            if requisition and row['requisition_id'] and row['requisition_id'] != requisition:
                continue   # two requisitions with the same title are two openings
            # An employer re-opens the same role months later. That is a new opening: it must not vanish
            # into a job last seen long ago or posted long before. Whether the user hid or rejected the
            # old job plays no part: the same posting on a second site must not bring it back as new.
            if row['last_seen_at'] < stale:
                continue
            if posted and row['posted_at'] and (date.fromisoformat(posted) - date.fromisoformat(row['posted_at'])).days > MERGE_DAYS:
                continue
            # This rule merges the same opening seen on different sites. A second listing on a
            # site that already lists the job is a separate posting there, so it stays separate.
            if db.execute('SELECT 1 FROM sightings WHERE job_id=? AND source=?', (row['id'], source)).fetchone():
                continue
            return row['id']
        return None

    def _upsert(self, db, run_id, result, job, ranker, now, authoritative=False):
        source = job.get('source') or result.get('source') or ''
        source_id = str(job['source_id'])
        key = getattr(ranker, 'canonical', company_key)(job.get('company'))
        found_cities = cities(job.get('location'))
        requisition = job.get('requisition_id') or None
        from_employer = source == EMPLOYER_SOURCE or result.get('kind') == 'ats'
        job_id = self._find(db, source, source_id, key, requisition, job, found_cities[0] if found_cities else '', now)
        created = job_id is None
        if created:
            row = {column: None for column in _JOB_COLUMNS}
            row.update(id=secrets.token_hex(8), title=job['title'], company=job.get('company') or '', company_key=key,
                       location=job.get('location') or '', url=job.get('url') or '',
                       description=job.get('description') or '', posted_at=job.get('posted_at') or None,
                       first_seen_at=now, first_run_id=run_id)
            for column in _FILL_IF_EMPTY:
                row[column] = None if _empty(job.get(column)) else job[column]
            merged_cities = found_cities
        else:
            row = dict(db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone())
            for column in _FILL_IF_EMPTY:
                if _empty(row[column]) and not _empty(job.get(column)):
                    row[column] = job[column]
            if not row['company_key']:
                row['company_key'] = key
            if len(job.get('description') or '') > len(row['description'] or ''):
                row['description'] = job['description']
            if job.get('posted_at') and (not row['posted_at'] or job['posted_at'] < row['posted_at']):
                row['posted_at'] = job['posted_at']
            if job.get('url'):
                has_employer_url = db.execute('SELECT 1 FROM sightings WHERE job_id=? AND source=?',
                                              (job_id, EMPLOYER_SOURCE)).fetchone()
                if not row['url'] or (from_employer and not has_employer_url):
                    row['url'] = job['url']
            merged_cities = json.loads(row['cities_json'] or '[]')
            merged_cities += [city for city in found_cities if city not in merged_cities]
        row.update(city=merged_cities[0] if merged_cities else '', cities_json=json.dumps(merged_cities),
                   is_bengaluru=int('Bengaluru' in merged_cities), last_seen_at=now, last_run_id=run_id,
                   possibly_closed=0)                 # listed again, so not closed
        if authoritative:
            row['last_confirmed_at'] = now
        self._apply_rank(row, ranker)
        db.execute(f'INSERT OR REPLACE INTO jobs({", ".join(_JOB_COLUMNS)}) VALUES ({", ".join("?" * len(_JOB_COLUMNS))})',
                   [row[column] for column in _JOB_COLUMNS])
        # A posting on a board several employers share is filed under the employer it belongs to.
        task, label = (result.get('shared_tasks') or {}).get(key) or (result.get('task'), result.get('label'))
        db.execute('INSERT INTO sightings(source, source_id, job_id, url, label, first_seen_at, last_seen_at, task, kind) '
                   'VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(source, source_id) DO UPDATE SET '
                   'job_id=excluded.job_id, url=excluded.url, label=excluded.label, last_seen_at=excluded.last_seen_at, '
                   'task=COALESCE(excluded.task, task), kind=COALESCE(excluded.kind, kind), missing_since=NULL, '
                   'suspect_since=NULL',
                   (source, source_id, row['id'], job.get('url') or '', label or '', now, now, task, result.get('kind')))
        return row['id'], created

    @staticmethod
    def _apply_rank(row, ranker):
        """Run the ranker on a job row (given a parsed `cities` list) and fold its verdict into the row."""
        verdict = ranker({**row, 'cities': json.loads(row['cities_json'] or '[]')})
        row.update(employer_type=verdict.get('employer_type') or 'unknown', score=int(round(verdict.get('score') or 0)),
                   fit_json=json.dumps(verdict.get('fit') or {}, ensure_ascii=False),
                   pega_title=int(bool(verdict.get('pega_title'))), pega_duty=int(bool(verdict.get('pega_duty'))))

    def rescore(self, ranker) -> int:
        """Re-run the ranker over every job, e.g. after config.json or companies.json changed.

        Company keys are refreshed too, so an employer added to the registry is matched from then on.
        """
        canonical = getattr(ranker, 'canonical', company_key)
        with self._db(write=True) as db:
            rows = [dict(row) for row in db.execute('SELECT * FROM jobs')]
            for row in rows:
                self._apply_rank(row, ranker)
                db.execute('UPDATE jobs SET company_key=?, employer_type=?, score=?, fit_json=?, pega_title=?, pega_duty=? '
                           'WHERE id=?', (canonical(row['company']), row['employer_type'], row['score'], row['fit_json'],
                                          row['pega_title'], row['pega_duty'], row['id']))
        return len(rows)

    # ── reading ──

    @staticmethod
    def _public(row, sources):
        """A database row as the dict handed to the server: JSON columns parsed, flags as booleans."""
        item = dict(row)
        item['cities'] = json.loads(item.pop('cities_json') or '[]')
        item['fit'] = json.loads(item.pop('fit_json') or '{}')
        for flag in ('is_bengaluru', 'pega_title', 'pega_duty', 'saved', 'hidden', 'is_new', 'has_description',
                     'possibly_closed'):
            item[flag] = bool(item[flag])
        item['seen'] = item['seen_at'] is not None
        item['sources'] = sources
        return item

    def jobs(self, *, view='all', city='all', types=None, q='', min_score=0, sort='score',
             limit=100, offset=0) -> tuple[list[dict], int]:
        """One page of jobs (without descriptions) and the total number that match the filters."""
        cutoff = _new_cutoff()
        where, params = [], []
        if view == 'new':
            where.append(_NEW)
            params.append(cutoff)
        else:
            where.append(_VIEWS.get(view, _VIEWS['all']))
        wanted_city = str(city or 'all').strip()
        if wanted_city.lower() != 'all':
            canonical = CITY_ALIASES.get(wanted_city.lower(), wanted_city)
            if canonical == 'Bengaluru':
                where.append('j.is_bengaluru = 1')
            else:
                where.append("j.cities_json LIKE ? ESCAPE '\\'")
                params.append(_like(json.dumps(_clean(canonical))))
        wanted_types = [_clean(kind) for kind in (types or ()) if kind]
        if wanted_types:
            where.append(f"j.employer_type IN ({', '.join('?' * len(wanted_types))})")
            params.extend(wanted_types)
        for word in _clean(q or '').split():
            where.append('(' + ' OR '.join(f"j.{column} LIKE ? ESCAPE '\\'"
                                           for column in ('title', 'company', 'location', 'description')) + ')')
            params.extend([_like(word)] * 4)
        if min_score:
            where.append('j.score >= ?')
            params.append(int(min_score))
        base = f'{_FROM} WHERE ' + ' AND '.join(where)
        with self._db() as db:
            total = db.execute('SELECT COUNT(*) ' + base, params).fetchone()[0]
            rows = db.execute(
                f"SELECT {_LIST_SELECT}, j.description <> '' AS has_description, {_STATE_SELECT}, {_NEW} AS is_new "
                f'{base} ORDER BY {_SORTS.get(sort, _SORTS["score"])} LIMIT ? OFFSET ?',
                [cutoff, *params, max(1, min(MAX_PAGE, int(limit))), max(0, int(offset))]).fetchall()
            sources = self._sources(db, [row['id'] for row in rows])
        return [self._public(row, sources.get(row['id'], [])) for row in rows], total

    @staticmethod
    def _sources(db, job_ids=None):
        """{job id: [distinct sighting sources, earliest first]} for the given jobs, or for all of them."""
        sql, params = 'SELECT job_id, source FROM sightings', []
        if job_ids is not None:
            if not job_ids:
                return {}
            sql += f" WHERE job_id IN ({', '.join('?' * len(job_ids))})"
            params = list(job_ids)
        found = {}
        for row in db.execute(sql + ' ORDER BY first_seen_at, rowid', params):
            names = found.setdefault(row['job_id'], [])
            if row['source'] not in names:
                names.append(row['source'])
        return found

    def job(self, job_id) -> dict | None:
        """The full job: every column, parsed fit, user state, sources and the list of sightings."""
        with self._db() as db:
            row = db.execute(f"SELECT j.*, j.description <> '' AS has_description, {_STATE_SELECT}, {_NEW} AS is_new "
                             f'{_FROM} WHERE j.id=?', (_new_cutoff(), job_id)).fetchone()
            if row is None:
                return None
            sightings = [dict(item) for item in db.execute(
                'SELECT source, source_id, url, label, first_seen_at, last_seen_at FROM sightings '
                'WHERE job_id=? ORDER BY first_seen_at, rowid', (job_id,))]
        item = self._public(row, list(dict.fromkeys(sighting['source'] for sighting in sightings)))
        item['sightings'] = sightings
        return item

    def set_state(self, job_id, *, saved=None, status=None, notes=None, hidden=None, seen=None) -> dict | None:
        """Update the user's state for a job; arguments left as None are unchanged.

        Saving a job or moving it off status 'new' also marks it seen. `seen=True` marks it seen
        (keeping an earlier time), `seen=False` makes it unseen again and wins over those two rules.
        Returns the new state, or None for an unknown job. Raises ValueError for an unknown status.
        """
        if status is not None and status not in USER_STATUSES:
            raise ValueError(f'unknown status {status!r}')
        with self._db(write=True) as db:
            if db.execute('SELECT 1 FROM jobs WHERE id=?', (job_id,)).fetchone() is None:
                return None
            current = db.execute('SELECT * FROM user_state WHERE job_id=?', (job_id,)).fetchone()
            now = now_iso()
            state = {'job_id': job_id, 'saved': bool(current['saved']) if current else False,
                     'status': current['status'] if current else 'new', 'notes': current['notes'] if current else '',
                     'hidden': bool(current['hidden']) if current else False,
                     'seen_at': current['seen_at'] if current else None, 'updated_at': now}
            if saved is not None:
                state['saved'] = bool(saved)
            if status is not None:
                state['status'] = status
            if notes is not None:
                state['notes'] = _clean(notes)[:MAX_NOTES]
            if hidden is not None:
                state['hidden'] = bool(hidden)
            if seen is False:
                state['seen_at'] = None
            elif seen or saved or (status is not None and status != 'new'):
                state['seen_at'] = state['seen_at'] or now
            db.execute('INSERT OR REPLACE INTO user_state(job_id, saved, status, notes, hidden, seen_at, updated_at) '
                       'VALUES (?,?,?,?,?,?,?)', (job_id, int(state['saved']), state['status'], state['notes'],
                                                  int(state['hidden']), state['seen_at'], now))
        state['seen'] = state['seen_at'] is not None
        return state

    def mark_all_seen(self) -> int:
        """Empty the "new" inbox: stamp every job that currently counts as new. Returns how many."""
        now = now_iso()
        with self._db(write=True) as db:
            return db.execute(
                'INSERT INTO user_state(job_id, saved, status, notes, hidden, seen_at, updated_at) '
                f"SELECT j.id, 0, 'new', '', 0, ?, ? {_FROM} WHERE {_NEW} "
                'ON CONFLICT(job_id) DO UPDATE SET seen_at = excluded.seen_at, updated_at = excluded.updated_at',
                (now, now, _new_cutoff())).rowcount

    def stats(self) -> dict:
        """Totals for the header tiles, each counted exactly as the matching view or `is_new` counts it."""
        cutoff = _new_cutoff()
        focus = "j.employer_type IN ('product', 'gcc')"
        with self._db() as db:
            totals = dict(db.execute(
                f'SELECT COALESCE(SUM({_VIEWS["all"]}), 0) AS total, COALESCE(SUM({_NEW}), 0) AS new, '
                f'COALESCE(SUM({_NEW} AND j.is_bengaluru), 0) AS new_bengaluru, '
                f'COALESCE(SUM({_NEW} AND {focus}), 0) AS new_product_gcc, '
                f'COALESCE(SUM({_VIEWS["all"]} AND j.is_bengaluru), 0) AS bengaluru, '
                f'COALESCE(SUM({_VIEWS["all"]} AND {focus}), 0) AS product_gcc, '
                f'COALESCE(SUM({_VIEWS["all"]} AND j.is_bengaluru AND {focus}), 0) AS bengaluru_product_gcc, '
                f'COALESCE(SUM({_VIEWS["saved"]}), 0) AS saved, COALESCE(SUM({_VIEWS["applied"]}), 0) AS applied, '
                f'COALESCE(SUM({_VIEWS["hidden"]}), 0) AS hidden {_FROM}', [cutoff] * 3).fetchone())
            totals['by_type'] = {item['employer_type']: item['n'] for item in db.execute(
                f'SELECT j.employer_type, COUNT(*) AS n {_FROM} WHERE {_VIEWS["all"]} GROUP BY j.employer_type')}
            latest = db.execute("SELECT finished_at, status FROM runs WHERE finished_at IS NOT NULL "
                                "AND status IN ('complete', 'partial') ORDER BY finished_at DESC, rowid DESC LIMIT 1").fetchone()
            totals['last_scan_at'] = latest['finished_at'] if latest else None
            totals['last_scan_status'] = latest['status'] if latest else None
        return totals

    def known_ids(self, source, *, with_description=True) -> set[str]:
        """Source ids already sighted for `source`; by default only those whose job has a description."""
        sql = 'SELECT s.source_id FROM sightings s JOIN jobs j ON j.id = s.job_id WHERE s.source=?'
        if with_description:
            sql += " AND j.description <> ''"
        with self._db() as db:
            return {row[0] for row in db.execute(sql, (source,))}

    def export_rows(self) -> list[dict]:
        """Every job (hidden ones included) with the user's state, flat, best fit first."""
        with self._db() as db:
            rows = db.execute(
                'SELECT j.id, j.score, j.title, j.company, j.employer_type, j.city, j.location, j.posted_at, '
                'j.experience_min, j.experience_max, j.salary_min_lpa, j.salary_max_lpa, j.url, j.apply_url, '
                f'j.requisition_id, j.first_seen_at, j.last_seen_at, j.last_confirmed_at, j.possibly_closed, {_STATE_SELECT} '
                'FROM jobs j LEFT JOIN user_state u ON u.job_id = j.id ORDER BY ' + _SORTS['score']).fetchall()
            sources = self._sources(db)
        exported = []
        for row in rows:
            item = dict(row)
            item['saved'], item['hidden'] = bool(item['saved']), bool(item['hidden'])
            item['possibly_closed'] = bool(item['possibly_closed'])
            item['sources'] = ', '.join(sources.get(item['id'], []))
            exported.append(item)
        return exported

    # ── coverage ──

    def coverage(self, registry, targets, tasks=None) -> list[dict]:
        """One row per registry employer and one per unresolved original target. Reads only.

        Three things are kept apart: who the employer is, which portals are configured, and what
        the latest attempt of those portals produced.

        `tasks` maps an employer name to the task names of its portals as configured today (see
        `scan.portal_tasks`, which is used when it is omitted). Only those tasks' outcomes count:
        health left behind by a portal that was since edited or removed is ignored, so a corrected
        board starts again as never attempted.

        `latest_status` is the worst outcome among the employer's current portals: a source status,
        'not_reached' when the time budget cut it off (that is not an attempt), or None when a
        portal has never been attempted or nothing is scannable. It is never a made-up `empty`.

        Job counts: `jobs_total` is every job ever attributed to the employer; `jobs_on_file` leaves
        out those the user hid or rejected; `jobs_open` are the on-file jobs not flagged possibly
        closed and listed by some source within the last 30 days.
        """
        if tasks is None:
            from .scan import portal_tasks   # imported here: scan builds on the store, not the reverse
            tasks = portal_tasks(registry)
        current = {}
        for employer, names in (tasks or {}).items():
            current.setdefault(registry.canonical_key(employer), []).extend(names)
        originals, unresolved = {}, []
        for target in targets or ():
            entry = registry.find(target['employer']) if target.get('employer') else None
            if entry is None or target.get('resolution') == 'unresolved':
                unresolved.append(target)
            else:
                originals.setdefault(entry['name'], []).append(target)
        recent = (datetime.now(timezone.utc) - timedelta(days=OPEN_DAYS)).isoformat(timespec='seconds')
        with self._db() as db:
            latest, attempted, succeeded = {}, {}, {}
            for row in db.execute(f'SELECT run_id, {", ".join(_HEALTH_COLUMNS)} FROM source_health '
                                  'WHERE task IS NOT NULL ORDER BY rowid'):
                latest[row['task']] = row
                if not unreached(row):                   # a source the budget cut off was not attempted
                    attempted[row['task']] = row
                    if row['status'] in ('ok', 'empty'):
                        succeeded[row['task']] = row['at']
            jobs = {row['company_key']: row for row in db.execute(
                'SELECT j.company_key, COUNT(*) AS total, '
                f"COALESCE(SUM({_VIEWS['all']}), 0) AS on_file, "
                f"COALESCE(SUM({_VIEWS['all']} AND j.possibly_closed = 0 AND j.last_seen_at >= ?), 0) AS open "
                f'{_FROM} GROUP BY j.company_key', (recent,))}
        rows = []
        for employer in sorted(registry.employers, key=lambda item: item['name'].lower()):
            key = registry.canonical_key(employer['name'])
            states = [portal['state'] for portal in employer['portals']]
            if any(state in SCANNABLE_STATES for state in states):
                inventory = 'configured'
            elif not states:
                inventory = 'not configured'
            else:
                inventory = 'unsupported' if 'unsupported' in states else 'wrong scope only'
            sources = []
            for name in dict.fromkeys(current.get(key, ())) if inventory == 'configured' else ():
                row, real = latest.get(name), attempted.get(name)
                status = None if row is None else NOT_REACHED if unreached(row) else row['status']
                sources.append({'task': name, 'status': status, 'reason': (row['reason'] or None) if row else None,
                                'error': row['error'] if row else None, 'at': real['at'] if real else None,
                                'run_id': real['run_id'] if real else None,
                                'pages_complete': None if real is None or real['pages_complete'] is None
                                else bool(real['pages_complete']),
                                'details_complete': None if real is None or real['details_complete'] is None
                                else bool(real['details_complete']),
                                'last_success_at': succeeded.get(name)})
            if inventory == 'configured' and not sources:
                # Scannable on paper, but no task exists for it (for example a kind without an adapter).
                sources.append({'task': None, 'status': None, 'reason': None, 'error': None, 'at': None, 'run_id': None,
                                'pages_complete': None, 'details_complete': None, 'last_success_at': None})
            worst = min(sources, key=lambda item: _SEVERITY.index(item['status'])
                        if item['status'] in _SEVERITY else 0, default=None)
            newest = max((item for item in sources if item['at']), key=lambda item: item['at'], default=None)
            matched = originals.get(employer['name'], [])
            counts = jobs.get(key)
            row = {
                'canonical': employer['name'],
                'original_names': list(dict.fromkeys(target['original_name'] for target in matched)),
                'original_rows': [target['row'] for target in matched],
                'type': employer['type'], 'bengaluru': employer['bengaluru'], 'parent': employer['parent'],
                'career_url': employer['career_url'],
                'portals': [{name: portal.get(name) for name in ('kind', 'state', 'scope', 'note', 'business_unit')}
                            for portal in employer['portals']],
                'linkedin_query': employer['linkedin_query'],
                'inventory_state': inventory, 'inventory_note': employer['inventory_note'],
                'unverified': any(state == 'candidate' for state in states),
                'last_attempt_at': newest['at'] if newest else None,
                'last_success_at': max(filter(None, (item['last_success_at'] for item in sources)), default=None),
                'latest_status': worst['status'] if worst else None,
                'latest_reason': worst['reason'] if worst else None,
                'latest_error': worst['error'] if worst else None,
                'run_id': newest['run_id'] if newest else None,
                'pages_complete': self._complete_flag(sources, 'pages_complete'),
                'details_complete': self._complete_flag(sources, 'details_complete'),
                'jobs_total': counts['total'] if counts else 0,
                'jobs_on_file': counts['on_file'] if counts else 0,
                'jobs_open': counts['open'] if counts else 0,
                'sources': [{name: item[name] for name in ('task', 'status', 'reason', 'at', 'run_id')} for item in sources],
            }
            row['next_action'] = _next_action(row)
            rows.append(row)
        for target in unresolved:
            row = dict.fromkeys(COVERAGE_COLUMNS)
            row.update(canonical=None, original_names=[target['original_name']], original_rows=[target['row']],
                       career_url=target.get('original_url'), portals=[], linkedin_query=False, unverified=False,
                       inventory_state='identity unresolved',
                       inventory_note=target.get('note') or (f"named employer {target['employer']!r} is not in companies.json"
                                                             if target.get('employer') else None),
                       jobs_total=0, jobs_on_file=0, jobs_open=0, sources=[])
            row['next_action'] = _next_action(row)
            rows.append(row)
        return rows

    @staticmethod
    def _complete_flag(sources, name):
        """True when every current portal was attempted and reported the flag true; False when any
        reported false; None when a portal was never attempted or none said."""
        flags = [item[name] for item in sources]
        if any(flag is False for flag in flags):
            return False
        return True if flags and all(flag is True for flag in flags) else None

    def coverage_summary(self, rows) -> dict:
        """Counts for the coverage tiles, computed from the rows of `coverage()`.

        Outcome counts are over employers with a scannable portal, by `latest_status`: `ok` includes
        empty, `error` includes skipped, `not_reached` are those the time budget cut off and
        `never_attempted` those with a portal that has never been tried. `attempted` counts the
        employers actually attempted in the most recent finished run.
        """
        with self._db() as db:
            latest = db.execute('SELECT id FROM runs WHERE finished_at IS NOT NULL '
                                'ORDER BY finished_at DESC, rowid DESC LIMIT 1').fetchone()
        latest_run_id = latest['id'] if latest else None
        configured = [row for row in rows if row['inventory_state'] == 'configured']

        def outcome(*statuses):
            return sum(1 for row in configured if row['latest_status'] in statuses)

        def inventory(state):
            return sum(1 for row in rows if row['inventory_state'] == state)
        return {
            'original_rows': sum(len(row['original_rows'] or ()) for row in rows),
            'employers': sum(1 for row in rows if row['canonical'] is not None),
            'configured': len(configured),
            'attempted': sum(1 for row in configured if latest_run_id and any(
                source['run_id'] == latest_run_id for source in row['sources'])),
            'never_attempted': outcome(None),
            'not_reached': outcome(NOT_REACHED),
            'ok': outcome('ok', 'empty'), 'partial': outcome('partial'), 'blocked': outcome('blocked'),
            'maintenance': outcome('maintenance'), 'error': outcome('error', 'skipped'),
            'unverified': sum(1 for row in configured if row['unverified']),
            'not_configured': inventory('not configured'), 'unsupported': inventory('unsupported'),
            'wrong_scope': inventory('wrong scope only'), 'unresolved': inventory('identity unresolved'),
            'run_id': latest_run_id,
            'generated_at': now_iso(),
        }

    # ── key/value ──

    def kv_get(self, key, default=None):
        with self._db() as db:
            row = db.execute('SELECT value_json FROM kv WHERE key=?', (key,)).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row['value_json'])
        except ValueError:
            return default

    def kv_set(self, key, value):
        with self._db(write=True) as db:
            db.execute('INSERT OR REPLACE INTO kv(key, value_json) VALUES (?,?)',
                       (key, json.dumps(value, ensure_ascii=False, default=str)))


# Every key of a coverage row, in the order exports list them.
COVERAGE_COLUMNS = ('canonical', 'original_names', 'original_rows', 'type', 'bengaluru', 'parent', 'career_url', 'portals',
                    'linkedin_query', 'inventory_state', 'inventory_note', 'unverified', 'last_attempt_at',
                    'last_success_at', 'latest_status', 'latest_reason', 'latest_error', 'run_id', 'pages_complete',
                    'details_complete', 'jobs_total', 'jobs_on_file', 'jobs_open', 'sources', 'next_action')

_REASON_ACTIONS = {
    'tls': 'Fix certificate trust on this PC (proxy or antivirus certificate), then retry incomplete sources.',
    'dns': 'The site name did not resolve; check the network or the configured host, then retry.',
    'timeout': 'The site did not answer in time; retry incomplete sources.',
    'refused': 'The site refused the request; open the careers page by hand and keep its own job alert on.',
    'unreachable': 'The site could not be reached; check the network or VPN, then retry incomplete sources.',
    'rate_limited': 'The site asked to slow down; retry incomplete sources later.',
    'http_4xx': 'The configured board address was rejected; check the tenant or site in companies.json.',
    'http_5xx': 'The site had a server error; retry incomplete sources later.',
    'shape': 'The site answered in an unexpected form; the adapter needs an update.',
    'cap': 'The site returns more results than can be paged; the adapter needs a narrower query.',
    'budget': 'Not reached within the time budget; run "Retry incomplete sources".',
    'maintenance': 'The site was in maintenance; retry incomplete sources later.',
}


def _next_action(row) -> str:
    """What the user should do about one coverage row, in a sentence."""
    state, status = row['inventory_state'], row['latest_status']
    note = f" ({row['inventory_note']})" if row.get('inventory_note') else ''
    portal_note = next((portal['note'] for portal in row['portals'] if portal.get('note')), None)
    if state == 'identity unresolved':
        return 'Decide which employer this target refers to' + note + '.'
    if state == 'not configured':
        return 'No career portal is configured; only general LinkedIn discovery applies. Use the careers page' + note + '.'
    if state == 'unsupported':
        return 'No adapter is possible yet: ' + (portal_note or 'see the portal note') + '.'
    if state == 'wrong scope only':
        return 'The known board does not cover India or this entity: ' + (portal_note or 'see the portal note') + '.'
    if status is None:
        return 'Not attempted yet; run a full scan.'
    if status == NOT_REACHED:
        return _REASON_ACTIONS['budget']
    if status in ('ok', 'empty'):
        return ('Read correctly, but a portal is unverified; run "radar.py verify" to confirm it.' if row['unverified']
                else 'Nothing to do; the latest attempt read this employer in full.')
    return _REASON_ACTIONS.get(row['latest_reason'] or ('refused' if status == 'blocked' else status),
                               'The latest attempt was incomplete; run "Retry incomplete sources".')
