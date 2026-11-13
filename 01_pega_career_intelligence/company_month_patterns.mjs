import fs from 'fs';

const html = fs.readFileSync('Pega_Career_Intelligence_Hub.html', 'utf8');
const tableMatch = html.match(/<table class="tbl searchable" id="people-audit-table">[\s\S]*?<\/table>/);
if (!tableMatch) throw new Error('people audit table not found');

const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const monthPattern = 'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|June|July|August|September|October|November|December';
const fullToShort = { January:'Jan', February:'Feb', March:'Mar', April:'Apr', June:'Jun', July:'Jul', August:'Aug', September:'Sep', October:'Oct', November:'Nov', December:'Dec' };
const fromSinceRegex = new RegExp(`\\b(?:from|since|joined|joins|joining|entry starts|starts|start(?:ed)?|moved to|announces|announced)\\s+(?:in\\s+|the\\s+)?(${monthPattern})\\.?\\s+(\\d{4})`, 'ig');
const rangeRegex = new RegExp(`\\b(${monthPattern})\\.?\\s+(\\d{4})(?:\\s*[–-]\\s*(?:present|current|now|\\w+\\s+\\d{4}))`, 'ig');

function decode(text) {
  return text.replace(/<br\s*\/?>/gi, '\n')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&nbsp;/g, ' ')
    .replace(/&rarr;/g, '->')
    .replace(/\s+\n/g, '\n')
    .replace(/\n\s+/g, '\n')
    .replace(/[ \t]+/g, ' ')
    .trim();
}
function short(month) { return fullToShort[month] || month.slice(0, 3); }
function bucket(company, month, year, row, kind) {
  const key = `${company}||${month}||${year}||${row.person}`;
  return { key, company, month, year, person: row.person, evidence: row.evidence, kind, outcome: row.outcome };
}

const rows = [...tableMatch[0].matchAll(/<tr[^>]*>([\s\S]*?)<\/tr>/g)].map(match => {
  const rawCells = [...match[1].matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map(cell => cell[1]);
  const cells = rawCells.map(cell => decode(cell));
  const [first, outcome, evidence, implication] = cells;
  const lines = (first || '').split('\n').map(line => line.trim()).filter(Boolean);
  const originalAssociation = first?.match(/Original directory association:\s*([^·<]+)(?:·|$)/);
  let company = originalAssociation?.[1]?.trim() || lines.slice(1).join(' / ') || 'Unknown';
  if (/^\d+$/.test(company) && first?.includes('·')) company = first.split('·')[1]?.split('—')[0]?.trim() || company;
  company = company.replace(/^[0-9]+\s*·\s*/, '').split('—')[0].trim();
  return { person: lines[0] || '', company, outcome: outcome || '', evidence: evidence || '', implication: implication || '' };
});

const observations = [];
for (const row of rows) {
  let match;
  const text = row.evidence;
  fromSinceRegex.lastIndex = 0;
  while ((match = fromSinceRegex.exec(text))) {
    observations.push(bucket(row.company, short(match[1]), Number(match[2]), row, /promotion|internal|follows/i.test(text + ' ' + row.outcome) ? 'promotion-or-internal' : 'join-or-current-start'));
  }
  rangeRegex.lastIndex = 0;
  while ((match = rangeRegex.exec(text))) {
    observations.push(bucket(row.company, short(match[1]), Number(match[2]), row, /promotion|internal|follows/i.test(text + ' ' + row.outcome) ? 'promotion-or-internal' : 'range-start'));
  }
}

const deduped = [...new Map(observations.map(obs => [obs.key, obs])).values()];
const recent = deduped.filter(obs => obs.year >= 2024 && obs.year <= 2026);
const byCompany = new Map();
for (const obs of recent) {
  const company = obs.company.split(' / ')[0].trim();
  if (!byCompany.has(company)) byCompany.set(company, []);
  byCompany.get(company).push({ ...obs, company });
}

const summary = [...byCompany.entries()].map(([company, items]) => {
  const counts = Object.fromEntries(monthNames.map(month => [month, 0]));
  for (const item of items) counts[item.month]++;
  const sorted = Object.entries(counts).filter(([, count]) => count > 0).sort((a, b) => b[1] - a[1] || monthNames.indexOf(a[0]) - monthNames.indexOf(b[0]));
  return { company, total: items.length, top: sorted.slice(0, 3), counts, items };
}).filter(row => row.total >= 2).sort((a, b) => b.total - a.total || a.company.localeCompare(b.company));

const reliable = summary.filter(row => row.total >= 3);
fs.writeFileSync('company_month_patterns.json', JSON.stringify({ generatedAt: new Date().toISOString(), totalRows: rows.length, datedObservations: deduped.length, recentObservations: recent.length, reliable, allCompaniesWithTwoPlus: summary }, null, 2));

console.log(`Audit rows: ${rows.length}`);
console.log(`Dated observations: ${deduped.length}; recent 2024-2026: ${recent.length}`);
console.log('\nCompanies with 3+ recent dated observations:');
for (const row of reliable) {
  console.log(`${row.company.padEnd(28)} n=${String(row.total).padStart(2)} peak=${row.top.map(([month, count]) => `${month}:${count}`).join(', ')}`);
}
