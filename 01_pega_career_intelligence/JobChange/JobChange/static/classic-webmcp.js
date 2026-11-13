'use strict';
(function registerClassicTools(){
 const registry=document.modelContext;
 if(!registry?.registerTool)return;
 const lifetime=new AbortController();
 window.addEventListener('pagehide',()=>lifetime.abort(),{once:true});
 const validate=(input,keys)=>{if(!input||typeof input!=='object'||Array.isArray(input)||Object.keys(input).some(k=>!keys.includes(k)))throw Error('Invalid input');if(!S.profile)throw Error('Research is still loading');};
 const definitions=[
  {name:'filter_saved_roles',title:'Filter saved job results',description:'Filter the visible saved roles by text and location. Does not start a search or apply to jobs.',inputSchema:{type:'object',properties:{query:{type:'string',maxLength:250},location:{type:'string',enum:['all','bangalore','india_remote','global']}},required:['query'],additionalProperties:false},annotations:{readOnlyHint:false,untrustedContentHint:true},execute(input){validate(input,['query','location']);if(typeof input.query!=='string'||input.query.length>250||input.location!==undefined&&!['all','bangalore','india_remote','global'].includes(input.location))throw Error('Invalid role filter');C.category='all';C.sector='all';S.companyScope=[];Object.assign(S.filters,{q:input.query,location:input.location||'all',employer:'all',fit:'all',pay:'target',track:'all',status:'active',pipeline:'all',origin:'fresh',relevance:'relevant'});navigate('opportunities');return{count:matchingJobs().length,ctc_floor_lpa:S.minimum,view:S.view};}},
  {name:'open_company_dossier',title:'Open a company dossier',description:'Open an existing researched company by exact company name or ID and return its ID and documented people count.',inputSchema:{type:'object',properties:{company:{type:'string',minLength:1,maxLength:200}},required:['company'],additionalProperties:false},annotations:{readOnlyHint:false,untrustedContentHint:true},execute(input){validate(input,['company']);if(typeof input.company!=='string'||!input.company.trim()||input.company.length>200)throw Error('Invalid company');const c=companyRows().find(c=>c.id===input.company||c.name.toLowerCase()===input.company.toLowerCase());if(!c)throw Error('Company is not in the researched catalogue');freshDetail(c.id);return{id:c.id,name:c.name,people_documented:companyPeople(c).length,view:'dossier'};}}
 ];
 for(const tool of definitions){try{Promise.resolve(registry.registerTool(tool,{signal:lifetime.signal})).catch(()=>{});}catch{}}
})();
