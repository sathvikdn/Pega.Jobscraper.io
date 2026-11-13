# Pega GCC Ranking — Compact Handoff Brief

> **Condensed context-transfer document** for small context windows. Carries the rubric, methodology, corrections, the two comparable ranking tiers and the known gaps — but omits per-company detail blocks, the Low-confidence table and the full lifestyle ledger. For those, use `PEGA_GCC_HANDOFF_BUNDLE.md`.

| | |
|---|---|
| **Data as of** | 2026-10 (scores generated 2026-10-02T16:46:44.285Z) |
| **Bundle generated** | 2026-10-02T17:13:54.915Z |
| **Companies scored** | 89 (+1 with insufficient evidence) |
| **Rubric** | GCC Engineering Culture & Autonomy Score, max 100 |
| **Source of truth** | `gcc_ranking_scores.json` (207.1 KB), `gcc_lifestyle_supplement.json` (13.4 KB) |

---

## 0. Read this before you use any number in here

This dataset has **one dominant limitation**, and it is quantified rather than hidden:

> **`corr(total_score, raw evidence volume) = 0.839`**

Score correlates 0.839 with raw evidence volume (people + audit rows). A low score predominantly indicates thin public evidence, not a poor engineering environment. Only compare companies within the same evidence_confidence tier.

**Practical consequence:** there is deliberately **no single 1-to-89 league table** in this
work. Companies are only rank-comparable *within* an evidence-confidence tier. A
company at score 35 is very often a company nobody researched, not a bad employer.

Other standing caveats, verbatim from the output file:

- **Tenure rule:** Pillar 4 scored only when >=3 engineers have parseable tenure; 55 of 89 companies fall below that and are recorded as Unknown rather than penalised.
- **Short-tenure rule:** Low average tenure is penalised only where departure evidence outweighs join evidence; intern-conversion and new-team growth are not treated as burnout.
- **Rubric arithmetic:** Spec's Pillar 2 itemised to 25 but was labelled Max 30, making the rubric total 95. A third +5 cloud/platform tier closes the gap to a true 100.
- **Not measured:** Glassdoor ratings and compensation were not used: no reliable programmatic source was available. No private profile data was accessed.

**Provenance.** All evidence came from the **public web search index** (search-result
text for public LinkedIn profiles, company career pages, official company blogs,
conference and award listings). No private profile data, no logged-in scraping, no
paid data source. It is **researched data with a timestamp, not a live employment
feed** — treat every individual's employer/title/location as "true as of 2026-10".

---

## 1. Who this research is for

The ranking was built for a specific candidate. Fit judgements only make sense
against this profile:

- **Name:** Sathvik D N
- **Current employer:** Mercedes-Benz R&D India (MBRDI), Bengaluru
- **Role:** Software Consultant — Pega
- **Certification:** Pega **CSSA** (no LSA/CLSA yet)
- **Core technical identity:** Pega + **Apache Kafka** event integration, **collections** domain, custom Java steps, enterprise REST/SOAP integration
- **Experience band targeted by matching roles:** ~4–7 years
- **Compensation band in play:** **₹24–27 LPA**
- **Geography:** Bengaluru / India GCCs and product companies

**Why the rubric is shaped the way it is:** the explicit goal was to filter out
"glorified L2/L3 support" shops and find places doing **real enterprise
engineering** — where India owns architecture rather than executing tickets.

---

## 2. The rubric

### 2.1 As originally specified

**Pillar 1 — Architectural Autonomy (max 30).** Who actually owns the Pega roadmap.
- **+30** Global Head of Pega/Workflow or Principal Pega Architect sits in India (India is the brain).
- **+15** India has Senior/Lead System Architects but the global VP is in US/EU (standard split-ownership GCC).
- **−20** Most senior India titles are "Delivery Manager", "Operations Lead", "Support Manager" (cost-centre / body-shop).

**Pillar 2 — Modernity & Integration Density (max 30).**
- **+15** Legacy-middleware migration, Apache Kafka, event-driven architecture, complex REST/SOAP enterprise nervous systems.
- **+10** Constellation UI, React integration, custom Java steps/wrappers for complex data parsing.
- **−15** JD heavily emphasises "L2/L3 support", "ticket resolution", "version upgrades".

**Pillar 3 — Talent Density & Innovation Visibility (max 20).**
- **+10** India team presented a use-case at PegaWorld in the last 3 years.
- **+10** Engineers publish tech blogs, open-source repos, or answer complex architecture questions on Pega Community.

**Pillar 4 — Burnout & Attrition Index (max 20).**
- **+20** Average Pega-engineer tenure 3+ years (stable, healthy).
- **+5** Average tenure 1.5–3 years.
- **−20** Rampant job-hopping, most leaving before 18 months (toxic management or dead-end work).

### 2.2 Two corrections made to the spec — and why

