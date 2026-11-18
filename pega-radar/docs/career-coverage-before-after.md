# Career-portal coverage: before and after

One row per original target group: the 286 original rows of `targets.json`, grouped by the employer each maps to.

**175 target groups** from 286 original rows. Before, 131 had a registry entry and 60 a direct portal. After, every group has an entry: 134 configured, 34 unsupported, 4 not configured, 3 wrong scope only. The configured groups hold 60 verified and 74 candidate portals.

- **Before** is the 15 November 2026 baseline registry: whether the employer had an entry, a direct portal and its own LinkedIn query.
- **After** is what `companies.json` v2 configures. `verified` portals were in the baseline. `candidate` portals are configured from
  the research and are scanned, but have not been checked live yet; `radar.py verify` does that on your PC. `wrong scope` and
  `unsupported` portals are listed with their reason and are **not** scanned.
- A configured portal is not a successful scan. Outcomes per run are in the Coverage view and in `radar.py coverage`.
- A general LinkedIn keyword search is never counted here; "LinkedIn query" means a dedicated `pega <employer>` search.

| Employer | Original rows | Before: entry | Before: direct portal | Before: LinkedIn query | After: state | After: portals | After: LinkedIn query | Reason / note |
|---|---|---|---|---|---|---|---|---|
| ABB | ABB — rows 2 | missing | none | no | configured | phenom `careers.abb/global/en` — candidate, scope global | no |  |
| Aflac | Aflac India — rows 3 | yes | none | no | configured | successfactors `careers.aflac.com` — candidate, scope global | no |  |
| AIG | AIG — rows 4 | yes | workday `aig/aig` | no | configured | workday `aig/wd1/aig` — verified, scope global | no |  |
| Airbus | Airbus — rows 5 | missing | none | no | configured | workday `ag/wd3/Airbus` — candidate, scope global | no |  |
| Airtel | Airtel — rows 6 | missing | none | no | unsupported | custom `https://careers.airtel.com/` — unsupported, scope unknown | no | No known vacancy provider was identified on the careers page; needs a site-specific parser once its job feed is found |
| Allianz Technology | Allianz Technology (×2); Allianz Technology India — rows 7, 8, 9 | yes | none | no | unsupported | custom `https://careers.allianz.com` — unsupported, scope unknown | no | The careers site could not be reached in the 15 Nov audit (TLS or network error), so its vacancy provider is unknown; needs a manual look before an adapter can be chosen |
| Amdocs | Amdocs India — rows 10 | yes | none | no | configured | eightfold `jobs.amdocs.com` — candidate, scope global | no |  |
| American Express | American Express (×2); American Express India — rows 11, 12, 13 | yes | none | yes | configured | oracle `egug.fa.us2.oraclecloud.com CX_1` — candidate, scope global | yes |  |
| Ameriprise | Ameriprise Financial India; Ameriprise India — rows 14, 15 | yes | workday `ameriprise/Ameriprise` | yes | configured | workday `ameriprise/wd5/Ameriprise` — verified, scope global | no |  |
| ANZ | ANZ; ANZ Bank; ANZ Bank India — rows 16, 17, 18 | yes | none | yes | configured | successfactors `careers.anz.com` — candidate, scope global | yes |  |
| AstraZeneca | AstraZeneca — rows 19 | missing | none | no | configured | talentbrew `careers.astrazeneca.com` — candidate, scope global | no |  |
| AT&T | AT&T India — rows 20 | yes | workday `att/ATTGeneral` | no | configured | workday `att/wd1/ATTGeneral` — verified, scope global | no |  |
| AXA | AXA — rows 21 | yes | none | no | configured | icims `careers.axa.com/careers-home` — candidate, scope global | no |  |
| Ayvens | Ayvens / LeasePlan — rows 22 | missing | none | no | configured | workday `ayvens/wd3/AyvensCareers` — candidate, scope global | no |  |
| Bank of America | Bank of America (×2); Bank of America India — rows 23, 24, 25 | yes | none | no | configured | workday `ghr/wd1/lateral-apac` — candidate, scope global<br>workday `ghr/wd1/lateral-us` — wrong scope, scope global | no | United States lateral-hire board; it cannot cover India roles |
| Barclays | Barclays (×2); Barclays India — rows 26, 27, 28 | yes | workday `barclays/External_Career_Site_Barclays` | no | configured | workday `barclays/wd3/External_Career_Site_Barclays` — verified, scope global | no |  |
| BD | BD / Becton Dickinson — rows 29 | yes | none | no | configured | workday `bdx/wd1/EXTERNAL_CAREER_SITE_USA` — wrong scope, scope global<br>talentbrew `jobs.bd.com/en` — candidate, scope global | no | USA-only career site (and its search ignored the keyword in the probe); not India coverage |
| BMW Financial Services | BMW Financial Services — rows 30 | missing | none | no | unsupported | custom `https://www.bmwgroup.jobs` — unsupported, scope unknown | no | The careers site could not be reached in the 15 Nov audit (TLS or network error), so its vacancy provider is unknown; needs a manual look before an adapter can be chosen |
| BMW TechWorks | BMW TechWorks — rows 31 | missing | none | no | unsupported | peoplestrong `careers-bmwtechworks.peoplestrong.com` — unsupported, scope india | no | PeopleStrong candidate portal: it loads jobs from script through an undocumented API, so reading it needs a JavaScript runtime or a published feed |
| BNP Paribas | BNP Paribas (×2); BNP Paribas India — rows 32, 33, 34 | yes | none | no | unsupported | custom `https://group.bnpparibas/careers` — unsupported, scope unknown | no | The careers site refused the 15 Nov audit request (HTTP 403); respected, not worked around. No public feed is known; the India page (bnpparibas.bank.in) is a marketing page |
| BNY | BNY India; BNY Mellon India — rows 35, 36 | yes | none | no | configured | oracle `eofe.fa.us2.oraclecloud.com BNY-Careers` — candidate, scope global | no |  |
| Boeing | Boeing — rows 37 | yes | workday `boeing/EXTERNAL_CAREERS` | no | configured | workday `boeing/wd1/EXTERNAL_CAREERS` — verified, scope global | no |  |
| Booking Holdings | Booking Holdings — rows 38 | yes | none | yes | not configured | — | yes | The group site lists its brands; each brand recruits on its own site. Booking.com is configured as its own entry. |
| Booking.com | Booking.com — rows 39 | only as an alias of Booking Holdings | none | no | configured | icims `jobs.booking.com/booking` — candidate, scope global | yes |  |
| Bosch | Bosch; Bosch / BGSW; Bosch India (BGSW) — rows 40, 41, 42 | yes | none | no | configured | smartrecruiters `BoschGroup` — candidate, scope global | no |  |
| BP | BP — rows 43 | yes | workday `bpinternational/bpCareers` | no | configured | workday `bpinternational/wd3/bpCareers` — verified, scope global | no |  |
| Broadridge | Broadridge India (×2) — rows 44, 45 | yes | workday `broadridge/Careers` | yes | configured | workday `broadridge/wd5/Careers` — verified, scope global | yes |  |
| BT Group | BT Group; BT Group India (×2) — rows 46, 47, 48 | yes | none | yes | unsupported | custom `https://bt.com/careers` — unsupported, scope unknown | yes | The careers site could not be reached in the 15 Nov audit (TLS or network error), so its vacancy provider is unknown; needs a manual look before an adapter can be chosen |
| Capital One | Capital One India — rows 49 | yes | workday `capitalone/Capital_One` | no | configured | workday `capitalone/wd12/Capital_One` — verified, scope global | no |  |
| Carelon Global Solutions | Carelon / Elevance; Carelon Global Solutions India; Elevance Health; Elevance Health India — rows 50, 51, 94, 95 | yes | workday `elevancehealth/ANT` | yes | configured | workday `elevancehealth/wd1/ANT` — verified, scope global | yes |  |
| Cargill | Cargill — rows 52 | missing | none | no | configured | talentbrew `careers.cargill.com/en` — candidate, scope global | no |  |
| Carrier | Carrier — rows 53 | yes | workday `carrier/jobs` | no | configured | workday `carrier/wd5/jobs` — verified, scope global | no |  |
| Charles Schwab | Charles Schwab India — rows 55 | yes | none | no | configured | talentbrew `www.schwabjobs.com` — candidate, scope global | no |  |
| Charter Communications | Charter / Spectrum — rows 56 | missing | none | no | unsupported | custom `https://jobs.spectrum.com` — unsupported, scope unknown | no | The careers site could not be reached in the 15 Nov audit (TLS or network error), so its vacancy provider is unknown; needs a manual look before an adapter can be chosen |
| Chevron | Chevron — rows 57 | missing | none | no | configured | talentbrew `careers.chevron.com` — candidate, scope global | no |  |
| Cisco | Cisco; Cisco India — rows 58, 59 | yes | none | yes | unsupported | custom `https://jobs.cisco.com` — unsupported, scope unknown | yes | The careers site could not be reached in the 15 Nov audit (TLS or network error), so its vacancy provider is unknown; needs a manual look before an adapter can be chosen |
| Citi | Citi / Citi India; Citi India; Citibank India — rows 60, 61, 62 | yes | workday `citi/2` | no | configured | workday `citi/wd5/2` — verified, scope global | no |  |
| CNH | CNH — rows 63 | missing | none | no | configured | successfactors `join.cnh.com` — candidate, scope global | no |  |
| CNO Financial | CNO Financial; CNO Financial India — rows 64, 65 | yes | workday `cnoinc/Careers` | no | configured | workday `cnoinc/wd5/Careers` — verified, scope global | no |  |
| Coca-Cola | Coca-Cola India — rows 66 | yes | none | no | configured | workday `coke/wd1/coca-cola-careers` — candidate, scope global | no |  |
| Cohere Health | Cohere Health — rows 67 | missing | none | no | configured | greenhouse `coherehealth` — candidate, scope global | no |  |
| Columbia Sportswear | Columbia Sportswear Company — rows 68 | missing | none | no | wrong scope only | workday `columbiasportswearcompany/wd5/retail` — wrong scope, scope global | no | Retail-store board for the United States; no corporate or India board is evidenced |
| Comcast | Comcast; Comcast India — rows 69, 70 | yes | workday `comcast/Comcast_Careers` | no | configured | workday `comcast/wd115/Comcast_Careers` — verified, scope global | no |  |
| Commonwealth Bank | CBA; Commonwealth Bank; Commonwealth Bank India — rows 54, 71, 72 | yes | workday `cba/CommBank_Careers` | yes | configured | workday `cba/wd3/CommBank_Careers` — verified, scope global | yes |  |
| Conduent | Conduent India — rows 73 | yes | none | no | configured | phenom `careers.conduent.com/us/en` — candidate, scope global | no |  |
| Confluent | IBM · Confluent support — rows 137 | related entry only | none | no | configured | ashby `confluent` — candidate, scope global | no | Only Confluent's own board is evidenced; Confluent is kept as its own entry under parent IBM, and IBM-wide roles are not covered by it |
| CSC | CSC (Corporation Service Company) (×2) — rows 75, 76 | yes | oracle `hczw.fa.us2.oraclecloud.com/CX_1001` | yes | configured | oracle `hczw.fa.us2.oraclecloud.com CX_1001` — verified, scope global | yes |  |
| Cummins | Cummins India — rows 77 | yes | none | no | configured | oracle `fa-espx-saasfaprod1.fa.ocs.oraclecloud.com CX_1` — candidate, scope global | no |  |
| CVS Health | CVS Health / Aetna; CVS Health India — rows 78, 79 | yes | none | no | configured | workday `cvshealth/wd1/CVS_Health_Careers` — candidate, scope global | no |  |
| Daimler Truck | Daimler Truck India (×2); Daimler Truck Innovation Center India — rows 81, 82, 83 | yes | none | yes | configured | beesite `https://global-jobboard-api-jobsearch.daimlertruck.com/search/` — candidate, scope global | yes |  |
| Danske Bank | Danske Bank — rows 84 | missing | none | no | configured | oracle `ejqi.fa.ocs.oraclecloud.eu CX_1001` — candidate, scope global | no |  |
| Dell Technologies | Dell India; Dell Technologies India — rows 85, 86 | yes | none | yes | configured | oracle `enterpriseplatform.dell.com careers` — candidate, scope global | yes |  |
| Deutsche Bank | Deutsche Bank; Deutsche Bank India — rows 87, 88 | yes | none | no | configured | beesite `https://api-deutschebank.beesite.de/search/` — candidate, scope global | no |  |
| Deutsche Telekom Digital Labs | Deutsche Telekom Digital Labs — rows 89 | missing | none | no | configured | smartrecruiters `DeutscheTelekom` — candidate, scope global | no |  |
| DHL | DHL India; DHL IT Services — rows 90, 91 | yes | none | no | unsupported | custom `https://careers.dhl.com` — unsupported, scope unknown | no | The careers site could not be reached in the 15 Nov audit (TLS or network error), so its vacancy provider is unknown; needs a manual look before an adapter can be chosen |
| DP World | DP World — rows 92 | yes | oracle `ehpv.fa.em2.oraclecloud.com/CX_1` | no | configured | oracle `ehpv.fa.em2.oraclecloud.com CX_1` — verified, scope global | no |  |
| Eaton | Eaton — rows 93 | missing | none | no | configured | eightfold `eaton.eightfold.ai` — candidate, scope global | no |  |
| Empower | Empower India (×2) — rows 96, 97 | yes | workday `empower/empower` | yes | configured | workday `empower/wd12/empower` — verified, scope global | yes |  |
| enGen | enGen / Highmark; enGen / Highmark India (×2) — rows 98, 99, 100 | yes | workday `highmarkhealth/highmark` | no | configured | workday `highmarkhealth/wd1/highmark` — verified, scope global | no |  |
| Estes Express | Estes Express; Estes Express India — rows 101, 102 | missing | none | no | configured | oracle `ecwr.fa.us2.oraclecloud.com CX_1` — candidate, scope global | no |  |
| Evernorth | Evernorth / Cigna; Evernorth / Cigna India — rows 103, 104 | yes | workday `cigna/cignacareers` | no | configured | workday `cigna/wd5/cignacareers` — verified, scope global | no |  |
| ExxonMobil | ExxonMobil; ExxonMobil India — rows 105, 106 | missing | none | no | configured | successfactors `jobs.exxonmobil.com` — candidate, scope global | no |  |
| FedEx | FedEx India — rows 107 | yes | none | no | unsupported | paradox `careers.fedex.com` — unsupported, scope unknown | no | Paradox career site: jobs are rendered from script and no public feed is known |
| Fidelity Investments | Fidelity India; Fidelity Investments — rows 108, 109 | yes | workday `fmr/FidelityCareers` | no | configured | workday `fmr/wd1/FidelityCareers` — verified, scope global | no |  |
| Fidelity National Financial | Fidelity National Financial India (FNF) — rows 110 | yes | workday `fntg/FNF-Careers` | yes | configured | workday `fntg/wd5/FNF-Careers` — verified, scope global | yes |  |
| First Citizens Bank | First Citizens Bank (×2); First Citizens Bank India — rows 111, 112, 113 | yes | workday `svb/firstcitizensindia` | yes | configured | workday `svb/wd5/firstcitizensindia` — verified, scope india | yes |  |
| FIS | FIS (TSYS); FIS India (×2) — rows 114, 115, 116 | yes | workday `fis/SearchJobs` | no | configured | workday `fis/wd5/SearchJobs` — verified, scope global | no | The old label joins two employers; it is mapped to FIS (its saved URL). TSYS belongs to Global Payments and is covered there as a business unit |
| Fiserv | Fiserv; Fiserv India — rows 117, 118 | yes | workday `fiserv/EXT` | no | configured | workday `fiserv/wd5/EXT` — verified, scope global | no |  |
| Ford | Ford; Ford Business Solutions India; Ford India (FBS); Ford Motor Company — rows 119, 120, 122, 123 | yes | none | no | unsupported | custom `https://corporate.ford.com/careers.html` — unsupported, scope unknown | no | The careers site refused the 15 Nov audit request (HTTP 403); respected, not worked around. No public feed is known |
| Ford Credit | Ford Credit — rows 121 | related entry only | none | no | unsupported | custom `https://corporate.ford.com/careers.html` — unsupported, scope unknown | no | The careers site refused the 15 Nov audit request (HTTP 403); respected, not worked around. No public feed is known Business unit of Ford, kept as its own entry; Ford's configuration does not establish Ford Credit coverage |
| GE Aerospace | GE Aerospace — rows 124 | missing | none | no | configured | workday `geaerospace/wd5/GE_ExternalSite` — candidate, scope global | no |  |
| GE HealthCare | GE Healthcare India — rows 125 | yes | workday `gehc/GEHC_ExternalSite` | yes | configured | workday `gehc/wd5/GEHC_ExternalSite` — verified, scope global | yes |  |
| GE Vernova | GE Vernova — rows 126 | missing | none | no | configured | workday `gevernova/wd5/Vernova_ExternalSite` — candidate, scope global | no |  |
| General Motors | General Motors India — rows 127 | yes | none | no | configured | workday `generalmotors/wd5/Careers_GM` — candidate, scope global | no |  |
| Global Payments | Global Payments / TSYS India; Global Payments India — rows 128, 129 | yes | none | no | configured | workday `tsys/wd1/TSYS` — candidate, scope global, business unit TSYS | no |  |
| Goldman Sachs | Goldman Sachs; Goldman Sachs India — rows 130, 131 | yes | none | yes | unsupported | custom `https://higher.gs.com/results` — unsupported, scope unknown | yes | Script-driven job search with no public feed identified; needs a site-specific client |
| HDFC Bank | HDFC Bank — rows 133 | yes | none | no | unsupported | ripplehire `hdfcbank.ripplehire.com` — unsupported, scope india | no | RippleHire portal: listings load with a per-portal token and session, which this project does not handle |
| Honeywell | Honeywell — rows 134 | missing | none | no | configured | oracle `ibqbjb.fa.ocs.oraclecloud.com CX_1` — candidate, scope global | no |  |
| HSBC | HSBC; HSBC India — rows 135, 136 | yes | none | yes | configured | avature `mycareer.hsbc.com/en_GB/external` — candidate, scope global | yes |  |
| ICICI Bank | ICICI Bank — rows 138 | yes | none | no | unsupported | custom `https://careers.icici.bank.in/CareerApplicant/Career/job-listing/` — unsupported, scope unknown | no | Bank-built careers application; needs a site-specific parser |
| IFFCO Tokio | IFFCO Tokio; IFFCO Tokio India — rows 139, 140 | yes | none | no | unsupported | custom `https://www.iffcotokio.co.in/about-us/careers` — unsupported, scope unknown | no | Careers page without a searchable job feed |
| IKEA | IKEA — rows 141 | missing | none | no | configured | talentbrew `jobs.ikea.com/en` — candidate, scope global | no |  |
| ING | ING — rows 142 | yes | none | no | unsupported | custom `https://www.ing.jobs` — unsupported, scope unknown | no | The careers site could not be reached in the 15 Nov audit (TLS or network error), so its vacancy provider is unknown; needs a manual look before an adapter can be chosen |
| Intel | Intel India (×2) — rows 143, 144 | yes | workday `intel/External` | yes | configured | workday `intel/wd1/External` — verified, scope global | yes |  |
| ITC Limited | ITC Limited (×2) — rows 145, 146 | yes | none | no | unsupported | custom `https://recruitment.itcportal.com/jobs/Careers` — unsupported, scope unknown | no | Zoho Recruit careers site; no Zoho Recruit adapter exists |
| JLR | JLR — rows 148 | missing | none | no | configured | successfactors `www.jaguarlandrovercareers.com` — candidate, scope global | no |  |
| John Deere | John Deere India — rows 150 | yes | none | no | configured | successfactors `jobs.deere.com` — candidate, scope global | no |  |
| John Deere Financial | John Deere Financial — rows 149 | related entry only | none | no | not configured | — | no | Business unit of John Deere, kept as its own entry No separate portal is evidenced; John Deere's board may list its roles but does not establish coverage. |
| Johnson & Johnson | Johnson & Johnson India — rows 151 | yes | workday `jj/JJ` | no | configured | workday `jj/wd5/JJ` — verified, scope global | no |  |
| Johnson Controls | JCI — rows 147 | yes | workday `jci/JCI` | no | configured | workday `jci/wd5/JCI` — verified, scope global | no |  |
| JPMorganChase | JPMorgan Chase & Co.; JPMorgan Chase India; JPMorganChase — rows 152, 153, 154 | yes | oracle `jpmc.fa.oraclecloud.com/CX_1001` | yes | configured | oracle `jpmc.fa.oraclecloud.com CX_1001` — verified, scope global | yes |  |
| Komatsu | Komatsu — rows 155 | missing | none | no | unsupported | custom `https://www.komatsu.com/en-us/careers` — unsupported, scope unknown | no | Marketing careers page; no job feed identified |
| Kotak Mahindra Bank | Kotak Mahindra Bank — rows 156 | yes | oracle `hcbt.fa.em2.oraclecloud.com/CX` | no | configured | oracle `hcbt.fa.em2.oraclecloud.com CX` — verified, scope global | no |  |
| Levi Strauss & Co. | Levi Strauss & Co. India (×2); Levi Strauss India — rows 157, 158, 159 | yes | workday `levistraussandco/External` | yes | configured | workday `levistraussandco/wd5/External` — verified, scope global | yes |  |
| Liberty Mutual | Liberty Mutual India — rows 160 | yes | none | no | configured | eightfold `searchjobs.libertymutualgroup.com` — candidate, scope global | no |  |
| Lloyds Banking Group | Lloyds Banking; Lloyds Banking Group; Lloyds Banking Group India; Lloyds Technology Centre India — rows 161, 162, 163, 164 | yes | workday `lbg/LBG_Careers` | no | configured | workday `lbg/wd3/LBG_Careers + Lloyds_Technology_Centre` — verified, scope global | no |  |
| Lockheed Martin | Lockheed Martin India — rows 165 | yes | none | no | unsupported | custom `https://lockheedmartinjobs.com` — unsupported, scope unknown | no | Only a redirect script was reachable; vacancy provider not identified |
| Lowe's | Lowe’s — rows 166 | yes | workday `lowes/LWS_External_CS` | no | configured | workday `lowes/wd5/LWS_External_CS` — verified, scope global | no |  |
| LPL Financial | LPL Financial India — rows 167 | yes | none | no | configured | workday `lplfinancial/wd1/External` — candidate, scope global | no |  |
| Lufthansa Systems | Lufthansa Systems India — rows 168 | missing | none | no | unsupported | custom `https://www.lhsystems.com/career` — unsupported, scope unknown | no | Careers page without a known vacancy provider; needs a site-specific parser |
| Maersk | A.P. Moller - Maersk; Maersk GSC; Maersk India — rows 1, 169, 170 | yes | workday `maersk/Maersk_Careers` | no | configured | workday `maersk/wd3/Maersk_Careers` — verified, scope global | no |  |
| Manulife | Manulife India — rows 171 | yes | none | no | configured | workday `manulife/wd3/MFCJH_Jobs` — candidate, scope global | no |  |
| Marsh McLennan | Marsh McLennan India; Marsh McLennan India (MMGS) (×2) — rows 172, 173, 174 | yes | none | no | configured | phenom `careers.marsh.com/global/en` — candidate, scope global | no |  |
| MassMutual | MassMutual India — rows 175 | missing | none | no | configured | talentbrew `careers.massmutual.com` — candidate, scope global | no |  |
| Mastercard | Mastercard India — rows 176 | yes | workday `mastercard/CorporateCareers` | no | configured | workday `mastercard/wd1/CorporateCareers` — verified, scope global | no |  |
| Maximus | Maximus India — rows 177 | yes | none | no | configured | avature `maximus.avature.net/careers` — candidate, scope global | no |  |
| Medtronic | Medtronic; Medtronic India — rows 178, 179 | yes | none | no | configured | workday `medtronic/wd1/MedtronicCareers` — candidate, scope global | no |  |
| Mercedes-Benz Group | Daimler AG (Mercedes parent) — rows 80 | related entry only | none | no | configured | beesite `https://jobs.api.mercedes-benz.com/search` — candidate, scope global | no | Parent company (formerly Daimler AG); kept separate from Mercedes-Benz Research and Development India and from Daimler Truck |
| Mercedes-Benz Mobility | Mercedes-Benz Mobility AG — rows 180 | related entry only | none | no | configured | beesite `https://jobs.api.mercedes-benz.com/search` — candidate, scope global, business unit Mercedes-Benz Mobility | no | Separate business of Mercedes-Benz Group; not the India R&D centre |
| Mercedes-Benz Research and Development India | Mercedes-Benz R&D India (×2) — rows 181, 182 | yes | none | no | configured | beesite `https://jobs.api.mercedes-benz.com/search` — candidate, scope global, business unit Mercedes-Benz Research and Development India | no | The user's current employer. |
| Merck | Merck India; MSD / Merck Sharp & Dohme — rows 183, 192 | yes | workday `msd/SearchJobs` | no | configured | workday `msd/wd5/SearchJobs` — verified, scope global | no |  |
| MetLife | MetLife India; MetLife India GCC; MetLife MGCC — rows 184, 185, 186 | yes | none | no | configured | avature `www.metlifecareers.com/en_US/ml` — candidate, scope global | no |  |
| Mizuho Financial Group | Mizuho — rows 187 | related entry only | none | no | unsupported | custom `https://www.mizuhogroup.com/careers` — unsupported, scope unknown | no | Marketing careers page; no job feed identified Parent group; Mizuho Global Services (India) is a separate entry |
| Mizuho Global Services | Mizuho Global Services India (MGS) — rows 188 | yes | none | no | unsupported | custom `https://www.mizuhogroup.com/careers` — unsupported, scope unknown | no | Marketing careers page; no job feed identified for the India centre |
| Mondelez | Mondelez India — rows 189 | yes | none | no | configured | workday `mdlz/wd3/External` — candidate, scope global | no |  |
| Morgan Stanley | Morgan Stanley; Morgan Stanley India — rows 190, 191 | yes | workday `ms/External` | yes | configured | workday `ms/wd5/External` — verified, scope global | yes |  |
| MUFG | MUFG; MUFG Global Service — rows 193, 194 | yes | workday `mufgub/MUFG-Careers` | yes | configured | workday `mufgub/wd3/MUFG-Careers` — verified, scope global | yes |  |
| MUFG Pension & Market Services | MUFG Pension & Market Services (Link Group); MUFG Pension & Market Svcs — rows 195, 196 | yes | oracle `hcmn.fa.ap1.oraclecloud.com/CX_1001` | no | configured | oracle `hcmn.fa.ap1.oraclecloud.com CX_1001` — verified, scope global | no |  |
| National Australia Bank | NAB; NAB Innovation Centre India — rows 197, 198 | yes | none | no | configured | eightfold `nab.eightfold.ai` — candidate, scope global | no |  |
| NatWest Group | NatWest Group; NatWest Group India — rows 199, 200 | yes | none | yes | configured | workday `rbs/wd3/RBS` — candidate, scope global | yes |  |
| Navistar | Navistar; Navistar / International Motors; Navistar India — rows 201, 202, 203 | yes | none | no | configured | icims `careers.international.com` — candidate, scope global | no |  |
| Nike | Nike India; Nike India (ITC) — rows 204, 205 | yes | workday `nike/nke` | yes | configured | workday `nike/wd1/nke + nke2` — verified, scope global | yes |  |
| Nokia | Nokia India (×2) — rows 206, 207 | yes | none | yes | configured | oracle `fa-evmr-saasfaprod1.fa.ocs.oraclecloud.com CX_1` — candidate, scope global | yes |  |
| Northern Trust | Northern Trust; Northern Trust India — rows 208, 209 | yes | workday `ntrs/northerntrust` | yes | configured | workday `ntrs/wd1/northerntrust` — verified, scope global | yes |  |
| Novartis | Novartis India — rows 210 | yes | none | no | unsupported | custom `https://www.novartis.com/careers/career-search` — unsupported, scope unknown | no | Site-built career search (Drupal); needs a site-specific parser |
| Optum | Optum / UHG; Optum / UHG India (×2); Optum / UnitedHealth Group India; Optum / UnitedHealth India — rows 211, 212, 213, 214, 215 | yes | none | no | configured | talentbrew `careers.unitedhealthgroup.com` — candidate, scope global | no |  |
| Orange Business | Orange Business — rows 216 | yes | none | yes | configured | phenom `orange.jobs/gb/en` — candidate, scope global | yes |  |
| PayPal | PayPal India — rows 217 | yes | workday `paypal/jobs` | yes | configured | workday `paypal/wd1/jobs` — verified, scope global | yes |  |
| Pegasystems | Pegasystems — rows 218 | yes | none | yes | unsupported | custom `https://www.pega.com/about/careers/job-listings` — unsupported, scope unknown | yes | Pega's own job-listings page; no known vacancy provider was identified, so it needs a site-specific parser |
| PepsiCo | PepsiCo India — rows 219 | yes | none | no | configured | icims `www.pepsicojobs.com/main` — candidate, scope global | no |  |
| Pfizer | Pfizer India — rows 220 | yes | workday `pfizer/PfizerCareers` | no | configured | workday `pfizer/wd1/PfizerCareers` — verified, scope global | no |  |
| Philips | Philips; Philips India — rows 221, 222 | yes | workday `philips/jobs-and-careers` | no | configured | workday `philips/wd3/jobs-and-careers` — verified, scope global | no |  |
| PNC | PNC India — rows 223 | yes | none | no | configured | workday `pnc/wd5/External` — candidate, scope global | no |  |
| Prime Therapeutics | Prime Therapeutics — rows 224 | yes | workday `primetherapeutics/PrimeTherapeuticsCareers` | no | configured | workday `primetherapeutics/wd1/PrimeTherapeuticsCareers` — verified, scope global | no |  |
| Procter & Gamble | Procter & Gamble India — rows 225 | yes | none | no | configured | workday `pg/wd5/1000` — candidate, scope global | no |  |
| Proximus | Proximus — rows 226 | yes | none | no | configured | phenom `jobs.proximus.com/be/en` — candidate, scope global | no |  |
| PwC | PwC Advisory GCC — rows 227 | yes | workday `pwc/Global_Experienced_Careers` | no | configured | workday `pwc/wd3/Global_Experienced_Careers` — verified, scope global | no | Mapped to PwC, whose global Workday board is configured; a separate Advisory GCC entity is not established by the research The original target "PwC Advisory GCC" is mapped here; a separate Advisory GCC entity is not established. |
| Qualcomm | Qualcomm — rows 228 | missing | none | no | configured | eightfold `careers.qualcomm.com` — candidate, scope global | no |  |
| Rabobank | Rabobank — rows 229 | missing | none | no | unsupported | custom `https://www.rabobank.jobs` — unsupported, scope unknown | no | The careers site refused the 15 Nov audit request (HTTP 403); respected, not worked around. No public feed is known |
| Renault Nissan Technology | Renault-Nissan Tech; Renault-Nissan Tech India — rows 230, 231 | yes | none | no | not configured | — | no | No dedicated India board is evidenced; the Renault Group board is configured on the parent entry. |
| Roche | Roche India — rows 232 | yes | none | no | configured | workday `roche/wd3/roche-ext` — candidate, scope global | no |  |
| Rolls-Royce | Rolls-Royce — rows 233 | missing | none | no | unsupported | custom `https://careers.rolls-royce.com/en/jobs` — unsupported, scope unknown | no | Careers site without a known vacancy provider; needs a site-specific parser |
| S&P Global | S&P Global India — rows 234 | yes | workday `spgi/SPGI_Careers` | no | configured | workday `spgi/wd5/SPGI_Careers` — verified, scope global | no |  |
| Schneider Electric | Schneider Electric — rows 235 | missing | none | no | configured | smartrecruiters `SchneiderElectric2` — candidate, scope global | no |  |
| Shell | Shell India — rows 236 | yes | workday `shell/ShellCareers` | yes | configured | workday `shell/wd3/ShellCareers` — verified, scope global | yes |  |
| Siemens | Siemens; Siemens India — rows 237, 238 | yes | none | yes | unsupported | custom `https://jobs.siemens.com/careers` — unsupported, scope unknown | yes | The careers site could not be reached in the 15 Nov audit (TLS or network error), so its vacancy provider is unknown; needs a manual look before an adapter can be chosen |
| SLB | SLB — rows 239 | missing | none | no | unsupported | custom `https://careers.slb.com` — unsupported, scope unknown | no | Search runs on a hosted search service (Coveo) that needs site keys; no public feed identified |
| Societe Generale | Societe Generale; Societe Generale GSC India; Societe Generale India; Société Générale GSC — rows 240, 241, 242, 243 | yes | none | yes | unsupported | taleo `careers.societegenerale.com` — unsupported, scope unknown | yes | Site-built search over a Taleo back end: Taleo career sections need a session-bound search, which this project does not do |
| Standard Chartered | Standard Chartered; Standard Chartered India — rows 244, 245 | yes | none | yes | configured | successfactors `jobs.standardchartered.com` — candidate, scope global | yes |  |
| State Street | State Street; State Street India — rows 246, 247 | yes | workday `statestreet/Global` | no | configured | workday `statestreet/wd1/Global` — verified, scope global | no |  |
| Stellantis | Stellantis India — rows 248 | yes | none | no | unsupported | custom `https://careers.stellantis.com/job-search-results/?keyword=pega` — unsupported, scope unknown | no | Search is served by a third-party jobs API loaded by script; needs a site-specific client |
| Sun Life | Sun Life / SLGS; Sun Life Financial; Sun Life India; Sun Life India GCC — rows 249, 250, 251, 252 | yes | workday `sunlife/Experienced-Jobs` | yes | configured | workday `sunlife/wd3/Experienced-Jobs` — verified, scope global | yes |  |
| Synchrony | Synchrony; Synchrony India — rows 253, 254 | yes | workday `synchronyfinancial/careers` | no | configured | workday `synchronyfinancial/wd5/careers` — verified, scope global | no |  |
| T-Mobile | T-Mobile / TMUS Global Solutions — rows 255 | missing | none | no | unsupported | custom `https://talent500.com/t-mobile/careers/india/` — unsupported, scope unknown | no | India hiring runs through a partner page (Talent500); no public feed identified |
| Target | Target; Target in India — rows 256, 257 | yes | workday `target/targetcareers` | no | configured | workday `target/wd5/targetcareers` — verified, scope global | no |  |
| Telstra | Telstra India — rows 258 | yes | workday `telstra/Telstra_Careers` | yes | configured | workday `telstra/wd3/Telstra_Careers` — verified, scope global | yes |  |
| Tesco | Tesco Bengaluru (×2) — rows 259, 260 | yes | none | yes | configured | avature `careers.tesco.com/en_GB/careers` — candidate, scope global | yes |  |
| The Hartford | Hartford India GCC; The Hartford India (×2) — rows 132, 261, 262 | yes | workday `thehartford/Careers_External` | no | configured | workday `thehartford/wd5/Careers_External` — verified, scope global | no |  |
| Toyota | Toyota India — rows 264 | yes | none | no | wrong scope only | workday `toyota/wd503/TMNA` — wrong scope, scope global | no | Toyota Motor North America board; it cannot cover India roles |
| Toyota Financial Services | Toyota / TFS — rows 263 | related entry only | none | no | wrong scope only | phenom `careers.toyota.com/us/en` — wrong scope, scope global | no | Toyota North America careers site; it cannot cover India roles Business unit of Toyota, kept as its own entry; its only evidenced careers site is North American |
| U.S. Bank | U.S. Bank India — rows 265 | yes | workday `usbank/US_Bank_Careers` | no | configured | workday `usbank/wd1/US_Bank_Careers` — verified, scope global | no |  |
| UBS | Credit Suisse / UBS India; UBS — rows 74, 266 | yes | none | no | unsupported | brassring `jobs.ubs.com` — unsupported, scope unknown | no | BrassRing talent gateway: its search needs a session-bound partner and site token; part of the site also refused the audit (HTTP 403) |
| Unilever | Unilever; Unilever / UniOps; Unilever India — rows 267, 268, 269 | yes | workday `unilever/Unilever_Experienced_Professionals` | yes | configured | workday `unilever/wd3/Unilever_Experienced_Professionals` — verified, scope global | yes |  |
| UPS | UPS; UPS India — rows 270, 271 | yes | none | no | configured | phenom `www.jobs-ups.com/imea/en` — candidate, scope global | no |  |
| Verizon | Verizon; Verizon India — rows 272, 273 | yes | workday `verizon/verizon-careers` | yes | configured | workday `verizon/wd12/verizon-careers` — verified, scope global | yes |  |
| Visa | Visa India — rows 274 | yes | none | no | configured | smartrecruiters `Visa` — candidate, scope global | no |  |
| Vodafone | Vodafone / VOIS; Vodafone / VOIS India — rows 275, 276 | yes | none | yes | unsupported | custom `https://careers.vodafone.com` — unsupported, scope unknown | yes | Vacancy provider not identified on the careers page |
| Vodafone Idea | Vodafone Idea — rows 277 | missing | none | no | configured | successfactors `careers.vodafoneidea.com` — candidate, scope india | no |  |
| Volvo Cars | Volvo Cars — rows 278 | missing | none | no | configured | successfactors `jobs.volvocars.com` — candidate, scope global | no |  |
| Voya Financial | Voya Financial India — rows 279 | yes | workday `godirect/voya_jobs` | no | configured | workday `godirect/wd5/voya_jobs` — verified, scope global | no |  |
| VW Digital Solutions | VW Digital Solutions — rows 280 | missing | none | no | not configured | — | no | No careers portal is evidenced: the saved URL belongs to CARIAD, a different Volkswagen software company. |
| Walmart Global Tech | Walmart Global Tech India — rows 281 | missing | none | no | configured | workday `walmart/wd504/WalmartExternal` — candidate, scope global | no |  |
| Wells Fargo | Wells Fargo (×2); Wells Fargo India — rows 282, 283, 284 | yes | workday `wf/WellsFargoJobs` | yes | configured | workday `wf/wd1/WellsFargoJobs` — verified, scope global | yes |  |
| Western Union | Western Union India — rows 285 | yes | workday `westernunion/WesternUnionJobs` | no | configured | workday `westernunion/wd5/WesternUnionJobs` — verified, scope global | no |  |
| Zurich Insurance | Zurich Insurance India — rows 286 | yes | none | no | configured | successfactors `www.careers.zurich.com` — candidate, scope global | no |  |
