# Canonical Corrections — authored by lead, apply VERBATIM

These blocks are verified against primary sources (links in Part 5). Do **not** paraphrase,
re-derive, "improve", or re-verify them. Where a block says APPLY VERBATIM, paste the HTML as-is.
Where it says DIRECTIVE, follow the instruction and write prose in the existing chapter voice.

Use only CSS classes that already exist in `assets/sourcebook.css`:
`.note .warning .dont .answer .flow .formula .card(.blue/.green/.amber/.red) .grid .grid3
.tag(.green/.amber/.red) .qa .q .muted .small .pagebreak table code`.
**Do not add, remove or edit any CSS. Do not change navigation, chapter order, filenames, or
`.chapnav` links.**

---

## PART 0 — CONVENTIONS

### 0.1 Evidence tags (item 3)

Every first-person claim, metric, or named-tool experience must carry exactly one tag, inline,
immediately after the claim's heading or as the first element of the claim block:

| Tag HTML | Meaning | When to use |
|---|---|---|
| `<span class="tag green">CONFIRMED</span>` | A. Confirmed personal implementation | Claim appears in `sathvik_resume_fcb.html` **as a described action by him** |
| `<span class="tag amber">CLAIM — NEEDS DETAIL</span>` | B. User-supplied claim requiring supporting detail | Appears in the resume as a number/outcome but the method, scope or measurement is not recorded |
| `<span class="tag">ILLUSTRATIVE</span>` | C. Illustrative calculation | Any number *derived* for teaching (per-record ms, thread counts, cost models) |
| `<span class="tag">PROPOSED DESIGN</span>` | D. Proposed improvement / hypothetical | Something he would build, not something he built |
| `<span class="tag">CONCEPTUAL</span>` | E. Conceptual knowledge | Studied, not operated |

Rules:
- **Never** move a claim from B to A. Only the user can do that.
- Category C numbers must **not** appear inside a first-person sentence. Rewrite
  "I tuned it to 9 ms per record" → "At 200K records in 5 minutes the implied average is ~9 ms per
  record `ILLUSTRATIVE`; the per-record figure was not separately measured."
- Category D must never use past tense. "I built" → "I would build".
- A STAR story that still contains `[YOUR DETAIL]` placeholders must carry a
  `<div class="warning">` noting it is a **scaffold, not a recounted event**.

### 0.2 Release-discipline labels (item 6)

| Tag HTML | Meaning |
|---|---|
| `<span class="tag">8.8 / traditional UI</span>` | Verified for 8.8.x and the traditional (Section/Harness) UI stack |
| `<span class="tag">Infinity / Constellation</span>` | Later Infinity + Constellation only |
| `<span class="tag">pattern</span>` | General architectural pattern, not a product feature |
| `<span class="tag amber">CUSTOM BUILD</span>` | Must be implemented by the team; **not** a Pega built-in |

`CUSTOM BUILD` is mandatory on every mention of: circuit breakers, dead-letter *topics*, replay
APIs, requeue dashboards, reconciliation jobs, idempotency stores, outbox tables.

### 0.3 Per-chapter references block (item 10)

Append to every chapter as the **last section before `.chapnav`**, id `sNN-ref`:

```html
<section id="sNN-ref" class="pagebreak">
  <h2>NN.R Authoritative references</h2>
  <p class="small muted">Each row states what the source actually supports. Where a number is
  release- or date-sensitive, the applicable release or effective date is given. Support notes are
  labelled as such and describe release-specific behaviour, not general design guidance.</p>
  <table>
    <tr><th>Source</th><th>URL</th><th>Release / effective date</th><th>What it supports here</th></tr>
    <!-- rows -->
  </table>
</section>
```

Add the chapter to the TOC (`.toc`) with the same markup pattern already used, and bump the
`.meta` count badges if they state a section count.

---

## PART 1 — RULE RESOLUTION (ch01 §1.6; aligned in ch03, ch14)

### 1.1 APPLY VERBATIM — replace ch01 lines 242–290 (from `<h3>The ordered logic</h3>` through the
closing `</table>` of the availability table) with the following.