**Correction 1 — the rubric did not add up to 100.**
Pillar 2 is labelled "Max 30" but its items total 25 (+15 integration, +10 modern UI),
making the true maximum **95**. Closed with a third **+5 cloud/platform tier**
(Pega Cloud, AWS, OpenShift/K8s, CI/CD, PDC). Recorded in the output as:
*"third +5 cloud/platform tier added to close the spec's 25-vs-30 gap"*

**Correction 2 — "short tenure = burnout" is wrong, and it inverted a real company.**
Under the literal rule, **First Citizens India** scored **−20 "High attrition"**. The
cause: all 13 of its detected "departure" signals were the strings
`ex-Pegasystems`, `ex-Cigna`, `ex-EvonSys` — those are **prior employers of people
who had just joined**, i.e. a *quality-of-hire* signal being read as an exit signal.
Its low average tenure was because it hired 3 senior engineers in 2026, 8 of them
ex-Pegasystems. It is now correctly **+5 growth-driven**.

Implemented rule: low tenure is penalised **only** where departure evidence
outweighs join evidence. Intern conversion and new-team growth are not burnout.

### 2.3 As actually implemented

| Pillar | Max | Min | Implementation note |
|---|--:|--:|---|
| P1 Architectural autonomy | 30 | -20 | Requires **named, located, currently-active** evidence. Departed staff cannot evidence present-day authority. Unknown location ≠ India. |
| P2 Modernity & integration | 30 | -15 | third +5 cloud/platform tier added to close the spec's 25-vs-30 gap |
| P3 Innovation visibility | 20 | 0 | Conference/award evidence + community/build-in-public evidence. |
| P4 Attrition index | 20 | -20 | scored only when >=3 engineers have parseable tenure; low tenure penalised only when departure-driven |

**Evidence-confidence tiers (exact logic from `gcc_score_rubric.mjs`):**

```
High   : >=3 distinct sources AND Pillar-4 measured AND >=5 people
Medium : >=2 distinct sources AND (Pillar-4 measured OR >=4 people)
None   : 0 people AND 0 audit rows  -> not scored at all
Low    : everything else            -> "score is indicative only"
```

A company is marked `rank_comparable: true` only in the **High** and **Medium** tiers.

---

## 3. Results

### 3.1 Distribution

| Measure | Value |
|---|--:|
| Scored | 89 |
| Insufficient evidence (not scored) | 1 |
| **High** confidence | 25 |
| **Medium** confidence | 23 |
| **Low** confidence | 41 |
| Attrition **Unknown** (below n≥3 tenure bar) | 55 |

That last row is the headline weakness: **55 of 89 companies have no
measurable tenure**, so Pillar 4 — a 40-point swing — is simply absent for them.
They are recorded as Unknown, **not penalised**.

### 3.2 High-confidence tier — the only genuinely comparable ranking

| # | Company | Score | P1 | P2 | P3 | P4 | Tenure | Attrition | Overall rank |
|--:|---|--:|--:|--:|--:|--:|---|---|--:|
| 1 | **Ford Motor Company** | 100 | 30 | 30 | 20 | 20 | 3.19y (n=8) | Low | 1 |
| 2 | **Commonwealth Bank** | 85 | 15 | 30 | 20 | 20 | 3.11y (n=10) | Low | 2 |
| 3 | **Vodafone / VOIS** | 85 | 15 | 30 | 20 | 20 | 3.46y (n=8) | Low | 3 |
| 4 | **Sun Life** | 80 | 30 | 10 | 20 | 20 | 3.25y (n=10) | Low | 4 |
| 5 | **JPMorgan Chase** | 75 | 30 | 30 | 10 | 5 | 2.94y (n=13) | Medium | 5 |
| 6 | **Wells Fargo** | 75 | 15 | 30 | 10 | 20 | 4.32y (n=14) | Low | 6 |
| 7 | **Barclays** | 75 | 15 | 20 | 20 | 20 | 3.96y (n=9) | Low | 8 |
| 8 | **Stellantis** | 75 | 30 | 5 | 20 | 20 | 3.87y (n=7) | Low | 9 |
| 9 | **Citibank** | 75 | 15 | 30 | 10 | 20 | 3.45y (n=5) | Low | 10 |
| 10 | **NatWest Group** | 75 | 30 | 15 | 10 | 20 | 3.3y (n=5) | Low | 11 |
| 11 | **HSBC** | 70 | 30 | 20 | 0 | 20 | 3.22y (n=8) | Low | 12 |
| 12 | **Siemens** | 65 | 15 | 10 | 20 | 20 | 5.08y (n=5) | Low | 14 |
| 13 | **John Deere India (JDTCI)** | 65 | 15 | 30 | 0 | 20 | 5.49y (n=6) | Low | 15 |
| 14 | **BT Group** | 65 | 15 | 30 | 0 | 20 | 3.77y (n=4) | Low | 16 |
| 15 | **Optum / UnitedHealth Group** | 60 | 15 | 15 | 10 | 20 | 5.99y (n=6) | Low | 19 |
| 16 | **Standard Chartered** | 50 | 15 | 5 | 10 | 20 | 4.92y (n=9) | Low | 22 |
| 17 | **Bank of America** | 50 | 15 | 15 | 0 | 20 | 4.75y (n=8) | Low | 24 |
| 18 | **Empower** | 50 | 15 | 15 | 0 | 20 | 5.47y (n=3) | Low | 25 |
| 19 | **Allianz Technology** | 50 | 15 | 15 | 0 | 20 | 7.28y (n=3) | Low | 26 |
| 20 | **Verizon** | 50 | 15 | 15 | 0 | 20 | 3.52y (n=8) | Low | 27 |
| 21 | **American Express** | 45 | 15 | 15 | 10 | 5 | 2.08y (n=7) | Medium | 30 |
| 22 | **Lloyds Banking Group** | 45 | 15 | 15 | 10 | 5 | 1.69y (n=4) | Medium | 32 |
| 23 | **Evernorth / Cigna** | 35 | 15 | 15 | 0 | 5 | 1.8y (n=5) | Medium | 35 |
| 24 | **MetLife India GCC** | 35 | 15 | 15 | 0 | 5 | 1.68y (n=6) | Medium | 36 |
| 25 | **First Citizens India** | 35 | 15 | 15 | 0 | 5 | 1.17y (n=6) | Medium | 37 |

