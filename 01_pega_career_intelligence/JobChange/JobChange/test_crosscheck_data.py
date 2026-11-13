import json,tempfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'.deps'))
import master_catalog,original_views,investigation_data

class CrosscheckDataTests(unittest.TestCase):
    def test_same_day_source_improvement_preserves_closure_precedence(self):
        base={'url':'https://example.com/jobs/pega','title':'Pega Developer','checked_at':'2026-09-08','status':'unverified','limitations':[]}
        old={**base,'access':'search_index','description':'Could not fetch'}
        page={**base,'access':'page','description':'Employer listing observed','limitations':['Application not checked']}
        current={**base,'access':'page','description':'Employer page read; application unavailable','application_access':'unavailable','limitations':['Experience unknown']}
        result=investigation_data.reconcile_signals([old,page,current])[0]
        self.assertEqual(result['description'],current['description'])
        self.assertEqual(result['application_access'],'unavailable')
        self.assertEqual(len(result['observations']),3)
        self.assertIn('Earlier observation: Application not checked',result['limitations'])
        closed={**old,'status':'closed'}
        self.assertEqual(investigation_data.reconcile_signals([closed,current])[0]['status'],'closed')
    def test_exact_alias_union_preserves_people_claims_targets_and_old_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);root=base/'research';root.mkdir()
            def save(name,doc):(root/name).write_text(json.dumps(doc),encoding='utf-8')
            save('master_catalog.json',{'companies':[{'id':'old-alpha','name':'Alpha','aliases':[],'source_company_ids':['older-alpha-bookmark']},{'id':'old-beta','name':'Beta','aliases':[]}]})
            cs=[{'id':'fresh-'+n.lower(),'name':n,'category':'services','aliases':[],'claims':[{'type':'project','text':n}],'flags':{'bangalore':True} if n=='Alpha' else {'pega':True},'hiring_signals':[],'limitations':[]} for n in ('Alpha','Beta')]
            save('independent_map.json',{'companies':cs,'people':[{'name':'Person','company':'Beta','company_id':'fresh-beta','profile_url':'https://www.linkedin.com/in/person','source_url':'https://www.linkedin.com/in/person','access':'search_index','title':'Developer'}]})
            save('directory.json',{'records':[{'name':'Beta','target_id':'original-beta','category':'services'}]})
            save('team_depth_fixture.json',{'team_depth':[{'company':'Alpha','match_names':['Beta'],'category':'services','people':[]}]})
            doc=master_catalog.build(base,root)
            self.assertEqual(len(doc['companies']),1)
            c=doc['companies'][0];self.assertEqual({x['text'] for x in c['claims']},{'Alpha','Beta'})
            self.assertTrue({'old-alpha','old-beta','fresh-alpha','fresh-beta','older-alpha-bookmark'}<={c['id'],*c['source_company_ids']})
            self.assertEqual(c['search_targets'][0]['target_id'],'original-beta')
            self.assertTrue(c['flags']['bangalore']);self.assertTrue(c['flags']['pega'])
            self.assertEqual(doc['people'][0]['company_ids'],[c['id']])
            self.assertEqual(doc['people'][0]['observations'][0]['company_id'],c['id'])
    def test_crosschecked_unknown_title_cannot_borrow_an_old_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);root=base/'research';root.mkdir()
            p={'name':'Person','profile_url':'https://www.linkedin.com/in/person','source_url':'https://www.linkedin.com/in/person','company_id':'fresh-a','company':'Alpha','access':'search_index'}
            doc={'companies':[{'id':'fresh-a','name':'Alpha','category':'gcc','aliases':[],'claims':[],'hiring_signals':[],'limitations':[],'flags':{}}],'people':[{**p,'observations':[{**p,'title':'Old guessed role'},{**p,'title':None,'crosschecked':True,'work_summary':'Only employer is visible'}]}]}
            (root/'independent_map.json').write_text(json.dumps(doc),encoding='utf-8')
            result=master_catalog.build(base,root)['people'][0]
            self.assertIsNone(result['title']);self.assertTrue(result['crosschecked'])
            self.assertEqual(len(result['observations']),2)
    def test_older_certifications_keep_their_qualification(self):
        p={'certifications':['CSSA','CLSA'],'observations':[{'access':'search_index','certifications':['CSSA']},{'access':'legacy','certifications':['CLSA']}]}
        self.assertEqual(original_views.certifications(p),['CSSA','CLSA (earlier source)'])
    def test_crosschecks_are_prominent_and_keep_safe_text(self):
        c={'claims':[{'type':'project','text':'older description'},{'type':'crosscheck','verdict':'not_verified','text':'<script>bad</script>'}]}
        rows=original_views.claims(c);self.assertEqual(rows[0]['type'],'crosscheck')
        self.assertIn('not verified',original_views.claim_text(rows[0]))
        self.assertNotIn('<script>',original_views.esc(original_views.claim_text(rows[0])))

if __name__=='__main__':unittest.main()
