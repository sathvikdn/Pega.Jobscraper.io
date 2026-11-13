"""Original portal selection flow backed by the current Python research engine."""
import re
from urllib.parse import urlsplit
from opportunity_data import company_key, normalize_opportunity, salary_bucket
from quality import canonical_url, effective_status

MODE_CATEGORY={'gcc_top10':'gcc','gcc_top20':'gcc','gcc_all':'gcc','si_top':'services','si_all':'services','remote_top':'global','remote_us':'global','remote_all':'global','all':'all'}

def build_catalog(directory,fresh):
    result={r['target_id']:dict(r) for r in directory if r.get('target_id')}
    result.update({r['target_id']:dict(r) for r in fresh if r.get('target_id')})
    return list(result.values())

def india_location(location):
    return bool(re.search(r'\b(india|bengaluru|bangalore|hyderabad|pune|chennai|mumbai|delhi|gurugram|gurgaon|noida|kolkata|kochi|coimbatore|ahmedabad|trivandrum)\b',str(location or ''),re.I))

def india_targets(records):
    rows=[dict(record,location=record.get('location') if india_location(record.get('location')) else 'India') for record in records
          if record.get('category') in ('gcc','product','services')
          and not re.search(r'\bremote\b',str(record.get('location','')),re.I)
          and (india_location(record.get('location')) or not record.get('location') or record.get('location')=='Worldwide')]
    return sorted(rows,key=lambda row:(row.get('category')=='services',not bool(re.search(r'bengaluru|bangalore',row.get('location',''),re.I))))

def india_job(job):
    location=str(job.get('location') or '').strip()
    if re.search(r'\bremote\b',location,re.I):return False
    return india_location(location) or location.lower() in ('','unknown','location unconfirmed','location not specified')

def select_targets(records,mode):
    if mode not in MODE_CATEGORY or mode.startswith('remote'):raise ValueError('Remote/global searches are on hold; choose an India preset.')
    category=MODE_CATEGORY[mode]
    rows=[r for r in india_targets(records) if category=='all' or r.get('category')==category or category=='gcc' and r.get('category')=='product']
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
        'remote':[],
        'all':[('all','All targets')]}
    return {category:[{'mode':mode,'label':label,'count':len(select_targets(records,mode))} for mode,label in modes] for category,modes in configs.items()}

def run_scan(targets,records,output_path,progress,stop_event,force=True):
    """Search the frozen selection while descriptions are checked concurrently."""
    from parallel_scan import run_parallel_scan
    return run_parallel_scan(targets,records,output_path,progress,stop_event,force=force)


def included_salary(job):
    return salary_bucket(job.get('salary'),20)!='below_target'

def grouped_results(jobs,targets,checkpoint,baseline=None,merge_checkpoint=True):
    checks={r['target_id']:r for r in checkpoint.get('targets',[])}
    groups={}
    alias_index={}
    selected_ids={r['target_id'] for r in targets}
    selected_urls={canonical_url(j.get('url','')) for r in checkpoint.get('targets',[]) if r.get('target_id') in selected_ids for j in r.get('jobs',[])}
    for target in targets:
        key=company_key(target['name'])
        group=groups.setdefault(key,{'name':target['name'],'category':target.get('category','unknown'),'jobs':[],'links':{},'checks':[],'new_count':0,'locations':[]})
        group['locations'].append(target.get('location',''))
        record=checks.get(target['target_id'],{})
        group['checks'].append({'status':record.get('status','pending'),'checked_at':record.get('checked_at'),'location':target.get('location',''),'target_id':target['target_id'],'diagnostics':record.get('diagnostics',[]),'partial':bool(record.get('partial'))})
        for alias in [target['name'],*target.get('keywords',[])]:alias_index.setdefault(company_key(alias),set()).add(key)
        query=record.get('source_url')
        if query and urlsplit(query).scheme in ('http','https'):group['links']['Last query']=query
        career=target.get('career_url')
        if career and urlsplit(career).scheme in ('http','https'):group['links']['Company careers']=career
    baseline_ids=set(baseline or [])
    # Prefer a newly read selected description over an older cached observation.
    indexed={canonical_url(j.get('url','')):j for j in jobs}
    for target in checkpoint.get('targets',[]) if merge_checkpoint else []:
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
        if not included_salary(job):continue
        if merge_checkpoint and (effective_status(job,job.get('verification'))=='closed' or job.get('relevance')=='unrelated'):continue
        # Drop stale jobs that were not rediscovered in the current scan
        if job.get('search_presence') == 'not_rediscovered':continue
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
            source=job.get('source') or ('LinkedIn' if host.endswith('linkedin.com') else 'Naukri' if host.endswith('naukri.com') else 'Indeed' if 'indeed.' in host else 'Employer / source')
            state={'open':'Employer page available','indexed_only':'Indexed lead','candidate':'Candidate','uncertain':'Needs recheck'}.get(job.get('status'),job.get('status','Unverified'))
            group['jobs'].append({'id':job['id'],'title':job.get('title','Role'),'company':job.get('company',group['name']),'location':job.get('location','Location unconfirmed'),'url':url,'source':source,'evidence_status':state,'checked_at':job.get('checked_at'),'is_new':baseline is not None and job['id'] not in baseline_ids,'category':group.get('category','unknown'),**{field:job.get(field) for field in ('recommendation','resume_match','description_checked_at','description_complete','sources','salary','level','work_mode','first_seen_at','last_seen_at','match_basis','normalization_issues','pipeline')}})
    for group in groups.values():
        group['jobs']=list({j['id']:j for j in group['jobs']}.values())
        group['new_count']=sum(j['is_new'] for j in group['jobs'])
    return list(groups.values())
