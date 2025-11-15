from __future__ import annotations

from collections import defaultdict
from django import template

from submissions.models import Submission

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


def is_subject_complete(slp_row):
    """Check if a subject is complete (has all required data filled)."""
    if not slp_row.is_offered:
        return True  # Not offered subjects are considered complete
    
    # Check required fields
    has_proficiency_data = (
        slp_row.enrolment > 0 and
        (slp_row.dnme + slp_row.fs + slp_row.s + slp_row.vs + slp_row.o) == slp_row.enrolment
    )
    
    has_llc = bool(slp_row.top_three_llc and slp_row.top_three_llc.strip())
    has_intervention = bool(slp_row.intervention_plan and slp_row.intervention_plan.strip())
    
    # Check analysis: current UI only requires an overall strategy
    # Other analysis fields (dnme_factors, fs_factors, s_practices, etc.) are optional
    has_analysis = False
    if hasattr(slp_row, 'analysis') and slp_row.analysis:
        analysis = slp_row.analysis
        has_analysis = bool(
            analysis.overall_strategy and analysis.overall_strategy.strip()
        )

    return has_proficiency_data and has_llc and has_intervention and has_analysis


@register.filter
def get_subject_status(slp_row):
    """Get completion status for a subject: 'complete', 'incomplete', or 'not-started'."""
    if not slp_row.is_offered:
        return 'not-applicable'
    
    # Check if any data is entered
    has_any_data = (
        slp_row.enrolment > 0 or
        bool(slp_row.top_three_llc and slp_row.top_three_llc.strip()) or
        bool(slp_row.intervention_plan and slp_row.intervention_plan.strip()) or
        bool(getattr(slp_row, 'non_mastery_reasons', '') or getattr(slp_row, 'non_mastery_other', ''))
    )
    
    if not has_any_data:
        return 'not-started'
    
    return 'complete' if is_subject_complete(slp_row) else 'incomplete'

