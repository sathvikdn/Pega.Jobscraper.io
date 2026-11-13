import { readFile, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const directory = dirname(fileURLToPath(import.meta.url));
const sourcePath = join(directory, 'bengaluru_pega_2026-11.json');
const hubPath = join(directory, 'Pega_Career_Intelligence_Hub.html');
const sectionStart = '<!-- BENGALURU_PEGA_SECTION_START -->';
const sectionEnd = '<!-- BENGALURU_PEGA_SECTION_END -->';
const navMarker = '<!-- TEAM_INSIDER_NAV -->';
const navLink = '<b>Bengaluru focus</b><a href="#bengaluru-pega" style="color:#38bdf8;font-weight:700">Bengaluru Pega map · Nov 2026</a>';

const escapeHtml = value => String(value ?? '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;');

const sourceLinks = sources => Array.isArray(sources) && sources.length ? sources
  .filter(source => Array.isArray(source) && /^https:\/\//.test(source[1] ?? ''))
  .map(([label, url]) => `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`)
  .join(' · ') : 'No source link recorded';

const countsTable = counts => `<div class="table-wrap"><table class="tbl searchable"><thead><tr><th>Metric</th><th>Count</th><th>Meaning</th></tr></thead><tbody>${counts
  .map(row => `<tr><td class="co">${escapeHtml(row[0])}</td><td><strong>${escapeHtml(row[1])}</strong></td><td>${escapeHtml(row[2])}</td></tr>`)
  .join('')}</tbody></table></div>`;

const tierCards = tiers => `<div class="grid3">${tiers.map(tier => `<div class="card"><h3>${escapeHtml(tier.name)}</h3><p>${escapeHtml(tier.why)}</p><p><strong>Companies:</strong> ${escapeHtml(tier.companies.join(', '))}</p></div>`).join('')}</div>`;

const teamTable = teams => `<div class="table-wrap"><table class="tbl searchable"><thead><tr><th>Rank / team</th><th>Base and shape</th><th>What they build</th><th>People signals</th><th>Fit, checks and outreach</th><th>Sources</th></tr></thead><tbody>${teams
  .map(team => `<tr id="blr-${escapeHtml(String(team.rank).padStart(2, '0'))}"><td class="co">#${escapeHtml(team.rank)} · ${escapeHtml(team.company)}<div class="sub">${escapeHtml(team.tier)}</div></td><td><strong>${escapeHtml(team.bengaluruBase)}</strong><br>${escapeHtml(team.teamShape)}</td><td>${escapeHtml(team.whatTheyBuild)}</td><td>${escapeHtml(team.peopleSignals)}</td><td><strong>Fit:</strong> ${escapeHtml(team.fitForYou)}<br><strong>Verify:</strong> ${escapeHtml(team.verifyBeforeApply)}<br><strong>Skills:</strong> ${escapeHtml(team.skillsToPrepare)}<br><strong>Outreach:</strong> ${escapeHtml(team.outreach)}</td><td class="sub">${sourceLinks(team.sources)}</td></tr>`)
  .join('')}</tbody></table></div>`;

const skillTable = rows => `<div class="table-wrap"><table class="tbl searchable"><thead><tr><th>Skill lane</th><th>Best Bengaluru targets</th><th>What to prepare</th></tr></thead><tbody>${rows
  .map(row => `<tr><td class="co">${escapeHtml(row[0])}</td><td>${escapeHtml(row[1])}</td><td>${escapeHtml(row[2])}</td></tr>`)
  .join('')}</tbody></table></div>`;

const applicationTable = rows => `<div class="table-wrap"><table class="tbl searchable"><thead><tr><th>Order</th><th>Teams</th><th>Action</th></tr></thead><tbody>${rows
  .map(row => `<tr><td class="co">${escapeHtml(row[0])}</td><td>${escapeHtml(row[1])}</td><td>${escapeHtml(row[2])}</td></tr>`)
  .join('')}</tbody></table></div>`;

const buildSection = data => `${sectionStart}
<section class="section" id="bengaluru-pega" style="overflow-wrap:anywhere">
<div class="head"><div class="bar"></div><h2>Bengaluru Pega map · product and GCC teams · ${escapeHtml(data.asOf)}</h2><p>A Bengaluru-first slice of the Pega employer universe: real counts, strongest teams, what each team appears to build, people signals, role-fit checks, skills to prepare and outreach order.</p></div>
<div class="review-note"><strong>Read this first:</strong> ${escapeHtml(data.method)}</div>
<h3>Reality check: is it 260 product companies?</h3>${countsTable(data.counts)}
<h3>Priority tiers</h3>${tierCards(data.tiers)}
<h3>Deep-dive Bengaluru team map</h3>${teamTable(data.teams)}
<h3>Skills to prepare by target lane</h3>${skillTable(data.skillMap)}
<h3>Application order</h3>${applicationTable(data.applicationOrder)}
<div class="review-note">Data file: <code>bengaluru_pega_2026-11.json</code> · regenerate with <code>node build_bengaluru_pega_section.mjs</code>. This section is Bengaluru-first and should be read alongside the all-India <a href="#team-insider">team insider</a>, <a href="#people-audit">people audit</a> and <a href="#employer-coverage">159-row employer coverage</a>.</div>
</section>
${sectionEnd}`;

try {
  const data = JSON.parse(await readFile(sourcePath, 'utf8'));
  let hub = await readFile(hubPath, 'utf8');
  const section = buildSection(data);
  const sectionPattern = new RegExp(`${sectionStart}[\\s\\S]*?${sectionEnd}`);

  if (sectionPattern.test(hub)) {
    hub = hub.replace(sectionPattern, section);
  } else {
    hub = hub.replace('<!-- TEAM_INSIDER_SECTION_START -->', `${section}\n\n<!-- TEAM_INSIDER_SECTION_START -->`);
  }

  if (!hub.includes(navLink)) {
    hub = hub.replace(navMarker, `${navMarker}${navLink}`);
  }

  await writeFile(hubPath, hub, 'utf8');
  console.log(`Bengaluru Pega section written for ${data.teams.length} teams.`);
} catch (error) {
  console.error(error);
  process.exit(1);
}