```html
    <h3>The five phases</h3>
    <p>Pega documents rule resolution as <strong>candidate gathering</strong>, then
      <strong>filtering</strong>, then <strong>ranking</strong>, then <strong>caching</strong> of the
      surviving ranked list, and finally <strong>runtime qualification</strong> that picks one
      candidate for the context in front of it. Keeping those five apart is the whole trick: most
      wrong answers in interviews come from collapsing ranking and runtime selection into one step.</p>

    <div class="flow">PHASE 1  GATHER CANDIDATES
        Start in the Applies-To class and walk up the inheritance structure, collecting every
        instance of (rule type, rule name) found on the way.

        Traversal is interleaved, not "pattern first then directed":
          search the class itself
          -> walk its pattern-inheritance chain (truncate name segments from the right at '-')
          -> then its directed parent, and run a *fresh pattern search from that class*
          -> repeat until @baseclass. Not found at @baseclass = error.

        Controlled by two checkboxes on the class rule:
          "Use class-based inheritance to arrive at the correct Rule to execute?"
              cleared -> NO superclass search at all; the rule must exist in the current class.
          "Find by name first (Pattern)?"  (Rule-Obj-Class.pyPatternInheritance)
              selected -> pattern chain is searched before the directed parent
              cleared  -> pattern inheritance is bypassed; directed parent chain only
              Directed inheritance ALWAYS applies for rule types with an Applies-To key part.
              Classes that belong to a class group have this selected automatically.
              It cannot be changed after the class form is saved.

PHASE 2  FILTER (remove candidates that cannot apply at all)
        - ruleset not on the requestor's ruleset list
        - ruleset version above the version allowed by the list
          (list entry FCBDeposits:01-02 permits 01-02-xx, not 01-03-xx)
        - availability = Not Available

PHASE 3  RANK the survivors, in this exact order
        1. Class            closest to the Applies-To class ranks highest
        2. Ruleset          order of the operator's ruleset list
        3. Circumstance     property or template
        4. Circumstance Date
        5. Date/Time Range
        6. Version          highest version within the same ruleset

        Then two clean-up steps, in order:
        3a. WITHDRAWN REMOVAL. For each candidate marked Withdrawn, remove every candidate in a
            LOWER version of the SAME ruleset that matches its Applies-To class, its purpose
            (rule type) and its qualifiers. Candidates in other classes or other rulesets survive.
            A HIGHER version in the same ruleset marked Available also survives.
        3b. DEFAULT CANDIDATE. The highest-ranked candidate that has NO qualifiers becomes the
            default - the fallback that always matches. Every candidate ranked BELOW it is
            discarded, because it could never be reached.

PHASE 4  CACHE
        The remaining ranked LIST of candidates is stored in the rules cache - not a single
        universal winner. Invalidated by rule save, check-in, or a cache refresh on the node.

PHASE 5  QUALIFY AT RUNTIME AND SELECT
        Walk the cached ranked list top-down for THIS case, THIS user, THIS moment. Take the
        highest-ranked candidate whose qualifiers are satisfied (circumstance values match,
        circumstance date and date/time range contain "now"). If none qualify, the default
        candidate runs.
        If the selected candidate is Blocked, the run HALTS and an error is written to the log.
        The winner is then assembled to Java if it is not already assembled.</div>

    <div class="note"><strong>Why the cache does not hold one winner.</strong> Phase 4 caches the
      ranked candidate list; Phase 5 chooses from it per context. That is exactly how one cached
      result can serve a California case and a Texas case and give each a different rule. If the
      cache held a single resolved winner, circumstancing could not work at all. Say this in an
      interview and you will sound like you have debugged it, because the usual wrong answer is
      "the winner is cached".</div>

    <div class="note"><strong>The class-versus-ruleset question, settled.</strong> Class is the
      <em>first</em> sort key and ruleset is the second, so a more specific class outranks a
      higher-priority ruleset. Ruleset order only breaks ties <em>within the same class</em>. The one
      real exception is documented: rule types whose class does not have <em>"Use class-based
      inheritance to arrive at the correct Rule to execute"</em> selected are <strong>not ranked by
      class at all</strong> — for those, ruleset order decides. That is the whole answer; it is not
      genuinely ambiguous, and you do not need to hedge it.</div>

    <div class="note"><strong>Version is ranked last, on purpose.</strong> Because Version sits below
      Circumstance, a newer base rule does <strong>not</strong> automatically supersede an older
      circumstanced rule. Pega states the intent directly: ranking by version last "ensures that
      circumstanced Rules are not automatically overridden if the base Rule is updated in a more
      recent Ruleset version." See worked example B.</div>

    <h3>Availability states</h3>
    <table>
      <tr><th>State</th><th>Used in resolution?</th><th>Effect</th><th>Dev Studio</th><th>Typical use</th></tr>
      <tr><td>Available</td><td>Yes</td><td>Normal participation. Default on creation.</td><td>View, copy, edit, run</td><td>Default</td></tr>
      <tr><td>Final</td><td>Yes</td><td>Cannot be edited, and cannot be copied into another ruleset under the same name. <strong>Cannot be overridden except by a higher version in the same ruleset.</strong></td><td>View and run only</td><td>Pega marks its own rules Final to signal they may change in a future release</td></tr>
      <tr><td>Not Available</td><td>No</td><td>Filtered out. The next-highest version is considered instead.</td><td>View, copy, edit; does not run</td><td>Save a half-built rule without validation during initial development</td></tr>
      <tr><td>Blocked</td><td><strong>Yes — it still ranks and can be selected</strong></td><td>If it is selected, the run <strong>halts</strong> and an error goes to the log. Lower candidates are <strong>not</strong> used as a fallback. A blocked <em>circumstanced</em> rule is not considered, but the other instances in the current version ruleset still are.</td><td>View, copy, edit; does not run</td><td>Stop a rule being used while a replacement is written</td></tr>
      <tr><td>Withdrawn</td><td>No — and it removes others</td><td>Hides itself <strong>and</strong> every candidate at an equal or lower version of the same ruleset with the same Applies-To class, purpose and qualifiers. The engine then looks to the parent class or the next ruleset in the stack. A <strong>higher</strong> version in the same ruleset survives. A withdrawn <em>circumstanced</em> rule is not considered, but the other instances in the current version ruleset still are.</td><td>View, copy, edit; does not run</td><td>Retire a rule across a ruleset's history without deleting it</td></tr>
    </table>

    <div class="dont"><strong>Four things not to say.</strong>
    <ul>
      <li>"Withdrawn is basically Not Available." It is not. Not Available removes <em>one</em>
        candidate; Withdrawn removes a whole band of lower versions in that ruleset.</li>
      <li>"Blocked makes resolution fall through to the next rule." It does not — it <em>fails</em>.</li>
      <li>"Final stops anyone overriding the rule anywhere." A higher version <em>in the same
        ruleset</em> supersedes it.</li>
      <li>"The resolved rule is cached." The ranked <em>candidate list</em> is cached.</li>
    </ul></div>

    <h3>Worked example A — more specific class vs higher-priority ruleset</h3>
    <p>Ruleset list, highest priority first: <code>FCBOverrides:01-01</code>, then
      <code>FCBDeposits:01-01</code>. Two candidates for <code>CalculateFee</code>:</p>
    <table>
      <tr><th>#</th><th>Applies-To class</th><th>Ruleset</th><th>Intuition says</th></tr>
      <tr><td>1</td><td><code>FCB-Dep-Work-AccountClosure</code> (more specific)</td><td><code>FCBDeposits:01-01-01</code> (lower priority)</td><td>—</td></tr>
      <tr><td>2</td><td><code>FCB-Dep-Work</code> (less specific)</td><td><code>FCBOverrides:01-01-01</code> (higher priority)</td><td>"my override ruleset wins"</td></tr>
    </table>
    <p><strong>Candidate 1 wins.</strong> Class is sort key 1, ruleset is sort key 2, so the more
      specific class outranks the higher-priority ruleset. Ruleset order would only have decided
      this if both candidates sat on the <em>same</em> class.</p>
    <p><strong>The trap:</strong> teams create an "overrides" ruleset expecting it to beat
      everything, then cannot explain why a class-level rule still wins. If you genuinely need the
      override to win, put it on the <em>same class</em> (or a more specific one), not merely in a
      higher ruleset.</p>
    <p><strong>The exception:</strong> if the class does not have <em>"Use class-based inheritance to
      arrive at the correct Rule to execute"</em> selected, class is not a ranking criterion and
      candidate 2 wins instead.</p>

    <h3>Worked example B — older circumstanced rule vs newer base rule</h3>
    <p><code>CalculateHoldPeriod</code> on <code>FCB-Dep-Work-LegalOrder</code>, same class, same
      ruleset:</p>
    <table>
      <tr><th>#</th><th>Rule</th><th>Ruleset version</th><th>Qualifier</th></tr>
      <tr><td>1</td><td>Circumstanced variant</td><td><code>FCBDeposits:01-02-04</code> (older)</td><td><code>.State = "CA"</code></td></tr>
      <tr><td>2</td><td>Base rule, just patched</td><td><code>FCBDeposits:01-03-02</code> (newer)</td><td>none</td></tr>
    </table>
    <p>For a case with <code>.State = "CA"</code>, <strong>candidate 1 wins</strong> — the older
      one. Circumstance is sort key 3; Version is sort key 6. Rule 2 becomes the default candidate
      and serves every other state.</p>
    <div class="warning"><strong>This is the single most expensive rule-resolution defect in
      production.</strong> You patch a bug in the base rule, ship 01-03-02, verify it in a state with
      no circumstanced variant, and close the ticket. California silently keeps running the old
      logic. The fix must always be: patch the base rule <em>and</em> every circumstanced variant, or
      withdraw the variants deliberately. Before shipping a base-rule fix, list the circumstanced
      variants — the rule form's circumstance list tells you in seconds and it is the cheapest
      possible check.</div>

    <h3>Worked example C — Not Available vs Withdrawn vs Blocked</h3>
    <p>One section rule, <code>CreateRequest</code>, one class, one ruleset
      (<code>Purchasing</code>), four versions present: 02-01-15, 02-01-10, 02-01-05, 02-01-01.
      In each row only the availability of <strong>02-01-10</strong> changes.</p>
    <table>
      <tr><th>02-01-10 is…</th><th>What is removed</th><th>What actually runs</th></tr>
      <tr><td>Available</td><td>nothing</td><td>02-01-15 (highest version)</td></tr>
      <tr><td><strong>Not Available</strong></td><td>only 02-01-10</td><td>02-01-15; and if 02-01-15 did not exist, 02-01-05 — the next-highest version</td></tr>
      <tr><td><strong>Withdrawn</strong></td><td>02-01-10, 02-01-05 <em>and</em> 02-01-01 — the whole band at or below it in this ruleset</td><td>02-01-15, because it is <em>higher</em> than the withdrawn version. If 02-01-15 did not exist, the engine looks to the parent class or the next ruleset in the stack</td></tr>
      <tr><td><strong>Blocked</strong></td><td>nothing — it still ranks</td><td>02-01-15. But if 02-01-15 did not exist, 02-01-10 is <em>selected</em>, the run halts, an error is logged, and the section does not render. 02-01-05 is never reached</td></tr>
    </table>
    <p class="small muted">Memory hook: Not Available skips <em>one</em>. Withdrawn deletes
      <em>downwards</em>. Blocked <em>detonates</em>. Final locks the <em>ruleset</em>, not the rule.</p>
```

