import { readFile, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
const manifestPath = join(root, 'reports', 'product_200_openings_watch_2026-11-12.json');
const outputPath = join(root, 'reports', 'product_200_portal_probes_2026-11-12.json');

function safeUrl(value) {
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.username || url.password || url.port ||
        !/^[a-z0-9.-]+\.[a-z]{2,}$/i.test(url.hostname) ||
        /^(localhost|.*\.local|.*\.internal)$/i.test(url.hostname)) return null;
    return url;
  } catch {
    return null;
  }
}

async function probe(urlValue) {
  let url = safeUrl(urlValue);
  if (!url) return { url: urlValue, status: 'invalid-url' };
  try {
    let response;
    for (let attempt = 0; attempt < 4; attempt++) {
      response = await fetch(url, {
        method: 'GET', redirect: 'manual', signal: AbortSignal.timeout(15000),
        headers: { Accept: 'text/html,application/json' }
      });
      if (![301, 302, 303, 307, 308].includes(response.status)) break;
      const next = safeUrl(new URL(response.headers.get('location') ?? '', url).href);
      if (!next) return { url: urlValue, status: 'unsafe-redirect-rejected', http: response.status };
      url = next;
    }
    if (response.status === 429) return { url: urlValue, status: 'rate-limited', http: 429 };
    if (response.status === 401 || response.status === 403)
      return { url: urlValue, status: 'access-denied', http: response.status };
    if (!response.ok) return { url: urlValue, status: 'unavailable-or-redirected', http: response.status };
    const type = response.headers.get('content-type') ?? '';
    if (!/text\/html|application\/json/.test(type))
      return { url: urlValue, status: 'reachable-non-html', http: response.status };
    const text = (await response.text()).slice(0, 200000);
    // A career landing page being reachable never establishes a vacancy or a negative search result.
    return { url: urlValue, status: 'reachable-search-not-verified', http: response.status,
      pageMentionsPega: /\bPega\b/i.test(text), bytesRead: text.length };
  } catch (error) {
    return { url: urlValue, status: 'network-error', error: error.name === 'TimeoutError' ? 'timeout' : 'fetch failed' };
  }
}

try {
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  const urls = [...new Set(manifest.records.filter(row => row.scanStatus.startsWith('Not checked'))
    .map(row => row.careerUrl).filter(Boolean))];
  const results = [];
  let index = 0;
  async function worker() {
    while (index < urls.length) {
      const url = urls[index++];
      results.push(await probe(url));
    }
  }
  await Promise.all(Array.from({ length: 3 }, () => worker()));
  results.sort((left, right) => left.url.localeCompare(right.url));
  await writeFile(outputPath, JSON.stringify({ checkedAt: new Date().toISOString(), results,
    warning: 'GET only: reachability is not job-search coverage. No negative vacancy claims follow from this probe.' }, null, 2), 'utf8');
  const counts = {};
  for (const row of results) counts[row.status] = (counts[row.status] ?? 0) + 1;
  console.log(JSON.stringify({ uniqueCareerPages: urls.length, counts, outputPath }, null, 2));
} catch (error) {
  console.error(error);
  process.exitCode = 1;
}
