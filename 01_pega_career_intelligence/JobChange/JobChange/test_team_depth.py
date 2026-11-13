import tempfile,json,unittest
from pathlib import Path
from unittest.mock import patch
import app
class TeamDepthAndRecoveryTests(unittest.TestCase):
    def test_goal_and_sourced_depth_are_preloaded(self):
        with tempfile.TemporaryDirectory() as folder:
            client=app.create_app(data_dir=folder).test_client()
            self.assertEqual(client.get('/api/bootstrap').get_json()['profile']['goal_ctc'],3500000)
            rows=client.get('/api/team-depth').get_json()['team_depth']
            self.assertGreaterEqual(len(rows),3)
            self.assertEqual(len({d['id'] for d in rows}),len(rows))
            for team in rows:
                self.assertTrue(team['sources'])
                self.assertTrue(team['bangalore_scope'])
                self.assertTrue(team['assessment']['questions_to_ask'])
                for source in team['sources']:
                    self.assertTrue(source['url'].startswith('https://'))
                    self.assertTrue(source['checked_at'])
    def test_global_consulting_type_uses_exact_employer_identity(self):
        from opportunity_data import employer_type_index,company_key
        records=[{'name':'Deloitte India','category':'services','keywords':['Deloitte']},{'name':'Citi','category':'gcc','keywords':['Citi']},{'name':'Deloitte US','category':'global','keywords':['Deloitte']}]
        types=employer_type_index(records)
        self.assertEqual(types[company_key('Deloitte')],'services')
        self.assertEqual(types[company_key('Citi')],'gcc')
        self.assertNotIn(company_key('First Citizens'),types)
    def test_first_citizens_brief_includes_india_legal_employer(self):
        with tempfile.TemporaryDirectory() as folder:
            client=app.create_app(data_dir=folder).test_client()
            rows=client.get('/api/team-depth').get_json()['team_depth']
            first=next(r for r in rows if r['company']=='First Citizens Bank')
            self.assertIn('First Citizens India (FC Global Services India LLP)',first['match_names'])
    def test_dead_process_is_resumable_without_mutating_artifact(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);research=root/'research';research.mkdir()
            saved={'status':'running','coverage':{'total':313,'checked':10},'targets':[],'detail_enrichment':{'status':'running'}}
            path=research/'preloaded_search.json';path.write_text(json.dumps(saved),encoding='utf-8')
            with patch('campaign.campaign_is_locked',return_value=False):
                client=app.create_app(data_dir=root/'data',research_dir=research).test_client()
                response=client.get('/api/campaign').get_json()
            self.assertEqual(response['status'],'interrupted')
            self.assertTrue(response['resume_available'])
            self.assertEqual(json.loads(path.read_text()),saved)
    def test_external_process_remains_running(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);research=root/'research';research.mkdir()
            (research/'preloaded_search.json').write_text(json.dumps({'status':'running','targets':[]}),encoding='utf-8')
            with patch('campaign.campaign_is_locked',return_value=True):
                client=app.create_app(data_dir=root/'data',research_dir=research).test_client()
                self.assertEqual(client.get('/api/campaign').get_json()['status'],'running')
if __name__=='__main__':unittest.main()
