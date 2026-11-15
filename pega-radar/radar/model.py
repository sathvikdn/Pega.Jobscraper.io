"""Text utilities, the job / result shapes every module exchanges, and configuration loading.

This module has no dependencies inside the package, so sources, store, rank, scan and
server can all import it freely.
"""
from __future__ import annotations

import copy
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

# Pega as a product name, however a board glues it to its neighbours: "Pega_Developer", "Pega8",
# "PegaDeveloper", "PEGADEVELOPER", "PRPC_Dev". After "pega" may come a non-letter, a capital in
# CamelCase, or a word that is known to follow it. Anything else is another word: Pegasus,
# Pegatron, Pegaso, Pegah, Pegadaian. Case matters to the CamelCase rule, so no IGNORECASE here.
_AFTER_PEGA = ('systems?|rules|prpc|developers?|dev|architects?|engineers?|leads?|consultants?|admin|administrators?|'
               'testers?|testing|analysts?|programmers?|specialists?|support|platform|decisioning|robotics|infinity|'
               'constellation|cssa|clsa|csa|ssa|lsa|bpm|crm|cdh|jobs?')
# CamelCase does not rescue the look-alikes: "PegaSus" and "PegaTron" are still Pegasus and Pegatron.
_NOT_PEGA = 'sus|tron|so|si|sos|sis|h|daian|tec'
PEGA_RE = re.compile(r'(?<![A-Za-z])(?:(?i:pega)(?![A-Za-z])|(?i:pega)(?=(?i:' + _AFTER_PEGA + r')(?![A-Za-z]))|'
                     r'[Pp]ega(?=[A-Z])(?!(?i:' + _NOT_PEGA + r')(?![A-Za-z]))|(?i:prpc)(?![A-Za-z]))')

# alias (lower case) -> canonical city name. Suburbs that postings use interchangeably with their
# metro and common misspellings are folded into the city so "same primary city" comparisons work.
CITY_ALIASES = {
    'bengaluru': 'Bengaluru', 'bangalore': 'Bengaluru', 'bengalooru': 'Bengaluru', 'banglore': 'Bengaluru',
    'bangaluru': 'Bengaluru', 'bengalore': 'Bengaluru', 'blr': 'Bengaluru',
    'hyderabad': 'Hyderabad', 'secunderabad': 'Hyderabad', 'hydrabad': 'Hyderabad', 'hyd': 'Hyderabad',
    'pune': 'Pune',
    'chennai': 'Chennai', 'madras': 'Chennai', 'chenai': 'Chennai',
    'mumbai': 'Mumbai', 'navi mumbai': 'Mumbai', 'bombay': 'Mumbai', 'mumabi': 'Mumbai', 'thane': 'Thane',
    'delhi': 'Delhi', 'new delhi': 'Delhi', 'ncr': 'Delhi',
    'gurugram': 'Gurugram', 'gurgaon': 'Gurugram', 'gurgoan': 'Gurugram',
    'noida': 'Noida', 'greater noida': 'Noida', 'faridabad': 'Faridabad', 'ghaziabad': 'Ghaziabad',
    'kolkata': 'Kolkata', 'calcutta': 'Kolkata',
    'kochi': 'Kochi', 'cochin': 'Kochi',
    'coimbatore': 'Coimbatore', 'madurai': 'Madurai', 'salem': 'Salem',
    'tiruchirappalli': 'Tiruchirappalli', 'trichy': 'Tiruchirappalli',
    'ahmedabad': 'Ahmedabad', 'gandhinagar': 'Gandhinagar', 'surat': 'Surat',
    'thiruvananthapuram': 'Thiruvananthapuram', 'trivandrum': 'Thiruvananthapuram',
    'jaipur': 'Jaipur', 'indore': 'Indore', 'bhopal': 'Bhopal', 'nagpur': 'Nagpur', 'nashik': 'Nashik',
    'bhubaneswar': 'Bhubaneswar', 'chandigarh': 'Chandigarh', 'mohali': 'Mohali',
    'mysuru': 'Mysuru', 'mysore': 'Mysuru', 'mangaluru': 'Mangaluru', 'mangalore': 'Mangaluru',
    'hubballi': 'Hubballi', 'hubli': 'Hubballi', 'belagavi': 'Belagavi',
    'visakhapatnam': 'Visakhapatnam', 'vizag': 'Visakhapatnam', 'vijayawada': 'Vijayawada', 'warangal': 'Warangal',
    'vadodara': 'Vadodara', 'baroda': 'Vadodara',
    'lucknow': 'Lucknow', 'patna': 'Patna', 'guwahati': 'Guwahati',
}
# Business parks and districts that mean Bengaluru when a posting gives no city. Other cities have
# an Ecospace, an Outer Ring Road and an Electronic City too, so these count only when the text
# names no Indian city and no place abroad.
BENGALURU_LOCALITIES = ('Manyata', 'Whitefield', 'Electronic City', 'Embassy Golf Links', 'Bagmane', 'Ecospace',
                        'Outer Ring Road', 'Koramangala', 'Marathahalli', 'Bellandur', 'Hebbal', 'Yelahanka')
