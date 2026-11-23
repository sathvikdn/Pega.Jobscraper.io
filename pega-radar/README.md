# Pega Radar

A private, local job radar for one person: a Pega CSSA developer in **Bengaluru** looking for **product-company and
captive-centre (GCC)** roles. Once a day it searches public job sources for Pega roles across India, ranks them with
Bengaluru and product/GCC employers first, and shows them in a local website where you can browse, save, track
applications and keep notes.

It was written from scratch on 14 November 2026 and extended on 15 November 2026 (v2) from your career-portal audit:
many more direct employer career sites, and a Coverage view that shows exactly which employers are covered and how. The older project in `../01_pega_career_intelligence/` was used only
as a reference; nothing here depends on it.

## Technology

Python 3.10+ **standard library only** — no `pip install`, no browser automation, no build step. SQLite for storage.
The website is plain HTML, CSS and JavaScript served from your own machine and works offline.

## UI update

The interface uses open top navigation, a personal first-use search brief, a source illustration and comparison
cards for opportunities. It includes light and dark themes, responsive layouts, and a readable detail panel. Saved, Pipeline and Hidden keep independent filters. Notes
retain a browser draft until saved, and bulk read actions affect only the unread roles currently displayed.
Cards show missing salary explicitly and prioritize relevant cautions; additional controls live under **Refine search**.

See `docs/ui-design.md` for the design decisions and `docs/ui-validation.md` for verification and preview images.
No frontend installation or build step has been added.

## Start on macOS or Linux

Extract `PegaRadar-creative-ui.zip`, then run these commands from its `pega-radar` folder:

```sh
python3 -B radar.py doctor
python3 -B radar.py serve
```

The server opens the local website. Start a scan from the website when you are ready to search.

## Start here (Windows)

**Before you begin** you need Python 3.10 or newer. Open *Command Prompt* and type `python --version`. If it is
missing or older, install it from https://www.python.org/downloads/ and tick **"Add python.exe to PATH"** on the
first installer screen. Nothing else needs installing.

1. Copy `PegaRadar-creative-ui.zip` to your own PC and unzip it (right-click → *Extract All*) somewhere permanent, for example
   `C:\PegaRadar`. You get a `pega-radar` folder; everything below happens inside it. Use a personal machine and
   network: the scan sends ordinary anonymous web requests to job sites, and those are visible to whoever runs the
   network.
2. Check the installation (no network): open the `pega-radar` folder, click the address bar, type `cmd`, press
   Enter, then run `python -B radar.py doctor`. It should end with "Everything needed is in place".
3. Run the first scan: double-click **`SCAN.cmd`** (or `python -B radar.py scan`). The first run looks back 30 days and
   can take up to about 40 minutes; later runs only cover the days since the last good LinkedIn sweep.
4. Open the website: double-click **`START.cmd`** (or `python -B radar.py serve`). It opens `http://127.0.0.1:8765/`.
   Close the window to stop it.
5. **Check the new employer sites once (v2):** run `python -B radar.py verify`. It makes a few small requests to each
   of the 76 employer career sites added from your audit ("candidates") and takes up to about 20 minutes. It writes a
   report to `data/acceptance/verify-<date>.md` listing each one as **passed**, **inconclusive** or **failed** with the
   reason. Then run `python -B radar.py verify --promote` to mark the passed ones as verified (it backs up
   `companies.json` first and makes no network requests). Send the report file to whoever maintains your copy of
   Pega Radar so failed sites can be fixed. Candidates are scanned before and after this; `verify` only tells you
   which ones really work.
6. Schedule the daily scan: `powershell -ExecutionPolicy Bypass -File setup_schedule.ps1`
   (07:30 by default; `-Time 06:45`, `-SecondTime 19:00` and `-Remove` are supported).

In the website, **Full scan** searches every configured source and **Retry incomplete sources** re-runs only the
ones that failed, were cut off by the time limit, or have not been tried yet. "Partial" is an outcome, not a different
kind of search.

**Upgrading from the first version:** unzip v2 over a copy of your old folder, keeping its `data` folder. On first
start your database is backed up to `data/backups/` and upgraded in place; saved roles, notes and statuses are kept.

## What it searches

