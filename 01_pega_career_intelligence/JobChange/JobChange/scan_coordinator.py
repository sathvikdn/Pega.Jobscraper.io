from __future__ import annotations

import random
import threading
import time
from urllib.parse import urlsplit


def schedule_targets(targets, deferred_ids=()):
    from collections import deque
    pending=set(deferred_ids)
    ordered=sorted(targets,key=lambda target:target['target_id'] not in pending)
    product=deque(target for target in ordered if target.get('category')!='services')
    consulting=deque(target for target in ordered if target.get('category')=='services')
    scheduled=[]
    while product or consulting:
        for _ in range(2):
            if product:scheduled.append(product.popleft())
        if consulting:scheduled.append(consulting.popleft())
    return scheduled


class CoverageLedger:
    def __init__(self,store,run_id):
        self.store,self.run_id=store,run_id

    def plan(self,targets,career_urls,boards=()):
        from storage import now
        with self.store.connect() as db:
            for target in targets:
                career=target.get('career_url') or career_urls.get(target['target_id']) or career_urls.get(target['name'].lower())
                for source,url,status in [('LinkedIn',None,'pending'),('Employer career page',career,'pending' if career else 'unconfigured')]:
                    db.execute('INSERT OR IGNORE INTO target_coverage(run_id,target_id,source,company,url,status,updated_at) VALUES (?,?,?,?,?,?,?)',
                               (self.run_id,target['target_id'],source,target['name'],url,status,now()))
            for board in boards:
                db.execute('INSERT OR IGNORE INTO target_coverage(run_id,target_id,source,company,url,status,updated_at) VALUES (?,?,?,?,?,?,?)',
                           (self.run_id,'board:'+board['name'],board['name'],board['name'],board['url'],'pending',now()))

    def record(self,target_id,source,status,candidate_count=0,diagnostic=None):
        import json
        from storage import now
        if status not in ('pending','searched','partial','deferred','failed','unverified','unconfigured'):
            raise ValueError('Invalid coverage outcome')
        with self.store.connect() as db:
            db.execute('UPDATE target_coverage SET status=?,candidate_count=?,diagnostic=?,updated_at=? WHERE run_id=? AND target_id=? AND source=?',
                       (status,candidate_count,json.dumps(diagnostic or {}),now(),self.run_id,target_id,source))

    @staticmethod
    def outcome(status,diagnostics=(),candidate_count=0,partial=False):
        if isinstance(diagnostics,dict):diagnostics=[diagnostics]
        if any(item.get('request_skipped') or item.get('http_status') in (401,403,429,999) or 'access denied' in str(item.get('error','')).lower() or 'HTTP 403' in str(item.get('error','')) or 'HTTP 429' in str(item.get('error','')) for item in diagnostics):return 'deferred'
        if status=='pending':return 'pending'
        if status=='blocked':return 'deferred'
        if any(item.get('error') for item in diagnostics) or status=='error':return 'partial' if candidate_count else 'failed'
        if partial:return 'partial'
        if status in ('results','no_matches'):return 'searched'
        return 'searched' if candidate_count else 'unverified'

    def rows(self):
        with self.store.connect() as db:
            return [dict(zip(('target_id','source','company','url','status','candidate_count','diagnostic','updated_at'),row)) for row in db.execute(
                'SELECT target_id,source,company,url,status,candidate_count,diagnostic,updated_at FROM target_coverage WHERE run_id=?',(self.run_id,))]

    def summary(self):
        with self.store.connect() as db:
            counts=dict(db.execute('SELECT status,COUNT(*) FROM target_coverage WHERE run_id=? GROUP BY status',(self.run_id,)).fetchall())
            companies=db.execute("SELECT COUNT(DISTINCT target_id) FROM target_coverage WHERE run_id=? AND target_id NOT LIKE 'board:%'",(self.run_id,)).fetchone()[0]
        return {'planned_sources':sum(counts.values()),'outcomes':counts,'incomplete':any(status!='searched' for status in counts),
                'companies':companies}

    def pending_ids(self):
        return {row['target_id'] for row in self.rows() if row['status'] not in ('searched','unconfigured') and not row['target_id'].startswith('board:')}


