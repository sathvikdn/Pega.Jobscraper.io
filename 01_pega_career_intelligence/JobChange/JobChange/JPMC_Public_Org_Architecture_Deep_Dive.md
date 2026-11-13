# JPMorganChase Public Org and Architecture Deep Dive

## Purpose

This dossier is a public-source, interview-preparation map of JPMorganChase for a Senior Pega Developer / workflow engineering target. It brings together official JPMorganChase pages, official technology blogs, public role reposts/search snippets, and local saved career-research evidence to explain:

- How JPMorganChase is publicly organized.
- Where India technology centers fit.
- How Global Technology appears to operate from public material.
- What public sources imply about engineering architecture, developer platforms, cloud, SDLC, security and controls.
- Where Pega, Camunda, Java, payments, securities operations, marketing automation and internal workflow likely fit.
- How to speak about this architecture in an interview without claiming internal/proprietary knowledge.

This is not an internal JPMorganChase architecture document. It does not claim access to confidential system names, data models, org charts, platform diagrams, headcount by team, internal repositories, internal tooling details, or current open requisitions. Anything beyond official/public text is labelled as inference.

## Evidence grading

| Grade | Meaning | Use in interview |
| --- | --- | --- |
| A | Official JPMorganChase page, official press release, official technology blog or careers page | Safe to state as public fact. |
| B | Public job repost/search result or local saved public job description | Treat as role-content signal; verify on official careers before applying. |
| C | Public profile/search snippet or non-official aggregation | Use to guide preparation/search terms only; do not cite as firm fact. |
| D | Inference from banking architecture, Pega patterns and role signals | Phrase as “I would expect / I would confirm / a reference architecture would be...” |

## Executive takeaway

JPMorganChase is not just a bank that uses technology. Public material presents it as a global financial-services firm with one of the largest technology organizations in the world: hundreds of thousands of employees, tens of thousands of technologists, large annual technology investment, India technology centers, centralized engineering platforms, cloud modernization, automated testing/deployment, strong governance and risk-control language.

For a Senior Pega Developer, the hidden expectation is this:

> You must not sound like only a Pega rule configurator. You must sound like a workflow engineer who can place Pega inside an enterprise banking architecture: business product line, case/workflow engine, Java/API layer, Camunda/BPMN layer when present, event streams, source systems, controls, monitoring, CI/CD, cloud platform, security and production support.

The most relevant public role signals cluster around:

1. Commercial & Investment Bank workflow orchestration.
2. Securities Services Operations Transformation.
3. Payments Technology.
4. Pega + Camunda + Java engineering.
5. Consumer & Community Banking Pega marketing automation / CAMP-style technology.
6. Corporate/CAO data-solutions workflow and dashboards.

## Public organization map

### Firm-level structure

From official careers and leadership material, JPMorganChase presents these major areas:

```text
JPMorganChase
  Board of Directors
  Operating Committee
    Chairman & CEO
    Global CIO / Global Technology
    CEOs / leaders for major businesses
    CFO, CRO, COO, General Counsel, HR and corporate officers
  Business areas
    Consumer & Community Banking (CCB)
    Commercial & Investment Bank (CIB)
    Asset & Wealth Management (AWM)
    Corporate Functions
    Technology
```

### Named official operating-committee anchors

These are official public leadership-page facts, useful for orientation only:

| Area | Public leader / role | Evidence grade | Why it matters for interview context |
| --- | --- | --- | --- |
| Firm | Jamie Dimon, Chairman and CEO | A | Sets top-level firm leadership context. |
| Global Technology | Lori Beer, Global Chief Information Officer | A | Technology org is visible at operating-committee level. Senior engineering roles sit in a serious technology organization. |
| Commercial & Investment Bank | Doug Petno, Co-President of JPMorganChase and CEO of Commercial & Investment Bank | A | CIB is the most relevant business line for Pega/Camunda/Payments/Securities signals. |
| Consumer & Community Banking | Troy Rohrbaugh, Co-President and CEO of CCB | A | Relevant for CCB/CAMP/Pega marketing automation signals. |
| Asset & Wealth Management | Mary Callahan Erdoes, CEO, AWM | A | Relevant if workflow roles are wealth/advisor/client-service oriented. |
| Firm operations | Jennifer Piepszak, COO | A | Operations/control/enterprise change context. |
| Risk | Ashley Bacon, Chief Risk Officer | A | Explains risk/control emphasis in workflow automation. |
| Finance | Jeremy Barnum, CFO | A | Finance/controls/reporting context. |
| Legal | Stacey Friedman, General Counsel | A | Legal/compliance-aware workflow context. |

Do not treat this as the reporting line for a Pega squad. It is just the public top-level org context.

## Business-area structure and what it means for Pega

### Consumer & Community Banking (CCB)

Official careers description: CCB helps 94 million individuals, families and businesses grow and thrive through banking, saving, investing and more.

