import copy,json,tempfile,unittest
from pathlib import Path
import people_research

class PeopleResearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.doc={'companies':[{'id':'a','name':'Bank A','aliases':['Bank A India'],'source_company_ids':['old-a']},{'id':'b','name':'Bank B'}],
          'people':[{'id':'keep-id','identity_key':'linkedin:alex','name':'Alex','company_id':'a','company_ids':['a'],'profile_url':'https://www.linkedin.com/in/alex','title':'Earlier developer','observations':[{'access':'legacy','title':'Earlier developer'}],'deep_audit':{'status':'partially_supported','title':'Developer','checked_at':'2026-09-08'}}],
          'stats':{'people_records':1},'pipeline':{'keep-id':'Keep notes'}}
        self.row={'name':'Alex','company_id':'a','profile_url':'https://in.linkedin.com/in/alex/','source_url':'https://in.linkedin.com/in/alex/','title':'Pega Lead System Architect','employer_as_stated':'Bank A','access':'search_index','checked_at':'2026-09-09'}
    def write(self,rows,**extra):
        (self.root/people_research.FILENAME).write_text(json.dumps({'research_date':'2026-09-09','people':rows,**extra}),encoding='utf-8')
    def test_preserves_identity_original_records_company_and_pipeline(self):
        before=copy.deepcopy(self.doc);self.write([self.row]);out=people_research.attach(self.doc,self.root);p=out['people'][0]
        self.assertEqual(self.doc,before);self.assertEqual(out['companies'],before['companies']);self.assertEqual(out['pipeline'],before['pipeline'])
        self.assertEqual(p['id'],'keep-id');self.assertEqual(p['profile_url'],before['people'][0]['profile_url']);self.assertEqual(p['observations'][0],before['people'][0]['observations'][0]);self.assertEqual(p['research_history'],[before['people'][0]['deep_audit']]);self.assertEqual(p['deep_audit']['title'],self.row['title'])
    def test_new_employer_keeps_history(self):
        self.write([{**self.row,'company_id':'b','employer_as_stated':'Bank B'}]);p=people_research.attach(self.doc,self.root)['people'][0]
        self.assertEqual(p['company_id'],'a');self.assertEqual(p['company_ids'],['a','b']);self.assertEqual(p['latest_company_id'],'b');self.assertEqual(p['deep_audit']['company_id'],'b')
    def test_blocked_only_does_not_override(self):
        self.write([{**self.row,'status':'blocked','access':'page','title':None}]);p=people_research.attach(self.doc,self.root)['people'][0]
        self.assertEqual(p['deep_audit'],self.doc['people'][0]['deep_audit']);self.assertEqual(p['observations'],self.doc['people'][0]['observations']);self.assertEqual(p['research_checks'][0]['status'],'blocked')
    def test_duplicate_rows_and_repeated_attach_idempotent(self):
        new={**self.row,'name':'Jordan','profile_url':'https://www.linkedin.com/in/jordan','source_url':'https://www.linkedin.com/in/jordan'}
        self.write([self.row,self.row,new,new]);a=people_research.attach(self.doc,self.root);b=people_research.attach(a,self.root)
        self.assertEqual(a,b);self.assertEqual(len(a['people']),2);self.assertEqual(a['people_refresh']['people_added'],1);self.assertEqual(a['people_refresh']['people_refreshed'],1)
    def test_unknown_company_and_untrusted_profile_ignored(self):
        for patch in ({'company_id':'unknown'},{'profile_url':'javascript:alert(1)'},{'profile_url':'https://www.linkedin.com/search/results/people/?keywords=Alex'}):
            with self.subTest(patch=patch):
                self.write([{**self.row,**patch}]);out=people_research.attach(self.doc,self.root);self.assertEqual(out['people'],self.doc['people']);self.assertTrue(out['people_refresh']['diagnostics'])
    def test_untrusted_sources_cannot_upgrade(self):
        for url in ['javascript:alert(1)','http://example.com/a','https://127.0.0.1/a','https://localhost/a','https://192.168.0.1/a','https://x:y@example.com/a','https://[','https://example.com:bad/a']:
            with self.subTest(url=url):
                self.write([{**self.row,'source_url':url}]);out=people_research.attach(self.doc,self.root);self.assertEqual(out['people'][0]['deep_audit'],self.doc['people'][0]['deep_audit']);self.assertEqual(out['people_refresh']['people_reviewed'],0)
    def test_missing_or_malformed_file_returns_deep_copy(self):
        out=people_research.attach(self.doc,self.root);self.assertEqual(out,self.doc);self.assertIsNot(out['people'][0],self.doc['people'][0])
        for content in ['{bad','[]','{"people":3}']:
            (self.root/people_research.FILENAME).write_text(content);self.assertEqual(people_research.attach(self.doc,self.root),self.doc)
    def test_alias_and_older_observation(self):
        self.write([{**self.row,'company_id':'old-a','checked_at':'2025-01-01'}]);out=people_research.attach(self.doc,self.root);p=out['people'][0]
        self.assertEqual(p['deep_audit'],self.doc['people'][0]['deep_audit']);self.assertEqual(len(p['observations']),2);self.assertEqual(p['research_history'][0]['company_id'],'a')
    def test_same_name_different_profile_is_separate(self):
        self.write([{**self.row,'profile_url':'https://www.linkedin.com/in/other','source_url':'https://www.linkedin.com/in/other'}]);out=people_research.attach(self.doc,self.root)
        self.assertEqual(len(out['people']),2);self.assertEqual(out['people'][0],self.doc['people'][0])
    def test_no_url_requires_unique_name_employer(self):
        self.write([{**self.row,'profile_url':None,'source_url':'https://www.pega.com/speakers/alex'}]);out=people_research.attach(self.doc,self.root);self.assertEqual(len(out['people']),1)
        self.doc['people'].append({**copy.deepcopy(self.doc['people'][0]),'id':'other','identity_key':'linkedin:other','profile_url':'https://www.linkedin.com/in/other'})
        out=people_research.attach(self.doc,self.root);self.assertEqual(out['people'],self.doc['people'])
    def test_nested_schema_official_page_and_profile_access_separate(self):
        raw={**self.row,'access':'direct_page','profile_access':'search_index','source_url':'https://www.pega.com/events/a','title':None,'sources':[{'url':'https://www.pega.com/events/a','access':'direct_page'},{'url':self.row['profile_url'],'access':'search_index'}]}
        (self.root/people_research.FILENAME).write_text(json.dumps({'research_date':'2026-09-09','companies':[{'company_id':'a','name':'Bank A','people':[raw]}]}))
        out=people_research.attach(self.doc,self.root);r=out['people'][0]['deep_audit'];self.assertIsNone(r['title']);self.assertEqual(r['sources'][0]['access'],'page');self.assertEqual(r['sources'][1]['access'],'search_index');self.assertFalse(r['current_employment_verified'])
    def test_explicit_id_cannot_merge_different_linkedin_identity(self):
        self.write([{**self.row,'existing_person_id':'keep-id','profile_url':'https://www.linkedin.com/in/other','source_url':'https://www.linkedin.com/in/other'}]);out=people_research.attach(self.doc,self.root)
        self.assertEqual(len(out['people']),2);self.assertEqual(out['people'][0],self.doc['people'][0])
    def test_stats_update_without_changing_other_catalog_counts(self):
        self.doc['stats'].update(unique_linkedin_profiles=1,people_observations=1,companies=2)
        self.write([{**self.row,'name':'Jordan','profile_url':'https://www.linkedin.com/in/jordan','source_url':'https://www.linkedin.com/in/jordan'}]);out=people_research.attach(self.doc,self.root)
        self.assertEqual(out['stats']['unique_linkedin_profiles'],2);self.assertEqual(out['stats']['people_observations'],2);self.assertEqual(out['stats']['companies'],2)
    def test_refresh_missing_title_does_not_inherit_seniority(self):
        self.write([{**self.row,'title':None}]);p=people_research.attach(self.doc,self.root)['people'][0];self.assertIsNone(p['deep_audit']['title']);self.assertEqual(p['title'],'Earlier developer')

if __name__=='__main__':unittest.main()
