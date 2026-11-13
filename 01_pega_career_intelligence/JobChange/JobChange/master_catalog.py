"""Conserve historical source observations alongside dated independent research.

Profile URLs identify profiles, not confirmed current employees. The raw source ledger
is retained so a refresh cannot silently shrink the directory or erase old observations.
"""
import copy, hashlib, json, re
from pathlib import Path
from urllib.parse import urlsplit, unquote
from collections import Counter
from directory_data import ALIASES
from opportunity_data import company_key

BASE=Path(__file__).resolve().parent

CURATED_SCAN_TARGETS=[
    {'target_id':'gcc-bd-becton-dickinson','name':'BD / Becton Dickinson','category':'gcc','location':'India',
     'keywords':['BD','Becton Dickinson','Becton Dickinson India','BD India'],
     'career_url':'https://jobs.bd.com/en/location/india-jobs/159/1269750/2',
     'priority':'top30','catalog_scope':'curated',
     'location_basis':'Curated India scan target; BD Technology Campus has Bengaluru roles.'},
    {'target_id':'gcc-cohere-health','name':'Cohere Health','category':'gcc','location':'India',
     'keywords':['Cohere Health','Cohere Health Hyderabad','Cohere Pega','Cohere clinical configuration','Cohere data migration'],
     'career_url':'https://job-boards.greenhouse.io/coherehealth',
     'priority':'gcc','catalog_scope':'curated',
     'location_basis':'Curated healthcare automation target; retain only postings with role-detail Pega/platform evidence.'},
    {'target_id':'gcc-msd-merck-sharp-dohme','name':'MSD / Merck Sharp & Dohme','category':'gcc','location':'India',
     'keywords':['MSD','Merck Sharp Dohme','Merck Sharp & Dohme','Merck India','Senior Pega Engineer'],
     'career_url':'https://jobs.merck.com',
     'priority':'gcc','catalog_scope':'curated','allow_duplicate':True,
     'location_basis':'Curated MSD alias target; generic Merck search may miss MSD-branded Pega postings.'},
    {'target_id':'gcc-pwc-advisory','name':'PwC Advisory GCC','category':'gcc','location':'India',
     'keywords':['PwC Advisory GCC','PwC GCC Advisory Hyderabad','PwC healthcare GCC Pega','PwC Azure Cloud Solutions Pega','PwC Pega Platform integration'],
     'career_url':'https://pwc.wd3.myworkdayjobs.com/en-US/Global_Experienced_Careers?locationCountry=16dcc53e4691011e83255a4483077800',
     'priority':'gcc','catalog_scope':'curated','allow_duplicate':True,
     'location_basis':'Curated advisory GCC target; captures healthcare cloud/integration roles where Pega appears in the JD.'},
    {'target_id':'services-ntt-data-north-america','name':'NTT DATA North America','category':'services','location':'India',
     'keywords':['NTT DATA North America','NTT DATA Pega Bangalore','NTT DATA Senior Pega Developer','NTT DATA Pega India'],
     'priority':'si_top','catalog_scope':'curated','allow_duplicate':True,
     'location_basis':'Evidence-backed target from repeated India/Bengaluru Senior Pega Developer postings.'},
    {'target_id':'services-tenth-revolution-group','name':'Tenth Revolution Group','category':'services','location':'India',
     'keywords':['Tenth Revolution Group','Tenth Revolution Pega','Tenth Revolution Pega Developer India','Tenth Revolution Pega Bengaluru'],
     'priority':'si_mid','catalog_scope':'curated','allow_duplicate':True,
     'location_basis':'Evidence-backed target from Hyderabad and Bengaluru Pega Developer postings.'},
    {'target_id':'services-vmc-soft-technologies','name':'VMC Soft Technologies','category':'services','location':'India',
     'keywords':['VMC Soft Technologies','VMC Soft Technologies Inc','VMC Soft Technologies, Inc','VMC Soft Pega','VMC Soft Pega Developer Bengaluru','VMC Soft PEGA Developer Karnataka'],
     'priority':'si_mid','catalog_scope':'curated','allow_duplicate':True,
     'location_basis':'Evidence-backed target from Bengaluru/Karnataka Pega Developer postings.'},
    {'target_id':'services-talent-toppers','name':'Talent Toppers','category':'services','location':'India',
     'keywords':['Talent Toppers','Talent Toppers Pega','Talent Toppers Pega Developer Bengaluru'],
     'priority':'si_mid','catalog_scope':'curated','allow_duplicate':True,
     'location_basis':'Evidence-backed target from Bengaluru Pega Developer Assistant Manager postings.'},
    {'target_id':'services-revolent-group','name':'Revolent Group','category':'services','location':'India',
     'keywords':['Revolent Group','Revolent Pega','Revolent Senior Pega Developer Hyderabad'],
     'priority':'si_mid','catalog_scope':'curated','allow_duplicate':True,
     'location_basis':'Evidence-backed target from Hyderabad Senior Pega Developer postings.'},
    {'target_id':'gcc-columbia-sportswear','name':'Columbia Sportswear Company','category':'gcc','location':'India',
     'keywords':['Columbia Sportswear Company','Columbia Sportswear Pega','Columbia Sportswear PEGA BPM Bengaluru'],
     'priority':'gcc','catalog_scope':'curated','allow_duplicate':True,
     'location_basis':'Evidence-backed target from Bengaluru Senior Automation Engineer - PEGA BPM posting.'},
    {'target_id':'gcc-mizuho','name':'Mizuho','category':'gcc','location':'India',
     'keywords':['Mizuho','Mizuho Global Services','Mizuho Pega','Mizuho Sr Pega Developer Chennai'],
     'priority':'gcc','catalog_scope':'curated','allow_duplicate':True,
     'location_basis':'Evidence-backed target from Mizuho Global Services Sr Pega Developer posting in Chennai.'},
    {'target_id':'services-process360','name':'Process360 Ltd','category':'services','location':'India',
     'keywords':['Process360','Process360 Ltd','Process360 Pega','Process360 CLSA','Process360 CSSA'],
     'priority':'si_mid','catalog_scope':'curated','allow_duplicate':True,
     'location_basis':'Evidence-backed target from Pega CLSA/CSSA postings in India.'},
    {'target_id':'services-acira-consultancy','name':'Acira Consultancy','category':'services','location':'India',
     'keywords':['Acira Consultancy','Acira Consultancy Pty Ltd','Acira Consultancy Pega','Acira Pega Senior System Analyst Bengaluru'],
     'priority':'si_mid','catalog_scope':'curated','allow_duplicate':True,
     'location_basis':'Evidence-backed target from Bengaluru Pega Senior System Analyst posting.'},
    {'target_id':'services-religent-systems','name':'Religent Systems','category':'services','location':'India',
     'keywords':['Religent Systems','Religent Pega','Religent Pega Constellation Hyderabad'],
     'priority':'si_mid','catalog_scope':'curated','allow_duplicate':True,
     'location_basis':'Evidence-backed target from Hyderabad Pega Constellation Developer posting.'},
    {'target_id':'services-innovationteam','name':'InnovationTeam','category':'services','location':'India',
     'keywords':['InnovationTeam','InnovationTeam Pega','InnovationTeam Senior Pega Engineer Hyderabad'],
     'priority':'si_mid','catalog_scope':'curated','allow_duplicate':True,
     'location_basis':'Evidence-backed target from Hyderabad Senior Pega Engineer posting.'},
    {'target_id':'services-allime-tech','name':'Allime Tech Solutions','category':'services','location':'India',
     'keywords':['Allime Tech Solutions','Allime Tech Pega','Allime PEGA Testing Bangalore'],
     'priority':'si_mid','catalog_scope':'curated','allow_duplicate':True,
     'location_basis':'Evidence-backed target from Bangalore PEGA Testing posting.'},
    {'target_id':'services-digitalxnode','name':'DigitalXNode','category':'services','location':'India',
     'keywords':['DigitalXNode','DigitalXNode Pega','DigitalXNode Pega BPM Consultant Bagalur'],
     'priority':'si_mid','catalog_scope':'curated','allow_duplicate':True,
     'location_basis':'Evidence-backed target from Bagalur/Karnataka Pega BPM Consultant posting.'},
    {'target_id':'gcc-rabobank','name':'Rabobank','category':'gcc','location':'India',
     'keywords':['Rabobank','Rabobank Pega','Rabobank Pega India','Rabobank Pega KYC CLM'],
     'priority':'gcc','catalog_scope':'curated','allow_duplicate':True,
     'location_basis':'Evidence-backed target from Pega KYC/CLM and agentic API platform claims.'},
    {'target_id':'gcc-metlife-india-gcc','name':'MetLife India GCC','category':'gcc','location':'India',
     'keywords':['MetLife India GCC','MetLife India Pega','MetLife Pega Constellation','MetLife intelligent automation'],
     'priority':'gcc','catalog_scope':'curated','allow_duplicate':True,
     'location_basis':'Evidence-backed alias target for MetLife India GCC Pega Constellation/intelligent automation evidence.'},
]

