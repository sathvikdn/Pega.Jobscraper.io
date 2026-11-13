# LTIM Study Pack — Authoring Spec

Authoring contract for every chapter in this folder. Read this, plus
`_research_dossier.md`, plus `assets/sourcebook.css`, plus the finished exemplars in
`..\FCB_Study_Pack\` (`ch04_ui_constellation_dx.html`, `ch07_file_email_listeners.html`)
before writing anything.

This pack is a **sibling** to `FCB_Study_Pack`, same house style, different target.

## 1. Who this is for and why

Sathvik DN — Pega CSSA + CSA, ~4.5 years at Mercedes-Benz R&D India — preparing for
**LTIMindtree (now branding as "LTM")** Pega roles that combine three things named in
their live requisitions and their internal enablement:

1. What LTIMindtree's Pega practice actually does, and how its teams are shaped.
2. **Pega Customer Service** — the strategic application.
3. **Pega Constellation and React** — the Constellation DX API, DX Components and the
   Constellation React SDK.

He asked for "3 hour reading material" covering all three. **The pack is three chapters,
one per topic, each sized for roughly one hour of careful reading.** He reads this
directly, under time pressure, to prepare for interviews and to decide what to put on his
resume. It is a textbook, not a summary.

## 2. Mandatory file skeleton

Identical to the FCB pack. Standalone HTML, `assets/sourcebook.css`, toolbar, cover,
chapter map, numbered sections, `.chapnav` at the end **inside `<main>` but outside the
last `<section>`** (note: ch04/ch07/ch09 of the FCB pack were corrected to this shape —
follow the corrected form).

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ch02 · Pega Customer Service | LTIM Study Pack</title>
<link rel="stylesheet" href="assets/sourcebook.css">
</head>
<body>
<div class="toolbar">
  <button onclick="window.print()">Print / Save as PDF</button>
  <a class="btn" href="index.html">Study Pack Index</a>
  <a class="btn" href="ch03_constellation_react.html">Next Chapter →</a>
</div>
<div class="book">
  <div class="cover">
    <div class="kicker">Chapter 02 · LTIM Pega Study Pack</div>
    <h1>Chapter title</h1>
    <p class="subtitle">What this chapter makes you able to do.</p>
    <div class="meta">
      <div><strong>N</strong><span>Sections</span></div>
      <div><strong>N</strong><span>Interview Q&amp;A</span></div>
      <div><strong>Nk</strong><span>Words</span></div>
      <div><strong>~60</strong><span>Min read</span></div>
    </div>
  </div>
  <main>
    <section><h2>Chapter map</h2><div class="toc">...</div>
      <div class="note"><strong>Honest scope.</strong> ...</div>
      <div class="note"><strong>Accuracy convention.</strong> ...</div>
    </section>
    <!-- numbered sections -->
    <div class="chapnav"><a href="index.html">← Index</a><a href="...">Next →</a></div>
  </main>
</div>
</body>
</html>
```

Use only classes defined in `assets/sourcebook.css`: `.toolbar`, `.book`, `.cover`,
`.kicker`, `.subtitle`, `.meta`, `.toc`, `.grid`, `.grid3`, `.card` (+ `.blue/.green/
.amber/.red`), `.tag`, `.answer`, `.warning`, `.dont`, `.note`, `.flow`, `.formula`,
`code`, `table/th/td`, `.qa` (+ `.q`), `.chapnav`, `.pagebreak`, `.small`, `.muted`.
**No new classes, no inline `<style>`.** Note the fourth `.meta` tile is "Min read" in this
pack, not "A4 / Print ready".

## 3. Depth bar

**6,000–9,000 words per chapter.** One hour of careful technical reading each. Every
concept gets: plain-English definition → why it exists / what came before → how it is
actually implemented (real names, real config, as a `<table>`) → a `.flow` diagram →
a concrete worked example → pitfalls → interview framing.

Per chapter: **14–18 `.qa` blocks**, at least **3 `.answer`** lead-level framing callouts,
at least **2 `.flow`** diagrams, and a closing `N.R Authoritative references` section in
the same shape as the FCB pack's reference sections (Source / URL / Release or date /
What it supports).

## 4. Honesty constraint (critical — never violate)

Read `_research_dossier.md` §7 in full. In short:

