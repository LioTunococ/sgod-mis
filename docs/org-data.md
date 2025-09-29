# Organization Data Model (Phase 1)

## Entities
- **Section**: `code` (slug), `name`
- **School**: `code` (slug), `name`, `division`, `district`, `school_type` (optional)

## Seeding Plan
- Load 6 Sections from `data/sections.seed.json`.
- Start with a small sample of Schools (5–10) for testing (CSV to be prepared).
- Later import the full list (~210 schools).

## Usage
- Every `FormTemplate` belongs to a **Section**.
- Every `Submission` belongs to a **School** (and indirectly to a Section via the template).
- Dashboards filter by Section and School (and by district for Section Admins).
