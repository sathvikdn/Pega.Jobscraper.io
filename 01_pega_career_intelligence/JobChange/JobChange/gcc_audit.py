"""Attach field-level research reviews without deleting historical source records."""
import copy
import json
from collections import Counter
from pathlib import Path


def read(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return {}


def attach(doc, research):
    root = Path(research)
    manifest = read(root / 'gcc_deep_audit_manifest.json')
    companies = {key: c for c in doc['companies']
                 for key in [c['id'], *c.get('source_company_ids', [])]}
    people = {p['id']: p for p in doc['people']}
    identities = {p['identity_key']: p for p in doc['people']}
    company_ids, person_ids, diagnostics, operations = set(), set(), [], 0
    for path in sorted(root.glob('gcc_deep_audit_[1234].json')):
        data = read(path)
        queries = {q['id']: q for q in data.get('queries', []) if q.get('id')}
        operations += len(queries)
        for field, lookup in (('company_reviews', companies), ('profile_reviews', people)):
            for raw in data.get(field, []):
                key = raw.get('company_id') if field == 'company_reviews' else raw.get('person_id')
                target = lookup.get(key)
                if target is None and field == 'profile_reviews':
                    target = identities.get(raw.get('identity_key'))
                if target is None:
                    diagnostics.append({'file': path.name, 'id': key, 'error': 'Unknown record'})
                    continue
                review = copy.deepcopy(raw)
                review['checked_at'] = review.get('checked_at') or data.get('research_date')
                review['research_file'] = path.name
                review['checks'] = [queries[q] for q in review.get('query_ids', []) if q in queries]
                # An inventory row alone must never become a completed source review.
                if not review['checks'] and not review.get('sources') and review.get('status') != 'not_a_person':
                    diagnostics.append({'file': path.name, 'id': key, 'error': 'No examination recorded'})
                    continue
                allowed = {'reviewed', 'no_public_evidence', 'ambiguous'} if field == 'company_reviews' else {'corroborated', 'partially_supported', 'unresolved', 'conflicting', 'not_a_person'}
                if review.get('status') not in allowed:
                    diagnostics.append({'file': path.name, 'id': key, 'error': 'Invalid review verdict'})
                    continue
                target['deep_audit'] = review
                if field == 'company_reviews':
                    target.setdefault('earlier_flags', copy.deepcopy(target.get('flags', {})))
                    for reviewed_key, flag in [('pega_usage_supported', 'pega'), ('bangalore_connection_supported', 'bangalore')]:
                        if isinstance(review.get(reviewed_key), bool):
                            target.setdefault('flags', {})[flag] = review[reviewed_key]
                (company_ids if field == 'company_reviews' else person_ids).add(target['id'])
    if not manifest and not company_ids and not person_ids:
        return doc
    expected_companies = set(manifest.get('company_ids', []))
    expected_people = set(manifest.get('people_ids', []))
    resolved_expected = {companies[i]['id'] for i in expected_companies if i in companies}
    doc['gcc_audit'] = {
        'research_date': manifest.get('research_date'),
        'company_records_in_scope': len(expected_companies),
        'profile_records_in_scope': len(expected_people),
        'company_records_reviewed': len(company_ids),
        'profile_records_reviewed': len(person_ids),
        'companies_pending': sorted(resolved_expected - company_ids),
        'profiles_pending': sorted(expected_people - person_ids),
        'profile_verdicts': dict(Counter(people[i]['deep_audit'].get('status', 'unknown') for i in person_ids)),
        'company_verdicts': dict(Counter(companies[i]['deep_audit'].get('status', 'unknown') for i in company_ids)),
        'logged_checks': operations,
        'diagnostics': diagnostics,
        'definition': 'Reviewed means the recorded source or identity check was completed; it does not mean all earlier claims were verified. Profile records are not employee headcount.',
    }
    doc['gcc_audit']['companies_with_supported_pega_connection'] = sum(c.get('deep_audit', {}).get('pega_usage_supported') is True for c in doc['companies'])
    doc['gcc_audit']['companies_with_supported_bangalore_connection'] = sum(c.get('deep_audit', {}).get('bangalore_connection_supported') is True for c in doc['companies'])
    doc['stats'].update(gcc_company_reviews=len(company_ids), gcc_profile_reviews=len(person_ids),
                        bangalore_companies=sum(c.get('flags', {}).get('bangalore') is True for c in doc['companies']))
    return doc
