
// Minimal, stable JS for submission edit page
console.log("TEST: submission-form.js loaded");
// Restores: tab navigation, Projects & Activities add/delete, and globals expected by the templates

document.addEventListener('DOMContentLoaded', function() {
  'use strict';

  function byId(id) { return document.getElementById(id); }

  // ---------------- Tab nav + form wiring ----------------
  function initTabsAndForm() {
    const form = byId('submission-form');
    if (!form) return;

    // Diagnostic: log all DELETE inputs present in the form before submit
    form.addEventListener('submit', function(ev) {
      const deleteInputs = Array.from(form.querySelectorAll('input[type="hidden"][name$="-DELETE"]'));
      console.log('DIAGNOSTIC: DELETE inputs before submit:', deleteInputs.map(i => i.name + '=' + i.value));
      const totals = Array.from(form.querySelectorAll('input[name$="-TOTAL_FORMS"]')).map(i => i.name + '=' + i.value);
      console.log('DIAGNOSTIC: TOTAL_FORMS:', totals.join(', '));
      // Serialize competencies paragraph (enumerated 1-4) directly stored in textarea
      document.querySelectorAll('.llc-section').forEach(section => {
        const ta = section.querySelector('textarea.llc-storage');
        if (!ta) return;
        // Clean trailing blank enumerated lines (e.g. "1. \n2. \n")
        const cleaned = ta.value.split(/\n/).map(l => l.trim()).filter(l => l && /\d+\./.test(l));
        // Preserve original formatting if user entered paragraphs; else rebuild numbered list
        if (cleaned.length) {
          ta.value = cleaned.join('\n');
        }
      });
      // Serialize reasons selections
      document.querySelectorAll('.reasons-section').forEach(section => {
        const hiddenCodes = section.querySelector('input[type="hidden"][name$="-non_mastery_reasons"]');
        if (!hiddenCodes) return;
        const codes = [];
        section.querySelectorAll('input.reason-choice:checked').forEach(cb => codes.push(cb.value));
        hiddenCodes.value = codes.join(',');
        const otherHidden = section.querySelector('textarea[name$="-non_mastery_other"]');
        const otherVisible = section.querySelector('.reason-other textarea');
        if (otherHidden && otherVisible) otherHidden.value = (otherVisible.value || '').trim();
      });

      // Serialize remediation interventions table to JSON stored in hidden interventions-storage
      document.querySelectorAll('.interventions-plan').forEach(section => {
        const storage = section.querySelector('textarea.interventions-storage');
        if (!storage) return;
        const subjectContent = section.closest('.subject-content');
        if (!subjectContent) return;
        const selected = Array.from(subjectContent.querySelectorAll('.reasons-section input.reason-choice:checked')).map(cb => {
          const labelSpan = cb.closest('label') && cb.closest('label').querySelector('span');
          const label = labelSpan ? labelSpan.textContent.trim() : (cb.closest('label') ? cb.closest('label').textContent.trim() : cb.value);
          return { code: cb.value, reason: label };
        });
        const data = selected.map(item => {
          const ta = section.querySelector(`.interventions-pairs textarea.intervention-textarea[data-reason-code="${item.code}"]`);
          const intervention = ta ? (ta.value || '').trim() : '';
          return { code: item.code, reason: item.reason, intervention };
        });
        try { storage.value = JSON.stringify(data); } catch (e) { storage.value = ''; }
      });
      // Serialize Reading Difficulties & Interventions (new structured builder)
      const rdStorage = document.querySelector('.reading-difficulties-storage');
      if (rdStorage) {
        const data = [];
        document.querySelectorAll('.reading-difficulty-grade').forEach(gradeEl => {
          const grade = gradeEl.getAttribute('data-grade');
          const pairs = [];
          gradeEl.querySelectorAll('.reading-difficulty-pair').forEach(pairEl => {
            const diffTa = pairEl.querySelector('textarea.reading-difficulty-textarea');
            const intTa = pairEl.querySelector('textarea.reading-intervention-textarea');
            const difficulty = diffTa ? (diffTa.value || '').trim() : '';
            const intervention = intTa ? (intTa.value || '').trim() : '';
            if (difficulty || intervention) {
              pairs.push({ difficulty, intervention });
            }
          });
          data.push({ grade, pairs });
        });
        try { rdStorage.value = JSON.stringify(data); } catch(e) { rdStorage.value = '[]'; }
      }

      // Serialize new RMA difficulties (Pre-Test Q3 and EOSY Q1)
      function serializeRMA(selectorStorage, selectorPlan) {
        const storage = document.querySelector(selectorStorage);
        const planRoot = document.querySelector(selectorPlan);
        if (!storage || !planRoot) return;
        const data = [];
        planRoot.querySelectorAll('.rma-difficulty-grade').forEach(gradeEl => {
          const grade = gradeEl.getAttribute('data-grade');
          const pairs = [];
          gradeEl.querySelectorAll('.rma-difficulty-pair').forEach(pairEl => {
            const diffTa = pairEl.querySelector('textarea.rma-difficulty-textarea');
            const intTa = pairEl.querySelector('textarea.rma-intervention-textarea');
            const difficulty = diffTa ? (diffTa.value || '').trim() : '';
            const intervention = intTa ? (intTa.value || '').trim() : '';
            if (difficulty || intervention) pairs.push({ difficulty, intervention });
          });
          data.push({ grade, pairs });
        });
        try { storage.value = JSON.stringify(data); } catch (e) { storage.value = '[]'; }
      }
      serializeRMA('.rma-pretest-storage', '.rma-pretest-plan');
      serializeRMA('.rma-eosy-storage', '.rma-eosy-plan');
    });
    const canEdit = (form.dataset.canEdit === '1');
    const nextTabInput = byId('id_next_tab');
    const autosaveInput = byId('id_autosave');
    const skipValidationInput = byId('id_skip_validation');

    // Guard corrupted action
    document.addEventListener('submit', function(ev) {
      try {
        const f = ev.target;
        if (f && typeof f.action === 'string' && f.action.indexOf('[object') !== -1) {
          f.removeAttribute('action');
        }
      } catch (e) {}
    });

    // Tab buttons
    document.querySelectorAll('.tab-nav').forEach(btn => {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        const target = this.dataset.navTarget;
        if (!target) return;
        if (!canEdit) {
          const url = new URL(window.location.href);
          url.searchParams.set('tab', target);
          window.location.assign(url.toString());
          return;
        }
        if (nextTabInput) nextTabInput.value = target;
        if (skipValidationInput) skipValidationInput.value = '1';
        if (autosaveInput) autosaveInput.value = '1';
        form.submit();
      });
    });
  }

  // ---------------- Projects ----------------
  function renumberProjects() {
    const sections = Array.from(document.querySelectorAll('.project-section'));
    const totalInput = document.querySelector('input[name="projects-TOTAL_FORMS"]');
    if (totalInput) totalInput.value = String(sections.length);
    sections.forEach((section, idx) => {
      section.setAttribute('data-project-index', String(idx));
              // Log the bin contents immediately after appending
              console.log('DIAGNOSTIC: bin.innerHTML after append', bin.innerHTML);
      section.querySelectorAll('input[name^="projects-"], select[name^="projects-"]').forEach(el => {
        const name = el.getAttribute('name');
        const id = el.getAttribute('id') || '';
        if (name) el.setAttribute('name', name.replace(/^projects-\d+-/, `projects-${idx}-`));
        if (id) el.setAttribute('id', id.replace(/^id_projects-\d+-/, `id_projects-${idx}-`));
      });
    });
  }

  function handleProjectDeleteButtonClick(e) {
    const section = e.target.closest('.project-section');
    if (!section) return;
    const del = section.querySelector('input[name^="projects-"][name$="-DELETE"]');
    if (!del) return;
    del.checked = true;
    handleProjectDelete({ target: del });
  }

  function handleProjectDelete(e) {
    const checkbox = e.target;
    const section = checkbox.closest('.project-section');
    const form = byId('submission-form');
    const totalFormsInput = document.querySelector('input[name="projects-TOTAL_FORMS"]');
    const hiddenIdInput = section ? section.querySelector('input[name^="projects-"][name$="-id"]') : null;
    const idxMatch = hiddenIdInput && hiddenIdInput.name ? hiddenIdInput.name.match(/^projects-(\d+)-id$/) : null;
    const projectIndex = idxMatch ? parseInt(idxMatch[1], 10) : (section ? parseInt(section.getAttribute('data-project-index') || '0', 10) : 0);

    if (checkbox.checked) {
      if (!confirm('Are you sure you want to remove this project? All activities will also be removed.')) { checkbox.checked = false; return; }

      if (hiddenIdInput && hiddenIdInput.value) {
        // Existing: keep minimal hidden deleted form and remove section immediately
        let bin = form ? form.querySelector('#project-delete-bin') : null;
        if (!bin && form) { bin = document.createElement('div'); bin.id='project-delete-bin'; bin.style.display='none'; form.appendChild(bin); }
        if (bin) {
          const delName = `projects-${projectIndex}-DELETE`;
          const idName = `projects-${projectIndex}-id`;
          bin.querySelectorAll(`input[name="${delName}"]`).forEach(n => n.remove());
          bin.querySelectorAll(`input[name="${idName}"]`).forEach(n => n.remove());
          const delInput = document.createElement('input'); delInput.type='hidden'; delInput.name=delName; delInput.value='on';
          const idInput = document.createElement('input'); idInput.type='hidden'; idInput.name=idName; idInput.value=hiddenIdInput.value;
          bin.appendChild(delInput); bin.appendChild(idInput);
        }
        if (section) section.remove();
        return;
      }

      // New: remove and renumber
      if (section) section.remove();
      if (totalFormsInput) totalFormsInput.value = String(Math.max(0, (parseInt(totalFormsInput.value || '0', 10) - 1)));
      renumberProjects();
    } else {
      if (section) { section.classList.remove('marked-for-deletion'); section.style.opacity=''; }
    }
  }

  function attachProjectDeleteHandlers() {
    document.querySelectorAll('input[name^="projects-"][name$="-DELETE"]').forEach(cb => {
      cb.removeEventListener('click', handleProjectDelete);
      cb.addEventListener('click', handleProjectDelete);
    });
    document.querySelectorAll('.project-delete-btn').forEach(btn => {
      btn.removeEventListener('click', handleProjectDeleteButtonClick);
      btn.addEventListener('click', handleProjectDeleteButtonClick);
    });
  }

  function addProjectRow() {
    const totalFormsInput = document.querySelector('input[name="projects-TOTAL_FORMS"]');
    const container = document.querySelector('#submission-form .card');
    if (!totalFormsInput || !container) return;
    const idx = parseInt(totalFormsInput.value || '0', 10);
    const div = document.createElement('div');
    div.className='project-section';
    div.setAttribute('data-project-index', String(idx));
    div.innerHTML = `
      <div class="project-header">
        <input type="hidden" name="projects-${idx}-id" id="id_projects-${idx}-id">
        <div class="project-header-grid">
          <div class="form-field">
            <label class="form-label" for="id_projects-${idx}-project_title">Project:</label>
            <input type="text" name="projects-${idx}-project_title" id="id_projects-${idx}-project_title" class="form-input" required>
          </div>
          <div class="form-field">
            <label class="form-label" for="id_projects-${idx}-area_of_concern">Area of Concern:</label>
            <select name="projects-${idx}-area_of_concern" id="id_projects-${idx}-area_of_concern" class="form-input" required>
              <option value="">-- Select Area of Concern --</option>
              <option value="Access">Access</option>
              <option value="Quality">Quality</option>
              <option value="Equity">Equity</option>
              <option value="Enabling Mechanisms">Enabling Mechanisms</option>
            </select>
          </div>
          <div class="form-field">
            <label class="form-label" for="id_projects-${idx}-conference_date">Conference Date:</label>
            <input type="date" name="projects-${idx}-conference_date" id="id_projects-${idx}-conference_date" class="form-input table-date">
          </div>
        </div>
        <div class="form-field" style="margin-top:.5rem; display:flex; justify-content:flex-end;">
          <input type="checkbox" name="projects-${idx}-DELETE" id="id_projects-${idx}-DELETE" style="display:none">
          <button type="button" class="btn btn--danger project-delete-btn">Delete Project</button>
        </div>
        <div class="save-project-notice" style="background:#fef3c7;border:1px solid #f59e0b;border-radius:.5rem;padding:1rem;margin:1rem 0;">
          <div style="display:flex;align-items:center;gap:.75rem;">
            <div style="color:#f59e0b;font-size:1.25rem;">!</div>
            <div>
              <p style="margin:0;font-weight:600;color:#92400e;">Save Project First</p>
              <p style="margin:.25rem 0 0 0;font-size:.875rem;color:#78350f;">Fill in the project details above, then click "Save Draft" to unlock the activities section.</p>
            </div>
          </div>
          <button type="button" class="btn btn--primary save-project-btn" style="margin-top:.75rem;font-size:.875rem;">Save This Project</button>
        </div>
      </div>`;
    const addBtn = document.querySelector('.btn.btn--primary[onclick="addProjectRow()"]');
    const anchor = addBtn ? addBtn.parentElement : container;
    container.insertBefore(div, anchor);
    totalFormsInput.value = String(idx + 1);
    attachProjectDeleteHandlers();
    const first = div.querySelector('input[type="text"]'); if (first) setTimeout(() => first.focus(), 50);
    const sp = div.querySelector('.save-project-btn');
    if (sp) sp.addEventListener('click', function() {
      const form = byId('submission-form'); if (!form) return;
      const nextTabInput = byId('id_next_tab'); const autosaveInput = byId('id_autosave');
      if (nextTabInput) nextTabInput.value = 'projects';
      if (autosaveInput) autosaveInput.value = '1';
      try { sessionStorage.setItem('project_quicksave_toast', 'Project saved'); } catch (e) {}
      form.submit();
    });
  }

  // ---------------- Activities ----------------
  const activityDeleteState = new WeakMap();

  function renumberActivities(tbody) {
    // Renumber repeated headers: Activity 1..N in document order
    const headers = Array.from(tbody.querySelectorAll('tr.activity-repeated-header .section-number'));
    headers.forEach((el, idx) => { el.textContent = String(idx + 1); });
  }

  function updateActivitiesHeaderVisibility(tbody) {
    if (!tbody) return;
    const table = tbody.closest('table');
    const thead = table ? table.querySelector('thead') : null;
    const count = tbody.querySelectorAll('.activity-row').length;
    // Always hide thead when using repeated headers
    if (thead) thead.style.display = 'none';
    const pid = tbody.getAttribute('data-project-id');
    if (pid) {
      const empty = document.querySelector(`.activities-empty[data-project-id="${pid}"]`);
      if (empty) empty.style.display = count > 0 ? 'none' : 'block';
    }
  }

  // Remove any orphan separators that can be left behind after deletes
  function cleanActivitySubheaders(tbody) {
    if (!tbody) return;
    const rows = Array.from(tbody.children);
    rows.forEach((tr) => {
      if (tr.classList && tr.classList.contains('activity-repeated-header')) {
        // valid only when directly followed by an activity-row
        const next = tr.nextElementSibling;
        if (!next || !next.classList || !next.classList.contains('activity-row')) {
          tr.remove();
        }
      }
    });
  }

  function getActivityDeleteBin(form) {
    let bin = form.querySelector('#activity-delete-bin');
    if (!bin) { bin = document.createElement('div'); bin.id='activity-delete-bin'; bin.style.display='none'; form.appendChild(bin); }
    return bin;
  }

  function handleActivityDelete(e) {
    console.log('DIAGNOSTIC: handleActivityDelete called', e);
  const checkbox = e.target;
  const row = checkbox.closest('tr');
  if (!row) return;
  const tbody = row.parentElement;
  const form = tbody.closest('form');
  if (!form) return;
  const maybeDetails = row.nextElementSibling && row.nextElementSibling.classList.contains('activity-details') ? row.nextElementSibling : null;
  const maybeSubheader = row.previousElementSibling && row.previousElementSibling.classList.contains('activity-repeated-header') ? row.previousElementSibling : null;

  // Robustly find the hidden id input for this activity
  let idInput = row.querySelector('input[type="hidden"][name$="-id"]');
  if (!idInput && maybeDetails) {
    idInput = maybeDetails.querySelector('input[type="hidden"][name$="-id"]');
  }
  let totalFormsInput = null;
  let idValue = '';
  if (idInput && idInput.name) {
    const prefixMatch = idInput.name.match(/^(activities_\d+)-\d+-id$/);
    if (prefixMatch) {
      totalFormsInput = document.querySelector(`input[name="${prefixMatch[1]}-TOTAL_FORMS"]`);
    }
    idValue = idInput.value || '';
  }
  if (checkbox.checked) {
    if (!confirm('Are you sure you want to remove this activity?')) { checkbox.checked = false; return; }
    // Always create hidden DELETE/id inputs for both new and existing rows
    const anyField = row.querySelector('textarea, input[name*="-"], select[name*="-"]');
    const nameAttr = anyField ? anyField.getAttribute('name') : '';
    const m = nameAttr ? nameAttr.match(/^(.+)-(\d+)-/) : null;
    const prefix = m ? m[1] : '';
    const idx = m ? m[2] : '';
    const delName = `${prefix}-${idx}-DELETE`;
    const idName = `${prefix}-${idx}-id`;
    // Remove any previous for this index
    form.querySelectorAll(`input[name="${delName}"]`).forEach(n => n.remove());
    form.querySelectorAll(`input[name="${idName}"]`).forEach(n => n.remove());
    // Create hidden DELETE and id inputs (idInput may be empty for new rows)
    const delInput = document.createElement('input'); delInput.type = 'hidden'; delInput.name = delName; delInput.value = 'on';
  const idInputCopy = document.createElement('input'); idInputCopy.type = 'hidden'; idInputCopy.name = idName; idInputCopy.value = idValue;
  form.appendChild(delInput); form.appendChild(idInputCopy);
    // Remove row and details/subheader from DOM
    if (maybeDetails) maybeDetails.remove();
    if (maybeSubheader) maybeSubheader.remove();
    row.remove();
    renumberActivities(tbody);
    updateActivitiesHeaderVisibility(tbody);
    cleanActivitySubheaders(tbody);
  } else {
    // Unhide if un-deleted (should rarely happen)
    let deleteInput = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
    if (deleteInput) deleteInput.checked = false;
    row.style.display = '';
    if (maybeDetails) maybeDetails.style.display = '';
    if (maybeSubheader) maybeSubheader.style.display = '';
  }
}

  function attachActivityDeleteHandlers() {
    // Attach to checkboxes as before
    document.querySelectorAll('.activity-row input[name*="-DELETE"]').forEach(cb => {
      cb.removeEventListener('click', handleActivityDelete);
      cb.addEventListener('click', handleActivityDelete);
    });
    // Use event delegation for delete buttons
    document.body.removeEventListener('click', delegatedActivityDeleteBtnHandler);
    document.body.addEventListener('click', delegatedActivityDeleteBtnHandler);
  }

  function delegatedActivityDeleteBtnHandler(e) {
    if (e.target && e.target.classList && e.target.classList.contains('activity-delete-btn')) {
      const row = e.target.closest('tr'); if (!row) return;
      const cb = row.querySelector('input[name*="-DELETE"]'); if (!cb) return;
      cb.checked = true; handleActivityDelete({ target: cb });
    }
  }

  // Collapse/expand activity base + details by clicking the repeated header
  function attachActivityHeaderToggles() {
    document.querySelectorAll('tr.activity-repeated-header').forEach(h => {
      h.style.cursor = 'pointer';
      h.addEventListener('click', function(){
        // Find all rows after this header until the next header or end of tbody
        let next = h.nextElementSibling;
        const rowsToToggle = [];
        while (next && !next.classList.contains('activity-repeated-header')) {
          rowsToToggle.push(next);
          next = next.nextElementSibling;
        }
        const expanded = h.getAttribute('data-expanded') !== 'false';
        const icon = h.querySelector('.acc-icon');
        if (expanded) {
          rowsToToggle.forEach(row => row.style.display = 'none');
          h.setAttribute('data-expanded','false');
          if (icon) icon.textContent = '▸';
          // Update header title with activity value
          const base = rowsToToggle.find(row => row.classList.contains('activity-row'));
          const titleSpan = h.querySelector('.activity-title-text');
          if (base) {
            const textarea = base.querySelector('textarea[name$="-activity"]');
            if (textarea && titleSpan) titleSpan.textContent = textarea.value || '';
          }
        } else {
          rowsToToggle.forEach(row => row.style.display = '');
          h.setAttribute('data-expanded','true');
          if (icon) icon.textContent = '▾';
        }
      });
    });
    // Update header title live as user types
    document.querySelectorAll('.activity-row textarea[name$="-activity"]').forEach(textarea => {
      textarea.addEventListener('input', function(){
        const row = textarea.closest('tr.activity-row');
        if (!row) return;
        const header = row.previousElementSibling && row.previousElementSibling.classList.contains('activity-table-headers') ? row.previousElementSibling.previousElementSibling : row.previousElementSibling;
        if (header && header.classList.contains('activity-repeated-header')) {
          const titleSpan = header.querySelector('.activity-title-text');
          if (titleSpan) titleSpan.textContent = textarea.value || '';
        }
      });
    });
  }

  function addActivityRow(projectId) {
    if (!projectId || projectId === 'None' || projectId === 'null') { alert('Please save this project first before adding activities.'); return; }
    const tbody = document.querySelector(`.activity-table-body[data-project-id="${projectId}"]`);
    if (!tbody) { alert('Cannot add activities to this project. Please refresh and try again.'); return; }
    let prefix = `activities_${projectId}`;
    let totalFormsInput = document.querySelector(`input[name="${prefix}-TOTAL_FORMS"]`);
    if (!totalFormsInput) { totalFormsInput = document.createElement('input'); totalFormsInput.type='hidden'; totalFormsInput.name=`${prefix}-TOTAL_FORMS`; totalFormsInput.value='0'; (tbody.closest('form')||document.body).appendChild(totalFormsInput); }
    ['INITIAL_FORMS','MIN_NUM_FORMS','MAX_NUM_FORMS'].forEach(s => {
      if (!document.querySelector(`input[name="${prefix}-${s}"]`)) { const el=document.createElement('input'); el.type='hidden'; el.name=`${prefix}-${s}`; el.value=(s==='MAX_NUM_FORMS'?'1000':'0'); (tbody.closest('form')||document.body).appendChild(el); }
    });
    const currentTotal = parseInt(totalFormsInput.value || '0', 10);
    const base = document.createElement('tr'); base.className='activity-row'; base.setAttribute('data-activity-index', String(currentTotal));
    base.innerHTML = `
      <input type="hidden" name="${prefix}-${currentTotal}-id" id="id_${prefix}-${currentTotal}-id">
      <td><textarea name="${prefix}-${currentTotal}-activity" class="table-input table-textarea" rows="2" placeholder="Enter activity description..."></textarea></td>
      <td><input type="number" name="${prefix}-${currentTotal}-output_target" class="table-input" min="0" step="1"></td>
      <td><input type="number" name="${prefix}-${currentTotal}-output_actual" class="table-input" min="0" step="1"></td>
      <td><input type="date" name="${prefix}-${currentTotal}-timeframe_target" class="table-input table-date"></td>
      <td><input type="date" name="${prefix}-${currentTotal}-timeframe_actual" class="table-input table-date"></td>
      <td><input type="number" name="${prefix}-${currentTotal}-budget_target" class="table-input" min="0" step="0.01" placeholder="0.00"></td>
      <td><input type="number" name="${prefix}-${currentTotal}-budget_actual" class="table-input" min="0" step="0.01" placeholder="0.00"></td>
      <td>
        <input type="checkbox" name="${prefix}-${currentTotal}-DELETE" id="id_${prefix}-${currentTotal}-DELETE" style="display:none" aria-label="Remove this activity">
        <button type="button" class="btn btn--danger btn--small activity-delete-btn" aria-label="Remove this activity">Delete</button>
      </td>`;
    const details = document.createElement('tr'); details.className='activity-details'; details.setAttribute('data-project-id', projectId); details.setAttribute('data-activity-index', String(currentTotal));
    const n = tbody.querySelectorAll('.activity-row').length + 1;
    details.innerHTML = `
      <td colspan="8">
        <div class="activity-details-grid">
          <div class="details-field"><label class="form-label" for="id_${prefix}-${currentTotal}-interpretation">Interpretation</label><textarea name="${prefix}-${currentTotal}-interpretation" id="id_${prefix}-${currentTotal}-interpretation" class="table-input table-textarea" rows="4" placeholder="Enter interpretation..."></textarea></div>
          <div class="details-field"><label class="form-label" for="id_${prefix}-${currentTotal}-issues_unaddressed">Issues / Problems</label><textarea name="${prefix}-${currentTotal}-issues_unaddressed" id="id_${prefix}-${currentTotal}-issues_unaddressed" class="table-input table-textarea" rows="4" placeholder="Enter issues..."></textarea></div>
          <div class="details-field"><label class="form-label" for="id_${prefix}-${currentTotal}-facilitating_factors">Facilitating Factors</label><textarea name="${prefix}-${currentTotal}-facilitating_factors" id="id_${prefix}-${currentTotal}-facilitating_factors" class="table-input table-textarea" rows="4" placeholder="Enter facilitating factors..."></textarea></div>
          <div class="details-field"><label class="form-label" for="id_${prefix}-${currentTotal}-agreements">Agreements</label><textarea name="${prefix}-${currentTotal}-agreements" id="id_${prefix}-${currentTotal}-agreements" class="table-input table-textarea" rows="4" placeholder="Enter agreements..."></textarea></div>
        </div>
      </td>`;
    // Insert a repeated header before this activity (always)
    {
      const sep = document.createElement('tr'); sep.className = 'activity-repeated-header'; sep.setAttribute('data-expanded','true');
      sep.innerHTML = `<td class="col-activity"><strong><span class="acc-icon" aria-hidden="true">▾</span> Activity <span class="section-number">${n}</span></strong></td><td class="col-output">Output<br><small class="text-muted">Target</small></td><td class="col-output">Output<br><small class="text-muted">Actual</small></td><td class="col-timeframe">Timeframe<br><small class="text-muted">Target</small></td><td class="col-timeframe">Timeframe<br><small class="text-muted">Actual</small></td><td class="col-budget">Budget<br><small class="text-muted">Target</small></td><td class="col-budget">Budget<br><small class="text-muted">Actual</small></td><td class="col-action">Action</td>`;
      tbody.appendChild(sep);
    }
    tbody.appendChild(base); if (base.nextSibling) tbody.insertBefore(details, base.nextSibling); else tbody.appendChild(details);
    totalFormsInput.value = String(currentTotal + 1);
    attachActivityDeleteHandlers();
    attachActivityHeaderToggles();
    const focusEl = base.querySelector('textarea, input:not([type="hidden"])'); if (focusEl) setTimeout(() => focusEl.focus(), 50);
    cleanActivitySubheaders(tbody);
    updateActivitiesHeaderVisibility(tbody);
  }

  // ---------------- SLP toggle stubs ----------------
  function toggleGrade(slug) {
    const el = byId(`grade-${slug}`); if (!el) return;
    const hidden = el.style.display === 'none' || getComputedStyle(el).display === 'none';
    el.style.display = hidden ? 'block' : 'none';
    const header = el.previousElementSibling; const icon = header && header.querySelector ? header.querySelector('.accordion-icon') : null;
    if (icon) icon.textContent = hidden ? String.fromCharCode(9660) : String.fromCharCode(9654);
  }
  function toggleSubject(composite) {
    const panel = byId(`subject-${composite}`); if (!panel) return;
    const hidden = panel.style.display === 'none' || getComputedStyle(panel).display === 'none';
    panel.style.display = hidden ? 'block' : 'none';
  }

  // ---------------- SLP offered + proficiency validation ----------------
  function updateProficiencyDisplay(subjectContent) {
    if (!subjectContent) return;
    const enrolmentInput = subjectContent.querySelector('input[id$="-enrolment"]');
    const dnmeInput = subjectContent.querySelector('input[id$="-dnme"]');
    const fsInput = subjectContent.querySelector('input[id$="-fs"]');
    const sInput = subjectContent.querySelector('input[id$="-s"]');
    const vsInput = subjectContent.querySelector('input[id$="-vs"]');
    const oInput = subjectContent.querySelector('input[id$="-o"]');
    if (!enrolmentInput) return;
    const enrolment = parseInt(enrolmentInput.value || '0', 10) || 0;
    const dnme = parseInt(dnmeInput?.value || '0', 10) || 0;
    const fs = parseInt(fsInput?.value || '0', 10) || 0;
    const s = parseInt(sInput?.value || '0', 10) || 0;
    const vs = parseInt(vsInput?.value || '0', 10) || 0;
    const o = parseInt(oInput?.value || '0', 10) || 0;
    const sum = dnme + fs + s + vs + o;
    const section = subjectContent.querySelector('[data-section="proficiency" ]');
    const errorContainer = section?.querySelector('.validation-errors');
    const errorMessages = section?.querySelector('.error-messages');
    // Try to derive a friendly grade label like "Grade 7" from the header
    let gradeLabel = 'Grade';
    const hdr = subjectContent.querySelector('.subject-label');
    if (hdr && hdr.textContent) {
      const txt = hdr.textContent.trim();
      const parts = txt.split(' - '); // e.g., "Grade 7 - Math"
      if (parts.length > 0) gradeLabel = parts[0];
    }

    if (enrolment > 0 && sum !== enrolment) {
      if (errorContainer && errorMessages) {
        errorContainer.style.display = 'flex';
        errorMessages.innerHTML = `<div class="message message--error">${gradeLabel} proficiency bands total (${sum}) must equal enrollment (${enrolment})</div>`;
      }
      [dnmeInput, fsInput, sInput, vsInput, oInput].forEach(el => el && el.classList.add('error'));
    } else {
      if (errorContainer) errorContainer.style.display = 'none';
      [dnmeInput, fsInput, sInput, vsInput, oInput].forEach(el => el && el.classList.remove('error'));
    }

    // Compact SLP banner (single card) similar to RMA style
    try {
      const mismatch = enrolment > 0 && sum !== enrolment;
      const existing = subjectContent.querySelector('.slp-validation-banner');
      if (existing) existing.remove();
      if (mismatch) {
        if (errorContainer) errorContainer.style.display = 'none';
        const banner = document.createElement('div');
        banner.className = 'validation-errors validation-errors--compact slp-validation-banner';
        banner.innerHTML = '<div class="error-icon">!</div><div class="error-messages"></div>';
        banner.querySelector('.error-messages').innerHTML = `<div>${gradeLabel} proficiency bands total (${sum}) must equal enrollment (${enrolment})</div>`;
        const insertBefore = section || subjectContent.firstElementChild || subjectContent;
        subjectContent.insertBefore(banner, insertBefore);
        if (section) section.classList.add('slp-proficiency-error');
      } else {
        if (section) section.classList.remove('slp-proficiency-error');
      }
    } catch (e) {}
  }

  // ---------------- SHS strand hiding (from dataset) ----------------
  function recalcGradeCompletionFor(gradeAccordion){
    if (!gradeAccordion) return;
    const container = gradeAccordion.querySelector('.subjects-container');
    if (!container) return;
    const rows = Array.from(container.querySelectorAll('.subject-accordion')).filter(el => el.style.display !== 'none');
    const offered = rows.filter(row => (row.getAttribute('data-offered') || 'true') !== 'false');
    const total = offered.length;
    let completed = 0;
    offered.forEach(row => { const isComplete = !!row.querySelector('.status-badge.complete'); if (isComplete) completed += 1; });
    const pct = total ? Math.round((completed / total) * 100) : 0;
    const stats = gradeAccordion.querySelector('.grade-stats');
    if (stats){
      const countEl = stats.querySelector('.subjects-count'); if (countEl) countEl.textContent = `${completed}/${total} subjects`;
      const bar = stats.querySelector('.completion-fill'); if (bar) bar.style.width = pct + '%';
      const pctEl = stats.querySelector('.completion-percentage'); if (pctEl) pctEl.textContent = pct + '%';
    }
  }

  function applyUnselectedStrandHidingFromDataset(){
    const form = byId('submission-form');
    if (!form) return;
    let unselected = [];
    try {
      const raw = form.dataset.shsUnselected || '[]';
      unselected = JSON.parse(raw);
    } catch (e) { unselected = []; }
    if (!Array.isArray(unselected) || unselected.length === 0) return;
    document.querySelectorAll('.grade-accordion').forEach(ga => {
      const gradeLabel = ga.getAttribute('data-grade');
      if (gradeLabel !== 'Grade 11' && gradeLabel !== 'Grade 12') return;
      const container = ga.querySelector('.subjects-container'); if (!container) return;
      container.querySelectorAll('.subject-accordion').forEach(acc => {
        const key = acc.getAttribute('data-subject-key') || '';
        const matches = unselected.some(pref => pref && key.indexOf(pref) === 0);
        if (matches) acc.style.display = 'none';
      });
      recalcGradeCompletionFor(ga);
    });
  }

  function initializeSLPOfferedToggle() {
    // Work directly with sections rendered by the template
    document.querySelectorAll('.card-section.proficiency-section').forEach(section => {
      // The subject content wrapper for this section
      const subjectContent = section.closest('.subject-content') || section;
      const offeredCheckbox = section.querySelector('input[id$="-is_offered"]');
      if (!offeredCheckbox) return;
      const notOfferedMsg = subjectContent.querySelector('.not-offered-message');
      const toggleFields = () => {
        const enabled = offeredCheckbox.checked;
        // Disable/enable all inputs for this subject except hidden fields and the offered checkbox itself
        subjectContent.querySelectorAll('input, textarea, select, button').forEach(el => {
          if (el === offeredCheckbox) return;
          if (el.type === 'hidden') return;
          if (el.closest('.offered-checkbox')) return; // leave the control area enabled
          // Use readOnly for input/textarea to keep values posted, disable buttons/selects
          if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
            try { el.readOnly = !enabled; } catch(e) {}
          } else {
            try { el.disabled = !enabled; } catch(e) {}
          }
        });
        // Grey out and show helper message
        subjectContent.style.opacity = enabled ? '' : '0.6';
        if (notOfferedMsg) notOfferedMsg.style.display = enabled ? 'none' : 'flex';
        if (enabled) {
          updateProficiencyDisplay(subjectContent);
        } else {
          const b = subjectContent.querySelector('.slp-validation-banner'); if (b) b.remove();
          if (section) section.classList.remove('slp-proficiency-error');
        }
      };
      toggleFields();
      offeredCheckbox.addEventListener('change', toggleFields);
      // Recompute proficiency as user types
      subjectContent.querySelectorAll('.proficiency-field input').forEach(inp => {
        inp.addEventListener('input', () => { updateProficiencyDisplay(subjectContent); });
      });
    });
  }

  // Restore LLC list and reasons selections from hidden storage
  function initializeSLPCompetenciesAndReasons() {
    // Competencies paragraph (if empty, inject enumerated placeholders 1-4)
    document.querySelectorAll('.llc-section').forEach(section => {
      const ta = section.querySelector('textarea.llc-storage');
      if (!ta) return;
      const existing = (ta.value || '').trim();
      if (!existing) {
        ta.value = '1. \n2. \n3. \n4. ';
      }
    });
    // Reasons and Other toggle
    document.querySelectorAll('.reasons-section').forEach(section => {
      const hiddenCodes = section.querySelector('input[type="hidden"][name$="-non_mastery_reasons"]');
      const otherHidden = section.querySelector('textarea[name$="-non_mastery_other"]');
      const codes = hiddenCodes ? (hiddenCodes.value || '').split(',').filter(Boolean) : [];
      codes.forEach(code => {
        const cb = section.querySelector(`input.reason-choice[value="${code}"]`);
        if (cb) cb.checked = true;
      });
      const fSelected = codes.includes('f');
      const otherWrap = section.querySelector('.reason-other');
      if (otherWrap) otherWrap.style.display = fSelected ? 'block' : 'none';
      if (fSelected && otherHidden && otherWrap) {
        const ta = otherWrap.querySelector('textarea');
        if (ta) ta.value = otherHidden.value || '';
      }
    });
    // Toggle on change + rebuild interventions table
    document.body.addEventListener('change', function(e){
      if (e.target && e.target.classList && e.target.classList.contains('reason-choice')) {
        const section = e.target.closest('.reasons-section');
        if (!section) return;
        const otherWrap = section.querySelector('.reason-other');
        if (!otherWrap) return;
        const show = !!section.querySelector('input.reason-choice[value="f"]:checked');
        otherWrap.style.display = show ? 'block' : 'none';

        const sc = section.closest('.subject-content');
        if (sc) rebuildInterventionsFor(sc);
      }
    });
  }

  // Build the interventions table from selected reasons; prefill from saved JSON if available
  function rebuildInterventionsFor(subjectContent) {
    const plan = subjectContent.querySelector('.interventions-plan');
    if (!plan) return;
  const pairsWrap = plan.querySelector('.interventions-pairs');
    const storage = plan.querySelector('textarea.interventions-storage');
    let saved = [];
    try { saved = storage && storage.value ? JSON.parse(storage.value) : []; } catch (e) { saved = []; }

    // Collect selected reasons; substitute 'Other' text when present
    const selected = Array.from(subjectContent.querySelectorAll('.reasons-section input.reason-choice:checked')).map(cb => {
      const labelSpan = cb.closest('label') && cb.closest('label').querySelector('span');
      let label = labelSpan ? labelSpan.textContent.trim() : (cb.closest('label') ? cb.closest('label').textContent.trim() : cb.value);
      if (cb.value === 'f') {
        const otherTa = subjectContent.querySelector('.reasons-section .reason-other textarea');
        if (otherTa && otherTa.value.trim()) label = otherTa.value.trim();
      }
      return { code: cb.value, reason: label };
    });

    // Clear current UI
    if (pairsWrap) { pairsWrap.innerHTML = ''; }

    if (!selected.length) {
      if (pairsWrap) {
        const emptyMsg = document.createElement('div');
        emptyMsg.style.gridColumn = '1 / span 2';
        emptyMsg.style.color = '#6b7280';
        emptyMsg.textContent = 'No reasons selected.';
        pairsWrap.appendChild(emptyMsg);
      }
      return;
    }

    // Build numbered reasons and matching textareas
    selected.forEach((item, idx) => {
      if (!pairsWrap) return;
      const reasonDiv = document.createElement('div');
      reasonDiv.className = 'intervention-reason';
      reasonDiv.setAttribute('data-number', String(idx + 1));
      const numberSpan = document.createElement('span');
      numberSpan.className = 'intervention-reason-number';
      numberSpan.textContent = `${idx + 1}.`;
      const textSpan = document.createElement('span');
      textSpan.textContent = item.reason;
      reasonDiv.appendChild(numberSpan);
      reasonDiv.appendChild(textSpan);
      const ta = document.createElement('textarea');
      ta.className = 'form-textarea intervention-textarea';
      ta.rows = 2;
      ta.placeholder = 'Example: Conduct LAC on teaching the difficult-to-teach competencies';
      ta.setAttribute('data-reason-code', item.code);
      const match = saved.find(s => s.code === item.code);
      if (match && match.intervention) ta.value = match.intervention;
      pairsWrap.appendChild(reasonDiv);
      pairsWrap.appendChild(ta);
    });
  }

  function initializeSLPNestedAccordion() {
    // Recompute on load for all visible subject contents
    document.querySelectorAll('.subject-content').forEach(sc => { 
      updateProficiencyDisplay(sc);
      rebuildInterventionsFor(sc);
    });
  }

  // Initialize Reading Difficulties builder from hidden JSON
  function initializeReadingDifficulties() {
    const storage = document.querySelector('.reading-difficulties-storage');
    if (!storage) return;
    let saved = [];
    try { saved = storage.value ? JSON.parse(storage.value) : []; } catch(e) { saved = []; }
    saved.forEach(entry => {
      const gradeEl = document.querySelector(`.reading-difficulty-grade[data-grade="${entry.grade}"]`);
      if (!gradeEl) return;
      const pairs = entry.pairs || [];
      pairs.forEach((pair, idx) => {
        const pairEl = gradeEl.querySelectorAll('.reading-difficulty-pair')[idx];
        if (!pairEl) return;
        const diffTa = pairEl.querySelector('textarea.reading-difficulty-textarea');
        const intTa = pairEl.querySelector('textarea.reading-intervention-textarea');
        if (diffTa) diffTa.value = pair.difficulty || '';
        if (intTa) intTa.value = pair.intervention || '';
      });
    });
  }

  // Initialize RMA difficulties builders from hidden JSON
  function initializeRMADifficulties() {
    function hydrate(selectorStorage, selectorPlan) {
      const storage = document.querySelector(selectorStorage);
      const planRoot = document.querySelector(selectorPlan);
      if (!storage || !planRoot) return;
      let saved = [];
      try { saved = storage.value ? JSON.parse(storage.value) : []; } catch (e) { saved = []; }
      saved.forEach(entry => {
        const gradeEl = planRoot.querySelector(`.rma-difficulty-grade[data-grade="${entry.grade}"]`);
        if (!gradeEl) return;
        const pairs = entry.pairs || [];
        pairs.forEach((pair, idx) => {
          const pairEl = gradeEl.querySelectorAll('.rma-difficulty-pair')[idx];
          if (!pairEl) return;
          const diffTa = pairEl.querySelector('textarea.rma-difficulty-textarea');
          const intTa = pairEl.querySelector('textarea.rma-intervention-textarea');
          if (diffTa) diffTa.value = pair.difficulty || '';
          if (intTa) intTa.value = pair.intervention || '';
        });
      });
    }
    hydrate('.rma-pretest-storage', '.rma-pretest-plan');
    hydrate('.rma-eosy-storage', '.rma-eosy-plan');
  }

  // Track which SLP subject is being saved so the server can resolve it
  function wireSLPSaveSubject() {
    const form = document.getElementById('submission-form');
    if (!form) return;
    const subjectIdInput = document.getElementById('id_current_subject_id');
    const subjectPrefixInput = document.getElementById('id_current_subject_prefix');
    const subjectIndexInput = document.getElementById('id_current_subject_index');

    function inferFromSection(btn) {
      const section = btn.closest('.subject-content') || btn.closest('.card-section');
      if (!section) return;
      const probe = section.querySelector('input[id*="slp_rows-"][id$="-enrolment"], input[name*="slp_rows-"][name$="-enrolment"]');
      const ref = probe ? (probe.id || probe.name || '') : '';
      const mPrefix = ref.match(/(slp_rows-\d+)/);
      const mIndex = ref.match(/slp_rows-(\d+)/);
      if (mPrefix && subjectPrefixInput) subjectPrefixInput.value = mPrefix[1];
      if (mIndex && subjectIndexInput) subjectIndexInput.value = mIndex[1];
    }

    document.querySelectorAll('.save-subject-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        if (subjectIdInput) subjectIdInput.value = this.dataset.subjectId || subjectIdInput.value || '';
        if (subjectPrefixInput) subjectPrefixInput.value = this.dataset.subjectPrefix || subjectPrefixInput.value || '';
        if (subjectIndexInput) subjectIndexInput.value = this.dataset.subjectIndex || subjectIndexInput.value || '';
        if ((!subjectPrefixInput?.value || !subjectIndexInput?.value)) {
          inferFromSection(this);
        }
      });
    });

    document.querySelectorAll('button[name="action"][value="save_draft"]').forEach(btn => {
      btn.addEventListener('click', function() {
        if (subjectIdInput) subjectIdInput.value = '';
        if (subjectPrefixInput) subjectPrefixInput.value = '';
        if (subjectIndexInput) subjectIndexInput.value = '';
      });
    });
  }
  // ---------------- Cross-tab validation (Reading/RMA) ----------------
  function getSLPEnrollmentData() {
    const slpData = {};
    document.querySelectorAll('input[id*="slp_rows"][id$="-enrolment"]').forEach(input => {
      const value = parseInt(input.value || '0', 10) || 0;
      if (value > 0) {
        const m = input.id.match(/slp_rows-\d+-(grade_\d+|kinder)-[^-]+-enrolment/);
        if (m) {
          const gradePart = m[1];
          const gradeName = gradePart === 'kinder' ? 'Kinder' : gradePart.replace('grade_', 'Grade ');
          if (!slpData[gradeName]) slpData[gradeName] = value;
        }
      }
    });
    return slpData;
  }

  function validateRMAEnrollment() {
    const errors = [];
    document.querySelectorAll('input[id*="rma_rows"][id$="-enrolment"]').forEach(enrollmentInput => {
      const row = enrollmentInput.closest('tr'); if (!row) return;
      const gradeCell = row.querySelector('td:first-child');
      const rmaEnrollment = parseInt(enrollmentInput.value || '0', 10) || 0;
      const grade = gradeCell ? gradeCell.textContent.trim() : 'Grade';
      if (rmaEnrollment > 0) {
        const profInputs = row.querySelectorAll('input[id$="-emerging_not_proficient"], input[id$="-emerging_low_proficient"], input[id$="-developing_nearly_proficient"], input[id$="-transitioning_proficient"], input[id$="-at_grade_level"]');
        const sum = Array.from(profInputs).reduce((a, inp) => a + (parseInt(inp.value || '0', 10) || 0), 0);
        if (sum !== rmaEnrollment) {
          errors.push({ element: row, message: `${grade} proficiency bands total (${sum}) must equal enrollment (${rmaEnrollment})` });
        }
      }
    });
    return errors;
  }

  function validateReadingEnrollment() {
    const slpData = getSLPEnrollmentData();
    if (Object.keys(slpData).length === 0) return [];
    const errors = [];
    const gradeMap = { '1':'Grade 1','2':'Grade 2','3':'Grade 3','4':'Grade 4','5':'Grade 5','6':'Grade 6','7':'Grade 7','8':'Grade 8','9':'Grade 9','10':'Grade 10' };
    const crlaTotals = {};
    document.querySelectorAll('input[id*="reading_crla_new"]').forEach(input => {
      const m = input.id.match(/_(mt|fil|eng)_grade_(\d+)/);
      if (!m) return; const gradeNum = m[2];
      const gradeName = gradeMap[gradeNum];
      const value = parseInt(input.value || '0', 10) || 0;
      crlaTotals[gradeName] = (crlaTotals[gradeName] || 0) + value;
    });
    Object.keys(crlaTotals).forEach(grade => {
      if (slpData[grade] && crlaTotals[grade] !== slpData[grade]) {
        errors.push({ message: `${grade} reading totals (${crlaTotals[grade]}) must equal SLP enrollment (${slpData[grade]})` });
      }
    });
    return errors;
  }

  function validateCurrentTab() {
    const qs = new URLSearchParams(window.location.search);
    const tab = qs.get('tab');
    if (tab === 'rma') return validateRMAEnrollment();
    if (tab === 'reading') return validateReadingEnrollment();
    return [];
  }

  // Lightweight visual indicators for RMA/Reading validation
  function wireRMAVerification() {
    const redraw = () => {
      // Clear previous outline and any prior banner
      document.querySelectorAll('tr.row-error').forEach(tr => { tr.classList.remove('row-error'); tr.style.outline = ''; tr.title = ''; });
      const oldBanner = document.querySelector('.rma-validation-banner'); if (oldBanner) oldBanner.remove();

      const errs = validateRMAEnrollment();
      // Outline rows in error (no inline messages)
      errs.forEach(e => { if (e.element) { e.element.classList.add('row-error'); e.element.style.outline = '2px solid #ef4444'; e.element.title = e.message; } });

      // Single, slim banner above the RMA table
      if (errs.length > 0) {
        const banner = document.createElement('div');
        banner.className = 'validation-errors validation-errors--compact rma-validation-banner';
        banner.innerHTML = '<div class="error-icon">!</div><div class="error-messages"></div>';
        banner.querySelector('.error-messages').innerHTML = `<div>${errs[0].message}</div>`;
        const host = document.querySelector('.data-table-wrapper');
        if (host && host.parentNode) host.parentNode.insertBefore(banner, host);
      }
    };
    document.querySelectorAll('input[id*="rma_rows"]').forEach(inp => {
      inp.addEventListener('input', redraw);
      inp.addEventListener('change', redraw);
    });
    redraw();
  }

  function wireReadingVerification() {
    const redraw = () => {
      const errs = validateReadingEnrollment();
      // For now, just log and optionally show one toast-like banner
      const old = document.querySelector('.reading-crosscheck'); if (old) old.remove();
      if (errs.length > 0) {
        const banner = document.createElement('div');
        banner.className = 'reading-crosscheck';
        banner.style.cssText = 'margin:.5rem 0;padding:.5rem 1rem;border:1px solid #f59e0b;background:#fef3c7;color:#92400e;border-radius:.5rem;';
        banner.textContent = errs[0].message;
        // Insert above the first reading section if found
        const host = document.querySelector('[data-tab="reading"], .assessment-section') || document.querySelector('.submission-shell');
        if (host && host.parentNode) host.parentNode.insertBefore(banner, host);
      }
      // Recompute CRLA totals in the matrix
      computeCRLATotals();
    };
    document.querySelectorAll('input[id*="reading_crla_new"], input[id*="reading_philiri"]').forEach(inp => {
      inp.addEventListener('input', redraw);
      inp.addEventListener('change', redraw);
    });
    redraw();
  }

  // ---------------- Reading totals (CRLA + PHILIRI) ----------------
  function readNumber(el) {
    const v = parseFloat(el && el.value ? el.value : '0');
    return Number.isFinite(v) ? v : 0;
  }
  function sumInputsInRow(row) {
    let total = 0;
    row.querySelectorAll('input[type="number"]').forEach(inp => { total += readNumber(inp); });
    return total;
  }
  function computeCRLATotals() {
    // Handle CRLA tables (mt/fil/eng for Grades 1-3)
    document.querySelectorAll('.reading-matrix-table').forEach(table => {
      try {
        const tbody = table.tBodies && table.tBodies[0] ? table.tBodies[0] : table.querySelector('tbody');
        if (!tbody) return;
        const rows = Array.from(tbody.querySelectorAll('tr'));
        let grand = 0;
        rows.forEach(tr => {
          if (tr.classList.contains('total-row')) return;
          const totalSpan = tr.querySelector('.total-cell .total-value');
          if (!totalSpan) return;
          const rowTotal = sumInputsInRow(tr);
          totalSpan.textContent = String(rowTotal);
          grand += rowTotal;
        });
        // Grand total (CRLA uses data-grand-total without key)
        const grandSpan = table.querySelector('.grand-total [data-grand-total], [data-grand-total]:not([data-grand-total=""])');
        if (grandSpan && !grandSpan.getAttribute('data-grand-total')) {
          grandSpan.textContent = String(grand);
        }
      } catch (e) { /* ignore */ }
    });

    // Handle PHILIRI (elem/junior) where totals are keyed by data-total="eng-elem" etc.
    // Elementary
    document.querySelectorAll('.reading-matrix-table').forEach(table => {
      try {
        const elemEng = table.querySelector('[data-total="eng-elem"]');
        const elemFil = table.querySelector('[data-total="fil-elem"]');
        const jrEng = table.querySelector('[data-total="eng-junior"]');
        const jrFil = table.querySelector('[data-total="fil-junior"]');
        // Elementary
        if (elemEng || elemFil) {
          let engSum = 0, filSum = 0;
          const engRow = elemEng ? elemEng.closest('tr') : null;
          const filRow = elemFil ? elemFil.closest('tr') : null;
          if (engRow) engSum = sumInputsInRow(engRow);
          if (filRow) filSum = sumInputsInRow(filRow);
          if (elemEng) elemEng.textContent = String(engSum);
          if (elemFil) elemFil.textContent = String(filSum);
          const g = table.querySelector('[data-grand-total="elem"]');
          if (g) g.textContent = String(engSum + filSum);
        }
        // Junior
        if (jrEng || jrFil) {
          let engJ = 0, filJ = 0;
          const engRowJ = jrEng ? jrEng.closest('tr') : null;
          const filRowJ = jrFil ? jrFil.closest('tr') : null;
          if (engRowJ) engJ = sumInputsInRow(engRowJ);
          if (filRowJ) filJ = sumInputsInRow(filRowJ);
          if (jrEng) jrEng.textContent = String(engJ);
          if (jrFil) jrFil.textContent = String(filJ);
          const gJ = table.querySelector('[data-grand-total="junior"]');
          if (gJ) gJ.textContent = String(engJ + filJ);
        }
      } catch (e2) { /* ignore */ }
    });
  }

  // ---------------- ADM helpers ----------------
  function toggleADMFields(isOffered) {
    const container = document.querySelector('.adm-table')?.closest('.card') || document;
    const controls = container.querySelectorAll('.adm-table input, .adm-table textarea, .adm-table select, #add-adm-ppa');
    controls.forEach(el => {
      if (el.type === 'hidden') return;
      // Prefer readOnly so values still post when disabled; keep Add button disabled
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
        try { el.readOnly = !isOffered; } catch(e) {}
      } else if (el.tagName === 'SELECT') {
        try { el.disabled = !isOffered; } catch(e) {}
      } else if (el.id === 'add-adm-ppa') {
        try { el.disabled = !isOffered; } catch(e) {}
      }
    });
  }
  function addADMPPA() {
    const tbody = document.getElementById('adm-table-body');
    const template = document.querySelector('.adm-row-template');
    if (!tbody || !template) return;
    // Find TOTAL_FORMS for ADM formset by sampling template field name prefix
    const sample = template.querySelector('input, textarea, select');
    if (!sample || !sample.name) return;
    const prefix = sample.name.split('-')[0];
    const total = document.querySelector(`input[name="${prefix}-TOTAL_FORMS"]`);
    const idx = total ? parseInt(total.value || '0', 10) : 0;
    const html = template.outerHTML.replace(/__prefix__/g, String(idx)).replace('style="display:none;"', '');
    const temp = document.createElement('tbody'); temp.innerHTML = html; const row = temp.querySelector('tr');
    row.classList.remove('adm-row-template'); tbody.appendChild(row);
    if (total) total.value = String(idx + 1);
    // Refresh delete handlers and normalize labels to "Delete"
    try { attachADMDeleteHandlers(); } catch (e) {}
  }

  // Confirm ADM delete and normalize text to "Delete"
  function handleADMDeleteCheckbox(e) {
    const cb = e.target; const row = cb.closest('tr'); if (!row) return;
    if (cb.checked) {
      if (!confirm('Are you sure you want to delete this ADM row?')) { cb.checked = false; return; }
      row.style.display = 'none';
    } else {
      row.style.display = '';
    }
  }
  function attachADMDeleteHandlers() {
    document.querySelectorAll('.adm-delete-control input[type="checkbox"]').forEach(cb => {
      cb.removeEventListener('change', handleADMDeleteCheckbox);
      cb.addEventListener('change', handleADMDeleteCheckbox);
    });
    document.querySelectorAll('.adm-delete-text').forEach(span => { span.textContent = 'Delete'; });
    // Clicking the label should toggle the checkbox; let the change handler
    // show a single confirmation. Avoid double confirms.
    document.querySelectorAll('.adm-delete-control').forEach(lbl => {
      lbl.addEventListener('click', function(e){
        const cb = this.querySelector('input[type="checkbox"]');
        if (!cb) return;
        if (e.target === cb) return; // native checkbox click
        e.preventDefault();
        cb.click(); // triggers change -> single confirm
      });
    });
  }

  // ---------------- PCT helpers (0–100% visual hint) ----------------
  function wirePctValidation() {
    document.querySelectorAll('.pct-area-row .pct-input input').forEach(inp => {
      let hint = inp.parentElement?.querySelector('.pct-hint-error');
      if (!hint) {
        hint = document.createElement('small');
        hint.className = 'pct-hint-error';
        hint.textContent = 'Enter a value from 0–100';
        inp.parentElement.appendChild(hint);
      }
      const redraw = () => {
        const v = parseFloat(inp.value || '');
        const bad = Number.isFinite(v) ? (v < 0 || v > 100) : false;
        hint.style.display = bad ? 'block' : 'none';
      };
      inp.addEventListener('input', redraw);
      inp.addEventListener('change', redraw);
      redraw();
    });
  }

  // ---------------- Init ----------------
  // ---------------- Read-Only Mode ----------------
  function initializeReadOnlyMode() {
    const form = byId('submission-form');
    if (!form) return;
    
    const canEdit = (form.dataset.canEdit === '1');
    if (canEdit) return; // Don't disable fields if editing is allowed
    const status = (form.dataset.status || '').toLowerCase();
    
    console.log('Initializing read-only mode for submitted form');
    
    // Disable all form inputs, textareas, and selects that aren't already handled by template
    const formElements = form.querySelectorAll('input:not([type="hidden"]):not([readonly]):not([disabled]), textarea:not([readonly]):not([disabled]), select:not([disabled])');
    formElements.forEach(element => {
      const tag = element.tagName.toLowerCase();
      const type = (element.type || '').toLowerCase();
      if (type === 'submit' || type === 'button') {
        element.disabled = true;
        return;
      }
      if (type === 'checkbox' || type === 'radio') {
        element.disabled = true;
        element.style.cursor = 'not-allowed';
        return;
      }
      // For number/date inputs, disable to block spinner arrows; others use readOnly
      const shouldDisable = (tag === 'select') || (tag === 'input' && ['number','date','datetime-local','time'].includes(type));
      if (shouldDisable) {
        element.disabled = true;
      } else if (tag === 'input' || tag === 'textarea') {
        element.readOnly = true;
      } else {
        element.disabled = true;
      }
      // Apply consistent read-only styles
      element.style.backgroundColor = '#f3f4f6';
      element.style.cursor = 'not-allowed';
      if (tag === 'input' || tag === 'textarea') element.style.border = '1px solid #d1d5db';
      // Prevent focus via keyboard
      element.setAttribute('tabindex', '-1');
    });
    
    // Disable all buttons except navigation buttons
    const buttons = form.querySelectorAll('button:not([disabled])');
    buttons.forEach(button => {
      // Keep tab navigation buttons enabled
      if (button.classList.contains('tab-nav')) {
        return;
      }
      button.disabled = true;
      button.style.opacity = '0.5';
      button.style.cursor = 'not-allowed';
    });
    
    // Hide action buttons for adding/deleting items
    const actionButtons = form.querySelectorAll('.btn--primary:not(.tab-nav), .btn--danger, .btn--secondary:not(.tab-nav)');
    actionButtons.forEach(button => {
      if (!button.classList.contains('tab-nav')) {
        button.style.display = 'none';
      }
    });
    
    // Add visual indicator for read-only state (contextual by status)
    const readOnlyOverlay = document.createElement('div');
    let bg = '#fee2e2', border = '#fca5a5', titleColor = '#dc2626', textColor = '#7f1d1d',
        title = 'Form Read-Only', message = 'This submission cannot be edited.';
    if (status === 'noted') {
      bg = '#ecfdf5'; border = '#86efac'; titleColor = '#16a34a'; textColor = '#166534';
      title = 'Noted';
      message = 'Review completed. You can view all entries; edits are disabled.';
    } else if (status === 'submitted') {
      bg = '#fef3c7'; border = '#f59e0b'; titleColor = '#b45309'; textColor = '#92400e';
      title = 'Submitted';
      message = 'Awaiting section review. Edits are disabled until returned.';
    }
    readOnlyOverlay.innerHTML = `
      <div style="position: fixed; top: 80px; right: 20px; background: ${bg}; border: 1px solid ${border}; border-radius: 8px; padding: 12px 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); z-index: 1000; max-width: 320px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
            ${status === 'noted' ? '<path fill="#16a34a" d="M16.707 5.293a1 1 0 00-1.414 0L8 12.586 4.707 9.293a1 1 0 10-1.414 1.414l4 4a1 1 0 001.414 0l8-8a1 1 0 000-1.414z"/>' : '<path fill="#b45309" d="M10 2a8 8 0 100 16 8 8 0 000-16zm.75 4a.75.75 0 00-1.5 0v5a.75.75 0 001.5 0V6zm0 7a.75.75 0 10-1.5 0 .75.75 0 001.5 0z"/>'}
          </svg>
          <div>
            <div style="font-weight: 600; color: ${titleColor}; font-size: 14px;">${title}</div>
            <div style="color: ${textColor}; font-size: 12px;">${message}</div>
          </div>
        </div>
      </div>`;
    document.body.appendChild(readOnlyOverlay);
    
    // Auto-hide the notification after 5 seconds
    setTimeout(() => {
      readOnlyOverlay.style.transition = 'opacity 0.3s ease';
      readOnlyOverlay.style.opacity = '0';
      setTimeout(() => readOnlyOverlay.remove(), 300);
    }, 5000);
  }

  function init() {
    initTabsAndForm();
    attachProjectDeleteHandlers();
    attachActivityDeleteHandlers();
    // Make Activity headers clickable to collapse/expand
    attachActivityHeaderToggles();
    attachADMDeleteHandlers();
    // Initialize read-only mode for submitted forms
    initializeReadOnlyMode();
    // Clean stray activity subheaders on load and toggle header/empty state
    document.querySelectorAll('.activity-table-body').forEach(tbody => { cleanActivitySubheaders(tbody); updateActivitiesHeaderVisibility(tbody); });
    // Sanitize any garbled em-dash placeholders in templates
    try { document.querySelectorAll('.na-cell').forEach(td => { td.textContent = '-'; }); } catch (e) {}
    // Show toast if a project quick-save just occurred
    try {
      const msg = sessionStorage.getItem('project_quicksave_toast');
      if (msg) {
        sessionStorage.removeItem('project_quicksave_toast');
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.style.cssText = 'position:fixed; top:16px; right:16px; background:#111827; color:#fff; padding:10px 14px; border-radius:6px; box-shadow:0 4px 12px rgba(0,0,0,.2); z-index:9999; font-size:.9rem;';
        toast.textContent = msg;
        document.body.appendChild(toast);
        setTimeout(() => { toast.style.transition = 'opacity .3s'; toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 1600);
      }
    } catch (e) {}
    // SLP helpers
    initializeSLPOfferedToggle();
  initializeSLPCompetenciesAndReasons();
    initializeSLPNestedAccordion();
    // Hide SHS unselected strands (from School Profile) if provided via dataset
    applyUnselectedStrandHidingFromDataset();
    initializeReadingDifficulties();
    initializeRMADifficulties();
    wireSLPSaveSubject();
    // ADM helpers
    const admToggle = document.querySelector('.adm-offered-checkbox');
    if (admToggle) toggleADMFields(admToggle.checked);
    const addAdmBtn = document.getElementById('add-adm-ppa');
    if (addAdmBtn) addAdmBtn.addEventListener('click', function(e){ e.preventDefault(); addADMPPA(); });
    // PCT helpers
    wirePctValidation();
    // RMA/Reading validation wiring on demand
    const tab = new URLSearchParams(window.location.search).get('tab');
    if (tab === 'rma') wireRMAVerification();
    if (tab === 'reading') wireReadingVerification();
    // Sort Performance Snapshot grade items by Grade 1..12 within each subject list
    setTimeout(() => {
      try {
        if (window.sortPerformanceSnapshot) window.sortPerformanceSnapshot();
      } catch (e) {}
    }, 0);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();

  // Globals required by inline onclicks
  window.addProjectRow = addProjectRow;
  window.addActivityRow = addActivityRow;
  window.toggleGrade = toggleGrade;
  window.toggleSubject = toggleSubject;
  window.toggleADMFields = toggleADMFields;
  window.addADMPPA = addADMPPA;
  // Ensure toggles are initialized on page load
  attachActivityHeaderToggles();
});

