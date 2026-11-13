// Two suspected defects in the Pillar-1 LSA audit:
//  A) The "No LSA/CLSA-certified architect" red flag lives ONLY in the +15
//     (archInIndia) branch. Companies scoring +30 skip the check entirely - so the
//     weakness is invisible at the TOP of the ranking, including Ford at #1.
//  B) /\blsa\b/ matches "LSA Part 1", an in-progress credential, counting a partial
//     LSA candidate as a certified LSA holder.
// Measure both rather than assert them.
import { readFileSync } from "node:fs";

const base = JSON.parse(readFileSync("gcc_evidence_base.json", "utf8"));
const rows = Array.isArray(base) ? base : base.companies ?? [];
const ranking = JSON.parse(readFileSync("gcc_ranking_scores.json", "utf8"));
const byName = new Map(rows.map((r) => [r.company, r]));

// Exactly the regex the scorer uses.
const LSA_LOOSE = /\b(?:lsa|clsa|pclsa)\b/i;
// A stricter reading: a COMPLETED LSA/CLSA, not a part-1/in-progress marker.
// Must allow the optional C prefix - "CLSA-1" and "CLSA Part 1" are partials too,
// and \blsa would never match inside "CLSA" because C is a word character.
const PARTIAL = /\bc?p?lsa[\s-]*(?:part[\s-]*)?(?:1|2|i|ii|one|two)\b|\bc?lsa\s*part\b|pursuing|in progress|appearing/i;

// Per-credential check: a person may hold BOTH a partial and a completed cert, so
// split the cert list and ask whether any single credential is a completed LSA.
const hasCompletedLsa = (s) =>
  String(s ?? "")
    .split(/[,;|]/)
    .map((t) => t.trim())
    .some((t) => /\bc?p?lsa\b/i.test(t) && !PARTIAL.test(t));

console.log("=== B) does the scorer's regex match an in-progress LSA? ===");
for (const s of ["LSA Part 1", "LSA Part 2", "CLSA", "LSA", "CSSA, CSA", "LSA-1", "CLSA-1", "CLSA Part 1", "LSA Part 1, CSSA, CSA", "CLSA, CSSA"]) {
  console.log(
    `  ${JSON.stringify(s).padEnd(26)} scorerSaysHolder=${String(LSA_LOOSE.test(s)).padEnd(5)}  hasCompletedLSA=${hasCompletedLsa(s)}`
  );
}

console.log("\n=== A) blast radius: P1=30 companies never get the LSA check ===");
const scored = ranking.companies.filter((c) => c.score_status === "SCORED");
const p30 = scored.filter((c) => c.pillar_breakdown?.p1_architectural_autonomy?.score === 30);
const p15 = scored.filter((c) => c.pillar_breakdown?.p1_architectural_autonomy?.score === 15);
console.log(`P1=30 companies: ${p30.length}   P1=15 companies: ${p15.length}`);

const flagFires = scored.filter((c) => (c.red_flags ?? []).some((f) => /LSA\/CLSA/i.test(f)));
console.log(`red flag currently fires on: ${flagFires.length} companies`);
console.log(`  ...all of them P1=15? ${flagFires.every((c) => c.pillar_breakdown?.p1_architectural_autonomy?.score === 15)}`);

console.log("\nP1=30 companies, audited for a REAL completed LSA/CLSA holder:");
let wouldFire = 0;
let wouldFirePartialOnly = 0;
for (const c of p30.sort((a, b) => b.total_score - a.total_score)) {
  const ev = byName.get(c.company_name);
  const members = ev?.members ?? [];
  const holders = members.filter((m) => LSA_LOOSE.test(`${m.title ?? ""} ${m.certs ?? ""}`));
  const strict = holders.filter((m) => hasCompletedLsa(`${m.title ?? ""} ${m.certs ?? ""}`));
  const partialOnly = holders.length > 0 && strict.length === 0;
  if (holders.length === 0) wouldFire++;
  if (partialOnly) wouldFirePartialOnly++;
  const verdict = holders.length === 0 ? "NO LSA AT ALL" : partialOnly ? "PARTIAL LSA ONLY" : `${strict.length} real`;
  console.log(
    `  ${String(c.total_score).padStart(3)}  rank ${String(c.rank).padStart(2)}  ${c.company_name.padEnd(32).slice(0, 32)} ${verdict}` +
      (holders.length ? `   [${holders.map((m) => `${m.name}: ${m.certs ?? "-"}`).join(" | ").slice(0, 110)}]` : "")
  );
}
console.log(`\nP1=30 companies that WOULD trip the flag (no LSA at all) : ${wouldFire}`);
console.log(`P1=30 companies whose only "LSA" is an in-progress one    : ${wouldFirePartialOnly}`);
console.log(`=> red flag coverage would go from ${flagFires.length} to ${flagFires.length + wouldFire + wouldFirePartialOnly} of ${scored.length}`);
