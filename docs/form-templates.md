# Form Template & Period Spec (Phase 1)

## Model Fields
- **section** (FK) – which SGOD section this form belongs to
- **code** – short slug (e.g., smea-form-1)
- **title** – human readable (e.g., "SMEA Form 1")
- **version** – for version tracking
- **period_type** – month, quarter, or semester
- **open_at / close_at** – date window when the form is active
- **is_active** – toggles visibility on dashboards
- **schema_descriptor** – (JSON) list of fields/questions; can expand later

## Notes
- School dashboard will only show forms where:
  - open_at <= today <= close_at
  - is_active = True
- Each school can have one Submission per FormTemplate+Period.
