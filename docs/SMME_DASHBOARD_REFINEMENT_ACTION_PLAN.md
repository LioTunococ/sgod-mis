# SMME Dashboard Refinement - Action Plan

**Created:** October 17, 2025  
**Status:** Planning Phase  
**Priority:** High  
**Estimated Time:** 6-8 hours

---

## Overview

This action plan addresses critical UX improvements and bug fixes for the SMME KPI Dashboard and Period Management system based on user feedback.

### Key Issues Identified:

1. ❌ **Period Management Too Complex** - Start/end dates not needed, only school year + quarters
2. ❌ **Unprofessional UI** - Emojis throughout the interface
3. ❌ **Poor Filter UX** - Page reloads on filter change, requires scrolling to see results
4. ❌ **Cluttered Interface** - Comparison feature adds complexity
5. ❌ **Display Bug** - Quarters showing as "Q1-Q1" instead of "Q1", "Q2", "Q3", "Q4"
6. ❌ **Layout Issues** - Dashboard requires scrolling to see graph

---

## Action Items

## Action Items

### 📝 Task 0: Refine SMME Form Management - Add Period Classification

**Goal:** Allow SMME staff to select school year and quarter when managing forms

**Priority:** HIGH  
**Estimated Time:** 1.5 hours  
**Files to Modify:**
- `submissions/models.py` (add fields to FormTemplate or use Period relationship)
- `submissions/forms.py` (add period selector)
- `submissions/admin.py` (update admin interface)
- Templates for form creation/editing

**Problem:**
Currently, when SMME staff manage forms (SMEA Form 1, etc.), there's no clear way to classify which school year and quarter the form data belongs to. This makes filtering in the KPI dashboard difficult.

**Solution:**

#### 0.1 Option A: Add Period Foreign Key to FormTemplate
```python
# submissions/models.py

class FormTemplate(models.Model):
    # ... existing fields ...
    
    # NEW: Link to specific period
    period = models.ForeignKey(
        Period,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="School year and quarter this form is for"
    )
```

#### 0.2 Option B: Use Submission Period (Current Approach)
Keep using `Submission.period` field (already exists). Just ensure it's properly populated when creating submissions.

**Recommendation:** Use Option B (existing Submission.period field). Forms are already linked to periods through submissions.

#### 0.3 Update Form Creation Interface
Ensure period selection is prominent when SMME staff create/review forms:

```html
<!-- In form creation template -->
<div class="form-group">
    <label>Period</label>
    <select name="period" required>
        <option value="">Select Period</option>
        {% for period in periods %}
        <option value="{{ period.id }}">
            {{ period.label }} ({{ period.quarter_tag }})
        </option>
        {% endfor %}
    </select>
</div>
```

**Testing Checklist:**
- [ ] Can select period when creating form
- [ ] Period displays in form list
- [ ] KPI dashboard can filter by selected periods
- [ ] Clear labels (e.g., "Q1 - SY 2025-2026")

---

### 🔢 Task 0B: Fix Incomplete KPI Calculations - Add ALL SMEA Form 1 Indicators

**Goal:** Calculate complete KPIs from SMEA Form 1 including Reading Assessments and Implementation Areas

**Priority:** CRITICAL ⚠️  
**Estimated Time:** 4 hours  
**Current Problem:** The existing `kpi_calculators.py` is calculating INCORRECT KPIs!

**Files to Modify:**
- `dashboards/kpi_calculators.py` (complete rewrite needed)
- `dashboards/views.py` (update to use new KPI structure)

---

## 📋 COMPLETE SMEA FORM 1 KPI STRUCTURE

After scanning the models, here are **ALL indicators** that should be in the dashboard:

### **Section 1: Student Learning Progress (SLP)** - `Form1SLPRow`

**Models Used:** `Form1SLPRow`

**KPI Indicators:**
1. **DNME Percentage** ⭐ PRIMARY KPI
   - Formula: `(sum(dnme) / sum(enrolment)) × 100`
   - Lower is better! Target: < 10%
   
2. **Fairly Satisfactory %**
   - Formula: `(sum(fs) / sum(enrolment)) × 100`
   
3. **Satisfactory %**
   - Formula: `(sum(s) / sum(enrolment)) × 100`
   
4. **Very Satisfactory %**
   - Formula: `(sum(vs) / sum(enrolment)) × 100`
   
5. **Outstanding %**
   - Formula: `(sum(o) / sum(enrolment)) × 100`

**Chart Display:** Stacked bar showing performance distribution per quarter

---

### **Section 2: Implementation Areas** - `Form1PctRow`

**Models Used:** `Form1PctRow` (action areas with percentage implementation)

**KPI Indicators:**
1. **Access Implementation %**
   - Formula: Average of `percent` where `area='access'`
   - Higher is better! Target: > 80%
   
2. **Quality Implementation %**
   - Formula: Average of `percent` where `area='quality'`
   
3. **Equity Implementation %**
   - Formula: Average of `percent` where `area='equity'`
   
4. **Enabling Mechanisms %**
   - Formula: Average of `percent` where `area='enabling_mechanisms'`

**Chart Display:** Grouped bar chart showing 4 areas per quarter

---

### **Section 3: Reading Assessment - CRLA** - `ReadingAssessmentCRLA`

**Models Used:** `ReadingAssessmentCRLA` (Comprehensive Reading and Literacy Assessment)

**Proficiency Levels:** (from `CRLAProficiencyLevel`)
- Independent Level (IL)
- Instructional Level (InL)
- Frustration Level (FL)
- Non-Reader (NR)

**KPI Indicators:**
1. **CRLA Independent Readers %**
   - Formula: (Total learners at Independent Level / Total learners) × 100
   - Target: > 70%
   
2. **CRLA Frustration Level %**
   - Formula: (Total learners at Frustration Level / Total learners) × 100
   - Lower is better! Target: < 15%
   
