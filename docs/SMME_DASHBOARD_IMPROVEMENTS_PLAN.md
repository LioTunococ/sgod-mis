# SMME Admin Dashboard Improvements Plan

**Date:** October 17, 2025  
**Target:** SMME KPI Dashboard (`/dashboards/smme_kpi/`)  
**Current State:** Functional but has inline styles, inconsistent design  
**Goal:** Apply "Boring Design System" + improve UX  
**Layout Reference:** See `docs/SMME_DASHBOARD_LAYOUT.md` for detailed wireframes

---

## Current Dashboard Analysis

### What Works ✅
- **Filtering System**: Period, District, Section dropdowns work well
- **Summary Metrics**: Good at-a-glance KPI cards (5 metrics)
- **Data Table**: Comprehensive district-level KPI breakdown
- **Auto-submit**: Dropdowns trigger form submission automatically

### Issues to Fix 🐛
1. **Inline Styles Anti-pattern**: All styles in `<style>` tag (line 9-26)
2. **Duplicate CSS Link**: `app.css` loaded twice (line 7-8)
3. **Inconsistent Design**: Doesn't match the form system aesthetic
4. **Limited max-width**: Body capped at `1100px` (could use more space)
5. **No Visual Hierarchy**: Summary cards blend with table
6. **Filter Form Layout**: Generic grid, not optimized
7. **Table Responsiveness**: Fixed width table might overflow
8. **No Loading States**: Filter changes have no feedback
9. **Missing Metadata**: No "last updated" or data freshness indicator
10. **No Quarter Navigation**: Can't see all quarters at a glance

---

## Refined Implementation Plan

### Phase 1: Foundation & CSS Cleanup
**Priority:** HIGH  
**Effort:** 2-3 hours  
**Goal:** Remove inline styles, apply design system, maintain functionality

#### Step 1.1: CSS Component Creation (30 min)
Add to `static/css/form-system.css`:

```css
/* ============================================
   DASHBOARD COMPONENTS
   ============================================ */

/* Filter Bar */
.filter-bar {
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius);
  padding: var(--space-6);
  margin-bottom: var(--space-8);
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-4);
  align-items: end;
}

/* Stats Card (KPI Metrics) */
.stats-card {
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: 0.75rem;
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.stats-card__label {
  font-size: var(--text-sm);
  color: var(--color-text-light);
  font-weight: 500;
}

.stats-card__value {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-text);
}

.stats-card__hint {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.stats-card__trend {
  font-size: var(--text-sm);
  font-weight: 600;
}

.stats-card__trend--up { color: var(--color-success); }
.stats-card__trend--down { color: var(--color-error); }
.stats-card__trend--neutral { color: var(--color-text-muted); }

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-8);
}

/* Data Table - KPI Variant */
.data-table--kpi {
  width: 100%;
  border-collapse: collapse;
  background: var(--color-bg);
  border-radius: var(--border-radius);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.data-table--kpi th,
.data-table--kpi td {
  padding: var(--space-3) var(--space-4);
  text-align: left;
  border: 1px solid var(--color-border-light);
}

.data-table--kpi th {
  background: var(--color-bg-subtle);
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--color-text);
  position: sticky;
  top: 0;
  z-index: 10;
}

.data-table--kpi tbody tr:nth-child(even) {
  background: var(--color-bg-subtle);
}

.data-table--kpi tbody tr:hover {
  background: #f0f9ff;
  cursor: pointer;
}

.data-table--kpi tfoot {
  background: var(--color-bg-gray);
  font-weight: 600;
}

/* Table Wrapper for Scroll */
.table-scroll {
  overflow-x: auto;
  margin-bottom: var(--space-8);
  border-radius: var(--border-radius);
  border: 1px solid var(--color-border-light);
}

/* Export Bar */
.export-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) 0;
  margin-bottom: var(--space-4);
  border-top: 1px solid var(--color-border-light);
}

.export-bar__actions {
  display: flex;
  gap: var(--space-3);
}

.export-bar__meta {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}
```

**Tasks:**
- [ ] Add dashboard components to `form-system.css`
- [ ] Test CSS variables are defined
- [ ] Verify no conflicts with existing styles

