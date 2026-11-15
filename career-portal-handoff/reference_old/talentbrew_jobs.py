"""TalentBrew keyword-only searches, without inferred browser geolocation."""
import re
from urllib.parse import urljoin,urlsplit,urlunsplit,quote
from bs4 import BeautifulSoup
from normalizer import jsonld_jobs

def parse_results(html,keyword):
 soup=BeautifulSoup(html,'html.parser');root=soup.select_one('#search-results')
 if not root:raise ValueError('TalentBrew search results missing')
 links=list(dict.fromkeys(a['href'] for a in root.select('#search-results-list a[data-job-id][href]')))
 if root.has_attr('data-total-results') or root.has_attr('data-total-job-results'):
  # Structured attributes are authoritative and expose location drift hidden in text.
  if root.get('data-keywords','').casefold()!=keyword.casefold() or root.get('data-location',''):
   raise ValueError('TalentBrew structured keyword/location not confirmed')
  raw_total=(root.get('data-total-job-results') or root.get('data-total-results') or '').replace(',','')
  if not raw_total.isdigit():raise ValueError('TalentBrew structured count invalid')
  return links,int(raw_total)
 text=root.get_text(' ',strip=True)
 match=re.search(r'(?:Showing\s+)?([\d,]+)\s+(?:Results|Jobs)\s+(?:for|found for)\s+["“]?'+re.escape(keyword)+r'\b',text,re.I)
 if not match:raise ValueError('TalentBrew keyword/count not confirmed')
 return links,int(match.group(1).replace(',',''))

def scrape_talentbrew(page,company,keyword,checked_at,navigate,extract):
 html=page.content();m=re.search(r'talentbrew\.com/company/(\d+)/',html)
 if not m:m=re.search(r'/search-jobs/[^/]+/(\d+)/1',html)
 form=page.query_selector('form[data-selector-name="searchform"][action]')
 if form:
  action=urljoin(page.url,form.get_attribute('action') or '')
  if 'search-jobs' not in action or not m:return [],{}
  target=action.rstrip('/')+'/'+quote(keyword)+'/'+m.group(1)+'/1'
 elif page.query_selector('#search-results[data-total-results], #search-results[data-total-job-results]'):
  parsed=urlsplit(page.url)
  prefix=parsed.path.split('/search-jobs')[0] if '/search-jobs' in parsed.path else ''
  base_action=urlunsplit((parsed.scheme,parsed.netloc,prefix+'/search-jobs','',''))
  target=base_action+'/'+quote(keyword)+(f'/{m.group(1)}/1' if m else '')
 else:return [],{}
 diag={'talentbrew':True,'partial':True,'method':'talentbrew_keyword_only','pages_checked':0,'details_checked':0};jobs=[]
 try:
  navigate(page,target,timeout=25000);urls=[];expected=None
  for _ in range(100):
   batch,total=parse_results(page.content(),keyword)
   diag['pages_checked']+=1;diag['reported_total']=total
   if expected is not None and total!=expected:raise ValueError('TalentBrew total changed')
   expected=total
   if total==0:
    diag.update(partial=False,verified_search=True,verified_empty=True,final_url=page.url);return [],diag
   batch=[urljoin(page.url,u) for u in batch]
   if not batch or any(u in urls for u in batch):raise ValueError('TalentBrew missing/repeated results')
   urls.extend(batch)
   if len(urls)==total:break
   nxt=page.get_by_role('link',name='Next',exact=True)
   if not nxt.count() or not nxt.first.is_visible():raise ValueError('TalentBrew next page missing')
   nxt.first.click(timeout=5000);page.wait_for_timeout(2000)
  if len(urls)!=expected:raise ValueError('TalentBrew incomplete results')
  for url in urls:
   if urlsplit(url).hostname!=urlsplit(target).hostname:raise ValueError('Unexpected detail host')
   navigate(page,url,timeout=25000)
   if not any(p.get('title') and p.get('description') for p in jsonld_jobs(page.content())):raise ValueError('TalentBrew description missing')
   jobs.extend(extract(page,company,checked_at));diag['details_checked']+=1
  diag.update(partial=False,verified_search=True,final_url=target)
 except Exception as exc:diag['error']=str(exc)[:250]
 return jobs,diag