// Helper: sort Performance Snapshot lists by numeric grade order (Grade 1..12, Kinder=0)
(function(){
  function gradeToNum(label) {
    if (!label) return 999;
    const t = label.trim();
    if (/^Kinder$/i.test(t)) return 0;
    const m = t.match(/Grade\s+(\d+)/i);
    if (m) return parseInt(m[1], 10);
    return 999;
  }
  window.sortPerformanceSnapshot = function sortPerformanceSnapshot() {
    // 1) Sort each subject's list items by grade number
    document.querySelectorAll('.slp-summary-list').forEach(ul => {
      const items = Array.from(ul.querySelectorAll('li.slp-summary-item'));
      items.sort((a, b) => {
        const ga = gradeToNum(a.querySelector('.slp-summary-grade')?.textContent || '');
        const gb = gradeToNum(b.querySelector('.slp-summary-grade')?.textContent || '');
        return ga - gb;
      });
      items.forEach(li => ul.appendChild(li));
    });   

    // 2) Sort the subject sections within each column by the lowest grade appearing in that subject
    document.querySelectorAll('.slp-summary-column').forEach(column => {
      const subjects = Array.from(column.querySelectorAll('.slp-summary-subject'));
      subjects.sort((sa, sb) => {
        const la = sa.querySelectorAll('.slp-summary-grade');
        const lb = sb.querySelectorAll('.slp-summary-grade');
        const mina = la.length ? Math.min(...Array.from(la).map(el => gradeToNum(el.textContent || ''))) : 999;
        const minb = lb.length ? Math.min(...Array.from(lb).map(el => gradeToNum(el.textContent || ''))) : 999;
        return mina - minb;
      });
      subjects.forEach(s => column.appendChild(s));
    });
  };

  // Removed Suggested DNME Action Focus sorting per user request
})();