3. **CRLA Non-Readers %**
   - Formula: (Total learners who are Non-Readers / Total learners) × 100
   - Lower is better! Target: < 5%

**Grade Breakdown:** Mother Tongue (Gr 1-3), Filipino (Gr 2-3), English (Gr 3)

**Chart Display:** Stacked bar showing proficiency distribution per assessment period

---

### **Section 4: Reading Assessment - PHILIRI** - `ReadingAssessmentPHILIRI`

**Models Used:** `ReadingAssessmentPHILIRI` (Philippine Informal Reading Inventory)

**Reading Levels:** (from `PHILIRIReadingLevel`)
- Independent
- Instructional
- Frustration
- Non-Reader

**KPI Indicators:**
1. **PHILIRI Independent Readers %**
   - Formula: (Total at Independent Level / Total learners) × 100
   - Target: > 75%
   
2. **PHILIRI Frustration Level %**
   - Formula: (Total at Frustration Level / Total learners) × 100
   - Lower is better! Target: < 15%

**Grade Breakdown:** English & Filipino (Grades 4/7, 5/8, 6/9, 10)

**Chart Display:** Stacked bar showing reading level distribution per assessment period

---

### **Section 5: Reading-Math Assessment (RMA)** - `Form1RMARow`

**Models Used:** `Form1RMARow`

**Performance Bands:**
- Below 75% (Needs Improvement)
- 75-79% (Fair)
- 80-84% (Satisfactory)
- 85-89% (Very Satisfactory)
- 90-100% (Outstanding)

**KPI Indicators:**
1. **RMA High Performers %** (85-100%)
   - Formula: `((band_85_89 + band_90_100) / enrolment) × 100`
   - Target: > 60%
   
2. **RMA Below Standard %** (Below 75%)
   - Formula: `(band_below_75 / enrolment) × 100`
   - Lower is better! Target: < 10%

**Chart Display:** Stacked bar showing band distribution per quarter

---

## 🎯 DASHBOARD KPI SELECTOR (Dropdown Options)

Based on the complete structure, the KPI metric dropdown should have:

```html
<select id="kpiMetricSelect">
    <optgroup label="Student Learning Progress">
        <option value="dnme" selected>DNME Percentage ⚠️</option>
        <option value="fs">Fairly Satisfactory %</option>
        <option value="satisfactory">Satisfactory %</option>
        <option value="very_satisfactory">Very Satisfactory %</option>
        <option value="outstanding">Outstanding %</option>
    </optgroup>
    
    <optgroup label="Implementation Areas">
        <option value="access">Access Implementation</option>
        <option value="quality">Quality Implementation</option>
        <option value="equity">Equity Implementation</option>
        <option value="enabling">Enabling Mechanisms</option>
    </optgroup>
    
    <optgroup label="Reading Assessments - CRLA">
        <option value="crla_independent">CRLA Independent Readers %</option>
        <option value="crla_frustration">CRLA Frustration Level % ⚠️</option>
        <option value="crla_nonreader">CRLA Non-Readers % ⚠️</option>
    </optgroup>
    
    <optgroup label="Reading Assessments - PHILIRI">
        <option value="philiri_independent">PHILIRI Independent %</option>
        <option value="philiri_frustration">PHILIRI Frustration % ⚠️</option>
    </optgroup>
    
    <optgroup label="Reading-Math Assessment">
        <option value="rma_high">RMA High Performers % (85-100%)</option>
        <option value="rma_low">RMA Below Standard % ⚠️</option>
    </optgroup>
</select>
```

---

## 💻 Updated Implementation - kpi_calculators.py

**Complete Rewrite Needed:**

