# Sathvik's Career desk

Private local career research workspace. Package goal: **₹35 LPA total CTC**. Broader discovery floor: **₹20 LPA+**. Last expansion: 8 September 2026.

## Open

Double-click **START_CAREER_DESK.cmd**, then open **http://127.0.0.1:5050**. Keep its terminal running. PowerShell alternative: `./Start-CareerDesk.ps1`. The original `python pega_job_portal.py` entry point also opens this version. The server binds only to localhost.

Dependencies already exist in `.deps` on this computer. A fresh copy requires Python 3.10+ and `./Setup-CareerDesk.ps1`. The launch scripts can use the bundled Codex Python. Personal PDF, Word and original HTML reference documents remain available.

## What the portal does

- **Opportunities:** merges reviewed requisitions, additional Pega/adjacent roles and persisted public discovery results. Pega, workflow/BPM, integration, automation and application-engineering leads remain searchable. Domain mismatches are excluded by default but can be inspected.
- **Complete directory:** 313 company and regional targets: 120 GCC/in-house, 58 services/consulting and 135 remote/international. These include country variants and five broad regional searches; this is not a count of unique employers. All 89 original dossiers and 403 saved professional profiles remain searchable. Team-size estimates, profile dates and geography retain their original provenance.
- **Team comparisons:** source-linked briefs cover documented projects, technologies, ownership evidence, learning opportunities, Bengaluru scope and questions for hiring managers. Compare up to three teams. Public PegaWorld/PegaFest and professional-post evidence is saved alongside employer information. Assessments do not establish salary, team culture or a vacancy.
- **Compensation:** your MBRDI and TCS documents supply the baseline. The goal is ₹35 LPA total CTC, while ₹20 LPA remains the initial search floor. Published annual INR CTC, overlapping ranges, fixed/basis-unknown pay, foreign currency and undisclosed pay remain separate. Unknown pay stays searchable. The calculator separates fixed, performance, allowance, employer contributions and joining bonuses; it is not a take-home or tax calculation.
- **Pipeline:** stage and notes saved in local SQLite, preserved across refreshes and restarts; CSV export includes salary basis and remote eligibility.
- **Preparation:** existing resume and interview references are retained, with historical or illustrative claims labelled.

## Search all / refresh

**Search all** covers the complete directory. Category buttons cover GCCs, consultancies or remote/international targets. The salary floor filters evidence; it does not invent compensation for listings without a published budget.

Public LinkedIn queries use exact employer matching, with broader role terms and a Pega fallback. A bounded result page per query cannot enumerate every opening. Individual job pages are then checked for experience, relevance, compensation and remote restrictions. Returned cards remain discovery candidates until exact employer availability is established. Five broad regional targets retain their real returned employers.

The portal saves progress after each target and each distinct job description, displays blocked/error/no-match outcomes, and supports pause/resume. OS file locking prevents overlapping writers; an interrupted process is shown as resumable. A refresh retains prior jobs not rediscovered, marks them for checking and preserves pipeline state.

**No query matches** means no matches from that query, not proof that an employer has no openings. A successful HTTP request is not proof of a current vacancy. Undisclosed pay is not proof of a ₹20L or ₹35L budget. An overseas remote vacancy is not automatically available from India.

## Research and provenance

`research/directory.json` preserves the full legacy directory and source mappings. `preloaded_search.json` records query coverage, diagnostics, role candidates and job-description checks. `openings.json` and `expanded_openings.json` contain individually researched requisitions. `team_depth_*.json` and `community_events.json` contain new team/event briefs. `teams.json` preserves the earlier16-team verification overlay.

Historical profile counts are saved research, not current employee counts. Office presence, event attendance and a global customer case study do not by themselves establish a Bengaluru delivery team. Synthetic health scores, guessed salaries and inferred departures are not used for current comparisons.

## Storage and checks

`data/workspace.sqlite3` stores private pipeline notes, verification results, search preferences and task status. Back up the data folder with the portal stopped. The installer copies reviewed code/research, backs up replaced files and verifies hashes; it does not overwrite private application state or job history.

Python checks: `python -B -m unittest test_portal test_scanner test_directory test_expanded_portal test_team_depth test_campaign test_checkpoint`.
Interface behavior checks: `node test_ui.cjs` (local DOM harness; not a real-browser visual test).
Original availability checks, expiry handling, exact employer/URL identity, pay basis, region restrictions, pause/resume, data retention and complete coverage have targeted regressions.

No outreach, application submission, recruiter message or public publication is performed.

Windows checkpoint saving coordinates dashboard readers with atomic replacement, retries transient file-sharing failures for a bounded period, and preserves a distinct recovery copy if replacement remains blocked. A failed checkpoint cancels queued network work. The hotfix was verified against a real held Windows read handle and concurrent live dashboard polling.
