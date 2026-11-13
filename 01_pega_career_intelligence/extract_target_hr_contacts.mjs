import fs from 'fs';

const files = [
  'New UPDATED 2026 Company Wise 3,000+ HR contact-1_extracted.txt',
  'New UPDATED 2026 Company Wise 3,000+ HR contact-2_extracted.txt'
];
const targets = [
  'Siemens','American Express','Sun Life','Cisco','JPMorgan','JP Morgan','JPMorgan Chase','Barclays','Tata Motors','Tata Technologies','Mastercard','Visa','Fiserv','FIS','Vodafone Idea','Reliance Jio'
];
const positiveRole = /\b(TA|Talent|Recruit|Recruiter|Recruitment|HR|Human Resources|People|RPO)\b/i;
const negativeRole = /\b(Design Engineer|Application Engineer|Project Manger|Project Manager|Regional Quality|Relationship|Local Specialist|Sales Manager|Finance Crime|Data Engineering Architect|City Operation|Operation Head|Mining Leader|Co Head Rate|Technical Lead|Manager project|BMS Services|Business Administration)\b/i;

function parseLine(line, sourceFile) {
  const emailMatch = line.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
  if (!emailMatch) return null;
  const email = emailMatch[0].replace(/[.,;:]+$/, '').toLowerCase();
  const before = line.slice(0, emailMatch.index).replace(/^\s*\d+\s*/, '').trim();
  const after = line.slice(emailMatch.index + emailMatch[0].length).trim();
  const target = targets.find(company => line.toLowerCase().includes(company.toLowerCase()));
  if (!target) return null;
  let company = target;
  if (/JP Morgan|JPMorgan/i.test(company)) company = 'JPMorgan Chase';
  const roleCompany = after.replace(/\s+/g, ' ').trim();
  const usable = positiveRole.test(line) && !negativeRole.test(line);
  const quality = usable ? 'possible-ta-hr' : positiveRole.test(line) ? 'mixed-role-check' : 'likely-not-ta';
  return { company, name: before || 'Name not parsed', email, roleCompany, sourceFile, sourceLine: line.trim(), quality };
}

const contacts = [];
for (const file of files) {
  const text = fs.readFileSync(file, 'utf8');
  for (const line of text.split(/\r?\n/)) {
    const row = parseLine(line, file);
    if (row) contacts.push(row);
  }
}
const deduped = [...new Map(contacts.map(row => [`${row.email}|${row.company}`, row])).values()];
const byCompany = deduped.reduce((acc, row) => {
  acc[row.company] ??= [];
  acc[row.company].push(row);
  return acc;
}, {});
for (const rows of Object.values(byCompany)) rows.sort((a,b) => a.quality.localeCompare(b.quality) || a.name.localeCompare(b.name));
const prioritized = Object.fromEntries(Object.entries(byCompany).sort(([a],[b]) => a.localeCompare(b)).map(([company, rows]) => [company, rows.slice(0, 12)]));
fs.writeFileSync('target_hr_contacts.json', JSON.stringify({ generatedAt: new Date().toISOString(), totalExtracted: contacts.length, totalDeduped: deduped.length, prioritized }, null, 2));
console.log(JSON.stringify(Object.fromEntries(Object.entries(prioritized).map(([company, rows]) => [company, { total: byCompany[company].length, selected: rows.length, possibleTA: rows.filter(r => r.quality === 'possible-ta-hr').length }])) , null, 2));