### 1.2 DIRECTIVE — ch01 §1.5 and the §1.4 table row at line ~175

Split the two concepts that are currently conflated. Add to §1.5:

- **Class group** is a *persistence* concept. It determines which database table the case instances
  are written to and the case ID prefix. Work classes in a group share one table.
- **Directed inheritance** is a *rule-resolution* concept. It names an explicit parent so a class can
  inherit rules from outside its own name path.
- They are independent. A class can belong to a class group *and* have a directed parent somewhere
  unrelated. Belonging to a class group does, however, force "Find by name first (Pattern)?" on.
- Note the documented edge case: if the directed parent is set to the longest prefix of the class
  name ending in a hyphen, selecting or clearing "Find by name first (Pattern)?" makes **no
  difference** to resolution behaviour.

Replace any wording implying the traversal is "pattern chain, then directed parents" with the
interleaved traversal from Phase 1 above.

### 1.3 DIRECTIVE — ch01 cover badge and ch14 Q2

- ch01 line ~22: `<div><strong>8-step</strong><span>Rule resolution model</span></div>`
  → `<div><strong>5-phase</strong><span>Rule resolution model</span></div>`
- ch01 line ~31 and §1.6 intro: delete "The practical eight-step model below matches that
  documentation closely enough… where I simplify, I say so." It is no longer a simplification.
