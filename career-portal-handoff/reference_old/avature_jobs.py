"""Avature SearchJobs listings with explicit query and total checks."""
import re
from urllib.parse import urljoin,urlsplit,quote,parse_qs,urlencode
from bs4 import BeautifulSoup
from normalizer import jsonld_jobs

def parse_results(html,url,keyword):
 soup=BeautifulSoup(html,'html.parser')
 field=soup.select_one('input[name="search"], input[name="semanticSearch"]')
 if not field or field.get('value','').casefold()!=keyword.casefold():raise ValueError('Avature keyword not confirmed')
 if field.get('name')=='semanticSearch' and parse_qs(urlsplit(url).query).get('semanticSearch')!=[keyword]:
  raise ValueError('Avature semantic query not confirmed')
 label=soup.select_one('.list-controls__text__legend');text=label.get_text(' ',strip=True) if label else ''
 match=re.search(r'([\d,]+)\s+results?',text,re.I)
 if not match:
  empty=soup.select_one('.section__content__results')
  if empty and re.match(r'^No jobs found(?:\.|$)',empty.get_text(' ',strip=True),re.I) and not soup.select('a[href*="/JobDetail/"]'):
   return [],0,None
  if soup.find(string=re.compile(r'There are no jobs that match your search criteria',re.I)):return [],0,None
  raise ValueError('Avature total missing')
 total=int(match.group(1).replace(',',''))
 urls=list(dict.fromkeys(urljoin(url,a['href']) for a in soup.select('a[href*="/JobDetail/"]') if urlsplit(urljoin(url,a['href'])).hostname==urlsplit(url).hostname))
 nxt=soup.select_one('a[rel="next"], a[aria-label="Next"], .pagination__item--next a[href]')
 return urls,total,urljoin(url,nxt['href']) if nxt and nxt.get('href') else None

def parse_detail(html,url):
 soup=BeautifulSoup(html,'html.parser')
 match=re.search(r'/JobDetail/(\d+)(?:/|$)',urlsplit(url).path,re.I)
 title=soup.select_one('.section__header__text')
 location=soup.select_one('.tf_locations .article__content__view__field__value')
 description=soup.select_one('.tf_replaceFieldVideoTokens .article__content__view__field__value')
 identity=next((re.search(r'\bJob ID\s+(\d+)\b',field.get_text(' ',strip=True),re.I)
                for field in soup.select('.article__content__view__field')
                if re.search(r'\bJob ID\s+\d+\b',field.get_text(' ',strip=True),re.I)),None)
 if not match or not identity or match.group(1)!=identity.group(1):
  raise ValueError('Avature detail identity missing/mismatch')
 if not title or not location or not description:
  raise ValueError('Avature detail fields missing')
 title_text=title.get_text(' ',strip=True)
 location_text=location.get_text(' ',strip=True)
 description_text=description.get_text(' ',strip=True)
 if not title_text or not location_text or not description_text:
  raise ValueError('Avature detail fields empty')
 return {'title':title_text,'location':location_text,'description_text':description_text,'requisition_id':identity.group(1)}

def scrape_avature(page,company,keyword,checked_at,navigate,extract,related,india):
 form=page.query_selector('form#tpt_jobSortableForm[action]')
 if not form:return [],{}
 action=urljoin(page.url,form.get_attribute('action') or '')
 if '/SearchJobs' not in action or urlsplit(action).hostname!=urlsplit(page.url).hostname:return [],{}
 action=action.split('#')[0].split('?')[0]
 if not page.query_selector('input[name="search"]') and page.query_selector('input[name="semanticSearch"]'):
  target=action+'?'+urlencode({'semanticSearch':keyword})
 else:
  target=action.rstrip('/')+'/'+quote(keyword)+'?listFilterMode=1'
 diag={'avature':True,'partial':True,'method':'avature_search','pages_checked':0,'details_checked':0};jobs=[]
 try:
  urls=[];expected=None
  for _ in range(100):
   navigate(page,target,timeout=25000)
   batch,total,nxt=parse_results(page.content(),page.url,keyword)
   diag['pages_checked']+=1;diag['reported_total']=total
   if expected is not None and total!=expected:raise ValueError('Avature total changed')
   expected=total
   if total==0:
    diag.update(partial=False,verified_empty=True,verified_search=True,final_url=page.url);return [],diag
   if not batch or any(u in urls for u in batch):raise ValueError('Avature missing/repeated results')
   urls.extend(batch)
   if len(urls)==total:break
   if not nxt or urlsplit(nxt).hostname!=urlsplit(page.url).hostname:raise ValueError('Avature next page unavailable')
   target=nxt
  if len(urls)!=expected:raise ValueError('Avature incomplete listing count')
  for url in urls:
   if urlsplit(url).hostname!=urlsplit(target).hostname:raise ValueError('Avature unexpected detail host')
   navigate(page,url,timeout=25000)
   if urlsplit(page.url).hostname!=urlsplit(url).hostname:
    raise ValueError('Avature detail redirected to another host')
   postings=list(jsonld_jobs(page.content()))
   if any(p.get('title') and p.get('description') for p in postings):
    jobs.extend(extract(page,company,checked_at))
   else:
    detail=parse_detail(page.content(),page.url)
    if detail['requisition_id']!=urlsplit(url).path.rstrip('/').rsplit('/',1)[-1]:
     raise ValueError('Avature detail redirected to another job')
    if related(detail['title']+' '+detail['description_text']) and india(detail['location']):
     jobs.append({**detail,'company':company,'url':page.url,'source':'Employer career page',
                  'checked_at':checked_at,'description':detail['description_text'][:500],
                  'description_complete':True,'description_source_url':page.url,'job_detail_status':'read'})
   diag['details_checked']+=1
  diag.update(partial=False,verified_search=True,final_url=target)
 except Exception as exc:diag['error']=str(exc)[:250]
 return jobs,diag
