# SMEA Form 1 KPI Analysis & Implementation Plan

**Date**: October 17, 2025  
**Status**: In Progress  
**Priority**: HIGH

---

## 📋 SMEA FORM 1 STRUCTURE (From Code Analysis)

### **Key Components**:

#### **1. Projects & Activities** (`SMEAProject` + `SMEAActivityRow`)
- **Purpose**: Track school improvement projects with baseline/monitoring data
- **Fields**:
  - `project_title`: Name of the project
  - `area_of_concern`: What the project addresses
  - `conference_date`: Date of assessment
  - **Activities** (multiple rows per project):
    - `activity`: Description
    - `output_target` vs `output_actual`
    - `timeframe_target` vs `timeframe_actual`
    - `budget_target` vs `budget_actual`
    - `interpretation`: Findings & analysis
    - `issues_unaddressed`: Problems not resolved
    - `facilitating_factors`: What helped
    - `agreements`: Action points

#### **2. Implementation & Action Points** (`Form1PctRow`)
- **Purpose**: Percentage implementation per action area
- **Action Areas** (4 areas from `SMEAActionArea`):
  1. **ACCESS** - "Access"
  2. **QUALITY** - "Quality"
  3. **EQUITY** - "Equity"
  4. **ENABLING_MECHANISMS** - "Enabling Mechanisms"
- **Fields**:
  - `area`: One of the 4 action areas
  - `percent`: Implementation percentage (0-100)
  - `action_points`: Description of actions

#### **3. Student Learning Progress (SLP)** (`Form1SLPRow`)
- **Purpose**: Track student performance by grade/subject
- **Key Fields**:
  - `grade_label`: "Kinder", "Grade 1", ... "Grade 12"
  - `subject`: Subject code (overall, filipino, english, mathematics, etc.)
  - `enrolment`: Total students
  - **Performance Categories** (5 levels):
    - **`dnme`**: Did Not Meet Expectations ❌ (MAIN KPI!)
    - `fs`: Fairly Satisfactory
    - `s`: Satisfactory
    - `vs`: Very Satisfactory
    - `o`: Outstanding
- **Calculated Property** `get_pct_breakdown()`:
  ```python
  {
      'dnme_pct': round((self.dnme / self.enrolment) * 100, 2),
      'fs_pct': ...,
      's_pct': ...,
      'vs_pct': ...,
      'o_pct': ...
  }
  ```

#### **4. SLP Analysis** (`Form1SLPAnalysis`)
- **Purpose**: Root cause analysis and intervention strategies
- **Fields**:
  - `dnme_factors`: Why learners didn't meet expectations
  - `fs_factors`: Why learners are fairly satisfactory
  - `s_practices`: Best practices for satisfactory learners
  - `vs_practices`: Best practices for very satisfactory learners
  - `o_practices`: Best practices for outstanding learners
  - `overall_intervention`: Strategy to address DNME learners

#### **5. Top 5 DNME** (`Form1SLPTopDNME`)
- **Purpose**: Identify grades/subjects with highest DNME rates
- **Fields**:
  - `grade_label`: Grade level
  - `subject_label`: Subject name
  - `is_offered`: Whether subject is offered
  - `position`: Ranking (1-5)

---

## 🎯 KEY PERFORMANCE INDICATORS (KPIs) FOR DASHBOARD

### **PRIMARY KPI: DNME Percentage** ⭐
**Definition**: Percentage of students who Did Not Meet Expectations across all grades/subjects

**Calculation**:
```python
total_students = sum(row.enrolment for row in Form1SLPRow where is_offered=True)
total_dnme = sum(row.dnme for row in Form1SLPRow where is_offered=True)
dnme_percentage = (total_dnme / total_students) * 100 if total_students > 0 else 0
```

**Display**: 
- Lower is better! ✅
- Target: < 10% (schools should have < 10% DNME)
- Warning: 10-20% (needs attention)
- Critical: > 20% (urgent intervention needed)

---

### **SECONDARY KPIs: Implementation Areas**

#### **Access Percentage**
**Definition**: Implementation rate of access-related action points
**Calculation**: Average `percent` from `Form1PctRow` where `area='access'`

#### **Quality Percentage**
**Definition**: Implementation rate of quality-related action points
**Calculation**: Average `percent` from `Form1PctRow` where `area='quality'`

#### **Equity Percentage**
**Definition**: Implementation rate of equity-related action points
**Calculation**: Average `percent` from `Form1PctRow` where `area='equity'`

