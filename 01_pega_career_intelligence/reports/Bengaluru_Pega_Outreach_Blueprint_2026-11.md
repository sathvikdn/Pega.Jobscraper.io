# Bengaluru Pega Outreach Blueprint — 2026-11-11

**Positioning:** Pega CSSA · event-driven Kafka integration · Service-REST replay & dead-letter recovery · metadata-driven JSON mapping · Pega observability

**Proof points:**
- Batch-to-real-time Kafka ingestion across 50+ topics, millions of records, seven APAC markets
- Multi-hour batch runs cut to under 15 minutes
- Service-REST replay + dead-letter recovery: incident recovery from ~2 hours to under 2 minutes
- Runtime metadata-driven JSON mapping: new-format onboarding from ~4 weeks to ~10 minutes
- $250K+ annual savings from automation (hub profile figure)

**Stay honest:** Production depth is integration, case management and observability. CDH strategy design is not production experience, so position for the data and integration side of decisioning teams.

## Module 1 · Architecture alignment & GCC tiers

### T1 · High-Throughput & Event-Driven
**Companies:** Commonwealth Bank / ASB, Cisco India, First Citizens India, Wells Fargo India, JPMorganChase India, Goldman Sachs, BNY, Siemens, John Deere India, Booking Holdings India, MBRDI (benchmark)

**Evidence:** Job descriptions and talks name Kafka, events and async patterns (CBA/ASB JD), externalised Kafka on OpenShift (Cisco PegaWorld 2025), Kafka/JMS (First Citizens SE II JD), Kafka/async plus queue processors on WaaS 24.1.3 (Wells Fargo), payment investigations at SWIFT/Fed volume (Wells, Goldman, JPMC), sanctions screening (BNY), 8M+ invoices across 40+ countries (Siemens CCMT) and real-time agent data for ~10,000 agents (Booking).

**Friction points:**
- Consumer lag and backpressure when topic volume outpaces queue processors or data flows; node scaling is reactive.
- Replays create duplicate cases or double writebacks because handlers are not idempotent.
- Poison messages are handled by hand, so a bad payload turns into a multi-hour incident with log digging.
- Schema drift across markets/versions breaks hard-coded mappings at every rollout.
- No end-to-end trace from topic offset to case ID to downstream writeback, so support cannot prove where an event died.
- Re-platforming (OpenShift, Pega Cloud, active-passive DR) changes rebalancing and failover behaviour of consumers.

**Talking points:**
1. Throughput without fragility: I moved batch integrations to real-time Kafka ingestion across 50+ topics and seven markets. Multi-hour batch windows came down to under 15 minutes, and handlers are idempotent, so replays never create duplicate cases.
1. Recovery as a feature, not a runbook: I built Service-REST replay and dead-letter handling that parks failed events with case context and reprocesses them automatically. Incident recovery went from ~2 hours to under 2 minutes, with monitoring that ties offset → case → writeback.

### T2 · Decisioning & Intelligence
**Companies:** Commonwealth Bank (CDH / Next Best Conversation), Standard Chartered (Bengaluru CDH), NatWest Group, VOIS (Vodafone), HSBC, Verizon, Telstra India, Pegasystems India (CDH / Process AI engineering)

**Evidence:** Public sources: ~200 adaptive models at ~200 ms decisions (CBA), 1,800 NBA actions across 8 channels and a Pega Cloud migration started because of timeouts (NatWest), 10+ channels for 6.4M customers (VOIS), a Bengaluru decisioning-architect hiring wave in 2025–26 (Standard Chartered), Process AI in case management (Telstra), and CDH/ML product teams (Pegasystems).

**Friction points:**
- Real-time event ingestion into CDH (Kafka data sets, data flows) cannot keep up with decision SLAs, so NBA runs on stale context.
- Response capture at volume: late or missing responses starve adaptive models.
- Validating strategy changes at scale before production (one public post notes teams without BOE fall back on manual testing).
- Cloud migration and upgrade stability: timeouts, long upgrade cycles, data-flow tuning.
- Onboarding each new channel or data source needs mapping code and a release.

**Talking points:**
1. The data path into decisioning: real-time NBA usually fails on ingestion, not strategy (late, malformed or duplicate events). I build high-throughput Kafka ingestion with dead-letter handling and lag monitoring, so decisions run on current context.
1. Configurable onboarding: my metadata-driven JSON mapping layer cut new-source onboarding from ~4 weeks to ~10 minutes. For a CDH team, new channels or attributes can be wired by configuration, without a release. I'd pair with your decisioning architects rather than claim strategy-design depth.

