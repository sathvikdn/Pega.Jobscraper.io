"""Pega Radar command line.

    python radar.py serve [--port N] [--no-browser]   open the local website
    python radar.py scan [--minutes N] [--open]       search every source once
    python radar.py doctor                            check the installation (no network)
    python radar.py export [path]                     write every saved job to a CSV file
    python radar.py rescore                           re-rank saved jobs after editing config/companies

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
DATABASE_NAME = 'radar.sqlite3'
MODULES = ('radar.model', 'radar.net', 'radar.store', 'radar.rank', 'radar.scan', 'radar.sources', 'radar.server')
EXPORT_COLUMNS = ('score', 'title', 'company', 'employer_type', 'city', 'location', 'posted_at', 'experience_min',
                  'experience_max', 'salary_min_lpa', 'salary_max_lpa', 'status', 'saved', 'hidden', 'notes', 'sources', 'url',
                  'apply_url', 'requisition_id', 'first_seen_at', 'last_seen_at', 'seen_at', 'id')
SCAN_EXIT = {'complete': 0, 'partial': 2}


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
            summary = scan.run_scan(config, store, minutes=args.minutes)
    except scan.ScanLocked as error:
        print(error)
        return 1
    if summary['attention']:
        print('Sources that need attention (jobs posted only there may be missing): ' + ', '.join(summary['attention']))
    if summary.get('error'):
        print('The scan failed: ' + summary['error'])
    if args.open:
        _serve(store, config, None, True)
    return SCAN_EXIT.get(summary['status'], 1)


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

    companies, problem = _read_json(COMPANIES_PATH)
    if problem:
        problems.append(problem)
    elif companies is None:
        notes.append('companies.json is missing; employer sites are not searched and employer types come from name patterns')
    else:
        entries = companies.get('companies') if isinstance(companies, dict) else None
        if not isinstance(entries, list):
            problems.append('companies.json must contain {"companies": [...]}.')
        else:
            valid = [entry for entry in entries if isinstance(entry, dict)]
            with_site = sum(1 for entry in valid if entry.get('ats'))
            by_type = {}
            for entry in valid:
                by_type[entry.get('type') or 'unknown'] = by_type.get(entry.get('type') or 'unknown', 0) + 1
            notes.append(f'companies.json: {len(entries)} employers, {with_site} with a searchable career site ('
                         + ', '.join(f'{count} {kind}' for kind, count in sorted(by_type.items())) + ')')

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
    scan.set_defaults(run=cmd_scan)
    serve = commands.add_parser('serve', help='open the local website')
    serve.add_argument('--port', type=int, default=None, help='port on 127.0.0.1 (default: config.json, 8765)')
    serve.add_argument('--no-browser', action='store_true', help='do not open a browser window')
    serve.set_defaults(run=cmd_serve)
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
