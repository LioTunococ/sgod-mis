# Flexible Period System - RECOMMENDATION

**Date**: October 17, 2025  
**Goal**: Enable KPI filtering by quarter/school year with graphs  
**Use Case**: Bar charts showing Q1 vs Q2 vs Q3 vs Q4 performance

---

## MY RECOMMENDATION: **Hybrid Flexible System** ✅

**Keep it simple but powerful:**

### System Design

```python
Period Model:
  - school_year_start: 2025 (required)
  - label: "Q1 Report" (flexible, not hardcoded)
  - quarter_tag: "Q1" (optional, for filtering/grouping)
  - open_date: When schools can start submitting
  - close_date: Submission deadline
  - display_order: 1, 2, 3, 4 (for sorting)
```

### Why This Works

**1. Flexible Labels**
- Can name periods anything: "Q1 Report", "First Quarter", "November Submission"
- Not hardcoded to Q1/Q2/Q3/Q4

**2. Quarter Tag for Filtering**
- Add optional `quarter_tag` field ("Q1", "Q2", "Q3", "Q4", "Semester 1", etc.)
- Used for grouping in KPI charts
- If blank, won't appear in quarterly comparisons

**3. Flexible Dates**
- `open_date`: When submission opens (e.g., September 1)
- `close_date`: Deadline (e.g., November 30)
- Solves "Q1 data due in November" problem

**4. Display Order**
- Number 1-4 for quarters
- Controls order in charts/dropdowns
- Allows custom ordering

---

## EXAMPLE USAGE

### Scenario 1: Standard Quarterly Reporting

**Create 4 Periods for SY 2025-2026:**

```
Period 1:
  School Year: 2025-2026
  Label: "First Quarter Report"
  Quarter Tag: "Q1"
  Open Date: September 1, 2025
  Close Date: November 30, 2025
  Display Order: 1

Period 2:
  School Year: 2025-2026
  Label: "Second Quarter Report"
  Quarter Tag: "Q2"
  Open Date: December 1, 2025
  Close Date: February 28, 2026
  Display Order: 2

Period 3:
  School Year: 2025-2026
  Label: "Third Quarter Report"
  Quarter Tag: "Q3"
  Open Date: March 1, 2026
  Close Date: May 31, 2026
  Display Order: 3

Period 4:
  School Year: 2025-2026
  Label: "Fourth Quarter Report"
  Quarter Tag: "Q4"
  Open Date: June 1, 2026
  Close Date: August 31, 2026
  Display Order: 4
```

**KPI Dashboard Filters:**
```
School Year: [2025-2026 ▼]
Quarter: [All ▼] [Q1] [Q2] [Q3] [Q4]

[Show Bar Chart] [Show Circular Chart]
```

**Bar Chart Result:**
```
Submission Rate by Quarter (SY 2025-2026)

100% ┤     ██
 90% ┤     ██  ██
 80% ┤ ██  ██  ██
 70% ┤ ██  ██  ██  ██
     └─────────────────
      Q1  Q2  Q3  Q4
```

### Scenario 2: Mixed Reporting (Quarterly + Monthly)

**Create Periods for SY 2025-2026:**

```
Period 1: "Q1 Report" (Quarter Tag: Q1, Order: 1)
Period 2: "Q2 Report" (Quarter Tag: Q2, Order: 2)
Period 3: "November Monthly Report" (Quarter Tag: blank, Order: 5)
Period 4: "Q3 Report" (Quarter Tag: Q3, Order: 3)
Period 5: "Q4 Report" (Quarter Tag: Q4, Order: 4)
```

**KPI Dashboard:**
- Quarterly view shows only Q1-Q4 (has quarter_tag)
- Full view shows all 5 periods
- Monthly report doesn't appear in quarterly comparison

---

## DATABASE SCHEMA

### Updated Period Model

