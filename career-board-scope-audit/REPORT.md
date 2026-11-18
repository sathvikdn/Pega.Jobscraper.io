# India and subsidiary career-board audit

16 November 2026 · New scanner in `C:\Users\sathv\Desktop\job hunter\pega-radar`

## What was checked

Inventory review covered **247 registry entries**, including **180 product/GCC entries**. Public-page discovery was attempted for **197 entries**, including **all 180 product/GCC entries**; remaining entries without career URLs are listed below. The scan compared official page/job/apply links with configured boards, then probed newly found Workday boards and compared selected vacancies with the local database.

**This is a bounded discovery audit, not a guarantee that every company has no other India/subsidiary board.** Most employers were inspected through their configured official entry page plus up to four linked pages; selected high-risk cases had additional official pages researched. HTTP 200 may be an application shell. Blocked/TLS/DNS cases remain unresolved. No scanner configuration, database records, schedules or code were changed.

## Confirmed and actionable findings

| Company | Finding | Required action / interpretation |
|---|---|---|
| Bank of America | Confirmed missing India board + missed Pega postings | Add an independently validated lateral-ba_continuum board alongside APAC, then run a targeted scan. Official job links and public search/details confirm 26036525 (Software Engineer III - GBS IND, Mumbai) and 26040022 (Senior Team Member, Gurugram) mention Pega/PRPC. No Bank of America records were present in the inspected saved jobs. The latter is not necessarily a developer role: rank duties separately. |
| BD | India-specific backend missing; existing frontend coverage unresolved | Official India job pages link bdx/wd1/EXTERNAL_CAREER_SITE_INDIA. Broad API returns 41 jobs; Pega and PRPC return zero. Add/evaluate this as an alternative to the existing TalentBrew adapter and compare requisition IDs before counting new coverage. It is not evidence of a missed Pega opening today. |
| Columbia Sportswear | Confirmed corporate/India board absent | Registry only has retail marked wrong_scope. columbiasportswearcompany/wd5/Columbia_Career_Site serves corporate India postings. Broad query returned 51, Pega returned 1. Its Bangalore R-026595 detail is now Senior Power Platform & AI Engineer and does not mention Pega/PRPC; the older URL slug says Senior-Automation-Engineer---PEGA-BPM. Add corporate board for scope, but do not treat stale slugs/search matches as current Pega duties. The lowercase URL redirects to the canonical capitalized site. |
| ABB | Alternative public backend discovered; no missed Pega job proved | India job apply link exposes abb/wd3/External_Career_Page behind the existing Phenom frontend. Broad total 2000; Pega returned 81 and PRPC 9. First five keyword-result details lacked Pega/PRPC. Upstream search is noisy; use detail matching and India filtering. No claim that 81 roles are relevant or that the Phenom source misses the same inventory. |
| Chevron | Alternative public backend discovered | Official Bengaluru vacancy links chevron/wd5/jobs. Broad total 153; Pega and PRPC zero. Existing TalentBrew source may cover the same jobs. Compare IDs and consider Workday as a fallback; do not double count companies or jobs. |
| PwC | Separate Acceleration Center route requires comparison | Official India AC pages expose CRM_Experienced_Careers_Site alongside configured Global_Experienced_Careers. The discovered board broad total was 1796. Its one Pega search match was a UK role without Pega in the description (location includes Pegasus Business Park). Do not label that an India Pega miss. Compare India AC requisitions across both boards and map business units. Parent-name matching is insufficient. |
| Toyota | India business has a separate career route; implementation unresolved | TMNA is already marked wrong_scope. Toyota Connected India has its own official careers page with India opportunities. Treat Toyota Connected as a separate business identity; do not assume it covers Toyota Kirloskar or Toyota Financial Services. Public feed/adapter and any Pega roles remain unverified. |
| Renault Nissan Technology | Dedicated employer career page found; feed unresolved | The registry points to a Renault Group URL that redirected to a Key figures page during this audit. RNTBCI has a dedicated rntbci.in/careers page. No dedicated feed was validated; do not assume Renault Group inventory covers all RNTBCI jobs. |
| IBM | Direct source missing; official India careers found | Registry has no career URL or direct portal for IBM. Official ibm.com/in-en/careers and search pages are reachable. Discover a supported public jobs feed. Confluent is a different employer/board and cannot establish IBM-wide coverage. |
| VW Digital Solutions | Unresolved India portal access | Registry has no career URL/direct portal. Official vwg-digitalsolutions.in was found via search, but local TLS validation failed. Keep unresolved; do not substitute CARIAD as proof of India entity coverage. |
| Zurich Insurance | User example captured; no missing-board evidence | Exact supplied Pega query returns two rows. Current saved jobs include Senior Product Manager - Case Management & BPM in Mumbai from Zurich careers; latest two source outcomes found 2, kept 1, status ok. Other result is Schaumburg, Illinois. Zurich verification passed. Check UI geography/saved/hidden filters if the Mumbai job is not visible. Same title also appears as Zurich Cover-More on LinkedIn: inspect brand attribution/deduplication rather than adding a duplicate portal. |
| Citi | Spot-checked official Pega posting already captured | Official Pega Application Developer requisition 261005347 is present in saved jobs from configured citi/wd5/2 board. This sample supports capture of that vacancy, not exhaustive coverage of Citi. |
| AT&T | Extra boards found; India gap not established | Published links expose ATTcollege (7 broad jobs, no Pega/PRPC matches) and Cricket (zero broad rows). Configured ATTGeneral remains separate. Do not automatically add campus/retail boards as India professional coverage. |
| FedEx | Additional regional board found; wrong region for target | Observed FXE-LAC_External_Career_Site is a Latin America board from a Mexico posting, not evidence of an India source. Broad total 158, Pega/PRPC zero. FedEx remains unsupported in current registry; find the India hiring path independently. |

## Exact additional Workday board configurations

These are discovery candidates. State remains unverified until full scope/detail/pagination acceptance. Do not add every candidate automatically; AT&T/FedEx examples illustrate why regional validation matters.

### ABB — External_Career_Page

```json
{
  "kind": "workday",
  "tenant": "abb",
  "datacentre": "wd3",
  "site": "External_Career_Page",
  "state": "candidate",
  "scope": "global"
}
```

