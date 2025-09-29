# Access Matrix (Phase 1: Reports Only)

**Roles in use now**
- **SchoolHead** — single account per school; creates, edits, submits reports; sees Noted/Returned remarks.
- **SectionAdmin:<code>** — reviews submitted reports for their section; can **Note** or **Return**.
- *(Placeholders, no actions in Phase 1)* **SGODAdmin**, **ASDS**, **SDS** — kept for future plan/proposal workflows.

## Screen Access

| Screen / Action                             | SchoolHead | SectionAdmin:<code> | SGODAdmin | ASDS | SDS |
|---------------------------------------------|-----------:|---------------------:|----------:|-----:|----:|
| Dashboard (school landing)                   | ✅         | 🔒                    | 🔒        | 🔒   | 🔒  |
| Section list (6 sections)                    | ✅         | 🔒                    | 🔒        | 🔒   | 🔒  |
| Section → Open forms list                    | ✅         | 🔒                    | 🔒        | 🔒   | 🔒  |
| Create/Edit Draft report                     | ✅         | 🔒                    | 🔒        | 🔒   | 🔒  |
| Submit report                                | ✅         | 🔒                    | 🔒        | 🔒   | 🔒  |
| View Submitted/Noted/Returned report         | ✅         | ✅                    | 🔒        | 🔒   | 🔒  |
| Note a report (mark as NOTED + remarks)      | 🔒         | ✅                    | 🔒        | 🔒   | 🔒  |
| Return report to school w/ remarks           | 🔒         | ✅                    | 🔒        | 🔒   | 🔒  |
| “Who Didn’t Submit” dashboard (per section)  | 🔒         | ✅                    | 🔒        | 🔒   | 🔒  |

Legend: ✅ allowed, 🔒 not allowed

## Status Transitions (Reports)
- `DRAFT` → **SchoolHead: Submit** → `SUBMITTED`
- **SectionAdmin:**  
  - **Note** → `NOTED` (School sees Noted + remarks)  
  - **Return** → `RETURNED` (School can edit and resubmit)