# A state places a posting in India without saying which city ("Karnataka" is not Bengaluru).
INDIAN_STATES = ('Karnataka', 'Telangana', 'Maharashtra', 'Tamil Nadu', 'Haryana', 'Uttar Pradesh', 'West Bengal',
                 'Kerala', 'Gujarat', 'Rajasthan', 'Andhra Pradesh', 'Odisha', 'Punjab', 'Madhya Pradesh', 'Goa')


def _alternatives(names):
    # Longest first so "navi mumbai" and "new delhi" win over "mumbai" and "delhi".
    return '|'.join(re.escape(name.lower()).replace(r'\ ', r'\s+') for name in sorted(names, key=len, reverse=True))


_CITY_RE = re.compile(r'\b(' + _alternatives(CITY_ALIASES) + r')\b', re.I)
_LOCALITY_RE = re.compile(r'\b(?:' + _alternatives(BENGALURU_LOCALITIES) + r')\b', re.I)
_INDIA_RE = re.compile(r'\b(?:india|bharat|' + _alternatives(INDIAN_STATES) + r')\b', re.I)
# ISO-style codes are upper case by convention. "IN-KA-BLR" and "IN-KA" can only be India.
_INDIA_REGION_RE = re.compile(r'\bIN-[A-Z]{2}\b')
# "Bengaluru, IN" or just "IN" is India too, unless the text is plainly American: IN is also Indiana.
_INDIA_COUNTRY_RE = re.compile(r',\s*IN\b(?!-)|^\s*IN\s*$')
_FOREIGN_RE = re.compile(r'\b(?:' + _alternatives((
    # countries
    'united states', 'united states of america', 'u.s.a', 'u.s', 'america', 'united kingdom', 'great britain',
    'britain', 'england', 'scotland', 'wales', 'northern ireland', 'ireland', 'canada', 'australia', 'new zealand',
    'germany', 'deutschland', 'france', 'netherlands', 'holland', 'belgium', 'luxembourg', 'switzerland', 'austria',
    'spain', 'portugal', 'italy', 'greece', 'malta', 'cyprus', 'sweden', 'norway', 'denmark', 'finland', 'iceland',
    'poland', 'czech republic', 'czechia', 'slovakia', 'hungary', 'romania', 'bulgaria', 'serbia', 'croatia',
    'slovenia', 'lithuania', 'latvia', 'estonia', 'ukraine', 'turkey', 'türkiye', 'israel', 'egypt', 'morocco',
    'tunisia', 'south africa', 'kenya', 'nigeria', 'ghana', 'mauritius', 'united arab emirates', 'saudi arabia',
    'qatar', 'kuwait', 'bahrain', 'oman', 'jordan', 'singapore', 'malaysia', 'philippines', 'indonesia', 'thailand',
    'vietnam', 'japan', 'china', 'hong kong', 'taiwan', 'south korea', 'korea', 'sri lanka', 'bangladesh', 'pakistan',
    'nepal', 'mexico', 'brazil', 'brasil', 'argentina', 'colombia', 'chile', 'peru', 'costa rica', 'panama',
    'puerto rico', 'uruguay',
    # major cities
    'london', 'manchester', 'birmingham', 'leeds', 'glasgow', 'edinburgh', 'belfast', 'dublin', 'cork', 'new york',
    'san francisco', 'san jose', 'los angeles', 'san diego', 'chicago', 'boston', 'dallas', 'plano', 'irving',
    'austin', 'houston', 'atlanta', 'seattle', 'denver', 'phoenix', 'charlotte', 'raleigh', 'washington',
    'philadelphia', 'pittsburgh', 'columbus', 'cincinnati', 'cleveland', 'detroit', 'minneapolis', 'st. louis',
    'kansas city', 'nashville', 'miami', 'tampa', 'orlando', 'jacksonville', 'indianapolis', 'salt lake city',
    'las vegas', 'portland', 'hartford', 'jersey city', 'toronto', 'vancouver', 'montreal', 'ottawa', 'calgary',
    'sydney', 'melbourne', 'brisbane', 'perth', 'adelaide', 'auckland', 'wellington', 'berlin', 'munich',
    'frankfurt', 'hamburg', 'cologne', 'stuttgart', 'paris', 'lyon', 'amsterdam', 'rotterdam', 'utrecht',
    'eindhoven', 'brussels', 'zurich', 'geneva', 'vienna', 'madrid', 'barcelona', 'lisbon', 'porto', 'milan', 'rome',
    'athens', 'stockholm', 'oslo', 'copenhagen', 'helsinki', 'warsaw', 'krakow', 'wroclaw', 'gdansk', 'prague',
    'brno', 'bratislava', 'budapest', 'bucharest', 'cluj', 'sofia', 'vilnius', 'riga', 'tallinn', 'istanbul',
    'tel aviv', 'cairo', 'johannesburg', 'cape town', 'nairobi', 'lagos', 'dubai', 'abu dhabi', 'riyadh', 'jeddah',
    'doha', 'kuala lumpur', 'penang', 'cyberjaya', 'manila', 'cebu', 'jakarta', 'bangkok', 'ho chi minh', 'hanoi',
    'tokyo', 'osaka', 'shanghai', 'beijing', 'shenzhen', 'seoul', 'taipei', 'colombo', 'dhaka', 'karachi', 'lahore',
    'kathmandu', 'mexico city', 'guadalajara', 'monterrey', 'sao paulo', 'são paulo', 'rio de janeiro',
    'buenos aires', 'bogota', 'santiago', 'lima',
    # US states and Canadian provinces by name
    'alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado', 'connecticut', 'delaware', 'florida',
    'georgia', 'hawaii', 'idaho', 'illinois', 'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana', 'maine',
    'maryland', 'massachusetts', 'michigan', 'minnesota', 'mississippi', 'missouri', 'montana', 'nebraska', 'nevada',
    'new hampshire', 'new jersey', 'new mexico', 'north carolina', 'north dakota', 'ohio', 'oklahoma', 'oregon',
    'pennsylvania', 'rhode island', 'south carolina', 'south dakota', 'tennessee', 'texas', 'utah', 'vermont',
    'virginia', 'west virginia', 'wisconsin', 'wyoming', 'ontario', 'quebec', 'british columbia', 'alberta',
)) + r')\b', re.I)
# Upper-case codes: countries and regions, and "City, ST" for US states. A code that is also an
# Indian state or territory (TN, GA, OR, AR, CT, LA, MN, and UK for Uttarakhand) proves nothing on
# its own, and neither does IN (the country code for India), so those are left out: "Hosur, TN"
# is kept, "Nashville, TN, United States" is foreign through its country.
_FOREIGN_CODE_RE = re.compile(
    r'\b(?:USA?|UAE|GB|EMEA|APAC|LATAM)\b|,\s*(?:AL|AK|AZ|CA|CO|DC|DE|FL|HI|ID|IL|IA|KS|KY|ME|MD|MA|MI|'
    r'MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|PA|RI|SC|SD|TX|UT|VT|VA|WA|WV|WI|WY)\b(?!-)')

