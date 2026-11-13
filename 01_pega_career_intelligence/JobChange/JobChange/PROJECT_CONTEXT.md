# Pega Job Hunter — Full Project Context

> This file describes the complete architecture, data flow, APIs, scraping pipeline, UI, database schema, and testing infrastructure of this project. It is designed for an LLM to understand and work with the codebase immediately.

---

## 1. What This Project Is

A **private, local-only career research portal** for tracking Pega (BPM/low-code platform) job opportunities in India. It is built for one user — Sathvik — who is a Pega CSSA-certified developer with ~4 years of experience at Mercedes-Benz R&D India, looking for Pega roles at GCCs (Global Capability Centers), consulting/SI firms, and product companies.

**Key capabilities:**
- Searches 400+ employer targets across LinkedIn, employer career portals, and job boards
- Uses Playwright (headless Chromium) to render JavaScript-heavy career sites
- Has dedicated API adapters for Workday and Greenhouse ATS platforms
- Matches jobs to a Pega-specific skill vocabulary and resume
- Provides a per-job application pipeline tracker (status + notes)
- Compares job descriptions against the user's resume with an explainable score
- All data is local (SQLite + JSON files); nothing is sent to external services except search queries

**Tech stack:**
- **Backend:** Python 3.12, Flask, SQLite (WAL mode), BeautifulSoup4, Playwright
- **Frontend:** Vanilla JavaScript (no framework), Inter font, dark theme
- **Scraping:** Playwright headless Chromium, `urllib.request` for API calls
- **Dependencies:** `Flask>=3.1`, `requests>=2.32.4`, `beautifulsoup4>=4.13`, `lxml>=5.3`, `playwright==1.60.0`

---

## 2. Project Structure

```
JobChange/
├── app.py                    # Flask application — ALL routes, business logic, startup
├── career_scraper.py         # Playwright browser scraper + Workday/Greenhouse API adapters
├── storage.py                # SQLite Store class — all DB operations
├── normalizer.py             # Job normalization, LD+JSON parsing, company name cleaning
├── quality.py                # URL canonicalization, identity hashing, evidence freshness
├── opportunity_data.py       # Opportunity normalization, salary bucketing, employer types
├── job_matching.py           # Resume/JD comparison engine, Pega skill vocabulary
├── job_details.py            # Public description fetcher with redirect safety
├── verification.py           # Job listing recheck (open/closed/uncertain)
├── portal_scan.py            # Scan target selection, India filtering, result grouping
├── scan_coordinator.py       # Multi-source scan state machine, coverage ledger
├── parallel_scan.py          # Parallel LinkedIn HTTP scan engine
├── campaign.py               # Campaign orchestration, checkpointing, enrichment
├── master_catalog.py         # Curated scan targets, career URL mappings (~400 employers)
├── directory_data.py         # Company aliases and keyword mappings
├── people_research.py        # LinkedIn profile/team research integration
├── people_views.py           # People profile HTML rendering
├── pega_job_hunter.py        # Legacy single-threaded scanner (older code path)
├── report_builder.py         # HTML report generation
├── nightly_scan.py           # Scheduled scan runner
│
├── static/
│   ├── original-scanner.js   # Main dashboard UI — scan controls, results table, job modal
│   ├── job-workspace.js      # Shared job table component + application status dropdown
│   ├── search.js             # Full-text opportunity search UI
│   ├── intelligence-hub.js   # Company intelligence/catalogue browser
│   ├── investigation.js      # Independent investigation UI
│   ├── dossier-view.js       # Company dossier viewer
│   ├── depth.js              # Team depth analysis UI
│   ├── directory.js          # Employer directory browser
│   └── *.css                 # Theme stylesheets (dark mode, workspace, etc.)
│
├── templates/
│   ├── scanner.html          # Main portal template (scan launcher + results dashboard)
│   └── index.html            # Legacy portal template
│
├── research/                 # Preloaded research data (JSON)
│   ├── preloaded_search.json # Resumable scan checkpoint (targets + jobs + coverage)
│   ├── directory.json        # Employer directory with career URLs, team snapshots
│   ├── independent_map.json  # Independent investigation companies
│   ├── master_catalog.json   # Full catalogue (companies + people + source ledger)
│   └── *.json                # Historical research, crosschecks, audit findings
│
├── data/
│   ├── workspace.sqlite3     # Main SQLite database (jobs, companies, pipeline, etc.)
│   ├── career_scrape_log.json # Playwright scrape diagnostics
│   ├── career_url_overrides.json # Manual career URL corrections
│   └── *.log                 # Server logs
│
├── test_*.py                 # Test files (228+ tests)
├── requirements.txt          # Python dependencies
├── AGENTS.md                 # Verification commands and data safety rules
└── README.md                 # User-facing documentation
```

