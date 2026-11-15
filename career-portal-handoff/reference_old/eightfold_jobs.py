"""Eightfold PCSX and v2 apply APIs observed from the employer's own browser requests."""
from urllib.parse import urlsplit,urlunsplit,urlencode,parse_qs,urljoin

def parse_search(payload):
 if isinstance(payload,dict) and isinstance(payload.get('positions'),list) and type(payload.get('count')) is int and payload['count']>=0 and 'data' not in payload:
  return payload['positions'],payload['count']
 if payload.get('status')!=200 or not isinstance(payload.get('data'),dict):raise ValueError('Eightfold unsuccessful response')
 data=payload['data'];rows=data.get('positions');count=data.get('count')
 if not isinstance(rows,list) or type(count) is not int or count<0:raise ValueError('Eightfold result count/list invalid')
 return rows,count

def scrape_eightfold(page,company,keyword,checked_at,strip,related,india):
 try:resources=page.evaluate('() => performance.getEntriesByType("resource").map(r=>r.name)')
 except Exception:return [],{}
 pcsx_urls=[u for u in resources if ('/api/pcsx/search?' in u or '/api/pcsx/job_cart?' in u) and urlsplit(u).scheme=='https' and urlsplit(u).netloc==urlsplit(page.url).netloc]
 v2_urls=[u for u in resources if '/api/apply/v2/jobs/' in u and 'domain=' in u and urlsplit(u).scheme=='https' and urlsplit(u).netloc==urlsplit(page.url).netloc]
 urls=pcsx_urls or v2_urls
 if not urls:return [],{}
 is_v2=bool(not pcsx_urls and v2_urls)
 observed=urlsplit(urls[-1]);params=parse_qs(observed.query);domain=params.get('domain',[''])[0]
 if not domain:return [],{}
 origin=urlunsplit((observed.scheme,observed.netloc,'','',''))
 diag={'eightfold':True,'partial':True,'method':'eightfold_observed_v2' if is_v2 else 'eightfold_observed_pcsx','pages_checked':0,'details_checked':0,'observed_api':urls[-1]};jobs=[]
 def fetch(path,query):
  page.wait_for_timeout(1500)
  endpoint=origin+path+'?'+urlencode(query)
  response=page.evaluate('''async url => {
    const reply = await fetch(url, {credentials: 'same-origin', signal: AbortSignal.timeout(20000)});
    return {http: reply.status, payload: reply.ok ? await reply.json() : null};
  }''',endpoint)
  if response['http']!=200:
   diag['http_status']=response['http'];raise ValueError('Eightfold HTTP '+str(response['http']))
  return response['payload']
 try:
  rows=[];seen=set();expected=None
  for _ in range(100):
   query_params={'domain':domain,'query':keyword,'start':len(rows),'num':10} if is_v2 else {'domain':domain,'query':keyword,'location':'','start':len(rows)}
   batch,total=parse_search(fetch('/api/apply/v2/jobs' if is_v2 else '/api/pcsx/search',query_params))
   diag['pages_checked']+=1;diag['reported_total']=total
   if expected is not None and total!=expected:raise ValueError('Eightfold total changed')
   expected=total
   if total==0:
    diag.update(partial=False,verified_empty=True,verified_search=True);return [],diag
   if not batch:raise ValueError('Eightfold premature empty page')
   for r in batch:
    identity=str(r.get('id') or '')
    if not identity or identity in seen:raise ValueError('Eightfold missing/repeated identity')
    seen.add(identity);rows.append(r)
   if len(rows)>=total:break
  if len(rows)!=expected:raise ValueError('Eightfold incomplete results')
  for r in rows:
   if is_v2:
    d=r if r.get('job_description') else fetch(f"/api/apply/v2/jobs/{r['id']}",{'domain':domain})
    if not isinstance(d,dict) or str(d.get('id'))!=str(r['id']) or not d.get('job_description'):raise ValueError('Eightfold v2 detail missing/mismatch')
    diag['details_checked']+=1;description=strip(d['job_description']);title=d.get('name','');location=', '.join(str(x) for x in (d.get('locations') or ([d['location']] if d.get('location') else [])))
    href=r.get('canonicalPositionUrl') or d.get('canonicalPositionUrl') or f"/careers/job/{r['id']}"
    req_id=str(d.get('display_job_id') or d.get('ats_job_id') or r['id'])
   else:
    payload=fetch('/api/pcsx/position_details',{'domain':domain,'position_id':r['id'],'hl':'en'})
    d=payload.get('data') or {}
    if payload.get('status')!=200 or str(d.get('id'))!=str(r['id']) or not d.get('jobDescription'):raise ValueError('Eightfold detail missing/mismatch')
    diag['details_checked']+=1;description=strip(d['jobDescription']);title=d.get('name','');location=', '.join(str(x) for x in d.get('locations',[]))
    href=r.get('positionUrl') or d.get('positionUrl')
    req_id=str(d.get('displayJobId') or r['id'])
   if not related(title+' '+description) or not india(location):continue
   if not href:raise ValueError('Eightfold canonical position URL missing')
   public_url=urljoin(origin,href)
   if urlsplit(public_url).scheme!='https' or urlsplit(public_url).netloc!=urlsplit(origin).netloc:
    raise ValueError('Eightfold unexpected detail host')
   jobs.append({'title':title,'company':company,'url':public_url,'location':location,'description':description[:500],'description_text':description,'description_complete':True,'description_source_url':public_url,'job_detail_status':'read','source':'Employer career page','checked_at':checked_at,'requisition_id':req_id,'vacancy_scope':'structured_job'})
  diag.update(partial=False,verified_search=True)
 except Exception as exc:diag['error']=str(exc)[:250]
 return jobs,diag
