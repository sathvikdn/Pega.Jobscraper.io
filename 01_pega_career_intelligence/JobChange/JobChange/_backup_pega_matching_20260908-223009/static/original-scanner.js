'use strict';
let selectedCat='gcc',selectedMode='gcc_top10',pollTimer=null,allResults=[],selectedCompany=null,csrf='',depthConfigs={},pollBusy=false,scanActive=false;
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
async function switchToResults(){
 try{const data=await request('/api/scan-results');allResults=data.companies||[];
  byId('rNew').textContent=new Set(allResults.flatMap(c=>c.jobs.filter(j=>j.is_new).map(j=>j.id))).size;byId('rTotal').textContent=new Set(allResults.flatMap(c=>c.jobs.map(j=>j.id))).size;byId('rCo').textContent=allResults.filter(c=>c.jobs.length).length;
  byId('scanScreen').classList.add('hide');byId('resultScreen').classList.add('show');history.replaceState(null,'','#results');selectedCompany=null;applyFilter();
 }catch(e){logError(e);}
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
function jobTable(jobs){
 const table=node('table','jtbl fade-in'),head=node('thead'),tr=node('tr');['','Title','Company','Location','Source'].forEach(x=>tr.append(node('th','',x)));head.append(tr);table.append(head);const body=node('tbody');table.append(body);
 for(const j of jobs){const row=node('tr');put(row,put(node('td'),j.is_new?node('span','new-dot'):null),put(node('td'),safeLink(j.title,j.url,'jl')),node('td','',j.company),node('td','',j.location),put(node('td'),node('span','src-pill '+j.source.toLowerCase().replace(/[^a-z]/g,''),j.source),node('div','source-state',j.evidence_status||'Unverified')));body.append(row);}return table;
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
  if(c.jobs.length)mc.append(jobTable(c.jobs));else mc.append(node('div','empty-state','No saved matches for this company. Try the source links above.'));
 }else{
  const jobs=[...new Map(companies.flatMap(c=>c.jobs).map(j=>[j.id,j])).values()].sort((a,b)=>Number(b.is_new)-Number(a.is_new));
  put(mc,put(node('div','mc-header fade-in'),node('h2','','All jobs ('+jobs.length+')')),jobs.length?jobTable(jobs):node('div','empty-state','No saved matches. Use New scan to choose another category or depth.'));
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
initializeScanner();
