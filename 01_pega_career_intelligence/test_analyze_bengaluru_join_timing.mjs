import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

const directory = dirname(fileURLToPath(import.meta.url));
execFileSync(process.execPath, [join(directory, 'analyze_bengaluru_join_timing.mjs')]);
const { companies } = JSON.parse(readFileSync(join(directory, 'reports', 'bengaluru_join_timing_2026-11.json'), 'utf8'));
const company = prefix => companies.find(row => row.company.startsWith(prefix));

test('First Citizens promotions, US leaders, and unproven Pega roles are not counted as Pega hires', () => {
  const row = company('First Citizens');
  assert.equal(row.recentDatedPegaRoles, 0);
  assert.deepEqual(row.recentStarts.map(person => person.name).sort(), ['Deepak Shahi', 'Nimalan Peter']);
  assert.ok(row.excludedOrAdjacent.some(person => person.name === 'Abhi Gummaraju' && person.category === 'internal-move'));
  assert.ok(row.excludedOrAdjacent.some(person => person.name === 'Sanjoy Sarkar' && person.category === 'excluded'));
});

test('Booking records distinct Pega-role and team-associated starts', () => {
  const row = company('Booking Holdings');
  assert.equal(row.recentDatedPegaRoles, 2);
  assert.equal(row.recentTeamAssociated, 1);
});

test('CBA recruiter start does not count as Pega engineer growth', () => {
  const row = company('Commonwealth Bank');
  assert.equal(row.recentStarts.length, 0);
  assert.ok(row.excludedOrAdjacent.some(person => person.name === 'Vandana P' && person.category === 'adjacent'));
});

test('Gurugram, vendor, and alumni profiles do not count as Bengaluru team growth', () => {
  for (const prefix of ['Ameriprise', 'ING (', 'Broadridge']) {
    assert.equal(company(prefix).recentStarts.length, 0, prefix);
  }
});
