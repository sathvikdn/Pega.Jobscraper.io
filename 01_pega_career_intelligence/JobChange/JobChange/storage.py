"""Local SQLite persistence. Every call owns its connection for safe thread use."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS records (kind TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(kind,id))')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS companies (
                    id TEXT PRIMARY KEY, canonical_name TEXT NOT NULL, domain TEXT,
                    employer_type TEXT NOT NULL DEFAULT 'unknown', type_verified INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS company_aliases (
                    alias TEXT PRIMARY KEY, company_id TEXT NOT NULL REFERENCES companies(id));
                CREATE TABLE IF NOT EXISTS scan_runs (
                    id TEXT PRIMARY KEY, state TEXT NOT NULL, started_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, company_id TEXT REFERENCES companies(id), title TEXT NOT NULL,
                    company_domain TEXT, requisition_id TEXT, probable_key TEXT, match_basis TEXT NOT NULL,
                    level TEXT, min_yoe REAL, max_yoe REAL, salary_min REAL, salary_max REAL,
                    salary_currency TEXT, work_mode TEXT, city TEXT, state TEXT, country TEXT,
                    first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS job_sources (
                    url TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id), source TEXT NOT NULL,
                    posting_id TEXT, application_url TEXT, status TEXT NOT NULL, first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL, run_id TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS job_observations (
                    id INTEGER PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id), source TEXT NOT NULL,
                    source_posting_id TEXT, raw_title TEXT, raw_employer TEXT, raw_location TEXT, raw_salary TEXT,
                    detail_url TEXT NOT NULL, run_id TEXT NOT NULL, observed_at TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS source_attempts (
                    id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, source TEXT NOT NULL, state TEXT NOT NULL,
                    observed_at TEXT NOT NULL, diagnostics TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS rejected_observations (
                    id INTEGER PRIMARY KEY,run_id TEXT NOT NULL,source TEXT NOT NULL,observed_at TEXT NOT NULL,
                    error TEXT NOT NULL,payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS target_coverage (
                    run_id TEXT NOT NULL,target_id TEXT NOT NULL,source TEXT NOT NULL,company TEXT NOT NULL,
                    url TEXT,status TEXT NOT NULL,candidate_count INTEGER NOT NULL DEFAULT 0,
                    diagnostic TEXT NOT NULL DEFAULT '{}',updated_at TEXT NOT NULL,
                    PRIMARY KEY(run_id,target_id,source));
                CREATE INDEX IF NOT EXISTS coverage_pending ON target_coverage(run_id,status,source);
                CREATE INDEX IF NOT EXISTS jobs_location ON jobs(country,city,state);
                CREATE INDEX IF NOT EXISTS jobs_experience ON jobs(min_yoe,max_yoe);
                CREATE INDEX IF NOT EXISTS jobs_salary ON jobs(salary_currency,salary_min,salary_max);
                CREATE INDEX IF NOT EXISTS jobs_company ON jobs(company_id,company_domain,requisition_id);
                CREATE INDEX IF NOT EXISTS jobs_probable ON jobs(probable_key);
                CREATE INDEX IF NOT EXISTS jobs_mode ON jobs(work_mode,level);
                CREATE INDEX IF NOT EXISTS observations_run ON job_observations(run_id,source);
                CREATE INDEX IF NOT EXISTS sources_job ON job_sources(job_id,status);
                CREATE INDEX IF NOT EXISTS sources_identity ON job_sources(source,posting_id);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def put(self, kind, key, payload):
        with self.connect() as db:
            db.execute('INSERT INTO records VALUES (?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at',
                       (kind, key, json.dumps(payload, ensure_ascii=False), now()))

    def get(self, kind, key, default=None):
        with self.connect() as db:
            row = db.execute('SELECT payload FROM records WHERE kind=? AND id=?', (kind,key)).fetchone()
        return json.loads(row[0]) if row else default

    def all(self, kind):
        with self.connect() as db:
            rows = db.execute('SELECT id,payload FROM records WHERE kind=? ORDER BY updated_at DESC', (kind,)).fetchall()
        return {key:json.loads(payload) for key,payload in rows}

    def register_company(self, name, domain='', aliases=(), employer_type='unknown', verified=False):
        from normalizer import clean_company, key
        canonical=clean_company(name)
        if not canonical:raise ValueError('Canonical employer name is required')
        if employer_type not in ('gcc','product','services','unknown'):raise ValueError('Invalid employer type')
        company_id=key(canonical)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT INTO companies VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET canonical_name=excluded.canonical_name,domain=excluded.domain,employer_type=excluded.employer_type,type_verified=excluded.type_verified',
                       (company_id,canonical,domain,employer_type,int(verified)))
            for alias in (name,*aliases):
                normalized=key(alias)
                conflict=db.execute('SELECT company_id FROM company_aliases WHERE alias=?',(normalized,)).fetchone()
                if conflict and conflict[0]!=company_id:raise ValueError('Alias is already assigned to another employer')
                db.execute('INSERT OR IGNORE INTO company_aliases VALUES (?,?)',(normalized,company_id))
        return company_id

    def save_job_batch(self, run_id, source, observations, diagnostics=None, stop_event=None, observed_at=None):
        import uuid
        from normalizer import normalize_job, probable_key
        stamp = observed_at or now()
        saved = []
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for raw in observations:
                if stop_event is not None and stop_event.is_set():raise InterruptedError('Source batch cancelled')
                try:
                    row = normalize_job(raw)
                except (TypeError,ValueError) as error:
                    db.execute('INSERT INTO rejected_observations(run_id,source,observed_at,error,payload) VALUES (?,?,?,?,?)',
                               (run_id,source,stamp,str(error),json.dumps(raw)))
                    continue
                company_id = row['company_key'] or 'unconfirmed:'+row['url']
                alias = db.execute('SELECT company_id FROM company_aliases WHERE alias=?', (company_id,)).fetchone()
                if alias:company_id = alias[0]
                db.execute('INSERT OR IGNORE INTO companies(id,canonical_name,domain) VALUES (?,?,?)',
                           (company_id,row['company'],row['company_domain']))
                if row['company_key']:
                    db.execute('INSERT OR IGNORE INTO company_aliases VALUES (?,?)', (row['company_key'],company_id))
                company_record=db.execute('SELECT canonical_name,domain,employer_type,type_verified FROM companies WHERE id=?',(company_id,)).fetchone()
                row['company']=company_record[0]
                row['company_domain']=row['company_domain'] or company_record[1] or ''
                row['employer_type']=company_record[2] if company_record[3] else 'unknown'
                row['company_key'] = company_id if row['company_key'] else ''
                fingerprint = probable_key(row)
                found = db.execute('SELECT job_id FROM job_sources WHERE url=?', (row['url'],)).fetchone()
                basis = 'exact_url'
                if not found and row['source_posting_id']:
                    found=db.execute('SELECT job_id FROM job_sources WHERE source=? AND posting_id=?',(source,row['source_posting_id'])).fetchone()
                    basis='exact_source_id'
                if not found and row['company_domain'] and row['requisition_id']:
                    found = db.execute('SELECT id FROM jobs WHERE company_domain=? AND requisition_id=?',
                                       (row['company_domain'],row['requisition_id'])).fetchone()
                    basis = 'exact_requisition'
                if not found and fingerprint:
                    candidates = db.execute('SELECT id,requisition_id FROM jobs WHERE probable_key=?', (fingerprint,)).fetchall()
                    for candidate_id, requisition in candidates:
                        if requisition and row['requisition_id'] and requisition != row['requisition_id']:continue
                        same_source = db.execute('SELECT 1 FROM job_sources WHERE job_id=? AND source=?', (candidate_id,source)).fetchone()
                        if not same_source:
                            found = (candidate_id,);basis = 'probable';break
                job_id = found[0] if found else 'job-'+uuid.uuid4().hex
                previous = db.execute('SELECT payload,first_seen_at,match_basis FROM jobs WHERE id=?', (job_id,)).fetchone()
                first_seen = previous[1] if previous else stamp
                primary_source=raw.get('source') or source
                if previous:
                    old = json.loads(previous[0])
                    if old.get('description_complete') and not row.get('description_complete'):
                        for field in ('description_text','description_complete','description_source_url','description_checked_at','job_detail_status'):
                            if field in old:row[field] = old[field]
                    if old.get('source') == 'Employer career page' and source != 'Employer career page':
                        row['url'] = old['url']
                        primary_source=old['source']
                    if previous[2] == 'probable':basis = 'probable'
                row.update(id=job_id, first_seen_at=first_seen, last_seen_at=stamp, match_basis=basis,
                           source=primary_source, checked_at=stamp)
                db.execute('''INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET title=excluded.title,level=excluded.level,
                    min_yoe=excluded.min_yoe,max_yoe=excluded.max_yoe,salary_min=excluded.salary_min,
                    salary_max=excluded.salary_max,salary_currency=excluded.salary_currency,
                    work_mode=excluded.work_mode,last_seen_at=excluded.last_seen_at,payload=excluded.payload,
                    match_basis=excluded.match_basis''',
                    (job_id,company_id,row['title'],row['company_domain'],row['requisition_id'],fingerprint,basis,
                     row['level'],row['min_yoe'],row['max_yoe'],row['salary_min'],row['salary_max'],row['salary_currency'],
                     row['work_mode'],row['city'],row['state'],row['country'],first_seen,stamp,json.dumps(row)))
                detail_url = normalize_job(raw)['url']
                db.execute('''INSERT INTO job_sources VALUES (?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(url) DO UPDATE SET last_seen_at=excluded.last_seen_at,run_id=excluded.run_id,status=excluded.status''',
                    (detail_url,job_id,source,row['source_posting_id'],detail_url if source=='Employer career page' else None,
                     'active',stamp,stamp,run_id))
                db.execute('''INSERT INTO job_observations(job_id,source,source_posting_id,raw_title,raw_employer,
                    raw_location,raw_salary,detail_url,run_id,observed_at,payload) VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                    (job_id,source,row['source_posting_id'],raw.get('title'),raw.get('company'),raw.get('location'),
                     json.dumps(raw.get('salary')),detail_url,run_id,stamp,json.dumps(raw)))
                saved.append(job_id)
            if stop_event is not None and stop_event.is_set():raise InterruptedError('Source batch cancelled')
            db.execute('INSERT INTO source_attempts(run_id,source,state,observed_at,diagnostics) VALUES (?,?,?,?,?)',
                       (run_id,source,'COMPLETED',stamp,json.dumps(diagnostics or {})))
        return saved

    def list_jobs(self, city=None, company_id=None):
        conditions, parameters = [], []
        for field, value in (('city',city),('company_id',company_id)):
            if value is not None:conditions.append(field+'=?');parameters.append(value)
        query = 'SELECT id,payload FROM jobs'+(' WHERE '+' AND '.join(conditions) if conditions else '')
        with self.connect() as db:
            result = []
            for job_id, payload in db.execute(query, parameters).fetchall():
                row = json.loads(payload)
                row['sources'] = [dict(zip(('url','source','application_url','status','first_seen_at','last_seen_at'), source))
                                  for source in db.execute('SELECT url,source,application_url,status,first_seen_at,last_seen_at FROM job_sources WHERE job_id=?', (job_id,))]
                result.append(row)
        return result
