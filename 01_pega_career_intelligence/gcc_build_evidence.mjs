// T3 of the GCC ranking build: merge every evidence source into ONE per-company record.
//
// Why this step exists: the evidence is split across three files and they do not agree on
// company names. team_intelligence_enriched.json is rich on team rosters but thin on
// conference/innovation evidence; the HTML hub is the opposite. Scoring off either alone
// systematically penalises whichever companies happen to be documented in the other file.
//
// Output: gcc_evidence_base.json  (input to the scorer; no scoring happens here)
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const directory = dirname(fileURLToPath(import.meta.url));
// Keep paths script-relative so the handoff export remains portable.
const DIR = directory + "/";
const EMDASH = "\u2014";

// ---------------------------------------------------------------------------
// Canonical company names + aliases.
// Hand-curated: automatic fuzzy matching merged entities that must stay separate
// (MUFG vs MUFG Pension & Market Services; Elevance vs its Carelon GCC), so the
// mapping is explicit and auditable instead of inferred.
// ---------------------------------------------------------------------------
const ALIASES = {
  "JPMorgan Chase": ["JPMorganChase", "JPMC", "JPMorgan"],
  "Wells Fargo": ["Wells Fargo Bank", "WF"],
  HSBC: [],
  Citibank: ["Citi", "Citi India"],
  "Bank of America": ["BoA", "BofA"],
  "Goldman Sachs": ["Marcus by Goldman Sachs"],
  Barclays: [],
  "Deutsche Bank": [],
  "Standard Chartered": ["SCB", "Standard Chartered Bank"],
  "American Express": ["Amex"],
  "Morgan Stanley": [],
  "NatWest Group": ["NatWest"],
  "Lloyds Banking Group": ["Lloyds Technology Centre India", "Lloyds Technology Centre", "Lloyds TC", "Lloyds"],
  "BNP Paribas": [],
  "Societe Generale": ["Société Générale", "SocGen", "Societe Generale GSC"],
  "ANZ Bank": ["ANZ"],
  MUFG: [],
  "MUFG Pension & Market Services (Link Group)": ["MUFG Pension & Market Services", "MUFG Pension", "Link Group"],
  "BNY Mellon": ["BNY"],
  "Allianz Technology": ["Allianz"],
  Aflac: [],
  "Sun Life": ["Sun Life / SLGS", "Sun Life (additional)", "SLGS"],
  "Ameriprise Financial": ["Ameriprise"],
  Empower: ["Empower Retirement"],
  "Charles Schwab": ["Schwab"],
  Mastercard: [],
  Visa: [],
  PayPal: [],
  "FIS (TSYS/Global Payments)": ["FIS (TSYS)", "FIS", "TSYS"],
  Broadridge: ["Broadridge India"],
  "Optum / UnitedHealth Group": ["Optum / UHG", "Optum", "UHG", "UnitedHealth Group"],
  "Elevance Health (Anthem)": ["Elevance Health", "Elevance", "Anthem"],
  "Carelon Global Solutions India": ["Carelon", "Carelon / Elevance"],
  "Evernorth / Cigna": ["Evernorth", "Cigna", "Evernorth Health Services"],
  Verizon: [],
  "Vodafone / VOIS": ["VOIS", "Vodafone", "Vodafone VOIS", "_VOIS"],
  "BT Group": ["BT"],
  Telstra: [],
  Amdocs: [],
  "Ford Motor Company": ["Ford", "Ford Credit"],
  Stellantis: [],
  Siemens: ["Siemens Technology India", "Siemens GBS"],
  "S&P Global": ["S&P Global Ratings"],
  Conduent: [],
  DHL: ["DHL IT Services", "DHL Group"],
  "Dell Technologies": ["Dell"],
  "Kotak Mahindra Bank": ["Kotak"],
  "ICICI Bank": ["ICICI"],
  "Synchrony Financial": ["Synchrony"],
  Bosch: ["Bosch / BGSW", "BGSW", "Bosch Global Software"],
  "The Hartford India": ["Hartford India", "The Hartford", "Hartford"],
  Rabobank: [],
  "Commonwealth Bank": ["Commonwealth Bank of Australia", "CBA", "CBA (Commonwealth Bank)"],
  "NAB (National Australia Bank)": ["NAB India", "NAB", "National Australia Bank"],
  "UBS India": ["UBS"],
  "MetLife India GCC": ["MetLife MGCC", "MetLife"],
  "AXA India": ["AXA"],
  "Roche India": ["Roche"],
  "GE HealthCare India": ["GE HealthCare", "GE Healthcare"],
  "Pfizer India": ["Pfizer"],
  "Novartis India": ["Novartis"],
  "John Deere India (JDTCI)": ["John Deere", "John Deere Financial", "Deere", "JDTCI"],
  "First Citizens India": ["First Citizens", "First Citizens Bank"],
  "Booking Holdings India": ["Booking Holdings", "Booking", "Booking.com"],
  "Cisco India": ["Cisco"],
  "Nokia India": ["Nokia"],
  "Orange Business India": ["Orange Business", "Orange"],
  "Maersk GSC India": ["Maersk"],
  "Shell India": ["Shell"],
  "Nike India": ["Nike", "Nike India (ITC)"],
  "Unilever India (Digital Hub)": ["Unilever", "UniOps"],
  "Mercedes-Benz R&D India (MBRDI)": ["Mercedes-Benz R&D India", "MBRDI", "Mercedes-Benz"],
  "Daimler Truck India": ["Daimler Truck", "DTICI"],
  "Renault-Nissan Tech India": ["Renault-Nissan", "Renault-Nissan Technology"],
  "Cummins India": ["Cummins"],
  "IFFCO Tokio General Insurance": ["IFFCO Tokio"],
  "Global Payments India": ["Global Payments"],
  "Pegasystems India": ["Pegasystems", "Pega"],
  "Fidelity National Financial India": ["FNF India", "Fidelity National Financial"],
  "Proximus India": ["Proximus"],
  "Mondelez India": ["Mondelez"],
  "enGen / Highmark India": ["enGen", "enGen Global", "Highmark"],
  "Marsh McLennan India (MMGS)": ["Marsh McLennan", "MMGS"],
  "PepsiCo India": ["PepsiCo"],
  "Capital One India": ["Capital One"],
  "Mizuho Global Services India (MGS)": ["Mizuho", "Mizuho Global Services"],
  "Intel India": ["Intel"],
  "Levi Strauss & Co. India": ["Levi Strauss", "Levi"],
  "ITC Limited": ["ITC"],
  Fiserv: [],
};

