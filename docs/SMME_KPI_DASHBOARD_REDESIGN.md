# SMME KPI Dashboard - Complete Redesign Plan

**Date**: October 18, 2025  
**Goal**: Simplified, table-based KPI dashboard with proper filters and accurate metrics  
**Approach**: One comprehensive table per SMEA Form 1 section with appropriate filters

---

## Executive Summary

The current SMME KPI Dashboard will be completely redesigned into a **simple, table-based interface** with proper filtering options. Each section of SMEA Form 1 will have its own dedicated view with relevant KPIs and filters.

### Key Changes
- ❌ Remove complex visualizations and confusing aggregations
- ✅ Simple HTML tables with clear headers
- ✅ Proper filters for each section (District, School Year, Quarter, Division, School)
- ✅ **CORRECTED RMA KPIs** (proficiency levels, not percentage bands)
- ✅ Export to Excel functionality

---

## SMEA Form 1 Structure Analysis

### Part 1: Percentage of Implementation & Action Points (PCT)
**Model**: `Form1PctRow`  
**KPIs**: Percentage of implementation for each action area

| Action Area | KPI Metric |
|-------------|------------|
| **Access** | % Implementation (0-100%) |
| **Quality** | % Implementation (0-100%) |
| **Equity** | % Implementation (0-100%) |
| **Enabling Mechanisms** | % Implementation (0-100%) |

**Filters Needed**:
- School Year
- Quarter (Q1, Q2, Q3, Q4)
- District
- Division/Section
- School (optional)

---

### Part 2: School Level of Proficiency (SLP)
**Model**: `Form1SLPRow`  
**KPIs**: Distribution of learners across proficiency levels **per subject**

| Grade | Subject | Proficiency Level | Count | Percentage |
|-------|---------|-------------------|-------|------------|
| Grade 1 | Mathematics | DNME | 10 | 10% |
| Grade 1 | Mathematics | Fairly Satisfactory | 20 | 20% |
| Grade 1 | Mathematics | Satisfactory | 30 | 30% |
| Grade 1 | Mathematics | Very Satisfactory | 25 | 25% |
| Grade 1 | Mathematics | Outstanding | 15 | 15% |

**Proficiency Levels**:
1. **DNME** - Did Not Meet Expectations
2. **FS** - Fairly Satisfactory
3. **S** - Satisfactory
4. **VS** - Very Satisfactory
5. **O** - Outstanding

**Filters Needed**:
- School Year
- Quarter
- District
- Division/Section
- School
- **Proficiency Level** (DNME, FS, S, VS, O)
- **Subject** (dropdown with all subjects)
- **Grade Level** (K-12)

**Views**:
1. **By Proficiency Level** - Filter by specific proficiency (e.g., all DNME across subjects/grades)
2. **By Subject** - Filter by specific subject (e.g., Mathematics across all grades)
3. **By Grade** - Filter by grade level (e.g., Grade 1 all subjects)

---

### Part 3: Reading Assessment - CRLA
**Model**: `Form1ReadingCRLA` (old model, still in use)  
**KPIs**: Distribution across CRLA proficiency bands

| Grade | Timing | Subject | Proficiency Band | Count |
|-------|--------|---------|------------------|-------|
| Grade 1 | BOSY | Mother Tongue | Low Emerging | 15 |
| Grade 1 | BOSY | Mother Tongue | High Emerging | 25 |
| Grade 1 | BOSY | Mother Tongue | Developing | 30 |
| Grade 1 | BOSY | Mother Tongue | Transitioning | 20 |

**Proficiency Bands** (CRLA):
1. **Low Emerging** - Frustration level
2. **High Emerging** - Early instructional
3. **Developing** - Instructional level
4. **Transitioning** - Approaching independent

**Filters Needed**:
- School Year
- **Assessment Timing** (BOSY, MOSY, EOSY)
- District
- School
- **Grade Level** (1-6)
- **Subject** (Mother Tongue, Filipino, English)
- **Proficiency Band**

---

### Part 4: Reading Assessment - PHILIRI
**Model**: `Form1ReadingPHILIRI`  
**KPIs**: Distribution across PHILIRI reading bands

| Grade | Timing | Language | Band 4-7 | Band 5-8 | Band 6-9 | Band 10 |
|-------|--------|----------|----------|----------|----------|---------|
| Grade 1 | BOSY | English | 10 | 20 | 30 | 5 |

