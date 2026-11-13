'use strict';
window.JobWorkspace = (() => {
    const element = (tag, className, value) => {
        const result = document.createElement(tag);
        result.className = className;
        if (value !== undefined) result.textContent = String(value);
        return result;
    };
    const link = (label, url) => {
        const result = element('a', 'workspace-link', label);
        try {
            const parsed = new URL(url);
            if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password) return element('span', '', label);
            result.href = parsed.href;
            result.target = '_blank';
            result.rel = 'noopener noreferrer';
        } catch { return element('span', '', label); }
        return result;
    };
    function compensation(job) {
        const salary = job.salary;
        if (!salary || !Number.isFinite(salary.amount_min)) return 'Undisclosed';
        const amount = value => new Intl.NumberFormat('en-IN', {maximumFractionDigits: 1}).format(value);
        const range = amount(salary.amount_min) + (Number.isFinite(salary.amount_max) ? '–' + amount(salary.amount_max) : '+');
        return [salary.currency ?? 'Currency unconfirmed', range, salary.period ?? 'Period unconfirmed', salary.basis ?? 'Basis unconfirmed'].join(' · ');
    }
    const stages = [['unreviewed','Not reviewed'],['shortlisted','Interested'],['contacted','Recruiter contacted'],['applied','Applied'],['interviewing','Interviewing'],['offer','Offer'],['dismissed','Not relevant / rejected']];
    const stageLabel = value => (stages.find(item => item[0] === value) ?? stages[0])[1];
    function statusSelect(stage, name) {
        const select = element('select', 'application-select');
        select.setAttribute('aria-label', name);
        for (const [value, label] of stages) {
            const option = element('option', '', label);
            option.value = value;
            select.append(option);
        }
        select.value = stages.some(([value]) => value === stage) ? stage : 'unreviewed';
        return select;
    }
    function table(jobs, openDetail, openDossier, savePipeline) {
        const wrapper = element('div', 'job-table-scroll workspace');
        wrapper.tabIndex = 0;
        wrapper.setAttribute('role', 'region');
        wrapper.setAttribute('aria-label', 'Job opportunities');
        const table = element('table', 'jtbl');
        const head = table.createTHead().insertRow();
        for (const label of ['Role / employer', 'Location / arrangement', 'Experience / level', 'Compensation', 'Your application']) {
            const heading = element('th', '', label);heading.scope = 'col';head.append(heading);
        }
        const body = table.createTBody();
        for (const job of jobs) {
            const row = body.insertRow();
            const role = row.insertCell();
            role.append(link(job.title, job.url));
            const employer = element(openDossier ? 'button' : 'div', 'workspace-employer', job.company);
            if (openDossier) {
                employer.type = 'button';
                employer.addEventListener('click', () => openDossier(job.company));
            }
            role.append(employer, element('span', 'workspace-tag', ({gcc:'GCC', product:'Product', services:'Consulting / SI'})[job.category] ?? 'Employer type unconfirmed'));
            if (job.is_new) role.append(element('span', 'workspace-tag', 'Newly discovered'));
            const location = row.insertCell();
            location.append(element('div', '', job.location ?? 'Location unconfirmed'),element('small', '', job.work_mode ?? 'Work arrangement unconfirmed'));
            const fit = row.insertCell();
            const assessment = job.recommendation ?? {};
            fit.append(element('div', '', assessment.experience_label ?? 'Experience unverified'),
                element('span', 'workspace-tag', job.level ?? 'Level unconfirmed'),
                element('small', '', ({recommended:'Match to assessment policy',stretch:'Stretch',excluded:'Outside assessment policy',review:'Needs verification'})[assessment.status] ?? 'Needs verification'));
            row.insertCell().textContent = compensation(job);
            const evidence = row.insertCell();
            const currentStage = job.pipeline?.stage ?? 'unreviewed';
            const statusWrap = element('div', 'application-cell');
            if (savePipeline) {
                const label = element('label', 'application-label', 'Status');
                const selectWrap = element('span', 'application-select-wrap');
                const select = statusSelect(currentStage, 'Application status for '+(job.title ?? 'job'));
                const feedback = element('span', 'application-feedback');
                feedback.setAttribute('role', 'status');
                select.addEventListener('change', () => savePipeline(job, select.value, job.pipeline?.notes ?? '', select, feedback));
                selectWrap.append(select);label.append(selectWrap);statusWrap.append(label, feedback);
            } else statusWrap.append(element('strong', 'application-current '+currentStage, stageLabel(currentStage)));
            if (job.pipeline?.notes) statusWrap.append(element('span', 'application-note-flag', 'Notes saved'));
            evidence.append(statusWrap, element('div', 'source-line', job.source ?? 'Source unconfirmed'),element('small', '', 'Checked: '+(job.checked_at ?? 'Not checked')));
            const button = element('button', 'btn-job-detail', 'View description');button.type = 'button';
            button.addEventListener('click', () => openDetail(job,button));evidence.append(button);
            const sources = job.sources ?? [];
            if (sources.length > 1) {
                const details = element('details', 'workspace-sources');
                details.append(element('summary', '', sources.length+' source observations'+(job.match_basis==='probable'?' · probable match':'')));
                for (const source of sources) details.append(link(source.source,source.url));
                evidence.append(details);
            }
        }
        wrapper.append(table);return wrapper;
    }
    return {table,stages,statusSelect};
})();
