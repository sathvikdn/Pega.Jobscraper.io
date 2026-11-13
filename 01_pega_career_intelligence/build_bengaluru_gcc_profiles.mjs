import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const directory = dirname(fileURLToPath(import.meta.url));
const sourcePath = join(directory, 'bengaluru_gcc_profiles_2026-11.json');
const hubPath = join(directory, 'Pega_Career_Intelligence_Hub.html');
const reportPath = join(directory, 'reports', 'Bengaluru_Pega_GCC_Profiles_2026-11.md');
const sectionStart = '<!-- BENGALURU_GCC_PROFILES_START -->';
const sectionEnd = '<!-- BENGALURU_GCC_PROFILES_END -->';
const navMarker = '<!-- TEAM_INSIDER_NAV -->';
const navLink = '<a href="#bengaluru-gcc-profiles" style="color:#38bdf8;font-weight:700">Bengaluru GCC profiles (63)</a>';

// Tier order drives both the hub and the Markdown so the strongest targets are read first.
const tiers = [
  { key: 'A', label: 'Tier A — strong Bengaluru Pega fit', test: fit => /^(very high|high|excellent)/i.test(fit) },
  { key: 'B', label: 'Tier B — worth a referral conversation', test: fit => /^medium/i.test(fit) },
  { key: 'M', label: 'Benchmark', test: fit => /^benchmark/i.test(fit) },
  { key: 'C', label: 'Tier C — low fit, unproven or negative findings', test: () => true }
];
const tierOf = profile => tiers.find(tier => tier.test(profile.fit ?? '')) ?? tiers[tiers.length - 1];

const escapeHtml = value => String(value ?? '')
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

const safeSources = sources => (Array.isArray(sources) ? sources : [])
  .filter(source => Array.isArray(source) && /^https:\/\//.test(source[1] ?? ''));

const slug = value => String(value).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60);

const peopleText = person => `${person[0]} — ${person[1]} · ${person[2]} · ${person[3]}`;

const htmlCard = profile => {
  const people = profile.people.length
    ? `<ul>${profile.people.map(person => `<li>${escapeHtml(peopleText(person))}</li>`).join('')}</ul>`
    : '<p class="sub">No current Bengaluru Pega personnel established in this pass.</p>';
  const sources = safeSources(profile.sources)
    .map(([label, url]) => `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`)
    .join(' · ');
  return `<div class="card" id="gcc-${escapeHtml(slug(profile.company))}"><span class="pill info">Confidence: ${escapeHtml(profile.confidence)}</span><h3>${escapeHtml(profile.company)} Pega GCC Profile</h3>
<p><strong>Estimated Team Size:</strong> ${escapeHtml(profile.size)}</p>
<p><strong>Core Domains:</strong> ${escapeHtml(profile.domains)}</p>
<p><strong>Tech Stack &amp; Architecture:</strong></p><ul>${profile.stack.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
<p><strong>Key Personnel:</strong></p>${people}
<p><strong>Hiring Verdict:</strong> ${escapeHtml(profile.hiring)}</p>
<p><strong>Fit for you:</strong> ${escapeHtml(profile.fit)}</p>
${sources ? `<p class="sub">Sources: ${sources}</p>` : ''}</div>`;
};

const summaryTable = groups => `<div class="table-wrap"><table class="tbl searchable"><thead><tr><th>Company</th><th>Tier</th><th>Team size</th><th>Hiring verdict</th><th>Confidence</th></tr></thead><tbody>${groups
  .flatMap(({ tier, items }) => items.map(profile => `<tr><td class="co"><a href="#gcc-${escapeHtml(slug(profile.company))}">${escapeHtml(profile.company)}</a></td><td>${escapeHtml(tier.key)}</td><td>${escapeHtml(profile.size)}</td><td>${escapeHtml(profile.hiring)}</td><td>${escapeHtml(profile.confidence)}</td></tr>`))
  .join('')}</tbody></table></div>`;

