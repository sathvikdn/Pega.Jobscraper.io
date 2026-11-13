"""
Apply cross-verification results: update LinkedIn URLs and fix departed people.
"""
import json

# Verified LinkedIn profile URLs from cross-check
VERIFIED_URLS = {
    # Wells Fargo
    "Raja Reddy Bommana": "https://www.linkedin.com/in/raja-reddy-bommana",
    "Ravi Kiran N G": "https://www.linkedin.com/in/ravi-kiran-n-g-a1386b78",
    "Praveen Kumar": "https://www.linkedin.com/in/praveen-kumar-66165822",
    "Rajesh Manem": "https://www.linkedin.com/in/rajesh-manem-27ba761a",
    "Ram Epuri": "https://www.linkedin.com/in/ram-epuri-6399777b",
    # JPMorgan
    "Ashish Agrawal": "https://www.linkedin.com/in/ashishagrawal-lsa",
    "Venkata Trinadh Desu": "https://www.linkedin.com/in/venkatatrinadhdesu",
    "Manusha Majji": "https://www.linkedin.com/in/manushamajji",
    "Rimjhim Srivastava": "https://www.linkedin.com/in/rimjhim-shrivastav",
    "Navya Pusuluri": "https://www.linkedin.com/in/navya-pusuluri-ab869115b",
    # Barclays
    "Harshad Mankar": "https://www.linkedin.com/in/harshadmankar89",
    "Atul Bhagat": "https://www.linkedin.com/in/atul-bhagat",
    # Citi
    "Senthilkumar Sivashanmugam": "https://www.linkedin.com/in/senthilkumar-sivashanmugam-9bb9a8a6",
    "Rajesh Kumar Vijayakumar": "https://www.linkedin.com/in/rajesh-kumar-vijayakumar-b7421b129",
    # Standard Chartered
    "Ashutosh Hingankar": "https://www.linkedin.com/in/ashutosh-hingankar-788984219",
    "Karthika A": "https://www.linkedin.com/in/karthika-a-9ba817102",
    "Jotheeswaran PM": "https://www.linkedin.com/in/joepegaprpc",
    # Sun Life
    "Swarup Mohanty": "https://www.linkedin.com/in/swarupmohanty",
    "Deepak Choudhary": "https://www.linkedin.com/in/deepak-choudhary-371ab3149",
    "Pushkar Raj": "https://www.linkedin.com/in/pushkar-raj-517ba430",
    # MetLife
    "Bhagavan Nagasai Radhakrishna K": "https://www.linkedin.com/in/bhagavan-k",
    "Mahesh Nair": "https://www.linkedin.com/in/mahesh-nair-1454601a9",
    "Suraj Kumar": "https://www.linkedin.com/in/suraj-kumar-ba8b4272",
    # Ford
    "Abinaya Elavarasan": "https://www.linkedin.com/in/abinaya-elavarasan-44056578",
    "Rabi Asirwadh P": "https://www.linkedin.com/in/rabi-asirwadh-p-a61663190",
    # Verizon
    "Smruti Rekha Swain": "https://www.linkedin.com/in/smrutirswain",
    "Sreekar Polepalli": "https://www.linkedin.com/in/sreekar-polepalli-423bb9201",
    # NAB
    "Somil Shukla": "https://www.linkedin.com/in/somil-shukla-428246157",
    "Sudhanshu Kumar": "https://www.linkedin.com/in/sudhanshu-kumar-a21131169",
    "Avinish Kumar": "https://www.linkedin.com/in/avinish-kumar-48799862",
    "Harshavardhan Reddy": "https://www.linkedin.com/in/harshavardhan-reddy-877a19259",
    # Intel
    "Pratik Raj Mishra": "https://www.linkedin.com/in/pratik-raj-mishra-51472449",
    "Poonam Shaw": "https://www.linkedin.com/in/poonam-shaw-908605115",
    # Ameriprise
    "Sunil Murugendrappa": "https://www.linkedin.com/in/sunil-murugendrappa-72489793",
    "Nand Kishor Swami": "https://www.linkedin.com/in/nand-kishor-swami-00b04329",
    # Goldman Sachs
    "Satish Kumar Reddy Bhima": "https://www.linkedin.com/in/satish-kumar-reddy-bhima-80ba285b",
    "Pavan Kumar Raavi": "https://www.linkedin.com/in/pavan-kumar-raavi-07593043",
    # NatWest
    "Karan Rajput": "https://www.linkedin.com/in/karanrajput-pegadecisioningarchitect",
    "Prasad S": "https://www.linkedin.com/in/prasad-s-9841bb30a",
    "Vishambher Gupta": "https://www.linkedin.com/in/vishambher-gupta-1806731a",
    # Rabobank
    "Krishnaprakash Chandrasekaran": "https://www.linkedin.com/in/krishnaprakash89",
    "Varun Kumar": "https://www.linkedin.com/in/varun-kumar-775b2929",
    "Anchal Garg": "https://www.linkedin.com/in/anchal-garg-90583112b",
    "Siddhartha Das": "https://www.linkedin.com/in/siddhartha-das-3a082233",
    "ADL Kumar": "https://www.linkedin.com/in/adl-kumar-03a56a178",
    # MUFG
    "Taha Ezzi": "https://www.linkedin.com/in/taha-ezzi",
    "Swamy Ajmeera": "https://www.linkedin.com/in/swamy-ajmeera-0b7a97226",
    "Praveen Tangella": "https://www.linkedin.com/in/praveentangella",
}

# People who LEFT their company (found during cross-check)
DEPARTED = {
    ("NatWest Group", "Karan Rajput"): "DEPARTED - Now SVP Domain Architect at NAB",
    ("Goldman Sachs", "Satish Kumar Reddy Bhima"): "Note: Based in Richardson, Texas (US), not India",
}


def main():
    for fname in ["team_intelligence.json", "team_intelligence_enriched.json"]:
        with open(fname, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        updated_urls = 0
        updated_titles = 0
        
        for company in data["companies"]:
            co_name = company["name"]
            for member in company.get("team_members", []):
                name = member["name"]
                
                # Update LinkedIn URL if we have a verified one
                if name in VERIFIED_URLS:
                    old = member.get("linkedin", "")
                    new = VERIFIED_URLS[name]
                    if "/search/" in old or old != new:
                        member["linkedin"] = new
                        updated_urls += 1
                
                # Mark departed people
                key = (co_name, name)
                if key in DEPARTED:
                    if "DEPARTED" not in (member.get("title") or ""):
                        member["title"] = DEPARTED[key] + " | " + (member.get("title") or "")
                        updated_titles += 1
        
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"{fname}: Updated {updated_urls} URLs, {updated_titles} titles")
    
    # Count final stats
    with open("team_intelligence_enriched.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    total = sum(len(c.get("team_members", [])) for c in data["companies"])
    direct = sum(1 for c in data["companies"] for m in c.get("team_members", []) 
                 if m.get("linkedin") and "/search/" not in m["linkedin"])
    search = sum(1 for c in data["companies"] for m in c.get("team_members", []) 
                 if m.get("linkedin") and "/search/" in m["linkedin"])
    
    print(f"\nFinal: {total} members | {direct} direct LinkedIn links | {search} search links")


if __name__ == "__main__":
    main()
