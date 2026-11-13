# Narrative Rewrite Specification — authored by lead

This supersedes the teaching *style* of `_authoring_spec.md`. It does **not** supersede the
technical corrections in `_canonical_corrections*.md` — every corrected fact there stays correct.

**The goal:** a patient engineer walking the reader through building and operating one deposits
application. A problem appears, we try something reasonable, we find where it breaks, we introduce
the Pega feature that addresses it, and we watch it run.

**The bar:** rewrite the *body*. A story paragraph bolted on top of unchanged reference tables fails
this task. If a section still reads definition → why it exists → field table → warning → model
answer, it has not been rewritten.

Preserve: `assets/sourcebook.css` untouched, all existing CSS classes only, `.chapnav` structure,
filenames, A4 print behaviour. You may reorganise within a chapter and rewrite headings, but every
existing `id` that is linked from elsewhere must still exist (or every inbound link updated).

---

## PART A — THE CONTINUING APPLICATION

### A.1 The one-time notice — APPLY VERBATIM in `index.html` and in ch01 §1.0

```html
<div class="note"><strong>About the worked example.</strong> Every chapter in this pack follows one
  application: <strong>Deposit Servicing</strong>, built for a fictional US bank called
  <strong>Riverbend</strong>. The customers, accounts, balances, case IDs, staff, policies,
  thresholds, SLAs and architecture are <strong>invented for teaching</strong>. They are not First
  Citizens' architecture, data or policy, and nothing here should be read as describing any real
  bank's internal processes. Where a figure is a legal requirement rather than an invented policy,
  it is cited to the regulation. Class names keep the <code>FCB-Dep-</code> prefix purely so the
  rule-resolution examples stay consistent across chapters.</div>
```

### A.2 The cast — use these names and nothing else

| Role | Name | Operator ID | Context |
|---|---|---|---|
| Customer | **Dana Whitfield** | — | Retail customer, customer ID `CUS-4417` |
| Operations maker | **Marcus Reed** | `mreed` | Deposit Operations analyst. Work queue `DepOps-Maintenance`. Can submit, cannot approve |
| Checker / approver | **Priya Raman** | `praman` | Deposit Operations supervisor. Approves sensitive changes. Cannot be the maker on the same case |
| Developer | **Sam Okonjo** | `sokonjo` | Builds the application. Appears when we configure a rule or diagnose why the wrong rule ran |
| Support engineer | **Lena Fischer** | `lfischer` | L2/L3 on-call. Appears for incidents, queues, replay, Tracer/PAL/PDC |

Secondary customers, used **only** where the main journey genuinely cannot carry the process:

| Name | Account | Used for |
|---|---|---|
| **Victor Osei** | `CHK-8842-0719` | Legal process order / tax levy (ch12, ch13) |
| **Harlow Freight Co.** (business) | `CHK-8842-1055` | ACH return / payment exception (ch07, ch12, ch13) |

Do not invent further people. Do not give Dana a legal levy *and* a dispute *and* a payment
exception — the user explicitly rejected forcing every process onto one customer.

### A.3 Scenario ledger — these values are FIXED. Never contradict them.

**Accounts (Dana Whitfield, `CUS-4417`)**

| Account | Type | Ledger balance | Available balance | Note |
|---|---|---|---|---|
| `CHK-8842-0117` | Checking, opened 14 Jun 2019 | $4,418.55 | **$4,218.55** | A $200.00 merchant authorisation hold explains the gap. This gap is the teaching hook for ledger vs available |
| `SAV-8842-0233` | Savings, opened 14 Jun 2019 | $12,040.00 | $12,040.00 | — |

**Timeline — all dates verified against the real calendar**

| Date | Day | Event |
|---|---|---|
| 8 Dec 2025 | Mon | Dana gives oral notice of an unauthorised $212.40 debit → dispute `DS-10915`. (Reg E worked example in ch12 already uses this date and its arithmetic is verified: +10 Reg E business days = Mon 22 Dec 2025; +45 calendar days = Thu 22 Jan 2026. **Do not change these dates.**) |
| 2 Mar 2026 | **Mon** | Dana submits an address change through the web channel → `AM-10417` |
| 2 Mar 2026 | Mon | Marcus reviews it; it is flagged sensitive because the address changed within 30 days of a card reissue request |
| 3 Mar 2026 | Tue | Priya approves; fulfilment updates the core; `AM-10417` resolves |
| 9 Mar 2026 | **Mon** | Dana requests closure of `CHK-8842-0117` → `AC-10882` |
| 9 Mar 2026 | Mon | Balance check, hold placement, interest accrual, disbursement to `SAV-8842-0233` |
| 10 Mar 2026 | Tue | Closure confirmed; account status `Closed` |

