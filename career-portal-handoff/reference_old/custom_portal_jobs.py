"""Verified employer-portal adapters for structured APIs and explicit search contracts."""
import json
import re
from urllib.parse import urljoin, urlsplit, urlunsplit, urlencode, parse_qs, quote
from bs4 import BeautifulSoup
from normalizer import jsonld_jobs


def scrape_paradox_jobs(page, company, keyword, checked_at, navigate, extract):
    inp = page.query_selector('input[id$="-keyword-search-input"]')
    if not inp:
        return [], {}
    parsed = urlsplit(page.url)
    host = parsed.hostname or ''
    base = urlunsplit((parsed.scheme, parsed.netloc, '', '', ''))
    target = base + '/jobs?' + urlencode({'keyword': keyword})
    diag = {'paradox': True, 'method': 'paradox_keyword_search', 'partial': True, 'pages_checked': 0, 'details_checked': 0}
    jobs = []
    try:
        navigate(page, target, timeout=25000)
        page.wait_for_timeout(1500)
        soup = BeautifulSoup(page.content(), 'html.parser')
        field = soup.select_one('input[id$="-keyword-search-input"]')
        if not field or field.get('value', '').casefold() != keyword.casefold():
            raise ValueError('Paradox keyword input not confirmed')
        text = soup.get_text(' ', strip=True)
        urls = list(dict.fromkeys(urljoin(page.url, a['href']) for a in soup.select('a[href*="/job/"]') if urlsplit(urljoin(page.url, a['href'])).hostname == host))
        if re.search(r'No\s+open\s+jobs\s+meet\s+your\s+search\s+criteria', text, re.I) and not urls:
            diag.update(partial=False, verified_empty=True, verified_search=True, reported_total=0, final_url=page.url)
            return [], diag
        match = re.search(r'Showing\s+(?:\d+\s*-\s*\d+\s+of\s+)?([\d,]+)\s+jobs', text, re.I) or re.search(r'([\d,]+)\s+related\s+jobs\s+displayed', text, re.I)
        if not match:
            raise ValueError('Paradox result total not confirmed')
        total = int(match.group(1).replace(',', ''))
        diag['pages_checked'] = 1
        diag['reported_total'] = total
        if total == 0 and not urls:
            diag.update(partial=False, verified_empty=True, verified_search=True, final_url=page.url)
            return [], diag
        if len(urls) != total:
            raise ValueError('Paradox listing count incomplete')
        for url in urls:
            navigate(page, url, timeout=25000)
            postings = list(jsonld_jobs(page.content()))
            if not any(p.get('title') and p.get('description') for p in postings):
                raise ValueError('Paradox structured description missing')
            jobs.extend(extract(page, company, checked_at))
            diag['details_checked'] += 1
        diag.update(partial=False, verified_search=True, final_url=target)
    except Exception as exc:
        diag['error'] = str(exc)[:250]
    return jobs, diag


def scrape_beesite_api(url, company, keyword, checked_at, fetch, strip, related, india):
    parsed = urlsplit(url)
    host = (parsed.hostname or '').lower()
    if 'mercedes-benz.com' in host:
        api_url = 'https://jobs.api.mercedes-benz.com/search'
        extra = []
    elif 'careers.db.com' in host:
        api_url = 'https://api-deutschebank.beesite.de/search/'
        extra = []
    elif 'daimlertruck.com' in host:
        api_url = 'https://global-jobboard-api-jobsearch.daimlertruck.com/search/'
        extra = [{'CriterionName': 'PublicationChannel.Code', 'CriterionValue': ['12']}]
    else:
        return [], {}
    diag = {'beesite': True, 'method': 'beesite_search_api', 'partial': True, 'pages_checked': 0, 'details_checked': 0}
    jobs = []
    try:
        rows = []
        seen = set()
        expected = None
        for _ in range(40):
            query = {
                'LanguageCode': 'EN',
                'SearchParameters': {
                    'FirstItem': len(rows) + 1,
                    'CountItem': 25,
                    'MatchedObjectDescriptor': [
                        'ID', 'PositionID', 'PositionTitle', 'PositionURI',
                        'PositionLocation.CityName', 'PositionLocation.Country',
                        'PositionLocation.CountryName', 'PositionFormattedDescription.Content',
                        'PositionFormattedDescription.Intro', 'PositionFormattedDescription.Tasks',
                        'PositionFormattedDescription.Profile', 'PublicationStartDate'
                    ],
                },
                'SearchCriteria': [{'CriterionName': 'PositionFormattedDescription.Content', 'CriterionValue': [keyword]}] + extra,
            }
            payload = fetch(api_url + '?data=' + quote(json.dumps(query)))
            sr = payload.get('SearchResult') if isinstance(payload, dict) else None
            if not isinstance(sr, dict) or type(sr.get('SearchResultCountAll')) is not int:
                raise ValueError('Beesite search envelope invalid')
            total = sr['SearchResultCountAll']
            diag['pages_checked'] += 1
            diag['reported_total'] = total
            if expected is not None and total != expected:
                raise ValueError('Beesite total changed')
            expected = total
            if total == 0:
                diag.update(partial=False, verified_empty=True, verified_search=True, final_url=url)
                return [], diag
            batch = sr.get('SearchResultItems') or []
            if not isinstance(batch, list) or not batch:
                raise ValueError('Beesite premature end of results')
            for item in batch:
                desc_obj = item.get('MatchedObjectDescriptor') if isinstance(item, dict) else None
                jid = str((desc_obj or {}).get('ID') or (desc_obj or {}).get('PositionID') or '')
                if not jid or jid in seen:
                    raise ValueError('Beesite missing/repeated item ID')
                seen.add(jid)
                rows.append(desc_obj)
            if len(rows) >= total:
                break
        if len(rows) != expected:
            raise ValueError('Beesite incomplete results')
        for desc_obj in rows:
            title = desc_obj.get('PositionTitle') or ''
            uri = (desc_obj.get('PositionURI') or '').replace('jobsearch.daimlertruck.com//', 'jobsearch.daimlertruck.com/')
            locs = desc_obj.get('PositionLocation') or []
            if isinstance(locs, dict):
                locs = [locs]
            loc_parts = []
            for loc in locs:
                if isinstance(loc, dict):
                    loc_parts.append(', '.join(str(loc[k]) for k in ('CityName', 'CountryName', 'Country') if loc.get(k)))
            location = '; '.join(x for x in loc_parts if x) or 'Location unconfirmed'
            fmt = desc_obj.get('PositionFormattedDescription')
            if isinstance(fmt, list) and fmt:
                fmt = fmt[0]
            description = ''
            if isinstance(fmt, dict):
                description = strip(' '.join(str(fmt.get(k) or '') for k in ('Content', 'Intro', 'Tasks', 'Profile')))
            diag['details_checked'] += 1
            if not india(location):
                continue
            if not description:
                raise ValueError('Beesite India candidate missing description')
            if not related(title + ' ' + description):
                continue
            jobs.append({
                'title': title, 'company': company, 'url': uri or url, 'location': location,
                'description': description[:500], 'description_text': description,
                'description_complete': True, 'description_source_url': uri or api_url,
                'job_detail_status': 'read', 'source': 'Employer career page',
                'checked_at': checked_at, 'requisition_id': str(desc_obj.get('PositionID') or desc_obj.get('ID')),
                'posted_at': desc_obj.get('PublicationStartDate'), 'vacancy_scope': 'structured_job',
            })
        diag.update(partial=False, verified_search=True, final_url=url)
    except Exception as exc:
        diag['error'] = str(exc)[:250]
    return jobs, diag


