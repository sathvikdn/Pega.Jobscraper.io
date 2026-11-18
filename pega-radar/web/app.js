'use strict';

/* Pega Radar — single-page client. All job text is untrusted: it only ever reaches the page
   through text nodes and setAttribute, and links are limited to http(s). */

const SVG_NS = 'http://www.w3.org/2000/svg';
const PAGE_SIZE = 50;
const MAX_LIMIT = 500;                 // the server's page cap
const SEARCH_DEBOUNCE_MS = 250;
const NOTES_DEBOUNCE_MS = 700;
const NOTES_RETRY_MS = 3000;
const NOTES_RETRY_MAX_MS = 30000;
const MAX_FAILURES = 5;                // consecutive unanswered requests before "Disconnected"
const VIEWS = [['new', 'New roles'], ['all', 'All roles'], ['saved', 'Saved'], ['applied', 'Pipeline'], ['hidden', 'Hidden']];
const VIEW_COPY = {
  new: ['Fresh on your radar.', 'A closer look at the Pega roles worth your attention.'],
  all: ['Find your next move.', 'Compare the work, the expectations and the opportunity.'],
  saved: ['Your shortlist', 'The roles you want to come back to, across all locations and employers.'],
  applied: ['Your application pipeline', 'Keep track of each application and its next step.'],
  hidden: ['Hidden roles', 'Out of your way, still here whenever you need them.'],
  coverage: ['Employer coverage', 'See which employers are searched and where the gaps are.'],
  sources: ['Scan sources', 'Check what answered, what needs attention, and how fresh your results are.'],
};
const STATUSES = [['new', 'New'], ['interested', 'Interested'], ['applied', 'Applied'],
  ['interviewing', 'Interviewing'], ['offer', 'Offer'], ['rejected', 'Rejected']];
const SORTS = ['score', 'posted', 'first_seen'];
const TYPE_LABELS = {product: 'Product', gcc: 'GCC', enterprise: 'Enterprise', services: 'Services', staffing: 'Staffing', unknown: 'Unclassified'};
const READOUT = [['total', 'Roles on file'], ['new', 'Unread'], ['saved', 'Saved'], ['applied', 'In pipeline']];
const ATTENTION = ['partial', 'blocked', 'maintenance', 'skipped', 'error'];   // radar.model.needs_attention
const STATUS_TONE = {ok: 'good', empty: 'quiet', skipped: 'warn', partial: 'warn', maintenance: 'warn', blocked: 'bad', error: 'bad'};
const WIDE = {city: 'all', types: '', q: '', min_score: 0};
const MODE_LABELS = {full: 'Full scan', retry: 'Retry of incomplete sources'};
const CLOSED_TIP = 'Every employer site or job board that listed this role has re-read its full listing and no longer shows it. '
  + 'Roles seen only on LinkedIn are never flagged.';
const NOT_REACHED_LABEL = 'Not reached (time budget)';
const SOURCE_STATES = {not_reached: 'not reached'};
const NO_COVERAGE_FILTERS = {q: '', inventory: '', status: '', type: '', bengaluru: '', portal: ''};
/* [group, [[label, coverage filter that the tile counts and applies] or [label, null, summary key]]] */
const TILE_GROUPS = [
  ['Inventory', [['Original targets', null, 'original_rows'], ['Employers', null, 'employers'],
    ['Configured', {inventory: 'configured'}], ['Unverified portal', {portal: 'candidate'}],
    ['Not configured', {inventory: 'not configured'}], ['Unsupported', {inventory: 'unsupported'}],
    ['Wrong scope', {inventory: 'wrong scope only'}], ['Identity unresolved', {inventory: 'identity unresolved'}]]],
  ['Last scan', [['Attempted', null, 'attempted'], [NOT_REACHED_LABEL, {status: 'not_reached'}],
    ['Never attempted', {status: 'never'}]]],
  ['Latest outcome', [['OK', {status: 'ok'}], ['Empty', {status: 'empty'}], ['Partial', {status: 'partial'}],
    ['Blocked', {status: 'blocked'}], ['Maintenance', {status: 'maintenance'}], ['Error', {status: 'error'}],
    ['Skipped', {status: 'skipped'}]]],
];
/* Inventory gaps are facts about what is on file, never scan outcomes; they get their own (dashed) look. */
const INVENTORY_GAPS = {'not configured': ['Not configured', 'none'], unsupported: ['Unsupported portal', 'unsupported'],
  'wrong scope only': ['Wrong scope', 'scope'], 'identity unresolved': ['Identity unresolved', 'identity']};
const PORTAL_STATES = {verified: 'verified', candidate: 'unverified', wrong_scope: 'wrong scope', unsupported: 'unsupported'};
/* "Needs attention first": failures, then incomplete, never tried, inventory gaps, and healthy rows last. */
const COVERAGE_RANK = {blocked: 0, error: 0, maintenance: 0, partial: 1, skipped: 1, not_reached: 2, never: 2, gap: 3, empty: 4, ok: 5};
/* Outcomes "Retry incomplete sources" would run again. */
const RETRYABLE = ['partial', 'blocked', 'maintenance', 'error', 'skipped', 'not_reached', 'never'];
const NOTHING_TO_RETRY = 'Nothing to retry — every configured source answered in the latest scan';
const PEGA_TERMS = /\b(pega(?:systems|rules)?|prpc|cssa|csa|lsa|cpdc|cdh|customer decision hub|dev studio|app studio|constellation|case management|decisioning)\b/gi;
const ICONS = {
  new: 'M2 3h12v10H2zM2 9h3l1 2h4l1-2h3',
  all: 'M2.5 2.5h4v4h-4zM9.5 2.5h4v4h-4zM2.5 9.5h4v4h-4zM9.5 9.5h4v4h-4z',
  saved: 'M4 2h8v12l-4-2.5L4 14z',
  applied: 'M2.5 4.5h11v9h-11zM5.5 4.5v-2h5v2M2.5 8h11M7 8v2h2V8',
  hidden: 'M2 2l12 12M6.6 6.6a2 2 0 0 0 2.8 2.8M4.2 4.4C2.8 5.3 1.8 6.7 1.3 8c.9 2.3 3.4 4.5 6.7 4.5 1 0 2-.2 2.8-.6M7 3.6l1-.1c3.3 0 5.8 2.2 6.7 4.5-.3.8-.8 1.6-1.5 2.3',
  coverage: 'M8 1.5a6.5 6.5 0 1 0 6.5 6.5M8 4.5a3.5 3.5 0 1 0 3.5 3.5M8 8l5-5M11 2.5h3v3',
  sources: 'M2 3.5h12v3H2zM2 9.5h12v3H2zM4.5 5h.1M4.5 11h.1',
  location: 'M12.5 6.5c0 3-4.5 7-4.5 7s-4.5-4-4.5-7a4.5 4.5 0 1 1 9 0zM8 8a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z',
  star: 'M8 1.8l1.9 3.9 4.3.6-3.1 3 .7 4.3L8 11.6l-3.8 2 .7-4.3-3.1-3 4.3-.6z',
  hide: 'M2 2l12 12M6.6 6.6a2 2 0 0 0 2.8 2.8M4.2 4.4C2.8 5.3 1.8 6.7 1.3 8c.9 2.3 3.4 4.5 6.7 4.5 1 0 2-.2 2.8-.6M7 3.6l1-.1c3.3 0 5.8 2.2 6.7 4.5-.3.8-.8 1.6-1.5 2.3',
  show: 'M1.3 8C2.2 5.7 4.7 3.5 8 3.5s5.8 2.2 6.7 4.5c-.9 2.3-3.4 4.5-6.7 4.5S2.2 10.3 1.3 8zM8 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4z',
  external: 'M9 2.5h4.5V7M13.5 2.5l-6 6M6 4H3.5a1 1 0 0 0-1 1v7.5a1 1 0 0 0 1 1H11a1 1 0 0 0 1-1V10',
  copy: 'M5.5 5.5v-2a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1h-2M3.5 5.5h6a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1h-6a1 1 0 0 1-1-1v-6a1 1 0 0 1 1-1z',
  close: 'M3.5 3.5l9 9M12.5 3.5l-9 9',
};

/* ---------- preferences (applied before first paint: this script is loaded in <head>) ---------- */

function storedGet(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;   // storage unavailable: preferences simply do not persist
  }
}

function storedSet(key, value) {
  try {
    localStorage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

const darkQuery = window.matchMedia('(prefers-color-scheme: dark)');

function applyTheme() {
  const stored = storedGet('radar.theme');
  const manual = stored === 'light' || stored === 'dark';
  document.documentElement.dataset.theme = manual ? stored : (darkQuery.matches ? 'dark' : 'light');
}

function toggleTheme() {
  storedSet('radar.theme', document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
  applyTheme();
}

applyTheme();
darkQuery.addEventListener('change', applyTheme);

function loadFilters(key = 'radar.filters', focused = true) {
  let saved = null;
  try {
    saved = JSON.parse(storedGet(key));
  } catch {
    saved = null;
  }
  saved = saved && typeof saved === 'object' ? saved : {};
  return {
    bengaluru: typeof saved.bengaluru === 'boolean' ? saved.bengaluru : focused,
    focus: typeof saved.focus === 'boolean' ? saved.focus : focused,
    minScore: Math.min(100, Math.max(0, Number(saved.minScore) || 0)),
    sort: SORTS.includes(saved.sort) ? saved.sort : 'score',
    q: '',                                     // kept exactly as typed; trimmed only for the request
  };
}

function saveFilters() {
  const {bengaluru, focus, minScore, sort} = state.filters;
  const group = filterGroup(state.view);
  storedSet(group === 'discovery' ? 'radar.filters' : `radar.filters.${group}`, JSON.stringify({bengaluru, focus, minScore, sort}));
}

function filterGroup(view) {
  return ['saved', 'applied', 'hidden'].includes(view) ? view : 'discovery';
}

const filterSets = {
  discovery: loadFilters(),
  saved: loadFilters('radar.filters.saved', false),
  applied: loadFilters('radar.filters.applied', false),
  hidden: loadFilters('radar.filters.hidden', false),
};

/* ---------- state ---------- */

const state = {
  token: '',
  stats: {},
  profile: {},
  counts: {},                                  // per-view totals under the active filters
  latestRun: null,                             // the most recent run by itself: header and failure notice
  sourcesRun: null,                            // every source as of now: the last full run merged with later retries
  scan: {running: false},
  scanTimer: null,
  view: 'new',
  filters: filterSets.discovery,
  jobs: [],
  total: 0,
  outside: 0,
  loading: false,
  loadTicket: 0,
  cursor: -1,
  detail: null,
  detailTicket: 0,
  markingSeen: false,
};
const coverage = {
  loaded: false,
  rows: [],
  summary: {},
  filters: {...NO_COVERAGE_FILTERS},
  sort: 'attention',
};
const cards = new Map();                       // job id -> <li>
const pendingNotes = restoreNotes();            // drafts survive reloads until the server has saved them
const notesSync = {timer: null, delay: NOTES_RETRY_MS};
const connection = {failures: 0, offline: false};
let overviewTimer = null;
let searchTimer = null;
let sliderTimer = null;

/* ---------- small helpers ---------- */

const $ = (id) => document.getElementById(id);

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === null || value === undefined || value === false) continue;
    if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? '' : String(value));
  }
  node.append(...children.flat().filter(Boolean));   // drops null, false, '' and SQLite-style 0 flags
  return node;
}