### T3 · Core Case Management & Enterprise Modernisation
**Companies:** Empower India, Daimler Truck India (DTICI), Nokia India, Broadridge India, Société Générale GSC, BT Group, Morgan Stanley, Sun Life, Ameriprise India, Shell India, Carelon, MUFG Global Service, ANZ, Ford (Bengaluru), Nike / Levi's / Intel / GE HealthCare / Unilever and other Tier-B/C teams

**Evidence:** Pega 24.x with Constellation and 24/7 production support (Empower), legacy rebuilt in 14 weeks on Blueprint/Pega Cloud (DTICI), order orchestration and DevOps (Nokia), Infinity + Constellation + GenAI JDs (Broadridge), migration/modernisation of banking apps (Société Générale), BT Business platform modernisation (BT), KYC/onboarding platforms (Morgan Stanley), on-prem 8.8 with FileNet (MUFG).

**Friction points:**
- Legacy retirement: mapping old system-of-record formats into Pega data models, with reconciliation done in spreadsheets.
- Upgrades (8.x → 24/25) and Constellation re-platforming expose custom UI and guardrail debt.
- Writeback to systems of record fails silently, leaving cases and SOR out of sync until a support ticket arrives.
- Background processing (file listeners, job schedulers, BIX extracts) grows into long nightly runs and on-call load.
- Contractor-heavy maintenance concentrates knowledge in vendors.

**Talking points:**
1. Batch retirement during modernisation: I replaced file/batch integrations with Kafka and REST, taking multi-hour runs to under 15 minutes and removing a nightly support burden. It's the kind of change that makes a re-platformed app cheaper to run, not just newer.
1. Self-healing writebacks and configurable mapping: failed SOR updates land in a replay/dead-letter queue with case context and recover automatically (~2 hours → under 2 minutes), and metadata-driven mapping makes new legacy formats a configuration task (weeks → minutes).

## Module 2 · Outreach scripts

### Peer SSA / Lead Architect · High-Throughput & Event-Driven (95 words)
*Use for: Cisco, Wells Fargo, Siemens, John Deere, First Citizens peers*

> Hi [Name] — your [Cisco] team's move to externalised Kafka during the OpenShift migration is close to what I work on: high-throughput Kafka ingestion into Pega across 50+ topics. The hard part for us wasn't throughput, it was replay and dead-letter handling: making reprocessing idempotent so a failover doesn't create duplicate cases. How does your team handle reprocessing after a consumer rebalance — replay from offsets, or park failures in a recovery queue? Happy to share what worked for us; it took recovery from about two hours to under two minutes. — Sathvik, Pega CSSA

### Peer SSA / Lead Architect · Decisioning & Intelligence (92 words)
*Use for: Standard Chartered, NatWest, VOIS, Verizon, CBA decisioning peers*

> Hi [Name] — your work on [CDH / NBA at Standard Chartered] caught my attention. I work on the ingestion side of Pega: Kafka events feeding a metadata-driven JSON mapping layer, so new sources onboard without code changes. In the setups I've seen, real-time NBA quality depends more on late or malformed events and response capture than on strategies. Is that your experience, or does the bottleneck sit elsewhere — data flows, simulation, model feedback? I'd value your view and can share what we learned about event plumbing. — Sathvik, Pega CSSA

### Peer SSA / Lead Architect · Core Case Management & Enterprise Modernisation (86 words)
*Use for: Empower, DTICI, Nokia, Broadridge, Société Générale, BT peers*

> Hi [Name] — I saw you're working on [the Blueprint-based modernisation at DTICI]. A lot of my last few years went into retiring batch integrations around Pega: moving file and batch flows to Kafka and REST, and adding replay and dead-letter recovery so failed writebacks to systems of record fix themselves. Multi-hour runs ended up under 15 minutes. How is your team handling background processing and SOR writeback in the new build — queue processors, listeners, something else? Curious how it compares. — Sathvik, Pega CSSA

### Engineering Manager / Director (live role ID) · High-Throughput & Event-Driven (93 words)
*Use for: CBA/ASB (after interview outcome), First Citizens SE II, Wells Fargo if a req opens*

