"""Render the original library layouts with current source-backed content."""
import html,json,re
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from opportunity_data import company_key

def esc(v):return html.escape(str(v or ''),quote=True)
def safe_url(v):
    try:return str(v) if urlsplit(str(v or '')).scheme in ('http','https') else ''
    except (ValueError,TypeError):return ''
def a(label,url):
    url=safe_url(url)
    return '<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">'+esc(label)+'</a>' if url else esc(label)
def people(c,doc):
    return [p for p in doc.get('people',[]) if c['id'] in {p.get('company_id'),*p.get('company_ids',[])}]
def claims(c):return[x for x in c.get('claims',[]) if x.get('type') in ('project','pega_usage','adjacent_role')]
def claim_text(x):return ('Earlier research (not reverified): ' if x.get('access')=='legacy' else 'Inference: ' if x.get('confidence')=='inference' else '')+str(x.get('text') or '')
def skills(c):
    text=json.dumps([c.get('claims'),c.get('people'),c.get('legacy_details',{}).get('tech_stack')]).lower()
    return [t for t in ['Pega','Kafka','REST','SOAP','SQL','CSSA','CLSA','Constellation','Blueprint','CLM','KYC','Customer Service','Decisioning'] if re.search(r'(?<![a-z])'+re.escape(t.lower())+r'(?![a-z])',text)]
def taxonomy(base):
    s=(base/'Pega_Deep_Dossiers.html').read_text(encoding='utf-8')
    raw=s.split('const DATA=',1)[1]
    old,end=json.JSONDecoder().raw_decode(raw)
    return s,raw,end,{company_key(c['name']):(c['sector'],c.get('_sector_group','Other')) for c in old}
def sector(c,tax):
    for name in [c['name'],*c.get('aliases',[])]:
        if company_key(name) in tax:return tax[company_key(name)]
    return ('Consulting / services','Consulting / services') if c.get('category')=='services' else ('Unclassified','Other')
def evidence(x):
    if x.get('access')=='legacy':return 'Earlier source · not reverified · '+str(x.get('source_file') or 'Original research')+' · '+str(x.get('source_date') or 'date unknown')
    label='Search index' if x.get('access')=='search_index' else 'Page read' if x.get('access')=='page' else 'Access unconfirmed'
    return 'Checked '+str(x.get('checked_at') or 'date unknown')+' · '+label+' · Source date '+str(x.get('source_date') or 'not stated')
