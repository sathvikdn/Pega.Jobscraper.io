"""Create synthetic data for local browser review, never for a live job search.

Run from the project folder, using an explicit new folder under the OS temp directory:
    python -B -m tests.ui_fixture /tmp/pega-radar-ui-review
Then point the existing server at that folder with PEGA_RADAR_DATA.

This helper makes no network requests, starts no server or scanner, and is not a
unittest-discovery module. Every employer, role and source outcome below is fictional.
"""

from __future__ import annotations

import argparse
import tempfile
from datetime import date, timedelta
from pathlib import Path

from radar.model import make_job, make_result
from radar.store import Store


def create_fixture(data_dir: Path) -> Path:
    """Create a fresh, explicitly selected temporary database and return its path."""
    data_dir = Path(data_dir).expanduser().resolve()
    temporary_roots = {Path(tempfile.gettempdir()).resolve()}
    if Path('/tmp').is_dir():
        temporary_roots.add(Path('/tmp').resolve())
    if not any(data_dir != root and data_dir.is_relative_to(root) for root in temporary_roots):
        raise ValueError('Choose a new subfolder of the operating system temporary directory.')
    if data_dir.exists() and any(data_dir.iterdir()):
        raise ValueError('The fixture folder must be empty; existing data will never be replaced.')
    data_dir.mkdir(parents=True, exist_ok=True)
    store = Store(data_dir / 'radar.sqlite3')
    today = date.today()
    # title, employer, type, city, score, experience, advertised salary, personal state
    scenarios = [
        ('Pega Developer', 'Sample Bank', 'gcc', 'Bengaluru', 94, (3, 6), (30, 38), {}),
        ('Pega Platform Engineer', 'Example Systems', 'product', 'Bengaluru', 88, (4, 7), (None, None),
         {'saved': True}),
        ('Senior Pega Developer', 'Sample Insurance', 'gcc', 'Bengaluru', 86, (4, 6), (32, 40),
         {'saved': True, 'status': 'applied', 'seen': True, 'notes': 'Sample note: follow up next week.'}),
        ('Pega CSSA Engineer', 'Example Digital', 'product', 'Hyderabad', 79, (3, 5), (28, 34),
         {'status': 'interviewing', 'seen': True}),
        ('Pega Consultant', 'Sample Consulting', 'services', 'Pune', 52, (3, 6), (None, None),
         {'saved': True}),
        ('Pega Technical Lead', 'Example Enterprise', 'enterprise', 'Bengaluru', 44, (8, 12), (35, 45), {}),
        ('Pega Developer', 'Sample Staffing', 'staffing', 'Chennai', 38, (2, 5), (20, 25),
         {'hidden': True, 'status': 'applied', 'seen': True}),
        ('Pega Associate', 'Example Software', 'product', 'Bengaluru', 42, (0, 2), (None, None),
         {'status': 'rejected', 'seen': True}),
        ('Pega Application Engineer', 'Sample Fintech', 'product', 'Bengaluru', 91, (4, 6), (34, 42),
         {'status': 'offer', 'seen': True, 'saved': True}),
        ('Pega Engineer', 'Example Remote Team', 'gcc', 'Remote, India', 67, (None, None), (None, None), {}),
        ('Pega Senior System Architect for Enterprise Workflow and Customer Decisioning',
         'Sample Employer With A Long Name For Layout Review', 'gcc', 'Bengaluru, Karnataka, India',
         83, (4, 8), (None, None), {}),
        ('Pega Developer <img src=x onerror=alert(1)>', 'Sample <b>Plain Text</b> Employer', 'unknown',
         'Mumbai', 19, (None, None), (None, None), {}),
    ]
    run_id = store.start_run()
    for index, (title, employer, kind, city, score, experience, salary, user_state) in enumerate(scenarios, 1):
        job = make_job(
            'Sample employer site', str(index), title, employer,
            f'https://example.invalid/sample-role/{index}', city,
            posted_at=(today - timedelta(days=index % 8)).isoformat(),
            experience_min=experience[0], experience_max=experience[1],
            salary_min_lpa=salary[0], salary_max_lpa=salary[1],
            apply_url=f'https://example.invalid/sample-apply/{index}' if index % 2 else None,
            description='' if index == 10 else (
                'Synthetic data for interface testing. This is not a live vacancy.\n\n'
                'Build Pega case types, integrations and reusable components. Work with '
                'Constellation and improve application performance.\n\n'
                'Collaborate with product and engineering teams, review changes, and '
                'support accessible, reliable application experiences.'
            ),
        )
        result = make_result('Sample employer site', employer, 'ats', jobs=[job],
                             pages_complete=True, details_complete=True, employer=employer)
        result['task'] = f'fixture:employer:{index}'

        def ranker(_job, kind=kind, score=score, city=city):
            reasons = ['Pega developer role']
            if 'Bengaluru' in city:
                reasons.append('Bengaluru location')
            if kind in ('product', 'gcc'):
                reasons.append('Product or GCC employer')
            return {
                'employer_type': kind, 'score': score, 'pega_title': True, 'pega_duty': True,
                'fit': {'reasons': reasons, 'labels': {'employer_type': kind,
                                                     'bengaluru': 'Bengaluru' in city}},
            }

        saved = store.save_result(run_id, result, ranker)
        if user_state:
            store.set_state(saved['new'][0], **user_state)
    incomplete = make_result(
        'Sample job board', 'Sample job board', 'board', status='partial',
        reason='budget', error='Synthetic review scenario: some pages were not reached.',
        pages_complete=False, details_complete=False,
    )
    incomplete['task'] = 'fixture:board:partial'
    store.record_health(run_id, incomplete)
    store.finish_run(run_id, 'partial', {
        'mode': 'full', 'requested': 13, 'attempted': 13, 'completed': 12,
        'new': len(scenarios), 'attention': ['Sample job board'],
    })
    (data_dir / 'SYNTHETIC-FIXTURE.txt').write_text(
        'Local UI test data only. All roles, employers and scan outcomes are fictional.\n'
        'Do not use this folder for a real scan or application search.\n',
        encoding='utf-8',
    )
    return store.path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('data_dir', type=Path, help='A new, empty folder under the OS temporary directory')
    arguments = parser.parse_args()
    try:
        database = create_fixture(arguments.data_dir)
    except ValueError as error:
        parser.error(str(error))
    print(f'Synthetic UI fixture created: {database}')
    print('12 fictional roles. No network requests or scans were made.')
