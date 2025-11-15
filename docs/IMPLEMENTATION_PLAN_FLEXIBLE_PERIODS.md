# Implementation Plan: Flexible Period System + SMME KPI Charts

**Date**: October 17, 2025  
**Estimated Time**: 1 day (8 hours)  
**Priority**: HIGH

---

## OVERVIEW

### Goals
1. ✅ Add flexible period system to Directory Tools (Periods tab)
2. ✅ Add KPI charts to SMME dashboard (bar/line/doughnut)
3. ✅ Fix "Manage Forms" in SMME section
4. ✅ Enable filtering by school year and quarter

### Scope
- **3 main areas**: Period management, SMME KPI visualization, SMME form management
- **7 files to modify**: 2 models, 2 views, 3 templates
- **1 migration**: Add flexible period fields
- **Testing**: Each phase tested before moving to next

---

## PHASE 1: UPDATE PERIOD MODEL (2 hours)

### Task 1.1: Update Period Model
**File**: `submissions/models.py`

**Changes**:
```python
class Period(models.Model):
    # Core fields
    label = models.CharField(
        max_length=100,
        help_text="e.g., 'Q1 Report', 'First Quarter', 'November Submission'"
    )
    school_year_start = models.PositiveIntegerField(
        help_text="e.g., 2025 for SY 2025-2026"
    )
    
    # NEW: Flexible grouping
    quarter_tag = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text="Optional tag for filtering (Q1, Q2, Q3, Q4, S1, S2, etc.)"
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order for sorting in charts and dropdowns"
    )
    
    # NEW: Clear submission window
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
    
    # NEW: Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this period is active"
    )
    
    # Keep old fields for now (remove later)
    quarter = models.CharField(
        max_length=10,
        choices=[('Q1', 'Q1'), ('Q2', 'Q2'), ('Q3', 'Q3'), ('Q4', 'Q4')],
        blank=True,  # Make optional
        null=True
    )
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['school_year_start', 'display_order', 'id']
        # Remove old constraint
        # constraints = [UniqueConstraint(fields=['school_year_start', 'quarter'])]
    
    def __str__(self):
        return f"SY {self.school_year_start}-{self.school_year_start + 1} {self.label}"
    
    @property
    def school_year_end(self):
        return self.school_year_start + 1
    
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
    
    @property
    def status_badge(self):
        """HTML badge for period status"""
        if not self.is_active:
            return '<span class="badge bg-secondary">Inactive</span>'
        elif self.is_open:
            return '<span class="badge bg-success">Open</span>'
        else:
            return '<span class="badge bg-warning">Closed</span>'
```

**Expected Result**:
- New fields added without breaking existing data
- Old fields kept for backward compatibility
- Properties for status checking

---

### Task 1.2: Create Migration
**File**: `submissions/migrations/000X_add_flexible_period_fields.py`

**Command**:
```bash
python manage.py makemigrations submissions
```

**Migration content** (auto-generated):
```python
operations = [
    migrations.AddField(
        model_name='period',
        name='quarter_tag',
        field=models.CharField(blank=True, default='', max_length=20),
    ),
    migrations.AddField(
        model_name='period',
        name='display_order',
        field=models.PositiveIntegerField(default=0),
    ),
    migrations.AddField(
        model_name='period',
        name='open_date',
        field=models.DateField(blank=True, null=True),
    ),
    migrations.AddField(
        model_name='period',
        name='close_date',
        field=models.DateField(blank=True, null=True),
    ),
    migrations.AddField(
        model_name='period',
        name='is_active',
        field=models.BooleanField(default=True),
    ),
    migrations.AlterField(
        model_name='period',
        name='quarter',
        field=models.CharField(blank=True, max_length=10, null=True),
    ),
]
```

**Command**:
```bash
python manage.py migrate
```

**Expected Result**:
- 5 new fields added to Period table
- Existing periods still work (old fields intact)
- No data loss

---

### Task 1.3: Migrate Existing Periods
**File**: Create `scripts/migrate_periods.py`

**Purpose**: Convert existing periods to new format

**Script**:
```python
from django.core.management.base import BaseCommand
from submissions.models import Period

class Command(BaseCommand):
    help = 'Migrate existing periods to flexible format'
    
    def handle(self, *args, **options):
        periods = Period.objects.all()
        
        for period in periods:
            # Set quarter_tag from old quarter field
            if period.quarter and not period.quarter_tag:
                period.quarter_tag = period.quarter
                self.stdout.write(f"Set quarter_tag={period.quarter} for {period}")
            
            # Set display_order based on quarter
            if period.quarter and period.display_order == 0:
                quarter_map = {'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4}
                period.display_order = quarter_map.get(period.quarter, 0)
                self.stdout.write(f"Set display_order={period.display_order} for {period}")
            
            # Migrate dates
            if period.starts_on and not period.open_date:
                period.open_date = period.starts_on
                self.stdout.write(f"Set open_date={period.open_date} for {period}")
            
            if period.ends_on and not period.close_date:
                period.close_date = period.ends_on
                self.stdout.write(f"Set close_date={period.close_date} for {period}")
            
            # Update label if needed
            if not period.label or period.label == f"SY {period.school_year_start}-{period.school_year_start+1} {period.quarter}":
                period.label = f"{period.quarter} Report" if period.quarter else "Period"
                self.stdout.write(f"Set label={period.label} for {period}")
            
            period.save()
        
        self.stdout.write(self.style.SUCCESS(f"Migrated {periods.count()} periods"))
```

