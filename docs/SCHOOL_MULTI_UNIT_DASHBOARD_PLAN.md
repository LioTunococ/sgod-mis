# School Multi-Unit Dashboard Plan

## Problem Statement
The current school portal (`dashboards/school_home.html`) is hardcoded to show only **"SMEA Submission Dashboard"** (which is actually SMME), but schools need to submit forms for **6 different units**:

1. **YFS** - Youth Formation Section
2. **PR** - Planning and Research Section
3. **SMME** - School Management, Monitoring and Evaluation Section
4. **HRD** - Human Resource Development Section
5. **SMN** - Social Mobilization and Networking Section
6. **DRRM** - Disaster Risk Reduction and Management Section

The Quarter and School Year filters should apply to **ALL forms across ALL units**, not just one section.

---

## Current Implementation Analysis

### Current Template Structure (`school_home.html`)
```html
<!-- School Year & Quarter Selection -->
<section class="card" style="margin-bottom: 1.5rem;">
  <div class="flex-between" style="margin-bottom: 1rem;">
    <div>
      <h2>SMEA Submission Dashboard</h2>  <!-- ❌ HARDCODED -->
      <p class="muted">Manage your quarterly school reports</p>
    </div>
    <div class="form-field" style="margin: 0;">
      <label>SCHOOL YEAR</label>
      <select name="school_year" onchange="window.location.href='?school_year='+this.value">
        <!-- School year options -->
      </select>
    </div>
  </div>

  <!-- Quarter Cards (Q1, Q2, Q3, Q4) -->
  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.75rem;">
    {% for quarter in quarter_stats %}
      <!-- Quarter cards with stats -->
    {% endfor %}
  </div>
</section>
```

### Current View Logic (`dashboards/views.py`)
The `school_home()` view already has good infrastructure:
- ✅ Fetches ALL sections (not just SMME)
- ✅ Groups drafts by section (`drafts_by_section`)
- ✅ Counts open forms per section (`open_counts`)
- ✅ Builds `section_cards` with all units
- ✅ Shows forms from all sections in unified view

**BUT**: The template only renders one hardcoded section title instead of showing all sections.

---

## Proposed Solution

### Option A: Tabbed Multi-Unit Dashboard (RECOMMENDED)
**Visual Structure:**
```
┌─────────────────────────────────────────────────────────────┐
│ Pudtol Vocational High School                               │
│ Code: 55555 · District: Pudtol                              │
│ [Update School Profile]                                     │
├─────────────────────────────────────────────────────────────┤
│ IN PROGRESS: 3 | SUBMITTED: 12 | RETURNS: 1 | OPEN: 8      │
├─────────────────────────────────────────────────────────────┤
│                           SCHOOL YEAR: [2024-2025 ▼]        │
│                                                              │
│ ┌─[SMME]─┬─[YFS]─┬─[HRD]─┬─[DRRM]─┬─[SMN]─┬─[PR]─┐       │
│ │                                                   │       │
│ │  SMME - School Management, Monitoring & Eval     │       │
│ │                                                   │       │
│ │  ┌────────┬────────┬────────┬────────┐          │       │
│ │  │  Q1    │  Q2    │  Q3    │  Q4    │          │       │
│ │  │   3    │   2    │   0    │   0    │          │       │
│ │  └────────┴────────┴────────┴────────┘          │       │
│ │                                                   │       │
│ │  📝 In Progress (2)                               │       │
│ │  ├─ SMME Form Q1 (45% complete)                  │       │
│ │  └─ SMME Form Q2 (78% complete)                  │       │
│ │                                                   │       │
│ │  ✅ Available Forms (3)                          │       │
│ │  ├─ SMME Form Q3 (Due: Nov 15, 2025)             │       │
│ │  └─ SMME Annual Report (Due: Dec 30, 2025)       │       │
│ │                                                   │       │
│ └───────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- ✅ Tabs for each unit (show only units with active forms)
- ✅ Quarter cards filter by selected unit
- ✅ School year dropdown applies to all units
- ✅ Each tab shows unit-specific drafts and available forms
- ✅ Visual consistency with current design
- ✅ Scalable (easy to add new units)

---

### Option B: Unified Multi-Section View (Alternative)
All sections displayed vertically on same page:

```
┌─────────────────────────────────────────────────────────────┐
│ SCHOOL YEAR: [2024-2025 ▼]    QUARTER: [All ▼]             │
├─────────────────────────────────────────────────────────────┤
│ SMME - School Management (3 forms)                          │
│ ┌────────┬────────┬────────┬────────┐                      │
│ │  Q1: 3 │  Q2: 2 │  Q3: 0 │  Q4: 0 │                      │
│ └────────┴────────┴────────┴────────┘                      │
├─────────────────────────────────────────────────────────────┤
│ YFS - Youth Formation (1 form)                              │
│ ┌────────┬────────┬────────┬────────┐                      │
│ │  Q1: 1 │  Q2: 0 │  Q3: 0 │  Q4: 0 │                      │
│ └────────┴────────┴────────┴────────┘                      │
├─────────────────────────────────────────────────────────────┤
│ ... (other sections)                                        │
└─────────────────────────────────────────────────────────────┘
```

**Pros:** Simple, see everything at once
**Cons:** Gets long with 6+ sections, harder to focus

---

## Recommended Implementation: Tabbed Dashboard

### Phase 1: Data Structure Updates

#### 1.1 Update View Logic (`dashboards/views.py`)
```python
def school_home(request):
    # ... existing code ...
    
    # NEW: Get selected section (default to first with forms)
    selected_section_code = request.GET.get('section', None)
    
    # Build quarter stats PER SECTION
    quarter_stats_by_section = {}
    for section in sections:
        quarter_stats = []
        for quarter in ['Q1', 'Q2', 'Q3', 'Q4']:
            # Count submissions for this section + quarter + school_year
            count = Submission.objects.filter(
                school=school,
                form_template__section=section,
                period__school_year_start=school_year_start,
                period__quarter=quarter
            ).count()
            quarter_stats.append({
                'quarter': quarter,
                'count': count,
                'is_selected': quarter == selected_quarter
            })
        quarter_stats_by_section[section.code] = quarter_stats
    
    # Auto-select first section with forms if none selected
    if not selected_section_code and section_cards:
        selected_section_code = section_cards[0]['section'].code
    
    context = {
        'section_cards': section_cards,
        'selected_section_code': selected_section_code,
        'quarter_stats_by_section': quarter_stats_by_section,
        'selected_school_year': selected_school_year,
        'selected_quarter': selected_quarter,
        # ... existing context ...
    }
