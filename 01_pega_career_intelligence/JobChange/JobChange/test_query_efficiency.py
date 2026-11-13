"""Offline guarantees for relevance-aware public search query limits."""
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

import campaign
from test_pagination_recovery import TARGET, EMPTY, FixtureClient, card, page


def generic_jd(text="Build Java services and REST APIs", title="Software Engineer"):
    return ('<h1 class="top-card-layout__title">' + title + '</h1>'
            '<a class="topcard__org-name-link">Example Bank</a>'
            '<div class="description__text">' + text + '</div>')


class QueryEfficiencyTests(unittest.TestCase):
    def setUp(self):
        network = patch.object(campaign.urllib.request, "urlopen", side_effect=AssertionError("Offline fixtures only"))
        network.start()
        self.addCleanup(network.stop)

    def test_default_query_is_simple_pega_with_unchanged_location(self):
        target = {**TARGET, "location": "Bengaluru, Karnataka, India"}
        fields = parse_qs(urlsplit(campaign.query_url(target)).query)
        self.assertEqual(fields["keywords"], ["pega Example Bank"])
        self.assertEqual(fields["location"], [target["location"]])
        self.assertIn("PRPC", parse_qs(urlsplit(campaign.query_url(target, expanded=True)).query)["keywords"][0])

    def test_two_irrelevant_full_pages_replace_ten_with_explicit_partial_coverage(self):
        unrelated = "".join(card(n, "Other Employer", "Java Developer") for n in range(10))
        client = FixtureClient([(unrelated, 200), (unrelated, 200)])
        result = campaign.check_target(TARGET, client)
        self.assertEqual(len(client.urls), 2)
        self.assertEqual(result["status"], "no_matches")
        self.assertEqual(result["jobs"], [])
        self.assertTrue(result["partial"])
        self.assertIn("does not establish", result["coverage_note"])
        stops = [x for x in result["diagnostics"] if x.get("relevance_early_stop")]
        self.assertEqual(len(stops), 2)
        self.assertTrue(all(x["pagination_incomplete"] for x in stops))
        self.assertTrue(all("later pages were not checked" in x["pagination_stop"] for x in stops))

    def test_generic_employer_card_does_not_suppress_alternate_query(self):
        client = FixtureClient([(card(1, title="Software Engineer"), 200),
                                (generic_jd(), 200), (card(2), 200)])
        result = campaign.check_target(TARGET, client)
        self.assertEqual([x["url"] for x in result["jobs"]], ["https://www.linkedin.com/jobs/view/2"])
        self.assertEqual(len(client.urls), 3)
        self.assertIn("jobPosting/1", client.urls[1])
        self.assertIn("PRPC", parse_qs(urlsplit(client.urls[2]).query)["keywords"][0])

    def test_generic_pega_description_unlocks_deeper_pages(self):
        listing = card(1, title="Software Engineer") + "".join(card(n, "Other Employer") for n in range(2, 11))
        client = FixtureClient([(listing, 200), (generic_jd("Pega PRPC application development; 4 years experience"), 200),
                                (page(20), 200), (EMPTY, 200)])
        result = campaign.check_target(TARGET, client)
        self.assertEqual(len(result["jobs"]), 11)
        self.assertEqual([parse_qs(urlsplit(u).query)["start"][0] for u in client.urls if "seeMoreJob" in u], ["0", "10", "20"])
        self.assertFalse(result["partial"])
        self.assertTrue(next(x for x in result["jobs"] if x["url"].endswith("/1"))["description_complete"])

    def test_productive_pega_query_retains_full_five_page_depth(self):
        client = FixtureClient([(page(n), 200) for n in range(100, 150, 10)])
        result = campaign.check_target(TARGET, client)
        self.assertEqual(len(result["jobs"]), 50)
        self.assertEqual(len(client.urls), 5)
        self.assertTrue(result["diagnostics"][-1]["pagination_capped"])
        self.assertFalse(any(x.get("relevance_early_stop") for x in result["diagnostics"]))

    def test_generic_description_budget_is_shared_across_queries_and_deduplicated(self):
        listing = "".join(card(n, title="Software Engineer") for n in range(10))
        client = FixtureClient([(listing, 200)] + [(generic_jd(), 200)] * 5 + [(listing, 200)])
        result = campaign.check_target(TARGET, client)
        urls = [u for u in client.urls if "jobPosting" in u]
        self.assertEqual(len(urls), 5)
        self.assertEqual(len(set(urls)), 5)
        self.assertEqual(len(client.urls), 7)
        self.assertEqual(result["jobs"], [])
        self.assertTrue(result["partial"])
        self.assertEqual(sum(x.get("generic_jds_not_checked", 0) for x in result["diagnostics"]), 5)

    def test_other_employer_generic_descriptions_are_never_fetched(self):
        listing = "".join(card(n, "Other Employer", "Software Engineer") for n in range(10))
        client = FixtureClient([(listing, 200), (EMPTY, 200)])
        result = campaign.check_target(TARGET, client)
        self.assertEqual(len(client.urls), 2)
        self.assertFalse(any("jobPosting" in u for u in client.urls))
        self.assertEqual(result["jobs"], [])

    def test_blocked_first_query_is_not_retried_with_another_format(self):
        client = FixtureClient([(None, 429)])
        result = campaign.check_target(TARGET, client)
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(result["partial"])
        self.assertEqual(len(client.urls), 1)

    def test_paused_generic_probe_does_not_start_fallback(self):
        listing = card(1, title="Software Engineer") + "".join(card(n, "Other Employer") for n in range(2, 11))
        client = FixtureClient([(listing, 200), campaign.Cancelled()])
        result = campaign.check_target(TARGET, client)
        self.assertEqual(result["status"], "pending")
        self.assertTrue(result["partial"])
        self.assertEqual(len(client.urls), 2)

    def test_two_explicit_empty_responses_do_not_claim_exhaustive_inventory(self):
        client = FixtureClient([(EMPTY, 200), (EMPTY, 200)])
        result = campaign.check_target(TARGET, client)
        self.assertEqual(result["status"], "no_matches")
        self.assertFalse(result["partial"])
        self.assertNotEqual(result["status"], "no_openings")
        self.assertEqual(len(client.urls), 2)

    def test_returned_employer_identity_still_controls_generic_pega_acceptance(self):
        foreign_body = generic_jd("Pega PRPC development").replace("Example Bank", "Other Employer")
        client = FixtureClient([(card(1, title="Software Engineer"), 200), (foreign_body, 200), (EMPTY, 200)])
        result = campaign.check_target(TARGET, client)
        self.assertEqual(result["jobs"], [])
        self.assertTrue(result["partial"])
        self.assertTrue(any("employer differs" in x.get("error", "").lower() for x in result["diagnostics"]))


if __name__ == "__main__":
    unittest.main()
