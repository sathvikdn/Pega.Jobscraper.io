"""
Final cleanup based on exhaustive LinkedIn cross-verification of all 20 empty companies.
1. Add verified people where found
2. Remove companies with ZERO India Pega devs
3. Mark vendor-only companies appropriately
"""
import json

# Companies to REMOVE - zero India-based Pega devs confirmed
REMOVE_COMPANIES = [
    "Comcast India",        # All Salesforce/SAP, no Pega
    "Navistar / International Motors India",  # All US-based Pega team
    "UPS India",            # No India Pega practice
    "Estes Express India",  # All US-based (Richmond VA)
    "CNO Financial India",  # All US-based (Carmel IN)
    "Medtronic India",      # No Pega platform usage
    "Philips India",        # No Pega platform usage
    "Fiserv",               # No India Pega devs
    "HDFC Bank",            # Vendor-only model, zero direct
]

# New members to ADD for previously empty companies
NEW_MEMBERS = {
    "Nike India": [
        {"name": "Balasubramani Veerapandian", "title": "Sr. Software Engineer - PEGA CSSA v25", "certs": "CSSA", "location": "Bengaluru",
         "linkedin": "https://www.linkedin.com/in/balasubramani-veerapandian-0851a1137"},
    ],
    "First Citizens India": [
        {"name": "Deepak Shahi", "title": "Principal Engineer - Pega CLSA, ex-Pegasystems", "certs": "CLSA, CSSA", "location": "Bengaluru",
         "linkedin": "https://www.linkedin.com/in/deepak-shahi-337470a3"},
        {"name": "Tushar Banerjee", "title": "Lead SE / Pega UX/UI Lead, ex-Pegasystems", "certs": "Pega UI", "location": "Bengaluru",
         "linkedin": "https://www.linkedin.com/in/tushar-banerjee-139366166"},
        {"name": "Nimalan Peter", "title": "Lead SE / Certified Pega Robotics System Architect", "certs": "Pega Robotics SA", "location": "Bengaluru",
         "linkedin": "https://www.linkedin.com/in/nimalan-peter-5425205b"},
        {"name": "Harika Ch", "title": "Developer 3 - CSSA, CPDC, ex-Pegasystems", "certs": "CSSA v7.2, CSA v7.2, CPDC v8.7", "location": "India",
         "linkedin": "https://www.linkedin.com/in/harika-ch-b3431625a"},
        {"name": "Prathyusha Davanpalli", "title": "Senior SE - Pega PRPC/BPM, ex-Cigna", "certs": "Pega PRPC", "location": "India",
         "linkedin": "https://www.linkedin.com/in/prathyusha-davanpalli-90a285144"},
    ],
    "Pegasystems India": [
        {"name": "Yesuraju Chokka", "title": "Principal Solutions Engineer - CLSA, Constellation", "certs": "CLSA v23, CSSA v23, CSSA v8.8", "location": "Hyderabad",
         "linkedin": "https://www.linkedin.com/in/yesuraju-chokka-0576a115a"},
        {"name": "Vivek Kumar Sonu", "title": "Senior System Architect - CLSA Architecture 24.2", "certs": "CLSA 24.2, CSSA, CSA", "location": "Bengaluru",
         "linkedin": "https://www.linkedin.com/in/vivek-kumar-sonu-75124a172"},
        {"name": "Vanaja Chittaboina", "title": "Principal Engineer - CSA, CSSA", "certs": "CSA, CSSA", "location": "Hyderabad",
         "linkedin": "https://www.linkedin.com/in/vanaja-chittaboina-032492147"},
        {"name": "Pradeep Kumar", "title": "Senior Application Engineer - CSSA, CSA, CPDC", "certs": "CSSA v8.8, CSA v8.7, CPDC", "location": "Hyderabad",
         "linkedin": "https://www.linkedin.com/in/pradeepkumar-pega"},
        {"name": "Devarapalli Pradeep Kumar Reddy", "title": "Senior Application Engineer - Smart Disputes, Constellation", "certs": "CSSA, CSA", "location": "Hyderabad",
         "linkedin": "https://www.linkedin.com/in/devarapalli-pradeep-kumar-reddy-039086175"},
        {"name": "Shirisha Reddy Sommannagari", "title": "Senior Cloud Development Engineer - Pega Cloud, GenAI", "certs": "CSSA", "location": "Hyderabad",
         "linkedin": "https://www.linkedin.com/in/shirisha-reddy-sommannagari-408475126"},
    ],
    "AXA India": [
        {"name": "Lekha A", "title": "Pega Developer", "certs": "Pega Developer", "location": "Bengaluru",
         "linkedin": "https://www.linkedin.com/in/lekha-a-7aa726212"},
    ],
    "GE HealthCare India": [
        {"name": "Nagendra Babu Vasa", "title": "Pega Developer", "certs": "Pega Developer", "location": "Hyderabad",
         "linkedin": "https://www.linkedin.com/in/nagendra-babu-vasa-19058423a"},
    ],
    "Novartis India": [
        {"name": "Vijay Krishna", "title": "Sr Pega Developer (via vendor)", "certs": "CSSA", "location": "Hyderabad",
         "linkedin": "https://www.linkedin.com/in/vijaykrishna-talasila"},
    ],
    "Visa": [
        {"name": "Venkata Radheshyam Yekkirala", "title": "Sr. Consultant - Pega BPM", "certs": "Pega BPM", "location": "Bengaluru",
         "linkedin": "https://www.linkedin.com/in/venkata-radheshyam-yekkirala"},
    ],
    "Proximus India": [
        {"name": "Niveditha Bandari", "title": "Solution Engineer - CSA, CSSA, CPDC", "certs": "CSA, CSSA, CPDC", "location": "Hyderabad",
         "linkedin": "https://www.linkedin.com/in/niveditha-bandari-67a577114"},
        {"name": "Abarna Ravichandran", "title": "Senior Associate Consultant (Infosys) - CSA, CSSA", "certs": "CSA, CSSA", "location": "India",
         "linkedin": "https://www.linkedin.com/in/abarnaravi01"},
    ],
    "Synchrony Financial": [
        {"name": "Krishna Das", "title": "Pega Developer", "certs": "Pega Developer", "location": "Mumbai",
         "linkedin": "https://www.linkedin.com/in/krishna-das-83161927a"},
    ],
    "Mondelez India": [
        {"name": "Archit Kumar", "title": "Technical Product Owner - PEGA (direct Mondelez)", "certs": "CPBA", "location": "India",
         "linkedin": "https://www.linkedin.com/in/architkumar4p"},
        {"name": "Modalavalasa Vinay Kumar", "title": "Senior Associate Consultant (Infosys) - Pega SSA", "certs": "CSSA", "location": "Hyderabad",
         "linkedin": "https://www.linkedin.com/in/vinaykumarmodalavalasa"},
    ],
    "Shell India": [
        # Already added in previous batch, skip if exists
    ],
    "Booking Holdings India": [
        # Already added in previous batch, skip if exists
    ],
}

