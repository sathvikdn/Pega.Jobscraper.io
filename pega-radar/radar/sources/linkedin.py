"""LinkedIn public guest job search - no sign-in, the same pages an anonymous visitor sees.

The query plan is Bengaluru first. Finished queries are checkpointed and unread postings are
kept in a backlog, so a rate-limited or interrupted run costs time but never a posting. When
LinkedIn refuses (the client's circuit breaker opens) all LinkedIn work stops and the result
says `partial`, `blocked` or `error`.

`run` writes nothing: it returns the result together with a `commit` callable that stores the
checkpoint, backlog and remembered postings. The orchestrator calls it only after the returned
jobs are saved, so a run that is killed or whose save fails is simply repeated.
"""
from __future__ import annotations

import logging
import re
import time
import urllib.parse
from collections import namedtuple
from datetime import date, datetime, timedelta, timezone

from ..model import (company_key, is_bengaluru, is_pega, make_job, make_result, now_iso, outside_india,
                     strip_html)
from . import FALLBACK_TITLE, FOCUS_TYPES, day, is_focus

logger = logging.getLogger('radar.linkedin')   # a child of the scan log, so lines land in data/logs

SOURCE = 'LinkedIn'
HOST = 'www.linkedin.com'
SEARCH_URL = 'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search'
DETAIL_URL = 'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/'
PUBLIC_URL = 'https://www.linkedin.com/jobs/view/'
HTML = 'text/html,*/*'

# Exact-phrase and role variants: each returns a slightly different slice of the guest feed.
# Rare bare keywords such as "PRPC" fuzzy-match thousands of unrelated jobs and are left out.
DEFAULT_KEYWORDS = ['pega', '"pega" OR "PRPC" OR "pegasystems"', 'pega developer', 'pega architect',
                    'pega senior system architect', 'pega CSSA', 'pega lead', 'pega CDH decisioning', 'pega engineer']
BENGALURU = 'Bengaluru, Karnataka, India'
INDIA = 'India'
DEFAULT_OTHER_CITIES = ['Hyderabad, Telangana, India', 'Pune, Maharashtra, India', 'Chennai, Tamil Nadu, India',
                        'Mumbai, Maharashtra, India', 'Gurugram, Haryana, India', 'Noida, Uttar Pradesh, India',
                        'Kolkata, West Bengal, India']
DEFAULT_DETAIL_BUDGET = 300
# LinkedIn's share of a scan. Without it a throttled sweep crawls (8 s pacing, retry pauses) until the
# whole scan budget is gone while every other source has long finished. The checkpoint and backlog
# carry unfinished work to the next run, so stopping early costs time, never a posting.
DEFAULT_MINUTES = 15
# Requests still refused with 429/999 after the client's own retries. The client's breaker only opens
# after 5 refusals in a row, and the odd success in between resets it, so a feed that throttles most
# requests never trips it; counting refusals across the run does.
DEFAULT_THROTTLE_LIMIT = 8
# Minutes of LinkedIn's share kept for reading descriptions. Searches alone can fill the whole share
# (the 21 Nov evening run spent all 15 minutes on 40 searches and read none of 423 waiting
# descriptions), and a posting without its description cannot be scored for Pega work or pay.
# Searches stop when only this much is left; whatever they leave unused also goes to descriptions.
DEFAULT_DETAIL_MINUTES = 5
THROTTLE_STATUSES = (429, 999)
PROGRESS_EVERY = 10          # log a progress line every this many searches
MAX_PAGES = 40
RESULT_CAP = 990             # LinkedIn's own limit: the guest endpoint stops serving results near 1,000
CHECKPOINT_KEY = 'linkedin_checkpoint'
REJECTED_KEY = 'linkedin_rejected'
BACKLOG_KEY = 'linkedin_backlog'
UNREADABLE_KEY = 'linkedin_unreadable'
RESUME_HOURS = 20            # a checkpoint older than this belongs to a previous day's scan
REMEMBER_DAYS = 45           # how long a rejected or unreadable posting is remembered
BACKLOG_TRIES = 3            # failed reads before a posting's description is declared unreadable
BACKLOG_DAYS = 21
BACKLOG_SIZE = 500
GONE_STATUSES = (404, 410)   # the posting was removed: its description will never load
NO_CARDS = 'search pages returned no job cards; markup changed or sign-in wall'
CARD_FIELDS = ('title', 'company', 'location', 'posted_at', 'title_match')

