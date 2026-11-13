"""Generate a self-contained HTML report of today's scan results.

Produces a single .html file with all CSS/data inline — no server needed.
Just double-click to open in any browser.
"""
import json
import os
import sys
from datetime import datetime, date
from html import escape
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / '.deps'))


def _load_results(app=None):
    """Load scan results using the Flask app's test client."""
    if app is None:
        from app import create_app
        app = create_app()

    client = app.test_client()
    boot = client.get('/api/bootstrap').get_json()
    results = client.get('/api/scan-results?scope=all').get_json()
    board_data = client.get('/api/board-jobs').get_json()
    scrape_log = client.get('/api/scrape-log').get_json()
    campaign = client.get('/api/campaign').get_json()

    return {
        "profile": boot.get("profile", {}),
        "scan_results": results,
        "board_jobs": board_data.get("jobs", []),
        "scrape_summary": scrape_log.get("summary", {}),
        "campaign": campaign,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


def build_report(data=None, output_path=None, app=None):
    """Build a self-contained HTML report and save it."""
    if data is None:
        data = _load_results(app)

    if output_path is None:
        desktop = Path(os.path.expanduser("~/Desktop"))
        output_path = desktop / f"Pega_Jobs_{date.today().isoformat()}.html"

    companies = data["scan_results"].get("companies", [])
    policy_counts = data["scan_results"].get("policy_counts", {})
    board_jobs = data.get("board_jobs", [])
    scrape = data.get("scrape_summary", {})
    profile = data.get("profile", {})

    # --- Helpers ---
    import re as _re
    import urllib.parse as _urlparse

    def _loc_bucket(loc):
        l = (loc or "").lower()
        if any(k in l for k in ("bengaluru", "bangalore")):
            return "bengaluru"
        if "remote" in l:
            return "remote"
        if any(k in l for k in ("india", "hyderabad", "pune", "chennai", "mumbai", "delhi", "gurgaon", "gurugram", "noida", "kolkata", "kochi")):
            return "other_india"
        return "international"

    def _norm_title(t):
        return _re.sub(r"[^a-z0-9]", "", (t or "").lower())

    def _norm_company(c):
        return _re.sub(r"[^a-z0-9]", "", (c or "").lower())[:20]

    def _norm_url(u):
        # Strip tracking params for dedup
        parsed = _urlparse.urlsplit(u or "")
        return (parsed.hostname or "") + parsed.path.rstrip("/").lower()

    def _source_label(source):
        s = (source or "").lower()
        if "linkedin" in s: return "LinkedIn"
        if "employer" in s: return "Employer"
        if "indeed" in s: return "Indeed"
        if "shine" in s: return "Shine"
        if "dice" in s: return "Dice"
        if "glassdoor" in s: return "Glassdoor"
        if "simplyhired" in s: return "SimplyHired"
        return source or "Other"

    def _source_key(source):
        return _re.sub(r"[^a-z]", "", _source_label(source).lower())

    # --- Merge + deduplicate all jobs ---
    raw_jobs = []
    for c in companies:
        for j in c.get("jobs", []):
            j.setdefault("category", c.get("category", "unknown"))
            raw_jobs.append(j)
    for j in board_jobs:
        j.setdefault("category", "unknown")
        j["is_new"] = True  # board jobs are always fresh
        raw_jobs.append(j)

    # Deduplicate: same URL, or same normalized title+company = duplicate
    seen_urls = set()
    seen_identity = set()
    merged = []
    dupes = 0
    for j in raw_jobs:
        url_key = _norm_url(j.get("url", ""))
        title_key = _norm_title(j.get("title", ""))
        company_key = _norm_company(j.get("company", ""))
        identity = title_key + "|" + company_key

        if url_key and url_key in seen_urls:
            dupes += 1
            continue
        if identity and identity in seen_identity and len(title_key) > 8:
            dupes += 1
            continue
        if url_key:
            seen_urls.add(url_key)
        if identity:
            seen_identity.add(identity)
        merged.append(j)

    # Stats
    total_jobs = len(merged)
    new_jobs = sum(1 for j in merged if j.get("is_new"))
    companies_with_jobs = len(set(j.get("company", "") for j in merged if j.get("company")))
    recommended = policy_counts.get("recommended", 0) + policy_counts.get("stretch", 0)
    review = policy_counts.get("review", 0)

    # Counts per filter
    loc_counts = {}
    cat_counts = {}
    src_counts = {}
    for j in merged:
        lb = _loc_bucket(j.get("location", ""))
        loc_counts[lb] = loc_counts.get(lb, 0) + 1
        cat = j.get("category", "unknown")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        sk = _source_key(j.get("source", ""))
        src_counts[sk] = src_counts.get(sk, 0) + 1

    # Build rows
    job_rows = []
    for j in sorted(merged, key=lambda x: (not x.get("is_new"), x.get("company", ""))):
        new_badge = '<span class="new">NEW</span>' if j.get("is_new") else ""
        rec = j.get("recommendation", {})
        rec_badge = ""
        if rec.get("status") == "recommended":
            rec_badge = '<span class="rec">Recommended</span>'
        elif rec.get("status") == "stretch":
            rec_badge = '<span class="stretch">Stretch</span>'

        url = escape(j.get("url", "#"))
        title = escape(j.get("title", "Role"))
        company = escape(j.get("company", "?"))
        location = escape(j.get("location", "?"))
        source = _source_label(j.get("source", "?"))
        cat = j.get("category", "unknown")
        loc_b = _loc_bucket(j.get("location", ""))
        src_b = _source_key(j.get("source", ""))
        cat_label = {"gcc": "GCC", "services": "Consulting", "global": "Global"}.get(cat, cat.title())

        job_rows.append(f"""<tr data-loc="{loc_b}" data-src="{src_b}" data-cat="{escape(cat)}" class="job-row">
            <td>{new_badge} <a href="{url}" target="_blank" rel="noopener">{title}</a></td>
            <td>{company}</td>
            <td>{location}</td>
            <td>{escape(source)}</td>
            <td><span class="cat-badge cat-{escape(cat)}">{cat_label}</span></td>
            <td>{rec_badge}</td>
        </tr>""")

    loc_labels = {"bengaluru": "Bengaluru", "remote": "Remote", "other_india": "Other India", "international": "International"}
    src_labels = {"linkedin": "LinkedIn", "employer": "Employer", "indeed": "Indeed", "shine": "Shine", "dice": "Dice", "glassdoor": "Glassdoor", "simplyhired": "SimplyHired"}

    # Build source filter chips dynamically from actual data
    src_chips = []
    for key in ["linkedin", "employer", "indeed", "shine", "dice", "glassdoor", "simplyhired"]:
        if src_counts.get(key, 0) > 0:
            label = src_labels.get(key, key.title())
            src_chips.append(f'<button class="chip" onclick="setFilter(\'src\',\'{key}\')">{label}<span class="cc">({src_counts[key]})</span></button>')

    loc_chips = []
    for key in ["bengaluru", "remote", "other_india", "international"]:
        if loc_counts.get(key, 0) > 0:
            label = loc_labels.get(key, key.title())
            loc_chips.append(f'<button class="chip" onclick="setFilter(\'loc\',\'{key}\')">{label}<span class="cc">({loc_counts[key]})</span></button>')

    cat_chips = []
    for key, label in [("gcc", "GCC / Product"), ("services", "Consulting / SI"), ("global", "Remote / Global")]:
        if cat_counts.get(key, 0) > 0:
            cat_chips.append(f'<button class="chip" onclick="setFilter(\'cat\',\'{key}\')">{label}<span class="cc">({cat_counts[key]})</span></button>')

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Pega Jobs Report — {date.today().isoformat()}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#09090b;color:#e4e4e7;padding:24px;max-width:1400px;margin:0 auto}}
h1{{font-size:2rem;font-weight:900;margin-bottom:4px}}
h1 span{{background:linear-gradient(135deg,#a855f7,#6366f1);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.subtitle{{color:#71717a;margin-bottom:24px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:20px}}
.card{{background:#111113;border:1px solid #27272a;border-radius:12px;padding:16px}}
.card .num{{font-size:2rem;font-weight:800;background:linear-gradient(135deg,#6366f1,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.card .label{{font-size:.78rem;color:#71717a;margin-top:2px}}
.card .num.green{{background:linear-gradient(135deg,#22c55e,#4ade80);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.card .num.red{{background:linear-gradient(135deg,#ef4444,#f87171);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
h2{{font-size:1.1rem;font-weight:700;margin:20px 0 8px;padding-top:14px;border-top:1px solid #27272a}}
table{{width:100%;border-collapse:collapse;font-size:.84rem}}
th{{text-align:left;padding:8px 10px;color:#52525b;font-size:.72rem;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #27272a;position:sticky;top:0;background:#09090b;cursor:pointer}}
th:hover{{color:#a5b4fc}}
td{{padding:8px 10px;border-bottom:1px solid #141416}}
tr:hover td{{background:rgba(99,102,241,.04)}}
a{{color:#818cf8;text-decoration:none}}a:hover{{text-decoration:underline;color:#c4b5fd}}
.new{{background:rgba(34,197,94,.15);color:#4ade80;padding:2px 8px;border-radius:5px;font-size:.65rem;font-weight:700}}
.rec{{background:rgba(99,102,241,.15);color:#a5b4fc;padding:2px 8px;border-radius:5px;font-size:.65rem;font-weight:700}}
.stretch{{background:rgba(234,179,8,.12);color:#fbbf24;padding:2px 8px;border-radius:5px;font-size:.65rem;font-weight:700}}
.dup{{background:rgba(239,68,68,.12);color:#fca5a5;padding:2px 8px;border-radius:5px;font-size:.65rem;font-weight:700}}
.cat-badge{{padding:2px 8px;border-radius:5px;font-size:.65rem;font-weight:700}}
.cat-gcc{{background:rgba(34,197,94,.12);color:#86efac}}
.cat-services{{background:rgba(99,102,241,.12);color:#a5b4fc}}
.cat-global{{background:rgba(168,85,247,.12);color:#d8b4fe}}
.cat-unknown{{background:rgba(113,113,122,.12);color:#a1a1aa}}
.filter-bar{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:12px 0 14px;padding:12px 14px;background:#111113;border:1px solid #27272a;border-radius:10px}}
.filter-group{{display:flex;align-items:center;gap:5px;flex-wrap:wrap}}
.filter-label{{font-size:.68rem;color:#52525b;text-transform:uppercase;letter-spacing:.8px;font-weight:700;margin-right:2px}}
.chip{{padding:5px 12px;border-radius:6px;font-size:.75rem;font-weight:600;border:1px solid #27272a;background:transparent;color:#a1a1aa;cursor:pointer;transition:all .15s;white-space:nowrap}}
.chip:hover{{border-color:#6366f1;color:#c4b5fd}}
.chip.active{{background:#6366f1;border-color:#6366f1;color:#fff}}
.chip .cc{{font-size:.65rem;opacity:.7;margin-left:3px}}
.filter-sep{{width:1px;height:20px;background:#27272a;margin:0 4px}}
.filter-count{{font-size:.82rem;color:#a1a1aa;margin:0 0 10px}}
.filter-count b{{color:#e4e4e7}}
.search-box{{flex:1;min-width:180px;max-width:320px}}
.search-box input{{width:100%;padding:7px 12px;border:1px solid #27272a;border-radius:6px;background:#09090b;color:#e4e4e7;font-size:.82rem;outline:none}}
.search-box input:focus{{border-color:#6366f1;box-shadow:0 0 0 2px rgba(99,102,241,.2)}}
.scrape-info{{font-size:.78rem;color:#52525b;margin-top:24px;padding:12px;border:1px solid #1e1e21;border-radius:8px}}
.footer{{text-align:center;color:#3f3f46;font-size:.72rem;margin-top:32px;padding-top:16px;border-top:1px solid #1e1e21}}
tr.hidden{{display:none}}
@media(max-width:800px){{.filter-sep{{display:none}}.cards{{grid-template-columns:repeat(3,1fr)}}}}
</style>
</head>
<body>

<h1>Pega Jobs <span>Daily Report</span></h1>
<p class="subtitle">{date.today().strftime('%A, %B %d, %Y')} | {profile.get('name','Sathvik')} | {profile.get('location','Bengaluru')} | Target: {profile.get('target_ctc_min',20)//100000}-{profile.get('goal_ctc',35)//100000} LPA</p>

<div class="cards">
    <div class="card"><div class="num">{total_jobs}</div><div class="label">Total unique jobs</div></div>
    <div class="card"><div class="num green">{new_jobs}</div><div class="label">New today</div></div>
    <div class="card"><div class="num">{recommended}</div><div class="label">Recommended</div></div>
    <div class="card"><div class="num">{review}</div><div class="label">Need verification</div></div>
    <div class="card"><div class="num">{companies_with_jobs}</div><div class="label">Companies</div></div>
    <div class="card"><div class="num red">{dupes}</div><div class="label">Duplicates removed</div></div>
</div>

<div class="filter-bar">
    <div class="filter-group">
        <span class="filter-label">Location</span>
        <button class="chip active" onclick="setFilter('loc','all')">All<span class="cc">({total_jobs})</span></button>
        {''.join(loc_chips)}
    </div>
    <div class="filter-sep"></div>
    <div class="filter-group">
        <span class="filter-label">Type</span>
        <button class="chip active" onclick="setFilter('cat','all')">All</button>
        {''.join(cat_chips)}
    </div>
    <div class="filter-sep"></div>
    <div class="filter-group">
        <span class="filter-label">Source</span>
        <button class="chip active" onclick="setFilter('src','all')">All</button>
        {''.join(src_chips)}
    </div>
    <div class="filter-sep"></div>
    <div class="search-box">
        <input type="text" id="searchInput" placeholder="Search company, role, or location..." oninput="applyFilters()">
    </div>
</div>
<p class="filter-count" id="filterCount">Showing <b>{total_jobs}</b> of {total_jobs} unique Pega jobs ({dupes} duplicates removed from {total_jobs + dupes} raw results)</p>

<table id="jobTable">
<tr>
    <th onclick="sortTable(0)">Role</th>
    <th onclick="sortTable(1)">Company</th>
    <th onclick="sortTable(2)">Location</th>
    <th onclick="sortTable(3)">Source</th>
    <th onclick="sortTable(4)">Type</th>
    <th onclick="sortTable(5)">Status</th>
</tr>
{''.join(job_rows)}
</table>

<div class="scrape-info">
    Sources: LinkedIn ({src_counts.get('linkedin',0)}) + Indeed ({src_counts.get('indeed',0)}) + Shine ({src_counts.get('shine',0)}) + Dice ({src_counts.get('dice',0)}) + Glassdoor ({src_counts.get('glassdoor',0)}) + SimplyHired ({src_counts.get('simplyhired',0)}) + Employer portals ({src_counts.get('employer',0)}) |
    Career portal scraping: {scrape.get('success',0)}/{scrape.get('total',0)} ({scrape.get('success_rate','?')}) |
    <a href="http://127.0.0.1:5050" target="_blank">Open full portal</a>
</div>

<div class="footer">
    Generated {data['generated_at']} | Pega Career Desk | {dupes} duplicates removed across all sources
</div>

<script>
const filters = {{loc:'all', cat:'all', src:'all'}};

function setFilter(key, value) {{
    filters[key] = value;
    const group = event.target.closest('.filter-group');
    group.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    event.target.classList.add('active');
    applyFilters();
}}

function applyFilters() {{
    const q = (document.getElementById('searchInput').value || '').toLowerCase();
    const rows = document.querySelectorAll('#jobTable .job-row');
    let visible = 0;

    // First pass: determine visibility
    rows.forEach(row => {{
        const show = (filters.loc === 'all' || row.dataset.loc === filters.loc)
            && (filters.cat === 'all' || row.dataset.cat === filters.cat)
            && (filters.src === 'all' || row.dataset.src === filters.src)
            && (!q || row.textContent.toLowerCase().includes(q));
        row.classList.toggle('hidden', !show);
        if (show) visible++;
    }});

    // Second pass: count what's visible per filter dimension
    // For each filter group, count how many visible rows match each value
    // (applying the OTHER active filters but not the one being counted)
    const dims = ['loc', 'cat', 'src'];
    dims.forEach(dim => {{
        const counts = {{}};
        let allCount = 0;
        rows.forEach(row => {{
            // Check all filters EXCEPT this dimension
            const otherMatch = dims.every(d => {{
                if (d === dim) return true;
                return filters[d] === 'all' || row.dataset[d] === filters[d];
            }}) && (!q || row.textContent.toLowerCase().includes(q));
            if (!otherMatch) return;
            const val = row.dataset[dim];
            counts[val] = (counts[val] || 0) + 1;
            allCount++;
        }});
        // Update chip counts
        document.querySelectorAll('.chip[onclick*="\\'' + dim + '\\'"]').forEach(chip => {{
            const cc = chip.querySelector('.cc');
            if (!cc) return;
            // Extract the second argument: setFilter('loc','bengaluru') -> 'bengaluru'
            const parts = chip.getAttribute('onclick').match(/,\\s*'([^']+)'/);
            if (!parts) {{
                // "All" button: setFilter('loc','all') — also matched above, but try first-arg pattern
                const allMatch = chip.getAttribute('onclick').match(/'all'/);
                if (allMatch) cc.textContent = '(' + allCount + ')';
                return;
            }}
            const chipVal = parts[1];
            if (chipVal === 'all') {{ cc.textContent = '(' + allCount + ')'; return; }}
            cc.textContent = '(' + (counts[chipVal] || 0) + ')';
        }});
    }});

    document.getElementById('filterCount').innerHTML = 'Showing <b>' + visible + '</b> of ' + rows.length + ' unique Pega jobs';
}}

let sortDir = {{}};
function sortTable(col) {{
    const table = document.getElementById('jobTable');
    const rows = Array.from(table.querySelectorAll('.job-row'));
    sortDir[col] = !sortDir[col];
    rows.sort((a, b) => {{
        const av = a.cells[col].textContent.trim().toLowerCase();
        const bv = b.cells[col].textContent.trim().toLowerCase();
        return sortDir[col] ? av.localeCompare(bv) : bv.localeCompare(av);
    }});
    rows.forEach(r => table.appendChild(r));
}}
</script>

</body>
</html>"""

    Path(output_path).write_text(html, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    os.chdir(str(BASE))
    path = build_report()
    print(f"Report saved to: {path}")
