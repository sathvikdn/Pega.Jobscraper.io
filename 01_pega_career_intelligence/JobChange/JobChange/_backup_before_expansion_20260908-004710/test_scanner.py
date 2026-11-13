"""Offline scanner regressions: scoped evidence, ownership, request budgets and audits."""
import json
import logging
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / ".deps"))
sys.path.insert(0, str(BASE))
with patch("logging.FileHandler", side_effect=lambda *a, **k: logging.NullHandler()):
    import pega_job_hunter as hunter

TARGET = {"name": "Citi India", "keywords": ["citi", "citibank"]}


def linkedin_card(number, employer="Citi", title="Software Engineer", nested=True):
    body = (f'<h3 class="base-search-card__title">{title}</h3>'
            f'<h4 class="base-search-card__subtitle">{employer}</h4>'
            f'<a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/{number}?trk=search">view</a>')
    return '<li><div class="base-card"><div class="job-search-card">' + body + '</div></div></li>' if nested else '<li>' + body + '</li>'


class ScannerTests(unittest.TestCase):
    def setUp(self):
        hunter._jd_check_cache.clear()
        hunter._broad_linkedin_cache.clear()
        hunter._broad_linkedin_audit.clear()
        hunter.FETCH_AUDIT.clear()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(hunter.time, "sleep"))

    def check_html(self, html):
        with patch.object(hunter, "fetch", return_value=html):
            return hunter._fetch_jd_pega_check("https://example.com/jobs/123")

    def test_recommendations_outside_role_do_not_match(self):
        self.assertFalse(self.check_html('<div class="description__text">Java backend development.</div><aside>Recommended: Pega Developer</aside>'))

    def test_full_page_branding_is_not_a_job_description(self):
        self.assertFalse(self.check_html('<article><h1>Our careers</h1><p>Join Pega in India</p></article>'))
        self.assertIn("No supported role-description", hunter.FETCH_AUDIT[-1]["error"])

    def test_structured_description_is_supported(self):
        data = {"@graph": [{"@type": "Organization", "description": "Pega employer"}, {"@type": "JobPosting", "description": "<p>Build PRPC integrations.</p>"}]}
        self.assertTrue(self.check_html('<script type="application/ld+json">' + json.dumps(data) + '</script>'))

    def test_structured_company_branding_does_not_match(self):
        data = [{"@type": "Organization", "description": "Pega employer"}, {"@type": "JobPosting", "description": "Build Java services."}]
        self.assertFalse(self.check_html('<script type="application/ld+json">' + json.dumps(data) + '</script>'))

    def test_multi_job_listing_is_not_an_individual_role(self):
        data = [{"@type": "JobPosting", "description": "Java"}, {"@type": "JobPosting", "description": "Pega"}]
        self.assertFalse(self.check_html('<script type="application/ld+json">' + json.dumps(data) + '</script>'))

    def test_cache_keeps_long_url_identity_and_removes_tracking(self):
        prefix = "https://example.com/" + "a" * 205
        with patch.object(hunter, "fetch", side_effect=['<div class="job-description">Pega</div>', '<div class="job-description">Java</div>']) as fetch:
            self.assertTrue(hunter._fetch_jd_pega_check(prefix + "?id=1&utm_source=a"))
            self.assertTrue(hunter._fetch_jd_pega_check(prefix + "?id=1&utm_source=b"))
            self.assertFalse(hunter._fetch_jd_pega_check(prefix + "?id=2"))
            self.assertEqual(fetch.call_count, 2)

    def test_linkedin_skips_other_employers_and_deduplicates_before_cap(self):
        html = ''.join(linkedin_card(i, "Unrelated Ltd") for i in range(100, 103))
        html += ''.join(linkedin_card(i) for i in range(200, 206))
        with patch.object(hunter, "_fetch_jd_pega_check", return_value=True) as check:
            jobs = hunter._parse_linkedin_cards(html, TARGET["name"], target_company=TARGET)
        checked = [call.args[0] for call in check.call_args_list]
        self.assertEqual(len(jobs), 5)
        self.assertEqual(len(set(checked)), 5)
        self.assertTrue(all('/20' in url for url in checked))

    def test_broad_linkedin_preserves_multiple_employers(self):
        html = linkedin_card(100, "Citi", "Pega Developer") + linkedin_card(200, "Example Ltd", "Pega Developer")
        jobs = hunter._parse_linkedin_cards(html, "")
        self.assertEqual({job.company for job in jobs}, {"Citi", "Example Ltd"})

    def test_targeted_linkedin_passes_company_dictionary(self):
        job = hunter.Job("Pega Developer", "Citi", "India", "LinkedIn", "https://www.linkedin.com/jobs/view/123")
        with patch.object(hunter, "fetch", return_value="html"), patch.object(hunter, "_parse_linkedin_cards", return_value=[job]) as parse:
            hunter.search_linkedin(TARGET)
        self.assertEqual(parse.call_args.kwargs["target_company"], TARGET)

    def test_indeed_skips_unrelated_and_nested_duplicates(self):
        html = ''
        for number, company in [(1, "Other Ltd"), (2, "Citi")]:
            html += f'<div class="job_seen_beacon"><div class="resultContent"><h2 class="jobTitle"><a href="/viewjob?jk={number}">Software Engineer</a></h2><span class="companyName">{company}</span></div></div>'
        with patch.object(hunter, "fetch", return_value=html), patch.object(hunter, "_fetch_jd_pega_check", return_value=True) as check:
            jobs = hunter.search_indeed(TARGET)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(check.call_count, 1)
        self.assertIn("jk=2", check.call_args.args[0])

    def test_career_portal_retains_shared_ats_tenant_path(self):
        target = {"name": "Citi", "keywords": ["citi"], "career_url": "https://shared.example.com/Citi"}
        urls = ["https://shared.example.com/Other/job/1", "https://shared.example.com/Citi/blogging", "https://evil.example.com/Citi/job/3"]
        html = ''.join(f'<div class="g"><a href="{url}"><h3>Pega jobs</h3></a></div>' for url in urls)
        with patch.object(hunter, "fetch", return_value=html) as fetch, patch.object(hunter, "_fetch_jd_pega_check", return_value=False) as check:
            self.assertEqual(hunter.search_career_portal(target), [])
        self.assertEqual(check.call_count, 1)
        self.assertEqual(check.call_args.args[0], urls[1])
        self.assertIn("site%3Ashared.example.com%2FCiti", fetch.call_args.args[0])

    def no_other_sources(self):
        for name in ("search_naukri", "search_linkedin", "search_indeed", "search_google", "search_career_portal"):
            self.stack.enter_context(patch.object(hunter, name, return_value=[]))

    def test_broad_cached_failures_are_visible(self):
        self.no_other_sources()
        hunter._broad_linkedin_cache["india"] = []
        hunter._broad_linkedin_audit["india"] = [{"url": "https://linkedin.com", "http_status": 429}]
        hunter.scan_company(TARGET)
        item = hunter.LAST_SCAN_DIAGNOSTICS[TARGET["name"]][-1]
        self.assertEqual(item["source"], "Broad LinkedIn")
        self.assertEqual(item["state"], "unavailable")
        self.assertTrue(item["cached"])
        self.assertEqual(item["failures"][0]["http_status"], 429)

    def test_broad_exception_is_not_silent(self):
        self.no_other_sources()
        with patch.object(hunter, "match_broad_jobs_to_company", side_effect=RuntimeError("parse failure")):
            hunter.scan_company(TARGET)
        item = hunter.LAST_SCAN_DIAGNOSTICS[TARGET["name"]][-1]
        self.assertEqual(item["state"], "error")
        self.assertIn("parse failure", item["error"])


if __name__ == "__main__":
    unittest.main()