function icon(name) {
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', '0 0 16 16');
  svg.setAttribute('width', '16');
  svg.setAttribute('height', '16');
  svg.setAttribute('class', 'icon');
  svg.setAttribute('aria-hidden', 'true');
  const path = document.createElementNS(SVG_NS, 'path');
  path.setAttribute('d', ICONS[name]);
  svg.append(path);
  return svg;
}

function safeUrl(url) {
  return typeof url === 'string' && /^https?:\/\//i.test(url) ? url : null;
}

function externalLink(url, props, ...children) {
  const href = safeUrl(url);
  return href ? el('a', {...props, href, target: '_blank', rel: 'noopener noreferrer'}, ...children) : null;
}

function plural(count, word) {
  return `${count} ${word}${count === 1 ? '' : 's'}`;
}

function ago(iso) {
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return '';
  const minutes = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  return daysLabel(Math.round(hours / 24));
}

function daysLabel(days) {
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 45) return `${days} d ago`;
  if (days < 365) return `${Math.round(days / 30)} mo ago`;
  return `${Math.round(days / 365)} y ago`;
}

/* posted_at is a calendar date (YYYY-MM-DD), so compare calendar days rather than instants. */
function postedAgo(day) {
  const parts = /^(\d{4})-(\d{2})-(\d{2})/.exec(day || '');
  if (!parts) return '';
  const now = new Date();
  const today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  return daysLabel(Math.round((today - Date.UTC(+parts[1], +parts[2] - 1, +parts[3])) / 86400000));
}

/* "09:41" for today, "13 Nov, 09:41" for any other day. */
function clockTime(iso) {
  const when = new Date(iso);
  if (Number.isNaN(when.getTime())) return '';
  const time = when.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
  const sameDay = when.toDateString() === new Date().toDateString();
  return sameDay ? time : `${when.toLocaleDateString([], {day: 'numeric', month: 'short'})}, ${time}`;
}

function range(low, high, prefix, unit) {
  const has = (value) => value !== null && value !== undefined && value !== '';
  if (has(low) && has(high) && Number(low) !== Number(high)) return `${prefix}${Number(low)}–${Number(high)} ${unit}`;
  if (has(low)) return `${prefix}${Number(low)}${has(high) ? '' : '+'} ${unit}`;
  if (has(high)) return `up to ${prefix}${Number(high)} ${unit}`;
  return null;
}

function scoreBand(score) {
  if (score >= 70) return 'high';
  return score >= 45 ? 'mid' : 'low';
}

/* The five job tabs share the list; Coverage and Sources are views of their own. */
function isJobView() {
  return VIEWS.some(([view]) => view === state.view);
}

function findJob(id) {
  return state.jobs.find((job) => job.id === id);
}

/* The list row and the open detail are separate objects for the same job. */
function copiesOf(id) {
  return [findJob(id), state.detail && state.detail.id === id ? state.detail : null].filter(Boolean);
}

function stateUrl(id) {
  return `/api/jobs/${encodeURIComponent(id)}/state`;
}

/* Replace a rendered node, keeping keyboard focus on the equivalent control. */
function swap(oldNode, newNode) {
  const active = document.activeElement;
  const role = oldNode.contains(active) ? active.dataset.role : null;
  oldNode.replaceWith(newNode);
  const target = role ? newNode.querySelector(`[data-role="${role}"]`) : null;
  if (target) target.focus();
}

/* ---------- API and connection state ---------- */

function connectionFailed() {
  connection.failures += 1;
  if (connection.failures < MAX_FAILURES || connection.offline) return;
  connection.offline = true;
  stopScanWatch();
  $('offline-strip').hidden = false;
}

function connectionOk() {
  connection.failures = 0;
  if (!connection.offline) return;
  connection.offline = false;
  $('offline-strip').hidden = true;
}

async function request(path, body) {
  const options = body === undefined ? {} : {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-Radar-Token': state.token},
    body: JSON.stringify(body),
    keepalive: true,
  };
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    connectionFailed();
    throw new Error('Pega Radar is not answering');
  }
  connectionOk();
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error((data && data.error) || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return data;
}

/* A restarted server issues a new token; fetch it once and retry instead of failing the action. */
async function api(path, body) {
  try {
    return await request(path, body);
  } catch (error) {
    if (body === undefined || error.status !== 403) throw error;
    await refreshOverview();
    return request(path, body);
  }
}

/* ---------- toasts ---------- */

function toast(message, {kind = 'info', actionLabel = null, onAction = null} = {}) {
  const node = el('div', {class: `toast toast-${kind}`}, el('span', {}, message));
  const life = actionLabel ? 10000 : (kind === 'error' ? 8000 : 5000);
  const dismiss = () => node.remove();
  let timer = setTimeout(dismiss, life);
  const pause = () => clearTimeout(timer);
  const resume = () => {
    clearTimeout(timer);
    timer = setTimeout(dismiss, life);
  };
  node.addEventListener('mouseenter', pause);
  node.addEventListener('focusin', pause);
  node.addEventListener('mouseleave', resume);
  node.addEventListener('focusout', resume);
  if (actionLabel) {
    node.append(el('button', {type: 'button', class: 'toast-action', onclick: () => { dismiss(); onAction(); }}, actionLabel));
  }
  placeToasts();
  $('toasts').append(node);
}

/* A modal dialog makes the rest of the page inert, so toasts live inside whichever dialog is open. */
function placeToasts() {
  const host = [$('help'), $('drawer')].find((dialog) => dialog.open) || document.body;
  if ($('toasts').parentNode !== host) host.append($('toasts'));
}

/* ---------- header: overview, tiles, attention, scan ---------- */

async function refreshOverview() {
  const data = await request('/api/bootstrap');
  state.token = data.token;
  state.stats = data.stats || {};
  state.profile = data.profile || {};
  state.latestRun = data.latest_run || null;
  state.sourcesRun = data.coverage_run || state.latestRun;
  state.scan = data.scan || {running: false};
  renderProfile(data.profile || {});
  renderScannedAt();
  renderReadout();
  renderAttention();
  renderTabs();
  renderScan();
  if (state.view === 'sources') renderSources();
}

function renderProfile(profile) {
  const node = $('profile-focus');
  if (!node) return;
  node.replaceChildren(
    el('div', {class: 'profile-person'}, el('span', {class: 'profile-avatar', 'aria-hidden': 'true'},
      String(profile.name || 'P').slice(0, 1).toUpperCase()),
    el('div', {}, el('strong', {}, profile.name || 'Your workspace'),
      el('p', {}, (profile.certifications || []).join(', ') || 'Pega developer'))),
    el('p', {class: 'profile-location'}, icon('location'), profile.city || 'India'),
    Number(profile.target_lpa) > 0 && el('p', {class: 'profile-target'}, `Target: ₹${Number(profile.target_lpa)} LPA+`));
}

/* requested / attempted / completed source counts of a scan, from its progress or its summary. */
function scanCounts(info) {
  if (!info || info.requested === undefined || info.requested === null) return '';
  const unreached = Array.isArray(info.not_attempted) ? info.not_attempted.length : Number(info.not_attempted) || 0;
  const missed = unreached ? ` · ${unreached} not reached` : '';
  return `${Number(info.requested) || 0} requested · ${Number(info.attempted) || 0} attempted · ${Number(info.completed) || 0} completed${missed}`;
}

/* After a change: refresh the tiles and the tab counts, but leave the list rows where they are. */
function scheduleOverview() {
  clearTimeout(overviewTimer);
  overviewTimer = setTimeout(() => {
    Promise.all([refreshOverview(), refreshCounts()]).catch((error) => toast(error.message, {kind: 'error'}));
  }, 400);
}

async function refreshCounts() {
  if (!isJobView()) return;
  const data = await api(jobsUrl({limit: 1}));
  state.counts = data.counts || {};
  renderTabs();
}

/* A run object carries null fields when every scan so far has failed; then there is nothing to show. */
function completedRun(run) {
  return run && run.id ? run : null;
}

/* The run the "Scanned …" line describes: the most recent one that actually attempted something.
   An empty retry no longer leaves a run behind, but an older database may still hold one. */
function headerRun() {
  const latest = completedRun(state.latestRun);
  const empty = latest && latest.summary && Number(latest.summary.requested) === 0;
  return empty ? completedRun(state.sourcesRun) : latest;
}