def scrape_goldman_graphql(url, company, keyword, checked_at, fetch, strip, related, india):
    parsed = urlsplit(url)
    if (parsed.hostname or '').lower() != 'higher.gs.com':
        return [], {}
    api_url = 'https://api-higher.gs.com/gateway/api/v1/graphql'
    diag = {'goldman_graphql': True, 'method': 'goldman_higher_graphql', 'partial': True, 'pages_checked': 0, 'details_checked': 0}
    jobs = []
    search_query = '''query GetRoles($searchQueryInput: RoleSearchQueryInput!) {
      roleSearch(searchQueryInput: $searchQueryInput) {
        totalCount
        items {
          roleId
          jobTitle
          locations { state country city }
          externalSource { sourceId }
        }
      }
    }'''
    detail_query = '''query GetRoleById($externalSourceId: String!, $externalSourceFetch: Boolean) {
      role(externalSourceId: $externalSourceId, externalSourceFetch: $externalSourceFetch) {
        roleId
        jobTitle
        descriptionHtml
        locations { state country city }
      }
    }'''
    try:
        rows = []
        seen = set()
        expected = None
        for page_num in range(50):
            payload = fetch(api_url, payload={
                'operationName': 'GetRoles',
                'variables': {'searchQueryInput': {
                    'page': {'pageSize': 20, 'pageNumber': page_num},
                    'sort': {'sortStrategy': 'RELEVANCE', 'sortOrder': 'DESC'},
                    'filters': [], 'experiences': ['EARLY_CAREER', 'PROFESSIONAL'],
                    'searchTerm': keyword,
                }},
                'query': search_query,
            })
            rs = ((payload or {}).get('data') or {}).get('roleSearch')
            if not isinstance(rs, dict) or type(rs.get('totalCount')) is not int:
                raise ValueError('Goldman GraphQL search envelope invalid')
            total = rs['totalCount']
            diag['pages_checked'] += 1
            diag['reported_total'] = total
            if expected is not None and total != expected:
                raise ValueError('Goldman total changed')
            expected = total
            if total == 0:
                diag.update(partial=False, verified_empty=True, verified_search=True, final_url=url)
                return [], diag
            batch = rs.get('items') or []
            if not isinstance(batch, list) or not batch:
                raise ValueError('Goldman premature empty page')
            for item in batch:
                rid = str((item.get('externalSource') or {}).get('sourceId') or item.get('roleId') or '')
                if not rid or rid in seen:
                    raise ValueError('Goldman missing/repeated roleId')
                seen.add(rid)
                rows.append(item)
            if len(rows) >= total:
                break
        if len(rows) != expected:
            raise ValueError('Goldman incomplete results')
        for item in rows:
            sid = str((item.get('externalSource') or {}).get('sourceId') or '').strip()
            if not sid:
                raise ValueError('Goldman externalSourceId missing')
            d_payload = fetch(api_url, payload={
                'operationName': 'GetRoleById',
                'variables': {'externalSourceId': sid, 'externalSourceFetch': True},
                'query': detail_query,
            })
            role = ((d_payload or {}).get('data') or {}).get('role') or {}
            description = strip(role.get('descriptionHtml') or '')
            if not description:
                raise ValueError('Goldman role description missing')
            diag['details_checked'] += 1
            title = role.get('jobTitle') or item.get('jobTitle') or ''
            locs = role.get('locations') or item.get('locations') or []
            location = '; '.join(', '.join(str(loc[k]) for k in ('city', 'state', 'country') if loc.get(k)) for loc in locs if isinstance(loc, dict)) or 'Location unconfirmed'
            if not related(title + ' ' + description) or not india(location):
                continue
            public_url = f'https://higher.gs.com/roles/{sid}'
            jobs.append({
                'title': title, 'company': company, 'url': public_url, 'location': location,
                'description': description[:500], 'description_text': description,
                'description_complete': True, 'description_source_url': public_url,
                'job_detail_status': 'read', 'source': 'Employer career page',
                'checked_at': checked_at, 'requisition_id': sid, 'vacancy_scope': 'structured_job',
            })
        diag.update(partial=False, verified_search=True, final_url=url)
    except Exception as exc:
        diag['error'] = str(exc)[:250]
    return jobs, diag


