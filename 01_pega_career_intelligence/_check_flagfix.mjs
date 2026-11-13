// Asserts the LSA-audit fix changed FLAGS ONLY and moved no score.
import { readFileSync } from "node:fs";

const before = JSON.parse(readFileSync("_baseline_ranking.json", "utf8"));
const after = JSON.parse(readFileSync("gcc_ranking_scores.json", "utf8"));
const b = new Map(before.companies.map((c) => [c.company_name, c]));

let scoreMoves = 0;
let flagChanges = 0;
const newlyFlagged = [];

for (const a of after.companies) {
  const o = b.get(a.company_name);
  if (!o) { console.log(`NEW company: ${a.company_name}`); continue; }
  if (a.total_score !== o.total_score) {
    scoreMoves++;
    console.log(`SCORE MOVED: ${a.company_name} ${o.total_score} -> ${a.total_score}`);
  }
  if (JSON.stringify(a.pillar_breakdown) !== JSON.stringify(o.pillar_breakdown)) {
    scoreMoves++;
    console.log(`PILLARS MOVED: ${a.company_name}`);
  }
  if (a.rank !== o.rank) console.log(`RANK MOVED: ${a.company_name} ${o.rank} -> ${a.rank}`);
  const rf = (x) => JSON.stringify(x.red_flags ?? []);
  const gf = (x) => JSON.stringify(x.green_flags ?? []);
  if (rf(a) !== rf(o) || gf(a) !== gf(o)) {
    flagChanges++;
    const added = (a.red_flags ?? []).filter((f) => !(o.red_flags ?? []).includes(f));
    if (added.some((f) => /LSA/i.test(f))) {
      newlyFlagged.push(`${a.company_name} (score ${a.total_score}, rank ${a.rank}, P1=${a.pillar_breakdown?.p1_architectural_autonomy?.score})`);
    }
  }
}

const lsaRed = (set) => set.companies.filter((c) => (c.red_flags ?? []).some((f) => /No LSA\/CLSA/i.test(f))).length;
const partialRed = (set) => set.companies.filter((c) => (c.red_flags ?? []).some((f) => /in-progress LSA/i.test(f))).length;

console.log(`\nscores/pillars moved : ${scoreMoves}   (MUST be 0)`);
console.log(`companies with flag changes : ${flagChanges}`);
console.log(`"No LSA/CLSA" red flag : ${lsaRed(before)} -> ${lsaRed(after)} of ${after.counts.scored}`);
console.log(`"in-progress LSA" red flag : ${partialRed(before)} -> ${partialRed(after)}`);
console.log(`\nnewly flagged for missing a completed LSA:`);
for (const n of newlyFlagged) console.log(`  ${n}`);

process.exit(scoreMoves === 0 ? 0 : 1);