/* A source the time budget cut off was not attempted; it is never shown as an error or a skip. */
function healthStatus(row) {
  return row.reason === 'budget' ? 'not_reached' : row.status;
}

function failedAttempt() {
  const attempt = state.latestRun && state.latestRun.last_attempt;
  return attempt && attempt.status === 'failed' && attempt.id !== state.latestRun.id ? attempt : null;
}

function renderScannedAt() {
  const node = $('scanned-at');
  const detail = $('scan-detail');
  const run = headerRun();
  if (!run) {
    node.textContent = state.latestRun ? 'No completed scan yet' : 'No scan yet';
    if (detail) {
      detail.textContent = 'The first scan can take up to 40 minutes. You can keep using Radar while it runs.';
      detail.hidden = false;
    }
    node.removeAttribute('title');
    return;
  }
  const when = run.finished_at || run.started_at;
  const summary = run.summary || {};
  const counts = scanCounts(summary);
  node.textContent = `Scanned ${ago(when)}${run.status === 'partial' ? ' · ended partial' : ''}`;
  if (detail) {
    detail.textContent = counts ? `${MODE_LABELS[summary.mode] || 'Scan'}: ${counts}.` : '';
    detail.hidden = !counts;
  }
  node.title = new Date(when).toLocaleString();
}

function renderReadout() {
  $('readout').replaceChildren(...READOUT.map(([key, label]) => el('div', {class: 'readout-item'},
    el('dt', {}, label), el('dd', {}, String(Number(state.stats[key]) || 0)))));
  $('readout').hidden = !isJobView() || !Number(state.stats.total);
}

function attentionRows() {
  const health = (state.sourcesRun && state.sourcesRun.health) || [];
  return health.filter((row) => ATTENTION.includes(row.status));
}

function failedAttemptLine(attempt) {
  const reason = attempt.error ? `: ${attempt.error}` : '';
  const tail = completedRun(state.sourcesRun) ? ' — showing coverage from the previous scan.' : '. No scan has completed yet.';
  return el('p', {}, el('strong', {}, `The last scan at ${clockTime(attempt.finished_at)} failed`), `${reason}${tail}`);
}

function attentionLine(rows) {
  const named = rows.filter((row) => row.kind !== 'ats')
    .map((row) => `${row.label || row.source} (${healthStatus(row).replace('_', ' ')})`);
  const employers = rows.length - named.length;
  if (employers) named.push(plural(employers, 'employer site'));
  const list = named.length > 1 ? `${named.slice(0, -1).join(', ')} and ${named[named.length - 1]}` : named[0];
  return el('p', {}, el('strong', {}, 'Needs attention: '),
    `${list}. Roles from ${rows.length === 1 ? 'this source' : 'these sources'} may be missing. `,
    el('button', {type: 'button', class: 'link', onclick: () => setView('sources')}, 'See sources'));
}

function renderAttention() {
  const attempt = failedAttempt();
  const rows = attentionRows();
  const lines = [attempt && failedAttemptLine(attempt), rows.length > 0 && attentionLine(rows)].filter(Boolean);
  $('attention-strip').hidden = lines.length === 0;
  $('attention-strip').replaceChildren(...lines);
}

function renderScan() {
  const {running, progress} = state.scan;
  const nothingToRetry = !retryNeeded();
  $('scan-button').disabled = Boolean(running);
  $('retry-button').disabled = Boolean(running) || nothingToRetry;
  $('retry-button').hidden = !completedRun(state.sourcesRun) && !failedAttempt();
  $('retry-button').title = nothingToRetry ? NOTHING_TO_RETRY : 'Re-run only the sources that failed or were not reached';
  $('scan-button-label').textContent = running && state.scan.mode !== 'retry' ? 'Scanning…' : 'Full scan';
  $('retry-button').textContent = running && state.scan.mode === 'retry' ? 'Retrying…' : 'Retry incomplete sources';
  $('scan-progress').hidden = !running;
  if (isJobView() && !state.jobs.length && !state.loading) renderEmpty();
  if (!running) return;
  const info = progress && typeof progress === 'object' ? progress : {};
  const counts = scanCounts(info);
  const done = Number(counts ? info.attempted : info.done) || 0;
  const total = Number(counts ? info.requested : info.total) || 0;
  const fill = $('scan-progress-fill');
  fill.classList.toggle('is-indeterminate', total === 0);
  fill.style.width = total ? `${Math.min(100, Math.round((done / total) * 100))}%` : '';
  const parts = [MODE_LABELS[info.mode || state.scan.mode] || MODE_LABELS.full,
    counts || (total ? `${done} of ${plural(total, 'source')}` : 'Starting…')];
  const active = Array.isArray(info.running) ? info.running : [];
  if (active.length) parts.push(`${active.slice(0, 2).join(', ')}${active.length > 2 ? ` +${active.length - 2}` : ''}`);
  if (Number(info.new)) parts.push(`${Number(info.new)} new so far`);
  $('scan-progress-text').textContent = parts.join(' · ');
}

async function startScan(mode) {
  try {
    await api('/api/scan', {mode});
  } catch (error) {
    if (error.status !== 409) {
      toast(`Could not start the scan: ${error.message}`, {kind: 'error'});
      return;
    }
  }
  watchScan(mode);
}

function startFullScan() {
  return startScan('full');
}

function watchScan(mode = state.scan.mode) {
  if (state.scanTimer) return;
  state.scan = {...state.scan, running: true, mode};
  renderScan();
  state.scanTimer = setInterval(pollScan, 1500);
  pollScan();
}

function stopScanWatch() {
  clearInterval(state.scanTimer);
  state.scanTimer = null;
  state.scan = {running: false};
  renderScan();
}

async function pollScan() {
  let status;
  try {
    status = await request('/api/scan/status');
  } catch {
    return;   // the next tick tries again; request() gives up after MAX_FAILURES in a row
  }
  if (!state.scanTimer) return;
  state.scan = status;
  renderScan();
  if (status.running) return;
  clearInterval(state.scanTimer);
  state.scanTimer = null;
  const summary = status.last_summary || {};
  const idle = summary.status === 'nothing_to_retry' || (summary.mode === 'retry' && Number(summary.requested) === 0);
  if (!status.error && idle) {
    toast(`${NOTHING_TO_RETRY}.`);      // nothing ran, so the header, Sources and the lists stay exactly as they were
    return;
  }
  if (status.error) {
    toast(`Scan failed: ${status.error}`, {kind: 'error'});
  } else if (summary.status === 'failed') {
    toast('The scan stopped before it finished. See Sources for what was reached.', {kind: 'error'});
  } else {
    const fresh = Number(summary.new) || 0;
    const local = Number(summary.new_bengaluru) || 0;
    toast(fresh ? `Scan finished: ${plural(fresh, 'new role')}, ${local} in Bengaluru.` : 'Scan finished: nothing new.');
  }
  await refreshOverview().catch((error) => toast(error.message, {kind: 'error'}));
  loadCoverage();
  reloadJobs();
}

/* ---------- tabs and filters ---------- */

function renderTabs() {
  document.body.classList.toggle('is-welcome', isFirstUse());
  const focused = $('tabs').contains(document.activeElement) ? document.activeElement.dataset.view : null;
  const tab = (view, label, count, alert) => el('button', {
    type: 'button', class: `tab${['hidden', 'coverage', 'sources'].includes(view) ? ' utility-tab' : ''}`, 'data-view': view,
    'aria-controls': ['coverage', 'sources'].includes(view) ? `${view}-view` : 'jobs-view',
    'aria-current': state.view === view ? 'page' : null, onclick: () => setView(view),
  }, icon(view), el('span', {class: 'tab-label'}, label),
  count === null ? null : el('span', {class: `tab-count${alert ? ' is-alert' : ''}`, hidden: count === 0,
    title: alert ? 'Sources needing attention' : 'Across all locations and employers'}, String(count)));
  const attention = attentionRows().length + (failedAttempt() ? 1 : 0);
  const count = (view) => {
    const key = view === 'all' ? 'total' : view;
    return key in state.stats ? Number(state.stats[key]) || 0 : null;
  };
  $('tabs').replaceChildren(
    ...VIEWS.map(([view, label]) => tab(view, label, count(view), false)),
    el('span', {class: 'nav-group'}, 'Your radar'),
    tab('coverage', 'Employer coverage', null, false),
    tab('sources', 'Scan sources', attention || null, true));
  if (focused) {
    const replacement = $('tabs').querySelector(`[data-view="${focused}"]`);
    if (replacement) replacement.focus();
  }
  const [title, description] = VIEW_COPY[state.view] || VIEW_COPY.new;
  if ($('view-title')) $('view-title').textContent = title;
  if ($('view-description')) $('view-description').textContent = description;
}

function setView(view) {
  clearTimeout(searchTimer);
  clearTimeout(sliderTimer);
  state.loadTicket += 1;
  state.loading = false;
  state.view = view;
  state.filters = filterSets[filterGroup(view)];
  renderFilters();
  renderTabs();
  renderReadout();
  $('jobs-view').hidden = !isJobView();
  $('coverage-view').hidden = view !== 'coverage';
  $('sources-view').hidden = view !== 'sources';
  if (view === 'sources') renderSources();
  else if (view === 'coverage') loadCoverage();
  else loadJobs();
}

function isFiltered() {
  const filters = state.filters;
  return filters.bengaluru || filters.focus || filters.q.trim() !== '' || filters.minScore > 0;
}

function renderFilters() {
  const filters = state.filters;
  for (const button of $('filters').querySelectorAll('[data-filter]')) {
    const on = filters[button.dataset.filter] === (button.dataset.value === 'on');
    button.setAttribute('aria-pressed', String(on));
  }
  // Never rewrite the control in use: it would eat a space typed just before a pause, or yank the slider back.
  if (document.activeElement !== $('search')) $('search').value = filters.q;
  if (document.activeElement !== $('min-score')) $('min-score').value = String(filters.minScore);
  $('min-score-value').textContent = String(filters.minScore);
  $('sort').value = filters.sort;
  renderChips();
}