### 3.3 Medium-confidence tier — comparable with care

| # | Company | Score | P1 | P2 | P3 | P4 | Tenure | Attrition | Overall rank |
|--:|---|--:|--:|--:|--:|--:|---|---|--:|
| 1 | **Mercedes-Benz R&D India (MBRDI)** | 75 | 15 | 30 | 10 | 20 | 4.25y (n=9) | Low | 7 |
| 2 | **Carelon Global Solutions India** | 70 | 15 | 25 | 10 | 20 | 3.53y (n=3) | Low | 13 |
| 3 | **Nokia India** | 65 | 15 | 30 | 0 | 20 | 4.39y (n=7) | Low | 17 |
| 4 | **Cisco India** | 65 | 15 | 30 | 0 | 20 | 3.86y (n=3) | Low | 18 |
| 5 | **BNP Paribas** | 55 | 15 | 20 | 20 | 0 | 8.17y (n=1) | Unknown | 21 |
| 6 | **Pegasystems India** | 50 | 15 | 15 | 0 | 20 | 3.5y (n=3) | Low | 23 |
| 7 | **Morgan Stanley** | 50 | 15 | 15 | 0 | 20 | 4.06y (n=3) | Low | 28 |
| 8 | **S&P Global** | 50 | 15 | 5 | 10 | 20 | 7.5y (n=3) | Low | 29 |
| 9 | **Booking Holdings India** | 45 | 15 | 10 | 20 | 0 | 1.42y (n=2) | Unknown | 31 |
| 10 | **Goldman Sachs** | 45 | 15 | 10 | 20 | 0 | 6.08y (n=2) | Unknown | 33 |
| 11 | **Rabobank** | 40 | 0 | 30 | 10 | 0 | 2.92y (n=1) | Unknown | 34 |
| 12 | **Shell India** | 35 | 15 | 0 | 0 | 20 | 4.92y (n=3) | Low | 38 |
| 13 | **Societe Generale** | 35 | 15 | 10 | 10 | 0 | 8.21y (n=2) | Unknown | 39 |
| 14 | **ANZ Bank** | 35 | 15 | 20 | 0 | 0 | no data | Unknown | 41 |
| 15 | **Broadridge** | 30 | 15 | 5 | 10 | 0 | 3.42y (n=2) | Unknown | 43 |
| 16 | **Telstra** | 25 | 15 | 10 | 0 | 0 | 4.63y (n=2) | Unknown | 50 |
| 17 | **NAB (National Australia Bank)** | 25 | 15 | 10 | 0 | 0 | 2y (n=2) | Unknown | 51 |
| 18 | **Ameriprise Financial** | 25 | 15 | 10 | 0 | 0 | 6.75y (n=2) | Unknown | 52 |
| 19 | **Charles Schwab** | 25 | 15 | 0 | 10 | 0 | 5.83y (n=1) | Unknown | 54 |
| 20 | **Intel India** | 25 | 15 | 10 | 0 | 0 | 4.25y (n=1) | Unknown | 55 |
| 21 | **MUFG Pension & Market Services (Link Group)** | 20 | 15 | 0 | 0 | 5 | 2.75y (n=6) | Medium | 59 |
| 22 | **Amdocs** | 20 | 15 | 5 | 0 | 0 | no data | Unknown | 60 |
| 23 | **BNY Mellon** | 15 | 15 | 0 | 0 | 0 | 11.33y (n=1) | Unknown | 68 |

