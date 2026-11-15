# Additional instructions and recommended changes for Claude

## Read first

This is a research handoff, not a statement that the proposed changes are already implemented. Inspect the current project before editing. Recommendations below identify required outcomes and areas to review; they are not all confirmed defects.

Read in this order: CLAUDE_PROMPT.md, this file, REPORT.md, portal-manifest.json, then reference_new/ARCHITECTURE.md. Use individual observations and evidence when implementing a source.

## User's intended outcome

Sathvik wants the original broad product-company/GCC list covered directly through company career portals, alongside LinkedIn. A small supported-ATS subset is insufficient. Preserve every original target and explicitly account for it, even when it cannot currently be scraped. Booking.com was specifically requested.

The user is a Pega CSSA developer, based in Bengaluru, targeting product/GCC roles and approximately ₹30 LPA+. Existing configuration prioritizes Bengaluru but searches India more broadly. Keep unknown salary roles eligible: an absent salary must not mean below target. Treat experience, compensation and company preference as ranking inputs unless the user's configuration explicitly makes them exclusion rules.

## Priority 0 — truthful and complete coverage accounting

1. Maintain a durable target inventory independent of enabled source configurations. A missing adapter must remain visible in the denominator. Link all 286 original name/alias rows to canonical employer IDs or an explicit unresolved identity record. Do not present 286 as a count of distinct companies.
2. Keep three separate dimensions: employer identity, configured source, and latest execution outcome. Having a URL is not an implemented adapter; having an adapter is not a successful scan.
3. Provide a company coverage screen and export with: canonical name; original names/aliases; type; career URL; ATS/board; company-specific LinkedIn query yes/no; direct portal configured yes/no; last attempted time; last successful time; latest status; failure reason; scan/run ID; completeness of search pages and details; next action. Include unconfigured/missing targets.
4. Distinguish generic LinkedIn keyword search, employer-specific keyword query, and employer-ID-filtered search. A company name inside a search query is not necessarily an exact employer filter. Do not count generic discovery as guaranteed company coverage.
5. Use the existing source outcomes (ok, empty, partial, blocked, maintenance, skipped, error). Keep an additional inventory state for not configured/unsupported/identity unresolved; do not label these empty.
6. Label UI actions clearly, for example full configured-source scan versus retry incomplete sources. Explain that a run marked partial is an outcome, not necessarily a separate search algorithm. Show what was requested, scheduled, attempted and completed for that run. Inspect current semantics before changing labels or behavior.

## Priority 1 — expand direct portals with the existing adapters

- Workday: use the exact tenant/datacentre/site candidates in workday_probes.json. There are 26 responding boards across 25 backlog targets; these are bounded search checks, not production-ready integrations. Verify India/entity scope before enabling. Do not hard-code all hosts to wd1/wd5: observed hosts include wd502, wd503 and wd504.
- Oracle: validate current official routes for American Express, BNY, Nokia, Cummins and other Oracle-marked targets. Resolve any custom-domain versus canonical API-host differences from published site information.
- Greenhouse/Lever: reuse current adapters where the actual official board identity is confirmed.
- Start with correctly scoped candidates, then report remaining work. Never silently enable a US/retail board to make the coverage number look larger.
- Identity gates: Booking.com versus Booking Holdings; BMW TechWorks versus BMW Group; FIS versus TSYS/Global Payments; IBM versus Confluent; Mercedes-Benz versus Daimler Truck; Toyota/TFS versus TMNA; VW Digital Solutions India versus CARIAD; Renault-Nissan India versus a broader Renault board. Preserve business-unit attribution where boards are shared.

## Priority 2 — add the missing adapter families

Use the per-company evidence to choose the actual vacancy provider. Build reusable adapters where possible for SuccessFactors, Eightfold, SmartRecruiters, Avature, TalentBrew and iCIMS. Evaluate PeopleStrong (BMW TechWorks), RippleHire (HDFC), Ashby (Confluent), BeeSite and company-specific feeds as needed. Some employers use Phenom as a frontend to Workday/Oracle: multiple HTML markers do not mean multiple independent job inventories.

Historical adapter modules are reference material. Some depend on Playwright/browser response listeners; they must not be copied into a stdlib-only runtime unchanged. Endpoint strings in old code are not current validation. If a portal cannot be supported under the current architecture, keep it visible with the reason and document the concrete architectural change needed; do not quietly add browser automation or third-party runtime dependencies.

## Priority 3 — completeness, reliability and relevance

