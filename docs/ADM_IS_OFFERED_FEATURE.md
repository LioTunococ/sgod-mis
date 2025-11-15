# ADM "Is Offered" Feature Implementation

**Date**: October 18, 2025  
**Feature**: Add checkbox to allow schools to indicate if they implement ADM programs  
**Status**: 🚧 IN PROGRESS

---

## Overview

Schools that do NOT implement ADM (Alternative Delivery Mode) programs should be able to check a box to indicate this, and all ADM fields will be greyed out/disabled, similar to how SLP works when a subject is not offered.

---

## Implementation Summary

### 1. ✅ Model Changes

**New Model**: `Form1ADMHeader`
```python
class Form1ADMHeader(models.Model):
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name="form1_adm_header")
    is_offered = models.BooleanField(
        default=True,
        verbose_name="School implements ADM",
        help_text="Check if your school implements ADM programs"
    )
```

**Updated Model**: `Form1ADMRow`
- Added verbose names to all fields
- Added `clean()` method to auto-clear data when `is_offered=False`

### 2. ✅ Migration Created
- Migration: `0014_adm_header_is_offered.py`
- Status: ✅ Applied

### 3. ✅ Forms Created
- `Form1ADMHeaderForm` - Checkbox for is_offered
- Updated `Form1ADMRowForm` - Added `adm-field` class to all widgets

### 4. ✅ Admin Registered
- `Form1ADMHeaderAdmin` - Shows is_offered status

### 5. ⏳ Views Update (PENDING)

Need to update `edit_submission` view in `submissions/views.py`:

**Location**: Around line 653

**Changes Needed**:
1. Import `Form1ADMHeader` and `Form1ADMHeaderForm`
2. Create/get ADM header instance
3. Create ADM header form
4. Handle ADM header form submission
5. Pass ADM header form to template

**Code to Add**:
```python
# Around line 67 - Add import
from .models import (
    ...
    Form1ADMHeader,
    Form1ADMRow,
    ...
)

# Around line 38 - Add form import
from .forms import (
    ...
    Form1ADMHeaderForm,
    Form1ADMRowFormSet,
    ...
)

# Around line 240-242 - Update initialization (replace existing code)
# Create ADM header if it doesn't exist
if not hasattr(submission, 'form1_adm_header'):
    Form1ADMHeader.objects.create(submission=submission, is_offered=True)

# Create default ADM row if none exist
if not Form1ADMRow.objects.filter(submission=submission).exists():
    Form1ADMRow.objects.create(submission=submission)

# Around line 653 - Add ADM header form creation
adm_header_form = None
if current_tab == "adm":
    adm_header, _ = Form1ADMHeader.objects.get_or_create(
        submission=submission,
        defaults={'is_offered': True}
    )
    adm_header_form = Form1ADMHeaderForm(
        request.POST if request.method == "POST" else None,
        instance=adm_header,
        prefix="adm_header"
    )

# Around line 760 - Handle ADM header form submission
elif current_tab == "adm":
    if adm_header_form and adm_header_form.is_valid():
        adm_header_form.save()
    if adm_formset is not None and adm_formset.is_valid():
        adm_formset.save()

# Around line 804 - Pass to template
context = {
    ...
    "adm_header_form": adm_header_form,
    "adm_formset": adm_formset,
    ...
}
```

### 6. ⏳ Template Update (PENDING)

**File**: `templates/submissions/edit_submission.html`  
**Location**: Around line 843-875

**Changes Needed**:

