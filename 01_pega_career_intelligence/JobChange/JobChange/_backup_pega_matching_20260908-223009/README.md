# Sathvik's Career desk

Private local career workspace. Goal: **₹35 LPA total CTC**. Broader search floor: **₹20 LPA+**. Independent investigation: 8 September 2026.

## Open

Run **START_CAREER_DESK.cmd** and open **http://127.0.0.1:5050**. Keep its terminal running. The server binds only to localhost. Python 3.10+ and the dependencies in requirements.txt are required; Setup-CareerDesk.ps1 installs them into .venv. Existing bundled dependencies are in .deps.

## Fresh evidence is the default

**Companies & people** reads research/independent_map.json. It currently contains 89 independently sourced employer records, 121 professional identities (76 distinct LinkedIn profiles), 200 evidence URLs and 170 search/check log records. There are 39 documented Bengaluru connections, not 39 proven local teams. Current headcount stays unknown. Company, professional, hiring and method views support search, location/category filters and comparisons of up to three employers. The priority brief links strong qualification leads and open questions.

**Opportunities** defaults to fresh evidence. It merges independently collected public jobs, source-linked employer requisitions and newly searched independent companies. Fresh facts replace older duplicate facts while retaining stable IDs, pipeline notes and archived evidence. Unknown salary remains unknown even when an older duplicate had an unsupported amount. Pega, workflow/BPM, integration and automation stay in scope. Domain mismatches are excluded by default. India-remote eligibility requires explicit evidence; foreign remote jobs are not automatically India eligible.

**Earlier research** remains available through the directory archive, Earlier team briefs and the opportunity evidence filter. The historical catalogue has 313 company/region targets, including country variants and five broad regional searches. Its 89 old dossiers and 403 stored profiles are historical inputs, separate from the newly discovered 89 employer records. They did not supply evidence for the new investigation.

**Compensation** keeps the documented MBRDI and TCS baseline and separates fixed pay, performance-linked pay, benefits and bonuses. Published annual INR total CTC, overlapping ranges, foreign amounts, unknown pay basis and undisclosed pay remain distinct. No fresh public-card result establishes an INR salary. The calculator is not a take-home or tax calculation.

## Search and refresh

The main search button targets the independent employer map. Category buttons select fresh GCC/in-house, consulting/services or international employers. A company's evidence dialog can search that exact employer. Earlier-catalogue searches are an explicit archive action. Resume preserves the chosen catalogue, company and category.

Public LinkedIn queries use exact employer matching. Broader role terms and Pega fallbacks remain bounded searches, not enumeration of every vacancy. Job descriptions are checked for requirements, relevance, salaries and remote restrictions. Explicit seniority and mandatory CLSA requirements produce experience/certification gaps rather than false matches.

Fresh description refreshes operate only on selected targets and prioritize selected copies over old cached duplicates. Saved results from other targets are retained. Progress saves after each company and description. Pause/resume, blocked/error outcomes, missing text and unresolved employer identity remain visible. A completed query or readable page does not guarantee an actively funded vacancy.

The first independent public-card investigation used eight skill/location combinations and 24 result pages, yielding 56 distinct roles from 30 employers. It checked 45 descriptions and read 44. Its audited snapshot has 32 possible and 24 stretch roles, including 11 outside India. This fixed snapshot is separate from later live campaign results.

## Source files and reproducibility

- fresh_people.json, fresh_ecosystem.json and fresh_consulting.json preserve new professional, customer/event, partner and hiring evidence.
- fresh_public_jobs.json preserves the independent skill/location job discovery and audit.
- investigation_data.py builds independent_map.json from only those four fresh files. It does not import the old catalogue as evidence.
- ecosystem_discovery.py performs bounded public job-card discovery without employer-name seeds. It stops on rate limiting and reports partial work.
- independent_research_brief.md and static/investigation-brief.html explain priorities and qualifications.
- preloaded_search.json holds live campaign results and checkpoints.
- directory.json, openings.json, expanded_openings.json, team_depth_*.json and the original references retain earlier research.

Public professional access is marked page or search_index. An indexed profile can be stale. Source observations, conflicts and field provenance remain preserved. Historical projects are not reassigned to someone's present employer. Event speakers do not prove local teams. Employee moves or welcome posts do not establish replacement vacancies. Profile counts do not establish headcount, retention or salary.

To rebuild the map after reviewing new sources: python investigation_data.py. Running ecosystem_discovery.py performs a new network investigation; do not use it merely to rebuild existing evidence.

## Storage and validation

data/workspace.sqlite3 holds private notes, pipeline stages, verification results and preferences. Back up with the portal stopped. The installer preserves an existing live preloaded_search.json and refuses to replace code during an active search. Personal documents and job history remain intact.

Windows checkpoint reads and atomic writes are coordinated. Unique temporary files and bounded sharing-error retries prevent the previous WinError 5 collision. Persistent replacement failures retain a complete recovery copy and cancel queued network work.

Backend checks: python -B -m unittest test_portal test_scanner test_directory test_expanded_portal test_team_depth test_campaign test_checkpoint test_investigation test_investigation_api test_experience_audit

UI checks: node test_ui.cjs and node test_ui_investigation.cjs. These use a DOM behavior harness, including every real fresh research record; they are not a real-browser visual inspection.

No outreach, applications, recruiter messages or public publication are performed.

Final installed refresh: all89 independent employers checked,27 with query results,79 of79 selected descriptions read,zero errors. The live snapshot has127 fresh posting/evidence records; availability, location and qualification filters still apply.
