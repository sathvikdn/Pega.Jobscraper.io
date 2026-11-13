# Pega Career Intelligence

## Purpose

This project contains the Pega career research, employer intelligence, team mapping, GCC feasibility scoring, HR contact validation, and job-hunting automation assets.

It is the main workspace for deciding which companies are realistic Pega opportunities, preserving evidence, ranking GCC employers, and maintaining the offline `Pega_Career_Intelligence_Hub.html` dashboard.

## Context

The folder was assembled from several related workstreams:

- Offline Pega career intelligence hub and backups.
- Full-directory audit data and verification scripts.
- GCC ranking/evidence bundle and handoff export.
- JobChange local job-hunting portal and supporting data.
- Team intelligence JSON ledgers and LinkedIn verification scripts.
- HR/recruiter PDF extraction and manual outreach queue.

The current hub is intended to work offline through `file://`.

The copy at `C:\Users\DNSATHV\Desktop\JobChange\JobChange\Pega_Career_Intelligence_Hub.html` is an old pre-reorganisation copy, byte-identical to `Pega_Career_Intelligence_Hub.backup-2026-09-22.html`. The file in this folder is the current hub.

The hub's main job is to explain the India Pega teams themselves: how each is structured, who the visible members are, what those members appear to work on, and what working there is like. The `#bengaluru-pega` section now comes first for Bengaluru-specific targeting, followed by the `#team-insider` section (refreshed 10 November 2026 for 12 key employers, now with member/work/outreach tables) and the job-listing refresh.

Latest live job refresh: **9 November 2026**. Both scanners were re-run and the tracked requisitions re-checked. The results are in the hub's `#live-refresh` section and in `reports\Pega_Career_Update_2026-11-09.md`.

## Technology stack

- HTML/CSS/JavaScript for the standalone career hub.
- Node.js ES modules for audit, evidence, export, and Puppeteer verification scripts.
- Puppeteer dependency under `node_modules` for browser-based verification.
- Python scripts for job-hunting, team intelligence enrichment, and data cleanup.
- JSON/CSV/Markdown data files for evidence, rankings, contacts, and handoff notes.

## Primary entry points

- `Pega_Career_Intelligence_Hub.html` — main offline career intelligence dashboard.
- `verify_pega_career_hub.mjs` — verification script for the hub.
- `bengaluru_pega_2026-11.json` + `build_bengaluru_pega_section.mjs` — Bengaluru-first Pega target map (counts, tiers, 22 team dossiers, skill lanes and application order) and its builder for the hub's `#bengaluru-pega` section.
- `build_bengaluru_top50.mjs` — **main Bengaluru builder.** Merges every Bengaluru ledger (deep dives, GCC profiles, Bengaluru map, team insider, enriched team ledger, Top-50 supplement) into `bengaluru_top50_2026-11.json`. It renders the hub's `#bengaluru-top50` section (50 companies, ~308 named people, ~244 with public LinkedIn profiles), writes `reports\Bengaluru_Pega_Top50_2026-11.md`, and merges the same data into `JobChange\Pega_Deep_Dossiers.html`.
- `bengaluru_outreach_blueprint_2026-11.json` + `build_bengaluru_outreach_blueprint.mjs` — outreach blueprint built on the Top 50: three architecture-fit tiers with friction points and talking points, nine persona × tier scripts (builder fails if any exceeds 125 words), a 5-point pre-outreach checklist applied to the top 15 targets, and a 7-day sprint. Renders the hub's `#outreach-blueprint` section (after the Top 50) and `reports\Bengaluru_Pega_Outreach_Blueprint_2026-11.md`. Run it after `build_bengaluru_top50.mjs`.
- `bengaluru_top50_supplement_2026-11.json` — fresh Nov 2026 lookups (people + workstreams) for Siemens, Ameriprise, Standard Chartered, John Deere, Morgan Stanley, Wells Fargo, VOIS, NatWest, Pegasystems, Booking and Sun Life.
- `bengaluru_team_deepdives_2026-11.json` + `build_bengaluru_team_deepdives.mjs` — in-depth dossiers for 10 priority Bengaluru teams (workstreams with evidence, how the team works, 66 named people with public LinkedIn profile URLs in contact order, connect plan, questions, watch-outs). Renders the hub's `#bengaluru-team-deepdives` section and `reports\Bengaluru_Pega_Team_Deepdives_2026-11.md`.
- `bengaluru_gcc_profiles_2026-11.json` + `build_bengaluru_gcc_profiles.mjs` — 63 per-employer Bengaluru Pega GCC profiles (team size, domains, architecture, key personnel with title/certification/tenure, hiring verdict, fit, sources) and their builder for the hub's `#bengaluru-gcc-profiles` section plus `reports\Bengaluru_Pega_GCC_Profiles_2026-11.md`.
- `team_insider_2026-11.json` + `build_team_insider_section.mjs` — team-insider ledger (structure, member work signals, outreach use, culture) and its builder for the hub's `#team-insider` section.
- `build_pega_full_audit.mjs` — embeds full audit records into the hub.
- `build_handoff_bundle.mjs` — builds GCC handoff bundle material.
- `JobChange\JobChange\app.py` — local JobChange Flask-style application entry point.
- `team_intelligence_enriched.json` — enriched team/person intelligence ledger.
- `gcc_ranking_scores.json` — current GCC ranking output.

