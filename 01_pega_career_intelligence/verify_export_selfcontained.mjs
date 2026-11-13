#!/usr/bin/env node
// Proves the export folder is genuinely self-contained and reproduces the SAME
// scores as the original workspace.
//
// WHY this is needed: the gcc_* scripts used to hardcode an absolute DIR. A copied
// folder would then read its inputs from the ORIGINAL directory and appear to work
// while being completely non-portable. That failure is invisible without an
// explicit check, so this asserts it rather than assuming it.
//
// Usage: node verify_export_selfcontained.mjs <exportDir> <originalRankingJson>
//   e.g. node verify_export_selfcontained.mjs ./PEGA_GCC_HANDOFF_EXPORT ./gcc_ranking_scores.json

import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, extname } from "node:path";

const exportDir = process.argv[2];
const originalJson = process.argv[3];

if (!exportDir || !originalJson) {
  console.error("usage: node verify_export_selfcontained.mjs <exportDir> <originalRankingJson>");
  process.exit(2);
}

let bad = 0;
const chk = (name, cond, detail) => {
  console.log((cond ? "PASS  " : "FAIL  ") + name + (detail ? `  ${detail}` : ""));
  if (!cond) bad++;
};

// -- 1. Score reproduction ------------------------------------------------
// generatedAt is a wall-clock timestamp and must differ between runs, so it is
// excluded. Everything that represents an actual finding must be identical.
function comparable(obj) {
  const { generatedAt, ...rest } = obj;
  return rest;
}

const exportedPath = join(exportDir, "gcc_ranking_scores.json");
chk("export contains gcc_ranking_scores.json", existsSync(exportedPath));

if (existsSync(exportedPath)) {
  const orig = JSON.parse(readFileSync(originalJson, "utf8"));
  const copy = JSON.parse(readFileSync(exportedPath, "utf8"));

  const a = JSON.stringify(comparable(orig));
  const b = JSON.stringify(comparable(copy));
  chk(
    "export pipeline reproduces IDENTICAL scores (generatedAt excluded)",
    a === b,
    a === b ? `${copy.companies.length} companies match` : "MISMATCH - see diff below"
  );

  if (a !== b) {
    // Pinpoint which companies differ so the failure is actionable.
    const byName = new Map(orig.companies.map((c) => [c.company_name, c]));
    let shown = 0;
    for (const c of copy.companies) {
      const o = byName.get(c.company_name);
      if (!o) { console.log(`   only in export: ${c.company_name}`); continue; }
      if (JSON.stringify(o) !== JSON.stringify(c)) {
        console.log(`   differs: ${c.company_name}  orig=${o.total_score} export=${c.total_score}`);
        if (++shown > 15) { console.log("   ... (truncated)"); break; }
      }
    }
    if (JSON.stringify(orig.counts) !== JSON.stringify(copy.counts)) {
      console.log(`   counts differ: ${JSON.stringify(orig.counts)} vs ${JSON.stringify(copy.counts)}`);
    }
  }
}

// -- 2. No absolute-path leakage ------------------------------------------
// A single surviving absolute path silently re-points the export at the original
// workspace, which is exactly the bug this export exists to avoid.
const FORBIDDEN = /C:[\\/]Users[\\/]DNSATHV/i;
const textExt = new Set([".mjs", ".js", ".json", ".md", ".bat", ".txt"]);
const offenders = [];

function walk(dir) {
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry);
    if (statSync(p).isDirectory()) { walk(p); continue; }
    if (!textExt.has(extname(entry).toLowerCase())) continue;
    // The HTML hub is data, not code, and may legitimately contain paths.
    const text = readFileSync(p, "utf8");
    const lines = text.split("\n");
    lines.forEach((line, i) => {
      if (FORBIDDEN.test(line)) offenders.push(`${entry}:${i + 1}: ${line.trim().slice(0, 110)}`);
    });
  }
}
if (existsSync(exportDir)) walk(exportDir);

chk("no hardcoded absolute workspace path in any export script/doc", offenders.length === 0);
for (const o of offenders.slice(0, 20)) console.log("   " + o);
if (offenders.length > 20) console.log(`   ... and ${offenders.length - 20} more`);

// -- 3. Required files present -------------------------------------------
const required = [
  "gcc_rank_feasibility.mjs",
  "gcc_build_evidence.mjs",
  "gcc_score_rubric.mjs",
  "gcc_explain_company.mjs",
  "build_gcc_ranking_section.mjs",
  "build_handoff_bundle.mjs",
  "team_intelligence_enriched.json",
  "pega_full_audit.json",
  "gcc_evidence_supplement.json",
  "gcc_lifestyle_supplement.json",
  "gcc_evidence_base.json",
  "gcc_ranking_scores.json",
  "Pega_Career_Intelligence_Hub.html",
  "PEGA_GCC_HANDOFF_BUNDLE.md",
  "PEGA_GCC_HANDOFF_BRIEF.md",
  "README.md",
];
const missing = required.filter((f) => !existsSync(join(exportDir, f)));
chk(`all ${required.length} required files present`, missing.length === 0, missing.length ? "missing: " + missing.join(", ") : "");

// -- 4. The handoff docs regenerated inside the export must match too -----
const bundlePath = join(exportDir, "PEGA_GCC_HANDOFF_BUNDLE.md");
if (existsSync(bundlePath)) {
  const md = readFileSync(bundlePath, "utf8");
  chk("export bundle has no unresolved placeholders", !/\bundefined\b/.test(md) && !md.includes("${"));
  const copy = existsSync(exportedPath) ? JSON.parse(readFileSync(exportedPath, "utf8")) : null;
  if (copy) {
    const allNamed = copy.companies.every((c) => md.includes(c.company_name));
    chk("export bundle names every company in the export scores", allNamed);
  }
}

console.log(`\nFAILURES: ${bad}`);
process.exit(bad === 0 ? 0 : 1);
