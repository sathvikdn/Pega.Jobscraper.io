# Pega GCC Engineering Culture & Autonomy Ranking — Portable Handoff Bundle

> **This is a context-transfer document.** It is written to be pasted into another LLM so that model can continue, critique or extend this work without access to the original machine. Everything factual below is read directly from the frozen output files, not restated from memory.

| | |
|---|---|
| **Data as of** | 2026-10 (scores generated 2026-10-02T16:46:44.285Z) |
| **Bundle generated** | 2026-10-02T17:13:54.909Z |
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

### 3.4 Low-confidence tier — indicative only, DO NOT rank these against each other

These scores mostly measure research coverage. Treat them as "not yet assessed".

| # | Company | Score | P1 | P2 | P3 | P4 | Tenure | Attrition | Overall rank |
|--:|---|--:|--:|--:|--:|--:|---|---|--:|
| 1 | **enGen / Highmark India** | 60 | 30 | 30 | 0 | 0 | 2.33y (n=2) | Unknown | 20 |
| 2 | **GE HealthCare India** | 35 | 0 | 15 | 20 | 0 | 6.5y (n=1) | Unknown | 40 |
| 3 | **Kotak Mahindra Bank** | 35 | 15 | 10 | 10 | 0 | 1.33y (n=1) | Unknown | 42 |
| 4 | **Bosch** | 30 | 15 | 15 | 0 | 0 | 5.79y (n=2) | Unknown | 44 |
| 5 | **The Hartford India** | 30 | 15 | 15 | 0 | 0 | 0.25y (n=1) | Unknown | 45 |
| 6 | **Aflac** | 30 | 15 | 15 | 0 | 0 | 7.25y (n=1) | Unknown | 46 |
| 7 | **Mastercard** | 30 | 15 | 15 | 0 | 0 | 11y (n=2) | Unknown | 47 |
| 8 | **Elevance Health (Anthem)** | 30 | 15 | 15 | 0 | 0 | 3.08y (n=1) | Unknown | 48 |
| 9 | **Global Payments India** | 30 | 30 | 0 | 0 | 0 | no data | Unknown | 49 |
| 10 | **Orange Business India** | 25 | 15 | 10 | 0 | 0 | 2.08y (n=1) | Unknown | 53 |
| 11 | **Roche India** | 25 | 15 | 10 | 0 | 0 | 0.92y (n=2) | Unknown | 56 |
| 12 | **Pfizer India** | 25 | 15 | 10 | 0 | 0 | no data | Unknown | 57 |
| 13 | **Nike India** | 25 | 15 | 10 | 0 | 0 | no data | Unknown | 58 |
| 14 | **UBS India** | 20 | 15 | 5 | 0 | 0 | no data | Unknown | 61 |
| 15 | **PayPal** | 20 | 15 | -5 | 10 | 0 | 4.79y (n=2) | Unknown | 62 |
| 16 | **Deutsche Bank** | 20 | 15 | 5 | 0 | 0 | 4.58y (n=1) | Unknown | 63 |
| 17 | **MUFG** | 20 | 15 | 5 | 0 | 0 | 2y (n=1) | Unknown | 64 |
| 18 | **FIS (TSYS/Global Payments)** | 20 | 15 | 5 | 0 | 0 | 6.5y (n=2) | Unknown | 65 |
| 19 | **Mizuho Global Services India (MGS)** | 20 | 15 | 5 | 0 | 0 | no data | Unknown | 66 |
| 20 | **Daimler Truck India** | 15 | 15 | 0 | 0 | 0 | 4.83y (n=1) | Unknown | 67 |
| 21 | **Conduent** | 15 | 15 | 0 | 0 | 0 | no data | Unknown | 69 |
| 22 | **DHL** | 15 | 15 | 0 | 0 | 0 | 4.42y (n=1) | Unknown | 70 |
| 23 | **Dell Technologies** | 15 | 15 | 0 | 0 | 0 | no data | Unknown | 71 |
| 24 | **IFFCO Tokio General Insurance** | 15 | 15 | 0 | 0 | 0 | 6.17y (n=1) | Unknown | 72 |
| 25 | **Fidelity National Financial India** | 15 | 15 | 0 | 0 | 0 | 9.92y (n=1) | Unknown | 73 |
| 26 | **Renault-Nissan Tech India** | 15 | 15 | 0 | 0 | 0 | no data | Unknown | 74 |
| 27 | **Proximus India** | 15 | 15 | 0 | 0 | 0 | no data | Unknown | 75 |
| 28 | **Mondelez India** | 15 | 15 | 0 | 0 | 0 | no data | Unknown | 76 |
| 29 | **Marsh McLennan India (MMGS)** | 15 | 15 | 0 | 0 | 0 | no data | Unknown | 77 |
| 30 | **Levi Strauss & Co. India** | 15 | 15 | 0 | 0 | 0 | no data | Unknown | 78 |
| 31 | **Novartis India** | 15 | 15 | 0 | 0 | 0 | no data | Unknown | 79 |
| 32 | **ICICI Bank** | 0 | 0 | 0 | 0 | 0 | 10.33y (n=1) | Unknown | 80 |
| 33 | **Visa** | 0 | 0 | 0 | 0 | 0 | 11y (n=1) | Unknown | 81 |
| 34 | **Capital One India** | 0 | 0 | 0 | 0 | 0 | 9.75y (n=1) | Unknown | 82 |
| 35 | **Synchrony Financial** | 0 | 0 | 0 | 0 | 0 | no data | Unknown | 83 |
| 36 | **PepsiCo India** | 0 | 0 | 0 | 0 | 0 | no data | Unknown | 84 |
| 37 | **Fiserv** | 0 | 0 | 0 | 0 | 0 | 7.58y (n=2) | Unknown | 85 |
| 38 | **AXA India** | 0 | 0 | 0 | 0 | 0 | no data | Unknown | 86 |
| 39 | **Maersk GSC India** | 0 | 0 | 0 | 0 | 0 | no data | Unknown | 87 |
| 40 | **Cummins India** | 0 | 0 | 0 | 0 | 0 | no data | Unknown | 88 |
| 41 | **ITC Limited** | 0 | 0 | 0 | 0 | 0 | no data | Unknown | 89 |

### 3.5 Not scored

- **Unilever India (Digital Hub)** — INSUFFICIENT_EVIDENCE: No people evidence available; cannot assess.

---

## 4. Per-company detail (all 90)

Each block below is the complete scored record.

### 4.1 High confidence

#### Ford Motor Company — 100/100 (High confidence, overall rank 1)

- **Pillars:** P1 autonomy 30/30 · P2 modernity 30/30 · P3 innovation 20/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 3.19y (n=8) indicates a settled environment.
- **Leadership:** India holds top-level Pega authority: Abinaya Elavarasan — Technical Project Manager - FORD Pega CoE Lead. 1 engineer is mid-LSA track but hold no completed LSA/CLSA: Abinaya Elavarasan — LSA Part 1, CSSA, CSA.
- **Tech stack:** Constellation, CDH/Decisioning, OpenShift/K8s, Azure, GCP, GenAI/Agentic, Blueprint, REST/SOAP, Splunk/PDC
- **Evidence:** 9 people · 8 audit rows · tenure n=8 avg 3.19y · departures 0 · joins 0
- **Locations:** Chennai
- **Sector:** Automotive
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Top-level Pega/architecture authority sits in India
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Conference / award visibility: PegaInnovate
  - Community / build-in-public visibility: bootcamp, published
  - Stable team: average Pega tenure 3.19y across 8 engineers
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Senior-most Pega credential evidenced in India is an in-progress LSA, not a completed one

