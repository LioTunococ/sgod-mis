# Organization Data (Phase 1)

## Entities
- **Section**: \code\ (slug), \
ame\
- **School**: \code\ (slug), \
ame\, \division\, \district\, \school_type\ (optional)

## Seeds
- Sections: \data/sections.seed.json\ (6 SGOD sections)
- Schools (test only for now): \data/schools.sample.csv\ (import later)

## Usage
- Every FormTemplate belongs to a **Section**.
- Every Submission belongs to a **School** (and is scoped in dashboards by district/section).
