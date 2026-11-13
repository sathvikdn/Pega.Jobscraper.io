'use strict';
window.DossierView = (() => {
    let generation = 0;
    const make = (tag, value) => {const node=document.createElement(tag);if(value!==undefined)node.textContent=String(value);return node;};
    async function open(company) {
        const requestNumber=++generation;
        const dialog=make('dialog');dialog.className='job-dialog dossier-view';
        dialog.setAttribute('aria-label', 'Company dossier: '+company);
        const header=make('header');header.className='detail-header';header.append(make('h2',company));
        const close=make('button','Close');close.type='button';close.addEventListener('click',()=>dialog.close());header.append(close);
        const content=make('div','Loading saved evidence…');content.className='detail-content';
        dialog.append(header,content);document.body.append(dialog);
        const opener=document.activeElement;
        dialog.addEventListener('close',()=>{dialog.remove();opener?.focus();});dialog.showModal();
        try {
            const response=await fetch('/api/company-dossier?name='+encodeURIComponent(company));
            if(!response.ok)throw new Error('Dossier request failed');
            const data=await response.json();
            if(requestNumber!==generation||!dialog.open)return;
            content.replaceChildren();
            const tabs=make('div');tabs.setAttribute('role','tablist');tabs.className='dossier-tabs';
            const panel=make('section');panel.setAttribute('role','tabpanel');panel.id='dossier-panel-'+requestNumber;
            const sections=[['Verified India offices',data.offices],['Active openings',data.openings],['Pega frameworks',data.frameworks],['Team evidence',data.people],['Source freshness',data.sources]];
            const buttons=[];
            function select(index) {
                buttons.forEach((button,position)=>{button.setAttribute('aria-selected',String(position===index));button.tabIndex=position===index?0:-1;});
                panel.setAttribute('aria-labelledby',buttons[index].id);panel.replaceChildren();
                panel.append(make('p',sections[index][0]==='Active openings'?'Saved leads; acceptance of applications must be checked on the employer site.':'Only source-linked saved evidence is shown. Missing evidence remains unknown.'));
                const items=sections[index][1]??[];
                if(sections[index][0]==='Team evidence'){
                    panel.append(make('p','Saved public profiles are evidence records, not a verified team headcount.'));
                    const label=make('label','Filter people');const input=make('input');input.type='search';label.append(input);
                    input.addEventListener('input',()=>panel.querySelectorAll('article').forEach(article=>{article.hidden=!article.textContent.toLowerCase().includes(input.value.trim().toLowerCase());}));
                    panel.append(label);
                }
                if(!items.length)panel.append(make('p','No verified evidence available for this section.'));
                for(const item of items) {
                    const article=make('article');article.className='dossier-evidence';article.append(make('h3',item.title??'Evidence'),make('p',item.text??''));
                    if(item.location)article.append(make('p',item.location));
                    article.append(make('small','Checked: '+(item.checked_at??'Unknown')));
                    if(item.url){try{const url=new URL(item.url);if(['http:','https:'].includes(url.protocol)&&!url.username&&!url.password){const anchor=make('a','View source');anchor.href=url.href;anchor.target='_blank';anchor.rel='noopener noreferrer';article.append(anchor);}}catch{}}
                    panel.append(article);
                }
            }
            sections.forEach(([label],index)=>{
                const button=make('button',label);button.type='button';button.id='dossier-tab-'+requestNumber+'-'+index;button.setAttribute('role','tab');button.setAttribute('aria-controls',panel.id);
                button.addEventListener('click',()=>select(index));
                button.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight'].includes(event.key)){event.preventDefault();const next=(index+(event.key==='ArrowRight'?1:sections.length-1))%sections.length;select(next);buttons[next].focus();}});
                buttons.push(button);tabs.append(button);
            });
            content.append(tabs,panel);select(0);
        } catch(error) {if(dialog.open)content.textContent='Unable to load dossier: '+error.message;}
    }
    return {open};
})();
