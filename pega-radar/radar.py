"""Pega Radar command line.

    python radar.py serve [--port N] [--no-browser]   open the local website
    python radar.py scan [--minutes N] [--open]       search every scannable source once
    python radar.py scan --retry-incomplete           only sources that failed or were not reached last time
    python radar.py scan --only "Name A,Name B"       only the named employers or sources
    python radar.py verify [--only NAMES] [--state candidate|all] [--promote]
                                                      live-check configured portals; --promote marks those
                                                      that passed as verified in companies.json
    python radar.py coverage [path]                   write the company coverage table (CSV and Markdown)
    python radar.py report [path]                     write the acceptance report for the latest run
    python radar.py doctor                            check the installation (no network)
    python radar.py export [path]                     write every saved job to a CSV file
    python radar.py rescore                           re-rank saved jobs after editing config/companies

`verify` is the only command besides `scan` that uses the network.

Scan exit codes: 0 every source answered, 2 at least one source needs attention
(results from the others are saved), 1 the scan itself failed or could not start.
Data lives in ./data unless the PEGA_RADAR_DATA environment variable names another folder.
"""
from __future__ import annotations

import argparse
import csv
import importlib
import json
import os
import sys
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

CONFIG_PATH = BASE / 'config.json'
COMPANIES_PATH = BASE / 'companies.json'
TARGETS_PATH = BASE / 'targets.json'
DATABASE_NAME = 'radar.sqlite3'
MODULES = ('radar.model', 'radar.net', 'radar.store', 'radar.rank', 'radar.scan', 'radar.acceptance', 'radar.sources',
           'radar.server')
EXPORT_COLUMNS = ('score', 'title', 'company', 'employer_type', 'city', 'location', 'posted_at', 'experience_min',
                  'experience_max', 'salary_min_lpa', 'salary_max_lpa', 'status', 'saved', 'hidden', 'notes', 'sources', 'url',
                  'apply_url', 'requisition_id', 'first_seen_at', 'last_seen_at', 'last_confirmed_at', 'possibly_closed',
                  'seen_at', 'id')
SCAN_EXIT = {'complete': 0, 'partial': 2, 'nothing_to_retry': 0}
VERIFY_MINUTES = 20


def data_dir() -> Path:
    return Path(os.environ.get('PEGA_RADAR_DATA') or BASE / 'data')


def _open_store():
    from radar.store import Store
    return Store(data_dir() / DATABASE_NAME)


def _load_config():
    from radar.model import load_config
    return load_config(CONFIG_PATH)


def _serve(store, config, port, open_browser):
    from radar.server import serve
    serve(store, config, port=port or int((config.get('server') or {}).get('port') or 8765), open_browser=open_browser)


def cmd_scan(args) -> int:
    from radar import scan
    scan.setup_console_logging()
    config, store = _load_config(), _open_store()
    try:
        with scan.scan_lock(data_dir()):
            summary = scan.run_scan(config, store, minutes=args.minutes, only=_names(args.only),
                                    mode='retry' if args.retry_incomplete else 'full')
    except scan.ScanLocked as error:
        print(error)
        return 1
    if summary['status'] == 'nothing_to_retry':
        print('Nothing to retry: every source was read in full at its latest attempt. No scan was run.')
        return 0
    print(f'{summary["mode"].capitalize()} scan: {summary["attempted"]} of {summary["requested"]} requested sources '
          f'attempted, {summary["completed"]} completed, {summary["new"]} new jobs.')
    if summary['unmatched']:
        print('No source matches: ' + ', '.join(summary['unmatched']))
    if summary['not_attempted']:
        print(f'{len(summary["not_attempted"])} sources were not reached before the time budget ended; '
              'run "radar.py scan --retry-incomplete" to attempt them.')
    if summary['attention']:
        print('Sources that need attention (jobs posted only there may be missing): ' + ', '.join(summary['attention']))
    if summary.get('error'):
        print('The scan failed: ' + summary['error'])
    if args.open:
        _serve(store, config, None, True)
    return SCAN_EXIT.get(summary['status'], 1)


def _names(text):
    """'A, B' -> ['A', 'B']; None when nothing was given."""
    names = [name.strip() for name in (text or '').split(',') if name.strip()]
    return names or None


def _coverage(store):
    from radar import scan
    return scan.load_coverage(store, {**_load_config(), 'companies_path': str(COMPANIES_PATH),
                                      'targets_path': str(TARGETS_PATH)})