```html
{% if current_tab == 'adm' %}
  <!-- ADM Header with is_offered checkbox -->
  <div class="section-card" style="margin-bottom: 1.5rem; background: #f0f9ff; border: 2px solid #3b82f6;">
    <div style="display: flex; align-items: center; gap: 1rem;">
      <div style="font-size: 1.5rem;">📋</div>
      <div style="flex: 1;">
        <h3 style="margin: 0; color: #1e40af;">ADM (Alternative Delivery Mode)</h3>
        <p class="muted" style="margin: 0.5rem 0 0 0; font-size: 0.875rem;">
          Summarize Alternative Delivery Mode implementation for the quarter
        </p>
      </div>
    </div>
    
    {% if adm_header_form %}
      <div style="margin-top: 1rem; padding: 1rem; background: white; border-radius: 0.5rem; border: 1px solid #e5e7eb;">
        <label style="display: flex; align-items: center; gap: 0.75rem; cursor: pointer; font-weight: 500;">
          {{ adm_header_form.is_offered }}
          <span>{{ adm_header_form.is_offered.label }}</span>
        </label>
        <p class="field-note" style="margin: 0.5rem 0 0 2rem; font-size: 0.875rem; color: #6b7280;">
          {{ adm_header_form.is_offered.help_text }}
        </p>
      </div>
    {% endif %}
  </div>

  <!-- ADM Formset (will be greyed out if not offered) -->
  {% if adm_formset %}
    <div id="adm-fields-container" class="adm-container">
      {{ adm_formset.management_form }}
      
      {% for form in adm_formset %}
        {{ form.id }}
        <div class="card adm-field-group">
          <h3>ADM Record {% if adm_formset|length > 1 %}#{{ forloop.counter }}{% endif %}</h3>
          <span class="field-note">Mirror the ADM monitoring sheet: provide actual counts and qualitative notes.</span>
          
          <label>PPAS Conducted {{ form.ppas_conducted }}</label>
          
          <div class="grid-two">
            <label>Physical Target {{ form.ppas_physical_target }}</label>
            <label>Physical Actual {{ form.ppas_physical_actual }}</label>
            <label>Physical % {{ form.ppas_physical_percent }}</label>
          </div>
          
          <div class="grid-two">
            <label>Funds Downloaded {{ form.funds_downloaded }}</label>
            <label>Funds Obligated {{ form.funds_obligated }}</label>
            <label>Funds Unobligated {{ form.funds_unobligated }}</label>
            <label>% Obligated {{ form.funds_percent_obligated }}</label>
            <label>Burn Rate % {{ form.funds_percent_burn_rate }}</label>
          </div>
          
          <h4 style="margin-top: 1.5rem; color: #1f2937;">Analysis Questions</h4>
          <label>1. What were those factors that had helped you facilitate your PPAs? {{ form.q1_response }}</label>
          <label>2. Do all your PPA's really address what it intends to address? {{ form.q2_response }}</label>
          <label>3. What PPAs/Best practice do you intend to sustain or enhance? Why? {{ form.q3_response }}</label>
          <label>4. What PPAs do you intend to drop or improved? Why? {{ form.q4_response }}</label>
          <label>5. Overall, how significant is ADM implementation in your school? {{ form.q5_response }}</label>
          
          {% if adm_formset.can_delete %}
            <div class="delete-field">Remove {{ form.DELETE }}</div>
          {% endif %}
        </div>
      {% endfor %}
    </div>
  {% endif %}
  
  <!-- JavaScript to toggle ADM fields -->
  <script>
    function toggleADMFields(isOffered) {
      const container = document.getElementById('adm-fields-container');
      const admFields = document.querySelectorAll('.adm-field');
      
      if (!isOffered) {
        // Grey out and disable all ADM fields
        if (container) {
          container.style.opacity = '0.5';
          container.style.pointerEvents = 'none';
        }
        admFields.forEach(field => {
          field.disabled = true;
          field.style.backgroundColor = '#f3f4f6';
        });
      } else {
        // Enable all ADM fields
        if (container) {
          container.style.opacity = '1';
          container.style.pointerEvents = 'auto';
        }
        admFields.forEach(field => {
          field.disabled = false;
          field.style.backgroundColor = '';
        });
      }
    }
    
    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
      const checkbox = document.querySelector('.adm-offered-checkbox');
      if (checkbox) {
        toggleADMFields(checkbox.checked);
      }
    });
  </script>
{% endif %}
```

### 7. ⏳ Review Template Update (PENDING)

**File**: `templates/submissions/review_tabs.html`  
**Location**: Around line 455-485

**Add check for is_offered**:

```html
{% elif current_tab == 'adm' %}
  <div class="section">
    <h3>ADM One-Stop-Shop & EiE</h3>
    
    {% if submission.form1_adm_header and not submission.form1_adm_header.is_offered %}
      <div style="padding: 2rem; background: #f9fafb; border: 1px dashed #d1d5db; border-radius: 0.5rem; text-align: center;">
        <p style="color: #6b7280; font-size: 1rem;">
          ℹ️ This school does not implement ADM (Alternative Delivery Mode) programs
        </p>
      </div>
    {% elif adm_rows %}
      {% for row in adm_rows %}
        <div class="data-section">
          <p><strong>PPAS Conducted:</strong> {{ row.ppas_conducted|linebreaksbr|default:'-' }}</p>
          ...
        </div>
      {% endfor %}
    {% else %}
      <p class="muted">No ADM records submitted.</p>
    {% endif %}
  </div>
{% endif %}
```

---

## Testing Checklist

- [ ] Checkbox appears at top of ADM section
- [ ] Checking/unchecking toggles field states
- [ ] Fields are greyed out when unchecked
- [ ] Fields are enabled when checked
- [ ] Data is saved correctly
- [ ] Review page shows "not offered" message
- [ ] Form submission works with ADM not offered
- [ ] Form submission works with ADM offered

---

## Files Modified

1. ✅ `submissions/models.py` - Added Form1ADMHeader model
2. ✅ `submissions/forms.py` - Added Form1ADMHeaderForm
3. ✅ `submissions/admin.py` - Registered Form1ADMHeader
4. ✅ `migrations/0014_adm_header_is_offered.py` - Migration
5. ⏳ `submissions/views.py` - Need to add header form handling
6. ⏳ `templates/submissions/edit_submission.html` - Need to add checkbox UI
7. ⏳ `templates/submissions/review_tabs.html` - Need to add not-offered message

---

**Status**: Models and forms ready. Need to update views and templates.

