"""Remove team members who don't pass Pega keyword verification."""
import json

PEGA_KEYWORDS = [
    'pega', 'prpc', 'cssa', 'csa ', 'clsa', 'cpdc', 'cpba', 'cmbb',
    'bpm', 'case management', 'decisioning', 'cdh', 'constellation',
    'smart investigate', 'smart dispute', 'collections blueprint',
    'customer service framework', 'cpmc', 'crsa', 'lsa ', 'lsa-',
    'pcsa', 'pclsa', 'pcds', 'cpsd', 'dpa', 'low-code'
]

def has_pega(m):
    blob_parts = [
        m.get('name', ''), m.get('title', ''),
        str(m.get('certs', '')), str(m.get('certifications', '')),
        m.get('tenure', ''),
    ]
    for s in m.get('career', []):
        blob_parts.extend([s.get('detail', ''), s.get('role', ''), s.get('company', '')])
    full = ' '.join(blob_parts).lower()
    return any(kw in full for kw in PEGA_KEYWORDS)

# Clean the base JSON
with open('team_intelligence.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

removed = 0
for c in data['companies']:
    before = len(c.get('team_members', []))
    c['team_members'] = [m for m in c.get('team_members', []) if has_pega(m)]
    removed += before - len(c['team_members'])

with open('team_intelligence.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Cleaned base JSON: removed {removed} non-Pega members")

# Now rebuild enriched version
import build_deep_dossiers
with open('team_intelligence.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
build_deep_dossiers.enrich_with_career_data(data)

# Verify enriched data is also clean
removed2 = 0
for c in data['companies']:
    before = len(c.get('team_members', []))
    c['team_members'] = [m for m in c.get('team_members', []) if has_pega(m)]
    removed2 += before - len(c['team_members'])

with open('team_intelligence_enriched.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

total = sum(len(c.get('team_members', [])) for c in data['companies'])
print(f"Cleaned enriched JSON: removed {removed2} more non-Pega members")
print(f"Final: {total} verified Pega team members across {len(data['companies'])} companies")
