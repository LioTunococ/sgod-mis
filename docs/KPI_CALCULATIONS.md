# KPI Calculations - Overview

This document summarizes how KPIs are calculated for the SMEA Form 1 indicators.

## High-level approach
- KPI calculations are implemented in `dashboards/kpi_calculators.py`.
- KPIs are computed per `Period` and can be aggregated across schools or quarters.
- The calculators accept either a `Period` object or a queryset of submission rows and return a dictionary with:
  - `dnme`: { `dnme_percentage`, `dnme_count`, `total_schools` }
  - `implementation_areas`: { `access_percentage`, `quality_percentage`, `equity_percentage`, `governance_percentage`, `management_percentage`, `leadership_percentage` }

## Data Sources
- Primary data comes from `submissions.models.Form1SLPRow` and related submission models.
- Calculations use submission rows filtered by `submission__period` and `submission__school` when needed.

## Aggregation
- When calculating for a period across all schools, the calculators aggregate per-school metrics and then compute averages as needed.
- Missing data is treated as zeros in summary outputs; presence flags indicate whether a school had data.

## Edge Cases
- No submissions for a period: calculators return zeroed metrics and `total_schools` appropriately.
- Partial submissions: calculators compute per-indicator denominators carefully to avoid division by zero.

## Where to find code
- Main entry points:
  - `dashboards/kpi_calculators.calculate_all_kpis_for_period(period, section_code)`
  - `dashboards/kpi_calculators.calculate_all_kpis(submissions_queryset)`

Review the functions in `dashboards/kpi_calculators.py` for implementation details and unit tests in `dashboards/tests.py`.
