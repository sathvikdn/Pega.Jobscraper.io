"""Evidence and identity rules shared by research, scanner and portal."""
import hashlib
import re
import unicodedata
from datetime import date
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING = {'trk', 'trackingid', 'refid', 'source', 'src', 'originalsubdomain',
            'position', 'pagenum', 'alternatechannel', 'from', 'jvid',
            'es_p', 'lastselectedfacet', 'selectedcategoriesfacet'}

def canonical_url(url):
    """Keep identity-bearing parameters, discard only known tracking parameters."""
    if not isinstance(url, str):
        return ''
    p = urlsplit(url.strip())
    if p.scheme not in ('https', 'http') or not p.hostname or p.username or p.password:
        return ''
    host = p.hostname.lower()
    if host == 'linkedin.com' or host.endswith('.linkedin.com'):
        query_id = next((v for k,v in parse_qsl(p.query) if k.lower() == 'currentjobid' and v.isdigit()), None)
        if query_id:
            return 'https://www.linkedin.com/jobs/view/' + query_id
        found = re.search(r'/jobs/view/(?:[^/?]*-)?(\d+)(?:/|$)', p.path)
        if found:
            return 'https://www.linkedin.com/jobs/view/' + found.group(1)
    query = [(k,v) for k,v in parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in TRACKING]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip('/') or '/',
                       urlencode(sorted(query)), ''))

def normalized_name(value):
    value = unicodedata.normalize('NFKD', value or '').encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', value).strip()

def broad_target(company):
    return '(broad)' in company['name'].lower() or '(worldwide)' in company['name'].lower()

def employer_matches(listed, company):
    listed = normalized_name(listed)
    if not listed:
        return False
    if broad_target(company):
        return True
    terms = [company['name']] + company.get('keywords', [])
    for value in terms:
        term = normalized_name(value)
        if not term:
            continue
        # 'pega' is a product keyword and cannot identify any employer containing it.
        if term == 'pega':
            if listed in ('pega', 'pegasystems', 'pegasystems inc', 'pegasystems india'):
                return True
            continue
        # Short bank aliases cannot match an unrelated brand by prefix alone.
        if term=='citi' and listed not in ('citi','citi india','citi bank','citi group','citi global','citi services','citi technology'):
            continue
        if re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', listed):
            return True
    return False

def job_identity(title, company, url):
    url = canonical_url(url)
    raw = url or f'{normalized_name(company)}|{normalized_name(title)}'
    return hashlib.sha256(raw.encode()).hexdigest()[:20]

def iso_date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None

def effective_status(record, verification=None, today=None):
    today = today or date.today()
    deadline = iso_date(record.get('closing_at'))
    if deadline and deadline < today:
        return 'closed'
    if verification:
        result = verification.get('status')
        if result in ('open', 'closed'):
            return result
        return 'uncertain'
    return record.get('status', 'uncertain')

def is_bangalore(value):
    text = ' '.join(value) if isinstance(value, list) else str(value or '')
    return bool(re.search(r'\b(bengaluru|bangalore)\b', text, re.I))

def evidence_freshness(checked_at, today=None):
    observed = iso_date(checked_at)
    if observed is None:
        return {'age_days': None, 'label': 'Date unknown'}
    age = max(0, ((today or date.today()) - observed).days)
    return {'age_days': age, 'label': 'Recent' if age <= 14 else 'Recheck recommended'}

def compare_offer(fixed, performance, city, retirals, one_time=0, payout=100):
    values = [float(v) for v in (fixed, performance, city, retirals, one_time, payout)]
    if any(v < 0 for v in values) or values[-1] > 100:
        raise ValueError('Amounts must be nonnegative and payout between 0 and 100.')
    fixed, performance, city, retirals, one_time, payout = values
    return {'recurring_package': fixed + performance + city + retirals,
            'scenario_annual_pay': fixed + performance * payout / 100 + city,
            'first_year_package': fixed + performance + city + retirals + one_time,
            'fixed_and_city': fixed + city}