def dossier_data(base,doc):
    _,_,_,tax=taxonomy(base)
    rows=[]
    for i,c in enumerate(doc.get('companies',[])):
        sector_name,group=sector(c,tax)
        public=people(c,doc)
        old=c.get('legacy_details',{})
        members=[]
        for p in public:
            obs=p.get('observations') or [p]
            career=[{'company':esc(o.get('employer_as_stated') or p.get('company') or c['name']),'role':esc(o.get('title') or 'Professional source observation'),'dates':esc(evidence(o)),'location':esc(o.get('location_as_stated')),'detail':esc(o.get('work_summary') or o.get('pega_connection'))} for o in obs]
            for o in obs:
                for step in o.get('career',[]):
                    if isinstance(step,dict):career.append({k:esc(v) for k,v in dict(step,dates='Earlier record · '+str(step.get('dates','date unknown'))).items() if k in ('company','role','dates','location','detail')})
            career=list({json.dumps(row,sort_keys=True):row for row in career}.values())
            members.append({'name':esc(p.get('name')),'title':esc(p.get('title') or 'Title not exposed'),'location':esc(p.get('location_as_stated') or 'Location unconfirmed'),'linkedin':esc(safe_url(p.get('profile_url') or p.get('source_url'))),'career':career,'certifications':[esc(v) for v in p.get('certifications',[])],'_role_label':'Documented professional profiles','_role_level':5})
        notes=[esc(claim_text(x))+' · '+a(x.get('source_title') or 'Source',x.get('source_url'))+' · '+esc(evidence(x)) for x in c.get('claims',[])]
        for signal in c.get('hiring_signals',[]):
            notes.append(a(signal.get('title') or 'Hiring source',signal.get('url'))+' · '+esc(signal.get('status','unverified'))+' · '+esc(evidence(signal)))
        notes.extend(esc(v) for v in c.get('limitations',[]))
        notes.extend('Earlier research (not reverified): '+esc(v) for v in old.get('highlights',[]))
        if old.get('team_size'):notes.append('Earlier team-size estimate: '+esc(old['team_size'])+' · basis not verified; profile count is not current headcount.')
        if c.get('evidence_status')=='search_target_only':notes.append('Original company search target. Current Pega team and vacancy evidence have not yet been established.')
        for depth in c.get('team_depth',[]):
            notes.append('Earlier sourced team research: '+esc(depth.get('team_focus'))+'<br>'+esc(' '.join(depth.get('what_they_build',[])))+'<br>'+esc(depth.get('ownership_evidence'))+'<br>'+esc(depth.get('bangalore_scope'))+'<br>'+' · '.join(a(x.get('title') or 'Source',x.get('url')) for x in depth.get('sources',[])))
            assessment=depth.get('assessment',{})
            for key in ('reasons','tradeoffs','questions_to_ask'):
                notes.extend(esc(key.replace('_',' ').capitalize()+': '+v) for v in assessment.get(key,[]))
        projects=' '.join(claim_text(x) for x in claims(c)) or 'Project scope not established by the saved sources.'
        locations=list(dict.fromkeys(p.get('location_as_stated') for p in public if p.get('location_as_stated')))
        if not locations:locations=['Bengaluru connection observed' if c.get('flags',{}).get('bangalore') else 'Location not established']
        opened=any(h.get('status') in ('confirmed_open','page_available') for h in c.get('hiring_signals',[]))
        rows.append({'_ui_key':'company_'+str(i),'_api_id':c['id'],'_api_ids':c.get('source_company_ids',[]),'name':esc(c['name']),'sector':esc(sector_name),'_sector_group':group,'locations':[esc(x) for x in list(dict.fromkeys(locations+old.get('locations',[])))],'team_size':'Unknown','maturity':'','hiring_status':'Application-page evidence' if opened else 'Hiring to confirm','_has_open':opened,'_bangalore':bool(c.get('flags',{}).get('bangalore')),'projects':esc(projects),'tech_stack':[esc(x) for x in list(dict.fromkeys(skills(c)+old.get('tech_stack',[])+[t for d in c.get('team_depth',[]) for t in d.get('technologies',[])]))],'domains':[esc(v) for v in old.get('domains',[])],'certifications_required':[esc(v)+' (earlier source)' for v in old.get('certifications_required',[])],'team_members':members,'highlights':notes,
                     '_hiring_playbook':{'business_reality':esc(projects),'project_phase':'Phase not established','difficulty':'Not established','salary_range':'Not disclosed · goal ₹35 LPA CTC','bangalore_intel':{'has_bangalore':bool(c.get('flags',{}).get('bangalore')),'summary':esc('Bengaluru evidence is present; confirm the actual role allocation.' if c.get('flags',{}).get('bangalore') else 'A Bengaluru assignment is not established.'),'contacts':[]},'insider_tip':esc(c.get('priority_reason') or 'Confirm the role scope, location and approved compensation with the employer.')}})
    for row,c in zip(rows,doc.get('companies',[])):
        pb=c.get('legacy_details',{}).get('_hiring_playbook',{})
        display=row['_hiring_playbook']
        for key in ('skills_to_master','pitch_to_manager'):
            display[key]=[esc('Earlier research: '+str(v)) for v in pb.get(key,[])]
        display['approach_ranking']=[{k:esc('Earlier research: '+str(v)) for k,v in item.items()} for item in pb.get('approach_ranking',[]) if isinstance(item,dict)]
    return rows

