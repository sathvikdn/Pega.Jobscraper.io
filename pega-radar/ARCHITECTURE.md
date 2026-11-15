# Pega Radar — architecture and module contracts

A standalone, from-scratch job radar for one user: a Pega CSSA developer (Pega Developer at Mercedes-Benz R&D India
since August 2022) in **Bengaluru**, targeting **product companies and captive centres (GCCs)** at ₹30 LPA+.
The older project in `../01_pega_career_intelligence/` is a **read-only reference**; nothing here imports from it.

## Goals

1. Find every publicly posted Pega role in India once a day, in minutes, with Bengaluru and product/GCC employers first.
2. Never lose an opening silently: every source reports `ok | empty | partial | blocked | maintenance | skipped | error`.
3. One local website to browse, filter, save, track applications and take notes.
4. Effortless on Windows: Python 3.10+ standard library only. No pip install, no browser automation, no build step.

## Hard rules (apply to everyone working on this)

- **Standard library only.** No third-party imports anywhere (runtime or tests). `unittest` for tests.
- **Resilient, not evasive.** Rate limits are handled by pacing, `Retry-After`, backoff, a per-host circuit breaker,
  caching and resumable checkpoints. Requests carry a standard browser `User-Agent` (configurable in `config.json`,
  the form the public endpoints were verified with) and nothing else: no cookies, no sign-in, no rotating identities
  or proxies, no challenge solving, and no working around an access-denied response. A refused source is reported as
  `blocked`.
- **A failed source is never reported as `empty`.**
- **Loopback only.** The web server binds `127.0.0.1` (constant, not configurable to a wider bind), validates `Host`,
  and requires a per-process token + JSON content type + same-origin on every mutation.
- All HTML shown in the UI is built with `textContent`/escaping. Job text is untrusted input. Links are `http(s)` only,
  opened with `rel="noopener noreferrer"`.
- Windows-safe: UTF-8 file I/O everywhere, `pathlib`, no POSIX-only calls, console output must not crash on cp1252.
- **Development is offline.** No request to any job site, board or employer during development or tests. Tests use
  fixtures and a fake HTTP client.

## Layout

```
pega-radar/
  radar.py               CLI: scan | serve | doctor | export          (core)
  config.json            profile and preferences                      (core)
  companies.json         employer registry                            (sources)
  START.cmd  SCAN.cmd  setup_schedule.ps1                             (core)
  radar/
    model.py   text utilities, job and result shapes                  (core)
    net.py     HTTP client                                            (core)
    store.py   SQLite persistence                                     (core)
    rank.py    employer classification and fit scoring                (core)
    scan.py    orchestrator                                           (core)
    sources/   __init__.py, linkedin.py, ats.py, boards.py            (sources)
    server.py  local web server + JSON API                            (web)
  web/         index.html, app.js, app.css                            (web)
  tests/       test_core.py, test_sources.py, test_server.py, fixtures/
  data/        runtime only: radar.sqlite3, logs/ (created on demand, git-ignored)
```

## `radar/model.py`

```python
PEGA_RE                      # (?<![a-z])(prpc|pega(?!sus|tron)), case-insensitive: matches Pega_Developer, Pega8, PegaDeveloper; never Pegasus/Pegatron
is_pega(text) -> bool
CITY_ALIASES                 # alias -> canonical: bangalore/bengaluru->Bengaluru, gurgaon/gurugram->Gurugram, ...
cities(text) -> list[str]    # canonical Indian cities found, in order, de-duplicated
is_india(text) -> bool       # a known Indian city or the word India
is_bengaluru(text) -> bool   # city names, common misspellings, BLR, and well-known Bengaluru localities
outside_india(text) -> bool  # True only on positive foreign evidence; blank, unknown and "Remote" are kept
salary_lpa(text)             # LPA band from board text; None for foreign currencies
load_config(path=None) -> dict   # config.json deep-merged onto DEFAULT_CONFIG
strip_html(html) -> str      # tags removed, entities decoded, block tags become newlines
now_iso() -> str             # UTC, seconds, e.g. 2026-11-14T02:00:00+00:00
company_key(name) -> str     # lowercase alphanumerics only, legal suffixes (pvt, ltd, limited, inc, india, llp, private) removed

def make_job(source, source_id, title, company, url, location, *, posted_at=None, description='',
             experience_min=None, experience_max=None, salary_min_lpa=None, salary_max_lpa=None,
             apply_url=None, requisition_id=None, employment_type=None, extra=None) -> dict
# Returns a plain dict with exactly those keys. `source_id` is a str unique within the source.
# `posted_at` is 'YYYY-MM-DD' or None. `description` is plain text ('' when not read).

def make_result(source, label, kind, *, status='ok', jobs=(), found=0, requests=0, error=None) -> dict
# {'source','label','kind','status','found','kept','requests','error','jobs'}; kept = len(jobs).
# kind is 'linkedin' | 'ats' | 'board'. For ATS, source='Employer site' and label=<company name>.

STATUSES = ('ok','empty','partial','blocked','maintenance','skipped','error')
def needs_attention(result) -> bool   # True for partial, blocked, maintenance, skipped, error
```