/* The active narrowing, always visible, each part removable on its own. */
function renderChips() {
  const filters = state.filters;
  const chip = (label, patch) => el('button', {type: 'button', class: 'chip', 'aria-label': `Remove filter: ${label}`,
    onclick: () => changeFilters(patch)}, label, el('span', {'aria-hidden': 'true'}, '×'));
  const chips = [
    filters.bengaluru && chip('Bengaluru', {bengaluru: false}),
    filters.focus && chip('Product + GCC', {focus: false}),
    filters.q.trim() && chip(`“${filters.q.trim()}”`, {q: ''}),
    filters.minScore > 0 && chip(`Fit ${filters.minScore}+`, {minScore: 0}),
  ].filter(Boolean);
  $('filter-chips').replaceChildren(...[
    el('span', {class: 'chips-label'}, chips.length ? 'Showing only' : 'No filters: all India, all employers.'),
    ...chips,
    chips.length > 0 && el('button', {type: 'button', class: 'link', onclick: widenFilters}, 'Clear all'),
  ].filter(Boolean));
}

function changeFilters(patch) {
  Object.assign(state.filters, patch);
  saveFilters();
  renderFilters();
  loadJobs();
}

function widenFilters() {
  changeFilters({bengaluru: false, focus: false, q: '', minScore: 0});
}

function bindFilters() {
  $('filters').addEventListener('click', (event) => {
    const button = event.target.closest('[data-filter]');
    if (button) changeFilters({[button.dataset.filter]: button.dataset.value === 'on'});
  });
  $('search').addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => changeFilters({q: $('search').value}), SEARCH_DEBOUNCE_MS);
  });
  $('min-score').addEventListener('input', () => {
    const minScore = Number($('min-score').value);     // captured now: another filter may re-render first
    $('min-score-value').textContent = String(minScore);
    clearTimeout(sliderTimer);
    sliderTimer = setTimeout(() => changeFilters({minScore}), SEARCH_DEBOUNCE_MS);
  });
  $('sort').addEventListener('change', () => changeFilters({sort: $('sort').value}));
}

/* ---------- job list ---------- */

function jobsUrl(overrides) {
  const filters = state.filters;
  return `/api/jobs?${new URLSearchParams({
    view: state.view,
    city: filters.bengaluru ? 'bengaluru' : 'all',
    types: filters.focus ? 'product,gcc' : '',
    q: filters.q.trim(),
    min_score: filters.minScore,
    sort: filters.sort,
    limit: PAGE_SIZE,
    offset: 0,
    ...overrides,
  })}`;
}

/* The first `count` rows of the current view, in as many requests as the server's page cap needs. */
async function fetchRows(count) {
  const first = await api(jobsUrl({limit: Math.min(count, MAX_LIMIT)}));
  const jobs = first.jobs;
  while (jobs.length < Math.min(count, first.total)) {
    const more = await api(jobsUrl({limit: MAX_LIMIT, offset: jobs.length}));
    if (!more.jobs.length) break;
    jobs.push(...more.jobs);
  }
  return {...first, jobs: jobs.slice(0, count)};
}

/* Always loads from the top of the view. Rows can leave a view when their state changes, so paging
   by offset from the rows already on screen would skip some; re-reading the first `count` cannot.
   `keep` preserves the scroll position and the keyboard cursor. Returns false when the load failed. */
async function loadJobs({count = PAGE_SIZE, keep = false} = {}) {
  if (!isJobView()) return true;
  const ticket = ++state.loadTicket;
  state.loading = true;
  $('jobs-view').setAttribute('aria-busy', 'true');
  $('result-line').textContent = state.jobs.length ? 'Updating roles…' : 'Loading roles…';
  $('load-more').disabled = true;
  $('seen-all').disabled = true;
  $('empty').hidden = true;
  try {
    const [page, wide] = await Promise.all([
      fetchRows(count),
      isFiltered() ? api(jobsUrl({...WIDE, limit: 1})) : null,
    ]);
    if (ticket !== state.loadTicket) return true;
    const cursorJob = keep ? state.jobs[state.cursor] : null;
    const scrollY = window.scrollY;
    state.jobs = page.jobs;
    state.total = page.total;
    state.counts = page.counts || {};
    state.outside = wide ? Math.max(0, wide.total - page.total) : 0;
    state.cursor = -1;
    cards.clear();
    $('list').replaceChildren(...state.jobs.map(renderCard));
    renderTabs();
    renderListChrome();
    if (keep) {
      window.scrollTo(0, scrollY);
      if (cursorJob) setCursor(state.jobs.findIndex((job) => job.id === cursorJob.id), false);
    }
    return true;
  } catch (error) {
    if (ticket !== state.loadTicket) return true;
    $('list').replaceChildren();
    state.jobs = [];
    cards.clear();
    $('load-more').hidden = true;
    $('seen-all').hidden = true;
    $('result-line').textContent = 'Roles could not be loaded.';
    showEmpty('Could not load these roles', `${error.message}. Try again to see results for the current filters.`,
      'Try again', () => loadJobs());
    return false;
  } finally {
    if (ticket === state.loadTicket) {
      state.loading = false;
      $('jobs-view').setAttribute('aria-busy', 'false');
      $('load-more').disabled = false;
      $('seen-all').disabled = state.markingSeen;
    }
  }
}

function reloadJobs() {
  return loadJobs({count: Math.max(PAGE_SIZE, state.jobs.length), keep: true});
}

function loadMore() {
  return loadJobs({count: state.jobs.length + PAGE_SIZE, keep: true});
}

function renderListChrome() {
  $('jobs-view').classList.toggle('is-first-run', isFirstUse());
  const line = $('result-line');
  line.replaceChildren(isFiltered() ? `${plural(state.total, 'role')} match${state.total === 1 ? 'es' : ''}` : plural(state.total, 'role'));
  if (state.outside > 0) {
    line.append(` · ${state.outside} more outside these filters — `,
      el('button', {type: 'button', class: 'link', onclick: widenFilters}, 'show all'));
  }
  $('seen-all').hidden = state.view !== 'new' || state.jobs.length === 0;
  const unread = state.jobs.filter((job) => job.is_new);
  $('seen-all').textContent = `Mark these ${unread.length} as read`;
  $('seen-all').title = 'Only the unread roles currently loaded in this list will be marked as read';
  $('seen-all').hidden = state.view !== 'new' || unread.length === 0;
  $('load-more').hidden = state.jobs.length >= state.total;
  renderEmpty();
}

function emptyState() {
  if (state.outside > 0) {
    return ['Nothing matches these filters',
      `${plural(state.outside, 'role')} in this view ${state.outside === 1 ? 'is' : 'are'} outside them.`,
      `Show all ${state.outside}`, widenFilters];
  }
  switch (state.view) {
    case 'saved':
      return ['Keep your next move in sight', 'Save a role using its star. Your shortlist stays here while you explore.',
        'Explore roles', () => setView('all')];
    case 'applied':
      return ['Your next chapter starts with a role',
        'When you apply, change the role’s status to Applied. Track interviews, offers and outcomes here.',
        'Explore roles', () => setView('all')];
    case 'hidden':
      return ['Nothing hidden', 'Roles you hide are kept here. You can restore them at any time.',
        'Explore roles', () => setView('all')];
  }
  if (state.scan.running) {
    return ['Your radar is searching', 'You can keep browsing while the scan runs. New results appear here when it finishes.',
      'View scan sources', () => setView('sources')];
  }
  if (!completedRun(state.latestRun) && !Number(state.stats.total)) {
    return ['Find your next Pega opportunity',
      'Search employer career sites and job boards in one place. Your first scan can take up to 40 minutes; you can keep using Radar while it runs.',
      'Run your first scan', startFullScan];
  }
  switch (state.view) {
    case 'new':
      return ['Inbox clear', 'Unread roles stay here for 14 days. Revisit everything found so far in All roles.',
        'Explore all roles', () => setView('all')];
    default:
      return ['No roles found', 'Run a scan to look again.', 'Full scan', startFullScan];
  }
}

function showEmpty(title, text, actionLabel, action) {
  $('empty').hidden = false;
  $('empty').classList.remove('welcome');
  $('empty').replaceChildren(el('div', {class: 'empty-art', 'aria-hidden': 'true'}, icon('coverage')),
    el('h2', {}, title), el('p', {}, text),
    actionLabel && el('button', {type: 'button', class: 'btn btn-primary', onclick: action}, actionLabel));
}

function renderEmpty() {
  $('empty').hidden = state.jobs.length > 0;
  if (!state.jobs.length) {
    if (isFirstUse()) showWelcome(...emptyState());
    else showEmpty(...emptyState());
  }
}

function isFirstUse() {
  return Boolean(state.token) && !Number(state.stats.total) && !completedRun(state.latestRun)
    && ['new', 'all'].includes(state.view);
}

