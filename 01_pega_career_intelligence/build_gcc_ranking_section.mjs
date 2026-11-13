import { readFile, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const directory = dirname(fileURLToPath(import.meta.url));
const sourcePath = join(directory, 'gcc_ranking_scores.json');
const lifestylePath = join(directory, 'gcc_lifestyle_supplement.json');
const hubPath = join(directory, 'Pega_Career_Intelligence_Hub.html');
const sectionStart = '<!-- GCC_RANKING_SECTION_START -->';
const sectionEnd = '<!-- GCC_RANKING_SECTION_END -->';
const projectSectionMarker = '<section class="section" id="project-skills-map">';

const escapeHtml = (value) => String(value ?? '')
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#39;');

const displayValue = (value, fallback = '—') => {
  if (value === null || value === undefined || value === '') return fallback;
  return escapeHtml(value);
};

const truncate = (value, limit) => {
  const text = String(value ?? '');
  if (text.length <= limit) return escapeHtml(text);
  return `${escapeHtml(text.slice(0, limit - 1).trimEnd())}…`;
};

const listText = (values, fallback = '—') => {
  if (!Array.isArray(values) || values.length === 0) return fallback;
  return values.map(value => escapeHtml(value)).join(' · ');
};

const scoreText = company => company.total_score === null ? '—' : displayValue(company.total_score);

const attritionPill = level => {
  const pillClass = { Low: 'yes', Medium: 'amber', High: 'red', Unknown: 'warn' }[level] ?? 'warn';
  return `<span class="pill ${pillClass}">${displayValue(level, 'Unknown')}</span>`;
};

const confidencePill = level => {
  const pillClass = { High: 'yes', Medium: 'amber', Low: 'warn', None: 'info' }[level] ?? 'info';
  return `<span class="pill ${pillClass}">${displayValue(level, 'None')}</span>`;
};

const pillarScore = (company, key) => displayValue(company.pillar_breakdown?.[key]?.score, '—');

const rankingRows = companies => companies.map(company => {
  const evidence = company.evidence ?? {};
  return `<tr><td class="rank">${displayValue(company.rank_within_confidence, '—')}</td><td class="co">${displayValue(company.company_name)}</td><td>${scoreText(company)}</td><td>${pillarScore(company, 'p1_architectural_autonomy')}</td><td>${pillarScore(company, 'p2_modernity_integration')}</td><td>${pillarScore(company, 'p3_innovation_visibility')}</td><td>${pillarScore(company, 'p4_attrition_index')}</td><td>${evidence.tenureAvgYears === null || evidence.tenureAvgYears === undefined ? '—' : `${displayValue(evidence.tenureAvgYears)}y (n=${displayValue(evidence.tenureN, '0')})`}</td><td>${attritionPill(company.attrition_warning_level)}</td><td>${truncate(company.leadership_location_analysis, 220)}</td><td>${truncate(company.tech_stack_modernity, 160)}</td></tr>`;
}).join('');

const rankingTable = (companies, id) => `<div class="table-wrap"><table class="tbl searchable" id="${id}"><thead><tr><th>Rank</th><th>Company</th><th>Score /100</th><th>P1</th><th>P2</th><th>P3</th><th>P4</th><th>Avg tenure</th><th>Attrition</th><th>Where authority sits</th><th>Modern stack</th></tr></thead><tbody>${rankingRows(companies)}</tbody></table></div>`;

// Must be a function: `companies` only exists inside buildSection(), so evaluating this
// at module scope threw ReferenceError before the script could run. It also has to
// receive the low-confidence subset rather than every company.
const lowEvidenceRows = companies => companies.map(company => {
  const evidence = company.evidence ?? {};
  const reason = company.score_status === 'INSUFFICIENT_EVIDENCE'
    ? 'Insufficient evidence for a defensible score.'
    : 'Under-documented public evidence; not rank-comparable.';
  return `<tr><td class="co">${displayValue(company.company_name)}</td><td>${scoreText(company)}</td><td>${displayValue(evidence.peopleCount, '0')} / ${displayValue(evidence.auditRows, '0')} / ${displayValue(evidence.tenureN, '0')}</td><td>${escapeHtml(reason)}</td></tr>`;
}).join('');

const digestRows = (companies, flagKey) => companies
  .filter(company => Array.isArray(company[flagKey]) && company[flagKey].length > 0)
  .sort((left, right) => {
    const countDifference = right[flagKey].length - left[flagKey].length;
    return countDifference || String(left.company_name).localeCompare(String(right.company_name));
  })
  .slice(0, 20)
  .map(company => `<tr><td class="co">${displayValue(company.company_name)}</td><td>${company[flagKey].map(flag => escapeHtml(flag)).join(' · ')}</td></tr>`)
  .join('');

const fullRankingRows = companies => companies
  .filter(company => company.score_status === 'SCORED')
  .sort((left, right) => (left.rank ?? Number.MAX_SAFE_INTEGER) - (right.rank ?? Number.MAX_SAFE_INTEGER) || String(left.company_name).localeCompare(String(right.company_name)))
  .map(company => {
    const evidence = company.evidence ?? {};
    const comparable = company.rank_comparable === false ? '<span class="pill warn">not comparable</span>' : displayValue(company.rank, '—');
    return `<tr><td class="rank">${comparable}</td><td class="co">${displayValue(company.company_name)}</td><td>${scoreText(company)}</td><td>${confidencePill(company.evidence_confidence)}</td><td>${attritionPill(company.attrition_warning_level)}</td><td>${listText(evidence.sectors)}</td><td>${listText(Array.isArray(evidence.locations) ? evidence.locations.slice(0, 3) : [])}</td><td>${displayValue(evidence.hiring_status)}</td></tr>`;
  })
  .join('');

const lifestyleStatusClass = status => ({
  VERIFIED: 'yes',
  VERIFIED_GLOBAL_POLICY: 'prob',
  CONTESTED_BY_ROLE: 'amber',
  UNVERIFIED: 'warn',
  NOT_RESEARCHED: 'info'
}[status] ?? 'info');

const lifestyleStatusPill = status => `<span class="pill ${lifestyleStatusClass(status)}">${displayValue(status, 'NOT_RESEARCHED')}</span>`;

const lifestyleClaimCell = claim => {
  if (!claim) return '<span class="pill info">NOT_RESEARCHED</span>';
  return `${lifestyleStatusPill(claim.status)} ${displayValue(claim.claim)}`;
};

const lifestyleLegendRows = supplement => Object.entries(supplement.status_legend).map(([status, meaning]) => `<tr><td>${lifestyleStatusPill(status)}</td><td>${displayValue(meaning)}</td></tr>`).join('');

const lifestyleLedgerRows = companies => companies
  .slice()
  .sort((left, right) => (right.engineering_score ?? Number.MIN_SAFE_INTEGER) - (left.engineering_score ?? Number.MIN_SAFE_INTEGER) || String(left.company_name).localeCompare(String(right.company_name)))
  .map(company => {
    const intelligence = company.lifestyle_intelligence ?? {};
    return `<tr><td class="co">${displayValue(company.company_name)}</td><td>${displayValue(company.engineering_score)}</td><td>${lifestyleClaimCell(intelligence.food_and_commute)}</td><td>${lifestyleClaimCell(intelligence.insurance_perks)}</td><td>${lifestyleClaimCell(intelligence.office_mandate)}</td><td>${lifestyleClaimCell(intelligence.the_flex)}</td><td>${displayValue(company.standout_fun_perk)}</td></tr>`;
  })
  .join('');

const lifestyleDetailRows = companies => companies.flatMap(company => Object.entries(company.lifestyle_intelligence ?? {}).map(([dimension, claim]) => `<tr><td class="co">${displayValue(company.company_name)}</td><td>${escapeHtml(dimension.replaceAll('_', ' '))}</td><td>${lifestyleStatusPill(claim.status)}</td><td>${displayValue(claim.claim)}</td><td>${Array.isArray(claim.sources) && claim.sources.length > 0 ? claim.sources.map(source => escapeHtml(source)).join(' · ') : '<em>—</em>'}</td></tr>`)).join('');

const pillarCards = rubric => {  // eslint-disable-line
  const pillarDescriptions = {
    p1_architectural_autonomy: {
      name: 'P1 · Architectural autonomy',
      earns: 'India/GCC-based senior, lead or top-level Pega architecture authority and evidence of owning platform decisions.',
      loses: 'Delivery/support-only signals, or no defensible local architecture authority.'
    },
    p2_modernity_integration: {
      name: 'P2 · Modernity & integration',
      earns: 'Heavy integration/event-driven work, modern UI/application signals, and cloud/platform ownership.',
      loses: 'Support-only or narrowly dated implementation evidence without modern, integration or cloud signals.'
    },
    p3_innovation_visibility: {
      name: 'P3 · Innovation visibility',
      earns: 'Conference, award, community, hackathon or build-in-public evidence connected to engineering work.',
      loses: 'This pillar has no negative floor in the supplied rubric; absent public visibility earns no points.'
    },
    p4_attrition_index: {
      name: 'P4 · Attrition index',
      earns: 'Measured, settled tenure patterns where at least three parseable engineer tenures are available.',
      loses: 'Departure-driven short tenure; unmeasured tenure is recorded as Unknown rather than penalised.'
    }
  };
  return Object.entries(rubric.pillars).map(([key, pillar]) => {
    const description = pillarDescriptions[key] ?? { name: key, earns: 'Positive evidence in this pillar.', loses: 'Negative or missing evidence in this pillar.' };
    return `<div class="card"><h3>${escapeHtml(description.name)} · max ${displayValue(pillar.max)} points</h3><p><strong>What earns points:</strong> ${escapeHtml(description.earns)}</p><p><strong>What loses points:</strong> ${escapeHtml(description.loses)}</p></div>`;
  }).join('');
};

const buildSection = (data, lifestyle) => {
  const companies = data.companies;
  const highConfidence = companies.filter(company => company.evidence_confidence === 'High').sort((left, right) => (left.rank_within_confidence ?? Number.MAX_SAFE_INTEGER) - (right.rank_within_confidence ?? Number.MAX_SAFE_INTEGER));
  const mediumConfidence = companies.filter(company => company.evidence_confidence === 'Medium').sort((left, right) => (left.rank_within_confidence ?? Number.MAX_SAFE_INTEGER) - (right.rank_within_confidence ?? Number.MAX_SAFE_INTEGER));
  const lowConfidence = companies.filter(company => company.evidence_confidence === 'Low' || company.score_status === 'INSUFFICIENT_EVIDENCE').sort((left, right) => String(left.company_name).localeCompare(String(right.company_name)));
  const caveats = data.methodology_caveats;
  // Read the live figures out of the dataset: hardcoding them let the prose drift from the
  // data (the correlation moved to 0.842 once the verified supplement was folded in).
  const corr = caveats.evidence_volume_correlation;
  const unknown = data.counts.attrition_unknown;
  const scoredTotal = data.counts.scored;
  const methodology = `<strong>Read this before using the ranking.</strong> The score measures <em>how much defensible public evidence exists</em> for a strong engineering environment — not a company's true quality. Measured correlation between score and raw evidence volume is <strong>${escapeHtml(corr)}</strong>, so a low score predominantly means <em>thin public evidence</em>, not a bad place to work. ${escapeHtml(unknown)} of ${escapeHtml(scoredTotal)} companies have no measurable tenure data and are recorded as <strong>Unknown</strong>, not penalised. <strong>Only compare companies inside the same evidence-confidence tier.</strong> Glassdoor ratings and compensation were not used — no reliable programmatic source was available. No private profile data was accessed. Scores are a research instrument for prioritising outreach, not a verdict on any employer or a prediction about any vacancy.`;
  return `${sectionStart}
<section class="section" id="gcc-culture-ranking">
<div class="head"><div class="bar"></div><h2>GCC engineering culture ranking · evidence-weighted research instrument</h2><p>October 2026 ranking of public evidence for engineering autonomy, modernity, innovation visibility and attrition signals across the GCC/company universe. This section now carries both the engineering ranking and a separate unscored lifestyle ledger. Scores and ranks are frozen from the supplied research dataset.</p></div>
<div class="review-note">${methodology}</div>
<h3>Rubric explainer</h3>
<div class="review-grid">${pillarCards(data.rubric)}</div>
<div class="review-note"><strong>Two documented corrections to the rubric as written:</strong> (a) <strong>rubric arithmetic:</strong> ${escapeHtml(caveats.rubric_arithmetic)} (b) <strong>short-tenure rule:</strong> ${escapeHtml(caveats.short_tenure_rule)}</div>
<h3>High confidence — the only rank-comparable table</h3>
<p class="sub">Compare these companies within this tier only. Rank is relative to the High evidence-confidence tier.</p>
${rankingTable(highConfidence, 'gcc-high-confidence')}
<h3>Medium confidence — indicative, treat as a watchlist</h3>
<p class="sub">These scores are directional and should be tested with targeted outreach.</p>
${rankingTable(mediumConfidence, 'gcc-medium-confidence')}

<h3>Lifestyle &amp; total rewards · evidence ledger (not scored)</h3>
<div class="review-note">${displayValue(lifestyle.note)} <strong>${displayValue(lifestyle.coverage.warning)}</strong></div>
<div class="table-wrap"><table class="tbl searchable" id="gcc-lifestyle-status-legend"><thead><tr><th>Status</th><th>What it means</th></tr></thead><tbody>${lifestyleLegendRows(lifestyle)}</tbody></table></div>
<div class="table-wrap"><table class="tbl searchable" id="gcc-lifestyle-ledger"><thead><tr><th>Company</th><th>Eng. score</th><th>Campus &amp; Food</th><th>Insurance</th><th>RTO policy</th><th>The Flex</th><th>Standout perk</th></tr></thead><tbody>${lifestyleLedgerRows(lifestyle.companies)}</tbody></table></div>
<div class="table-wrap"><table class="tbl searchable" id="gcc-lifestyle-claim-details"><thead><tr><th>Company</th><th>Dimension</th><th>Status</th><th>Claim</th><th>Sources</th></tr></thead><tbody>${lifestyleDetailRows(lifestyle.companies)}</tbody></table></div>
<div class="call amber"><p>Lifestyle claims are not scored on purpose. Perks vary by grade, shift and year, and sources openly contradict each other — the most widely repeated claim in this whole ledger, that Goldman Sachs Bengaluru gives free gourmet meals and free AC cabs, did not survive checking. Treat every CONTESTED_BY_ROLE and UNVERIFIED row as a question for the recruiter, not a fact. Ask specifically: is lunch free or subsidised, is transport all-day or late-hours only, how many days in office, and is parental insurance covered from day one without co-pay.</p></div>

<h3>Low confidence — under-documented, NOT judged weak</h3>
<div class="call amber"><p>A low score here reflects missing research coverage, not a weak engineering environment. Several companies in this tier are known-good targets whose evidence simply has not been gathered yet.</p></div>
<div class="table-wrap"><table class="tbl searchable" id="gcc-low-confidence"><thead><tr><th>Company</th><th>Score</th><th>Evidence available (people / audit rows / tenure n)</th><th>Why it cannot be ranked</th></tr></thead><tbody>${lowEvidenceRows(lowConfidence)}</tbody></table></div>
<h3>Red-flag digest</h3>
<div class="table-wrap"><table class="tbl searchable" id="gcc-red-flags"><thead><tr><th>Company</th><th>Red flags</th></tr></thead><tbody>${digestRows(companies, 'red_flags')}</tbody></table></div>
<h3>Green-flag digest</h3>
<div class="table-wrap"><table class="tbl searchable" id="gcc-green-flags"><thead><tr><th>Company</th><th>Green flags</th></tr></thead><tbody>${digestRows(companies, 'green_flags')}</tbody></table></div>
<h3>Full ranking · all scored companies</h3>
<p class="sub">The full table contains the 89 companies with a scored result. Rows marked not comparable should not be compared across evidence-confidence tiers.</p>
<div class="table-wrap"><table class="tbl searchable" id="gcc-full-ranking"><thead><tr><th>Rank</th><th>Company</th><th>Score</th><th>Confidence</th><th>Attrition</th><th>Sector</th><th>Locations</th><th>Hiring status</th></tr></thead><tbody>${fullRankingRows(companies)}</tbody></table></div>
</section>
${sectionEnd}`;
};

const inject = (html, section) => {
  const blockPattern = new RegExp(`${sectionStart}[\\s\\S]*?${sectionEnd}`, 'g');
  const matches = html.match(blockPattern) ?? [];
  if (matches.length > 1) throw new Error(`Expected at most one GCC section block, found ${matches.length}.`);
  const withSection = matches.length === 1
    ? html.replace(blockPattern, section)
    : html.replace(projectSectionMarker, `${section}\n${projectSectionMarker}`);
  const navLink = '<a href="#gcc-culture-ranking" style="color:#f59e0b;font-weight:700">GCC culture ranking (NEW)</a>';
  const existingNavPattern = /<a href="#gcc-culture-ranking"[^>]*>[\s\S]*?<\/a>/g;
  const navMatches = withSection.match(existingNavPattern) ?? [];
  if (navMatches.length > 1) throw new Error(`Expected at most one GCC sidebar link, found ${navMatches.length}.`);
  if (navMatches.length === 1) return withSection.replace(existingNavPattern, navLink);
  const projectLinkPattern = /(<a href="#project-skills-map"[^>]*>[\s\S]*?<\/a>)/;
  if (!projectLinkPattern.test(withSection)) throw new Error('Could not find the project-skills-map sidebar link.');
  return withSection.replace(projectLinkPattern, `$1${navLink}`);
};

try {
  const [source, lifestyleSource, hub] = await Promise.all([readFile(sourcePath, 'utf8'), readFile(lifestylePath, 'utf8'), readFile(hubPath, 'utf8')]);
  const data = JSON.parse(source);
  const lifestyle = JSON.parse(lifestyleSource);
  if (!Array.isArray(data.companies) || data.companies.length === 0) throw new Error('Ranking source has no companies.');
  if (!Array.isArray(lifestyle.companies) || lifestyle.companies.length === 0) throw new Error('Lifestyle supplement has no companies.');
  const output = inject(hub, buildSection(data, lifestyle));
  await writeFile(hubPath, output, 'utf8');
  const highCount = data.companies.filter(company => company.evidence_confidence === 'High').length;
  const mediumCount = data.companies.filter(company => company.evidence_confidence === 'Medium').length;
  const lowCount = data.companies.filter(company => company.evidence_confidence === 'Low' || company.score_status === 'INSUFFICIENT_EVIDENCE').length;
  const redCount = data.companies.filter(company => Array.isArray(company.red_flags) && company.red_flags.length > 0).sort((left, right) => right.red_flags.length - left.red_flags.length).slice(0, 20).length;
  const greenCount = data.companies.filter(company => Array.isArray(company.green_flags) && company.green_flags.length > 0).sort((left, right) => right.green_flags.length - left.green_flags.length).slice(0, 20).length;
  const scoredCount = data.companies.filter(company => company.score_status === 'SCORED').length;
  const lifestyleClaimCount = lifestyle.companies.reduce((total, company) => total + Object.keys(company.lifestyle_intelligence ?? {}).length, 0);
  console.log(JSON.stringify({ highConfidenceRows: highCount, mediumConfidenceRows: mediumCount, lowConfidenceRows: lowCount, redFlagRows: redCount, greenFlagRows: greenCount, fullRankingRows: scoredCount, lifestyleStatusRows: Object.keys(lifestyle.status_legend).length, lifestyleLedgerRows: lifestyle.companies.length, lifestyleClaimDetailRows: lifestyleClaimCount, searchableTablesAdded: 9 }, null, 2));
} catch (error) {
  console.error(`GCC ranking section build failed: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}
