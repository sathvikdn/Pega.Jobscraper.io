import { readFile, writeFile } from 'node:fs/promises';
import { basename, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const directory = dirname(fileURLToPath(import.meta.url));
const sourcePath = resolve(directory, process.argv[2] ?? 'Pega_Career_Intelligence_Hub.html');
const csvPath = resolve(directory, 'linkedin_profiles.csv');
const queuePath = resolve(directory, 'linkedin_manual_outreach_queue.html');

const htmlEntities = new Map([
  ['amp', '&'],
  ['quot', '"'],
  ['apos', "'"],
  ['nbsp', ' '],
  ['rsquo', '’'],
  ['lsquo', '‘'],
  ['rdquo', '”'],
  ['ldquo', '“'],
  ['ndash', '–'],
  ['mdash', '—']
]);

const decodeHtml = value => value
  .replace(/&#x([0-9a-f]+);/gi, (_match, code) => {
    try {
      return String.fromCodePoint(Number.parseInt(code, 16));
    } catch (error) {
      return _match;
    }
  })
  .replace(/&#(\d+);/g, (_match, code) => {
    try {
      return String.fromCodePoint(Number.parseInt(code, 10));
    } catch (error) {
      return _match;
    }
  })
  .replace(/&([a-z]+);/gi, (match, entity) => htmlEntities.get(entity.toLowerCase()) ?? match);

const normalizeText = value => decodeHtml(value)
  .replace(/\s+/g, ' ')
  .trim();

const stripHtml = value => normalizeText(value
  .replace(/<br\s*\/?>/gi, '\n')
  .replace(/<\/(p|div|td|th|tr|li|h[1-6])>/gi, '\n')
  .replace(/<[^>]*>/g, ' '));

const stripHtmlLines = value => decodeHtml(value
  .replace(/<br\s*\/?>/gi, '\n')
  .replace(/<\/(p|div|td|th|tr|li|h[1-6])>/gi, '\n')
  .replace(/<[^>]*>/g, ' '))
  .split('\n')
  .map(line => line.replace(/\s+/g, ' ').trim())
  .filter(Boolean);

const csvCell = value => `"${String(value ?? '').replace(/"/g, '""')}"`;
const htmlEscape = value => String(value ?? '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;');

const jsonScriptEscape = value => JSON.stringify(value)
  .replace(/&/g, '\\u0026')
  .replace(/</g, '\\u003c')
  .replace(/>/g, '\\u003e');

const normalizeLinkedInProfileUrl = href => {
  try {
    const decodedHref = decodeHtml(href);
    const parsedUrl = new URL(decodedHref);
    const host = parsedUrl.hostname.toLowerCase().replace(/^www\./, '');
    const pathParts = parsedUrl.pathname.split('/').filter(Boolean);
    if (host !== 'linkedin.com' || pathParts[0] !== 'in' || !pathParts[1]) return null;
    const slugMatch = pathParts[1].match(/^[a-z0-9_-]+/i);
    if (!slugMatch) return null;
    return `https://www.linkedin.com/in/${slugMatch[0]}`;
  } catch (error) {
    return null;
  }
};

const getEnclosingBlock = (html, anchorStart) => {
  const rowStart = html.lastIndexOf('<tr', anchorStart);
  const rowEnd = html.indexOf('</tr>', anchorStart);
  if (rowStart !== -1 && rowEnd !== -1) return html.slice(rowStart, rowEnd + '</tr>'.length);
  const cardStart = html.lastIndexOf('<div class="card"', anchorStart);
  const cardEnd = html.indexOf('</div>', anchorStart);
  if (cardStart !== -1 && cardEnd !== -1) return html.slice(cardStart, cardEnd + '</div>'.length);
  return html.slice(Math.max(0, anchorStart - 500), Math.min(html.length, anchorStart + 500));
};

