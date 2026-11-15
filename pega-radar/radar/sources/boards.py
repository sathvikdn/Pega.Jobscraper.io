"""India job boards that publish a public feed or server-rendered search page.

Instahyre, Cutshort, Shine, Hirist and TimesJobs. Endpoint shapes were verified against live
responses on 14 November 2026. Retrying a board that errors is the orchestrator's decision.
"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser

from ..model import is_india, is_pega, make_job, outside_india, salary_lpa, strip_html
from . import FALLBACK_TITLE, WRONG_SHAPE, day, failure, number, records, settle

UNEXPECTED = ('error', 'the page no longer has the expected structure')
OUT_OF_TIME = ('error', 'the time budget ran out')


def _result(name, jobs, found, http, problem=None, read_any=False):
    return settle(name, name, 'board', jobs, found=found, requests=http.count, problem=problem, read_any=read_any)


def _count(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _paged(http, fetch, key, following, page_limit):
    """Read a paged JSON feed. Returns `(rows, problem)`; `problem` is None when every page was read.

    `fetch(page_index, rows_so_far)` performs the request and `key` names the list of rows, which
    must be present: a 200 answer without it is a changed or refused feed, not an empty one.
    `following(data, batch, page_index)` is falsy on the last page, else the feed's page count
    (or True when the feed only says that more follow).
    """
    rows, pages = [], True
    for index in range(page_limit):
        if index and http.expired():
            return rows, OUT_OF_TIME
        response = fetch(index, len(rows))
        data = response.json() if response.ok else None
        if not isinstance(data, dict) or not isinstance(data.get(key), list):
            return rows, (failure(response) if not response.ok else WRONG_SHAPE)
        batch = records(data[key])
        rows.extend(batch)
        pages = bool(batch) and following(data, batch, index)
        if not pages:
            return rows, None
    total = pages if isinstance(pages, int) and not isinstance(pages, bool) else 'more'
    return rows, ('error', f'stopped at page {page_limit} of {total}; raise the cap')


# ───────────────────────────── Instahyre ─────────────────────────────

INSTAHYRE_PAGES = 60


def instahyre(http):
    rows, problem = _paged(
        http,
        lambda index, seen: http.get(f'https://www.instahyre.com/api/v1/job_search?skills=pega&offset={seen}'),
        'objects',
        lambda data, batch, index: bool(isinstance(data.get('meta'), dict) and data['meta'].get('next')),
        page_limit=INSTAHYRE_PAGES)
    jobs = []
    for row in rows:
        title = row.get('title') or row.get('candidate_title') or ''
        skills = ' '.join(str(skill) for skill in row.get('keywords') or [])
        location = str(row.get('locations') or '').replace(',', ', ')
        if not is_pega(title + ' ' + skills) or not row.get('public_url') or outside_india(location):
            continue
        jobs.append(make_job('Instahyre', row.get('id') or row['public_url'], title or FALLBACK_TITLE,
                             (row.get('employer') or {}).get('company_name'), row['public_url'], location or 'India'))
    return _result('Instahyre', jobs, len(rows), http, problem, read_any=bool(rows))


# ───────────────────────────── Cutshort ─────────────────────────────

def _cutshort_page(page_html):
    """`(jobs, live_job_count)` from the page's embedded Next.js data, or None when it is not there."""
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page_html, re.S)
    try:
        queries = json.loads(match.group(1))['props']['pageProps']['dehydratedState']['queries']
    except (AttributeError, ValueError, KeyError, TypeError):
        return None
    for query in queries if isinstance(queries, list) else ():
        try:
            page = query['state']['data']['data']['pageData']
            jobs = page['jobs']
        except (KeyError, TypeError):
            continue
        if isinstance(jobs, list):
            return records(jobs), _count(page.get('liveJobCount'))
    return None


def cutshort(http):
    response = http.get('https://cutshort.io/jobs/pega-jobs', accept='text/html')
    if not response.ok:
        return _result('Cutshort', [], 0, http, failure(response))
    page = _cutshort_page(response.text)
    if page is None:
        return _result('Cutshort', [], 0, http, UNEXPECTED)
    rows, live = page
    jobs = []
    for row in rows:
        title = row.get('headline') or ''
        description = strip_html(row.get('sanitizedComment') or '')
        skills = ' '.join(str(skill) for skill in row.get('allSkills') or [])
        location = row.get('locationsText') or ''
        if not is_pega(f'{title} {description} {skills}') or not row.get('publicUrl'):
            continue
        if outside_india(location) and row.get('remoteType') == 'remote_not_okay':
            continue
        experience = row.get('expRange') if isinstance(row.get('expRange'), dict) else {}
        low, high = salary_lpa(row.get('salaryRangeText'))
        jobs.append(make_job('Cutshort', row.get('_id') or row['publicUrl'], title or FALLBACK_TITLE,
                             (row.get('companyDetails') or {}).get('name'), row['publicUrl'], location or 'India',
                             description=description, experience_min=number(experience.get('min')),
                             experience_max=number(experience.get('max')), salary_min_lpa=low, salary_max_lpa=high))
    # The page embeds only its first batch of jobs; the rest load in the browser.
    problem = ('error', f'stopped at {len(rows)} of {live}; the remaining jobs are not in the page') \
        if live > len(rows) else None
    return _result('Cutshort', jobs, max(len(rows), live), http, problem, read_any=True)


