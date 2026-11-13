"""
Pega Job Hunter Portal
=======================
A sleek dark-themed web portal that lets you trigger job scans from the browser
and view results in real time.

Usage:
    python pega_job_portal.py          # Starts on http://localhost:5050
    python pega_job_portal.py --port 8080
"""

import json
import threading
import argparse
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request, send_from_directory

# Import scanner components from the existing job hunter
import pega_job_hunter
from pega_job_hunter import (
    COMPANIES,
    CONSULTING_COMPANIES,
    REMOTE_GLOBAL_COMPANIES,
    HISTORY_FILE,
    REPORTS_DIR,
    Job,
    JobHistory,
    generate_search_links,
    scan_company,
    log,
)

app = Flask(__name__)

# Shared state for background scanning
scan_state = {
    "running": False,
    "progress": 0,
    "total": 0,
    "current_company": "",
    "results": {},       # company -> {jobs: [...], links: {...}}
    "last_scan": None,
    "scan_mode": None,
    "log_lines": [],
}
scan_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Background scanner
# ---------------------------------------------------------------------------
def run_scan(mode: str = "quick"):
    """Run a scan in the background, updating scan_state as it goes."""
    global scan_state
    with scan_lock:
        if scan_state["running"]:
            return
        scan_state["running"] = True
        scan_state["progress"] = 0
        scan_state["results"] = {}
        scan_state["log_lines"] = []
        scan_state["scan_mode"] = mode

    try:
        # Reset the broad LinkedIn cache so each scan is fresh
        pega_job_hunter._broad_linkedin_cache = {}

        history = JobHistory(HISTORY_FILE)
        REPORTS_DIR.mkdir(exist_ok=True)

        # Pick targets based on mode
        if mode == "gcc_top10":
            targets = [c for c in COMPANIES if c["priority"] == "top30"][:10]
        elif mode == "gcc_top20":
            targets = [c for c in COMPANIES if c["priority"] == "top30"]
        elif mode == "gcc_all":
            targets = COMPANIES
        elif mode == "si_top":
            targets = [c for c in CONSULTING_COMPANIES if c["priority"] == "si_top"]
        elif mode == "si_all":
            targets = CONSULTING_COMPANIES
        elif mode == "remote_top":
            targets = [c for c in REMOTE_GLOBAL_COMPANIES if c["priority"] == "remote_top"]
        elif mode == "remote_us":
            targets = [c for c in REMOTE_GLOBAL_COMPANIES if c.get("location", "") in ("United States", "Remote")]
        elif mode == "remote_all":
            targets = REMOTE_GLOBAL_COMPANIES
        elif mode == "all":
            targets = COMPANIES + CONSULTING_COMPANIES + REMOTE_GLOBAL_COMPANIES
        else:
            targets = [c for c in COMPANIES if c["priority"] == "top30"]

        scan_state["total"] = len(targets)
        scan_state["log_lines"].append(f"Starting {mode} scan: {len(targets)} companies")

        for idx, company in enumerate(targets, 1):
            scan_state["current_company"] = company["name"]
            scan_state["progress"] = idx
            scan_state["log_lines"].append(f"[{idx}/{len(targets)}] Scanning {company['name']}...")

            jobs, links = scan_company(company)

            # Mark new vs seen
            for job in jobs:
                if history.is_new(job.uid):
                    job.is_new = True
                    history.mark_seen(job.uid)

            scan_state["results"][company["name"]] = {
                "jobs": [j.to_dict() for j in jobs],
                "links": links,
                "new_count": sum(1 for j in jobs if j.is_new),
            }
            scan_state["log_lines"].append(
                f"  -> {company['name']}: {len(jobs)} jobs ({sum(1 for j in jobs if j.is_new)} new)"
            )

        history.save()
        scan_state["last_scan"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scan_state["log_lines"].append(f"Scan complete at {scan_state['last_scan']}")

    except Exception as exc:
        scan_state["log_lines"].append(f"ERROR: {exc}")
    finally:
        scan_state["running"] = False
        scan_state["current_company"] = ""


# ---------------------------------------------------------------------------
# Load previous results from history if available
# ---------------------------------------------------------------------------
def load_cached_results():
    """Load the last report data from disk if present."""
    # Check if there are any report files
    if REPORTS_DIR.exists():
        reports = sorted(REPORTS_DIR.glob("pega_jobs_*.html"), reverse=True)
        if reports:
            scan_state["last_scan"] = reports[0].stem.replace("pega_jobs_", "")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template_string(PORTAL_HTML)


@app.route("/api/scan", methods=["POST"])
def start_scan():
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "quick")
    if scan_state["running"]:
        return jsonify({"status": "already_running", "progress": scan_state["progress"], "total": scan_state["total"]})
    thread = threading.Thread(target=run_scan, args=(mode,), daemon=True)
    thread.start()
    return jsonify({"status": "started", "mode": mode})


@app.route("/api/status")
def get_status():
    total_jobs = sum(len(r["jobs"]) for r in scan_state["results"].values())
    new_jobs = sum(r["new_count"] for r in scan_state["results"].values())
    companies_with_jobs = sum(1 for r in scan_state["results"].values() if r["jobs"])
    return jsonify({
        "running": scan_state["running"],
        "progress": scan_state["progress"],
        "total": scan_state["total"],
        "current_company": scan_state["current_company"],
        "last_scan": scan_state["last_scan"],
        "scan_mode": scan_state["scan_mode"],
        "total_jobs": total_jobs,
        "new_jobs": new_jobs,
        "companies_with_jobs": companies_with_jobs,
        "companies_scanned": len(scan_state["results"]),
        "log_lines": scan_state["log_lines"][-20:],
    })


@app.route("/api/results")
def get_results():
    """Return all job results sorted by relevance."""
    # Sort: companies with NEW jobs first, then by total
    sorted_companies = sorted(
        scan_state["results"].items(),
        key=lambda x: (-x[1]["new_count"], -len(x[1]["jobs"])),
    )
    return jsonify({
        "companies": [
            {"name": name, **data} for name, data in sorted_companies
        ],
        "last_scan": scan_state["last_scan"],
    })


@app.route("/api/team-intelligence")
def get_team_intelligence():
    """Return the team intelligence data — enriched version with career timelines."""
    try:
        # Read enriched file with career data (227 members, 60 career timelines)
        fpath = r"C:\Users\DNSATHV\Desktop\calude\team_intelligence_enriched.json"
        import os
        if not os.path.isfile(fpath):
            fpath = r"C:\Users\DNSATHV\Desktop\calude\team_intelligence.json"
        with open(fpath, "rb") as fh:
            raw = fh.read()
        from flask import Response
        return Response(raw, status=200, content_type="application/json; charset=utf-8")
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/intel")
def team_intel_page():
    """Serve the integrated Intelligence + Dossiers page."""
    try:
        # Prefer the integrated Pega_Deep_Dossiers.html which combines both views
        dossier_path = Path(__file__).parent / "Pega_Deep_Dossiers.html"
        if dossier_path.exists():
            with open(dossier_path, "r", encoding="utf-8") as fh:
                return fh.read(), 200, {"Content-Type": "text/html; charset=utf-8"}
    except Exception:
        pass
    # Fallback to old template
    return render_template_string(TEAM_INTEL_HTML)


@app.route("/dossiers")
def deep_dossiers_page():
    """Serve the integrated Intelligence + Dossiers page (same as /intel)."""
    try:
        dossier_path = Path(__file__).parent / "Pega_Deep_Dossiers.html"
        if dossier_path.exists():
            with open(dossier_path, "r", encoding="utf-8") as fh:
                return fh.read(), 200, {"Content-Type": "text/html; charset=utf-8"}
        return "Deep Dossiers file not found", 404
    except Exception as exc:
        return f"Error loading dossiers: {exc}", 500


@app.route("/interview-masterclass")
def interview_masterclass_page():
    """Serve the personalized PEGA interview preparation masterclass."""
    try:
        masterclass_path = Path(__file__).parent / "Pega_Interview_Masterclass.html"
        if masterclass_path.exists():
            with open(masterclass_path, "r", encoding="utf-8") as fh:
                return fh.read(), 200, {"Content-Type": "text/html; charset=utf-8"}
        return "Interview Masterclass file not found", 404
    except Exception as exc:
        return f"Error loading interview masterclass: {exc}", 500


