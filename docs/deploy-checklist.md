# Deployment Checklist (SMME MVP)

## Pre-Deploy
- git pull / review latest changes
- python manage.py test
- python manage.py migrate
- python manage.py collectstatic --noinput
- python manage.py shell -c "from scripts.seed_data import run; run()"

## Demo Prep
- Verify seeded users (sgod_admin, section_admin_smme, psds_flora, schoolhead_luna)
- Confirm profile alerts / dashboards render expected data
- Ensure docs/screenshots/ images are up to date
- Have docs/demo-guide.md open for talking points

## Post-Demo / Post-Deploy
- Collect stakeholder feedback
- Log issues / enhancements in backlog (Phase 2+)
- Reset DB if needed for subsequent demos

## Accessibility Notes
- Keyboard navigation: auth_nav links, filter forms, buttons tested in Chrome (tab/shift+tab)
- Focus outline is visible on primary/secondary buttons and links
- Table scroll wrappers ensure mobile accessibility (horizontal overflow)
- Remaining follow-ups: add aria-labels for chip warnings (Profile missing/Contact missing)
