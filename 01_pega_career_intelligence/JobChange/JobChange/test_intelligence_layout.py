import copy,json,sys,unittest,tempfile
from unittest.mock import patch
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'.deps'));sys.path.insert(0,str(BASE))
from bs4 import BeautifulSoup
import app,original_views,people_views

class IntelligenceLayoutTests(unittest.TestCase):
    def sample(self):
        company={'id':'test-bank','name':'Test Bank','category':'gcc','aliases':[],'flags':{},'claims':[{'type':'project','text':'Pega payment investigations','source_url':'https://example.com/project','access':'page'}],'hiring_signals':[],'limitations':[]}
        titles=['Pega Developer','Pega Lead System Architect','Pega Engineering Manager','Pega Technical Lead']
        people=[{'id':str(i),'name':'Person '+str(i),'company':'Test Bank','company_id':'test-bank','company_ids':['test-bank'],'title':title,'location_as_stated':'Bengaluru','profile_url':'https://www.linkedin.com/in/person-'+str(i),'source_url':'https://www.linkedin.com/in/person-'+str(i),'access':'search_index','checked_at':'2026-09-09','pega_connection':'Pega payment investigations','work_summary':'Develops Pega payment investigation workflows.','observations':[]} for i,title in enumerate(titles)]
        return {'companies':[company],'people':people,'stats':{'people_records':4},'research_date':'2026-09-09'}

    def test_dossier_groups_roles_without_losing_any_person_and_collapses_details(self):
        doc=self.sample();before=copy.deepcopy(doc);rows=original_views.dossier_data(BASE,doc);members=rows[0]['team_members']
        self.assertEqual(len(members),4)
        self.assertEqual([m['_role_level'] for m in members],sorted(m['_role_level'] for m in members))
        self.assertIn('Manager',members[0]['title'])
        for member in members:
            parsed=BeautifulSoup(member['_profile_html'],'html.parser')
            self.assertTrue(parsed.select('.pv-person'))
            self.assertTrue(parsed.select('details'))
            self.assertFalse(parsed.select('details[open]'))
            self.assertIsNotNone(parsed.find('a',href=member['linkedin']))
        self.assertEqual(doc,before)

    def test_hub_company_cards_are_closed_and_include_all_profiles_and_links(self):
        doc=self.sample();soup=BeautifulSoup(original_views.career_page(BASE,doc,app.PROFILE),'html.parser')
        for section_id in ('contacts','referral-dossiers','team-dossiers'):
            section=soup.find(id=section_id)
            self.assertEqual(len(section.select('.pv-person')),4)
            self.assertEqual(len(section.select('.intel-company')),1)
            self.assertFalse(section.select('details[open]'))
            self.assertEqual(len(section.select('.person-profile-link a[href^="https://www.linkedin.com/in/"]')),4)
        self.assertIsNotNone(soup.find('script',src='/static/intelligence-hub.js'))
        self.assertIsNotNone(soup.find('link',href='/static/intelligence.css'))

    def test_expanding_profile_reads_saved_sources_and_checks_company_membership(self):
        doc=self.sample();doc['companies'].append({'id':'other-bank','name':'Other Bank'})
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);research=root/'research';research.mkdir()
            (research/'master_catalog.json').write_text(json.dumps(doc),encoding='utf-8')
            client=app.create_app(root/'data',research).test_client()
            with patch('urllib.request.urlopen',side_effect=AssertionError('No external request allowed')):
                response=client.get('/api/intelligence/companies/test-bank/people/0')
                self.assertEqual(response.status_code,200)
                html=BeautifulSoup(response.get_json()['html'],'html.parser')
                self.assertIn('Develops Pega payment investigation workflows.',html.select_one('.person-body').get_text())
                self.assertIsNotNone(html.select_one('.person-profile-link a'))
                self.assertEqual(client.get('/api/intelligence/companies/other-bank/people/0').status_code,404)
                self.assertEqual(client.get('/api/intelligence/companies/test-bank/people/missing').status_code,404)
            doc['people'][0]['title']='Updated Pega Developer'
            (research/'master_catalog.json').write_text(json.dumps(doc),encoding='utf-8')
            self.assertIn('Updated Pega Developer',client.get('/api/intelligence/companies/test-bank/people/0').get_json()['html'])

    def test_new_company_renderer_keeps_company_navigation_and_people_filter(self):
        page=original_views.dossiers_page(BASE,self.sample())
        self.assertIn('function filterCompanyPeople()',page)
        self.assertIn('DossierView.open(co.name)',page)
        self.assertIn('/static/dossier-view.js',page)
        self.assertIn('teamPeopleSearch',page)
        self.assertIn('teamBengaluru',page)
        self.assertNotIn('Hiring Playbook — How to Get Hired at',page)
        self.assertIn('function renderSidebar()',page)
        self.assertIn('function showAllDossiers()',page)

if __name__=='__main__':unittest.main()