- ch01 Q2 (line ~632) and **ch14's equivalent rule-resolution answers**: rewrite so the stated order
  is Class → Ruleset → Circumstance → Circumstance Date → Date/Time Range → Version, and so that
  circumstancing is **not** described as happening after version selection. Suggested replacement
  for the 20–30 second answer:

  > "The engine gathers every candidate with that name from the Applies-To class up the inheritance
  > structure, filters out anything whose ruleset is not on my list, whose version is above what the
  > list allows, or that is Not Available. It ranks what is left by class, then ruleset, then
  > circumstance, then circumstance date, then date range, then version — version last, which is why
  > a newer base rule does not override an older circumstanced one. Withdrawn rules take out the
  > lower versions in their own ruleset, the highest unqualified candidate becomes the default, and
  > the ranked list is cached. At runtime the engine takes the highest-ranked candidate whose
  > circumstances actually match this case, falling back to the default. If that candidate is
  > Blocked, the run fails rather than falling through."

### 1.4 DIRECTIVE — ch03

ch03 discusses circumstancing in depth. Make it consistent: remove any statement that a newer
version supersedes a circumstanced rule, and cross-reference "Chapter 01 §1.6, worked example B"
rather than repeating the ranking table (item 10).

---

## PART 2 — SLA URGENCY AND BACKGROUND PROCESSING (ch02 §2.8; ch14)

### 2.1 APPLY VERBATIM — replace ch02 lines 349–360 (`<h3>Urgency math</h3>` through the
"Do not over-claim extra terms." paragraph) with:

```html
    <h3>Urgency math</h3>
    <p>Urgency is an integer from <strong>0 to 100</strong> that ranks work. It drives worklist order
      and the Get Next Work selection algorithm. Values above 100 are not stored — the system ignores
      adjustments that would push it past 100. There are two urgencies, and conflating them is the
      classic interview slip: <strong>case urgency</strong> is the priority of the case,
      <strong>assignment urgency</strong> is the priority of one piece of work on it.</p>

    <h4>Assignment urgency — the property that actually ranks work</h4>
    <div class="formula">.pxUrgencyAssign  =  .pxUrgencyWork            (case urgency, copied in at assignment creation)
                   +  .pxUrgencyAssignSLA      (assignment SLA: initial urgency + interval increments)
                   +  .pyUrgencyAssignAdjust   (manual adjustment, via the ChangeAssignmentSLA local action)
                   bounded to 0..100</div>
    <table>
      <tr><th>Property</th><th>Prefix</th><th>Meaning</th></tr>
      <tr><td><code>.pxUrgencyAssign</code></td><td>px — calculated</td><td>The assignment urgency. This is the number that ranks work.</td></tr>
      <tr><td><code>.pxUrgencyWork</code></td><td>px — calculated</td><td>Case urgency, contributed into the assignment when the assignment is created.</td></tr>
      <tr><td><code>.pxUrgencyAssignSLA</code></td><td>px — calculated</td><td>The assignment SLA's contribution: its initial urgency plus the increments for goal, deadline and passed-deadline as each interval elapses.</td></tr>
      <tr><td><code>.pyUrgencyAssignAdjust</code></td><td>py — you set it</td><td>Manual adjustment to this assignment. The <code>ChangeAssignmentSLA</code> local action writes it.</td></tr>
    </table>

    <h4>Case urgency — calculated separately</h4>
    <div class="formula">.pxUrgencyWork  =  .pxUrgencyWorkClass      (case type Initial Urgency; default 10)
                +  .pyUrgencyWorkAdjust     (manual, via the UrgencyUpdate local action)
                +  .pxUrgencyWorkSLA        (case-level SLA, if any)
                +  .pxUrgencyPartyTotal     (sum of work-party urgency; rare)
                +  .pxUrgencyWorkStageSLA   (current stage's SLA, if any)
                +  .pxUrgencyWorkStepSLA    (sum of process SLAs in the current stage)</div>
    <p>The last four are documented but rarely used in practice. The two you will actually configure
      are the case type's <em>Initial Urgency</em> (Settings &gt; General, default 10) and
      <code>.pyUrgencyWorkAdjust</code>.</p>

    <div class="warning"><strong>Case urgency does not propagate to assignments that already
      exist.</strong> Pega's documentation is explicit: <code>.pxUrgencyAssign</code> reflects a
      manual adjustment to case urgency only if the adjustment is made <em>before</em> the assignment
      is created — not after. <code>.pxUrgencyWork</code> is copied into the assignment's total at
      creation time; raising case urgency later moves the case, not the open assignment sitting in
      somebody's worklist. If you need an existing assignment to jump the queue, adjust
      <code>.pyUrgencyAssignAdjust</code> on the assignment. This is a superb interview answer
      because it is the thing that bites teams in production: "we escalated the case and the work
      still did not come up next in Get Next Work."</p></div>
    <p class="small muted">Runtime: the system recalculates urgency when the value of a standard
      urgency property changes, or when a user saves the case.</p>

    <h4>Worked example</h4>
    <p>A legal-order case. Case type Initial Urgency is set to 30 (above the default 10 because these
      carry statutory deadlines). A supervisor raises case urgency by 10 <em>before</em> the review
      assignment is created. The review assignment's SLA has initial urgency 10, +10 at goal, +30 at
      deadline. No manual assignment adjustment yet.</p>
    <table>
      <tr><th>Moment</th><th><code>.pxUrgencyWork</code></th><th><code>.pxUrgencyAssignSLA</code></th><th><code>.pyUrgencyAssignAdjust</code></th><th><code>.pxUrgencyAssign</code></th></tr>
      <tr><td>Assignment created</td><td>30 + 10 = 40</td><td>10</td><td>0</td><td><strong>50</strong></td></tr>
      <tr><td>Goal elapses</td><td>40</td><td>10 + 10 = 20</td><td>0</td><td><strong>60</strong></td></tr>
      <tr><td>Deadline elapses</td><td>40</td><td>20 + 30 = 50</td><td>0</td><td><strong>90</strong></td></tr>
      <tr><td>CSR escalates the assignment by 20</td><td>40</td><td>50</td><td>20</td><td><strong>100</strong> (capped — the raw sum is 110)</td></tr>
      <tr><td>Supervisor now raises <em>case</em> urgency by 10</td><td>50</td><td>50</td><td>20</td><td><strong>100</strong> — unchanged; the existing assignment does not pick up the later case-urgency change</td></tr>
    </table>
    <p>The last two rows are the ones worth remembering: the cap is real, and the late case-urgency
      bump does nothing for work already assigned.</p>
```

