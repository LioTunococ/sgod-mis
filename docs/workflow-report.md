# Report Submission Workflow (Phase 1)

## Statuses
- **DRAFT** – editable by SchoolHead.
- **SUBMITTED** – locked, pending review.
- **RETURNED** – unlocked after SectionAdmin return.
- **NOTED** – final; SectionAdmin marks noted with remarks.

## Transitions
- SchoolHead: DRAFT ? SUBMITTED (Submit button)
- SectionAdmin: SUBMITTED ? RETURNED (Return with remarks)
- SectionAdmin: SUBMITTED ? NOTED (Note with remarks)
- SchoolHead: RETURNED ? SUBMITTED (Resubmit after edits)

## Role Visibility
- SchoolHead always sees own submissions (all statuses) and remarks.
- SectionAdmin sees submissions for their section (Submitted/Returned/Noted) with full review tools.
- PSDS accesses read-only queue filtered to assigned districts plus dashboards.
- SGODAdmin sees division-wide queues/dashboards; no direct edit in Phase 1.

Future phases: integrate SchoolProfile-driven tabs (grade/strand filtering) and add plan workflows for ASDS/SDS.
