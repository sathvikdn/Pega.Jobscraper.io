import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

const root = dirname(fileURLToPath(import.meta.url));
const script = join(root, 'build_product_200_watchlist.mjs');
execFileSync(process.execPath, [script]);
execFileSync(process.execPath, [script]);
const data = JSON.parse(readFileSync(join(root, 'reports', 'product_200_openings_watch_2026-11-12.json'), 'utf8'));
const record = id => data.records.find(row => row.id === id);

test('accounts are distinct, and the original Top 50 excludes the current employer', () => {
  assert.equal(data.records.length, 200);
  assert.equal(new Set(data.records.map(row => row.id)).size, 200);
  assert.equal(data.records.filter(row => row.top50Rank !== null).length, 49);
  assert.ok(!data.records.some(row => /Mercedes-Benz R&D India/i.test(row.company)));
});

test('only employer-confirmed vacancies are listed as live', () => {
  const cba = record('commonwealth bank');
  assert.equal(cba.officialJobs.length, 6);
  assert.equal(cba.officialJobs.filter(job => job.relevance === 'ASB build-out').length, 4);
  assert.equal(record('pegasystems').officialJobs[0].reqId, '24123');
  assert.equal(record('booking').officialJobs.length, 0);
  assert.equal(record('siemens').officialJobs.length, 0);
  assert.equal(record('anz bank').scanStatus, 'Official search: no Bengaluru Pega match');
  assert.equal(record('first citizens bank').scanStatus, 'Partial board: no reliable negative');
});

test('unknown sites and historical signals are never labelled confirmed vacancies', () => {
  assert.match(record('broadridge').scanStatus, /no Bengaluru Pega match/);
  assert.equal(record('booking').newTeamSignal.verdict, 'Plausible squad growth; no employer-verified open Pega seat');
  assert.ok(data.records.some(row => row.scanStatus.startsWith('Not checked')));
  assert.ok(data.records.every(row => row.olderLeads.every(lead => lead.url.startsWith('https://'))));
});

test('standalone and hub versions keep one searchable 200-account section', () => {
  const html = readFileSync(join(root, 'reports', 'Product_200_Pega_Opportunity_Watch_2026-11-12.html'), 'utf8');
  const hub = readFileSync(join(root, 'Pega_Career_Intelligence_Hub.html'), 'utf8');
  assert.equal((hub.match(/PRODUCT_200_WATCH_START/g) ?? []).length, 1);
  assert.equal((hub.match(/id="product-200-watch"/g) ?? []).length, 1);
  assert.ok(hub.includes('href="#product-200-watch"'));
  assert.ok(html.includes('New-team signals: confirmed versus plausible'));
  assert.ok(html.includes("document.querySelectorAll('tbody')[1].querySelectorAll('tr')"));
});
