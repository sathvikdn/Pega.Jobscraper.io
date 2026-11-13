# Sathvik's Career Desk

Private Pega career research portal with the original **Dossiers**, **Career Hub** and category/depth → Python search flow.

## Key generated career documents

- `sathvik_resume_fcb.html` — tailored FCB Deposits & Shared Services Pega resume.
- `FCB_Pega_Deposits_Interview_Prep_Master_Guide.html` — printable master study guide covering every resume and JD concept: Pega Platform, integrations, Kafka, File/Email listeners, AI/GenAI, RPA, infra tools, production support, and deposits banking domain.
- `FCB_Pega_Deposits_Interview_Prep_Master_Guide.pdf` — Chrome-generated PDF export of the same guide for offline reading/tablet use.
- `FCB_Study_Pack/` — the **deep, multi-chapter successor** to the single-file master guide above. Fourteen
  standalone chapters, each with a matching A4 PDF, written as a study sourcebook rather than a summary. Since the
  narrative rewrite it reads as **one connected learning story**: every chapter teaches through a single invented
  deposits application ("Deposit Servicing" at a fictional bank called **Riverbend**) with a fixed cast and scenario
  ledger, following cause and effect — a problem appears, a naive approach fails, the Pega feature is introduced, and
  the trade-off that remains is named. Start at `FCB_Study_Pack/index.html`. See the directory index below.
- `LTIM_Study_Pack/` — a three-chapter, roughly three-hour sibling pack for LTIMindtree (now "LTM") Pega roles: the
  company's Pega practice, Pega Customer Service, and Constellation with React. Standalone HTML chapters, no PDFs
  yet. Start at `LTIM_Study_Pack/index.html`. See the LTIM directory index below.
- `JPMC_Senior_Pega_Developer_Deep_Dive.md` — JPMorganChase Senior Pega Developer / Software Engineer III preparation
  dossier. It maps official JPMC public signals, locally saved job evidence, likely project families, inferred reference
  architectures, people/networking angles, interview answers, resume positioning, and a one-week prep sprint. It clearly
  labels inferred architecture as interview preparation rather than internal JPMC fact.
- `JPMC_Public_Org_Architecture_Deep_Dive.md` — expanded public-source JPMorganChase organization and architecture
  dossier. It covers official business-line structure, operating-committee anchors, India technology centers, Global
  Technology engineering-platform signals, JET/EPX/SDLC/cloud/control themes, and an interview-safe reference
  architecture for Pega + Camunda + Java + APIs + event streams across CIB Payments, Securities Services, CCB marketing
  automation and CAO/corporate workflows. It separates official facts, public role signals and inferred architecture.
- `CBA_ASB_Pega_Interview_Dossier.html` — standalone printable interview dossier for the Commonwealth Bank India Pega squad that serves ASB (NZ), Senior Software Engineer – Pega Development (REQ266821/REQ266822). It covers org structure, people, workstreams, the reported interview process, a resume fit map, technical and design practice, values and STAR stories, pay bands and a prep plan. Evidence is labelled Fact, Reported or Inference.
- `JPMC_Public_Org_Architecture_Deep_Dive.html` — standalone printable HTML rendering of the public JPMC organization
  and architecture dossier, with a toolbar, section navigation, tables, architecture diagrams, interview answers,
  preparation roadmap, and source notes for offline browser review or PDF export.

### FCB_Study_Pack — directory structure and file index

Superseding note: the single-file `FCB_Pega_Deposits_Interview_Prep_Master_Guide.*` is retained for reference, but
`FCB_Study_Pack/` is the current and far more detailed material. Chapters are HTML source of truth; each `.pdf` is a
Chrome-generated render of the same-named `.html`.

