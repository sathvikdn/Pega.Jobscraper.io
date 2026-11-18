"""Career portals read from their server-rendered search pages: SuccessFactors Career Site
Builder, Phenom, TalentBrew (Radancy) and Avature.

These pages are plain HTML answers to a GET; nothing here runs JavaScript, keeps cookies or
sends anything but the client's standard headers. What the 15 November 2026 captures confirm
and what is assumed is noted per family; assumed markup is parsed defensively, so a page that
does not have it is `error` ("unexpected response shape") rather than an empty board.

SuccessFactors CSB — CONFIRMED (ANZ, ExxonMobil, JLR, Volvo Cars, Zurich, Vodafone Idea):
  GET https://{host}{path}/search/?q=pega&startrow=N&locationsearch= ; rows are
  <tr class="data-row"> with a.jobTitle-link href "/job/{slug}/{id}/", span.jobLocation
  ("Mumbai, Maharashtra, IN", "Docklands, AU"), span.jobDate ("10 Nov 2026" / "Nov 14, 2026"),
  span.jobDepartment / jobFacility; span.paginationLabel "Results <b>1 – 7</b> of <b>347</b>".
  A search without matches shows div#noresults *and then lists the most recent jobs "for your
  convenience"* (ExxonMobil, Volvo): those rows are not matches and are ignored. Detail pages
  carry itemprop="description" (Standard Chartered capture). Page size varies by site, so the
  next startrow is the current one plus the rows received.

Phenom — CONFIRMED (ABB, Conduent, CVS, LPL, Marsh, Orange, Proximus, Toyota, UPS):
  GET https://{host}/{locale_path}/search-results?keywords=pega&from=N embeds
  `phApp.ddo = {...}` whose eagerLoadRefineSearch is {status: 200, hits, totalHits, data: {jobs}};
  jobs carry jobSeqNo, jobId, reqId, title, location, multi_location, country, postedDate,
  category, descriptionTeaser. phApp.urlMap gives job pages as "job/:jobSeqNo/:title" and
  phApp.ddoRealPath {"jobDetail": "data.job"}. ASSUMED: the job page's ddo jobDetail.data.job
  has `description` (HTML); the search without keywords lists the whole board.

TalentBrew — CONFIRMED (BD, IKEA, Optum, Schwab, AstraZeneca, Cargill, MassMutual, Chevron):
  GET https://{host}/{locale_path}/search-jobs/{keyword}/{org_id}/{page}; section#search-results
  carries data-total-job-results, data-total-pages, data-current-page, data-organization-ids;
  results are <a href="/…/job/{city}/{slug}/{org}/{job id}" data-job-id> with an <h2> title or
  the link text, and an element of class job-location. A search without matches still renders
  the section with total 0, and its data-organization-ids proves the site. ASSUMED: job pages
  carry a schema.org JobPosting (JSON-LD) or a div.ats-description.

Avature — CONFIRMED only for an empty search (Maximus, MetLife, Tesco, HSBC):
  GET https://{host}/{path}/SearchJobs/{keyword}?listFilterMode=1 renders
  <article class="article article--result"> "No jobs found" and a list-controls legend
  aria-label="0 results". ASSUMED: result articles hold an <a> to …/JobDetail/{slug}/{id} as
  title and a location line; paging is jobOffset/jobRecordsPerPage; job pages carry the
  description in article__content__view__field__value blocks or JSON-LD.
"""
from __future__ import annotations

import re
import urllib.parse

from . import WRONG_SHAPE
from .portal_base import (Family, Page, attributes, code_from_location, element, inner_html, integer,
                          job_posting_ld, json_after, page_get, plain, text, when)

AVATURE_PAGE = 50


def _host(portal):
    value = str(portal.get('host') or '').strip()
    if '://' in value:
        value = urllib.parse.urlsplit(value).hostname or ''
    return value.strip('/').lower()


def _prefix(value):
    """'' or '/a/b' from a configured path such as 'global/en' or '/careers/'."""
    value = str(value or '').strip().strip('/')
    return '/' + value if value else ''