# The `source` every ATS (employer career site) result uses; its URLs outrank board URLs.
EMPLOYER_SOURCE = 'Employer site'
KINDS = ('linkedin', 'ats', 'board')
STATUSES = ('ok', 'empty', 'partial', 'blocked', 'maintenance', 'skipped', 'error')
# Every source that is a task is expected to answer, so one that was skipped is lost coverage too.
_ATTENTION = frozenset(('partial', 'blocked', 'maintenance', 'skipped', 'error'))

_LEGAL_SUFFIX = re.compile(r'\b(?:pvt|ltd|limited|inc|india|llp|private)\b', re.I)
_DATE_RE = re.compile(r'\d{4}-\d{2}-\d{2}')
_MONEY_UNIT = r'(?P<{}>lpa|lacs?|lakhs?|l|crores?|cr)\b'
_MONEY_RE = re.compile(
    r'(?:(?P<lo>\d+(?:\.\d+)?)\s*(?:' + _MONEY_UNIT.format('lo_unit') + r')?\s*(?:-|–|to)\s*(?:₹|rs\.?|inr)?\s*)?'
    r'(?P<hi>\d+(?:\.\d+)?)\s*' + _MONEY_UNIT.format('hi_unit'), re.I)
_CEILING_RE = re.compile(r'\b(?:up\s?to|max(?:imum)?(?: of)?|below|under)\s*(?:₹|rs\.?|inr)?\s*$', re.I)
_MONTHLY_RE = re.compile(r'/\s*mo\b|\b(?:per|a|p\.?)\s*m(?:onth)?\b|\bmonth(?:ly)?\b|\bpm\b', re.I)
_MAX_LPA = 200            # a larger figure is not an annual salary in lakh
_FOREIGN_CURRENCY_RE = re.compile(r'[$£€¥]|\b(?:usd|gbp|eur|aud|cad|sgd|aed|dollars?|pounds?|euros?)\b', re.I)