**Case IDs** — `AM-10417` (address change), `AC-10882` (closure), `DS-10915` (dispute),
`LO-20331` (Victor Osei legal order), `PE-30142` (Harlow Freight ACH return).

**Event / message identifiers** for ch06 and ch07:
- Kafka topic `rb.deposits.account.balance.v1`, key = account number, partition 3 for `CHK-8842-0117`.
- Balance event IDs `EVT-55120`, `EVT-55121`, `EVT-55122` (sequence 881, 882, 883).
- Inbound file `RB_BAL_20260309_0730.csv`, trigger file `RB_BAL_20260309_0730.done`, 14,207 rows.
- Correlation ID on the core hold call: `AC-10882-HOLD-1`.

**Invented policy values** (always labelled `assumed Riverbend policy`, never as law):
address-change review goal 4 business hours / deadline 1 business day; closure target 2 business
days; sensitive-change approval threshold — any address change within 30 days of a card reissue.

Keep a visible ledger: put a compact version of the accounts + timeline + case IDs table in
**ch01 §1.0** and link back to it from later chapters rather than restating it.

---

## PART B — HOW TO TEACH EACH CONCEPT

### B.1 The cause-and-effect sequence — an authoring guide, NOT eight visible headings

For each major concept, move through: what the application is doing → what problem that creates →
the straightforward thing we might try → where that fails → the Pega feature that addresses it →
how it behaves at runtime → what changes in the worked example → what trade-off or failure mode
remains.

Render that as **flowing prose with ordinary descriptive headings**. Never emit literal headings
like "What problem does this create?". If a reader can see the scaffold, it is wrong.

**Worked illustration of the required transformation — Data Pages (ch03).**

*Wrong (what the pack does now):* a definition of a data page, then a table of the three scopes,
then a refresh-options table, then a warning, then a model answer.

*Right:* the closure screen needs Dana's balance. So does the review screen, and the fulfilment
step. The obvious approach is to call the core each time — so we do, and now one case makes five
identical calls to a system that bills per call and takes 400 ms. We need the answer remembered
once and reused, which is what a data page is. Then: who is "we"? Marcus and Priya are different
people looking at the same account, and that question is what scope answers — so introduce node,
thread and requestor *at the moment the question arises*. Then the balance changes while the case
sits in Priya's queue, which is what refresh answers. Only then, once every setting has a reason
attached, does the configuration table appear as a summary the reader can now read fluently.

### B.2 Make runtime behaviour visible

Replace "Pega processes the request" with a concrete sequence. For each runtime moment, choose the
details that matter for *this* concept — do not recite the whole checklist every time:

what triggered it · which rule runs and on which page and class · what data enters · what changes ·
what is only on the clipboard · what is actually saved and committed · what is synchronous versus
asynchronous · what the operator sees · what happens if it fails.

Teach these confusions **in context**, at the moment they bite, not as a glossary:
case vs assignment · stage vs process vs step · Data Transform vs Data Page · validation vs
authorisation · clipboard change vs persisted change · Pega case lock vs database row lock ·
queued intent vs confirmed external success · event acknowledgement vs completed business processing.

### B.3 Prose is the main format; tables are for comparisons

Rewrite the core reading path into short connected paragraphs. Keep a table when it is a genuine
comparison, a configuration reference, an exact mapping, or a worked result — and **explain the
concept in prose before the table appears**.

Move exhaustive field lists, rare options and secondary detail into a clearly marked reference
block at the end of the topic or chapter:

```html
<h3>Reference: <em>topic</em> settings in full</h3>
<p class="small muted">Skip this on a first read. It is here so you can look up a field you meet
  later; the explanation above covers everything you need to understand the mechanism.</p>
```

Reduce callout frequency hard. **Never place two callout boxes back to back**, and never more than
roughly two or three in a section. Prefer a sentence in the prose to a box.

### B.4 Introduce jargon only when the reader needs it

