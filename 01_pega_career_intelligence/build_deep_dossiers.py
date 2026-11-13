"""
Build the complete Pega Deep Dossiers HTML from team_intelligence.json
Generates a comprehensive dossier for ALL 98+ GCC companies with full details.
"""
import json
import html as html_mod

def load_data():
    with open(r"C:\Users\DNSATHV\Desktop\calude\team_intelligence.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Merge supplementary career timeline data from deep research
    enrich_with_career_data(data)
    add_hiring_playbooks(data)
    return data

def enrich_with_career_data(data):
    """Add rich career timeline data for companies where deep research was done"""
    # Map of company name -> additional team members with career timelines
    EXTRA_MEMBERS = {
        "Wells Fargo": [
            {"name": "Bhagyashree Choudhary", "title": "Lead Software Engineer - Pega Architect", "certs": "LSA Part 1, CSSA, CSA", "location": "Hyderabad",
             "career": [
                {"company": "Wells Fargo", "role": "Lead Software Engineer", "dates": "May 2025 - Present", "detail": "Promoted from Sr SE. Attends PegaInnovate. Got LSA-1 in Oct 2024."},
                {"company": "Wells Fargo", "role": "Senior Software Engineer", "dates": "Mar 2020 - May 2025 (5yr 2mo)", "detail": "Pega Developer on PRPC 7.1. Health Insurance -> banking transition."}
             ]},
            {"name": "Shiva Kumar Singani", "title": "Lead Software Engineer - Enterprise Architect", "certs": "CLSA v7.4, TOGAF, CRSA, CSSA, CSA", "location": "Hyderabad",
             "career": [
                {"company": "Wells Fargo", "role": "Lead Software Engineer", "dates": "Jun 2024 - Present", "detail": "16+ years Pega experience. CPM, CPMHC, CardCPM frameworks. TOGAF + CLSA double-certified."}
             ]},
            {"name": "SanthoshKumar Buddha", "title": "Senior Software Engineer - Pega SSA", "certs": "CLSA Part 1, CSSA", "location": "Hyderabad",
             "career": [
                {"company": "Wells Fargo", "role": "Senior Software Engineer", "dates": "Apr 2023 - Present (3yr 4mo)"},
                {"company": "Previous employer", "role": "Technical Lead", "dates": "Jul 2022 - Apr 2023", "detail": "Came from Tech Lead role. Downgraded title to join WF."}
             ]},
            {"name": "Saritha K (Kadiveti)", "title": "Senior Software Engineer - 10yr Pega Veteran", "certs": "CSSA, CSA", "location": "Hyderabad",
             "career": [
                {"company": "Wells Fargo", "role": "Senior Software Engineer", "dates": "Feb 2023 - Present (3yr 5mo)"},
                {"company": "PegaOne", "role": "Senior Pega Developer", "dates": "Sep 2020 - Oct 2022 (2yr 1mo)", "detail": "PegaOne is a German vendor that deploys to GCCs."}
             ]},
            {"name": "Alekhya Anumalla", "title": "Senior Pega Engineer - 10+ yr career", "certs": "CSSA, CSA", "location": "Hyderabad",
             "career": [
                {"company": "Wells Fargo", "role": "Senior Pega Engineer", "dates": "Oct 2022 - Present (3yr 10mo)"},
                {"company": "Incessant Technologies", "role": "Pega Developer", "dates": "Dec 2015 - Oct 2022 (6yr 10mo)"}
             ]},
            {"name": "Hari Hara Kumar P", "title": "Senior Software Engineer - Java + Pega", "certs": "CRSA, CSSA", "location": "Hyderabad",
             "career": [
                {"company": "Wells Fargo", "role": "Senior Software Engineer", "dates": "Dec 2021 - Present (4yr 8mo)", "detail": "Java + Pega hybrid. Pega Robotics certified."}
             ]},
            {"name": "Arun Kumar Bombili", "title": "Lead Software Engineer - People Manager", "certs": "CSSA, CSA", "location": "Hyderabad",
             "career": [
                {"company": "Wells Fargo", "role": "Lead Software Engineer", "dates": "Feb 2024 - Present", "detail": "Promoted from Sr SE. People Manager role. 10+ years Pega."},
                {"company": "Wells Fargo", "role": "Senior Software Engineer", "dates": "Nov 2021 - Feb 2024 (2yr 3mo)"}
             ]}
        ],
        "JPMorgan Chase": [
            {"name": "Sandeep Ega", "title": "Pega Developer Specialist - Longest-tenured", "certs": "CSSA", "location": "Hyderabad",
             "career": [
                {"company": "JPMorgan Chase", "role": "Pega Developer (Specialist)", "dates": "May 2021 - Present (5yr 3mo)", "detail": "5+ year anchor. Longest-serving known Pega dev at JPMC India."}
             ]},
            {"name": "Subhasmita Panda", "title": "Associate - Pega Developer", "certs": "CSSA v8.8, CSA v8", "location": "Bengaluru",
             "career": [
                {"company": "JPMorgan Chase", "role": "Associate", "dates": "Apr 2024 - Present (2yr 4mo)", "detail": "Case Management, UI development, SLAs, REST/SOAP APIs."}
             ]},
            {"name": "Guna Sekhar C N", "title": "Associate - Senior Pega Developer (6yr exp)", "certs": "CSSA", "location": "Bengaluru",
             "career": [
                {"company": "JPMorganChase", "role": "Associate", "dates": "Jul 2024 - Present", "detail": "Attended Pega Innovate 2026 Hyderabad."},
                {"company": "Cognizant", "role": "Pega Developer", "dates": "Feb 2019 - Jul 2024 (5yr 5mo)", "detail": "Worked on Verizon Pega product at Cognizant. Left for JPMC direct."}
             ]},
            {"name": "Indrani Das", "title": "SDE II - Pega Developer", "certs": "CSSA, CSA, CPDC", "location": "Hyderabad",
             "career": [
                {"company": "JPMorganChase", "role": "SDE II", "dates": "Jun 2025 - Present", "detail": "Newest JPMC Pega hire. Cross-functional team."},
                {"company": "LTIMindtree", "role": "Senior Software Engineer", "dates": "Previous role", "detail": "SI-to-GCC career path."}
             ]},
            {"name": "Shaik Danish", "title": "Software Engineer II - 4+ yr Pega", "certs": "CSSA, CSA", "location": "Hyderabad",
             "career": [
                {"company": "JPMorganChase", "role": "Software Engineer II", "dates": "Aug 2025 - Present (11mo)", "detail": "Workflow automation, system integration. Recent hire."}
             ]}
        ],
        "Barclays": [
            {"name": "Sudhanshu Chatterjee", "title": "Vice President - Pega Team Lead (Hiring Manager)", "certs": "CSSA, CSA", "location": "Pune",
             "career": [
                {"company": "Barclays", "role": "Vice President", "dates": "Jun 2023 - Present", "detail": "THE hiring manager for Pega roles. Posted: 'We are looking for CSSA and CLSA with 5+ yr exp.'"},
                {"company": "HCL Technologies", "role": "Senior Consultant", "dates": "Previous"},
                {"company": "Zensar Technologies", "role": "Pega Lead Developer", "dates": "Earlier", "detail": "15yr 8mo total experience. Career: Zensar -> HCL -> Barclays."}
             ]},
            {"name": "Shubhani Panbude", "title": "AVP / Technical Lead - Smart Dispute Expert", "certs": "CPMC, CSSA, CSA", "location": "Pune",
             "career": [
                {"company": "Barclays", "role": "AVP + Technical Lead", "dates": "Apr 2024 (AVP) / Mar 2021 (joined)", "detail": "7.5yr IT exp. Smart Dispute Framework specialist. CPMC certified."},
                {"company": "Zensar Technologies", "role": "Pega Developer", "dates": "Mar 2017 - Dec 2020 (3yr 9mo)"},
                {"company": "Atos India", "role": "Pega Developer", "dates": "Mar 2014 - Feb 2017 (2yr 11mo)"}
             ]},
            {"name": "Karan Yadav", "title": "Pega Developer - AWS AI Certified", "certs": "AWS AI Practitioner, CSSA", "location": "Pune",
             "career": [
                {"company": "Barclays", "role": "Pega Developer", "dates": "Jan 2022 - Present (4yr 7mo)", "detail": "Smart Dispute Framework for Issuer. AWS AI Practitioner cert May 2026."}
             ]},
            {"name": "Niranjan Kale", "title": "Senior Pega Developer - Smart Dispute SSA", "certs": "CSSA Infinity 23, CSA v8.5", "location": "Pune",
             "career": [
                {"company": "Barclays", "role": "Senior Pega Developer", "dates": "Aug 2025 (promoted) - Present", "detail": "Promoted from Dev to Sr Dev."},
                {"company": "Barclays", "role": "Pega Developer", "dates": "Dec 2021 - Aug 2025 (3yr 8mo)"}
             ]},
            {"name": "Mehak Raina", "title": "Pega Developer - 4yr+ at Barclays", "certs": "CSSA", "location": "Pune",
             "career": [
                {"company": "Barclays", "role": "Pega Developer (Specialist)", "dates": "Jul 2022 - Present (4yr 1mo)", "detail": "Application security, archival, headcount management."}
             ]},
            {"name": "Saumit Datta, Rupanshi Thakkar, Abhilash Kulkarni, Paridhi Khare", "title": "Additional team members (tagged in Innovate 2026)", "certs": "",
             "career": [
                {"company": "Barclays", "role": "Pega Team Members", "dates": "Current", "detail": "All tagged by VP Sudhanshu in Pega Innovate 2026 team photo. Confirms 12+ people."}
             ]}
        ],
        "Citibank": [
            {"name": "Akash Pratap", "title": "Vice President - Pega Lead System Architect", "certs": "CLSA, CPDC, CSSA, CSA", "location": "Pune",
             "career": [
                {"company": "Citi India", "role": "Vice President", "dates": "Feb 2024 - Present", "detail": "CLSA + CPDC certified VP. Returned from onsite (Irving, TX)."},
                {"company": "Citi", "role": "Onsite (Irving, TX)", "dates": "Aug 2022 - Feb 2024 (1yr 6mo)"}
             ]},
            {"name": "CHRISTOPHER PRADEEP JOHN BRITTO", "title": "Lead System Architect - Jul 2026 from SCB", "certs": "CPDC v8.8, CSSA",
             "career": [
                {"company": "Citi", "role": "Lead System Architect", "dates": "Jul 2026 - Present", "detail": "JUST joined from Standard Chartered (5.5yr there). HCL Hackathon winner."}
             ]},
            {"name": "Kavitha Kuppusamy", "title": "Senior Pega Developer - CLSA P1 + Chat Dev", "certs": "CLSA Part 1, CSSA", "location": "Chennai",
             "career": [
                {"company": "Citi India", "role": "Senior Pega Developer", "dates": "Aug 2021 - Present (4yr 11mo)", "detail": "CLSA P1 certified. Pega Chat Developer. ML interest."}
             ]},
            {"name": "Amit Dangayach", "title": "Project Lead - Smart Investigate + CPMHC", "certs": "CSSA", "location": "Pune",
             "career": [
                {"company": "Citi India", "role": "Project Lead", "dates": "Jan 2023 - Present", "detail": "13yr Pega exp. Smart Investigate + CPMHC framework expert."},
                {"company": "HSBC", "role": "Pega Lead", "dates": "May 2016 - Aug 2023 (7yr 3mo)", "detail": "7+ years at HSBC Pune before Citi."}
             ]}
        ],
        "MetLife India GCC": [
            {"name": "Bhagavan Nagasai Radhakrishna K", "title": "Software Platform Engineer II - Most Senior", "certs": "AWS Certified, Pega Infinity, Constellation", "location": "Hyderabad",
             "career": [
                {"company": "MetLife", "role": "Software Platform Engineer II", "dates": "~2022 - Present (4yr+)", "detail": "THE most senior Pega dev. Led Pega Cloud 2->3 migration. 50+ REST services, 70+ connectors. Mentored 200+ engineers."}
             ]},
            {"name": "Srikanth Amma", "title": "Lead Software Engineer - 9yr+ Pega", "certs": "CSA", "location": "Hyderabad",
             "career": [
                {"company": "MetLife", "role": "Lead Software Engineer", "dates": "Apr 2026 - Present (3mo)", "detail": "Newest senior hire. 9+ years Pega exp."},
                {"company": "TCS", "role": "Pega Developer", "dates": "Feb 2025 - Apr 2026", "detail": "Was TCS -> deployed to MetLife -> converted to direct."}
             ]},
            {"name": "Mahesh Nair", "title": "Specialist - Pega Constellation", "certs": "CSSA", "location": "Noida",
             "career": [
                {"company": "MetLife", "role": "Specialist Technology Services", "dates": "Jan 2025 - Present", "detail": "Pega Constellation design system. End-to-end case lifecycles. Guardrails compliance."}
             ]},
            {"name": "Pranathi Rachamalla", "title": "Senior Software Engineer - ex-Coforge/Accenture", "certs": "CSSA", "location": "Hyderabad",
             "career": [
                {"company": "MetLife", "role": "Senior Software Engineer", "dates": "Sep 2025 - Present", "detail": "Coforge -> MetLife conversion. 5.5yr+ IT exp."},
                {"company": "Coforge", "role": "Pega Developer", "dates": "Jun 2022 - Sep 2025 (3yr 3mo)"},
                {"company": "Accenture", "role": "Application Development Analyst", "dates": "~2019 - Jun 2022 (2yr 7mo)"}
             ]}
        ],
        "Ford Motor Company": [
            {"name": "Abinaya Elavarasan", "title": "Technical Project Manager - FORD Pega CoE Lead", "certs": "LSA Part 1, CSSA, CSA", "location": "Chennai",
             "career": [
                {"company": "Ford Motor Company", "role": "Technical Project Manager", "dates": "Jun 2024 - Present", "detail": "THE Ford Pega CoE Lead. 10+ years Pega. Architected 40+ enterprise automations. 59 FTEs saved. 98% defect-free releases."},
                {"company": "Ford Motor Company", "role": "Earlier Pega roles", "dates": "~2017+ - Jun 2024", "detail": "Grew from developer to project manager within Ford."}
             ]},
            {"name": "Mamtha Nivedha Paulraj", "title": "Pega Developer - Integrations + Mobile", "certs": "CSSA", "location": "Chennai",
             "career": [
                {"company": "Ford Motor Company", "role": "Pega Developer", "dates": "Mar 2024 - Present", "detail": "5+ years Pega exp. REST/SOAP integrations, Pega Mobile, CPM, UI design."}
             ]},
            {"name": "Lakshmi A", "title": "Software Engineer - Intern converted to FTE", "certs": "CSSA, CSA", "location": "Chennai",
             "career": [
                {"company": "Ford Motor Company", "role": "Software Engineer", "dates": "Feb 2024 - Present", "detail": "Intern->FTE conversion. Got CSSA in Feb 2026. Ford investing in growing juniors."}
             ]},
            {"name": "Somesh B M", "title": "Software Engineer - CPDC + CSSA triple-certified", "certs": "CPDC, CSSA, CSA", "location": "Chennai",
             "career": [
                {"company": "Ford Motor Company", "role": "Software Engineer", "dates": "Feb 2024 - Present", "detail": "Triple-certified within 1 year of joining. Ford encourages aggressive certification."}
             ]},
            {"name": "RAGUL S", "title": "Pega Developer - ex-TCS, converted to Ford direct", "certs": "CSA", "location": "Chennai",
             "career": [
                {"company": "Ford Motor Company", "role": "Pega Developer", "dates": "Jun 2025 - Present"},
                {"company": "TCS", "role": "Pega Developer", "dates": "May 2021 - Feb 2024 (2yr 9mo)"}
             ]},
            {"name": "SURYA S", "title": "Software Engineer - transferred to Bengaluru", "certs": "CSSA v8.7", "location": "Bengaluru",
             "career": [
                {"company": "Ford Motor Company", "role": "Software Engineer", "dates": "Jan 2026 - Present", "detail": "Transferred from Chennai to Bengaluru. Ford expanding Pega to BLR!"},
                {"company": "Ford Motor Company", "role": "Pega Developer", "dates": "Jan 2024 - Dec 2025 (2yr)", "detail": "Originally in Chennai."}
             ]}
        ],
        "Standard Chartered": [
            {"name": "CHRISTOPHER PRADEEP JOHN BRITTO", "title": "Lead System Architect - LEFT for Citi Jul 2026", "certs": "CPDC v8.8, CSSA", "location": "Chennai",
             "career": [
                {"company": "Standard Chartered Bank", "role": "Lead System Architect (LEFT)", "dates": "Dec 2020 - Jul 2026 (5yr 7mo)", "detail": "LEFT in Jul 2026 to join Citi. HCL Hackathon 2022 2nd prize. 5.5yr tenure lost!"}
             ]},
            {"name": "Ashokkumar Selvam", "title": "Pega Lead System Architect - 6yr+ at SCB", "certs": "CSSA", "location": "Chennai",
             "career": [
                {"company": "Standard Chartered Bank", "role": "Pega Lead System Architect", "dates": "Jun 2022 - Present (4yr 2mo)"},
                {"company": "Standard Chartered Bank", "role": "Pega Architect (earlier stint)", "dates": "Dec 2018 - Jan 2020 (1yr 1mo)", "detail": "Returned to SCB after a gap. Total SCB tenure: 6+ years across stints."}
             ]},
            {"name": "Bhavya Arunkumar", "title": "Senior Pega Developer - Promoted Jul 2025", "certs": "CSSA v8.6, CSA", "location": "Bengaluru",
             "career": [
                {"company": "Standard Chartered India", "role": "Senior Pega Developer", "dates": "Jul 2025 (promoted) - Present", "detail": "Promoted after 4yr as Dev."},
                {"company": "Standard Chartered India", "role": "Pega Developer", "dates": "Jul 2021 - Jul 2025 (4yr)"}
             ]},
            {"name": "Subhashree Venkatachalam", "title": "Pega SSA - Jun 2025 hire", "certs": "CSSA", "location": "India",
             "career": [
                {"company": "Standard Chartered", "role": "Pega SSA (Senior)", "dates": "Jun 2025 - Present", "detail": "NEW hire. Dispute Resolution, Fire Insurance, Collateral, Loan Applications. Nordea + Citi Program experience."}
             ]}
        ],
        "Sun Life": [
            {"name": "Akansha Bhadauria", "title": "Development Specialist - Longest-tenured (3yr+)", "certs": "CPDC, CSSA, CSA", "location": "Gurugram",
             "career": [
                {"company": "Sun Life", "role": "Development Specialist (promoted Oct 2024)", "dates": "Jan 2022 - Present (4yr 7mo)", "detail": "Promoted from Dev Analyst. CPDC certified Jul 2024. 4+ year anchor."}
             ]},
            {"name": "Vishal Kasana", "title": "Development Specialist - ex-Pegasystems", "certs": "CLM KYC, Constellation, React JS, Gen AI",
             "career": [
                {"company": "Sun Life", "role": "Development Specialist", "dates": "Apr 2025 - Present"},
                {"company": "Pegasystems", "role": "Application Engineer, Financial Services Onboarding", "dates": "Apr 2022 - Apr 2025 (3yr)", "detail": "Was AT Pegasystems. Left Pega to join customer directly. CLM KYC + Constellation specialist."}
             ]},
            {"name": "Srinivas Adabala", "title": "Senior Specialist Development - Mobile Client expert", "certs": "CPDC, CSSA", "location": "Bengaluru",
             "career": [
                {"company": "Sun Life", "role": "Senior Specialist Development", "dates": "Oct 2025 - Present", "detail": "Pega Mobile Client experience - rare skill. React.js, jQuery, front-end."}
             ]},
            {"name": "Baivaw Kumar Dubey", "title": "Specialist Development - Constellation + Gen AI", "certs": "CSSA, CPBA, Constellation, Gen AI", "location": "Bengaluru",
             "career": [
                {"company": "Sun Life", "role": "Specialist Development", "dates": "Jul 2025 - Present"},
                {"company": "LTIMindtree", "role": "Senior Software Engineer", "dates": "May 2023 - Jul 2025 (2yr 2mo)"},
                {"company": "Coforge", "role": "Pega Developer", "dates": "May 2022 - May 2023 (1yr)"},
                {"company": "Cognizant", "role": "Pega Developer", "dates": "Jan 2020 - May 2022 (2yr 4mo)"}
             ]},
            {"name": "Datri Awasthi", "title": "Specialist Developer - ex-John Deere!", "certs": "CSSA, CSA", "location": "Gurugram",
             "career": [
                {"company": "Sun Life", "role": "Specialist Developer", "dates": "Jul 2025 - Present"},
                {"company": "John Deere", "role": "Senior Software Engineer", "dates": "Nov 2022 - Jul 2025 (2yr 8mo)", "detail": "LEFT JOHN DEERE for Sun Life! 'Proactive and learning mindset. Works as a lead by example.' - colleague review."}
             ]}
        ],
        "Roche India": [
            {"name": "Prashant Patil", "title": "Pega Architect - ex-Pegasystems, JUST got CLSA", "certs": "CLSA (Aug 2026!), CSSA", "location": "Pune",
             "career": [
                {"company": "Roche", "role": "Pega Architect", "dates": "Nov 2025 - Present (9mo)", "detail": "Day-1 hire for Roche Pega team. JUST cleared CLSA in Aug 2026! Hiring more AI Architects."},
                {"company": "Pegasystems", "role": "Solutions Engineer / Architect", "dates": "Apr 2022 - Nov 2025 (3yr 7mo)", "detail": "Was AT Pegasystems itself. Left the mothership to build Roche's team from scratch."}
             ]},
            {"name": "Kirti Gabda", "title": "Pega IT Lead - Triple-certified veteran", "certs": "CSSA, CPDC, CPBA", "location": "Pune",
             "career": [
                {"company": "Roche", "role": "Pega IT Lead", "dates": "Nov 2025 - Present (9mo)", "detail": "Day-1 hire alongside Prashant. 10+ years Pega exp. Worked on projects from Netherlands, Belgium, Norway."}
             ]}
        ],
        "NAB (National Australia Bank)": [
            {"name": "Gyanendra Mishra", "title": "Pega Developer - SERVING NOTICE PERIOD", "certs": "CSSA, CSA, Constellation", "location": "Gurugram",
             "career": [
                {"company": "NAB", "role": "Pega Developer (SERVING NOTICE)", "dates": "Mar 2025 - Present (LEAVING)", "detail": "LinkedIn headline literally says 'Serving Notice Period.' Leaving after only 1.4 years!"},
                {"company": "Cognizant", "role": "Pega Developer (Analyst)", "dates": "Dec 2022 - Feb 2025 (2yr 2mo)"}
             ]}
        ],
        "Morgan Stanley": [
            {"name": "Abhinav Anand", "title": "Director - CLSA + Microsoft Power Platform", "certs": "CLSA, Microsoft Power Platform", "location": "Bengaluru",
             "career": [
                {"company": "Morgan Stanley", "role": "Director (promoted Jan 2025)", "dates": "Jul 2021 - Present (4yr 3mo)", "detail": "Director level = very senior. CLSA + Power Platform dual expertise."},
                {"company": "Pegasystems", "role": "System Architect II", "dates": "Previous", "detail": "Was at Pegasystems before moving to Morgan Stanley."}
             ]},
            {"name": "Snehasis Panda", "title": "Director - 8yr+ Pega veteran, CLSA-1", "certs": "CLSA Part 1, CSSA v8, Power Apps", "location": "Bengaluru",
             "career": [
                {"company": "Morgan Stanley", "role": "Director (promoted Jan 2025)", "dates": "Aug 2021 - Present (4yr)", "detail": "8+ years Pega exp. Complex KYC, client onboarding, regulatory platforms. Pega v7->v24 experience."},
                {"company": "Mphasis", "role": "Pega Developer", "dates": "Nov 2017 - Feb 2020 (2yr 3mo)"}
             ]}
        ],
        "Verizon": [
            {"name": "Harika Yadavalli", "title": "Software Engineer III - LSA-P1 anchor", "certs": "LSA Part 1, CSSA, CPBA, CPDC", "location": "Hyderabad",
             "career": [
                {"company": "Verizon", "role": "Software Engineer III", "dates": "Jul 2023 - Present", "detail": "8+ years Pega exp. LSA-P1 + CPDC + CPBA quad-certified. Carnatic music vocalist."},
                {"company": "Pegasystems", "role": "Solutions Engineer", "dates": "Mar 2021 - Jul 2023 (2yr 4mo)"},
                {"company": "TCS", "role": "Pega Developer", "dates": "Jul 2018 - Feb 2021 (2yr 7mo)"}
             ]},
            {"name": "Shireesha Chappidi", "title": "Engr II - Promoted Apr 2025", "certs": "CSSA, CSA, CPDC", "location": "Hyderabad",
             "career": [
                {"company": "Verizon", "role": "Engr II - Emerging Commercial Platforms", "dates": "Apr 2025 (promoted) - Present"},
                {"company": "Verizon", "role": "Engr I", "dates": "Aug 2023 - Mar 2025 (1yr 7mo)"}
             ]},
            {"name": "Sivaguru Sankaranarayanan", "title": "Engr II - CDH + GenAI specialist", "certs": "CSSA, GenAI/Agentic AI", "location": "Chennai",
             "career": [
                {"company": "Verizon", "role": "Engr II", "dates": "Dec 2023 - Present", "detail": "Pega Decisioning + Case Management. POC for Power BI + Pega REST. GenAI/Langflow/Ollama!"}
             ]},
            {"name": "Sreekar Polepalli", "title": "SE III Consultant - CDH tester", "certs": "CSA, CDH", "location": "Hyderabad",
             "career": [
                {"company": "Verizon Business", "role": "SE III Consultant - Pega CDH", "dates": "Sep 2025 - Present", "detail": "UAT testing for marketing campaigns. CDH decisioning validation. ex-Infosys."}
             ]},
            {"name": "SUBRAHMANYAN D", "title": "Engr I - Intern to FTE conversion", "certs": "CSSA", "location": "Chennai",
             "career": [
                {"company": "Verizon", "role": "Engr I Software Developer", "dates": "Jul 2024 - Present"},
                {"company": "Verizon", "role": "Student Intern", "dates": "Feb 2024 - Jul 2024 (5mo)", "detail": "Intern->FTE conversion. Got CSSA during internship!"}
             ]},
            {"name": "Winnie Mathew", "title": "DEPARTED - 6yr veteran, left Jul 2026", "certs": "", "location": "",
             "career": [
                {"company": "Verizon", "role": "~6yr tenure (LEFT Jul 2026)", "dates": "~2020 - Jul 2026", "detail": "Posted: 'After nearly 6 incredible years at Verizon, I've decided to embark on a new journey.'"}
             ]}
        ],
        "Nokia India": [
            {"name": "Vivek Kumar", "title": "Technical Lead / Pega System Architect - CLSA-1", "certs": "CLSA Part 1, CPDC, CSSA, CSA", "location": "Bengaluru",
             "career": [
                {"company": "Nokia", "role": "Pega System Architect", "dates": "Mar 2022 - Present (4yr 5mo)", "detail": "CLSA-P1 + CPDC + CSSA quad-certified. Was sharing Nokia Pega job posts (Oct 2025)."}
             ]},
            {"name": "Sirisha Pullagura", "title": "Pega System Architect - New hire May 2025", "certs": "CSSA, CSA",
             "career": [
                {"company": "Nokia", "role": "Pega System Architect", "dates": "May 2025 - Present"},
                {"company": "Cognizant", "role": "Pega Developer", "dates": "Feb 2021 - Jul 2022 (1yr 5mo)"}
             ]}
        ],
        "Commonwealth Bank": [
            {"name": "Anjana A", "title": "Senior Software Engineer - 10yr Pega veteran", "certs": "CSSA", "location": "Bengaluru",
             "career": [
                {"company": "Commonwealth Bank", "role": "Senior Software Engineer", "dates": "Feb 2023 - Present", "detail": "10+ year Pega career. Trebla (Smart POS). AI-Assisted Development (Copilot, Claude). Next.js learning."},
                {"company": "Deloitte", "role": "Senior Software Engineer", "dates": "Jun 2022 - Feb 2023 (8mo)"}
             ]},
            {"name": "Kumar Kanisetty", "title": "Pega (Data) Engineer - CSSA + CPDC + AWS", "certs": "AWS Data Engineer Associate, CPDC, CSSA", "location": "Bengaluru",
             "career": [
                {"company": "Commonwealth Bank", "role": "Pega (Data) Engineer", "dates": "Mar 2022 - Present (4yr 5mo)", "detail": "4+ year CBA anchor. Triple-certified. Data engineering + Pega hybrid = rare."}
             ]},
            {"name": "Premkumar Ganesan", "title": "DEPARTED - CLSA, Pega CoE Lead", "certs": "CLSA", "location": "Bengaluru",
             "career": [
                {"company": "Commonwealth Bank", "role": "Pega CoE Lead (LEFT Dec 2025)", "dates": "~2023 - Dec 2025 (2.5yr)", "detail": "LEFT in Dec 2025. Posted: 'After an amazing 2.5-year flight path with the Pega CoE...'"}
             ]}
        ],
        "MUFG Pension & Market Services (Link Group)": [
            {"name": "Shubham Shinde", "title": "Senior Pega Developer - Promoted Oct 2024", "certs": "CSSA", "location": "Pune",
             "career": [
                {"company": "MUFG Pension & Market Services", "role": "Senior Pega Developer", "dates": "Oct 2024 (promoted) - Present"},
                {"company": "MUFG Pension & Market Services", "role": "Pega Developer", "dates": "May 2022 - Oct 2024 (2yr 5mo)"}
             ]},
            {"name": "Shivshant Singh", "title": "Pega Developer - Promoted Oct 2025", "certs": "CSSA, CSA", "location": "Mumbai",
             "career": [
                {"company": "MUFG Pension & Market Services", "role": "Pega Developer (promoted)", "dates": "Oct 2025 - Present"},
                {"company": "MUFG Pension & Market Services", "role": "Associate Developer", "dates": "Sep 2023 - Oct 2025 (2yr 1mo)"}
             ]},
            {"name": "Aastha Shah", "title": "Pega Developer - Promoted Oct 2025", "certs": "CSSA v8.8, CSA v8.7", "location": "Mumbai",
             "career": [
                {"company": "MUFG Pension & Market Services", "role": "Pega Developer (promoted)", "dates": "Oct 2025 - Present"},
                {"company": "MUFG Pension & Market Services", "role": "Associate Developer", "dates": "Jul 2023 - Sep 2025 (2yr 2mo)"}
             ]},
            {"name": "Sakshi Khandelwal", "title": "Pega Developer - New hire Jan 2026", "certs": "CSSA, CSA", "location": "Mumbai",
             "career": [
                {"company": "MUFG Pension & Market Services", "role": "Pega Developer", "dates": "Jan 2026 - Present"},
                {"company": "TCS", "role": "System Engineer (Pega)", "dates": "Jul 2024 - Jan 2026 (1yr 6mo)", "detail": "Left TCS for MUFG direct."}
             ]},
            {"name": "Prathamesh D", "title": "Pega Developer - Newest hire Jul 2026", "certs": "", "location": "Mumbai",
             "career": [
                {"company": "MUFG Pension & Market Services", "role": "Pega Developer", "dates": "Jul 2026 - Present (1mo)", "detail": "Newest hire. Posted excitedly about joining MUFG."}
             ]}
        ],
        "Mercedes-Benz R&D India (MBRDI)": [
            {"name": "Manomit Das", "title": "Program Manager - Pega Team Lead (AAP Markets)", "certs": "Six Sigma Green Belt", "location": "Bengaluru",
             "linkedin": "https://www.linkedin.com/in/manomit-das-4b354a16",
             "career": [
                {"company": "Mercedes-Benz R&D India", "role": "Program Manager", "dates": "Jul 2025 - Present (1yr 1mo)", "detail": "THE Pega team manager. Leads AAP markets Pega team. Attended Pega Innovate 2026. Spontan Award winner. 14yr+ total exp."},
                {"company": "Mercedes-Benz R&D India", "role": "IT Product Owner - APAC", "dates": "Earlier", "detail": "Product ownership for APAC Pega initiatives."},
                {"company": "Mercedes-Benz R&D India", "role": "Solutions Architect", "dates": "Earlier", "detail": "Grew from Solutions Architect to Program Manager within MBRDI."},
                {"company": "EY", "role": "Associate Project Manager", "dates": "Previous", "detail": "Career: EY -> MBRDI. Consulting to GCC path."}
             ]},
            {"name": "Bhanu Prasad V", "title": "Solutions Architect - Pega Architect", "certs": "CSA v7.1", "location": "Bengaluru",
             "linkedin": "https://www.linkedin.com/in/bhanu-prasad-v-1b019727",
             "career": [
                {"company": "Mercedes-Benz R&D India", "role": "Solutions Architect (Pega)", "dates": "Jul 2022 - Present (4yr 1mo)", "detail": "THE Pega Architect. PEGA + Java Enterprise + Agile. 4+ years leading architecture at MBRDI."}
             ]},
            {"name": "Sathvik D N", "title": "Software Consultant - Pega CSSA | Kafka | Collections", "certs": "CSSA, CSA", "location": "Bengaluru",
             "linkedin": "https://www.linkedin.com/in/sathvik-d-n-7462071ab",
             "career": [
                {"company": "Mercedes-Benz R&D India", "role": "Software Consultant (Pega CSSA)", "dates": "Sep 2023 - Present (3yr)", "detail": "Auto Finance Collections. Kafka real-time integration. Case Management, REST APIs, CI/CD. Mobility Maverick recognition."}
             ]},
            {"name": "Mithun R", "title": "DEPARTED Jun 2026 - Now at Inadev", "certs": "CSSA, CSA", "location": "Bengaluru",
             "linkedin": "https://www.linkedin.com/in/mithun-r-a13a501a6",
             "career": [
                {"company": "Inadev", "role": "Senior Software Engineer (Current)", "dates": "Jun 2026 - Present", "detail": "LEFT MBRDI. Posted: 'Cruising out of an amazing chapter. Accelerating into the next one.'"},
                {"company": "Mercedes-Benz R&D India", "role": "Senior Consultant (LEFT Jun 2026)", "dates": "Jul 2025 - Jun 2026 (11mo)", "detail": "Promoted to Sr Consultant. Designed Collections Blueprint for EU markets. 4 markets rolled out in 1 year. Mobility Maverick Award."},
                {"company": "Mercedes-Benz R&D India", "role": "Consultant (Pega Developer)", "dates": "Apr 2023 - Jul 2025 (2yr 3mo)", "detail": "E2E implementation. Legacy system migrations. Service Operations."},
                {"company": "Cognizant", "role": "Associate (Pega Developer)", "dates": "Jan 2023 - Mar 2023 (2mo)", "detail": "CDH, REST API architecture."}
             ]},
            {"name": "Rupali Chaturvedi", "title": "Principal Consultant PEGA - Lead Business Process Analyst", "certs": "CMBB, CBA v6.1, CPBA", "location": "Bengaluru",
             "linkedin": "https://www.linkedin.com/in/rupali-chaturvedi-9a93799",
             "career": [
                {"company": "Mercedes-Benz R&D India", "role": "Principal Consultant PEGA", "dates": "Feb 2019 - Present (7yr 6mo)", "detail": "14+ years exp. Lead BA/Delivery Lead. SmartBPM, PMF, TMF methodologies. Smart Investigate for Payments expertise."},
                {"company": "Accenture", "role": "Sr Business Analyst - Pega BPM", "dates": "Previous", "detail": "Process Architect for Pega Smart Investigate Framework for Payments."},
                {"company": "IBM", "role": "Solution Consultant - Pega BPM", "dates": "Earlier"}
             ]},
            {"name": "Moumita Dasgupta", "title": "Manager / Principal Consultant - Pega PRPC Senior Architect", "certs": "CSSA v7.1, CSA v7.1", "location": "Bengaluru",
             "linkedin": "https://www.linkedin.com/in/mdgupta",
             "career": [
                {"company": "Mercedes-Benz R&D India", "role": "Manager - Pega PRPC Senior Architect", "dates": "Oct 2022 - Present (3yr 9mo)", "detail": "Leading Core Teams in PEGA Platform Integrations. 8+ years Pega exp in BFSI sector. SME for Transition Management."},
                {"company": "Previous (Banking)", "role": "Pega Senior System Architect", "dates": "Earlier", "detail": "Enterprise BPM solutions for US and UK banks. Splunk, Jenkins, ALM."}
             ]},
            {"name": "Swapneel Chitragar", "title": "Senior Consultant - Pega Developer", "certs": "CSSA, CSA", "location": "Bengaluru",
             "linkedin": "https://www.linkedin.com/in/swapneel-chitragar-848a05137",
             "career": [
                {"company": "Mercedes-Benz R&D India", "role": "Senior Consultant", "dates": "Aug 2022 - Present (4yr)", "detail": "Pega development for automotive finance."},
                {"company": "Cognizant", "role": "Pega Developer", "dates": "Dec 2018 - Aug 2022 (3yr 8mo)", "detail": "SI to GCC career path."}
             ]},
            {"name": "D Dhana Raja Rao", "title": "Application Consultant - Pega Developer", "certs": "CSSA, CSA", "location": "Bengaluru",
             "linkedin": "https://www.linkedin.com/in/d-dhana-raja-rao-587a0a328",
             "career": [
                {"company": "Mercedes-Benz R&D India", "role": "Application Consultant", "dates": "Current", "detail": "Pega Developer. CSA & CSSA certified."}
             ]},
            {"name": "Vinay Meher Puvvada", "title": "IT Consultant - Pega Lead Developer", "certs": "CSSA", "location": "Germany (ex-MBRDI Bengaluru)",
             "linkedin": "https://www.linkedin.com/in/vinay-meher-puvvada-5207a657",
             "career": [
                {"company": "Mercedes-Benz AG", "role": "IT Consultant", "dates": "Current", "detail": "12+ years IT, 6+ years Pega. Case management, Integration, Data modelling, Performance tuning."},
                {"company": "Daimler Mobility AG", "role": "Assistant Manager - Lead Pega Developer", "dates": "Previous", "detail": "Financial services Pega architecture."},
                {"company": "Instellars (deployed to MBRDI)", "role": "Pega Developer", "dates": "Earlier"}
             ]},

            {"name": "Eshwar M H", "title": "DEPARTED Jul 2026 - AWS DevOps (via vendor)", "certs": "AWS", "location": "Bengaluru",
             "linkedin": "https://www.linkedin.com/in/eshwarmh",
             "career": [
                {"company": "Mercedes-Benz R&D India (via vendor)", "role": "AWS DevOps Engineer (LEFT Jul 2026)", "dates": "May 2025 - Jul 2026 (1yr 2mo)", "detail": "LEFT. Enterprise Pega on AWS. Reduced AWS spend 30%. Cut deploy time 2hrs to 25min. Mobility Maverick Award Mar 2026. Was contractor, not direct."}
             ]}
        ],
        "American Express": [
            {"name": "Deepak Chauhan", "title": "Senior Software Engineer II - 12+ yr Pega veteran", "certs": "CPBA, CSSA v7.1, CSA", "location": "Gurugram",
             "linkedin": "https://www.linkedin.com/in/deepak-chauhan-85663742",
             "career": [
                {"company": "American Express", "role": "Senior Software Engineer II", "dates": "Jul 2025 - Present", "detail": "Promoted. 12+ years Pega v5.x through Infinity 24.x."},
                {"company": "American Express", "role": "Senior Engineer", "dates": "Jul 2022 - Jul 2025 (3yr)"},
                {"company": "American Express", "role": "Engineer", "dates": "Feb 2016 - Jun 2022 (6yr 4mo)", "detail": "8+ years total at AmEx. Longest-tenured Pega dev."},
                {"company": "IBM", "role": "Pega Application Developer", "dates": "Earlier"}
             ]},
            {"name": "Himanshu Rajput", "title": "Software Engineer II - LSA-1, CSSA, CPDC, CPBA", "certs": "LSA Part 1, CSSA, CPDC, CPBA, CPSA", "location": "Gurugram",
             "linkedin": "https://www.linkedin.com/in/himanshu-rajput-7a4a83149",
             "career": [
                {"company": "American Express", "role": "Software Engineer II", "dates": "May 2024 - Present (2yr 2mo)", "detail": "LSA-1 + 4 other Pega certs. Highest-certified Pega dev at AmEx India."}
             ]},
            {"name": "Amit Singh Sachan", "title": "Software Engineer III - 10yr Pega exp", "certs": "CSSA v7.2", "location": "Gurugram",
             "linkedin": "https://www.linkedin.com/in/amit-singh-sachan-06ba2b226",
             "career": [
                {"company": "American Express", "role": "Software Engineer III", "dates": "Dec 2024 - Present", "detail": "10 years Pega in Banking/Financial domain."}
             ]},
            {"name": "Yashika Guleria", "title": "Business Logic Developer 1 - CSSA", "certs": "CSSA, CSA", "location": "Gurugram",
             "linkedin": "https://www.linkedin.com/in/yashikaguleria",
             "career": [
                {"company": "American Express", "role": "Business Logic Developer 1", "dates": "Sep 2024 - Present", "detail": "4yr Pega exp. Car rental, insurance, banking domains."}
             ]},
            {"name": "Ganesh Agarwal", "title": "Business Logic Developer - CSSA + Constellation", "certs": "CSSA v8.6", "location": "Gurugram",
             "linkedin": "https://www.linkedin.com/in/ganesh-agarwal-239130174",
             "career": [
                {"company": "American Express", "role": "Business Logic Developer", "dates": "Feb 2026 - Present (5mo)"},
                {"company": "_VOIS (Vodafone)", "role": "Pega CSSA Developer", "dates": "Nov 2023 - Feb 2026 (2yr 3mo)", "detail": "Pune. Vodafone to AmEx career path."}
             ]},
            {"name": "Prerna Chouhan", "title": "Business Logic Developer II - CSSA", "certs": "CSSA, CSA", "location": "Gurugram",
             "linkedin": "https://www.linkedin.com/in/prerna-chouhan",
             "career": [
                {"company": "American Express", "role": "Business Logic Developer II", "dates": "May 2026 - Present (3mo)", "detail": "Newest hire. Ex-TCS, Ex-Infosys."}
             ]},
            {"name": "Anuj Yadav", "title": "BLD 1 - ex-Intel Cloud App Engineer", "certs": "CSSA, CSA", "location": "Gurugram",
             "linkedin": "https://www.linkedin.com/in/anuj-yadav-3b8301203",
             "career": [
                {"company": "American Express", "role": "BLD 1", "dates": "May 2025 - Present", "detail": "Ex-Intel Cloud Application Engineer. Intel to AmEx career path."}
             ]}
        ],
        "Stellantis": [
            {"name": "Sudhir K Chavan", "title": "Pega COE Lead System Architect", "certs": "CSSA, CSA", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/sudhir-k-chavan-18443610",
             "career": [
                {"company": "Stellantis", "role": "Pega COE Lead System Architect", "dates": "Jul 2022 - Present (4yr 1mo)", "detail": "10+ years Pega exp. Heads the Pega CoE at Stellantis India."},
                {"company": "Pegasystems", "role": "Pega Global Support Engineer", "dates": "Previous", "detail": "Was at Pegasystems GCS before Stellantis."}
             ]},
            {"name": "Vijay Manubolu", "title": "Product Manager - 7yr Pega veteran", "certs": "CSSA", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/vijay-manubolu-78a49b142",
             "career": [
                {"company": "Stellantis Digital Hub", "role": "Product Manager", "dates": "Jul 2021 - Present (5yr 1mo)"},
                {"company": "Stellantis", "role": "Technical Lead", "dates": "Nov 2020 - Jun 2022 (1yr 7mo)", "detail": "Attended Pega Innovation Day 2026 Hyderabad."}
             ]},
            {"name": "Sathvik Anukuri", "title": "Software Engineer - Pega CSA & CSSA", "certs": "CSSA, CSA", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/sathvik-anukuri-208379186",
             "career": [
                {"company": "Stellantis", "role": "Software Engineer", "dates": "Jan 2025 - Present (1yr 7mo)", "detail": "Enterprise Pega app development, workflow automation, Agile."},
                {"company": "Stellantis", "role": "Associate Software Engineer", "dates": "Jul 2023 - Jan 2025 (1yr 6mo)"}
             ]},
            {"name": "Karthikeya Gedala", "title": "Software Engineer - Pega CSSA v8.7", "certs": "CSSA v8.7, CSA v8.7", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/karthikeya-gedala-b489691b4",
             "career": [
                {"company": "Stellantis", "role": "Software Engineer", "dates": "Jan 2025 - Present"},
                {"company": "Stellantis", "role": "Associate Software Engineer", "dates": "Jul 2023 - Jan 2025 (1yr 6mo)"}
             ]},
            {"name": "Mohammad Gouse Pasha", "title": "Pega Developer - 6+ yr exp", "certs": "CSA", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/mohammad-gouse-pasha-a57a8179",
             "career": [
                {"company": "Stellantis", "role": "Pega Developer", "dates": "Current", "detail": "6+ years IT. Case management, Flows, SLAs, UI, Data Transform."}
             ]}
        ],
        "Goldman Sachs": [
            {"name": "MAYANK VISHWAKARMA", "title": "Vice President - Pega CLSA", "certs": "CLSA, CSSA", "location": "Bengaluru",
             "linkedin": "https://www.linkedin.com/in/mayank-vishwakarma",
             "career": [
                {"company": "Goldman Sachs", "role": "Vice President", "dates": "Current", "detail": "Pega CLSA. Infinity, Constellation & DX API. Python automation."},
                {"company": "Pegasystems", "role": "Solutions Engineer", "dates": "Previous"}
             ]}
        ],
        "HSBC": [
            {"name": "Aditya Nath", "title": "Pega Lead Decisioning Architect - CLDA, ex-John Deere", "certs": "CLDA, CPDC, CPMC, CSA", "location": "Pune",
             "linkedin": "https://www.linkedin.com/in/aditya-nath-a2a51a45",
             "career": [
                {"company": "HSBC", "role": "Pega Lead Decisioning Architect", "dates": "Sep 2021 - Present (4yr 11mo)", "detail": "CLDA certified. CDH decisioning expert. GCP + BigQuery integration."},
                {"company": "John Deere India (JDTCI)", "role": "Lead Software Engineer III", "dates": "May 2020 - Sep 2021 (1yr 4mo)", "detail": "Pega at John Deere before HSBC."}
             ]},
            {"name": "Swapnil Ghatul", "title": "Sr. Consultant Specialist - 13yr Pega veteran", "certs": "CSSA, CSA", "location": "Pune",
             "linkedin": "https://www.linkedin.com/in/swapnil-ghatul-03360625",
             "career": [{"company": "HSBC", "role": "Sr. Consultant Specialist", "dates": "Jan 2023 - Present (3yr 7mo)", "detail": "13 years Pega exp. PRPC v5.4 through v7.1.8."}]},
            {"name": "Kayum Shaikh", "title": "Sr Consultant - Pega CDH Expert", "certs": "CSSA, CPDC", "location": "Pune",
             "linkedin": "https://www.linkedin.com/in/kayum-shaikh-862727b3",
             "career": [
                {"company": "HSBC", "role": "Senior Consultant", "dates": "Jan 2026 - Present (7mo)", "detail": "Pega CDH. REST API, Kafka, Data Flow, PDC integration. Chat bot, mobile, ATM, WhatsApp integrations."},
                {"company": "American Express", "role": "Sr. Developer", "dates": "May 2017 - Mar 2019 (1yr 10mo)", "detail": "AmEx to HSBC career path."}
             ]},
            {"name": "Venkatesh Dasari", "title": "Senior Consultant Specialist - CSSA", "certs": "CSSA, CSA", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/venkatesh-dasari",
             "career": [{"company": "HSBC", "role": "Senior Consultant Specialist", "dates": "Jun 2024 - Present (2yr 1mo)", "detail": "8+ years Pega. End-to-end development."}]},
            {"name": "Shravani Gannu", "title": "Senior Software Engineer - CSSA", "certs": "CSSA", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/shravanireddy",
             "career": [
                {"company": "HSBC", "role": "Senior Software Engineer", "dates": "Mar 2025 (promoted) - Present", "detail": "Promoted from SE. Hyderabad."},
                {"company": "HSBC", "role": "Software Engineer", "dates": "Nov 2022 - Mar 2025 (2yr 4mo)"}
             ]}
        ],
        "Bank of America": [
            {"name": "Ramakrishna Pasupuleti", "title": "Software Engineer II B - 7yr AML/KYC veteran", "certs": "CSSA", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/ramakrishna-pasupuleti-3a3988280",
             "career": [{"company": "Bank of America", "role": "Software Engineer II B", "dates": "Feb 2019 - Present (7yr 2mo)", "detail": "AML-KYC applications. Pega CLM. Enhanced risk management capabilities."}]},
            {"name": "Kavya Badam", "title": "Senior Software Engineer - CSSA, 7yr+", "certs": "CSSA", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/kavya-badam-7982766a",
             "career": [
                {"company": "Bank of America", "role": "Senior Software Engineer", "dates": "Sep 2018 - Present (7yr 11mo)", "detail": "Nearly 8 years at BofA. Longest-tenured Pega dev."},
                {"company": "Accenture India", "role": "Senior Software Engineer", "dates": "Jul 2014 - Sep 2018 (4yr)", "detail": "Accenture to BofA direct path."}
             ]},
            {"name": "Sabarna Ghosh", "title": "Software Engineer II A / AVP - CSSA", "certs": "CSSA", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/sabarna-ghosh-ba9536a8",
             "career": [{"company": "Bank of America", "role": "Software Engineer II A", "dates": "Aug 2022 - Present (3yr 11mo)", "detail": "5 years Pega exp. CSSA certified."}]},
            {"name": "Rashmi Gupta", "title": "Software Engineer I A - AML/KYC/CLM/Constellation", "certs": "CSSA v8.8, CSA v8.7", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/rashmigupta19",
             "career": [{"company": "Bank of America", "role": "Software Engineer I A", "dates": "Apr 2024 - Present (2yr 3mo)", "detail": "AML, KYC, CLM, Constellation. Newest generation Pega hire."}]},
            {"name": "Aliuddin Ahmed", "title": "Software Engineer I A - CLM KYC Expert", "certs": "CSSA", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/aliuddinahmed",
             "career": [{"company": "Bank of America", "role": "Software Engineer I A", "dates": "Nov 2025 - Present (9mo)", "detail": "3.6yr Pega + 2.4yr Pega CLM KYC framework specialist."}]},
            {"name": "Naveen Reddy", "title": "Software Engineer II A - CSSA", "certs": "CSSA v8.5, CSA v8", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/naveen-reddy-24013a109",
             "career": [{"company": "Bank of America", "role": "Software Engineer II A", "dates": "Oct 2025 - Present (10mo)", "detail": "7.4 years IT, 4+ years Pega."}]}
        ],
        "NatWest Group": [
            {"name": "Ramani Jeyachandrasekar", "title": "Director - Engineering Lead Pega CDH", "certs": "CSSA, Azure", "location": "India",
             "linkedin": "https://www.linkedin.com/in/ramani-jeyachandrasekar-2288817a",
             "career": [{"company": "NatWest Group", "role": "Director / Engineering Lead - Pega CDH", "dates": "Sep 2025 - Present (10mo)", "detail": "18+ years Pega & Java exp. CDH decisioning lead."}]},
            {"name": "Milan Patra", "title": "Software Engineer AVP - CLM KYC", "certs": "CSSA, CPDC, Pega Data Scientist", "location": "India",
             "linkedin": "https://www.linkedin.com/in/milan-patra-3709a855",
             "career": [
                {"company": "NatWest Group", "role": "Software Engineer AVP", "dates": "Current", "detail": "CLM KYC development."},
                {"company": "Coforge", "role": "Senior Technology Specialist (Pega)", "dates": "Previous"},
                {"company": "Capgemini", "role": "Senior Consultant - Pega", "dates": "Earlier"},
                {"company": "Cognizant", "role": "Senior Developer", "dates": "Earlier"}
             ]},
            {"name": "Nemi Nath", "title": "Software Engineer - 8+ yr CSSA, 1.5yr US onsite", "certs": "CSSA v7.2, CPDC v8.8", "location": "Chennai",
             "linkedin": "https://www.linkedin.com/in/nemi-nath",
             "career": [{"company": "NatWest Group", "role": "Software Engineer", "dates": "Jun 2021 - Present (5yr 2mo)", "detail": "8+ years Pega. Banking domain. 1.5yr US onsite. Splunk, App Dynamics."}]}
        ],
        "Lloyds Banking Group": [
            {"name": "Srinivas Yalagala", "title": "Pega CLSA - AIM Framework + Constellation Specialist", "certs": "CLSA, CPSD, CSSA, CSA", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/srinivas-yalagala-30a250328",
             "career": [{"company": "Lloyds Banking Group", "role": "Pega CLSA", "dates": "May 2025 - Present (1yr 3mo)", "detail": "Released Pega Constellation + AIM Framework at Lloyds Technology Centre."}]},
            {"name": "Rammohan Tattikota", "title": "Senior Technical Application Specialist - CLSA, ex-Pegasystems", "certs": "CLSA", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/rammohan-tattikota-b0087b1a1",
             "career": [
                {"company": "Lloyds Technology Centre India", "role": "Senior Technical Application Specialist", "dates": "Sep 2025 - Present (10mo)", "detail": "CLSA certified. Dev Lead."},
                {"company": "Pegasystems", "role": "Dev Lead", "dates": "Apr 2020 - Sep 2025 (5yr 5mo)", "detail": "5+ years at Pegasystems before Lloyds."}
             ]},
            {"name": "Shiva Kumar Asamchetti", "title": "Software Engineer - CSA + CSSA", "certs": "CSSA v8, CSA v7.1", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/shivakumar-asamchetti-15930668",
             "career": [{"company": "Lloyds Technology Centre India", "role": "Software Engineer", "dates": "Jun 2024 - Present (2yr 2mo)", "detail": "Smart BPM, Customer Service framework."}]},
            {"name": "Tejaswini Vinjamuri", "title": "Technical Application Specialist - CSSA, ex-Infosys", "certs": "CSSA, CSA", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/tejaswini-vinjamuri-62872a189",
             "career": [{"company": "Lloyds Technology Centre India", "role": "Technical Application Specialist", "dates": "Current", "detail": "4yr Pega. Customer Service framework. 90%+ compliance. Pega content creator on LinkedIn."}]},
            {"name": "Vamsi Krishna Sai Maddali", "title": "Technical Application Specialist - Fraud Lab", "certs": "CSSA", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/vamsikrishnasaimaddali",
             "career": [{"company": "Lloyds Technology Centre India", "role": "Technical Application Specialist", "dates": "Current", "detail": "5+ years Pega. Resolving Fraud Lab."}]}
        ],
        "Optum / UnitedHealth Group": [
            {"name": "Yugandhar Dasari", "title": "Software Engineering Lead - 6yr+ Pega veteran", "certs": "CSSA, CSA, AHM 250, ISTQB", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/yugandhar-dasari-0a2434a9",
             "career": [{"company": "UnitedHealth Group / Optum", "role": "Pega Senior Software Engineer", "dates": "Dec 2018 - Present (6yr 9mo)", "detail": "Longest-tenured Pega dev at Optum India."}]},
            {"name": "Pankaj Singh", "title": "Senior Software Engineer - CSSA + Decisioning", "certs": "CSSA, Decisioning Consultant", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/pankajsingh6",
             "career": [
                {"company": "Optum", "role": "Senior Software Engineer", "dates": "Jun 2022 - Present (4yr 2mo)"},
                {"company": "Optum", "role": "System Engineer (Pega)", "dates": "Aug 2019 - Jun 2022 (2yr 10mo)"},
                {"company": "TCS", "role": "Pega Developer", "dates": "Aug 2017 - Jul 2019 (2yr)", "detail": "TCS to Optum career path."}
             ]},
            {"name": "Sai Prassanna Byreddy", "title": "Senior Software Engineer - CSSA", "certs": "CSSA", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/sai-prassanna-byreddy-a9a2a8320",
             "career": [{"company": "Optum", "role": "Senior Software Engineer", "dates": "Jul 2022 - Present (4yr)", "detail": "Case management, workflow design, integrations."}]},
            {"name": "NagaBhargavi Valavala", "title": "Software Engineer - 8yr+ CSSA + CPDC", "certs": "CSSA, CCSA, CPDC", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/nagabhargavi-valavala-b33788146",
             "career": [{"company": "Optum Global Solutions", "role": "Software Engineer", "dates": "Feb 2018 - Present (8yr 6mo)", "detail": "8+ year veteran. One of the longest-tenured at Optum."}]},
            {"name": "Manoj Kumar Undralla", "title": "Senior Software Engineer - Constellation + GenAI", "certs": "CSSA", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/manoj-kumar-undralla",
             "career": [{"company": "Optum India", "role": "Senior Software Engineer", "dates": "Jul 2026 - Present (1mo)", "detail": "Newest hire. Pega Constellation + GenAI-driven automation."}]}
        ],
        "Vodafone / VOIS": [
            {"name": "Ganesh Mahagaonkar", "title": "Senior Manager - CLSA, 12yr Pega", "certs": "CLSA v8.6, CPDC, CSSA, CSA", "location": "Bengaluru",
             "linkedin": "https://www.linkedin.com/in/ganesh-mahagaonkar-4aba225b",
             "career": [
                {"company": "_VOIS", "role": "Senior Manager", "dates": "Aug 2025 - Present (1yr)", "detail": "12+ years Pega. CLSA. 1yr US + 4yr UK onsite."},
                {"company": "Mphasis", "role": "Software Development Engineer", "dates": "Previous"}
             ]},
            {"name": "Shobhit Goyal", "title": "Senior Manager - Pega LSA + Constellation", "certs": "CLSA Part 1, CSSA", "location": "Bengaluru",
             "linkedin": "https://www.linkedin.com/in/shobhit-goyal-40218623",
             "career": [{"company": "Vodafone", "role": "Senior Manager", "dates": "Aug 2022 - Present (3yr 11mo)", "detail": "CLSA Part 1 (Mar 2025). Pega 6x through Infinity 25."}]},
            {"name": "Anshul Sharma", "title": "Manager - CLSA-1, React, AWS, DevOps", "certs": "CLSA Part 1, CSSA", "location": "Pune",
             "linkedin": "https://www.linkedin.com/in/anshul-sharma-8474b339",
             "career": [
                {"company": "_VOIS", "role": "Manager", "dates": "Sep 2022 - Present (3yr 11mo)"},
                {"company": "Capgemini", "role": "Pega Senior System Architect (CSSA)", "dates": "Previous"},
                {"company": "TCS", "role": "System Engineer / Pega Developer", "dates": "Dec 2014 - Dec 2017 (3yr)"}
             ]},
            {"name": "Anil Das", "title": "Manager - CLSA-1, CDH Decisioning, AWS", "certs": "CLSA Part 1, CPDC, CSSA, SAFe 6", "location": "Bengaluru",
             "linkedin": "https://www.linkedin.com/in/anil-das-ba2915160",
             "career": [{"company": "_VOIS", "role": "Manager", "dates": "Apr 2023 - Present (3yr 4mo)", "detail": "Vodafone Business Germany client. Pega + Jira + ADO integration. Star Award winner."}]},
            {"name": "Koteswararao Kasthuri", "title": "Manager - Pega Technology, CSSA", "certs": "CSSA", "location": "Bengaluru",
             "linkedin": "https://www.linkedin.com/in/kkoteswar",
             "career": [{"company": "_VOIS", "role": "Manager - Pega Technology", "dates": "Feb 2023 - Present (3yr 6mo)", "detail": "8+ years Pega. Vodafone Stars Award winner."}]}
        ],
        "Cisco India": [
            {"name": "Sahitya Srinivasan", "title": "Software Engineer - CSSA", "certs": "CSSA v7.4, CSA v7.2", "location": "Bengaluru",
             "linkedin": "https://www.linkedin.com/in/sahitya-srinivasan-045346114",
             "career": [{"company": "Cisco", "role": "Software Engineer", "dates": "Current", "detail": "Pega Application Developer. Jira Fundamentals certified."}]},
            {"name": "Mounika Reddy", "title": "Senior Pega Developer / Architect - CSSA", "certs": "CSSA, CSA", "location": "Hyderabad",
             "linkedin": "https://www.linkedin.com/in/mounika-reddy-9a907b26b",
             "career": [{"company": "Cisco", "role": "Senior Pega Developer PRPC System Architect", "dates": "Current", "detail": "Pega Architect level. CPM framework."}]},
            {"name": "Vijaykumar Perugu", "title": "Pega Developer", "certs": "", "location": "Bengaluru",
             "linkedin": "https://www.linkedin.com/in/vijaykumar-perugu-4b6226280",
             "career": [{"company": "Cisco", "role": "Pega Developer", "dates": "Current"}]},
            {"name": "Pooja Maadishetty", "title": "Pega Developer", "certs": "", "location": "India",
             "linkedin": "https://www.linkedin.com/in/pooja-maadishetty-466548121",
             "career": [{"company": "Cisco", "role": "Pega Developer", "dates": "Current"}]}
        ],
        "John Deere India (JDTCI)": [
            {"name": "Rahul Chaher", "title": "AGM Software Engineering - CLSA, 12.5yr Pega", "certs": "CLSA, CSSA, CSA", "location": "Pune",
             "linkedin": "https://www.linkedin.com/in/rahul-chaher-a31b8575",
             "career": [{"company": "John Deere", "role": "Assistant General Manager - Software Engineering", "dates": "Current", "detail": "CLSA. 12.5yr Pega. Collections Framework, Customer Service for FS, CDH, AWS Cloud Migration. Constellation + GenAI expert."}]},
            {"name": "Abhiraj Gupta", "title": "Pega Developer - US Collections, Customer Service for FS", "certs": "CSSA", "location": "Bengaluru",
             "linkedin": "https://www.linkedin.com/in/guptaabhiraj4",
             "career": [
                {"company": "John Deere", "role": "Pega Developer", "dates": "Current", "detail": "US Collections team. Customer Service for Finance using Collections bundle."},
                {"company": "Commonwealth Bank", "role": "Pega Developer", "dates": "Jul 2019 - Sep 2021 (2yr 2mo)", "detail": "Built applications from scratch on Pega 7.4."}
             ]},
            {"name": "Shailendra Mishra", "title": "Lead Software Engineer - Full Stack + GenAI", "certs": "CSSA", "location": "Bengaluru",
             "linkedin": "https://www.linkedin.com/in/shailendra-mishra-3585001b",
             "career": [{"company": "John Deere", "role": "Lead Software Engineer", "dates": "Nov 2021 - Present (4yr 9mo)", "detail": "Full Stack + GenAI + Pega + AWS."}]},
            {"name": "Manan Awasthi", "title": "Senior Lead Software Engineer - CSSA", "certs": "CSSA, CSA", "location": "Pune",
             "linkedin": "https://www.linkedin.com/in/manan-awasthi",
             "career": [
                {"company": "John Deere India (JDTCI)", "role": "Senior Lead Software Engineer", "dates": "Oct 2022 - Present (3yr 10mo)"},
                {"company": "John Deere India (JDTCI)", "role": "Lead Software Engineer", "dates": "Sep 2020 - Sep 2022 (2yr)"}
             ]},
            {"name": "Sarvesh Kumar", "title": "DEPARTED Apr 2026 - ex-Lead SE II, Collections", "certs": "CSSA, CSA, CPDC", "location": "Pune",
             "linkedin": "https://www.linkedin.com/in/sarvesh-kumar-b57671124",
             "career": [
                {"company": "John Deere", "role": "Lead Software Engineer II (LEFT Apr 2026)", "dates": "Sep 2022 - Apr 2026 (3yr 7mo)", "detail": "LEFT. Collection Application for delinquency management. CS for FS Framework."}
             ]}
        ],
        "Deutsche Bank": [
            {"name": "Deepika Tiwari", "title": "Associate - Pega CSA, ex-Pegasystems", "certs": "CSA, GCP Engineer", "location": "Pune",
             "linkedin": "https://www.linkedin.com/in/deepika-tiwari-abb1a5127",
             "career": [
                {"company": "Deutsche Bank", "role": "Associate", "dates": "Oct 2023 - Present (2yr 5mo)", "detail": "Pega + Google Cloud Platform certified."},
                {"company": "Pegasystems", "role": "Application Quality Engineer - Financial Services", "dates": "Previous", "detail": "Was at Pegasystems before Deutsche Bank."}
             ]},
            {"name": "Dhanasekar P", "title": "Assistant Vice President - 18+ yr IT veteran", "certs": "", "location": "Pune",
             "linkedin": "https://www.linkedin.com/in/dhanasekarp",
             "career": [
                {"company": "Deutsche Bank", "role": "Assistant Vice President", "dates": "May 2017 - Present (9yr 3mo)", "detail": "18+ years IT. Production Support Manager, SRE, DevOps for GTB Trade Finance. Managed 24x7 support team of 18. 80+ weekly changes to Production."}
             ]}
        ]
    }
    
    # ── Additional Bangalore-focused members (from 2025-2026 research) ──
    BLR_EXTRA = {
        "HSBC": [
            {"name": "Deepak Lama", "title": "Assistant Director - Pega LDA / CDH Decisioning", "certs": "Pega Certified Decisioning Consultant",
             "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/dpklama",
             "_role_level": 1, "_role_label": "Management",
             "career": [
                {"company": "HSBC", "role": "Assistant Director - Pega Decisioning Architect", "dates": "Mar 2023 - Present (3yr+)", "detail": "Pega CDH decisioning architect in Bangalore. Ex-Pegasystems."},
                {"company": "Pegasystems", "role": "Senior Software Engineer", "dates": "Prior", "detail": "Came from Pega directly — deep platform knowledge."}
             ]},
            {"name": "Prashanth Shankar", "title": "Technical Manager - Decisioning Specialist", "certs": "Pega Certified Decisioning Consultant",
             "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/prashanth-shankar-8970b0145",
             "_role_level": 2, "_role_label": "Architect",
             "career": [
                {"company": "HSBC", "role": "Decisioning Consultant Specialist / Technical Manager", "dates": "Present", "detail": "CDH/NBA specialist in Bangalore. Ex-Pegasystems employee."},
                {"company": "Pegasystems", "role": "Senior Software Engineer", "dates": "Prior", "detail": "Former Pegasystems engineer — knows the platform inside out."}
             ]},
        ],
        "Deutsche Bank": [
            {"name": "Krishna Kumar", "title": "AVP - Pega Architect (ex-Pegasystems 4yr)", "certs": "CSSA",
             "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/krishna-kumar-6226b358",
             "_role_level": 1, "_role_label": "Management",
             "career": [
                {"company": "Deutsche Bank", "role": "Assistant Vice President", "dates": "Jun 2023 - Present (3yr+)", "detail": "Pega Architect in Bengaluru GCC."},
                {"company": "Pegasystems", "role": "Senior Software Engineer", "dates": "Jan 2017 - Jan 2021 (4yr)", "detail": "4 years at Pegasystems Hyderabad — deep platform expertise."}
             ]},
        ],
        "Standard Chartered": [
            {"name": "Deepak Rudraiah", "title": "Development Head - PEGA Platform, Cyber (9yr+ at SCB)", "certs": "",
             "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/deepak-rudraiah-275274217",
             "_role_level": 1, "_role_label": "Management",
             "career": [
                {"company": "Standard Chartered", "role": "Development Head - PEGA Platform, Cyber", "dates": "Apr 2017 - Present (9yr+)", "detail": "Set up the Pega Workflow team in Bengaluru from ground up. Talent scouting, hiring & training. Delivered 8+ workflows to production. KEY HIRING MANAGER."}
             ]},
            {"name": "Vishal Srivastava", "title": "Chapter Lead - Digital Onboarding (22yr exp)", "certs": "CLSA",
             "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/vishal-srivastava-57902311",
             "_role_level": 1, "_role_label": "Management",
             "career": [
                {"company": "Standard Chartered", "role": "Chapter Lead - Digital Onboarding", "dates": "Dec 2024 - Present", "detail": "Leads large team of Pega, Java and UI/UX professionals. Enterprise onboarding platform across multiple markets."},
                {"company": "Standard Chartered", "role": "AVP, Lead System Architect", "dates": "Dec 2021 - Dec 2024 (3yr)", "detail": "Led digital onboarding program in Bengaluru. Built world-class client onboarding for international markets."},
                {"company": "Virtusa", "role": "Associate Director", "dates": "Jun 2017 - Dec 2021 (4yr+)", "detail": "Pega solution architecture for multiple clients from Bengaluru."}
             ]},
            {"name": "Abhishek Saurabh", "title": "Pega Lead System Architect - COE & Architecture", "certs": "CLSA, CSSA, CSA",
             "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/abhishek-saurabh-12299232",
             "_role_level": 2, "_role_label": "Architect",
             "career": [
                {"company": "Standard Chartered", "role": "Pega Lead System Architect", "dates": "Present", "detail": "Architecture, design, enterprise Pega COE. Smart Disputes, CSM frameworks expertise."}
             ]},
            {"name": "Swathi Vaddi", "title": "Lead Decisioning Architect - CDH Specialist", "certs": "CPDC, Pega Data Scientist, CSA",
             "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/swathi-vaddi",
             "_role_level": 2, "_role_label": "Architect",
             "career": [
                {"company": "Standard Chartered", "role": "Lead Decisioning Architect", "dates": "Jun 2025 - Present", "detail": "CDH/Decisioning specialist. 13yr Pega experience. Recent hire from CBA."},
                {"company": "Commonwealth Bank", "role": "Pega Lead Decisioning Developer", "dates": "Jun 2022 - Jun 2025 (3yr)", "detail": "CDH Decisioning work for CBA from Bengaluru."}
             ]},
        ],
        "Verizon": [
            {"name": "Smruti Rekha Swain", "title": "Pega Tech Lead - Team Manager (10+ devs)", "certs": "CSSA, CSA",
             "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/smrutirswain",
             "_role_level": 3, "_role_label": "Lead",
             "career": [
                {"company": "Verizon", "role": "Pega Tech Lead", "dates": "May 2020 - Present (6yr+)", "detail": "Manages 10+ developer team. End-to-end delivery, product prioritization. KEY BANGALORE CONTACT."}
             ]},
            {"name": "Swagat Patnaik", "title": "Pega Architect - CLSA Certified (6yr+ at Verizon)", "certs": "CLSA v7.19",
             "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/swagatpatnaik",
             "_role_level": 2, "_role_label": "Architect",
             "career": [
                {"company": "Verizon", "role": "Pega Architect", "dates": "Mar 2020 - Present (6yr+)", "detail": "CLSA-certified architect in Bengaluru. Solution design and technical leadership."}
             ]},
            {"name": "Shakti Thakur", "title": "Principal Engineer - CLSA, CSSA, CPDC", "certs": "CLSA, CSSA, CSA, CPDC",
             "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/shaktisaurav",
             "_role_level": 2, "_role_label": "Architect",
             "career": [
                {"company": "Verizon", "role": "Principal Engineer", "dates": "Jan 2022 - Present (4yr+)", "detail": "Senior technical role. CPM, Smart Dispute expertise. Multi-certified."}
             ]},
        ],
        "Pegasystems": [
            {"name": "Aditya Banerjee", "title": "Senior Manager - Pega Process AI, NLP & GenAI", "certs": "",
             "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/aditya-banerjee-b830481b4",
             "_role_level": 1, "_role_label": "Management",
             "career": [
                {"company": "Pegasystems", "role": "Senior Manager - Process AI, NLP & GenAI", "dates": "Apr 2025 - Present", "detail": "Leads Pega Process AI and GenAI team in Bengaluru. KEY HIRING MANAGER."},
                {"company": "Pegasystems", "role": "Manager", "dates": "Apr 2022 - Apr 2025 (3yr)", "detail": "Engineering management in Bengaluru."},
                {"company": "Pegasystems", "role": "Technical Lead", "dates": "Feb 2020 - May 2022 (2yr)", "detail": "Started as Tech Lead, promoted to management track."}
             ]},
            {"name": "Sambit Sahu", "title": "Senior Engineering Manager - Product Engineering", "certs": "CSA, CSSA, CSM, CSPO",
             "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/sambit06",
             "_role_level": 1, "_role_label": "Management",
             "career": [
                {"company": "Pegasystems", "role": "Senior Engineering Manager", "dates": "Apr 2025 - Present", "detail": "Builds and leads multiple high-performing teams. KEY HIRING MANAGER."},
                {"company": "Pegasystems", "role": "Engineering Manager", "dates": "Apr 2022 - Aug 2025 (3yr+)", "detail": "Product engineering management in Bengaluru."},
                {"company": "Pegasystems", "role": "Technical Lead", "dates": "Mar 2017 - Mar 2022 (5yr)", "detail": "5 years as Tech Lead in Bangalore."}
             ]},
            {"name": "Satyajit Acharjya", "title": "Senior Engineering Manager - Product Development", "certs": "",
             "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/satyajit-acharjya-4785424b",
             "_role_level": 1, "_role_label": "Management",
             "career": [
                {"company": "Pegasystems", "role": "Senior Engineering Manager", "dates": "Oct 2025 - Present", "detail": "Manages Pega product development teams in Bengaluru."},
                {"company": "Pegasystems", "role": "Software Engineering Manager", "dates": "May 2023 - Oct 2025 (2yr+)", "detail": "Engineering management."}
             ]},
            {"name": "Satya Kiranmayee V", "title": "Senior Consulting Manager - Technical Solutions & Design (CLSA)", "certs": "CLSA",
             "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/satya-kiranmayee-vajapeyajula-932b7910",
             "_role_level": 1, "_role_label": "Management",
             "career": [
                {"company": "Pegasystems", "role": "Senior Consulting Manager - Technical Design & Solutions", "dates": "Apr 2025 - Present", "detail": "Leads consulting/advisory practice in Bengaluru. CLSA certified."},
                {"company": "Pegasystems", "role": "Senior Manager - Consulting", "dates": "Jul 2022 - Apr 2025", "detail": "Technical solutions design."},
                {"company": "Pegasystems", "role": "Lead System Architect", "dates": "Jun 2021 - Jul 2022", "detail": "Technical solutions from Bangalore."}
             ]},
        ],
        "American Express": [
            {"name": "Rajesh Kuppusamy", "title": "Application Architect - 15yr+ at AmEx", "certs": "",
             "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/rajesh-kuppusamy-20b4291a",
             "_role_level": 2, "_role_label": "Architect",
             "career": [
                {"company": "American Express", "role": "Application Architect", "dates": "Jan 2011 - Present (15yr+)", "detail": "15+ year veteran at AmEx Bengaluru. Deep institutional knowledge. One of the longest-serving Pega architects."},
                {"company": "American Express", "role": "Technical Lead", "dates": "Jan 2005 - Jan 2011 (6yr)", "detail": "Started as Tech Lead, grew to Architect over 20+ years at AmEx."}
             ]},
            {"name": "Nitin Dhanopiya", "title": "Senior Software Engineer I (recently promoted)", "certs": "CSSA, CSA",
             "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/nitin-dhanopiya-664a30144",
             "_role_level": 4, "_role_label": "Senior",
             "career": [
                {"company": "American Express", "role": "Senior Software Engineer I (Engineer III)", "dates": "Jul 2024 - Present", "detail": "Recently promoted Jul 2026. Active Pega specialist."},
                {"company": "American Express", "role": "Engineer II", "dates": "Dec 2021 - Jun 2024 (2yr+)", "detail": "Pega development in Bengaluru."}
             ]},
        ],
        "Bank of America": [
            {"name": "Venkata Neelima Mullangi", "title": "Vice President - Pega LSA, Managing 20+ direct reports", "certs": "LSA, CLSA",
             "location": "Hyderabad", "linkedin": "https://www.linkedin.com/in/neelima1410",
             "_role_level": 1, "_role_label": "Management",
             "career": [
                {"company": "Bank of America", "role": "Vice President - Pega Architecture & Talent", "dates": "Jan 2026 - Present", "detail": "LSA specializing in AML/KYC. Manages 20+ direct reports. Handles vendor management (50+ members). Spearheads talent acquisition and team expansion. KEY HIRING DECISION MAKER."}
             ]},
        ],
    }
    for comp_name, members in BLR_EXTRA.items():
        for company in data.get("companies", []):
            if company.get("name", "") == comp_name:
                existing_names = {m.get("name", "").lower().strip() for m in company.get("team_members", [])}
                for extra in members:
                    if extra["name"].lower().strip() not in existing_names:
                        company["team_members"].append(extra)
                break

    # Merge extra members into existing companies
    for company in data.get("companies", []):
        name = company.get("name", "")
        if name in EXTRA_MEMBERS:
            existing_names = {m.get("name", "").lower().strip() for m in company.get("team_members", [])}
            for extra in EXTRA_MEMBERS[name]:
                if extra["name"].lower().strip() not in existing_names:
                    company["team_members"].append(extra)

def _determine_project_phase(company):
    """Determine project lifecycle phase from company attributes"""
    projects = company.get("projects", "").lower()
    maturity = company.get("maturity", "").lower()
    hiring = company.get("hiring_status", "").lower()

    if any(w in projects for w in ["migrat", "upgrade", "moderniz", "prpc to"]):
        return "Migration & Modernization"
    if "very high" in maturity:
        if any(w in hiring for w in ["rapid", "active"]):
            return "Existing & Rapidly Expanding"
        if "grow" in hiring:
            return "Existing & Expanding"
        return "Existing & Mature"
    if "high" in maturity:
        if any(w in hiring for w in ["rapid", "active"]):
            return "Existing & Expanding"
        if "grow" in hiring:
            return "Existing & Growing"
        return "Existing & Stable"
    if "medium" in maturity:
        if "grow" in hiring:
            return "Growing Implementation"
        return "Early / Emerging"
    return "Emerging"


def _determine_difficulty(company):
    sector = company.get("sector", "").lower()
    maturity = company.get("maturity", "").lower()
    hiring = company.get("hiring_status", "").lower()
    name = company.get("name", "")

    elite = ["Goldman Sachs", "Morgan Stanley", "UBS", "Pegasystems"]
    if name in elite:
        return "Very Hard"
    top_banks = ["JPMorgan Chase", "Bank of America", "Deutsche Bank", "Barclays"]
    if name in top_banks and "stable" in hiring:
        return "Hard"
    if any(w in hiring for w in ["rapid", "active"]):
        return "Medium"
    if "grow" in hiring:
        return "Medium"
    if "stable" in hiring and "very high" in maturity:
        return "Hard"
    if "declin" in hiring:
        return "Hard"
    return "Medium"


def _determine_salary(company):
    name = company.get("name", "")
    sector = company.get("sector", "").lower()

    tier1 = ["Goldman Sachs", "Morgan Stanley", "UBS", "Pegasystems", "Deutsche Bank"]
    tier2 = ["JPMorgan Chase", "Wells Fargo", "HSBC", "Citibank", "Bank of America",
             "Barclays", "Standard Chartered", "American Express", "BNP Paribas",
             "NatWest Group", "Lloyds Banking Group", "ANZ Bank", "Commonwealth Bank"]
    tier3 = ["Optum / UnitedHealth Group", "Verizon", "Mercedes-Benz R&D India",
             "Ford Motor Company", "Mastercard", "Visa", "PayPal", "S&P Global India",
             "Roche India", "Novartis India", "Nike India"]

    if name in tier1:
        return "30-45+ LPA"
    if name in tier2:
        return "22-35 LPA"
    if name in tier3:
        return "20-30 LPA"
    if "bank" in sector or "financial" in sector:
        return "18-28 LPA"
    if "insurance" in sector or "health" in sector:
        return "16-25 LPA"
    if "telecom" in sector:
        return "16-24 LPA"
    if "auto" in sector or "manufactur" in sector:
        return "16-24 LPA"
    return "15-22 LPA"


def _build_skills(company):
    """Build prioritised skill list from company data"""
    tech = company.get("tech_stack", [])
    domains = company.get("domains", [])
    projects = company.get("projects", "").lower()

    skip = {"Agile/Scrum", "Java", "Oracle", "SOAP/REST", "REST/SOAP", "J2EE",
            "Java/J2EE", "SOAP", "REST", "PL/SQL", "SQL", "CI/CD"}
    skills = [t for t in tech if t not in skip]

    for d in domains:
        skills.append(f"{d} domain")

    # Add context-aware extras
    if "constellation" in projects or any("constellation" in t.lower() for t in tech):
        if "Constellation UI patterns" not in skills:
            skills.append("Constellation UI patterns")
    if "cdh" in projects or any("cdh" in t.lower() for t in tech):
        if "CDH / Next-Best-Action" not in skills:
            skills.append("CDH / Next-Best-Action")
    if "kafka" in projects or any("kafka" in t.lower() for t in tech):
        if "Kafka event streaming" not in skills:
            skills.append("Kafka event streaming")
    if "genai" in projects or any("genai" in t.lower() for t in tech):
        if "Pega GenAI / Agentic AI" not in skills:
            skills.append("Pega GenAI / Agentic AI")
    if "migrat" in projects or "upgrade" in projects:
        if "Version upgrade strategies" not in skills:
            skills.append("Version upgrade strategies")

    return skills[:10]


def _build_approach(company):
    """Build ranked approach strategies"""
    members = company.get("team_members", [])
    hiring = company.get("hiring_status", "").lower()
    name = company.get("name", "")

    # Find managers / leads
    managers = [m for m in members if m.get("_role_level", 9) <= 2 and m.get("linkedin")]
    leads = [m for m in members if m.get("_role_level", 9) == 3 and m.get("linkedin")]
    any_linked = [m for m in members if m.get("linkedin")]

    approaches = []

    # LinkedIn connect with team members
    if managers:
        mgr = managers[0]
        approaches.append({
            "method": "LinkedIn — Connect with Hiring Manager",
            "effectiveness": "BEST",
            "tip": f"Connect with {mgr['name']} ({mgr.get('title','')}) on LinkedIn. Send a personalised note mentioning their specific Pega projects."
        })
    elif leads:
        ld = leads[0]
        approaches.append({
            "method": "LinkedIn — Connect with Team Lead",
            "effectiveness": "HIGH",
            "tip": f"Connect with {ld['name']} ({ld.get('title','')}) and mention your relevant Pega experience."
        })
    elif any_linked:
        person = any_linked[0]
        approaches.append({
            "method": "LinkedIn — Connect with Team Member",
            "effectiveness": "HIGH",
            "tip": f"Connect with {person['name']} for referral. Even peer-level connections convert well."
        })

    # Career portal
    approaches.append({
        "method": "Career Portal — Direct Application",
        "effectiveness": "HIGH" if "active" in hiring or "rapid" in hiring else "MEDIUM",
        "tip": f"Apply directly at {name}'s career site with Pega-keyword-optimised resume. Most GCC hiring funnels route through the portal."
    })

    # Employee referral
    if len(members) > 3:
        approaches.append({
            "method": "Employee Referral",
            "effectiveness": "BEST",
            "tip": "Referrals have 5-10x higher conversion than cold applies. Reach out to any team member on LinkedIn for a referral — most companies pay referral bonuses so they're motivated to help."
        })
    else:
        approaches.append({
            "method": "Employee Referral",
            "effectiveness": "HIGH",
            "tip": "Find current employees on LinkedIn (search: Pega + company name). Ask for a referral — it fast-tracks your application."
        })

    # LinkedIn InMail
    approaches.append({
        "method": "LinkedIn InMail to Recruiters",
        "effectiveness": "MEDIUM",
        "tip": f"Search for '{name} talent acquisition' or '{name} recruiter technology' on LinkedIn. InMail gets noticed more than regular messages."
    })

    # Naukri/Indeed
    if "active" in hiring or "rapid" in hiring or "grow" in hiring:
        approaches.append({
            "method": "Job Portals (Naukri / LinkedIn Jobs)",
            "effectiveness": "MEDIUM",
            "tip": "Set alerts for Pega roles at this company. Apply within 24 hours of posting — early applicants get 3x more callbacks."
        })

    # Pega community
    approaches.append({
        "method": "Pega Community / Events",
        "effectiveness": "MEDIUM",
        "tip": "Attend PegaWorld / PegaInnovate events. Many hiring managers attend. Build visibility by posting Pega content on LinkedIn."
    })

    return approaches


def _build_pitch(company):
    """Build interview pitch points"""
    projects = company.get("projects", "")
    tech = company.get("tech_stack", [])
    domains = company.get("domains", [])
    maturity = company.get("maturity", "")
    hiring = company.get("hiring_status", "")
    proj_lower = projects.lower()

    pitch = []

    # Domain-specific pitches
    if any("kyc" in d.lower() for d in domains):
        pitch.append("Highlight any KYC/onboarding or compliance automation experience — this is their core Pega use-case.")
    if any("payment" in d.lower() for d in domains):
        pitch.append("Emphasise payments processing or financial transaction workflow experience.")
    if any("cdh" in d.lower() or "decision" in d.lower() for d in domains):
        pitch.append("Talk about CDH, Next-Best-Action, or any decisioning/marketing automation experience.")
    if any("case" in d.lower() or "service" in d.lower() for d in domains):
        pitch.append("Showcase your case management and customer service automation expertise — it maps directly to their implementation.")
    if any("claim" in d.lower() or "underwriting" in d.lower() for d in domains):
        pitch.append("Mention any insurance claims processing or underwriting workflow experience.")

    # Tech-specific pitches
    if any("constellation" in t.lower() for t in tech):
        pitch.append("Mention Constellation UI / DX API experience — they're actively adopting it and it's a rare skill.")
    if any("kafka" in t.lower() for t in tech):
        pitch.append("Highlight Kafka / event-driven architecture experience — shows you can handle their integration patterns.")
    if any("cloud" in t.lower() or "aws" in t.lower() or "gcp" in t.lower() or "azure" in t.lower() for t in tech):
        pitch.append("Discuss cloud deployment experience (Pega Cloud / containerised Pega) — they value cloud-native skills.")
    if any("genai" in t.lower() for t in tech):
        pitch.append("Talk about Pega GenAI features or any AI/ML integration work — this is cutting-edge and they're investing heavily.")

    # Maturity-specific
    if "migrat" in proj_lower or "upgrade" in proj_lower:
        pitch.append("Share your version upgrade/migration experience (PRPC to Infinity, Classic to Cosmos). This is exactly what they need.")
    if "grow" in hiring.lower() or "active" in hiring.lower():
        pitch.append("Emphasise your ability to ramp up quickly and deliver in fast-growing teams. They're scaling and need people who can hit the ground running.")
    if "stable" in hiring.lower():
        pitch.append("Show deep technical depth and ownership mindset — stable teams value senior contributors who can take full ownership of modules.")

    # Universal strong points
    pitch.append("Lead with your CSSA certification — it's a hard requirement. If you're pursuing CLSA, mention your progress.")
    pitch.append("Prepare a short 'Pega architecture walkthrough' of a project you built end-to-end — interviewers love concrete examples.")

    return pitch[:6]


def _build_insider_tip(company):
    """Generate company-specific insider tip"""
    name = company.get("name", "")
    members = company.get("team_members", [])
    hiring = company.get("hiring_status", "").lower()
    highlights = company.get("highlights", [])
    projects = company.get("projects", "").lower()

    # Check for recent hires — means the door is open
    recent = [m for m in members if m.get("career") and
              any("present" in (s.get("dates", "").lower()) and
                  any(y in s.get("dates", "") for y in ["2025", "2026"])
                  for s in m.get("career", [])[:1])]

    # Check for departures — open positions
    departed = [m for m in members if m.get("_role_level") == 9 or
                "depart" in m.get("title", "").lower() or
                "left" in m.get("title", "").lower()]

    if departed:
        return f"Someone recently departed from the Pega team — this likely means there's a backfill position open. Apply NOW, these slots fill fast."
    if recent and len(recent) >= 2:
        return f"Multiple recent hires ({len(recent)} people joined in 2025-2026) — the team is actively growing and the hiring pipeline is warm. Your chances are higher than usual."
    if "active" in hiring or "rapid" in hiring:
        return "The team is in active growth mode. This is the BEST time to apply — hiring managers have approved headcount and are under pressure to fill roles quickly."
    if "genai" in projects or "ai" in projects:
        return "They're investing in Pega GenAI/AI capabilities. If you can demo even basic GenAI Pega features, you'll stand out from 90% of candidates."
    if "constellation" in projects:
        return "Constellation UI adoption is underway — candidates with hands-on Constellation experience are extremely rare and get fast-tracked."
    if any("clsa" in h.lower() or "lsa" in h.lower() for h in highlights):
        return "Multiple CLSA/LSA-certified architects on the team. If you're pursuing CLSA, mention it — they value the cert path and may sponsor your preparation."
    if "stable" in hiring:
        return "Team is stable, so openings are rare. Set up LinkedIn alerts and be ready to apply within 24 hours when a role appears. Timing is everything."
    return "Research the company's specific Pega use-cases before your interview. Candidates who mention concrete project details get dramatically better outcomes."


def _build_business_reality(company):
    """Build a plain-English description of what the company actually does with Pega"""
    name = company.get("name", "")
    projects = company.get("projects", "")
    maturity = company.get("maturity", "")
    team_size = company.get("team_size", "")
    hiring = company.get("hiring_status", "")
    domains = company.get("domains", [])

    if not projects:
        return f"{name} has a Pega practice in their India GCC operations. Specific project details are not publicly available yet."

    maturity_context = ""
    if "very high" in maturity.lower():
        maturity_context = f"This is a well-established, mature Pega implementation with ~{team_size} developers. The codebase has established patterns and frameworks."
    elif "high" in maturity.lower():
        maturity_context = f"This is a solid, proven Pega implementation (~{team_size} devs). Expect a mix of maintaining existing systems and building new features."
    elif "medium" in maturity.lower():
        maturity_context = f"Their Pega practice is relatively newer (~{team_size} devs). You'll likely get more greenfield development opportunities."
    else:
        maturity_context = f"Pega footprint is emerging at this company (~{team_size} devs)."

    hiring_context = ""
    if "active" in hiring.lower() or "rapid" in hiring.lower():
        hiring_context = "They're actively expanding the team — high demand for Pega talent right now."
    elif "grow" in hiring.lower():
        hiring_context = "The team is steadily growing with new hiring."
    elif "stable" in hiring.lower():
        hiring_context = "Team is stable — positions open mainly for backfills."
    elif "declin" in hiring.lower():
        hiring_context = "Be cautious — the team appears to be shrinking or restructuring."

    return f"{projects}\n\n{maturity_context} {hiring_context}"


def _build_bangalore_intel(company):
    """Build Bangalore-specific hiring intelligence"""
    name = company.get("name", "")
    members = company.get("team_members", [])
    locations = [l.lower() for l in company.get("locations", [])]
    has_blr = any("bengaluru" in l or "bangalore" in l for l in locations)

    blr_members = [m for m in members if "bengaluru" in (m.get("location", "") or "").lower()
                   or "bangalore" in (m.get("location", "") or "").lower()]
    blr_managers = [m for m in blr_members if m.get("_role_level", 9) <= 2]
    blr_leads = [m for m in blr_members if m.get("_role_level", 9) == 3]

    if not has_blr and not blr_members:
        # Check if ANY member is in Bangalore even if company location doesn't list it
        other_locs = list({m.get("location", "") for m in members if m.get("location")})
        other_locs = [l for l in other_locs if l]
        nearest = ", ".join(other_locs[:3]) if other_locs else "Check LinkedIn for current openings"
        return {
            "has_bangalore": False,
            "summary": f"No confirmed Pega team presence in Bangalore. Primary locations: {nearest}.",
            "contacts": [],
            "tip": f"This company's Pega team operates from other cities. Apply via career portal or LinkedIn — some companies allow relocation or WFH."
        }

    contacts = []
    for m in blr_managers + blr_leads:
        contact = {
            "name": m.get("name", ""),
            "title": m.get("title", ""),
            "role_type": "Hiring Manager" if m.get("_role_level", 9) <= 1 else ("Architect" if m.get("_role_level") == 2 else "Lead"),
            "linkedin": m.get("linkedin", ""),
            "certs": m.get("certs", ""),
        }
        contacts.append(contact)

    summary_parts = []
    if blr_managers:
        summary_parts.append(f"{len(blr_managers)} manager(s)/architect(s)")
    if blr_leads:
        summary_parts.append(f"{len(blr_leads)} lead(s)")
    total_blr = len(blr_members)
    summary = f"Bangalore Pega presence confirmed: {total_blr} team member(s) identified — {', '.join(summary_parts) if summary_parts else 'team members present'}."

    tip = ""
    if blr_managers:
        mgr = blr_managers[0]
        tip = f"Connect with {mgr['name']} ({mgr.get('title','')}) on LinkedIn — they are the key decision-maker for the Bangalore Pega team."
    elif blr_leads:
        ld = blr_leads[0]
        tip = f"Connect with {ld['name']} ({ld.get('title','')}) for a referral. Team leads often influence hiring decisions."
    else:
        tip = "Pega team members are in Bangalore. Connect with any of them on LinkedIn for referral opportunities."

    return {
        "has_bangalore": True,
        "summary": summary,
        "contacts": contacts,
        "tip": tip,
        "total_blr_members": total_blr,
    }


def add_hiring_playbooks(data):
    """Add comprehensive hiring strategy playbooks for every company."""

    # Deep intelligence overrides for top companies (unique insights beyond what rules can derive)
    DEEP_OVERRIDES = {
        "JPMorgan Chase": {
            "business_reality": "JPMC India's Pega team runs the Wholesale KYC Operations (WKO) platform — automating client onboarding, due diligence, and KYC compliance across 180+ countries. This is a LIVE, mission-critical system processing ~30,000 KYC requirements annually for their Corporate & Investment Banking (CIB) division. They also build low-code workflow platforms for internal banking operations.\n\nThis is NOT a greenfield project — it's a well-established system with 5+ year-old codebases. Day-to-day work involves maintaining complex case lifecycles, building new rules within existing frameworks, and integrating with downstream compliance systems. The team works in Agile sprints with a mature DevOps pipeline.",
            "insider_tip": "JPMC titles are unique — 'Associate' = mid-level, 'VP' = senior developer/lead (NOT actual management). Don't be confused by titles. The Pega team is split across Hyderabad and Bengaluru. Most hiring happens at Associate/VP level. Ashish Agrawal (ED, CLSA) leads the Pega practice — connecting with him or his direct reports gives you the best shot."
        },
        "Wells Fargo": {
            "business_reality": "Wells Fargo has one of the most advanced Pega implementations in India. Their flagship is Pega Smart Investigate for payments — automating Swift/Wire payment investigations and dispute resolution. They're ALSO pioneering Pega GenAI adoption (one of the first GCCs to do so) and actively building with Constellation UI and Cosmos.\n\nThis team is technically cutting-edge. Day-to-day involves working with the latest Pega versions (8.x/24.x), GenAI features, Constellation UI components, and CDH decisioning. If you want to work with the newest Pega tech, Wells Fargo is one of the best places in India.",
            "insider_tip": "Wells Fargo has multiple VP-level Pega architects (unusual depth for a GCC). The team values CLSA-certified architects highly — Shiva Kumar Singani has both CLSA and TOGAF. If you're pursuing CLSA, this team will actively support your certification journey. They also send people to PegaInnovate events."
        },
        "HSBC": {
            "business_reality": "HSBC's India Pega team is entirely focused on Customer Decision Hub (CDH) — building Next-Best-Action decisioning engines, marketing campaign orchestration, and pricing engines across global markets. They're migrating CDH workloads to Google Cloud Platform (GCP with BigQuery, Dataflow, Pub/Sub).\n\nThis is a CDH-specialist team. If your experience is purely case management, you'll need to upskill significantly on CDH, adaptive models, and decisioning strategies. However, if you have any CDH exposure, this is one of the best CDH-focused teams in India.",
            "insider_tip": "HSBC is unique because they're almost exclusively CDH-focused (not case management). Most Pega developers in India have case management experience. If you invest time learning CDH and NBA strategies, you'll face almost zero competition for these roles. They also value GCP cloud skills — BigQuery + Dataflow experience is a bonus."
        },
        "Citibank": {
            "business_reality": "Citi's Pega implementation is one of the most diverse in India — they run multiple distinct applications: CitiKYC (client KYC workflows), Metro (CIB Markets platform), STARS (operational app), and Swift MT/ISO20022 MX message processing. They're cloud-native on Red Hat OpenShift, actively adopting Constellation UI, and building with Kafka for event-driven architecture.\n\nDay-to-day involves working across complex enterprise integrations. The tech stack is modern — OpenShift containers, Kafka event streaming, REST/DX APIs. Citi expects developers who can handle both Pega platform work and integration architecture.",
            "insider_tip": "Citi has VP-level hiring happening in Chennai (not just Hyderabad/Bangalore). Chennai has less competition for Pega roles. They're one of the few banks running Pega on Red Hat OpenShift — if you have any containerisation/Kubernetes experience, even basic, mention it prominently. Their Swift/ISO20022 work is unique and interesting."
        },
        "Bank of America": {
            "business_reality": "BofA is in the middle of a major Pega modernisation — migrating from legacy PRPC to Pega Infinity and implementing Cosmos UI. Current work involves contact preference management, CTI integration, and case tracking systems.\n\nThis is a migration-focused team right now. The long-tenured team (since 2018) means established processes and deep institutional knowledge. New hires will mainly work on upgrade/modernisation efforts — converting old rules, redesigning UIs for Cosmos, and testing regression.",
            "insider_tip": "BofA's team has been stable since 2018 — they rarely hire. But the Infinity migration is creating new headcount. If you have specific PRPC-to-Infinity migration experience, you're in a very strong position. Mention any Cosmos UI implementation experience — it's exactly what they need right now."
        },
        "Barclays": {
            "business_reality": "Barclays India has a growing Pega practice spanning core banking workflows and operations automation. The team is expanding with VP-level Pega architects leading the practice.\n\nBarclays offers a unique blend — strong UK banking culture with India GCC flexibility. The team is smaller and growing, meaning more ownership and visibility for individual developers compared to mega-teams at JPMC or Wells Fargo.",
            "insider_tip": "Sudhanshu Chatterjee (VP, Pega Architect) is a key hiring manager. He actively recruits through LinkedIn. A direct connection with him is the fastest path to an interview. Barclays also values the CLSA certification path highly."
        },
        "Standard Chartered": {
            "business_reality": "Standard Chartered uses Pega for trade finance operations, client onboarding, and compliance workflows across their Asia/Middle East/Africa markets. The team handles complex multi-jurisdiction banking processes.\n\nSC is unique because of their emerging markets focus — the Pega work involves multi-country regulatory compliance (not just India/US). If you understand cross-border banking regulations, you're extremely valuable to them.",
            "insider_tip": "Standard Chartered often hires Pega developers who previously worked at other banks (they value banking domain knowledge heavily). If you're currently at a consulting company working on a banking client, SC considers that relevant experience."
        },
        "Goldman Sachs": {
            "business_reality": "Goldman Sachs has a selective Pega practice focused on internal operations automation for their Securities and Asset Management divisions. The team is small but elite — they hire ex-Pegasystems employees and require deep architectural knowledge.\n\nGS expects Pega developers to also be strong general software engineers. Interviews include system design and coding rounds beyond just Pega platform knowledge.",
            "insider_tip": "Goldman Sachs pays the highest in the market (30-45 LPA for experienced devs). But they interview like a tech company — expect DSA/system design rounds alongside Pega questions. They have an ex-Pegasystems VP on the team, so the bar is very high. Only apply if you have strong fundamentals beyond Pega."
        },
        "Deutsche Bank": {
            "business_reality": "Deutsche Bank India uses Pega for Global Transaction Banking (GTB) trade finance operations, workflow automation, and production support. The team has a strong SRE/DevOps focus managing 80+ weekly production changes.\n\nDB values operational excellence. Day-to-day includes production support management, SRE practices, and DevOps for Pega applications — not just development. If you enjoy the ops side of Pega (deployment, monitoring, incident management), DB is excellent.",
            "insider_tip": "Deutsche Bank's Pega team has very long tenure (9+ year veteran AVP). They value stability and deep expertise over frequent job-hopping. If your resume shows 3+ years at one company, highlight that — it resonates with their culture."
        },
        "Optum / UnitedHealth Group": {
            "business_reality": "Optum (UHG's tech arm) uses Pega for healthcare claims processing, member services, provider workflows, and clinical operations automation. This is the US healthcare domain — complex regulatory requirements (HIPAA), large transaction volumes, and intricate business rules.\n\nHealthcare Pega is a niche with high demand and relatively few practitioners. If you can learn healthcare domain basics (claims adjudication, member enrollment, provider credentialing), you become very marketable. Optum's India team is one of the largest healthcare Pega practices.",
            "insider_tip": "Healthcare Pega developers are scarce — most Indian Pega devs have banking experience. If you invest time learning healthcare domain basics (even just HIPAA 101 and claims processing concepts), you'll face minimal competition. Optum also offers US-client exposure, which is valuable for visa/relocation prospects."
        },
        "Verizon": {
            "business_reality": "Verizon uses Pega for telecom service fulfillment, customer service case management, order management, and network operations workflows. Their implementation spans consumer and enterprise divisions.\n\nTelecom Pega is different from banking — it involves high-volume real-time processing, complex product catalogs, and integration with telecom-specific systems (OSS/BSS). Cognizant has historically been Verizon's primary Pega vendor, so many Verizon Pega devs join from Cognizant.",
            "insider_tip": "Many current Verizon direct Pega hires previously worked on Verizon projects at Cognizant/other SIs. If you can get placed on a Verizon engagement at a consulting company first, transitioning to Verizon direct is a well-trodden path with higher success rate."
        },
        "Mercedes-Benz R&D India": {
            "business_reality": "Mercedes-Benz R&D India has a surprisingly large Pega practice focused on customer experience platforms, dealer management systems, after-sales service workflows, and vehicle lifecycle management. They build automotive-specific CRM and case management solutions.\n\nThis is an unusual and interesting Pega implementation — automotive domain with premium brand standards. The work involves luxury customer experience design, multi-channel dealer integrations, and high-quality UI requirements. Less 'back-office workflow', more 'customer-facing platform'.",
            "insider_tip": "Mercedes-Benz has 9+ profiled team members — one of the largest automotive Pega teams. They've had some departures recently, which means backfill positions. Automotive Pega is rare, so even basic case management experience positions you well. They value clean UI/UX sensibility given their brand standards."
        },
        "American Express": {
            "business_reality": "AmEx uses Pega for card member services, dispute resolution, fraud case management, and operations automation. Their Pega implementation integrates with complex payments infrastructure spanning global markets.\n\nAmEx is unique because of their 'membership' culture — Pega applications serve high-value card members and need to reflect premium service standards. The team works on both servicing workflows and decisioning (CDH for offers/marketing).",
            "insider_tip": "AmEx has 8+ profiled Pega team members with diverse specialisations. They value customer experience thinking alongside technical skills. If you can articulate how your Pega work improved end-customer experience (not just process efficiency), you'll resonate with AmEx culture."
        },
        "Ford Motor Company": {
            "business_reality": "Ford Business Solutions (FBS) India uses Pega for vehicle financing, dealer operations, customer service, and supply chain workflow automation. Their Pega practice spans the entire vehicle lifecycle from manufacturing to after-sales.\n\nAutomotive + finance Pega is a niche combination. Day-to-day involves building workflows for auto-finance products, dealer management, and customer service. If you have auto-finance or collections experience (like CPM), this is highly relevant.",
            "insider_tip": "Ford's Pega team has had some departures — creating backfill openings. Your auto-finance and collections experience (CPM) maps directly to their needs. Highlight this in your application — it's a rare combination in the Pega market."
        },
        "Pegasystems": {
            "business_reality": "Pega itself — the product company. India roles include professional services (implementing Pega for clients), product engineering, support engineering, and pre-sales solution architecture. Working here means you'll implement Pega for multiple clients across industries, not just one company.\n\nPega expects the deepest platform knowledge. You'll work on cutting-edge features before they reach market. The bar is the highest in the Pega ecosystem — they want people who understand the platform at an architectural level.",
            "insider_tip": "Pegasystems heavily values CLSA certification — it's almost mandatory for senior roles. If you're CSSA, start your CLSA prep before applying. Pega also hires from their partner ecosystem (Areteans, Aaseya, etc.) — working at a Pega Elite partner first is a proven path to Pegasystems direct."
        },
        "Stellantis": {
            "business_reality": "Stellantis (Jeep, Chrysler, Fiat, Peugeot parent) uses Pega for multi-brand customer service, dealer management, and vehicle lifecycle workflows. Their India GCC handles Pega implementations spanning multiple automotive brands.\n\nThis is interesting because of the multi-brand complexity — one Pega platform serving Jeep, Chrysler, Fiat, Peugeot customers with different business rules per brand. Good exposure to multi-tenant Pega architecture.",
            "insider_tip": "Stellantis has had departures creating openings. They value people who can handle multi-brand complexity — emphasise any experience working on applications that serve multiple business units or product lines."
        },
        "Aflac": {
            "business_reality": "Aflac India GCC uses Pega for supplemental insurance claims processing, policy servicing, and customer workflow automation. Aflac is the largest supplemental insurance provider in the US — their Pega platform handles high-volume claims across cancer, accident, and disability insurance products.\n\nInsurance claims Pega is a stable, growing niche. Day-to-day involves complex business rules for claims adjudication, policy validation, and regulatory compliance.",
            "insider_tip": "Aflac is growing their India GCC rapidly — they're one of the easier insurance GCCs to get into right now. Insurance Pega experience is valued but not required. Show willingness to learn the insurance domain and you'll be considered."
        },
        "Sun Life": {
            "business_reality": "Sun Life India GCC uses Pega for insurance policy administration, claims workflows, and customer service automation for their global life insurance and asset management businesses.\n\nSun Life offers good exposure to both insurance and wealth management domains. The team is growing with investment in modern Pega versions.",
            "insider_tip": "Sun Life is actively expanding their India Pega team. They're open to candidates from non-insurance backgrounds who have strong Pega platform skills. Good stepping-stone to other insurance GCCs."
        },
        "Mastercard": {
            "business_reality": "Mastercard India uses Pega for payments operations, merchant services, fraud case management, and dispute resolution workflows. The Pega platform integrates with Mastercard's global payment processing infrastructure.\n\nPayments Pega at Mastercard is high-visibility work — the workflows impact millions of transactions. Strong emphasis on performance, security, and regulatory compliance.",
            "insider_tip": "Mastercard values fintech/payments domain knowledge. If you've worked on any payment processing, reconciliation, or fraud detection Pega projects, highlight them prominently. They also value candidates who understand card payment lifecycles."
        },
        "MUFG": {
            "business_reality": "MUFG (Mitsubishi UFJ Financial Group) Pension & Market Services uses Pega for pension administration, fund management operations, and financial markets workflows. This is Japanese banking culture with Australian/global operations.\n\nNiche domain but very stable work. Pension administration Pega requires understanding of complex financial products and regulatory frameworks across multiple jurisdictions.",
            "insider_tip": "MUFG has 5+ profiled team members and is steadily growing. They're one of the less-competitive banking GCCs to get into. If you can demonstrate attention to detail and complex rule management skills, you'll do well in their interviews."
        },
        "Vodafone / VOIS": {
            "business_reality": "Vodafone Intelligent Solutions (VOIS) India uses Pega for telecom customer service, order management, network fault management, and billing dispute resolution across Vodafone's global operations (UK, Europe, Africa).\n\nTelecom Pega at Vodafone involves high-volume case processing, complex SLA management, and integration with telecom-specific systems. Good exposure to European telecom standards.",
            "insider_tip": "VOIS actively hires Pega developers and is one of the more accessible telecom GCCs. They value candidates who can handle high-volume case management and have experience with SLA-based workflows."
        },
        "Nokia India": {
            "business_reality": "Nokia India uses Pega for internal operations automation, supply chain workflows, and customer engagement across their telecom equipment business. Nokia's Pega practice is smaller but strategic.\n\nAn interesting choice for developers who want telecom domain exposure without the massive team politics of larger companies. More ownership per developer.",
            "insider_tip": "Nokia's Pega team is small — each person has significant ownership. They value self-starters who can design and deliver independently. Good stepping-stone for developers who want to transition from SI to GCC."
        },
        "Roche India": {
            "business_reality": "Roche India uses Pega for pharmaceutical operations, clinical trial management workflows, and patient engagement platforms. Roche is a global pharma/diagnostics leader.\n\nPharma Pega is one of the most specialised niches. Understanding GxP compliance, clinical data management, and pharmaceutical manufacturing processes is valuable but not required — Roche trains on domain.",
            "insider_tip": "Roche has hired ex-Pegasystems employees — they value deep platform expertise. If you can show strong Pega architecture knowledge, domain gaps are overlooked. They're also a 'gcc_top' priority company — actively being scanned for openings."
        },
        "Commonwealth Bank": {
            "business_reality": "CBA (Commonwealth Bank of Australia) India uses Pega for retail banking operations, customer onboarding, and mortgage/lending workflows for Australian markets.\n\nAustralian banking culture is different from US/UK — more relaxed, good work-life balance, but the Pega work is still complex (Australian financial regulations, multi-product banking).",
            "insider_tip": "CBA's Pega CoE lead departed recently — this creates both a backfill opening and potential restructuring opportunity. If you can position yourself as a senior/lead candidate, the timing could be excellent."
        },
        "John Deere": {
            "business_reality": "John Deere India (JDTCI) uses Pega for manufacturing operations, dealer management, equipment lifecycle management, and customer service workflows for their agriculture and construction equipment business.\n\nManufacturing Pega is unique — involves complex product configuration rules, dealer network management, and field service workflows. Very different from banking/insurance.",
            "insider_tip": "John Deere has had departures creating openings. Manufacturing domain is unique enough that they're open to candidates from other sectors. Show willingness to learn the manufacturing/dealer domain and you'll be competitive."
        },
        "Lloyds Banking Group": {
            "business_reality": "Lloyds India GCC uses Pega for retail banking operations, mortgage processing, customer service automation, and compliance workflows for the UK's largest retail bank.\n\nUK banking standards (FCA regulations, PSD2, Open Banking) create interesting technical challenges. Good exposure to UK financial regulations if you're interested in UK market opportunities.",
            "insider_tip": "Lloyds has 5+ profiled team members and is growing. They're slightly less competitive than HSBC/Barclays for Pega roles. UK banking domain knowledge is a strong differentiator — even basic understanding of FCA/PRA regulations helps."
        },
        "NatWest Group": {
            "business_reality": "NatWest India uses Pega for commercial banking operations, KYC/AML workflows, and customer service automation for UK markets. NatWest has been a significant Pega investor.\n\nSimilar to Lloyds in terms of UK banking focus. The team handles complex KYC/AML regulatory workflows — if you have compliance/KYC experience, it's highly relevant.",
            "insider_tip": "NatWest actively hires Pega developers in their India GCC. They value KYC/AML domain knowledge. If you've worked on any compliance automation or regulatory workflow projects, highlight them."
        },
    }

    for company in data.get("companies", []):
        name = company.get("name", "")
        overrides = DEEP_OVERRIDES.get(name, {})

        blr_intel = _build_bangalore_intel(company)
        playbook = {
            "business_reality": overrides.get("business_reality", _build_business_reality(company)),
            "project_phase": overrides.get("project_phase", _determine_project_phase(company)),
            "skills_to_master": overrides.get("skills_to_master", _build_skills(company)),
            "pitch_to_manager": overrides.get("pitch_to_manager", _build_pitch(company)),
            "approach_ranking": overrides.get("approach_ranking", _build_approach(company)),
            "difficulty": overrides.get("difficulty", _determine_difficulty(company)),
            "salary_range": overrides.get("salary_range", _determine_salary(company)),
            "insider_tip": overrides.get("insider_tip", _build_insider_tip(company)),
            "bangalore_intel": blr_intel,
        }
        company["_hiring_playbook"] = playbook


def esc(text):
    """HTML-escape text"""
    if not text:
        return ""
    return html_mod.escape(str(text))

def get_health_badge(company):
    """Determine health badge based on hiring_status and maturity"""
    status = company.get("hiring_status", "").lower()
    maturity = company.get("maturity", "").lower()
    
    if "rapidly" in status or "actively" in status:
        return "hot", "HOT GROWTH"
    elif "growing" in status:
        return "grow", "GROWING"
    elif "declining" in status:
        return "bleed", "DECLINING"
    elif "stable" in status and "very high" in maturity:
        return "stable", "STABLE-PREMIUM"
    elif "stable" in status:
        return "stable", "STABLE"
    elif "moderate" in status:
        return "mixed", "MODERATE"
    else:
        return "stable", "STABLE"

def get_sector_icon(sector):
    """Return sector category for grouping"""
    s = sector.lower()
    if any(x in s for x in ["bank", "financial", "payment"]):
        return "Banking & Financial Services"
    elif any(x in s for x in ["insur", "health", "pharma", "medical"]):
        return "Insurance, Healthcare & Pharma"
    elif any(x in s for x in ["telecom", "media"]):
        return "Telecom & Media"
    elif any(x in s for x in ["auto", "manufact", "industrial", "truck"]):
        return "Automotive & Industrial"
    elif any(x in s for x in ["tech", "semi", "platform"]):
        return "Technology"
    elif any(x in s for x in ["retail", "fmcg", "consumer", "fashion", "travel"]):
        return "Consumer, Retail & FMCG"
    elif any(x in s for x in ["logist", "energy", "business"]):
        return "Logistics, Energy & Services"
    else:
        return "Other"

def make_id(name):
    """Generate HTML id from company name"""
    return name.lower().replace(" ", "-").replace("&", "and").replace("/", "-").replace("(", "").replace(")", "").replace(",", "").replace(".", "")[:40]

def get_cert_class(cert):
    """Determine if cert is top-tier"""
    c = cert.upper()
    if any(x in c for x in ["CLSA", "LSA", "PCLSA", "PSA"]):
        return "top"
    return ""

def build_person_html(member):
    """Build HTML for a single team member"""
    name = member.get("name", "Unknown")
    title = member.get("title", "")
    location = member.get("location", "")
    tenure = member.get("tenure", "")
    career = member.get("career", [])
    
    # Handle both "certs" (string) and "certifications" (list) formats
    certs_raw = member.get("certs", member.get("certifications", []))
    if isinstance(certs_raw, str):
        certs = [c.strip() for c in certs_raw.split(",") if c.strip()]
    elif isinstance(certs_raw, list):
        certs = [c for c in certs_raw if c]
    else:
        certs = []
    
    linkedin = member.get("linkedin", "")
    
    parts = []
    parts.append(f'<div class="person">')
    if linkedin:
        parts.append(f'<div class="pn"><a href="{esc(linkedin)}" target="_blank" style="color:#fff;text-decoration:none">{esc(name)} <span style="font-size:10px;color:#0a66c2">&#x1F517; LinkedIn</span></a></div>')
    else:
        parts.append(f'<div class="name">{esc(name)}</div>')
    if title:
        parts.append(f'<div class="title">{esc(title)}</div>')
    
    if certs:
        parts.append('<div class="certs">')
        for c in certs:
            cls = get_cert_class(c)
            cls_attr = f' class="cert {cls}"' if cls else ' class="cert"'
            parts.append(f'<span{cls_attr}>{esc(c)}</span>')
        parts.append('</div>')
    
    # Rich career timeline if available
    if career:
        parts.append('<div class="timeline">')
        for i, stop in enumerate(career):
            co = stop.get("company", "")
            role = stop.get("role", "")
            dates = stop.get("dates", "")
            detail = stop.get("detail", "")
            
            # Determine stop class
            stop_class = "current" if i == 0 else ""
            if "LEFT" in role.upper() or "DEPARTED" in role.upper() or "LEAVING" in dates.upper():
                stop_class = "left"
            
            parts.append(f'<div class="stop {stop_class}">')
            parts.append(f'<span class="co">{esc(co)}</span> — <span class="role">{esc(role)}</span>')
            if dates:
                parts.append(f'<br><span class="dates">{esc(dates)}</span>')
            loc = stop.get("location", location if i == 0 else "")
            if loc:
                parts.append(f' · <span class="loc">{esc(loc)}</span>')
            if detail:
                parts.append(f'<br><span class="detail">{esc(detail)}</span>')
            parts.append('</div>')
        parts.append('</div>')
    elif location or tenure:
        parts.append('<div class="timeline">')
        loc_str = f' · <span class="loc">{esc(location)}</span>' if location else ''
        tenure_str = f'<span class="dates">{esc(tenure)}</span>' if tenure else ''
        parts.append(f'<div class="stop current"><span class="co">Current</span>{loc_str}')
        if tenure_str:
            parts.append(f'<br>{tenure_str}')
        parts.append('</div></div>')
    
    parts.append('</div>')
    return "\n".join(parts)

def build_company_html(company):
    """Build HTML for a single company"""
    name = company.get("name", "Unknown")
    sector = company.get("sector", "")
    locations = company.get("locations", [])
    team_size = company.get("team_size", "Unknown")
    maturity = company.get("maturity", "")
    hiring_status = company.get("hiring_status", "")
    projects = company.get("projects", "")
    tech_stack = company.get("tech_stack", [])
    domains = company.get("domains", [])
    certs_req = company.get("certifications_required", [])
    members = company.get("team_members", [])
    highlights = company.get("highlights", [])
    
    health_class, health_label = get_health_badge(company)
    comp_id = make_id(name)
    loc_str = " + ".join(locations) if locations else "India"
    
    # Build search data
    search_terms = f"{name} {sector} {loc_str} {' '.join(domains)} {' '.join(tech_stack)}".lower()
    
    parts = []
    parts.append(f'<div class="company" id="{comp_id}" data-health="{health_class}" data-search="{esc(search_terms)}">')
    
    # Company header
    parts.append(f'<div class="company-head" onclick="this.parentElement.classList.toggle(\'open\')">')
    parts.append(f'<div class="info">')
    parts.append(f'<h3>{esc(name)}</h3>')
    domain_str = ", ".join(domains[:3]) if domains else sector
    parts.append(f'<div class="meta"><b>{esc(loc_str)}</b> · {esc(sector)} · {esc(domain_str)}</div>')
    parts.append(f'</div>')
    parts.append(f'<span class="badge {health_class}">{esc(health_label)}</span>')
    parts.append(f'<span class="team-size">~{esc(team_size)} Pega devs</span>')
    parts.append(f'</div>')
    
    # Company body
    parts.append(f'<div class="company-body">')
    
    # Team Health Assessment
    parts.append(f'<div class="analysis">')
    parts.append(f'<h4>Team Profile & Intelligence</h4>')
    
    assessment_parts = []
    
    # Maturity
    if maturity:
        mat_class = "good" if "high" in maturity.lower() or "very" in maturity.lower() else "highlight"
        assessment_parts.append(f'<span class="{mat_class}">Maturity: {esc(maturity)}</span>')
    
    # Hiring status
    if hiring_status:
        hire_class = "good" if "grow" in hiring_status.lower() or "rapid" in hiring_status.lower() or "active" in hiring_status.lower() else "highlight"
        if "declin" in hiring_status.lower():
            hire_class = "danger"
        assessment_parts.append(f'<span class="{hire_class}">Hiring: {esc(hiring_status)}</span>')
    
    # Team size
    if team_size:
        assessment_parts.append(f'Team size: ~{esc(team_size)} Pega developers.')
    
    assessment_str = " · ".join(assessment_parts)
    
    # Projects
    if projects:
        assessment_str += f'<br><br><b>Projects & Use Cases:</b> {esc(projects)}'
    
    # Tech stack
    if tech_stack:
        stack_str = ", ".join(tech_stack)
        assessment_str += f'<br><br><b>Tech Stack:</b> {esc(stack_str)}'
    
    # Certifications required
    if certs_req:
        cert_str = ", ".join(certs_req)
        assessment_str += f'<br><b>Certifications:</b> {esc(cert_str)}'
    
    # Highlights
    if highlights:
        assessment_str += '<br><br><b>Key Intelligence:</b><br>'
        for h in highlights:
            assessment_str += f'&bull; {esc(h)}<br>'
    
    parts.append(f'<p>{assessment_str}</p>')
    parts.append(f'</div>')
    
    # Team members
    if members:
        parts.append(f'<div class="analysis" style="background:#0a1929;border-color:#1e4d7f">')
        parts.append(f'<h4>Team Members ({len(members)} confirmed)</h4>')
        parts.append(f'</div>')
        
        for member in members:
            parts.append(build_person_html(member))
    else:
        parts.append(f'<div class="analysis" style="background:#1a0f0f;border-color:#4a2020">')
        parts.append(f'<h4>Team Members</h4>')
        parts.append(f'<p><span class="highlight">Individual team member data not yet available.</span> Pega usage confirmed via job postings, customer stories, or LinkedIn signals. Company has ~{esc(team_size)} Pega developers based on available intelligence.</p>')
        parts.append(f'</div>')
    
    parts.append(f'</div></div>')
    return "\n".join(parts)

def build_sidebar_nav(sectors_map):
    """Build sidebar navigation"""
    parts = []
    for sector_name, companies in sectors_map.items():
        parts.append(f'<div class="cat">{esc(sector_name)}</div>')
        for c in companies:
            name = c.get("name", "")
            comp_id = make_id(name)
            health_class, _ = get_health_badge(c)
            team_size = c.get("team_size", "?")
            members = c.get("team_members", [])
            member_count = f"{len(members)} people" if members else f"~{team_size}"
            
            # Nav link style
            nav_class = ""
            if health_class == "hot":
                nav_class = ' class="hot"'
            elif health_class == "grow":
                nav_class = ' class="grow"'
            elif health_class == "bleed":
                nav_class = ' class="bleed"'
            
            parts.append(f'<a href="#{comp_id}"{nav_class}>{esc(name)} ({member_count})</a>')
    return "\n".join(parts)

def build_html(data):
    """Build the integrated Team Intelligence + Deep Dossiers page.
    
    Embeds all company data as JSON and uses JavaScript to render:
    - Dashboard grid view (Team Intelligence style)
    - Deep Dossier detail view when a company is selected
    Both views in one page, no server required.
    """
    companies = data.get("companies", [])
    total_companies = len(companies)
    total_members = sum(len(c.get("team_members", [])) for c in companies)
    growing = sum(1 for c in companies if "grow" in c.get("hiring_status", "").lower() or "rapid" in c.get("hiring_status", "").lower() or "active" in c.get("hiring_status", "").lower())
    stable = sum(1 for c in companies if "stable" in c.get("hiring_status", "").lower())
    
    # Assign a sector group to each company
    for c in companies:
        c["_sector_group"] = get_sector_icon(c.get("sector", "Other"))

    # Serialize to JSON for embedding in HTML script tag
    # Use ensure_ascii=True so no unicode chars break, and escape </script> sequences
    data_json = json.dumps(companies, ensure_ascii=True)
    data_json = data_json.replace("</", "<\\/")  # prevent closing script tag in JSON

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Pega GCC Intelligence &amp; Deep Dossiers — {total_companies} Companies | {total_members}+ People</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Inter,system-ui,sans-serif;background:#09090b;color:#e4e4e7;min-height:100vh;overflow-x:hidden}}
a{{color:#818cf8;text-decoration:none}}a:hover{{text-decoration:underline}}
/* Top bar */
.topbar{{position:sticky;top:0;z-index:20;background:rgba(9,9,11,.94);backdrop-filter:blur(14px);border-bottom:1px solid #1e1e21;padding:10px 20px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}}
.brand{{font-size:.95rem;font-weight:900;letter-spacing:-.02em;white-space:nowrap}}
.brand .g1{{background:linear-gradient(135deg,#a855f7,#6366f1);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.tabs{{display:flex;border-radius:8px;overflow:hidden;border:1px solid #27272a}}
.tabs .tb{{padding:7px 18px;font-size:.78rem;font-weight:600;cursor:pointer;background:transparent;color:#71717a;border:none;transition:.15s}}
.tabs .tb.active{{background:#6366f1;color:#fff}}
.tabs .tb:hover:not(.active){{background:#18181b;color:#a5b4fc}}
.search-box{{flex:1;max-width:500px;position:relative}}
.search-box input{{width:100%;padding:8px 12px 8px 34px;border:1px solid #27272a;border-radius:8px;background:#111113;color:#e4e4e7;font-size:.82rem;outline:none}}
.search-box input:focus{{border-color:#6366f1;box-shadow:0 0 0 2px rgba(99,102,241,.2)}}
.search-box .ico{{position:absolute;left:10px;top:7px;color:#52525b;font-size:.9rem}}
.pills{{display:flex;gap:10px;align-items:center;font-size:.78rem;color:#71717a}}
.pills b{{font-weight:800}}
.pills .pv{{background:linear-gradient(135deg,#6366f1,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.pills .gv{{color:#4ade80}}
/* Layout */
.dash{{display:flex;height:calc(100vh - 52px)}}
.sidebar{{width:250px;border-right:1px solid #1e1e21;overflow-y:auto;padding:10px 0;flex-shrink:0;background:#0c0c0e}}
.sidebar .sh{{font-size:.62rem;color:#52525b;text-transform:uppercase;letter-spacing:1px;font-weight:700;padding:12px 12px 4px}}
.sidebar .fp-row{{display:flex;flex-wrap:wrap;gap:4px;padding:4px 12px 10px}}
.sidebar .fp{{padding:3px 10px;border-radius:6px;font-size:.66rem;font-weight:600;border:1px solid #27272a;background:transparent;color:#71717a;cursor:pointer;transition:.15s}}
.sidebar .fp:hover{{border-color:#6366f1;color:#c4b5fd}}
.sidebar .fp.active{{background:#6366f1;border-color:#6366f1;color:#fff}}
.sidebar .ci{{display:flex;align-items:center;gap:6px;padding:6px 12px;cursor:pointer;font-size:.78rem;color:#a1a1aa;transition:.1s;border-left:3px solid transparent}}
.sidebar .ci:hover{{background:#111113;color:#e4e4e7}}
.sidebar .ci.active{{background:#111113;color:#fff;border-left-color:#6366f1}}
.sidebar .ci .sz{{margin-left:auto;font-size:.65rem;color:#52525b;font-weight:700}}
.main-c{{flex:1;overflow-y:auto;padding:20px 24px}}
/* Stat cards */
.stat-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:18px}}
.sc{{background:#111113;border:1px solid #1e1e21;border-radius:10px;padding:14px;text-align:center}}
.sc .sv{{font-size:1.3rem;font-weight:900;margin-bottom:2px}}
.sc .sl{{font-size:.65rem;color:#52525b;text-transform:uppercase;letter-spacing:.5px;font-weight:600}}
.sv.pv{{background:linear-gradient(135deg,#6366f1,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.sv.gv{{color:#4ade80}}.sv.av{{color:#fbbf24}}.sv.rv{{color:#f87171}}
/* Overview grid */
.ov-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px}}
.ov-card{{background:#111113;border:1px solid #1e1e21;border-radius:12px;padding:14px 16px;cursor:pointer;transition:.15s}}
.ov-card:hover{{border-color:#6366f1;transform:translateY(-2px);box-shadow:0 8px 30px rgba(99,102,241,.08)}}
.ov-card .oc-top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}}
.ov-card .oc-name{{font-size:.88rem;font-weight:800}}
.ov-card .oc-loc{{font-size:.7rem;color:#52525b;margin-bottom:6px}}
.ov-card .oc-proj{{font-size:.76rem;color:#71717a;line-height:1.4;margin-bottom:8px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.ov-card .oc-bottom{{display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
.ov-card .oc-sz{{font-size:.68rem;color:#a1a1aa;font-weight:700;margin-left:auto}}
.tp{{display:inline-block;font-size:.62rem;padding:1px 6px;border-radius:3px;background:rgba(99,102,241,.08);color:#818cf8;border:1px solid rgba(99,102,241,.15);margin:1px}}
/* Sector badges */
.sb{{font-size:.68rem;padding:2px 10px;border-radius:12px;font-weight:600}}
.sb-bk{{background:rgba(99,102,241,.12);color:#818cf8}}
.sb-in{{background:rgba(168,85,247,.12);color:#c084fc}}
.sb-te{{background:rgba(251,146,60,.12);color:#fb923c}}
.sb-au{{background:rgba(56,189,248,.12);color:#38bdf8}}
.sb-tc{{background:rgba(45,212,191,.12);color:#2dd4bf}}
.sb-co{{background:rgba(250,204,21,.12);color:#facc15}}
.sb-lo{{background:rgba(217,119,6,.12);color:#d97706}}
/* Hiring status */
.hs{{display:inline-flex;align-items:center;gap:4px;font-weight:700;font-size:.72rem;padding:2px 8px;border-radius:6px}}
.hs-g{{background:rgba(34,197,94,.12);color:#4ade80}}
.hs-h{{background:rgba(34,197,94,.22);color:#22c55e}}
.hs-s{{background:rgba(250,204,21,.12);color:#fbbf24}}
.hs-d{{background:rgba(244,63,94,.12);color:#fb7185}}
.hs-m{{background:rgba(251,146,60,.12);color:#fb923c}}
.hs-dot{{width:5px;height:5px;border-radius:50%;background:currentColor}}
/* Detail view (dossier) */
.detail-back{{padding:6px 14px;border-radius:8px;border:1px solid #27272a;background:#111113;color:#a1a1aa;font-size:.8rem;cursor:pointer;margin-bottom:16px;display:inline-flex;align-items:center;gap:6px;transition:.15s}}
.detail-back:hover{{border-color:#6366f1;color:#fff}}
.dh h2{{font-size:1.4rem;font-weight:900;color:#fff;margin-bottom:6px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.dh .meta-r{{display:flex;gap:14px;flex-wrap:wrap;color:#71717a;font-size:.8rem;margin-bottom:16px}}
.section{{background:#111113;border:1px solid #1e1e21;border-radius:12px;padding:16px 18px;margin-bottom:14px}}
.section h3{{font-size:.85rem;font-weight:700;margin-bottom:10px;color:#e4e4e7}}
/* Tech/domain/cert pills in detail */
.pill-row{{display:flex;flex-wrap:wrap;gap:5px}}
.p-tech{{padding:3px 10px;border-radius:6px;font-size:.72rem;font-weight:600;background:rgba(99,102,241,.1);color:#a5b4fc;border:1px solid rgba(99,102,241,.15)}}
.p-dom{{padding:3px 10px;border-radius:6px;font-size:.72rem;font-weight:600;background:rgba(168,85,247,.1);color:#c4b5fd;border:1px solid rgba(168,85,247,.15)}}
.p-cert{{padding:3px 10px;border-radius:6px;font-size:.72rem;font-weight:600;background:rgba(250,204,21,.08);color:#fde047;border:1px solid rgba(250,204,21,.15)}}
/* Person card (dossier style) */
.person{{background:#0c0c0e;border:1px solid #1e1e21;border-radius:10px;padding:14px 16px;margin-top:10px}}
.person .pn{{font-size:.88rem;font-weight:700;color:#fff}}
.person .pt{{font-size:.78rem;color:#818cf8;margin-bottom:4px}}
.person .pc{{margin:5px 0}}
.person .pc span{{display:inline-block;font-size:.65rem;background:rgba(250,204,21,.08);border:1px solid rgba(250,204,21,.15);color:#fde047;padding:1px 7px;border-radius:4px;margin:1px}}
.person .pc span.top{{background:rgba(250,204,21,.15);border-color:rgba(250,204,21,.3);font-weight:700}}
/* Career timeline */
.tl{{margin-top:8px;padding-left:16px;border-left:2px solid #27272a}}
.tl .st{{position:relative;padding:4px 0 8px 14px;font-size:.78rem}}
.tl .st::before{{content:'';position:absolute;left:-21px;top:8px;width:8px;height:8px;border-radius:50%;border:2px solid #3f3f46;background:#0c0c0e}}
.tl .st.cur::before{{border-color:#4ade80;background:#166534}}
.tl .st.lft::before{{border-color:#f87171;background:#991b1b}}
.tl .st .sc{{font-weight:600;color:#e4e4e7}}.tl .st .sr{{color:#818cf8}}.tl .st .sd{{color:#52525b;font-size:.72rem}}.tl .st .sl{{color:#3f3f46;font-size:.72rem}}.tl .st .sdt{{color:#71717a;font-size:.72rem;font-style:italic;margin-top:2px}}
/* Highlights */
.hi li{{padding:4px 0;font-size:.8rem;color:#a1a1aa;display:flex;align-items:flex-start;gap:8px;list-style:none}}
.hi li::before{{content:'';display:inline-block;width:5px;height:5px;border-radius:50%;background:#6366f1;flex-shrink:0;margin-top:7px}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:translateY(0)}}}}
.fade{{animation:fadeIn .25s ease forwards}}
@media(max-width:900px){{.sidebar{{display:none}}.main-c{{padding:12px}}.ov-grid{{grid-template-columns:1fr}}.pills{{display:none}}}}
/* Hiring Playbook styles */
.pb-section{{background:linear-gradient(135deg,#0f0a1e,#111113);border:2px solid #4f46e5;border-radius:14px;padding:20px 22px;margin-bottom:14px;position:relative;overflow:hidden}}
.pb-section::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,#6366f1,#a855f7,#ec4899)}}
.pb-section h3{{font-size:.95rem;font-weight:900;margin-bottom:14px;color:#e4e4e7;display:flex;align-items:center;gap:8px}}
.pb-block{{margin-bottom:16px;padding-bottom:14px;border-bottom:1px solid rgba(99,102,241,.1)}}
.pb-block:last-child{{margin-bottom:0;padding-bottom:0;border-bottom:none}}
.pb-label{{font-size:.72rem;font-weight:700;color:#818cf8;text-transform:uppercase;letter-spacing:.8px;margin-bottom:8px}}
.pb-text{{font-size:.82rem;color:#a1a1aa;line-height:1.7;white-space:pre-line}}
.pb-phase{{display:inline-flex;align-items:center;gap:6px;padding:4px 14px;border-radius:20px;font-size:.74rem;font-weight:700;margin-bottom:12px}}
.phase-mature{{background:rgba(250,204,21,.1);color:#fde047;border:1px solid rgba(250,204,21,.2)}}
.phase-growing,.phase-expanding{{background:rgba(34,197,94,.1);color:#4ade80;border:1px solid rgba(34,197,94,.2)}}
.phase-migration{{background:rgba(251,146,60,.1);color:#fb923c;border:1px solid rgba(251,146,60,.2)}}
.phase-emerging{{background:rgba(168,85,247,.1);color:#c084fc;border:1px solid rgba(168,85,247,.2)}}
.phase-stable{{background:rgba(56,189,248,.1);color:#38bdf8;border:1px solid rgba(56,189,248,.2)}}
.approach-item{{display:flex;align-items:flex-start;gap:10px;padding:10px 12px;margin-bottom:6px;border-radius:8px;background:rgba(99,102,241,.04);border:1px solid rgba(99,102,241,.08)}}
.approach-item:hover{{background:rgba(99,102,241,.08)}}
.approach-eff{{flex-shrink:0;padding:2px 8px;border-radius:4px;font-size:.65rem;font-weight:800;text-transform:uppercase;letter-spacing:.5px;min-width:50px;text-align:center}}
.eff-best{{background:rgba(34,197,94,.2);color:#4ade80;border:1px solid rgba(34,197,94,.3)}}
.eff-high{{background:rgba(99,102,241,.2);color:#a5b4fc;border:1px solid rgba(99,102,241,.3)}}
.eff-medium{{background:rgba(250,204,21,.15);color:#fde047;border:1px solid rgba(250,204,21,.2)}}
.approach-method{{font-size:.8rem;font-weight:700;color:#e4e4e7;min-width:180px;flex-shrink:0}}
.approach-tip{{font-size:.76rem;color:#71717a;line-height:1.5}}
.pitch-list{{list-style:none;padding:0}}
.pitch-list li{{padding:8px 0 8px 20px;font-size:.8rem;color:#a1a1aa;line-height:1.5;position:relative;border-bottom:1px solid rgba(99,102,241,.06)}}
.pitch-list li:last-child{{border-bottom:none}}
.pitch-list li::before{{content:'\\2713';position:absolute;left:0;color:#4ade80;font-weight:700;font-size:.75rem}}
.pb-meta{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px}}
.pb-diff{{padding:5px 14px;border-radius:8px;font-size:.76rem;font-weight:700}}
.diff-easy{{background:rgba(34,197,94,.12);color:#4ade80;border:1px solid rgba(34,197,94,.2)}}
.diff-medium{{background:rgba(250,204,21,.12);color:#fbbf24;border:1px solid rgba(250,204,21,.2)}}
.diff-hard{{background:rgba(251,146,60,.12);color:#fb923c;border:1px solid rgba(251,146,60,.2)}}
.diff-vhard{{background:rgba(244,63,94,.12);color:#fb7185;border:1px solid rgba(244,63,94,.2)}}
.pb-salary{{padding:5px 14px;border-radius:8px;font-size:.76rem;font-weight:700;background:rgba(99,102,241,.12);color:#a5b4fc;border:1px solid rgba(99,102,241,.2)}}
.pb-insider{{background:linear-gradient(135deg,rgba(168,85,247,.08),rgba(99,102,241,.08));border:1px solid rgba(168,85,247,.2);border-radius:10px;padding:14px 16px}}
.pb-insider-label{{font-size:.72rem;font-weight:800;color:#c084fc;text-transform:uppercase;letter-spacing:.8px;margin-bottom:6px}}
.pb-insider p{{font-size:.82rem;color:#e4e4e7;line-height:1.6;font-style:italic}}
.p-skill{{padding:3px 10px;border-radius:6px;font-size:.72rem;font-weight:600;background:rgba(34,197,94,.08);color:#86efac;border:1px solid rgba(34,197,94,.15)}}
</style>
</head>
<body>
<div class="topbar">
  <div class="brand">Pega <span class="g1">Intelligence Hub</span></div>
  <div class="tabs">
    <button class="tb active" onclick="switchView('dashboard')">Dashboard</button>
    <button class="tb" onclick="switchView('dossiers')">Deep Dossiers</button>
  </div>
  <div class="search-box"><span class="ico">&#x2315;</span><input id="searchInput" placeholder="Search companies, people, tech, certs, cities..." oninput="applySearch()"></div>
  <div class="pills"><b class="pv" id="sCo">{total_companies}</b> companies &nbsp;<b class="gv" id="sPpl">{total_members}+</b> people &nbsp;<b class="gv" id="sGrow">{growing}</b> growing</div>
</div>
<div class="dash">
  <div class="sidebar" id="sidebar"></div>
  <div class="main-c" id="mainContent"></div>
</div>
<script>
const DATA=''' + data_json + f''';
let activeSector='all',activeCompany=null,viewMode='dashboard';
const sectorMap={{'Banking & Financial Services':'bk','Insurance, Healthcare & Pharma':'in','Telecom & Media':'te','Automotive & Industrial':'au','Technology':'tc','Consumer, Retail & FMCG':'co','Logistics, Energy & Services':'lo','Other':'lo'}};
function sbClass(sg){{return 'sb sb-'+(sectorMap[sg]||'bk');}}
function hsClass(s){{s=s.toLowerCase();if(s.includes('rapidly')||s.includes('actively'))return 'hs hs-h';if(s.includes('growing'))return 'hs hs-g';if(s.includes('declining'))return 'hs hs-d';if(s.includes('moderate'))return 'hs hs-m';return 'hs hs-s';}}
function getCerts(m){{if(m.certs&&typeof m.certs==='string')return m.certs.split(',').map(c=>c.trim()).filter(c=>c);if(m.certifications&&Array.isArray(m.certifications))return m.certifications.filter(c=>c);return[];}}
function isTop(c){{const u=c.toUpperCase();return u.includes('CLSA')||u.includes('LSA')||u.includes('PCLSA')||u.includes('PSA');}}
function getFiltered(){{
  const q=document.getElementById('searchInput').value.toLowerCase();
  let list=activeSector==='all'?DATA:DATA.filter(c=>c._sector_group===activeSector);
  if(q)list=list.filter(c=>{{
    const blob=(c.name+' '+c.sector+' '+(c.locations||[]).join(' ')+' '+(c.tech_stack||[]).join(' ')+' '+(c.domains||[]).join(' ')+' '+c.projects+' '+c.hiring_status+' '+c.maturity+' '+(c.highlights||[]).join(' ')+' '+(c.certifications_required||[]).join(' ')+' '+(c.team_members||[]).map(m=>m.name+' '+m.title+' '+getCerts(m).join(' ')).join(' ')).toLowerCase();
    return blob.includes(q);
  }});
  return list.sort((a,b)=>(parseInt(b.team_size)||0)-(parseInt(a.team_size)||0));
}}
function renderSidebar(){{
  const sb=document.getElementById('sidebar');
  const sectors=[...new Set(DATA.map(c=>c._sector_group))];
  let h='<div class="sh">Sectors</div><div class="fp-row"><button class="fp'+(activeSector==='all'?' active':'')+'" onclick="filterSector(\\'all\\')">All ('+DATA.length+')</button>';
  sectors.forEach(s=>{{const n=DATA.filter(c=>c._sector_group===s).length;h+='<button class="fp'+(activeSector===s?' active':'')+'" onclick="filterSector(\\''+s.replace(/'/g,"\\\\'")+'\\')">'+s.split(' ')[0]+' ('+n+')</button>';}});
  h+='</div><div class="sh">Companies</div>';
  getFiltered().forEach(c=>{{
    const act=activeCompany&&activeCompany.name===c.name;
    const mc=(c.team_members||[]).length;
    h+='<div class="ci'+(act?' active':'')+'" onclick="openCompany(\\''+c.name.replace(/'/g,"\\\\'")+'\\')">'; 
    h+='<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+c.name+'</span>';
    h+='<span class="sz">'+(mc>0?mc+'p':'~'+c.team_size)+'</span></div>';
  }});
  sb.innerHTML=h;
}}
function filterSector(s){{activeSector=s;activeCompany=null;renderSidebar();showDashboard();}}
function switchView(v){{
  viewMode=v;
  document.querySelectorAll('.tabs .tb').forEach(b=>b.classList.remove('active'));
  document.querySelectorAll('.tabs .tb')[v==='dashboard'?0:1].classList.add('active');
  if(v==='dashboard'){{activeCompany=null;renderSidebar();showDashboard();}}
  else{{activeCompany=null;renderSidebar();showAllDossiers();}}
}}
function showDashboard(){{
  const list=getFiltered();
  const mc=document.getElementById('mainContent');
  const totalPpl=list.reduce((s,c)=>s+(c.team_members||[]).length,0);
  const gr=list.filter(c=>{{const s=c.hiring_status.toLowerCase();return s.includes('growing')||s.includes('rapidly')||s.includes('actively');}}).length;
  const hi=list.filter(c=>c.maturity&&(c.maturity.toLowerCase().includes('high')||c.maturity.toLowerCase().includes('very'))).length;
  const cities=new Set();list.forEach(c=>(c.locations||[]).forEach(l=>cities.add(l)));
  let h='<div class="stat-grid fade"><div class="sc"><div class="sv pv">'+list.length+'</div><div class="sl">Companies</div></div>';
  h+='<div class="sc"><div class="sv av">'+totalPpl+'</div><div class="sl">People Profiled</div></div>';
  h+='<div class="sc"><div class="sv gv">'+gr+'</div><div class="sl">Actively Growing</div></div>';
  h+='<div class="sc"><div class="sv gv">'+hi+'</div><div class="sl">High Maturity</div></div>';
  h+='<div class="sc"><div class="sv pv">'+cities.size+'</div><div class="sl">Cities</div></div></div>';
  h+='<div class="ov-grid fade">';
  list.forEach(c=>{{
    const mc_=(c.team_members||[]).length;
    h+='<div class="ov-card" onclick="openCompany(\\''+c.name.replace(/'/g,"\\\\'")+'\\')">'; 
    h+='<div class="oc-top"><span class="oc-name">'+c.name+'</span><span class="'+sbClass(c._sector_group)+'">'+c.sector+'</span></div>';
    h+='<div class="oc-loc">'+(c.locations||[]).join(' / ')+(mc_>0?' &bull; '+mc_+' members profiled':'')+'</div>';
    h+='<div class="oc-proj">'+c.projects+'</div>';
    if(c.tech_stack&&c.tech_stack.length>0){{h+='<div style="margin-bottom:6px">';c.tech_stack.slice(0,5).forEach(t=>{{h+='<span class="tp">'+t+'</span>';}});if(c.tech_stack.length>5)h+='<span class="tp" style="color:#52525b">+'+(c.tech_stack.length-5)+'</span>';h+='</div>';}}
    h+='<div class="oc-bottom"><span class="'+hsClass(c.hiring_status)+'"><span class="hs-dot"></span>'+c.hiring_status+'</span>';
    if(c.maturity)h+='<span style="font-size:.66rem;color:#71717a">'+c.maturity+'</span>';
    h+='<span class="oc-sz">~'+c.team_size+'</span></div></div>';
  }});
  h+='</div>';
  mc.innerHTML=h;mc.scrollTop=0;
}}
function renderPersonHTML(m){{
  const certs=getCerts(m);
  const li=m.linkedin||'';
  let h='<div class="person">';
  if(li)h+='<div class="pn"><a href="'+li+'" target="_blank" style="color:#fff;text-decoration:none">'+m.name+' <span style="font-size:10px;color:#0a66c2">&#x1F517;</span></a></div>';
  else h+='<div class="pn">'+m.name+'</div>';
  if(m.title)h+='<div class="pt">'+m.title+'</div>';
  if(certs.length>0){{h+='<div class="pc">';certs.forEach(c=>{{h+='<span'+(isTop(c)?' class="top"':'')+'>'+c+'</span>';}});h+='</div>';}}
  if(m.career&&m.career.length>0){{
    h+='<div class="tl">';
    m.career.forEach((s,i)=>{{
      let cls='st';if(i===0)cls+=' cur';if(s.role&&(s.role.toUpperCase().includes('LEFT')||s.role.toUpperCase().includes('DEPARTED')||s.role.toUpperCase().includes('SERVING NOTICE')))cls+=' lft';
      h+='<div class="'+cls+'"><span class="sc">'+(s.company||'')+'</span> &mdash; <span class="sr">'+(s.role||'')+'</span>';
      if(s.dates)h+='<br><span class="sd">'+s.dates+'</span>';
      const loc=s.location||(i===0?m.location:'');
      if(loc)h+=' &middot; <span class="sl">'+loc+'</span>';
      if(s.detail)h+='<br><span class="sdt">'+s.detail+'</span>';
      h+='</div>';
    }});
    h+='</div>';
  }} else if(m.location||m.tenure){{
    h+='<div class="tl"><div class="st cur"><span class="sc">Current</span>';
    if(m.location)h+=' &middot; <span class="sl">'+m.location+'</span>';
    if(m.tenure)h+='<br><span class="sd">'+m.tenure+'</span>';
    h+='</div></div>';
  }}
  h+='</div>';return h;
}}
function openCompany(name){{
  const co=DATA.find(c=>c.name===name);
  if(!co)return;
  activeCompany=co;renderSidebar();
  const mc=document.getElementById('mainContent');
  const tm=co.team_members||[];
  let h='<button class="detail-back" onclick="activeCompany=null;renderSidebar();'+(viewMode==='dashboard'?'showDashboard()':'showAllDossiers()')+'">&#x2190; Back</button>';
  h+='<div class="dh fade"><h2>'+co.name+' <span class="'+sbClass(co._sector_group)+'">'+co.sector+'</span></h2>';
  h+='<div class="meta-r"><span>&#x1F4CD; '+(co.locations||[]).join(', ')+'</span><span>&#x1F465; Team: ~'+co.team_size+'</span>';
  h+='<span class="'+hsClass(co.hiring_status)+'"><span class="hs-dot"></span>'+co.hiring_status+'</span>';
  if(co.maturity)h+='<span>&#x1F3AF; '+co.maturity+' Maturity</span>';
  h+='</div></div>';
  // Stats
  h+='<div class="stat-grid fade"><div class="sc"><div class="sv pv">~'+co.team_size+'</div><div class="sl">Team Size</div></div>';
  h+='<div class="sc"><div class="sv av">'+tm.length+'</div><div class="sl">Members Profiled</div></div>';
  h+='<div class="sc"><div class="sv gv">'+(co.tech_stack||[]).length+'</div><div class="sl">Technologies</div></div>';
  h+='<div class="sc"><div class="sv pv">'+(co.domains||[]).length+'</div><div class="sl">Domains</div></div></div>';
  // Projects
  h+='<div class="section fade"><h3>&#x1F4CB; Projects &amp; Use Cases</h3><p style="font-size:.82rem;color:#a1a1aa;line-height:1.6">'+co.projects+'</p></div>';
  // Tech + Domains + Certs row
  h+='<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px" class="fade">';
  h+='<div class="section"><h3>&#x2699; Tech Stack</h3><div class="pill-row">';(co.tech_stack||[]).forEach(t=>{{h+='<span class="p-tech">'+t+'</span>';}});h+='</div></div>';
  h+='<div class="section"><h3>&#x1F3E2; Domains</h3><div class="pill-row">';(co.domains||[]).forEach(d=>{{h+='<span class="p-dom">'+d+'</span>';}});h+='</div></div>';
  h+='<div class="section"><h3>&#x1F3C6; Certifications</h3><div class="pill-row">';(co.certifications_required||[]).forEach(c_=>{{h+='<span class="p-cert">'+c_+'</span>';}});h+='</div></div></div>';
  // Team members - grouped by org level
  if(tm.length>0){{
    h+='<div class="section fade"><h3>&#x1F464; Team Members ('+tm.length+' confirmed)</h3>';
    const levelColors={{1:'#818cf8',2:'#c084fc',3:'#38bdf8',4:'#4ade80',5:'#a1a1aa',9:'#f87171'}};
    const levelIcons={{1:'&#x1F451;',2:'&#x1F3D7;',3:'&#x1F6E0;',4:'&#x2B50;',5:'&#x1F4BB;',9:'&#x1F6AA;'}};
    let curLabel='';
    tm.forEach(m=>{{
      const rl=m._role_label||'';
      if(rl&&rl!==curLabel){{
        curLabel=rl;
        const lv=m._role_level||5;
        const col=levelColors[lv]||'#a1a1aa';
        const ico=levelIcons[lv]||'';
        h+='<div style="margin-top:14px;margin-bottom:6px;padding:4px 10px;border-left:3px solid '+col+';font-size:.72rem;font-weight:700;color:'+col+';text-transform:uppercase;letter-spacing:1px">'+ico+' '+rl+'</div>';
      }}
      h+=renderPersonHTML(m);
    }});
    h+='</div>';
  }} else {{
    h+='<div class="section fade"><h3>&#x1F464; Team Members</h3><p style="font-size:.82rem;color:#52525b;padding:8px 0">Individual profiles not yet available. Pega usage confirmed via job postings, customer stories, or LinkedIn signals. Estimated team: ~'+co.team_size+' developers.</p></div>';
  }}
  // Highlights
  if(co.highlights&&co.highlights.length>0){{
    h+='<div class="section fade"><h3>&#x2728; Key Intelligence</h3><ul class="hi">';
    co.highlights.forEach(hl=>{{h+='<li>'+hl+'</li>';}});
    h+='</ul></div>';
  }}
  // Hiring Playbook
  if(co._hiring_playbook){{
    const pb=co._hiring_playbook;
    h+='<div class="pb-section fade">';
    h+='<h3>&#x1F3AF; Hiring Playbook — How to Get Hired at '+co.name+'</h3>';
    // Bangalore Intel
    if(pb.bangalore_intel){{
      const bi=pb.bangalore_intel;
      if(bi.has_bangalore){{
        h+='<div class="pb-block" style="background:linear-gradient(135deg,rgba(34,197,94,.06),rgba(56,189,248,.06));border:1px solid rgba(34,197,94,.2);border-radius:10px;padding:14px 16px;margin-bottom:16px">';
        h+='<div class="pb-label" style="color:#4ade80">&#x1F4CD; Bangalore Pega Team — Confirmed Presence</div>';
        h+='<p style="font-size:.82rem;color:#a1a1aa;margin-bottom:10px">'+bi.summary+'</p>';
        if(bi.contacts&&bi.contacts.length>0){{
          h+='<div style="font-size:.72rem;font-weight:700;color:#38bdf8;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px">Key Bangalore Contacts</div>';
          bi.contacts.forEach(ct=>{{
            h+='<div style="display:flex;align-items:center;gap:10px;padding:8px 10px;margin-bottom:4px;background:rgba(9,9,11,.5);border-radius:6px;border:1px solid #1e1e21">';
            const roleCol=ct.role_type==="Hiring Manager"?"#4ade80":ct.role_type==="Architect"?"#818cf8":"#38bdf8";
            h+='<span style="font-size:.62rem;font-weight:800;padding:2px 8px;border-radius:4px;background:rgba(99,102,241,.1);color:'+roleCol+';border:1px solid rgba(99,102,241,.2);white-space:nowrap">'+ct.role_type+'</span>';
            if(ct.linkedin)h+='<a href="'+ct.linkedin+'" target="_blank" style="font-size:.8rem;font-weight:700;color:#fff;text-decoration:none">'+ct.name+' <span style="color:#0a66c2;font-size:.65rem">&#x1F517;</span></a>';
            else h+='<span style="font-size:.8rem;font-weight:700;color:#fff">'+ct.name+'</span>';
            h+='<span style="font-size:.72rem;color:#52525b;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+ct.title+'</span>';
            if(ct.certs)h+='<span style="font-size:.6rem;color:#fde047;background:rgba(250,204,21,.08);padding:1px 6px;border-radius:3px">'+ct.certs+'</span>';
            h+='</div>';
          }});
        }}
        if(bi.tip)h+='<p style="font-size:.78rem;color:#4ade80;margin-top:10px;font-style:italic">&#x1F4A1; '+bi.tip+'</p>';
        h+='</div>';
      }} else {{
        h+='<div class="pb-block" style="background:rgba(251,146,60,.04);border:1px solid rgba(251,146,60,.15);border-radius:10px;padding:12px 16px;margin-bottom:16px">';
        h+='<div class="pb-label" style="color:#fb923c">&#x1F4CD; Bangalore Presence</div>';
        h+='<p style="font-size:.82rem;color:#71717a">'+bi.summary+'</p>';
        if(bi.tip)h+='<p style="font-size:.76rem;color:#fb923c;margin-top:6px;font-style:italic">'+bi.tip+'</p>';
        h+='</div>';
      }}
    }}
    // Business Reality
    h+='<div class="pb-block"><div class="pb-label">What They Are Actually Doing With Pega</div>';
    const phaseRaw=(pb.project_phase||'').toLowerCase();
    let phCls='phase-emerging';
    if(phaseRaw.includes('mature')||phaseRaw.includes('stable'))phCls='phase-stable';
    else if(phaseRaw.includes('expand')||phaseRaw.includes('growing')||phaseRaw.includes('rapid'))phCls='phase-growing';
    else if(phaseRaw.includes('migrat'))phCls='phase-migration';
    h+='<div class="pb-phase '+phCls+'">&#x25CF; '+pb.project_phase+'</div>';
    h+='<p class="pb-text">'+pb.business_reality+'</p></div>';
    // Skills to Master
    if(pb.skills_to_master&&pb.skills_to_master.length>0){{
      h+='<div class="pb-block"><div class="pb-label">Skills to Master for This Company</div>';
      h+='<div class="pill-row">';pb.skills_to_master.forEach(s=>{{h+='<span class="p-skill">'+s+'</span>';}});h+='</div></div>';
    }}
    // Difficulty + Salary
    h+='<div class="pb-block"><div class="pb-meta">';
    const diffLow=(pb.difficulty||'').toLowerCase();
    let dCls='diff-medium';
    if(diffLow==='easy')dCls='diff-easy';else if(diffLow==='hard')dCls='diff-hard';else if(diffLow.includes('very'))dCls='diff-vhard';
    h+='<span class="pb-diff '+dCls+'">&#x1F512; Difficulty: '+pb.difficulty+'</span>';
    h+='<span class="pb-salary">&#x1F4B0; Expected: '+pb.salary_range+'</span>';
    h+='</div></div>';
    // How to Get Hired — Approach Ranking
    if(pb.approach_ranking&&pb.approach_ranking.length>0){{
      h+='<div class="pb-block"><div class="pb-label">Best Way to Get Hired — Ranked Approaches</div>';
      pb.approach_ranking.forEach(a=>{{
        const eLow=(a.effectiveness||'').toLowerCase();
        let eCls='eff-medium';if(eLow==='best')eCls='eff-best';else if(eLow==='high')eCls='eff-high';
        h+='<div class="approach-item"><span class="approach-eff '+eCls+'">'+a.effectiveness+'</span>';
        h+='<span class="approach-method">'+a.method+'</span>';
        h+='<span class="approach-tip">'+a.tip+'</span></div>';
      }});
      h+='</div>';
    }}
    // Pitch to Manager
    if(pb.pitch_to_manager&&pb.pitch_to_manager.length>0){{
      h+='<div class="pb-block"><div class="pb-label">Your Pitch to the Hiring Manager</div>';
      h+='<ul class="pitch-list">';pb.pitch_to_manager.forEach(p=>{{h+='<li>'+p+'</li>';}});h+='</ul></div>';
    }}
    // Insider Tip
    if(pb.insider_tip){{
      h+='<div class="pb-insider"><div class="pb-insider-label">&#x1F4A1; Insider Tip</div>';
      h+='<p>'+pb.insider_tip+'</p></div>';
    }}
    h+='</div>';
  }}
  mc.innerHTML=h;mc.scrollTop=0;
}}
function showAllDossiers(){{
  const list=getFiltered();
  const mc=document.getElementById('mainContent');
  const sectors=[...new Set(list.map(c=>c._sector_group))];
  let h='';
  sectors.forEach(sg=>{{
    const sc=list.filter(c=>c._sector_group===sg);
    if(sc.length===0)return;
    h+='<div style="background:linear-gradient(90deg,#111113,transparent);border-radius:10px;padding:12px 18px;margin:20px 0 12px;border-left:4px solid #6366f1" class="fade"><h2 style="font-size:1rem;color:#fff;font-weight:800">'+sg.toUpperCase()+'</h2><p style="font-size:.72rem;color:#52525b">'+sc.length+' companies</p></div>';
    sc.forEach(co=>{{
      const tm=co.team_members||[];
      h+='<div style="background:#111113;border:1px solid #1e1e21;border-radius:12px;margin-bottom:14px;overflow:hidden">';
      // Header (clickable)
      h+='<div style="padding:14px 18px;display:flex;align-items:center;gap:12px;cursor:pointer;border-bottom:1px solid #141416" onclick="openCompany(\\''+co.name.replace(/'/g,"\\\\'")+'\\')">'; 
      h+='<div style="flex:1"><div style="font-size:.9rem;font-weight:800;color:#fff">'+co.name+'</div>';
      h+='<div style="font-size:.72rem;color:#52525b">'+(co.locations||[]).join(' / ')+' &bull; '+co.sector+' &bull; '+(co.domains||[]).slice(0,3).join(', ')+'</div></div>';
      h+='<span class="'+hsClass(co.hiring_status)+'"><span class="hs-dot"></span>'+co.hiring_status+'</span>';
      h+='<span style="font-size:.78rem;color:#22d3ee;font-weight:700">~'+co.team_size+'</span></div>';
      // Quick info
      h+='<div style="padding:10px 18px;font-size:.78rem;color:#71717a;cursor:pointer" onclick="openCompany(\\''+co.name.replace(/'/g,"\\\\'")+'\\')">'; 
      h+='<div style="margin-bottom:6px">'+co.projects.substring(0,200)+(co.projects.length>200?'...':'')+'</div>';
      if(co.tech_stack&&co.tech_stack.length>0){{h+='<div>';co.tech_stack.slice(0,6).forEach(t=>{{h+='<span class="tp">'+t+'</span>';}});h+='</div>';}}
      if(tm.length>0)h+='<div style="margin-top:6px;color:#a1a1aa;font-weight:600">'+tm.length+' team members profiled &rarr; click for full dossier</div>';
      h+='</div></div>';
    }});
  }});
  mc.innerHTML=h;mc.scrollTop=0;
}}
function applySearch(){{renderSidebar();if(activeCompany)return;viewMode==='dashboard'?showDashboard():showAllDossiers();}}
renderSidebar();showDashboard();
</script>
</body>
</html>'''

def main():
    try:
        data = load_data()
        html_content = build_html(data)
        
        output_path = r"C:\Users\DNSATHV\Desktop\calude\Pega_Deep_Dossiers.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        companies = data.get("companies", [])
        total_members = sum(len(c.get("team_members", [])) for c in companies)
        print(f"SUCCESS: Generated {output_path}")
        print(f"  - {len(companies)} companies")
        print(f"  - {total_members} individual team members")
        print(f"  - File size: {len(html_content):,} bytes")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
