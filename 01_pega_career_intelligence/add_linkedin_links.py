"""
Add LinkedIn search URLs for every team member who doesn't have a direct link.
Format: https://www.linkedin.com/search/results/people/?keywords=NAME+COMPANY+Pega
"""
import json
import urllib.parse

def make_linkedin_search(name, company):
    """Generate a LinkedIn people search URL for this person."""
    # Clean company name for search
    co = company.replace("(MBRDI)", "").replace("(JDTCI)", "").replace("(Link Group)", "")
    co = co.replace("India", "").replace("GCC", "").strip()
    query = f"{name} {co} Pega"
    encoded = urllib.parse.quote(query)
    return f"https://www.linkedin.com/search/results/people/?keywords={encoded}"

def main():
    for fname in ["team_intelligence.json", "team_intelligence_enriched.json"]:
        with open(fname, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        added = 0
        for company in data["companies"]:
            co_name = company["name"]
            for member in company.get("team_members", []):
                if not member.get("linkedin"):
                    member["linkedin"] = make_linkedin_search(member["name"], co_name)
                    added += 1
        
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        total = sum(1 for c in data["companies"] for m in c.get("team_members", []) if m.get("linkedin"))
        print(f"{fname}: Added {added} search links. Total with links: {total}")

if __name__ == "__main__":
    main()
