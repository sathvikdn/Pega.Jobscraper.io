import json,sys,unittest,tempfile
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'.deps'));sys.path.insert(0,str(BASE))
import master_catalog,original_views,app,portal_scan
from bs4 import BeautifulSoup

class CatalogueConservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc=master_catalog.build()
        cls.fresh=master_catalog.read(BASE/'research/independent_map.json')
        cls.directory=master_catalog.read(BASE/'research/directory.json')
        cls.recovered=master_catalog.read(BASE/'research/legacy_conservation_20260908.json')
    def test_all_original_profiles_and_named_contacts_survive(self):
        expected=set()
        def collect(value):
            if isinstance(value,str):
                identity=master_catalog.profile_identity(value)
                if identity:expected.add(identity)
            elif isinstance(value,list):
                for x in value:collect(x)
            elif isinstance(value,dict):
                for x in value.values():collect(x)
        collect(self.directory);collect(self.recovered)
        for filename in ('team_intelligence.json','team_intelligence_enriched.json'):collect(master_catalog.read(BASE/filename))
        actual={p['identity_key'] for p in self.doc['people']}
        self.assertGreaterEqual(len(expected),429)
        self.assertFalse(expected-actual)
        self.assertTrue(any(p['name']=='Devender' for p in self.doc['people']))
    def test_all_targets_roster_rows_and_depth_observations_survive(self):
        expected={r['target_id'] for r in self.directory['records']}
        actual={r['target_id'] for c in self.doc['companies'] for r in c['search_targets']}
        self.assertTrue(expected<=actual)
        rows=[r for r in self.doc['person_source_rows'] if r['source_record_id'].startswith('directory.json#historical_snapshots/') and '/team_members/' in r['source_record_id']]
        self.assertEqual(len(rows),403)
        for path in (BASE/'research').glob('team_depth_*.json'):
            for i,row in enumerate(master_catalog.read(path)['team_depth']):
                for j,p in enumerate(row.get('people',[])):
                    rid=path.name+'#team_depth/'+str(i)+'/people/'+str(j)
                    self.assertTrue(any(r['source_record_id']==rid for r in self.doc['person_source_rows']),p['name'])
        self.assertEqual(len(self.doc['legacy_hub_rows']),769)
        self.assertEqual(len(self.doc['movement_observations']),104)
    def test_fresh_company_aliases_cannot_replace_source_claims(self):
        for source in self.fresh['companies']:
            matches=[c for c in self.doc['companies'] if source['id'] in c.get('source_company_ids',[])]
            self.assertEqual(len(matches),1,source['name'])
            company=matches[0]
            for field in ('claims','hiring_signals','limitations'):
                for row in source.get(field,[]):self.assertIn(row,company[field],source['name']+' '+field)
    def test_primary_fresh_titles_never_come_from_legacy(self):
        for p in self.doc['people']:
            fresh=[o for o in p['observations'] if o.get('access')!='legacy']
            if fresh and p.get('title'):
                self.assertIn(p['title'],[o.get('title') for o in fresh],p['name'])
        for c in self.doc['companies']:self.assertIsNotNone(c['category'])
    def test_hub_provenance_and_team_labels_survive_without_fake_employers(self):
        for source in self.recovered['professional_observations']:
            if not source.get('source_file'):continue
            matches=[o for p in self.doc['people'] for o in p['observations'] if o.get('source_record_id')==source['source_record_id'] and o.get('name')==source['name']]
            self.assertTrue(any(o.get('source_file')==source['source_file'] for o in matches),source['name'])
        labels={r['company'] for r in self.recovered['company_observations'] if r.get('entity_kind')!='company_or_group'}
        self.assertFalse(labels & {c['name'] for c in self.doc['companies']})
    def test_curated_healthcare_and_advisory_targets_are_in_active_india_scan(self):
        existing=portal_scan.build_catalog(self.directory['records'],[])
        targets=master_catalog.apply_career_urls(portal_scan.india_targets(portal_scan.build_catalog(existing,master_catalog.extra_targets(self.doc,existing))))
        by_id={target['target_id']:target for target in targets}
        expected_categories={
            'gcc-bd-becton-dickinson':'gcc','gcc-cohere-health':'gcc','gcc-msd-merck-sharp-dohme':'gcc','gcc-pwc-advisory':'gcc',
            'services-ntt-data-north-america':'services','services-tenth-revolution-group':'services','services-vmc-soft-technologies':'services',
            'services-talent-toppers':'services','services-revolent-group':'services','gcc-columbia-sportswear':'gcc','gcc-mizuho':'gcc',
            'services-process360':'services','services-acira-consultancy':'services','services-religent-systems':'services','services-innovationteam':'services',
            'services-allime-tech':'services','services-digitalxnode':'services','gcc-rabobank':'gcc','gcc-metlife-india-gcc':'gcc'}
        for target_id,category in expected_categories.items():
            self.assertIn(target_id,by_id)
            self.assertEqual(by_id[target_id]['category'],category)
        self.assertIn('Becton Dickinson',by_id['gcc-bd-becton-dickinson']['keywords'])
        self.assertIn('jobs.bd.com',by_id['gcc-bd-becton-dickinson'].get('career_url',''))
        self.assertIn('Cohere clinical configuration',by_id['gcc-cohere-health']['keywords'])
        self.assertIn('greenhouse.io/coherehealth',by_id['gcc-cohere-health'].get('career_url',''))
        self.assertIn('MSD',by_id['gcc-msd-merck-sharp-dohme']['keywords'])
        self.assertIn('PwC healthcare GCC Pega',by_id['gcc-pwc-advisory']['keywords'])
        csc=next(target for target in targets if target['name']=='CSC (Corporation Service Company)')
        self.assertIn('cscglobal.com',csc['career_url'])
        self.assertEqual(csc['career_url_basis'],'official override')
        jpmc=next(target for target in targets if target['name'] in ('JPMorgan Chase & Co.','JPMorganChase'))
        self.assertIn('jpmc.fa.oraclecloud.com',jpmc['career_url'])

    def test_original_layout_and_navigation(self):
        dossiers=original_views.dossiers_page(BASE,self.doc)
        soup=BeautifulSoup(dossiers,'html.parser')
        original=BeautifulSoup((BASE/'Pega_Deep_Dossiers.html').read_text(encoding='utf-8'),'html.parser')
        self.assertEqual(soup.style.get_text(),original.style.get_text())
        self.assertNotIn('masterclass',[a.get('href','').lower() for a in soup.find_all('a')])
        career=original_views.career_page(BASE,self.doc,app.PROFILE)
        for page in (career,dossiers,(BASE/'templates/scanner.html').read_text(encoding='utf-8')):
            links=BeautifulSoup(page,'html.parser').find_all('a',href=True)
            self.assertFalse(any('masterclass' in a['href'].lower() for a in links))
        for marker in ('movement-radar','referral-dossiers','team-dossiers'):self.assertIn('id="'+marker+'"',career)

if __name__=='__main__':unittest.main()