Query = namedtuple('Query', 'id keywords location quiet_pages')
# How one query ended. DONE and CAPPED are checkpointed: both read everything LinkedIn will serve.
DONE, CAPPED, FAILED, UNPARSED, HALTED = 'done', 'capped', 'failed', 'unparsed', 'halted'


def _query(keywords, location, quiet_pages=3):
    return Query(f'{keywords}|{location}', keywords, location, quiet_pages)


def _words(name):
    return re.findall(r'[a-z0-9]+', str(name or '').lower())


def _is_current_employer(company, current):
    """The registry entry is the user's own employer: flagged so, or sharing its leading words with `current`."""
    if company.get('current_employer'):
        return True
    wanted = _words(current)
    for name in (company.get('name'), *(company.get('aliases') or [])):
        words = _words(name)
        shared = min(len(words), len(wanted))
        if shared and words[:shared] == wanted[:shared]:
            return True
    return False


def query_plan(settings, companies, current_employer=''):
    """Every keyword for Bengaluru, then India-wide, then the other cities, then `pega <employer>`."""
    keywords = [keyword for keyword in _list(settings.get('keywords')) if isinstance(keyword, str)] or DEFAULT_KEYWORDS
    other_cities = _list(settings['other_cities']) if 'other_cities' in settings else DEFAULT_OTHER_CITIES
    plan = [_query(keyword, location) for location in (BENGALURU, INDIA, *other_cities) for keyword in keywords]
    # Employer queries catch roles that leave Pega out of the title. One quiet page ends them:
    # everything after it is filler. The user's own employer is not searched.
    flagged = sorted((company for company in companies
                      if company.get('linkedin_query') and not _is_current_employer(company, current_employer)),
                     key=lambda company: not is_focus(company))
    plan += [_query('pega ' + company['name'], INDIA, quiet_pages=1) for company in flagged]
    return list({query.id: query for query in plan}.values())


def _list(value):
    return value if isinstance(value, list) else []


def parse_cards(html):
    """Job cards from a guest search fragment. Tolerates markup drift field by field."""
    cards = []
    for block in re.split(r'<li\b[^>]*>', html or '')[1:]:
        found = re.search(r'urn:li:jobPosting:(\d+)', block) or re.search(r'/jobs/view/(?:[^"?/]*-)?(\d+)', block)
        if not found:
            continue
        posted = re.search(r'<time[^>]*datetime="([^"]+)"', block)
        # A card whose title cannot be read is kept: its description decides whether it is a Pega role.
        cards.append({'id': found.group(1), 'title': _field(block, r'base-search-card__title[^>]*>(.*?)</h3>'),
                      'company': _field(block, r'base-search-card__subtitle[^>]*>(.*?)</h4>'),
                      'location': _field(block, r'job-search-card__location[^>]*>(.*?)</span>'),
                      'posted_at': day(posted.group(1)) if posted else None})
    return cards


def parse_detail(html):
    """Description and apply metadata from a guest job-posting fragment."""
    text = html or ''
    body = re.search(r'show-more-less-html__markup[^>]*>(.*?)</div>\s*(?:<button|<icon|</section)', text, re.S) \
        or re.search(r'show-more-less-html__markup[^>]*>(.*?)</div>', text, re.S)
    apply_url = None
    external = re.search(r'id="applyUrl"[^>]*>\s*<!--\s*"([^"]+)"', text)
    if external:
        link = urllib.parse.urlsplit(external.group(1).replace('&amp;', '&'))
        target = urllib.parse.parse_qs(link.query).get('url', [''])[0]
        if target.startswith(('http://', 'https://')):
            apply_url = target
    criteria = {strip_html(item.group(1)).lower(): strip_html(item.group(2)) for item in re.finditer(
        r'description__job-criteria-subheader[^>]*>(.*?)</h3>.*?description__job-criteria-text[^>]*>(.*?)</span>',
        text, re.S)}
    return {'location': _field(text, r'topcard__flavor--bullet[^>]*>(.*?)</span>'),
            'description': strip_html(body.group(1)) if body else '',
            'applicants': _field(text, r'num-applicants__caption[^>]*>(.*?)</(?:span|figcaption)>') or None,
            'apply_url': apply_url,
            'employment_type': criteria.get('employment type') or None,
            'closed': bool(re.search(r'no longer accepting applications', text, re.I))}