Likely Pega/workflow relevance:

| CCB area | Possible workflow/decisioning themes | Pega angle |
| --- | --- | --- |
| Customer servicing | Complaints, requests, disputes, account servicing, escalations | Case management, SLAs, routing, customer correspondence. |
| Marketing / customer engagement | Campaigns, treatments, eligibility, customer journeys, contact policy | Pega Marketing/CDH/NBA concepts if the role is CAMP/MarTech. |
| Digital onboarding/account opening | KYC, fraud checks, document collection, approval | Case lifecycle, integration, document/evidence, maker-checker. |
| Card/banking operations | Disputes, claims, exceptions, servicing | High-volume cases, queues, controls, audit. |
| Platform modernization | API-first services, cloud, CI/CD, observability | Pega must integrate cleanly with Java/cloud systems. |

### Commercial & Investment Bank (CIB)

Official careers description: CIB provides strategic advice, raises capital, manages risk, extends liquidity, delivers payment solutions, and safeguards assets in markets around the world.

Public investor-day search snippets and role signals show CIB-related subdomains such as Global Banking, Payments, Securities Services and Markets. Treat subdomain details as public directional evidence, not a full internal org chart.

Likely Pega/workflow relevance:

| CIB subdomain | Workflow patterns | Pega/Camunda/Java angle |
| --- | --- | --- |
| Payments | Payment repair, investigation, sanction hits, return handling, reconciliation breaks | Pega case + Java services + event streams + idempotent APIs. |
| Securities Services | Custody/client instructions, post-trade exceptions, reconciliations, asset servicing, operational controls | Pega/Appian/PowerApps/Camunda-style workflow automation; forms, approvals, audit. |
| Global Banking | Client onboarding, KYC/CLM, credit/limits workflows, document approvals | Pega CLM/KYC-style case patterns; integrations and evidence. |
| Markets | Trade exceptions, onboarding, control reviews, regulatory workflows | Controlled workflows with audit, segmentation and restricted access. |
| Operations Transformation | Replacing SOP/manual work with governed workflow products | Low-code workflow, BPMN, APIs, JIRA delivery, controls. |

CIB is the strongest match for a Senior Pega Developer with integration, Kafka, production support and banking workflow strength.

### Asset & Wealth Management (AWM)

Official careers description: AWM provides strategic solutions across the full spectrum of asset classes for individuals, advisors and institutions.

Likely Pega/workflow relevance:

| Area | Potential workflows | Pega angle |
| --- | --- | --- |
| Client onboarding | Account setup, KYC, documents, approvals | Case management, external data pages, audit. |
| Advisor/client service | Requests, maintenance, exceptions | Service case framework, correspondence, SLA. |
| Investment operations | Static data, document workflows, control reviews | Restricted roles and evidence tracking. |

No strong public Pega-specific signal was found for AWM in the current research pass; keep it as a possible but lower-confidence landing zone.

### Corporate Functions / CAO / internal operations

Official careers description: Corporate Functions collaborates with internal and external clients looking for expertise with business strategies.

Public Pega role signal: older CAO Data Solutions Pega Developer reposts mentioned data strategy/governance, Global Site Services, Supplier Services, Global Security & Investigations, Global Real Estate, Amenities Services, Global Business & Document Services and CAO Strategic Initiatives.

Likely Pega/workflow relevance:

| Function family | Workflow patterns | Pega angle |
| --- | --- | --- |
| Supplier/services | Vendor onboarding, exception handling, approvals | Case lifecycle, references, attachments, maker-checker. |
| Real estate/site services | Facilities requests, approvals, dashboards | Forms, routing, SLA, reporting. |
| Security/investigations | Restricted workflows, evidence, legal/risk handoffs | Access control, audit, restricted queues. |
| Data governance | Data-quality cases, issue remediation, stewardship | Pega as workflow/evidence layer, not data warehouse. |

## India org and technology-center map

### Official India facts

| Fact | Evidence grade | Source meaning |
| --- | --- | --- |
| JPMorganChase has corporate centers in Mumbai, Bengaluru and Hyderabad supporting global technology and business operations. | A | Official India page. |
| 2023 press release described new Mumbai and Bengaluru campuses as among the firm’s largest technology and operations centers globally. | A | Official press release. |
| 2023 press release said India had 50,000+ employees at that time supporting every division of the firm. | A | Official press release. |
| 2025 DEVUP Hyderabad blog said about one third of ~63K technologists were based in India across Mumbai, Hyderabad, Bengaluru and Pune. | A | Official technology blog. |
| DEVUP India brought 350 technologists from global technology centers; agenda covered engineering excellence, cybersecurity, cloud modernization, data and AI/ML at speed/scale. | A | Official technology blog. |

### India technology interpretation