def _absolute(host, href):
    href = text(href)
    if href.startswith('https://') or href.startswith('http://'):
        return href
    return f'https://{host}/' + href.lstrip('/') if href else ''


def _slug(title):
    return re.sub(r'[^a-z0-9]+', '-', str(title or '').lower()).strip('-') or 'job'


def _ld_fields(posting):
    """Description, location and date from a schema.org JobPosting."""
    if not isinstance(posting, dict):
        return {}
    places = posting.get('jobLocation')
    places = places if isinstance(places, list) else [places]
    names = []
    for place in places:
        address = place.get('address') if isinstance(place, dict) else None
        if isinstance(address, dict):
            country = address.get('addressCountry')
            country = country.get('name') if isinstance(country, dict) else country
            names.append(', '.join(part for part in (text(address.get('addressLocality')),
                                                     text(address.get('addressRegion')), text(country)) if part))
    learnt = {'description': plain(posting.get('description')), 'posted': when(posting.get('datePosted'))}
    location = ' · '.join(dict.fromkeys(name for name in names if name))
    if location:
        learnt['location'] = location
    return learnt


# ───────────────────────────── SuccessFactors Career Site Builder ─────────────────────────────

_SF_ROW = re.compile(r'(?is)<tr\b[^>]*class="[^"]*\bdata-row\b[^"]*"[^>]*>(.*?)</tr>')
_SF_TOTAL = re.compile(r'(?is)class="paginationLabel"[^>]*>.*?<b>\s*([\d.,]+)\s*[–-]\s*([\d.,]+)\s*</b>.*?<b>\s*([\d.,]+)\s*</b>')
_SF_MARKERS = ('id="noresults"', 'searchResultsShell', 'id="searchresults"', 'class="data-row')


def _span(fragment, name):
    match = re.search(r'(?is)<span\b[^>]*class="' + name + r'"[^>]*>(.*?)</span>', fragment)
    return plain(match.group(1)) if match else ''


def _digits(value):
    return int(re.sub(r'[^\d]', '', value)) if re.search(r'\d', value or '') else None


class SuccessFactors(Family):
    kind = 'successfactors'

    def identity(self, portal):
        return _host(portal) + _prefix(portal.get('path'))

    def search(self, http, portal, query, cursor):
        startrow = cursor or 0
        host = _host(portal)
        url = (f'https://{host}{_prefix(portal.get("path"))}/search/?'
               + urllib.parse.urlencode({'q': query or '', 'startrow': startrow, 'locationsearch': ''}))
        page, problem = page_get(http, url)
        if page is None:
            return None, problem
        if not any(marker in page for marker in _SF_MARKERS):
            return None, WRONG_SHAPE
        if 'id="noresults"' in page:
            # "No open positions match" - the rows after it are the newest jobs, not matches.
            return Page([], 0, None), None
        rows = []
        for match in _SF_ROW.finditer(page):
            cells = match.group(1)
            link = re.search(r'(?is)<a\b([^>]*class="[^"]*jobTitle-link[^"]*"[^>]*)>(.*?)</a>', cells)
            href = attributes(link.group(1)).get('href') or '' if link else ''
            identifier = re.search(r'/(\d+)/?(?:[?#].*)?$', href)
            if not identifier:
                continue
            location = _span(cells, 'jobLocation')
            rows.append({'id': identifier.group(1), 'title': plain(link.group(2)), 'location': location,
                         'country_code': code_from_location(location), 'posted': when(_span(cells, 'jobDate')),
                         'unit': _span(cells, 'jobDepartment') or _span(cells, 'jobFacility'),
                         'requisition': identifier.group(1), 'description': '', 'url': _absolute(host, href)})
        counted = _SF_TOTAL.search(page)
        total = _digits(counted.group(3)) if counted else None
        if total and not rows:
            return None, WRONG_SHAPE            # the site says it found jobs but no row could be read
        # The page size is the site's own, so the next startrow follows from the rows received.
        following = startrow + len(rows)
        more = bool(rows) and total is not None and following < total
        return Page(rows, total if total is not None else len(rows), following if more else None), None

    def detail(self, http, portal, row):
        page, _ = page_get(http, row['url'])
        if page is None:
            return None
        body = element(page, 'itemprop', 'description')
        learnt = {'description': plain(body)} if body else _ld_fields(job_posting_ld(page))
        return learnt if learnt.get('description') else None


