import { writeFile, mkdir } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

// Queries employers' official Workday career sites (the same public JSON the careers page uses)
// for "Pega" and keeps India postings. Sequential with a pause to stay polite to each site.
const directory = dirname(fileURLToPath(import.meta.url));
const today = new Date().toISOString().slice(0, 10);
const outputPath = join(directory, 'reports', `workday_pega_openings_${today}.json`);

// [employer label, tenant, Workday data centre, career-site name]. Unknown or wrong sites are
// reported as unreachable rather than "no openings".
const SITES = [
  ['Commonwealth Bank', 'cba', 'wd3', 'CommBank_Careers'], ['First Citizens India', 'svb', 'wd5', 'firstcitizensindia'],
  ['Empower', 'empower', 'wd12', 'empower'], ['Evernorth / Cigna', 'cigna', 'wd5', 'cignacareers'], ['Citi', 'citi', 'wd5', '2'],
  ['Intel', 'intel', 'wd1', 'External'], ['Levi Strauss', 'levistraussandco', 'wd5', 'External'], ['State Street', 'statestreet', 'wd1', 'Global'],
  ['The Hartford', 'thehartford', 'wd5', 'Careers_External'], ['Wells Fargo', 'wf', 'wd1', 'WellsFargoJobs'], ['Nike', 'nike', 'wd1', 'nke'],
  ['Dell', 'dell', 'wd1', 'External'], ['PayPal', 'paypal', 'wd1', 'jobs'], ['Mastercard', 'mastercard', 'wd1', 'CorporateCareers'],
  ['Target', 'target', 'wd5', 'targetcareers'], ['Walmart', 'walmart', 'wd5', 'WalmartExternal'], ['Capital One', 'capitalone', 'wd12', 'Capital_One'],
  ['Synchrony', 'synchronyfinancial', 'wd5', 'careers'], ['Fidelity Investments', 'fmr', 'wd1', 'FidelityCareers'], ['Northern Trust', 'ntrs', 'wd1', 'northerntrust'],
  ['GE HealthCare', 'gehc', 'wd5', 'GEHC_ExternalSite'], ['Broadridge', 'broadridge', 'wd5', 'Careers'], ['Sun Life', 'sunlife', 'wd3', 'Experienced-Jobs'],
  ['Shell', 'shell', 'wd3', 'ShellCareers'], ['Ameriprise', 'ameriprise', 'wd5', 'Ameriprise'], ['Lloyds', 'lbg', 'wd3', 'LBG_Careers'],
  ['Maersk', 'maersk', 'wd3', 'Maersk_Careers'], ['Elevance / Carelon', 'elevancehealth', 'wd1', 'ANT'], ['Pegasystems', 'pega', 'wd3', 'Pega'],
  ['Telstra', 'telstra', 'wd3', 'Telstra_Careers'], ['Morgan Stanley', 'ms', 'wd5', 'External'], ['Verizon', 'verizon', 'wd12', 'verizon-careers'],
  ['Philips', 'philips', 'wd3', 'jobs-and-careers'], ['Fiserv', 'fiserv', 'wd5', 'EXT'], ['Macquarie', 'mq', 'wd3', 'CareersatMQ'],
  ['John Deere', 'johndeere', 'wd5', 'johndeere'], ['Booking Holdings', 'bookingholdings', 'wd5', 'BookingHoldings'], ['NAB', 'nab', 'wd3', 'nab'],
  ['HSBC', 'hsbc', 'wd3', 'external'], ['Standard Chartered', 'scb', 'wd3', 'Standard_Chartered'], ['Nokia', 'nokia', 'wd3', 'Nokia'],
  ['BT Group', 'bt', 'wd3', 'BT'], ['Vanguard', 'vanguard', 'wd5', 'vanguard_external'], ['Lowe\'s', 'lowes', 'wd5', 'LWS_External_CS']
];
const searches = ['Pega', 'Pegasystems'];
const pause = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

const searchSite = async ([label, tenant, dataCentre, site]) => {
  const base = `https://${tenant}.${dataCentre}.myworkdayjobs.com/wday/cxs/${tenant}/${site}`;
  const found = new Map();
  for (const searchText of searches) {
    for (let offset = 0; offset < 200; offset += 20) {
      const response = await fetch(`${base}/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ appliedFacets: {}, limit: 20, offset, searchText })
      });
      if (!response.ok) return { label, status: `unreachable (HTTP ${response.status})`, jobs: [] };
      const page = await response.json();
      for (const posting of page.jobPostings ?? []) {
        found.set(posting.externalPath, {
          title: posting.title, location: posting.locationsText ?? '', posted: posting.postedOn ?? '',
          url: `https://${tenant}.${dataCentre}.myworkdayjobs.com/en-US/${site}${posting.externalPath}`, path: posting.externalPath
        });
      }
      if (offset + 20 >= (page.total ?? 0)) break;
      await pause(400);
    }
  }
  // A wrong career-site name can still answer with zero results, so record the size of the whole
  // board; "0 Pega roles" only means something when the board itself is non-empty.
  const board = await (await fetch(`${base}/jobs`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ appliedFacets: {}, limit: 1, offset: 0, searchText: '' })
  })).json();
  // "N Locations" postings hide the country in the list view, so those are kept until the detail check.
  const candidates = [...found.values()].filter(job => /india|bengaluru|bangalore|hyderabad|pune|chennai|gurugram|gurgaon|noida|mumbai|kolkata|\d+ locations/i.test(job.location));
  for (const job of candidates) {
    try {
      const detail = await (await fetch(`${base}${job.path}`, { headers: { Accept: 'application/json' } })).json();
      const info = detail.jobPostingInfo ?? {};
      const text = String(info.jobDescription ?? '').replace(/<[^>]+>/g, ' ').replace(/&nbsp;|&#160;/g, ' ').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim();
      const allLocations = [info.location, ...(info.additionalLocations ?? []), info.country?.descriptor].filter(Boolean).join(' · ');
      Object.assign(job, {
        reqId: info.jobReqId, location: allLocations || job.location, startDate: info.startDate, endDate: info.endDate ?? '',
        // Word boundary plus the "Pegasus" exclusion stops chip-design (Cadence Pegasus) postings matching.
        mentionsPega: /\bpega(?!sus)/i.test(`${text} ${job.title}`),
        inIndia: /india|bengaluru|bangalore|hyderabad|pune|chennai|gurugram|gurgaon|noida|mumbai|kolkata/i.test(allLocations),
        description: text.slice(0, 6000)
      });
    } catch (error) {
      job.detailError = String(error);
    }
    await pause(300);
  }
  return { label, status: 'ok', boardSize: board.total ?? 0, totalMatches: found.size, jobs: candidates.filter(job => job.mentionsPega && job.inIndia) };
};

try {
  const results = [];
  for (const site of SITES) {
    try {
      results.push(await searchSite(site));
    } catch (error) {
      results.push({ label: site[0], status: `error: ${error.message}`, jobs: [] });
    }
    await pause(500);
  }
  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(outputPath, JSON.stringify({ scannedAt: new Date().toISOString(), searches, results }, null, 2), 'utf8');
  for (const result of results) {
    console.log(`${result.label}: ${result.status}${result.status === 'ok' ? ` · board ${result.boardSize} · India Pega roles ${result.jobs.length}` : ''}`);
    for (const job of result.jobs) console.log(`   - ${job.title} | ${job.location} | ${job.reqId ?? ''} | start ${job.startDate ?? job.posted} | ends ${job.endDate}`);
  }
  console.log(`Saved ${outputPath}`);
} catch (error) {
  console.error(error);
  process.exit(1);
}
