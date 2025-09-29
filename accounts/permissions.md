# Role Groups & Permission Checks (Phase 1)

## Groups to create
- **SchoolHead**
- **SectionAdmin:yfs**
- **SectionAdmin:pr**
- **SectionAdmin:smme**
- **SectionAdmin:hrd**
- **SectionAdmin:smn**
- **SectionAdmin:drrm**
- *(Placeholders)* **SGODAdmin**, **ASDS**, **SDS**

## Guarding rules (high level)
- **SchoolHead**: can CRUD **own** school's drafts and submit; can view any of **own** submissions (Submitted/Returned/Noted).  
- **SectionAdmin:<code>**: can list & act on submissions where orm_template.section.code == <code>.

## Button visibility (Phase 1)
- SchoolHead: **Save Draft**, **Submit** (when valid), **Edit** (if Returned)
- SectionAdmin:<code>: **Note**, **Return with remarks** (only when status = Submitted)
- Others: no action buttons in Phase 1

## Notes
- Keep these as Django Groups. Later phases will add SGOD/ASDS/SDS actions for proposals.