```python
# dashboards/kpi_calculators.py

from django.db.models import Sum, Count, Q, F, Avg
from submissions.models import (
    Submission,
    Form1SLPRow,
    Form1PctRow,
    ReadingAssessmentCRLA,
    ReadingAssessmentPHILIRI,
    Form1RMARow
)


def calculate_slp_kpis(period, section_code='smme'):
    """
    Calculate Student Learning Progress KPIs from Form1SLPRow.
    
    Returns: {
        'dnme_percentage': float,
        'fs_percentage': float,
        'satisfactory_percentage': float,
        'very_satisfactory_percentage': float,
        'outstanding_percentage': float,
        'total_students': int
    }
    """
    slp_rows = Form1SLPRow.objects.filter(
        submission__period=period,
        submission__form_template__section__code__iexact=section_code,
        submission__status__in=['submitted', 'noted', 'approved'],
        is_offered=True  # Only count offered subjects
    )
    
    if not slp_rows.exists():
        return {
            'dnme_percentage': 0.0,
            'fs_percentage': 0.0,
            'satisfactory_percentage': 0.0,
            'very_satisfactory_percentage': 0.0,
            'outstanding_percentage': 0.0,
            'total_students': 0
        }
    
    # Calculate totals
    total_enrollment = sum(row.enrolment for row in slp_rows)
    total_dnme = sum(row.dnme for row in slp_rows)
    total_fs = sum(row.fs for row in slp_rows)
    total_s = sum(row.s for row in slp_rows)
    total_vs = sum(row.vs for row in slp_rows)
    total_o = sum(row.o for row in slp_rows)
    
    if total_enrollment == 0:
        return {
            'dnme_percentage': 0.0,
            'fs_percentage': 0.0,
            'satisfactory_percentage': 0.0,
            'very_satisfactory_percentage': 0.0,
            'outstanding_percentage': 0.0,
            'total_students': 0
        }
    
    return {
        'dnme_percentage': round((total_dnme / total_enrollment) * 100, 1),
        'fs_percentage': round((total_fs / total_enrollment) * 100, 1),
        'satisfactory_percentage': round((total_s / total_enrollment) * 100, 1),
        'very_satisfactory_percentage': round((total_vs / total_enrollment) * 100, 1),
        'outstanding_percentage': round((total_o / total_enrollment) * 100, 1),
        'total_students': total_enrollment
    }


def calculate_implementation_kpis(period, section_code='smme'):
    """
    Calculate Implementation Area KPIs from Form1PctRow.
    
    Returns: {
        'access_percentage': float,
        'quality_percentage': float,
        'equity_percentage': float,
        'enabling_percentage': float,
        'overall_percentage': float
    }
    """
    from submissions.constants import SMEAActionArea
    
    pct_rows = Form1PctRow.objects.filter(
        submission__period=period,
        submission__form_template__section__code__iexact=section_code,
        submission__status__in=['submitted', 'noted', 'approved']
    )
    
    if not pct_rows.exists():
        return {
            'access_percentage': 0.0,
            'quality_percentage': 0.0,
            'equity_percentage': 0.0,
            'enabling_percentage': 0.0,
            'overall_percentage': 0.0
        }
    
    # Calculate average percentage per area
    access_avg = pct_rows.filter(area=SMEAActionArea.ACCESS).aggregate(avg=Avg('percent'))['avg'] or 0
    quality_avg = pct_rows.filter(area=SMEAActionArea.QUALITY).aggregate(avg=Avg('percent'))['avg'] or 0
    equity_avg = pct_rows.filter(area=SMEAActionArea.EQUITY).aggregate(avg=Avg('percent'))['avg'] or 0
    enabling_avg = pct_rows.filter(area=SMEAActionArea.ENABLING_MECHANISMS).aggregate(avg=Avg('percent'))['avg'] or 0
    
    overall = round((access_avg + quality_avg + equity_avg + enabling_avg) / 4, 1)
    
    return {
        'access_percentage': round(access_avg, 1),
        'quality_percentage': round(quality_avg, 1),
        'equity_percentage': round(equity_avg, 1),
        'enabling_percentage': round(enabling_avg, 1),
        'overall_percentage': overall
    }


def calculate_crla_kpis(period, section_code='smme'):
    """
    Calculate CRLA Reading Assessment KPIs.
    
    Returns: {
        'independent_percentage': float,
        'instructional_percentage': float,
        'frustration_percentage': float,
        'nonreader_percentage': float,
        'total_assessed': int
    }
    """
    from submissions.constants import CRLAProficiencyLevel
    
    crla_data = ReadingAssessmentCRLA.objects.filter(
        submission__period=period,
        submission__form_template__section__code__iexact=section_code,
        submission__status__in=['submitted', 'noted', 'approved']
    )
    
    if not crla_data.exists():
        return {
            'independent_percentage': 0.0,
            'instructional_percentage': 0.0,
            'frustration_percentage': 0.0,
            'nonreader_percentage': 0.0,
            'total_assessed': 0
        }
    
    # Calculate totals per proficiency level
    total_independent = sum(
        row.total_learners() for row in crla_data.filter(level=CRLAProficiencyLevel.INDEPENDENT)
    )
    total_instructional = sum(
        row.total_learners() for row in crla_data.filter(level=CRLAProficiencyLevel.INSTRUCTIONAL)
    )
    total_frustration = sum(
        row.total_learners() for row in crla_data.filter(level=CRLAProficiencyLevel.FRUSTRATION)
    )
    total_nonreader = sum(
        row.total_learners() for row in crla_data.filter(level=CRLAProficiencyLevel.NON_READER)
    )
    
    total_assessed = total_independent + total_instructional + total_frustration + total_nonreader
    
    if total_assessed == 0:
        return {
            'independent_percentage': 0.0,
            'instructional_percentage': 0.0,
            'frustration_percentage': 0.0,
            'nonreader_percentage': 0.0,
            'total_assessed': 0
        }
    
    return {
        'independent_percentage': round((total_independent / total_assessed) * 100, 1),
        'instructional_percentage': round((total_instructional / total_assessed) * 100, 1),
        'frustration_percentage': round((total_frustration / total_assessed) * 100, 1),
        'nonreader_percentage': round((total_nonreader / total_assessed) * 100, 1),
        'total_assessed': total_assessed
    }


def calculate_philiri_kpis(period, section_code='smme'):
    """
    Calculate PHILIRI Reading Assessment KPIs.
    
    Returns: {
        'independent_percentage': float,
        'instructional_percentage': float,
        'frustration_percentage': float,
        'nonreader_percentage': float,
        'total_assessed': int
    }
    """
    from submissions.constants import PHILIRIReadingLevel
    
    philiri_data = ReadingAssessmentPHILIRI.objects.filter(
        submission__period=period,
        submission__form_template__section__code__iexact=section_code,
        submission__status__in=['submitted', 'noted', 'approved']
    )
    
    if not philiri_data.exists():
        return {
            'independent_percentage': 0.0,
            'instructional_percentage': 0.0,
            'frustration_percentage': 0.0,
            'nonreader_percentage': 0.0,
            'total_assessed': 0
        }
    
    # Calculate totals per reading level
    total_independent = sum(
        row.total_learners() for row in philiri_data.filter(level=PHILIRIReadingLevel.INDEPENDENT)
    )
    total_instructional = sum(
        row.total_learners() for row in philiri_data.filter(level=PHILIRIReadingLevel.INSTRUCTIONAL)
    )
    total_frustration = sum(
        row.total_learners() for row in philiri_data.filter(level=PHILIRIReadingLevel.FRUSTRATION)
    )
    total_nonreader = sum(
        row.total_learners() for row in philiri_data.filter(level=PHILIRIReadingLevel.NON_READER)
    )
    
    total_assessed = total_independent + total_instructional + total_frustration + total_nonreader
    
    if total_assessed == 0:
        return {
            'independent_percentage': 0.0,
            'instructional_percentage': 0.0,
            'frustration_percentage': 0.0,
            'nonreader_percentage': 0.0,
            'total_assessed': 0
        }
    
    return {
        'independent_percentage': round((total_independent / total_assessed) * 100, 1),
        'instructional_percentage': round((total_instructional / total_assessed) * 100, 1),
        'frustration_percentage': round((total_frustration / total_assessed) * 100, 1),
        'nonreader_percentage': round((total_nonreader / total_assessed) * 100, 1),
        'total_assessed': total_assessed
    }


def calculate_rma_kpis(period, section_code='smme'):
    """
    Calculate Reading-Math Assessment KPIs.
    
    Returns: {
        'high_performers_percentage': float,  # 85-100%
        'below_standard_percentage': float,    # Below 75%
        'total_assessed': int
    }
    """
    rma_data = Form1RMARow.objects.filter(
        submission__period=period,
        submission__form_template__section__code__iexact=section_code,
        submission__status__in=['submitted', 'noted', 'approved']
    )
    
    if not rma_data.exists():
        return {
            'high_performers_percentage': 0.0,
            'below_standard_percentage': 0.0,
            'total_assessed': 0
        }
    
    total_enrollment = sum(row.enrolment for row in rma_data)
    total_high = sum(row.band_85_89 + row.band_90_100 for row in rma_data)
    total_below = sum(row.band_below_75 for row in rma_data)
    
    if total_enrollment == 0:
        return {
            'high_performers_percentage': 0.0,
            'below_standard_percentage': 0.0,
            'total_assessed': 0
        }
    
    return {
        'high_performers_percentage': round((total_high / total_enrollment) * 100, 1),
        'below_standard_percentage': round((total_below / total_enrollment) * 100, 1),
        'total_assessed': total_enrollment
    }


def calculate_all_kpis_for_period(period, section_code='smme'):
    """
    Calculate ALL KPIs for a single period.
    
    Returns: {
        'period': Period object,
        'slp': {...},
        'implementation': {...},
        'crla': {...},
        'philiri': {...},
        'rma': {...}
    }
    """
    return {
        'period': period,
        'period_label': period.quarter_tag or period.label,
        'slp': calculate_slp_kpis(period, section_code),
        'implementation': calculate_implementation_kpis(period, section_code),
        'crla': calculate_crla_kpis(period, section_code),
        'philiri': calculate_philiri_kpis(period, section_code),
        'rma': calculate_rma_kpis(period, section_code)
    }
```