**Command**:
```bash
python manage.py migrate_periods
```

**Expected Result**:
- Existing periods converted to new format
- No data loss
- Periods ready for new system

---

## PHASE 2: UPDATE DIRECTORY TOOLS - PERIODS TAB (2 hours)

### Task 2.1: Update Period Creation View
**File**: `organizations/views.py`

**Changes**: Replace `create_school_year` handler

**New Implementation**:
```python
# Action: create_school_year (improved)
if action == "create_school_year":
    sy_start = request.POST.get("sy_start")
    
    # Validate
    try:
        sy_start = int(sy_start)
        sy_end = sy_start + 1
    except (ValueError, TypeError):
        messages.error(request, "Invalid school year start")
        return redirect("organizations:manage_directory")
    
    # Check for duplicates
    existing = Period.objects.filter(school_year_start=sy_start).exists()
    if existing:
        messages.error(request, f"School year {sy_start}-{sy_end} already exists")
        return redirect("organizations:manage_directory")
    
    # Create 4 quarters
    quarters = [
        {"tag": "Q1", "label": "Q1 Report", "order": 1},
        {"tag": "Q2", "label": "Q2 Report", "order": 2},
        {"tag": "Q3", "label": "Q3 Report", "order": 3},
        {"tag": "Q4", "label": "Q4 Report", "order": 4},
    ]
    
    created_periods = []
    
    for q in quarters:
        # Get optional dates from form
        q_lower = q['tag'].lower()
        open_date_str = request.POST.get(f"{q_lower}_open")
        close_date_str = request.POST.get(f"{q_lower}_close")
        
        # Parse dates
        open_date = None
        close_date = None
        
        if open_date_str:
            try:
                from datetime import datetime
                open_date = datetime.strptime(open_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
        
        if close_date_str:
            try:
                from datetime import datetime
                close_date = datetime.strptime(close_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
        
        # Create period
        period = Period.objects.create(
            school_year_start=sy_start,
            label=q['label'],
            quarter_tag=q['tag'],
            display_order=q['order'],
            open_date=open_date,
            close_date=close_date,
            is_active=True
        )
        created_periods.append(period)
    
    messages.success(
        request,
        f"Created school year {sy_start}-{sy_end} with 4 quarters: " +
        ", ".join([p.label for p in created_periods])
    )
    return redirect("organizations:manage_directory")
```

**Expected Result**:
- Creates 4 periods with flexible labels
- Sets quarter_tag for filtering
- Sets display_order for sorting
- Optional open/close dates

---

### Task 2.2: Add Single Period Creation
**File**: `organizations/views.py`

**New Action**:
```python
# Action: create_period (NEW)
if action == "create_period":
    sy_start = request.POST.get("sy_start")
    label = request.POST.get("label")
    quarter_tag = request.POST.get("quarter_tag", "")
    display_order = request.POST.get("display_order", 0)
    open_date_str = request.POST.get("open_date")
    close_date_str = request.POST.get("close_date")
    
    # Validate
    try:
        sy_start = int(sy_start)
        display_order = int(display_order)
    except (ValueError, TypeError):
        messages.error(request, "Invalid input")
        return redirect("organizations:manage_directory")
    
    if not label:
        messages.error(request, "Period label is required")
        return redirect("organizations:manage_directory")
    
    # Check for duplicate label in same school year
    existing = Period.objects.filter(
        school_year_start=sy_start,
        label=label
    ).exists()
    if existing:
        messages.error(request, f"Period '{label}' already exists for SY {sy_start}-{sy_start+1}")
        return redirect("organizations:manage_directory")
    
    # Parse dates
    open_date = None
    close_date = None
    
    if open_date_str:
        try:
            from datetime import datetime
            open_date = datetime.strptime(open_date_str, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid open date format")
            return redirect("organizations:manage_directory")
    
    if close_date_str:
        try:
            from datetime import datetime
            close_date = datetime.strptime(close_date_str, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid close date format")
            return redirect("organizations:manage_directory")
    
    # Create period
    period = Period.objects.create(
        school_year_start=sy_start,
        label=label,
        quarter_tag=quarter_tag,
        display_order=display_order,
        open_date=open_date,
        close_date=close_date,
        is_active=True
    )
    
    messages.success(request, f"Created period: {period}")
    return redirect("organizations:manage_directory")
```

**Expected Result**:
- Can create custom periods (not just Q1-Q4)
- Flexible labels and dates
- Optional quarter tag for filtering

---

### Task 2.3: Update Directory Template - Periods Tab
**File**: `templates/organizations/manage_directory.html`

**Changes**: Replace Periods tab content

