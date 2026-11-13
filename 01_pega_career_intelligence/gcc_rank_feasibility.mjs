// Task 1 of the GCC ranking build: coverage feasibility report.
// Purpose: before scoring anything, measure how much evidence actually exists per
// company for each of the four rubric pillars. A pillar that cannot be measured must
// be reported as unmeasured, never silently scored as zero or guessed.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const directory = dirname(fileURLToPath(import.meta.url));
// Keep paths script-relative so the handoff export remains portable.
const SRC = join(directory, "team_intelligence_enriched.json");
const data = JSON.parse(readFileSync(SRC, "utf8"));

// "Present"/current-role anchor. The dataset was last refreshed Sep 2026 and the hub's
// review date is Oct 2026, so tenure-to-now is measured against Oct 2026 rather than
// the real clock, otherwise re-running this later silently inflates every tenure.
const AS_OF = { y: 2026, m: 10 };
const MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];

function parseMonthYear(text) {
  if (!text) return null;
  const m = /([a-z]{3})[a-z]*\s+(\d{4})/i.exec(text);
  if (m) {
    const idx = MONTHS.indexOf(m[1].toLowerCase());
    if (idx >= 0) return { y: Number(m[2]), m: idx + 1 };
  }
  const yearOnly = /\b(19|20)(\d{2})\b/.exec(text);
  if (yearOnly) return { y: Number(yearOnly[0]), m: 7 }; // mid-year when only a year is known
  return null;
}

const monthsBetween = (a, b) => (b.y - a.y) * 12 + (b.m - a.m);

// Normalise company names enough to match a career[].company string against the GCC.
function norm(s) {
  return (s || "")
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]/g, "");
}

function companyMatches(careerCompany, gccName) {
  const a = norm(careerCompany);
  const b = norm(gccName);
  if (!a || !b) return false;
  if (a === b) return true;
  // Compare on the distinctive leading token(s): "JPMorganChase" vs "JPMorgan Chase",
  // "Wells Fargo" vs "Wells Fargo Bank", "MetLife India GCC" vs "MetLife".
  const short = a.length < b.length ? a : b;
  const long = a.length < b.length ? b : a;
  return short.length >= 5 && long.startsWith(short.slice(0, Math.max(5, Math.floor(short.length * 0.8))));
}

// Tenure at THIS company for one member: earliest start across all career entries that
// belong to the company, measured to the end of the latest such entry (or to AS_OF when
// the person is still there). career[] is role-level, so consecutive promotions at the
// same employer must collapse into a single tenure, not be averaged as separate stints.
function memberTenureMonths(member, gccName) {
  const career = member.career || [];
  const owned = career.filter((stop) => {
    if (stop.company) return companyMatches(stop.company, gccName);
    // No company field: treat as the current employer only for the first entry.
    return career.indexOf(stop) === 0;
  });
  if (!owned.length) return null;

  let earliest = null;
  let stillThere = false;
  let latestEnd = null;

  for (const stop of owned) {
    const dates = stop.dates || "";
    const [startRaw, endRaw] = dates.split(/\s*[-–]\s*/, 2);
    const start = parseMonthYear(startRaw);
    if (start && (!earliest || start.y * 12 + start.m < earliest.y * 12 + earliest.m)) earliest = start;
    if (/present|current/i.test(dates)) stillThere = true;
    else {
      const end = parseMonthYear(endRaw);
      if (end && (!latestEnd || end.y * 12 + end.m > latestEnd.y * 12 + latestEnd.m)) latestEnd = end;
    }
  }
  if (!earliest) return null;
  const end = stillThere ? AS_OF : latestEnd;
  if (!end) return null;
  const months = monthsBetween(earliest, end);
  return months > 0 && months < 600 ? months : null;
}

// --- Pillar keyword probes (presence of evidence, not scoring yet) ---
const P2_HEAVY = /kafka|event[- ]driven|event stream|middleware|esb|mq\b|activemq|jms|rabbitmq|ibm mq|nervous system|soap|rest\b|api gateway|iso ?20022|swift/i;
const P2_MODERN = /constellation|react|dx api|custom java|java step|cosmos|blueprint|agentic|genai|gen ai|llm/i;
const P2_CLOUD = /pega cloud|aws|azure|gcp|google cloud|openshift|kubernetes|helm|docker|ci\/cd|jenkins|devops|terraform|pdc|splunk|observability/i;
const P2_SUPPORT = /l2\/l3|l2 \/ l3|\bl2\b|\bl3\b|ticket|incident|production support|bau\b|version upgrade|patch(ing)?\b|maintenance/i;
const P3_EVENT = /pegaworld|pega world|pegainnovate|pega innovate|pegafest|pega day|keynote|presented|speaker|conference/i;
const P3_COMMUNITY = /forum|community|blog|open[- ]source|github|stack overflow|published|article|webinar|badge/i;
const P1_TOP = /global head|head of pega|principal architect|principal pega|chief architect|global lead|director[ ,-]*pega|pega architecture|engineering director|distinguished/i;
const P1_ARCH = /\b(lsa|clsa|pclsa)\b|lead system architect|senior system architect|solution architect|technical architect|principal engineer|senior staff|staff engineer|lead architect/i;
const P1_DELIVERY = /delivery manager|operations lead|support manager|ops lead|service delivery|production support|bau lead|incident manager|scrum master|project manager|program manager/i;