def is_pega(text) -> bool:
    return bool(PEGA_RE.search(text or ''))


def _names_abroad(text) -> bool:
    return bool(_FOREIGN_RE.search(text) or _FOREIGN_CODE_RE.search(text))


def cities(text) -> list[str]:
    """Canonical Indian cities named in `text`, in order of appearance, de-duplicated.

    A Bengaluru business park or district counts as Bengaluru only when the text names no
    city of its own and nothing abroad.
    """
    text = text or ''
    found = []
    for match in _CITY_RE.finditer(text):
        city = CITY_ALIASES[re.sub(r'\s+', ' ', match.group(1).lower())]
        if city not in found:
            found.append(city)
    if not found and _LOCALITY_RE.search(text) and not _names_abroad(text):
        found.append('Bengaluru')
    return found


def is_india(text) -> bool:
    """True when the text names an Indian city, state, the country, or an IN country code."""
    text = text or ''
    if cities(text) or _INDIA_RE.search(text) or _INDIA_REGION_RE.search(text):
        return True
    return bool(_INDIA_COUNTRY_RE.search(text)) and not _names_abroad(text)


def outside_india(text) -> bool:
    """True only when the text positively names a foreign country, city or US state and nothing Indian.

    Blank, "Remote", "Work From Home" and "2 Locations" are unknown, not foreign, so they are
    False: a posting should be dropped for its location only when this returns True.
    """
    text = text or ''
    return _names_abroad(text) and not is_india(text)


def is_bengaluru(text) -> bool:
    return 'Bengaluru' in cities(text)


def salary_lpa(text) -> tuple[float | None, float | None]:
    """(low, high) in lakh rupees a year from text such as "20-35 Lacs PA" or "₹8.5L - ₹1.2Cr / yr".

    "Upto ₹20L" is a ceiling only: (None, 20). A band quoted in a foreign currency or per month
    is not LPA and yields (None, None).
    """
    text = str(text or '')
    if _FOREIGN_CURRENCY_RE.search(text) or _MONTHLY_RE.search(text):
        return None, None

    def lakh(amount, unit):
        return float(amount) * (100 if unit.lower().startswith('cr') else 1)
    lows, highs = [], []
    for match in _MONEY_RE.finditer(text):
        high = lakh(match['hi'], match['hi_unit'])
        if match['lo'] is not None:
            # "20-35 Lacs": the first figure borrows the unit of the second.
            lows.append(lakh(match['lo'], match['lo_unit'] or match['hi_unit']))
        elif not _CEILING_RE.search(text[:match.start()]):
            lows.append(high)
        highs.append(high)
    lows = [value for value in lows if 0 < value <= _MAX_LPA]
    highs = [value for value in highs if 0 < value <= _MAX_LPA]
    return (min(lows) if lows else None), (max(highs) if highs else None)


def strip_html(value) -> str:
    """Plain text from an HTML fragment: tags removed, entities decoded, block tags become newlines."""
    text = re.sub(r'(?is)<(script|style)\b[^>]*>.*?</\1\s*>', ' ', str(value or ''))
    text = re.sub(r'(?s)<!--.*?-->', ' ', text)
    text = re.sub(r'(?i)<\s*(?:br|/p|/li|/div|/h[1-6]|/tr|/ul|/ol|/section)\b[^>]*>', '\n', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text).replace('\xa0', ' ')
    text = re.sub(r'[ \t\r\f\v]+', ' ', text)
    text = re.sub(r' ?\n ?', '\n', text)
    return re.sub(r'\n{2,}', '\n', text).strip()


def now_iso() -> str:
    """Current UTC time to the second, e.g. 2026-11-14T02:00:00+00:00."""
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def company_key(name) -> str:
    """Comparison key for an employer name: lowercase alphanumerics without legal suffixes."""
    text = str(name or '').lower()
    key = re.sub(r'[^a-z0-9]', '', _LEGAL_SUFFIX.sub(' ', text))
    # A name made only of suffix words ("India Ltd") still needs a usable key.
    return key or re.sub(r'[^a-z0-9]', '', text)


def _text(value) -> str:
    return str(value).strip() if value is not None else ''


