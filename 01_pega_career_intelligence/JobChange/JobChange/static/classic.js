'use strict';
// These views preserve the original hub, dossier and scanner navigation.
// All company/work/person content comes from the current evidence APIs.
const C={category:'all',place:'all',mode:'dashboard',company:null,query:'',sector:'all',sort:'evidence',hubQuery:'',novelty:'all'};
const CLASSIC_SECTORS={"JPMorgan Chase": "Banking & financial services", "Wells Fargo": "Banking & financial services", "HSBC": "Banking & financial services", "Citibank": "Banking & financial services", "Bank of America": "Banking & financial services", "Goldman Sachs": "Banking & financial services", "Barclays": "Banking & financial services", "Deutsche Bank": "Banking & financial services", "Standard Chartered": "Banking & financial services", "American Express": "Banking & financial services", "Morgan Stanley": "Banking & financial services", "NatWest Group": "Banking & financial services", "Lloyds Banking Group": "Banking & financial services", "BNP Paribas": "Banking & financial services", "Societe Generale": "Banking & financial services", "ANZ Bank": "Banking & financial services", "MUFG": "Banking & financial services", "BNY Mellon": "Banking & financial services", "Allianz Technology": "Insurance & healthcare", "Aflac": "Insurance & healthcare", "Sun Life": "Insurance & healthcare", "Ameriprise Financial": "Banking & financial services", "Empower": "Banking & financial services", "Charles Schwab": "Banking & financial services", "Mastercard": "Banking & financial services", "Visa": "Banking & financial services", "PayPal": "Banking & financial services", "FIS (TSYS/Global Payments)": "Banking & financial services", "Broadridge": "Banking & financial services", "Optum / UnitedHealth Group": "Insurance & healthcare", "Elevance Health (Anthem)": "Insurance & healthcare", "Evernorth / Cigna": "Insurance & healthcare", "Verizon": "Telecom & consumer", "Vodafone / VOIS": "Telecom & consumer", "BT Group": "Telecom & consumer", "Telstra": "Telecom & consumer", "Amdocs": "Telecom & consumer", "Ford Motor Company": "Automotive & industrial", "Stellantis": "Automotive & industrial", "Siemens": "Automotive & industrial", "S&P Global": "Banking & financial services", "Conduent": "Logistics, energy & services", "DHL": "Logistics, energy & services", "Dell Technologies": "Technology", "Kotak Mahindra Bank": "Banking & financial services", "ICICI Bank": "Banking & financial services", "Synchrony Financial": "Banking & financial services", "Bosch": "Automotive & industrial", "The Hartford India": "Insurance & healthcare", "Rabobank": "Banking & financial services", "Commonwealth Bank": "Banking & financial services", "NAB (National Australia Bank)": "Banking & financial services", "UBS India": "Banking & financial services", "MetLife India GCC": "Insurance & healthcare", "AXA India": "Insurance & healthcare", "Roche India": "Insurance & healthcare", "GE HealthCare India": "Insurance & healthcare", "Pfizer India": "Insurance & healthcare", "Novartis India": "Insurance & healthcare", "John Deere India (JDTCI)": "Automotive & industrial", "First Citizens India": "Banking & financial services", "Booking Holdings India": "Technology", "Cisco India": "Technology", "Nokia India": "Telecom & consumer", "Orange Business India": "Telecom & consumer", "Maersk GSC India": "Logistics, energy & services", "Shell India": "Logistics, energy & services", "Nike India": "Telecom & consumer", "Unilever India (Digital Hub)": "Telecom & consumer", "Mercedes-Benz R&D India (MBRDI)": "Automotive & industrial", "Daimler Truck India": "Automotive & industrial", "Renault-Nissan Tech India": "Automotive & industrial", "Cummins India": "Automotive & industrial", "IFFCO Tokio General Insurance": "Insurance & healthcare", "Global Payments India": "Banking & financial services", "Pegasystems India": "Technology", "Fidelity National Financial India (FNF)": "Insurance & healthcare", "Proximus India": "Telecom & consumer", "Mondelez India": "Telecom & consumer", "enGen / Highmark India": "Insurance & healthcare", "Marsh McLennan India (MMGS)": "Insurance & healthcare", "PepsiCo India": "Telecom & consumer", "Capital One India": "Banking & financial services", "Mizuho Global Services India (MGS)": "Banking & financial services", "Carelon Global Solutions India": "Insurance & healthcare", "MUFG Pension & Market Services (Link Group)": "Banking & financial services", "Intel India": "Technology", "Levi Strauss & Co. India": "Telecom & consumer", "ITC Limited": "Telecom & consumer"};
function companySector(c){for(const alias of [c.name,...(c.aliases||[])]){const found=Object.keys(CLASSIC_SECTORS).find(n=>companyKey(n)===companyKey(alias));if(found)return CLASSIC_SECTORS[found];}return c.category==='services'?'Consulting / services':'Other / unclassified';}
function companyRows(){return S.investigation.companies||[];}
let indexedJobs=null,indexedCompanies=null,jobsByCompany=new Map(),indexedPeople=null,peopleByCompany=new Map();
function companyPeople(c){if(indexedPeople!==S.investigation.people){indexedPeople=S.investigation.people;peopleByCompany=new Map();for(const p of indexedPeople||[])for(const id of new Set([p.company_id,...(p.company_ids||[])])){if(!peopleByCompany.has(id))peopleByCompany.set(id,[]);peopleByCompany.get(id).push(p);}}return peopleByCompany.get(c.id)||[];}
function companyJobs(c){if(indexedJobs!==S.jobs||indexedCompanies!==S.investigation.companies){indexedJobs=S.jobs;indexedCompanies=S.investigation.companies;jobsByCompany=new Map();const byName=new Map();for(const j of S.jobs){const key=companyKey(j.company);if(!byName.has(key))byName.set(key,[]);byName.get(key).push(j);}for(const company of companyRows()){const ids=new Set(),rows=[];for(const key of new Set([company.name,...(company.aliases||[])].map(companyKey)))for(const j of byName.get(key)||[])if(!ids.has(j.id)){ids.add(j.id);rows.push(j);}jobsByCompany.set(company.id,rows);}}return jobsByCompany.get(c.id)||[];}
const baseMatchingJobs=matchingJobs;
matchingJobs=function(){const rows=baseMatchingJobs();if(C.category==='all'&&C.sector==='all')return rows;const keys=new Set(companyRows().filter(c=>(C.category==='all'||c.category===C.category)&&(C.sector==='all'||companySector(c)===C.sector)).flatMap(c=>[c.name,...(c.aliases||[])]).map(companyKey));return rows.filter(j=>keys.has(companyKey(j.company)));};
const baseOpenCompanyRoles=openCompanyRoles;
openCompanyRoles=function(names,origin='all'){C.category='all';C.sector='all';S.filters.employer='all';baseOpenCompanyRoles(names,origin);};
const baseRenderFreshRows=renderFreshRows;
renderFreshRows=function(){if(document.body?.dataset?.classic){renderInvestigation();return;}baseRenderFreshRows();};
function currentJobs(c){return companyJobs(c).filter(j=>j.status!=='closed'&&j.relevance!=='unrelated'&&(j.independent_discovery||j.independent_evidence));}
function claimText(c){return(c.claims||[]).filter(x=>['project','pega_usage','adjacent_role'].includes(x.type));}
function projectText(c){return claimText(c).find(x=>x.type==='project')?.text||claimText(c)[0]?.text||'Open the dossier for the public professional and hiring evidence.';}
function documentedSkills(c){const text=JSON.stringify([c.claims,c.people]).toLowerCase();return['Pega','Kafka','REST','SOAP','SQL','Constellation','Blueprint','Customer Decision Hub','Customer Service','CLM','KYC','Smart Dispute','BPM','Java','CSSA','CLSA','GenAI'].filter(t=>new RegExp('(^|[^a-z])'+t.toLowerCase()+'([^a-z]|$)').test(text));}
function hiringOpen(c){return(c.hiring_signals||[]).filter(h=>['confirmed_open','page_available'].includes(h.status)).length;}
function evidenceScore(c){return (currentJobs(c).some(j=>j.status==='open'&&['strong','possible'].includes(j.fit))?8:0)+(hiringOpen(c)?4:0)+(c.flags?.bangalore?2:0)+(c.flags?.project?1:0);}
function companyMatches(c){const f=C;return(f.sector==='all'||companySector(c)===f.sector)&&(f.novelty==='all'||employerNovelty(c)?.status===f.novelty)&&(f.category==='all'||c.category===f.category)&&(f.place==='all'||f.place==='bangalore'&&c.flags?.bangalore||f.place==='remote'&&c.flags?.india_remote_lead)&&(!f.query||JSON.stringify([c.name,c.aliases,c.claims,companyPeople(c),c.hiring_signals]).toLowerCase().includes(f.query.toLowerCase()));}
function visibleCompanies(){const rows=companyRows().filter(companyMatches);return rows.sort(C.sort==='name'?(a,b)=>a.name.localeCompare(b.name):(a,b)=>evidenceScore(b)-evidenceScore(a)||a.name.localeCompare(b.name));}
function statTiles(items){return append(el('div','stat-grid'),items.map(([value,label])=>append(el('div','sc'),el('div','sv',value),el('div','sl',label))));}
function fold(title,...nodes){return append(el('details'),el('summary','',title),nodes);}
function section(title,id){const n=append(el('section','section'),el('h2','',title));if(id)n.id=id;return n;}
function table(headers,rows){const t=el('table','tbl'),thead=el('thead'),head=el('tr');headers.forEach(h=>head.append(el('th','',h)));thead.append(head);t.append(thead);const body=el('tbody');for(const cells of rows){const tr=el('tr');for(const cell of cells)tr.append(append(el('td'),cell?.nodeType?cell:el('span','',cell)));body.append(tr);}t.append(body);return append(el('div','tablewrap'),t);}
function companyButton(c){return btn(c.name,()=>freshDetail(c.id),'table-button');}
function updateCounts(){const st=S.investigation.stats||{};$('#classicCounts').textContent=companyRows().length+' companies · '+(st.people_records||0)+' public professional records · '+S.jobs.length+' saved roles';}
function localAnchor(label,id){const a=el('a','',label);a.href='#'+id;a.addEventListener('click',e=>{e.preventDefault();document.getElementById(id)?.scrollIntoView({behavior:'smooth'});closeMobile();});return a;}
function closeMobile(){document.body.classList.remove('mobile-sidebar-open');setMenuLabel();}
function setMenuLabel(){const expanded=matchMedia('(max-width:760px)').matches?document.body.classList.contains('mobile-sidebar-open'):!document.body.classList.contains('sidebar-collapsed');$('#menuToggle').setAttribute('aria-expanded',String(expanded));$('#menuToggle').setAttribute('aria-label',expanded?'Collapse sidebar':'Expand sidebar');}
function renderSidebar(){
 const filters=empty($('#sideFilters')),nav=empty($('#companyNav'));nav.className='company-nav';
 if(S.view==='career'){
  filters.append(el('h3','side-title','Strategy & employer universe'));
  for(const [id,label]of [['overview','Executive dashboard'],['profile','Your market story'],['pay','Compensation'],['priority','Apply-first targets'],['confirmed','Pega evidence'],['probable','Watchlist & gaps'],['global','Global & remote leads'],['teams','Team work & projects'],['contacts','People & referral research'],['movement','Career movements'],['outreach','Outreach & interview approach'],['sources','Sources & search method']])nav.append(localAnchor(label,id));
  return;
 }
 if(['teams','opportunities'].includes(S.view)){
  filters.append(el('h3','side-title','Employer universe'));
  const chips=el('div','side-chips');
  for(const [v,label]of [['all','All'],['gcc','GCC / in-house'],['services','Consulting / SI'],['global','Remote / global'],['unclassified','Unclassified']]){
   const count=companyRows().filter(c=>v==='all'||c.category===v).length;
   chips.append(btn(label+' '+count,()=>{C.category=v;C.company=null;S.companyScope=[];if(S.view==='opportunities'){S.filters.employer='all';renderOpportunities();}else renderInvestigation();renderSidebar();},'fp'+(C.category===v?' active':'')));
  }filters.append(chips);
  filters.append(el('h3','side-title','Sector'),select([['all','All sectors'],...([...new Set(companyRows().map(companySector))].sort().map(x=>[x,x]))],C.sector,v=>{C.sector=v;C.company=null;if(S.view==='opportunities')renderOpportunities();else renderInvestigation();},'Employer sector'));
  if(S.view==='teams'){
   filters.append(el('h3','side-title','Location evidence'));
   const place=el('div','side-chips');for(const [v,l]of [['all','All locations'],['bangalore','Bengaluru'],['remote','India remote leads']])place.append(btn(l,()=>{C.place=v;C.company=null;renderInvestigation();renderSidebar();},'fp'+(C.place===v?' active':'')));filters.append(place);
  }
  const companies=S.view==='teams'?visibleCompanies():companyRows().filter(c=>(C.category==='all'||c.category===C.category)&&(C.sector==='all'||companySector(c)===C.sector)).filter(c=>!S.filters.q||JSON.stringify([c.name,companyJobs(c)]).toLowerCase().includes(S.filters.q.toLowerCase()));
  nav.append(el('h3','side-title',companies.length+' companies'));
  if(S.view==='opportunities')nav.append(btn('All company results',()=>{S.companyScope=[];renderJobList();renderSidebar();},'ci'));
  for(const c of companies){const b=btn('',()=>S.view==='teams'?freshDetail(c.id):openCompanyRoles(c.aliases?.length?c.aliases:[c.name],'fresh'),'ci'+(C.company===c.id?' active':''));append(b,el('span','',c.name),el('small','',S.view==='teams'?companyPeople(c).length+' people':currentJobs(c).length+' roles'));nav.append(b);}
 }
}
function sourceLinks(c=null){
 const phrase=c?'"'+c.name+'" Pega':'Pega OR PRPC OR "workflow automation" OR "integration engineer"';
 const q=encodeURIComponent(phrase),loc=encodeURIComponent(C.place==='remote'?'India':'Bengaluru, Karnataka, India');
 const wrap=el('div','actions');
 append(wrap,link('LinkedIn jobs ↗','https://www.linkedin.com/jobs/search/?keywords='+q+'&location='+loc,'button small'),link('LinkedIn people ↗','https://www.linkedin.com/search/results/people/?keywords='+encodeURIComponent((c?c.name+' ':'')+'Pega Bengaluru'),'button small'),link('Google jobs & teams ↗','https://www.google.com/search?q='+encodeURIComponent(phrase+' Bangalore jobs team'),'button small'),link('Pega events & projects ↗','https://www.google.com/search?q='+encodeURIComponent('site:pega.com '+(c?'"'+c.name+'" ':'')+'PegaWorld'),'button small'),link('Naukri ↗','https://www.naukri.com/pega-jobs?k='+q+'&l=bangalore','button small'));
 if(c){const seen=new Set();for(const h of c.hiring_signals||[]){if(h.kind==='employer_job'&&h.url&&!seen.has(h.url)){seen.add(h.url);wrap.append(link('Employer listing · '+pretty(h.status)+' ↗',h.url,'button small'));}}}
 return append(el('div'),el('p','muted','Manual searches · open the source to explore beyond saved results'),wrap);
}
function classicLaunch(){
 const p=el('section','classic-controls'),field=el('div'),label=el('label','','Annual total CTC floor (LPA)'),input=el('input');input.type='number';input.min=0;input.max=200;input.step=1;input.value=S.minimum;input.id='target-ctc';label.htmlFor=input.id;
 input.addEventListener('input',()=>{const n=input.value===''?NaN:Number(input.value);input.setCustomValidity(Number.isFinite(n)&&n>=0&&n<=200?'':'Enter a CTC floor between 0 and 200.');if(input.checkValidity()){S.minimum=n;const b=$('#searchAllButton');if(b)b.textContent='Search employers · ₹'+n+' LPA+';renderJobList();}});
 const scan=btn('Search employers · ₹'+S.minimum+' LPA+',()=>{if(input.reportValidity())beginFullSearch(false,S.view==='career'?'all':C.category,'fresh');},'button primary');scan.id='searchAllButton';
 append(p,append(field,label,input),scan,btn('Resume saved search',()=>beginFullSearch(true),'button'),btn('Search progress',()=>navigate('discovery'),'button'),el('p','control-note','Broad search: Pega, workflow/BPM and integration roles. The CTC floor filters saved evidence; undisclosed budgets remain leads to confirm. Final goal: ₹35 LPA.'));
 return p;
}
renderOpportunities=function(){
 const main=empty($('#main'));append(main,heading('Pega Job Scanner','Saved results are ready to browse. Use the company sidebar, filters or a new search.',[link('Export CSV','/api/export','button small'),btn('Recheck visible roles',recheckVisible,'button small')]),classicLaunch());
 const f=S.filters,controls=el('div','filters'),change=(key,v)=>{f[key]=v;S.jobLimit=60;renderJobList();renderSidebar();};
 for(const [key,label,options]of [
  ['location','Location',[['all','All locations'],['bangalore','Bengaluru'],['india_remote','Remote from India'],['global','International']]],
  ['track','Filter saved roles',[['all','Pega + adjacent roles'],['pega','Pega roles'],['adjacent','Adjacent skills']]],
  ['pay','CTC evidence',[['target','Target + budget to confirm'],['meets_target','Published CTC meets floor'],['overlaps_target','CTC range crosses floor'],['undisclosed','Undisclosed pay'],['basis_unknown','Pay basis unknown'],['foreign_currency','Foreign currency'],['all','All salary levels']]],
  ['fit','Experience / skill fit',[['all','All fit levels'],['strong','Strong fit'],['possible','Possible fit'],['stretch','Stretch']]],
  ['status','Availability',[['active','Active leads'],['open','Employer page available'],['needs_check','Needs recheck'],['closed','Closed / expired'],['all','All states']]],
  ['pipeline','Pipeline',[['all','All stages'],...['unreviewed','shortlisted','contacted','applied','interviewing','offer','dismissed'].map(x=>[x,pretty(x)])]],
  ['origin','Research catalogue',[['fresh','Fresh evidence'],['all','Include earlier research']]],
  ['relevance','Domain relevance',[['relevant','Relevant / unchecked'],['unrelated','Excluded mismatches'],['all','All discoveries']]]]){
   controls.append(select(options,f[key]||options[0][0],v=>change(key,v),label));
 }
 controls.append(btn('Reset filters',()=>{Object.assign(S.filters,{q:'',location:'all',fit:'all',status:'active',pipeline:'all',employer:'all',pay:'target',track:'all',origin:'fresh',relevance:'relevant'});C.category='all';C.sector='all';S.companyScope=[];$('#classicSearch').value='';renderOpportunities();},'button small'));
 append(main,controls,append(el('div','section-bar'),el('h2','','Saved job results'),el('span','count-text')));main.lastChild.lastChild.id='jobCount';
 if(S.companyScope?.length)main.append(append(el('div','actions'),tag('Selected employer'),btn('Show all companies',()=>{S.companyScope=[];renderOpportunities();},'button small')));
 const rows=el('div');rows.id='jobList';main.append(rows);renderJobList();main.append(fold('Search other sources',sourceLinks()));renderSidebar();
};
renderJobList=function(){
 const target=$('#jobList');if(!target)return;empty(target);
 const rows=matchingJobs();
 if($('#jobCount'))$('#jobCount').textContent=rows.length+' matching · '+S.jobs.length+' saved';
 if(!rows.length){target.append(el('p','empty','No saved roles match. Clear a filter, include undisclosed pay, or search employers again.'));return;}
 const body=rows.slice(0,S.jobLimit).map(j=>{
  const role=append(el('div','role-col'),btn(j.title,()=>jobDetail(j.id),'table-button'),el('p','muted',(j.skills||[]).slice(0,5).join(' · ')),append(el('div','tags'),tag(j.track==='pega'?'Pega':'Adjacent'),j.experience_min!=null?tag(j.experience_min+(j.experience_max?'–'+j.experience_max:'+')+' yrs'):tag('Experience to confirm')));
  const company=append(el('div','company-col'),el('strong','',j.company),el('p','muted',j.location||'Location unconfirmed'));
  const source=append(el('div'),statusTag(j.status),j.evidence?.[0]?.url?link('Source ↗',j.evidence[0].url):null,el('p','muted',(j.checked_at||'').slice(0,10)));
  const pay=append(el('div'),el('span','',payText(j)),el('p','muted',pretty(j.fit)+' fit'));
  const stage=append(el('div'),tag(pretty(j.pipeline?.stage||'unreviewed')),btn('Details & notes',()=>jobDetail(j.id),'button small'));
  return[role,company,source,pay,stage];
 });target.append(table(['Role / skills','Company / location','Availability / source','CTC / fit','Pipeline'],body));
 if(rows.length>S.jobLimit)target.append(btn('Show 60 more · '+(rows.length-S.jobLimit)+' remaining',()=>{S.jobLimit+=60;renderJobList();},'button'));
 updateCounts();
};
renderInvestigation=function(){
 S.directoryMode='fresh';const main=empty($('#main')),companies=visibleCompanies(),st=S.investigation.stats||{};
 append(main,heading('Deep Dossiers','Explore companies, documented work and the people connected to it.',[btn('Search these employer types',()=>beginFullSearch(false,C.category,'fresh'),'button primary')]),statTiles([[companyRows().length,'Researched companies'],[st.people_records||0,'Public professional records'],[st.bangalore_companies||0,'Bengaluru connections'],[st.companies_with_confirmed_vacancies||0,'Employers with application-page evidence']]));
 const tabs=el('div','actions');for(const [v,label]of [['dashboard','Dashboard'],['dossiers','Deep Dossiers'],['people','People'],['hiring','Hiring signals'],['method','Method & search log']])tabs.append(btn(label,()=>{C.mode=v;C.company=null;renderInvestigation();},'fp'+(C.mode===v?' active':'')));
 tabs.append(select([['all','All researched employers'],['new','New employer groups'],['refinement','Newly specified employer'],['existing','Previously covered']],C.novelty,v=>{C.novelty=v;renderInvestigation();},'New or existing employers'));
 tabs.append(select([['evidence','Order by evidence & fit'],['name','Company A–Z']],C.sort,v=>{C.sort=v;renderInvestigation();},'Company order'));main.append(tabs);
 if(C.mode==='method'){
  append(main,employerComparisonMethod()||el('span'),append(el('section','panel'),el('h2','','What was checked'),el('p','',S.investigation.basis),freshList(S.investigation.limitations),el('p','muted',(S.investigation.stats.query_records||0)+' logged research checks · '+(S.investigation.research_date||'Date unknown'))));
  main.append(table(['Research query / source','Check date','Outcome'],(S.investigation.queries||[]).map(q=>[append(el('div'),el('p','',q.query||q.action||q.url||'Source check'),q.url?link('Exact source / query',q.url):null),q.checked_at||'Not stated',freshText(q.outcome||q.source||q.research_file)])));
  renderSidebar();return;
 }
 if(S.employerComparison.new_group_count!=null)main.append(el('p','muted',S.employerComparison.new_group_count+' new employer groups added · '+S.employerComparison.refinement_group_count+' newly specified group. Use the employer filter or Method tab for the comparison.'));
 append(main,el('p','muted',companies.length+' companies match · Public profiles are a discovered sample; current team headcount remains unknown.'));
 const comparison=el('div');comparison.id='freshComparison';main.append(comparison);
 const rows=el('div');rows.id='classicCompanyRows';rows.className=C.mode==='dashboard'?'ov-grid':'fresh-list';main.append(rows);
 if(C.mode==='people'){
  const ids=new Set(companies.map(c=>c.id)),people=(S.investigation.people||[]).filter(p=>[p.company_id,...(p.company_ids||[])].some(id=>ids.has(id))).filter(p=>!C.query||JSON.stringify(p).toLowerCase().includes(C.query.toLowerCase())).filter(p=>C.place!=='bangalore'||/bengaluru|bangalore/i.test(p.location_as_stated||'')||(p.observations||[]).some(o=>/bengaluru|bangalore/i.test(o.location_as_stated||'')));
  rows.className='detail-grid';people.forEach(p=>rows.append(classicPerson(p)));if(!people.length)rows.append(el('p','empty','No named professional matches these filters.'));
 }else if(C.mode==='hiring'){
  for(const c of companies)for(const h of c.hiring_signals||[])rows.append(freshHiringCard(h,c.name));
  if(!rows.children.length)rows.append(el('p','empty','No hiring signals for this selection.'));
 }else if(C.mode==='dossiers'){
  rows.append(table(['Company','Documented work','People / location','Hiring'],companies.map(c=>[companyButton(c),projectText(c),companyPeople(c).length+' profiles · '+(c.flags?.bangalore?'Bengaluru evidence':'Bengaluru unconfirmed'),currentJobs(c).length+' saved role leads'])));
 }else for(const c of companies){
  const card=el('article','ov-card');append(card,companyButton(c),el('p','muted',categories[c.category]||'Employer type unconfirmed'),append(el('div','tags'),c.flags?.bangalore?tag('Bengaluru connection','green'):tag('Location to confirm','gray'),employerNoveltyTag(c)),el('p','project-preview',projectText(c)),append(el('div','tags'),documentedSkills(c).slice(0,6).map(x=>tag(x))),el('p','muted',companyPeople(c).length+' people documented · '+currentJobs(c).length+' role leads'),append(el('div','actions'),btn('Open dossier',()=>freshDetail(c.id),'button small'),btn(S.fresh.compare.includes(c.id)?'Remove comparison':'Compare',()=>{if(S.fresh.compare.includes(c.id))S.fresh.compare=S.fresh.compare.filter(id=>id!==c.id);else if(S.fresh.compare.length<3)S.fresh.compare.push(c.id);else{toast('Compare up to three companies.');return;}renderInvestigation();},'button small')));rows.append(card);
 }
 if(!companies.length)rows.append(el('p','empty','No companies match. Clear the search or change employer/location filters.'));
 renderFreshComparison();renderSidebar();
};
function classicPerson(p){
 const card=el('article','person');append(card,p.profile_url?link(p.name,p.profile_url,'pn'):el('h3','pn',p.name),el('p','pt',[p.title||'Title not exposed',p.employer_as_stated||p.company].filter(Boolean).join(' · ')),el('p','muted',p.location_as_stated||'Location not established'),el('p','',p.pega_connection),el('p','',p.work_summary),append(el('div','tags'),tag(accessLabel(p.access),p.access==='page'?'':'amber'),tag('Checked '+(p.checked_at||'unknown'))));
 const details=fold('Professional sources & observations',p.source_url?link('Source ↗',p.source_url):null,freshList(p.limitations));
 for(const o of p.observations||[])details.append(append(el('div','profile-observation'),el('p','',[o.title,o.employer_as_stated,o.location_as_stated].filter(Boolean).join(' · ')),el('p','',o.work_summary||o.pega_connection),o.source_url?link('Observation source ↗',o.source_url):null));
 card.append(details);return card;
}
freshDetail=function(id){
 const c=companyRows().find(x=>x.id===id);if(!c)return;
 if(S.view!=='teams'){navigate('teams');}
 C.company=id;history.replaceState(null,'','#company='+encodeURIComponent(id));
 const main=empty($('#main'));append(main,btn('← Back to '+(C.mode==='dashboard'?'dashboard':'dossiers'),()=>{C.company=null;history.replaceState(null,'','#teams');renderInvestigation();},'button small'),heading(c.name,categories[c.category]||'Employer type unconfirmed',[btn('Search this company',()=>beginFreshSearch(c.id),'button primary'),btn('View saved roles',()=>openCompanyRoles([c.name,...(c.aliases||[])],'fresh'),'button')]),statTiles([[companyPeople(c).length,'People documented'],[currentJobs(c).length,'Saved role leads'],[hiringOpen(c),'Application-page signals'],[c.current_team_size??'Unknown','Current Pega team size']]));
 const grid=el('div','detail-grid'),projects=section('Projects & use cases'),local=section('Bengaluru & team context');
 for(const claim of claimText(c)){const box=append(el('article','source'),el('p','',claim.text),claim.confidence==='inference'?tag('Inference','amber'):null);box.append(fold('Source · '+accessLabel(claim.access)+' · '+(claim.checked_at||'date unknown'),link(claim.source_title||'Read source',claim.source_url),el('p','muted','Source date: '+(claim.source_date||'not stated')),freshList(claim.limitations)));projects.append(box);}
 if(!claimText(c).length)projects.append(el('p','muted','No independently documented project scope in the saved research.'));
 const localPeople=companyPeople(c).filter(p=>/bengaluru|bangalore/i.test(p.location_as_stated||''));
 append(local,el('p','',c.flags?.bangalore?'A Bengaluru connection is documented. Confirm the team, reporting line and location for the specific role.':'A Bengaluru assignment is not established by this research.'),el('p','',localPeople.map(p=>p.name+' · '+p.location_as_stated).join('; ')||'No named Bengaluru profile in this record.'),el('p','muted',c.flags?.india_remote_lead?'An India remote lead exists; role eligibility needs confirmation.':'Remote-from-India eligibility is not established at employer level.'),fold('Location sources',freshClaimNodes((c.claims||[]).filter(x=>x.type==='bangalore_team'))));
 append(grid,projects,local);main.append(grid);
 const skills=section('Technologies & certifications mentioned');const found=documentedSkills(c);append(skills,append(el('div','tags'),found.length?found.map(x=>tag(x)):tag('Not established')),el('p','muted','Mentions across the saved company and professional sources; these are not requirements for every role.'));main.append(skills);
 const people=section('People & what they work on'),persons=el('div','detail-grid');companyPeople(c).forEach(p=>persons.append(classicPerson(p)));people.append(persons);if(!persons.children.length)people.append(el('p','muted','No named people established in the current research.'));main.append(people);
 const hiring=section('Vacancies & hiring signals');for(const h of c.hiring_signals||[])hiring.append(freshHiringCard(h,c.name));if(!(c.hiring_signals||[]).length)hiring.append(el('p','muted','No current vacancy confirmed. Use saved roles and company searches to investigate.'));main.append(hiring);
 const play=append(el('section','pb-section'),el('h3','','Your approach to this company'),el('p','',c.priority_reason||'Review the documented work and confirm the scope of the specific vacancy.'),el('p','','Position your Pega delivery, Kafka / API integrations and production ownership against the work described above. Ask which team owns the role and what you would deliver in the first six months.'),list(['Confirm role level and whether four years of experience meets the requirement.','Ask about Pega version, UI architecture, integration ownership and on-call expectations.','Confirm Bengaluru allocation or permission to work from India.','Ask for the approved annual total CTC range, fixed pay and variable split. Your goal is ₹35 LPA; no company budget is assumed.']),fold('Open questions from the research',freshList(c.limitations)));main.append(play,section('Search & source shortcuts'));main.lastChild.append(sourceLinks(c));renderSidebar();window.scrollTo({top:0});
};
function companyTable(rows){return table(['Company / type','Documented work','Bengaluru / people','Jobs & next step'],rows.map(c=>[append(el('div'),companyButton(c),el('p','muted',categories[c.category])),projectText(c),append(el('div'),tag(c.flags?.bangalore?'Bengaluru connection':'Location to confirm',c.flags?.bangalore?'green':'gray'),el('p','muted',companyPeople(c).length+' public professional records')),append(el('div'),el('p','',currentJobs(c).length+' saved role leads'),btn('View roles',()=>openCompanyRoles([c.name,...(c.aliases||[])],'fresh'),'button small'))]));}
function careerPane(){
 const main=empty($('#main')),companies=companyRows().filter(c=>!C.hubQuery||JSON.stringify([c,companyPeople(c)]).toLowerCase().includes(C.hubQuery.toLowerCase())).sort((a,b)=>evidenceScore(b)-evidenceScore(a)||a.name.localeCompare(b.name)),st=S.investigation.stats||{};
 const overview=section('Career Intelligence Hub','overview');append(overview,el('p','subtitle','Your employer universe, team research and next steps in one place.'),statTiles([[companyRows().length,'Researched companies'],[st.bangalore_companies||0,'Bengaluru connections'],[st.people_records||0,'People documented'],['₹35 LPA','Your final total CTC goal']]),classicLaunch());main.append(overview);
 const profile=section('Your market story','profile');append(profile,append(el('div','panel'),el('h3','','Pega delivery + integration + production ownership'),el('p','','Four years of experience. Mercedes-Benz R&D India. Pega CSSA, Kafka, REST / SOAP, SQL and auto finance.'),el('p','','Explain the business problem, your design choice, the failure modes you handled and the measurable result. Match the story to the team’s documented work.'),link('Your experience and interview stories','/static/Pega_Interview_Handbook.html?edition=3&layout=wide#ch29','button small')));main.append(profile);
 const pay=section('Compensation','pay');append(pay,statTiles([[money(S.profile.current_ctc),'Current stated CTC'],[money(S.profile.tcs.total),'TCS offered total package'],[money(S.profile.tcs.fixed),'TCS fixed basic + benefits'],['₹'+S.minimum+' LPA','Current search floor']]),el('p','','Published annual INR total CTC, undisclosed pay and unconfirmed salary splits stay separate. An employer salary range is not an offer.'),btn('Open full offer comparison',()=>navigate('salary'),'button'));main.append(pay);
 const groups=[
 ['priority','Apply-first targets',companies.filter(c=>hiringOpen(c)||currentJobs(c).some(j=>j.status==='open')), 'Ordered by available application evidence, role fit, Bengaluru connection and documented project context. This is research priority, not a team-quality rating.'],
 ['confirmed','Companies with Pega evidence',companies.filter(c=>c.flags?.pega),'Evidence may refer to a project, a professional or a role. Open the dossier for scope and dates.'],
 ['probable','Watchlist & unanswered questions',companies.filter(c=>!hiringOpen(c)&&!currentJobs(c).some(j=>j.status==='open')),'Companies worth investigating where current employer hiring is not established.'],
 ['global','Global employers & India remote leads',companies.filter(c=>c.category==='global'||c.flags?.india_remote_lead),'An international employer does not automatically permit remote work from India.'],
 ['teams','Team work & projects',companies.filter(c=>c.flags?.project),'Use the documented work to choose your interview stories and the questions you ask.']];
 for(const [id,title,rows,description]of groups){const sec=section(title+' · '+rows.length,id);append(sec,el('p','muted',description),rows.length?companyTable(rows):el('p','empty','No matching evidence for this section.'));main.append(sec);}
 const contacts=section('People & referral research','contacts'),ids=new Set(companies.map(c=>c.id)),people=(S.investigation.people||[]).filter(p=>[p.company_id,...(p.company_ids||[])].some(id=>ids.has(id))).filter(p=>!C.hubQuery||JSON.stringify(p).toLowerCase().includes(C.hubQuery.toLowerCase()));
 append(contacts,el('p','muted','Public professional observations, not a complete team roster. Exact role, employment dates and willingness to refer may be unknown.'),table(['Person / company','Role / location','Work described','Source'],people.map(p=>[append(el('div'),el('strong','',p.name),el('p','muted',p.company)),append(el('div'),el('span','',p.title||'Title not exposed'),el('p','muted',p.location_as_stated||'Location unconfirmed')),p.work_summary||p.pega_connection||'Not established',append(el('div'),link('Professional source ↗',p.profile_url||p.source_url),el('p','muted',accessLabel(p.access)+' · '+(p.checked_at||'date unknown')))])));main.append(contacts);
 const movement=section('Career movements & hiring context','movement'),moves=companies.flatMap(c=>(c.claims||[]).filter(x=>x.type==='employee_move').map(x=>({...x,company:c.name})));
 append(movement,el('p','muted','A career move does not establish a replacement vacancy. Investigate only against a dated job or hiring source.'),moves.length?freshClaimNodes(moves):el('p','','No sourced movement claim in the current selection.'));main.append(movement);
 const outreach=section('Outreach & interview approach','outreach');append(outreach,append(el('div','panel'),el('h3','','A focused referral message'),el('p','','Hi [Name], I’m a Pega CSSA developer with four years of experience at Mercedes-Benz R&D India, working on Pega delivery, Kafka / API integrations and production automation. I saw [specific role or documented team work]. Could you help me understand the team’s scope and whether this opening fits my background? I can share my resume.'),el('p','muted','Replace the brackets with verified details. Keep project metrics consistent with your resume.'),el('h3','','Questions before committing to a role'),list(['Which product or client team would I join, and what delivery would I own?','How much is new development, modernization, support and on-call work?','What are the Pega version, UI architecture and integration responsibilities?','Is Bengaluru or India remote work approved for this role?','What is the approved total CTC range and fixed / variable split?'])));main.append(outreach);
 const sources=section('Evidence rules & search method','sources');append(sources,el('p','','The current research powers every company and person table on this page. Source dates and page-versus-index access are retained in the dossiers. Job refreshes use public employer-qualified discovery queries and job-description checks. Manual shortcuts let you investigate other sites.'),el('p','muted','The company catalogue is the researched set, not a complete census of all Pega employers. Team sizes, vacancies following departures and employer salary budgets are not inferred.'),btn('View search coverage',()=>navigate('discovery'),'button'),sourceLinks());main.append(sources);renderSidebar();
}
const previousLibraryPane=libraryPane;
libraryPane=function(){previousLibraryPane();for(const a of document.querySelectorAll('.library-card'))if(a.href.includes('/library/career-hub')||a.href.includes('/library/dossiers')){const p=a.querySelector('p');if(p)p.textContent='Familiar layout with current companies, people, jobs and search.';}};
navigate=function(view){
 if(view.startsWith('company=')){const id=decodeURIComponent(view.slice(8));S.view='teams';setClassicView();freshDetail(id);return;}
 const hubAnchors=['overview','profile','pay','priority','confirmed','probable','global','contacts','movement','outreach','sources'];
 if(location.pathname.includes('career-hub')&&hubAnchors.includes(view)){S.view='career';setClassicView();careerPane();document.getElementById(view)?.scrollIntoView();return;}
 if(!['career','opportunities','teams','depth','salary','discovery','library'].includes(view))view='opportunities';
 S.view=view;C.company=null;history.replaceState(null,'','#'+view);setClassicView();
 ({career:careerPane,opportunities:jobsPane,teams:()=>renderInvestigation(),depth:renderTeamDepth,salary:salaryPane,discovery:discoveryPane,library:libraryPane}[view])();renderSidebar();closeMobile();
};
function setClassicView(){
 document.body.classList.toggle('career-mode',S.view==='career');
 document.querySelectorAll('nav button[data-view]').forEach(b=>{b.classList.toggle('active',b.dataset.view===S.view);if(b.dataset.view===S.view)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
 $('#currentView').textContent={career:'Career Intelligence Hub',opportunities:'Job Scanner',teams:'Deep Dossiers',salary:'Compensation',discovery:'Search progress & coverage',library:'Interview preparation',depth:'Earlier team briefs'}[S.view];
 const q=$('#classicSearch');q.value=S.view==='opportunities'?S.filters.q:S.view==='career'?C.hubQuery:C.query;q.hidden=!['teams','opportunities','career'].includes(S.view);q.placeholder=S.view==='opportunities'?'Search roles, companies, skills, cities…':'Search companies, people, work, cities…';updateCounts();
}
$('#menuToggle').addEventListener('click',()=>{if(matchMedia('(max-width:760px)').matches)document.body.classList.toggle('mobile-sidebar-open');else{document.body.classList.toggle('sidebar-collapsed');try{localStorage.setItem('pega-classic-sidebar',document.body.classList.contains('sidebar-collapsed')?'collapsed':'open');}catch{}}setMenuLabel();});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeMobile();});
document.addEventListener('click',e=>{if(document.body.classList.contains('mobile-sidebar-open')&&!$('#classicSidebar').contains(e.target)&&!$('#menuToggle').contains(e.target))closeMobile();});
$('#classicSearch').addEventListener('input',e=>{const q=e.target.value;if(S.view==='opportunities'){S.filters.q=q;S.jobLimit=60;renderJobList();renderSidebar();}else if(S.view==='career'){C.hubQuery=q;careerPane();}else{C.query=q;C.company=null;history.replaceState(null,'','#teams');renderInvestigation();}});
try{if(localStorage.getItem('pega-classic-sidebar')==='collapsed')document.body.classList.add('sidebar-collapsed');}catch{}
window.addEventListener('resize',setMenuLabel);
if(typeof ResizeObserver!=='undefined'){const observer=new ResizeObserver(()=>document.body.style.setProperty('--toolbar-height',$('.topbar').getBoundingClientRect().height+'px'));observer.observe($('.topbar'));}
setMenuLabel();S.jobLimit=60;
if(!location.hash){if(location.pathname.includes('career-hub'))history.replaceState(null,'','#career');else if(location.pathname.includes('dossiers'))history.replaceState(null,'','#teams');}
window.classicReady=true;
init();