## `radar/net.py`

```python
class Response: status:int; text:str; url:str; error:str
    ok (2xx) ; blocked (status in 401,403,406,429,999) ; json() -> object | None ; header(name) -> str | None

class Http:
    def __init__(self, *, deadline=None, stop=None, pacing=None, default_pacing=0.5, timeout=25, opener=None)
    # deadline: time.monotonic() value; stop: threading.Event; pacing: {host: seconds between requests}
    # opener: injectable callable(urllib.request.Request, timeout) for tests
    def get(self, url, *, headers=None, accept='application/json', retries=2) -> Response
    def post_json(self, url, payload, *, headers=None, retries=2) -> Response
    def expired(self) -> bool
    def host_open(self, url_or_host) -> bool      # False while that host's circuit breaker is open
    requests: int                                 # total attempts
    def host_report(self) -> dict                 # {host: {'requests','blocked','errors','pacing'}}
```

Behaviour: per-host serialised pacing with jitter; honours `Retry-After`; on 429/999 doubles that host's pacing
(cap 8 s) and retries; pacing decays back towards its base after consecutive successes; after 5 consecutive blocked
or failed responses the host's breaker opens for the rest of the run and every further call returns immediately with
`status=0, error='circuit open'`. gzip handled. Never raises for network errors. Thread-safe.

## `radar/store.py`

SQLite (WAL), one connection per call, safe from several threads.

```
jobs(id PK, title, company, company_key, employer_type, city, cities_json, location, is_bengaluru,
     url, apply_url, description, experience_min, experience_max, salary_min_lpa, salary_max_lpa,
     posted_at, requisition_id, first_seen_at, last_seen_at, first_run_id, last_run_id,
     score, fit_json, pega_title, pega_duty)
sightings(source, source_id, job_id, url, label, first_seen_at, last_seen_at, PRIMARY KEY(source, source_id))
user_state(job_id PK, saved, status, notes, updated_at)       -- status: new|interested|applied|interviewing|offer|rejected|hidden
runs(id PK, started_at, finished_at, status, summary_json)     -- status: running|complete|partial|failed
source_health(run_id, source, label, kind, status, found, kept, requests, error)
kv(key PK, value_json)
```

```python
class Store:
    def __init__(self, path)
    def start_run(self) -> str                                  # run id; started_at = now_iso()
    def finish_run(self, run_id, status, summary: dict)
    def save_result(self, run_id, result, ranker) -> dict       # {'new': [job ids], 'updated': [job ids]}
        # ranker(job_dict) -> {'employer_type','score','fit','pega_title','pega_duty'}; called for every upsert.
        # Also writes one source_health row for the result.
    def jobs(self, *, view='all', city='all', types=None, q='', min_score=0, sort='score',
             limit=100, offset=0) -> tuple[list[dict], int]     # (rows without description, total)
        # view: new (first_run_id == latest finished run) | all | saved | applied (status in applied,interviewing,offer)
        #       | hidden. Every view except 'hidden' excludes status 'hidden' and 'rejected'.
        # city: 'bengaluru' | 'all' | a canonical city. types: iterable of employer types or None.
        # sort: score | posted | first_seen (all descending).
    def job(self, job_id) -> dict | None                        # full row + 'sightings' list + user state
    def set_state(self, job_id, *, saved=None, status=None, notes=None) -> dict | None
    def latest_run(self) -> dict | None                         # includes 'health': [source_health rows]
    def stats(self) -> dict                                     # totals for the header tiles
    def known_ids(self, source, *, with_description=True) -> set[str]
    def kv_get(self, key, default=None); def kv_set(self, key, value)
    def rescore(self, ranker) -> int                            # re-run the ranker over every job
    def export_rows(self) -> list[dict]
```