**Owned in production (write confident first-person answers):** Pega case management,
flows, stages, SLAs, routing, Data Pages, Data Transforms, decision rules, Connect-REST,
Service-REST, Connect-SOAP, Connect-SQL, Kafka ingestion (50+ topics, Datasets, Data
Flows), Queue Processors, Job Schedulers, SFTP/AXWAY file integration, correspondence
and SMS frameworks, Report Definitions, PDC/Tracer/PAL, CI/CD and release management,
production support and hypercare, guardrail discipline (95+).

**NOT owned — never phrase as experience:** the Pega Customer Service strategic
application, the Interaction Portal, Constellation (any part), Constellation DX API,
Constellation DX Components, the Constellation React SDK, React itself, Pega Blueprint,
CDH/NBA strategies, Infinity 24.x.

Three things the pack must handle explicitly and unflinchingly:

1. **The "Customer Service" ambiguity.** His resume lists Customer Service alongside
   Collections, Debt Recovery and Remarketing at MBFS. That is a *business function* built
   as custom case management — it is almost certainly not the Pega CS product. Chapter 02
   must give him the exact wording that claims the real credit without implying the
   framework, and must warn that a CS interviewer will probe it within two minutes.
2. **Constellation and React are a genuine gap, not a framing problem.** Chapter 03 says
   so plainly and then makes him genuinely conversant plus gives a ramp plan.
3. **8.x vs the JD's 24.x.** Name it; don't paper over it.

Use the FCB pack's tagging convention where a resume claim needs backing:
`<span class="tag amber">CLAIM — NEEDS DETAIL</span>`.

## 5. Style rules

- Number sections `N.1`, `N.2`…; `class="pagebreak"` on major sections.
- No emojis. Professional, plain, direct. British/neutral spelling as in the FCB pack.
- **Never invent**: Pega rule names, field labels, API endpoint paths, LTIM client names,
  LTIM team names, headcounts, or interview-process detail. If unsure, describe
  functionally. He will be quizzed by real Pega people and by LTIM's own practice leads.
- **All LTIMindtree claims must trace to `_research_dossier.md`.** If it is not in the
  dossier, it does not go in the pack. Inferences must be visibly labelled as inference.
- Pega product behaviour is release-sensitive: describe function, flag the release, and
  tell him to confirm against docs for the deployed version — exactly as the FCB pack does.
- Cross-reference `..\FCB_Study_Pack\ch04_ui_constellation_dx.html` for the traditional-UI
  and DX API groundwork rather than repeating it; this pack goes deeper on Constellation.

## 6. Chapter manifest

| File | Chapter | Target |
|---|---|---|
| `index.html` | Pack index and the 3-hour reading plan | lead-authored |
| `ch01_ltimindtree_pega_practice.html` | 01 · LTIMindtree's Pega Practice: company, partnership, teams, and the roles they hire | ~7k words |
| `ch02_pega_customer_service.html` | 02 · Pega Customer Service: the strategic application | ~8k words |
| `ch03_constellation_react.html` | 03 · Constellation and React: architecture, DX API, DX Components, SDK | ~9k words |

### ch01 — LTIMindtree's Pega Practice
The company and its scale; the L&T lineage and the LTI+Mindtree merger; the LTM rebrand
(he must not be caught out when the careers site says LTM). The Pega partnership in depth:
Global Elite status and what Pega's Authorized → Specialized → Elite tiering actually
means; the Ruletronics acquisition as the origin of the practice; the award record and
what it reveals about where they are strong (HCLS, manufacturing/automotive, workflow
automation) versus where they merely offer (contact centre). The industry verticals and
the named strategic applications (Customer Services, Warranty, Recall, Field Service).
The CoE-plus-squad delivery model: what a Pega CoE actually owns at an SI, what
accelerators are and why partners build them, and the squad/tribe/chapter vocabulary from
JD-C with an explanation of where that language comes from. Then the four JD archetypes
reproduced and decoded line by line — what each line is really testing. Then an explicit
fit-mapping table: his evidence against each JD requirement, including the misses. Close
with questions *he* should ask an LTIM interviewer that demonstrate he understands the SI
delivery model (bench vs billable, which client, CoE vs client-embedded, upgrade work vs
greenfield, Constellation adoption stage). Q&A should include the "why are you leaving a
product company for a services company" question, honestly answered.