## Common procedures

From this folder:

```powershell
node verify_pega_career_hub.mjs
```

For the JobChange app, use the instructions in:

```text
JobChange\JobChange\AGENTS.md
JobChange\JobChange\README.md
```

Typical workflow:

1. Update research/evidence JSON or source HTML.
2. Regenerate the affected hub/audit/ranking section.
3. Run `node verify_pega_career_hub.mjs`.
4. Review generated screenshots and handoff Markdown.

Bengaluru-first Pega map refresh:

1. Research and edit `bengaluru_pega_2026-11.json`, keeping per-team source links and preserving the caveat that search-index profile text is not live employment or vacancy verification.
2. Run `node build_bengaluru_pega_section.mjs`. It is idempotent: it replaces the section between the `BENGALURU_PEGA_SECTION_START/END` markers and adds the sidebar link once.
3. Run `node verify_pega_career_hub.mjs`.
4. Review the rendered `#bengaluru-pega` section through `file://`, especially the wide deep-dive table on mobile widths.

Bengaluru GCC profile refresh (one profile per employer):

1. Add or update entries in `bengaluru_gcc_profiles_2026-11.json` from public lookups only: site-restricted search results for public profiles, job descriptions, Pega.com/PegaWorld material and public posts. Record name, title, certification and tenure only; never contact details.
2. Run `node build_bengaluru_gcc_profiles.mjs` after `build_bengaluru_pega_section.mjs` (it inserts after the `BENGALURU_PEGA_SECTION_END` marker). It is idempotent, tiers profiles by the `fit` field (A/B/Benchmark/C) and rewrites `reports\Bengaluru_Pega_GCC_Profiles_2026-11.md`.
3. Run `node verify_pega_career_hub.mjs`.

Bengaluru Top 50 refresh (main Bengaluru view; supersedes the 10-team deep-dive section):

1. Add research to the source ledgers: hand-written deep dives in `bengaluru_team_deepdives_2026-11.json`, new lookups in `bengaluru_top50_supplement_2026-11.json` (keyed by lower-case company name), or the GCC profiles. Record work facts and public profile URLs only, never contact details.
2. Run the builders in order: `node build_bengaluru_pega_section.mjs`, `node build_bengaluru_gcc_profiles.mjs`, `node build_bengaluru_top50.mjs`. The Top-50 builder replaces the deep-dive section markers with `BENGALURU_TOP50_START/END`. Do not run `build_bengaluru_team_deepdives.mjs` afterwards; it would need those deep-dive markers again.
3. The dossiers merge always starts from `JobChange\Pega_Deep_Dossiers.pre-top50-2026-11-11.html`, so reruns are idempotent. Preserve that snapshot.
4. Run `node verify_pega_career_hub.mjs`. Open `JobChange\Pega_Deep_Dossiers.html` and open a company to check for console errors.

Bengaluru team deep-dive refresh (who does what, who to contact; now an input to the Top 50):