---

## 3. Database Schema (SQLite — `data/workspace.sqlite3`)

### Core tables

```sql
-- Generic key-value store (pipeline notes, preferences, scan state, etc.)
records (kind TEXT, id TEXT, payload TEXT [JSON], updated_at TEXT, PRIMARY KEY(kind,id))

-- Normalized employer directory
companies (id TEXT PRIMARY KEY, canonical_name TEXT, domain TEXT, employer_type TEXT, type_verified INTEGER)
company_aliases (alias TEXT PRIMARY KEY, company_id TEXT REFERENCES companies(id))

-- Deduplicated job postings (one row per unique job, regardless of how many sources found it)
jobs (id TEXT PRIMARY KEY, company_id TEXT, title TEXT, company_domain TEXT,
      requisition_id TEXT, probable_key TEXT, match_basis TEXT,
      level TEXT, min_yoe REAL, max_yoe REAL,
      salary_min REAL, salary_max REAL, salary_currency TEXT,
      work_mode TEXT, city TEXT, state TEXT, country TEXT,
      first_seen_at TEXT, last_seen_at TEXT, payload TEXT [JSON])

-- Each URL where a job was observed (LinkedIn, career page, job board, etc.)
job_sources (url TEXT PRIMARY KEY, job_id TEXT REFERENCES jobs(id), source TEXT,
             posting_id TEXT, application_url TEXT, status TEXT,
             first_seen_at TEXT, last_seen_at TEXT, run_id TEXT)

-- Raw observation log — every time a job is seen from any source
job_observations (id INTEGER PRIMARY KEY, job_id TEXT, source TEXT,
                  source_posting_id TEXT, raw_title TEXT, raw_employer TEXT,
                  raw_location TEXT, raw_salary TEXT, detail_url TEXT,
                  run_id TEXT, observed_at TEXT, payload TEXT [JSON])

-- Scan run state machine
scan_runs (id TEXT PRIMARY KEY, state TEXT, started_at TEXT, updated_at TEXT)

-- Per-target, per-source coverage tracking
target_coverage (run_id TEXT, target_id TEXT, source TEXT, company TEXT,
                 url TEXT, status TEXT, candidate_count INTEGER, diagnostic TEXT [JSON],
                 updated_at TEXT, PRIMARY KEY(run_id,target_id,source))

-- Source-level attempt log
source_attempts (id INTEGER PRIMARY KEY, run_id TEXT, source TEXT, state TEXT,
                 observed_at TEXT, diagnostics TEXT [JSON])

-- Observations rejected during normalization
rejected_observations (id INTEGER PRIMARY KEY, run_id TEXT, source TEXT,
                       observed_at TEXT, error TEXT, payload TEXT [JSON])
```

### Key-value `records` table usage (kind → id → JSON payload)

| kind | id | payload |
|---|---|---|
| `pipeline` | job_id | `{stage, notes, updated_at}` — application tracker per job |
| `verification` | job_id | `{status, detail, checked_at}` — recheck result |
| `job_descriptions` | canonical_url | Saved description snapshot |
| `meta` | `last_scan` | Last scan state snapshot |
| `meta` | `scanner_selection` | Selected targets, mode, baseline |
| `meta` | `search_preferences` | `{minimum_ctc_lpa, role_scope, category}` |
| `meta` | `board_jobs` | `{jobs, diagnostics, checked_at}` |
| `meta` | `job_identity_aliases` | `{canonical_url: stable_job_id}` — cross-scan identity |
| `meta` | `jobs_reset_at` | Timestamp; if set, historical seeds are excluded |
| `discovery` | company_name | Legacy scanner results |

---

## 4. Application Architecture & Data Flow

### Startup

```
python -B app.py --port 5050
```

1. `create_app()` initializes Flask, SQLite `Store`, CSRF token, scan state, `ScanCoordinator`
2. Reads `research/preloaded_search.json` for cached campaign results
3. Reads `research/directory.json` for employer directory (400+ targets with career URLs)
4. Serves the portal at `http://127.0.0.1:5050`

