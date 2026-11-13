"""Build the complete target directory from local snapshots, without importing the scanner.

Only Python literal assignments and the dossier's JSON DATA payload are read.
Importing this module performs no file access, logging setup or network activity.
"""
import argparse
import ast
import copy
import hashlib
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus, urlsplit

BASE = Path(__file__).resolve().parent
POOLS = {'COMPANIES': 'gcc', 'CONSULTING_COMPANIES': 'services', 'REMOTE_GLOBAL_COMPANIES': 'global'}

# Exact aliases only. Groups retain potentially confusing employers separately:
# Citi / First Citizens, FIS / Global Payments / FNF / Fidelity Investments,
# Mercedes-Benz / Daimler Truck and MUFG / MUFG Pension & Market Services.
ALIASES = {
    'JPMorgan Chase': ['jpmorgan', 'jpmorganchase', 'jpmc', 'jp morgan', 'JPMorgan Chase & Co.'],
    'Citibank': ['citi', 'citi india'],
    'Lloyds Banking Group': ['lloyds banking', 'lloyds bank'],
    'ANZ Bank': ['anz', 'anz india'],
    'BNY Mellon': ['bny india', 'bny'],
    'Allianz Technology': ['allianz'],
    'Aflac': ['aflac india'],
    'Sun Life': ['sun life india'],
    'Ameriprise Financial': ['ameriprise', 'ameriprise india'],
    'Empower': ['empower india', 'empower retirement'],
    'Charles Schwab': ['charles schwab india', 'schwab india'],
    'Mastercard': ['mastercard india'],
    'Visa': ['visa india', 'visa inc'],
    'PayPal': ['paypal india'],
    'FIS (TSYS/Global Payments)': ['fis', 'fis india', 'fidelity national information'],
    'Broadridge': ['broadridge india'],
    'Optum / UnitedHealth Group': ['optum', 'unitedhealth', 'uhg india', 'optum uhg india', 'unitedhealth group'],
    'Elevance Health (Anthem)': ['elevance health', 'anthem'],
    'Evernorth / Cigna': ['evernorth', 'cigna', 'cigna india'],
    'Verizon': ['verizon india'],
    'Vodafone / VOIS': ['vodafone', 'vois'],
    'BT Group': ['bt india'],
    'Telstra': ['telstra india'],
    'Amdocs': ['amdocs india'],
    'Ford Motor Company': ['ford motor', 'ford business solutions', 'ford india'],
    'Stellantis': ['stellantis india'],
    'Siemens': ['siemens india', 'siemens technology'],
    'S&P Global': ['s&p global india', 'spglobal'],
    'Conduent': ['conduent india'],
    'DHL': ['dhl india'],
    'Dell Technologies': ['dell', 'dell technologies india'],
    'Synchrony Financial': ['synchrony'],
    'Bosch': ['bosch india', 'bosch global'],
    'The Hartford India': ['the hartford', 'hartford'],
    'Commonwealth Bank': ['cba', 'commbank', 'Commonwealth Bank / CommBank India'],
    'NAB (National Australia Bank)': ['nab', 'national australia bank'],
    'UBS India': ['ubs'],
    'MetLife India GCC': ['metlife', 'metlife india'],
    'AXA India': ['axa', 'axa insurance'],
    'Roche India': ['roche', 'roche diagnostics'],
    'GE HealthCare India': ['ge healthcare'],
    'Pfizer India': ['pfizer'],
    'Novartis India': ['novartis'],
    'John Deere India (JDTCI)': ['john deere', 'john deere india', 'jdtci'],
    'First Citizens India': ['first citizens bank', 'first citizens'],
    'Booking Holdings India': ['booking holdings', 'booking.com', 'Booking Holdings / Booking.com'],
    'Cisco India': ['cisco'],
    'Nokia India': ['nokia'],
    'Orange Business India': ['orange business'],
    'Maersk GSC India': ['maersk', 'maersk india'],
    'Shell India': ['shell'],
    'Nike India': ['nike'],
    'Unilever India (Digital Hub)': ['unilever india', 'hindustan unilever'],
    'Mercedes-Benz R&D India (MBRDI)': ['mercedes-benz', 'mercedes benz', 'mercedes-benz r&d india', 'mbrdi', 'Mercedes-Benz Research and Development India (MBRDI)'],
    'Daimler Truck India': ['daimler truck'],
    'Renault-Nissan Tech India': ['renault-nissan', 'renault nissan'],
    'Cummins India': ['cummins'],
    'IFFCO Tokio General Insurance': ['iffco tokio'],
    'Global Payments India': ['global payments'],
    'Pegasystems India': ['pegasystems', 'Pegasystems (Pega)'],
    'Fidelity National Financial India (FNF)': ['fidelity national financial', 'fnf'],
    'Proximus India': ['proximus'],
    'Mondelez India': ['mondelez'],
    'enGen / Highmark India': ['engen', 'highmark', 'highmark health', 'thryve digital'],
    'Marsh McLennan India (MMGS)': ['marsh mclennan', 'mmgs'],
    'PepsiCo India': ['pepsico'],
    'Capital One India': ['capital one'],
    'Mizuho Global Services India (MGS)': ['mizuho global services', 'mgs'],
    'Carelon Global Solutions India': ['carelon global solutions'],
    'MUFG Pension & Market Services (Link Group)': ['mufg pension market services', 'link group'],
    'Intel India': ['intel'],
    'Levi Strauss & Co. India': ['levi strauss', 'levi strauss co'],
    'ITC Limited': ['itc limited'],
    'CSC (Corporation Service Company)': ['corporation service company', 'csc'],
    'NTT DATA Services': ['ntt data'],
}