**New UI**:
```html
<!-- Periods Tab -->
<div class="tab-pane fade" id="periods" role="tabpanel">
    <div class="row">
        <!-- Left Column: Quick Create 4 Quarters -->
        <div class="col-md-6">
            <div class="card shadow-sm mb-4">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0">📅 Quick Create: School Year (4 Quarters)</h5>
                </div>
                <div class="card-body">
                    <form method="post">
                        {% csrf_token %}
                        <input type="hidden" name="action" value="create_school_year">
                        
                        <div class="mb-3">
                            <label class="form-label fw-bold">School Year Start *</label>
                            <input type="number" name="sy_start" class="form-control" 
                                   placeholder="2025" min="2020" max="2050" required>
                            <small class="text-muted">This will create: SY 2025-2026 with Q1, Q2, Q3, Q4 Reports</small>
                        </div>
                        
                        <hr>
                        
                        <h6 class="mb-3">Quarter Deadlines (Optional)</h6>
                        
                        <!-- Q1 -->
                        <div class="mb-3">
                            <label class="form-label"><strong>Q1 Report</strong></label>
                            <div class="row">
                                <div class="col-6">
                                    <label class="form-label small">Open Date</label>
                                    <input type="date" name="q1_open" class="form-control">
                                </div>
                                <div class="col-6">
                                    <label class="form-label small">Close Date</label>
                                    <input type="date" name="q1_close" class="form-control">
                                </div>
                            </div>
                        </div>
                        
                        <!-- Q2 -->
                        <div class="mb-3">
                            <label class="form-label"><strong>Q2 Report</strong></label>
                            <div class="row">
                                <div class="col-6">
                                    <label class="form-label small">Open Date</label>
                                    <input type="date" name="q2_open" class="form-control">
                                </div>
                                <div class="col-6">
                                    <label class="form-label small">Close Date</label>
                                    <input type="date" name="q2_close" class="form-control">
                                </div>
                            </div>
                        </div>
                        
                        <!-- Q3 -->
                        <div class="mb-3">
                            <label class="form-label"><strong>Q3 Report</strong></label>
                            <div class="row">
                                <div class="col-6">
                                    <label class="form-label small">Open Date</label>
                                    <input type="date" name="q3_open" class="form-control">
                                </div>
                                <div class="col-6">
                                    <label class="form-label small">Close Date</label>
                                    <input type="date" name="q3_close" class="form-control">
                                </div>
                            </div>
                        </div>
                        
                        <!-- Q4 -->
                        <div class="mb-3">
                            <label class="form-label"><strong>Q4 Report</strong></label>
                            <div class="row">
                                <div class="col-6">
                                    <label class="form-label small">Open Date</label>
                                    <input type="date" name="q4_open" class="form-control">
                                </div>
                                <div class="col-6">
                                    <label class="form-label small">Close Date</label>
                                    <input type="date" name="q4_close" class="form-control">
                                </div>
                            </div>
                        </div>
                        
                        <button type="submit" class="btn btn-primary w-100">
                            <i class="bi bi-plus-circle"></i> Create School Year with 4 Quarters
                        </button>
                    </form>
                </div>
            </div>
        </div>
        
        <!-- Right Column: Create Single Period -->
        <div class="col-md-6">
            <div class="card shadow-sm mb-4">
                <div class="card-header bg-success text-white">
                    <h5 class="mb-0">➕ Create Single Period</h5>
                </div>
                <div class="card-body">
                    <form method="post">
                        {% csrf_token %}
                        <input type="hidden" name="action" value="create_period">
                        
                        <div class="mb-3">
                            <label class="form-label fw-bold">School Year Start *</label>
                            <input type="number" name="sy_start" class="form-control" 
                                   placeholder="2025" min="2020" max="2050" required>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label fw-bold">Period Label *</label>
                            <input type="text" name="label" class="form-control" 
                                   placeholder="e.g., Q1 Report, November Submission" required>
                            <small class="text-muted">Custom name for this period</small>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label fw-bold">Quarter Tag (Optional)</label>
                            <select name="quarter_tag" class="form-select">
                                <option value="">-- No tag (not shown in quarterly charts) --</option>
                                <option value="Q1">Q1 - First Quarter</option>
                                <option value="Q2">Q2 - Second Quarter</option>
                                <option value="Q3">Q3 - Third Quarter</option>
                                <option value="Q4">Q4 - Fourth Quarter</option>
                                <option value="S1">S1 - First Semester</option>
                                <option value="S2">S2 - Second Semester</option>
                            </select>
                            <small class="text-muted">For filtering and grouping in charts</small>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label fw-bold">Display Order</label>
                            <input type="number" name="display_order" class="form-control" 
                                   placeholder="1" value="1" min="0">
                            <small class="text-muted">Order in dropdowns and charts (1, 2, 3...)</small>
                        </div>
                        
                        <hr>
                        
                        <h6 class="mb-3">Submission Window</h6>
                        
                        <div class="mb-3">
                            <label class="form-label">Open Date</label>
                            <input type="date" name="open_date" class="form-control">
                            <small class="text-muted">When schools can start submitting</small>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label">Close Date</label>
                            <input type="date" name="close_date" class="form-control">
                            <small class="text-muted">Submission deadline</small>
                        </div>
                        
                        <button type="submit" class="btn btn-success w-100">
                            <i class="bi bi-plus-circle"></i> Create Period
                        </button>
                    </form>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Existing Periods Table -->
    <div class="card shadow-sm">
        <div class="card-header bg-light">
            <h5 class="mb-0">📋 Existing Periods</h5>
        </div>
        <div class="card-body">
            {% if periods %}
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead class="table-light">
                        <tr>
                            <th>School Year</th>
                            <th>Label</th>
                            <th>Tag</th>
                            <th>Order</th>
                            <th>Open Date</th>
                            <th>Close Date</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for period in periods %}
                        <tr>
                            <td>
                                <strong>SY {{ period.school_year_start }}-{{ period.school_year_end }}</strong>
                            </td>
                            <td>{{ period.label }}</td>
                            <td>
                                {% if period.quarter_tag %}
                                <span class="badge bg-info">{{ period.quarter_tag }}</span>
                                {% else %}
                                <span class="text-muted">—</span>
                                {% endif %}
                            </td>
                            <td>{{ period.display_order }}</td>
                            <td>
                                {% if period.open_date %}
                                {{ period.open_date|date:"M d, Y" }}
                                {% else %}
                                <span class="text-muted">Not set</span>
                                {% endif %}
                            </td>
                            <td>
                                {% if period.close_date %}
                                {{ period.close_date|date:"M d, Y" }}
                                {% else %}
                                <span class="text-muted">Not set</span>
                                {% endif %}
                            </td>
                            <td>
                                {% if period.is_active %}
                                    {% if period.is_open %}
                                    <span class="badge bg-success">Open</span>
                                    {% else %}
                                    <span class="badge bg-warning">Closed</span>
                                    {% endif %}
                                {% else %}
                                <span class="badge bg-secondary">Inactive</span>
                                {% endif %}
                            </td>
                            <td>
                                <form method="post" style="display:inline;" 
                                      onsubmit="return confirm('Delete period {{ period.label }}?');">
                                    {% csrf_token %}
                                    <input type="hidden" name="action" value="delete_period">
                                    <input type="hidden" name="period_id" value="{{ period.id }}">
                                    <button type="submit" class="btn btn-sm btn-outline-danger">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <p class="text-muted mb-0">No periods created yet.</p>
            {% endif %}
        </div>
    </div>
</div>
```

