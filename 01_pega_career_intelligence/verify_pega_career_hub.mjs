import puppeteer from 'puppeteer';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const browser = await puppeteer.launch({ headless: true });
const check = (condition, message) => {
  assert.ok(condition, message);
  console.log(`PASS ${message}`);
};
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error') errors.push(message.text());
  });
  const backup = await readFile(new URL('./Pega_Career_Intelligence_Hub.backup-2026-09-22.html', import.meta.url));
  check(createHash('sha256').update(backup).digest('hex') === '1a666c6fc0d7478140ab5903e3c5e2f1eff0b725bb076a7bd8e4871e20b389cc', 'backup matches original SHA-256');
  await page.setViewport({ width: 1440, height: 1000 });
  await page.goto(new URL('./Pega_Career_Intelligence_Hub.html#priority', import.meta.url).href);
  await page.evaluate(() => { document.documentElement.style.scrollBehavior = 'auto'; });
  const initial = await page.evaluate(() => ({
    rows: document.querySelectorAll('tbody tr').length,
    tables: document.querySelectorAll('table.searchable').length,
    missing: [...document.querySelectorAll('a')].filter(link => link.getAttribute('href')?.startsWith('#') && !document.getElementById(link.hash.slice(1))).map(link => link.hash),
    overflow: document.documentElement.scrollWidth > innerWidth,
    font: getComputedStyle(document.querySelector('#priority td')).fontSize,
    ids: [...document.querySelectorAll('[id]')].map(element => element.id)
  }));
  check(initial.tables >= 89, `all ${initial.tables} tables searchable (minimum 89 from prior pass)`);
  check(initial.rows >= 1776, `${initial.rows} rows present (minimum 1776 from prior pass)`);
  check(await page.evaluate(() => document.querySelectorAll('#people-audit-table tbody tr[data-profile]').length === 329), '329 consolidated audit records');
  check(await page.evaluate(() => { const links = [...document.querySelectorAll('a[data-research-outcome]')]; return links.length === 355 && links.every(link => link.dataset.researchOutcome !== 'not-researched'); }), 'all 355 original contact occurrences have an outcome');
  check(await page.evaluate(() => document.querySelectorAll('[data-audit-id="not-reviewed"]').length === 0 && document.querySelectorAll('.audit-pending').length === 0), 'zero unchecked directory contacts');
  check(await page.evaluate(() => document.querySelectorAll('[data-directory-reconciliation="checked"]').length === 137), 'all 137 historical movement rows cross-referenced without claiming verification');
  const ledger = JSON.parse(await readFile(new URL('./pega_full_audit.json', import.meta.url), 'utf8'));
  const inventory = JSON.parse(await readFile(new URL('./pega_directory_inventory.json', import.meta.url), 'utf8'));
  check(inventory.pending.length === 270 && inventory.pending.every(entry => ledger.records[entry.key]), 'every previously unchecked inventory key has a research record');
  check(Object.keys(ledger.followUps).length === 33, '33 targeted follow-up investigations retained');
  const fullAuditBackup = await readFile(new URL('./Pega_Career_Intelligence_Hub.pre-full-audit-2026-09-22.html', import.meta.url));
  check(createHash('sha256').update(fullAuditBackup).digest('hex') === '7453bdec38ac6a1174d594e887cdfbcae0c3cec4d2d0b075ac85671497fc8bdd', 'pre-full-audit backup unchanged');
  check(await page.evaluate(() => [...document.querySelectorAll('#people-audit-table tbody tr')].every(row => row.querySelector('a[href^="https:"]') && row.cells.length === 4)), 'each audit record has evidence identity link and four fields');
  check(await page.evaluate(() => [...document.querySelectorAll('#referral-dossiers tbody tr')].filter(row => row.querySelector('a')).every(row => row.dataset.auditId)), 'every referral contact marked reviewed or pending');
  check(await page.evaluate(() => !document.getElementById('backfill').textContent.includes('Wells Fargo lost 2 Pega devs')), 'incorrect Wells Fargo vacancy claim removed');
  check(await page.evaluate(() => document.getElementById('audit-kalyan').textContent.includes('Senior Data Engineer')), 'Optum data-engineering correction present');
  check(await page.evaluate(() => { const section = document.getElementById('creative-market-exposure'); const tables = [...section.querySelectorAll('table')]; return tables.length === 2 && tables[0].querySelectorAll('tbody tr').length === 10 && tables[1].querySelectorAll('tbody tr').length === 11 && [...section.querySelectorAll('tbody tr')].every(row => row.cells.length === 4 && row.querySelector('a[href^="https://"]')); }), 'ten named-work dossiers and eleven first-party programme rows have sources');
  check(await page.evaluate(() => { const employerRows = [...document.querySelectorAll('#employer-evidence-rows tr')]; const unmapped = [...document.querySelectorAll('#unmapped-people-rows tr')]; const auditIds = new Set([...document.querySelectorAll('#people-audit-table tbody tr')].map(row => row.id)); const linked = new Set([...document.querySelectorAll('#employer-evidence-rows a[href^="#"],#unmapped-people-rows a[href^="#"]')].map(link => link.getAttribute('href').slice(1))); return employerRows.length === 159 && unmapped.length === 36 && auditIds.size === 329 && [...auditIds].every(id => linked.has(id)) && [...linked].every(id => auditIds.has(id)); }), 'all 159 employer rows and all 329 audit identities are accounted for without forced attribution');
  check(await page.evaluate(() => document.getElementById('full-audit-250').textContent.includes('Coforge') && document.getElementById('resume-fit').textContent.includes('Coforge') && document.getElementById('creative-market-exposure').textContent.includes('not an exhaustive scan')), 'Deere payroll and research-coverage caveats visible');
  const preAudit = await readFile(new URL('./Pega_Career_Intelligence_Hub.pre-audit-2026-09-22.html', import.meta.url));
  check(createHash('sha256').update(preAudit).digest('hex') === '1162e73e33f9425489db4c007ffd83a73770cd354b73218eee523af314b225e7', 'pre-audit backup unchanged');
  console.log(await page.$eval('#audit-coverage', element => element.textContent));
  check(initial.missing.length === 0, 'all anchor targets exist');
  check(new Set(initial.ids).size === initial.ids.length, 'unique element IDs');
  check(!initial.overflow, 'desktop has no page-level horizontal overflow');
  check(initial.font === '15px', 'readable 15px table text');
  await page.type('#search', 'Wells Fargo');
  check(await page.evaluate(() => document.querySelectorAll('#priority tbody tr:not(.hidden)').length === 1), 'company search filters priority table');
  check(await page.evaluate(() => document.querySelectorAll('#backfill tbody tr:not(.hidden)').length === 2), 'rowspan search retains both company rows');
  await page.click('#clear-search');
  await page.type('#search', 'zz-no-such-employer-zz');
  check(await page.evaluate(() => document.querySelectorAll('tbody tr:not(.hidden)').length === 0), 'no-match search hides all rows');
  check(await page.evaluate(() => { const count = document.querySelectorAll('.empty-results:not([hidden])').length; return count === document.querySelectorAll('table.searchable').length; }), 'each table shows empty state');
  await page.click('#clear-search');
  check(await page.evaluate(() => document.querySelectorAll('tbody tr.hidden').length === 0), 'clear restores every row');
  await page.click('#text-toggle');
  check(await page.evaluate(() => getComputedStyle(document.querySelector('#priority td')).fontSize === '17px'), 'larger text control works');
  await page.click('#text-toggle');
  await page.evaluate(() => document.getElementById('priority').scrollIntoView());
  await page.screenshot({ path: new URL('./Pega_Career_Intelligence_Hub.review-desktop.png', import.meta.url).pathname.replace(/^\/(.:)/, '$1') });
  await page.evaluate(() => document.getElementById('directory-insights').scrollIntoView());
  await page.screenshot({ path: new URL('./Pega_Career_Intelligence_Hub.audit-desktop.png', import.meta.url).pathname.replace(/^\/(.:)/, '$1') });
  for (const width of [390, 760, 768, 1024, 1920]) {
    await page.setViewport({ width, height: 900 });
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `no page overflow at ${width}px`);
  }
  await page.setViewport({ width: 390, height: 844 });
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  await page.waitForFunction(() => getComputedStyle(document.getElementById('side')).visibility === 'hidden');
  await page.click('#menu-toggle');
  check(await page.$eval('#menu-toggle', element => element.getAttribute('aria-expanded') === 'true'), 'mobile menu opens accessibly');
  await page.keyboard.press('Escape');
  check(await page.$eval('#menu-toggle', element => element.getAttribute('aria-expanded') === 'false'), 'Escape closes menu');
  await page.evaluate(() => document.getElementById('priority').scrollIntoView());
  check(await page.evaluate(() => document.getElementById('priority').getBoundingClientRect().top >= document.querySelector('.top').getBoundingClientRect().bottom), 'mobile anchor heading clears sticky toolbar');
  await page.screenshot({ path: new URL('./Pega_Career_Intelligence_Hub.review-mobile.png', import.meta.url).pathname.replace(/^\/(.:)/, '$1') });
  await page.evaluate(() => document.getElementById('directory-insights').scrollIntoView());
  await page.screenshot({ path: new URL('./Pega_Career_Intelligence_Hub.audit-mobile.png', import.meta.url).pathname.replace(/^\/(.:)/, '$1') });
  await page.evaluate(() => document.getElementById('full-audit-055').scrollIntoView());
  check(await page.evaluate(() => document.getElementById('full-audit-055').getBoundingClientRect().top >= document.querySelector('.top').getBoundingClientRect().bottom), 'deep audit row anchor clears sticky toolbar');
  const offlinePage = await browser.newPage();
  await offlinePage.setJavaScriptEnabled(false);
  await offlinePage.goto(new URL('./Pega_Career_Intelligence_Hub.html', import.meta.url).href);
  check(await offlinePage.evaluate(() => document.querySelectorAll('#people-audit-table tbody tr').length === 329), 'complete audit readable offline with JavaScript disabled');
  await offlinePage.close();
  await page.emulateMediaType('print');
  check(await page.$eval('.top', element => getComputedStyle(element).display === 'none'), 'print hides controls');
  check(errors.length === 0, `no browser script or console errors: ${errors.join('; ')}`);
  console.log(`Verified ${initial.rows} research rows.`);
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  await browser.close();
}