| Source | Coverage |
| --- | --- |
| LinkedIn (public guest search) | Pega keyword variants for Bengaluru first, then all India, then seven other cities, then `pega <employer>` for 42 Bengaluru product/GCC employers. Not tied to the company list, so unknown employers are found. Descriptions are read for new postings, Bengaluru and product/GCC first |
| Employer career sites | 154 official boards for 134 employer groups, queried directly: 78 verified (Workday, Oracle) and 76 candidates from your audit (Workday, Oracle, SuccessFactors, TalentBrew, Phenom, Eightfold, SmartRecruiters, iCIMS, Avature, BeeSite, Greenhouse, Ashby). Only Pega roles in India are kept; each board reads at most 120 new job descriptions per run and continues the rest next run |
| India job boards | Instahyre, Cutshort, Shine, Hirist, TimesJobs |

### What it does not cover — read this

- **Naukri and Foundit** refuse automated access, and this tool does not try to get around that. Keep their own
  e-mail job alerts for "Pega" switched on. Naukri is India's largest board, so this is the biggest gap.
- **41 employer groups have no direct career-site scan** and are covered only through LinkedIn and the boards. The
  **Coverage** tab lists each with its reason: the site was unreachable or refused access in your audit (e.g. Cisco,
  Siemens, Allianz, Ford, BNP Paribas), it uses a system that needs a browser or a login (PeopleStrong for BMW
  TechWorks, RippleHire for HDFC Bank, Taleo, BrassRing, Paradox), it has a custom search page that needs its own
  parser (e.g. Goldman Sachs, ICICI Bank, Pegasystems), or only a US/retail board exists (BD USA, Toyota North America,
  Columbia retail, Bank of America US lateral hiring).
- **Candidate sites may not work yet.** Their response formats are partly assumed because they could not be checked
  from the machine this was built on. A mismatch shows as `error: unexpected response shape` in Coverage, never as
  "no jobs". Run `verify` (step 5) to find out.
- Roles filled by referral or recruiter outreach are never posted anywhere.

No tool can promise 100%. What this one promises instead is that a source failure is never silent (next section).

## Reading the website

- **New roles** is an inbox: a role stays unread until you open, save or mark it as read, for up to 14 days.
  **Mark these N as read** affects only unread roles currently loaded in the list; roles outside the filters remain
  unread. Running another scan does not empty the inbox.
- **New roles** and **All roles** start with **Bengaluru** and **Product + GCC** filters. **Saved**, **Pipeline** and
  **Hidden** start with all locations and employers and keep separate filter preferences. Navigation counts include
  all locations and employers; the result line shows the current filters. Each active filter can be removed with
  one click, and the result line says how many more roles sit outside those filters.
- **Notes** save automatically. A draft stays in this browser until the local server confirms the save, including
  after a reload. If browser storage is unavailable, keep the tab open until the note says **Saved**.
- **Fit** (0–100) is a sorting aid: Pega developer role → Bengaluru → product/GCC employer → experience fits your
  tenure (counted from August 2022) → advertised salary meets ₹30 LPA → recency. Services and staffing employers,
  8+ year or lead-only titles, junior titles, non-developer roles and postings older than 60 days are pushed down.
  It is not a hiring probability, and "30+ plausible" is a statement about the employer type, never a confirmed budget.
- **Hide** only hides; it never changes a role's status. **Pipeline** holds Applied, Interviewing, Offer and Rejected.
- Your current employer (set in `config.json`) is kept but sorted last and labelled.
- **Scan sources** shows how every source answered in the last good scan. Open **Details** in the scan-status strip for
  requested, attempted and completed counts. Statuses: `ok` found roles · `empty` answered,
  none listed · `partial` some pages missing or a page limit was reached · `blocked` access refused ·
  `maintenance` Workday's weekly window (Saturday afternoon IST) · `skipped` not attempted · `error` anything else,
  including a page whose layout changed. Anything other than `ok`/`empty` raises a warning strip naming the source.

- A role marked **possibly closed** is no longer listed by any employer site or board that listed it, after two
  complete reads in a row. Roles seen only on LinkedIn are never flagged. Nothing is ever deleted.

### Employer coverage (v2)

Every one of the 286 rows of your original target list is accounted for (`targets.json`), grouped into 175 employer
groups. For each employer it shows separately:

- **Configured** — which career sites are set up for it (*verified*, *candidate* = set up but not yet live-checked,
  *wrong scope*, *unsupported*), and whether it has its own `pega <employer>` LinkedIn search (a keyword search, not a
  guaranteed company filter).