function showWelcome(title, text, actionLabel, action) {
  const profile = state.profile;
  const brief = (label, value) => el('div', {}, el('dt', {}, label), el('dd', {}, value));
  const template = $('onboard-art');
  const art = template && template.content ? template.content.cloneNode(true)
    : el('div', {class: 'empty-art', 'aria-hidden': 'true'}, icon('coverage'));
  if (state.scan.running && template && template.content) {
    art.querySelector('.ready-label').replaceChildren(el('span'), 'Searching sources');
    art.querySelector('.signal-art').setAttribute('aria-label',
      'Pega Radar is searching employer career sites, LinkedIn and India job boards.');
  }
  $('empty').hidden = false;
  $('empty').classList.add('welcome');
  $('empty').replaceChildren(
    el('div', {class: 'welcome-copy'},
      el('h1', {}, state.scan.running ? 'Your radar is searching' : 'Pega roles.\nOn your terms.'),
      el('p', {class: 'welcome-intro'}, state.scan.running
        ? 'Keep exploring while your sources are checked. New roles appear here when the scan finishes.'
        : 'Employer career sites, LinkedIn and India job boards. Brought together for your next move.'),
      el('dl', {class: 'search-brief', 'aria-label': 'Your search brief'},
        brief('Location first', profile.city || 'Bengaluru'),
        brief('Employer focus', 'Product + GCC'),
        brief('Certification', (profile.certifications || []).join(', ') || 'Pega developer'),
        Number(profile.target_lpa) > 0 && brief('Your salary target', `₹${Number(profile.target_lpa)} LPA+`)),
      el('div', {class: 'welcome-actions'},
        actionLabel && el('button', {type: 'button', class: 'btn btn-primary', onclick: action},
          icon(state.scan.running ? 'sources' : 'coverage'), actionLabel),
        el('button', {type: 'button', class: 'link', onclick: () => setView('coverage')}, 'Explore coverage')),
      el('p', {class: 'welcome-note'}, 'Runs on your device. Your first scan can take up to 40 minutes; you can keep using Radar while it runs.')),
    art);
}

function employerBadge(job) {
  const type = TYPE_LABELS[job.employer_type] ? job.employer_type : 'unknown';
  return el('span', {class: `badge type-${type}`}, TYPE_LABELS[type]);
}

function metaItems(job) {
  const posted = postedAgo(job.posted_at);
  return [
    el('span', {class: job.is_bengaluru ? 'loc is-bengaluru' : 'loc'}, job.location || job.city || 'Location not stated'),
    range(job.experience_min, job.experience_max, '', 'yrs'),
    range(job.salary_min_lpa, job.salary_max_lpa, '₹', 'LPA'),
    posted ? `Posted ${posted}` : `Found ${ago(job.first_seen_at)}`,
  ].filter(Boolean).map((item) => (typeof item === 'string' ? el('span', {}, item) : item));
}

function closedMark(job) {
  if (!job.possibly_closed) return null;
  const confirmed = job.last_confirmed_at ? ` Last confirmed ${ago(job.last_confirmed_at)}.` : '';
  return el('span', {class: 'badge closed-mark', title: CLOSED_TIP + confirmed}, 'Possibly closed');
}

function scoreChip(job) {
  const score = Math.round(Number(job.score) || 0);
  return el('span', {class: `score score-${scoreBand(score)}`,
    'aria-label': `Fit score ${score} of 100. A relevance ranking, not a hiring probability.`,
    title: 'A relevance ranking out of 100, not a hiring probability'},
    String(score), el('span', {class: 'score-label'}, 'Fit'));
}

function saveButton(job, withLabel) {
  return el('button', {
    type: 'button', class: `btn btn-quiet star${job.saved ? ' is-on' : ''}`, 'data-role': 'save',
    'aria-pressed': String(Boolean(job.saved)), 'aria-label': withLabel ? null : `${job.saved ? 'Unsave' : 'Save'} ${job.title || 'role'}`,
    title: job.saved ? 'Remove from saved (s)' : 'Save role (s)', onclick: () => toggleSaved(job),
  }, icon('star'), withLabel && (job.saved ? 'Saved' : 'Save'));
}

function statusSelect(job) {
  const select = el('select', {class: 'status-select', 'data-role': 'status', 'aria-label': `Application status for ${job.title || 'role'}`,
    onchange: async () => {
      if (await updateState(job.id, {status: select.value})) {
        toast(`Status updated to ${STATUSES.find(([value]) => value === select.value)[1]}.`);
        if (state.view === 'applied' || state.view === 'new' || select.value === 'rejected') reloadJobs();
      }
    }},
  STATUSES.map(([value, label]) => el('option', {value}, label)));
  select.value = job.status || 'new';
  return select;
}

function hideButton(job, withLabel) {
  const label = job.hidden ? 'Restore' : 'Hide';
  return el('button', {type: 'button', class: 'btn btn-quiet', 'data-role': 'hide', 'aria-label': withLabel ? null : label,
    title: `${label} (x)`, onclick: () => toggleHidden(job)}, icon(job.hidden ? 'show' : 'hide'), withLabel && label);
}

const CAUTION_REASON = /not a developer|not read|only mentioned|not stated|stretch|lead or architect|junior|advertised only|stale|current employer|capped at/i;

function visibleReasons(job) {
  const reasons = (job.fit && job.fit.reasons) || [];
  return [...reasons.filter((reason) => CAUTION_REASON.test(reason)),
    ...reasons.filter((reason) => !CAUTION_REASON.test(reason))].slice(0, 3);
}

function cardFacts(job) {
  const fact = (label, value) => el('div', {}, el('dt', {}, label), el('dd', {}, value));
  return el('dl', {class: 'job-facts'},
    fact('Location', job.city || job.location || 'Not specified'),
    fact('Experience', range(job.experience_min, job.experience_max, '', 'years') || 'Not specified'),
    fact('Salary', range(job.salary_min_lpa, job.salary_max_lpa, '₹', 'LPA') || 'Not listed'));
}

function renderCard(job) {
  const reasons = visibleReasons(job);
  const posted = postedAgo(job.posted_at);
  const card = el('li', {class: `job band-${scoreBand(Number(job.score) || 0)}`, onclick: (event) => {
    if (event.target.closest('button, a, select')) return;
    openJob(job.id);
  }},
  el('div', {class: 'job-top'},
    el('span', {class: `company-avatar avatar-${job.employer_type || 'unknown'}`, 'aria-hidden': 'true'},
      (job.company || '?').trim().split(/\s+/).slice(0, 2).map((word) => word[0]).join('').toUpperCase()),
    el('div', {class: 'job-company'}, el('span', {class: 'company'}, job.company || 'Unknown employer'), employerBadge(job)),
    job.is_new && el('span', {class: 'new-mark'}, 'New')),
  el('div', {class: 'job-main'},
    el('div', {class: 'job-head'},
      el('button', {type: 'button', class: 'job-title', 'data-role': 'title',
        title: job.title || 'Untitled role', onclick: () => openJob(job.id)}, job.title || 'Untitled role'),
      closedMark(job),
      job.notes && el('span', {class: 'badge note-mark'}, 'Notes')),
    cardFacts(job),
    reasons.length > 0 && el('ul', {class: 'job-reasons'},
      reasons.map((reason) => el('li', {class: CAUTION_REASON.test(reason) ? 'is-caution' : null}, reason)))),
  el('div', {class: 'job-source'},
    el('span', {}, (job.sources || []).join(', ')),
    el('span', {}, posted ? `Posted ${posted}` : `Found ${ago(job.first_seen_at)}`)),
  el('div', {class: 'job-side'}, el('div', {class: 'job-score'}, scoreChip(job)),
    el('div', {class: 'job-actions'}, saveButton(job, true), statusSelect(job), hideButton(job, false))));
  cards.set(job.id, card);
  return card;
}

function refreshJob(id) {
  const job = findJob(id);
  const old = cards.get(id);
  if (job && old) {
    const cursor = old.classList.contains('is-cursor');
    swap(old, renderCard(job));
    cards.get(id).classList.toggle('is-cursor', cursor);
  }
  if (state.detail && state.detail.id === id && $('drawer-actions')) {
    swap($('drawer-actions'), detailActions(state.detail));
  }
}

function setCursor(index, scroll = true) {
  const previous = state.jobs[state.cursor];
  if (previous && cards.has(previous.id)) cards.get(previous.id).classList.remove('is-cursor');
  state.cursor = index;
  const job = state.jobs[index];
  if (!job) return;
  const card = cards.get(job.id);
  card.classList.add('is-cursor');
  if (scroll) card.scrollIntoView({block: 'nearest'});
}

function moveCursor(delta) {
  if (!state.jobs.length) return;
  setCursor(Math.min(state.jobs.length - 1, Math.max(0, state.cursor + delta)));
  if ($('drawer').open) openJob(state.jobs[state.cursor].id);
  else cards.get(state.jobs[state.cursor].id).querySelector('[data-role="title"]').focus({preventScroll: true});
}

/* ---------- saving state: optimistic, rolled back on failure ---------- */

async function updateState(id, patch) {
  const targets = copiesOf(id);
  const before = targets.map((job) => Object.fromEntries(Object.keys(patch).map((key) => [key, job[key]])));
  targets.forEach((job) => Object.assign(job, patch));
  refreshJob(id);
  try {
    const result = await api(stateUrl(id), patch);
    // Saving or advancing a role also marks it read on the server.
    if (result && result.seen) {
      targets.forEach((job) => Object.assign(job, {seen: true, is_new: false}));
      refreshJob(id);
      if (isJobView()) renderListChrome();
    }
    scheduleOverview();
    return true;
  } catch (error) {
    targets.forEach((job, index) => Object.assign(job, before[index]));
    refreshJob(id);
    toast(`Not saved: ${error.message}`, {kind: 'error'});
    return false;
  }
}

async function toggleSaved(job) {
  const saved = !job.saved;
  if (!(await updateState(job.id, {saved}))) return;
  toast(saved ? 'Added to your shortlist.' : 'Removed from your shortlist.');
  if (state.view === 'saved') reloadJobs();
}

/* Hiding is its own flag and never touches the status. The row leaves the view straight away. */
async function setHidden(job, hidden) {
  const {id, title} = job;
  const index = state.jobs.findIndex((item) => item.id === id);
  if (!(await updateState(id, {hidden}))) return;
  if (index >= 0) {
    await reloadJobs();
    setCursor(Math.min(index, state.jobs.length - 1), false);
  }
  if ($('drawer').open && state.detail && state.detail.id === id) {
    const next = index >= 0 ? state.jobs[state.cursor] : null;
    if (next && next.id !== id) openJob(next.id);
    else $('drawer').close();
  }
  toast(`${hidden ? 'Hidden' : 'Restored'}: ${title || 'role'}`, {actionLabel: 'Undo', onAction: async () => {
    if (await updateState(id, {hidden: !hidden})) reloadJobs();
  }});
}

