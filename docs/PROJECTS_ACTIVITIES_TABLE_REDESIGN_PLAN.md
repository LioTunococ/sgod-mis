# Projects & Activities Table Redesign Plan

## Overview
Redesign the Projects & Activities section to match the clean, simple table format used in Instructional Supervision and ADM sections, while maintaining the hierarchical structure (Projects → Activities).

---

## Current Structure Analysis

### Models
1. **SMEAProject** (Parent)
   - `project_title`: CharField(255)
   - `area_of_concern`: CharField(255)
   - `conference_date`: DateField
   - ForeignKey to Submission

2. **SMEAActivityRow** (Child - many per project)
   - `activity`: TextField
   - `output_target`: TextField
   - `output_actual`: TextField
   - `timeframe_target`: TextField
   - `timeframe_actual`: TextField
   - `budget_target`: CharField(64)
   - `budget_actual`: CharField(64)
   - `interpretation`: TextField (Progress Interpretation)
   - `issues_unaddressed`: TextField (Issues/Gaps)
   - `facilitating_factors`: TextField
   - `agreements`: TextField (Agreements/Next Steps)
   - `row_order`: PositiveIntegerField
   - ForeignKey to SMEAProject

### Current UI Approach
- **Separate pages** for adding projects (`add_project.html`) and activities (`add_activity.html`)
- **Complex nested structure**: Each project is a card containing a table of activities
- **11 columns** in activity table (very wide, requires horizontal scrolling)
- **"Add New Project"** button at top
- **"Add Activity"** button for each project

### Challenges
1. **Two-level hierarchy**: Projects contain multiple activities
2. **Wide table**: 11 columns make it hard to view
3. **Separate forms**: Adding projects/activities requires navigation to different pages
4. **Complex navigation**: Users leave the main form to add data

---

## Proposed Redesign

### Option A: Single Inline Table with Project Headers (RECOMMENDED)

**Visual Structure:**
```
IV. PROJECTS AND ACTIVITIES

┌─────────────────────────────────────────────────────────────────┐
│ Project: [Project Title Input]                                   │
│ Area of Concern: [Input]   Conference Date: [Date]               │
│ [Remove Project]                                                  │
└─────────────────────────────────────────────────────────────────┘

TABLE:
┌──────────────┬────────┬────────┬─────────┬─────────┬────────┐
│ Activity     │ Output │ Output │ Budget  │ Budget  │ Action │
│              │ Target │ Actual │ Target  │ Actual  │        │
├──────────────┼────────┼────────┼─────────┼─────────┼────────┤
│ [textarea]   │ [text] │ [text] │ [text]  │ [text]  │   —    │
│ [textarea]   │ [text] │ [text] │ [text]  │ [text]  │ Remove │
│ [textarea]   │ [text] │ [text] │ [text]  │ [text]  │ Remove │
└──────────────┴────────┴────────┴─────────┴─────────┴────────┘

[Add Activity Row]

┌─────────────────────────────────────────────────────────────────┐
│ Project: [Another Project Title]                                 │
│ Area of Concern: [Input]   Conference Date: [Date]               │
│ [Remove Project]                                                  │
└─────────────────────────────────────────────────────────────────┘

TABLE:
┌──────────────┬────────┬────────┬─────────┬─────────┬────────┐
│ Activity     │ Output │ Output │ Budget  │ Budget  │ Action │
│              │ Target │ Actual │ Target  │ Actual  │        │
├──────────────┼────────┼────────┼─────────┼─────────┼────────┤
│ [textarea]   │ [text] │ [text] │ [text]  │ [text]  │   —    │
└──────────────┴────────┴────────┴─────────┴─────────┴────────┘

[Add Activity Row]

[Add New Project]
```

**Features:**
- ✅ Each project = header card + its own table
- ✅ Simplified to 5 columns (removed timeframe, interpretation, issues, facilitating factors, agreements)
- ✅ Inline editing (no separate pages)
- ✅ "Add Activity Row" button adds rows to current project's table
- ✅ "Add New Project" button at bottom creates new project section
- ✅ Remove functionality with instant feedback (like ADM)
- ✅ All editing happens on one page

