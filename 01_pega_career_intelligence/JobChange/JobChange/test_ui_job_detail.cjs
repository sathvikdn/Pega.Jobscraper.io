'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
let document;
class E{
 constructor(tag){this.tagName=tag;this.children=[];this.events={};this.attrs={};this.dataset={};this.style={};this.className='';this.value='';this.disabled=false;this.open=false;this.classList={contains:c=>this.className.split(' ').includes(c),add:c=>{if(!this.classList.contains(c))this.className+=' '+c;},remove:c=>{this.className=this.className.split(' ').filter(x=>x!==c).join(' ');},toggle:(c,v)=>{const on=v??!this.classList.contains(c);on?this.classList.add(c):this.classList.remove(c);return on;}};}
 append(...items){for(const n of items){n.parentNode=this;this.children.push(n);}}
 replaceChildren(){for(const child of this.children)child.parentNode=null;this.children=[];this._text='';}
 set textContent(v){this.replaceChildren();this._text=String(v);}get textContent(){return(this._text||'')+this.children.map(c=>c.textContent).join(' ');}
 set innerHTML(_){throw Error('Job content must never use raw HTML');}
 setAttribute(k,v){this.attrs[k]=v;}addEventListener(k,f){this.events[k]=f;}
 showModal(){this.open=true;}close(){this.open=false;this.events.close?.();}focus(){document.activeElement=this;}
 get isConnected(){return this===body||Boolean(this.parentNode?.isConnected);}
}
const walk=n=>[n,...n.children.flatMap(walk)],body=new E('body');
const html=fs.readFileSync(path.join(__dirname,'templates/scanner.html'),'utf8');
for(const match of html.matchAll(/<([a-z0-9]+)[^>]*\bid="([^"]+)"/g)){const e=new E(match[1]);e.id=match[2];body.append(e);}
for(const cat of ['gcc','si','remote','all']){const e=new E('button');e.className='cat-tab';e.dataset.cat=cat;body.append(e);}
document={activeElement:null,getElementById:id=>walk(body).find(e=>e.id===id),createElement:t=>new E(t),querySelectorAll:s=>s==='.cat-tab[data-cat]'?walk(body).filter(e=>e.classList.contains('cat-tab')&&e.dataset.cat):[]};
const job={
 id:'role 1',title:'Pega Developer',company:'Example GCC',location:'Bengaluru',url:'https://example.test/jobs/1',source:'Employer',is_new:true,evidence_status:'Description checked',
 recommendation:{eligible:true,status:'recommended',experience_label:'3–5 years',reasons:['Pega is required in the checked description.']},
 resume_match:{score:76,label:'Good evidence match',method:'Weighted comparison of requirements with resume evidence',matched:[{requirement:'Case management',evidence:'Built Pega case workflows for applications.',jd_evidence:'Must design case lifecycles.',importance:'required'}],missing:[{requirement:'Constellation',jd_evidence:'Constellation experience preferred.',importance:'preferred'}],notes:['Assess only skills you can demonstrate.'],resume_source:'Pega_Resume.html'},
 description_text:'Pega developer, 3–5 years.\nBuild case management.\n<img src=x onerror=alert(1)>',
 description_complete:true,description_source_url:'https://example.test/jobs/1',description_checked_at:'2026-09-08T10:00:00Z'
};
const unverified={...job,id:'review-role',title:'Pega Engineer',recommendation:{eligible:false,status:'review',experience_label:'Experience unknown',reasons:['Experience requirement not verified.']},resume_match:{score:null,label:'Description not yet checked',method:'Not an ATS score.'},description_complete:false,description_text:'',description_source_url:'javascript:alert(1)'};
const recommended={companies:[{name:'Example GCC',jobs:[job],new_count:1,checks:[],links:{}}],policy_counts:{recommended:1,stretch:0,review:1,excluded:8},policy:'Pega in the checked description; stated experience below 8 years.'};
const review={...recommended,companies:[{name:'Example GCC',jobs:[unverified],new_count:0,checks:[],links:{}}]};
const fixtures={'/api/bootstrap':{token:'fixture-csrf'},'/api/scan-options':{total_targets:20,categories:{gcc:[{mode:'gcc_top10',label:'Top 10',count:10},{mode:'gcc_top20',label:'Top 20',count:20}],si:[],remote:[],all:[]}},'/api/status':{running:false,progress:0,total:0,log_lines:[]},'/api/scan-results':recommended,'/api/scan-results?scope=review':review,'/api/opportunities/role%201':{opportunity:job},'/api/opportunities/review-role':{opportunity:unverified}};
const sent=[],location={origin:'http://127.0.0.1:5050',hash:'#scan'};
let pendingDetail=null,refreshError=false;
const context=vm.createContext({document,assert,console,URL,Set,Map,location,history:{replaceState(_,__,hash){location.hash=hash;}},setInterval:()=>1,clearInterval(){},fetch:async(url,options={})=>{
 sent.push({url,...options});
 if(url==='/api/opportunities/slow')return new Promise(resolve=>{pendingDetail=()=>resolve({ok:true,json:async()=>({opportunity:{...job,id:'slow',title:'STALE ROLE'}})});});
 if(url.endsWith('/description'))return{ok:!refreshError,json:async()=>refreshError?{error:'Source unavailable'}:{opportunity:{...job,resume_match:{...job.resume_match,score:80}}}};
 return{ok:true,json:async()=>url==='/api/scan'?{status:'started',total:20}:fixtures[url]};
}});
context.job=job;context.unverified=unverified;context.sent=sent;context.walk=walk;
vm.runInContext(fs.readFileSync(path.join(__dirname,'static/original-scanner.js'),'utf8').replace(/\ninitializeScanner\(\);\s*$/,''),context);
const run=code=>vm.runInContext(code,context);
(async()=>{
 await run('initializeScanner()');
 assert.equal(sent.filter(r=>r.url==='/api/scan').length,0);
 run("byId('depthRow').children[1].events.click();assert.equal(selectedMode,'gcc_top20')");
 await run('startScan()');
 assert.equal(JSON.parse(sent.find(r=>r.url==='/api/scan').body).mode,'gcc_top20');
 run("assert.ok(byId('mainContent').textContent.includes('Recommended Pega jobs'));assert.ok(byId('mainContent').textContent.includes('3–5 years'));assert.ok(byId('mainContent').textContent.includes('76/100'));assert.ok(byId('mainContent').textContent.includes('View description'));assert.ok(!byId('mainContent').textContent.includes('review-role'));assert.equal(byId('reviewScope').textContent,'Needs verification (1)')");
 run("showCompany('Example GCC');assert.ok(byId('mainContent').textContent.includes('Example GCC'));byId('filterInput').value='__missing__';applyFilter();assert.ok(byId('mainContent').textContent.includes('No results match'));byId('filterInput').value='';showAll()");
 await run("switchToResults('review')");
 run("assert.ok(byId('mainContent').textContent.includes('Not scored'));assert.ok(byId('mainContent').textContent.includes('Needs verification'));assert.ok(!byId('mainContent').textContent.includes('76/100'))");
 await run("switchToResults('recommended')");
 const opener=run("walk(byId('mainContent')).find(e=>e.tagName==='button'&&e.textContent==='View description')");
 context.opener=opener;opener.focus();
 const beforePost=sent.filter(r=>r.method==='POST').length;
 await run('openJobDetail(job,opener)');
 assert.equal(sent.filter(r=>r.method==='POST').length,beforePost,'Viewing must only read saved data');
 run("assert.ok(byId('jobDialog').open);assert.equal(document.activeElement,byId('closeJobDetail'));assert.ok(byId('jobDialogContent').textContent.includes('<img src=x onerror=alert(1)>'));assert.ok(!walk(byId('jobDialogContent')).some(e=>e.tagName==='img'));assert.ok(byId('jobDialogContent').textContent.includes('Built Pega case workflows'));assert.ok(byId('jobDialogContent').textContent.includes('Constellation'));assert.ok(byId('jobDialogContent').textContent.includes('not an ATS'));assert.ok(byId('jobDialogContent').textContent.includes('2026-09-08'));assert.ok(walk(byId('jobDialogContent')).some(e=>e.href==='http://127.0.0.1:5050/library/resume'))");
 await run('refreshJobDescription()');
 const refresh=sent.find(r=>r.url.endsWith('/description'));
 assert.equal(refresh.url,'/api/opportunities/role%201/description');assert.equal(refresh.method,'POST');assert.equal(refresh.headers['X-Career-Token'],'fixture-csrf');assert.deepEqual(JSON.parse(refresh.body),{});
 run("assert.ok(byId('jobDialogContent').textContent.includes('80/100'));assert.ok(byId('jobDialog').open);assert.equal(byId('refreshDescription').disabled,false)");
 refreshError=true;await run('refreshJobDescription()');
 run("assert.ok(byId('jobDialogStatus').textContent.includes('Source unavailable'));assert.equal(byId('refreshDescription').disabled,false);closeJobDialog();assert.equal(document.activeElement,byId('recommendedScope'))");
 refreshError=false;
 await run('openJobDetail(unverified,byId("reviewScope"))');
 run("assert.ok(byId('jobDialogContent').textContent.includes('Not scored'));assert.ok(byId('jobDialogContent').textContent.includes('No saved description'));assert.ok(!walk(byId('jobDialogContent')).some(e=>(e.href||'').startsWith('javascript:')));closeJobDialog();assert.equal(document.activeElement,byId('reviewScope'))");
 const slow=run("openJobDetail({...job,id:'slow'},byId('recommendedScope'))");
 run('closeJobDialog()');
 await run('openJobDetail(job,byId("recommendedScope"))');
 pendingDetail();await slow;
 run("assert.equal(byId('jobDialogTitle').textContent,'Pega Developer');closeJobDialog();goBack();assert.ok(!byId('resultScreen').classList.contains('show'));assert.ok(!byId('scanScreen').classList.contains('hide'));assert.equal(safeLink('bad','javascript:alert(1)').tagName,'span')");
 assert.ok(html.includes('aria-labelledby="jobDialogTitle"'));assert.ok(html.includes('<dialog '));assert.ok(html.includes('white-space:pre-wrap'));assert.ok(html.includes('overflow-x:auto'));
 console.log('PASS: original category/depth/search flow; strict scopes; experience and scores; saved description GET; safe text/links; authenticated refresh; evidence/gaps; missing JD; error recovery; stale request protection; dialog close/focus restoration.');
})().catch(error=>{console.error(error);process.exitCode=1;});
