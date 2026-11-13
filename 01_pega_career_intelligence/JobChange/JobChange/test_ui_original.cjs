const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
class E{
 constructor(tag){this.tagName=tag;this.children=[];this.events={};this.attrs={};this.dataset={};this.style={};this.className='';this.value='';this.classList={contains:c=>this.className.split(' ').includes(c),add:c=>{if(!this.classList.contains(c))this.className+=' '+c;},remove:c=>this.className=this.className.split(' ').filter(x=>x!==c).join(' '),toggle:(c,v)=>{const on=v??!this.classList.contains(c);on?this.classList.add(c):this.classList.remove(c);}};}
 append(...xs){this.children.push(...xs);}replaceChildren(){this.children=[];this._text='';}
 set textContent(x){this._text=String(x);this.children=[];}get textContent(){return(this._text||'')+this.children.map(x=>x.textContent).join(' ');}
 addEventListener(k,f){this.events[k]=f;}setAttribute(k,v){this.attrs[k]=v;}
}
const walk=e=>[e,...e.children.flatMap(walk)],body=new E('body');
// Build the static controls from the actual template so newly added controls do not break this legacy flow harness.
const template=fs.readFileSync(path.join(__dirname,'templates/scanner.html'),'utf8');
for(const match of template.matchAll(/<([a-z0-9]+)[^>]*\bid="([^"]+)"/g)){const e=new E(match[1]);e.id=match[2];body.append(e);}
for(const cat of ['gcc','si','remote','all']){const e=new E('button');e.className='cat-tab';e.dataset.cat=cat;body.append(e);}
const document={getElementById:id=>walk(body).find(e=>e.id===id),createElement:t=>new E(t),querySelectorAll:s=>s==='.cat-tab[data-cat]'?walk(body).filter(e=>e.classList.contains('cat-tab')&&e.dataset.cat):[]};
const sent=[],location={origin:'http://127.0.0.1:5050',hash:'#scan'},fixtures=JSON.parse(fs.readFileSync(path.join(__dirname,'.ui-validation/original-fixtures.json'),'utf8'));
const context=vm.createContext({document,assert,console,URL,Set,Map,location,history:{replaceState(_,__,hash){location.hash=hash;}},setInterval:()=>1,clearInterval(){},fetch:async(path,options={})=>{sent.push({path,...options});return{ok:true,json:async()=>path==='/api/scan'?{status:'started',total:20}:fixtures[path]};}});
context.sent=sent;context.walk=walk;context.fixtures=fixtures;
vm.runInContext(fs.readFileSync(path.join(__dirname,'static/original-scanner.js'),'utf8').replace(/\ninitializeScanner\(\);\s*$/,''),context);
(async()=>{
 await vm.runInContext('initializeScanner()',context);
 vm.runInContext("assert.equal(selectedMode,'gcc_top10');assert.equal(byId('depthRow').children.length,3);assert.ok(!byId('resultScreen').classList.contains('show'));assert.equal(sent.filter(x=>x.path==='/api/scan').length,0);byId('depthRow').children[1].events.click();assert.equal(selectedMode,'gcc_top20');",context);
 await vm.runInContext('startScan()',context);
 const request=sent.find(x=>x.path==='/api/scan');assert.equal(JSON.parse(request.body).mode,'gcc_top20');assert.equal(request.headers['X-Career-Token'],'fixture-only');
 vm.runInContext("assert.ok(byId('resultScreen').classList.contains('show'));assert.ok(byId('mainContent').textContent.includes('Recommended Pega jobs'));const previous=byId('mainContent').textContent;byId('filterInput').value='__missing__';applyFilter();assert.ok(byId('mainContent').textContent.includes('No verified Pega matches'));byId('filterInput').value='';applyFilter();assert.equal(byId('mainContent').textContent,previous);const company=allResults.find(c=>c.jobs.length);showCompany(company.name);assert.ok(byId('mainContent').textContent.includes(company.name));showAll();assert.ok(byId('mainContent').textContent.includes('Recommended Pega jobs'));goBack();assert.ok(!byId('resultScreen').classList.contains('show'));assert.ok(!byId('scanScreen').classList.contains('hide'));assert.equal(safeLink('bad','javascript:alert(1)').tagName,'span');assert.equal(byId('rNew').textContent,String(new Set(allResults.flatMap(c=>c.jobs.filter(j=>j.is_new).map(j=>j.id))).size));",context);
 fixtures['/api/status']={running:true,phase:'parallel_scan',progress:7,total:278,description_progress:3,description_total:5,parallel:{discovery_active:12,descriptions_active:6},log_lines:[]};
 await vm.runInContext('pollStatus()',context);
 vm.runInContext("assert.ok(byId('progTxt').textContent.includes('Companies 7/278'));assert.ok(byId('progTxt').textContent.includes('Descriptions 3/5'));assert.ok(byId('progTxt').textContent.includes('12 company searches + 6 descriptions'));assert.ok(!byId('resultScreen').classList.contains('show'));",context);
 await vm.runInContext('switchToResults()',context);
 const before=sent.filter(x=>x.path==='/api/scan-results').length;
 vm.runInContext('lastResultsRefresh=0',context);await vm.runInContext('pollStatus()',context);
 assert.equal(sent.filter(x=>x.path==='/api/scan-results').length,before+1);
 vm.runInContext("assert.equal(byId('liveResultsStatus').hidden,false);assert.ok(byId('liveResultsStatus').textContent.includes('Results update'));",context);
 fixtures['/api/status']={running:false,phase:'parallel_scan',progress:7,total:278,scanner:{status:'paused'},log_lines:[]};
 await vm.runInContext('pollStatus()',context);
 vm.runInContext("assert.ok(byId('progTxt').textContent.includes('paused'));assert.equal(byId('liveResultsStatus').hidden,true);",context);
 console.log('PASS: original launcher -> depth selection -> Python POST -> saved results -> company/filter/clear -> New scan; safe links and unique new count.');
})().catch(e=>{console.error(e);process.exitCode=1;});