# ───────────────────────────── Phenom ─────────────────────────────

class Phenom(Family):
    kind = 'phenom'
    queries = ('pega',)      # Phenom's search is semantic; a PRPC query adds requests, not jobs

    def identity(self, portal):
        return _host(portal) + _prefix(portal.get('locale_path'))

    def _base(self, portal):
        return f'https://{_host(portal)}{_prefix(portal.get("locale_path"))}'

    def search(self, http, portal, query, cursor):
        offset = cursor or 0
        params = {'keywords': query, 'from': offset} if query else {'from': offset}
        page, problem = page_get(http, self._base(portal) + '/search-results?' + urllib.parse.urlencode(params))
        if page is None:
            return None, problem
        ddo = json_after(page, 'phApp.ddo')
        found = ddo.get('eagerLoadRefineSearch') if isinstance(ddo, dict) else None
        data = found.get('data') if isinstance(found, dict) else None
        if not isinstance(data, dict) or not isinstance(data.get('jobs'), list) or \
                found.get('status') not in (200, '200') or integer(found.get('totalHits')) is None:
            return None, WRONG_SHAPE
        total = integer(found['totalHits'])
        jobs = [job for job in data['jobs'] if isinstance(job, dict)]
        rows = [row for row in (self._row(portal, job) for job in jobs) if row]
        # Phenom pages by `from`; the page size is whatever the site renders (10 by default).
        following = offset + len(jobs)
        return Page(rows, total, following if jobs and following < total else None), None

    def _row(self, portal, job):
        identifier = text(job.get('jobSeqNo')) or text(job.get('jobId'))
        if not identifier:
            return None
        places = job.get('multi_location') if isinstance(job.get('multi_location'), list) else []
        places = [text(place) for place in places] or [text(job.get('location')) or text(job.get('cityStateCountry'))]
        country = text(job.get('country'))
        location = ' · '.join(dict.fromkeys(place for place in places if place))
        if country and country.lower() not in location.lower():
            location = f'{location} · {country}' if location else country
        title = text(job.get('title'))
        return {'id': identifier, 'title': title, 'location': location, 'posted': when(job.get('postedDate')),
                'requisition': text(job.get('reqId')) or text(job.get('jobId')),
                'unit': text(job.get('businessUnit')) or text(job.get('category')),
                'employment_type': text(job.get('type')), 'description': '',
                'apply_url': text(job.get('applyUrl')),
                'url': f'{self._base(portal)}/job/{urllib.parse.quote(identifier, safe="")}/{_slug(title)}'}

    def detail(self, http, portal, row):
        page, _ = page_get(http, row['url'])
        if page is None:
            return None
        ddo = json_after(page, 'phApp.ddo')
        detail = ddo.get('jobDetail') if isinstance(ddo, dict) else None
        data = detail.get('data') if isinstance(detail, dict) else None
        job = data.get('job') if isinstance(data, dict) else None
        if isinstance(job, dict):
            parts = [plain(job.get(key)) for key in ('description', 'qualifications', 'responsibilities')]
            description = '\n'.join(part for part in parts if part)
            if description:
                return {'description': description}
        learnt = _ld_fields(job_posting_ld(page))
        return learnt if learnt.get('description') else None


# ───────────────────────────── TalentBrew (Radancy) ─────────────────────────────

_TB_SECTION = re.compile(r'(?is)<section\b[^>]*\bid="search-results"[^>]*>')
_TB_LINK = re.compile(r'(?is)<a\b([^>]*\bdata-job-id="\d+"[^>]*)>(.*?)</a>')


_TB_NEXT = re.compile(r'(?is)<a\b[^>]*class="[^"]*\bnext\b[^"]*"[^>]*>')