Give the problem first, then the name, then the mechanism, then its limits. The user's own example
is the target register:

> "The same request may arrive twice because the sender did not receive our response. We need the
> second attempt to recognise the first operation instead of placing another hold. That property is
> called idempotency."

Never stack unexplained acronyms. Reintroduce a term in half a sentence after a long gap. Assume
the reader knows Pega but **not** Kafka internals, PostgreSQL concurrency, US deposit regulation,
CDH or RPA.

### B.5 Style — match this register

Explanatory, calm, specific. No decorative dialogue, no dramatised incidents, no "imagine you
are…" openings, no exclamation. The user's model paragraph (the stale balance on the closure
screen) is the benchmark: it states what is on screen, names the real problem precisely, derives
the design response, and ends on the judgement the reader should carry away.

---

## PART C — STRUCTURE

### C.1 Chapter opening

Pick up the unresolved problem the previous chapter ended on, in two or three sentences, then state
what this chapter will make the application able to do. Include a one-line recap so the chapter
still stands alone. Use brief callbacks — "Earlier the case cached Dana's balance at intake…" —
rather than re-explaining.

### C.2 Chapter ending — APPLY to every chapter

```html
<section id="sNN-recap">
  <h2>NN.Z Where we are now</h2>
  <h3>What the application can do</h3>
  <p>…</p>
  <h3>The mechanisms behind it</h3>
  <p>…</p>
  <h3>What it still cannot do</h3>
  <p>… and that is what Chapter NN+1 takes up.</p>
</section>
```

### C.3 Understanding checks — sparing, roughly two per chapter, at genuinely hard points

```html
<div class="card blue"><strong>Check your understanding.</strong>
  <p>⟨one concrete question about the worked example⟩</p>
  <p><strong>Answer.</strong> ⟨reasoning, the assumptions it depends on, and the alternative if
    those assumptions change⟩</p>
</div>
```

Use the user's four questions where they fit: two operators opening the same case; the balance that
changed after the screen loaded; core accepted the hold but Pega timed out; a newer snapshot
arriving before an older payment delta. Do not turn sections into quizzes.

---

## PART D — EVIDENCE TAGS COME OUT OF THE LEARNING STORY

This reverses the placement, **not** the honesty, of the previous pass.

The learning story is fiction about Riverbend, so it needs no résumé tags at all. **Remove all
`CLAIM — NEEDS DETAIL`, `CONCEPTUAL`, `PROPOSED DESIGN`, `CUSTOM BUILD` and `ILLUSTRATIVE` tags,
and all "he must not overclaim" / "own this skill" / "never say" coaching, from the body prose of
ch01–ch13.** There are ~290 tags and ~15 coaching blocks; they belong in two places only:

1. **`ch14` interview-practice chapter** — where a model answer makes a personal claim, the tag
   stays, because that is the claim's point of use.
2. **A new evidence register**, `index.html` → a section `#evidence-register`, carrying the full
   claim table from `_canonical_corrections.md` Part 4: claim, résumé line, category A–E, what to
   confirm. One place, complete, not sprinkled.

Two exceptions that stay inline because they are *engineering* statements, not résumé statements:
- `CUSTOM BUILD` where the text would otherwise read as a Pega built-in (replay API, dead-letter
  topic, outbox table, circuit breaker, requeue dashboard). Reword to prose instead where possible:
  "Pega has no built-in replay API; this is something you build."
- `assumed Riverbend policy` on invented thresholds and SLAs, and the legal-vs-policy separation in
  ch12. These protect the reader from mistaking fiction for law.

Keep ch09's "RPA is conceptual" statement — but as **one** note at the top of the chapter, not
repeated per section.

**Do not invent personal achievements.** A claim appearing in the current pack is not evidence it
is true; the résumé is the only evidence, per the Part 4 register.

---

## PART E — TECHNICAL ISSUES TO FIX WHILE REWRITING

### E.1 APPLY VERBATIM — ch03, replacing the "savable data pages and save plans" treatment and
reconciling the Q6 contradiction. This is now documented, not hedged.