```text
Global Technology
  India technology centers
    Mumbai
      Large technology/operations center; CIB, corporate, payments or operations teams may exist here.
    Bengaluru
      Large technology/operations center; strong public signals for Pega/Camunda/Java, Pega marketing automation, technology innovation forum.
    Hyderabad
      Global Technology Centre; DEVUP hosted here; strong developer-community signal.
    Pune
      Mentioned in DEVUP 2025 as part of India technologist footprint.
```

Do not assume a Pega team exists in all four cities. Public role signals mention Bengaluru, Mumbai and Hyderabad in different contexts, but team placement must be verified by the official requisition or recruiter.

## Global Technology public architecture signals

### What official technology sources establish

| Public signal | Evidence grade | Architecture meaning |
| --- | --- | --- |
| Technology/data operations are among the world’s largest; official technology page cites massive scale and technology investment. | A | Expect enterprise-grade engineering standards, not isolated low-code work. |
| Careers page says Technology creates solutions powered by ~65K technologists. | A | Technology is a major formal career area. |
| 2025 DEVUP page says ~63K technologists and $17B annual tech spend at that time. | A | Scale and investment are explicit. |
| Technology page says $19.8B technology investment in 2026. | A | Continuing large investment. |
| Official developer-platform blog describes JET, JPMorganChase Enterprise Toolchain, as a centralized developer platform. | A | Expect standard enterprise SDLC, toolchain gates, observability, security scans and SLO thinking. |
| EPX blog describes Engineer’s Platform & Experience building integrated, self-service internal development platform for 43,000 software engineers. | A | Engineers are expected to use internal platform/paved roads, not freestyle tooling. |
| Engineering blogs mention cloud-agnostic observability, public-cloud journey, hybrid/multi-cloud deployments and modernization. | A | Cloud and observability are part of architecture language. |
| DEVUP 2026 blog mentions AI-first mindset, cybersecurity, SDLC automation, cloud modernization, automated testing and deployment. | A | Safe deployment and automation are top engineering themes. |
| DEVUP 2026 blog mentions technology preferences, fewer choices, foundational offerings, reuse and paved-road thinking. | A | Architecture is likely standardized and opinionated. |

### Public reference architecture for JPMC engineering

This is an inferred model, not an internal diagram.

```text
BUSINESS PRODUCT LINES
  CCB | CIB | AWM | Corporate Functions
          |
          v
PRODUCT / PLATFORM SQUADS
  Product owner, engineering lead, developers, SRE/support, QA/automation, architecture, risk/control partners
          |
          v
APPLICATION LAYER
  Web/mobile/internal portals | Pega/low-code workflow | Java/Spring services | Camunda/BPMN processes | batch/event jobs
          |
          v
INTEGRATION LAYER
  REST APIs | API gateway | service-to-service auth | OAuth2/OIDC/mTLS | MQ/Kafka/event streams | file/MFT where needed
          |
          v
DATA AND SYSTEMS OF RECORD
  Customer/account/payment/securities/core systems | document stores | reference data | operational data stores | warehouse/lake
          |
          v
PLATFORM ENGINEERING
  JET / enterprise toolchain | EPX / engineer platform | CI/CD | security scanning | threat modeling | observability | SLOs
          |
          v
INFRASTRUCTURE
  Hybrid cloud | multi-cloud | private/internal platforms | Kubernetes/containerized workloads where applicable
          |
          v
CONTROL PLANE
  Risk, compliance, audit, change management, access governance, production readiness, resiliency testing
```

For interview purposes, the key point is that a Pega application must sit cleanly in the application layer and follow the platform/control-plane expectations.

## Developer platform and SDLC architecture

Official blogs give enough information to reconstruct the public SDLC philosophy.

### JET / enterprise toolchain pattern

```text
Idea / requirement
  -> design and threat-model thinking
  -> code / low-code configuration
  -> unit tests and model/rule tests
  -> component and contract tests
  -> security scans and compliance checks
  -> CI/CD pipeline
  -> canary / blue-green / feature toggle style release where applicable
  -> production validation
  -> observability and SLO monitoring
  -> auto-remediation / rollback / incident response
```

What a Pega engineer should say:

> “Even in a Pega role, I would expect the application to pass enterprise SDLC gates: guardrails, unit tests, integration/contract tests, security checks, deployment approval, monitoring and rollback planning. Low-code cannot bypass engineering controls.”

### “Paved road” architecture meaning

DEVUP 2026 public material says the firm emphasizes fewer foundational technology choices, paved roads, reuse and technology preferences.

Interview implication:

| Theme | What it means for Pega |
| --- | --- |
| Fewer choices | Do not introduce a custom integration mechanism if the firm has approved API/event patterns. |
| Paved roads | Use approved CI/CD, logging, monitoring, secrets, authentication, deployment and testing patterns. |
| Reuse | Build shared Pega components, rule frameworks, data pages and integration adapters instead of one-off case logic. |
| Standards | Align with architecture and control requirements early; avoid after-the-fact compliance retrofits. |
| AI-assisted development | AI may help delivery, but output must be validated against firm standards and governance. |