```

#### 1.2 Template Structure (`school_home.html`)
```html
<!-- School Year Filter (applies to ALL sections) -->
<div class="school-year-filter">
  <label>SCHOOL YEAR</label>
  <select name="school_year" onchange="filterBySchoolYear(this.value)">
    {% for year in available_school_years %}
      <option value="{{ year }}" {% if year == selected_school_year %}selected{% endif %}>
        {{ year }}
      </option>
    {% endfor %}
  </select>
</div>

<!-- Section Tabs -->
<div class="section-tabs">
  {% for section_card in section_cards %}
    <button 
      class="section-tab {% if section_card.section.code == selected_section_code %}active{% endif %}"
      onclick="selectSection('{{ section_card.section.code }}')">
      {{ section_card.section.code|upper }}
      {% if section_card.drafts_count > 0 or section_card.open_count > 0 %}
        <span class="tab-badge">{{ section_card.drafts_count|add:section_card.open_count }}</span>
      {% endif %}
    </button>
  {% endfor %}
</div>

<!-- Active Section Content -->
{% for section_card in section_cards %}
  <div 
    class="section-content" 
    id="section-{{ section_card.section.code }}"
    {% if section_card.section.code != selected_section_code %}style="display: none;"{% endif %}>
    
    <h2>{{ section_card.section.name }}</h2>
    <p class="muted">Manage your {{ section_card.section.code|upper }} submissions</p>
    
    <!-- Quarter Cards (filtered by this section) -->
    <div class="quarter-grid">
      {% for quarter in quarter_stats_by_section|get_item:section_card.section.code %}
        <div class="quarter-card {% if quarter.is_selected %}active{% endif %}">
          <div class="quarter-label">{{ quarter.quarter }}</div>
          <div class="quarter-count">{{ quarter.count }}</div>
          <div class="quarter-status">
            {% if quarter.count > 0 %}Submitted{% else %}Not Started{% endif %}
          </div>
        </div>
      {% endfor %}
    </div>
    
    <!-- In Progress Forms -->
    {% if section_card.drafts_count > 0 %}
      <div class="drafts-section">
        <h3>📝 In Progress ({{ section_card.drafts_count }})</h3>
        {% for draft in section_card.drafts %}
          <div class="draft-card">
            <div class="draft-title">{{ draft.submission.form_template.title }}</div>
            <div class="draft-progress">{{ draft.progress }}% complete</div>
            <a href="{% url 'edit_submission' draft.submission.id %}" class="btn btn--sm">Continue</a>
          </div>
        {% endfor %}
      </div>
    {% endif %}
    
    <!-- Available Forms -->
    {% if section_card.open_count > 0 %}
      <div class="available-forms">
        <h3>✅ Available Forms ({{ section_card.open_count }})</h3>
        {% for form_info in section_card.available_forms %}
          <div class="form-card">
            <div class="form-title">{{ form_info.form_template.title }}</div>
            <div class="form-deadline">Due: {{ form_info.deadline|date:"M d, Y" }}</div>
            <a href="{% url 'new_submission' form_info.form_template.code %}" class="btn btn--primary btn--sm">
              Start Form
            </a>
          </div>
        {% endfor %}
      </div>
    {% endif %}
    
  </div>
{% endfor %}