**Testing Checklist:**
- [ ] SLP KPIs calculate correctly (DNME, FS, S, VS, O)
- [ ] Implementation KPIs calculate correctly (Access, Quality, Equity, Enabling)
- [ ] CRLA KPIs calculate correctly (Independent, Frustration, Non-Reader)
- [ ] PHILIRI KPIs calculate correctly
- [ ] RMA KPIs calculate correctly
- [ ] All percentages add up correctly
- [ ] Returns 0% when no data exists

---

### 📋 Task 1: Refine Period Management - Remove Date Fields

**Goal:** Simplify period creation to only allow school years with quarters (Q1-Q4)

**Priority:** HIGH  
**Estimated Time:** 2 hours  
**Files to Modify:**
- `submissions/models.py` (Period model)
- `submissions/admin.py` (Period admin interface)
- `submissions/forms.py` (if exists)
- Create migration file

**Changes Required:**

#### 1.1 Update Period Model
```python
# submissions/models.py

class Period(models.Model):
    """
    Simplified Period model - Only school year and quarter tag
    """
    label = models.CharField(
        max_length=100,
        help_text="Auto-generated: e.g., 'Q1 - SY 2025-2026'"
    )
    school_year_start = models.PositiveIntegerField(
        help_text="e.g., 2025 for SY 2025-2026"
    )
    quarter_tag = models.CharField(
        max_length=2,
        choices=[('Q1', 'Q1'), ('Q2', 'Q2'), ('Q3', 'Q3'), ('Q4', 'Q4')],
        help_text="Quarter: Q1, Q2, Q3, or Q4"
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order for sorting (auto-calculated)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this period is active"
    )
    
    # REMOVE these fields:
    # - open_date
    # - close_date
    # - starts_on
    # - ends_on
    # - quarter (old field)
    
    class Meta:
        ordering = ["school_year_start", "display_order"]
        unique_together = ('school_year_start', 'quarter_tag')
    
    def save(self, *args, **kwargs):
        # Auto-generate label
        self.label = f"{self.quarter_tag} - SY {self.school_year_start}-{self.school_year_start + 1}"
        
        # Auto-calculate display_order
        order_map = {'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4}
        self.display_order = order_map.get(self.quarter_tag, 0)
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.label
```

#### 1.2 Create Migration
```bash
python manage.py makemigrations submissions --name simplify_period_model
```

Migration should:
- Make `open_date`, `close_date`, `starts_on`, `ends_on` nullable (if removing)
- Add data migration to populate `quarter_tag` from old `quarter` field
- Add unique_together constraint

#### 1.3 Update Admin Interface
```python
# submissions/admin.py

@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ['label', 'school_year_start', 'quarter_tag', 'is_active']
    list_filter = ['school_year_start', 'quarter_tag', 'is_active']
    search_fields = ['label']
    ordering = ['-school_year_start', 'display_order']
    
    # Only allow editing these fields
    fields = ['school_year_start', 'quarter_tag', 'is_active']
    
    # Auto-populate label and display_order on save
    readonly_fields = ['label', 'display_order']
```

**Testing Checklist:**
- [ ] Can create period with only school_year and quarter
- [ ] Label auto-generates correctly (e.g., "Q1 - SY 2025-2026")
- [ ] Display_order auto-calculates (Q1=1, Q2=2, Q3=3, Q4=4)
- [ ] Unique constraint prevents duplicate school_year + quarter
- [ ] Existing periods migrate correctly

---

### 🎨 Task 2: Remove All Emojis from UI

**Goal:** Professional, clean interface without emojis

