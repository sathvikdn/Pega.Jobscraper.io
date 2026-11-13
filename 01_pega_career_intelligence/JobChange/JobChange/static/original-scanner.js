'use strict';
let selectedCat='gcc',selectedMode='gcc_top10',pollTimer=null,allResults=[],selectedCompany=null,csrf='',depthConfigs={},pollBusy=false,scanActive=false,resultScope='all',resultsRequest=0,detailRequest=0,detailJob=null,detailOpener=null,lastResultsRefresh=0,filterCategory='all',filterLocation='all';
const byId=id=>document.getElementById(id);
function node(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=String(text);return e;}
function put(parent,...children){for(const c of children.flat())if(c)parent.append(c);return parent;}
function action(text,fn,cls){const b=node('button',cls,text);b.type='button';b.addEventListener('click',fn);return b;}
function safeLink(text,url,cls){const a=node('a',cls,text);try{const u=new URL(url,location.origin);if(!['http:','https:'].includes(u.protocol))return node('span',cls,text);a.href=u.href;a.target='_blank';a.rel='noopener noreferrer';}catch{return node('span',cls,text);}return a;}
async function request(path,options={}){const r=await fetch(path,{...options,headers:{'Content-Type':'application/json','X-Career-Token':csrf,...options.headers}});const data=await r.json();if(!r.ok)throw Error(data.error||'Request failed');return data;}
function logError(error){const notice=byId('scanNotice');notice.hidden=false;notice.textContent=String(error.message??error);}
function renderDepth(){
 const cfg=depthConfigs[selectedCat]||[],row=byId('depthRow');row.replaceChildren();
 if(!cfg.some(d=>d.mode===selectedMode))selectedMode=cfg[0]?.mode;
 for(const d of cfg){const label=d.label+(d.label==='Top 10'&&d.count===10||d.label==='Top 20'&&d.count===20?'':' ('+d.count+')');const b=action(label,()=>{if(scanActive)return;selectedMode=d.mode;renderDepth();},'dp'+(d.mode===selectedMode?' active':''));b.disabled=scanActive||!d.count;b.dataset.mode=d.mode;b.setAttribute('aria-pressed',String(d.mode===selectedMode));row.append(b);}
 for(const t of document.querySelectorAll('.cat-tab[data-cat]')){t.classList.toggle('active',t.dataset.cat===selectedCat);t.disabled=scanActive;t.setAttribute('aria-pressed',String(t.dataset.cat===selectedCat));}
}
async function startScan(){
 if(scanActive)return;
 const choice=(depthConfigs[selectedCat]||[]).find(d=>d.mode===selectedMode);if(!choice?.count){logError(Error('Choose a category and depth first.'));return;}
 scanActive=true;byId('scanBtn').disabled=true;byId('scanBtn').textContent='Scanning…';showStopButtons(true);renderDepth();
 byId('progArea').classList.add('show');byId('scanNotice').hidden=true;byId('scanNotice').textContent='';byId('progTxt').textContent='Starting job search…';byId('progFill').style.width='0%';
 try{await request('/api/scan',{method:'POST',body:JSON.stringify({mode:selectedMode})});startPolling();await pollStatus();}
 catch(e){scanActive=false;byId('scanBtn').disabled=false;byId('scanBtn').textContent='Start scanning →';showStopButtons(false);renderDepth();logError(e);}
}
async function stopScan(){
 const stopBtn=byId('stopBtn'),stopBtnR=byId('stopBtnResults');
 if(stopBtn)stopBtn.disabled=true;if(stopBtnR)stopBtnR.disabled=true;
 try{
  await request('/api/search/pause',{method:'POST',body:'{}'});
  if(stopBtn)stopBtn.textContent='Stopping\u2026';if(stopBtnR)stopBtnR.textContent='Stopping\u2026';
 }catch(e){logError(Error('Could not stop the scan: '+e.message));if(stopBtn)stopBtn.disabled=false;if(stopBtnR)stopBtnR.disabled=false;}
}
function showStopButtons(show){
 const stopBtn=byId('stopBtn'),stopBtnR=byId('stopBtnResults');
 if(stopBtn){stopBtn.classList.toggle('show',show);stopBtn.disabled=false;stopBtn.textContent='Stop scan';}
 if(stopBtnR){stopBtnR.hidden=!show;stopBtnR.disabled=false;stopBtnR.textContent='Stop scan';}
}
function renderPlatformStats(parallel,status){
 const s=status||{};
 const phase=s.phase||'';
 const running=s.running;
 const platforms=(parallel||{}).requests?.platforms||{};

 // Pipeline steps definition
 const steps=[
  {id:'linkedin_http',label:'LinkedIn (HTTP API)',phase:'parallel_scan',icon:'LI'},
  {id:'linkedin_retry',label:'LinkedIn (Playwright retry)',phase:'linkedin_retry',icon:'LI+'},
  {id:'career_portals',label:'Selected India employer portals',phase:'career_portals',icon:'CP'},
  {id:'indeed_india',label:'Indeed India',phase:'job_boards',icon:'IN'},
  {id:'shine',label:'Shine.com',phase:'job_boards',icon:'SH'},
  {id:'glassdoor',label:'Glassdoor',phase:'job_boards',icon:'GD'},
  {id:'simplyhired',label:'SimplyHired',phase:'job_boards',icon:'SH'},
 ];
 const phaseOrder=['parallel_scan','linkedin_retry','career_portals','job_boards'];
 const currentIdx=phaseOrder.indexOf(phase);

 for(const id of ['platformStats','platformStatsResults']){
  const el=byId(id);if(!el)continue;
  el.classList.add('show');
 }
 for(const gridId of ['platformGrid','platformGridResults']){
  const grid=byId(gridId);if(!grid)continue;grid.replaceChildren();

  // Pipeline tracker
  const pipeline=node('div','');
  pipeline.style.cssText='margin-bottom:10px;border-bottom:1px solid #1e1e21;padding-bottom:8px';
  const pTitle=node('div','platform-stats-title','SCAN PIPELINE');
  pipeline.append(pTitle);

  for(const step of steps){
   const stepPhaseIdx=phaseOrder.indexOf(step.phase);
   let stepState='waiting';
   const metricKey=step.phase==='parallel_scan'?'LinkedIn':step.phase==='linkedin_retry'?'LinkedIn (retry)':step.phase==='career_portals'?'Career Portals':step.label;
   const metric=platforms[metricKey];
   if(running&&phase===step.phase&&(phase!=='job_boards'||s.current_company===step.label))stepState='active';
   else if(metric&&(metric.pages||metric.skipped))stepState=metric.error&&!metric.ok?'failed':'done';

   const row=node('div','pipeline-step');
   row.append(node('span','pipeline-dot '+stepState));
   row.append(node('span','pipeline-label'+(stepState==='active'?' active':''),step.label));

   // Add progress for active step
   if(stepState==='active'&&s.progress!==undefined){
    row.append(node('span','pipeline-progress',s.progress+'/'+s.total));
   }else if(stepState==='done'){
    const p=platforms[step.label]||platforms[step.id];
    if(p) row.append(node('span','pipeline-progress p-ok',p.ok+' ok'));
   }
   pipeline.append(row);
  }
  grid.append(pipeline);

  // Platform cards (existing data)
  const cardTitle=node('div','platform-stats-title','PAGES SCRAPED');
  cardTitle.style.marginTop='8px';
  grid.append(cardTitle);

  const cardGrid=node('div','platform-grid');
  const order=['LinkedIn','LinkedIn (retry)','Career Portals','Indeed India','Indeed US','Shine.com','Dice','Glassdoor','SimplyHired','Employer'];
  const sorted=order.filter(p=>platforms[p]).concat(Object.keys(platforms).filter(p=>!order.includes(p)));
  for(const name of sorted){
   const p=platforms[name],card=node('div','platform-card');
   const stepPhase=name.includes('retry')?'linkedin_retry':name==='Career Portals'?'career_portals':['Indeed India','Indeed US','Shine.com','Dice','Glassdoor','SimplyHired'].includes(name)?'job_boards':'parallel_scan';
   const stepIdx=phaseOrder.indexOf(stepPhase);
   if(running){card.classList.add(phase===stepPhase?'active':stepIdx<currentIdx?'done':'waiting');}
   card.append(node('div','platform-name',name));
   card.append(node('div','platform-pages'+(p.ok&&!p.blocked?' green':''),String(p.pages)));
   const detail=node('div','platform-detail');
   if(p.ok)put(detail,node('span','p-ok',p.ok+' ok'));
   if(p.ok&&(p.blocked||p.error))detail.append(document.createTextNode(' · '));
   if(p.blocked)put(detail,node('span','p-block',p.blocked+' blocked'));
   if(p.blocked&&p.error)detail.append(document.createTextNode(' · '));
   if(p.error)put(detail,node('span','p-err',p.error+' err'));
   if(p.unverified)put(detail,node('span','p-wait',' · '+p.unverified+' unverified'));
   if(!p.ok&&!p.blocked&&!p.error&&!p.unverified)put(detail,node('span','p-wait','waiting...'));
   card.append(detail);cardGrid.append(card);
  }
  grid.append(cardGrid);
 }
}
function startPolling(){if(pollTimer)clearInterval(pollTimer);pollTimer=setInterval(pollStatus,1500);}
async function pollStatus(){
 if(pollBusy)return;pollBusy=true;
 try{
  const s=await request('/api/status'),pct=s.total?Math.min(100,Math.round(s.progress/s.total*100)):0;
  byId('progFill').style.width=pct+'%';
  const parallel=s.parallel||{},paused=['paused','interrupted'].includes(s.scanner?.status);

  const phase=s.phase||'';
  const progressText=phase==='parallel_scan'?'Companies '+s.progress+'/'+s.total+' · Descriptions '+(s.description_progress||0)+'/'+(s.description_total||0)+' · In progress: '+(parallel.discovery_active||0)+' company searches + '+(parallel.descriptions_active||0)+' descriptions':phase==='linkedin_retry'?'LinkedIn Playwright retry '+s.progress+'/'+s.total+' · '+(s.current_company||''):phase==='career_portals'?'Career portals '+s.progress+'/'+s.total+' · '+(s.current_company||''):phase==='job_boards'?'Job boards · '+(s.current_company||'scanning...'):(phase==='job_details'?'Checking job descriptions':'Scanning '+(s.current_company||'selected companies'))+' ('+s.progress+'/'+s.total+')';
  const incomplete=Boolean(s.coverage?.incomplete)||Object.values(parallel.requests?.platforms??{}).some(source=>source.blocked>0||source.skipped>0||source.error>0||source.unverified>0);
  byId('progTxt').textContent=s.running?progressText:paused?'Scan paused — completed results saved':s.error?'Scan stopped — saved results retained':incomplete?'Search finished with incomplete coverage — saved results available.':'Search finished — saved results available.';
  const liveStatus=byId('liveResultsStatus');if(liveStatus){liveStatus.hidden=!s.running&&!incomplete;liveStatus.textContent=s.running?progressText+' · Results update as descriptions are checked.':incomplete?'Some company searches could not be verified. Saved results remain available.':'';}
  if(s.error)logError(Error(s.error));
  if(!s.running&&s.scanner?.status==='interrupted')logError(Error(s.scanner.error||'Previous scan interrupted; completed results saved.'));
  if(!s.running){clearInterval(pollTimer);pollTimer=null;scanActive=false;byId('scanBtn').disabled=false;byId('scanBtn').textContent='Start scanning →';showStopButtons(false);renderDepth();if(s.error)logError(Error(s.error));else{for(const id of ['platformStatsResults'])byId(id)?.classList.remove('show');}await switchToResults();}
  else if(byId('resultScreen').classList.contains('show')&&Date.now()-lastResultsRefresh>=5000)await switchToResults(resultScope,true,true);
 }catch(e){logError(Error('Connection interrupted. Retrying while the scan continues. '+e.message));}finally{pollBusy=false;}
}
async function switchToResults(scope=resultScope,preserveCompany=false,background=false){
 const requestNumber=++resultsRequest;
 try{
  const data=await request('/api/scan-results'+(scope!=='all'?'?scope='+scope:''));
  if(requestNumber!==resultsRequest)return;
  if(background&&!byId('resultScreen').classList.contains('show'))return;
  lastResultsRefresh=Date.now();
  resultScope=scope;allResults=data.companies||[];
  buildLocationChips();updateCategoryCounts();
  byId('rNew').textContent=new Set(allResults.flatMap(c=>c.jobs.filter(j=>j.is_new).map(j=>j.id))).size;byId('rTotal').textContent=new Set(allResults.flatMap(c=>c.jobs.map(j=>j.id))).size;byId('rCo').textContent=allResults.filter(c=>c.jobs.length).length;
  const counts=data.policy_counts||{},eligible=Number(counts.recommended||0)+Number(counts.stretch||0);
  const allCount=new Set(allResults.flatMap(c=>c.jobs.map(j=>j.id))).size;
  byId('allScope').textContent='All jobs ('+allCount+')';byId('recommendedScope').textContent='Recommended ('+eligible+')';byId('reviewScope').textContent='Needs verification ('+Number(counts.review||0)+')';
  for(const [id,mode]of [['allScope','all'],['recommendedScope','recommended'],['reviewScope','review']]){byId(id).classList.toggle('active',scope===mode);byId(id).setAttribute('aria-pressed',String(scope===mode));}
  byId('resultsPolicy').textContent=typeof data.policy==='string'?data.policy:'Recommendations require Pega in a checked description and a stated experience requirement below 8 years. Your experience: 4 years.';
  byId('scopeSummary').textContent=scope==='review'?'These saved leads need a checked description or experience requirement before they can be recommended.':'Pega roles for your 4 years of experience. Roles asking for 5–7 years are marked as a stretch.';
  byId('scanScreen').classList.add('hide');byId('resultScreen').classList.add('show');history.replaceState(null,'','#results');if(!preserveCompany)selectedCompany=null;applyFilter();
 }catch(e){if(requestNumber===resultsRequest)logError(e);}
}
function goBack(){
 byId('resultScreen').classList.remove('show');byId('scanScreen').classList.remove('hide');history.replaceState(null,'','#scan');
 filterCategory='all';filterLocation='all';filterSource='all';
 if(!scanActive){byId('scanBtn').disabled=false;byId('scanBtn').textContent='Start scanning →';byId('progArea').classList.remove('show');byId('scanNotice').hidden=true;}
}
function classifyLocation(loc){
 if(!loc||/unknown|unconfirmed|not specified/i.test(loc))return 'unknown';
 const l=loc.toLowerCase();
 if(/\bbengaluru\b|\bbangalore\b/.test(l))return 'bengaluru';
 if(/\bremote\b/.test(l))return 'remote';
 if(/\bindia\b|\bhyderabad\b|\bchennai\b|\bmumbai\b|\bpune\b|\bdelhi\b|\bgurgaon\b|\bgurugram\b|\bnoida\b|\bkolkata\b|\bjaipur\b|\bkochi\b|\bthiruvananthapuram\b|\bcoimbatore\b/.test(l))return 'other_india';
 return 'international';
}
function setCategoryFilter(cat){
 filterCategory=cat;
 for(const btn of document.querySelectorAll('#filterBar [data-category]')){btn.classList.toggle('active',btn.dataset.category===cat);btn.setAttribute('aria-pressed',String(btn.dataset.category===cat));}
 selectedCompany=null;applyFilter();
}
function setLocationFilter(loc){
 filterLocation=loc;
 for(const btn of document.querySelectorAll('#locationFilterGroup [data-location]')){btn.classList.toggle('active',btn.dataset.location===loc);btn.setAttribute('aria-pressed',String(btn.dataset.location===loc));}
 selectedCompany=null;applyFilter();
}
let filterSource='all';
function _allJobs(){return [...new Map(allResults.flatMap(company=>company.jobs.map(job=>({...job,_group:company.name,_cat:['gcc','product'].includes(job.category??company.category)?'gcc':(job.category??company.category)==='services'?'services':'unknown'}))).map(job=>[job.id,job])).values()];}
function matchesJobFilters(job,skip){
 const query=byId('filterInput').value.trim().toLowerCase();
 return (skip==='cat'||filterCategory==='all'||job._cat===filterCategory)
  &&(skip==='loc'||filterLocation==='all'||classifyLocation(job.location)===filterLocation)
  &&(skip==='source'||filterSource==='all'||job.source===filterSource||(job.sources??[]).some(source=>source.source===filterSource))
  &&(!query||[job.title,job.company,job.location,job._group].join(' ').toLowerCase().includes(query));
}
function renderSourceFilters(jobs){
 const group=byId('sourceFilterGroup');if(!group)return;
 group.replaceChildren(node('span','filter-label','Source'));
 const sources=['all',...new Set(jobs.flatMap(job=>[job.source,...(job.sources??[]).map(source=>source.source)]).filter(Boolean))];
 for(const source of sources){
  const count=jobs.filter(job=>matchesJobFilters(job,'source')&&(source==='all'||job.source===source||(job.sources??[]).some(item=>item.source===source))).length;
  const button=action((source==='all'?'All':source)+' ('+count+')',()=>{filterSource=source;selectedCompany=null;applyFilter();},'filter-chip'+(source===filterSource?' active':''));
  button.setAttribute('aria-pressed',String(source===filterSource));group.append(button);
 }
}
function buildLocationChips(){
 const group=byId('locationFilterGroup');if(!group)return;
 const labels={all:'All',bengaluru:'Bengaluru',other_india:'Other India',unknown:'Location unconfirmed'};
 // Build chips once; counts update dynamically via updateFilterCounts
 const existing=group.querySelectorAll('[data-location]');
 if(existing.length)return; // already built
 const lbl=group.querySelector('.filter-label');group.replaceChildren();if(lbl)group.append(lbl);
 for(const[key,text]of Object.entries(labels)){
  const btn=document.createElement('button');btn.className='filter-chip'+(filterLocation===key?' active':'');btn.dataset.location=key;
  btn.setAttribute('aria-pressed',String(filterLocation===key));
  btn.innerHTML=text+'<span class="chip-count"></span>';
  btn.addEventListener('click',()=>setLocationFilter(key));group.append(btn);
 }
}
function updateFilterCounts(){
 // Count per dimension, considering the OTHER active filters (cross-filtering)
 const jobs=_allJobs();
 const q=byId('filterInput').value.trim().toLowerCase();
 const matches=matchesJobFilters;
 renderSourceFilters(jobs);
 // Location counts (apply cat filter but not loc filter)
 const locCounts={all:0,bengaluru:0,remote:0,other_india:0,international:0,unknown:0};
 for(const j of jobs){if(!matches(j,'loc')){continue;}const b=classifyLocation(j.location);locCounts[b]++;locCounts.all++;}
 for(const btn of document.querySelectorAll('#locationFilterGroup [data-location]')){const k=btn.dataset.location;const s=btn.querySelector('.chip-count');if(s)s.textContent='('+locCounts[k]+')';}
 // Category counts (apply loc filter but not cat filter)
 const catCounts={all:0,gcc:0,services:0,global:0,unknown:0};
 for(const j of jobs){if(!matches(j,'cat')){continue;}if(catCounts[j._cat]!==undefined)catCounts[j._cat]++;catCounts.all++;}
 for(const btn of document.querySelectorAll('#filterBar [data-category]')){const k=btn.dataset.category;const s=btn.querySelector('.chip-count');const label={all:'All',gcc:'GCC / Product',services:'Consulting / SI',global:'Remote / Global'}[k]||k;
  if(s)s.textContent='('+catCounts[k]+')';else btn.innerHTML=label+'<span class="chip-count">('+catCounts[k]+')</span>';}
 // Update top stats + scope tab to match the filtered view
 const visible=jobs.filter(j=>matches(j,null));
 const visibleCount=new Set(visible.map(j=>j.id)).size;
 byId('rTotal').textContent=visibleCount;
 byId('rCo').textContent=new Set(visible.map(j=>j.company)).size;
 byId('rNew').textContent=new Set(visible.filter(j=>j.is_new).map(j=>j.id)).size;
 const allTab=byId('allScope');if(allTab)allTab.textContent='All jobs ('+visibleCount+')';
}
function updateCategoryCounts(){updateFilterCounts();}
function filteredCompanies(){
 // Apply category filter
 // Apply location filter
 // Apply text search
 const visible=new Set(_allJobs().filter(job=>matchesJobFilters(job,null)).map(job=>job.id));
 return allResults.map(company=>{
  const jobs=company.jobs.filter(job=>visible.has(job.id));
  return {...company,jobs,new_count:jobs.filter(job=>job.is_new).length};
 }).filter(company=>company.jobs.length);
}
function renderSidebar(companies){
 const sb=byId('sidebar');sb.replaceChildren();
 const all=action('',showAll,'ci');put(all,node('span','','All jobs'),node('span','cnt',new Set(companies.flatMap(c=>c.jobs.map(j=>j.id))).size));sb.append(all);
 const withJobs=companies.filter(c=>c.jobs.length).sort((a,b)=>b.new_count-a.new_count||b.jobs.length-a.jobs.length),empty=companies.filter(c=>!c.jobs.length);
 sb.append(node('div','sh','With saved results ('+withJobs.length+')'));
 for(const c of withJobs){const b=action('',()=>showCompany(c.name),'ci'+(selectedCompany===c.name?' active':''));b.dataset.co=c.name;put(b,c.new_count?node('span','dot'):null,node('span','company-name',c.name),node('span','cnt'+(c.new_count?' new':''),c.new_count||c.jobs.length));sb.append(b);}
 if(empty.length){put(sb,node('div','divider'),node('div','sh','No saved matches ('+empty.length+')'));for(const c of empty)sb.append(action(c.name,()=>showCompany(c.name),'no-jobs'));}
}
const applicationStages=JobWorkspace.stages;
function stageLabel(stage){return (applicationStages.find(([value])=>value===stage)||[])[1]||'Not reviewed';}
function resumeScore(match){return Number.isFinite(match?.score)?Math.round(match.score)+'/100':'Not scored';}
function updateCachedPipeline(job,payload){
 for(const company of allResults){
  for(const item of company.jobs||[]){
   if(item.id===job.id||item.url===job.url)item.pipeline=payload;
  }
 }
 if(detailJob&&(detailJob.id===job.id||detailJob.url===job.url))detailJob.pipeline=payload;
}
async function saveApplicationFromRow(job,stage,notes,control,feedback){
 control.disabled=true;
 feedback.classList.remove('error');feedback.textContent='Saving…';
 try{
  const payload=await request('/api/pipeline/'+encodeURIComponent(job.id),{method:'POST',body:JSON.stringify({stage,notes})});
  updateCachedPipeline(job,payload);applyFilter();
 }catch(error){
  control.value=job.pipeline?.stage||'unreviewed';
  feedback.classList.add('error');feedback.textContent='Not saved: '+error.message;
 }finally{if(control.isConnected)control.disabled=false;}
}
function jobTable(jobs){
 return JobWorkspace.table(jobs,openJobDetail,null,saveApplicationFromRow);
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
function renderApplicationTracker(job){
 const pipeline=job.pipeline||{stage:'unreviewed',notes:''},section=node('section','application-tracker');
 section.append(node('h3','','Your application'));
 section.append(node('p','detail-muted','Changing status saves immediately. Use Save changes to keep notes for this job.'));
 const controls=node('div','application-tracker-controls'),stageField=node('label','application-field','Status'),notesLabel=node('label','','Notes / next step');
 const stageSelect=JobWorkspace.statusSelect(pipeline.stage||'unreviewed','Application status');stageSelect.id='applicationStage';
 const selectWrap=node('span','application-select-wrap');selectWrap.append(stageSelect);stageField.append(selectWrap);
 stageSelect.addEventListener('change',()=>saveApplicationStatus());
 const notes=document.createElement('textarea');notes.id='applicationNotes';notes.maxLength=4000;notes.placeholder='Referral, resume version, interview round, or follow-up date…';notes.value=pipeline.notes||'';
 notesLabel.append(notes);controls.append(stageField,notesLabel);section.append(controls);
 const actions=node('div','application-actions'),save=action('Save changes',()=>saveApplicationStatus(),'btn-job-detail application-save'),updated=node('span','application-updated',pipeline.updated_at?'Last saved: '+pipeline.updated_at:'No status saved yet');
 save.id='saveApplication';updated.id='applicationUpdated';actions.append(save,updated);section.append(actions);return section;
}
function renderJobDetail(job){
 const content=byId('jobDialogContent'),rec=job.recommendation||{},match=job.resume_match||{};
 byId('jobDialogTitle').textContent=job.title||'Job description';content.replaceChildren();
 put(content,node('p','detail-company',[job.company,job.location].filter(Boolean).join(' · ')));
 const links=node('div','detail-links');
 if(job.url)links.append(safeLink('Open job posting ↗',job.url));
 links.append(safeLink('View your saved resume ↗','/library/resume'));content.append(links);
 content.append(renderApplicationTracker(job));
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
async function saveApplicationStatus(){
 if(!detailJob)return;
 const job=detailJob,generation=detailRequest,stageSelect=byId('applicationStage'),stage=stageSelect?.value||'unreviewed',notes=byId('applicationNotes')?.value||'';
 const button=byId('saveApplication');if(button)button.disabled=true;if(stageSelect)stageSelect.disabled=true;
 detailStatus('Saving application status…');
 try{
  const payload=await request('/api/pipeline/'+encodeURIComponent(job.id),{method:'POST',body:JSON.stringify({stage,notes})});
  updateCachedPipeline(job,payload);applyFilter();
  if(generation===detailRequest&&detailJob?.id===job.id&&byId('jobDialog').open){
   detailJob.pipeline=payload;const updated=byId('applicationUpdated');if(updated)updated.textContent='Last saved: '+(payload.updated_at||'just now');
   detailStatus('Saved for this job: '+stageLabel(payload.stage)+'.');
  }
 }catch(error){if(generation===detailRequest&&byId('jobDialog').open){if(stageSelect?.isConnected)stageSelect.value=job.pipeline?.stage||'unreviewed';detailStatus('Could not save: '+error.message,true);}}
 finally{if(button?.isConnected)button.disabled=false;if(stageSelect?.isConnected)stageSelect.disabled=false;}
}
async function openJobDetail(job,opener){
 const generation=++detailRequest,dialog=byId('jobDialog');detailJob=job;detailOpener=opener||document.activeElement;
 byId('jobDialogTitle').textContent=job.title||'Job description';byId('jobDialogContent').replaceChildren(node('p','detail-muted','Loading job details and saved application status…'));
 detailStatus('Loading saved description…');byId('refreshDescription').disabled=true;
 if(!dialog.open)dialog.showModal();byId('closeJobDetail').focus();byId('jobDialogContent').scrollTop=0;
 try{
  const result=await request('/api/opportunities/'+encodeURIComponent(job.id));
  if(generation!==detailRequest||!dialog.open)return;
  detailJob=result.opportunity;renderJobDetail(detailJob);detailStatus('Saved description loaded.');
 }catch(error){if(generation===detailRequest&&dialog.open){renderJobDetail(job);detailStatus('Could not load the saved description: '+error.message,true);}}
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
  if((c.checks||[]).some(x=>x.partial))mc.append(node('p','source-state','Search coverage is partial: some result pages or descriptions could not be checked. No saved match does not mean the company has no openings.'));
  if(c.jobs.length)mc.append(jobTable(c.jobs));else mc.append(node('div','empty-state',resultScope==='review'?'No saved leads need verification for this company.':'No verified Pega matches for this company yet. Check Needs verification or the source links above.'));
 }else{
  const jobs=[...new Map(companies.flatMap(c=>c.jobs).map(j=>[j.id,j])).values()].sort((a,b)=>Number(b.is_new)-Number(a.is_new));
  put(mc,put(node('div','mc-header fade-in'),node('h2','',(resultScope==='review'?'Needs verification':'Recommended Pega jobs')+' ('+jobs.length+')')),jobs.length?jobTable(jobs):node('div','empty-state',resultScope==='review'?'No saved leads need verification in this selection.':'No verified Pega matches for this selection yet. Check Needs verification or run a new scan.'));
 }
}
function showCompany(name){selectedCompany=name;applyFilter();}
function showAll(){selectedCompany=null;applyFilter();}
function applyFilter(){const companies=filteredCompanies();renderSidebar(companies);renderMain(companies);updateFilterCounts();}
function switchMainTab(){goBack();}
async function initializeScanner(){
 try{
  const [boot,options,status]=await Promise.all([request('/api/bootstrap'),request('/api/scan-options'),request('/api/status')]);
  csrf=boot.token;depthConfigs=options.categories;byId('scanTargetCount').textContent=options.total_targets+' company / region targets';renderDepth();
  if(status.running){scanActive=true;selectedMode=status.scan_mode||selectedMode;selectedCat=Object.keys(depthConfigs).find(c=>depthConfigs[c].some(m=>m.mode===selectedMode))||'gcc';renderDepth();byId('scanBtn').disabled=true;byId('scanBtn').textContent='Scanning…';showStopButtons(true);byId('progArea').classList.add('show');byId('scanNotice').hidden=true;startPolling();await pollStatus();}
  else if(location.hash==='#results'||location.hash==='#opportunities')await switchToResults();
  if(status.scanner?.status==='interrupted')logError(Error(status.scanner.error));
  if(!status.running&&status.coverage?.incomplete){const notice=byId('liveResultsStatus');notice.hidden=false;notice.textContent='Latest search has coverage gaps. Earlier saved leads may not have been freshly verified.';}
  byId('savedResults').hidden=false;
 }catch(e){logError(e);byId('scanBtn').disabled=true;byId('scanBtn').textContent='Reload to reconnect';}
}
for(const t of document.querySelectorAll('.cat-tab[data-cat]'))t.addEventListener('click',()=>{if(scanActive)return;selectedCat=t.dataset.cat;selectedMode=null;renderDepth();});
byId('jobDialog').addEventListener('close',()=>{
 detailRequest++;detailJob=null;byId('refreshDescription').disabled=false;byId('refreshDescription').textContent='Refresh description';
 const target=detailOpener?.isConnected?detailOpener:byId(resultScope==='review'?'reviewScope':'recommendedScope');target?.focus();detailOpener=null;
});
initializeScanner();