#### **Enabling Mechanisms Percentage**
**Definition**: Implementation rate of enabling mechanisms action points
**Calculation**: Average `percent` from `Form1PctRow` where `area='enabling_mechanisms'`

**Display**: Higher is better! ✅
- Target: > 80% (good implementation)
- Warning: 50-80% (moderate progress)
- Critical: < 50% (low implementation)

---

### **TERTIARY KPIs: Performance Distribution**

#### **Outstanding Percentage**
**Calculation**: `(sum(row.o) / sum(row.enrolment)) * 100`

#### **Very Satisfactory Percentage**
**Calculation**: `(sum(row.vs) / sum(row.enrolment)) * 100`

#### **Satisfactory Percentage**
**Calculation**: `(sum(row.s) / sum(row.enrolment)) * 100`

#### **Fairly Satisfactory Percentage**
**Calculation**: `(sum(row.fs) / sum(row.enrolment)) * 100`

---

## 📊 DASHBOARD REQUIREMENTS

### **Chart Display: Bar Chart by Quarter (Q1-Q4)**

**X-Axis**: Quarters (Q1 Report, Q2 Report, Q3 Report, Q4 Report)
**Y-Axis**: Percentage (0-100%)
**Bars**: Selected KPI metric

### **KPI Metric Selector** (Dropdown):
```
Options:
1. DNME Percentage (default) - RED bars (lower is better)
2. Access Implementation - BLUE bars (higher is better)
3. Quality Implementation - GREEN bars (higher is better)
4. Equity Implementation - PURPLE bars (higher is better)
5. Enabling Mechanisms Implementation - ORANGE bars (higher is better)
6. Overall Implementation (average of 4 areas) - TEAL bars (higher is better)
7. Outstanding Students % - GOLD bars (higher is better)
8. Performance Distribution (stacked bar: DNME, FS, S, VS, O)
```

### **Summary Cards** (Top of dashboard):
```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│ Total Schools   │ Avg DNME %      │ Avg Access %    │ Avg Quality %   │ Avg Equity %    │
│                 │                 │                 │                 │                 │
│      45         │     12.5%       │     78%         │     82%         │     75%         │
│                 │  (⚠️ Warning)   │  (✅ Good)      │  (✅ Good)      │  (✅ Good)      │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

---

## 💻 IMPLEMENTATION DETAILS

### **File: `dashboards/kpi_calculators.py`** (NEW)

```python
from django.db.models import Sum, Count, Q, F
from submissions.models import (
    Submission, Form1SLPRow, Form1PctRow
)


def calculate_dnme_percentage(submissions):
    """
    Calculate DNME percentage across all SMEA Form 1 submissions.
    
    Returns: {
        'dnme_pct': float,  # Overall DNME percentage
        'total_students': int,
        'total_dnme': int,
        'by_grade': {...}  # Optional: breakdown by grade
    }
    """
    total_students = 0
    total_dnme = 0
    by_grade = {}
    
    for submission in submissions:
        # Get all SLP rows for this submission
        slp_rows = Form1SLPRow.objects.filter(
            submission=submission,
            is_offered=True  # Only count offered subjects
        )
        
        for row in slp_rows:
            total_students += row.enrolment
            total_dnme += row.dnme
            
            # Optional: Track by grade
            grade = row.grade_label
            if grade not in by_grade:
                by_grade[grade] = {'students': 0, 'dnme': 0}
            by_grade[grade]['students'] += row.enrolment
            by_grade[grade]['dnme'] += row.dnme
    
    dnme_pct = round((total_dnme / total_students * 100), 2) if total_students > 0 else 0
    
    # Calculate by_grade percentages
    for grade, data in by_grade.items():
        data['dnme_pct'] = round((data['dnme'] / data['students'] * 100), 2) if data['students'] > 0 else 0
    
    return {
        'dnme_pct': dnme_pct,
        'total_students': total_students,
        'total_dnme': total_dnme,
        'by_grade': by_grade
    }


