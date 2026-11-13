import { readFile, writeFile, readdir } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const root = dirname(fileURLToPath(import.meta.url));
const reportDate = new Date().toISOString().slice(0, 10);
const reportStamp = reportDate.replaceAll('-', '');

const aliases = new Map([
  ['booking holdings', 'booking'], ['booking holdings india', 'booking'], ['booking com', 'booking'],
  ['commonwealth bank cba', 'commonwealth bank'], ['commonwealth bank cba india', 'commonwealth bank'], ['cba', 'commonwealth bank'],
  ['first citizens india', 'first citizens bank'], ['first citizens', 'first citizens bank'],
  ['jpmorgan chase', 'jpmorganchase'], ['jpmorgan chase india', 'jpmorganchase'], ['jpmorgan chase and co', 'jpmorganchase'],
  ['anz', 'anz bank'], ['anz bank', 'anz bank'], ['citi india pega', 'citi'], ['citibank india', 'citi'], ['citi', 'citi'],
  ['vodafone vois', 'vodafone'], ['vois vodafone', 'vodafone'], ['vois', 'vodafone'], ['pegasystems india bengaluru', 'pegasystems'],
  ['john deere india jdtci', 'john deere'], ['john deere', 'john deere'], ['sun life global solutions', 'sun life'],
  ['carelon global solutions india', 'elevance health'], ['elevance carelon', 'elevance health'], ['optum unitedhealth group', 'optum'],
  ['daimler truck innovation center india dtici', 'daimler truck'], ['daimler truck innovation center india', 'daimler truck'],
  ['société générale gsc', 'societe generale'], ['societe generale gsc', 'societe generale'], ['lloyds technology centre india', 'lloyds banking'],
  ['mufg global service mufg bank', 'mufg pension and market services'], ['bny mellon india', 'bny'], ['bny', 'bny']
]);