const norm = (s) =>
  (s || "").replace(/&amp;/g, "&").toLowerCase().replace(/&/g, "and").replace(/[^a-z0-9]/g, "");

// alias lookup: normalised string -> canonical name
const LOOKUP = new Map();
for (const [canon, aliases] of Object.entries(ALIASES)) {
  LOOKUP.set(norm(canon), canon);
  for (const a of aliases) LOOKUP.set(norm(a), canon);
}

function canonicalise(raw) {
  if (!raw) return null;
  let s = raw.replace(/&amp;/g, "&").trim();
  s = s.replace(/^\d+\s*[·.]\s*/, "");              // strip "9 · " dossier index
  s = s.split(new RegExp(`\\s*${EMDASH}\\s*`))[0];  // drop " — Programme" suffix
  s = s.split("·")[0].trim();                        // drop " · City"
  s = s.replace(/\s*\(additional\)\s*$/i, "").trim();
  // Correction phrasing from the hub ("NAB (not NatWest)", "Visa (US)") must resolve to
  // the asserted employer, not become a phantom company of its own.
  s = s.replace(/\s*\((?:not|was|ex|formerly|previously)\b[^)]*\)/i, "").trim();
  const n = norm(s);
  if (LOOKUP.has(n)) return LOOKUP.get(n);
  // Longest-alias prefix/containment fallback, longest first so "Sun Life" does not
  // win over a more specific "MUFG Pension & Market Services".
  const cands = [...LOOKUP.keys()].filter((k) => k.length >= 4 && (n === k || n.startsWith(k) || k.startsWith(n)));
  if (cands.length) {
    cands.sort((a, b) => b.length - a.length);
    return LOOKUP.get(cands[0]);
  }
  return s || null;
}

const stripTags = (html) =>
  html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&nbsp;/g, " ")
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/\s+/g, " ")
    .trim();

// ---------------------------------------------------------------------------
// Tenure parsing (shared contract with the feasibility script)
// ---------------------------------------------------------------------------
const AS_OF = { y: 2026, m: 10 };
const MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];