CAREER_URL_OVERRIDES={
    'CSC (Corporation Service Company)':'https://www.cscglobal.com/service/careers/',
    'Danske Bank':'https://danskebank.com/Job',
    'Lloyds Banking Group':'https://lloydstechnologycentre.com/our-roles',
    'Daimler Truck India':'https://locations.daimlertruck.com/en/career/locations/detail/bengaluru-daimler-truck-innovation-center-india-private-limited',
    'Daimler Truck Innovation Center India':'https://locations.daimlertruck.com/en/career/locations/detail/bengaluru-daimler-truck-innovation-center-india-private-limited',
    'Ford Motor Company':'https://corporate.ford.com/careers.html',
    'Intel India':'https://jobs.intel.com',
    'Northern Trust':'https://www.northerntrust.com/united-states/careers',
    'Societe Generale GSC India':'https://careers.societegenerale.com/en',
    'UBS':'https://www.ubs.com/global/en/careers.html',
    'NAB':'https://www.nab.com.au/about-us/careers',
    'MUFG':'https://www.mufg.jp/english/careers/index.html',
    'Synchrony':'https://www.synchronycareers.com',
    'AXA':'https://careers.axa.com',
    'Orange Business':'https://www.orange-business.com/en/careers',
    'Siemens India':'https://jobs.siemens.com/careers',
    'DHL India':'https://careers.dhl.com',
    'Unilever India':'https://careers.unilever.com',
    'Mondelez India':'https://www.mondelezinternational.com/careers',
    'Visa India':'https://usa.visa.com/careers.html',
    'Fiserv India':'https://www.careers.fiserv.com',
    'U.S. Bank India':'https://careers.usbank.com',
    'PNC India':'https://careers.pnc.com',
    'Pfizer India':'https://www.pfizer.com/about/careers',
    'Novartis India':'https://www.novartis.com/careers',
    'Medtronic India':'https://medtronic.eightfold.ai/careers',
    'Philips India':'https://www.careers.philips.com',
    'Mercedes-Benz R&D India':'https://jobs.mercedes-benz.com',
    'Bosch India (BGSW)':'https://www.bosch.in/careers/',
    'Amdocs India':'https://www.amdocs.com/careers',
    'Western Union India':'https://careers.westernunion.com',
    'State Street India':'https://statestreet.wd1.myworkdayjobs.com/Global',
    'Levi Strauss & Co. India':'https://www.levistrauss.com/careers/',
    'Wells Fargo India':'https://www.wellsfargojobs.com/en/jobs/?search=pega&country=India',
    'Kotak Mahindra Bank':'https://www.kotak.com/en/about-us/careers.html',
    'CNO Financial':'https://careers.cnoinc.com',
    'Proximus':'https://www.proximus.com/careers.html',
    'Ford India (FBS)':'https://corporate.ford.com/careers.html',
    'Stellantis India':'https://www.careers.stellantis.com',
    'Cummins India':'https://www.cummins.com/careers',
    'FIS India':'https://careers.fisglobal.com',
    'Global Payments India':'https://jobs.globalpayments.com',
    'Empower India':'https://www.empower.com/careers',
    'IFFCO Tokio':'https://www.iffcotokio.co.in/career',
    'Manulife India':'https://www.manulife.com/en/careers.html',
    'Renault-Nissan Tech India':'https://www.renaultgroup.com/en/our-company/careers/',
    'Navistar India':'https://www.international.com/careers',
    'UPS India':'https://www.jobs-ups.com',
    'LPL Financial India':'https://careers.lpl.com',
    'Voya Financial India':'https://www.voya.com/careers',
    'Conduent India':'https://jobs.conduent.com',
    'Ameriprise India':'https://www.ameriprise.com/careers',
    'HDFC Bank':'https://www.hdfcbank.com/personal/about-us/careers',
    'ICICI Bank':'https://www.icicicareers.com',
    'Fidelity India':'https://india.fidelity.com/careers/',
    'Charles Schwab India':'https://www.schwabjobs.com',
    'BNY India':'https://bnymellon.eightfold.ai/careers',
    'The Hartford India':'https://www.thehartford.com/careers',
    'Fidelity National Financial India (FNF)':'https://www.fnf.com/careers',
    'Marsh McLennan India (MMGS)':'https://careers.marshmclennan.com',
    'PepsiCo India':'https://www.pepsicojobs.com',
    'Mizuho Global Services India (MGS)':'https://www.mizuhogroup.com/careers',
    'Carelon Global Solutions India':'https://www.carelon.com/careers',
    'MUFG Pension & Market Services (Link Group)':'https://www.mpms.mufg.com/careers',
    'ITC Limited':'https://www.itcportal.com/careers/',
    'Barclays India':'https://search.jobs.barclays',
    'Citi / Citi India':'https://jobs.citi.com',
    'Hartford India GCC':'https://www.thehartford.com/careers',
    'Bosch':'https://www.bosch.in/careers/',
    'Cargill':'https://careers.cargill.com',
    'DHL IT Services':'https://careers.dhl.com',
    'IKEA':'https://www.ikea.com/global/en/work-with-us/',
    'Lloyds Technology Centre India':'https://lloydstechnologycentre.com/our-roles',
    'Mercedes-Benz Mobility AG':'https://jobs.mercedes-benz.com',
    'NAB Innovation Centre India':'https://www.nab.com.au/about-us/careers',
    'Standard Chartered India':'https://www.sc.com/en/global-careers/',
    'Evernorth / Cigna':'https://jobs.thecignagroup.com',
    'Siemens':'https://jobs.siemens.com/careers',
    'Vodafone / VOIS':'https://careers.vodafone.com',
    'Sun Life / SLGS':'https://sunlife.com/careers',
    'Maersk GSC':'https://maersk.com/careers',
    'enGen / Highmark':'https://careers.highmarkhealth.org',
    'Lloyds Banking Group India':'https://lloydstechnologycentre.com/our-roles',
    'MetLife MGCC':'https://www.metlifecareers.com',
    'CNO Financial India':'https://careers.cnoinc.com',
    'Carelon / Elevance':'https://careers.elevancehealth.com',
    'Optum / UHG':'https://careers.unitedhealthgroup.com',
    'Philips':'https://www.careers.philips.com',
    'Nike India (ITC)':'https://careers.nike.com',
    'Unilever / UniOps':'https://careers.unilever.com',
    'Bosch / BGSW':'https://www.bosch.in/careers/',
    'Ford':'https://corporate.ford.com/careers.html',
    'Renault-Nissan Tech':'https://www.renaultgroup.com/en/our-company/careers/',
    'Navistar / International Motors':'https://www.international.com/careers',
    'UPS':'https://www.jobs-ups.com',
    'Credit Suisse / UBS India':'https://www.ubs.com/global/en/careers.html',
    'MUFG Global Service':'https://www.mufg.jp/english/careers/index.html',
    'First Citizens Bank India':'https://jobs.firstcitizens.com',
    'Ameriprise Financial India':'https://www.ameriprise.com/careers',
    'Optum / UnitedHealth Group India':'https://careers.unitedhealthgroup.com',
    'Elevance Health India':'https://careers.elevancehealth.com',
    'Ford Business Solutions India':'https://corporate.ford.com/careers.html',
    'MassMutual India':'https://careers.massmutual.com',
    'ING':'https://www.ing.jobs',
    'AIG':'https://www.aig.com/careers',
    'AstraZeneca':'https://careers.astrazeneca.com',
    'DP World':'https://www.dpworld.com/careers',
    'T-Mobile / TMUS Global Solutions':'https://www.t-mobile.com/careers',
    'Deutsche Telekom Digital Labs':'https://www.telekom.com/en/careers',
    'Schneider Electric':'https://www.se.com/ww/en/about-us/careers/overview.jsp',
    'Honeywell':'https://careers.honeywell.com',
    'Airbus':'https://www.airbus.com/en/careers',
    'CVS Health / Aetna':'https://jobs.cvshealth.com',
    'Prime Therapeutics':'https://www.primetherapeutics.com/careers/',
    'Lufthansa Systems India':'https://www.lufthansa-systems.com/career',
    'ExxonMobil India':'https://jobs.exxonmobil.com',
    'NatWest Group India':'https://jobs.natwestgroup.com',
    'Bank of America India':'https://careers.bankofamerica.com',
    'Deutsche Bank India':'https://careers.db.com',
    'Target in India':'https://corporate.target.com/careers',
    'Columbia Sportswear Company':'https://www.columbiasportswearcompany.com/careers/',
    'Rabobank':'https://www.rabobank.jobs',
    'MetLife India GCC':'https://www.metlifecareers.com',
    'Estes Express':'https://www.work4estes.com',
    'Ayvens / LeasePlan':'https://www.ayvens.com/en-cp/careers/',
    'Charter / Spectrum':'https://jobs.spectrum.com',
    'Walmart Global Tech India':'https://careers.walmart.com/technology',
    'Vodafone Idea':'https://www.myvi.in/careers',
    'BMW Financial Services':'https://www.bmwgroup.jobs',
    'Toyota / TFS':'https://www.toyotafinancial.com/us/en/careers.html',
    'Unilever':'https://careers.unilever.com',
    'Ford Credit':'https://corporate.ford.com/careers.html',
    'John Deere Financial':'https://www.deere.com/en/our-company/john-deere-careers/',
    'FIS (TSYS)':'https://careers.fisglobal.com',
    'JPMorgan Chase India':'https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions?keyword=pega&location=India',
    'Goldman Sachs India':'https://higher.gs.com/roles?q=pega&location=India',
    'Citibank India':'https://jobs.citi.com',
    'HSBC India':'https://mycareer.hsbc.com/en_GB/external/SearchJobs/?q=pega&locationsearch=India',
    'Societe Generale India':'https://careers.societegenerale.com/en',
    'Optum / UnitedHealth India':'https://careers.unitedhealthgroup.com',
    'Sun Life India GCC':'https://sunlife.com/careers',
    'American Express India':'https://aexp.com/careers',
    'Global Payments / TSYS India':'https://jobs.globalpayments.com',
    'Synchrony India':'https://www.synchronycareers.com',
    'Morgan Stanley India':'https://www.morganstanley.com/people-opportunities/careers',
    'BNP Paribas India':'https://group.bnpparibas/careers',
    'BNY Mellon India':'https://bnymellon.eightfold.ai/careers',
    'Commonwealth Bank India':'https://commbank.com.au/about-us/careers',
    'MUFG Pension & Market Svcs':'https://www.mpms.mufg.com/careers',
    'ANZ Bank India':'https://careers.anz.com',
    'Allianz Technology India':'https://careers.allianz.com',
    'IFFCO Tokio India':'https://www.iffcotokio.co.in/career',
    'Dell India':'https://jobs.dell.com',
    'Marsh McLennan India':'https://careers.marshmclennan.com',
    'Qualcomm':'https://careers.qualcomm.com',
    'Airtel':'https://www.airtel.in/careers',
    'Lowe’s':'https://talent.lowes.com',
    'JLR':'https://www.jaguarlandrovercareers.com',
    'BMW TechWorks':'https://www.bmwgroup.jobs',
    'VW Digital Solutions':'https://www.cariad.technology/careers/',
    'Volvo Cars':'https://www.volvocars.com/intl/v/careers',
    'GE Aerospace':'https://jobs.gecareers.com/aviation/global/en',
    'GE Vernova':'https://jobs.gecareers.com/vernova/global/en',
    'BP':'https://www.bp.com/en/global/corporate/careers.html',
    'Chevron':'https://careers.chevron.com',
    'ExxonMobil':'https://jobs.exxonmobil.com',
    'SLB':'https://careers.slb.com',
    'Boeing':'https://jobs.boeing.com',
    'Rolls-Royce':'https://careers.rolls-royce.com',
    'ABB':'https://careers.abb/global/en',
    'Eaton':'https://www.eaton.com/us/en-us/company/careers.html',
    'CNH':'https://www.cnh.com/en-US/Careers',
    'Komatsu':'https://www.komatsu.com/en/careers/',
    'Carrier':'https://jobs.carrier.com',
    'JCI':'https://jobs.johnsoncontrols.com',
    'HCLTech':'https://www.hcltech.com/careers',
    'Ness Digital Engineering':'https://www.ness.com/careers/',
    'Bits In Glass':'https://bitsinglass.com/careers/',
    'Coforge':'https://careers.coforge.com',
    'KPMG India':'https://kpmg.com/in/en/home/careers.html',
    'Tata Consultancy Services':'https://www.tcs.com/careers/india',
    'Truviq Systems':'https://www.truviq.com/careers',
    'V2Soft':'https://www.v2soft.com/careers',
    'HashedIn by Deloitte':'https://hashedin.com/careers/',
    'Levi Strauss India':'https://www.levistrauss.com/careers/',
    'Daimler AG (Mercedes parent)':'https://jobs.mercedes-benz.com',
    'Target':'https://corporate.target.com/careers',
    'Instellars':'https://www.instellars.com/careers',
    'Hexaware Technologies':'https://hexaware.com/careers/',
    'NTT DATA Services':'https://www.nttdata.com/global/en/careers',
    'Perficient':'https://www.perficient.com/careers',
    'Unisys':'https://www.unisys.com/careers/',
    'EY India':'https://www.ey.com/en_in/careers',
    'PwC India':'https://pwc.wd3.myworkdayjobs.com/en-US/Global_Experienced_Careers?locationCountry=16dcc53e4691011e83255a4483077800',
    'Publicis Sapient':'https://www.publicissapient.com/careers',
    'NTT DATA':'https://www.nttdata.com/global/en/careers',
    'Persistent Systems':'https://www.persistent.com/careers/',
    'Birlasoft':'https://www.birlasoft.com/careers',
    'DXC Technology':'https://careers.dxc.com',
    'Hexaware':'https://hexaware.com/careers/',
    'Zensar Technologies':'https://www.zensar.com/careers',
    'UST Global':'https://www.ust.com/en/careers',
    'Genpact':'https://www.genpact.com/careers',
    'Eviden (Atos)':'https://eviden.com/careers/',
    'Innova ESI':'https://www.innovaesi.com/careers',
    'PruTech Solutions':'https://www.prutech.com/careers/',
    'Nous Infosystems':'https://www.nousinfosystems.com/careers/',
    'Merkle (dentsu)':'https://www.dentsu.com/careers',
    'Sonata Software':'https://www.sonata-software.com/careers',
    'Cyient':'https://www.cyient.careers',
    'Artech LLC':'https://www.artech.com/careers/',
    'Collabera':'https://collabera.com/careers/',
    'Mastech Holdings':'https://www.mastechdigital.com/careers/',
    'Quess Corp':'https://www.quesscorp.com/careers/',
    'Anlage Infotech':'https://www.anlage.co.in/careers',
    'EvonSys':'https://www.evonsys.com/careers/',
    'EY':'https://www.ey.com/en_in/careers',
    'ITC Infotech':'https://www.itcinfotech.com/careers/',
    'Randstad Digital':'https://www.randstaddigital.com/careers/',
    'Mphasis India':'https://careers.mphasis.com',
    'Coforge India':'https://careers.coforge.com',
    'Virtusa India':'https://www.virtusa.com/careers',
    'CGI India':'https://www.cgi.com/en/careers',
    'Tenth Revolution Group':'https://www.tenthrevolution.com/careers/',
    'Revolent Group':'https://www.revolentgroup.com/careers/',
    'Talent Toppers':'https://www.talenttoppers.com/current-openings/',
    'VMC Soft Technologies':'https://www.vmcsofttech.com/careers/',
    'Allime Tech Solutions':'https://allimetech.com/careers/',
    'Teamware Solutions':'https://www.teamwaresolutions.net/careers/',
    'Billennium':'https://billennium.com/career/',
    'QualiZeal':'https://qualizeal.com/careers/',
    'enGen Global':'https://www.engen.health/careers/',
    'Process360 Ltd':'https://www.processthreesixty.com/jobs/',
    'Religent Systems':'https://religentsystems.com/career/hiring-pega-lead-system-architect-2/',
    'Estes Express India':'https://www.work4estes.com',
    'Societe Generale GSC India':'https://careers.societegenerale.com/en',
}

