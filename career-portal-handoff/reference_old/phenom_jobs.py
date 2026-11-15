"""Phenom public page data; totals and detail evidence gate completeness."""
import re
from urllib.parse import urljoin,urlsplit,urlencode
from normalizer import jsonld_jobs

def validate_search(payload,keyword):
    if not isinstance(payload,dict) or payload.get('status') != 200:
        raise ValueError('Phenom search response unsuccessful')
    data=payload.get('data')
    if not isinstance(data,dict) or str(data.get('keywords','')).casefold()!=keyword.casefold():
        raise ValueError('Phenom did not confirm the requested keyword')
    jobs=data.get('jobs');total=payload.get('totalHits')
    if not isinstance(jobs,list) or type(total) is not int or total<0 or len(jobs)>total:
        raise ValueError('Phenom result list/count invalid')
    return jobs,total

def scrape_phenom(page,company,keyword,checked_at,navigate,extract):
    try: config=page.evaluate('() => window.phApp ? {baseUrl:phApp.baseUrl, pageName:phApp.pageName} : null')
    except Exception:return [],{}
    if not isinstance(config,dict) or not config.get('baseUrl'):return [],{}
    base=config['baseUrl'];diag={'phenom':True,'method':'phenom_embedded_search','partial':True,'pages_checked':0,'details_checked':0};jobs=[]
    try:
        if urlsplit(base).hostname != urlsplit(page.url).hostname:raise ValueError('Phenom base domain mismatch')
        seen=set();expected=None;detail_urls=[]
        for _ in range(100):
            search_url=urljoin(base,'search-results')+'?'+urlencode({'keywords':keyword,'from':len(seen)})
            navigate(page,search_url,timeout=25000)
            page.wait_for_function('() => window.phApp && phApp.ddo && phApp.ddo.eagerLoadRefineSearch',timeout=12000)
            rows,total=validate_search(page.evaluate('() => phApp.ddo.eagerLoadRefineSearch'),keyword)
            diag['pages_checked']+=1;diag['reported_total']=total
            if expected is not None and expected!=total:raise ValueError('Phenom total changed during pagination')
            expected=total
            if total==0:
                diag.update(partial=False,verified_empty=True,verified_search=True,final_url=page.url)
                return [],diag
            if not rows:raise ValueError('Phenom ended before reported total')
            for row in rows:
                identity=str(row.get('jobSeqNo') or row.get('jobId') or '')
                if not identity or identity in seen:raise ValueError('Phenom missing/repeated job identity')
                seen.add(identity)
                href=row.get('jobUrl') or row.get('url')
                if not href:
                    job_id=row.get('jobId');title=row.get('title')
                    if not job_id or not title:raise ValueError('Phenom missing detail URL fields')
                    href='job/'+str(job_id)+'/'+re.sub(r'[^\w]+','-',title).strip('-')
                href=urljoin(base,href)
                if urlsplit(href).scheme!='https' or urlsplit(href).hostname!=urlsplit(base).hostname:
                    raise ValueError('Phenom unexpected detail host')
                detail_urls.append(href)
            if len(seen)==total:break
        else:raise ValueError('Phenom pagination limit reached')
        diag['listings_checked']=len(seen)
        for href in detail_urls:
            navigate(page,href,timeout=25000)
            page.wait_for_function('() => !!document.querySelector(\'script[type="application/ld+json"]\')',timeout=10000)
            postings=list(jsonld_jobs(page.content()))
            if not any(p.get('title') and p.get('description') for p in postings):raise ValueError('Phenom job description missing')
            diag['details_checked']+=1
            jobs.extend(extract(page,company,checked_at))
        diag.update(partial=False,verified_search=True,final_url=search_url)
    except Exception as exc:diag['error']=str(exc)[:250]
    return jobs,diag
