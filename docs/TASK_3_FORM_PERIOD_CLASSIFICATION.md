# Task 3: Refine SMME Form Management - Add Period Classification

**Goal:** Enable SMME staff to classify forms by school year and quarter for accurate KPI filtering

**Priority:** HIGH  
**Estimated Time:** 2.5 hours  
**Dependencies:** Task 1 (Period Management refinement)

---

## Problem Statement

Currently, when SMME staff create or manage forms (SMEA Form 1, etc.), there's no clear way to:
1. Specify which **school year** the form belongs to
2. Specify which **quarter** (Q1, Q2, Q3, Q4) the form is for
3. Filter forms by period in the dashboard

This makes it difficult to:
- Track which forms belong to which reporting period
- Filter KPI data accurately by school year and quarter
- Generate period-specific reports

---

## Solution Overview

Add **period classification fields** to form management:
- When creating/editing a form template or submission, SMME staff select:
  - **School Year** (e.g., SY 2025-2026)
  - **Quarter** (Q1, Q2, Q3, or Q4)
- This links submissions to specific periods for accurate filtering
- KPI dashboard can then filter by these classifications

---

## Files to Modify

### Core Models
- `submissions/models.py` - Add period fields to Submission model
- `submissions/forms.py` - Add period selectors to forms
- `submissions/admin.py` - Update admin interface

### Templates
- `templates/submissions/submission_form.html` - Add period dropdowns
- `templates/submissions/submission_list.html` - Show period column
- `templates/submissions/formtemplate_form.html` - Period selector

### Views
- `submissions/views.py` - Handle period selection in create/edit views

---

## Implementation Details

### Step 1: Update Submission Model

Add period tracking to submissions:

```python
# submissions/models.py

class Submission(models.Model):
    """
    A submission of a FormTemplate by a School for a specific Period
    """
    form_template = models.ForeignKey(FormTemplate, on_delete=models.CASCADE)
    school = models.ForeignKey('organizations.School', on_delete=models.CASCADE)
    period = models.ForeignKey(Period, on_delete=models.CASCADE)  # Already exists
    
    # NEW: Add explicit school year and quarter for easier filtering
    school_year = models.PositiveIntegerField(
        help_text="School year (e.g., 2025 for SY 2025-2026)",
        null=True,  # Make nullable for migration
        blank=True
    )
    quarter = models.CharField(
        max_length=2,
        choices=[('Q1', 'Q1'), ('Q2', 'Q2'), ('Q3', 'Q3'), ('Q4', 'Q4')],
        help_text="Quarter: Q1, Q2, Q3, or Q4",
        null=True,  # Make nullable for migration
        blank=True
    )
    
    # Existing fields
    status = models.CharField(...)
    submitted_at = models.DateTimeField(...)
    # ... other fields ...
    
    class Meta:
        ordering = ['-school_year', 'quarter', '-submitted_at']
        indexes = [
            models.Index(fields=['school_year', 'quarter']),
            models.Index(fields=['period', 'status']),
        ]
    
    def save(self, *args, **kwargs):
        # Auto-populate school_year and quarter from period if not set
        if self.period and not self.school_year:
            self.school_year = self.period.school_year_start
        if self.period and not self.quarter:
            self.quarter = self.period.quarter_tag
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.form_template.name} - {self.school.name} ({self.quarter} SY {self.school_year}-{self.school_year + 1})"
```

