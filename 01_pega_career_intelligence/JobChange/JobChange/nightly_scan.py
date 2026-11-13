"""Nightly automated scan: LinkedIn + career portals + job boards.

Designed to run headless from Windows Task Scheduler at midnight.
Starts the Flask app temporarily, triggers a full scan, waits for
completion, then shuts down. Results are preloaded for the morning.
"""
import json
import logging
import os
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / '.deps'))
os.chdir(str(BASE))

LOG_DIR = BASE / '_logs'
LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / f'nightly-{datetime.now().strftime("%Y%m%d-%H%M%S")}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger('nightly')


def run_nightly():
    start = time.perf_counter()
    logger.info('=' * 60)
    logger.info('NIGHTLY SCAN STARTING')
    logger.info('=' * 60)

    try:
        # Use the existing service so nightly and interactive scans share state.
        from scan_coordinator import PortalClient
        _start_portal_server()
        client = PortalClient('http://127.0.0.1:5050')

        # Get CSRF token
        boot = client.get('/api/bootstrap').get_json()
        token = boot['token']
        headers = {'Content-Type': 'application/json', 'X-Career-Token': token}

        # Check if a scan is already running
        status = client.get('/api/status').get_json()
        if status.get('running'):
            logger.warning('A scan is already running. Skipping nightly run.')
            return

        # Start a full scan (all companies, fresh)
        logger.info('Starting full scan (all targets, fresh)...')
        resp = client.post('/api/scan', json={'mode': 'all'}, headers=headers)
        result = resp.get_json()
        if resp.status_code != 200:
            logger.error('Failed to start scan: %s', result.get('error', 'unknown'))
            return
        logger.info('Scan started: %d targets', result.get('total', 0))

        # Poll until complete
        last_progress = -1
        stall_count = 0
        while True:
            time.sleep(10)
            status = client.get('/api/status').get_json()

            if not status.get('running'):
                if status.get('error'):
                    logger.error('Scan ended with error: %s', status['error'])
                else:
                    logger.info('Scan complete.')
                break

            progress = status.get('progress', 0)
            total = status.get('total', 0)
            phase = status.get('phase', '')
            company = status.get('current_company', '')

            if progress != last_progress:
                logger.info('Progress: %d/%d [%s] %s', progress, total, phase, company)
                last_progress = progress
                stall_count = 0
            else:
                stall_count += 1

            # Safety: if stalled for 30 minutes, stop
            if stall_count > 180:
                logger.error('Scan stalled for 30 minutes. Forcing stop.')
                client.post('/api/search/pause', json={}, headers=headers)
                time.sleep(5)
                break

        # Log final results
        try:
            scan_results = client.get('/api/scan-results?scope=all').get_json()
            companies = scan_results.get('companies', [])
            total_jobs = sum(len(c.get('jobs', [])) for c in companies)
            with_jobs = sum(1 for c in companies if c.get('jobs'))
            logger.info('Results: %d jobs from %d companies', total_jobs, with_jobs)

            counts = scan_results.get('policy_counts', {})
            logger.info('Recommendations: %s', counts)
        except Exception as exc:
            logger.error('Could not read results: %s', exc)

        # Log scrape analysis
        try:
            scrape = client.get('/api/scrape-log').get_json()
            summary = scrape.get('summary', {})
            logger.info('Career portals: %s/%s found jobs (%s)',
                        summary.get('success', 0), summary.get('total', 0),
                        summary.get('success_rate', '?'))
            for reason, info in summary.get('failure_reasons', {}).items():
                logger.info('  %s: %d failures', reason, info['count'])
        except Exception:
            pass

        # Log board jobs
        try:
            boards = client.get('/api/board-jobs').get_json()
            board_count = len(boards.get('jobs', []))
            logger.info('Job boards: %d additional listings', board_count)
        except Exception:
            pass

    except Exception as exc:
        logger.exception('Nightly scan crashed: %s', exc)

    elapsed = time.perf_counter() - start
    logger.info('Total runtime: %.1f minutes', elapsed / 60)
    logger.info('Log saved to: %s', log_file)
    logger.info('=' * 60)
    logger.info('NIGHTLY SCAN COMPLETE — starting portal server')
    logger.info('=' * 60)

    # Start the portal server and leave it running so results are ready
    _start_portal_server()


def _start_portal_server(port=5050):
    """Start the Flask portal in the background and create a Desktop shortcut."""
    import subprocess

    desktop = Path(os.path.expanduser("~/Desktop"))

    # Create a clickable shortcut on the Desktop
    shortcut = desktop / "Pega Jobs Today.url"
    shortcut.write_text(
        f"[InternetShortcut]\nURL=http://127.0.0.1:{port}#results\n",
        encoding="utf-8",
    )

    # Reuse only a verified portal; never terminate an unrelated port owner.
    import urllib.request
    import urllib.error
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health',timeout=5) as response:
            health=json.load(response)
        if health.get('service')!='pega-job-hunter' or not health.get('instance_token'):
            raise RuntimeError('Port is occupied by an unverified service')
        logger.info('Reusing portal instance %s',health['instance_token'])
        return
    except urllib.error.HTTPError as error:
        raise RuntimeError('Port is occupied by a service without a valid health endpoint') from error
    except urllib.error.URLError as error:
        if not isinstance(error.reason,ConnectionRefusedError):raise

    time.sleep(1)

    # Start the server as a detached background process that survives this script
    server_proc = subprocess.Popen(
        [sys.executable, "-B", "app.py", "--port", str(port)],
        cwd=str(BASE),
        stdout=open(LOG_DIR / "server-stdout.log", "w"),
        stderr=open(LOG_DIR / "server-stderr.log", "w"),
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
    )

    # Wait a moment and verify it started
    time.sleep(2)
    try:
        import urllib.request
        urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=5)
        logging.getLogger('nightly').info(
            'Portal server started on port %d (PID %d). '
            'Desktop shortcut: %s', port, server_proc.pid, shortcut
        )
    except Exception:
        logging.getLogger('nightly').warning(
            'Portal server may not have started. Try: python app.py --port %d', port
        )


if __name__ == '__main__':
    run_nightly()