def scrape_rollsroyce_api(url, company, keyword, checked_at, fetch, strip, related, india):
    parsed = urlsplit(url)
    if 'rolls-royce.com' not in (parsed.hostname or '').lower():
        return [], {}
    diag = {'rollsroyce': True, 'method': 'rollsroyce_connectid_api', 'partial': True, 'pages_checked': 0, 'details_checked': 0}
    jobs = []
    try:
        tok_resp = fetch('https://rollsroyceats-prod-api.connectid.cloud/auth/gettoken')
        token = (tok_resp or {}).get('token')
        if not token:
            raise ValueError('Rolls-Royce auth token missing')
        import urllib.request
        from career_scraper import _SSL_CONTEXT
        rows = []
        seen = set()
        expected = None
        for page_num in range(1, 51):
            api_url = f'https://rollsroyceats-prod-api.connectid.cloud/api/jobs?page={page_num}&perPage=20&search={quote(keyword)}'
            req = urllib.request.Request(api_url, data=b'{}', headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}, method='POST')
            with urllib.request.urlopen(req, timeout=20, context=_SSL_CONTEXT) as resp:
                payload = json.loads(resp.read().decode('utf-8'))
            meta = (payload or {}).get('meta') or {}
            total = meta.get('totalCount')
            if type(total) is not int or total < 0:
                raise ValueError('Rolls-Royce totalCount missing')
            diag['pages_checked'] += 1
            diag['reported_total'] = total
            if expected is not None and total != expected:
                raise ValueError('Rolls-Royce total changed')
            expected = total
            if total == 0:
                diag.update(partial=False, verified_empty=True, verified_search=True, final_url=url)
                return [], diag
            batch = payload.get('jobs') or []
            if not isinstance(batch, list) or not batch:
                raise ValueError('Rolls-Royce premature empty page')
            for item in batch:
                jid = str(item.get('jobRequisitionId') or item.get('id') or '')
                if not jid or jid in seen:
                    raise ValueError('Rolls-Royce missing/repeated job ID')
                seen.add(jid)
                rows.append(item)
            if len(rows) >= total:
                break
        if len(rows) != expected:
            raise ValueError('Rolls-Royce incomplete results')
        for item in rows:
            description = strip(item.get('jobDescription') or '')
            if not description:
                raise ValueError('Rolls-Royce description missing')
            diag['details_checked'] += 1
            title = item.get('jobTitle') or ''
            location = item.get('primaryLocation') or ', '.join(str(item.get(k) or '') for k in ('primaryCity', 'primaryCountry') if item.get(k)) or 'Location unconfirmed'
            if not related(title + ' ' + description) or not india(location):
                continue
            jid = str(item.get('jobRequisitionId') or item.get('id'))
            public_url = item.get('applyUrl') or f'https://careers.rolls-royce.com/en/jobs?search={quote(jid)}'
            jobs.append({
                'title': title, 'company': company, 'url': public_url, 'location': location,
                'description': description[:500], 'description_text': description,
                'description_complete': True, 'description_source_url': public_url,
                'job_detail_status': 'read', 'source': 'Employer career page',
                'checked_at': checked_at, 'requisition_id': jid, 'vacancy_scope': 'structured_job',
            })
        diag.update(partial=False, verified_search=True, final_url=url)
    except Exception as exc:
        diag['error'] = str(exc)[:250]
    return jobs, diag


def scrape_slb_coveo(url, company, keyword, checked_at, fetch, strip, related, india):
    parsed = urlsplit(url)
    if 'careers.slb.com' not in (parsed.hostname or '').lower():
        return [], {}
    diag = {'slb_coveo': True, 'method': 'slb_coveo_api', 'partial': True, 'pages_checked': 0, 'details_checked': 0}
    jobs = []
    try:
        tok_resp = fetch('https://careers.slb.com/coveo/rest/token')
        token = (tok_resp or {}).get('token')
        if not token:
            raise ValueError('SLB Coveo token missing')
        import urllib.request
        from career_scraper import _SSL_CONTEXT
        api_url = 'https://schlumbergerproduction0cs2zrh7.org.coveo.com/rest/search/v2?organizationId=schlumbergerproduction0cs2zrh7'
        rows = []
        seen = set()
        expected = None
        for _ in range(50):
            body = json.dumps({'q': keyword, 'cq': '@source=="ATS_Jobs_Source - Prod"', 'numberOfResults': 25, 'firstResult': len(rows)}).encode('utf-8')
            req = urllib.request.Request(api_url, data=body, headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}, method='POST')
            with urllib.request.urlopen(req, timeout=20, context=_SSL_CONTEXT) as resp:
                payload = json.loads(resp.read().decode('utf-8'))
            total = payload.get('totalCount')
            if type(total) is not int or total < 0:
                raise ValueError('SLB Coveo totalCount missing')
            diag['pages_checked'] += 1
            diag['reported_total'] = total
            if expected is not None and total != expected:
                raise ValueError('SLB Coveo total changed')
            expected = total
            if total == 0:
                diag.update(partial=False, verified_empty=True, verified_search=True, final_url=url)
                return [], diag
            batch = payload.get('results') or []
            if not isinstance(batch, list) or not batch:
                raise ValueError('SLB Coveo premature empty page')
            for item in batch:
                uid = str(item.get('uniqueId') or item.get('clickUri') or '')
                if not uid or uid in seen:
                    raise ValueError('SLB Coveo missing/repeated ID')
                seen.add(uid)
                rows.append(item)
            if len(rows) >= total:
                break
        if len(rows) != expected:
            raise ValueError('SLB Coveo incomplete results')
        for item in rows:
            raw = item.get('raw') or {}
            description = strip(str(raw.get('description') or item.get('excerpt') or ''))
            if not description:
                raise ValueError('SLB Coveo description missing')
            diag['details_checked'] += 1
            title = item.get('title') or ''
            countries = raw.get('country') or []
            if isinstance(countries, str):
                countries = [countries]
            loc_str = ', '.join(str(x) for x in [raw.get('location') or raw.get('city') or '', *countries] if x) or 'Location unconfirmed'
            if not related(title + ' ' + description) or not india(loc_str):
                continue
            click_url = item.get('clickUri') or url
            jobs.append({
                'title': title, 'company': company, 'url': click_url, 'location': loc_str,
                'description': description[:500], 'description_text': description,
                'description_complete': True, 'description_source_url': click_url,
                'job_detail_status': 'read', 'source': 'Employer career page',
                'checked_at': checked_at, 'requisition_id': str(raw.get('permanentid') or ''),
                'vacancy_scope': 'structured_job',
            })
        diag.update(partial=False, verified_search=True, final_url=url)
    except Exception as exc:
        diag['error'] = str(exc)[:250]
    return jobs, diag