def cmd_verify(args) -> int:
    """Bounded live checks of configured portals. Changes companies.json only with --promote."""
    from radar import acceptance
    from radar.net import Http
    from radar.rank import load_registry
    store = _open_store()
    if args.promote:
        promoted = acceptance.promote(COMPANIES_PATH, store, data_dir() / 'backups')
        for item in promoted:
            print(f'verified: {item["employer"]} ({item["kind"]})')
        print(f'{len(promoted)} portals marked verified in companies.json.'
              + (' The previous file is in the data/backups folder.' if promoted else
                 ' Nothing to promote: run "radar.py verify" first. Only candidates that passed within the last '
                 f'{acceptance.VERIFICATION_DAYS} days are promoted.'))
        return 0
    import time
    config = _load_config()
    http = Http(deadline=time.monotonic() + (args.minutes or VERIFY_MINUTES) * 60,
                user_agent=(config.get('http') or {}).get('user_agent'))
    report = acceptance.run_verify(store, load_registry(COMPANIES_PATH), http, only=_names(args.only), state=args.state)
    json_path, md_path = acceptance.write_verify(report, data_dir() / 'acceptance')
    print(f'{report["checked"]} portals checked: {len(report["passed"])} passed, '
          f'{len(report["inconclusive"])} inconclusive, {len(report["failed"])} failed.')
    print(f'Report: {md_path}')
    print(f'Data:   {json_path}')
    if report['passed']:
        print('To mark the candidates that passed as verified: python -B radar.py verify --promote')
    return 0 if report['checked'] else 1


def cmd_coverage(args) -> int:
    from datetime import datetime
    from radar import acceptance
    rows, summary = _coverage(_open_store())
    path = args.path or data_dir() / 'acceptance' / f'coverage-{datetime.now():%Y%m%d-%H%M%S}.csv'
    csv_path, md_path = acceptance.write_coverage(rows, summary, path)
    print(f'{len(rows)} rows: {summary["employers"]} employers, {summary["configured"]} with a scannable portal, '
          f'{summary["ok"]} read in full at their latest attempt, {summary["unresolved"]} unresolved targets.')
    print(f'Table:  {csv_path}')
    print(f'Report: {md_path}')
    return 0


def cmd_report(args) -> int:
    from datetime import datetime
    from radar import acceptance
    store = _open_store()
    rows, summary = _coverage(store)
    path = Path(args.path) if args.path else data_dir() / 'acceptance' / f'report-{datetime.now():%Y%m%d-%H%M%S}.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(acceptance.report_markdown(store, rows, summary), encoding='utf-8')
    print(f'Report: {path}')
    return 0


def cmd_serve(args) -> int:
    _serve(_open_store(), _load_config(), args.port, not args.no_browser)
    return 0


def _read_json(path):
    """(document, problem). A missing file is not a problem here; the caller decides."""
    if not path.exists():
        return None, None
    try:
        return json.loads(path.read_text(encoding='utf-8-sig')), None
    except (OSError, ValueError) as error:
        return None, f'{path.name} cannot be read as JSON: {error}'


def _check_companies(entries, problems, notes) -> set:
    """Validate employers and their portals; returns the set of employer names."""
    from radar.rank import EMPLOYER_TYPES, PORTAL_SCOPES, PORTAL_STATES, employer_portals
    valid = [entry for entry in entries if isinstance(entry, dict) and entry.get('name')]
    if len(valid) != len(entries):
        problems.append(f'companies.json: {len(entries) - len(valid)} entries are not objects with a "name".')
    by_type, by_state = {}, {}
    for entry in valid:
        name = entry['name']
        if entry.get('type') not in EMPLOYER_TYPES:
            problems.append(f'companies.json: {name} has an unknown type {entry.get("type")!r}.')
        by_type[entry.get('type')] = by_type.get(entry.get('type'), 0) + 1
        listed = entry.get('portals')
        if listed is not None and not isinstance(listed, list):
            problems.append(f'companies.json: "portals" of {name} must be a list.')
            continue
        for raw in listed or []:
            if not isinstance(raw, dict) or not raw.get('kind'):
                problems.append(f'companies.json: a portal of {name} has no "kind".')
            elif raw.get('state') not in PORTAL_STATES:
                problems.append(f'companies.json: portal {raw["kind"]} of {name} has an unknown state {raw.get("state")!r}.')
            elif raw.get('scope') not in PORTAL_SCOPES:
                problems.append(f'companies.json: portal {raw["kind"]} of {name} has an unknown scope {raw.get("scope")!r}.')
            elif raw['state'] in ('wrong_scope', 'unsupported') and not raw.get('note'):
                problems.append(f'companies.json: portal {raw["kind"]} of {name} is {raw["state"]} and must say why in "note".')
        for portal in employer_portals(entry):
            by_state[portal['state']] = by_state.get(portal['state'], 0) + 1
    with_portal = sum(1 for entry in valid if employer_portals(entry))
    notes.append(f'companies.json: {len(valid)} employers ('
                 + ', '.join(f'{count} {kind}' for kind, count in sorted(by_type.items(), key=str)) + f'), {with_portal} with a portal')
    notes.append('portals: ' + (', '.join(f'{count} {state}' for state, count in sorted(by_state.items())) or 'none configured'))
    return {entry['name'] for entry in valid}


