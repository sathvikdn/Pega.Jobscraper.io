import tempfile
import threading
import unittest
from pathlib import Path
from storage import Store
from scan_coordinator import ScanCoordinator, DomainBudget


class CoordinatorTests(unittest.TestCase):
    def test_weighted_schedule_keeps_every_target_and_services_get_early_slots(self):
        from scan_coordinator import schedule_targets
        targets=[{'target_id':'g'+str(index),'category':'gcc'} for index in range(6)]+[{'target_id':'s'+str(index),'category':'services'} for index in range(3)]
        result=schedule_targets(targets,{'g5','s2'})
        self.assertEqual([row['target_id'] for row in result[:3]],['g5','g0','s2'])
        self.assertEqual({row['target_id'] for row in result},{row['target_id'] for row in targets})
        self.assertEqual(len(result),len(targets))

    def test_coverage_persists_unattempted_and_missing_sources(self):
        from scan_coordinator import CoverageLedger
        with tempfile.TemporaryDirectory() as folder:
            store=Store(Path(folder)/'coverage.sqlite3')
            ledger=CoverageLedger(store,'run')
            targets=[{'target_id':'one','name':'One'},{'target_id':'two','name':'Two'}]
            ledger.plan(targets,{'one':'https://example.com/careers'})
            ledger.record('one','LinkedIn','searched',3)
            ledger.record('two','LinkedIn',ledger.outcome('blocked',[{'http_status':403,'request_skipped':True}]))
            restarted=CoverageLedger(Store(store.path),'run')
            summary=restarted.summary()
            self.assertEqual(summary['planned_sources'],4)
            self.assertEqual(summary['outcomes'],{'searched':1,'pending':1,'deferred':1,'unconfigured':1})
            self.assertTrue(summary['incomplete'])
            self.assertEqual(restarted.pending_ids(),{'one','two'})
            restarted.plan(targets,{'one':'https://example.com/careers'})
            self.assertEqual(restarted.summary(),summary)

    def test_empty_extraction_is_not_verified_empty_result(self):
        from scan_coordinator import CoverageLedger
        self.assertEqual(CoverageLedger.outcome(None,{},0),'unverified')
        self.assertEqual(CoverageLedger.outcome('results',[],2,True),'partial')
        self.assertEqual(CoverageLedger.outcome(None,{'error':'Source returned HTTP 403'}),'deferred')

    def test_failed_source_keeps_previous_job_observations(self):
        from scan_coordinator import CoverageLedger
        with tempfile.TemporaryDirectory() as folder:
            store=Store(Path(folder)/'preserve.sqlite3')
            store.save_job_batch('old','Employer career page',[{'title':'Pega Developer','company':'Example','location':'Pune','url':'https://example.com/job/1'}])
            ledger=CoverageLedger(store,'new');ledger.plan([{'target_id':'one','name':'Example'}],{'one':'https://example.com/careers'})
            ledger.record('one','Employer career page','failed',diagnostic={'error':'timeout'})
            self.assertEqual(len(store.list_jobs()),1)
            with store.connect() as db:self.assertEqual(db.execute('SELECT run_id FROM job_observations').fetchone()[0],'old')

    def test_states_cancel_and_persist(self):
        with tempfile.TemporaryDirectory() as folder:
            coordinator=ScanCoordinator(Store(Path(folder)/'test.sqlite3'))
            coordinator.begin('test')
            self.assertEqual(coordinator.snapshot()['state'],'QUEUED')
            with self.assertRaises(RuntimeError):coordinator.begin('another')
            coordinator.transition('FETCHING','test-source')
            coordinator.persist('test-source',[{'title':'Pega Developer','company':'Barclays','url':'https://example.com/jobs/1','location':'Pune'}])
            self.assertEqual(len(coordinator.store.list_jobs()),1)
            coordinator.cancel()
            with self.assertRaises(InterruptedError):coordinator.persist('test-source',[])
            self.assertEqual(coordinator.snapshot()['state'],'FAILED')

    def test_domain_denial_is_not_retried(self):
        budget=DomainBudget(spacing=0)
        stop=threading.Event()
        budget.reject('https://example.com/jobs',403)
        with self.assertRaises(PermissionError):budget.wait('https://example.com/jobs/2',stop)
        budget.wait('https://other.example/jobs',stop)
        stop.set()
        with self.assertRaises(InterruptedError):budget.wait('https://other.example/jobs',stop)

    def test_retry_after_is_not_shortened(self):
        import time
        budget=DomainBudget()
        started=time.monotonic()
        budget.reject('https://example.com/jobs',429,retry_after=900)
        self.assertGreaterEqual(budget.next_at['example.com'],started+900)


if __name__=='__main__':unittest.main()