```html
    <h3>Writing data back: savable pages and save plans</h3>
    <p>So far the account page has been something we read. Marcus now needs to correct Dana's
      address, and the system of record is the core, not Pega. We could write an activity that calls
      a connector, and people often do — but Pega has a mechanism built for exactly this, and the
      reason to understand it properly is that it controls <em>when the write actually commits</em>.</p>
    <p>A data page's <strong>edit mode</strong> decides what may happen to it. A
      <strong>read-only</strong> page can be modified only while it loads and during post-activity
      processing; it appears in the clipboard's data page list. An <strong>editable</strong> page is
      loaded read-write so a form can bind to it — but it has <em>no refresh strategy and no save
      plan</em>, and it <em>cannot be node-scoped</em>; it appears in the clipboard's user page list
      instead. A <strong>savable</strong> page is an editable page that also carries a
      <strong>save plan</strong>: the mechanism that pushes changes back to the system of record.</p>
    <p>The save plan can be a direct database save, an activity (which is where an
      <code>Obj-Save</code> or a <code>Connect-REST</code> call would sit), a REST connector using
      POST, PUT or PATCH, or robotic automation. A plan runs when its <em>when</em> condition is
      true, and here is a detail that surprises people: save plans are <strong>not mutually
      exclusive</strong>. If two conditions are true, two plans apply. There is an
      <em>Otherwise</em> condition for the fallback case.</p>
    <p>Only a savable page can be named in the places that trigger a save: flow action
      post-processing, the <strong>Save Data Page</strong> shape after an assignment, and the
      <code>Save-DataPage</code> method in an activity.</p>
    <h4>The part that decides whether the data is really in the database</h4>
    <p>When you save a savable page you can set the <code>WriteNow</code> parameter, and it changes
      the transaction boundary. With <code>WriteNow</code> true the save happens
      <strong>immediately, as its own independent transaction</strong>. With it false the save is
      <strong>deferred</strong> and joins the larger surrounding transaction that commits later.
      With the direct <em>Database save</em> option you do not have to set it at all.</p>
    <p>This is the clipboard-versus-committed distinction with a switch on it. A deferred save has
      changed nothing that another requestor or a SQL query can see; the row appears only when the
      enclosing transaction commits. If Priya approves the address change and the case then fails
      two steps later, a deferred save rolls back with everything else — usually what you want. An
      immediate save does not, and now Pega and the core disagree.</p>
    <div class="card blue"><strong>Check your understanding.</strong>
      <p>Marcus edits Dana's address on a savable page, the flow action's post-processing saves it
        with <code>WriteNow</code> false, and the next step throws. What does the core hold, and
        what does Marcus see?</p>
      <p><strong>Answer.</strong> The core holds the old address. The save was deferred into the
        surrounding transaction, which rolled back, so nothing was written. Marcus sees the error
        and the case has not advanced — consistent, if confusing, because the screen looked as
        though the edit had been accepted. This is why a fulfilment step that must reach an external
        system is better modelled as an explicit integration step with its own status, rather than
        as a side effect of saving a page: with <code>WriteNow</code> true you would instead have the
        opposite problem, a committed core change behind a failed case.</p></div>
    <h4>So is a data page the wrong tool for writes?</h4>
    <p>Not as a rule, and the pack previously overstated this. Writing a single object back to its
      system of record is precisely what savable pages and save plans are <em>for</em>, and they
      save you hand-written persistence logic. What they are poor at is different and narrower:
      <strong>bulk row-by-row work</strong>, where one save per row means one call per row and a set-based
      operation in the database would do the whole job (Chapter 05 §5.8, Chapter 11); and
      <strong>writes that must carry business validation, approval and an audit trail</strong>, where
      the right model is a case step with an Integrator, an idempotency key and a visible status,
      because a save plan buried in post-processing is invisible to the business and hard to retry.</p>
    <p>So the honest rule is about <em>which write</em>, not about data pages: a maintenance screen
      editing reference or customer data is a good fit; placing a hold on Dana's account during
      closure is not, because that needs approval, idempotency and a recoverable status.</p>
```

Then fix ch03 Q6 and the matching ch14 answer: replace "for transactional writes" with "for bulk
row-by-row writes, and for writes that need approval, idempotency and an auditable status — a
single-object write back to a system of record is what savable pages are for."

Also correct the ch03 scope/refresh material with these documented facts, which remove the
"release-dependent restrictions" hedge: editable pages cannot be node-scoped and have no refresh
strategy or save plan; **Reload once per interaction is available only for thread or requestor
scope**; a node-scope page on a class carrying access control policies raises a **severe guardrail
warning**; and for Customer Service chat, associate requestors hold their own copy of
requestor-level pages, so an editable requestor page edited in one chat is not seen in another.