Published/discovered on: [https://careers.abb/global/en/how-to-apply](https://careers.abb/global/en/how-to-apply), [https://careers.abb/global/en/search-results](https://careers.abb/global/en/search-results)

- Query `(broad)`: reported total 2000; HTTP 200; JSON returned. Evidence: `evidence/4da46c43357e606d3725.json.gz`.
- Query `Pega`: reported total 81; HTTP 200; JSON returned. Evidence: `evidence/dbd901c69df9cdf3c12f.json.gz`.
- Query `PRPC`: reported total 9; HTTP 200; JSON returned. Evidence: `evidence/2036e9fc5cb890ee6bbb.json.gz`.
- Detail JR00050710: Tootmistöötaja. India evidence: False; Pega/PRPC text marker: False. Evidence `evidence/8151529f990d8d6ae92f.json.gz`. The marker is a screening check, not a role-quality judgment.
- Detail JR00052573: Lead Telecom Engineer (2 Years Contract). India evidence: False; Pega/PRPC text marker: False. Evidence `evidence/60af010373405836674f.json.gz`. The marker is a screening check, not a role-quality judgment.
- Detail JR00052574: Lead Telecom Engineer (2 Years Contract). India evidence: False; Pega/PRPC text marker: False. Evidence `evidence/b6285aa15dba209e7039.json.gz`. The marker is a screening check, not a role-quality judgment.
- Detail JR00053071: Analista de Engenharia de Projetos Pleno. India evidence: False; Pega/PRPC text marker: False. Evidence `evidence/5db1abd63e1df632d2e2.json.gz`. The marker is a screening check, not a role-quality judgment.
- Detail JR00046074: Kontroler/ka Jakości. India evidence: False; Pega/PRPC text marker: False. Evidence `evidence/d120518023ca6406ea99.json.gz`. The marker is a screening check, not a role-quality judgment.

### AT&T — ATTcollege

```json
{
  "kind": "workday",
  "tenant": "att",
  "datacentre": "wd1",
  "site": "ATTcollege",
  "state": "candidate",
  "scope": "global"
}
```

Published/discovered on: [https://att.jobs](https://att.jobs)

- Query `(broad)`: reported total 7; HTTP 200; JSON returned. Evidence: `evidence/20c27b5b39fdc48a599d.json.gz`.
- Query `Pega`: reported total 0; HTTP 200; JSON returned. Evidence: `evidence/0150a40e650fbe3eb3a1.json.gz`.
- Query `PRPC`: reported total 0; HTTP 200; JSON returned. Evidence: `evidence/7dcee1075346fb8c2bdd.json.gz`.

### AT&T — Cricket

```json
{
  "kind": "workday",
  "tenant": "att",
  "datacentre": "wd1",
  "site": "Cricket",
  "state": "candidate",
  "scope": "global"
}
```

Published/discovered on: [https://att.jobs](https://att.jobs)

- Query `(broad)`: reported total 0; HTTP 200; JSON returned. Evidence: `evidence/7e0ffd564733a90acf4f.json.gz`.
- Query `Pega`: reported total 0; HTTP 200; JSON returned. Evidence: `evidence/e2f350e4c8d1b37992aa.json.gz`.
- Query `PRPC`: reported total 0; HTTP 200; JSON returned. Evidence: `evidence/b2ad34bdbd1ead02f1f7.json.gz`.

### Bank of America — lateral-ba_continuum

```json
{
  "kind": "workday",
  "tenant": "ghr",
  "datacentre": "wd1",
  "site": "lateral-ba_continuum",
  "state": "candidate",
  "scope": "global"
}
```

Published/discovered on: [https://careers.bankofamerica.com/en-us/job-detail/26036525/software-engineer-iii-gbs-ind-mumbai-india](https://careers.bankofamerica.com/en-us/job-detail/26036525/software-engineer-iii-gbs-ind-mumbai-india), [https://ghr.wd1.myworkdayjobs.com/lateral-ba_continuum/job/Mumbai/Software-Engineer-III---GBS-IND_26036525](https://ghr.wd1.myworkdayjobs.com/lateral-ba_continuum/job/Mumbai/Software-Engineer-III---GBS-IND_26036525), [https://careers.bankofamerica.com/en-us/job-detail/26039606/team-developer-gandhinagar-india](https://careers.bankofamerica.com/en-us/job-detail/26039606/team-developer-gandhinagar-india), [https://ghr.wd1.myworkdayjobs.com/lateral-ba_continuum/job/Gandhinagar/Team-Developer_26039606](https://ghr.wd1.myworkdayjobs.com/lateral-ba_continuum/job/Gandhinagar/Team-Developer_26039606), [https://careers.bankofamerica.com/en-us/job-detail/26040653/team-leader-gandhinagar-india](https://careers.bankofamerica.com/en-us/job-detail/26040653/team-leader-gandhinagar-india)

- Query `(broad)`: reported total 108; HTTP 200; JSON returned. Evidence: `evidence/4550743c1e3d9c9cb27a.json.gz`.
- Query `Pega`: reported total 2; HTTP 200; JSON returned. Evidence: `evidence/1ba8dcf12149c5eedc08.json.gz`.
- Query `PRPC`: reported total 1; HTTP 200; JSON returned. Evidence: `evidence/94d970d27d7e2d700322.json.gz`.
- Detail 26036525: Software Engineer III - GBS IND. India evidence: True; Pega/PRPC text marker: True. Evidence `evidence/d157bb0bde923d1a66df.json.gz`. The marker is a screening check, not a role-quality judgment.
- Detail 26040022: Senior Team Member. India evidence: True; Pega/PRPC text marker: True. Evidence `evidence/655ab7ccf7aa2a4a1486.json.gz`. The marker is a screening check, not a role-quality judgment.

### BD — EXTERNAL_CAREER_SITE_INDIA

```json
{
  "kind": "workday",
  "tenant": "bdx",
  "datacentre": "wd1",
  "site": "EXTERNAL_CAREER_SITE_INDIA",
  "state": "candidate",
  "scope": "global"
}
```

Published/discovered on: [https://jobs.bd.com/en/job/chennai/area-sales-manager/159/103235948224](https://jobs.bd.com/en/job/chennai/area-sales-manager/159/103235948224), [https://jobs.bd.com/en/job/bengaluru/area-sales-manager-sr-area-sales-manager/159/102536092976](https://jobs.bd.com/en/job/bengaluru/area-sales-manager-sr-area-sales-manager/159/102536092976), [https://bdx.wd1.myworkdayjobs.com/EXTERNAL_CAREER_SITE_INDIA/job/IND-Chennai---Kochar-Globe/Area-Sales-Manager_R-559155/apply](https://bdx.wd1.myworkdayjobs.com/EXTERNAL_CAREER_SITE_INDIA/job/IND-Chennai---Kochar-Globe/Area-Sales-Manager_R-559155/apply), [https://bdx.wd1.myworkdayjobs.com/EXTERNAL_CAREER_SITE_INDIA/job/IND-Bengaluru---Cornich-Al-Latheef/Area-Sales-Manager---Sr-Area-Sales-Manager_R-557827-1/apply](https://bdx.wd1.myworkdayjobs.com/EXTERNAL_CAREER_SITE_INDIA/job/IND-Bengaluru---Cornich-Al-Latheef/Area-Sales-Manager---Sr-Area-Sales-Manager_R-557827-1/apply)

- Query `(broad)`: reported total 41; HTTP 200; JSON returned. Evidence: `evidence/074b8bef1295049faaf1.json.gz`.
- Query `Pega`: reported total 0; HTTP 200; JSON returned. Evidence: `evidence/bec26ce11487f857f938.json.gz`.
- Query `PRPC`: reported total 0; HTTP 200; JSON returned. Evidence: `evidence/427988aaac40357c4e17.json.gz`.

### Chevron — jobs

```json
{
  "kind": "workday",
  "tenant": "chevron",
  "datacentre": "wd5",
  "site": "jobs",
  "state": "candidate",
  "scope": "global"
}
```

Published/discovered on: [https://careers.chevron.com/job/bengaluru/talent-acquisition-specialist/38138/101341422384](https://careers.chevron.com/job/bengaluru/talent-acquisition-specialist/38138/101341422384), [https://careers.chevron.com/job/bengaluru/wells-engineer/38138/98691063856](https://careers.chevron.com/job/bengaluru/wells-engineer/38138/98691063856)

- Query `(broad)`: reported total 153; HTTP 200; JSON returned. Evidence: `evidence/a156c76eec46ec3a9ef0.json.gz`.
- Query `Pega`: reported total 0; HTTP 200; JSON returned. Evidence: `evidence/6b52004453985b97bf15.json.gz`.
- Query `PRPC`: reported total 0; HTTP 200; JSON returned. Evidence: `evidence/43eaca425bb1e524085c.json.gz`.

### Columbia Sportswear — columbia_career_site

```json
{
  "kind": "workday",
  "tenant": "columbiasportswearcompany",
  "datacentre": "wd5",
  "site": "columbia_career_site",
  "state": "candidate",
  "scope": "global"
}
```

Published/discovered on: [https://columbiasportswearcompany.wd5.myworkdayjobs.com/columbia_career_site](https://columbiasportswearcompany.wd5.myworkdayjobs.com/columbia_career_site)

- Query `(broad)`: reported total 51; HTTP 200; JSON returned. Evidence: `evidence/ed93f5f710c49726f13d.json.gz`.
- Query `Pega`: reported total 1; HTTP 200; JSON returned. Evidence: `evidence/b5830b1bc7a8c2f2481f.json.gz`.
- Query `PRPC`: reported total 0; HTTP 200; JSON returned. Evidence: `evidence/744e7a2e4904ff815b66.json.gz`.
- Detail R-026595: Senior Power Platform & AI Engineer. India evidence: True; Pega/PRPC text marker: False. Evidence `evidence/4ca4c2360f8728eb55d7.json.gz`. The marker is a screening check, not a role-quality judgment.

### FedEx — FXE-LAC_External_Career_Site

```json
{
  "kind": "workday",
  "tenant": "fedex",
  "datacentre": "wd1",
  "site": "FXE-LAC_External_Career_Site",
  "state": "candidate",
  "scope": "global"
}
```

Published/discovered on: [https://careers.fedex.com/jobs](https://careers.fedex.com/jobs), [https://careers.fedex.com/lm016-operations-handler/job/66AC4EEC404159A8FCDD12D813DCC564](https://careers.fedex.com/lm016-operations-handler/job/66AC4EEC404159A8FCDD12D813DCC564)

- Query `(broad)`: reported total 158; HTTP 200; JSON returned. Evidence: `evidence/92e29a94beda6bff325e.json.gz`.
- Query `Pega`: reported total 0; HTTP 200; JSON returned. Evidence: `evidence/ea27d6bd932f3cc4ee13.json.gz`.
- Query `PRPC`: reported total 0; HTTP 200; JSON returned. Evidence: `evidence/f2b21bca5c36d5cebec6.json.gz`.

### PwC — CRM_Experienced_Careers_Site

```json
{
  "kind": "workday",
  "tenant": "pwc",
  "datacentre": "wd3",
  "site": "CRM_Experienced_Careers_Site",
  "state": "candidate",
  "scope": "global"
}
```

Published/discovered on: [https://jobs-ta.pwc.com/global/en/ac-india-job-search](https://jobs-ta.pwc.com/global/en/ac-india-job-search)

- Query `(broad)`: reported total 1796; HTTP 200; JSON returned. Evidence: `evidence/cbf9aae127806a63ddb2.json.gz`.
- Query `Pega`: reported total 1; HTTP 200; JSON returned. Evidence: `evidence/0a37d87aadbc5ef9d6dd.json.gz`.
- Query `PRPC`: reported total 0; HTTP 200; JSON returned. Evidence: `evidence/4d4f1e0ae39f207998c5.json.gz`.
- Detail 737509WD: Regulatory Training Advisor – Senior Associate. India evidence: False; Pega/PRPC text marker: False. Evidence `evidence/39bc7d992e8e82bc87b4.json.gz`. The marker is a screening check, not a role-quality judgment.

## Zurich: the supplied example

The exact user-provided search is recorded in `zurich-user-search.json`. The Mumbai role was already saved from the official careers portal. Prior verification found 2 results, one India result, and passed. Recent scan outcomes also report 2 found / 1 kept. The other search result was an Illinois role. This is a captured case, not the same missing-board error as Bank of America.

Official Mumbai vacancy: [https://www.careers.zurich.com/job/Mumbai-Senior-Product-Manager-Case-Management-%26-BPM-MH/1376611457/](https://www.careers.zurich.com/job/Mumbai-Senior-Product-Manager-Case-Management-%26-BPM-MH/1376611457/)

## Every registry entry

“No new board confirmed” does not mean “coverage complete.” See the record for page failures, corporate/apply links and declared limits. All unsupported/unconfigured sources remain coverage gaps.

| Company | Type | Pages attempted / reachable | Finding | Latest scan | Evidence record |
|---|---|---:|---|---|---|
| Aaseya | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C001](C001.json) |
| ABB | gcc | 3 / 3 | Alternative public backend discovered; no missed Pega job proved | empty / found 0 / kept 0 | [C002](C002.json) |
| Accenture | services | 1 / 0 | Access/URL unresolved | blocked / found 0 / kept 0 | [C003](C003.json) |
| Aflac | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C004](C004.json) |
| AIG | gcc | 2 / 2 | No new board confirmed in bounded review | empty / found 2 / kept 0 | [C005](C005.json) |
| Airbus | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C006](C006.json) |
| Airtel | enterprise | 1 / 1 | No scannable direct portal configured | no source outcome / found — / kept — | [C007](C007.json) |
| Allianz Technology | gcc | 1 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C008](C008.json) |
| Allied Solutions | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 3 / kept 0 | [C009](C009.json) |
| Amadeus Labs | product | 2 / 2 | No new board confirmed in bounded review | empty / found 1 / kept 0 | [C010](C010.json) |
| Amdocs | product | 5 / 3 | No new board confirmed in bounded review | empty / found 3 / kept 0 | [C011](C011.json) |
| American Express | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C012](C012.json) |
| Ameriprise | gcc | 2 / 2 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C013](C013.json) |
| Anlage Infotech | staffing | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C014](C014.json) |
| ANZ | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 2 / kept 0 | [C015](C015.json) |
| Areteans | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C016](C016.json) |
| Artech LLC | staffing | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C017](C017.json) |
| AstraZeneca | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C018](C018.json) |
| AT&T | gcc | 1 / 1 | Extra boards found; India gap not established | empty / found 0 / kept 0 | [C019](C019.json) |
| AXA | gcc | 3 / 3 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C020](C020.json) |
| Ayvens | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C021](C021.json) |
| Bank of America | gcc | 7 / 7 | Confirmed missing India board + missed Pega postings | empty / found 0 / kept 0 | [C022](C022.json) |
| Barclays | gcc | 5 / 5 | No new board confirmed in bounded review | ok / found 2 / kept 1 | [C023](C023.json) |
| BD | gcc | 5 / 5 | India-specific backend missing; existing frontend coverage unresolved | empty / found 3 / kept 0 | [C024](C024.json) |
| Birlasoft | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C025](C025.json) |
| BlueRose Technologies | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C026](C026.json) |
| BMW Financial Services | gcc | 1 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C027](C027.json) |
| BMW Group | gcc | 1 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C028](C028.json) |
| BMW TechWorks | gcc | 1 / 1 | No scannable direct portal configured | no source outcome / found — / kept — | [C029](C029.json) |
| BNP Paribas | gcc | 5 / 4 | No scannable direct portal configured | no source outcome / found — / kept — | [C030](C030.json) |
| BNY | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C031](C031.json) |
| Boeing | gcc | 5 / 3 | No new board confirmed in bounded review | empty / found 3 / kept 0 | [C032](C032.json) |
| Booking Holdings | product | 1 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C033](C033.json) |
| Booking.com | product | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C034](C034.json) |
| Booz Allen Hamilton | services | 1 / 1 | No new board confirmed in bounded review | empty / found 10 / kept 0 | [C035](C035.json) |
| Bosch | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C036](C036.json) |
| BP | gcc | 3 / 3 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C037](C037.json) |
| Broadridge | product | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C038](C038.json) |
| BT Group | gcc | 1 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C039](C039.json) |
| Bupa | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C040](C040.json) |
| Caesars Entertainment | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C041](C041.json) |
| Capgemini | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C042](C042.json) |
| Capital One | gcc | 1 / 0 | Access/URL unresolved | empty / found 0 / kept 0 | [C043](C043.json) |
| Carelon Global Solutions | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C044](C044.json) |
| Cargill | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C045](C045.json) |
| Carrier | gcc | 1 / 0 | Access/URL unresolved | empty / found 2 / kept 0 | [C046](C046.json) |
| Charles Schwab | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 4 / kept 0 | [C047](C047.json) |
| Charter Communications | gcc | 1 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C048](C048.json) |
| Chevron | gcc | 5 / 5 | Alternative public backend discovered | empty / found 0 / kept 0 | [C049](C049.json) |
| Cisco | product | 1 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C050](C050.json) |
| Citi | gcc | 5 / 5 | Spot-checked official Pega posting already captured | partial / found 608 / kept 16 | [C051](C051.json) |
| CNH | gcc | 1 / 1 | No new board confirmed in bounded review | error / found 0 / kept 0 | [C052](C052.json) |
| CNO Financial | gcc | 4 / 4 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C053](C053.json) |
| Coca-Cola | gcc | 5 / 4 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C054](C054.json) |
| Coforge | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C055](C055.json) |
| Cognizant | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C056](C056.json) |
| Cohere Health | product | 5 / 5 | No new board confirmed in bounded review | empty / found 63 / kept 0 | [C057](C057.json) |
| Collabera | staffing | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C058](C058.json) |
| Columbia Sportswear | gcc | 3 / 3 | Confirmed corporate/India board absent | no source outcome / found — / kept — | [C059](C059.json) |
| Comcast | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C060](C060.json) |
| Commonwealth Bank | gcc | 5 / 5 | No new board confirmed in bounded review | ok / found 8 / kept 8 | [C061](C061.json) |
| Conduent | services | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C062](C062.json) |
| Confluent | product | 1 / 1 | No new board confirmed in bounded review | error / found 0 / kept 0 | [C063](C063.json) |
| CSC | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 1 / kept 0 | [C064](C064.json) |
| Cummins | gcc | 2 / 2 | No new board confirmed in bounded review | empty / found 63 / kept 0 | [C065](C065.json) |
| CVS Health | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C066](C066.json) |
| Cyient | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C067](C067.json) |
| Daimler Truck | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 2 / kept 0 | [C068](C068.json) |
| Danske Bank | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C069](C069.json) |
| DBS Bank | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C070](C070.json) |
| Dell Technologies | product | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C071](C071.json) |
| Deloitte | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C072](C072.json) |
| Deutsche Bank | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C073](C073.json) |
| Deutsche Telekom Digital Labs | gcc | 1 / 1 | No new board confirmed in bounded review | error / found 0 / kept 0 | [C074](C074.json) |
| DHL | gcc | 1 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C075](C075.json) |
| DP World | gcc | 4 / 4 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C076](C076.json) |
| DXC Technology | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C077](C077.json) |
| EAI Systems | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C078](C078.json) |
| Eaton | gcc | 3 / 3 | No new board confirmed in bounded review | empty / found 23 / kept 0 | [C079](C079.json) |
| Eclatprime | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C080](C080.json) |
| Empower | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C081](C081.json) |
| enGen | gcc | 5 / 5 | No new board confirmed in bounded review | ok / found 6 / kept 5 | [C082](C082.json) |
| EPAM Systems | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C083](C083.json) |
| Estes Express | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 4 / kept 0 | [C084](C084.json) |
| Evernorth | gcc | 3 / 3 | No new board confirmed in bounded review | empty / found 2 / kept 0 | [C085](C085.json) |
| Eviden | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C086](C086.json) |
| Evoke Technologies | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C087](C087.json) |
| ExxonMobil | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C088](C088.json) |
| EY | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C089](C089.json) |
| FedEx | gcc | 4 / 4 | Additional regional board found; wrong region for target | no source outcome / found — / kept — | [C090](C090.json) |
| Fidelity Investments | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 1 / kept 0 | [C091](C091.json) |
| Fidelity National Financial | gcc | 2 / 2 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C092](C092.json) |
| First Citizens Bank | gcc | 2 / 2 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C093](C093.json) |
| FIS | product | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C094](C094.json) |
| Fiserv | product | 2 / 2 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C095](C095.json) |
| Ford | gcc | 1 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C096](C096.json) |
| Ford Credit | gcc | 1 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C097](C097.json) |
| fusionAIx | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C098](C098.json) |
| GE Aerospace | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C099](C099.json) |
| GE HealthCare | gcc | 2 / 2 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C100](C100.json) |
| GE Vernova | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C101](C101.json) |
| General Motors | gcc | 5 / 3 | No new board confirmed in bounded review | empty / found 16 / kept 0 | [C102](C102.json) |
| Genpact | services | 1 / 1 | No new board confirmed in bounded review | partial / found 20 / kept 1 | [C103](C103.json) |
| Global Payments | product | 1 / 0 | Access/URL unresolved | empty / found 0 / kept 0 | [C104](C104.json) |
| Goldman Sachs | gcc | 1 / 1 | No scannable direct portal configured | no source outcome / found — / kept — | [C105](C105.json) |
| HCL Technologies | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C106](C106.json) |
| HDFC Bank | enterprise | 5 / 5 | No scannable direct portal configured | no source outcome / found — / kept — | [C107](C107.json) |
| Hexaware | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C108](C108.json) |
| Honeywell | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C109](C109.json) |
| Horizontal | staffing | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C110](C110.json) |
| HSBC | gcc | 5 / 5 | No new board confirmed in bounded review | error / found 0 / kept 0 | [C111](C111.json) |
| IBM | product | 5 / 5 | Direct source missing; official India careers found | no source outcome / found — / kept — | [C112](C112.json) |
| ICICI Bank | enterprise | 1 / 1 | No scannable direct portal configured | no source outcome / found — / kept — | [C113](C113.json) |
| IFFCO Tokio | enterprise | 1 / 1 | No scannable direct portal configured | no source outcome / found — / kept — | [C114](C114.json) |
| IKEA | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C115](C115.json) |
| Inadev | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C116](C116.json) |
| Infosys | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C117](C117.json) |
| ING | gcc | 1 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C118](C118.json) |
| Innova ESI | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C119](C119.json) |
| Intel | product | 1 / 0 | Access/URL unresolved | empty / found 10 / kept 0 | [C120](C120.json) |
| ITC Limited | enterprise | 1 / 1 | No scannable direct portal configured | no source outcome / found — / kept — | [C121](C121.json) |
| JLR | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C122](C122.json) |
| John Deere | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C123](C123.json) |
| John Deere Financial | gcc | 1 / 1 | No scannable direct portal configured | no source outcome / found — / kept — | [C124](C124.json) |
| Johnson & Johnson | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C125](C125.json) |
| Johnson Controls | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C126](C126.json) |
| JPMorganChase | gcc | 1 / 1 | No new board confirmed in bounded review | ok / found 9 / kept 1 | [C127](C127.json) |
| Jyotirgamay Solutions | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C128](C128.json) |
| Ketan Software | staffing | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C129](C129.json) |
| Komatsu | gcc | 1 / 1 | No scannable direct portal configured | no source outcome / found — / kept — | [C130](C130.json) |
| Kotak Mahindra Bank | enterprise | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C131](C131.json) |
| KPMG | services | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C132](C132.json) |
| Levi Strauss & Co. | gcc | 1 / 1 | No new board confirmed in bounded review | partial / found 298 / kept 0 | [C133](C133.json) |
| Liberty Mutual | gcc | 4 / 4 | No new board confirmed in bounded review | blocked / found 0 / kept 0 | [C134](C134.json) |
| Lloyds Banking Group | gcc | 1 / 1 | No new board confirmed in bounded review | ok / found 1 / kept 1 | [C135](C135.json) |
| Lockheed Martin | gcc | 1 / 1 | No scannable direct portal configured | no source outcome / found — / kept — | [C136](C136.json) |
| Lowe's | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C137](C137.json) |
| LPL Financial | gcc | 2 / 2 | No new board confirmed in bounded review | empty / found 1 / kept 0 | [C138](C138.json) |
| LTIMindtree | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C139](C139.json) |
| Lufthansa Systems | gcc | 2 / 2 | No scannable direct portal configured | no source outcome / found — / kept — | [C140](C140.json) |
| Maantic | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C141](C141.json) |
| Macquarie | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C142](C142.json) |
| Macy's | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 2 / kept 0 | [C143](C143.json) |
| Maersk | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C144](C144.json) |
| Manulife | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 1 / kept 0 | [C145](C145.json) |
| Marriott | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 4 / kept 0 | [C146](C146.json) |
| Marsh McLennan | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C147](C147.json) |
| MassMutual | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C148](C148.json) |
| Mastech Holdings | staffing | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C149](C149.json) |
| Mastercard | product | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C150](C150.json) |
| Maximus | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C151](C151.json) |
| Medtronic | gcc | 1 / 1 | No new board confirmed in bounded review | partial / found 907 / kept 0 | [C152](C152.json) |
| Mercedes-Benz Group | gcc | 1 / 0 | Access/URL unresolved | error / found 0 / kept 0 | [C153](C153.json) |
| Mercedes-Benz Mobility | gcc | 1 / 0 | Access/URL unresolved | error / found 0 / kept 0 | [C154](C154.json) |
| Mercedes-Benz Research and Development India | gcc | 1 / 0 | Access/URL unresolved | error / found 0 / kept 0 | [C155](C155.json) |
| Merck | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C156](C156.json) |
| Merkle | services | 1 / 1 | No new board confirmed in bounded review | empty / found 18 / kept 0 | [C157](C157.json) |
| MetLife | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C158](C158.json) |
| Mizuho Financial Group | gcc | 4 / 4 | No scannable direct portal configured | no source outcome / found — / kept — | [C159](C159.json) |
| Mizuho Global Services | gcc | 4 / 4 | No scannable direct portal configured | no source outcome / found — / kept — | [C160](C160.json) |
| Mondelez | gcc | 5 / 5 | No new board confirmed in bounded review | ok / found 383 / kept 1 | [C161](C161.json) |
| Morgan Stanley | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C162](C162.json) |
| Mphasis | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C163](C163.json) |
| MUFG | gcc | 2 / 2 | No new board confirmed in bounded review | empty / found 3 / kept 0 | [C164](C164.json) |
| MUFG Pension & Market Services | gcc | 3 / 3 | No new board confirmed in bounded review | ok / found 2 / kept 1 | [C165](C165.json) |
| National Australia Bank | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 1 / kept 0 | [C166](C166.json) |
| NatWest Group | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C167](C167.json) |
| Navistar | gcc | 2 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C168](C168.json) |
| Ness Digital Engineering | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C169](C169.json) |
| Nike | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 3 / kept 0 | [C170](C170.json) |
| Nokia | product | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C171](C171.json) |
| Northern Trust | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C172](C172.json) |
| Nous Infosystems | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C173](C173.json) |
| Novartis | gcc | 5 / 5 | No scannable direct portal configured | no source outcome / found — / kept — | [C174](C174.json) |
| NTT DATA | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C175](C175.json) |
| Optum | gcc | 5 / 5 | No new board confirmed in bounded review | ok / found 2 / kept 1 | [C176](C176.json) |
| Orange Business | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C177](C177.json) |
| PayPal | product | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C178](C178.json) |
| Pegasystems | product | 5 / 1 | No scannable direct portal configured | no source outcome / found — / kept — | [C179](C179.json) |
| People Prime Worldwide | staffing | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C180](C180.json) |
| PepsiCo | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C181](C181.json) |
| Persistent Systems | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C182](C182.json) |
| Pfizer | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 2 / kept 0 | [C183](C183.json) |
| Philips | gcc | 2 / 2 | No new board confirmed in bounded review | empty / found 1 / kept 0 | [C184](C184.json) |
| PNC | gcc | 1 / 1 | No new board confirmed in bounded review | ok / found 2 / kept 1 | [C185](C185.json) |
| Prime Therapeutics | gcc | 2 / 2 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C186](C186.json) |
| Procter & Gamble | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 9 / kept 0 | [C187](C187.json) |
| Proximus | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C188](C188.json) |
| PruTech Solutions | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C189](C189.json) |
| Publicis Sapient | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C190](C190.json) |
| PwC | services | 6 / 5 | Separate Acceleration Center route requires comparison | ok / found 3 / kept 1 | [C191](C191.json) |
| Qualcomm | product | 1 / 1 | No new board confirmed in bounded review | empty / found 2 / kept 0 | [C192](C192.json) |
| Quess Corp | staffing | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C193](C193.json) |
| Rabobank | gcc | 1 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C194](C194.json) |
| Renault Group | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C195](C195.json) |
| Renault Nissan Technology | gcc | 2 / 2 | Dedicated employer career page found; feed unresolved | no source outcome / found — / kept — | [C196](C196.json) |
| Roche | gcc | 1 / 1 | No new board confirmed in bounded review | ok / found 1 / kept 1 | [C197](C197.json) |
| Rolls-Royce | gcc | 5 / 5 | No scannable direct portal configured | no source outcome / found — / kept — | [C198](C198.json) |
| S&P Global | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C199](C199.json) |
| Scadea | staffing | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C200](C200.json) |
| Schneider Electric | gcc | 1 / 0 | Access/URL unresolved | error / found 0 / kept 0 | [C201](C201.json) |
| Shell | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C202](C202.json) |
| Siemens | gcc | 1 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C203](C203.json) |
| Sky | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C204](C204.json) |
| SLB | gcc | 2 / 2 | No scannable direct portal configured | no source outcome / found — / kept — | [C205](C205.json) |
| Societe Generale | gcc | 2 / 2 | No scannable direct portal configured | no source outcome / found — / kept — | [C206](C206.json) |
| Sonata Software | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C207](C207.json) |
| Sopra Steria | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C208](C208.json) |
| Standard Chartered | gcc | 5 / 5 | No new board confirmed in bounded review | error / found 0 / kept 0 | [C209](C209.json) |
| State Street | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 1 / kept 0 | [C210](C210.json) |
| Stellantis | gcc | 1 / 1 | No scannable direct portal configured | no source outcome / found — / kept — | [C211](C211.json) |
| Sun Life | gcc | 1 / 0 | Access/URL unresolved | empty / found 2 / kept 0 | [C212](C212.json) |
| Synchrony | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C213](C213.json) |
| Synechron | services | 1 / 1 | No new board confirmed in bounded review | ok / found 1 / kept 1 | [C214](C214.json) |
| T-Mobile | gcc | 3 / 3 | No scannable direct portal configured | no source outcome / found — / kept — | [C215](C215.json) |
| Target | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C216](C216.json) |
| Tata Consultancy Services | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C217](C217.json) |
| Tech Mahindra | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C218](C218.json) |
| Telstra | gcc | 2 / 2 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C219](C219.json) |
| Tesco | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C220](C220.json) |
| The Hartford | gcc | 1 / 0 | Access/URL unresolved | empty / found 0 / kept 0 | [C221](C221.json) |
| Toyota | gcc | 6 / 5 | India business has a separate career route; implementation unresolved | no source outcome / found — / kept — | [C222](C222.json) |
| Toyota Financial Services | gcc | 1 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C223](C223.json) |
| U.S. Bank | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C224](C224.json) |
| UBS | gcc | 1 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C225](C225.json) |
| Uni-Pega | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C226](C226.json) |
| Unilever | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 4 / kept 0 | [C227](C227.json) |
| Unisys | services | 1 / 1 | No new board confirmed in bounded review | empty / found 1 / kept 0 | [C228](C228.json) |
| UPS | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C229](C229.json) |
| UST | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C230](C230.json) |
| Vanguard | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C231](C231.json) |
| Verizon | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 1 / kept 0 | [C232](C232.json) |
| Virtusa | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C233](C233.json) |
| Visa | product | 1 / 0 | Access/URL unresolved | error / found 0 / kept 0 | [C234](C234.json) |
| Vodafone | gcc | 5 / 5 | No scannable direct portal configured | no source outcome / found — / kept — | [C235](C235.json) |
| Vodafone Idea | enterprise | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C236](C236.json) |
| Volvo Cars | gcc | 5 / 5 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C237](C237.json) |
| Voya Financial | gcc | 2 / 2 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C238](C238.json) |
| VW Digital Solutions | gcc | 1 / 0 | Unresolved India portal access | no source outcome / found — / kept — | [C239](C239.json) |
| Walmart Global Tech | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C240](C240.json) |
| Wells Fargo | gcc | 5 / 5 | No new board confirmed in bounded review | ok / found 1 / kept 1 | [C241](C241.json) |
| Western Union | gcc | 1 / 0 | Access/URL unresolved | empty / found 0 / kept 0 | [C242](C242.json) |
| Westpac | gcc | 1 / 1 | No new board confirmed in bounded review | empty / found 0 / kept 0 | [C243](C243.json) |
| Wipro | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C244](C244.json) |
| Xperteez Technology | services | 0 / 0 | No scannable direct portal configured | no source outcome / found — / kept — | [C245](C245.json) |
| Zensar Technologies | services | 1 / 1 | No new board confirmed in bounded review | ok / found 5 / kept 5 | [C246](C246.json) |
| Zurich Insurance | gcc | 1 / 1 | User example captured; no missing-board evidence | ok / found 2 / kept 1 | [C247](C247.json) |

