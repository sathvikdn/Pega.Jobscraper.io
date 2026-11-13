"""Offline regressions for full-directory discovery, conservative pay and eligibility."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import campaign

TARGET = {"target_id": "gcc-citi", "name": "Citi", "category": "gcc", "keywords": ["citi"], "location": "India"}


def card(number=123, company="Citi", title="Pega Developer"):
    return f'<li><div class="base-card"><h3 class="base-search-card__title">{title}</h3><h4 class="base-search-card__subtitle">{company}</h4><a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/{number}?trk=search">View</a><span class="job-search-card__location">Pune, India</span></div></li>'


class FakeClient:
    def __init__(self, pages):
        self.pages, self.urls = iter(pages), []

    def get(self, url):
        self.urls.append(url)
        html, status = next(self.pages)
        return html, {"url": url, "checked_at": "2026-09-07", "http_status": status}


class CampaignTests(unittest.TestCase):
    def test_html_valueless_attributes_are_safe(self):
        html = '<div class disabled><span>Welcome</span></div>' + card()
        jobs, count = campaign.parse_cards(html, TARGET)
        self.assertEqual((len(jobs), count), (1, 1))

    def test_card_dedup_and_exact_employer_before_jd(self):
        jobs, count = campaign.parse_cards(card() + card() + card(456, "Other Ltd"), TARGET)
        self.assertEqual((len(jobs), count), (1, 2))
        self.assertEqual(jobs[0]["url"], "https://www.linkedin.com/jobs/view/123")

    def test_adjacent_role_and_generic_jd_requirements(self):
        self.assertEqual(campaign.classify_track("Workflow Automation Engineer"), "adjacent")
        self.assertEqual(campaign.classify_track("Software Engineer", "Build Kafka and REST APIs"), "adjacent")
        self.assertEqual(campaign.classify_track("Clinical Configuration Analyst", "Configure healthcare workflows on Pega Cloud with case lifecycle rules."), "pega")
        self.assertEqual(campaign.classify_track("Data Migration Business Analyst", "Own data migration for Pega Platform integrations and Connect-SQL mapping."), "pega")
        self.assertEqual(campaign.classify_track("Senior Cloud Solutions Associate", "Healthcare GCC delivery with Pega Platform integration, Service REST, and Connect REST."), "pega")
        self.assertEqual(campaign.classify_track("Decision Hub Senior Developer", "Build Customer Decision Hub strategies and NBA decisioning."), "adjacent")
        self.assertIsNone(campaign.classify_track("Clinical Configuration Analyst", "Configure healthcare forms in Excel."))
        self.assertIsNone(campaign.classify_track("Software Engineer"))
        self.assertIsNone(campaign.classify_track("Electrical Automation Engineer", "PLC integration"))

    def test_jd_scoping_ignores_recommendations(self):
        text, _ = campaign.role_description('<div class="description__text">Java development</div><aside>Pega roles</aside>')
        self.assertNotIn("Pega", text)
        self.assertEqual(campaign.role_description('<article>Pega careers and recommended jobs</article>'), ("", None))

    def test_only_explicit_ctc_qualifies_for_threshold(self):
        self.assertEqual(campaign.pay_bucket(campaign.salary_evidence("CTC: INR 20-25 LPA")), "at_least_20")
        self.assertEqual(campaign.pay_bucket(campaign.salary_evidence("CTC: 18 to 22 LPA")), "overlaps_20")
        self.assertEqual(campaign.pay_bucket(campaign.salary_evidence("CTC: Rs 15 LPA")), "below_20")
        self.assertEqual(campaign.pay_bucket(campaign.salary_evidence("Salary: INR 25 LPA")), "unknown")
        self.assertEqual(campaign.pay_bucket(campaign.salary_evidence("Fixed pay INR 20 LPA. Final CTC will be negotiated.")), "unknown")
        self.assertIsNone(campaign.salary_evidence("Salary USD 20-25 LPA"))

    def test_remote_team_is_not_candidate_eligibility(self):
        self.assertEqual(campaign.remote_eligibility("India; Remote"), "india_remote")
        self.assertEqual(campaign.remote_eligibility("United States; Remote"), "country_restricted")
        self.assertEqual(campaign.remote_eligibility("London", "Collaborate with remote teams worldwide and colleagues in India."), "unknown")
        self.assertEqual(campaign.remote_eligibility("Worldwide Remote"), "worldwide")
        self.assertEqual(campaign.remote_eligibility("India Remote", "Must reside in the United States."), "country_restricted")
        self.assertEqual(campaign.remote_eligibility("Worldwide Remote", "Applicants must be based in Canada."), "country_restricted")
        self.assertEqual(campaign.remote_eligibility("United States; Remote", "Enjoy a work from anywhere benefit."), "country_restricted")
        self.assertEqual(campaign.remote_eligibility("London", "Work from anywhere with remote teams."), "unknown")

    def test_boolean_fallback_runs_after_simple_query_has_zero_employer_matches(self):
        client = FakeClient([(card(company="Other Ltd"), 200), (card(), 200)])
        result = campaign.check_target(TARGET, client)
        self.assertEqual(result["status"], "results")
        self.assertEqual(len(result["jobs"]), 1)
        self.assertIn("keywords=pega+citi", client.urls[0])
        self.assertIn("PRPC", client.urls[1])

    def test_blocked_does_not_claim_no_matches(self):
        result = campaign.check_target(TARGET, FakeClient([(None, 429)]))
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["jobs"], [])

    def test_generic_role_checks_only_matching_employer(self):
        pages = [(card(123, "Other Ltd", "Software Engineer") + card(456, "Citi", "Software Engineer"), 200), ('<div class="description__text">Pega PRPC and Kafka development</div>', 200)]
        client = FakeClient(pages)
        result = campaign.check_target(TARGET, client)
        self.assertEqual(result["jobs"][0]["track"], "pega")
        self.assertIn("jobPosting/456", client.urls[1])

    def test_resume_and_subset_force_preserve_full_coverage(self):
        targets = [TARGET, {**TARGET, "target_id": "gcc-other", "name": "Other", "keywords": ["other"]}]
        def checked(target, client):
            return {**target, "status": "no_matches", "checked_at": "2026-09-07", "diagnostics": [{"http_status": 200}], "jobs": []}
        with tempfile.TemporaryDirectory() as folder, patch.object(campaign, "check_target", side_effect=checked) as check:
            path = Path(folder) / "results.json"
            first = campaign.run_campaign(data=targets, output_path=path)
            self.assertEqual(first["coverage"]["checked"], 2)
            self.assertEqual(check.call_count, 2)
            campaign.run_campaign(data=targets, output_path=path)
            self.assertEqual(check.call_count, 2)
            refreshed = campaign.run_campaign(target_ids=[TARGET["target_id"]], force=True, data=targets, output_path=path)
            self.assertEqual(check.call_count, 3)
            self.assertEqual(refreshed["coverage"]["total"], 2)
            self.assertEqual(refreshed["coverage"]["checked"], 2)
            self.assertEqual(len(json.loads(path.read_text())["targets"]), 2)

    def test_cancel_before_requests_leaves_targets_pending(self):
        stop = threading.Event()
        stop.set()
        with tempfile.TemporaryDirectory() as folder, patch.object(campaign, "check_target") as check:
            result = campaign.run_campaign(data=[TARGET], output_path=Path(folder) / "results.json", stop_event=stop)
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(result["coverage"]["pending"], 1)
        check.assert_not_called()

    def test_prior_jobs_survive_failed_refresh_with_old_evidence_date(self):
        old = campaign.make_job("Pega Developer", "Citi", "India", "https://example.com/job/1", "Employer", "2026-09-01")
        saved = {**TARGET, "status": "results", "checked_at": "2026-09-01", "jobs": [old], "diagnostics": []}
        failed = {**TARGET, "status": "blocked", "checked_at": "2026-09-07", "jobs": [], "diagnostics": [{"http_status": 429}]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "results.json"
            campaign.save_campaign({"targets": [saved], "status": "complete"}, path)
            with patch.object(campaign, "check_target", return_value=failed):
                result = campaign.run_campaign(force=True, data=[TARGET], output_path=path)
        job = result["targets"][0]["jobs"][0]
        self.assertEqual(job["status"], "uncertain")
        self.assertEqual(job["search_presence"], "not_rediscovered")
        self.assertEqual(job["last_seen_at"], "2026-09-01")
        self.assertEqual(job["checked_at"], "2026-09-01")
        self.assertEqual(result["targets"][0]["retained_job_count"], 1)
        self.assertEqual(result["targets"][0]["diagnostics"][0]["http_status"], 429)

    def test_rediscovered_canonical_url_replaces_old_record(self):
        old = campaign.make_job("Pega Developer", "Citi", "India", "https://example.com/job/1?utm_source=a", "Employer", "2026-09-01")
        fresh = campaign.make_job("Pega Engineer", "Citi", "India", "https://example.com/job/1?utm_source=b", "Employer", "2026-09-07")
        record = campaign.retain_previous_jobs({"status": "results", "jobs": [fresh]}, {"jobs": [old]})
        self.assertEqual(len(record["jobs"]), 1)
        self.assertEqual(record["jobs"][0]["title"], "Pega Engineer")
        self.assertEqual(record["retained_job_count"], 0)

    def test_directory_id_matches_normalization_contract(self):
        self.assertEqual(campaign.target_id("global", "JPMorgan Chase (US)"), "global-jpmorgan-chase-us")


    def test_actual_lock_probe_ignores_stale_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "results.json"
            path.write_text('{"status":"running"}', encoding="utf-8")
            self.assertFalse(campaign.campaign_is_locked(path))
            with campaign.campaign_lock(path):
                self.assertTrue(campaign.campaign_is_locked(path))
            self.assertFalse(campaign.campaign_is_locked(path))

    def test_description_enrichment_keeps_candidate_and_explicit_pay(self):
        job = campaign.make_job("Pega Developer", "Citi", "India Remote", "https://www.linkedin.com/jobs/view/123", "LinkedIn public jobs", "2026-09-01")
        html = '<h2 class="top-card-layout__title">Pega Developer</h2><div class="description__text">Minimum 5 years of Pega experience. CTC INR 35-40 LPA. Kafka and REST APIs. Role remote India.</div>'
        enriched = campaign.enrich_job(job, FakeClient([(html, 200)]))
        self.assertEqual(enriched["job_detail_status"], "read")
        self.assertEqual(enriched["experience_min"], 5)
        self.assertEqual(enriched["salary"]["amount_min"], 3500000)
        self.assertEqual(enriched["fit"], "stretch")
        self.assertEqual(enriched["remote_eligibility"], "india_remote")
        self.assertEqual(enriched["verification_status"], "candidate")
        self.assertIn("Kafka", enriched["skills"])
        self.assertNotIn("Full role requirements not fetched", enriched["requirements_unknown"])

    def test_description_title_mismatch_retains_original_evidence(self):
        job = campaign.make_job("Pega Developer", "Citi", "India", "https://www.linkedin.com/jobs/view/123", "LinkedIn public jobs", "2026-09-01")
        html = '<h2 class="top-card-layout__title">Principal Engineer</h2><div class="description__text">Pega, CTC INR 50 LPA</div>'
        enriched = campaign.enrich_job(job, FakeClient([(html, 200)]))
        self.assertEqual(enriched["job_detail_status"], "identity_unconfirmed")
        self.assertIsNone(enriched["salary"])
        self.assertEqual(enriched["title"], job["title"])

    def test_description_failure_never_removes_or_closes_candidate(self):
        job = campaign.make_job("Pega Developer", "Citi", "India", "https://www.linkedin.com/jobs/view/123", "LinkedIn public jobs", "2026-09-01")
        enriched = campaign.enrich_job(job, FakeClient([(None, 429)]))
        self.assertEqual(enriched["job_detail_status"], "unavailable")
        self.assertEqual(enriched["id"], job["id"])
        self.assertNotEqual(enriched["status"], "closed")

    def test_enrichment_preserves_senior_roles_as_stretch_for_review(self):
        job = campaign.make_job("Pega Developer", "Citi", "India", "https://www.linkedin.com/jobs/view/123", "LinkedIn public jobs", "2026-09-01")
        html = '<div class="description__text">Minimum 10 years of software development experience; 3 years of Pega experience. CLSA required.</div>'
        enriched = campaign.enrich_job(job, FakeClient([(html, 200)]))
        self.assertEqual(enriched["experience_min"], 10)
        self.assertEqual(enriched["fit"], "stretch")
        self.assertIn("CLSA", enriched["skills"])
        self.assertEqual(enriched["id"], job["id"])

    def test_enrichment_resume_and_duplicate_urls_preserve_records(self):
        job = campaign.make_job("Pega Developer", "Citi", "India", "https://www.linkedin.com/jobs/view/123", "LinkedIn public jobs", "2026-09-01")
        other = {**TARGET, "target_id": "global-citi", "category": "global"}
        targets = [{**TARGET, "status": "results", "jobs": [job]}, {**other, "status": "results", "jobs": [job.copy()]}]
        html = '<div class="description__text">Pega experience and REST APIs</div>'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "results.json"
            campaign.save_campaign({"targets": targets, "status": "complete"}, path)
            with patch.object(campaign.PublicClient, "get", return_value=(html, {"http_status": 200, "checked_at": "2026-09-07"})) as get:
                first = campaign.enrich_campaign(path)
                second = campaign.enrich_campaign(path)
            self.assertEqual(get.call_count, 1)
            self.assertEqual(first["detail_enrichment"]["total"], 1)
            self.assertEqual(second["detail_enrichment"]["checked"], 1)
            self.assertEqual(first["detail_enrichment"]["cached"], 0)
            self.assertEqual(second["detail_enrichment"]["cached"], 1)
            self.assertEqual(second["targets"][0]["jobs"][0]["id"], job["id"])
            self.assertEqual(second["targets"][1]["jobs"][0]["id"], job["id"])
            self.assertEqual(second["coverage"]["jobs"], 2)

    def test_hardware_application_role_is_preserved_but_unrelated(self):
        job = campaign.make_job("Application Engineer", "Example", "India", "https://www.linkedin.com/jobs/view/123", "LinkedIn public jobs", "2026-09-01")
        html = '<div class="description__text">Work on semiconductor FPGA verification and RTL design.</div>'
        enriched = campaign.enrich_job(job, FakeClient([(html, 200)]))
        self.assertEqual(enriched["relevance"], "unrelated")
        self.assertEqual(enriched["id"], job["id"])
        self.assertEqual(enriched["fit"], "stretch")
        self.assertIsNone(campaign.classify_track("Application Engineer", "Customer support for industrial equipment."))
        self.assertEqual(campaign.classify_track("Application Engineer", "Develop enterprise integration with Kafka and REST APIs."), "adjacent")

    def test_enrichment_retains_prior_salary_with_stale_evidence_note(self):
        job = campaign.make_job("Pega Developer", "Citi", "India", "https://www.linkedin.com/jobs/view/123", "LinkedIn public jobs", "2026-09-01", description="Pega, CTC INR 35 LPA")
        html = '<div class="description__text">Develop Pega workflows with Kafka and REST APIs.</div>'
        enriched = campaign.enrich_job(job, FakeClient([(html, 200)]))
        self.assertEqual(enriched["salary"]["amount_min"], 3500000)
        self.assertEqual(enriched["salary"]["latest_presence"], "not_rediscovered")
        self.assertEqual(enriched["salary"]["evidence_checked_at"], "2026-09-01")
        self.assertTrue(any("Previous salary evidence retained" in gap for gap in enriched["requirements_unknown"]))

    def test_second_campaign_lock_is_rejected_and_released(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "results.json"
            with campaign.campaign_lock(path):
                with self.assertRaises((RuntimeError, BlockingIOError)):
                    with campaign.campaign_lock(path):
                        self.fail("A second writer acquired the campaign lock")
            with campaign.campaign_lock(path):
                pass


if __name__ == "__main__":
    unittest.main()
