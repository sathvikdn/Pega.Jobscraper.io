"""Offline regression tests for sourced full job descriptions and refreshes."""
import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import campaign

URL = "https://www.linkedin.com/jobs/view/123"


class Client:
    def __init__(self, html, checked="2026-09-09", final_url=None, status=200):
        self.html, self.checked, self.final_url, self.status = html, checked, final_url, status

    def get(self, url):
        return self.html, {"url": url, "final_url": self.final_url or url,
                           "http_status": self.status, "checked_at": self.checked}


def seed():
    return campaign.make_job("Pega Developer", "Citi", "India", URL, "LinkedIn public jobs", "2026-09-01")


def page(description):
    return '<h1 class="top-card-layout__title">Pega Developer</h1><a class="topcard__org-name-link">Citi</a><div class="description__text">' + description + '</div>'


def snapshot():
    return campaign.enrich_job(seed(), Client(page("<p>Develop Pega cases.</p><p>Minimum 6-7 years of experience. CLSA required.</p>"), "2026-09-02"))


class DescriptionCaptureTests(unittest.TestCase):
    def test_paragraphs_lists_and_inline_content_are_readable(self):
        text, _ = campaign.role_description(page('<p>Build <strong>Pega</strong> cases &amp; workflows.</p><p>Requirements:</p><ul><li>REST APIs</li><li>4-6 years of experience</li></ul><p>Location: Bengaluru<br>Hybrid work</p>'))
        self.assertEqual(text, "Build Pega cases & workflows.\n\nRequirements:\n\n- REST APIs\n\n- 4-6 years of experience\n\nLocation: Bengaluru\nHybrid work")

    def test_no_synthetic_summary_is_substituted_for_actual_description(self):
        result = campaign.enrich_job(seed(), Client(page("<p>Develop Pega cases.</p><p>Build REST APIs.</p>")))
        self.assertEqual(result["description_text"], "Develop Pega cases.\n\nBuild REST APIs.")
        self.assertTrue(result["description_complete"])
        self.assertEqual(result["description_source_url"], URL)
        self.assertEqual(result["description_checked_at"], "2026-09-09")
        self.assertNotEqual(result["description_text"], result["summary"])

    def test_jsonld_html_and_plain_paragraphs(self):
        for raw, expected in [("<p>Pega development.</p><p>Four years.</p>", "Pega development.\n\nFour years."),
                              ("Pega development.\n\nFour years.", "Pega development.\n\nFour years.")]:
            posting = {"@type": "JobPosting", "title": "Pega Developer", "description": raw, "url": URL}
            result = campaign.enrich_job(seed(), Client('<script type="application/ld+json">' + json.dumps(posting) + '</script>'))
            self.assertEqual(result["description_text"], expected)

    def test_recommended_jobs_and_branding_are_excluded_from_role(self):
        html = '<aside><div class="job-description">Pega Engineer 12 years</div></aside>' + page('<p>Java backend development.</p><aside>Pega jobs</aside><div class="similar-jobs">Pega architect</div><div class="company-branding">Pega</div>')
        result = campaign.enrich_job(seed(), Client(html))
        self.assertEqual(result["description_text"], "Java backend development.")
        self.assertEqual(result["relevance"], "unrelated")
        self.assertNotIn("Pega", result["skills"])

    def test_multiple_individual_descriptions_are_ambiguous(self):
        html = '<div class="job-description">Pega</div><div class="job-description">Java</div>'
        self.assertEqual(campaign.role_description(html), ("", None))

    def test_successful_reread_clears_old_experience_certification_and_fit(self):
        old = snapshot()
        self.assertEqual((old["experience_min"], old["experience_max"]), (6, 7))
        refreshed = campaign.enrich_job(old, Client(page("<p>Develop Pega cases with REST APIs.</p>")))
        self.assertIsNone(refreshed["experience_min"])
        self.assertIsNone(refreshed["experience_max"])
        self.assertEqual(refreshed["experience_evidence"], [])
        self.assertEqual(refreshed["required_certifications"], [])
        self.assertEqual(refreshed["certification_evidence"], [])
        self.assertEqual(refreshed["fit"], "possible")
        self.assertFalse(any("6+ years" in x or "requires lead" in x for x in refreshed["requirements_unknown"]))

    def test_successful_nonpega_reread_overrides_old_pega_title_and_jd(self):
        refreshed = campaign.enrich_job(snapshot(), Client(page("<p>Build Java microservices.</p>")))
        self.assertEqual(refreshed["description_checked_at"], "2026-09-09")
        self.assertEqual(refreshed["description_text"], "Build Java microservices.")
        self.assertEqual(refreshed["relevance"], "unrelated")
        self.assertEqual(refreshed["track"], "unrelated")
        self.assertNotIn("Pega", refreshed["skills"])

    def test_failed_missing_or_mismatched_role_keeps_last_successful_snapshot(self):
        old = snapshot()
        scenarios = [Client(None, status=429), Client('<p>Welcome to our careers</p>'),
                     Client(page("Pega"), final_url="https://www.linkedin.com/jobs"),
                     Client('<h1 class="top-card-layout__title">Java Developer</h1><div class="description__text">Pega</div>')]
        for client in scenarios:
            with self.subTest(html=client.html):
                result = campaign.enrich_job(old, client)
                for key in ("description_text", "description_source_url", "description_checked_at", "description_complete", "experience_min", "experience_max"):
                    self.assertEqual(result[key], old[key])
                self.assertNotEqual(result["job_detail_status"], "read")
                self.assertEqual(result["job_detail_checked_at"], "2026-09-09")

    def test_structured_other_url_is_not_the_saved_vacancy(self):
        value = {"@type": "JobPosting", "title": "Pega Developer", "description": "Pega", "url": "https://www.linkedin.com/jobs/view/999"}
        result = campaign.enrich_job(snapshot(), Client('<script type="application/ld+json">' + json.dumps(value) + '</script>'))
        self.assertEqual(result["job_detail_status"], "identity_unconfirmed")
        self.assertEqual(result["description_checked_at"], "2026-09-02")

    def test_failed_first_fetch_cannot_claim_a_complete_description(self):
        result = campaign.enrich_job(seed(), Client(None, status=403))
        self.assertFalse(result["description_complete"])
        self.assertFalse(result["description_text"])
        self.assertIsNone(result["description_checked_at"])

    def test_refresh_propagates_snapshot_and_clears_stale_duplicate_years(self):
        old = snapshot()
        other = copy.deepcopy(old)
        other.update(id="other-id", notes="Keep my note", experience_min=12, experience_max=14)
        targets = [{"target_id": "one", "name": "Citi", "status": "results", "jobs": [old]},
                   {"target_id": "two", "name": "Citi", "status": "results", "jobs": [other]}]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "results.json"
            campaign.save_campaign({"targets": targets}, path)
            with patch.object(campaign, "PublicClient", return_value=Client(page("<p>Build Pega cases.</p><p>Use REST APIs.</p>"))):
                result = campaign.enrich_campaign(path, target_ids=["one"], force=True)
        first, duplicate = result["targets"][0]["jobs"][0], result["targets"][1]["jobs"][0]
        for field in ("description_text", "description_source_url", "description_checked_at", "description_complete"):
            self.assertEqual(first[field], duplicate[field])
        self.assertIsNone(duplicate["experience_min"])
        self.assertIsNone(duplicate["experience_max"])
        self.assertEqual(duplicate["notes"], "Keep my note")
        self.assertEqual(duplicate["id"], "other-id")

    def test_failed_refresh_preserves_each_duplicates_own_snapshot(self):
        old, fresh = snapshot(), campaign.enrich_job(seed(), Client(page("Pega with Kafka."), "2026-09-05"))
        targets = [{"target_id": "one", "name": "Citi", "status": "results", "jobs": [old]},
                   {"target_id": "two", "name": "Citi", "status": "results", "jobs": [fresh]}]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "results.json"
            campaign.save_campaign({"targets": targets}, path)
            with patch.object(campaign, "PublicClient", return_value=Client(None, status=429)):
                result = campaign.enrich_campaign(path, target_ids=["one"], force=True)
        duplicate = result["targets"][1]["jobs"][0]
        self.assertEqual(duplicate["description_checked_at"], "2026-09-05")
        self.assertEqual(duplicate["description_text"], "Pega with Kafka.")
        self.assertEqual(duplicate["job_detail_status"], "unavailable")

    def test_rediscovered_card_keeps_snapshot_until_next_detail_fetch(self):
        old = snapshot()
        result = campaign.retain_previous_jobs({"jobs": [seed()]}, {"jobs": [old]})["jobs"][0]
        self.assertEqual(result["description_text"], old["description_text"])
        self.assertEqual(result["description_checked_at"], "2026-09-02")
        self.assertNotIn("job_detail_status", result)
        failed = campaign.enrich_job(result, Client(None, status=429))
        self.assertEqual(failed["description_checked_at"], "2026-09-02")

    def test_nested_similar_job_markup_never_becomes_the_description(self):
        html = page('<p>Build Java.</p><aside><div class="show-more-less-html__markup">Pega job</div></aside>')
        self.assertEqual(campaign.role_description(html)[0], "Build Java.")

    def test_truncated_response_cannot_refresh_a_complete_snapshot(self):
        class TruncatedClient:
            def get(self, url):
                return page("Develop Pega."), {"url": url, "checked_at": "2026-09-09", "content_truncated": True}
        result = campaign.enrich_job(snapshot(), TruncatedClient())
        self.assertEqual(result["description_checked_at"], "2026-09-02")
        self.assertEqual(result["job_detail_status"], "description_missing")

    def test_employer_index_needs_an_individual_role_url(self):
        raw = {"@type": "JobPosting", "title": "Pega Developer", "description": "Pega development.\n\nBuild REST APIs.", "hiringOrganization": {"name": "Citi"}}
        def employer_page(value):
            return '<script type="application/ld+json">' + json.dumps(value) + '</script>'
        target = {"name": "Citi"}
        self.assertEqual(campaign.employer_structured(employer_page(raw), target, "https://example.com/careers", "2026-09-09"), [])
        raw["url"] = "/jobs/123"
        jobs = campaign.employer_structured(employer_page(raw), target, "https://example.com/careers", "2026-09-09")
        self.assertEqual(jobs[0]["description_source_url"], "https://example.com/jobs/123")
        self.assertEqual(jobs[0]["description_text"], raw["description"])

    def test_fresh_successful_search_discards_roles_not_rediscovered(self):
        target = {"target_id": "citi", "name": "Citi", "category": "gcc", "location": "India"}
        for status in ("results", "no_matches"):
            new_job = {**seed(), "id": "new", "url": "https://www.linkedin.com/jobs/view/999"}
            fresh_jobs = [new_job] if status == "results" else []
            with self.subTest(status=status), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "results.json"
                campaign.save_campaign({"targets": [{**target, "status": "results", "jobs": [snapshot()]}]}, path)
                checked = {**target, "status": status, "checked_at": "2026-09-10", "jobs": fresh_jobs}
                with patch.object(campaign, "check_target", return_value=checked):
                    result = campaign.run_campaign(data=[target], output_path=path, force=True)
                jobs = result["targets"][0]["jobs"]
                self.assertEqual([job["url"] for job in jobs], [job["url"] for job in fresh_jobs])
                self.assertEqual(result["targets"][0]["retained_job_count"], 0)

    def test_normal_resume_keeps_already_checked_jobs_without_refetching(self):
        target = {"target_id": "citi", "name": "Citi", "category": "gcc", "location": "India"}
        old = snapshot()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "results.json"
            campaign.save_campaign({"targets": [{**target, "status": "results", "jobs": [old]}]}, path)
            with patch.object(campaign, "check_target") as check:
                result = campaign.run_campaign(data=[target], output_path=path)
                check.assert_not_called()
        self.assertEqual(result["targets"][0]["jobs"], [old])

    def test_paused_fresh_search_resumes_with_replacement_policy(self):
        target = {"target_id": "citi", "name": "Citi", "category": "gcc", "location": "India"}
        stop = threading.Event()
        stop.set()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "results.json"
            campaign.save_campaign({"targets": [{**target, "status": "results", "jobs": [snapshot()]}]}, path)
            with patch.object(campaign, "check_target") as check:
                paused = campaign.run_campaign(data=[target], output_path=path, force=True, stop_event=stop)
                check.assert_not_called()
            self.assertTrue(paused["targets"][0]["replace_previous_on_success"])
            self.assertEqual(paused["targets"][0]["jobs"][0]["search_presence"], "not_rediscovered")
            checked = {**target, "status": "no_matches", "checked_at": "2026-09-10", "jobs": []}
            with patch.object(campaign, "check_target", return_value=checked):
                resumed = campaign.run_campaign(data=[target], output_path=path)
            self.assertEqual(resumed["targets"][0]["jobs"], [])

    def test_failed_fresh_search_preserves_but_does_not_rediscover_old_job(self):
        target = {"target_id": "citi", "name": "Citi", "category": "gcc", "location": "India"}
        old = snapshot()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "results.json"
            campaign.save_campaign({"targets": [{**target, "status": "results", "jobs": [old]}]}, path)
            checked = {**target, "status": "blocked", "checked_at": "2026-09-10", "jobs": []}
            with patch.object(campaign, "check_target", return_value=checked):
                result = campaign.run_campaign(data=[target], output_path=path, force=True)
        saved = result["targets"][0]["jobs"][0]
        self.assertEqual(saved["description_text"], old["description_text"])
        self.assertEqual(saved["description_checked_at"], "2026-09-02")
        self.assertEqual(saved["search_presence"], "not_rediscovered")
        self.assertNotEqual(saved["verification_status"], "verified")

    def test_search_queries_only_request_pega_or_prpc(self):
        target = {"name": "Citi", "target_id": "gcc-citi", "category": "gcc", "location": "India"}
        for expanded in (True, False):
            keywords = parse_qs(urlsplit(campaign.query_url(target, expanded)).query)["keywords"][0]
            self.assertIn("pega", keywords.lower())
            for broad_word in ("workflow", "BPM", "integration engineer", "application engineer"):
                self.assertNotIn(broad_word, keywords)


if __name__ == "__main__":
    unittest.main()
