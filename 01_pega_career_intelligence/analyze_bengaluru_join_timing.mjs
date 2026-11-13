import { readFile, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

// Counts dated profile starts, not verified external hires. Exclude promotions, alumni and
// out-of-city/vendor contacts before treating a start as Bengaluru hiring evidence.
const directory = dirname(fileURLToPath(import.meta.url));
const inputPath = join(directory, 'bengaluru_top50_2026-11.json');
const outputPath = join(directory, 'reports', 'bengaluru_join_timing_2026-11.json');
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const windowStart = 2025 * 12 + 10;

function dateAfterSince(tenure) {
  const match = String(tenure ?? '').match(/\bsince\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(20\d\d)\b/i);
  if (!match) return null;
  return { year: Number(match[2]), month: MONTHS.findIndex(month => month.toLowerCase() === match[1].slice(0, 3).toLowerCase()) };
}

function classify(person) {
  const name = String(person.name ?? '');
  const title = String(person.title ?? '');
  const tenure = String(person.tenure ?? '');
  const date = dateAfterSince(tenure);
  if (/\bpromoted\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/i.test(tenure) && !date)
    return { category: 'internal-move', reason: 'Promotion, not a company start' };
  if (!date) return { category: 'undated', reason: 'No explicit "since Mon YYYY" company start' };
  if (/\b(left|alumnus|alumna)\b/i.test(name) || /^ex-/i.test(title) || /\bmay have left\b/i.test(tenure))
    return { category: 'excluded', reason: 'Former or potentially departed' };
  if (/\bvia\s+(HCLTech|Capgemini|Quess)\b/i.test(`${title} ${tenure}`) || /\bvendor\b/i.test(name))
    return { category: 'excluded', reason: 'Vendor rather than direct employer' };
  if (/\b(Gurugram|Gurgaon|Hyderabad|Chennai|Pune|Kolkata|Melbourne)\b|\(US\)/i.test(title))
    return { category: 'excluded', reason: 'Outside Bengaluru' };
  if (/\b(recruit|talent acquisition|country head|business analyst|lead analyst)\b/i.test(title))
    return { category: 'adjacent', reason: 'Not a Bengaluru Pega engineering role' };
  if (/\bPega\b|\bDecisioning Architect\b/i.test(title))
    return { category: 'pega-role', reason: 'Role explicitly names Pega or decisioning' };
  return { category: 'team-associated', reason: 'Pega assignment or exact office not independently established' };
}

try {
  const ledger = JSON.parse(await readFile(inputPath, 'utf8'));
  const companies = [];
  for (const company of ledger.companies) {
    const records = (company.people ?? []).map(person => {
      const date = dateAfterSince(person.tenure);
      const { category, reason } = classify(person);
      return {
        name: person.name, title: person.title, tenure: person.tenure, category, reason,
        year: date?.year ?? null, month: date ? MONTHS[date.month] : null
      };
    });
    const recent = records.filter(record =>
      ['pega-role', 'team-associated'].includes(record.category) &&
      record.year * 12 + MONTHS.indexOf(record.month) >= windowStart
    ).sort((left, right) =>
      (right.year * 12 + MONTHS.indexOf(right.month)) - (left.year * 12 + MONTHS.indexOf(left.month)));
    companies.push({
      rank: company.rank, company: company.company, people: records.length,
      recentDatedPegaRoles: recent.filter(record => record.category === 'pega-role').length,
      recentTeamAssociated: recent.filter(record => record.category === 'team-associated').length,
      recentStarts: recent,
      excludedOrAdjacent: records.filter(record => ['excluded', 'adjacent', 'internal-move'].includes(record.category)),
      undated: records.filter(record => record.category === 'undated').length
    });
  }
  const result = {
    generatedAt: new Date().toISOString(), source: 'bengaluru_top50_2026-11.json',
    windowStart: 'Nov 2025',
    caveat: 'Public search-index tenure snippets, not verified employee histories. "Since" can be a role start, not an external hire. Team-associated entries do not prove Pega work; absent dates do not prove no hiring. No hiring-calendar inference is justified.',
    companies
  };
  await writeFile(outputPath, JSON.stringify(result, null, 2), 'utf8');
  for (const company of companies.filter(row => row.recentStarts.length)) {
    console.log(`${company.company}: explicit Pega ${company.recentDatedPegaRoles}, team-associated ${company.recentTeamAssociated}; ` +
      company.recentStarts.map(record => `${record.name} (${record.month} ${record.year}, ${record.category})`).join(', '));
  }
  console.log(`\nSaved ${outputPath}`);
} catch (error) {
  console.error(error);
  process.exitCode = 1;
}