---

### Option B: Simplified Single Project with Analysis Questions

**Visual Structure:**
```
IV. PROJECTS AND ACTIVITIES

┌─────────────────────────────────────────────────────────────────┐
│ Project Title: [Input]                                           │
│ Area of Concern: [Input]   Conference Date: [Date]               │
└─────────────────────────────────────────────────────────────────┘

TABLE:
┌──────────────┬────────┬────────┬─────────┬─────────┬────────┐
│ Activity     │ Output │ Output │ Budget  │ Budget  │ Action │
│              │ Target │ Actual │ Target  │ Actual  │        │
├──────────────┼────────┼────────┼─────────┼─────────┼────────┤
│ [textarea]   │ [text] │ [text] │ [text]  │ [text]  │   —    │
│ [textarea]   │ [text] │ [text] │ [text]  │ [text]  │ Remove │
└──────────────┴────────┴────────┴─────────┴─────────┴────────┘

[Add Activity Row]

OVERALL PROJECT ANALYSIS (for all activities):
1. Progress Interpretation: [textarea]
2. Issues/Gaps: [textarea]
3. Facilitating Factors: [textarea]
4. Agreements/Next Steps: [textarea]
```

**Features:**
- ✅ Assumes ONE main project per submission
- ✅ Simplified 5-column table for activities
- ✅ Analysis questions appear once (like ADM)
- ✅ Questions apply to entire project, not per activity
- ✅ Simplest approach

---

## Recommended Approach: **Option A**

### Why Option A?
1. **Maintains flexibility**: Schools can track multiple projects
2. **Clear hierarchy**: Each project has its own visible header and table
3. **Similar to ADM**: Multiple sections with tables (familiar pattern)
4. **No data loss**: All existing projects/activities preserved
5. **Inline editing**: Everything on one page (like Supervision/ADM)

---

## Implementation Steps

### Phase 1: Backend Changes

#### 1.1 Create Django FormSets
```python
# submissions/forms.py

SMEAProjectFormSet = inlineformset_factory(
    Submission,
    SMEAProject,
    fields=['project_title', 'area_of_concern', 'conference_date'],
    extra=1,
    can_delete=True
)

SMEAActivityFormSet = inlineformset_factory(
    SMEAProject,
    SMEAActivityRow,
    fields=['activity', 'output_target', 'output_actual', 
            'budget_target', 'budget_actual'],
    extra=1,
    can_delete=True,
    widgets={
        'activity': Textarea(attrs={'rows': 2, 'class': 'project-field'}),
        'output_target': TextInput(attrs={'class': 'project-field'}),
        'output_actual': TextInput(attrs={'class': 'project-field'}),
        'budget_target': TextInput(attrs={'class': 'project-field'}),
        'budget_actual': TextInput(attrs={'class': 'project-field'}),
    }
)
```

#### 1.2 Update Views
```python
# submissions/views.py - edit_submission()

# Add to context when current_tab == 'projects'
if current_tab == 'projects':
    projects_formset = SMEAProjectFormSet(
        request.POST or None,
        instance=submission,
        prefix='projects'
    )
    
    # Create activity formsets for each project
    activity_formsets = []
    for project_form in projects_formset:
        if project_form.instance.pk:
            activity_formset = SMEAActivityFormSet(
                request.POST or None,
                instance=project_form.instance,
                prefix=f'activities_{project_form.instance.pk}'
            )
            activity_formsets.append({
                'project_form': project_form,
                'activity_formset': activity_formset
            })
    
    context['projects_formset'] = projects_formset
    context['activity_formsets'] = activity_formsets
```

#### 1.3 Handle Saving
```python
# In save logic
if current_tab == 'projects' and projects_formset.is_valid():
    projects_formset.save()
    
    # Save each activity formset
    for formset_data in activity_formsets:
        if formset_data['activity_formset'].is_valid():
            formset_data['activity_formset'].save()
```