### Request flow for displaying jobs

```
Browser → GET /api/scan-results
  → opportunities() assembles all known jobs from:
     1. Legacy research JSON files (openings.json, expanded_openings.json, etc.)
     2. Campaign checkpoint (preloaded_search.json) — LinkedIn search results
     3. SQLite repository (jobs table) — Playwright-sourced jobs
     4. Board jobs (meta/board_jobs) — job board scrape results
  → Each job is normalized, deduplicated by canonical URL, assessed against resume
  → Pipeline status (stage + notes) is attached from records table
  → portal_scan.grouped_results() groups by employer target
  → Deduplication removes duplicate URLs, search/listing page false positives
  → Response: {companies: [{name, category, jobs: [...], checks: [...]}], policy_counts, ...}
```

### Scan execution flow

```
User clicks "Start scanning" → POST /api/scan {mode: "gcc_all"}
  → Selects targets from directory (gcc, services, or all)
  → Spawns background thread: original_scan_worker()
     │
     ├── Phase 1: LinkedIn HTTP API scan (parallel_scan.py)
     │   → Searches each target on LinkedIn for "pega {company}" in India
     │   → Parses search results, extracts job cards
     │   → Persists to SQLite via scan_coordinator.persist()
     │
     ├── Phase 2: LinkedIn Playwright retry (for blocked targets)
     │   → Opens linkedin.com/jobs/search in headless Chromium
     │   → Extracts rendered job cards
     │
     ├── Phase 3: Employer career portal scraping (career_scraper.py)
     │   → For each target with a career_url:
     │     1. Try Workday CXS API (if myworkdayjobs.com URL)
     │     2. Try Greenhouse board API (if greenhouse.io URL)
     │     3. Fall back to Playwright browser scraping:
     │        a. Navigate to career page
     │        b. Extract LD+JSON structured data
     │        c. Search for pega keyword in search box
     │        d. Extract visible HTML job cards
     │        e. Follow candidate detail links
     │   → Each result is Pega-evidence checked and India-scope filtered
     │
     ├── Phase 4: Job board scraping
     │   → Indeed India, Shine, Glassdoor, SimplyHired
     │   → Each board has its own search URL pattern
     │
     └── Phase 5: Description enrichment
         → For each job without a full description, fetches the public URL
         → Parses LD+JSON or HTML for the complete job posting text
         → Runs job_matching.assess_job() for resume comparison
```

### Job identity and deduplication

Jobs are identified and deduplicated in this priority order:
1. **Exact URL match** (canonical_url strips tracking params)
2. **Exact source + posting ID** (e.g., same LinkedIn job ID)
3. **Exact company domain + requisition ID**
4. **Probable key** (SHA-256 of company_key + title + city + state + experience range)

Cross-scan identity persistence: when a user saves a pipeline status, the canonical URL is stored as an alias → stable job ID. Future scans with different raw IDs for the same URL reuse the saved status.

---

## 5. API Reference

### Read endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Serves `scanner.html` (main portal) |
| `GET /api/health` | `{service, schema_version, instance_token, pid}` |
| `GET /api/bootstrap` | `{profile, token (CSRF), library, today, search_preferences}` |
| `GET /api/scan-options` | `{categories: {gcc: [...], si: [...], all: [...]}, total_targets}` |
| `GET /api/scan-results?scope=all` | Main dashboard data — grouped by employer |
| `GET /api/opportunities?scope=recommended` | All assessed jobs with resume scores |
| `GET /api/opportunities/<id>` | Single job detail |
| `GET /api/campaign` | Campaign status, checkpoint, coverage |
| `GET /api/directory` | Employer directory with team snapshots |
| `GET /api/catalogue` | Full company/people catalogue |
| `GET /api/company-dossier?name=X` | Company deep dossier (sources, offices, people) |
| `GET /api/board-jobs` | Job board scrape results |
| `GET /api/scrape-log` | Career scraper diagnostics |
| `GET /api/export` | CSV download of all opportunities |
| `GET /api/ingestion-health` | DB table counts and source attempts |
| `GET /api/teams` | Team research data |
| `GET /api/team-depth` | Team depth analysis |
| `GET /api/investigation` | Independent investigation companies |
| `GET /api/salaries` | Salary evidence |
| `GET /api/intelligence/companies/<cid>/people/<pid>` | Person profile HTML |

