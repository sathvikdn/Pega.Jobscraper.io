// Audit helper: explain exactly WHY a company got the Pillar-1 score it did, naming
// every person counted and the literal token that matched. Usage:
//   node gcc_explain_company.mjs "Mercedes-Benz R&D India (MBRDI)"
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const directory = dirname(fileURLToPath(import.meta.url));
// Keep paths script-relative so the handoff export remains portable.
const DIR = directory + "/";
const target = process.argv[2] || "Mercedes-Benz R&D India (MBRDI)";
const base = JSON.parse(readFileSync(DIR + "gcc_evidence_base.json", "utf8"));
const c = base.companies.find((x) => x.company === target);
if (!c) { console.error("Not found: " + target); process.exit(1); }

// Regexes copied verbatim from gcc_score_rubric.mjs
const T_TOP = /global head|head of pega|head pega|pega coe lead|coe lead|chief architect|principal architect|principal solution architect|executive director|engineering director|managing director|distinguished|director[^.]{0,40}(?:pega|architect|engineering|application)|(?:pega|architecture)[^.]{0,20}director|head[^.]{0,25}(?:pega|workflow|automation|coe)/i;
const T_ARCH = /\b(?:lsa|clsa|pclsa|cssa|cpdc|lsa-1|lsa-2)\b|lead system architect|senior system architect|system architect|solution architect|technical architect|lead architect|pega architect|staff engineer|senior staff|lead engineer|lead software engineer|lead pega|pega lead|tech(?:nical)? lead|development lead|team lead|delivery architect|principal engineer|principal consultant|senior manager|lead decisioning|decisioning architect/i;
const T_DELIVERY = /delivery manager|delivery lead|operations lead|ops lead|support manager|support lead|service delivery|production support|bau lead|incident manager|project manager|program manager|scrum master|technical recruiter|talent acquisition|recruiter/i;
const INDIA = /bengaluru|bangalore|hyderabad|chennai|pune|mumbai|gurugram|gurgaon|noida|new delhi|delhi|kolkata|trivandrum|thiruvananthapuram|coimbatore|ahmedabad|\bindia\b/i;
const NON_INDIA = /richardson|texas|atlanta|pittsburgh|charlotte|melbourne|sydney|\blondon\b|amsterdam|utrecht|singapore|\bus\)|\busa\b|united states|australia|netherlands|\buk\)|not india/i;

console.log(`=== ${c.company} ===`);
console.log(`members=${c.members.length}  auditRows=${c.auditRows}  tenureN=${c.tenureN}  avgTenure=${c.tenureAvgYears}y`);
console.log("");

let archN = 0;
const archList = [], topList = [], otherList = [], deptList = [];

for (const m of c.members) {
  const title = m.title || "";
  const certs = m.certs || "";
  const loc = m.location || "";
  const titleAndCerts = `${title} ${certs}`;
  const departed = /departed|has left|serving notice|resigned/i.test(title);
  const abroad = NON_INDIA.test(`${loc} ${title}`) && !INDIA.test(loc);

  let tier, matchedOn = "";
  if (departed) { tier = "EXCLUDED (departed)"; deptList.push(m.name); }
  else if (T_TOP.test(title)) {
    tier = INDIA.test(loc) ? "TOP +30" : "TOP (location unverified)";
    matchedOn = title.match(T_TOP)[0];
    topList.push(m.name);
  } else if (T_ARCH.test(titleAndCerts) && !abroad) {
    archN++;
    tier = `ARCH #${archN}`;
    matchedOn = titleAndCerts.match(T_ARCH)[0];
    archList.push({ n: archN, name: m.name, title, certs, matchedOn, loc });
  } else {
    tier = T_DELIVERY.test(title) ? "delivery/ops only" : "no tier";
    otherList.push(m.name);
  }

  console.log(`${tier.padEnd(26)} | ${m.name.padEnd(24)} | ${title}`);
  if (certs) console.log(`${"".padEnd(26)} |   certs: ${certs}`);
  if (loc) console.log(`${"".padEnd(26)} |   location: ${loc}`);
  if (matchedOn) console.log(`${"".padEnd(26)} |   >> matched token: "${matchedOn}"`);
}

console.log("");
console.log(`Counted as architect ladder: ${archN}`);
console.log("");
console.log("--- the architect-ladder list as the scorer sees it ---");
for (const a of archList) {
  console.log(`${String(a.n).padStart(2)}. ${a.name} — ${a.title}  [matched: "${a.matchedOn}"]`);
}

// How many qualified on a REAL architect title vs only on a certification string?
const TITLE_ONLY = /lead system architect|senior system architect|system architect|solution architect|technical architect|lead architect|pega architect|staff engineer|senior staff|lead engineer|lead software engineer|lead pega|pega lead|tech(?:nical)? lead|development lead|team lead|delivery architect|principal engineer|principal consultant|senior manager|lead decisioning|decisioning architect/i;
const byTitle = archList.filter((a) => TITLE_ONLY.test(a.title));
const byCertOnly = archList.filter((a) => !TITLE_ONLY.test(a.title));
console.log("");
console.log(`qualified via an architect/lead TITLE : ${byTitle.length}`);
byTitle.forEach((a) => console.log(`   - ${a.name} — ${a.title}`));
console.log(`qualified ONLY via a certification   : ${byCertOnly.length}`);
byCertOnly.forEach((a) => console.log(`   - ${a.name} — ${a.title} (certs: ${a.certs})`));