def scrape_smartrecruiters_api(url, company, keyword, checked_at, fetch, strip, related, india):
    parsed = urlsplit(url)
    host = (parsed.hostname or '').lower()
    slug_map = {
        'jobs.bosch.com': 'BoschGroup',
        'www.bosch.in': 'BoschGroup',
        'www.telekom.com': 'DeutscheTelekom',
        'careers.telekom.com': 'DeutscheTelekom',
        'www.se.com': 'SchneiderElectric2',
        'careers.se.com': 'SchneiderElectric2',
        'usa.visa.com': 'Visa',
        'jobs.smartrecruiters.com': 'Visa' if '/Visa' in parsed.path else None,
    }
    slug = slug_map.get(host)
    if not slug:
        return [], {}
    diag = {'smartrecruiters': True, 'method': 'smartrecruiters_public_api', 'company_slug': slug, 'partial': True, 'pages_checked': 0, 'details_checked': 0}
    jobs = []
    try:
        rows = []
        seen = set()
        expected = None
        for _ in range(50):
            api_url = f'https://api.smartrecruiters.com/v1/companies/{slug}/postings?' + urlencode({'q': keyword, 'limit': 100, 'offset': len(rows)})
            payload = fetch(api_url)
            total = (payload or {}).get('totalFound')
            if type(total) is not int or total < 0:
                raise ValueError('SmartRecruiters totalFound missing')
            diag['pages_checked'] += 1
            diag['reported_total'] = total
            if expected is not None and total != expected:
                raise ValueError('SmartRecruiters total changed')
            expected = total
            if total == 0:
                diag.update(partial=False, verified_empty=True, verified_search=True, final_url=api_url)
                return [], diag
            batch = payload.get('content') or []
            if not isinstance(batch, list) or not batch:
                raise ValueError('SmartRecruiters premature empty page')
            for item in batch:
                jid = str(item.get('id') or '')
                if not jid or jid in seen:
                    raise ValueError('SmartRecruiters missing/repeated ID')
                seen.add(jid)
                rows.append(item)
            if len(rows) >= total:
                break
        if len(rows) != expected:
            raise ValueError('SmartRecruiters incomplete results')
        for item in rows:
            jid = str(item['id'])
            detail = fetch(f'https://api.smartrecruiters.com/v1/companies/{slug}/postings/{jid}')
            sections = ((detail or {}).get('jobAd') or {}).get('sections') or {}
            description = strip(' '.join(str((sections.get(k) or {}).get('text') or '') for k in ('companyDescription', 'jobDescription', 'qualifications', 'additionalInformation')))
            if not description:
                raise ValueError('SmartRecruiters detail description missing')
            diag['details_checked'] += 1
            title = detail.get('name') or item.get('name') or ''
            loc_obj = detail.get('location') or item.get('location') or {}
            location = ', '.join(str(loc_obj.get(k) or '') for k in ('city', 'region', 'country') if loc_obj.get(k)) or 'Location unconfirmed'
            if not related(title + ' ' + description) or not (str(loc_obj.get('country') or '').lower() == 'in' or india(location)):
                continue
            public_url = detail.get('postingUrl') or f'https://jobs.smartrecruiters.com/{slug}/{jid}'
            jobs.append({
                'title': title, 'company': company, 'url': public_url, 'location': location,
                'description': description[:500], 'description_text': description,
                'description_complete': True, 'description_source_url': public_url,
                'job_detail_status': 'read', 'source': 'Employer career page',
                'checked_at': checked_at, 'requisition_id': str(detail.get('refNumber') or jid),
                'posted_at': detail.get('releasedDate'), 'vacancy_scope': 'structured_job',
            })
        diag.update(partial=False, verified_search=True, final_url=url)
    except Exception as exc:
        diag['error'] = str(exc)[:250]
    return jobs, diag


def scrape_embedded_zoho(page, company, keyword, checked_at, strip, related, india):
    if 'recruitment.itcportal.com' not in (urlsplit(page.url).hostname or '').lower():
        return [], {}
    soup = BeautifulSoup(page.content(), 'html.parser')
    jobs_el = soup.find('input', {'id': 'jobs'})
    if not jobs_el or not jobs_el.get('value'):
        return [], {}
    diag = {'zoho_recruit': True, 'method': 'zoho_embedded_json', 'partial': True, 'pages_checked': 1, 'details_checked': 0}
    jobs = []
    try:
        rows = json.loads(jobs_el['value'])
        if not isinstance(rows, list):
            raise ValueError('Zoho jobs payload not a list')
        diag['reported_total'] = len(rows)
        for item in rows:
            if not isinstance(item, dict) or not item.get('id'):
                raise ValueError('Zoho job item malformed')
            title = str(item.get('Posting_Title') or item.get('Job_Opening_Name') or '')
            description = strip(str(item.get('Job_Description') or ''))
            if not description:
                raise ValueError('Zoho job description missing')
            diag['details_checked'] += 1
            location = ', '.join(str(item.get(k) or '') for k in ('City', 'State', 'Country') if item.get(k)) or 'India'
            if not related(title + ' ' + description) or not india(location):
                continue
            jid = str(item['id'])
            slug = re.sub(r'[^\w]+', '-', title).strip('-')
            public_url = f'https://recruitment.itcportal.com/jobs/Careers/{jid}/{slug}?source=CareerSite'
            jobs.append({
                'title': title, 'company': company, 'url': public_url, 'location': location,
                'description': description[:500], 'description_text': description,
                'description_complete': True, 'description_source_url': page.url,
                'job_detail_status': 'read', 'source': 'Employer career page',
                'checked_at': checked_at, 'requisition_id': jid, 'vacancy_scope': 'structured_job',
            })
        diag.update(partial=False, verified_search=True, verified_empty=len(jobs) == 0, final_url=page.url)
    except Exception as exc:
        diag['error'] = str(exc)[:250]
    return jobs, diag


