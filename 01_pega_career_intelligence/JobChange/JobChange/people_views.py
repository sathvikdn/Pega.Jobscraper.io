"""Compact, source-labelled professional profiles shared by both library views."""
import html
import re
from urllib.parse import urlsplit

ROLE_GROUPS = (
    ('managers', 'Managers & project owners', 1),
    ('architects', 'System & solution architects', 2),
    ('leads', 'Technical & team leads', 3),
    ('developers', 'Developers & engineers', 4),
    ('other', 'Other roles / role unconfirmed', 5),
    ('historical', 'Earlier roles / other employer', 6),
)

PEOPLE_CSS = """
.people-groups{display:grid;gap:16px;margin:12px 0}.people-group>h4{margin:0 0 8px;font-size:14px}.people-group>h4 span{font-weight:400;opacity:.72}
.person-row{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:start;gap:12px;border:1px solid var(--border,#dce2e9);border-radius:8px;padding:10px 12px;margin:7px 0;background:var(--card,#fff);color:var(--text,#243347)}
.person-row details{min-width:0}.person-row summary{cursor:pointer;list-style:revert;line-height:1.5}.person-name{font-size:14px}.person-title{display:block;margin-left:18px;font-size:13px}.person-meta{display:block;margin:3px 0 0 18px;font-size:12px;opacity:.8}.person-badge{display:inline-block;font-size:11px;line-height:1.4;padding:2px 6px;border-radius:4px;background:var(--bg,#f2f5f8);margin:4px 4px 0 0}.person-profile-link{font-size:12px;font-weight:600;white-space:nowrap;padding:3px 0}.person-body{font-size:13px;line-height:1.55;padding-top:10px;overflow-wrap:anywhere}.person-body p{margin:6px 0 10px}.person-body h5{font-size:12px;text-transform:none;margin:14px 0 5px}.person-body ul{padding-left:20px;margin:6px 0 10px}.person-body li{margin-bottom:8px}.person-body details{margin:10px 0}.person-source-meta{display:block;font-size:11px;opacity:.8}.people-empty{font-size:13px;opacity:.75}
@media(max-width:560px){.person-row{gap:6px;padding:9px}.person-title,.person-meta{margin-left:0}.person-name{display:block}.person-profile-link{font-size:11px}}
"""


def _text(value):
    if isinstance(value, dict):
        return str(value.get('summary') or value.get('text') or value.get('basis') or '')
    if isinstance(value, list):
        return '; '.join(filter(None, (_text(item) for item in value)))
    return str(value or '')


def _list(value):
    return value if isinstance(value, list) else [value] if value else []


def esc(value):
    return html.escape(_text(value), quote=True)


def safe_url(value):
    value = str(value or '').strip()
    if not value or any(ord(char) < 32 for char in value) or '\\' in value:
        return ''
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
            return ''
        _ = parsed.port
        return value
    except (ValueError, TypeError):
        return ''


def linkedin_url(value):
    value = safe_url(value)
    if not value:
        return ''
    host = (urlsplit(value).hostname or '').lower()
    return value if host == 'linkedin.com' or host.endswith('.linkedin.com') else ''


def _link(label, value):
    value = safe_url(value)
    return ('<a href="' + esc(value) + '" target="_blank" rel="noopener noreferrer">' + esc(label) + '</a>') if value else esc(label)


def _key(value):
    return re.sub(r'[^a-z0-9]', '', str(value or '').lower())


def _company_names(company):
    if not company:
        return set()
    return {_key(name) for name in [company.get('name'), *_list(company.get('aliases'))] if name}


def _matches_company(observation, company):
    if not company:
        return True
    ids = {company.get('id'), *_list(company.get('source_company_ids'))} - {None}
    # Never overwrite a different stated employer with the catalogue association.
    employer = observation.get('employer_as_stated') or observation.get('company')
    if employer:
        return _key(employer) in _company_names(company)
    return bool(ids.intersection({observation.get('company_id'), *_list(observation.get('company_ids'))}))


