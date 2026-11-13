"""Regression evidence from the September independent public-job audit."""
import unittest
import copy
import tempfile
from pathlib import Path
from unittest.mock import patch
import campaign
import ecosystem_discovery

class ExperienceAuditTests(unittest.TestCase):
    def test_observed_experience_wordings(self):
        examples = [
            ("You have at least 7 years of hands\u2011on experience in Pega development.", 7),
            ("12 plus years of Pega experience in building and implementing solutions.", 12),
            ("6+ years (Senior Associate level) of hands-on Pega development experience.", 6),
            ("3-5 years relevant experience in Pega development with 1-2 project implementations.", 3),
            ("A minimum of 5\u20137 years of professional experience.", 5),
        ]
        for text, years in examples:
            with self.subTest(text=text):
                self.assertEqual(campaign.experience_signals(text)[0]["minimum_years"], years)

    def test_title_explicit_years_but_not_seniority_guess(self):
        self.assertEqual(campaign.experience_signals("", "Pega Developer (CSA/CSSA) - 8 Years Experience")[0]["minimum_years"], 8)
        self.assertEqual(campaign.experience_signals("", "Senior Pega Lead Architect"), [])
        self.assertEqual(campaign.experience_signals("JavaScript ES6+ experience and Pega 8.7 knowledge"), [])
        self.assertEqual(campaign.experience_signals("Our company has 25 years of experience in consulting."), [])

    def test_make_job_honors_numeric_title(self):
        job = campaign.make_job("Pega Developer - 8 Years Experience", "Example", "Hyderabad, India", "https://example.com/jobs/8", "Public card", "2026-09-08")
        self.assertEqual((job["experience_min"], job["fit"]), (8, "stretch"))

    def test_required_and_optional_certifications(self):
        self.assertTrue(campaign.mandatory_clsa_evidence("Pega CLSA Certified resource must."))
        self.assertTrue(campaign.mandatory_clsa_evidence("Pega LSA certified with strong hands-on experience in Pega Infinity."))
        for text in ["CSSA or LSA certification preferred.", "CLSA is not mandatory.", "CLSA preferred.", "Work with a CLSA on projects.", "Work with Pega LSA certified architects."]:
            with self.subTest(text=text):
                self.assertEqual(campaign.mandatory_clsa_evidence(text), [])

    def test_explicit_certification_makes_stretch_without_inventing_years(self):
        job = campaign.make_job("Pega Architect", "Example", "India", "https://example.com/jobs/1", "Public card", "2026-09-08")
        class Client:
            def get(self, url):
                return '<h1 class="top-card-layout__title">Pega Architect</h1><div class="description__text">Pega LSA certified with strong hands-on experience in Pega Infinity.</div>', {"url": url, "final_url": url, "http_status": 200, "checked_at": "2026-09-08"}
        result = campaign.enrich_job(job, Client())
        self.assertEqual(result["fit"], "stretch")
        self.assertIsNone(result["experience_min"])
        self.assertEqual(result["required_certifications"], ["CLSA"])

    def test_selected_enrichment_ignores_old_cache_and_preserves_pipeline_identity(self):
        def job(number, identity, source):
            value = campaign.make_job("Pega Developer", "Citi", "India", f"https://www.linkedin.com/jobs/view/{number}", source, "2026-09-08")
            value.update(id=identity, pipeline_id="pipeline-" + identity, status="shortlisted", notes="Keep " + identity)
            return value
        old = job(123, "old-123", "Old catalog")
        old.update(job_detail_status="read", summary="Old cached description", skills=["CLSA"])
        old["salary"] = {"amount_min": 3500000, "amount_max": 3500000, "currency": "INR", "period": "annual", "basis": "total_compensation", "source_url": "https://example.com/older-budget", "evidence_checked_at": "2026-08-01"}
        unrelated = job(789, "old-only-789", "Old catalog")
        fresh = job(123, "fresh-123", "Independent discovery")
        fresh_only = job(456, "fresh-456", "Independent discovery")
        original = {"targets": [
            {"target_id": "old-citi", "name": "Citi", "status": "results", "jobs": [old, unrelated]},
            {"target_id": "fresh-citi", "name": "Citi", "status": "results", "jobs": [fresh, fresh_only]},
        ], "status": "complete"}
        inspected, events = [], []
        def enrich(prior, client):
            inspected.append(prior["id"])
            result = copy.deepcopy(prior)
            result.update(job_detail_status="read", summary="New exact description", skills=["Pega", "Kafka"], experience_min=4)
            return result
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "results.json"
            campaign.save_campaign(original, path)
            with patch.object(campaign, "enrich_job", side_effect=enrich):
                result = campaign.enrich_campaign(path, target_ids=["fresh-citi"], progress=lambda event: events.append(copy.deepcopy(event)))
                resumed = campaign.enrich_campaign(path, target_ids=["fresh-citi"])
                forced = campaign.enrich_campaign(path, target_ids=["fresh-citi"], force=True)
        self.assertCountEqual(inspected, ["fresh-123", "fresh-456", "fresh-123", "fresh-456"])
        self.assertEqual(result["detail_enrichment"]["total"], 2)
        self.assertEqual(result["detail_enrichment"]["cached"], 0)
        self.assertEqual(resumed["detail_enrichment"]["cached"], 2)
        self.assertEqual(forced["detail_enrichment"]["cached"], 0)
        self.assertTrue(all(event["detail_enrichment"]["total"] == 2 for event in events))
        old_copy, unrelated_copy = result["targets"][0]["jobs"]
        fresh_copy = result["targets"][1]["jobs"][0]
        self.assertEqual(unrelated_copy, unrelated)
        for record, identity, source in [(old_copy, "old-123", "Old catalog"), (fresh_copy, "fresh-123", "Independent discovery")]:
            self.assertEqual(record["summary"], "New exact description")
            self.assertEqual(record["skills"], ["Pega", "Kafka"])
            self.assertEqual((record["id"], record["pipeline_id"], record["source"], record["status"], record["notes"]), (identity, "pipeline-" + identity, source, "shortlisted", "Keep " + identity))
        self.assertIsNone(fresh_copy["salary"])
        self.assertEqual(old_copy["salary"]["source_url"], "https://example.com/older-budget")
        self.assertEqual(old_copy["salary"]["latest_presence"], "not_rediscovered")

    def test_empty_enrichment_selection_does_not_request_old_roles(self):
        job = campaign.make_job("Pega Developer", "Citi", "India", "https://www.linkedin.com/jobs/view/123", "Old catalog", "2026-09-08")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "results.json"
            campaign.save_campaign({"targets": [{"target_id": "old", "name": "Citi", "status": "results", "jobs": [job]}]}, path)
            with patch.object(campaign, "enrich_job") as enrich:
                result = campaign.enrich_campaign(path, target_ids=[])
                enrich.assert_not_called()
            self.assertEqual(result["detail_enrichment"]["total"], 0)
            self.assertEqual(result["targets"][0]["jobs"][0], job)
            with self.assertRaisesRegex(ValueError, "unknown target_id"):
                campaign.enrich_campaign(path, target_ids=["missing"])

    def test_discovery_stops_after_a_rate_limited_search(self):
        class Client:
            calls = 0
            def get(self, url):
                self.calls += 1
                return None, {"url": url, "http_status": 429, "checked_at": "2026-09-08", "error": "Rate limited"}
        client = Client()
        with tempfile.TemporaryDirectory() as folder, patch.object(campaign, "PublicClient", return_value=client):
            result = ecosystem_discovery.discover(Path(folder) / "result.json")
        self.assertEqual(client.calls, 1)
        self.assertEqual(result["status"], "partial")

    def test_foreign_country_stays_unknown_remote(self):
        job = {"title": "Pega Developer", "location": "Bucharest, Romania", "remote_eligibility": "unknown", "requirements_unknown": [], "posted_at": "2026-06-01"}
        result = ecosystem_discovery.audit_candidate(job, "2026-09-08")
        self.assertEqual(result["listed_geography"], "outside_india")
        self.assertEqual(result["remote_eligibility"], "unknown")
        self.assertEqual(result["posting_freshness"], "older_than_90_days")
        self.assertNotIn("status", result)

if __name__ == "__main__":
    unittest.main()
