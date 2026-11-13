import fs from 'fs';

const { joins, leaves } = JSON.parse(fs.readFileSync('dates_extracted.json', 'utf8'));

// Dedupe joins: same month+year+ctx-prefix (first 50 chars) can be double-counted by two regexes matching the same mention.
const seen = new Set();
const dedupedJoins = [];
for (const j of joins) {
  const key = j.month + '|' + j.year + '|' + j.ctx.slice(0, 45);
  if (seen.has(key)) continue;
  seen.add(key);
  dedupedJoins.push(j);
}

const monthOrder = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

function monthHistogram(list) {
  const h = Object.fromEntries(monthOrder.map(m => [m, 0]));
  for (const j of list) if (h[j.month] !== undefined) h[j.month]++;
  return h;
}

const allTime = dedupedJoins;
const recent = dedupedJoins.filter(j => j.year >= 2024);
const veryRecent = dedupedJoins.filter(j => j.year >= 2025);

const histAll = monthHistogram(allTime);
const histRecent = monthHistogram(recent);
const histVeryRecent = monthHistogram(veryRecent);

// Year-month timeline for recent window
const ymCounts = {};
for (const j of recent) {
  const key = `${j.year}-${j.month}`;
  ymCounts[key] = (ymCounts[key] || 0) + 1;
}

function printHist(name, hist, total) {
  console.log(`\n${name} (n=${total})`);
  const max = Math.max(...Object.values(hist), 1);
  for (const m of monthOrder) {
    const c = hist[m];
    const bar = '#'.repeat(Math.round((c / max) * 30));
    console.log(`${m}  ${String(c).padStart(3)}  ${bar}`);
  }
}

printHist('All-time indexed join-month distribution', histAll, allTime.length);
printHist('2024-2026 indexed join-month distribution', histRecent, recent.length);
printHist('2025-2026 indexed join-month distribution', histVeryRecent, veryRecent.length);

console.log('\nYear-month breakdown (2024+):');
Object.entries(ymCounts).sort().forEach(([k, v]) => console.log(`${k}: ${v}`));

console.log('\nLeaves (departures) sample count:', leaves.length);
const leaveHist = monthHistogram(leaves.filter(l => l.year >= 2024));
printHist('2024-2026 indexed departure-month distribution', leaveHist, leaves.filter(l=>l.year>=2024).length);

fs.writeFileSync('date_histograms.json', JSON.stringify({ histAll, histRecent, histVeryRecent, ymCounts, leaveHist, totals: { allTime: allTime.length, recent: recent.length, veryRecent: veryRecent.length, leaves: leaves.length } }, null, 2));