const getSectionLabel = (html, anchorStart) => {
  const sectionStart = html.lastIndexOf('<section', anchorStart);
  if (sectionStart === -1) return '';
  const sectionSnippet = html.slice(sectionStart, anchorStart);
  const idMatch = sectionSnippet.match(/<section\b[^>]*\bid=["']([^"']+)["']/i);
  const headings = [...sectionSnippet.matchAll(/<h[1-3][^>]*>([\s\S]*?)<\/h[1-3]>/gi)].map(match => stripHtml(match[1])).filter(Boolean);
  const heading = headings.at(-1) ?? '';
  return [idMatch?.[1] ?? '', heading].filter(Boolean).join(' · ');
};

const companyPattern = /\b(Booking|Cisco|Wells Fargo|JPMC|JPMorgan|Standard Chartered|First Citizens|CBA|Shell|John Deere|Optum|Barclays|BNY|Commonwealth Bank|Bankwest|NAB|ANZ|Telstra|Vodafone|HSBC|Citi|Accenture|TCS|Infosys|Cognizant|Capgemini|HCL|LTIMindtree|Pegasystems)\b/i;
const nonCompanyPattern = /\b(Index-supported|Checked|evidence|correction|promotion|scope|limited|verified|stale|signal|route|Lead|Developer|Engineer|Architect|Manager|System|Pega|CLSA|CSSA|yrs|current|historical|association|cluster)\b/i;

const cleanCompanyCandidate = value => {
  const candidate = normalizeText(value.replace(/^Original directory association:\s*/i, '').split(' · ')[0]);
  if (!candidate || /^https?:/i.test(candidate)) return '';
  if (companyPattern.test(candidate)) return candidate;
  if (nonCompanyPattern.test(candidate)) return '';
  return candidate.length <= 60 ? candidate : '';
};

const inferCompany = (name, blockHtml) => {
  const lines = stripHtmlLines(blockHtml);
  const cleanName = normalizeText(name.replace(/\s+—\s+.*$/, '').replace(/\s+\([^)]*\)$/, ''));
  const nameIndex = lines.findIndex(line => line === cleanName || line === name || line.startsWith(`${cleanName} `));
  if (nameIndex >= 0 && lines[nameIndex + 1]) {
    const nextLineCompany = cleanCompanyCandidate(lines[nameIndex + 1]);
    if (nextLineCompany) return nextLineCompany;
  }
  const associationLine = lines.find(line => /^Original directory association:/i.test(line));
  if (associationLine) return cleanCompanyCandidate(associationLine);
  const companyLine = lines.find(line => companyPattern.test(line));
  return companyLine ? cleanCompanyCandidate(companyLine) : '';
};

const buildConnectionNote = profile => {
  const cleanName = profile.name.replace(/\s+—\s+.*$/, '').replace(/\s+\([^)]*\)$/, '').trim();
  const firstName = cleanName.split(/\s+/)[0] || 'there';
  const companyPart = profile.company ? ` at ${profile.company}` : '';
  const note = `Hi ${firstName}, I came across your Pega work${companyPart}. I’m exploring Pega SSA/architect roles and would value connecting and learning from your perspective. Thanks, Sathvik`;
  return note.length <= 300 ? note : `Hi ${firstName}, I came across your Pega work. I’m exploring Pega SSA/architect roles and would value connecting and learning from your perspective. Thanks, Sathvik`;
};

const extractProfiles = html => {
  const profiles = new Map();
  const anchorRegex = /<a\b[^>]*href=["']([^"']*linkedin\.com\/in\/[^"']*)["'][^>]*>([\s\S]*?)<\/a>/gi;
  let match;
  while ((match = anchorRegex.exec(html))) {
    const url = normalizeLinkedInProfileUrl(match[1]);
    if (!url) continue;
    const name = stripHtml(match[2]) || url.split('/').at(-1);
    const blockHtml = getEnclosingBlock(html, match.index);
    const section = getSectionLabel(html, match.index);
    const company = inferCompany(name, blockHtml);
    const context = stripHtml(blockHtml).slice(0, 700);
    const existingProfile = profiles.get(url);
    const profile = {
      name,
      url,
      company,
      section,
      context
    };
    if (!existingProfile || profile.context.length > existingProfile.context.length) profiles.set(url, profile);
  }
  return [...profiles.values()].map((profile, index) => ({
    id: index + 1,
    ...profile,
    note: buildConnectionNote(profile),
    status: '',
    notes: ''
  }));
};

