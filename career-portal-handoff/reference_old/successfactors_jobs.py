"""Total-checked SuccessFactors public search forms and RMK v1 API (not recommended jobs)."""
import re
from urllib.parse import urljoin,urlsplit,urlencode,parse_qs
from bs4 import BeautifulSoup
from normalizer import jsonld_jobs

def parse_results(html,url,keyword):
 soup=BeautifulSoup(html,'html.parser')
 if parse_qs(urlsplit(url).query).get('q')!=[keyword]:raise ValueError('Keyword not confirmed in search URL')
 empty=soup.select_one('#noresults')
 if empty and re.search(r'no open positions matching\s*["“]?\s*'+re.escape(keyword)+r'\b',empty.get_text(' ',strip=True),re.I):return [],0
 label=soup.select_one('.paginationLabel')
 match=re.search(r'of\s+([\d,]+)',label.get_text(' ',strip=True) if label else '',re.I)
 if not match:raise ValueError('Search result total not found')
 urls=list(dict.fromkeys(urljoin(url,a['href']) for a in soup.select('#searchresults a.jobTitle-link[href]')))
 return urls,int(match.group(1).replace(',',''))

def parse_rmk_detail(html,url):
 soup=BeautifulSoup(html,'html.parser')
 desc=soup.select_one('.jobdescription, [itemprop="description"], .jobDisplay')
 title=soup.select_one('h1, [itemprop="title"], .jobTitle')
 if not desc or not title:raise ValueError('SuccessFactors RMK detail missing title/description')
 desc_text=desc.get_text(' ',strip=True)
 title_text=title.get_text(' ',strip=True)
 if not desc_text or not title_text:raise ValueError('SuccessFactors RMK detail empty')
 loc_el=soup.select_one('[itemprop="jobLocation"], .jobGeoLocation')
 loc_text=loc_el.get_text(' ',strip=True) if loc_el else ''
 return {'title':title_text,'description_text':desc_text,'location':loc_text}

def scrape_successfactors_rmk(page,company,keyword,checked_at,navigate,extract,related,india):
 html=page.content()
 if '/platform/css/j2w/' not in html and 'JobsSearch_appContainer' not in html and 'rmk-jobs-search' not in html:
  return [],{}
 host=urlsplit(page.url).hostname
 diag={'successfactors':True,'method':'successfactors_rmk_api','partial':True,'pages_checked':0,'details_checked':0};jobs=[]
 try:
  locale=page.evaluate('() => (document.documentElement.getAttribute("lang") || "en_US").replace("-", "_")')
  rows=[];seen=set();expected=None
  for page_num in range(100):
   res=page.evaluate('''async ({locale, pageNumber, keywords}) => {
     const r = await fetch('/services/recruiting/v1/jobs', {
       method: 'POST',
       headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
       body: JSON.stringify({locale, pageNumber, sortBy: '', keywords, location: '', facetFilters: {}, brand: '', skills: [], categoryId: 0, alertId: '', rcmCandidateId: ''})
     });
     return {http: r.status, data: r.ok ? await r.json() : null};
   }''',{'locale':locale,'pageNumber':page_num,'keywords':keyword})
   if res.get('http')!=200 or not isinstance(res.get('data'),dict):
    raise ValueError('SuccessFactors RMK API HTTP '+str(res.get('http')))
   data=res['data'];total=data.get('totalJobs')
   if type(total) is not int or total<0:raise ValueError('SuccessFactors RMK totalJobs missing')
   diag['pages_checked']+=1;diag['reported_total']=total
   if expected is not None and total!=expected:raise ValueError('SuccessFactors RMK total changed')
   expected=total
   if total==0:
    diag.update(partial=False,verified_empty=True,verified_search=True,final_url=page.url);return [],diag
   batch=data.get('jobSearchResult') or []
   if not isinstance(batch,list) or not batch:raise ValueError('SuccessFactors RMK empty result page')
   for item in batch:
    resp=item.get('response') if isinstance(item,dict) else None
    if not isinstance(resp,dict) or not resp.get('id'):raise ValueError('SuccessFactors RMK malformed item')
    jid=str(resp['id'])
    if jid in seen:raise ValueError('SuccessFactors RMK repeated item')
    seen.add(jid);rows.append(resp)
   if len(rows)>=total:break
  if len(rows)!=expected:raise ValueError('SuccessFactors RMK incomplete count')
  for resp in rows:
   jid=str(resp['id'])
   url_title=resp.get('urlTitle') or resp.get('unifiedUrlTitle') or 'job'
   loc_list=resp.get('jobLocationShort') or resp.get('jobLocationCountry') or []
   loc_str='; '.join(str(x).strip() for x in loc_list if x) or 'Location unconfirmed'
   detail_url=f"https://{host}/job/{url_title}/{jid}-{locale}/"
   navigate(page,detail_url,timeout=25000)
   postings=list(jsonld_jobs(page.content()))
   if any(p.get('title') and p.get('description') for p in postings):
    jobs.extend(extract(page,company,checked_at))
   else:
    d=parse_rmk_detail(page.content(),page.url)
    title_text=resp.get('unifiedStandardTitle') or d['title']
    final_loc=d['location'] if d['location'] else loc_str
    if related(title_text+' '+d['description_text']) and india(final_loc):
     jobs.append({'title':title_text,'company':company,'url':page.url,'location':final_loc,'source':'Employer career page','checked_at':checked_at,'description':d['description_text'][:500],'description_text':d['description_text'],'description_complete':True,'description_source_url':page.url,'job_detail_status':'read','requisition_id':jid})
   diag['details_checked']+=1
  diag.update(partial=False,verified_search=True,final_url=page.url)
 except Exception as exc:diag['error']=str(exc)[:250]
 return jobs,diag

