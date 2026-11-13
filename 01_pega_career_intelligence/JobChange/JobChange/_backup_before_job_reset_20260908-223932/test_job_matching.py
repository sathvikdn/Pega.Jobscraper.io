"""Policy regressions: false positives must not become recommendations."""
import tempfile
import unittest
from pathlib import Path

from job_matching import assess_job, plain_text


class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.resume = Path(self.temp.name) / 'resume.html'
        self.resume.write_text("""<html><head><script>CDH CLSA</script></head><body>
          <h1>Candidate</h1><p>Skills: Constellation, DX API</p>
          <ul><li>Designed Pega case management and <strong>REST</strong> services using Kafka, data pages and SQL.</li></ul>
          <div class="credential"><div class="credential-title">Pega Certified Senior System Architect</div><div>CSSA</div></div>
          <p>Currently learning Customer Decision Hub.</p>
        </body></html>""", encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def check(self, description, **kwargs):
        job = {'description_text': description, 'description_complete': True,
               'job_detail_status': 'read', 'title': 'Pega Developer', **kwargs}
        return assess_job(job, self.resume)

    def test_jd_repeated_title_is_not_a_responsibility(self):
        result = self.check('Senior Pega Developer\nDevelop Java applications. 4–6 years experience.')
        self.assertEqual(result['recommendation']['status'], 'excluded')

    def test_title_company_query_and_skills_are_not_proof(self):
        result = self.check('Required: develop Java applications. Experience: 4–7 years.',
                            company='Pega', query='Pega developer', skills=['Pega'])
        self.assertEqual(result['recommendation']['status'], 'excluded')
        self.assertIsNone(result['resume_match']['score'])

    def test_snippet_is_not_a_saved_full_description(self):
        result = assess_job({'title': 'Pega Developer', 'summary': 'Pega development 4 years',
                             'description': 'Pega development 4 years', 'job_detail_status': 'read'}, self.resume)
        self.assertEqual(result['recommendation']['status'], 'review')
        self.assertIsNone(result['resume_match']['score'])

    def test_failed_recheck_retains_text_but_is_review(self):
        result = self.check('Develop Pega applications. Experience: 4–6 years.', job_detail_status='blocked')
        self.assertEqual(result['recommendation']['status'], 'review')
        self.assertIsNone(result['resume_match']['score'])

    def test_company_boilerplate_is_not_pega_evidence(self):
        for text in [
            'Develop Java applications. Experience: 4–6 years.\nAbout Us\nWe provide Pega development services.',
            'Our company is a leading Pega implementation partner.\nDevelop Java applications. Experience: 4 years.',
            'Pega helps companies automate processes. Develop Java applications. Experience: 4 years.'
        ]:
            with self.subTest(text=text):
                self.assertEqual(self.check(text)['recommendation']['status'], 'excluded')

    def test_required_role_after_boilerplate_can_qualify(self):
        result = self.check('About Us\nWe serve many clients.\nResponsibilities\nDevelop Pega applications.\nRequired experience\n4–7 years')
        self.assertTrue(result['recommendation']['eligible'])

    def test_optional_alternative_platform_is_not_specific(self):
        for text in ['Experience with Pega or Appian. 4–6 years of experience.',
                     'Experience in any of Pega, Appian or Camunda. 4–6 years experience.',
                     'Develop Java applications; Pega knowledge preferred. 4–6 years experience.',
                     'Experience with Salesforce or Pega. 4–6 years experience.']:
            with self.subTest(text=text):
                self.assertEqual(self.check(text)['recommendation']['status'], 'excluded')

    def test_pega_is_mandatory_even_when_other_skills_are_alternatives(self):
        result = self.check('Develop Pega applications. Java or JavaScript knowledge preferred. 4–6 years experience.')
        self.assertTrue(result['recommendation']['eligible'])

    def test_java_service_interfacing_with_pega_is_not_specific(self):
        result = self.check('Develop Java APIs integrating with Pega. Experience: 4–6 years.')
        self.assertEqual(result['recommendation']['status'], 'excluded')

    def test_prpc_and_pegarules_are_valid_role_evidence(self):
        for platform in ('PRPC', 'PegaRULES'):
            with self.subTest(platform=platform):
                self.assertTrue(self.check(f'Develop applications using {platform}. 4–6 years of experience.')['recommendation']['eligible'])

    def test_four_to_seven_fits(self):
        result = self.check('Develop Pega applications. Required experience: 4–7 years.')
        self.assertTrue(result['recommendation']['eligible'])
        self.assertEqual(result['recommendation']['minimum_years'], 4)
        self.assertEqual(result['recommendation']['maximum_years'], 7)

    def test_5_to_7_is_stretch(self):
        result = self.check('Develop Pega applications. Required experience: 5–7 years.')
        self.assertTrue(result['recommendation']['eligible'])
        self.assertEqual(result['recommendation']['status'], 'stretch')

    def test_explicit_ranges_with_eight_are_excluded(self):
        for amount in ('3–8 years', '4 to 10 years', '8 years', '10+ years', 'eight to ten years'):
            with self.subTest(amount=amount):
                result = self.check('Develop Pega applications. Required experience: ' + amount)
                self.assertEqual(result['recommendation']['status'], 'excluded')

    def test_four_plus_minimum_is_clear_about_unknown_upper(self):
        result = self.check('Develop Pega applications. Minimum 4+ years of experience.')
        self.assertTrue(result['recommendation']['eligible'])
        self.assertIsNone(result['recommendation']['maximum_years'])
        self.assertIn('upper limit not stated', result['recommendation']['experience_label'])

    def test_word_numbers_and_months_are_interpreted(self):
        for amount in ('between four and seven years', '48–84 months', '4 years to 7 years'):
            with self.subTest(amount=amount):
                result = self.check('Develop Pega applications. Required experience: ' + amount)
                self.assertEqual(result['recommendation']['minimum_years'], 4)
                self.assertEqual(result['recommendation']['maximum_years'], 7)
                self.assertTrue(result['recommendation']['eligible'])

    def test_company_age_does_not_override_work_experience(self):
        text = 'Our company has 25 years of experience in consulting.\nDevelop Pega applications. Required experience: 4–6 years.'
        self.assertTrue(self.check(text)['recommendation']['eligible'])

    def test_unknown_experience_is_review(self):
        result = self.check('Develop Pega case management applications with REST services.')
        self.assertEqual(result['recommendation']['status'], 'review')
        self.assertFalse(result['recommendation']['eligible'])
        self.assertIsNone(result['recommendation']['minimum_years'])
        self.assertIsNotNone(result['resume_match']['score'])

    def test_total_experience_overrides_fewer_pega_years(self):
        text = 'Required: develop Pega applications with 4 years of Pega experience. Overall 10 years.'
        self.assertEqual(self.check(text)['recommendation']['status'], 'excluded')

    def test_degree_duration_is_not_job_experience(self):
        result = self.check('Develop Pega applications. A four year degree in computer science is required.')
        self.assertEqual(result['recommendation']['status'], 'review')

    def test_less_than_eight_is_not_same_as_including_eight(self):
        result = self.check('Develop Pega applications. Less than eight years of experience.')
        self.assertTrue(result['recommendation']['eligible'])
        self.assertIn('Less than 8', result['recommendation']['experience_label'])

    def test_closed_roles_are_excluded(self):
        for extra in ({'status': 'closed'}, {'expired': True}, {'validThrough': '2000-01-01T00:00:00Z'}):
            with self.subTest(extra=extra):
                result = self.check('Develop Pega applications. 4–6 years experience.', **extra)
                self.assertEqual(result['recommendation']['status'], 'excluded')
                self.assertIsNone(result['resume_match']['score'])

    def test_closure_message_is_excluded(self):
        result = self.check('This job has expired. Develop Pega applications. 4–6 years experience.')
        self.assertEqual(result['recommendation']['status'], 'excluded')

    def test_html_scripts_do_not_prove_relevance(self):
        result = self.check('<script>Develop Pega applications. 4 years experience.</script><p>Develop Java applications. 4 years experience.</p>')
        self.assertEqual(result['recommendation']['status'], 'excluded')

    def test_hidden_html_is_not_evidence(self):
        text = '<div style="display:none">Develop Pega applications.</div><p>Java development, 4 years experience.</p>'
        self.assertNotIn('Pega', plain_text(text))
        self.assertEqual(self.check(text)['recommendation']['status'], 'excluded')

    def test_div_requirements_are_preserved(self):
        result = self.check('<p>Responsibilities</p><div>Develop Pega applications.</div><div>4–6 years experience.</div>')
        self.assertTrue(result['recommendation']['eligible'])

    def test_score_is_evidence_not_probability(self):
        result = self.check('Develop Pega applications using Kafka and REST. 4–6 years experience.')['resume_match']
        self.assertEqual(result['score'], 100)
        self.assertIn('not an ATS score', result['method'])
        rest = next(item for item in result['matched'] if item['requirement'] == 'REST')
        self.assertEqual(rest['evidence_strength'], 'project')
        self.assertIn('REST services', rest['evidence'])

    def test_cdh_and_clsa_are_mandatory_gaps_not_inferred(self):
        result = self.check('Develop Pega applications. CDH experience and CLSA certification are mandatory. 4–6 years experience.')['resume_match']
        names = [item['requirement'] for item in result['missing']]
        self.assertIn('Customer Decision Hub / CDH', names)
        self.assertIn('CLSA certification', names)
        self.assertTrue(all(item['importance'] == 'required' for item in result['missing']))
        self.assertLess(result['score'], 100)

    def test_listed_constellation_is_not_project_evidence(self):
        result = self.check('Develop Pega applications. Constellation experience is required. 4–6 years experience.')['resume_match']
        item = next(item for item in result['matched'] if item['requirement'] == 'Constellation')
        self.assertEqual(item['evidence_strength'], 'listed')
        self.assertLess(result['score'], 100)

    def test_certification_alternative_is_one_requirement(self):
        result = self.check('Develop Pega applications. CSSA or CLSA certification is required. 4–6 years experience.')['resume_match']
        certs = [item for item in result['matched'] if 'certification' in item['requirement']]
        self.assertEqual(len(certs), 1)
        self.assertIn(' or ', certs[0]['requirement'])
        self.assertNotIn('CLSA certification', [item['requirement'] for item in result['missing']])

    def test_preferred_gap_is_labeled(self):
        result = self.check('Develop Pega applications. React knowledge preferred. 4–6 years experience.')['resume_match']
        react = next(item for item in result['missing'] if item['requirement'] == 'React')
        self.assertEqual(react['importance'], 'preferred')

    def test_missing_resume_does_not_make_up_score(self):
        result = assess_job({'description_text': 'Develop Pega applications. 4–6 years experience.', 'description_complete': True, 'job_detail_status': 'read'}, Path(self.temp.name) / 'absent.html')
        self.assertIsNone(result['resume_match']['score'])

    def test_real_resume_has_project_kafka_and_listed_constellation(self):
        result = assess_job({'description_text': 'Develop Pega applications with Kafka and Constellation. CSSA certification required. 4–6 years experience.', 'description_complete': True, 'job_detail_status': 'read'})['resume_match']
        skills = {item['requirement']: item for item in result['matched']}
        self.assertEqual(skills['Kafka']['evidence_strength'], 'project')
        self.assertEqual(skills['Constellation']['evidence_strength'], 'listed')
        self.assertEqual(skills['CSSA certification']['evidence_strength'], 'certification')

    def test_read_resume_cache_is_path_specific(self):
        other = Path(self.temp.name) / 'other.html'
        other.write_text('<p>Java programming</p>', encoding='utf-8')
        job = {'description_text': 'Develop Pega applications with Kafka. 4–6 years experience.', 'description_complete': True, 'job_detail_status': 'read'}
        first = assess_job(job, self.resume)['resume_match']
        second = assess_job(job, other)['resume_match']
        self.assertGreater(first['score'], second['score'])


    def test_inaccessible_source_is_review_not_closed(self):
        result = self.check('Develop Pega applications. 4–6 years experience.', job_detail_status='unavailable')
        self.assertEqual(result['recommendation']['status'], 'review')

    def test_source_read_does_not_hide_explicit_closure(self):
        result = self.check('Develop Pega applications. 4–6 years experience.', research_status='expired')
        self.assertEqual(result['recommendation']['status'], 'excluded')

    def test_today_date_only_closing_is_not_expired_at_midnight(self):
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date().isoformat()
        self.assertTrue(self.check('Develop Pega applications. 4–6 years experience.', closing_at=today)['recommendation']['eligible'])

    def test_project_duration_is_not_experience(self):
        result = self.check('Develop Pega applications for a 10 year roadmap.')
        self.assertEqual(result['recommendation']['status'], 'review')

    def test_certification_not_required_is_not_a_gap(self):
        result = self.check('Develop Pega applications. CLSA certification is not required. 4–6 years experience.')['resume_match']
        self.assertNotIn('CLSA certification', [item['requirement'] for item in result['missing']])

    def test_slash_certifications_are_alternatives(self):
        result = self.check('Develop Pega applications. CSSA/CLSA certification required. 4–6 years experience.')['resume_match']
        self.assertFalse(result['missing'])

    def test_mandatory_missing_certification_remains_visible_despite_many_matches(self):
        result = self.check('Develop Pega applications with REST, Kafka, SQL, case management and data pages. CLSA certification required. 4–6 years experience.')
        self.assertEqual(result['recommendation']['status'], 'stretch')
        self.assertTrue(result['recommendation']['eligible'])
        self.assertLessEqual(result['resume_match']['score'], 69)


    def test_real_kafka_evidence_is_implementation_not_project_title(self):
        result = assess_job({'description_text': 'Develop Pega applications using Kafka. 4–6 years experience.', 'description_complete': True, 'job_detail_status': 'read'})['resume_match']
        kafka = next(item for item in result['matched'] if item['requirement'] == 'Kafka')
        self.assertEqual(kafka['evidence_strength'], 'project')
        self.assertIn('Designed the Pega integration layer', kafka['evidence'])
        self.assertIn('50+ Kafka topics', kafka['evidence'])

    def test_project_heading_alone_is_listed_evidence(self):
        self.resume.write_text('<article><h3>Kafka Integration</h3><p>Coordinated the team.</p></article>', encoding='utf-8')
        result = self.check('Develop Pega applications using Kafka. 4–6 years experience.')['resume_match']
        kafka = next(item for item in result['matched'] if item['requirement'] == 'Kafka')
        self.assertEqual(kafka['evidence_strength'], 'listed')

    def test_pega_ai_products_are_scored_individually_against_actual_resume(self):
        result = assess_job({'description_text': 'Develop Pega applications. Pega GenAI, KnowledgeBuddy and Pega Blueprint experience required. 4–6 years experience.', 'description_complete': True, 'job_detail_status': 'read'})['resume_match']
        matched = {item['requirement']: item for item in result['matched']}
        missing = {item['requirement']: item for item in result['missing']}
        self.assertEqual(matched['Pega GenAI']['evidence_strength'], 'listed')
        self.assertEqual(matched['Pega Blueprint']['evidence_strength'], 'listed')
        self.assertEqual(missing['Pega Knowledge Buddy']['importance'], 'required')

    def test_generic_ai_and_diagram_blueprints_do_not_imply_pega_products(self):
        self.resume.write_text('<li>Built AI-assisted tools and architecture blueprints.</li>', encoding='utf-8')
        result = self.check('Develop Pega applications. Pega GenAI, Knowledge Buddy and Pega Blueprint experience required. 4–6 years experience.')['resume_match']
        missing = {item['requirement'] for item in result['missing']}
        self.assertTrue({'Pega GenAI', 'Pega Knowledge Buddy', 'Pega Blueprint'} <= missing)


if __name__ == '__main__':
    unittest.main()
