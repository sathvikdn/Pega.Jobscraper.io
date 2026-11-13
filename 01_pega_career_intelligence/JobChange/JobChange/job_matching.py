"""Conservative Pega relevance and explainable resume/JD comparison.

No employer, query, search snippet, inferred skill, or job title is proof that a
role uses Pega. Only the saved, successfully read full job description is used.
The score compares written evidence, and is not an ATS or hiring prediction.
"""
from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
import re

from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parent
DEFAULT_RESUME = BASE / 'sathvik_resume_v2.html'
PEGA = re.compile(r'\b(?:pega(?:rules)?|prpc)\b', re.I)
YEAR_WORDS = {'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
              'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
              'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
              'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
              'nineteen': 19, 'twenty': 20, 'thirty': 30}
UNIT = r'(?:years?|yrs?|months?|mos?)'
NUM = r'\d+(?:\.\d+)?'
RANGE = re.compile(rf'(?<![\w.])(?:between\s+)?(?P<lo>{NUM})\s*(?P<u1>{UNIT})?\s*(?:[-–—]|to|and)\s*(?P<hi>{NUM})\s*(?P<u2>{UNIT})\b', re.I)
SINGLE = re.compile(rf'(?<![\w.])(?P<n>{NUM})\s*(?P<plus>\+)?\s*(?P<u>{UNIT})\b', re.I)
BOILER_HEADING = re.compile(r'^(?:about\s+(?:us|the company|our company|the employer|pega|pegasystems)|who we are|our (?:company|clients|partners|story)|company (?:overview|profile)|equal opportunity|benefits|what we offer|why (?:join|work)|diversity(?: and inclusion)?|privacy|similar jobs|recommended jobs)\s*[:.?]?$', re.I)
ROLE_HEADING = re.compile(r'^(?:(?:your |key |main |job )?(?:responsibilities|duties|qualifications|requirements|skills)|required (?:skills|qualifications|experience)|preferred (?:skills|qualifications)|about (?:the |this )?(?:role|job)|what you(?: will|\x27ll) do|job (?:description|summary)|experience|technical skills)\s*[:.?]?$', re.I)
ORG_PROSE = re.compile(r'\b(?:our (?:company|partners?|clients?|customers?|services?|portfolio|firm)|we (?:are|partner|serve|offer|provide)|company (?:has|offers|provides)|leading (?:provider|consultancy|company)|certified partner|pega(?:systems)? (?:is|helps|enables))\b', re.I)
OPTIONAL = re.compile(r'\b(?:preferred|desirable|nice[- ]to[- ]have|optional|a plus|added advantage|bonus|beneficial)\b', re.I)
MANDATORY = re.compile(r'\b(?:mandatory|required|must|essential|minimum|at least|need to|shall)\b', re.I)
ACTION = re.compile(r'\b(?:develop(?:er|ment|ing)?|design(?:ing)?|build(?:ing)?|implement(?:ation|ing)?|configur(?:e|ing|ation)|maintain(?:ing)?|architect(?:ure|ing)?|debug(?:ging)?|deliver(?:ing)?|troubleshoot(?:ing)?|hands[- ]on|proficien(?:t|cy)|expertise|experience|knowledge|certifi(?:ed|cation)|programming|coding)\b', re.I)
ALT_PLATFORM = r'(?:appian|salesforce|servicenow|mendix|outsystems|camunda|power\s*apps|java|\.net)'
ALTERNATIVE_PEGA = re.compile(rf'(?:\b(?:pega|prpc)\b\s*(?:,\s*{ALT_PLATFORM}\s*)?(?:or|/|and/or)\s*{ALT_PLATFORM}\b|\b{ALT_PLATFORM}\s*(?:or|/|and/or)\s*(?:pega|prpc)\b|(?:any|one)\s+of[^.;\n]{{0,70}}\b(?:pega|prpc)\b)', re.I)
INCIDENTAL = re.compile(r'\b(?:integrat(?:e|es|ion|ions|ing)|interfac(?:e|es|ing)|connect(?:ing)?|interact(?:ing)?)\b[^.;\n]{0,60}\b(?:with|to|into)\s+(?:the\s+)?(?:pega|prpc)\b', re.I)
EXPERIENCE_ORG = re.compile(r'\b(?:our company|our firm|our team|company has|company with|we have|we bring|we offer|founded|in business|serving clients|industry leader|combined experience)\b', re.I)

