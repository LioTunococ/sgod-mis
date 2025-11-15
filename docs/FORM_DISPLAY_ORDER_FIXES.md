# Form Display Order Fixes

## Changes Made

### 1. Percent Implementation Area Order ✅
**File:** `submissions/views.py` (lines ~571-582)

**Problem:** Areas were displayed in alphabetical order (access, enabling_mechanisms, equity, quality)

**Solution:** Added custom ordering using Django's `Case`/`When` to sort by correct sequence

**Order:**
1. Access
2. Quality
3. Equity
4. Enabling Mechanisms

```python
# Order PCT rows by correct sequence
pct_ordering = Case(
    When(area='access', then=Value(1)),
    When(area='quality', then=Value(2)),
    When(area='equity', then=Value(3)),
    When(area='enabling_mechanisms', then=Value(4)),
    output_field=IntegerField(),
)

pct_formset = Form1PctRowFormSet(
    queryset=header.rows.annotate(sort_order=pct_ordering).order_by("sort_order"),
    ...
)
```

---

### 2. CRLA Proficiency Level Order ✅
**File:** `submissions/views.py` (lines ~618-640)

**Problem:** CRLA levels displayed in alphabetical order (developing, high_emerging, low_emerging, transitioning)

**Solution:** Added custom ordering for CRLA assessment formset

**Order:**
1. Low Emerging
2. High Emerging
3. Developing
4. Transitioning

```python
# Custom ordering for CRLA levels
crla_ordering = Case(
    When(level='low_emerging', then=Value(1)),
    When(level='high_emerging', then=Value(2)),
    When(level='developing', then=Value(3)),
    When(level='transitioning', then=Value(4)),
    output_field=IntegerField(),
)

reading_crla_new_formset = ReadingAssessmentCRLAFormSet(
    queryset=ReadingAssessmentCRLA.objects.filter(...)
        .annotate(sort_order=crla_ordering).order_by("sort_order"),
    ...
)
```

---

### 3. PHILIRI Reading Level Order ✅
**File:** `submissions/views.py` (lines ~643-650)

**Problem:** PHILIRI levels displayed in alphabetical order (frustration, independent, instructional)

**Solution:** Added custom ordering for PHILIRI assessment formset

**Order:**
1. Frustration
2. Instructional
3. Independent

```python
# Custom ordering for PHILIRI levels
philiri_ordering = Case(
    When(level='frustration', then=Value(1)),
    When(level='instructional', then=Value(2)),
    When(level='independent', then=Value(3)),
    output_field=IntegerField(),
)

reading_philiri_new_formset = ReadingAssessmentPHILIRIFormSet(
    queryset=ReadingAssessmentPHILIRI.objects.filter(...)
        .annotate(sort_order=philiri_ordering).order_by("sort_order"),
    ...
)
```

---

## Technical Details

### Why the Issue Occurred
Django's `Meta.ordering = ["field_name"]` sorts by the **database field values** alphabetically, not by the desired display order. Since field values are slugs (e.g., "developing", "frustration"), they sorted incorrectly.

### Solution Approach
Used Django's `Case`/`When` expressions to create a custom `sort_order` annotation that assigns numeric values (1, 2, 3...) to each choice, then ordered by that annotation.

### Benefits
- ✅ No database migration required
- ✅ No model changes needed
- ✅ Preserves existing data
- ✅ Form displays in correct order
- ✅ Works with existing formsets

---

## Testing

**To verify:**
1. Navigate to **Percent Implementation** tab → Areas should show: Access, Quality, Equity, Enabling Mechanisms
2. Navigate to **Reading Assessment (CRLA)** tab → Levels should show: Low Emerging, High Emerging, Developing, Transitioning
3. Navigate to **Reading Assessment (PHILIRI)** tab → Levels should show: Frustration, Instructional, Independent

---

## Status
✅ **COMPLETE** - All three ordering issues fixed

**Date:** January 2025
**Files Modified:** `submissions/views.py`