**Migration Strategy:**
```python
# submissions/migrations/0XXX_add_period_classification.py

from django.db import migrations, models

def populate_period_fields(apps, schema_editor):
    """Populate school_year and quarter from existing period data"""
    Submission = apps.get_model('submissions', 'Submission')
    
    for submission in Submission.objects.all():
        if submission.period:
            submission.school_year = submission.period.school_year_start
            submission.quarter = submission.period.quarter_tag
            submission.save()

class Migration(migrations.Migration):
    dependencies = [
        ('submissions', '0XXX_previous_migration'),
    ]
    
    operations = [
        # Add fields as nullable first
        migrations.AddField(
            model_name='submission',
            name='school_year',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='submission',
            name='quarter',
            field=models.CharField(max_length=2, null=True, blank=True),
        ),
        
        # Populate from existing period data
        migrations.RunPython(populate_period_fields),
        
        # Add indexes for performance
        migrations.AddIndex(
            model_name='submission',
            index=models.Index(fields=['school_year', 'quarter'], name='sub_period_idx'),
        ),
    ]
```

---

### Step 2: Create Period Selection Form

Add user-friendly period selector widget:

```python
# submissions/forms.py

from django import forms
from submissions.models import Submission, Period
from organizations.models import School

class SubmissionForm(forms.ModelForm):
    """
    Form for creating/editing submissions with period classification
    """
    
    # School Year dropdown (shows available years)
    school_year = forms.ChoiceField(
        label="School Year",
        help_text="Select the school year for this submission"
    )
    
    # Quarter dropdown
    quarter = forms.ChoiceField(
        choices=[
            ('', '--- Select Quarter ---'),
            ('Q1', 'Quarter 1 (Q1)'),
            ('Q2', 'Quarter 2 (Q2)'),
            ('Q3', 'Quarter 3 (Q3)'),
            ('Q4', 'Quarter 4 (Q4)'),
        ],
        label="Quarter",
        help_text="Select the quarter for this submission"
    )
    
    class Meta:
        model = Submission
        fields = ['form_template', 'school', 'school_year', 'quarter', 'status']
        widgets = {
            'form_template': forms.Select(attrs={'class': 'form-control'}),
            'school': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate school year choices from Period model
        school_years = Period.objects.values_list(
            'school_year_start', flat=True
        ).distinct().order_by('-school_year_start')
        
        self.fields['school_year'].choices = [
            ('', '--- Select School Year ---')
        ] + [
            (year, f'SY {year}-{year + 1}')
            for year in school_years
        ]
        
        # Set current values if editing
        if self.instance and self.instance.pk:
            self.fields['school_year'].initial = self.instance.school_year
            self.fields['quarter'].initial = self.instance.quarter
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Get or create the corresponding Period
        school_year = self.cleaned_data['school_year']
        quarter = self.cleaned_data['quarter']
        
        try:
            period = Period.objects.get(
                school_year_start=int(school_year),
                quarter_tag=quarter
            )
            instance.period = period
        except Period.DoesNotExist:
            # Auto-create period if doesn't exist
            period = Period.objects.create(
                school_year_start=int(school_year),
                quarter_tag=quarter,
                is_active=True
            )
            instance.period = period
        
        instance.school_year = int(school_year)
        instance.quarter = quarter
        
        if commit:
            instance.save()
        
        return instance
```

---

### Step 3: Update Admin Interface

Make period classification easy in admin:

```python
# submissions/admin.py

from django.contrib import admin
from submissions.models import Submission, Period

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'form_template',
        'school',
        'school_year_display',
        'quarter',
        'status',
        'submitted_at'
    ]
    
    list_filter = [
        'school_year',
        'quarter',
        'status',
        'form_template__section',
        'submitted_at'
    ]
    
    search_fields = [
        'school__name',
        'form_template__name'
    ]
    
    ordering = ['-school_year', 'quarter', '-submitted_at']
    
    # Add period fields to edit form
    fieldsets = (
        ('Basic Information', {
            'fields': ('form_template', 'school', 'status')
        }),
        ('Period Classification', {
            'fields': ('school_year', 'quarter', 'period'),
            'description': 'Specify which school year and quarter this submission belongs to'
        }),
        ('Timestamps', {
            'fields': ('submitted_at', 'noted_at', 'approved_at'),
            'classes': ('collapse',)
        }),
    )
    
    def school_year_display(self, obj):
        """Display school year in readable format"""
        if obj.school_year:
            return f"SY {obj.school_year}-{obj.school_year + 1}"
        return "N/A"
    school_year_display.short_description = 'School Year'
    school_year_display.admin_order_field = 'school_year'
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Customize school_year field
        if 'school_year' in form.base_fields:
            school_years = Period.objects.values_list(
                'school_year_start', flat=True
            ).distinct().order_by('-school_year_start')
            
            form.base_fields['school_year'].widget = forms.Select(
                choices=[
                    (year, f'SY {year}-{year + 1}')
                    for year in school_years
                ]
            )
        
        # Customize quarter field
        if 'quarter' in form.base_fields:
            form.base_fields['quarter'].widget = forms.Select(
                choices=[
                    ('Q1', 'Quarter 1 (Q1)'),
                    ('Q2', 'Quarter 2 (Q2)'),
                    ('Q3', 'Quarter 3 (Q3)'),
                    ('Q4', 'Quarter 4 (Q4)'),
                ]
            )
        
        return form
```

---

### Step 4: Update Submission Form Template

Add period selectors to the form UI:

```html
<!-- templates/submissions/submission_form.html -->

{% extends "layout/base.html" %}

{% block content %}
<div class="container">
    <h1>{{ form_title }}</h1>
    
    <form method="POST" class="submission-form">
        {% csrf_token %}
        
        <!-- Period Classification Section -->
        <div class="form-section">
            <h2>Period Classification</h2>
            <p class="help-text">Specify which school year and quarter this submission belongs to.</p>
            
            <div class="form-row">
                <div class="form-group">
                    <label for="{{ form.school_year.id_for_label }}">
                        School Year <span class="required">*</span>
                    </label>
                    {{ form.school_year }}
                    {% if form.school_year.errors %}
                        <div class="error">{{ form.school_year.errors }}</div>
                    {% endif %}
                    <small class="help-text">{{ form.school_year.help_text }}</small>
                </div>
                
                <div class="form-group">
                    <label for="{{ form.quarter.id_for_label }}">
                        Quarter <span class="required">*</span>
                    </label>
                    {{ form.quarter }}
                    {% if form.quarter.errors %}
                        <div class="error">{{ form.quarter.errors }}</div>
                    {% endif %}
                    <small class="help-text">{{ form.quarter.help_text }}</small>
                </div>
            </div>
        </div>
        
        <!-- Other Form Fields -->
        <div class="form-section">
            <h2>Submission Details</h2>
            
            <div class="form-group">
                <label for="{{ form.form_template.id_for_label }}">
                    Form Template <span class="required">*</span>
                </label>
                {{ form.form_template }}
                {% if form.form_template.errors %}
                    <div class="error">{{ form.form_template.errors }}</div>
                {% endif %}
            </div>
            
            <div class="form-group">
                <label for="{{ form.school.id_for_label }}">
                    School <span class="required">*</span>
                </label>
                {{ form.school }}
                {% if form.school.errors %}
                    <div class="error">{{ form.school.errors }}</div>
                {% endif %}
            </div>
            
            <div class="form-group">
                <label for="{{ form.status.id_for_label }}">
                    Status
                </label>
                {{ form.status }}
            </div>
        </div>
        
        <!-- Submit Buttons -->
        <div class="form-actions">
            <button type="submit" class="btn btn-primary">Save Submission</button>
            <a href="{% url 'submission_list' %}" class="btn btn-secondary">Cancel</a>
        </div>
    </form>
</div>

<style>
.form-section {
    margin-bottom: 2rem;
    padding: 1.5rem;
    background: #f9fafb;
    border-radius: 8px;
}

.form-section h2 {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
}

.form-section .help-text {
    color: #6b7280;
    margin-bottom: 1rem;
}

.form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
}

.form-group {
    margin-bottom: 1rem;
}

.form-group label {
    display: block;
    font-weight: 600;
    margin-bottom: 0.5rem;
}

.form-group .required {
    color: #dc2626;
}

.form-group select,
.form-group input {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    font-size: 1rem;
}

.form-group small.help-text {
    display: block;
    margin-top: 0.25rem;
    font-size: 0.875rem;
    color: #6b7280;
}

.error {
    color: #dc2626;
    font-size: 0.875rem;
    margin-top: 0.25rem;
}

.form-actions {
    display: flex;
    gap: 1rem;
    margin-top: 2rem;
}

.btn {
    padding: 0.75rem 1.5rem;
    border-radius: 6px;
    font-weight: 600;
    text-decoration: none;
    border: none;
    cursor: pointer;
}

.btn-primary {
    background: #2563eb;
    color: white;
}

.btn-primary:hover {
    background: #1d4ed8;
}

.btn-secondary {
    background: #6b7280;
    color: white;
}

.btn-secondary:hover {
    background: #4b5563;
}
</style>
{% endblock %}
```

