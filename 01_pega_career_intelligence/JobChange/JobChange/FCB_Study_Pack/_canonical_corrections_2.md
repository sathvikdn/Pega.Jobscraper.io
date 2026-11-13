# Canonical Corrections, part 2 — authored by lead

Same rules as `_canonical_corrections.md`: APPLY VERBATIM means paste as written; DIRECTIVE means
follow the instruction in the existing chapter voice. Existing CSS classes only. No UI changes.

---

## PART 6 — INTEGRATION CORRECTNESS (ch05, ch06; referenced in ch13, ch14)

ch06's Kafka fundamentals are already correct — keep them. What follows sharpens the parts that are
currently blurred. Three conflations are doing the damage and must be pulled apart everywhere.

### 6.1 APPLY VERBATIM — add to ch06 §6.4 (idempotency), before "Making a consumer idempotent"

```html
    <h3>Three things that get called "idempotency" and are not the same</h3>
    <p>Most incorrect designs come from solving one of these and assuming the other two came free.</p>
    <table>
      <tr><th>#</th><th>Concern</th><th>Question it answers</th><th>Mechanism</th><th>What it does <em>not</em> give you</th></tr>
      <tr><td>1</td><td><strong>Duplicate-event detection</strong></td><td>"Have I seen this exact event before?"</td><td>Event ID with a unique constraint; a processed-events table</td><td>Nothing about whether applying it twice would be harmful, and nothing about ordering</td></tr>
      <tr><td>2</td><td><strong>Idempotent state change</strong></td><td>"If I apply this twice, is the end state the same?"</td><td>Absolute writes (<code>SET balance = 500</code>), latest-wins guards, <code>WHEN MATCHED AND source_ts &gt; target_ts</code></td><td>Safety for <em>relative</em> operations. <code>balance = balance - 50</code> is not idempotent no matter how clean the guard is</td></tr>
      <tr><td>3</td><td><strong>Safe business operation</strong></td><td>"Is it acceptable to the business if this happens twice?"</td><td>Natural keys and business invariants: "an account can only be closed once", "one levy hold per order number"</td><td>Protection against two <em>different</em> events racing to a contradictory state</td></tr>
    </table>
    <div class="note"><strong>Say it like this:</strong> "De-duplication stops the same event being
      processed twice. Idempotent state changes make it harmless if it is. A safe business operation
      means the outcome is correct even so. I design for all three, because event-ID de-duplication
      alone fails the moment a retry arrives after the de-duplication record has aged out."</div>

    <h3>Event shape decides which guard is legal</h3>
    <table>
      <tr><th>Event shape</th><th>Payload</th><th>Safe to drop a stale one?</th><th>Correct guard</th></tr>
      <tr><td><strong>Full-state snapshot</strong></td><td>The entire current state of the entity</td><td><strong>Yes.</strong> A newer snapshot fully supersedes an older one</td><td>Latest-wins on source sequence. Dropping the older event loses nothing</td></tr>
      <tr><td><strong>Partial update</strong></td><td>Only the fields that changed</td><td><strong>No — per entity.</strong> Only per <em>field</em></td><td>Per-field version/sequence, or merge semantics. A single row-level latest-wins silently discards a different field's valid update</td></tr>
      <tr><td><strong>Transactional / delta event</strong></td><td>A change to apply, not a state to assume (a $50 debit)</td><td><strong>Never.</strong> Every event is independently meaningful</td><td>De-duplicate by event ID and apply <em>all</em> survivors. Latest-wins here destroys money</td></tr>
    </table>
    <div class="dont"><strong>The most dangerous single line in event-driven banking:</strong>
      "apply only if the timestamp is newer than what we have." It is correct for snapshots and
      <em>catastrophic</em> for payments. Two debits of $50 and $30 on the same account in the same
      second are both valid; a latest-wins guard keeps one and silently drops the other, and the
      ledger is wrong by $50 with no error anywhere. Before writing a latest-wins guard, say out loud
      which of the three shapes the topic carries. If a topic mixes shapes, that is the defect.</div>

    <h3>Ordering metadata: what to carry and what can still go wrong</h3>
    <table>
      <tr><th>Problem</th><th>Why a timestamp alone fails</th><th>What to do</th></tr>
      <tr><td><strong>Clock skew</strong></td><td>The producer's clock is authoritative for nothing. Two producers, or one after an NTP correction, can emit a "newer" event with an older timestamp</td><td>Carry a <strong>source sequence number</strong> issued by the system of record, monotonic per key. Treat the timestamp as diagnostic, not as the ordering key</td></tr>
      <tr><td><strong>Equal timestamps</strong></td><td>Millisecond resolution collides under load, so <code>&gt;</code> drops a valid event and <code>&gt;=</code> re-applies one</td><td>A sequence number makes ties impossible. If you genuinely only have a timestamp, you need a documented deterministic tiebreak</td></tr>
      <tr><td><strong>Gaps</strong></td><td>Seq 7 arrives when you last applied 5: event 6 is missing, lost or merely late</td><td>Decide explicitly — park and wait with a timeout, or apply and flag. Never silently accept the gap. A gap that is never reported is an invisible data-loss bug</td></tr>
      <tr><td><strong>Late arrivals</strong></td><td>Seq 4 arrives after 7 has been applied</td><td>For snapshots, discard. For deltas, it must still be applied — which means the state model has to tolerate out-of-order arithmetic, or the event goes to a repair queue</td></tr>
    </table>

    <h3>Kafka's ordering guarantee stops at the Data Flow</h3>
    <p>This is worth being precise about, because it is the thing most candidates get wrong after
      correctly reciting "order is per partition".</p>
    <div class="flow">Kafka partition (ordered)      ->   Data Flow reads in order       ->   OK so far
                                    |
                                    v
                        Queue-For-Processing / queue items
                                    |
                 +------------------+------------------+
                 v                  v                  v
            QP thread 1        QP thread 2        QP thread 3     <-- INDEPENDENT execution
                 |                  |                  |
                 +------------------+------------------+
                                    v
                            ORDER IS NOW LOST

Partition ordering buys you nothing once work is dispatched to independently executing
queue items. Two events for the SAME account, correctly ordered in the same partition,
can be committed in either order by two threads.</div>
    <div class="warning"><strong>So "I keyed by account number, therefore ordering is safe" is
      incomplete.</strong> The key gets the events into one partition in the right order; it does
      nothing about what happens after dispatch. If strict per-account order must survive, you need
      one of: processing inline in the Data Flow without re-queueing; a per-key lock so only one
      thread handles an account at a time (Pega's case lock gives you this when the key is the case);
      or — the usual answer — a consumer designed not to need order, using a sequence guard.
      <span class="tag">pattern</span></div>

    <h3>Kafka transactions do not cover your database or the core</h3>
    <p>Kafka's transactional producer gives atomicity <strong>within Kafka</strong>: writes across
      topics and partitions plus the consumer offset commit succeed or fail together. The moment the
      effect leaves Kafka — a row in PostgreSQL, a REST call to the core banking system — it is
      outside that transaction. There is no two-phase commit between Kafka and the core.</p>
    <div class="formula">INSIDE  Kafka transaction:   produce to topic(s)  +  commit consumer offset
OUTSIDE it:                  your DB write,  the core banking call,  the email you sent</div>

    <h3>The atomic boundary that actually matters</h3>
    <p>De-duplication only works if recording "I have seen event X" and applying X's business effect
      are in the <strong>same</strong> transaction. Split them and you have created the bug you were
      trying to prevent, in one direction or the other:</p>
    <table>
      <tr><th>Order</th><th>Crash in the gap</th><th>Result</th></tr>
      <tr><td>Record event ID, commit; then apply effect</td><td>After the first commit</td><td><strong>Lost update.</strong> The retry sees the ID, concludes "already processed", and skips. The effect never happens — silently</td></tr>
      <tr><td>Apply effect, commit; then record event ID</td><td>After the first commit</td><td><strong>Duplicate.</strong> The retry does not see the ID and applies the effect again</td></tr>
      <tr><td><strong>Both in one transaction</strong></td><td>Anywhere</td><td><strong>Correct.</strong> Either both happened or neither did; the retry is clean</td></tr>
    </table>
    <div class="note">When the effect is a <em>local</em> database write this is easy — one
      transaction, insert the event ID and the business row together, and let the unique constraint
      on event ID be your de-duplication. When the effect is a <em>remote</em> call it is impossible,
      and you fall back to an idempotency key the remote side honours, plus reconciliation. Knowing
      which of those two situations you are in is the whole design.</div>

    <h3>Is Queue-For-Processing a transactional outbox?</h3>
    <div class="warning"><strong>Do not assert that it is.</strong> A transactional outbox requires
      that the queued item be committed in the <em>same database transaction</em> as the business
      write. Whether Pega's <code>Queue-For-Processing</code> does that — rather than committing
      independently — is release- and configuration-dependent, and I have not verified it for any
      specific release. It matters enormously: if the queue write commits separately, you have a
      dual-write and either the business row or the queue item can survive alone.
      <span class="tag amber">verify on your release before claiming it</span>
      <br><br><strong>How to settle it on the deployed version:</strong> in a lower environment, run
      an activity that performs a business write, then <code>Queue-For-Processing</code>, then
      deliberately throws before any explicit commit. Inspect whether the queue item exists. Repeat
      with the rollback after the commit point. That ten-minute experiment is a better interview
      answer than any assertion.
      <br><br><strong>What to say:</strong> "I would not claim Pega's queueing is a transactional
      outbox without proving the commit boundary on that release. If it is not, the outbox has to be
      an explicit table written in the same transaction as the business change, with a separate
      dispatcher." <span class="tag amber">CUSTOM BUILD</span></div>
```

