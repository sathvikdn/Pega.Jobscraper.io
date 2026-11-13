"""
Bulk import all LinkedIn-verified Pega team members from subagent research.
Merges into team_intelligence.json, then runs verify + clean + org_sort.
"""
import json

# All new members found from LinkedIn research, organized by company name
# ONLY people with verified Pega keywords (CSSA/CSA/PRPC/BPM/Pega in title/certs)
NEW_MEMBERS = {
    # ===== BANKING =====
    "BNP Paribas": [
        {"name": "Senthil Kannan Jayabalan", "title": "Vice President / Delivery Manager", "certs": "CSSA", "linkedin": "https://www.linkedin.com/in/senthilkannan"},
        {"name": "Jeevaprabha B", "title": "Associate Level 1 / Pega Developer", "certs": "CSSA, CSA", "location": "Chennai", "linkedin": "https://www.linkedin.com/in/jeevaprabhabdev"},
    ],
    "Societe Generale": [
        {"name": "Raj Shekhar Deo", "title": "Software Engineering Specialist / Pega Developer", "certs": "CSA, CSSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/raj-shekhar-deo-8a820a176"},
        {"name": "Sudhir Sharma", "title": "Lead Software Engineer / Pega Tech Lead", "certs": "CSSA, CSA, CPDC", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/sudhircse79"},
        {"name": "Rekha B.N", "title": "Lead Software Engineer - 11yr IT, 8yr PRPC", "certs": "CSSA v7.1, CSA v6.2", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/rekha-b-n-408b5937"},
        {"name": "R V Kishore", "title": "Software Engineer / PEGA Developer", "certs": "CSA, CSSA", "linkedin": "https://www.linkedin.com/in/rv-kishore33"},
    ],
    "ANZ Bank": [
        {"name": "Rajeswari Bungatavula", "title": "Engineer / Pega Developer", "certs": "CSSA, CSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/rajeswari-bungatavula-68a556215"},
        {"name": "Abhigna Lahiri Jallapally", "title": "Analyst / Business Analyst - Pega CSSA", "certs": "CSSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/jallapally-abhigna-lahiri"},
        {"name": "Sanjay Royal", "title": "Operations Engineer - Pega", "certs": "CSSA, CSA", "linkedin": "https://www.linkedin.com/in/sanjay-royal-868540143"},
    ],
    "BNY Mellon": [
        {"name": "Janardhan Krishnan", "title": "Lead PEGA Developer - 16yr veteran", "certs": "LSA", "location": "Chennai", "linkedin": "https://www.linkedin.com/in/janardhan-krishnan-90042623"},
        {"name": "Pravin Ankush", "title": "Project Lead Developer - 14yr veteran", "certs": "CSA, IBM BPM", "location": "Pune", "linkedin": "https://www.linkedin.com/in/pravin-ankush-63a05935"},
    ],
    "UBS India": [
        {"name": "Ankit Dangaich", "title": "Director - CLSA, Pega Architect/Admin", "certs": "CLSA v7", "linkedin": "https://www.linkedin.com/in/ankit-dangaich-483a8713a"},
        {"name": "Saptarshi Chakraborty", "title": "Director / Pega Architect - 12yr CSSA", "certs": "CSSA v5.5, CSA", "linkedin": "https://www.linkedin.com/in/saptarshi-chakraborty-66483221"},
        {"name": "Anuj Malviya", "title": "Associate Director / PEGA Senior System Architect", "certs": "CSSA v8, CSA v7.2", "linkedin": "https://www.linkedin.com/in/anuj-malviya-47a51176"},
        {"name": "Ranganathan Krishnamoorthy", "title": "Authorized Officer / Pega Technical Architect", "certs": "CSSA v8.5, CSA, Azure AZ-900", "location": "Pune", "linkedin": "https://www.linkedin.com/in/ranganathan-krishnamoorthy-403aaa75"},
        {"name": "Prakruti K S", "title": "Tech Engineer / Pega Developer - CSSA", "certs": "CSSA", "location": "Pune", "linkedin": "https://www.linkedin.com/in/prakruti-k-s-63333a15b"},
        {"name": "Vaishnav Ghadage", "title": "Software Engineer / Pega Developer", "certs": "CSA", "location": "Pune", "linkedin": "https://www.linkedin.com/in/vaishnav-ghadage"},
    ],
    "Commonwealth Bank": [
        {"name": "Deep Shikha", "title": "Senior Software Engineer - CSA, CSSA, PCDC", "certs": "CSSA, CSA, PCDC", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/deep-shikha-86b6061b2"},
        {"name": "Kavya T V", "title": "Senior Engineer - 5yr+ Pega veteran", "certs": "CSSA, CSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/kavya-t-v-9390a39a"},
        {"name": "Tanuja Pedapudi", "title": "Associate Software Engineer (PEGA) - CSSA", "certs": "CSSA, CSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/tanujapedapudi"},
        {"name": "Avinash Mathur", "title": "Software Engineer - CSSA, ex-CGI, ex-Accenture", "certs": "CSSA, CSA, AWS SA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/avinash-mathur-804b5716b"},
        {"name": "Ravi Shankar Bukkitla", "title": "Software Engineer - CSSA, ex-Infosys", "certs": "CSSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/ravi-shankar-bukkitla-359481209"},
        {"name": "Rajesh Kumar M", "title": "Software Engineer - CSSA, ex-TCS", "certs": "CSSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/rajesh-kumar-m-b35a4580"},
        {"name": "Akhil Chakka", "title": "PEGA Senior Developer - CSA, CSSA", "certs": "CSSA, CSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/chakkavijayakhil"},
    ],
    "Charles Schwab": [
        {"name": "Renuka Jampani", "title": "Software Developer Senior (Pega) - 13yr exp", "certs": "CSSA", "linkedin": "https://www.linkedin.com/in/renuka-jampani-56876380"},
        {"name": "Prathap Kumar", "title": "Pega Technology Lead", "certs": "CSA v8, CSSA v8", "linkedin": "https://www.linkedin.com/in/prathap-kumar-1aa645264"},
    ],
    "Kotak Mahindra Bank": [
        {"name": "Tanmay Sonar", "title": "Pega Developer - CSSA", "certs": "CSSA, CSA", "location": "Mumbai", "linkedin": "https://www.linkedin.com/in/tanmay-sonar-141817334"},
    ],
    "Capital One India": [
        # Only 2 found, already in data - skip
    ],
    # ===== INSURANCE / HEALTHCARE =====
    "Aflac": [
        # Already have Prathap Reddy and Rama Chandraiah - they match existing data
    ],
    "Carelon Global Solutions India": [
        {"name": "Nagarjun Reddy Padigapati", "title": "Senior Pega Developer / Senior SE", "certs": "CSSA, CSA", "location": "Hyderabad", "linkedin": "https://www.linkedin.com/in/nagarjun-reddy-padigapati-4360a9287"},
        {"name": "Jagadeesh Ponugoti", "title": "Pega Developer / Sr SE", "certs": "CSSA v7.2", "location": "Hyderabad", "linkedin": "https://www.linkedin.com/in/jagadeesh-ponugoti-68590798"},
        {"name": "Purva Patil", "title": "Sr Software Engineer / Pega Developer", "certs": "CSA, CSSA, CPDC", "location": "Hyderabad", "linkedin": "https://www.linkedin.com/in/purva-patil-87a5a5140"},
        {"name": "Achalasri Kaza", "title": "PEGA CSSA Developer / Senior SE", "certs": "CSSA v8.7", "location": "Hyderabad", "linkedin": "https://www.linkedin.com/in/achalasrikaza"},
        {"name": "SAI Praneeth Patel", "title": "Pega Developer / Senior System Architect", "certs": "CSA, CSSA", "location": "Hyderabad", "linkedin": "https://www.linkedin.com/in/sai-praneeth-patel-79b597129"},
        {"name": "Nagabhushanam Gaddam", "title": "Pega Developer / SE II", "certs": "CSSA, CSA", "location": "Hyderabad", "linkedin": "https://www.linkedin.com/in/nagabhushanam-gaddam-2433a482"},
        {"name": "Uday Kumar", "title": "Pega Developer / Senior SE - 7yr veteran", "certs": "CSA", "location": "Hyderabad", "linkedin": "https://www.linkedin.com/in/uday-kumar-7b930741"},
        {"name": "Bhargava Reddy", "title": "Pega Developer", "certs": "CSSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/bhargava-reddy-5a0399250"},
    ],
    "Allianz Technology": [
        {"name": "Tibin Mammen", "title": "Senior SE / PEGA Developer", "certs": "CSSA", "location": "Trivandrum", "linkedin": "https://www.linkedin.com/in/tibin-mammen-b7ab5816a"},
        {"name": "Kunal Rathod", "title": "Senior SE / Pega Developer", "certs": "CSA", "location": "Pune", "linkedin": "https://www.linkedin.com/in/kunal-rathod-2492571a6"},
        {"name": "Alinta Kunjumon", "title": "Pega CSA Engineer / Senior SE", "certs": "CSA", "location": "Kerala", "linkedin": "https://www.linkedin.com/in/alinta-kunjumon"},
        {"name": "Manikandan M", "title": "Senior SE / Pega Developer - CSSA", "certs": "CSSA, CSA", "location": "Pune", "linkedin": "https://www.linkedin.com/in/manikandan-m-166223219"},
    ],
    "Empower": [
        {"name": "Nithin H N", "title": "Senior Software Developer - Pega CSSA", "certs": "CSSA v7", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/nithin-h-n-399287121"},
        {"name": "Ashish Aryan", "title": "Engineer Software - Pega CSSA", "certs": "CSSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/ashish-aryan-87497414b"},
        {"name": "Sai Raghava", "title": "Senior SE - Pega CSA, CSSA", "certs": "CSA, CSSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/sai-raghava-b7a6b6127"},
        {"name": "Abhimanyu Verma", "title": "Lead Software Developer - ex-TCS/Cognizant", "certs": "Pega Developer", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/abhimanyu-verma-1108"},
    ],
    "Evernorth / Cigna": [
        {"name": "Subbarao Tatikonda", "title": "Advisor - CLSA, ex-Pegasystems", "certs": "CLSA v8.8, CSSA v7.1, CSA", "location": "Hyderabad", "linkedin": "https://www.linkedin.com/in/subbarao-tatikonda-198b7519"},
        {"name": "Vijay Reddy", "title": "Software Engineering Lead Analyst - CSA,CSSA,CPDC,CPBA", "certs": "CSA, CSSA, CPDC, CPBA", "location": "Hyderabad", "linkedin": "https://www.linkedin.com/in/vijay-reddy-50759258"},
        {"name": "Jahnavi Paladara", "title": "Application Development Advisor / Pega Architect", "certs": "CSSA v7.2, CSA v7.1", "location": "Hyderabad", "linkedin": "https://www.linkedin.com/in/jahnavi-paladara-00736b101"},
        {"name": "Manoj Kumar Reddy", "title": "Pega Developer / Senior Analyst", "certs": "CSSA, CSA", "location": "Hyderabad", "linkedin": "https://www.linkedin.com/in/manoj-kumar-reddy-870839129"},
        {"name": "Vineetha Ganduri", "title": "Pega Developer - CSSA", "certs": "CSSA, CSA", "linkedin": "https://www.linkedin.com/in/vineetha-ganduri"},
        {"name": "Seeion Kumari Kotapuri", "title": "Pega Developer / Senior Analyst", "certs": "CSSA, CSA", "location": "Hyderabad", "linkedin": "https://www.linkedin.com/in/seeion-kumari-kotapuri-05b71a194"},
    ],
    "enGen / Highmark India": [
        {"name": "Sathya Prakash K", "title": "Senior Pega Developer - CSA, CSSA, PCDC", "certs": "CSA, CSSA, PCDC", "location": "Hyderabad", "linkedin": "https://www.linkedin.com/in/sathyaprakashkella"},
        {"name": "Saikumar Boorugupelli", "title": "Senior Pega Developer / Consultant", "certs": "CSSA", "location": "Hyderabad", "linkedin": "https://www.linkedin.com/in/saikumar-boorugupelli-513406121"},
    ],
    "The Hartford India": [
        # Already has Srinandhu, Krishna Mohan, Sharmila - skip
    ],
    "Pfizer India": [
        {"name": "Arman Khan", "title": "Pega Developer - CSA, CSSA", "certs": "CSSA, CSA", "location": "Mumbai", "linkedin": "https://www.linkedin.com/in/arman-khan-sh310819"},
    ],
    # ===== PAYMENTS / FINTECH =====
    "Mastercard": [
        {"name": "Koushik Anand Vadapally", "title": "Senior BizOps Engineer / Pega Developer", "certs": "CSA, CSSA", "location": "Pune", "linkedin": "https://www.linkedin.com/in/koushik-anand-vadapally-06188379"},
        {"name": "Prudhvi Raghupatruni", "title": "Manager Product Development - ex-Pegasystems", "certs": "CSA", "location": "Pune", "linkedin": "https://www.linkedin.com/in/prudhvi-raghupatruni"},
    ],
    "Broadridge": [
        {"name": "Sairamya Pola", "title": "Pega Developer", "certs": "Pega Developer", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/sairamya-pola-55b063298"},
        {"name": "Sahaja Nayuni", "title": "Senior Member Technical - CSSA", "certs": "CSSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/sahaja-nayuni-59051b172"},
    ],
    "Global Payments India": [
        {"name": "Puran Kaushal", "title": "Director Application System Development - 20yr+ exp", "certs": "CSSA v7.2, CSA v7.1, Scrum Master", "location": "Noida", "linkedin": "https://www.linkedin.com/in/puran-kaushal-38ab967"},
        {"name": "Shubham Nayak", "title": "Associate Lead SE - Pega CSSA", "certs": "CSA, CSSA v7.1", "location": "Noida", "linkedin": "https://www.linkedin.com/in/shubham-nayak-35b02bb2"},
    ],
    # ===== TELECOM =====
    "BT Group": [
        {"name": "Srivatsan Babu", "title": "Software Engineering Pega Senior Developer", "certs": "CSA v7.1, CSSA v8.6", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/srivatsan-babu-59429251"},
        {"name": "Praveen Kumar", "title": "Lead Pega Decisioning Consultant - PCLSA", "certs": "PCLSA", "linkedin": "https://www.linkedin.com/in/praveenm08"},
        {"name": "Bindhu Gunuru", "title": "Senior Pega Developer - CSA, CSSA", "certs": "CSA, CSSA", "linkedin": "https://www.linkedin.com/in/bindhu-gunuru-23724b12a"},
        {"name": "Serika Mekala", "title": "Software Engineer Pega Developer", "certs": "CSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/serika-mekala-01aa1219b"},
    ],
    "Telstra": [
        {"name": "Rashmi K V", "title": "Pega Developer - CSSA, CSA", "certs": "CSSA, CSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/rashmi-k-v-5a474225"},
        {"name": "Prachi Ranjan", "title": "Senior SE - CSSA, CSA, CUIS - 9yr Pega", "certs": "CSSA, CSA, CUIS", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/prachi-ranjan-8a300025"},
        {"name": "Sourabh S.", "title": "Senior SE - CLSA-1, SAFe 5 Agilist", "certs": "CLSA Part 1, CSSA, CSA, SAFe 5", "location": "Pune", "linkedin": "https://www.linkedin.com/in/sourabh-soni"},
        {"name": "Sanket Bose", "title": "Software Engineer - CSA", "certs": "CSA", "location": "Pune", "linkedin": "https://www.linkedin.com/in/sanket-bose-39768714b"},
    ],
    "Amdocs": [
        {"name": "Jai Veer", "title": "Senior SE - CSA, CSSA", "certs": "CSA, CSSA", "location": "Gurugram", "linkedin": "https://www.linkedin.com/in/jaiveer7503"},
        {"name": "Raghu Pungav", "title": "Senior Pega Technical Engineer - CSA, CSSA", "certs": "CSA, CSSA", "location": "Gurugram", "linkedin": "https://www.linkedin.com/in/raghu-pungav-7385741aa"},
        {"name": "Aditya Teppalwar", "title": "Senior PEGA Engineer", "certs": "CSA", "location": "Pune", "linkedin": "https://www.linkedin.com/in/aditya-teppalwar-b93616168"},
    ],
    "Nokia India": [
        {"name": "Somesh Rayapati", "title": "Pega Developer - CSSA, CSA", "certs": "CSSA, CSA", "linkedin": "https://www.linkedin.com/in/somesh-rayapati-89331b1b9"},
        {"name": "Pandav Chakma", "title": "Pega Developer", "certs": "Pega Developer", "linkedin": "https://www.linkedin.com/in/pandav-chakma-039b91370"},
    ],
    "Orange Business India": [
        {"name": "Shivani Baranwal", "title": "Pega Developer - CSSA", "certs": "CSSA", "location": "Gurugram", "linkedin": "https://www.linkedin.com/in/shivani-baranwal"},
        {"name": "Suyash Gupta", "title": "Software Engineer / Junior Pega Developer", "certs": "Pega Developer", "location": "Gurugram", "linkedin": "https://www.linkedin.com/in/suyash15gupta"},
        {"name": "Rachit Varshney", "title": "IT Business Analyst - CSA, CPBA, SAFe 6", "certs": "CSA, CPBA", "location": "Gurugram", "linkedin": "https://www.linkedin.com/in/rachitvarshney"},
    ],
    # ===== AUTO / INDUSTRIAL =====
    "Siemens": [
        {"name": "Saheli Misra", "title": "Solutions Architect - CLSA, 11yr BPM", "certs": "CLSA v7.4, CSSA, CPMC", "linkedin": "https://www.linkedin.com/in/saheli-misra-a6891a57"},
        {"name": "Renuka Deshpande", "title": "Lead System Architect - CSSA, CSA", "certs": "CSSA, CSA", "linkedin": "https://www.linkedin.com/in/renuka-deshpande-08868a79"},
        {"name": "Aastha Patil", "title": "Software Developer Engineer / Pega Developer", "certs": "CSSA v8.8, CSA v8.5", "location": "Maharashtra", "linkedin": "https://www.linkedin.com/in/aastha-patil-11a605193"},
        {"name": "Rajashekar Nagireddy", "title": "Pega Developer - CSSA", "certs": "CSSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/rajashekar-nagireddy-577079247"},
        {"name": "Sandeep Punekar", "title": "Pega Developer - CSA, ex-TCS", "certs": "CSA", "linkedin": "https://www.linkedin.com/in/sandeep-punekar-2985ab88"},
    ],
    "Daimler Truck India": [
        {"name": "Sapana Mishra", "title": "Principal Consultant - Pega CSSA, ex-Accenture", "certs": "CSSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/sapana-mishra-a39a85117"},
        {"name": "Nidhi Sinha", "title": "Solutions Architect - CSA, CSSA, ex-TCS", "certs": "CSA, CSSA", "linkedin": "https://www.linkedin.com/in/nidhi-sinha-a06b6ba4"},
        {"name": "Subramanya S", "title": "Senior Consultant - CSA, ex-Instellars", "certs": "CSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/subramanya2388"},
    ],
    "Renault-Nissan Tech India": [
        {"name": "Bharathi Priya S", "title": "Software Developer / Pega CSSA", "certs": "CSSA", "location": "Chennai", "linkedin": "https://www.linkedin.com/in/bharathi-priya-s-a36a15202"},
        {"name": "Megala Kumaravel", "title": "Engineer - Pega CSSA v8.8", "certs": "CSSA v8.8", "location": "Chennai", "linkedin": "https://www.linkedin.com/in/megala-kumaravel-21a281214"},
    ],
    "Bosch": [
        {"name": "Kartik Rao Patange", "title": "Associate SE - CSA, CSSA", "certs": "CSA, CSSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/pkartikrao"},
        {"name": "Charan Sai Damineni", "title": "Software Engineer - CSA v8.7", "certs": "CSA v8.7", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/charan-sai-damineni-713122340"},
    ],
    "Cummins India": [
        {"name": "Deepakkumar Kumar", "title": "Pega Developer", "certs": "Pega Developer", "linkedin": "https://www.linkedin.com/in/deepakkumar-kumar-371820184"},
    ],
    # ===== TECH / CONSUMER =====
    "Intel India": [
        {"name": "Ajith Kumar", "title": "Cloud App Dev Engineer - CSSA, CSA, PCDC", "certs": "CSSA, CSA, PCDC", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/ajk2098"},
        {"name": "Kavitha Murthy", "title": "Pega Developer / Project Manager - 7yr+", "certs": "CSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/kavitha-murthy-713b241b"},
    ],
    "Shell India": [
        {"name": "Deepak Ojha", "title": "Software Engineer - Pega CSSA, CPDC, CRSA", "certs": "CSSA, CPDC, CSA, CRSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/ojha-deepak"},
        {"name": "Kanti Dwivedi", "title": "Senior SE / COE Platform Lead - ex-Pegasystems", "certs": "CSSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/kanti-dwivedi-353746144"},
        {"name": "Chinmai Sravanthi Udayagiri", "title": "Software Engineer - Pega, ex-Pegasystems", "certs": "Pega", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/chinmai-sravanthi-udayagiri-969342b3"},
        {"name": "Bhawna Garg", "title": "Pega Consultant / Senior System Architect - ex-Pegasystems", "certs": "CSSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/bhawna-garg-79b69213a"},
        {"name": "Bhavya Satija", "title": "Associate Software Engineer - CSA", "certs": "CSA", "linkedin": "https://www.linkedin.com/in/bhavyasatija06"},
    ],
    "Booking Holdings India": [
        {"name": "Navya Chatrati", "title": "Pega Senior System Architect - Constellation", "certs": "CSSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/navya-chatrati-6a9b3a82"},
        {"name": "Pavithra Namboodiri", "title": "Pega System Architect - CSA, CSSA", "certs": "CSA v8.6, CSSA v8.7", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/pavithra-namboodiri-a96b0186"},
        {"name": "Yamini G N", "title": "Pega System Architect - CSA, CSSA", "certs": "CSA, CSSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/yamini-g-n-9702a31b0"},
        {"name": "Satish Varma Penmetsa", "title": "Pega System Architect - ex-TCS", "certs": "CSSA", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/penmetsasatish"},
        {"name": "Siva Kasi Reddy Bathina", "title": "Pega Developer - ex-TCS", "certs": "Pega PRPC", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/siva-kasi-reddy-bathina-244849185"},
        {"name": "Shreya Chaudhury", "title": "Pega Developer - Customer Service Constellation", "certs": "Pega Developer", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/shreya-chaudhury-6582051a5"},
    ],
    "DHL": [
        {"name": "Siva Jyothi Pamireddy", "title": "Senior Software Developer - CLSA, CSSA, CSA", "certs": "CLSA, CSSA, CSA", "location": "Tamil Nadu", "linkedin": "https://www.linkedin.com/in/siva-jyothi-pamireddy-4b454b14b"},
        {"name": "Yogitha K.", "title": "DevOps Engineer - CSSA, CSA certified Pega developer", "certs": "CSSA, CSA", "linkedin": "https://www.linkedin.com/in/yogitha-k-3536ba105"},
    ],
    "Dell Technologies": [
        {"name": "Jvr Ramakrishna", "title": "Pega Developer - 4yr+", "certs": "Pega Developer", "location": "Hyderabad", "linkedin": "https://www.linkedin.com/in/jvr-ramakrishna-060795209"},
        {"name": "Dhulappa Rajole", "title": "CDH Core Developer / Pega Developer", "certs": "CSA, CSSA, CPDC, Pega UI", "linkedin": "https://www.linkedin.com/in/dhulappa-rajole-08780226"},
        {"name": "Prasadreddy Ponugoti", "title": "Senior SE - Pega BPM, 9yr+ veteran", "certs": "CSA v7.1", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/prasadreddy-ponugoti-08b3b830"},
    ],
    "Conduent": [
        {"name": "Gowsalya R", "title": "App Developer & Support Engineer II - CSA, CSSA", "certs": "CSA, CSSA", "linkedin": "https://www.linkedin.com/in/gowsalya-r-8822a520b"},
    ],
    "Levi Strauss & Co. India": [
        {"name": "Hemant M", "title": "Pega Developer - CSSA, CSA, CPDC", "certs": "CSSA v7.1, CSA v7.1, CPDC", "location": "Bengaluru", "linkedin": "https://www.linkedin.com/in/hemant-mohanan"},
    ],
    "Maersk GSC India": [
        {"name": "Abhilasha Das", "title": "Software Engineer - Pega SA v6.2", "certs": "Pega SA v6.2", "linkedin": "https://www.linkedin.com/in/abhilasha-das-95bbb5145"},
    ],
}


def main():
    # Load base JSON
    with open("team_intelligence.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    added_total = 0
    companies_updated = 0
    
    for company in data["companies"]:
        name = company["name"]
        if name in NEW_MEMBERS and NEW_MEMBERS[name]:
            existing_names = {m.get("name", "").lower().strip() for m in company.get("team_members", [])}
            added = 0
            for new_m in NEW_MEMBERS[name]:
                if new_m["name"].lower().strip() not in existing_names:
                    company["team_members"].append(new_m)
                    added += 1
            if added > 0:
                added_total += added
                companies_updated += 1
                print(f"  + {added} members -> {name} (now {len(company['team_members'])})")
    
    # Save
    with open("team_intelligence.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\nDone: Added {added_total} new members across {companies_updated} companies")
    total = sum(len(c.get("team_members", [])) for c in data["companies"])
    print(f"Total members in base JSON: {total}")


if __name__ == "__main__":
    main()