### 2.2 DIRECTIVE — ch02 SLA engine section (lines ~374–402), item 2 second half

Rewrite so nothing is stated as universal. Specifically:

1. Change the queue-processor table into a two-column "What to say / How to confirm it on the
   deployed version" table. Every row's second column must name the **Admin Studio or DSS screen**
   that proves it, because the names and defaults are release-sensitive.
2. Delete the unqualified row `Default — pyProcessSLA is disabled by default`. Replace with: the
   default has varied by release; confirm via the `UseSLAQueueProcessor` DSS value and the Queue
   Processors landing page on the deployed version.
3. **Delete the claim** "On switching, `pyProcessSLA` takes over items already sitting in
   `System-Queue-ServiceLevel`." I could not verify it. Replace with a `<div class="warning">`:
   migration drain behaviour for items already queued by the agent is **not something to assert** —
   before switching, confirm on a lower environment whether existing queued items are picked up by
   the queue processor or must be drained by the agent first, and keep the agent enabled until the
   backlog is observed to be zero.
4. Replace "disable the `ServiceLevelEvents` agent when you enable the queue processor" with a
   sequenced instruction that does not risk stranding queued items: verify drain behaviour → enable
   the queue processor → watch both the agent's queue and the processor's queue → disable the agent
   only once the agent-side backlog is confirmed drained. Keep the double-processing warning.
5. Add one sentence separating the mechanisms: the legacy agent and the queue processor are
   different execution models (agent schedule vs queue-processor dequeue), and **do not assume every
   SLA-like timer in the platform uses `System-Queue-ServiceLevel`** — case-level, stage-level and
   step-level SLAs, and timer/wait shapes, are configured separately and may be serviced by
   different background mechanisms. Verify per release rather than generalising from assignment SLAs.
6. Keep the existing release-caveat note but add the support-note label per Part 0.2.

### 2.3 DIRECTIVE — ch14

Fix the Q6 headline and model answer (line ~186–187) and any other urgency answer to match 2.1:
name `.pxUrgencyAssign` as the ranking property, give the three-term sum, state the 0–100 bound, and
include the "case urgency does not propagate to existing assignments" point as the differentiator.
Remove "the case urgency starting from the class default plus the assignment urgency" phrasing.

---

## PART 3 — REGULATORY CLOCKS (ch12 primary; ch02, ch11, ch13, ch14 reference it)

### 3.1 APPLY VERBATIM — insert into ch12 as a new subsection immediately before the existing
regulatory-timeline content, and make ch02 §2.8's calendar bullets link to it instead of repeating.

