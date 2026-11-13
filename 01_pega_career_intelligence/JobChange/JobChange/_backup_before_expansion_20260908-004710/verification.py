"""Conservative public listing rechecks. Access failure never proves a job closed."""
import ipaddress
import json
import re
import socket
from datetime import date
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup
from quality import canonical_url, iso_date, normalized_name
from storage import now

def public_url(url):
    p = urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None,443):
        raise ValueError('Only public HTTPS sources are supported.')
    for item in socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(item[4][0]).is_global:
            raise ValueError('Private network addresses are not allowed.')
    return url

def classify_page(html, expected_title='', today=None):
    soup = BeautifulSoup(html,'html.parser')
    text = soup.get_text(' ',strip=True)
    lower = text.lower()
    # Match explicit closure messages, not navigation links to other/expired jobs.
    closed = ('this job is no longer available', 'this position has been filled',
              'this job has expired', 'this job posting is no longer active',
              'job you are looking for is no longer', 'job you are trying to apply for has been filled')
    if any(x in lower for x in closed):
        return 'closed','The page explicitly says this vacancy is unavailable.'
    def walk(obj):
        if isinstance(obj,list):
            for item in obj: yield from walk(item)
        elif isinstance(obj,dict):
            kind=obj.get('@type',[])
            if kind == 'JobPosting' or isinstance(kind,list) and 'JobPosting' in kind:
                yield obj
            for key in ('@graph','mainEntity'):
                if key in obj: yield from walk(obj[key])
    apply_controls=[e.get_text(' ',strip=True).lower() or e.get('value','').lower() for e in soup.select('a[href],button,input[type=submit]')]
    has_apply=any(re.search(r'\bapply(?: now| for| online| to)?\b',x) for x in apply_controls)
    expected=normalized_name(expected_title)
    all_jobs=[]
    for script in soup.select('script[type="application/ld+json"]'):
        try: objects=list(walk(json.loads(script.string or script.get_text())))
        except (ValueError,TypeError): continue
        all_jobs.extend(objects)
    # A multi-job search page cannot establish availability of one saved requisition.
    if len(all_jobs)>1:
        return 'uncertain','Multiple job postings were returned; review the exact requisition manually.'
    for obj in all_jobs:
        if expected and normalized_name(obj.get('title','')) == expected:
            expiry=iso_date(obj.get('validThrough'))
            if expiry and expiry < (today or date.today()):
                return 'closed','The employer structured listing has passed its valid-through date.'
            # Structured jobs may persist after closure, so require an application control too.
            if has_apply:
                return 'open','A structured job posting and application control were found.'
    title_match=bool(expected) and any(normalized_name(h.get_text(' ',strip=True))==expected for h in soup.select('h1'))
    if not all_jobs and title_match and has_apply and ('pega' in lower or 'prpc' in lower):
        return 'open','The role text and an application link were found; availability can still change.'
    return 'uncertain','Could not confirm a live role and application control from the returned page.'

def recheck(record):
    result={'checked_at':now(),'status':'uncertain','url':record['url'],'method':'HTTP page check'}
    try:
        url=record['url']
        for _ in range(5):
            public_url(url)
            with requests.get(url,timeout=(8,18),allow_redirects=False,stream=True,
                              headers={'User-Agent':'CareerResearch/2.0 (personal listing freshness check)'}) as response:
                result['http_status']=response.status_code
                if response.status_code in (301,302,303,307,308):
                    url=urljoin(url,response.headers.get('Location','')); continue
                if response.status_code in (404,410):
                    result.update(status='closed',detail='The saved listing URL returned HTTP '+str(response.status_code)+'.'); return result
                if response.status_code != 200:
                    result.update(status='unavailable',detail='Source returned HTTP '+str(response.status_code)+'. This does not prove the vacancy is closed.'); return result
                body=bytearray()
                for chunk in response.iter_content(16384):
                    body.extend(chunk)
                    if len(body)>2_000_000: break
                if canonical_url(url) != canonical_url(record['url']):
                    result.update(status='uncertain',detail='The saved URL redirected to a different listing address. Review the requisition manually.',final_url=url)
                    return result
                status,detail=classify_page(body.decode(response.encoding or 'utf-8',errors='replace'),record.get('title',''))
                result.update(status=status,detail=detail,final_url=url); return result
        result['detail']='Too many redirects; review the employer page manually.'
    except (requests.RequestException,ValueError,OSError) as exc:
        result.update(status='unavailable',detail='Source could not be checked: '+str(exc)[:200])
    return result
