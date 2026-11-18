"""Career portals with public JSON feeds: SmartRecruiters, Ashby, Eightfold, iCIMS (Jibe) and BeeSite.

None of these endpoints could be called while this was written (development is offline), so
each family notes what the 15 November 2026 captures confirm and what is assumed from the
platform's public contract. Every assumed field is read defensively: an answer that does not
have the expected envelope is `error` ("unexpected response shape"), a posting without an id is
ignored, and a detail that cannot be read is counted as unread (`partial`).

SmartRecruiters — CONFIRMED by captures (BoschGroup, DeutscheTelekom, SchneiderElectric2, Visa):
  GET https://api.smartrecruiters.com/v1/companies/{company_id}/postings?q=pega&limit=100&offset=0
  answers {"offset", "limit", "totalFound", "content": []}. ASSUMED (public Posting API docs):
  content rows {id, name, refNumber, releasedDate, location{city, region, country (ISO, lower
  case), remote}, department{label}, typeOfEmployment{label}}; detail
  GET .../postings/{id} -> {jobAd{sections{companyDescription, jobDescription, qualifications,
  additionalInformation}{text}}, postingUrl, applyUrl}; an unknown company answers totalFound 0,
  which the broad query (no q) exposes as a wrong company id.

Ashby — CONFIRMED: jobs.ashbyhq.com/{org} embeds window.__appData with organization
  .hostedJobsPageSlug == org (Confluent). ASSUMED (public posting API docs):
  GET https://api.ashbyhq.com/posting-api/job-board/{org} -> {"jobs": [{id, title, location,
  secondaryLocations[{location}], address{postalAddress{addressCountry}}, isListed, publishedAt,
  jobUrl, applyUrl, descriptionPlain|descriptionHtml, department, team, employmentType}]}.
  The whole board is one feed (no search), descriptions included.

Eightfold — CONFIRMED: tenant pages are PCSX career sites and name their group domain in
  `window._EF_GROUP_ID` (eaton.com, nab.com.au, amdocs.com, astrazeneca.com). ASSUMED (endpoints
  the employers' own pages called, recorded in the research; not re-validated):
  PCSX  GET https://{host}/api/pcsx/search?domain=D&query=pega&location=&start=N
        -> {status: 200, data: {positions: [...], count}}; detail
        GET /api/pcsx/position_details?domain=D&position_id=ID&hl=en -> {status: 200,
        data: {jobDescription, name, locations, positionUrl, displayJobId}}
  v2    GET https://{host}/api/apply/v2/jobs?domain=D&query=pega&start=N&num=10
        -> {positions: [...], count}; detail GET /api/apply/v2/jobs/{id}?domain=D -> {job_description}
  If either API needs a browser session the answer is a refusal and is reported as `blocked`.

iCIMS — CONFIRMED: jobs.booking.com, careers.axa.com, careers.international.com and
  pepsicojobs.com are iCIMS Jibe career sites (`data-jibe-search-version`, `window._jibe.cid`,
  job cards configured with `req_id`). ASSUMED (Jibe search API used by those pages):
  GET https://{host}/api/jobs?keywords=pega&page=1&limit=100 -> {"jobs": [{"data": {slug,
  req_id, title, description (HTML), city, state, country, country_code, location_name,
  full_location, additional_locations, posted_date, apply_url, categories}}], "totalCount": N}.
  Classic iCIMS iframe portals (careers-*.icims.com/jobs/search) are not covered.

BeeSite (milch & zucker) — CONFIRMED: jobsearch.daimlertruck.com is a BeeSite job board whose
  search form filters `PublicationChannel.Code` = 12 and searches `PositionFormattedDescription
  .Content`. ASSUMED (the research's earlier adapter): GET {api}?data=<JSON query> answers
  {"SearchResult": {"SearchResultCountAll": N, "SearchResultItems": [{"MatchedObjectDescriptor":
  {ID, PositionID, PositionTitle, PositionURI, PositionLocation[{CityName, CountryName, Country}],
  PositionFormattedDescription[{Content}], PublicationStartDate}}]}}.
"""
from __future__ import annotations

import json
import urllib.parse

from ..model import is_india
from . import records
from .portal_base import Family, Page, integer, json_get, plain, problem_of, text, when

SR_PAGE = 100
EIGHTFOLD_PAGE = 10
JIBE_PAGE = 100
BEESITE_PAGE = 25


def _q(value):
    return urllib.parse.quote(str(value), safe='')


def _https_host(value):
    """The bare host of a configured `host`, tolerating a pasted URL; '' when unusable."""
    value = str(value or '').strip()
    if '://' in value:
        value = urllib.parse.urlsplit(value).hostname or ''
    return value.strip('/').lower()


# ───────────────────────────── SmartRecruiters ─────────────────────────────