### 3.4 Low-confidence tier

41 companies omitted here — their scores mostly measure research
coverage, not quality. See the full bundle. Treat them as "not yet assessed".

---

## 5. The lifestyle / "fun quotient" layer — an evidence ledger, NOT a score

### 5.1 Why there is no lifestyle score

A 50-point "Lifestyle Index" was specified (food & commute 15, insurance 15,
flexibility 10, campus vibe 10). **It was deliberately not implemented as a score.**

Reason, verbatim from the ledger:

> LIFESTYLE EVIDENCE LEDGER - deliberately NOT a score. Lifestyle perks vary by role, grade, shift and year, and sources openly contradict each other, so any numeric index would imply precision the evidence cannot support. Each claim therefore carries its own status and sources. Keep the 100-point engineering score (gcc_ranking_scores.json) separate and unmodified: that one rests on verifiable architecture and tenure evidence, this one does not.

The decisive test case: the anchor claim for the top +15 food tier was *"Goldman
Sachs — free gourmet meals and free AC cabs"*. Checking it produced **direct
contradiction**:

| Source | Says |
|---|---|
| GS official benefits page | "**reimbursement** for certain entertainment, meals… transportation" — not free |
| GS official Bengaluru PDF | "We provide transportation within 30 kilometres" — transport ✅, meals unmentioned |
| AmbitionBox (Production Eng, 2022) | "free food and transportation" ✅ |
| Taro (Assoc. Software Engineer, Sep 2023) | "**Almost no free benefits; everything is to be paid for: food, cabs, gym**" ❌ |
| Quora (IB context) | "almost all of them have the no free lunches concept" ❌ |

Transport is well-supported. **Free meals is contested** — and it was the calibration
anchor for the entire +15 tier. Scoring on that base would have produced confident
numbers resting on role-, grade- and year-dependent anecdote.

**Correction to an earlier claim made during this work:** Glassdoor/AmbitionBox were
first reported as programmatically inaccessible. That was too absolute — AmbitionBox
*does* return review content. What is unreliable is the **data** (self-reported,
varies by role/level/year), not the access.

### 5.2 Status legend

- **`VERIFIED`** — Stated on an official company careers/benefits page or official company blog, and applicable to the India/Bengaluru location.
- **`VERIFIED_GLOBAL_POLICY`** — Stated on an official global page, but the page does not confirm it applies to the India office. Confirm with the recruiter.
- **`CONTESTED_BY_ROLE`** — Credible sources disagree, typically because the benefit depends on grade, shift or year. Treat as a question to ask, not a fact.
- **`UNVERIFIED`** — Commonly repeated but not found on an official source during this pass. Do not rely on it.
- **`NOT_RESEARCHED`** — No lifestyle research performed for this company yet. Absence here is not a negative signal.

### 5.3 Claim tally (computed across the ledger)

| Status | Claims |
|---|--:|
| `NOT_RESEARCHED` | 16 |
| `UNVERIFIED` | 7 |
| `VERIFIED` | 5 |
| `VERIFIED_GLOBAL_POLICY` | 4 |
| `CONTESTED_BY_ROLE` | 1 |
| **Total** | **33** |

**Coverage:** 8 of 89 ranked companies.
Lifestyle research covers 8 of 89 ranked companies. Do not read an absent or thin lifestyle entry as a negative signal - it means no research has been done. The three companies with genuinely verified India-applicable evidence are Cisco India, Booking Holdings India and Goldman Sachs.

### 5.5 The gap this layer still leaves

**The top of the engineering ranking is exactly where lifestyle evidence is thinnest.**
Ford ranks #1 at 100/100 with essentially no verified lifestyle research; the same
applies to Commonwealth Bank (85) and Vodafone/VOIS (85). So the tiebreaker works
for Cisco vs Booking vs Goldman and is effectively **blank for the elite tier**.

---

## 6. Bug log — 15 defects found during review

This section exists so a model continuing the work **does not reintroduce these**.
Every one was found by reading scores back against source evidence, not by testing.

