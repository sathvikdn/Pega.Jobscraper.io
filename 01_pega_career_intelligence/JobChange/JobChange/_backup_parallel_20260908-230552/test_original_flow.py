import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'.deps'));sys.path.insert(0,str(BASE))
import app,portal_scan,original_views
from bs4 import BeautifulSoup

def target(i,category='gcc',priority='top30',location='India'):
    return {'target_id':str(i),'name':'Company '+str(i),'category':category,'priority':priority,'location':location,'keywords':['Company '+str(i)]}

class OriginalFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);self.research=root/'research';self.research.mkdir()
        self.records=[target(i) for i in range(25)]+[target('s','services','si_top'),target('us','global','remote_top','United States'),target('world','global','remote_top','Worldwide')]
        (self.research/'directory.json').write_text(json.dumps({'records':self.records}))
        self.doc={'companies':[{'id':'fresh-example','name':'Fresh Example','category':'services','aliases':['Fresh Example'],'flags':{'pega':True},'claims':[],'people':[],'hiring_signals':[],'limitations':[]}],'people':[],'stats':{'companies':1,'people_records':0},'research_date':'2026-09-08'}
        (self.research/'independent_map.json').write_text(json.dumps(self.doc))
        self.application=app.create_app(root/'data',self.research);self.client=self.application.test_client()
        self.headers={'X-Career-Token':self.client.get('/api/bootstrap').get_json()['token']}
    def test_exact_presets_and_counts(self):
        options=self.client.get('/api/scan-options').get_json()
        self.assertEqual([x['count'] for x in options['categories']['gcc']],[10,20,25])
        self.assertEqual(options['categories']['si'][-1]['count'],2)
        self.assertEqual(len(portal_scan.select_targets(self.records,'remote_us')),1)
        self.assertEqual(len(portal_scan.select_targets(self.records,'remote_top')),2)
        self.assertEqual(options['total_targets'],29)
    def test_button_dispatches_selected_python_worker_and_rejects_overlap(self):
        with patch.object(app.threading,'Thread') as thread:
            for mode,count in [('gcc_top10',10),('gcc_top20',20),('gcc_all',25)]:
                self.application.extensions['scan_state']['running']=False
                response=self.client.post('/api/scan',json={'mode':mode},headers=self.headers)
                self.assertEqual(response.status_code,200);self.assertEqual(response.get_json()['total'],count)
                args=thread.call_args.kwargs['args'];self.assertEqual(len(args[0]),count);self.assertTrue(args[2])
                session=self.application.extensions['store'].get('meta','scanner_selection')
                self.assertEqual(session['mode'],mode);self.assertEqual(len(session['targets']),count)
            self.assertEqual(self.client.post('/api/scan',json={'mode':'all'},headers=self.headers).status_code,409)
    def test_resume_uses_frozen_snapshot_and_baseline(self):
        with patch.object(app.threading,'Thread') as thread:
            self.client.post('/api/scan',json={'mode':'gcc_top10'},headers=self.headers)
            saved=self.application.extensions['store'].get('meta','scanner_selection')
            self.application.extensions['scan_state']['running']=False
            (self.research/'directory.json').write_text(json.dumps({'records':list(reversed(self.records))}))
            response=self.client.post('/api/scan',json={'mode':'all','resume':True},headers=self.headers)
            self.assertEqual(response.status_code,200)
            args=thread.call_args.kwargs['args']
            self.assertEqual(args[0],saved['targets']);self.assertFalse(args[2])
    def test_invalid_mode_and_csrf_do_not_start_python(self):
        with patch.object(app.threading,'Thread') as thread:
            self.assertEqual(self.client.post('/api/scan',json={'mode':'../other.py'},headers=self.headers).status_code,400)
            self.assertEqual(self.client.post('/api/scan',json={'mode':'all'}).status_code,403)
            thread.assert_not_called()
    def test_python_executes_selected_ids_and_preserves_unselected_records(self):
        import threading,campaign
        with patch.object(campaign,'load_campaign',return_value={'targets':[target('saved')]}),patch.object(campaign,'run_campaign') as run,patch.object(campaign,'enrich_campaign') as enrich:
            portal_scan.run_scan(self.records[:10],self.records,self.research/'checkpoint.json',lambda _:None,threading.Event())
            self.assertEqual(run.call_args.kwargs['target_ids'],[str(i) for i in range(10)])
            self.assertIn('saved',{t['target_id'] for t in run.call_args.kwargs['data']})
            self.assertEqual(enrich.call_args.kwargs['target_ids'],run.call_args.kwargs['target_ids'])
    def test_selected_region_excludes_unselected_campaign_and_foreign_seed(self):
        selected=[target('india')]
        jobs=[{'id':'us','company':'Company india','title':'Pega Engineer','location':'New York','country':'United States','target_id':'us','url':'https://example.com/jobs/1','status':'candidate'},
              {'id':'seed','company':'Company india','title':'Pega Engineer','location':'New York','country':'United States','url':'https://example.com/jobs/2','status':'open'}]
        self.assertEqual(portal_scan.grouped_results(jobs,selected,{'targets':[]})[0]['jobs'],[])
    def test_newly_read_closed_description_overrides_stale_curated_open(self):
        t=target('india');url='https://example.com/jobs/1'
        job={'id':'stable','company':t['name'],'title':'Pega Engineer','url':url,'status':'open','checked_at':'2026-09-01'}
        newer={**job,'status':'closed','checked_at':'2026-09-08','job_detail_status':'read','job_detail_checked_at':'2026-09-08'}
        result=portal_scan.grouped_results([job],[t],{'targets':[{**t,'jobs':[newer]}]})
        self.assertEqual(result[0]['jobs'],[])
    def test_baseline_survives_newly_normalized_checkpoint_job(self):
        t=target('india');url='https://example.com/jobs/1'
        job={'id':'stable','company':t['name'],'title':'Pega Engineer','url':url,'status':'open','checked_at':'2026-09-01'}
        newer={**job,'checked_at':'2026-09-08','job_detail_status':'read','job_detail_checked_at':'2026-09-08'}
        result=portal_scan.grouped_results([job],[t],{'targets':[{**t,'jobs':[newer]}]},['stable'])
        self.assertFalse(result[0]['jobs'][0]['is_new'])
        result=portal_scan.grouped_results([],[t],{'targets':[{**t,'jobs':[newer]}]},[])
        self.assertTrue(result[0]['jobs'][0]['is_new'])
    def test_expired_and_explicit_foreign_location_without_country_hidden(self):
        t=target('india')
        rows=[{'id':'expired','company':t['name'],'title':'Pega Engineer','url':'https://example.com/jobs/1','status':'open','closing_at':'2020-01-01'},
              {'id':'foreign','company':t['name'],'title':'Pega Engineer','url':'https://example.com/jobs/2','status':'open','location':'New York, United States'}]
        self.assertEqual(portal_scan.grouped_results(rows,[t],{'targets':[]})[0]['jobs'],[])
    def test_unknown_and_fixed_salary_retained_explicit_low_ctc_excluded(self):
        self.assertTrue(portal_scan.included_salary({'salary':None}))
        base={'currency':'INR','period':'annual','amount_min':1500000,'amount_max':1900000}
        self.assertTrue(portal_scan.included_salary({'salary':{**base,'basis':'fixed'}}))
        self.assertFalse(portal_scan.included_salary({'salary':{**base,'basis':'ctc'}}))
    def test_original_routes_and_dossier_safe_data(self):
        for route,marker in [('/','id="scanScreen"'),('/library/career-hub','class="sidebar"'),('/library/dossiers',"let activeSector='all'")]:
            response=self.client.get(route)
            self.assertEqual(response.status_code,200)
            page=response.get_data(as_text=True);self.assertIn(marker,page);self.assertNotIn('/static/classic.js',page)
        original=(BASE/'Pega_Deep_Dossiers.html').read_text(encoding='utf-8')
        rendered=self.client.get('/library/dossiers').get_data(as_text=True)
        self.assertEqual(BeautifulSoup(original,'html.parser').style.get_text(),BeautifulSoup(rendered,'html.parser').style.get_text())
        unsafe=copy.deepcopy(self.doc);unsafe['companies'][0]['name']='<img src=x onerror=alert(1)>'
        page=original_views.dossiers_page(BASE,unsafe)
        self.assertNotIn('<img src=x',page);self.assertIn('company_0',page);self.assertNotIn("c.name.replace(",page)
    def test_malformed_urls_and_evidence_text_are_preserved_safely(self):
        self.assertEqual(original_views.safe_url('https://['),'')
        doc=copy.deepcopy(self.doc)
        doc['stats']['people_records']='0;globalThis.INJECTED=true'
        doc['companies'][0]['claims']=[{'type':'project','text':'Around ~10 people growing adoption','source_url':'https://[','confidence':'inference'}]
        page=original_views.dossiers_page(BASE,doc)
        self.assertNotIn('globalThis.INJECTED',page)
        self.assertIn('Around ~10 people growing adoption',page)
        self.assertIn('Inference:',page)
    def test_interrupted_scan_is_reported_after_restart(self):
        store=self.application.extensions['store'];store.put('meta','scanner_selection',{'mode':'gcc_top10','status':'running','targets':self.records[:10]})
        self.application.extensions['scan_state']['running']=False
        response=self.client.get('/api/status').get_json()
        self.assertEqual(response['scanner']['status'],'interrupted')

if __name__=='__main__':unittest.main()