- **Attempted** — when a scan last actually reached each site. *Not reached* means the time limit ran out first;
  *never attempted* means it has not been tried yet.
- **Result** — the latest outcome with its reason (timeout, certificate problem, DNS, refused, rate limited, page
  limit, layout changed …), whether all pages and descriptions were read, roles on file, and a plain next action.

An employer with no site configured is shown as a gap, never as "no jobs". **Export CSV** gives the same table; the
command line equivalents are `radar.py coverage` and `radar.py report`. `docs/career-coverage-before-after.md` compares
every target group before and after v2.

Keyboard: `j`/`k` or arrows move, `Enter` opens, `s` saves, `x` hides, `/` searches, `?` opens Help.

## If something goes wrong

| What you see | What to do |
| --- | --- |
| `python` is not recognised | Python is not installed or not on PATH. Reinstall it with "Add python.exe to PATH" ticked, then open a new Command Prompt |
| `doctor` reports a problem | It prints the fix next to each problem. The usual cause is an incomplete unzip: extract the whole zip again |
| PowerShell refuses to run `setup_schedule.ps1` | Use the full command shown above, including `-ExecutionPolicy Bypass` |
| The website does not open | Run `python -B radar.py serve` in the folder and open the address it prints. If port 8765 is taken it picks the next free one |
| "Another scan is already running" | A scheduled or earlier scan is still going. Wait for it; a lock left by a crashed scan is taken over automatically |
| A source shows `blocked` or `partial` on LinkedIn | The site is rate limiting. Do nothing: the next run resumes where this one stopped. If it happens every day, raise `linkedin.pacing_seconds` in `config.json` to 2 |
| A scan seems stuck after the other sources finish | LinkedIn is being rate limited. It now stops after `linkedin.minutes` (default 15) or after `linkedin.throttle_limit` refused requests (default 8), and the scan log prints a `LinkedIn: n of m searches done` line every 10 searches. The last `linkedin.detail_minutes` (default 5) of those minutes are kept for reading job descriptions, so searches can't use up the whole share. Unfinished searches resume on the next run. Avoid running two full scans in a row: use "Retry incomplete sources" instead |
| A candidate site shows `error: unexpected response shape` | Its format differs from what was assumed. Run `python -B radar.py verify --only "<employer>"` and send the report; the other sources are unaffected |
| A source shows "certificate could not be verified" | Usually a proxy or antivirus intercepting HTTPS on that network. Try another network; TLS checks are never turned off |
| Many sources show `not reached` | The time limit ran out. They go first next run; or press **Retry incomplete sources**. You can raise `scan.minutes` in `config.json` |
| A source shows `error` | Open **Sources** and read the note. "unexpected response shape" or "no job cards" means that site changed its page; the other sources are unaffected. Send the newest file in `data/logs/` to whoever maintains the code |
| Several employer sites show `maintenance` | Workday's weekly window (Saturday afternoon IST). They are checked again on the next run |
| The scan seems slow the first time | Expected: the first run looks back 30 days. Later runs take a few minutes |

To move to another PC or back up: copy the whole `pega-radar` folder, including `data/`. To start completely fresh,
delete the `data` folder.

## Commands

```
python -B radar.py scan [--minutes N] [--open]   exit 0 complete · 2 a source needs attention (results saved) · 1 failed
python -B radar.py scan --retry-incomplete       only sources that failed, were cut off, or were never tried
python -B radar.py scan --only "CBA,Wells Fargo" only these employers or sources
python -B radar.py verify [--only NAMES] [--state candidate|all] [--minutes N]
                                                 live-check career sites; writes data/acceptance/verify-*.md
python -B radar.py verify --promote              mark sites that passed as verified (backs up companies.json)
python -B radar.py coverage [path]               company coverage table (CSV and Markdown)
python -B radar.py report [path]                 acceptance report for the latest scan
python -B radar.py serve [--port N] [--no-browser]
python -B radar.py doctor                        offline installation check
python -B radar.py export [path]                 CSV of every saved role with your status and notes
python -B radar.py rescore                       re-rank after editing config.json or companies.json
```

## Configuration

- `config.json` — your profile (career start, target LPA, current employer), LinkedIn keywords and cities, request
  pacing, description budget per run, scan time budget, server port, and the browser `User-Agent` sent with requests.