**Priority:** HIGH  
**Estimated Time:** 30 minutes  
**Files to Modify:**
- `templates/dashboards/smme_kpi_dashboard.html`
- `templates/organizations/school_list.html` (if has emojis)
- `templates/accounts/user_list.html` (if has emojis)
- Any period management templates

**Changes Required:**

#### 2.1 SMME KPI Dashboard
```html
<!-- BEFORE -->
<h1>📊 SMME KPI Dashboard</h1>
<button>📊 Compare Schools</button>

<!-- AFTER -->
<h1>SMME KPI Dashboard</h1>
<button>Compare Schools</button>  <!-- Will be removed in Task 5 -->
```

#### 2.2 Summary Cards
```html
<!-- BEFORE -->
<div class="card">
    <h3>🏫 Total Schools</h3>
    <p class="metric">{{ total_schools }}</p>
</div>

<!-- AFTER -->
<div class="card">
    <h3>Total Schools</h3>
    <p class="metric">{{ total_schools }}</p>
</div>
```

#### 2.3 Search for All Emojis
Run this command to find all emoji usage:
```bash
grep -r "📊\|🏫\|📈\|📉\|✅\|❌\|🔍\|⚠️\|📝\|👤\|🎯" templates/
```

**Search Patterns:**
- Chart emojis: 📊 📈 📉
- School emojis: 🏫
- Status emojis: ✅ ❌ ⚠️
- Action emojis: 🔍 📝 🎯
- User emojis: 👤

**Testing Checklist:**
- [ ] No emojis in SMME KPI Dashboard
- [ ] No emojis in Period management pages
- [ ] No emojis in School directory
- [ ] No emojis in User directory
- [ ] Interface looks professional

---

### ⚡ Task 3: Implement Smooth AJAX Filter Transitions

**Goal:** Filters update dashboard without page reload, with smooth animations

**Priority:** HIGH  
**Estimated Time:** 2 hours  
**Files to Modify:**
- `templates/dashboards/smme_kpi_dashboard.html` (JavaScript section)
- `dashboards/views.py` (add JSON API endpoint)
- `dashboards/urls.py` (add API route)

**Changes Required:**

#### 3.1 Create AJAX API Endpoint
```python
# dashboards/views.py

@login_required
def smme_kpi_data_api(request):
    """
    API endpoint to return KPI data as JSON (for AJAX updates)
    """
    user = request.user
    _require_reviewer_access(user)
    
    school_year = request.GET.get('school_year')
    quarter_filter = request.GET.get('quarter', 'all')
    kpi_metric = request.GET.get('kpi_metric', 'dnme')
    
    if not school_year:
        return JsonResponse({'error': 'Missing school_year'}, status=400)
    
    # Calculate KPIs
    from dashboards.kpi_calculators import calculate_all_kpis_for_period
    
    if quarter_filter == 'all':
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
        ).order_by('display_order')
    else:
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__iexact=quarter_filter
        )
    
    # Calculate data for chart
    chart_labels = []
    chart_values = []
    summary_data = {
        'total_schools': 0,
        'dnme': 0,
        'access': 0,
        'quality': 0,
        'governance': 0,
        'management': 0
    }
    
    for period in periods:
        period_kpis = calculate_all_kpis_for_period(period, 'smme')
        
        chart_labels.append(period.quarter_tag)
        
        # Extract metric value
        if kpi_metric == 'dnme':
            value = period_kpis['dnme']['dnme_percentage']
            summary_data['dnme'] += value
        elif kpi_metric == 'access':
            value = period_kpis['implementation_areas']['access_percentage']
            summary_data['access'] += value
        # ... other metrics
        
        chart_values.append(value)
        summary_data['total_schools'] = period_kpis['dnme']['total_schools']
    
    # Calculate averages
    num_periods = len(periods)
    if num_periods > 0:
        for key in ['dnme', 'access', 'quality', 'governance', 'management']:
            summary_data[key] = round(summary_data[key] / num_periods, 1)
    
    return JsonResponse({
        'chart_labels': chart_labels,
        'chart_values': chart_values,
        'summary': summary_data
    })
```

#### 3.2 Update URL Configuration
```python
# dashboards/urls.py

urlpatterns = [
    # ... existing patterns
    path("dashboards/smme-kpi/data/", views.smme_kpi_data_api, name="smme_kpi_data_api"),
]
```

