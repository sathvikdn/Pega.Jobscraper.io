"""Offline API coverage for independently sourced employers and search catalogs."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'.deps'))
sys.path.insert(0,str(BASE))
import app as portal_app
import campaign

class ImmediateThread:
    def __init__(self,target,args=(),daemon=None):
        self.target,self.args=target,args
    def start(self):
        self.target(*self.args)

class InvestigationAPITests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='investigation-api-')
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.research=self.root/'research'
        self.research.mkdir()
        self.legacy={'target_id':'gcc-legacy','name':'Legacy Only','category':'gcc','location':'India','keywords':['Legacy Only']}
        self.saved={'target_id':'gcc-legacy','name':'Legacy Only','category':'gcc','location':'India','status':'results','jobs':[{'id':'old-job','company':'Legacy Only','title':'Pega Engineer','location':'Bengaluru','url':'https://jobs.example.com/old','status':'candidate'}]}
        self.fresh=[
            {'id':'fresh-new','name':'New Discovery','category':'services','aliases':['New Discovery India'],'flags':{'bangalore':True},'claims':[],'people':[],'hiring_signals':[]},
            {'id':'fresh-unknown','name':'Unknown Category','category':'unclassified','aliases':[],'flags':{'bangalore':False},'claims':[],'people':[],'hiring_signals':[]},
        ]
        self.write('directory.json',{'records':[self.legacy],'stats':{}})
        self.write('preloaded_search.json',{'targets':[self.saved],'status':'complete'})
        self.write('independent_map.json',{'companies':self.fresh,'stats':{'companies':2}})
        self.application=portal_app.create_app(data_dir=self.root/'data',research_dir=self.research)
        self.application.config['TESTING']=True
        self.client=self.application.test_client()
        self.headers={'X-Career-Token':self.client.get('/api/bootstrap').get_json()['token']}
    def write(self,name,value):
        (self.research/name).write_text(json.dumps(value),encoding='utf-8')
    def post(self,payload):
        return self.client.post('/api/search',json=payload,headers=self.headers)
    def run_mocked(self,payload):
        with patch.object(portal_app.threading,'Thread',ImmediateThread), patch.object(campaign,'run_campaign') as run, patch.object(campaign,'enrich_campaign'), patch.object(campaign,'campaign_is_locked',return_value=False):
            response=self.post(payload)
        return response,run

    def test_investigation_missing_is_explicit_and_does_not_fall_back_to_legacy(self):
        (self.research/'independent_map.json').unlink()
        doc=self.client.get('/api/investigation').get_json()
        self.assertEqual(doc['companies'],[])
        self.assertEqual(doc['status'],'unavailable')
        response,run=self.run_mocked({'catalog_scope':'fresh'})
        self.assertEqual(response.status_code,400)
        run.assert_not_called()

    def test_investigation_and_directory_join_fresh_checkpoint_without_mutating_archive(self):
        record={'target_id':'fresh-new','name':'New Discovery','status':'results','checked_at':'2026-09-08','jobs':[{'url':'https://jobs.example.com/new'}]}
        self.write('preloaded_search.json',{'targets':[self.saved,record]})
        investigation=self.client.get('/api/investigation').get_json()
        self.assertEqual(investigation['companies'][0]['latest_search']['status'],'results')
        self.assertEqual(investigation['companies'][0]['opportunity_count'],1)
        directory=self.client.get('/api/directory').get_json()
        self.assertEqual(len(directory['records']),1)
        self.assertEqual(len(directory['fresh_targets']),2)
        self.assertEqual(directory['fresh_targets'][0]['opportunity_count'],1)
        self.assertNotIn('fresh_targets',json.loads((self.research/'directory.json').read_text()))

    def test_fresh_search_targets_only_new_map_and_preserves_saved_catalog(self):
        response,run=self.run_mocked({'catalog_scope':'fresh','minimum_ctc_lpa':20})
        self.assertEqual(response.status_code,200)
        kwargs=run.call_args.kwargs
        self.assertEqual(kwargs['target_ids'],['fresh-new','fresh-unknown'])
        targets={r['target_id']:r for r in kwargs['data']}
        self.assertEqual(targets['gcc-legacy']['jobs'],self.saved['jobs'])
        self.assertEqual(targets['fresh-new']['keywords'],['New Discovery','New Discovery India'])
        self.assertEqual(targets['fresh-new']['location'],'Bengaluru, Karnataka, India')
        self.assertEqual(targets['fresh-unknown']['location'],'Worldwide')
        self.assertEqual(targets['fresh-unknown']['category'],'unclassified')
        self.assertNotIn('remote_eligibility',targets['fresh-unknown'])

    def test_single_company_resume_inherits_fresh_catalog_and_selection(self):
        response,run=self.run_mocked({'catalog_scope':'fresh','company_id':'fresh-new','minimum_ctc_lpa':35})
        self.assertEqual(response.get_json()['total'],1)
        response,run=self.run_mocked({'resume':True})
        self.assertEqual(response.status_code,200)
        self.assertEqual(run.call_args.kwargs['target_ids'],['fresh-new'])
        self.assertFalse(run.call_args.kwargs['force'])
        preferences=self.client.get('/api/bootstrap').get_json()['search_preferences']
        self.assertEqual(preferences['catalog_scope'],'fresh')
        self.assertEqual(preferences['company_id'],'fresh-new')
        self.assertEqual(preferences['minimum_ctc_lpa'],35)
        self.assertEqual(self.client.get('/api/campaign').get_json()['catalog_scope'],'fresh')

    def test_explicit_legacy_selection_and_unclassified_fresh_filter(self):
        response,run=self.run_mocked({'catalog_scope':'fresh','category':'unclassified'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(run.call_args.kwargs['target_ids'],['fresh-unknown'])
        response,run=self.run_mocked({'catalog_scope':'legacy','resume':True})
        self.assertEqual(response.status_code,200)
        self.assertEqual(run.call_args.kwargs['target_ids'],['gcc-legacy'])

    def test_fresh_detail_enrichment_is_selected_and_resume_uses_cache(self):
        with patch.object(portal_app.threading,'Thread',ImmediateThread), patch.object(campaign,'run_campaign'), patch.object(campaign,'enrich_campaign') as enrich, patch.object(campaign,'campaign_is_locked',return_value=False):
            self.assertEqual(self.post({'catalog_scope':'fresh','company_id':'fresh-new'}).status_code,200)
            self.assertEqual(enrich.call_args.kwargs['target_ids'],['fresh-new'])
            self.assertTrue(enrich.call_args.kwargs['force'])
            self.assertEqual(self.post({'resume':True}).status_code,200)
            self.assertEqual(enrich.call_args.kwargs['target_ids'],['fresh-new'])
            self.assertFalse(enrich.call_args.kwargs['force'])
            self.assertEqual(self.post({'catalog_scope':'legacy'}).status_code,200)
            self.assertNotIn('target_ids',enrich.call_args.kwargs)
            self.assertTrue(enrich.call_args.kwargs['force'])

    def test_unknown_or_invalid_fresh_scopes_do_not_start_worker(self):
        for payload in (
            {'catalog_scope':'fresh','company_id':'gcc-legacy'},
            {'catalog_scope':'fresh','company_id':[]},
            {'catalog_scope':'other'},
            {'catalog_scope':'legacy','company_id':'fresh-new'},
            {'catalog_scope':'fresh','category':'bad'},
            {'catalog_scope':'fresh','minimum_ctc_lpa':True},
        ):
            with self.subTest(payload=payload):
                response,run=self.run_mocked(payload)
                self.assertEqual(response.status_code,400)
                run.assert_not_called()

    def test_fresh_jobs_deduplicate_and_keep_provenance_and_user_notes(self):
        curated={'id':'curated','title':'Pega Engineer','company':'New Discovery','location':'Bengaluru','url':'https://www.linkedin.com/jobs/view/123','status':'open','summary':'Curated source'}
        fresh={**curated,'id':'fresh-copy','url':'https://in.linkedin.com/jobs/view/pega-engineer-123?trk=feed','summary':'Independent description','status':'closed','checked_at':'2026-09-08','experience_min':7,'fit':'stretch','salary':None}
        unique={'id':'fresh-role','title':'Workflow Engineer','company':'Unknown Category','location':'Worldwide','url':'https://jobs.example.com/fresh','status':'candidate'}
        curated['salary']={'currency':'INR','period':'annual','basis':'ctc','amount_min':3500000,'amount_max':3500000}
        self.write('openings.json',{'opportunities':[curated]})
        self.write('fresh_public_jobs.json',{'opportunities':[fresh,unique]})
        # A legacy classification must not fill an independently unclassified employer.
        self.write('directory.json',{'records':[self.legacy,{'name':'Unknown Category','category':'services','keywords':[]}]})
        self.application.extensions['store'].put('pipeline','curated',{'stage':'shortlisted','notes':'Saved note'})
        self.application.extensions['store'].put('verification','curated',{'status':'open','checked_at':'2026-09-07'})
        rows=self.client.get('/api/opportunities?scope=all').get_json()['opportunities']
        duplicate=[r for r in rows if r['url']=='https://www.linkedin.com/jobs/view/123']
        self.assertEqual(len(duplicate),1)
        self.assertTrue(duplicate[0]['independent_discovery'])
        self.assertEqual(duplicate[0]['pipeline']['notes'],'Saved note')
        self.assertEqual(duplicate[0]['status'],'closed')
        self.assertEqual(duplicate[0]['experience_min'],7)
        self.assertEqual(duplicate[0]['fit'],'stretch')
        self.assertEqual(duplicate[0]['summary'],'Independent description')
        self.assertIsNone(duplicate[0]['salary'])
        unique=next(r for r in rows if r['id']=='fresh-role')
        self.assertEqual(unique['employer_type'],'unknown')
        self.assertEqual(unique['remote_eligibility'],'unknown')
        self.assertIsNone(unique['salary'])

    def test_fresh_campaign_jobs_are_marked_by_map_identity(self):
        self.write('preloaded_search.json',{'targets':[{'target_id':'fresh-new','name':'New Discovery','category':'services','jobs':[{'title':'Pega Developer','url':'https://jobs.example.com/campaign-fresh','status':'candidate'}]}]})
        row=self.client.get('/api/opportunities?scope=all').get_json()['opportunities'][0]
        self.assertTrue(row['independent_discovery'])
        self.assertEqual(row['employer_type'],'services')

    def test_employer_signals_keep_status_remote_evidence_and_exclude_nonjobs(self):
        def signal(title,url,**values):
            return {'kind':'employer_job','title':title,'url':url,'location':'Bengaluru','description':'Employer summary','access':'page','checked_at':'2026-09-08',**values}
        self.fresh[0]['hiring_signals']=[
            signal('Pega Developer','https://jobs.example.com/role/1',vacancy_confirmed=True,experience_min=4),
            signal('Pega Architect','https://jobs.example.com/role/2',vacancy_confirmed=True,status='historical',description='Mandatory CLSA required.'),
            signal('Pega Test Engineer','https://jobs.example.com/role/3',location='India - Remote',access='search_index'),
            signal('Careers','https://jobs.example.com/careers'),
            signal('Pega Developer','javascript:alert(1)'),
            signal('Pega Developer','http://127.0.0.1/private'),
            {**signal('Pega Developer','https://jobs.example.com/post'),'kind':'recruiter_post'},
        ]
        self.write('independent_map.json',{'companies':self.fresh})
        rows=[r for r in self.client.get('/api/opportunities?scope=all').get_json()['opportunities'] if r.get('independent_discovery')]
        self.assertEqual(len(rows),3)
        byurl={r['url']:r for r in rows}
        self.assertEqual(byurl['https://jobs.example.com/role/1']['experience_min'],4)
        self.assertIsNone(byurl['https://jobs.example.com/role/1']['salary'])
        self.assertEqual(byurl['https://jobs.example.com/role/2']['status'],'closed')
        self.assertEqual(byurl['https://jobs.example.com/role/2']['fit'],'stretch')
        self.assertEqual(byurl['https://jobs.example.com/role/3']['remote_eligibility'],'india_remote')
        self.assertEqual(byurl['https://jobs.example.com/role/3']['status'],'indexed_only')

    def test_actual_campaign_switches_keep_unselected_jobs_without_network(self):
        def checked(target,client):
            return {'target_id':target['target_id'],'name':target['name'],'category':target['category'],'location':target['location'],'status':'no_matches','checked_at':'2026-09-08','diagnostics':[],'jobs':[]}
        with patch.object(campaign,'PublicClient'), patch.object(campaign,'check_target',side_effect=checked) as checker, patch.object(campaign,'enrich_campaign'):
            with patch.object(portal_app.threading,'Thread') as thread:
                response=self.post({'catalog_scope':'fresh','company_id':'fresh-new'})
                worker,arguments=thread.call_args.kwargs['target'],thread.call_args.kwargs['args']
            worker(*arguments)
            self.assertEqual(response.status_code,200)
            self.assertEqual(self.client.get('/api/status').get_json()['error'],None)
            self.assertEqual([c.args[0]['target_id'] for c in checker.call_args_list],['fresh-new'])
            saved=campaign.load_campaign(self.research/'preloaded_search.json')
            self.assertEqual(next(r for r in saved['targets'] if r['target_id']=='gcc-legacy')['jobs'],self.saved['jobs'])
            checker.reset_mock()
            with patch.object(portal_app.threading,'Thread') as thread:
                response=self.post({'catalog_scope':'legacy'})
                worker,arguments=thread.call_args.kwargs['target'],thread.call_args.kwargs['args']
            worker(*arguments)
            self.assertEqual(response.status_code,200)
            self.assertEqual([c.args[0]['target_id'] for c in checker.call_args_list],['gcc-legacy'])
            saved=campaign.load_campaign(self.research/'preloaded_search.json')
            self.assertEqual({r['target_id'] for r in saved['targets']},{'gcc-legacy','fresh-new','fresh-unknown'})
            self.assertEqual(next(r for r in saved['targets'] if r['target_id']=='fresh-new')['status'],'no_matches')

if __name__=='__main__':
    unittest.main()
