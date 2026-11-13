"""Overlay dated public professional observations without losing the saved directory.

This module reads research artifacts; it does not fetch profiles or infer reporting lines.
"""
import copy
import hashlib
import ipaddress
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

FILENAME = 'people_refresh_20260909.json'
POSITIVE_ACCESS = {'page', 'search_index'}
FAILURES = {'blocked', 'unavailable', 'error', 'failed', 'no_matches', 'unresolved',
            'conflicting', 'not_a_person', 'access_denied', 'login_required'}
FIELDS = ('title', 'employer_as_stated', 'location_as_stated', 'pega_connection', 'work_summary')


def _key(value):
    return re.sub('[^a-z0-9]', '', unicodedata.normalize('NFKD', str(value or '')).lower())


def _seq(value):
    return value if isinstance(value, list) else [value] if value else []


def _unique(values):
    seen, result = set(), []
    for value in values:
        marker = json.dumps(value, sort_keys=True, ensure_ascii=True)
        if marker not in seen:
            seen.add(marker)
            result.append(value)
    return result


def _public_url(value):
    if not isinstance(value, str):
        return None
    try:
        parts = urlsplit(value)
        host = (parts.hostname or '').lower().rstrip('.')
        if (parts.scheme != 'https' or not host or parts.username or parts.password
                or host == 'localhost' or host.endswith(('.localhost', '.local'))
                or any(ord(ch) < 32 for ch in value)):
            return None
        try:
            if not ipaddress.ip_address(host).is_global:
                return None
        except ValueError:
            if '.' not in host:
                return None
        # Force validation of malformed port strings as well.
        if parts.port not in (None, 443):
            return None
        return value
    except (TypeError, ValueError):
        return None


def _profile_identity(url):
    if not _public_url(url):
        return ''
    parts = urlsplit(url)
    host = parts.hostname.lower()
    match = re.fullmatch(r'/in/([^/]+)/?', parts.path, re.I)
    if (host == 'linkedin.com' or host.endswith('.linkedin.com')) and match:
        return 'linkedin:' + unquote(match.group(1)).lower()
    return ''


