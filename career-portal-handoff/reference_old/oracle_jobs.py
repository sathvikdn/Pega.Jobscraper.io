"""Oracle public CandidateExperience search and full external descriptions."""
import re
from urllib.parse import urlsplit,urlunsplit,urlencode

def oracle_context(url):
 p=urlsplit(url);m=re.search(r'/hcmUI/CandidateExperience/([^/]+)/sites/([^/?#]+)',p.path)
 if p.scheme!='https' or not m or p.username or p.password:return None
 return urlunsplit((p.scheme,p.netloc,'','','')),m.group(1),m.group(2)

def parse_search(payload,site,keyword,offset):
 items=payload.get('items')
 if not isinstance(items,list) or len(items)!=1:raise ValueError('Oracle search envelope invalid')
 data=items[0]
 if data.get('SiteNumber')!=site or str(data.get('Keyword','')).casefold()!=keyword.casefold() or data.get('Offset')!=offset:raise ValueError('Oracle query/site/offset not confirmed')
 rows=data.get('requisitionList');total=data.get('TotalJobsCount')
 if not isinstance(rows,list) or type(total) is not int or total<0:raise ValueError('Oracle result count/list missing')
 return rows,total

def scrape_oracle(url,company,keyword,checked_at,fetch,strip,related,india):
 context=oracle_context(url)
 if not context:return [],{}
 origin,language,site=context;root=origin+'/hcmRestApi/resources/latest/'
 diag={'oracle':True,'method':'oracle_public_api','partial':True,'pages_checked':0,'details_checked':0};jobs=[]
 try:
  rows=[];seen=set();expected=None
  for _ in range(100):
   query={'onlyData':'true','expand':'requisitionList','finder':f'findReqs;siteNumber={site},keyword={keyword},limit=25,offset={len(rows)}'}
   batch,total=parse_search(fetch(root+'recruitingCEJobRequisitions?'+urlencode(query)),site,keyword,len(rows))
   diag['pages_checked']+=1;diag['reported_total']=total
   if expected is not None and total!=expected:raise ValueError('Oracle total changed')
   expected=total
   if total==0:
    diag.update(partial=False,verified_empty=True,verified_search=True);return [],diag
   if not batch:raise ValueError('Oracle premature end of results')
   for row in batch:
    identity=str(row.get('Id',''))
    if not identity or identity in seen:raise ValueError('Oracle missing/repeated requisition')
    seen.add(identity);rows.append(row)
   if len(rows)>=total:break
  if len(rows)!=expected:raise ValueError('Oracle result count incomplete')
  for row in rows:
   identity=str(row['Id'])
   detail_url=root+'recruitingCEJobRequisitionDetails?'+urlencode({'onlyData':'true','finder':f'ById;Id={identity},siteNumber={site}'})
   payload=fetch(detail_url)
   details=payload.get('items',[])
   if len(details)!=1 or str(details[0].get('Id'))!=identity:raise ValueError('Oracle detail identity missing/mismatch')
   detail=details[0];description=strip(' '.join(str(detail.get(k) or '') for k in ['ExternalDescriptionStr','ExternalResponsibilitiesStr','ExternalQualificationsStr']))
   if not description:raise ValueError('Oracle full description missing')
   diag['details_checked']+=1
   title=detail.get('Title') or row.get('Title','');location=detail.get('PrimaryLocation') or row.get('PrimaryLocation','')
   if not related(title+' '+description) or not (detail.get('PrimaryLocationCountry')=='IN' or row.get('PrimaryLocationCountry')=='IN' or india(location)):continue
   jobs.append({'title':title,'company':company,'url':f'{origin}/hcmUI/CandidateExperience/{language}/sites/{site}/job/{identity}','location':location,'description_text':description,'description':description[:500],'description_complete':True,'description_source_url':detail_url,'job_detail_status':'read','source':'Employer career page','checked_at':checked_at,'requisition_id':identity,'posted_at':row.get('PostedDate'),'vacancy_scope':'structured_job'})
  diag.update(partial=False,verified_search=True)
 except Exception as exc:
  diag['error']=str(exc)[:250]
  if getattr(exc,'code',None):diag['http_status']=exc.code
 return jobs,diag
