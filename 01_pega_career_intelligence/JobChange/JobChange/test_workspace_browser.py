import json
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE=Path(__file__).resolve().parent


class WorkspaceBrowserTests(unittest.TestCase):
    def test_full_workspace_filter_and_detail_integration(self):
        import tempfile
        from urllib.parse import urlsplit
        from app import create_app
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            application=create_app(root/'data',root/'research')
            repository=application.extensions['store']
            for index,(city,source) in enumerate([('Bengaluru','Indeed'),('Pune','Glassdoor')]):
                repository.save_job_batch('fixture',source,[{'title':'Pega Developer','company':'Truviq Systems','location':city,'url':'https://example.com/jobs/'+str(index),'source':source}])
            client=application.test_client()
            with sync_playwright() as driver:
                browser=driver.chromium.launch(headless=True)
                try:
                    page=browser.new_page()
                    def serve(route):
                        url=urlsplit(route.request.url)
                        with client.get(url.path+('?' + url.query if url.query else '')) as response:
                            route.fulfill(status=response.status_code,body=response.get_data(),content_type=response.content_type)
                    page.route('http://127.0.0.1:8765/**',serve)
                    page.goto('http://127.0.0.1:8765/#results')
                    page.wait_for_function("document.getElementById('rTotal').textContent === '2'")
                    page.locator('[data-location="bengaluru"]').click()
                    self.assertEqual(page.locator('#rTotal').inner_text(),'1')
                    self.assertEqual(page.locator('#mainContent tbody tr').count(),1)
                    page.get_by_role('button',name='View description',exact=True).click()
                    page.wait_for_function("document.getElementById('jobDialogStatus').textContent === 'Saved description loaded.'")
                    self.assertIn('Truviq Systems',page.locator('#jobDialogContent').inner_text())
                    self.assertEqual(page.locator('#tabIntel, #intelTab, #platformStats, #platformStatsResults, #scanLog').count(),0)
                    self.assertEqual(page.locator('a[href="/intel"]').count(),0)
                    self.assertEqual(page.locator('#mainContent button.workspace-employer').count(),0)
                    page.get_by_role('button',name='Close job description').click()
                    page.get_by_role('button',name='New scan',exact=True).click()
                    self.assertEqual(page.locator('.cat-tabs button').all_text_contents(),['GCC / Product','Consulting / SI','All'])
                    self.assertTrue(page.locator('#scanBtn').is_enabled())
                finally:browser.close()

    def test_application_status_survives_switching_jobs_and_reload(self):
        import tempfile
        from urllib.parse import urlsplit
        from app import create_app
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            application=create_app(root/'data',root/'research')
            repository=application.extensions['store']
            repository.save_job_batch('fixture','Employer',[{'title':title,'company':'Truviq Systems','location':'Bengaluru, India','url':'https://example.com/jobs/'+str(index),'source':'Employer'} for index,title in enumerate(('Pega Developer','Pega Architect'))])
            client=application.test_client()
            with sync_playwright() as driver:
                browser=driver.chromium.launch(headless=True)
                try:
                    page=browser.new_page()
                    responses=[]
                    def serve(route):
                        request=route.request
                        url=urlsplit(request.url)
                        response=client.open(url.path+('?' + url.query if url.query else ''),method=request.method,data=request.post_data,headers={'Host':url.netloc,**{key:value for key,value in request.headers.items() if key in ('x-career-token','content-type','origin')}})
                        if request.method=='POST':responses.append((url.path,response.status_code,response.get_json()))
                        route.fulfill(status=response.status_code,body=response.get_data(),content_type=response.content_type)
                    page.route('http://127.0.0.1:8765/**',serve)
                    page.goto('http://127.0.0.1:8765/#results')
                    page.wait_for_function("document.getElementById('rTotal').textContent === '2'")
                    first=page.locator('#mainContent tbody tr').filter(has_text='Pega Developer')
                    second=page.locator('#mainContent tbody tr').filter(has_text='Pega Architect')
                    options=['Not reviewed','Interested','Recruiter contacted','Applied','Interviewing','Offer','Not relevant / rejected']
                    self.assertEqual(first.locator('select.application-select option').all_text_contents(),options)
                    first.locator('select.application-select').select_option('applied')
                    page.wait_for_function("document.querySelector('#mainContent tbody tr select.application-select')?.value === 'applied' && document.querySelector('#mainContent tbody tr select.application-select')?.disabled === false",timeout=10000)
                    self.assertEqual(first.locator('select.application-select').input_value(),'applied',msg=str(responses))
                    self.assertEqual(second.locator('select.application-select').input_value(),'unreviewed')
                    self.assertGreaterEqual(first.locator('.application-cell').evaluate('(element) => parseInt(getComputedStyle(element).paddingLeft)'),14)
                    page.locator('#reviewScope').click()
                    page.wait_for_function("document.getElementById('reviewScope').getAttribute('aria-pressed') === 'true'")
                    self.assertEqual(first.locator('select.application-select').input_value(),'applied')
                    page.locator('#allScope').click()
                    page.wait_for_function("document.getElementById('allScope').getAttribute('aria-pressed') === 'true'")
                    self.assertEqual(first.locator('select.application-select').input_value(),'applied')
                    first.get_by_role('button',name='View description').click()
                    page.wait_for_function("document.getElementById('jobDialogStatus').textContent === 'Saved description loaded.'")
                    self.assertEqual(page.locator('#applicationStage option').all_text_contents(),options)
                    self.assertEqual(page.locator('#applicationStage').input_value(),'applied')
                    page.locator('#applicationNotes').fill('Referral asked; follow up Friday')
                    page.get_by_role('button',name='Save changes').click()
                    page.wait_for_function("document.getElementById('jobDialogStatus').textContent.startsWith('Saved for this job:')")
                    page.get_by_role('button',name='Close job description').click()
                    second.get_by_role('button',name='View description').click()
                    page.wait_for_function("document.getElementById('jobDialogStatus').textContent === 'Saved description loaded.'")
                    self.assertEqual(page.locator('#applicationStage').input_value(),'unreviewed')
                    page.get_by_role('button',name='Close job description').click()
                    first.get_by_role('button',name='View description').click()
                    page.wait_for_function("document.getElementById('jobDialogStatus').textContent === 'Saved description loaded.'")
                    self.assertEqual(page.locator('#applicationStage option').all_text_contents(),options)
                    self.assertEqual(page.locator('#applicationStage').input_value(),'applied')
                    self.assertEqual(page.locator('#applicationNotes').input_value(),'Referral asked; follow up Friday')
                    page.locator('#applicationStage').select_option('interviewing')
                    page.wait_for_function("document.getElementById('jobDialogStatus').textContent === 'Saved for this job: Interviewing.'")
                    page.get_by_role('button',name='Close job description').click()
                    page.reload()
                    page.wait_for_function("document.getElementById('rTotal').textContent === '2'")
                    self.assertEqual(page.locator('#mainContent tbody tr').filter(has_text='Pega Developer').locator('select.application-select').input_value(),'interviewing')
                    self.assertEqual(page.locator('#mainContent tbody tr').filter(has_text='Pega Architect').locator('select.application-select').input_value(),'unreviewed')
                    page.route('**/api/pipeline/**',lambda route:route.fulfill(status=403,content_type='application/json',body='{"error":"Saving unavailable"}'))
                    first.locator('select.application-select').select_option('shortlisted')
                    page.wait_for_function("document.querySelector('#mainContent tbody tr .application-feedback')?.textContent.includes('Not saved: Saving unavailable')")
                    self.assertEqual(first.locator('select.application-select').input_value(),'interviewing')
                    first.get_by_role('button',name='View description').click()
                    page.wait_for_function("document.getElementById('jobDialogStatus').textContent === 'Saved description loaded.'")
                    page.locator('#applicationStage').select_option('offer')
                    page.wait_for_function("document.getElementById('jobDialogStatus').textContent.includes('Could not save: Saving unavailable')")
                    self.assertEqual(page.locator('#applicationStage').input_value(),'interviewing')
                    self.assertEqual(page.locator('#applicationNotes').input_value(),'Referral asked; follow up Friday')
                finally:browser.close()

    def test_safe_table_and_dossier_tabs(self):
        with sync_playwright() as driver:
            browser=driver.chromium.launch(headless=True)
            try:
                page=browser.new_page()
                page.route('**/api/company-dossier?*',lambda route:route.fulfill(content_type='application/json',body=json.dumps({
                    'offices':[], 'frameworks':[], 'openings':[],
                    'sources':[{'title':'<img src=x onerror=alert(1)>','text':'Untrusted <script> content','url':'javascript:alert(1)'}]})))
                page.route('http://127.0.0.1:8765/',lambda route:route.fulfill(body='<html><body></body></html>',content_type='text/html'))
                page.goto('http://127.0.0.1:8765/')
                page.add_script_tag(path=str(BASE/'static'/'dossier-view.js'))
                page.add_script_tag(path=str(BASE/'static'/'job-workspace.js'))
                page.evaluate("""() => document.body.append(JobWorkspace.table([
                    {title:'<img src=x onerror=alert(1)>',company:'Truviq Systems',url:'javascript:alert(1)',location:'Bengaluru',recommendation:{status:'review'}}
                ],()=>{},DossierView.open))""")
                self.assertEqual(page.locator('img').count(),0)
                self.assertEqual(page.locator('a[href^="javascript:"]').count(),0)
                self.assertIn('Undisclosed',page.locator('table').inner_text())
                page.get_by_role('button',name='Truviq Systems').click()
                page.get_by_role('tab',name='Source freshness').click()
                self.assertEqual(page.locator('dialog img').count(),0)
                self.assertEqual(page.locator('dialog a').count(),0)
                self.assertIn('Untrusted <script> content',page.get_by_role('tabpanel').inner_text())
                page.get_by_role('button',name='Close',exact=True).click()
                page.locator('dialog').wait_for(state='detached')
                self.assertEqual(page.locator('dialog').count(),0)
            finally:
                browser.close()


if __name__=='__main__':unittest.main()
