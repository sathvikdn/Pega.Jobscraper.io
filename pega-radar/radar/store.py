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

USER_STATUSES = ('new', 'interested', 'applied', 'interviewing', 'offer', 'rejected')
NEW_DAYS = 14             # a job nobody has looked at stops counting as new after this long
MAX_PAGE = 500
UNTITLED = 'Pega role (title not given)'
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
    pega_title INTEGER NOT NULL DEFAULT 0, pega_duty INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS jobs_company ON jobs(company_key);
CREATE INDEX IF NOT EXISTS jobs_first_run ON jobs(first_run_id);
CREATE TABLE IF NOT EXISTS sightings(
    source TEXT NOT NULL, source_id TEXT NOT NULL, job_id TEXT NOT NULL, url TEXT NOT NULL DEFAULT '',
    label TEXT NOT NULL DEFAULT '', first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
    PRIMARY KEY(source, source_id));
CREATE INDEX IF NOT EXISTS sightings_job ON sightings(job_id);
CREATE TABLE IF NOT EXISTS user_state(
    job_id TEXT PRIMARY KEY, saved INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'new',
    notes TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL, hidden INTEGER NOT NULL DEFAULT 0, seen_at TEXT);
CREATE TABLE IF NOT EXISTS runs(
    id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL, summary_json TEXT);
CREATE TABLE IF NOT EXISTS source_health(
    run_id TEXT NOT NULL, source TEXT, label TEXT, kind TEXT, status TEXT, found INTEGER, kept INTEGER,
    requests INTEGER, error TEXT);
CREATE INDEX IF NOT EXISTS source_health_run ON source_health(run_id);
CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value_json TEXT NOT NULL);
'''

_JOB_COLUMNS = ('id', 'title', 'company', 'company_key', 'employer_type', 'city', 'cities_json', 'location',
                'is_bengaluru', 'url', 'apply_url', 'description', 'experience_min', 'experience_max',
                'salary_min_lpa', 'salary_max_lpa', 'posted_at', 'requisition_id', 'first_seen_at', 'last_seen_at',
                'first_run_id', 'last_run_id', 'score', 'fit_json', 'pega_title', 'pega_duty')
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
            db.executescript(_SCHEMA)
            outdated = 'hidden' not in {row['name'] for row in db.execute('PRAGMA table_info(user_state)')}
        if outdated:
            self._migrate_user_state()

    def _migrate_user_state(self):
        """Bring a database from before `hidden` and `seen_at` existed up to date, keeping every row."""
        with self._db(write=True) as db:
            columns = {row['name'] for row in db.execute('PRAGMA table_info(user_state)')}
            if 'hidden' not in columns:       # checked again under the write lock: another process may have won
                db.execute('ALTER TABLE user_state ADD COLUMN hidden INTEGER NOT NULL DEFAULT 0')
            if 'seen_at' not in columns:
                db.execute('ALTER TABLE user_state ADD COLUMN seen_at TEXT')
            # Hiding used to be a status, which overwrote where the job stood in the pipeline.
            db.execute("UPDATE user_state SET hidden = 1, status = 'new', seen_at = COALESCE(seen_at, updated_at) "
                       "WHERE status = 'hidden'")

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
            health = [dict(item) for item in db.execute(
                'SELECT source, label, kind, status, found, kept, requests, error FROM source_health '
                'WHERE run_id=? ORDER BY rowid', (row['id'],))] if row else []
        return {'id': row['id'] if row else None, 'started_at': row['started_at'] if row else None,
                'finished_at': row['finished_at'] if row else None, 'status': row['status'] if row else None,
                'summary': json.loads(row['summary_json'] or '{}') if row else {}, 'health': health,
                'last_attempt': {'id': attempt['id'], 'status': attempt['status'], 'finished_at': attempt['finished_at'],
                                 'error': json.loads(attempt['summary_json'] or '{}').get('error')}}

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
        result's jobs were actually stored, and is what the health row records.
        """
        now = now_iso()
        new, updated, kept = [], [], 0
        with self._db(write=True) as db:
            for job in result.get('jobs') or ():
                if not isinstance(job, dict):
                    continue                      # nothing to store; `kept` will show the shortfall
                job_id, created = self._upsert(db, run_id, result, self._complete(job), ranker, now)
                kept += 1
                if created:
                    new.append(job_id)
                elif job_id not in new and job_id not in updated:
                    updated.append(job_id)
            db.execute('INSERT INTO source_health VALUES (?,?,?,?,?,?,?,?,?)',
                       (run_id, result.get('source'), result.get('label'), result.get('kind'), result.get('status'),
                        max(result.get('found') or 0, kept), kept, result.get('requests', 0), result.get('error')))
        return {'new': new, 'updated': updated, 'kept': kept}

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

    def _upsert(self, db, run_id, result, job, ranker, now):
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
                   is_bengaluru=int('Bengaluru' in merged_cities), last_seen_at=now, last_run_id=run_id)
        self._apply_rank(row, ranker)
        db.execute(f'INSERT OR REPLACE INTO jobs({", ".join(_JOB_COLUMNS)}) VALUES ({", ".join("?" * len(_JOB_COLUMNS))})',
                   [row[column] for column in _JOB_COLUMNS])
        db.execute('INSERT INTO sightings(source, source_id, job_id, url, label, first_seen_at, last_seen_at) '
                   'VALUES (?,?,?,?,?,?,?) ON CONFLICT(source, source_id) DO UPDATE SET '
                   'job_id=excluded.job_id, url=excluded.url, label=excluded.label, last_seen_at=excluded.last_seen_at',
                   (source, source_id, row['id'], job.get('url') or '', result.get('label') or '', now, now))
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
        for flag in ('is_bengaluru', 'pega_title', 'pega_duty', 'saved', 'hidden', 'is_new', 'has_description'):
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
                f'j.requisition_id, j.first_seen_at, j.last_seen_at, {_STATE_SELECT} '
                'FROM jobs j LEFT JOIN user_state u ON u.job_id = j.id ORDER BY ' + _SORTS['score']).fetchall()
            sources = self._sources(db)
        exported = []
        for row in rows:
            item = dict(row)
            item['saved'], item['hidden'] = bool(item['saved']), bool(item['hidden'])
            item['sources'] = ', '.join(sources.get(item['id'], []))
            exported.append(item)
        return exported

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
