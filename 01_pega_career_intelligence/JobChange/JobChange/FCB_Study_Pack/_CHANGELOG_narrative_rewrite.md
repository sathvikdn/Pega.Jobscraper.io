# FCB Study Pack — narrative rewrite change log

Rewrite of all 14 chapters plus `index.html` from a reference sourcebook into one connected
learning story. UI, CSS (`assets/sourcebook.css` is untouched), navigation, filenames and A4 print
behaviour are unchanged. 229,105 words across 15 files. Zero broken links and zero dead anchors.

---

## 1. What changed structurally, pack-wide

### One continuing application
Every chapter now teaches through a single invented application — **Deposit Servicing**, built for a
fictional US bank called **Riverbend**. The illustrative notice appears once in `index.html` and once
in ch01 §1.0; it is not repeated per chapter. Class names keep the `FCB-Dep-` prefix so the
rule-resolution examples stay consistent.

Fixed cast, used pack-wide and nowhere contradicted:

| Role | Name | Operator ID |
|---|---|---|
| Customer | Dana Whitfield (`CUS-4417`) | — |
| Operations maker | Marcus Reed | `mreed` |
| Checker / approver | Priya Raman | `praman` |
| Developer | Sam Okonjo | `sokonjo` |
| Support engineer | Lena Fischer | `lfischer` |

Secondary customers exist only where the main journey genuinely cannot carry the process: **Victor
Osei** (`CHK-8842-0719`) for the legal order, **Harlow Freight Co.** (`CHK-8842-1055`) for the ACH
return. Dana is deliberately not given a levy *and* a dispute *and* a payment exception.

### Scenario ledger
A fixed ledger (accounts, balances, dates, case IDs, event IDs, file names) is published in ch01 §1.0
and referenced rather than restated. Cases: `AM-10417` (address change, 2–3 Mar 2026), `AC-10882`
(closure, 9–10 Mar 2026), `DS-10915` (dispute, oral notice 8 Dec 2025), `LO-20331` (legal order),
`PE-30142` (ACH return). The $200 authorisation hold that makes `CHK-8842-0117`'s ledger balance
($4,418.55) differ from its available balance ($4,218.55) is the teaching hook for ledger vs
available, and it settles at 09:40 on 9 Mar as event `EVT-55121` — consistently in ch06, ch07, ch11,
ch12 and ch13.

### Cause and effect instead of definition-first
The old pattern — definition, why it exists, field table, warning, lead-level framing, model answer —
is gone from the core reading path. Each major concept is now built as: what the application is
doing → what problem that creates → the straightforward approach → where it fails → the Pega feature
→ how it behaves at runtime → what changes in the example → what trade-off remains. The eight steps
are an authoring guide, not visible headings.

Exhaustive field lists and rare options moved to clearly marked reference blocks at the end of the
relevant chapter (`§n.R` references everywhere; ch13 gained `13.R1` and `13.R2`). Tables were kept
where they are genuine comparisons, configuration references, exact mappings or worked results — and
each is now introduced by prose that explains the concept first.

### Transitions, recaps and understanding checks
Every chapter ends with a `§n.Z "Where we are now"` recap — what the application can now do, the
mechanisms learned, and the unresolved problem that opens the next chapter. The next chapter opens on
that problem. 1–3 understanding checks per chapter are placed at genuinely hard points (concrete
question first, reasoned answer with assumptions and alternatives after), not after every section.

### Experience labels left the learning story
This partly reverses the previous accuracy pass, which had put ~290 inline evidence tags into the
prose. Chapters 01–13 are a fictional teaching story and now carry **no personal claims**, so the
tags, the "he must not overclaim" coaching and the lead-level framing blocks were removed from them.
The only tags left in ch01–ch13 are `assumed Riverbend policy`, marking invented SLAs and thresholds
so they are never mistaken for law or for FCB policy.

Personal-experience verification is consolidated into the **evidence register** at
`index.html#evidence-register`: 24 claims, each with the résumé line that supports it, a category
A–E, and what must be confirmed. Tags still appear beside individual ch14 model answers, because a
model answer is a claim's point of use.

---

## 2. Per-chapter changes