> Hi [Name] — I've applied for [role, ID]. The JD's focus on [events, async patterns and resiliency] is what I run in production: Kafka ingestion into Pega across 50+ topics and seven markets, with Service-REST replay and dead-letter recovery that cut incident recovery from about two hours to under two minutes and took batch windows from hours to under 15 minutes. In practice that meant fewer support escalations and faster market rollouts. If it helps your shortlist, I can walk through the recovery design in 15 minutes. — Sathvik D N, Pega CSSA

### Engineering Manager / Director (live role ID) · Decisioning & Intelligence (86 words)
*Use for: Decisioning teams with a posted role*

> Hi [Name] — I've applied for [role, ID]. Where I'd add value to a decisioning team is the data path into CDH: high-throughput Kafka ingestion, a metadata-driven mapping layer that cut new-source onboarding from about four weeks to ten minutes, and monitoring on lag and failed events so models aren't fed stale context. To be upfront, my production depth is integration and case management, not strategy design. I'd pair with your decisioning architects rather than replace them. Open to a short call if that profile fits.

### Engineering Manager / Director (live role ID) · Core Case Management & Enterprise Modernisation (82 words)
*Use for: Empower, Broadridge, Nokia, Booking, DTICI with a posted role*

> Hi [Name] — I've applied for [role, ID]. In modernisation programmes the slow parts are usually integration rewrites, data mapping and post-go-live support. That's my work: I moved batch flows to Kafka and REST (hours to under 15 minutes), built metadata-driven JSON mapping that turned new formats from weeks into minutes, and automated replay and dead-letter recovery so support load drops after go-live. Happy to share specifics in a 15-minute call if it helps your shortlist. — Sathvik D N, Pega CSSA

### Leadership / AGM (no public posting) · High-Throughput & Event-Driven (77 words)
*Use for: John Deere AGM, Cisco SRE lead, Siemens lead*

> Hi [Name] — a question rather than a pitch. As more of [company]'s Pega workload moves onto event-driven integration, do you expect to grow the Bengaluru team around that layer, or keep it with platform/SRE? I'm a Pega CSSA who builds exactly that: high-throughput Kafka ingestion with automated replay and dead-letter recovery. I'd like to be on your radar if a role opens in the next couple of quarters. No ask beyond that. — Sathvik D N

### Leadership / AGM (no public posting) · Decisioning & Intelligence (78 words)
*Use for: Decisioning leaders without postings*

> Hi [Name] — a quick question on direction. Is [company]'s decisioning work over the next year more about scaling real-time NBA (more event sources, tighter latency) or about running what's already live? I ask because my strength is the integration side of that problem: Kafka ingestion, configurable data mapping and monitoring so decisions run on current data. If expansion is planned in Bengaluru, I'd appreciate knowing where to keep an eye out. — Sathvik D N, Pega CSSA

### Leadership / AGM (no public posting) · Core Case Management & Enterprise Modernisation (77 words)
*Use for: Modernisation leaders without postings*

> Hi [Name] — I enjoyed reading about [the 14-week Blueprint rebuild / your platform modernisation]. Will the next phase stay with the current team, or is the Bengaluru team expanding for it? I'm a Pega CSSA whose work is the unglamorous part of modernisation: retiring batch integrations, making SOR writebacks self-recovering, and making data mapping configurable. If that's on your roadmap, I'd welcome a pointer to the right team when the time comes. — Sathvik D N

## Module 3 · Pre-outreach checklist

1. **Production stack breakdown:** List what coexists with Pega from JDs, PegaWorld talks and engineer profiles: messaging (Kafka/JMS), cloud (AWS/Azure/GCP, Pega Cloud vs on-prem/OpenShift), databases (Oracle/Postgres), services (Spring Boot/Java), UI (Constellation vs UI-kit), DevOps (Deployment Manager, Jenkins, Azure DevOps). Fit check: does at least one item match your Kafka/REST/observability strengths?
2. **The hook:** Find one dated, public change: a migration, upgrade, Blueprint/Constellation rebuild, cloud move, new squad or new manager. Use it as the first line of every message. No hook means no message yet.
3. **Contact hierarchy:** Peer (same band, recent joiner) → architect/lead (one technical question) → manager only with a role ID → leadership only for roadmap questions. Never message two people on the same squad on the same day. If you are in an active interview loop, message peers only.
4. **Technical interview prep:** Derive the three likeliest deep-dive questions from that firm's JD and workstreams (not hearsay): usually one integration/resilience design, one platform/version question (Cloud, Constellation, upgrade) and one domain case-design question. Prepare a 3-minute whiteboard answer for each.
5. **Red flags:** Contractor or staffing-firm seats posing as direct roles, '24/7 support' or 'BAU' wording, title inflation through consulting titles, Pega being replaced by Java/low-code alternatives, frozen or removed postings, and the lead or decision-makers sitting in another city.

