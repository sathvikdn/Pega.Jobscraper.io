import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';

const file = name => new URL(name, import.meta.url);
const escape = value => String(value ?? '').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
try {
  const ledger = JSON.parse(await readFile(file('pega_full_audit.json'), 'utf8'));
  const inventory = JSON.parse(await readFile(file('pega_directory_inventory.json'), 'utf8'));
  const backup = await readFile(file('Pega_Career_Intelligence_Hub.pre-full-audit-2026-09-22.html'));
  assert.equal(createHash('sha256').update(backup).digest('hex'), '7453bdec38ac6a1174d594e887cdfbcae0c3cec4d2d0b075ac85671497fc8bdd');
  assert.equal(inventory.pending.length, 270);
  assert.equal(Object.keys(ledger.records).length, 270);
  const resolve = (key, visited = new Set()) => {
    assert.ok(!visited.has(key), `Circular alias ${key}`);
    visited.add(key);
    const base = ledger.records[key];
    assert.ok(base, `Missing investigation: ${key}`);
    if (base.aliasOf) return resolve(base.aliasOf, visited);
    const followUp = ledger.followUps?.[key];
    return { ...base, ...followUp, canonicalKey: key, queries: [base.query, followUp?.query].filter(Boolean) };
  };
  const groups = new Map();
  inventory.pending.forEach((entry, index) => {
    const record = resolve(entry.key);
    assert.ok(record.query && record.outcome && record.finding, `Incomplete outcome: ${entry.key}`);
    if (!groups.has(record.canonicalKey)) groups.set(record.canonicalKey, { entry, record, index, origins: [] });
    groups.get(record.canonicalKey).origins.push(entry.url);
  });
  const rows = [...groups.values()].map(({ entry, record, index, origins }) => {
    const source = record.source === 'profile' ? entry.url : record.source;
    if (source) assert.ok(new URL(source).protocol === 'https:', `Unsafe source: ${entry.key}`);
    const sourceURL = source ? new URL(source) : null;
    const linkedInProfile = sourceURL && (sourceURL.hostname === 'linkedin.com' || sourceURL.hostname.endsWith('.linkedin.com')) && sourceURL.pathname.startsWith('/in/');
    const identityURL = linkedInProfile ? source : entry.url;
    const identity = new URL(identityURL);
    const profile = identity.pathname.startsWith('/in/') ? identity.pathname.split('/')[2] : `unresolved-${index + 1}`;
    const method = record.method ?? (/third-party/i.test(record.outcome) ? 'Third-party search-index evidence' : source ? 'Search-index evidence; not live profile verification' : 'Search attempted; no matching evidence established');
    const sourceLabel = record.method === 'Public post read' || record.method?.startsWith('Public post read') && !record.additionalSource ? 'Public post read' : 'Search-index source';
    const citation = source ? `<a href="${escape(source)}" target="_blank" rel="noopener noreferrer">${sourceLabel}</a>` : '<span>No matching source established; original link is not verification.</span>';
    const additional = record.additionalSource ? ` · <a href="${escape(record.additionalSource)}" target="_blank" rel="noopener noreferrer">Public post read</a>` : '';
    const queries = record.queries.map(query => `<li>${escape(query)}</li>`).join('');
    const checkedDate = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(record.checkedAt ?? ledger.checkedAt));
    return `<tr id="full-audit-${String(index + 1).padStart(3, '0')}" data-profile="${escape(profile)}" data-original-urls="${escape(JSON.stringify(origins))}" data-audit-key="${escape(record.canonicalKey)}"><td><a href="${escape(identityURL)}" target="_blank" rel="noopener noreferrer">${escape(entry.name)}</a><div class="sub">Original directory association: ${escape(entry.companyDisplay ?? entry.company)}</div></td><td>${escape(record.outcome)}<div class="sub">Checked ${escape(checkedDate)}</div></td><td>${escape(record.finding)}<p class="audit-context">${escape(method)}. ${citation}${additional}</p><details><summary>Research trail</summary><ul>${queries}</ul><p>Original entry: ${escape(entry.previous)}</p></details></td><td>Use this outcome instead of the old confidence label. Confirm current employer, legal entity, office, role level and approved requisition before referral. Research coverage is complete; successful verification is not guaranteed.</td></tr>`;
  });
  const target = file('Pega_Career_Intelligence_Hub.html');
  const html = await readFile(target, 'utf8');
  const marker = /<tbody id="full-directory-audit-rows">[\s\S]*?<\/tbody>/g;
  assert.equal([...html.matchAll(marker)].length, 1, 'Expected one generated audit region');
  let updated = html.replace(marker, `<tbody id="full-directory-audit-rows">\n${rows.join('\n')}\n</tbody>`);
  const employerMarker = /<tbody id="employer-evidence-rows">[\s\S]*?<\/tbody>/g;
  assert.equal([...updated.matchAll(employerMarker)].length, 1, 'Expected one employer evidence region');
  const sources = new Map([
    ['Commonwealth Bank', ['https://www.pega.com/customers/cba-marketing', 'Customer Decision Hub / Customer Engagement Engine; global account, not an India squad']],
    ['Wells Fargo', ['https://www.pega.com/customers/wells-fargo-platform', 'Estate Care Center with nested cases and internal/external integrations; programme geography unproven']],
    ['HSBC', ['https://www.pega.com/customers/hsbc-smart-investigate', 'Smart Investigate Global Payment Investigations and Pega COE; no named India implementer in case']],
    ['NAB', ['https://www.pega.com/customers/national-australia-bank-customer-decision-hub', 'Customer Brain CDH and adaptive models; Australia-wide result, not proof of India engineering ownership']],
    ['ANZ', ['https://www.pega.com/customers/anz-bank-platform', '20+ Pega apps consolidated into five cloud stacks, Blueprint used on fraud workflow; India ownership unproved']],
    ['Booking', ['https://www.pega.com/customers/booking-com-customer-service', 'Customer Service on Pega Cloud; India innovation evidence is separate in named-person dossier']],
    ['Cisco', ['https://www.pega.com/customers/cisco-platform', '30+ application OpenShift modernization with externalized Kafka; India implementation team not named']],
    ['Siemens', ['https://www.pega.com/insights/resources/pegaworld-2025-siemens-accelerating-transformation-ai-blueprint-constellation', 'PegaWorld named programme: Constellation, Blueprint and reusable enterprise layer; not every Siemens team']],
    ['Sun Life', ['https://www.pega.com/customers/sun-life-customer-service', 'Knowledge Agent embedded in existing Pega casework; country and named India implementers not established']],
    ['GE HealthCare', ['https://www.pega.com/customers/ge-healthcare-migrates-to-pega-cloud', 'Quality/Legal Pega Cloud migration, 2TB/1.3B records; historical project']],
    ['Ford', ['https://www.pega.com/customers/ford-motor-company-platform', 'Pega App Factory and COE enablement; programme != a specific Ford Credit squad']],
    ['Evernorth', ['https://www.pega.com/customers/evernorth-platform', 'Polaris Pega CRM integrates legacy client workflows; not proof CRD or AI COE is same team']],
    ['Orange Business', ['https://www.pega.com/customers/orange-business-platform', 'Optima global network-deployment workflow/API integration; India squad unproven']],
    ['Verizon', ['https://www.pega.com/customers/verizon-ai-automation-customer-decision-hub', 'Cross-channel CDH and case management delivered with Cognizant; direct India team unproven']],
    ['Lloyds', ['https://www.pega.com/customers/lloyds-banking-group-transform', 'Fraud and disputes workflows at UK scale; India engineering involvement unproven']],
    ['Vodafone', ['https://www.pega.com/customers/vodafone-digital-transformation', 'Enterprise order automation and Pega Cloud, delivered with Accenture; local VOIS remit unproven']]
  ]);
  const aliases = new Map([['cba','Commonwealth Bank'],['commonwealth bank of australia','Commonwealth Bank'],['jpmc','JPMorganChase'],['citibank','Citi'],['citi / citi india','Citi'],['sun life / slgs','Sun Life'],['sun life (additional)','Sun Life'],['optum / uhg','Optum'],['ge healthcare','GE HealthCare'],['nab india','NAB'],['anz bank','ANZ'],['booking holdings','Booking'],['booking.com','Booking'],['booking / former cba','Booking'],['ford credit','Ford'],['ford motor company','Ford'],['jdf','John Deere Financial'],['engen global','enGen'],['engen / highmark','enGen'],['evernorth / cigna','Evernorth'],['bt group','BT'],['lloyds banking group','Lloyds'],['lloyds banking group india','Lloyds'],['vodafone / vois','Vodafone'],['vodafone / vois india','Vodafone'],['vodafone / _vois','Vodafone'],['société générale','Société Générale'],['societe generale','Société Générale'],['societe generale gsc india','Société Générale'],['first citizens','First Citizens India'],['first citizens bank india','First Citizens India'],['bny mellon','BNY'],['metlife','MetLife India GCC'],['metlife mgcc','MetLife India GCC'],['dtici','Daimler Truck'],['daimler truck innovation center india','Daimler Truck'],['broadridge','Broadridge India'],['ameriprise financial','Ameriprise Financial India'],['telstra','Telstra India'],['synchrony financial','Synchrony'],['empower','Empower India'],['capital one claim','Capital One India'],['mizuho global services','Mizuho Global Services India (MGS)'],['elevance health','Elevance Health India']]);
  const canonical = text => {
    const clean = text.replace(/&amp;/g, '&').replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim().replace(/^\d+\s*·\s*/, '').split(' — ')[0].split(' · ')[0];
    return aliases.get(clean.toLowerCase()) ?? clean;
  };
  const audit = updated.match(/<table class="tbl searchable" id="people-audit-table">[\s\S]*?<\/table>/)?.[0];
  assert.ok(audit, 'Missing person audit table');
  const people = [...audit.matchAll(/<tr id="([^"]+)"[^>]*><td>([\s\S]*?)<\/td>/g)].map(([, id, cell]) => {
    const name = cell.match(/<a[^>]*>([^<]+)<\/a>/)?.[1];
    const context = cell.match(/Original directory association:\s*([^<]+)<\/div>/)?.[1] ?? cell.match(/<br\s*\/?>\s*([^<]+)/)?.[1];
    return { id, name, company: canonical(context ?? '') };
  });
  assert.equal(people.length, 329);
  const universe = ['confirmed', 'probable', 'global'].flatMap(section => {
    const body = updated.match(new RegExp(`<section class="section" id="${section}">[\\s\\S]*?<tbody>([\\s\\S]*?)<\\/tbody>`))?.[1];
    assert.ok(body, `Missing ${section} employer section`);
    return [...body.matchAll(/<tr>\s*<td class="co">([\s\S]*?)<\/td>/g)].map(([, label]) => ({ label, company: canonical(label), category: section }));
  });
  assert.equal(universe.length, 159);
  const employerRows = universe.map(({ label, company, category }) => {
    const mapped = people.filter(person => person.company === company);
    const links = mapped.length ? mapped.map(person => `<a href="#${escape(person.id)}">${escape(person.name)}</a>`).join(' · ') : 'No mapped person in the audited directory';
    const source = sources.get(company);
    const evidence = source ? `<a href="${escape(source[0])}" target="_blank" rel="noopener noreferrer">First-party programme account</a>: ${escape(source[1])}` : 'No first-party programme source checked in this extension; original employer claim remains historical.';
    return `<tr><td class="co">${label}</td><td>${escape(category)} · ${mapped.length} mapped audit ${mapped.length === 1 ? 'record' : 'records'}</td><td>${links}</td><td>${evidence}</td></tr>`;
  });
  updated = updated.replace(employerMarker, `<tbody id="employer-evidence-rows">\n${employerRows.join('\n')}\n</tbody>`);
  const unmapped = people.filter(person => !universe.some(employer => employer.company === person.company));
  const unmappedMarker = /<tbody id="unmapped-people-rows">[\s\S]*?<\/tbody>/g;
  assert.equal([...updated.matchAll(unmappedMarker)].length, 1, 'Expected one unmatched-person region');
  updated = updated.replace(unmappedMarker, `<tbody id="unmapped-people-rows">\n${unmapped.map(person => `<tr><td>${escape(person.name)}</td><td>${escape(person.company)}</td><td><a href="#${escape(person.id)}">Read individual research outcome</a></td></tr>`).join('\n')}\n</tbody>`);
  assert.ok(updated.includes('id="priority"') && updated.includes('id="backfill"'));
  await writeFile(target, updated);
  console.log(JSON.stringify({ additionalRows: rows.length, employerRows: employerRows.length, peopleRecords: people.length, peopleMappedToEmployerUniverse: people.length - unmapped.length, unmappedPeople: unmapped.length, unmappedEmployerLabels: [...new Set(unmapped.map(person => person.company))].sort(), inventoryContactOccurrences: inventory.entries.length, identityKeys: inventory.unique.length, followUps: Object.keys(ledger.followUps ?? {}).length, missingInvestigations: inventory.pending.filter(entry => !ledger.records[entry.key]).length }, null, 2));
} catch (error) {
  console.error(error);
  process.exitCode = 1;
}