### Phase 2: Frontend Template Changes

#### 2.1 Replace Projects Section
```html
{% if current_tab == 'projects' %}
  <div class="card">
    <h3 style="margin-bottom: 1rem;">IV. PROJECTS AND ACTIVITIES</h3>
    
    {{ projects_formset.management_form }}
    
    {% for project_form in projects_formset %}
      <div class="project-section" data-project-index="{{ forloop.counter0 }}">
        
        {# Project Header Card #}
        <div class="card" style="background: #f0f9ff; margin-bottom: 0.5rem;">
          <div class="form-grid form-grid--three">
            <div class="form-field" style="grid-column: span 2;">
              <label class="form-label">Project Title</label>
              {{ project_form.project_title }}
            </div>
            <div class="form-field">
              <label class="form-label">
                {{ project_form.DELETE }}
                Remove Project
              </label>
            </div>
          </div>
          <div class="form-grid form-grid--two">
            <div class="form-field">
              <label class="form-label">Area of Concern</label>
              {{ project_form.area_of_concern }}
            </div>
            <div class="form-field">
              <label class="form-label">Conference Date</label>
              {{ project_form.conference_date }}
            </div>
          </div>
          {{ project_form.id }}
        </div>
        
        {# Activities Table #}
        {% if project_form.instance.pk %}
          {% with activity_formset=activity_formsets|get_formset:forloop.counter0 %}
            {{ activity_formset.management_form }}
            
            <table class="data-table">
              <thead>
                <tr>
                  <th>Activity</th>
                  <th>Output Target</th>
                  <th>Output Actual</th>
                  <th>Budget Target</th>
                  <th>Budget Actual</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody class="activity-table-body" data-project="{{ project_form.instance.pk }}">
                {% for activity_form in activity_formset %}
                  <tr class="activity-row" data-activity-index="{{ forloop.counter0 }}">
                    {{ activity_form.id }}
                    <td>{{ activity_form.activity }}</td>
                    <td>{{ activity_form.output_target }}</td>
                    <td>{{ activity_form.output_actual }}</td>
                    <td>{{ activity_form.budget_target }}</td>
                    <td>{{ activity_form.budget_actual }}</td>
                    <td>
                      {% if forloop.first %}
                        —
                      {% else %}
                        {{ activity_form.DELETE }}
                      {% endif %}
                    </td>
                  </tr>
                {% endfor %}
              </tbody>
            </table>
            
            <button type="button" class="btn btn--secondary" 
                    style="margin-top: 0.5rem; margin-bottom: 1.5rem;"
                    onclick="addActivityRow({{ project_form.instance.pk }})">
              Add Activity Row
            </button>
          {% endwith %}
        {% endif %}
        
      </div>
    {% endfor %}
    
    <button type="button" class="btn btn--primary" 
            style="margin-top: 1rem;"
            id="add-project-btn">
      Add New Project
    </button>
  </div>
  
  {# Navigation #}
  <div style="display: flex; justify-content: space-between; margin-top: 1.5rem;">
    <span></span> {# First tab, no previous #}
    <div style="display: flex; gap: 0.75rem;">
      <button type="submit" class="btn btn--primary" name="action" value="save_draft">Save Draft</button>
      <a href="?tab=pct" class="btn btn--primary">Next</a>
    </div>
  </div>
{% endif %}
```