def scrape_socgen_search(page, company, keyword, checked_at, navigate, extract):
    host = (urlsplit(page.url).hostname or '').lower()
    if 'careers.societegenerale.com' not in host:
        return [], {}
    target = f'https://{host}/en/search?' + urlencode({'query': keyword})
    diag = {'socgen': True, 'method': 'socgen_quantum_search', 'partial': True, 'pages_checked': 0, 'details_checked': 0}
    jobs = []
    try:
        navigate(page, target, timeout=25000)
        page.wait_for_function('() => { const el = document.querySelector(".jobs-count"); return el && (/\\d+\\s+jobs?/i.test(el.innerText) || /no results/i.test(el.innerText)); }', timeout=10000)
        soup = BeautifulSoup(page.content(), 'html.parser')
        count_el = soup.select_one('.jobs-count')
        if not count_el:
            raise ValueError('SocGen jobs-count element missing')
        count_text = count_el.get_text(' ', strip=True)
        diag['pages_checked'] = 1
        if re.search(r'no results for this search', count_text, re.I):
            diag.update(partial=False, verified_empty=True, verified_search=True, reported_total=0, final_url=page.url)
            return [], diag
        match = re.search(r'(\d+)\s+jobs?', count_text, re.I)
        if not match:
            raise ValueError('SocGen job count not parsed')
        total = int(match.group(1))
        diag['reported_total'] = total
        urls = list(dict.fromkeys(urljoin(page.url, a['href']) for a in soup.select('a[href*="/job-offers/"]') if urlsplit(urljoin(page.url, a['href'])).hostname == host))
        if len(urls) != total:
            raise ValueError('SocGen listing count mismatch')
        for url in urls:
            navigate(page, url, timeout=25000)
            page.wait_for_timeout(1200)
            postings = list(jsonld_jobs(page.content()))
            if not any(p.get('title') and p.get('description') for p in postings):
                raise ValueError('SocGen structured description missing')
            jobs.extend(extract(page, company, checked_at))
            diag['details_checked'] += 1
        diag.update(partial=False, verified_search=True, final_url=target)
    except Exception as exc:
        diag['error'] = str(exc)[:250]
    return jobs, diag


def scrape_novartis_drupal(page, company, keyword, checked_at, navigate, extract):
    host = (urlsplit(page.url).hostname or '').lower()
    if 'novartis.com' not in host:
        return [], {}
    target = f'https://{host}/careers/career-search?' + urlencode({'search_api_fulltext': keyword, 'field_job_posted_date': 'All', 'op': 'Submit'})
    diag = {'novartis': True, 'method': 'novartis_career_search', 'partial': True, 'pages_checked': 0, 'details_checked': 0}
    jobs = []
    try:
        navigate(page, target, timeout=25000)
        page.wait_for_timeout(1500)
        soup = BeautifulSoup(page.content(), 'html.parser')
        inp = soup.select_one('input[name="search_api_fulltext"]')
        if not inp or inp.get('value', '').casefold() != keyword.casefold():
            raise ValueError('Novartis keyword input not confirmed')
        header = soup.select_one('.view-header, .view-empty')
        text = (header.get_text(' ', strip=True) if header else '') + ' ' + soup.get_text(' ', strip=True)
        match = re.search(r'Showing\s+(\d+)\s+results', text, re.I)
        if not match:
            raise ValueError('Novartis result count not confirmed')
        total = int(match.group(1))
        diag['pages_checked'] = 1
        diag['reported_total'] = total
        urls = list(dict.fromkeys(urljoin(page.url, a['href']) for a in soup.select('a[href*="/careers/career-search/job/"]') if urlsplit(urljoin(page.url, a['href'])).hostname == host))
        if total == 0 and not urls:
            diag.update(partial=False, verified_empty=True, verified_search=True, final_url=page.url)
            return [], diag
        if len(urls) != total:
            raise ValueError('Novartis listing count incomplete')
        for url in urls:
            navigate(page, url, timeout=25000)
            postings = list(jsonld_jobs(page.content()))
            if not any(p.get('title') and p.get('description') for p in postings):
                raise ValueError('Novartis structured description missing')
            jobs.extend(extract(page, company, checked_at))
            diag['details_checked'] += 1
        diag.update(partial=False, verified_search=True, final_url=target)
    except Exception as exc:
        diag['error'] = str(exc)[:250]
    return jobs, diag


def scrape_bmw_jobfinder(page, company, keyword, checked_at, navigate, extract):
    host = (urlsplit(page.url).hostname or '').lower()
    if 'bmwgroup.jobs' not in host:
        return [], {}
    diag = {'bmw': True, 'method': 'bmw_jobfinder_table', 'partial': True, 'pages_checked': 0, 'details_checked': 0}
    jobs = []
    try:
        res = page.evaluate('''async (kw) => {
            const r = await fetch(`/en/_jcr_content/main/layoutcontainer_5337/jobfinder30.jobfinder_table.content.html?textSearch=${encodeURIComponent(kw)}&rowIndex=0&blockCount=50`);
            return {http: r.status, html: r.ok ? await r.text() : ''};
        }''', keyword)
        if res.get('http') != 200:
            raise ValueError('BMW jobfinder HTTP ' + str(res.get('http')))
        soup = BeautifulSoup(res['html'], 'html.parser')
        table = soup.select_one('.grp-jobfinder__table[data-counter]')
        if not table:
            raise ValueError('BMW jobfinder counter missing')
        total = int(table['data-counter'])
        diag['pages_checked'] = 1
        diag['reported_total'] = total
        if total == 0 and not soup.select('.grp-jobfinder__wrapper'):
            diag.update(partial=False, verified_empty=True, verified_search=True, final_url=page.url)
            return [], diag
        raise ValueError('BMW non-zero results require detail verification')
    except Exception as exc:
        diag['error'] = str(exc)[:250]
    return jobs, diag