def _check_targets(document, names, problems, notes):
    """Validate targets.json, the original target inventory that coverage is measured against."""
    from radar.rank import TARGET_RESOLUTIONS
    rows = document.get('rows') if isinstance(document, dict) else None
    if not isinstance(rows, list):
        problems.append('targets.json must contain {"rows": [...]}.')
        return
    by_resolution = {}
    for row in rows:
        label = f'targets.json row {row.get("row")!r}' if isinstance(row, dict) else 'targets.json'
        if not isinstance(row, dict) or not row.get('original_name'):
            problems.append(f'{label}: every row needs an "original_name".')
            continue
        resolution = row.get('resolution')
        by_resolution[resolution] = by_resolution.get(resolution, 0) + 1
        if resolution not in TARGET_RESOLUTIONS:
            problems.append(f'{label} ({row["original_name"]}): unknown resolution {resolution!r}.')
        elif resolution == 'unresolved':
            if not row.get('note'):
                problems.append(f'{label} ({row["original_name"]}): an unresolved target must give its reason in "note".')
        elif row.get('employer') not in names:
            problems.append(f'{label} ({row["original_name"]}): employer {row.get("employer")!r} is not in companies.json.')
    notes.append(f'targets.json: {len(rows)} original rows ('
                 + ', '.join(f'{count} {resolution}' for resolution, count in sorted(by_resolution.items(), key=str)) + ')')


def cmd_doctor(_args) -> int:
    """Offline installation check: each problem is printed with what it prevents."""
    problems, notes = [], []
    if sys.version_info < (3, 10):
        problems.append(f'Python 3.10 or newer is required; this is {sys.version.split()[0]}.')
    else:
        notes.append(f'Python {sys.version.split()[0]}')
    for name in MODULES:
        try:
            importlib.import_module(name)
        except Exception as error:
            problems.append(f'Module {name} cannot be loaded: {type(error).__name__}: {error}')
    if not (BASE / 'web' / 'index.html').exists():
        problems.append('web/index.html is missing; the website cannot be shown.')

    folder = data_dir()
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / '.write_test'
        probe.write_text('ok', encoding='utf-8')
        probe.unlink()
        notes.append(f'Data folder {folder} is writable')
    except OSError as error:
        problems.append(f'The data folder {folder} is not writable: {error}')
    else:
        try:
            stats = _open_store().stats()
            notes.append(f'Database opens; {stats["total"]} jobs saved, last scan: {stats["last_scan_at"] or "never"}')
        except Exception as error:
            problems.append(f'The database in {folder} cannot be opened: {type(error).__name__}: {error}')

    config, problem = _read_json(CONFIG_PATH)
    if problem:
        problems.append(problem)
    elif config is None:
        notes.append('config.json is missing; built-in defaults are used')
    elif not isinstance(config, dict):
        problems.append('config.json must contain a JSON object.')
    else:
        notes.append('config.json is valid')
        budget = (config.get('portals') or {}).get('detail_budget_per_board', 120) if isinstance(config.get('portals', {}), dict) else None
        if isinstance(budget, bool) or not isinstance(budget, (int, float)) or budget <= 0:
            problems.append('config.json: portals.detail_budget_per_board must be a positive number '
                            '(how many new descriptions one employer board reads per run).')
        else:
            notes.append(f'Each employer board reads at most {budget:g} new descriptions per run')

    companies, problem = _read_json(COMPANIES_PATH)
    names = set()
    if problem:
        problems.append(problem)
    elif companies is None:
        notes.append('companies.json is missing; employer sites are not searched and employer types come from name patterns')
    else:
        entries = companies.get('companies') if isinstance(companies, dict) else None
        if not isinstance(entries, list):
            problems.append('companies.json must contain {"companies": [...]}.')
        else:
            names = _check_companies(entries, problems, notes)

    targets, problem = _read_json(TARGETS_PATH)
    if problem:
        problems.append(problem)
    elif targets is None:
        notes.append('targets.json is missing; coverage lists the employers in companies.json only')
    else:
        _check_targets(targets, names, problems, notes)

    for line in notes:
        print('ok       ' + line)
    for line in problems:
        print('PROBLEM  ' + line)
    print('Doctor found problems; fix them and run it again.' if problems else 'Everything needed is in place.')
    return 1 if problems else 0