def _source_label(source):
    access = source.get('access') or source.get('profile_access')
    return {'page': 'Page read', 'search_index': 'Search-index observation', 'legacy': 'Earlier source · not reverified'}.get(access, 'Saved source · access unconfirmed')


def _source(source, default_date=None):
    return {
        'url': safe_url(source.get('url') or source.get('source_url') or source.get('profile_url')),
        'profile_url': linkedin_url(source.get('profile_url')),
        'title': _text(source.get('source_title') or source.get('source_file') or source.get('title') or 'Professional source'),
        'access_label': _source_label(source),
        'checked_at': _text(source.get('checked_at') or default_date),
        'source_date': _text(source.get('source_date')),
        'summary': _text(source.get('summary')),
    }


def _role(title, placeholder=False):
    text = title.lower()
    text = re.sub(r'\b(?:decision|deployment) manager\b', '', text)
    # A certification, seniority grade or LSA title does not prove management.
    certification_only = bool(re.search(r'employment title not exposed|^\s*(?:pega[- ]?)?(?:certified|certification)\b', text)) and not re.search(r'\b(developer|engineer|manager|product owner)\b', text)
    if placeholder or not title or certification_only:
        return ROLE_GROUPS[4]
    # Profile headlines mix held positions with qualifications. Remove an
    # explicit certification clause before checking for architecture/lead roles.
    # In 'Developer | Certified Pega System Architect', only Developer is a role.
    text = re.sub(r'\b(?:certified|certifications?)\b[^|;,/]*', '', text)
    if re.search(r'\b(manager|head of|product owner|project owner|programme owner|program owner|managing director)\b', text):
        return ROLE_GROUPS[0]
    if re.search(r'\bdirector\b', text) and re.search(r'engineering|technology|development|product|program|practice|operations|systems|crm|architecture|personalization', text):
        return ROLE_GROUPS[0]
    if re.search(r'\barchitect\b', text):
        return ROLE_GROUPS[1]
    if re.search(r'\b(?:lead|leader)\b', text) and re.search(r'team|tech|technical|engineering|developer|development|consultant|delivery|change|account|product area|ui/ux|pega|project|practice', text):
        return ROLE_GROUPS[2]
    if re.search(r'\b(developer|engineer|programmer)\b', text):
        return ROLE_GROUPS[3]
    return ROLE_GROUPS[4]