| # | Defect | Effect | Fix |
|--:|---|---|---|
| 1 | Pillar-1 title regex missed GCC/Indian senior phrasing (`Executive Director`, `Head Pega CoE`, `Director - Engineering Lead`, `SVP - Principal Solution Architect`, `Director - CLSA`) | Probe reported **0** companies with top-level leadership; 41 real senior titles unmatched | Broadened title ladder |
| 2 | `ex-Pegasystems`/`ex-Cigna`/`ex-EvonSys` counted as **departures** | First Citizens read **−20 High attrition** while actually hiring aggressively | Treat prior-employer strings as **join/quality-of-hire** signals |
| 3 | Pillar 2 itemised to 25 but labelled max 30 | Rubric total was 95, not 100 | Added **+5 cloud/platform** tier |
| 4 | Commonwealth Bank's perfect 100 rested on a person tagged `DEPARTED` | Overstated present-day India authority | P1 requires **active** personnel → CBA 85 |
| 5 | BNY Mellon credited India autonomy via **Virad Fernando**, who is in **Pittsburgh** (empty location field) | False +30 | Empty location = **unknown**, never India |
| 6 | Visa and GE HealthCare got +30 from **single-person** entries via a loose text match (any "Director" + any India city within a ~5,000-char blob) | False +30 ×2 | Require named + located + corroborated evidence |
| 7 | Barclays scored **0** on autonomy despite `AVP - Pega Tech Lead`, `Pega Lead`, `Development Lead` + CLSA certs | Regex required the literal "lead pega" | Added Indian-bank title phrasing → Barclays 75 |
| 8 | `Principal Consultant` / `Principal Engineer` counted as **global ownership** | These are senior **IC** grades at Indian GCCs, not roadmap ownership | Demoted to architect tier |
| 9 | After fix 8, HSBC was **under**-credited — Pradeep V genuinely *is* Global Head of Pega & Cloud Platform in Bengaluru | Lost a true +30 | Separated unambiguous ownership phrasing from generic seniority → HSBC 70 |
| 10 | `NON_INDIA` list lacked **Germany** (also Japan, Poland, Canada, UAE), **and** the India test matched "Bengaluru" inside the parenthetical `"Germany (ex-MBRDI Bengaluru)"` | A Germany-based engineer counted inside MBRDI's **India** ladder | Residency tests the **primary** location only |
| 11 | Ladder described as "LSA/architect-level" when **none** of the matched people held LSA/CLSA | Overstated seniority in generated prose | New red flag *"No LSA/CLSA-certified architect evidenced in the India sample"* |
| 12 | Concatenation bug emitting `"seniorlead"` | Cosmetic, in generated prose | String fixed |
| 13 | **LATENT, still unfixed** — the primary-location residency test from fix 10 was applied to **Pillar 1 only**. The Pillar-4 tenure sample in `gcc_build_evidence.mjs` applies **no location filter at all**, so a non-India person can sit inside an "India team stability" average. | Measured: **1 of 265** tenure samples company-wide come from a non-India primary location, across **1 company/companies** (Rabobank n=1→0). **No company's Pillar-4 grade changes** if this is filtered, because no affected company sits at or above the n≥3 bar on the strength of a non-India sample. | Not fixed, because it currently changes nothing. **Fix it before adding more people data**, or the first non-India hire will silently distort an average. |
| 14 | **The LSA audit never ran on the top of the ranking.** Two compounding faults: (a) the "No LSA/CLSA-certified architect" red flag lived *inside* the `+15` ladder branch, so all **8** companies scoring **+30** skipped it entirely; (b) `/\b(?:lsa\|clsa\|pclsa)\b/` matched **in-progress** credentials — `LSA Part 1`, `CLSA-1`, `CLSA Part 2` — so an engineer still working through the LSA track counted as a certified architect. | **Ford, ranked #1 at 100/100, showed zero red flags while having no completed LSA/CLSA anywhere in its India sample** — its +30 rests on one person holding `LSA Part 1`. Same for **NatWest (rank 11)**. Flag coverage was understated at 32 of 89. | Audit hoisted to run for **every** company with positive autonomy evidence, and completed vs mid-track credentials separated per-credential. Coverage now **54 of 89**, plus a distinct flag for in-progress-only (**12** companies). **No score moved — flags only.** |
| 15 | **The fix for defect 14 was itself incomplete.** The new LSA audit filtered `c.members` directly, applying **neither** the residency test from fix 10 **nor** the departed-exclusion from fix 7 — while its flag text asserts *"in India"*. Separately, the `INDIA` regex was **city-only**, so a profile recording an Indian *state* ("Tamil Nadu", "Kerala", "Maharashtra") matched neither the India nor the non-India list and was discarded as "unverified". | **Rabobank was credited with 4 "India" CLSA holders who are in Utrecht, Netherlands**, and **BNY Mellon was credited with Virad Fernando — the person fix 9 had already established is in Pittsburgh**. Measured before the fix (historical, not recomputable from the corrected data): of **49** flagged holders, **16** were not India-resident by primary location. In the other direction, **DHL** lost a genuine Tamil Nadu holder. | Residency and departed filters applied to the LSA audit; unlocated holders now reported under a separate flag *"Completed LSA/CLSA found, but India residency unverified"* instead of counting as India. Indian states added to `INDIA`. Flag coverage 54 of 89. **No score moved — flags only.** Exposed **Commonwealth Bank (rank 2)**, whose sole completed CLSA is tagged DEPARTED. |

### 6.1 Worked example — the MBRDI audit (how to verify any score)

Asking "who are the 9 people behind MBRDI's Pillar-1 score?" is what exposed
defects 10, 11 and 13. The matched set was:

| # | Name | Title | Matched on |
|--:|---|---|---|
| 1 | Manomit Das | Program Manager · Pega Team Lead (AAP Markets) | `Team Lead` |
| 2 | Bhanu Prasad V | Solutions Architect · Pega Architect | `Pega Architect` |
| 3 | Moumita Dasgupta | Manager / Principal Consultant · Pega PRPC Senior Architect | `Principal Consultant` |
| 4 | Rupali Chaturvedi | Principal Consultant PEGA · Lead **Business Process Analyst** | `Principal Consultant` |
| 5 | Swapneel Chitragar | Senior Consultant · Pega Developer | **`CSSA` only** |
| 6 | ~~Vinay Meher Puvvada~~ | IT Consultant · Pega Lead Developer | **REMOVED — primary location is Germany** |
| 7 | Aneesha Neeruganti | Senior Pega Developer (Hyderabad) | **`CSSA` only** |
| 8 | D Dhana Raja Rao | Application Consultant · Pega Developer | **`CSSA` only** |
| 9 | Sathvik D N | Software Consultant · Pega CSSA \| Kafka \| Collections | **`CSSA` only** |

Findings: the Pillar-1 ladder is **8**, not 9. **None holds LSA or CLSA.** 4 of 8
qualified on a CSSA certification alone. Rupali Chaturvedi is a **Business Process
Analyst** (CPBA/CBA) — a BA is not architecture authority. A strict reading of MBRDI's
actual architecture ladder is **3**: Bhanu Prasad, Moumita Dasgupta, Manomit Das.

**Do not confuse the two MBRDI counts.** The Pillar-1 ladder is 8 people; the
Pillar-4 tenure sample is a **different set** of 9 (it includes the two DEPARTED
engineers, Eshwar M H and Mithun R, whose completed stints are legitimate attrition
data, and excludes Vinay). Vinay is absent from the tenure sample only because he has
no parseable career dates — **not** because a residency filter removed him. That is
defect 13.

**Reproduce any company's score the same way:**
```bash
node gcc_explain_company.mjs "Mercedes-Benz R&D India (MBRDI)"
```

### 6.2 The same audit applied to Ford (#1) — read this before treating 100/100 as settled

Running `gcc_explain_company.mjs "Ford Motor Company"` is what exposed defect 14.
Ford's 100/100 is real against the rubric, but the composition matters:

- Its **+30 autonomy rests on one person**: Abinaya Elavarasan, *Technical Project
  Manager — FORD Pega CoE Lead*, Chennai. Credentials: **`LSA Part 1`**, CSSA, CSA —
  i.e. **mid-LSA-track, not a completed LSA**.
- Its architect ladder is **7 people, of whom 6 qualified on certification alone**
  (CSSA/CPDC), including one *"Intern converted to FTE"*. Only **1** qualified on an
  architect/lead title.
- **No completed LSA or CLSA exists anywhere in Ford's India sample.**

Of the 8 companies scoring **+30** on autonomy, **4** have no completed LSA/CLSA in
India: Ford Motor Company (rank 1), NatWest Group (rank 11), enGen / Highmark India (rank 20), Global Payments India (rank 49).

**Career consequence, stated plainly.** The strongest argument for leaving MBRDI was
"there is no completed LSA/CLSA above you to learn from." **Ford has that exact same
gap** — so on the mentorship criterion it is not an upgrade, despite ranking #1.

### 6.3 Mentorship availability — the ranking's single most decision-relevant cut

Only **23 of 89** companies have a **confirmed India-resident, currently-employed
engineer holding a completed LSA/CLSA**. This list is generated from the scorer's own
green flags, so it cannot drift from the data. The **Named holders** column is capped
at the first three names by the flag text, so where the count is 4 only 3 are listed.

| India CLSA/LSA holders | Rank | Score | Company | Named holders |
|--:|--:|--:|---|---|
| **4** | 6 | 75 | Wells Fargo | Raja Reddy Bommana, Rajesh Manem, Ram Epuri |
| **3** | 32 | 45 | Lloyds Banking Group | Srinivas Yalagala, Vijay Mahesh Bobba, Rammohan Tattikota |
| **3** | 33 | 45 | Goldman Sachs | MAYANK VISHWAKARMA, Pavan Kumar Raavi, Priyabharathi Ayyaswamy |
| **2** | 3 | 85 | Vodafone / VOIS | Ganesh Mahagaonkar, Praveen Kesari |
| **2** | 8 | 75 | Barclays | Girish Gaikwad, Harshad Mankar |
| **2** | 23 | 50 | Pegasystems India | Vivek Kumar Sonu, Yesuraju Chokka |
| **1** | 4 | 80 | Sun Life | Pushkar Raj |
| **1** | 5 | 75 | JPMorgan Chase | Ashish Agrawal |
| **1** | 9 | 75 | Stellantis | Kishore Kumar Panathula |
| **1** | 10 | 75 | Citibank | Akash Pratap |
| **1** | 12 | 70 | HSBC | Punit Sharma |
| **1** | 14 | 65 | Siemens | Amit Abhishek |
| **1** | 15 | 65 | John Deere India (JDTCI) | Rahul Chaher |
| **1** | 24 | 50 | Bank of America | Rajendra Dubey |
| **1** | 28 | 50 | Morgan Stanley | Abhinav Anand |
| **1** | 30 | 45 | American Express | Rahul Kumar |
| **1** | 35 | 35 | Evernorth / Cigna | Subbarao Tatikonda |
| **1** | 37 | 35 | First Citizens India | Deepak Shahi |
| **1** | 52 | 25 | Ameriprise Financial | Sunil Murugendrappa |
| **1** | 56 | 25 | Roche India | Prashant Patil |
| **1** | 63 | 20 | Deutsche Bank | Mayank Jain |
| **1** | 68 | 15 | BNY Mellon | Janardhan Krishnan |
| **1** | 70 | 15 | DHL | Siva Jyothi Pamireddy |