### Applied to the top 15

#### Commonwealth Bank / ASB (T1/T2)
- **Stack:** Pega Infinity, Pega Cloud 24.2, CDH (~200 models, ~200 ms), REST, events/async, AWS skills on the team
- **Hook:** New ASB India squad: Engineering Manager REQ266820 + Senior SWE REQ266821/822 (Oct 2026)
- **Sequence:** Interview is live, so prep chats with peers only (Deep Shikha, Nalini Landge, Krishnachaitanya Mudragani). No panel members or managers until the outcome.
- **Likely deep-dive questions:** Design a case hierarchy and class structure for a lending app shared across tribes · Make an async event integration resilient: retries, idempotency, error handling, observability · What changes on Pega Cloud vs on-prem (no DB/JVM access, upgrades, extensions)?
- **Red flags:** Down-level to Software Engineer; staffing-firm seats

#### First Citizens India (T1)
- **Stack:** Pega Infinity, Pega AI (GenAI, Knowledge Buddy), REST/Kafka/JMS/SOAP, Java, Robot Manager
- **Hook:** SE I/II Pega Developer postings (Deposits & Shared Services, Aug–Sep 2026) + Senior Manager – Pega (Lending Digital Automation)
- **Sequence:** Apply → Tushar Banerjee or Nimalan Peter → Deepak Shahi (one technical question) → Abhi Gummaraju with the role ID
- **Likely deep-dive questions:** Consume Kafka/JMS events into case creation with error handling and replay · Design a Knowledge Buddy/GenAI feature with guardrails and audit · Where does Robot Manager orchestration end and Pega workflow begin?
- **Red flags:** US-hours overlap; robotics-heavy role labelled 'Pega'

#### Empower India (T3)
- **Stack:** Pega 24.x, Constellation, PDC, BIX, file listeners, job schedulers, agents, AWS modernisation
- **Hook:** Developer Software (3–4 yrs, CSA) and Senior Production Support postings
- **Sequence:** Apply → Divya Mohanraj or Nithin H N → Ankit Punjarwar with the role ID
- **Likely deep-dive questions:** Design high-volume file intake with listeners/job schedulers and failure handling · Triage a production slowdown using PDC, PAL and DB tracer · Migrate an existing UI-kit app to Constellation
- **Red flags:** 24/7 support role; AWS modernisation may shrink Pega scope

#### Daimler Truck India (DTICI) (T3)
- **Stack:** Pega Infinity, Pega Blueprint, Pega Cloud (PaaS), Constellation
- **Hook:** PegaWorld 2026: DTFS legacy app rebuilt in 14 weeks on Blueprint; Aug 2025 hiring wave
- **Sequence:** Sivakumar Annameti or Subiksha Ramachandran → Aradhika Sinha (CBA vs DTICI) → Nidhi Sinha
- **Likely deep-dive questions:** Harden a Blueprint-generated app for production (data model, integrations, security) · Constellation DX/data-page design for a finance workflow · Integrate leasing/loan systems of record with reliable writeback
- **Red flags:** Consulting titles hide band; small team hires in waves

#### Booking Holdings India (T1/T3)
- **Stack:** Pega Customer Service, Constellation, CDH, REST/legacy integrations
- **Hook:** Three new Pega Engineering Managers (Mar 2025, Sep 2026, Oct 2026) and three LSAs in 20 months
- **Sequence:** Satish Varma Penmetsa or Vartika Tiwari → Nanda Kumari K B or Ananda Bhat → Anish Kumar K P / Sarabdeep Singh with the role ID
- **Likely deep-dive questions:** Constellation agent-desktop design for booking changes/cancellations · Resilient real-time data retrieval for agents (timeouts, caching, fallbacks) · Customer Service intents/interactions modelling
- **Red flags:** Contractor postings for client-site roles; on-call

#### JPMorganChase India (T1)
- **Stack:** Pega + Java/Python/React, Oracle/Postgres, CLM/KYC, Smart Investigate
- **Hook:** VP Rohit Hundet's Sep 2026 call for 2–5 years Pega (Hyderabad/Mumbai/Bangalore)
- **Sequence:** Ashish Kumar Jha or Guna Sekhar C N → Rimjhim Srivastava → reply to Rohit Hundet's post
- **Likely deep-dive questions:** Bulk case creation at volume: data flows vs queue processors · KYC case design with controls and audit trail · Pega ↔ Java service integration patterns
- **Red flags:** Strict RTO; some 'JPMC' profiles are contractors

