import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const directory = dirname(fileURLToPath(import.meta.url));
const sourcePath = join(directory, 'bengaluru_team_deepdives_2026-11.json');
const hubPath = join(directory, 'Pega_Career_Intelligence_Hub.html');
const reportPath = join(directory, 'reports', 'Bengaluru_Pega_Team_Deepdives_2026-11.md');
const sectionStart = '<!-- BENGALURU_TEAM_DEEPDIVES_START -->';
const sectionEnd = '<!-- BENGALURU_TEAM_DEEPDIVES_END -->';
const anchorAfter = '<!-- BENGALURU_GCC_PROFILES_END -->';
const navAfter = '<a href="#bengaluru-gcc-profiles" style="color:#38bdf8;font-weight:700">Bengaluru GCC profiles (63)</a>';
const navLink = '<a href="#bengaluru-team-deepdives" style="color:#38bdf8;font-weight:700">Team deep dives + who to contact</a>';
const priorityLabel = { 1: '1 · Peer first', 2: '2 · Architect/lead', 3: '3 · Manager (role ID)', 4: '4 · Senior/TA (context only)' };

const escapeHtml = value => String(value ?? '')
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
const isSafeUrl = url => /^https:\/\//.test(url ?? '');
const slug = value => String(value).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50);

const personLinkHtml = person => isSafeUrl(person.url)
  ? `<a href="${escapeHtml(person.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(person.name)}</a>`
  : escapeHtml(person.name);

const teamHtml = team => {
  const people = [...team.people].sort((left, right) => left.priority - right.priority);
  const sources = (team.sources ?? []).filter(source => isSafeUrl(source[1]))
    .map(([label, url]) => `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`).join(' · ');
  return `<div class="card" id="deep-${escapeHtml(slug(team.company))}"><span class="pill info">${escapeHtml(team.base)}</span><h3>${escapeHtml(team.company)}</h3>
<p><strong>In one line:</strong> ${escapeHtml(team.oneLine)}</p>
<h4>What the team actually does</h4><div class="table-wrap"><table class="tbl searchable"><thead><tr><th>Workstream</th><th>What it is</th><th>Evidence</th></tr></thead><tbody>${team.workstreams
  .map(row => `<tr><td class="co">${escapeHtml(row[0])}</td><td>${escapeHtml(row[1])}</td><td>${escapeHtml(row[2])}</td></tr>`).join('')}</tbody></table></div>
<p><strong>How the team works:</strong> ${escapeHtml(team.howTeamWorks)}</p>
<h4>Who to connect with (public LinkedIn profiles, in contact order)</h4><div class="table-wrap"><table class="tbl searchable"><thead><tr><th>Order</th><th>Person</th><th>Title · certification · tenure</th><th>What they work on</th><th>Why contact them</th></tr></thead><tbody>${people
  .map(person => `<tr><td>${escapeHtml(priorityLabel[person.priority] ?? person.priority)}</td><td class="co">${personLinkHtml(person)}</td><td>${escapeHtml(person.title)}<br><span class="sub">${escapeHtml(person.cert)} · ${escapeHtml(person.tenure)}</span></td><td>${escapeHtml(person.worksOn)}</td><td>${escapeHtml(person.why)}</td></tr>`).join('')}</tbody></table></div>
<p><strong>Connect plan:</strong> ${escapeHtml(team.connectPlan)}</p>
<p><strong>Ask them:</strong></p><ul>${team.askThem.map(question => `<li>${escapeHtml(question)}</li>`).join('')}</ul>
<p><strong>Watch-outs:</strong> ${escapeHtml(team.redFlags.join(' · '))}</p>
${sources ? `<p class="sub">Sources: ${sources}</p>` : ''}</div>`;
};