def build_person_view(person, company=None):
    """Plain view data: absent audit fields never erase saved observations."""
    review = person.get('deep_audit') or {}
    observations = [item for item in _list(person.get('observations')) if isinstance(item, dict)]
    observations = sorted(observations, key=lambda item: (item.get('access') != 'legacy', _text(item.get('checked_at') or item.get('source_date'))), reverse=True)
    relevant = [item for item in observations if _matches_company(item, company)]
    reviewed_here = bool(review) and _matches_company(review, company)
    reviewed_title = review.get('title') if reviewed_here else None
    historical = next((item for item in relevant if item.get('title')), None)
    if historical is None and _matches_company(person, company) and person.get('title'):
        historical = person
    if reviewed_title:
        title, title_basis, title_record = _text(reviewed_title), 'Reviewed title', review
    elif historical:
        title = _text(historical.get('title'))
        title_basis = 'Earlier title · not reverified' if review or historical.get('access') == 'legacy' else 'Observed title'
        title_record = historical
    elif review.get('title'):
        title, title_basis, title_record = _text(review.get('title')), 'Title at another employer', review
    else:
        title, title_basis, title_record = 'Role not established', 'Role unconfirmed', review or person
    placeholder = review.get('status') == 'not_a_person' or person.get('identity_method') in ('placeholder', 'search_lead')
    role_key, role_label, role_level = _role(title, placeholder)
    employer = _text(review.get('employer_as_stated') or title_record.get('employer_as_stated') or title_record.get('company'))
    if review.get('employer_as_stated') and not reviewed_here and company:
        relationship = 'Latest source: ' + employer + ' · association here needs confirmation'
    elif any(re.search(r'\b(former|previous|ex-)\b', _text(title_record.get(key)), re.I) for key in ('employment_status', 'relationship', 'title')):
        relationship = 'Former role recorded'
    elif review and not review.get('employer_as_stated'):
        relationship = 'Current employer unconfirmed'
    elif company:
        relationship = 'Employer named in source · dates to confirm'
    else:
        relationship = employer or 'Employer unconfirmed'
    recorded_role_key, recorded_role_label = role_key, role_label
    if company and (relationship == 'Former role recorded' or (review.get('employer_as_stated') and not reviewed_here)):
        role_key, role_label, role_level = ROLE_GROUPS[5]
    display_name = {'Sam Sundar — current Pega developer': 'Sam Sundar', 'Sibaram Siba — Pega Developer': 'Sibaram Siba'}.get(person.get('name'), person.get('name'))
    profile_candidates = [review.get('profile_url'), person.get('profile_url'), *[item.get('profile_url') for item in observations], review.get('source_url'), person.get('source_url')]
    profile = next((linkedin_url(value) for value in profile_candidates if linkedin_url(value)), '')
    reviewed_link = bool(profile and profile == linkedin_url(review.get('profile_url')) and review.get('status') in ('corroborated', 'partially_supported'))
    profile_basis = 'LinkedIn' if not review or reviewed_link else 'LinkedIn · saved'
    limitations = list(dict.fromkeys(filter(None, [_text(item) for item in _list(review.get('limitations')) + _list(person.get('limitations'))])))
    if review.get('status') in ('unresolved', 'conflicting', 'not_a_person'):
        limitations.insert(0, {'unresolved': 'Identity or current details were not established in the latest review.', 'conflicting': 'The latest review records conflicting identity or employment information.', 'not_a_person': 'This is a retained research lead, not an identified team member.'}[review['status']])
    if review and not reviewed_title and historical:
        limitations.insert(0, 'The saved title is retained for research; the latest review did not re-establish this role at this company.')
    history = []
    for item in observations or [person]:
        history.append({'employer': _text(item.get('employer_as_stated') or item.get('company')), 'title': _text(item.get('title')), 'location': _text(item.get('location_as_stated') or item.get('location')), 'work': _text(item.get('work_summary') or item.get('pega_connection')), 'limitations': _text(item.get('limitations')), 'source': _source(item), 'career': [step for step in _list(item.get('career')) if isinstance(step, dict)]})
    sources = [_source(item, review.get('checked_at')) for item in _list(review.get('sources')) if isinstance(item, dict)]
    if not sources:
        sources = [_source(title_record)]
    certifications = [{'name': _text(item), 'basis': 'Latest review'} for item in _list(review.get('certifications'))]
    seen_certifications = {_key(item['name']) for item in certifications}
    for item in _list(person.get('certifications')):
        if _key(item) not in seen_certifications:
            certifications.append({'name': _text(item), 'basis': 'Earlier source · not reverified' if review or person.get('access') == 'legacy' else 'Source observation'})
            seen_certifications.add(_key(item))
    work = _text(review.get('work_summary') or review.get('pega_connection'))
    work_basis = 'Latest review' + (' · ' + _text(review.get('employer_as_stated')) if review.get('employer_as_stated') else '')
    if not work:
        work = _text(title_record.get('work_summary') or title_record.get('pega_connection') or person.get('work_summary') or person.get('pega_connection'))
        work_basis = 'Earlier source · not reverified' if review or title_record.get('access') == 'legacy' else 'Source observation'
    search_certifications = list(dict.fromkeys([item['name'] for item in certifications] + [_text(cert) for source in observations + [item for item in _list(person.get('research_history')) if isinstance(item, dict)] for field in ('certifications', 'certs') for cert in _list(source.get(field))]))
    return {
        'person_id': _text(person.get('id') or person.get('person_id') or person.get('identity_key')),
        'company_id': _text((company or {}).get('id') or person.get('company_id')),
        'search_certifications': search_certifications,
        'name': _text(display_name) or 'Unnamed research lead', 'title': title,
        'title_basis': title_basis, 'location': _text(review.get('location_as_stated') or title_record.get('location_as_stated') or title_record.get('location')) or 'Location unconfirmed',
        'location_basis': 'Earlier location' if review and not review.get('location_as_stated') else 'Location in source',
        'employer': employer, 'relationship': relationship,
        'role_key': role_key, 'role_label': role_label, 'role_level': role_level,
        'recorded_role_key': recorded_role_key, 'recorded_role_label': recorded_role_label,
        'linkedin_url': profile, 'linkedin_label': profile_basis,
        'saved_profile_links': list(dict.fromkeys(linkedin_url(value) for value in profile_candidates if linkedin_url(value) and linkedin_url(value) != profile)),
        'source_url': next((source['url'] for source in sources if source['url']), ''),
        'work': work, 'work_basis': work_basis, 'certifications': certifications,
        'limitations': limitations, 'sources': sources, 'history': history,
        'review_summary': _text(review.get('summary')), 'review_status': _text(review.get('status')),
        'checked_at': _text(review.get('checked_at') or title_record.get('checked_at')),
        'checks': [item for item in _list(review.get('checks')) if isinstance(item, dict)],
        'research_history': [item for item in _list(person.get('research_history')) if isinstance(item, dict)],
    }