### Mutation endpoints (require CSRF token via `X-Career-Token` header + JSON body)

| Endpoint | Description |
|---|---|
| `POST /api/scan {mode}` | Start the original (portal_scan) scan flow |
| `POST /api/search {category, catalog_scope, ...}` | Start full campaign search |
| `POST /api/search/pause {}` | Stop a running scan |
| `POST /api/pipeline/<job_id> {stage, notes}` | Save application status for a job |
| `POST /api/opportunities/<id>/description {}` | Refresh a job's description |
| `POST /api/recheck {ids: [...]}` | Recheck job listings (open/closed) |

### Pipeline stages (application tracker)

```
unreviewed → shortlisted → contacted → applied → interviewing → offer → dismissed
```

UI labels: Not reviewed, Interested, Recruiter contacted, Applied, Interviewing, Offer, Not relevant / rejected

---

## 6. Career Scraper Pipeline (`career_scraper.py`)

### Workday CXS adapter

For URLs matching `*.myworkdayjobs.com`:

```
1. Parse tenant/site from URL: https://{tenant}.wd{N}.myworkdayjobs.com/en-US/{site}
2. POST /wday/cxs/{tenant}/{site}/jobs  {"searchText": "pega", "limit": 20, "offset": 0}
3. For each result, GET /wday/cxs/{tenant}/{site}/job/{externalPath}
4. Parse jobDescription HTML for Pega evidence + India scope
5. Return matching jobs with full description
```

### Greenhouse board adapter

For URLs matching `*greenhouse.io*`:

```
1. Extract board token from URL
2. GET https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true
3. Filter by Pega evidence + India scope in title/location/content
4. Return matching jobs with full description
```

### Generic Playwright scraper

```
1. Navigate to career URL (domcontentloaded, 2s wait)
2. Try to extract LD+JSON JobPosting structured data
3. Dismiss cookie/consent banners
4. Find search box → type "pega" → submit → wait for results
5. If no search box, try URL variants (?q=pega, ?keyword=pega, etc.)
6. Extract from visible HTML job cards (link text + parent context)
7. Follow candidate detail links and extract each page
8. All results filtered by: _is_pega_related(), _is_india_scope(), _is_search_or_listing_page()
```

### False positive filters

- `_is_search_or_listing_page(url, title)` — rejects search page URLs (`/jobsuche/`, `jobsearch?`, `/recherche/`) and page-title headings ("Search jobs at X", "Careers", "Browse Jobs")
- `_is_zero_result_page(body_text)` — detects "0 results", "no jobs found", "keine Ergebnisse"
- `_is_pega_related(text)` — requires Pega/PRPC/CSSA/CDH keywords in evidence
- `_is_india_scope(text)` — requires Indian city names or "India"/"Remote"

### Job boards

```python
JOB_BOARDS = [
    {name: 'Indeed India', url: 'https://www.indeed.co.in/jobs?q=pega&l=India'},
    {name: 'Shine', url: 'https://www.shine.com/job-search/pega-jobs'},
    {name: 'Glassdoor', url: 'https://www.glassdoor.co.in/Job/india-pega-jobs'},
    {name: 'SimplyHired', url: 'https://www.simplyhired.co.in/search?q=pega&l=india'},
    # Indeed US and Dice are paused
]
```

---

## 7. Job Matching Engine (`job_matching.py`)

### How `assess_job()` works

1. Parses the saved job description into role-relevant lines (strips boilerplate "About Us", "Equal Opportunity" sections)
2. Extracts **Pega evidence** — lines where Pega/PRPC appears with action verbs (develop, implement, configure)
3. Extracts **experience requirements** — parses ranges like "4-7 years", "5+ years", word numbers
4. Extracts **skill requirements** — matches against a 40+ item Pega skill vocabulary
5. Compares each skill against the resume (`sathvik_resume_v2.html`)
6. Produces:
   - `recommendation.status`: recommended / stretch / review / excluded
   - `recommendation.pega_evidence`: true/false (are Pega duties confirmed?)
   - `resume_match.score`: 0-100 weighted evidence score
   - `resume_match.matched[]`: skills found in both JD and resume
   - `resume_match.missing[]`: skills in JD but not in resume

### Recommendation policy

> Pega duties or requirements confirmed in a saved job description; stated experience below 8 years. Requirements above your 4 years are marked Stretch. Unknowns need verification.

