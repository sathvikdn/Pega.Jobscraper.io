"""
Pega Job Hunter Agent
======================
On-demand discovery scanner that checks multiple job sources for Pega openings
at target companies — GCC/product in India, Consulting/SI, AND remote/global
companies (US, UK, EU) that hire remote Pega talent.

Sources: Naukri, LinkedIn Jobs, Indeed (India + US), Google, direct career pages
Output:  HTML report saved to ./reports/ folder
Scheduling: no recurring task is configured by this scanner.

Usage:
    python pega_job_hunter.py              # Full scan, all companies
    python pega_job_hunter.py --quick      # Quick scan, top 30 only
    python pega_job_hunter.py --company "JPMC"  # Single company
    python pega_job_hunter.py --remote     # Scan remote/global companies only
    python pega_job_hunter.py --open       # Scan + auto-open report
    python pega_job_hunter.py --browser    # Open all search links in browser
"""

import json
import os
import re
import sys
import time
import hashlib
import logging
import argparse
import subprocess
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import webbrowser
import html as html_escape
from quality import canonical_url, employer_matches, broad_target, job_identity

# Optional workspace-local dependencies installed by setup.ps1.
sys.path.insert(0, str(Path(__file__).parent / ".deps"))

try:
    import requests
    from bs4 import BeautifulSoup
    import urllib3
except ImportError as exc:
    print(f"Missing dependency: {exc}")
    print("Run: pip install requests beautifulsoup4 lxml")
    sys.exit(1)

# Corporate CA bundles can be supplied through REQUESTS_CA_BUNDLE.
SSL_VERIFY = True

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
REPORTS_DIR = BASE_DIR / "reports"
HISTORY_FILE = BASE_DIR / "job_history.json"
LOG_FILE = BASE_DIR / "pega_job_hunter.log"

# Rate-limiting: seconds between requests to the same domain
DELAY_BETWEEN_REQUESTS = 2.5
# Max retries per request
MAX_RETRIES = 2
# Request timeout in seconds
REQUEST_TIMEOUT = 15

# Headers to mimic a real browser
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("pega_hunter")

# ---------------------------------------------------------------------------
# Pega-related keywords — catches generic job titles (Software Engineer III)
# where Pega is only in skills/tags/description, not the title itself
# ---------------------------------------------------------------------------
PEGA_KEYWORDS = {
    "pega", "prpc", "pega platform", "pega infinity", "pega cdh",
    "pega marketing", "pega customer service", "pega decisioning",
    "pega constellation", "openspan", "pega robotics", "pega dx api",
    "pega cosmos", "pegasystems", "pega cssa", "pega csa", "pega clsa",
    "case management pega", "pega 8", "pega cloud",
}

# Multiple search variations to catch generic-titled Pega roles
SEARCH_QUERIES = [
    "pega developer",
    "pega architect",
    "pega engineer",
    "software engineer pega",
    "pega PRPC",
    "pega consultant",
    "pega lead",
]


