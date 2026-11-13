# Verification

Run from this directory:

- `python -B -m unittest test_unified_repository test_scan_coordinator test_workspace_browser test_portal test_original_flow test_job_matching test_job_recommendations test_campaign test_parallel_scan test_parallel_client test_people_views test_intelligence_layout`
- Browser fixture tests require the Python Playwright package and its Chromium installation. They route application requests to a temporary Flask test client and do not scrape external sites.
- `python app.py --port 5050` starts the local portal. Use the direct URL to preserve same-origin mutation checks.

# Data safety and scope

- Keep legacy `records` and research files intact. The relational tables are additive.
- Never clean, deduplicate, or delete the production database during verification; use temporary SQLite databases.
- India/Bengaluru is the active scope. Remote/global discovery, Indeed US, and Dice US remain paused.
- A source returning no extracted candidates is not proof of no openings. Employer branding is not proof of Pega responsibilities.
- Probable vacancy matches must retain all raw observations and source links; conflicting requisition IDs or different cities stay separate.
- Do not bypass TLS verification or access-denial responses to install dependencies or fetch sites.
