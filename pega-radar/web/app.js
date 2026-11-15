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
const VIEWS = [['new', 'New'], ['all', 'All'], ['saved', 'Saved'], ['applied', 'Pipeline'], ['hidden', 'Hidden']];
const STATUSES = [['new', 'New'], ['interested', 'Interested'], ['applied', 'Applied'],
  ['interviewing', 'Interviewing'], ['offer', 'Offer'], ['rejected', 'Rejected']];
const SORTS = ['score', 'posted', 'first_seen'];
const TYPE_LABELS = {product: 'Product', gcc: 'GCC', enterprise: 'Enterprise', services: 'Services', staffing: 'Staffing', unknown: 'Unclassified'};
const READOUT = [['new', 'New (unread)'], ['new_bengaluru', 'New in Bengaluru'], ['new_product_gcc', 'New at product / GCC'],
  ['saved', 'Saved'], ['applied', 'Pipeline'], ['total', 'Total tracked']];
const ATTENTION = ['partial', 'blocked', 'maintenance', 'skipped', 'error'];   // radar.model.needs_attention
const STATUS_TONE = {ok: 'good', empty: 'quiet', skipped: 'warn', partial: 'warn', maintenance: 'warn', blocked: 'bad', error: 'bad'};
const WIDE = {city: 'all', types: '', q: '', min_score: 0};
const PEGA_TERMS = /\b(pega(?:systems|rules)?|prpc|cssa|csa|lsa|cpdc|cdh|customer decision hub|dev studio|app studio|constellation|case management|decisioning)\b/gi;
const ICONS = {
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
  } catch {
    // storage unavailable: preferences simply do not persist
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

function loadFilters() {
  let saved = null;
  try {
    saved = JSON.parse(storedGet('radar.filters'));
  } catch {
    saved = null;
  }
  saved = saved && typeof saved === 'object' ? saved : {};
  return {
    bengaluru: saved.bengaluru !== false,
    focus: saved.focus !== false,
    minScore: Math.min(100, Math.max(0, Number(saved.minScore) || 0)),
    sort: SORTS.includes(saved.sort) ? saved.sort : 'score',
    q: '',                                     // kept exactly as typed; trimmed only for the request
  };
}

function saveFilters() {
  const {bengaluru, focus, minScore, sort} = state.filters;
  storedSet('radar.filters', JSON.stringify({bengaluru, focus, minScore, sort}));
}

/* ---------- state ---------- */

const state = {
  token: '',
  stats: {},
  counts: {},                                  // per-view totals under the active filters
  latestRun: null,
  scan: {running: false},
  scanTimer: null,
  view: 'new',
  filters: loadFilters(),
  jobs: [],
  total: 0,
  outside: 0,
  loading: false,
  loadTicket: 0,
  cursor: -1,
  detail: null,
  detailTicket: 0,
};
const cards = new Map();                       // job id -> <li>
const pendingNotes = new Map();                // job id -> {value, sending, warned}: text not yet on the server
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
  state.latestRun = data.latest_run || null;
  state.scan = data.scan || {running: false};
  renderScannedAt();
  renderReadout();
  renderAttention();
  renderTabs();
  renderScan();
  if (state.view === 'sources') renderSources();
}

/* After a change: refresh the tiles and the tab counts, but leave the list rows where they are. */
function scheduleOverview() {
  clearTimeout(overviewTimer);
  overviewTimer = setTimeout(() => {
    Promise.all([refreshOverview(), refreshCounts()]).catch((error) => toast(error.message, {kind: 'error'}));
  }, 400);
}

async function refreshCounts() {
  if (state.view === 'sources') return;
  const data = await api(jobsUrl({limit: 1}));
  state.counts = data.counts || {};
  renderTabs();
}

/* The run that supplies coverage: latest_run carries null fields when every scan so far has failed. */
function coverageRun() {
  return state.latestRun && state.latestRun.id ? state.latestRun : null;
}

function failedAttempt() {
  const attempt = state.latestRun && state.latestRun.last_attempt;
  return attempt && attempt.status === 'failed' && attempt.id !== state.latestRun.id ? attempt : null;
}

function renderScannedAt() {
  const node = $('scanned-at');
  const run = coverageRun();
  if (!run) {
    node.textContent = state.latestRun ? 'No completed scan yet' : 'No scan yet';
    node.removeAttribute('title');
    return;
  }
  const when = run.finished_at || run.started_at;
  node.textContent = `Scanned ${ago(when)}${run.status === 'partial' ? ' · partial' : ''}`;
  node.title = new Date(when).toLocaleString();
}

