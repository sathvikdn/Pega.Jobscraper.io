"""
Team Health Analysis - Score every company based on REAL signals:
- Departures (people who LEFT = bad)
- Recent hires (people who JOINED recently = good)
- Certification depth (CLSA/LSA = strong architecture)
- Team size (bigger = more stable)
- Tenure stability (long-tenured people = healthy)
- Contractor dependency (vendor-heavy = weaker internal team)

Outputs a ranked list and updates team_intelligence JSONs with health scores.
"""
import json
import re

def analyze_company(company):
    """Analyze a single company and return health metrics."""
    name = company["name"]
    members = company.get("team_members", [])
    highlights = company.get("highlights", [])
    hiring_status = (company.get("hiring_status") or "").lower()
    maturity = (company.get("maturity") or "").lower()
    
    # Count signals
    total = len(members)
    departed = 0
    recent_hires = 0  # joined 2025-2026
    clsa_count = 0
    cssa_count = 0
    long_tenure = 0  # 3+ years
    contractors = 0
    ex_pega = 0  # ex-Pegasystems = strong hire
    
    for m in members:
        title = (m.get("title") or "").lower()
        certs = (m.get("certs") or str(m.get("certifications", ""))).lower()
        career = m.get("career", [])
        
        # Departed?
        if "departed" in title or "left" in title or "serving notice" in title or "ex-" in title.split("|")[0]:
            departed += 1
            continue
        
        # CLSA/LSA level?
        if "clsa" in certs or "lsa" in certs or "pclsa" in certs:
            clsa_count += 1
        if "cssa" in certs:
            cssa_count += 1
        
        # Recent hire? Check career dates for 2025/2026
        for stop in career[:1]:  # first career entry = current
            dates = (stop.get("dates") or "").lower()
            if any(y in dates for y in ["2025", "2026", "present"]):
                if any(m in dates for m in ["jan 2025", "feb 2025", "mar 2025", "apr 2025", "may 2025", 
                    "jun 2025", "jul 2025", "aug 2025", "sep 2025", "oct 2025", "nov 2025", "dec 2025",
                    "jan 2026", "feb 2026", "mar 2026", "apr 2026", "may 2026", "jun 2026", "jul 2026",
                    "aug 2026", "sep 2026"]):
                    recent_hires += 1
        
        # Long tenure? Check for 3yr+ or 4yr+ or 5yr+ in dates
        for stop in career[:1]:
            dates = (stop.get("dates") or "")
            yr_match = re.search(r'(\d+)yr', dates)
            if yr_match and int(yr_match.group(1)) >= 3:
                long_tenure += 1
            elif "2021" in dates or "2020" in dates or "2019" in dates or "2018" in dates:
                long_tenure += 1
        
        # Contractor/vendor?
        if "via vendor" in title or "via infosys" in title or "via cognizant" in title or "contractor" in title:
            contractors += 1
        
        # Ex-Pegasystems?
        for stop in career[1:]:
            co = (stop.get("company") or "").lower()
            if "pegasystems" in co or "pega" == co.strip():
                ex_pega += 1
                break
    
    # Check highlights for vendor dependency
    vendor_dependent = any("contractor" in h.lower() or "vendor" in h.lower() or 
                          "through" in h.lower() or "outsource" in h.lower() 
                          for h in highlights)
    
    active = total - departed
    
    # === SCORING (0-100) ===
    score = 50  # baseline
    
    # Team size impact
    if active >= 10: score += 15
    elif active >= 6: score += 10
    elif active >= 3: score += 5
    elif active == 1: score -= 10
    elif active == 0: score -= 30
    
    # Architecture strength (CLSA = senior leadership)
    if clsa_count >= 2: score += 15
    elif clsa_count == 1: score += 8
    
    # CSSA depth
    if cssa_count >= 5: score += 8
    elif cssa_count >= 3: score += 5
    
    # Departures are BAD
    if departed >= 3: score -= 20
    elif departed >= 2: score -= 12
    elif departed == 1: score -= 5
    
    # Recent hires are GOOD
    if recent_hires >= 3: score += 12
    elif recent_hires >= 1: score += 6
    
    # Long tenure = stability
    if long_tenure >= 3: score += 10
    elif long_tenure >= 1: score += 5
    
    # Ex-Pegasystems hires = quality signal
    if ex_pega >= 2: score += 8
    elif ex_pega == 1: score += 4
    
    # Vendor dependency = weaker
    if vendor_dependent: score -= 10
    if contractors >= 2: score -= 8
    
    # Hiring status boost
    if "rapidly" in hiring_status or "actively" in hiring_status: score += 8
    elif "growing" in hiring_status: score += 4
    elif "declining" in hiring_status: score -= 10
    
    # Maturity boost
    if "very high" in maturity: score += 5
    elif "high" in maturity: score += 3
    
    # Cap score
    score = max(10, min(100, score))
    
    # Determine grade
    if score >= 85: grade = "A+"
    elif score >= 75: grade = "A"
    elif score >= 65: grade = "B+"
    elif score >= 55: grade = "B"
    elif score >= 45: grade = "C+"
    elif score >= 35: grade = "C"
    else: grade = "D"
    
    # Determine health label
    if score >= 75: health = "Excellent"
    elif score >= 60: health = "Strong"
    elif score >= 45: health = "Moderate"
    elif score >= 30: health = "Weak"
    else: health = "Critical"
    
    return {
        "score": score,
        "grade": grade,
        "health": health,
        "active": active,
        "departed": departed,
        "clsa": clsa_count,
        "cssa": cssa_count,
        "recent_hires": recent_hires,
        "long_tenure": long_tenure,
        "ex_pega": ex_pega,
        "contractors": contractors,
        "vendor_dependent": vendor_dependent,
    }


