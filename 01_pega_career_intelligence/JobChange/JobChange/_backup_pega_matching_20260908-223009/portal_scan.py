"""Original portal selection flow backed by the current Python research engine."""
from urllib.parse import urlsplit
from opportunity_data import company_key, normalize_opportunity, salary_bucket
from quality import canonical_url, effective_status

MODE_CATEGORY={'gcc_top10':'gcc','gcc_top20':'gcc','gcc_all':'gcc','si_top':'services','si_all':'services','remote_top':'global','remote_us':'global','remote_all':'global','all':'all'}

def build_catalog(directory,fresh):
    result={r['target_id']:dict(r) for r in directory if r.get('target_id')}
    result.update({r['target_id']:dict(r) for r in fresh if r.get('target_id')})
    return list(result.values())

def select_targets(records,mode):
    if mode not in MODE_CATEGORY:raise ValueError('Choose one of the original scan presets.')
    category=MODE_CATEGORY[mode]
    rows=[r for r in records if category=='all' or r.get('category')==category]
    if mode in ('gcc_top10','gcc_top20'):
        return [r for r in rows if r.get('priority')=='top30'][:10 if mode=='gcc_top10' else 20]
    if mode=='si_top':return[r for r in rows if r.get('priority')=='si_top']
    if mode=='remote_top':return[r for r in rows if r.get('priority')=='remote_top']
    if mode=='remote_us':return[r for r in rows if r.get('location') in ('United States','Remote')]
    return rows

def scan_options(records):
    configs={
        'gcc':[('gcc_top10','Top 10'),('gcc_top20','Top 20'),('gcc_all','All')],
        'si':[('si_top','Top firms'),('si_all','All')],
        'remote':[('remote_top','Top targets'),('remote_us','US + Remote'),('remote_all','All Global')],
        'all':[('all','All targets')]}
    return {category:[{'mode':mode,'label':label,'count':len(select_targets(records,mode))} for mode,label in modes] for category,modes in configs.items()}

def run_scan(targets,records,output_path,progress,stop_event,force=True):
    """Execute the current scanner's Python script logic for exactly these targets."""
    import campaign
    previous=campaign.load_campaign(output_path)
    merged={r['target_id']:r for r in previous.get('targets',[]) if r.get('target_id') and r.get('name')}
    merged.update({r['target_id']:r for r in records})
    merged.update({r['target_id']:r for r in targets})
    ids=[r['target_id'] for r in targets]
    campaign.run_campaign(target_ids=ids,force=force,progress=progress,stop_event=stop_event,output_path=output_path,data=list(merged.values()))
    if not stop_event.is_set():
        campaign.enrich_campaign(output_path=output_path,progress=progress,stop_event=stop_event,force=force,target_ids=ids)

def included_salary(job):
    return salary_bucket(job.get('salary'),20)!='below_target'

def grouped_results(jobs,targets,checkpoint,baseline=None):
    checks={r['target_id']:r for r in checkpoint.get('targets',[])}
    groups={}
    alias_index={}
    selected_ids={r['target_id'] for r in targets}
    selected_urls={canonical_url(j.get('url','')) for r in checkpoint.get('targets',[]) if r.get('target_id') in selected_ids for j in r.get('jobs',[])}
    for target in targets:
        key=company_key(target['name'])
        group=groups.setdefault(key,{'name':target['name'],'jobs':[],'links':{},'checks':[],'new_count':0,'locations':[]})
        group['locations'].append(target.get('location',''))
        record=checks.get(target['target_id'],{})
        group['checks'].append({'status':record.get('status','pending'),'checked_at':record.get('checked_at'),'location':target.get('location',''),'target_id':target['target_id'],'diagnostics':record.get('diagnostics',[])})
        for alias in [target['name'],*target.get('keywords',[])]:alias_index.setdefault(company_key(alias),set()).add(key)
        query=record.get('source_url')
        if query and urlsplit(query).scheme in ('http','https'):group['links']['Last query']=query
        career=target.get('career_url')
        if career and urlsplit(career).scheme in ('http','https'):group['links']['Company careers']=career
    baseline_ids=set(baseline or [])
    # Prefer a newly read selected description over an older cached observation.
    indexed={canonical_url(j.get('url','')):j for j in jobs}
    for target in checkpoint.get('targets',[]):
        if target.get('target_id') not in selected_ids:continue
        for raw in target.get('jobs',[]):
            normalized=normalize_opportunity(raw,'campaign',target)
            if not normalized:continue
            url=canonical_url(normalized.get('url',''));prior=indexed.get(url)
            if prior:
                checked=normalized.get('job_detail_checked_at') or normalized.get('checked_at') or ''
                previous=prior.get('verification',{}).get('checked_at') if prior.get('verification') else None
                previous=previous or prior.get('job_detail_checked_at') or prior.get('checked_at') or ''
                if checked<=previous or normalized.get('job_detail_status')!='read':continue
                normalized['id']=prior['id']
            indexed[url]=normalized
    for job in indexed.values():
        if job.get('target_id') and job['target_id'] not in selected_ids and canonical_url(job.get('url','')) not in selected_urls:continue
        if effective_status(job,job.get('verification'))=='closed' or job.get('relevance')=='unrelated' or not included_salary(job):continue
        for key in alias_index.get(company_key(job.get('company','')),set()):
            group=groups[key]
            if not job.get('target_id'):
                locations=' '.join(group['locations']).lower()
                country=str(job.get('country') or '').lower()
                if not country:
                    location=str(job.get('location') or '').lower()
                    country=next((v for v in ('united states','united kingdom','canada','australia','singapore','india') if v in location),'')
                if 'worldwide' not in locations and 'remote' not in locations:
                    if 'india' in locations or 'bengaluru' in locations or 'bangalore' in locations:
                        if country and country not in ('india','unknown'):continue
                    elif 'united states' in locations and country and country not in ('united states','usa','us','unknown'):continue
            url=canonical_url(job.get('url',''))
            host=urlsplit(url).hostname or ''
            if not url or urlsplit(url).scheme not in ('https','http'):continue
            source='LinkedIn' if host.endswith('linkedin.com') else 'Naukri' if host.endswith('naukri.com') else 'Indeed' if 'indeed.' in host else 'Employer / source'
            state={'open':'Employer page available','indexed_only':'Indexed lead','candidate':'Candidate','uncertain':'Needs recheck'}.get(job.get('status'),job.get('status','Unverified'))
            group['jobs'].append({'id':job['id'],'title':job.get('title','Role'),'company':job.get('company',group['name']),'location':job.get('location','Location unconfirmed'),'url':url,'source':source,'evidence_status':state,'checked_at':job.get('checked_at'),'is_new':baseline is not None and job['id'] not in baseline_ids})
    for group in groups.values():
        group['jobs']=list({j['id']:j for j in group['jobs']}.values())
        group['new_count']=sum(j['is_new'] for j in group['jobs'])
    return list(groups.values())