## Security, risk and controls architecture

Official business-principles material emphasizes risk discipline, governance, controls, compliance, operational excellence and acting with urgency. For workflow systems, that translates directly into architecture.

### Control expectations for workflow/Pega systems

| Control area | Architecture implementation |
| --- | --- |
| Access control | Access groups, roles, privileges, AROs, Access Deny, least privilege, service accounts separated from users. |
| Maker-checker | Separate privileges for create/submit/approve/release; no user can approve their own work where dual control applies. |
| Audit evidence | Store who, when, rule version, input snapshot, decision result, approver, external correlation ID and attachment references. |
| Change governance | Ruleset versioning, branch review, deployment gates, approval workflow, rollback plan. |
| Data protection | Mask PII/financial data in UI/logs, restrict attachments, avoid secrets in rules/logs, protect non-prod data. |
| Integration security | OAuth2/OIDC/mTLS/service-to-service auth, certificate/secrets rotation, API scope control. |
| Resilience | Timeouts, idempotency, duplicate detection, circuit-breaking/fallback, queue retry, DLQ/replay, status reconciliation. |
| Monitoring | PDC/logs/APM metrics, correlation IDs, queue depth, SLA backlog, failed connectors, broken queue items. |
| Regulatory/risk review | Risk sign-off for high-impact workflow, evidence retention, audit-ready reporting. |

## Where Pega likely fits

### Pega as workflow/case layer

In a JPMC-scale architecture, Pega should be positioned as:

```text
Pega owns:
  - Human workflow and case state
  - Assignments, work queues, urgency and SLAs
  - Forms/screens for operations users
  - Business rules that belong in workflow
  - Data pages for reading/reference integration
  - Integration orchestration around cases
  - Correspondence, attachments and audit history
  - Access control at case/action level
  - Background work tied to Pega case lifecycle

Pega should not own:
  - Core banking/payment/security master data
  - Every enterprise API
  - Heavy compute outside workflow context
  - Duplicate process state already owned by Camunda/another workflow engine
  - Enterprise data lake/warehouse responsibilities
  - Secrets management outside approved platform patterns
```

### Pega + Java + Camunda boundary

Public Software Engineer III Pega/Camunda/Java role signals are very strong. The architecture you should be ready to explain:

```text
Pega case
  -> calls Java API for domain/service operation
  -> Java API may start or interact with Camunda process
  -> Camunda executes BPMN process / external tasks / DMN decisions
  -> Java workers perform service tasks and integrations
  -> status events/callbacks update Pega case
  -> Pega shows human-visible state, assignment and evidence
```

Boundary rule:

> One platform must own the business state. If Pega owns the case, Camunda should not independently own the same case lifecycle. If Camunda owns the process, Pega should be a bounded human-work or case component. The contract must define correlation ID, status model, retry owner, timeout meaning and audit source of truth.

### Pega + event streams

Public roles mention messaging/event streams. Your own experience with Kafka/eventing is useful.

```text
External event / payment file / operation trigger
  -> event topic / queue / API intake
  -> dedupe and validation
  -> Pega case created only if human workflow needed
  -> case action produces outbound intent
  -> Queue Processor / Java worker sends update
  -> confirmation event updates case
  -> reconciliation job handles missing/late/unknown outcomes
```

Senior phrase:

> “In a bank, timeout is not automatically failure. Timeout can mean unknown outcome. I would persist outbound intent, use idempotency keys, reconcile with status events/polls and avoid blind duplicate business actions.”

## Pega-relevant project-family architecture

### 1. CIB Payments Technology

Evidence: public role reposts mention Pega Developer within CIB Payments Technology, Pega 7/8+, secure/stable/scalable products, debugging, database querying, CI/CD, resiliency and security. Public Pega/Camunda/Java roles also sit in CIB.

Likely architecture:

```text
Payment systems / network events / client inquiries
  -> API/event/file intake
  -> exception classifier
  -> Pega case: Payment Investigation / Repair / Return / Sanctions Escalation / Reconciliation Break
  -> data pages read payment status, customer profile, account status, sanctions/reference data
  -> decision table selects treatment by reason/product/market/risk/amount
  -> maker-checker or specialist review
  -> outbound repair/hold/release/update through Java/API layer
  -> confirmation event/status poll
  -> evidence package and closure
```

Case types to prepare:

| Case | Trigger | Architecture concern |
| --- | --- | --- |
| Payment repair | Validation failure or missing/invalid fields | Resubmission idempotency, approval, audit. |
| Investigation | Client/internal inquiry | Linked references, correspondence, SLA. |
| Sanctions escalation | Screening hit or fuzzy match | Restricted access, no auto-release, legal/compliance evidence. |
| Return/exception | Network/payment rail response | Reason-code treatment, cutoff clocks, fees/notifications. |
| Reconciliation break | Ledger/control mismatch | Batch/event matching, confidence score, queue routing. |

