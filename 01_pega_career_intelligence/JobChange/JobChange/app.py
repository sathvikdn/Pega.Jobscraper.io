"""Personal career research workspace. Local-only, source-linked and persistent."""
import sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'.deps'))
import argparse
import copy
import csv
import io
import ipaddress
import re
import json
import os
import secrets
import threading
from datetime import date, datetime, timezone
from urllib.parse import urlsplit
from flask import Flask, jsonify, request, render_template, send_from_directory, Response, abort
from quality import canonical_url, effective_status, evidence_freshness, is_bangalore, job_identity
from storage import Store, now
from campaign import load_campaign as read_campaign_checkpoint
from verification import recheck
from opportunity_data import normalize_opportunity, salary_bucket, company_key, employer_type_index
from job_matching import assess_job
from job_details import PublicDescriptionClient, description_snapshot, overlay_description

PROFILE={'name':'Sathvik','years_experience':4,'location':'Bengaluru','current_employer':'Mercedes-Benz R&D India',
         'joining_date':'2026-12-02','current_ctc':1157434.49,'tcs':{'fixed':1362636,'performance':252000,'city':21600,'retirals':63769,'total':1700005},
         'target_ctc_min':2000000,'target_ctc_max':3500000,'goal_ctc':3500000,'search_floor_ctc':2000000,'skills':['Pega CSSA','Kafka','REST / SOAP','SQL','Auto finance','Production automation']}