```html
    <h3>Calendars are not interchangeable — and the Fed holiday list is the wrong default</h3>
    <p>The pack previously assumed one Federal Reserve holiday calendar could drive every regulatory
      deadline. That is wrong, and it is wrong in a way an examiner would catch. There are at least
      five different clocks, and two of them are defined by statute in terms that do not match the
      Fed's own holiday list.</p>
    <table>
      <tr><th>Clock</th><th>Defined as</th><th>Who decides the calendar</th></tr>
      <tr><td><strong>Reg E business day</strong><br><span class="small muted">12 CFR 1005.2(d)</span></td><td>"Any day on which the offices of the consumer's financial institution are open to the public for carrying on <em>substantially all</em> business functions."</td><td><strong>The institution itself.</strong> Not a public holiday list.</td></tr>
      <tr><td><strong>Reg CC business day</strong><br><span class="small muted">12 CFR 229.2(g)</span></td><td>A calendar day other than Saturday, Sunday, or an <em>enumerated</em> list of ten holidays written into the regulation.</td><td><strong>The regulation.</strong> A fixed statutory list.</td></tr>
      <tr><td><strong>Reg CC banking day</strong><br><span class="small muted">12 CFR 229.2(f)</span></td><td>"That part of any <em>business day</em> on which an office of a bank is open to the public for carrying on substantially all of its banking functions."</td><td>Per office, and nested inside a Reg CC business day.</td></tr>
      <tr><td><strong>ACH / network deadlines</strong></td><td>Processing windows and file cut-off times set by Nacha rules and the operator's schedule.</td><td>The network and the operator — cut-off <em>times</em>, not just days.</td></tr>
      <tr><td><strong>State legal-order deadlines</strong></td><td>Varies per state statute; often calendar days, sometimes court days.</td><td>Each state.</td></tr>
      <tr><td><strong>Internal operational SLA</strong></td><td>Whatever the bank commits to.</td><td>The bank. <span class="tag amber">policy, not law</span></td></tr>
    </table>

    <div class="warning"><strong>Three concrete traps in those definitions.</strong>
    <ul>
      <li><strong>Reg E's business day is per-institution and includes back-office work.</strong> The
        official interpretation is explicit: if a branch opens on Saturday for teller transactions
        but does not perform internal functions such as investigating account errors, Saturday is
        <em>not</em> a Reg E business day for that institution. A bank may also elect whether an
        abbreviated day counts. So the Reg E calendar is a <em>configuration item per institution</em>,
        not a holiday feed. A Reg E business day is also the full 24-hour period ending at midnight.</li>
      <li><strong>Reg CC's statutory list does not include Juneteenth.</strong> §229.2(g) enumerates
        January 1, the third Monday in January, the third Monday in February, the last Monday in May,
        July 4, the first Monday in September, the second Monday in October, November 11, the fourth
        Thursday in November, and December 25. Federal Reserve Banks have observed Juneteenth as a
        holiday since 2021. Drive Reg CC off "the Fed holiday calendar" and your availability
        schedule is wrong on 19 June.</li>
      <li><strong>Reg CC's Sunday rule is one-directional.</strong> If January 1, July 4, November 11
        or December 25 falls on a <em>Sunday</em>, the following Monday is also not a business day.
        There is no matching rule for a Saturday — so when July 4 falls on a Saturday, the preceding
        Friday is still a Reg CC business day even though federal offices observe the holiday then.</li>
    </ul></div>

    <div class="note"><strong>Design consequence.</strong> A single <code>IsBusinessDay</code> helper
      is a defect waiting to happen. Model the calendar as an <em>input</em> to the deadline, not a
      global: <code>CalculateDueDate(trigger, ruleId, calendarId, timeZone, cutOff)</code>. In Pega
      terms that means more than one Calendar rule — at minimum a Reg CC statutory calendar, a
      per-institution Reg E calendar, and separate operational calendars — chosen by the rule being
      applied rather than by the case type. <span class="tag">pattern</span></div>

    <h4>Represent every deadline as a record, not a duration</h4>
    <p>Store these eight fields for each regulatory clock in the application, and make them
      reportable. A duration alone ("10 days") cannot be audited.</p>
    <table>
      <tr><th>Field</th><th>Example</th></tr>
      <tr><td>Trigger event</td><td>Date the institution receives the notice of error</td></tr>
      <tr><td>Applicable rule</td><td>12 CFR 1005.11(c)(1)</td></tr>
      <tr><td>Calendar definition</td><td>Reg E business day, this institution</td></tr>
      <tr><td>Time zone</td><td>America/New_York</td></tr>
      <tr><td>Cut-off</td><td>Notice received after the cut-off counts as the next business day</td></tr>
      <tr><td>Exceptions</td><td>New account (&lt;30 days since first deposit); foreign-initiated; POS debit</td></tr>
      <tr><td>Due date</td><td>Computed, stored, and never recomputed silently</td></tr>
      <tr><td>Rule version / effective date</td><td>Which version of the policy produced this date</td></tr>
    </table>
    <div class="note">Store the computed due date <em>and</em> the inputs that produced it. When the
      policy changes, in-flight cases must keep the deadline they were given; only new cases get the
      new rule. Recomputing historical due dates from today's configuration is how banks fail
      look-backs.</div>

    <h4>Worked deadline example 1 — Reg E error resolution, provisional credit</h4>
    <p><span class="tag">worked example</span> <strong>Assumptions, stated explicitly:</strong> the
      institution performs substantially all business functions Monday–Friday only, so Saturdays and
      Sundays are not Reg E business days for it; it observes 1 January; it has no same-day cut-off
      rule; the account is more than 30 days old; the transfer was domestic.</p>
    <p>A consumer gives oral notice of an unauthorised EFT on <strong>Tuesday 2 December 2025</strong>.</p>
    <table>
      <tr><th>Obligation</th><th>Clock</th><th>Due</th><th>Source</th></tr>
      <tr><td>Determine whether an error occurred</td><td>10 <strong>business</strong> days from receipt</td><td>Tue 16 Dec 2025</td><td>1005.11(c)(1)</td></tr>
      <tr><td>If not finished, provisionally credit the account</td><td>10 <strong>business</strong> days from receipt</td><td>Tue 16 Dec 2025</td><td>1005.11(c)(2)(i)</td></tr>
      <tr><td>Tell the consumer the amount and date of that credit</td><td>2 <strong>business</strong> days after crediting</td><td>Thu 18 Dec 2025</td><td>1005.11(c)(2)(ii)</td></tr>
      <tr><td>Complete the investigation</td><td>45 <strong>calendar</strong> days from receipt</td><td>Fri 16 Jan 2026</td><td>1005.11(c)(2)</td></tr>
      <tr><td>Report the result</td><td>3 <strong>business</strong> days after completing</td><td>depends on completion date</td><td>1005.11(c)(2)(iv)</td></tr>
      <tr><td>Correct the error, if there was one</td><td>1 <strong>business</strong> day after determining</td><td>depends</td><td>1005.11(c)(2)(iii)</td></tr>
    </table>
    <div class="warning"><strong>The detail that separates a domain-aware engineer from a guesser:
      the 10, 3, 2 and 1 are <em>business</em> days but the 45 and 90 are <em>calendar</em>
      days.</strong> The regulation says "45 days", not "45 business days". Mixing them is the single
      most common implementation error in dispute workflows, and it fails in the direction that
      harms the consumer. Two documented extensions also change the arithmetic: <strong>20</strong>
      business days replaces 10 if the notice involves a transfer within 30 days of the first deposit
      to a new account, and <strong>90</strong> calendar days replaces 45 for transfers not initiated
      within a state, among other listed cases.</div>

    <h4>Worked deadline example 2 — the same date on three different calendars</h4>
    <p><span class="tag">worked example</span> Take <strong>Thursday 19 June 2025</strong>
      (Juneteenth), and assume the bank's branches are closed that day but its back office is not.</p>
    <table>
      <tr><th>Clock</th><th>Is 19 Jun 2025 counted?</th><th>Why</th></tr>
      <tr><td>Reg CC business day</td><td><strong>Yes</strong></td><td>Juneteenth is not in the §229.2(g) list, so it is an ordinary business day for Reg CC availability</td></tr>
      <tr><td>Reg CC banking day</td><td><strong>No</strong>, for a closed office</td><td>A banking day is the part of a business day when that office is open for substantially all banking functions</td></tr>
      <tr><td>Reg E business day</td><td><strong>Depends on this institution</strong></td><td>If the back office still performs substantially all functions including error investigation, it counts; if not, it does not</td></tr>
      <tr><td>Fed holiday calendar</td><td><strong>No</strong></td><td>Federal Reserve Banks observe Juneteenth — which is exactly why it is the wrong source for the two rows above</td></tr>
    </table>
    <p>One date, four different answers. That is the whole argument for modelling the calendar as an
      input rather than a constant.</p>
```

