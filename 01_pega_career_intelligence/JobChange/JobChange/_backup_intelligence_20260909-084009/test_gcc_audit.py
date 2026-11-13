import copy,json,sys,tempfile,unittest
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path[:0]=[str(BASE),str(BASE/'.deps')]
import gcc_audit,audit_views,original_views,app
from bs4 import BeautifulSoup

class DeepGccAuditTests(unittest.TestCase):
    def sample(self):
        company={'id':'sample-gcc','name':'Example GCC','category':'gcc','aliases':[],'source_company_ids':['old-example'],'claims':[],'hiring_signals':[],'flags':{},'limitations':[]}
        person={'id':'sample-person','identity_key':'linkedin:sample','name':'Example Person','company':'Example GCC','company_id':'sample-gcc','company_ids':['sample-gcc'],'title':'Old assumed architect','location_as_stated':'Bengaluru','certifications':['CLSA'],'profile_url':'https://www.linkedin.com/in/sample','observations':[{'access':'legacy','title':'Old assumed architect','company':'Example GCC','certifications':['CLSA']}]}
        return {'companies':[company],'people':[person],'stats':{'people_records':1},'research_date':'2026-09-08'}
    def write(self,root,name,value):
        (root/name).write_text(json.dumps(value),encoding='utf-8')
    def test_recorded_examination_required_and_aliases_preserved(self):
        doc=self.sample()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            self.write(root,'gcc_deep_audit_manifest.json',{'company_ids':['old-example'],'people_ids':['sample-person']})
            self.write(root,'gcc_deep_audit_1.json',{'company_reviews':[{'company_id':'old-example','status':'reviewed'}],'profile_reviews':[]})
            gcc_audit.attach(doc,root)
            self.assertEqual(doc['gcc_audit']['company_records_reviewed'],0)
            self.assertEqual(len(doc['gcc_audit']['diagnostics']),1)
            self.write(root,'gcc_deep_audit_1.json',{'queries':[{'id':'q1','query':'Exact company Pega India','outcome':'No matching public source'}],'company_reviews':[{'company_id':'old-example','status':'no_public_evidence','query_ids':['q1']}],'profile_reviews':[]})
            gcc_audit.attach(doc,root)
            self.assertEqual(doc['gcc_audit']['company_records_reviewed'],1)
            self.assertEqual(doc['gcc_audit']['companies_pending'],[])
            self.assertEqual(doc['gcc_audit']['profiles_pending'],['sample-person'])
            self.assertEqual(doc['companies'][0]['source_company_ids'],['old-example'])
    def test_audited_unknown_fields_do_not_inherit_old_assumptions(self):
        p=self.sample()['people'][0];before=copy.deepcopy(p)
        p['deep_audit']={'status':'unresolved','summary':'Exact identity not established','title':None,'employer_as_stated':None,'location_as_stated':None,'certifications':[]}
        display=audit_views.profile_display(p)
        self.assertIsNone(display['title']);self.assertIsNone(display['location_as_stated'])
        self.assertEqual(original_views.certifications(display),[])
        self.assertEqual(p['title'],before['title'])
        self.assertEqual(p['observations'],before['observations'])
    def test_reviewed_location_flags_override_legacy_and_preserve_history(self):
        for supported in (False, True):
            with self.subTest(bangalore_supported=supported), tempfile.TemporaryDirectory() as td:
                doc=self.sample(); company=doc['companies'][0]
                company['flags']={'bangalore':not supported,'pega':not supported,'employer_job':True}
                company['legacy_details']={'locations':['Bangalore'],'highlights':['Earlier location assumption']}
                original_flags=copy.deepcopy(company['flags'])
                original_legacy=copy.deepcopy(company['legacy_details'])
                original_person=copy.deepcopy(doc['people'][0])
                root=Path(td)
                self.write(root,'gcc_deep_audit_1.json',{
                    'research_date':'2026-09-08',
                    'queries':[{'id':'company-check','query':'Example GCC Pega Bengaluru','outcome':'Location evidence reviewed'}],
                    'company_reviews':[{'company_id':'old-example','status':'reviewed',
                        'query_ids':['company-check'],'pega_usage_supported':supported,
                        'bangalore_connection_supported':supported,
                        'bangalore_scope':'Named Bengaluru connection' if supported else 'No Bengaluru connection established'}]})
                gcc_audit.attach(doc,root)
                self.assertIs(company['flags']['bangalore'],supported)
                self.assertIs(company['flags']['pega'],supported)
                self.assertTrue(company['flags']['employer_job'])
                self.assertEqual(company['earlier_flags'],original_flags)
                row=original_views.dossier_data(BASE,doc)[0]
                self.assertIs(row['_bangalore'],supported)
                self.assertIs(row['_hiring_playbook']['bangalore_intel']['has_bangalore'],supported)
                self.assertNotIn('Bangalore',row['locations'])
                if supported:
                    self.assertIn('Bengaluru connection supported',row['locations'])
                else:
                    self.assertNotIn('Bengaluru connection supported',row['locations'])
                self.assertEqual(company['legacy_details'],original_legacy)
                self.assertEqual(doc['people'][0],original_person)
                # Reattaching must preserve the pre-review flag snapshot.
                gcc_audit.attach(doc,root)
                self.assertEqual(company['earlier_flags'],original_flags)

    def reviewed_profile(self):
        person=self.sample()['people'][0]
        person.update({'access':'page','source_date':'2025-01-01','checked_at':'2025-01-02',
                       'source_url':'https://www.linkedin.com/in/sample'})
        reviewed_url='https://www.linkedin.com/in/new-observed'
        person['deep_audit']={
            'status':'partially_supported','checked_at':'2026-09-08',
            'employer_as_stated':'Reviewed Employer','title':'Software Engineer',
            'location_as_stated':'Pune','profile_url':reviewed_url,'certifications':[],
            'summary':'Profile identity and employer corroborated; certifications not exposed.',
            'sources':[
                {'url':'https://example.org/employer','title':'Employer page','access':'page','source_date':'2026-06-01'},
                {'url':reviewed_url,'title':'Reviewed public professional profile','access':'search_index',
                 'checked_at':'2026-09-08','source_date':None}]}
        return person

    def test_profile_metadata_comes_from_the_matching_reviewed_source(self):
        person=self.reviewed_profile(); before=copy.deepcopy(person)
        display=audit_views.profile_display(person)
        self.assertEqual(display['profile_url'],'https://www.linkedin.com/in/new-observed')
        self.assertEqual(display['source_url'],display['profile_url'])
        self.assertEqual(display['access'],'search_index')
        self.assertIsNone(display['source_date'])
        self.assertEqual(display['checked_at'],'2026-09-08')
        self.assertEqual(display['company'],'Reviewed Employer')
        self.assertEqual(display['location_as_stated'],'Pune')
        self.assertEqual(original_views.certifications(display),[])
        self.assertIn('Search index',original_views.evidence(display))
        self.assertNotIn('2025-01-01',original_views.evidence(display))
        self.assertEqual(person,before)

    def test_unresolved_profile_clears_current_metadata_but_keeps_saved_link_in_history(self):
        person=self.reviewed_profile()
        person['deep_audit']={'status':'unresolved','checked_at':'2026-09-08',
                              'summary':'Exact identity not established','sources':[],'certifications':[]}
        before=copy.deepcopy(person)
        display=audit_views.profile_display(person)
        self.assertIsNone(display['profile_url'])
        self.assertIsNone(display['source_url'])
        self.assertIsNone(display['source_date'])
        self.assertEqual(display['access'],'unknown')
        self.assertIsNone(display['location_as_stated'])
        self.assertEqual(original_views.certifications(display),[])
        review=BeautifulSoup(audit_views.profile_review_html(person),'html.parser')
        old_link=review.find('a',href=person['profile_url'])
        self.assertIsNotNone(old_link)
        self.assertIsNotNone(old_link.find_parent('details'))
        self.assertIn('Earlier saved profile',old_link.get_text())
        self.assertEqual(person,before)

    def test_reviewed_links_and_historical_links_are_separate_in_both_views(self):
        doc=self.sample(); person=self.reviewed_profile(); doc['people']=[person]
        before=copy.deepcopy(doc)
        current_url=person['deep_audit']['profile_url']; old_url=person['profile_url']
        member=original_views.dossier_data(BASE,doc)[0]['team_members'][0]
        self.assertEqual(member['linkedin'],current_url)
        self.assertEqual(member['location'],'Pune')
        dossier_review=BeautifulSoup(member['_review_html'],'html.parser')
        self.assertIn('Reviewed Employer',dossier_review.get_text())
        self.assertIsNotNone(dossier_review.find('a',href=old_url).find_parent('details'))
        career=BeautifulSoup(original_views.career_page(BASE,doc,app.PROFILE),'html.parser')
        for section_id in ('contacts','referral-dossiers'):
            with self.subTest(section=section_id):
                row=career.find(id=section_id).select_one('tbody tr')
                cells=row.find_all('td',recursive=False)
                self.assertIn('Reviewed Employer',cells[0].get_text())
                self.assertIn('Pune',cells[1].get_text())
                self.assertEqual(cells[-1].find('a')['href'],current_url)
                self.assertIn('Search index',cells[-1].get_text())
                self.assertNotIn('Page read',cells[-1].get_text())
                self.assertNotIn('2025-01-01',cells[-1].get_text())
                historical=row.find_all('a',href=old_url)
                self.assertTrue(historical)
                self.assertTrue(all(a.find_parent('details') is not None for a in historical))
        self.assertEqual(doc,before)

    def test_same_review_reaches_both_pages_with_original_style_and_safe_sources(self):
        doc=self.sample()
        review={'status':'reviewed','checked_at':'2026-09-08','summary':'Reviewed company summary','pega_work':'Reviewed sanctions workflow','bangalore_scope':'Project allocation not established','sources':[{'url':'javascript:alert(1)','title':'<script>bad</script>','access':'search_index','summary':'<img src=x onerror=bad()>','checked_at':'2026-09-08'}]}
        doc['companies'][0]['deep_audit']=review
        doc['people'][0]['deep_audit']={'status':'unresolved','checked_at':'2026-09-08','summary':'Checked identity unresolved','certifications':[],'sources':[]}
        doc['gcc_audit']={'company_records_reviewed':1,'company_records_in_scope':1,'profile_records_reviewed':1,'profile_records_in_scope':1}
        rows=original_views.dossier_data(BASE,doc)
        self.assertEqual(rows[0]['projects'],'Reviewed sanctions workflow')
        self.assertEqual(rows[0]['team_members'][0]['title'],'Title not exposed')
        self.assertNotIn('javascript:',str(rows[0]['highlights']))
        self.assertIn('&lt;script&gt;',str(rows[0]['highlights']))
        for html,name in [(original_views.dossiers_page(BASE,doc),'Pega_Deep_Dossiers.html'),(original_views.career_page(BASE,doc,app.PROFILE),'Pega_Career_Intelligence_Hub.html')]:
            soup=BeautifulSoup(html,'html.parser');old=BeautifulSoup((BASE/name).read_text(encoding='utf-8'),'html.parser')
            self.assertEqual(soup.style.get_text(),old.style.get_text())
            self.assertIn('Reviewed sanctions workflow',html)
            ids=[tag['id'] for tag in soup.select('[id]')]
            self.assertEqual(len(ids),len(set(ids)))
        career=BeautifulSoup(original_views.career_page(BASE,doc,app.PROFILE),'html.parser')
        sec=career.find(id='team-dossiers')
        self.assertIn('Reviewed sanctions workflow',sec.find(class_='card').get_text())
        self.assertIsNotNone(sec.find('details'))

if __name__=='__main__':unittest.main()