1. Edit `bengaluru_team_deepdives_2026-11.json`. Per person record only public work facts: name, title, certification, tenure, what they work on, public profile URL, contact priority (1 peer, 2 architect, 3 manager, 4 senior/TA). Never store emails or phone numbers.
2. Run `node build_bengaluru_team_deepdives.mjs` after `build_bengaluru_gcc_profiles.mjs` (it inserts after the `BENGALURU_GCC_PROFILES_END` marker and adds the sidebar link once).
3. Run `node verify_pega_career_hub.mjs`.

Team-insider refresh (structure, what they build, what it's like to work there):

1. Research and edit `team_insider_2026-11.json`, keeping the per-company `sources` and optional per-company `people` rows. Profile text is search-index evidence, not live LinkedIn verification.
2. Run `node build_team_insider_section.mjs`. It is idempotent: it replaces the section between the `TEAM_INSIDER_SECTION_START/END` markers and adds the sidebar link once.
3. Run `node verify_pega_career_hub.mjs`.

Live rescrape (as run on 9 November 2026):

```powershell
# 1. Back up the scanner state first (workspace.sqlite3, preloaded_search.json, career_scrape_log.json, job_history.json)
# 2. Full Career Desk scan: LinkedIn public search + employer career portals + India job boards (about 4 hours)
cd JobChange\JobChange
python -B job_runner.py --mode all --poll-seconds 15
# 3. Standalone hunter report (GCC/product pool, about 40 minutes); writes reports\pega_jobs_<date>.html
cd ..\..
python -B pega_job_hunter.py
```

- Run the two scanners one after the other, not together. Both use LinkedIn's public job API, which rate-limits (HTTP 429).
- `job_runner.py` exits with `outcome: interrupted` when any source was deferred. Completed results are still saved.
- The nightly Windows task `PegaCareerDeskNightlyScan` runs `JobChange\JobChange\nightly_scan.py` at midnight. It was repointed to this folder on 9 Nov 2026; before that it pointed at the pre-reorganisation path and had been failing since early October.

## Important cautions

- Keep `Pega_Career_Intelligence_Hub.backup-2026-09-22.html` unchanged.
- Several scripts may still contain old absolute paths from before folder organization.
- Search-index job evidence is not the same as a verified open official requisition.
- Historical team movement should not be treated as approved replacement hiring.
- Do not mass-email extracted HR contacts; use verified role IDs and official channels first.
- LinkedIn's public job API rate-limited both 9 Nov 2026 scan passes (HTTP 429), so most LinkedIn targets were deferred. Deferred means unknown, not "no openings". Do not bypass the limit; re-run later.
- The hub's `#live-refresh` section is the only part refreshed on 9 Nov 2026. Everything else is retained September–October research.

## Directory Structure & File Index

### Core hub files

- `Pega_Career_Intelligence_Hub.html` — main offline career intelligence dashboard.
- `Pega_Career_Intelligence_Hub.backup-2026-09-22.html` — immutable original backup; preserve unchanged.
- `Pega_Career_Intelligence_Hub.pre-audit-2026-09-22.html` — pre-audit checkpoint copy.
- `Pega_Career_Intelligence_Hub.pre-full-audit-2026-09-22.html` — immutable source snapshot used by `audit_pega_directory.mjs`.
- `Pega_Career_Intelligence_Hub.pre-gcc-ranking.html` — checkpoint before GCC ranking integration.
- `Pega_Career_Intelligence_Hub.pre-live-refresh-2026-11-09.html` — checkpoint taken just before the 9 Nov 2026 `#live-refresh` section was added; preserve unchanged.
- `Pega_Career_Intelligence_Hub.pre-team-insider-2026-11-10.html` — checkpoint taken just before the 10 Nov 2026 `#team-insider` section was added; preserve unchanged.

### Bengaluru Pega map

- `bengaluru_pega_2026-11.json` — Bengaluru-first target ledger: reality-check counts (159 maintained employer rows, 89 deep-dossier companies, 47 Bengaluru-evidence companies and 105 Bengaluru member rows), priority tiers, 22 deep-dive team dossiers, skill lanes and application order.
- `build_bengaluru_pega_section.mjs` — renders the ledger into the hub's `#bengaluru-pega` section (HTML-escaped, https-only source links) and adds the sidebar link.
- `bengaluru_gcc_profiles_2026-11.json` — 63 Bengaluru employer profiles (12 Tier A, 18 Tier B, 1 benchmark, 32 Tier C/negative), 145 named people. Grouped negative findings are kept to prevent re-researching dead ends. Search-index evidence, not live verification.
- `build_bengaluru_gcc_profiles.mjs` — renders the profiles into the hub's `#bengaluru-gcc-profiles` section and writes the Markdown export.
- `reports\Bengaluru_Pega_GCC_Profiles_2026-11.md` — generated Markdown export of all profiles in the Intelligence Hub profile format.
- `bengaluru_team_deepdives_2026-11.json` — 10 in-depth Bengaluru team dossiers (CBA, First Citizens, Empower, DTICI, Booking, JPMC, Nokia, Telstra, Broadridge, Cisco), 66 people (64 with public profile URLs). Contains personal names and work history from public pages; no contact details.
- `build_bengaluru_team_deepdives.mjs` — renders the dossiers into `#bengaluru-team-deepdives` and writes the playbook.
- `reports\Bengaluru_Pega_Team_Deepdives_2026-11.md` — generated outreach playbook (workstreams, contact order, questions).
- `bengaluru_top50_2026-11.json` — generated Top-50 dataset (do not hand-edit; edit the source ledgers and rebuild). Includes a `notInTop50` list of checked-and-excluded employers.
- `reports\Bengaluru_Pega_Top50_2026-11.md` — generated Markdown export of the Top 50.
- `JobChange\Pega_Deep_Dossiers.pre-top50-2026-11-11.html` — untouched snapshot of the dossiers dashboard taken before the Top-50 merge; the builder regenerates from it.
- `JobChange\Pega_Deep_Dossiers.html` — now 93 companies / 533+ people. Bengaluru Top-50 companies carry a "[Nov 2026 Bengaluru refresh]" project summary, refreshed highlights and Bengaluru contacts in the hiring playbook. Amadeus Labs, ING, Northern Trust and Tesco Bengaluru were added. The Flask app's own copy at `JobChange\JobChange\Pega_Deep_Dossiers.html` was not changed.

### Team insider (structure, work, culture)

- `team_insider_2026-11.json` — 12-company ledger (Pegasystems, CBA, Booking, Cisco, Ford Pega CoE, Citi, JPMorganChase, Wells Fargo, First Citizens India, VOIS, Sun Life, John Deere). Per company: team structure and named people, what the team builds, member/work/outreach rows, day-to-day culture, review ratings, watch-outs, fit for the candidate, and source links. Includes an at-a-glance comparison table.
- `build_team_insider_section.mjs` — renders the ledger into the hub's `#team-insider` section (HTML-escaped, https-only source links, optional `people` table, optional `dossier` field for a validated relative `.html` link) and adds the sidebar link.
- `JobChange\JobChange\CBA_ASB_Pega_Interview_Dossier.html` — CBA India / ASB Pega squad interview dossier (10 Nov 2026): org and squad structure, people, likely workstreams, reported interview process, JD-to-resume fit map, technical Q&A, design scenarios, values/STAR stories, questions to ask, pay bands and level risk, 48-hour prep plan, sources. Linked from the hub's CBA team-insider card.
- `JobChange\JobChange\CBA_Study_Pack\` — CBA/ASB study pack in the FCB house style: `index.html` and `ch01_cba_asb_architecture_blueprints.html` (architecture blueprint for a fictional NZ bank's Pega lending-care application on an event backbone, built by an India squad inside an NZ tribe), plus PDF renders. Linked from the dossier's navigation bar.
- `Pega_Career_Intelligence_Hub.audit-desktop.png` / `audit-mobile.png` — audit review screenshots.
- `Pega_Career_Intelligence_Hub.review-desktop.png` / `review-mobile.png` — visual review screenshots.

### Career hub verification and audit scripts

- `AGENTS.md` — project-specific rules for career hub verification and immutable backup handling.
- `audit_pega_directory.mjs` — extracts a directory inventory from the immutable pre-full-audit HTML snapshot.
- `build_pega_full_audit.mjs` — embeds the full audit ledger into the current hub and regenerates mapped/unmapped sections.
- `verify_pega_career_hub.mjs` — Puppeteer verification for search, navigation, responsive layout, backup hash, contact coverage, and audit readability.
- `pega_directory_inventory.json` — generated inventory from the pre-full-audit snapshot.
- `pega_full_audit.json` — researched directory audit ledger.
- `v3.txt` — captured verification pass output.

### GCC ranking and handoff bundle

- `build_gcc_ranking_section.mjs` — injects/updates GCC ranking content in the hub.
- `gcc_build_evidence.mjs` — builds the evidence base from hub/audit/team data.
- `gcc_explain_company.mjs` — explains company scoring inputs.
- `gcc_rank_feasibility.mjs` — feasibility/ranking calculation script.
- `gcc_score_rubric.mjs` — scoring rubric implementation.
- `build_handoff_bundle.mjs` — generates Markdown handoff deliverables.
- `verify_export_selfcontained.mjs` — validates the self-contained export bundle.
- `gcc_evidence_base.json` — core GCC evidence records.
- `gcc_evidence_supplement.json` — supplementary GCC evidence.
- `gcc_lifestyle_supplement.json` — lifestyle/context supplement used by ranking.
- `gcc_ranking_scores.json` — generated ranking score output.
- `_baseline_ranking.json` — baseline scores for comparison.
- `_check_flagfix.mjs` / `_probe_lsa_gap.mjs` — focused ranking/LSA audit probes.
- `PEGA_GCC_HANDOFF_BRIEF.md` — concise handoff brief.
- `PEGA_GCC_HANDOFF_BUNDLE.md` — full handoff bundle.
- `PEGA_GCC_HANDOFF_EXPORT\` — packaged handoff export copy with scripts, data, hub HTML, and README.

### Job hunting and team intelligence

- `JobChange\` — migrated JobChange workspace; contains app, backups, reports, templates, static assets, research, and tests.
- `JobChange\JobChange\AGENTS.md` — verification and safety rules for the JobChange application.
- `JobChange\JobChange\README.md` — JobChange application documentation.
- `pega_job_hunter.py` — standalone job-hunting automation script.
- `pega_job_portal.py` — portal script for job intelligence display.
- `pega_job_hunter.log` — captured job-hunter runtime log.
- `setup_daily_scan.bat` — Windows Task Scheduler setup helper for daily job scan.
- `job_history.json` — historical job-scan data.
- `JobChange.so` / `deviceChange.zip` — archived packaged copies of JobChange-related material.
- `reports\` — generated job report output:
  - `pega_jobs_2026-08-30.html`, `pega_jobs_2026-10-04.html`, `pega_jobs_2026-11-09.html` — dated hunter reports.
  - `_hunter_run_20261109.txt` — console log of the 9 Nov 2026 hunter run.
  - `Pega_Career_Update_2026-11-09.md` — 9 Nov 2026 live-refresh summary: current-file status, verified live roles, tracked-lead outcomes, scanner coverage limits and fixes.
  - `workday_pega_openings_2026-11-12.json` — output of `scan_workday_pega_openings.mjs`: India Pega postings (title, location, req ID, start/end dates, description excerpt) from 44 attempted official Workday site configurations (34 responded; 10 were inaccessible), with board size or error status. A zero on one Workday feed does not cover other career portals: Citi's own site separately showed a Chennai Pega role on 12 Nov.
  - `bengaluru_join_timing_2026-11.json` — corrected output of `analyze_bengaluru_join_timing.mjs`: dated Pega-role starts versus unverified team-associated starts from Nov 2025 onward, with excluded promotion, vendor, alumni, offsite and adjacent contacts. These are public-profile claims, not verified hires or a hiring calendar.
  - `portfolio_company_research_20261113.json`, `Portfolio_Company_Research_20261113.md`, `Portfolio_Company_Research_20261113.html` — 13 Nov complete portfolio deep-research outputs for 200 candidate product/GCC accounts. They include official/current role signals, team/workstream understanding, fresh priority-employer research, Pega stack/version clues, profile/movement caveats, verification questions and action guidance. The report now distinguishes CBA/Pegasystems Bengaluru targets from Citi/Lloyds India-but-not-Bengaluru roles and from watchlist-only signals.
- `build_product_200_watchlist.mjs` — merges duplicate employers from the 191 GCC-labelled catalogue rows, other enterprise candidates and the external Top 50 into 200 distinct product/GCC watch accounts. Combines the dated Workday snapshot, targeted first-party checks, career-page reachability and historical leads into the standalone HTML watch page, JSON ledger and the hub's `#product-200-watch` section. Run **after** the join-date report and all input scans. Rerunning replaces only the generated watch page/section; it never alters the immutable backups.
- `build_portfolio_company_research.mjs` — portfolio-level deep-research builder added 13 Nov 2026 and expanded the same day. It reconciles the current hub, `JobChange\Pega_Deep_Dossiers.html`, Top-50 people/workstreams, corrected join-timing audit, latest `workday_pega_openings_*.json`, targeted official checks and manual first-party/web/profile findings into `reports\portfolio_company_research_YYYYMMDD.json`, `reports\Portfolio_Company_Research_YYYYMMDD.md`, `reports\Portfolio_Company_Research_YYYYMMDD.html`, and the hub's `#complete-portfolio-research` section. Each generated company row carries current-opening conclusion, team/architecture understanding, stack/version evidence and verification questions; unsupported roles remain `unknown`, not `no opening`. It keeps the old `Desktop\JobChange\JobChange` movement radar as historical evidence only.
- `scan_product_career_pages.mjs` — GET-only reachability probe for mapped career URLs without a supported job-search feed; writes `reports\product_200_portal_probes_2026-11-12.json`. It does not infer vacancy status from a reachable homepage; respects 403/429 instead of bypassing.
- `verify_product_extra_roles.mjs` — first-party role checks for Pega GenAI Engineering (24123), ANZ's Pega search and Cohere Health's Greenhouse board; writes `reports\product_200_extra_official_checks_2026-11-12.json`.
- `test_build_product_200_watchlist.mjs` — regression tests for 200 unique accounts, ASB role attribution, unverified leads, and idempotent hub rendering. Run `node --test test_build_product_200_watchlist.mjs`.
- `reports\product_200_openings_watch_2026-11-12.json` / `reports\Product_200_Pega_Opportunity_Watch_2026-11-12.html` — machine-readable evidence tiers and a standalone searchable offline copy of all 200 watch accounts.
- `reports\product_200_new_team_evidence_2026-11-12.json` — manually curated seven-employer new-team evidence with source URLs, contradictions and next checks; the builder renders it above the 200-row table.
- `reports\Product_200_Research_Summary_2026-11-12.md` — current openings, 200-account coverage/limitations, new-team judgments and direct first-party job links. **These are candidates, not 200 proven Pega teams:** 159 accounts lack a supported vacancy search; use `unknown`, not `no openings`.
- `analyze_bengaluru_join_timing.mjs` — classifies explicit "since Mon YYYY" entries in `bengaluru_top50_2026-11.json` without treating promotions or former/non-Bengaluru contacts as Pega hires. Run `node analyze_bengaluru_join_timing.mjs`. Absence of a dated record does not mean no hiring.
- `test_analyze_bengaluru_join_timing.mjs` — regression tests for First Citizens promotion/US-leader exclusions, Booking starts, CBA recruiter and vendor/non-Bengaluru profiles. Run `node --test test_analyze_bengaluru_join_timing.mjs`.
- `scan_workday_pega_openings.mjs` — queries employers' official Workday career-site job feeds (no LinkedIn, so no rate limit) for "Pega"/"Pegasystems", keeps India postings whose description really mentions Pega (excludes the "Cadence Pegasus" chip tool), and writes a dated JSON in `reports\`. On the corporate network run it as `node --use-system-ca scan_workday_pega_openings.mjs` with `NODE_USE_ENV_PROXY=1` and `HTTPS_PROXY` set to the system proxy; plain `node` fails with "fetch failed" because of TLS inspection. Sites marked "unreachable (HTTP 422/404)" have an unknown or wrong career-site name and were **not** checked; a board size under ~50 can also mean a partial site.
- `JobChange\JobChange\_backup_before_rescrape_20261109-pre-rescrape\` — pre-rescrape copies of `workspace.sqlite3`, `preloaded_search.json`, `career_scrape_log.json` and the root `job_history.json`; preserve unchanged.
- `JobChange\JobChange\_logs\rescrape-20261109.log` / `rescrape-20261109-pass2.log` — JSON progress logs of the 9 Nov 2026 scanner runs. Pass 2 was stopped after its LinkedIn phase.
- `JobChange\JobChange\nightly_task.xml` — Task Scheduler definition for the nightly scan; path updated to this folder on 9 Nov 2026.

### Team/person intelligence data and cleanup scripts

- `team_intelligence.json` — base company/team intelligence ledger.
- `team_intelligence_enriched.json` — enriched team intelligence data used by hub/ranking scripts.
- `build_deep_dossiers.py` — builds detailed Pega team/person dossiers.
- `Pega_Deep_Dossiers.html` — generated dossier report.
- `team_health_analysis.py` — scores company/team health using departures, hires, certification depth, size, tenure, and contractor signals.
- `add_linkedin_links.py` — generates LinkedIn search links for team members missing direct links.
- `apply_verification.py` — applies verified profile URLs and departed-person corrections.
- `bulk_import_members.py` — imports researched team members into the intelligence ledger.
- `clean_members.py` — removes members without Pega-keyword evidence.
- `final_cleanup.py` — final cleanup/removal of zero-signal or vendor-only companies.
- `org_sort_members.py` — sorts members by role hierarchy and assigns role-level tags.
- `verify_members.py` — checks member records for Pega evidence keywords.

### Date/contact/HR outreach analysis

- `aggregate_dates.mjs` / `extract_dates.mjs` — extract and aggregate date references from the hub.
- `company_month_patterns.mjs` / `company_month_patterns.json` — company/month pattern mining output.
- `dates_extracted.json` / `date_histograms.json` — extracted date and histogram data.
- `analyze_hr_pdfs.mjs` — analyzes downloaded HR/contact PDF text extracts.
- `extract_target_hr_contacts.mjs` — extracts target HR contacts into JSON.
- `mine_hidden_profile_insights.mjs` — mines hidden profile/context signals from the hub.
- `prepare_linkedin_outreach.mjs` — generates LinkedIn manual outreach queue and profile CSV.
- `hr_pdf_analysis.json` — HR PDF analysis output.
- `target_hr_contacts.json` — extracted target HR/contact list.
- `hidden_profile_insights.json` — mined hidden profile/context insights.
- `linkedin_profiles.csv` — LinkedIn profile export/list.
- `linkedin_manual_outreach_queue.html` — manual outreach review queue.
- `verified_hr_pega_outreach_notes.md` — cautionary notes from HR/recruiter verification.
- `500+ Companies Hiring Career Links List_extracted.txt` — extracted career-link reference list.
- `New UPDATED 2026 Company Wise 3,000+ HR contact-1_extracted.txt` / `-2_extracted.txt` — extracted source contact lists; not trusted without verification.

### Dependencies and package files

- `package.json` / `package-lock.json` — Node dependency metadata, primarily Puppeteer.
- `node_modules\` — installed Node dependencies used by verification scripts.

## Documentation status

High-level and granular project indexing are now included. Very large dependency/vendor folders are summarized rather than listed file-by-file.

Last updated 9 November 2026 for the live rescrape: new report, hub checkpoint, scanner backup, scheduled-task path fix and rescrape procedure.

Updated 10 November 2026: team-insider ledger, builder, hub section and checkpoint; later refreshed the team-insider ledger with explicit member/work/outreach tables for all 12 priority employers and added a Bengaluru-first Pega map with 22 priority team dossiers, followed by 63 per-employer Bengaluru Pega GCC profiles with a Markdown export. Updated 11 November 2026: added in-depth dossiers for 10 priority Bengaluru teams with 66 named contacts and an outreach playbook, then expanded them into the Bengaluru Top 50 (hub section, Markdown and Deep Dossiers merge), and added the outreach blueprint (tiers, scripts, checklist, 7-day sprint). Updated 12 November 2026: added `scan_workday_pega_openings.mjs` and its first output for a new-team/openings sweep; corrected the Top 50 timing report and its regression tests, relabelled the older hub chart as historical profile-date evidence, and added the 200-account opportunity watch with coverage/probe/first-party evidence and a searchable hub section. Updated 13 November 2026: added and then expanded `build_portfolio_company_research.mjs`, refreshed the official Workday-style Pega scan, rechecked Pegasystems/ANZ/Cohere, reconciled the old movement radar and Deep Dossiers into a complete 200-account portfolio report, added priority-company deep research across official openings, architecture, stack/version clues and verification questions, identified Lloyds Hyderabad as an official India-but-not-Bengaluru Pega role, and updated the hub's `#complete-portfolio-research` section.