#### Step 1.2: Template Cleanup (60 min)
Clean up `templates/dashboards/smme_kpi.html`:

**Remove:**
- [ ] `<style>` block (lines 9-26)
- [ ] Duplicate `app.css` link
- [ ] Inline styles in HTML elements

**Add:**
- [ ] Link to `form-system.css`
- [ ] Semantic HTML structure (sections, proper classes)
- [ ] CSS classes from design system

**Structure:**
```html
{% load static %}
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>SMME KPI Dashboard</title>
  <link rel="stylesheet" href="{% static 'css/app.css' %}">
  <link rel="stylesheet" href="{% static 'css/form-system.css' %}">
</head>
<body class="container dashboards-page">
  {% include "includes/auth_nav.html" %}
  
  <h1>SMME KPI Dashboard</h1>
  
  <!-- Filter Bar -->
  <form method="get" class="filter-bar">
    <!-- School Year, District, Section dropdowns -->
  </form>
  
  <!-- KPI Summary -->
  <section class="stats-grid">
    <!-- 6 stats cards -->
  </section>
  
  <!-- Data Table -->
  <section>
    <div class="export-bar">
      <!-- Export buttons + metadata -->
    </div>
    <div class="table-scroll">
      <table class="data-table--kpi">
        <!-- District breakdown -->
      </table>
    </div>
  </section>
</body>
</html>
```

**Tasks:**
- [ ] Refactor template structure
- [ ] Apply CSS classes
- [ ] Test all filters still work
- [ ] Verify table displays correctly

#### Step 1.3: Testing & Validation (30 min)
- [ ] Load dashboard in browser
- [ ] Test all filter combinations
- [ ] Check responsive behavior (desktop, tablet, mobile)
- [ ] Verify no console errors
- [ ] Compare before/after screenshots

---

### Phase 2: Quarter Navigation & UX Enhancements
**Priority:** HIGH  
**Effort:** 3-4 hours  
**Goal:** Add quarter navigation like school dashboard + better metrics

#### Step 2.1: Backend - Quarter Stats (90 min)
Modify `dashboards/views.py` - `smme_kpi_dashboard()` function:

```python
def smme_kpi_dashboard(request):
    user = request.user
    _require_reviewer_access(user)

    # Get selected school year and quarter
    selected_school_year = request.GET.get("school_year", "2025-2026")
    selected_quarter = request.GET.get("quarter")
    
    # Parse school year
    try:
        school_year_start = int(selected_school_year.split('-')[0])
    except (ValueError, IndexError):
        school_year_start = 2025
    
    # Calculate quarter statistics
    quarter_stats = []
    for q in range(1, 5):
        # Get submissions for this quarter
        q_submissions = Submission.objects.filter(
            period__school_year_start=school_year_start,
            period__quarter=f'Q{q}'
        )
        
        # Apply user's section/district filters
        if not account_services.user_is_sgod_admin(user):
            allowed_codes = account_services.allowed_section_codes(user)
            q_submissions = q_submissions.filter(
                form_template__section__code__in=allowed_codes
            )
        
        total_schools = q_submissions.values('school').distinct().count()
        
        quarter_stats.append({
            'quarter': q,
            'total': total_schools,
            'is_current': q == 3,  # TODO: Calculate dynamically
        })
    
    # Existing filter logic...
    period_options = list(Period.objects.order_by("-school_year_start", "-quarter"))
    
    # Filter by selected quarter if provided
    if selected_quarter:
        period = Period.objects.filter(
            school_year_start=school_year_start,
            quarter=f'Q{selected_quarter}'
        ).first()
    else:
        period_id = request.GET.get("period_id") or (
            period_options[0].id if period_options else None
        )
        period = get_object_or_404(Period, pk=period_id) if period_id else _latest_period()
    
    # Rest of existing logic...
    
    return render(
        request,
        "dashboards/smme_kpi.html",
        {
            # Existing context
            "periods": period_options,
            "selected_period": period,
            # New context
            "selected_school_year": selected_school_year,
            "selected_quarter": selected_quarter,
            "quarter_stats": quarter_stats,
            "available_school_years": ['2025-2026', '2024-2025', '2023-2024'],
            # ... rest of context
        },
    )
```

