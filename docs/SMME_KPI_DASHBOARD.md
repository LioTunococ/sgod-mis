# SMME KPI Dashboard

This dashboard provides district-aware school KPIs with filters, tabbed detail views, sorting, grouping, and CSV export.

## Views

- % Implementation
  - Columns: Overall, Access, Quality, Equity, Enabling Mechanisms
  - Computed from Form 1 Implementation section
- SLP (Subject-Level Performance)
  - Shows per-subject proficiency with DNME rates
  - Subject-level sorting: proficiency asc/desc, subject name
- Reading
  - CRLA (Low/High Emerging, Developing, Transitioning)
  - PHILIRI (Frustration, Instructional, Independent)
  - Timing filter: BOSY, MOSY, EOSY
- RMA
  - Bands: Not Proficient, Low, Nearly Proficient, Proficient, At Grade Level
  - Optional grade filter
- Instructional Supervision & TA
  - % Teachers with TA = (Teachers supervised/observed with TA) / (Total teachers)
- ADM One-Stop-Shop & EiE
  - Funding and PPAs summary (% Obligated, % Burn Rate)

## Filters

- School Year and Quarter (Q1–Q4); can be overridden by Form period selection
- Form Period (SMEA Form 1 instance) — when selected, it sets the School Year and Quarter context
- District and School
- School Level (Elementary/Secondary/Mixed)
- View-specific:
  - SLP: Subject, Grade-range (K–3, 4–6, 7–9, 10–12), Min enrollment, Has intervention
  - Reading: Type (CRLA/PHILIRI), Assessment Timing (BOSY/MOSY/EOSY)
  - RMA: Grade

## Sorting

- Default: School Name A→Z
- District: Groups by District then School; grouping headers appear in the UI
- View-specific metrics (e.g., SLP proficiency, Reading categories, RMA bands, % TA)
- Direction: Asc/Desc

## CSV Export

- Export reflects the current view, filters, and sorting

## Unified JSON API

Endpoint: `/dashboards/smme-kpi/api/`

Common query params:
- `kpi_part`: `all` (overview), `implementation`, `slp`, `reading`, `rma`, `supervision`
- `school_year`: 2025 (start year)
- `quarter`: `Q1|Q2|Q3|Q4|all`
- `form_period`: Period id (overrides school_year/quarter)
- `district`, `school`
- `sort_by`, `sort_dir`: `asc|desc`
- `page`, `page_size` (default 50, max 500)

View-specific params:
- SLP: `subject`, `grade_range` (k-3|4-6|7-9|10-12), `min_enrollment`, `has_intervention`
- Reading: `reading_type` (`crla|philiri`), `assessment_timing` (`bosy|mosy|eosy`)
- RMA: `rma_grade` (e.g., `g4`)

Example:
- Overview grouped by district:
  `/dashboards/smme-kpi/api/?kpi_part=all&school_year=2025&quarter=all&sort_by=district&sort_dir=asc&page=1&page_size=50`
- SLP subject proficiency (desc):
  `/dashboards/smme-kpi/api/?kpi_part=slp&school_year=2025&quarter=all&sort_by=subject_proficiency&sort_dir=desc`
- Reading CRLA BOSY:
  `/dashboards/smme-kpi/api/?kpi_part=reading&reading_type=crla&assessment_timing=bosy`
- RMA Grade 4 sorted by Proficient:
  `/dashboards/smme-kpi/api/?kpi_part=rma&rma_grade=g4&sort_by=proficient&sort_dir=desc`

Response shape:
- All responses include: `view`, `page`, `page_size`, `total`, `results`
- Fields in `results` vary by `kpi_part` (match the dashboard table columns)

## Notes

- District grouping appears when sorting by District.
- Implementation Overall is the mean of sub-areas when all are present (Access, Quality, Equity, Enabling).
- API and dashboard share the same filter and sorting logic.

## Troubleshooting

- If the page seems slow with many schools, use filters or rely on pagination (default 50 per page).
- Ensure SMEA Form period selection aligns with the intended School Year/Quarter; selecting a Form period overrides both.
- For programmatic integrations, prefer the JSON API with explicit parameters for reproducibility.