| Ch | Words | Narrative arc now | Notable technical changes |
|---|---|---|---|
| **01** Platform core | 11,304 | Dana's address-change request arrives and must behave correctly for her market and product. Rules, classes, pattern vs directed inheritance, rulesets and versions, then rule resolution as "which rule runs for Dana". Clipboard, requestors and threads as that request's working memory. Detailed resolution reference follows the worked walkthrough | Rule resolution kept as the verified five-phase model (gather → filter → rank → cache → runtime-qualify) with sort order Class → Ruleset → Circumstance → Circumstance Date → Date/Time Range → **Version last**; interleaved inheritance traversal; the ranked *list* is cached, not the resolved rule |
| **02** Case management | 11,380 | The request has to travel: intake → review → approval → fulfilment → resolution. Stages, processes and steps, then flow shapes, then a late proof-of-address and a rejection, then routing, then maker-checker. `AM-10417` end to end, with closure and the legal order as variations | SLA urgency corrected to `.pxUrgencyAssign = .pxUrgencyWork + .pxUrgencyAssignSLA + .pyUrgencyAssignAdjust`, bounded 0–100; case-urgency changes do not propagate to assignments that already exist; `pyProcessSLA` behaviour labelled release-sensitive rather than asserted |
| **03** Data and decisions | 12,710 | The case has a journey but no data. One account lookup through a data page into the case; scope explained through Marcus and Priya holding it at once; refresh through the balance changing while the case waits for Priya. Then properties, declaratives, data transforms, decision rules, circumstancing and validation as changes to that same example | **Savable data pages reconciled.** The old flat "data pages are unsuitable for transactional writes" is replaced: a savable data page is a legitimate write path; what it is unsuitable for is bulk row-by-row writes and writes needing approval, idempotency and an auditable status. Refresh strategy is framed as a business freshness decision, not only a performance one |
| **04** UI and DX | 8,557 | Marcus opens `AM-10417`, edits the address, gets a validation message, submits. Built twice — traditional section-based UI and Constellation — as two genuinely separate implementation paths, never interchangeable artifacts. Then the DX API carrying the same business action from the web channel | Release labels (`8.8 / traditional UI` vs `Infinity / Constellation`) applied to the headings where the path actually differs; the cost of switching path stated explicitly |
| **05** Integration | 16,190 | Read Dana's account from the core, then ask the core to change it and to place the hold for `AC-10882`. Then break that call three ways in order: the core goes slow, the core rejects, the core accepts but the response is lost | **Timeouts removed from the transient-retry bucket.** A lost response after a possibly successful write is an `Unknown` status, not a failure and not a safe retry; it is resolved by a status lookup on the same key. 409 is not success. **"Bulk staging cannot fail on business rules" removed** — staging still fails on constraints, type and malformed data, and partial failure is explained. Retry ownership named per hop |
| **06** Kafka and background | 14,498 | One balance event, `EVT-55121` (seq 882, partition 3), from topic through consumer, Pega processing, persistence and acknowledgement. Then production happens to it: delivered twice, delivered late, the consumer crashes mid-handling, a backlog builds, a replay is needed | Queue Processors and Job Schedulers taught as related but distinct. Kafka Data Set consumer group is monitoring-only; Data Flow manages partitions and offsets. **Timing figures de-precised** — §6.8 is "a designed experiment" and §6.14 is labelled `ILLUSTRATIVE` capacity arithmetic; the ~10 ms/record figure is order-of-magnitude arithmetic, never a measurement |
| **07** Files and email | 13,580 | A partner that can only send files, and a request that arrives as email. `RB_BAL_20260309_0730.csv` (14,207 rows) from arrival → readiness detection → parse → validate → queue → database apply → reconcile → archive. Malformed rows and a duplicate file handled without discarding the batch. Then one inbound email through identification, attachments, case creation/update and duplicate protection | Native File Listener processing kept separate from custom SFTP polling throughout |
| **08** AI and decisioning | 12,073 | Marcus cannot find the right procedure and a scanned document needs classifying. Starts from those tasks, then separates deterministic rules, predictive models, RAG and agents by the role each plays. One RAG question followed from retrieval to answer to source verification — then a wrong answer, and what evaluation and human review must catch | Kept explicitly separate from any claim of production experience; the area is category E (conceptual) in the register |
| **09** RPA | 11,301 | One legacy screen with no API, and a queued work item that needs it. The item travels into a robot and back to the case. Then the screen changes; then, separately, the robot times out after possibly completing the action — Chapter 05's unknown outcome in a new guise. Controls, reconciliation and eventual replacement follow from that | The bot treated as a privileged non-human user (least privilege, segregation of duties, audit) |
| **10** Security and operations | 15,394 | Marcus and Priya attempt different actions on `AM-10417`, showing where server-side authorisation allows and refuses, and why hiding a control in the UI is not security. Then a deployment, then an incident worked in order: symptom → evidence → hypothesis → tool → containment → verification → prevention | §10.8 explains what each of Tracer, PAL, PDC, DB trace, clipboard and Splunk actually *reveals* and what it cannot tell you, instead of listing the tools |
| **11** SQL | 18,640 | One small deposits dataset around the ledger, Dana's two accounts, Victor and Harlow Freight. Each business question gives input rows → query → result → why it is correct. Joins, aggregates and window functions as progressively harder questions. Concurrency through Marcus and Priya touching Dana's row. One slow query, one index, and why the plan improved | **PostgreSQL and SQL Server syntax separated** ("one dialect at a time"). A Pega case lock is not a database row lock, and a deferred save is not a write. `EXPLAIN ANALYZE` executes DML. Two over-broad claims qualified: vacuum needs a *long-running transaction*, not mere idleness; the BLOB is not universal |
| **12** Deposits domain | 29,412 | The life of a deposit account explained before any catalogue of rules. Then four separate worked journeys on Riverbend's ledger — a payment, a hold, a dispute (`DS-10915`) and a closure (`AC-10882`) — each with its trigger, required action, clock, exceptions and evidence | **Five distinct regulatory clocks** replace the old single-Fed-calendar assumption. Reg E business day is *per-institution*; Reg CC business day is a **fixed statutory list that excludes Juneteenth** (§229.2(g)), so a Fed holiday feed is wrong on 19 June. Reg E's 10/3/2/1 are business days while the 45 and 90 are calendar days. Reg CC availability cited to §229.10/§229.12 with the $275/$550 amounts effective 1 Jul 2025. Legal requirement is kept rigidly separate from invented Riverbend policy |
| **13** Architecture | 19,591 | **Rewritten from six disconnected blueprints into one spine.** §13.1 names the failure each boundary prevents. §13.7 (`#s13-walk`, ~4,700 words) walks `AC-10882` across seven hops — UI, case engine, data pages, the core hold call (`AC-10882-HOLD-1`) timing out into an unknown outcome, asynchronous confirmation as `EVT-55122`, disbursement to `SAV-8842-0233`, audit — stating per hop what triggered it, the rule and class, data in, what changes, clipboard vs committed, sync vs async, what Marcus sees, and the failure behaviour. §13.8 then gives the other case types as **variations** stating only what differs and why. §13.10 covers scale, failure, deployment and recovery as consequences of that design | The 28-row integration inventory and the five other blueprint tables moved to reference blocks `13.R1`/`13.R2`. "Accrued interest is $0" stated so the disbursement arithmetic ($12,040.00 + $4,218.55 = $16,258.55) is checkable. All 35 evidence tags, 15 `CLAIM` strings, both lead-framing blocks and all third-person résumé framing removed |
| **14** Interview practice | 32,540 | Receives everything personal that left the learning chapters: the design scenarios as new §14.13b (D1–D10), the first-90-days plan, the résumé mapping and the first-conversation questions. 135 model answers in 19 groups | **110 of 135 answers now carry the full practice shape** — direct answer, mechanism, one clearly labelled example, two likely follow-ups, one common mistake. The label is uniform across all 135 blocks. Hypothetical examples use the ledger so continuity holds. Unsourced regulatory figures found during conversion were removed (Q86's "at least thirty days", Q87's "twenty-five percent") and reattributed to reference data owned by Compliance |