**Reading Bands** (PHILIRI):
1. **Band 4-7** - Frustration
2. **Band 5-8** - Instructional (lower)
3. **Band 6-9** - Instructional (higher)
4. **Band 10** - Independent

**Filters Needed**:
- School Year
- **Assessment Timing** (BOSY, MOSY, EOSY)
- District
- School
- **Grade Level** (1-6)
- **Language** (English, Filipino, Ilokano, Others)

---

### Part 5: Reading and Mathematics Assessment (RMA)
**Model**: `Form1RMARow`  
**KPIs**: ⚠️ **CORRECTED** - Proficiency levels, NOT percentage bands

| Grade | Proficiency Level | Count | Percentage |
|-------|-------------------|-------|------------|
| Grade 1 | Emerging - Not Proficient (below 25%) | 15 | 15% |
| Grade 1 | Emerging - Low Proficient (25%-49%) | 20 | 20% |
| Grade 1 | Developing - Nearly Proficient (50%-74%) | 25 | 25% |
| Grade 1 | Transitioning - Proficient (75%-84%) | 30 | 30% |
| Grade 1 | At Grade Level (above 85%) | 10 | 10% |

**CORRECTED Proficiency Levels** (RMA):
1. **Emerging - Not Proficient** - Below 25%
2. **Emerging - Low Proficient** - 25%-49%
3. **Developing - Nearly Proficient** - 50%-74%
4. **Transitioning - Proficient** - 75%-84%
5. **At Grade Level** - Above 85%

**Current (WRONG) Implementation**:
- `band_below_75` - ❌ Wrong metric
- `band_75_79` - ❌ Wrong metric
- `band_80_84` - ❌ Wrong metric
- `band_85_89` - ❌ Wrong metric
- `band_90_100` - ❌ Wrong metric

**Required Model Changes**:
```python
class Form1RMARow(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="form1_rma_rows")
    grade_label = models.CharField(max_length=8, choices=smea_constants.RMAGradeLabel.CHOICES)
    enrolment = models.PositiveIntegerField()
    
    # CORRECTED fields
    emerging_not_proficient = models.PositiveIntegerField(default=0, help_text="Below 25%")
    emerging_low_proficient = models.PositiveIntegerField(default=0, help_text="25%-49%")
    developing_nearly_proficient = models.PositiveIntegerField(default=0, help_text="50%-74%")
    transitioning_proficient = models.PositiveIntegerField(default=0, help_text="75%-84%")
    at_grade_level = models.PositiveIntegerField(default=0, help_text="Above 85%")
```

**Filters Needed**:
- School Year
- Quarter
- District
- School
- **Grade Level** (K-6)
- **Proficiency Level**

---

## Dashboard Design

### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│                     SMME KPI DASHBOARD                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  [Tab: PCT Implementation] [Tab: SLP] [Tab: CRLA]            │
│  [Tab: PHILIRI] [Tab: RMA]                                   │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│  FILTERS (dynamic based on selected tab)                     │
│  ┌────────────┬────────────┬────────────┬────────────┐     │
│  │ District   │ School Year│ Quarter    │ School      │     │
│  │ [All    ▼] │ [2025-2026▼]│ [All    ▼] │ [All     ▼]│     │
│  └────────────┴────────────┴────────────┴────────────┘     │
│  ┌────────────┬────────────┐                                │
│  │ Grade      │ Subject    │  (SLP/CRLA only)               │
│  │ [All    ▼] │ [All    ▼] │                                │
│  └────────────┴────────────┘                                │
│                                                               │
│  [Apply Filters] [Clear] [Export to Excel]                  │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│  RESULTS TABLE                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ School │ District │ Quarter │ KPI Metric │ Value     │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ School A│ District 1│ Q1     │ Access %  │ 85%       │  │
│  │ School A│ District 1│ Q1     │ Quality % │ 78%       │  │
│  │ School B│ District 1│ Q1     │ Access %  │ 92%       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  Showing 1-50 of 250 results                                 │
│  [< Previous] [1] [2] [3] [4] [5] [Next >]                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Tab 1: PCT Implementation

### Table Columns
| School | District | School Year | Quarter | Access % | Quality % | Equity % | Enabling Mech % | Average % |
|--------|----------|-------------|---------|----------|-----------|----------|-----------------|-----------|
| ABC Elementary | District 1 | 2025-2026 | Q1 | 85% | 78% | 90% | 82% | 83.75% |