def _date(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    except (ValueError, TypeError):
        return datetime.min.replace(tzinfo=timezone.utc)


def _indexes(doc):
    companies, aliases, profiles = {}, {}, {}
    for company in doc.get('companies', []):
        for cid in [company['id'], *company.get('source_company_ids', [])]:
            companies.setdefault(cid, []).append(company)
        for name in [company.get('name'), *company.get('aliases', [])]:
            if name:
                aliases.setdefault(_key(name), []).append(company)
    for person in doc.get('people', []):
        identities = {person.get('identity_key'), _profile_identity(person.get('profile_url'))}
        for observation in person.get('observations', []):
            identities.add(_profile_identity(observation.get('profile_url')))
        for identity in identities:
            if identity and identity.startswith('linkedin:'):
                profiles.setdefault(identity, []).append(person)
    return companies, aliases, profiles


def _one(rows):
    choices = {row['id']: row for row in rows}
    return next(iter(choices.values())) if len(choices) == 1 else None


def _company(raw, companies, aliases):
    if raw.get('company_id'):
        return _one(companies.get(raw['company_id'], []))
    return _one(aliases.get(_key(raw.get('company') or raw.get('employer_as_stated')), []))


def _person(raw, company, people, profiles):
    identity = _profile_identity(raw.get('profile_url'))
    explicit = next((p for p in people if p['id'] == raw.get('existing_person_id')), None)
    if explicit and _key(explicit.get('name')) == _key(raw.get('name')) and company['id'] in {explicit.get('company_id'), *explicit.get('company_ids', [])}:
        saved_identity = _profile_identity(explicit.get('profile_url'))
        if not saved_identity or not identity or saved_identity == identity:
            return explicit, identity or explicit.get('identity_key', ''), False
    if identity:
        matches = profiles.get(identity, [])
        if matches:
            return _one(matches), identity, len({p['id'] for p in matches}) > 1
        # A URL-bearing record must not merge into a different profile on name alone.
        candidates = [p for p in people if not _profile_identity(p.get('profile_url'))
                      and not str(p.get('identity_key', '')).startswith('linkedin:')
                      and _key(p.get('name')) == _key(raw.get('name'))
                      and company['id'] in {p.get('company_id'), *p.get('company_ids', [])}]
        return _one(candidates), identity, len(candidates) > 1
    candidates = [p for p in people if _key(p.get('name')) == _key(raw.get('name'))
                  and company['id'] in {p.get('company_id'), *p.get('company_ids', [])}]
    # When the incoming record has no profile URL, exact name plus employer is the
    # only fallback, and only a single saved person may match.
    return _one(candidates), 'named:' + company['id'] + ':' + _key(raw.get('name')), len(candidates) > 1


def _source(raw, checked_at):
    return {'url': raw['source_url'], 'title': raw.get('source_title') or raw['name'] + ' — public professional source',
            'access': raw['access'], 'checked_at': checked_at, 'source_date': raw.get('source_date'),
            'summary': raw.get('source_summary') or raw.get('work_summary') or raw.get('pega_connection') or ''}


def _sources(raw, checked_at):
    sources = []
    for item in raw.get('sources', []):
        if not isinstance(item, dict):
            continue
        url = _public_url(item.get('url') or item.get('source_url'))
        if not url:
            continue
        source = copy.deepcopy(item)
        source.update(url=url, checked_at=item.get('checked_at') or checked_at)
        how = source.get('access')
        if how == 'direct_page' and not (urlsplit(url).hostname or '').lower().endswith('linkedin.com'):
            source['access'] = 'page'
        source['summary'] = source.get('summary') or source.get('excerpt') or ''
        sources.append(source)
    if not any(s.get('url') == raw['source_url'] for s in sources):
        sources.insert(0, _source(raw, checked_at))
    return sources


def attach(doc, research_path):
    """Return a copied catalog with safe, dated observations from the refresh file.

    ``research_path`` may be the research directory or the exact JSON artifact.
    Failed fetches keep prior verified facts, and earlier company relationships
    remain in ``company_ids`` and observations when the latest employer changes.
    """
    result = copy.deepcopy(doc)
    path = Path(research_path)
    path = path if path.suffix.lower() == '.json' else path / FILENAME
    try:
        research = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return result
    if not isinstance(research, dict):
        return result
    rows = research.get('people', research.get('profile_observations'))
    if rows is None and isinstance(research.get('companies'), list):
        rows = [{**person, 'company_id': company.get('company_id') or company.get('id'), 'company': company.get('name')}
                for company in research['companies'] if isinstance(company, dict)
                for person in company.get('people', []) if isinstance(person, dict)]
    rows = rows if rows is not None else []
    if not isinstance(rows, list):
        return result
    people = result.setdefault('people', [])
    companies, aliases, profiles = _indexes(result)
    diagnostics, touched, company_ids, applied = [], set(), set(), set()
    file_checks = research.get('checks', research.get('queries', research.get('access_checks', [])))
    file_checks = file_checks if isinstance(file_checks, list) else []
    for index, incoming in enumerate(rows):
        if not isinstance(incoming, dict):
            diagnostics.append({'row': index, 'reason': 'Invalid person observation'})
            continue
        raw = copy.deepcopy(incoming)
        raw['profile_url'] = raw.get('profile_url') or raw.get('linkedin')
        raw['name'] = str(raw.get('name') or '').strip()
        company = _company(raw, companies, aliases)
        if not company:
            diagnostics.append({'row': index, 'reason': 'Unknown or ambiguous company', 'company_id': raw.get('company_id')})
            continue
        if not raw['name'] or _key(raw['name']) in {'unknown', 'notidentified'}:
            diagnostics.append({'row': index, 'reason': 'No identified person'})
            continue
        if raw.get('profile_url') and not _profile_identity(raw['profile_url']):
            diagnostics.append({'row': index, 'reason': 'Invalid LinkedIn profile URL'})
            continue
        person, identity, ambiguous = _person(raw, company, people, profiles)
        if ambiguous:
            diagnostics.append({'row': index, 'reason': 'Ambiguous saved person identity'})
            continue
        checked_at = raw.get('checked_at') or research.get('checked_at') or research.get('research_date')
        if _date(checked_at) == datetime.min.replace(tzinfo=timezone.utc):
            diagnostics.append({'row': index, 'reason': 'Missing or invalid check date'})
            continue
        source_url = _public_url(raw.get('source_url'))
        raw['source_url'] = source_url
        raw['access'] = str(raw.get('access') or '').lower()
        if raw['access'] == 'direct_page' and source_url and not ((urlsplit(source_url).hostname or '').lower().endswith('linkedin.com')):
            raw['access'] = 'page'
        failed = str(raw.get('status') or raw.get('outcome') or '').lower() in FAILURES
        positive = bool(source_url and raw['access'] in POSITIVE_ACCESS and not failed)
        if not positive:
            if person:
                check = {k: raw.get(k) for k in ('status', 'outcome', 'access', 'source_url', 'profile_url', 'limitations') if raw.get(k) is not None}
                check.update(checked_at=checked_at, research_file=path.name)
                person['research_checks'] = _unique(person.get('research_checks', []) + [check])
            diagnostics.append({'row': index, 'reason': 'No positive public-source observation; previous facts retained'})
            continue
        if person is None:
            person = {'id': hashlib.sha256(identity.encode()).hexdigest()[:18], 'identity_key': identity,
                      'name': raw['name'], 'company': company['name'], 'company_id': company['id'],
                      'company_ids': [company['id']], 'observations': [], 'certifications': [],
                      'research_origin': path.name}
            if any(p['id'] == person['id'] for p in people):
                diagnostics.append({'row': index, 'reason': 'Stable person ID collision'})
                continue
            people.append(person)
        person['company_ids'] = _unique([*person.get('company_ids', []), *([person['company_id']] if person.get('company_id') else []), company['id']])
        if not person.get('profile_url') and raw.get('profile_url'):
            person['profile_url'] = raw['profile_url']
        if identity.startswith('linkedin:'):
            profiles.setdefault(identity, []).append(person)
        touched.add(person['id'])
        company_ids.add(company['id'])
        observation = {**raw, 'company_id': company['id'], 'company': company['name'],
                       'checked_at': checked_at, 'research_file': path.name, 'crosschecked': True}
        person['observations'] = _unique(person.get('observations', []) + [observation])
        current = person.get('deep_audit') or {}
        review = {field: raw.get(field) for field in FIELDS}
        review.update(status='partially_supported', person_id=person['id'], identity_key=person['identity_key'],
                      company_id=company['id'], name=raw['name'], profile_url=raw.get('profile_url'),
                      certifications=copy.deepcopy(raw.get('certifications') or []), checked_at=checked_at,
                      research_file=path.name, summary=raw.get('summary') or raw.get('work_summary') or raw.get('pega_connection') or 'Dated public professional observation; current project allocation is not established.',
                      limitations=_unique(_seq(raw.get('limitations')) + ['Public professional evidence does not establish a reporting line, complete team roster or vacancy.']),
                      sources=_sources(raw, checked_at), current_employment_verified=raw.get('current_employment_verified', False),
                      profile_access=raw.get('profile_access') or raw['access'], role_basis=raw.get('role_basis'),
                      role_group=raw.get('role_group'))
        referenced = set(_seq(raw.get('query_ids')))
        if referenced:
            review['checks'] = [copy.deepcopy(check) for check in file_checks if isinstance(check, dict) and check.get('id') in referenced]
        if _date(checked_at) >= _date(current.get('checked_at')):
            if current and current != review:
                person['research_history'] = _unique(person.get('research_history', []) + [copy.deepcopy(current)])
            person['deep_audit'] = review
            person['latest_company_id'] = company['id']
            applied.add(person['id'])
        elif current != review:
            person['research_history'] = _unique(person.get('research_history', []) + [review])
    created = {p['id'] for p in people if p.get('research_origin') == path.name and p['id'] in touched}
    result['people_refresh'] = {'research_date': research.get('research_date') or research.get('checked_at'),
                              'research_file': path.name, 'people_refreshed': len(touched - created),
                              'people_added': len(created), 'people_reviewed': len(touched),
                              'latest_reviews_applied': len(applied), 'companies_checked': len(company_ids),
                              'diagnostics': diagnostics, 'checks': copy.deepcopy(file_checks)}
    result.setdefault('stats', {})['people_records'] = len(people)
    result['stats']['people_refresh_reviewed'] = len(touched)
    result['stats']['people_refresh_added'] = len(created)
    if 'unique_linkedin_profiles' in result['stats']:
        result['stats']['unique_linkedin_profiles'] = sum(bool(_profile_identity(p.get('profile_url'))) for p in people)
    if 'people_observations' in result['stats']:
        result['stats']['people_observations'] = sum(len(p.get('observations', [])) for p in people)
    return result
