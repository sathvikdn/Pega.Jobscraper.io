import puppeteer from 'puppeteer';
import { writeFile } from 'node:fs/promises';

const browser = await puppeteer.launch({ headless: true });
try {
  const page = await browser.newPage();
  await page.goto(new URL('./Pega_Career_Intelligence_Hub.pre-full-audit-2026-09-22.html', import.meta.url).href);
  const inventory = await page.evaluate(() => {
    const entries = [];
    const normalize = text => text.replace(/\s+/g, ' ').trim();
    for (const sectionId of ['referral-dossiers', 'contacts', 'team-dossiers']) {
      const section = document.getElementById(sectionId);
      let company = '';
      let companyDisplay = '';
      for (const row of section.querySelectorAll('tbody tr')) {
        const companyCell = row.querySelector('.co');
        if (companyCell) {
          company = normalize(companyCell.textContent);
          companyDisplay = [...companyCell.childNodes].map(node => normalize(node.textContent)).filter(Boolean).join(' · ');
        }
        if (sectionId === 'team-dossiers') {
          company = normalize(row.closest('.card')?.querySelector('h3')?.textContent ?? 'Team dossier');
          companyDisplay = company;
        }
        const snapshot = row.cloneNode(true);
        snapshot.querySelectorAll('.audit-pointer,.audit-pending').forEach(element => element.remove());
        snapshot.querySelectorAll('[title^="Historical label:"]').forEach(element => { element.textContent = element.title.slice('Historical label:'.length).trim(); });
        const previous = [...snapshot.cells].map(cell => normalize(cell.textContent)).join(' | ');
        for (const link of row.querySelectorAll('a[href]')) {
          if (link.classList.contains('audit-pointer') || !/^https?:/.test(link.href)) continue;
          const name = normalize(link.querySelector('b')?.textContent ?? link.textContent);
          const url = new URL(link.href);
          const profile = url.pathname.startsWith('/in/') ? url.pathname.split('/')[2] : null;
          const audit = profile ? [...document.querySelectorAll('#people-audit-table tr[data-profile]')].find(record => record.dataset.profile === profile) : null;
          const key = profile ?? `${company.toLowerCase()}::${name.toLowerCase()}`;
          entries.push({ key, name, company, companyDisplay, url: link.href, section: sectionId, previous: previous.slice(0, 1000), auditId: audit?.id ?? null });
        }
      }
    }
    const unique = [...new Set(entries.map(entry => entry.key))].map(key => entries.find(entry => entry.key === key));
    const pending = unique.filter(entry => !entry.auditId);
    const movements = [...document.querySelectorAll('#movement-radar tbody tr,#backfill tbody tr')].map((row, index) => ({ id: `movement-${index + 1}`, section: row.closest('section').id, text: normalize(row.textContent), urls: [...row.querySelectorAll('a[href]')].filter(link => /^https?:/.test(link.href)).map(link => link.href) }));
    return { checkedAt: '2026-09-22', entries, unique, pending, movements };
  });
  await writeFile(new URL('./pega_directory_inventory.json', import.meta.url), JSON.stringify(inventory, null, 2));
  console.log(JSON.stringify({ occurrences: inventory.entries.length, unique: inventory.unique.length, pending: inventory.pending.length, movements: inventory.movements.length }));
  const start = Number(process.argv[2] ?? 0);
  const count = Number(process.argv[3] ?? 30);
  console.log(inventory.pending.slice(start, start + count).map((entry, index) => `${start + index + 1}|${entry.key}|${entry.name}|${entry.company}|${entry.url}`).join('\n'));
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  await browser.close();
}