def calculate_implementation_areas(submissions):
    """
    Calculate average implementation percentage for each action area.
    
    Returns: {
        'access': float,
        'quality': float,
        'equity': float,
        'enabling_mechanisms': float,
        'overall': float  # Average of all 4
    }
    """
    areas = {
        'access': [],
        'quality': [],
        'equity': [],
        'enabling_mechanisms': []
    }
    
    for submission in submissions:
        # Get implementation percentages
        pct_rows = Form1PctRow.objects.filter(
            header__submission=submission
        )
        
        for row in pct_rows:
            areas[row.area].append(row.percent)
    
    # Calculate averages
    result = {}
    for area, percentages in areas.items():
        result[area] = round(sum(percentages) / len(percentages), 1) if percentages else 0
    
    # Overall average
    result['overall'] = round(
        sum(result.values()) / len(result), 1
    ) if result else 0
    
    return result


def calculate_performance_distribution(submissions):
    """
    Calculate distribution of student performance levels.
    
    Returns: {
        'dnme_pct': float,
        'fs_pct': float,
        's_pct': float,
        'vs_pct': float,
        'o_pct': float
    }
    """
    total_students = 0
    totals = {'dnme': 0, 'fs': 0, 's': 0, 'vs': 0, 'o': 0}
    
    for submission in submissions:
        slp_rows = Form1SLPRow.objects.filter(
            submission=submission,
            is_offered=True
        )
        
        for row in slp_rows:
            total_students += row.enrolment
            totals['dnme'] += row.dnme
            totals['fs'] += row.fs
            totals['s'] += row.s
            totals['vs'] += row.vs
            totals['o'] += row.o
    
    if total_students == 0:
        return {k: 0 for k in ['dnme_pct', 'fs_pct', 's_pct', 'vs_pct', 'o_pct']}
    
    return {
        'dnme_pct': round((totals['dnme'] / total_students * 100), 2),
        'fs_pct': round((totals['fs'] / total_students * 100), 2),
        's_pct': round((totals['s'] / total_students * 100), 2),
        'vs_pct': round((totals['vs'] / total_students * 100), 2),
        'o_pct': round((totals['o'] / total_students * 100), 2),
    }


def get_kpi_data_for_period(period, kpi_metric='dnme'):
    """
    Get KPI data for a specific period.
    
    Args:
        period: Period object
        kpi_metric: 'dnme', 'access', 'quality', 'equity', 'enabling_mechanisms', 
                    'overall_implementation', 'performance_distribution'
    
    Returns: dict with KPI values
    """
    # Get all approved SMEA Form 1 submissions for this period
    submissions = Submission.objects.filter(
        period=period,
        form_template__code='smea-form-1',  # Adjust if different code
        status__in=['submitted', 'noted', 'approved']
    )
    
    if not submissions.exists():
        return None
    
    if kpi_metric == 'dnme':
        return calculate_dnme_percentage(submissions)
    elif kpi_metric in ['access', 'quality', 'equity', 'enabling_mechanisms', 'overall_implementation']:
        impl_data = calculate_implementation_areas(submissions)
        if kpi_metric == 'overall_implementation':
            return {'value': impl_data['overall']}
        return {'value': impl_data[kpi_metric]}
    elif kpi_metric == 'performance_distribution':
        return calculate_performance_distribution(submissions)
    
    return None
```

---

### **File: `dashboards/views.py`** - Update `smme_kpi_dashboard`

```python
from dashboards.kpi_calculators import get_kpi_data_for_period


def smme_kpi_dashboard(request):
    """SMME KPI Dashboard with real SMEA Form 1 metrics"""
    
    # Get SMME section
    try:
        smme_section = Section.objects.get(code__iexact='smme')
    except Section.DoesNotExist:
        messages.error(request, "SMME section not found.")
        return redirect('school_home')
    
    # Get filters
    school_year = request.GET.get('school_year', Period.objects.order_by('-school_year_start').values_list('school_year_start', flat=True).first() or 2025)
    kpi_metric = request.GET.get('kpi_metric', 'dnme')  # NEW!
    view_type = request.GET.get('view_type', 'quarterly')
    chart_type = request.GET.get('chart_type', 'bar')
    
    # Get periods for selected school year
    if view_type == 'quarterly':
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
        ).order_by('display_order')
    else:
        periods = Period.objects.filter(
            school_year_start=int(school_year)
        ).order_by('display_order')
    
    # Calculate KPIs per quarter
    kpi_data = []
    for period in periods:
        data = get_kpi_data_for_period(period, kpi_metric)
        
        if data:
            kpi_data.append({
                'period': period,
                'label': period.quarter_tag or period.label,
                'data': data
            })
    
    # Prepare chart data based on selected metric
    chart_data = prepare_chart_data(kpi_data, kpi_metric)
    
    # Calculate summary statistics
    summary = calculate_summary_statistics(kpi_data, kpi_metric)
    
    # Get total schools
    total_schools = School.objects.count()
    
    # Get available school years
    school_years = Period.objects.values_list('school_year_start', flat=True).distinct().order_by('-school_year_start')
    
    context = {
        'smme_section': smme_section,
        'periods': periods,
        'kpi_data': kpi_data,
        'chart_data': chart_data,
        'summary': summary,
        'total_schools': total_schools,
        'school_years': school_years,
        'selected_year': school_year,
        'selected_kpi': kpi_metric,
        'view_type': view_type,
        'chart_type': chart_type,
    }
    
    return render(request, 'dashboards/smme_kpi_dashboard.html', context)