#### 3.3 Add AJAX JavaScript
```javascript
// templates/dashboards/smme_kpi_dashboard.html

// Global variables
let myChart = null;
let isUpdating = false;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeChart();
    attachFilterListeners();
});

function attachFilterListeners() {
    // School Year dropdown
    document.getElementById('schoolYearSelect').addEventListener('change', function() {
        updateDashboard();
    });
    
    // Quarter dropdown
    document.getElementById('quarterSelect').addEventListener('change', function() {
        updateDashboard();
    });
    
    // KPI Metric dropdown
    document.getElementById('kpiMetricSelect').addEventListener('change', function() {
        updateDashboard();
    });
}

function updateDashboard() {
    if (isUpdating) return; // Prevent multiple simultaneous updates
    
    isUpdating = true;
    
    // Get filter values
    const schoolYear = document.getElementById('schoolYearSelect').value;
    const quarter = document.getElementById('quarterSelect').value;
    const kpiMetric = document.getElementById('kpiMetricSelect').value;
    
    // Show loading state
    showLoadingState();
    
    // Fetch new data
    fetch(`/dashboards/smme-kpi/data/?school_year=${schoolYear}&quarter=${quarter}&kpi_metric=${kpiMetric}`)
        .then(response => response.json())
        .then(data => {
            // Update summary cards with animation
            updateSummaryCards(data.summary);
            
            // Update chart with smooth transition
            updateChart(data.chart_labels, data.chart_values, kpiMetric);
            
            hideLoadingState();
            isUpdating = false;
        })
        .catch(error => {
            console.error('Error fetching data:', error);
            alert('Failed to update dashboard. Please try again.');
            hideLoadingState();
            isUpdating = false;
        });
}

function updateSummaryCards(summary) {
    // Animate number changes
    animateValue('totalSchools', summary.total_schools, 500);
    animateValue('dnmeMetric', summary.dnme, 500, '%');
    animateValue('accessMetric', summary.access, 500, '%');
    animateValue('qualityMetric', summary.quality, 500, '%');
    animateValue('governanceMetric', summary.governance, 500, '%');
    animateValue('managementMetric', summary.management, 500, '%');
}

function animateValue(elementId, endValue, duration, suffix = '') {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const startValue = parseFloat(element.textContent.replace('%', '')) || 0;
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function (ease-out)
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const currentValue = startValue + (endValue - startValue) * easeOut;
        
        element.textContent = currentValue.toFixed(1) + suffix;
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

function updateChart(labels, values, metricName) {
    // Smooth transition for chart update
    if (myChart) {
        myChart.data.labels = labels;
        myChart.data.datasets[0].data = values;
        myChart.data.datasets[0].label = getMetricDisplayName(metricName);
        
        // Animate chart update
        myChart.update('active'); // 'active' mode for smooth animation
    }
}

function showLoadingState() {
    // Add loading overlay or spinner
    document.getElementById('dashboardContent').style.opacity = '0.5';
    document.getElementById('dashboardContent').style.pointerEvents = 'none';
}

function hideLoadingState() {
    document.getElementById('dashboardContent').style.opacity = '1';
    document.getElementById('dashboardContent').style.pointerEvents = 'auto';
}

function getMetricDisplayName(metric) {
    const names = {
        'dnme': 'DNME Percentage',
        'access': 'Access Percentage',
        'quality': 'Quality Percentage',
        'governance': 'Governance Percentage',
        'management': 'Management Percentage',
        'leadership': 'Leadership Percentage'
    };
    return names[metric] || metric;
}
```

#### 3.4 Add CSS Transitions
```css
/* Smooth transitions */
.card {
    transition: all 0.3s ease;
}

.metric {
    transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
    font-size: 2rem;
    font-weight: bold;
}

#dashboardContent {
    transition: opacity 0.3s ease;
}

/* Loading state */
.loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(255, 255, 255, 0.8);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 9999;
}

.loading-overlay.active {
    display: flex;
}
```

**Testing Checklist:**
- [ ] School year change updates dashboard without page reload
- [ ] Quarter filter updates smoothly
- [ ] Numbers animate when changing
- [ ] Chart transitions smoothly
- [ ] Loading state shows during update
- [ ] No flash of unstyled content

---

### 📐 Task 4: Optimize Dashboard Layout - Fit Screen

**Goal:** All filters, summary cards, and chart visible without scrolling

**Priority:** HIGH  
**Estimated Time:** 1.5 hours  
**Files to Modify:**
- `templates/dashboards/smme_kpi_dashboard.html`
- `static/css/dashboard.css` (or inline styles)

**Changes Required:**

#### 4.1 New Layout Structure
```html
<!-- templates/dashboards/smme_kpi_dashboard.html -->

<div class="smme-dashboard-container">
    <!-- Header Section (Fixed Height: ~80px) -->
    <header class="dashboard-header">
        <h1>SMME KPI Dashboard</h1>
    </header>
    
    <!-- Filter Bar (Fixed Height: ~60px) -->
    <section class="filter-bar">
        <div class="filter-group">
            <label>School Year</label>
            <select id="schoolYearSelect">
                <option value="2025">SY 2025-2026</option>
                <option value="2024">SY 2024-2025</option>
            </select>
        </div>
        
        <div class="filter-group">
            <label>Quarter</label>
            <select id="quarterSelect">
                <option value="all">All Quarters</option>
                <option value="Q1">Q1</option>
                <option value="Q2">Q2</option>
                <option value="Q3">Q3</option>
                <option value="Q4">Q4</option>
            </select>
        </div>
        
        <div class="filter-group">
            <label>KPI Metric</label>
            <select id="kpiMetricSelect">
                <option value="dnme">DNME %</option>
                <option value="access">Access</option>
                <option value="quality">Quality</option>
                <option value="governance">Governance</option>
                <option value="management">Management</option>
            </select>
        </div>
    </section>
    
    <!-- Summary Cards Row (Fixed Height: ~120px) -->
    <section class="summary-cards">
        <div class="summary-card">
            <h3>Total Schools</h3>
            <p class="metric" id="totalSchools">{{ total_schools }}</p>
        </div>
        <div class="summary-card">
            <h3>DNME %</h3>
            <p class="metric" id="dnmeMetric">{{ dnme_percentage }}%</p>
            <span class="hint">Lower is Better</span>
        </div>
        <div class="summary-card">
            <h3>Access</h3>
            <p class="metric" id="accessMetric">{{ access_percentage }}%</p>
        </div>
        <div class="summary-card">
            <h3>Quality</h3>
            <p class="metric" id="qualityMetric">{{ quality_percentage }}%</p>
        </div>
        <div class="summary-card">
            <h3>Governance</h3>
            <p class="metric" id="governanceMetric">{{ governance_percentage }}%</p>
        </div>
        <div class="summary-card">
            <h3>Management</h3>
            <p class="metric" id="managementMetric">{{ management_percentage }}%</p>
        </div>
    </section>
    
    <!-- Chart Section (Flexible Height: Fills Remaining Space) -->
    <section class="chart-section">
        <div class="chart-container">
            <canvas id="kpiChart"></canvas>
        </div>
    </section>
</div>
```