def normalized(value):
    text = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()


def target_id(category, name):
    return category + '-' + normalized(name).replace(' ', '-')


def read_scanner_constants(path):
    """Reject executable values instead of executing any scanner statement."""
    wanted = set(POOLS) | {'CAREER_PORTAL_DOMAINS'}
    result = {}
    for node in ast.parse(Path(path).read_text(encoding='utf-8-sig')).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in wanted:
                result[name] = ast.literal_eval(node.value)
    missing = set(POOLS) - result.keys()
    if missing:
        raise ValueError('Missing scanner target pools: ' + ', '.join(sorted(missing)))
    return result


def source_info(path, source_id, classification, as_of=None):
    path = Path(path)
    return {'id': source_id, 'path': str(path.resolve()), 'as_of': as_of,
            'classification': classification,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def career_url(company, domains):
    value = company.get('career_url')
    if not value:
        value = next((domains[k.lower().strip()] for k in company.get('keywords', []) if k.lower().strip() in domains), None)
    if not value:
        return None
    value = value if '://' in value else 'https://' + value
    parsed = urlsplit(value)
    return value if parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username else None


def search_links(company, location, career=None):
    keyword = company.get('keywords', [company['name']])[0]
    query = quote_plus('pega ' + keyword)
    result = {
        'LinkedIn': f'https://www.linkedin.com/jobs/search/?keywords={query}&location={quote_plus(location)}',
        'Google': 'https://www.google.com/search?q=' + quote_plus(f'{keyword} pega jobs {location}'),
        'People': 'https://www.linkedin.com/search/results/people/?keywords=' + quote_plus(f'{keyword} Pega {location}'),
        'Indeed': f'https://www.indeed.com/jobs?q={query}&l={quote_plus(location)}',
    }
    if location.lower() == 'india':
        result['Naukri'] = 'https://www.naukri.com/pega-' + quote_plus(keyword.replace(' ', '-')) + '-jobs-in-india'
    if career:
        result['Career Portal'] = career
    return result


def load_catalog(base_dir=BASE):
    constants = read_scanner_constants(Path(base_dir) / 'pega_job_hunter.py')
    records = []
    for pool, category in POOLS.items():
        for original in constants[pool]:
            company = copy.deepcopy(original)
            location = company.get('location') or 'India'
            career = career_url(company, constants.get('CAREER_PORTAL_DOMAINS', {}))
            records.append({
                'target_id': target_id(category, company['name']), 'name': company['name'],
                'category': category, 'location': location, 'keywords': company.get('keywords', []),
                'search_links': search_links(company, location, career), 'career_url': career,
                'team_snapshot': None, 'recent_team': None, 'check_status': 'pending',
                'target_source': 'scanner_catalog', 'original_target': company,
                'priority': company.get('priority'), 'tier': company.get('tier'),
                'mapping': {'snapshot': None, 'recent_team': None},
            })
    if len({r['target_id'] for r in records}) != len(records):
        raise ValueError('Duplicate category/name target IDs in scanner catalog')
    return records


def extract_dossiers(path):
    html = Path(path).read_text(encoding='utf-8-sig')
    marker = re.search(r'\bconst\s+DATA\s*=\s*', html)
    if not marker:
        raise ValueError('Dossier JSON DATA payload was not found')
    result, _ = json.JSONDecoder().raw_decode(html[marker.end():])
    if not isinstance(result, list):
        raise ValueError('Dossier DATA must be a JSON array')
    return result


def merge_values(earlier, preferred):
    """Preserve supplemental fields/list entries; preferred conflicting scalars win.

    Unmodified source records are retained separately, including scalar conflicts.
    """
    if isinstance(earlier, dict) and isinstance(preferred, dict):
        result = copy.deepcopy(earlier)
        for key, value in preferred.items():
            result[key] = merge_values(result[key], value) if key in result else copy.deepcopy(value)
        return result
    if isinstance(earlier, list) and isinstance(preferred, list):
        result = copy.deepcopy(preferred)
        for value in earlier:
            if value not in result:
                result.append(copy.deepcopy(value))
        return result
    return copy.deepcopy(preferred if preferred is not None else earlier)


def merge_members(earlier, preferred):
    result = copy.deepcopy(preferred)
    for person in earlier:
        key = normalized(person.get('name'))
        matches = [i for i, member in enumerate(result) if key and normalized(member.get('name')) == key]
        if len(matches) == 1:
            index = matches[0]
            result[index] = merge_values(person, result[index])
        elif person not in result:
            result.append(copy.deepcopy(person))
    return result


def build_snapshots(enriched, dossier, sources):
    original = {normalized(c['name']): c for c in enriched.get('companies', [])}
    preferred = {normalized(c['name']): c for c in dossier}
    snapshots = []
    for key in dict.fromkeys(list(preferred) + list(original)):
        earlier, later = original.get(key), preferred.get(key)
        data = merge_values(earlier or {}, later or {})
        data['team_members'] = merge_members((earlier or {}).get('team_members', []), (later or {}).get('team_members', []))
        variants = []
        for source_id, value in (('enriched', earlier), ('dossiers', later)):
            if value is not None:
                variants.append({'source_id': source_id, 'record': copy.deepcopy(value)})
        data['_source_records'] = variants
        data['_provenance'] = {
            'classification': 'historical_snapshot', 'geographic_scope': 'India',
            'snapshot_date': sources['dossiers']['as_of'] if later else sources['enriched']['as_of'],
            'date_note': 'Dossier publication date is not stated. Enriched JSON declares 2026-09-04; generation time is not a new evidence check.',
            'sources': [copy.deepcopy(sources[v['source_id']]) for v in variants],
            'team_size_basis': 'Original snapshot estimate; not a current headcount or a count of listed profiles.',
            'team_size_sources': [{'value': v['record'].get('team_size'), 'source_id': v['source_id'], 'as_of': sources[v['source_id']]['as_of']} for v in variants],
            'listed_profiles': len(data['team_members']),
            'current_team_size': None,
            'member_status': 'Original public-profile claims and inferred annotations retained; present employment has not been rechecked.',
            'derived_fields': 'Original health scores, salary guesses, departure inferences and playbooks remain historical source claims, not newly validated findings.',
        }
        if data['name'] == 'FIS (TSYS/Global Payments)':
            data['_provenance']['employer_caveat'] = 'Original source conflates FIS with TSYS/Global Payments. Kept under FIS for fidelity; do not treat this as a verified corporate/team relationship.'
        snapshots.append(data)
    return snapshots


def alias_index(items, name_key='name'):
    """An ambiguous exact alias maps to nothing, never to the first matching company."""
    result = {}
    for item in items:
        name = item[name_key]
        group = next((canonical for canonical, aliases in ALIASES.items() if normalized(name) in {normalized(canonical), *(normalized(a) for a in aliases)}), name)
        for alias in [name, group] + ALIASES.get(group, []):
            result.setdefault(normalized(alias), []).append(item)
    return {key: {item[name_key]: item for item in values} for key, values in result.items()}


def exact_match(record, index):
    # Catalog keywords are explicit employer aliases; no substring or fuzzy matching.
    candidates = {}
    aliases_used = []
    for alias in [record['name']] + record.get('keywords', []):
        found = index.get(normalized(alias), {})
        if found:
            aliases_used.append(alias)
            candidates.update(found)
    if len(candidates) == 1:
        return next(iter(candidates.values())), {'method': 'exact_normalized_alias', 'matched_aliases': aliases_used}
    return None, {'method': 'ambiguous_alias' if candidates else 'no_exact_alias', 'candidate_names': sorted(candidates)}


def supplemental_record(name, source, domains, existing=None):
    """Expose a researched employer even when it is absent from the scanner pools."""
    keywords = ALIASES.get(name, [name])
    company = {'name': name, 'keywords': keywords, 'career_url': (existing or {}).get('career_url')}
    career = career_url(company, domains)
    return {
        'target_id': target_id('gcc', name), 'name': name, 'category': 'gcc',
        'location': 'India', 'keywords': copy.deepcopy(keywords),
        'search_links': search_links(company, 'India', career), 'career_url': career,
        'team_snapshot': None, 'recent_team': None, 'check_status': 'pending',
        'target_source': source, 'original_target': None, 'priority': None, 'tier': None,
        'mapping': {'snapshot': None, 'recent_team': None},
    }


def build_directory(base_dir=BASE):
    base = Path(base_dir)
    enriched_path, dossier_path, teams_path = base / 'team_intelligence_enriched.json', base / 'Pega_Deep_Dossiers.html', base / 'research' / 'teams.json'
    enriched = json.loads(enriched_path.read_text(encoding='utf-8-sig'))
    dossier = extract_dossiers(dossier_path)
    recent = json.loads(teams_path.read_text(encoding='utf-8-sig')) if teams_path.exists() else {'teams': []}
    sources = {
        'catalog': source_info(base / 'pega_job_hunter.py', 'catalog', 'local_target_catalog'),
        'enriched': source_info(enriched_path, 'enriched', 'historical_snapshot', enriched.get('meta', {}).get('last_updated')),
        'dossiers': source_info(dossier_path, 'dossiers', 'historical_snapshot'),
    }
    if teams_path.exists():
        sources['recent_teams'] = source_info(teams_path, 'recent_teams', 'source_linked_research', recent.get('as_of'))
    snapshots = build_snapshots(enriched, dossier, sources)
    snapshot_index, recent_index = alias_index(snapshots), alias_index(recent.get('teams', []), 'company')
    records = load_catalog(base)
    scanner_count = len(records)
    domains = read_scanner_constants(base / 'pega_job_hunter.py').get('CAREER_PORTAL_DOMAINS', {})
    scanner_snapshot_names = {snapshot['name'] for record in records for snapshot, _ in [exact_match(record, snapshot_index)] if snapshot}
    for snapshot in snapshots:
        if snapshot['name'] not in scanner_snapshot_names:
            records.append(supplemental_record(snapshot['name'], 'historical_only', domains, snapshot))
    historical_added = len(records) - scanner_count
    covered_recent = {team['company'] for record in records for team, _ in [exact_match(record, recent_index)] if team}
    for team in recent.get('teams', []):
        if team['company'] not in covered_recent:
            records.append(supplemental_record(team['company'], 'recent_research_only', domains, team))
    recent_added = len(records) - scanner_count - historical_added
    matched = set()
    for record in records:
        snapshot, mapping = exact_match(record, snapshot_index)
        record['mapping']['snapshot'] = mapping
        if snapshot:
            matched.add(snapshot['name'])
            record['team_snapshot'] = copy.deepcopy(snapshot)
            record['team_snapshot']['_provenance']['target_scope_note'] = (
                'India snapshot shown for employer background only; it does not describe this overseas target team or establish remote eligibility.'
                if record['category'] == 'global' else
                'Historical India snapshot; individual member locations are preserved and should be checked separately.'
            )
        team, mapping = exact_match(record, recent_index)
        record['mapping']['recent_team'] = mapping
        record['recent_team'] = copy.deepcopy(team)
        if record['category'] == 'global' and team:
            record['recent_team_scope_note'] = 'Recent India research is employer background, not confirmation of an overseas team or remote opening.'
    categories = Counter(r['category'] for r in records)
    return {
        'schema_version': 1, 'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'sources': sources, 'records': records, 'historical_snapshots': snapshots,
        'recent_teams': copy.deepcopy(recent.get('teams', [])),
        'stats': {
            'total_targets': len(records), 'categories': dict(categories),
            'scanner_targets': scanner_count, 'scanner_categories': dict(Counter(r['category'] for r in records if r['target_source'] == 'scanner_catalog')),
            'historical_only_targets': historical_added, 'recent_research_only_targets': recent_added,
            'historical_companies': len(snapshots),
            'historical_profiles': sum(len(s.get('team_members', [])) for s in snapshots),
            'dossier_profiles': sum(len(s.get('team_members', [])) for s in dossier),
            'enriched_profiles': sum(len(s.get('team_members', [])) for s in enriched.get('companies', [])),
            'targets_with_snapshot': sum(r['team_snapshot'] is not None for r in records),
            'distinct_snapshots_mapped': len(matched),
            'unmatched_snapshot_names': sorted(s['name'] for s in snapshots if s['name'] not in matched),
            'recent_team_records': len(recent.get('teams', [])),
            'targets_with_recent_team': sum(r['recent_team'] is not None for r in records),
            'pending_checks': len(records),
        },
        'methodology': [
            'All three scanner catalogs are parsed with ast.literal_eval; scanner imports, logging and network behavior are never executed.',
            'Historical snapshots are preserved in full. Dossier values lead the merged view; original source variants retain every conflicting field and profile.',
            'A named profile is an observed historical profile, not proof of current employment or a complete team headcount.',
            'Matching uses explicit exact normalized aliases; ambiguous mappings remain unmatched. Global targets reuse India information only with an explicit scope label.',
            'Search links and career URLs are navigation aids from the catalog, not claims of open vacancies. Pending checks are not zero jobs.',
            'Category counts describe catalog targets, including overseas and broad searches; they are not unique employers or verified Pega teams.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-dir', type=Path, default=BASE)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = build_directory(args.base_dir)
    output = args.output or args.base_dir / 'research' / 'directory.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result['stats'], ensure_ascii=False))


if __name__ == '__main__':
    main()