const buildSection = (data, groups) => `${sectionStart}
<section class="section" id="bengaluru-gcc-profiles" style="overflow-wrap:anywhere">
<div class="head"><div class="bar"></div><h2>Bengaluru Pega GCC profiles · ${escapeHtml(data.profiles.length)} entries · ${escapeHtml(data.asOf)}</h2><p>One profile per employer in the Bengaluru list: team size, domains, architecture, key personnel (name, title, certification, tenure), hiring verdict and fit. Grouped negative findings are kept so the same dead ends are not researched again.</p></div>
<div class="review-note"><strong>Method:</strong> ${escapeHtml(data.method)}</div>
<h3>All profiles at a glance</h3>${summaryTable(groups)}
${groups.map(({ tier, items }) => `<h3>${escapeHtml(tier.label)} (${items.length})</h3><div class="review-grid">${items.map(htmlCard).join('\n')}</div>`).join('\n')}
<div class="review-note">Data file: <code>bengaluru_gcc_profiles_2026-11.json</code> · regenerate with <code>node build_bengaluru_gcc_profiles.mjs</code> · Markdown export: <code>reports/Bengaluru_Pega_GCC_Profiles_2026-11.md</code>.</div>
</section>
${sectionEnd}`;

const markdownProfile = profile => [
  `## ${profile.company} Pega GCC Profile`,
  `- Estimated Team Size: ${profile.size}`,
  `- Core Domains: ${profile.domains}`,
  '- Tech Stack & Architecture:',
  ...profile.stack.map(item => `  - ${item}`),
  '- Key Personnel:',
  ...(profile.people.length ? profile.people.map(person => `  - ${peopleText(person)}`) : ['  - None established in this pass']),
  `- Hiring Verdict: ${profile.hiring}`,
  `- Fit for you: ${profile.fit} (confidence: ${profile.confidence})`,
  ...(safeSources(profile.sources).length ? [`- Sources: ${safeSources(profile.sources).map(([label, url]) => `[${label}](${url})`).join(' · ')}`] : []),
  ''
].join('\n');

const buildMarkdown = (data, groups) => [
  `# Bengaluru Pega GCC Profiles — ${data.asOf}`,
  '',
  data.method,
  '',
  ...groups.flatMap(({ tier, items }) => [`# ${tier.label} (${items.length})`, '', ...items.map(markdownProfile)])
].join('\n');

try {
  const data = JSON.parse(await readFile(sourcePath, 'utf8'));
  if (!Array.isArray(data.profiles) || data.profiles.length === 0) throw new Error('No profiles in ledger');

  const groups = tiers
    .map(tier => ({ tier, items: data.profiles.filter(profile => tierOf(profile) === tier) }))
    .filter(group => group.items.length);

  let hub = await readFile(hubPath, 'utf8');
  const section = buildSection(data, groups);
  const sectionPattern = new RegExp(`${sectionStart}[\\s\\S]*?${sectionEnd}`);
  if (sectionPattern.test(hub)) {
    hub = hub.replace(sectionPattern, section);
  } else if (hub.includes('<!-- BENGALURU_PEGA_SECTION_END -->')) {
    // Place the profiles directly after the Bengaluru map so the two Bengaluru views sit together.
    hub = hub.replace('<!-- BENGALURU_PEGA_SECTION_END -->', `<!-- BENGALURU_PEGA_SECTION_END -->\n\n${section}`);
  } else {
    throw new Error('Bengaluru map section marker not found; run build_bengaluru_pega_section.mjs first');
  }
  if (!hub.includes(navLink)) {
    const mapLink = '<a href="#bengaluru-pega" style="color:#38bdf8;font-weight:700">Bengaluru Pega map · Nov 2026</a>';
    hub = hub.includes(mapLink) ? hub.replace(mapLink, `${mapLink}${navLink}`) : hub.replace(navMarker, `${navMarker}${navLink}`);
  }
  await writeFile(hubPath, hub, 'utf8');

  await mkdir(dirname(reportPath), { recursive: true });
  await writeFile(reportPath, buildMarkdown(data, groups), 'utf8');

  console.log(JSON.stringify({ profiles: data.profiles.length, tiers: Object.fromEntries(groups.map(group => [group.tier.key, group.items.length])), report: reportPath }));
} catch (error) {
  console.error(error);
  process.exit(1);
}
