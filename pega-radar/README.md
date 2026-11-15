# Pega Radar

A private, local job radar for one person: a Pega CSSA developer in **Bengaluru** looking for **product-company and
captive-centre (GCC)** roles. Once a day it searches public job sources for Pega roles across India, ranks them with
Bengaluru and product/GCC employers first, and shows them in a local website where you can browse, save, track
applications and keep notes.

It was written from scratch on 14 November 2026. The older project in `../01_pega_career_intelligence/` was used only
as a reference; nothing here depends on it.

## Technology

Python 3.10+ **standard library only** — no `pip install`, no browser automation, no build step. SQLite for storage.
The website is plain HTML, CSS and JavaScript served from your own machine and works offline.

## Start here (Windows)

**Before you begin** you need Python 3.10 or newer. Open *Command Prompt* and type `python --version`. If it is
missing or older, install it from https://www.python.org/downloads/ and tick **"Add python.exe to PATH"** on the
first installer screen. Nothing else needs installing.

1. Copy `PegaRadar.zip` to your own PC and unzip it (right-click → *Extract All*) somewhere permanent, for example
   `C:\PegaRadar`. You get a `pega-radar` folder; everything below happens inside it. Use a personal machine and
   network: the scan sends ordinary anonymous web requests to job sites, and those are visible to whoever runs the
   network.
2. Check the installation (no network): open the `pega-radar` folder, click the address bar, type `cmd`, press
   Enter, then run `python -B radar.py doctor`. It should end with "Everything needed is in place".
3. Run the first scan: double-click **`SCAN.cmd`** (or `python -B radar.py scan`). The first run looks back 30 days and
   can take up to about 40 minutes; later runs only cover the days since the last good LinkedIn sweep.
4. Open the website: double-click **`START.cmd`** (or `python -B radar.py serve`). It opens `http://127.0.0.1:8765/`.
   Close the window to stop it.
5. Schedule the daily scan: `powershell -ExecutionPolicy Bypass -File setup_schedule.ps1`
   (07:30 by default; `-Time 06:45`, `-SecondTime 19:00` and `-Remove` are supported).

You can also press **Scan now** in the website.

## What it searches

| Source | Coverage |
| --- | --- |
| LinkedIn (public guest search) | Pega keyword variants for Bengaluru first, then all India, then seven other cities, then `pega <employer>` for 42 Bengaluru product/GCC employers. Not tied to the company list, so unknown employers are found. Descriptions are read for new postings, Bengaluru and product/GCC first |
| Employer job boards | 78 official boards queried directly (Workday and Oracle Recruiting; Greenhouse and Lever adapters exist for entries you add) |
| India job boards | Instahyre, Cutshort, Shine, Hirist, TimesJobs |

### What it does not cover — read this

- **Naukri and Foundit** refuse automated access, and this tool does not try to get around that. Keep their own
  e-mail job alerts for "Pega" switched on. Naukri is India's largest board, so this is the biggest gap.
- **Employers on SuccessFactors, Taleo, iCIMS, Phenom or custom career sites** have no direct adapter; they are
  covered only through LinkedIn and the boards. NTT DATA, BD and Toyota are in this group (their earlier board
  entries pointed at the wrong company or a US-only board and were removed).
- Roles filled by referral or recruiter outreach are never posted anywhere.

No tool can promise 100%. What this one promises instead is that a source failure is never silent (next section).

## Reading the website

- **New** is an inbox: a role stays there until you open it (or press *Mark all as seen*), for up to 14 days. Running
  another scan does not empty it.
- Default filters are **Bengaluru** and **Product + GCC**. Chips above the list show every active filter, each
  removable with one click, and the result line says how many more roles sit outside the filters. Nothing is deleted
  for a low score — weak matches are just listed last.
- **Fit** (0–100) is a sorting aid: Pega developer role → Bengaluru → product/GCC employer → experience fits your
  tenure (counted from August 2022) → advertised salary meets ₹30 LPA → recency. Services and staffing employers,
  8+ year or lead-only titles, junior titles, non-developer roles and postings older than 60 days are pushed down.
  It is not a hiring probability, and "30+ plausible" is a statement about the employer type, never a confirmed budget.
- **Hide** only hides; it never changes a role's status. **Pipeline** holds Applied, Interviewing, Offer and Rejected.
- Your current employer (set in `config.json`) is kept but sorted last and labelled.
- **Sources** shows how every source answered in the last good scan. Statuses: `ok` found roles · `empty` answered,
  none listed · `partial` some pages missing or a page limit was reached · `blocked` access refused ·
  `maintenance` Workday's weekly window (Saturday afternoon IST) · `skipped` not attempted · `error` anything else,
  including a page whose layout changed. Anything other than `ok`/`empty` raises a warning strip naming the source.