#### 4.2 CSS Layout (Fit to Screen)
```css
/* Container uses full viewport height */
.smme-dashboard-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    padding: 1rem;
    box-sizing: border-box;
    overflow: hidden; /* Prevent scrolling */
}

/* Header - Fixed Height */
.dashboard-header {
    height: 80px;
    display: flex;
    align-items: center;
    border-bottom: 2px solid #e5e7eb;
    margin-bottom: 1rem;
}

.dashboard-header h1 {
    font-size: 1.75rem;
    font-weight: 700;
    margin: 0;
}

/* Filter Bar - Fixed Height */
.filter-bar {
    display: flex;
    gap: 1rem;
    height: 60px;
    align-items: center;
    background: #f9fafb;
    padding: 0 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
}

.filter-group {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.filter-group label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #6b7280;
}

.filter-group select {
    padding: 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    font-size: 0.875rem;
    min-width: 150px;
}

/* Summary Cards - Fixed Height */
.summary-cards {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 1rem;
    height: 120px;
    margin-bottom: 1rem;
}

.summary-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}

.summary-card h3 {
    font-size: 0.875rem;
    font-weight: 600;
    margin: 0 0 0.5rem 0;
    color: #6b7280;
}

.summary-card .metric {
    font-size: 1.5rem;
    font-weight: 700;
    margin: 0;
    color: #111827;
}

.summary-card .hint {
    font-size: 0.75rem;
    color: #9ca3af;
    margin-top: 0.25rem;
}

/* Chart Section - Flexible Height (Fills Remaining Space) */
.chart-section {
    flex: 1; /* Takes remaining vertical space */
    min-height: 0; /* Important for flexbox sizing */
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 1rem;
}

.chart-container {
    width: 100%;
    height: 100%;
    position: relative;
}

#kpiChart {
    max-height: 100% !important;
}

/* Responsive adjustments for smaller screens */
@media (max-width: 1400px) {
    .summary-cards {
        grid-template-columns: repeat(3, 1fr);
        height: 240px; /* 2 rows */
    }
}

@media (max-width: 768px) {
    .filter-bar {
        flex-direction: column;
        height: auto;
        padding: 1rem;
    }
    
    .summary-cards {
        grid-template-columns: repeat(2, 1fr);
        height: 360px; /* 3 rows */
    }
}
```

**Testing Checklist:**
- [ ] Dashboard fits on 1920×1080 screen without scrolling
- [ ] Dashboard fits on 1366×768 screen without scrolling
- [ ] All elements visible on page load
- [ ] Chart uses remaining vertical space efficiently
- [ ] Responsive on smaller screens

---

### 🗑️ Task 5: Remove Compare Schools Feature

**Goal:** Simplify dashboard by removing comparison functionality

**Priority:** MEDIUM  
**Estimated Time:** 30 minutes  
**Files to Modify:**
- `templates/dashboards/smme_kpi_dashboard.html`
- `dashboards/views.py` (remove comparison view)
- `dashboards/urls.py` (remove comparison URL)

**Changes Required:**

#### 5.1 Remove from Template
Delete these sections:
- Comparison toggle button
- School selection panel (`#comparisonPanel`)
- All comparison-related JavaScript (renderComparisonChart, resetToNormalView, etc.)
- School checkbox labels and styles

```html
<!-- DELETE THESE SECTIONS -->

<!-- Comparison Toggle Button -->
<button id="toggleComparison" class="btn btn--outline">Compare Schools</button>

<!-- School Selection Panel -->
<div id="comparisonPanel" style="display: none;">
    <!-- ... entire panel ... -->
</div>

<!-- JavaScript comparison logic (Lines ~492-640) -->
<script>
// DELETE all comparison-related code
</script>
```

#### 5.2 Remove from Views
```python
# dashboards/views.py

# DELETE this entire function
def smme_kpi_comparison(request):
    # ... entire function ...
    pass
```

#### 5.3 Remove from URLs
```python
# dashboards/urls.py

# DELETE this line
path("dashboards/smme-kpi/comparison/", views.smme_kpi_comparison, name="smme_kpi_comparison"),
```

**Testing Checklist:**
- [ ] No "Compare Schools" button visible
- [ ] No JavaScript errors in console
- [ ] Chart still renders correctly
- [ ] Simplified, cleaner interface

---

### 🐛 Task 6: Fix Quarter Display Bug (Q1-Q1 Issue)

**Goal:** Ensure quarters display as "Q1", "Q2", "Q3", "Q4" not "Q1-Q1"

**Priority:** HIGH  
**Estimated Time:** 30 minutes  
**Files to Investigate:**
- `submissions/models.py` (Period.__str__ method)
- `templates/dashboards/smme_kpi_dashboard.html` (chart labels)
- `dashboards/views.py` (quarter data preparation)

**Root Cause Analysis:**

The issue might be:
1. Period `label` field includes both quarter and school year
2. Chart is concatenating quarter_tag with label
3. Template is using wrong field for display

**Fix Strategy:**

#### 6.1 Check Period Data
```bash
python manage.py shell
```
```python
from submissions.models import Period
periods = Period.objects.filter(school_year_start=2025)
for p in periods:
    print(f"ID: {p.id}, Label: {p.label}, Quarter: {p.quarter_tag}")
```

Expected output:
```
ID: 1, Label: Q1 - SY 2025-2026, Quarter: Q1
ID: 2, Label: Q2 - SY 2025-2026, Quarter: Q2
ID: 3, Label: Q3 - SY 2025-2026, Quarter: Q3
ID: 4, Label: Q4 - SY 2025-2026, Quarter: Q4
```

#### 6.2 Fix Chart Labels
```javascript
// In template, use ONLY quarter_tag, not label

// WRONG:
chart_labels = [{{ period.label|safe }}, ...]  // Might show "Q1 - SY 2025-2026"

// CORRECT:
chart_labels = ['{{ period.quarter_tag }}', ...]  // Shows "Q1"
```

#### 6.3 Update View Context
```python
# dashboards/views.py

# Ensure chart_data uses quarter_tag only
chart_data = {
    'labels': [period.quarter_tag for period in periods],  # NOT period.label
    'values': [...]
}
```