- **Recommended**: Pega evidence confirmed, experience <=7 years, within skill match
- **Stretch**: Pega confirmed but experience >4 years or CLSA required
- **Review**: No full description read, or Pega evidence unclear
- **Excluded**: Experience >=8 years, expired, or explicitly non-Pega

---

## 8. Frontend Architecture

### Main portal (`scanner.html` + `original-scanner.js`)

Two-screen layout:
1. **Scan Launcher** — category tabs (GCC/Consulting/All), depth pills (Top 10/20/All), Start button
2. **Results Dashboard** — topbar with search/stats, company-grouped job table, job detail modal

### Key state variables in `original-scanner.js`

```javascript
selectedCat    // 'gcc' | 'si' | 'all'
selectedMode   // 'gcc_top10' | 'gcc_top20' | 'gcc_all' | 'si_top' | 'si_all' | 'all'
allResults     // Array of company groups from /api/scan-results
csrf           // CSRF token from /api/bootstrap
scanActive     // Boolean — is a scan running?
detailJob      // Currently opened job in modal
filterCategory // Company category filter
filterLocation // Location filter
```

### Job detail modal

When "View description" is clicked:
1. Fetches `GET /api/opportunities/<id>` for full detail
2. Displays: title, company, location, salary, experience, recommendation
3. Shows full plain-text job description
4. Shows resume match score with matched/missing skills
5. Application status dropdown + notes textarea + Save button

### Shared components (`job-workspace.js`)

- `JobWorkspace.table(jobs, openDetail, openDossier, savePipeline)` — renders the job table
- `JobWorkspace.statusSelect(stage, name)` — returns a `<select>` with all 7 pipeline stages
- `JobWorkspace.stages` — array of `[value, label]` pairs

### Application status flow

```
Dashboard dropdown change → savePipeline callback
  → POST /api/pipeline/<job_id> {stage, notes}
  → Update local allResults cache immediately
  → If error: revert dropdown, show "Not saved" feedback
  → If success: update detailJob if modal is open for same job
```

### CSS theme

Dark mode with purple/indigo accent:
- Background: `#09090b`
- Card: `#111113`
- Border: `#27272a`
- Primary: `#6366f1` (indigo)
- Accent: `#a855f7` (purple)
- Text: `#e4e4e7`
- Font: Inter

---

## 9. User Profile (hardcoded in `app.py`)

```python
PROFILE = {
    'name': 'Sathvik',
    'years_experience': 4,
    'location': 'Bengaluru',
    'current_employer': 'Mercedes-Benz R&D India',
    'joining_date': '2026-12-02',
    'current_ctc': 1157434.49,  # INR annual
    'tcs': {'fixed': 1362636, 'performance': 252000, 'city': 21600, 'retirals': 63769, 'total': 1700005},
    'target_ctc_min': 2000000,   # 20 LPA
    'target_ctc_max': 3500000,   # 35 LPA
    'goal_ctc': 3500000,
    'search_floor_ctc': 2000000,
    'skills': ['Pega CSSA', 'Kafka', 'REST / SOAP', 'SQL', 'Auto finance', 'Production automation']
}
```

---

## 10. Testing

### Run all tests

```bash
python -B -m unittest test_unified_repository test_scan_coordinator test_workspace_browser test_portal test_original_flow test_job_matching test_job_recommendations test_campaign test_parallel_scan test_parallel_client test_people_views test_intelligence_layout test_career_scraper
```

Currently **228+ tests** passing.

### Test files and what they cover

| File | Covers |
|---|---|
| `test_portal.py` | API routes, CSRF protection, pipeline persistence, identity matching, verification |
| `test_original_flow.py` | Scan options, grouped results, board sweep, baseline, description overlay |
| `test_career_scraper.py` | Playwright extraction, false positive rejection, Workday/Greenhouse adapters |
| `test_unified_repository.py` | Job dedup (URL, requisition, probable key), company registration, save_job_batch |
| `test_scan_coordinator.py` | State machine, coverage ledger, domain budget |
| `test_workspace_browser.py` | Browser fixture tests (Playwright → Flask test client) |
| `test_job_matching.py` | Resume/JD comparison, experience parsing, Pega evidence detection |
| `test_job_recommendations.py` | Recommendation policy (recommended/stretch/review/excluded) |
| `test_campaign.py` | Campaign checkpointing, enrichment, interruption |
| `test_parallel_scan.py` | Parallel scan engine |
| `test_parallel_client.py` | Parallel HTTP client |
| `test_people_views.py` | People profile rendering |
| `test_intelligence_layout.py` | Intelligence hub layout |

