from __future__ import annotations

from collections import defaultdict
from django import template

from submissions.models import Submission
import json

register = template.Library()


_STATUS_BADGES = {
    Submission.Status.DRAFT: "badge badge--draft",
    Submission.Status.SUBMITTED: "badge badge--submitted",
    Submission.Status.RETURNED: "badge badge--returned",
    Submission.Status.NOTED: "badge badge--noted",
}


@register.filter
def status_badge_class(status: str) -> str:
    """Return the CSS class for the status badge."""
    return _STATUS_BADGES.get(status, "badge")


@register.simple_tag
def status_badge(status: str) -> dict[str, str]:
    """Return both label and class for use with the UX badge pattern."""
    label = dict(Submission.Status.choices).get(status, status)
    return {"label": label, "css_class": status_badge_class(status)}


@register.filter
def group_slp_by_grade(formset):
    """
    Group SLP formset by grade level for nested accordion display.
    Returns a list of dicts with grade info and subjects.
    """
    grouped = defaultdict(list)
    
    for form in formset:
        grade = form.instance.grade_label
        grouped[grade].append(form)
    
    # Build result with completion stats
    result = []
    for grade_label in sorted(grouped.keys(), key=lambda x: int(x.split()[1]) if len(x.split()) > 1 else 0):
        subjects = grouped[grade_label]
        
        # Only count offered subjects in totals and completion
        offered_subjects = [form for form in subjects if getattr(form.instance, 'is_offered', True)]
        total_subjects = len(offered_subjects)
        completed_subjects = sum(1 for form in offered_subjects if is_subject_complete(form.instance))
        completion_percentage = int((completed_subjects / total_subjects * 100)) if total_subjects > 0 else 0
        
        result.append({
            'grade_label': grade_label,
            'subjects': subjects,
            'total_subjects': total_subjects,
            'completed_subjects': completed_subjects,
            'completion_percentage': completion_percentage,
        })
    
    return result


def _has_real_llc(text: str) -> bool:
    """Return True if LLC text contains any non-placeholder content.

    Placeholder lines like "1.", "2.", "3.", "4." (optionally with trailing spaces)
    are ignored. Any other non-empty content counts as real.
    """
    if not text:
        return False
    lines = [ln.strip() for ln in str(text).splitlines() if ln.strip()]
    if not lines:
        return False
    # If every non-empty line is just an enumeration like "N." then it's placeholder
    all_placeholders = all(bool(l) and (len(l) <= 3) and l[:-1].isdigit() and l.endswith('.') for l in lines)
    return not all_placeholders


def _has_real_intervention(plan_str: str) -> bool:
    """Return True if intervention_plan contains at least one non-empty item.

    Accepts JSON array of objects with key 'intervention'. Treats empty array [] or
    array with all blank interventions as empty. Falls back to simple truthiness for
    legacy plain-text values.
    """
    if not plan_str:
        return False
    s = str(plan_str).strip()
    if not s:
        return False
    # Consider a literal '[]' as empty
    if s == '[]':
        return False
    try:
        data = json.loads(s)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    val = str(item.get('intervention', '')).strip()
                    if val:
                        return True
                elif isinstance(item, str) and item.strip():
                    return True
            return False
    except Exception:
        # Not JSON; treat any non-empty string as present
        return True
    return True


def _interventions_cover_all_selected(codes_csv: str, plan_str: str) -> bool:
    """Return True if every selected reason code has a non-empty intervention.

    - Reasons come from comma-separated codes (e.g., "a,b,f").
    - Interventions are stored as JSON array of objects with keys {code, intervention}.
    - For legacy free-text intervention plans (non-JSON), treat as covered if non-empty
      and at least one reason was selected (best-effort compatibility).
    """
    codes = [c.strip().lower() for c in (codes_csv or "").split(",") if c.strip()]
    if not codes:
        return False
    if not plan_str or not str(plan_str).strip():
        return False
    try:
        data = json.loads(str(plan_str))
        if not isinstance(data, list):
            # Non-list JSON — fall back
            return bool(str(plan_str).strip())
        by_code = {}
        for item in data:
            if isinstance(item, dict):
                code = str(item.get("code", "")).strip().lower()
                intervention = str(item.get("intervention", "")).strip()
                if code and intervention and code not in by_code:
                    by_code[code] = intervention
        # Every selected code must have a non-empty intervention
        return all(bool(by_code.get(code, "").strip()) for code in codes)
    except Exception:
        # Not JSON; if any non-empty string and at least one reason, accept
        return True


