"""Employer classification and fit scoring.

The score (0-100) is a sorting aid built from what a posting says, not a hiring
probability, and nothing is ever dropped for a low score. Weights, largest first:
Pega developer role, Bengaluru, product / GCC employer, experience fit, advertised
salary, recency.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from .model import CITY_ALIASES, PEGA_RE, cities, company_key

EMPLOYER_TYPES = ('product', 'gcc', 'enterprise', 'services', 'staffing', 'unknown')
# A portal is one employer career board. Only verified and candidate portals are scanned.
PORTAL_STATES = ('verified', 'candidate', 'wrong_scope', 'unsupported')
SCANNABLE_STATES = ('verified', 'candidate')
PORTAL_SCOPES = ('india', 'global', 'unknown')
TARGET_RESOLUTIONS = ('matched', 'added', 'related', 'unresolved')

# ── score weights ──
W_PEGA_DEV_TITLE = 30     # the title names Pega and it is a developer-track role
W_PEGA_DUTY_ONLY = 16     # the title does not name Pega but the description shows Pega duties
W_PEGA_NON_DEV = 6        # Pega in the title of a testing / BA / support role
W_PEGA_DUTY = 10          # description confirms hands-on Pega work
W_FOCUS_CITY = 24
W_CITY_UNSTATED = 4       # could still be Bengaluru
W_OTHER_CITY = 2
W_EMPLOYER = {'product': 16, 'gcc': 16, 'enterprise': 8, 'unknown': 4, 'services': -4, 'staffing': -6}
W_EXPERIENCE_FITS = 10
W_EXPERIENCE_STRETCH = 4
W_SALARY = 6
W_CERTIFICATION = 3
W_FRESH = 4               # posted within a week
W_RECENT = 2              # posted within a month
P_NON_DEV = 25
P_ASKS_8_PLUS = 25
P_ASKS_MORE = 8
P_CAPPED_BELOW = 12
P_SENIOR_TITLE = 15
P_JUNIOR_TITLE = 15
P_STALE = 10              # older than STALE_DAYS
STALE_DAYS = 60
MAX_PLAUSIBLE_LPA = 200   # anything larger is not a figure in lakh rupees a year
STRETCH_YEARS = 1.7       # how far above the candidate's tenure a minimum may sit and still be a stretch

# ── employer name patterns: the fallback when companies.json has no entry ──
_SERVICES = re.compile(
    r'\btcs\b|tata consultancy|infosys|wipro|\bhcl|tech mahindra|cognizant|capgemini|accenture|ltimindtree|\blti\b|'
    r'mindtree|mphasis|virtusa|coforge|hexaware|persistent|birlasoft|zensar|\bdxc\b|\bntt\b|\batos\b|eviden|unisys|'
    r'genpact|\bibm\b|deloitte|\bey\b|ernst|\bpwc\b|pricewaterhouse|kpmg|areteans|evonsys|aaseya|\byash\b|sonata|'
    r'cyient|synechron|iris software|incedo|happiest minds|sopra|\bcgi\b|publicis|merkle|truviq|bits in glass|'
    r'rulesware|srm tech|kanini|maantic|\bust\b|quest global|altimetrik|nagarro|globallogic|\bepam\b', re.I)
_PRODUCT = re.compile(
    r'pegasystems|salesforce|servicenow|\boracle\b|\bsap\b|adobe|microsoft|google|amazon|\buber\b|paypal|\bcisco\b|'
    r'\bdell\b|\bintel\b|mastercard|\bvisa\b|booking|fiserv|broadridge|transunion|experian|equifax|thomson reuters|'
    r'philips|medtronic|siemens|bosch', re.I)
_GCC = re.compile(
    r'jpmorgan|jpmc|goldman|morgan stanley|wells fargo|\bciti\b|citigroup|citibank|barclays|deutsche|\bubs\b|natwest|'
    r'standard chartered|american express|\bamex\b|fidelity|\bbny\b|state street|northern trust|commonwealth bank|'
    r'commbank|\banz\b|\bnab\b|macquarie|lloyds|hsbc|\boptum\b|unitedhealth|elevance|carelon|\bcigna\b|evernorth|\bcvs\b|'
    r'walmart|\btarget\b|\blowe\'?s\b|verizon|t-mobile|comcast|\bnike\b|synchrony|capital one|discover financial|'
    r'swiss re|allianz|metlife|prudential|sun life|manulife|first citizens|maersk|telstra|\bbt group\b|'
    r'mercedes|daimler|\bing\b|rabobank|societe generale|\bbnp\b|credit suisse|franklin templeton|blackrock|nomura|'
    r'\bmufg\b|mizuho|\baig\b|\bchubb\b|\bzurich\b|\baviva\b|\bvoya\b|ameriprise|charles schwab|vanguard|invesco|airbus|boeing|'
    r'ge healthcare|novartis|pfizer|astrazeneca|\bmerck\b|\bmsd\b|\broche\b', re.I)
# Indian domestic employers running their own IT.
_ENTERPRISE = re.compile(
    r'\bhdfc\b|\bicici\b|\bkotak\b|\bitc\b|axis bank|state bank of india|\bsbi\b|\bbajaj\b|\breliance\b|'
    r'\bairtel\b|\bjio\b|yes bank|indusind|\bidfc\b', re.I)
_STAFFING = re.compile(
    r'staffing|recruit|talent|manpower|consultanc|placement|hr solutions|careernet|huntingcube|randstad|adecco|'
    r'teamlease|quess|collabera|artech|mastech|hiring|resourc|\bjobs?\b|search partners|people ?tech', re.I)

# ── title patterns ──
_PEGA_CERTIFICATION = re.compile(r'\b(?:cssa|clsa|lsa|csa)\b', re.I)   # in a title these mean Pega
_JUNIOR = re.compile(r'\b(?:intern|internship|fresher|trainee|graduate|apprentice|junior|jr|entry[- ]level|'
                     r'associate system architect)\b', re.I)
_NON_DEV = re.compile(r'\b(?:test(?:er|ing)?|qa|quality|sdet|business (?:analyst|architect)|ba|product owner|'
                      r'scrum master|support|admin(?:istrator)?|sales|pre-?sales|recruit\w*|trainer|operations)\b', re.I)
# A title that also names one of these is a build role even if it mentions support or testing.
_DEV_TRACK = re.compile(r'\b(?:developer|programmer|cssa|ssa|system architect|software engineer)\b', re.I)
_LEAD_SYSTEM_ARCHITECT = re.compile(r'\blead\s+system\s+architect\b', re.I)
# "Senior System Architect" is the CSSA-level developer role, not an architect-only one.
_SYSTEM_ARCHITECT = re.compile(r'\b(?:senior\s+|sr\.?\s+)?system\s+architect\b', re.I)
_SENIOR_ONLY = re.compile(r'\b(?:lead|architect|lsa|clsa|principal|director|head|vp|avp|vice president|manager)\b', re.I)

# ── description patterns (Pega duties) ──
_BOILER_HEADING = re.compile(
    r'^(?:about\s+(?:us|the company|our company|the employer|pega|pegasystems)|who we are|our (?:company|clients|'
    r'partners|story)|company (?:overview|profile)|equal opportunity|benefits|what we offer|why (?:join|work).*|'
    r'diversity(?: and inclusion)?|privacy|similar jobs|recommended jobs)\s*[:.?]?$', re.I)
_ROLE_HEADING = re.compile(
    r'^(?:(?:your |key |main |job |roles? (?:and|&) )?(?:responsibilities|duties|qualifications|requirements|skills)|'
    r'required (?:skills|qualifications|experience)|preferred (?:skills|qualifications)|about (?:the |this )?(?:role|job)|'
    r'what you(?: will|\'ll) do|job (?:description|summary)|experience|technical skills)\s*[:.?]?$', re.I)
_ORG_PROSE = re.compile(
    # "We are a leading ..." is about the company; "We are looking for / hiring ..." is about the role.
    r'\b(?:our (?:company|partners?|clients?|customers?|services?|portfolio|firm)|'
    r'we (?:are(?! (?:looking|hiring|seeking|searching|recruiting|in need|on the lookout))|partner|serve|offer|provide)|'
    r'company (?:has|offers|provides)|leading (?:provider|consultancy|company)|certified partner|'
    r'pegasystems (?:is|helps|enables)|pega (?:is (?:a|an|the)|helps|enables))\b', re.I)
_OPTIONAL = re.compile(r'\b(?:preferred|desirable|nice[- ]to[- ]have|optional|a plus|added advantage|bonus|beneficial)\b', re.I)
_MANDATORY = re.compile(r'\b(?:mandatory|required|must|essential|minimum|at least|need to|shall)\b', re.I)
_ACTION = re.compile(
    r'\b(?:develop(?:er|ment|ing)?|design(?:ing)?|build(?:ing)?|implement(?:ation|ing)?|configur(?:e|ing|ation)|'
    r'maintain(?:ing)?|architect(?:ure|ing)?|debug(?:ging)?|deliver(?:ing)?|troubleshoot(?:ing)?|hands[- ]on|'
    r'proficien(?:t|cy)|expertise|experience|knowledge|certifi(?:ed|cation)|programming|coding)\b', re.I)
_ALT_PLATFORM = r'(?:appian|salesforce|servicenow|mendix|outsystems|camunda|power\s*apps|java|\.net)'
# "Pega or Appian": Pega is one acceptable option, not the job.
_ALTERNATIVE = re.compile(
    rf'(?:\b(?:pega|prpc)\b\s*(?:,\s*{_ALT_PLATFORM}\s*)?(?:or|/|and/or)\s*{_ALT_PLATFORM}\b|'
    rf'\b{_ALT_PLATFORM}\s*(?:or|/|and/or)\s*(?:pega|prpc)\b|(?:any|one)\s+of[^.;\n]{{0,70}}\b(?:pega|prpc)\b)', re.I)
_NOT_NEEDED = re.compile(r'\b(?:no|without|not require[ds]?)\s+(?:prior\s+)?pega\b|'
                         r'\bpega\s+(?:experience\s+)?(?:not required|is optional)\b', re.I)
# A line made only of these words is a repeated job title, not a duty.
_TITLE_WORDS = frozenset(
    'pega prpc pegarules pegasystems developer developers engineer engineers architect architects system systems '
    'senior junior lead principal staff associate technical consultant analyst manager job title role position '
    'sr jr ii iii iv'.split())

# ── experience patterns ──
_NUMBER_WORDS = {'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8,
                 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15}
_NUMBER_WORD = re.compile(r'\b(' + '|'.join(_NUMBER_WORDS) + r')\b')
_UNIT = r'(?:years?|yrs?|months?|mos)'
_NUM = r'\d+(?:\.\d+)?'
_RANGE = re.compile(rf'(?<![\w.])(?P<lo>{_NUM})\s*(?P<u1>{_UNIT})?\s*(?:-|–|—|to|and)\s*(?P<hi>{_NUM})\s*\+?\s*(?P<u2>{_UNIT})\b', re.I)
_SINGLE = re.compile(rf'(?<![\w.])(?P<n>{_NUM})\s*\+?\s*(?P<u>{_UNIT})\b', re.I)
_UPPER_ONLY = re.compile(r'\b(?:less than|under|fewer than|up to|upto|maximum(?: of)?|max|at most|no more than)\s*$', re.I)
_EXPERIENCE_CONTEXT = re.compile(r'\b(?:experience|experienced|exp|overall|total|relevant|hands[- ]on|minimum|at least)\b', re.I)
# Years that describe the company or a person's age, not the requirement.
_NOT_A_REQUIREMENT = re.compile(
    r'\b(?:our company|our firm|our team|company has|company with|we have|we bring|we offer|founded|established|'
    r'in business|serving clients|industry leader|combined experience|years? (?:of age|old)|years ago|for over)\b', re.I)
# "6 Months Contract", "contract of 12 months", "notice period 2 months": a duration, not a requirement.
_DURATION_AFTER = re.compile(r'^\s*[-(]?\s*(?:contract|c2h|duration|project|assignment|engagement|extend\w*|extension|'
                             r'notice|bond|internship|probation|term)\b', re.I)
_DURATION_BEFORE = re.compile(r'\b(?:contract|c2h|duration|tenure|notice(?: period)?|bond|probation|internship)'
                              r'\W{0,3}(?:of|for|is|period)?\W{0,3}$', re.I)
_SHORT_TEXT = 60          # a field such as "4-7 Yrs" needs no context word
_MAX_YEARS = 40


# ───────────────────────────── employer registry ─────────────────────────────

# Words that may follow an employer's name without making it a different employer
# ("Intel Technology India", "Shell Business Operations").
_GENERIC_WORDS = frozenset(
    'and of the co company corp corporation group holdings global international worldwide technology technologies '
    'tech services solutions systems software labs digital business operations enterprise enterprises bank banking '
    'financial finance capital markets insurance healthcare health research development center centre capability '
    'gcc gbs hub shared support'.split())
_LEGAL_WORDS = frozenset('pvt ltd limited inc india llp private'.split())
_MIN_PARTIAL_KEY = 5      # shorter names ("CBA", "EY", "UST") match exactly or not at all


def _name_words(name):
    return tuple(word for word in re.findall(r'[a-z0-9]+', str(name or '').lower()) if word not in _LEGAL_WORDS)


def _same_employer(short, long):
    """True when `short` is the leading whole words of `long` and what follows cannot name someone else.

    Whole words, never substrings: "Intellect Design Arena" is not Intel and "San Francisco Health"
    is not Cisco. A one-word name also needs the rest to be generic, so "Shell Infotech" is not Shell.
    """
    if not short or len(short) >= len(long) or long[:len(short)] != short or len(''.join(short)) < _MIN_PARTIAL_KEY:
        return False
    return len(short) >= 2 or all(word in _GENERIC_WORDS for word in long[len(short):])


def employer_portals(entry) -> list[dict]:
    """The career boards configured for a companies.json entry, as a list of portal dicts.

    The v1 `ats` block is read as one verified portal (it was in the live-checked baseline).
    Every portal comes back with `kind`, `state` and `scope` filled in.
    """
    listed = entry.get('portals')
    portals = [dict(portal) for portal in listed if isinstance(portal, dict)] if isinstance(listed, list) else []
    legacy = entry.get('ats')
    if not portals and isinstance(legacy, dict):
        portals = [{**legacy, 'state': 'verified'}]
    for portal in portals:
        portal['kind'] = str(portal.get('kind') or '')
        if portal.get('state') not in PORTAL_STATES:
            portal['state'] = 'candidate'        # an unknown state is never trusted as verified
        if portal.get('scope') not in PORTAL_SCOPES:
            portal['scope'] = 'unknown'
    return portals


def _employer(entry) -> dict:
    kind = entry.get('type')
    return {'name': entry['name'], 'aliases': [str(alias) for alias in entry.get('aliases') or []],
            'type': kind if kind in EMPLOYER_TYPES else 'unknown',
            'bengaluru': entry.get('bengaluru') if isinstance(entry.get('bengaluru'), bool) else None,
            'linkedin_query': entry.get('linkedin_query') is True, 'parent': entry.get('parent') or None,
            'career_url': entry.get('career_url') or None, 'portals': employer_portals(entry),
            'inventory_note': entry.get('inventory_note') or None,
            'current_employer': entry.get('current_employer') is True}


class Registry:
    """companies.json in memory. Works with no entries at all (name patterns only)."""

    def __init__(self, entries=()):
        self.entries = [entry for entry in entries if isinstance(entry, dict) and entry.get('name')]
        self._index = {}        # company_key -> entry; first entry wins on a duplicate name
        self._names = []        # (words, entry) for whole-word matching
        self._found = {}        # memo: postings repeat the same few hundred employer names
        for entry in self.entries:
            for name in [entry['name'], *(entry.get('aliases') or [])]:
                key = company_key(name)
                if key and key not in self._index:
                    self._index[key] = entry
                    self._names.append((_name_words(name), entry))

    def __len__(self):
        return len(self.entries)

    @property
    def employers(self) -> list[dict]:
        """Every employer in a uniform shape: identity, careers page and its `portals`."""
        return [_employer(entry) for entry in self.entries]

    def find(self, company) -> dict | None:
        """The registry entry for a company name: exact key, then whole-word matches only."""
        key = company_key(company)
        if not key:
            return None
        if key not in self._found:
            entry = self._index.get(key)
            words = _name_words(company)
            if entry is None:
                # "JPMorgan Chase & Co." is "JPMorganChase" once the trailing generic words are dropped.
                core = list(words)
                while core and core[-1] in _GENERIC_WORDS:
                    core.pop()
                if len(''.join(core)) >= _MIN_PARTIAL_KEY:
                    entry = self._index.get(''.join(core))
            if entry is None:
                matches = [(len(''.join(known)), index) for index, (known, _) in enumerate(self._names)
                           if _same_employer(known, words) or _same_employer(words, known)]
                if matches:
                    # The longest name is the most specific; file order settles a tie.
                    entry = self._names[max(matches, key=lambda match: (match[0], -match[1]))[1]][1]
            self._found[key] = entry
        return self._found[key]

    def canonical_key(self, company) -> str:
        """company_key of the registry name when the company is known, else of the name as given."""
        entry = self.find(company)
        return company_key(entry['name'] if entry is not None else company)

    def classify(self, company) -> tuple[str, dict | None]:
        entry = self.find(company)
        if entry is not None:
            kind = entry.get('type')
            return (kind if kind in EMPLOYER_TYPES else 'unknown'), entry
        name = str(company or '')
        for kind, pattern in (('services', _SERVICES), ('product', _PRODUCT), ('gcc', _GCC),
                              ('enterprise', _ENTERPRISE), ('staffing', _STAFFING)):
            if pattern.search(name):
                return kind, None
        return 'unknown', None


def load_registry(path) -> Registry:
    """Read companies.json. A missing, empty or malformed file gives a pattern-only Registry."""
    try:
        document = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError, TypeError):
        return Registry()
    companies = document.get('companies') if isinstance(document, dict) else document
    return Registry(companies if isinstance(companies, list) else ())


def load_targets(path) -> list[dict]:
    """The rows of targets.json, the original target inventory that coverage is measured against.

    A missing or malformed file is an empty inventory, not an error: coverage then lists the
    registry's employers only.
    """
    try:
        document = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError, TypeError):
        return []
    rows = document.get('rows') if isinstance(document, dict) else document
    targets = []
    for row in rows if isinstance(rows, list) else ():
        if not isinstance(row, dict) or not row.get('original_name'):
            continue
        resolution = row.get('resolution')
        targets.append({'row': row.get('row'), 'original_name': str(row['original_name']),
                        'original_url': row.get('original_url') or None, 'employer': row.get('employer') or None,
                        'resolution': resolution if resolution in TARGET_RESOLUTIONS else 'unresolved',
                        'note': row.get('note') or None})
    return targets


# ───────────────────────────── text evidence ─────────────────────────────

def _sentences(text):
    return [re.sub(r'^\s*[•*\-]\s*', '', part).strip()
            for part in re.split(r'\n+|(?<=[.!?;])\s+(?=[A-Z0-9•*])', text or '') if part.strip()]


def has_pega_duty(description) -> bool:
    """True when Pega appears in a sentence about the work itself, not only in company boilerplate."""
    in_boilerplate = False
    for sentence in _sentences(description):
        if _BOILER_HEADING.match(sentence):
            in_boilerplate = True
            continue
        if _ROLE_HEADING.match(sentence):
            in_boilerplate = False
            continue
        if in_boilerplate or not PEGA_RE.search(sentence):
            continue
        if _ORG_PROSE.search(sentence) or _NOT_NEEDED.search(sentence) or _ALTERNATIVE.search(sentence):
            continue
        if set(re.findall(r'[a-z]+', sentence.lower())) <= _TITLE_WORDS:
            continue
        if _OPTIONAL.search(sentence) and not _MANDATORY.search(sentence):
            continue
        if _ACTION.search(sentence) or _MANDATORY.search(sentence):
            return True
    return False


def _years(value, unit):
    number = float(value)
    return round(number / 12, 2) if unit.lower().startswith('mo') else number


def _is_duration(sentence, match) -> bool:
    return bool(_DURATION_AFTER.search(sentence[match.end():]) or _DURATION_BEFORE.search(sentence[:match.start()]))


def parse_experience(text) -> tuple[float | None, float | None]:
    """(minimum, maximum) years asked for in free text; None where the text does not say.

    "4-7 years" -> (4, 7); "5+ yrs" -> (5, None); "minimum 6 years" -> (6, None);
    "up to 3 years" -> (None, 3). With several statements the highest minimum wins.
    """
    text = str(text or '')
    short = len(text) <= _SHORT_TEXT
    lows, highs = [], []
    for sentence in _sentences(text):
        in_context = bool(_EXPERIENCE_CONTEXT.search(sentence))
        if _NOT_A_REQUIREMENT.search(sentence) or not (short or in_context):
            continue
        sentence = _NUMBER_WORD.sub(lambda match: str(_NUMBER_WORDS[match.group(1)]), sentence.lower())

        def counts(match, unit):
            # Months are how contracts are measured, so they need an experience word beside them.
            return not _is_duration(sentence, match) and (in_context or not unit.startswith('mo'))
        taken = []
        for match in _RANGE.finditer(sentence):
            taken.append(match.span())
            low, high = _years(match['lo'], match['u1'] or match['u2']), _years(match['hi'], match['u2'])
            if low <= high <= _MAX_YEARS and counts(match, match['u2']):
                lows.append(low)
                highs.append(high)
        for match in _SINGLE.finditer(sentence):
            if any(start <= match.start() < end for start, end in taken) or not counts(match, match['u']):
                continue
            amount = _years(match['n'], match['u'])
            if amount > _MAX_YEARS:
                continue
            if _UPPER_ONLY.search(sentence[:match.start()]):
                highs.append(amount)
            else:
                lows.append(amount)
    minimum = max(lows) if lows else None
    maximum = max(highs) if highs else None
    if minimum is not None and maximum is not None and maximum < minimum:
        maximum = None   # the range belonged to a lesser requirement; the upper limit is unknown
    return minimum, maximum


def _stated_experience(job):
    """The experience range to judge a job by: the source's numbers, else what its text says.

    Boards send 0/0 for "not stated", so zeros carry no information and a maximum of 0 is never a
    cap. When both the title and the description state a requirement the stricter one is used,
    so "Pega Developer (3-5 yrs)" does not hide "Minimum 9 years" in the description.
    """
    low, high = job.get('experience_min') or None, job.get('experience_max') or None
    if low is not None or high is not None:
        return low, high
    from_title = parse_experience(job.get('title'))
    from_text = parse_experience(job.get('description'))
    if from_text == (None, None) or (from_title[0] or 0) > (from_text[0] or 0):
        return from_title
    return from_text


def _is_senior_only(title) -> bool:
    text = _LEAD_SYSTEM_ARCHITECT.sub(' lsa ', title)
    return bool(_SENIOR_ONLY.search(_SYSTEM_ARCHITECT.sub(' ', text)))


def _years_label(low, high) -> str:
    if low is None and high is None:
        return 'not stated'
    if low is None:
        return f'up to {high:g} yrs'
    return f'{low:g}-{high:g} yrs' if high is not None else f'{low:g}+ yrs'


def _parse_date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


# ───────────────────────────── ranker ─────────────────────────────

def make_ranker(config, registry, today=None):
    """Build `ranker(job) -> {'employer_type', 'score', 'fit', 'pega_title', 'pega_duty'}`.

    `job` is a make_job() dict or a stored job row; only its text and number fields are read.
    """
    profile = config.get('profile') or {}
    focus = config.get('focus') or {}
    today = today or date.today()
    career_start = _parse_date(profile.get('career_start')) or date(2022, 8, 1)
    tenure = max(0.0, (today - career_start).days / 365.25)
    try:
        target = float(profile.get('target_lpa') or 30)
    except (TypeError, ValueError):
        target = 30.0
    focus_cities = {CITY_ALIASES.get(str(city).lower(), str(city)) for city in focus.get('cities_first') or ['Bengaluru']}
    focus_types = set(focus.get('employer_types_first') or ['product', 'gcc'])
    held = [re.escape(str(name)) for name in profile.get('certifications') or [] if name]
    certification = re.compile(r'\b(?:' + '|'.join(held) + r')\b', re.I) if held else None
    own_words = _name_words(profile.get('current_employer'))
    own_entry = registry.find(profile.get('current_employer'))

    flagged = any(entry.get('current_employer') is True for entry in registry.entries)

    def is_current_employer(company, entry):
        if entry is not None and flagged:
            # The registry names the exact entity. Its parent group and sister companies share the
            # name's first words but are separate employers, so the config name is not consulted.
            return entry.get('current_employer') is True
        if entry is not None and entry is own_entry:
            return True
        words = _name_words(company)
        return bool(own_words) and (words == own_words or _same_employer(own_words, words))

    def ranker(job):
        title = job.get('title') or ''
        description = job.get('description') or ''
        reasons = []
        score = 0

        # 1. Is it a Pega developer role?
        pega_title = bool(PEGA_RE.search(title) or _PEGA_CERTIFICATION.search(title))
        pega_duty = has_pega_duty(description)
        non_dev = bool(_NON_DEV.search(title)) and not _DEV_TRACK.search(title)
        if non_dev:
            score += (W_PEGA_NON_DEV if pega_title else 0) - P_NON_DEV
            reasons.append('Not a developer role')
        elif pega_title:
            score += W_PEGA_DEV_TITLE
        elif pega_duty:
            score += W_PEGA_DUTY_ONLY
        if pega_duty:
            score += W_PEGA_DUTY
            reasons.append('Pega duties confirmed in the description')
        elif not description:
            reasons.append('Description not read yet')
        elif not pega_title:
            reasons.append('Pega is only mentioned in passing')

        # 2. Bengaluru (or whichever cities the config puts first)
        job_cities = job.get('cities') or cities(job.get('location'))
        in_focus = [city for city in job_cities if city in focus_cities]
        if in_focus:
            score += W_FOCUS_CITY
            reasons.append(in_focus[0])
        elif job_cities:
            score += W_OTHER_CITY
        else:
            score += W_CITY_UNSTATED
            reasons.append('City not stated')

        # 3. Employer type
        employer_type, entry = registry.classify(job.get('company'))
        weight = W_EMPLOYER[employer_type]
        if employer_type in ('product', 'gcc') and employer_type not in focus_types:
            weight = W_EMPLOYER['unknown']
        score += weight
        reasons.append({'product': 'Product company', 'gcc': 'Captive centre (GCC)',
                        'enterprise': 'Indian enterprise (in-house IT)', 'services': 'Services company',
                        'staffing': 'Recruiter or staffing firm', 'unknown': 'Employer type unknown'}[employer_type])

        # 4. Experience: stated numbers first, title words only when nothing is stated
        low, high = _stated_experience(job)
        junior = bool(_JUNIOR.search(title))
        if low is not None or high is not None:
            if high is not None and high < tenure - 0.5:
                score -= P_CAPPED_BELOW
                reasons.append(f'Capped at {high:g} years')
            elif low is None or low <= tenure:
                score += W_EXPERIENCE_FITS
                reasons.append('Experience range fits')
            elif low <= tenure + STRETCH_YEARS:
                score += W_EXPERIENCE_STRETCH
                reasons.append(f'Asks {low:g}+ years (stretch)')
            elif low >= 8:
                score -= P_ASKS_8_PLUS
                reasons.append(f'Asks {low:g}+ years')
            else:
                score -= P_ASKS_MORE
                reasons.append(f'Asks {low:g}+ years')
        elif _is_senior_only(title):
            score -= P_SENIOR_TITLE
            reasons.append('Lead or architect title; likely 8+ years')
        elif junior:
            score -= P_JUNIOR_TITLE
            reasons.append('Junior title')

        # 5. Advertised salary against the target
        advertised = job.get('salary_max_lpa') or job.get('salary_min_lpa')
        if advertised is not None and not 0 < advertised <= MAX_PLAUSIBLE_LPA:
            advertised = None                        # a foreign-currency or monthly figure, not LPA
        if advertised is not None:
            if advertised >= target:
                score += W_SALARY
                reasons.append(f'Advertised up to {advertised:g} LPA')
            elif advertised < target * 2 / 3:
                score -= W_SALARY
                reasons.append(f'Advertised only up to {advertised:g} LPA')
            pay = f'up to {advertised:g} LPA'
        elif employer_type in ('product', 'gcc') and not junior:
            pay = f'{target:g}+ plausible'
        elif employer_type == 'services':
            pay = f'{target:g}+ unlikely'
        else:
            pay = 'pay unknown'

        if certification and certification.search(title + '\n' + description):
            score += W_CERTIFICATION
            reasons.append('Names a certification you hold')

        # 6. Recency
        posted = _parse_date(job.get('posted_at'))
        if posted:
            age = (today - posted).days
            if age > STALE_DAYS:
                score -= P_STALE
                reasons.append(f'Posted over {STALE_DAYS} days ago; may be stale')
            elif age <= 7:
                score += W_FRESH
            elif age <= 30:
                score += W_RECENT

        # The candidate's own employer is kept, labelled and sorted last: it is not an opening to chase.
        current = is_current_employer(job.get('company'), entry)
        if current:
            reasons.insert(0, 'Current employer')
        return {'employer_type': employer_type, 'score': 0 if current else max(0, min(100, round(score))),
                'fit': {'reasons': reasons,
                        'labels': {'employer_type': employer_type, 'pay': pay, 'experience': _years_label(low, high),
                                   'bengaluru': 'Bengaluru' in job_cities, 'current_employer': current}},
                'pega_title': pega_title, 'pega_duty': pega_duty}

    # Lets the store key a job by its registry employer, so "Commonwealth Bank of Australia" on one
    # site and "Commonwealth Bank" on another are recognised as the same company.
    ranker.canonical = registry.canonical_key
    return ranker
