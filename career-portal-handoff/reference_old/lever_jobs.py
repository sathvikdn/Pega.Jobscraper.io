"""Read Lever's documented public postings API, without browser guessing."""
from urllib.parse import urlsplit, quote

def lever_site(url):
    p=urlsplit(url)
    parts=[x for x in p.path.split('/') if x]
    if p.scheme!='https' or p.hostname not in ('jobs.lever.co','jobs.eu.lever.co') or not parts:return None
    return ('api.eu.lever.co' if p.hostname=='jobs.eu.lever.co' else 'api.lever.co',parts[0])

def scrape_lever(url,company,fetch,strip_html,is_pega,is_india,checked_at,stop_event,page_size=100,max_pages=100):
    site=lever_site(url)
    if not site:return [],{'lever':False}
    host,slug=site
    base='https://'+host+'/v0/postings/'+quote(slug,safe='')
    diag={'lever':True,'source':'lever_public_api','url':url,'checked_at':checked_at,'partial':True,'returned':0}
    jobs=[];seen=set();missing=False
    try:
        for page in range(max_pages):
            if stop_event.is_set():raise InterruptedError('Scan cancelled')
            if page and stop_event.wait(2):raise InterruptedError('Scan cancelled')
            endpoint=base+'?mode=json&skip='+str(page*page_size)+'&limit='+str(page_size)
            postings=fetch(endpoint)
            if not isinstance(postings,list):raise ValueError('Unrecognized Lever response')
            diag['pages']=page+1
            for post in postings:
                if not isinstance(post,dict) or not post.get('id'):raise ValueError('Malformed Lever posting')
                if post['id'] in seen:raise ValueError('Repeated Lever posting; pagination incomplete')
                seen.add(post['id']);diag['returned']+=1
                categories=post.get('categories') or {}
                location='; '.join(dict.fromkeys([categories.get('location',''),*(categories.get('allLocations') or [])]))
                description=strip_html(' '.join([post.get('descriptionPlain') or post.get('description') or '',*[str(x.get('content','')) for x in post.get('lists',[])],post.get('additionalPlain') or '']))
                if not description:missing=True
                title=post.get('text','');link=post.get('hostedUrl')
                if not link or not title:missing=True;continue
                if post.get('workplaceType')=='remote':continue
                if not (post.get('country')=='IN' or is_india(location)):continue
                if not is_pega(title+' '+description):continue
                jobs.append({'title':title,'company':company,'location':location or 'India','url':link,'source':'Employer career page','checked_at':checked_at,'description_text':description,'description':description[:500],'description_complete':bool(description),'description_source_url':endpoint,'job_detail_status':'read' if description else 'unavailable','requisition_id':post['id']})
            if len(postings)<page_size:
                diag.update(partial=missing,verified_search=not missing,verified_empty=not seen,jobs_found=len(jobs),searched=True)
                return jobs,diag
        diag['error']='Lever page limit reached; additional postings may exist'
    except InterruptedError:raise
    except Exception as exc:
        diag['error']=str(exc)[:180]
        if getattr(exc,'code',None):diag['http_status']=exc.code
    diag['jobs_found']=len(jobs)
    return jobs,diag