def _tb_next(page, host):
    """The next page's URL from the pagination's "Next" link; '' when the link is there but unusable,
    None when there is no such link."""
    paging = page.find('pagination__paging')
    paging = paging if paging >= 0 else page.find('class="pagination')
    if paging < 0:
        return None
    match = _TB_NEXT.search(page, paging)
    if not match:
        return None
    tag = attributes(match.group(0))
    href = (tag.get('href') or '').strip()
    if 'disabled' in tag.get('class', '').split() or not href or href.startswith('#') or href.startswith('javascript'):
        return ''
    url = _absolute(host, href)
    return url if urllib.parse.urlsplit(url).hostname == host and url.startswith('https://') else ''


class TalentBrew(Family):
    kind = 'talentbrew'

    def identity(self, portal):
        return _host(portal)

    def _built(self, portal, query, number):
        keyword = urllib.parse.quote(query or '', safe='')
        org = urllib.parse.quote(str(portal['org_id']).strip())
        return f'https://{_host(portal)}{_prefix(portal.get("locale_path"))}/search-jobs/{keyword}/{org}/{number}'

    def search(self, http, portal, query, cursor):
        # The cursor is `(page number, URL)`: the next page's URL is taken from the page's own
        # "Next" link (sites differ: ".../159/1/1" then ".../159/2/2"); the first page is built.
        number, url = cursor or (1, None)
        host = _host(portal)
        org = str(portal['org_id']).strip()
        page, problem = page_get(http, url or self._built(portal, query, number))
        if page is None:
            return None, problem
        section = _TB_SECTION.search(page)
        if not section:
            return None, WRONG_SHAPE
        info = attributes(section.group(0))
        if org not in re.split(r'[,\s]+', info.get('data-organization-ids', '')):
            return None, ('error', f'the site is not organisation {org}; check org_id')
        total = integer(info.get('data-total-job-results'))
        total = total if total is not None else integer(info.get('data-total-results'))
        pages = integer(info.get('data-total-pages')) or 1
        if total is None:
            return None, WRONG_SHAPE
        listing = page[section.end():]
        start = listing.find('id="search-results-list"')
        listing = listing[start:] if start >= 0 else listing
        links = list(_TB_LINK.finditer(listing))
        rows = []
        for position, link in enumerate(links):
            tag = attributes(link.group(1))
            identifier = tag.get('data-job-id') or ''
            following = links[position + 1].start() if position + 1 < len(links) else link.end() + 4000
            window = listing[link.start():following]
            heading = re.search(r'(?is)<h[23]\b[^>]*>(.*?)</h[23]>', link.group(2))
            location = re.search(r'(?is)<(\w+)\b[^>]*class="[^"]*\bjob-location\b[^"]*"[^>]*>(.*?)</\1>', window)
            requisition = re.search(r'(?is)class="[^"]*\bjob-(?:req-)?id\b[^"]*"[^>]*>(.*?)</', window)
            place = plain(location.group(2)) if location else ''
            rows.append({'id': identifier, 'title': plain(heading.group(1) if heading else link.group(2)),
                         'location': place, 'country_code': '', 'description': '',
                         'requisition': re.sub(r'(?i)^requisition id:\s*', '', plain(requisition.group(1)))
                         if requisition else '',
                         'url': _absolute(host, tag.get('href'))})
        if total and not rows:
            return None, WRONG_SHAPE
        current = integer(info.get('data-current-page')) or number
        if not rows or current >= pages:
            return Page(rows, total, None), None
        following, note = _tb_next(page, host), None
        if following is None:
            # No "Next" link at all: fall back to the documented URL pattern.
            following = self._built(portal, query, current + 1)
        elif following == '':
            note = 'the next-page link could not be read; the page URL was constructed instead'
            following = self._built(portal, query, current + 1)
        return Page(rows, total, (current + 1, following), note), None

    def board_size(self, http, portal):
        # The empty search page itself proves the site (its organisation id matches), and
        # TalentBrew has no unfiltered search URL that every site honours.
        return None, None

    def detail(self, http, portal, row):
        page, _ = page_get(http, row['url'])
        if page is None:
            return None
        learnt = _ld_fields(job_posting_ld(page))
        if not learnt.get('description'):
            body = element(page, 'class', 'ats-description', contains=True) or \
                element(page, 'class', 'job-description', contains=True)
            learnt = {'description': plain(body)} if body else {}
        return learnt if learnt.get('description') else None