function companyText(c) {
  return [
    c.projects || "",
    (c.tech_stack || []).join(" "),
    (c.domains || []).join(" "),
    (c.highlights || []).join(" "),
    (c.team_members || []).map((m) => [m.title, m.certs, (m.career || []).map((s) => s.detail).join(" ")].join(" ")).join(" "),
  ].join(" ");
}

const rows = [];
for (const c of data.companies) {
  const members = c.team_members || [];
  const tenures = members.map((m) => memberTenureMonths(m, c.name)).filter((v) => v !== null);
  const text = companyText(c);
  const titles = members.map((m) => m.title || "").join(" | ");

  rows.push({
    name: c.name,
    members: members.length,
    tenureN: tenures.length,
    tenureAvgYrs: tenures.length ? +(tenures.reduce((a, b) => a + b, 0) / tenures.length / 12).toFixed(2) : null,
    p1_top: P1_TOP.test(titles),
    p1_arch: P1_ARCH.test(titles) || P1_ARCH.test(members.map((m) => m.certs || "").join(" ")),
    p1_delivery: P1_DELIVERY.test(titles),
    p2_heavy: P2_HEAVY.test(text),
    p2_modern: P2_MODERN.test(text),
    p2_cloud: P2_CLOUD.test(text),
    p2_support: P2_SUPPORT.test(text),
    p3_event: P3_EVENT.test(text),
    p3_comm: P3_COMMUNITY.test(text),
  });
}

// --- Coverage summary: the thing that decides whether this ranking is honest ---
const tenureUsable = rows.filter((r) => r.tenureN >= 3).length;
const tenureThin = rows.filter((r) => r.tenureN >= 1 && r.tenureN < 3).length;
const tenureNone = rows.filter((r) => r.tenureN === 0).length;

console.log("=== GCC RANKING FEASIBILITY (source: team_intelligence_enriched.json) ===");
console.log(`companies: ${rows.length}   members: ${rows.reduce((a, r) => a + r.members, 0)}`);
console.log("");
console.log("PILLAR 4 (tenure/attrition) measurability:");
console.log(`  n>=3 engineers with parseable company tenure : ${tenureUsable}  <- defensible average`);
console.log(`  n=1..2 (too thin for an average)            : ${tenureThin}`);
console.log(`  n=0 (no tenure evidence at all)             : ${tenureNone}`);
console.log("");
console.log("PILLAR 1 (autonomy) title-signal presence:");
console.log(`  top-level (global head / principal / director): ${rows.filter((r) => r.p1_top).length}`);
console.log(`  architect ladder (LSA/CLSA/lead arch)         : ${rows.filter((r) => r.p1_arch).length}`);
console.log(`  delivery/ops-led signal present               : ${rows.filter((r) => r.p1_delivery).length}`);
console.log("");
console.log("PILLAR 2 (modernity) keyword presence:");
console.log(`  heavy integration (Kafka/EDA/middleware/MQ)   : ${rows.filter((r) => r.p2_heavy).length}`);
console.log(`  modern UI/custom Java (Constellation/React)   : ${rows.filter((r) => r.p2_modern).length}`);
console.log(`  cloud/devops/observability                   : ${rows.filter((r) => r.p2_cloud).length}`);
console.log(`  support-farm language present                 : ${rows.filter((r) => r.p2_support).length}`);
console.log("");
console.log("PILLAR 3 (innovation visibility) keyword presence:");
console.log(`  conference/PegaWorld/PegaInnovate evidence    : ${rows.filter((r) => r.p3_event).length}`);
console.log(`  forum/blog/community evidence                 : ${rows.filter((r) => r.p3_comm).length}`);
console.log("");
console.log("=== per-company tenure detail (sorted by sample size) ===");
rows
  .slice()
  .sort((a, b) => b.tenureN - a.tenureN || b.members - a.members)
  .forEach((r) => {
    const avg = r.tenureAvgYrs === null ? "  n/a" : `${String(r.tenureAvgYrs).padStart(5)}y`;
    console.log(
      `${r.name.padEnd(34).slice(0, 34)} mem=${String(r.members).padStart(3)} tenureN=${String(r.tenureN).padStart(2)} avg=${avg}`
    );
  });