def _field(text, pattern):
    match = re.search(pattern, text, re.S)
    return strip_html(match.group(1)).replace('\n', ' ').strip() if match else ''


def _names_pega(card):
    return is_pega(card['title'] + ' ' + card['company'])


def _halted(http):
    return http.expired() or not http.host_open(HOST)


WALLED = 'LinkedIn sent its sign-in page instead of results (a soft block)'


def _walled(response):
    """True when a guest API call was redirected away from /jobs-guest/ (sign-in page, authwall, home page).

    LinkedIn's soft block answers 200 OK with its sign-in page, so neither the status nor the
    client's breaker sees it; only the final URL gives it away.
    """
    url = str(getattr(response, 'url', '') or '')
    if not getattr(response, 'ok', False) or '://' not in url:
        return False
    parts = urllib.parse.urlsplit(url)
    return (parts.hostname or '').endswith('linkedin.com') and not parts.path.startswith('/jobs-guest/')


def _setting(settings, key, default, cast):
    try:
        value = cast(settings.get(key, default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


class _Guard:
    """When LinkedIn work must stop: the scan's own limits, LinkedIn's share of time, or repeated throttling."""

    def __init__(self, http, settings):
        self.http = http
        clock = getattr(http, '_clock', None)
        self.clock = clock if callable(clock) else time.monotonic
        self.minutes = _setting(settings, 'minutes', DEFAULT_MINUTES, float)
        self.limit = _setting(settings, 'throttle_limit', DEFAULT_THROTTLE_LIMIT, int)
        # At most half the share, so searches always get time of their own.
        self.detail_minutes = min(_setting(settings, 'detail_minutes', DEFAULT_DETAIL_MINUTES, float),
                                  self.minutes / 2)
        self.started = self.clock()
        self.until = self.started + self.minutes * 60
        self.search_until = self.until - self.detail_minutes * 60
        self.throttled = 0
        self.why = ''          # every LinkedIn request must stop
        self.search_why = ''   # only searches stop; descriptions use the time kept for them

    def note(self, response):
        if getattr(response, 'status', None) in THROTTLE_STATUSES or _walled(response):
            self.throttled += 1

    def elapsed_minutes(self):
        return (self.clock() - self.started) / 60

    def halted(self):
        if self.why:
            return True
        if _halted(self.http):
            return True
        if self.throttled >= self.limit:
            self.why = (f'LinkedIn rate-limited or sign-in-walled {self.throttled} requests, so it was left '
                        'for the next run instead of waiting out the scan budget')
        elif self.clock() >= self.until:
            self.why = f"LinkedIn's {self.minutes:g}-minute share of the scan ran out"
        if self.why:
            logger.warning('LinkedIn stopped early: %s', self.why)
        return bool(self.why)

    def search_halted(self):
        if self.halted():
            return True
        if not self.search_why and self.clock() >= self.search_until:
            self.search_why = (f"LinkedIn's search time ran out ({self.minutes - self.detail_minutes:g} of "
                               f'{self.minutes:g} minutes; the rest is kept for reading descriptions)')
            logger.info('LinkedIn: searches paused: %s', self.search_why)
        return bool(self.search_why)


class _Search:
    """Pages search queries and collects the cards they return, keyed by posting id."""

    def __init__(self, http, window_seconds, guard=None):
        self.http, self.window = http, window_seconds
        self.guard = guard
        self.cards = {}
        self.pages_read = 0
        self.blocked = 0
        self.errors = []

    def run(self, query):
        """Page one query while it still returns Pega roles and say how it ended.

        The guest feed lists genuine matches first and then pads the list with unrelated jobs,
        so paging stops after `quiet_pages` consecutive pages without a Pega title. Cards seen
        before the padding (`zone`) may be worth a description check even without a Pega title.
        """
        start = quiet = pages = 0
        while pages < MAX_PAGES and start < RESULT_CAP:
            if (self.guard.search_halted() if self.guard else _halted(self.http)):
                return HALTED
            parameters = urllib.parse.urlencode({'keywords': query.keywords, 'location': query.location,
                                                 'f_TPR': f'r{self.window}', 'sortBy': 'DD', 'start': start})
            response = self.http.get(SEARCH_URL + '?' + parameters, accept=HTML)
            if self.guard:
                self.guard.note(response)
            if _walled(response):
                self.blocked += 1
                self.errors.append(f'{query.keywords} / {query.location}: {WALLED}')
                return FAILED
            if not response.ok:
                if response.status == 400 and pages:
                    return DONE  # LinkedIn answers 400 once the offset runs past the last result
                self.blocked += response.blocked
                self.errors.append(f'{query.keywords} / {query.location}: {response.error or response.status}')
                return FAILED
            page = parse_cards(response.text)
            if not page:
                # A blank body is the feed's way of saying "no (more) results". Anything else
                # without cards is a page this parser cannot read - a failure, not an answer.
                return DONE if not response.text.strip() else UNPARSED
            self.pages_read += 1
            pages += 1
            quiet = 0 if any(_names_pega(card) for card in page) else quiet + 1
            for card in page:
                seen = self.cards.setdefault(card['id'], dict(card, zone=False, title_match=_names_pega(card)))
                seen['zone'] = seen['zone'] or quiet <= 1
            start += len(page)  # pages hold 10 cards today; never assume the size
            if quiet >= query.quiet_pages:
                return DONE
        return CAPPED   # out of pages before the results ran out: whatever lay beyond was not seen


def _load_checkpoint(store):
    """The resumable state of the current sweep, or a fresh one when none is recent enough."""
    saved = store.kv_get(CHECKPOINT_KEY)
    try:
        started = datetime.fromisoformat(saved['window_started'])
        if datetime.now(timezone.utc) - started < timedelta(hours=RESUME_HOURS):
            return {'window_started': saved['window_started'], 'done': [str(query) for query in saved['done']],
                    'capped': [str(query) for query in _list(saved.get('capped'))]}
    except (TypeError, KeyError, ValueError, AttributeError):
        pass
    return {'window_started': now_iso(), 'done': [], 'capped': []}


def _load_remembered(store, key):
    """Posting id -> day it was recorded, for the rejected and unreadable lists; entries expire after 45 days."""
    cutoff = (date.today() - timedelta(days=REMEMBER_DAYS)).isoformat()
    saved = store.kv_get(key)
    return {posting: seen for posting, seen in (saved.items() if isinstance(saved, dict) else ())
            if isinstance(seen, str) and seen >= cutoff}


def _load_backlog(store, today):
    """Posting id -> card for postings whose description an earlier run wanted but could not read."""
    saved = store.kv_get(BACKLOG_KEY)
    backlog = {}
    for posting, card in (saved.items() if isinstance(saved, dict) else ()):
        if isinstance(card, dict):
            backlog[str(posting)] = {
                'id': str(posting), 'title': str(card.get('title') or ''), 'company': str(card.get('company') or ''),
                'location': str(card.get('location') or ''), 'posted_at': day(card.get('posted_at')),
                'title_match': bool(card.get('title_match')), 'zone': True,
                'tries': card['tries'] if isinstance(card.get('tries'), int) else 0,
                'since': day(card.get('since')) or today}
    return backlog


def _detail_order(cards, skip, companies):
    """New postings worth reading, in the order the budget is spent.

    The backlog of earlier runs first; then Pega-title postings in Bengaluru, Pega-title postings
    elsewhere and untitled candidates from the relevant zone (Bengaluru first). Product and
    captive employers lead each group.
    """
    focus = {company_key(name) for company in companies if company.get('type') in FOCUS_TYPES
             for name in (company['name'], *(company.get('aliases') or []))}
    wanted = [card for card in cards if card['id'] not in skip and (card['title_match'] or card['zone'])]
    return sorted(wanted, key=lambda card: ('since' not in card, not card['title_match'],
                                            not is_bengaluru(card['location']),
                                            company_key(card['company']) not in focus))


def _budget(settings):
    try:
        return max(0, int(settings.get('detail_budget', DEFAULT_DETAIL_BUDGET)))
    except (TypeError, ValueError):
        return DEFAULT_DETAIL_BUDGET


def _to_job(card, detail, keep_unread, rejected, today):
    """The job for one card, or None. Postings read and found unsuitable are added to `rejected`."""
    if card['id'] in rejected:
        return None
    if detail is None:
        # Not read: keep Pega titles and whatever `keep_unread` names, never guess about the rest.
        if not (card['title_match'] or card['id'] in keep_unread):
            return None
    elif detail['closed'] or outside_india(detail['location']) or (
            not card['title_match'] and not is_pega(detail['description'])):
        # Every query is scoped to India, so only the posting's own page can place it abroad.
        rejected[card['id']] = today
        return None
    detail = detail or {}
    return make_job(SOURCE, card['id'], card['title'] or FALLBACK_TITLE, card['company'], PUBLIC_URL + card['id'],
                    detail.get('location') or card['location'], posted_at=card['posted_at'],
                    description=detail.get('description', ''), apply_url=detail.get('apply_url'),
                    employment_type=detail.get('employment_type'),
                    extra={'applicants': detail.get('applicants'), 'title_match': card['title_match']})


def run(http, ctx, companies=()):
    """One sweep. Returns `(result, commit)`; see the module docstring for why state is committed later."""
    store = ctx['store']
    config = ctx.get('config') if isinstance(ctx.get('config'), dict) else {}
    settings = config.get('linkedin') if isinstance(config.get('linkedin'), dict) else {}
    profile = config.get('profile') if isinstance(config.get('profile'), dict) else {}
    today = date.today().isoformat()
    checkpoint = _load_checkpoint(store)
    rejected = _load_remembered(store, REJECTED_KEY)
    unreadable = _load_remembered(store, UNREADABLE_KEY)
    backlog = _load_backlog(store, today)
    known = set(store.known_ids(SOURCE))
    plan = query_plan(settings, companies, profile.get('current_employer') or '')

    guard = _Guard(http, settings)
    search = _Search(http, int(ctx.get('window_days') or 3) * 86400, guard)
    endings = {}
    todo = [query for query in plan if query.id not in checkpoint['done']]
    logger.info('LinkedIn: %d of %d searches to run (%d resumed from an earlier run), limit %g minutes',
                len(todo), len(plan), len(plan) - len(todo), guard.minutes)
    for number, query in enumerate(todo, 1):
        if guard.search_halted():
            break
        endings[query.id] = search.run(query)
        if endings[query.id] in (FAILED, UNPARSED):
            logger.info('LinkedIn: search %d of %d %s (%s)', number, len(todo), endings[query.id],
                        search.errors[-1] if search.errors and endings[query.id] == FAILED else query.id)
        if number % PROGRESS_EVERY == 0 or number == len(todo):
            logger.info('LinkedIn: %d of %d searches done, %d postings seen, %d rate-limited, %.1f minutes',
                        number, len(todo), len(search.cards), guard.throttled, guard.elapsed_minutes())
    capped = [query for query, ending in endings.items() if ending == CAPPED]
    finished = checkpoint['done'] + [query for query, ending in endings.items() if ending in (DONE, CAPPED)]
    unfinished = len(plan) - len(set(finished) & {query.id for query in plan})
    unparsed = sum(ending == UNPARSED for ending in endings.values())

    # A posting found again by this run's searches keeps its backlog history.
    cards = dict(backlog)
    for posting, card in search.cards.items():
        history = {field: backlog[posting][field] for field in ('tries', 'since')} if posting in backlog else {}
        cards[posting] = dict(card, **history)

    # Backlog entries that have waited too long are given up before any budget is spent on them.
    cutoff = (date.today() - timedelta(days=BACKLOG_DAYS)).isoformat()
    given_up = {posting for posting, card in backlog.items() if card['since'] < cutoff}
    order = _detail_order(cards.values(), known | set(rejected) | set(unreadable) | given_up, companies)
    budget = _budget(settings)
    if order and not guard.halted():
        logger.info('LinkedIn: reading up to %d of %d descriptions', min(budget, len(order)), len(order))
    details, unread, refused, failed, waiting = {}, 0, 0, 0, []
    for position, card in enumerate(order):
        if position >= budget or guard.halted():
            unread += 1
            waiting.append(card)
            continue
        if position and position % 50 == 0:
            logger.info('LinkedIn: %d descriptions read, %d rate-limited, %.1f minutes',
                        position, guard.throttled, guard.elapsed_minutes())
        response = http.get(DETAIL_URL + card['id'], accept=HTML)
        guard.note(response)
        walled = _walled(response)
        detail = parse_detail(response.text) if response.ok and not walled else None
        if detail and detail['description']:
            details[card['id']] = detail
        elif response.blocked or walled:
            # A sign-in page is a refusal, not a broken posting: it must not count towards "unreadable".
            refused += 1
            waiting.append(card)
        elif response.status in GONE_STATUSES:
            given_up.add(card['id'])
        else:
            # A failed load, or a page without the description markup: retried a few times.
            failed += not response.ok
            card['tries'] = card.get('tries', 0) + 1
            if card['tries'] >= BACKLOG_TRIES:
                given_up.add(card['id'])
            else:
                waiting.append(card)

    # The backlog must stay bounded even when descriptions are refused run after run: oldest out.
    waiting.sort(key=lambda card: card.get('since', today))
    given_up.update(card['id'] for card in waiting[:-BACKLOG_SIZE] if len(waiting) > BACKLOG_SIZE)
    next_backlog = {card['id']: {**{field: card[field] for field in CARD_FIELDS}, 'tries': card.get('tries', 0),
                                 'since': card.get('since', today)}
                    for card in waiting if card['id'] not in given_up}

    # A posting given up on is remembered so it is never queued again. One with a Pega title is still
    # returned from its card; one without is unverified and is only counted, never stored as a job.
    jobs = [job for job in (_to_job(card, details.get(card['id']), known, rejected, today)
                            for card in cards.values()) if job]
    unreadable.update({posting: today for posting in given_up if posting not in rejected})
    not_kept = sum(not cards[posting]['title_match'] and posting not in known for posting in given_up)

    def commit():
        store.kv_set(REJECTED_KEY, rejected)
        store.kv_set(UNREADABLE_KEY, unreadable)
        store.kv_set(BACKLOG_KEY, next_backlog)
        store.kv_set(CHECKPOINT_KEY, {'window_started': checkpoint['window_started'], 'done': finished,
                                      'capped': checkpoint['capped'] + capped} if unfinished else None)

    notes = []
    if unfinished:
        reason = (guard.why or guard.search_why or (search.errors[0] if search.errors else NO_CARDS if unparsed
                  else 'LinkedIn stopped answering' if not http.host_open(HOST) else 'the time budget ran out'))
        notes.append(f'{unfinished} of {len(plan)} searches not finished ({reason}); the next run resumes them')
    if capped:
        notes.append(f'{len(capped)} searches stopped at the page limit ({MAX_PAGES} pages or {RESULT_CAP} results) '
                     'with results left; a shorter look-back on the next run brings them back in range')
    if unread:
        notes.append(f'{unread} descriptions not read yet')
    if refused:
        notes.append(f'{refused} description requests were refused')
    if failed:
        notes.append(f'{failed} descriptions failed to load')
    if unfinished and not search.pages_read:
        # Nothing was searched. Only a refusal is "blocked"; timeouts, 5xx and unreadable pages are errors.
        status = 'blocked' if search.blocked else 'error'
    elif notes:
        status = 'partial'
    else:
        status = 'ok' if jobs else 'empty'
    # `sweep_complete`: every planned search ran to its end (or LinkedIn's limit), whatever happened
    # to the descriptions, so the orchestrator may shorten the next look-back.
    if not_kept:
        # Reported, but not a gap in this run: these pages will never load, so the status is unchanged.
        notes.append(f'{not_kept} description-only candidates could not be read and were not kept')
    result = make_result(SOURCE, SOURCE, 'linkedin', status=status, jobs=jobs, found=len(cards),
                         requests=http.count, error='; '.join(notes) or None, sweep_complete=not unfinished)
    return result, commit
