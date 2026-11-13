"""Normalize saved research and campaign candidates without inventing pay or eligibility."""
import copy
import math
import re
import unicodedata
from quality import canonical_url, job_identity


def company_key(name):
    return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',str(name or '')).lower())

def employer_type_index(records):
    observed={}
    for record in records:
        if record.get('category') not in ('gcc','services'):
            continue
        kind=record['category']
        for name in [record.get('name'),(record.get('team_snapshot') or {}).get('name'),*record.get('keywords',[])]:
            key=company_key(name)
            if key:observed.setdefault(key,set()).add(kind)
    return {key:next(iter(kinds)) for key,kinds in observed.items() if len(kinds)==1}

def salary_bucket(salary, minimum_lpa=20):
    if not isinstance(salary, dict):
        return 'undisclosed'
    if not salary.get('currency'):
        return 'basis_unknown'
    if salary.get('currency') != 'INR':
        return 'foreign_currency'
    if salary.get('period') not in ('annual', 'year', 'yearly'):
        return 'basis_unknown'
    # An ambiguous headline range must not become a confirmed CTC claim.
    if salary.get('basis') not in ('total_compensation', 'ctc', 'total_ctc'):
        return 'basis_unknown'
    low = salary.get('amount_min', salary.get('min'))
    high = salary.get('amount_max', salary.get('max', low))
    try:
        low, high = float(low), float(high)
    except (ValueError, TypeError):
        return 'undisclosed'
    if not math.isfinite(low) or not math.isfinite(high) or not 0 <= low <= high:
        return 'basis_unknown'
    minimum = minimum_lpa * 100000
    return 'meets_target' if low >= minimum else 'overlaps_target' if high >= minimum else 'below_target'


def normalize_opportunity(original, origin='research', target=None):
    row = copy.deepcopy(original)
    row['url'] = canonical_url(row.get('url', ''))
    if not row['url']:
        return None
    row.setdefault('id', job_identity(row.get('title', ''), row.get('company', ''), row['url']))
    row.setdefault('company', (target or {}).get('name', 'Employer unconfirmed'))
    row.setdefault('title', 'Role title unconfirmed')
    row.setdefault('location', (target or {}).get('location', 'Location unconfirmed'))
    row.setdefault('status', 'candidate' if origin == 'campaign' else 'uncertain')
    row.setdefault('checked_at', (target or {}).get('checked_at'))
    row.setdefault('skills', [])
    row.setdefault('fit', 'possible')
    row.setdefault('fit_reasons', ['Potential overlap with your experience; review the full requirements.'])
    row.setdefault('gaps', row.get('requirements_unknown') or ['Experience, work authorization, compensation and exact team scope need confirmation.'])
    row.setdefault('summary', 'Saved search result. The employer posting must establish the exact requirements and availability.')
    row.setdefault('salary', None)
    row.setdefault('work_mode', 'unknown')
    row.setdefault('track', 'pega' if re.search(r'\b(pega|prpc)\b', row['title'], re.I) else 'adjacent')
    row.setdefault('remote_eligibility', 'unknown')
    row.setdefault('employer_type', 'product' if row['company'] == 'Pegasystems' else 'services' if (target or {}).get('category') == 'services' else 'gcc' if (target or {}).get('category') == 'gcc' else 'unknown')
    row['origin'] = origin
    if target:
        row['target_id'] = target['target_id']
        row['target_category'] = target.get('category')
    if not row.get('evidence'):
        row['evidence'] = [{'url': row['url'], 'title': row['company'] + ' — ' + row['title'],
                            'source_type': row.get('source', 'public job search'), 'checked_at': row.get('checked_at'),
                            'excerpt': row.get('summary', ''), 'status': 'candidate' if origin == 'campaign' else row['status']}]
    row['pay_bucket'] = salary_bucket(row['salary'])
    return row