def is_subject_complete(slp_row):
    """Determine if a subject is complete based on current (revised) UI fields.

    The analysis 'overall_strategy' field was removed from the frontend; requiring it
    kept subjects perpetually 'incomplete'. Treat analysis as satisfied if the field
    is absent or empty, so completion now depends solely on: offered status, valid
    proficiency distribution, at least one competency listed, and at least one
    intervention entry.
    """
    if not slp_row.is_offered:
        return True  # Not offered subjects are considered complete

    has_proficiency_data = (
        slp_row.enrolment > 0 and
        (slp_row.dnme + slp_row.fs + slp_row.s + slp_row.vs + slp_row.o) == slp_row.enrolment
    )
    has_llc = _has_real_llc(getattr(slp_row, 'top_three_llc', ''))
    # Require interventions for every selected reason code (strict completeness)
    reasons_csv = getattr(slp_row, 'non_mastery_reasons', '') or ''
    has_intervention = _interventions_cover_all_selected(reasons_csv, getattr(slp_row, 'intervention_plan', ''))
    # Analysis no longer required; default True
    has_analysis = True
    return has_proficiency_data and has_llc and has_intervention and has_analysis


@register.filter
def get_subject_status(slp_row):
    """Get completion status for a subject: 'complete', 'incomplete', or 'not-started'."""
    if not slp_row.is_offered:
        return 'not-applicable'
    
    # Check if any data is entered
    has_any_data = (
        slp_row.enrolment > 0 or
        _has_real_llc(getattr(slp_row, 'top_three_llc', '')) or
        _has_real_intervention(getattr(slp_row, 'intervention_plan', '')) or
        bool((getattr(slp_row, 'non_mastery_reasons', '') or '').strip() or (getattr(slp_row, 'non_mastery_other', '') or '').strip())
    )
    
    if not has_any_data:
        return 'not-started'
    
    return 'complete' if is_subject_complete(slp_row) else 'incomplete'


@register.filter
def format_non_mastery_reasons(codes_csv: str, other_text: str = "") -> str:
    """Format comma-separated non-mastery reason codes into readable labels.

    Accepts the stored CSV codes (e.g., "a,b,f") and optional other_text
    for code 'f'. Returns a human-friendly, comma-separated string.
    """
    if not codes_csv:
        return ""
    reasons_map = {
        "a": "Pre-requisite skills were not mastered",
        "b": "The identified LLC are difficult to teach",
        "c": "The identified LLC were not covered or taught during the quarter",
        "d": "Learners under DNME or FS have special education needs",
        "e": "Reading proficiency DNME/FS: low/high emerging (G1-G3) or non-reader/frustration (G4-G10)",
        "f": "Other observable reasons (specify)",
    }
    labels: list[str] = []
    for raw in (codes_csv or "").split(","):
        code = raw.strip().lower()
        if not code:
            continue
        label = reasons_map.get(code, code.upper())
        if code == "f" and (other_text or "").strip():
            # Include the specified 'other' details inline
            label = f"Other: {(other_text or '').strip()}"
        labels.append(label)
    return ", ".join(labels)


@register.filter
def non_mastery_reasons_list(codes_csv: str) -> list:
    """Return list of human labels for non-mastery reason codes (excludes 'Other' text)."""
    if not codes_csv:
        return []
    reasons_map = {
        "a": "Pre-requisite skills not mastered",
        "b": "LLC difficult to teach",
        "c": "LLC not covered",
        "d": "Learners with SPED needs",
        "e": "Reading DNME/FS low/high emerging",
        "f": "Other",
    }
    labels: list[str] = []
    for raw in (codes_csv or "").split(","):
        code = raw.strip().lower()
        if not code:
            continue
        label = reasons_map.get(code)
        if label and code != "f":  # exclude free-text here
            labels.append(label)
        elif code not in reasons_map:
            labels.append(code.upper())
    return labels


@register.filter
def llc_to_list(text: str) -> list:
    """Split LLC multiline text into a cleaned list of non-empty items."""
    if not text:
        return []
    lines = []
    for raw in str(text).splitlines():
        item = raw.strip()
        if not item:
            continue
        # Strip leading numbering like "1. ", "- ", etc.
        if item[:2].isdigit() and len(item) > 2 and item[2] in ".)":
            item = item[3:].strip()
        elif item and item[0] in "-•*":
            item = item[1:].strip()
        lines.append(item)
    return lines