Keyboard: `j`/`k` or arrows move, `Enter` opens, `s` saves, `x` hides, `/` searches, `?` lists shortcuts.

## If something goes wrong

| What you see | What to do |
| --- | --- |
| `python` is not recognised | Python is not installed or not on PATH. Reinstall it with "Add python.exe to PATH" ticked, then open a new Command Prompt |
| `doctor` reports a problem | It prints the fix next to each problem. The usual cause is an incomplete unzip: extract the whole zip again |
| PowerShell refuses to run `setup_schedule.ps1` | Use the full command shown above, including `-ExecutionPolicy Bypass` |
| The website does not open | Run `python -B radar.py serve` in the folder and open the address it prints. If port 8765 is taken it picks the next free one |
| "Another scan is already running" | A scheduled or earlier scan is still going. Wait for it; a lock left by a crashed scan is taken over automatically |
| A source shows `blocked` or `partial` on LinkedIn | The site is rate limiting. Do nothing: the next run resumes where this one stopped. If it happens every day, raise `linkedin.pacing_seconds` in `config.json` to 2 |
| A source shows `error` | Open **Sources** and read the note. "unexpected response shape" or "no job cards" means that site changed its page; the other sources are unaffected. Send the newest file in `data/logs/` to whoever maintains the code |
| Several employer sites show `maintenance` | Workday's weekly window (Saturday afternoon IST). They are checked again on the next run |
| The scan seems slow the first time | Expected: the first run looks back 30 days. Later runs take a few minutes |

To move to another PC or back up: copy the whole `pega-radar` folder, including `data/`. To start completely fresh,
delete the `data` folder.

## Commands

```
python -B radar.py scan [--minutes N] [--open]   exit 0 complete · 2 a source needs attention (results saved) · 1 failed
python -B radar.py serve [--port N] [--no-browser]
python -B radar.py doctor                        offline installation check
python -B radar.py export [path]                 CSV of every saved role with your status and notes
python -B radar.py rescore                       re-rank after editing config.json or companies.json
```

## Configuration

- `config.json` — your profile (career start, target LPA, current employer), LinkedIn keywords and cities, request
  pacing, description budget per run, scan time budget, server port, and the browser `User-Agent` sent with requests.
- `companies.json` — 200 employers with `type` (`product`, `gcc`, `enterprise`, `services`, `staffing`), a
  `bengaluru` flag (`true` only where your November research shows a Bengaluru team, otherwise `null` = unknown), and
  an optional `ats` block for employers whose job board is queried directly. To add a Workday employer, take the three
  values from its board URL `https://<tenant>.<wdN>.myworkdayjobs.com/<site>`:
  `"ats": {"kind": "workday", "tenant": "...", "datacentre": "wd5", "site": "..."}`. Run `rescore` afterwards.

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

- `python -B -m unittest discover -s tests` — 329 tests at the time of writing, all offline (fake HTTP, temporary
  databases, the server on a loopback test port). One website test drives `web/app.js` in Node and is skipped when
  Node is not installed.
- Three developers built the core, the sources and the website in parallel against `ARCHITECTURE.md`; two independent
  reviews and an acceptance pass followed, and their confirmed findings were fixed.
- **Not yet done, deliberately:** the project was built on a machine where live job-site traffic was not allowed, so
  **no live scan has been run with this code** and **the website has never been opened in a real browser**. The
  endpoint formats were carried over from adapters verified against live responses on 14 November 2026. Treat your
  first scan as the live test: open **Sources**, and if a source shows `error` or `blocked` the message says why.
  `START.cmd`, `SCAN.cmd` and `setup_schedule.ps1` were checked by content only, not executed on Windows.

## Directory structure

```
pega-radar/
  README.md            this file
  ARCHITECTURE.md      module contracts and design rules (read before changing code)
  radar.py             command line: scan | serve | doctor | export | rescore
  config.json          profile and preferences
  companies.json       employer registry (type, Bengaluru flag, job-board endpoints)
  START.cmd  SCAN.cmd  setup_schedule.ps1     Windows launchers and scheduler setup
  radar/
    model.py           text utilities (Pega / India / Bengaluru detection), job and result shapes, config loading
    net.py             HTTP client: per-site pacing, Retry-After, backoff, circuit breaker
    store.py           SQLite storage, de-duplication across sources, your saved state
    rank.py            employer classification and fit scoring
    scan.py            scan orchestrator, look-back window, run lock
    server.py          local web server and JSON API (loopback only)
    sources/           linkedin.py, ats.py (Workday, Oracle, Greenhouse, Lever), boards.py
  web/                 index.html, app.js, app.css
  tests/               test_core.py, test_sources.py, test_server.py, fixtures/
  data/                created on first run: radar.sqlite3, logs/
```
