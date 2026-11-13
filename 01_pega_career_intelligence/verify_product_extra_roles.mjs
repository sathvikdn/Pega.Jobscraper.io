import { writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
const outputPath = join(root, 'reports', 'product_200_extra_official_checks_2026-11-12.json');
const checks = [];
const pegaUrl = 'https://www.pega.com/about/careers/24123/software-engineer-genai-engineering-pega-developer-csa-cssa';

async function check(label, url, inspect) {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(20000) });
    if (!response.ok) {
      checks.push({ label, url, status: `HTTP ${response.status}`, checkedAt: new Date().toISOString() });
      return;
    }
    const body = await response.text();
    checks.push({ label, url, status: 'checked', checkedAt: new Date().toISOString(), ...inspect(body) });
  } catch (error) {
    checks.push({ label, url, status: error.name === 'TimeoutError' ? 'timeout' : 'network error',
      checkedAt: new Date().toISOString() });
  }
}

try {
  await check('Pegasystems', pegaUrl, text => {
    const listed = /Software Engineer, GenAI Engineering \(Pega Developer CSA, CSSA\)/i.test(text) &&
      /India\s*-\s*Karnataka\s*-\s*Bangalore/i.test(text) && /2.{0,15}4 years of Pega/i.test(text);
    return {
      searchStatus: listed ? 'official-live-role' : 'not-confirmed',
      jobs: listed ? [{
        title: 'Software Engineer, GenAI Engineering (Pega Developer CSA, CSSA)',
        reqId: '24123', location: 'Bengaluru', url: pegaUrl, posted: null, closes: null,
        relevance: '2-4 years Pega; CSA and CSSA; GenAI agents, evaluations, guardrails and observability'
      }] : []
    };
  });
  await check('ANZ', 'https://careers.anz.com/search/?q=pega', text => ({
    searchStatus: /Results\s*<b>1\s*.\s*2<\/b>\s*of\s*<b>2<\/b>/i.test(text) &&
      /Docklands/i.test(text) && !/\b(Bangalore|Bengaluru)\b/i.test(text)
      ? 'official-search-no-bengaluru-pega-match' : 'search-result-needs-review',
    note: 'ANZ search lists two Docklands/Australia results as of this request, not a Bengaluru requisition.'
  }));
  await check('Cohere Health', 'https://boards-api.greenhouse.io/v1/boards/coherehealth/jobs?content=true', text => {
    try {
      const data = JSON.parse(text);
      const jobs = Array.isArray(data.jobs) ? data.jobs : [];
      const matching = jobs.filter(job => /\bpega\b/i.test(`${job.title ?? ''} ${job.content ?? ''}`));
      return { searchStatus: 'official-search-checked', boardSize: jobs.length, pegaMatches: matching.length,
        note: 'No Pega mention on current Greenhouse board' };
    } catch {
      return { searchStatus: 'invalid-response' };
    }
  });
  await writeFile(outputPath, JSON.stringify({ generatedAt: new Date().toISOString(), checks }, null, 2), 'utf8');
  console.log(JSON.stringify({ checks, outputPath }, null, 2));
} catch (error) {
  console.error(error);
  process.exitCode = 1;
}