function parseMonthYear(text) {
  if (!text) return null;
  const m = /([a-z]{3})[a-z]*\s+(\d{4})/i.exec(text);
  if (m) {
    const idx = MONTHS.indexOf(m[1].toLowerCase());
    if (idx >= 0) return { y: Number(m[2]), m: idx + 1 };
  }
  const y = /\b(?:19|20)\d{2}\b/.exec(text);
  return y ? { y: Number(y[0]), m: 7 } : null;
}
const monthsBetween = (a, b) => (b.y - a.y) * 12 + (b.m - a.m);

// Tenure at one company across consecutive roles (promotions must not count as
// separate short stints, which would fake high attrition).
function tenureFromCareer(career, canon) {
  const owned = career.filter((s, i) => (s.company ? canonicalise(s.company) === canon : i === 0));
  if (!owned.length) return null;
  let earliest = null, stillThere = false, latestEnd = null;
  for (const stop of owned) {
    const dates = stop.dates || "";
    const [a, b] = dates.split(/\s*[-\u2013]\s*/, 2);
    const st = parseMonthYear(a);
    if (st && (!earliest || st.y * 12 + st.m < earliest.y * 12 + earliest.m)) earliest = st;
    if (/present|current/i.test(dates)) stillThere = true;
    else {
      const en = parseMonthYear(b);
      if (en && (!latestEnd || en.y * 12 + en.m > latestEnd.y * 12 + latestEnd.m)) latestEnd = en;
    }
  }
  if (!earliest) return null;
  const end = stillThere ? AS_OF : latestEnd;
  if (!end) return null;
  const mo = monthsBetween(earliest, end);
  return mo > 0 && mo < 600 ? mo : null;
}

// "from April 2024" / "since Mar 2023" inside free-text findings -> tenure to AS_OF.
// Only used when the text also ties the person to the company, and only as a
// lower-confidence supplement to roster career data.
function tenureFromText(text) {
  const m = /\b(?:from|since)\s+([a-z]{3,9}\s+\d{4})/i.exec(text || "");
  if (!m) return null;
  const st = parseMonthYear(m[1]);
  if (!st) return null;
  const mo = monthsBetween(st, AS_OF);
  return mo > 0 && mo < 600 ? mo : null;
}

// ---------------------------------------------------------------------------
// Build the merged base
// ---------------------------------------------------------------------------
const ti = JSON.parse(readFileSync(DIR + "team_intelligence_enriched.json", "utf8"));
const audit = JSON.parse(readFileSync(DIR + "pega_full_audit.json", "utf8"));
const html = readFileSync(DIR + "Pega_Career_Intelligence_Hub.html", "utf8");

const base = new Map();
function rec(canon) {
  if (!base.has(canon)) {
    base.set(canon, {
      company: canon,
      sectors: new Set(),
      locations: new Set(),
      team_size: null,
      hiring_status: null,
      maturity: null,
      tech_stack: new Set(),
      domains: new Set(),
      titles: [],
      members: [],
      tenureSamples: [],   // {name, months, source}
      textChunks: [],      // all free text for keyword probes
      auditRows: 0,
      sources: new Set(),
    });
  }
  return base.get(canon);
}

// --- Source A: team_intelligence_enriched.json (rosters, tech stack, projects) ---
for (const c of ti.companies) {
  const canon = canonicalise(c.name);
  const r = rec(canon);
  r.sources.add("team_intelligence");
  if (c.sector) r.sectors.add(c.sector);
  (c.locations || []).forEach((l) => r.locations.add(l));
  r.team_size = r.team_size ?? c.team_size ?? null;
  r.hiring_status = r.hiring_status ?? c.hiring_status ?? null;
  r.maturity = r.maturity ?? c.maturity ?? null;
  (c.tech_stack || []).forEach((t) => r.tech_stack.add(t));
  (c.domains || []).forEach((d) => r.domains.add(d));
  if (c.projects) r.textChunks.push(c.projects);
  (c.highlights || []).forEach((h) => r.textChunks.push(h));

  for (const m of c.team_members || []) {
    const title = m.title || "";
    r.titles.push(title);
    const months = tenureFromCareer(m.career || [], canon);
    if (months !== null) r.tenureSamples.push({ name: m.name, months, source: "roster_career" });
    r.members.push({ name: m.name, title, certs: m.certs || m.certifications || "", location: m.location || "" });
    r.textChunks.push([title, m.certs || "", (m.career || []).map((s) => `${s.role || ""} ${s.detail || ""}`).join(" ")].join(" "));
  }
}