function renderReadout() {
  $('readout').replaceChildren(...READOUT.map(([key, label]) => el('div', {class: 'readout-item'},
    el('dt', {}, label), el('dd', {}, String(Number(state.stats[key]) || 0)))));
}

function attentionRows() {
  const health = (state.latestRun && state.latestRun.health) || [];
  return health.filter((row) => ATTENTION.includes(row.status));
}

function failedAttemptLine(attempt) {
  const reason = attempt.error ? `: ${attempt.error}` : '';
  const tail = coverageRun() ? ' — showing coverage from the previous scan.' : '. No scan has completed yet.';
  return el('p', {}, el('strong', {}, `The last scan at ${clockTime(attempt.finished_at)} failed`), `${reason}${tail}`);
}

function attentionLine(rows) {
  const named = rows.filter((row) => row.kind !== 'ats').map((row) => `${row.label || row.source} (${row.status})`);
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
  $('scan-button').disabled = Boolean(running);
  $('scan-button-label').textContent = running ? 'Scanning…' : 'Scan now';
  $('scan-progress').hidden = !running;
  if (!running) return;
  const info = progress && typeof progress === 'object' ? progress : {};
  const done = Number(info.done) || 0;
  const total = Number(info.total) || 0;
  const fill = $('scan-progress-fill');
  fill.classList.toggle('is-indeterminate', total === 0);
  fill.style.width = total ? `${Math.min(100, Math.round((done / total) * 100))}%` : '';
  const parts = [total ? `${done} of ${plural(total, 'source')}` : 'Starting…'];
  const active = Array.isArray(info.running) ? info.running : [];
  if (active.length) parts.push(`${active.slice(0, 2).join(', ')}${active.length > 2 ? ` +${active.length - 2}` : ''}`);
  if (Number(info.new)) parts.push(`${Number(info.new)} new so far`);
  $('scan-progress-text').textContent = parts.join(' · ');
}

async function startScan() {
  try {
    await api('/api/scan', {});
  } catch (error) {
    if (error.status !== 409) {
      toast(`Could not start the scan: ${error.message}`, {kind: 'error'});
      return;
    }
  }
  watchScan();
}

function watchScan() {
  if (state.scanTimer) return;
  state.scan = {...state.scan, running: true};
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
  reloadJobs();
}

/* ---------- tabs and filters ---------- */

function renderTabs() {
  const tab = (view, label, count, alert) => el('button', {
    type: 'button', class: 'tab', 'aria-current': state.view === view ? 'page' : null, onclick: () => setView(view),
  }, label, count === null ? null : el('span', {class: `tab-count${alert ? ' is-alert' : ''}`}, String(count)));
  const attention = attentionRows().length + (failedAttempt() ? 1 : 0);
  $('tabs').replaceChildren(
    ...VIEWS.map(([view, label]) => tab(view, label, view in state.counts ? Number(state.counts[view]) || 0 : null, false)),
    el('span', {class: 'tabs-gap'}),
    tab('sources', 'Sources', attention || null, true));
}

function setView(view) {
  state.view = view;
  renderTabs();
  $('jobs-view').hidden = view === 'sources';
  $('sources-view').hidden = view !== 'sources';
  if (view === 'sources') renderSources();
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
  if (state.view === 'sources') return true;
  const ticket = ++state.loadTicket;
  state.loading = true;
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
    toast(`Could not load roles: ${error.message}`, {kind: 'error'});
    return false;
  } finally {
    if (ticket === state.loadTicket) state.loading = false;
  }
}

function reloadJobs() {
  return loadJobs({count: Math.max(PAGE_SIZE, state.jobs.length), keep: true});
}

function loadMore() {
  return loadJobs({count: state.jobs.length + PAGE_SIZE, keep: true});
}

function renderListChrome() {
  const line = $('result-line');
  line.replaceChildren(isFiltered() ? `${plural(state.total, 'role')} match${state.total === 1 ? 'es' : ''}` : plural(state.total, 'role'));
  if (state.outside > 0) {
    line.append(` · ${state.outside} more outside these filters — `,
      el('button', {type: 'button', class: 'link', onclick: widenFilters}, 'show all'));
  }
  $('seen-all').hidden = state.view !== 'new' || state.jobs.length === 0;
  $('load-more').hidden = state.jobs.length >= state.total;
  renderEmpty();
}