```python
class Period(models.Model):
    # Core
    label = models.CharField(max_length=100)  # "Q1 Report", "November Submission"
    school_year_start = models.PositiveIntegerField()  # 2025
    
    # Grouping/Filtering
    quarter_tag = models.CharField(
        max_length=20, 
        blank=True,
        help_text="Optional tag for grouping (e.g., Q1, Q2, Q3, Q4, S1, S2)"
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order for sorting (1, 2, 3, 4...)"
    )
    
    # Submission Window
    open_date = models.DateField(
        null=True, 
        blank=True,
        help_text="When schools can start submitting"
    )
    close_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Submission deadline"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['school_year_start', 'display_order', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['school_year_start', 'label'],
                name='unique_period_per_year'
            )
        ]
    
    def __str__(self):
        return f"SY {self.school_year_start}-{self.school_year_start + 1} {self.label}"
    
    @property
    def is_open(self):
        """Check if period is currently open for submissions"""
        from django.utils import timezone
        today = timezone.now().date()
        if self.open_date and today < self.open_date:
            return False
        if self.close_date and today > self.close_date:
            return False
        return self.is_active
```

---

## UI CHANGES

### 1. Period Creation Form (Simple)

```html
<h2>Create Period</h2>

<label>School Year Start *</label>
<input type="number" name="sy_start" placeholder="2025" required>

<label>Period Label * (e.g., "Q1 Report", "First Quarter")</label>
<input type="text" name="label" placeholder="Q1 Report" required>

<label>Quarter Tag (optional, for filtering)</label>
<select name="quarter_tag">
  <option value="">-- No tag (not shown in quarterly charts) --</option>
  <option value="Q1">Q1 - First Quarter</option>
  <option value="Q2">Q2 - Second Quarter</option>
  <option value="Q3">Q3 - Third Quarter</option>
  <option value="Q4">Q4 - Fourth Quarter</option>
  <option value="S1">S1 - First Semester</option>
  <option value="S2">S2 - Second Semester</option>
</select>

<label>Display Order (for sorting)</label>
<input type="number" name="display_order" placeholder="1" value="1">

<h3>Submission Window (optional)</h3>

<label>Open Date (when schools can submit)</label>
<input type="date" name="open_date">

<label>Close Date (submission deadline)</label>
<input type="date" name="close_date">

<button>Create Period</button>
```

### 2. Quick Create: School Year with 4 Quarters

```html
<h2>Quick Create: School Year with 4 Quarters</h2>

<label>School Year Start *</label>
<input type="number" name="sy_start" placeholder="2025" required>

<p>This will create 4 periods: Q1, Q2, Q3, Q4 Report</p>

<h3>Quarter Deadlines (optional)</h3>

<div>
  <strong>Q1 Report:</strong>
  <label>Open</label> <input type="date" name="q1_open">
  <label>Close</label> <input type="date" name="q1_close">
</div>

<div>
  <strong>Q2 Report:</strong>
  <label>Open</label> <input type="date" name="q2_open">
  <label>Close</label> <input type="date" name="q2_close">
</div>

<div>
  <strong>Q3 Report:</strong>
  <label>Open</label> <input type="date" name="q3_open">
  <label>Close</label> <input type="date" name="q3_close">
</div>

<div>
  <strong>Q4 Report:</strong>
  <label>Open</label> <input type="date" name="q4_open">
  <label>Close</label> <input type="date" name="q4_close">
</div>

<button>Create 4 Quarters</button>
```

**What it creates:**
```python
Period(label="Q1 Report", quarter_tag="Q1", display_order=1, ...)
Period(label="Q2 Report", quarter_tag="Q2", display_order=2, ...)
Period(label="Q3 Report", quarter_tag="Q3", display_order=3, ...)
Period(label="Q4 Report", quarter_tag="Q4", display_order=4, ...)
```

### 3. KPI Dashboard Filters