### Filters
- District (dropdown: All, District 1, District 2, ...)
- School Year (dropdown: 2024-2025, 2025-2026, ...)
- Quarter (dropdown: All, Q1, Q2, Q3, Q4)
- Division/Section (dropdown: All, SMME, Division, ...)
- School (dropdown: All, School A, School B, ..., or search box)

### SQL Query Logic
```sql
SELECT 
    s.name AS school_name,
    d.name AS district_name,
    p.label AS period_label,
    sub.school_year_start,
    MAX(CASE WHEN pct.area = 'access' THEN pct.percent END) AS access_pct,
    MAX(CASE WHEN pct.area = 'quality' THEN pct.percent END) AS quality_pct,
    MAX(CASE WHEN pct.area = 'equity' THEN pct.percent END) AS equity_pct,
    MAX(CASE WHEN pct.area = 'enabling_mechanisms' THEN pct.percent END) AS enabling_pct,
    AVG(pct.percent) AS average_pct
FROM submissions_form1pctrow pct
JOIN submissions_form1pctheader h ON pct.header_id = h.id
JOIN submissions_submission sub ON h.submission_id = sub.id
JOIN organizations_school s ON sub.school_id = s.id
JOIN organizations_district d ON s.district_id = d.id
JOIN submissions_period p ON sub.period_id = p.id
WHERE sub.status = 'submitted'
  AND (:district_id IS NULL OR s.district_id = :district_id)
  AND (:school_year IS NULL OR p.school_year_start = :school_year)
  AND (:quarter IS NULL OR p.quarter_tag = :quarter)
  AND (:school_id IS NULL OR s.id = :school_id)
GROUP BY s.id, d.id, p.id, sub.school_year_start
ORDER BY d.name, s.name, p.display_order
```

---

## Tab 2: School Level of Proficiency (SLP)

### Table Columns
| School | District | Quarter | Grade | Subject | DNME | FS | S | VS | O | Total | DNME % | FS % | S % | VS % | O % |
|--------|----------|---------|-------|---------|------|----|----|----|----|-------|--------|------|-----|------|-----|
| ABC Elem | Dist 1 | Q1 | Grade 1 | Mathematics | 10 | 20 | 30 | 25 | 15 | 100 | 10% | 20% | 30% | 25% | 15% |

### Filters
- District
- School Year
- Quarter
- School
- **Grade Level** (All, K, 1, 2, 3, ..., 12)
- **Subject** (All, Mathematics, English, Science, ...)
- **Proficiency Focus** (All, DNME, FS, S, VS, O) - Highlights specific column

### View Options
1. **Aggregated View** - One row per school/grade/subject
2. **Proficiency-Focused View** - Only show selected proficiency level
   - Example: Select "DNME" → Shows only DNME counts and percentages

### SQL Query Logic
```sql
SELECT 
    s.name AS school_name,
    d.name AS district_name,
    p.label AS period_label,
    slp.grade_label,
    slp.subject,
    SUM(slp.enrolment) AS total_enrolment,
    SUM(slp.dnme) AS dnme_count,
    SUM(slp.fs) AS fs_count,
    SUM(slp.s) AS s_count,
    SUM(slp.vs) AS vs_count,
    SUM(slp.o) AS o_count,
    ROUND(SUM(slp.dnme) * 100.0 / NULLIF(SUM(slp.enrolment), 0), 2) AS dnme_pct,
    ROUND(SUM(slp.fs) * 100.0 / NULLIF(SUM(slp.enrolment), 0), 2) AS fs_pct,
    ROUND(SUM(slp.s) * 100.0 / NULLIF(SUM(slp.enrolment), 0), 2) AS s_pct,
    ROUND(SUM(slp.vs) * 100.0 / NULLIF(SUM(slp.enrolment), 0), 2) AS vs_pct,
    ROUND(SUM(slp.o) * 100.0 / NULLIF(SUM(slp.enrolment), 0), 2) AS o_pct
FROM submissions_form1slprow slp
JOIN submissions_submission sub ON slp.submission_id = sub.id
JOIN organizations_school s ON sub.school_id = s.id
JOIN organizations_district d ON s.district_id = d.id
JOIN submissions_period p ON sub.period_id = p.id
WHERE sub.status = 'submitted'
  AND (:district_id IS NULL OR s.district_id = :district_id)
  AND (:school_year IS NULL OR p.school_year_start = :school_year)
  AND (:quarter IS NULL OR p.quarter_tag = :quarter)
  AND (:school_id IS NULL OR s.id = :school_id)
  AND (:grade IS NULL OR slp.grade_label = :grade)
  AND (:subject IS NULL OR slp.subject = :subject)
GROUP BY s.id, d.id, p.id, slp.grade_label, slp.subject
ORDER BY d.name, s.name, slp.grade_label, slp.subject
```

