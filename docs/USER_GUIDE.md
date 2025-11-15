# SMME Dashboard - User Guide

This guide explains how to use the SMME KPI Dashboard and the related admin features.

## Overview
The dashboard provides KPI summaries and charts for the SMME section. Filters allow selecting school year, quarter, school, KPI metric, and chart type.

## Dashboard Filters
- School Year: Select the academic year (e.g., SY 2025-2026). School years are created in the admin and automatically include Q1-Q4.
- Quarter: Choose a quarter (Q1-Q4) or "All Quarters" to view aggregated data.
- School: Filter by a specific school or "All Schools".
- KPI Metric: Choose between DNME, Access, Quality, Governance, Management, Leadership.
- Chart Type: Bar, Line, Doughnut, Pie.

Notes:
- Filters update the dashboard via AJAX (no page reload). Click "Apply Filters" or change a filter to trigger update.
- School year and quarter are categorical; they do not contain start/end dates. Forms maintain their own open/close dates.

## Creating a School Year (Admin)
1. Login to Django admin and go to `Submissions → Period`.
2. Use the "Quick School Year Creation" panel at the top.
3. Enter the starting year (e.g., `2025`) and click "Create SY with Q1-Q4".
4. The system will create four Period records (Q1–Q4) for that school year.

## Managing Forms
- Form templates have `school_year` and `quarter_filter` fields for classification. These are optional and used for KPI filtering.
- FormTemplate still has `open_at` and `close_at` fields — those control when forms are accessible.

## Submissions
- When creating submissions, staff choose the school year and quarter (categorical selection).
- The system does not enforce submission dates to match quarters — classification is manual.

## Admin Actions
- In the Period admin you can select periods and use the "Auto-create Q1-Q4 for school year(s)" action to create missing quarters.

## Troubleshooting
- If filters don't update, check browser console for JS errors and ensure you are authenticated.
- If a school year doesn't appear, verify Period records exist (`school_year_start` field) in admin.

## Support
If you need help or want automation (date-based validation or scheduled activation), open an issue in the project tracker or ask the project lead.
