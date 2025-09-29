# Missing Logic

Given (Section S, Period P):
- Get all active FormTemplates in S where P is within open/close
- For each school:
  - If no Submission for (FormTemplate, School, P) → Missing
  - Else map status:
    - DRAFT → Draft
    - SUBMITTED → Submitted
    - RETURNED → Returned
    - NOTED → Noted
