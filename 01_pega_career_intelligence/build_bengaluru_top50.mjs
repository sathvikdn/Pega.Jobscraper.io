import { readFile, writeFile, mkdir, access, copyFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

// Merges every Bengaluru research ledger into one Top-50 dataset, then renders it into the
// hub (#bengaluru-top50), a Markdown export and the Deep Dossiers dashboard.
const directory = dirname(fileURLToPath(import.meta.url));
const paths = {
  deepdives: join(directory, 'bengaluru_team_deepdives_2026-11.json'),
  profiles: join(directory, 'bengaluru_gcc_profiles_2026-11.json'),
  map22: join(directory, 'bengaluru_pega_2026-11.json'),
  insider: join(directory, 'team_insider_2026-11.json'),
  enriched: join(directory, 'team_intelligence_enriched.json'),
  supplement: join(directory, 'bengaluru_top50_supplement_2026-11.json'),
  output: join(directory, 'bengaluru_top50_2026-11.json'),
  hub: join(directory, 'Pega_Career_Intelligence_Hub.html'),
  report: join(directory, 'reports', 'Bengaluru_Pega_Top50_2026-11.md'),
  dossiers: join(directory, 'JobChange', 'Pega_Deep_Dossiers.html'),
  dossiersBackup: join(directory, 'JobChange', 'Pega_Deep_Dossiers.pre-top50-2026-11-11.html')
};

// Rank order = Bengaluru fit + evidence strength. Patterns match company names across all ledgers.
const TOP50 = [
  ['Commonwealth Bank (CBA India)', /commonwealth/i], ['First Citizens India', /first citizens/i], ['Empower India', /^empower/i],
  ['Daimler Truck Innovation Center India (DTICI)', /daimler truck/i], ['Booking Holdings India', /booking/i], ['JPMorganChase India', /jpmorgan|jp morgan/i],
  ['Nokia India', /nokia/i], ['Broadridge India', /broadridge/i], ['Telstra India', /telstra/i], ['Cisco India', /cisco/i],
  ['Pegasystems India (Bengaluru)', /pegasystems/i], ['Siemens', /siemens/i], ['John Deere India (JDTCI)', /deere/i],
  ['Ameriprise India', /ameriprise/i], ['Société Générale GSC', /soci[eé]t[eé] g[eé]n[eé]rale/i], ['BT Group', /^bt\b/i],
  ['Verizon', /verizon/i], ['Morgan Stanley', /morgan stanley/i], ['Goldman Sachs', /goldman/i], ['VOIS (Vodafone)', /vois|vodafone/i],
  ['Sun Life Global Solutions', /sun ?life/i], ['NatWest Group', /natwest/i], ['Standard Chartered', /standard chartered/i],
  ['Shell India', /^shell/i], ['Carelon Global Solutions India', /carelon/i], ['Wells Fargo India', /wells fargo/i],
  ['MUFG Global Service (MUFG Bank)', /^mufg(?! pension)/i], ['ANZ', /^anz/i], ['BNY', /^bny/i], ['HSBC', /hsbc/i],
  ['Nike India', /nike/i], ['Intel India', /^intel\b/i], ['Levi Strauss & Co. India', /levi/i], ['GE HealthCare', /ge health/i],
  ['Unilever (UniOps / Digital Hub)', /unilever/i], ['Ford Business Solutions (Bengaluru satellite)', /^ford/i],
  ['Mercedes-Benz R&D India (MBRDI) — current employer', /mercedes/i], ['Orange Business', /orange business/i],
  ['American Express', /american express/i], ['Amadeus Labs', /amadeus/i], ['Dell Technologies', /^dell/i],
  ['Fidelity National Financial India (FNF)', /fidelity national/i], ['PayPal', /paypal/i], ['ING (ING Hubs India)', /^ing\b/i],
  ['Optum / UnitedHealth Group', /optum|unitedhealth/i], ['Evernorth / Cigna', /evernorth|cigna/i], ['Conduent', /conduent/i],
  ['Deutsche Bank', /deutsche bank/i], ['Northern Trust', /northern trust/i], ['Tesco Bengaluru', /tesco/i]
];
const priorityLabel = { 1: '1 · Peer first', 2: '2 · Architect/lead', 3: '3 · Manager (role ID)', 4: '4 · Senior/TA (context only)' };

const escapeHtml = value => String(value ?? '')
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
const isProfileUrl = url => /^https:\/\/([a-z]+\.)?linkedin\.com\/in\//.test(url ?? '');
const isSafeUrl = url => /^https:\/\//.test(url ?? '');
const normaliseName = name => String(name ?? '').toLowerCase()
  .replace(/\((left|alumnus|alumna|vendor[^)]*)\)/g, '').replace(/[^a-z]/g, '');
