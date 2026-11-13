"""Offline pagination and saved-result regressions.

May run from research_work or after installation beside campaign.py:
python -B research_work/test_pagination_recovery.py
All response bodies are fixtures; real network requests are forbidden.
"""
import copy
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

HERE = Path(__file__).resolve().parent
PORTAL = HERE if (HERE / "campaign.py").exists() else HERE.parent / "portal"
sys.path.insert(0, str(PORTAL / ".deps"))
sys.path.insert(0, str(PORTAL))
import campaign
import portal_scan

TARGET = {
    "target_id": "gcc-example",
    "name": "Example Bank",
    "category": "gcc",
    "keywords": ["Example Bank"],
    "location": "India",
}
EMPTY = '<div class="empty">No jobs found</div>'


def card(number, company="Example Bank", title="Pega Developer"):
    return (
        '<li><div class="base-card">'
        '<h3 class="base-search-card__title">' + title + '</h3>'
        '<h4 class="base-search-card__subtitle">' + company + '</h4>'
        '<a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/'
        + str(number) + '?trk=fixture">View</a>'
        '<span class="job-search-card__location">Bengaluru, India</span>'
        '</div></li>'
    )


def page(start, count=10):
    return "".join(card(n) for n in range(start, start + count))


class FixtureClient:
    def __init__(self, responses, stop_event=None):
        self.responses = list(responses)
        self.urls = []
        self.stop_event = stop_event

    def get(self, url):
        self.urls.append(url)
        if not self.responses:
            raise AssertionError("Unexpected additional request: " + url)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            if self.stop_event is not None and isinstance(response, campaign.Cancelled):
                self.stop_event.set()
            raise response
        html, status, *extra = response
        diagnostic = {"url": url, "http_status": status,
                      "checked_at": "2026-09-08T10:00:00+00:00"}
        if html is None:
            diagnostic["error"] = "Fixture access rejection"
        if extra:
            diagnostic.update(extra[0])
        return html, diagnostic