#### Nokia India (T3)
- **Stack:** Pega v8+, Constellation, Pega DevOps, Azure DevOps, Jira
- **Hook:** 4–7-year Pega System Architect openings; ex-CBA engineers joining 2025–26
- **Sequence:** Lavanya Bevara or Sirisha Pullagura → Vivek Kumar → Abhimanu Bhardwaj
- **Likely deep-dive questions:** Order-orchestration case design with external fulfilment systems · CI/CD for Pega with Azure DevOps · Constellation adoption plan for an existing app
- **Red flags:** Internal-IT scope; hires in bursts

#### Broadridge India (T3)
- **Stack:** Pega Infinity, Constellation, Pega GenAI, REST/SOAP/JMS, AWS
- **Hook:** Bengaluru Senior Technical Member – Pega post; team attended a Pega Infinity '26 session (Jul 2026)
- **Sequence:** Sahaja Nayuni → Ranjith Murugesan (alumnus, ask why he left) → Suresh Kathi
- **Likely deep-dive questions:** SLA and case-lifecycle tuning at high volume · JMS/messaging integration with failure handling · Where GenAI fits in Pega development
- **Red flags:** Lead in Hyderabad; a 4-month exit in 2025

#### Telstra India (T2/T3)
- **Stack:** Pega 8.x estate (~17 apps), decisioning, Process AI
- **Hook:** Pega chapter-lead change (Jun 2026)
- **Sequence:** RaviKiran Valluru or Pradeep Koutha → confirm the chapter lead → manager
- **Likely deep-dive questions:** Upgrade strategy for a long-lived estate · Performance tuning with PAL/DB tracer/alerts · Predictive models in case management (Process AI)
- **Red flags:** Upgrade/maintenance-heavy work

#### Cisco India (T1)
- **Stack:** Pega Infinity 24.1, OpenShift, Helm, externalised Kafka + Elasticsearch, CI/CD
- **Hook:** PegaWorld 2025 platform modernisation (150+ VMs → containers)
- **Sequence:** Dharani Murugan → Sumit Kumar
- **Likely deep-dive questions:** Kafka consumer behaviour and rebalancing on containerised Pega · Zero-downtime upgrade strategy · Observability for Pega on Kubernetes
- **Red flags:** Rare openings; pay

#### Siemens (T1)
- **Stack:** Pega CCMT (global collections), SAP AR integration, GenAI exploration
- **Hook:** Global collections at scale (130+ entities, 300k customers, 8M+ invoices)
- **Sequence:** Anusha G or Faizan Bhat → Amit Abhishek (LSA)
- **Likely deep-dive questions:** Collection strategy and customer-segmentation design · SAP AR integration and reconciliation · Configuring multi-country rollouts without forks
- **Red flags:** Partner co-development; check legal entity (Siemens Technology and Services)

#### John Deere India (T1)
- **Stack:** Pega Customer Service for FS, Collections framework, Pega Cloud/AWS, Deployment Manager
- **Hook:** Bengaluru AGM (ex-Pegasystems) + new Senior SE hire (Nov 2025)
- **Sequence:** MalakondaReddy Boyella → Shailendra Mishra → NITHIN TL (roadmap question only)
- **Likely deep-dive questions:** Customising the Collections framework for delinquency strategies · AWS integration patterns from Pega Cloud · OAuth/secure integration design
- **Red flags:** Coforge-staffed workstreams; Pune weighting

#### Pegasystems India (T2)
- **Stack:** Pega product (Java, React), CDH, Process AI, GenAI, Pega Cloud ops
- **Hook:** Software Engineer – GenAI Engineering (2–4 yrs, CSA/CSSA) posting; Bengaluru CDH/ML engineering managers
- **Sequence:** Ashwinraj Shekar (LSA) or a peer engineer → managers only with a requisition
- **Likely deep-dive questions:** Rule resolution and engine internals · Design a reusable product feature, not a project feature · GenAI guardrails and evaluation
- **Red flags:** Product-engineering interview bar; politics in reviews

