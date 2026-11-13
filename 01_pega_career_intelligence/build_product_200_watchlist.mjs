import { readFile, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
const load = async path => JSON.parse(await readFile(join(root, path), 'utf8'));
const aliases = new Map([
  ['booking holdings', 'booking'], ['booking com', 'booking'],
  ['bosch bgsw', 'bosch'], ['dell technologies', 'dell'],
  ['dhl it services', 'dhl'], ['jpmorgan chase and co', 'jpmorganchase'],
  ['levi strauss and co', 'levi strauss'], ['nab innovation centre', 'nab'],
  ['navistar international motors', 'navistar'], ['optum unitedhealth', 'optum'],
  ['unilever uniops', 'unilever'], ['cvs health aetna', 'cvs health'],
  ['engen highmark', 'engen'], ['engen global', 'engen'],
  ['credit suisse ubs', 'ubs'],
  ['anz', 'anz bank'], ['anz bank', 'anz bank'],
  ['ameriprise', 'ameriprise'], ['ameriprise financial', 'ameriprise'],
  ['commonwealth bank', 'commonwealth bank'], ['cba', 'commonwealth bank'],
  ['first citizens bank', 'first citizens bank'], ['first citizens', 'first citizens bank'],
  ['jpmorgan chase co', 'jpmorganchase'], ['jpmorgan chase', 'jpmorganchase'], ['jpmorganchase', 'jpmorganchase'],
  ['citi citi', 'citi'], ['citibank', 'citi'], ['citi', 'citi'],
  ['societe generale', 'societe generale'], ['societe generale gsc', 'societe generale'],
  ['vodafone vois', 'vodafone'], ['vois', 'vodafone'], ['vodafone', 'vodafone'],
  ['elevance health', 'elevance health'], ['carelon global solutions', 'elevance health'], ['carelon elevance', 'elevance health'],
  ['optum uhg', 'optum'], ['optum unitedhealth group', 'optum'],
  ['ford motor company', 'ford'], ['ford business solutions', 'ford'], ['ford credit', 'ford'],
  ['daimler truck innovation center', 'daimler truck'], ['daimler truck', 'daimler truck'],
  ['the hartford', 'the hartford'], ['hartford', 'the hartford'],
  ['sun life financial', 'sun life'], ['sun life global solutions', 'sun life'], ['sun life slgs', 'sun life'],
  ['lloyds technology centre', 'lloyds banking'], ['lloyds banking group', 'lloyds banking'],
  ['nokia', 'nokia'], ['nokia india', 'nokia'],
  ['deere financial', 'john deere'], ['john deere financial', 'john deere'], ['john deere', 'john deere'],
  ['a p moller maersk', 'maersk'], ['maersk gsc', 'maersk'], ['maersk', 'maersk'],
  ['northern trust', 'northern trust'], ['bny mellon', 'bny'], ['bny', 'bny'],
  ['fidelity india', 'fidelity investments'], ['fidelity', 'fidelity investments'],
  ['fidelity investments', 'fidelity investments'], ['target in', 'target'],
  ['mufg pension and market svcs', 'mufg pension and market services'],
  ['global payments tsys', 'global payments'], ['global payments', 'global payments'],
  ['ge healthcare', 'ge healthcare'], ['metlife mgcc', 'metlife'], ['metlife', 'metlife'],
  ['mizuho global services', 'mizuho'], ['mizuho', 'mizuho'],
  ['roche', 'roche'], ['msd merck sharp dohme', 'merck'], ['merck', 'merck']
]);

function key(value) {
  const normalized = String(value ?? '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .replace(/\([^)]*\)/g, ' ').replace(/&/g, ' and ').toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ').replace(/\b(india|bengaluru|bangalore|gcc|gsc)\b/g, ' ')
    .replace(/\s+/g, ' ').trim();
  return aliases.get(normalized) ?? normalized;
}
const escapeHtml = text => String(text ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;')
  .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
const link = (url, label) => {
  if (!/^https:\/\//i.test(url ?? '')) return escapeHtml(label);
  return `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`;
};

try {
  const catalog = await load('JobChange/JobChange/research/master_catalog.json');
  const directory = await load('JobChange/JobChange/research/directory.json');
  const catalogSource = await readFile(join(root, 'JobChange/JobChange/master_catalog.py'), 'utf8');
  const overridesBlock = catalogSource.split('CAREER_URL_OVERRIDES={')[1]?.split('\n}')[0] ?? '';
  const officialOverrides = new Map([...overridesBlock.matchAll(/^\s*'([^']+)'\s*:\s*'(https:\/\/[^']+)'/gm)]
    .map(match => [key(match[1]), match[2]]));
  const top50 = await load('bengaluru_top50_2026-11.json');
  const starts = await load('reports/bengaluru_join_timing_2026-11.json');
  const workday = await load('reports/workday_pega_openings_2026-11-12.json');
  const probes = await load('reports/product_200_portal_probes_2026-11-12.json');
  const extra = await load('reports/product_200_extra_official_checks_2026-11-12.json');
  const newTeam = await load('reports/product_200_new_team_evidence_2026-11-12.json');
  const groups = new Map();
  const skip = /\b(ntt data|tenth revolution|thakral|vmc soft|accenture|delpath|digitalxnode|innovationteam|religent|revolent|teksystems|usaa)\b/i;

  for (const row of catalog.companies.filter(company => ['gcc', 'unclassified'].includes(company.category))) {
    if (/^IBM · Confluent support|^Mercedes-Benz R&D India$/i.test(row.name)) continue;
    if (row.category === 'unclassified' && skip.test(row.name)) continue;
    const id = key(row.name);
    if (!id) continue;
    const group = groups.get(id) ?? { id, aliases: [], catalog: [], rank: 999 };
    group.aliases.push(row.name);
    group.catalog.push(row);
    groups.set(id, group);
  }
  for (const row of top50.companies) {
    if (/^Mercedes-Benz R&D India/i.test(row.company)) continue;
    const id = key(row.company);
    const group = groups.get(id) ?? { id, aliases: [], catalog: [], rank: 999 };
    group.rank = Math.min(group.rank, row.rank);
    group.top50 = row;
    group.aliases.push(row.company);
    groups.set(id, group);
  }
  // These are exploratory product/GCC accounts, not claims that their Bengaluru offices use Pega.
  const supplemental = [
    'BD / Becton Dickinson', 'Vanguard', 'Sainsbury\'s Tech', 'Swiss Re', 'Caterpillar', 'Thomson Reuters',
    'London Stock Exchange Group', 'Nasdaq', 'Invesco', 'Aon', 'SAP Labs India',
    'Oracle India', 'Adobe India', 'Salesforce India', 'Intuit India', 'Amazon India',
    'Flipkart', 'PhonePe', 'Razorpay', 'Stripe India', 'Expedia Group',
    'Google India', 'Microsoft India', 'Atlassian India', 'Uber India',
    'Home Depot India', 'Kroger Technology', 'Paytm', 'Meesho', 'Myntra',
    'Cleartrip', 'Twilio India', 'ServiceNow India', 'Snowflake India',
    'Databricks India', 'Apple India'
  ];
  for (const name of supplemental) {
    if (groups.size >= 200) break;
    const id = key(name);
    if (!groups.has(id)) groups.set(id, {
      id, aliases: [name], catalog: [], rank: 999, exploratory: true
    });
  }
  const directoryMap = new Map(directory.records.filter(record => record.category === 'gcc')
    .map(record => [key(record.name), record]));
  const startingMap = new Map(starts.companies.map(row => [key(row.company), row]));
  const boards = new Map(workday.results.map(row => [key(row.label), row]));
  const probeMap = new Map(probes.results.map(row => [row.url, row]));
  const extraMap = new Map(extra.checks.map(row => [key(row.label), row]));
  const signalMap = new Map(newTeam.signals.map(row => [row.id, row]));

  const ordered = [...groups.values()].sort((left, right) =>
    left.rank - right.rank ||
    Number(right.catalog.some(row => row.category === 'gcc')) - Number(left.catalog.some(row => row.category === 'gcc')) ||
    left.id.localeCompare(right.id));
  if (ordered.length < 200) throw new Error(`Only ${ordered.length} distinct candidate employers; do not pad with aliases`);
  const records = ordered.slice(0, 200).map((group, index) => {
    const employer = group.catalog.find(row => row.category === 'gcc') ?? group.catalog[0] ?? {};
    const original = directoryMap.get(group.id);
    const site = group.catalog.flatMap(row => row.search_targets ?? [])
      .find(target => target.career_url)?.career_url ??
      original?.career_url ??
      group.aliases.map(name => officialOverrides.get(key(name))).find(Boolean) ?? '';
    const board = boards.get(group.id);
    const supplementalCheck = extraMap.get(group.id);
    const signal = signalMap.get(group.id);
    const timing = startingMap.get(group.id);
    const jobs = (board?.jobs ?? []).filter(job =>
      /\b(bengaluru|bangalore)\b/i.test(job.location ?? '') &&
      /\b(pega|pegasystems)\b/i.test(`${job.title} ${job.description ?? ''}`)
    ).map(job => ({
      title: job.title, location: job.location, reqId: job.reqId,
      posted: job.startDate, closes: job.endDate, url: job.url,
      relevance: group.id === 'commonwealth bank'
        ? ['REQ266820', 'REQ266821', 'REQ266822', 'REQ266311'].includes(job.reqId)
          ? 'ASB build-out' : 'Separate CBA role: Pega is one of several skills'
        : /\bpega\b/i.test(job.title) ? 'Pega in title' : 'Pega in description'
    }));
    jobs.push(...(supplementalCheck?.searchStatus === 'official-live-role' ? supplementalCheck.jobs : []));
    const status = supplementalCheck?.searchStatus === 'official-live-role'
      ? 'Official employer page: Bengaluru Pega role'
      : supplementalCheck?.searchStatus === 'official-search-no-bengaluru-pega-match'
        ? 'Official search: no Bengaluru Pega match'
        : supplementalCheck?.searchStatus === 'official-search-checked'
          ? 'Official search: no Pega match'
          : board?.status === 'ok' && board.boardSize >= 50
      ? jobs.length ? 'Official feed: Bengaluru Pega mention' : 'Official feed: no Bengaluru Pega match'
      : board?.status === 'ok' ? 'Partial board: no reliable negative' : board
        ? 'Portal unreachable: unknown' : 'Not checked via supported official feed';
    const olderLeads = group.catalog.flatMap(row => row.hiring_signals ?? [])
      .filter(signal => /\b(bengaluru|bangalore)\b/i.test(signal.location ?? '') &&
        /\bpega\b/i.test(`${signal.title ?? ''} ${signal.text ?? ''} ${signal.description ?? ''}`) &&
        /^https:\/\//i.test(signal.source_url ?? signal.url ?? ''))
      .map(signal => ({
        title: signal.title, location: signal.location, url: signal.source_url ?? signal.url,
        checkedAt: signal.checked_at ?? null, sourceDate: signal.source_date ?? null
      }))
      .sort((left, right) => String(right.sourceDate ?? right.checkedAt ?? '')
        .localeCompare(String(left.sourceDate ?? left.checkedAt ?? ''))).slice(0, 2);
    const historicalClaim = group.catalog.flatMap(row => row.claims ?? [])
      .find(claim => ['project', 'bangalore_team'].includes(claim.type) &&
        claim.access !== 'legacy' && /^https:\/\//i.test(claim.source_url ?? ''));
    return {
      index: index + 1, id: group.id, company: group.top50?.company ?? employer.name ?? group.aliases[0],
      aliases: [...new Set(group.aliases)], top50Rank: group.rank === 999 ? null : group.rank,
      historicalTeamEvidence: group.top50?.confidence ?? employer.bangalore_scope ?? 'unproven',
      careerUrl: site, scanStatus: status,
      checkedAt: supplementalCheck?.status === 'checked' ? supplementalCheck.checkedAt
        : board?.status === 'ok' ? workday.scannedAt : null,
      careerPageProbe: probeMap.get(site)?.status ?? (site ? 'not probed' : 'career URL not mapped'),
      officialJobs: jobs, boardSize: supplementalCheck?.boardSize ?? board?.boardSize ?? null,
      olderLeads, historicalClaim: historicalClaim ? {
        text: String(historicalClaim.text ?? '').slice(0, 350),
        url: historicalClaim.source_url, checkedAt: historicalClaim.checked_at ?? null
      } : null,
      newTeamSignal: signal ? {
        verdict: signal.verdict, evidence: signal.evidence, sourceUrl: signal.sourceUrl,
        nextAction: signal.nextAction
      } : null,
      joinedProfileStarts: timing ? { explicitlyPega: timing.recentDatedPegaRoles, teamAssociated: timing.recentTeamAssociated } : null,
      fit: group.top50?.fit ?? 'Unassessed: verify Bengaluru Pega engineering ownership and payroll',
      program: group.top50?.oneLine ?? historicalClaim?.text ??
        'No verified Bengaluru Pega workstream in this project'
    };
  });
  const result = {
    generatedAt: new Date().toISOString(), targetCount: 200, candidatePool: ordered.length,
    selection: 'Top 50 first, then deduplicated GCC catalogue and additional product/enterprise accounts. A target is not a confirmed Bengaluru Pega employer.',
    scanAt: workday.scannedAt,
    scanLimits: 'Only official Workday feed matches from sites that responded; zero means no matching listing on that board at scan time, not no Pega openings across the employer. Third-party posts and search-index results are not treated as open jobs.',
    records
  };
  const jsonPath = join(root, 'reports', 'product_200_openings_watch_2026-11-12.json');
  const htmlPath = join(root, 'reports', 'Product_200_Pega_Opportunity_Watch_2026-11-12.html');
  await writeFile(jsonPath, JSON.stringify(result, null, 2), 'utf8');
  const total = status => records.filter(row => row.scanStatus.startsWith(status)).length;
  const rows = records.map(row => `<tr><td>${row.index}</td><td><strong>${escapeHtml(row.company)}</strong>${row.top50Rank ? ` <small>Top ${row.top50Rank}</small>` : ''}<br><small>Aliases: ${escapeHtml(row.aliases.join(', '))}</small></td><td>${escapeHtml(row.scanStatus)}<br><small>${row.checkedAt ? escapeHtml(row.checkedAt) : 'Job search not verified'} · ${escapeHtml(row.careerPageProbe)}</small></td><td>${row.officialJobs.length ? row.officialJobs.map(job =>
    `${link(job.url, `${job.title} (${job.reqId ?? 'no ID'})`)} · ${escapeHtml(job.relevance)} · ${escapeHtml(job.closes || 'close date unknown')}`).join('<br>') : '—'}</td><td>${escapeHtml(row.program)}${row.historicalClaim ? `<br><small>${link(row.historicalClaim.url, 'Historical source')} (checked ${escapeHtml(row.historicalClaim.checkedAt ?? 'unknown')})</small>` : ''}</td><td>${row.olderLeads.length
    ? row.olderLeads.map(lead => `${link(lead.url, lead.title || 'Pega lead')} · ${escapeHtml(lead.sourceDate ?? lead.checkedAt ?? 'date unknown')} · <strong>NOT live-verified</strong>`).join('<br>')
    : 'No dated lead in this ledger'}<br><small>${escapeHtml(row.joinedProfileStarts
    ? `Profile starts since Nov 2025: ${row.joinedProfileStarts.explicitlyPega} Pega-labelled, ${row.joinedProfileStarts.teamAssociated} team-associated; not confirmed hires`
    : 'Join timing not assessed')}</small></td><td>${link(row.careerUrl, row.careerUrl ? 'Careers' : 'URL not mapped')}<br>${escapeHtml(row.fit)}</td></tr>`).join('\n');
  const signalRows = newTeam.signals.map(item => {
    const employer = records.find(row => row.id === item.id);
    return `<tr><td class="co">${escapeHtml(employer?.company ?? item.id)}</td><td>${escapeHtml(item.verdict)}</td><td>${escapeHtml(item.evidence)} ${link(item.sourceUrl, 'Source')}</td><td>${escapeHtml(item.nextAction)}</td></tr>`;
  }).join('\n');
  const standaloneSignals = `<h2>New-team signals: confirmed versus plausible</h2><div class="scroll"><table><thead><tr><th>Employer</th><th>Verdict</th><th>Evidence</th><th>Action</th></tr></thead><tbody>${signalRows}</tbody></table></div><h2>All 200 accounts</h2>`;
  const hubSignals = `<h3>New-team signals: confirmed versus plausible</h3><div class="table-wrap"><table class="tbl searchable"><thead><tr><th>Employer</th><th>Verdict</th><th>Evidence</th><th>Action</th></tr></thead><tbody>${signalRows}</tbody></table></div><h3>All 200 candidate accounts</h3>`;
  const html = `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>200-Account Pega Opportunity Watch</title><style>
body{font:15px/1.55 Georgia,serif;background:#f5f4ef;color:#1d2933;margin:0;padding:28px}main{max-width:1640px;margin:auto}h1{font:700 36px/1.1 Georgia,serif}a{color:#005d60}p{max-width:1050px}table{border-collapse:collapse;background:#fff;width:100%}th,td{padding:11px;border:1px solid #d6dcd9;text-align:left;vertical-align:top}th{background:#103d42;color:#fff;position:sticky;top:0}td:nth-child(4){min-width:230px}small{color:#53636c}input{padding:12px;width:min(500px,90vw);font-size:16px;margin:12px 0 24px}tr[hidden]{display:none}@media(max-width:800px){body{padding:12px}.scroll{overflow:auto}table{min-width:1200px}}
</style><main><h1>200-Account Pega Opportunity Watch</h1><p>Generated ${escapeHtml(result.generatedAt)} · Workday scan ${escapeHtml(result.scanAt)}. ${escapeHtml(result.selection)} ${escapeHtml(result.scanLimits)}</p><p><strong>Coverage:</strong> ${total('Official feed:')} checked Workday feeds, ${total('Official employer page:') + total('Official search:')} other official checks, ${total('Partial board:')} partial boards, ${total('Portal unreachable:')} unreachable and ${total('Not checked')} without a supported job-search feed. The separate career-page probe only tests reachability. None of these account counts establishes 200 Bengaluru Pega teams.</p><label>Filter rows <input id="filter" aria-label="Filter accounts" type="search" placeholder="Company, role, status, workstream"></label><div class="scroll"><table><thead><tr><th>#</th><th>Company / aliases</th><th>Search status &amp; portal probe</th><th>Official Bengaluru roles</th><th>Historical team signal</th><th>Old leads (not verified)</th><th>Careers / fit</th></tr></thead><tbody>${rows}</tbody></table></div></main><script>
const search=document.getElementById('filter');search.addEventListener('input',()=>{const q=search.value.toLowerCase();for(const row of document.querySelectorAll('tbody tr'))row.hidden=!row.textContent.toLowerCase().includes(q)});
</script></html>`;
  const htmlWithSignals = html.replace('<label>Filter rows', `${standaloneSignals}<label>Filter rows`)
    .replace("document.querySelectorAll('tbody tr')", "document.querySelectorAll('tbody')[1].querySelectorAll('tr')");
  await writeFile(htmlPath, htmlWithSignals, 'utf8');
  const hubPath = join(root, 'Pega_Career_Intelligence_Hub.html');
  let hub = await readFile(hubPath, 'utf8');
  const start = '<!-- PRODUCT_200_WATCH_START -->';
  const end = '<!-- PRODUCT_200_WATCH_END -->';
  const section = `${start}
<section class="section" id="product-200-watch">
<div class="head"><div class="bar"></div><h2>200-account product/GCC Pega opportunity watch · 12 Nov 2026</h2><p>Official openings, historical workstreams and profile-date signals for 200 distinct candidate accounts. This is NOT a list of 200 confirmed Bengaluru Pega teams. Only roles linked to an employer page and marked official were checked as open; older lead links are never live-verified. Workday snapshot: ${escapeHtml(result.scanAt)}; other official checks are individually dated.</p></div>
<div class="review-note">Coverage: ${total('Official feed:')} Workday searches, ${total('Official employer page:') + total('Official search:')} other official checks, ${total('Partial board:')} partial boards, ${total('Portal unreachable:')} unreachable, ${total('Not checked')} not checked via supported job-search feed. A reachable career homepage is NOT a job search. Use the hub search box to filter companies or roles.</div>
<div class="table-wrap"><table class="tbl searchable"><thead><tr><th>#</th><th>Company / aliases</th><th>Search status / portal probe</th><th>Official Bengaluru roles</th><th>Historical team signal</th><th>Older leads / profile dates</th><th>Careers / fit</th></tr></thead><tbody>${rows}</tbody></table></div>
<p class="sub">Full offline report: <a href="reports/Product_200_Pega_Opportunity_Watch_2026-11-12.html">Product 200 Opportunity Watch</a>. Data and evidence tiers: <code>reports/product_200_openings_watch_2026-11-12.json</code>.</p></section>
${end}`;
  const sectionWithSignals = section.replace('<div class="table-wrap"><table class="tbl searchable">',
    `${hubSignals}<div class="table-wrap"><table class="tbl searchable">`);
  const marker = new RegExp(`${start}[\\s\\S]*?${end}`);
  if (marker.test(hub)) hub = hub.replace(marker, sectionWithSignals);
  else if (hub.includes('<!-- OUTREACH_BLUEPRINT_END -->'))
    hub = hub.replace('<!-- OUTREACH_BLUEPRINT_END -->', `<!-- OUTREACH_BLUEPRINT_END -->\n${sectionWithSignals}`);
  else throw new Error('Hub outreach blueprint marker missing; will not insert watchlist');
  const nav = '<a href="#product-200-watch" style="color:#93c5fd;font-weight:700">200-account openings watch</a>';
  if (!hub.includes(nav)) {
    const anchor = /(<a href="#outreach-blueprint"[^>]*>[^<]*<\/a>)/;
    if (!anchor.test(hub)) throw new Error('Hub outreach nav anchor missing');
    hub = hub.replace(anchor, `$1${nav}`);
  }
  await writeFile(hubPath, hub, 'utf8');
  console.log(JSON.stringify({
    accounts: records.length, distinctCandidates: ordered.length, officialFeedAccounts: total('Official feed:'),
    extraOfficial: total('Official employer page:') + total('Official search:'),
    partial: total('Partial board:'), unreachable: total('Portal unreachable:'), notChecked: total('Not checked'),
    withRoles: records.filter(row => row.officialJobs.length).map(row => row.company),
    jsonPath, htmlPath
  }, null, 2));
} catch (error) {
  console.error(error);
  process.exitCode = 1;
}