def read(path, default=None):
    try:return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError,ValueError):return {} if default is None else default

def profile_identity(url):
    try:
        p=urlsplit(str(url or ''));host=(p.hostname or '').lower()
        m=re.match(r'/in/([^/]+)',p.path,re.I)
        if (host=='linkedin.com' or host.endswith('.linkedin.com')) and m:return 'linkedin:'+unquote(m.group(1)).lower()
    except ValueError:pass
    return ''

def seq(v):return v if isinstance(v,list) else [v] if v else []

def apply_career_urls(targets):
    rows=[dict(target) for target in targets]
    by_alias={}
    for target in rows:
        url=target.get('career_url')
        if not url:continue
        for value in [target.get('name',''),*target.get('keywords',[]),*target.get('aliases',[])]:
            by_alias.setdefault(company_key(value),url)
    for target in rows:
        aliases=[target.get('name',''),*target.get('keywords',[]),*target.get('aliases',[])]
        override=next((url for name,url in CAREER_URL_OVERRIDES.items() if company_key(name) in {company_key(value) for value in aliases}),None)
        inherited=next((by_alias[company_key(value)] for value in aliases if company_key(value) in by_alias),None)
        if not target.get('career_url') and (override or inherited):
            target['career_url']=override or inherited
            target['career_url_basis']='official override' if override else 'alias inheritance'
        if target.get('career_url'):
            for value in aliases:
                by_alias.setdefault(company_key(value),target['career_url'])
    return rows