# ───────────────────────────── Shine ─────────────────────────────

SHINE_URL = 'https://www.shine.com/job-search/pega-jobs'
SHINE_PAGES = 25
_SHINE_JOB_LINK = re.compile(r'^/jobs/[^/]+/[^/]+/\d+')
_SHINE_COMPANY = re.compile(r'company|employer|recruiter', re.I)
_SHINE_YEARS = re.compile(r'(\d{1,2})\s*(?:to|-)\s*(\d{1,2})\s*(?:yrs?|years?)', re.I)
_VOID_TAGS = frozenset('area base br col embed hr img input link meta source track wbr'.split())


class _Node:
    def __init__(self, tag, attributes, parent):
        self.tag, self.parent = tag, parent
        self.attributes = attributes
        self.children = []          # _Node elements and str text runs, in document order

    @property
    def classes(self):
        return self.attributes.get('class') or ''

    def lines(self):
        """Non-empty text runs beneath this element, in document order."""
        found = []
        for child in self.children:
            if isinstance(child, _Node):
                found.extend(child.lines())
            elif child.strip():
                found.append(' '.join(child.split()))
        return found

    def descendants(self):
        for child in self.children:
            if isinstance(child, _Node):
                yield child
                yield from child.descendants()


class _Tree(HTMLParser):
    """Just enough of a document tree to find a job link's card and read its text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = self.current = _Node('', {}, None)
        self.links = []

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, dict(attrs), self.current)
        self.current.children.append(node)
        if tag == 'a' and _SHINE_JOB_LINK.match(node.attributes.get('href') or ''):
            self.links.append(node)
        if tag not in _VOID_TAGS:
            self.current = node

    def handle_endtag(self, tag):
        node = self.current
        while node.parent is not None and node.tag != tag:
            node = node.parent
        if node.parent is not None:      # ignore a stray closing tag that matches nothing open
            self.current = node.parent

    def handle_data(self, data):
        if self.current.tag not in ('script', 'style'):
            self.current.children.append(data)


def _shine_card(link):
    """The result card around a job link: the nearest of six ancestors whose class says so."""
    node = link
    for _ in range(6):
        node = node.parent
        if node is None or node.parent is None:
            break
        if 'result-card_card' in node.classes:
            return node
    return link.parent


def parse_shine(page_html):
    """`(path, title, company, location, experience_min, experience_max, card_text)` per job link."""
    tree = _Tree()
    tree.feed(page_html or '')
    tree.close()
    rows = []
    for link in tree.links:
        path = link.attributes['href'].split('?')[0]
        card = _shine_card(link)
        title = ' '.join(link.lines())
        lines = card.lines()
        company = next((' '.join(node.lines()) for node in card.descendants()
                        if _SHINE_COMPANY.search(node.classes) and node.lines()), '')
        if not company:
            # /jobs/<title-slug>/<company-slug>/<id>
            company = path.split('/')[3].replace('-', ' ').title()
        location = next((line for line in lines if is_india(line) and len(line) < 80 and line != title), '')
        years = _SHINE_YEARS.search(' '.join(lines))
        rows.append((path, title, company, location, int(years.group(1)) if years else None,
                     int(years.group(2)) if years else None, ' '.join(lines)))
    return rows


def shine(http):
    """Shine search pages are server rendered; each card carries title, employer, location and experience."""
    jobs, seen, problem = [], set(), None
    for page in range(1, SHINE_PAGES + 1):
        if page > 1 and http.expired():
            problem = OUT_OF_TIME
            break
        response = http.get(SHINE_URL + ('' if page == 1 else f'-{page}'), accept='text/html')
        if not response.ok:
            problem = failure(response)   # Shine pages intermittently answer HTTP 500
            break
        fresh = 0
        for path, title, company, location, low, high, text in parse_shine(response.text):
            if path in seen:
                continue
            seen.add(path)
            fresh += 1
            if is_pega(title + ' ' + text):
                jobs.append(make_job('Shine', path.rstrip('/').split('/')[-1], title or FALLBACK_TITLE, company,
                                     'https://www.shine.com' + path, location or 'India',
                                     experience_min=low, experience_max=high))
        if not fresh:
            if page == 1:
                # A search page for "pega" with no job links at all means the markup has changed.
                problem = UNEXPECTED
            break
    else:
        problem = ('error', f'stopped at page {SHINE_PAGES} while pages still had new jobs; raise the cap')
    return _result('Shine', jobs, len(seen), http, problem, read_any=bool(seen))


# ───────────────────────────── Hirist ─────────────────────────────

FEED_PAGES = 60


def hirist(http):
    """Hirist's own search feed; includes experience and the advertised salary band in LPA."""
    headers = {'Origin': 'https://www.hirist.tech', 'Referer': 'https://www.hirist.tech/'}  # required by the feed
    rows, problem = _paged(
        http,
        lambda index, seen: http.get(
            f'https://gladiator.hirist.tech/job/search?query=Pega&page={index}&posting=0&industry=&size=20',
            headers=headers),
        'data',
        lambda data, batch, index: len(batch) >= 20 and index + 1 < _count(data.get('totalPages'))
        and _count(data.get('totalPages')),
        page_limit=FEED_PAGES)
    jobs = []
    for row in rows:
        title = row.get('title') or ''
        tags = ' '.join(tag.get('name') or '' for tag in row.get('tags') or [] if isinstance(tag, dict))
        location = ', '.join(place.get('name') or '' for place in row.get('locations') or []
                             if isinstance(place, dict)) or row.get('otherLocation') or ''
        if not is_pega(title + ' ' + tags) or not row.get('jobDetailUrl') or outside_india(location):
            continue
        low, high = number(row.get('minSal')), number(row.get('maxSal'))
        advertised = low is not None and high is not None and high > 0 and not row.get('hideSal')
        jobs.append(make_job('Hirist', row.get('id') or row['jobDetailUrl'], title or FALLBACK_TITLE,
                             (row.get('companyData') or {}).get('companyName'), row['jobDetailUrl'], location or 'India',
                             posted_at=day(row.get('createdTimeMs') or row.get('createdTime')),
                             experience_min=number(row.get('min')), experience_max=number(row.get('max')),
                             salary_min_lpa=low if advertised else None, salary_max_lpa=high if advertised else None,
                             apply_url=row.get('applyUrl')))
    return _result('Hirist', jobs, len(rows), http, problem, read_any=bool(rows))