def scrape_ubs_brassring(page, company, keyword, checked_at, navigate):
    host = (urlsplit(page.url).hostname or '').lower()
    if 'ubs.com' not in host:
        return [], {}
    target = 'https://jobs.ubs.com/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25008&siteid=5012&PageType=searchResults&SearchType=linkquery&LinkID=15709'
    diag = {'ubs_brassring': True, 'method': 'ubs_brassring_ajax', 'partial': True, 'pages_checked': 0, 'details_checked': 0}
    try:
        matched_responses = []
        def on_resp(resp):
            if '/Search/Ajax/MatchedJobs' in resp.url and resp.status == 200:
                try:
                    matched_responses.append({'post': resp.request.post_data or '', 'json': resp.json()})
                except Exception:
                    pass
        page.on('response', on_resp)
        navigate(page, target, timeout=25000)
        page.wait_for_timeout(2500)
        for btn_text in ('Agree to all', 'Agree', 'Accept all'):
            try:
                btn = page.locator(f'button:has-text("{btn_text}")').first
                if btn.is_visible():
                    btn.click(timeout=1500)
                    page.wait_for_timeout(1200)
                    break
            except Exception:
                pass
        inp = page.locator('input[type="text"], input[placeholder*="keyword" i]').first
        inp.fill(keyword)
        inp.press('Enter')
        page.wait_for_timeout(3500)
        if not matched_responses:
            raise ValueError('UBS MatchedJobs AJAX not observed')
        last = matched_responses[-1]
        post_data = json.loads(last['post']) if last['post'] else {}
        if str(post_data.get('Keyword') or '').casefold() != keyword.casefold():
            raise ValueError('UBS MatchedJobs keyword mismatch')
        payload = last['json']
        total = payload.get('TotalJobsCount')
        if type(total) is not int or total < 0:
            raise ValueError('UBS TotalJobsCount invalid')
        diag['pages_checked'] = 1
        diag['reported_total'] = total
        job_list = ((payload.get('Jobs') or {}).get('Job')) or []
        if total == 0 and not job_list:
            diag.update(partial=False, verified_empty=True, verified_search=True, final_url=page.url)
            return [], diag
        raise ValueError('UBS non-zero BrassRing results require detail extraction')
    except Exception as exc:
        diag['error'] = str(exc)[:250]
    return [], diag


def scrape_pega_drupal(page, company, keyword, checked_at, navigate, strip, related, india):
    host = (urlsplit(page.url).hostname or '').lower()
    if 'pega.com' not in host:
        return [], {}
    target = f'https://{host}/about/careers/job-listings?' + urlencode({'q': keyword})
    diag = {'pega_drupal': True, 'method': 'pega_bolt_listings', 'partial': True, 'pages_checked': 0, 'details_checked': 0}
    jobs = []
    try:
        navigate(page, target, timeout=25000)
        page.wait_for_timeout(1500)
        soup0 = BeautifulSoup(page.content(), 'html.parser')
        inp = soup0.select_one('input[name="q"]')
        if not inp or inp.get('value', '').casefold() != keyword.casefold():
            raise ValueError('Pegasystems keyword input not confirmed')
        m = re.search(r'Showing\s+(\d+)\s+results', soup0.get_text(' ', strip=True), re.I)
        if not m:
            raise ValueError('Pegasystems result total missing')
        total = int(m.group(1))
        diag['reported_total'] = total
        if total == 0:
            diag.update(partial=False, verified_empty=True, verified_search=True, pages_checked=1, final_url=page.url)
            return [], diag
        num_pages = (total + 29) // 30
        pages_data = page.evaluate('''async ({kw, count}) => {
            const out = [];
            for (let pg = 0; pg < count; pg++) {
                const r = await fetch(`/about/careers/job-listings?q=${encodeURIComponent(kw)}&page=${pg}`, {credentials: 'same-origin'});
                out.push({pg, status: r.status, html: r.ok ? await r.text() : ''});
            }
            return out;
        }''', {'kw': keyword, 'count': min(num_pages, 10)})
        cards = []
        seen = set()
        last_cards = 0
        for pitem in pages_data:
            if pitem.get('status') != 200:
                raise ValueError('Pegasystems page fetch failed')
            diag['pages_checked'] += 1
            psoup = BeautifulSoup(pitem['html'], 'html.parser')
            page_cards = 0
            for c in psoup.select('bolt-card-replacement[url^="/about/careers/"]'):
                u = c.get('url') or ''
                if not re.match(r'^/about/careers/\d+/', u):
                    continue
                if u in seen:
                    raise ValueError('Pegasystems repeated card URL')
                seen.add(u)
                cards.append((u, c.get_text(' ', strip=True)))
                page_cards += 1
            last_cards = page_cards
        if not (len(cards) == total or (diag['pages_checked'] == num_pages and 0 < last_cards < 30 and total - 2 <= len(cards) <= total)):
            raise ValueError(f'Pegasystems card count {len(cards)} != reported {total}')
        is_india = lambda text: bool(re.search(r'\b(India|Bengaluru|Bangalore|Hyderabad|Pune|Chennai|Mumbai|Delhi|Gurgaon|Gurugram|Noida|Kolkata|Kochi)\b', text or '', re.I))
        candidate_urls = []
        for u, card_text in cards:
            loc_m = re.search(r'Location:\s*(.+)$', card_text)
            loc_hint = loc_m.group(1).strip() if loc_m else card_text
            if is_india(loc_hint) or 'other location' in loc_hint.lower():
                candidate_urls.append(u)
            else:
                diag['details_checked'] += 1
        details = page.evaluate('''async (urls) => {
            const out = [];
            for (let i = 0; i < urls.length; i += 6) {
                const batch = urls.slice(i, i + 6);
                const res = await Promise.all(batch.map(async u => {
                    const r = await fetch(u, {credentials: 'same-origin'});
                    return {url: u, status: r.status, html: r.ok ? await r.text() : ''};
                }));
                out.push(...res);
            }
            return out;
        }''', candidate_urls)
        for ditem in details:
            if ditem.get('status') != 200:
                raise ValueError('Pegasystems detail fetch failed')
            dsoup = BeautifulSoup(ditem['html'], 'html.parser')
            h1 = dsoup.select_one('h1')
            article = dsoup.select_one('article, main')
            if not h1 or not article:
                raise ValueError('Pegasystems detail structure missing')
            title = h1.get_text(' ', strip=True)
            description = strip(article.get_text(' ', strip=True))
            if not title or not description:
                raise ValueError('Pegasystems detail empty')
            diag['details_checked'] += 1
            loc_m = re.search(r'Location:\s*([^\n]+?)(?:\s+Apply now|\s+Share(?:\s+this\s+page)?|\s+Meet Our Team|$)', description)
            location = loc_m.group(1).strip() if loc_m else 'Location unconfirmed'
            if not related(title + ' ' + description) or not is_india(location):
                continue
            jid_m = re.match(r'^/about/careers/(\d+)/', ditem['url'])
            public_url = urljoin(f'https://{host}', ditem['url'])
            jobs.append({
                'title': title, 'company': company, 'url': public_url, 'location': location,
                'description': description[:500], 'description_text': description,
                'description_complete': True, 'description_source_url': public_url,
                'job_detail_status': 'read', 'source': 'Employer career page',
                'checked_at': checked_at, 'requisition_id': jid_m.group(1) if jid_m else None,
                'vacancy_scope': 'structured_job',
            })
        diag.update(partial=False, verified_search=True, final_url=target)
    except Exception as exc:
        diag['error'] = str(exc)[:250]
    return jobs, diag