def dossiers_page(base,doc):
    original,raw,end,_=taxonomy(base)
    rows=dossier_data(base,doc)
    original=re.sub(r'<a\b[^>]*href=[\"\'][^\"\']*(?:masterclass|Masterclass)[^\"\']*[\"\'][^>]*>.*?</a>','',original,flags=re.I|re.S)
    page=original.replace('const DATA='+raw[:end],'const DATA=__SOURCED_DOSSIER_ROWS__',1)
    page=re.sub(r"(co|c)\.name\.replace\([^)]*\)",r"\1._ui_key",page)
    page=page.replace('DATA.find(c=>c.name===name)','DATA.find(c=>c._ui_key===name||c.name===name)')
    page=page.replace("return list.sort((a,b)=>(parseInt(b.team_size)||0)-(parseInt(a.team_size)||0));","return list.sort((a,b)=>Number(b._has_open)-Number(a._has_open)||a.name.localeCompare(b.name));")
    page=page.replace("const gr=list.filter(c=>{const s=c.hiring_status.toLowerCase();return s.includes('growing')||s.includes('rapidly')||s.includes('actively');}).length;","const gr=list.filter(c=>c._has_open).length;")
    page=page.replace("const hi=list.filter(c=>c.maturity&&(c.maturity.toLowerCase().includes('high')||c.maturity.toLowerCase().includes('very'))).length;","const hi=list.filter(c=>c._bangalore).length;")
    page=page.replace('Actively Growing','Application-page evidence').replace('High Maturity','Bengaluru connections').replace('Team Members','People / Profile Records').replace('Members Profiled','People / Profile Records').replace(' confirmed)</h3>',' documented)</h3>').replace('members profiled','profiles documented').replace('team members profiled','professional profiles documented')
    page=page.replace('~','').replace('>Current</span>','>Source observation</span>').replace('Bangalore Pega Team — Confirmed Presence','Bengaluru connection observed').replace('Expected:','Employer pay:').replace('Insider Tip','Research note')
    page=page.replace('What They Are Actually Doing With Pega','Work described in the sources')
    page=page.replace('Pega usage confirmed via job postings, customer stories, or LinkedIn signals. Estimated team:','See the sourced claims below. Current team size:').replace("+' developers.</p>","+'.</p>")
    page=page.replace("function filterSector(s){activeSector=s;activeCompany=null;renderSidebar();showDashboard();}","function filterSector(s){activeSector=s;activeCompany=null;switchView(viewMode);}")
    page=page.replace("function applySearch(){renderSidebar();if(activeCompany)return;viewMode==='dashboard'?showDashboard():showAllDossiers();}","function applySearch(){activeCompany=null;renderSidebar();viewMode==='dashboard'?showDashboard():showAllDossiers();}")
    page=page.replace('Pega_Career_Intelligence_Hub.html','/library/career-hub')
    page=page.replace("renderSidebar();showDashboard();\n</script>", """document.getElementById('sCo').textContent=DATA.length;
document.getElementById('sPpl').textContent="""+str(len(doc.get('people',[])))+""";
document.getElementById('sGrow').textContent=DATA.filter(c=>c._has_open).length;
renderSidebar();showDashboard();
const wanted=new URLSearchParams(location.hash.slice(1)).get('company');
if(wanted){const company=DATA.find(c=>c._api_id===wanted||(c._api_ids||[]).includes(wanted));if(company)openCompany(company._ui_key);}
</script>""")
    page=page.replace(' growing',' application-page signals')
    page=re.sub(r'<title>.*?</title>','<title>Pega Deep Dossiers</title>',page)
    page=page.replace('target="_blank"','target="_blank" rel="noopener noreferrer"')
    return page.replace('__SOURCED_DOSSIER_ROWS__',json.dumps(rows,ensure_ascii=False).replace('<','\\u003c'))

