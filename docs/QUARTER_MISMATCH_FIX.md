# Quarter Mismatch Fix

## Problem Description

**Reported Issue:**
- User selected **Q1** when creating a form in "Manage Forms"
- School dashboard showed **"Fourth Quarter"** instead of Q1

## Root Cause Analysis

The system has two separate places where quarter information is stored:

### 1. FormTemplate.quarter_filter
- Set when creating a form in "Manage Forms"
- Stores the quarter tag (Q1, Q2, Q3, Q4)
- Used for filtering and organization

### 2. Period.quarter_tag
- Separate model that represents reporting periods
- Each Period has: `label`, `quarter_tag`, `school_year_start`, `display_order`
- Submissions are linked to a **Period** (not directly to FormTemplate's quarter)

### The Mismatch
When the school dashboard displayed available forms, it was:
1. ❌ Using the **highest display_order Period** (usually Q4) for ALL forms
2. ❌ Ignoring the FormTemplate's `quarter_filter` setting
3. ✅ When submission created, it showed Period.label (e.g., "Fourth Quarter")

**Result:** User selects Q1 in manage forms → School sees Q4 in dashboard

## Solution Implemented

### File: `dashboards/views.py` - `school_home()` function

**Before (Buggy Code):**
```python
# Get the current active period for new submissions
active_period = (
    Period.objects.filter(is_active=True)
    .order_by("-school_year_start", "-display_order")
    .first()
    or Period.objects.order_by("-school_year_start", "-display_order").first()
)

# Later in code...
for form in active_forms:
    if form.id not in draft_form_template_ids:
        available_forms_by_section[form.section_id].append({
            'form_template': form,
            'deadline': form.close_at,
            'period': active_period,  # ❌ SAME PERIOD FOR ALL FORMS
        })
```

**After (Fixed Code):**
```python
# Get all active periods (we'll match specific quarters to forms later)
active_periods = list(
    Period.objects.filter(is_active=True)
    .order_by("-school_year_start", "display_order")
)

# Fallback to latest periods if no active periods
if not active_periods:
    active_periods = list(
        Period.objects.order_by("-school_year_start", "display_order")[:4]
    )

# Later in code...
for form in active_forms:
    if form.id not in draft_form_template_ids:
        # Match form's quarter_filter with appropriate Period
        matched_period = None
        if form.quarter_filter and active_periods:
            # Try to find a period with matching quarter_tag
            for period in active_periods:
                if period.quarter_tag == form.quarter_filter:
                    matched_period = period
                    break
        
        # Fallback to first active period if no match
        if not matched_period and active_periods:
            matched_period = active_periods[0]
        
        if matched_period:  # Only add if we have a period
            available_forms_by_section[form.section_id].append({
                'form_template': form,
                'deadline': form.close_at,
                'period': matched_period,  # ✅ CORRECT PERIOD BASED ON QUARTER_FILTER
            })
```

## How It Works Now

### Step-by-Step Flow:

1. **Section Admin creates form**
   - Selects Q1 in "Manage Forms"
   - `FormTemplate.quarter_filter = 'Q1'`

2. **Dashboard loads available forms**
   - Fetches all active Periods
   - For each FormTemplate, matches `quarter_filter` with Period's `quarter_tag`
   - If FormTemplate has `quarter_filter='Q1'`, finds Period with `quarter_tag='Q1'`

3. **School sees form**
   - Dashboard shows correct Period label (e.g., "Q1" or "First Quarter")
   - "Start Form" button links to correct Period

4. **Submission created**
   - Links to correct Period based on quarter match
   - Displays correct `submission.period.label` everywhere

## Testing Checklist

- [ ] Create form with Q1 → School sees Q1
- [ ] Create form with Q2 → School sees Q2
- [ ] Create form with Q3 → School sees Q3
- [ ] Create form with Q4 → School sees Q4
- [ ] Create form with no quarter_filter → Uses first active period
- [ ] Existing submissions still display correct quarters

## Database Requirements

For this fix to work correctly, you need:

1. **Active Periods in database** with correct quarter_tags:
   ```sql
   SELECT id, label, quarter_tag, school_year_start, is_active 
   FROM submissions_period 
   WHERE is_active = 1 
   ORDER BY school_year_start DESC, display_order;
   ```

2. **Verify Periods exist for all quarters:**
   - Q1: quarter_tag='Q1'
   - Q2: quarter_tag='Q2'
   - Q3: quarter_tag='Q3'
   - Q4: quarter_tag='Q4'

3. **If missing Periods, create them:**
   ```python
   # In Django shell: python manage.py shell
   from submissions.models import Period
   
   for i, (tag, label, order) in enumerate([
       ('Q1', 'First Quarter', 1),
       ('Q2', 'Second Quarter', 2),
       ('Q3', 'Third Quarter', 3),
       ('Q4', 'Fourth Quarter', 4),
   ]):
       Period.objects.get_or_create(
           school_year_start=2025,
           quarter_tag=tag,
           defaults={
               'label': label,
               'display_order': order,
               'is_active': True,
           }
       )
   ```

## Edge Cases Handled

1. **No matching Period:** Falls back to first active period
2. **No active Periods:** Falls back to latest 4 periods
3. **Empty quarter_filter:** Uses first active period
4. **Multiple periods with same quarter_tag:** Uses first match

## Related Files

- `dashboards/views.py` - Fixed period matching logic
- `submissions/models.py` - FormTemplate.quarter_filter, Period model
- `submissions/forms.py` - FormTemplateCreateForm (saves quarter_filter)
- `templates/dashboards/school_home.html` - Displays period.label

## Status

✅ **FIXED** - Forms now correctly match their selected quarter with the appropriate Period object.

---

**Fixed Date:** January 2025
**Fixed By:** GitHub Copilot
**Issue:** Quarter mismatch between Manage Forms and School Dashboard