# Explicit, bounded vocabulary; a generic decision rule is never CDH evidence.
SKILLS = [
 ('Pega platform', r'\b(?:pega(?:rules)?|prpc)\b', 'technology'),
 ('Case management', r'\bcase (?:management|types?|life[- ]?cycle)\b', 'technology'),
 ('Data pages', r'\bdata pages?\b', 'technology'),
 ('Data transforms', r'\bdata transforms?\b', 'technology'),
 ('Declarative rules', r'\bdeclarative rules?\b', 'technology'),
 ('SLAs', r'\b(?:slas?|service[- ]level agreements?)\b', 'technology'),
 ('REST', r'\brest(?:ful)?\b|\bservice-rest\b', 'technology'),
 ('SOAP', r'\bsoap\b', 'technology'),
 ('Kafka', r'\bkafka\b', 'technology'),
 ('SQL', r'\b(?:sql|connect-sql|stored procedures?)\b', 'technology'),
 ('OAuth', r'\boauth(?:\s*2(?:\.0)?)?\b', 'technology'),
 ('SFTP', r'\bsftp\b', 'technology'),
 ('Queue processors', r'\bqueue processors?\b', 'technology'),
 ('Data flows', r'\bdata flows?\b', 'technology'),
 ('Constellation', r'\bconstellation\b', 'technology'),
 ('DX API', r'\bdx\s*apis?\b', 'technology'),
 ('Pega GenAI', r'\b(?:pega\s+)?genai\b', 'technology'),
 ('Pega Knowledge Buddy', r'\b(?:pega\s+(?:genai\s+)?)?knowledge\s*buddy\b', 'technology'),
 ('Pega Blueprint', r'\b(?:pega\s+(?:genai\s+)?blueprint|(?-i:Blueprint))\b', 'technology'),
 ('Customer Decision Hub / CDH', r'\b(?:customer decision hub|cdh)\b', 'technology'),
 ('Next Best Action', r'\b(?:next[- ]best[- ]action|nba designer)\b', 'technology'),
 ('Adaptive models', r'\badaptive (?:models?|decision manager)\b|\badm\b', 'technology'),
 ('Pega Customer Service / CPM', r'\b(?:pega customer service|cpm)\b', 'technology'),
 ('Pega Robotics', r'\b(?:pega robotics|openspan)\b', 'technology'),
 ('PDC', r'\b(?:pdc|predictive diagnostic cloud)\b', 'technology'),
 ('Tracer / PAL', r'\b(?:tracer|pal|performance analyzer)\b', 'technology'),
 ('Deployment Manager', r'\bdeployment manager\b', 'technology'),
 ('Java', r'\bjava\b', 'technology'),
 ('JavaScript', r'\bjavascript\b', 'technology'),
 ('React', r'\breact(?:js|\.js)?\b', 'technology'),
 ('Agile / Scrum', r'\b(?:agile|scrum)\b', 'technology'),
 ('Production support', r'\b(?:production support|l2/l3 support|incident (?:analysis|response|management))\b', 'technology'),
 ('CSA certification', r'\b(?:csa|pcsa|certified system architect)\b', 'certification'),
 ('CSSA certification', r'\b(?:cssa|pcssa|certified senior system architect)\b', 'certification'),
 ('CLSA certification', r'\b(?:clsa|pclsa|certified lead system architect)\b', 'certification'),
 ('CPDC certification', r'\b(?:cpdc|pcpdc|certified (?:pega )?decisioning consultant)\b', 'certification'),
]
COMPILED_SKILLS = [(name, re.compile(pattern, re.I), kind) for name, pattern, kind in SKILLS]


def plain_text(value):
    """Drop executable/hidden metadata before considering any textual evidence."""
    text = str(value or '')
    if re.search(r'<[a-zA-Z!/][^>]*>', text):
        soup = BeautifulSoup(text, 'html.parser')
        for element in soup(['script', 'style', 'noscript', 'head', 'template', 'svg']):
            element.decompose()
        for element in soup.select('[hidden], [aria-hidden="true"]'):
            element.decompose()
        for element in soup.select('[style]'):
            if re.search(r'(?:display\s*:\s*none|visibility\s*:\s*hidden)', element.get('style', ''), re.I):
                element.decompose()
        for element in soup.find_all('br'):
            element.replace_with('\n')
        for element in soup.find_all(['p', 'li', 'div', 'h1', 'h2', 'h3', 'h4', 'section']):
            element.append('\n')
        text = soup.get_text(' ', strip=False)
    return re.sub(r'[ \t\r\f\v]+', ' ', text).strip()


