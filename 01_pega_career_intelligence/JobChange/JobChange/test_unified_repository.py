import tempfile
import threading
import unittest
from pathlib import Path

from storage import Store
from normalizer import clean_company, normalize_job, pega_evidence


class UnifiedRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'jobs.sqlite3')

    def job(self, url, city='Bengaluru', requisition=None):
        return {'title': 'Pega Developer', 'company': 'Truviq systems', 'location': city,
                'url': url, 'source': 'test', 'experience_min': 4, 'experience_max': 6,
                'company_domain': 'truviq.com', 'requisition_id': requisition}

    def test_jsonld_preserves_description_and_salary_basis(self):
        import json
        from normalizer import jsonld_jobs,from_jobposting
        posting={'@type':'JobPosting','title':'Pega Developer','url':'/jobs/1','hiringOrganization':{'name':'Truviq systems'},
                 'description':'Required: hands-on Pega development with case design. 4 to 6 years of experience.',
                 'baseSalary':{'currency':'INR','value':{'minValue':2000000,'maxValue':3000000,'unitText':'YEAR'}}}
        document='<script type="application/ld+json">'+json.dumps({'@graph':[posting]})+'</script>'
        parsed=from_jobposting(next(jsonld_jobs(document)),'https://example.com/jobs')
        self.assertEqual(parsed['url'],'https://example.com/jobs/1')
        self.assertEqual(parsed['salary']['basis'],'base_salary')
        self.assertEqual(parsed['salary']['period'],'annual')
        self.assertTrue(parsed['description_complete'])

    def test_company_cleaning(self):
        self.assertEqual(clean_company('Truviq systems —Bengaluru, Karnataka4'), 'Truviq Systems')
        self.assertEqual(clean_company('Barclays — Pune, Maharashtra3.9'), 'Barclays')
        self.assertEqual(clean_company('Pega Developer', title='Pega Developer'), '')
        self.assertEqual(clean_company('New York Life'), 'New York Life')

    def test_verified_company_aliases_do_not_guess_entities(self):
        self.store.register_company('Commonwealth Bank',aliases=['CBA'],employer_type='gcc',verified=True)
        self.store.save_job_batch('run1','test',[dict(self.job('https://example.com/job/alias'),company='CBA')])
        row=self.store.list_jobs()[0]
        self.assertEqual(row['company'],'Commonwealth Bank')
        self.assertEqual(row['employer_type'],'gcc')
        with self.assertRaises(ValueError):self.store.register_company('Another Bank',aliases=['CBA'])

    def test_cross_board_probable_match_retains_all_sources(self):
        for source, url in [('LinkedIn','https://www.linkedin.com/jobs/view/123'),
                            ('Indeed','https://in.indeed.com/viewjob?jk=abc'),
                            ('Glassdoor','https://www.glassdoor.co.in/job-listing/abc')]:
            self.store.save_job_batch('run1', source, [dict(self.job(url), source=source)])
        jobs = self.store.list_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(len(jobs[0]['sources']), 3)
        self.assertEqual(jobs[0]['match_basis'], 'probable')

    def test_distinct_city_and_requisitions_survive(self):
        rows = [self.job('https://truviq.com/jobs/1', requisition='1'),
                self.job('https://truviq.com/jobs/2', requisition='2'),
                self.job('https://truviq.com/jobs/3', city='Pune', requisition='3')]
        self.store.save_job_batch('run1', 'employer', rows)
        self.assertEqual(len(self.store.list_jobs()), 3)

    def test_exact_requisition_merges_different_urls(self):
        self.store.save_job_batch('run1', 'employer', [self.job('https://truviq.com/jobs/1', requisition='R1')])
        self.store.save_job_batch('run2', 'board', [self.job('https://in.indeed.com/viewjob?jk=xyz', requisition='R1')])
        self.assertEqual(len(self.store.list_jobs()), 1)

    def test_interrupted_batch_rolls_back_every_table(self):
        stop = threading.Event()
        def interrupted():
            yield self.job('https://truviq.com/jobs/1')
            stop.set()
            yield self.job('https://truviq.com/jobs/2')
        with self.assertRaises(InterruptedError):
            self.store.save_job_batch('run1', 'employer', interrupted(), stop_event=stop)
        with self.store.connect() as db:
            for table in ('jobs','companies','job_observations','job_sources','source_attempts'):
                self.assertEqual(db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0], 0)

    def test_invalid_observation_is_quarantined_not_silently_lost(self):
        self.store.save_job_batch('run1','test',[{'title':'Missing URL'},self.job('https://example.com/jobs/good')])
        self.assertEqual(len(self.store.list_jobs()),1)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM rejected_observations').fetchone()[0],1)

    def test_recency_and_raw_evidence_preserved(self):
        row = self.job('https://truviq.com/jobs/1')
        self.store.save_job_batch('one', 'employer', [row], observed_at='2026-09-01T00:00:00+00:00')
        self.store.save_job_batch('two', 'employer', [row], observed_at='2026-09-02T00:00:00+00:00')
        job = self.store.list_jobs()[0]
        self.assertEqual(job['first_seen_at'], '2026-09-01T00:00:00+00:00')
        self.assertEqual(job['last_seen_at'], '2026-09-02T00:00:00+00:00')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM job_observations').fetchone()[0], 2)

    def test_repository_job_list_and_detail_share_identity(self):
        from app import create_app
        root=Path(self.temp.name)
        application=create_app(root/'api-data',root/'research')
        repository=application.extensions['store']
        repository.save_job_batch('run1','Indeed',[self.job('https://in.indeed.com/viewjob?jk=api')])
        client=application.test_client()
        response=client.get('/api/scan-results')
        self.assertEqual(response.status_code,200)
        rows=[job for company in response.get_json()['companies'] for job in company['jobs']]
        self.assertEqual(len(rows),1)
        detail=client.get('/api/opportunities/'+rows[0]['id'])
        self.assertEqual(detail.status_code,200)
        self.assertEqual(detail.get_json()['opportunity']['recommendation']['status'],'review')
        self.assertEqual(client.get('/api/health').get_json()['service'],'pega-job-hunter')

    def test_pega_brand_is_not_role_evidence(self):
        self.assertEqual(pega_evidence('Pegasystems is hiring an HR manager.'), 'unverified')
        self.assertEqual(pega_evidence('Required: hands-on Pega development using rulesets and case design.'), 'confirmed')
        row = normalize_job(self.job('https://truviq.com/jobs/1'))
        self.assertEqual(row['pega_verification'], 'unverified')


if __name__ == '__main__':
    unittest.main()