def _source_html(source):
    dates = source['access_label'] + ' · checked ' + (source['checked_at'] or 'date not recorded')
    if source['source_date']:
        dates += ' · source dated ' + source['source_date']
    return _link(source['title'], source['url']) + (' · ' + _link('Saved LinkedIn profile', source['profile_url']) if source.get('profile_url') and source['profile_url'] != source['url'] else '') + '<span class="person-source-meta">' + esc(dates) + '</span>' + ('<p>' + esc(source['summary']) + '</p>' if source['summary'] else '')


def _render_person_body(view):
    body = '<div class="person-body"><p class="person-source-meta">' + esc(view['relationship']) + '</p>'
    body += '<h5>Project / work described</h5><p>' + esc(view['work'] or "A named project and this person's responsibilities are not established in the saved sources.") + '</p>'
    if view['work']:
        body += '<span class="person-source-meta">' + esc(view['work_basis']) + '</span>'
    if view['review_summary']:
        body += '<p>' + esc(view['review_summary']) + '</p>'
    if view['certifications']:
        body += '<h5>Certifications mentioned</h5><ul>' + ''.join('<li>' + esc(item['name']) + ' <span class="person-source-meta">' + esc(item['basis']) + '</span></li>' for item in view['certifications']) + '</ul>'
    if view['limitations']:
        body += '<h5>What still needs confirming</h5><ul>' + ''.join('<li>' + esc(item) + '</li>' for item in view['limitations']) + '</ul>'
    body += '<h5>Sources & dates</h5><ul>' + ''.join('<li>' + _source_html(item) + '</li>' for item in view['sources']) + '</ul>'
    if view['history']:
        body += '<details><summary>Saved observations & career history (' + str(len(view['history'])) + ')</summary><ul>'
        for item in view['history']:
            body += '<li><b>' + esc(item['title'] or 'Title not exposed') + '</b> · ' + esc(item['employer'] or 'Employer not stated')
            if item['location']:
                body += ' · ' + esc(item['location'])
            body += '<p>' + esc(item['work']) + '</p>' + _source_html(item['source'])
            if item['limitations']:
                body += '<p>' + esc(item['limitations']) + '</p>'
            for step in item['career']:
                body += '<p><b>' + esc(step.get('role')) + '</b> · ' + esc(step.get('company')) + ' · ' + esc(step.get('dates')) + '<br>' + esc(step.get('location')) + ' ' + esc(step.get('detail')) + '</p>'
            body += '</li>'
        body += '</ul></details>'
    if view['saved_profile_links']:
        body += '<details><summary>Earlier saved profile links</summary><ul>' + ''.join('<li>' + _link('Earlier saved LinkedIn profile', url) + '</li>' for url in view['saved_profile_links']) + '</ul></details>'
    if view['research_history']:
        body += '<details><summary>Earlier source reviews (' + str(len(view['research_history'])) + ')</summary><ul>'
        for earlier in view['research_history']:
            body += '<li>' + esc(earlier.get('summary') or earlier.get('work_summary')) + '<br>' + esc(earlier.get('title')) + ' · ' + esc(earlier.get('employer_as_stated')) + ' · ' + esc(earlier.get('checked_at'))
            body += '<ul>' + ''.join('<li>' + _source_html(_source(source, earlier.get('checked_at'))) + '</li>' for source in _list(earlier.get('sources')) if isinstance(source, dict)) + '</ul></li>'
        body += '</ul></details>'
    if view['checks']:
        body += '<details><summary>Source checks (' + str(len(view['checks'])) + ')</summary><ul>' + ''.join('<li>' + esc(item.get('query') or item.get('url')) + '<br>' + esc(item.get('outcome')) + '</li>' for item in view['checks']) + '</ul></details>'
    body += '</div>'
    return body