### 6.2 APPLY VERBATIM — add to ch05 in the REST/idempotency area

```html
    <h3>HTTP 409 on an idempotency key is not a success signal</h3>
    <p>A tempting shortcut: "I sent the payment with an idempotency key, got 409 Conflict, so the
      original must have worked — treat it as success." That is unsafe. 409 means the server refused
      because of a conflict; it does not tell you what the conflicting thing <em>was</em>, or how it
      ended.</p>
    <table>
      <tr><th>What 409 might actually mean</th><th>Correct conclusion</th></tr>
      <tr><td>Same key, same payload, original succeeded</td><td>Safe to treat as success — <em>only</em> if the contract guarantees this</td></tr>
      <tr><td>Same key, same payload, original <strong>failed</strong> or is still in flight</td><td>Not success. You must look up the outcome</td></tr>
      <tr><td>Same key, <strong>different</strong> payload</td><td>A genuine client bug — key reuse across different requests. Must alert, never retry</td></tr>
      <tr><td>Conflict on something unrelated (a business-state conflict, e.g. account already closed)</td><td>Not an idempotency response at all</td></tr>
    </table>
    <p>So: check the API contract for what 409 means <em>on this endpoint</em>; confirm the original
      payload matches; and establish the original operation's outcome before concluding anything.
      If the contract does not define 409 for replayed keys, a 409 is an error, not a receipt.</p>

    <h3>The unknown outcome — the case everyone forgets</h3>
    <p>You call the core to post a transaction. The core processes it successfully. The response is
      lost — timeout, connection reset, pod restart. You now hold <strong>no information</strong>.
      This is not a failure; it is an <em>unknown</em>, and it is the single most important state in
      financial integration because the two wrong moves are both expensive.</p>
    <div class="dont"><strong>Both naive responses are wrong.</strong> Retrying blindly can
      double-post. Marking it failed can lose a payment the customer has already been debited for.
      "Timeout means it failed" is the assumption that produces duplicate payments in production.</div>
    <table>
      <tr><th>Resolution route</th><th>When it applies</th></tr>
      <tr><td><strong>Status lookup</strong> — query the core by your correlation ID to find out what happened</td><td>Best, when the core exposes it. Design for this by sending a client-generated ID on <em>every</em> write</td></tr>
      <tr><td><strong>Contractually safe retry</strong> — resend with the same idempotency key, relying on a documented guarantee that the core will not double-apply</td><td>Only when the contract states it. Not an assumption you may make</td></tr>
      <tr><td><strong>Reconciliation</strong> — park the item in an unknown-outcome state and settle it against the core's end-of-day file</td><td>The backstop. Needs a real queue and a real human process, not a log line</td></tr>
    </table>
    <div class="note">Model this as a distinct case status — <code>Unknown</code>, not
      <code>Failed</code> — so it is visible, countable and alertable. An unknown-outcome queue with
      zero items is a healthy signal; the same items hidden inside a generic error bucket are a
      future audit finding.</div>

    <h3>Who owns the retry at each hop</h3>
    <p>Retries multiply. Three hops each retrying three times is up to 27 attempts at the core from
      one business event, which is how a modest incident turns into a self-inflicted denial of
      service.</p>
    <div class="flow">Caller  --3 retries-->  Pega  --3 retries-->  ESB  --3 retries-->  Core      = up to 27 calls

RULE: exactly ONE layer owns retrying for any given failure class.
      Everyone else fails fast and propagates.

Typical split:
  Connector timeouts / 5xx / connection resets ....... Pega connector or the QP, ONCE
  Business rejections (4xx that are not 408/429) ..... never retried, routed to a human
  429 / Retry-After .................................. honoured at the hop that received it
  Whole-message failure after retries exhausted ...... dead-letter, then replay on purpose</div>
    <p>Write the ownership down per integration — the retrying layer, the count, the backoff, and
      what happens when it is exhausted. "Everything retries three times" is not a design.</p>
```