class SmartRecruiters(Family):
    kind = 'smartrecruiters'

    def identity(self, portal):
        return str(portal['company_id'])

    def _base(self, portal):
        return f"https://api.smartrecruiters.com/v1/companies/{_q(portal['company_id'])}/postings"

    def search(self, http, portal, query, cursor):
        offset = cursor or 0
        params = {'limit': SR_PAGE, 'offset': offset}
        if query:
            params = {'q': query, **params}
        data, response = json_get(http, self._base(portal) + '?' + urllib.parse.urlencode(params))
        if not isinstance(data, dict) or not isinstance(data.get('content'), list) or \
                integer(data.get('totalFound')) is None:
            return None, problem_of(response)
        total = integer(data['totalFound'])
        rows = [self._row(portal, item) for item in records(data['content'])]
        rows = [row for row in rows if row]
        return Page(rows, total, offset + SR_PAGE if offset + SR_PAGE < total else None), None

    def _row(self, portal, item):
        identifier = text(item.get('id'))
        if not identifier:
            return None
        place = item.get('location') if isinstance(item.get('location'), dict) else {}
        parts = [text(place.get(key)) for key in ('city', 'region')]
        country = text(place.get('country')).upper()
        location = ', '.join(part for part in parts if part)
        if place.get('remote') is True:
            location = (location + ' (remote)').strip()
        department = item.get('department') if isinstance(item.get('department'), dict) else {}
        employment = item.get('typeOfEmployment') if isinstance(item.get('typeOfEmployment'), dict) else {}
        return {'id': identifier, 'title': text(item.get('name')), 'location': location or country,
                'country_code': country if len(country) == 2 else '', 'posted': when(item.get('releasedDate')),
                'requisition': text(item.get('refNumber')) or identifier, 'unit': text(department.get('label')),
                'employment_type': text(employment.get('label')), 'description': '',
                'url': f"https://jobs.smartrecruiters.com/{_q(portal['company_id'])}/{_q(identifier)}"}

    def detail(self, http, portal, row):
        data, _ = json_get(http, f"{self._base(portal)}/{_q(row['id'])}")
        ad = data.get('jobAd') if isinstance(data, dict) else None
        sections = ad.get('sections') if isinstance(ad, dict) else None
        if not isinstance(sections, dict):
            return None
        parts = [plain(section.get('text')) for key in ('jobDescription', 'qualifications', 'additionalInformation',
                                                       'companyDescription')
                 for section in [sections.get(key)] if isinstance(section, dict)]
        description = '\n'.join(part for part in parts if part)
        if not description:
            return None
        learnt = {'description': description, 'url': text(data.get('postingUrl')),
                  'apply_url': text(data.get('applyUrl'))}
        if isinstance(data.get('location'), dict):
            learnt.update({key: value for key, value in self._row(portal, {**data, 'id': row['id']}).items()
                           if key in ('location', 'country_code') and value})
        return learnt


# ───────────────────────────── Ashby ─────────────────────────────

class Ashby(Family):
    kind = 'ashby'
    queries = (None,)

    def identity(self, portal):
        return str(portal['org'])

    def search(self, http, portal, query, cursor):
        url = f"https://api.ashbyhq.com/posting-api/job-board/{_q(portal['org'])}?includeCompensation=false"
        data, response = json_get(http, url)
        if not isinstance(data, dict) or not isinstance(data.get('jobs'), list):
            return None, problem_of(response)
        rows = [self._row(portal, item) for item in records(data['jobs']) if item.get('isListed') is not False]
        rows = [row for row in rows if row]
        return Page(rows, len(rows), None), None

    def _row(self, portal, item):
        identifier = text(item.get('id'))
        if not identifier:
            return None
        places = [text(item.get('location'))]
        places += [text(extra.get('location')) for extra in records(item.get('secondaryLocations') or [])]
        address = item.get('address') if isinstance(item.get('address'), dict) else {}
        postal = address.get('postalAddress') if isinstance(address.get('postalAddress'), dict) else {}
        country = text(postal.get('addressCountry'))
        if country and not any(country.lower() in place.lower() for place in places if place):
            places.append(country)
        description = text(item.get('descriptionPlain')) or plain(item.get('descriptionHtml'))
        return {'id': identifier, 'title': text(item.get('title')),
                'location': ' · '.join(dict.fromkeys(place for place in places if place)),
                'posted': when(item.get('publishedAt')), 'requisition': identifier,
                'unit': text(item.get('department')) or text(item.get('team')),
                'employment_type': text(item.get('employmentType')), 'description': description,
                'apply_url': text(item.get('applyUrl')),
                'url': text(item.get('jobUrl')) or f"https://jobs.ashbyhq.com/{_q(portal['org'])}/{_q(identifier)}"}


# ───────────────────────────── Eightfold ─────────────────────────────