def _sentences(text):
    # Preserve decimals and abbreviations in year counts, and isolate list bullets.
    return [re.sub(r'^\s*[•*\-]\s*', '', part).strip() for part in
            re.split(r'\n+|(?<=[.!?;])\s+(?=[A-Z0-9•*])', text) if part.strip()]


def _role_lines(text):
    result, in_boilerplate, heading = [], False, ''
    for line in _sentences(text):
        if BOILER_HEADING.match(line):
            in_boilerplate = True
            continue
        if ROLE_HEADING.match(line):
            in_boilerplate = False
            heading = line
            continue
        if in_boilerplate or ORG_PROSE.search(line):
            continue
        # An inline company section must not turn a vendor name into role evidence.
        line = re.split(r'\b(?:About Us|About the Company|Equal Opportunity|Our Partners)\s*:', line, flags=re.I)[0].strip()
        if line:
            result.append((line, heading))
    return result


def _pega_evidence(lines):
    found = []
    for line, heading in lines:
        if not PEGA.search(line) or ALTERNATIVE_PEGA.search(line):
            continue
        # The JD page may repeat its title; a bare role name is still not duties.
        content_words = set(re.findall(r'[a-z]+', line.lower()))
        title_words = {'pega', 'prpc', 'pegarules', 'developer', 'developers', 'engineer', 'engineers', 'architect', 'architects', 'system', 'systems', 'senior', 'junior', 'lead', 'principal', 'staff', 'associate', 'technical', 'consultant', 'analyst', 'manager', 'job', 'title', 'role', 'sr', 'jr', 'ii', 'iii', 'iv'}
        if content_words and content_words <= title_words:
            continue
        if re.search(r'\b(?:no|without|not require[ds]?)\s+(?:prior\s+)?pega\b|\bpega\s+(?:experience\s+)?(?:not required|is optional)\b', line, re.I):
            continue
        if INCIDENTAL.search(line) and not re.search(r'\bpega\s+(?:develop|design|implement|rules?|applications?|case|platform)', line, re.I):
            continue
        if OPTIONAL.search(line) and not MANDATORY.search(line):
            continue
        if ACTION.search(line) or re.search(r'\b(?:required|mandatory|must|essential)\b', line, re.I) or re.search(r'(?:required|technical) skills|responsibilities|requirements', heading, re.I):
            found.append(line[:420])
    return list(dict.fromkeys(found))[:6]


def _number_words(text):
    text = re.sub(r'\b(twenty|thirty)[ -](one|two|three|four|five|six|seven|eight|nine)\b',
                  lambda m: str(YEAR_WORDS[m[1]] + YEAR_WORDS[m[2]]), text.lower())
    return re.sub(r'\b(' + '|'.join(YEAR_WORDS) + r')\b', lambda m: str(YEAR_WORDS[m[1]]), text)


def _years(value, unit):
    number = float(value)
    return round(number / 12, 3) if unit.lower().startswith(('mo', 'mon')) else number


def _pretty(number):
    return str(int(number)) if number is not None and number == int(number) else str(number)