### E.2 ch05 §5.8 — "Staging first … cannot fail on business rules" is wrong. Replace that cell with:

Bulk insert into staging avoids *row-by-row Pega round trips* and defers *application-level* rule
evaluation — that is the real benefit. It is **not** failure-free. A bulk load can still fail on
NOT NULL and CHECK constraints, unique/primary-key violations, foreign keys, type and length
conversion, encoding, and malformed input. It can fail **partially**: depending on the load method
and transaction scope you may get all-or-nothing, or a committed prefix with the rest rejected, and
you must know which. Business rules are not escaped either — they are *moved*, either into the
MERGE's conditions or into a validation pass over staging, and whatever they reject still needs a
reject table, a count and an owner. State the loader's error-handling mode explicitly rather than
assuming rows "cannot fail".

### E.3 ch05 — timeouts must not sit inside the transient-retry bucket

A timeout on a **read** is transient and safely retryable. A timeout on a **write that may have
succeeded** is an *unknown outcome*, and retrying it is a decision, not a default. Audit the retry
tables and the `TRANSIENT` classification lines: split them into "transient and safe to retry" and
"unknown outcome — resolve by status lookup, a contractually safe retry, or reconciliation". The
§5.9 unknown-outcome material already says this; the classification tables upstream still
contradict it. Make them agree.

### E.4 ch06 — keep the illustrative arithmetic, drop the false precision

The 200K-in-5-minutes breakdown should read as an order-of-magnitude reconstruction: ~667 records/s,
and a per-record budget of *roughly ten milliseconds* across however many threads. Remove "9 ms"
and "6 threads" as if measured; present it as "if six threads each handled a record in about ten
milliseconds, you would land near this throughput — which is how you sanity-check a target, not a
measurement of what happened." Frame it as a designed experiment the reader could run.

### E.5 Source labelling — this matters and the current labels are wrong

I established today that **`docs.pega.com` is JavaScript-rendered: every bundle URL returns an empty
shell on direct fetch.** The page content I have came from search-engine indexing. So:

| Source family | Honest label |
|---|---|
| `academy.pega.com` topics | `directly retrieved 2026-10-12` — these do return full content |
| `docs.pega.com` bundle pages | `content via search index 2026-10-12; page is JavaScript-rendered and not directly retrievable` |
| eCFR API, CFPB, federalregister.gov, govinfo.gov | `directly retrieved 2026-10-12` |
| `kafka.apache.org`, `postgresql.org`, RFCs, OWASP | `URL verified 2026-10-12` (HTTP 200 confirmed) |

**Never write "fetched" or "verified" for something that was not.** Replace the bare
`https://docs.pega.com` / `https://academy.pega.com` homepage citations in ch04, ch07, ch08, ch09
and ch10 with topic-specific URLs where one can be identified by title through search; where none
can, cite the document **title** and say the URL could not be confirmed. Do not invent paths.

Verified-today additions for ch03's references, replacing the broken
`.../bundle/platform/.../data-page-definition.html` (that URL returns an empty shell):
- `https://docs.pega.com/bundle/platform-241/page/platform/data-integration/data-page-definition.html` — scopes, the three edit modes, editable-page restrictions, reload-once-per-interaction limited to thread/requestor, node-scope guardrail warning.
- `https://docs.pega.com/bundle/platform-25/page/platform/data-integration/savable-data-pages.html` — save plan options, save triggers, `WriteNow` semantics.
- `https://docs.pega.com/bundle/platform/page/platform/data-integration/configure-save-plan-inf-studio.html` — save plans not mutually exclusive, the `Otherwise` condition.

### E.6 Counts and links

Recalculate every `.meta` badge (`Sections`, `Interview Q&A`, `Words`) from the delivered file, and
every TOC entry, after rewriting. Confirm `.chapnav` and all cross-file links point at real
filenames, and that every `href="#…"` has a matching `id`.

---

## PART F — PER-CHAPTER ARCS

Each chapter opens on the previous chapter's unresolved problem and closes on the next one's.