class Eightfold(Family):
    kind = 'eightfold'
    queries = ('pega',)          # the search is semantic; a PRPC query only repeats it
    page_cap = 300

    def identity(self, portal):
        return _https_host(portal['host'])

    def _v2(self, portal):
        return str(portal.get('api') or 'pcsx').lower() == 'v2'

    def search(self, http, portal, query, cursor):
        origin = 'https://' + _https_host(portal['host'])
        start = cursor or 0
        if self._v2(portal):
            url = origin + '/api/apply/v2/jobs?' + urllib.parse.urlencode(
                {'domain': portal['domain'], 'query': query or '', 'start': start, 'num': EIGHTFOLD_PAGE})
        else:
            url = origin + '/api/pcsx/search?' + urllib.parse.urlencode(
                {'domain': portal['domain'], 'query': query or '', 'location': '', 'start': start})
        data, response = json_get(http, url)
        body = data
        if isinstance(data, dict) and not self._v2(portal):
            body = data.get('data') if data.get('status') in (200, '200', None) else None
        if not isinstance(body, dict) or not isinstance(body.get('positions'), list) or \
                integer(body.get('count')) is None:
            return None, problem_of(response)
        total = integer(body['count'])
        rows = [self._row(origin, item) for item in records(body['positions'])]
        rows = [row for row in rows if row]
        following = start + len(body['positions'])
        return Page(rows, total, following if body['positions'] and following < total else None), None

    def _row(self, origin, item):
        identifier = text(item.get('id'))
        if not identifier:
            return None
        places = item.get('locations') if isinstance(item.get('locations'), list) else []
        places = [text(place) for place in places] or [text(item.get('location'))]
        path = text(item.get('positionUrl')) or text(item.get('canonicalPositionUrl')) or f'/careers/job/{identifier}'
        url = path if path.startswith('https://') else origin + '/' + path.lstrip('/')
        return {'id': identifier, 'title': text(item.get('name')),
                'location': ' · '.join(dict.fromkeys(place for place in places if place)),
                'posted': when(item.get('postedTs') or item.get('t_create') or item.get('t_update')),
                'requisition': text(item.get('displayJobId') or item.get('display_job_id') or item.get('atsJobId'))
                or identifier,
                'unit': text(item.get('department')) or text(item.get('business_unit')),
                'description': plain(item.get('job_description')), 'url': url}

    def detail(self, http, portal, row):
        origin = 'https://' + _https_host(portal['host'])
        if self._v2(portal):
            data, _ = json_get(http, f"{origin}/api/apply/v2/jobs/{_q(row['id'])}?"
                               + urllib.parse.urlencode({'domain': portal['domain']}))
            body, field = data, 'job_description'
        else:
            data, _ = json_get(http, origin + '/api/pcsx/position_details?' + urllib.parse.urlencode(
                {'domain': portal['domain'], 'position_id': row['id'], 'hl': 'en'}))
            body = data.get('data') if isinstance(data, dict) and data.get('status') in (200, '200', None) else None
            field = 'jobDescription'
        if not isinstance(body, dict) or text(body.get('id')) not in ('', row['id']):
            return None
        description = plain(body.get(field))
        if not description:
            return None
        learnt = {'description': description}
        places = body.get('locations') if isinstance(body.get('locations'), list) else []
        if places:
            learnt['location'] = ' · '.join(dict.fromkeys(text(place) for place in places if text(place)))
        return learnt


# ───────────────────────────── iCIMS (Jibe career sites) ─────────────────────────────

class Icims(Family):
    kind = 'icims'

    def identity(self, portal):
        return _https_host(portal['host'])

    def search(self, http, portal, query, cursor):
        number = cursor or 1
        params = {'page': number, 'limit': JIBE_PAGE, 'sortBy': 'relevance'}
        if query:
            params = {'keywords': query, **params}
        url = f"https://{_https_host(portal['host'])}/api/jobs?" + urllib.parse.urlencode(params)
        data, response = json_get(http, url)
        if not isinstance(data, dict) or not isinstance(data.get('jobs'), list) or \
                integer(data.get('totalCount')) is None:
            return None, problem_of(response)
        total = integer(data['totalCount'])
        rows = [self._row(portal, item.get('data')) for item in records(data['jobs'])]
        rows = [row for row in rows if row]
        return Page(rows, total, number + 1 if number * JIBE_PAGE < total else None), None

    def _row(self, portal, item):
        if not isinstance(item, dict):
            return None
        identifier = text(item.get('req_id')) or text(item.get('slug'))
        if not identifier:
            return None
        places = [text(item.get('full_location')) or ', '.join(
            part for part in (text(item.get('city')), text(item.get('state')), text(item.get('country'))) if part)]
        for extra in records(item.get('additional_locations') or []):
            places.append(', '.join(part for part in (text(extra.get('city')), text(extra.get('state')),
                                                     text(extra.get('country'))) if part))
        categories = item.get('categories') if isinstance(item.get('categories'), list) else []
        unit = next((text(category.get('name')) for category in records(categories) if text(category.get('name'))), '')
        slug = text(item.get('slug')) or identifier
        prefix = str(portal.get('path') or '').strip('/')
        host = _https_host(portal['host'])
        code = text(item.get('country_code')).upper()
        return {'id': identifier, 'title': text(item.get('title')),
                'location': ' · '.join(dict.fromkeys(place for place in places if place)),
                'country_code': code if len(code) == 2 else '', 'posted': when(item.get('posted_date')),
                'requisition': text(item.get('req_id')) or identifier, 'unit': unit,
                'employment_type': text(item.get('employment_type')),
                'description': plain(item.get('description')), 'apply_url': text(item.get('apply_url')),
                'url': f"https://{host}/{prefix + '/' if prefix else ''}jobs/{_q(slug)}"}

    # A Jibe answer without a description leaves nothing better to read: the job page is
    # rendered by JavaScript from this same API. Such postings are judged by their title.