---

## Tab 3: Reading Assessment - CRLA

### Table Columns
| School | District | School Year | Timing | Grade | Subject | Low Emerging | High Emerging | Developing | Transitioning | Total |
|--------|----------|-------------|--------|-------|---------|--------------|---------------|------------|---------------|-------|
| ABC Elem | Dist 1 | 2025-2026 | BOSY | G1 | Mother Tongue | 15 | 25 | 30 | 20 | 90 |

### Filters
- District
- School Year
- **Assessment Timing** (BOSY, MOSY, EOSY)
- School
- **Grade Level** (1, 2, 3, 4, 5, 6)
- **Subject** (Mother Tongue, Filipino, English)

### SQL Query Logic
```sql
SELECT 
    s.name AS school_name,
    d.name AS district_name,
    p.school_year_start,
    crla.timing,
    crla.level AS grade,
    crla.subject,
    SUM(CASE WHEN crla.band = 'frustration' THEN crla.count ELSE 0 END) AS low_emerging,
    SUM(CASE WHEN crla.band = 'instructional' THEN crla.count ELSE 0 END) AS high_emerging,
    SUM(CASE WHEN crla.band = 'independent' THEN crla.count ELSE 0 END) AS developing,
    SUM(crla.count) AS total
FROM submissions_form1readingcrla crla
JOIN submissions_submission sub ON crla.submission_id = sub.id
JOIN organizations_school s ON sub.school_id = s.id
JOIN organizations_district d ON s.district_id = d.id
JOIN submissions_period p ON sub.period_id = p.id
WHERE sub.status = 'submitted'
  AND (:district_id IS NULL OR s.district_id = :district_id)
  AND (:school_year IS NULL OR p.school_year_start = :school_year)
  AND (:timing IS NULL OR crla.timing = :timing)
  AND (:school_id IS NULL OR s.id = :school_id)
  AND (:grade IS NULL OR crla.level = :grade)
  AND (:subject IS NULL OR crla.subject = :subject)
GROUP BY s.id, d.id, p.school_year_start, crla.timing, crla.level, crla.subject
ORDER BY d.name, s.name, crla.timing, crla.level, crla.subject
```

---

## Tab 4: Reading Assessment - PHILIRI

### Table Columns
| School | District | School Year | Timing | Grade | Language | Band 4-7 | Band 5-8 | Band 6-9 | Band 10 | Total |
|--------|----------|-------------|--------|-------|----------|----------|----------|----------|---------|-------|
| ABC Elem | Dist 1 | 2025-2026 | BOSY | G1 | English | 10 | 20 | 30 | 5 | 65 |

### Filters
- District
- School Year
- **Assessment Timing** (BOSY, MOSY, EOSY)
- School
- **Grade Level** (1-6)
- **Language** (English, Filipino, Ilokano, Others)

### SQL Query Logic
```sql
SELECT 
    s.name AS school_name,
    d.name AS district_name,
    p.school_year_start,
    phil.timing,
    phil.level AS grade,
    phil.language,
    SUM(phil.band_4_7) AS band_4_7,
    SUM(phil.band_5_8) AS band_5_8,
    SUM(phil.band_6_9) AS band_6_9,
    SUM(phil.band_10) AS band_10,
    SUM(phil.band_4_7 + phil.band_5_8 + phil.band_6_9 + phil.band_10) AS total
FROM submissions_form1readingphiliri phil
JOIN submissions_submission sub ON phil.submission_id = sub.id
JOIN organizations_school s ON sub.school_id = s.id
JOIN organizations_district d ON s.district_id = d.id
JOIN submissions_period p ON sub.period_id = p.id
WHERE sub.status = 'submitted'
  AND (:district_id IS NULL OR s.district_id = :district_id)
  AND (:school_year IS NULL OR p.school_year_start = :school_year)
  AND (:timing IS NULL OR phil.timing = :timing)
  AND (:school_id IS NULL OR s.id = :school_id)
  AND (:grade IS NULL OR phil.level = :grade)
  AND (:language IS NULL OR phil.language = :language)
GROUP BY s.id, d.id, p.school_year_start, phil.timing, phil.level, phil.language
ORDER BY d.name, s.name, phil.timing, phil.level, phil.language
```

