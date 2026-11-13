import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const directory = dirname(fileURLToPath(import.meta.url));
const sourcePath = join(directory, 'bengaluru_outreach_blueprint_2026-11.json');
const hubPath = join(directory, 'Pega_Career_Intelligence_Hub.html');
const reportPath = join(directory, 'reports', 'Bengaluru_Pega_Outreach_Blueprint_2026-11.md');
const sectionStart = '<!-- OUTREACH_BLUEPRINT_START -->';
const sectionEnd = '<!-- OUTREACH_BLUEPRINT_END -->';
const anchorAfter = '<!-- BENGALURU_TOP50_END -->';
const navAfter = '<a href="#bengaluru-top50" style="color:#38bdf8;font-weight:700">Bengaluru Top 50 · teams + contacts</a>';
const navLink = '<a href="#outreach-blueprint" style="color:#a3e635;font-weight:700">Outreach blueprint + 7-day sprint</a>';
const maxScriptWords = 125;

const escapeHtml = value => String(value ?? '')
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
const wordCount = text => String(text).trim().split(/\s+/).filter(Boolean).length;
const list = items => `<ul>${items.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`;

try {
  const data = JSON.parse(await readFile(sourcePath, 'utf8'));

  // Enforce the brief: every outreach script must stay under the word limit.
  const tooLong = data.scripts.filter(script => wordCount(script.text) > maxScriptWords);
  if (tooLong.length) throw new Error(`Scripts over ${maxScriptWords} words: ${tooLong.map(script => `${script.persona}/${script.tier} (${wordCount(script.text)})`).join(', ')}`);

  const tierName = Object.fromEntries(data.tiers.map(tier => [tier.id, tier.name]));
  const tierCards = data.tiers.map(tier => `<div class="card"><span class="pill info">${escapeHtml(tier.id)}</span><h3>${escapeHtml(tier.name)}</h3>
<p><strong>Companies:</strong> ${escapeHtml(tier.companies.join(', '))}</p>
<p><strong>Evidence:</strong> ${escapeHtml(tier.evidence)}</p>
<p><strong>Production friction points:</strong></p>${list(tier.friction)}
<p><strong>Your talking points:</strong></p>${list(tier.talkingPoints)}</div>`).join('\n');

  const scriptRows = data.scripts.map(script => `<tr><td class="co">${escapeHtml(script.persona)}</td><td>${escapeHtml(tierName[script.tier] ?? script.tier)}</td><td>${escapeHtml(script.text)}<div class="sub">${wordCount(script.text)} words · use for: ${escapeHtml(script.useFor)}</div></td></tr>`).join('');
  const checklistRows = data.checklist.map(([name, rule], index) => `<tr><td class="co">${index + 1}. ${escapeHtml(name)}</td><td>${escapeHtml(rule)}</td></tr>`).join('');
  const dossierRows = data.dossiers.map(item => `<tr><td class="co">${escapeHtml(item.company)}<div class="sub">${escapeHtml(item.tier)}</div></td><td>${escapeHtml(item.stack)}</td><td>${escapeHtml(item.hook)}</td><td>${escapeHtml(item.sequence)}</td><td>${list(item.questions)}</td><td>${escapeHtml(item.redFlags)}</td></tr>`).join('');
  const dayRows = data.sprint.days.map(([day, plan]) => `<tr><td class="co">${escapeHtml(day)}</td><td>${escapeHtml(plan)}</td></tr>`).join('');

  const section = `${sectionStart}
<section class="section" id="outreach-blueprint" style="overflow-wrap:anywhere;border-left:4px solid #a3e635">
<div class="head"><div class="bar" style="background:#a3e635"></div><h2>Outreach blueprint · architecture fit, scripts, micro-dossiers, 7-day sprint · ${escapeHtml(data.asOf)}</h2><p>Built from the Bengaluru Top 50. Tiers group companies by architectural fit with your Kafka, replay/dead-letter, metadata-mapping and observability work.</p></div>
<div class="review-note"><strong>Your positioning:</strong> ${escapeHtml(data.candidate.headline)}<br><strong>Proof points:</strong> ${escapeHtml(data.candidate.proofPoints.join(' · '))}<br><strong>Stay honest:</strong> ${escapeHtml(data.candidate.honesty)}</div>
<h3>Module 1 · Architecture alignment &amp; GCC tiers</h3><div class="review-grid">${tierCards}</div>
<h3>Module 2 · Outreach scripts (all under ${maxScriptWords} words)</h3><div class="table-wrap"><table class="tbl searchable"><thead><tr><th>Persona</th><th>Tier</th><th>Script (replace [brackets])</th></tr></thead><tbody>${scriptRows}</tbody></table></div>
<h3>Module 3 · Pre-outreach checklist</h3><div class="table-wrap"><table class="tbl searchable"><thead><tr><th>Check</th><th>What to confirm</th></tr></thead><tbody>${checklistRows}</tbody></table></div>
<h4>Checklist applied to the 15 highest-conviction targets</h4><p class="sub">Interview questions are derived from each firm's public JDs and workstreams, not from leaked interview reports. Treat them as likely, not guaranteed.</p><div class="table-wrap"><table class="tbl searchable"><thead><tr><th>Company</th><th>Production stack</th><th>Hook</th><th>Contact sequence</th><th>Likely deep-dive questions</th><th>Red flags</th></tr></thead><tbody>${dossierRows}</tbody></table></div>
<h3>Module 4 · 7-day sprint (15 targets)</h3>${list(data.sprint.rules)}<div class="table-wrap"><table class="tbl searchable"><thead><tr><th>Day</th><th>Actions</th></tr></thead><tbody>${dayRows}</tbody></table></div>
<div class="review-note">Data file: <code>bengaluru_outreach_blueprint_2026-11.json</code> · regenerate with <code>node build_bengaluru_outreach_blueprint.mjs</code> (after the Top-50 builder) · Markdown: <code>reports/Bengaluru_Pega_Outreach_Blueprint_2026-11.md</code>. Contact names and profiles are in the <a href="#bengaluru-top50">Bengaluru Top 50</a>.</div>
</section>
${sectionEnd}`;

  let hub = await readFile(hubPath, 'utf8');
  const sectionPattern = new RegExp(`${sectionStart}[\\s\\S]*?${sectionEnd}`);
  if (sectionPattern.test(hub)) hub = hub.replace(sectionPattern, section);
  else if (hub.includes(anchorAfter)) hub = hub.replace(anchorAfter, `${anchorAfter}\n\n${section}`);
  else throw new Error('Top-50 section marker not found; run build_bengaluru_top50.mjs first');
  if (!hub.includes(navLink)) {
    if (!hub.includes(navAfter)) throw new Error('Top-50 nav link not found');
    hub = hub.replace(navAfter, `${navAfter}${navLink}`);
  }
  await writeFile(hubPath, hub, 'utf8');

  const markdown = [
    `# Bengaluru Pega Outreach Blueprint — ${data.asOf}`, '',
    `**Positioning:** ${data.candidate.headline}`, '', '**Proof points:**', ...data.candidate.proofPoints.map(point => `- ${point}`), '',
    `**Stay honest:** ${data.candidate.honesty}`, '',
    '## Module 1 · Architecture alignment & GCC tiers', '',
    ...data.tiers.flatMap(tier => [`### ${tier.id} · ${tier.name}`, `**Companies:** ${tier.companies.join(', ')}`, '', `**Evidence:** ${tier.evidence}`, '', '**Friction points:**', ...tier.friction.map(item => `- ${item}`), '', '**Talking points:**', ...tier.talkingPoints.map(item => `1. ${item}`), '']),
    '## Module 2 · Outreach scripts', '',
    ...data.scripts.flatMap(script => [`### ${script.persona} · ${tierName[script.tier]} (${wordCount(script.text)} words)`, `*Use for: ${script.useFor}*`, '', `> ${script.text}`, '']),
    '## Module 3 · Pre-outreach checklist', '',
    ...data.checklist.map(([name, rule], index) => `${index + 1}. **${name}:** ${rule}`), '',
    '### Applied to the top 15', '',
    ...data.dossiers.flatMap(item => [`#### ${item.company} (${item.tier})`, `- **Stack:** ${item.stack}`, `- **Hook:** ${item.hook}`, `- **Sequence:** ${item.sequence}`, `- **Likely deep-dive questions:** ${item.questions.join(' · ')}`, `- **Red flags:** ${item.redFlags}`, '']),
    '## Module 4 · 7-day sprint', '', ...data.sprint.rules.map(rule => `- ${rule}`), '',
    ...data.sprint.days.map(([day, plan]) => `**${day}:** ${plan}\n`)
  ].join('\n');
  await mkdir(dirname(reportPath), { recursive: true });
  await writeFile(reportPath, markdown, 'utf8');

  console.log(JSON.stringify({ tiers: data.tiers.length, scripts: data.scripts.map(script => wordCount(script.text)), dossiers: data.dossiers.length, days: data.sprint.days.length }));
} catch (error) {
  console.error(error);
  process.exit(1);
}
