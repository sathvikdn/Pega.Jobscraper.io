'use strict';
let selectedCat='gcc',selectedMode='gcc_top10',pollTimer=null,allResults=[],selectedCompany=null,csrf='',depthConfigs={},pollBusy=false,scanActive=false,resultScope='recommended',resultsRequest=0,detailRequest=0,detailJob=null,detailOpener=null;
const byId=id=>document.getElementById(id);
function node(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=String(text);return e;}
function put(parent,...children){for(const c of children.flat())if(c)parent.append(c);return parent;}
function action(text,fn,cls){const b=node('button',cls,text);b.type='button';b.addEventListener('click',fn);return b;}
function safeLink(text,url,cls){const a=node('a',cls,text);try{const u=new URL(url,location.origin);if(!['http:','https:'].includes(u.protocol))return node('span',cls,text);a.href=u.href;a.target='_blank';a.rel='noopener noreferrer';}catch{return node('span',cls,text);}return a;}
async function request(path,options={}){const r=await fetch(path,{...options,headers:{'Content-Type':'application/json','X-Career-Token':csrf,...options.headers}});const data=await r.json();if(!r.ok)throw Error(data.error||'Request failed');return data;}
function logError(error){byId('scanLog').classList.add('show');byId('scanLog').append(node('div','ln',error.message||error));}
function renderDepth(){
 const cfg=depthConfigs[selectedCat]||[],row=byId('depthRow');row.replaceChildren();
 if(!cfg.some(d=>d.mode===selectedMode))selectedMode=cfg[0]?.mode;
 for(const d of cfg){const label=d.label+(d.label==='Top 10'&&d.count===10||d.label==='Top 20'&&d.count===20?'':' ('+d.count+')');const b=action(label,()=>{if(scanActive)return;selectedMode=d.mode;renderDepth();},'dp'+(d.mode===selectedMode?' active':''));b.disabled=scanActive||!d.count;b.dataset.mode=d.mode;b.setAttribute('aria-pressed',String(d.mode===selectedMode));row.append(b);}
 for(const t of document.querySelectorAll('.cat-tab[data-cat]')){t.classList.toggle('active',t.dataset.cat===selectedCat);t.disabled=scanActive;t.setAttribute('aria-pressed',String(t.dataset.cat===selectedCat));}
}
async function startScan(){
 if(scanActive)return;
 const choice=(depthConfigs[selectedCat]||[]).find(d=>d.mode===selectedMode);if(!choice?.count){logError(Error('Choose a category and depth first.'));return;}
 scanActive=true;byId('scanBtn').disabled=true;byId('scanBtn').textContent='Scanning…';renderDepth();
 byId('progArea').classList.add('show');byId('scanLog').classList.add('show');byId('scanLog').replaceChildren();byId('progTxt').textContent='Starting Python scanner…';byId('progFill').style.width='0%';
 try{await request('/api/scan',{method:'POST',body:JSON.stringify({mode:selectedMode})});startPolling();await pollStatus();}
 catch(e){scanActive=false;byId('scanBtn').disabled=false;byId('scanBtn').textContent='Start scanning →';renderDepth();logError(e);}
}
function startPolling(){if(pollTimer)clearInterval(pollTimer);pollTimer=setInterval(pollStatus,1500);}
async function pollStatus(){
 if(pollBusy)return;pollBusy=true;
 try{
  const s=await request('/api/status'),pct=s.total?Math.min(100,Math.round(s.progress/s.total*100)):0;
  byId('progFill').style.width=pct+'%';
  byId('progTxt').textContent=s.running?(s.phase==='job_details'?'Checking job descriptions':'Scanning '+(s.current_company||'selected companies'))+' ('+s.progress+'/'+s.total+')':s.error?'Scan stopped — saved results retained':'Scan complete';
  const log=byId('scanLog');log.replaceChildren();for(const [i,l] of (s.log_lines||[]).entries())log.append(node('div','ln'+(i===s.log_lines.length-1&&s.running?' cur':''),l));log.scrollTop=log.scrollHeight;
  if(!s.running&&s.scanner?.status==='interrupted')logError(Error(s.scanner.error||'Previous scan interrupted; completed results saved.'));
  if(!s.running){clearInterval(pollTimer);pollTimer=null;scanActive=false;byId('scanBtn').disabled=false;byId('scanBtn').textContent='Start scanning →';renderDepth();if(s.error)logError(Error(s.error));await switchToResults();}
 }catch(e){logError(Error('Connection interrupted. Retrying while the scan continues. '+e.message));}finally{pollBusy=false;}
}
async function switchToResults(scope=resultScope,preserveCompany=false){
 const requestNumber=++resultsRequest;
 try{
  const data=await request('/api/scan-results'+(scope==='review'?'?scope=review':''));
  if(requestNumber!==resultsRequest)return;
  resultScope=scope;allResults=data.companies||[];
  byId('rNew').textContent=new Set(allResults.flatMap(c=>c.jobs.filter(j=>j.is_new).map(j=>j.id))).size;byId('rTotal').textContent=new Set(allResults.flatMap(c=>c.jobs.map(j=>j.id))).size;byId('rCo').textContent=allResults.filter(c=>c.jobs.length).length;
  const counts=data.policy_counts||{},eligible=Number(counts.recommended||0)+Number(counts.stretch||0);
  byId('recommendedScope').textContent='Recommended ('+eligible+')';byId('reviewScope').textContent='Needs verification ('+Number(counts.review||0)+')';
  for(const [id,mode]of [['recommendedScope','recommended'],['reviewScope','review']]){byId(id).classList.toggle('active',scope===mode);byId(id).setAttribute('aria-pressed',String(scope===mode));}
  byId('resultsPolicy').textContent=typeof data.policy==='string'?data.policy:'Recommendations require Pega in a checked description and a stated experience requirement below 8 years. Your experience: 4 years.';
  byId('scopeSummary').textContent=scope==='review'?'These saved leads need a checked description or experience requirement before they can be recommended.':'Pega roles for your 4 years of experience. Roles asking for 5–7 years are marked as a stretch.';
  byId('scanScreen').classList.add('hide');byId('resultScreen').classList.add('show');history.replaceState(null,'','#results');if(!preserveCompany)selectedCompany=null;applyFilter();
 }catch(e){if(requestNumber===resultsRequest)logError(e);}
}
function goBack(){
 byId('resultScreen').classList.remove('show');byId('scanScreen').classList.remove('hide');history.replaceState(null,'','#scan');
 if(!scanActive){byId('scanBtn').disabled=false;byId('scanBtn').textContent='Start scanning →';byId('progArea').classList.remove('show');byId('scanLog').classList.remove('show');}
}
function filteredCompanies(){
 const q=byId('filterInput').value.trim().toLowerCase();
 if(!q)return allResults;
 return allResults.map(c=>({...c,jobs:c.name.toLowerCase().includes(q)?c.jobs:c.jobs.filter(j=>[j.title,j.company,j.location].join(' ').toLowerCase().includes(q))})).filter(c=>c.jobs.length||c.name.toLowerCase().includes(q));
}
function renderSidebar(companies){
 const sb=byId('sidebar');sb.replaceChildren();
 const all=action('',showAll,'ci');put(all,node('span','','All jobs'),node('span','cnt',new Set(companies.flatMap(c=>c.jobs.map(j=>j.id))).size));sb.append(all);
 const withJobs=companies.filter(c=>c.jobs.length).sort((a,b)=>b.new_count-a.new_count||b.jobs.length-a.jobs.length),empty=companies.filter(c=>!c.jobs.length);
 sb.append(node('div','sh','With saved results ('+withJobs.length+')'));
 for(const c of withJobs){const b=action('',()=>showCompany(c.name),'ci'+(selectedCompany===c.name?' active':''));b.dataset.co=c.name;put(b,c.new_count?node('span','dot'):null,node('span','company-name',c.name),node('span','cnt'+(c.new_count?' new':''),c.new_count||c.jobs.length));sb.append(b);}
 if(empty.length){put(sb,node('div','divider'),node('div','sh','No saved matches ('+empty.length+')'));for(const c of empty)sb.append(action(c.name,()=>showCompany(c.name),'no-jobs'));}
}
function resumeScore(match){return Number.isFinite(match?.score)?Math.round(match.score)+'/100':'Not scored';}
function jobTable(jobs){
 const wrap=node('div','job-table-scroll');wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label','Job results table');
 const table=node('table','jtbl fade-in'),head=node('thead'),tr=node('tr');['','Title','Company','Location','Experience / resume match','Source','Description'].forEach(x=>tr.append(node('th','',x)));head.append(tr);table.append(head);const body=node('tbody');table.append(body);
 for(const j of jobs){
  const row=node('tr'),rec=j.recommendation||{},match=j.resume_match||{},source=String(j.source||'Source'),fit=node('td','job-fit');
  put(fit,node('div','experience-label',rec.experience_label||'Experience not verified'),node('div','match-label','Resume: '+resumeScore(match)));
  if(rec.status==='stretch')fit.append(node('div','stretch-label','Stretch for your 4 years'));
  if(rec.status==='review')fit.append(node('div','review-label','Needs verification'));
  const view=action('View description',event=>openJobDetail(j,event.currentTarget),'btn-job-detail');view.setAttribute('aria-label','View description and resume match for '+j.title);
  put(row,put(node('td'),j.is_new?node('span','new-dot'):null),put(node('td'),safeLink(j.title,j.url,'jl')),node('td','',j.company),node('td','',j.location),fit,put(node('td'),node('span','src-pill '+source.toLowerCase().replace(/[^a-z]/g,''),source),node('div','source-state',j.evidence_status||'Unverified')),put(node('td'),view));body.append(row);
 }
 wrap.append(table);return wrap;
}
function closeJobDialog(){byId('jobDialog').close();}
function detailStatus(text,isError=false){const status=byId('jobDialogStatus');status.textContent=text;status.classList.toggle('detail-error',isError);}
function detailList(title,items,missing=false){
 const section=node('section','detail-evidence');section.append(node('h3','',title));
 if(!Array.isArray(items)||!items.length){section.append(node('p','detail-muted',missing?'No additional gaps identified in the checked text.':'No supporting resume evidence identified.'));return section;}
 const list=node('ul');
 for(const item of items){
  const li=node('li'),label=typeof item==='string'?item:item.requirement||'Requirement';
  li.append(node('strong','',label));
  if(item.importance)li.append(node('span','requirement-importance',' · '+item.importance));
  if(item.evidence)li.append(node('p','resume-evidence',String(item.evidence)));
  if(item.jd_evidence)li.append(node('p','jd-evidence','Job asks: '+String(item.jd_evidence)));
  if(missing)li.append(node('p','detail-muted','Not evidenced in the saved resume.'));
  list.append(li);
 }
 section.append(list);return section;
}
function renderJobDetail(job){
 const content=byId('jobDialogContent'),rec=job.recommendation||{},match=job.resume_match||{};
 byId('jobDialogTitle').textContent=job.title||'Job description';content.replaceChildren();
 put(content,node('p','detail-company',[job.company,job.location].filter(Boolean).join(' · ')));
 const links=node('div','detail-links');
 if(job.url)links.append(safeLink('Open job posting ↗',job.url));
 links.append(safeLink('View your saved resume ↗','/library/resume'));content.append(links);
 const summary=node('section','detail-summary');
 put(summary,node('h3','','Experience and recommendation'),node('p','experience-label',rec.experience_label||'Experience requirement not verified'),node('p','detail-muted','Your experience: 4 years.'));
 if(rec.status==='stretch')summary.append(node('p','stretch-label',Number(rec.minimum_years)>4?'Stretch role: the stated experience requirement exceeds your 4 years.':'Stretch role: review the mandatory requirements and gaps below.'));
 if(Array.isArray(rec.reasons)&&rec.reasons.length){const list=node('ul');for(const reason of rec.reasons)list.append(node('li','',reason));summary.append(list);}content.append(summary);
 const scoreSection=node('section','detail-score');
 put(scoreSection,node('h3','','Resume evidence match'),node('p','detail-score-number',resumeScore(match)),node('p','',match.label||'A checked description and saved resume are needed to calculate a score.'),node('p','detail-muted',match.method||'Heuristic comparison of the description against your saved resume; this is not an ATS score or an interview probability.'));
 if(match.method&&!/not an ATS|not ATS/i.test(match.method))scoreSection.append(node('p','detail-muted','This is a heuristic match, not an ATS score or a probability of selection.'));
 const notes=Array.isArray(match.notes)?match.notes:match.notes?[match.notes]:[];
 if(notes.length){const method=node('details','score-method');method.append(node('summary','','How this score is calculated'));for(const note of notes)method.append(node('p','detail-muted',note));scoreSection.append(method);}
 if(match.resume_source)scoreSection.append(node('p','detail-muted','Resume used: '+String(match.resume_source)));
 content.append(scoreSection);
 let evidence=null;
 if(Number.isFinite(match.score)||(match.matched||[]).length||(match.missing||[]).length){
  evidence=node('div','detail-evidence-grid');put(evidence,detailList('Supported by your resume',match.matched),detailList('Gaps to review',match.missing,true));
  const gaps=(match.missing||[]).filter(item=>item.importance==='required').length;
  if(gaps)scoreSection.append(node('p','stretch-label',gaps+' required resume-evidence gap'+(gaps===1?'':'s')+' — review the comparison below.'));
 }
 const description=node('section','detail-description');description.append(node('h3','','Job description'));
 const text=typeof job.description_text==='string'?job.description_text.trim():'';
 if(!job.description_complete)description.append(node('p','review-label',text?'Only partial saved text is available. Refresh the description to check the role.':'A full description has not been retrieved. Refresh to check the public job page.'));
 const meta=node('div','description-meta');
 if(job.description_source_url)meta.append(safeLink('Description source ↗',job.description_source_url));
 meta.append(node('span','','Checked: '+(job.description_checked_at||'Not yet checked')));description.append(meta);
 if(text)description.append(node('div','job-description-text',text));else description.append(node('p','detail-muted','No saved description. No resume score is invented for an unread description.'));
 content.append(description);
 if(evidence){const comparison=node('details','score-method');comparison.append(node('summary','','Resume evidence and gaps'));comparison.append(evidence);content.append(comparison);}
}
async function openJobDetail(job,opener){
 const generation=++detailRequest,dialog=byId('jobDialog');detailJob=job;detailOpener=opener||document.activeElement;
 renderJobDetail(job);detailStatus('Loading saved description…');byId('refreshDescription').disabled=true;
 if(!dialog.open)dialog.showModal();byId('closeJobDetail').focus();byId('jobDialogContent').scrollTop=0;
 try{
  const result=await request('/api/opportunities/'+encodeURIComponent(job.id));
  if(generation!==detailRequest||!dialog.open)return;
  detailJob=result.opportunity;renderJobDetail(detailJob);detailStatus('Saved description loaded.');
 }catch(error){if(generation===detailRequest&&dialog.open)detailStatus('Could not load the saved description: '+error.message,true);}
 finally{if(generation===detailRequest)byId('refreshDescription').disabled=false;}
}
async function refreshJobDescription(){
 if(!detailJob||byId('refreshDescription').disabled)return;
 const id=detailJob.id,generation=detailRequest,button=byId('refreshDescription');button.disabled=true;button.textContent='Checking description…';detailStatus('Checking the public job page and updating your resume match…');
 try{
  const result=await request('/api/opportunities/'+encodeURIComponent(id)+'/description',{method:'POST',body:'{}'});
  if(generation!==detailRequest||!byId('jobDialog').open)return;
  detailJob=result.opportunity;renderJobDetail(detailJob);detailStatus(detailJob.description_complete&&detailJob.job_detail_status==='read'?'Description checked and resume match updated.':'The full description could not be verified. Available text and any earlier saved description are shown.');
  await switchToResults(resultScope,true);
 }catch(error){if(generation===detailRequest&&byId('jobDialog').open)detailStatus('Could not refresh the description: '+error.message,true);}
 finally{if(generation===detailRequest){button.disabled=false;button.textContent='Refresh description';}}
}
function queryLinks(c){
 const links=node('div','links'),q=encodeURIComponent(c.name+' Pega');for(const [text,url]of Object.entries({...c.links,LinkedIn:'https://www.linkedin.com/jobs/search/?keywords='+q,Google:'https://www.google.com/search?q='+q+'+jobs',Naukri:'https://www.naukri.com/pega-jobs?k='+q,Indeed:'https://in.indeed.com/jobs?q='+q}))links.append(safeLink(text+' ↗',url));return links;
}
function renderMain(companies){
 const mc=byId('mainContent');mc.replaceChildren();
 if(selectedCompany){
  const c=companies.find(c=>c.name===selectedCompany);if(!c){mc.append(node('div','empty-state','No results match this filter.'));return;}
  put(mc,put(node('div','mc-header fade-in'),node('h2','',c.name),queryLinks(c)));
  const issues=(c.checks||[]).filter(x=>['blocked','error','pending','partial'].includes(x.status));
  if(issues.length)mc.append(node('p','source-state','Check status: '+[...new Set(issues.map(x=>x.status))].join(', ')+'. Saved leads remain available.'));
  if(c.jobs.length)mc.append(jobTable(c.jobs));else mc.append(node('div','empty-state',resultScope==='review'?'No saved leads need verification for this company.':'No verified Pega matches for this company yet. Check Needs verification or the source links above.'));
 }else{
  const jobs=[...new Map(companies.flatMap(c=>c.jobs).map(j=>[j.id,j])).values()].sort((a,b)=>Number(b.is_new)-Number(a.is_new));
  put(mc,put(node('div','mc-header fade-in'),node('h2','',(resultScope==='review'?'Needs verification':'Recommended Pega jobs')+' ('+jobs.length+')')),jobs.length?jobTable(jobs):node('div','empty-state',resultScope==='review'?'No saved leads need verification in this selection.':'No verified Pega matches for this selection yet. Check Needs verification or run a new scan.'));
 }
}
function showCompany(name){selectedCompany=name;applyFilter();}
function showAll(){selectedCompany=null;applyFilter();}
function applyFilter(){const companies=filteredCompanies();renderSidebar(companies);renderMain(companies);}
function switchMainTab(tab){if(tab==='intel')location.href='/library/dossiers';else goBack();}
async function initializeScanner(){
 try{
  const [boot,options,status]=await Promise.all([request('/api/bootstrap'),request('/api/scan-options'),request('/api/status')]);
  csrf=boot.token;depthConfigs=options.categories;byId('scanTargetCount').textContent=options.total_targets+' company / region targets';renderDepth();
  if(status.running){scanActive=true;selectedMode=status.scan_mode||selectedMode;selectedCat=Object.keys(depthConfigs).find(c=>depthConfigs[c].some(m=>m.mode===selectedMode))||'gcc';renderDepth();byId('scanBtn').disabled=true;byId('scanBtn').textContent='Scanning…';byId('progArea').classList.add('show');byId('scanLog').classList.add('show');startPolling();await pollStatus();}
  else if(location.hash==='#results'||location.hash==='#opportunities')await switchToResults();
  if(status.scanner?.status==='interrupted')logError(Error(status.scanner.error));
  byId('savedResults').hidden=false;
 }catch(e){logError(e);byId('scanBtn').disabled=true;byId('scanBtn').textContent='Reload to reconnect';}
}
for(const t of document.querySelectorAll('.cat-tab[data-cat]'))t.addEventListener('click',()=>{if(scanActive)return;selectedCat=t.dataset.cat;selectedMode=null;renderDepth();});
byId('jobDialog').addEventListener('close',()=>{
 detailRequest++;detailJob=null;byId('refreshDescription').disabled=false;byId('refreshDescription').textContent='Refresh description';
 const target=detailOpener?.isConnected?detailOpener:byId(resultScope==='review'?'reviewScope':'recommendedScope');target?.focus();detailOpener=null;
});
initializeScanner();
