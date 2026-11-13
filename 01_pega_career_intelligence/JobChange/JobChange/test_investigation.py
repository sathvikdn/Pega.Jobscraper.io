"""Regression tests for evidence boundaries, provenance and identity retention."""
import json
import tempfile
import unittest
from pathlib import Path

from investigation_data import build_map, public_source

DATE = "2026-09-08"
PROFILE = "https://in.linkedin.com/in/engineer-one"
JOB = "https://employer.example/careers/123"


def person(**changes):
    value = {
        "name": "Engineer One", "title": "Pega Engineer",
        "employer_as_stated": "Example", "location_as_stated": "Bengaluru, India",
        "profile_url": PROFILE, "source_url": PROFILE, "checked_at": DATE,
        "access": "search_index", "pega_connection": "Describes Pega development",
        "work_summary": "Builds workflow integrations", "limitations": "Self-reported profile",
    }
    value.update(changes)
    return value


def signal(**changes):
    value = {
        "kind": "employer_job", "title": "Pega Developer", "url": JOB,
        "location": "Bengaluru", "checked_at": DATE, "access": "page",
        "status": "page_available", "vacancy_confirmed": True,
    }
    value.update(changes)
    return value


def company(name="Example", **changes):
    value = {"name": name, "category": "unclassified", "aliases": [],
             "claims": [], "people": [], "hiring_signals": [], "limitations": []}
    value.update(changes)
    return value


class InvestigationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, filename="fresh_people.json", companies=None, **changes):
        value = {"research_date": DATE, "companies": companies or [], "queries": []}
        value.update(changes)
        (self.root / filename).write_text(json.dumps(value), encoding="utf-8")

    def build(self):
        return build_map(self.root)

    def test_legacy_catalogue_is_never_an_evidence_input(self):
        self.write("directory.json", [company(people=[person()])])
        self.assertEqual(self.build()["stats"]["companies"], 0)
        self.assertEqual(self.build()["inputs"], [])

    def test_source_url_signal_schema_is_retained_and_normalized(self):
        self.write(companies=[company(hiring_signals=[
            signal(url=None, source_url=JOB, kind=None, type="employer_requisition",
                   access=None, status="search_index_only", vacancy_confirmed=False)
        ])])
        actual = self.build()["companies"][0]["hiring_signals"][0]
        self.assertEqual(actual["url"], JOB)
        self.assertEqual(actual["source_url"], JOB)
        self.assertEqual(actual["kind"], "employer_job")
        self.assertEqual(actual["access"], "search_index")
        self.assertFalse(actual["vacancy_confirmed"])

    def test_requisition_text_preserves_exact_title_location_and_limitations(self):
        self.write(companies=[company(hiring_signals=[{
            "type": "employer_requisition", "source_url": JOB,
            "text": "Requisition 24759: Software Engineer I - Pega Developer; Bengaluru hybrid; three years experience.",
            "checked_at": DATE, "status": "search_index_only",
            "not_evidence_of": "Equipment-finance team membership or current vacancy."
        }])])
        actual = self.build()["companies"][0]["hiring_signals"][0]
        self.assertEqual(actual["title"], "Software Engineer I - Pega Developer")
        self.assertEqual(actual["location"], "Bengaluru hybrid")
        self.assertEqual(actual["requisition_id"], "24759")
        self.assertEqual(actual["title_basis"], "parsed_requisition_text")
        self.assertEqual(actual["access"], "search_index")
        self.assertIn("Equipment-finance team membership or current vacancy.", actual["limitations"])
        self.assertFalse(actual["vacancy_confirmed"])

    def test_only_confirmed_page_observed_employer_vacancy_sets_hiring(self):
        self.write(companies=[company(hiring_signals=[signal()])])
        result = self.build()
        self.assertTrue(result["companies"][0]["flags"]["hiring"])
        self.assertEqual(result["stats"]["confirmed_vacancies"], 1)
        self.assertEqual(result["companies"][0]["hiring_signals"][0]["status"], "confirmed_open")

    def test_closed_historical_and_move_records_never_set_active_hiring(self):
        for status in ("closed", "expired", "historical_needs_recheck", "employee_move"):
            with self.subTest(status=status):
                self.write(companies=[company(hiring_signals=[signal(status=status)])])
                result = self.build()["companies"][0]
                self.assertFalse(result["flags"]["hiring"])
                self.assertFalse(result["flags"]["hiring_lead"])
                self.assertFalse(result["hiring_signals"][0]["vacancy_confirmed"])

    def test_employee_move_type_overrides_wrong_employer_job_kind(self):
        self.write(companies=[company(hiring_signals=[signal(type="employee_move")])])
        actual = self.build()["companies"][0]["hiring_signals"][0]
        self.assertEqual(actual["kind"], "employee_move")
        self.assertFalse(actual["vacancy_confirmed"])

    def test_historical_description_cannot_be_active_recruiting_lead(self):
        self.write(companies=[company(hiring_signals=[
            signal(kind="recruiter_post", status="unverified",
                   description="Historical posting for a Pega engineer")
        ])])
        actual = self.build()["companies"][0]
        self.assertFalse(actual["flags"]["hiring_lead"])
        self.assertEqual(actual["hiring_signals"][0]["status"], "historical")

    def test_index_access_and_string_confirmation_do_not_confirm_vacancy(self):
        for changes in ({"access": "search-index"}, {"vacancy_confirmed": "true"},
                        {"vacancy_confirmed": False}, {"checked_at": None},
                        {"kind": "recruiter_post"}, {"kind": "public_job_card"}):
            with self.subTest(changes=changes):
                self.write(companies=[company(hiring_signals=[signal(**changes)])])
                actual = self.build()["companies"][0]
                self.assertFalse(actual["flags"]["hiring"])
                self.assertTrue(actual["flags"]["hiring_lead"])

    def test_page_available_alone_does_not_promote_search_card_to_job_description(self):
        self.write(companies=[company(hiring_signals=[signal(
            kind="public_job_card", vacancy_confirmed=False, status=None)])])
        actual = self.build()["companies"][0]["hiring_signals"][0]
        self.assertEqual(actual["evidence_scope"], "job_search_card")
        self.assertEqual(actual["access"], "page")
        self.assertEqual(actual["status"], "candidate")

    def test_same_linkedin_job_closure_overrides_card_and_preserves_observations(self):
        self.write(companies=[company(hiring_signals=[signal(
            url="https://in.linkedin.com/jobs/view/pega-developer-at-example-1234567",
            checked_at="2026-09-08T08:00:00+00:00")])])
        self.write("fresh_public_jobs.json", [company(hiring_signals=[signal(
            url="https://www.linkedin.com/jobs/view/1234567?trk=card", status="closed",
            checked_at=DATE, vacancy_confirmed=False, kind="public_job_card")])])
        actual = self.build()["companies"][0]
        self.assertEqual(len(actual["hiring_signals"]), 1)
        self.assertEqual(actual["hiring_signals"][0]["status"], "closed")
        self.assertEqual(len(actual["hiring_signals"][0]["observations"]), 2)
        self.assertFalse(actual["flags"]["hiring"])

    def test_generic_careers_page_retains_separate_roles(self):
        self.write(companies=[company(hiring_signals=[
            signal(url="https://example.com/careers", title="Pega SSA"),
            signal(url="https://example.com/careers", title="Pega LSA")
        ])])
        self.assertEqual(len(self.build()["companies"][0]["hiring_signals"]), 2)

    def test_person_observations_and_string_limitations_survive_merging(self):
        self.write(companies=[company(people=[person()])])
        self.write("fresh_consulting.json", [company(people=[person(
            profile_url="https://www.linkedin.com/in/engineer-one/",
            source_url="https://www.linkedin.com/posts/engineer-one-project",
            work_summary="Explores Pega decisioning", limitations="Historical project")])])
        result = self.build()
        self.assertEqual(result["stats"]["people_records"], 1)
        self.assertEqual(result["stats"]["people_observations"], 2)
        actual = result["companies"][0]["people"][0]
        self.assertEqual(len(actual["observations"]), 2)
        self.assertEqual(actual["limitations"], ["Self-reported profile", "Historical project"])
        self.assertEqual(len(actual["work_summaries"]), 2)

    def test_top_level_person_retains_all_company_memberships(self):
        self.write(companies=[
            company("Employer A", people=[person(employer_as_stated="Employer A")]),
            company("Employer B", people=[person(employer_as_stated="Employer B")])
        ])
        actual = self.build()["people"][0]
        self.assertEqual(len(actual["company_ids"]), 2)
        self.assertEqual(set(actual["companies"]), {"Employer A", "Employer B"})
        self.assertEqual(len(actual["observations"]), 2)

    def test_event_page_does_not_upgrade_linkedin_location_source(self):
        event = "https://www.pega.com/events/agenda/session"
        self.write(companies=[company(people=[person(
            source_url=event, access="page", profile_source_url=PROFILE,
            profile_access="search_index", location_as_stated="Pune")])])
        actual = self.build()["people"][0]
        self.assertEqual(actual["access"], "page")
        self.assertEqual(actual["profile_access"], "search_index")
        self.assertEqual(actual["field_sources"]["title"][0]["source_url"], event)
        self.assertEqual(actual["field_sources"]["location_as_stated"][0]["source_url"], PROFILE)
        self.assertEqual(actual["field_sources"]["location_as_stated"][0]["access"], "search_index")

    def test_event_historical_negative_city_mentions_are_not_local_footprint(self):
        for location in ("United Kingdom profile; Bangalore not established",
                         "Current employer experience: Asia; older entries Bengaluru",
                         "Bengaluru event participation; current work city not stated",
                         "Not in Bengaluru"):
            with self.subTest(location=location):
                self.write(companies=[company(people=[person(location_as_stated=location)])])
                self.assertFalse(self.build()["companies"][0]["flags"]["bangalore"])

    def test_local_person_or_vacancy_is_connection_not_verified_team(self):
        for changes in ({"people": [person()]}, {"hiring_signals": [signal()]}):
            with self.subTest(changes=changes):
                self.write(companies=[company(**changes)])
                actual = self.build()["companies"][0]
                self.assertTrue(actual["flags"]["bangalore"])
                self.assertFalse(actual["flags"]["bangalore_team_verified"])
                self.assertEqual(actual["bangalore_scope"], "documented_connection_only")
                self.assertIsNone(actual["current_team_size"])

    def test_historical_local_claim_is_not_current_team_evidence(self):
        self.write(companies=[company(claims=[{
            "type": "bangalore_team", "source_url": JOB, "confidence": "direct",
            "access": "search_index", "source_kind": "professional_post",
            "text": "A historical Bengaluru hiring post; no active requisition."
        }])])
        self.assertFalse(self.build()["companies"][0]["flags"]["bangalore"])

    def test_team_verified_requires_explicit_scope_and_page_employer_evidence(self):
        claim = {"type": "bangalore_team", "text": "The Bengaluru Pega team builds workflows",
                 "source_url": JOB, "confidence": "direct", "access": "page",
                 "source_kind": "employer", "team_location_verified": True,
                 "evidence_scope": "current_employer_team"}
        self.write(companies=[company(claims=[claim])])
        self.assertTrue(self.build()["companies"][0]["flags"]["bangalore_team_verified"])
        claim["access"] = "search_index"
        self.write(companies=[company(claims=[claim])])
        self.assertFalse(self.build()["companies"][0]["flags"]["bangalore_team_verified"])

    def test_exact_aliases_and_transitive_bridge_merge_under_canonical_name(self):
        self.write(companies=[
            company("Areteans", aliases=["Areteans Technology"], people=[person()]),
            company("Credera", hiring_signals=[signal()]),
        ])
        self.write("fresh_consulting.json", [company(
            "Credera", aliases=["Areteans", "Areteans Technology Solutions"],
            people=[person(name="Second Engineer", profile_url="https://linkedin.com/in/two")])])
        result = self.build()
        self.assertEqual(result["stats"]["companies"], 1)
        self.assertEqual(result["companies"][0]["name"], "Credera")
        self.assertIn("Areteans", result["companies"][0]["aliases"])
        self.assertEqual(result["stats"]["people_records"], 2)

    def test_substrings_do_not_merge_citi_with_first_citizens(self):
        self.write(companies=[company("Citi", people=[person()]),
                              company("First Citizens", hiring_signals=[signal()])])
        self.assertEqual(self.build()["stats"]["companies"], 2)

    def test_category_missing_null_or_conflicting_is_explicit(self):
        self.write(companies=[company(category=None, people=[person()])])
        self.assertEqual(self.build()["companies"][0]["category"], "unclassified")
        self.write(companies=[company(category="gcc", people=[person()])])
        self.write("fresh_consulting.json", [company(category="services", hiring_signals=[signal()])])
        self.assertEqual(self.build()["companies"][0]["category"], "unclassified")

    def test_invalid_sources_and_malformed_rows_do_not_crash_or_gain_evidence(self):
        self.write(companies=[company(
            claims=[None, "bad", {"source_url": "javascript:alert(1)", "text": "claim"},
                    {"url": JOB, "text": "Source-linked claim without type"}],
            people=[None, {"name": "Not sourced"}, person()],
            hiring_signals=[None, signal(url=JOB, kind=None)],
            aliases=None, limitations="Company limitation")], queries=["plain query", None])
        result = self.build()
        self.assertEqual(len(result["companies"][0]["claims"]), 1)
        self.assertEqual(result["companies"][0]["claims"][0]["type"], "other")
        self.assertEqual(result["companies"][0]["limitations"], ["Company limitation"])
        self.assertEqual(len(result["queries"]), 1)
        self.assertTrue(result["diagnostics"])

    def test_india_remote_lead_requires_explicit_noncontradictory_role_location(self):
        cases = [
            ("Pan India - Remote", {}, True),
            ("India - Remote", {"status": "historical"}, False),
            ("Remote - United States", {}, False),
            ("India", {"remote_filter_requested": True}, False),
            ("Remote - India, US only", {}, False),
            ("Remote - outside India", {}, False),
            ("India - Hybrid", {}, False),
            ("India - Remote", {"remote_eligibility": "country_restricted"}, False),
        ]
        for location, changes, expected in cases:
            with self.subTest(location=location, changes=changes):
                self.write(companies=[company(hiring_signals=[
                    signal(location=location, **changes)])])
                self.assertEqual(self.build()["companies"][0]["flags"]["india_remote_lead"], expected)

    def test_public_source_rejects_local_and_non_https_urls(self):
        for value in (None, 42, "javascript:alert(1)", "http://example.com",
                      "https://localhost/x", "https://127.0.0.1/x",
                      "https://[::1]/x", "https://name:password@example.com/x"):
            with self.subTest(value=value):
                self.assertFalse(public_source(value))
        self.assertTrue(public_source(JOB))


if __name__ == "__main__":
    unittest.main()