def cmd_export(args) -> int:
    from radar.model import csv_cell
    rows = _open_store().export_rows()
    path = Path(args.path) if args.path else data_dir() / f'pega-radar-jobs-{date.today():%Y%m%d}.csv'
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig so Excel on Windows reads company names and the rupee sign correctly.
    with open(path, 'w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(EXPORT_COLUMNS)
        for row in rows:
            writer.writerow([csv_cell(row.get(column)) for column in EXPORT_COLUMNS])   # job text is untrusted
    print(f'{len(rows)} jobs written to {path}')
    return 0


def cmd_rescore(_args) -> int:
    from radar.rank import load_registry, make_ranker
    count = _open_store().rescore(make_ranker(_load_config(), load_registry(COMPANIES_PATH)))
    print(f'{count} jobs re-ranked')
    return 0


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors='replace')   # a cp1252 console must not crash on a company name
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(prog='radar.py', description='Pega Radar: find Pega roles in India, Bengaluru first.')
    commands = parser.add_subparsers(dest='command', required=True)
    scan = commands.add_parser('scan', help='search every source once')
    scan.add_argument('--minutes', type=float, default=None, help='time budget (default: config.json, 40)')
    scan.add_argument('--open', action='store_true', help='open the website when the scan has finished')
    scan.add_argument('--retry-incomplete', action='store_true',
                      help='only sources whose latest outcome needs attention or that the last full scan did not reach')
    scan.add_argument('--only', default=None, metavar='NAMES', help='only these employers or sources, comma-separated')
    scan.set_defaults(run=cmd_scan)
    serve = commands.add_parser('serve', help='open the local website')
    serve.add_argument('--port', type=int, default=None, help='port on 127.0.0.1 (default: config.json, 8765)')
    serve.add_argument('--no-browser', action='store_true', help='do not open a browser window')
    serve.set_defaults(run=cmd_serve)
    verify = commands.add_parser('verify', help='live-check configured portals (uses the network)')
    verify.add_argument('--only', default=None, metavar='NAMES', help='only these employers, comma-separated')
    verify.add_argument('--state', choices=('candidate', 'all'), default='candidate',
                        help='check unverified portals only (default) or verified ones too')
    verify.add_argument('--promote', action='store_true',
                        help='mark candidates that passed the last check as verified in companies.json; no network')
    verify.add_argument('--minutes', type=float, default=None, help=f'time budget (default {VERIFY_MINUTES})')
    verify.set_defaults(run=cmd_verify)
    coverage = commands.add_parser('coverage', help='write the company coverage table (CSV and Markdown)')
    coverage.add_argument('path', nargs='?', default=None, help='CSV file (default: data/acceptance/coverage-<time>.csv)')
    coverage.set_defaults(run=cmd_coverage)
    report = commands.add_parser('report', help='write the acceptance report for the latest run')
    report.add_argument('path', nargs='?', default=None, help='Markdown file (default: data/acceptance/report-<time>.md)')
    report.set_defaults(run=cmd_report)
    commands.add_parser('doctor', help='check the installation without network access').set_defaults(run=cmd_doctor)
    export = commands.add_parser('export', help='write every saved job to a CSV file')
    export.add_argument('path', nargs='?', default=None, help='output file (default: data/pega-radar-jobs-<date>.csv)')
    export.set_defaults(run=cmd_export)
    commands.add_parser('rescore', help='re-rank saved jobs after editing config.json or companies.json').set_defaults(run=cmd_rescore)
    args = parser.parse_args(argv)
    try:
        return args.run(args)
    except KeyboardInterrupt:
        print('Stopped.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