class PaginationRecoveryTests(unittest.TestCase):
    def setUp(self):
        network = patch.object(
            campaign.urllib.request, "urlopen",
            side_effect=AssertionError("Real network is forbidden in this suite"),
        )
        network.start()
        self.addCleanup(network.stop)

    def test_empty_expanded_and_fallback_are_not_a_repeated_page(self):
        client = FixtureClient([(EMPTY, 200), (EMPTY, 200)])
        result = campaign.check_target(TARGET, client)
        self.assertEqual(result["jobs"], [])
        self.assertEqual(result["status"], "no_matches")
        self.assertFalse(result["partial"])
        self.assertEqual(len(client.urls), 2)
        self.assertNotEqual(parse_qs(urlsplit(client.urls[0]).query)["keywords"],
                            parse_qs(urlsplit(client.urls[1]).query)["keywords"])

    def test_short_page_retains_every_job_and_stops(self):
        client = FixtureClient([(page(100, 3), 200)])
        result = campaign.check_target(TARGET, client)
        self.assertEqual(len(result["jobs"]), 3)
        self.assertEqual(result["status"], "results")
        self.assertFalse(result["partial"])
        self.assertEqual(len(client.urls), 1)

    def test_repeated_full_page_stops_without_duplicates_and_marks_partial(self):
        client = FixtureClient([(page(100), 200), (page(100), 200)])
        result = campaign.check_target(TARGET, client)
        self.assertEqual(len(result["jobs"]), 10)
        self.assertTrue(result["partial"])
        self.assertEqual(len(client.urls), 2)
        self.assertTrue(any(d.get("pagination_incomplete")
                            for d in result["diagnostics"]))

    def test_five_page_cap_retains_all_pages_and_correct_offsets(self):
        client = FixtureClient([(page(n), 200) for n in range(100, 150, 10)])
        result = campaign.check_target(TARGET, client)
        self.assertEqual(len(result["jobs"]), 50)
        self.assertEqual(len({j["url"] for j in result["jobs"]}), 50)
        self.assertEqual([int(parse_qs(urlsplit(u).query)["start"][0])
                          for u in client.urls], [0, 10, 20, 30, 40])
        self.assertTrue(result["partial"])
        self.assertTrue(result["diagnostics"][-1]["pagination_capped"])

    def test_later_access_rejection_keeps_earlier_results(self):
        for status in (401, 403, 429, 999):
            with self.subTest(status=status):
                client = FixtureClient([(page(100), 200), (None, status)])
                result = campaign.check_target(TARGET, client)
                self.assertEqual(len(result["jobs"]), 10)
                self.assertEqual(result["status"], "results")
                self.assertTrue(result["partial"])
                self.assertEqual(len(client.urls), 2)
                self.assertTrue(all(j["source"] == "LinkedIn public jobs"
                                    for j in result["jobs"]))

    def test_access_rejection_stops_generic_description_requests(self):
        listing = page(100, 9) + card(109, title="Software Engineer")
        client = FixtureClient([(listing, 200), (None, 429)])
        result = campaign.check_target(TARGET, client)
        self.assertEqual(len(client.urls), 2)
        self.assertEqual(len(result["jobs"]), 9)
        self.assertTrue(result["partial"])
        self.assertTrue(any(d.get("generic_jds_not_checked")
                            for d in result["diagnostics"]))

    def test_later_parse_failure_does_not_erase_first_page(self):
        original = campaign.parse_cards

        def parse(html, target):
            if html == "malformed-fixture":
                raise ValueError("fixture parse failure")
            return original(html, target)

        client = FixtureClient([(page(100), 200), ("malformed-fixture", 200)])
        with patch.object(campaign, "parse_cards", side_effect=parse):
            result = campaign.check_target(TARGET, client)
        self.assertEqual(len(result["jobs"]), 10)
        self.assertTrue(result["partial"])
        self.assertTrue(any("parse failed" in d.get("error", "").lower()
                            for d in result["diagnostics"]))

    def test_cancel_after_first_page_returns_pending_with_saved_cards(self):
        target = {**TARGET, "career_url": "https://careers.example.com"}
        client = FixtureClient([(page(100), 200), campaign.Cancelled()])
        result = campaign.check_target(target, client)
        self.assertEqual(result["status"], "pending")
        self.assertTrue(result["partial"])
        self.assertEqual(len(result["jobs"]), 10)
        self.assertEqual(len(client.urls), 2)

    def test_cancel_during_employer_fallback_preserves_prior_cards(self):
        target = {**TARGET, "career_url": "https://careers.example.com"}
        client = FixtureClient([(page(100), 200), (None, 429), campaign.Cancelled()])
        result = campaign.check_target(target, client)
        self.assertEqual(result["status"], "pending")
        self.assertTrue(result["partial"])
        self.assertEqual(len(result["jobs"]), 10)

    def test_employer_filter_precedes_generic_jd_and_offset_uses_raw_cards(self):
        listing = "".join(card(n, "Other Employer", "Software Engineer")
                          for n in range(100, 109)) + card(109)
        client = FixtureClient([(listing, 200), (EMPTY, 200)])
        result = campaign.check_target(TARGET, client)
        self.assertEqual([j["company"] for j in result["jobs"]], ["Example Bank"])
        self.assertEqual(result["jobs"][0]["url"],
                         "https://www.linkedin.com/jobs/view/109")
        self.assertEqual(len(client.urls), 2)
        self.assertEqual(parse_qs(urlsplit(client.urls[1]).query)["start"], ["10"])

    def test_invalid_generic_jd_keeps_identity_checks_and_allows_query_fallback(self):
        body = ('<h1 class="top-card-layout__title">Different Role</h1>'
                '<a class="topcard__org-name-link">Other Employer</a>'
                '<div class="description__text">Pega PRPC development</div>')
        client = FixtureClient([
            (card(123, title="Software Engineer"), 200),
            (body, 200, {"final_url": "https://www.linkedin.com/jobs/view/999"}),
            (EMPTY, 200),  # No verified Pega JD: alternate listing query remains necessary.
        ])
        result = campaign.check_target(TARGET, client)
        self.assertEqual(result["jobs"], [])
        self.assertTrue(result["partial"])

    def test_cancelled_checkpoint_resumes_selected_target_and_keeps_old_jobs(self):
        stop = threading.Event()
        old = campaign.make_job("Pega Developer", TARGET["name"], "India",
                                "https://www.linkedin.com/jobs/view/99",
                                "Employer", "2026-09-01")
        other = {**TARGET, "target_id": "gcc-unselected", "name": "Unselected Bank",
                 "keywords": ["Unselected Bank"], "status": "results",
                 "checked_at": "2026-09-01",
                 "jobs": [{**old, "id": "untouched", "company": "Unselected Bank",
                           "url": "https://example.com/unselected"}]}
        with tempfile.TemporaryDirectory(prefix="pagination-recovery-") as folder:
            path = Path(folder) / "checkpoint.json"
            campaign.save_campaign({
                "status": "complete",
                "targets": [{**TARGET, "status": "results", "jobs": [old]}, other],
            }, path)
            client = FixtureClient([(page(100), 200), campaign.Cancelled()], stop)
            with patch.object(campaign, "PublicClient", return_value=client):
                paused = campaign.run_campaign(
                    target_ids=[TARGET["target_id"]], force=True, workers=1,
                    output_path=path, data=[TARGET, other], stop_event=stop,
                )
            saved = json.loads(path.read_text(encoding="utf-8"))
            selected = next(t for t in saved["targets"]
                            if t["target_id"] == TARGET["target_id"])
            self.assertEqual(paused["status"], "cancelled")
            self.assertEqual(selected["status"], "pending")
            self.assertEqual(len(selected["jobs"]), 11)
            self.assertEqual(next(t for t in saved["targets"]
                                  if t["target_id"] == other["target_id"]), other)
            stop.clear()
            client = FixtureClient([(page(200, 1), 200)], stop)
            with patch.object(campaign, "PublicClient", return_value=client):
                resumed = campaign.run_campaign(
                    target_ids=[TARGET["target_id"]], force=False, workers=1,
                    output_path=path, data=[TARGET, other], stop_event=stop,
                )
            selected = next(t for t in resumed["targets"]
                            if t["target_id"] == TARGET["target_id"])
            self.assertEqual(resumed["status"], "complete")
            self.assertEqual(len(selected["jobs"]), 12)
            self.assertEqual(next(t for t in resumed["targets"]
                                  if t["target_id"] == other["target_id"]), other)
            self.assertEqual(len(client.urls), 1)

    def test_baseline_stays_a_set_when_new_description_replaces_cached_job(self):
        url = "https://www.linkedin.com/jobs/view/123"
        old = {"id": "stable-note-id", "company": TARGET["name"],
               "title": "Pega Developer", "url": url, "location": "India",
               "status": "uncertain", "checked_at": "2026-09-01"}
        newer = {**old, "id": "engine-generated-id",
                 "checked_at": "2026-09-08", "job_detail_status": "read",
                 "job_detail_checked_at": "2026-09-08"}
        fresh = {**newer, "id": "new-role",
                 "url": "https://www.linkedin.com/jobs/view/456"}
        result = portal_scan.grouped_results(
            [old], [TARGET], {"targets": [{**TARGET, "jobs": [newer, fresh]}]},
            baseline=["stable-note-id"],
        )
        jobs = {j["id"]: j for j in result[0]["jobs"]}
        self.assertFalse(jobs["stable-note-id"]["is_new"])
        self.assertTrue(jobs["new-role"]["is_new"])
        self.assertEqual(result[0]["new_count"], 1)
        self.assertEqual(old["id"], "stable-note-id")

    def test_no_baseline_does_not_label_all_saved_roles_new(self):
        old = {"id": "stable", "company": TARGET["name"],
               "title": "Pega Developer",
               "url": "https://www.linkedin.com/jobs/view/123",
               "location": "India", "status": "uncertain"}
        result = portal_scan.grouped_results([old], [TARGET], {"targets": []})
        self.assertFalse(result[0]["jobs"][0]["is_new"])
        self.assertEqual(result[0]["new_count"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