**Read this against the engineering ranking, because they disagree sharply:**

- **Wells Fargo (rank 6) leads on mentorship with 4 completed CLSA holders** — more than
  any elite-tier company. It is the strongest single answer to "who can teach me LSA?"
- **Goldman Sachs holds 3 India CLSA VPs in Bengaluru** *and* owns the Collections &
  Recoveries domain — the closest match to this candidate's work. It ranks only
  33 because of thin research coverage, not a weak team.
- **2 of the 4 elite-tier companies have NO confirmed India LSA/CLSA at all**: Ford Motor Company (rank 1), Commonwealth Bank (rank 2).
  For Commonwealth Bank the only completed CLSA on its roster, Premkumar Ganesan, is
  tagged **DEPARTED**, so it is excluded — a departed architect cannot mentor anyone.

A receiving model should treat this table, not the 100-point score, as the primary
input to "which offer best develops this candidate toward LSA".

---

## 7. The n≥3 tenure threshold, and why it was not lowered

Cisco and Goldman Sachs both sat at **n=2** — just under the bar — so both read
"Unknown" attrition despite healthy averages. The threshold was **held**, because
lowering it to fit two companies would corrupt every other company's Pillar 4.

**Cisco: resolved properly.** Searching for *departed* engineers (a completed tenure
is better attrition data than an in-progress one) surfaced **Vivek Kumar Sonu**, who
left Cisco after **19 months** (Jan 2021 → Aug 2022, to Pegasystems). That third
sample moved Cisco to **n=3, avg 3.86y, Pillar 4 +20, score 45 → 65, rank 18**.
Including a *short* completed stint matters: counting only survivors biases the
average upward. Cisco now also trips the ≥3-departure red flag, so the healthy
average and the churn signal are visible together.

**Goldman Sachs: still Unknown, deliberately.** The only other GS Bengaluru person
found — Nuthan Kumar S, 8 months — is a **Java/Spring Boot backend developer on
Marcus, not a Pega engineer**. Using him to reach n=3 would have polluted the data.
Goldman remains at **45 with Unknown attrition**.

> **Important judgement for whoever continues this:** Goldman Sachs is very likely
> **under-ranked**. It has two CLSA VPs in Bengaluru — Pavan Kumar Raavi (**6y9m**)
> and Priyabharathi Ayyaswamy (**5y3m**) — both ex-Pegasystems, both working on
> **Marcus Collections & Recoveries**, the single closest domain match to the
> candidate's collections background. Its 45 reflects **missing research coverage,
> not a weak team.**

Similarly **Booking Holdings India ranks 45** despite being the strongest innovation
target (internal hackathon, A2A Protocol winner, 130-attendee Hybrid Pega Day,
2026 Impact Award). Its evidence is innovation-rich but tenure-thin (n=2). **The
rubric cannot see culture.**

---

## 9. Reproduction

```bash
# Stage 0 - coverage audit before scoring (run this first; it is the honesty check)
node gcc_rank_feasibility.mjs

# Stage 1 - merge all sources + hand-verified supplement
node gcc_build_evidence.mjs      # -> gcc_evidence_base.json

# Stage 2 - score
node gcc_score_rubric.mjs        # -> gcc_ranking_scores.json

# Audit a single company's score, person by person
node gcc_explain_company.mjs "Ford Motor Company"

# Render both layers into the HTML hub (idempotent - safe to re-run)
node build_gcc_ranking_section.mjs

# Verification gate - must be 40 PASS / 0 FAIL
node verify_pega_career_hub.mjs

# Regenerate this handoff bundle
node build_handoff_bundle.mjs
```

Last verified state: **40 PASS, 0 FAIL, exit 0** · 89 searchable tables · 1,776 rows ·
3 SHA-256 snapshot-integrity checks pass · generator confirmed idempotent.