function emptyState() {
  if (state.outside > 0) {
    return ['Nothing matches these filters',
      `${plural(state.outside, 'role')} in this view ${state.outside === 1 ? 'is' : 'are'} outside them.`,
      `Show all ${state.outside}`, widenFilters];
  }
  if (!coverageRun() && !Number(state.stats.total)) {
    return ['No roles yet', 'Run your first scan to look for Pega roles across India. It takes a few minutes.',
      'Run your first scan', startScan];
  }
  switch (state.view) {
    case 'new':
      return ['Inbox clear', 'Roles you have not opened yet appear here for 14 days. Everything found so far is under All.',
        'Go to All', () => setView('all')];
    case 'saved':
      return ['No saved roles yet', 'Press s, or the star on a role, to keep it here.', null, null];
    case 'applied':
      return ['Nothing in your pipeline yet',
        'Set a role’s status to Applied, Interviewing, Offer or Rejected and it is tracked here.', null, null];
    case 'hidden':
      return ['Nothing hidden', 'Roles you hide (x) are kept here, out of the way, with their status untouched.', null, null];
    default:
      return ['No roles found', 'Run a scan to look again.', 'Scan now', startScan];
  }
}

function showEmpty(title, text, actionLabel, action) {
  $('empty').hidden = false;
  $('empty').replaceChildren(el('h2', {}, title), el('p', {}, text),
    actionLabel && el('button', {type: 'button', class: 'btn btn-primary', onclick: action}, actionLabel));
}

function renderEmpty() {
  $('empty').hidden = state.jobs.length > 0;
  if (!state.jobs.length) showEmpty(...emptyState());
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

function scoreChip(job) {
  const score = Math.round(Number(job.score) || 0);
  return el('span', {class: `score score-${scoreBand(score)}`, title: `Fit score ${score} of 100`}, String(score));
}

function saveButton(job, withLabel) {
  return el('button', {
    type: 'button', class: `btn btn-quiet star${job.saved ? ' is-on' : ''}`, 'data-role': 'save',
    'aria-pressed': String(Boolean(job.saved)), 'aria-label': withLabel ? null : (job.saved ? 'Remove from saved' : 'Save'),
    title: 'Save (s)', onclick: () => toggleSaved(job),
  }, icon('star'), withLabel && (job.saved ? 'Saved' : 'Save'));
}

function statusSelect(job) {
  const select = el('select', {class: 'status-select', 'data-role': 'status', 'aria-label': 'Status',
    onchange: () => updateState(job.id, {status: select.value})},
  STATUSES.map(([value, label]) => el('option', {value}, label)));
  select.value = job.status || 'new';
  return select;
}

function hideButton(job, withLabel) {
  const label = job.hidden ? 'Restore' : 'Hide';
  return el('button', {type: 'button', class: 'btn btn-quiet', 'data-role': 'hide', 'aria-label': withLabel ? null : label,
    title: `${label} (x)`, onclick: () => toggleHidden(job)}, icon(job.hidden ? 'show' : 'hide'), withLabel && label);
}

function renderCard(job) {
  const reasons = ((job.fit && job.fit.reasons) || []).slice(0, 3);
  const card = el('li', {class: `job band-${scoreBand(Number(job.score) || 0)}`, onclick: (event) => {
    if (event.target.closest('button, a, select')) return;
    openJob(job.id);
  }},
  scoreChip(job),
  el('div', {class: 'job-main'},
    el('div', {class: 'job-head'},
      el('button', {type: 'button', class: 'job-title', 'data-role': 'title', onclick: () => openJob(job.id)}, job.title || 'Untitled role'),
      job.is_new && el('span', {class: 'new-mark'}, 'New'),
      job.notes && el('span', {class: 'badge note-mark'}, 'Notes')),
    el('div', {class: 'job-company'}, el('span', {class: 'company'}, job.company || 'Unknown employer'), employerBadge(job)),
    el('div', {class: 'job-meta'}, metaItems(job), (job.sources || []).map((name) => el('span', {class: 'badge source'}, name))),
    reasons.length > 0 && el('ul', {class: 'job-reasons'}, reasons.map((reason) => el('li', {}, reason)))),
  el('div', {class: 'job-actions'}, saveButton(job, false), statusSelect(job), hideButton(job, false)));
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
}

/* ---------- saving state: optimistic, rolled back on failure ---------- */

async function updateState(id, patch) {
  const targets = copiesOf(id);
  const before = targets.map((job) => Object.fromEntries(Object.keys(patch).map((key) => [key, job[key]])));
  targets.forEach((job) => Object.assign(job, patch));
  refreshJob(id);
  try {
    await api(stateUrl(id), patch);
    scheduleOverview();
    return true;
  } catch (error) {
    targets.forEach((job, index) => Object.assign(job, before[index]));
    refreshJob(id);
    toast(`Not saved: ${error.message}`, {kind: 'error'});
    return false;
  }
}

function toggleSaved(job) {
  updateState(job.id, {saved: !job.saved});
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
  copiesOf(job.id).forEach((copy) => Object.assign(copy, {seen: true, is_new: false}));
  refreshJob(job.id);
  api(stateUrl(job.id), {seen: true}).then(scheduleOverview, () => {
    // Not worth interrupting reading for: the role just stays unread and is marked next time.
  });
}

async function markAllSeen() {
  try {
    await api('/api/jobs/seen-all', {});
  } catch (error) {
    toast(`Could not mark them as seen: ${error.message}`, {kind: 'error'});
    return;
  }
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
  state.detail = null;
  state.detailTicket += 1;
  if (hashJobId()) history.replaceState(null, '', location.pathname + location.search);
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
    el('h3', {}, 'Why it fits'),
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
      el('div', {class: 'job-meta'}, metaItems(job), job.posted_at && el('span', {}, `Found ${ago(job.first_seen_at)}`))),
    detailActions(job),
    fitSection(job),
    notesSection(job),
    sightingsSection(job),
    descriptionSection(job),
  ].filter(Boolean));
  $('drawer-body').scrollTop = 0;
}