def _experience(lines):
    requirements = []
    for original, heading in lines:
        text = _number_words(original)
        if EXPERIENCE_ORG.search(original):
            continue
        experience_context = re.search(r'\b(?:experience|exp|experienced|overall|total)\b', text) or re.search(r'experience', heading, re.I) or re.search(r'\b(?:years?|yrs?|months?)\s+(?:of\s+|in\s+)?(?:working|professional|software development|developing|pega development)', text)
        if not experience_context:
            continue
        if re.search(r'\b(?:degree|bachelor|master|university|college|study|education)\b', text) and not re.search(r'\b(?:work|professional|relevant|development|years? of)\s+experience', text):
            continue
        if OPTIONAL.search(original) and not MANDATORY.search(original):
            continue
        occupied = []
        for match in RANGE.finditer(text):
            lo = _years(match['lo'], match['u1'] or match['u2'])
            hi = _years(match['hi'], match['u2'])
            if lo > hi:
                continue
            requirements.append((lo, hi, original[:420], False))
            occupied.append(match.span())
        for match in SINGLE.finditer(text):
            if any(start <= match.start() < end for start, end in occupied):
                continue
            amount = _years(match['n'], match['u'])
            before = text[max(0, match.start() - 35):match.start()]
            if re.search(r'(?:less than|under|fewer than)\s*$', before):
                requirements.append((0.0, amount, original[:420], True))
            elif re.search(r'(?:up to|maximum(?: of)?|at most|no more than)\s*$', before):
                requirements.append((0.0, amount, original[:420], False))
            else:
                requirements.append((amount, None, original[:420], False))
    if not requirements:
        return None, None, '', [], False
    minimum = max(item[0] for item in requirements)
    upper = [item[1] for item in requirements if item[1] is not None]
    maximum = max(upper) if upper else None
    outside = any(lo >= 8 or (hi is not None and (hi > 8 or (hi == 8 and not exclusive)))
                  for lo, hi, _, exclusive in requirements)
    if maximum is not None:
        exclusive = any(hi == maximum and ex for _, hi, _, ex in requirements)
        label = (f'Less than {_pretty(maximum)} years' if exclusive and minimum == 0 else
                 f'{_pretty(minimum)}–{_pretty(maximum)} years')
    else:
        label = f'{_pretty(minimum)}+ years (upper limit not stated)'
    return minimum, maximum, label, list(dict.fromkeys(item[2] for item in requirements)), outside


def _expired(job, description):
    if job.get('expired') is True or job.get('is_expired') is True or job.get('is_active') is False:
        return True
    closure_statuses = {'expired', 'closed', 'removed', 'inactive', 'no_longer_available'}
    if any(str(job.get(key) or '').lower() in closure_statuses for key in ('status', 'research_status', 'job_detail_status')):
        return True
    if re.search(r'\b(?:this (?:job|position|vacancy) (?:is|has been) (?:closed|expired|filled|removed)|no longer accepting applications|job (?:has expired|is no longer available))\b', description, re.I):
        return True
    for key in ('validThrough', 'valid_through', 'expires_at', 'closing_at'):
        raw = job.get(key)
        if not raw:
            continue
        try:
            dt = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
            if re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(raw)):
                dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt < datetime.now(timezone.utc):
                return True
        except (ValueError, TypeError):
            pass
    return False


@lru_cache(maxsize=8)
def _read_resume(path, mtime, size):
    soup = BeautifulSoup(Path(path).read_text(encoding='utf-8'), 'html.parser')
    for tag in soup(['script', 'style', 'head', 'noscript', 'template']):
        tag.decompose()
    for tag in soup.select('[hidden], [aria-hidden="true"], .toolbar'):
        tag.decompose()
    pieces = []
    for tag in soup.find_all(['li', 'p', 'h1', 'h2', 'h3', 'h4', 'div', 'span']):
        if tag.name in {'div', 'span'} and (tag.find(['li', 'p', 'h1', 'h2', 'h3', 'h4', 'div', 'span']) or tag.find_parent(['li', 'p'])):
            continue
        text = tag.get_text(' ', strip=True)
        if not text:
            continue
        # An article title labels a project; only delivered-content sentences
        # substantiate implementation. Headings and isolated metric spans do not.
        is_project = tag.name == 'li' or (tag.name == 'p' and tag.find_parent(['li', 'article', 'aside']) is not None)
        credential = tag.find_parent(class_='credential') is not None or 'credential-title' in tag.get('class', [])
        pieces.append((text, 'certification' if credential else 'project' if is_project else 'listed'))
    if not pieces:
        pieces = [(line, 'listed') for line in _sentences(soup.get_text(' ', strip=True))]
    return pieces


def _resume_evidence(pattern, kind, pieces):
    found = []
    for text, strength in pieces:
        if not pattern.search(text):
            continue
        if re.search(r'\b(?:not certified|not experienced|no experience|learning|aspiring|planning|working towards|pursuing|studying)\b', text, re.I):
            continue
        # Certification tokens must come from explicit certification evidence.
        if kind == 'certification' and strength != 'certification' and not re.search(r'\b(?:certified|certifications?|credentials?|cssa|clsa|cpdc|pcssa|pcsa|pclsa)\b', text, re.I):
            continue
        found.append((text[:420], 'certification' if kind == 'certification' else strength))
    priorities = {'project': 3, 'certification': 3, 'listed': 1}
    delivered_action = re.compile(r'\b(?:designed|developed|built|implemented|configured|delivered|integrated|optimized|deployed|maintained|resolved|provided|created|automated)\b', re.I)
    return max(found, key=lambda item: (priorities.get(item[1], 0), bool(delivered_action.search(item[0])))) if found else ('', 'none')