**Testing Checklist:**
- [ ] Chart X-axis shows "Q1", "Q2", "Q3", "Q4"
- [ ] No duplicate labels (e.g., "Q1-Q1")
- [ ] Quarter dropdown shows clean labels
- [ ] Database has correct quarter_tag values

---

### 📚 Task 7: Update Documentation

**Goal:** Reflect all changes in documentation

**Priority:** LOW  
**Estimated Time:** 1 hour  
**Files to Update:**
- `docs/SMME_DASHBOARD_PHASE_4_COMPLETE.md`
- `docs/SMME_DASHBOARD_REFINEMENT_PLAN_V2.md`
- Create new `docs/PERIOD_MANAGEMENT_SIMPLIFIED.md`

**Changes Required:**

#### 7.1 Create New Documentation
Document the simplified period management system

#### 7.2 Update Existing Docs
Remove references to:
- Comparison feature
- Period date fields
- Emojis in UI

Add references to:
- AJAX filtering
- Smooth transitions
- Simplified period model

---

## Implementation Order

### Phase 1: Critical Data Fixes (Day 1 - 6 hours) ⚠️ HIGH PRIORITY
1. ✅ **Task 0: Add Form Period Classification** (1.5 hours) - Link forms to periods properly
2. ✅ **Task 8: Fix Quarter Display** (30 min) - Fix "Q1-Q1" bug  
3. ✅ **Task 0B: Fix Incomplete KPI Calculations** (4 hours) ⚠️ CRITICAL
   - Complete rewrite of kpi_calculators.py
   - Add SLP, Implementation, CRLA, PHILIRI, RMA indicators
   - This is the MOST IMPORTANT task - current KPIs are wrong!

### Phase 2: UI Improvements (Day 2 - 2.5 hours)
4. ✅ **Task 2: Remove Emojis** (30 min) - Professional interface
5. ✅ **Task 7: Remove Comparison Feature** (30 min) - Simplify dashboard
6. ✅ **Task 1: Simplify Period Management** (1.5 hours) - Remove date fields

### Phase 3: UX Enhancements (Day 3 - 3.5 hours)
7. ✅ **Task 6: Layout Optimization** (1.5 hours) - Fit everything on screen
8. ✅ **Task 5: AJAX Filters** (2 hours) - Smooth transitions

### Phase 4: Documentation (Day 4 - 1 hour)
9. ✅ **Task 9: Update Documentation** (1 hour) - Record all changes

**Total Estimated Time: 13-15 hours (spread over 3-4 days)**

---

## Testing Strategy

### Unit Tests
```python
# tests/test_period_model.py
def test_period_label_auto_generation():
    period = Period.objects.create(
        school_year_start=2025,
        quarter_tag='Q1'
    )
    assert period.label == 'Q1 - SY 2025-2026'

def test_period_display_order():
    q2 = Period.objects.create(school_year_start=2025, quarter_tag='Q2')
    q1 = Period.objects.create(school_year_start=2025, quarter_tag='Q1')
    
    periods = Period.objects.all()
    assert periods[0].quarter_tag == 'Q1'
    assert periods[1].quarter_tag == 'Q2'
```

### Integration Tests
- [ ] Dashboard loads without errors
- [ ] Filters update via AJAX
- [ ] Chart renders with correct labels
- [ ] No scrolling needed to see all elements
- [ ] Mobile responsive

### Manual Testing Checklist
- [ ] Create new period (only school year + quarter)
- [ ] View SMME dashboard
- [ ] Change school year filter → updates smoothly
- [ ] Change quarter filter → updates smoothly
- [ ] Chart shows Q1, Q2, Q3, Q4 (not Q1-Q1)
- [ ] All elements fit on screen
- [ ] No emojis visible
- [ ] No comparison button visible

---

## Rollback Plan

If issues arise:

### Database Rollback
```bash
# Revert migration
python manage.py migrate submissions <previous_migration_number>
```

### Code Rollback
```bash
# Revert to previous commit
git log --oneline  # Find commit hash
git revert <commit_hash>
```

### Emergency Hotfix
- Keep old `Period` fields as nullable
- Maintain backward compatibility
- Gradual migration vs big bang

---

## Success Criteria

### Functionality
- [x] Periods created with only school year + quarter
- [x] No date fields in period management
- [x] Dashboard updates without page reload
- [x] Smooth animations on filter change
- [x] All elements visible without scrolling

### Performance
- [x] AJAX updates < 500ms
- [x] Chart animation smooth (60fps)
- [x] No visible lag or flicker

### User Experience
- [x] Professional appearance (no emojis)
- [x] Clean, simplified interface
- [x] Intuitive filter usage
- [x] Quarters display correctly (Q1, Q2, Q3, Q4)

### Code Quality
- [x] No console errors
- [x] No Python errors
- [x] Tests pass
- [x] Documentation updated

---

## Resources

### Django Documentation
- [Model Meta Options](https://docs.djangoproject.com/en/5.1/ref/models/options/)
- [Migrations](https://docs.djangoproject.com/en/5.1/topics/migrations/)
- [JSON Responses](https://docs.djangoproject.com/en/5.1/ref/request-response/#jsonresponse-objects)

### JavaScript/CSS
- [Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)
- [CSS Flexbox](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Flexible_Box_Layout)
- [CSS Grid](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Grid_Layout)
- [Chart.js Animations](https://www.chartjs.org/docs/latest/configuration/animations.html)

---

## Notes

- **Migration Safety**: Test migration on copy of production database first
- **Browser Compatibility**: Test AJAX on Chrome, Firefox, Safari, Edge
- **Performance**: Monitor query times with Django Debug Toolbar
- **User Training**: May need brief training on new filter behavior

---

**End of Action Plan**

**Next Step:** Review plan with stakeholders, then begin Phase 1 implementation.
