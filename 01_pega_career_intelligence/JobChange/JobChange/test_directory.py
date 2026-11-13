"""Offline checks that the directory preserves breadth without mixing employers."""
import json
import tempfile
import unittest
from pathlib import Path

import directory_data as directory


class DirectoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = directory.build_directory()
        cls.records = cls.result['records']

    def record(self, name):
        return next(record for record in self.records if record['name'] == name)

    def test_all_scanner_targets_survive_with_stable_ids(self):
        catalog = directory.load_catalog()
        actual = {record['target_id']: record for record in self.records}
        self.assertEqual(len(catalog), 301)
        self.assertEqual(self.result['stats']['scanner_categories'], {'gcc': 108, 'services': 58, 'global': 135})
        for original in catalog:
            with self.subTest(name=original['name']):
                saved = actual[original['target_id']]
                self.assertEqual(saved['original_target'], original['original_target'])
                self.assertEqual(saved['keywords'], original['keywords'])
                self.assertEqual(saved['location'], original['location'])
        self.assertEqual(len(actual), len(self.records))
        self.assertEqual(directory.target_id('global', 'JPMorgan Chase (US)'), 'global-jpmorgan-chase-us')

    def test_historical_and_recent_only_companies_are_visible(self):
        self.assertEqual(self.result['stats']['total_targets'], 313)
        self.assertEqual(self.result['stats']['historical_only_targets'], 11)
        self.assertEqual(self.result['stats']['recent_research_only_targets'], 1)
        self.assertEqual(self.record('Intel India')['target_source'], 'historical_only')
        self.assertEqual(self.record('CSC (Corporation Service Company)')['target_source'], 'recent_research_only')
        self.assertEqual(self.result['stats']['unmatched_snapshot_names'], [])

    def test_all_historical_people_and_unmodified_source_records_are_preserved(self):
        snapshots = self.result['historical_snapshots']
        self.assertEqual(len(snapshots), 89)
        self.assertEqual(sum(len(s['team_members']) for s in snapshots), 403)
        originals = {
            'enriched': json.loads((directory.BASE / 'team_intelligence_enriched.json').read_text(encoding='utf-8-sig'))['companies'],
            'dossiers': directory.extract_dossiers(directory.BASE / 'Pega_Deep_Dossiers.html'),
        }
        by_name = {snapshot['name']: snapshot for snapshot in snapshots}
        for source_id, companies in originals.items():
            for original in companies:
                with self.subTest(source=source_id, company=original['name']):
                    snapshot = by_name[original['name']]
                    variant = next(v['record'] for v in snapshot['_source_records'] if v['source_id'] == source_id)
                    self.assertEqual(variant, original)
                    merged_names = {directory.normalized(p['name']) for p in snapshot['team_members']}
                    self.assertTrue({directory.normalized(p['name']) for p in original['team_members']} <= merged_names)
        mapped = {r['team_snapshot']['name'] for r in self.records if r['team_snapshot']}
        self.assertEqual(mapped, set(by_name))

    def test_citi_and_first_citizens_keep_distinct_snapshots(self):
        self.assertEqual(self.record('Citi India')['team_snapshot']['name'], 'Citibank')
        self.assertEqual(self.record('First Citizens Bank')['team_snapshot']['name'], 'First Citizens India')
        self.assertEqual(self.record('Citi (US)')['team_snapshot']['name'], 'Citibank')
        self.assertEqual(self.record('First Citizens Bank (US)')['team_snapshot']['name'], 'First Citizens India')

    def test_similarly_named_financial_and_automotive_employers_do_not_merge(self):
        self.assertEqual(self.record('FIS India')['team_snapshot']['name'], 'FIS (TSYS/Global Payments)')
        self.assertEqual(self.record('Global Payments India')['team_snapshot']['name'], 'Global Payments India')
        self.assertIsNone(self.record('Fidelity India')['team_snapshot'])
        self.assertEqual(self.record('MUFG')['team_snapshot']['name'], 'MUFG')
        self.assertEqual(self.record('MUFG Pension & Market Services (Link Group)')['team_snapshot']['name'], 'MUFG Pension & Market Services (Link Group)')
        self.assertEqual(self.record('Mercedes-Benz R&D India')['team_snapshot']['name'], 'Mercedes-Benz R&D India (MBRDI)')
        self.assertEqual(self.record('Daimler Truck India')['team_snapshot']['name'], 'Daimler Truck India')

    def test_ambiguous_or_substring_only_alias_does_not_guess(self):
        index = directory.alias_index([{'name': 'Citibank'}, {'name': 'First Citizens India'}])
        match, mapping = directory.exact_match({'name': 'Unknown', 'keywords': ['citi', 'first citizens bank']}, index)
        self.assertIsNone(match)
        self.assertEqual(mapping['method'], 'ambiguous_alias')
        match, _ = directory.exact_match({'name': 'First Citizens Bank Staffing', 'keywords': []}, index)
        self.assertIsNone(match)

    def test_recent_research_is_an_overlay_and_all_16_teams_remain_available(self):
        recent = {team['id']: team for team in self.result['recent_teams']}
        mapped = {record['recent_team']['id'] for record in self.records if record['recent_team']}
        self.assertEqual(len(recent), 16)
        self.assertEqual(mapped, set(recent))
        wells = self.record('Wells Fargo')
        self.assertEqual(wells['recent_team'], recent['wells_fargo'])
        self.assertGreater(len(wells['team_snapshot']['team_members']), len(wells['recent_team']['people']))
        self.assertEqual(wells['check_status'], 'pending')

    def test_global_snapshots_do_not_claim_overseas_headcount_or_remote_eligibility(self):
        count = 0
        for record in self.records:
            snapshot = record['team_snapshot']
            if record['category'] == 'global' and snapshot:
                count += 1
                with self.subTest(name=record['name']):
                    provenance = snapshot['_provenance']
                    self.assertEqual(provenance['geographic_scope'], 'India')
                    self.assertIsNone(provenance['current_team_size'])
                    self.assertIn('does not describe this overseas target team', provenance['target_scope_note'])
                    self.assertEqual(provenance['classification'], 'historical_snapshot')
                    self.assertIsNone(provenance['snapshot_date'])
        self.assertGreater(count, 0)

    def test_source_dates_and_size_estimates_are_not_refreshed_by_generation(self):
        self.assertEqual(self.result['sources']['enriched']['as_of'], '2026-09-04')
        self.assertIsNone(self.result['sources']['dossiers']['as_of'])
        for snapshot in self.result['historical_snapshots']:
            provenance = snapshot['_provenance']
            self.assertIn('not a current headcount', provenance['team_size_basis'])
            self.assertEqual(provenance['listed_profiles'], len(snapshot['team_members']))
            self.assertTrue(provenance['team_size_sources'])
        self.assertEqual(self.result['stats']['pending_checks'], len(self.records))

    def test_ast_catalog_reader_does_not_execute_scanner_code(self):
        with tempfile.TemporaryDirectory(prefix='pega-directory-test-') as temp:
            path = Path(temp) / 'scanner.py'
            path.write_text("raise RuntimeError('must never execute')\nCOMPANIES = []\nCONSULTING_COMPANIES = []\nREMOTE_GLOBAL_COMPANIES = []\n", encoding='utf-8')
            self.assertEqual(directory.read_scanner_constants(path)['COMPANIES'], [])
            path.write_text('COMPANIES = list()\nCONSULTING_COMPANIES = []\nREMOTE_GLOBAL_COMPANIES = []\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                directory.read_scanner_constants(path)

    def test_generated_file_matches_actual_catalog_and_snapshot_counts(self):
        saved = json.loads((directory.BASE / 'research' / 'directory.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['stats'], self.result['stats'])
        self.assertEqual({r['target_id'] for r in saved['records']}, {r['target_id'] for r in self.records})


if __name__ == '__main__':
    unittest.main()