<script>
function selectSection(sectionCode) {
  // Hide all section contents
  document.querySelectorAll('.section-content').forEach(el => el.style.display = 'none');
  
  // Show selected section
  document.getElementById('section-' + sectionCode).style.display = 'block';
  
  // Update tab active states
  document.querySelectorAll('.section-tab').forEach(tab => tab.classList.remove('active'));
  event.target.classList.add('active');
  
  // Update URL without reload
  const url = new URL(window.location);
  url.searchParams.set('section', sectionCode);
  window.history.pushState({}, '', url);
}

function filterBySchoolYear(schoolYear) {
  const url = new URL(window.location);
  url.searchParams.set('school_year', schoolYear);
  window.location.href = url.toString();
}
</script>
```

---

### Phase 2: CSS Styling

#### 2.1 Add Tab Styles (to `app.css`)
```css
/* Section Tabs */
.section-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid #e5e7eb;
  overflow-x: auto;
}

.section-tab {
  padding: 0.75rem 1.5rem;
  background: none;
  border: none;
  border-bottom: 3px solid transparent;
  color: #6b7280;
  font-weight: 500;
  font-size: 0.875rem;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
  position: relative;
}

.section-tab:hover {
  color: #1f2937;
  background: #f9fafb;
}

.section-tab.active {
  color: #2563eb;
  border-bottom-color: #2563eb;
  font-weight: 600;
}

.tab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.25rem;
  height: 1.25rem;
  padding: 0 0.375rem;
  margin-left: 0.5rem;
  background: #ef4444;
  color: white;
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 9999px;
}

.section-tab.active .tab-badge {
  background: #2563eb;
}

/* Quarter Grid */
.quarter-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
  margin-bottom: 2rem;
}

.quarter-card {
  padding: 1.25rem;
  background: #f9fafb;
  border: 2px solid #e5e7eb;
  border-radius: 0.5rem;
  text-align: center;
  transition: all 0.2s;
  cursor: pointer;
}

.quarter-card:hover {
  border-color: #2563eb;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
}

.quarter-card.active {
  background: #eff6ff;
  border-color: #2563eb;
}

.quarter-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  margin-bottom: 0.5rem;
}

.quarter-count {
  font-size: 2rem;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 0.25rem;
}

.quarter-status {
  font-size: 0.75rem;
  color: #6b7280;
}
```

---

### Phase 3: Database Query Optimization

#### 3.1 Update View to Prefetch All Data
```python
# Optimize queries for multi-section view
section_cards_optimized = []

for section in sections:
    # Get quarter breakdown
    quarter_breakdown = {}
    for quarter in ['Q1', 'Q2', 'Q3', 'Q4']:
        quarter_breakdown[quarter] = Submission.objects.filter(
            school=school,
            form_template__section=section,
            period__school_year_start=school_year_start,
            period__quarter=quarter
        ).values('status').annotate(count=Count('id'))
    
    section_cards_optimized.append({
        'section': section,
        'drafts': drafts_by_section.get(section.id, []),
        'available_forms': available_forms_by_section.get(section.id, []),
        'quarter_breakdown': quarter_breakdown,
        'total_submissions': sum(q.get('count', 0) for q in quarter_breakdown.values())
    })