def scrape_walmart_graphql(page, company, keyword, checked_at, navigate):
    host = (urlsplit(page.url).hostname or '').lower()
    if 'careers.walmart.com' not in host:
        return [], {}
    target = 'https://careers.walmart.com/us/en/results?' + urlencode({'searchQuery': keyword})
    diag = {'walmart': True, 'method': 'walmart_hybrid_graphql', 'partial': True, 'pages_checked': 0, 'details_checked': 0}
    try:
        tool_Payloads = []
        def on_resp(resp):
            if '/api/graphql' in resp.url and resp.status == 200:
                try:
                    j = resp.json()
                    assistant = ((j.get('data') or {}).get('jobSearchAssistant')) or {}
                    for tm in assistant.get('tool_messages') or []:
                        if tm.get('name') == 'combined_hybrid_search_tool' and tm.get('content'):
                            tool_Payloads.append(json.loads(tm['content']))
                except Exception:
                    pass
        page.on('response', on_resp)
        navigate(page, target, timeout=25000)
        for _ in range(16):
            if tool_Payloads:
                break
            page.wait_for_timeout(500)
        if not tool_Payloads:
            body_text = page.locator('body').first.inner_text()
            if re.search(r'\b0\s+open\s+roles\b', body_text, re.I) and re.search(r'\b0\s+results\b', body_text, re.I):
                diag.update(partial=False, verified_empty=True, verified_search=True, pages_checked=1, reported_total=0, final_url=page.url)
                return [], diag
            raise ValueError('Walmart hybrid search tool response not observed')
        latest = tool_Payloads[-1]
        total = latest.get('total_jobs')
        if type(total) is not int or total < 0 or keyword.casefold() not in str(latest.get('refined_query') or '').casefold():
            raise ValueError('Walmart hybrid search query/total not confirmed')
        diag['pages_checked'] = 1
        diag['reported_total'] = total
        if total == 0:
            diag.update(partial=False, verified_empty=True, verified_search=True, final_url=page.url)
            return [], diag
        raise ValueError('Walmart non-zero results require detail extraction')
    except Exception as exc:
        diag['error'] = str(exc)[:250]
    return [], diag


def scrape_icici_portal(page, company, keyword, checked_at, navigate, strip, related, india):
    host = (urlsplit(page.url).hostname or '').lower()
    if 'careers.icici.bank.in' not in host:
        return [], {}
    target = 'https://careers.icici.bank.in/CareerApplicant/Career/job-listing/'
    diag = {'icici': True, 'method': 'icici_portal_search', 'partial': True, 'pages_checked': 0, 'details_checked': 0}
    try:
        if page.url != target:
            navigate(page, target, timeout=25000)
        page.wait_for_timeout(2500)
        inps = page.locator('input[name="search"]')
        filled = False
        for idx in range(inps.count()):
            el = inps.nth(idx)
            if el.is_visible():
                el.fill(keyword)
                page.wait_for_timeout(1500)
                filled = True
                break
        if not filled:
            raise ValueError('ICICI search input not visible')
        sugg = page.evaluate('() => Array.from(document.querySelectorAll("[id*=\\"react-autowhatever\\"]")).map(e => e.innerText.trim()).filter(Boolean)')
        diag['pages_checked'] = 1
        if any(s.lower() == 'no job found' for s in sugg):
            diag.update(partial=False, verified_empty=True, verified_search=True, reported_total=0, final_url=page.url)
            return [], diag
        raise ValueError('ICICI returned suggestions requiring detail check')
    except Exception as exc:
        diag['error'] = str(exc)[:250]
    return [], diag


def scrape_eaton_eightfold(url, company, keyword, checked_at, fetch, strip, related, india):
    parsed = urlsplit(url)
    if 'eaton.com' not in (parsed.hostname or '').lower() and 'eaton.eightfold.ai' not in (parsed.hostname or '').lower():
        return [], {}
    origin = 'https://eaton.eightfold.ai'
    diag = {'eightfold': True, 'method': 'eightfold_eaton_api', 'partial': True, 'pages_checked': 0, 'details_checked': 0}
    jobs = []
    try:
        rows = []
        seen = set()
        expected = None
        for _ in range(20):
            payload = fetch(origin + '/api/pcsx/search?' + urlencode({'domain': 'eaton.com', 'query': keyword, 'location': '', 'start': len(rows)}))
            if (payload or {}).get('status') != 200 or not isinstance((payload or {}).get('data'), dict):
                raise ValueError('Eaton Eightfold search failed')
            data = payload['data']
            total = data.get('count')
            batch = data.get('positions') or []
            if type(total) is not int or total < 0:
                raise ValueError('Eaton Eightfold count invalid')
            diag['pages_checked'] += 1
            diag['reported_total'] = total
            if expected is not None and total != expected:
                raise ValueError('Eaton Eightfold total changed')
            expected = total
            if total == 0:
                diag.update(partial=False, verified_empty=True, verified_search=True, final_url=origin + '/careers')
                return [], diag
            if not batch:
                raise ValueError('Eaton Eightfold premature empty page')
            for r in batch:
                jid = str(r.get('id') or '')
                if not jid or jid in seen:
                    raise ValueError('Eaton Eightfold repeated ID')
                seen.add(jid)
                rows.append(r)
            if len(rows) >= total:
                break
        if len(rows) != expected:
            raise ValueError('Eaton Eightfold incomplete results')
        for r in rows:
            loc_str = ', '.join(str(x) for x in (r.get('locations') or []))
            if not india(loc_str):
                diag['details_checked'] += 1
                continue
            d_payload = fetch(origin + '/api/pcsx/position_details?' + urlencode({'domain': 'eaton.com', 'position_id': r['id'], 'hl': 'en'}))
            d = (d_payload or {}).get('data') or {}
            description = strip(d.get('jobDescription') or '')
            if not description:
                raise ValueError('Eaton Eightfold detail missing')
            diag['details_checked'] += 1
            title = d.get('name') or r.get('name') or ''
            if not related(title + ' ' + description):
                continue
            public_url = urljoin(origin, r.get('positionUrl') or d.get('positionUrl') or f'/careers/job/{r["id"]}')
            jobs.append({
                'title': title, 'company': company, 'url': public_url, 'location': loc_str,
                'description': description[:500], 'description_text': description,
                'description_complete': True, 'description_source_url': public_url,
                'job_detail_status': 'read', 'source': 'Employer career page',
                'checked_at': checked_at, 'requisition_id': str(d.get('displayJobId') or r['id']),
                'vacancy_scope': 'structured_job',
            })
        diag.update(partial=False, verified_search=True, final_url=origin + '/careers')
    except Exception as exc:
        diag['error'] = str(exc)[:250]
    return jobs, diag


