'use strict';
// Extend the original Hub search to its expandable company and people cards.
const originalHubFilter=filterRows;
const companyOpenBeforeSearch=new WeakMap();
filterRows=function(){
 originalHubFilter();
 const q=document.getElementById('search').value.toLowerCase().trim();
 document.querySelectorAll('.intel-company').forEach(company=>{
  const summary=company.querySelector(':scope > summary');const companyMatch=!!q&&summary.textContent.toLowerCase().includes(q);let count=0;
  company.querySelectorAll('.pv-person').forEach(person=>{
   const haystack=(person.dataset.search||person.textContent).toLowerCase();
   person.hidden=!!(q&&!companyMatch&&!haystack.includes(q));if(!person.hidden)count++;
  });
  company.querySelectorAll('.pv-group').forEach(group=>{group.hidden=!Array.from(group.querySelectorAll('.pv-person')).some(person=>!person.hidden);});
  company.hidden=!!q&&!count;
  if(q){if(!companyOpenBeforeSearch.has(company))companyOpenBeforeSearch.set(company,company.open);if(count)company.open=true;}
  else if(companyOpenBeforeSearch.has(company)){company.open=companyOpenBeforeSearch.get(company);companyOpenBeforeSearch.delete(company);}
 });
};
const savedProfileBodies=new Map();
document.addEventListener('toggle',async event=>{
 const details=event.target;if(!details.matches('details[data-profile-lazy]')||!details.open||details.dataset.loaded||details.dataset.loading)return;
 const row=details.closest('.pv-person'),body=details.querySelector('.person-body');
 const path='/api/intelligence/companies/'+encodeURIComponent(row.dataset.companyId)+'/people/'+encodeURIComponent(row.dataset.personId);
 details.dataset.loading='true';body.textContent='Loading saved profile details…';
 try{
  if(!savedProfileBodies.has(path))savedProfileBodies.set(path,fetch(path).then(async response=>{const data=await response.json();if(!response.ok)throw Error(data.error||'Saved details could not be loaded.');return data.html;}).catch(error=>{savedProfileBodies.delete(path);throw error;}));
  const html=await savedProfileBodies.get(path),template=document.createElement('template');template.innerHTML=html;
  const saved=template.content.querySelector('.person-body');if(!saved)throw Error('Saved profile details were not available.');
  body.replaceWith(saved.cloneNode(true));details.dataset.loaded='true';
 }catch(error){body.textContent=error.message+' Close and expand this person to retry.';}
 finally{delete details.dataset.loading;}
},true);