def _requirements(lines):
    result = []
    for line, heading in lines:
        if not (ACTION.search(line) or MANDATORY.search(line) or ROLE_HEADING.match(heading)):
            continue
        if re.search(r'\b(?:not (?:required|mandatory|essential)|no (?:need|requirement))\b', line, re.I):
            continue
        importance = 'preferred' if OPTIONAL.search(line + ' ' + heading) and not MANDATORY.search(line) else 'required'
        mentions = [(name, pattern, kind, pattern.search(line)) for name, pattern, kind in COMPILED_SKILLS if pattern.search(line)]
        used = set()
        # Only the directly connected skill expressions form an either/or group.
        # 'CSSA or CLSA' is satisfied by either, not two separate mandatory gaps.
        ordered = sorted(mentions, key=lambda item: item[3].start())
        for i, (name, pattern, kind, hit) in enumerate(ordered):
            if name in used:
                continue
            options = [(name, pattern, kind)]
            last_end = hit.end()
            for other_name, other_pattern, other_kind, other_hit in ordered[i + 1:]:
                between = line[last_end:other_hit.start()]
                if re.fullmatch(r'\s*(?:certification\s*)?(?:or|and/or)\s*(?:a\s*)?', between, re.I) or (kind == other_kind == 'certification' and re.fullmatch(r'\s*/\s*', between)):
                    options.append((other_name, other_pattern, other_kind))
                    last_end = other_hit.end()
                    used.add(other_name)
                else:
                    break
            used.add(name)
            result.append({'requirement': ' or '.join(item[0] for item in options),
                           'importance': importance, 'options': options, 'jd_evidence': line[:420]})
    merged = {}
    for item in result:
        key = item['requirement']
        if key not in merged or (item['importance'] == 'required' and merged[key]['importance'] != 'required'):
            merged[key] = item
    return list(merged.values())


def _match(lines, resume_path, years_experience, experience, available):
    resume = Path(resume_path) if resume_path else DEFAULT_RESUME
    result = {'score': None, 'label': 'Not scored',
              'method': 'Evidence-weighted resume/JD comparison; not an ATS score or interview probability.',
              'matched': [], 'missing': [], 'notes': [], 'resume_source': resume.name}
    if not available:
        result['notes'].append('A complete, readable Pega job description is needed before a resume score is shown.')
        return result
    try:
        stat = resume.stat()
        pieces = _read_resume(str(resume.resolve()), stat.st_mtime_ns, stat.st_size)
    except (OSError, UnicodeError):
        result['notes'].append('The resume source could not be read; no score was guessed.')
        return result
    if not pieces:
        result['notes'].append('The resume contains no readable evidence; no score was guessed.')
        return result
    requirements = _requirements(lines)
    earned = possible = 0.0
    for requirement in requirements:
        hits = [_resume_evidence(pattern, kind, pieces) for _, pattern, kind in requirement.pop('options')]
        strengths = {'project': 1.0, 'certification': 1.0, 'listed': 0.7, 'none': 0.0}
        evidence, strength = max(hits, key=lambda hit: strengths[hit[1]])
        item = {**requirement, 'evidence': evidence, 'evidence_strength': strength}
        weight = 4 if item['importance'] == 'required' else 1
        possible += weight
        earned += weight * strengths[strength]
        result['matched' if evidence else 'missing'].append(item)
    minimum, maximum, _, experience_lines, _ = experience
    if minimum is not None:
        weight = 4
        possible += weight
        fits = years_experience >= minimum and (maximum is None or years_experience <= maximum)
        if fits:
            earned += weight
        elif years_experience < minimum:
            earned += weight * max(0, min(1, years_experience / minimum))
        item = {'requirement': 'Advertised experience', 'importance': 'required',
                'evidence': f'{_pretty(float(years_experience))} years stated by you; job asks {experience[2]}.',
                'evidence_strength': 'profile', 'jd_evidence': ' | '.join(experience_lines)[:600]}
        result['matched' if fits else 'missing'].append(item)
    if not possible:
        result['notes'].append('No comparable skills or experience requirements were found; no numeric score was invented.')
        return result
    result['score'] = round(100 * earned / possible)
    mandatory_cert_gap = any(item['importance'] == 'required' and 'certification' in item['requirement'] for item in result['missing'])
    if mandatory_cert_gap and result['score'] > 69:
        result['score'] = 69
        result['notes'].append('Score capped at 69 because a required certification is not evidenced in the resume.')
    result['label'] = 'Resume evidence match'
    result['notes'].append('Required evidence has weight 4; preferred evidence has weight 1. Project/certification evidence earns full credit; a listed skill earns 70%. Experience uses your stated years against the advertised range.')
    result['notes'].append('Missing means not evidenced in this resume, not proof you lack the skill. Only recognized requirements are scored; review the complete JD for additional requirements.')
    if any(item['evidence_strength'] == 'listed' for item in result['matched']):
        result['notes'].append('Some matches appear only in the resume skills list; hands-on depth has not been verified.')
    if any(item['importance'] == 'required' for item in result['missing']):
        result['notes'].append('Required gaps are listed explicitly; a high overall score does not override them.')
    if minimum is None:
        result['notes'].append('The job does not state numeric experience; experience fit remains unverified.')
    return result


