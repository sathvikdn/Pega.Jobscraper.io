function renderPersonHTML(m){return m._profile_html||'';}
function openCompany(name){
  const co=DATA.find(c=>c._ui_key===name||c.name===name);if(!co)return;
  DossierView.open(co.name);
}
function filterCompanyPeople(){
 const q=document.getElementById('teamPeopleSearch').value.toLowerCase().trim();
 const local=document.getElementById('teamBengaluru').checked;let visible=0;
 document.querySelectorAll('#mainContent .intel-role-group').forEach(group=>{
  let count=0;group.querySelectorAll('.pv-person').forEach(row=>{
   const text=(row.dataset.search||row.textContent).toLowerCase();
   const location=row.dataset.location||'';
   row.hidden=!!(q&&!text.includes(q)||local&&!/bengaluru|bangalore/i.test(location));
   if(!row.hidden)count++;
  });group.hidden=count===0;visible+=count;
 });document.getElementById('teamPeopleEmpty').hidden=visible>0;
}