def main():
    with open("team_intelligence_enriched.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    results = []
    for company in data["companies"]:
        metrics = analyze_company(company)
        company["_health_score"] = metrics["score"]
        company["_health_grade"] = metrics["grade"]
        company["_health_label"] = metrics["health"]
        company["_health_metrics"] = metrics
        results.append((company["name"], metrics))
    
    # Save updated JSON
    with open("team_intelligence_enriched.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # Also update base JSON
    with open("team_intelligence.json", "r", encoding="utf-8") as f:
        base = json.load(f)
    for company in base["companies"]:
        metrics = analyze_company(company)
        company["_health_score"] = metrics["score"]
        company["_health_grade"] = metrics["grade"]
        company["_health_label"] = metrics["health"]
    with open("team_intelligence.json", "w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, indent=2)
    
    # Print ranked results
    results.sort(key=lambda x: -x[1]["score"])
    
    print("=" * 90)
    print(f"{'RANK':<5} {'SCORE':<6} {'GRADE':<6} {'HEALTH':<12} {'ACTIVE':<7} {'LEFT':<5} {'CLSA':<5} {'HIRE':<5} {'COMPANY'}")
    print("=" * 90)
    
    for i, (name, m) in enumerate(results, 1):
        dep_flag = f" !!{m['departed']}LEFT" if m['departed'] > 0 else ""
        vendor_flag = " [VENDOR]" if m['vendor_dependent'] else ""
        print(f"{i:<5} {m['score']:<6} {m['grade']:<6} {m['health']:<12} {m['active']:<7} {m['departed']:<5} {m['clsa']:<5} {m['recent_hires']:<5} {name}{dep_flag}{vendor_flag}")
    
    # Print tier summary
    tiers = {"A+": [], "A": [], "B+": [], "B": [], "C+": [], "C": [], "D": []}
    for name, m in results:
        tiers[m["grade"]].append(name)
    
    print("\n" + "=" * 90)
    print("TIER SUMMARY")
    print("=" * 90)
    for grade in ["A+", "A", "B+", "B", "C+", "C", "D"]:
        if tiers[grade]:
            print(f"\n  {grade} ({len(tiers[grade])} companies):")
            for name in tiers[grade]:
                print(f"    - {name}")


if __name__ == "__main__":
    main()
