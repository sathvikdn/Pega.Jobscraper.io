import puppeteer from 'puppeteer';
import { readdirSync, statSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

// Chrome is extremely slow to start and to open tabs in this environment (launch ~130s,
// newPage ~185s), so we pay both costs once and reuse a single page for every chapter.
const dir = resolve(process.argv[2]);
const files = readdirSync(dir)
  .filter((f) => f.endsWith('.html'))
  .sort((a, b) => (a === 'index.html' ? 1 : b === 'index.html' ? -1 : a.localeCompare(b)));

const countPages = (pdfPath) => {
  const m = readFileSync(pdfPath).toString('latin1').match(/\/Type\s*\/Page[^s]/g);
  return m ? m.length : 0;
};

const t0 = Date.now();
const stamp = () => `${String(Math.round((Date.now() - t0) / 1000)).padStart(5)}s`;

const browser = await puppeteer.launch({
  headless: true,
  protocolTimeout: 900000,
  timeout: 600000,
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
});
console.log(`${stamp()} browser launched`);

const page = await browser.newPage();
page.setDefaultTimeout(600000);
page.setDefaultNavigationTimeout(600000);
await page.emulateMediaType('print');
console.log(`${stamp()} page ready`);

let total = 0;
let failed = 0;
for (const f of files) {
  const src = join(dir, f);
  const out = src.replace(/\.html$/, '.pdf');
  try {
    await page.goto(pathToFileURL(src).href, { waitUntil: 'domcontentloaded', timeout: 600000 });
    await page.pdf({
      path: out,
      format: 'A4',
      printBackground: true,
      preferCSSPageSize: true,
      timeout: 600000,
      // sourcebook.css declares `@page{size:A4;margin:0}` and supplies its own padding via
      // `.book` / `main`. Passing margins here would stack on top of that and shrink the text block.
      margin: { top: '0', bottom: '0', left: '0', right: '0' },
    });
    const n = countPages(out);
    total += n;
    const fresh = statSync(out).mtimeMs > statSync(src).mtimeMs ? 'ok   ' : 'STALE';
    console.log(`${stamp()} ${fresh} ${f.padEnd(44)} ${String(n).padStart(4)}p ${String(Math.round(statSync(out).size / 1024)).padStart(6)}KB`);
  } catch (err) {
    failed += 1;
    console.log(`${stamp()} FAIL  ${f}: ${err.message}`);
  }
}

await browser.close();
console.log(`\nTOTAL PAGES: ${total}   failed: ${failed}`);