def assess_job(job, resume_path=None, years_experience=4):
    """Return conservative recommendation metadata and a transparent evidence score.

    Complete JD evidence is opt-in: description_complete must be True and
    job_detail_status must be 'read'. The provided title is never used as proof.
    An advertised band including 8 years is excluded; 5–7 minimum is stretch.
    """
    job = job if isinstance(job, dict) else {}
    description = plain_text(job.get('description_text'))
    complete = job.get('description_complete') is True and job.get('job_detail_status') == 'read'
    lines = _role_lines(description)
    evidence = _pega_evidence(lines) if complete else []
    experience = _experience(lines) if complete else (None, None, '', [], False)
    minimum, maximum, label, _, outside = experience
    rec = {'eligible': False, 'status': 'review', 'reasons': [],
           'experience_label': label or 'Experience not verified',
           'minimum_years': minimum, 'maximum_years': maximum, 'pega_evidence': evidence}
    expired = _expired(job, description)
    if expired:
        rec.update(status='excluded', reasons=['This vacancy is closed, expired, or no longer accepting applications.'])
    elif job.get('search_presence') == 'not_rediscovered':
        rec['reasons'] = ['This saved role has not been rediscovered in the fresh search. Its current presence is unverified; it is not a current recommendation or a confirmed closed vacancy.']
    elif not complete or not description:
        rec['reasons'] = ['The full job description has not been read successfully; this is a lead to verify, not a recommendation.']
    elif not evidence:
        rec.update(status='excluded', reasons=['The job description does not establish Pega/PRPC as a required role responsibility or skill. A title, company mention, or optional platform alternative is insufficient.'])
    elif outside:
        rec.update(status='excluded', reasons=['The advertised experience requirement includes 8 or more years, outside your below-8-years search.'])
    elif minimum is None:
        rec['reasons'] = ['Pega is evidenced, but numeric experience is not stated; verify it before treating this as a match.']
    elif maximum is not None and float(years_experience) > maximum:
        rec.update(status='excluded', reasons=[f'The advertised upper experience limit is below your {_pretty(float(years_experience))} years.'])
    elif minimum > float(years_experience):
        rec.update(eligible=True, status='stretch', reasons=[f'Pega is evidenced, but the stated minimum is {_pretty(minimum)} years; you have {_pretty(float(years_experience))}.'])
    else:
        rec.update(eligible=True, status='recommended', reasons=['Pega is evidenced in the job description and your stated experience meets the advertised requirement below 8 years.'])
        if maximum is None:
            rec['reasons'].append('The employer gives a minimum only; the upper experience limit is not stated.')
    match = _match(lines, resume_path, float(years_experience), experience, bool(complete and description and evidence and not expired))
    required_certs = [item['requirement'] for item in match['missing'] if item['importance'] == 'required' and 'certification' in item['requirement']]
    if rec['eligible'] and required_certs:
        rec['status'] = 'stretch'
        rec['reasons'].append('Required certification not evidenced in your resume: ' + ', '.join(required_certs) + '.')
    return {'recommendation': rec, 'resume_match': match}
