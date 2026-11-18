# Pega job scanners and career portal research

## Current scraper: Pega Radar (18 November 2026)

The current standalone scanner is in [pega-radar/](pega-radar/). Start with its [README](pega-radar/README.md) and [architecture](pega-radar/ARCHITECTURE.md).

```powershell
cd pega-radar
python radar.py serve
```

Open http://127.0.0.1:8765/. See the app README for scanning and scheduling commands. Runtime databases, logs and Python caches are excluded from this new app upload.

This version is synchronized from the active installation at `C:\Users\sathv\Desktop\job hunter\pega-radar`. It includes the updated UI, target inventory, portal adapters, verification/coverage commands, and additional boards for Bank of America BA Continuum, BD India, Columbia Sportswear corporate, ABB, Chevron and PwC Acceleration Center recruitment.

The 16 November targeted operational run completed all 12 requested portal sources. Both Bank of America roles were retained, along with the previously captured Zurich role. New board configuration does not guarantee relevant openings or exhaustive employer coverage.

### Latest board-scope audit

- [Company-by-company audit](career-board-scope-audit/REPORT.md)
- [Machine-readable findings](career-board-scope-audit/company-findings.json)
- [Audit evidence ZIP](career-board-scope-audit.zip)

The audit describes findings before the subsequent board additions. The current `pega-radar/companies.json` is authoritative for what is configured now. Historical source snapshots in the handoff folders are retained as research references.

## Claude implementation handoff

1. Read [CLAUDE_PROMPT.md](career-portal-handoff/CLAUDE_PROMPT.md).
2. Read [CLAUDE_CHANGE_BRIEF.md](career-portal-handoff/CLAUDE_CHANGE_BRIEF.md) for priorities and acceptance criteria.
3. Use the [117-target audit report](career-portal-handoff/REPORT.md) and [machine-readable manifest](career-portal-handoff/portal-manifest.json).
4. The [complete ZIP](career-portal-handoff.zip) includes observations, compressed evidence and reference source snapshots.

Local paths in the handoff describe the research machine. In this repository, implement changes in `pega-radar/`. The `career-portal-handoff/reference_new/` and `reference_old/` directories are reference snapshots, not the active application.

The original audit identified 25 targets with responding Workday searches, 77 with reachable pages but unverified integrations, and 15 unresolved targets. Those are historical research counts. Parts of the expansion are now implemented in the current app; unsupported sites, unresolved identities and access failures remain gaps. Consult current coverage and verification reports rather than treating the historical counts as today's successful coverage.

The existing `01_pega_career_intelligence/` tree contains the older application and career-intelligence archive. Its original upload documentation follows.

---

# Job Scraper and Career Portals Upload Copy 2026-11-13

## Purpose

This folder is a non-destructive duplicate copy prepared for upload or handoff. It collates the complete Pega job scraper / JobChange application and the related company-specific career intelligence portals from `01_pega_career_intelligence`.

The original project remains at `C:\Users\DNSATHV\Desktop\calude\01_pega_career_intelligence` and was not moved or modified by the copy operation.

## Context

Created on 13 November 2026 after the owner asked to gather the complete job scraper and the company-specific portals such as the Career Intelligence portal into a duplicate copy.

The copy operation duplicated `01_pega_career_intelligence` into this folder using `robocopy /E`. The copy transcript reported:

- Directories copied: 305
- Files copied: 3,362
- Bytes copied: 302.79 MB
- Failed files/directories: 0

## Technology stack

