# Access Matrix (Phase 1)

## Roles
- **SchoolHead** - creates/edits submissions, sees remarks, resubmits when returned.
- **SectionAdmin** - reviews submissions for their section; can note/return; sees dashboards for their section.
- **PSDS** - reviews district-wide metrics (assigned districts), can open reviewer dashboards and queue in read-only mode.
- **SGOD Admin/Chief** - division-wide overview; inherits section admin tooling for overrides.
- **ASDS/SDS** - reserved for future plan workflows.

## Screen & Action Access
| Screen / Action                            | SchoolHead             | SectionAdmin          | PSDS                       | SGODAdmin                |
|--------------------------------------------|------------------------|-----------------------|----------------------------|--------------------------|
| School landing dashboard                   | Yes                    | Yes (queue widgets)   | Yes                        | Yes                      |
| Section open-forms list                    | Yes (assigned school)  | View (cannot start)   | No                         | No *                     |
| Create/edit draft submission               | Yes                    | No                    | No                         | Yes *                    |
| Submit submission                          | Yes                    | No                    | No                         | Yes *                    |
| View submitted/returned/noted submission   | Yes (own school)       | Yes (section)         | View (district scope)      | Yes                      |
| Note submission                            | No                     | Yes                   | No                         | Yes                      |
| Return submission                          | No                     | Yes                   | No                         | Yes                      |
| Review queue                               | No                     | Yes                   | View (district filtered)   | Yes                      |
| "Who Didn't Submit" dashboard              | No                     | View (section scope)  | View (district scope)      | Yes (division scope)     |
| SMME KPI dashboard                         | No                     | View (section scope)  | View (district scope)      | Yes (division selector)  |

Legend: Yes = authorised, No = not authorised, View = read-only.  
*SGOD Admin inherits Section Admin capabilities for override scenarios but typically does not initiate school submissions.

## Status Transitions
- DRAFT -> SUBMITTED: SchoolHead submits.
- SUBMITTED -> RETURNED: SectionAdmin returns with remarks.
- SUBMITTED -> NOTED: SectionAdmin notes (final).
- RETURNED -> SUBMITTED: SchoolHead re-submits after editing.

Future phases will extend SGOD Admin/Division Admin with school/user management and expand ASDS/SDS actions.