| Path | Contents |
| --- | --- |
| `index.html` | Study-pack hub: how to use the pack, suggested reading order, the honesty rule, chapter directory, headline-metrics table |
| `_authoring_spec.md` | Authoring contract for the pack (audience, HTML skeleton, depth bar, honesty constraint, chapter manifest, PDF render procedure). Needed to regenerate or extend chapters consistently |
| `_canonical_corrections.md` | **Accuracy-pass spec, part 1.** The evidence-tag and release-label vocabularies; the verified five-phase rule-resolution model; the corrected assignment-urgency formula; the regulatory-calendar model; and the **personal-claim register** mapping every first-person claim in the pack to its résumé evidence and category A–E. The register is the authority for what the pack may assert about the candidate |
| `_canonical_corrections_2.md` | **Accuracy-pass spec, part 2.** Integration correctness (duplicate-detection vs idempotent state change vs safe business operation; snapshot vs partial-update vs delta; the atomic dedupe boundary; five failure walkthroughs), release discipline, the SQL/code audit, testing guidance, the ch14 practice format, and the deduplication/references plan |
| `_narrative_spec.md` | **Narrative-rewrite spec.** The authoring contract for the connected learning story: the one-time illustrative notice, the fixed cast, the scenario ledger (accounts, balances, dated timeline, case/event IDs) that no chapter may contradict, the cause-and-effect teaching sequence, the prose-first format rule, the per-chapter arcs and the technical fixes E.1-E.6. Read this before editing any chapter |
| `_CHANGELOG_narrative_rewrite.md` | Per-chapter record of the narrative rewrite: what each chapter's arc now is, the technical corrections applied, source-labelling policy, and the verification performed |
| `_canonical_corrections_3.md` | **Accuracy-pass spec, part 3.** The sourced Reg CC funds-availability schedule (12 CFR 229.10 and 229.12), with the $275/$550 amounts and their 1 July 2025 effective date |
| `assets/sourcebook.css` | Shared stylesheet for every chapter; screen layout plus A4 print rules |
| `ch01_pega_platform_core.*` | Rules, class hierarchy, inheritance, rule resolution, rulesets, clipboard, locking, guardrails, PegaUnit |
| `ch02_case_management_bpm.*` | Case lifecycle, stages, flow shapes, routing, approvals, maker-checker, SLAs, correspondence, case blueprints |
| `ch03_data_model_decisioning.*` | Properties, exposed columns vs BLOB, Data Pages, declarative rules, Data Transforms, activities, decision tables, circumstancing |
| `ch04_ui_constellation_dx.*` | Traditional UI, Constellation architecture, DX Components, DX API v1 vs Constellation DX API, SDKs |
| `ch05_integration_rest_soap_esb.*` | Connectors/services, Connect-REST, SOAP, ESB patterns, Connect-SQL MERGE, resilience engineering, OAuth 2.0 / SAML / mTLS |
| `ch06_kafka_dataflow_queue_processors.*` | Kafka internals, delivery semantics, Pega datasets and Data Flows, Queue Processor tuning, Job Schedulers, dead-letter and replay |
| `ch07_file_email_listeners.*` | File Listener/SFTP chain, trigger-file handshake, parse rules, per-record error isolation, NACHA files, Email Listener/Channel |
| `ch08_pega_ai_genai_decisioning.*` | Prediction Studio, CDH/Next-Best-Action, GenAI governance, Knowledge Buddy and RAG, agentic patterns, Blueprint |
| `ch09_pega_rpa.*` | RPA vs API vs BPM decision framework, Robot Studio/Runtime/Manager, bot fragility, OCR/IDP, bot credentials and audit |
| `ch10_security_devops_monitoring.*` | Access groups/roles/AROs and production levels, role design with segregation of duties, PDC/Tracer/PAL, Splunk SPL, CI/CD, incident runbook |
| `ch11_postgresql_sql_deep.*` | Deposits schema, joins/CTEs/window functions, isolation levels and MVCC, deadlocks, EXPLAIN ANALYZE, indexing, Pega `pr_*` tables |
| `ch12_deposits_banking_domain.*` | Deposit products, account lifecycle, KYC/AML/OFAC, legal process orders, ACH/checks/wires, Reg E/CC/DD, reconciliation, 101-term glossary |
| `ch13_fcb_architecture_blueprints.*` | The application revisited whole: why each boundary exists, then one complete request (closure `AC-10882`) walked across UI, case engine, integration, core, asynchronous confirmation and audit, then scale, failure, deployment and recovery. The other case types follow as *variations* stating what differs and why. Exhaustive integration inventory and blueprint tables sit in reference blocks `13.R1`/`13.R2` |
| `ch14_interview_question_bank.*` | 135 model answers in nineteen groups. The interview-deciding questions carry the full practice shape — direct answer, mechanism, one clearly labelled example, two likely follow-ups, one common mistake. Also holds the material moved out of the learning chapters: design scenarios (`14.13b`), the first-90-days plan, the résumé mapping, STAR scaffolds, and the metrics cheat sheet |

