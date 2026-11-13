import fs from 'fs';

const html = fs.readFileSync('Pega_Career_Intelligence_Hub.html', 'utf8');
const tableMatch = html.match(/<table class="tbl searchable" id="people-audit-table">[\s\S]*?<\/table>/);
if (!tableMatch) throw new Error('people audit table not found');

function decode(cell) {
  return cell.replace(/<br\s*\/?>/gi, '\n')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&nbsp;/g, ' ')
    .replace(/&rarr;/g, '->')
    .replace(/\s+\n/g, '\n')
    .replace(/\n\s+/g, '\n')
    .replace(/[ \t]+/g, ' ')
    .trim();
}
function normalizeCompany(first) {
  const originalAssociation = first?.match(/Original directory association:\s*([^·<]+)(?:·|$)/);
  let company = originalAssociation?.[1]?.trim();
  if (!company) {
    const lines = (first || '').split('\n').map(line => line.trim()).filter(Boolean);
    company = lines.slice(1).join(' / ') || 'Unknown';
  }
  if (/^\d+$/.test(company) && first?.includes('·')) company = first.split('·')[1]?.split('—')[0]?.trim() || company;
  return company.replace(/^[0-9]+\s*·\s*/, '').split('—')[0].trim();
}
const rows = [...tableMatch[0].matchAll(/<tr[^>]*>([\s\S]*?)<\/tr>/g)].map(match => {
  const cells = [...match[1].matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map(cell => decode(cell[1]));
  const [first, outcome, evidence, implication] = cells;
  const lines = (first || '').split('\n').map(line => line.trim()).filter(Boolean);
  return { person: lines[0] || '', company: normalizeCompany(first), outcome: outcome || '', evidence: evidence || '', implication: implication || '', text: `${first} ${outcome} ${evidence} ${implication}` };
});

const skillPatterns = {
  integration: /\b(kafka|rest|soap|api|connect|connector|integration|sftp|jms|amq|ldap|nginx|openshift|helm|cloud|deployment|pipeline|pdc|splunk|staging|database connector)\b/i,
  collections: /\b(collection|collections|recover|recovery|cash collection|ccms|csfs|financial services|payment investigations|smart investigate|global payment investigations)\b/i,
  decisioning: /\b(cdh|decisioning|nba|next best action|adaptive|strategy|marketing)\b/i,
  constellation: /\b(constellation|dx api|infinity 24|pega 25|ui gallery)\b/i,
  automation: /\b(automation|rpa|power platform|copilot|ai|genai|blueprint|workflow|process optimization)\b/i,
  seniorityHigh: /\b(lead|architect|lsa|principal|vp|director|head|manager|agm|dgm|chapter|executive director|avp)\b/i,
  nearPeer: /\b(developer|software engineer|senior software engineer|engineer ii|analyst|consultant)\b/i,
  taRecruiting: /\b(talent acquisition|recruit|ta partner|recruiter|hrbp|human resources)\b/i,
  staleFormer: /\b(former|ended|left|ex-|farewell|last working|stale|old|historical|previously|prior)\b/i,
  geographyRisk: /\b(utrecht|tampa|us|united states|canada|uk|overseas|not india|location not established|city.*unverified|exact city)\b/i,
  levelRisk: /\b(8\+ years|10\+ years|13\+ years|5\+ years|lsa preference|above level|not your level|leadership|executive)\b/i,
};

const byCompany = new Map();
for (const row of rows) {
  const flags = Object.fromEntries(Object.entries(skillPatterns).map(([key, regex]) => [key, regex.test(row.text)]));
  row.flags = flags;
  if (!byCompany.has(row.company)) byCompany.set(row.company, []);
  byCompany.get(row.company).push(row);
}

function countFlag(items, flag) { return items.filter(item => item.flags[flag]).length; }
function examples(items, predicate, n=3) { return items.filter(predicate).slice(0,n).map(item => `${item.person}: ${item.evidence.slice(0,160)}`); }

const companies = [...byCompany.entries()].map(([company, items]) => ({
  company,
  total: items.length,
  integration: countFlag(items, 'integration'),
  collections: countFlag(items, 'collections'),
  decisioning: countFlag(items, 'decisioning'),
  constellation: countFlag(items, 'constellation'),
  automation: countFlag(items, 'automation'),
  nearPeer: countFlag(items, 'nearPeer'),
  seniorityHigh: countFlag(items, 'seniorityHigh'),
  taRecruiting: countFlag(items, 'taRecruiting'),
  staleFormer: countFlag(items, 'staleFormer'),
  geographyRisk: countFlag(items, 'geographyRisk'),
  levelRisk: countFlag(items, 'levelRisk'),
  score: 0,
  examples: {}
}));
for (const c of companies) {
  c.score = c.integration * 3 + c.collections * 3 + c.nearPeer * 2 + c.constellation * 2 + c.automation - c.seniorityHigh - c.geographyRisk * 2 - c.staleFormer;
  const items = byCompany.get(c.company);
  c.examples.integration = examples(items, item => item.flags.integration);
  c.examples.collections = examples(items, item => item.flags.collections);
  c.examples.nearPeer = examples(items, item => item.flags.nearPeer && !item.flags.seniorityHigh);
}
const ranked = companies.filter(c => c.total >= 1).sort((a,b)=>b.score-a.score || b.integration-a.integration || a.company.localeCompare(b.company));
const hidden = {
  bestResumeFitNotJustLogo: ranked.slice(0, 20),
  integrationCollectionsOverlap: ranked.filter(c => c.integration && c.collections).slice(0, 20),
  nearPeerRoutes: ranked.filter(c => c.nearPeer >= 2 && c.seniorityHigh <= c.nearPeer).slice(0, 20),
  highLogoLowUsability: companies.filter(c => c.total >= 2 && (c.geographyRisk + c.staleFormer + c.levelRisk) >= 2).sort((a,b)=>(b.geographyRisk+b.staleFormer+b.levelRisk)-(a.geographyRisk+a.staleFormer+a.levelRisk)).slice(0, 20),
  constellationSignals: ranked.filter(c => c.constellation > 0).slice(0, 20),
  recruiterHeavyNotEngineer: companies.filter(c => c.taRecruiting >= 2 && c.integration === 0 && c.collections === 0).sort((a,b)=>b.taRecruiting-a.taRecruiting).slice(0, 20)
};
fs.writeFileSync('hidden_profile_insights.json', JSON.stringify({ generatedAt: new Date().toISOString(), totals: { rows: rows.length, companies: companies.length }, hidden }, null, 2));
console.log('Rows', rows.length, 'companies', companies.length);
for (const [name, list] of Object.entries(hidden)) {
  console.log('\n## '+name);
  for (const c of list.slice(0, 10)) console.log(`${c.company} score=${c.score} total=${c.total} int=${c.integration} coll=${c.collections} near=${c.nearPeer} high=${c.seniorityHigh} stale=${c.staleFormer} geo=${c.geographyRisk}`);
}
