from __future__ import annotations

import copy
import hashlib
import html
import json
import math
import re
import unicodedata
from urllib.parse import parse_qs, urlsplit, urljoin

from bs4 import BeautifulSoup
from quality import canonical_url

CITY_ALIASES = {'bangalore': 'Bengaluru', 'bengaluru': 'Bengaluru', 'gurgaon': 'Gurugram',
                'gurugram': 'Gurugram', 'pune': 'Pune', 'hyderabad': 'Hyderabad',
                'chennai': 'Chennai', 'mumbai': 'Mumbai', 'noida': 'Noida', 'delhi': 'Delhi'}
COMPANY_NAMES = {'truviq systems': 'Truviq Systems'}


def text(value):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', html.unescape(str(value or '')))).strip()


def key(value):
    return re.sub(r'[^\w]+', ' ', text(value).casefold()).strip()


def clean_company(value, title=''):
    name = text(value)
    name = re.split(r'\s*[—–]|\s+-\s+|\ufffd+', name, maxsplit=1)[0].strip()
    name = re.sub(r'\s+(?:\d(?:\.\d)?\s*(?:out of 5|stars?|ratings?|reviews?).*)$', '', name, flags=re.I).strip()
    if not name or key(name) == key(title) or key(name) in {'unknown', 'employer unconfirmed', 'easily apply', 'sort by', 'company'}:
        return ''
    if re.fullmatch(r'(?:senior\s+)?(?:pega\s+)?(?:developer|software engineer|architect)', name, re.I):
        return ''
    return COMPANY_NAMES.get(name.casefold(), name)


def number(value):
    if isinstance(value,bool):return None
    try:
        result = float(value)
        return result if math.isfinite(result) and result >= 0 else None
    except (TypeError, ValueError):
        return None


def pega_evidence(description):
    for sentence in re.split(r'[.;\n]', text(description)):
        if re.search(r'\b(?:pega|prpc)\b', sentence, re.I) and re.search(
                r'\b(?:develop\w*|implement\w*|hands.on|rulesets?|case design|cssa|clsa)\b', sentence, re.I):
            if not re.search(r'\b(?:preferred|optional|nice to have|partner|about us)\b', sentence, re.I):
                return 'confirmed'
    return 'unverified'


def jsonld_jobs(document):
    def walk(value):
        if isinstance(value, list):
            for item in value:
                yield from walk(item)
        elif isinstance(value, dict):
            types = value.get('@type', [])
            if 'JobPosting' in ([types] if isinstance(types, str) else types):
                yield value
            for field in ('@graph', 'itemListElement', 'item'):
                if field in value:
                    yield from walk(value[field])
    soup = BeautifulSoup(document, 'html.parser')
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            yield from walk(json.loads(script.get_text()))
        except (ValueError, TypeError):
            continue


def from_jobposting(posting, page_url):
    organization = posting.get('hiringOrganization') or {}
    identifier = posting.get('identifier') or {}
    locations = posting.get('jobLocation') or []
    if not isinstance(locations, list):locations = [locations]
    labels = []
    for location in locations:
        address = location.get('address', {}) if isinstance(location, dict) else {}
        if isinstance(address, dict):
            labels.append(', '.join(text(address.get(field)) for field in ('addressLocality','addressRegion','addressCountry') if address.get(field)))
    description = BeautifulSoup(str(posting.get('description') or ''), 'html.parser').get_text(' ', strip=True)
    published_salary=posting.get('baseSalary') or {}
    salary=None
    if isinstance(published_salary,dict):
        value=published_salary.get('value') or {}
        if isinstance(value,dict):
            salary={'amount_min':number(value.get('minValue',value.get('value'))),'amount_max':number(value.get('maxValue',value.get('value'))),
                    'currency':published_salary.get('currency'),'period':{'YEAR':'annual','MONTH':'monthly','HOUR':'hourly'}.get(str(value.get('unitText','')).upper(),'unknown'),
                    'basis':'base_salary','source_url':page_url}
    return {'title': posting.get('title'), 'company': organization.get('name') if isinstance(organization, dict) else organization,
            'company_domain': urlsplit(organization.get('sameAs', '')).hostname if isinstance(organization, dict) else None,
            'requisition_id': identifier.get('value') if isinstance(identifier, dict) else identifier,
            'url': urljoin(page_url,posting.get('url') or page_url), 'location': '; '.join(labels),
            'salary':salary,'description_text': description, 'description_complete': bool(description),
            'description_source_url': page_url, 'job_detail_status': 'read', 'posted_at': posting.get('datePosted')}


def normalize_job(raw):
    if not isinstance(raw, dict):raise ValueError('Job observation must be an object')
    row = copy.deepcopy(raw)
    url = canonical_url(raw.get('url', ''))
    title = text(raw.get('title'))
    if not url or not title:raise ValueError('Job title and safe detail URL are required')
    company = clean_company(raw.get('company'), title)
    location = text(raw.get('location'))
    cities = {label for alias, label in CITY_ALIASES.items() if re.search(r'\b'+alias+r'\b', location, re.I)}
    city = next(iter(cities)) if len(cities)==1 else ''
    salary = raw.get('salary') if isinstance(raw.get('salary'), dict) else {}
    domain = text(raw.get('company_domain')).lower().removeprefix('www.')
    if domain and (not re.fullmatch(r'[a-z0-9.-]+\.[a-z]{2,}', domain) or any(domain==host or domain.endswith('.'+host) for host in ('linkedin.com','wikipedia.org','indeed.com','glassdoor.com'))):domain = ''
    requisition = text(raw.get('requisition_id'))
    description = text(raw.get('description_text'))
    level = next((label for pattern, label in [(r'\bCLSA\b','CLSA'),(r'\bCSSA\b','CSSA'),(r'\blead\b','Lead'),(r'\barchitect\b','Architect'),(r'\bsenior\b','Senior Developer')]
                  if re.search(pattern, title+' '+description, re.I)), 'Unconfirmed')
    query = parse_qs(urlsplit(url).query)
    posting_id = text(raw.get('source_posting_id')) or query.get('jk', [''])[0]
    row.update(url=url, title=title, company=company or 'Employer unconfirmed', company_key=key(company),
               company_domain=domain, requisition_id=requisition, source_posting_id=posting_id,
               location=location or 'Location unconfirmed', city=city, state=text(raw.get('state')),
               country='India' if city or re.search(r'\bindia\b', location, re.I) else text(raw.get('country')),
               level=level, min_yoe=number(raw.get('experience_min')), max_yoe=number(raw.get('experience_max')),
               salary_min=number(salary.get('amount_min')), salary_max=number(salary.get('amount_max')),
               salary_currency=text(salary.get('currency')), work_mode=raw.get('work_mode') or 'unknown',
               pega_verification=pega_evidence(description) if raw.get('description_complete') else 'unverified',
               normalization_issues=[] if company else ['Employer identity requires verification'])
    if row.get('description_complete') and row.get('job_detail_status')=='read':
        from job_matching import assess_job
        assessment=assess_job(row)
        row.update(assessment)
        recommendation=assessment['recommendation']
        row['min_yoe']=recommendation['minimum_years']
        row['max_yoe']=recommendation['maximum_years']
        row['pega_verification']='confirmed' if recommendation.get('pega_evidence') else 'unverified'
    return row


def probable_key(row):
    if not row['company_key'] or not row['city'] or row['min_yoe'] is None or row['max_yoe'] is None:return None
    values = [row['company_key'],key(row['title']),row['city'],row['state'],row['min_yoe'],row['max_yoe']]
    return hashlib.sha256(json.dumps(values, ensure_ascii=False).encode()).hexdigest()
