# SMME Dashboard & Manage Forms Refinement Plan

**Date**: October 17, 2025  
**Status**: Planning Phase  
**Priority**: HIGH

---

## 🎯 ISSUES IDENTIFIED

### **Issue 1: Navigation Bar Missing** ❌
- Dashboard has no navigation bar (navbar)
- "Back to Dashboard" button floats without proper header structure
- Need to integrate with existing site navigation

### **Issue 2: Emoji in Title** ❌
- "📊 SMME KPI Dashboard" has emoji
- Should be removed for professional appearance

### **Issue 3: KPI Metrics Wrong** ❌
**Current Implementation**:
- Shows generic submission counts (Submitted/Pending/Not Started)
- No actual KPI calculations from SMME Form 1

**Required Implementation**:
- Show **DNME (Do Not Meet Expectations)** percentage
- Show all KPIs from **SMME Form 1** fields:
  - DNME percentage
  - School Planning indicators
  - Resource Management metrics
  - Monitoring & Evaluation scores
  - etc.

### **Issue 4: Manage Forms Needs Refinement** ❌
- No clear plan for what improvements needed
- Need to identify pain points

---

## 📋 REFINEMENT PLAN

---

## **PART 1: FIX SMME KPI DASHBOARD**

### **Phase 1.1: Add Navigation Bar** (30 min)

**Goal**: Integrate dashboard with existing site navigation

**Tasks**:
1. Check existing navbar template location
2. Update `smme_kpi_dashboard.html` to include navbar
3. Remove floating "Back to Dashboard" button
4. Add dashboard to main navigation menu

**Files to Modify**:
- `templates/dashboards/smme_kpi_dashboard.html`
- Check: `templates/layout/base.html` for navbar structure
- Possibly: `templates/includes/nav.html` or similar

**Expected Result**:
```
┌──────────────────────────────────────────────────────────┐
│ SGOD MIS    Home | Dashboard | Directory | Reports      │ [User Menu]
└──────────────────────────────────────────────────────────┘
  
  SMME KPI Dashboard
  School Management, Monitoring and Evaluation
```

---

### **Phase 1.2: Remove Emoji from Title** (5 min)

**Change**:
```html
<!-- BEFORE -->
<h1>📊 SMME KPI Dashboard</h1>

<!-- AFTER -->
<h1>SMME KPI Dashboard</h1>
```

**Files to Modify**:
- `templates/dashboards/smme_kpi_dashboard.html` (line ~16)

---

### **Phase 1.3: Implement Real SMME Form 1 KPIs** (3-4 hours)

**Goal**: Show actual KPI metrics from SMME Form 1 data, not just submission counts

#### **Step 1: Understand SMME Form 1 Structure**

Need to identify what fields exist in SMME Form 1. Typically includes:
- **DNME (Do Not Meet Expectations)**: Key metric
- School Planning Score
- Resource Management Score
- Monitoring & Evaluation Score
- Compliance Rate
- Other indicators

**Action**: Review `submissions/models.py` or form schema to find SMME Form 1 fields

#### **Step 2: Define KPI Calculations**

**Example KPIs** (based on typical SMME Form 1):

