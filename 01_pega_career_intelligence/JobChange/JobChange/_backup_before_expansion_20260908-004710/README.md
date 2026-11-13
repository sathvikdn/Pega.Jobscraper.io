# Sathvik's Career desk

Local Pega career research and application planning workspace. Research checked on 7 September 2026.

## Open the portal

Double-click **START_CAREER_DESK.cmd** and open **http://127.0.0.1:5050**. Keep the terminal running. Alternatively, in PowerShell run `./Start-CareerDesk.ps1` from this folder. The existing command `python pega_job_portal.py` also starts this version. Use `./Start-CareerDesk.ps1 -Port 5051` if another program occupies port 5050.

Dependencies are included in `.deps` on this computer. On a fresh copy, install Python 3.10+ and run `./Setup-CareerDesk.ps1`. The scripts use the bundled Codex Python when available, otherwise the installed Python. No Windows execution-policy changes are needed by the app; if script execution is restricted, use `python app.py` after installing requirements.

## What is included

- **Opportunities:** 15 distinct requisitions from source-linked research, eight including Bengaluru. Thirteen employer pages had application controls when researched; two leads were visible only in search indexes. Experience requirements, project overlap and gaps are separate from availability. Employer type distinguishes GCC/in-house, product, and services companies. Multiple similar titles retain distinct requisition IDs.
- **Bengaluru teams:** 16 researched companies, including 12 with confirmed or supporting local Pega evidence. Eight public professional profile claims are linked where relevant. A profile or expired hiring page can establish a team lead, but cannot establish a current opening or guarantee current employment.
- **Compensation:** 11 evidence records with pay basis, experience, dates and limitations. Your actual MBRDI and TCS documents supply the baseline. The calculator separates fixed, performance, city allowance, employer contributions/insurance and one-time bonus. It is not a take-home or tax calculator.
- **Pipeline:** stage and notes saved locally; CSV export.
- **Discovery tools:** small company scans with saved candidates and per-source diagnostics. Results from aggregators are unverified until an exact employer requisition is checked. Public sites can block automation; an empty or failed response never proves there are no jobs.
- **Preparation:** existing resume and interview guides are preserved. Older dossiers and guides remain explicitly historical/unverified where appropriate.

## Research rules

`research/openings.json`, `teams.json`, and `salaries.json` are the reviewable source records. Openings need a specific role URL, employer, location, experience requirements, observation date and evidence. Search snippets are labeled `indexed_only`. Known passed deadlines override an open claim. Automated rechecks retain separate evidence; inaccessible or ambiguous pages become uncertain, and identity-changing redirects require manual review. A successful HTTP fetch is not itself proof that hiring continues.

Salary research does not turn a CTC range into a fixed salary claim. The 24–27 LPA CTC target is a plausible stretch, especially near 24–25 LPA, based on adjacent advertised roles. The researched data does not establish 22–24 LPA fixed as typical for four years of experience. Undisclosed employer pay is left undisclosed.

The original 89-company data is available as a historical import. Synthetic health scores, guessed salary bands and inferred employee departures are excluded from current decisions. The scanner's 301 targets include regional variants and broad searches; they are not 301 distinct employers.

## Storage and maintenance

`data/workspace.sqlite3` stores your pipeline, verification results, discovery scans and last task status. Back up the `data` folder with the portal stopped. Research files are versionable separately from private notes. The server binds only to `127.0.0.1`; no external account or application submission is connected.

Scanner fixes include TLS certificate verification, token-boundary employer matching (Citi does not match First Citizens), canonical job URLs, persistent results, escaped report text and honest source diagnostics. Generic Google search remains a manual search link because its snippets do not reliably establish the hiring employer. Some HTTP-200 blocking or unsupported listing pages can still resemble an empty result, so empty scans are inconclusive. V2 uses a new stable identifier format; an old V1 history-only hash cannot always be migrated without its original URL, so the first V2 scan may label an old job newly seen. This means first seen by this scanner, not newly posted.

`legacy/pega_job_portal_v1.py` preserves the earlier portal source. Existing personal documents are not rewritten. To test: `python test_portal.py`. Python must have access to the local `.deps` packages.

No outreach, job application, recruiter message, or public publication is performed by the portal.
