import json
import sys
import unittest
from pathlib import Path

BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'.deps'));sys.path.insert(0,str(BASE))

import career_scraper


class FakeLocator:
    def __init__(self, text):self._text=text
    @property
    def first(self):return self
    def inner_text(self, timeout=0):return self._text


class FakeJobPage:
    url='https://jobs.bd.com/en/job/bengaluru/bpm-architect-and-analyst/159/90537282656'
    title='BPM Architect and Analyst'
    description='Build Pega Blueprints, case lifecycle design, Pega decisioning, guardrails, and Pega Platform delivery.'
    company='Becton Dickinson & Company'
    requisition='R-534936'
    def content(self):
        posting={
            '@context':'https://schema.org', '@type':'JobPosting',
            'title':self.title,
            'hiringOrganization':{'@type':'Organization','name':self.company},
            'identifier':{'value':self.requisition},
            'url':self.url,
            'jobLocation':{'@type':'Place','address':{'addressLocality':'Bengaluru','addressRegion':'Karnataka','addressCountry':'India'}},
            'description':self.description
        }
        return '<script type="application/ld+json">'+json.dumps(posting)+'</script>'
    def inner_text(self, selector):return self.title+' Bengaluru '+self.description
    def locator(self, selector):return FakeLocator(self.title)


class FakeCloudSolutionsPage(FakeJobPage):
    url='https://pwc.wd3.myworkdayjobs.com/en-US/Global_Experienced_Careers/job/Hyderabad/cloud-solutions'
    title='IN_Senior Associate_Azure Cloud Solutions _GCC_Advisory_Hyderabad'
    company='PwC India'
    requisition='PWC-PEGA-CLOUD'
    description='Healthcare GCC delivery integrating Oracle, Azure, Pega Platform, Service REST, Connect REST, and Connect-SQL.'


class FakeGenericConsultantPage(FakeJobPage):
    url='https://example.com/careers/software-consultant-hyderabad'
    title='Software Consultant'
    company='Example GCC'
    requisition=''
    description='Apply for this role in Hyderabad. Responsibilities include Pega PRPC case management, rulesets, integrations, and guardrails.'
    def content(self):return '<html><body></body></html>'
    def inner_text(self, selector):return self.title+' Hyderabad '+self.description


class FakeSearchResultsPage(FakeGenericConsultantPage):
    url='https://example.com/search-jobs/pega/159/1'
    title='Search Results'


class FakeGermanSearchPage(FakeGenericConsultantPage):
    """Cargill-style German search page with zero results."""
    url='https://careers.cargill.com/de/jobsuche/pega/23251/1'
    title='Helfen Sie Landwirten dabei, mehr zu erreichen. Arbeiten Sie an der Zukunft mit.'
    description='Pega Karriere durchsuchen 0 results found try different keywords'
    def inner_text(self, selector):return self.title+' '+self.description


class FakeCarrierSearchPage(FakeGenericConsultantPage):
    """Carrier-style German search page."""
    url='https://jobs.carrier.com/de/jobsuche/pega/Vepery/29289/1/4/1269750/13x08472/80x2675/50/0'
    title='Carrier Jobs durchsuchen'
    description='pega Carrier Jobs durchsuchen India 0 results found.'
    def inner_text(self, selector):return self.title+' '+self.description


class FakeAccentureSearchPage(FakeGenericConsultantPage):
    """Accenture jobsearch? query param page."""
    url='https://www.accenture.com/in-en/careers/jobsearch?is_rj=0&jk=pega&sb=0&vw=0'
    title='Search jobs at Accenture'
    description='Search jobs at Accenture. pega 0 results. Try different keywords.'
    def inner_text(self, selector):return self.title+' '+self.description


class FakeZeroResultPage(FakeGenericConsultantPage):
    """Generic zero-result search page that echoes the keyword."""
    url='https://example.com/careers/search'
    title='Pega role'
    description='Pega 0 results found. Sorry, no jobs matched your search criteria. Try different keywords.'
    def inner_text(self, selector):return self.title+' Bengaluru '+self.description


class FakeUsOnlyJobPage(FakeJobPage):
    url='https://example.com/job/franklin-lakes/director-quality-systems'
    title='Director, Quality Systems'
    company='Example US'
    requisition='US-PEGA'
    description='Own Pega quality systems and platform processes.'
    def content(self):
        posting={
            '@context':'https://schema.org','@type':'JobPosting','title':self.title,
            'hiringOrganization':{'@type':'Organization','name':self.company},'identifier':{'value':self.requisition},
            'url':self.url,'jobLocation':{'@type':'Place','address':{'addressLocality':'Franklin Lakes','addressRegion':'New Jersey','addressCountry':'United States'}},
            'description':self.description
        }
        return '<script type="application/ld+json">'+json.dumps(posting)+'</script>'
    def inner_text(self, selector):return self.title+' Franklin Lakes New Jersey United States '+self.description