1. **DNME Percentage** (Priority #1)
   ```python
   # Schools rated "Do Not Meet Expectations"
   dnme_count = submissions with DNME rating
   dnme_percentage = (dnme_count / total_schools) * 100
   ```

2. **School Planning Compliance**
   ```python
   # Schools that submitted valid School Improvement Plans
   planning_compliant = count schools with SIP submitted
   planning_rate = (planning_compliant / total_schools) * 100
   ```

3. **Resource Management Score**
   ```python
   # Average score across all schools
   avg_resource_score = average of resource_management_field
   ```

4. **Monitoring & Evaluation Score**
   ```python
   # Average M&E score
   avg_me_score = average of monitoring_evaluation_field
   ```

5. **Overall Compliance Rate**
   ```python
   # Schools meeting all requirements
   compliant_schools = schools with all indicators met
   compliance_rate = (compliant_schools / total_schools) * 100
   ```

#### **Step 3: Update Dashboard View Logic**

**File**: `dashboards/views.py` - `smme_kpi_dashboard` function

**Changes Needed**:
```python
# FOR EACH QUARTER (Q1-Q4):
for period in periods:
    # Get all SMME Form 1 submissions for this period
    submissions = Submission.objects.filter(
        period=period,
        form_template__code__icontains='smme-form-1',  # Adjust code as needed
        status__in=['submitted', 'noted', 'approved']
    )
    
    # Extract data from submission JSON
    dnme_count = 0
    total_with_data = 0
    
    for sub in submissions:
        data = sub.data  # Assuming JSON field
        
        # Check DNME rating field (adjust field name)
        if data.get('overall_rating') == 'DNME':
            dnme_count += 1
        total_with_data += 1
    
    # Calculate DNME percentage
    dnme_percentage = (dnme_count / total_with_data * 100) if total_with_data else 0
    
    # Calculate other KPIs...
    planning_score = calculate_planning_kpi(submissions)
    resource_score = calculate_resource_kpi(submissions)
    me_score = calculate_me_kpi(submissions)
    
    kpi_data.append({
        'period': period,
        'label': period.quarter_tag or period.label,
        'dnme_percentage': dnme_percentage,
        'planning_score': planning_score,
        'resource_score': resource_score,
        'me_score': me_score,
        'total_submissions': total_with_data
    })
```

#### **Step 4: Update Dashboard Template**

**File**: `templates/dashboards/smme_kpi_dashboard.html`

**New Summary Cards**:
```html
<!-- Replace generic cards with KPI-specific cards -->
<div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem;">
    <div class="card">
        <h6>Total Schools</h6>
        <h3>{{ summary.total_schools }}</h3>
    </div>
    
    <div class="card">
        <h6>DNME Percentage</h6>
        <h3 style="color: #ef4444;">{{ summary.avg_dnme }}%</h3>
        <small>Do Not Meet Expectations</small>
    </div>
    
    <div class="card">
        <h6>Planning Score</h6>
        <h3 style="color: #3b82f6;">{{ summary.avg_planning }}/100</h3>
    </div>
    
    <div class="card">
        <h6>Resource Mgmt</h6>
        <h3 style="color: #10b981;">{{ summary.avg_resource }}/100</h3>
    </div>
    
    <div class="card">
        <h6>M&E Score</h6>
        <h3 style="color: #f59e0b;">{{ summary.avg_me }}/100</h3>
    </div>
</div>
```

**New Chart Options**:
```html
<select name="kpi_metric" class="form-input">
    <option value="dnme">DNME Percentage</option>
    <option value="planning">School Planning Score</option>
    <option value="resource">Resource Management Score</option>
    <option value="me">M&E Score</option>
    <option value="compliance">Overall Compliance Rate</option>
</select>
```

**Updated Bar Chart**:
```
DNME Percentage by Quarter - SY 2025-2026

25% ┤                    ██
20% ┤           ██       ██
15% ┤     ██    ██       ██
10% ┤ ██  ██    ██       ██
 5% ┤ ██  ██    ██       ██
    └─────────────────────────
     Q1  Q2    Q3       Q4

Lower is better for DNME!
```

#### **Step 5: Add KPI Toggle**

Allow users to switch between different KPI metrics in the chart:
- DNME Percentage (bar chart - lower is better)
- Planning Score (bar chart - higher is better)
- Resource Management (bar chart - higher is better)
- M&E Score (bar chart - higher is better)
- Multi-KPI Comparison (grouped bar chart - all KPIs side by side)

---

## **PART 2: REFINE MANAGE FORMS**

### **Phase 2.1: Identify Pain Points** (Assessment)

**Need to determine**:
1. Which "Manage Forms" page? 
   - Section admin manage forms (`/submissions/manage-section-forms/`)?
   - SGOD admin manage all forms?
   - School head form list?

2. Current issues to fix:
   - [ ] No period filtering (already noted in Phase 4 of original plan)
   - [ ] No status filtering
   - [ ] No bulk actions
   - [ ] Unclear form status
   - [ ] No search functionality
   - [ ] No export options
   - [ ] Pagination issues
   - [ ] Missing deadline indicators

**Action Required**: User needs to specify which manage forms page and what specific issues they're experiencing.

### **Phase 2.2: Proposed Improvements for Section Admin Manage Forms**

**Current State** (based on code review):
- Basic form template management
- Can update schedules
- Can open/close forms
- No advanced filtering

**Proposed Enhancements**:

#### **Enhancement 1: Add Period Filtering**
```html
<select name="period" onchange="this.form.submit()">
    <option value="">All Periods</option>
    {% for period in periods %}
    <option value="{{ period.id }}">{{ period }}</option>
    {% endfor %}
</select>
```

#### **Enhancement 2: Add Status Indicators**
```html
<td>
    {% if form.is_open_today %}
        <span class="badge badge--success">Open</span>
    {% else %}
        <span class="badge badge--danger">Closed</span>
    {% endif %}
    
    <!-- Days until deadline -->
    {% if form.close_at %}
        <small>{{ form.close_at|timeuntil }} remaining</small>
    {% endif %}
</td>
```

#### **Enhancement 3: Add Submission Statistics**
```html
<td>
    <strong>{{ form.submission_count }}</strong> submissions
    <div class="progress-bar">
        <div style="width: {{ form.completion_rate }}%"></div>
    </div>
    {{ form.completion_rate }}% complete
</td>
```

#### **Enhancement 4: Add Bulk Actions**
```html
<form method="post">
    <select name="bulk_action">
        <option value="">Bulk Actions...</option>
        <option value="extend_deadline">Extend Deadline</option>
        <option value="close_all">Close All Selected</option>
        <option value="activate">Activate</option>
        <option value="deactivate">Deactivate</option>
    </select>
    
    <table>
        <tr>
            <td><input type="checkbox" name="form_ids" value="{{ form.id }}"></td>
            <td>{{ form.title }}</td>
            ...
        </tr>
    </table>
    
    <button>Apply</button>
</form>
```

#### **Enhancement 5: Add Export Functionality**
```html
<a href="{% url 'export_forms_csv' %}?section={{ section.code }}" class="btn">
    Export to CSV
</a>
```

---

## 📊 DETAILED IMPLEMENTATION PLAN

---

### **TASK 1: Research SMME Form 1 Structure** (30 min)

**Objective**: Understand what data SMME Form 1 collects

**Steps**:
1. Check `submissions/models.py` for SMME-related models
2. Check `fixtures/formtemplates.json` for SMME Form 1 schema
3. Query database for existing SMME Form 1 submissions
4. Document field names and data structure

**Command to run**:
```bash
python manage.py shell -c "from submissions.models import FormTemplate; smme_forms = FormTemplate.objects.filter(section__code__iexact='smme'); print('SMME Forms:'); [print(f'  {f.code}: {f.title}') for f in smme_forms]"

python manage.py shell -c "from submissions.models import FormTemplate; form = FormTemplate.objects.filter(code__icontains='smme').first(); print('Schema:', form.schema_descriptor if form else 'No form found')"
```

**Expected Output**:
- List of SMME form template codes
- JSON schema showing field names
- Identification of DNME field and other KPIs

---

### **TASK 2: Fix Navigation & UI** (1 hour)

**Subtask 2.1: Check existing navbar** (15 min)
```bash
# Find navbar template
grep -r "navbar\|nav-menu\|header" templates/layout/
```

**Subtask 2.2: Integrate navbar** (30 min)
- Copy navbar structure from `layout/base.html`
- Add to SMME KPI dashboard template
- Ensure proper styling

**Subtask 2.3: Remove emoji & polish UI** (15 min)
- Remove "📊" from title
- Adjust header spacing
- Ensure consistent styling with rest of site

---

### **TASK 3: Implement Real KPI Calculations** (3 hours)

**Subtask 3.1: Create KPI calculation functions** (1 hour)
```python
# In dashboards/views.py or new dashboards/kpi_calculators.py

def calculate_dnme_percentage(submissions):
    """Calculate percentage of schools with DNME rating"""
    dnme_count = 0
    total = len(submissions)
    
    for sub in submissions:
        data = sub.data
        # Adjust field name based on actual schema
        if data.get('overall_rating') == 'DNME':
            dnme_count += 1
    
    return round((dnme_count / total * 100), 1) if total else 0

def calculate_planning_score(submissions):
    """Calculate average school planning score"""
    scores = []
    for sub in submissions:
        data = sub.data
        score = data.get('planning_score', 0)
        scores.append(score)
    
    return round(sum(scores) / len(scores), 1) if scores else 0

# Similar functions for other KPIs...
```

**Subtask 3.2: Update view to use real KPIs** (1 hour)
- Modify `smme_kpi_dashboard` function
- Query SMME Form 1 submissions
- Calculate KPIs per quarter
- Pass to template

**Subtask 3.3: Update template with new KPIs** (1 hour)
- Replace summary cards
- Add KPI metric selector
- Update chart to show selected KPI
- Add proper labels and colors

---

### **TASK 4: Refine Manage Forms** (2 hours)

**Subtask 4.1: Add filters** (45 min)
- Period filter dropdown
- Status filter (Open/Closed/All)
- Search box for form names

**Subtask 4.2: Add statistics columns** (45 min)
- Submission count
- Completion rate
- Progress bar
- Days remaining

**Subtask 4.3: Add bulk actions** (30 min)
- Checkboxes for selection
- Bulk action dropdown
- Implementation for extend deadline, close, activate

---

## 📝 SUMMARY OF CHANGES

### **Files to Modify**:

1. **dashboards/views.py**
   - Add KPI calculation functions
   - Update `smme_kpi_dashboard` to calculate real KPIs
   - Add KPI metric selection logic

2. **templates/dashboards/smme_kpi_dashboard.html**
   - Add/integrate navbar
   - Remove emoji from title
   - Update summary cards with real KPIs
   - Add KPI metric selector
   - Update chart labels and data

3. **submissions/views.py** (if managing forms)
   - Add period filtering
   - Add status filtering
   - Add statistics calculation
   - Add bulk action handlers

4. **templates/submissions/manage_section_forms.html** (if exists)
   - Add filters UI
   - Add statistics columns
   - Add bulk action UI

---

## 🎯 PRIORITY ORDER

### **IMMEDIATE (Do First)**:
1. ✅ Remove emoji from SMME KPI title (5 min)
2. ✅ Add navbar to SMME KPI dashboard (30 min)
3. ✅ Research SMME Form 1 structure (30 min)

### **HIGH PRIORITY (Do Next)**:
4. ✅ Implement DNME percentage calculation (1 hour)
5. ✅ Update dashboard to show DNME in bar chart (1 hour)
6. ✅ Add other KPI calculations (1 hour)

### **MEDIUM PRIORITY (Do After)**:
7. ✅ Add KPI metric selector to dashboard (30 min)
8. ✅ Refine manage forms with filters (1 hour)
9. ✅ Add bulk actions to manage forms (30 min)

---

## ❓ QUESTIONS TO CLARIFY

**Before starting implementation, need to know**:

1. **SMME Form 1 Structure**:
   - What is the exact field name for DNME rating?
   - What other KPI fields exist in SMME Form 1?
   - Are KPIs stored in JSON `data` field or separate model?

2. **Manage Forms Scope**:
   - Which manage forms page needs refinement?
   - What specific issues are you experiencing?
   - What features are most important?

3. **KPI Definitions**:
   - Is DNME a binary field (Yes/No) or rating scale (1-5)?
   - What constitutes "meeting expectations" vs "not meeting"?
   - Are there other specific KPIs beyond DNME that must be shown?

---

## 🚀 NEXT STEPS

**Option A: Start with quick fixes**
1. Remove emoji (5 min)
2. Add navbar (30 min)
3. Then research SMME Form 1 structure

**Option B: Research first, then implement**
1. Query database for SMME Form 1 schema
2. Document all KPI fields
3. Create comprehensive plan
4. Implement all at once

**Recommendation**: Option A (quick wins first)

---

**Ready to proceed? Please confirm**:
1. Should I start with removing emoji + adding navbar?
2. Do you have documentation on SMME Form 1 fields/KPIs?
3. Which manage forms page needs refinement?