function toggleHidden(job) {
  setHidden(job, !job.hidden);
}

/* Opening a role takes it out of the "new" inbox. The card keeps its place until the next reload. */
function markSeen(job) {
  if (job.seen) return;
  const targets = copiesOf(job.id);
  const previous = targets.map((copy) => ({seen: copy.seen, is_new: copy.is_new}));
  targets.forEach((copy) => Object.assign(copy, {seen: true, is_new: false}));
  refreshJob(job.id);
  renderListChrome();
  api(stateUrl(job.id), {seen: true}).then(scheduleOverview, () => {
    targets.forEach((copy, index) => Object.assign(copy, previous[index]));
    refreshJob(job.id);
    renderListChrome();
  });
}

async function markAllSeen() {
  if (state.markingSeen || state.loading) return;
  const unread = state.jobs.filter((job) => job.is_new).map((job) => job.id);
  state.markingSeen = true;
  $('seen-all').disabled = true;
  let marked = 0;
  const queue = [...unread];
  await Promise.all(Array.from({length: Math.min(5, queue.length)}, async () => {
    while (queue.length) {
      const id = queue.shift();
      try {
        await api(stateUrl(id), {seen: true});
        marked += 1;
      } catch { /* Keep failed items unread; report the total below. */ }
    }
  }));
  state.markingSeen = false;
  $('seen-all').disabled = false;
  toast(marked === unread.length ? `${plural(marked, 'role')} marked as read.`
    : `${marked} of ${unread.length} marked as read. The rest are still unread; try again.`,
  {kind: marked === unread.length ? 'info' : 'error'});
  scheduleOverview();
  loadJobs();
}

/* ---------- detail drawer ---------- */

function hashJobId() {
  const match = /^#job=(.+)$/.exec(location.hash);
  if (!match) return null;
  try {
    return decodeURIComponent(match[1]);
  } catch {
    return null;
  }
}

/* Moving between roles inside the open drawer replaces the history entry, so Back closes it. */
function openJob(id) {
  const hash = `#job=${encodeURIComponent(id)}`;
  if ($('drawer').open) location.replace(hash);
  else location.hash = hash;
}

async function syncDrawer() {
  const id = hashJobId();
  const drawer = $('drawer');
  flushNotes();
  if (!id) {
    if (drawer.open) drawer.close();
    return;
  }
  if (state.detail && state.detail.id === id) return;
  const ticket = ++state.detailTicket;
  if (!drawer.open) {
    $('drawer-body').replaceChildren(drawerMessage('Loading…'));
    drawer.showModal();
  }
  try {
    const job = await api(`/api/jobs/${encodeURIComponent(id)}`);
    if (ticket !== state.detailTicket) return;
    state.detail = job;
    renderDetail(job);
    const index = state.jobs.findIndex((item) => item.id === id);
    if (index >= 0) setCursor(index);
    markSeen(job);
  } catch (error) {
    if (ticket !== state.detailTicket) return;
    state.detail = null;
    $('drawer-body').replaceChildren(drawerMessage(
      error.status === 404 ? 'This role is no longer in the database.' : `Could not load this role: ${error.message}`));
  }
  $('drawer-title').focus();
}

function onDrawerClosed() {
  flushNotes();
  const id = state.detail && state.detail.id;
  state.detail = null;
  state.detailTicket += 1;
  if (hashJobId()) history.replaceState(null, '', location.pathname + location.search);
  const next = state.jobs[state.cursor] || state.jobs[0];
  const card = cards.get(id) || cards.get(next && next.id);
  if (card) card.querySelector('[data-role="title"]').focus({preventScroll: true});
  else if ($('main-content')) $('main-content').focus({preventScroll: true});
}

function closeButton() {
  return el('button', {type: 'button', class: 'btn btn-quiet drawer-close', 'aria-label': 'Close', title: 'Close (Esc)',
    onclick: () => $('drawer').close()}, icon('close'));
}

function drawerTitle(text) {
  return el('h2', {id: 'drawer-title', tabindex: -1}, text);
}

function drawerMessage(text) {
  return el('div', {class: 'drawer-message'}, closeButton(), drawerTitle(text));
}

function highlighted(text) {
  const fragment = document.createDocumentFragment();
  let last = 0;
  for (const match of text.matchAll(PEGA_TERMS)) {
    fragment.append(text.slice(last, match.index), el('mark', {}, match[0]));
    last = match.index + match[0].length;
  }
  fragment.append(text.slice(last));
  return fragment;
}

function detailActions(job) {
  const target = safeUrl(job.apply_url) || safeUrl(job.url);
  return el('div', {class: 'drawer-actions', id: 'drawer-actions'},
    externalLink(target, {class: 'btn btn-primary', 'data-role': 'apply'},
      safeUrl(job.apply_url) ? 'Apply on employer site' : 'Open posting', icon('external')),
    saveButton(job, true),
    statusSelect(job),
    target && el('button', {type: 'button', class: 'btn btn-quiet', 'data-role': 'copy', onclick: () => copyLink(target)},
      icon('copy'), 'Copy link'),
    hideButton(job, true));
}

async function copyLink(url) {
  try {
    await navigator.clipboard.writeText(url);
    toast('Link copied.');
  } catch {
    toast('Could not copy the link — the browser refused clipboard access.', {kind: 'error'});
  }
}

function fitSection(job) {
  const fit = job.fit || {};
  const reasons = fit.reasons || [];
  const labels = Object.entries(fit.labels || {}).filter(([, value]) => typeof value === 'string' && value);
  if (!reasons.length && !labels.length) return null;
  return el('section', {class: 'drawer-section'},
    el('h3', {}, 'How this role matches'),
    el('p', {class: 'fit-explanation muted'}, 'Fit ranks relevance to your search. It is not a hiring probability.'),
    reasons.length > 0 && el('ul', {class: 'reasons'}, reasons.map((reason) => el('li', {}, reason))),
    labels.length > 0 && el('p', {class: 'fit-labels'},
      labels.map(([key, value]) => el('span', {class: 'badge'}, `${key.replace(/_/g, ' ')}: ${value}`))));
}

function sightingsSection(job) {
  const rows = (job.sightings || []).map((sighting) => {
    const name = sighting.label && sighting.label !== sighting.source ? `${sighting.source} · ${sighting.label}` : sighting.source;
    const seen = `first seen ${ago(sighting.first_seen_at)}, last seen ${ago(sighting.last_seen_at)}`;
    return el('li', {}, externalLink(sighting.url, {}, name, icon('external')) || el('span', {}, name), el('span', {class: 'muted'}, seen));
  });
  return rows.length ? el('section', {class: 'drawer-section'}, el('h3', {}, 'Where it was found'), el('ul', {class: 'sightings'}, rows)) : null;
}

function notesSection(job) {
  const unsaved = pendingNotes.get(job.id);
  const status = el('span', {class: 'notes-status', id: 'notes-status', role: 'status'}, unsaved && 'Not saved yet');
  const box = el('textarea', {id: 'notes', rows: 4, maxlength: 5000, placeholder: 'Recruiter, referral, salary discussed, next step…',
    oninput: () => queueNotes(job.id, box.value)});
  box.value = unsaved ? unsaved.value : (job.notes || '');
  return el('section', {class: 'drawer-section'},
    el('div', {class: 'notes-head'}, el('h3', {}, el('label', {for: 'notes'}, 'Notes')), status), box);
}

function descriptionSection(job) {
  const paragraphs = (job.description || '').split(/\n\s*\n|\n/).map((text) => text.trim()).filter(Boolean);
  return el('section', {class: 'drawer-section'},
    el('h3', {}, 'Description'),
    paragraphs.length
      ? el('div', {class: 'description'}, paragraphs.map((text) => el('p', {}, highlighted(text))))
      : el('p', {class: 'muted'}, 'The description has not been read yet — open the posting to see it.'));
}

function renderDetail(job) {
  $('drawer-body').replaceChildren(...[
    el('header', {class: 'drawer-head'},
      closeButton(),
      el('div', {class: 'drawer-title-row'}, scoreChip(job), drawerTitle(job.title || 'Untitled role')),
      el('div', {class: 'job-company'}, el('span', {class: 'company'}, job.company || 'Unknown employer'), employerBadge(job)),
      el('div', {class: 'job-meta'}, metaItems(job), job.posted_at && el('span', {}, `Found ${ago(job.first_seen_at)}`),
        job.last_confirmed_at && el('span', {}, `Last confirmed ${ago(job.last_confirmed_at)}`)),
      job.possibly_closed && el('p', {class: 'closed-note'}, el('strong', {}, 'Possibly closed. '), CLOSED_TIP,
        ' Open the posting to check.')),
    detailActions(job),
    fitSection(job),
    descriptionSection(job),
    notesSection(job),
    sightingsSection(job),
  ].filter(Boolean));
  $('drawer-body').scrollTop = 0;
}

/* ---------- notes autosave: text stays queued until the server has it ---------- */

function restoreNotes() {
  try {
    const values = JSON.parse(storedGet('radar.note-drafts')) || {};
    return new Map(Object.entries(values).filter(([, value]) => typeof value === 'string')
      .map(([id, value]) => [id, {value: value.slice(0, 5000), sending: false, warned: false, durable: true}]));
  } catch {
    return new Map();
  }
}

function persistNotes() {
  const saved = storedSet('radar.note-drafts', JSON.stringify(Object.fromEntries(
    [...pendingNotes].map(([id, entry]) => [id, entry.value]))));
  pendingNotes.forEach((entry) => { entry.durable = saved; });
  return saved;
}

function setNotesStatus(id, text) {
  const node = $('notes-status');
  if (node && state.detail && state.detail.id === id) node.textContent = text;
}

/* A surrogate pair cut in half by the length limit cannot be encoded; drop the stray half. */
function sendableNotes(value) {
  return value.replace(/[\uD800-\uDBFF]$/, '');
}