**Tasks:**
- [ ] Add quarter stats calculation
- [ ] Update context data
- [ ] Handle quarter filtering
- [ ] Test backend logic

#### Step 2.2: Frontend - Quarter Navigation (60 min)
Add to template after filter bar:

```html
<!-- Quarter Navigation -->
<section class="quarter-navigation">
  {% for quarter in quarter_stats %}
    <a href="?school_year={{ selected_school_year }}&quarter={{ quarter.quarter }}" 
       class="quarter-card {% if selected_quarter == quarter.quarter|stringformat:'s' or not selected_quarter and quarter.is_current %}quarter-card--active{% endif %}">
      <div class="quarter-card__label">Quarter {{ quarter.quarter }}</div>
      <div class="quarter-card__value">{{ quarter.total }}</div>
      <div class="quarter-card__status">schools</div>
    </a>
  {% endfor %}
  
  <a href="?school_year={{ selected_school_year }}" 
     class="quarter-card {% if not selected_quarter %}quarter-card--active{% endif %}">
    <div class="quarter-card__label">View All</div>
  </a>
</section>
```

**Tasks:**
- [ ] Add quarter navigation HTML
- [ ] Verify quarter-card CSS exists (from school dashboard)
- [ ] Test quarter filtering
- [ ] Check active state styling

#### Step 2.3: Enhanced Metrics (90 min)
Improve summary cards with trends and color coding:

```html
<section class="stats-grid">
  <div class="stats-card">
    <span class="stats-card__label">Total Schools</span>
    <span class="stats-card__value">{{ summary_metrics.total_schools }}</span>
    <span class="stats-card__hint">{{ summary_metrics.completion_rate }}% completion rate</span>
  </div>
  
  <div class="stats-card">
    <span class="stats-card__label">Submitted Forms</span>
    <span class="stats-card__value">{{ summary_metrics.submitted_count }}</span>
    {% if summary_metrics.trend %}
      <span class="stats-card__trend stats-card__trend--{{ summary_metrics.trend_direction }}">
        {{ summary_metrics.trend }}% {% if summary_metrics.trend_direction == 'up' %}↑{% else %}↓{% endif %}
      </span>
    {% endif %}
  </div>
  
  <!-- Repeat for other metrics -->
</section>
```

**Backend calculation for trends:**
```python
# In _build_kpi_context(), add trend calculation
prev_period = Period.objects.filter(
    school_year_start=period.school_year_start,
    quarter=f'Q{int(period.quarter[1]) - 1}'
).first()

if prev_period:
    prev_metrics = _calculate_metrics(prev_period)
    trend = ((current_submitted - prev_submitted) / prev_submitted) * 100
    summary_metrics['trend'] = round(trend, 1)
    summary_metrics['trend_direction'] = 'up' if trend > 0 else 'down'
```

**Tasks:**
- [ ] Add trend calculation to backend
- [ ] Update summary card template
- [ ] Add trend styling
- [ ] Test with real data

---

### Phase 3: Export & Metadata
**Priority:** MEDIUM  
**Effort:** 2-3 hours  
**Goal:** Add CSV export + show data freshness

#### Step 3.1: Export CSV Functionality (90 min)
Create new view in `dashboards/views.py`:

```python
@login_required
def export_smme_kpi_csv(request):
    user = request.user
    _require_reviewer_access(user)
    
    # Get same filters as dashboard
    period_id = request.GET.get("period_id")
    district_id = request.GET.get("district_id")
    section_code = request.GET.get("section_code")
    
    # Build KPI data
    kpi_context = _build_kpi_context(...)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="smme_kpi_{period.label}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'District', 'Total Schools', 'Submitted', 'Completion Rate %',
        'DNME %', 'DNME Learners', 'Total Enrolment', 
        'Avg ADM Burn Rate %', 'PHILIRI Band 10 Total'
    ])
    
    for row in kpi_context['kpi_rows']:
        writer.writerow([
            row['district'].name if row['district'] else 'Unassigned',
            row['total_schools'],
            row['submitted_count'],
            row['completion_rate'],
            row['dnme_percent'],
            row['total_dnme'],
            row['total_enrolment'],
            row['average_burn_rate'],
            row['philiri_band10_total'],
        ])
    
    return response
```