# ───────────────────────────── BeeSite ─────────────────────────────

class BeeSite(Family):
    kind = 'beesite'
    page_cap = 500

    def identity(self, portal):
        return _https_host(portal['api'])

    def search(self, http, portal, query, cursor):
        first = cursor or 1
        criteria = []
        if query:
            criteria.append({'CriterionName': 'PositionFormattedDescription.Content', 'CriterionValue': [query]})
        if portal.get('channel'):
            criteria.append({'CriterionName': 'PublicationChannel.Code', 'CriterionValue': [str(portal['channel'])]})
        payload = {'LanguageCode': 'EN', 'SearchParameters': {
            'FirstItem': first, 'CountItem': BEESITE_PAGE,
            'MatchedObjectDescriptor': ['ID', 'PositionID', 'PositionTitle', 'PositionURI', 'PositionLocation.CityName',
                                        'PositionLocation.Country', 'PositionLocation.CountryName',
                                        'PositionFormattedDescription.Content', 'PublicationStartDate',
                                        'OrganizationName']},
            'SearchCriteria': criteria}
        api = str(portal['api'])
        if not api.startswith('https://'):
            return None, ('error', 'the BeeSite api setting must be an https URL')
        url = api + ('&' if '?' in api else '?') + 'data=' + urllib.parse.quote(json.dumps(payload, separators=(',', ':')))
        data, response = json_get(http, url)
        found = data.get('SearchResult') if isinstance(data, dict) else None
        if not isinstance(found, dict) or integer(found.get('SearchResultCountAll')) is None or \
                not isinstance(found.get('SearchResultItems', []), list):
            return None, problem_of(response)
        total = integer(found['SearchResultCountAll'])
        items = records(found.get('SearchResultItems') or [])
        rows = [self._row(item.get('MatchedObjectDescriptor')) for item in items]
        rows = [row for row in rows if row]
        following = first + len(items)
        return Page(rows, total, following if items and following - 1 < total else None), None

    def board_notes(self, rows):
        # Shared boards (Mercedes-Benz) are split between employers by OrganizationName.
        if rows and not any(row.get('unit') for row in rows):
            return ['organisation missing; business-unit attribution unavailable']
        return []

    def _row(self, item):
        if not isinstance(item, dict):
            return None
        identifier = text(item.get('ID')) or text(item.get('PositionID'))
        if not identifier:
            return None
        places = item.get('PositionLocation')
        places = records([places] if isinstance(places, dict) else places or [])
        location = ' · '.join(dict.fromkeys(
            ', '.join(part for part in (text(place.get('CityName')), text(place.get('CountryName'))) if part)
            for place in places if text(place.get('CityName')) or text(place.get('CountryName'))))
        codes = {text(place.get('Country')).upper() for place in places} - {''}
        formatted = item.get('PositionFormattedDescription')
        formatted = records([formatted] if isinstance(formatted, dict) else formatted or [])
        description = '\n'.join(plain(part.get('Content')) for part in formatted if part.get('Content'))
        india = 'IN' in codes or is_india(location)
        return {'id': identifier, 'title': text(item.get('PositionTitle')), 'location': location,
                # Several sites: India decides when it is one of them; one foreign code decides otherwise.
                'country_code': 'IN' if india else (codes.pop() if len(codes) == 1 and len(next(iter(codes))) == 2
                                                     else ''),
                'posted': when(item.get('PublicationStartDate')),
                'requisition': text(item.get('PositionID')) or identifier, 'unit': text(item.get('OrganizationName')),
                'description': description, 'url': text(item.get('PositionURI'))}


FAMILIES = {family.kind: family for family in (SmartRecruiters(), Ashby(), Eightfold(), Icims(), BeeSite())}