def render_person(view, include_details=True):
    body = _render_person_body(view) if include_details else '<div class="person-body"></div>'
    short_location = view['location'] + (' · earlier location' if view['location_basis'] == 'Earlier location' else '')
    summary = '<summary><strong class="person-name">' + esc(view['name']) + '</strong><span class="person-title">' + esc(view['title']) + '</span><span class="person-meta">' + esc(short_location) + '</span><span class="person-badge">' + esc(view['title_basis']) + '</span>' + ('<span class="person-meta">' + esc(view['relationship']) + '</span>' if view['relationship'] != 'Employer named in source · dates to confirm' else '') + '</summary>'
    if view['linkedin_url']:
        profile = '<span class="person-profile-link">' + _link(view['linkedin_label'], view['linkedin_url']) + '</span>'
    elif view['source_url']:
        profile = '<span class="person-profile-link">' + _link('Source', view['source_url']) + '</span>'
    else:
        profile = '<span class="person-profile-link">No profile link</span>'
    return '<article class="person-row pv-person" data-location="' + esc(view['location']) + '" data-search="' + esc(' '.join([view['name'], view['title'], view['employer'], view['work'], view['location'], *view.get('search_certifications', [item['name'] for item in view['certifications']])])) + '" data-role="' + esc(view['role_key']) + '" data-person-id="' + esc(view.get('person_id')) + '" data-company-id="' + esc(view.get('company_id')) + '"><details' + (' data-profile-lazy="true"' if not include_details else '') + '>' + summary + body + '</details>' + profile + '</article>'


def render_profile(person, company=None, include_details=True):
    return render_person(build_person_view(person, company), include_details=include_details)


def linked_people(company, people):
    ids = {company.get('id'), *_list(company.get('source_company_ids'))} - {None}
    return [person for person in people if ids.intersection({person.get('company_id'), *_list(person.get('company_ids'))})]


def group_people(people, company=None):
    views = [build_person_view(person, company) for person in people]
    return [{'key': key, 'label': label, 'level': level, 'people': sorted([view for view in views if view['role_key'] == key], key=lambda view: view['name'].casefold())} for key, label, level in ROLE_GROUPS if any(view['role_key'] == key for view in views)]


def render_groups(groups, include_details=True):
    if not groups:
        return '<p class="people-empty">No named professional profiles are saved for this company yet.</p>'
    return '<div class="people-groups">' + ''.join('<section class="people-group pv-group"><h4>' + esc(group['label']) + ' <span>(' + str(len(group['people'])) + ')</span></h4>' + ''.join(render_person(view, include_details=include_details) for view in group['people']) + '</section>' for group in groups) + '</div>'


def render_company_people(company, people, include_details=True):
    return render_groups(group_people(linked_people(company, people), company), include_details=include_details)