#### Commonwealth Bank — 85/100 (High confidence, overall rank 2)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 30/30 · P3 innovation 20/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 3.11y (n=10) indicates a settled environment.
- **Leadership:** India has a senior Pega ladder of 9 (0 by architect/lead title, 9 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Akhil Chakka — PEGA Senior Developer - CSA, CSSA; Anjana A — Senior Software Engineer - 10yr Pega veteran; Deep Shikha — Senior Software Engineer - CSA, CSSA, PCDC. Excluded 1 departed roster entry from this assessment: Premkumar Ganesan — DEPARTED - CLSA, Pega CoE Lead.
- **Tech stack:** Kafka/event-driven, CDH/Decisioning, AWS, GCP, GenAI/Agentic, REST/SOAP, JMS/MQ, Pega Cloud
- **Evidence:** 10 people · 4 audit rows · tenure n=10 avg 3.11y · departures 1 · joins 5
- **Locations:** Bengaluru
- **Sector:** Banking
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Conference / award visibility: PegaInnovate
  - Community / build-in-public visibility: Pega forum
  - Stable team: average Pega tenure 3.11y across 10 engineers
  - 3 ex-Pegasystems hires — imports product-level platform depth
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - 1 senior/lead roster entry evidenced as departed

#### Vodafone / VOIS — 85/100 (High confidence, overall rank 3)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 30/30 · P3 innovation 20/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 3.46y (n=8) indicates a settled environment.
- **Leadership:** Leadership evidenced in profile text near an India location, but no India-located senior roster entry confirms global ownership.
- **Tech stack:** Kafka/event-driven, Constellation, React, CDH/Decisioning, AWS
- **Evidence:** 7 people · 4 audit rows · tenure n=8 avg 3.46y · departures 0 · joins 2
- **Locations:** Pune, Bengaluru
- **Sector:** Telecom
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Architect ladder present in India (2 completed LSA/CLSA holders: Ganesh Mahagaonkar, Praveen Kesari)
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Conference / award visibility: PegaFest
  - Community / build-in-public visibility: hackathon
  - Stable team: average Pega tenure 3.46y across 8 engineers

#### Sun Life — 80/100 (High confidence, overall rank 4)

- **Pillars:** P1 autonomy 30/30 · P2 modernity 10/30 · P3 innovation 20/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 3.25y (n=10) indicates a settled environment.
- **Leadership:** India holds top-level Pega authority: Swarup Mohanty — Principal Solution Architect.
- **Tech stack:** Constellation, React, GenAI/Agentic, REST/SOAP
- **Evidence:** 8 people · 7 audit rows · tenure n=10 avg 3.25y · departures 0 · joins 8
- **Locations:** Gurugram
- **Sector:** Insurance
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Top-level Pega/architecture authority sits in India
  - Architect ladder present in India (1 completed LSA/CLSA holder: Pushkar Raj)
  - Constellation / React / custom-Java modernisation evidenced
  - Conference / award visibility: PegaWorld
  - Community / build-in-public visibility: community
  - Stable team: average Pega tenure 3.25y across 10 engineers

#### JPMorgan Chase — 75/100 (High confidence, overall rank 5)

- **Pillars:** P1 autonomy 30/30 · P2 modernity 30/30 · P3 innovation 10/20 · P4 attrition 5/20
- **Attrition:** Medium — Average tenure 2.94y (n=13) — mid-range; neither clearly stable nor clearly churning.
- **Leadership:** India holds top-level Pega authority: Ashish Agrawal — Executive Director.
- **Tech stack:** React, CDH/Decisioning, SWIFT/ISO 20022, AWS, GenAI/Agentic, Blueprint, REST/SOAP, JMS/MQ, Pega Cloud
- **Evidence:** 9 people · 13 audit rows · tenure n=13 avg 2.94y · departures 2 · joins 6
- **Locations:** Hyderabad, Bengaluru, Mumbai
- **Sector:** Banking
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Top-level Pega/architecture authority sits in India
  - Architect ladder present in India (1 completed LSA/CLSA holder: Ashish Agrawal)
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Conference / award visibility: PegaInnovate, Pega Day

#### Wells Fargo — 75/100 (High confidence, overall rank 6)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 30/30 · P3 innovation 10/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 4.32y (n=14) indicates a settled environment.
- **Leadership:** India has a senior Pega ladder of 12 (8 by architect/lead title, 4 by certification only; 4 hold a completed LSA/CLSA), but no evidenced global owner in India: Raja Reddy Bommana — VP, Lead Software Engineer; Rajesh Manem — VP, Pega Lead System Architect; Ram Epuri — VP, Pega Architect.
- **Tech stack:** Constellation, DX API, React, CDH/Decisioning, SWIFT/ISO 20022, GenAI/Agentic
- **Evidence:** 12 people · 5 audit rows · tenure n=14 avg 4.32y · departures 1 · joins 0
- **Locations:** Hyderabad, Bengaluru
- **Sector:** Banking
- **Hiring status:** Actively Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Architect ladder present in India (4 completed LSA/CLSA holders: Raja Reddy Bommana, Rajesh Manem, Ram Epuri)
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Conference / award visibility: PegaInnovate
  - Stable team: average Pega tenure 4.32y across 14 engineers

#### Barclays — 75/100 (High confidence, overall rank 8)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 20/30 · P3 innovation 20/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 3.96y (n=9) indicates a settled environment.
- **Leadership:** India has a senior Pega ladder of 9 (5 by architect/lead title, 4 by certification only; 2 hold a completed LSA/CLSA), but no evidenced global owner in India: Abheek Chattopadhyay — AVP - Pega Tech Lead; Girish Gaikwad — AVP - Pega Lead; Harshad Mankar — AVP - Development Lead.
- **Tech stack:** Kafka/event-driven, CDH/Decisioning, SWIFT/ISO 20022, AWS, REST/SOAP, JMS/MQ
- **Evidence:** 10 people · 4 audit rows · tenure n=9 avg 3.96y · departures 0 · joins 4
- **Locations:** Pune
- **Sector:** Banking
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Architect ladder present in India (2 completed LSA/CLSA holders: Girish Gaikwad, Harshad Mankar)
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Conference / award visibility: PegaInnovate
  - Community / build-in-public visibility: community, badge
  - Stable team: average Pega tenure 3.96y across 9 engineers

#### Stellantis — 75/100 (High confidence, overall rank 9)

- **Pillars:** P1 autonomy 30/30 · P2 modernity 5/30 · P3 innovation 20/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 3.87y (n=7) indicates a settled environment.
- **Leadership:** India holds top-level Pega authority: Kishore Kumar Panathula — Head Pega CoE, ICT India; Sudhir K Chavan — Pega COE Lead System Architect.
- **Tech stack:** CDH/Decisioning, AWS, REST/SOAP
- **Evidence:** 8 people · 6 audit rows · tenure n=7 avg 3.87y · departures 0 · joins 2
- **Locations:** Hyderabad
- **Sector:** Automotive
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Top-level Pega/architecture authority sits in India
  - Architect ladder present in India (1 completed LSA/CLSA holder: Kishore Kumar Panathula)
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Conference / award visibility: PegaInnovate
  - Community / build-in-public visibility: hackathon
  - Stable team: average Pega tenure 3.87y across 7 engineers

#### Citibank — 75/100 (High confidence, overall rank 10)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 30/30 · P3 innovation 10/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 3.45y (n=5) indicates a settled environment.
- **Leadership:** India has a senior Pega ladder of 6 (4 by architect/lead title, 2 by certification only; 1 hold a completed LSA/CLSA), but no evidenced global owner in India: Akash Pratap — Vice President - Pega Lead System Architect; Rajesh Kumar Vijayakumar — SVP, Pega Lead Architect; Senthilkumar Sivashanmugam — VP - Tech Lead, Lead Pega Architect.
- **Tech stack:** Kafka/event-driven, Constellation, CDH/Decisioning, SWIFT/ISO 20022, OpenShift/K8s, GenAI/Agentic, REST/SOAP, JMS/MQ
- **Evidence:** 7 people · 4 audit rows · tenure n=5 avg 3.45y · departures 0 · joins 3
- **Locations:** Chennai, Mumbai
- **Sector:** Banking
- **Hiring status:** Actively Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Architect ladder present in India (1 completed LSA/CLSA holder: Akash Pratap)
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Community / build-in-public visibility: hackathon
  - Stable team: average Pega tenure 3.45y across 5 engineers

#### NatWest Group — 75/100 (High confidence, overall rank 11)

- **Pillars:** P1 autonomy 30/30 · P2 modernity 15/30 · P3 innovation 10/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 3.3y (n=5) indicates a settled environment.
- **Leadership:** India holds top-level Pega authority: Ramani Jeyachandrasekar — Director - Engineering Lead Pega CDH. 1 engineer is mid-LSA track but hold no completed LSA/CLSA: Prasad S — CLSA-1, CSSA, CPDC, CSA. Excluded 1 departed roster entry from this assessment: Karan Rajput — DEPARTED - Now SVP Domain Architect at NAB \| Lead Architect - Customer Decisioning.
- **Tech stack:** Constellation, CDH/Decisioning, Azure, Pega Cloud, Splunk/PDC
- **Evidence:** 6 people · 4 audit rows · tenure n=5 avg 3.3y · departures 1 · joins 4
- **Locations:** Bengaluru, Gurugram
- **Sector:** Banking
- **Hiring status:** Actively Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Top-level Pega/architecture authority sits in India
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Conference / award visibility: PegaWorld
  - Stable team: average Pega tenure 3.3y across 5 engineers
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Senior-most Pega credential evidenced in India is an in-progress LSA, not a completed one
  - 1 senior/lead roster entry evidenced as departed

#### HSBC — 70/100 (High confidence, overall rank 12)

- **Pillars:** P1 autonomy 30/30 · P2 modernity 20/30 · P3 innovation 0/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 3.22y (n=8) indicates a settled environment.
- **Leadership:** Unambiguous India-based Pega ownership evidenced in research text: "...Bengaluru platform Checked 22 Sept 2026 HSBC Global Head of Pega & Cloud Platform...".
- **Tech stack:** Kafka/event-driven, CDH/Decisioning, SWIFT/ISO 20022, GCP, REST/SOAP, Pega Cloud, Splunk/PDC
- **Evidence:** 7 people · 11 audit rows · tenure n=8 avg 3.22y · departures 2 · joins 3
- **Locations:** Pune, Hyderabad, Bengaluru, Kolkata
- **Sector:** Banking
- **Hiring status:** Actively Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - India-based global Pega/platform owner evidenced in research findings
  - Architect ladder present in India (1 completed LSA/CLSA holder: Punit Sharma)
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Stable team: average Pega tenure 3.22y across 8 engineers

#### Siemens — 65/100 (High confidence, overall rank 14)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 10/30 · P3 innovation 20/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 5.08y (n=5) indicates a settled environment.
- **Leadership:** India has a senior Pega ladder of 6 (2 by architect/lead title, 4 by certification only; 1 hold a completed LSA/CLSA), but no evidenced global owner in India: Renuka Deshpande — Lead System Architect - CSSA, CSA; Saheli Misra — Solutions Architect - CLSA, 11yr BPM; Amit Abhishek — Lead Pega Developer.
- **Tech stack:** Constellation, REST/SOAP
- **Evidence:** 7 people · 7 audit rows · tenure n=5 avg 5.08y · departures 0 · joins 1
- **Locations:** Bengaluru, Pune, Mumbai
- **Sector:** Industrial
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Architect ladder present in India (1 completed LSA/CLSA holder: Amit Abhishek)
  - Constellation / React / custom-Java modernisation evidenced
  - Conference / award visibility: PegaWorld, case study
  - Community / build-in-public visibility: Pega forum
  - Stable team: average Pega tenure 5.08y across 5 engineers
  - 2 ex-Pegasystems hires — imports product-level platform depth

#### John Deere India (JDTCI) — 65/100 (High confidence, overall rank 15)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 30/30 · P3 innovation 0/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 5.49y (n=6) indicates a settled environment.
- **Leadership:** India has a senior Pega ladder of 4 (2 by architect/lead title, 2 by certification only; 1 hold a completed LSA/CLSA), but no evidenced global owner in India: Rahul Chaher — AGM Software Engineering - CLSA, 12.5yr Pega; Manan Awasthi — Senior Lead Software Engineer - CSSA; Shailendra Mishra — Lead Software Engineer - Full Stack + GenAI. Excluded 1 departed roster entry from this assessment: Sarvesh Kumar — DEPARTED Apr 2026 - ex-Lead SE II, Collections.
- **Tech stack:** Kafka/event-driven, Constellation, React, CDH/Decisioning, AWS, GenAI/Agentic, REST/SOAP, JMS/MQ, Pega Cloud
- **Evidence:** 5 people · 9 audit rows · tenure n=6 avg 5.49y · departures 1 · joins 0
- **Locations:** Pune, Bengaluru
- **Sector:** Manufacturing
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Architect ladder present in India (1 completed LSA/CLSA holder: Rahul Chaher)
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Stable team: average Pega tenure 5.49y across 6 engineers
- **Red flags:**
  - 1 senior/lead roster entry evidenced as departed

#### BT Group — 65/100 (High confidence, overall rank 16)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 30/30 · P3 innovation 0/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 3.77y (n=4) indicates a settled environment.
- **Leadership:** India has a senior Pega ladder of 6 (2 by architect/lead title, 4 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Praveen Kumar — Lead Pega Decisioning Consultant - PCLSA; Manjunatha A — Software Engineering Practitioner (Tech Lead); Bindhu Gunuru — Senior Pega Developer - CSA, CSSA. 1 completed LSA/CLSA holder found but with no verified India location, so it cannot evidence an India ladder: Praveen Kumar — PCLSA.
- **Tech stack:** Constellation, CDH/Decisioning, GenAI/Agentic, Blueprint, REST/SOAP, JMS/MQ, Splunk/PDC
- **Evidence:** 7 people · 3 audit rows · tenure n=4 avg 3.77y · departures 0 · joins 0
- **Locations:** Bengaluru, Hyderabad
- **Sector:** Telecom
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Stable team: average Pega tenure 3.77y across 4 engineers
  - 4 ex-Pegasystems hires — imports product-level platform depth
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Completed LSA/CLSA found, but India residency unverified

#### Optum / UnitedHealth Group — 60/100 (High confidence, overall rank 19)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 15/30 · P3 innovation 10/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 5.99y (n=6) indicates a settled environment.
- **Leadership:** India has a senior Pega ladder of 6 (0 by architect/lead title, 6 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Yugandhar Dasari — Software Engineering Lead; Manoj Kumar Undralla — Senior Software Engineer - Constellation + GenAI; Pankaj Singh — Senior Software Engineer.
- **Tech stack:** Constellation, CDH/Decisioning, GenAI/Agentic, REST/SOAP, Splunk/PDC
- **Evidence:** 7 people · 3 audit rows · tenure n=6 avg 5.99y · departures 0 · joins 0
- **Locations:** Hyderabad
- **Sector:** Healthcare
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Conference / award visibility: PegaInnovate
  - Stable team: average Pega tenure 5.99y across 6 engineers
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample

#### Standard Chartered — 50/100 (High confidence, overall rank 22)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 5/30 · P3 innovation 10/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 4.92y (n=9) indicates a settled environment.
- **Leadership:** Leadership evidenced in profile text near an India location, but no India-located senior roster entry confirms global ownership. 1 engineer is mid-LSA track but hold no completed LSA/CLSA: Krishnan Govindaprasad — CLSA Part 1, CSSA, CSA.
- **Tech stack:** CDH/Decisioning, OpenShift/K8s, REST/SOAP
- **Evidence:** 7 people · 8 audit rows · tenure n=9 avg 4.92y · departures 0 · joins 2
- **Locations:** Chennai, Bengaluru
- **Sector:** Banking
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Community / build-in-public visibility: hackathon
  - Stable team: average Pega tenure 4.92y across 9 engineers
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Senior-most Pega credential evidenced in India is an in-progress LSA, not a completed one

#### Bank of America — 50/100 (High confidence, overall rank 24)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 15/30 · P3 innovation 0/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 4.75y (n=8) indicates a settled environment.
- **Leadership:** Leadership evidenced in profile text near an India location, but no India-located senior roster entry confirms global ownership.
- **Tech stack:** Constellation, AWS, REST/SOAP
- **Evidence:** 9 people · 2 audit rows · tenure n=8 avg 4.75y · departures 0 · joins 0
- **Locations:** Hyderabad, Gurugram
- **Sector:** Banking
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Architect ladder present in India (1 completed LSA/CLSA holder: Rajendra Dubey)
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Stable team: average Pega tenure 4.75y across 8 engineers

#### Empower — 50/100 (High confidence, overall rank 25)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 15/30 · P3 innovation 0/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 5.47y (n=3) indicates a settled environment.
- **Leadership:** India has a senior Pega ladder of 6 (0 by architect/lead title, 6 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: AnandBabu Edagotti — Senior Pega Developer; Divya Mohanraj — Senior Software Engineer; Mithun Padmanabhan — Senior Software Developer.
- **Tech stack:** CDH/Decisioning, AWS, GenAI/Agentic, Splunk/PDC
- **Evidence:** 7 people · 4 audit rows · tenure n=3 avg 5.47y · departures 0 · joins 1
- **Locations:** Bengaluru
- **Sector:** Financial Services
- **Hiring status:** Rapidly Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Stable team: average Pega tenure 5.47y across 3 engineers
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample

#### Allianz Technology — 50/100 (High confidence, overall rank 26)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 15/30 · P3 innovation 0/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 7.28y (n=3) indicates a settled environment.
- **Leadership:** India has a senior Pega ladder of 5 (3 by architect/lead title, 2 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Anju Murali — Senior Technical Architect; Nitin Kumar — Pega Senior System Architect; Shery Alphonsa George — Technical Lead.
- **Tech stack:** Constellation, CDH/Decisioning, AWS
- **Evidence:** 7 people · 3 audit rows · tenure n=3 avg 7.28y · departures 0 · joins 0
- **Locations:** Trivandrum, Pune
- **Sector:** Insurance
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Stable team: average Pega tenure 7.28y across 3 engineers
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample

#### Verizon — 50/100 (High confidence, overall rank 27)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 15/30 · P3 innovation 0/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 3.52y (n=8) indicates a settled environment.
- **Leadership:** Leadership evidenced in profile text near an India location, but no India-located senior roster entry confirms global ownership. 1 engineer is mid-LSA track but hold no completed LSA/CLSA: Harika Yadavalli — LSA Part 1, CSSA, CPBA, CPDC.
- **Tech stack:** CDH/Decisioning, GenAI/Agentic, REST/SOAP
- **Evidence:** 6 people · 3 audit rows · tenure n=8 avg 3.52y · departures 0 · joins 2
- **Locations:** Hyderabad, Bengaluru, Chennai
- **Sector:** Telecom
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Stable team: average Pega tenure 3.52y across 8 engineers
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Senior-most Pega credential evidenced in India is an in-progress LSA, not a completed one

#### American Express — 45/100 (High confidence, overall rank 30)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 15/30 · P3 innovation 10/20 · P4 attrition 5/20
- **Attrition:** Medium — Average tenure 2.08y (n=7) — mid-range; neither clearly stable nor clearly churning.
- **Leadership:** India has a senior Pega ladder of 9 (0 by architect/lead title, 9 by certification only; 1 hold a completed LSA/CLSA), but no evidenced global owner in India: Himanshu Rajput — Software Engineer II - LSA-1, CSSA, CPDC, CPBA; Karthik Gandham — Pega Solutions Architect; Amit Singh Sachan — Software Engineer III - 10yr Pega exp.
- **Tech stack:** Constellation, DX API, CDH/Decisioning, AWS, Azure, GenAI/Agentic, REST/SOAP
- **Evidence:** 9 people · 5 audit rows · tenure n=7 avg 2.08y · departures 0 · joins 0
- **Locations:** Gurugram
- **Sector:** Banking
- **Hiring status:** Actively Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Architect ladder present in India (1 completed LSA/CLSA holder: Rahul Kumar)
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Community / build-in-public visibility: evidenced

#### Lloyds Banking Group — 45/100 (High confidence, overall rank 32)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 15/30 · P3 innovation 10/20 · P4 attrition 5/20
- **Attrition:** Medium — Average tenure 1.69y (n=4) — mid-range; neither clearly stable nor clearly churning.
- **Leadership:** India has a senior Pega ladder of 7 (0 by architect/lead title, 7 by certification only; 3 hold a completed LSA/CLSA), but no evidenced global owner in India: Sangram Keshari Nayak — Solutions Architect; Srinivas Yalagala — Pega CLSA; Vijay Mahesh Bobba — Sr. Technical Application Specialist / LSA.
- **Tech stack:** Constellation, CDH/Decisioning
- **Evidence:** 7 people · 2 audit rows · tenure n=4 avg 1.69y · departures 0 · joins 2
- **Locations:** Hyderabad
- **Sector:** Banking
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Architect ladder present in India (3 completed LSA/CLSA holders: Srinivas Yalagala, Vijay Mahesh Bobba, Rammohan Tattikota)
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Conference / award visibility: PegaWorld

#### Evernorth / Cigna — 35/100 (High confidence, overall rank 35)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 15/30 · P3 innovation 0/20 · P4 attrition 5/20
- **Attrition:** Medium — Average tenure 1.8y (n=5) — mid-range; neither clearly stable nor clearly churning.
- **Leadership:** India has a senior Pega ladder of 7 (1 by architect/lead title, 6 by certification only; 1 hold a completed LSA/CLSA), but no evidenced global owner in India: Jahnavi Paladara — Application Development Advisor / Pega Architect; Ravi Krishna Ladi — Software Engineering Lead Analyst; Vijay Reddy — Software Engineering Lead Analyst - CSA,CSSA,CPDC,CPBA.
- **Tech stack:** AWS, Azure, GenAI/Agentic, REST/SOAP
- **Evidence:** 7 people · 6 audit rows · tenure n=5 avg 1.8y · departures 0 · joins 4
- **Locations:** Hyderabad
- **Sector:** Healthcare
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Architect ladder present in India (1 completed LSA/CLSA holder: Subbarao Tatikonda)
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)

#### MetLife India GCC — 35/100 (High confidence, overall rank 36)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 15/30 · P3 innovation 0/20 · P4 attrition 5/20
- **Attrition:** Medium — Average tenure 1.68y (n=6) — mid-range; neither clearly stable nor clearly churning.
- **Leadership:** India has a senior Pega ladder of 6 (1 by architect/lead title, 5 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Srikanth Amma — Lead Software Engineer - 9yr+ Pega; Mahesh Nair — Specialist - Pega Constellation; Poorvi Jayant — Pega Developer/Specialist.
- **Tech stack:** Constellation, AWS, REST/SOAP, Pega Cloud
- **Evidence:** 7 people · 2 audit rows · tenure n=6 avg 1.68y · departures 0 · joins 6
- **Locations:** Noida, Hyderabad
- **Sector:** Insurance
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample

#### First Citizens India — 35/100 (High confidence, overall rank 37)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 15/30 · P3 innovation 0/20 · P4 attrition 5/20
- **Attrition:** Medium — Average tenure 1.17y (n=6) is low, but join signals outweigh departures — reads as recent hiring/intern conversion, not churn. Not penalised.
- **Leadership:** India has a senior Pega ladder of 3 (2 by architect/lead title, 1 by certification only; 1 hold a completed LSA/CLSA), but no evidenced global owner in India: Nimalan Peter — Lead SE / Certified Pega Robotics System Architect; Deepak Shahi — Principal Engineer - Pega CLSA, ex-Pegasystems; Harika Ch — Developer 3 - CSSA, CPDC, ex-Pegasystems.
- **Tech stack:** Kafka/event-driven, CDH/Decisioning, REST/SOAP
- **Evidence:** 5 people · 4 audit rows · tenure n=6 avg 1.17y · departures 0 · joins 7
- **Locations:** Bengaluru
- **Sector:** Banking
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Architect ladder present in India (1 completed LSA/CLSA holder: Deepak Shahi)
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Short tenure is growth-driven, not attrition: 7 join signal(s) vs 0 departure signal(s)
  - 8 ex-Pegasystems hires — imports product-level platform depth

### 4.2 Medium confidence

#### Mercedes-Benz R&D India (MBRDI) — 75/100 (Medium confidence, overall rank 7)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 30/30 · P3 innovation 10/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 4.25y (n=9) indicates a settled environment.
- **Leadership:** India has a senior Pega ladder of 8 (4 by architect/lead title, 4 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Manomit Das — Program Manager - Pega Team Lead (AAP Markets); Bhanu Prasad V — Solutions Architect - Pega Architect; Moumita Dasgupta — Manager / Principal Consultant - Pega PRPC Senior Architect. Excluded 2 departed roster entries from this assessment: Eshwar M H — DEPARTED Jul 2026 - AWS DevOps (via vendor); Mithun R — DEPARTED Jun 2026 - Now at Inadev.
- **Tech stack:** Kafka/event-driven, Constellation, CDH/Decisioning, AWS, Azure, Blueprint, REST/SOAP, Splunk/PDC
- **Evidence:** 11 people · 4 audit rows · tenure n=9 avg 4.25y · departures 2 · joins 0
- **Locations:** Bengaluru, Pune
- **Sector:** Automotive
- **Hiring status:** Actively Growing
- **Sources merged:** team_intelligence, hub_audit
- **Green flags:**
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Conference / award visibility: evidenced
  - Stable team: average Pega tenure 4.25y across 9 engineers
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - 2 senior/lead roster entries evidenced as departed

#### Carelon Global Solutions India — 70/100 (Medium confidence, overall rank 13)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 25/30 · P3 innovation 10/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 3.53y (n=3) indicates a settled environment.
- **Leadership:** India has a senior Pega ladder of 12 (2 by architect/lead title, 10 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: SAI Praneeth Patel — Pega Developer / Senior System Architect; Jasjeet Singh — Pega Tech Lead; AKASH ANAND — Senior SE. 1 engineer is mid-LSA track but hold no completed LSA/CLSA: AKASH ANAND — CLSA-1,PCDS,CSSA,CPDC.
- **Tech stack:** Kafka/event-driven, CDH/Decisioning, REST/SOAP
- **Evidence:** 13 people · 5 audit rows · tenure n=3 avg 3.53y · departures 0 · joins 2
- **Locations:** Hyderabad, Gurugram, Bengaluru
- **Sector:** Healthcare
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit
- **Green flags:**
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Constellation / React / custom-Java modernisation evidenced
  - Community / build-in-public visibility: hackathon
  - Stable team: average Pega tenure 3.53y across 3 engineers
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Senior-most Pega credential evidenced in India is an in-progress LSA, not a completed one

#### Nokia India — 65/100 (Medium confidence, overall rank 17)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 30/30 · P3 innovation 0/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 4.39y (n=7) indicates a settled environment.
- **Leadership:** India has a senior Pega ladder of 3 (2 by architect/lead title, 1 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Sirisha Pullagura — Pega System Architect - New hire May 2025; Vivek Kumar — Technical Lead / Pega System Architect - CLSA-1; Somesh Rayapati — Pega Developer - CSSA, CSA. 1 engineer is mid-LSA track but hold no completed LSA/CLSA: Vivek Kumar — CLSA Part 1, CPDC, CSSA, CSA.
- **Tech stack:** Kafka/event-driven, Constellation, React, CDH/Decisioning, Azure, GenAI/Agentic, REST/SOAP
- **Evidence:** 4 people · 6 audit rows · tenure n=7 avg 4.39y · departures 0 · joins 0
- **Locations:** Bengaluru
- **Sector:** Telecom
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Stable team: average Pega tenure 4.39y across 7 engineers
  - 2 ex-Pegasystems hires — imports product-level platform depth
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Senior-most Pega credential evidenced in India is an in-progress LSA, not a completed one

#### Cisco India — 65/100 (Medium confidence, overall rank 18)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 30/30 · P3 innovation 0/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 3.86y (n=3) indicates a settled environment.
- **Leadership:** India has a senior Pega ladder of 2 (0 by architect/lead title, 2 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Mounika Reddy — Senior Pega Developer / Architect - CSSA; Sahitya Srinivasan — Software Engineer - CSSA.
- **Tech stack:** Kafka/event-driven, CDH/Decisioning, OpenShift/K8s, GenAI/Agentic, REST/SOAP
- **Evidence:** 4 people · 5 audit rows · tenure n=3 avg 3.86y · departures 3 · joins 1
- **Locations:** Bengaluru
- **Sector:** Technology
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence, verified_supplement
- **Green flags:**
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Stable team: average Pega tenure 3.86y across 3 engineers
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - 3 separate departure signals found in evidence

#### BNP Paribas — 55/100 (Medium confidence, overall rank 21)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 20/30 · P3 innovation 20/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 4 (1 by architect/lead title, 3 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Senthil Kannan Jayabalan — Vice President / Delivery Manager; Arul Mano — Technical Lead / Asst. Manager; Beniz Xavier — Pega Developer. 1 engineer is mid-LSA track but hold no completed LSA/CLSA: Arul Mano — LSA Part 1, CSSA.
- **Tech stack:** SWIFT/ISO 20022, REST/SOAP, Splunk/PDC
- **Evidence:** 4 people · 2 audit rows · tenure n=1 avg 8.17y · departures 0 · joins 0
- **Locations:** Chennai
- **Sector:** Banking
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Conference / award visibility: PegaInnovate
  - Community / build-in-public visibility: Pega forum
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Senior-most Pega credential evidenced in India is an in-progress LSA, not a completed one
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified

#### Pegasystems India — 50/100 (Medium confidence, overall rank 23)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 15/30 · P3 innovation 0/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 3.5y (n=3) indicates a settled environment.
- **Leadership:** Leadership evidenced in profile text near an India location, but no India-located senior roster entry confirms global ownership.
- **Tech stack:** Constellation, React, CDH/Decisioning, GenAI/Agentic, Blueprint, Pega Cloud
- **Evidence:** 6 people · 7 audit rows · tenure n=3 avg 3.5y · departures 0 · joins 0
- **Locations:** Hyderabad, Bengaluru
- **Sector:** Platform Vendor
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit
- **Green flags:**
  - Architect ladder present in India (2 completed LSA/CLSA holders: Vivek Kumar Sonu, Yesuraju Chokka)
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Stable team: average Pega tenure 3.5y across 3 engineers

#### Morgan Stanley — 50/100 (Medium confidence, overall rank 28)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 15/30 · P3 innovation 0/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 4.06y (n=3) indicates a settled environment.
- **Leadership:** India has a senior Pega ladder of 3 (1 by architect/lead title, 2 by certification only; 1 hold a completed LSA/CLSA), but no evidenced global owner in India: Abhinav Anand — CLSA / Power Platform Consultant; Rahul K — Senior Manager / Sr. Pega System Arch.; Snehasis Panda — Senior Pega Developer.
- **Tech stack:** Constellation, REST/SOAP, Splunk/PDC
- **Evidence:** 3 people · 5 audit rows · tenure n=3 avg 4.06y · departures 0 · joins 1
- **Locations:** Bengaluru, Pune
- **Sector:** Banking
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Architect ladder present in India (1 completed LSA/CLSA holder: Abhinav Anand)
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Stable team: average Pega tenure 4.06y across 3 engineers

#### S&P Global — 50/100 (Medium confidence, overall rank 29)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 5/30 · P3 innovation 10/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 7.5y (n=3) indicates a settled environment.
- **Leadership:** India has a senior Pega ladder of 2 (1 by architect/lead title, 1 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Souritra Ganguly — Lead Software Engineer; Swathi Veldi — Lead System Engineer.
- **Tech stack:** Azure, Splunk/PDC
- **Evidence:** 3 people · 3 audit rows · tenure n=3 avg 7.5y · departures 0 · joins 0
- **Locations:** Hyderabad
- **Sector:** Financial Services
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Community / build-in-public visibility: blog
  - Stable team: average Pega tenure 7.5y across 3 engineers
  - 2 ex-Pegasystems hires — imports product-level platform depth
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample

#### Booking Holdings India — 45/100 (Medium confidence, overall rank 31)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 10/30 · P3 innovation 20/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 2 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 4 (4 by architect/lead title, 0 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Navya Chatrati — Pega Senior System Architect - Constellation; Pavithra Namboodiri — Pega System Architect - CSA, CSSA; Yamini G N — Pega System Architect - CSA, CSSA.
- **Tech stack:** Constellation, CDH/Decisioning, GenAI/Agentic, REST/SOAP
- **Evidence:** 6 people · 7 audit rows · tenure n=2 avg 1.42y · departures 0 · joins 4
- **Locations:** Bengaluru
- **Sector:** Travel/Technology
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence, verified_supplement
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
  - Conference / award visibility: PegaWorld, Pega Day, Impact Award, keynote
  - Community / build-in-public visibility: Pega forum, hackathon
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 2 dated engineer record(s)) — stability unverified

#### Goldman Sachs — 45/100 (Medium confidence, overall rank 33)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 10/30 · P3 innovation 20/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 2 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 3 (0 by architect/lead title, 3 by certification only; 3 hold a completed LSA/CLSA), but no evidenced global owner in India: MAYANK VISHWAKARMA — Vice President - Pega CLSA; Pavan Kumar Raavi — VP - Collections & Recoveries; Priyabharathi Ayyaswamy — VP - Pega Developer.
- **Tech stack:** Constellation, DX API, CDH/Decisioning, GenAI/Agentic, REST/SOAP
- **Evidence:** 4 people · 3 audit rows · tenure n=2 avg 6.08y · departures 0 · joins 1
- **Locations:** Bengaluru, Hyderabad
- **Sector:** Banking
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence, verified_supplement
- **Green flags:**
  - Architect ladder present in India (3 completed LSA/CLSA holders: MAYANK VISHWAKARMA, Pavan Kumar Raavi, Priyabharathi Ayyaswamy)
  - Constellation / React / custom-Java modernisation evidenced
  - Conference / award visibility: PegaInnovate
  - Community / build-in-public visibility: community
  - 5 ex-Pegasystems hires — imports product-level platform depth
- **Red flags:**
  - Tenure/attrition unmeasured (only 2 dated engineer record(s)) — stability unverified

#### Rabobank — 40/100 (Medium confidence, overall rank 34)

- **Pillars:** P1 autonomy 0/30 · P2 modernity 30/30 · P3 innovation 10/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** No title evidence strong enough to locate architectural ownership.
- **Tech stack:** Constellation, Azure, GenAI/Agentic
- **Evidence:** 5 people · 2 audit rows · tenure n=1 avg 2.92y · departures 0 · joins 0
- **Sector:** Banking
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit
- **Green flags:**
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Conference / award visibility: Pega Day
- **Red flags:**
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified

#### Shell India — 35/100 (Medium confidence, overall rank 38)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 20/20
- **Attrition:** Low — Average tenure 4.92y (n=3) indicates a settled environment.
- **Leadership:** India has a senior Pega ladder of 3 (1 by architect/lead title, 2 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Deepak Ojha — Software Engineer - Pega CSSA, CPDC, CRSA; Bhawna Garg — Pega Consultant / Senior System Architect - ex-Pegasystems; Kanti Dwivedi — Senior SE / COE Platform Lead - ex-Pegasystems.
- **Tech stack:** REST/SOAP
- **Evidence:** 5 people · 4 audit rows · tenure n=3 avg 4.92y · departures 0 · joins 0
- **Locations:** Bengaluru
- **Sector:** Energy
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit
- **Green flags:**
  - Stable team: average Pega tenure 4.92y across 3 engineers
  - 3 ex-Pegasystems hires — imports product-level platform depth
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample

#### Societe Generale — 35/100 (Medium confidence, overall rank 39)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 10/30 · P3 innovation 10/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 2 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 6 (4 by architect/lead title, 2 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Rekha B.N — Lead Software Engineer - 11yr IT, 8yr PRPC; Subramanyam Kolipakula — Lead Pega Developer (SSA); Sudhir Sharma — Lead Software Engineer / Pega Tech Lead.
- **Tech stack:** Constellation, React
- **Evidence:** 6 people · 2 audit rows · tenure n=2 avg 8.21y · departures 0 · joins 0
- **Locations:** Bengaluru
- **Sector:** Banking
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
  - Community / build-in-public visibility: Pega forum
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 2 dated engineer record(s)) — stability unverified

#### ANZ Bank — 35/100 (Medium confidence, overall rank 41)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 20/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 4 (1 by architect/lead title, 3 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Srikanth Gaddamanugu — Pega Lead System Architect; Abhigna Lahiri Jallapally — Analyst / Business Analyst - Pega CSSA; Rajeswari Bungatavula — Engineer / Pega Developer. 1 completed LSA/CLSA holder found but with no verified India location, so it cannot evidence an India ladder: Srikanth Gaddamanugu — CLSA 8.6, CPDS, CPBA, CPDC.
- **Tech stack:** CDH/Decisioning, OpenShift/K8s, JMS/MQ, Splunk/PDC
- **Evidence:** 4 people · 1 audit rows · tenure n=0 · departures 0 · joins 0
- **Locations:** Bengaluru
- **Sector:** Banking
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit
- **Green flags:**
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Completed LSA/CLSA found, but India residency unverified
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified

#### Broadridge — 30/100 (Medium confidence, overall rank 43)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 5/30 · P3 innovation 10/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 2 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 2 (0 by architect/lead title, 2 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Kiran Kumar Reddy Yandrapalli — Senior Member Technical; Sahaja Nayuni — Senior Member Technical - CSSA.
- **Tech stack:** AWS, REST/SOAP
- **Evidence:** 4 people · 3 audit rows · tenure n=2 avg 3.42y · departures 0 · joins 1
- **Locations:** Hyderabad, Bengaluru
- **Sector:** Financial Services
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Community / build-in-public visibility: hackathon
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 2 dated engineer record(s)) — stability unverified

#### Telstra — 25/100 (Medium confidence, overall rank 50)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 10/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 2 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 6 (1 by architect/lead title, 5 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Dineshkumar Jagadeesan — Staff Software Engineer / CLSA; Sourabh S. — Senior SE - CLSA-1, SAFe 5 Agilist; Deborupa Dasgupta — Lead Pega Developer. 1 completed LSA/CLSA holder found but with no verified India location, so it cannot evidence an India ladder: Dineshkumar Jagadeesan — CLSA, CPDC, CSSA, CSA. 1 engineer is mid-LSA track but hold no completed LSA/CLSA: Sourabh S. — CLSA Part 1, CSSA, CSA, SAFe 5.
- **Tech stack:** Constellation, CDH/Decisioning, REST/SOAP
- **Evidence:** 7 people · 3 audit rows · tenure n=2 avg 4.63y · departures 0 · joins 1
- **Locations:** Hyderabad, Pune, Bengaluru
- **Sector:** Telecom
- **Hiring status:** Stable/Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Completed LSA/CLSA found, but India residency unverified
  - Senior-most Pega credential evidenced in India is an in-progress LSA, not a completed one
  - Tenure/attrition unmeasured (only 2 dated engineer record(s)) — stability unverified

#### NAB (National Australia Bank) — 25/100 (Medium confidence, overall rank 51)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 10/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 2 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** Leadership evidenced in profile text near an India location, but no India-located senior roster entry confirms global ownership. 1 engineer is mid-LSA track but hold no completed LSA/CLSA: Somil Shukla — LSA-1,CSSA,CPDC. Excluded 1 departed roster entry from this assessment: Gyanendra Mishra — Pega Developer - SERVING NOTICE PERIOD.
- **Tech stack:** Constellation, CDH/Decisioning, REST/SOAP
- **Evidence:** 5 people · 4 audit rows · tenure n=2 avg 2y · departures 3 · joins 4
- **Locations:** Gurugram
- **Sector:** Banking
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
  - 3 ex-Pegasystems hires — imports product-level platform depth
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Senior-most Pega credential evidenced in India is an in-progress LSA, not a completed one
  - 1 senior/lead roster entry evidenced as departed
  - Tenure/attrition unmeasured (only 2 dated engineer record(s)) — stability unverified

#### Ameriprise Financial — 25/100 (Medium confidence, overall rank 52)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 10/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 2 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** Leadership evidenced in profile text near an India location, but no India-located senior roster entry confirms global ownership.
- **Tech stack:** Constellation, CDH/Decisioning, AWS, GenAI/Agentic
- **Evidence:** 4 people · 4 audit rows · tenure n=2 avg 6.75y · departures 0 · joins 1
- **Locations:** Gurugram, Bengaluru
- **Sector:** Financial Services
- **Hiring status:** Stable/Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Architect ladder present in India (1 completed LSA/CLSA holder: Sunil Murugendrappa)
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
- **Red flags:**
  - Support/upgrade language present, build evidence absent
  - Tenure/attrition unmeasured (only 2 dated engineer record(s)) — stability unverified

#### Charles Schwab — 25/100 (Medium confidence, overall rank 54)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 0/30 · P3 innovation 10/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 4 (1 by architect/lead title, 3 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Prathap Kumar — Pega Technology Lead; Renuka Jampani — Software Developer Senior (Pega) - 13yr exp; Shantharaj Mogalapu — Senior Software Specialist. 1 completed LSA/CLSA holder found but with no verified India location, so it cannot evidence an India ladder: Vinay Durgam — CLSA, CSSA, CSA.
- **Tech stack:** CDH/Decisioning
- **Evidence:** 4 people · 2 audit rows · tenure n=1 avg 5.83y · departures 0 · joins 0
- **Locations:** Hyderabad
- **Sector:** Financial Services
- **Hiring status:** Rapidly Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Community / build-in-public visibility: Pega forum
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Completed LSA/CLSA found, but India residency unverified
  - Support/upgrade language present, build evidence absent
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified

#### Intel India — 25/100 (Medium confidence, overall rank 55)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 10/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 4 (0 by architect/lead title, 4 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Ajith Kumar — Cloud App Dev Engineer; Anuj Yadav — Software Engineer (ex-Intel); Poonam Shaw — Cloud App Dev Engineer (ex-Intel).
- **Tech stack:** Constellation, CDH/Decisioning, REST/SOAP
- **Evidence:** 5 people · 1 audit rows · tenure n=1 avg 4.25y · departures 0 · joins 0
- **Locations:** Bengaluru
- **Sector:** Technology / Semiconductor
- **Hiring status:** Stable (some attrition 2025)
- **Sources merged:** team_intelligence, hub_audit
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified

#### MUFG Pension & Market Services (Link Group) — 20/100 (Medium confidence, overall rank 59)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 5/20
- **Attrition:** Medium — Average tenure 2.75y (n=6) — mid-range; neither clearly stable nor clearly churning.
- **Leadership:** India has a senior Pega ladder of 5 (0 by architect/lead title, 5 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Shubham Shinde — Senior Pega Developer - Promoted Oct 2024; Aastha Shah — Pega Developer - Promoted Oct 2025; Praveen Tangella — Pega Application Support.
- **Tech stack:** REST/SOAP
- **Evidence:** 7 people · 0 audit rows · tenure n=6 avg 2.75y · departures 0 · joins 0
- **Locations:** Pune, Mumbai
- **Sector:** Financial Services
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_fresh_evidence
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample

#### Amdocs — 20/100 (Medium confidence, overall rank 60)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 5/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 3 (1 by architect/lead title, 2 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Sai V. — Pega Architect; Jai Veer — Senior Software Engineer; Raghu Pungav — Senior Pega Technical Engineer - CSA, CSSA.
- **Tech stack:** CDH/Decisioning, GenAI/Agentic
- **Evidence:** 4 people · 2 audit rows · tenure n=0 · departures 0 · joins 1
- **Locations:** Gurugram, Pune
- **Sector:** Telecom
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Support/upgrade language present, build evidence absent
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified

#### BNY Mellon — 15/100 (Medium confidence, overall rank 68)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** Top-level title found but India location unverified, so global ownership is not established: Virad Fernando — SVP - Principal Solution Architect (location unverified).
- **Tech stack:** CDH/Decisioning, REST/SOAP
- **Evidence:** 4 people · 2 audit rows · tenure n=1 avg 11.33y · departures 0 · joins 0
- **Locations:** Chennai, Pune
- **Sector:** Banking
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit
- **Green flags:**
  - Architect ladder present in India (1 completed LSA/CLSA holder: Janardhan Krishnan)
- **Red flags:**
  - Senior-most title could not be confirmed as India-based
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified

### 4.3 Low confidence

#### enGen / Highmark India — 60/100 (Low confidence, overall rank 20)

- **Pillars:** P1 autonomy 30/30 · P2 modernity 30/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 2 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** Unambiguous India-based Pega ownership evidenced in research text: "...Director Pega Architecture in Hyderabad...".
- **Tech stack:** Kafka/event-driven, Constellation, CDH/Decisioning, GCP, REST/SOAP, Splunk/PDC
- **Evidence:** 2 people · 5 audit rows · tenure n=2 avg 2.33y · departures 0 · joins 3
- **Locations:** Hyderabad, Chennai
- **Sector:** Healthcare
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - India-based global Pega/platform owner evidenced in research findings
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 2 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### GE HealthCare India — 35/100 (Low confidence, overall rank 40)

- **Pillars:** P1 autonomy 0/30 · P2 modernity 15/30 · P3 innovation 20/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** No title evidence strong enough to locate architectural ownership.
- **Tech stack:** GenAI/Agentic, REST/SOAP, Pega Cloud, Splunk/PDC
- **Evidence:** 1 people · 5 audit rows · tenure n=1 avg 6.5y · departures 0 · joins 0
- **Locations:** Bengaluru, Hyderabad
- **Sector:** Healthcare
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
  - Conference / award visibility: case study
  - Community / build-in-public visibility: Pega forum
- **Red flags:**
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Kotak Mahindra Bank — 35/100 (Low confidence, overall rank 42)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 10/30 · P3 innovation 10/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 1 (0 by architect/lead title, 1 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Tanmay Sonar — Pega Developer - CSSA.
- **Tech stack:** GenAI/Agentic, REST/SOAP
- **Evidence:** 2 people · 1 audit rows · tenure n=1 avg 1.33y · departures 0 · joins 1
- **Locations:** Mumbai, Hyderabad
- **Sector:** Banking
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
  - Community / build-in-public visibility: hackathon
  - 4 ex-Pegasystems hires — imports product-level platform depth
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Bosch — 30/100 (Low confidence, overall rank 44)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 15/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 2 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** Leadership evidenced in profile text near an India location, but no India-located senior roster entry confirms global ownership.
- **Tech stack:** AWS, GenAI/Agentic, Pega Cloud
- **Evidence:** 2 people · 5 audit rows · tenure n=2 avg 5.79y · departures 0 · joins 0
- **Locations:** Bengaluru, Coimbatore
- **Sector:** Industrial
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 2 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### The Hartford India — 30/100 (Low confidence, overall rank 45)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 15/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 3 (2 by architect/lead title, 1 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Krishna Mohan — Lead Software Engineer; Srinandhu Challa — Lead Software Engineer; Sharmila Gurram — Senior Software Engineer.
- **Tech stack:** Constellation, DX API, GenAI/Agentic, Blueprint, REST/SOAP, Splunk/PDC
- **Evidence:** 3 people · 3 audit rows · tenure n=1 avg 0.25y · departures 0 · joins 4
- **Locations:** Hyderabad
- **Sector:** Insurance
- **Hiring status:** Rapidly Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Aflac — 30/100 (Low confidence, overall rank 46)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 15/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 2 (2 by architect/lead title, 0 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Rama Chandraiah Vupputuri — Pega Technical Architect; Prathap Reddy — Pega Lead Developer. 1 engineer is mid-LSA track but hold no completed LSA/CLSA: Rama Chandraiah Vupputuri — CLSA-1, CPDC, CSA.
- **Tech stack:** Constellation, AWS
- **Evidence:** 2 people · 3 audit rows · tenure n=1 avg 7.25y · departures 0 · joins 0
- **Locations:** Hyderabad
- **Sector:** Insurance
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Senior-most Pega credential evidenced in India is an in-progress LSA, not a completed one
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Mastercard — 30/100 (Low confidence, overall rank 47)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 15/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 2 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** Leadership evidenced in profile text near an India location, but no India-located senior roster entry confirms global ownership.
- **Tech stack:** Kafka/event-driven
- **Evidence:** 3 people · 2 audit rows · tenure n=2 avg 11y · departures 0 · joins 0
- **Locations:** Pune
- **Sector:** Payments
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Heavy integration / event-driven / legacy-decommission work evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Significant L2/L3-support and upgrade language alongside build work
  - Tenure/attrition unmeasured (only 2 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Elevance Health (Anthem) — 30/100 (Low confidence, overall rank 48)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 15/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 1 (0 by architect/lead title, 1 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Rahul S. — Senior Pega Developer.
- **Tech stack:** Constellation, DX API, Azure, REST/SOAP
- **Evidence:** 2 people · 2 audit rows · tenure n=1 avg 3.08y · departures 0 · joins 0
- **Locations:** Hyderabad, Gurugram
- **Sector:** Healthcare
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Global Payments India — 30/100 (Low confidence, overall rank 49)

- **Pillars:** P1 autonomy 30/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India holds top-level Pega authority: Puran Kaushal — Director Application System Development - 20yr+ exp.
- **Tech stack:** REST/SOAP
- **Evidence:** 2 people · 0 audit rows · tenure n=0 · departures 0 · joins 0
- **Locations:** Noida
- **Sector:** Fintech
- **Hiring status:** Stable
- **Sources merged:** team_intelligence
- **Green flags:**
  - Top-level Pega/architecture authority sits in India
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Orange Business India — 25/100 (Low confidence, overall rank 53)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 10/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 1 (0 by architect/lead title, 1 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Shivani Baranwal — Pega Developer - CSSA.
- **Tech stack:** GenAI/Agentic, Blueprint, REST/SOAP
- **Evidence:** 3 people · 4 audit rows · tenure n=1 avg 2.08y · departures 0 · joins 0
- **Locations:** Bengaluru, Gurugram
- **Sector:** Telecom
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Roche India — 25/100 (Low confidence, overall rank 56)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 10/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 2 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 2 (1 by architect/lead title, 1 by certification only; 1 hold a completed LSA/CLSA), but no evidenced global owner in India: Kirti Gabda — Pega IT Lead - Triple-certified veteran; Prashant Patil — Pega Architect - ex-Pegasystems, JUST got CLSA.
- **Tech stack:** CDH/Decisioning, GenAI/Agentic, REST/SOAP
- **Evidence:** 2 people · 0 audit rows · tenure n=2 avg 0.92y · departures 0 · joins 0
- **Locations:** Pune
- **Sector:** Pharma
- **Hiring status:** Growing
- **Sources merged:** team_intelligence
- **Green flags:**
  - Architect ladder present in India (1 completed LSA/CLSA holder: Prashant Patil)
  - Constellation / React / custom-Java modernisation evidenced
- **Red flags:**
  - Tenure/attrition unmeasured (only 2 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Pfizer India — 25/100 (Low confidence, overall rank 57)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 10/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 1 (0 by architect/lead title, 1 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Arman Khan — Pega Developer - CSA, CSSA.
- **Tech stack:** GenAI/Agentic, REST/SOAP
- **Evidence:** 1 people · 0 audit rows · tenure n=0 · departures 0 · joins 0
- **Locations:** Mumbai, Chennai
- **Sector:** Pharma
- **Hiring status:** Stable
- **Sources merged:** team_intelligence
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Nike India — 25/100 (Low confidence, overall rank 58)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 10/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 1 (0 by architect/lead title, 1 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Balasubramani Veerapandian — Sr. Software Engineer - PEGA CSSA v25.
- **Tech stack:** Constellation
- **Evidence:** 1 people · 0 audit rows · tenure n=0 · departures 0 · joins 0
- **Locations:** Bengaluru
- **Sector:** Retail
- **Hiring status:** Stable
- **Sources merged:** team_intelligence
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### UBS India — 20/100 (Low confidence, overall rank 61)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 5/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** Top-level title found but India location unverified, so global ownership is not established: Ankit Dangaich — Director - CLSA, Pega Architect/Admin (location unverified); Anuj Malviya — Associate Director / PEGA Senior System Architect (location unverified). 1 completed LSA/CLSA holder found but with no verified India location, so it cannot evidence an India ladder: Ankit Dangaich — CLSA v7.
- **Tech stack:** Azure, REST/SOAP
- **Evidence:** 6 people · 0 audit rows · tenure n=0 · departures 0 · joins 0
- **Locations:** Pune
- **Sector:** Banking
- **Hiring status:** Stable
- **Sources merged:** team_intelligence
- **Green flags:**
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
- **Red flags:**
  - Senior-most title could not be confirmed as India-based
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Completed LSA/CLSA found, but India residency unverified
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### PayPal — 20/100 (Low confidence, overall rank 62)

- **Pillars:** P1 autonomy 15/30 · P2 modernity -5/30 · P3 innovation 10/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 2 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 2 (0 by architect/lead title, 2 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Ashwin Kumar — Software Engineer 3; Rajpriya Shanmugaraj — Software Engineer. 1 engineer is mid-LSA track but hold no completed LSA/CLSA: Ashwin Kumar — CSA, CSSA, LSA-I.
- **Tech stack:** GenAI/Agentic, REST/SOAP
- **Evidence:** 2 people · 3 audit rows · tenure n=2 avg 4.79y · departures 0 · joins 0
- **Locations:** Chennai, Bengaluru
- **Sector:** Payments
- **Hiring status:** Stable/Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
  - Community / build-in-public visibility: hackathon
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Senior-most Pega credential evidenced in India is an in-progress LSA, not a completed one
  - Support-farm language dominates with no build/integration evidence
  - Tenure/attrition unmeasured (only 2 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Deutsche Bank — 20/100 (Low confidence, overall rank 63)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 5/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 1 (1 by architect/lead title, 0 by certification only; 1 hold a completed LSA/CLSA), but no evidenced global owner in India: Mayank Jain — Senior Solution Architect.
- **Tech stack:** GCP, REST/SOAP
- **Evidence:** 2 people · 2 audit rows · tenure n=1 avg 4.58y · departures 0 · joins 1
- **Locations:** Pune, Bengaluru
- **Sector:** Banking
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Architect ladder present in India (1 completed LSA/CLSA holder: Mayank Jain)
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
- **Red flags:**
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### MUFG — 20/100 (Low confidence, overall rank 64)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 5/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 2 (1 by architect/lead title, 1 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Taha Ezzi — Lead Pega Developer; Shubham Shinde — Senior Pega Developer. 1 engineer is mid-LSA track but hold no completed LSA/CLSA: Taha Ezzi — CLSA Part 1, CSSA, CSA.
- **Tech stack:** No specific modern integration/UI stack evidenced.
- **Evidence:** 2 people · 2 audit rows · tenure n=1 avg 2y · departures 0 · joins 0
- **Locations:** Mumbai, Pune, Bengaluru
- **Sector:** Banking
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit
- **Green flags:**
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Senior-most Pega credential evidenced in India is an in-progress LSA, not a completed one
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### FIS (TSYS/Global Payments) — 20/100 (Low confidence, overall rank 65)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 5/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 2 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 2 (2 by architect/lead title, 0 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Akash Sharma — Lead Software Engineer; Utkarsh Saraswat — Lead Software Engineer.
- **Tech stack:** AWS, Azure, Splunk/PDC
- **Evidence:** 2 people · 2 audit rows · tenure n=2 avg 6.5y · departures 0 · joins 0
- **Locations:** Pune, Noida, Hyderabad
- **Sector:** Payments
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 2 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Mizuho Global Services India (MGS) — 20/100 (Low confidence, overall rank 66)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 5/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 1 (0 by architect/lead title, 1 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Sagar Kanchan — Officer 2 - CSSA.
- **Tech stack:** Constellation, GenAI/Agentic, Blueprint, REST/SOAP
- **Evidence:** 1 people · 0 audit rows · tenure n=0 · departures 0 · joins 0
- **Locations:** Navi Mumbai, Chennai
- **Sector:** Banking
- **Hiring status:** Actively Hiring
- **Sources merged:** team_intelligence
- **Green flags:**
  - Constellation / React / custom-Java modernisation evidenced
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Support/upgrade language present, build evidence absent
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Daimler Truck India — 15/100 (Low confidence, overall rank 67)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 2 (1 by architect/lead title, 1 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Nidhi Sinha — Solutions Architect - CSA, CSSA, ex-TCS; Sapana Mishra — Principal Consultant - Pega CSSA, ex-Accenture.
- **Tech stack:** REST/SOAP
- **Evidence:** 3 people · 4 audit rows · tenure n=1 avg 4.83y · departures 0 · joins 0
- **Locations:** Bengaluru
- **Sector:** Automotive
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Conduent — 15/100 (Low confidence, overall rank 69)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 3 (2 by architect/lead title, 1 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Sreenivasulu Ramisetty — Pega Lead System Architect; Sridhar Taniparti — Pega Architect; Gowsalya R — App Developer & Support Engineer II - CSA, CSSA. 1 completed LSA/CLSA holder found but with no verified India location, so it cannot evidence an India ladder: Sreenivasulu Ramisetty — CLSA.
- **Tech stack:** No specific modern integration/UI stack evidenced.
- **Evidence:** 3 people · 2 audit rows · tenure n=0 · departures 0 · joins 0
- **Locations:** Hyderabad, Bengaluru
- **Sector:** Business Services
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Completed LSA/CLSA found, but India residency unverified
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### DHL — 15/100 (Low confidence, overall rank 70)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 3 (0 by architect/lead title, 3 by certification only; 1 hold a completed LSA/CLSA), but no evidenced global owner in India: Siva Jyothi Pamireddy — Senior Software Developer - CLSA, CSSA, CSA; Sameer Mohammad — Senior Software Consultant; Yogitha K. — DevOps Engineer - CSSA, CSA certified Pega developer.
- **Tech stack:** CDH/Decisioning
- **Evidence:** 3 people · 1 audit rows · tenure n=1 avg 4.42y · departures 0 · joins 0
- **Locations:** Hyderabad
- **Sector:** Logistics
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - Architect ladder present in India (1 completed LSA/CLSA holder: Siva Jyothi Pamireddy)
  - Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)
- **Red flags:**
  - Support/upgrade language present, build evidence absent
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Dell Technologies — 15/100 (Low confidence, overall rank 71)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 1 (0 by architect/lead title, 1 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Dhulappa Rajole — CDH Core Developer / Pega Developer.
- **Tech stack:** CDH/Decisioning
- **Evidence:** 3 people · 1 audit rows · tenure n=0 · departures 0 · joins 0
- **Locations:** Hyderabad, Bengaluru
- **Sector:** Technology
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### IFFCO Tokio General Insurance — 15/100 (Low confidence, overall rank 72)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 2 (1 by architect/lead title, 1 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Devender — Pega Lead & Senior Manager; Kamlesh Agarwal — Senior Pega Developer.
- **Tech stack:** No specific modern integration/UI stack evidenced.
- **Evidence:** 2 people · 2 audit rows · tenure n=1 avg 6.17y · departures 0 · joins 0
- **Locations:** Gurugram
- **Sector:** Insurance
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Fidelity National Financial India — 15/100 (Low confidence, overall rank 73)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 1 (1 by architect/lead title, 0 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Sachin Korvi — PEGA System Architect.
- **Tech stack:** REST/SOAP
- **Evidence:** 1 people · 2 audit rows · tenure n=1 avg 9.92y · departures 0 · joins 0
- **Locations:** Bengaluru
- **Sector:** Insurance/Title Services
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Renault-Nissan Tech India — 15/100 (Low confidence, overall rank 74)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 2 (0 by architect/lead title, 2 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Bharathi Priya S — Software Developer / Pega CSSA; Megala Kumaravel — Engineer - Pega CSSA v8.8.
- **Tech stack:** REST/SOAP
- **Evidence:** 2 people · 0 audit rows · tenure n=0 · departures 0 · joins 0
- **Locations:** Chennai
- **Sector:** Automotive
- **Hiring status:** Stable
- **Sources merged:** team_intelligence
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Proximus India — 15/100 (Low confidence, overall rank 75)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 2 (0 by architect/lead title, 2 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Abarna Ravichandran — Senior Associate Consultant (Infosys) - CSA, CSSA; Niveditha Bandari — Solution Engineer - CSA, CSSA, CPDC.
- **Tech stack:** CDH/Decisioning, REST/SOAP
- **Evidence:** 2 people · 0 audit rows · tenure n=0 · departures 0 · joins 0
- **Locations:** Hyderabad
- **Sector:** Telecom
- **Hiring status:** Stable
- **Sources merged:** team_intelligence
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Mondelez India — 15/100 (Low confidence, overall rank 76)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 1 (0 by architect/lead title, 1 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Modalavalasa Vinay Kumar — Senior Associate Consultant (Infosys) - Pega SSA.
- **Tech stack:** REST/SOAP
- **Evidence:** 2 people · 0 audit rows · tenure n=0 · departures 0 · joins 0
- **Locations:** India
- **Sector:** FMCG
- **Hiring status:** Stable
- **Sources merged:** team_intelligence
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Marsh McLennan India (MMGS) — 15/100 (Low confidence, overall rank 77)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 1 (1 by architect/lead title, 0 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Dhananjay Dhawale — Senior Manager - Workflow Application Lead, Pega Platform.
- **Tech stack:** REST/SOAP
- **Evidence:** 1 people · 1 audit rows · tenure n=0 · departures 0 · joins 0
- **Locations:** Mumbai
- **Sector:** Insurance/Professional Services
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Levi Strauss & Co. India — 15/100 (Low confidence, overall rank 78)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 2 (0 by architect/lead title, 2 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Disha Kukreja — Senior Pega Developer; Hemant M — Pega Developer - CSSA, CSA, CPDC.
- **Tech stack:** REST/SOAP
- **Evidence:** 2 people · 0 audit rows · tenure n=0 · departures 0 · joins 0
- **Locations:** Bengaluru
- **Sector:** Retail / Fashion
- **Hiring status:** Stable
- **Sources merged:** team_intelligence
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Novartis India — 15/100 (Low confidence, overall rank 79)

- **Pillars:** P1 autonomy 15/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** India has a senior Pega ladder of 1 (0 by architect/lead title, 1 by certification only; 0 hold a completed LSA/CLSA), but no evidenced global owner in India: Vijay Krishna — Sr Pega Developer (via vendor).
- **Tech stack:** No specific modern integration/UI stack evidenced.
- **Evidence:** 1 people · 0 audit rows · tenure n=0 · departures 0 · joins 0
- **Locations:** Hyderabad
- **Sector:** Pharma
- **Hiring status:** Stable
- **Sources merged:** team_intelligence
- **Red flags:**
  - No LSA/CLSA-certified architect evidenced in the India sample
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### ICICI Bank — 0/100 (Low confidence, overall rank 80)

- **Pillars:** P1 autonomy 0/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** No title evidence strong enough to locate architectural ownership.
- **Tech stack:** REST/SOAP
- **Evidence:** 2 people · 2 audit rows · tenure n=1 avg 10.33y · departures 0 · joins 0
- **Locations:** Visakhapatnam, Noida, Hyderabad
- **Sector:** Banking
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Red flags:**
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Visa — 0/100 (Low confidence, overall rank 81)

- **Pillars:** P1 autonomy 0/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** No title evidence strong enough to locate architectural ownership.
- **Tech stack:** CDH/Decisioning
- **Evidence:** 1 people · 2 audit rows · tenure n=1 avg 11y · departures 0 · joins 0
- **Locations:** Bengaluru, Pune
- **Sector:** Payments
- **Hiring status:** Moderate
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Red flags:**
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Capital One India — 0/100 (Low confidence, overall rank 82)

- **Pillars:** P1 autonomy 0/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 1 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** No title evidence strong enough to locate architectural ownership.
- **Tech stack:** REST/SOAP
- **Evidence:** 2 people · 1 audit rows · tenure n=1 avg 9.75y · departures 0 · joins 0
- **Locations:** Bengaluru, Pune
- **Sector:** Banking
- **Hiring status:** Stable
- **Sources merged:** team_intelligence, hub_audit
- **Red flags:**
  - Tenure/attrition unmeasured (only 1 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Synchrony Financial — 0/100 (Low confidence, overall rank 83)

- **Pillars:** P1 autonomy 0/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** No title evidence strong enough to locate architectural ownership.
- **Tech stack:** No specific modern integration/UI stack evidenced.
- **Evidence:** 1 people · 1 audit rows · tenure n=0 · departures 0 · joins 1
- **Locations:** Hyderabad
- **Sector:** Financial Services
- **Hiring status:** Declining
- **Sources merged:** team_intelligence, hub_audit, hub_fresh_evidence
- **Green flags:**
  - 2 ex-Pegasystems hires — imports product-level platform depth
- **Red flags:**
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### PepsiCo India — 0/100 (Low confidence, overall rank 84)

- **Pillars:** P1 autonomy 0/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** No title evidence strong enough to locate architectural ownership.
- **Tech stack:** REST/SOAP
- **Evidence:** 1 people · 1 audit rows · tenure n=0 · departures 0 · joins 0
- **Locations:** India
- **Sector:** FMCG
- **Hiring status:** Growing
- **Sources merged:** team_intelligence, hub_audit
- **Red flags:**
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Fiserv — 0/100 (Low confidence, overall rank 85)

- **Pillars:** P1 autonomy 0/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 2 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** No title evidence strong enough to locate architectural ownership.
- **Tech stack:** No specific modern integration/UI stack evidenced.
- **Evidence:** 0 people · 2 audit rows · tenure n=2 avg 7.58y · departures 0 · joins 0
- **Sources merged:** hub_audit
- **Red flags:**
  - Tenure/attrition unmeasured (only 2 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### AXA India — 0/100 (Low confidence, overall rank 86)

- **Pillars:** P1 autonomy 0/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** No title evidence strong enough to locate architectural ownership.
- **Tech stack:** REST/SOAP
- **Evidence:** 1 people · 0 audit rows · tenure n=0 · departures 0 · joins 0
- **Locations:** Bengaluru
- **Sector:** Insurance
- **Hiring status:** Stable
- **Sources merged:** team_intelligence
- **Red flags:**
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Maersk GSC India — 0/100 (Low confidence, overall rank 87)

- **Pillars:** P1 autonomy 0/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** No title evidence strong enough to locate architectural ownership.
- **Tech stack:** REST/SOAP
- **Evidence:** 1 people · 0 audit rows · tenure n=0 · departures 0 · joins 0
- **Locations:** Bengaluru, Mumbai
- **Sector:** Logistics
- **Hiring status:** Stable
- **Sources merged:** team_intelligence
- **Red flags:**
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### Cummins India — 0/100 (Low confidence, overall rank 88)

- **Pillars:** P1 autonomy 0/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** No title evidence strong enough to locate architectural ownership.
- **Tech stack:** REST/SOAP
- **Evidence:** 1 people · 0 audit rows · tenure n=0 · departures 0 · joins 0
- **Locations:** Pune
- **Sector:** Manufacturing
- **Hiring status:** Stable
- **Sources merged:** team_intelligence
- **Red flags:**
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

#### ITC Limited — 0/100 (Low confidence, overall rank 89)

- **Pillars:** P1 autonomy 0/30 · P2 modernity 0/30 · P3 innovation 0/20 · P4 attrition 0/20
- **Attrition:** Unknown — Tenure unmeasured: only 0 engineer(s) with parseable dates (need 3). Pillar scored 0, not penalised.
- **Leadership:** No title evidence strong enough to locate architectural ownership.
- **Tech stack:** REST/SOAP
- **Evidence:** 1 people · 0 audit rows · tenure n=0 · departures 0 · joins 0
- **Locations:** Gurugram
- **Sector:** FMCG / Conglomerate
- **Hiring status:** Growing
- **Sources merged:** team_intelligence
- **Red flags:**
  - Tenure/attrition unmeasured (only 0 dated engineer record(s)) — stability unverified
  - Thin evidence base: score is indicative only
  - Not rank-comparable: too little evidence to place this company against the others

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

### 5.4 The ledger

#### Cisco India — engineering score 65/100

- **Food And Commute** — `UNVERIFIED`
  - Subsidised multi-cuisine cafeterias on the Bangalore campus. No official confirmation of free daily meals or blanket AC cab routes was found.
  - _Sources:_ Cisco Bangalore campus blog (blogs.cisco.com) · no official India food/transport policy page located
- **Insurance Perks** — `VERIFIED`
  - LifeConnections Health Center on the Bangalore campus (BGL-15) - a full onsite medical facility with physicians, specialists and mental-health professionals. Bangalore is one of only THREE Cisco campuses worldwide with this, alongside San Jose and Research Triangle Park.
  - _Sources:_ cisco.com Purpose Reporting Hub - Benefits · blogs.cisco.com Cisco Bangalore campus tour
- **Office Mandate** — `NOT_RESEARCHED`
  - Hybrid, but no specific India day-count mandate was found on an official source.
- **The Flex** — `VERIFIED`
  - Time2Give: 10 paid volunteer days per year. Four 'Days for Me' designated days off. A paid day off for your birthday. Two gyms plus an onsite massage facility (BGL-16) on the Bangalore campus. Employee Stock Purchase Plan available in 70+ countries at a discount.
  - _Sources:_ careers.cisco.com/global/en/benefits-and-perks · cisco.com Purpose Reporting Hub · blogs.cisco.com Bangalore campus tour
- **Espp Discount Rate** — `UNVERIFIED`
  - A 10% ESPP discount is widely cited, but official Cisco pages state only 'at a discount' without a percentage.
  - _Sources:_ careers.cisco.com states discount without rate
- **Standout perk:** An onsite full medical centre that exists at only three Cisco sites on earth, and Bangalore is one of them.

#### Booking Holdings India — engineering score 45/100

- **Food And Commute** — `VERIFIED_GLOBAL_POLICY`
  - Official careers page offers lunch benefits and game rooms 'in some of our locations' - it does NOT confirm Bangalore specifically. Third-party listings cite on-site meals, coffee and snacks including vegan options.
  - _Sources:_ careers.booking.com/hybrid-ways-of-working/ · Welcome to the Jungle / Otta company listing
- **Insurance Perks** — `VERIFIED_GLOBAL_POLICY`
  - Health insurance, life insurance, disability insurance, pension plan, Global Employee Assistance Program, and free Headspace access for employee and loved ones. India-specific parental-insurance detail not confirmed.
  - _Sources:_ careers.booking.com/benefits/ · Welcome to the Jungle listing
- **Office Mandate** — `VERIFIED_GLOBAL_POLICY`
  - Explicit hybrid model: 'We want you to do your best work and we know that doesn't always mean working from an office.' No fixed India day-count published.
  - _Sources:_ careers.booking.com/hybrid-ways-of-working/
- **The Flex** — `VERIFIED`
  - Working from Abroad up to 20 days per calendar year, conditional on legal right to work in that country and no tax or social-security consequences. Parent leave 22 weeks. Grandparent leave 10 days. Care leave 10 days. Bereavement up to 4 weeks. Booking Cares: 2 paid volunteer/learning days. Anniversary leave. Work-from-home furniture and ergonomic support.
  - _Sources:_ careers.booking.com/benefits/ · careers.booking.com/hybrid-ways-of-working/
- **Standout perk:** Working from Abroad - up to 20 days a year from another country, published as official policy rather than an informal arrangement.

#### Goldman Sachs — engineering score 45/100

- **Food And Commute** — `CONTESTED_BY_ROLE`
  - Not free. Lunch is roughly 50% subsidised; breakfast, dinner and late-night meals are free only on extended or overnight shifts. Transport is provided within about 30km of the office, but as late-hours drops rather than blanket all-day AC cab routes. The official benefits page describes 'reimbursement for certain entertainment, meals, communication, and transportation' - reimbursement, not complimentary provision.
  - _Sources:_ goldmansachs.com/careers/benefits (reimbursement wording) · GS official Guide to Bengaluru PDF (transport within 30km) · AmbitionBox reviews 2022-2024 (some report free food/transport) · Taro Associate Software Engineer review Sep 2023 ('almost no free benefits; everything is to be paid for') · Quora employee threads (investment-bank 'no free lunches' norm)
- **Insurance Perks** — `VERIFIED_GLOBAL_POLICY`
  - Medical, dental, short- and long-term disability, life, accidental death and business travel accident insurance, explicitly varying by office location. Onsite health clinics and onsite childcare are reported at the Bengaluru campus. Day-1 no-co-pay parental cover was NOT confirmed.
  - _Sources:_ goldmansachs.com/careers/benefits · AmbitionBox office-perks listing
- **Office Mandate** — `VERIFIED`
  - Strict return-to-office, widely reported as 5 days per week, at Helios Business Park on Outer Ring Road.
  - _Sources:_ GS official Guide to Bengaluru PDF (Helios Business Park, LEED Platinum) · tech forum and review consensus 2024
- **The Flex** — `VERIFIED`
  - Elite base pay, LEED Platinum campus at Helios Business Park, onsite gym and health facilities. The trade is compensation and facilities in exchange for low flexibility.
  - _Sources:_ GS official Guide to Bengaluru PDF · goldmansachs.com/careers/benefits
- **Standout perk:** A purpose-built LEED Platinum campus with onsite clinics and childcare - strong facilities, weak flexibility.

#### Pegasystems India — engineering score 50/100

- **Food And Commute** — `NOT_RESEARCHED`
  - Not researched in this pass.
- **Insurance Perks** — `NOT_RESEARCHED`
  - Not researched in this pass.
- **Office Mandate** — `UNVERIFIED`
  - Fully remote India roles were recorded earlier in this hub's remote-work table, but that entry is flagged as an unrevalidated historical lead.
  - _Sources:_ hub remote/hybrid table - flagged as historical, needs revalidation
- **The Flex** — `UNVERIFIED`
  - Strong ESPP and good work-life balance are commonly reported, but no official source was checked in this pass.
- **Standout perk:** Owning stock in the product you build - attractive, but the ESPP terms were not verified here.

#### Ford Motor Company — engineering score 100/100

- **Food And Commute** — `NOT_RESEARCHED`
  - Not researched in this pass.
- **Insurance Perks** — `NOT_RESEARCHED`
  - Not researched in this pass.
- **Office Mandate** — `NOT_RESEARCHED`
  - Not researched in this pass.
- **The Flex** — `NOT_RESEARCHED`
  - Not researched in this pass.
- **Standout perk:** Unknown - not researched.

#### Commonwealth Bank — engineering score 85/100

- **Food And Commute** — `NOT_RESEARCHED`
  - Not researched in this pass.
- **Insurance Perks** — `NOT_RESEARCHED`
  - Not researched in this pass.
- **Office Mandate** — `UNVERIFIED`
  - Hybrid, Manyata Tech Park Bengaluru, per a 2024 internal hiring post found earlier in this research.
  - _Sources:_ Rishabh Raj CBA hiring post Oct 2024 - describes hybrid, Manyata Tech Park
- **The Flex** — `NOT_RESEARCHED`
  - Not researched in this pass.
- **Standout perk:** Unknown - not researched.

#### Vodafone / VOIS — engineering score 85/100

- **Food And Commute** — `NOT_RESEARCHED`
  - Not researched in this pass.
- **Insurance Perks** — `NOT_RESEARCHED`
  - Not researched in this pass.
- **Office Mandate** — `UNVERIFIED`
  - Hybrid, Pune, per a March 2025 Pega hiring post found earlier in this research.
  - _Sources:_ Yogesh Dixit VOIS hiring post Mar 2025 - 'permanent positions, Pune, hybrid'
- **The Flex** — `NOT_RESEARCHED`
  - Not researched in this pass.
- **Standout perk:** Unknown - not researched.

#### Sun Life — engineering score 80/100

- **Food And Commute** — `NOT_RESEARCHED`
  - Not researched in this pass.
- **Insurance Perks** — `NOT_RESEARCHED`
  - Not researched in this pass.
- **Office Mandate** — `UNVERIFIED`
  - Gurugram / Bengaluru per Jun 2025 hiring posts; attendance policy unknown.
  - _Sources:_ Anil Kumar Pal Sun Life hiring post Jun 2025 - job IDs JR00110363, JR00110359
- **The Flex** — `NOT_RESEARCHED`
  - Not researched in this pass.
- **Standout perk:** Unknown - not researched.

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

## 8. Person-level corrections (research integrity)

10 individuals were filed under the wrong employer or country in the prior audit.
These matter because a misfiled person shifts a company's pillar scores:

- **Tarani Bhavani**, **Devansh Mathur** → **JPMC** (were filed under Booking)
- **Karthik Manimozhi**, **Abhishek Saurabh** → **Standard Chartered**
- **Ajay Kumar** → **Wells Fargo**
- **Chinmaya Baral**, **Vivek Kumar** → **Nokia**
- **Karan Rajput** → **NAB**
- **Virad Fernando** → **BNY Mellon, Pittsburgh (USA — not India)**
- **Pankaj Goel** → **Visa, Texas (USA — not India)**

Also produced: **15+** people newly discovered beyond the prior audit, and **18**
actionable hiring signals.

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

## 10. JSON schemas

### 10.1 `gcc_ranking_scores.json`

```
{
  generatedAt, asOf,
  rubric: { name, max, pillars: { p1..p4: { max, min, note? } } },
  counts: { scored, insufficient_evidence, high_confidence,
            medium_confidence, low_confidence, attrition_unknown },
  methodology_caveats: { evidence_volume_correlation, interpretation,
                         tenure_rule, short_tenure_rule,
                         rubric_arithmetic, not_measured },
  companies: [{
    company_name, total_score, score_status,
    leadership_location_analysis, tech_stack_modernity,
    attrition_warning_level,                 // Low | Medium | High | Unknown
    red_flags: [], green_flags: [],
    evidence_confidence,                     // High | Medium | Low | None
    pillar_breakdown: {
      p1_architectural_autonomy: { score, max },
      p2_modernity_integration: { score, max, signals: { heavy, modern, cloud, support } },
      p3_innovation_visibility: { score, max, signals: { ev, comm } },
      p4_attrition_index:       { score, max, measured, notes }
    },
    evidence: { peopleCount, auditRows, tenureN, tenureAvgYears,
                departureSignals, joinSignals, sources: [],
                locations: [], team_size, hiring_status, sectors: [] },
    rank, rank_within_confidence, confidence_tier_size, rank_comparable
  }]
}
```

### 10.2 `gcc_lifestyle_supplement.json`

```
{
  note, asOf,
  status_legend: { VERIFIED, VERIFIED_GLOBAL_POLICY,
                   CONTESTED_BY_ROLE, UNVERIFIED, NOT_RESEARCHED },
  companies: [{
    company_name, engineering_score,
    lifestyle_intelligence: {
      <aspect>: { claim, status, sources: [] }    // food_and_commute, insurance_perks,
                                                 // office_mandate, the_flex, ...
    },
    standout_fun_perk?, caveat?
  }],
  coverage: { companies_with_verified_lifestyle_evidence,
              companies_with_partial_or_unverified,
              companies_not_researched, total_in_ledger,
              engineering_ranking_total, warning }
}
```

**Note on `score_status`:** the original spec asked for a flat object per company.
`score_status`, `evidence_confidence` and `rank_comparable` were added because
emitting a bare `total_score` for a company with zero evidence would have been
indistinguishable from a genuinely low score.

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