const buildSection = data => `${sectionStart}
<section class="section" id="bengaluru-team-deepdives" style="overflow-wrap:anywhere">
<div class="head"><div class="bar"></div><h2>Bengaluru team deep dives · what each team does and who to contact · ${escapeHtml(data.asOf)}</h2><p>${escapeHtml(data.teams.length)} priority teams. Each has its workstreams with evidence, how the team is organised, named people with public LinkedIn profiles in contact order, a connect plan, questions to ask and watch-outs.</p></div>
<div class="review-note"><strong>Method and limits:</strong> ${escapeHtml(data.method)}</div>
<div class="review-note"><strong>Message rules:</strong> Keep connection notes under 300 characters. Name the team or workstream you read about, ask one specific question, and never ask a stranger for a referral in the first message. Contact managers only with a role ID; while a CBA interview is in progress, do not message its interviewers.</div>
<p>Jump to: ${data.teams.map(team => `<a href="#deep-${escapeHtml(slug(team.company))}">${escapeHtml(team.company)}</a>`).join(' · ')}</p>
<div class="review-grid">${data.teams.map(teamHtml).join('\n')}</div>
<div class="review-note">Data file: <code>bengaluru_team_deepdives_2026-11.json</code> · regenerate with <code>node build_bengaluru_team_deepdives.mjs</code> · playbook export: <code>reports/Bengaluru_Pega_Team_Deepdives_2026-11.md</code>.</div>
</section>
${sectionEnd}`;

const teamMarkdown = team => {
  const people = [...team.people].sort((left, right) => left.priority - right.priority);
  return [
    `## ${team.company}`,
    `**Base:** ${team.base}`,
    '',
    team.oneLine,
    '',
    '### What the team actually does',
    '| Workstream | What it is | Evidence |',
    '|---|---|---|',
    ...team.workstreams.map(row => `| ${row[0]} | ${row[1]} | ${row[2]} |`),
    '',
    `**How the team works:** ${team.howTeamWorks}`,
    '',
    '### Who to connect with (in order)',
    '| Order | Person | Title · cert · tenure | Works on | Why |',
    '|---|---|---|---|---|',
    ...people.map(person => `| ${priorityLabel[person.priority] ?? person.priority} | ${isSafeUrl(person.url) ? `[${person.name}](${person.url})` : person.name} | ${person.title} · ${person.cert} · ${person.tenure} | ${person.worksOn} | ${person.why} |`),
    '',
    `**Connect plan:** ${team.connectPlan}`,
    '',
    '**Ask them:**',
    ...team.askThem.map(question => `- ${question}`),
    '',
    `**Watch-outs:** ${team.redFlags.join(' · ')}`,
    '',
    `**Sources:** ${(team.sources ?? []).filter(source => isSafeUrl(source[1])).map(([label, url]) => `[${label}](${url})`).join(' · ')}`,
    ''
  ].join('\n');
};

try {
  const data = JSON.parse(await readFile(sourcePath, 'utf8'));
  if (!Array.isArray(data.teams) || data.teams.length === 0) throw new Error('No teams in ledger');

  let hub = await readFile(hubPath, 'utf8');
  const section = buildSection(data);
  const sectionPattern = new RegExp(`${sectionStart}[\\s\\S]*?${sectionEnd}`);
  if (sectionPattern.test(hub)) {
    hub = hub.replace(sectionPattern, section);
  } else if (hub.includes(anchorAfter)) {
    hub = hub.replace(anchorAfter, `${anchorAfter}\n\n${section}`);
  } else {
    throw new Error('Bengaluru GCC profiles marker not found; run build_bengaluru_gcc_profiles.mjs first');
  }
  if (!hub.includes(navLink)) {
    if (!hub.includes(navAfter)) throw new Error('Bengaluru GCC profiles nav link not found');
    hub = hub.replace(navAfter, `${navAfter}${navLink}`);
  }
  await writeFile(hubPath, hub, 'utf8');

  const markdown = [
    `# Bengaluru Pega Team Deep Dives — ${data.asOf}`,
    '',
    data.method,
    '',
    'Message rules: keep notes under 300 characters, name the workstream, ask one specific question, no referral ask in the first message, and contact managers only with a role ID.',
    '',
    ...data.teams.map(teamMarkdown)
  ].join('\n');
  await mkdir(dirname(reportPath), { recursive: true });
  await writeFile(reportPath, markdown, 'utf8');

  const peopleCount = data.teams.reduce((total, team) => total + team.people.length, 0);
  const linkedCount = data.teams.reduce((total, team) => total + team.people.filter(person => isSafeUrl(person.url)).length, 0);
  console.log(JSON.stringify({ teams: data.teams.length, people: peopleCount, withProfileUrl: linkedCount, report: reportPath }));
} catch (error) {
  console.error(error);
  process.exit(1);
}