```

---

## Benefits

### For Schools
✅ **Clear organization** - Forms grouped by government unit/section  
✅ **Quick navigation** - Tab switching without page reload  
✅ **Complete visibility** - See all submission requirements across all units  
✅ **Progress tracking** - Per-unit and per-quarter progress at a glance  
✅ **Unified filters** - School year applies to entire dashboard  

### For SGOD Administrators
✅ **Accurate reporting** - Schools can't miss forms from other units  
✅ **Better compliance** - Visibility increases submission rates  
✅ **Scalable design** - Easy to add new sections/units in the future  
✅ **Data integrity** - All forms tracked in one unified system  

### For Development
✅ **Uses existing data** - No database changes needed  
✅ **Reuses view logic** - `section_cards` already built  
✅ **Progressive enhancement** - Add tabs without breaking existing functionality  
✅ **Mobile-friendly** - Horizontal scrolling tabs work on small screens  

---

## Implementation Checklist

### Week 1: Core Functionality
- [ ] Update `dashboards/views.py` to build `quarter_stats_by_section`
- [ ] Add `selected_section_code` query parameter handling
- [ ] Update context with new data structures
- [ ] Modify `school_home.html` template structure
- [ ] Add section tabs navigation
- [ ] Add JavaScript for tab switching
- [ ] Test with existing schools (Flora NHS, Luna NHS, Pudtol VHS)

### Week 2: Styling & Polish
- [ ] Add CSS for `.section-tabs` and `.section-tab`
- [ ] Style `.quarter-grid` and `.quarter-card`
- [ ] Add hover states and transitions
- [ ] Add responsive mobile layout
- [ ] Add loading states for tab switching
- [ ] Test on different screen sizes

### Week 3: Testing & Documentation
- [ ] Test all 6 sections (SMME, YFS, HRD, DRRM, SMN, PR)
- [ ] Verify quarter filtering works per section
- [ ] Test school year changes persist selected section
- [ ] Write unit tests for new view logic
- [ ] Update AGENT.md with new dashboard structure
- [ ] Create user documentation/guide

---

## Edge Cases to Handle

1. **No active forms** - Show empty state: "No forms available for this section"
2. **Only one section** - Hide tabs, show single section directly
3. **URL bookmark** - Preserve `?section=smme&school_year=2024-2025` in URLs
4. **Missing data** - Handle schools with no submissions gracefully
5. **Mobile layout** - Horizontal scrolling tabs on small screens

---

## Future Enhancements (Phase 4+)

### Analytics Dashboard
- Completion rates per section
- Time-to-completion metrics
- Historical trends (year-over-year comparison)

### Notification System
- Email alerts for approaching deadlines
- Push notifications for returned submissions
- Daily digest of pending forms

### Batch Operations
- "Complete all Q1 forms" workflow
- Bulk upload attachments
- Copy previous quarter data

### Advanced Filtering
- Filter by submission status (draft/submitted/returned)
- Search forms by title
- Sort by deadline

---

## Success Metrics

**Before Implementation:**
- ❌ Only SMME forms visible to schools
- ❌ Schools miss forms from other units
- ❌ Confusion about which forms to submit
- ❌ Low completion rates for non-SMME forms

**After Implementation:**
- ✅ All 6 unit forms visible in tabbed interface
- ✅ Schools can navigate between units easily
- ✅ Clear visibility of all submission requirements
- ✅ Increased completion rates across all units
- ✅ Reduced support requests about "missing forms"

---

## Technical Debt Addressed

1. **Hardcoded section name** - Replaced with dynamic section tabs
2. **Single-unit view** - Expanded to multi-unit dashboard
3. **Inflexible filtering** - Added per-section quarter filtering
4. **Poor scalability** - Tab system supports unlimited sections

---

## Risk Assessment

**LOW RISK** because:
- ✅ View already fetches all sections (`section_cards`)
- ✅ No database migrations required
- ✅ Existing functionality preserved
- ✅ Progressive enhancement approach
- ✅ Easy to roll back if issues arise

**Potential Issues:**
- ⚠️ Performance with many sections (6 sections × 4 quarters = 24 queries)
  - **Mitigation**: Use `select_related()` and `prefetch_related()`
- ⚠️ Mobile UX with many tabs
  - **Mitigation**: Horizontal scroll, touch-friendly tap targets
- ⚠️ User confusion with new interface
  - **Mitigation**: Clear labels, tooltips, user guide

---

## Conclusion

The tabbed multi-unit dashboard is the **recommended solution** because it:
1. Solves the immediate problem (visibility of all unit forms)
2. Scales to support future sections/units
3. Maintains visual consistency with current design
4. Requires minimal code changes
5. Improves user experience significantly

**Next Step**: Review this plan, then proceed with Week 1 implementation.