**Expected Result**:
- Two creation methods: Quick (4 quarters) + Single period
- Table shows all period details including status
- Delete functionality

---

## PHASE 3: SMME KPI DASHBOARD WITH CHARTS (3 hours)

### Task 3.1: Update SMME KPI View
**File**: `dashboards/views.py`

**Find**: `smme_kpi_dashboard` function

**Changes**: Add filtering and chart data

**New Implementation**:
```python
@login_required
def smme_kpi_dashboard(request):
    """SMME KPI Dashboard with charts and filtering"""
    from submissions.models import Period, Submission
    from organizations.models import School, Section
    from django.db.models import Count, Q
    from django.utils import timezone
    
    # Check permissions
    user = request.user
    if not (user.is_staff or user.profile.is_sgod_admin or 
            user.profile.is_section_admin or user.profile.is_psds):
        return HttpResponseForbidden("You don't have permission to view this page")
    
    # Check SMME section access
    from accounts import services
    allowed_codes = services.allowed_section_codes(user)
    if allowed_codes and 'SMME' not in [c.upper() for c in allowed_codes]:
        return HttpResponseForbidden("You don't have access to SMME section")
    
    # Get SMME section
    try:
        smme_section = Section.objects.get(code__iexact='smme')
    except Section.DoesNotExist:
        messages.error(request, "SMME section not found")
        return redirect('dashboards:dashboard')
    
    # Get filters from request
    school_year = request.GET.get('school_year')
    view_type = request.GET.get('view_type', 'quarterly')  # quarterly, all_periods, single
    period_id = request.GET.get('period_id')
    chart_type = request.GET.get('chart_type', 'bar')  # bar, line, doughnut, pie
    
    # Get available school years
    school_years = Period.objects.values_list(
        'school_year_start', flat=True
    ).distinct().order_by('-school_year_start')
    
    # Default to latest school year if not specified
    if not school_year and school_years:
        school_year = str(school_years[0])
    
    # Get periods based on filters
    if view_type == 'single' and period_id:
        # Single period view
        periods = Period.objects.filter(id=period_id)
    elif view_type == 'quarterly' and school_year:
        # Quarterly view - only periods with Q1-Q4 tags
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
        ).order_by('display_order')
    elif school_year:
        # All periods for the school year
        periods = Period.objects.filter(
            school_year_start=int(school_year)
        ).order_by('display_order')
    else:
        periods = Period.objects.none()
    
    # Get all periods for dropdown
    all_periods = Period.objects.all().order_by('-school_year_start', 'display_order')
    
    # Calculate KPIs for each period
    total_schools = School.objects.filter(is_active=True).count()
    kpi_data = []
    
    for period in periods:
        # Count schools that submitted in this period
        submitted_schools = Submission.objects.filter(
            period=period,
            form_template__section__code__iexact='smme',
            status__in=['submitted', 'noted', 'approved']
        ).values('school').distinct().count()
        
        # Count pending submissions
        pending_schools = Submission.objects.filter(
            period=period,
            form_template__section__code__iexact='smme',
            status='pending'
        ).values('school').distinct().count()
        
        # Calculate rate
        submission_rate = round(submitted_schools / total_schools * 100) if total_schools else 0
        
        kpi_data.append({
            'period': period,
            'label': period.quarter_tag or period.label,
            'full_label': str(period),
            'submitted': submitted_schools,
            'pending': pending_schools,
            'not_started': total_schools - submitted_schools - pending_schools,
            'total': total_schools,
            'rate': submission_rate,
            'is_open': period.is_open,
        })
    
    # Prepare chart data
    chart_data = {
        'labels': [d['label'] for d in kpi_data],
        'submitted': [d['submitted'] for d in kpi_data],
        'pending': [d['pending'] for d in kpi_data],
        'not_started': [d['not_started'] for d in kpi_data],
        'rates': [d['rate'] for d in kpi_data],
        'type': chart_type,
    }
    
    # Summary statistics (for current school year)
    if school_year and kpi_data:
        summary = {
            'total_schools': total_schools,
            'avg_submission_rate': round(sum(d['rate'] for d in kpi_data) / len(kpi_data)),
            'total_submitted': sum(d['submitted'] for d in kpi_data),
            'total_pending': sum(d['pending'] for d in kpi_data),
            'periods_count': len(kpi_data),
        }
    else:
        summary = None
    
    context = {
        'section': smme_section,
        'school_years': school_years,
        'selected_school_year': school_year,
        'view_type': view_type,
        'selected_period_id': period_id,
        'chart_type': chart_type,
        'kpi_data': kpi_data,
        'chart_data': chart_data,
        'summary': summary,
        'all_periods': all_periods,
        'total_schools': total_schools,
    }
    
    return render(request, 'dashboards/smme_kpi_dashboard.html', context)
```