- `companies.json` — 247 employers with `type` (`product`, `gcc`, `enterprise`, `services`, `staffing`), a
  `bengaluru` flag (`true` only where your November research shows a Bengaluru team, otherwise `null` = unknown),
  `career_url`, optional `parent`, and a `portals` list of career sites with their `state` and `scope`. To add a Workday
  employer, take the values from its board URL `https://<tenant>.<wdN>.myworkdayjobs.com/<site>`:
  `"portals": [{"kind": "workday", "tenant": "...", "datacentre": "wd5", "site": "...", "state": "candidate",
  "scope": "global"}]`, then run `verify --only "<employer>"`. Editing a site's identity makes it start again as
  "never attempted".
- `targets.json` — your original 286-row target list and which employer each row maps to. It is the denominator of
  coverage and never shrinks.

## How rate limits are handled

LinkedIn and the boards limit how fast anonymous visitors can search. The radar spaces its requests per site, honours
`Retry-After`, slows down further when a site pushes back, stops asking a site that keeps refusing for the rest of the
run, and checkpoints finished LinkedIn queries so the next run resumes instead of starting again. Descriptions it could
not read are queued and read first next time. It sends a standard browser `User-Agent` and nothing else: no sign-in,
no cookies, no proxies, no challenge solving, and it does not work around an access-denied response — a refusal is
shown as `blocked`.

## Privacy and safety

- Everything stays on your PC in `data/radar.sqlite3` (plus logs in `data/logs/`). Back up that file to keep your
  saved roles and notes. `PEGA_RADAR_DATA` can point the data folder elsewhere.
- The website listens on `127.0.0.1` only and cannot be reached from another machine; this is not configurable.
  Changes require a per-session token, so another website open in your browser cannot alter your data.
- Job text comes from the internet and is treated as untrusted everywhere it is displayed or exported.

## Verification status

- `python -B -m unittest discover -s tests` — 551 tests at the time of writing (v2), all offline (fake HTTP, temporary
  databases, the server on a loopback test port). One website test drives `web/app.js` in Node and is skipped when
  Node is not installed.
- Three developers built the core, the sources and the website in parallel against `ARCHITECTURE.md`; two independent
  reviews and an acceptance pass followed, and their confirmed findings were fixed. v2 was built the same way by four
  developers from your audit, followed by two more independent reviews and two acceptance passes.
- The UI was checked in local Chrome with synthetic roles and a separate empty database, across desktop, tablet
  and phone sizes in both themes. Search, collections, notes recovery, native dialogs, keyboard focus and error
  recovery were exercised against the local server. Details are in `docs/ui-validation.md`.
- **No live scan has been run as part of this development or UI validation.** The
  endpoint formats were carried over from adapters verified against live responses on 14 November 2026; the v2
  candidate sites rest on pages captured in your 15 November audit plus partly assumed formats. Treat `verify` and your
  first scan as the live test: open **Sources**, and if a source shows `error` or `blocked` the message says why.
  `START.cmd`, `SCAN.cmd` and `setup_schedule.ps1` were checked by content only, not executed on Windows.

## Directory structure

```
pega-radar/
  README.md            this file
  ARCHITECTURE.md      module contracts and design rules (read before changing code)
  radar.py             command line: scan | serve | verify | coverage | report | doctor | export | rescore
  config.json          profile and preferences
  companies.json       employer registry (type, Bengaluru flag, career sites with state and scope)
  targets.json         your original 286 target rows and the employer each maps to
  docs/                career-coverage-before-after.md
  START.cmd  SCAN.cmd  setup_schedule.ps1     Windows launchers and scheduler setup
  radar/
    model.py           text utilities (Pega / India / Bengaluru detection), job and result shapes, config loading
    net.py             HTTP client: per-site pacing, Retry-After, backoff, circuit breaker
    store.py           SQLite storage, de-duplication across sources, your saved state
    rank.py            employer classification and fit scoring
    scan.py            scan orchestrator: full / retry / only modes, fair ordering, time budget, run lock
    acceptance.py      verify, promote, coverage export, run report
    server.py          local web server and JSON API (loopback only)
    sources/           linkedin.py, ats.py (Workday, Oracle, Greenhouse, Lever), boards.py,
                       portals.py + portal_base.py + portal_api.py + portal_pages.py (the v2 career-site families)
  web/                 index.html, app.js, app.css
  tests/               test_core.py, test_sources.py, test_server.py, fixtures/
  data/                created on first run: radar.sqlite3, logs/, backups/, acceptance/
```