- Search Pega/PRPC using the project's matcher and confirm title or description relevance. Review search synonym coverage and upstream title-only behavior. Do not assume a query for Pega finds PRPC-only listings; establish search behavior and merge query results by stable ID.
- Read full descriptions where required. Unknown descriptions, unread pages and failed detail calls must affect completeness. Review whether current detail budgets can hide otherwise relevant roles.
- India remains the geographic scope, Bengaluru first. Check multi-location details; unknown/remote locations need an explicit policy and must not be silently treated as foreign. Do not accidentally narrow every source to Bengaluru only.
- Use stable employer/board/requisition identifiers and preserve both career-site and LinkedIn provenance. Review source-ID collisions between different boards and companies. Avoid merging unrelated same-title vacancies.
- Preserve original posted dates when available, first_seen, last_seen and last successful source check separately. A missing result during a partial/failed scan is not proof a vacancy closed. Confirm availability from a successful authoritative check before expiring/removing a job.
- Complete pagination or report a cap/timeout explicitly. An unfiltered sanity check should distinguish a valid zero-match query from a wrong tenant/site. Preserve what was already collected when a later page fails.
- Current config uses a 40-minute budget and 6 workers. Expansion may exceed this budget. Measure source cost, maintain per-host pacing, use bounded retries/backoff and resumable progress, and make budget-exhausted sources visible. Do not guarantee every target is scanned daily until an actual full run demonstrates it.
- Review fairness so slow LinkedIn/detail work cannot repeatedly leave the same portal backlog unattempted. Shared boards should be fetched once where safe and attributed to verified business units afterward.
- Preserve existing source circuit breakers, TLS verification and refusal reporting. Diagnose certificate trust/DNS separately from site refusals; do not convert them to empty results.

## Priority 4 — operations and handoff

The new app is at C:\Users\sathv\Desktop\image\pega-radar and serves http://127.0.0.1:8765/. Earlier session work disabled PegaCareerDeskNightlyScan and enabled PegaRadarDailyScan at 07:30 Asia/Calcutta. This is historical session context, not a fresh scheduler check. Inspect actual task state before operational changes; preserve one primary daily scanner and do not re-enable the old job or create duplicate schedules.

Preserve saved jobs, applications, notes, preferences, existing source history and deduplication links. Back up the data before any schema migration and make migration repeatable. Keep the server loopback-only and retain existing mutation-token and HTML-escaping protections.

Update README/ARCHITECTURE and UI help with the actual coverage model, run modes and remaining limitations. Include an export the user can review without reading code.

## Validation and acceptance

Develop with offline fixtures/fake HTTP, as ARCHITECTURE.md requires. The request for bounded live checks in CLAUDE_PROMPT.md refers to a separate operational acceptance stage after offline implementation, not network calls embedded in unit tests. Follow any current applicable project instructions for that stage.

Required evidence before calling an integration complete:

1. Canonical employer/aliases and official portal relationship established.
2. Broad search sanity and correctly scoped India/entity search demonstrated.
3. Pagination, detail extraction and stable IDs verified; totals/caps explained.
4. Relevant and irrelevant Pega/PRPC fixtures, multi-location India fixtures and malformed/empty/error response fixtures covered.
5. Source state and user-facing coverage accurately reflect timeout, refusal, detail failure and budget exhaustion.
6. Persistence/deduplication and existing saved data remain intact.
7. Before/after matrix for every original target and a run-level acceptance report with unresolved cases and reasons. An unresolved source is still a gap; it must not increase successful coverage.

## What this package does and does not establish

- All 117 backlog/identity targets received a research attempt. Outcome: 25 targets with responding Workday searches, 77 with reachable pages but no verified integration, 15 with unresolved access/network/URL issues.
- The 68 currently configured product/GCC portal entries are a configuration baseline, not a fresh live audit. Recheck them during operational acceptance as well as newly added boards.
- Homepage HTTP 200 and heuristic vendor markers are weak evidence. Workday probes read only one result per query. No complete job enumeration or complete India/entity validation was performed.
- Historical observations are stored under history. Do not promote old success or endpoint diagnostics to current evidence.
- No scanner source, registry, schedule or database was modified by this research. The package contains research and reference code, not an implementation patch.

## Expected final delivery from Claude

Deliver working code, documented migrations if needed, offline test results, an operational acceptance report, and the complete company coverage export. List implemented versus still unresolved targets and explain each unresolved case. Clearly state actual daily-run coverage and runtime; do not replace those facts with the number of names in the registry.
