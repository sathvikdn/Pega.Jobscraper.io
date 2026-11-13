"""Read and retain exact public job descriptions without altering saved pipeline notes."""
import copy
from urllib.parse import urljoin
import requests
from campaign import RateLimiter
from verification import public_url
from storage import now

DESCRIPTION_FIELDS = (
    'description_text', 'description_source_url', 'description_checked_at', 'description_complete',
    'job_detail_status', 'job_detail_checked_at', 'job_detail_diagnostic', 'description_identity',
    'evidence_scope', 'skills', 'experience_evidence', 'experience_min', 'experience_max',
    'required_certifications', 'certification_evidence', 'requirements_unknown',
    'track', 'relevance', 'summary', 'evidence', 'closing_at', 'verification_status',
    'fit', 'salary', 'pay_bucket', 'remote_eligibility',
)

class PublicDescriptionClient:
    """Bounded public HTTPS fetches; redirects cannot reach local/private addresses."""
    def __init__(self, spacing=2.5):
        import threading
        self.stop_event = threading.Event()
        self.limiter = RateLimiter(spacing)

    def get(self, url):
        diagnostic = {'url': url, 'checked_at': now()}
        try:
            current = url
            for _ in range(5):
                public_url(current)
                self.limiter.wait(current, self.stop_event)
                with requests.get(current, timeout=(8, 18), allow_redirects=False, stream=True,
                                  headers={'User-Agent': 'CareerResearch/3.0 (personal public job description check)'}) as response:
                    diagnostic.update(http_status=response.status_code, final_url=current)
                    if response.status_code in (301, 302, 303, 307, 308):
                        current = urljoin(current, response.headers.get('Location', ''))
                        continue
                    if response.status_code != 200:
                        diagnostic['error'] = 'Source returned HTTP ' + str(response.status_code)
                        return None, diagnostic
                    chunks, size = [], 0
                    for chunk in response.iter_content(32768):
                        size += len(chunk)
                        if size > 3_000_000:
                            diagnostic['error'] = 'Page exceeded the full-description capture limit.'
                            return None, diagnostic
                        chunks.append(chunk)
                    return b''.join(chunks).decode(response.encoding or 'utf-8', errors='replace'), diagnostic
            diagnostic['error'] = 'Too many redirects.'
        except (requests.RequestException, ValueError, OSError) as error:
            diagnostic['error'] = 'Public description could not be read: ' + str(error)[:180]
        return None, diagnostic

def description_snapshot(job):
    return {key: copy.deepcopy(job[key]) for key in DESCRIPTION_FIELDS if key in job}

def overlay_description(job, saved):
    if not saved:
        return job
    saved_time = saved.get('job_detail_checked_at') or saved.get('description_checked_at') or ''
    current_time = job.get('job_detail_checked_at') or job.get('description_checked_at') or ''
    # A new scanner snapshot takes precedence over an older manual refresh.
    if current_time and saved_time < current_time:
        return job
    updated = copy.deepcopy(job)
    updated.update(description_snapshot(saved))
    return updated