| Ch | Opens with | Teaches through | Hands forward |
|---|---|---|---|
| 01 | Dana's address-change request arrives and the application must behave correctly for *her* market and product | Rules, classes, inheritance, rulesets, rule resolution — all through variations of this one request. Two versions of one rule plus a circumstance; walk the candidate list and show which runs and why. Clipboard, requestors and threads as the same request's working memory. Detailed rule-resolution tables go to a reference block *after* the worked walkthrough | We can select the right rule, but nothing yet moves the request through review and approval |
| 02 | The request needs to travel: intake → review → approval → fulfilment → resolution | Stages, processes, steps, assignments, routing, SLAs — each introduced when the journey needs it. Let Dana's proof-of-address arrive late, and let Priya reject once. Child cases only where ownership genuinely separates. Alternate flow shapes as variations | The lifecycle works but the case has no real data: the balance and address come from somewhere |
| 03 | The case needs account data it does not own | One account lookup through a data page into the case. Scope through Marcus and Priya; refresh through the balance changing in Priya's queue. Then properties, declaratives, decision rules, validation, circumstancing — all as changes to this same example. Includes E.1 verbatim | Data is right, but no one can see or edit it |
| 04 | Marcus opens `AM-10417`, edits a field, gets a validation message, submits | Traditional UI and Constellation as two genuinely separate implementation paths for this one interaction — never interchangeable artifacts. DX API through the web channel completing the same address change | The screen is there; the core still knows nothing |
| 05 | Read Dana's account from core, then ask core to change it | Request mapping, authentication, connector execution, response mapping, case update. Then make core slow, then make it reject, then lose its response. Timeouts, unknown outcomes, idempotency, retries, async fulfilment emerge from those three failures. Includes E.2 and E.3 | Point-to-point works but data is stale between batch runs |
| 06 | Balances are up to a day old | One balance event (`EVT-55121`, seq 882, partition 3) through topic, partition, consumer, Pega processing, persistence, acknowledgement. Then duplicates, out-of-order, a crash, a backlog, a replay. Queue Processors and Job Schedulers as related but distinct. Includes E.4 | Events cover one partner; another sends only files, and a third emails |
| 07 | A partner can only send files; another request arrives by email | `RB_BAL_20260309_0730.csv` from arrival → readiness detection → parse → validate → queue → database apply → reconcile → archive. Malformed rows and a duplicate file without losing the batch. Native File Listener kept separate from custom SFTP polling. Then one inbound email → identification → attachments → case creation/update → duplicate protection | Volume is handled; judgement work still falls on people |
| 08 | Marcus cannot find the right procedure; a document needs classifying | Start from the task, then separate deterministic rules, predictive models, RAG and agents by the role each plays. One RAG question from retrieval to answer to source check. Then a wrong answer, and what evaluation and human review must catch | Some systems have no interface at all |
| 09 | One legacy screen has no API | A queued work item into a robot and back to the case. The screen changes; the robot times out after possibly completing the action. Controls, reconciliation, replacement | Everything now works — and anyone could do anything |
| 10 | Marcus tries to approve his own change; Priya tries something else | Where server-side authorisation allows or refuses, and why UI hiding is not security. Then a deployment, then an incident: symptom → evidence → hypothesis → tool → containment → verification → prevention. Explain what Tracer, PAL, PDC and logs each actually reveal | Reports and reconciliation need the database directly |
| 11 | A business question about the deposits data | Small fixed dataset. Question → input rows → query → result → why it is correct. Joins, aggregates, window functions as progressively harder questions. Concurrency through two sessions on Dana's row. One execution plan, one change, why it improved | We can build it; we have not justified the rules the business imposes |
| 12 | Why the account lifecycle exists before any regulation is named | Lifecycle first. Then a payment, a hold, a dispute (`DS-10915`), a closure as separate journeys. Per regulation: trigger, required action, clock, exceptions, evidence. Legal requirement rigidly separated from invented Riverbend policy. Dated examples with stated assumptions | We have parts; how do they fit and scale? |
| 13 | Revisit the application built across twelve chapters | Why each boundary exists. One complete request across UI → case engine → integration → core → async confirmation → audit. Then scale, failure, deployment, recovery. Other blueprints as *variations* on this one, not six repetitions | Understanding must become answers |
| 14 | Turning understanding into concise answers | Per important question: short direct answer · mechanism · one example (confirmed or clearly hypothetical) · two follow-ups · one common misconception. **Not** a second textbook — keep teaching in the chapters and cross-reference | — |