def prepare_chart_data(kpi_data, kpi_metric):
    """Prepare chart data based on selected KPI metric"""
    labels = [item['label'] for item in kpi_data]
    
    if kpi_metric == 'dnme':
        values = [item['data'].get('dnme_pct', 0) for item in kpi_data]
        return {
            'labels': labels,
            'datasets': [{
                'label': 'DNME Percentage',
                'data': values,
                'backgroundColor': 'rgba(239, 68, 68, 0.8)',  # Red
                'borderColor': 'rgba(239, 68, 68, 1)',
                'borderWidth': 1
            }]
        }
    
    elif kpi_metric in ['access', 'quality', 'equity', 'enabling_mechanisms']:
        values = [item['data'].get('value', 0) for item in kpi_data]
        colors = {
            'access': 'rgba(59, 130, 246, 0.8)',  # Blue
            'quality': 'rgba(16, 185, 129, 0.8)',  # Green
            'equity': 'rgba(139, 92, 246, 0.8)',  # Purple
            'enabling_mechanisms': 'rgba(245, 158, 11, 0.8)'  # Orange
        }
        return {
            'labels': labels,
            'datasets': [{
                'label': f'{kpi_metric.replace("_", " ").title()} Implementation',
                'data': values,
                'backgroundColor': colors.get(kpi_metric, 'rgba(107, 114, 128, 0.8)'),
                'borderColor': colors.get(kpi_metric, 'rgba(107, 114, 128, 1)'),
                'borderWidth': 1
            }]
        }
    
    elif kpi_metric == 'performance_distribution':
        # Stacked bar chart
        dnme_values = [item['data'].get('dnme_pct', 0) for item in kpi_data]
        fs_values = [item['data'].get('fs_pct', 0) for item in kpi_data]
        s_values = [item['data'].get('s_pct', 0) for item in kpi_data]
        vs_values = [item['data'].get('vs_pct', 0) for item in kpi_data]
        o_values = [item['data'].get('o_pct', 0) for item in kpi_data]
        
        return {
            'labels': labels,
            'datasets': [
                {
                    'label': 'DNME',
                    'data': dnme_values,
                    'backgroundColor': 'rgba(239, 68, 68, 0.8)'
                },
                {
                    'label': 'Fairly Satisfactory',
                    'data': fs_values,
                    'backgroundColor': 'rgba(251, 191, 36, 0.8)'
                },
                {
                    'label': 'Satisfactory',
                    'data': s_values,
                    'backgroundColor': 'rgba(59, 130, 246, 0.8)'
                },
                {
                    'label': 'Very Satisfactory',
                    'data': vs_values,
                    'backgroundColor': 'rgba(16, 185, 129, 0.8)'
                },
                {
                    'label': 'Outstanding',
                    'data': o_values,
                    'backgroundColor': 'rgba(245, 158, 11, 0.8)'
                }
            ]
        }
    
    return {'labels': labels, 'datasets': []}
```

---

## 🔧 TEMPLATE UPDATES

### **File: `templates/dashboards/smme_kpi_dashboard.html`**

**Changes Needed**:

1. **Remove emoji** (line 16):
```html
<!-- BEFORE -->
<h1>📊 SMME KPI Dashboard</h1>