### 6.3 APPLY VERBATIM — failure walkthroughs; place at the end of ch06 §6.4 or as a new
`<h3>` block in ch05, whichever reads better. Keep all five together.

```html
    <h3>Five failure walkthroughs</h3>
    <p>Each is a real sequence, not a category. If you can narrate these, you will outperform most
      candidates at this level.</p>

    <div class="card amber"><strong>A. Crash after the database update but before the acknowledgement.</strong>
      <p>The consumer updated the account row and committed, then the pod died before committing the
        Kafka offset. On restart the same event is redelivered — this is at-least-once working as
        designed, not a fault.</p>
      <p><strong>Correct behaviour:</strong> the event ID was inserted in the <em>same</em>
        transaction as the update, so the retry hits the unique constraint, recognises the duplicate
        and commits the offset without re-applying. <strong>If instead</strong> the event ID is
        written separately, this is precisely the split-boundary bug above.
        <strong>Test:</strong> kill the node mid-batch and assert row counts are unchanged after
        recovery.</p></div>

    <div class="card amber"><strong>B. The core succeeds but the response is lost.</strong>
      <p>Pega posts a $500 debit; the core applies it; the gateway times out at 30s.</p>
      <p><strong>Correct behaviour:</strong> do not retry and do not fail. Move to
        <code>Unknown</code>, then resolve by status lookup on the correlation ID sent with the
        original request. If no lookup exists, hold for reconciliation against the core's end-of-day
        file. <strong>The wrong answer in an interview is "retry with the idempotency key"</strong>
        unless you also say the contract guarantees de-duplication for that endpoint.</p></div>

    <div class="card amber"><strong>C. A replay arrives after newer events.</strong>
      <p>Support replays yesterday's events at 14:00 to recover a gap. Account 123 has already
        received today's events.</p>
      <p><strong>Correct behaviour depends entirely on event shape.</strong> Snapshots: the sequence
        guard discards the stale replay — safe. Deltas: the replayed debit is a <em>real</em> debit
        and event-ID de-duplication is the only thing standing between you and double-posting; if the
        de-duplication window has aged out, you will re-apply it. <strong>Therefore:</strong> the
        de-duplication retention must be at least as long as the replay window, and replay must be
        scoped by key and time range rather than "replay the topic".
        <span class="tag amber">CUSTOM BUILD</span></p></div>

    <div class="card amber"><strong>D. Two duplicate requests arrive concurrently.</strong>
      <p>Not sequentially — at the same instant, on two nodes. Both check "have I seen this event
        ID?", both see no, both proceed.</p>
      <p><strong>A read-then-write check cannot fix this</strong>, however carefully written; the
        window between the read and the write is the bug. The fix is a <strong>unique constraint on
        the event ID</strong> so the database arbitrates: one transaction commits, the other gets a
        constraint violation and treats it as a duplicate. In Pega, the case lock does the same job
        when the work is keyed to a case. <strong>Test:</strong> fire the same event from two threads
        simultaneously and assert exactly one effect.</p></div>

    <div class="card amber"><strong>E. An older partial update arrives after a newer update to a different field.</strong>
      <p>Event 1 (seq 5) changes the address. Event 2 (seq 6) changes the phone number. They arrive
        out of order: 6, then 5.</p>
      <p>A row-level latest-wins guard rejects event 5 because seq 5 &lt; seq 6 — and
        <strong>the address change is silently lost</strong>, even though the two events never
        conflicted. This is the partial-update trap from the table above, and it produces no error
        anywhere. <strong>Options:</strong> per-field sequence tracking; publish full-state snapshots
        instead of partial updates (usually the right answer); or merge non-overlapping fields and
        apply latest-wins only per field. <strong>Test:</strong> deliver a two-field update pair in
        reverse order and assert both fields are correct.</p></div>
```