(An earlier note in this project said "41 PASS". That was a miscount: the counting
command was case-insensitive and matched the word "pass" inside a prose summary line.
The verifier emits **40** assertions.)

### File inventory

| File | Size | Role |
|---|---|---|
| `gcc_rank_feasibility.mjs` | 8.6 KB | Stage 0 — measures evidence coverage per pillar BEFORE any scoring. This is what caught that 68 of 89 companies had zero parseable tenure. |
| `gcc_build_evidence.mjs` | 19.1 KB | Stage 1 — merges 3 sources (team_intelligence_enriched.json, hub audit rows, hub fresh-evidence rows) + the hand-verified supplement into one record per company. |
| `gcc_evidence_supplement.json` | 5.5 KB | Stage 1 input — hand-verified findings kept as auditable data instead of edited into scores. |
| `gcc_evidence_base.json` | 539.1 KB | Stage 1 output — the merged per-company evidence base. |
| `gcc_score_rubric.mjs` | 29.4 KB | Stage 2 — the 100-point scorer. All pillar logic lives here. |
| `gcc_ranking_scores.json` | 207.1 KB | Stage 2 output — the rankings, in the requested JSON schema. |
| `gcc_lifestyle_supplement.json` | 13.4 KB | Parallel layer — lifestyle evidence ledger. Deliberately unscored. |
| `gcc_explain_company.mjs` | 4.9 KB | Audit tool — shows exactly which people/strings produced each pillar score. |
| `build_gcc_ranking_section.mjs` | 18.9 KB | Renders both layers into the HTML hub. Idempotent. |
| `verify_pega_career_hub.mjs` | 10.6 KB | Verification gate — 40 checks incl. SHA-256 snapshot integrity, table/row preservation, search, responsive overflow, no-JS readability. |
| `build_handoff_bundle.mjs` | 45.6 KB | Generates this handoff bundle. |
| `Pega_Career_Intelligence_Hub.html` | 995.8 KB | The deliverable dashboard. Standalone, works over file://, no server or build. |

**Environment:** Node.js with Puppeteer (already present). Windows / PowerShell.
No build step, no web server — the hub is a standalone `file://` HTML document.
`git` is **not** installed in this workspace, so there is no diff history; rollback
relies on the `.pre-*`/`.backup-*` HTML snapshots, which are hash-protected.

---

## 11. Open work

1. **Fix defect 13** — apply the primary-location residency filter to the Pillar-4
   tenure sample in `gcc_build_evidence.mjs`. Harmless today (1/265 samples),
   but it will silently distort averages as soon as more people are added.
2. **Lifestyle research for the elite tier — Ford, Commonwealth Bank, Vodafone/VOIS.**
   The three strongest engineering options are the three with no lifestyle evidence.
   **Use official career/benefits pages only**; the Goldman free-meals case shows
   review-site aggregation is not safe to encode.
3. **Lift under-documented companies past the n≥3 tenure bar** by searching for
   *departed* engineers (the technique that resolved Cisco): Kotak, Broadridge,
   Orange, NAB, Schwab, Ameriprise, enGen, Siemens.
4. **Goldman Sachs needs one more verified Pega engineer** to get a real attrition
   grade. Do not substitute non-Pega engineers to reach the threshold.
5. **Reduce the 0.839 evidence-volume bias** by levelling research depth across
   companies — not by reweighting pillars, which would only hide it.

---

## 12. Instructions for a receiving LLM

If you are continuing this work:

1. **Do not present a flat 1–89 ranking.** The 0.839 correlation with evidence
   volume makes cross-tier comparison invalid. Always carry the confidence tier.
2. **Do not fill `NOT_RESEARCHED` or `UNVERIFIED` fields from general knowledge or
   reputation.** That is precisely the failure mode this ledger was built to avoid.
   An absent claim is not a negative signal.
3. **Do not lower the n≥3 tenure threshold** to make a company scoreable, and do not
   pad the sample with non-Pega engineers.
4. **Low tenure is not automatically burnout.** Check whether departure evidence
   actually outweighs join evidence before penalising.
5. **Location fields are untrustworthy.** Empty ≠ India. Check for parentheticals
   like `"Germany (ex-MBRDI Bengaluru)"` before inferring residency.
6. **Certification ≠ authority, and an in-progress certification is not a certification.**
   A CSSA is not an architect; a Business Process Analyst holding "Principal Consultant"
   is not architecture ownership; `LSA Part 1` / `CLSA-1` is **not** a completed LSA.
   Check for mid-track markers before counting someone as a certified architect.
7. **Every claim about a person or company is as-of 2026-10** and came from the
   public search index. Re-verify before anyone acts on it in an interview.
8. **Keep the two layers separate.** The 100-point engineering score rests on
   verifiable architecture and tenure evidence. The lifestyle ledger does not.
   Merging them into one number would launder the weaker evidence.