const slug = value => String(value).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50);
const unique = items => [...new Set(items.filter(Boolean))];

// Infer contact order from the title when a ledger does not record one.
const inferPriority = (title = '') => {
  if (/recruit|talent|\bta\b/i.test(title)) return 4;
  if (/director|head|country|svp|executive|\bed\b/i.test(title)) return 4;
  if (/manager|chapter lead|vice president|\bvp\b|avp|agm|dgm/i.test(title)) return 3;
  if (/architect|lead|lsa|principal|staff|left|alumn/i.test(title)) return 2;
  return 1;
};

const findBy = (list, pattern, nameOf) => list.filter(item => pattern.test(nameOf(item) ?? ''));

try {
  const [deepdives, profiles, map22, insider, enriched, supplement] = await Promise.all(
    [paths.deepdives, paths.profiles, paths.map22, paths.insider, paths.enriched, paths.supplement]
      .map(async path => JSON.parse(await readFile(path, 'utf8')))
  );

  // Global URL lookup so a name found in one ledger gets its profile link from another.
  const urlByName = new Map();
  const rememberUrl = (name, url) => {
    if (isProfileUrl(url) && !urlByName.has(normaliseName(name))) urlByName.set(normaliseName(name), url);
  };
  deepdives.teams.forEach(team => team.people.forEach(person => rememberUrl(person.name, person.url)));
  Object.values(supplement.companies).forEach(entry => entry.people.forEach(person => rememberUrl(person.name, person.url)));
  enriched.companies.forEach(company => (company.team_members ?? []).forEach(member => rememberUrl(member.name, member.linkedin)));
  [...profiles.profiles, ...map22.teams, ...insider.companies, ...deepdives.teams].forEach(item =>
    (item.sources ?? []).forEach(([label, url]) => rememberUrl(String(label).replace(/\s*\(.*$/, ''), url)));

  const companies = TOP50.map(([display, pattern], index) => {
    const deep = findBy(deepdives.teams, pattern, team => team.company)[0];
    const profile = findBy(profiles.profiles, pattern, item => item.company)[0];
    const mapTeam = findBy(map22.teams, pattern, team => team.company)[0];
    const insiderTeam = findBy(insider.companies, pattern, item => item.name)[0];
    const enrichedCompany = findBy(enriched.companies, pattern, item => item.name)[0];
    const supplementEntries = Object.entries(supplement.companies).filter(([key]) => pattern.test(key)).map(([, entry]) => entry);

    // People: hand-researched first, then supplements, then retained ledgers. Deduplicate by name.
    const people = [];
    const seen = new Set();
    const addPerson = person => {
      const key = normaliseName(person.name);
      if (!key || seen.has(key)) return;
      seen.add(key);
      const url = isProfileUrl(person.url) ? person.url : (urlByName.get(key) ?? '');
      people.push({
        name: person.name, title: person.title ?? '', cert: person.cert ?? '', tenure: person.tenure ?? '',
        worksOn: person.worksOn ?? '', why: person.why ?? '', location: person.location ?? '',
        url, priority: person.priority ?? inferPriority(person.title), source: person.source
      });
    };
    (deep?.people ?? []).forEach(person => addPerson({ ...person, source: 'Deep dive (Nov 2026)' }));
    supplementEntries.flatMap(entry => entry.people).forEach(person => addPerson({ ...person, source: 'Top-50 lookup (Nov 2026)' }));
    (insiderTeam?.people ?? []).forEach(person => addPerson({ name: person.name, title: person.role, worksOn: person.work, why: person.use, source: 'Team insider (Nov 2026)' }));
    (profile?.people ?? []).forEach(([name, title, cert, tenure]) => addPerson({ name, title, cert, tenure, source: 'GCC profile lookup (Nov 2026)' }));
    (enrichedCompany?.team_members ?? [])
      .filter(member => /bengaluru|bangalore/i.test(member.location ?? '') || (enrichedCompany.team_members.length <= 6))
      .forEach(member => addPerson({
        name: member.name, title: member.title, cert: member.certs ?? (member.certifications ?? []).join(', '),
        location: member.location, url: member.linkedin,
        worksOn: (member.career ?? []).map(step => step.detail).filter(Boolean).join(' ').slice(0, 220),
        source: 'Retained team ledger (Sep 2026)'
      }));
    people.sort((left, right) => left.priority - right.priority || Number(Boolean(right.url)) - Number(Boolean(left.url)));

    const workstreams = [];
    const seenWork = new Set();
    const addWork = row => {
      const key = String(row[1] ?? '').slice(0, 80).toLowerCase();
      if (!row[1] || seenWork.has(key)) return;
      seenWork.add(key);
      workstreams.push(row);
    };
    (deep?.workstreams ?? []).forEach(addWork);
    supplementEntries.flatMap(entry => entry.workstreams ?? []).forEach(addWork);
    if (mapTeam?.whatTheyBuild) addWork(['What they build (Bengaluru map)', mapTeam.whatTheyBuild, 'Bengaluru map, Nov 2026']);
    if (insiderTeam?.what_they_build) addWork(['What they build (team insider)', insiderTeam.what_they_build, 'Team insider, Nov 2026']);
    if (!deep) (profile?.stack ?? []).forEach(item => addWork(['Architecture signal', item, 'GCC profile lookup, Nov 2026']));
    if (enrichedCompany?.projects) addWork(['Retained project ledger', enrichedCompany.projects, 'Team intelligence ledger, Sep 2026']);

    const sources = unique([...(deep?.sources ?? []), ...(profile?.sources ?? []), ...(mapTeam?.sources ?? []), ...(insiderTeam?.sources ?? [])]
      .filter(source => isSafeUrl(source[1])).map(source => JSON.stringify(source))).map(text => JSON.parse(text));

    const firstPeer = people.find(person => person.priority === 1);
    const firstLead = people.find(person => person.priority === 2);
    const generatedPlan = firstPeer
      ? `Message ${firstPeer.name} first for team reality${firstLead ? `, then ask ${firstLead.name} one specific technical question` : ''}. Contact managers only with a live role ID.`
      : 'No current peer-level Bengaluru contact established; watch official career pages and contact only with a live role ID.';

    return {
      rank: index + 1,
      company: display,
      tier: profile?.fit ?? '',
      size: profile?.size ?? enrichedCompany?.team_size ?? 'Not established',
      domains: profile?.domains ?? (enrichedCompany?.domains ?? []).join(', '),
      hiring: profile?.hiring ?? enrichedCompany?.hiring_status ?? 'Unknown',
      confidence: profile?.confidence ?? 'Medium',
      oneLine: deep?.oneLine ?? mapTeam?.teamShape ?? `${profile?.size ?? ''}. ${profile?.domains ?? ''}.`,
      howTeamWorks: deep?.howTeamWorks ?? insiderTeam?.team_shape ?? mapTeam?.teamShape ?? '',
      culture: insiderTeam ? `${insiderTeam.vibe} Ratings: ${insiderTeam.ratings}` : '',
      techStack: unique([...(enrichedCompany?.tech_stack ?? [])]),
      workstreams,
      people,
      fit: unique([profile?.fit, mapTeam?.fitForYou]).join(' '),
      verify: mapTeam?.verifyBeforeApply ?? '',
      skills: mapTeam?.skillsToPrepare ?? (enrichedCompany?.certifications_required ?? []).join(', '),
      connectPlan: deep?.connectPlan ?? mapTeam?.outreach ?? generatedPlan,
      askThem: deep?.askThem ?? (mapTeam?.verifyBeforeApply ? [mapTeam.verifyBeforeApply] : []),
      redFlags: deep?.redFlags ?? (insiderTeam?.watch_outs ? [insiderTeam.watch_outs] : []),
      sources
    };
  });

  const notInTop50 = profiles.profiles
    .filter(profile => !TOP50.some(([, pattern]) => pattern.test(profile.company)))
    .map(profile => ({ company: profile.company, finding: profile.stack.join(' '), hiring: profile.hiring }));

  const dataset = { asOf: '2026-11-11', method: deepdives.method, companies, notInTop50 };
  await writeFile(paths.output, JSON.stringify(dataset, null, 2), 'utf8');

  // ---------- Hub section ----------
  const personCell = person => isProfileUrl(person.url)
    ? `<a href="${escapeHtml(person.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(person.name)}</a>`
    : escapeHtml(person.name);
  const card = item => `<div class="card" id="top50-${escapeHtml(slug(item.company))}"><span class="pill info">#${item.rank} · Confidence ${escapeHtml(item.confidence)}</span><h3>${item.rank}. ${escapeHtml(item.company)}</h3>
<p><strong>In one line:</strong> ${escapeHtml(item.oneLine)}</p>
<p><strong>Team size:</strong> ${escapeHtml(item.size)} · <strong>Domains:</strong> ${escapeHtml(item.domains)}</p>
<p><strong>Hiring verdict:</strong> ${escapeHtml(item.hiring)}</p>
<p><strong>Fit for you:</strong> ${escapeHtml(item.fit)}</p>
${item.techStack.length ? `<p><strong>Tech stack seen:</strong> ${escapeHtml(item.techStack.join(' · '))}</p>` : ''}
<h4>What the team actually does</h4><div class="table-wrap"><table class="tbl searchable"><thead><tr><th>Workstream</th><th>What it is</th><th>Evidence</th></tr></thead><tbody>${item.workstreams
  .map(row => `<tr><td class="co">${escapeHtml(row[0])}</td><td>${escapeHtml(row[1])}</td><td>${escapeHtml(row[2])}</td></tr>`).join('') || '<tr><td colspan="3">No workstream evidence established.</td></tr>'}</tbody></table></div>
${item.howTeamWorks ? `<p><strong>How the team works:</strong> ${escapeHtml(item.howTeamWorks)}</p>` : ''}
${item.culture ? `<p><strong>Day to day:</strong> ${escapeHtml(item.culture)}</p>` : ''}
<h4>Who to connect with (${item.people.length} people, contact order)</h4><div class="table-wrap"><table class="tbl searchable"><thead><tr><th>Order</th><th>Person</th><th>Title · cert · tenure</th><th>Works on / why</th><th>Source</th></tr></thead><tbody>${item.people
  .map(person => `<tr><td>${escapeHtml(priorityLabel[person.priority] ?? person.priority)}</td><td class="co">${personCell(person)}${person.location ? `<div class="sub">${escapeHtml(person.location)}</div>` : ''}</td><td>${escapeHtml(person.title)}<div class="sub">${escapeHtml([person.cert, person.tenure].filter(Boolean).join(' · '))}</div></td><td>${escapeHtml(person.worksOn)}${person.why ? `<div class="sub">${escapeHtml(person.why)}</div>` : ''}</td><td class="sub">${escapeHtml(person.source)}</td></tr>`).join('') || '<tr><td colspan="5">No Bengaluru Pega personnel established.</td></tr>'}</tbody></table></div>
<p><strong>Connect plan:</strong> ${escapeHtml(item.connectPlan)}</p>
${item.askThem.length ? `<p><strong>Ask them:</strong></p><ul>${item.askThem.map(question => `<li>${escapeHtml(question)}</li>`).join('')}</ul>` : ''}
${item.skills ? `<p><strong>Skills to prepare:</strong> ${escapeHtml(item.skills)}</p>` : ''}
${item.redFlags.length ? `<p><strong>Watch-outs:</strong> ${escapeHtml(item.redFlags.join(' · '))}</p>` : ''}
${item.sources.length ? `<p class="sub">Sources: ${item.sources.map(([label, url]) => `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`).join(' · ')}</p>` : ''}
<p class="sub"><a href="#bengaluru-top50">↑ Back to the Top-50 table</a></p></div>`;

  const summary = `<div class="table-wrap"><table class="tbl searchable"><thead><tr><th>#</th><th>Company</th><th>Team size</th><th>Hiring verdict</th><th>Contacts</th><th>Message first</th></tr></thead><tbody>${companies
    .map(item => {
      const first = item.people.find(person => person.priority === 1) ?? item.people[0];
      return `<tr><td>${item.rank}</td><td class="co"><a href="#top50-${escapeHtml(slug(item.company))}">${escapeHtml(item.company)}</a></td><td>${escapeHtml(item.size)}</td><td>${escapeHtml(item.hiring)}</td><td>${item.people.length} (${item.people.filter(person => isProfileUrl(person.url)).length} linked)</td><td>${first ? personCell(first) : '—'}</td></tr>`;
    }).join('')}</tbody></table></div>`;

  const appendix = `<div class="table-wrap"><table class="tbl searchable"><thead><tr><th>Not in Top 50</th><th>Finding</th><th>Hiring</th></tr></thead><tbody>${notInTop50
    .map(row => `<tr><td class="co">${escapeHtml(row.company)}</td><td>${escapeHtml(row.finding)}</td><td>${escapeHtml(row.hiring)}</td></tr>`).join('')}</tbody></table></div>`;

  const totalPeople = companies.reduce((sum, item) => sum + item.people.length, 0);
  const linkedPeople = companies.reduce((sum, item) => sum + item.people.filter(person => isProfileUrl(person.url)).length, 0);
  const sectionStart = '<!-- BENGALURU_TOP50_START -->';
  const sectionEnd = '<!-- BENGALURU_TOP50_END -->';
  const section = `${sectionStart}
<section class="section" id="bengaluru-top50" style="overflow-wrap:anywhere;border-left:4px solid #38bdf8">
<div class="head"><div class="bar" style="background:#38bdf8"></div><h2>Bengaluru Top 50 · every Pega product/GCC team in one place · ${dataset.asOf}</h2><p>${companies.length} companies ranked by Bengaluru fit and evidence strength, with ${totalPeople} named people (${linkedPeople} with public LinkedIn profiles). Each company shows what the team does, how it works, who to contact in what order, what to ask and the watch-outs. Companies below rank 30 have thin or negative Bengaluru evidence and are kept so you don't research them again.</p></div>
<div class="review-note"><strong>Method and limits:</strong> ${escapeHtml(dataset.method)}</div>
<div class="review-note"><strong>Message rules:</strong> Keep connection notes under 300 characters. Name the workstream you read about, ask one specific question, and never ask a stranger for a referral in the first message. Contact managers only with a role ID; while a CBA interview is in progress, do not message its interviewers.</div>
<h3>Top 50 at a glance</h3>${summary}
<h3>Company by company</h3><div class="review-grid">${companies.map(card).join('\n')}</div>
<h3>Checked but not in the Top 50</h3>${appendix}
<div class="review-note">Generated by <code>node build_bengaluru_top50.mjs</code> from all Bengaluru ledgers · dataset: <code>bengaluru_top50_2026-11.json</code> · Markdown: <code>reports/Bengaluru_Pega_Top50_2026-11.md</code> · also merged into <code>JobChange/Pega_Deep_Dossiers.html</code>.</div>
</section>
${sectionEnd}`;

  let hub = await readFile(paths.hub, 'utf8');
  const top50Pattern = /<!-- BENGALURU_TOP50_START -->[\s\S]*?<!-- BENGALURU_TOP50_END -->/;
  const deepPattern = /<!-- BENGALURU_TEAM_DEEPDIVES_START -->[\s\S]*?<!-- BENGALURU_TEAM_DEEPDIVES_END -->/;
  if (top50Pattern.test(hub)) hub = hub.replace(top50Pattern, section);
  else if (deepPattern.test(hub)) hub = hub.replace(deepPattern, section); // Top 50 supersedes the 10-team view.
  else if (hub.includes('<!-- BENGALURU_GCC_PROFILES_END -->')) hub = hub.replace('<!-- BENGALURU_GCC_PROFILES_END -->', `<!-- BENGALURU_GCC_PROFILES_END -->\n\n${section}`);
  else throw new Error('No Bengaluru anchor found in hub');
  const deepNav = '<a href="#bengaluru-team-deepdives" style="color:#38bdf8;font-weight:700">Team deep dives + who to contact</a>';
  const top50Nav = '<a href="#bengaluru-top50" style="color:#38bdf8;font-weight:700">Bengaluru Top 50 · teams + contacts</a>';
  if (hub.includes(deepNav)) hub = hub.replace(deepNav, top50Nav);
  else if (!hub.includes(top50Nav)) hub = hub.replace('<b>Bengaluru focus</b>', `<b>Bengaluru focus</b>${top50Nav}`);
  await writeFile(paths.hub, hub, 'utf8');

  // ---------- Markdown ----------
  const markdown = [
    `# Bengaluru Pega Top 50 — ${dataset.asOf}`, '', dataset.method, '',
    '| # | Company | Team size | Hiring verdict | Contacts |', '|---|---|---|---|---|',
    ...companies.map(item => `| ${item.rank} | ${item.company} | ${item.size} | ${item.hiring} | ${item.people.length} |`), '',
    ...companies.flatMap(item => [
      `## ${item.rank}. ${item.company}`, '', item.oneLine, '',
      `- **Team size:** ${item.size}`, `- **Domains:** ${item.domains}`, `- **Hiring verdict:** ${item.hiring}`, `- **Fit:** ${item.fit}`,
      ...(item.techStack.length ? [`- **Tech stack:** ${item.techStack.join(', ')}`] : []), '',
      '### What the team does', '| Workstream | What it is | Evidence |', '|---|---|---|',
      ...item.workstreams.map(row => `| ${row[0]} | ${String(row[1]).replace(/\|/g, '/')} | ${row[2]} |`), '',
      ...(item.howTeamWorks ? [`**How the team works:** ${item.howTeamWorks}`, ''] : []),
      '### Who to connect with', '| Order | Person | Title · cert · tenure | Works on |', '|---|---|---|---|',
      ...item.people.map(person => `| ${priorityLabel[person.priority]} | ${isProfileUrl(person.url) ? `[${person.name}](${person.url})` : person.name} | ${[person.title, person.cert, person.tenure].filter(Boolean).join(' · ')} | ${String(person.worksOn || person.why).replace(/\|/g, '/')} |`), '',
      `**Connect plan:** ${item.connectPlan}`, '',
      ...(item.askThem.length ? ['**Ask them:**', ...item.askThem.map(question => `- ${question}`), ''] : []),
      ...(item.redFlags.length ? [`**Watch-outs:** ${item.redFlags.join(' · ')}`, ''] : [])
    ])
  ].join('\n');
  await mkdir(dirname(paths.report), { recursive: true });
  await writeFile(paths.report, markdown, 'utf8');

  // ---------- Deep Dossiers dashboard ----------
  // The dashboard renders strings with innerHTML, so every added string is HTML-escaped.
  // Always rebuild from the untouched pre-Top-50 snapshot so repeated runs stay idempotent.
  try { await access(paths.dossiersBackup); } catch { await copyFile(paths.dossiers, paths.dossiersBackup); }
  let dossierHtml = await readFile(paths.dossiersBackup, 'utf8');
  const dataStart = dossierHtml.indexOf('const DATA=');
  const dataEnd = dossierHtml.indexOf('\n', dataStart);
  if (dataStart < 0 || dataEnd < 0) throw new Error('DATA block not found in Deep Dossiers');
  const dossierData = JSON.parse(dossierHtml.slice(dataStart + 'const DATA='.length, dataEnd).replace(/;\s*$/, ''));
  const roleFor = priority => ({ 1: [5, 'Developer'], 2: [3, 'Architecture & Leads'], 3: [1, 'Management'], 4: [1, 'Management'] }[priority] ?? [5, 'Developer']);
  const contactType = priority => ({ 1: 'Peer', 2: 'Architect', 3: 'Hiring Manager', 4: 'Leadership' }[priority] ?? 'Peer');
  let added = 0;
  let updated = 0;

  companies.forEach(item => {
    const pattern = TOP50[item.rank - 1][1];
    let entry = dossierData.find(company => pattern.test(company.name));
    if (!entry) {
      entry = {
        name: escapeHtml(item.company), sector: escapeHtml(item.domains.split(',')[0] || 'Other'), locations: ['Bengaluru'],
        team_size: escapeHtml(item.size), maturity: 'Medium', hiring_status: 'Stable', projects: '', tech_stack: [], domains: [],
        certifications_required: ['CSSA'], team_members: [], highlights: [], _sector_group: 'Other',
        _hiring_playbook: { business_reality: '', project_phase: 'Existing & Mature', skills_to_master: [], difficulty: 'Medium', salary_range: 'Verify with recruiter', approach_ranking: [], pitch_to_manager: [], insider_tip: '' }
      };
      dossierData.push(entry);
      added += 1;
    } else {
      updated += 1;
    }
    const workText = item.workstreams.slice(0, 6).map(row => `${row[0]}: ${row[1]}`).join(' • ');
    entry.projects = escapeHtml(`[Nov 2026 Bengaluru refresh] ${item.oneLine} ${workText}`) + (entry.projects && !entry.projects.startsWith('[Nov 2026') ? ` | Earlier research: ${entry.projects}` : '');
    entry.highlights = [
      escapeHtml(`Bengaluru Top 50 rank #${item.rank} · ${item.size}`),
      escapeHtml(`Hiring verdict (Nov 2026): ${item.hiring}`),
      escapeHtml(`Fit: ${item.fit}`),
      ...(entry.highlights ?? []).filter(text => !/Bengaluru Top 50 rank|Hiring verdict \(Nov 2026\)|^Fit: /.test(text))
    ];
    if (!(entry.locations ?? []).some(city => /bengaluru|bangalore/i.test(city))) entry.locations = [...(entry.locations ?? []), 'Bengaluru'];
    if (/expand|active/i.test(item.hiring)) entry.hiring_status = 'Actively Growing';
    else if (/frozen|contract|declin|moving off/i.test(item.hiring)) entry.hiring_status = 'Declining';
    else if (/stable/i.test(item.hiring)) entry.hiring_status = 'Stable';

    const members = entry.team_members ?? [];
    const memberNames = new Set(members.map(member => normaliseName(member.name)));
    item.people.forEach(person => {
      if (memberNames.has(normaliseName(person.name))) return;
      const [level, label] = roleFor(person.priority);
      members.push({
        name: escapeHtml(person.name), title: escapeHtml(person.title), certs: escapeHtml(person.cert),
        location: escapeHtml(person.location || 'Bengaluru'), tenure: escapeHtml(person.tenure),
        _role_level: level, _role_label: label, ...(isProfileUrl(person.url) ? { linkedin: person.url } : {})
      });
    });
    members.sort((left, right) => (left._role_level ?? 5) - (right._role_level ?? 5));
    entry.team_members = members;

    const playbook = entry._hiring_playbook ?? (entry._hiring_playbook = {});
    playbook.bangalore_intel = {
      has_bangalore: item.people.length > 0,
      summary: escapeHtml(`${item.oneLine} ${item.howTeamWorks}`.trim()),
      contacts: item.people.filter(person => person.priority <= 3).slice(0, 8).map(person => ({
        name: escapeHtml(person.name), title: escapeHtml(person.title), certs: escapeHtml(person.cert),
        role_type: contactType(person.priority), ...(isProfileUrl(person.url) ? { linkedin: person.url } : {})
      })),
      tip: escapeHtml(item.connectPlan)
    };
    const askText = item.askThem.length ? `Ask: ${item.askThem.join(' / ')}` : '';
    const flagText = item.redFlags.length ? `Watch-outs: ${item.redFlags.join(' / ')}` : '';
    playbook.insider_tip = escapeHtml([askText, flagText].filter(Boolean).join(' — ')) || playbook.insider_tip || '';
    if (item.skills) playbook.skills_to_master = unique([...item.skills.split(/,\s*/).map(escapeHtml), ...(playbook.skills_to_master ?? [])]).slice(0, 14);
    if (!playbook.business_reality) playbook.business_reality = escapeHtml(item.oneLine);
  });

  const peopleTotal = dossierData.reduce((sum, company) => sum + (company.team_members ?? []).length, 0);
  dossierHtml = dossierHtml.slice(0, dataStart) + 'const DATA=' + JSON.stringify(dossierData) + ';' + dossierHtml.slice(dataEnd);
  dossierHtml = dossierHtml.replace(/— \d+ Companies \| \d+\+ People<\/title>/, `— ${dossierData.length} Companies | ${peopleTotal}+ People</title>`);
  // The header counters are static text in the original page, so keep them in step with DATA.
  const growing = dossierData.filter(company => /growing/i.test(company.hiring_status ?? '')).length;
  dossierHtml = dossierHtml
    .replace(/<b class="pv" id="sCo">\d+<\/b>/, `<b class="pv" id="sCo">${dossierData.length}</b>`)
    .replace(/<b class="gv" id="sPpl">\d+\+?<\/b>/, `<b class="gv" id="sPpl">${peopleTotal}+</b>`)
    .replace(/<b class="gv" id="sGrow">\d+<\/b>/, `<b class="gv" id="sGrow">${growing}</b>`);
  await writeFile(paths.dossiers, dossierHtml, 'utf8');

  console.log(JSON.stringify({ top50: companies.length, people: totalPeople, linkedPeople, notInTop50: notInTop50.length, dossiers: { updated, added, companies: dossierData.length, people: peopleTotal } }));
} catch (error) {
  console.error(error);
  process.exit(1);
}