function scheduleNotes(delay) {
  clearTimeout(notesSync.timer);
  notesSync.timer = setTimeout(flushNotes, delay);
}

function queueNotes(id, value) {
  const entry = pendingNotes.get(id) || {value, sending: false, warned: false};
  entry.value = value;
  pendingNotes.set(id, entry);
  persistNotes();
  setNotesStatus(id, 'Saving…');
  scheduleNotes(NOTES_DEBOUNCE_MS);
}

async function saveNotes(id, entry) {
  const value = entry.value;
  entry.sending = true;
  try {
    await api(stateUrl(id), {notes: sendableNotes(value)});
  } catch (error) {
    setNotesStatus(id, 'Not saved — retrying');
    if (!entry.warned) {
      entry.warned = true;
      toast(`Notes not saved yet (${error.message}). ${entry.durable
        ? 'A draft is saved in this browser and will be retried.'
        : 'Keep this tab open until they finish saving.'}`, {kind: 'error'});
    }
    return false;
  } finally {
    entry.sending = false;
  }
  copiesOf(id).forEach((job) => { job.notes = value; });
  refreshJob(id);
  if (entry.value === value) {
    pendingNotes.delete(id);
    persistNotes();
    setNotesStatus(id, 'Saved');
  }
  return true;
}

/* Sends everything queued. A failed save stays queued and is retried with a growing delay, on the
   next keystroke, and whenever the drawer closes or moves to another role. */
async function flushNotes() {
  clearTimeout(notesSync.timer);
  const waiting = [...pendingNotes].filter(([, entry]) => !entry.sending);
  const results = await Promise.all(waiting.map(([id, entry]) => saveNotes(id, entry)));
  if (results.includes(false)) {
    scheduleNotes(notesSync.delay);
    notesSync.delay = Math.min(notesSync.delay * 2, NOTES_RETRY_MAX_MS);
  } else {
    notesSync.delay = NOTES_RETRY_MS;
    if (pendingNotes.size) scheduleNotes(NOTES_DEBOUNCE_MS);   // typed again while a save was in flight
  }
}

/* ---------- sources ---------- */

function statusPill(status, text) {
  if (status === 'not_reached') return el('span', {class: 'pill pill-gap gap-unreached'}, text || NOT_REACHED_LABEL);
  return el('span', {class: `pill pill-${STATUS_TONE[status] || 'quiet'}`}, text || status);
}

function sourceRow(name, pill, found, kept, note) {
  return el('tr', {}, el('th', {scope: 'row'}, name), el('td', {}, pill),
    el('td', {class: 'num'}, String(found)), el('td', {class: 'num'}, String(kept)), el('td', {class: 'note'}, note || ''));
}

function employerRow(sites) {
  const answered = sites.filter((row) => row.status === 'ok' || row.status === 'empty').length;
  const unanswered = sites.length - answered;
  const sum = (key) => sites.reduce((total, row) => total + (Number(row[key]) || 0), 0);
  return sourceRow('Employer sites', statusPill(unanswered ? 'partial' : 'ok', `${answered} of ${sites.length} answered`),
    sum('found'), sum('kept'), unanswered ? `${unanswered} skipped or failed — listed below` : '');
}

function employerList(title, rows, describe, open) {
  if (!rows.length) return null;
  return el('details', {class: 'employer-list', open},
    el('summary', {}, `${title} (${rows.length})`),
    el('ul', {}, rows.map((row) => el('li', {}, el('span', {}, row.label || row.source), describe(row)))));
}

function renderSources() {
  const view = $('sources-view');
  const run = completedRun(state.sourcesRun);
  const attempt = failedAttempt();
  if (!run) {
    view.replaceChildren(el('div', {class: 'empty'},
      el('h2', {}, attempt ? 'No scan has completed yet' : 'No scan yet'),
      el('p', {}, attempt ? `The last attempt failed${attempt.error ? `: ${attempt.error}` : '.'}`
        : 'Run your first scan to see which sources answered.'),
      el('button', {type: 'button', class: 'btn btn-primary', onclick: startFullScan}, attempt ? 'Scan again' : 'Run your first scan')));
    return;
  }
  const health = run.health || [];
  const retries = (run.later_runs || []).length;
  const sites = health.filter((row) => row.kind === 'ats');
  const others = health.filter((row) => row.kind !== 'ats');
  view.replaceChildren(...[
    el('h2', {}, 'Sources as they stand now'),
    el('p', {class: 'muted'}, `Last full scan ${ago(run.finished_at || run.started_at)} (ended ${run.status || 'unknown'})`
      + (retries ? `, with each source’s newer result from ${plural(retries, 'later retry run')}.` : '.')),
    el('div', {class: 'table-wrap'}, el('table', {class: 'sources'},
      el('thead', {}, el('tr', {}, ['Source', 'Status', 'Listings seen', 'Roles kept', 'Note'].map((name, index) =>
        el('th', {scope: 'col', class: index === 2 || index === 3 ? 'num' : null}, name)))),
      el('tbody', {},
        others.map((row) => sourceRow(row.label || row.source, statusPill(healthStatus(row)), Number(row.found) || 0, Number(row.kept) || 0, row.error)),
        sites.length > 0 && employerRow(sites)))),
    employerList('Employer sites that did not answer', sites.filter((row) => ATTENTION.includes(row.status)),
      (row) => el('span', {class: 'muted'}, [healthStatus(row).replace('_', ' '), row.error].filter(Boolean).join(' — ')), true),
    employerList('Employer sites with Pega roles', sites.filter((row) => Number(row.kept) > 0),
      (row) => el('span', {class: 'muted'}, plural(Number(row.kept), 'role')), false),
    el('p', {class: 'muted'}, 'Not covered: Naukri and Foundit refuse automated access. Keep their e-mail alerts switched on.'),
  ].filter(Boolean));
}

/* ---------- coverage: every employer on the original list, how it is searched, what happened ---------- */

async function loadCoverage() {
  let data;
  try {
    data = await api('/api/coverage');
  } catch (error) {
    $('coverage-table').hidden = true;
    $('coverage-empty').hidden = false;
    $('coverage-empty').replaceChildren(el('h2', {}, 'Coverage could not be loaded'), el('p', {}, error.message),
      el('button', {type: 'button', class: 'btn btn-primary', onclick: loadCoverage}, 'Retry'));
    return;
  }
  coverage.rows = Array.isArray(data.rows) ? data.rows : [];
  coverage.summary = data.summary || {};
  coverage.loaded = true;
  renderCoverage();
  renderScan();                                // the Retry button depends on what is incomplete
}

/* False only when coverage is known and no configured source is failed, cut off or untried. */
function retryNeeded() {
  return !coverage.loaded || coverage.rows.some((row) => RETRYABLE.includes(coverageOutcome(row)));
}

/* What the Latest result column and its filter show: a scan status, 'never', or 'gap' for inventory gaps. */
function coverageOutcome(row) {
  if (row.inventory_state !== 'configured') return 'gap';
  return row.latest_status || 'never';
}

function bengaluruKey(row) {
  if (row.bengaluru === null || row.bengaluru === undefined) return 'unknown';
  return row.bengaluru ? 'yes' : 'no';
}

function coverageName(row) {
  return row.canonical || (row.original_names || [])[0] || 'Unnamed target';
}

function coverageMatches(row, filters) {
  const portals = row.portals || [];
  const needle = filters.q.trim().toLowerCase();
  const haystack = [row.canonical, ...(row.original_names || []), ...portals.map((portal) => portal.kind),
    row.next_action, row.latest_error, row.latest_reason].filter(Boolean).join(' ').toLowerCase();
  return (!needle || haystack.includes(needle))
    && (!filters.inventory || row.inventory_state === filters.inventory)
    && (!filters.status || coverageOutcome(row) === filters.status)
    && (!filters.type || (row.type || 'unknown') === filters.type)
    && (!filters.bengaluru || bengaluruKey(row) === filters.bengaluru)
    && (!filters.portal || portals.some((portal) => portal.state === filters.portal));
}

function rolesOnFile(row) {
  return Number(row.jobs_on_file ?? row.jobs_total) || 0;
}

function coverageOrder(sort) {
  const byName = (a, b) => coverageName(a).localeCompare(coverageName(b));
  const rank = (row) => COVERAGE_RANK[coverageOutcome(row)] ?? COVERAGE_RANK.never;
  const lastSuccess = (row) => Date.parse(row.last_success_at) || 0;
  const isGap = (row) => Number(coverageOutcome(row) === 'gap');       // never scanned, so never "without success"
  const orders = {
    name: byName,
    attention: (a, b) => rank(a) - rank(b) || byName(a, b),
    jobs: (a, b) => rolesOnFile(b) - rolesOnFile(a) || byName(a, b),
    stale: (a, b) => isGap(a) - isGap(b) || lastSuccess(a) - lastSuccess(b) || byName(a, b),
  };
  return orders[sort] || orders.attention;
}

function outcomePill(row) {
  const outcome = coverageOutcome(row);
  if (outcome === 'gap') {
    const [label, slug] = INVENTORY_GAPS[row.inventory_state] || [row.inventory_state || 'Not configured', 'none'];
    return el('span', {class: `pill pill-gap gap-${slug}`}, label);
  }
  return outcome === 'never' ? el('span', {class: 'pill pill-gap gap-never'}, 'Never attempted') : statusPill(outcome);
}

function portalBadge(portal) {
  const state = PORTAL_STATES[portal.state] || portal.state || 'unknown';
  const scanned = portal.state === 'verified' || portal.state === 'candidate';
  return el('li', {},
    el('span', {class: `portal portal-${scanned ? portal.state : 'off'}`},
      el('strong', {}, portal.kind || 'portal'), ` · ${state} · ${portal.scope || 'unknown'} scope`,
      portal.business_unit && ` · ${portal.business_unit}`),
    portal.note && el('p', {class: 'muted small'}, portal.note));
}

