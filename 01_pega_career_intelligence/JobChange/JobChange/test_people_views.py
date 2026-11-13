import copy
import unittest
from unittest.mock import patch
from bs4 import BeautifulSoup
import people_views as pv


class PeopleViewsTests(unittest.TestCase):
    def setUp(self):
        self.company = {'id': 'citi', 'name': 'Citi', 'aliases': ['Citigroup'], 'source_company_ids': ['old-citi']}
        self.person = {'name': 'Person A', 'title': 'Pega Developer', 'company': 'Citi', 'company_id': 'citi', 'location_as_stated': 'Bengaluru', 'profile_url': 'https://in.linkedin.com/in/person-a', 'access': 'search_index', 'checked_at': '2026-09-08', 'work_summary': 'Builds Pega case-management workflows.', 'certifications': ['CSSA']}

    def view(self, **changes):
        return pv.build_person_view(dict(self.person, **changes), self.company)

    def test_hierarchy_and_all_people_preserved(self):
        titles = ['Pega Developer', 'Technical Lead', 'Pega Lead System Architect', 'Engineering Manager', 'Senior Consultant']
        people = [dict(self.person, name=str(i), title=title) for i, title in enumerate(titles)]
        groups = pv.group_people(people, self.company)
        self.assertEqual([g['key'] for g in groups], ['managers', 'architects', 'leads', 'developers', 'other'])
        self.assertEqual(sum(len(g['people']) for g in groups), len(people))

    def test_lsa_is_architect_not_people_manager(self):
        for title in ['Pega Lead System Architect', 'Lead Systems Architect', 'Principal System Architect', 'Senior Technical Architect']:
            with self.subTest(title=title):
                self.assertEqual(self.view(title=title)['role_key'], 'architects')

    def test_seniority_does_not_establish_manager(self):
        for title in ['Vice President', 'SVP', 'Senior Consultant', 'Principal Consultant', 'Director']:
            with self.subTest(title=title):
                self.assertEqual(self.view(title=title)['role_key'], 'other')

    def test_named_management_roles(self):
        for title in ['Engineering Manager', 'Product Owner', 'Program Manager', 'Head of Pega', 'Director, Pega Development']:
            with self.subTest(title=title):
                self.assertEqual(self.view(title=title)['role_key'], 'managers')

    def test_product_name_does_not_establish_manager(self):
        for title in ['Pega Decision Manager Developer', 'Pega Deployment Manager Engineer']:
            with self.subTest(title=title):
                self.assertEqual(self.view(title=title)['role_key'], 'developers')

    def test_pega_ui_ux_lead(self):
        self.assertEqual(self.view(title='Pega UI/UX Lead')['role_key'], 'leads')

    def test_certification_does_not_erase_explicit_developer_role(self):
        self.assertEqual(self.view(title='Senior Pega Developer / Certified CSSA')['role_key'], 'developers')

    def test_certified_architect_clause_does_not_replace_actual_role(self):
        for title, expected in [('Lead SE / Certified Pega Robotics System Architect', 'other'), ('Senior Developer | Certified Pega System Architect', 'developers'), ('Lead System Architect | CSSA', 'architects'), ('Pega UI/UX Lead Software Engineer', 'leads'), ('Certified Pega System Architect / Senior Developer', 'developers')]:
            with self.subTest(title=title):
                self.assertEqual(self.view(title=title)['role_key'], expected)

    def test_old_source_does_not_imply_departure(self):
        v = self.view(checked_at='2020-01-01', access='legacy')
        self.assertNotEqual(v['role_key'], 'historical')
        self.assertNotIn('Former', v['relationship'])

    def test_certification_alone_does_not_become_held_architect_role(self):
        self.assertEqual(self.view(title=None, certifications=['CLSA'])['role_key'], 'other')
        self.assertEqual(self.view(title='Pega-certified Senior System Architect (employment title not exposed)')['role_key'], 'other')

    def test_placeholder_preserved_without_manager_group(self):
        p = dict(self.person, name='Search for Pega Manager', title='Pega Manager', deep_audit={'status': 'not_a_person'})
        result = pv.build_person_view(p, self.company)
        self.assertEqual(result['role_key'], 'other')
        self.assertEqual(result['name'], p['name'])
        self.assertIn('not an identified', pv.render_person(result))

    def test_unresolved_review_keeps_earlier_title_location_and_link(self):
        p = dict(self.person, deep_audit={'status': 'unresolved', 'title': None, 'location_as_stated': None, 'employer_as_stated': None, 'profile_url': None, 'certifications': [], 'checked_at': '2026-09-09'})
        result = pv.build_person_view(p, self.company)
        self.assertEqual(result['title'], 'Pega Developer')
        self.assertEqual(result['title_basis'], 'Earlier title · not reverified')
        self.assertEqual(result['location'], 'Bengaluru')
        self.assertEqual(result['location_basis'], 'Earlier location')
        self.assertEqual(result['relationship'], 'Current employer unconfirmed')
        self.assertEqual(result['linkedin_url'], self.person['profile_url'])
        self.assertEqual(result['linkedin_label'], 'LinkedIn · saved')
        self.assertEqual(result['certifications'][0]['basis'], 'Earlier source · not reverified')

    def test_different_employer_does_not_promote_new_manager_role_to_old_company(self):
        review = {'status': 'partially_supported', 'employer_as_stated': 'New Bank', 'title': 'Pega Engineering Manager', 'company_id': 'new-bank', 'work_summary': 'Pega workflow delivery at New Bank.'}
        result = self.view(deep_audit=review)
        self.assertEqual(result['title'], 'Pega Developer')
        self.assertEqual(result['role_key'], 'historical')
        self.assertEqual(result['recorded_role_key'], 'developers')
        self.assertIn('New Bank', result['relationship'])
        self.assertIn('New Bank', result['work_basis'])
        self.assertNotIn('Former', result['relationship'])
        new = pv.build_person_view(dict(self.person, deep_audit=review), {'id': 'new-bank', 'name': 'New Bank'})
        self.assertEqual(new['title'], 'Pega Engineering Manager')
        self.assertEqual(new['role_key'], 'managers')

    def test_explicit_former_role_is_labelled(self):
        result = self.view(employment_status='former')
        self.assertEqual(result['relationship'], 'Former role recorded')
        self.assertEqual(result['role_key'], 'historical')

    def test_company_membership_does_not_establish_employment_title(self):
        result = self.view(title=None)
        self.assertEqual(result['title'], 'Role not established')
        self.assertEqual(result['role_key'], 'other')

    def test_company_specific_historical_observation_wins(self):
        p = dict(self.person, title='Manager', company='New Bank', observations=[dict(self.person, title='Pega System Architect')])
        result = pv.build_person_view(p, self.company)
        self.assertEqual(result['role_key'], 'architects')

    def test_sources_dates_all_observations_and_career_retained(self):
        first = dict(self.person, title='Pega Developer', source_date='2025-04-01', career=[{'company': 'Old Firm', 'role': 'Developer', 'dates': '2020–2023', 'detail': 'Integration work'}])
        second = dict(self.person, title='Pega Lead Developer', checked_at='2026-09-09')
        p = dict(self.person, observations=[first, second])
        v = pv.build_person_view(p, self.company)
        self.assertEqual(v['title'], 'Pega Lead Developer')
        html = pv.render_person(v)
        for expected in ['2025-04-01', '2026-09-08', '2026-09-09', 'Old Firm', 'Integration work', 'Search-index observation']:
            self.assertIn(expected, html)
        self.assertEqual(len(v['history']), 2)

    def test_legacy_source_never_labelled_fresh(self):
        v = self.view(access='legacy', checked_at=None)
        self.assertIn('Earlier title', v['title_basis'])
        self.assertEqual(v['sources'][0]['access_label'], 'Earlier source · not reverified')

    def test_review_history_retained(self):
        p = dict(self.person, research_history=[{'summary': 'Earlier source review', 'title': 'Engineer', 'sources': [{'url': 'https://example.org/speaker', 'access': 'page', 'checked_at': '2026-08-01'}]}])
        html = pv.render_profile(p, self.company)
        self.assertIn('Earlier source reviews (1)', html)
        self.assertIn('2026-08-01', html)
        self.assertIn('https://example.org/speaker', html)

    def test_all_profile_body_content_collapsed_and_link_visible(self):
        soup = BeautifulSoup(pv.render_profile(self.person, self.company), 'html.parser')
        article = soup.select_one('.pv-person')
        self.assertIsNotNone(article)
        self.assertFalse(article.select('details[open]'))
        self.assertEqual(article['data-location'], 'Bengaluru')
        self.assertEqual(article.select_one(':scope > .person-profile-link a').get_text(), 'LinkedIn')
        self.assertIsNone(article.select_one('summary .person-body'))
        self.assertEqual(len(article.select('summary .person-badge')), 1)
        self.assertIsNotNone(article.select_one('details .person-body'))

    def test_company_linking_preserves_alias_ids_and_repeated_associations(self):
        a = dict(self.person, company_id='elsewhere', company_ids=['old-citi'])
        b = dict(self.person, name='Other', company_id='other')
        c = dict(self.person, name='C', company_id=None, company_ids=['citi', 'new-bank'])
        self.assertEqual(pv.linked_people(self.company, [a, b, c]), [a, c])
        soup = BeautifulSoup(pv.render_company_people(self.company, [a, b, c]), 'html.parser')
        self.assertEqual(len(soup.select('.pv-person')), 2)
        self.assertTrue(soup.select('.pv-group'))

    def test_linkedin_url_rejects_lookalikes_and_active_schemes(self):
        for url in ['javascript:alert(1)', 'data:text/html,bad', 'https://linkedin.com.evil.test/in/x', 'https://linkedin.com@evil.test/in/x', '//linkedin.com/in/x', 'https://linkedin.com\\@evil.test/in/x', 'https://linkedin.com:bad/in/x']:
            with self.subTest(url=url):
                self.assertEqual(pv.linkedin_url(url), '')
        self.assertEqual(pv.linkedin_url('https://in.linkedin.com/in/test'), 'https://in.linkedin.com/in/test')

    def test_xss_is_escaped_in_every_render_surface(self):
        payload = '<img src=x onerror="alert(1)">'
        p = dict(self.person, name=payload, title=payload, location_as_stated=payload, work_summary=payload, certifications=[payload], profile_url='javascript:alert(1)', source_url='javascript:alert(1)', limitations=[payload], observations=[dict(self.person, work_summary=payload, career=[{'role': payload, 'detail': payload}])])
        rendered = pv.render_profile(p, self.company)
        soup = BeautifulSoup(rendered, 'html.parser')
        self.assertFalse(soup.select('img,script,iframe'))
        self.assertFalse(any(a.get('href', '').startswith('javascript:') for a in soup.find_all('a')))
        self.assertIn('&lt;img', rendered)
        self.assertIn(payload, soup.get_text())

    def test_saved_profile_link_retained_when_source_and_review_links_differ(self):
        old = self.person['profile_url']
        p = dict(self.person, source_url='https://example.com/speaker', deep_audit={'status': 'partially_supported', 'title': 'Developer', 'employer_as_stated': 'Citi', 'profile_url': 'https://linkedin.com/in/new-profile'})
        soup = BeautifulSoup(pv.render_profile(p, self.company), 'html.parser')
        self.assertEqual(soup.select_one('.person-profile-link a')['href'], 'https://linkedin.com/in/new-profile')
        old_links = soup.find_all('a', href=old)
        self.assertTrue(old_links)
        self.assertTrue(all(link.find_parent('details') for link in old_links))

    def test_lazy_card_keeps_summary_link_and_certification_search(self):
        person = dict(self.person, id='person-a', observations=[dict(self.person, certifications=['CLSA'], certs=['CPDC'])], research_history=[{'certifications': ['CPMC']}])
        view = pv.build_person_view(person, self.company)
        with patch.object(pv, '_render_person_body', side_effect=AssertionError('Full details must not be rendered')):
            lazy = BeautifulSoup(pv.render_person(view, include_details=False), 'html.parser')
            grouped = BeautifulSoup(pv.render_company_people(self.company, [person], include_details=False), 'html.parser')
        for soup in [lazy, grouped]:
            card = soup.select_one('.pv-person')
            self.assertEqual(card['data-person-id'], 'person-a')
            self.assertEqual(card['data-company-id'], 'citi')
            self.assertIsNotNone(card.select_one('details[data-profile-lazy="true"]'))
            self.assertEqual(card.select_one('.person-body').get_text(), '')
            self.assertNotIn('Saved observations', card.get_text())
            self.assertEqual(card.select_one('.person-profile-link a')['href'], self.person['profile_url'])
            for text in ['Person A', 'Pega Developer', 'Bengaluru', 'CSSA', 'CLSA', 'CPDC', 'CPMC']:
                self.assertIn(text, card['data-search'])
        full = BeautifulSoup(pv.render_person(view), 'html.parser')
        self.assertIsNone(full.select_one('[data-profile-lazy]'))
        self.assertIn(self.person['work_summary'], full.select_one('.person-body').get_text())
        self.assertEqual(lazy.select_one('summary').get_text(), full.select_one('summary').get_text())

    def test_input_is_not_mutated(self):
        person = copy.deepcopy(self.person)
        before = copy.deepcopy(person)
        pv.render_profile(person, self.company)
        self.assertEqual(person, before)

    def test_empty_company_has_clear_no_profile_state(self):
        self.assertIn('No named professional profiles', pv.render_company_people(self.company, []))


if __name__ == '__main__':
    unittest.main()