def _number(value):
    try:
        return float(value) if value is not None and value != '' else None
    except (TypeError, ValueError):
        return None


def make_job(source, source_id, title, company, url, location, *, posted_at=None, description='',
             experience_min=None, experience_max=None, salary_min_lpa=None, salary_max_lpa=None,
             apply_url=None, requisition_id=None, employment_type=None, extra=None) -> dict:
    """One posting as a plain dict. Values are tidied, never validated against the network."""
    posted = _DATE_RE.match(_text(posted_at))
    return {
        'source': _text(source),
        'source_id': _text(source_id),
        'title': _text(title)[:300],
        'company': _text(company),
        'url': _text(url),
        'location': _text(location),
        'posted_at': posted.group(0) if posted else None,
        'description': _text(description),
        'experience_min': _number(experience_min),
        'experience_max': _number(experience_max),
        'salary_min_lpa': _number(salary_min_lpa),
        'salary_max_lpa': _number(salary_max_lpa),
        'apply_url': _text(apply_url) or None,
        'requisition_id': _text(requisition_id) or None,
        'employment_type': _text(employment_type) or None,
        'extra': dict(extra) if extra else {},
    }


def make_result(source, label, kind, *, status='ok', jobs=(), found=0, requests=0, error=None,
                sweep_complete=None) -> dict:
    """The outcome of one source. `found` is listings seen, `kept` is Pega roles returned.

    `sweep_complete` is for time-windowed sources: True when every query of the look-back window was
    answered, even if the result is `partial` for another reason. The key is present only when given.
    """
    if status not in STATUSES:
        raise ValueError(f'unknown result status {status!r}')
    if kind not in KINDS:
        raise ValueError(f'unknown result kind {kind!r}')
    jobs = list(jobs)
    result = {'source': source, 'label': label, 'kind': kind, 'status': status,
              'found': max(int(found or 0), len(jobs)), 'kept': len(jobs),
              'requests': int(requests or 0), 'error': _text(error) or None, 'jobs': jobs}
    if sweep_complete is not None:
        result['sweep_complete'] = bool(sweep_complete)
    return result


def csv_cell(value) -> str:
    """One value as CSV text that a spreadsheet will not run as a formula.

    Job text is untrusted. A cell whose first visible character is = + - or @ (or that starts with
    a tab or carriage return) gets a leading apostrophe. Used by `radar.py export` and the server.
    """
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'yes' if value else 'no'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, tuple)):
        text = '; '.join(str(item) for item in value)
    elif isinstance(value, dict):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    risky = text.startswith(('\t', '\r')) or text.lstrip().startswith(('=', '+', '-', '@'))
    return "'" + text if risky else text


def needs_attention(result) -> bool:
    """True when coverage was lost: the source was cut short, refused, down, skipped or broken."""
    return result.get('status') in _ATTENTION


# ───────────────────────────── configuration ─────────────────────────────

DEFAULT_CONFIG = {
    'profile': {'name': 'Sathvik', 'career_start': '2022-08-01', 'city': 'Bengaluru',
                'certifications': ['CSSA'], 'target_lpa': 30, 'current_employer': 'Mercedes-Benz'},
    'focus': {'cities_first': ['Bengaluru'], 'employer_types_first': ['product', 'gcc']},
    'linkedin': {
        # Each phrasing returns a slightly different slice of the public feed.
        'keywords': ['pega', '"pega" OR "PRPC" OR "pegasystems"', 'pega developer', 'pega architect',
                     'pega senior system architect', 'pega CSSA', 'pega lead', 'pega CDH decisioning',
                     'pega engineer'],
        'other_cities': ['Hyderabad, Telangana, India', 'Pune, Maharashtra, India',
                         'Chennai, Tamil Nadu, India', 'Mumbai, Maharashtra, India',
                         'Gurugram, Haryana, India', 'Noida, Uttar Pradesh, India',
                         'Kolkata, West Bengal, India'],
        'detail_budget': 300,
        'pacing_seconds': 1.0,
    },
    'scan': {'minutes': 40, 'workers': 6},
    'server': {'port': 8765},
    'http': {'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                           '(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'},
}


def _merge(defaults, overrides):
    """Overlay `overrides` on `defaults`; nested dicts merge, everything else replaces."""
    merged = copy.deepcopy(defaults)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_config(path=None) -> dict:
    """config.json overlaid on DEFAULT_CONFIG. A missing or unreadable file yields the defaults."""
    loaded = {}
    if path is not None:
        try:
            loaded = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            loaded = {}
    return _merge(DEFAULT_CONFIG, loaded if isinstance(loaded, dict) else {})
