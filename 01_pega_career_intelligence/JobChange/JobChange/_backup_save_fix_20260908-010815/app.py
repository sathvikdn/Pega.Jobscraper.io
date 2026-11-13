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
from opportunity_data import normalize_opportunity, salary_bucket, company_key, employer_type_index

PROFILE={'name':'Sathvik','years_experience':4,'location':'Bengaluru','current_employer':'Mercedes-Benz R&D India',
         'joining_date':'2026-12-02','current_ctc':1157434.49,'tcs':{'fixed':1362636,'performance':252000,'city':21600,'retirals':63769,'total':1700005},
         'target_ctc_min':2000000,'target_ctc_max':3500000,'goal_ctc':3500000,'search_floor_ctc':2000000,'skills':['Pega CSSA','Kafka','REST / SOAP','SQL','Auto finance','Production automation']}
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
    campaign_stop=threading.Event()
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

    def read_document(name,default=None):
        try:return json.loads((research/name).read_text(encoding='utf-8-sig'))
        except (OSError,ValueError):return default if default is not None else {}

    def campaign_document():
        return read_document('preloaded_search.json',{'coverage':{},'targets':[],'status':'not_started'})

    def opportunities():
        employer_types=employer_type_index(read_document('directory.json').get('records',[]))
        rows=[]
        for filename in ('openings.json','expanded_openings.json'):
            for original in read_research(filename,'opportunities'):
                row=normalize_opportunity(original)
                if row:rows.append(row)
        for target in campaign_document().get('targets',[]):
            for original in target.get('jobs',[]):
                row=normalize_opportunity(original,'campaign',target)
                if row:rows.append(row)
        saved=store.all('pipeline'); checks=store.all('verification')
        unique={}
        for original in rows:
            row=copy.deepcopy(original)
            if row.get('employer_type')=='unknown':row['employer_type']=employer_types.get(company_key(row['company']),'unknown')
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
        return jsonify(profile=PROFILE,token=csrf,library=[{'id':k,'title':v[1]} for k,v in LIBRARY.items()],today=date.today().isoformat(),search_preferences=store.get('meta','search_preferences',{'minimum_ctc_lpa':20,'role_scope':'broad','category':'all'}))

    @app.get('/api/opportunities')
    def jobs(): return jsonify(opportunities=opportunities(),as_of=date.today().isoformat())

    @app.get('/api/teams')
    def teams(): return jsonify(teams=read_research('teams.json','teams'))

    @app.get('/api/team-depth')
    def team_depth():
        rows=[]
        for filename in ('team_depth_gcc.json','team_depth_consulting.json','team_depth_remote.json'):
            rows.extend(read_research(filename,'team_depth'))
        events=read_document('community_events.json',{'events':[]})
        return jsonify(team_depth=rows,events=events.get('events',[]),as_of=date.today().isoformat())

    @app.get('/api/directory')
    def directory():
        doc=read_document('directory.json',{'records':[],'stats':{}})
        doc.pop('historical_snapshots',None)
        checks={r['target_id']:r for r in campaign_document().get('targets',[])}
        for row in doc.get('records',[]):
            if row.get('team_snapshot'):row['team_snapshot'].pop('_source_records',None)
            check=checks.get(row['target_id'])
            row['latest_search']={k:check.get(k) for k in ('status','checked_at','source_url','diagnostics')} if check else {'status':'pending'}
            row['opportunity_count']=len(check.get('jobs',[])) if check else 0
        doc.setdefault('stats',{})['pending_checks']=sum(r['latest_search'].get('status')=='pending' for r in doc.get('records',[]))
        return jsonify(doc)

    @app.get('/api/campaign')
    def campaign_status():
        doc=campaign_document()
        if doc.get('status')=='running' or doc.get('detail_enrichment',{}).get('status')=='running':
            import campaign
            active=getattr(campaign,'campaign_is_locked',lambda path:False)(research/'preloaded_search.json')
            if not active and not state['running']:
                doc['status']='interrupted'
                doc['resume_available']=True
                if doc.get('detail_enrichment',{}).get('status')=='running':
                    doc['detail_enrichment']['status']='interrupted'
        # The job list and rich company research have their own endpoints.
        doc['targets']=[{k:v for k,v in r.items() if k!='jobs'}|{'job_count':len(r.get('jobs',[]))} for r in doc.get('targets',[])]
        return jsonify(doc)

    def campaign_worker(target_ids,force):
        try:
            import campaign
            def progress(update):
                coverage=update.get('detail_enrichment') or update.get('coverage',update)
                with lock:
                    state.update(phase=update.get('phase','directory'),progress=coverage.get('checked',state['progress']),total=coverage.get('total',state['total']),current_company=update.get('current_company',update.get('current_target',update.get('name',''))))
            campaign.run_campaign(target_ids=target_ids,force=force,progress=progress,stop_event=campaign_stop,output_path=research/'preloaded_search.json',data=read_document('directory.json').get('records',[]))
            if not campaign_stop.is_set() and hasattr(campaign,'enrich_campaign'):
                campaign.enrich_campaign(output_path=research/'preloaded_search.json',progress=progress,stop_event=campaign_stop,force=force)
            finish()
        except Exception as exc:finish(str(exc))

    @app.post('/api/search')
    def search_all():
        data=request.get_json()
        category=data.get('category','all')
        minimum=data.get('minimum_ctc_lpa',20)
        scope=data.get('role_scope','broad')
        if category not in ('all','gcc','services','global') or scope not in ('broad','pega'):
            return jsonify(error='Choose a valid search scope.'),400
        if isinstance(minimum,bool) or not isinstance(minimum,(int,float)) or not 0<=minimum<=200:
            return jsonify(error='Enter a CTC target between 0 and 200 LPA.'),400
        records=read_document('directory.json').get('records',[])
        targets=[r for r in records if category=='all' or r['category']==category]
        if not targets:return jsonify(error='The preloaded company directory is unavailable.'),400
        import campaign
        if getattr(campaign,'campaign_is_locked',lambda path:False)(research/'preloaded_search.json'):
            return jsonify(error='The directory search is already running. Follow Search coverage for saved progress.'),409
        if not begin('full_search',len(targets)):return jsonify(error='A task is already running. Its results remain available.'),409
        store.put('meta','search_preferences',{'minimum_ctc_lpa':minimum,'role_scope':scope,'category':category})
        campaign_stop.clear()
        threading.Thread(target=campaign_worker,args=([r['target_id'] for r in targets],not bool(data.get('resume',False))),daemon=True).start()
        return jsonify(status='started',total=len(targets),minimum_ctc_lpa=minimum,role_scope=scope)

    @app.post('/api/search/pause')
    def pause_search():
        with lock:
            if not state['running'] or state['kind']!='full_search':return jsonify(error='No full search is running.'),409
        campaign_stop.set()
        return jsonify(status='pausing',detail='Finishing requests already in flight; completed results are saved.')

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
        writer.writerow(['Company','Role','Location','Evidence status','Experience minimum','Fit','Pipeline','Notes','Employer URL','Checked','Salary minimum','Salary maximum','Currency','Pay basis','Role family','Remote eligibility'])
        def safe(v):
            value=str(v if v is not None else '')
            return "'"+value if value.startswith(('=','+','-','@','\t','\r')) else value
        for row in opportunities():
            salary=row.get('salary') or {}
            writer.writerow([safe(v) for v in (row['company'],row['title'],row['location'],row['status'],row.get('experience_min'),row.get('fit'),row['pipeline']['stage'],row['pipeline']['notes'],row['url'],(row.get('verification') or {}).get('checked_at') or row.get('checked_at'),salary.get('amount_min'),salary.get('amount_max'),salary.get('currency'),salary.get('basis'),row.get('track'),row.get('remote_eligibility'))])
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
