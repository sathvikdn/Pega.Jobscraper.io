import { readFile, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const directory = dirname(fileURLToPath(import.meta.url));
const sourcePath = join(directory, 'team_insider_2026-11.json');
const hubPath = join(directory, 'Pega_Career_Intelligence_Hub.html');
const sectionStart = '<!-- TEAM_INSIDER_SECTION_START -->';
const sectionEnd = '<!-- TEAM_INSIDER_SECTION_END -->';
// First run inserts ahead of the live job refresh so team understanding leads the page.
const insertBeforeMarker = '<section class="section" id="live-refresh">';
const navStart = '<!-- TEAM_INSIDER_NAV -->';
const navLink = `${navStart}<b>Team insider</b><a href="#team-insider" style="color:#a3e635;font-weight:700">How teams work · Nov 2026</a>`;
const navAnchor = '<nav class="nav">';

const escapeHtml = (value) => String(value ?? '')
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#39;');

const safeHttpsUrl = (url) => {
  // Source URLs come from a hand-edited ledger; only render https links.
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'https:' ? parsed.href : null;
  } catch {
    return null;
  }
};

const sourceLinks = (sources = []) => sources
  .map(([label, url]) => {
    const href = safeHttpsUrl(url);
    return href ? `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>` : escapeHtml(label);
  })
  .join(' · ');

const dossierLink = path => {
  // Only allow simple relative .html paths inside this project, never URLs or parent traversal.
  if (typeof path !== 'string' || path.includes('..') || !/^[\w\-./]+\.html$/.test(path)) return '';
  return `<p><a href="${escapeHtml(path)}" style="font-weight:700">Open the interview dossier →</a></p>`;
};

const peopleTable = people => Array.isArray(people) && people.length ? `<h4>Key people and what they indicate</h4><div class="table-wrap"><table class="tbl searchable"><thead><tr><th>Person</th><th>Role / level signal</th><th>What they appear to work on</th><th>Best outreach use</th></tr></thead><tbody>${people
  .map(person => `<tr><td class="co">${escapeHtml(person.name)}</td><td>${escapeHtml(person.role)}</td><td>${escapeHtml(person.work)}</td><td>${escapeHtml(person.use)}</td></tr>`)
  .join('')}</tbody></table></div>` : '';

const glanceTable = rows => `<div class="table-wrap"><table class="tbl searchable"><thead><tr><th>Team</th><th>Where</th><th>Office rhythm</th><th>Work-life signal</th><th>Best thing</th><th>Main watch-out</th></tr></thead><tbody>${rows
  .map(row => `<tr><td class="co">${escapeHtml(row[0])}</td>${row.slice(1).map(cell => `<td>${escapeHtml(cell)}</td>`).join('')}</tr>`)
  .join('')}</tbody></table></div>`;

const companyCard = company => `<div class="card" id="insider-${escapeHtml(company.id)}"><span class="pill info">${escapeHtml(company.hubs)}</span><h3>${escapeHtml(company.name)}</h3>
<p><strong>How the team is structured:</strong> ${escapeHtml(company.team_shape)}</p>
<p><strong>What they actually build:</strong> ${escapeHtml(company.what_they_build)}</p>
${peopleTable(company.people)}
<p><strong>What it's like day to day:</strong> ${escapeHtml(company.vibe)}</p>
<p><strong>Ratings:</strong> ${escapeHtml(company.ratings)}</p>
<p><strong>Watch-outs:</strong> ${escapeHtml(company.watch_outs)}</p>
<p><strong>For you:</strong> ${escapeHtml(company.your_angle)}</p>
${dossierLink(company.dossier)}<p class="sub">Sources: ${sourceLinks(company.sources)}</p></div>`;

const buildSection = ledger => `${sectionStart}
<section class="section" id="team-insider" style="overflow-wrap:anywhere">
<div class="head"><div class="bar"></div><h2>Team insider · how each Pega team works · ${escapeHtml(ledger.asOf)}</h2><p>For each team: how it is structured, what it actually builds, and what working there is like. Refreshed on ${escapeHtml(ledger.asOf)} for ${ledger.companies.length} employers that matter most to your search. Lens: ${escapeHtml(ledger.candidate_lens)}</p></div>
<div class="review-note"><strong>How to read this:</strong> ${escapeHtml(ledger.note)}</div>
<h3>At a glance</h3>${glanceTable(ledger.at_a_glance)}
<h3>Team by team</h3><div class="review-grid">
${ledger.companies.map(companyCard).join('\n')}
</div>
<div class="review-note">Data file: <code>team_insider_2026-11.json</code> · regenerate with <code>node build_team_insider_section.mjs</code>. The deeper retained rosters remain in <a href="#team-dossiers">team dossiers</a>, <a href="#gcc-culture-ranking">GCC culture ranking</a> and <a href="#creative-market-exposure">what Pega teams build</a>.</div>
</section>
${sectionEnd}`;

try {
  const ledger = JSON.parse(await readFile(sourcePath, 'utf8'));
  if (!Array.isArray(ledger.companies) || ledger.companies.length === 0) throw new Error('Ledger has no companies');
  let hub = await readFile(hubPath, 'utf8');
  const section = buildSection(ledger);
  const startIndex = hub.indexOf(sectionStart);
  if (startIndex !== -1) {
    const endIndex = hub.indexOf(sectionEnd, startIndex);
    if (endIndex === -1) throw new Error('Start marker found without end marker');
    hub = hub.slice(0, startIndex) + section + hub.slice(endIndex + sectionEnd.length);
  } else {
    const insertIndex = hub.indexOf(insertBeforeMarker);
    if (insertIndex === -1) throw new Error('Insertion marker #live-refresh not found');
    hub = hub.slice(0, insertIndex) + section + '\n\n' + hub.slice(insertIndex);
  }
  if (!hub.includes(navStart)) {
    if (!hub.includes(navAnchor)) throw new Error('Sidebar nav not found');
    hub = hub.replace(navAnchor, navAnchor + navLink);
  }
  await writeFile(hubPath, hub, 'utf8');
  console.log(`Team insider section written for ${ledger.companies.length} companies.`);
} catch (error) {
  console.error(`Team insider build failed: ${error.message}`);
  process.exitCode = 1;
}
