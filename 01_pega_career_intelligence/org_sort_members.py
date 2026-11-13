"""
Sort team members within each company by organizational hierarchy.
Order: Manager/Director/VP > Architect/LSA > Lead > Senior > Developer > Departed

Also adds a 'role_level' tag to each member for display in the UI.
"""
import json

ROLE_LEVELS = {
    # Level 1: Top management
    "director": 1, "program manager": 1, "general manager": 1, "dgm": 1,
    "vice president": 1, "vp": 1, "svp": 1, "avp -": 1,
    "head pega": 1, "head of": 1, "coe lead": 1, "coe head": 1,
    "product manager": 1,
    
    # Level 2: Architects
    "solutions architect": 2, "solution architect": 2, "architect": 2,
    "clsa": 2, "lsa": 2, "lead system architect": 2,
    "principal consultant": 2, "principal": 2,
    "enterprise architect": 2, "pega architect": 2,
    
    # Level 3: Leads / Tech Leads
    "lead": 3, "tech lead": 3, "technical lead": 3, "team lead": 3,
    "engineering lead": 3, "module lead": 3, "delivery lead": 3,
    "manager -": 3, "manager pega": 3, "senior manager": 3,
    "senior consultant": 3, "agm": 3,
    
    # Level 4: Senior developers
    "senior": 4, "sr ": 4, "sr.": 4, "specialist": 4,
    "senior software": 4, "senior pega": 4, "se ii": 4, "se iii": 4,
    "software engineer ii": 4, "software engineer iii": 4,
    "engineer ii": 4, "engineer iii": 4,
    
    # Level 5: Developers
    "developer": 5, "consultant": 5, "associate": 5, "analyst": 5,
    "software engineer": 5, "application consultant": 5,
    "engineer i": 5, "se i": 5, "bld": 5,
    "jr.": 5, "junior": 5, "intern": 5, "graduate": 5,
}

# Departed keywords push to level 9
DEPARTED_KEYWORDS = ["departed", "left", "leaving", "serving notice", "ex-"]


def get_role_level(member):
    """Return numeric level (1=highest) based on title and career status."""
    title = (member.get("title", "") or "").lower()
    name = (member.get("name", "") or "").lower()
    
    # Check if departed first
    for kw in DEPARTED_KEYWORDS:
        if kw in title:
            return 9, "Departed"
    
    # Check career for departure
    for stop in member.get("career", []):
        role = (stop.get("role", "") or "").lower()
        dates = (stop.get("dates", "") or "").lower()
        if any(kw in role or kw in dates for kw in ["left", "departed", "leaving", "serving notice"]):
            if stop == member.get("career", [{}])[0]:  # First career entry = current
                return 9, "Departed"
    
    # Match against role levels (first match wins, so order matters)
    # Check level 1 first, then 2, etc.
    for level in [1, 2, 3, 4, 5]:
        for keyword, kw_level in ROLE_LEVELS.items():
            if kw_level == level and keyword in title:
                labels = {1: "Management", 2: "Architect", 3: "Lead", 4: "Senior", 5: "Developer"}
                return level, labels[level]
    
    return 5, "Developer"  # Default


def get_role_label(level_num):
    """Get display label for org level."""
    return {1: "Management", 2: "Architect", 3: "Lead", 
            4: "Senior Developer", 5: "Developer", 9: "Departed"}[level_num]


def sort_company_members(data):
    """Sort team members within each company by org hierarchy."""
    changes = 0
    for company in data.get("companies", []):
        members = company.get("team_members", [])
        if len(members) <= 1:
            continue
        
        # Assign levels
        for m in members:
            level, label = get_role_level(m)
            m["_role_level"] = level
            m["_role_label"] = label
        
        # Sort by level (1 first = top management)
        sorted_members = sorted(members, key=lambda m: (m["_role_level"], m.get("name", "")))
        
        # Check if order changed
        old_order = [m.get("name") for m in members]
        new_order = [m.get("name") for m in sorted_members]
        if old_order != new_order:
            changes += 1
        
        company["team_members"] = sorted_members
    
    return changes


def main():
    # Sort the enriched JSON
    with open("team_intelligence_enriched.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    changes = sort_company_members(data)
    
    with open("team_intelligence_enriched.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # Also sort the base JSON
    with open("team_intelligence.json", "r", encoding="utf-8") as f:
        base = json.load(f)
    sort_company_members(base)
    with open("team_intelligence.json", "w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, indent=2)
    
    # Print the org structure for verification
    print(f"Re-sorted {changes} companies by org hierarchy.\n")
    
    # Show a few examples
    for company in data["companies"]:
        members = company.get("team_members", [])
        if len(members) >= 3:
            print(f"\n{'='*60}")
            print(f"{company['name']} ({len(members)} members)")
            print(f"{'='*60}")
            current_label = None
            for m in members:
                label = m.get("_role_label", "?")
                if label != current_label:
                    current_label = label
                    print(f"\n  --- {label} ---")
                print(f"    {m['name']} | {m.get('title', '')[:60]}")


if __name__ == "__main__":
    main()