function completeness(label, value) {
  if (value === null || value === undefined) return null;
  return `${label} ${value ? 'complete' : 'incomplete'}`;
}

function coverageEmployerCell(row) {
  const name = coverageName(row);
  const others = (row.original_names || []).filter((original) => original !== name);
  return el('td', {'data-label': 'Employer'},
    el('div', {class: 'job-company'}, el('span', {class: 'company'}, name),
      row.type && employerBadge({employer_type: row.type}),
      row.bengaluru === true && el('span', {class: 'badge blr-mark'}, 'Bengaluru')),
    row.parent && el('p', {class: 'muted small'}, `Part of ${row.parent}`),
    others.length > 0 && el('p', {class: 'muted small'}, `Listed as: ${others.join('; ')}`),
    row.inventory_note && el('p', {class: 'small note'}, row.inventory_note));
}

function coverageSearchCell(row) {
  const portals = row.portals || [];
  return el('td', {'data-label': 'How it is searched'},
    portals.length ? el('ul', {class: 'portals'}, portals.map(portalBadge)) : el('p', {class: 'muted small'}, 'No portal on file'),
    el('p', {class: 'small'}, externalLink(row.career_url, {}, 'Careers page', icon('external'))),
    el('p', {class: 'muted small', title: 'A LinkedIn search for the word Pega plus this employer’s name. It is not a company filter and is not counted as coverage.'},
      `LinkedIn keyword query: ${row.linkedin_query ? 'yes' : 'no'}`));
}

function coverageResultCell(row) {
  const attempted = Boolean(row.last_attempt_at);
  const detail = [row.latest_reason, row.latest_error].filter(Boolean).join(' — ');
  const ages = [attempted && `Attempted ${ago(row.last_attempt_at)}`,
    row.last_success_at ? `last success ${ago(row.last_success_at)}` : (attempted && 'never succeeded')].filter(Boolean).join(' · ');
  const complete = attempted
    ? [completeness('Pages', row.pages_complete), completeness('details', row.details_complete)].filter(Boolean).join(' · ') : '';
  const tasks = (row.sources || []).length > 1 ? row.sources : [];      // several portals: the pill shows the worst
  return el('td', {'data-label': 'Latest result'}, outcomePill(row),
    detail && el('p', {class: 'small note'}, detail),
    tasks.length > 0 && el('ul', {class: 'muted small'}, tasks.map((source) =>
      el('li', {}, `${source.task}: ${[SOURCE_STATES[source.status] || source.status || 'never attempted', source.reason].filter(Boolean).join(', ')}`))),
    ages && el('p', {class: 'muted small'}, ages),
    complete && el('p', {class: 'muted small'}, complete));
}

function coverageRow(row) {
  const onFile = rolesOnFile(row);
  return el('tr', {class: `cov cov-${coverageOutcome(row)}`},
    coverageEmployerCell(row),
    coverageSearchCell(row),
    coverageResultCell(row),
    el('td', {class: 'num', 'data-label': 'Roles on file'}, String(onFile),
      onFile > 0 && el('p', {class: 'muted small'}, `${Number(row.jobs_open) || 0} seen in last 30 days, not flagged closed`)),
    el('td', {'data-label': 'Next action'}, row.next_action || ''));
}

function renderCoverage() {
  $('coverage-tiles').replaceChildren(...TILE_GROUPS.map(([title, tiles]) => el('section', {class: 'tile-group'},
    el('h3', {}, title), el('div', {class: 'tiles'}, tiles.map((tile) => coverageTile(...tile))))));
  const shown = coverage.rows.filter((row) => coverageMatches(row, coverage.filters)).sort(coverageOrder(coverage.sort));
  $('coverage-rows').replaceChildren(...shown.map(coverageRow));
  $('coverage-line').textContent = shown.length === coverage.rows.length
    ? plural(coverage.rows.length, 'row') : `${shown.length} of ${plural(coverage.rows.length, 'row')} match`;
  $('coverage-table').hidden = shown.length === 0;
  $('coverage-empty').hidden = shown.length > 0;
  if (shown.length) return;
  $('coverage-empty').replaceChildren(...(coverage.rows.length
    ? [el('h2', {}, 'No employer matches these filters'),
      el('button', {type: 'button', class: 'btn', onclick: clearCoverageFilters}, 'Clear filters')]
    : [el('h2', {}, 'No coverage data yet'), el('p', {}, 'The employer list (companies.json and targets.json) is empty or missing.')]));
}

/* A tile either counts the rows one filter would show (and applies that filter when clicked), or
   shows a figure from the summary that no filter can reproduce. */
function coverageTile(label, filter, summaryKey) {
  if (!filter) {
    const value = coverage.summary[summaryKey];
    return el('div', {class: 'tile'}, el('span', {class: 'tile-value'}, value === undefined || value === null ? '–' : String(value)),
      el('span', {class: 'tile-label'}, label));
  }
  const only = {...NO_COVERAGE_FILTERS, ...filter};
  const active = Object.keys(only).every((key) => coverage.filters[key] === only[key]);
  return el('button', {type: 'button', class: 'tile', 'aria-pressed': String(active), title: active ? 'Showing these rows — click to show all' : 'Show these rows',
    onclick: () => setCoverageFilters(active ? NO_COVERAGE_FILTERS : only)},
  el('span', {class: 'tile-value'}, String(coverage.rows.filter((row) => coverageMatches(row, only)).length)),
  el('span', {class: 'tile-label'}, label));
}

function setCoverageFilters(filters) {
  coverage.filters = {...filters};
  $('coverage-search').value = coverage.filters.q;
  for (const select of $('coverage-filters').querySelectorAll('[data-coverage-filter]')) {
    select.value = coverage.filters[select.dataset.coverageFilter];
  }
  renderCoverage();
}

function clearCoverageFilters() {
  setCoverageFilters(NO_COVERAGE_FILTERS);
}

function bindCoverageFilters() {
  $('coverage-search').addEventListener('input', () => {
    coverage.filters.q = $('coverage-search').value;
    renderCoverage();
  });
  $('coverage-filters').addEventListener('change', (event) => {
    const key = event.target.dataset.coverageFilter;
    if (key) coverage.filters[key] = event.target.value;
    else if (event.target.id === 'coverage-sort') coverage.sort = event.target.value;
    renderCoverage();
  });
}

/* ---------- keyboard ---------- */

function onKeydown(event) {
  if (event.ctrlKey || event.metaKey || event.altKey) return;
  const refinement = $('more-filters');
  if (event.key === 'Escape' && refinement && refinement.open && !$('drawer').open) {
    refinement.open = false;
    refinement.querySelector('summary').focus();
    event.preventDefault();
    return;
  }
  const target = event.target;
  if (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) {
    if (event.key === 'Escape' && target.id === 'search') target.blur();
    return;
  }
  if ($('help').open) return;
  const inDrawer = $('drawer').open;
  const listActive = isJobView();
  const current = inDrawer ? state.detail : (listActive ? state.jobs[state.cursor] : null);
  const arrows = !inDrawer && listActive;
  if (event.key === '?') $('help').showModal();
  else if (event.key === '/' && !inDrawer && (listActive || state.view === 'coverage')) {
    (state.view === 'coverage' ? $('coverage-search') : $('search')).focus();
  }
  else if ((event.key === 'j' && listActive) || (event.key === 'ArrowDown' && arrows)) moveCursor(1);
  else if ((event.key === 'k' && listActive) || (event.key === 'ArrowUp' && arrows)) moveCursor(-1);
  else if (event.key === 'Enter' && arrows && current && !target.closest('button, a, summary')) openJob(current.id);
  else if (event.key === 's' && current) toggleSaved(current);
  else if (event.key === 'x' && current) toggleHidden(current);
  else return;
  event.preventDefault();
}

/* ---------- start ---------- */

/* Loads everything; safe to call again (Retry, or after "Disconnected"). */
async function start() {
  try {
    await refreshOverview();
  } catch (error) {
    $('scanned-at').textContent = 'Not connected';
    showLoadError(error.message);
    return;
  }
  if (state.scan.running) watchScan();
  if (pendingNotes.size) flushNotes();
  loadCoverage();                              // in the background: it decides whether Retry has anything to do
  if (!(await loadJobs()) && !state.jobs.length) showLoadError('The list of roles could not be loaded.');
  syncDrawer();
}

function showLoadError(detail) {
  if (state.jobs.length) {
    toast(`Still disconnected. ${detail}`, {kind: 'error'});   // keep what is already on screen
    return;
  }
  showEmpty('Cannot reach Pega Radar', `${detail} Start Pega Radar again if it has stopped, then retry.`, 'Retry', start);
}

function init() {
  $('scan-button').addEventListener('click', startFullScan);
  $('retry-button').addEventListener('click', () => startScan('retry'));
  $('theme-button').addEventListener('click', toggleTheme);
  $('help-button').addEventListener('click', () => $('help').showModal());
  $('help-close').addEventListener('click', () => $('help').close());
  $('seen-all').addEventListener('click', markAllSeen);
  $('offline-retry').addEventListener('click', start);
  $('load-more').addEventListener('click', loadMore);
  new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting) && !state.loading) loadMore();
  }, {rootMargin: '300px'}).observe($('load-more'));
  for (const dialog of [$('drawer'), $('help')]) {
    dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
    dialog.addEventListener('close', placeToasts);
  }
  $('drawer').addEventListener('close', onDrawerClosed);
  document.addEventListener('keydown', onKeydown);
  document.addEventListener('click', (event) => {
    const refinement = $('more-filters');
    if (refinement && refinement.open && !refinement.contains(event.target)) refinement.open = false;
  });
  window.addEventListener('hashchange', syncDrawer);
  window.addEventListener('pagehide', flushNotes);
  setInterval(renderScannedAt, 60000);
  bindFilters();
  bindCoverageFilters();
  renderFilters();
  return start();
}

document.addEventListener('DOMContentLoaded', init);