## Official website entry points and request outcomes

### C001 — Aaseya

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C002 — ABB

Configured career URL: [https://careers.abb/global/en](https://careers.abb/global/en)

- [https://careers.abb/global/en](https://careers.abb/global/en): page reachable; HTTP 200. 
- [https://careers.abb/global/en/how-to-apply](https://careers.abb/global/en/how-to-apply): page reachable; HTTP 200. 
- [https://careers.abb/global/en/search-results](https://careers.abb/global/en/search-results): page reachable; HTTP 200. 

### C003 — Accenture

Configured career URL: [https://accenture.wd103.myworkdayjobs.com/AccentureCareers](https://accenture.wd103.myworkdayjobs.com/AccentureCareers)

- [https://accenture.wd103.myworkdayjobs.com/AccentureCareers](https://accenture.wd103.myworkdayjobs.com/AccentureCareers): HTTP error; HTTP 429. HTTP Error 429: Too Many Requests

### C004 — Aflac

Configured career URL: [https://careers.aflac.com](https://careers.aflac.com)

- [https://careers.aflac.com](https://careers.aflac.com): page reachable; HTTP 200. 
- [https://careers.aflac.com/go/View-All-Jobs/8697400/](https://careers.aflac.com/go/View-All-Jobs/8697400/): page reachable; HTTP 200. 
- [https://careers.aflac.com/viewalljobs/](https://careers.aflac.com/viewalljobs/): page reachable; HTTP 200. 
- [https://careers.aflac.com/go/View-All-Jobs/8697400/](https://careers.aflac.com/go/View-All-Jobs/8697400/): page reachable; HTTP 200. 
- [https://careers.aflac.com/go/View-All-Jobs/8697400/?q=&sortColumn=referencedate&sortDirection=desc](https://careers.aflac.com/go/View-All-Jobs/8697400/?q=&sortColumn=referencedate&sortDirection=desc): page reachable; HTTP 200. 

### C005 — AIG

Configured career URL: [https://www.aig.com/careers](https://www.aig.com/careers)

- [https://www.aig.com/careers](https://www.aig.com/careers): page reachable; HTTP 200. 
- [https://aig.wd1.myworkdayjobs.com/aig](https://aig.wd1.myworkdayjobs.com/aig): page reachable; HTTP 200. 

### C006 — Airbus

Configured career URL: [https://www.airbus.com/en/careers](https://www.airbus.com/en/careers)

- [https://www.airbus.com/en/careers](https://www.airbus.com/en/careers): page reachable; HTTP 200. 
- [https://ag.wd3.myworkdayjobs.com/en-US/Airbus/job/Bangalore-Area/Training-Product-Support-Engineer_JR10446378?workerSubType=f5811cef9cb501a69768a71d470a6d15&locationCountry=c4f78be1a8f14da0ab49ce1162348a5e](https://ag.wd3.myworkdayjobs.com/en-US/Airbus/job/Bangalore-Area/Training-Product-Support-Engineer_JR10446378?workerSubType=f5811cef9cb501a69768a71d470a6d15&locationCountry=c4f78be1a8f14da0ab49ce1162348a5e): page reachable; HTTP 200. 
- [https://ag.wd3.myworkdayjobs.com/en-US/Airbus/job/Bangalore-Area/In-Service-Airworthiness-Engineering_JR10446954?workerSubType=f5811cef9cb501a69768a71d470a6d15&locationCountry=c4f78be1a8f14da0ab49ce1162348a5e](https://ag.wd3.myworkdayjobs.com/en-US/Airbus/job/Bangalore-Area/In-Service-Airworthiness-Engineering_JR10446954?workerSubType=f5811cef9cb501a69768a71d470a6d15&locationCountry=c4f78be1a8f14da0ab49ce1162348a5e): page reachable; HTTP 200. 
- [https://ag.wd3.myworkdayjobs.com/en-US/Airbus/job/Bristol-Area/Safety---Reliability-Engineer_JR10451843?workerSubType=f5811cef9cb501a69768a71d470a6d15&locationCountry=29247e57dbaf46fb855b224e03170bc7](https://ag.wd3.myworkdayjobs.com/en-US/Airbus/job/Bristol-Area/Safety---Reliability-Engineer_JR10451843?workerSubType=f5811cef9cb501a69768a71d470a6d15&locationCountry=29247e57dbaf46fb855b224e03170bc7): page reachable; HTTP 200. 
- [https://ag.wd3.myworkdayjobs.com/en-US/Airbus/job/Wichita-KS/Principal-Stress-Engineer_JR10447399-1?workerSubType=f5811cef9cb501a69768a71d470a6d15&locationCountry=bc33aa3152ec42d4995f4791a106ed09](https://ag.wd3.myworkdayjobs.com/en-US/Airbus/job/Wichita-KS/Principal-Stress-Engineer_JR10447399-1?workerSubType=f5811cef9cb501a69768a71d470a6d15&locationCountry=bc33aa3152ec42d4995f4791a106ed09): page reachable; HTTP 200. 

### C007 — Airtel

Configured career URL: [https://careers.airtel.com/](https://careers.airtel.com/)

- [https://careers.airtel.com/](https://careers.airtel.com/): page reachable; HTTP 200. 

### C008 — Allianz Technology

Configured career URL: [https://careers.allianz.com](https://careers.allianz.com)

- [https://careers.allianz.com](https://careers.allianz.com): network/TLS error; HTTP n/a. <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate in certificate chain (_ssl.c:1032)>

### C009 — Allied Solutions

Configured career URL: [https://alliedsolutions.wd501.myworkdayjobs.com/Allied_External](https://alliedsolutions.wd501.myworkdayjobs.com/Allied_External)

- [https://alliedsolutions.wd501.myworkdayjobs.com/Allied_External](https://alliedsolutions.wd501.myworkdayjobs.com/Allied_External): page reachable; HTTP 200. 

### C010 — Amadeus Labs

Configured career URL: [https://amadeus.com/en/careers/overview](https://amadeus.com/en/careers/overview)

- [https://amadeus.com/en/careers/overview](https://amadeus.com/en/careers/overview): page reachable; HTTP 200. 
- [https://amadeus.wd502.myworkdayjobs.com/jobs](https://amadeus.wd502.myworkdayjobs.com/jobs): page reachable; HTTP 200. 

### C011 — Amdocs

Configured career URL: [https://www.amdocs.com/careers/you-without-limits/india](https://www.amdocs.com/careers/you-without-limits/india)

- [https://www.amdocs.com/careers/you-without-limits/india](https://www.amdocs.com/careers/you-without-limits/india): page reachable; HTTP 200. 
- [https://jobs.amdocs.com/job/Pune-SW-Test-Engineer-MH/783723200/?locale=en_US](https://jobs.amdocs.com/job/Pune-SW-Test-Engineer-MH/783723200/?locale=en_US): HTTP error; HTTP 404. HTTP Error 404: NOT FOUND
- [https://www.amdocs.com/careers/you-without-limits/india](https://www.amdocs.com/careers/you-without-limits/india): page reachable; HTTP 200. 
- [https://www.amdocs.com/careers/you-without-limits/india?category=award](https://www.amdocs.com/careers/you-without-limits/india?category=award): page reachable; HTTP 200. 
- [https://career4.successfactors.com/sfcareer/jobreqcareer?jobId=123062&company=amdocs](https://career4.successfactors.com/sfcareer/jobreqcareer?jobId=123062&company=amdocs): HTTP error; HTTP 404. HTTP Error 404: NOT FOUND

### C012 — American Express

Configured career URL: [https://careers.americanexpress.com/en/sites/CX_1/jobs?location=India](https://careers.americanexpress.com/en/sites/CX_1/jobs?location=India)

- [https://careers.americanexpress.com/en/sites/CX_1/jobs?location=India](https://careers.americanexpress.com/en/sites/CX_1/jobs?location=India): page reachable; HTTP 200. 

### C013 — Ameriprise

Configured career URL: [https://www.ameriprise.com/careers](https://www.ameriprise.com/careers)

- [https://www.ameriprise.com/careers](https://www.ameriprise.com/careers): page reachable; HTTP 200. 
- [https://www.ameriprise.com/careers](https://www.ameriprise.com/careers): page reachable; HTTP 200. 

### C014 — Anlage Infotech

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C015 — ANZ

Configured career URL: [https://careers.anz.com](https://careers.anz.com)

- [https://careers.anz.com](https://careers.anz.com): page reachable; HTTP 200. 

### C016 — Areteans

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C017 — Artech LLC

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C018 — AstraZeneca

Configured career URL: [https://careers.astrazeneca.com](https://careers.astrazeneca.com)

- [https://careers.astrazeneca.com](https://careers.astrazeneca.com): page reachable; HTTP 200. 
- [https://careers.astrazeneca.com/india](https://careers.astrazeneca.com/india): page reachable; HTTP 200. 
- [https://astrazeneca.eightfold.ai/careers/join?domain=astrazeneca.com&hl=en](https://astrazeneca.eightfold.ai/careers/join?domain=astrazeneca.com&hl=en): page reachable; HTTP 200. 
- [https://careers.astrazeneca.com/job/bengaluru/senior-consultant-ai-ml-engineering/7684/103245988128](https://careers.astrazeneca.com/job/bengaluru/senior-consultant-ai-ml-engineering/7684/103245988128): page reachable; HTTP 200. 
- [https://careers.astrazeneca.com/job/bengaluru/associate-web-delivery/7684/103239724608](https://careers.astrazeneca.com/job/bengaluru/associate-web-delivery/7684/103239724608): page reachable; HTTP 200. 

### C019 — AT&T

Configured career URL: [https://att.jobs](https://att.jobs)

- [https://att.jobs](https://att.jobs): page reachable; HTTP 200. 

### C020 — AXA

Configured career URL: [https://careers.axa.com/careers-home/](https://careers.axa.com/careers-home/)

- [https://careers.axa.com/careers-home/](https://careers.axa.com/careers-home/): page reachable; HTTP 200. 
- [https://careers.axa.com/jobs?page=1&country=India%7CPhillippines%7CHong%20Kong%7CSingapore%7CMalaysia%7CJapan%7CChina%7CIndonesia%7CKorea%7CThailand%7CT%C3%BCrkiye%7CViet%20Nam%7CUnited%20Arab%20Emirates%7CLebanon](https://careers.axa.com/jobs?page=1&country=India%7CPhillippines%7CHong%20Kong%7CSingapore%7CMalaysia%7CJapan%7CChina%7CIndonesia%7CKorea%7CThailand%7CT%C3%BCrkiye%7CViet%20Nam%7CUnited%20Arab%20Emirates%7CLebanon): page reachable; HTTP 200. 
- [https://careers.axa.com/careers-home/jobs?page=1&country=India%7CPhillippines%7CHong%20Kong%7CSingapore%7CMalaysia%7CJapan%7CChina%7CIndonesia%7CKorea%7CThailand%7CT%C3%BCrkiye%7CViet%20Nam%7CUnited%20Arab%20Emirates%7CLebanon](https://careers.axa.com/careers-home/jobs?page=1&country=India%7CPhillippines%7CHong%20Kong%7CSingapore%7CMalaysia%7CJapan%7CChina%7CIndonesia%7CKorea%7CThailand%7CT%C3%BCrkiye%7CViet%20Nam%7CUnited%20Arab%20Emirates%7CLebanon): page reachable; HTTP 200. 

### C021 — Ayvens

Configured career URL: [https://www.ayvens.com/en-cp/careers/](https://www.ayvens.com/en-cp/careers/)

- [https://www.ayvens.com/en-cp/careers/](https://www.ayvens.com/en-cp/careers/): page reachable; HTTP 200. 
- [https://www.ayvens.com/en-in/](https://www.ayvens.com/en-in/): page reachable; HTTP 200. 
- [https://www.ayvens.com/en-cp/careers/open-positions/](https://www.ayvens.com/en-cp/careers/open-positions/): page reachable; HTTP 200. 
- [https://ayvens.wd3.myworkdayjobs.com/AyvensCareers?locations=df6649765eae10019cd4f8a65b220000](https://ayvens.wd3.myworkdayjobs.com/AyvensCareers?locations=df6649765eae10019cd4f8a65b220000): page reachable; HTTP 200. 
- [https://ayvens.wd3.myworkdayjobs.com/AyvensCareers?locations=74b16fde840b10019a2e8d53422d0000](https://ayvens.wd3.myworkdayjobs.com/AyvensCareers?locations=74b16fde840b10019a2e8d53422d0000): page reachable; HTTP 200. 

### C022 — Bank of America

Configured career URL: [https://careers.bankofamerica.com/en-us](https://careers.bankofamerica.com/en-us)

- [https://careers.bankofamerica.com/en-us](https://careers.bankofamerica.com/en-us): page reachable; HTTP 200. 
- [https://careers.bankofamerica.com/en-us/job-search/india](https://careers.bankofamerica.com/en-us/job-search/india): page reachable; HTTP 200. 
- [https://careers.bankofamerica.com/en-us/job-detail/26036525/software-engineer-iii-gbs-ind-mumbai-india](https://careers.bankofamerica.com/en-us/job-detail/26036525/software-engineer-iii-gbs-ind-mumbai-india): page reachable; HTTP 200. 
- [https://ghr.wd1.myworkdayjobs.com/lateral-ba_continuum/job/Mumbai/Software-Engineer-III---GBS-IND_26036525](https://ghr.wd1.myworkdayjobs.com/lateral-ba_continuum/job/Mumbai/Software-Engineer-III---GBS-IND_26036525): page reachable; HTTP 200. 
- [https://careers.bankofamerica.com/en-us/job-detail/26039606/team-developer-gandhinagar-india](https://careers.bankofamerica.com/en-us/job-detail/26039606/team-developer-gandhinagar-india): page reachable; HTTP 200. 
- [https://ghr.wd1.myworkdayjobs.com/lateral-ba_continuum/job/Gandhinagar/Team-Developer_26039606](https://ghr.wd1.myworkdayjobs.com/lateral-ba_continuum/job/Gandhinagar/Team-Developer_26039606): page reachable; HTTP 200. 
- [https://careers.bankofamerica.com/en-us/job-detail/26040653/team-leader-gandhinagar-india](https://careers.bankofamerica.com/en-us/job-detail/26040653/team-leader-gandhinagar-india): page reachable; HTTP 200. 

### C023 — Barclays

Configured career URL: [https://search.jobs.barclays](https://search.jobs.barclays)

- [https://search.jobs.barclays](https://search.jobs.barclays): page reachable; HTTP 200. 
- [https://search.jobs.barclays/job/pune/group-records-execution-analyst/13015/98136606448](https://search.jobs.barclays/job/pune/group-records-execution-analyst/13015/98136606448): page reachable; HTTP 200. 
- [https://search.jobs.barclays](https://search.jobs.barclays): page reachable; HTTP 200. 
- [https://barclays.wd3.myworkdayjobs.com/External_Career_Site_Barclays/job/Pune-Gera-Commerzone-SEZ/Group-Records-Execution-Analyst_JR-0000109644-1/apply](https://barclays.wd3.myworkdayjobs.com/External_Career_Site_Barclays/job/Pune-Gera-Commerzone-SEZ/Group-Records-Execution-Analyst_JR-0000109644-1/apply): page reachable; HTTP 200. 
- [https://search.jobs.barclays/job/pune/group-records-execution-analyst/13015/98136606448](https://search.jobs.barclays/job/pune/group-records-execution-analyst/13015/98136606448): page reachable; HTTP 200. 

### C024 — BD

Configured career URL: [https://jobs.bd.com/en/location/india-jobs/159/1269750/2](https://jobs.bd.com/en/location/india-jobs/159/1269750/2)

- [https://jobs.bd.com/en/location/india-jobs/159/1269750/2](https://jobs.bd.com/en/location/india-jobs/159/1269750/2): page reachable; HTTP 200. 
- [https://jobs.bd.com/en/job/chennai/area-sales-manager/159/103235948224](https://jobs.bd.com/en/job/chennai/area-sales-manager/159/103235948224): page reachable; HTTP 200. 
- [https://jobs.bd.com/en/job/bengaluru/area-sales-manager-sr-area-sales-manager/159/102536092976](https://jobs.bd.com/en/job/bengaluru/area-sales-manager-sr-area-sales-manager/159/102536092976): page reachable; HTTP 200. 
- [https://bdx.wd1.myworkdayjobs.com/EXTERNAL_CAREER_SITE_INDIA/job/IND-Chennai---Kochar-Globe/Area-Sales-Manager_R-559155/apply](https://bdx.wd1.myworkdayjobs.com/EXTERNAL_CAREER_SITE_INDIA/job/IND-Chennai---Kochar-Globe/Area-Sales-Manager_R-559155/apply): page reachable; HTTP 200. 
- [https://bdx.wd1.myworkdayjobs.com/EXTERNAL_CAREER_SITE_INDIA/job/IND-Bengaluru---Cornich-Al-Latheef/Area-Sales-Manager---Sr-Area-Sales-Manager_R-557827-1/apply](https://bdx.wd1.myworkdayjobs.com/EXTERNAL_CAREER_SITE_INDIA/job/IND-Bengaluru---Cornich-Al-Latheef/Area-Sales-Manager---Sr-Area-Sales-Manager_R-557827-1/apply): page reachable; HTTP 200. 

### C025 — Birlasoft

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C026 — BlueRose Technologies

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C027 — BMW Financial Services

Configured career URL: [https://www.bmwgroup.jobs](https://www.bmwgroup.jobs)

- [https://www.bmwgroup.jobs](https://www.bmwgroup.jobs): network/TLS error; HTTP n/a. The read operation timed out

### C028 — BMW Group

Configured career URL: [https://www.bmwgroup.jobs](https://www.bmwgroup.jobs)

- [https://www.bmwgroup.jobs](https://www.bmwgroup.jobs): network/TLS error; HTTP n/a. The read operation timed out

### C029 — BMW TechWorks

Configured career URL: [https://careers-bmwtechworks.peoplestrong.com/](https://careers-bmwtechworks.peoplestrong.com/)

- [https://careers-bmwtechworks.peoplestrong.com/](https://careers-bmwtechworks.peoplestrong.com/): page reachable; HTTP 200. 

### C030 — BNP Paribas

Configured career URL: [https://www.bnpparibas.bank.in/en/work-with-us/apply-now/](https://www.bnpparibas.bank.in/en/work-with-us/apply-now/)

- [https://www.bnpparibas.bank.in/en/work-with-us/apply-now/](https://www.bnpparibas.bank.in/en/work-with-us/apply-now/): page reachable; HTTP 200. 
- [https://group.bnpparibas/en/careers/all-job-offers/india](https://group.bnpparibas/en/careers/all-job-offers/india): HTTP error; HTTP 403. HTTP Error 403: Forbidden
- [https://www.bnpparibas.bank.in/en/](https://www.bnpparibas.bank.in/en/): page reachable; HTTP 200. 
- [https://www.bnpparibas.bank.in/en/live-currency-rates-for-india/](https://www.bnpparibas.bank.in/en/live-currency-rates-for-india/): page reachable; HTTP 200. 
- [https://www.bnpparibas.bank.in/en/about-us/](https://www.bnpparibas.bank.in/en/about-us/): page reachable; HTTP 200. 

### C031 — BNY

Configured career URL: [https://www.bny.com/corporate/global/en/about-us/careers/experienced-professionals.html](https://www.bny.com/corporate/global/en/about-us/careers/experienced-professionals.html)

- [https://www.bny.com/corporate/global/en/about-us/careers/experienced-professionals.html](https://www.bny.com/corporate/global/en/about-us/careers/experienced-professionals.html): page reachable; HTTP 200. 
- [https://www.bny.com/corporate/in/en.html](https://www.bny.com/corporate/in/en.html): page reachable; HTTP 200. 
- [https://www.bny.com/corporate/global/en/about-us/careers/applying-interviewing.html](https://www.bny.com/corporate/global/en/about-us/careers/applying-interviewing.html): page reachable; HTTP 200. 
- [https://eofe.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/BNY-Careers](https://eofe.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/BNY-Careers): page reachable; HTTP 200. 
- [https://www.bny.com/corporate/in/en/about-bny-india.html](https://www.bny.com/corporate/in/en/about-bny-india.html): page reachable; HTTP 200. 

### C032 — Boeing

Configured career URL: [https://jobs.boeing.com](https://jobs.boeing.com)

- [https://jobs.boeing.com](https://jobs.boeing.com): page reachable; HTTP 200. 
- [https://jobs.boeing.com/sweindia](https://jobs.boeing.com/sweindia): page reachable; HTTP 200. 
- [https://jobs.boeing.com/boeing-in-india](https://jobs.boeing.com/boeing-in-india): page reachable; HTTP 200. 
- [https://jobs.boeing.com/job/bengaluru/electrical-engineering-manager/185/63469181456](https://jobs.boeing.com/job/bengaluru/electrical-engineering-manager/185/63469181456): HTTP error; HTTP 404. HTTP Error 404: Not Found
- [https://jobs.boeing.com/job/bengaluru/lead-software-engineer/185/63473768832](https://jobs.boeing.com/job/bengaluru/lead-software-engineer/185/63473768832): HTTP error; HTTP 404. HTTP Error 404: Not Found

### C033 — Booking Holdings

Configured career URL: [https://careers.bookingholdings.com](https://careers.bookingholdings.com)

- [https://careers.bookingholdings.com](https://careers.bookingholdings.com): network/TLS error; HTTP n/a. <urlopen error [Errno 11001] getaddrinfo failed>

### C034 — Booking.com

Configured career URL: [https://jobs.booking.com/booking/jobs](https://jobs.booking.com/booking/jobs)

- [https://jobs.booking.com/booking/jobs](https://jobs.booking.com/booking/jobs): page reachable; HTTP 200. 

### C035 — Booz Allen Hamilton

Configured career URL: [https://bah.wd1.myworkdayjobs.com/BAH_Jobs](https://bah.wd1.myworkdayjobs.com/BAH_Jobs)

- [https://bah.wd1.myworkdayjobs.com/BAH_Jobs](https://bah.wd1.myworkdayjobs.com/BAH_Jobs): page reachable; HTTP 200. 

### C036 — Bosch

Configured career URL: [https://www.bosch.in/careers/](https://www.bosch.in/careers/)

- [https://www.bosch.in/careers/](https://www.bosch.in/careers/): page reachable; HTTP 200. 
- [https://www.bosch.in/our-company/bosch-in-india/](https://www.bosch.in/our-company/bosch-in-india/): page reachable; HTTP 200. 
- [https://www.bosch.in/spark-nxt-100-years-of-bosch-in-india.html](https://www.bosch.in/spark-nxt-100-years-of-bosch-in-india.html): page reachable; HTTP 200. 
- [https://www.bosch.in/our-company/bosch-in-india/](https://www.bosch.in/our-company/bosch-in-india/): page reachable; HTTP 200. 
- [https://www.boschrexroth.com/en/in/](https://www.boschrexroth.com/en/in/): page reachable; HTTP 200. 

### C037 — BP

Configured career URL: [https://www.bp.com/en/global/corporate/careers.html](https://www.bp.com/en/global/corporate/careers.html)

- [https://www.bp.com/en/global/corporate/careers.html](https://www.bp.com/en/global/corporate/careers.html): page reachable; HTTP 200. 
- [https://careers.bp.com/listing](https://careers.bp.com/listing): page reachable; HTTP 200. 
- [https://bp.avature.net/talentcommunity ](https://bp.avature.net/talentcommunity%20): page reachable; HTTP 200. 

### C038 — Broadridge

Configured career URL: [https://broadridge.com/careers](https://broadridge.com/careers)

- [https://broadridge.com/careers](https://broadridge.com/careers): page reachable; HTTP 200. 

### C039 — BT Group

Configured career URL: [https://bt.com/careers](https://bt.com/careers)

- [https://bt.com/careers](https://bt.com/careers): network/TLS error; HTTP n/a. <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1032)>

### C040 — Bupa

Configured career URL: [https://elvh.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2001](https://elvh.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2001)

- [https://elvh.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2001](https://elvh.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2001): page reachable; HTTP 200. 

### C041 — Caesars Entertainment

Configured career URL: [https://edmn.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1](https://edmn.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1)

- [https://edmn.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1](https://edmn.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1): page reachable; HTTP 200. 

### C042 — Capgemini

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C043 — Capital One

Configured career URL: [https://capitalone.com/tech/careers](https://capitalone.com/tech/careers)

- [https://capitalone.com/tech/careers](https://capitalone.com/tech/careers): HTTP error; HTTP 404. HTTP Error 404: Not Found

### C044 — Carelon Global Solutions

Configured career URL: [https://careers.elevancehealth.com](https://careers.elevancehealth.com)

- [https://careers.elevancehealth.com](https://careers.elevancehealth.com): page reachable; HTTP 200. 
- [https://careers.elevancehealth.com/jobs](https://careers.elevancehealth.com/jobs): page reachable; HTTP 200. 
- [https://careers.elevancehealth.com/ai-solutions-engineer-lead-senior/job/873BD08A57129F822477F39794D435FB](https://careers.elevancehealth.com/ai-solutions-engineer-lead-senior/job/873BD08A57129F822477F39794D435FB): page reachable; HTTP 200. 
- [https://elevancehealth.wd1.myworkdayjobs.com/ANT/job/GA-ATLANTA-740-W-PEACHTREE-ST-NW/AI-Solutions-Engineer-Lead-Senior_JR211739/apply](https://elevancehealth.wd1.myworkdayjobs.com/ANT/job/GA-ATLANTA-740-W-PEACHTREE-ST-NW/AI-Solutions-Engineer-Lead-Senior_JR211739/apply): page reachable; HTTP 200. 
- [https://careers.elevancehealth.com/aso-contract-admin-consultant/job/93E361CFEF18E5268C1346CAB457ACA7](https://careers.elevancehealth.com/aso-contract-admin-consultant/job/93E361CFEF18E5268C1346CAB457ACA7): page reachable; HTTP 200. 

### C045 — Cargill

Configured career URL: [https://careers.cargill.com/en](https://careers.cargill.com/en)

- [https://careers.cargill.com/en](https://careers.cargill.com/en): page reachable; HTTP 200. 
- [https://careers.cargill.com/professional-jobs](https://careers.cargill.com/professional-jobs): page reachable; HTTP 200. 
- [https://careers.cargill.com/hourly-pipeline-jobs](https://careers.cargill.com/hourly-pipeline-jobs): page reachable; HTTP 200. 
- [https://careers.cargill.com/en/job/uberlandia/senior-analyst-spend-and-market-analysis/23251/103270935472](https://careers.cargill.com/en/job/uberlandia/senior-analyst-spend-and-market-analysis/23251/103270935472): page reachable; HTTP 200. 
- [https://careers.cargill.com/campus-jobs](https://careers.cargill.com/campus-jobs): page reachable; HTTP 200. 

### C046 — Carrier

Configured career URL: [https://jobs.carrier.com](https://jobs.carrier.com)

- [https://jobs.carrier.com](https://jobs.carrier.com): network/TLS error; HTTP n/a. <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1032)>

### C047 — Charles Schwab

Configured career URL: [https://www.schwabjobs.com](https://www.schwabjobs.com)

- [https://www.schwabjobs.com](https://www.schwabjobs.com): page reachable; HTTP 200. 
- [https://www.schwabjobs.com/indianapolis-indiana](https://www.schwabjobs.com/indianapolis-indiana): page reachable; HTTP 200. 
- [https://www.schwabjobs.com/building-careers-indianapolis](https://www.schwabjobs.com/building-careers-indianapolis): page reachable; HTTP 200. 
- [https://www.schwabjobs.com/job/westlake/sr-manager-equity-compensation-planner/33727/102953490848](https://www.schwabjobs.com/job/westlake/sr-manager-equity-compensation-planner/33727/102953490848): page reachable; HTTP 200. 
- [https://www.schwabjobs.com/job/indianapolis/specialist-estates-services/33727/103170562800](https://www.schwabjobs.com/job/indianapolis/specialist-estates-services/33727/103170562800): page reachable; HTTP 200. 

### C048 — Charter Communications

Configured career URL: [https://jobs.spectrum.com](https://jobs.spectrum.com)

- [https://jobs.spectrum.com](https://jobs.spectrum.com): network/TLS error; HTTP n/a. <urlopen error [Errno 11001] getaddrinfo failed>

### C049 — Chevron

Configured career URL: [https://careers.chevron.com](https://careers.chevron.com)

- [https://careers.chevron.com](https://careers.chevron.com): page reachable; HTTP 200. 
- [https://careers.chevron.com/search-jobs](https://careers.chevron.com/search-jobs): page reachable; HTTP 200. 
- [https://careers.chevron.com](https://careers.chevron.com): page reachable; HTTP 200. 
- [https://careers.chevron.com/job/bengaluru/talent-acquisition-specialist/38138/101341422384](https://careers.chevron.com/job/bengaluru/talent-acquisition-specialist/38138/101341422384): page reachable; HTTP 200. 
- [https://careers.chevron.com/job/bengaluru/wells-engineer/38138/98691063856](https://careers.chevron.com/job/bengaluru/wells-engineer/38138/98691063856): page reachable; HTTP 200. 

### C050 — Cisco

Configured career URL: [https://jobs.cisco.com](https://jobs.cisco.com)

- [https://jobs.cisco.com](https://jobs.cisco.com): network/TLS error; HTTP n/a. <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1032)>

### C051 — Citi

Configured career URL: [https://jobs.citi.com](https://jobs.citi.com)

- [https://jobs.citi.com](https://jobs.citi.com): page reachable; HTTP 200. 
- [https://jobs.citi.com/search-jobs](https://jobs.citi.com/search-jobs): page reachable; HTTP 200. 
- [https://citi.eightfold.ai/careers/join?jtn_form_id=jtn-early-career](https://citi.eightfold.ai/careers/join?jtn_form_id=jtn-early-career): page reachable; HTTP 200. 
- [https://jobs.citi.com/search-jobs](https://jobs.citi.com/search-jobs): page reachable; HTTP 200. 
- [https://jobs.citi.com/job/houston/credit-officer-real-estate-underwriting/287/102161067904](https://jobs.citi.com/job/houston/credit-officer-real-estate-underwriting/287/102161067904): page reachable; HTTP 200. 

### C052 — CNH

Configured career URL: [https://join.cnh.com/](https://join.cnh.com/)

- [https://join.cnh.com/](https://join.cnh.com/): page reachable; HTTP 200. 

### C053 — CNO Financial

Configured career URL: [https://careers.cnoinc.com](https://careers.cnoinc.com)

- [https://careers.cnoinc.com](https://careers.cnoinc.com): page reachable; HTTP 200. 
- [https://careers.cnoinc.com/jobs/](https://careers.cnoinc.com/jobs/): page reachable; HTTP 200. 
- [https://cnoinc.wd5.myworkdayjobs.com/Careers/userHome](https://cnoinc.wd5.myworkdayjobs.com/Careers/userHome): page reachable; HTTP 200. 
- [https://cnoinc.wd5.myworkdayjobs.com/Careers/jobAlerts](https://cnoinc.wd5.myworkdayjobs.com/Careers/jobAlerts): page reachable; HTTP 200. 

### C054 — Coca-Cola

Configured career URL: [https://www.coca-colacompany.com/careers](https://www.coca-colacompany.com/careers)

- [https://www.coca-colacompany.com/careers](https://www.coca-colacompany.com/careers): page reachable; HTTP 200. 
- [https://careers.coca-colacompany.com/?store_id=India](https://careers.coca-colacompany.com/?store_id=India): page reachable; HTTP 200. 
- [https://www.coca-colacompany.com/careers/job-search/systemjobs](https://www.coca-colacompany.com/careers/job-search/systemjobs): page reachable; HTTP 200. 
- [https://www.coca-colacompany.com/careers/job-search/systemjobs](https://www.coca-colacompany.com/careers/job-search/systemjobs): page reachable; HTTP 200. 
- [https://www.coca-colacompany.com/careers/job-search/systemjobs/coca-cola-hbc](https://www.coca-colacompany.com/careers/job-search/systemjobs/coca-cola-hbc): HTTP error; HTTP 404. HTTP Error 404: Not Found

### C055 — Coforge

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C056 — Cognizant

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C057 — Cohere Health

Configured career URL: [https://job-boards.greenhouse.io/coherehealth](https://job-boards.greenhouse.io/coherehealth)

- [https://job-boards.greenhouse.io/coherehealth](https://job-boards.greenhouse.io/coherehealth): page reachable; HTTP 200. 
- [https://job-boards.greenhouse.io/coherehealth/jobs/7980595003](https://job-boards.greenhouse.io/coherehealth/jobs/7980595003): page reachable; HTTP 200. 
- [https://job-boards.greenhouse.io/coherehealth/jobs/7854046003](https://job-boards.greenhouse.io/coherehealth/jobs/7854046003): page reachable; HTTP 200. 
- [https://job-boards.greenhouse.io/coherehealth/jobs/7854316003](https://job-boards.greenhouse.io/coherehealth/jobs/7854316003): page reachable; HTTP 200. 
- [https://job-boards.greenhouse.io/coherehealth/jobs/7693376003](https://job-boards.greenhouse.io/coherehealth/jobs/7693376003): page reachable; HTTP 200. 

### C058 — Collabera

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C059 — Columbia Sportswear

Configured career URL: [https://www.columbiasportswearcompany.com/careers/](https://www.columbiasportswearcompany.com/careers/)

- [https://www.columbiasportswearcompany.com/careers/](https://www.columbiasportswearcompany.com/careers/): page reachable; HTTP 200. 
- [https://www.columbiasportswearcompany.com/careers/frequently-asked-questions](https://www.columbiasportswearcompany.com/careers/frequently-asked-questions): page reachable; HTTP 200. 
- [https://columbiasportswearcompany.wd5.myworkdayjobs.com/columbia_career_site](https://columbiasportswearcompany.wd5.myworkdayjobs.com/columbia_career_site): page reachable; HTTP 200. 

### C060 — Comcast

Configured career URL: [https://jobs.comcast.com](https://jobs.comcast.com)

- [https://jobs.comcast.com](https://jobs.comcast.com): page reachable; HTTP 200. 
- [https://jobs.comcast.com/search-jobs](https://jobs.comcast.com/search-jobs): page reachable; HTTP 200. 
- [https://jobs.comcast.com](https://jobs.comcast.com): page reachable; HTTP 200. 
- [https://jobs.comcast.com](https://jobs.comcast.com): page reachable; HTTP 200. 
- [https://jobs.comcast.com/search-jobs](https://jobs.comcast.com/search-jobs): page reachable; HTTP 200. 

### C061 — Commonwealth Bank

Configured career URL: [https://commbank.com.au/about-us/careers](https://commbank.com.au/about-us/careers)

- [https://commbank.com.au/about-us/careers](https://commbank.com.au/about-us/careers): page reachable; HTTP 200. 
- [https://www.commbank.com.au/about-us/careers/india.html?ei=india](https://www.commbank.com.au/about-us/careers/india.html?ei=india): page reachable; HTTP 200. 
- [https://cba.wd3.myworkdayjobs.com/CommBank_Careers?locationCountry=d903bb3fedad45039383f6de334ad4db](https://cba.wd3.myworkdayjobs.com/CommBank_Careers?locationCountry=d903bb3fedad45039383f6de334ad4db): page reachable; HTTP 200. 
- [https://www.commbank.com.au/about-us/careers/india.html?ei=india](https://www.commbank.com.au/about-us/careers/india.html?ei=india): page reachable; HTTP 200. 
- [https://www.commbank.com.au/about-us/careers/india.html?ei=india](https://www.commbank.com.au/about-us/careers/india.html?ei=india): page reachable; HTTP 200. 

### C062 — Conduent

Configured career URL: [https://careers.conduent.com/us/en/search-results?keywords=pega&from=0](https://careers.conduent.com/us/en/search-results?keywords=pega&from=0)

- [https://careers.conduent.com/us/en/search-results?keywords=pega&from=0](https://careers.conduent.com/us/en/search-results?keywords=pega&from=0): page reachable; HTTP 200. 

### C063 — Confluent

Configured career URL: [https://jobs.ashbyhq.com/confluent](https://jobs.ashbyhq.com/confluent)

- [https://jobs.ashbyhq.com/confluent](https://jobs.ashbyhq.com/confluent): page reachable; HTTP 200. 

### C064 — CSC

Configured career URL: [https://www.cscglobal.com/service/careers/](https://www.cscglobal.com/service/careers/)

- [https://www.cscglobal.com/service/careers/](https://www.cscglobal.com/service/careers/): page reachable; HTTP 200. 
- [https://www.cscglobal.com/service/careers/opportunities-in-india/](https://www.cscglobal.com/service/careers/opportunities-in-india/): page reachable; HTTP 200. 
- [https://hczw.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001](https://hczw.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001): page reachable; HTTP 200. 
- [https://hczw.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions?location=India&locationId=300000000361484&locationLevel=country&mode=location](https://hczw.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions?location=India&locationId=300000000361484&locationLevel=country&mode=location): page reachable; HTTP 200. 
- [https://hczw.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs?location=India&locationId=300000000361484&locationLevel=country&mode=location](https://hczw.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs?location=India&locationId=300000000361484&locationLevel=country&mode=location): page reachable; HTTP 200. 

### C065 — Cummins

Configured career URL: [https://cummins.jobs](https://cummins.jobs)

- [https://cummins.jobs](https://cummins.jobs): page reachable; HTTP 200. 
- [https://fa-espx-saasfaprod1.fa.ocs.oraclecloud.com/fscmUI/redwood/internalmobility/opportunitymarketplace](https://fa-espx-saasfaprod1.fa.ocs.oraclecloud.com/fscmUI/redwood/internalmobility/opportunitymarketplace): page reachable; HTTP 200. 

### C066 — CVS Health

Configured career URL: [https://jobs.cvshealth.com/us/en/home](https://jobs.cvshealth.com/us/en/home)

- [https://jobs.cvshealth.com/us/en/home](https://jobs.cvshealth.com/us/en/home): page reachable; HTTP 200. 

### C067 — Cyient

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C068 — Daimler Truck

Configured career URL: [https://jobsearch.daimlertruck.com/index.php?ac=search_result](https://jobsearch.daimlertruck.com/index.php?ac=search_result)

- [https://jobsearch.daimlertruck.com/index.php?ac=search_result](https://jobsearch.daimlertruck.com/index.php?ac=search_result): page reachable; HTTP 200. 

### C069 — Danske Bank

Configured career URL: [https://danskebank.com/Job](https://danskebank.com/Job)

- [https://danskebank.com/Job](https://danskebank.com/Job): page reachable; HTTP 200. 
- [https://ejqi.fa.ocs.oraclecloud.eu/hcmUI/CandidateExperience/en/sites/CX_1001/job/25338](https://ejqi.fa.ocs.oraclecloud.eu/hcmUI/CandidateExperience/en/sites/CX_1001/job/25338): page reachable; HTTP 200. 
- [https://ejqi.fa.ocs.oraclecloud.eu/hcmUI/CandidateExperience/en/sites/CX_1001/job/25341](https://ejqi.fa.ocs.oraclecloud.eu/hcmUI/CandidateExperience/en/sites/CX_1001/job/25341): page reachable; HTTP 200. 
- [https://ejqi.fa.ocs.oraclecloud.eu/hcmUI/CandidateExperience/en/sites/CX_1001/job/25213](https://ejqi.fa.ocs.oraclecloud.eu/hcmUI/CandidateExperience/en/sites/CX_1001/job/25213): page reachable; HTTP 200. 
- [https://ejqi.fa.ocs.oraclecloud.eu/hcmUI/CandidateExperience/en/sites/CX_1001/job/25380](https://ejqi.fa.ocs.oraclecloud.eu/hcmUI/CandidateExperience/en/sites/CX_1001/job/25380): page reachable; HTTP 200. 

### C070 — DBS Bank

Configured career URL: [https://dbs.wd3.myworkdayjobs.com/DBS_Careers](https://dbs.wd3.myworkdayjobs.com/DBS_Careers)

- [https://dbs.wd3.myworkdayjobs.com/DBS_Careers](https://dbs.wd3.myworkdayjobs.com/DBS_Careers): page reachable; HTTP 200. 

### C071 — Dell Technologies

Configured career URL: [https://enterpriseplatform.dell.com/hcmUI/CandidateExperience/en/sites/careers](https://enterpriseplatform.dell.com/hcmUI/CandidateExperience/en/sites/careers)

- [https://enterpriseplatform.dell.com/hcmUI/CandidateExperience/en/sites/careers](https://enterpriseplatform.dell.com/hcmUI/CandidateExperience/en/sites/careers): page reachable; HTTP 200. 

### C072 — Deloitte

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C073 — Deutsche Bank

Configured career URL: [https://careers.db.com](https://careers.db.com)

- [https://careers.db.com](https://careers.db.com): page reachable; HTTP 200. 

### C074 — Deutsche Telekom Digital Labs

Configured career URL: [https://www.telekom.com/en/telekom-as-an-employer](https://www.telekom.com/en/telekom-as-an-employer)

- [https://www.telekom.com/en/telekom-as-an-employer](https://www.telekom.com/en/telekom-as-an-employer): page reachable; HTTP 200. 

### C075 — DHL

Configured career URL: [https://careers.dhl.com](https://careers.dhl.com)

- [https://careers.dhl.com](https://careers.dhl.com): network/TLS error; HTTP n/a. <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1032)>

### C076 — DP World

Configured career URL: [https://www.dpworld.com/careers](https://www.dpworld.com/careers)

- [https://www.dpworld.com/careers](https://www.dpworld.com/careers): page reachable; HTTP 200. 
- [https://www.dpworld.com/en/about-us/our-locations/india](https://www.dpworld.com/en/about-us/our-locations/india): page reachable; HTTP 200. 
- [https://www.dpworld.com/en/about-us/our-locations/india/services](https://www.dpworld.com/en/about-us/our-locations/india/services): page reachable; HTTP 200. 
- [https://www.dpworld.com/en/about-us/leadership/india](https://www.dpworld.com/en/about-us/leadership/india): page reachable; HTTP 200. 

### C077 — DXC Technology

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C078 — EAI Systems

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C079 — Eaton

Configured career URL: [https://eaton.eightfold.ai/careers](https://eaton.eightfold.ai/careers)

- [https://eaton.eightfold.ai/careers](https://eaton.eightfold.ai/careers): page reachable; HTTP 200. 
- [https://eaton.eightfold.ai/careers?domain=eaton.com](https://eaton.eightfold.ai/careers?domain=eaton.com): page reachable; HTTP 200. 
- [https://app.eightfold.ai/careers?domain=eaton.com](https://app.eightfold.ai/careers?domain=eaton.com): page reachable; HTTP 200. 

### C080 — Eclatprime

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C081 — Empower

Configured career URL: [https://www.empower.com/careers](https://www.empower.com/careers)

- [https://www.empower.com/careers](https://www.empower.com/careers): page reachable; HTTP 200. 
- [https://jobs.empower.com/india](https://jobs.empower.com/india): page reachable; HTTP 200. 
- [https://jobs.empower.com/india-jobs](https://jobs.empower.com/india-jobs): page reachable; HTTP 200. 
- [https://jobs.empower.com/india](https://jobs.empower.com/india): page reachable; HTTP 200. 
- [https://jobs.empower.com/job/bengaluru/analyst-financial-planning-and-analysis-technology/42743/98556411568](https://jobs.empower.com/job/bengaluru/analyst-financial-planning-and-analysis-technology/42743/98556411568): page reachable; HTTP 200. 

### C082 — enGen

Configured career URL: [https://careers.highmarkhealth.org](https://careers.highmarkhealth.org)

- [https://careers.highmarkhealth.org](https://careers.highmarkhealth.org): page reachable; HTTP 200. 
- [https://careers.highmarkhealth.org/jobs](https://careers.highmarkhealth.org/jobs): page reachable; HTTP 200. 
- [https://careers.highmarkhealth.org/jobs?filter%5Bcategory%5D%5B0%5D=Clinical%20Services&filter%5Bcategory%5D%5B1%5D=Direct%20Patient%20Care%20Providers&filter%5Bcategory%5D%5B2%5D=Emergency%20Services&filter%5Bcategory%5D%5B3%5D=Facilities%20Management%20%26%20Real%20Estate&filter%5Bcategory%5D%5B4%5D=Food%2FNutrition&filter%5Bcategory%5D%5B5%5D=Intern&filter%5Bcategory%5D%5B6%5D=Internal%20Staffing%20Team&filter%5Bcategory%5D%5B7%5D=Laboratory&filter%5Bcategory%5D%5B8%5D=Nursing&filter%5Bcategory%5D%5B9%5D=Patient%20Support&filter%5Bcategory%5D%5B10%5D=Pharmacy&filter%5Bcategory%5D%5B11%5D=Rehab&filter%5Bcategory%5D%5B12%5D=Research&filter%5Bcategory%5D%5B13%5D=Tech](https://careers.highmarkhealth.org/jobs?filter%5Bcategory%5D%5B0%5D=Clinical%20Services&filter%5Bcategory%5D%5B1%5D=Direct%20Patient%20Care%20Providers&filter%5Bcategory%5D%5B2%5D=Emergency%20Services&filter%5Bcategory%5D%5B3%5D=Facilities%20Management%20%26%20Real%20Estate&filter%5Bcategory%5D%5B4%5D=Food%2FNutrition&filter%5Bcategory%5D%5B5%5D=Intern&filter%5Bcategory%5D%5B6%5D=Internal%20Staffing%20Team&filter%5Bcategory%5D%5B7%5D=Laboratory&filter%5Bcategory%5D%5B8%5D=Nursing&filter%5Bcategory%5D%5B9%5D=Patient%20Support&filter%5Bcategory%5D%5B10%5D=Pharmacy&filter%5Bcategory%5D%5B11%5D=Rehab&filter%5Bcategory%5D%5B12%5D=Research&filter%5Bcategory%5D%5B13%5D=Tech): page reachable; HTTP 200. 
- [https://careers.highmarkhealth.org/associate-print-shop-operator-wed-sat-3pm-1-30am/job/J290411](https://careers.highmarkhealth.org/associate-print-shop-operator-wed-sat-3pm-1-30am/job/J290411): page reachable; HTTP 200. 
- [https://careers.highmarkhealth.org/assistant-nurse-manager-trauma-medsurg/job/J291736](https://careers.highmarkhealth.org/assistant-nurse-manager-trauma-medsurg/job/J291736): page reachable; HTTP 200. 

### C083 — EPAM Systems

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C084 — Estes Express

Configured career URL: [https://work4estes.com/en/sites/work4estes](https://work4estes.com/en/sites/work4estes)

- [https://work4estes.com/en/sites/work4estes](https://work4estes.com/en/sites/work4estes): page reachable; HTTP 200. 

### C085 — Evernorth

Configured career URL: [https://jobs.thecignagroup.com](https://jobs.thecignagroup.com)

- [https://jobs.thecignagroup.com](https://jobs.thecignagroup.com): page reachable; HTTP 200. 
- [https://jobs.thecignagroup.com/us/en/search-results](https://jobs.thecignagroup.com/us/en/search-results): page reachable; HTTP 200. 
- [https://jobs.thecignagroup.com/us/en/cigna-healthcare-search-results](https://jobs.thecignagroup.com/us/en/cigna-healthcare-search-results): page reachable; HTTP 200. 

### C086 — Eviden

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C087 — Evoke Technologies

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C088 — ExxonMobil

Configured career URL: [https://jobs.exxonmobil.com](https://jobs.exxonmobil.com)

- [https://jobs.exxonmobil.com](https://jobs.exxonmobil.com): page reachable; HTTP 200. 

### C089 — EY

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C090 — FedEx

Configured career URL: [https://careers.fedex.com](https://careers.fedex.com)

- [https://careers.fedex.com](https://careers.fedex.com): page reachable; HTTP 200. 
- [https://careers.fedex.com/jobs](https://careers.fedex.com/jobs): page reachable; HTTP 200. 
- [https://careers.fedex.com/lm016-operations-handler/job/66AC4EEC404159A8FCDD12D813DCC564](https://careers.fedex.com/lm016-operations-handler/job/66AC4EEC404159A8FCDD12D813DCC564): page reachable; HTTP 200. 
- [https://careers.fedex.com/material-handler-part-time-warehouse-like/job/P25-93862-23](https://careers.fedex.com/material-handler-part-time-warehouse-like/job/P25-93862-23): page reachable; HTTP 200. 

### C091 — Fidelity Investments

Configured career URL: [https://india.fidelity.com/careers/](https://india.fidelity.com/careers/)

- [https://india.fidelity.com/careers/](https://india.fidelity.com/careers/): page reachable; HTTP 200. 

### C092 — Fidelity National Financial

Configured career URL: [https://www.fnf.com/careers](https://www.fnf.com/careers)

- [https://www.fnf.com/careers](https://www.fnf.com/careers): page reachable; HTTP 200. 
- [https://fntg.wd5.myworkdayjobs.com/FNF-Careers](https://fntg.wd5.myworkdayjobs.com/FNF-Careers): page reachable; HTTP 200. 

### C093 — First Citizens Bank

Configured career URL: [https://jobs.firstcitizens.com](https://jobs.firstcitizens.com)

- [https://jobs.firstcitizens.com](https://jobs.firstcitizens.com): page reachable; HTTP 200. 
- [https://jobs.firstcitizens.com/jobs](https://jobs.firstcitizens.com/jobs): page reachable; HTTP 200. 

### C094 — FIS

Configured career URL: [https://careers.fisglobal.com/us/en](https://careers.fisglobal.com/us/en)

- [https://careers.fisglobal.com/us/en](https://careers.fisglobal.com/us/en): page reachable; HTTP 200. 

### C095 — Fiserv

Configured career URL: [https://www.careers.fiserv.com](https://www.careers.fiserv.com)

- [https://www.careers.fiserv.com](https://www.careers.fiserv.com): page reachable; HTTP 200. 
- [https://careers.fiserv.com/us/en/search-results](https://careers.fiserv.com/us/en/search-results): page reachable; HTTP 200. 

### C096 — Ford

Configured career URL: [https://corporate.ford.com/careers.html](https://corporate.ford.com/careers.html)

- [https://corporate.ford.com/careers.html](https://corporate.ford.com/careers.html): HTTP error; HTTP 403. HTTP Error 403: Forbidden

### C097 — Ford Credit

Configured career URL: [https://corporate.ford.com/careers.html](https://corporate.ford.com/careers.html)

- [https://corporate.ford.com/careers.html](https://corporate.ford.com/careers.html): HTTP error; HTTP 403. HTTP Error 403: Forbidden

### C098 — fusionAIx

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C099 — GE Aerospace

Configured career URL: [https://geaerospace.wd5.myworkdayjobs.com/GE_ExternalSite](https://geaerospace.wd5.myworkdayjobs.com/GE_ExternalSite)

- [https://geaerospace.wd5.myworkdayjobs.com/GE_ExternalSite](https://geaerospace.wd5.myworkdayjobs.com/GE_ExternalSite): page reachable; HTTP 200. 

### C100 — GE HealthCare

Configured career URL: [https://careers.gehealthcare.com](https://careers.gehealthcare.com)

- [https://careers.gehealthcare.com](https://careers.gehealthcare.com): page reachable; HTTP 200. 
- [https://careers.gehealthcare.com/global/en/search-results](https://careers.gehealthcare.com/global/en/search-results): page reachable; HTTP 200. 

### C101 — GE Vernova

Configured career URL: [https://gevernova.wd5.myworkdayjobs.com/Vernova_ExternalSite](https://gevernova.wd5.myworkdayjobs.com/Vernova_ExternalSite)

- [https://gevernova.wd5.myworkdayjobs.com/Vernova_ExternalSite](https://gevernova.wd5.myworkdayjobs.com/Vernova_ExternalSite): page reachable; HTTP 200. 

### C102 — General Motors

Configured career URL: [https://search-careers.gm.com](https://search-careers.gm.com)

- [https://search-careers.gm.com](https://search-careers.gm.com): page reachable; HTTP 200. 
- [https://search-careers.gm.com/en/locations/india/](https://search-careers.gm.com/en/locations/india/): page reachable; HTTP 200. 
- [https://search-careers.gm.com/en/jobs/](https://search-careers.gm.com/en/jobs/): HTTP error; HTTP 403. HTTP Error 403: Forbidden
- [https://search-careers.gm.com/en/locations/india/](https://search-careers.gm.com/en/locations/india/): page reachable; HTTP 200. 
- [https://search-careers.gm.com/es/ubicaciones/india/](https://search-careers.gm.com/es/ubicaciones/india/): not retried after host refusal; HTTP n/a. 

### C103 — Genpact

Configured career URL: [https://genpact.wd108.myworkdayjobs.com/External_Careers](https://genpact.wd108.myworkdayjobs.com/External_Careers)

- [https://genpact.wd108.myworkdayjobs.com/External_Careers](https://genpact.wd108.myworkdayjobs.com/External_Careers): page reachable; HTTP 200. 

### C104 — Global Payments

Configured career URL: [https://jobs.globalpayments.com](https://jobs.globalpayments.com)

- [https://jobs.globalpayments.com](https://jobs.globalpayments.com): network/TLS error; HTTP n/a. <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1032)>

### C105 — Goldman Sachs

Configured career URL: [https://higher.gs.com/results](https://higher.gs.com/results)

- [https://higher.gs.com/results](https://higher.gs.com/results): page reachable; HTTP 200. 

### C106 — HCL Technologies

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C107 — HDFC Bank

Configured career URL: [https://www.hdfc.bank.in/careers](https://www.hdfc.bank.in/careers)

- [https://www.hdfc.bank.in/careers](https://www.hdfc.bank.in/careers): page reachable; HTTP 200. 
- [https://applyonline.hdfc.bank.in/cards/credit-cards.html?channelsource=iocl&LGCode=MKTG&mc_id=website_TAN_CC_Footer_tele_assist&icid=website_TAN_organic_IOCL_CC_footer_teke_assist](https://applyonline.hdfc.bank.in/cards/credit-cards.html?channelsource=iocl&LGCode=MKTG&mc_id=website_TAN_CC_Footer_tele_assist&icid=website_TAN_organic_IOCL_CC_footer_teke_assist): page reachable; HTTP 200. 
- [https://hdfcbank.ripplehire.com/candidate/careers](https://hdfcbank.ripplehire.com/candidate/careers): page reachable; HTTP 200. 
- [https://www.hdfc.bank.in/credit-cards/indianoil-hdfc-bank-credit-card](https://www.hdfc.bank.in/credit-cards/indianoil-hdfc-bank-credit-card): page reachable; HTTP 200. 
- [https://www.hdfc.bank.in/prepaid-cards/one-pune-prepaid-card](https://www.hdfc.bank.in/prepaid-cards/one-pune-prepaid-card): page reachable; HTTP 200. 

### C108 — Hexaware

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C109 — Honeywell

Configured career URL: [https://careers.honeywell.com/en/sites/Honeywell](https://careers.honeywell.com/en/sites/Honeywell)

- [https://careers.honeywell.com/en/sites/Honeywell](https://careers.honeywell.com/en/sites/Honeywell): page reachable; HTTP 200. 

### C110 — Horizontal

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C111 — HSBC

Configured career URL: [https://mycareer.hsbc.com/en_GB/external/SearchJobs/?q=pega&locationsearch=India](https://mycareer.hsbc.com/en_GB/external/SearchJobs/?q=pega&locationsearch=India)

- [https://mycareer.hsbc.com/en_GB/external/SearchJobs/?q=pega&locationsearch=India](https://mycareer.hsbc.com/en_GB/external/SearchJobs/?q=pega&locationsearch=India): page reachable; HTTP 200. 
- [https://mycareer.hsbc.com/en_GB/external/SearchJobs/?q=pega&locationsearch=India](https://mycareer.hsbc.com/en_GB/external/SearchJobs/?q=pega&locationsearch=India): page reachable; HTTP 200. 
- [https://mycareer.hsbc.com/es_ES/external/SearchJobs/?q=pega&locationsearch=India](https://mycareer.hsbc.com/es_ES/external/SearchJobs/?q=pega&locationsearch=India): page reachable; HTTP 200. 
- [https://mycareer.hsbc.com/fr_CA/external/SearchJobs/?q=pega&locationsearch=India](https://mycareer.hsbc.com/fr_CA/external/SearchJobs/?q=pega&locationsearch=India): page reachable; HTTP 200. 
- [https://mycareer.hsbc.com/fr_FR/external/SearchJobs/?q=pega&locationsearch=India](https://mycareer.hsbc.com/fr_FR/external/SearchJobs/?q=pega&locationsearch=India): page reachable; HTTP 200. 

### C112 — IBM

Configured career URL: Not configured

- [https://www.ibm.com/in-en/careers](https://www.ibm.com/in-en/careers): page reachable; HTTP 200. 
- [https://www.ibm.com/careers/search?location=India&remote=true](https://www.ibm.com/careers/search?location=India&remote=true): page reachable; HTTP 200. 
- [https://careers.ibm.com/en_US/globalform?source=WEB_Search_INDIA](https://careers.ibm.com/en_US/globalform?source=WEB_Search_INDIA): page reachable; HTTP 200. 
- [https://careers.ibm.com/en_US/careers/JobAlerts?source=WEB_Search_INDIA](https://careers.ibm.com/en_US/careers/JobAlerts?source=WEB_Search_INDIA): page reachable; HTTP 202. 
- [https://www.ibm.com/in-en/careers/search](https://www.ibm.com/in-en/careers/search): page reachable; HTTP 200. 

### C113 — ICICI Bank

Configured career URL: [https://careers.icici.bank.in/CareerApplicant/Career/Home/](https://careers.icici.bank.in/CareerApplicant/Career/Home/)

- [https://careers.icici.bank.in/CareerApplicant/Career/Home/](https://careers.icici.bank.in/CareerApplicant/Career/Home/): page reachable; HTTP 200. 

### C114 — IFFCO Tokio

Configured career URL: [https://www.iffcotokio.co.in/about-us/careers](https://www.iffcotokio.co.in/about-us/careers)

- [https://www.iffcotokio.co.in/about-us/careers](https://www.iffcotokio.co.in/about-us/careers): page reachable; HTTP 200. 

### C115 — IKEA

Configured career URL: [https://jobs.ikea.com/en/search-jobs/pega/22908/1](https://jobs.ikea.com/en/search-jobs/pega/22908/1)

- [https://jobs.ikea.com/en/search-jobs/pega/22908/1](https://jobs.ikea.com/en/search-jobs/pega/22908/1): page reachable; HTTP 200. 
- [https://jobs.ikea.com/en/search-jobs/pega/22908/1](https://jobs.ikea.com/en/search-jobs/pega/22908/1): page reachable; HTTP 200. 
- [https://jobs.ikea.com/en/search-jobs/pega/22908/1](https://jobs.ikea.com/en/search-jobs/pega/22908/1): page reachable; HTTP 200. 
- [https://jobs.ikea.com/en/search-jobs/pega/22908/1](https://jobs.ikea.com/en/search-jobs/pega/22908/1): page reachable; HTTP 200. 
- [https://jobs.ikea.com/en/search-jobs/perk/22908/1/1](https://jobs.ikea.com/en/search-jobs/perk/22908/1/1): page reachable; HTTP 200. 

### C116 — Inadev

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C117 — Infosys

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C118 — ING

Configured career URL: [https://www.ing.jobs](https://www.ing.jobs)

- [https://www.ing.jobs](https://www.ing.jobs): network/TLS error; HTTP n/a. <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1032)>

### C119 — Innova ESI

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C120 — Intel

Configured career URL: [https://jobs.intel.com](https://jobs.intel.com)

- [https://jobs.intel.com](https://jobs.intel.com): network/TLS error; HTTP n/a. <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1032)>

### C121 — ITC Limited

Configured career URL: [https://itcportal.com/careers.html](https://itcportal.com/careers.html)

- [https://itcportal.com/careers.html](https://itcportal.com/careers.html): page reachable; HTTP 200. 

### C122 — JLR

Configured career URL: [https://www.jaguarlandrovercareers.com](https://www.jaguarlandrovercareers.com)

- [https://www.jaguarlandrovercareers.com](https://www.jaguarlandrovercareers.com): page reachable; HTTP 200. 

### C123 — John Deere

Configured career URL: [https://www.deere.com/en-us/our-company/careers](https://www.deere.com/en-us/our-company/careers)

- [https://www.deere.com/en-us/our-company/careers](https://www.deere.com/en-us/our-company/careers): page reachable; HTTP 200. 

### C124 — John Deere Financial

Configured career URL: [https://www.deere.com/en/our-company/john-deere-careers/](https://www.deere.com/en/our-company/john-deere-careers/)

- [https://www.deere.com/en/our-company/john-deere-careers/](https://www.deere.com/en/our-company/john-deere-careers/): page reachable; HTTP 200. 

### C125 — Johnson & Johnson

Configured career URL: [https://careers.jnj.com](https://careers.jnj.com)

- [https://careers.jnj.com](https://careers.jnj.com): page reachable; HTTP 200. 
- [https://www.careers.jnj.com/en/employee-stories/professional-development/build-global-skills-from-bengaluru-early-career-opportunities-at-jj/](https://www.careers.jnj.com/en/employee-stories/professional-development/build-global-skills-from-bengaluru-early-career-opportunities-at-jj/): page reachable; HTTP 200. 
- [https://www.careers.jnj.com/en/jobs/saved-jobs/](https://www.careers.jnj.com/en/jobs/saved-jobs/): page reachable; HTTP 200. 
- [https://www.careers.jnj.com/en/employee-stories/professional-development/build-global-skills-from-bengaluru-early-career-opportunities-at-jj/](https://www.careers.jnj.com/en/employee-stories/professional-development/build-global-skills-from-bengaluru-early-career-opportunities-at-jj/): page reachable; HTTP 200. 
- [https://www.careers.jnj.com/zh-cn/employee-stories/professional-development/build-global-skills-from-bengaluru-early-career-opportunities-at-jj/](https://www.careers.jnj.com/zh-cn/employee-stories/professional-development/build-global-skills-from-bengaluru-early-career-opportunities-at-jj/): page reachable; HTTP 200. 

### C126 — Johnson Controls

Configured career URL: [https://jobs.johnsoncontrols.com](https://jobs.johnsoncontrols.com)

- [https://jobs.johnsoncontrols.com](https://jobs.johnsoncontrols.com): page reachable; HTTP 200. 
- [https://jobs.johnsoncontrols.com/job-search](https://jobs.johnsoncontrols.com/job-search): page reachable; HTTP 200. 
- [https://jobs.johnsoncontrols.com/job-search?production_JCI_jobs%5BrefinementList%5D%5Bparent_category%5D%5B0%5D=Digital](https://jobs.johnsoncontrols.com/job-search?production_JCI_jobs%5BrefinementList%5D%5Bparent_category%5D%5B0%5D=Digital): page reachable; HTTP 200. 
- [https://jobs.johnsoncontrols.com/job-search?production_JCI_jobs%5BrefinementList%5D%5Bparent_category%5D%5B0%5D=Engineering](https://jobs.johnsoncontrols.com/job-search?production_JCI_jobs%5BrefinementList%5D%5Bparent_category%5D%5B0%5D=Engineering): page reachable; HTTP 200. 
- [https://jobs.johnsoncontrols.com/job-search?production_JCI_jobs%5BrefinementList%5D%5Bparent_category%5D%5B0%5D=Operations](https://jobs.johnsoncontrols.com/job-search?production_JCI_jobs%5BrefinementList%5D%5Bparent_category%5D%5B0%5D=Operations): page reachable; HTTP 200. 

### C127 — JPMorganChase

Configured career URL: [https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions?keyword=pega&location=India](https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions?keyword=pega&location=India)

- [https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions?keyword=pega&location=India](https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions?keyword=pega&location=India): page reachable; HTTP 200. 

### C128 — Jyotirgamay Solutions

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C129 — Ketan Software

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C130 — Komatsu

Configured career URL: [https://www.komatsu.com/en-us/careers](https://www.komatsu.com/en-us/careers)

- [https://www.komatsu.com/en-us/careers](https://www.komatsu.com/en-us/careers): page reachable; HTTP 200. 

### C131 — Kotak Mahindra Bank

Configured career URL: [https://www.kotak.com/en/about-us/careers.html](https://www.kotak.com/en/about-us/careers.html)

- [https://www.kotak.com/en/about-us/careers.html](https://www.kotak.com/en/about-us/careers.html): page reachable; HTTP 200. 
- [https://www.kotak.bank.in/en/personal-banking/nri/cards/debit-cards/rupay-india-debit-card.html](https://www.kotak.bank.in/en/personal-banking/nri/cards/debit-cards/rupay-india-debit-card.html): page reachable; HTTP 200. 
- [https://fastag.kotak.bank.in/SR/](https://fastag.kotak.bank.in/SR/): page reachable; HTTP 200. 
- [https://www.kotak.bank.in/en/personal-banking/nri/cards/debit-cards/rupay-india-debit-card/features.html](https://www.kotak.bank.in/en/personal-banking/nri/cards/debit-cards/rupay-india-debit-card/features.html): page reachable; HTTP 200. 
- [https://www.kotak.bank.in/en/personal-banking/nri/cards/debit-cards/rupay-india-debit-card/eligibility.html](https://www.kotak.bank.in/en/personal-banking/nri/cards/debit-cards/rupay-india-debit-card/eligibility.html): page reachable; HTTP 200. 

### C132 — KPMG

Configured career URL: [https://ejgk.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_3](https://ejgk.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_3)

- [https://ejgk.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_3](https://ejgk.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_3): page reachable; HTTP 200. 

### C133 — Levi Strauss & Co.

Configured career URL: [https://levistraussandco.wd5.myworkdayjobs.com/External](https://levistraussandco.wd5.myworkdayjobs.com/External)

- [https://levistraussandco.wd5.myworkdayjobs.com/External](https://levistraussandco.wd5.myworkdayjobs.com/External): page reachable; HTTP 200. 

### C134 — Liberty Mutual

Configured career URL: [https://jobs.libertymutualgroup.com/](https://jobs.libertymutualgroup.com/)

- [https://jobs.libertymutualgroup.com/](https://jobs.libertymutualgroup.com/): page reachable; HTTP 200. 
- [https://searchjobs.libertymutualgroup.com/careers](https://searchjobs.libertymutualgroup.com/careers): page reachable; HTTP 200. 
- [https://searchjobs.libertymutualgroup.com/careers?elementor_library=elementor-header-426&elementor-preview=426&ver=1692974535](https://searchjobs.libertymutualgroup.com/careers?elementor_library=elementor-header-426&elementor-preview=426&ver=1692974535): page reachable; HTTP 200. 
- [https://jobs.libertymutualgroup.com/careers/digital-technology](https://jobs.libertymutualgroup.com/careers/digital-technology): page reachable; HTTP 200. 

### C135 — Lloyds Banking Group

Configured career URL: [https://lloydsbankinggrouptalent.com](https://lloydsbankinggrouptalent.com)

- [https://lloydsbankinggrouptalent.com](https://lloydsbankinggrouptalent.com): page reachable; HTTP 200. 

### C136 — Lockheed Martin

Configured career URL: [https://lockheedmartinjobs.com](https://lockheedmartinjobs.com)

- [https://lockheedmartinjobs.com](https://lockheedmartinjobs.com): page reachable; HTTP 200. 

### C137 — Lowe's

Configured career URL: [https://talent.lowes.com](https://talent.lowes.com)

- [https://talent.lowes.com](https://talent.lowes.com): page reachable; HTTP 200. 

### C138 — LPL Financial

Configured career URL: [https://career.lpl.com/](https://career.lpl.com/)

- [https://career.lpl.com/](https://career.lpl.com/): page reachable; HTTP 200. 
- [https://career.lpl.com/search-results](https://career.lpl.com/search-results): page reachable; HTTP 200. 

### C139 — LTIMindtree

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C140 — Lufthansa Systems

Configured career URL: [https://www.lhsystems.com/career](https://www.lhsystems.com/career)

- [https://www.lhsystems.com/career](https://www.lhsystems.com/career): page reachable; HTTP 200. 
- [https://www.lhsystems.com/company/our-subsidiaries/lufthansa-systems-india](https://www.lhsystems.com/company/our-subsidiaries/lufthansa-systems-india): page reachable; HTTP 200. 

### C141 — Maantic

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C142 — Macquarie

Configured career URL: [https://mq.wd3.myworkdayjobs.com/CareersatMQ](https://mq.wd3.myworkdayjobs.com/CareersatMQ)

- [https://mq.wd3.myworkdayjobs.com/CareersatMQ](https://mq.wd3.myworkdayjobs.com/CareersatMQ): page reachable; HTTP 200. 

### C143 — Macy's

Configured career URL: [https://ebwh.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001](https://ebwh.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001)

- [https://ebwh.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001](https://ebwh.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001): page reachable; HTTP 200. 

### C144 — Maersk

Configured career URL: [https://maersk.com/careers](https://maersk.com/careers)

- [https://maersk.com/careers](https://maersk.com/careers): page reachable; HTTP 200. 

### C145 — Manulife

Configured career URL: [https://manulife.wd3.myworkdayjobs.com/MFCJH_Jobs](https://manulife.wd3.myworkdayjobs.com/MFCJH_Jobs)

- [https://manulife.wd3.myworkdayjobs.com/MFCJH_Jobs](https://manulife.wd3.myworkdayjobs.com/MFCJH_Jobs): page reachable; HTTP 200. 

### C146 — Marriott

Configured career URL: [https://ejwl.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX](https://ejwl.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX)

- [https://ejwl.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX](https://ejwl.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX): page reachable; HTTP 200. 

### C147 — Marsh McLennan

Configured career URL: [https://careers.marsh.com/global/en](https://careers.marsh.com/global/en)

- [https://careers.marsh.com/global/en](https://careers.marsh.com/global/en): page reachable; HTTP 200. 

### C148 — MassMutual

Configured career URL: [https://careers.massmutual.com](https://careers.massmutual.com)

- [https://careers.massmutual.com](https://careers.massmutual.com): page reachable; HTTP 200. 
- [https://careers.massmutualindia.com/](https://careers.massmutualindia.com/): page reachable; HTTP 200. 
- [https://careers.massmutual.com/search-jobs](https://careers.massmutual.com/search-jobs): page reachable; HTTP 200. 
- [https://careers.massmutualindia.com/search-jobs](https://careers.massmutualindia.com/search-jobs): page reachable; HTTP 200. 
- [https://careers.massmutualindia.com/](https://careers.massmutualindia.com/): page reachable; HTTP 200. 

### C149 — Mastech Holdings

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C150 — Mastercard

Configured career URL: [https://careers.mastercard.com](https://careers.mastercard.com)

- [https://careers.mastercard.com](https://careers.mastercard.com): page reachable; HTTP 200. 

### C151 — Maximus

Configured career URL: [https://maximus.avature.net/careers/SearchJobs/pega?listFilterMode=1](https://maximus.avature.net/careers/SearchJobs/pega?listFilterMode=1)

- [https://maximus.avature.net/careers/SearchJobs/pega?listFilterMode=1](https://maximus.avature.net/careers/SearchJobs/pega?listFilterMode=1): page reachable; HTTP 200. 
- [https://maximus.avature.net/careers/SearchJobs/pega?listFilterMode=1](https://maximus.avature.net/careers/SearchJobs/pega?listFilterMode=1): page reachable; HTTP 200. 
- [https://maximus.avature.net/careers/SearchJobs](https://maximus.avature.net/careers/SearchJobs): page reachable; HTTP 200. 
- [https://maximus.avature.net/careers/SearchJobs](https://maximus.avature.net/careers/SearchJobs): page reachable; HTTP 200. 
- [https://maximus.avature.net/careers/ApplicationMethods?folderId=44255](https://maximus.avature.net/careers/ApplicationMethods?folderId=44255): page reachable; HTTP 200. 

### C152 — Medtronic

Configured career URL: [https://medtronic.wd1.myworkdayjobs.com/MedtronicCareers](https://medtronic.wd1.myworkdayjobs.com/MedtronicCareers)

- [https://medtronic.wd1.myworkdayjobs.com/MedtronicCareers](https://medtronic.wd1.myworkdayjobs.com/MedtronicCareers): page reachable; HTTP 200. 

### C153 — Mercedes-Benz Group

Configured career URL: [https://jobs.mercedes-benz.com](https://jobs.mercedes-benz.com)

- [https://jobs.mercedes-benz.com](https://jobs.mercedes-benz.com): network/TLS error; HTTP n/a. <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1032)>

### C154 — Mercedes-Benz Mobility

Configured career URL: [https://jobs.mercedes-benz.com](https://jobs.mercedes-benz.com)

- [https://jobs.mercedes-benz.com](https://jobs.mercedes-benz.com): network/TLS error; HTTP n/a. <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1032)>

### C155 — Mercedes-Benz Research and Development India

Configured career URL: [https://jobs.mercedes-benz.com](https://jobs.mercedes-benz.com)

- [https://jobs.mercedes-benz.com](https://jobs.mercedes-benz.com): network/TLS error; HTTP n/a. <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1032)>

### C156 — Merck

Configured career URL: [https://jobs.merck.com](https://jobs.merck.com)

- [https://jobs.merck.com](https://jobs.merck.com): page reachable; HTTP 200. 

### C157 — Merkle

Configured career URL: [https://dentsuaegis.wd3.myworkdayjobs.com/DAN_GLOBAL](https://dentsuaegis.wd3.myworkdayjobs.com/DAN_GLOBAL)

- [https://dentsuaegis.wd3.myworkdayjobs.com/DAN_GLOBAL](https://dentsuaegis.wd3.myworkdayjobs.com/DAN_GLOBAL): page reachable; HTTP 200. 

### C158 — MetLife

Configured career URL: [https://www.metlifecareers.com/en_US/ml](https://www.metlifecareers.com/en_US/ml)

- [https://www.metlifecareers.com/en_US/ml](https://www.metlifecareers.com/en_US/ml): page reachable; HTTP 200. 
- [https://www.metlifecareers.com/en_US/ml/SearchJobs](https://www.metlifecareers.com/en_US/ml/SearchJobs): page reachable; HTTP 200. 
- [https://metlife.avature.net/eventlisting](https://metlife.avature.net/eventlisting): page reachable; HTTP 200. 
- [https://www.metlifecareers.com/en_US/ml/SearchJobs](https://www.metlifecareers.com/en_US/ml/SearchJobs): page reachable; HTTP 200. 
- [https://www.metlifecareers.com/es_ES/ml/SearchJobs](https://www.metlifecareers.com/es_ES/ml/SearchJobs): page reachable; HTTP 200. 

### C159 — Mizuho Financial Group

Configured career URL: [https://www.mizuhogroup.com/careers](https://www.mizuhogroup.com/careers)

- [https://www.mizuhogroup.com/careers](https://www.mizuhogroup.com/careers): page reachable; HTTP 200. 
- [https://www.mizuhogroup.com/asia-pacific/india](https://www.mizuhogroup.com/asia-pacific/india): page reachable; HTTP 200. 
- [https://www.mizuhogroup.com/asia-pacific/india/about-home](https://www.mizuhogroup.com/asia-pacific/india/about-home): page reachable; HTTP 200. 
- [https://www.mizuhogroup.com/asia-pacific/india/about?tab=about-us](https://www.mizuhogroup.com/asia-pacific/india/about?tab=about-us): page reachable; HTTP 200. 

### C160 — Mizuho Global Services

Configured career URL: [https://www.mizuhogroup.com/careers](https://www.mizuhogroup.com/careers)

- [https://www.mizuhogroup.com/careers](https://www.mizuhogroup.com/careers): page reachable; HTTP 200. 
- [https://www.mizuhogroup.com/asia-pacific/india](https://www.mizuhogroup.com/asia-pacific/india): page reachable; HTTP 200. 
- [https://www.mizuhogroup.com/asia-pacific/india/about-home](https://www.mizuhogroup.com/asia-pacific/india/about-home): page reachable; HTTP 200. 
- [https://www.mizuhogroup.com/asia-pacific/india/about?tab=about-us](https://www.mizuhogroup.com/asia-pacific/india/about?tab=about-us): page reachable; HTTP 200. 

### C161 — Mondelez

Configured career URL: [https://www.mondelezinternational.com/careers/index.html](https://www.mondelezinternational.com/careers/index.html)

- [https://www.mondelezinternational.com/careers/index.html](https://www.mondelezinternational.com/careers/index.html): page reachable; HTTP 200. 
- [https://www.mondelezinternational.com/india/](https://www.mondelezinternational.com/india/): page reachable; HTTP 200. 
- [https://www.mondelezinternational.com/careers/jobs/](https://www.mondelezinternational.com/careers/jobs/): page reachable; HTTP 200. 
- [https://www.mondelezinternational.com/careers/stories/?filter=india/](https://www.mondelezinternational.com/careers/stories/?filter=india/): page reachable; HTTP 200. 
- [https://www.mondelezinternational.com/india/](https://www.mondelezinternational.com/india/): page reachable; HTTP 200. 

### C162 — Morgan Stanley

Configured career URL: [https://morganstanley.com/careers](https://morganstanley.com/careers)

- [https://morganstanley.com/careers](https://morganstanley.com/careers): page reachable; HTTP 200. 

### C163 — Mphasis

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C164 — MUFG

Configured career URL: [https://www.mufg.jp/english/careers/index.html](https://www.mufg.jp/english/careers/index.html)

- [https://www.mufg.jp/english/careers/index.html](https://www.mufg.jp/english/careers/index.html): page reachable; HTTP 200. 
- [https://mufgub.wd3.myworkdayjobs.com/MUFG-Careers](https://mufgub.wd3.myworkdayjobs.com/MUFG-Careers): page reachable; HTTP 200. 

### C165 — MUFG Pension & Market Services

Configured career URL: [https://www.mpms.mufg.com/careers](https://www.mpms.mufg.com/careers)

- [https://www.mpms.mufg.com/careers](https://www.mpms.mufg.com/careers): page reachable; HTTP 200. 
- [https://hcmn.fa.ap1.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions](https://hcmn.fa.ap1.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions): page reachable; HTTP 200. 
- [https://www.mpms.mufg.com/en/careers/apply-now/](https://www.mpms.mufg.com/en/careers/apply-now/): page reachable; HTTP 200. 

### C166 — National Australia Bank

Configured career URL: [https://www.nab.com.au/about-us/careers](https://www.nab.com.au/about-us/careers)

- [https://www.nab.com.au/about-us/careers](https://www.nab.com.au/about-us/careers): page reachable; HTTP 200. 
- [https://www.nab.com.au/about-us/careers/nabindia](https://www.nab.com.au/about-us/careers/nabindia): page reachable; HTTP 200. 
- [https://careers.nab.com.au/en/listing/](https://careers.nab.com.au/en/listing/): page reachable; HTTP 200. 
- [https://nab.eightfold.ai/careers?location=India](https://nab.eightfold.ai/careers?location=India): page reachable; HTTP 200. 
- [https://www.nab.com.au/about-us/careers/nabindia](https://www.nab.com.au/about-us/careers/nabindia): page reachable; HTTP 200. 

### C167 — NatWest Group

Configured career URL: [https://rbs.wd3.myworkdayjobs.com/RBS](https://rbs.wd3.myworkdayjobs.com/RBS)

- [https://rbs.wd3.myworkdayjobs.com/RBS](https://rbs.wd3.myworkdayjobs.com/RBS): page reachable; HTTP 200. 

### C168 — Navistar

Configured career URL: [https://careers.international.com/jobs](https://careers.international.com/jobs)

- [https://careers.international.com/jobs](https://careers.international.com/jobs): page reachable; HTTP 200. 
- [https://internalcareers.international.com](https://internalcareers.international.com): HTTP error; HTTP 302. HTTP Error 302: The HTTP server returned a redirect error that would lead to an infinite loop. The last 30x error message was: Found

### C169 — Ness Digital Engineering

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C170 — Nike

Configured career URL: [https://careers.nike.com/?query=pega](https://careers.nike.com/?query=pega)

- [https://careers.nike.com/?query=pega](https://careers.nike.com/?query=pega): page reachable; HTTP 200. 
- [https://careers.nike.com/retail-associate-pt-nike-las-vegas-south/job/R-92914](https://careers.nike.com/retail-associate-pt-nike-las-vegas-south/job/R-92914): page reachable; HTTP 200. 
- [https://careers.nike.com/doradca-doradczyni-klienta-w-sklepie-30-godz-tydz/job/R-97141](https://careers.nike.com/doradca-doradczyni-klienta-w-sklepie-30-godz-tydz/job/R-97141): page reachable; HTTP 200. 
- [https://nike.wd1.myworkdayjobs.com/nke2/job/Las-Vegas-Nevada/Retail-Associate--PT---Nike-Las-Vegas-South_R-92914-1/apply](https://nike.wd1.myworkdayjobs.com/nke2/job/Las-Vegas-Nevada/Retail-Associate--PT---Nike-Las-Vegas-South_R-92914-1/apply): page reachable; HTTP 200. 
- [https://nike.wd1.myworkdayjobs.com/nke/job/Wroclaw-Poland/Doradca-Doradczyni-klienta-w-sklepie--30-godz-tydz-_R-97141/apply](https://nike.wd1.myworkdayjobs.com/nke/job/Wroclaw-Poland/Doradca-Doradczyni-klienta-w-sklepie--30-godz-tydz-_R-97141/apply): page reachable; HTTP 200. 

### C171 — Nokia

Configured career URL: [https://jobs.nokia.com/en/sites/CX_1/jobs](https://jobs.nokia.com/en/sites/CX_1/jobs)

- [https://jobs.nokia.com/en/sites/CX_1/jobs](https://jobs.nokia.com/en/sites/CX_1/jobs): page reachable; HTTP 200. 

### C172 — Northern Trust

Configured career URL: [https://ntrs.wd1.myworkdayjobs.com/northerntrust](https://ntrs.wd1.myworkdayjobs.com/northerntrust)

- [https://ntrs.wd1.myworkdayjobs.com/northerntrust](https://ntrs.wd1.myworkdayjobs.com/northerntrust): page reachable; HTTP 200. 

### C173 — Nous Infosystems

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C174 — Novartis

Configured career URL: [https://www.novartis.com/careers](https://www.novartis.com/careers)

- [https://www.novartis.com/careers](https://www.novartis.com/careers): page reachable; HTTP 200. 
- [https://www.novartis.com/in-en/](https://www.novartis.com/in-en/): page reachable; HTTP 200. 
- [https://www.novartis.com/careers/career-hub](https://www.novartis.com/careers/career-hub): page reachable; HTTP 200. 
- [https://www.novartis.com/in-en/about/novartis-india](https://www.novartis.com/in-en/about/novartis-india): page reachable; HTTP 200. 
- [https://www.novartis.com/in-en/about/india-country-leadership-team](https://www.novartis.com/in-en/about/india-country-leadership-team): page reachable; HTTP 200. 

### C175 — NTT DATA

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C176 — Optum

Configured career URL: [https://careers.unitedhealthgroup.com/search-jobs](https://careers.unitedhealthgroup.com/search-jobs)

- [https://careers.unitedhealthgroup.com/search-jobs](https://careers.unitedhealthgroup.com/search-jobs): page reachable; HTTP 200. 
- [https://careers.unitedhealthgroup.com/search-jobs](https://careers.unitedhealthgroup.com/search-jobs): page reachable; HTTP 200. 
- [https://careers.unitedhealthgroup.com/search-jobs](https://careers.unitedhealthgroup.com/search-jobs): page reachable; HTTP 200. 
- [https://careers.unitedhealthgroup.com/search-jobs](https://careers.unitedhealthgroup.com/search-jobs): page reachable; HTTP 200. 
- [https://careers.unitedhealthgroup.com/search-jobs](https://careers.unitedhealthgroup.com/search-jobs): page reachable; HTTP 200. 

### C177 — Orange Business

Configured career URL: [https://www.orange-business.com/en](https://www.orange-business.com/en)

- [https://www.orange-business.com/en](https://www.orange-business.com/en): page reachable; HTTP 200. 

### C178 — PayPal

Configured career URL: [https://careers.pypl.com](https://careers.pypl.com)

- [https://careers.pypl.com](https://careers.pypl.com): page reachable; HTTP 200. 
- [https://careers.pypl.com/locations/india/default.aspx](https://careers.pypl.com/locations/india/default.aspx): page reachable; HTTP 200. 
- [https://careers.pypl.com/how-we-recruit/applying/default.aspx](https://careers.pypl.com/how-we-recruit/applying/default.aspx): page reachable; HTTP 200. 
- [https://paypal.eightfold.ai/careers?location=india&domain=paypal.com](https://paypal.eightfold.ai/careers?location=india&domain=paypal.com): page reachable; HTTP 200. 
- [https://paypal.eightfold.ai/careers?location=Bangalore%2C%20Karnataka%2C%20India](https://paypal.eightfold.ai/careers?location=Bangalore%2C%20Karnataka%2C%20India): page reachable; HTTP 200. 

### C179 — Pegasystems

Configured career URL: [https://www.pega.com/about/careers/job-listings](https://www.pega.com/about/careers/job-listings)

- [https://www.pega.com/about/careers/job-listings](https://www.pega.com/about/careers/job-listings): page reachable; HTTP 200. 
- [https://www.pega.com/about/careers/job-listings?f%5B0%5D=location%3A25951](https://www.pega.com/about/careers/job-listings?f%5B0%5D=location%3A25951): HTTP error; HTTP 403. HTTP Error 403: Forbidden
- [https://www.pega.com/about/careers/job-listings?f%5B0%5D=location%3A25956](https://www.pega.com/about/careers/job-listings?f%5B0%5D=location%3A25956): not retried after host refusal; HTTP n/a. 
- [https://www.pega.com/about/careers/job-listings?f%5B0%5D=location%3A25961](https://www.pega.com/about/careers/job-listings?f%5B0%5D=location%3A25961): not retried after host refusal; HTTP n/a. 
- [https://www.pega.com/about/careers/23970/talent-advisory-partner](https://www.pega.com/about/careers/23970/talent-advisory-partner): not retried after host refusal; HTTP n/a. 

### C180 — People Prime Worldwide

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C181 — PepsiCo

Configured career URL: [https://www.pepsicojobs.com/main/](https://www.pepsicojobs.com/main/)

- [https://www.pepsicojobs.com/main/](https://www.pepsicojobs.com/main/): page reachable; HTTP 200. 
- [https://www.pepsicojobs.com/main/our-locations/amesa/india](https://www.pepsicojobs.com/main/our-locations/amesa/india): page reachable; HTTP 200. 
- [https://www.pepsicojobs.com/jobs](https://www.pepsicojobs.com/jobs): page reachable; HTTP 200. 
- [https://www.pepsicojobs.com/india/jobs](https://www.pepsicojobs.com/india/jobs): page reachable; HTTP 200. 
- [https://www.pepsicojobs.com/main/our-locations/amesa/india?lang=en-US](https://www.pepsicojobs.com/main/our-locations/amesa/india?lang=en-US): page reachable; HTTP 200. 

### C182 — Persistent Systems

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C183 — Pfizer

Configured career URL: [https://www.pfizer.com/about/careers](https://www.pfizer.com/about/careers)

- [https://www.pfizer.com/about/careers](https://www.pfizer.com/about/careers): page reachable; HTTP 200. 

### C184 — Philips

Configured career URL: [https://www.careers.philips.com](https://www.careers.philips.com)

- [https://www.careers.philips.com](https://www.careers.philips.com): page reachable; HTTP 200. 
- [https://www.careers.philips.com/in/en/search-results](https://www.careers.philips.com/in/en/search-results): page reachable; HTTP 200. 

### C185 — PNC

Configured career URL: [https://careers.pnc.com/global/en](https://careers.pnc.com/global/en)

- [https://careers.pnc.com/global/en](https://careers.pnc.com/global/en): page reachable; HTTP 200. 

### C186 — Prime Therapeutics

Configured career URL: [https://www.primetherapeutics.com/careers/](https://www.primetherapeutics.com/careers/)

- [https://www.primetherapeutics.com/careers/](https://www.primetherapeutics.com/careers/): page reachable; HTTP 200. 
- [https://primetherapeutics.wd1.myworkdayjobs.com/PrimeTherapeuticsCareers](https://primetherapeutics.wd1.myworkdayjobs.com/PrimeTherapeuticsCareers): page reachable; HTTP 200. 

### C187 — Procter & Gamble

Configured career URL: [https://www.pgcareers.com/in/en](https://www.pgcareers.com/in/en)

- [https://www.pgcareers.com/in/en](https://www.pgcareers.com/in/en): page reachable; HTTP 200. 

### C188 — Proximus

Configured career URL: [https://jobs.proximus.com/be/en/search-results?keywords=pega&from=0](https://jobs.proximus.com/be/en/search-results?keywords=pega&from=0)

- [https://jobs.proximus.com/be/en/search-results?keywords=pega&from=0](https://jobs.proximus.com/be/en/search-results?keywords=pega&from=0): page reachable; HTTP 200. 

### C189 — PruTech Solutions

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C190 — Publicis Sapient

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C191 — PwC

Configured career URL: [https://pwc.wd3.myworkdayjobs.com/Global_Experienced_Careers](https://pwc.wd3.myworkdayjobs.com/Global_Experienced_Careers)

- [https://pwc.wd3.myworkdayjobs.com/Global_Experienced_Careers](https://pwc.wd3.myworkdayjobs.com/Global_Experienced_Careers): page reachable; HTTP 200. 
- [https://jobs-ta.pwc.com/global/en/ACs-in-India-Career-Site?linkId=14903784](https://jobs-ta.pwc.com/global/en/ACs-in-India-Career-Site?linkId=14903784): page reachable; HTTP 200. 
- [https://www.pwc.in/careers.html](https://www.pwc.in/careers.html): HTTP error; HTTP 403. HTTP Error 403: Forbidden
- [https://jobs-ta.pwc.com/global/en/ac-india-job-search](https://jobs-ta.pwc.com/global/en/ac-india-job-search): page reachable; HTTP 200. 
- [https://jobs-ta.pwc.com/global/en/ACs-in-India-Entry-Level-Campus-Careers](https://jobs-ta.pwc.com/global/en/ACs-in-India-Entry-Level-Campus-Careers): page reachable; HTTP 200. 
- [https://jobs-ta.pwc.com/global/en/ACs-in-India-Experienced-Careers](https://jobs-ta.pwc.com/global/en/ACs-in-India-Experienced-Careers): page reachable; HTTP 200. 

### C192 — Qualcomm

Configured career URL: [https://careers.qualcomm.com/careers](https://careers.qualcomm.com/careers)

- [https://careers.qualcomm.com/careers](https://careers.qualcomm.com/careers): page reachable; HTTP 200. 

### C193 — Quess Corp

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C194 — Rabobank

Configured career URL: [https://www.rabobank.jobs](https://www.rabobank.jobs)

- [https://www.rabobank.jobs](https://www.rabobank.jobs): HTTP error; HTTP 403. HTTP Error 403: Forbidden

### C195 — Renault Group

Configured career URL: [https://alliancewd.wd3.myworkdayjobs.com/en-US/renault-group-careers](https://alliancewd.wd3.myworkdayjobs.com/en-US/renault-group-careers)

- [https://alliancewd.wd3.myworkdayjobs.com/en-US/renault-group-careers](https://alliancewd.wd3.myworkdayjobs.com/en-US/renault-group-careers): page reachable; HTTP 200. 

### C196 — Renault Nissan Technology

Configured career URL: [https://www.renaultgroup.com/en/our-company/careers/](https://www.renaultgroup.com/en/our-company/careers/)

- [https://www.renaultgroup.com/en/our-company/careers/](https://www.renaultgroup.com/en/our-company/careers/): page reachable; HTTP 200. 
- [https://rntbci.in/careers](https://rntbci.in/careers): page reachable; HTTP 200. 

### C197 — Roche

Configured career URL: [https://careers.roche.com/global/en](https://careers.roche.com/global/en)

- [https://careers.roche.com/global/en](https://careers.roche.com/global/en): page reachable; HTTP 200. 

### C198 — Rolls-Royce

Configured career URL: [https://careers.rolls-royce.com/en/jobs](https://careers.rolls-royce.com/en/jobs)

- [https://careers.rolls-royce.com/en/jobs](https://careers.rolls-royce.com/en/jobs): page reachable; HTTP 200. 
- [https://careers.rolls-royce.com/en/students-and-graduates/india](https://careers.rolls-royce.com/en/students-and-graduates/india): page reachable; HTTP 200. 
- [https://careers.rolls-royce.com/en/students-and-graduates/india/work-experience](https://careers.rolls-royce.com/en/students-and-graduates/india/work-experience): page reachable; HTTP 200. 
- [https://careers.rolls-royce.com/en/our-locations/india](https://careers.rolls-royce.com/en/our-locations/india): page reachable; HTTP 200. 
- [https://careers.rolls-royce.com/en/jobs?country=United+States+of+America&city=Indianapolis](https://careers.rolls-royce.com/en/jobs?country=United+States+of+America&city=Indianapolis): page reachable; HTTP 200. 

### C199 — S&P Global

Configured career URL: [https://careers.spglobal.com](https://careers.spglobal.com)

- [https://careers.spglobal.com](https://careers.spglobal.com): page reachable; HTTP 200. 

### C200 — Scadea

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C201 — Schneider Electric

Configured career URL: [https://www.se.com/ww/en/about-us/careers/overview.jsp](https://www.se.com/ww/en/about-us/careers/overview.jsp)

- [https://www.se.com/ww/en/about-us/careers/overview.jsp](https://www.se.com/ww/en/about-us/careers/overview.jsp): HTTP error; HTTP 403. HTTP Error 403: Forbidden

### C202 — Shell

Configured career URL: [https://shell.com/careers](https://shell.com/careers)

- [https://shell.com/careers](https://shell.com/careers): page reachable; HTTP 200. 

### C203 — Siemens

Configured career URL: [https://jobs.siemens.com/careers](https://jobs.siemens.com/careers)

- [https://jobs.siemens.com/careers](https://jobs.siemens.com/careers): network/TLS error; HTTP n/a. <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate in certificate chain (_ssl.c:1032)>

### C204 — Sky

Configured career URL: [https://sky.wd3.myworkdayjobs.com/sky_careers](https://sky.wd3.myworkdayjobs.com/sky_careers)

- [https://sky.wd3.myworkdayjobs.com/sky_careers](https://sky.wd3.myworkdayjobs.com/sky_careers): page reachable; HTTP 200. 

### C205 — SLB

Configured career URL: [https://careers.slb.com](https://careers.slb.com)

- [https://careers.slb.com](https://careers.slb.com): page reachable; HTTP 200. 
- [https://careers.slb.com/job-listing](https://careers.slb.com/job-listing): page reachable; HTTP 200. 

### C206 — Societe Generale

Configured career URL: [https://careers.societegenerale.com/en](https://careers.societegenerale.com/en)

- [https://careers.societegenerale.com/en](https://careers.societegenerale.com/en): page reachable; HTTP 200. 
- [https://careers.societegenerale.com/en/search](https://careers.societegenerale.com/en/search): page reachable; HTTP 200. 

### C207 — Sonata Software

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C208 — Sopra Steria

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C209 — Standard Chartered

Configured career URL: [https://www.sc.com/en/global-careers/](https://www.sc.com/en/global-careers/)

- [https://www.sc.com/en/global-careers/](https://www.sc.com/en/global-careers/): page reachable; HTTP 200. 
- [https://sc.com/en/global-careers/early-careers/apply/](https://sc.com/en/global-careers/early-careers/apply/): page reachable; HTTP 200. 
- [https://jobs.standardchartered.com/?utm_source=careersite](https://jobs.standardchartered.com/?utm_source=careersite): page reachable; HTTP 200. 
- [https://www.sc.com/en/global-careers/early-careers/apply/](https://www.sc.com/en/global-careers/early-careers/apply/): page reachable; HTTP 200. 
- [https://www.sc.com/en/global-careers/early-careers/apply/](https://www.sc.com/en/global-careers/early-careers/apply/): page reachable; HTTP 200. 

### C210 — State Street

Configured career URL: [https://statestreet.wd1.myworkdayjobs.com/Global](https://statestreet.wd1.myworkdayjobs.com/Global)

- [https://statestreet.wd1.myworkdayjobs.com/Global](https://statestreet.wd1.myworkdayjobs.com/Global): page reachable; HTTP 200. 

### C211 — Stellantis

Configured career URL: [https://careers.stellantis.com/job-search-results/?keyword=pega](https://careers.stellantis.com/job-search-results/?keyword=pega)

- [https://careers.stellantis.com/job-search-results/?keyword=pega](https://careers.stellantis.com/job-search-results/?keyword=pega): page reachable; HTTP 200. 

### C212 — Sun Life

Configured career URL: [https://sunlife.com/careers](https://sunlife.com/careers)

- [https://sunlife.com/careers](https://sunlife.com/careers): HTTP error; HTTP 403. HTTP Error 403: Forbidden

### C213 — Synchrony

Configured career URL: [https://www.synchronycareers.com](https://www.synchronycareers.com)

- [https://www.synchronycareers.com](https://www.synchronycareers.com): page reachable; HTTP 200. 
- [https://www.synchronycareers.com/About-Us-India](https://www.synchronycareers.com/About-Us-India): page reachable; HTTP 200. 
- [https://www.synchronycareers.com/search-jobs](https://www.synchronycareers.com/search-jobs): page reachable; HTTP 200. 
- [https://www.synchronycareers.com/job/hyderabad/manager-campaign-operations-l09/49398/102015774128](https://www.synchronycareers.com/job/hyderabad/manager-campaign-operations-l09/49398/102015774128): page reachable; HTTP 200. 
- [https://www.synchronycareers.com/job/hyderabad/avp-quality-engineering-qe-automation-architect-l11/49398/100005082432](https://www.synchronycareers.com/job/hyderabad/avp-quality-engineering-qe-automation-architect-l11/49398/100005082432): page reachable; HTTP 200. 

### C214 — Synechron

Configured career URL: [https://synechron.wd1.myworkdayjobs.com/SynechronCareers](https://synechron.wd1.myworkdayjobs.com/SynechronCareers)

- [https://synechron.wd1.myworkdayjobs.com/SynechronCareers](https://synechron.wd1.myworkdayjobs.com/SynechronCareers): page reachable; HTTP 200. 

### C215 — T-Mobile

Configured career URL: [https://talent500.com/t-mobile/careers/india/](https://talent500.com/t-mobile/careers/india/)

- [https://talent500.com/t-mobile/careers/india/](https://talent500.com/t-mobile/careers/india/): page reachable; HTTP 200. 
- [https://talent500.com/t-mobile/careers/india/](https://talent500.com/t-mobile/careers/india/): page reachable; HTTP 200. 
- [https://talent500.com/jobs/t-mobile/](https://talent500.com/jobs/t-mobile/): page reachable; HTTP 200. 

### C216 — Target

Configured career URL: [https://corporate.target.com/careers](https://corporate.target.com/careers)

- [https://corporate.target.com/careers](https://corporate.target.com/careers): page reachable; HTTP 200. 
- [https://corporate.target.com/careers/job-search/store/stores](https://corporate.target.com/careers/job-search/store/stores): page reachable; HTTP 200. 
- [https://corporate.target.com/careers/job-search/supply-chain/supply-chain](https://corporate.target.com/careers/job-search/supply-chain/supply-chain): page reachable; HTTP 200. 
- [https://corporate.target.com/careers/job-search/corporate/corporate](https://corporate.target.com/careers/job-search/corporate/corporate): page reachable; HTTP 200. 
- [https://corporate.target.com/careers/job-search/internships/internships-entry-level-programs](https://corporate.target.com/careers/job-search/internships/internships-entry-level-programs): page reachable; HTTP 200. 

### C217 — Tata Consultancy Services

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C218 — Tech Mahindra

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C219 — Telstra

Configured career URL: [https://careers.telstra.com](https://careers.telstra.com)

- [https://careers.telstra.com](https://careers.telstra.com): page reachable; HTTP 200. 
- [https://telstra.wd3.myworkdayjobs.com/Telstra_Careers](https://telstra.wd3.myworkdayjobs.com/Telstra_Careers): page reachable; HTTP 200. 

### C220 — Tesco

Configured career URL: [https://careers.tesco.com/en_GB/careers/SearchJobs?semanticSearch=pega](https://careers.tesco.com/en_GB/careers/SearchJobs?semanticSearch=pega)

- [https://careers.tesco.com/en_GB/careers/SearchJobs?semanticSearch=pega](https://careers.tesco.com/en_GB/careers/SearchJobs?semanticSearch=pega): page reachable; HTTP 200. 
- [https://careers.tesco.com/en_GB/careers/SearchJobs?semanticSearch=pega](https://careers.tesco.com/en_GB/careers/SearchJobs?semanticSearch=pega): page reachable; HTTP 200. 
- [https://careers.tesco.com/en_GB/careers/SearchJobs](https://careers.tesco.com/en_GB/careers/SearchJobs): page reachable; HTTP 200. 
- [https://careers.tesco.com/cs_CZ/careers/SearchJobs?semanticSearch=pega](https://careers.tesco.com/cs_CZ/careers/SearchJobs?semanticSearch=pega): page reachable; HTTP 200. 
- [https://careers.tesco.com/hu_HU/careers/SearchJobs?semanticSearch=pega](https://careers.tesco.com/hu_HU/careers/SearchJobs?semanticSearch=pega): page reachable; HTTP 200. 

### C221 — The Hartford

Configured career URL: [https://www.thehartford.com/careers](https://www.thehartford.com/careers)

- [https://www.thehartford.com/careers](https://www.thehartford.com/careers): network/TLS error; HTTP n/a. <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1032)>

### C222 — Toyota

Configured career URL: [https://toyota.com/careers](https://toyota.com/careers)

- [https://toyota.com/careers](https://toyota.com/careers): page reachable; HTTP 200. 
- [https://www.toyotaconnected.co.in/careers](https://www.toyotaconnected.co.in/careers): page reachable; HTTP 200. 
- [https://toyota.wd503.myworkdayjobs.com/TMNA](https://toyota.wd503.myworkdayjobs.com/TMNA): page reachable; HTTP 200. 
- [https://www.toyotaconnected.co.in/article/sahil-chronicles-his-campus-to-corporate-journey-at-tcin](https://www.toyotaconnected.co.in/article/sahil-chronicles-his-campus-to-corporate-journey-at-tcin): page reachable; HTTP 200. 
- [https://medium.com/toyota-connected-india](https://medium.com/toyota-connected-india): HTTP error; HTTP 403. HTTP Error 403: Forbidden
- [https://www.toyotaconnected.co.in/category/news-updates](https://www.toyotaconnected.co.in/category/news-updates): page reachable; HTTP 200. 

### C223 — Toyota Financial Services

Configured career URL: [https://www.toyotafinancial.com/us/en/careers.html](https://www.toyotafinancial.com/us/en/careers.html)

- [https://www.toyotafinancial.com/us/en/careers.html](https://www.toyotafinancial.com/us/en/careers.html): HTTP error; HTTP 404. HTTP Error 404: Not Found

### C224 — U.S. Bank

Configured career URL: [https://careers.usbank.com](https://careers.usbank.com)

- [https://careers.usbank.com](https://careers.usbank.com): page reachable; HTTP 200. 

### C225 — UBS

Configured career URL: [https://www.ubs.com/global/en/careers.html](https://www.ubs.com/global/en/careers.html)

- [https://www.ubs.com/global/en/careers.html](https://www.ubs.com/global/en/careers.html): HTTP error; HTTP 403. HTTP Error 403: Forbidden

### C226 — Uni-Pega

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C227 — Unilever

Configured career URL: [https://careers.unilever.com](https://careers.unilever.com)

- [https://careers.unilever.com](https://careers.unilever.com): page reachable; HTTP 200. 
- [https://careers.unilever.com/en/job/tinsukia/senior-finance-executive/34155/101120724592](https://careers.unilever.com/en/job/tinsukia/senior-finance-executive/34155/101120724592): page reachable; HTTP 200. 
- [https://careers.unilever.com/en/job/gandhidham/senior-finance-executive/34155/102852309232](https://careers.unilever.com/en/job/gandhidham/senior-finance-executive/34155/102852309232): page reachable; HTTP 200. 
- [https://unilever.wd3.myworkdayjobs.com/en-US/Unilever_Experienced_Professionals/job/Assam--Doom-Dooma/Senior-Finance-Executive_R-1187730-1/apply](https://unilever.wd3.myworkdayjobs.com/en-US/Unilever_Experienced_Professionals/job/Assam--Doom-Dooma/Senior-Finance-Executive_R-1187730-1/apply): page reachable; HTTP 200. 
- [https://unilever.wd3.myworkdayjobs.com/en-US/Unilever_Experienced_Professionals/job/Kandla-Exports-Factory/Senior-Finance-Executive_R-1190885/apply](https://unilever.wd3.myworkdayjobs.com/en-US/Unilever_Experienced_Professionals/job/Kandla-Exports-Factory/Senior-Finance-Executive_R-1190885/apply): page reachable; HTTP 200. 

### C228 — Unisys

Configured career URL: [https://unisys.wd5.myworkdayjobs.com/External](https://unisys.wd5.myworkdayjobs.com/External)

- [https://unisys.wd5.myworkdayjobs.com/External](https://unisys.wd5.myworkdayjobs.com/External): page reachable; HTTP 200. 

### C229 — UPS

Configured career URL: [https://www.jobs-ups.com/imea/en](https://www.jobs-ups.com/imea/en)

- [https://www.jobs-ups.com/imea/en](https://www.jobs-ups.com/imea/en): page reachable; HTTP 200. 

### C230 — UST

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C231 — Vanguard

Configured career URL: [https://vanguard.wd5.myworkdayjobs.com/vanguard_external](https://vanguard.wd5.myworkdayjobs.com/vanguard_external)

- [https://vanguard.wd5.myworkdayjobs.com/vanguard_external](https://vanguard.wd5.myworkdayjobs.com/vanguard_external): page reachable; HTTP 200. 

### C232 — Verizon

Configured career URL: [https://mycareer.verizon.com](https://mycareer.verizon.com)

- [https://mycareer.verizon.com](https://mycareer.verizon.com): page reachable; HTTP 200. 

### C233 — Virtusa

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C234 — Visa

Configured career URL: [https://usa.visa.com/careers.html](https://usa.visa.com/careers.html)

- [https://usa.visa.com/careers.html](https://usa.visa.com/careers.html): network/TLS error; HTTP n/a. <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1032)>

### C235 — Vodafone

Configured career URL: [https://careers.vodafone.com](https://careers.vodafone.com)

- [https://careers.vodafone.com](https://careers.vodafone.com): page reachable; HTTP 200. 
- [https://jobs.vodafone.com/careers](https://jobs.vodafone.com/careers): page reachable; HTTP 200. 
- [https://careers.vodafone.com/applying-to-vodafone/our-hiring-process/](https://careers.vodafone.com/applying-to-vodafone/our-hiring-process/): page reachable; HTTP 200. 
- [https://careers.vodafone.com/applying-to-vodafone/application-and-interview-top-tips/](https://careers.vodafone.com/applying-to-vodafone/application-and-interview-top-tips/): page reachable; HTTP 200. 
- [https://careers.vodafone.com/applying-to-vodafone/application-adjustments/](https://careers.vodafone.com/applying-to-vodafone/application-adjustments/): page reachable; HTTP 200. 

### C236 — Vodafone Idea

Configured career URL: [https://careers.vodafoneidea.com/search/](https://careers.vodafoneidea.com/search/)

- [https://careers.vodafoneidea.com/search/](https://careers.vodafoneidea.com/search/): page reachable; HTTP 200. 
- [https://careers.vodafoneidea.com/job/Mumbai-Manager-247-Desk-Maha/1447895833/](https://careers.vodafoneidea.com/job/Mumbai-Manager-247-Desk-Maha/1447895833/): page reachable; HTTP 200. 
- [https://careers.vodafoneidea.com/job/Mumbai-AGM-Corp-FP&A%2C-Technology-Finance-Maha/1448030533/](https://careers.vodafoneidea.com/job/Mumbai-AGM-Corp-FP&A%2C-Technology-Finance-Maha/1448030533/): page reachable; HTTP 200. 
- [https://careers.vodafoneidea.com/job/Hyderabad-AGM-Area-Sales-Tela/1447902933/](https://careers.vodafoneidea.com/job/Hyderabad-AGM-Area-Sales-Tela/1447902933/): page reachable; HTTP 200. 
- [https://careers.vodafoneidea.com/job/Pune-Manager-OSS-&-Tools-Maha/1437517433/](https://careers.vodafoneidea.com/job/Pune-Manager-OSS-&-Tools-Maha/1437517433/): page reachable; HTTP 200. 

### C237 — Volvo Cars

Configured career URL: [https://jobs.volvocars.com/search/?q=pega&startrow=0&locationsearch=](https://jobs.volvocars.com/search/?q=pega&startrow=0&locationsearch=)

- [https://jobs.volvocars.com/search/?q=pega&startrow=0&locationsearch=](https://jobs.volvocars.com/search/?q=pega&startrow=0&locationsearch=): page reachable; HTTP 200. 
- [https://jobs.volvocars.com/search/?q=&locationsearch=India](https://jobs.volvocars.com/search/?q=&locationsearch=India): page reachable; HTTP 200. 
- [https://jobs.volvocars.com/job/Ghent-Stage-enof-masterproef-Maintenance-BE-9000/934446501/](https://jobs.volvocars.com/job/Ghent-Stage-enof-masterproef-Maintenance-BE-9000/934446501/): page reachable; HTTP 200. 
- [https://jobs.volvocars.com/search/?q=&locationsearch=India](https://jobs.volvocars.com/search/?q=&locationsearch=India): page reachable; HTTP 200. 
- [https://jobs.volvocars.com/search/?q=&locationsearch=India&locale=de_DE](https://jobs.volvocars.com/search/?q=&locationsearch=India&locale=de_DE): page reachable; HTTP 200. 

### C238 — Voya Financial

Configured career URL: [https://www.voya.com/careers](https://www.voya.com/careers)

- [https://www.voya.com/careers](https://www.voya.com/careers): page reachable; HTTP 200. 
- [https://godirect.wd5.myworkdayjobs.com/voya_jobs](https://godirect.wd5.myworkdayjobs.com/voya_jobs): page reachable; HTTP 200. 

### C239 — VW Digital Solutions

Configured career URL: Not configured

- [https://vwg-digitalsolutions.in/](https://vwg-digitalsolutions.in/): network/TLS error; HTTP n/a. <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate in certificate chain (_ssl.c:1032)>

### C240 — Walmart Global Tech

Configured career URL: [https://careers.walmart.com/us/en/home/careers-areas/technology](https://careers.walmart.com/us/en/home/careers-areas/technology)

- [https://careers.walmart.com/us/en/home/careers-areas/technology](https://careers.walmart.com/us/en/home/careers-areas/technology): page reachable; HTTP 200. 

### C241 — Wells Fargo

Configured career URL: [https://www.wellsfargojobs.com/en/jobs/?search=pega&country=India](https://www.wellsfargojobs.com/en/jobs/?search=pega&country=India)

- [https://www.wellsfargojobs.com/en/jobs/?search=pega&country=India](https://www.wellsfargojobs.com/en/jobs/?search=pega&country=India): page reachable; HTTP 200. 
- [https://www.wellsfargojobs.com/en/jobs/?search=pega&country=India](https://www.wellsfargojobs.com/en/jobs/?search=pega&country=India): page reachable; HTTP 200. 
- [https://www.wellsfargojobs.com/en/early-careers/international-programs/india-programs/](https://www.wellsfargojobs.com/en/early-careers/international-programs/india-programs/): page reachable; HTTP 200. 
- [https://www.wellsfargojobs.com/en/jobs/?search=pega&country=India](https://www.wellsfargojobs.com/en/jobs/?search=pega&country=India): page reachable; HTTP 200. 
- [https://www.wellsfargojobs.com/en/jobs/?search=pega&country=India](https://www.wellsfargojobs.com/en/jobs/?search=pega&country=India): page reachable; HTTP 200. 

### C242 — Western Union

Configured career URL: [https://careers.westernunion.com](https://careers.westernunion.com)

- [https://careers.westernunion.com](https://careers.westernunion.com): network/TLS error; HTTP n/a. <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate in certificate chain (_ssl.c:1032)>

### C243 — Westpac

Configured career URL: [https://ebuu.fa.ap1.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX](https://ebuu.fa.ap1.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX)

- [https://ebuu.fa.ap1.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX](https://ebuu.fa.ap1.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX): page reachable; HTTP 200. 

### C244 — Wipro

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C245 — Xperteez Technology

Configured career URL: Not configured

No live request: registry has no career URL. Requires official-source discovery.

### C246 — Zensar Technologies

Configured career URL: [https://fa-etvl-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1](https://fa-etvl-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1)

- [https://fa-etvl-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1](https://fa-etvl-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1): page reachable; HTTP 200. 

### C247 — Zurich Insurance

Configured career URL: [https://www.zurich.com/careers](https://www.zurich.com/careers)

- [https://www.zurich.com/careers](https://www.zurich.com/careers): page reachable; HTTP 200. 

## Changes recommended to Claude

1. Add Bank of America BA Continuum and scan it first. Add Columbia corporate/India board with current descriptions driving relevance. Evaluate BD India as a direct backend alongside the existing frontend.
2. Support multiple portal definitions per employer/business unit. Record parent/subsidiary relationship, India evidence URL and sample requisition ID for each board. Do not infer geography from the board name alone.
3. Treat API success as transport/schema evidence, not whole-company coverage. A positive India job sample should establish board scope. A zero-keyword result cannot establish that no India roles exist elsewhere.
4. Keep discovery completeness separate from adapter health. Verification currently checks configured portals only; it cannot find missing boards such as BA Continuum.
5. Compare sampled official India job IDs with stored job IDs. Distinguish missed listing, parser/detail failure, deliberately excluded geography, no current Pega relevance, UI filtering, and already captured.
6. Use title plus current description to establish Pega relevance. A stale URL containing Pega, or a location containing Pegasus, is not sufficient. Preserve the original external ID even when title/slug changes.
7. Use reusable official backends where appropriate (ABB/Chevron Workday), compare IDs before claiming incremental coverage, and retain per-source provenance.
8. Keep unsupported and access-failed employers visible. Resolve IBM, Toyota Connected, RNTBCI and VW India independently; never replace India scope with a convenient global/US parent board.
9. Add fixtures for missing subsidiary boards, wrong-region boards, stale keyword slugs and already-captured roles; operationally compare old/new source results before promoting configuration.
10. Do not promote every new URL or mark every registry entry covered based on this report. Full pagination and entity validation remain outstanding.

## Evidence package

`company-findings.json` contains per-company conclusions; `C*.json` contains observed links and current configurations; `board-probes.json` has live public API responses and sampled details; `scanner-outcomes.json` records the inspected scan outcomes and selected saved jobs; `evidence/` holds compressed source responses. Website content is untrusted data, not instructions. Timestamps are UTC within evidence records.