- Python / Flask-style local app for the JobChange career desk.
- SQLite / JSON / CSV state and evidence files for job scanning, company research, profiles, reports and saved portal state.
- Static HTML/CSS/JavaScript portals and study/dossier pages.
- Node.js ES modules and Puppeteer for hub builders, report generation and visual verification.
- PowerShell/CMD helper scripts for setup and scheduled scans.
- Existing dependency folders are included as copied content: `node_modules\`, `JobChange\JobChange\.deps\`, and Python `__pycache__\` folders.

## Primary entry points

Inside `01_pega_career_intelligence\`:

- `Pega_Career_Intelligence_Hub.html` — current offline Career Intelligence portal.
- `Pega_Deep_Dossiers.html` — company/team dossier portal.
- `pega_job_hunter.py` — standalone job-hunting automation script.
- `pega_job_portal.py` — job intelligence portal script.
- `scan_workday_pega_openings.mjs` — official Workday-style career-site scanner.
- `scan_product_career_pages.mjs` — company career-page reachability probe.
- `build_portfolio_company_research.mjs` — 200-account portfolio company research builder.
- `README.md` / `AGENTS.md` — detailed project documentation and safety rules.

Inside `01_pega_career_intelligence\JobChange\JobChange\`:

- `app.py` — local JobChange career desk application entry point.
- `career_scraper.py` — core career scraper implementation.
- `job_runner.py` — scanner runner used for full refreshes.
- `portal_scan.py` — company/job portal scan support.
- `pega_job_hunter.py` / `pega_job_portal.py` — JobChange-local hunter/portal scripts.
- `Pega_Career_Intelligence_Hub.html`, `Pega_Deep_Dossiers.html`, `PegaSSA_FullPortal.html`, `Pega_Interview_Masterclass.html` — copied static portals.
- `templates\` and `static\` — local web UI assets.
- `data\`, `research\`, `reports\` — copied runtime state, research state and generated outputs.
- `test_*.py` / `test_*.cjs` — regression and UI test files.

## Common procedures

Run from this duplicate copy only if you intentionally want to operate on the duplicate state:

```powershell
cd C:\Users\DNSATHV\Desktop\calude\13_job_scraper_career_portals_upload_copy_20261113\01_pega_career_intelligence
node verify_pega_career_hub.mjs
```

For the JobChange app duplicate:

```powershell
cd C:\Users\DNSATHV\Desktop\calude\13_job_scraper_career_portals_upload_copy_20261113\01_pega_career_intelligence\JobChange\JobChange
python app.py --port 5050
```

Then open `http://127.0.0.1:5050`.

For tests, follow the copied project instructions in:

```text
01_pega_career_intelligence\AGENTS.md
01_pega_career_intelligence\JobChange\JobChange\AGENTS.md
01_pega_career_intelligence\JobChange\JobChange\README.md
```

## Important cautions

- This duplicate contains personal career material, HR/recruiter contact research, LinkedIn/profile research, saved job pipeline state, generated reports and local SQLite/JSON state. Keep it private; do not upload it to a public repository or shared public drive.
- The copy includes logs, caches and dependency folders because the request was for a complete duplicate. If a smaller source-only upload is needed later, create a separate reduced copy rather than deleting from this one.
- Search-index job evidence is not the same as a verified open official requisition. Treat saved scan data as research evidence, not guaranteed live openings.
- Do not bypass TLS verification, access-denial responses, LinkedIn rate limits or employer portal restrictions when running scanners.
- The source project has immutable backups and snapshots. Those were copied here; preserve them unchanged unless the owner explicitly requests otherwise.

## Directory Structure & File Index

```text
13_job_scraper_career_portals_upload_copy_20261113\
  README.md
  01_pega_career_intelligence\
    README.md
    AGENTS.md
    Pega_Career_Intelligence_Hub.html
    Pega_Deep_Dossiers.html
    pega_job_hunter.py
    pega_job_portal.py
    scan_workday_pega_openings.mjs
    scan_product_career_pages.mjs
    build_portfolio_company_research.mjs
    reports\
    node_modules\
    JobChange\
      JobChange\
        README.md
        AGENTS.md
        app.py
        career_scraper.py
        job_runner.py
        portal_scan.py
        pega_job_hunter.py
        pega_job_portal.py
        Pega_Career_Intelligence_Hub.html
        Pega_Deep_Dossiers.html
        PegaSSA_FullPortal.html
        Pega_Interview_Masterclass.html
        templates\
        static\
        data\
        research\
        reports\
        .deps\
        test_*.py / test_*.cjs
```

For the full granular index, use the copied `01_pega_career_intelligence\README.md` and `01_pega_career_intelligence\JobChange\JobChange\README.md`.

## Documentation status

Created 13 November 2026 for the duplicate upload-copy bundle. The bundle README records what was copied, where the main entry points are, how to run the duplicate, and the privacy/safety cautions for upload or handoff.