# Mark companies as vendor-only where applicable
VENDOR_NOTES = {
    "Unilever India (Digital Hub)": "Pega work done entirely through Capgemini, Cognizant, Areteans/Credera contractors. No direct Pega hires.",
    "Mondelez India": "Pega development through Infosys, NTT Data, Ascend Avenue contractors. Archit Kumar is direct hire (Product Owner).",
    "Novartis India": "Pega work likely through vendor/contractor model (EPAM, Capgemini).",
}


def main():
    for fname in ["team_intelligence.json", "team_intelligence_enriched.json"]:
        with open(fname, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 1. Remove companies with zero India Pega presence
        before = len(data["companies"])
        data["companies"] = [c for c in data["companies"] if c["name"] not in REMOVE_COMPANIES]
        removed = before - len(data["companies"])
        
        # 2. Add new members
        added = 0
        for company in data["companies"]:
            name = company["name"]
            if name in NEW_MEMBERS and NEW_MEMBERS[name]:
                existing = {m.get("name", "").lower().strip() for m in company.get("team_members", [])}
                for m in NEW_MEMBERS[name]:
                    if m["name"].lower().strip() not in existing:
                        company["team_members"].append(m)
                        added += 1
            
            # 3. Add vendor notes to highlights
            if name in VENDOR_NOTES:
                highlights = company.get("highlights", [])
                note = VENDOR_NOTES[name]
                if note not in highlights:
                    highlights.insert(0, note)
                    company["highlights"] = highlights
        
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        total_co = len(data["companies"])
        total_m = sum(len(c.get("team_members", [])) for c in data["companies"])
        empty = sum(1 for c in data["companies"] if len(c.get("team_members", [])) == 0)
        
        print(f"{fname}:")
        print(f"  Removed {removed} fake companies")
        print(f"  Added {added} verified members")
        print(f"  Final: {total_co} companies, {total_m} members, {empty} still empty")


if __name__ == "__main__":
    main()