def scrape_medtronic_workday(url, company, keyword, checked_at, fetch, strip, related, india):
    parsed = urlsplit(url)
    if 'medtronic.eightfold.ai' not in (parsed.hostname or '').lower():
        return [], {}
    api_url = 'https://medtronic.wd1.myworkdayjobs.com/wday/cxs/medtronic/MedtronicCareers/jobs'
    diag = {'workday': True, 'method': 'workday_cxs', 'partial': True, 'pages_checked': 0, 'details_checked': 0}
    try:
        res_pega = fetch(api_url, payload={'appliedFacets': {'locationCountry': ['c4f78be1a8f14da0ab49ce1162348a5e']}, 'limit': 20, 'offset': 0, 'searchText': keyword})
        res_prpc = fetch(api_url, payload={'appliedFacets': {'locationCountry': ['c4f78be1a8f14da0ab49ce1162348a5e']}, 'limit': 20, 'offset': 0, 'searchText': 'PRPC'})
        if not isinstance(res_pega, dict) or not isinstance(res_prpc, dict):
            raise ValueError('Medtronic Workday response invalid')
        diag['pages_checked'] = 2
        diag['reported_total'] = res_prpc.get('total', 0)
        if res_prpc.get('total') == 0 and not any(related(str(p.get('title') or '')) for p in (res_pega.get('jobPostings') or [])):
            diag.update(partial=False, verified_empty=True, verified_search=True, final_url='https://medtronic.wd1.myworkdayjobs.com/MedtronicCareers')
            return [], diag
        raise ValueError('Medtronic Workday returned candidate matches requiring detail inspection')
    except Exception as exc:
        diag['error'] = str(exc)[:250]
    return [], diag


def scrape_stellantis_mcloud(url, company, keyword, checked_at, fetch, strip, related, india):
    parsed = urlsplit(url)
    if 'stellantis.com' not in (parsed.hostname or '').lower():
        return [], {}
    api_url = 'https://jobsapi-google.m-cloud.io/api/job/search?' + urlencode({
        'pageSize': 20, 'offset': 0,
        'companyName': 'companies/16115603-6c1b-4c45-b544-238a4e6c51b3',
        'query': keyword, 'orderBy': 'relevance desc', 'queryLanguageCode': 'en-US',
    })
    diag = {'stellantis_mcloud': True, 'method': 'stellantis_mcloud_api', 'partial': True, 'pages_checked': 0, 'details_checked': 0}
    try:
        payload = fetch(api_url)
        total = (payload or {}).get('totalHits')
        if type(total) is not int or total < 0:
            raise ValueError('Stellantis m-cloud totalHits invalid')
        diag['pages_checked'] = 1
        diag['reported_total'] = total
        if total == 0 and not (payload.get('searchResults') or []):
            diag.update(partial=False, verified_empty=True, verified_search=True, final_url='https://careers.stellantis.com/job-search-results/?keyword=' + quote(keyword))
            return [], diag
        raise ValueError('Stellantis m-cloud returned non-zero results requiring detail extraction')
    except Exception as exc:
        diag['error'] = str(exc)[:250]
    return [], diag


def scrape_ashby_api(url, company, keyword, checked_at, fetch, strip, related, india):
    parsed = urlsplit(url)
    host = (parsed.hostname or '').lower()
    parts = [p for p in parsed.path.split('/') if p]
    if 'ashbyhq.com' not in host or not parts:
        return [], {}
    slug = parts[-1] if parts[0] in ('posting-api', 'job-board') else parts[0]
    api_url = f'https://api.ashbyhq.com/posting-api/job-board/{quote(slug, safe="")}?includeCompensation=true'
    diag = {'ashby': True, 'method': 'ashby_public_api', 'board': slug, 'partial': True, 'pages_checked': 0, 'details_checked': 0}
    jobs = []
    try:
        payload = fetch(api_url)
        postings = (payload or {}).get('jobs')
        if not isinstance(postings, list):
            raise ValueError('Ashby response jobs list missing')
        diag['pages_checked'] = 1
        diag['reported_total'] = len(postings)
        for p in postings:
            if not isinstance(p, dict):
                continue
            title = str(p.get('title') or '')
            description = strip(str(p.get('descriptionPlain') or p.get('descriptionHtml') or ''))
            if not description:
                raise ValueError('Ashby posting description missing')
            diag['details_checked'] += 1
            loc_str = str(p.get('location') or '')
            if not related(title + ' ' + description) or not india(loc_str):
                continue
            public_url = p.get('jobUrl') or f'https://jobs.ashbyhq.com/{slug}/{p.get("id")}'
            jobs.append({
                'title': title, 'company': company, 'url': public_url, 'location': loc_str or 'India',
                'description': description[:500], 'description_text': description,
                'description_complete': True, 'description_source_url': api_url,
                'job_detail_status': 'read', 'source': 'Employer career page',
                'checked_at': checked_at, 'requisition_id': str(p.get('id') or ''),
                'posted_at': p.get('publishedAt'), 'vacancy_scope': 'structured_job',
            })
        diag.update(partial=False, verified_search=True, verified_empty=len(postings) == 0, final_url=url)
    except Exception as exc:
        diag['error'] = str(exc)[:250]
    return jobs, diag