Interview line:

> “My design starts with ownership: payment system is the source of truth; Pega is the investigation and control layer. Pega stores references, decisions and evidence, while writes happen through idempotent APIs with correlation IDs and confirmation.”

### 2. Securities Services Operations Transformation

Evidence: local saved public job detail and public reposts for Operations Automation / Workflow Developer mention Securities Services Operations Transformation, Intelligent Solutions, Pega/Appian/PowerApps, Camunda/Signavio, BPMN, forms/screens, APIs, JIRA, risk/controls and compliance.

Likely architecture:

```text
SOP/manual operation
  -> process discovery / BPMN model
  -> workflow product design
  -> low-code workflow or Pega case
  -> forms/screens and validation
  -> API integration with custody/securities/document/reference systems
  -> review/approval/risk controls
  -> dashboards and backlog/SLA reporting
```

Possible workflows:

| Workflow | Why it matters | Pega pattern |
| --- | --- | --- |
| Client instruction processing | Instructions may be incomplete, time-sensitive and evidence-heavy | Intake, validation, assignment, exception path. |
| Post-trade exception | Settlement/custody issues require controlled resolution | Case state, specialist queues, SLA. |
| Reconciliation | Breaks need investigation and closure evidence | Batch intake, case per exception, root-cause tagging. |
| Corporate action support | Dates, elections, approvals and documents matter | Calendar-aware SLA and audit. |
| Static/reference data change | Incorrect data causes downstream impact | Maker-checker, effective dates, approval. |

Interview line:

> “Operations transformation is not only digitizing a form. The real value is turning an SOP into a governed workflow with validation, routing, SLA, audit, controls, exception handling and measurable backlog.”

### 3. CIB Pega + Camunda + Java workflow platform

Evidence: public Software Engineer III Pega/Camunda/Java postings mention Pega case management/workflow orchestration, rule sets, data pages, activities, integrations, Camunda BPMN/DMN/external task workers, Java/Spring Boot, REST APIs, messaging/event streams, OAuth2/OIDC and monitoring/CI-CD quality gates.

Likely architecture:

```text
Business process requirement
  -> decide platform ownership
      if human case centric -> Pega owns case; Camunda/Java provide service-process subflows
      if service-process centric -> Camunda owns BPMN; Pega handles human task/case component
  -> API contracts and status model
  -> observability/correlation
  -> deployment gates and tests across both platforms
```

What to master:

| Topic | Minimum interview depth |
| --- | --- |
| BPMN | Events, tasks, gateways, timers, subprocess, boundary error/timeout. |
| DMN | Decision tables separate from process model. |
| External task worker | Java worker pulls/handles work from Camunda and completes/fails with retry. |
| Pega data page | How Pega reads/caches external data and handles connector errors. |
| Contract testing | Verify Pega/Java/Camunda payloads and status transitions. |
| Correlation ID | Trace one business event across systems. |

### 4. CCB CAMP / Pega Marketing Automation

Evidence: public role reposts mention Product Manager - Pega, Marketing Automation in Bengaluru within CCB; another public lead role signal mentions CCB CAMP Technology, Pega 8/Pega 24, OAuth2, AWS/Kubernetes, Java/Spring Boot.

Likely architecture:

```text
Customer context / product intent / campaign objective
  -> customer data contract
  -> eligibility and policy checks
  -> action/treatment/offer configuration
  -> channel orchestration
  -> API execution and measurement
  -> governance/reporting
```

Pega concepts:

| Concept | What to know | Honest framing |
| --- | --- | --- |
| Action | What the customer may receive | Conceptual if no CDH production proof. |
| Treatment | Channel-specific presentation | Prepare examples. |
| Engagement policy | Eligibility/applicability/suitability/contact limits | Strong conceptual area. |
| Arbitration | Prioritization of eligible actions | Learn formula concept; do not overclaim. |
| Customer data | Profile/context/preferences/events | Tie to data pages/API contracts. |
| Governance | Approval, compliance and evidence around campaigns/actions | Strong workflow/control bridge. |

Interview line:

> “For marketing automation, I would separate decision policy, customer data contract and channel execution. Pega should not become an uncontrolled customer-data copy. Actions need eligibility, contact policy, explainability, API integration and audit.”

### 5. CAO / Corporate Functions / Data Solutions

Evidence: older CAO Data Solutions public repost mentions Pega architecture/features, UI/dashboard development, BPM, data modeling, SQL and large disparate datasets.

Likely architecture:

```text
Data/control issue or internal service request
  -> Pega case intake
  -> classification and ownership
  -> data page reads source/reference state
  -> approval/remediation workflow
  -> SQL/report/dashboard for operational status
  -> evidence and closure
```