Identity when saving a job (first match wins): same `(source, source_id)` sighting → same job; same `company_key`
+ `requisition_id`; same `company_key` + normalised title + same primary city (cross-source merge). On merge keep the
longest description, the earliest `posted_at`, prefer an employer-site URL over a board URL, and never clear a field
with an empty value. User state is keyed by job id and is never modified by a scan.

## `radar/rank.py`

```python
def load_registry(path) -> Registry                 # companies.json
class Registry:
    def classify(self, company) -> tuple[str, dict | None]   # (employer_type, entry); name patterns as fallback
    # employer_type: 'product' | 'gcc' | 'services' | 'staffing' | 'unknown'
def parse_experience(text) -> tuple[float | None, float | None]
def make_ranker(config, registry, today=None) -> callable     # the `ranker` passed to Store.save_result
```

Score 0–100, a sorting aid only. Largest weights, in this order: Pega developer role (title names Pega; description
shows Pega duties) → **Bengaluru** → **product / GCC employer** → experience fits the candidate's tenure → advertised
salary meets the target → recency. Penalties: services and staffing employers, 8+ years or lead/architect-only titles,
junior titles, non-developer roles (testing, BA, support), postings older than 60 days. `fit` is
`{'reasons': [str], 'labels': {'employer_type','pay','experience','bengaluru': bool}}`. Nothing is ever dropped for a
low score.

## `radar/sources/`

```python
class Task:                       # defined in sources/__init__.py
    name: str                     # stable id, e.g. 'linkedin', 'ats:workday:cba', 'board:hirist'
    label: str                    # display name
    kind: str                     # 'linkedin' | 'ats' | 'board'
    priority: int                 # lower runs first
    def run(self, http, ctx) -> dict   # a make_result() dict; must never raise

def build_tasks(config, registry, store) -> list[Task]
```

`ctx` is a dict: `{'window_days': int, 'store': Store, 'config': dict, 'log': logging.Logger}`.

- `linkedin.py` — public guest job search. Query plan is **Bengaluru first**: every keyword for Bengaluru, then
  India-wide, then the other cities, then `pega <employer>` for registry entries flagged `linkedin_query`. Paging stops
  after three consecutive pages without a Pega title. Descriptions are read for new postings, Bengaluru and
  product/GCC first, within a budget. Finished queries are checkpointed in `kv` so an interrupted or rate-limited run
  resumes instead of starting again. Postings found not to be Pega roles are remembered and not re-read.
- `ats.py` — Workday CXS, Oracle Recruiting, Greenhouse, Lever. One Task per registry entry with an `ats` block.
- `boards.py` — Instahyre, Cutshort, Shine, Hirist, TimesJobs public feeds.

Endpoint shapes and parsing must be ported from the reference file
`../01_pega_career_intelligence/JobChange/JobChange/pega_sources.py`, whose adapters were verified against live
responses on 14 November 2026 (Shine there uses BeautifulSoup — re-implement with `html.parser`/regex).

## `companies.json`

```json
{"companies": [{"name": "Commonwealth Bank", "aliases": ["CBA", "CommBank"], "type": "gcc", "bengaluru": true,
                "linkedin_query": true,
                "ats": {"kind": "workday", "tenant": "cba", "datacentre": "wd3", "site": "CommBank_Careers"}}]}
```

`type` is `product | gcc | services | staffing`. `bengaluru` is `true`, `false` or `null` (unknown) and must come
from the reference research files, never guessed. `ats` is optional.

## `radar/scan.py`

