# Career hub verification

These instructions apply to `Pega_Career_Intelligence_Hub.html` and its verification script only.

- The hub is a standalone HTML file that works through `file://`; no build or web server is required.
- Run `node verify_pega_career_hub.mjs` from this directory. It uses the existing Puppeteer dependency, checks the original backup SHA-256, table preservation, search, navigation, responsive overflow and toolbar clearance, and generates desktop/mobile review screenshots.
- Keep `Pega_Career_Intelligence_Hub.backup-2026-09-22.html` unchanged. It is the original user-requested backup.
- Distinguish search-index job evidence from a verified open official requisition. Historical team movement does not establish approved replacement hiring.
- `pega_full_audit.json` records the full-directory research and follow-ups. It is researched data, not an automated live employment feed.
- `node audit_pega_directory.mjs 0 0` regenerates the inventory from the immutable `Pega_Career_Intelligence_Hub.pre-full-audit-2026-09-22.html` snapshot, not from the evolving current page. Preserve this snapshot and the earlier backups.
- `node build_pega_full_audit.mjs` embeds the ledger into the current HTML's `full-directory-audit-rows` region and regenerates `employer-evidence-rows` and `unmapped-people-rows`. It checks the immutable snapshot hash and covers 159 employer rows and all 329 audit records (293 mapped, 36 held separately for unsafe or absent employer labels). The first-party programme map is manually curated inside this script; programme-level sources do not prove a listed individual's assignment or a current vacancy. No external data file is needed to view the resulting HTML offline.
- After regenerating, run `node verify_pega_career_hub.mjs`; it also checks complete contact coverage, deep audit anchors, and audit readability with JavaScript disabled.