### 6.4 DIRECTIVE — sweep ch05, ch06, ch13, ch14

Remove or correct any surviving text that: equates queueing with an outbox; says a timeout means
failure; treats 409 as success; claims exactly-once end to end; or claims ordering is guaranteed
because of the key. Cross-reference these new blocks rather than restating them (item 10).

---

## PART 7 — RELEASE DISCIPLINE (all chapters)

Apply the Part 0.2 labels. Priorities, highest first:

1. **Anything described as a Pega feature that is actually a build.** Dead-letter *topics*, replay
   APIs, requeue dashboards, circuit breakers, idempotency stores, reconciliation jobs. Every
   mention gets `CUSTOM BUILD`. The Kafka dashboard (claim 12) is his own build — correct, and it
   must not read as a platform capability.
2. **Thread-scope data pages.** The pack says "one case tab". Correct it: thread scope is
   **requestor-thread** scoped. A thread usually corresponds to one open case tab in the traditional
   portal, but that is a consequence of how the portal allocates threads, not the definition — and it
   does not hold in Constellation or for background requestors. State the definition, then the
   common case, in that order.
3. **Savable data pages.** Verify scope/mode restrictions and refresh behaviour against the docs for
   the stated release before asserting; if you cannot verify, state the constraint as
   release-dependent and name the screen that confirms it. Do not guess.
