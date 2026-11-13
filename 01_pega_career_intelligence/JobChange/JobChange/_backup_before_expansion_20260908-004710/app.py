"""Personal career research workspace. Local-only, source-linked and persistent."""
import sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'.deps'))
import argparse
import copy
import csv
import io
import json
import os
import secrets
import threading
from datetime import date
from flask import Flask, jsonify, request, render_template, send_from_directory, Response, abort
from quality import canonical_url, effective_status, evidence_freshness, is_bangalore, job_identity
from storage import Store, now
from verification import recheck

PROFILE={'name':'Sathvik','years_experience':4,'location':'Bengaluru','current_employer':'Mercedes-Benz R&D India',
         'joining_date':'2026-12-02','current_ctc':1157434.49,'tcs':{'fixed':1362636,'performance':252000,'city':21600,'retirals':63769,'total':1700005},
         'target_ctc_min':2400000,'target_ctc_max':2700000,'skills':['Pega CSSA','Kafka','REST / SOAP','SQL','Auto finance','Production automation']}
LIBRARY={'resume':('sathvik_resume_v2.html','Your resume'),
         'interview-masterclass':('Pega_Interview_Masterclass.html','Interview masterclass'),
         'ssa':('PegaSSA_FullPortal.html','SSA practice and interview feedback'),
         'csc':('CSC_PEGA_Software_Engineer_Interview_Master_Guide.html','CSC interview preparation'),
         'career-hub':('Pega_Career_Intelligence_Hub.html','Original career strategy · historical research'),
         'dossiers':('Pega_Deep_Dossiers.html','Original dossiers · unverified legacy claims')}
PIPELINE={'unreviewed','shortlisted','contacted','applied','interviewing','offer','dismissed'}

