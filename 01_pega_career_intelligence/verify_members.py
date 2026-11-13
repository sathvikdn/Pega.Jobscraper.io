"""Verify every team member has Pega keywords in their profile data."""
import json

PEGA_KEYWORDS = [
    'pega', 'prpc', 'cssa', 'csa ', 'clsa', 'cpdc', 'cpba', 'cmbb',
    'bpm', 'case management', 'decisioning', 'cdh', 'constellation',
    'smart investigate', 'smart dispute', 'collections blueprint',
    'customer service framework', 'cpmc', 'crsa', 'lsa ', 'lsa-',
    'pcsa', 'pclsa', 'pcds', 'cpsd', 'dpa', 'low-code'
]

with open('team_intelligence_enriched.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

flagged = []
passed = 0

for c in data['companies']:
    for m in c.get('team_members', []):
        # Build a blob of all text about this person
        blob_parts = [
            m.get('name', ''),
            m.get('title', ''),
            str(m.get('certs', '')),
            str(m.get('certifications', '')),
            m.get('tenure', ''),
        ]
        for s in m.get('career', []):
            blob_parts.append(s.get('detail', ''))
            blob_parts.append(s.get('role', ''))
            blob_parts.append(s.get('company', ''))
        
        full = ' '.join(blob_parts).lower()
        has_pega = any(kw in full for kw in PEGA_KEYWORDS)
        
        if not has_pega:
            flagged.append((c['name'], m['name'], m.get('title', '')))
        else:
            passed += 1

print(f"PASSED: {passed} members have Pega keywords")
print(f"FLAGGED: {len(flagged)} members with NO Pega keywords\n")

if flagged:
    for company, name, title in flagged:
        print(f"  REMOVE -> {company} | {name} | {title}")
else:
    print("All members verified clean.")