### Browser tests

Uses Playwright's `sync_api` with a Flask test client adapter. No external sites are accessed. Tests create temporary SQLite databases and mock all external responses.

---

## 11. Key Design Decisions & Gotchas

1. **Everything is local-only.** No cloud DB, no external API keys, no telemetry. The portal runs on `127.0.0.1:5050`.

2. **Multiple data sources converge.** Jobs come from 6+ origins (legacy JSON, campaign checkpoint, SQLite repository, board_jobs, employer career pages, LinkedIn). The `opportunities()` function in `app.py` merges them all.

3. **Identity follows URL.** A job's stable ID is derived from its canonical URL (SHA-256). The `quality.canonical_url()` function strips tracking params, normalizes LinkedIn slugs, etc.

4. **Pipeline status follows the URL too.** When a user saves "Applied" for a job, the canonical URL is stored as an alias. If a future scan produces the same URL with a different raw ID, the old status is preserved.

5. **Description is king.** A job is only "recommended" if its full description has been read and shows Pega duties. A title containing "Pega" is not enough. The `job_matching.py` engine is conservative.

6. **India scope only.** Remote/global/US searches are paused. The active scope is India cities (Bengaluru, Hyderabad, Pune, Chennai, Mumbai, Delhi, etc.).

7. **Salary floor is 20 LPA.** Jobs with confirmed CTC below INR 20,00,000/year are excluded. Unknown salary is kept.

8. **Search page false positive detection.** The scraper can land on a zero-result search page (e.g., `/jobsuche/pega/` in German) where "pega" appears only because it's echoed in the search bar. `_is_search_or_listing_page()` and `_is_zero_result_page()` catch these.

9. **Never delete production data.** Tests use temporary databases. The production `workspace.sqlite3` is never cleaned or deduplicated during verification.

10. **CSRF protection.** All mutations require `X-Career-Token` header matching the server's random token, plus `Content-Type: application/json` and same-origin check.

---

## 12. How to Run

```bash
# Install dependencies
pip install -r requirements.txt
python -m playwright install chromium

# Start the portal
python -B app.py --port 5050

# Open in browser
http://127.0.0.1:5050

# Run tests
python -B -m unittest discover -s . -p 'test_*.py'
```

---

## 13. File-Level Summary (every significant Python file)

| File | Lines | Role |
|---|---|---|
| `app.py` | ~900 | Flask app, all routes, `opportunities()` assembler, scan workers, CSRF |
| `career_scraper.py` | ~1180 | Playwright scraper, Workday/Greenhouse adapters, job board scrapers |
| `storage.py` | ~200 | SQLite Store class, `save_job_batch()`, `register_company()` |
| `normalizer.py` | ~150 | Job normalization, LD+JSON parsing, `from_jobposting()`, `probable_key()` |
| `quality.py` | ~105 | `canonical_url()`, `job_identity()`, `effective_status()`, offer comparison |
| `opportunity_data.py` | ~77 | `normalize_opportunity()`, `salary_bucket()`, `company_key()` |
| `job_matching.py` | ~420 | `assess_job()`, Pega skill vocabulary, resume comparison, experience parsing |
| `portal_scan.py` | ~117 | `grouped_results()`, `india_job()`, `select_targets()`, `scan_options()` |
| `scan_coordinator.py` | ~170 | `ScanCoordinator` state machine, `CoverageLedger`, `DomainBudget` |
| `verification.py` | ~100 | `recheck()` — public HTTPS page classification (open/closed/uncertain) |
| `job_details.py` | ~80 | `PublicDescriptionClient`, safe redirect following, description snapshots |
| `master_catalog.py` | ~400 | Curated scan targets, career URL mappings for ~400 employers |
| `campaign.py` | ~300 | Campaign orchestration, `run_campaign()`, `enrich_campaign()` |
| `parallel_scan.py` | ~250 | Parallel LinkedIn HTTP scan with rate limiting |
| `original-scanner.js` | ~400 | Dashboard UI, scan controls, job modal, application status |
| `job-workspace.js` | ~100 | Shared job table + status dropdown component |
| `scanner.html` | ~700 | HTML template with all CSS (dark theme) |