def table(headers,rows):
    return '<div class="table-wrap"><table class="tbl searchable"><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+cell+'</td>' for cell in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def career_page(base,doc,profile):
    soup=BeautifulSoup((base/'Pega_Career_Intelligence_Hub.html').read_text(encoding='utf-8'),'html.parser')
    _,_,_,tax=taxonomy(base)
    originals={sec.get('id'):str(sec) for sec in soup.select('.content > section')}
    companies=doc.get('companies',[])
    ordered=sorted(companies,key=lambda c:(-int(c.get('flags',{}).get('employer_job',False)),-int(c.get('flags',{}).get('bangalore',False)),c['name']))
    def company_table(rows):
        return table(['Company','Sector','Documented work','Location / people','Next step'],[[ '<a class="co" href="/library/dossiers#company='+esc(c['id'])+'">'+esc(c['name'])+'</a>',esc(sector(c,tax)[0]),'<br>'.join(esc(claim_text(x))+' '+a('Source',x.get('source_url')) for x in claims(c)[:2]) or 'Project scope not established',esc('Bengaluru connection' if c.get('flags',{}).get('bangalore') else 'Location to confirm')+'<br>'+str(len(people(c,doc)))+' public profiles','<a href="/#scan">Open Job Scanner</a>'] for c in rows])
    person_table=table(['Person / employer','Role / location','Work described','Source'],[[esc(p.get('name'))+'<br>'+esc(p.get('company')),esc(p.get('title') or 'Title not exposed')+'<br>'+esc(p.get('location_as_stated') or 'Location unconfirmed'),esc(p.get('work_summary') or p.get('pega_connection'))+'<br>'+esc(', '.join(p.get('certifications',[])))+'<br>'+'<br>'.join(esc(o.get('employer_as_stated') or o.get('company'))+' · '+esc(o.get('title'))+' · '+esc(evidence(o)) for o in p.get('observations',[]) if o.get('access')=='legacy') ,a('Professional source',p.get('profile_url') or p.get('source_url'))+'<br>'+esc(evidence(p))] for p in doc.get('people',[])])
    selections={'priority':[c for c in ordered if c.get('flags',{}).get('employer_job')],'confirmed':[c for c in ordered if c.get('flags',{}).get('pega')],'probable':[c for c in ordered if not c.get('flags',{}).get('employer_job')],'global':[c for c in ordered if c.get('category')=='global'],'remote-intel':[c for c in ordered if c.get('flags',{}).get('india_remote_lead')],'reverse-search':[c for c in ordered if people(c,doc)],'auto':[c for c in ordered if sector(c,tax)[1]=='Automotive & Industrial'],'bfsi':[c for c in ordered if sector(c,tax)[1]=='Banking & Financial Services'],'health':[c for c in ordered if sector(c,tax)[1]=='Insurance, Healthcare & Pharma'],'telecom':[c for c in ordered if sector(c,tax)[1] in ('Telecom & Media','Technology','Consumer, Retail & FMCG')],'team-ranking':ordered,'team-dossiers':[c for c in ordered if claims(c)]}
    titles={'overview':'Pega Career Intelligence Hub','confirmed':'Employers with Pega evidence','global':'Global employer research','remote-intel':'India remote leads — eligibility to confirm','reverse-search':'Companies connected to public professional profiles','team-ranking':'Teams to investigate — ordered by hiring and Bengaluru evidence','team-counts':'Documented people and team-size gaps','team-dossiers':'Team dossiers — work, technologies and people','referral-dossiers':'Public professional sources for referral research','movement-radar':'Dated professional observations','backfill':'Vacancies and replacement-hiring evidence','roadmap':'Joining and preparation'}
    for sec in soup.select('.content > section'):
        key=sec.get('id')
        heading=sec.find(['h1','h2'])
        title=titles.get(key,heading.get_text(' ',strip=True) if heading else key)
        sec.clear()
        inner='<h1>'+esc(title)+'</h1>' if key=='overview' else '<div class="head"><div class="bar"></div><h2>'+esc(title)+'</h2></div>'
        if key=='overview':inner+='<p>GCCs, consultancies and global employers. Use the original scanner to select a category and depth, run the Python search and view results.</p><p><a href="/#scan">Open Job Scanner →</a></p>'
        elif key=='team-dossiers':
            for c in selections[key]:
                inner+='<div class="card"><h3>'+esc(c['name'])+'</h3><div class="grid2"><div><p><b>Documented work:</b> '+'<br>'.join(esc(claim_text(x))+' '+a('Source',x.get('source_url')) for x in claims(c))+'</p></div><div><p><b>Technologies mentioned:</b> '+esc(', '.join(skills(c)) or 'Not established')+'</p><p><b>People documented:</b> '+str(len(people(c,doc)))+'</p><p><a href="/library/dossiers#company='+esc(c['id'])+'">Open full dossier</a></p></div></div></div>'
        elif key in selections:inner+=company_table(selections[key])
        elif key=='profile':inner+='<div class="profile"><div class="card"><div class="call"><h3>Professional headline</h3><p>Pega CSSA · Kafka · REST / SOAP · SQL · Auto finance · Production automation</p></div><div class="facts"><div><b>Experience</b><span>Four years at Mercedes-Benz R&amp;D India</span></div><div><b>Delivery</b><span>Pega application and integration development</span></div><div><b>Production</b><span>Monitoring, recovery and release ownership</span></div></div></div><div class="card"><h3>Role families to explore</h3><ol><li>Pega developer / senior developer</li><li>Pega integration or platform engineer</li><li>Workflow and BPM engineer</li><li>Automation / integration engineer</li></ol><div class="call green"><h3>Interview positioning</h3><p>Explain the business problem, your contribution, design decisions and measured results using your resume.</p></div></div></div>'
        elif key=='pay':inner+=table(['Current total package','TCS offered total','Search floor','Final total CTC goal'],[['₹'+str(round(profile['current_ctc']/1e5,2))+' LPA','₹'+str(round(profile['tcs']['total']/1e5,2))+' LPA','₹20 LPA+','₹35 LPA']])+'<p>Undisclosed salary remains a lead to confirm. Fixed pay and total CTC are separate.</p>'
        elif key in ('contacts','referral-dossiers'):inner+=person_table
        elif key=='team-counts':inner+=table(['Company','Public profiles documented','Current Pega team size'],[[esc(c['name']),str(len(people(c,doc))),'Unknown'] for c in ordered])
        elif key=='movement-radar':
            moves=[x for c in ordered for x in c.get('claims',[]) if x.get('type')=='employee_move']
            inner+='<p>A source observation is not a complete employment history.</p>'+table(['Observation','Source / date'],[[esc(claim_text(x)),a('Source',x.get('source_url'))+' '+esc(evidence(x))] for x in moves])
        elif key=='backfill':
            inner+='<p>A departure does not establish an approved replacement vacancy.</p>'+table(['Company','Hiring source','Status / checked'],[[esc(c['name']),a(h.get('title') or 'Hiring lead',h.get('url')),esc(h.get('status'))+' · '+esc(h.get('checked_at'))] for c in ordered for h in c.get('hiring_signals',[])])
        elif key=='rejected':inner+='<p>Team sizes, growth, salary budgets and replacement vacancies are not inferred. Open a dossier for the source-specific limitations.</p>'
        elif key=='outreach':inner+='<div class="templates"><div class="template"><h3>Referral peer</h3><p>Hi [Name], I’m a Pega CSSA developer with four years of experience at Mercedes-Benz R&amp;D India, working on Pega delivery, integrations and production automation. I saw [specific role or documented work]. Could you help me understand the team’s scope and whether the opening fits my background?</p></div><div class="template"><h3>Recruiter with role ID</h3><p>Hi [Name], I am interested in [role and requisition]. My background covers Pega, Kafka / API integration and production ownership. Could you confirm the role scope, experience requirement and approved CTC range?</p></div></div>'
        elif key=='roadmap':inner+='<p>TCS joining: 02 December 2026. Reporting time: 08:00 AM. Await the manual joining invite for the reporting location.</p><p><a href="/static/Pega_Interview_Handbook.html?edition=3&amp;layout=wide">Open your complete interview material</a></p>'
        elif key=='sources':inner+='<p>Company and people information comes from the current independent research. Project and professional observations retain source dates and access limitations in the dossiers. A query without matches does not establish that no vacancy exists.</p>'
        preserved={'probable','global','remote-intel','reverse-search','rejected','auto','bfsi','health','telecom','team-ranking','team-counts','team-dossiers','movement-radar','backfill','outreach','roadmap','sources','priority','confirmed'}
        if key in preserved and key in originals:
            original_section=BeautifulSoup(originals[key],'html.parser').find('section')
            # The old tables and diagrams remain visible; their estimates are explicitly dated-source notes.
            original_section.insert(0,BeautifulSoup('<p class="call">Earlier research retained below; names, estimates and hiring claims need rechecking. Dated public findings are in <a href="/library/dossiers">Deep Dossiers</a>.</p>','html.parser'))
            for node in list(original_section.contents):sec.append(node)
            if key in ('priority','confirmed','remote-intel'):
                sec.append(BeautifulSoup('<h3>Latest public-source observations</h3>'+company_table(selections[key]),'html.parser'))
        else:
            sec.append(BeautifulSoup(inner,'html.parser'))
    metrics=soup.select_one('.content > .metrics')
    if metrics:
        metrics.clear()
        for value,label in [(len(companies),'Companies / search targets'),(doc.get('stats',{}).get('people_records',0),'Profiles / named contacts'),(doc.get('stats',{}).get('bangalore_companies',0),'Bengaluru connections')]:
            metrics.append(BeautifulSoup('<div class="metric"><strong>'+esc(value)+'</strong><span>'+label+'</span></div>','html.parser'))
    for link in soup.find_all('a',href=True):
        href=link['href']
        if 'masterclass' in href.lower() or 'interview masterclass' in link.get_text(' ',strip=True).lower():
            link.decompose();continue
        if 'Pega_Deep_Dossiers' in href or href.endswith('/intel'):link['href']='/library/dossiers'
        elif 'Consulting_Intelligence' in href:link['href']='/#scan'
        elif 'localhost:5050' in href:link['href']='/#scan'
    for link in soup.select('.sidebar a[href="#confirmed"]'):link.string='Pega employer evidence'
    for link in soup.select('.sidebar a[href="#team-ranking"]'):link.string='Team research priorities'
    for stamp in soup.select('.stamp'):stamp.string='Research checked '+str(doc.get('research_date') or 'date unknown')
    return str(soup)