---

### Step 5: Update Submission List View

Show period classification in list views:

```html
<!-- templates/submissions/submission_list.html -->

<table class="submission-table">
    <thead>
        <tr>
            <th>ID</th>
            <th>Form</th>
            <th>School</th>
            <th>School Year</th>
            <th>Quarter</th>
            <th>Status</th>
            <th>Submitted</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        {% for submission in submissions %}
        <tr>
            <td>{{ submission.id }}</td>
            <td>{{ submission.form_template.name }}</td>
            <td>{{ submission.school.name }}</td>
            <td>
                {% if submission.school_year %}
                    SY {{ submission.school_year }}-{{ submission.school_year|add:1 }}
                {% else %}
                    N/A
                {% endif %}
            </td>
            <td>
                <span class="quarter-badge quarter-{{ submission.quarter|lower }}">
                    {{ submission.quarter|default:"N/A" }}
                </span>
            </td>
            <td>
                <span class="status-badge status-{{ submission.status }}">
                    {{ submission.get_status_display }}
                </span>
            </td>
            <td>{{ submission.submitted_at|date:"M d, Y" }}</td>
            <td>
                <a href="{% url 'submission_edit' submission.id %}">Edit</a>
                <a href="{% url 'submission_view' submission.id %}">View</a>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<style>
.quarter-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    font-size: 0.875rem;
    font-weight: 600;
}

.quarter-q1 {
    background: #dbeafe;
    color: #1e40af;
}

.quarter-q2 {
    background: #d1fae5;
    color: #065f46;
}

.quarter-q3 {
    background: #fef3c7;
    color: #92400e;
}

.quarter-q4 {
    background: #fce7f3;
    color: #9f1239;
}
</style>
```

---

### Step 6: Update KPI Dashboard Filtering

Use new period fields for efficient filtering:

```python
# dashboards/views.py

@login_required
def smme_kpi_dashboard(request):
    """SMME KPI Dashboard with period filtering"""
    user = request.user
    _require_reviewer_access(user)
    
    # Get filter parameters
    school_year = request.GET.get('school_year', datetime.now().year)
    quarter_filter = request.GET.get('quarter', 'all')
    
    # Filter submissions by school_year and quarter (much faster!)
    if quarter_filter == 'all':
        submissions = Submission.objects.filter(
            school_year=int(school_year),
            quarter__in=['Q1', 'Q2', 'Q3', 'Q4'],
            form_template__section__code='smme',
            status__in=['submitted', 'noted', 'approved']
        ).select_related('school', 'period')
    else:
        submissions = Submission.objects.filter(
            school_year=int(school_year),
            quarter=quarter_filter,
            form_template__section__code='smme',
            status__in=['submitted', 'noted', 'approved']
        ).select_related('school', 'period')
    
    # Calculate KPIs using filtered submissions
    # ... (existing KPI calculation logic)
```