def _is_pega_relevant(text: str) -> bool:
    """Check if text contains ANY Pega-related keyword.
    
    Used to keep results where Pega is in tags/skills/snippet even if
    the job title is generic (e.g., 'Software Engineer III').
    """
    lower = text.lower()
    return any(re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", lower) for kw in PEGA_KEYWORDS)

# ---------------------------------------------------------------------------
# Target GCC Companies (non-SI, direct employers only)
# ---------------------------------------------------------------------------
COMPANIES = [
    # --- Banking / Finance ---
    {"name": "JPMorganChase", "keywords": ["jpmorgan", "jpmorganchase", "jpmc", "jp morgan"], "career_url": "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions?keyword=pega&location=India", "priority": "top30"},
    {"name": "Wells Fargo", "keywords": ["wells fargo"], "career_url": "https://www.wellsfargojobs.com/en/jobs/?search=pega&country=India", "priority": "top30"},
    {"name": "Bank of America", "keywords": ["bank of america", "bofa"], "career_url": None, "priority": "top30"},
    {"name": "HSBC", "keywords": ["hsbc"], "career_url": "https://mycareer.hsbc.com/en_GB/external/SearchJobs/?q=pega&locationsearch=India", "priority": "top30"},
    {"name": "Standard Chartered", "keywords": ["standard chartered"], "career_url": None, "priority": "top30"},
    {"name": "Goldman Sachs", "keywords": ["goldman sachs"], "career_url": "https://higher.gs.com/roles?q=pega&location=India", "priority": "top30"},
    {"name": "Morgan Stanley", "keywords": ["morgan stanley"], "career_url": None, "priority": "top30"},
    {"name": "Barclays", "keywords": ["barclays"], "career_url": None, "priority": "top30"},
    {"name": "Citi India", "keywords": ["citi", "citibank", "citi india"], "career_url": None, "priority": "top30"},
    {"name": "Deutsche Bank", "keywords": ["deutsche bank"], "career_url": None, "priority": "top30"},
    {"name": "UBS", "keywords": ["ubs"], "career_url": None, "priority": "top30"},
    {"name": "ANZ", "keywords": ["anz bank", "anz india"], "career_url": None, "priority": "top30"},
    {"name": "CBA", "keywords": ["commonwealth bank", "cba"], "career_url": None, "priority": "top30"},
    {"name": "NatWest Group", "keywords": ["natwest"], "career_url": None, "priority": "top30"},
    {"name": "Lloyds Banking", "keywords": ["lloyds banking", "lloyds bank"], "career_url": None, "priority": "top30"},
    {"name": "BNP Paribas", "keywords": ["bnp paribas"], "career_url": None, "priority": "top30"},
    {"name": "Societe Generale", "keywords": ["societe generale", "socgen"], "career_url": None, "priority": "gcc"},
    {"name": "NAB", "keywords": ["national australia bank", "nab"], "career_url": None, "priority": "gcc"},
    {"name": "MUFG", "keywords": ["mufg", "mitsubishi ufj"], "career_url": None, "priority": "gcc"},
    {"name": "American Express", "keywords": ["american express", "amex"], "career_url": None, "priority": "top30"},
    {"name": "Synchrony", "keywords": ["synchrony"], "career_url": None, "priority": "gcc"},
    {"name": "First Citizens Bank", "keywords": ["first citizens bank"], "career_url": None, "priority": "gcc"},
    {"name": "Kotak Mahindra Bank", "keywords": ["kotak mahindra"], "career_url": None, "priority": "gcc"},

    # --- Insurance ---
    {"name": "AXA", "keywords": ["axa insurance", "axa india"], "career_url": None, "priority": "gcc"},
    {"name": "Allianz Technology", "keywords": ["allianz technology", "allianz"], "career_url": None, "priority": "gcc"},
    {"name": "MetLife India", "keywords": ["metlife india", "metlife"], "career_url": None, "priority": "gcc"},
    {"name": "Aflac India", "keywords": ["aflac"], "career_url": None, "priority": "gcc"},
    {"name": "Sun Life India", "keywords": ["sun life india", "sun life"], "career_url": None, "priority": "gcc"},
    {"name": "CNO Financial", "keywords": ["cno financial"], "career_url": None, "priority": "gcc"},

    # --- Healthcare ---
    {"name": "Optum / UHG India", "keywords": ["optum", "unitedhealth", "uhg india"], "career_url": None, "priority": "top30"},
    {"name": "Elevance Health", "keywords": ["elevance health", "anthem"], "career_url": None, "priority": "gcc"},
    {"name": "GE Healthcare India", "keywords": ["ge healthcare"], "career_url": None, "priority": "gcc"},
    # Roche: Pega IT Lead + Pega Architect + developers hired Pune Nov 2025,
    # Pega-based workflow automation for Drug Development / Diagnostics
    {"name": "Roche India", "keywords": ["roche india", "roche", "roche diagnostics"], "career_url": None, "priority": "gcc_top"},

    # --- Telecom ---
    {"name": "Verizon India", "keywords": ["verizon india", "verizon"], "career_url": None, "priority": "top30"},
    {"name": "BT Group India", "keywords": ["bt group", "bt india"], "career_url": None, "priority": "gcc"},
    {"name": "Vodafone / VOIS India", "keywords": ["vodafone", "vois"], "career_url": None, "priority": "gcc"},
    {"name": "Telstra India", "keywords": ["telstra india", "telstra"], "career_url": None, "priority": "gcc"},
    {"name": "Nokia India", "keywords": ["nokia india", "nokia"], "career_url": None, "priority": "gcc"},
    {"name": "Orange Business", "keywords": ["orange business"], "career_url": None, "priority": "gcc"},
    {"name": "Proximus", "keywords": ["proximus"], "career_url": None, "priority": "gcc"},

    # --- Tech / Product ---
    {"name": "Pegasystems", "keywords": ["pegasystems", "pega"], "career_url": "https://www.pega.com/about/careers/search?keywords=&location=India", "priority": "top30"},
    {"name": "Nike India", "keywords": ["nike"], "career_url": "https://careers.nike.com/?query=pega", "priority": "gcc"},
    {"name": "Booking Holdings", "keywords": ["booking holdings", "booking.com"], "career_url": None, "priority": "gcc"},
    {"name": "Siemens India", "keywords": ["siemens india", "siemens technology"], "career_url": None, "priority": "gcc"},

    # --- Automotive / Manufacturing ---
    {"name": "Ford India (FBS)", "keywords": ["ford motor", "ford business solutions", "ford india"], "career_url": None, "priority": "gcc"},
    {"name": "John Deere India", "keywords": ["john deere india", "john deere", "jdtci"], "career_url": None, "priority": "gcc"},
    {"name": "Stellantis India", "keywords": ["stellantis india", "stellantis"], "career_url": None, "priority": "gcc"},
    {"name": "Cummins India", "keywords": ["cummins india", "cummins"], "career_url": None, "priority": "gcc"},

    # --- Logistics ---
    {"name": "DHL India", "keywords": ["dhl india", "dhl"], "career_url": None, "priority": "gcc"},

    # --- FMCG ---
    {"name": "Unilever India", "keywords": ["unilever india", "hindustan unilever"], "career_url": None, "priority": "gcc"},
    {"name": "Mondelez India", "keywords": ["mondelez india", "mondelez"], "career_url": None, "priority": "gcc"},

    # --- Fintech / Payments ---
    {"name": "Mastercard India", "keywords": ["mastercard"], "career_url": None, "priority": "gcc"},
    {"name": "Visa India", "keywords": ["visa india", "visa inc"], "career_url": None, "priority": "gcc"},
    {"name": "PayPal India", "keywords": ["paypal india", "paypal"], "career_url": None, "priority": "gcc"},
    {"name": "Broadridge India", "keywords": ["broadridge"], "career_url": None, "priority": "gcc"},
    {"name": "FIS India", "keywords": ["fis ", "fis india", "fidelity national information"], "career_url": None, "priority": "gcc"},
    {"name": "Global Payments India", "keywords": ["global payments"], "career_url": None, "priority": "gcc"},
    {"name": "Fiserv India", "keywords": ["fiserv india", "fiserv"], "career_url": None, "priority": "gcc"},
    {"name": "Empower India", "keywords": ["empower india", "empower retirement", "empower "], "career_url": None, "priority": "gcc"},

    # --- US Banks with India GCC ---
    {"name": "U.S. Bank India", "keywords": ["u.s. bank", "us bank", "us bancorp"], "career_url": None, "priority": "gcc"},
    {"name": "Capital One India", "keywords": ["capital one"], "career_url": None, "priority": "gcc"},
    {"name": "PNC India", "keywords": ["pnc financial", "pnc india"], "career_url": None, "priority": "gcc"},

    # --- Insurance (additional) ---
    {"name": "IFFCO Tokio", "keywords": ["iffco tokio"], "career_url": None, "priority": "gcc"},
    {"name": "Liberty Mutual India", "keywords": ["liberty mutual"], "career_url": None, "priority": "gcc"},
    {"name": "Manulife India", "keywords": ["manulife india", "manulife"], "career_url": None, "priority": "gcc"},

    # --- Healthcare (additional) ---
    {"name": "Evernorth / Cigna India", "keywords": ["evernorth", "cigna india", "cigna"], "career_url": None, "priority": "gcc"},
    {"name": "enGen / Highmark India", "keywords": ["engen", "highmark", "thryve digital"], "career_url": None, "priority": "gcc"},
    {"name": "Pfizer India", "keywords": ["pfizer india", "pfizer"], "career_url": None, "priority": "gcc"},
    # Novartis: Pega-based clinical/regulatory apps, CSA certified staff in Hyderabad
    {"name": "Novartis India", "keywords": ["novartis india", "novartis"], "career_url": None, "priority": "gcc_top"},
    {"name": "Medtronic India", "keywords": ["medtronic india", "medtronic"], "career_url": None, "priority": "gcc"},
    {"name": "Philips India", "keywords": ["philips india", "philips healthcare"], "career_url": None, "priority": "gcc"},

    # --- Automotive (additional) ---
    {"name": "Mercedes-Benz R&D India", "keywords": ["mercedes-benz", "mercedes benz", "daimler"], "career_url": None, "priority": "gcc"},
    {"name": "Renault-Nissan Tech India", "keywords": ["renault-nissan", "renault nissan"], "career_url": None, "priority": "gcc"},
    {"name": "Bosch India (BGSW)", "keywords": ["bosch india", "bosch global"], "career_url": None, "priority": "gcc"},
    {"name": "Navistar India", "keywords": ["navistar", "international motors"], "career_url": None, "priority": "gcc"},

    # --- Logistics (additional) ---
    {"name": "Maersk India", "keywords": ["maersk india", "maersk"], "career_url": None, "priority": "gcc"},
    {"name": "UPS India", "keywords": ["ups india"], "career_url": None, "priority": "gcc"},

    # --- Telecom (additional) ---
    {"name": "Comcast India", "keywords": ["comcast india", "comcast"], "career_url": None, "priority": "gcc"},
    {"name": "Amdocs India", "keywords": ["amdocs india", "amdocs"], "career_url": None, "priority": "gcc"},

    # --- Energy ---
    {"name": "Shell India", "keywords": ["shell india", "shell "], "career_url": None, "priority": "gcc"},

    # --- Retail / Consumer ---
    {"name": "Tesco Bengaluru", "keywords": ["tesco bengaluru", "tesco"], "career_url": None, "priority": "gcc"},

    # --- Technology / IT (verified Pega users) ---
    # Dell: pega.com case study — 30,000 agents, Pega Customer Service + CDH,
    # Intelligent Routing across 52 countries, 98% SLA, 16.5% more cases/day
    {"name": "Dell Technologies India", "keywords": ["dell technologies", "dell"], "career_url": "https://jobs.dell.com", "priority": "gcc_top"},

    # --- Manufacturing / Automotive (verified Pega users — India GCCs) ---
    # Toyota: pega.com case study — QIMS quality management, 300% faster resolution
    {"name": "Toyota India", "keywords": ["toyota india", "toyota"], "career_url": None, "priority": "gcc"},
    # General Motors: pega.com case study — OnStar CDH, 12M connected vehicles, 1M decisions/hour
    {"name": "General Motors India", "keywords": ["general motors", "gm india"], "career_url": None, "priority": "gcc"},
    # Procter & Gamble: verified Pega customer (ReadyContacts, notable client list)
    {"name": "Procter & Gamble India", "keywords": ["procter gamble", "p&g india"], "career_url": None, "priority": "gcc"},
    # Johnson & Johnson: verified Pega customer (notable client list)
    {"name": "Johnson & Johnson India", "keywords": ["johnson & johnson", "j&j india"], "career_url": None, "priority": "gcc"},
    # Merck: verified Pega customer (notable client list)
    {"name": "Merck India", "keywords": ["merck india", "merck"], "career_url": None, "priority": "gcc"},
    # Coca-Cola: Wikipedia verified Pega client
    {"name": "Coca-Cola India", "keywords": ["coca-cola", "coca cola"], "career_url": None, "priority": "gcc"},

    # --- Telecom (additional verified Pega users — India GCCs) ---
    # AT&T: verified Pega customer (notable client list — top 4 US telcos use Pega)
    {"name": "AT&T India", "keywords": ["at&t india", "at&t"], "career_url": None, "priority": "gcc"},

    # --- Logistics (additional verified Pega users — India GCCs) ---
    # FedEx: verified Pega customer (notable client list)
    {"name": "FedEx India", "keywords": ["fedex india", "fedex"], "career_url": None, "priority": "gcc"},

    # --- Healthcare (additional verified Pega users — India GCCs) ---
    # CVS Health: Landbase verified Pega Platform user
    {"name": "CVS Health India", "keywords": ["cvs health", "cvs india"], "career_url": None, "priority": "gcc"},

    # --- Defense (India GCC) ---
    # Lockheed Martin: verified Pega customer (notable client list)
    {"name": "Lockheed Martin India", "keywords": ["lockheed martin"], "career_url": None, "priority": "gcc"},

    # --- Financial Data / Analytics (verified Pega users) ---
    # S&P Global: multiple Pega developers on LinkedIn, Hyderabad GCC, Pega Decisioning
    {"name": "S&P Global India", "keywords": ["s&p global", "spglobal"], "career_url": "https://careers.spglobal.com", "priority": "gcc_top"},

    # --- New GCCs (2024-2026 entrants) with confirmed Pega usage ---
    # Zurich Insurance: Pega developers in Hyderabad, Constellation v24 migration,
    # GCC expansion announced 2025-2026
    {"name": "Zurich Insurance India", "keywords": ["zurich insurance", "zurich"], "career_url": None, "priority": "gcc_top"},
    # LPL Financial: CTO served on Pega Customer Advisory Board, Senior Pega
    # developers in India, new GCC in Hyderabad 2025
    {"name": "LPL Financial India", "keywords": ["lpl financial", "lpl "], "career_url": None, "priority": "gcc_top"},
    # Maximus: Pega developers for Case & Care Management, new 2nd GCC in
    # Hyderabad 2025-2026 (1st in Bengaluru)
    {"name": "Maximus India", "keywords": ["maximus"], "career_url": None, "priority": "gcc_top"},
    # Western Union: Pega developers on team, new Hyderabad GCC with HCLTech
    # partnership 2026, 400+ professionals
    {"name": "Western Union India", "keywords": ["western union"], "career_url": None, "priority": "gcc"},
    # Roche: already in list above — upgraded to gcc_top (Pega team growing in Pune since Nov 2025)
    # Novartis: already in list above — Pega-based clinical apps in Hyderabad GCC
    # Voya Financial: new GCC expansion in Hyderabad 2026
    {"name": "Voya Financial India", "keywords": ["voya financial", "voya "], "career_url": None, "priority": "gcc"},
    # Costco: brand new GCC in Hyderabad 2025, 1000+ hires target, no Pega
    # yet but monitoring — retail/ecom GCC with rapid scaling
    # (not added — no Pega evidence found)

    # --- Other GCCs ---
    {"name": "Conduent India", "keywords": ["conduent"], "career_url": None, "priority": "gcc"},
    {"name": "Ameriprise India", "keywords": ["ameriprise india", "ameriprise"], "career_url": None, "priority": "gcc"},
    {"name": "HDFC Bank", "keywords": ["hdfc bank"], "career_url": None, "priority": "gcc"},
    {"name": "ICICI Bank", "keywords": ["icici bank"], "career_url": None, "priority": "gcc"},
    {"name": "Fidelity India", "keywords": ["fidelity investments", "fidelity india"], "career_url": None, "priority": "gcc"},
    {"name": "Charles Schwab India", "keywords": ["charles schwab", "schwab india"], "career_url": None, "priority": "gcc"},
    {"name": "State Street India", "keywords": ["state street"], "career_url": None, "priority": "gcc"},
    {"name": "Northern Trust India", "keywords": ["northern trust"], "career_url": None, "priority": "gcc"},
    {"name": "BNY India", "keywords": ["bny mellon", "bny india"], "career_url": None, "priority": "gcc"},
    {"name": "Daimler Truck India", "keywords": ["daimler truck"], "career_url": None, "priority": "gcc"},
]

# ---------------------------------------------------------------------------
# Consulting / SI Companies with Pega practices (>20 LPA target)
# ---------------------------------------------------------------------------
CONSULTING_COMPANIES = [
    # --- Tier 1: Big 4 (30-60+ LPA) ---
    {"name": "Deloitte India", "keywords": ["deloitte"], "career_url": "https://southasiacareers.deloitte.com/job-search-results/?keyword=pega", "priority": "si_top", "tier": "Big 4"},
    {"name": "EY India", "keywords": ["ey ", "ernst & young", "ernst young", "ernstandyoung"], "career_url": None, "priority": "si_top", "tier": "Big 4"},
    {"name": "PwC India", "keywords": ["pwc", "pricewaterhouse"], "career_url": None, "priority": "si_top", "tier": "Big 4"},
    {"name": "KPMG India", "keywords": ["kpmg"], "career_url": None, "priority": "si_top", "tier": "Big 4"},

    # --- Tier 2: Global Premium SIs (22-45 LPA) ---
    {"name": "Accenture", "keywords": ["accenture"], "career_url": "https://www.accenture.com/in-en/careers/jobsearch?jk=pega&sb=0&vw=0&is_rj=0", "priority": "si_top", "tier": "Premium SI"},
    {"name": "Cognizant", "keywords": ["cognizant"], "career_url": "https://careers.cognizant.com/global/en/search-results?keywords=pega&location=India", "priority": "si_top", "tier": "Premium SI"},
    {"name": "Capgemini", "keywords": ["capgemini"], "career_url": "https://www.capgemini.com/in-en/careers/job-search/?search_term=pega", "priority": "si_top", "tier": "Premium SI"},
    {"name": "EPAM Systems", "keywords": ["epam"], "career_url": "https://www.epam.com/careers?query=pega&country=India", "priority": "si_top", "tier": "Premium SI"},
    {"name": "Publicis Sapient", "keywords": ["publicis sapient", "sapient"], "career_url": None, "priority": "si_top", "tier": "Premium SI"},

    # --- Tier 3: Major Indian SIs (18-30 LPA) ---
    {"name": "TCS", "keywords": ["tata consultancy", "tcs"], "career_url": "https://ibegin.tcs.com/iBegin/jobs/search?skill=pega", "priority": "si_mid", "tier": "Major SI"},
    {"name": "Infosys", "keywords": ["infosys"], "career_url": "https://www.infosys.com/careers/search-jobs.html?q=pega", "priority": "si_mid", "tier": "Major SI"},
    {"name": "Wipro", "keywords": ["wipro"], "career_url": "https://careers.wipro.com/search-jobs/pega/India", "priority": "si_mid", "tier": "Major SI"},
    {"name": "HCL Technologies", "keywords": ["hcl technologies", "hcltech", "hcl tech"], "career_url": None, "priority": "si_mid", "tier": "Major SI"},
    {"name": "Tech Mahindra", "keywords": ["tech mahindra"], "career_url": None, "priority": "si_mid", "tier": "Major SI"},
    {"name": "LTIMindtree", "keywords": ["ltimindtree", "lti mindtree"], "career_url": None, "priority": "si_mid", "tier": "Major SI"},
    {"name": "Mphasis", "keywords": ["mphasis"], "career_url": None, "priority": "si_mid", "tier": "Major SI"},
    {"name": "NTT DATA", "keywords": ["ntt data"], "career_url": None, "priority": "si_mid", "tier": "Major SI"},

    # --- Tier 4: Niche / Mid-tier (20-35 LPA) ---
    # Synechron: active Pega practice — hiring Pega devs in Chennai, US, Dubai; KYC/CLM, PRPC, LSA roles
    {"name": "Synechron", "keywords": ["synechron"], "career_url": "https://www.synechron.com/careers", "priority": "si_niche", "tier": "Niche SI"},
    {"name": "Virtusa", "keywords": ["virtusa"], "career_url": None, "priority": "si_niche", "tier": "Niche SI"},
    {"name": "Persistent Systems", "keywords": ["persistent systems", "persistent"], "career_url": None, "priority": "si_niche", "tier": "Niche SI"},
    {"name": "Coforge", "keywords": ["coforge"], "career_url": None, "priority": "si_niche", "tier": "Niche SI"},
    {"name": "Birlasoft", "keywords": ["birlasoft"], "career_url": None, "priority": "si_niche", "tier": "Niche SI"},
    {"name": "DXC Technology", "keywords": ["dxc technology", "dxc"], "career_url": None, "priority": "si_niche", "tier": "Niche SI"},
    {"name": "Hexaware", "keywords": ["hexaware"], "career_url": None, "priority": "si_niche", "tier": "Niche SI"},
    {"name": "Zensar Technologies", "keywords": ["zensar"], "career_url": None, "priority": "si_niche", "tier": "Niche SI"},
    {"name": "Areteans / Credera", "keywords": ["areteans", "credera"], "career_url": None, "priority": "si_niche", "tier": "Niche SI"},
    {"name": "UST Global", "keywords": ["ust global", "ust "], "career_url": None, "priority": "si_niche", "tier": "Niche SI"},
    {"name": "Genpact", "keywords": ["genpact"], "career_url": None, "priority": "si_niche", "tier": "Niche SI"},
    {"name": "Eviden (Atos)", "keywords": ["eviden", "atos"], "career_url": None, "priority": "si_niche", "tier": "Niche SI"},

    # --- Pega Elite Partners (600+ consultants, award-winning) ---
    {"name": "Aaseya (YASH)", "keywords": ["aaseya", "yash technologies"], "career_url": "https://aaseya.com/careers/", "priority": "si_top", "tier": "Pega Elite"},
    {"name": "Maantic", "keywords": ["maantic"], "career_url": "https://maantic.com/careers/", "priority": "si_top", "tier": "Pega Elite"},
    {"name": "BlueRose Technologies", "keywords": ["bluerose", "blue rose"], "career_url": "https://www.bluerose-tech.com/careers/", "priority": "si_top", "tier": "Pega Elite"},

    # --- Pega-Focused Boutiques (high pay for niche expertise) ---
    {"name": "Inadev India", "keywords": ["inadev"], "career_url": "https://www.inadev.com/careers", "priority": "si_top", "tier": "Pega Boutique"},
    {"name": "EAI Systems", "keywords": ["eai systems", "eai"], "career_url": None, "priority": "si_niche", "tier": "Pega Boutique"},
    {"name": "Innova ESI", "keywords": ["innova esi", "innovaesi"], "career_url": None, "priority": "si_niche", "tier": "Pega Boutique"},
    {"name": "fusionAIx", "keywords": ["fusionaix"], "career_url": "https://www.fusionaix.com/careers/", "priority": "si_niche", "tier": "Pega Boutique"},
    {"name": "Eclatprime", "keywords": ["eclatprime"], "career_url": "https://eclatprime.com/careers/", "priority": "si_niche", "tier": "Pega Boutique"},
    {"name": "Xperteez Technology", "keywords": ["xperteez"], "career_url": None, "priority": "si_niche", "tier": "Pega Boutique"},
    {"name": "Uni-Pega", "keywords": ["uni-pega", "unipega"], "career_url": None, "priority": "si_niche", "tier": "Pega Boutique"},
    {"name": "Jyotirgamay Solutions", "keywords": ["jyotirgamay"], "career_url": None, "priority": "si_niche", "tier": "Pega Boutique"},
    {"name": "PruTech Solutions", "keywords": ["prutech solutions", "prutech"], "career_url": None, "priority": "si_niche", "tier": "Pega Boutique"},
    {"name": "Nous Infosystems", "keywords": ["nous infosystems", "nous info"], "career_url": None, "priority": "si_niche", "tier": "Pega Boutique"},

    # --- European / Global SIs with India Pega practices ---
    {"name": "Sopra Steria India", "keywords": ["sopra steria"], "career_url": None, "priority": "si_niche", "tier": "Global SI"},
    {"name": "Evoke Technologies", "keywords": ["evoke technologies", "evoke tech"], "career_url": "https://www.evoketechnologies.com/careers/", "priority": "si_niche", "tier": "Pega Boutique"},
    {"name": "Ness Digital Engineering", "keywords": ["ness digital", "ness "], "career_url": None, "priority": "si_niche", "tier": "Global SI"},
    {"name": "Merkle (dentsu)", "keywords": ["merkle"], "career_url": None, "priority": "si_niche", "tier": "Global SI"},

    # --- Mid-tier SIs with Pega practices ---
    {"name": "Sonata Software", "keywords": ["sonata software", "sonata"], "career_url": None, "priority": "si_niche", "tier": "Niche SI"},
    {"name": "Cyient", "keywords": ["cyient"], "career_url": None, "priority": "si_niche", "tier": "Niche SI"},
    {"name": "Horizontal", "keywords": ["horizontal "], "career_url": None, "priority": "si_niche", "tier": "Niche SI"},
    {"name": "Thryve Digital", "keywords": ["thryve digital"], "career_url": None, "priority": "si_niche", "tier": "Niche SI"},

    # --- Staffing / Contract firms (route to GCC roles) ---
    {"name": "Artech LLC", "keywords": ["artech"], "career_url": None, "priority": "si_niche", "tier": "Staffing"},
    {"name": "Collabera", "keywords": ["collabera"], "career_url": None, "priority": "si_niche", "tier": "Staffing"},
    {"name": "Mastech Holdings", "keywords": ["mastech"], "career_url": None, "priority": "si_niche", "tier": "Staffing"},
    {"name": "Quess Corp", "keywords": ["quess corp", "quess"], "career_url": None, "priority": "si_niche", "tier": "Staffing"},
    {"name": "Anlage Infotech", "keywords": ["anlage infotech", "anlage"], "career_url": None, "priority": "si_niche", "tier": "Staffing"},
    {"name": "People Prime Worldwide", "keywords": ["people prime"], "career_url": None, "priority": "si_niche", "tier": "Staffing"},
    {"name": "Scadea", "keywords": ["scadea"], "career_url": None, "priority": "si_niche", "tier": "Staffing"},
    {"name": "Ketan Software", "keywords": ["ketan software"], "career_url": None, "priority": "si_niche", "tier": "Staffing"},
]

# ---------------------------------------------------------------------------
# Remote / Global Companies — VERIFIED Pega users worldwide
# Every company here is confirmed via Pega customer stories, partner directory,
# real job postings, or PegaWorld presentations. No guesses.
#
# Resume fit annotations (Sathvik: CSSA, Kafka, REST/SOAP, case mgmt,
# collections, auto-finance, CPM, Constellation, DX API, 4yr exp):
#   "fit": "excellent" = direct match to core skills
#   "fit": "strong"    = good match, transferable domain
#   "fit": "possible"  = Pega role exists but domain/seniority gap
# ---------------------------------------------------------------------------
REMOTE_GLOBAL_COMPANIES = [
    # ===== PEGASYSTEMS (product company, HQ) =====
    {"name": "Pegasystems (US HQ)", "keywords": ["pegasystems", "pega"], "career_url": "https://www.pega.com/about/careers", "priority": "remote_top", "location": "Remote", "fit": "excellent"},

    # ===== US BANKING — Verified Pega customers (customer stories + real postings) =====
    # JPMorgan: Smart Investigate, CLM/KYC, payment investigations — pega.com customer
    {"name": "JPMorgan Chase (US)", "keywords": ["jpmorgan", "jpmorganchase", "jpmc"], "career_url": None, "priority": "remote_top", "location": "United States", "fit": "excellent"},
    # Wells Fargo: Smart Investigate, CDH, adaptive ML — pega.com customer
    {"name": "Wells Fargo (US)", "keywords": ["wells fargo"], "career_url": None, "priority": "remote_top", "location": "United States", "fit": "excellent"},
    # BofA: AML, CLM/KYC, disputes, Constellation — pega.com customer
    {"name": "Bank of America (US)", "keywords": ["bank of america", "bofa"], "career_url": None, "priority": "remote_top", "location": "United States", "fit": "excellent"},
    # Citi: CDH, CPM, case management — verified Pega user
    {"name": "Citi (US)", "keywords": ["citi", "citibank", "citigroup"], "career_url": None, "priority": "remote_top", "location": "United States", "fit": "excellent"},
    # First Citizens Bank: Pega CDH Specialist role posted $129-172K remote
    {"name": "First Citizens Bank (US)", "keywords": ["first citizens bank", "first citizens"], "career_url": None, "priority": "remote_top", "location": "United States", "fit": "excellent"},
    # Capital One: verified Pega platform user
    {"name": "Capital One (US)", "keywords": ["capital one"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # Goldman Sachs: Pega for operations workflows
    {"name": "Goldman Sachs (US)", "keywords": ["goldman sachs"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # Morgan Stanley: KYC, onboarding, Constellation — verified
    {"name": "Morgan Stanley (US)", "keywords": ["morgan stanley"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},

    # ===== US HEALTHCARE / INSURANCE — Verified Pega customers =====
    # UnitedHealth/Optum: massive Pega estate, OptumRx Prior Auth (verified remote postings)
    {"name": "UnitedHealth / Optum (US)", "keywords": ["unitedhealth", "uhg", "optum", "optumrx"], "career_url": None, "priority": "remote_top", "location": "United States", "fit": "excellent"},
    # Cigna/Evernorth: pega.com customer story — onboarding platform on Pega
    {"name": "Cigna / Evernorth (US)", "keywords": ["cigna", "evernorth"], "career_url": None, "priority": "remote_top", "location": "United States", "fit": "excellent"},
    # Highmark Health: verified remote Pega Software Engineer role, H1B sponsor
    {"name": "Highmark Health (US)", "keywords": ["highmark health", "highmark"], "career_url": None, "priority": "remote_top", "location": "United States", "fit": "excellent"},
    # Aflac: pega.com customer story — Customer Service, automation, AI
    {"name": "Aflac (US)", "keywords": ["aflac"], "career_url": None, "priority": "remote_top", "location": "United States", "fit": "excellent"},
    # Northwestern Mutual: PegaWorld 2025 presenter — Customer Service transformation
    {"name": "Northwestern Mutual (US)", "keywords": ["northwestern mutual"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # Prime Therapeutics: verified remote IT Manager Pega role — PBM/healthcare
    {"name": "Prime Therapeutics (US)", "keywords": ["prime therapeutics"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # Elevance/Anthem: verified Pega CDH and platform user
    {"name": "Elevance Health / Anthem (US)", "keywords": ["elevance health", "anthem"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # Primerica: pega.com customer — claims transformation
    {"name": "Primerica (US)", "keywords": ["primerica"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # Humana: known Pega user in healthcare
    {"name": "Humana (US)", "keywords": ["humana"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # MetLife: verified Pega CRM user (3060 customer list)
    {"name": "MetLife (US)", "keywords": ["metlife"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # Liberty Mutual: verified Pega user — insurance case management
    {"name": "Liberty Mutual (US)", "keywords": ["liberty mutual"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},

    # ===== US TELECOM — Verified Pega customers =====
    # Verizon: pega.com customer story — CDH, 90 omni-channel journeys, 1B txn/month
    {"name": "Verizon (US)", "keywords": ["verizon"], "career_url": None, "priority": "remote_top", "location": "United States", "fit": "excellent"},
    # T-Mobile: verified Pega CRM user
    {"name": "T-Mobile (US)", "keywords": ["t-mobile", "tmobile"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # Comcast: verified Pega user — customer service
    {"name": "Comcast (US)", "keywords": ["comcast", "xfinity"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},

    # ===== US TECHNOLOGY — Verified Pega customers =====
    # Dell Technologies: pega.com case study — Pega Customer Service + CDH,
    # 30,000 agents, 52 countries, Intelligent Routing, 98% SLA
    {"name": "Dell Technologies (US)", "keywords": ["dell technologies", "dell"], "career_url": "https://jobs.dell.com", "priority": "remote_top", "location": "United States", "fit": "excellent"},
    # S&P Global: multiple Pega developers, Pega Decisioning Consultant certified staff, Hyderabad+US
    {"name": "S&P Global (US)", "keywords": ["s&p global", "spglobal"], "career_url": "https://careers.spglobal.com", "priority": "remote_top", "location": "United States", "fit": "excellent"},

    # ===== US GOVERNMENT / DEFENSE — Pega is huge in federal =====
    # Accenture Federal Services: verified SSA remote role posted Aug 2026
    {"name": "Accenture Federal (US)", "keywords": ["accenture federal"], "career_url": None, "priority": "remote_top", "location": "United States", "fit": "excellent"},
    # Booz Allen Hamilton: known Pega federal partner
    {"name": "Booz Allen Hamilton (US)", "keywords": ["booz allen"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # Anakim Consulting: verified IRS Pega modernization program (remote)
    {"name": "Anakim Consulting (US Gov)", "keywords": ["anakim"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # SAIC: verified Pega federal contractor
    {"name": "SAIC (US)", "keywords": ["saic"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "possible"},
    # Maximus: verified Pega gov user
    {"name": "Maximus (US)", "keywords": ["maximus"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "possible"},

    # ===== US / GLOBAL SIs — Verified Pega practices =====
    # Accenture: Pega Global Elite Partner, verified US remote roles
    {"name": "Accenture (US Remote)", "keywords": ["accenture"], "career_url": None, "priority": "remote_top", "location": "United States", "fit": "excellent"},
    # Cognizant: Pega Elite Partner, Verizon implementation partner
    {"name": "Cognizant (US)", "keywords": ["cognizant"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "excellent"},
    # Capgemini: Pega Global Elite Partner (12x award winner)
    {"name": "Capgemini (US)", "keywords": ["capgemini"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # Deloitte: verified Pega partner, US roles
    {"name": "Deloitte (US)", "keywords": ["deloitte"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # EY: Pega Alliance partner, Northwestern Mutual presenter
    {"name": "EY (US)", "keywords": ["ey ", "ernst & young"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # EPAM: verified Pega practice, remote roles
    {"name": "EPAM (US Remote)", "keywords": ["epam"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},

    # ===== PEGA BOUTIQUES (US) — Premium contract rates $80-180/hr =====
    # Inadev: verified Pega Elite partner, US roles
    {"name": "Inadev (US)", "keywords": ["inadev"], "career_url": "https://www.inadev.com/careers", "priority": "remote_top", "location": "United States", "fit": "excellent"},
    # Areteans: Pega Global Elite partner, CDH CoE, 750+ specialists
    {"name": "Areteans (US/Global)", "keywords": ["areteans", "credera"], "career_url": None, "priority": "remote_top", "location": "United States", "fit": "excellent"},
    # Aaseya/YASH: Pega Elite partner, 400+ certified professionals
    {"name": "Aaseya (US)", "keywords": ["aaseya", "yash technologies"], "career_url": "https://aaseya.com/careers/", "priority": "remote_mid", "location": "United States", "fit": "excellent"},
    # Virtusa: known Pega practice
    {"name": "Virtusa (US)", "keywords": ["virtusa"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},

    # ===== UK — Verified Pega customers (pega.com customer stories) =====
    # HSBC: Smart Investigate, SWIFT, ISO 20022 — verified
    {"name": "HSBC (UK)", "keywords": ["hsbc"], "career_url": None, "priority": "remote_top", "location": "United Kingdom", "fit": "excellent"},
    # Barclays: Smart Investigate, Visa disputes, CDH — verified
    {"name": "Barclays (UK)", "keywords": ["barclays"], "career_url": None, "priority": "remote_top", "location": "United Kingdom", "fit": "excellent"},
    # Lloyds: pega.com customer story — 32,000 users, Pega Cloud, 30M customers
    {"name": "Lloyds Banking Group (UK)", "keywords": ["lloyds banking", "lloyds bank"], "career_url": None, "priority": "remote_top", "location": "United Kingdom", "fit": "excellent"},
    # NatWest: pega.com customer story — digital banking, cloud migration
    {"name": "NatWest Group (UK)", "keywords": ["natwest"], "career_url": None, "priority": "remote_top", "location": "United Kingdom", "fit": "excellent"},
    # Nationwide: pega.com customer story — mortgage ops, 10-month transformation
    {"name": "Nationwide (UK)", "keywords": ["nationwide building"], "career_url": None, "priority": "remote_mid", "location": "United Kingdom", "fit": "strong"},
    # BT Group: pega.com customer story — ordering/service management
    {"name": "BT Group (UK)", "keywords": ["bt group", "bt business"], "career_url": None, "priority": "remote_mid", "location": "United Kingdom", "fit": "strong"},
    # Vodafone: pega.com customer story — Blueprint, CDH, 340M customers
    {"name": "Vodafone (UK)", "keywords": ["vodafone"], "career_url": None, "priority": "remote_mid", "location": "United Kingdom", "fit": "excellent"},
    # Standard Chartered: verified Pega user — investigations, CDH
    {"name": "Standard Chartered (UK)", "keywords": ["standard chartered"], "career_url": None, "priority": "remote_mid", "location": "United Kingdom", "fit": "strong"},

    # ===== NETHERLANDS — Huge Pega market (verified active job postings) =====
    # ING: verified multiple Pega developer roles in Netherlands
    {"name": "ING Bank (Netherlands)", "keywords": ["ing bank", "ing group"], "career_url": None, "priority": "remote_top", "location": "Netherlands", "fit": "excellent"},
    # Rabobank: verified Pega developer roles in NL
    {"name": "Rabobank (Netherlands)", "keywords": ["rabobank"], "career_url": None, "priority": "remote_top", "location": "Netherlands", "fit": "excellent"},
    # ABN AMRO: verified Pega roles in Amsterdam
    {"name": "ABN AMRO (Netherlands)", "keywords": ["abn amro"], "career_url": None, "priority": "remote_mid", "location": "Netherlands", "fit": "strong"},
    # BPM Company: European Pega Partner, Utrecht — authorized training partner
    {"name": "BPM Company (Netherlands)", "keywords": ["bpm company"], "career_url": "https://www.bpmcompany.eu/en/", "priority": "remote_mid", "location": "Netherlands", "fit": "excellent"},
    # Dutch Government (NCG/RijksZaak): verified CSSA roles in Groningen
    {"name": "Dutch Government - RijksZaak (NL)", "keywords": ["rijkszaak", "ncg"], "career_url": None, "priority": "remote_mid", "location": "Netherlands", "fit": "strong"},

    # ===== BELGIUM — Verified Pega customers =====
    # Proximus: pega.com customer story — B2B modernization, AI-powered design
    {"name": "Proximus (Belgium)", "keywords": ["proximus"], "career_url": None, "priority": "remote_mid", "location": "Belgium", "fit": "strong"},
    # Telenet: pega.com customer — brand loyalty, CDH
    {"name": "Telenet (Belgium)", "keywords": ["telenet"], "career_url": None, "priority": "remote_mid", "location": "Belgium", "fit": "strong"},

    # ===== GERMANY — Verified Pega market (active job postings) =====
    # Sopra Steria Germany: verified Pega Developer role, remote DE
    {"name": "Sopra Steria (Germany)", "keywords": ["sopra steria"], "career_url": None, "priority": "remote_mid", "location": "Germany", "fit": "strong"},
    # CONET: verified Low Code/Pega Senior role, multiple German cities + remote
    {"name": "CONET (Germany)", "keywords": ["conet"], "career_url": None, "priority": "remote_mid", "location": "Germany", "fit": "strong"},
    # Senacor: verified Pega System Architect role, Stuttgart, remote available
    {"name": "Senacor (Germany)", "keywords": ["senacor"], "career_url": None, "priority": "remote_mid", "location": "Germany", "fit": "strong"},
    # Deutsche Bank: verified Pega CLM/KYC — also UK offices
    {"name": "Deutsche Bank (Germany/UK)", "keywords": ["deutsche bank"], "career_url": None, "priority": "remote_mid", "location": "Germany", "fit": "excellent"},

    # ===== NORDICS — Verified Pega market =====
    # Nordea: verified Pega Lead Architect role Helsinki — CLM, Financial Crime
    {"name": "Nordea (Finland/Nordics)", "keywords": ["nordea"], "career_url": None, "priority": "remote_top", "location": "Finland", "fit": "excellent"},
    # Swedish Major Bank (via Academic Work): verified Pega Developer role, long-term
    {"name": "Swedish Banks - Pega (Sweden)", "keywords": ["pega developer sweden", "swedish bank"], "career_url": None, "priority": "remote_mid", "location": "Sweden", "fit": "strong"},
    # Denmark: verified Pega LSA contract role (Belmont Lavan), CLM application
    {"name": "Pega CLM Denmark (Contract)", "keywords": ["pega clm denmark"], "career_url": None, "priority": "remote_mid", "location": "Denmark", "fit": "strong"},

    # ===== FRANCE / SOUTHERN EUROPE — Verified =====
    # BNP Paribas: verified Pega user — banking workflows, SWIFT
    {"name": "BNP Paribas (France)", "keywords": ["bnp paribas"], "career_url": None, "priority": "remote_mid", "location": "France", "fit": "strong"},
    # Societe Generale: verified Pega user
    {"name": "Societe Generale (France)", "keywords": ["societe generale", "socgen"], "career_url": None, "priority": "remote_mid", "location": "France", "fit": "strong"},
    # Santander: pega.com customer story — legal ops, GenAI
    {"name": "Santander (Spain/Europe)", "keywords": ["santander", "banco santander"], "career_url": None, "priority": "remote_mid", "location": "Spain", "fit": "strong"},
    # Zurich Insurance: pega.com customer story — underwriting transformation
    {"name": "Zurich Insurance (Switzerland)", "keywords": ["zurich insurance", "zurich santander"], "career_url": None, "priority": "remote_mid", "location": "Switzerland", "fit": "strong"},
    # AXA: verified Pega user — insurance
    {"name": "AXA (France/Europe)", "keywords": ["axa"], "career_url": None, "priority": "remote_mid", "location": "France", "fit": "strong"},
    # Allianz: verified Pega user — insurance AGCS
    {"name": "Allianz (Germany/Europe)", "keywords": ["allianz"], "career_url": None, "priority": "remote_mid", "location": "Germany", "fit": "strong"},

    # ===== EUROPEAN PEGA BOUTIQUES / SIs (visa-sponsor friendly) =====
    # Capgemini Financial Services Benelux: verified Pega CSSA/LSA roles in NL
    {"name": "Capgemini FS Benelux", "keywords": ["capgemini"], "career_url": None, "priority": "remote_mid", "location": "Netherlands", "fit": "excellent"},
    # A2G Technologies NL: verified CSSA role, visa sponsorship offered
    {"name": "A2G Technologies (Netherlands)", "keywords": ["a2g consulting", "a2g technologies"], "career_url": None, "priority": "remote_mid", "location": "Netherlands", "fit": "excellent"},
    # Avance Consulting NL: verified Pega CSSA roles Amsterdam
    {"name": "Avance Consulting (Netherlands)", "keywords": ["avance consulting"], "career_url": None, "priority": "remote_mid", "location": "Netherlands", "fit": "excellent"},
    # WLG Netherlands: verified CSSA role Groningen
    {"name": "WLG (Netherlands)", "keywords": ["wlg", "wlgroup"], "career_url": "https://career.wlgroup.eu/", "priority": "remote_mid", "location": "Netherlands", "fit": "excellent"},
    # AIDA Recruitment: verified Europe-wide CSSA roles (remote from EU)
    {"name": "AIDA Recruitment (Europe)", "keywords": ["aida recruitment", "aida projektai"], "career_url": None, "priority": "remote_mid", "location": "Europe", "fit": "excellent"},
    # Next Ventures: verified European Pega LSA/CSSA contract roles
    {"name": "Next Ventures (Europe)", "keywords": ["next ventures"], "career_url": "https://next-ventures.com/", "priority": "remote_mid", "location": "Europe", "fit": "strong"},
    # Accenture Europe: Pega Global Elite Partner, EU Pega Practice
    {"name": "Accenture (Europe)", "keywords": ["accenture"], "career_url": None, "priority": "remote_mid", "location": "Europe", "fit": "excellent"},
    # EY Europe: Pega Alliance, Nils Müller-Sheffer leads EU practice
    {"name": "EY (Europe)", "keywords": ["ey ", "ernst & young"], "career_url": None, "priority": "remote_mid", "location": "Europe", "fit": "strong"},

    # ===== VODAFONE GROUP (multiple countries, massive Pega estate) =====
    # Vodafone Greece: pega.com customer story — CDH, real-time personalization
    {"name": "Vodafone Greece", "keywords": ["vodafone greece"], "career_url": None, "priority": "remote_mid", "location": "Greece", "fit": "strong"},

    # ===== AUSTRALIA — Verified Pega customers =====
    # ANZ: verified Pega customer, CSSA contract roles (AU citizenship often required)
    {"name": "ANZ Bank (Australia)", "keywords": ["anz bank", "anz"], "career_url": None, "priority": "remote_mid", "location": "Australia", "fit": "excellent"},
    # CBA: verified massive Pega CDH estate, 200 ML models
    {"name": "CBA (Australia)", "keywords": ["commonwealth bank", "cba"], "career_url": None, "priority": "remote_mid", "location": "Australia", "fit": "excellent"},
    # NAB: verified Pega customer
    {"name": "NAB (Australia)", "keywords": ["national australia bank", "nab"], "career_url": None, "priority": "remote_mid", "location": "Australia", "fit": "strong"},
    # Telstra: verified Pega customer
    {"name": "Telstra (Australia)", "keywords": ["telstra"], "career_url": None, "priority": "remote_mid", "location": "Australia", "fit": "strong"},
    # QBE Insurance: verified Pega CRM customer (3060 customer list)
    {"name": "QBE Insurance (Australia)", "keywords": ["qbe insurance", "qbe"], "career_url": None, "priority": "remote_mid", "location": "Australia", "fit": "strong"},
    # Suncorp: verified Pega customer
    {"name": "Suncorp (Australia)", "keywords": ["suncorp"], "career_url": None, "priority": "remote_mid", "location": "Australia", "fit": "strong"},
    # NCS Australia: verified Pega Developer contract roles (Brisbane)
    {"name": "NCS Australia", "keywords": ["ncs australia"], "career_url": None, "priority": "remote_mid", "location": "Australia", "fit": "strong"},

    # ===== SINGAPORE — Verified Pega market =====
    # DBS Bank: verified Pega CRM customer
    {"name": "DBS Bank (Singapore)", "keywords": ["dbs bank"], "career_url": None, "priority": "remote_mid", "location": "Singapore", "fit": "excellent"},
    # Great Eastern: pega.com customer story — Customer Service, 16M policyholders
    {"name": "Great Eastern (Singapore)", "keywords": ["great eastern"], "career_url": None, "priority": "remote_mid", "location": "Singapore", "fit": "strong"},
    # Synpulse: verified Pega Senior Consultant role SGD 140-190K
    {"name": "Synpulse (Singapore)", "keywords": ["synpulse"], "career_url": None, "priority": "remote_mid", "location": "Singapore", "fit": "strong"},

    # ===== TURKEY — Verified =====
    # Akbank: verified Pega CDH implementation via Adqura
    {"name": "Akbank (Turkey)", "keywords": ["akbank"], "career_url": None, "priority": "remote_mid", "location": "Turkey", "fit": "strong"},

    # ===== US INSURANCE (additional verified) — pega.com case studies =====
    # New York Life: PegaWorld 2025 — Pega Customer Service for claims, 10+ implementations with Virtusa
    {"name": "New York Life (US)", "keywords": ["new york life"], "career_url": None, "priority": "remote_top", "location": "United States", "fit": "excellent"},
    # USAA: verified notable Pega client (ReadyContacts, 7/10 top US banks use Pega)
    {"name": "USAA (US)", "keywords": ["usaa"], "career_url": None, "priority": "remote_top", "location": "United States", "fit": "excellent"},
    # Unum Group: PegaWorld 2026 KEYNOTE — COBOL-to-Cloud modernization, Pega Blueprint + AWS Transform
    {"name": "Unum Group (US)", "keywords": ["unum"], "career_url": None, "priority": "remote_top", "location": "United States", "fit": "excellent"},
    # CSAA Insurance: pega.com case study — Pega Customer Service, AAA members, 5M calls/year
    {"name": "CSAA Insurance (US)", "keywords": ["csaa insurance", "csaa"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # Farmers Insurance: pega.com case study — 14-minute complex quotes, doubled market share
    {"name": "Farmers Insurance (US)", "keywords": ["farmers insurance"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # Allied Solutions: PegaWorld 2026 presenter — Contact Center, Insurance Billing
    {"name": "Allied Solutions (US)", "keywords": ["allied solutions"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # Church Mutual Insurance: pega.com case study — $2.5M annual savings
    {"name": "Church Mutual Insurance (US)", "keywords": ["church mutual"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "possible"},
    # Great American Insurance: pega.com case study — annuity servicing, 7-min withdrawals
    {"name": "Great American Insurance (US)", "keywords": ["great american insurance"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "possible"},
    # Delta Dental: verified notable Pega client
    {"name": "Delta Dental (US)", "keywords": ["delta dental"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # Transamerica: verified notable Pega client
    {"name": "Transamerica (US)", "keywords": ["transamerica"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},

    # ===== US HEALTHCARE (additional verified) =====
    # CVS Health: Landbase verified Pega Platform user
    {"name": "CVS Health (US)", "keywords": ["cvs health"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # Molina Healthcare: pega.com case study — 22 states, 5M+ members, $40M annual savings
    {"name": "Molina Healthcare (US)", "keywords": ["molina healthcare", "molina"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # Blue Cross Blue Shield: verified Pega user (multiple BCBS entities)
    {"name": "Blue Cross Blue Shield (US)", "keywords": ["blue cross", "bcbs"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # Walgreens: verified notable Pega client
    {"name": "Walgreens (US)", "keywords": ["walgreens"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "possible"},

    # ===== US TELECOM (additional verified) =====
    # AT&T: verified notable Pega client (top 4 US telcos use Pega)
    {"name": "AT&T (US)", "keywords": ["at&t"], "career_url": None, "priority": "remote_top", "location": "United States", "fit": "strong"},

    # ===== US AUTOMOTIVE / MANUFACTURING (verified pega.com case studies) =====
    # General Motors / OnStar: pega.com case study — CDH, 12M connected vehicles, 1M decisions/hour
    {"name": "General Motors (US)", "keywords": ["general motors", "gm "], "career_url": None, "priority": "remote_top", "location": "United States", "fit": "excellent"},
    # Toyota: pega.com case study — QIMS quality management, 300% faster resolution
    {"name": "Toyota (US)", "keywords": ["toyota"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # Procter & Gamble: verified notable Pega client
    {"name": "Procter & Gamble (US)", "keywords": ["procter gamble", "p&g"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "possible"},
    # Coca-Cola: Wikipedia verified Pega client
    {"name": "Coca-Cola (US)", "keywords": ["coca-cola", "coca cola"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "possible"},

    # ===== US DEFENSE (additional verified) =====
    # Lockheed Martin: verified notable Pega client
    {"name": "Lockheed Martin (US)", "keywords": ["lockheed martin"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},
    # General Dynamics IT: verified Pega federal contractor
    {"name": "General Dynamics IT (US)", "keywords": ["general dynamics", "gdit"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},

    # ===== US LOGISTICS =====
    # FedEx: verified notable Pega client
    {"name": "FedEx (US)", "keywords": ["fedex"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "possible"},

    # ===== US RETAIL / HOSPITALITY =====
    # Macy's: verified notable Pega client
    {"name": "Macy's (US)", "keywords": ["macys", "macy's"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "possible"},
    # Target: ReadyContacts verified Pega user
    {"name": "Target (US)", "keywords": ["target"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "possible"},
    # Marriott: verified notable Pega client
    {"name": "Marriott (US)", "keywords": ["marriott"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "possible"},
    # Caesars Entertainment: ReadyContacts verified Pega user
    {"name": "Caesars Entertainment (US)", "keywords": ["caesars entertainment", "caesars"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "possible"},

    # ===== US TECHNOLOGY =====
    # InterSystems: PegaWorld 2025 presenter — Pega Sales Automation
    {"name": "InterSystems (US)", "keywords": ["intersystems"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "strong"},

    # ===== US PHARMA =====
    # Merck: verified notable Pega client
    {"name": "Merck (US)", "keywords": ["merck"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "possible"},
    # Johnson & Johnson: verified notable Pega client
    {"name": "Johnson & Johnson (US)", "keywords": ["johnson & johnson", "j&j"], "career_url": None, "priority": "remote_mid", "location": "United States", "fit": "possible"},

    # ===== GERMANY (additional verified) =====
    # Deutsche Telekom: pega.com featured case study — CX transformation with Blueprint
    {"name": "Deutsche Telekom (Germany)", "keywords": ["deutsche telekom"], "career_url": None, "priority": "remote_mid", "location": "Germany", "fit": "strong"},
    # Siemens (Global): 3 pega.com case studies, PegaWorld 2025 — 80-90% efficiency gain, 20+ projects
    {"name": "Siemens (Germany)", "keywords": ["siemens"], "career_url": None, "priority": "remote_top", "location": "Germany", "fit": "excellent"},

    # ===== SPAIN (additional verified) =====
    # BBVA: verified notable Pega client (banking)
    {"name": "BBVA (Spain)", "keywords": ["bbva"], "career_url": None, "priority": "remote_mid", "location": "Spain", "fit": "strong"},

    # ===== FRANCE (additional verified) =====
    # Groupama: PegaWorld 2025 presenter — customer relationship transformation
    {"name": "Groupama (France)", "keywords": ["groupama"], "career_url": None, "priority": "remote_mid", "location": "France", "fit": "strong"},

    # ===== UK (additional verified) =====
    # Sky: ReadyContacts verified Pega user (UK telecom)
    {"name": "Sky (UK)", "keywords": ["sky uk", "sky "], "career_url": None, "priority": "remote_mid", "location": "United Kingdom", "fit": "strong"},
    # Centrica: Wikipedia verified Pega client (British Gas parent)
    {"name": "Centrica (UK)", "keywords": ["centrica"], "career_url": None, "priority": "remote_mid", "location": "United Kingdom", "fit": "strong"},
    # Bupa: pega.com case study — CDH, health insurance + dental + optical + aged care
    {"name": "Bupa (UK)", "keywords": ["bupa"], "career_url": None, "priority": "remote_mid", "location": "United Kingdom", "fit": "strong"},
    # NHS 24: pega.com case study — urgent care modernization, Scotland's 5.5M citizens
    {"name": "NHS 24 (Scotland)", "keywords": ["nhs 24", "nhs24"], "career_url": None, "priority": "remote_mid", "location": "United Kingdom", "fit": "possible"},

    # ===== AUSTRALIA (additional verified) =====
    # Westpac: ReadyContacts verified Pega user (major AU bank)
    {"name": "Westpac (Australia)", "keywords": ["westpac"], "career_url": None, "priority": "remote_mid", "location": "Australia", "fit": "strong"},
    # Toyota Finance Australia: pega.com case study — loan origination, 70% e-sign
    {"name": "Toyota Finance Australia", "keywords": ["toyota finance australia"], "career_url": None, "priority": "remote_mid", "location": "Australia", "fit": "strong"},
    # Bupa Australia: pega.com case study — CDH, health insurance
    {"name": "Bupa Australia", "keywords": ["bupa australia"], "career_url": None, "priority": "remote_mid", "location": "Australia", "fit": "strong"},

    # ===== BRAZIL (verified pega.com case studies) =====
    # Bradesco: pega.com case study — wholesale credit modernization
    {"name": "Bradesco (Brazil)", "keywords": ["bradesco"], "career_url": None, "priority": "remote_mid", "location": "Brazil", "fit": "strong"},
    # Itaú Unibanco: ReadyContacts verified Pega user
    {"name": "Itaú Unibanco (Brazil)", "keywords": ["itau", "itaú"], "career_url": None, "priority": "remote_mid", "location": "Brazil", "fit": "strong"},

    # ===== CATCH-ALL BROAD SEARCHES — for discovering new companies =====
    {"name": "Remote Pega Jobs (Worldwide)", "keywords": ["pega"], "career_url": None, "priority": "remote_top", "location": "Remote", "fit": "excellent"},
    {"name": "Pega Jobs USA (Broad)", "keywords": ["pega"], "career_url": None, "priority": "remote_top", "location": "United States", "fit": "excellent"},
    {"name": "Pega Jobs Europe (Broad)", "keywords": ["pega"], "career_url": None, "priority": "remote_top", "location": "Europe", "fit": "excellent"},
    {"name": "Pega Jobs UK (Broad)", "keywords": ["pega"], "career_url": None, "priority": "remote_top", "location": "United Kingdom", "fit": "excellent"},
    {"name": "Pega Jobs Netherlands (Broad)", "keywords": ["pega"], "career_url": None, "priority": "remote_top", "location": "Netherlands", "fit": "excellent"},
]


# ---------------------------------------------------------------------------
# Job History tracker  (persists between runs to detect NEW jobs)
# ---------------------------------------------------------------------------
class JobHistory:
    """Tracks previously seen job IDs to highlight new ones."""

    def __init__(self, path: Path):
        self.path = path
        self.data: dict = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    return json.load(fh)
            except (json.JSONDecodeError, IOError):
                log.warning("Corrupted history file, starting fresh")
        return {"seen_ids": {}, "last_run": None}

    def save(self):
        self.data["last_run"] = datetime.now().isoformat()
        # Prune entries older than 90 days to keep file small
        cutoff = (datetime.now() - timedelta(days=90)).isoformat()
        self.data["seen_ids"] = {
            k: v for k, v in self.data["seen_ids"].items() if v > cutoff
        }
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=2)

    def is_new(self, job_id: str) -> bool:
        return job_id not in self.data["seen_ids"]

    def mark_seen(self, job_id: str):
        self.data["seen_ids"][job_id] = datetime.now().isoformat()

    @property
    def last_run(self) -> Optional[str]:
        return self.data.get("last_run")


# ---------------------------------------------------------------------------
# Job data model
# ---------------------------------------------------------------------------
class Job:
    def __init__(self, title, company, location, source, url, snippet="", posted=""):
        self.title = title
        self.company = company
        self.location = location
        self.source = source
        self.url = canonical_url(url)
        self.snippet = snippet
        self.posted = posted
        # Unique ID based on title + company + url
        self.uid = job_identity(title, company, self.url)
        self.is_new = False

    def to_dict(self):
        return {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "source": self.source,
            "url": self.url,
            "snippet": self.snippet,
            "posted": self.posted,
            "uid": self.uid,
            "verification_status": "candidate",
            "is_new": self.is_new,
        }


# ---------------------------------------------------------------------------
# HTTP helper with retries and rate-limiting
# ---------------------------------------------------------------------------
_last_request_time: dict[str, float] = {}
FETCH_AUDIT = []
LAST_SCAN_DIAGNOSTICS = {}

def audited_get(url, **kwargs):
    domain = urllib.parse.urlparse(url).netloc
    delay = DELAY_BETWEEN_REQUESTS - (time.time() - _last_request_time.get(domain, 0))
    if delay > 0:
        time.sleep(delay)
    try:
        response = requests.get(url, **kwargs)
        _last_request_time[domain] = time.time()
        FETCH_AUDIT.append({"url": url, "http_status": response.status_code})
        return response
    except requests.RequestException as exc:
        FETCH_AUDIT.append({"url": url, "error": str(exc)[:180]})
        raise


def fetch(url: str, params: dict = None) -> Optional[str]:
    """GET a URL with rate limiting and retries. Returns HTML or None."""
    domain = urllib.parse.urlparse(url).netloc
    # Rate-limit per domain
    now = time.time()
    last = _last_request_time.get(domain, 0)
    wait = DELAY_BETWEEN_REQUESTS - (now - last)
    if wait > 0:
        time.sleep(wait)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = audited_get(
                url, headers=HEADERS, params=params,
                timeout=REQUEST_TIMEOUT, allow_redirects=True,
                verify=SSL_VERIFY,
            )
            _last_request_time[domain] = time.time()
            if resp.status_code == 200:
                return resp.text
            if resp.status_code == 429:
                log.warning("Rate limited on %s, backing off...", domain)
                time.sleep(10 * attempt)
                continue
            log.debug("HTTP %d from %s", resp.status_code, url[:80])
            return None
        except requests.RequestException as exc:
            log.debug("Request failed (%s): %s", url[:60], exc)
            if attempt < MAX_RETRIES:
                time.sleep(3 * attempt)
    return None


# ---------------------------------------------------------------------------
# Source: Naukri.com  (try JSON API first, then HTML fallback)
# ---------------------------------------------------------------------------
def search_naukri(company: dict, location: str = "india") -> list[Job]:
    """Search Naukri.com for Pega jobs at a company."""
    jobs = []
    keyword = company["keywords"][0]

    # Strategy 1: Naukri JSON API (v4 endpoint, more permissive)
    for api_ver in ["v4", "v3"]:
        query = f"pega {keyword}"
        encoded = urllib.parse.quote_plus(query)
        loc_slug = location.lower().replace(" ", "-")
        api_url = (
            f"https://www.naukri.com/jobapi/{api_ver}/search"
            f"?noOfResults=20&urlType=search_by_keyword&searchType=adv"
            f"&keyword={encoded}&location={loc_slug}&pageNo=1&seoKey=pega-{keyword.replace(' ', '-')}-jobs-in-{loc_slug}"
        )
        try:
            resp = audited_get(
                api_url,
                headers={
                    **HEADERS,
                    "appid": "109",
                    "systemid": "109",
                    "Accept": "application/json",
                    "gid": "LOCATION,INDUSTRY,EDUCATION,FAREA_ROLE",
                    "Referer": f"https://www.naukri.com/pega-{keyword.replace(' ', '-')}-jobs-in-{loc_slug}",
                },
                timeout=REQUEST_TIMEOUT,
                verify=SSL_VERIFY,
            )
            _last_request_time["www.naukri.com"] = time.time()
            if resp.status_code == 200:
                try:
                    data = resp.json()
                except ValueError:
                    FETCH_AUDIT.append({"url": api_url, "error": "Invalid JSON response"})
                    continue
                for item in data.get("jobDetails", []):
                    title = item.get("title", "")
                    tags = " ".join(item.get("tagsAndSkills", "").split(","))
                    desc = item.get("jobDescription", "")[:300]
                    # Check title + tags + description for Pega relevance
                    combined = f"{title} {tags} {desc}".lower()
                    if not _is_pega_relevant(combined):
                        continue
                    loc_val = "India"
                    placeholders = item.get("placeholders", [])
                    if placeholders and isinstance(placeholders, list):
                        loc_val = placeholders[0].get("value", "India") if placeholders[0] else "India"
                    jd_url = item.get("jdURL", "")
                    if jd_url and not jd_url.startswith("http"):
                        jd_url = "https://www.naukri.com" + jd_url
                    job = Job(
                        title=title,
                        company=item.get("companyName", ""),
                        location=loc_val,
                        source="Naukri",
                        url=jd_url,
                        snippet=item.get("jobDescription", "")[:200],
                        posted=item.get("footerPlaceholderLabel", ""),
                    )
                    jobs.append(job)
                if jobs:
                    break
        except Exception as exc:
            FETCH_AUDIT.append({"url": api_url, "error": str(exc)[:180]})
            log.debug("Naukri API %s error for %s: %s", api_ver, company["name"], exc)
        time.sleep(1)

    # Strategy 2: also try a broad "pega" search (catches more)
    if not jobs:
        try:
            broad_url = (
                "https://www.naukri.com/jobapi/v3/search"
                "?noOfResults=25&urlType=search_by_keyword&searchType=adv"
                f"&keyword=pega&location={location.lower()}&pageNo=1&companyName={urllib.parse.quote_plus(keyword)}"
            )
            resp = audited_get(
                broad_url,
                headers={**HEADERS, "appid": "109", "systemid": "109", "Accept": "application/json"},
                timeout=REQUEST_TIMEOUT,
                verify=SSL_VERIFY,
            )
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    for item in data.get("jobDetails", []):
                        title = item.get("title", "")
                        tags = item.get("tagsAndSkills", "")
                        desc = item.get("jobDescription", "")[:300]
                        if _is_pega_relevant(f"{title} {tags} {desc}"):
                            jd_url = item.get("jdURL", "")
                            if jd_url and not jd_url.startswith("http"):
                                jd_url = "https://www.naukri.com" + jd_url
                            job = Job(
                                title=title,
                                company=item.get("companyName", ""),
                                location="India",
                                source="Naukri",
                                url=jd_url,
                                snippet=item.get("jobDescription", "")[:200],
                            )
                            jobs.append(job)
                except ValueError:
                    FETCH_AUDIT.append({"url": broad_url, "error": "Invalid JSON response"})
        except Exception as exc:
            FETCH_AUDIT.append({"url": broad_url, "error": str(exc)[:180]})
    return jobs


# ---------------------------------------------------------------------------
# JD deep-check: fetch a job page and look for Pega keywords in the body
# Used when the title is generic (e.g. "Principal Architect") — we fetch
# the actual JD to see if Pega/PRPC/CDH is mentioned in the description.
# ---------------------------------------------------------------------------
_jd_check_cache: dict[str, bool] = {}  # url -> is_pega_relevant
_JD_CHECKS_PER_SEARCH = 5  # cap deep-checks per search to avoid hammering


def _fetch_jd_pega_check(url: str) -> bool:
    """Fetch a job page and check if JD text mentions Pega keywords."""
    cache_key = canonical_url(url)
    if not cache_key:
        return False
    if cache_key in _jd_check_cache:
        return _jd_check_cache[cache_key]

    try:
        html = fetch(cache_key)
        if not html:
            _jd_check_cache[cache_key] = False
            return False

        soup = BeautifulSoup(html, "lxml")
        # Only inspect the actual role description. Navigation, company branding,
        # search results and recommended jobs are not evidence for this role.
        descriptions = []

        def collect_job_postings(value):
            if isinstance(value, list):
                for item in value:
                    collect_job_postings(item)
            elif isinstance(value, dict):
                kinds = value.get("@type", [])
                if isinstance(kinds, str):
                    kinds = [kinds]
                if "JobPosting" in kinds and isinstance(value.get("description"), str):
                    descriptions.append(BeautifulSoup(value["description"], "lxml").get_text(" ", strip=True))
                if "@graph" in value:
                    collect_job_postings(value["@graph"])

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                collect_job_postings(json.loads(script.string or script.get_text()))
            except (ValueError, TypeError):
                continue
        # Multiple JobPosting objects usually describe a listing page, not one JD.
        if len(descriptions) > 1:
            FETCH_AUDIT.append({"url": cache_key, "error": "Multiple job descriptions; individual role could not be identified"})
            return False
        if not descriptions:
            jd_el = soup.select_one(
                "div.show-more-less-html__markup, div.description__text, "
                "div.jobsearch-jobDescriptionText, div#jobDescriptionText, "
                "div.job-description, section.job-description, "
                '[itemtype="https://schema.org/JobPosting"] [itemprop="description"], '
                '[itemtype="http://schema.org/JobPosting"] [itemprop="description"]'
            )
            if jd_el:
                descriptions.append(jd_el.get_text(" ", strip=True))
        if not descriptions:
            FETCH_AUDIT.append({"url": cache_key, "error": "No supported role-description markup; relevance could not be checked"})
            return False

        result = _is_pega_relevant(descriptions[0])
        _jd_check_cache[cache_key] = result
        if result:
            log.info("JD deep-check PASS for: %s", url[:80])
        else:
            log.debug("JD deep-check FAIL for: %s", url[:80])
        return result
    except Exception as exc:
        FETCH_AUDIT.append({"url": cache_key, "error": "JD parse/check failed: " + str(exc)[:140]})
        log.debug("JD deep-check error for %s: %s", url[:60], exc)
        _jd_check_cache[cache_key] = False
        return False


# ---------------------------------------------------------------------------
# Source: LinkedIn Jobs (public API endpoint)
# ---------------------------------------------------------------------------
def _parse_linkedin_cards(html: str, company_name: str, default_location: str = "India", target_company: Optional[dict] = None) -> list[Job]:
    """Parse LinkedIn HTML cards into Job objects.
    
    Two-pass filtering:
    1. Require the listed employer to match a supplied named target
    2. If title has a Pega keyword → KEEP immediately
    3. Otherwise fetch a unique job URL and inspect the role description
    4. Keep only roles whose description contains a Pega technology keyword
    """
    jobs = []
    pending_jd_check = []  # (job, url) pairs that need JD deep-check
    seen_urls = set()
    soup = BeautifulSoup(html, "lxml")
    for card in soup.select("li, div.base-card, div.job-search-card"):
        title_el = card.select_one(
            "h3.base-search-card__title, h3.result-card__title, "
            "h3[class*='title'], a.base-card__full-link"
        )
        comp_el = card.select_one(
            "h4.base-search-card__subtitle, h4.result-card__subtitle, "
            "a[class*='company'], h4[class*='subtitle']"
        )
        loc_el = card.select_one(
            "span.job-search-card__location, span[class*='location']"
        )
        link_el = card.select_one("a.base-card__full-link, a[class*='base-card']")

        if not title_el:
            continue
        title_text = title_el.get_text(strip=True)
        comp_text = comp_el.get_text(strip=True) if comp_el else ""
        if not comp_text or (target_company is not None and not employer_matches(comp_text, target_company)):
            continue

        href = ""
        if link_el:
            href = link_el.get("href", "")
        elif title_el.name == "a":
            href = title_el.get("href", "")
        href = canonical_url(href)
        # Nested li/base-card/job-search-card elements describe the same job.
        # Deduplicate before spending the limited JD request budget.
        if not href or href in seen_urls:
            continue
        seen_urls.add(href)
        loc_text = loc_el.get_text(strip=True) if loc_el else default_location

        job = Job(
            title=title_text,
            company=comp_text,
            location=loc_text,
            source="LinkedIn",
            url=href,
        )

        # Company branding alone does not establish a Pega technology role.
        combined = title_text.lower()
        if _is_pega_relevant(combined):
            jobs.append(job)
        else:
            # Queue for JD deep-check (will fetch the actual job page)
            pending_jd_check.append((job, href))

    # Pass 2: for generic-titled jobs, fetch the JD page and check description
    # Cap the number of deep-checks to avoid hammering job sites
    checked = 0
    for job, url in pending_jd_check:
        if checked >= _JD_CHECKS_PER_SEARCH:
            log.debug("JD deep-check cap reached, skipping remaining %d",
                      len(pending_jd_check) - checked)
            break
        if _fetch_jd_pega_check(url):
            jobs.append(job)
        checked += 1

    return jobs


def search_linkedin(company: dict, location: str = "India") -> list[Job]:
    """Search LinkedIn public job listings via their public jobs API."""
    jobs = []
    keyword = company["keywords"][0]

    # Try multiple Pega-related queries to catch generic-titled roles
    queries = [f"pega {keyword}", f"pega developer {keyword}", f"PRPC {keyword}"]
    seen_urls = set()

    for query in queries:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={encoded}&location={location}&start=0"
        html = fetch(url)
        if not html:
            url = f"https://www.linkedin.com/jobs/search/?keywords={encoded}&location={location}"
            html = fetch(url)
        if not html:
            continue

        found = _parse_linkedin_cards(html, company["name"], location, target_company=company)
        for job in found:
            if job.url not in seen_urls:
                seen_urls.add(job.url)
                jobs.append(job)
        # Don't hammer LinkedIn — only try extra queries if first found nothing
        if jobs:
            break
        time.sleep(DELAY_BETWEEN_REQUESTS)

    return jobs


# ---------------------------------------------------------------------------
# Source: Indeed India
# ---------------------------------------------------------------------------
def search_indeed(company: dict, location: str = "India") -> list[Job]:
    """Search Indeed for Pega jobs. Uses indeed.co.in for India, indeed.com for US/global."""
    jobs = []
    keyword = company["keywords"][0]
    query = f"pega {keyword}"
    encoded = urllib.parse.quote_plus(query)

    # Pick the right Indeed domain based on location
    if location.lower() in ("india", ""):
        base_domain = "https://www.indeed.co.in"
        loc_param = "India"
    elif location.lower() in ("united states", "us", "usa", "remote"):
        base_domain = "https://www.indeed.com"
        loc_param = "Remote" if location.lower() == "remote" else "United States"
    else:
        base_domain = "https://www.indeed.com"
        loc_param = location

    url = f"{base_domain}/jobs?q={encoded}&l={urllib.parse.quote_plus(loc_param)}"
    html = fetch(url)
    if not html:
        return jobs

    soup = BeautifulSoup(html, "lxml")
    pending_jd_check = []  # (job, url) pairs needing JD deep-check
    seen_urls = set()
    for card in soup.select(
        "div.job_seen_beacon, div.jobsearch-SerpJobCard, "
        "td.resultContent, div.resultContent, div[class*='result']"
    ):
        title_el = card.select_one(
            "h2.jobTitle a, a[data-jk], h2 a, a.jcs-JobTitle, "
            "span[id*='jobTitle'], a[class*='JobTitle']"
        )
        comp_el = card.select_one(
            "span[data-testid='company-name'], span.companyName, "
            "span.company, a[data-tn-element='companyName']"
        )
        loc_el = card.select_one(
            "div[data-testid='text-location'], div.companyLocation, "
            "span.location, div[class*='Location']"
        )
        if title_el:
            title_text = title_el.get_text(strip=True)
            comp_text = comp_el.get_text(strip=True) if comp_el else ""
            if not employer_matches(comp_text, company):
                continue
            href = title_el.get("href", "")
            if href and not href.startswith("http"):
                href = base_domain + href
            href = canonical_url(href)
            if not href or href in seen_urls:
                continue
            seen_urls.add(href)
            job = Job(
                title=title_text,
                company=comp_text,
                location=loc_el.get_text(strip=True) if loc_el else loc_param,
                source="Indeed",
                url=href,
            )
            # Pass 1: the role title explicitly mentions Pega technology.
            combined = title_text.lower()
            if _is_pega_relevant(combined):
                jobs.append(job)
            else:
                # Queue for JD deep-check
                pending_jd_check.append((job, href))

    # Pass 2: fetch JD page for generic-titled results, check for Pega
    checked = 0
    for job, url in pending_jd_check:
        if checked >= _JD_CHECKS_PER_SEARCH:
            break
        if _fetch_jd_pega_check(url):
            jobs.append(job)
        checked += 1

    return jobs


# ---------------------------------------------------------------------------
# Source: Google Search (job aggregation)
# ---------------------------------------------------------------------------
def search_google(company: dict, location: str = "India") -> list[Job]:
    """Search Google for Pega job postings at a company."""
    jobs = []
    keyword = company["keywords"][0]
    loc_term = "remote" if location.lower() == "remote" else location
    query = f'"{keyword}" pega developer {loc_term} jobs'
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={encoded}&num=15"

    html = fetch(url)
    if not html:
        return jobs

    soup = BeautifulSoup(html, "lxml")
    for result in soup.select("div.g, div[data-sokoban-container]"):
        link_el = result.select_one("a[href]")
        title_el = result.select_one("h3")
        snippet_el = result.select_one("div.VwiC3b, span.aCOpRe, div[data-snc]")

        if not (link_el and title_el):
            continue
        href = link_el.get("href", "")
        title_text = title_el.get_text(strip=True)
        snippet_text = snippet_el.get_text(strip=True) if snippet_el else ""
        combined = f"{title_text} {snippet_text}".lower()

        # Filter: must be a job-related result with Pega relevance
        job_indicators = [
            "job", "career", "hiring", "opening", "apply",
            "naukri", "indeed", "linkedin.com/jobs", "glassdoor",
        ]
        if _is_pega_relevant(combined) and any(ind in combined for ind in job_indicators):
            if "linkedin.com/in/" in href:
                continue
            job = Job(
                title=title_text,
                company="",
                location=location,
                source="Google",
                url=href,
                snippet=snippet_text[:200],
            )
            jobs.append(job)
    return jobs


# ---------------------------------------------------------------------------
# Company Career Portal Domains — verified internal job sites
# These are the ACTUAL career portals where companies post jobs directly,
# many of which never appear on LinkedIn/Indeed.
# Format: keyword (from company dict) → career portal domain
# ---------------------------------------------------------------------------
CAREER_PORTAL_DOMAINS = {
    # --- US Banking ---
    "jpmorgan":             "careers.jpmorganchase.com",
    "jpmorganchase":        "careers.jpmorganchase.com",
    "wells fargo":          "wellsfargojobs.com",
    "bank of america":      "careers.bankofamerica.com",
    "citi":                 "jobs.citi.com",
    "citibank":             "jobs.citi.com",
    "capital one":          "capitalone.com/tech/careers",
    "goldman sachs":        "goldmansachs.com/careers",
    "morgan stanley":       "morganstanley.com/careers",
    "first citizens bank":  "jobs.firstcitizens.com",
    "first citizens":       "jobs.firstcitizens.com",
    # --- US Healthcare / Insurance ---
    "unitedhealth":         "careers.unitedhealthgroup.com",
    "optum":                "careers.unitedhealthgroup.com",
    "cigna":                "jobs.thecignagroup.com",
    "evernorth":            "jobs.thecignagroup.com",
    "highmark health":      "careers.highmarkhealth.org",
    "highmark":             "careers.highmarkhealth.org",
    "aflac":                "careers.aflac.com",
    "northwestern mutual":  "careers.northwesternmutual.com",
    "prime therapeutics":   "jobs.primetherapeutics.com",
    "elevance health":      "careers.elevancehealth.com",
    "anthem":               "careers.elevancehealth.com",
    "humana":               "careers.humana.com",
    "metlife":              "jobs.metlife.com",
    "liberty mutual":       "jobs.libertymutual.com",
    "primerica":            "careers.primerica.com",
    # --- US Telecom ---
    "verizon":              "mycareer.verizon.com",
    "t-mobile":             "careers.t-mobile.com",
    "comcast":              "jobs.comcast.com",
    # --- US Government / Defense ---
    "accenture federal":    "accenture.com/us-en/careers",
    "booz allen":           "careers.boozallen.com",
    "saic":                 "jobs.saic.com",
    "maximus":              "careers.maximus.com",
    # --- US / Global SIs ---
    "accenture":            "accenture.com/careers",
    "cognizant":            "careers.cognizant.com",
    "capgemini":            "capgemini.com/careers",
    "deloitte":             "apply.deloitte.com",
    "epam":                 "epam.com/careers",
    # --- Pega Boutiques ---
    "inadev":               "inadev.com/careers",
    "areteans":             "areteanstech.com/careers",
    "aaseya":               "aaseya.com/careers",
    "virtusa":              "virtusa.com/careers",
    "pegasystems":          "pega.com/about/careers",
    "pega":                 "pega.com/about/careers",
    # --- UK Banking ---
    "hsbc":                 "hsbc.com/careers",
    "barclays":             "search.jobs.barclays",
    "lloyds banking":       "lloydsbankinggrouptalent.com",
    "lloyds bank":          "lloydsbankinggrouptalent.com",
    "natwest":              "jobs.natwestgroup.com",
    "nationwide building":  "nationwide-jobs.co.uk",
    "standard chartered":   "sc.com/careers",
    # --- UK Telecom ---
    "bt group":             "bt.com/careers",
    "vodafone":             "careers.vodafone.com",
    # --- Netherlands ---
    "ing bank":             "careers.ing.com",
    "ing group":            "careers.ing.com",
    "rabobank":             "rabobank.jobs",
    "abn amro":             "abnamro.com/careers",
    # --- Germany ---
    "deutsche bank":        "careers.db.com",
    "allianz":              "careers.allianz.com",
    "sopra steria":         "soprasteria.com/careers",
    # --- France ---
    "bnp paribas":          "group.bnpparibas/careers",
    "societe generale":     "careers.societegenerale.com",
    "axa":                  "careers.axa.com",
    # --- Nordics ---
    "nordea":               "nordea.com/en/careers",
    # --- Spain / Switzerland ---
    "santander":            "santander.com/careers",
    "zurich insurance":     "zurich.com/careers",
    # --- Australia ---
    "anz bank":             "careers.anz.com",
    "anz":                  "careers.anz.com",
    "commonwealth bank":    "commbank.com.au/about-us/careers",
    "cba":                  "commbank.com.au/about-us/careers",
    "telstra":              "careers.telstra.com",
    "qbe insurance":        "qbe.com/careers",
    "suncorp":              "suncorpgroup.com.au/careers",
    # --- Singapore ---
    "dbs bank":             "dbs.com/careers",
    "great eastern":        "greateasternlife.com/careers",
    # --- US / Global Technology ---
    "dell technologies":     "jobs.dell.com",
    "dell":                  "jobs.dell.com",
    "intersystems":          "intersystems.com/careers",
    "s&p global":            "careers.spglobal.com",
    "spglobal":              "careers.spglobal.com",
    "synechron":             "synechron.com/careers",
    # --- US Automotive / Manufacturing ---
    "general motors":        "search-careers.gm.com",
    "gm ":                   "search-careers.gm.com",
    "toyota":                "toyota.com/careers",
    "procter gamble":        "pgcareers.com",
    "p&g":                   "pgcareers.com",
    "coca-cola":             "coca-colacompany.com/careers",
    "coca cola":             "coca-colacompany.com/careers",
    # --- US Insurance (additional) ---
    "new york life":         "newyorklife.com/careers",
    "usaa":                  "usaa.com/careers",
    "unum":                  "jobs.unum.com",
    "csaa insurance":        "csaa-insurance.com/careers",
    "farmers insurance":     "farmers.com/careers",
    "allied solutions":      "alliedsolutions.net/careers",
    "church mutual":         "churchmutual.com/careers",
    "great american insurance": "greatamericaninsurance.com/careers",
    "delta dental":          "deltadental.com/careers",
    "transamerica":          "transamerica.com/careers",
    # --- US Healthcare (additional) ---
    "cvs health":            "jobs.cvshealth.com",
    "molina healthcare":     "molinahealthcare.com/careers",
    "molina":                "molinahealthcare.com/careers",
    "blue cross":            "bcbs.com/careers",
    "walgreens":             "jobs.walgreens.com",
    # --- US Telecom (additional) ---
    "at&t":                  "att.jobs",
    # --- US Defense (additional) ---
    "lockheed martin":       "lockheedmartinjobs.com",
    "general dynamics":      "gd.com/careers",
    "gdit":                  "gd.com/careers",
    # --- US Logistics ---
    "fedex":                 "careers.fedex.com",
    # --- US Retail / Hospitality ---
    "macys":                 "macysjobs.com",
    "target":                "jobs.target.com",
    "marriott":              "careers.marriott.com",
    "caesars entertainment":  "caesars.com/careers",
    # --- US Pharma ---
    "johnson & johnson":     "careers.jnj.com",
    "j&j":                   "careers.jnj.com",
    "merck":                 "jobs.merck.com",
    # --- Germany (additional) ---
    "deutsche telekom":      "telekom.com/careers",
    "siemens":               "siemens.com/careers",
    # --- Spain (additional) ---
    "bbva":                  "bbva.com/careers",
    # --- France (additional) ---
    "groupama":              "groupama.com/careers",
    # --- UK (additional) ---
    "sky uk":                "skygroup.sky/careers",
    "sky ":                  "skygroup.sky/careers",
    "centrica":              "centrica.com/careers",
    "bupa":                  "bupa.com/careers",
    "nhs 24":                "nhs24.scot.nhs.uk/careers",
    # --- Australia (additional) ---
    "westpac":               "westpac.com.au/about-westpac/careers",
    "toyota finance australia": "toyota.com.au/careers",
    "bupa australia":        "bupa.com.au/careers",
    # --- Brazil ---
    "bradesco":              "bradesco.com.br/carreiras",
    "itau":                  "itau.com.br/carreiras",
    # --- India (GCC / Product) ---
    "cisco":                "jobs.cisco.com",
    "john deere":           "deere.com/careers",
    "american express":     "aexp.com/careers",
    "booking holdings":     "careers.bookingholdings.com",
    "nokia":                "nokia.com/careers",
    "shell":                "shell.com/careers",
    "ge healthcare":        "careers.gehealthcare.com",
    "roche":                "roche.com/careers",
    "mastercard":           "careers.mastercard.com",
    "paypal":               "careers.pypl.com",
    "broadridge":           "broadridge.com/careers",
    "visa":                 "usa.visa.com/careers",
    "tesco":                "tescoplc.com/careers",
    "maersk":               "maersk.com/careers",
    "sun life":             "sunlife.com/careers",
    "deutsche bank":        "careers.db.com",
    # --- India (SI / Consulting) ---
    "tcs":                  "tcs.com/careers",
    "infosys":              "infosys.com/careers",
    "wipro":                "careers.wipro.com",
    "hcl":                  "hcltech.com/careers",
    "tech mahindra":        "techmahindra.com/careers",
    "ltimindtree":          "ltimindtree.com/careers",
    "mphasis":              "mphasis.com/careers",
}


def _get_career_domain(company: dict) -> Optional[str]:
    """Look up the career portal domain for a company."""
    if broad_target(company):
        return None
    if company.get("career_url"):
        return company["career_url"]
    for kw in company.get("keywords", []):
        kw_lower = kw.lower()
        if kw_lower in CAREER_PORTAL_DOMAINS:
            return CAREER_PORTAL_DOMAINS[kw_lower]
    return company.get("career_url", None)


# ---------------------------------------------------------------------------
# Source: Company Career Portal (via Google site: search)
# Searches the company's public career site for Pega roles that may not
# appear on LinkedIn/Indeed. It cannot access internal-only vacancies.
# ---------------------------------------------------------------------------
def search_career_portal(company: dict, location: str = "India") -> list[Job]:
    """Search a company's career portal via Google site: search."""
    jobs = []
    career_domain = _get_career_domain(company)
    if not career_domain:
        return jobs

    # Preserve the configured career path, including tenant paths on shared ATSs.
    portal_url = career_domain if career_domain.startswith(("https://", "http://")) else "https://" + career_domain
    portal = urllib.parse.urlparse(portal_url)
    domain = (portal.hostname or "").lower()
    career_path = portal.path.rstrip("/")
    if "." not in domain:
        return jobs

    keyword = company["keywords"][0]
    loc_term = location if location.lower() != "remote" else ""

    # Google site: search — finds Pega jobs on their internal career portal
    query = f"site:{domain}{career_path} pega {loc_term}".strip()
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={encoded}&num=10"

    html = fetch(url)
    if not html:
        return jobs

    soup = BeautifulSoup(html, "lxml")
    seen_urls = set()
    for result in soup.select("div.g, div[data-sokoban-container]"):
        link_el = result.select_one("a[href]")
        title_el = result.select_one("h3")
        snippet_el = result.select_one("div.VwiC3b, span.aCOpRe, div[data-snc]")

        if not (link_el and title_el):
            continue
        href = canonical_url(link_el.get("href", ""))
        returned_host = urllib.parse.urlparse(href).hostname or ""
        if returned_host != domain and not returned_host.endswith("." + domain):
            continue
        returned_path = urllib.parse.urlparse(href).path.rstrip("/")
        if career_path and returned_path != career_path and not returned_path.startswith(career_path + "/"):
            continue
        if href in seen_urls:
            continue
        seen_urls.add(href)
        title_text = title_el.get_text(strip=True)
        snippet_text = snippet_el.get_text(strip=True) if snippet_el else ""

        # A matching domain/snippet may be a landing page or article. Require
        # an individual role description even when the title says Pega.
        if not _fetch_jd_pega_check(href):
            continue

        job = Job(
            title=title_text,
            company=company["name"],
            location=location,
            source="Career Portal",
            url=href,
            snippet=snippet_text[:200],
        )
        jobs.append(job)
    return jobs


# ---------------------------------------------------------------------------
# Generate quick-access search links (always work, no scraping needed)
# ---------------------------------------------------------------------------
def generate_search_links(company: dict, location: str = "India") -> dict:
    """Generate direct search URLs the user can click."""
    keyword = company["keywords"][0]
    q = urllib.parse.quote_plus(f"pega {keyword}")
    loc = location if location else "India"
    loc_enc = urllib.parse.quote_plus(loc)

    links = {
        "LinkedIn": f"https://www.linkedin.com/jobs/search/?keywords={q}&location={loc_enc}",
        "Google": f"https://www.google.com/search?q={urllib.parse.quote_plus(f'{keyword} pega jobs {loc}')}",
    }

    # Naukri only makes sense for India
    if loc.lower() in ("india", ""):
        links["Naukri"] = f"https://www.naukri.com/pega-{keyword.replace(' ', '-')}-jobs-in-india"
        links["Indeed"] = f"https://www.indeed.co.in/jobs?q={q}&l=India"
    else:
        # US/Global — use indeed.com
        indeed_loc = "Remote" if loc.lower() == "remote" else loc
        links["Indeed"] = f"https://www.indeed.com/jobs?q={q}&l={urllib.parse.quote_plus(indeed_loc)}"

    # Career Portal direct link — search pega on their internal site
    career_domain = _get_career_domain(company)
    if career_domain:
        domain = career_domain.replace("https://", "").replace("http://", "")
        links["Career Portal"] = f"https://www.google.com/search?q={urllib.parse.quote_plus(f'site:{domain} pega')}"
        # Also add direct career page link for easy access
        if not career_domain.startswith("http"):
            career_domain = f"https://{career_domain}"
        links["Direct Career Site"] = career_domain

    return links


# ---------------------------------------------------------------------------
# Broad LinkedIn scan: fetches all Pega jobs, assigns to companies
# Supports multiple locations (India, US, Remote, etc.)
# ---------------------------------------------------------------------------
_broad_linkedin_cache: dict[str, list[Job]] = {}  # keyed by location
_broad_linkedin_audit: dict[str, list[dict]] = {}


def fetch_broad_linkedin_jobs(location: str = "India") -> list[Job]:
    """Fetch a broad set of Pega jobs from LinkedIn for a given location."""
    global _broad_linkedin_cache
    cache_key = location.lower()
    if cache_key in _broad_linkedin_cache:
        return _broad_linkedin_cache[cache_key]

    audit_start = len(FETCH_AUDIT)
    all_jobs = []
    # Multiple search queries to catch generic-titled roles too
    search_terms = [
        "pega+developer",
        "pega+architect",
        "pega+engineer",
        "pega+PRPC",
        "pega+consultant",
        "software+engineer+pega",
    ]
    seen_urls = set()

    for term in search_terms:
        for start in [0, 25]:
            loc_enc = urllib.parse.quote_plus(location)
            url = (
                f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
                f"?keywords={term}&location={loc_enc}&start={start}"
            )
            html = fetch(url)
            if not html:
                continue
            # Generic titles require a scoped role-description check.
            found = _parse_linkedin_cards(html, "", location)
            for job in found:
                if job.url and job.url not in seen_urls:
                    seen_urls.add(job.url)
                    all_jobs.append(job)
            time.sleep(DELAY_BETWEEN_REQUESTS)
        # If we've found plenty from the first search term, skip the rest
        if len(all_jobs) >= 50:
            break

    _broad_linkedin_cache[cache_key] = all_jobs
    _broad_linkedin_audit[cache_key] = list(FETCH_AUDIT[audit_start:])
    log.info("Broad LinkedIn scan [%s]: %d total Pega jobs", location, len(all_jobs))
    return all_jobs


def match_broad_jobs_to_company(company: dict, location: str = "India") -> list[Job]:
    """From the broad LinkedIn results, return jobs matching this company."""
    broad = fetch_broad_linkedin_jobs(location)
    return [job for job in broad if employer_matches(job.company, company)]


# ---------------------------------------------------------------------------
# Known vendor / SI company names to filter out
# ---------------------------------------------------------------------------
VENDOR_NAMES = {
    "tcs", "tata consultancy", "infosys", "wipro", "hcl", "cognizant",
    "capgemini", "accenture", "tech mahindra", "mphasis", "virtusa",
    "mindtree", "ltimindtree", "ntt data", "deloitte", "ey ", "ernst",
    "kpmg", "pwc", "pricewaterhouse", "ibm", "dxc", "hexaware",
    "cyient", "l&t infotech", "lti", "zensar", "persistent", "coforge",
    "birlasoft", "sonata", "eviden", "atos", "genpact", "eai systems",
    "mastech", "isgn", "collabera", "us tech solutions", "randstad",
    "adecco", "manpower", "kelly services", "robert half", "hays",
}


def _is_vendor_job(job: Job, company: dict) -> bool:
    """Return True if the job's listed company does NOT match the target GCC.
    
    Strict whitelist approach: only keep jobs where the employer name
    clearly matches the target company. Everything else (vendors, SIs,
    unrelated firms that appeared in search results) gets filtered out.
    """
    return not employer_matches(job.company, company)


# ---------------------------------------------------------------------------
# Master scan function
# ---------------------------------------------------------------------------
def scan_company(company: dict) -> tuple[list[Job], dict]:
    """Run all sources for a single company. Returns (jobs, search_links).
    
    Uses the company's 'location' field if present (for remote/global companies),
    otherwise defaults to India.
    """
    name = company["name"]
    location = company.get("location", "India")
    log.info("Scanning: %s [%s]", name, location)

    all_jobs: list[Job] = []

    # Strategy 1: Company-specific searches
    # Skip Naukri for non-India locations (Naukri is India-only)
    if location.lower() in ("india", ""):
        sources = [
            ("Naukri", search_naukri),
            ("LinkedIn", search_linkedin),
            ("Indeed", search_indeed),
            ("Google", search_google),
            ("Career Portal", search_career_portal),
        ]
    else:
        sources = [
            ("LinkedIn", search_linkedin),
            ("Indeed", search_indeed),
            ("Google", search_google),
            ("Career Portal", search_career_portal),
        ]

    diagnostics = []
    for src_name, func in sources:
        if src_name == 'Google':
            diagnostics.append({'source': 'Google', 'candidates': 0, 'state': 'manual_search',
                                'detail': 'Use the search link. Generic search snippets cannot reliably establish the hiring employer.'})
            continue
        FETCH_AUDIT.clear()
        try:
            found = func(company, location=location)
            log.info("  %s: %d raw results", src_name, len(found))
            all_jobs.extend(found)
            failures = [x for x in FETCH_AUDIT if x.get("error") or x.get("http_status",200) != 200]
            diagnostics.append({"source": src_name, "candidates": len(found), "state": "partial" if failures and found else "unavailable" if failures else "collected" if found else "no_candidates", "failures": failures[:5]})
        except Exception as exc:
            diagnostics.append({"source": src_name, "candidates": 0, "state": "error", "error": str(exc)[:200]})
            log.warning("  %s failed: %s", src_name, exc)

    # Strategy 2: Broad LinkedIn scan — match this company from all Pega jobs
    FETCH_AUDIT.clear()
    broad_cache_key = location.lower()
    broad_cached = broad_cache_key in _broad_linkedin_cache
    try:
        broad_matched = match_broad_jobs_to_company(company, location=location)
        if broad_matched:
            log.info("  Broad LinkedIn: %d direct matches", len(broad_matched))
            all_jobs.extend(broad_matched)
        broad_audit = _broad_linkedin_audit.get(broad_cache_key, []) if broad_cached else FETCH_AUDIT
        failures = [x for x in broad_audit if x.get("error") or x.get("http_status", 200) != 200]
        diagnostics.append({
            "source": "Broad LinkedIn", "candidates": len(broad_matched),
            "state": "partial" if failures and broad_matched else "unavailable" if failures else "collected" if broad_matched else "no_candidates",
            "cached": broad_cached, "failures": failures[:5],
        })
    except Exception as exc:
        diagnostics.append({"source": "Broad LinkedIn", "candidates": 0, "state": "error", "cached": broad_cached, "error": str(exc)[:200]})
        log.warning("  Broad LinkedIn match failed: %s", exc)

    # Filter out unrelated jobs (e.g. Pegasystems showing under KPMG search)
    # _is_vendor_job uses a whitelist approach — it checks if the job's listed
    # company matches the target company name/keywords.  This works for ALL
    # company types (GCC *and* SI/consulting) so we always apply it.
    direct_jobs = []
    vendor_count = 0
    for job in all_jobs:
        if _is_vendor_job(job, company):
            vendor_count += 1
            log.debug("  Filtered unrelated job: '%s' at %s", job.title, job.company)
        else:
            direct_jobs.append(job)
    if vendor_count:
        log.info("  Filtered %d vendor/SI jobs (kept %d direct)", vendor_count, len(direct_jobs))

    # Deduplicate by uid
    seen_uids = set()
    unique_jobs = []
    for job in direct_jobs:
        if job.uid not in seen_uids:
            seen_uids.add(job.uid)
            unique_jobs.append(job)

    LAST_SCAN_DIAGNOSTICS[name] = diagnostics
    links = generate_search_links(company, location=location)
    return unique_jobs, links


# ---------------------------------------------------------------------------
# HTML Report Generator
# ---------------------------------------------------------------------------
def generate_report(
    all_results: dict[str, tuple[list[Job], dict]],
    history: JobHistory,
    scan_time: str,
) -> str:
    """Generate a beautiful HTML report."""

    total_jobs = sum(len(jobs) for jobs, _ in all_results.values())
    new_jobs = sum(
        sum(1 for j in jobs if j.is_new) for jobs, _ in all_results.values()
    )
    companies_with_jobs = sum(1 for jobs, _ in all_results.values() if jobs)

    # Sort: companies with NEW jobs first, then by job count
    sorted_results = sorted(
        all_results.items(),
        key=lambda x: (
            -sum(1 for j in x[1][0] if j.is_new),  # new jobs first
            -len(x[1][0]),                            # then by total
        ),
    )

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pega Job Hunter Report - {scan_time[:10]}</title>
<style>
:root {{--bg:#0f172a;--card:#1e293b;--accent:#38bdf8;--green:#22c55e;--amber:#f59e0b;
--red:#ef4444;--text:#e2e8f0;--muted:#94a3b8;--border:#334155;}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);padding:20px;line-height:1.5}}
.header{{text-align:center;padding:30px 0;border-bottom:2px solid var(--accent)}}
.header h1{{font-size:2rem;background:linear-gradient(135deg,var(--accent),var(--green));-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.header .sub{{color:var(--muted);margin-top:6px}}
.metrics{{display:flex;gap:16px;justify-content:center;margin:20px 0;flex-wrap:wrap}}
.metric{{background:var(--card);border-radius:10px;padding:16px 24px;text-align:center;min-width:140px;border:1px solid var(--border)}}
.metric strong{{display:block;font-size:1.8rem;color:var(--accent)}}
.metric .label{{font-size:.85rem;color:var(--muted)}}
.metric.new strong{{color:var(--green)}}
.section{{margin:30px 0}}
.section h2{{color:var(--accent);font-size:1.3rem;margin-bottom:12px;padding-left:10px;border-left:3px solid var(--accent)}}
.company-block{{background:var(--card);border-radius:10px;margin:12px 0;padding:16px;border:1px solid var(--border)}}
.company-block.has-new{{border-color:var(--green);box-shadow:0 0 10px rgba(34,197,94,.15)}}
.company-name{{font-size:1.1rem;font-weight:700;margin-bottom:6px}}
.search-links{{margin:6px 0;display:flex;gap:8px;flex-wrap:wrap}}
.search-links a{{color:var(--accent);font-size:.8rem;padding:3px 10px;border:1px solid var(--accent);border-radius:12px;text-decoration:none;transition:.2s}}
.search-links a:hover{{background:var(--accent);color:var(--bg)}}
table{{width:100%;border-collapse:collapse;margin-top:10px;font-size:.9rem}}
th{{text-align:left;padding:8px 10px;background:var(--bg);color:var(--muted);font-weight:600;border-bottom:1px solid var(--border)}}
td{{padding:8px 10px;border-bottom:1px solid var(--border);vertical-align:top}}
tr:hover td{{background:rgba(56,189,248,.05)}}
.pill{{display:inline-block;padding:2px 8px;border-radius:8px;font-size:.75rem;font-weight:600}}
.pill.new{{background:rgba(34,197,94,.2);color:var(--green)}}
.pill.seen{{background:rgba(148,163,184,.15);color:var(--muted)}}
.pill.naukri{{background:rgba(56,189,248,.2);color:var(--accent)}}
.pill.linkedin{{background:rgba(10,102,194,.3);color:#60a5fa}}
.pill.indeed{{background:rgba(46,64,138,.3);color:#818cf8}}
.pill.google{{background:rgba(245,158,11,.2);color:var(--amber)}}
a.job-link{{color:var(--accent);text-decoration:none}}
a.job-link:hover{{text-decoration:underline}}
.no-jobs{{color:var(--muted);font-style:italic;font-size:.9rem;padding:8px 0}}
.footer{{text-align:center;color:var(--muted);font-size:.8rem;margin-top:40px;padding-top:20px;border-top:1px solid var(--border)}}
.timestamp{{color:var(--amber);font-size:.85rem}}
</style></head><body>
<div class="header">
<h1>Pega Job Hunter Report</h1>
<div class="sub">Automated daily scan for Pega openings at target GCC companies in India</div>
<div class="timestamp">Scan completed: {scan_time} | Previous: {history.last_run or 'First run'}</div>
</div>

<div class="metrics">
<div class="metric new"><strong>{new_jobs}</strong><span class="label">Newly Seen Candidates</span></div>
<div class="metric"><strong>{total_jobs}</strong><span class="label">Unverified Discovery Candidates</span></div>
<div class="metric"><strong>{companies_with_jobs}</strong><span class="label">Companies with Candidates</span></div>
<div class="metric"><strong>{len(all_results)}</strong><span class="label">Companies Scanned</span></div>
</div>
"""

    # Companies WITH jobs
    html += '<div class="section"><h2>Discovery candidates — verify each employer listing</h2>\n'
    for co_name, (jobs, links) in sorted_results:
        if not jobs:
            continue
        has_new = any(j.is_new for j in jobs)
        html += f'<div class="company-block {"has-new" if has_new else ""}">\n'
        html += f'<div class="company-name">{html_escape.escape(co_name)}'
        if has_new:
            new_count = sum(1 for j in jobs if j.is_new)
            html += f' <span class="pill new">{new_count} NEW</span>'
        html += "</div>\n"
        html += '<div class="search-links">'
        for src, link in links.items():
            html += f'<a href="{html_escape.escape(link, quote=True)}" target="_blank" rel="noopener noreferrer">Search {src}</a> '
        html += "</div>\n"
        html += "<table><tr><th>Title</th><th>Company Listed</th><th>Location</th><th>Source</th><th>Status</th></tr>\n"
        for j in jobs:
            src_class = j.source.lower().replace(" ", "")
            status_pill = '<span class="pill new">NEW</span>' if j.is_new else '<span class="pill seen">Seen</span>'
            html += f'<tr><td><a class="job-link" href="{html_escape.escape(j.url, quote=True)}" target="_blank" rel="noopener noreferrer">{html_escape.escape(j.title)}</a></td>'
            html += f"<td>{html_escape.escape(j.company)}</td><td>{html_escape.escape(j.location)}</td>"
            html += f'<td><span class="pill {src_class}">{j.source}</span></td>'
            html += f"<td>{status_pill}</td></tr>\n"
        html += "</table></div>\n"
    html += "</div>\n"

    # Companies WITHOUT jobs (quick-search links)
    html += '<div class="section"><h2>No candidates collected - sources may be unavailable</h2>\n'
    html += "<p style='color:var(--muted);font-size:.9rem;margin-bottom:12px'>No Pega jobs were scraped from these companies. Click the links below to manually check.</p>\n"
    for co_name, (jobs, links) in sorted_results:
        if jobs:
            continue
        html += f'<div class="company-block"><div class="company-name">{html_escape.escape(co_name)}</div>'
        html += '<div class="search-links">'
        for src, link in links.items():
            html += f'<a href="{html_escape.escape(link, quote=True)}" target="_blank" rel="noopener noreferrer">{src}</a> '
        html += "</div></div>\n"
    html += "</div>\n"

    html += f"""
<div class="footer">
    Pega Job Hunter Agent v1.0 | Generated {scan_time}<br>
    Discovery results are not independently verified openings. NEW means newly seen, not newly posted.
</div>
</body></html>"""
    return html


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Pega Job Hunter Agent")
    parser.add_argument("--quick", action="store_true", help="Scan top 30 companies only")
    parser.add_argument("--consulting", action="store_true", help="Scan consulting/SI companies instead of GCCs")
    parser.add_argument("--remote", action="store_true", help="Scan remote/global companies (US, UK, EU)")
    parser.add_argument("--all", action="store_true", help="Scan ALL pools (GCC + consulting + remote)")
    parser.add_argument("--company", type=str, help="Scan a single company by name")
    parser.add_argument("--open", action="store_true", help="Auto-open report in browser")
    parser.add_argument("--dry-run", action="store_true", help="Generate links only, no scraping")
    parser.add_argument("--browser", action="store_true", help="Open top search links in browser tabs")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(exist_ok=True)

    log.info("=" * 60)
    log.info("Pega Job Hunter - Starting scan")
    log.info("=" * 60)

    history = JobHistory(HISTORY_FILE)
    if history.last_run:
        log.info("Last scan: %s", history.last_run)

    # Determine which company pool to use
    if args.remote:
        pool = REMOTE_GLOBAL_COMPANIES
        log.info("Mode: Remote/Global companies (US, UK, EU)")
    elif args.consulting:
        pool = CONSULTING_COMPANIES
        log.info("Mode: Consulting/SI companies")
    elif args.all:
        pool = COMPANIES + CONSULTING_COMPANIES + REMOTE_GLOBAL_COMPANIES
        log.info("Mode: All companies (GCC + Consulting + Remote/Global)")
    else:
        pool = COMPANIES
        log.info("Mode: GCC/Product companies")

    # Filter companies based on args
    targets = pool
    if args.quick:
        quick_priorities = {"top30", "gcc_top", "si_top", "remote_top"}
        targets = [c for c in pool if c["priority"] in quick_priorities]
        log.info("Quick mode: scanning %d top-priority companies", len(targets))
    elif args.company:
        # Search across ALL pools when targeting a specific company
        search = args.company.lower()
        targets = [c for c in (COMPANIES + CONSULTING_COMPANIES + REMOTE_GLOBAL_COMPANIES) if search in c["name"].lower() or any(search in kw.lower() for kw in c["keywords"])]
        if not targets:
            log.error("Company '%s' not found in target list", args.company)
            sys.exit(1)
        log.info("Single company mode: %s", targets[0]["name"])
    else:
        log.info("Full scan: %d companies", len(targets))

    # Run scans
    all_results: dict[str, tuple[list[Job], dict]] = {}
    for idx, company in enumerate(targets, 1):
        log.info("[%d/%d] %s", idx, len(targets), company["name"])
        if args.dry_run:
            jobs = []
            links = generate_search_links(company, company.get("location", "India"))
        else:
            jobs, links = scan_company(company)

        # Mark new vs seen
        for job in jobs:
            if history.is_new(job.uid):
                job.is_new = True
                history.mark_seen(job.uid)

        all_results[company["name"]] = (jobs, links)

    # Generate report
    scan_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_html = generate_report(all_results, history, scan_time)

    report_name = f"pega_jobs_{datetime.now().strftime('%Y-%m-%d')}.html"
    report_path = REPORTS_DIR / report_name
    report_path.write_text(report_html, encoding="utf-8")
    log.info("Report saved: %s", report_path)

    # Save history
    history.save()
    log.info("Job history updated (%d entries)", len(history.data["seen_ids"]))

    # Summary
    total = sum(len(j) for j, _ in all_results.values())
    new = sum(sum(1 for j in jobs if j.is_new) for jobs, _ in all_results.values())
    log.info("-" * 40)
    log.info("SCAN COMPLETE: %d jobs found, %d NEW", total, new)
    log.info("-" * 40)

    # Auto-open report
    if args.open or (new > 0 and not args.dry_run):
        try:
            os.startfile(str(report_path))
        except Exception:
            log.info("Open the report: %s", report_path)

    # --browser mode: open Naukri/LinkedIn search links in browser tabs
    if args.browser:
        log.info("Opening search links in browser...")
        opened = 0
        for co_name, (_, links) in all_results.items():
            if opened >= 20:
                log.info("Opened 20 tabs, stopping (use report for rest)")
                break
            for src in ["Naukri", "LinkedIn"]:
                if src in links:
                    webbrowser.open_new_tab(links[src])
                    opened += 1
                    time.sleep(0.5)

    return str(report_path)


if __name__ == "__main__":
    main()
