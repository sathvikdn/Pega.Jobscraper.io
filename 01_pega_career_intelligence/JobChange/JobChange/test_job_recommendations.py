"""Integration checks for strict defaults, cached JDs, notes and refresh protection."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'.deps'));sys.path.insert(0,str(BASE))
import app
import job_details

class RecommendationAPITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.research=root/'research';self.research.mkdir()
        self.data=root/'data'
        self.target={'target_id':'gcc-example','name':'Example','category':'gcc','priority':'top30','location':'India','keywords':['Example']}
        (self.research/'directory.json').write_text(json.dumps({'records':[self.target]}))
        self.rows=[]
        for ident,description in [
            ('fit','Develop Pega applications and REST services. Required experience: 3–5 years in Pega development. CSSA certification required.'),
            ('stretch','Develop Pega applications. Required experience: 5–7 years in Pega development.'),
            ('nonpega','Develop Java microservices. Required experience: 3–5 years in Java development.'),
            ('senior','Develop Pega applications. Required experience: 8–10 years in Pega development.'),
            ('unknown','Develop Pega applications and REST services.'),
        ]:
            self.rows.append({'id':ident,'title':'Pega Developer','company':'Example','location':'Bengaluru, India',
                'url':'https://example.com/jobs/'+ident,'status':'candidate','checked_at':'2026-09-01',
                'description_text':description,'description_complete':True,'description_source_url':'https://example.com/jobs/'+ident,
                'description_checked_at':'2026-09-01','job_detail_status':'read','job_detail_checked_at':'2026-09-01'})
        self.rows.append({'id':'card','title':'Pega Developer','company':'Example','location':'India','url':'https://example.com/jobs/card','status':'candidate','summary':'Pega 4 years','skills':['Pega'],'experience_min':4})
        (self.research/'openings.json').write_text(json.dumps({'opportunities':self.rows}))
        self.application=app.create_app(self.data,self.research)
        self.client=self.application.test_client()
        self.token={'X-Career-Token':self.client.get('/api/bootstrap').get_json()['token']}
        self.store=self.application.extensions['store']

    def test_defaults_exclude_nonpega_senior_and_unverified(self):
        body=self.client.get('/api/opportunities').get_json()
        self.assertEqual({r['id'] for r in body['opportunities']},{'fit','stretch'})
        self.assertEqual(body['policy_counts'],{'recommended':1,'stretch':1,'review':2,'excluded':2})
        scores={r['id']:r['resume_match']['score'] for r in body['opportunities']}
        self.assertIsInstance(scores['fit'],int)

    def test_review_and_archive_are_explicit(self):
        review=self.client.get('/api/opportunities?scope=review').get_json()['opportunities']
        self.assertEqual({r['id'] for r in review},{'unknown','card'})
        self.assertIsNone(next(r for r in review if r['id']=='card')['resume_match']['score'])
        self.assertEqual(len(self.client.get('/api/opportunities?scope=all').get_json()['opportunities']),6)
        self.assertEqual(self.client.get('/api/opportunities?scope=anything').status_code,400)

    def test_original_scan_defaults_and_scope_have_same_policy(self):
        all_data=self.client.get('/api/scan-results').get_json()
        self.assertEqual({j['id'] for c in all_data['companies'] for j in c['jobs']},{'fit','stretch','unknown','card','nonpega','senior'})
        data=self.client.get('/api/scan-results?scope=recommended').get_json()
        self.assertEqual({j['id'] for c in data['companies'] for j in c['jobs']},{'fit','stretch'})
        self.assertEqual(data['policy_counts']['excluded'],2)
        self.assertEqual({j['id'] for c in self.client.get('/api/scan-results?scope=review').get_json()['companies'] for j in c['jobs']},{'unknown','card'})
        self.assertEqual(self.client.get('/api/scan-results?scope=unsafe').status_code,400)

    def test_view_does_not_fetch_and_nonrecommended_remains_accessible(self):
        with patch('campaign.enrich_job') as fetch:
            row=self.client.get('/api/opportunities/nonpega').get_json()['opportunity']
            self.assertIn('Java microservices',row['description_text'])
            self.assertEqual(row['recommendation']['status'],'excluded')
            fetch.assert_not_called()
        self.assertEqual(self.client.get('/api/opportunities/missing').status_code,404)

    def test_refresh_requires_csrf_and_known_identity(self):
        with patch('campaign.enrich_job') as fetch:
            self.assertEqual(self.client.post('/api/opportunities/fit/description',json={}).status_code,403)
            self.assertEqual(self.client.post('/api/opportunities/missing/description',json={},headers=self.token).status_code,404)
            self.assertEqual(self.client.post('/api/opportunities/fit/description',json={},headers={**self.token,'Origin':'https://evil.example'}).status_code,403)
            fetch.assert_not_called()

    def test_successful_changed_description_removes_recommendation_keeps_notes(self):
        self.store.put('pipeline','fit',{'stage':'shortlisted','notes':'My note'})
        def changed(row,client):
            row=copy.deepcopy(row)
            row.update(description_text='Develop Java microservices. Required experience: 3–5 years in Java development.',
                       description_checked_at='2099-01-01',job_detail_checked_at='2099-01-01',skills=['Java'])
            return row
        with patch('campaign.enrich_job',side_effect=changed):
            response=self.client.post('/api/opportunities/fit/description',json={},headers=self.token)
        self.assertEqual(response.status_code,200)
        self.assertFalse(response.get_json()['opportunity']['recommendation']['eligible'])
        restarted=app.create_app(self.data,self.research).test_client()
        row=restarted.get('/api/opportunities/fit').get_json()['opportunity']
        self.assertIn('Java microservices',row['description_text'])
        self.assertEqual(row['pipeline'],{'stage':'shortlisted','notes':'My note'})
        self.assertNotIn('fit',{r['id'] for r in restarted.get('/api/opportunities').get_json()['opportunities']})

    def test_failed_latest_read_is_review_not_closed_and_retains_saved_text(self):
        def failed(row,client):
            return {**row,'job_detail_status':'unavailable','job_detail_checked_at':'2099-01-01','job_detail_diagnostic':{'http_status':429}}
        with patch('campaign.enrich_job',side_effect=failed):
            row=self.client.post('/api/opportunities/fit/description',json={},headers=self.token).get_json()['opportunity']
        self.assertEqual(row['recommendation']['status'],'review')
        self.assertEqual(row['status'],'candidate')
        self.assertIn('Develop Pega',row['description_text'])
        self.assertEqual(row['description_checked_at'],'2026-09-01')
        self.assertIsNone(row['resume_match']['score'])

    def test_new_checkpoint_description_overrides_older_curated_record_without_raw_bypass(self):
        newer={**self.rows[0],'id':'different-source-id','description_text':'Develop Java microservices with 4 years experience.',
               'job_detail_checked_at':'2098-01-01','description_checked_at':'2098-01-01'}
        (self.research/'preloaded_search.json').write_text(json.dumps({'targets':[{**self.target,'jobs':[newer]}]}))
        allrows=self.client.get('/api/opportunities?scope=all').get_json()['opportunities']
        row=next(r for r in allrows if r['url']==newer['url'])
        self.assertEqual(row['id'],'fit')
        self.assertEqual(row['recommendation']['status'],'excluded')
        self.assertNotIn('fit',{j['id'] for c in self.client.get('/api/scan-results?scope=recommended').get_json()['companies'] for j in c['jobs']})

    def test_reset_excludes_legacy_seeds_and_preserves_identity_on_new_discovery(self):
        self.store.put('meta','jobs_reset_at','2026-09-08T12:00:00+00:00')
        self.store.put('meta','job_identity_aliases',{self.rows[0]['url']:'fit'})
        self.store.put('pipeline','fit',{'stage':'shortlisted','notes':'Preserve my note'})
        self.assertEqual(self.client.get('/api/opportunities?scope=all').get_json()['opportunities'],[])
        stale={**self.rows[0],'id':'new-id'}
        (self.research/'preloaded_search.json').write_text(json.dumps({'targets':[{**self.target,'jobs':[stale]}]}))
        self.assertEqual(self.client.get('/api/opportunities?scope=all').get_json()['opportunities'],[])
        fresh={**stale,'checked_at':'2026-09-08T13:00:00+00:00','job_detail_checked_at':'2026-09-08T13:01:00+00:00'}
        (self.research/'preloaded_search.json').write_text(json.dumps({'targets':[{**self.target,'jobs':[fresh]}]}))
        rows=self.client.get('/api/opportunities').get_json()['opportunities']
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['id'],'fit')
        self.assertEqual(rows[0]['pipeline']['notes'],'Preserve my note')

class DescriptionSafetyTests(unittest.TestCase):
    def test_private_destination_rejected_before_request(self):
        with patch.object(job_details,'public_url',side_effect=ValueError('Private address')),patch.object(job_details.requests,'get') as fetch:
            html,diagnostic=job_details.PublicDescriptionClient(spacing=0).get('https://127.0.0.1/private')
        self.assertIsNone(html);fetch.assert_not_called()

    def test_saved_descriptor_does_not_override_newer_scan_or_user_fields(self):
        job={'id':'stable','url':'https://example.com/j','pipeline':{'notes':'keep'},'job_detail_checked_at':'2026-09-08'}
        old={'id':'wrong','job_detail_checked_at':'2026-09-01','description_text':'older'}
        self.assertEqual(job_details.overlay_description(job,old),job)
        newer={**old,'job_detail_checked_at':'2026-09-09'}
        merged=job_details.overlay_description(job,newer)
        self.assertEqual(merged['id'],'stable');self.assertEqual(merged['pipeline']['notes'],'keep')
        self.assertEqual(merged['description_text'],'older')

if __name__=='__main__':unittest.main()