Senior positioning:

> “Pega is the workflow and evidence layer for data governance. The warehouse or system of record remains the data master. Pega tracks ownership, remediation, SLA, approval and audit.”

## Full reference architecture for a JPMC-style Pega workflow product

```text
USERS / ACTORS
  Operations analysts | supervisors | risk/control | legal/compliance | product owner | support engineer | auditors

CHANNELS
  Pega internal portal / Constellation or legacy UI
  Bank internal web portal
  Email/file/API/event intake
  Reporting/dashboard views

PEGA APPLICATION
  Enterprise/framework/application rulesets
  Work classes by case type
  Data classes by reusable data object
  Case types: Payment Investigation, Repair, Reconciliation Break, Client Instruction, Data Governance Issue
  Shared frameworks:
    - intake
    - validation
    - SLA/calendar
    - routing/work queues
    - authority/maker-checker
    - correspondence
    - audit/evidence
    - integration status
    - exception/rework
  Data pages:
    - D_Customer
    - D_Account
    - D_Payment
    - D_CaseReferenceData
    - D_DocumentMetadata
    - D_UserEntitlements
  Background:
    - Queue Processors for async outbound intent
    - Job Schedulers for sweeps/reconciliation/aging
    - listeners or service APIs for inbound events/files where applicable

PROCESS / SERVICE LAYER
  Camunda BPMN process where used
  Java/Spring Boot APIs
  External task workers
  API gateway / service mesh / approved integration boundary
  Messaging/event streams

SYSTEMS OF RECORD
  Payment systems
  Securities/custody systems
  Customer/account master
  Document/attachment store
  Sanctions/fraud/risk systems
  Data warehouse/lake/reporting systems
  Reference data services

PLATFORM / OPERABILITY
  JET / enterprise toolchain
  EPX / internal engineer platform
  CI/CD gates
  Security scans and threat modeling
  Observability: logs, metrics, traces, dashboards, alerting
  SLO/error-budget style thinking
  Incident management and runbooks

CONTROL PLANE
  Access governance
  Maker-checker and segregation of duties
  Audit and evidence retention
  Change/release approval
  Risk and compliance review
  Production readiness and resiliency testing
```

## Org structure a Pega developer likely experiences

A senior Pega developer probably does not interact with the CEO-level org. The real day-to-day org may look like this:

```text
Business line / product area
  Product executive / product manager
    Product owner / business owner
      Agile squad / engineering team
        Engineering manager / lead software engineer
        Pega senior developer / SSA / LSA
        Java/Spring developer
        Camunda/BPMN developer if applicable
        QA / automation engineer
        SRE / production support partner
        Business analyst / process analyst
        Scrum master / delivery lead
      Cross-functional partners
        Architecture review
        Cyber/security
        Risk and controls
        Compliance/legal if regulated workflow
        Data owners
        API/source-system owners
        Release/change management
        Production operations
```

### Interview implication

You need to show you can collaborate across this matrix:

- With business analysts: convert SOP/business process into case lifecycle and rules.
- With Java/API teams: agree contract, timeout, status and idempotency.
- With Camunda teams: avoid double orchestration and define ownership.
- With risk/control: design maker-checker, audit, access and evidence.
- With support/SRE: add logs, dashboards, alerts and runbooks.
- With product owner: sequence thin slices and avoid overbuilding.

## What “complete architecture understanding” should sound like in interview

Use this as a 90-second architecture answer:

> “From public JPMorganChase material, I understand the firm operates at very large technology scale with global businesses like CCB, CIB, AWM and Corporate Functions, and with Global Technology providing standardized engineering platforms, toolchains, observability, automated testing, cloud modernization and strong controls. For a Pega role, I would expect Pega to sit as the workflow/case layer inside a broader enterprise architecture. In CIB payments or securities operations, Pega would own human workflow: intake, case state, assignments, SLAs, approvals, evidence and audit. Java/Spring services would own reusable APIs and domain logic; Camunda may own BPMN service orchestration where used; Kafka/MQ/event streams would handle asynchronous updates; systems of record would remain master for payment/account/security/customer data. The key senior responsibilities are boundary ownership, idempotent integration, maker-checker controls, observability, deployment gates and production support. I would confirm the team’s actual platform ownership before designing anything, because the anti-pattern is duplicate state between Pega, Camunda and services.”

## Public-source facts vs assumptions

