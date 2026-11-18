"""Operational acceptance: live portal verification, the coverage export and the run report.

Nothing here runs during a scan. `verify` is the only part that talks to the network, and only
when the user runs it on their own PC; tests drive it with a fake probe.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .model import csv_cell, now_iso
from .rank import SCANNABLE_STATES, employer_portals
from .scan import KV_MATRIX, _name_key
from .store import COVERAGE_COLUMNS

KV_VERIFICATION = 'portal_verification'
VERIFICATION_DAYS = 30    # a check older than this proves nothing about the board today
OUTCOMES = ('passed', 'inconclusive', 'failed')
# What a probe reports, under the names the adapters use. Every record has these keys; anything
# else a probe returns is kept as well, so a new field can never be dropped on the way to the report.
PROBE_KEYS = ('board_ok', 'board_size', 'pega_total', 'india_in_first_page', 'page2_ok', 'detail_ok', 'rows_parsed',
              'inconclusive', 'notes', 'status', 'requests', 'reason', 'error')
# Describe the portal, not the probe: a probe result must not overwrite them.
_RECORD_KEYS = ('key', 'employer', 'portal_index', 'kind', 'state', 'scope', 'passed', 'outcome', 'checked_at')
# Older spellings of board_size and india_in_first_page that the adapters still send alongside.
_DUPLICATE_KEYS = ('board_total', 'india_first_page')
# Portal keys that describe our knowledge of a board rather than which board it is.
_NOT_IDENTITY = ('state', 'scope', 'note', 'business_unit')


def portal_key(employer_name, portal) -> str:
    """A stable id for one configured portal: it changes when the board it points at changes, and
    not when its state or note does, so an old verification never promotes a different board."""
    identity = {name: value for name, value in portal.items() if name not in _NOT_IDENTITY}
    digest = hashlib.sha1(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:12]
    return f'{employer_name}|{portal.get("kind") or ""}|{digest}'


def outcome(record) -> str:
    """'passed', 'inconclusive' or 'failed' for one probe result. Only 'passed' can be promoted.

    failed: the board did not answer as the right site, the Pega search could not be read, or
    page 2 or a detail read failed. inconclusive: nothing failed, but the adapter parsed no posting
    at all, or it says itself that the check proves nothing (for example no India posting on a
    global board) or gives its own verdict as not passed. A board that answers with rows nobody
    could parse must not look verified.
    """
    if not record.get('board_ok') or record.get('pega_total') is None \
            or record.get('page2_ok') is False or record.get('detail_ok') is False:
        return 'failed'
    parsed = record.get('rows_parsed')
    if record.get('inconclusive') or isinstance(parsed, bool) or not isinstance(parsed, int) or parsed < 1:
        return 'inconclusive'
    # The adapter knows things this rule cannot see, such as whether descriptions had to be read.
    return 'inconclusive' if record.get('probe_passed') is False else 'passed'


def passed(record) -> bool:
    return outcome(record) == 'passed'


def _fresh(record, now=None) -> bool:
    """Was this portal checked within VERIFICATION_DAYS?"""
    try:
        checked = datetime.fromisoformat(str(record.get('checked_at')))
    except ValueError:
        return False
    return (now or datetime.now(timezone.utc)) - checked <= timedelta(days=VERIFICATION_DAYS)


def _stamp() -> str:
    return datetime.now().strftime('%Y%m%d-%H%M%S')


def _cell(value) -> str:
    """A value inside a Markdown table cell."""
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'yes' if value else 'no'
    if isinstance(value, (list, tuple)):
        value = '; '.join(str(item) for item in value)
    return str(value).replace('|', '\\|').replace('\r', ' ').replace('\n', ' ')


def _table(headers, rows) -> list[str]:
    lines = ['| ' + ' | '.join(headers) + ' |', '|' + ' --- |' * len(headers)]
    lines += ['| ' + ' | '.join(_cell(value) for value in row) + ' |' for row in rows]
    return lines


# ───────────────────────────── verify ─────────────────────────────

def run_verify(store, registry, http, *, probe=None, only=None, state='candidate') -> dict:
    """Probe configured portals and return the verification report.

    `state` is 'candidate' (portals not yet live-verified) or 'all' (verified ones too). Portals
    marked wrong_scope or unsupported are never probed. Results are merged into kv
    `portal_verification`; nothing in companies.json changes here.
    """
    if probe is None:
        from .sources import probe_portal as probe   # the adapters' per-kind bounded check
    wanted = {_name_key(name) for name in only or () if str(name).strip()}
    states = SCANNABLE_STATES if state == 'all' else ('candidate',)
    results = []
    for entry in registry.entries:
        if wanted and not ({_name_key(entry['name'])} | {_name_key(alias) for alias in entry.get('aliases') or []}) & wanted:
            continue
        for index, portal in enumerate(employer_portals(entry)):
            if portal['state'] not in states:
                continue
            record = {'key': portal_key(entry['name'], portal), 'employer': entry['name'], 'portal_index': index,
                      'kind': portal['kind'], 'state': portal['state'], 'scope': portal['scope'],
                      **dict.fromkeys(PROBE_KEYS)}
            record.update(requests=0, reason='', notes=[])
            if http.expired():
                record.update(status='error', reason='budget', error='not checked: the time budget ran out')
            else:
                try:
                    probed = probe(http, entry, portal)
                    if not isinstance(probed, dict):
                        raise TypeError('the probe did not return a result')
                    record.update({name: value for name, value in probed.items()
                                   if name not in _RECORD_KEYS and name not in _DUPLICATE_KEYS
                                   and not str(name).startswith('_')})   # a probe's own working keys stay out
                    if 'passed' in probed:
                        record['probe_passed'] = bool(probed['passed'])    # the adapter's own verdict, kept apart from ours
                except Exception as error:   # one broken probe must not end the whole check
                    record.update(status='error', reason='shape', error=f'{type(error).__name__}: {str(error)[:200]}')
            record.update(outcome=outcome(record), passed=passed(record), checked_at=now_iso())
            results.append(record)
    saved = store.kv_get(KV_VERIFICATION) or {}
    saved.update({record['key']: record for record in results})
    store.kv_set(KV_VERIFICATION, saved)
    return {'generated_at': now_iso(), 'state': state, 'checked': len(results),
            **{name: [record['key'] for record in results if record['outcome'] == name] for name in OUTCOMES},
            'results': results}


def verify_markdown(report) -> str:
    results = report['results']
    buckets = {name: [record for record in results if record['outcome'] == name] for name in OUTCOMES}
    lines = ['# Pega Radar portal verification', '',
             f'Generated {report["generated_at"]}. Portals checked: {len(results)}. Passed: {len(buckets["passed"])}. '
             f'Inconclusive: {len(buckets["inconclusive"])}. Failed: {len(buckets["failed"])}.', '',
             'Passed: the board answered as the right site, the Pega search could be read, at least one posting was '
             'parsed, and neither page 2 nor a detail read failed. Inconclusive: nothing failed, but no posting was '
             'parsed or the check proves nothing about India. Failed: something could not be read. Only passed portals '
             f'can be promoted, and only within {VERIFICATION_DAYS} days of the check. Nothing has been changed in '
             'companies.json.', '']
    candidates = [record for record in buckets['passed'] if record['state'] == 'candidate']
    if candidates:
        lines += [f'{len(candidates)} candidate portal(s) passed. To mark them verified run: '
                  '`python -B radar.py verify --promote`', '']
    for name in OUTCOMES:
        lines += [f'## {name.capitalize()} ({len(buckets[name])})', '']
        lines += _table(
            ('Employer', 'Kind', 'State', 'Probe status', 'Board size', 'Rows parsed', 'Pega total', 'India on page 1',
             'Page 2', 'Detail', 'Requests', 'Reason', 'Notes'),
            [(record['employer'], record['kind'], record['state'], record['status'], record['board_size'],
              record['rows_parsed'], record['pega_total'], record['india_in_first_page'], record['page2_ok'],
              record['detail_ok'], record['requests'], record['reason'],
              '; '.join(dict.fromkeys(filter(None, [*(record['notes'] or []), record['error']]))))
             for record in sorted(buckets[name], key=lambda item: item['employer'].lower())]) if buckets[name] else ['None.']
        lines.append('')
    return '\n'.join(lines)


def write_verify(report, folder) -> tuple[Path, Path]:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    stem = folder / f'verify-{_stamp()}'
    json_path, md_path = stem.with_suffix('.json'), stem.with_suffix('.md')
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    md_path.write_text(verify_markdown(report), encoding='utf-8')
    return json_path, md_path


def promote(companies_path, store, backups_dir) -> list[dict]:
    """Set `state: verified` on candidate portals whose latest verification passed.

    companies.json is copied to `backups_dir` before it is rewritten. A portal is matched by
    `portal_key`, so a verification of a board that has since been edited promotes nothing; an
    inconclusive or failed check promotes nothing; and neither does one older than
    VERIFICATION_DAYS. Returns [{'employer', 'kind'}] for what was promoted.
    """
    companies_path = Path(companies_path)
    # Judged again from the stored figures, so a record written under a laxer rule cannot slip through.
    verified = {key for key, record in (store.kv_get(KV_VERIFICATION) or {}).items()
                if isinstance(record, dict) and outcome(record) == 'passed' and _fresh(record)}
    document = json.loads(companies_path.read_text(encoding='utf-8-sig'))
    promoted = []
    for entry in document.get('companies') or []:
        if not isinstance(entry, dict) or not isinstance(entry.get('portals'), list):
            continue
        for portal in entry['portals']:
            if isinstance(portal, dict) and portal.get('state') == 'candidate' and portal_key(entry.get('name'), portal) in verified:
                portal['state'] = 'verified'
                promoted.append({'employer': entry.get('name'), 'kind': portal.get('kind')})
    if promoted:
        backups_dir = Path(backups_dir)
        backups_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(companies_path, backups_dir / f'companies-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json')
        temporary = companies_path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(document, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        os.replace(temporary, companies_path)   # never leaves a half-written registry behind
    return promoted


# ───────────────────────────── coverage export ─────────────────────────────

def _flat(column, value):
    if column == 'portals':
        return '; '.join(f'{portal.get("kind")} ({portal.get("state")}, {portal.get("scope")})' for portal in value or [])
    if column == 'sources':
        return '; '.join(f'{source["task"]}: {source["status"] or "never attempted"}'
                         + (f' [{source["reason"]}]' if source.get('reason') else '')
                         for source in value or [])
    return value


def coverage_csv(rows) -> str:
    """The coverage table as CSV text, one line per `Store.coverage()` row, every column included."""
    out = io.StringIO(newline='')
    writer = csv.writer(out, lineterminator='\r\n')
    writer.writerow(COVERAGE_COLUMNS)
    for row in rows:
        writer.writerow([csv_cell(_flat(column, row.get(column))) for column in COVERAGE_COLUMNS])
    return out.getvalue()


def _summary_lines(summary) -> list[str]:
    return [f'- Original target rows: {summary["original_rows"]}',
            f'- Canonical employers: {summary["employers"]}',
            f'- With a scannable portal configured: {summary["configured"]} ({summary["unverified"]} still unverified)',
            f'- Attempted in the latest run: {summary["attempted"]}',
            f'- Never attempted: {summary["never_attempted"]}; not reached within the time budget: {summary["not_reached"]}',
            f'- Latest outcome ok or empty: {summary["ok"]}; partial: {summary["partial"]}; blocked: {summary["blocked"]}; '
            f'maintenance: {summary["maintenance"]}; error: {summary["error"]}',
            f'- Not configured: {summary["not_configured"]}; unsupported: {summary["unsupported"]}; '
            f'wrong scope only: {summary["wrong_scope"]}; identity unresolved: {summary["unresolved"]}']


def coverage_markdown(rows, summary) -> str:
    lines = ['# Pega Radar company coverage', '', f'Generated {summary["generated_at"]}.', '',
             'A configured portal is not a successful scan, and a general LinkedIn keyword search is not company '
             'coverage. An employer that was never attempted has no status; it is never shown as empty.', '',
             *_summary_lines(summary), '']
    lines += _table(('Employer', 'Original names', 'Type', 'Bengaluru', 'Portals', 'LinkedIn query', 'Inventory',
                     'Latest status', 'Reason', 'Error', 'Last attempt', 'Last success', 'Pages complete', 'Details complete',
                     'Jobs (open / on file / ever)', 'Careers page', 'Next action'),
                    [(row['canonical'] or '(unresolved)', row['original_names'], row['type'], row['bengaluru'],
                      _flat('portals', row['portals']), row['linkedin_query'], row['inventory_state'], row['latest_status'],
                      row['latest_reason'], row['latest_error'], row['last_attempt_at'], row['last_success_at'],
                      row['pages_complete'],
                      row['details_complete'], f'{row["jobs_open"]} / {row["jobs_on_file"]} / {row["jobs_total"]}',
                      row['career_url'],
                      row['next_action']) for row in rows])
    return '\n'.join(lines) + '\n'


def write_coverage(rows, summary, path) -> tuple[Path, Path]:
    """Write the CSV at `path` (a `.csv` suffix is added when missing) and the Markdown beside it."""
    csv_path = Path(path)
    if csv_path.suffix.lower() != '.csv':
        csv_path = csv_path.with_name(csv_path.name + '.csv')
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    md_path = csv_path.with_suffix('.md')
    # utf-8-sig so Excel on Windows reads employer names correctly.
    csv_path.write_text(coverage_csv(rows), encoding='utf-8-sig', newline='')
    md_path.write_text(coverage_markdown(rows, summary), encoding='utf-8')
    return csv_path, md_path


# ───────────────────────────── run report ─────────────────────────────

def report_markdown(store, rows, summary) -> str:
    """The acceptance report for the most recent finished run, with the before/after coverage matrix."""
    run = store.latest_run()
    lines = ['# Pega Radar run report', '']
    if run is None:
        return '\n'.join(lines + ['No scan has finished yet. Run `python -B radar.py scan` first.']) + '\n'
    attempt = run['last_attempt']
    if attempt['id'] != run['id']:
        lines += [f'**The most recent attempt ({attempt["id"]}, finished {attempt["finished_at"]}) {attempt["status"]}'
                  + (f': {attempt["error"]}' if attempt.get('error') else '') + '.** '
                  'The figures below are from the last run that produced coverage.', '']
    if run['id'] is None:
        return '\n'.join(lines + ['No run has produced coverage yet.']) + '\n'
    details = run['summary']
    sources = details.get('sources') or []
    lines += [f'Run `{run["id"]}`: mode **{details.get("mode", "full")}**, status **{run["status"]}**, '
              f'started {run["started_at"]}, finished {run["finished_at"]}, {details.get("minutes", "?")} minutes, '
              f'{details.get("requests", "?")} requests.', '',
              '## Sources', '',
              f'- Scannable sources configured: {details.get("configured", len(sources))}',
              f'- Requested in this run: {details.get("requested", len(sources))}',
              f'- Attempted (actually started): {details.get("attempted", len(sources))}',
              f'- Completed without needing attention: {details.get("completed", "?")}',
              f'- Not reached before the time budget ended: {len(details.get("not_attempted") or [])}'
              + (' (' + ', '.join(details['not_attempted']) + ')' if details.get('not_attempted') else ''),
              f'- New jobs: {details.get("new", 0)} ({details.get("new_bengaluru", 0)} in Bengaluru, '
              f'{details.get("new_product_gcc", 0)} at product or GCC employers)', '']
    if details.get('unmatched'):
        lines += ['Names given to --only that matched no source: ' + ', '.join(details['unmatched']) + '.', '']
    lines += ['## Outcomes', '']
    statuses = {}
    for source in sources:
        statuses[source['status']] = statuses.get(source['status'], 0) + 1
    lines += _table(('Status', 'Sources'), sorted(statuses.items()))
    lines += ['', '## Sources needing attention, by reason', '']
    reasons = details.get('reasons') or {}
    lines += _table(('Reason', 'Sources'), sorted(reasons.items())) if reasons else ['None.']
    troubled = [source for source in sources if source['label'] in (details.get('attention') or [])]
    if troubled:
        lines += ['', *_table(('Source', 'Status', 'Reason', 'Seconds', 'Error'),
                              [(source['label'], source['status'], source.get('reason'), source.get('elapsed_s'),
                                source.get('error')) for source in troubled])]
    lines += ['', '## Slowest sources', '']
    timed = sorted((source for source in sources if source.get('elapsed_s')), key=lambda item: -item['elapsed_s'])[:15]
    lines += _table(('Source', 'Seconds', 'Requests', 'Status'),
                    [(source['label'], source['elapsed_s'], source['requests'], source['status']) for source in timed]) \
        if timed else ['No timings were recorded.']
    lines += ['', '## Coverage now', '', *_summary_lines(summary), '', '## Coverage before and after', '']
    matrix = store.kv_get(KV_MATRIX)
    if not matrix:
        lines += ['No before/after matrix was recorded for a run yet.']
    else:
        if matrix.get('run_id') != run['id']:
            lines += [f'The matrix below belongs to run `{matrix.get("run_id")}`, the last one that recorded it.', '']
        before, after = matrix.get('before') or {}, matrix.get('after') or {}
        names = sorted(set(before) | set(after), key=str.lower)
        changed = sum(1 for name in names if before.get(name) != after.get(name))
        lines += [f'{len(names)} employers and unresolved targets; {changed} changed in this run. A state such as '
                  '"not configured" or "identity unresolved" is still a gap, not coverage.', '',
                  *_table(('Employer or target', 'Before', 'After', 'Changed'),
                          [(name, before.get(name, '(absent)'), after.get(name, '(absent)'),
                            before.get(name) != after.get(name)) for name in names])]
    return '\n'.join(lines) + '\n'