#### 2.2 Add JavaScript for Dynamic Rows
```javascript
// Add activity row functionality
function addActivityRow(projectId) {
  const tableBody = document.querySelector(`.activity-table-body[data-project="${projectId}"]`);
  const firstRow = tableBody.querySelector('.activity-row');
  
  if (!firstRow) return;
  
  const newRow = firstRow.cloneNode(true);
  const totalFormsInput = tableBody.closest('form').querySelector(`input[name="activities_${projectId}-TOTAL_FORMS"]`);
  const formIndex = parseInt(totalFormsInput.value);
  
  // Update form indices in cloned row
  newRow.querySelectorAll('input, textarea, select').forEach(field => {
    if (field.name) {
      field.name = field.name.replace(/-\d+-/, `-${formIndex}-`);
      field.id = field.id ? field.id.replace(/-\d+-/, `-${formIndex}-`) : '';
      field.value = '';
    }
  });
  
  // Show remove checkbox
  const actionCell = newRow.querySelector('td:last-child');
  actionCell.innerHTML = `<input type="checkbox" name="activities_${projectId}-${formIndex}-DELETE" id="id_activities_${projectId}-${formIndex}-DELETE">`;
  
  tableBody.appendChild(newRow);
  totalFormsInput.value = formIndex + 1;
  
  attachDeleteHandlers();
}

// Add project functionality
document.getElementById('add-project-btn')?.addEventListener('click', function() {
  // Clone first project section and update indices
  // Similar logic to addActivityRow but for projects
});

// Delete handlers (same as ADM)
function attachDeleteHandlers() {
  const deleteCheckboxes = document.querySelectorAll('input[name*="DELETE"]');
  deleteCheckboxes.forEach(function(checkbox) {
    checkbox.removeEventListener('click', handleDeleteClick);
    checkbox.addEventListener('click', handleDeleteClick);
  });
}

function handleDeleteClick(e) {
  const checkbox = e.target;
  const row = checkbox.closest('tr') || checkbox.closest('.project-section');
  
  if (checkbox.checked) {
    if (confirm('Are you sure you want to remove this?')) {
      row.remove();
    } else {
      checkbox.checked = false;
    }
  }
}
```

### Phase 3: Migration & Data Preservation

**No migration needed!** Existing data structure remains the same. Only the UI changes.

---

## Removed Fields (Optional - Discuss with User)

The following fields are currently in the wide table but could be:
1. **Removed entirely** (if not needed)
2. **Moved to analysis questions** (overall, not per-activity)
3. **Kept in simplified format**

### Fields to Consider:
- ❓ **Timeframe Target/Actual**: Remove or keep?
- ❓ **Progress Interpretation**: Move to overall analysis?
- ❓ **Issues/Gaps**: Move to overall analysis?
- ❓ **Facilitating Factors**: Move to overall analysis?
- ❓ **Agreements/Next Steps**: Move to overall analysis?

### Recommended: Remove from table, add as overall analysis questions
This makes each project section similar to ADM structure.

---

## Testing Checklist

- [ ] Create new project inline
- [ ] Add activities to project inline
- [ ] Remove activity with checkbox (instant feedback)
- [ ] Remove project with checkbox
- [ ] Save draft preserves all data
- [ ] Multiple projects display correctly
- [ ] Navigation buttons work (Next to PCT)
- [ ] Existing projects load correctly
- [ ] Form validation works
- [ ] Responsive design on mobile

---

## Rollback Plan

If issues arise:
1. Keep current `add_project.html` and `add_activity.html` templates
2. Keep current URL routes in `urls.py`
3. Template changes are isolated to `edit_submission.html`
4. Can revert template changes without affecting database

---

## Timeline Estimate

- **Backend (FormSets + Views)**: 1-2 hours
- **Frontend (Template + JavaScript)**: 2-3 hours
- **Testing**: 1 hour
- **Total**: 4-6 hours

---

## Questions for User

1. **Field simplification**: OK to reduce from 11 columns to 5? Which fields are essential?
2. **Analysis questions**: Move interpretation/issues/factors/agreements to overall project analysis (like ADM)?
3. **Multiple projects**: Keep support for multiple projects per submission?
4. **Timeframe fields**: Keep or remove? (Target/Actual dates)

---

## Success Metrics

✅ Inline editing (no separate pages)
✅ Clean table format (5-6 columns max)
✅ Clear project hierarchy
✅ Instant remove feedback
✅ Similar UX to Supervision/ADM
✅ All data preserved
✅ Mobile-friendly

---

**Status**: 📋 PLAN READY - Awaiting user feedback on questions above