### Deliberately *not* converted in ch14
25 blocks keep their lighter shape: §14.1 (Q1–Q8, the pitch and "why FCB"), §14.15 (Q102–Q109, STAR
scaffolds), §14.17 (questions to ask the interviewer) and §14.18 (Q117–Q122, salary and logistics). A
"mechanism" and a "common misconception" are meaningless for "what is your notice period", and
forcing the format there would pad the chapter without helping. §14.15 was retitled from
"Behavioural (STAR) answers from real MBRDI work" to "Behavioural (STAR) answer scaffolds", because
the old title asserted that every answer below it was a real event.

---

## 3. Source labelling

The previous pass left "fetched"/"verified" labels that did not reflect real retrieval. Established
during this rewrite and applied pack-wide: **`docs.pega.com` is JavaScript-rendered and returns an
empty shell on direct fetch**, so no Pega reference may carry a "fetched on <date>" label. Those are
now cited by exact title with a "search by title" instruction. No invented retrieval dates remain.

Non-Pega sources that were genuinely retrieved keep their citations with effective dates: 12 CFR
1005.2/1005.11 (Reg E), 12 CFR 229.2/229.10/229.12 (Reg CC), 89 FR 43738/43739 for the 1 Jul 2025
amounts, Docket R-1382 for the single check-processing region (effective 27 Feb 2010), IRC §6332(c),
and the Nacha rules.

---

## 4. Verification performed

- **Counts recalculated, not estimated.** Every chapter's cover badge (sections, words) matches a
  measured count; ch14's badge reads 135 model answers in 19 groups, both verified.
- **Links.** Zero broken file links and zero dead `#anchor` targets across all 15 files.
- **Ledger continuity.** Identifiers, balances, dates and event IDs checked for contradiction across
  chapters; `EVT-55121` = the 09:40 settlement and `EVT-55122` = sequence 883 are consistent in
  ch06, ch07, ch11, ch13 and ch14.
- **Leak scan.** No `Lead-level framing`, `must not overclaim`, `CLAIM —`, `verify current` or
  third-person résumé framing remains in ch01–ch13.
- **PDFs** re-rendered from the delivered HTML with `render_study_pack.mjs` (Puppeteer). Chrome in
  this environment is pathologically slow to start (~130 s launch, ~185 s first tab), so the script
  launches once and reuses a single page; `chrome.exe --print-to-pdf` hangs outright and should not
  be used here.