```html
<div class="filters">
  <label>School Year:</label>
  <select name="school_year">
    <option value="2025">SY 2025-2026</option>
    <option value="2024">SY 2024-2025</option>
  </select>
  
  <label>View Type:</label>
  <select name="view_type" id="viewType">
    <option value="quarterly">Quarterly Comparison (Q1-Q4)</option>
    <option value="all_periods">All Periods</option>
    <option value="single">Single Period</option>
  </select>
  
  <!-- Show only when view_type = "single" -->
  <div id="singlePeriod" style="display:none;">
    <label>Period:</label>
    <select name="period_id">
      <option value="1">Q1 Report</option>
      <option value="2">Q2 Report</option>
      <option value="3">Q3 Report</option>
      <option value="4">Q4 Report</option>
    </select>
  </div>
  
  <label>Chart Type:</label>
  <select name="chart_type">
    <option value="bar">Bar Chart</option>
    <option value="line">Line Chart</option>
    <option value="doughnut">Circular (Doughnut)</option>
    <option value="pie">Pie Chart</option>
  </select>
  
  <button>Show Chart</button>
</div>
```

---

## KPI CHARTS

### Chart 1: Quarterly Submission Rate (Bar Chart)

**Filter**: School Year = 2025-2026, View = Quarterly

**Data**:
```python
{
  'Q1': {'submitted': 85, 'total': 100, 'rate': 85},
  'Q2': {'submitted': 92, 'total': 100, 'rate': 92},
  'Q3': {'submitted': 78, 'total': 100, 'rate': 78},
  'Q4': {'submitted': 88, 'total': 100, 'rate': 88}
}
```

**Chart.js Code**:
```javascript
{
  type: 'bar',
  data: {
    labels: ['Q1', 'Q2', 'Q3', 'Q4'],
    datasets: [{
      label: 'Submission Rate (%)',
      data: [85, 92, 78, 88],
      backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444']
    }]
  },
  options: {
    scales: {
      y: { beginAtZero: true, max: 100 }
    }
  }
}
```

### Chart 2: School Year Progress (Doughnut Chart)

**Filter**: School Year = 2025-2026, View = All Periods

**Data**:
```python
{
  'Submitted': 255,
  'In Progress': 30,
  'Not Started': 115
}
```

**Chart.js Code**:
```javascript
{
  type: 'doughnut',
  data: {
    labels: ['Submitted', 'In Progress', 'Not Started'],
    datasets: [{
      data: [255, 30, 115],
      backgroundColor: ['#10b981', '#f59e0b', '#ef4444']
    }]
  }
}
```

### Chart 3: Quarterly Trend (Line Chart)

**Filter**: School Year = 2025-2026, View = Quarterly

**Chart.js Code**:
```javascript
{
  type: 'line',
  data: {
    labels: ['Q1', 'Q2', 'Q3', 'Q4'],
    datasets: [{
      label: 'Submission Rate (%)',
      data: [85, 92, 78, 88],
      borderColor: '#3b82f6',
      tension: 0.4
    }]
  }
}
```

---

## VIEW LOGIC (Example)

### KPI Dashboard View

```python
@login_required
@require_sgod_admin()
def kpi_dashboard(request):
    # Get filters
    school_year = request.GET.get('school_year', 2025)
    view_type = request.GET.get('view_type', 'quarterly')
    chart_type = request.GET.get('chart_type', 'bar')
    
    # Get periods
    if view_type == 'quarterly':
        # Only periods with quarter tags (Q1-Q4)
        periods = Period.objects.filter(
            school_year_start=school_year,
            quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
        ).order_by('display_order')
    else:
        # All periods
        periods = Period.objects.filter(
            school_year_start=school_year
        ).order_by('display_order')
    
    # Calculate KPIs for each period
    kpi_data = []
    for period in periods:
        total_schools = School.objects.count()
        submitted = Submission.objects.filter(
            period=period,
            status__in=['submitted', 'noted']
        ).values('school').distinct().count()
        
        kpi_data.append({
            'label': period.quarter_tag or period.label,
            'submitted': submitted,
            'total': total_schools,
            'rate': round(submitted / total_schools * 100) if total_schools else 0
        })
    
    # Prepare chart data
    chart_data = {
        'labels': [d['label'] for d in kpi_data],
        'data': [d['rate'] for d in kpi_data],
        'type': chart_type
    }
    
    return render(request, 'dashboards/kpi_dashboard.html', {
        'periods': periods,
        'kpi_data': kpi_data,
        'chart_data': chart_data,
        'school_year': school_year,
        'view_type': view_type,
        'chart_type': chart_type
    })
```