# ---------------------------------------------------------------------------
# Full-page HTML template (embedded)
# ---------------------------------------------------------------------------
PORTAL_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Pega Job Hunter</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
body{font-family:'Inter',system-ui,-apple-system,sans-serif;background:#09090b;color:#e4e4e7;min-height:100vh;overflow-x:hidden}
a{color:inherit;text-decoration:none}

/* ======== SCREEN 1: SCAN LAUNCHER (centered full-screen) ======== */
#scanScreen{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;padding:0;position:relative;transition:opacity .5s,transform .5s}
#scanScreen.hide{opacity:0;transform:scale(.97);pointer-events:none;position:absolute}
#scanScreen::before{content:'';position:fixed;inset:0;z-index:0;background-image:linear-gradient(rgba(255,255,255,.015) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.015) 1px,transparent 1px);background-size:64px 64px;pointer-events:none}
.launch-wrap{position:relative;z-index:1;text-align:center;max-width:560px;width:100%}
.launch-wrap h1{font-size:clamp(2.6rem,6vw,4.2rem);font-weight:900;line-height:1.06;letter-spacing:-.04em;margin-bottom:8px}
.launch-wrap h1 .g1{background:linear-gradient(135deg,#a855f7,#6366f1 60%,#818cf8);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.launch-wrap .tagline{color:#71717a;font-size:1.05rem;margin-bottom:36px;line-height:1.5}
.launch-wrap .tagline b{color:#a1a1aa}

/* card */
.scan-card{background:#111113;border:1px solid #27272a;border-radius:20px;padding:32px 36px;text-align:left}
.scan-card h2{font-size:1rem;font-weight:700;text-align:center;margin-bottom:2px}
.scan-card .sc-sub{text-align:center;color:#52525b;font-size:.8rem;margin-bottom:18px}

/* cat tabs */
.cat-tabs{display:flex;gap:0;margin-bottom:16px;border-radius:10px;overflow:hidden;border:1px solid #27272a}
.cat-tab{flex:1;padding:10px 0;text-align:center;font-size:.82rem;font-weight:700;cursor:pointer;background:transparent;color:#71717a;border:none;transition:all .15s}
.cat-tab.active{background:#6366f1;color:#fff}
.cat-tab:hover:not(.active){background:#18181b;color:#a5b4fc}

/* depth pills */
.depth-row{display:flex;gap:6px;justify-content:center;flex-wrap:wrap;margin-bottom:14px}
.dp{padding:7px 18px;border-radius:8px;font-size:.82rem;font-weight:600;border:1px solid #27272a;background:transparent;color:#a1a1aa;cursor:pointer;transition:all .15s}
.dp:hover{border-color:#6366f1;color:#c4b5fd}
.dp.active{background:#6366f1;border-color:#6366f1;color:#fff}

/* scan btn */
.btn-scan{display:block;width:100%;padding:14px 0;border:none;border-radius:12px;font-size:.95rem;font-weight:700;cursor:pointer;margin-top:16px;background:linear-gradient(135deg,#6366f1,#7c3aed);color:#fff;transition:all .2s;letter-spacing:.01em}
.btn-scan:hover{transform:translateY(-2px);box-shadow:0 10px 40px rgba(99,102,241,.4)}
.btn-scan:disabled{opacity:.55;cursor:not-allowed;transform:none;box-shadow:none}

/* progress */
.prog-area{margin-top:18px;display:none}
.prog-area.show{display:block}
.prog-bar{height:5px;border-radius:3px;background:#27272a;overflow:hidden}
.prog-bar .fill{height:100%;border-radius:3px;background:linear-gradient(90deg,#6366f1,#a855f7);transition:width .4s}
.prog-txt{font-size:.78rem;color:#71717a;margin-top:5px;text-align:center}

/* live log inside scan screen */
.scan-log{margin-top:14px;background:#0a0a0b;border:1px solid #1e1e21;border-radius:10px;padding:10px 14px;font-family:'Cascadia Code','Fira Code',monospace;font-size:.72rem;color:#52525b;max-height:140px;overflow-y:auto;display:none}
.scan-log.show{display:block}
.scan-log .ln{padding:1px 0}
.scan-log .ln.cur{color:#a855f7}

.scan-note{text-align:center;color:#3f3f46;font-size:.72rem;margin-top:14px}
.scan-note span{color:#a855f7}

/* ======== SCREEN 2: RESULTS DASHBOARD (full-width) ======== */
#resultScreen{display:none;min-height:100vh}
#resultScreen.show{display:block}

/* top bar */
.topbar{position:sticky;top:0;z-index:20;background:rgba(9,9,11,.92);backdrop-filter:blur(14px);border-bottom:1px solid #1e1e21;padding:10px 24px;display:flex;align-items:center;gap:16px}
.topbar .brand{font-size:.95rem;font-weight:800;letter-spacing:-.02em;white-space:nowrap}
.topbar .brand .g1{background:linear-gradient(135deg,#a855f7,#6366f1);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.topbar .search-box{flex:1;max-width:400px;position:relative}
.topbar .search-box input{width:100%;padding:8px 12px 8px 34px;border:1px solid #27272a;border-radius:8px;background:#111113;color:#e4e4e7;font-size:.82rem;outline:none}
.topbar .search-box input:focus{border-color:#6366f1;box-shadow:0 0 0 2px rgba(99,102,241,.2)}
.topbar .search-box .ico{position:absolute;left:10px;top:7px;color:#52525b;font-size:.9rem}
.topbar .stat-pills{display:flex;gap:10px;margin-left:auto;align-items:center}
.topbar .sp{display:flex;align-items:center;gap:5px;font-size:.78rem;color:#71717a}
.topbar .sp b{font-size:1rem;font-weight:800}
.topbar .sp b.green{color:#4ade80}
.topbar .sp b.purple{background:linear-gradient(135deg,#6366f1,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.btn-new-scan{padding:7px 18px;border-radius:8px;font-size:.78rem;font-weight:700;border:1px solid #27272a;background:transparent;color:#a1a1aa;cursor:pointer;transition:all .15s;margin-left:8px}
.btn-new-scan:hover{border-color:#6366f1;color:#c4b5fd;background:#111}

/* body grid */
.dash-body{display:flex;height:calc(100vh - 52px)}
.sidebar-r{width:220px;border-right:1px solid #1e1e21;overflow-y:auto;padding:12px 0;flex-shrink:0;background:#0c0c0e}
.sidebar-r .sh{font-size:.65rem;color:#52525b;text-transform:uppercase;letter-spacing:1px;font-weight:700;padding:10px 14px 4px}
.sidebar-r .ci{display:flex;align-items:center;gap:8px;padding:7px 14px;cursor:pointer;font-size:.8rem;color:#a1a1aa;transition:all .1s;border-left:3px solid transparent}
.sidebar-r .ci:hover{background:#111113;color:#e4e4e7}
.sidebar-r .ci.active{background:#111113;color:#fff;border-left-color:#6366f1}
.sidebar-r .ci .cnt{margin-left:auto;font-size:.7rem;background:rgba(99,102,241,.15);color:#818cf8;padding:1px 7px;border-radius:10px;font-weight:700}
.sidebar-r .ci .cnt.new{background:rgba(34,197,94,.15);color:#4ade80}
.sidebar-r .ci .dot{width:6px;height:6px;border-radius:50%;background:#22c55e;flex-shrink:0}
.sidebar-r .no-jobs{color:#3f3f46;font-size:.72rem;padding:3px 14px}

/* main content */
.main-content{flex:1;overflow-y:auto;padding:20px 28px}
.mc-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;gap:12px;flex-wrap:wrap}
.mc-header h2{font-size:1.2rem;font-weight:800}
.mc-header .links{display:flex;gap:6px;flex-wrap:wrap}
.mc-header .links a{font-size:.72rem;padding:4px 12px;border:1px solid #27272a;border-radius:20px;color:#71717a;transition:all .15s}
.mc-header .links a:hover{border-color:#6366f1;color:#c4b5fd}

/* job table */
.jtbl{width:100%;border-collapse:collapse;font-size:.84rem}
.jtbl th{text-align:left;padding:8px 12px;color:#52525b;font-weight:600;font-size:.72rem;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #1e1e21;position:sticky;top:0;background:#09090b}
.jtbl td{padding:9px 12px;border-bottom:1px solid #141416;vertical-align:middle}
.jtbl tr:hover td{background:rgba(99,102,241,.03)}
.jtbl .new-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#22c55e;margin-right:6px;box-shadow:0 0 6px rgba(34,197,94,.5)}
.jtbl .jl{color:#818cf8;transition:color .15s}
.jtbl .jl:hover{color:#c4b5fd;text-decoration:underline}
.src-pill{display:inline-block;padding:2px 8px;border-radius:5px;font-size:.65rem;font-weight:600}
.src-pill.linkedin{background:rgba(10,102,194,.2);color:#60a5fa}
.src-pill.naukri{background:rgba(99,102,241,.15);color:#a5b4fc}
.src-pill.indeed{background:rgba(139,92,246,.15);color:#c4b5fd}
.src-pill.google{background:rgba(234,179,8,.12);color:#fbbf24}
.badge-new{background:rgba(34,197,94,.15);color:#4ade80;padding:2px 8px;border-radius:6px;font-size:.65rem;font-weight:700}
.empty-state{text-align:center;padding:80px 20px;color:#3f3f46;font-size:.9rem}
.empty-state .big{font-size:2.5rem;margin-bottom:8px}

/* all-jobs view */
.view-tabs{display:flex;gap:0;margin-bottom:16px;border-radius:8px;overflow:hidden;border:1px solid #27272a;width:fit-content}
.vt{padding:7px 18px;font-size:.78rem;font-weight:600;cursor:pointer;background:transparent;color:#71717a;border:none;transition:all .15s}
.vt.active{background:#6366f1;color:#fff}
.vt:hover:not(.active){background:#18181b;color:#a5b4fc}

/* no-results sidebar section */
.sidebar-r .divider{height:1px;background:#1e1e21;margin:8px 14px}

@media(max-width:900px){.dash-body{flex-direction:column}.sidebar-r{width:100%;max-height:180px;border-right:none;border-bottom:1px solid #1e1e21}.main-content{padding:14px 16px}.topbar .stat-pills{display:none}}
@media(max-width:600px){.launch-wrap h1{font-size:2.2rem}.scan-card{padding:22px 20px}.topbar{padding:8px 12px;gap:8px}}

@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
.scanning{animation:pulse 1.5s ease-in-out infinite}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.fade-in{animation:fadeIn .3s ease forwards}
</style>
</head>
<body>

<!-- ==================== SCREEN 1: SCAN + INTEL TABS ==================== -->
<div id="scanScreen">
  <!-- TOP TAB BAR -->
  <div style="position:sticky;top:0;z-index:15;background:rgba(9,9,11,.94);backdrop-filter:blur(14px);border-bottom:1px solid #1e1e21;padding:10px 24px;display:flex;align-items:center;gap:16px">
    <div class="brand" style="font-size:.95rem;font-weight:900;letter-spacing:-.02em">Pega <span class="g1">Hub</span></div>
    <div style="display:flex;border-radius:8px;overflow:hidden;border:1px solid #27272a">
      <button id="tabScan" class="cat-tab active" onclick="switchMainTab('scan')" style="padding:8px 22px;font-size:.82rem;font-weight:700;cursor:pointer;border:none;transition:.15s">Job Scanner</button>
      <button id="tabIntel" class="cat-tab" onclick="switchMainTab('intel')" style="padding:8px 22px;font-size:.82rem;font-weight:700;cursor:pointer;border:none;transition:.15s">Team Intelligence</button>
      <a href="/interview-masterclass" class="cat-tab" style="padding:8px 22px;font-size:.82rem;font-weight:700;cursor:pointer;border:none;transition:.15s;color:#fbbf24">Interview Masterclass</a>
    </div>
    <!-- Search for intel tab -->
    <div id="intelSearchWrap" style="display:none;flex:1;max-width:420px;position:relative">
      <span style="position:absolute;left:10px;top:7px;color:#52525b;font-size:.9rem">&#x2315;</span>
      <input id="intelSearch" placeholder="Search companies, people, tech, certs..." oninput="applyIntelSearch()" style="width:100%;padding:8px 12px 8px 34px;border:1px solid #27272a;border-radius:8px;background:#111113;color:#e4e4e7;font-size:.82rem;outline:none">
    </div>
    <div id="intelPills" style="display:none;margin-left:auto;font-size:.78rem;color:#71717a">
      <b style="background:linear-gradient(135deg,#6366f1,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent" id="sCo2">98</b> companies &nbsp;
      <b style="color:#4ade80" id="sPpl2">227+</b> people
    </div>
  </div>

  <!-- TAB 1: JOB SCANNER -->
  <div id="scanTab" style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:calc(100vh - 52px);padding:32px">
    <div class="launch-wrap">
      <h1>Pega jobs,<br><span class="g1">made visible.</span></h1>
      <div class="tagline">Scan <b>295 companies</b> across Naukri, LinkedIn, Indeed, Google &amp; <b>Company Career Portals</b> — India, US, UK, EU, AU, Brazil &amp; Remote.</div>
      <div class="scan-card">
        <h2>Launch a scan</h2>
        <div class="sc-sub">Pick a category and depth</div>
        <div class="cat-tabs">
          <button class="cat-tab active" data-cat="gcc">GCC / Product</button>
          <button class="cat-tab" data-cat="si">Consulting / SI</button>
          <button class="cat-tab" data-cat="remote">Remote / Global</button>
          <button class="cat-tab" data-cat="all">All</button>
        </div>
        <div class="depth-row" id="depthRow">
          <button class="dp active" data-mode="gcc_top10">Top 10</button>
          <button class="dp" data-mode="gcc_top20">Top 20</button>
          <button class="dp" data-mode="gcc_all">All 90+</button>
        </div>
        <button class="btn-scan" id="scanBtn" onclick="startScan()">Start scanning &rarr;</button>
        <div class="prog-area" id="progArea">
          <div class="prog-bar"><div class="fill" id="progFill" style="width:0%"></div></div>
          <div class="prog-txt" id="progTxt">Preparing...</div>
        </div>
        <div class="scan-log" id="scanLog"></div>
      </div>
      <div class="scan-note"><span>&#9679;</span> Targets Pega roles in India, US, UK &amp; Remote — generic titles included</div>
    </div>
  </div>

  <!-- TAB 2: TEAM INTELLIGENCE & DOSSIERS -->
  <div id="intelTab" style="display:none;height:calc(100vh - 52px);overflow-y:auto">
    <div id="intelContent" style="max-width:1400px;margin:0 auto;padding:20px 24px">
      <div style="text-align:center;padding:60px;color:#52525b;font-size:.9rem">Loading team intelligence...</div>
    </div>
  </div>
</div>

<!-- ==================== SCREEN 2: RESULTS ==================== -->
<div id="resultScreen">
  <div class="topbar">
    <div class="brand">Pega <span class="g1">Hunter</span></div>
    <div style="display:flex;gap:0;border-radius:8px;overflow:hidden;border:1px solid #27272a;margin-left:8px">
      <span style="padding:7px 18px;font-size:.78rem;font-weight:600;background:#6366f1;color:#fff">Job Scanner</span>
      <a href="/intel" style="padding:7px 18px;font-size:.78rem;font-weight:600;color:#a5b4fc;transition:all .15s;text-decoration:none" onmouseover="this.style.background='#18181b';this.style.color='#c4b5fd'" onmouseout="this.style.background='';this.style.color='#a5b4fc'">Intelligence &amp; Dossiers</a>
      <a href="/interview-masterclass" style="padding:7px 18px;font-size:.78rem;font-weight:600;color:#fbbf24;transition:all .15s;text-decoration:none" onmouseover="this.style.background='#18181b';this.style.color='#fde68a'" onmouseout="this.style.background='';this.style.color='#fbbf24'">Interview Masterclass</a>
    </div>
    <div class="search-box">
      <span class="ico">&#x2315;</span>
      <input id="filterInput" placeholder="Filter companies or jobs..." oninput="applyFilter()">
    </div>
    <div class="stat-pills">
      <div class="sp"><b class="green" id="rNew">0</b> new</div>
      <div class="sp"><b class="purple" id="rTotal">0</b> jobs</div>
      <div class="sp"><b class="purple" id="rCo">0</b> companies</div>
    </div>
    <button class="btn-new-scan" onclick="goBack()">New scan</button>
  </div>

  <div class="dash-body">
    <div class="sidebar-r" id="sidebar">
      <!-- filled by JS -->
    </div>
    <div class="main-content" id="mainContent">
      <div class="empty-state" id="emptyState">
        <div class="big">&#x1F50D;</div>
        Select a company from the sidebar
      </div>
    </div>
  </div>
</div>

<script>
let selectedCat='gcc',selectedMode='gcc_top10',pollTimer=null;
let allResults=[];

const depthConfigs={
  gcc:[{mode:'gcc_top10',label:'Top 10'},{mode:'gcc_top20',label:'Top 20'},{mode:'gcc_all',label:'All 90+'}],
  si:[{mode:'si_top',label:'Top 12 (Elite + Big 4)'},{mode:'si_all',label:'All 57'}],
  remote:[{mode:'remote_top',label:'Top 27 (Verified)'},{mode:'remote_us',label:'US + Remote (40)'},{mode:'remote_all',label:'All 91 Global'}],
  all:[{mode:'all',label:'All 295 companies'}]
};

document.querySelectorAll('.cat-tab').forEach(t=>{
  t.addEventListener('click',()=>{
    document.querySelectorAll('.cat-tab').forEach(x=>x.classList.remove('active'));
    t.classList.add('active');
    selectedCat=t.dataset.cat;
    renderDepth();
  });
});

function renderDepth(){
  const row=document.getElementById('depthRow'),cfg=depthConfigs[selectedCat];
  row.innerHTML=cfg.map((d,i)=>`<button class="dp ${i===0?'active':''}" data-mode="${d.mode}">${d.label}</button>`).join('');
  selectedMode=cfg[0].mode;
  row.querySelectorAll('.dp').forEach(b=>{
    b.addEventListener('click',()=>{
      row.querySelectorAll('.dp').forEach(x=>x.classList.remove('active'));
      b.classList.add('active');
      selectedMode=b.dataset.mode;
    });
  });
}

async function startScan(){
  const btn=document.getElementById('scanBtn');
  btn.disabled=true;btn.innerHTML='<span class="scanning">Scanning...</span>';
  document.getElementById('progArea').classList.add('show');
  document.getElementById('scanLog').classList.add('show');
  document.getElementById('scanLog').innerHTML='';
  try{
    await fetch('/api/scan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:selectedMode})});
    startPolling();
  }catch(e){btn.disabled=false;btn.innerHTML='Start scanning &rarr;';}
}

function startPolling(){if(pollTimer)clearInterval(pollTimer);pollTimer=setInterval(pollStatus,800);}

async function pollStatus(){
  try{
    const r=await fetch('/api/status'),s=await r.json();
    const pct=s.total>0?Math.round(s.progress/s.total*100):0;
    document.getElementById('progFill').style.width=pct+'%';
    document.getElementById('progTxt').textContent=s.running?`Scanning ${s.current_company}... (${s.progress}/${s.total})`:'Scan complete!';

    const log=document.getElementById('scanLog');
    log.innerHTML=s.log_lines.map((l,i)=>`<div class="ln ${i===s.log_lines.length-1&&s.running?'cur':''}">${l}</div>`).join('');
    log.scrollTop=log.scrollHeight;

    if(!s.running&&s.companies_scanned>0){
      clearInterval(pollTimer);pollTimer=null;
      setTimeout(()=>switchToResults(s),600);
    }
  }catch(e){}
}

async function switchToResults(stats){
  try{
    const r=await fetch('/api/results'),d=await r.json();
    allResults=d.companies;
    document.getElementById('rNew').textContent=stats.new_jobs;
    document.getElementById('rTotal').textContent=stats.total_jobs;
    document.getElementById('rCo').textContent=stats.companies_with_jobs;
    renderSidebar(allResults);
    document.getElementById('scanScreen').classList.add('hide');
    document.getElementById('resultScreen').classList.add('show');
    // auto-select first with jobs
    const first=allResults.find(c=>c.jobs.length>0);
    if(first)showCompany(first.name);
    else showAll();
  }catch(e){}
}

function goBack(){
  document.getElementById('resultScreen').classList.remove('show');
  document.getElementById('scanScreen').classList.remove('hide');
  const btn=document.getElementById('scanBtn');
  btn.disabled=false;btn.innerHTML='Start scanning &rarr;';
  document.getElementById('progArea').classList.remove('show');
  document.getElementById('scanLog').classList.remove('show');
}

function renderSidebar(companies){
  const sb=document.getElementById('sidebar');
  const withJobs=companies.filter(c=>c.jobs.length>0).sort((a,b)=>b.new_count-a.new_count||b.jobs.length-a.jobs.length);
  const noJobs=companies.filter(c=>c.jobs.length===0);

  let html='<div class="ci" onclick="showAll()" style="font-weight:700;color:#a5b4fc"><span>All jobs</span><span class="cnt" style="background:rgba(99,102,241,.25)">'+companies.reduce((s,c)=>s+c.jobs.length,0)+'</span></div>';
  html+='<div class="sh">With openings ('+withJobs.length+')</div>';
  withJobs.forEach(c=>{
    html+='<div class="ci" data-co="'+c.name+'" onclick="showCompany(\''+c.name.replace(/'/g,"\\'")+'\')">';
    if(c.new_count>0)html+='<span class="dot"></span>';
    html+='<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+c.name+'</span>';
    if(c.new_count>0)html+='<span class="cnt new">'+c.new_count+'</span>';
    else html+='<span class="cnt">'+c.jobs.length+'</span>';
    html+='</div>';
  });
  if(noJobs.length>0){
    html+='<div class="divider"></div><div class="sh">No openings ('+noJobs.length+')</div>';
    noJobs.forEach(c=>{
      html+='<div class="no-jobs" title="'+c.name+'">'+c.name+'</div>';
    });
  }
  sb.innerHTML=html;
}

function showCompany(name){
  // highlight sidebar
  document.querySelectorAll('.sidebar-r .ci').forEach(el=>{
    el.classList.toggle('active',el.dataset.co===name);
  });
  const co=allResults.find(c=>c.name===name);
  if(!co)return;
  const mc=document.getElementById('mainContent');
  let html='<div class="mc-header fade-in"><h2>'+co.name+(co.new_count>0?' <span class="badge-new">'+co.new_count+' NEW</span>':'')+'</h2>';
  html+='<div class="links">';
  for(const [src,url] of Object.entries(co.links)){html+='<a href="'+url+'" target="_blank">'+src+' &nearr;</a>';}
  html+='</div></div>';

  if(co.jobs.length===0){
    html+='<div class="empty-state fade-in"><div class="big">&#128566;</div>No Pega openings found at '+co.name+'.<br>Try the quick links above to search manually.</div>';
  }else{
    html+='<table class="jtbl fade-in"><thead><tr><th></th><th>Title</th><th>Company</th><th>Location</th><th>Source</th></tr></thead><tbody>';
    co.jobs.forEach(j=>{
      const sc=j.source.toLowerCase();
      html+='<tr><td>'+(j.is_new?'<span class="new-dot"></span>':'')+'</td>';
      html+='<td><a class="jl" href="'+j.url+'" target="_blank">'+j.title+'</a></td>';
      html+='<td>'+j.company+'</td><td>'+j.location+'</td>';
      html+='<td><span class="src-pill '+sc+'">'+j.source+'</span></td></tr>';
    });
    html+='</tbody></table>';
  }
  mc.innerHTML=html;
  document.getElementById('emptyState')?.remove();
}

function showAll(){
  document.querySelectorAll('.sidebar-r .ci').forEach(el=>el.classList.remove('active'));
  const mc=document.getElementById('mainContent');
  const allJobs=[];
  allResults.forEach(co=>{
    co.jobs.forEach(j=>{allJobs.push({...j,coName:co.name});});
  });
  allJobs.sort((a,b)=>(b.is_new?1:0)-(a.is_new?1:0));

  let html='<div class="mc-header fade-in"><h2>All jobs ('+allJobs.length+')</h2></div>';
  html+='<table class="jtbl fade-in"><thead><tr><th></th><th>Title</th><th>Company</th><th>Location</th><th>Source</th></tr></thead><tbody>';
  allJobs.forEach(j=>{
    const sc=j.source.toLowerCase();
    html+='<tr><td>'+(j.is_new?'<span class="new-dot"></span>':'')+'</td>';
    html+='<td><a class="jl" href="'+j.url+'" target="_blank">'+j.title+'</a></td>';
    html+='<td>'+j.coName+'</td><td>'+j.location+'</td>';
    html+='<td><span class="src-pill '+sc+'">'+j.source+'</span></td></tr>';
  });
  html+='</tbody></table>';
  mc.innerHTML=html;
}

function applyFilter(){
  const q=document.getElementById('filterInput').value.toLowerCase();
  if(!q){renderSidebar(allResults);return;}
  const filtered=allResults.map(c=>({
    ...c,
    jobs:c.jobs.filter(j=>j.title.toLowerCase().includes(q)||j.company.toLowerCase().includes(q)||j.location.toLowerCase().includes(q)),
    _nameMatch:c.name.toLowerCase().includes(q)
  })).filter(c=>c.jobs.length>0||c._nameMatch);
  renderSidebar(filtered);
  // also filter main if showing all
  const mc=document.getElementById('mainContent');
  if(mc.querySelector('.jtbl')){
    mc.querySelectorAll('.jtbl tbody tr').forEach(tr=>{
      const txt=tr.textContent.toLowerCase();
      tr.style.display=txt.includes(q)?'':'none';
    });
  }
}

// ===================== INTEL & DOSSIERS TAB =====================
let intelData=null, intelSector='all', intelActive=null;

function switchMainTab(tab){
  const scanTab=document.getElementById('scanTab');
  const intelTabEl=document.getElementById('intelTab');
  const tabScan=document.getElementById('tabScan');
  const tabIntel=document.getElementById('tabIntel');
  const searchWrap=document.getElementById('intelSearchWrap');
  const pills=document.getElementById('intelPills');
  if(tab==='scan'){
    scanTab.style.display='flex';intelTabEl.style.display='none';
    tabScan.classList.add('active');tabIntel.classList.remove('active');
    searchWrap.style.display='none';pills.style.display='none';
  } else {
    scanTab.style.display='none';intelTabEl.style.display='block';
    tabScan.classList.remove('active');tabIntel.classList.add('active');
    searchWrap.style.display='block';pills.style.display='block';
    if(!intelData)loadIntel();
  }
}
function applyIntelSearch(){renderIntelDashboard();}

async function loadIntel(){
  try{
    const r=await fetch('/api/team-intelligence');
    const d=await r.json();
    if(d.error){document.getElementById('intelContent').innerHTML='<div style="text-align:center;padding:40px;color:#f87171">'+d.error+'</div>';return;}
    intelData=d.companies||[];
    renderIntelDashboard();
  }catch(e){document.getElementById('intelContent').innerHTML='<div style="text-align:center;padding:40px;color:#f87171">Failed to load</div>';}
}

function getSbClass(sg){const m={'Banking & Finance':'bk','Insurance & Healthcare':'in','Telecom':'te','Auto & Industrial':'au','Technology':'tc','Payments':'bk','Consumer & Retail':'co','Logistics & Energy':'lo'};return m[sg]||'bk';}
function getHsClass(s){s=s.toLowerCase();if(s.includes('rapidly')||s.includes('actively'))return 'hs-h';if(s.includes('growing'))return 'hs-g';if(s.includes('declining'))return 'hs-d';return 'hs-s';}
function iGetCerts(m){if(m.certs&&typeof m.certs==='string')return m.certs.split(',').map(c=>c.trim()).filter(c=>c);if(m.certifications&&Array.isArray(m.certifications))return m.certifications.filter(c=>c);return[];}
function iIsTop(c){const u=c.toUpperCase();return u.includes('CLSA')||u.includes('LSA')||u.includes('PSA');}

function getSectorGroup(s){
  s=(s||'').toLowerCase();
  if(s.includes('bank')||s.includes('financial'))return 'Banking & Finance';
  if(s.includes('insur')||s.includes('health')||s.includes('pharma'))return 'Insurance & Healthcare';
  if(s.includes('telecom')||s.includes('media'))return 'Telecom';
  if(s.includes('auto')||s.includes('manufact')||s.includes('industrial'))return 'Auto & Industrial';
  if(s.includes('tech')||s.includes('semi')||s.includes('platform'))return 'Technology';
  if(s.includes('payment')||s.includes('fintech'))return 'Payments';
  if(s.includes('retail')||s.includes('fmcg')||s.includes('consumer')||s.includes('travel')||s.includes('fashion'))return 'Consumer & Retail';
  if(s.includes('logist')||s.includes('energy')||s.includes('business'))return 'Logistics & Energy';
  return 'Other';
}

function getIntelFiltered(){
  const q=(document.getElementById('intelSearch')||{}).value||'';
  const ql=q.toLowerCase();
  let list=intelSector==='all'?intelData:intelData.filter(c=>getSectorGroup(c.sector)===intelSector);
  if(ql)list=list.filter(c=>{
    const blob=(c.name+' '+c.sector+' '+(c.locations||[]).join(' ')+' '+(c.tech_stack||[]).join(' ')+' '+(c.domains||[]).join(' ')+' '+c.projects+' '+c.hiring_status+' '+(c.highlights||[]).join(' ')+' '+(c.certifications_required||[]).join(' ')+' '+(c.team_members||[]).map(m=>m.name+' '+m.title+' '+iGetCerts(m).join(' ')).join(' ')).toLowerCase();
    return blob.includes(ql);
  });
  return list.sort((a,b)=>(parseInt(b.team_size)||0)-(parseInt(a.team_size)||0));
}

function renderIntelDashboard(){
  intelActive=null;
  const list=getIntelFiltered();
  const totalPpl=list.reduce((s,c)=>s+(c.team_members||[]).length,0);
  const gr=list.filter(c=>{const s=c.hiring_status.toLowerCase();return s.includes('growing')||s.includes('rapidly')||s.includes('actively');}).length;
  const sectors=[...new Set(intelData.map(c=>getSectorGroup(c.sector)))].filter(Boolean).sort();
  
  let h='<div style="padding:16px 20px">';
  // Sector filter pills
  h+='<div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:14px">';
  h+='<button onclick="intelSector=\'all\';renderIntelDashboard()" style="padding:4px 12px;border-radius:6px;font-size:.72rem;font-weight:600;border:1px solid '+(intelSector==='all'?'#6366f1':'#27272a')+';background:'+(intelSector==='all'?'#6366f1':'transparent')+';color:'+(intelSector==='all'?'#fff':'#71717a')+';cursor:pointer">All ('+intelData.length+')</button>';
  sectors.forEach(s=>{const n=intelData.filter(c=>getSectorGroup(c.sector)===s).length;h+='<button onclick="intelSector=\''+s.replace(/'/g,"\\'")+'\';renderIntelDashboard()" style="padding:4px 12px;border-radius:6px;font-size:.72rem;font-weight:600;border:1px solid '+(intelSector===s?'#6366f1':'#27272a')+';background:'+(intelSector===s?'#6366f1':'transparent')+';color:'+(intelSector===s?'#fff':'#71717a')+';cursor:pointer">'+s+' ('+n+')</button>';});
  h+='</div>';
  // Stat row
  h+='<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin-bottom:16px">';
  h+='<div style="background:#0c0c0e;border:1px solid #1e1e21;border-radius:8px;padding:10px;text-align:center"><div style="font-size:1.2rem;font-weight:900;background:linear-gradient(135deg,#6366f1,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent">'+list.length+'</div><div style="font-size:.6rem;color:#52525b;text-transform:uppercase;font-weight:600">Companies</div></div>';
  h+='<div style="background:#0c0c0e;border:1px solid #1e1e21;border-radius:8px;padding:10px;text-align:center"><div style="font-size:1.2rem;font-weight:900;color:#fbbf24">'+totalPpl+'</div><div style="font-size:.6rem;color:#52525b;text-transform:uppercase;font-weight:600">People Profiled</div></div>';
  h+='<div style="background:#0c0c0e;border:1px solid #1e1e21;border-radius:8px;padding:10px;text-align:center"><div style="font-size:1.2rem;font-weight:900;color:#4ade80">'+gr+'</div><div style="font-size:.6rem;color:#52525b;text-transform:uppercase;font-weight:600">Growing</div></div>';
  h+='</div>';
  // Company grid
  h+='<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:10px">';
  list.forEach(co=>{
    const mc=(co.team_members||[]).length;
    h+='<div onclick="openIntelCompany(\''+co.name.replace(/'/g,"\\'")+'\')" style="background:#0c0c0e;border:1px solid #1e1e21;border-radius:10px;padding:12px 14px;cursor:pointer;transition:all .15s" onmouseover="this.style.borderColor=\'#6366f1\';this.style.transform=\'translateY(-1px)\'" onmouseout="this.style.borderColor=\'#1e1e21\';this.style.transform=\'\'">';
    const hg=co._health_grade||'';const hs_=co._health_score||0;
    const gc={'A+':'#4ade80','A':'#86efac','B+':'#60a5fa','B':'#93c5fd','C+':'#fbbf24','C':'#f97316','D':'#f87171'};
    h+='<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px"><span style="font-size:.84rem;font-weight:800;color:#e4e4e7">'+co.name+(hg?' <span style="font-size:.6rem;font-weight:700;padding:1px 6px;border-radius:4px;background:rgba(0,0,0,.3);color:'+(gc[hg]||'#a1a1aa')+'">'+hg+'</span>':'')+'</span>';
    const sbC=getSbClass(getSectorGroup(co.sector));
    const colors={bk:'99,102,241',in:'168,85,247',te:'251,146,60',au:'56,189,248',tc:'45,212,191',co:'250,204,21',lo:'217,119,6'};
    const rgb=colors[sbC]||'99,102,241';
    h+='<span style="font-size:.64rem;padding:2px 8px;border-radius:10px;background:rgba('+rgb+',.12);color:rgba('+rgb+',1);font-weight:600">'+co.sector+'</span></div>';
    h+='<div style="font-size:.68rem;color:#52525b;margin-bottom:4px">'+(co.locations||[]).join(' / ')+(mc>0?' &bull; '+mc+' profiled':'')+'</div>';
    h+='<div style="font-size:.72rem;color:#71717a;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;margin-bottom:6px">'+co.projects+'</div>';
    // Tech pills
    if(co.tech_stack&&co.tech_stack.length>0){h+='<div style="margin-bottom:6px">';co.tech_stack.slice(0,4).forEach(t=>{h+='<span style="display:inline-block;font-size:.58rem;padding:1px 5px;border-radius:3px;background:rgba(99,102,241,.06);color:#818cf8;border:1px solid rgba(99,102,241,.12);margin:1px">'+t+'</span>';});if(co.tech_stack.length>4)h+='<span style="font-size:.58rem;color:#3f3f46;margin-left:2px">+'+(co.tech_stack.length-4)+'</span>';h+='</div>';}
    h+='<div style="display:flex;align-items:center;gap:6px"><span style="display:inline-flex;align-items:center;gap:3px;font-size:.68rem;font-weight:700;padding:2px 6px;border-radius:4px;background:rgba('+(co.hiring_status.toLowerCase().includes('growing')||co.hiring_status.toLowerCase().includes('rapidly')?'34,197,94':'250,204,21')+',.12);color:'+(co.hiring_status.toLowerCase().includes('growing')||co.hiring_status.toLowerCase().includes('rapidly')?'#4ade80':'#fbbf24')+'"><span style="width:4px;height:4px;border-radius:50%;background:currentColor"></span>'+co.hiring_status+'</span>';
    h+='<span style="font-size:.66rem;color:#a1a1aa;font-weight:700;margin-left:auto">~'+co.team_size+'</span></div></div>';
  });
  h+='</div></div>';
  document.getElementById('intelContent').innerHTML=h;
}

function openIntelCompany(name){
  const co=intelData.find(c=>c.name===name);
  if(!co)return;
  intelActive=co;
  const tm=co.team_members||[];
  let h='<div style="padding:16px 20px">';
  h+='<button onclick="renderIntelDashboard()" style="display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:6px;border:1px solid #27272a;background:#0c0c0e;color:#a1a1aa;font-size:.78rem;cursor:pointer;margin-bottom:14px">&#x2190; Back to all</button>';
  h+='<h2 style="font-size:1.3rem;font-weight:900;color:#fff;margin-bottom:6px">'+co.name+'</h2>';
  h+='<div style="display:flex;gap:12px;flex-wrap:wrap;color:#71717a;font-size:.78rem;margin-bottom:14px">';
  h+='<span>&#x1F4CD; '+(co.locations||[]).join(', ')+'</span><span>&#x1F465; ~'+co.team_size+'</span>';
  h+='<span style="display:inline-flex;align-items:center;gap:3px;font-weight:700;padding:2px 6px;border-radius:4px;background:rgba(34,197,94,.12);color:#4ade80;font-size:.72rem"><span style="width:4px;height:4px;border-radius:50%;background:currentColor"></span>'+co.hiring_status+'</span>';
  if(co.maturity)h+='<span>'+co.maturity+' Maturity</span>';
  const dhg=co._health_grade||'';const dhs=co._health_score||0;const dhl=co._health_label||'';
  const dgc={'A+':'#4ade80','A':'#86efac','B+':'#60a5fa','B':'#93c5fd','C+':'#fbbf24','C':'#f97316','D':'#f87171'};
  if(dhg)h+='<span style="font-weight:700;padding:2px 8px;border-radius:4px;background:rgba(0,0,0,.3);color:'+(dgc[dhg]||'#a1a1aa')+'">Team Health: '+dhg+' ('+dhs+'/100) '+dhl+'</span>';
  h+='</div>';
  // Stats
  const dm=co._health_metrics||{};
  h+='<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:8px;margin-bottom:14px">';
  h+='<div style="background:#0c0c0e;border:1px solid #1e1e21;border-radius:8px;padding:8px;text-align:center"><div style="font-size:1rem;font-weight:900;color:'+(dgc[dhg]||'#a1a1aa')+'">'+dhg+'</div><div style="font-size:.58rem;color:#52525b;text-transform:uppercase">Health</div></div>';
  h+='<div style="background:#0c0c0e;border:1px solid #1e1e21;border-radius:8px;padding:8px;text-align:center"><div style="font-size:1rem;font-weight:900;color:#818cf8">'+(dm.active||0)+'</div><div style="font-size:.58rem;color:#52525b;text-transform:uppercase">Active</div></div>';
  h+='<div style="background:#0c0c0e;border:1px solid #1e1e21;border-radius:8px;padding:8px;text-align:center"><div style="font-size:1rem;font-weight:900;color:'+(dm.departed>0?'#f87171':'#4ade80')+'">'+(dm.departed||0)+'</div><div style="font-size:.58rem;color:#52525b;text-transform:uppercase">Departed</div></div>';
  h+='<div style="background:#0c0c0e;border:1px solid #1e1e21;border-radius:8px;padding:8px;text-align:center"><div style="font-size:1rem;font-weight:900;color:#fbbf24">'+(dm.clsa||0)+'</div><div style="font-size:.58rem;color:#52525b;text-transform:uppercase">CLSA</div></div>';
  h+='<div style="background:#0c0c0e;border:1px solid #1e1e21;border-radius:8px;padding:8px;text-align:center"><div style="font-size:1rem;font-weight:900;color:#4ade80">'+(dm.recent_hires||0)+'</div><div style="font-size:.58rem;color:#52525b;text-transform:uppercase">New Hires</div></div>';
  h+='<div style="background:#0c0c0e;border:1px solid #1e1e21;border-radius:8px;padding:8px;text-align:center"><div style="font-size:1rem;font-weight:900;color:#818cf8">'+(co.tech_stack||[]).length+'</div><div style="font-size:.58rem;color:#52525b;text-transform:uppercase">Tech</div></div>';
  h+='</div>';
  // Projects
  h+='<div style="background:#0c0c0e;border:1px solid #1e1e21;border-radius:10px;padding:14px 16px;margin-bottom:10px"><h3 style="font-size:.82rem;font-weight:700;margin-bottom:8px;color:#e4e4e7">&#x1F4CB; Projects &amp; Use Cases</h3><p style="font-size:.8rem;color:#a1a1aa;line-height:1.5">'+co.projects+'</p></div>';
  // Tech + Domains + Certs
  h+='<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px">';
  h+='<div style="background:#0c0c0e;border:1px solid #1e1e21;border-radius:10px;padding:12px 14px"><h3 style="font-size:.76rem;font-weight:700;margin-bottom:6px;color:#e4e4e7">&#x2699; Tech Stack</h3><div style="display:flex;flex-wrap:wrap;gap:3px">';(co.tech_stack||[]).forEach(t=>{h+='<span style="display:inline-block;font-size:.66rem;padding:2px 8px;border-radius:4px;background:rgba(99,102,241,.1);color:#a5b4fc;border:1px solid rgba(99,102,241,.15)">'+t+'</span>';});h+='</div></div>';
  h+='<div style="background:#0c0c0e;border:1px solid #1e1e21;border-radius:10px;padding:12px 14px"><h3 style="font-size:.76rem;font-weight:700;margin-bottom:6px;color:#e4e4e7">&#x1F3E2; Domains</h3><div style="display:flex;flex-wrap:wrap;gap:3px">';(co.domains||[]).forEach(d=>{h+='<span style="display:inline-block;font-size:.66rem;padding:2px 8px;border-radius:4px;background:rgba(168,85,247,.1);color:#c4b5fd;border:1px solid rgba(168,85,247,.15)">'+d+'</span>';});h+='</div></div>';
  h+='<div style="background:#0c0c0e;border:1px solid #1e1e21;border-radius:10px;padding:12px 14px"><h3 style="font-size:.76rem;font-weight:700;margin-bottom:6px;color:#e4e4e7">&#x1F3C6; Certifications</h3><div style="display:flex;flex-wrap:wrap;gap:3px">';(co.certifications_required||[]).forEach(c_=>{h+='<span style="display:inline-block;font-size:.66rem;padding:2px 8px;border-radius:4px;background:rgba(250,204,21,.08);color:#fde047;border:1px solid rgba(250,204,21,.15)">'+c_+'</span>';});h+='</div></div></div>';
  // Team members
  if(tm.length>0){
    const lvlColors={1:'#818cf8',2:'#c084fc',3:'#38bdf8',4:'#4ade80',5:'#a1a1aa',9:'#f87171'};
    const lvlIcons={1:'&#x1F451;',2:'&#x1F3D7;',3:'&#x1F6E0;',4:'&#x2B50;',5:'&#x1F4BB;',9:'&#x1F6AA;'};
    let curLbl='';
    h+='<div style="background:#0c0c0e;border:1px solid #1e1e21;border-radius:10px;padding:14px 16px;margin-bottom:10px"><h3 style="font-size:.82rem;font-weight:700;margin-bottom:10px;color:#e4e4e7">&#x1F464; Team Members ('+tm.length+' confirmed)</h3>';
    tm.forEach(m=>{
      const rl=m._role_label||'';
      if(rl&&rl!==curLbl){curLbl=rl;const lv=m._role_level||5;const col=lvlColors[lv]||'#a1a1aa';const ico=lvlIcons[lv]||'';h+='<div style="margin-top:12px;margin-bottom:4px;padding:3px 8px;border-left:3px solid '+col+';font-size:.68rem;font-weight:700;color:'+col+';text-transform:uppercase;letter-spacing:1px">'+ico+' '+rl+'</div>';}
      const certs=iGetCerts(m);
      h+='<div style="background:#111113;border:1px solid #1e1e21;border-radius:8px;padding:12px 14px;margin-top:8px">';
      const li=m.linkedin||'';
      if(li)h+='<div style="font-size:.84rem;font-weight:700"><a href="'+li+'" target="_blank" style="color:#fff;text-decoration:none">'+m.name+' <span style="font-size:10px;color:#0a66c2">&#x1F517;</span></a></div>';
      else h+='<div style="font-size:.84rem;font-weight:700;color:#fff">'+m.name+'</div>';
      if(m.title)h+='<div style="font-size:.76rem;color:#818cf8;margin-bottom:3px">'+m.title+'</div>';
      if(certs.length>0){h+='<div style="margin:4px 0">';certs.forEach(c=>{h+='<span style="display:inline-block;font-size:.6rem;padding:1px 6px;border-radius:3px;background:rgba(250,204,21,'+(iIsTop(c)?'.15':'.06')+');border:1px solid rgba(250,204,21,'+(iIsTop(c)?'.3':'.12')+');color:#fde047;margin:1px'+(iIsTop(c)?';font-weight:700':'')+'">'+c+'</span>';});h+='</div>';}
      // Career timeline
      if(m.career&&m.career.length>0){
        h+='<div style="margin-top:6px;padding-left:14px;border-left:2px solid #27272a">';
        m.career.forEach((s,i)=>{
          const dotCol=i===0?'#4ade80':(s.role&&(s.role.toUpperCase().includes('LEFT')||s.role.toUpperCase().includes('DEPARTED')||s.role.toUpperCase().includes('NOTICE'))?'#f87171':'#3f3f46');
          h+='<div style="padding:3px 0 6px 12px;position:relative;font-size:.74rem">';
          h+='<span style="position:absolute;left:-8px;top:7px;width:7px;height:7px;border-radius:50%;background:'+dotCol+'"></span>';
          h+='<span style="font-weight:600;color:#e4e4e7">'+(s.company||'')+'</span> &mdash; <span style="color:#818cf8">'+(s.role||'')+'</span>';
          if(s.dates)h+='<br><span style="color:#52525b;font-size:.68rem">'+s.dates+'</span>';
          if(s.detail)h+='<br><span style="color:#71717a;font-size:.68rem;font-style:italic">'+s.detail+'</span>';
          h+='</div>';
        });
        h+='</div>';
      } else if(m.location||m.tenure){
        h+='<div style="font-size:.72rem;color:#52525b;margin-top:4px">'+(m.location?'&#x1F4CD; '+m.location:'')+(m.tenure?' &bull; '+m.tenure:'')+'</div>';
      }
      h+='</div>';
    });
    h+='</div>';
  } else {
    h+='<div style="background:#0c0c0e;border:1px solid #1e1e21;border-radius:10px;padding:14px 16px;margin-bottom:10px"><h3 style="font-size:.82rem;font-weight:700;margin-bottom:6px;color:#e4e4e7">&#x1F464; Team Members</h3><p style="font-size:.78rem;color:#52525b">Individual profiles not yet available. Estimated team: ~'+co.team_size+' Pega developers.</p></div>';
  }
  // Highlights
  if(co.highlights&&co.highlights.length>0){
    h+='<div style="background:#0c0c0e;border:1px solid #1e1e21;border-radius:10px;padding:14px 16px;margin-bottom:10px"><h3 style="font-size:.82rem;font-weight:700;margin-bottom:8px;color:#e4e4e7">&#x2728; Key Intelligence</h3><ul style="list-style:none;padding:0">';
    co.highlights.forEach(hl=>{h+='<li style="padding:3px 0;font-size:.78rem;color:#a1a1aa;display:flex;align-items:flex-start;gap:6px"><span style="display:inline-block;width:5px;height:5px;border-radius:50%;background:#6366f1;flex-shrink:0;margin-top:6px"></span>'+hl+'</li>';});
    h+='</ul></div>';
  }
  // Hiring Playbook
  if(co._hiring_playbook){
    const pb=co._hiring_playbook;
    h+='<div style="background:linear-gradient(135deg,#0f0a1e,#111113);border:2px solid #4f46e5;border-radius:14px;padding:20px 22px;margin-bottom:10px;position:relative;overflow:hidden">';
    h+='<div style="position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,#6366f1,#a855f7,#ec4899)"></div>';
    h+='<h3 style="font-size:.95rem;font-weight:900;margin-bottom:14px;color:#e4e4e7">&#x1F3AF; Hiring Playbook — How to Get Hired at '+co.name+'</h3>';
    // Bangalore Intel
    if(pb.bangalore_intel){
      const bi=pb.bangalore_intel;
      if(bi.has_bangalore){
        h+='<div style="background:linear-gradient(135deg,rgba(34,197,94,.06),rgba(56,189,248,.06));border:1px solid rgba(34,197,94,.2);border-radius:10px;padding:14px 16px;margin-bottom:16px">';
        h+='<div style="font-size:.72rem;font-weight:700;color:#4ade80;text-transform:uppercase;letter-spacing:.8px;margin-bottom:8px">&#x1F4CD; Bangalore Pega Team — Confirmed</div>';
        h+='<p style="font-size:.82rem;color:#a1a1aa;margin-bottom:10px">'+bi.summary+'</p>';
        if(bi.contacts&&bi.contacts.length>0){
          h+='<div style="font-size:.72rem;font-weight:700;color:#38bdf8;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px">Key Bangalore Contacts</div>';
          bi.contacts.forEach(ct=>{
            h+='<div style="display:flex;align-items:center;gap:10px;padding:8px 10px;margin-bottom:4px;background:rgba(9,9,11,.5);border-radius:6px;border:1px solid #1e1e21">';
            const roleCol=ct.role_type==="Hiring Manager"?"#4ade80":ct.role_type==="Architect"?"#818cf8":"#38bdf8";
            h+='<span style="font-size:.62rem;font-weight:800;padding:2px 8px;border-radius:4px;background:rgba(99,102,241,.1);color:'+roleCol+';border:1px solid rgba(99,102,241,.2);white-space:nowrap">'+ct.role_type+'</span>';
            if(ct.linkedin)h+='<a href="'+ct.linkedin+'" target="_blank" style="font-size:.8rem;font-weight:700;color:#fff;text-decoration:none">'+ct.name+' <span style="color:#0a66c2;font-size:.65rem">&#x1F517;</span></a>';
            else h+='<span style="font-size:.8rem;font-weight:700;color:#fff">'+ct.name+'</span>';
            h+='<span style="font-size:.72rem;color:#52525b;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+ct.title+'</span>';
            if(ct.certs)h+='<span style="font-size:.6rem;color:#fde047;background:rgba(250,204,21,.08);padding:1px 6px;border-radius:3px">'+ct.certs+'</span>';
            h+='</div>';
          });
        }
        if(bi.tip)h+='<p style="font-size:.78rem;color:#4ade80;margin-top:10px;font-style:italic">&#x1F4A1; '+bi.tip+'</p>';
        h+='</div>';
      } else {
        h+='<div style="background:rgba(251,146,60,.04);border:1px solid rgba(251,146,60,.15);border-radius:10px;padding:12px 16px;margin-bottom:16px">';
        h+='<div style="font-size:.72rem;font-weight:700;color:#fb923c;text-transform:uppercase;letter-spacing:.8px;margin-bottom:6px">&#x1F4CD; Bangalore Presence</div>';
        h+='<p style="font-size:.82rem;color:#71717a">'+bi.summary+'</p>';
        if(bi.tip)h+='<p style="font-size:.76rem;color:#fb923c;margin-top:6px;font-style:italic">'+bi.tip+'</p>';
        h+='</div>';
      }
    }
    // Business Reality + Phase
    h+='<div style="margin-bottom:16px;padding-bottom:14px;border-bottom:1px solid rgba(99,102,241,.1)">';
    h+='<div style="font-size:.72rem;font-weight:700;color:#818cf8;text-transform:uppercase;letter-spacing:.8px;margin-bottom:8px">What They Are Actually Doing With Pega</div>';
    const phRaw=(pb.project_phase||'').toLowerCase();
    let phCol='#c084fc';
    if(phRaw.includes('mature')||phRaw.includes('stable'))phCol='#38bdf8';
    else if(phRaw.includes('expand')||phRaw.includes('growing'))phCol='#4ade80';
    else if(phRaw.includes('migrat'))phCol='#fb923c';
    h+='<span style="display:inline-flex;padding:4px 14px;border-radius:20px;font-size:.74rem;font-weight:700;margin-bottom:10px;background:rgba(99,102,241,.08);color:'+phCol+';border:1px solid rgba(99,102,241,.15)">&#x25CF; '+pb.project_phase+'</span>';
    h+='<p style="font-size:.82rem;color:#a1a1aa;line-height:1.7;white-space:pre-line">'+pb.business_reality+'</p></div>';
    // Skills
    if(pb.skills_to_master&&pb.skills_to_master.length>0){
      h+='<div style="margin-bottom:16px;padding-bottom:14px;border-bottom:1px solid rgba(99,102,241,.1)">';
      h+='<div style="font-size:.72rem;font-weight:700;color:#818cf8;text-transform:uppercase;letter-spacing:.8px;margin-bottom:8px">Skills to Master</div>';
      h+='<div style="display:flex;flex-wrap:wrap;gap:5px">';pb.skills_to_master.forEach(s=>{h+='<span style="padding:3px 10px;border-radius:6px;font-size:.72rem;font-weight:600;background:rgba(34,197,94,.08);color:#86efac;border:1px solid rgba(34,197,94,.15)">'+s+'</span>';});h+='</div></div>';
    }
    // Difficulty + Salary
    h+='<div style="margin-bottom:16px;padding-bottom:14px;border-bottom:1px solid rgba(99,102,241,.1)">';
    const diffLow=(pb.difficulty||'').toLowerCase();
    let diffCol='#fbbf24';if(diffLow==='easy')diffCol='#4ade80';else if(diffLow==='hard')diffCol='#fb923c';else if(diffLow.includes('very'))diffCol='#fb7185';
    h+='<span style="padding:5px 14px;border-radius:8px;font-size:.76rem;font-weight:700;background:rgba(99,102,241,.08);color:'+diffCol+';border:1px solid rgba(99,102,241,.15);margin-right:12px">&#x1F512; Difficulty: '+pb.difficulty+'</span>';
    h+='<span style="padding:5px 14px;border-radius:8px;font-size:.76rem;font-weight:700;background:rgba(99,102,241,.12);color:#a5b4fc;border:1px solid rgba(99,102,241,.2)">&#x1F4B0; Expected: '+pb.salary_range+'</span>';
    h+='</div>';
    // Approach Ranking
    if(pb.approach_ranking&&pb.approach_ranking.length>0){
      h+='<div style="margin-bottom:16px;padding-bottom:14px;border-bottom:1px solid rgba(99,102,241,.1)">';
      h+='<div style="font-size:.72rem;font-weight:700;color:#818cf8;text-transform:uppercase;letter-spacing:.8px;margin-bottom:8px">Best Way to Get Hired</div>';
      pb.approach_ranking.forEach(a=>{
        const eLow=(a.effectiveness||'').toLowerCase();
        let eCol='#fde047';let eBg='rgba(250,204,21,.15)';
        if(eLow==='best'){eCol='#4ade80';eBg='rgba(34,197,94,.2)';}else if(eLow==='high'){eCol='#a5b4fc';eBg='rgba(99,102,241,.2)';}
        h+='<div style="display:flex;align-items:flex-start;gap:10px;padding:10px 12px;margin-bottom:6px;border-radius:8px;background:rgba(99,102,241,.04);border:1px solid rgba(99,102,241,.08)">';
        h+='<span style="flex-shrink:0;padding:2px 8px;border-radius:4px;font-size:.65rem;font-weight:800;text-transform:uppercase;min-width:50px;text-align:center;background:'+eBg+';color:'+eCol+';border:1px solid rgba(99,102,241,.2)">'+a.effectiveness+'</span>';
        h+='<span style="font-size:.8rem;font-weight:700;color:#e4e4e7;min-width:180px;flex-shrink:0">'+a.method+'</span>';
        h+='<span style="font-size:.76rem;color:#71717a;line-height:1.5">'+a.tip+'</span></div>';
      });
      h+='</div>';
    }
    // Pitch
    if(pb.pitch_to_manager&&pb.pitch_to_manager.length>0){
      h+='<div style="margin-bottom:16px;padding-bottom:14px;border-bottom:1px solid rgba(99,102,241,.1)">';
      h+='<div style="font-size:.72rem;font-weight:700;color:#818cf8;text-transform:uppercase;letter-spacing:.8px;margin-bottom:8px">Your Pitch to the Manager</div>';
      h+='<ul style="list-style:none;padding:0">';pb.pitch_to_manager.forEach(p=>{h+='<li style="padding:8px 0 8px 20px;font-size:.8rem;color:#a1a1aa;line-height:1.5;position:relative;border-bottom:1px solid rgba(99,102,241,.06)"><span style="position:absolute;left:0;color:#4ade80;font-weight:700;font-size:.75rem">&#x2713;</span>'+p+'</li>';});h+='</ul></div>';
    }
    // Insider Tip
    if(pb.insider_tip){
      h+='<div style="background:linear-gradient(135deg,rgba(168,85,247,.08),rgba(99,102,241,.08));border:1px solid rgba(168,85,247,.2);border-radius:10px;padding:14px 16px">';
      h+='<div style="font-size:.72rem;font-weight:800;color:#c084fc;text-transform:uppercase;letter-spacing:.8px;margin-bottom:6px">&#x1F4A1; Insider Tip</div>';
      h+='<p style="font-size:.82rem;color:#e4e4e7;line-height:1.6;font-style:italic">'+pb.insider_tip+'</p></div>';
    }
    h+='</div>';
  }
  h+='</div>';
  document.getElementById('intelContent').innerHTML=h;
  document.getElementById('intelContent').scrollTop=0;
}

// on load: check if scan is running or has results
window.addEventListener('load',async()=>{
  try{
    const r=await fetch('/api/status'),s=await r.json();
    if(s.running){
      document.getElementById('scanBtn').disabled=true;
      document.getElementById('scanBtn').innerHTML='<span class="scanning">Scanning...</span>';
      document.getElementById('progArea').classList.add('show');
      document.getElementById('scanLog').classList.add('show');
      startPolling();
    }else if(s.companies_scanned>0){
      // already have results, go straight to results screen
      switchToResults(s);
    }
  }catch(e){}
});
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Team Intelligence HTML template
# ---------------------------------------------------------------------------
TEAM_INTEL_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Pega Team Intelligence</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
body{font-family:'Inter',system-ui,-apple-system,sans-serif;background:#09090b;color:#e4e4e7;min-height:100vh;overflow-x:hidden}
a{color:inherit;text-decoration:none}

/* top bar */
.topbar{position:sticky;top:0;z-index:20;background:rgba(9,9,11,.92);backdrop-filter:blur(14px);border-bottom:1px solid #1e1e21;padding:10px 24px;display:flex;align-items:center;gap:16px}
.topbar .brand{font-size:.95rem;font-weight:800;letter-spacing:-.02em;white-space:nowrap}
.topbar .brand .g1{background:linear-gradient(135deg,#a855f7,#6366f1);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.topbar .nav-tabs{display:flex;gap:0;border-radius:8px;overflow:hidden;border:1px solid #27272a;margin-left:16px}
.topbar .nt{padding:7px 18px;font-size:.78rem;font-weight:600;cursor:pointer;background:transparent;color:#71717a;border:none;transition:all .15s;text-decoration:none}
.topbar .nt.active{background:#6366f1;color:#fff}
.topbar .nt:hover:not(.active){background:#18181b;color:#a5b4fc}
.topbar .search-box{flex:1;max-width:400px;position:relative;margin-left:auto}
.topbar .search-box input{width:100%;padding:8px 12px 8px 34px;border:1px solid #27272a;border-radius:8px;background:#111113;color:#e4e4e7;font-size:.82rem;outline:none}
.topbar .search-box input:focus{border-color:#6366f1;box-shadow:0 0 0 2px rgba(99,102,241,.2)}
.topbar .search-box .ico{position:absolute;left:10px;top:7px;color:#52525b;font-size:.9rem}
.topbar .stat-pills{display:flex;gap:10px;align-items:center}
.topbar .sp{display:flex;align-items:center;gap:5px;font-size:.78rem;color:#71717a}
.topbar .sp b{font-size:1rem;font-weight:800}
.topbar .sp b.purple{background:linear-gradient(135deg,#6366f1,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.topbar .sp b.green{color:#4ade80}

/* body grid */
.dash-body{display:flex;height:calc(100vh - 52px)}
.sidebar-r{width:240px;border-right:1px solid #1e1e21;overflow-y:auto;padding:12px 0;flex-shrink:0;background:#0c0c0e}
.sidebar-r .sh{font-size:.65rem;color:#52525b;text-transform:uppercase;letter-spacing:1px;font-weight:700;padding:10px 14px 4px}
.sidebar-r .ci{display:flex;align-items:center;gap:8px;padding:7px 14px;cursor:pointer;font-size:.8rem;color:#a1a1aa;transition:all .1s;border-left:3px solid transparent}
.sidebar-r .ci:hover{background:#111113;color:#e4e4e7}
.sidebar-r .ci.active{background:#111113;color:#fff;border-left-color:#6366f1}
.sidebar-r .ci .cnt{margin-left:auto;font-size:.7rem;padding:1px 7px;border-radius:10px;font-weight:700}
.sidebar-r .filter-pills{display:flex;flex-wrap:wrap;gap:4px;padding:6px 14px 10px}
.sidebar-r .fp{padding:3px 10px;border-radius:6px;font-size:.68rem;font-weight:600;border:1px solid #27272a;background:transparent;color:#71717a;cursor:pointer;transition:all .15s}
.sidebar-r .fp:hover{border-color:#6366f1;color:#c4b5fd}
.sidebar-r .fp.active{background:#6366f1;border-color:#6366f1;color:#fff}

/* main content */
.main-content{flex:1;overflow-y:auto;padding:20px 28px}

/* company card detail */
.co-header{margin-bottom:20px}
.co-header h2{font-size:1.5rem;font-weight:900;margin-bottom:4px;display:flex;align-items:center;gap:10px}
.co-header .sector-badge{font-size:.72rem;padding:3px 12px;border-radius:20px;font-weight:600}
.sector-banking{background:rgba(99,102,241,.15);color:#818cf8}
.sector-insurance{background:rgba(168,85,247,.15);color:#c084fc}
.sector-payments{background:rgba(34,197,94,.15);color:#4ade80}
.sector-healthcare{background:rgba(244,63,94,.15);color:#fb7185}
.sector-telecom{background:rgba(251,146,60,.15);color:#fb923c}
.sector-automotive{background:rgba(56,189,248,.15);color:#38bdf8}
.sector-financial{background:rgba(250,204,21,.15);color:#facc15}
.sector-technology{background:rgba(45,212,191,.15);color:#2dd4bf}
.sector-industrial{background:rgba(148,163,184,.15);color:#94a3b8}
.sector-logistics{background:rgba(217,119,6,.15);color:#d97706}
.sector-business{background:rgba(139,92,246,.15);color:#8b5cf6}

.co-header .meta-row{display:flex;gap:16px;flex-wrap:wrap;color:#71717a;font-size:.82rem;margin-top:8px}
.co-header .meta-row .mi{display:flex;align-items:center;gap:4px}

/* stat cards */
.stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:20px}
.stat-card{background:#111113;border:1px solid #1e1e21;border-radius:12px;padding:16px;text-align:center}
.stat-card .sv{font-size:1.4rem;font-weight:900;margin-bottom:2px}
.stat-card .sv.purple{background:linear-gradient(135deg,#6366f1,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.stat-card .sv.green{color:#4ade80}
.stat-card .sv.amber{color:#fbbf24}
.stat-card .sv.red{color:#f87171}
.stat-card .sl{font-size:.72rem;color:#52525b;text-transform:uppercase;letter-spacing:.5px;font-weight:600}

/* sections */
.section{background:#111113;border:1px solid #1e1e21;border-radius:12px;padding:18px 20px;margin-bottom:16px}
.section h3{font-size:.88rem;font-weight:700;margin-bottom:10px;display:flex;align-items:center;gap:6px}
.section h3 .sec-ico{font-size:1rem}

/* tech stack pills */
.tech-pills{display:flex;flex-wrap:wrap;gap:6px}
.tp{padding:4px 12px;border-radius:6px;font-size:.74rem;font-weight:600;background:rgba(99,102,241,.1);color:#a5b4fc;border:1px solid rgba(99,102,241,.2)}

/* domain pills */
.domain-pills{display:flex;flex-wrap:wrap;gap:6px}
.dmp{padding:4px 12px;border-radius:6px;font-size:.74rem;font-weight:600;background:rgba(168,85,247,.1);color:#c4b5fd;border:1px solid rgba(168,85,247,.2)}

/* cert pills */
.cert-pills{display:flex;flex-wrap:wrap;gap:6px}
.cp{padding:4px 12px;border-radius:6px;font-size:.74rem;font-weight:600;background:rgba(250,204,21,.1);color:#fde047;border:1px solid rgba(250,204,21,.2)}

/* team table */
.ttbl{width:100%;border-collapse:collapse;font-size:.82rem;margin-top:8px}
.ttbl th{text-align:left;padding:8px 10px;color:#52525b;font-weight:600;font-size:.7rem;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #1e1e21}
.ttbl td{padding:8px 10px;border-bottom:1px solid #141416;vertical-align:middle}
.ttbl tr:hover td{background:rgba(99,102,241,.03)}
.ttbl .cert-mini{display:inline-block;padding:1px 6px;border-radius:4px;font-size:.65rem;font-weight:600;background:rgba(250,204,21,.1);color:#fde047;margin:1px 2px}

/* highlights */
.highlights{list-style:none;padding:0}
.highlights li{padding:5px 0;font-size:.82rem;color:#a1a1aa;display:flex;align-items:flex-start;gap:8px}
.highlights li::before{content:'';display:inline-block;width:6px;height:6px;border-radius:50%;background:#6366f1;flex-shrink:0;margin-top:6px}

/* hiring status indicator */
.hs{display:inline-flex;align-items:center;gap:4px;font-weight:700;font-size:.78rem;padding:3px 10px;border-radius:6px}
.hs-growing{background:rgba(34,197,94,.12);color:#4ade80}
.hs-actively{background:rgba(34,197,94,.2);color:#22c55e}
.hs-rapidly{background:rgba(34,197,94,.25);color:#16a34a;animation:pulse 2s infinite}
.hs-stable{background:rgba(250,204,21,.12);color:#fbbf24}
.hs-declining{background:rgba(244,63,94,.12);color:#fb7185}
.hs-moderate{background:rgba(251,146,60,.12);color:#fb923c}
.hs-dot{width:6px;height:6px;border-radius:50%}
.hs-growing .hs-dot{background:#4ade80}
.hs-actively .hs-dot{background:#22c55e}
.hs-rapidly .hs-dot{background:#16a34a}
.hs-stable .hs-dot{background:#fbbf24}
.hs-declining .hs-dot{background:#fb7185}
.hs-moderate .hs-dot{background:#fb923c}

/* overview cards for "All" view */
.ov-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px}
.ov-card{background:#111113;border:1px solid #1e1e21;border-radius:12px;padding:16px 18px;cursor:pointer;transition:all .15s}
.ov-card:hover{border-color:#6366f1;transform:translateY(-2px);box-shadow:0 8px 30px rgba(99,102,241,.1)}
.ov-card .oc-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}
.ov-card .oc-name{font-size:.92rem;font-weight:800}
.ov-card .oc-loc{font-size:.72rem;color:#52525b;margin-bottom:8px}
.ov-card .oc-proj{font-size:.78rem;color:#71717a;line-height:1.4;margin-bottom:10px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.ov-card .oc-bottom{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.ov-card .oc-ts{font-size:.68rem;font-weight:700;padding:2px 8px;border-radius:4px;background:rgba(99,102,241,.1);color:#818cf8}
.ov-card .oc-sz{font-size:.72rem;color:#a1a1aa;font-weight:700;margin-left:auto}

/* empty state */
.empty-state{text-align:center;padding:80px 20px;color:#3f3f46;font-size:.9rem}
.empty-state .big{font-size:2.5rem;margin-bottom:8px}

@keyframes pulse{0%,100%{opacity:1}50%{opacity:.6}}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.fade-in{animation:fadeIn .3s ease forwards}

@media(max-width:900px){.dash-body{flex-direction:column}.sidebar-r{width:100%;max-height:200px;border-right:none;border-bottom:1px solid #1e1e21}.main-content{padding:14px 16px}.topbar{padding:8px 12px;gap:8px}.topbar .stat-pills{display:none}.ov-grid{grid-template-columns:1fr}}
</style>
</head>
<body>

<div class="topbar">
  <div class="brand">Pega <span class="g1">Intel</span></div>
  <div class="nav-tabs">
    <a class="nt" href="/">Job Scanner</a>
    <a class="nt active" href="/intel">Team Intelligence</a>
    <a class="nt" href="/dossiers" style="color:#f97316">Deep Dossiers</a>
    <a class="nt" href="/interview-masterclass" style="color:#fbbf24">Interview Masterclass</a>
  </div>
  <div class="search-box">
    <span class="ico">&#x2315;</span>
    <input id="filterInput" placeholder="Search companies, tech, domains..." oninput="applyFilter()">
  </div>
  <div class="stat-pills">
    <div class="sp"><b class="purple" id="totalCo">0</b> companies</div>
    <div class="sp"><b class="green" id="totalGrowing">0</b> growing</div>
  </div>
</div>

<div class="dash-body">
  <div class="sidebar-r" id="sidebar">
    <!-- filled by JS -->
  </div>
  <div class="main-content" id="mainContent">
    <div class="empty-state" id="loadingState">
      <div class="big">&#x23F3;</div>
      Loading team intelligence...
    </div>
  </div>
</div>

<script>
let allCompanies=[], activeSector='all', activeCompany=null;

const sectorColors={
  'Banking':'sector-banking','Insurance':'sector-insurance','Payments':'sector-payments',
  'Healthcare':'sector-healthcare','Telecom':'sector-telecom','Automotive':'sector-automotive',
  'Financial Services':'sector-financial','Technology':'sector-technology','Industrial':'sector-industrial',
  'Logistics':'sector-logistics','Business Services':'sector-business'
};

function getSectorClass(sector){return sectorColors[sector]||'sector-banking';}

function getHiringClass(status){
  const s=status.toLowerCase();
  if(s.includes('rapidly'))return 'hs-rapidly';
  if(s.includes('actively'))return 'hs-actively';
  if(s.includes('growing'))return 'hs-growing';
  if(s.includes('declining'))return 'hs-declining';
  if(s.includes('moderate'))return 'hs-moderate';
  return 'hs-stable';
}

async function loadData(){
  try{
    const r=await fetch('/api/team-intelligence');
    const d=await r.json();
    if(d.error){document.getElementById('loadingState').innerHTML='<div class="big">&#x26A0;</div>'+d.error;return;}
    allCompanies=d.companies||[];
    document.getElementById('totalCo').textContent=allCompanies.length;
    document.getElementById('totalGrowing').textContent=allCompanies.filter(c=>c.hiring_status.toLowerCase().includes('growing')).length;
    renderSidebar(allCompanies);
    showOverview(allCompanies);
  }catch(e){
    document.getElementById('loadingState').innerHTML='<div class="big">&#x26A0;</div>Failed to load data';
  }
}

function renderSidebar(companies){
  const sb=document.getElementById('sidebar');
  const sectors=[...new Set(companies.map(c=>c.sector))].sort();

  let html='<div class="filter-pills">';
  html+='<button class="fp'+(activeSector==='all'?' active':'')+'" onclick="filterSector(\'all\')">All</button>';
  sectors.forEach(s=>{
    html+='<button class="fp'+(activeSector===s?' active':'')+'" onclick="filterSector(\''+s+'\')">'+s+'</button>';
  });
  html+='</div>';

  // Sort by team size (extract first number)
  const sorted=[...companies].sort((a,b)=>{
    const sa=parseInt(a.team_size)||0, sb_=parseInt(b.team_size)||0;
    return sb_-sa;
  });

  const filtered=activeSector==='all'?sorted:sorted.filter(c=>c.sector===activeSector);

  filtered.forEach(c=>{
    const isActive=activeCompany&&activeCompany.name===c.name;
    html+='<div class="ci'+(isActive?' active':'')+'" onclick="showCompany(\''+c.name.replace(/'/g,"\\'")+'\')">';
    html+='<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+c.name+'</span>';
    html+='<span class="cnt '+getSectorClass(c.sector)+'" style="background:inherit;color:inherit;font-size:.65rem">'+c.team_size+'</span>';
    html+='</div>';
  });
  sb.innerHTML=html;
}

function filterSector(sector){
  activeSector=sector;
  const filtered=sector==='all'?allCompanies:allCompanies.filter(c=>c.sector===sector);
  renderSidebar(filtered);
  showOverview(filtered);
  activeCompany=null;
}

function showOverview(companies){
  activeCompany=null;
  renderSidebar(activeSector==='all'?allCompanies:allCompanies.filter(c=>c.sector===activeSector));
  const mc=document.getElementById('mainContent');
  const sorted=[...companies].sort((a,b)=>{
    const sa=parseInt(a.team_size)||0, sb_=parseInt(b.team_size)||0;
    return sb_-sa;
  });

  let html='<div class="co-header fade-in"><h2>Pega GCC Intelligence Dashboard</h2>';
  html+='<div class="meta-row"><span class="mi">'+companies.length+' companies</span>';
  html+='<span class="mi">'+(activeSector==='all'?'All sectors':activeSector)+'</span></div></div>';

  // Summary stats
  const totalMembers=companies.reduce((s,c)=>(s+(c.team_members||[]).length),0);
  html+='<div class="stat-grid fade-in">';
  html+='<div class="stat-card"><div class="sv purple">'+companies.length+'</div><div class="sl">Companies</div></div>';
  const growing=companies.filter(c=>c.hiring_status.toLowerCase().includes('growing')||c.hiring_status.toLowerCase().includes('rapidly')||c.hiring_status.toLowerCase().includes('actively')).length;
  html+='<div class="stat-card"><div class="sv green">'+growing+'</div><div class="sl">Actively Growing</div></div>';
  html+='<div class="stat-card"><div class="sv amber">'+totalMembers+'</div><div class="sl">People Profiled</div></div>';
  const locations=new Set();companies.forEach(c=>c.locations.forEach(l=>locations.add(l)));
  html+='<div class="stat-card"><div class="sv purple">'+locations.size+'</div><div class="sl">Cities</div></div>';
  const sectors=new Set(companies.map(c=>c.sector));
  html+='<div class="stat-card"><div class="sv purple">'+sectors.size+'</div><div class="sl">Sectors</div></div>';
  const highMat=companies.filter(c=>c.maturity&&(c.maturity.toLowerCase().includes('high')||c.maturity.toLowerCase().includes('very'))).length;
  html+='<div class="stat-card"><div class="sv green">'+highMat+'</div><div class="sl">High Maturity</div></div>';
  html+='</div>';

  // Company cards grid
  html+='<div class="ov-grid fade-in">';
  sorted.forEach(c=>{
    const memberCount=(c.team_members||[]).length;
    const certsList=(c.certifications_required||[]).slice(0,3).join(', ');
    html+='<div class="ov-card" onclick="showCompany(\''+c.name.replace(/'/g,"\\'")+'\')">';
    html+='<div class="oc-top"><span class="oc-name">'+c.name+'</span>';
    html+='<span class="sector-badge '+getSectorClass(c.sector)+'">'+c.sector+'</span></div>';
    html+='<div class="oc-loc">'+c.locations.join(' / ')+(memberCount>0?' &bull; '+memberCount+' members profiled':'')+'</div>';
    html+='<div class="oc-proj">'+c.projects+'</div>';
    // Show tech stack preview
    if(c.tech_stack&&c.tech_stack.length>0){
      html+='<div style="display:flex;flex-wrap:wrap;gap:3px;margin-bottom:8px">';
      c.tech_stack.slice(0,4).forEach(t=>{html+='<span style="font-size:.62rem;padding:1px 6px;border-radius:3px;background:rgba(99,102,241,.08);color:#818cf8;border:1px solid rgba(99,102,241,.15)">'+t+'</span>';});
      if(c.tech_stack.length>4)html+='<span style="font-size:.62rem;padding:1px 6px;color:#52525b">+'+(c.tech_stack.length-4)+' more</span>';
      html+='</div>';
    }
    html+='<div class="oc-bottom">';
    html+='<span class="hs '+getHiringClass(c.hiring_status)+'"><span class="hs-dot"></span>'+c.hiring_status+'</span>';
    if(certsList)html+='<span style="font-size:.68rem;color:#fde047">'+certsList+'</span>';
    html+='<span class="oc-sz">Team: '+c.team_size+'</span></div>';
    html+='</div>';
  });
  html+='</div>';
  mc.innerHTML=html;
}

function showCompany(name){
  const co=allCompanies.find(c=>c.name===name);
  if(!co)return;
  activeCompany=co;
  renderSidebar(activeSector==='all'?allCompanies:allCompanies.filter(c=>c.sector===activeSector));

  const mc=document.getElementById('mainContent');
  let html='<div class="co-header fade-in">';
  html+='<h2>'+co.name+' <span class="sector-badge '+getSectorClass(co.sector)+'">'+co.sector+'</span></h2>';
  html+='<div class="meta-row">';
  html+='<span class="mi">&#x1F4CD; '+co.locations.join(', ')+'</span>';
  html+='<span class="mi">&#x1F465; Team: '+co.team_size+'</span>';
  html+='<span class="mi">&#x1F3AF; '+co.maturity+' Maturity</span>';
  html+='<span class="hs '+getHiringClass(co.hiring_status)+'"><span class="hs-dot"></span>'+co.hiring_status+'</span>';
  html+='</div></div>';

  // Stat cards
  const tmCount=(co.team_members||[]).length;
  html+='<div class="stat-grid fade-in">';
  html+='<div class="stat-card"><div class="sv purple">'+co.team_size+'</div><div class="sl">Team Size</div></div>';
  html+='<div class="stat-card"><div class="sv green">'+tmCount+'</div><div class="sl">Members Profiled</div></div>';
  html+='<div class="stat-card"><div class="sv amber">'+co.tech_stack.length+'</div><div class="sl">Technologies</div></div>';
  html+='<div class="stat-card"><div class="sv purple">'+co.domains.length+'</div><div class="sl">Domains</div></div>';
  html+='<div class="stat-card"><div class="sv purple">'+co.locations.length+'</div><div class="sl">Locations</div></div>';
  html+='<div class="stat-card"><div class="sv'+(co.maturity&&co.maturity.toLowerCase().includes('high')?' green':' amber')+'">'+co.maturity+'</div><div class="sl">Maturity</div></div>';
  html+='</div>';

  // Projects
  html+='<div class="section fade-in"><h3><span class="sec-ico">&#x1F4CB;</span> Active Projects</h3>';
  html+='<p style="font-size:.84rem;color:#a1a1aa;line-height:1.6">'+co.projects+'</p></div>';

  // Tech stack
  html+='<div class="section fade-in"><h3><span class="sec-ico">&#x2699;</span> Tech Stack</h3>';
  html+='<div class="tech-pills">';
  co.tech_stack.forEach(t=>{html+='<span class="tp">'+t+'</span>';});
  html+='</div></div>';

  // Domains + Certifications side by side
  html+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px" class="fade-in">';
  html+='<div class="section"><h3><span class="sec-ico">&#x1F3E2;</span> Domains</h3>';
  html+='<div class="domain-pills">';
  co.domains.forEach(d=>{html+='<span class="dmp">'+d+'</span>';});
  html+='</div></div>';

  html+='<div class="section"><h3><span class="sec-ico">&#x1F3C6;</span> Certifications Required</h3>';
  html+='<div class="cert-pills">';
  (co.certifications_required||[]).forEach(c_=>{html+='<span class="cp">'+c_+'</span>';});
  html+='</div></div></div>';

  // Team members - with rich details
  if(co.team_members&&co.team_members.length>0){
    html+='<div class="section fade-in"><h3><span class="sec-ico">&#x1F464;</span> Confirmed Team Members ('+co.team_members.length+')</h3>';
    html+='<table class="ttbl"><thead><tr><th>Name</th><th>Title / Role</th><th>Certifications</th><th>Location</th></tr></thead><tbody>';
    co.team_members.forEach(m=>{
      // Handle both certs (string) and certifications (array) formats
      let certsArr=[];
      if(m.certs&&typeof m.certs==='string'){certsArr=m.certs.split(',').map(c_=>c_.trim()).filter(c_=>c_);}
      else if(m.certifications&&Array.isArray(m.certifications)){certsArr=m.certifications.filter(c_=>c_);}
      const certsHtml=certsArr.length>0?certsArr.map(c_=>'<span class="cert-mini">'+c_+'</span>').join(''):'<span style="color:#3f3f46">-</span>';
      html+='<tr><td style="font-weight:600;color:#e4e4e7">'+m.name+'</td>';
      html+='<td style="color:#a5b4fc">'+m.title+'</td>';
      html+='<td>'+certsHtml+'</td>';
      html+='<td>'+(m.location||'<span style="color:#3f3f46">-</span>')+'</td></tr>';
      // Show career history if available
      if(m.career&&m.career.length>0){
        html+='<tr><td colspan="4" style="padding:4px 10px 12px;border-bottom:1px solid #1e1e21"><div style="padding-left:20px;border-left:2px solid #27272a">';
        m.career.forEach((stop,i)=>{
          const dotColor=i===0?'#4ade80':(stop.role&&stop.role.toUpperCase().includes('LEFT')?'#f87171':'#3f3f46');
          html+='<div style="padding:4px 0 6px 14px;position:relative;font-size:.78rem">';
          html+='<span style="position:absolute;left:-6px;top:8px;width:8px;height:8px;border-radius:50%;background:'+dotColor+'"></span>';
          html+='<span style="font-weight:600;color:#e4e4e7">'+(stop.company||'')+'</span>';
          html+=' &mdash; <span style="color:#818cf8">'+(stop.role||'')+'</span>';
          if(stop.dates){html+='<br><span style="color:#52525b;font-size:.72rem">'+stop.dates+'</span>';}
          if(stop.detail){html+='<br><span style="color:#71717a;font-size:.72rem;font-style:italic">'+stop.detail+'</span>';}
          html+='</div>';
        });
        html+='</div></td></tr>';
      }
      // Show tenure if available
      if(m.tenure){
        html+='<tr><td colspan="4" style="padding:2px 10px 8px;color:#52525b;font-size:.72rem;border-bottom:1px solid #1e1e21">Tenure: '+m.tenure+'</td></tr>';
      }
    });
    html+='</tbody></table></div>';
  } else {
    html+='<div class="section fade-in"><h3><span class="sec-ico">&#x1F464;</span> Team Members</h3>';
    html+='<p style="font-size:.84rem;color:#52525b;padding:12px 0">Individual team member profiles not yet available. Pega usage confirmed via job postings, customer stories, or LinkedIn signals. Estimated team size: '+co.team_size+'.</p></div>';
  }

  // Highlights
  if(co.highlights&&co.highlights.length>0){
    html+='<div class="section fade-in"><h3><span class="sec-ico">&#x2728;</span> Key Highlights</h3>';
    html+='<ul class="highlights">';
    co.highlights.forEach(h=>{html+='<li>'+h+'</li>';});
    html+='</ul></div>';
  }

  mc.innerHTML=html;
  mc.scrollTop=0;
}

function applyFilter(){
  const q=document.getElementById('filterInput').value.toLowerCase();
  if(!q){
    renderSidebar(allCompanies);
    if(!activeCompany)showOverview(allCompanies);
    activeSector='all';
    return;
  }
  const filtered=allCompanies.filter(c=>{
    const getCerts=m=>{
      if(m.certs&&typeof m.certs==='string')return m.certs.toLowerCase();
      if(m.certifications&&Array.isArray(m.certifications))return m.certifications.join(' ').toLowerCase();
      return '';
    };
    return c.name.toLowerCase().includes(q)||
      c.sector.toLowerCase().includes(q)||
      c.locations.some(l=>l.toLowerCase().includes(q))||
      c.tech_stack.some(t=>t.toLowerCase().includes(q))||
      c.domains.some(d=>d.toLowerCase().includes(q))||
      c.projects.toLowerCase().includes(q)||
      c.hiring_status.toLowerCase().includes(q)||
      (c.certifications_required||[]).some(cr=>cr.toLowerCase().includes(q))||
      (c.highlights||[]).some(h=>h.toLowerCase().includes(q))||
      c.maturity.toLowerCase().includes(q)||
      (c.team_members||[]).some(m=>m.name.toLowerCase().includes(q)||m.title.toLowerCase().includes(q)||getCerts(m).includes(q));
  });
  activeSector='all';
  renderSidebar(filtered);
  showOverview(filtered);
}

window.addEventListener('load',loadData);
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pega Job Hunter Portal")
    parser.add_argument("--port", type=int, default=5050, help="Port (default 5050)")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args = parser.parse_args()

    load_cached_results()
    print(f"\n  Pega Job Hunter Portal")
    print(f"  http://{args.host}:{args.port}\n")
    app.run(host=args.host, port=args.port, debug=False)