class ScanCoordinator:
    STATES = {'IDLE','QUEUED','FETCHING','PARSING','PERSISTING','COMPLETED','PARTIAL','FAILED'}

    def __init__(self, store, stop_event=None):
        self.store = store
        self.stop_event = stop_event if stop_event is not None else threading.Event()
        self.lock = threading.RLock()
        self.run_id = None
        self.state = 'IDLE'
        self.current_source = None
        self.error = None

    def begin(self, run_id):
        with self.lock:
            if self.state not in ('IDLE','COMPLETED','PARTIAL','FAILED'):raise RuntimeError('Scan is already active')
            self.run_id = run_id
            self.stop_event.clear()
            self.transition('QUEUED')

    def transition(self, state, source=None, error=None):
        from storage import now
        if state not in self.STATES:raise ValueError('Unknown scan state')
        with self.lock:
            self.state,self.current_source,self.error = state,source,error
            if self.run_id:
                stamp = now()
                with self.store.connect() as db:
                    db.execute('INSERT INTO scan_runs VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state,updated_at=excluded.updated_at',
                               (self.run_id,state,stamp,stamp))

    def persist(self, source, observations, diagnostics=None):
        self.transition('PERSISTING', source)
        try:
            result = self.store.save_job_batch(self.run_id,source,observations,diagnostics,self.stop_event)
            self.transition('FETCHING', source)
            return result
        except Exception as error:
            import json
            from storage import now
            self.transition('FAILED',source,str(error))
            with self.store.connect() as db:
                db.execute('INSERT INTO source_attempts(run_id,source,state,observed_at,diagnostics) VALUES (?,?,?,?,?)',
                           (self.run_id,source,'FAILED',now(),json.dumps({'error':str(error)})))
            raise

    def cancel(self):
        self.stop_event.set()

    def snapshot(self):
        with self.lock:
            return {'run_id':self.run_id,'state':self.state,'source':self.current_source,
                    'cancel_requested':self.stop_event.is_set(),'error':self.error}


class PortalClient:
    def __init__(self, base_url):
        self.base_url = base_url
        health = self.get('/api/health').get_json()
        if health.get('service') != 'pega-job-hunter' or not health.get('instance_token'):
            raise RuntimeError('Unverified portal service')
        self.instance_token = health['instance_token']

    def get(self, path):
        return self._request(path)

    def post(self, path, json=None, headers=None):
        health = self.get('/api/health').get_json()
        if health.get('instance_token') != self.instance_token:raise RuntimeError('Portal restarted; aborting stale client')
        return self._request(path, json, headers)

    def _request(self, path, payload=None, headers=None):
        import json
        import urllib.request
        import urllib.error
        from types import SimpleNamespace
        request = urllib.request.Request(self.base_url+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers or {})
        try:
            with urllib.request.urlopen(request,timeout=30) as response:
                data,status = json.load(response),response.status
        except urllib.error.HTTPError as error:
            with error:data,status = json.load(error),error.code
        return SimpleNamespace(status_code=status,get_json=lambda:data)


class DomainBudget:
    def __init__(self, spacing=2.0):
        self.spacing = spacing
        self.lock = threading.Lock()
        self.next_at = {}
        self.denied = set()

    def wait(self, url, stop_event):
        host = urlsplit(url).hostname
        with self.lock:
            if host in self.denied:raise PermissionError('Source access denied for this run')
            scheduled = max(time.monotonic(),self.next_at.get(host,0))
            self.next_at[host] = scheduled+self.spacing
        if stop_event.wait(max(0,scheduled-time.monotonic())):raise InterruptedError('Scan cancelled')

    def reject(self, url, status, attempt=1, retry_after=0):
        host = urlsplit(url).hostname
        with self.lock:
            if status in (401,403):self.denied.add(host)
            if status == 429 or status >= 500:
                delay = max(float(retry_after),min(300,2**min(attempt,8))+random.uniform(0,1))
                self.next_at[host] = max(self.next_at.get(host,0),time.monotonic()+delay)