Cautions for this folder:

- **Where personal claims live changed in the narrative rewrite.** Chapters 01–13 are now a fictional teaching story
  and carry *no* personal claims, so the inline evidence tags were removed from them (the only tags left in ch13 are
  `assumed Riverbend policy`, marking invented SLAs and thresholds). Personal-experience verification is consolidated
  in the **evidence register** — the table in `index.html#evidence-register`, which maps all 24 claims to the résumé
  line that supports them, a category A–E, and what the candidate must confirm. Tags still appear beside individual
  **ch14** model answers, because a model answer is a claim's point of use. Categories: **A** confirmed personal
  implementation (only the candidate may promote a claim to this), **B** on the résumé but method/scope/measurement
  unrecorded, **C** derived for teaching, **D** would build rather than built, **E** conceptual knowledge. Nothing is
  category A until confirmed. **Never upgrade a claim's category without the candidate's confirmation**, and never add
  a claim the résumé does not support — a claim already appearing in the pack is not evidence that it is true.
- Several claims are deliberately marked `CONCEPTUAL` because the résumé lists them as skills but describes no usage:
  Deployment Manager, PostgreSQL in production, Splunk, and Okta/SAML. Mentoring is absent from the résumé entirely and
  must not be presented as an achievement. Keeping these honest is the point of the tagging; do not quietly promote them.
- Throughput and cost figures from different projects are recorded separately, each with a measurement record (volume,
  environment, processing boundary, elapsed time, concurrency, error rate, measurement method). Unconfirmed fields are
  marked `[CONFIRM]`. Do not merge measurements across projects.
- Regulatory figures are now **sourced or deleted** — the previous `verify current` hedge has been removed throughout.
  Each chapter carries an authoritative references table giving source, URL, effective date and what it supports.
  Primary sources used include 12 CFR 1005.2/1005.11 (Reg E), 12 CFR 229.2/229.10/229.12 (Reg CC), IRC §6332(c), and
  the Nacha rules. Reg CC dollar amounts ($275/$550) are effective 1 July 2025 and adjust on a five-year cycle — always
  quote them with the date.
- Pega behaviour that is release-sensitive is labelled as such rather than asserted. Two in particular are deliberately
  left open because they cannot be settled without a deployed system: the `pyProcessSLA` / `UseSLAQueueProcessor`
  default and its migration drain behaviour, and whether `Queue-For-Processing` commits in the same transaction as the
  business write (i.e. whether it is a true transactional outbox). Each names the experiment or screen that settles it.
  Do not replace those with an assertion.
- Regenerating the PDFs: run `node render_study_pack.mjs "JobChange\JobChange\FCB_Study_Pack"` from
  `01_pega_career_intelligence/` (uses the Puppeteer already in `node_modules`). It renders every `.html` in the folder
  to a same-named `.pdf` and prints per-file page counts. **Do not use `chrome.exe --print-to-pdf` here — it hangs.**
  Chrome in this environment is pathologically slow to start (~70-130 s to launch, ~190 s to open the first tab), so the
  script launches once and reuses a single page; allow roughly ten minutes for all fifteen files and run it in the
  background. If a run fails with `Network.enable timed out` or `WS endpoint URL`, stray headless Chrome processes from a
  previous attempt are the cause — kill the windowless `chrome` processes and retry.
- The renderer passes zero margins deliberately: `assets/sourcebook.css` declares `@page{size:A4;margin:0}` and supplies
  its own page padding through `.book` and `main`. Passing Puppeteer margins stacks on top of that and shrinks the text
  block, so leave them at zero.