class FakeElement:
    def __init__(self, href, text, parent_text=''):
        self.href=href;self.text=text;self.parent_text=parent_text
    def get_attribute(self, name):return self.href if name=='href' else ''
    def inner_text(self):return self.text
    def evaluate(self, script):return self.parent_text


class FakeListingPage:
    url='https://example.com/careers'
    def __init__(self):
        self.elements=[
            FakeElement('/careers/software-consultant-hyderabad','Software Consultant','Software Consultant Hyderabad Apply now'),
            FakeElement('/privacy','Privacy','Privacy'),
        ]
    def query_selector_all(self, selector):return self.elements if selector=='li a' else []


class CareerScraperTests(unittest.TestCase):
    def test_generic_title_jobposting_is_kept_when_description_has_pega(self):
        jobs=career_scraper._extract_current_job_page(FakeJobPage(),'BD / Becton Dickinson','2026-09-28T00:00:00+00:00')
        self.assertEqual(len(jobs),1)
        self.assertEqual(jobs[0]['title'],'BPM Architect and Analyst')
        self.assertEqual(jobs[0]['requisition_id'],'R-534936')
        self.assertIn('Bengaluru',jobs[0]['location'])
        self.assertEqual(jobs[0]['source'],'Employer career page')

    def test_cloud_advisory_title_is_kept_when_description_has_pega_integration(self):
        jobs=career_scraper._extract_current_job_page(FakeCloudSolutionsPage(),'PwC Advisory GCC','2026-09-28T00:00:00+00:00')
        self.assertEqual(len(jobs),1)
        self.assertIn('Azure Cloud Solutions',jobs[0]['title'])
        self.assertEqual(jobs[0]['requisition_id'],'PWC-PEGA-CLOUD')
        self.assertIn('Pega Platform',jobs[0]['description_text'])

    def test_generic_consultant_detail_page_is_kept_when_body_has_pega(self):
        jobs=career_scraper._extract_current_job_page(FakeGenericConsultantPage(),'Example GCC','2026-09-28T00:00:00+00:00')
        self.assertEqual(len(jobs),1)
        self.assertEqual(jobs[0]['title'],'Software Consultant')
        self.assertIn('Pega PRPC',jobs[0]['description_text'])
        self.assertIn('Hyderabad',jobs[0]['location'])

    def test_generic_listing_link_is_detail_checked_without_pega_in_card_text(self):
        urls=career_scraper._collect_candidate_detail_urls(FakeListingPage(),limit=5)
        self.assertEqual(urls,['https://example.com/careers/software-consultant-hyderabad'])

    def test_search_results_page_itself_is_not_kept_as_job(self):
        jobs=career_scraper._extract_current_job_page(FakeSearchResultsPage(),'Example GCC','2026-09-28T00:00:00+00:00')
        self.assertEqual(jobs,[])

    def test_german_jobsuche_search_page_is_not_kept(self):
        jobs=career_scraper._extract_current_job_page(FakeGermanSearchPage(),'Cargill','2026-09-28T00:00:00+00:00')
        self.assertEqual(jobs,[],'German /jobsuche/ search page should be rejected')

    def test_carrier_durchsuchen_search_page_is_not_kept(self):
        jobs=career_scraper._extract_current_job_page(FakeCarrierSearchPage(),'Carrier','2026-09-28T00:00:00+00:00')
        self.assertEqual(jobs,[],'Carrier "durchsuchen" search page should be rejected')

    def test_accenture_jobsearch_query_page_is_not_kept(self):
        jobs=career_scraper._extract_current_job_page(FakeAccentureSearchPage(),'Accenture','2026-09-28T00:00:00+00:00')
        self.assertEqual(jobs,[],'Accenture jobsearch? page should be rejected')

    def test_zero_result_page_is_not_kept_even_with_pega_keyword(self):
        jobs=career_scraper._extract_current_job_page(FakeZeroResultPage(),'Example','2026-09-28T00:00:00+00:00')
        self.assertEqual(jobs,[],'Zero-result search page echoing pega keyword should be rejected')

    def test_is_search_or_listing_page_catches_localized_urls(self):
        self.assertTrue(career_scraper._is_search_or_listing_page('https://careers.cargill.com/de/jobsuche/pega/23251/1'))
        self.assertTrue(career_scraper._is_search_or_listing_page('https://jobs.carrier.com/de/jobsuche/pega/Vepery/29289'))
        self.assertTrue(career_scraper._is_search_or_listing_page('https://www.accenture.com/in-en/careers/jobsearch?jk=pega'))
        self.assertTrue(career_scraper._is_search_or_listing_page('https://example.com/recherche-emploi/pega'))
        # Real job detail URLs must NOT be caught
        self.assertFalse(career_scraper._is_search_or_listing_page('https://jobs.bd.com/en/job/bengaluru/bpm-architect/159/905'))
        self.assertFalse(career_scraper._is_search_or_listing_page('https://example.com/careers/software-consultant-hyderabad'))

    def test_is_search_or_listing_page_catches_listing_titles(self):
        self.assertTrue(career_scraper._is_search_or_listing_page('', 'Search jobs at Accenture'))
        self.assertTrue(career_scraper._is_search_or_listing_page('', 'Carrier Jobs durchsuchen'))
        self.assertTrue(career_scraper._is_search_or_listing_page('', 'Careers'))
        self.assertTrue(career_scraper._is_search_or_listing_page('', 'Browse Jobs'))
        # Real job titles must NOT be caught
        self.assertFalse(career_scraper._is_search_or_listing_page('', 'Senior Pega Developer'))
        self.assertFalse(career_scraper._is_search_or_listing_page('', 'BPM Architect and Analyst'))

    def test_is_zero_result_page_detects_empty_search(self):
        self.assertTrue(career_scraper._is_zero_result_page('pega 0 results found'))
        self.assertTrue(career_scraper._is_zero_result_page('No jobs found matching your criteria'))
        self.assertTrue(career_scraper._is_zero_result_page('Your search did not return any results'))
        self.assertTrue(career_scraper._is_zero_result_page('Sorry, no results match your query'))
        self.assertTrue(career_scraper._is_zero_result_page('Keine Ergebnisse'))
        # Pages with actual results must NOT be flagged
        self.assertFalse(career_scraper._is_zero_result_page('Showing 5 results for pega'))
        self.assertFalse(career_scraper._is_zero_result_page('Apply for Pega Developer in Hyderabad'))

    def test_non_india_jobposting_is_not_kept_for_india_scan(self):
        jobs=career_scraper._extract_current_job_page(FakeUsOnlyJobPage(),'Example US','2026-09-28T00:00:00+00:00')
        self.assertEqual(jobs,[])

    def test_workday_context_derives_tenant_and_site(self):
        context=career_scraper._workday_context('https://pwc.wd3.myworkdayjobs.com/en-US/Global_Experienced_Careers?locationCountry=india')
        self.assertEqual(context['tenant'],'pwc')
        self.assertEqual(context['site'],'Global_Experienced_Careers')

    def test_workday_cxs_keeps_generic_title_when_detail_has_pega(self):
        calls=[]
        def fake_api(url,payload=None,timeout=20):
            calls.append((url,payload))
            if payload is not None:
                return {'total':1,'jobPostings':[{'title':'Software Consultant','externalPath':'/job/Hyderabad/Software-Consultant_REQ1','locationsText':'Hyderabad, India','postedOn':'Posted Today','bulletFields':['REQ1']}]}
            return {'jobPostingInfo':{'title':'Software Consultant','location':'Hyderabad, India','jobDescription':'<p>Build Pega PRPC case management and integrations.</p>','postedOn':'Posted Today'}}
        original=career_scraper._workday_api_json
        career_scraper._workday_api_json=fake_api
        try:
            jobs,diag=career_scraper.scrape_workday_cxs('https://tenant.wd5.myworkdayjobs.com/en-US/site','Example GCC',checked_at='2026-09-28T00:00:00+00:00')
        finally:
            career_scraper._workday_api_json=original
        self.assertEqual(len(jobs),1)
        self.assertEqual(jobs[0]['title'],'Software Consultant')
        self.assertIn('Pega PRPC',jobs[0]['description_text'])
        self.assertEqual(jobs[0]['requisition_id'],'REQ1')
        self.assertEqual(diag['jobs_found'],1)

    def test_greenhouse_board_keeps_generic_title_when_content_has_pega(self):
        def fake_api(url,payload=None,timeout=20):
            return {'jobs':[{'title':'Clinical Configuration Analyst','absolute_url':'https://job-boards.greenhouse.io/coherehealth/jobs/1','location':{'name':'Hyderabad, Telangana, India'},'content':'<p>Configure Pega Cloud case lifecycle workflows.</p>','company_name':'Cohere Health','requisition_id':'GH1','first_published':'Posted Today'}]}
        original=career_scraper._workday_api_json
        career_scraper._workday_api_json=fake_api
        try:
            jobs,diag=career_scraper.scrape_greenhouse_board('https://job-boards.greenhouse.io/coherehealth','Cohere Health',checked_at='2026-09-28T00:00:00+00:00')
        finally:
            career_scraper._workday_api_json=original
        self.assertEqual(len(jobs),1)
        self.assertEqual(jobs[0]['title'],'Clinical Configuration Analyst')
        self.assertIn('Pega Cloud',jobs[0]['description_text'])
        self.assertEqual(jobs[0]['requisition_id'],'GH1')
        self.assertEqual(diag['jobs_found'],1)


if __name__=='__main__':unittest.main()