def unique(v):
    result=[];seen=set()
    for x in v:
        key=json.dumps(x,sort_keys=True,ensure_ascii=True)
        if key not in seen:seen.add(key);result.append(x)
    return result

def build(base=BASE,research=None):
    base=Path(base);root=Path(research or base/'research')
    fresh=read(root/'independent_map.json',{'companies':[],'people':[]})
    directory=read(root/'directory.json')
    recovered=read(root/'legacy_conservation_20260908.json')
    companies={};names={};persons={};ledger=[];source_rows=[];redirects={}
    prior_catalog=read(root/'master_catalog.json')
    aliases={company_key(v):company_key(k) for k,vs in ALIASES.items() for v in [k,*vs]}
    extra_aliases={'Mercedes-Benz / MBRDI':'Mercedes-Benz R&D India (MBRDI)','Fidelity National Financial India':'Fidelity National Financial India (FNF)','FNF India':'Fidelity National Financial India (FNF)','Sun Life (additional)':'Sun Life','Optum / UnitedHealth':'Optum / UnitedHealth Group','NAB India':'NAB (National Australia Bank)','BT':'BT Group','BT Group Bengaluru':'BT Group','Pegasystems Bengaluru':'Pegasystems India','Siemens Technology India':'Siemens','Lloyds Technology Centre':'Lloyds Technology Centre India'}
    aliases.update({company_key(k):aliases.get(company_key(v),company_key(v)) for k,v in extra_aliases.items()})
    # Do not convert a historically conflated FIS/TSYS label into Global Payments.
    def co_key(name):return aliases.get(company_key(name),company_key(name))
    stable_names={}
    for old in prior_catalog.get('companies',[]):
        for name in [old['name'],*old.get('aliases',[])]:stable_names.setdefault(co_key(name),set()).add(old['id'])
    old_link_ids={old['id']:set(old.get('source_company_ids',[])) for old in prior_catalog.get('companies',[])}
    def resolved(cid):
        while cid in redirects:cid=redirects[cid]
        return cid
    def company(name,category='unclassified',preferred=None,other_names=()):
        category=category or 'unclassified'
        keys={co_key(v) for v in [name,*other_names] if v}
        ids={resolved(names[k]) for k in keys if k in names}
        saved={resolved(cid) for k in keys for cid in stable_names.get(k,[]) if cid}
        cid=sorted(ids,key=lambda x:(not x.startswith('fresh-'),x))[0] if ids else next(iter(saved)) if len(saved)==1 else (preferred or 'catalogue-'+co_key(name))
        # Only exact names and supplied aliases join groups. Keep every observation and old ID.
        for other in sorted(ids-{cid}):
            current=companies[cid];duplicate=companies.pop(other)
            for field,value in duplicate.items():
                if isinstance(value,list):current[field]=unique(current.get(field,[])+value)
                elif field=='flags':current[field]={k:bool(current.get(field,{}).get(k) or value.get(k)) for k in set(current.get(field,{}))|set(value)}
                elif not current.get(field):current[field]=copy.deepcopy(value)
            current['source_company_ids']=unique(current.get('source_company_ids',[])+[other])
            redirects[other]=cid
            for key,value in list(names.items()):
                if value==other:names[key]=cid
        if cid not in companies:
            companies[cid]={'id':cid,'name':name,'category':category,'aliases':[], 'claims':[],'hiring_signals':[],'limitations':[], 'flags':{},'legacy_snapshots':[],'source_rows':[],'search_targets':[]}
        c=companies[cid]
        if c['category']=='unclassified' and category!='unclassified':c['category']=category
        c['aliases']=unique([*c['aliases'],name,*other_names])
        c['source_company_ids']=unique(c.get('source_company_ids',[])+sorted(saved-{cid})+sorted({link for prior in saved|{cid} for link in old_link_ids.get(prior,set())}))
        for k in keys:
            if k not in names or names[k]==cid:names[k]=cid
        return c
    def add_person(raw,c,source_id,legacy=False):
        if not raw.get('name') or str(raw['name']).strip() in ('—','-','Unknown','Not identified'):return
        url=raw.get('profile_url') or raw.get('linkedin') or raw.get('source_url')
        ident=profile_identity(url) or 'named:'+c['id']+':'+company_key(raw['name'])
        certs=seq(raw.get('certifications'))+seq(raw.get('certs'))
        obs=copy.deepcopy(raw)
        obs.update(company_id=c['id'],company=c['name'],source_record_id=source_id)
        if legacy:
            obs.update(access='legacy',checked_at=None,source_file=raw.get('source_file') or source_id.split('#')[0],source_date=raw.get('source_date') or raw.get('tenure') or raw.get('dates'),
                       employer_as_stated=raw.get('employer_as_stated') or raw.get('company_as_stated') or c['name'],profile_url=url if profile_identity(url) else None,
                       source_url=url,location_as_stated=raw.get('location_as_stated') or raw.get('location'),
                       work_summary=raw.get('work_summary') or raw.get('detail') or raw.get('pega_connection') or 'Earlier named professional record; current employer, role and location need rechecking.',
                       certifications=certs)
        p=persons.setdefault(ident,{'id':hashlib.sha256(ident.encode()).hexdigest()[:18],'identity_key':ident,'name':raw['name'], 'company':c['name'],'company_id':c['id'],'company_ids':[], 'observations':[],'certifications':[]})
        p['company_ids']=unique(p['company_ids']+[c['id']])
        p['observations'].append(obs);p['certifications']=unique(p['certifications']+certs)
        # Fresh observations are added first; older rows only fill missing displayed fields.
        replace_primary=bool(obs.get('crosschecked') and not p.get('crosschecked'))
        if replace_primary:p.update(name=raw['name'],company=c['name'],company_id=c['id'],crosschecked=True)
        for key in ('title','profile_url','source_url','location_as_stated','work_summary','pega_connection','checked_at','access','source_date'):
            if legacy and any(o.get('access') not in (None,'legacy') for o in p['observations']):continue
            if replace_primary:p[key]=obs.get(key)
            elif not p.get('crosschecked') and not p.get(key) and obs.get(key):p[key]=obs[key]
        if not p.get('access'):p['access']='legacy'
        source_rows.append({'source_record_id':source_id,'person_id':p['id'],'company_id':c['id']})
    for raw in fresh.get('companies',[]):
        c=company(raw['name'],raw.get('category','unclassified'),raw.get('id'),raw.get('aliases',[]))
        c['source_company_ids']=unique(c.get('source_company_ids',[])+[raw['id']])
        for k,v in raw.items():
            if k in ('claims','hiring_signals','limitations'):c[k]=unique(c.get(k,[])+copy.deepcopy(v))
            elif k=='flags':c[k]={flag:bool(c.get(k,{}).get(flag) or v.get(flag)) for flag in set(c.get(k,{}))|set(v)}
            elif k not in ('id','name','aliases','people'):c[k]=copy.deepcopy(v)
        c['evidence_status']='dated_public_research'
    for i,p in enumerate(fresh.get('people',[])):
        for j,obs in enumerate(p.get('observations') or [p]):
            source_id=obs.get('company_id') or p.get('company_id')
            source_company=companies.get(source_id) or next((c for c in companies.values() if source_id in c.get('source_company_ids',[])),None)
            c=source_company or company(obs.get('company') or p.get('company') or obs.get('employer_as_stated') or 'Employer unconfirmed')
            add_person(obs,c,'independent_map.json#people/'+str(i)+'/observations/'+str(j))
    ledger.append({'source':'independent_map.json','company_rows':len(fresh.get('companies',[])),'person_rows':len(fresh.get('people',[]))})
    # All original scan targets are retained even where no Pega team is established.
    for i,t in enumerate(directory.get('records',[])):
        c=company(t['name'],t.get('category','unclassified'))
        c['search_targets'].append(copy.deepcopy(t))
        c['evidence_status']=c.get('evidence_status') or 'search_target_only'
        c['source_rows'].append({'source_record_id':'directory.json#records/'+str(i),'target_id':t['target_id']})
    snapshots=[('directory.json#historical_snapshots',directory.get('historical_snapshots',[]))]
    for filename in ('team_intelligence.json','team_intelligence_enriched.json'):
        snapshots.append((filename,read(base/filename).get('companies',[])))
    for source,rows in snapshots:
        count=0
        for i,raw in enumerate(rows):
            c=company(raw['name'],'gcc');rid=source+'/'+str(i)
            c['legacy_snapshots'].append({'source_record_id':rid,'data':copy.deepcopy(raw)})
            c['evidence_status']=c.get('evidence_status') or 'legacy_unverified'
            # Merged historical snapshot displays the rich details; base variants remain in ledger.
            if source.startswith('directory'):
                c['legacy_details']=copy.deepcopy(raw)
                if raw.get('projects'):c['claims'].append({'type':'project','text':raw['projects'],'access':'legacy','source_file':source,'source_url':None,'source_date':None,'confidence':'unverified','checked_at':None})
            for j,p in enumerate(raw.get('team_members',[])):
                add_person(p,c,rid+'/team_members/'+str(j),True);count+=1
            for j,p in enumerate(raw.get('_hiring_playbook',{}).get('bangalore_intel',{}).get('contacts',[])):
                if isinstance(p,dict):add_person(p,c,rid+'/bangalore_contacts/'+str(j),True)
        ledger.append({'source':source,'company_rows':len(rows),'person_rows':count})
    # Recent team notes are distinct observations; never assert they are live rosters.
    recent=directory.get('recent_teams',[])
    if isinstance(recent,dict):recent=[dict(v,name=k) for k,v in recent.items() if isinstance(v,dict)]
    for i,row in enumerate(recent):
        if not isinstance(row,dict):continue
        name=row.get('name') or row.get('company')
        if not name:continue
        c=company(name)
        c.setdefault('recent_team_notes',[]).append(copy.deepcopy(row))
        for j,source in enumerate(row.get('sources',[])):
            if profile_identity(source.get('url')):
                title=source.get('title','')
                named=title.split('—',1)[0].strip()
                if named and named!=title:
                    add_person({'name':named,'profile_url':source['url'],'source_url':source['url'],'work_summary':source.get('excerpt'),'source_date':source.get('published_at'),'source_file':'directory.json','company_as_stated':name},c,'directory.json#recent_teams/'+str(i)+'/sources/'+str(j),True)
        for j,p in enumerate(row.get('people',[]) or row.get('team_members',[])):
            add_person(p,c,'directory.json#recent_teams/'+str(i)+'/'+str(j),True)
    # Extraction keys are normalized by the import step and preserve every raw Hub row.
    for i,row in enumerate(recovered.get('company_observations',[])):
        if row.get('entity_kind') not in (None,'company_or_group'):continue
        name=row.get('company') or row.get('name')
        if name:
            c=company(name,row.get('category','unclassified'));c['source_rows'].append(copy.deepcopy(row))
    for i,p in enumerate(recovered.get('professional_observations',[])):
        name=p.get('company') or p.get('employer_as_stated')
        if name:add_person(p,company(name),p.get('source_record_id') or 'career-hub#person/'+str(i),True)
    for path in sorted(root.glob('team_depth_*.json')):
        depth=read(path);rows=depth.get('team_depth',[]);count=0
        for i,row in enumerate(rows):
            c=company(row['company'],row.get('category','unclassified'),other_names=row.get('match_names',[]))
            c.setdefault('team_depth',[]).append(copy.deepcopy(row))
            for j,p in enumerate(row.get('people',[])):
                add_person(dict(p,work_summary=p.get('connection_to_team')),c,path.name+'#team_depth/'+str(i)+'/people/'+str(j),True);count+=1
        ledger.append({'source':path.name,'company_rows':len(rows),'person_rows':count})
    for c in companies.values():
        c['evidence_status']=c.get('evidence_status') or 'legacy_unverified'
        c['legacy_snapshots']=unique(c['legacy_snapshots'])
        c['current_team_size']=None
    for p in persons.values():
        p['company_id']=resolved(p['company_id'])
        p['company_ids']=unique([resolved(cid) for cid in p['company_ids']])
        for obs in p['observations']:obs['company_id']=resolved(obs['company_id'])
        p['observations']=unique(p['observations'])
        p['limitations']=unique([v for obs in p['observations'] for v in obs.get('limitations',[])])
    for row in source_rows:row['company_id']=resolved(row['company_id'])
    rows=list(companies.values());people=list(persons.values())
    doc = {'schema_version':1,'research_date':fresh.get('research_date'),'companies':rows,'people':people,'queries':fresh.get('queries',[]),
            'source_ledger':ledger,'person_source_rows':source_rows,'recovered_source_ledger':recovered.get('source_ledger',{}),
            'movement_observations':recovered.get('movement_observations',[]),'legacy_hub_rows':recovered.get('table_rows',[]),'legacy_company_observations':recovered.get('company_observations',[]),
            'stats':{'companies':len(rows),'people_records':len(people),'unique_linkedin_profiles':sum(bool(profile_identity(p.get('profile_url'))) for p in people),
                     'people_observations':sum(len(p['observations']) for p in people),'source_person_rows':len(source_rows),'bangalore_companies':sum(bool(c.get('flags',{}).get('bangalore')) for c in rows),
                     'fresh_companies':len(fresh.get('companies',[])),'legacy_company_snapshots':len(directory.get('historical_snapshots',[])),
                     'crosscheck_records':sum(x.get('type')=='crosscheck' for c in rows for x in c.get('claims',[])),'crosschecked_companies':sum(any(x.get('type')=='crosscheck' for x in c.get('claims',[])) for c in rows),
                     'original_scan_targets':len(directory.get('records',[])),'categories':dict(Counter(c['category'] for c in rows))},
            'definitions':{'people_records':'Profile URL identities, or unresolved name/employer records. Not a current employee count.','legacy':'Restored original observation, not freshly verified.','search_target_only':'Included in the original scan catalogue; Pega usage is not established.'}}
    from gcc_audit import attach
    return attach(doc,root)

def extra_targets(doc,existing):
    represented={company_key(t['name']) for t in existing}
    result=[]
    for target in CURATED_SCAN_TARGETS:
        if not target.get('allow_duplicate') and any(company_key(name) in represented for name in [target['name'],*target.get('keywords',[])]):continue
        result.append(dict(target))
    represented.update(company_key(t['name']) for t in result)
    for c in doc.get('companies',[]):
        if c.get('search_targets') or any(company_key(n) in represented for n in [c['name'],*c.get('aliases',[])]):continue
        category=c.get('category','unclassified')
        result.append({'target_id':c['id'],'name':c['name'],'keywords':[c['name']], 'category':category if category in ('gcc','services','global') else 'gcc',
                       'location':'India','catalog_scope':'restored','location_basis':'India search scope; assignment location unconfirmed'})
    return result

if __name__=='__main__':
    doc=build();(BASE/'research/master_catalog.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(doc['stats']))