| Topic | Publicly supported | Inferred / must confirm |
| --- | --- | --- |
| India centers | Mumbai, Bengaluru, Hyderabad official; Pune mentioned in DEVUP tech workforce context. | Which exact Pega squads sit in which city. |
| Business areas | CCB, CIB, AWM, Corporate Functions, Technology. | Detailed internal product org and reporting lines. |
| Global Technology | CIO, large technologist population, JET, EPX, cloud modernization, SDLC automation. | Actual internal tool names beyond published ones; team-specific pipelines. |
| Pega in JPMC | Public roles/reposts mention Pega in CIB, Payments, CCB marketing, CAO, Securities Services workflow. | Current active requisition availability and exact product architecture. |
| Camunda/Java | Public Pega/Camunda/Java role descriptions mention BPMN/DMN, Spring Boot, REST APIs, messaging/event streams. | Which platform owns state in a given team. |
| Cloud | Official blogs mention hybrid/multi-cloud, public-cloud journey, AWS collaboration, cloud-agnostic observability. | Exact deployment model for Pega apps. |
| Controls | Official principles emphasize risk, controls, compliance and operational excellence. | Workflow-specific control matrices and approvals. |

## Deep interview question bank

### Org and business understanding

**Q: Which JPMorganChase business line do you think this role belongs to?**

Answer:

> “I would first confirm the requisition, but public signals suggest the strongest Pega/workflow roles are in Commercial & Investment Bank, especially Payments Technology and Securities Services Operations Transformation. There are also CCB signals around Pega marketing automation/CAMP and corporate-function/CAO data-solutions signals. My preparation is strongest for CIB workflow because it matches Pega case management, integration resilience, event processing, audit and controls.”

**Q: What do you know about JPMorganChase India technology centers?**

Answer:

> “Official material says corporate centers in Mumbai, Bengaluru and Hyderabad support global technology and business operations, and an official DEVUP blog says about one third of the firm’s technologists were based in India across Mumbai, Hyderabad, Bengaluru and Pune. That tells me India teams are not peripheral support only; they are part of global engineering and operations delivery.”

### Architecture

**Q: Design a Pega workflow in JPMC’s engineering environment.**

Answer:

> “I would design Pega as the case layer and integrate through approved service/event boundaries. A case stores state, assignments, SLA, evidence and decision history. Data pages read external state. Writes go through Java/API services or approved connectors with idempotency keys and correlation IDs. Long-running operations are queued and confirmed through callback/event/status poll. CI/CD includes guardrail checks, unit tests, integration/contract tests, security scan, deployment gate and production validation. Observability tracks connector failures, queue depth, SLA backlog and business exceptions.”

**Q: How do you decide between Pega and Camunda?**

Answer:

> “If the work is human-case-centric with assignments, SLAs, UI, correspondence and evidence, Pega is a strong owner. If the work is BPMN service orchestration across Java services with external task workers and DMN decisions, Camunda may be a better process owner. In a mixed environment, I would prevent double ownership: one platform owns business state, the other participates through contracts and callbacks.”

**Q: How would you make this production-ready?**

Answer:

> “Production-ready means tested, observable, controlled and recoverable. I would define error taxonomy, retry rules, timeout handling, idempotency, duplicate detection, access controls, audit evidence, queue monitoring, alerts, runbooks, data retention and rollback. I would test downstream failure, duplicate request, partial success, timeout, unauthorized access, broken queue and late confirmation.”

### Controls and banking domain

**Q: What is the biggest risk in a payment exception workflow?**

Answer:

> “The biggest risk is an incorrect business action after an unknown outcome. If an outbound repair or hold request times out, the system may not know whether the downstream system applied it. Retrying blindly can duplicate impact. I would persist outbound intent, use idempotency and correlation IDs, check status through confirmation or polling, and route unresolved outcomes to a controlled exception queue.”

**Q: How do you design maker-checker?**

Answer:

> “I would not treat maker-checker as only routing. It needs roles, privileges, Access When/ARO logic, validation preventing self-approval, audit showing maker/checker identities, approval limits from reference data, and reports for violations. Sensitive cases also need restricted work queues and negative access testing.”

## People/networking map without overstepping

Do not scrape or mass-message people. Use public names only for orientation and use manual, selective outreach.

| Public role/person type | Public evidence | Why it matters |
| --- | --- | --- |
| Lori Beer, Global CIO | Official leadership and DEVUP quotes | Signals technology’s operating-committee importance. |
| Vibhavari Jahagirdar, Head of Global Technology for India / co-lead Global Post-trade Technology | Official DEVUP/TIF blogs | Key public India technology anchor. |
| Scot Baldry, CTO | Official DEVUP 2026 blog | Public signal for technology preferences/paved-road architecture. |
| Sri Shivananda, Head of Payments Technology at J.P. Morgan | Official DEVUP 2026 blog | Public anchor for Payments Technology relevance. |
| Sandhya Sridharan, Global Head of Engineer’s Platform and Experience | Official EPX blog | Public anchor for engineering platform/toolchain expectations. |
| Gill Haus, CIO at Chase | Official DEVUP 2026 blog | CCB/Chase technology and automated-testing/resiliency theme. |
| Donald Raab, Head of Developer Advocacy and Practices for CTO | Official DEVUP 2026 blog | Developer practices and SDLC automation theme. |
| Pega/Camunda/Payments managers/recruiters | Public role snippets/search only | Search terms for manual outreach; do not claim internal facts. |