<!-- AFTER -->
<h1>SMME KPI Dashboard</h1>
```

2. **Add KPI Metric Selector** (after school_year dropdown):
```html
<!-- KPI Metric -->
<div>
    <label class="form-label" style="font-weight: 600;">KPI Metric</label>
    <select name="kpi_metric" class="form-input" onchange="this.form.submit()">
        <option value="dnme" {% if selected_kpi == 'dnme' %}selected{% endif %}>DNME Percentage</option>
        <option value="access" {% if selected_kpi == 'access' %}selected{% endif %}>Access Implementation</option>
        <option value="quality" {% if selected_kpi == 'quality' %}selected{% endif %}>Quality Implementation</option>
        <option value="equity" {% if selected_kpi == 'equity' %}selected{% endif %}>Equity Implementation</option>
        <option value="enabling_mechanisms" {% if selected_kpi == 'enabling_mechanisms' %}selected{% endif %}>Enabling Mechanisms</option>
        <option value="overall_implementation" {% if selected_kpi == 'overall_implementation' %}selected{% endif %}>Overall Implementation</option>
        <option value="performance_distribution" {% if selected_kpi == 'performance_distribution' %}selected{% endif %}>Performance Distribution</option>
    </select>
</div>
```

3. **Update Summary Cards**:
```html
<div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem;">
    <div class="card">
        <h6 style="color: #6b7280;">Total Schools</h6>
        <h3>{{ total_schools }}</h3>
    </div>
    
    <div class="card">
        <h6 style="color: #6b7280;">Avg DNME %</h6>
        <h3 style="color: {% if summary.avg_dnme < 10 %}#10b981{% elif summary.avg_dnme < 20 %}#f59e0b{% else %}#ef4444{% endif %};">
            {{ summary.avg_dnme|floatformat:1 }}%
        </h3>
        <small>{% if summary.avg_dnme < 10 %}✅ Good{% elif summary.avg_dnme < 20 %}⚠️ Warning{% else %}🚨 Critical{% endif %}</small>
    </div>
    
    <div class="card">
        <h6 style="color: #6b7280;">Avg Access %</h6>
        <h3 style="color: {% if summary.avg_access > 80 %}#10b981{% elif summary.avg_access > 50 %}#f59e0b{% else %}#ef4444{% endif %};">
            {{ summary.avg_access|floatformat:1 }}%
        </h3>
    </div>
    
    <div class="card">
        <h6 style="color: #6b7280;">Avg Quality %</h6>
        <h3 style="color: {% if summary.avg_quality > 80 %}#10b981{% elif summary.avg_quality > 50 %}#f59e0b{% else %}#ef4444{% endif %};">
            {{ summary.avg_quality|floatformat:1 }}%
        </h3>
    </div>
    
    <div class="card">
        <h6 style="color: #6b7280;">Avg Equity %</h6>
        <h3 style="color: {% if summary.avg_equity > 80 %}#10b981{% elif summary.avg_equity > 50 %}#f59e0b{% else %}#ef4444{% endif %};">
            {{ summary.avg_equity|floatformat:1 }}%
        </h3>
    </div>
</div>
```

---

## ✅ TESTING PLAN

1. **Create Test SMEA Form 1 Submissions**:
   - Create submissions for Q1, Q2, Q3, Q4
   - Add Form1SLPRow data with varying DNME percentages
   - Add Form1PctRow data for all 4 implementation areas

2. **Verify DNME Calculations**:
   - Check that DNME % matches manual calculation
   - Verify by-grade breakdown is correct

3. **Verify Implementation Area Calculations**:
   - Check Access, Quality, Equity, Enabling Mechanisms percentages
   - Verify overall average is correct

4. **Test Chart Display**:
   - Switch between different KPI metrics
   - Verify colors and labels are correct
   - Test stacked bar chart for performance distribution

5. **Test Summary Cards**:
   - Verify all averages are calculated correctly
   - Check color coding (green/yellow/red) works

---

## 🚀 IMPLEMENTATION ORDER

1. ✅ Remove emoji from title (5 min)
2. ✅ Add navbar integration (30 min)
3. ✅ Create kpi_calculators.py (1 hour)
4. ✅ Update smme_kpi_dashboard view (1 hour)
5. ✅ Update dashboard template (1 hour)
6. ✅ Test with real data (30 min)
7. ✅ Document for future expansion to SMEA Forms 2, 3, 4

---

## 🔮 FUTURE EXPANSION: SMEA Forms 2, 3, 4

**Design Consideration**: 
- Create separate dashboard for each form, OR
- Add "Form" dropdown selector to switch between SMEA 1/2/3/4
- Use same KPI calculator pattern
- Each form will have different KPI metrics based on its purpose

**Recommendation**: Create modular KPI calculator functions so they can be reused across all SMEA forms.