### ch02 — Pega Customer Service
What Pega CS *is*: a strategic application layered on Infinity, with its own class
hierarchy, data model and portal — not a platform feature and not something you get by
building cases yourself. Why it exists. The **Interaction** as the wrapper case and
service cases as the work inside it; the relationship between Interaction, service request
type, case type and **Microjourney** — define Microjourney properly as Pega uses the term.
The **Interaction Portal** and its six functional areas (navigation bar, customer details,
suggestions, action area, composites, utilities and channels) — from the dossier/Academy
material; cover both the UI Kit portal and the Constellation portal introduced in Pega CS
23. Channels: voice/CTI, email, chat and digital messaging, self-service, co-browse,
transfer and queue routing, CSR availability. Intelligence: Next-Best-Action Advisor and
its link to CDH, Pega Knowledge, suggested replies and common phrases, CSR assistant,
GenAI summarisation (mark as release-sensitive). The industry editions and real named
Microjourneys from the Pega docs — Communications (Billing Inquiry, Add Mobile Device and
Plan, Guided Internet Setup, Make Payment, Move Service) and Financial Services (Change
PIN, Fee Inquiry, Make Payment, Manage Lost or Stolen Card, Travel Notification, Payment
Inquiry, Repossession and Collateral Management, Manage Customer-Circumstance). Explain
the contact-centre metrics that drive every CS conversation — **AHT**, **NPS**, first
contact resolution, containment — because Pega CS design decisions are justified in those
terms and he will be expected to speak that language. Extension points: configuring and
extending service request types, interaction drivers, routing. Then the honest mapping
section: what his Collections/Debt Recovery work genuinely transfers (case lifecycle,
SLAs, routing, correspondence, integration under a live agent's hands, seven-market
rollout) and what it does not.

### ch03 — Constellation and React
The UI lineage: UI Kit → Theme Cosmos → Cosmos React → Constellation, including the
**8.8 renaming** (Cosmos React → Constellation design system, DX API v2 → Constellation
DX API, SDKs → Constellation SDKs) — this is a lead-verified fact in the FCB pack, state
it confidently. The architectural break: server-side section/harness rendering versus
client-side **view**-based rendering; MVC, microservices and **stateless** requestors with
the Clipboard released after each DX API call, and the consequences (no session affinity
needed at the load balancer except for Studios; multiple tabs do not multiply threads;
When rules still run server-side while expressions run client-side). The **Constellation
UI Service** as a static-content microservice, auto-provisioned on Pega Cloud. The
**Constellation DX API versus Traditional DX API** comparison in full — view-based vs
harness/section-based, data/layout separation, HATEOAS and available actions, reduced
chattiness, extra endpoints (follow/unfollow, change stage) — and when each is correct.
**Mashups are replaced by Web Embed.** **Coexistence and hybrid adoption** — the
Constellation UI Service in a traditional app (Constellation landing pages, tables and
Constellation Cases inside a section-based app), and Pega CS coexistence running UI Kit
service requests from the Constellation Interaction Portal; why an app's UI architecture
cannot be casually flipped.

Then the part that matters most, because he will otherwise conflate them — **the three
distinct levels at which React appears**, as a table and then one subsection each:
1. The Constellation design system is itself React. He consumes it; he does not write it.
2. **Constellation DX Components** — custom React components built with the DX Component
   Builder, published back to the server, then used by low-code authors in App Studio
   exactly like out-of-the-box components. Needs React, npm and Git. Types: widgets,
   templates, controls. Usable in native Pega UI, Web Embed, or a React SDK app.
3. **Constellation React SDK** — a React bridge from the ConstellationJS Orchestration
   Engine to a *non-Pega* design system (the reference implementation uses Material UI).
   Packages `@pega/react-sdk-components` and `@pega/react-sdk-overrides`; repos
   `pegasystems/react-sdk` and `pegasystems/react-sdk-components`; the MediaCo sample app;
   **embedded** (most common) versus **portal** use cases.

Then: the minimum React he actually needs — components, props, JSX, state and effect
hooks, the npm/build/bundle toolchain, and why a Pega server-side developer finds the
client-side mental model unfamiliar. Debugging Constellation: the browser network tab on
DX API calls, why Tracer does not see client-side rendering, where the server-side portion
is still traceable. Governance: why every custom DX component is a future upgrade cost,
the same argument the FCB pack makes about custom controls.

Close with the **ramp plan**: Pega Academy Constellation and DX component topics, a
Personal/Community Edition or trial for hands-on, cloning `pegasystems/react-sdk` and
running the MediaCo sample, and building one trivial DX component end to end. Give him
something he can genuinely say he has done within a week — and be explicit that the
honest claim after that week is "I have built a sample DX component against the SDK",
never "I have delivered Constellation in production".
