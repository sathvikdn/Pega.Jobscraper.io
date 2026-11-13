# FCB Pega Deposits Study Pack — Authoring Spec

Authoring contract for every chapter file in this folder. Read this plus
`assets/sourcebook.css` plus the two finished exemplars (`ch01_pega_platform_core.html`,
`ch02_case_management_bpm.html`) before writing any new chapter.

## 1. Who this is for

Sathvik DN — Pega CSSA, 4.5 years at Mercedes-Benz R&D India (MBRDI) — interviewing for
**Pega Software Engineer II / lead-track at First Citizens Bank India (FCB/FCI), Deposits &
Shared Services**. Greenfield Pega implementation. Middleware is TIBCO ESB. Core banking is
Fiserv/Flexcube style. Domain is deposit operations.

He studies from this directly, under time pressure. It is a textbook, not a plan, not a summary,
not a checklist. He complained repeatedly that earlier drafts were "just a gist". Depth is the
entire point of this document.

Reference files one folder up (`..\`): `sathvik_resume_fcb.html` (his exact claims and metrics)
and `FCB_Pega_Deposits_Interview_Prep_Master_Guide.html` (the older, shallower single-file guide —
read it so you go far beyond it rather than repeating it).

## 2. Mandatory file skeleton

Every chapter is a standalone HTML file in this folder using this exact shape:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ch03 · Data Model &amp; Decisioning | FCB Study Pack</title>
<link rel="stylesheet" href="assets/sourcebook.css">
</head>
<body>
<div class="toolbar">
  <button onclick="window.print()">Print / Save as PDF</button>
  <a class="btn" href="index.html">Study Pack Index</a>
  <a class="btn" href="ch04_ui_constellation_dx.html">Next Chapter →</a>
</div>
<div class="book">
  <div class="cover">
    <div class="kicker">Chapter 03 · FCB Pega Deposits Study Pack</div>
    <h1>Chapter title</h1>
    <p class="subtitle">One or two sentences on what this chapter makes you able to do.</p>
    <div class="meta">
      <div><strong>14</strong><span>Sections</span></div>
      <div><strong>18</strong><span>Interview Q&amp;A</span></div>
      <div><strong>9k</strong><span>Words</span></div>
      <div><strong>A4</strong><span>Print ready</span></div>
    </div>
  </div>
  <main>
    <section><h2>Chapter map</h2><div class="toc"> ...anchor links to each section... </div></section>
    <!-- numbered sections -->
    <div class="chapnav"><a href="index.html">← Index</a><a href="ch04_ui_constellation_dx.html">Next: Chapter 04 →</a></div>
  </main>
</div>
</body>
</html>
```

`index.html` is authored separately by the lead. Always link to it anyway.

Use only the classes defined in `assets/sourcebook.css`: `.toolbar`, `.book`, `.cover`, `.kicker`,
`.subtitle`, `.meta`, `section`, `.toc`, `.grid`, `.grid3`, `.card` (+ `.blue/.green/.amber/.red`),
`.tag` (+ variants), `.answer`, `.warning`, `.dont`, `.note`, `.flow` (dark monospace block for
diagrams/code/SQL/JSON), `.formula`, `code`, `table/th/td`, `.qa` (+ `.q`), `.chapnav`,
`.pagebreak`, `.small`, `.muted`. Do not invent new classes and do not add inline `<style>`.

## 3. Depth bar (non-negotiable)

**3,500–6,000 words minimum per chapter; the ch01/ch02 exemplars run ~9,200 words and that is the
preferred level.** For every concept introduced, cover all of:

1. **Plain-English definition** — assume no prior knowledge.
2. **Why it exists** — the problem it solves; what people did before it.
3. **How Pega implements it** — exact rule type names, where it lives in Dev Studio / App Studio,
   and the real configuration fields with what each field does, as a `<table>`.
4. **A `.flow` diagram** — runtime sequence or architecture.
5. **A concrete FCB Deposits banking example** — draw from: account opening, address change,
   signer/beneficiary maintenance, account closure, CD maturity and rollover, legal process orders
   (garnishment, tax levy, subpoena, court-ordered freeze), payment exceptions (ACH/NACHA returns
   R01/R02/R03, stop payment, wire exceptions, OFAC hits), KYC/AML review, reconciliation breaks,
   dormancy and escheatment, Reg E / Reg CC / Reg DD style compliance timers.
6. **Pitfalls / anti-patterns** — what juniors get wrong; what breaks in production.
7. **Performance and security considerations** where relevant.
8. **Interview Q&A** — close every chapter with 12–20 `.qa` blocks: realistic interviewer
   questions with full model answers in Sathvik's first-person voice.
9. **Lead-level framing** — at least 2–3 `.answer` callouts per chapter contrasting a junior answer
   with a P2/P3/lead answer (architecture, reuse, supportability, failure modes, scale, governance).

Use tables heavily for config fields, comparisons and rule-type reference. Use `.flow` for
diagrams, pseudo-config, JSON/XML samples and SQL. Concrete always beats abstract.

## 4. Honesty constraint (critical — never violate)

**Genuinely done in production:** Pega case management, BPM, flows, SLAs, Data Pages, Data
Transforms, decision tables/trees, when rules, circumstancing, activities, Connect-REST,
Service-REST, Connect-SOAP, Connect-SQL (including metadata-driven MERGE), Kafka ingestion
(50+ topics, Datasets, Data Flows), Queue Processors (200K records in 5 minutes), Job Schedulers,
File Listener + SFTP, Email Listener / Email Channel, correspondence frameworks (SMS, email,
letters), Report Definitions, Tracer / Clipboard / PAL / PDC, Deployment Manager, Agile/Scrum,
24/7 L2/L3 production support, dashboards (Kafka pipeline health, Service-REST replay API),
guardrails 95+. His AI usage is **real but limited to**: AI-assisted mapping generation,
bottleneck analysis, failure pattern detection, and code review.

**NOT done in production:** Knowledge Buddy, Agentic AI, Pega Blueprint, Prediction Studio models,
CDH / Next-Best-Action strategies, Pega RPA bots, Okta administration, Splunk administration.

Therefore: for owned skills, write confident first-person model answers. For non-owned skills,
model answers must read as conceptual understanding plus concrete readiness to ramp up — never as
production experience. Any chapter covering a non-owned topic must carry a `.warning` callout
stating exactly how to frame it honestly, and should bridge to an adjacent thing he *has* done.

## 5. Style rules

- Number sections `N.1`, `N.2`… matching the chapter number.
- Put `class="pagebreak"` on major sections so PDF pagination breaks cleanly.
- No emojis. Professional, plain, direct.
- **Do not invent Pega rule names, field labels or API endpoint paths.** If unsure of an exact
  string, describe it functionally instead of guessing. He will be quizzed by real Pega people;
  accuracy outranks specificity. Where you simplify a documented algorithm, say so in a `.note`.
- Do not fabricate FCB-internal facts (team names, system names beyond those above, org charts).
- Cross-reference sibling chapters by name when a topic is covered in depth elsewhere.

## 6. Chapter manifest

| File | Chapter | Status |
|---|---|---|
| `ch01_pega_platform_core.html` | 01 · Pega Platform Core & Rule Resolution | done |
| `ch02_case_management_bpm.html` | 02 · Case Management, BPM, SLAs, Routing, Correspondence | done |
| `ch03_data_model_decisioning.html` | 03 · Data Model, Data Pages, Declarative Rules, Decisioning | done |
| `ch04_ui_constellation_dx.html` | 04 · UI: Traditional, Constellation, DX API | done (lead-edited) |
| `ch05_integration_rest_soap_esb.html` | 05 · Integration & Authentication | done (lead-edited) |
| `ch06_kafka_dataflow_queue_processors.html` | 06 · Kafka, Data Flows, Queue Processors, Job Schedulers | done |
| `ch07_file_email_listeners.html` | 07 · File Listener / SFTP / Parse Rules, Email Listener / Channel | done |
| `ch08_pega_ai_genai_decisioning.html` | 08 · Pega AI, GenAI, Knowledge Buddy, Agentic AI, Prediction Studio, CDH | done |
| `ch09_pega_rpa.html` | 09 · Pega RPA & Intelligent Automation | done |
| `ch10_security_devops_monitoring.html` | 10 · Security, Okta/SAML, Splunk, PDC, CI/CD | done (lead-edited) |
| `ch11_postgresql_sql_deep.html` | 11 · PostgreSQL & SQL for Pega Engineers | done |
| `ch12_deposits_banking_domain.html` | 12 · Deposit Operations Domain | done (lead-edited) |
| `ch13_fcb_architecture_blueprints.html` | 13 · FCB Target Architecture & Case Blueprints | done |
| `ch14_interview_question_bank.html` | 14 · Master Interview Question Bank (100+) | done (lead-edited) |

**Pack complete:** 14 chapters, ~200,000 words, 346 Q&A blocks, 653 PDF pages. All internal links and
anchors verified with zero broken references.

### Lead-verified facts (checked against primary sources — state these confidently)

These were originally hedged by the author and later confirmed; do not re-hedge them in future edits.

| Fact | Detail | Where |
|---|---|---|
| Constellation naming | From Pega Platform **8.8** all new UI tech bundled as "Constellation": Cosmos React → Constellation design system, DX API v2 → Constellation DX API, DX SDK → Constellation SDK. Constellation is the **recommended UI for new apps as of Pega '23**. Two design systems coexist post-8.8 (Constellation for the new architecture, Cosmos for Theme Cosmos / pre-8.7 apps) | ch04 |
| ARO access controls | **Open instances, Modify instances, Delete instances, Run reports, Execute activities**. Each takes an Access When rule name or a production level **0–5**; granted only when the control's level **>=** the system's production level. 0/blank = none, 5 = all systems. Levels: 1 Sandbox, 2 Development, 3 Test/QA, 4 Pre-production, 5 Production | ch10, ch13, ch14 |
| SLA processing | Queue processor **`pyProcessSLA`** (legacy: **`ServiceLevelEvents`** agent). Queue table **`System-Queue-ServiceLevel`**. Switched by the **`UseSLAQueueProcessor`** DSS; **disabled by default**; the agent must be disabled when the queue processor is enabled — they must not run concurrently | ch02, ch14 |
| Federal tax levy | **21 calendar days** under IRC §6332(c) / Treas. Reg. §301.6332-3; surrender on the **first business day after** expiry; IRS may extend; depositor may waive; purpose is settling ownership disputes | ch12, ch14 |
| NACHA return rates | Unauthorised return rate **threshold 0.5%** (from 1.0% in 2015) on **R05, R07, R10, R11, R29, R51** over the preceding 60 days / two calendar months. Administrative return rate **level 3.0%** (R02, R03, R04) and overall return rate **level 15.0%** open Nacha's inquiry process. 0.5% is a hard *threshold*; 3%/15% are *levels* triggering inquiry, not automatic violation | ch12, ch14 |

### Known soft spots (acceptable, but do not let them drift)

- Illustrative numbers appear in ch06/ch13/ch14 (the 667/s, 9 ms, 6-thread throughput model), ch09 (RPA ROI),
  ch11 (sample query plans) and ch13 (all volumes and node counts). Every one is labelled; keep it that way.
- Proposed SLA values for the same process differ slightly between ch02, ch07, ch12 and ch13 (e.g. legal-order
  restraint "same day" vs "within 4 hours"). These are proposals rather than facts, but standardise if revisited.
- Unverified regulatory figures in ch12 remain tagged `verify current` — notably the Reg CC cut-off, the OFAC
  10-business-day report, Reg E/DD periods and all state-level rules. Do not promote these to `verified` without
  checking a primary source.

### ch03 — Data Model, Data Pages, Declarative Rules, Decisioning
Properties (all types; single value / value list / value group / page / page list / page group),
property modes, Property rules vs App Studio field definitions; data classes vs work classes; data
objects / data types / App Studio data model vs Dev Studio classes; Pega-provided vs application
classes; **exposed columns vs the BLOB (`pzPVStream`)** — what the BLOB is, why exposing matters,
how to expose, reporting and performance consequences; Declare Index for embedded-page reporting;
**Data Pages in real depth** — page vs list structure, scope (Node / Requestor / Thread) with
trade-offs and thread-safety, editable vs read-only, parameterised pages and cache keying, load
strategy (Snapshot vs Reference / always-on-demand), refresh strategies (do not reload, reload if
older than, when-rule based), sourcing by Data Transform / Report Definition / Connector /
Activity / Lookup, error handling and `pxErrorMessages`, savable data pages and save plans, `D_`
naming, and when a Data Page is the wrong tool; **Declarative rules** — Declare Expression
(forward vs backward chaining, change tracking), Declare OnChange, Declare Constraint, Declare
Trigger, Declare Index, plus dependency-network and infinite-loop pitfalls; **Data Transforms** —
every action (Set, Update Page, Append to, Append and map to, Apply Data Transform, For Each Page
In, Call, When/Otherwise, Remove, Exit), superclass data transform inheritance, `pyDefault`, when
to use vs an Activity; **Activities** — why guardrails discourage them, legitimate uses, the step
methods that matter (Property-Set, Page-New, Page-Copy, Page-Remove, Obj-Open, Obj-Open-By-Handle,
Obj-Save, Obj-Delete, Obj-Browse, Obj-List, Call, Branch, Queue-For-Processing, Commit, Rollback,
Property-Map-DecisionTable, Apply-Model, Page-Set-Messages), transition conditions, step pages,
parameters, Java-step risk; **Decisioning rules** — Decision Table (conditions, results, evaluation
order, otherwise, allowed results), Decision Tree, When rules, Map Value, Decision Data rules, and
how business users maintain them; **circumstancing in depth** (single property, multi-property via
template plus circumstance definition, date-based) with a worked US-state garnishment-exemption
example; validation (Validate rule, Edit Validate, Edit Input, constraints, client vs server side);
keyed data instances and reference-data strategy for a bank. Include a `.flow` of a deposit
account/customer data model and a rendered Decision Table example.

### ch04 — UI: Traditional, Constellation, DX API
Traditional UI architecture (harness, section, layout types, dynamic layouts, repeating/table
layouts, cell properties, controls, skins, portals, flow action forms, when-rule visibility,
refresh-section-on-change, the risk of non-auto-generated sections); UI reuse and section
inclusion; client vs server validation; **Constellation architecture in depth** — view-based
authoring, the design system, the static-content microservice, why Pega moved there, what
"opinionated/prescribed" means, what you gain and lose, Constellation DX Components as the React
escape hatch and what they replace (custom controls, HTML rules, custom JS, design templates),
naming history (Cosmos React → Constellation, DX API v2 → Constellation DX API), and migration
reality (an app's UI architecture cannot be casually flipped; it is manual reconfiguration);
**DX API in depth** — traditional DX API (v1, section-based) vs Constellation DX API (v2,
view-based), what "UI metadata in the response" means and how that differs from a plain data API,
available-actions/HATEOAS style navigation, reduced chattiness, and the typical endpoint journey
(list case types → create case → fetch assignment + view metadata → submit flow action → advance
stage); Constellation SDKs (React / Angular / Web Components) and when a bank uses them (custom
customer-facing portal on the bank's own design system while Pega stays the case engine); agent
desktop / Interaction Portal concepts from Pega Customer Service and CPM (he has CS/CPM
experience — frame accordingly); dashboards and reporting widgets for deposit-ops supervisors;
accessibility and localisation for banking UIs; responsive/mobile considerations. Include a `.flow`
of the Constellation request path (browser → static content service → DX API → Pega) and a
comparison table answering "which UI architecture would you pick for FCB Deposits and why".

### ch05 — Integration & Authentication
Pega integration layer end to end: connectors vs services; Integration-Resources (Connect-REST,
Connect-SOAP, Connect-SQL, Connect-JMS, Connect-HTTP, Connect-File) and service rule types
(Service-REST, Service-SOAP, Service-Email, Service-File, Service-JMS); Service Packages, access
groups for services, and service-level authentication; **Connect-REST build sequence** in exact
order (data model first, authentication profile, Connector & Metadata accelerator or manual
creation, endpoint URL with parameters, resource path, methods, request/response Data Transforms,
JSON data transform mapping, error handling, simulation); request and response mapping patterns;
**canonical / intermediate data model** and why you never bind a case directly to a vendor payload;
SOAP specifics (WSDL import, envelope, headers, faults, MTOM attachments); **ESB / TIBCO
integration pattern** — hub-and-spoke, canonical message model, routing, transformation, throttling,
who owns retries, synchronous vs asynchronous boundaries, and what to negotiate with the
middleware team; Connect-SQL and metadata-driven MERGE (his real work — explain the pattern
properly: staging table, metadata-driven column mapping, MERGE/upsert, write-back elimination);
**resilience engineering** — timeouts (connect vs read), retry with exponential backoff and jitter,
idempotency keys, circuit breaker, bulkhead, fallback/degraded mode, and the queueing of outbound
calls (Queue-For-Processing, Connect-Wait, async connectors); error classification (transport vs
protocol vs business) and how each is handled differently; integration logging, correlation IDs
and traceability; **Authentication deep dive** — Authentication Profiles and Authentication
Services in Pega; Basic auth; API keys; **OAuth 2.0** (client credentials, authorization code,
refresh tokens, JWT structure header/payload/signature, claims, expiry, token caching, JWKS,
scopes); **SAML 2.0 / Okta SSO** (SP vs IdP, metadata exchange, assertion contents, SP-initiated
vs IdP-initiated flow, signing vs encryption, attribute mapping to Pega operator and access group,
just-in-time operator provisioning, logout); mTLS and keystore/truststore management in Pega;
SFTP key-based authentication; secrets handling and credential rotation. Include `.flow` diagrams
for the OAuth client-credentials sequence, the SAML SP-initiated sequence, and the full FCB
Pega ↔ TIBCO ESB ↔ core banking call path. Mark Okta administration as not-owned per §4.

### ch06 — Kafka, Data Flows, Queue Processors, Job Schedulers
Kafka fundamentals: broker, cluster, topic, partition, offset, replication factor, leader/follower,
ISR, producer, consumer, consumer group, rebalancing, retention, compaction, ordering guarantees
(per-partition only) and what that means for account events; keys and partitioning strategy (why
account number is the right key); delivery semantics (at-most-once, at-least-once, exactly-once)
and why at-least-once plus idempotent consumers is the practical banking choice; consumer lag as
the primary health metric; **Pega-side Kafka** — Kafka configuration instance, Kafka Dataset,
Stream vs Database vs Decision Data Store datasets, Data Flow rules (source, shapes, destination),
Data Flow run types (batch vs real-time), Data Flow service nodes and node types (Stream, Batch,
RealTime, BackgroundProcessing), resilience settings and error thresholds, Data Set Execute,
Stream service; **Queue Processors** — standard vs dedicated, immediate vs delayed queueing,
`Queue-For-Processing`, queue item lifecycle, broken items and the broken-queue, retry and
backoff configuration, commit behaviour, partitions/threads and how he reached 200K in 5 minutes
(batching, exposed columns, bulk DB writes, reduced per-item DB round trips, right-sized node
classification, avoiding per-item connector calls), scaling levers and their limits; **Job
Schedulers** vs legacy Agents — cron-style scheduling, node classification, single-node vs
all-nodes, restart behaviour, and why Agents are deprecated in favour of Job Scheduler and Queue
Processor; **event-driven design** — event contract and schema (topic name, key, version,
correlation ID, event type, timestamp, payload), schema evolution and backward compatibility,
upstream/downstream contracts, replay strategy, dead-letter topics and a replay API (his real
dashboard work), poison-message handling, duplicate detection, and ordering/late-arrival handling;
his real migration story (SSIS batch ~24 hours → real-time Kafka) framed as an architecture
decision record; monitoring (consumer lag, queue depth, broken items, PDC, dashboards, alert
thresholds, what to page on vs what to batch); capacity planning arithmetic. Include `.flow`
diagrams for the end-to-end event path, the retry/dead-letter/replay loop, and a worked throughput
calculation in `.formula`.

### ch07 — File Listener / SFTP / Parse Rules, Email Listener / Channel
**File-based integration end to end** — why banks still exchange files, and the batch window
problem; the Pega artifact chain in exact build order (Service Package → Service File → File
Listener → Parse rules → data model → case or staging table); File Listener configuration fields
in detail (source location, source name mask, listener properties, requestor type/access group,
blocked/standby behaviour, node classification, multi-node safety, polling interval, file
encoding); repository vs direct filesystem vs SFTP sourcing; **SFTP specifics** — SSH key pairs,
known-hosts, passive vs active, file naming conventions, control/trigger files (`.done` sentinel
files) to avoid reading partial uploads, archive and error directories, PGP-encrypted file
handling, file-level checksums; **Parse rules** — Parse Delimited, Parse Fixed, Parse Structured,
Parse XML, Parse JSON; parse record types, header/detail/trailer structures, mapping to clipboard
properties, and validating a trailer record count against actual rows; **processing patterns** —
raw-to-staging-to-case, chunking large files, per-record error isolation so one bad row does not
fail the file, duplicate-file prevention (file registry table on name + hash), reconciliation
counts, idempotent reprocessing, and replay of a single record vs a whole file; bank-grade
controls (file arrival SLA and missing-file alerting, dual-control for manual reprocessing,
retention, PII handling, audit evidence); **NACHA/ACH return file** and **positive-pay/legal-order
file** worked examples; **Email integration** — Email Listener vs Email Channel (and when each is
right), email accounts, Service Email, inbound mapping, attachment extraction and conversion,
threading and correlation to an existing case by reply-to/subject token, auto-reply and
out-of-office loop prevention, bounce handling, spam/phishing considerations, mailbox throughput;
Email Channel with NLP — text analyzer, topic detection, entity extraction, intent-based routing,
confidence thresholds and human fallback (clearly separating what he built with Email Listener from
NLP capability he understands conceptually); outbound correspondence linkage back to chapter 02.
Include `.flow` diagrams for the File Listener runtime path, the trigger-file handshake, and inbound
email → case creation, plus a troubleshooting table ("file arrived but no case was created").

### ch08 — Pega AI, GenAI, Knowledge Buddy, Agentic AI, Prediction Studio, CDH
**Open with the honesty frame** (`.warning`): exactly what he has done with AI (AI-assisted mapping
generation across 50+ Kafka topics, bottleneck analysis, failure-pattern detection in logs, code
review) and how to present everything else as informed conceptual knowledge. Then teach properly:
Pega's AI landscape and how the pieces relate; **Prediction Studio** — predictions vs models,
adaptive models (Adaptive Decision Manager) vs predictive models vs text analytics, the model
lifecycle (define, train, validate, monitor, champion/challenger), data requirements, outcome
labelling, model monitoring and drift, and the difference between a prediction and a decision;
**Customer Decision Hub / Next-Best-Action** — NBA Designer, the arbitration formula
(propensity × value × context weighting, with priority), engagement policies (eligibility,
applicability, suitability), treatments, channels, strategies, Decision Data, and what CDH is
actually for in a deposits context (not marketing spam — think fee-waiver decisioning, retention on
closure requests, cross-sell suitability); **GenAI in Pega** — GenAI capabilities and the general
shape of connected generative services, prompt-driven features, and the governance questions a
bank asks (data residency, PII redaction, audit, hallucination risk, human-in-the-loop, model
approval); **Knowledge Buddy** — what it is, the RAG pattern explained from first principles
(chunking, embeddings, vector search, retrieval, grounded generation, citations), collections and
curation, access control on source content, evaluation and feedback loops, and a deposit-ops use
case (ops analyst asking "what is the hold period for a court-ordered freeze on a joint account");
**Agentic AI** — what an agent is versus a workflow, tool/function calling, planning and
reflection loops, autonomy levels, guardrails and approval gates, and why banking keeps a human
decision point; **Pega Blueprint** — AI-assisted application design, what it generates, and where
it fits in delivery; **his own AI-leverage stories told well** — how he used AI for mapping
generation and log pattern detection, what he verified by hand, and why that verification habit is
the real signal of seniority. Include a `.flow` of the RAG pipeline, a `.flow` of the NBA
arbitration path, and a comparison table (deterministic rules vs predictive model vs GenAI vs
agentic — when to use which, and what a bank will and will not approve). Be rigorous: do not state
version-specific product claims you are unsure of; describe capability shape functionally instead.

### ch09 — Pega RPA & Intelligent Automation
`.warning` honesty frame first (not production-owned). Then: what RPA is and why it exists (systems
with no API: green-screen/mainframe terminals, legacy teller and core-banking front ends, vendor
portals); RPA vs API integration vs BPM — the decision framework and why RPA is a tactical bridge,
not an architecture; **attended vs unattended automation** and the Robotic Desktop Automation vs
Robotic Process Automation distinction; **the Pega RPA toolchain** — Robot Studio (building
automations), Robot Runtime (executing on a desktop/VM), Robot Manager (deploying, scheduling,
assigning work to robots, monitoring), work queues for robots, and robot pools/capacity; how a Pega
case hands work to a bot and gets a result back (queueing an assignment to a robot work queue,
bot picks it up, performs the UI steps, writes results back, case advances) and what happens on bot
failure; adapters and interrogation (how a bot identifies UI controls), control matching fragility,
and why UI changes break bots; exception handling, screenshots as evidence, and retry; **OCR and
intelligent document processing** — scanned legal orders and ID documents, OCR confidence, template
vs ML extraction, and mandatory human verification thresholds; credential handling for bots (never
hardcode; vault-based), least privilege, segregation of duties, and the audit/compliance problems
auditors raise about bots acting as a human user; operational concerns (bot infrastructure, session
management, licence/concurrency limits, monitoring, the "unattended bot failed at 2am" runbook);
**deposit-ops RPA candidates** — keying a legal-order hold into a legacy core screen, pulling
statements from a vendor portal, re-keying ACH exception details, dormancy flag updates; and a
clear lead-level `.answer` on how to argue for API-first and treat RPA as a time-boxed bridge with
a decommission plan. Include a `.flow` of the Pega case ↔ Robot Manager ↔ bot ↔ legacy app loop.

### ch10 — Security, Okta/SAML, Splunk, PDC, CI/CD
**Pega security model in depth** — operator ID, access group, access role, Access of Role to Object
(ARO) with its real access controls (Open instances / Modify instances / Delete instances / Run
reports / Execute activities) and the 0–5 production-level scale (0 = none, 5 = all systems;
granted only when the control's level >= the system's production level; 1 Sandbox, 2 Development,
3 Test/QA, 4 Pre-production, 5 Production), Access Deny, privileges, Access When conditions
(enterable in place of a numeric level), role inheritance and
dependent roles, portal and application association, and how to design roles for deposit ops
(maker, checker, supervisor, read-only auditor, ops admin) with segregation of duties;
**attribute-based access control** and client-based access control concepts; field-level and
property-level security, masking, and encryption (platform encryption/cipher, column encryption,
`pzPVStream` considerations); **authentication** cross-referenced to chapter 05 (Okta/SAML, OAuth)
with the Pega-side wiring: authentication service, operator provisioning, access group mapping,
timeout and session policy, MFA expectations; API security for Service-REST; CSRF, XSS, injection
and the OWASP Top 10 mapped onto Pega guardrails and what Pega gives you for free versus what you
must do; audit trail, field-level auditing, security event logging and tamper evidence; PII/NPI
handling, data retention and purge/archive, and masking in lower environments; **observability** —
Pega logs (PegaRULES log, alert log, exception log), ALERT severities and common alert IDs by
category (slow DB query, large clipboard, long-running connector, queue backlog), **PDC** (what it
ingests, how to read a case/alert, trending, how to use it to prove a fix worked), **Tracer** (and
why you never leave it on in production), **Clipboard**, **PAL** readings, **DB Trace**, and SQL
query analysis; **Splunk** — indexes, sourcetypes, SPL basics (`search`, `where`, `stats`,
`timechart`, `transaction`, `eval`, `rex`), correlation-ID-driven cross-system tracing, dashboards
and saved searches, and alerting (frame Splunk admin as not-owned, log analysis as owned); **CI/CD
and release** — Deployment Manager pipelines, candidate vs release systems, RAP/product rules,
branch-based development and merge, rule locking, PegaUnit tests in the pipeline, guardrail and
test gates, Jenkins/prpcServiceUtils style automation, promotion through DEV→QA→UAT→PROD, dual
control on production deployment, rollback strategy and why data/schema changes break rollback,
hotfix process, and release evidence for audit; **24/7 L2/L3 support runbook** — triage severity
matrix, first-15-minutes checklist, evidence capture, containment vs fix, comms/escalation,
RCA and the 5-whys, preventive action, and on-call handover. Include `.flow` for the incident
triage decision tree and tables for ARO design and alert-to-action mapping.

### ch11 — PostgreSQL & SQL for Pega Engineers
Relational fundamentals: tables, rows, columns, data types, NULL semantics and three-valued logic,
primary vs unique vs foreign keys, constraints, normalisation (1NF–3NF) and sensible denormalisation;
**SQL from basics to advanced** — SELECT/WHERE/ORDER BY/LIMIT, all JOIN types with worked results,
GROUP BY and HAVING, aggregates, subqueries vs CTEs, window functions
(`ROW_NUMBER`, `RANK`, `LAG`, `SUM() OVER`) with a running-balance and a latest-row-per-account
example, `CASE`, set operations, `EXISTS` vs `IN` vs `JOIN` performance, UPSERT
(`INSERT ... ON CONFLICT` in PostgreSQL vs `MERGE` in SQL Server) tied to his real MERGE work,
and bulk-load patterns (`COPY`, batch inserts, staging tables); **transactions and concurrency** —
ACID, explicit transactions, the four isolation levels with the anomaly each prevents, PostgreSQL
MVCC, row vs table locks, `SELECT ... FOR UPDATE`, deadlocks (how they happen and how to avoid
them by consistent lock ordering), long-running transaction damage, and how Pega commits
(`Obj-Save` + `Commit`, deferred saves, the Pega transaction boundary, and why a Connect call inside
a transaction is dangerous); **indexing and performance** — B-tree vs other index types, composite
index column order, selectivity, covering indexes, partial indexes, index bloat, `EXPLAIN` /
`EXPLAIN ANALYZE` read end to end (seq scan vs index scan vs bitmap heap scan, nested loop vs hash
vs merge join, estimated vs actual rows), statistics and `ANALYZE`, `VACUUM` and autovacuum,
table bloat and dead tuples, partitioning for large history tables, and connection pooling;
**the Pega database specifically** — the `pr_*` tables (`pr4_base`/work tables, `pr_data`,
`pr_sys_*`, index tables), what the BLOB column is and why Pega stores it, exposed columns and the
property-to-column mapping, `pr_index_*` / Declare Index tables, when to use a Report Definition
vs Connect-SQL vs a DB view, Optimize-for-reporting, schema change management through Pega vs DBA,
split schema (rules vs data) in regulated environments, and why direct DDL on Pega tables is
dangerous; **operational SQL for support** — finding stuck queue items, assignment counts by work
queue, SLA breach queries, reconciliation break detection, and duplicate-detection queries, each as
runnable SQL in `.flow`; backup/restore, point-in-time recovery, and read replicas at a conceptual
level. Every SQL example must use a plausible deposits schema (accounts, customers, account_holders,
transactions, holds, legal_orders, ach_returns, staging tables) that you define once up front in a
`.flow` DDL block and reuse throughout.

### ch12 — Deposit Operations Domain
This chapter is domain knowledge, not Pega. **Banking fundamentals** — what a bank balance sheet is,
why deposits are a funding source, the difference between retail/business/commercial deposits, and
where "Deposits & Shared Services" sits in a bank's org; **deposit product taxonomy** — checking/DDA,
savings, money market, CD/time deposit (term, maturity, rollover, early-withdrawal penalty), IRA and
custodial/fiduciary accounts, escrow, trust, HSA, and business accounts with signers and resolutions;
**the account lifecycle end to end** — origination and application, CIP/KYC, funding, activation,
servicing/maintenance, overdraft, dormancy, escheatment, closure, and post-closure; **account
opening and KYC/AML** — CIP minimum data, identity verification, beneficial ownership (CDD/UBO),
risk rating, sanctions screening (OFAC/SDN), PEP screening, enhanced due diligence, ongoing
monitoring, SAR/CTR concepts, and false-positive handling; **maintenance transactions** — address
and name change, signer/authorised-user changes, beneficiary/POD/TOD designation, title changes,
joint-to-individual conversion, power of attorney, deceased-account handling and estate processing,
account conversion/product change, fee waivers and rate exceptions, statement and tax-form
(1099-INT, W-8/W-9, backup withholding) handling; **holds, freezes and legal process orders** —
garnishment, tax levy (IRS and state), child-support order, subpoena, court-ordered freeze, and
law-enforcement requests; service of process, the legal hold workflow, exempt funds and state-level
exemption rules, response deadlines, customer notice requirements, remittance to the creditor,
priority when multiple orders hit one account, and joint-account complications; **payments and
exceptions** — ACH and the NACHA network (ODFI/RDFI, entry classes, settlement, return codes
R01/R02/R03/R04/R07/R10 and their deadlines), checks and Check 21 (deposit, clearing, return
reasons, duplicate presentment), stop payments, wires (domestic/Fedwire and international/SWIFT,
recall, investigation), card/debit disputes, RTP/instant payments, and **Reg E** dispute/error
resolution timelines, **Reg CC** funds-availability/hold rules, **Reg DD** disclosure and APY, and
**Reg D** history; **reconciliation and controls** — GL vs subledger, suspense and clearing
accounts, break detection, aging and resolution, dual control/maker-checker, segregation of duties,
daily proof, and audit evidence; **risk, fraud and disputes** — kiting, mule accounts, elder
financial exploitation, fraud holds; **operational metrics** — SLA/turnaround time, first-pass
yield, backlog aging, exception rate, and what an ops manager cares about. Throughout, add a
"how this becomes a Pega case type" line per process, and close with a glossary table of 60+ terms
and acronyms plus 15+ `.qa` domain questions an FCB interviewer would actually ask.

### ch13 — FCB Target Architecture & Case Blueprints
Synthesis chapter — this is where he proves lead-level thinking. **The architecture brief** — a
greenfield Pega Deposits & Shared Services platform for a US bank: actors (branch, contact centre,
ops analyst, supervisor, legal/compliance, customer self-service), surrounding systems (core
banking via TIBCO ESB, CRM, document management, Okta, Splunk, data warehouse, payment hubs,
sanctions screening, print/mail vendor), and the integration inventory with the chosen pattern for
each (sync REST, async event, batch file, ESB-mediated); **a layered application architecture** —
enterprise/org layer, framework layer, implementation layer, class and ruleset naming, reusable
component strategy, what belongs in the framework vs the implementation, and how to avoid the
"everything in one implementation layer" trap; **canonical data model** for customer, account,
hold, order and transaction, and the mapping/translation boundary; **case type inventory** for
deposits with a dependency map, and then **full blueprints** (stages, steps, routing, SLA per stage,
integrations per step, correspondence, audit points, failure handling, reporting) for at least six:
Account Maintenance, Account Closure, Legal Process Order, ACH/Payment Exception, KYC/AML Review,
and Reconciliation Break; **non-functional design** — volume and sizing assumptions, throughput
targets, batch windows, performance budget per transaction, HA/DR and RPO/RTO, node classification
and topology (web/background/stream/batch nodes), environment strategy, data retention/archival;
**governance** — guardrail policy, code review standards, definition of done, test strategy
(PegaUnit, scenario tests, integration stubs, UAT), release cadence, dual control, and audit
readiness; **migration and rollout** — pilot product/market first, parallel run, data migration and
backfill, cutover and rollback, decommissioning legacy; **a risk register** with mitigation for the
top 10 delivery risks; **the first-90-days plan** he can state in the interview; and an explicit
**"how my MBRDI experience maps to FCB"** translation table (Kafka/SSIS → ESB/core-banking events,
multi-market circumstancing → multi-state legal exemptions, collections SLAs → legal-order
deadlines, Connect-SQL MERGE → deposit reconciliation, Kafka dashboard → ops observability, 24/7
support → bank on-call). Include at least four `.flow` architecture diagrams.

### ch14 — Master Interview Question Bank
**100+ questions minimum**, grouped and numbered, each as a `.qa` with a complete model answer in
Sathvik's first-person voice — not hints. Groups: (1) tell-me-about-yourself, walk-me-through-your-
project, and why-FCB/why-leave positioning, with a tight 90-second pitch and a 5-minute deep version;
(2) Pega platform and rule resolution; (3) case management, BPM and SLA; (4) data model, data pages
and declaratives; (5) integration, REST/SOAP/ESB and authentication; (6) Kafka, Data Flow, Queue
Processor and Job Scheduler; (7) file and email integration; (8) performance tuning and
troubleshooting; (9) SQL and database; (10) security and compliance; (11) AI/GenAI/RPA conceptual;
(12) deposits domain and regulation; (13) architecture and design scenarios ("design a legal order
case type", "100K-record file must process in the batch window", "the ESB is down for 4 hours —
what happens to in-flight cases"); (14) production incident scenarios; (15) behavioural/STAR
(conflict, failure, mentoring, pushing back on a bad design, missed deadline, difficult
stakeholder) — each with a real STAR answer drawn from his actual MBRDI work; (16) lead/P2-level
questions (how do you review code, how do you estimate, how do you mentor, how do you decide
build-vs-reuse, how do you handle tech debt); (17) **questions he should ask the interviewer**,
grouped by audience (hiring manager, tech lead, architect, HR), and (18) salary/notice/logistics
framing. Add a `.warning` block listing the traps — topics where he must not overclaim (CDH,
Knowledge Buddy, RPA, Blueprint, Okta/Splunk admin) with the exact honest phrasing to use, and a
final one-page `.card` cheat-sheet of his headline metrics (4.5 years, 10+ case types, 50+ Kafka
topics, 200K records in 5 minutes, ~24 hours → real-time, 100% manual write-back eliminated,
guardrails 95+, zero-defect go-lives, 24/7 L2/L3).

## 7. Verification before reporting

1. Every file exists in `FCB_Study_Pack\` and links `assets/sourcebook.css` (relative, same folder).
2. Internal `href` links point at real sibling filenames from the manifest above.
3. Render each chapter to PDF with Chrome headless — this both validates layout and produces the
   artifact. PowerShell needs the call operator `&` for a quoted exe path; run one command per file.
   **`--user-data-dir` is required**: without it the render silently produces no file whenever the
   user has Chrome open, because the default profile is locked. This exact form is known to work:

   ```powershell
   & "C:\Program Files\Google\Chrome\Application\chrome.exe" --headless --disable-gpu --no-sandbox `
     --user-data-dir="$env:TEMP\chrome-pdf-profile" --virtual-time-budget=20000 `
     --print-to-pdf="C:\...\FCB_Study_Pack\ch03_data_model_decisioning.pdf" `
     "file:///C:/.../FCB_Study_Pack/ch03_data_model_decisioning.html"
   ```

   Chrome prints harmless GCM/registration errors to stderr and may return a non-zero exit code even
   on success. Judge success by whether the PDF file exists and its byte count, not the exit code.
   Page count: `([regex]::Matches($asciiText,'/Type\s*/Page[^s]')).Count` over the PDF bytes.

   **Chrome returns before it finishes writing the PDF.** If you re-render over an existing file and
   measure immediately, you will read the *old* file and wrongly conclude the render was a no-op.
   Always `Remove-Item` the existing PDF first, then poll until the size stops changing:

   ```powershell
   if (Test-Path $pdf) { Remove-Item $pdf -Force }
   # ...run chrome...
   $last=-1; $stable=0
   for ($i=0; $i -lt 40; $i++) {
     Start-Sleep -Milliseconds 700
     if (Test-Path $pdf) {
       $sz=(Get-Item $pdf).Length
       if ($sz -eq $last -and $sz -gt 0) { $stable++ } else { $stable=0 }
       if ($stable -ge 3) { break }
       $last=$sz
     }
   }
   ```

4. Report per file: approximate body word count, `.qa` count, table count, PDF size, and **anything
   you described functionally rather than naming exactly because you were unsure**. That last item
   is required, not optional.

## 8. Ownership

`index.html`, `assets/sourcebook.css`, this spec, `..\README.md`,
`..\sathvik_resume_fcb.html` and `..\FCB_Pega_Deposits_Interview_Prep_Master_Guide.html` are
lead-owned. Do not modify them.