function companyKey(value) {
  const normalized = String(value ?? '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .replace(/\([^)]*\)/g, ' ').replace(/&/g, ' and ').toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ').replace(/\b(india|bengaluru|bangalore|gcc|gsc)\b/g, ' ')
    .replace(/\s+/g, ' ').trim();
  return aliases.get(normalized) ?? normalized;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function link(url, label) {
  if (!/^https:\/\//i.test(String(url ?? ''))) return escapeHtml(label);
  return `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`;
}

async function readJson(relativePath) {
  return JSON.parse(await readFile(join(root, relativePath), 'utf8'));
}

async function latestJson(prefix) {
  const files = (await readdir(join(root, 'reports'))).filter(file => file.startsWith(prefix) && file.endsWith('.json')).sort();
  if (files.length === 0) throw new Error(`No report file found for ${prefix}`);
  const file = files.at(-1);
  return { file, data: await readJson(join('reports', file)) };
}

function extractDataArray(html) {
  const marker = 'const DATA=';
  const markerIndex = html.indexOf(marker);
  if (markerIndex < 0) return [];
  const startIndex = html.indexOf('[', markerIndex);
  if (startIndex < 0) return [];
  let depth = 0;
  let inString = false;
  let escaped = false;
  for (let index = startIndex; index < html.length; index++) {
    const char = html[index];
    if (inString) {
      if (escaped) {
        escaped = false;
      } else if (char === '\\') {
        escaped = true;
      } else if (char === '"') {
        inString = false;
      }
      continue;
    }
    if (char === '"') {
      inString = true;
      continue;
    }
    if (char === '[') depth += 1;
    if (char === ']') {
      depth -= 1;
      if (depth === 0) return vm.runInNewContext(html.slice(startIndex, index + 1), Object.create(null));
    }
  }
  return [];
}

function roleKind(job, companyId) {
  const text = `${job.title ?? ''} ${job.description ?? ''} ${job.relevance ?? ''}`;
  const reqId = job.reqId ?? '';
  if (companyId === 'commonwealth bank' && ['REQ266821', 'REQ266822'].includes(reqId)) return 'target-bengaluru-ic';
  if (companyId === 'commonwealth bank' && ['REQ266820', 'REQ266311'].includes(reqId)) return 'team-build-leadership';
  if (companyId === 'pegasystems' && /software engineer/i.test(text)) return 'target-bengaluru-ic';
  if (/quality assurance|ops support|operation|support specialist|supervisor/i.test(text)) return 'adjacent-or-non-developer';
  if (/developer|software engineer|system architect|solution architect|lead architect|application developer/i.test(text) && /\bpega\b/i.test(text)) return 'target-india-engineering';
  return 'adjacent-or-needs-review';
}

function evidenceGrade(row, allJobs, teamProfile, deepDossier, joinTiming) {
  const targetBengaluru = allJobs.some(job => job.kind === 'target-bengaluru-ic');
  const targetIndia = allJobs.some(job => job.kind === 'target-india-engineering');
  const currentAdjacent = allJobs.some(job => ['adjacent-or-non-developer', 'adjacent-or-needs-review'].includes(job.kind));
  if (targetBengaluru) return 'A1 current Bengaluru application target';
  if (targetIndia) return 'A2 current India Pega engineering target';
  if (allJobs.some(job => job.kind === 'team-build-leadership')) return 'B1 current team-build signal';
  if (row?.newTeamSignal) return 'B3 new-team hypothesis needs confirmation';
  if (currentAdjacent) return 'B2 current adjacent Pega mention';
  if (row?.historicalTeamEvidence === 'High' || teamProfile?.confidence === 'High' || deepDossier?.maturity === 'High') return 'C1 established team, no current opening verified';
  if ((joinTiming?.recentDatedPegaRoles ?? 0) > 0 || (joinTiming?.recentTeamAssociated ?? 0) > 0) return 'C2 movement/profile signal, no opening verified';
  if (/low|unproven/i.test(`${teamProfile?.confidence ?? ''} ${row?.historicalTeamEvidence ?? ''}`)) return 'D low or unproven Bengaluru Pega evidence';
  return 'C3 watchlist or unknown';
}

function jobPriority(job) {
  const order = {
    'target-bengaluru-ic': 1,
    'target-india-engineering': 2,
    'team-build-leadership': 3,
    'adjacent-or-non-developer': 4,
    'adjacent-or-needs-review': 5,
    'search-index-needs-live-confirmation': 6,
    'outside-india': 7,
    'profile-signal-no-current-india-role': 8,
    'non-pega-current-roles': 9,
    'no-live-role-found': 10
  };
  return order[job.kind] ?? 99;
}

function recordPriority(record) {
  if (record.id === 'commonwealth bank') return 1;
  if (record.id === 'pegasystems') return 2;
  if (record.id === 'citi') return 3;
  if (record.evidenceGrade.startsWith('A1')) return 4;
  if (record.evidenceGrade.startsWith('A2')) return 5;
  if (record.evidenceGrade.startsWith('B1')) return 6;
  if (record.evidenceGrade.startsWith('B3')) return 7;
  return 99;
}

function actionFor(grade, row, allJobs) {
  if (row?.id === 'commonwealth bank') return 'Apply/track REQ266821 and REQ266822 first; use leadership reqs only to understand the ASB build-out.';
  if (row?.id === 'pegasystems') return 'Apply if you want Pega product/GenAI engineering rather than a bank Customer Service delivery team.';
  if (row?.id === 'citi' && allJobs.some(job => job.reqId === '261005347')) return 'Good India-wide role, but Chennai. Use only if location flexibility is real.';
  if (row?.id === 'lloyds banking' && allJobs.some(job => job.reqId === '163071')) return 'Strong India Pega role, but Hyderabad. Use only if Hyderabad or remote/hybrid flexibility is real.';
  if (row?.newTeamSignal?.nextAction) return row.newTeamSignal.nextAction;
  if (grade.startsWith('C1')) return 'Use referral/watchlist mode; do not assume an opening until there is a first-party req ID.';
  if (grade.startsWith('C2')) return 'Ask a peer whether the movement signal created approved headcount; do not call it a vacancy.';
  if (grade.startsWith('D')) return 'Archive unless a direct official req appears.';
  return 'Monitor official careers and keep evidence as unknown, not negative.';
}

function compactPeople(topRow, deepDossier, profile) {
  const names = [];
  for (const person of topRow?.people ?? []) {
    if (person?.name) names.push(`${person.name}${person.title ? ` — ${person.title}` : ''}`);
  }
  for (const person of deepDossier?.team_members ?? []) {
    if (person?.name) names.push(`${person.name}${person.title ? ` — ${person.title}` : ''}`);
  }
  for (const person of profile?.people ?? []) {
    if (Array.isArray(person) && person[0]) names.push(`${person[0]} — ${person[1] ?? ''}`.trim());
  }
  return [...new Set(names)].slice(0, 6);
}

function compactWork(topRow, deepDossier, profile, row) {
  const items = [];
  for (const workstream of topRow?.workstreams ?? []) {
    if (Array.isArray(workstream)) items.push(`${workstream[0]}: ${workstream[1]}`);
  }
  if (deepDossier?.projects) items.push(deepDossier.projects);
  if (profile?.domains) items.push(profile.domains);
  if (row?.program) items.push(row.program);
  return [...new Set(items.map(item => String(item).replace(/\s+/g, ' ').trim()).filter(Boolean))].slice(0, 4);
}

const priorityDeepResearch = [
  {
    id: 'commonwealth bank', confidence: 'Very high', currentOpeningConclusion: 'Confirmed Bengaluru ASB build-out: Senior SWE Pega REQ266821/REQ266822 plus Pega Engineering Manager and ASB India technology leadership roles.',
    teamArchitecture: 'ASB-owned engineering outcomes delivered through CBA India squads. Public evidence points to Pega case management, integrations, security, production support, Constellation/Cloud direction, and ASB modernisation across core banking, lending, onboarding, payments and service.',
    stackVersionEvidence: 'CBA/ASB postings name Pega development, case management, integrations, security, CI/CD and Pega Cloud/Constellation expectations; ASB profile evidence also points to Pega 24.x and Constellation in parts of the estate.',
    peopleMovement: 'Profile dates are not the evidence here. The official requisition cluster is the evidence.',
    fitAction: 'Apply first. Prepare Customer Service, integration resilience, replay/dead-letter, system-of-record boundary and Constellation/Pega Cloud learning stories.',
    verificationQuestions: ['Which ASB journeys does India own first?', 'Is the role Customer Service, onboarding, lending, payments or financial crime?', 'Is the platform on Pega Cloud and which version is used by the squad?'],
    sourceLinks: ['https://cba.wd3.myworkdayjobs.com/en-US/CommBank_Careers/job/Senior-Software-Engineer_REQ266821', 'https://cba.wd3.myworkdayjobs.com/en-US/CommBank_Careers/job/Senior-Software-Engineer_REQ266822']
  },
  {
    id: 'pegasystems', confidence: 'Very high', currentOpeningConclusion: 'Confirmed official Bengaluru product-engineering role 24123 for Software Engineer, GenAI Engineering, Pega Developer CSA/CSSA.',
    teamArchitecture: 'Product/platform engineering, not client delivery. Work is on GenAI capabilities inside Pega Platform, developer assistant/agent capabilities, evaluations, observability and guardrails.',
    stackVersionEvidence: 'Official role asks 2-4 years Pega development, CSA/CSSA, Java/J2EE, Oracle/Postgres, SQL, JSP and Agile/Scrum; page frames AI maturity and responsible validation of AI outputs.',
    peopleMovement: 'Growth signal comes from Pega’s Bengaluru product presence and current official role, not profile movement.',
    fitAction: 'Apply if you want product/platform engineering. Reframe your Pega build experience toward reusable rules, quality, observability and AI-assisted developer productivity.',
    verificationQuestions: ['Which platform component owns the role?', 'How much is Pega rule-building versus Java/platform work?', 'What GenAI guardrail/evaluation work is expected from a Pega developer?'],
    sourceLinks: ['https://www.pega.com/about/careers/24123/software-engineer-genai-engineering-pega-developer-csa-cssa']
  },
  {
    id: 'citi', confidence: 'High', currentOpeningConclusion: 'Confirmed official India Pega developer role 261005347 in Chennai, not Bengaluru.',
    teamArchitecture: 'Cards/loans delinquency-management application development. The role is intermediate programmer analyst in Citi Technology, with independent issue resolution and stakeholder coaching.',
    stackVersionEvidence: 'Official page asks Advanced Pega Developer skills, CSA+, Pega 24.x/25.x, Docker/Kubernetes, VM-to-OSE/OpenShift migration, Oracle, MongoDB, prompt engineering/model integration and AI governance.',
    peopleMovement: 'No Bengaluru movement inference needed; current official Chennai req is the evidence.',
    fitAction: 'Good skill match if Chennai/hybrid is acceptable. Strong angle: delinquency workflows, integrations, containers and modern Pega versions.',
    verificationQuestions: ['Can the role be done from Bengaluru later?', 'Is it Pega Cloud, OpenShift or internal OSE?', 'Which delinquency framework/app is being modernised?'],
    sourceLinks: ['https://jobs.citi.com/job/chennai/pega-application-developer/287/102929640944']
  },
  {
    id: 'booking', confidence: 'Medium-high', currentOpeningConclusion: 'No first-party live Pega vacancy found, but strong Bengaluru team-growth evidence from public profiles and historical/newly-formed Pega Delivery Team ads.',
    teamArchitecture: 'Trips/Customer Service Pega delivery for agent-facing travel operations: booking changes, cancellations, loyalty/service requests, rental cars, Customer Service Framework, Constellation UI and backend REST/legacy integrations.',
    stackVersionEvidence: 'Public profiles and ads mention Pega Customer Service Framework, Constellation, reusable views/data pages, secure REST/SOAP integrations and Customer Decision Hub in some senior profiles.',
    peopleMovement: 'Recent profile evidence includes Pega developers/SSA/LSA in Bengaluru from 2024-2026. This is a growth signal, not proof of open headcount.',
    fitAction: 'Best non-bank Customer Service watch target. Ask a Booking peer for a direct employer req ID before treating vendor ads as permanent seats.',
    verificationQuestions: ['Are current SA/SSA seats Booking payroll or vendor payroll?', 'Which squads report to CS Tech versus Trips?', 'Is Constellation already production for agent desktop?'],
    sourceLinks: ['https://www.instahyre.com/job-297596-pega-lead-system-architect-at-booking-bangalore/']
  },
  {
    id: 'siemens', confidence: 'Medium', currentOpeningConclusion: 'Search results show official Siemens Pega architect/lead pages, but direct English/local fetches are inconsistent; one fetched official November role is operations/order workflow, not developer.',
    teamArchitecture: 'Likely Pega Nearshore Consulting / Global Business Services model for customer-facing Pega delivery and internal workflow/order processes.',
    stackVersionEvidence: 'Search snippets mention Pega Infinity, target-industry frameworks, architecture/design/delivery, guardrails and global customer consulting; operations role uses Pega as a workflow request system around SAP order handling.',
    peopleMovement: 'Use as search-index lead only until Siemens returns an applyable page.',
    fitAction: 'Do not prioritise unless you can open/apply to req 514440/523881 or get a recruiter confirmation.',
    verificationQuestions: ['Are req 514440/523881 still open?', 'Is the role developer/architect or process operations?', 'Is payroll Siemens Technology and Services?'],
    sourceLinks: ['https://jobs.siemens.com/nl_NL/externaljobs/JobDetail/523881', 'https://jobs.siemens.com/zh_CN/externaljobs/JobDetail/514440']
  },
  {
    id: 'first citizens bank', confidence: 'Medium-high historical, low current-opening', currentOpeningConclusion: 'Strong 2026 India Pega posting history, but 13 Nov official India feed had zero India Pega roles; US remote Pega roles are separate.',
    teamArchitecture: 'Deposits & Shared Services and Lending Digital Automation. Public postings describe enterprise workflow on Pega, robotics/Robot Manager, GenAI/Knowledge Buddy/Agentic AI, REST/Kafka/JMS/SOAP/microservices and production support.',
    stackVersionEvidence: 'Historic India postings cite Pega PRPC v6/v7 and Pega Infinity, banking/insurance frameworks, Okta, SQL, ServiceNow, Kafka/JMS/SOAP and microservices.',
    peopleMovement: 'Recent engineering starts exist in the ledger, but current Pega assignment is not independently established.',
    fitAction: 'Watch/referral mode. Ask directly whether the SE I/II or Lead Pega seats will reopen.',
    verificationQuestions: ['Did the Deposit & Shared Services Pega roles close or pause?', 'Is Bengaluru delivery owned by FCI or SVB/First Citizens technology?', 'Will lending automation add IC headcount?'],
    sourceLinks: ['https://jobs.firstcitizens.com/jobs/29082?lang=en-us']
  },
  {
    id: 'empower', confidence: 'Medium', currentOpeningConclusion: 'Pega 24.x/8.x production-support and developer evidence exists, but no first-party live Bengaluru req was verified in the saved official scan.',
    teamArchitecture: 'Retirement/financial services applications with 24/7 production support, incident analysis, application reliability and Pega full-stack remediation.',
    stackVersionEvidence: 'Mirrored roles mention PRPC 8.x/24.x, Pega 24.x development, Constellation architecture, REST/SOAP APIs, Agile, CSA and production support.',
    peopleMovement: 'Recent senior Pega profile movement appears in the Top-50 timing report.',
    fitAction: 'Good stability/support target if you want Pega 24.x production ownership; verify direct role status first.',
    verificationQuestions: ['Is the open work development or production support?', 'Which apps are on 24.x versus 8.x?', 'Is the role Bengaluru or broader India?'],
    sourceLinks: ['https://builtin.com/job/lead-engineer-software/6607546']
  },
  {
    id: 'daimler truck', confidence: 'Medium-high team, unknown current opening', currentOpeningConclusion: 'No current India Pega opening verified, but DTFS/DTICI has strong public transformation evidence.',
    teamArchitecture: 'Daimler Truck Financial Services transformation using Pega Blueprint, Pega-as-a-Service and cloud-native platform; DTICI profile evidence points to Bengaluru Pega Infinity/Constellation consultants.',
    stackVersionEvidence: 'PegaWorld 2026 session says legacy transformation went live in 14 weeks using Pega Blueprint, Pega-as-a-Service and cloud-native platform.',
    peopleMovement: 'Multiple 2025 DTICI senior consultant joins support a past hiring wave, not a current vacancy.',
    fitAction: 'Warm watchlist. Strong story fit if they reopen Pega consultant roles.',
    verificationQuestions: ['Is DTICI supporting DTFS Pega directly?', 'Is the new app Constellation?', 'Will 2025 consultant wave expand in Bengaluru?'],
    sourceLinks: ['https://www.pega.com/events/pegaworld/agenda/turning-legacy-light-speed-daimler-truck%E2%80%99s-14-week-transformation-pega']
  },
  {
    id: 'jpmorganchase', confidence: 'Medium-high team, low current-opening', currentOpeningConclusion: 'Established Bengaluru Pega usage in CDAO workflow, Wholesale KYC and payments technology, but no current official India Pega role verified in the saved scan.',
    teamArchitecture: 'Workflow automation hub, KYC/onboarding/client due diligence, payments technology and low-code process reengineering using Pega with enterprise SDLC/CI/CD/resiliency practices.',
    stackVersionEvidence: 'Historical/current mirrors mention CSA/CSSA, Pega 7/8+, CDAO workflow, Pega-based solutions, KYC/AML, Python/AI/ML in operations automation and enterprise databases.',
    peopleMovement: 'Existing team evidence is stronger than movement timing; movement dates are sparse.',
    fitAction: 'Referral-only unless a fresh official req appears. Your KYC/integration story fits but competition is high.',
    verificationQuestions: ['Which JPMC org owns Pega seats now: CDAO, WKO, CIB Payments or operations automation?', 'Are roles employee or contractor?', 'Which city owns the current team?'],
    sourceLinks: ['https://www.talentify.io/job/analytics-solutions-analyst-workflow-team-pega-developer-bengaluru-karnataka-jp-morgan-210546300']
  },
  {
    id: 'nokia', confidence: 'Medium-high', currentOpeningConclusion: 'Recent public hiring signal for Bengaluru Pega System Architect, but first-party req status still needs confirmation.',
    teamArchitecture: 'Agile scrum team building and enhancing Pega applications for business objectives; profiles show solution architecture, Constellation, DevOps and stakeholder-facing delivery.',
    stackVersionEvidence: 'Hiring post asks 4-7 years, Pega v8.x+, solution design, Agile, Pega DevOps/Azure DevOps/Jira, Constellation UI and CSSA as nice-to-have.',
    peopleMovement: 'Recent Bengaluru Pega System Architect join/profile signal exists, including movement from CBA.',
    fitAction: 'High-quality watch/referral target for 4-7 years. Ask for the official req link before applying.',
    verificationQuestions: ['Is the Oct hiring post still open?', 'Which Nokia business process/app uses Pega?', 'Is Constellation mandatory or nice-to-have?'],
    sourceLinks: ['https://www.mncjobsindia.com/jobs/pega-system-architect-bangalore-4519826']
  },
  {
    id: 'broadridge', confidence: 'Medium', currentOpeningConclusion: 'Recent third-party Pega Developer ads mention Bengaluru/Hyderabad, but checked employer feed had zero Pega matches; treat as unverified.',
    teamArchitecture: 'Financial-services workflow/case management, investor communications/governance/back-office systems; profiles show Bengaluru Senior Member Technical Pega roles.',
    stackVersionEvidence: 'Third-party JD asks Pega Infinity, Constellation UI, Pega GenAI, REST/SOAP APIs, Agile, CSSA preferred and financial-services domain.',
    peopleMovement: 'Short-tenure 2025 Broadridge profile suggests churn/backfill possibility, not approved headcount.',
    fitAction: 'Good skills match if direct req appears. Do not rely on mirrors without a Broadridge JR ID.',
    verificationQuestions: ['What is the official Broadridge req ID?', 'Is location Bengaluru or Hyderabad?', 'Is it product team or vendor delivery?'],
    sourceLinks: ['https://broadridge.wd5.myworkdayjobs.com/en-US/Careers']
  },
  {
    id: 'telstra', confidence: 'Medium team, low current India opening', currentOpeningConclusion: 'Established Pega chapter/profile evidence, but surfaced official Pega Infra role was Australia and removed; no current Bengaluru developer opening verified.',
    teamArchitecture: 'Pega chapter across telecom workflows and infrastructure, with AWS/container/security/authentication platform responsibilities visible in historical infra roles.',
    stackVersionEvidence: 'Historical infra role cites AWS, Docker/Kubernetes, SSO via Shibboleth/EntraID, Tomcat, PostgreSQL, security approvals and DevOps workflows.',
    peopleMovement: 'Bengaluru LSA/SSA profiles exist, but no recent official opening.',
    fitAction: 'Watch/referral. Good for platform/infrastructure Pega if India roles reopen.',
    verificationQuestions: ['Does Bengaluru own development or platform support?', 'Are Pega apps on AWS/container runtime?', 'Any India IC seats planned?'],
    sourceLinks: ['https://builtin.com/job/staff-software-engineer-pega-infra/4834399']
  },
  {
    id: 'cisco', confidence: 'High platform evidence, low opening', currentOpeningConclusion: 'No current Bengaluru Pega vacancy verified, but Cisco has one of the strongest public Pega platform-modernisation cases.',
    teamArchitecture: '30+ legacy Pega applications modernised onto container-based OpenShift architecture across sales, logistics and finance.',
    stackVersionEvidence: 'Pega official case study says Pega Infinity + OpenShift, 150+ VMs replaced, Kafka and Elasticsearch externalised, Helm charts, CI/CD, active-passive data-centre architecture, 99.99% uptime and Constellation/AI exploration.',
    peopleMovement: 'Team appears mature/stable rather than currently hiring in Bengaluru.',
    fitAction: 'Use as aspirational platform target; apply only if direct Pega/OpenShift role appears.',
    verificationQuestions: ['Is India involved in Cisco’s Pega platform team?', 'Are current openings SRE/platform or app engineering?', 'Has Constellation adoption started?'],
    sourceLinks: ['https://www.pega.com/customers/cisco-platform']
  },
  {
    id: 'anz bank', confidence: 'High recent role, status uncertain', currentOpeningConclusion: 'Recent Bengaluru SSA req 126222 is a strong signal, but official ANZ status previously showed closed; verify before applying.',
    teamArchitecture: 'Digital Sales Experience domain: platform engineering, integrations, security, operational excellence and some CDH outbound email/SMS communications.',
    stackVersionEvidence: 'Role text mentions REST APIs, SMTP, SMPP, event streams, file interfaces, authentication/authorization/access controls, data flows, NBAD, actions, treatments, outbound schedules and SendGrid.',
    peopleMovement: 'New Bengaluru Pega hiring signal, not a confirmed currently open vacancy.',
    fitAction: 'Set alerts and ask ANZ peers/recruiters whether 126222 was filled or will reopen.',
    verificationQuestions: ['Is req 126222 still open internally?', 'How much is CDH versus core Pega platform?', 'Is the team at Manyata/Acacia?'],
    sourceLinks: ['https://www.anz.com/careers/']
  },
  {
    id: 'standard chartered', confidence: 'Medium historical/recent, current uncertain', currentOpeningConclusion: '2026 Bengaluru Pega/CDH roles existed, but targeted official current search surfaced non-Pega WRB roles; status needs direct careers confirmation.',
    teamArchitecture: 'WRB decisioning, RTIM and onboarding/customer due diligence workflows. Role snippets describe Pega CDH architecture, NBA, strategies, data flows and governance.',
    stackVersionEvidence: 'Historical roles mention Pega CDH, NBAD, data flows, data sets, strategies, PEGA CSSA, Pega v8, REST/SOAP, BIX, background processing, onboarding/CDD.',
    peopleMovement: 'Corrected Top-50 ledger has one recent CDH decisioning architect profile start.',
    fitAction: 'Decisioning-heavy target. Apply only when a current SCB req is visible; otherwise network with WRB/CDH peers.',
    verificationQuestions: ['Are Band 8/Band 5 Pega roles closed?', 'Is the work CDH decisioning or core workflow?', 'Which city owns delivery?'],
    sourceLinks: ['https://jobs.standardchartered.com/content/Search-Result-Page/?market=IN']
  },
  {
    id: 'lloyds banking', confidence: 'High official India, low Bengaluru fit', currentOpeningConclusion: 'Official Lloyds Technology Centre Pega role is current in Hyderabad, not Bengaluru: Lead Software Engineer 163071 closes 29 Nov 2026.',
    teamArchitecture: 'Lloyds India technology centre supports UK digital bank transformation. Pega work includes CLM, Customer Service, Smart Disputes, cloud-based Pega applications, security, monitoring and REST APIs.',
    stackVersionEvidence: 'Official role asks CLSA/CSSA, 5+ years Pega, Pega 8.x, REST API development, cloud-based Pega applications, CLM/Customer Service/Smart Disputes, Pega Cloud, security and monitoring.',
    peopleMovement: 'Hyderabad centre is growing sharply; not a Bengaluru signal.',
    fitAction: 'Strong skill target only if Hyderabad is acceptable. Not a Bengaluru switch target.',
    verificationQuestions: ['Is remote/hybrid from Bengaluru possible?', 'Which framework is used by the team?', 'Is 163071 still open on Workday?'],
    sourceLinks: ['https://lbg.wd3.myworkdayjobs.com/en-US/Lloyds_Technology_Centre/job/Hyderabad-Knowledge-Park-Tower-2/Lead-Software-Engineer_163071']
  },
  {
    id: 'natwest group', confidence: 'Medium team, current uncertain', currentOpeningConclusion: 'Historical Bengaluru Pega Principal Engineer/KYC role and current India board has many roles, but visible official current India list did not surface Pega.',
    teamArchitecture: 'KYC/CLM Pega application, economic-crime shared services and real-time decisioning/API/microservice direction.',
    stackVersionEvidence: 'Historical role asks Pega KYC/CLM v8.x, CSSA/LSA, CI/CD, cloud, Java, JavaScript, REST, SOAP and database skills.',
    peopleMovement: 'Bengaluru Pega AVP profile evidence supports team existence.',
    fitAction: 'Watch/referral. Strong KYC fit if fresh req appears, but do not call it live now.',
    verificationQuestions: ['Is Pega KYC/CLM still hiring in Bengaluru?', 'Did R-00259128 close or move?', 'Is economic crime platform Pega or adjacent?'],
    sourceLinks: ['https://jobs.natwestgroup.com/search/jobs/in/country/india']
  },
  {
    id: 'goldman sachs', confidence: 'Medium-high team, low current Bengaluru proof', currentOpeningConclusion: 'Strong Transaction Banking Smart Investigate evidence, but current official visible Pega role is Dallas and Bengaluru signals are mirrored/recruiter posts.',
    teamArchitecture: 'TxB Ops & Sales Engineering builds workflow-driven client servicing and payment investigation capabilities using Pega Smart Investigate.',
    stackVersionEvidence: 'Role text mentions Pega Smart Investigate, payment investigation, cloud/container concepts, resilient/scalable/secure modules, product/operations/engineering collaboration.',
    peopleMovement: 'Historical/mirrored Bengaluru VP Pega Engineer signal exists; not verified as live.',
    fitAction: 'Very relevant domain but likely too senior. Watch for Associate/VP India direct roles.',
    verificationQuestions: ['Is Bengaluru TxB Pega hiring open now?', 'Are IC levels below VP available?', 'Is Smart Investigate mandatory?'],
    sourceLinks: ['https://higher.gs.com/roles/184065']
  },
  {
    id: 'morgan stanley', confidence: 'Medium-high team, low current opening', currentOpeningConclusion: 'Real Bengaluru Pega team/profile evidence for KYC, onboarding and regulatory platforms; visible job ads are old/closed.',
    teamArchitecture: 'Firm-wide BPM Community of Practice plus client onboarding/regulatory workflows. Pega is used for workflow implementations across technology teams.',
    stackVersionEvidence: 'Profile evidence mentions Pega v7-v24, Constellation UI, Cosmos UI, data model design, integrations, background processing, performance optimisation and production issue resolution.',
    peopleMovement: 'Senior Bengaluru Pega profiles are active, but no current official opening was verified.',
    fitAction: 'Referral-only. Strong domain fit but wait for fresh req.',
    verificationQuestions: ['Is BPM CoP still hiring in Bengaluru?', 'Which platforms are moving to v24/Constellation?', 'What level fits 4-5 years?'],
    sourceLinks: ['https://www.instahyre.com/job-126010-pega-developer-at-morgan-stanley-bangalore/']
  },
  {
    id: 'vodafone', confidence: 'Medium-high team, low current opening', currentOpeningConclusion: 'VOIS has strong Pega/CDH team evidence and 2024-2025 hiring posts, but no fresh official req was verified in this pass.',
    teamArchitecture: 'Telecom CDH/decisioning and always-on marketing, omnichannel offer orchestration, order/customer journeys and Pega delivery across Pune/Bangalore.',
    stackVersionEvidence: 'Public posts mention Pega CDH developers/architects/testers, NBA decisioning, engagement policies, customer offer orchestration, SOAP/REST, Kafka/SSO/email in related decisioning roles.',
    peopleMovement: 'Profiles show Bengaluru CDH managers and decisioning architects.',
    fitAction: 'Good CDH target if you want decisioning; less direct Customer Service fit unless the role is core Pega workflow.',
    verificationQuestions: ['Is there a current Bangalore opening?', 'Is it CDH developer, tester or architect?', 'Which European operator/business unit is served?'],
    sourceLinks: ['https://www.linkedin.com/feed/update/urn:li:activity:7272608082118000642']
  },
  {
    id: 'sun life', confidence: 'Medium', currentOpeningConclusion: 'Strong 2025 Bengaluru/Gurugram Pega hiring signal and current profile movement, but no official current Bengaluru developer req verified.',
    teamArchitecture: 'Insurance/financial-services digital team using Pega development, APIs, integrations, JavaScript, listeners and email channels; LSA roles for large-scale implementations.',
    stackVersionEvidence: 'Hiring posts mention Pega PRPC v7/v8, Pega API, JavaScript API, integrations, listeners, email channel, CSA/CSSA/LSA and Customer Service Framework as recommended in LSA role.',
    peopleMovement: 'Corrected ledger shows a recent senior Pega specialist start.',
    fitAction: 'Good watch target; verify whether current role is Bengaluru or Gurugram and IC versus LSA.',
    verificationQuestions: ['Are Bengaluru developer roles still open?', 'Is Customer Service Framework used?', 'What Pega version is active?'],
    sourceLinks: ['https://www.linkedin.com/posts/rahul-khanna-32b910212_hiring-pegadeveloper-pegalsa-activity-7336278523155779586-Q949']
  },
  {
    id: 'shell', confidence: 'Medium-high team, low current opening', currentOpeningConclusion: 'Mature Bengaluru Pega CoE/platform profile evidence; current official openings were not verified.',
    teamArchitecture: 'BPM/CRM applications integrating with mainframe, web and client/server legacy systems; Pega platform/CoE leadership.',
    stackVersionEvidence: 'Historical Shell role asks Pega PRPC v8.x, CSA/CSSA, BPM/CRM suite, integrations with supporting applications, demos, POCs and reusable enterprise rules/workflows.',
    peopleMovement: 'Profile evidence shows a Bengaluru Pega CoE/platform lead from Pegasystems.',
    fitAction: 'Strong established-team watchlist. Apply only with direct Shell req.',
    verificationQuestions: ['Is the Bengaluru CoE hiring now?', 'Which business process is on Pega?', 'Is version v8.x or later?'],
    sourceLinks: ['https://jobs.allyenergy.com/jobs/Full-time/Technical-Lead---PEGA/251399']
  },
  {
    id: 'elevance health', confidence: 'Medium', currentOpeningConclusion: 'Carelon has healthcare Pega job/profile signals for Bengaluru/Gurugram, but first-party current Pega req was not verified in the official scan.',
    teamArchitecture: 'Healthcare claims/payment-integrity/benefits technology, in-house claims processing and operational process simplification.',
    stackVersionEvidence: 'Mirrors mention Pega PRPC 7.1+, CSA, Agile/Waterfall, shifts/support, healthcare claims processing, SQL/Java nice-to-have and PEGA-Senior Software Engineer business Health Benefits Technology.',
    peopleMovement: 'Large India GCC growth supports watchlist but not specific Pega headcount.',
    fitAction: 'Good healthcare workflow target; verify official Carelon JR ID and city.',
    verificationQuestions: ['Is JR148317 still open?', 'Is the role Bengaluru or Gurugram?', 'Is the work claims, payment integrity or benefits?'],
    sourceLinks: ['https://jobs.carelonglobal.com/in/jobs']
  },
  {
    id: 'optum', confidence: 'Medium', currentOpeningConclusion: 'Optum has current-looking Hyderabad Pega developer mirrors and Bengaluru profile signal, but no current Bengaluru official req was verified.',
    teamArchitecture: 'Healthcare Pega applications for case management, workflow, integrations and GenAI/Constellation in next-generation applications.',
    stackVersionEvidence: 'Mirrors mention Pega CSSA, Pega integrations REST/SOAP, case management/BPM/workflow, Pega Constellation UI, GenAI, PostgreSQL and Pega Infinity.',
    peopleMovement: 'Bengaluru SSE Pega profile signal exists from Dec 2025.',
    fitAction: 'Use as India-wide healthcare Pega watchlist; Bengaluru status is weak.',
    verificationQuestions: ['Is current role Hyderabad-only?', 'Are Bengaluru Pega teams hiring?', 'Is Constellation production or desired?'],
    sourceLinks: ['https://builtin.com/job/software-engineer-pega-developer/11212240']
  },
  {
    id: 'wells fargo', confidence: 'Medium adjacent', currentOpeningConclusion: 'Current signal is Hyderabad QA/payments role mentioning PEGA/Smart Investigate, not a Bengaluru developer opening.',
    teamArchitecture: 'Payments testing and payment investigations around ACI, Volante, SWIFT, PEGA/Smart Investigate and automation frameworks.',
    stackVersionEvidence: 'QA role mentions Playwright, Selenium Java, Jenkins, payment investigations, wire/ACH/real-time payments and PEGA/Smart Investigate. Separate mirrors mention Pega 8.x/24.x, Constellation, Cosmos UI, DXAPI, GenAI and Pega Cloud.',
    peopleMovement: 'No actionable Bengaluru developer movement established.',
    fitAction: 'Skip unless you are open to Hyderabad or QA/automation.',
    verificationQuestions: ['Is there a developer role separate from QA?', 'Is Smart Investigate used by India engineering?', 'Which city owns Pega delivery?'],
    sourceLinks: ['https://www.qarera.com/job/2836092']
  },
  {
    id: 'bt group', confidence: 'Medium team, low current opening', currentOpeningConclusion: 'BT has Bengaluru Pega CoE/team evidence, but visible hiring posts are historical/profile-based.',
    teamArchitecture: 'BT Pega Centre of Excellence for digital transformation, with certified software engineers/developers and business architects across Bengaluru/Gurugram.',
    stackVersionEvidence: 'Profiles mention Pega Infinity 24.2, v8.6/v8.8.5, upgrade work from 8.3.3 to 8.6.2, reusable components and application/database maintenance.',
    peopleMovement: 'Multiple Bengaluru Pega developer profiles from 2022-2024 support established team.',
    fitAction: 'Established-team referral target, not new hiring wave.',
    verificationQuestions: ['Is the CoE hiring in Bengaluru now?', 'Which BT transformation programme owns Pega?', 'Is latest version 24.2 in production?'],
    sourceLinks: ['https://www.linkedin.com/posts/anand-singh-55a77124_digitaltransformation-pegajobs-pegasystems-activity-7125449854490681345-vVUG']
  },
  {
    id: 'verizon', confidence: 'Medium-high team, low current Bengaluru opening', currentOpeningConclusion: 'Verizon has Bengaluru Pega/CDH history and Hyderabad Emerging Commercial Platforms signal; no current official Bengaluru Pega opening verified.',
    teamArchitecture: 'Pega Community of Practice for omni/customer-centric experiences, commercial platforms and decisioning/CDH.',
    stackVersionEvidence: 'Public posts mention Pega 8.x, branch development, CI/CD, SOAP/REST, Kafka, SSO, email, Cloud deployment, CSSA/LSA; Hyderabad role mentions Pega CoP and large enterprise systems.',
    peopleMovement: 'Potential leaver/backfill signal exists from historical ledger, but not vacancy proof.',
    fitAction: 'Watch/referral only. Decisioning role may require more CDH depth.',
    verificationQuestions: ['Are current roles Bengaluru or Hyderabad?', 'Is work CDH decisioning or core workflow?', 'Any 4-7 year roles open now?'],
    sourceLinks: ['https://jobs.weekday.works/verizon-principle-engineer---emerging-commercial-platforms-(pega)']
  },
  {
    id: 'societe generale', confidence: 'Medium current mirror, official unverified', currentOpeningConclusion: 'Current-looking Bengaluru Specialist Software Engineer - PEGA mirrors exist, but first-party official status was not verified here.',
    teamArchitecture: 'Investment-banking/software engineering Pega work with code, test scenarios, reusable clean code, release validations, metadata/data pipeline standards and quality automation.',
    stackVersionEvidence: 'Mirrored JD asks PEGA CSSA certification, software lifecycle/design principles, test/defect reporting, scripts/configuring quality and investment-banking domain understanding.',
    peopleMovement: 'Older recruiter posts show long-running Bengaluru Pega hiring history.',
    fitAction: 'Potentially relevant but verify on SocGen careers before applying.',
    verificationQuestions: ['What is the official SocGen req ID?', 'Is it developer or QA/validation heavy?', 'Is one-year tenure text a contract indicator?'],
    sourceLinks: ['https://www.simplyhired.co.in/job/UD8_6r9-MIFyCae-dhTvkSXmsNtsaC2l4vdPdqdg3HG1Ujr5N2MqOw']
  },
  {
    id: 'mufg global service', confidence: 'Medium-high team, low current opening', currentOpeningConclusion: 'Bengaluru Pega team/profile evidence is strong; current opening evidence is not first-party verified in this pass.',
    teamArchitecture: 'MUFG PMS/Global Service uses Pega as workflow-management tool for retirement solutions and global business-process optimisation; bank profiles show workflow applications and production support.',
    stackVersionEvidence: 'Profile evidence names Pega PRPC 8.7 and 8.8.2, FileNet, Java, Linux, SQL, Jenkins, production/pre-production monitoring, cloud basics and workflow/business-process flows.',
    peopleMovement: 'Active Bengaluru Pega senior analyst/AVP profiles support established team.',
    fitAction: 'Good BFS workflow target if a direct MUFG req appears.',
    verificationQuestions: ['Is the active opening MUFG Bank or MUFG Pension Market Services?', 'Bengaluru or Mumbai?', 'Which Pega version is production?'],
    sourceLinks: ['https://www.instahyre.com/job-185136-senior-analyst-pega-developer-at-mufg-bangalore/']
  },
  {
    id: 'paypal', confidence: 'Medium team, low current opening', currentOpeningConclusion: 'PayPal has India Pega CPM/Compass profile evidence but no current Pega vacancy on PayPal’s India role list surfaced.',
    teamArchitecture: 'Compass call-centre/customer-process tool built on Pega CPM to support agents handling account queries/issues and reduce interaction time.',
    stackVersionEvidence: 'Profile evidence mentions Pega CPM Framework and payment/call-center domain; official PayPal India careers currently show broad software roles, not Pega.',
    peopleMovement: 'Pega profile is Chennai-heavy, with PayPal India tech centres in Chennai and Bengaluru.',
    fitAction: 'Low priority unless direct Pega role appears; generic software roles do not use your Pega edge.',
    verificationQuestions: ['Is Compass still Pega-based?', 'Any Bengaluru team ownership?', 'Are current openings generic Java/backend only?'],
    sourceLinks: ['https://careers.pypl.com/locations/india/']
  },
  {
    id: 'mastercard', confidence: 'Medium domain, low direct Pega opening', currentOpeningConclusion: 'Mastercard has dispute-lifecycle product signals, but visible Pega Smart Dispute/Investigate roles are mostly vendor or adjacent, not direct Mastercard Bengaluru Pega jobs.',
    teamArchitecture: 'Dispute Lifecycle Solutions and global/regional dispute processing; Pega Smart Disputes domain is relevant but direct ownership in India is not established.',
    stackVersionEvidence: 'Adjacent roles mention Smart Disputes/Smart Investigate, card-network dispute rules, chargeback lifecycle, REST/SOAP, Queue Processors, Job Schedulers and PDC/Pega logs.',
    peopleMovement: 'No reliable Bengaluru Mastercard Pega movement established.',
    fitAction: 'Domain-adjacent watchlist only. Do not treat vendor Smart Dispute jobs as Mastercard openings.',
    verificationQuestions: ['Does Mastercard India use Pega internally for disputes?', 'Are Pega roles direct or vendor-supported?', 'Is Pune product role technical PM only?'],
    sourceLinks: ['https://mastercard.wd1.myworkdayjobs.com/en-US/CorporateCareers/job/Lead-Product-Manager-Technical--Dispute-Lifecycle-Solutions-_R-288290']
  },
  {
    id: 'dell', confidence: 'Low Pega', currentOpeningConclusion: 'Dell has many Bengaluru software roles, but no meaningful Pega opening/team signal in this pass.',
    teamArchitecture: 'Large Bengaluru technology organisation, but Pega ownership not established.',
    stackVersionEvidence: 'Official Dell Bengaluru listing shows generic software/IAM/data-science/cyber roles, not Pega.',
    peopleMovement: 'No current Pega movement signal established.',
    fitAction: 'Archive for Pega switch unless a direct Pega req appears.',
    verificationQuestions: ['Any internal Pega workflow platform?', 'Any Pega keyword on Dell official jobs?', 'Is evidence only generic CRM/customer support?'],
    sourceLinks: ['https://jobs.dell.com/en/location/bengaluru-karnataka-india-jobs/375-5787/1269750-1267701-1277331-1277333/4']
  },
  {
    id: 'walmart global tech', confidence: 'Low Pega', currentOpeningConclusion: 'Large Bengaluru tech hiring, but no direct Pega evidence found; ServiceNow appears more relevant for enterprise workflow.',
    teamArchitecture: 'Enterprise Business Services and service operations exist, but visible workflow technology is ServiceNow, not Pega.',
    stackVersionEvidence: 'Search surfaced ServiceNow developer and generic engineering roles; no Pega role verified.',
    peopleMovement: 'No Pega-specific movement signal established.',
    fitAction: 'Archive for Pega-specific search.',
    verificationQuestions: ['Does EBS use Pega anywhere?', 'Are any Pega keyword roles on official careers?', 'Is this only a generic product-tech target?'],
    sourceLinks: ['https://tech.walmart.com/content/walmart-global-tech/en_us.html']
  },
  {
    id: 'fidelity investments', confidence: 'Low direct Pega, medium adjacent', currentOpeningConclusion: 'No direct Fidelity Pega role found; surfaced Pega CDH roles are vendor/consulting or generic asset-management Java/AWS roles.',
    teamArchitecture: 'Fidelity India has strong asset-management technology teams, but direct Pega ownership is unproven in this pass.',
    stackVersionEvidence: 'Official Fidelity role found is Full Stack Engineer Java/AWS for Asset Management data platform; Pega CDH hits belong to Cognizant/Deloitte/InCrest, not Fidelity direct.',
    peopleMovement: 'No reliable Fidelity Bengaluru Pega movement established.',
    fitAction: 'Do not prioritise for Pega unless direct req appears.',
    verificationQuestions: ['Any internal Pega platform in Fidelity India?', 'Is asset-management CDH work vendor-delivered?', 'Any Bengaluru Pega profiles on payroll?'],
    sourceLinks: ['https://jobs.fidelity.com/in/jobs/2138085/full-stack-engineer-java-aws/']
  }
];

const deepResearchMap = new Map(priorityDeepResearch.map(item => [item.id, item]));

function defaultDeepResearch(id, grade, allJobs, work, timing, row) {
  const currentRoles = allJobs.filter(job => job.kind !== 'no-live-role-found');
  const roleText = currentRoles.length ? currentRoles.slice(0, 2).map(job => `${job.title}${job.reqId ? ` ${job.reqId}` : ''} in ${job.location ?? 'unknown location'}`).join('; ') : 'No current official Pega role captured in the supported feeds.';
  const movement = timing ? `${timing.recentDatedPegaRoles} recent Pega-labelled and ${timing.recentTeamAssociated} team-associated starts in the corrected profile ledger; this is not a hiring census.` : 'No corrected recent-start signal available.';
  return {
    confidence: grade.startsWith('D') ? 'Low' : grade.startsWith('C3') ? 'Unknown' : 'Medium',
    currentOpeningConclusion: roleText,
    teamArchitecture: work[0] ?? row?.program ?? 'No verified Bengaluru Pega workstream in the project evidence.',
    stackVersionEvidence: currentRoles[0]?.evidence ?? 'No public Pega version/stack evidence captured beyond the portfolio ledger.',
    peopleMovement: movement,
    fitAction: actionFor(grade, row, allJobs),
    verificationQuestions: ['Confirm a first-party requisition ID before applying.', 'Confirm Bengaluru ownership and direct payroll.', 'Confirm Pega version/framework and whether the role is developer, support, QA or operations.'],
    sourceLinks: [row?.careerUrl].filter(Boolean)
  };
}

try {
  const product = await readJson('reports/product_200_openings_watch_2026-11-12.json');
  const top50 = await readJson('bengaluru_top50_2026-11.json');
  const joinTiming = await readJson('reports/bengaluru_join_timing_2026-11.json');
  const gccProfiles = await readJson('bengaluru_gcc_profiles_2026-11.json');
  const teamInsider = await readJson('team_insider_2026-11.json');
  const newTeam = await readJson('reports/product_200_new_team_evidence_2026-11-12.json');
  const extra = await readJson('reports/product_200_extra_official_checks_2026-11-12.json');
  const { file: workdayFile, data: workday } = await latestJson('workday_pega_openings_');
  const deepDossiers = extractDataArray(await readFile(join(root, 'JobChange', 'Pega_Deep_Dossiers.html'), 'utf8'));

  const topMap = new Map(top50.companies.map(company => [companyKey(company.company), company]));
  const timingMap = new Map(joinTiming.companies.map(company => [companyKey(company.company), company]));
  const profileMap = new Map(gccProfiles.profiles.map(profile => [companyKey(profile.company), profile]));
  const insiderMap = new Map(teamInsider.companies.map(company => [companyKey(company.name), company]));
  const dossierMap = new Map(deepDossiers.map(company => [companyKey(company.name), company]));
  const workdayMap = new Map(workday.results.map(result => [companyKey(result.label), result]));
  const extraMap = new Map(extra.checks.map(check => [companyKey(check.label), check]));

  const manualOfficialFindings = [
    {
      id: 'citi', company: 'Citi India', title: 'Pega Application Developer', reqId: '261005347', location: 'Chennai, Tamil Nadu, India',
      posted: '2026-11-06', url: 'https://jobs.citi.com/job/chennai/pega-application-developer/287/102929640944', kind: 'target-india-engineering',
      evidence: 'Citi official page fetched on 13 Nov. Requires 4-6 years application development, Advanced Pega Developer skills, CSA+, Pega 24.x/25.x, delinquency management in cards/loans, Docker/Kubernetes, Oracle/MongoDB.'
    },
    {
      id: 'siemens', company: 'Siemens', title: 'Process Expert - Marcom, Sales and Delivery Services', reqId: '528370', location: 'Bangalore, Karnataka, India',
      posted: '2026-11-10', url: 'https://jobs.siemens.com/en_US/externaljobs/JobDetail/528370', kind: 'adjacent-or-non-developer',
      evidence: 'Siemens official page fetched on 13 Nov. Operations/order-management role that creates SAP orders and initiates Pega workflow requests; not a Pega developer role.'
    },
    {
      id: 'siemens', company: 'Siemens', title: 'Lead System Architect - R & D / Senior Lead Software Developer', reqId: '514440 / 523881', location: 'Bengaluru, Karnataka, India',
      posted: '2026-07-22 / 2026-09-30', url: 'https://jobs.siemens.com/en_US/externaljobs/SearchJobs?searchBy=pega', kind: 'search-index-needs-live-confirmation',
      evidence: 'Search result snippets show official Siemens Pega architect/lead pages, but direct English job-detail fetch returned 404 on 13 Nov. Treat as historical/search-index evidence until Siemens search returns an applyable page.'
    },
    {
      id: 'first citizens bank', company: 'First Citizens Bank', title: 'Senior/Lead/Business Systems Analyst Pega roles', reqId: '29082 / 29387 / 29821', location: 'US remote / multiple US locations',
      posted: null, url: 'https://jobs.firstcitizens.com/jobs/29082?lang=en-us', kind: 'outside-india',
      evidence: 'Official First Citizens search results show US remote Pega roles. The India Workday feed has zero India Pega roles in the 13 Nov scan.'
    },
    {
      id: 'lloyds banking', company: 'Lloyds Technology Centre India', title: 'Lead Software Engineer', reqId: '163071', location: 'Hyderabad Knowledge Park Tower 2, India',
      posted: '2026-09-03', url: 'https://lbg.wd3.myworkdayjobs.com/en-US/Lloyds_Technology_Centre/job/Hyderabad-Knowledge-Park-Tower-2/Lead-Software-Engineer_163071', kind: 'target-india-engineering',
      evidence: 'Lloyds official Workday search result fetched on 13 Nov. Current to 29 Nov 2026; asks CLSA/CSSA, 5+ years Pega, Pega 8.x, REST APIs, cloud-based Pega applications, CLM, Customer Service, Smart Disputes, Pega Cloud, security and monitoring. Hyderabad, not Bengaluru.'
    },
    {
      id: 'standard chartered', company: 'Standard Chartered', title: 'Current Bangalore WRB roles found in targeted search', reqId: '65004 / 65722 / 64381', location: 'Bangalore, India',
      posted: '2026-11', url: 'https://jobs.standardchartered.com/content/Search-Result-Page/?market=IN', kind: 'non-pega-current-roles',
      evidence: 'Targeted official search surfaced Java/cards/Camunda roles, not Pega developer seats. Earlier Pega/CDH roles remain historical unless a current req is found.'
    },
    {
      id: 'booking', company: 'Booking Holdings India', title: 'Booking careers engineering pages', reqId: null, location: 'Bengaluru listed as office, no Pega role surfaced',
      posted: null, url: 'https://careers.booking.com/teams/engineering/', kind: 'no-live-role-found',
      evidence: 'Booking official careers pages loaded through search results, but no employer-hosted Pega vacancy surfaced. Profile growth remains a team signal, not a live opening.'
    },
    {
      id: 'john deere', company: 'John Deere India', title: 'Bengaluru profile signal; US Pega role removed', reqId: '2026005', location: 'Bengaluru profile evidence; removed US role',
      posted: null, url: 'https://builtin.com/job/2026005-pega-software-engineer/8663584', kind: 'profile-signal-no-current-india-role',
      evidence: 'Search shows a Bengaluru John Deere CSSA profile, but the surfaced official Pega Software Engineer role is US and removed. No current Bengaluru Pega requisition established.'
    }
  ];

  const byIdManual = new Map();
  for (const finding of manualOfficialFindings) {
    const values = byIdManual.get(finding.id) ?? [];
    values.push(finding);
    byIdManual.set(finding.id, values);
  }

  const records = product.records.map(row => {
    const id = row.id;
    const topRow = topMap.get(id);
    const timing = timingMap.get(id);
    const profile = profileMap.get(id);
    const insider = insiderMap.get(id);
    const dossier = dossierMap.get(id);
    const workdayResult = workdayMap.get(id);
    const extraResult = extraMap.get(id);
    const workdayJobs = (workdayResult?.jobs ?? []).map(job => ({
      title: job.title, reqId: job.reqId, location: job.location, posted: job.startDate ?? job.posted ?? null, closes: job.endDate ?? null,
      url: job.url, kind: roleKind(job, id), evidence: String(job.description ?? '').slice(0, 420)
    }));
    const extraJobs = (extraResult?.jobs ?? []).map(job => ({
      title: job.title, reqId: job.reqId, location: job.location, posted: job.posted ?? null, closes: job.closes ?? null,
      url: job.url, kind: roleKind(job, id), evidence: job.relevance ?? ''
    }));
    const manualJobs = (byIdManual.get(id) ?? []).map(job => ({
      title: job.title, reqId: job.reqId, location: job.location, posted: job.posted, closes: null, url: job.url, kind: job.kind, evidence: job.evidence
    }));
    const allJobs = [...workdayJobs, ...extraJobs, ...manualJobs].sort((left, right) => jobPriority(left) - jobPriority(right));
    const grade = evidenceGrade(row, allJobs, profile, dossier, timing);
    const people = compactPeople(topRow, dossier, profile);
    const work = compactWork(topRow, dossier, profile, row);
    return {
      index: row.index, id, company: row.company, top50Rank: row.top50Rank, evidenceGrade: grade,
      officialSearchStatus: workdayResult ? `${workdayResult.status}${workdayResult.boardSize ? ` · board ${workdayResult.boardSize}` : ''}` : row.scanStatus,
      officialRoles: allJobs, currentAction: actionFor(grade, row, allJobs),
      teamEvidence: row.historicalTeamEvidence, teamSummary: topRow?.oneLine ?? insider?.what_they_build ?? dossier?.projects ?? row.program,
      workstreams: work, peopleCount: topRow?.people?.length ?? dossier?.team_members?.length ?? profile?.people?.length ?? 0,
      keyPeople: people, recentProfileStarts: timing ? {
        explicitlyPega: timing.recentDatedPegaRoles, teamAssociated: timing.recentTeamAssociated,
        starts: timing.recentStarts.map(start => `${start.name} (${start.month} ${start.year}, ${start.category})`)
      } : null,
      newTeamSignal: newTeam.signals.find(signal => signal.id === id) ?? null,
      deepResearch: deepResearchMap.get(id) ?? defaultDeepResearch(id, grade, allJobs, work, timing, row),
      fit: row.fit, careerUrl: row.careerUrl, sources: [row.careerUrl, ...(topRow?.sources ?? []).map(source => source[1]).filter(Boolean)].filter(Boolean).slice(0, 8)
    };
  });

  const summary = {
    generatedAt: new Date().toISOString(), reportDate, workdayFile, workdayScannedAt: workday.scannedAt,
    portfolio: {
      accounts: records.length, deepDossiers: deepDossiers.length, deepDossierPeople: deepDossiers.reduce((sum, company) => sum + (company.team_members?.length ?? 0), 0),
      top50Companies: top50.companies.length, top50People: top50.companies.reduce((sum, company) => sum + (company.people?.length ?? 0), 0),
      gccProfiles: gccProfiles.profiles.length
    },
    gradeCounts: records.reduce((counts, record) => ({ ...counts, [record.evidenceGrade]: (counts[record.evidenceGrade] ?? 0) + 1 }), {}),
    keyConclusion: 'CBA/ASB remains the only confirmed Bengaluru new-team requisition cluster. Pegasystems has a live Bengaluru product-engineering role. Citi and Lloyds have current official India Pega roles outside Bengaluru. Booking, Nokia, ANZ, Siemens, First Citizens, DTICI, Standard Chartered and others are deep-research watch targets, not verified live Bengaluru developer openings.'
  };

  const jsonOutput = { ...summary, manualOfficialFindings, priorityDeepResearch, records };
  const jsonPath = join(root, 'reports', `portfolio_company_research_${reportStamp}.json`);
  await writeFile(jsonPath, JSON.stringify(jsonOutput, null, 2), 'utf8');

  const topActions = records.filter(record => /^A|^B1|^B3/.test(record.evidenceGrade))
    .sort((left, right) => recordPriority(left) - recordPriority(right) || left.index - right.index)
    .slice(0, 18);
  const mdRows = records.map(record => `| ${record.index} | ${record.company.replaceAll('|', '\\|')} | ${record.evidenceGrade.replaceAll('|', '\\|')} | ${record.officialRoles.slice(0, 3).map(job => `${job.title}${job.reqId ? ` ${job.reqId}` : ''} (${job.location})`).join('<br>') || '—'} | ${record.deepResearch.currentOpeningConclusion.replaceAll('|', '\\|')} | ${record.peopleCount} | ${record.recentProfileStarts ? `${record.recentProfileStarts.explicitlyPega} Pega, ${record.recentProfileStarts.teamAssociated} associated` : 'not assessed'} | ${record.currentAction.replaceAll('|', '\\|')} |`);
  const priorityDiveRows = records.filter(record => deepResearchMap.has(record.id)).map(record => `| ${record.company.replaceAll('|', '\\|')} | ${record.deepResearch.confidence.replaceAll('|', '\\|')} | ${record.deepResearch.currentOpeningConclusion.replaceAll('|', '\\|')} | ${record.deepResearch.teamArchitecture.replaceAll('|', '\\|')} | ${record.deepResearch.stackVersionEvidence.replaceAll('|', '\\|')} | ${record.deepResearch.fitAction.replaceAll('|', '\\|')} |`);
  const markdown = `# Complete Pega portfolio research refresh - ${reportDate}\n\n## Bottom line\n\n${summary.keyConclusion}\n\n## Source reconciliation\n\n- Current source of truth: \`Pega_Career_Intelligence_Hub.html\` in this project folder, plus \`JobChange/Pega_Deep_Dossiers.html\`.\n- Old linked hub at \`C:/Users/DNSATHV/Desktop/JobChange/JobChange/Pega_Career_Intelligence_Hub.html#movement-radar\` is retained as an August historical movement snapshot, not a live hiring feed.\n- Deep dossiers parsed: ${summary.portfolio.deepDossiers} companies and ${summary.portfolio.deepDossierPeople} profiled people.\n- Top-50 Bengaluru ledger parsed: ${summary.portfolio.top50Companies} companies and ${summary.portfolio.top50People} public-profile rows.\n- 200-account watch parsed: ${summary.portfolio.accounts} distinct candidate accounts.\n- Latest official Workday-style scan: \`${workdayFile}\` at ${summary.workdayScannedAt}.\n\n## Apply-now / active-watch list\n\n| Company | Evidence grade | Why it matters | Action |\n| --- | --- | --- | --- |\n${topActions.map(record => `| ${record.company.replaceAll('|', '\\|')} | ${record.evidenceGrade} | ${record.officialRoles.slice(0, 4).map(job => `${job.title}${job.reqId ? ` ${job.reqId}` : ''}`).join('<br>') || record.teamSummary?.slice(0, 160) || 'Team evidence'} | ${record.currentAction.replaceAll('|', '\\|')} |`).join('\n')}\n\n## Priority deep dives added in this pass\n\n| Company | Confidence | Current opening conclusion | Team / architecture understanding | Stack / version evidence | Action |\n| --- | --- | --- | --- | --- | --- |\n${priorityDiveRows.join('\n')}\n\n## Movement/profile signal corrections\n\n- Treat movement radar as historical profile evidence only. It is not a resignation calendar, vacancy forecast or complete hiring census.\n- Recent Bengaluru Pega-labelled starts in the corrected Top-50 audit are concentrated at Booking, Empower, Nokia, John Deere, Sun Life and Standard Chartered; First Citizens has two team-associated engineering starts but their current Pega assignment is not independently established.\n- CBA's current openings, not profile-date movement, are the strong evidence for a new ASB India team.\n\n## All 200 accounts\n\n| # | Company | Evidence grade | Official/opening signal | Deep research conclusion | People rows | Recent profile starts | Next action |\n| ---: | --- | --- | --- | --- | ---: | --- | --- |\n${mdRows.join('\n')}\n`;
  const mdPath = join(root, 'reports', `Portfolio_Company_Research_${reportStamp}.md`);
  await writeFile(mdPath, markdown, 'utf8');

  const htmlRows = records.map(record => `<tr><td>${record.index}</td><td><strong>${escapeHtml(record.company)}</strong>${record.top50Rank ? `<br><small>Top ${record.top50Rank}</small>` : ''}</td><td>${escapeHtml(record.evidenceGrade)}<br><small>${escapeHtml(record.officialSearchStatus)}</small></td><td>${record.officialRoles.length ? record.officialRoles.map(job => `${link(job.url, `${job.title}${job.reqId ? ` ${job.reqId}` : ''}`)}<br><small>${escapeHtml(job.location ?? '')} · ${escapeHtml(job.kind)}${job.posted ? ` · posted ${escapeHtml(job.posted)}` : ''}${job.closes ? ` · closes ${escapeHtml(job.closes)}` : ''}</small>`).join('<hr>') : '—'}</td><td><strong>${escapeHtml(record.deepResearch.confidence)}</strong><br>${escapeHtml(record.deepResearch.currentOpeningConclusion)}<hr>${escapeHtml(record.deepResearch.teamArchitecture)}<hr><small>${escapeHtml(record.deepResearch.stackVersionEvidence)}</small><br><small>Verify: ${record.deepResearch.verificationQuestions.map(escapeHtml).join(' · ')}</small></td><td>${record.workstreams.map(item => `<p>${escapeHtml(item)}</p>`).join('')}</td><td><strong>${record.peopleCount}</strong> profiled rows<br>${record.keyPeople.map(escapeHtml).join('<br>')}<br><small>${record.recentProfileStarts ? `Recent: ${record.recentProfileStarts.explicitlyPega} Pega-labelled, ${record.recentProfileStarts.teamAssociated} associated` : 'Recent starts not assessed'}</small></td><td>${escapeHtml(record.fit)}<hr>${escapeHtml(record.currentAction)}<br>${link(record.careerUrl, record.careerUrl ? 'Careers' : 'No mapped career URL')}</td></tr>`).join('\n');
  const priorityDiveRowsHtml = records.filter(record => deepResearchMap.has(record.id)).map(record => `<tr><td>${escapeHtml(record.company)}</td><td>${escapeHtml(record.deepResearch.confidence)}</td><td>${escapeHtml(record.deepResearch.currentOpeningConclusion)}</td><td>${escapeHtml(record.deepResearch.teamArchitecture)}</td><td>${escapeHtml(record.deepResearch.fitAction)}</td></tr>`).join('\n');
  const html = `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Complete Pega Portfolio Research ${reportDate}</title><style>body{font:15px/1.5 system-ui,Segoe UI,Arial,sans-serif;margin:0;background:#f6f7fb;color:#172033}main{max-width:1760px;margin:auto;padding:28px}h1{font-size:34px;margin-bottom:6px}.note{background:#fff7ed;border:1px solid #fed7aa;padding:12px;border-radius:12px}table{width:100%;border-collapse:collapse;background:white}th,td{border:1px solid #d8dee9;padding:10px;vertical-align:top}th{background:#10233f;color:white;position:sticky;top:0}td:nth-child(4){min-width:260px}td:nth-child(5){min-width:360px}td:nth-child(6){min-width:320px}small{color:#5e6b7a}input{padding:11px;min-width:360px;max-width:90vw;margin:18px 0;border:1px solid #aeb7c4;border-radius:9px}.wrap{overflow:auto}hr{border:0;border-top:1px solid #e5e7eb;margin:8px 0}@media(max-width:800px){main{padding:12px}table{min-width:1600px}}</style><main><h1>Complete Pega portfolio research refresh · ${escapeHtml(reportDate)}</h1><p class="note">${escapeHtml(summary.keyConclusion)} This report merges the November hub, Deep Dossiers, Top-50 profiles, corrected join-timing audit, latest official Workday scan and targeted official web checks. Unknown remains unknown; profile movement is not a vacancy.</p><p>Coverage: ${summary.portfolio.accounts} candidate accounts · ${summary.portfolio.deepDossiers} deep-dossier companies · ${summary.portfolio.deepDossierPeople} profiled people · Workday scan ${escapeHtml(workday.scannedAt)}.</p><h2>Priority deep dives</h2><div class="wrap"><table><thead><tr><th>Company</th><th>Confidence</th><th>Current-opening conclusion</th><th>Team / architecture</th><th>Action</th></tr></thead><tbody>${priorityDiveRowsHtml}</tbody></table></div><label>Filter <input id="filter" type="search" placeholder="Company, role, Pega, Bengaluru, grade, action"></label><div class="wrap"><table><thead><tr><th>#</th><th>Company</th><th>Evidence grade</th><th>Official/current signals</th><th>Deep research / architecture</th><th>Team/work understanding</th><th>Profiles/movement</th><th>Fit/action</th></tr></thead><tbody>${htmlRows}</tbody></table></div></main><script>const input=document.getElementById('filter');input.addEventListener('input',()=>{const query=input.value.toLowerCase();for(const row of document.querySelectorAll('tbody tr'))row.hidden=!row.textContent.toLowerCase().includes(query);});</script></html>`;
  const htmlPath = join(root, 'reports', `Portfolio_Company_Research_${reportStamp}.html`);
  await writeFile(htmlPath, html, 'utf8');

  const hubPath = join(root, 'Pega_Career_Intelligence_Hub.html');
  let hub = await readFile(hubPath, 'utf8');
  const start = '<!-- PORTFOLIO_RESEARCH_START -->';
  const end = '<!-- PORTFOLIO_RESEARCH_END -->';
  const topSeven = topActions.slice(0, 9).map(record => `<tr><td>${escapeHtml(record.company)}</td><td>${escapeHtml(record.evidenceGrade)}</td><td>${record.officialRoles.slice(0, 3).map(job => link(job.url, `${job.title}${job.reqId ? ` ${job.reqId}` : ''}`)).join('<br>') || escapeHtml(record.teamSummary ?? '')}</td><td>${escapeHtml(record.deepResearch.currentOpeningConclusion)}<hr>${escapeHtml(record.deepResearch.teamArchitecture)}</td><td>${escapeHtml(record.currentAction)}</td></tr>`).join('\n');
  const section = `${start}\n<section class="section" id="complete-portfolio-research" style="border-left:4px solid #2563eb">\n<div class="head"><div class="bar" style="background:#2563eb"></div><h2>Complete portfolio deep research refresh · ${escapeHtml(reportDate)}</h2><p>Portfolio-level reconciliation plus fresh manual web/profile research for priority employers. Each company now carries confirmed openings, inferred team/work architecture, stack/version clues, movement evidence and verification questions. Unknown is kept separate from no-opening.</p></div>\n<div class="review-note">${escapeHtml(summary.keyConclusion)} Parsed ${summary.portfolio.deepDossiers} deep-dossier companies / ${summary.portfolio.deepDossierPeople} profiled people and ${summary.portfolio.accounts} candidate accounts. Fresh official scan: <code>${escapeHtml(workdayFile)}</code>.</div>\n<div class="table-wrap"><table class="tbl searchable"><thead><tr><th>Company</th><th>Evidence grade</th><th>Current/official signal</th><th>Deep research takeaway</th><th>Next action</th></tr></thead><tbody>${topSeven}</tbody></table></div>\n<p class="sub">Full searchable report: <a href="reports/Portfolio_Company_Research_${reportStamp}.html">Portfolio Company Research ${escapeHtml(reportDate)}</a>. Markdown: <code>reports/Portfolio_Company_Research_${reportStamp}.md</code>. Data: <code>reports/portfolio_company_research_${reportStamp}.json</code>.</p>\n</section>\n${end}`;
  if (hub.includes(start)) {
    hub = hub.replace(new RegExp(`${start}[\\s\\S]*?${end}`), section);
  } else {
    hub = hub.replace('<!-- PRODUCT_200_WATCH_END -->', `<!-- PRODUCT_200_WATCH_END -->\n${section}`);
  }
  if (!hub.includes('href="#complete-portfolio-research"')) {
    hub = hub.replace('<a href="#product-200-watch" style="color:#93c5fd;font-weight:700">200-account openings watch</a>', '<a href="#product-200-watch" style="color:#93c5fd;font-weight:700">200-account openings watch</a><a href="#complete-portfolio-research" style="color:#60a5fa;font-weight:700">Complete portfolio research</a>');
  }
  await writeFile(hubPath, hub, 'utf8');
  console.log(JSON.stringify({ jsonPath, mdPath, htmlPath, records: records.length, gradeCounts: summary.gradeCounts }, null, 2));
} catch (error) {
  console.error(error);
  process.exitCode = 1;
}