def create_app(data_dir=None,research_dir=None):
    app=Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=32*1024,TRUSTED_HOSTS=['127.0.0.1','localhost','[::1]'])
    store=Store(Path(data_dir or os.environ.get('PEGA_DATA_DIR',BASE/'data'))/'workspace.sqlite3')
    research=Path(research_dir or BASE/'research')
    csrf=secrets.token_urlsafe(32)
    lock=threading.RLock()
    state={'running':False,'kind':None,'progress':0,'total':0,'current_company':'','error':None,'log_lines':[],'last_scan':None}
    last=store.get('meta','last_scan')
    if last: state.update(last,running=False)
    app.extensions['store']=store
    app.extensions['scan_state']=state

    def read_research(name,key):
        path=research/name
        if not path.exists(): return []
        try:
            value=json.loads(path.read_text(encoding='utf-8-sig'))
            return value.get(key,[])
        except (ValueError,OSError):
            app.logger.exception('Cannot read research file %s',path)
            return []

    def opportunities():
        rows=read_research('openings.json','opportunities')
        saved=store.all('pipeline'); checks=store.all('verification')
        unique={}
        for original in rows:
            row=copy.deepcopy(original)
            url=canonical_url(row.get('url',''))
            if not url: continue
            key=url
            if key in unique: continue
            row['url']=url
            row['id']=str(row.get('id') or job_identity(row.get('title',''),row.get('company',''),url))
            check=checks.get(row['id'])
            row['research_status']=row.get('status','uncertain')
            row['status']=effective_status(row,check)
            row['verification']=check
            row['freshness']=evidence_freshness((check or {}).get('checked_at') or row.get('checked_at'))
            row['bangalore']=is_bangalore(row.get('location'))
            row['pipeline']=saved.get(row['id'],{'stage':'unreviewed','notes':''})
            unique[key]=row
        rank={'strong':0,'possible':1,'stretch':2}
        return sorted(unique.values(),key=lambda r:(r['status']=='closed',not r['bangalore'],rank.get(r.get('fit'),3),r.get('company','')))

    @app.before_request
    def protect_local_mutations():
        if request.method in ('POST','PUT','PATCH','DELETE'):
            if request.headers.get('X-Career-Token')!=csrf:
                return jsonify(error='Reload the portal before saving.'),403
            if not request.is_json: return jsonify(error='JSON request required.'),415
            if not isinstance(request.get_json(silent=True),dict):
                return jsonify(error='A JSON object is required.'),400
            origin=request.headers.get('Origin')
            if origin and origin.rstrip('/')!=request.host_url.rstrip('/'):
                return jsonify(error='Cross-origin changes are not allowed.'),403

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Cache-Control']='no-store'
        response.headers['X-Frame-Options']='SAMEORIGIN'
        return response

    @app.get('/')
    def index(): return render_template('index.html')

    @app.get('/api/bootstrap')
    def bootstrap():
        return jsonify(profile=PROFILE,token=csrf,library=[{'id':k,'title':v[1]} for k,v in LIBRARY.items()],today=date.today().isoformat())

    @app.get('/api/opportunities')
    def jobs(): return jsonify(opportunities=opportunities(),as_of=date.today().isoformat())

    @app.get('/api/teams')
    def teams(): return jsonify(teams=read_research('teams.json','teams'))

    @app.get('/api/salaries')
    def salaries():
        path=research/'salaries.json'
        return jsonify(json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {'salary_evidence':[],'assessment':{}})

    @app.get('/api/legacy')
    @app.get('/api/team-intelligence')
    def legacy():
        path=next((BASE/n for n in ('team_intelligence_enriched.json','team_intelligence.json') if (BASE/n).exists()),None)
        if not path:return jsonify(companies=[],label='Original data unavailable')
        raw=json.loads(path.read_text(encoding='utf-8-sig'))
        # Exclude synthetic health scores, inferred departures, salary bands and playbooks.
        rows=[{k:c.get(k) for k in ('name','sector','locations','projects','tech_stack','domains')} for c in raw.get('companies',[])]
        return jsonify(companies=rows,total_companies=len(rows),label='Historical import · claims not reverified',
                       warning='Office locations do not establish local Pega teams. Use the sourced team research for current evidence.')

    @app.post('/api/pipeline/<job_id>')
    def pipeline(job_id):
        if job_id not in {r['id'] for r in opportunities()}:return jsonify(error='Unknown opportunity.'),404
        data=request.get_json(); stage=data.get('stage','unreviewed'); notes=data.get('notes','')
        if not isinstance(stage,str) or stage not in PIPELINE or not isinstance(notes,str) or len(notes)>4000:return jsonify(error='Invalid stage or notes (maximum 4,000 characters).'),400
        payload={'stage':stage,'notes':notes,'updated_at':now()}
        store.put('pipeline',job_id,payload)
        return jsonify(payload)

    @app.get('/api/export')
    def export():
        output=io.StringIO();writer=csv.writer(output)
        writer.writerow(['Company','Role','Location','Evidence status','Experience minimum','Fit','Pipeline','Notes','Employer URL','Checked'])
        def safe(v):
            value=str(v if v is not None else '')
            return "'"+value if value.startswith(('=','+','-','@','\t','\r')) else value
        for row in opportunities():
            writer.writerow([safe(v) for v in (row['company'],row['title'],row['location'],row['status'],row.get('experience_min'),row.get('fit'),row['pipeline']['stage'],row['pipeline']['notes'],row['url'],(row.get('verification') or {}).get('checked_at') or row.get('checked_at'))])
        return Response('\ufeff'+output.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=pega-opportunities.csv'})

    def begin(kind,total):
        with lock:
            if state['running']:return False
            state.update(running=True,kind=kind,progress=0,total=total,current_company='',error=None,log_lines=[])
            return True

    def finish(error=None):
        with lock:
            state.update(running=False,current_company='',last_scan=now(),error=error)
            store.put('meta','last_scan',copy.deepcopy(state))

    def check_worker(rows):
        try:
            for i,row in enumerate(rows):
                with lock:state['current_company']=row['company']
                result=recheck(row); store.put('verification',row['id'],result)
                with lock:
                    state['progress']=i+1
                    state['log_lines'].append(row['company']+': '+result['status']+' — '+result.get('detail',''))
            finish()
        except Exception as exc:finish(str(exc))

    @app.post('/api/recheck')
    def recheck_jobs():
        ids=request.get_json().get('ids',[])
        if not isinstance(ids,list) or len(ids)>50:return jsonify(error='Choose at most 50 opportunities.'),400
        rows=[r for r in opportunities() if r['id'] in ids]
        if not rows:return jsonify(error='Select at least one known opportunity.'),400
        if not begin('recheck',len(rows)):return jsonify(error='A task is already running.'),409
        threading.Thread(target=check_worker,args=(rows,),daemon=True).start()
        return jsonify(status='started',total=len(rows))

    def catalog():
        import pega_job_hunter as hunter
        return hunter.COMPANIES+hunter.CONSULTING_COMPANIES+hunter.REMOTE_GLOBAL_COMPANIES

    @app.get('/api/companies')
    def companies():
        return jsonify(companies=[{'name':c['name'],'location':c.get('location','India')} for c in catalog()])

    def scan_worker(targets):
        import pega_job_hunter as hunter
        try:
            hunter._broad_linkedin_cache.clear();hunter._jd_check_cache.clear()
            history=hunter.JobHistory(hunter.HISTORY_FILE)
            for i,company in enumerate(targets):
                with lock:state['current_company']=company['name']
                found,links=hunter.scan_company(company)
                for job in found:
                    job.is_new=history.is_new(job.uid)
                    if job.is_new:history.mark_seen(job.uid)
                result={'name':company['name'],'jobs':[j.to_dict() for j in found],'links':links,'checked_at':now(),
                        'new_count':sum(j.is_new for j in found),'diagnostics':hunter.LAST_SCAN_DIAGNOSTICS.get(company['name'],[])}
                store.put('discovery',company['name'],result)
                # Persist after each company, so interruption does not discard completed work.
                history.save()
                with lock:
                    state['progress']=i+1
                    state['log_lines'].append(company['name']+': '+str(len(found))+' discovery candidates; employer verification still required.')
            finish()
        except Exception as exc:finish(str(exc))

    @app.post('/api/scan')
    def start_scan():
        names=request.get_json().get('companies',[])
        if not isinstance(names,list) or not 1<=len(names)<=5:return jsonify(error='Choose one to five companies per discovery scan.'),400
        targets=[c for c in catalog() if c['name'] in names]
        if not targets:return jsonify(error='No matching companies.'),400
        if not begin('discovery',len(targets)):return jsonify(error='A task is already running.'),409
        threading.Thread(target=scan_worker,args=(targets,),daemon=True).start()
        return jsonify(status='started',total=len(targets))

    @app.get('/api/status')
    def status():
        with lock:return jsonify(copy.deepcopy(state))

    @app.get('/api/results')
    @app.get('/api/discovery')
    def discovery():return jsonify(companies=list(store.all('discovery').values()))

    @app.get('/library/<key>')
    def library(key):
        if key not in LIBRARY:abort(404)
        return send_from_directory(BASE,LIBRARY[key][0])

    @app.get('/intel')
    @app.get('/dossiers')
    def intelligence():return render_template('index.html')

    @app.get('/interview-masterclass')
    def masterclass():return send_from_directory(BASE,LIBRARY['interview-masterclass'][0])

    return app

def main():
    parser=argparse.ArgumentParser(description='Sathvik career research workspace')
    parser.add_argument('--port',type=int,default=5050)
    args=parser.parse_args()
    create_app().run(host='127.0.0.1',port=args.port,debug=False,threaded=True)

if __name__=='__main__':main()
