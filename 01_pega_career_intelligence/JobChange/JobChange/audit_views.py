"""Readable source reviews within the original Dossiers and Career Hub components."""
import html
import re
from urllib.parse import urlsplit


def esc(value):
    return html.escape(str(value or ''), quote=True)


def value_text(value):
    if isinstance(value, dict):
        return str(value.get('summary') or value.get('basis') or value.get('text') or '')
    if isinstance(value, list):
        return '; '.join(value_text(x) for x in value)
    return str(value or '')


def safe_url(url):
    try:
        p = urlsplit(str(url or ''))
        return str(url) if p.scheme in ('http', 'https') and p.hostname else ''
    except ValueError:
        return ''


def link(label, url):
    url = safe_url(url)
    return '<a href="' + esc(url) + '" target="_blank" rel="noopener noreferrer">' + esc(label) + '</a>' if url else esc(label)


def verdict(review):
    return {
        'corroborated': 'Profile details supported by the cited source',
        'partially_supported': 'Some profile details supported; gaps remain',
        'unresolved': 'Identity or claimed details not established',
        'conflicting': 'Conflicting identity or employment evidence',
        'not_a_person': 'Search lead or placeholder; not an identified person',
        'reviewed': 'Company source review completed',
        'no_public_evidence': 'No supporting match in the recorded checks',
        'ambiguous': 'Company or project allocation remains ambiguous',
    }.get(review.get('status'), 'Review recorded')


def sources_html(review):
    parts = []
    for source in review.get('sources', []):
        access = 'Page read' if source.get('access') == 'page' else 'Search-index evidence' if source.get('access') == 'search_index' else 'Access unconfirmed'
        stamp = source.get('checked_at') or review.get('checked_at') or 'date unknown'
        parts.append('<li>' + link(source.get('title') or 'Public source', source.get('url') or source.get('source_url')) +
                     ' · ' + esc(access) + ' · checked ' + esc(stamp) +
                     (' · source dated ' + esc(source['source_date']) if source.get('source_date') else '') +
                     ('<br>' + esc(source['summary']) if source.get('summary') else '') + '</li>')
    result = '<ul class="hi">' + ''.join(parts) + '</ul>' if parts else '<p>No supporting public source was established by these checks.</p>'
    checks = review.get('checks', [])
    if checks:
        result += '<details><summary>Checks performed (' + str(len(checks)) + ')</summary><ul class="hi">'
        for check in checks:
            result += '<li>' + esc(check.get('query') or check.get('url') or 'Source check') + '<br>' + esc(value_text(check.get('outcome'))) + '</li>'
        result += '</ul></details>'
    return result


def profile_display(person):
    review = person.get('deep_audit')
    if not review:
        return person
    display = dict(person)
    display['name'] = {'Sam Sundar — current Pega developer': 'Sam Sundar', 'Sibaram Siba — Pega Developer': 'Sibaram Siba'}.get(person.get('name'), person.get('name'))
    for key in ('title', 'location_as_stated', 'pega_connection', 'work_summary'):
        display[key] = review.get(key)
    display['company'] = review.get('employer_as_stated') or 'Employer not established in this review'
    display['certifications'] = review.get('certifications') or []
    display['work_summary'] = review.get('work_summary') or review.get('summary') or verdict(review)
    display['checked_at'] = review.get('checked_at')
    primary = next((x for x in review.get('sources', []) if x.get('url') == review.get('profile_url')), None)
    primary = primary or next(iter(review.get('sources', [])), {})
    display['access'] = primary.get('access', 'unknown')
    display['source_date'] = primary.get('source_date')
    display['source_url'] = primary.get('url')
    # Saved links remain in the historical record; never relabel them as freshly read.
    display['profile_url'] = review.get('profile_url') if review.get('status') in ('corroborated', 'partially_supported', 'conflicting') else None
    return display


def profile_review_html(person):
    review = person.get('deep_audit')
    if not review:
        return ''
    professional = '<p><b>Employer as stated:</b> ' + esc(review.get('employer_as_stated') or 'Not established') + '<br><b>Location as stated:</b> ' + esc(review.get('location_as_stated') or 'Not established') + '</p>'
    saved = person.get('profile_url')
    historical_link = '<details><summary>Saved profile link</summary>' + link('Earlier saved profile (identity may be unresolved)', saved) + '</details>' if saved and saved != profile_display(person).get('profile_url') else ''
    if profile_display(person).get('name') != person.get('name'):
        historical_link += '<details><summary>Earlier record label</summary>' + esc(person.get('name')) + '</details>'
    return professional + historical_link + '<p><b>' + esc(verdict(review)) + '</b> · ' + esc(review.get('checked_at')) + '</p><p>' + esc(review.get('summary')) + '</p>' + sources_html(review) + ('<p>' + esc(value_text(review.get('limitations'))) + '</p>' if review.get('limitations') else '')