Manual outreach question:

```text
Hi <Name>, I’m preparing for JPMorganChase senior Pega/workflow engineering roles. Public role signals point to Pega with Camunda/Java, Payments Technology and Operations Transformation. If you are open to one quick pointer, what matters most in interviews: Pega architecture depth, Java/Camunda integration, payments/securities domain, or production stability/controls?
```

## Preparation roadmap for “complete understanding”

### Week 1: Public org and product context

- Memorize business areas: CCB, CIB, AWM, Corporate Functions, Technology.
- Understand CIB: payments, securities services, markets, global banking.
- Understand India tech centers and why India is strategic.
- Prepare one “why JPMC” answer using public facts.

### Week 2: Architecture stack

- Pega case design and rule architecture.
- Java/Spring Boot REST API basics.
- Camunda BPMN/DMN/external task basics.
- OAuth2/OIDC, mTLS and service-to-service security basics.
- Kafka/MQ event-driven patterns.

### Week 3: Banking workflows

- Payment repair/investigation/reconciliation/sanctions workflow.
- Securities operations workflow: client instructions, post-trade exceptions, static data change.
- Corporate data-governance workflow.
- CCB marketing/CDH concepts.

### Week 4: Senior engineering bar

- System design whiteboarding.
- Production RCA stories.
- CI/CD, automated testing, guardrails and deployment gates.
- Controls, maker-checker, evidence, access, audit.
- Resume and LinkedIn positioning for workflow engineering.

## Final positioning statement

Use this when talking to a recruiter or interviewer:

> “I am targeting JPMorganChase because public evidence shows your Pega roles sit inside serious engineering programs: CIB Payments, Securities Services Operations Transformation, Pega plus Camunda/Java and CCB marketing automation. My core value is not just Pega configuration; it is designing workflow systems that are integrated, observable, controlled and supportable. I bring hands-on Pega case management, integrations, Kafka/event processing, queue processors, file/email listeners and production support. I am preparing specifically for your broader engineering context: Java APIs, Camunda/BPMN, CI/CD, security, cloud modernization, risk controls and operational stability.”

## Source notes

Official JPMorganChase sources used in this dossier:

- `https://www.jpmorganchase.com/careers` — business areas, employee/technologist counts, technology career framing.
- `https://www.jpmorganchase.com/about/leadership` — Board and Operating Committee, named public leaders including Global CIO and business CEOs.
- `https://www.jpmorganchase.com/communities/india` — India corporate centers and community/role context.
- `https://www.jpmorganchase.com/newsroom/press-releases/2023/jpmorgan-chase-opens-new-offices-in-mumbai-and-bengaluru` — India campus scale and 50,000+ employee context at that time.
- `https://www.jpmorganchase.com/about/technology` — technology scale, 2026 technology investment, payments/customer scale language.
- `https://www.jpmorganchase.com/careers/explore-opportunities/programs/software-engineer-cohort` — experienced software engineer expectations: system design, development, testing, operational stability, Java/Python, SDLC and Agile.
- `https://www.jpmorganchase.com/about/technology/blog/devup-hyderabad-2025` — India technologist footprint, DEVUP India, 63K technologists and $17B tech spend at publication time.
- `https://www.jpmorganchase.com/about/technology/blog/devup-hyderabad-returns-in-full-force` — AI-first, automated testing/deployment, technology preferences, paved-road/fewer-choice architecture, public names/roles.
- `https://www.jpmorganchase.com/about/technology/blog/driving-enterprise-software-delivery` — JET enterprise toolchain, DevOps, security scans, threat modeling, observability, hybrid/multi-cloud, SLOs.
- `https://www.jpmorganchase.com/about/technology/blog/our-commitment-to-the-engineer-experience` — EPX, self-service internal developer platform, cloud-agnostic observability and engineer experience.
- `https://www.jpmorganchase.com/about/business-principles` — operational excellence, risk discipline, governance, controls and compliance language.

Public role/search evidence used as role signals, not official-current-opening proof:

- Public repost/search snippets for Software Engineer III - Pega, Camunda/Java in Bengaluru/Mumbai.
- Public repost/search snippets for Pega Developer / Software Engineer II within CIB Payments Technology, Bengaluru.
- Public repost/search snippets for Product Manager - Pega, Marketing Automation in Bengaluru / CCB.
- Public repost/search snippets for Lead Software Engineer - PEGA Certified / AWS / CCB CAMP.
- Public repost/search snippets for Operations Automation Associate / Securities Services Operations Transformation Workflow Developer.
- Local saved evidence in `research/preloaded_search.json`, especially the saved public `Operations Automation Associate` role detail and the India search coverage notes.