**Expected Result**:
- Filters by school year and quarter
- Calculates submission rates per period
- Prepares data for charts
- Shows summary statistics

---

### Task 3.2: Create SMME KPI Dashboard Template
**File**: `templates/dashboards/smme_kpi_dashboard.html`

**Create new file**:
```html
{% extends "base.html" %}
{% load static %}

{% block title %}SMME KPI Dashboard{% endblock %}

{% block extra_head %}
<!-- Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
{% endblock %}

{% block content %}
<div class="container-fluid py-4">
    <!-- Header -->
    <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
            <h2 class="mb-1">📊 SMME KPI Dashboard</h2>
            <p class="text-muted mb-0">School Management, Monitoring and Evaluation</p>
        </div>
        <a href="{% url 'dashboards:dashboard' %}" class="btn btn-outline-secondary">
            <i class="bi bi-arrow-left"></i> Back to Dashboard
        </a>
    </div>
    
    <!-- Filters -->
    <div class="card shadow-sm mb-4">
        <div class="card-body">
            <form method="get" class="row g-3">
                <!-- School Year -->
                <div class="col-md-3">
                    <label class="form-label fw-bold">School Year</label>
                    <select name="school_year" class="form-select" onchange="this.form.submit()">
                        {% for sy in school_years %}
                        <option value="{{ sy }}" {% if sy|stringformat:"s" == selected_school_year %}selected{% endif %}>
                            SY {{ sy }}-{{ sy|add:1 }}
                        </option>
                        {% endfor %}
                    </select>
                </div>
                
                <!-- View Type -->
                <div class="col-md-3">
                    <label class="form-label fw-bold">View Type</label>
                    <select name="view_type" class="form-select" id="viewTypeSelect" onchange="handleViewTypeChange()">
                        <option value="quarterly" {% if view_type == 'quarterly' %}selected{% endif %}>
                            Quarterly Comparison (Q1-Q4)
                        </option>
                        <option value="all_periods" {% if view_type == 'all_periods' %}selected{% endif %}>
                            All Periods
                        </option>
                        <option value="single" {% if view_type == 'single' %}selected{% endif %}>
                            Single Period
                        </option>
                    </select>
                </div>
                
                <!-- Period (shown only for single view) -->
                <div class="col-md-3" id="periodSelectDiv" style="{% if view_type != 'single' %}display:none;{% endif %}">
                    <label class="form-label fw-bold">Period</label>
                    <select name="period_id" class="form-select">
                        {% for period in all_periods %}
                        <option value="{{ period.id }}" {% if period.id|stringformat:"s" == selected_period_id %}selected{% endif %}>
                            {{ period }}
                        </option>
                        {% endfor %}
                    </select>
                </div>
                
                <!-- Chart Type -->
                <div class="col-md-3">
                    <label class="form-label fw-bold">Chart Type</label>
                    <select name="chart_type" class="form-select" onchange="this.form.submit()">
                        <option value="bar" {% if chart_type == 'bar' %}selected{% endif %}>Bar Chart</option>
                        <option value="line" {% if chart_type == 'line' %}selected{% endif %}>Line Chart</option>
                        <option value="doughnut" {% if chart_type == 'doughnut' %}selected{% endif %}>Doughnut Chart</option>
                        <option value="pie" {% if chart_type == 'pie' %}selected{% endif %}>Pie Chart</option>
                    </select>
                </div>
                
                <div class="col-12">
                    <button type="submit" class="btn btn-primary">
                        <i class="bi bi-bar-chart"></i> Update Chart
                    </button>
                </div>
            </form>
        </div>
    </div>
    
    <!-- Summary Statistics -->
    {% if summary %}
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card shadow-sm">
                <div class="card-body text-center">
                    <h6 class="text-muted mb-2">Total Schools</h6>
                    <h3 class="mb-0">{{ summary.total_schools }}</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card shadow-sm">
                <div class="card-body text-center">
                    <h6 class="text-muted mb-2">Avg Submission Rate</h6>
                    <h3 class="mb-0 text-success">{{ summary.avg_submission_rate }}%</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card shadow-sm">
                <div class="card-body text-center">
                    <h6 class="text-muted mb-2">Total Submitted</h6>
                    <h3 class="mb-0 text-primary">{{ summary.total_submitted }}</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card shadow-sm">
                <div class="card-body text-center">
                    <h6 class="text-muted mb-2">Pending</h6>
                    <h3 class="mb-0 text-warning">{{ summary.total_pending }}</h3>
                </div>
            </div>
        </div>
    </div>
    {% endif %}
    
    <!-- Chart -->
    <div class="card shadow-sm mb-4">
        <div class="card-header bg-light">
            <h5 class="mb-0">
                {% if view_type == 'quarterly' %}
                Quarterly Submission Rates - SY {{ selected_school_year }}-{{ selected_school_year|add:1 }}
                {% elif view_type == 'single' %}
                Single Period View
                {% else %}
                All Periods - SY {{ selected_school_year }}-{{ selected_school_year|add:1 }}
                {% endif %}
            </h5>
        </div>
        <div class="card-body">
            {% if kpi_data %}
            <canvas id="kpiChart" width="400" height="150"></canvas>
            {% else %}
            <p class="text-muted text-center py-5 mb-0">
                No data available. Please create periods in the Directory Tools.
            </p>
            {% endif %}
        </div>
    </div>
    
    <!-- Detailed Table -->
    {% if kpi_data %}
    <div class="card shadow-sm">
        <div class="card-header bg-light">
            <h5 class="mb-0">Detailed Statistics</h5>
        </div>
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead class="table-light">
                        <tr>
                            <th>Period</th>
                            <th>Status</th>
                            <th>Submitted</th>
                            <th>Pending</th>
                            <th>Not Started</th>
                            <th>Total Schools</th>
                            <th>Submission Rate</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for data in kpi_data %}
                        <tr>
                            <td>
                                <strong>{{ data.full_label }}</strong>
                                {% if data.period.quarter_tag %}
                                <span class="badge bg-info ms-2">{{ data.period.quarter_tag }}</span>
                                {% endif %}
                            </td>
                            <td>
                                {% if data.is_open %}
                                <span class="badge bg-success">Open</span>
                                {% else %}
                                <span class="badge bg-warning">Closed</span>
                                {% endif %}
                            </td>
                            <td class="text-success fw-bold">{{ data.submitted }}</td>
                            <td class="text-warning fw-bold">{{ data.pending }}</td>
                            <td class="text-danger fw-bold">{{ data.not_started }}</td>
                            <td>{{ data.total }}</td>
                            <td>
                                <div class="progress" style="height: 25px;">
                                    <div class="progress-bar bg-success" role="progressbar" 
                                         style="width: {{ data.rate }}%;" 
                                         aria-valuenow="{{ data.rate }}" aria-valuemin="0" aria-valuemax="100">
                                        {{ data.rate }}%
                                    </div>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    {% endif %}
</div>

<script>
// Handle view type change
function handleViewTypeChange() {
    const viewType = document.getElementById('viewTypeSelect').value;
    const periodDiv = document.getElementById('periodSelectDiv');
    
    if (viewType === 'single') {
        periodDiv.style.display = 'block';
    } else {
        periodDiv.style.display = 'none';
    }
}

// Chart rendering
{% if kpi_data %}
const ctx = document.getElementById('kpiChart').getContext('2d');

const chartData = {
    labels: {{ chart_data.labels|safe }},
    datasets: []
};

const chartType = '{{ chart_type }}';

// Prepare datasets based on chart type
if (chartType === 'doughnut' || chartType === 'pie') {
    // For circular charts, show submitted vs pending vs not started
    chartData.datasets = [{
        label: 'Schools',
        data: [
            {{ chart_data.submitted|join:', ' }},
            {{ chart_data.pending|join:', ' }},
            {{ chart_data.not_started|join:', ' }}
        ],
        backgroundColor: [
            '#10b981',  // Green for submitted
            '#f59e0b',  // Orange for pending
            '#ef4444'   // Red for not started
        ]
    }];
    chartData.labels = ['Submitted', 'Pending', 'Not Started'];
} else {
    // For bar/line charts, show submission rates
    chartData.datasets = [{
        label: 'Submission Rate (%)',
        data: {{ chart_data.rates|safe }},
        backgroundColor: '#3b82f6',
        borderColor: '#3b82f6',
        borderWidth: 2,
        tension: 0.4
    }];
}

const config = {
    type: chartType,
    data: chartData,
    options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: {
                display: true,
                position: 'top'
            },
            tooltip: {
                enabled: true
            }
        },
        scales: chartType === 'bar' || chartType === 'line' ? {
            y: {
                beginAtZero: true,
                max: 100,
                ticks: {
                    callback: function(value) {
                        return value + '%';
                    }
                }
            }
        } : {}
    }
};

new Chart(ctx, config);
{% endif %}
</script>
{% endblock %}
```