---

## Tab 5: Reading and Mathematics Assessment (RMA)

### ⚠️ CRITICAL: Model Needs Migration

**Current (WRONG) Model Fields**:
```python
band_below_75 = models.PositiveIntegerField(default=0)
band_75_79 = models.PositiveIntegerField(default=0)
band_80_84 = models.PositiveIntegerField(default=0)
band_85_89 = models.PositiveIntegerField(default=0)
band_90_100 = models.PositiveIntegerField(default=0)
```

**Correct Model Fields** (Migration Required):
```python
emerging_not_proficient = models.PositiveIntegerField(default=0, help_text="Below 25%")
emerging_low_proficient = models.PositiveIntegerField(default=0, help_text="25%-49%")
developing_nearly_proficient = models.PositiveIntegerField(default=0, help_text="50%-74%")
transitioning_proficient = models.PositiveIntegerField(default=0, help_text="75%-84%")
at_grade_level = models.PositiveIntegerField(default=0, help_text="Above 85%")
```

### Table Columns
| School | District | Quarter | Grade | Not Prof (<25%) | Low Prof (25-49%) | Nearly Prof (50-74%) | Proficient (75-84%) | Grade Level (>85%) | Total |
|--------|----------|---------|-------|-----------------|-------------------|----------------------|---------------------|-------------------|-------|
| ABC Elem | Dist 1 | Q1 | K | 10 | 15 | 25 | 30 | 20 | 100 |

### Filters
- District
- School Year
- Quarter
- School
- **Grade Level** (K, 1, 2, 3, 4, 5, 6)

### SQL Query Logic (After Migration)
```sql
SELECT 
    s.name AS school_name,
    d.name AS district_name,
    p.label AS period_label,
    rma.grade_label,
    SUM(rma.enrolment) AS total_enrolment,
    SUM(rma.emerging_not_proficient) AS not_proficient,
    SUM(rma.emerging_low_proficient) AS low_proficient,
    SUM(rma.developing_nearly_proficient) AS nearly_proficient,
    SUM(rma.transitioning_proficient) AS proficient,
    SUM(rma.at_grade_level) AS grade_level,
    ROUND(SUM(rma.emerging_not_proficient) * 100.0 / NULLIF(SUM(rma.enrolment), 0), 2) AS not_prof_pct,
    ROUND(SUM(rma.emerging_low_proficient) * 100.0 / NULLIF(SUM(rma.enrolment), 0), 2) AS low_prof_pct,
    ROUND(SUM(rma.developing_nearly_proficient) * 100.0 / NULLIF(SUM(rma.enrolment), 0), 2) AS nearly_prof_pct,
    ROUND(SUM(rma.transitioning_proficient) * 100.0 / NULLIF(SUM(rma.enrolment), 0), 2) AS prof_pct,
    ROUND(SUM(rma.at_grade_level) * 100.0 / NULLIF(SUM(rma.enrolment), 0), 2) AS grade_level_pct
FROM submissions_form1rmarow rma
JOIN submissions_submission sub ON rma.submission_id = sub.id
JOIN organizations_school s ON sub.school_id = s.id
JOIN organizations_district d ON s.district_id = d.id
JOIN submissions_period p ON sub.period_id = p.id
WHERE sub.status = 'submitted'
  AND (:district_id IS NULL OR s.district_id = :district_id)
  AND (:school_year IS NULL OR p.school_year_start = :school_year)
  AND (:quarter IS NULL OR p.quarter_tag = :quarter)
  AND (:school_id IS NULL OR s.id = :school_id)
  AND (:grade IS NULL OR rma.grade_label = :grade)
GROUP BY s.id, d.id, p.id, rma.grade_label
ORDER BY d.name, s.name, rma.grade_label
```

---

## Implementation Plan