### CBA_Study_Pack — directory structure and file index

This pack is preparation for the Commonwealth Bank India Pega squad that serves ASB in New Zealand (Senior Software Engineer – Pega Development, REQ266821/REQ266822). It uses the method of `FCB_Study_Pack/ch13`: one invented application, every boundary justified by the failure it prevents, and one request walked end to end. Chapters are HTML source of truth; each `.pdf` is a Puppeteer render of the same-named `.html`.

| Path | Contents |
| --- | --- |
| `index.html` | Pack hub: the worked-example notice, reading order, and links to the dossier and the related FCB chapters (ch13, ch06) |
| `ch01_cba_asb_architecture_blueprints.html` | **Architecture: How It All Fits.** Lending Care for the fictional NZ bank *Tōtara Bank*. Covers public facts vs invented (§1.0); the ten boundaries; the brief; a context diagram; integration patterns and contract; layered rulesets and classes; the canonical model and event envelope; event streaming in depth (topics, ownership, consumption, ordering, duplicates, DLQ, replay, outbox); Aroha's hardship `HA-20417` in eight hops (with a core timeout and an event confirmation); variations (arrears, KYC review, payment exception, service, broker); shared frameworks; scale, failure, deployment and recovery; the India–NZ working model; migration; risks; interview whiteboard and twelve prompts; integration inventory; four case blueprints; references |
| `assets/sourcebook.css` | Copy of the FCB stylesheet. Chapter-local tweaks (mobile table scrolling, cover code contrast) live in the chapter's own `<style>`, not here |

Cautions for this folder:

- Tōtara Bank, Lending Care, every person, ID, topic name, threshold and SLA marked "assumed Tōtara policy" are invented. Only the facts in §1.0 (with sources in §1.R) are public. Never present the invented specifics as CBA or ASB facts in an interview.
- The NZ hardship clocks come from the Credit Contracts and Consumer Finance Act 2003 (s55–57A) and Consumer Protection NZ guidance: 5, 10 and 20 working days. The Act's working-day definition must be confirmed before you quote edge cases.
- Pega behaviour marked "release-sensitive" (data-flow partitions and threads, offset commits, whether a queued item commits atomically with the case) must be verified on the target release.
- Regenerate the PDFs with `node render_study_pack.mjs "JobChange\JobChange\CBA_Study_Pack"` from `01_pega_career_intelligence/`.

### LTIM_Study_Pack — directory structure and file index

Sibling of `FCB_Study_Pack/`, same house style and shared stylesheet, different target: LTIMindtree Pega roles that
combine the company's Pega practice, Pega Customer Service and Constellation/React. Chapters are HTML source of truth;
no PDFs have been generated.

| Path | Contents |
| --- | --- |
| `index.html` | Pack hub: how to use the pack, the honesty rule, evidence tags, chapter directory, the 3-hour reading plan (three ~60 minute blocks), headline evidence table |
| `_authoring_spec.md` | Authoring contract (audience, HTML skeleton, depth bar, honesty constraint, style rules, per-chapter content outlines). Needed to extend chapters consistently |
| `_research_dossier.md` | The only permitted source for LTIMindtree-specific claims, with a confidence level per fact and a list of things explicitly not established. Never add an LTIMindtree claim that is not in it |
| `_verify.py` | Structural checker: anchors, cross-file links, classes against the stylesheet, no inline styles, word, Q&A, answer and flow counts, cover tiles, chapter map against headings. Run `python _verify.py` from the folder |
| `assets/sourcebook.css` | Copy of the FCB stylesheet; screen layout plus A4 print rules. Do not modify |
| `ch01_ltimindtree_pega_practice.html` | Company and the LTM rebrand, Pega partner tiers, Ruletronics, award record, CoE and accelerators, squad/tribe/chapter, the four job descriptions decoded, fit mapping, questions to ask |
| `ch02_pega_customer_service.html` | Strategic application vs platform, Interaction and service request types, Microjourneys, the six Interaction Portal areas, channels, intelligence, industry editions, AHT/FCR/NPS, honest mapping of the resume's "Customer Service" line |
| `ch03_constellation_react.html` | 8.8 renaming, stateless architecture, Constellation UI Service, Constellation vs Traditional DX API, Web Embed and coexistence, three levels of React, DX Components, React SDK, debugging, governance, one-week ramp plan |

