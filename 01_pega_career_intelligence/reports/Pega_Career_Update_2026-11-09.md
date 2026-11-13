# Pega Career Update · 9 November 2026

Live rescrape plus a status check of every role lead the Career Intelligence Hub was tracking. The same content is in the
hub's `#live-refresh` section. Everything else in the hub is retained research from September–October 2026.

## 1. Which file is current

| File | State |
| --- | --- |
| `C:\Users\DNSATHV\Desktop\JobChange\JobChange\Pega_Career_Intelligence_Hub.html` | **Stale.** Byte-identical (SHA-256 `1A666C6F…89CC`) to `Pega_Career_Intelligence_Hub.backup-2026-09-22.html`, the original from early September. Not modified. |
| `C:\Users\DNSATHV\Desktop\calude\01_pega_career_intelligence\Pega_Career_Intelligence_Hub.html` | **Current.** About 1 MB, 89+ searchable tables, 329 audit records, 159 employer rows, GCC ranking, plus the 9 Nov live-refresh section. |
| `...\JobChange\JobChange\` (inside `01_pega_career_intelligence`) | **Current** Career Desk app, database and study packs. The Desktop `JobChange` folder is an older copy. |

## 2. What was run today

- `JobChange\JobChange\job_runner.py --mode all`: 408 targets. Covers LinkedIn public search, 377 employer career portals (Playwright) and the India job boards.
- `pega_job_hunter.py` (GCC/product pool, 108 employers) produced `reports\pega_jobs_2026-11-09.html`: 34 rows, about 20 unique roles.
- Manual checks on official career pages and public postings for every tracked requisition.

**Coverage limits**

- LinkedIn's public job API returned **HTTP 429 (rate limited)** after roughly 170–225 requests in both passes, so 329–357 of 408 targets were *deferred*. Deferred means unknown, not "no openings". The scanner correctly did not try to bypass the limit.
- Career portals: 26 of 345 attempted pages returned Pega listings. 117 failed to load and 145 had no usable search box.
- The second pass was stopped after its LinkedIn phase because its portal phase would only repeat today's first pass.

## 3. Act now: roles checked live on 9 November

| # | Employer · role | Location | Posting asks | Evidence | Fit / action |
| --- | --- | --- | --- | --- | --- |
| 1 | **Pegasystems · Software Engineer, GenAI Engineering (Pega Developer CSA, CSSA)** | Bengaluru | 2–4 yrs Pega, CSA + CSSA, SQL, Java/J2EE a plus; builds Pega's GenAI agents/assistant, evaluations, guardrails | LinkedIn 4484663558, about 5 days old, 74 applicants | **Best band fit.** Apply this week. |
| 2 | **Commonwealth Bank · Senior Software Engineer – Pega Development (REQ266822)** | Bengaluru, Manyata | 5+ yrs, CSSA, case management, integrations, CI/CD; Pega Cloud / Constellation / KYC-CLM / Smart Disputes / CS preferred | LinkedIn 4479519256 / 4479526073, posted 5–8 Nov, **ad ends 19 Nov 2026**, 153 applicants | Stretch (about 4 vs 5+ yrs). Your #1 strategic employer. Get a referral before 19 Nov. |
| 3 | **Citi · Pega Application Developer (req 261005347)** | Chennai, hybrid | 4–6 yrs dev, 5+ yrs FS, CSA+, Pega 24.x/25.x, **mandatory delinquency management (cards/loans)**, Docker/K8s, Oracle/MongoDB | Official Citi Careers page, posted 6 Nov 2026; LinkedIn 4487302906, 90 applicants | Stretch, but the collections domain is a direct match. Gaps: containers, 24.x. |
| 4 | First Citizens India · SE I / SE II – Pega Developer (Deposits & Shared Services) | Bengaluru | SE I 3+ yrs; SE II 5+ yrs, CSA, Pega GenAI | LinkedIn 4449009855 last seen 4 Oct; mirrors list SE II valid until 3 Dec 2026 | Matches your FCB/FCI study pack. Check status on Workday. |
| 5 | Citi · PEGA Developer (req 26968715) | Pune | 4+ yrs, CSSA pref., Pega 8.x, REST/SOAP/Kafka | Official URL still 404; aggregator copies persist | Unchanged: verify by requisition ID first. |
| 6 | Pegasystems · Senior Applications Engineer (5–6 yrs) / System Architect (no band) | Hyderabad | — | 4465964866 (177 applicants) / 4482295831 (62) | Secondary, only if Hyderabad is acceptable. |

## 4. Status of the 30 September leads

| Lead | 9 Nov finding | Decision |
| --- | --- | --- |
| Optum 2385172 (Hyderabad) | Official 404; Built In marks it removed 21 Sep 2026; sibling 2385232 removed 23 Sep | Closed |
| Citi Java Pega Developer 26985252 (Chennai) | Workday index entry dated 4 Sep 2026; page needs JavaScript | Verify; below 261005347 |
| Commonwealth Bank | Live REQ266822, closes 19 Nov | Upgraded to act now |
| Booking Holdings | Only a third-party staffing post (TeamPlus, Jul 2026, Booking.com client site) | Contractor route only |
| Cisco / John Deere | No Pega requisition found; LinkedIn coverage deferred | Unknown, re-run later |
| Wells Fargo India | Earlier Hyderabad Pega listings removed or ended | Monitor |

## 5. Other India postings (review only)

BNP Paribas Pega Technical Architect (Chennai, 30 Oct) · Credera Pega CSSA Developer – Constellation (Bengaluru, 3 Nov, 6+) ·
Deloitte Applied AI Platform Engineer (PEGA) SSE II / Lead (Bengaluru, 6+ / 10+) · Infosys Pega Consultant family (Bengaluru,
21–23 Oct) · Accenture Custom Software Engineer, Pega Platform (Bengaluru, 3+, services) · JPMorganChase SE III – Pega
(Hyderabad, third-party mirror) · LTM Pega CSSA + Constellation / Customer Service (multi-city, 4+ to 5–8).

## 6. Career Desk scanner state after the refresh

- `/api/opportunities` policy counts: 33 recommended, 65 stretch, 354 review, 113 excluded. These are the scanner's experience/evidence gates, not hiring probabilities.
- Many "recommended" rows are services firms (Accenture) or overseas roles kept from September; filter to India GCC/product employers when reading the portal.
- Pre-rescrape data is preserved in `JobChange\JobChange\_backup_before_rescrape_20261109-pre-rescrape\` (`workspace.sqlite3`, `preloaded_search.json`, `career_scrape_log.json`, root `job_history.json`).

## 7. Fixes made during the refresh

- The Windows scheduled task `PegaCareerDeskNightlyScan` still pointed at the pre-reorganisation path `Desktop\calude\JobChange\JobChange\nightly_scan.py`. Last result code 2 (file not found), with no nightly logs after 3 Oct. It now points at `01_pega_career_intelligence\JobChange\JobChange\nightly_scan.py`, and `nightly_task.xml` was updated to match.

## 8. Recommended next steps

1. Pegasystems GenAI Engineering (Bengaluru): apply or ask for a referral now.
2. CBA REQ266822: secure a referral and apply **before 19 Nov 2026**.
3. Citi 261005347 (Chennai): apply if Chennai is acceptable; lead with collections and delinquency work.
4. First Citizens India: confirm the status of your SE I/II application or requisition.
5. Re-run `python -B job_runner.py --mode all` from `JobChange\JobChange` in a day or two, alone. LinkedIn is rate limiting this IP, so do not run the hunter at the same time.