# ───────────────────────────── Avature ─────────────────────────────

_AV_ARTICLE = re.compile(r'(?is)<article\b[^>]*class="[^"]*\barticle--result\b[^"]*"[^>]*>(.*?)</article>')
_AV_LEGEND = re.compile(r'(?is)class="[^"]*list-controls__text__legend[^"]*"[^>]*>')


class Avature(Family):
    kind = 'avature'

    def identity(self, portal):
        return _host(portal) + _prefix(portal.get('path'))

    def _url(self, portal, query, offset):
        base = f'https://{_host(portal)}{_prefix(portal.get("path"))}/SearchJobs'
        params = {'listFilterMode': 1, 'jobRecordsPerPage': AVATURE_PAGE, 'jobOffset': offset}
        if portal.get('search_param'):
            return base + '/?' + urllib.parse.urlencode({str(portal['search_param']): query or '', **params})
        return base + (f'/{urllib.parse.quote(query, safe="")}' if query else '') + '?' + urllib.parse.urlencode(params)

    def search(self, http, portal, query, cursor):
        offset = cursor or 0
        page, problem = page_get(http, self._url(portal, query, offset))
        if page is None:
            return None, problem
        articles = [match.group(1) for match in _AV_ARTICLE.finditer(page)]
        legend = _AV_LEGEND.search(page)
        if not articles and not legend:
            return None, WRONG_SHAPE
        total = None
        if legend:
            label = attributes(legend.group(0)).get('aria-label', '') + ' ' + plain(inner_html(page, legend.start()))
            counted = re.search(r'(?i)(?:of\s+)?([\d.,]+)\s+results?', label)
            total = _digits(counted.group(1)) if counted else None
        host = _host(portal)
        rows = []
        for article in articles:
            link = re.search(r'(?is)<a\b([^>]*href="[^"]*JobDetail[^"]*"[^>]*)>(.*?)</a>', article) or \
                re.search(r'(?is)<h3\b[^>]*>.*?<a\b([^>]*href="[^"]+"[^>]*)>(.*?)</a>', article)
            if not link:
                continue                       # the "No jobs found" article has no link
            href = attributes(link.group(1)).get('href', '')
            identifier = re.search(r'(?:jobId=|/)(\d+)/?(?:[?#].*)?$', href)
            if not identifier:
                continue
            location = re.search(r'(?is)<(\w+)\b[^>]*class="[^"]*location[^"]*"[^>]*>(.*?)</\1>', article)
            subtitle = re.search(r'(?is)<(\w+)\b[^>]*class="[^"]*article__header__text__subtitle[^"]*"[^>]*>(.*?)</\1>',
                                 article)
            place = plain((location or subtitle).group(2)) if (location or subtitle) else ''
            rows.append({'id': identifier.group(1), 'title': plain(link.group(2)), 'location': place,
                         'country_code': '', 'description': '', 'requisition': identifier.group(1),
                         'url': _absolute(host, href)})
        if total is None:
            total = offset + len(rows) + (AVATURE_PAGE if len(rows) >= AVATURE_PAGE else 0)
        if total and not rows and not offset:
            return None, WRONG_SHAPE
        following = offset + len(rows)
        return Page(rows, total, following if rows and following < total else None), None

    def detail(self, http, portal, row):
        page, _ = page_get(http, row['url'])
        if page is None:
            return None
        learnt = _ld_fields(job_posting_ld(page))
        if not learnt.get('description'):
            values = [plain(inner_html(page, match.start())) for match in re.finditer(
                r'<[A-Za-z][\w-]*\b[^>]*class="[^"]*article__content__view__field__value[^"]*"[^>]*>', page)]
            description = '\n'.join(value for value in values if value)
            learnt = {'description': description} if description else {}
        return learnt if learnt.get('description') else None


FAMILIES = {family.kind: family for family in (SuccessFactors(), Phenom(), TalentBrew(), Avature())}