def company_summary(company):
    review = company.get('deep_audit')
    if not review:
        return None
    return value_text(review.get('pega_work')) or value_text(review.get('summary'))


def company_card(company):
    review = company.get('deep_audit')
    if not review:
        return ''
    items = [
        ('Pega work', review.get('pega_work')),
        ('India delivery / employer', review.get('india_scope')),
        ('Bengaluru scope', review.get('bangalore_scope')),
        ('Company type', review.get('entity_type')),
        ('Fit for your experience', review.get('role_fit')),
        ('Current team size', review.get('team_size') or 'Not established'),
        ('Compensation', review.get('salary') or 'Not disclosed'),
    ]
    body = '<div class="card"><h3>' + esc(company['name']) + '</h3><p><b>' + esc(verdict(review)) + '</b> · ' + esc(review.get('checked_at')) + '</p><p>' + esc(review.get('summary')) + '</p><div class="grid2">'
    for label, value in items:
        body += '<div><p><b>' + esc(label) + ':</b> ' + esc(value_text(value) or 'Not established by the checked sources') + '</p></div>'
    body += '</div>' + sources_html(review)
    if review.get('questions_to_ask'):
        body += '<p><b>Confirm with the team:</b></p><ul>' + ''.join('<li>' + esc(value_text(q)) + '</li>' for q in review['questions_to_ask']) + '</ul>'
    if review.get('limitations'):
        body += '<p>' + esc(value_text(review['limitations'])) + '</p>'
    return body + '<p><a href="/library/dossiers#company=' + esc(company['id']) + '">Open company and profile details</a></p></div>'


def apply_dossier(company, row, people):
    review = company.get('deep_audit')
    if not review:
        return
    summary = company_summary(company)
    row['_bangalore'] = review.get('bangalore_connection_supported') is True
    row['locations'] = ['Bengaluru connection supported' if row['_bangalore'] else 'See reviewed location scope']
    row['projects'] = esc(summary)
    row['tech_stack'] = [esc(value_text(t)) for t in review.get('technologies', [])]
    row['domains'] = [esc(value_text(t)) for t in review.get('domains', [])]
    row['certifications_required'] = [esc(value_text(t)) for t in review.get('certifications_required', [])]
    old = row['highlights']
    row['highlights'] = [company_card(company)]
    if old:
        row['highlights'].append('<details><summary>Earlier findings and original notes (' + str(len(old)) + ')</summary><ul class="hi">' + ''.join('<li>' + x + '</li>' for x in old) + '</ul></details>')
    playbook = row['_hiring_playbook']
    playbook['business_reality'] = esc(summary)
    playbook['project_phase'] = esc(value_text(review.get('project_phase')) or 'Project phase not established')
    playbook['difficulty'] = 'Role-specific'
    playbook['salary_range'] = esc(value_text(review.get('salary')) or 'Not disclosed')
    playbook['insider_tip'] = esc(value_text(review.get('role_fit')) or 'Review the exact role requirements.')
    playbook['bangalore_intel'] = {
        'has_bangalore': row['_bangalore'],
        'summary': esc(value_text(review.get('bangalore_scope')) or 'Bengaluru project allocation not established.'),
        'contacts': [],
    }
    playbook['skills_to_master'] = [esc(value_text(t)) for t in review.get('technologies', [])]
    playbook['pitch_to_manager'] = [esc(value_text(t)) for t in review.get('questions_to_ask', [])]
    playbook['approach_ranking'] = []
    row['_review_status'] = review.get('status')
    row['_review_date'] = review.get('checked_at')


def coverage_html(doc):
    audit = doc.get('gcc_audit')
    if not audit:
        return ''
    return '<p class="call"><b>GCC source review:</b> ' + str(audit['company_records_reviewed']) + '/' + str(audit['company_records_in_scope']) + ' company entries and ' + str(audit['profile_records_reviewed']) + '/' + str(audit['profile_records_in_scope']) + ' profile/contact records reviewed. Each record states the result; reviewed does not mean every earlier claim was verified.</p>'