// --- Source B: hub audit rows (company association + research finding text) ---
// Each row carries data-audit-key, letting us join to pega_full_audit.json findings.
const rowRe = /<tr\s+id="full-audit-\d+"[\s\S]*?<\/tr>/g;
for (const row of html.match(rowRe) || []) {
  const assoc = /Original directory association:\s*([^<]+)</.exec(row);
  if (!assoc) continue;
  const canon = canonicalise(assoc[1]);
  if (!canon) continue;
  const r = rec(canon);
  r.sources.add("hub_audit");
  r.auditRows++;
  const keyM = /data-audit-key="([^"]+)"/.exec(row);
  const nameM = /rel="noopener noreferrer">([^<]+)<\/a>/.exec(row);
  const text = stripTags(row);
  r.textChunks.push(text);
  const key = keyM ? keyM[1] : null;
  const finding = key && audit.records[key] ? audit.records[key].finding : "";
  if (finding) r.textChunks.push(finding);
  const months = tenureFromText(finding) ?? tenureFromText(text);
  if (months !== null) {
    r.tenureSamples.push({ name: nameM ? nameM[1].trim() : key || "unknown", months, source: "audit_text" });
  }
}

// --- Source C: hub fresh-person-evidence company sections (Oct 2026 scrape) ---
// These h3-headed tables hold the PegaWorld/PegaInnovate/hackathon/hiring evidence
// that Pillar 3 depends on and that source A almost entirely lacks.
const secRe = /<h3 style="color:#166534">([^<]+)<\/h3>([\s\S]*?)(?=<h3 |<\/section>)/g;
let s;
while ((s = secRe.exec(html))) {
  const heading = s[1].replace(/&amp;/g, "&");
  const headCo = heading.split("·")[0].trim();
  const body = s[2];
  // Generic buckets ("Other key companies…") hold many companies in one table, so
  // attribute those row-by-row using the row's own company cell instead of the heading.
  const generic = /^other|^additional/i.test(headCo);
  for (const tr of body.match(/<tr>[\s\S]*?<\/tr>/g) || []) {
    const cells = [...tr.matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map((m) => stripTags(m[1]));
    if (!cells.length) continue;
    const canon = canonicalise(generic ? cells[1] || cells[0] : headCo);
    if (!canon) continue;
    const r = rec(canon);
    r.sources.add("hub_fresh_evidence");
    const text = cells.join(" | ");
    r.textChunks.push(text);
    const months = tenureFromText(text);
    if (months !== null) r.tenureSamples.push({ name: cells[0], months, source: "fresh_evidence_text" });
  }
}

// --- Source D: hand-verified supplement -------------------------------------------
// Findings read directly from individual profiles/posts during the Oct 2026 pass that
// the three bulk sources do not carry. Kept in a separate file so the scorer is never
// hand-patched and every added fact stays attributable.
let supplement = { companies: {} };
try {
  supplement = JSON.parse(readFileSync(DIR + "gcc_evidence_supplement.json", "utf8"));
} catch { /* optional file */ }
for (const [rawName, sup] of Object.entries(supplement.companies || {})) {
  const canon = canonicalise(rawName);
  const r = rec(canon);
  r.sources.add("verified_supplement");
  if (sup.extraText) r.textChunks.push(sup.extraText);
  for (const t of sup.tenureSamples || []) {
    r.tenureSamples.push({ name: t.name, months: t.months, source: "roster_career" }); // same confidence as dated roster data
    if (t.detail) r.textChunks.push(t.detail);
  }
  if (sup.departureDetail) r.textChunks.push(sup.departureDetail);
  r._supDepartures = sup.departureSignalsAdd || 0;
  r._supExPega = sup.exPegasystemsHiresAdd || 0;
}

// --- De-duplicate tenure samples per person (same human can appear in all 3 sources) ---
const out = [];
for (const r of base.values()) {
  const seen = new Map();
  for (const t of r.tenureSamples) {
    const k = norm(t.name);
    if (!k) continue;
    const prior = seen.get(k);
    // Prefer roster career data; it is date-structured rather than regex-sniffed.
    const rank = { roster_career: 3, audit_text: 2, fresh_evidence_text: 1 };
    if (!prior || rank[t.source] > rank[prior.source]) seen.set(k, t);
  }
  const tenures = [...seen.values()];

  // Pillar 4 cannot read short tenure as burnout on its own. A team that converts interns
  // and hires juniors (Booking) shows the same low average as a team people flee, but the
  // meaning is opposite. So separate the two causes and let the scorer weigh them:
  //   departures = people evidenced as having LEFT
  //   recentHires = people evidenced as having JOINED in the last ~18 months
  const allText = r.textChunks.join(" ");
  // CAREFUL: "ex-Pegasystems" / "ex-Cigna" name a person's PRIOR employer — they joined
  // this company from there. Counting those as departures inverted the signal completely
  // (First Citizens, a brand-new team of senior ex-Pegasystems hires, read as 13
  // departures and scored as the worst attrition risk in the list). Only count phrasing
  // that evidences leaving THIS company. "now at"/"moved to" are too ambiguous to use.
  const DEPART = /last working day|\bdeparted\b|serving notice|farewell|has left\b|\bresigned\b/gi;
  // Prior-employer provenance is a hiring-quality signal, so capture it separately.
  const EX_PEGA = /ex-pegasystems|ex pegasystems|former(?:ly)? (?:at )?pegasystems/gi;
  const JOINED = /joined|thrilled to share i|new beginnings|since (?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+202[56]|from (?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+202[56]/gi;
  const departures = (allText.match(DEPART) || []).length;
  const joinMentions = (allText.match(JOINED) || []).length;
  const freshTenures = tenures.filter((t) => t.months <= 18).length;

  out.push({
    company: r.company,
    departureSignals: departures + (r._supDepartures || 0),
    joinSignals: joinMentions,
    freshTenureCount: freshTenures,
    exPegasystemsHires: (allText.match(EX_PEGA) || []).length + (r._supExPega || 0),
    sectors: [...r.sectors],
    locations: [...r.locations],
    team_size: r.team_size,
    hiring_status: r.hiring_status,
    maturity: r.maturity,
    tech_stack: [...r.tech_stack],
    domains: [...r.domains],
    titles: r.titles,
    members: r.members,
    peopleCount: r.members.length,
    auditRows: r.auditRows,
    tenureSamples: tenures,
    tenureN: tenures.length,
    tenureAvgYears: tenures.length
      ? +(tenures.reduce((a, b) => a + b.months, 0) / tenures.length / 12).toFixed(2)
      : null,
    evidenceText: r.textChunks.join(" \n ").replace(/\s+/g, " ").trim(),
    sources: [...r.sources],
  });
}

out.sort((a, b) => b.peopleCount + b.auditRows - (a.peopleCount + a.auditRows));
writeFileSync(
  DIR + "gcc_evidence_base.json",
  JSON.stringify({ builtAt: new Date().toISOString(), asOf: "2026-10", companies: out }, null, 2),
  "utf8"
);

// --- Report so the merge can be checked rather than trusted ---
console.log("=== MERGED EVIDENCE BASE ===");
console.log(`companies: ${out.length}`);
console.log(`  from 3+ sources         : ${out.filter((c) => c.sources.length >= 3).length}`);
console.log(`  from 2 sources          : ${out.filter((c) => c.sources.length === 2).length}`);
console.log(`  from 1 source           : ${out.filter((c) => c.sources.length === 1).length}`);
console.log("");
const n3 = out.filter((c) => c.tenureN >= 3).length;
const n12 = out.filter((c) => c.tenureN >= 1 && c.tenureN < 3).length;
console.log(`tenure n>=3 (was 16 pre-merge): ${n3}`);
console.log(`tenure n=1..2                 : ${n12}`);
console.log(`tenure n=0                    : ${out.filter((c) => c.tenureN === 0).length}`);
console.log("");
console.log("top 30 by evidence volume:");
out.slice(0, 30).forEach((c) =>
  console.log(
    `  ${c.company.padEnd(36).slice(0, 36)} people=${String(c.peopleCount).padStart(3)} audit=${String(c.auditRows).padStart(3)} tenureN=${String(c.tenureN).padStart(2)} avg=${c.tenureAvgYears ?? "n/a"} src=${c.sources.length} chars=${c.evidenceText.length}`
  )
);
console.log("");
console.log("companies with NO people and NO audit rows (unscoreable):");
out.filter((c) => c.peopleCount === 0 && c.auditRows === 0).forEach((c) => console.log("  " + c.company));