---

## MIGRATION PLAN

### Step 1: Add New Fields (Safe)

```python
# migrations/000X_add_flexible_period_fields.py

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('submissions', '000X_previous_migration'),
    ]
    
    operations = [
        # Add new fields as nullable first
        migrations.AddField(
            model_name='period',
            name='quarter_tag',
            field=models.CharField(max_length=20, blank=True, default=''),
        ),
        migrations.AddField(
            model_name='period',
            name='display_order',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='period',
            name='open_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='period',
            name='close_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='period',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
```

### Step 2: Data Migration (Convert Existing)

```python
# migrations/000X_migrate_quarter_to_quarter_tag.py

from django.db import migrations

def migrate_quarters(apps, schema_editor):
    Period = apps.get_model('submissions', 'Period')
    
    for period in Period.objects.all():
        # Extract quarter from old field
        if hasattr(period, 'quarter'):
            period.quarter_tag = period.quarter  # Q1 -> Q1
            
            # Set display order
            quarter_map = {'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4}
            period.display_order = quarter_map.get(period.quarter, 0)
            
            # Migrate dates
            if hasattr(period, 'starts_on'):
                period.open_date = period.starts_on
            if hasattr(period, 'ends_on'):
                period.close_date = period.ends_on
            
            period.save()

class Migration(migrations.Migration):
    dependencies = [
        ('submissions', '000X_add_flexible_period_fields'),
    ]
    
    operations = [
        migrations.RunPython(migrate_quarters),
    ]
```

### Step 3: Remove Old Fields (Breaking)

```python
# migrations/000X_remove_old_period_fields.py

from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('submissions', '000X_migrate_quarter_to_quarter_tag'),
    ]
    
    operations = [
        migrations.RemoveField(
            model_name='period',
            name='quarter',  # Remove hardcoded quarter
        ),
        migrations.RemoveField(
            model_name='period',
            name='starts_on',  # Remove ambiguous field
        ),
        migrations.RemoveField(
            model_name='period',
            name='ends_on',  # Remove ambiguous field
        ),
    ]
```

---

## FINAL RECOMMENDATION

### ✅ USE THIS SYSTEM

**Pros:**
1. ✅ Flexible labels (not hardcoded to Q1-Q4)
2. ✅ Quarter tags for filtering/charts
3. ✅ Flexible submission dates (solves November deadline issue)
4. ✅ Display order for custom sorting
5. ✅ Works for quarterly, semester, monthly, annual reports
6. ✅ Simple enough to understand
7. ✅ Powerful enough for KPI charts

**Implementation:**
- **Time**: 1 day
- **Complexity**: Medium
- **Risk**: Low (additive changes, can migrate gradually)

**What You Get:**
- Bar charts comparing Q1 vs Q2 vs Q3 vs Q4
- Circular charts showing completion rates
- Line charts showing trends
- Flexible enough for special reports
- No "Q1 due in November" confusion

---

## ANSWER TO YOUR QUESTION

> "What do you recommend? I want to filter to show KPI per quarter or school year, create circular or bar graph of the KPI."

**I recommend:** Implement the **Hybrid Flexible System** above.

**Why:**
- You can filter by school year ✅
- You can filter by quarter (Q1-Q4) ✅
- You can show bar charts comparing quarters ✅
- You can show circular/doughnut charts ✅
- Dates are flexible (solves the November issue) ✅
- Simple to use, powerful for analysis ✅

**Next Step:** Say "yes, implement this" and I'll start coding! 🚀