**Expected Result**:
- Filters for school year, view type, period, chart type
- Summary statistics cards
- Dynamic Chart.js visualization
- Detailed table with progress bars

---

## PHASE 4: FIX SMME MANAGE FORMS (1 hour)

### Task 4.1: Identify Current Issues
**Action**: Test current SMME manage forms page

**Expected Issues**:
- Case sensitivity problems
- Missing period filtering
- No bulk actions
- Unclear form status

---

### Task 4.2: Update Manage Forms View
**File**: `submissions/views.py`

**Find**: `manage_section_forms` function

**Add period filtering**:
```python
@login_required
def manage_section_forms(request, section_code):
    """Manage forms for a section (e.g., SMME)"""
    from submissions.models import Period
    
    # Get section
    section = get_object_or_404(Section, code__iexact=section_code)
    
    # Check permissions
    user = request.user
    if not (user.is_staff or user.profile.is_sgod_admin):
        from accounts import services
        allowed_codes = services.allowed_section_codes(user)
        if section.code.upper() not in [c.upper() for c in allowed_codes]:
            return HttpResponseForbidden("You don't have access to this section")
    
    # Get filters
    period_id = request.GET.get('period')
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    
    # Get periods for dropdown
    periods = Period.objects.all().order_by('-school_year_start', 'display_order')
    
    # Get form templates for this section
    form_templates = FormTemplate.objects.filter(
        section__code__iexact=section_code
    ).order_by('sort_order', 'name')
    
    # Get submissions
    submissions = Submission.objects.filter(
        form_template__section__code__iexact=section_code
    ).select_related('school', 'form_template', 'period', 'submitted_by')
    
    # Apply filters
    if period_id:
        submissions = submissions.filter(period_id=period_id)
    
    if status_filter:
        submissions = submissions.filter(status=status_filter)
    
    if search_query:
        submissions = submissions.filter(
            Q(school__name__icontains=search_query) |
            Q(form_template__name__icontains=search_query)
        )
    
    # Order by latest first
    submissions = submissions.order_by('-updated_at')
    
    # Paginate
    from django.core.paginator import Paginator
    paginator = Paginator(submissions, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate statistics
    stats = {
        'total': submissions.count(),
        'submitted': submissions.filter(status__in=['submitted', 'noted', 'approved']).count(),
        'pending': submissions.filter(status='pending').count(),
        'draft': submissions.filter(status='draft').count(),
    }
    
    context = {
        'section': section,
        'form_templates': form_templates,
        'page_obj': page_obj,
        'periods': periods,
        'selected_period': period_id,
        'status_filter': status_filter,
        'search_query': search_query,
        'stats': stats,
    }
    
    return render(request, 'submissions/manage_section_forms.html', context)
```

