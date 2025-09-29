# Report Submission Workflow (Phase 1)

## Statuses
- **DRAFT** – initial state, editable by SchoolHead
- **SUBMITTED** – locked, pending review
- **RETURNED** – unlocked for edit after SectionAdmin request
- **NOTED** – final state, marked as noted by SectionAdmin

## Transitions
- DRAFT ? SUBMITTED: SchoolHead clicks **Submit**
- SUBMITTED ? RETURNED: SectionAdmin clicks **Return**, adds remarks
- SUBMITTED ? NOTED: SectionAdmin clicks **Note**, adds remarks
- RETURNED ? SUBMITTED: SchoolHead fixes data and clicks **Re-Submit**

## Visibility Rules
- SchoolHead can always view submissions in any state
- SectionAdmin sees only SUBMITTED/RETURNED/NOTED for their section
- Returned submissions show remarks inline for SchoolHead
