"""Conserve historical source observations alongside dated independent research.

Profile URLs identify profiles, not confirmed current employees. The raw source ledger
is retained so a refresh cannot silently shrink the directory or erase old observations.
"""
import copy, hashlib, json, re
from pathlib import Path
from urllib.parse import urlsplit, unquote
from collections import Counter
from directory_data import ALIASES
from opportunity_data import company_key

BASE=Path(__file__).resolve().parent

def read(path, default=None):
    try:return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError,ValueError):return {} if default is None else default

def profile_identity(url):
    try:
        p=urlsplit(str(url or ''));host=(p.hostname or '').lower()
        m=re.match(r'/in/([^/]+)',p.path,re.I)
        if (host=='linkedin.com' or host.endswith('.linkedin.com')) and m:return 'linkedin:'+unquote(m.group(1)).lower()
    except ValueError:pass
    return ''

def seq(v):return v if isinstance(v,list) else [v] if v else []
def unique(v):
    result=[];seen=set()
    for x in v:
        key=json.dumps(x,sort_keys=True,ensure_ascii=True)
        if key not in seen:seen.add(key);result.append(x)
    return result

def build(base=BASE,research=None):
    base=Path(base);root=Path(research or base/'research')
    fresh=read(root/'independent_map.json',{'companies':[],'people':[]})
    directory=read(root/'directory.json')
    recovered=read(root/'legacy_conservation_20260908.json')
    companies={};names={};persons={};ledger=[];source_rows=[];redirects={}
    prior_catalog=read(root/'master_catalog.json')
    aliases={company_key(v):company_key(k) for k,vs in ALIASES.items() for v in [k,*vs]}
    extra_aliases={'Mercedes-Benz / MBRDI':'Mercedes-Benz R&D India (MBRDI)','Fidelity National Financial India':'Fidelity National Financial India (FNF)','FNF India':'Fidelity National Financial India (FNF)','Sun Life (additional)':'Sun Life','Optum / UnitedHealth':'Optum / UnitedHealth Group','NAB India':'NAB (National Australia Bank)','BT':'BT Group','BT Group Bengaluru':'BT Group','Pegasystems Bengaluru':'Pegasystems India','Siemens Technology India':'Siemens','Lloyds Technology Centre':'Lloyds Technology Centre India'}
    aliases.update({company_key(k):aliases.get(company_key(v),company_key(v)) for k,v in extra_aliases.items()})
    # Do not convert a historically conflated FIS/TSYS label into Global Payments.
    def co_key(name):return aliases.get(company_key(name),company_key(name))
    stable_names={}
    for old in prior_catalog.get('companies',[]):
        for name in [old['name'],*old.get('aliases',[])]:stable_names.setdefault(co_key(name),set()).add(old['id'])
    old_link_ids={old['id']:set(old.get('source_company_ids',[])) for old in prior_catalog.get('companies',[])}
    def resolved(cid):
        while cid in redirects:cid=redirects[cid]
        return cid
    def company(name,category='unclassified',preferred=None,other_names=()):
        category=category or 'unclassified'
        keys={co_key(v) for v in [name,*other_names] if v}
        ids={resolved(names[k]) for k in keys if k in names}
        saved={resolved(cid) for k in keys for cid in stable_names.get(k,[]) if cid}
        cid=sorted(ids,key=lambda x:(not x.startswith('fresh-'),x))[0] if ids else next(iter(saved)) if len(saved)==1 else (preferred or 'catalogue-'+co_key(name))
        # Only exact names and supplied aliases join groups. Keep every observation and old ID.
        for other in sorted(ids-{cid}):
            current=companies[cid];duplicate=companies.pop(other)
            for field,value in duplicate.items():
                if isinstance(value,list):current[field]=unique(current.get(field,[])+value)
                elif field=='flags':current[field]={k:bool(current.get(field,{}).get(k) or value.get(k)) for k in set(current.get(field,{}))|set(value)}
                elif not current.get(field):current[field]=copy.deepcopy(value)
            current['source_company_ids']=unique(current.get('source_company_ids',[])+[other])
            redirects[other]=cid
            for key,value in list(names.items()):
                if value==other:names[key]=cid
        if cid not in companies:
            companies[cid]={'id':cid,'name':name,'category':category,'aliases':[], 'claims':[],'hiring_signals':[],'limitations':[], 'flags':{},'legacy_snapshots':[],'source_rows':[],'search_targets':[]}
        c=companies[cid]
        if c['category']=='unclassified' and category!='unclassified':c['category']=category
        c['aliases']=unique([*c['aliases'],name,*other_names])
        c['source_company_ids']=unique(c.get('source_company_ids',[])+sorted(saved-{cid})+sorted({link for prior in saved|{cid} for link in old_link_ids.get(prior,set())}))
        for k in keys:
            if k not in names or names[k]==cid:names[k]=cid
        return c
    def add_person(raw,c,source_id,legacy=False):
        if not raw.get('name') or str(raw['name']).strip() in ('—','-','Unknown','Not identified'):return
        url=raw.get('profile_url') or raw.get('linkedin') or raw.get('source_url')
        ident=profile_identity(url) or 'named:'+c['id']+':'+company_key(raw['name'])
        certs=seq(raw.get('certifications'))+seq(raw.get('certs'))
        obs=copy.deepcopy(raw)
        obs.update(company_id=c['id'],company=c['name'],source_record_id=source_id)
        if legacy:
            obs.update(access='legacy',checked_at=None,source_file=raw.get('source_file') or source_id.split('#')[0],source_date=raw.get('source_date') or raw.get('tenure') or raw.get('dates'),
                       employer_as_stated=raw.get('employer_as_stated') or raw.get('company_as_stated') or c['name'],profile_url=url if profile_identity(url) else None,
                       source_url=url,location_as_stated=raw.get('location_as_stated') or raw.get('location'),
                       work_summary=raw.get('work_summary') or raw.get('detail') or raw.get('pega_connection') or 'Earlier named professional record; current employer, role and location need rechecking.',
                       certifications=certs)
        p=persons.setdefault(ident,{'id':hashlib.sha256(ident.encode()).hexdigest()[:18],'identity_key':ident,'name':raw['name'], 'company':c['name'],'company_id':c['id'],'company_ids':[], 'observations':[],'certifications':[]})
        p['company_ids']=unique(p['company_ids']+[c['id']])
        p['observations'].append(obs);p['certifications']=unique(p['certifications']+certs)
        # Fresh observations are added first; older rows only fill missing displayed fields.
        replace_primary=bool(obs.get('crosschecked') and not p.get('crosschecked'))
        if replace_primary:p.update(name=raw['name'],company=c['name'],company_id=c['id'],crosschecked=True)
        for key in ('title','profile_url','source_url','location_as_stated','work_summary','pega_connection','checked_at','access','source_date'):
            if legacy and any(o.get('access') not in (None,'legacy') for o in p['observations']):continue
            if replace_primary:p[key]=obs.get(key)
            elif not p.get('crosschecked') and not p.get(key) and obs.get(key):p[key]=obs[key]
        if not p.get('access'):p['access']='legacy'
        source_rows.append({'source_record_id':source_id,'person_id':p['id'],'company_id':c['id']})
    for raw in fresh.get('companies',[]):
        c=company(raw['name'],raw.get('category','unclassified'),raw.get('id'),raw.get('aliases',[]))
        c['source_company_ids']=unique(c.get('source_company_ids',[])+[raw['id']])
        for k,v in raw.items():
            if k in ('claims','hiring_signals','limitations'):c[k]=unique(c.get(k,[])+copy.deepcopy(v))
            elif k=='flags':c[k]={flag:bool(c.get(k,{}).get(flag) or v.get(flag)) for flag in set(c.get(k,{}))|set(v)}
            elif k not in ('id','name','aliases','people'):c[k]=copy.deepcopy(v)
        c['evidence_status']='dated_public_research'
    for i,p in enumerate(fresh.get('people',[])):
        for j,obs in enumerate(p.get('observations') or [p]):
            source_id=obs.get('company_id') or p.get('company_id')
            source_company=companies.get(source_id) or next((c for c in companies.values() if source_id in c.get('source_company_ids',[])),None)
            c=source_company or company(obs.get('company') or p.get('company') or obs.get('employer_as_stated') or 'Employer unconfirmed')
            add_person(obs,c,'independent_map.json#people/'+str(i)+'/observations/'+str(j))
    ledger.append({'source':'independent_map.json','company_rows':len(fresh.get('companies',[])),'person_rows':len(fresh.get('people',[]))})
    # All original scan targets are retained even where no Pega team is established.
    for i,t in enumerate(directory.get('records',[])):
        c=company(t['name'],t.get('category','unclassified'))
        c['search_targets'].append(copy.deepcopy(t))
        c['evidence_status']=c.get('evidence_status') or 'search_target_only'
        c['source_rows'].append({'source_record_id':'directory.json#records/'+str(i),'target_id':t['target_id']})
    snapshots=[('directory.json#historical_snapshots',directory.get('historical_snapshots',[]))]
    for filename in ('team_intelligence.json','team_intelligence_enriched.json'):
        snapshots.append((filename,read(base/filename).get('companies',[])))
    for source,rows in snapshots:
        count=0
        for i,raw in enumerate(rows):
            c=company(raw['name'],'gcc');rid=source+'/'+str(i)
            c['legacy_snapshots'].append({'source_record_id':rid,'data':copy.deepcopy(raw)})
            c['evidence_status']=c.get('evidence_status') or 'legacy_unverified'
            # Merged historical snapshot displays the rich details; base variants remain in ledger.
            if source.startswith('directory'):
                c['legacy_details']=copy.deepcopy(raw)
                if raw.get('projects'):c['claims'].append({'type':'project','text':raw['projects'],'access':'legacy','source_file':source,'source_url':None,'source_date':None,'confidence':'unverified','checked_at':None})
            for j,p in enumerate(raw.get('team_members',[])):
                add_person(p,c,rid+'/team_members/'+str(j),True);count+=1
            for j,p in enumerate(raw.get('_hiring_playbook',{}).get('bangalore_intel',{}).get('contacts',[])):
                if isinstance(p,dict):add_person(p,c,rid+'/bangalore_contacts/'+str(j),True)
        ledger.append({'source':source,'company_rows':len(rows),'person_rows':count})
    # Recent team notes are distinct observations; never assert they are live rosters.
    recent=directory.get('recent_teams',[])
    if isinstance(recent,dict):recent=[dict(v,name=k) for k,v in recent.items() if isinstance(v,dict)]
    for i,row in enumerate(recent):
        if not isinstance(row,dict):continue
        name=row.get('name') or row.get('company')
        if not name:continue
        c=company(name)
        c.setdefault('recent_team_notes',[]).append(copy.deepcopy(row))
        for j,source in enumerate(row.get('sources',[])):
            if profile_identity(source.get('url')):
                title=source.get('title','')
                named=title.split('—',1)[0].strip()
                if named and named!=title:
                    add_person({'name':named,'profile_url':source['url'],'source_url':source['url'],'work_summary':source.get('excerpt'),'source_date':source.get('published_at'),'source_file':'directory.json','company_as_stated':name},c,'directory.json#recent_teams/'+str(i)+'/sources/'+str(j),True)
        for j,p in enumerate(row.get('people',[]) or row.get('team_members',[])):
            add_person(p,c,'directory.json#recent_teams/'+str(i)+'/'+str(j),True)
    # Extraction keys are normalized by the import step and preserve every raw Hub row.
    for i,row in enumerate(recovered.get('company_observations',[])):
        if row.get('entity_kind') not in (None,'company_or_group'):continue
        name=row.get('company') or row.get('name')
        if name:
            c=company(name,row.get('category','unclassified'));c['source_rows'].append(copy.deepcopy(row))
    for i,p in enumerate(recovered.get('professional_observations',[])):
        name=p.get('company') or p.get('employer_as_stated')
        if name:add_person(p,company(name),p.get('source_record_id') or 'career-hub#person/'+str(i),True)
    for path in sorted(root.glob('team_depth_*.json')):
        depth=read(path);rows=depth.get('team_depth',[]);count=0
        for i,row in enumerate(rows):
            c=company(row['company'],row.get('category','unclassified'),other_names=row.get('match_names',[]))
            c.setdefault('team_depth',[]).append(copy.deepcopy(row))
            for j,p in enumerate(row.get('people',[])):
                add_person(dict(p,work_summary=p.get('connection_to_team')),c,path.name+'#team_depth/'+str(i)+'/people/'+str(j),True);count+=1
        ledger.append({'source':path.name,'company_rows':len(rows),'person_rows':count})
    for c in companies.values():
        c['evidence_status']=c.get('evidence_status') or 'legacy_unverified'
        c['legacy_snapshots']=unique(c['legacy_snapshots'])
        c['current_team_size']=None
    for p in persons.values():
        p['company_id']=resolved(p['company_id'])
        p['company_ids']=unique([resolved(cid) for cid in p['company_ids']])
        for obs in p['observations']:obs['company_id']=resolved(obs['company_id'])
        p['observations']=unique(p['observations'])
        p['limitations']=unique([v for obs in p['observations'] for v in obs.get('limitations',[])])
    for row in source_rows:row['company_id']=resolved(row['company_id'])
    rows=list(companies.values());people=list(persons.values())
    return {'schema_version':1,'research_date':fresh.get('research_date'),'companies':rows,'people':people,'queries':fresh.get('queries',[]),
            'source_ledger':ledger,'person_source_rows':source_rows,'recovered_source_ledger':recovered.get('source_ledger',{}),
            'movement_observations':recovered.get('movement_observations',[]),'legacy_hub_rows':recovered.get('table_rows',[]),'legacy_company_observations':recovered.get('company_observations',[]),
            'stats':{'companies':len(rows),'people_records':len(people),'unique_linkedin_profiles':sum(bool(profile_identity(p.get('profile_url'))) for p in people),
                     'people_observations':sum(len(p['observations']) for p in people),'source_person_rows':len(source_rows),'bangalore_companies':sum(bool(c.get('flags',{}).get('bangalore')) for c in rows),
                     'fresh_companies':len(fresh.get('companies',[])),'legacy_company_snapshots':len(directory.get('historical_snapshots',[])),
                     'crosscheck_records':sum(x.get('type')=='crosscheck' for c in rows for x in c.get('claims',[])),'crosschecked_companies':sum(any(x.get('type')=='crosscheck' for x in c.get('claims',[])) for c in rows),
                     'original_scan_targets':len(directory.get('records',[])),'categories':dict(Counter(c['category'] for c in rows))},
            'definitions':{'people_records':'Profile URL identities, or unresolved name/employer records. Not a current employee count.','legacy':'Restored original observation, not freshly verified.','search_target_only':'Included in the original scan catalogue; Pega usage is not established.'}}

def extra_targets(doc,existing):
    represented={company_key(t['name']) for t in existing}
    result=[]
    for c in doc.get('companies',[]):
        if c.get('search_targets') or any(company_key(n) in represented for n in [c['name'],*c.get('aliases',[])]):continue
        category=c.get('category','unclassified')
        result.append({'target_id':c['id'],'name':c['name'],'keywords':[c['name']], 'category':category if category in ('gcc','services','global') else 'gcc',
                       'location':'India','catalog_scope':'restored','location_basis':'India search scope; assignment location unconfirmed'})
    return result

if __name__=='__main__':
    doc=build();(BASE/'research/master_catalog.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(doc['stats']))