def scrape_successfactors(page,company,keyword,checked_at,navigate,extract,related=None,india=None):
 form=page.query_selector('form[name="keywordsearch"][action]')
 if not form:
  if related and india:
   return scrape_successfactors_rmk(page,company,keyword,checked_at,navigate,extract,related,india)
  return [],{}
 action=urljoin(page.url,form.get_attribute('action'));host=urlsplit(page.url).hostname
 if urlsplit(action).hostname!=host:return [],{}
 diag={'successfactors':True,'method':'successfactors_form','partial':True,'pages_checked':0,'details_checked':0};jobs=[]
 try:
  urls=[];expected=None
  for _ in range(100):
   target=action.split('?')[0]+'?'+urlencode({'q':keyword,'startrow':len(urls),'locationsearch':''})
   navigate(page,target,timeout=25000)
   batch,total=parse_results(page.content(),page.url,keyword)
   diag['pages_checked']+=1;diag['reported_total']=total
   if expected is not None and total!=expected:raise ValueError('Search total changed')
   expected=total
   if total==0:
    diag.update(partial=False,verified_empty=True,verified_search=True,final_url=page.url);return [],diag
   if not batch or any(u in urls for u in batch):raise ValueError('Missing/repeated result page')
   urls.extend(batch)
   if len(urls)>=total:break
  if len(urls)!=expected:raise ValueError('Result count incomplete')
  for url in urls:
   if urlsplit(url).hostname!=host:raise ValueError('Unexpected detail host')
   navigate(page,url,timeout=25000)
   postings=list(jsonld_jobs(page.content()))
   if any(p.get('title') and p.get('description') for p in postings):
    jobs.extend(extract(page,company,checked_at))
   elif related and india:
    d=parse_rmk_detail(page.content(),page.url)
    if related(d['title']+' '+d['description_text']) and india(d['location']):
     jobs.append({'title':d['title'],'company':company,'url':page.url,'location':d['location'] or 'Location unconfirmed','source':'Employer career page','checked_at':checked_at,'description':d['description_text'][:500],'description_text':d['description_text'],'description_complete':True,'description_source_url':page.url,'job_detail_status':'read'})
   else:
    raise ValueError('Structured description missing')
   diag['details_checked']+=1
  diag.update(partial=False,verified_search=True,final_url=target)
 except Exception as exc:diag['error']=str(exc)[:250]
 return jobs,diag