const renderQueueHtml = profiles => `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LinkedIn Manual Outreach Queue</title>
<style>
:root { color-scheme: light dark; font-family: Inter, Segoe UI, Arial, sans-serif; }
body { margin: 0; background: #0f172a; color: #e5e7eb; }
header { position: sticky; top: 0; z-index: 2; padding: 18px 24px; background: rgba(15, 23, 42, .96); border-bottom: 1px solid #334155; }
h1 { margin: 0 0 8px; font-size: 24px; }
main { padding: 20px 24px 40px; }
.controls { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
input, select, textarea, button { border: 1px solid #475569; border-radius: 10px; background: #111827; color: #f8fafc; font: inherit; }
input, select { padding: 10px 12px; }
input[type="search"] { min-width: min(420px, 100%); }
button, a.button { display: inline-flex; align-items: center; gap: 6px; padding: 9px 12px; text-decoration: none; border: 1px solid #38bdf8; border-radius: 10px; background: #075985; color: white; cursor: pointer; }
button.secondary, a.secondary { border-color: #64748b; background: #1e293b; }
.summary { margin-top: 10px; color: #cbd5e1; }
.notice { margin: 14px 0 0; padding: 12px; border: 1px solid #f59e0b; border-radius: 12px; background: rgba(245, 158, 11, .12); color: #fde68a; }
.grid { display: grid; gap: 14px; }
.card { border: 1px solid #334155; border-radius: 16px; padding: 16px; background: #111827; box-shadow: 0 12px 30px rgba(0, 0, 0, .22); }
.card h2 { margin: 0 0 6px; font-size: 18px; }
.meta { color: #cbd5e1; font-size: 14px; }
.context { margin: 10px 0; color: #d1d5db; font-size: 14px; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }
textarea { width: 100%; min-height: 78px; padding: 10px; resize: vertical; box-sizing: border-box; }
.status { display: inline-block; padding: 3px 8px; border-radius: 999px; background: #334155; color: #e2e8f0; font-size: 12px; }
.status.connected { background: #166534; }
.status.skipped { background: #7f1d1d; }
.hidden { display: none; }
</style>
</head>
<body>
<header>
<h1>LinkedIn Manual Outreach Queue</h1>
<div class="controls">
<input id="search" type="search" placeholder="Search name, company, section, context">
<select id="filter">
<option value="all">All profiles</option>
<option value="pending">Pending</option>
<option value="connected">Marked connected</option>
<option value="skipped">Skipped</option>
</select>
<button class="secondary" id="copyUrls">Copy all profile URLs</button>
<button class="secondary" id="resetStatuses">Reset local statuses</button>
</div>
<div class="summary" id="summary"></div>
<div class="notice">This queue is intentionally manual. It opens profiles and copies notes only when you click; it does not log in, scrape LinkedIn, click Connect, or send requests.</div>
</header>
<main><div class="grid" id="profiles"></div></main>
<script type="application/json" id="profile-data">${jsonScriptEscape(profiles)}</script>
<script>
try {
  const profiles = JSON.parse(document.getElementById('profile-data').textContent);
  const storageKey = 'linkedin-manual-outreach-status-v1';
  const statusStore = JSON.parse(localStorage.getItem(storageKey) || '{}');
  const list = document.getElementById('profiles');
  const search = document.getElementById('search');
  const filter = document.getElementById('filter');
  const summary = document.getElementById('summary');
  const save = () => localStorage.setItem(storageKey, JSON.stringify(statusStore));
  const escapeHtml = value => String(value || '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const copyText = async text => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (error) {
      const holder = document.createElement('textarea');
      holder.value = text;
      document.body.appendChild(holder);
      holder.select();
      document.execCommand('copy');
      holder.remove();
    }
  };
  const render = () => {
    const query = search.value.trim().toLowerCase();
    const selectedFilter = filter.value;
    let shown = 0;
    list.replaceChildren();
    for (const profile of profiles) {
      const status = statusStore[profile.url] || 'pending';
      const haystack = [profile.name, profile.company, profile.section, profile.context, profile.url].join(' ').toLowerCase();
      const visible = (!query || haystack.includes(query)) && (selectedFilter === 'all' || selectedFilter === status);
      if (!visible) continue;
      shown += 1;
      const card = document.createElement('article');
      card.className = 'card';
      card.dataset.url = profile.url;
      const title = document.createElement('h2');
      title.textContent = profile.id + '. ' + profile.name + ' ';
      const statusBadge = document.createElement('span');
      statusBadge.className = 'status ' + status;
      statusBadge.textContent = status;
      title.appendChild(statusBadge);
      const meta = document.createElement('div');
      meta.className = 'meta';
      meta.textContent = [profile.company, profile.section].filter(Boolean).join(' · ');
      const context = document.createElement('div');
      context.className = 'context';
      context.textContent = profile.context;
      const note = document.createElement('textarea');
      note.setAttribute('aria-label', 'Connection note for ' + profile.name);
      note.value = profile.note;
      const actions = document.createElement('div');
      actions.className = 'actions';
      const openProfile = document.createElement('a');
      openProfile.className = 'button';
      openProfile.href = profile.url;
      openProfile.target = '_blank';
      openProfile.rel = 'noopener noreferrer';
      openProfile.textContent = 'Open profile';
      const copyNote = document.createElement('button');
      copyNote.type = 'button';
      copyNote.dataset.action = 'copy-note';
      copyNote.textContent = 'Copy note';
      const connectedButton = document.createElement('button');
      connectedButton.type = 'button';
      connectedButton.dataset.action = 'connected';
      connectedButton.textContent = 'Mark connected';
      const skippedButton = document.createElement('button');
      skippedButton.type = 'button';
      skippedButton.dataset.action = 'skipped';
      skippedButton.className = 'secondary';
      skippedButton.textContent = 'Skip';
      actions.append(openProfile, copyNote, connectedButton, skippedButton);
      card.append(title, meta, context, note, actions);
      list.appendChild(card);
    }
    const connected = profiles.filter(profile => statusStore[profile.url] === 'connected').length;
    const skipped = profiles.filter(profile => statusStore[profile.url] === 'skipped').length;
    summary.textContent = shown + ' shown · ' + profiles.length + ' total · ' + connected + ' connected · ' + skipped + ' skipped · ' + (profiles.length - connected - skipped) + ' pending';
  };
  list.addEventListener('click', event => {
    try {
      const button = event.target.closest('button[data-action]');
      if (!button) return;
      const card = button.closest('.card');
      const url = card.dataset.url;
      if (button.dataset.action === 'copy-note') {
        copyText(card.querySelector('textarea').value);
        return;
      }
      statusStore[url] = button.dataset.action;
      save();
      render();
    } catch (error) {
      alert(error.message);
    }
  });
  search.addEventListener('input', render);
  filter.addEventListener('change', render);
  document.getElementById('copyUrls').addEventListener('click', () => copyText(profiles.map(profile => profile.url).join('\\n')));
  document.getElementById('resetStatuses').addEventListener('click', () => {
    localStorage.removeItem(storageKey);
    for (const key of Object.keys(statusStore)) delete statusStore[key];
    render();
  });
  render();
} catch (error) {
  const errorPre = document.createElement('pre');
  errorPre.textContent = String(error.stack || error.message || error);
  document.body.prepend(errorPre);
}
</script>
</body>
</html>`;

try {
  const html = await readFile(sourcePath, 'utf8');
  const profiles = extractProfiles(html);
  const csvRows = [
    ['id', 'name', 'profileUrl', 'company', 'section', 'connectionNote', 'status', 'notes'],
    ...profiles.map(profile => [profile.id, profile.name, profile.url, profile.company, profile.section, profile.note, profile.status, profile.notes])
  ];
  await writeFile(csvPath, `${csvRows.map(row => row.map(csvCell).join(',')).join('\n')}\n`);
  await writeFile(queuePath, renderQueueHtml(profiles));
  console.log(`Source: ${basename(sourcePath)}`);
  console.log(`Profiles: ${profiles.length}`);
  console.log(`CSV: ${csvPath}`);
  console.log(`Queue: ${queuePath}`);
} catch (error) {
  console.error(error);
  process.exitCode = 1;
}