```python
def run_scan(config, store, *, http=None, tasks=None, progress=None, minutes=None) -> dict
# Builds tasks (unless given), runs them concurrently (thread pool; the Http client does per-host pacing),
# saves each result as it arrives, records progress in kv['scan_progress'], finishes the run, returns the summary:
# {'run_id','started_at','finished_at','minutes','status','new','new_bengaluru','new_product_gcc','requests',
#  'sources': [result without 'jobs'], 'attention': [labels]}
# window_days: days since the last complete run + 2 (min 3, max 30); 30 on the first run.
def scan_lock(data_dir)   # context manager; pid-aware (works on Windows), stale locks are taken over
```

## `radar/server.py`

`serve(store, config, *, port=8765, open_browser=True)`; `make_handler(store, config, token, scan_controller)` is
exposed for tests (ephemeral port 0 on 127.0.0.1).

| Route | Result |
| --- | --- |
| `GET /` , `GET /static/<file>` | the single-page app (files from `web/` only; no path traversal) |
| `GET /api/bootstrap` | `{token, profile, stats, latest_run, scan}` |
| `GET /api/jobs?view=&city=&types=&q=&min_score=&sort=&limit=&offset=` | `{jobs, total}` |
| `GET /api/jobs/<id>` | full job with description, sightings, fit, state |
| `POST /api/jobs/<id>/state` `{saved?, status?, notes?}` | updated state |
| `POST /api/scan` `{}` | starts a background scan (409 if one is running) |
| `GET /api/scan/status` | `{running, progress, last_summary}` |
| `GET /api/export.csv` | all jobs with state |

Defaults in the UI: **Bengaluru** and **Product + GCC** filters on, view "New", sorted by fit — with one click to
widen to all India / all employers so nothing is hidden.

## Verification

`python -B -m unittest discover -s tests` must pass offline. `python radar.py doctor` checks the installation without
network access.

## Decisions made after review (these supersede the text above where they differ)

- **New is an inbox, not "the latest run".** `user_state` has `hidden` (boolean, independent of `status`) and
  `seen_at`. A job is new when it is not hidden, has status `new`, has never been seen, and was first seen within
  14 days. `status` is `new|interested|applied|interviewing|offer|rejected` (no `hidden`).
  `Store.set_state(..., hidden=None, seen=None)`, `Store.mark_all_seen()`, and `POST /api/jobs/seen-all`.
  Views: `all` (not hidden, not rejected), `saved`, `applied` (applied, interviewing, offer, rejected — shown as
  "Pipeline"), `hidden`.
- `latest_run()` is the last `complete` or `partial` run with its health rows, plus `last_attempt` for the most
  recent finished run of any status, so a failed scan never blanks the coverage table.
- `GET /api/jobs` also returns `counts` for every tab under the active filters. Search matches title, company,
  location and description.
- **Cross-source merging is bounded.** Company + title + city merges only when the existing job was seen in the last
  30 days, the new `posted_at` is within 30 days of the old one, and the existing job is neither hidden nor rejected.
  Company names are canonicalised through the registry first. Jobs are never dropped for a missing title or id.
- **A source may only say `empty` when the expected rows are present and empty.** A wrong response shape, a page with
  no parseable cards, or a wrong board name is `error`. Stopping at a page limit while more results exist is `partial`.
- **Locations only exclude on positive foreign evidence** (`model.outside_india`). LinkedIn cards are never dropped
  for their card location; every query is already India-scoped.
- **LinkedIn state** in `kv`: `linkedin_checkpoint`, `linkedin_rejected`, `linkedin_backlog` (descriptions wanted but
  not read; read first next run; dropped after three failed tries) — all written once, at the end of a run, so an
  interrupted run loses only time. `linkedin_last_ok_at` drives the look-back and is stamped only when LinkedIn itself
  answered `ok`/`empty` with results or a previous stamp exists.
- Employer types add `enterprise` (Indian domestic employer with in-house IT). `companies.json` entries may carry
  `current_employer: true`, and a Workday `ats` block may list `more_sites`. `bengaluru: false` is reserved for
  research that explicitly rules Bengaluru out; "not found" is `null`.
- `config.json` adds `http.user_agent` and `profile.current_employer`. Jobs at the current employer score 0 and are
  labelled, not hidden.
- Server additions: `Cross-Origin-Resource-Policy: same-origin`, a 15 s socket timeout, `Host` must carry this
  server's exact port, unknown `view`/`sort`/state fields answer 400, `POST /api/scan` answers 202 and takes the same
  run lock as the command line.