4. **Exact endpoints, config fields, rule methods, queue limits, node behaviour.** Where the pack
   gives a specific DX API path, DSS name, or numeric limit, either verify it or demote it to an
   approximate label clearly marked as such. **Never present an unverified label as an executable
   instruction** — that is the failure mode that embarrasses him in a live exercise.
5. Separate 8.8.x / traditional UI from later Infinity / Constellation wherever both are discussed —
   ch04 especially.

---

## PART 8 — SQL AND CODE (ch05, ch06, ch07, ch11)

- **Dialect separation.** Every SQL block gets a visible PostgreSQL or SQL Server label. Never a
  blended example. `MERGE` is SQL Server (and PG 15+); `INSERT … ON CONFLICT` is PostgreSQL. If the
  pack shows `MERGE` as PostgreSQL, fix it or state the version requirement.
- **UPSERT concurrency.** Note that `ON CONFLICT`/`MERGE` still need the right unique index, and that
  **duplicate source keys inside one statement** are a distinct failure — SQL Server `MERGE` raises
  an error; PostgreSQL `ON CONFLICT` cannot update the same row twice in one command. Show
  de-duplicating the source set first.
- **Parameter binding.** Values are always bound parameters. Identifiers (table/column names) cannot
  be bound — those require an **allow-list**, never string concatenation. Show both.
- Atomic event de-duplication and apply: one transaction (Part 6).
- Claim expiry / concurrent workers: show `FOR UPDATE SKIP LOCKED` and an expiry timestamp so a dead
  worker's claim is recoverable.
- **Money is `NUMERIC`/`DECIMAL`, never float.** Timestamps: `timestamptz` in PostgreSQL;
  `datetimeoffset` in SQL Server. Say why.
- **Pega case locks are not database row locks.** A Pega lock is a logical lock in the lock table
  held for the requestor; a DB row lock is held for the transaction. They have different lifetimes,
  different timeouts and different failure modes. Keep the two separate wherever the pack discusses
  concurrency.
- **Deferred saves are not writes.** `Obj-Save` without `Obj-Commit` leaves the change in the
  deferred-save list; it is not in the database and is invisible to other requestors and to SQL. Be
  explicit about where the actual commit happens.
- **Qualify these two over-broad claims** currently in ch11:
  - "every idle read-only transaction prevents vacuum cleanup" → it is specifically a **long-running
    transaction holding an old snapshot** (`idle in transaction` is the dangerous state, not `idle`)
    that holds back the xmin horizon. An idle connection with no open transaction does not.
  - "the BLOB is always the sole source of truth" → exposed columns are **copies** maintained by Pega
    for reporting/indexing, and the BLOB is authoritative for properties stored in it — but not every
    class is BLOB-backed (external/mapped classes, Pega-managed system tables), and columns can be
    exposed and optimised. State the rule and its exceptions.