Cautions for this folder:

- LTIMindtree facts were retrieved on 2026-10-12. Re-check the careers site and the Pega partner pages before an
  interview. No client name, headcount, team structure or interview-process detail is established; do not add any.
- The candidate has not used Pega Customer Service, Constellation, the DX API, DX Components, the React SDK, React or
  Infinity 24.x. `_authoring_spec.md` §4 records this; chapters phrase these as understanding plus a ramp plan. Preserve
  that distinction in any edit.
- Pega product behaviour is release-sensitive; chapters describe function and cite the documentation bundle read.

The saved GCC review covers 191 catalogue entries and 698 associated records. The complete catalogue keeps 522 company entries and 574 distinct LinkedIn profile identities. Review status is shown per record; these numbers are not current team headcounts.

## Run locally

Python 3.10+:

~~~bash
pip install -r requirements.txt
python app.py --port 5050
~~~

Open http://127.0.0.1:5050. Windows can also use START_CAREER_DESK.cmd after setup.

## Run online

See [README-CLOUD.md](README-CLOUD.md) for the private repository, authenticated Docker/Render deployment and GitHub Actions jobs. The repository contains personal career information and must remain private.

- The online portal's existing Search button executes Python on the hosting server.
- The online GitHub workflow starts that same server job; results appear in the same portal.
- The standalone GitHub workflow runs Python on a GitHub runner and returns a separate results artifact.
- No recurring schedule is enabled.

## Evidence and state

The salary floor is ₹20 LPA annual total CTC; ₹35 LPA is the goal, not an assumed employer budget. Unknown pay, location, vacancy acceptance and profile identity remain unknown. Indexed sources can be stale. Public search does not bypass LinkedIn login/access restrictions and does not guarantee complete employee or vacancy coverage.

The Python job refreshes public job discovery and descriptions. It does not automatically reproduce the manually reviewed, 1,073-check company/profile investigation. Those curated reviews remain preloaded.

research/preloaded_search.json contains resumable scan results. data/workspace.sqlite3 contains notes, preferences and pipeline state. The cloud entry point places these on persistent storage. Original study material and historical observations remain available; Interview Masterclass is not exposed as a route.

## Validate

~~~bash
python -B -m unittest discover -s . -p 'test_*.py'
python -B job_runner.py --mode gcc_all --dry-run
~~~

The tests mock external sources; a successful test run does not prove public sites will accept requests from a cloud IP address.

## Pega recommendations and resume comparison

The scanner now recommends only roles whose saved full description establishes Pega/PRPC responsibilities and explicit experience below eight years. A range including eight is excluded; a minimum-only requirement such as four-plus is labelled as such. Requirements above the candidate's four years are labelled Stretch. A title, a query hit or an employer's Pega branding is not enough. Unread descriptions or unstated experience appear under Needs verification. Earlier discoveries remain saved.

View description opens the captured plain-text posting, source URL/date, and a resume evidence score against sathvik_resume_v2.html. The score explains matched resume evidence, missing requirements, listed-only skills, experience gaps and its weighting. It is not an ATS score or a hiring probability. Refresh description rechecks the exact public posting and preserves the prior snapshot if access fails.

GET /api/opportunities and /api/scan-results default to recommendations. Use scope=review for incomplete evidence or scope=all for explicit archival access. GET /api/opportunities/<id> reads saved detail without network access. POST /api/opportunities/<id>/description requires the portal CSRF token and updates only the saved description cache, preserving pipeline notes.

After an explicit job reset, historical job seeds are no longer loaded into active results. Fresh searches replace the selected companies' old job lists after successful queries; failed or pending checks cannot keep stale jobs in recommendations. Company/people research and pipeline notes remain separate and are preserved.