### 3.2 DIRECTIVE — audit the remaining regulatory statements in ch12 (and ch02/ch11/ch13/ch14)

For **every** numeric regulatory statement — Reg E, Reg CC availability schedules, ACH return
windows and deadlines, legal process / levy holds, sanctions screening, CIP/CDD, dormancy and
escheatment — do one of exactly three things. "Verify current" on its own is **banned**.

1. **Source it.** Add the citation, the URL, and the effective date, and state the calendar basis
   (business / banking / calendar days).
2. **Demote it to an assumption.** If it is a bank policy rather than a legal requirement, move it
   under a clearly headed "Assumed FCB policy" block with
   `<span class="tag amber">assumed FCB policy — not a legal requirement</span>`.
3. **Delete the number** and keep the concept, if neither of the above can be done honestly.

Dormancy and escheatment are **state law** and vary by state and property type — do not state a
single national dwell period. Already-verified items from the previous pass (IRC §6332(c) 21-day
levy period; Nacha unauthorised-return threshold vs inquiry levels) keep their existing verified
citations; do not re-verify or reword them.

Keep legal requirements, illustrative bank policy, and assumed FCB policy in **visually distinct
blocks** throughout — never in the same table without a column distinguishing them.

---

## PART 4 — PERSONAL CLAIM REGISTER (item 3)

Source of truth: `../sathvik_resume_fcb.html`. **Nothing else counts as evidence.** Apply exactly
this classification. Do not re-derive it, do not upgrade anything, do not invent supporting detail.

| # | Claim as it appears in the pack | Resume evidence | Category | Required treatment |
|---|---|---|---|---|
| 1 | 200,000 records in 5 minutes | Yes — "Tuned Queue Processor & Job Scheduler-based bulk processing to handle 200,000 records in 5 minutes" | **B** | Keep, tag `CLAIM — NEEDS DETAIL`, attach the measurement-record table (4.2) with fields left as `[CONFIRM]` |
| 2 | ~6 threads, ~9 ms per record | **No** — appears nowhere in the resume | **C** | Remove from all first-person sentences. Re-present as an arithmetic illustration derived from claim 1 |
| 3 | Bulk staging + one MERGE per chunk | **CORRECTED 2026-10-12.** The resume *does* describe this at line 228: "Engineered metadata-driven integration: runtime-resolved Dataset mappings, dynamic JSON-to-SQL mapping, and **Connect-SQL MERGE** to populate target tables". My earlier register entry was wrong. | **B** for the MERGE itself; **B-partial** for the specifics | `Connect-SQL MERGE`, runtime-resolved Dataset mappings and dynamic JSON-to-SQL mapping are described actions → tag `CLAIM — NEEDS DETAIL`, **not** `PROPOSED DESIGN`. The *staging table* and *one-MERGE-per-chunk chunking* are still **not** in the resume — keep those two specifics tagged `CLAIM — NEEDS DETAIL` with a `[CONFIRM]` on the chunking strategy, or drop the specifics and keep the MERGE |
| 4 | 50+ Kafka topics | Yes — "50+ topics across seven markets" | **B** | Tag `CLAIM — NEEDS DETAIL` |
| 5 | Seven markets | Yes — "seven APAC markets" | **B** | Tag `CLAIM — NEEDS DETAIL` |
| 6 | $200K annual infrastructure savings | Yes — but worded "**contributing to** $200K **estimated** annual infrastructure savings" | **B** | Must retain both hedges: contributory, not sole; estimated, not measured. Never render as "I saved $200K" |
| 7 | $250K+ total savings | Yes — impact card: $200K infra + $50K monitoring | **B** | Same treatment as 6 |
| 8 | ~24 hours → real-time | Yes | **B** | Tag `CLAIM — NEEDS DETAIL` |
| 9 | 100% reduction in manual write-back | Yes — "reducing manual writeback by 100%" | **B** | Tag `CLAIM — NEEDS DETAIL`. Flag in the confirmation list that 100% is an absolute and invites challenge |
| 10 | 10+ REST/SOAP/Connect-SQL integrations | Yes | **B** | Tag `CLAIM — NEEDS DETAIL` |
| 11 | 20+ production releases, 95+ guardrails | Yes | **B** | Tag `CLAIM — NEEDS DETAIL` |
| 12 | Kafka replay / requeue dashboard | Yes — "Built a Pega Data Pages dashboard… one-click Service-REST requeue… hours to seconds" | **B** | Tag `CLAIM — NEEDS DETAIL`. Also tag the dashboard itself `CUSTOM BUILD` so nobody reads it as a Pega feature |
| 13 | **Deployment Manager** | Listed in the skills line only. **No** described usage | **E** | Downgrade to `CONCEPTUAL` unless the user confirms. Remove any first-person pipeline story |
| 14 | **PostgreSQL production experience** | Listed in skills and Stack only. **No** experience bullet | **E** | Downgrade to `CONCEPTUAL`. ch11 must teach PostgreSQL fully but must not imply he ran it in production |
| 15 | **Splunk** | Skills line says "Splunk (log analysis)", but the project bullet says log-analysis patterns "**applicable to** Splunk-based production monitoring" — the resume itself declines to claim it | **E** | `CONCEPTUAL`. This is the clearest case in the register: do not let the pack claim more than the resume does |
| 16 | **Okta / SAML authentication work** | Stack line only. No described usage | **E** | `CONCEPTUAL` |
| 17 | **Mentoring / coaching achievements** | **Absent from the resume entirely** | **unsupported** | Remove the achievement framing. Either delete or convert to `PROPOSED DESIGN` ("how I would onboard a junior"). Do **not** invent a mentee, a count, or an outcome |
| 18 | AI-assisted mapping utility, 50+ tables in 10 minutes | Yes | **B** | Tag `CLAIM — NEEDS DETAIL` |