- **`EXPLAIN ANALYZE` executes the statement** — including `UPDATE`/`DELETE`/`INSERT`. Say so
  plainly. Mark destructive examples with `<div class="dont">` and show the safe pattern: wrap in
  `BEGIN; … ROLLBACK;`, or use plain `EXPLAIN`, and verify in a lower environment first.
- Every executable example must run against a small sample schema — include the `CREATE TABLE` and a
  couple of `INSERT`s so it is self-contained. Anything not executable must be labelled
  **pseudocode**.

---

## PART 9 — TESTING (ch01, ch05, ch06, ch07, ch10)

Add a concise `<h3>Testing</h3>` block to the relevant sections using existing styles — a table of
*what to test / how / what proves it passes*. Do not pad. Cover, placed where each belongs:

PegaUnit and scenario tests; mocked connectors and data sources; validation failures vs business
rejections; authentication expiry and access-control tests; duplicate events; concurrent duplicate
requests; out-of-order events; schema changes; timeout/unknown-outcome; queue retries, broken items
and replay; CSV quoting, encoding, malformed rows, partial files, duplicate file names; SLA and
calendar boundaries (use the Reg CC Juneteenth case and a weekend boundary); production-like load
tests with explicit acceptance criteria.

**Mandatory framing:** head the block with one line stating these are *recommended* tests. Do not
imply he wrote them. If the resume evidences a test practice, it is category B at best — see the
Part 4 register.

---

## PART 10 — CH14 PRACTICE FORMAT

For the **highest-priority questions only** (judge ~20–25, concentrated on rule resolution, SLA and
urgency, idempotency and ordering, data pages, security, SQL, and the regulatory clocks), restructure
to exactly this shape using existing classes:

```html
<div class="qa"><span class="q">Q. …</span>
  <p><strong>Direct answer (20–30s):</strong> …</p>
  <p><strong>If they want more:</strong> …</p>
  <p><strong>Example:</strong> … <span class="tag green">CONFIRMED</span> or <span class="tag">hypothetical</span></p>
  <p><strong>Likely follow-ups:</strong> 1) … 2) …</p>
  <div class="dont"><strong>Common mistake:</strong> …</div>
</div>
```

The example must be tagged honestly per the Part 4 register — a hypothetical example is fine, an
undisclosed one is not. **Do not copy chapter explanations into ch14**; the "if they want more"
paragraph should be a few sentences and a cross-reference.

### Practical exercises
Place each inside the chapter that teaches it, not in ch14 — one `<div class="card blue">` per
exercise with a task and either an answer or assessment criteria:

| Exercise | Chapter |
|---|---|
| Diagnose a rule-resolution mismatch (use worked example B's setup) | ch01 |
| Select data-page scope and refresh for three given scenarios | ch03 |
| Design maker-checker enforcement | ch10 |
| Design a safe asynchronous core write | ch05 |
| Diagnose a queue backlog | ch06 |
| Handle duplicate and out-of-order events | ch06 |
| Write and explain a SQL statement | ch11 |
| Calculate a regulatory deadline (give a date, require the calendar basis) | ch12 |

---

## PART 11 — DEDUPLICATION, REFERENCES, FINAL CONSISTENCY

- **Repetition.** Each concept has one home chapter; elsewhere, one-sentence summary plus a
  cross-reference. The worst offenders are idempotency, rule resolution, and the Kafka story.
- **Lead-level framing.** There are ~40 of these blocks. Keep roughly the best third — where the
  framing genuinely adds a decision or a trade-off — and delete the rest. Never two in one section.
- **Honesty warnings.** Replace the repeated inline warnings with the Part 0.1 tags, which carry the
  same information without interrupting the prose. Keep one consolidated statement in the index and
  one at the head of ch14.
- **References.** Add the Part 0.3 block to every chapter.
- **Final consistency sweep** — verify and report:
  - property names and formulas identical everywhere (`.pxUrgencyAssign` etc.)
  - one rule-resolution explanation, no contradictions
  - personal metrics and their categories identical everywhere
  - cross-references and chapter counts correct; index matches reality
  - FCB hypothetical assumptions consistent (same org shape, same case types, same volumes) and
    labelled hypothetical
  - no stale model answers contradicting corrected chapters