**Expected Result**:
- Period filtering dropdown
- Status filtering
- Search functionality
- Statistics display

---

### Task 4.3: Update Manage Forms Template
**File**: `templates/submissions/manage_section_forms.html`

**Add filters section**:
```html
<!-- Filters -->
<div class="card shadow-sm mb-4">
    <div class="card-body">
        <form method="get" class="row g-3">
            <!-- Period Filter -->
            <div class="col-md-3">
                <label class="form-label fw-bold">Period</label>
                <select name="period" class="form-select" onchange="this.form.submit()">
                    <option value="">All Periods</option>
                    {% for period in periods %}
                    <option value="{{ period.id }}" {% if period.id|stringformat:"s" == selected_period %}selected{% endif %}>
                        {{ period }}
                    </option>
                    {% endfor %}
                </select>
            </div>
            
            <!-- Status Filter -->
            <div class="col-md-3">
                <label class="form-label fw-bold">Status</label>
                <select name="status" class="form-select" onchange="this.form.submit()">
                    <option value="">All Statuses</option>
                    <option value="draft" {% if status_filter == 'draft' %}selected{% endif %}>Draft</option>
                    <option value="pending" {% if status_filter == 'pending' %}selected{% endif %}>Pending</option>
                    <option value="submitted" {% if status_filter == 'submitted' %}selected{% endif %}>Submitted</option>
                    <option value="noted" {% if status_filter == 'noted' %}selected{% endif %}>Noted</option>
                    <option value="approved" {% if status_filter == 'approved' %}selected{% endif %}>Approved</option>
                </select>
            </div>
            
            <!-- Search -->
            <div class="col-md-4">
                <label class="form-label fw-bold">Search</label>
                <input type="text" name="q" class="form-control" 
                       placeholder="School or form name..." value="{{ search_query }}">
            </div>
            
            <div class="col-md-2">
                <label class="form-label">&nbsp;</label>
                <button type="submit" class="btn btn-primary w-100">
                    <i class="bi bi-search"></i> Filter
                </button>
            </div>
        </form>
        
        <!-- Statistics -->
        <div class="row mt-3">
            <div class="col-md-3">
                <div class="text-center">
                    <h6 class="text-muted mb-1">Total</h6>
                    <h4 class="mb-0">{{ stats.total }}</h4>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center">
                    <h6 class="text-muted mb-1">Submitted</h6>
                    <h4 class="mb-0 text-success">{{ stats.submitted }}</h4>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center">
                    <h6 class="text-muted mb-1">Pending</h6>
                    <h4 class="mb-0 text-warning">{{ stats.pending }}</h4>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center">
                    <h6 class="text-muted mb-1">Draft</h6>
                    <h4 class="mb-0 text-secondary">{{ stats.draft }}</h4>
                </div>
            </div>
        </div>
    </div>
</div>
```