#### Société Générale GSC (T3)
- **Stack:** Pega Infinity 24.2, Constellation, Deployment Manager, JavaScript/React
- **Hook:** Application migration/modernisation; Constellation hiring post (Jul 2024)
- **Sequence:** Sudhir Sharma or Vijendra H D → Subramanyam Kolipakula
- **Likely deep-dive questions:** Migrate a legacy UI to Constellation · Deployment Manager pipelines and branching · Onboarding product-matrix case design
- **Red flags:** Last visible hiring signal is from 2024

#### Wells Fargo India (T1)
- **Stack:** Pega 24.1.3 Workflow-as-a-Service, OAuth 2.0/JWT, Oracle + Postgres, Kafka/async, Smart Investigate
- **Hook:** WaaS platform built around exactly your stack (watch for a req)
- **Sequence:** Peers only (kopparapu suhas, Sheshachal Galagali) until a requisition appears
- **Likely deep-dive questions:** Queue processors/job schedulers at high volume · OAuth/JWT-secured Service-REST design · Smart Investigate SWIFT/Fed payment flows
- **Red flags:** Frozen hiring; old-tech complaints

## Module 4 · 7-day sprint

- At most 15 invitations a day and about 50 for the week; LinkedIn caps weekly invitations and limits personalised notes on free accounts, so check your own limits first.
- Free account with few notes left: send the invitation without a note to peers and send the scripted message after they accept. Save personalised notes for leads and managers.
- One follow-up only, 5–7 days after acceptance. No follow-up to leadership.
- Log every touch (date, person, company, script, response) in one tracker; never contact two people from the same squad on the same day.
- Do not share MBRDI-internal architecture, data or client details; talk in patterns and outcomes.

**Day 1 · Foundation:** Update headline/About to the candidate headline; add a one-page sanitised architecture note (Kafka ingestion + replay/DLQ + metadata mapping) to Featured. Apply to live roles: First Citizens SE II, Empower Developer Software, Broadridge Pega Developer, Nokia Pega SA, Pegasystems GenAI SE. Build the tracker. Invitations: 0.

**Day 2 · Tier-1 peers:** Invite 10 peers: Cisco (Dharani Murugan), Wells Fargo (kopparapu suhas), Siemens (Anusha G, Faizan Bhat), John Deere (MalakondaReddy Boyella), First Citizens (Tushar Banerjee, Nimalan Peter), CBA prep peers (Deep Shikha, Nalini Landge, Krishnachaitanya Mudragani). Comment on two relevant posts (e.g., a PegaWorld/Cisco or Kafka topic).

**Day 3 · Tier-3 peers:** Invite 10 peers: Empower (Divya Mohanraj, Nithin H N), DTICI (Sivakumar Annameti, Subiksha Ramachandran), Booking (Satish Varma Penmetsa, Vartika Tiwari), Nokia (Lavanya Bevara, Sirisha Pullagura), Broadridge (Sahaja Nayuni), Société Générale (Sudhir Sharma). Message Day-2 acceptances with the T1 peer script.

**Day 4 · Remaining peers + public post:** Invite 8: JPMC (Ashish Kumar Jha, Guna Sekhar C N), Telstra (RaviKiran Valluru, Pradeep Koutha), Pegasystems (Ashwinraj Shekar), Siemens/Cisco leads (Amit Abhishek, Sumit Kumar), DTICI (Aradhika Sinha). Reply to Rohit Hundet's Sep 2026 hiring post with a 3-line fit summary. Message Day-3 acceptances.

**Day 5 · Architect/lead layer:** Only for companies where a peer replied: invite or message 5–6 leads with one technical question each (e.g., Deepak Shahi, Nanda Kumari K B, Vivek Kumar, Shailendra Mishra, Rimjhim Srivastava).

**Day 6 · Managers with role IDs:** Send the Persona-2 script to managers whose role you applied for: Abhi Gummaraju (FCI), Ankit Punjarwar (Empower), Suresh Kathi (Broadridge), Abhimanu Bhardwaj (Nokia), Anish Kumar K P (Booking, only if a role ID exists). One Persona-3 roadmap note: NITHIN TL (John Deere). CBA: no manager contact during the interview.

**Day 7 · Review and prep:** Score the week: acceptance %, reply %, referral offers. For every company with a reply, fill the micro-dossier and prepare the three interview answers. Plan week 2: next 15 targets (Ameriprise, VOIS, Standard Chartered, BT, Sun Life, Morgan Stanley, Goldman Sachs, NatWest, Verizon, Carelon, MUFG, ANZ, BNY, Shell, Intel) and follow-ups for Day-2/3 acceptances.