LIBRARY={'resume':('sathvik_resume_v2.html','Your resume'),
         'ssa':('PegaSSA_FullPortal.html','SSA practice and interview feedback'),
         'csc':('CSC_PEGA_Software_Engineer_Interview_Master_Guide.html','CSC interview preparation'),
         'career-hub':('Pega_Career_Intelligence_Hub.html','Career Intelligence Hub'),
         'dossiers':('Pega_Deep_Dossiers.html','Deep Dossiers')}
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
    from scan_coordinator import ScanCoordinator
    coordinator=ScanCoordinator(store,campaign_stop)
    instance_token=secrets.token_urlsafe(24)
    @app.get('/api/health')
    def health():
        return jsonify(service='pega-job-hunter',schema_version=1,instance_token=instance_token,pid=os.getpid())
    description_client=PublicDescriptionClient()
    description_busy=set()
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

    catalogue_cache={}
    catalogue_lock=threading.Lock()
    def master_document():
        import people_research
        stamp=[]
        for filename in ('master_catalog.json','independent_map.json',people_research.FILENAME):
            try:
                stat=(research/filename).stat();stamp.append((filename,stat.st_mtime_ns,stat.st_size))
            except OSError:stamp.append((filename,None,None))
        stamp=tuple(stamp)
        with catalogue_lock:
            if catalogue_cache.get('stamp')!=stamp:
                doc=read_document('master_catalog.json') or read_document('independent_map.json',{'companies':[],'people':[],'stats':{}})
                catalogue_cache.update(stamp=stamp,doc=people_research.attach(doc,research))
            return catalogue_cache['doc']

    @app.get('/api/intelligence/companies/<company_id>/people/<person_id>')
    def saved_intelligence_person(company_id,person_id):
        import people_views
        doc=master_document()
        company=next((c for c in doc.get('companies',[]) if c['id']==company_id),None)
        person=next((p for p in doc.get('people',[]) if p['id']==person_id),None)
        if not company or not person or not people_views.linked_people(company,[person]):
            return jsonify(error='This saved person was not found for this company.'),404
        return jsonify(person_id=person_id,company_id=company_id,html=people_views.render_profile(person,company))

    @app.get('/api/catalogue')
    def catalogue():
        doc=master_document()
        return jsonify(gcc_audit=doc.get('gcc_audit',{}),people_refresh=doc.get('people_refresh',{}),stats=doc.get('stats',{}),companies=[{k:v for k,v in c.items() if k not in ('legacy_snapshots','legacy_details','search_targets','source_rows')} for c in doc.get('companies',[])],people=doc.get('people',[]),source_ledger=doc.get('source_ledger',[]),definitions=doc.get('definitions',{}))

    def campaign_document():
        try:
            return read_campaign_checkpoint(research/'preloaded_search.json')
        except (OSError,ValueError):
            app.logger.exception('Cannot read the saved campaign')
            return {'coverage':{},'targets':[],'status':'unavailable'}

    def fresh_employer_jobs(companies):
        rows=[]
        for company in companies:
            for signal in company.get('hiring_signals',[]):
                if signal.get('kind')!='employer_job':continue
                title=signal.get('title')
                url=canonical_url(signal.get('url',''))
                if not isinstance(title,str) or not title.strip() or title.strip().lower() in ('jobs','careers','openings','current openings','all roles','open positions') or not url:
                    continue
                hostname=urlsplit(url).hostname or ''
                if hostname=='localhost' or hostname.endswith('.localhost'):continue
                try:
                    if not ipaddress.ip_address(hostname).is_global:continue
                except ValueError:pass
                description=signal.get('description') or 'Employer role lead; full requirements need confirmation.'
                limitations=company.get('limitations',[])
                if isinstance(limitations,str):limitations=[limitations]
                experience=signal.get('experience_min')
                if isinstance(experience,bool) or not isinstance(experience,(int,float)):experience=None
                if experience is None:
                    years=re.search(r'\b(?:minimum(?:\s+of)?|at\s+least|requires?|asks(?:\s+for)?)\s+(\d{1,2})\s*\+?\s+(?:Pega\s+)?years?\b',description,re.I)
                    if years:experience=int(years.group(1))
                clsa_required=bool(re.search(r'\b(?:mandatory|required|requires?|must\s+have)\b.{0,35}\bCLSA\b|\bCLSA\b.{0,25}\b(?:mandatory|required)\b',description,re.I))
                location=signal.get('location') or 'Location unconfirmed'
                status='closed' if signal.get('status') in ('closed','expired','historical') else 'open' if signal.get('vacancy_confirmed') is True and signal.get('access')=='page' else 'indexed_only' if signal.get('access')=='search_index' else 'uncertain'
                remote=signal.get('remote_eligibility') or ('india_remote' if re.search(r'\bindia\b',location,re.I) and re.search(r'\bremote\b',location,re.I) else 'unknown')
                rows.append({'company':company['name'],'title':title,'url':url,'location':location,
                             'status':status,'checked_at':signal.get('checked_at'),'posted_at':signal.get('source_date'),
                             'summary':description,'salary':None,'experience_min':experience,
                             'fit':'stretch' if (experience is not None and experience>4) or clsa_required else 'possible',
                             'fit_reasons':['Independently sourced employer role; review the description for fit.'],
                             'gaps':['Compensation and exact team assignment need confirmation.',*(['CLSA is explicitly required; the known profile lists CSSA.'] if clsa_required else []),*limitations],
                             'remote_eligibility':remote,'independent_discovery':True,'evidence_scope':'employer_job',
                             'employer_type':company.get('category') if company.get('category') in ('gcc','services') else 'unknown',
                             'evidence':[{'url':url,'title':title,'source_type':'Employer job page' if signal.get('access')=='page' else 'Indexed employer job',
                                          'checked_at':signal.get('checked_at'),'excerpt':description,'status':status,'access':signal.get('access')}]})
        return rows

    def evidence_time(value):
        try:
            parsed=datetime.fromisoformat(str(value).replace('Z','+00:00'))
            return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
        except (TypeError,ValueError):return datetime.min.replace(tzinfo=timezone.utc)

    def fresh_evidence_rank(row):
        if row.get('job_detail_status')=='read' or row.get('evidence_scope')=='role_description':return 3
        if row.get('evidence_scope')=='employer_job' and row.get('status')=='open':return 2
        return 1

    def opportunities():
        reset_at=store.get('meta','jobs_reset_at')
        identity_aliases=store.get('meta','job_identity_aliases',{})
        employer_types=employer_type_index(read_document('directory.json').get('records',[]))
        fresh_companies=read_document('independent_map.json').get('companies',[])
        fresh_types=employer_type_index([{**r,'keywords':r.get('aliases',[])} for r in fresh_companies])
        fresh_ids={r.get('id') for r in fresh_companies}
        rows=[]
        for filename in (() if reset_at else ('openings.json','expanded_openings.json','fresh_public_jobs.json','linkedin_refresh_observations_20260908.json','crosscheck_root_20260908.json','gcc_deep_findings_20260908.json')):
            for original in read_research(filename,'opportunities'):
                row=normalize_opportunity(original)
                if row:
                    if filename in ('fresh_public_jobs.json','linkedin_refresh_observations_20260908.json','crosscheck_root_20260908.json','gcc_deep_findings_20260908.json'):row['independent_discovery']=True
                    rows.append(row)
        for original in ([] if reset_at else fresh_employer_jobs(fresh_companies)):
            row=normalize_opportunity(original)
            if row:rows.append(row)
        for target in campaign_document().get('targets',[]):
            for original in target.get('jobs',[]):
                if reset_at and evidence_time(original.get('checked_at'))<evidence_time(reset_at):continue
                row=normalize_opportunity(original,'campaign',target)
                if row:
                    if target.get('target_id') in fresh_ids:row['independent_discovery']=True
                    rows.append(row)
        from normalizer import normalize_job
        repository_rows=store.list_jobs()
        repository_urls={source['url'] for job in repository_rows for source in job.get('sources',[])}
        legacy_ids={row['url']:row['id'] for row in rows}
        for row in repository_rows:
            legacy_id=next((legacy_ids[source['url']] for source in row.get('sources',[]) if source['url'] in legacy_ids),None)
            if legacy_id:row['id']=legacy_id
        rows=[row for row in rows if row['url'] not in repository_urls]
        legacy_browser=[row for row in store.get('meta','board_jobs',{}).get('jobs',[]) if canonical_url(row.get('url','')) not in repository_urls]
        for original in [*legacy_browser,*repository_rows]:
            try:
                row=normalize_opportunity(normalize_job(original))
                if row:rows.append(row)
            except (ValueError,TypeError):
                app.logger.warning('Invalid saved observation excluded from active results')
        saved=store.all('pipeline'); checks=store.all('verification')
        descriptions=store.all('job_descriptions')
        unique={}
        for original in rows:
            row=copy.deepcopy(original)
            if row.get('employer_type')=='unknown':row['employer_type']=(fresh_types if row.get('independent_discovery') else employer_types).get(company_key(row['company']),'unknown')
            url=canonical_url(row.get('url',''))
            if not url: continue
            key=url
            if key in unique:
                previous=unique[key]
                stamp=evidence_time(row.get('job_detail_checked_at') or row.get('checked_at'))
                prior_stamp=evidence_time(previous.get('job_detail_checked_at') or previous.get('checked_at'))
                newer_description=bool(row.get('description_complete') and row.get('description_text')) and stamp>=prior_stamp
                if not row.get('independent_discovery') and not newer_description and not row.get('sources'):continue
                if previous.get('independent_discovery') or newer_description:
                    if stamp<prior_stamp:continue
                    if not newer_description and row.get('status')!='closed' and fresh_evidence_rank(row)<fresh_evidence_rank(previous):continue
                # Replace researched facts, including missing salary, but retain the
                # stable identity used by the user's notes and pipeline history.
                row['id']=previous['id']
                row['independent_evidence']=True
                row['archived_evidence']=previous.get('archived_evidence',previous.get('evidence',[]))
            row=overlay_description(row,descriptions.get(url))
            row['url']=url
            row['id']=identity_aliases.get(url,str(row.get('id') or job_identity(row.get('title',''),row.get('company',''),url)))
            check=checks.get(row['id'])
            if check and row.get('independent_discovery') and evidence_time(check.get('checked_at'))<=evidence_time(row.get('job_detail_checked_at') or row.get('checked_at')):
                row['previous_verification']=check
                check=None
            row['research_status']=row.get('status','uncertain')
            row['status']=effective_status(row,check)
            row['verification']=check
            row['freshness']=evidence_freshness((check or {}).get('checked_at') or row.get('checked_at'))
            row['bangalore']=is_bangalore(row.get('location'))
            row['pipeline']=saved.get(row['id'],{'stage':'unreviewed','notes':''})
            row.update(assess_job(row,BASE/'sathvik_resume_v2.html',PROFILE['years_experience']))
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
    def index(): return render_template('scanner.html')

    @app.get('/api/bootstrap')
    def bootstrap():
        return jsonify(profile=PROFILE,token=csrf,library=[{'id':k,'title':v[1]} for k,v in LIBRARY.items()],today=date.today().isoformat(),search_preferences=store.get('meta','search_preferences',{'minimum_ctc_lpa':20,'role_scope':'broad','category':'all'}))

    recommendation_policy='Pega duties or requirements confirmed in a saved job description; stated experience below 8 years. Requirements above your 4 years are marked Stretch. Unknowns need verification.'
    def policy_counts(rows):
        return {key:sum(row.get('recommendation',{}).get('status')==key for row in rows) for key in ('recommended','stretch','review','excluded')}

    def in_scope(row,scope):
        assessment=row.get('recommendation',{})
        return scope=='all' or (assessment.get('eligible') if scope=='recommended' else assessment.get('status')==scope)

    @app.get('/api/opportunities')
    def jobs():
        scope=request.args.get('scope','recommended')
        if scope not in ('recommended','review','excluded','all'):return jsonify(error='Unknown recommendation scope.'),400
        rows=opportunities()
        return jsonify(opportunities=[row for row in rows if in_scope(row,scope)],policy_counts=policy_counts(rows),policy=recommendation_policy,as_of=date.today().isoformat())

    @app.get('/api/opportunities/<job_id>')
    def opportunity_detail(job_id):
        row=next((row for row in opportunities() if row['id']==job_id),None)
        if row is None:return jsonify(error='Unknown opportunity.'),404
        return jsonify(opportunity=row)

    @app.post('/api/opportunities/<job_id>/description')
    def refresh_opportunity_description(job_id):
        import campaign
        row=next((row for row in opportunities() if row['id']==job_id),None)
        if row is None:return jsonify(error='Unknown opportunity.'),404
        with lock:
            if row['url'] in description_busy:return jsonify(error='This description is already being checked.'),409
            description_busy.add(row['url'])
        try:
            updated=campaign.enrich_job(row,description_client)
            store.put('job_descriptions',row['url'],description_snapshot(updated))
            updated.update(assess_job(updated,BASE/'sathvik_resume_v2.html',PROFILE['years_experience']))
            return jsonify(opportunity=updated)
        finally:
            with lock:description_busy.discard(row['url'])

    @app.get('/api/ingestion-health')
    def ingestion_health():
        with store.connect() as db:
            counts={table:db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('jobs','job_observations','job_sources','rejected_observations')}
            attempts=[dict(zip(('run_id','source','state','observed_at','diagnostics'),row)) for row in db.execute('SELECT run_id,source,state,observed_at,diagnostics FROM source_attempts ORDER BY id DESC LIMIT 100')]
        return jsonify(counts=counts,attempts=attempts,coordinator=coordinator.snapshot())

    @app.get('/api/company-dossier')
    def company_dossier():
        name=request.args.get('name','')
        doc=master_document()
        company=next((row for row in doc.get('companies',[]) if company_key(name) in {company_key(value) for value in [row.get('name'),*row.get('aliases',[])]}),{})
        sources=[];offices=[];frameworks=[]
        for claim in company.get('claims',[]):
            url=canonical_url(claim.get('url') or claim.get('source_url',''))
            if not url:continue
            item={'title':claim.get('type','Source').replace('_',' '),'text':claim.get('text',''),'url':url,'checked_at':claim.get('checked_at')}
            sources.append(item)
            verified=claim.get('access')=='page' and claim.get('confidence') in ('confirmed','high')
            if verified and claim.get('type') in ('office','office_location','location') and re.search(r'India|Bengaluru|Bangalore',item['text'],re.I):offices.append(item)
            if verified and re.search(r'Constellation|Smart Dispute|CLM|KYC|Customer Service',item['text'],re.I):frameworks.append(item)
        openings=[{'title':row['title'],'text':row['location'],'url':row['url'],'checked_at':row.get('checked_at')} for row in opportunities() if company_key(row['company'])==company_key(name) and row.get('status')!='closed']
        people=[{'title':person.get('name','Name unconfirmed'),'text':person.get('title','Role unconfirmed'),'location':person.get('location_as_stated','Location unconfirmed'),'url':canonical_url(person.get('profile_url') or person.get('source_url','')),'checked_at':person.get('checked_at')} for person in doc.get('people',[]) if company.get('id') and company['id'] in [person.get('company_id'),*person.get('company_ids',[])]]
        return jsonify(company=name,offices=offices,frameworks=frameworks,sources=sources,openings=openings,people=people)

    @app.get('/api/teams')
    def teams(): return jsonify(teams=read_research('teams.json','teams'))

    @app.get('/api/team-depth')
    def team_depth():
        rows=[]
        for filename in ('team_depth_gcc.json','team_depth_consulting.json','team_depth_remote.json'):
            rows.extend(read_research(filename,'team_depth'))
        events=read_document('community_events.json',{'events':[]})
        return jsonify(team_depth=rows,events=events.get('events',[]),as_of=date.today().isoformat())

    @app.get('/api/investigation')
    def investigation():
        doc=read_document('independent_map.json',{'companies':[],'stats':{},'status':'unavailable'})
        checks={r['target_id']:r for r in campaign_document().get('targets',[])}
        for row in doc.get('companies',[]):
            check=checks.get(row.get('id'),{})
            row['latest_search']={k:check.get(k) for k in ('status','checked_at','source_url','diagnostics')} if check else {'status':'pending'}
            row['opportunity_count']=len(check.get('jobs',[]))
        return jsonify(doc)

    def fresh_targets():
        targets=[]
        for company in read_document('independent_map.json').get('companies',[]):
            if not isinstance(company,dict) or not isinstance(company.get('id'),str) or not isinstance(company.get('name'),str):
                continue
            if not company['id'].strip() or not company['name'].strip():continue
            aliases=[value for value in company.get('aliases',[]) if isinstance(value,str) and value.strip()]
            bangalore=bool((company.get('flags') or {}).get('bangalore'))
            targets.append({'target_id':company['id'],'name':company['name'],
                            'category':company.get('category','unclassified'),
                            'keywords':list(dict.fromkeys([company['name'],*aliases])),
                            'location':'Bengaluru, Karnataka, India' if bangalore else 'Worldwide',
                            'location_basis':'Sourced Bengaluru evidence' if bangalore else 'Worldwide query scope; employee location and remote eligibility are not assumed',
                            'catalog_scope':'fresh'})
        return targets

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
        doc['fresh_targets']=fresh_targets()
        for row in doc['fresh_targets']:
            check=checks.get(row['target_id'],{})
            row['latest_search']={k:check.get(k) for k in ('status','checked_at','source_url','diagnostics')} if check else {'status':'pending'}
            row['opportunity_count']=len(check.get('jobs',[]))
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
        doc['search_preferences']=store.get('meta','search_preferences',{})
        doc['catalog_scope']=doc['search_preferences'].get('catalog_scope','legacy')
        # The job list and rich company research have their own endpoints.
        doc['targets']=[{k:v for k,v in r.items() if k!='jobs'}|{'job_count':len(r.get('jobs',[]))} for r in doc.get('targets',[])]
        return jsonify(doc)

    def campaign_worker(target_ids,force,target_records=None):
        try:
            import campaign
            # run_campaign serializes only its supplied catalog. Include prior targets
            # to preserve results when switching between independent and legacy searches.
            records=target_records if target_records is not None else read_document('directory.json').get('records',[])
            catalog={r['target_id']:r for r in campaign_document().get('targets',[]) if isinstance(r,dict) and r.get('target_id') and r.get('name')}
            catalog.update({r['target_id']:r for r in records})
            def progress(update):
                coverage=update.get('detail_enrichment') or update.get('coverage',update)
                with lock:
                    state.update(phase=update.get('phase','directory'),progress=coverage.get('checked',state['progress']),total=coverage.get('total',state['total']),current_company=update.get('current_company',update.get('current_target',update.get('name',''))))
            campaign.run_campaign(target_ids=target_ids,force=force,progress=progress,stop_event=campaign_stop,output_path=research/'preloaded_search.json',data=list(catalog.values()))
            if not campaign_stop.is_set() and hasattr(campaign,'enrich_campaign'):
                enrichment={'output_path':research/'preloaded_search.json','progress':progress,'stop_event':campaign_stop,'force':force}
                if target_records is not None:enrichment['target_ids']=target_ids
                campaign.enrich_campaign(**enrichment)
            finish()
        except Exception as exc:finish(str(exc))

    @app.post('/api/search')
    def search_all():
        data=request.get_json()
        saved=store.get('meta','search_preferences',{}) if data.get('resume') else {}
        catalog_scope=data.get('catalog_scope',saved.get('catalog_scope','legacy'))
        same_catalog=catalog_scope==saved.get('catalog_scope','legacy')
        inherited=saved if same_catalog else {}
        category=data.get('category',inherited.get('category','all'))
        minimum=data.get('minimum_ctc_lpa',inherited.get('minimum_ctc_lpa',20))
        scope=data.get('role_scope',inherited.get('role_scope','broad'))
        company_id=data.get('company_id',inherited.get('company_id'))
        categories=('all','gcc','services','global','unclassified') if catalog_scope=='fresh' else ('all','gcc','services','global')
        if catalog_scope not in ('legacy','fresh') or category not in categories or scope not in ('broad','pega'):
            return jsonify(error='Choose a valid search scope.'),400
        if company_id is not None and (catalog_scope!='fresh' or not isinstance(company_id,str) or not company_id):
            return jsonify(error='Choose a company from the independent investigation.'),400
        if isinstance(minimum,bool) or not isinstance(minimum,(int,float)) or not 0<=minimum<=200:
            return jsonify(error='Enter a CTC target between 0 and 200 LPA.'),400
        records=fresh_targets() if catalog_scope=='fresh' else read_document('directory.json').get('records',[])
        if company_id is not None and company_id not in {r['target_id'] for r in records}:
            return jsonify(error='Unknown independently researched company.'),400
        targets=[r for r in records if (category=='all' or r['category']==category) and (company_id is None or r['target_id']==company_id)]
        if not targets:return jsonify(error='No researched companies match this search scope.' if catalog_scope=='fresh' else 'The preloaded company directory is unavailable.'),400
        import campaign
        if getattr(campaign,'campaign_is_locked',lambda path:False)(research/'preloaded_search.json'):
            return jsonify(error='The directory search is already running. Follow Search coverage for saved progress.'),409
        if not begin('full_search',len(targets)):return jsonify(error='A task is already running. Its results remain available.'),409
        preferences={'minimum_ctc_lpa':minimum,'role_scope':scope,'category':category}
        if catalog_scope=='fresh':preferences.update(catalog_scope='fresh',company_id=company_id)
        store.put('meta','search_preferences',preferences)
        campaign_stop.clear()
        arguments=([r['target_id'] for r in targets],not bool(data.get('resume',False)))
        if catalog_scope=='fresh':arguments=(*arguments,records)
        threading.Thread(target=campaign_worker,args=arguments,daemon=True).start()
        return jsonify(status='started',total=len(targets),minimum_ctc_lpa=minimum,role_scope=scope,catalog_scope=catalog_scope,company_id=company_id)

    @app.post('/api/search/pause')
    def pause_search():
        with lock:
            if not state['running'] or state['kind']!='full_search':return jsonify(error='No full search is running.'),409
            expected=request.get_json().get('expected_run_id')
            if expected is not None and expected!=state.get('run_id'):
                return jsonify(error='This is no longer the job you started.'),409
            campaign_stop.set()
        return jsonify(status='pausing',detail='Finishing requests already in flight; completed results are saved.')

    @app.get('/api/board-jobs')
    def board_jobs():
        data=store.get('meta','board_jobs',{})
        return jsonify(jobs=data.get('jobs',[]),diagnostics=data.get('diagnostics',[]),checked_at=data.get('checked_at'))

    @app.get('/api/scrape-log')
    def scrape_log():
        log_path=BASE/'data'/'career_scrape_log.json'
        if log_path.exists():
            try:return jsonify(json.loads(log_path.read_text(encoding='utf-8')))
            except (ValueError,OSError):pass
        return jsonify(log=[],summary={'total':0})

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
        row=next((r for r in opportunities() if r['id']==job_id),None)
        if row is None:return jsonify(error='Unknown opportunity.'),404
        data=request.get_json(); stage=data.get('stage','unreviewed'); notes=data.get('notes','')
        if not isinstance(stage,str) or stage not in PIPELINE or not isinstance(notes,str) or len(notes)>4000:return jsonify(error='Invalid stage or notes (maximum 4,000 characters).'),400
        payload={'stage':stage,'notes':notes,'updated_at':now()}
        store.put('pipeline',job_id,payload)
        aliases=store.get('meta','job_identity_aliases',{})
        if row.get('url'):
            aliases[canonical_url(row['url'])]=job_id
            store.put('meta','job_identity_aliases',aliases)
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
            state.update(run_id=None,running=True,kind=kind,phase=None,parallel={},description_progress=0,description_total=0,progress=0,total=total,current_company='',error=None,log_lines=[])
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

    def original_scan_catalog():
        import portal_scan
        import master_catalog
        existing=portal_scan.build_catalog(read_document('directory.json').get('records',[]),fresh_targets())
        records=portal_scan.india_targets(portal_scan.build_catalog(existing,master_catalog.extra_targets(master_document(),existing)))
        return master_catalog.apply_career_urls(records)

    @app.get('/api/scan-options')
    def original_scan_options():
        import portal_scan
        records=original_scan_catalog()
        return jsonify(categories=portal_scan.scan_options(records),total_targets=len(records))

    @app.get('/api/scan-results')
    def original_scan_results():
        import portal_scan
        selected=store.get('meta','scanner_selection',{})
        targets=selected.get('targets') or original_scan_catalog()
        scope=request.args.get('scope','all')
        if scope not in ('recommended','review','excluded','all'):return jsonify(error='Unknown recommendation scope.'),400
        # The assembled records already contain the newest description and saved notes.
        assessed=[job for job in opportunities() if portal_scan.india_job(job)]
        targets=list(targets)
        known_names={company_key(name) for target in targets for name in [target['name'],*target.get('keywords',[])]}
        for job in assessed:
            if job.get('target_id') or company_key(job['company']) in known_names:continue
            targets.append({'target_id':'observed-'+company_key(job['company']),'name':job['company'],'category':job.get('employer_type','unknown'),'location':'India'})
            known_names.add(company_key(job['company']))
        companies=portal_scan.grouped_results(assessed,targets,campaign_document(),selected.get('baseline_ids'),merge_checkpoint=False)
        # Merge Playwright-sourced jobs (LinkedIn retry + career portals + job boards)
        # Preserve source provenance and distinct requisitions from the repository.
        # Cross-board identity decisions live in the repository, not the view.
        # Repeated company groups must not duplicate an identical source URL.
        global_urls=set()
        import career_scraper as _cs
        for co in companies:
            deduped=[]
            for j in co['jobs']:
                url_key=canonical_url(j.get('url',''))
                if url_key and url_key in global_urls:
                    continue
                if not j.get('title'):
                    continue
                # Reject search/listing pages that slipped through earlier scans
                if _cs._is_search_or_listing_page(j.get('url',''), j.get('title','')):
                    continue
                if url_key:global_urls.add(url_key)
                deduped.append(j)
            co['jobs']=deduped
            co['new_count']=sum(j.get('is_new',False) for j in deduped)
        companies=[co for co in companies if co['jobs'] or co.get('checks')]
        unique={job['id']:job for company in companies for job in company['jobs']}
        counts=policy_counts(unique.values())
        if scope!='all':
            for company in companies:
                company['jobs']=[job for job in company['jobs'] if in_scope(job,scope)]
                company['new_count']=sum(job['is_new'] for job in company['jobs'])
        return jsonify(companies=companies,policy_counts=counts,policy=recommendation_policy,scope=scope,run_id=selected.get('run_id'),mode=selected.get('mode'),total_targets=len(targets),last_scan=state.get('last_scan'))

    def original_scan_worker(targets,records,force=True):
        import portal_scan
        from scan_coordinator import CoverageLedger
        ledger=CoverageLedger(store,state.get('run_id') or secrets.token_hex(16))
        completed=set()
        def progress(update):
            outcome=update.get('target_status','checked')
            if update.get('event_kind')=='target' and update.get('target_id'):
                outcome=ledger.outcome(update.get('target_status'),update.get('target_diagnostics',[]),update.get('target_job_count',0),update.get('target_partial',False))
                ledger.record(update['target_id'],'LinkedIn',outcome,update.get('target_job_count',0),{'diagnostics':update.get('target_diagnostics',[])})
            with lock:
                detail=update.get('detail_enrichment')
                selected=update.get('selected_coverage')
                if selected is not None:
                    state.update(phase='parallel_scan',progress=selected.get('checked',0),total=selected.get('total',len(targets)),
                                 description_progress=(detail or {}).get('checked',0),description_total=(detail or {}).get('total',0),
                                 parallel=update.get('parallel',{}))
                elif detail:
                    state.update(phase='job_details',progress=detail.get('checked',0),total=detail.get('total',0))
                else:
                    if update.get('target_status')!='pending' and update.get('target_id') in {t['target_id'] for t in targets}:completed.add(update['target_id'])
                    state.update(phase='directory',progress=len(completed),total=len(targets))
                company=update.get('current_company') or update.get('current_target') or ''
                state['current_company']=company
                if company:
                    state['log_lines'].append(company+': '+('description checked' if update.get('event_kind')=='detail' else outcome if update.get('event_kind')=='target' else update.get('target_status','checked')))
                    state['log_lines']=state['log_lines'][-150:]
        try:
            import career_scraper
            career_scraper.clear_scrape_log()
            career_scraper.configure_run(campaign_stop)
            coordinator.begin(ledger.run_id)
            planned_urls={}
            for record in read_document('directory.json').get('records',[]):
                if record.get('career_url'):
                    planned_urls[record.get('target_id')]=record['career_url']
                    planned_urls[record.get('name','').lower()]=record['career_url']
            ledger.plan(targets,planned_urls,[board for board in career_scraper.JOB_BOARDS if board['name'] not in ('Indeed US','Dice')])
            coordinator.transition('FETCHING','LinkedIn')
            portal_scan.run_scan(targets,records,research/'preloaded_search.json',progress,campaign_stop,force=force)
            for target in campaign_document().get('targets',[]):
                if target.get('target_id') not in {item['target_id'] for item in targets}:continue
                if campaign_stop.is_set():break
                fresh_jobs=[job for job in target.get('jobs',[]) if job.get('search_presence')!='not_rediscovered']
                coordinator.persist('LinkedIn',fresh_jobs,{'target_id':target.get('target_id')})
                ledger.record(target['target_id'],'LinkedIn',ledger.outcome(target.get('status'),target.get('diagnostics',[]),len(fresh_jobs),target.get('partial',False)),len(fresh_jobs),{'diagnostics':target.get('diagnostics',[])})
            # Playwright career portal + job board scraping runs on this thread.
            # FRESH start: clear old board_jobs so we don't accumulate duplicates across runs.
            if not campaign_stop.is_set():
                all_extra_jobs=[]
                all_extra_diags=[]
                # Step 0: Retry blocked LinkedIn targets with Playwright
                try:
                    import campaign as _campaign
                    checkpoint=_campaign.load_campaign(research/'preloaded_search.json')
                    selected_ids={target['target_id'] for target in targets}
                    checkpoint['targets']=[target for target in checkpoint.get('targets',[]) if target.get('target_id') in selected_ids]
                    blocked_targets=[target for target in checkpoint.get('targets',[]) if target.get('status')=='error' and not any(audit.get('http_status') in (401,403,429,999) for audit in target.get('diagnostics',[]))]
                    if blocked_targets:
                        total_retry=len(blocked_targets)
                        with lock:state.update(phase='linkedin_retry',progress=0,total=total_retry);state['log_lines'].append(f'Retrying {total_retry} eligible transient failures with Playwright...');state['current_company']='LinkedIn retry'
                        for i,target in enumerate(blocked_targets):
                            if campaign_stop.is_set():break
                            name=target.get('name','?')
                            with lock:state.update(progress=i+1,current_company=name);state['log_lines'].append(f'LinkedIn retry {i+1}/{total_retry}: {name}');state['log_lines']=state['log_lines'][-150:]
                            try:
                                jobs,diag=career_scraper.scrape_linkedin_target(name,target.get('keywords',[name]),target.get('location','India'))
                                coordinator.persist('LinkedIn',jobs,diag)
                                ledger.record(target['target_id'],'LinkedIn',ledger.outcome(None,diag,len(jobs)),len(jobs),diag)
                                all_extra_jobs.extend(jobs)
                                all_extra_diags.append(diag)
                            except InterruptedError:break
                            except Exception as exc:
                                with lock:state['log_lines'].append(name+': source attempt failed: '+str(exc)[:180])
                            import time as _time;_time.sleep(1.0)
                        with lock:state['log_lines'].append(f'LinkedIn retry: {len(all_extra_jobs)} jobs recovered from {total_retry} targets.')
                except Exception as exc:
                    with lock:state['log_lines'].append('LinkedIn retry: '+str(exc)[:80])
                # Step 1: Scrape employer career portals and SAVE results
                try:
                    dir_doc=read_document('directory.json')
                    career_url_map={}
                    for r in dir_doc.get('records',[]):
                        if r.get('career_url') and r.get('target_id'):
                            career_url_map[r['target_id']]=r['career_url']
                        if r.get('career_url') and r.get('name'):
                            career_url_map[r['name'].lower()]=r['career_url']
                    import campaign as _campaign
                    checkpoint=_campaign.load_campaign(research/'preloaded_search.json')
                    career_targets=[]
                    for t in targets:
                        url=t.get('career_url') or career_url_map.get(t.get('target_id')) or career_url_map.get((t.get('name') or '').lower())
                        if url:career_targets.append((t['target_id'],t['name'],url))
                    if career_targets:
                        with lock:state.update(phase='career_portals',progress=0,total=len(career_targets));state['log_lines'].append(f'Scraping {len(career_targets)} employer career portals...');state['current_company']='Career portals'
                        portal_cache={}
                        for i,(target_id,name,career_url) in enumerate(career_targets):
                            if campaign_stop.is_set():break
                            with lock:state.update(progress=i+1,current_company=name);state['log_lines'].append(f'Career portal {i+1}/{len(career_targets)}: {name}');state['log_lines']=state['log_lines'][-150:]
                            try:
                                cache_key=(canonical_url(career_url),company_key(name))
                                reused=cache_key in portal_cache
                                if reused:pjobs,pdiag=portal_cache[cache_key]
                                else:
                                    pjobs,pdiag=career_scraper.scrape_career_page(career_url,name)
                                    portal_cache[cache_key]=(pjobs,pdiag)
                                    coordinator.transition('PARSING',name)
                                    coordinator.persist('Employer career page',pjobs,pdiag)
                                    all_extra_jobs.extend(pjobs)
                                    all_extra_diags.append(pdiag)
                                ledger.record(target_id,'Employer career page',ledger.outcome(None,pdiag,len(pjobs)),len(pjobs),{**pdiag,'reused_attempt':reused})
                            except InterruptedError:break
                            except Exception as exc:
                                ledger.record(target_id,'Employer career page','failed',diagnostic={'error':str(exc)[:180]})
                                with lock:state['log_lines'].append(name+': source attempt failed: '+str(exc)[:180])
                        with lock:state['log_lines'].append(f'Career portals: {sum(1 for d in all_extra_diags if d.get("source")=="career_portal_playwright" and d.get("jobs_found",0)>0)} portals found Pega jobs.')
                except Exception as exc:
                    with lock:state['log_lines'].append('Career portal scan: '+str(exc)[:80])
                # Step 2: Scrape job boards
                try:
                    board_count=sum(board['name'] not in ('Indeed US','Dice') for board in career_scraper.JOB_BOARDS)
                    with lock:state.update(phase='job_boards',progress=0,total=board_count);state['log_lines'].append('Scanning India boards (Indeed India, Shine, Glassdoor, SimplyHired)...');state['current_company']='Job boards'
                    def board_started(source):
                        coordinator.transition('FETCHING',source)
                        with lock:state['current_company']=source
                    def board_finished(source,jobs,diagnostic):
                        coordinator.persist(source,jobs,diagnostic)
                        ledger.record('board:'+source,source,ledger.outcome(None,diagnostic,len(jobs)),len(jobs),diagnostic)
                        with lock:state['progress']+=1
                    board_jobs,board_diags=career_scraper.scrape_all_job_boards(campaign_stop,board_finished,board_started)
                    all_extra_jobs.extend(board_jobs)
                    all_extra_diags.extend(board_diags)
                    with lock:state.update(progress=len(board_diags));state['log_lines'].append(f'Job boards: {len(board_jobs)} candidate listings extracted from {len(board_diags)} attempted boards.')
                except Exception as exc:
                    with lock:state['log_lines'].append('Job board scan: '+str(exc)[:80])
                # Keep run diagnostics separate from incrementally saved observations.
                store.put('meta','last_browser_run',{'run_id':ledger.run_id,'candidate_count':len(all_extra_jobs),'diagnostics':all_extra_diags,'checked_at':now()})
            # Save the scrape log and add Playwright stats to platform panel
            try:
                log_path=career_scraper.save_scrape_log()
                summary=career_scraper.analyze_scrape_log()
                scrape_log=career_scraper.get_scrape_log()
                pw_platforms={}
                for entry in scrape_log:
                    src=entry.get('type','?')
                    label={'linkedin_retry':'LinkedIn (retry)','career_portal':'Career Portals','job_board':entry.get('source',entry.get('company','Board'))}.get(src,src)
                    p=pw_platforms.setdefault(label,{'ok':0,'blocked':0,'error':0,'unverified':0,'pages':0})
                    p['pages']+=1
                    if entry.get('jobs_found',0)>0:p['ok']+=1
                    elif entry.get('failure_reason') in ('navigation_failed','exception'):p['error']+=1
                    else:p['unverified']+=1
                with lock:
                    existing=state.get('parallel',{}).get('requests',{}).get('platforms',{})
                    existing.update(pw_platforms)
                    state.setdefault('parallel',{}).setdefault('requests',{})['platforms']=existing
                    state['log_lines'].append(f'Scrape log: {summary.get("success",0)}/{summary.get("total",0)} portals found jobs. Log saved to {log_path.name}')
            except Exception:pass
            coverage=ledger.summary()
            with lock:
                state['coverage']=coverage
                state['log_lines'].append('Scan paused; completed results saved.' if campaign_stop.is_set() else 'Search finished with coverage gaps; unverified targets retained.' if coverage['incomplete'] else 'Search attempts complete. Results saved.')
            session=store.get('meta','scanner_selection',{})
            session.update(status='paused' if campaign_stop.is_set() else 'partial' if coverage['incomplete'] else 'complete',completed_at=now())
            store.put('meta','scanner_selection',session)
            finish()
        except Exception as exc:
            session=store.get('meta','scanner_selection',{})
            session.update(status='failed',error=str(exc),completed_at=now())
            store.put('meta','scanner_selection',session)
            with lock:state['log_lines'].append('Scan failed: '+str(exc))
            finish(str(exc))
        finally:
            career_scraper.shutdown()
            coordinator.transition('FAILED' if campaign_stop.is_set() or state.get('error') else 'PARTIAL' if ledger.summary()['incomplete'] else 'COMPLETED',error=state.get('error') or ('Cancelled' if campaign_stop.is_set() else None))

    def start_original_scan(data):
        import portal_scan,campaign
        previous=store.get('meta','scanner_selection',{}) if data.get('resume') else {}
        mode=previous.get('mode') if data.get('resume') else data.get('mode')
        if data.get('resume') and not previous.get('targets'):return jsonify(error='No saved scan selection to resume.'),400
        records=original_scan_catalog()
        try:targets=portal_scan.select_targets(records,mode) if not previous.get('targets') else portal_scan.india_targets(previous['targets'])
        except (ValueError,TypeError):return jsonify(error='Choose a valid category and depth.'),400
        if not targets:return jsonify(error='No search targets exist for this preset.'),400
        from scan_coordinator import CoverageLedger,schedule_targets
        prior=store.get('meta','scanner_selection',{})
        deferred_ids=CoverageLedger(store,prior.get('run_id','')).pending_ids()
        targets=schedule_targets(targets,deferred_ids)
        if campaign.campaign_is_locked(research/'preloaded_search.json'):return jsonify(error='A search is already running.'),409
        if not begin('full_search',len(targets)):return jsonify(error='A task is already running.'),409
        campaign_stop.clear()
        run_id=secrets.token_hex(16)
        try:
            store.put('meta','scanner_selection',{'run_id':run_id,'mode':mode,'targets':targets,'baseline_ids':previous.get('baseline_ids',[j['id'] for j in opportunities()]),'started_at':previous.get('started_at',now()),'status':'running'})
            with lock:state.update(run_id=run_id,scan_mode=mode,phase='parallel_scan',parallel={},description_progress=0,description_total=0,log_lines=[('Resuming' if data.get('resume') else 'Starting')+' parallel Python scan: '+mode+' — '+str(len(targets))+' targets.'])
            threading.Thread(target=original_scan_worker,args=(targets,records,not bool(data.get('resume'))),daemon=True).start()
        except Exception as exc:
            finish(str(exc))
            return jsonify(error='Could not start the Python scanner: '+str(exc)),500
        return jsonify(status='started',run_id=run_id,mode=mode,total=len(targets))

    @app.post('/api/scan')
    def start_scan():
        data=request.get_json()
        if 'mode' in data:return start_original_scan(data)
        names=data.get('companies',[])
        if not isinstance(names,list) or not 1<=len(names)<=5:return jsonify(error='Choose one to five companies per discovery scan.'),400
        targets=[c for c in catalog() if c['name'] in names]
        if not targets:return jsonify(error='No matching companies.'),400
        if not begin('discovery',len(targets)):return jsonify(error='A task is already running.'),409
        threading.Thread(target=scan_worker,args=(targets,),daemon=True).start()
        return jsonify(status='started',total=len(targets))

    @app.get('/api/coverage')
    def source_coverage():
        from scan_coordinator import CoverageLedger
        run_id=store.get('meta','scanner_selection',{}).get('run_id','')
        ledger=CoverageLedger(store,run_id)
        return jsonify(run_id=run_id,summary=ledger.summary(),targets=ledger.rows())

    @app.get('/api/status')
    def status():
        with lock:result=copy.deepcopy(state)
        result['coordinator']=coordinator.snapshot()
        session=store.get('meta','scanner_selection',{})
        if session.get('run_id'):
            from scan_coordinator import CoverageLedger
            result['coverage']=CoverageLedger(store,session['run_id']).summary()
        if session:
            if session.get('status')=='running' and not result['running']:
                import campaign
                if not campaign.campaign_is_locked(research/'preloaded_search.json'):
                    session.update(status='interrupted',error='The previous scan was interrupted; completed results are saved.')
                    store.put('meta','scanner_selection',session)
            result['scanner']={k:session.get(k) for k in ('run_id','mode','status','error','started_at','completed_at')}
        return jsonify(result)

    @app.get('/api/results')
    @app.get('/api/discovery')
    def discovery():return jsonify(companies=list(store.all('discovery').values()))

    @app.get('/library/<key>')
    def library(key):
        if key not in LIBRARY:abort(404)
        if key in ('career-hub', 'dossiers'):
            import original_views
            doc=master_document()
            return original_views.career_page(BASE,doc,PROFILE) if key=='career-hub' else original_views.dossiers_page(BASE,doc)
        return send_from_directory(BASE,LIBRARY[key][0])

    @app.get('/intel')
    @app.get('/dossiers')
    def intelligence():
        import original_views
        return original_views.dossiers_page(BASE,master_document())


    return app

def port_is_serving(port):
    # Windows lets a second process bind a port that is already being listened on, so the
    # bind succeeds and the server reports a normal start while a stale instance keeps
    # answering every request. Probe for an existing listener instead of trusting bind().
    import socket
    with socket.socket() as probe:
        probe.settimeout(0.5)
        return probe.connect_ex(('127.0.0.1',port))==0

def main():
    parser=argparse.ArgumentParser(description='Sathvik career research workspace')
    parser.add_argument('--port',type=int,default=5050)
    args=parser.parse_args()
    if port_is_serving(args.port):
        print('Port '+str(args.port)+' is already serving. Stop the running portal first, or pass --port with a free port.',file=sys.stderr)
        return 1
    create_app().run(host='127.0.0.1',port=args.port,debug=False,threaded=True)
    return 0

if __name__=='__main__':sys.exit(main())