/* ---------- notes autosave: text stays queued until the server has it ---------- */

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
      toast(`Notes not saved yet (${error.message}). They are kept and will be retried.`, {kind: 'error'});
    }
    return false;
  } finally {
    entry.sending = false;
  }
  copiesOf(id).forEach((job) => { job.notes = value; });
  refreshJob(id);
  if (entry.value === value) {
    pendingNotes.delete(id);
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
  const run = coverageRun();
  const attempt = failedAttempt();
  if (!run) {
    view.replaceChildren(el('div', {class: 'empty'},
      el('h2', {}, attempt ? 'No scan has completed yet' : 'No scan yet'),
      el('p', {}, attempt ? `The last attempt failed${attempt.error ? `: ${attempt.error}` : '.'}`
        : 'Run your first scan to see which sources answered.'),
      el('button', {type: 'button', class: 'btn btn-primary', onclick: startScan}, attempt ? 'Scan again' : 'Run your first scan')));
    return;
  }
  const health = run.health || [];
  const sites = health.filter((row) => row.kind === 'ats');
  const others = health.filter((row) => row.kind !== 'ats');
  view.replaceChildren(...[
    el('h2', {}, 'Sources in the last completed scan'),
    el('p', {class: 'muted'}, `Scanned ${ago(run.finished_at || run.started_at)} · run ${run.status || 'unknown'}.`),
    el('div', {class: 'table-wrap'}, el('table', {class: 'sources'},
      el('thead', {}, el('tr', {}, ['Source', 'Status', 'Listings seen', 'Roles kept', 'Note'].map((name, index) =>
        el('th', {scope: 'col', class: index === 2 || index === 3 ? 'num' : null}, name)))),
      el('tbody', {},
        others.map((row) => sourceRow(row.label || row.source, statusPill(row.status), Number(row.found) || 0, Number(row.kept) || 0, row.error)),
        sites.length > 0 && employerRow(sites)))),
    employerList('Employer sites that did not answer', sites.filter((row) => ATTENTION.includes(row.status)),
      (row) => el('span', {class: 'muted'}, [row.status, row.error].filter(Boolean).join(' — ')), true),
    employerList('Employer sites with Pega roles', sites.filter((row) => Number(row.kept) > 0),
      (row) => el('span', {class: 'muted'}, plural(Number(row.kept), 'role')), false),
    el('p', {class: 'muted'}, 'Not covered: Naukri and Foundit refuse automated access. Keep their e-mail alerts switched on.'),
  ].filter(Boolean));
}

/* ---------- keyboard ---------- */

function onKeydown(event) {
  if (event.ctrlKey || event.metaKey || event.altKey) return;
  const target = event.target;
  if (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) {
    if (event.key === 'Escape' && target.id === 'search') target.blur();
    return;
  }
  if ($('help').open) return;
  const inDrawer = $('drawer').open;
  const listActive = state.view !== 'sources';
  const current = inDrawer ? state.detail : (listActive ? state.jobs[state.cursor] : null);
  const arrows = !inDrawer && listActive;
  if (event.key === '?') $('help').showModal();
  else if (event.key === '/' && arrows) $('search').focus();
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
  $('scan-button').addEventListener('click', startScan);
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
  window.addEventListener('hashchange', syncDrawer);
  window.addEventListener('pagehide', flushNotes);
  setInterval(renderScannedAt, 60000);
  bindFilters();
  renderFilters();
  return start();
}

document.addEventListener('DOMContentLoaded', init);