# ───────────────────────────── TimesJobs ─────────────────────────────

def timesjobs(http):
    headers = {'Origin': 'https://www.timesjobs.com', 'Referer': 'https://www.timesjobs.com/'}  # required by the feed
    rows, problem = _paged(
        http,
        lambda index, seen: http.post_json(
            'https://tjapi.timesjobs.com/search/api/v1/search/jobs/list',
            {'keyword': 'pega', 'location': '', 'experience': '', 'page': str(index + 1), 'size': '25',
             'jobFunctions': [], 'company': '', 'industry': '', 'functionAreaId': '', 'jobFunction': ''},
            headers=headers),
        'jobs',
        lambda data, batch, index: index + 1 < _count(data.get('totalPages')) and _count(data.get('totalPages')),
        page_limit=FEED_PAGES)
    jobs = []
    for row in rows:
        title = row.get('title') or ''
        snippet = strip_html(row.get('description') or '')
        location = row.get('location') or ''
        if (not is_pega(f"{title} {row.get('skills') or ''} {snippet}") or not row.get('jobDetailUrl')
                or outside_india(location)):
            continue
        low, high = number(row.get('lowSalary')), number(row.get('highSalary'))
        advertised = low is not None and high is not None and high > 0
        # The band is in annual rupees for most rows and already in lakhs for some.
        lakh = 100000 if advertised and high > 1000 else 1
        url = row['jobDetailUrl'].split('&source=')[0]   # drop the click-tracking suffix
        jobs.append(make_job('TimesJobs', row.get('jobId') or url, title or FALLBACK_TITLE, row.get('company') or row.get('hfCompany'),
                             url, location or 'India', posted_at=day(row.get('postDate')), description=snippet,
                             experience_min=number(row.get('experienceFrom')),
                             experience_max=number(row.get('experienceTo')),
                             salary_min_lpa=low / lakh if advertised else None,
                             salary_max_lpa=high / lakh if advertised else None))
    return _result('TimesJobs', jobs, len(rows), http, problem, read_any=bool(rows))


BOARDS = {'Instahyre': instahyre, 'Cutshort': cutshort, 'Shine': shine, 'Hirist': hirist, 'TimesJobs': timesjobs}