### Phase 1: RMA Model Migration (CRITICAL)
1. ✅ Create migration to rename RMA fields
2. ✅ Update form templates to use new field names
3. ✅ Update validation logic
4. ✅ Data migration (if existing data needs conversion)

### Phase 2: Backend Implementation
1. ✅ Create new view: `smme_kpi_dashboard_v2`
2. ✅ Create AJAX endpoints for each tab:
   - `/api/kpi/pct/`
   - `/api/kpi/slp/`
   - `/api/kpi/crla/`
   - `/api/kpi/philiri/`
   - `/api/kpi/rma/`
3. ✅ Implement filtering logic in view functions
4. ✅ Add pagination support (50 results per page)
5. ✅ Add Excel export functionality

### Phase 3: Frontend Implementation
1. ✅ Create new template: `smme_kpi_dashboard_v2.html`
2. ✅ Implement tab navigation
3. ✅ Build filter forms with dynamic dropdown population
4. ✅ Create results tables with sorting
5. ✅ Add AJAX calls for real-time filtering
6. ✅ Add loading indicators
7. ✅ Implement Excel export button

### Phase 4: Testing
1. ✅ Test each tab with various filter combinations
2. ✅ Verify KPI calculations are correct
3. ✅ Test Excel export
4. ✅ Performance testing with large datasets
5. ✅ User acceptance testing

### Phase 5: Deployment
1. ✅ Backup database
2. ✅ Run RMA migration
3. ✅ Deploy new dashboard
4. ✅ Update documentation
5. ✅ Train users on new interface

---

## File Structure

```
dashboards/
├── views.py              # Add new view functions
├── urls.py               # Add new URL routes
├── kpi_calculators.py    # Add KPI calculation functions
templates/dashboards/
├── smme_kpi_dashboard_v2.html    # Main dashboard template
├── kpi/
│   ├── pct_table.html           # PCT results table
│   ├── slp_table.html           # SLP results table
│   ├── crla_table.html          # CRLA results table
│   ├── philiri_table.html       # PHILIRI results table
│   └── rma_table.html           # RMA results table
static/
├── js/
│   └── kpi_dashboard.js         # AJAX filtering logic
└── css/
    └── kpi_dashboard.css        # Dashboard styling
submissions/
├── models.py            # Update Form1RMARow model
└── migrations/
    └── 0013_rma_proficiency_levels.py  # New migration
```

---

## URL Structure

```
/dashboards/smme-kpi-v2/                    # Main dashboard
/dashboards/smme-kpi-v2/pct/                # PCT tab (default)
/dashboards/smme-kpi-v2/slp/                # SLP tab
/dashboards/smme-kpi-v2/crla/               # CRLA tab
/dashboards/smme-kpi-v2/philiri/            # PHILIRI tab
/dashboards/smme-kpi-v2/rma/                # RMA tab

# AJAX API endpoints
/api/kpi/pct/data/                          # PCT data
/api/kpi/slp/data/                          # SLP data
/api/kpi/crla/data/                         # CRLA data
/api/kpi/philiri/data/                      # PHILIRI data
/api/kpi/rma/data/                          # RMA data

# Export endpoints
/dashboards/smme-kpi-v2/pct/export/         # Export PCT to Excel
/dashboards/smme-kpi-v2/slp/export/         # Export SLP to Excel
/dashboards/smme-kpi-v2/crla/export/        # Export CRLA to Excel
/dashboards/smme-kpi-v2/philiri/export/     # Export PHILIRI to Excel
/dashboards/smme-kpi-v2/rma/export/         # Export RMA to Excel
```

---

## Success Criteria

✅ **Simplicity**: Users can understand the dashboard without training  
✅ **Accuracy**: All KPIs match official SMEA Form 1 definitions  
✅ **Performance**: Dashboard loads in < 2 seconds  
✅ **Filtering**: All filters work correctly and intuitively  
✅ **Export**: Excel exports contain all visible data with proper formatting  
✅ **Mobile**: Dashboard is usable on tablets  
✅ **Accessibility**: Meets WCAG 2.1 AA standards  

---

## Next Steps

1. **Confirm design with stakeholders** ✅
2. **Create RMA migration** (high priority)
3. **Start backend implementation**
4. **Build frontend templates**
5. **User testing**

---

**Prepared by**: GitHub Copilot  
**Date**: October 18, 2025  
**Status**: Design Complete - Awaiting Approval