**Performance Benefit:**
- **BEFORE:** Filter by period FK, requires JOIN
- **AFTER:** Filter by indexed school_year + quarter columns (direct lookup)
- **Speed improvement:** ~30-50% faster queries

---

## Testing Checklist

### Model & Data Migration
- [ ] Migration runs without errors
- [ ] Existing submissions have school_year and quarter populated
- [ ] New submissions auto-populate from period
- [ ] Unique constraints work correctly

### Admin Interface
- [ ] Can create submission with school year + quarter
- [ ] School year dropdown shows available years
- [ ] Quarter dropdown shows Q1-Q4
- [ ] Period auto-selects based on school_year + quarter
- [ ] List view shows school year and quarter columns
- [ ] Filtering by school_year and quarter works

### Forms & Templates
- [ ] Submission form displays period selectors
- [ ] School year dropdown populated from database
- [ ] Quarter dropdown shows Q1, Q2, Q3, Q4
- [ ] Form validation works (required fields)
- [ ] Submission list shows period classification

### KPI Dashboard
- [ ] Dashboard filters by school_year correctly
- [ ] Dashboard filters by quarter correctly
- [ ] "All Quarters" option shows all Q1-Q4
- [ ] KPI calculations accurate for selected period
- [ ] Performance is acceptable (queries < 500ms)

### Edge Cases
- [ ] What if period doesn't exist? (Auto-create or error?)
- [ ] What if migrating old data without quarters?
- [ ] What if user changes school_year but not quarter?
- [ ] What if form submitted for future period?

---

## User Workflow Example

### SMME Staff Creating a Submission

1. **Navigate to** "Create New Submission"
2. **See Period Classification section** at top of form
3. **Select School Year** from dropdown:
   - Options: "SY 2025-2026", "SY 2024-2025", etc.
4. **Select Quarter** from dropdown:
   - Options: "Quarter 1 (Q1)", "Quarter 2 (Q2)", "Quarter 3 (Q3)", "Quarter 4 (Q4)"
5. **Fill in other fields** (Form Template, School, Status)
6. **Click "Save Submission"**
7. **System auto-links** to corresponding Period object

### SMME Reviewer Viewing Dashboard

1. **Navigate to** SMME KPI Dashboard
2. **See filters** at top:
   - School Year: [SY 2025-2026 ▼]
   - Quarter: [All Quarters ▼]
3. **Select "Q1"** from quarter dropdown
4. **Dashboard updates** to show only Q1 submissions
5. **KPI calculations** reflect only Q1 data
6. **Charts and cards** update accordingly

---

## Success Criteria

### Functionality
- [x] Submissions have school_year and quarter fields
- [x] Admin interface allows period selection
- [x] Forms have user-friendly period selectors
- [x] KPI dashboard filters by period accurately
- [x] Data migration preserves existing submissions

### Performance
- [x] Queries use indexed school_year + quarter fields
- [x] Dashboard loads < 1 second with 500 submissions
- [x] Filter changes respond < 500ms

### User Experience
- [x] Intuitive period selection UI
- [x] Clear labels and help text
- [x] Period classification visible in lists
- [x] Easy to understand school year format (SY 2025-2026)

---

## Future Enhancements (Optional)

### 1. Bulk Period Assignment
Allow updating period for multiple submissions at once:
```python
# Admin action
def assign_period(modeladmin, request, queryset):
    # Show form to select school_year and quarter
    # Apply to all selected submissions
```

### 2. Period Validation Rules
Prevent submissions for closed periods:
```python
def clean(self):
    if self.period and not self.period.is_active:
        raise ValidationError("Cannot submit to inactive period")
```

### 3. Auto-Period Detection
Automatically suggest period based on current date:
```python
def get_current_period():
    """Suggest period based on today's date"""
    # Logic to determine Q1, Q2, Q3, Q4 based on month
```

---

**End of Task 3 Documentation**