Add URL in `dashboards/urls.py`:
```python
path('smme_kpi/export/', views.export_smme_kpi_csv, name='smme_kpi_export'),
```

**Tasks:**
- [ ] Create export view
- [ ] Add URL route
- [ ] Test CSV download
- [ ] Verify data accuracy

#### Step 3.2: Metadata Display (30 min)
Add to template before table:

```html
<div class="export-bar">
  <div class="export-bar__actions">
    <a href="{% url 'smme_kpi_export' %}?{{ request.GET.urlencode }}" 
       class="btn btn--outline">
      📊 Export CSV
    </a>
  </div>
  <div class="export-bar__meta">
    Last updated: {{ last_updated|timesince }} ago<br>
    Data range: {{ selected_period.label }}
  </div>
</div>
```

Backend:
```python
# In smme_kpi_dashboard()
last_updated = Submission.objects.filter(
    period=period
).aggregate(Max('updated_at'))['updated_at__max']

context['last_updated'] = last_updated or timezone.now()
```

**Tasks:**
- [ ] Add export button
- [ ] Calculate last_updated timestamp
- [ ] Display metadata
- [ ] Style export bar

---

### Phase 4: Polish & Optimization (Optional)
**Priority:** LOW  
**Effort:** 2-3 hours

#### Polish Items
- [ ] Loading spinner on filter submit
- [ ] Empty state designs
- [ ] Table sorting (JavaScript)
- [ ] Performance optimization (caching)
- [ ] Accessibility audit
- [ ] Mobile responsiveness fine-tuning

---

## Implementation Timeline

### Day 1 (Today)
- ✅ Create layout wireframes
- ✅ Refine implementation plan
- ⏳ **Next:** Start Phase 1 - CSS cleanup
  - Add dashboard CSS components
  - Clean up template
  - Test functionality

### Day 2
- Complete Phase 1 testing
- Start Phase 2 - Quarter navigation
  - Backend logic
  - Frontend UI
  - Integration testing

### Day 3
- Complete Phase 2 - Enhanced metrics
- Start Phase 3 - Export functionality
  - CSV export view
  - Metadata display

### Day 4
- Complete Phase 3
- Phase 4 polish (if time permits)
- Final testing & bug fixes

---

## Success Criteria

### Phase 1 ✅
- [ ] Zero inline styles in template
- [ ] All styles use design system
- [ ] Page loads <500ms
- [ ] All filters work identically

### Phase 2 ✅
- [ ] Quarter navigation visible and functional
- [ ] Can filter by quarter
- [ ] Active quarter highlighted
- [ ] Metrics show trends

### Phase 3 ✅
- [ ] CSV export downloads correctly
- [ ] Export includes all current filters
- [ ] Metadata displays accurately

---

## Questions Answered

1. **Quarter Navigation:** ✅ YES - Match school dashboard design
2. **Data Frequency:** Check with team (assume hourly updates)
3. **Export Format:** CSV first, PDF later if needed
4. **Performance:** Check typical district count (estimate: 10-20)
5. **Permissions:** Yes, filtered by section codes (already implemented)
6. **Mobile Priority:** Desktop-first, but responsive

---

## Files to Modify

### Phase 1
- ✅ `docs/SMME_DASHBOARD_LAYOUT.md` - Created
- ✅ `docs/SMME_DASHBOARD_IMPROVEMENTS_PLAN.md` - Refined
- ⏳ `static/css/form-system.css` - Add dashboard components
- ⏳ `templates/dashboards/smme_kpi.html` - Clean up template

### Phase 2
- ⏳ `dashboards/views.py` - Add quarter stats
- ⏳ `templates/dashboards/smme_kpi.html` - Add quarter navigation

### Phase 3
- ⏳ `dashboards/views.py` - Add export view
- ⏳ `dashboards/urls.py` - Add export URL
- ⏳ `templates/dashboards/smme_kpi.html` - Add export button

---

**Current Status:** 📋 PLANNING COMPLETE - Ready to start Phase 1 implementation

**Next Action:** Add dashboard CSS components to `form-system.css` and start template cleanup