### 4.1 Rule for STAR stories

Any STAR story that asserts a situation, action, result or ownership not traceable to the table
above is **unsupported**. Do not delete the teaching value — convert it:

- Keep the structure and the technical reasoning.
- Change "I did X and achieved Y" to a labelled scaffold with
  `<span class="tag">PROPOSED DESIGN</span>` or a `<div class="warning">` stating it is a template to
  be completed with a real example, **not** a recounted event.
- A story containing any `[YOUR DETAIL]` placeholder must carry that warning even if the rest reads
  complete. Count them and list them in the final report.

### 4.2 Measurement record — attach to each category-B throughput claim

Different projects must never share a measurement. Use this table, with `[CONFIRM]` wherever the
resume does not supply the value:

```html
<table>
  <tr><th>Field</th><th>Value</th></tr>
  <tr><td>Volume</td><td>200,000 records</td></tr>
  <tr><td>Environment</td><td>[CONFIRM — prod / perf / UAT, node count, node size]</td></tr>
  <tr><td>Processing boundary</td><td>[CONFIRM — enqueue→commit? file-read→DB-commit? end-to-end incl. downstream?]</td></tr>
  <tr><td>Elapsed time</td><td>5 minutes</td></tr>
  <tr><td>Concurrency</td><td>[CONFIRM — QP thread count and node count at the time]</td></tr>
  <tr><td>Error rate</td><td>[CONFIRM — failures and retries during the run]</td></tr>
  <tr><td>Measurement method</td><td>[CONFIRM — PAL, QP landing page, DB row counts, log timestamps?]</td></tr>
</table>
```

Add a one-line note: until the boundary is confirmed, state the claim in interview as "200,000
records in about five minutes on that pipeline" and let the interviewer ask for the boundary —
rather than volunteering a per-record figure that was never measured.

---

## PART 5 — VERIFIED SOURCE REGISTER

Cite these, with these exact descriptions of what they support. All fetched 2026-10-12.

| Source | URL | Supports |
|---|---|---|
| Pega Academy — Remaining Rule candidates and ranking (v6) | https://academy.pega.com/topic/remaining-rule-candidates-and-ranking/v6 | The six-key sort order; class-based-inheritance caution; Withdrawn removing lower versions matching class + purpose + qualifiers; default rule candidate; ranked candidates going to the rules cache; version-last rationale |
| Pega Academy — Rule resolution process and Rule availability (v6) | https://academy.pega.com/topic/rule-resolution-process-and-rule-availability/v6 | All five availability states; Final overridable only by a higher version in the same ruleset; Blocked halting the run and logging an error; Withdrawn affecting current and previous versions; the circumstanced-rule notes for Blocked and Withdrawn |
| Pega Academy — Assignment Urgency (v4) | https://academy.pega.com/topic/assignment-urgency/v4/in/74506/74516 | 0–100 bound and the >100 rule; the three-term `.pxUrgencyAssign` sum; the six-term `.pxUrgencyWork` sum; Initial Urgency default 10; `UrgencyUpdate` and `ChangeAssignmentSLA` local actions; the before/after assignment-creation caution; recalculation triggers |
| Pega Academy — Rule reuse through inheritance | https://academy.pega.com/topic/rule-reuse-through-inheritance/v1/in/2861/2206 | The interleaved traversal: pattern chain, then directed parent as the basis for a fresh pattern search, repeating to @baseclass |
| Pega docs — General tab on the Class form | https://docs.pega.com/bundle/platform-242/page/platform/app-dev/general-tab-class-form.html | "Use class-based inheritance…" and "Find by name first (Pattern)?" semantics; `pyPatternInheritance`; class-group forcing the checkbox; immutability after save |
| 12 CFR 1005.2(d) + official interpretation | https://www.consumerfinance.gov/rules-policy/regulations/1005/2 | Reg E business day = institution open for substantially all business functions; back-office test; Saturday example; short-hours election; 24-hour period |
| 12 CFR 1005.11 | https://www.consumerfinance.gov/rules-policy/regulations/1005/11 | 10 business days; 3 business days to report; 1 business day to correct; 45 calendar days; provisional credit within 10 business days; notify within 2 business days; 20-business-day new-account extension; 90-day extension |
| 12 CFR 229.2(f),(g) | https://www.ecfr.gov/current/title-12/chapter-II/subchapter-A/part-229/subpart-A/section-229.2 | Reg CC banking day and the enumerated ten-holiday business-day list, including the Sunday rollover and the absence of Juneteenth |

Mark the Pega docs row `support/product documentation`; mark Academy rows `training`. Both are
release-sensitive — state the release where the chapter depends on it.