**Expected Result**:
- Period dropdown filter
- Status filter
- Search box
- Statistics display

---

## TESTING CHECKLIST

### Phase 1 Testing: Period Model
- [ ] Run migrations successfully
- [ ] Create new period with all fields
- [ ] Verify old periods still work
- [ ] Check `is_open` property
- [ ] Run migrate_periods script

### Phase 2 Testing: Directory Tools
- [ ] Quick create 4 quarters for SY 2025-2026
- [ ] Verify all 4 periods created with correct tags
- [ ] Create single custom period
- [ ] Verify period appears in table
- [ ] Delete period
- [ ] Check validation (duplicate labels)

### Phase 3 Testing: SMME KPI Dashboard
- [ ] Access dashboard (check permissions)
- [ ] Filter by school year
- [ ] Select quarterly view (Q1-Q4 only)
- [ ] Select all periods view
- [ ] Select single period view
- [ ] Switch to bar chart
- [ ] Switch to line chart
- [ ] Switch to doughnut chart
- [ ] Switch to pie chart
- [ ] Verify chart data matches table
- [ ] Check summary statistics

### Phase 4 Testing: Manage Forms
- [ ] Access SMME manage forms
- [ ] Filter by period
- [ ] Filter by status
- [ ] Search for school/form
- [ ] Check statistics display
- [ ] Verify pagination works

---

## ROLLBACK PLAN

### If Phase 1 Fails (Model Changes)
```bash
# Rollback migration
python manage.py migrate submissions <previous_migration_number>

# Remove migration file
del submissions\migrations\000X_add_flexible_period_fields.py
```

### If Phase 2 Fails (Directory Tools)
- Revert organizations/views.py changes
- Revert manage_directory.html changes
- Old period creation still works

### If Phase 3 Fails (KPI Dashboard)
- Dashboard is new, no existing functionality broken
- Simply don't add to navigation
- Fix and re-deploy

### If Phase 4 Fails (Manage Forms)
- Revert to previous version
- Old manage forms page still accessible

---

## DEPLOYMENT STEPS

### Step 1: Backup Database
```bash
python manage.py dumpdata > backup_before_flexible_periods.json
```

### Step 2: Deploy Code
```bash
git pull
```

### Step 3: Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 4: Migrate Existing Periods
```bash
python manage.py migrate_periods
```

### Step 5: Test Each Phase
- Test period creation
- Test KPI dashboard
- Test manage forms

### Step 6: Verify Production
- Create test period
- View KPI charts
- Filter forms by period

---

## TIMELINE

| Phase | Task | Duration | Start | End |
|-------|------|----------|-------|-----|
| 1 | Update Period Model | 2 hours | 8:00 AM | 10:00 AM |
| 2 | Update Directory Tools | 2 hours | 10:00 AM | 12:00 PM |
| 3 | SMME KPI Dashboard | 3 hours | 1:00 PM | 4:00 PM |
| 4 | Fix Manage Forms | 1 hour | 4:00 PM | 5:00 PM |
| Testing | Full system testing | 30 min | 5:00 PM | 5:30 PM |

**Total**: 8.5 hours (1 day)

---

## SUCCESS CRITERIA

✅ **Phase 1 Complete**: Period model has flexible fields, migrations run successfully

✅ **Phase 2 Complete**: Can create school year with 4 quarters AND single custom periods

✅ **Phase 3 Complete**: SMME KPI dashboard shows charts with filtering by school year/quarter

✅ **Phase 4 Complete**: Manage forms has period filtering and better UI

✅ **Overall Success**: 
- SGOD admin can create flexible periods
- SMME section has KPI dashboard with bar/line/doughnut charts
- Can filter KPIs by school year and quarter
- Manage forms page improved with period filtering
- No existing functionality broken

---

## NEXT STEPS AFTER COMPLETION

1. Add KPI dashboards for other sections (YFS, HRD, DRRM, SMN, PR, SHN)
2. Add trend analysis (compare quarters year-over-year)
3. Add export to Excel for KPI data
4. Add email notifications for deadline reminders
5. Add bulk actions in manage forms (approve multiple, etc.)

---

## NOTES

- **Backward compatible**: Old periods still work during transition
- **Gradual migration**: Can test new system while old system runs
- **No breaking changes**: Existing submissions not affected
- **Chart.js**: Using CDN, no installation needed
- **Responsive**: All UIs mobile-friendly with Bootstrap 5

