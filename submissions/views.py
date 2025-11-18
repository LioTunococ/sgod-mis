from __future__ import annotations
import datetime
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse
from django.db.models import Case, IntegerField, Q, Value, When, Sum, F, Count, Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django import forms

from .models import (
    Submission,
    Form1SLPRow,
    Form1SLPLLCEntry,
    Form1SLPAnalysis,
)
from .forms import (
    SLPProficiencyForm,
    SLPLLCEntryForm,
    SLPAnalysisForm,
    SLPLLCEntryFormSet,
    Form1SLPRowForm,
)
from django.urls import reverse
from django.utils import timezone

from accounts import roles as account_roles
from accounts import scope as account_scope
from accounts import services as account_services
from accounts.decorators import require_school_head, require_section_admin
from organizations.models import Section

from . import constants as smea_constants
from . import exports as submission_exports
from .forms import (
    Form1ADMHeaderForm,
    Form1ADMRowFormSet,
    Form1PctRowFormSet,
    Form1ReadingCRLAFormSet,
    Form1ReadingInterventionFormSet,
    Form1ReadingPHILIRIFormSet,
    Form1RMAInterventionFormSet,
    Form1RMARowFormSet,
    Form1SLPAnalysisForm,
    Form1SLPRowFormSet,
    Form1SLPTopDNMEFormSet,
    Form1SLPTopOutstandingFormSet,
    Form1SignatoriesForm,
    Form1SupervisionRowFormSet,
    FormTemplateCreateForm,
    FormTemplateScheduleForm,
    SMEAActivityRowForm,
    SMEAActivityRowFormSet,
    SMEAProjectForm,
    SMEAProjectFormSet,
    SubmissionAttachmentForm,
    SubmissionReviewForm,
    # New Reading Assessment Forms
    ReadingAssessmentCRLAForm,
    ReadingAssessmentPHILIRIForm,
    ReadingInterventionNewForm,
    # New Reading Assessment FormSets
    ReadingAssessmentCRLAFormSet,
    ReadingAssessmentPHILIRIFormSet,
    ReadingInterventionNewFormSet,
)
from .models import (
    Form1ADMHeader,
    Form1ADMRow,
    Form1PctHeader,
    Form1PctRow,
    Form1ReadingCRLA,
    Form1ReadingIntervention,
    Form1ReadingPHILIRI,
    Form1RMAIntervention,
    Form1RMARow,
    Form1SLPAnalysis,
    Form1SLPLLCEntry,
    Form1SLPRow,
    Form1SLPTopDNME,
    Form1SLPTopOutstanding,
    Form1Signatories,
    Form1SupervisionRow,
    FormTemplate,
    Period,
    Submission,
    SubmissionAttachment,
    SMEAProject,
    SMEAActivityRow,
    # New Reading Assessment Models
    ReadingAssessmentCRLA,
    ReadingAssessmentPHILIRI,
    ReadingInterventionNew,
)

EXPECTED_TIMINGS_BY_QUARTER = {
    # Policy: Q1 → EOSY, Q2/Q3 → BOSY, Q4 → MOSY
    "Q1": ["eosy"],
    "Q2": ["bosy"],
    "Q3": ["bosy"],
    "Q4": ["mosy"],
}


def _resolve_grade_span(school) -> tuple[int | None, int | None]:
    if not school:
        return (None, None)
    profile = getattr(school, "profile", None)
    start = getattr(profile, "grade_span_start", None)
    end = getattr(profile, "grade_span_end", None)
    if start is not None and end is not None:
        return (start, end)
    if school.min_grade is not None and school.max_grade is not None:
        return (school.min_grade, school.max_grade)
    return (None, None)


def grade_numbers_for_school(school) -> list[int]:
    start, end = _resolve_grade_span(school)
    if start is None or end is None:
        return sorted(smea_constants.GRADE_NUMBER_TO_LABEL.keys())
    start = max(0, start)
    end = max(start, end)
    return [n for n in range(start, end + 1) if n in smea_constants.GRADE_NUMBER_TO_LABEL]


def slp_grade_labels_for_school(school) -> list[str]:
    return [smea_constants.GRADE_NUMBER_TO_LABEL[n] for n in grade_numbers_for_school(school) if n in smea_constants.GRADE_NUMBER_TO_LABEL]


def slp_subjects_for_grade(grade_number: int):
    subjects = smea_constants.SLP_SUBJECTS_BY_GRADE.get(grade_number)
    if not subjects:
        return [smea_constants.SLP_DEFAULT_SUBJECT]
    return subjects


def slp_grade_subject_pairs(school) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for grade_label in slp_grade_labels_for_school(school):
        grade_number = smea_constants.GRADE_LABEL_TO_NUMBER.get(grade_label)
        for subject_code, _ in slp_subjects_for_grade(grade_number):
            pairs.append((grade_label, subject_code))
    if not pairs:
        default_grade = smea_constants.GRADE_NUMBER_TO_LABEL.get(0, 'Grade 1')
        pairs.append((default_grade, smea_constants.SLP_DEFAULT_SUBJECT[0]))
    return pairs

def _display_grade_label(label: str) -> str:
    if label in smea_constants.GRADE_LABEL_TO_NUMBER:
        return label
    for number, code in smea_constants.RMA_GRADE_LABEL_FOR_NUMBER.items():
        if code == label:
            return smea_constants.GRADE_NUMBER_TO_LABEL.get(number, label)
    return label


def build_slp_dnme_summary(slp_rows) -> dict[str, list[dict[str, int | str]]]:
    return build_slp_top_summary(slp_rows, "dnme")


def build_slp_dnme_recommendations(slp_rows) -> list[dict[str, int | float | str]]:
    """Pick per-subject focus by highest DNME percentage.

    We look across ALL SLP rows (not just Top 5 by count) to find the
    grade with the highest DNME percentage per subject. Ties are broken
    by absolute DNME count, then by lowest grade number.
    """
    best_by_subject: dict[str, dict[str, int | float | str]] = {}
    for row in slp_rows:
        if not getattr(row, "is_offered", True):
            continue
        enrolment = getattr(row, "enrolment", 0) or 0
        dnme = getattr(row, "dnme", 0) or 0
        pct = (dnme / enrolment) * 100 if enrolment else 0.0

        subject = row.get_subject_display()
        grade_display = _display_grade_label(row.grade_label)
        grade_order = _grade_number_for_label(grade_display)

        candidate = {
            "subject": subject,
            "grade": grade_display,
            "count": dnme,
            "pct": round(pct, 1),
            "_order": grade_order,
        }

        current = best_by_subject.get(subject)
        if not current:
            best_by_subject[subject] = candidate
            continue
        # Compare by pct, then by count, then by grade order (lower first)
        if (
            candidate["pct"], candidate["count"], -candidate["_order"]
        ) > (
            current["pct"], current["count"], -current["_order"]
        ):
            best_by_subject[subject] = candidate

    # Clean internal keys and order by subject
    result: list[dict[str, int | float | str]] = []
    for subject in sorted(best_by_subject.keys()):
        entry = dict(best_by_subject[subject])
        entry.pop("_order", None)
        result.append(entry)
    return result


def _grade_number_for_label(label: str) -> int:
    """Return numeric grade order for a label.

    Supports SLP labels (e.g., "Kinder", "Grade 1") and RMA codes
    (e.g., "g7"). Falls back to a large number for unknown labels to
    keep them at the end of ordered lists.
    """
    # Direct SLP mapping
    if label in smea_constants.GRADE_LABEL_TO_NUMBER:
        return smea_constants.GRADE_LABEL_TO_NUMBER[label]
    # RMA code mapping (g1, g2, ...)
    for number, code in smea_constants.RMA_GRADE_LABEL_FOR_NUMBER.items():
        if code == label:
            return number
    # Try to parse raw strings like "Grade 7"
    try:
        lower = (label or "").lower().strip()
        if lower.startswith("grade "):
            return int(lower.split()[1])
        if lower == "kinder":
            return 0
    except Exception:
        pass
    return 999


def build_slp_top_summary(slp_rows, field: str, sort_top_by_grade: bool = True) -> dict[str, list[dict[str, int | str]]]:
    """Build per-subject Top 5 summary for SLP rows.

    - Picks the Top 5 grade levels by absolute learner count for the given field
      (e.g., "dnme" or "o").
    - Returns those Top 5 ordered by grade level (lowest to highest) when
      sort_top_by_grade is True.
    - Each entry includes the absolute count and the percentage relative to
      enrolment (pct), enabling the UI to show both.
    """
    summary: dict[str, list[dict[str, int | str]]] = {}
    for row in slp_rows:
        if not getattr(row, "is_offered", True):
            continue
        value = getattr(row, field, 0) or 0
        enrolment = getattr(row, "enrolment", 0) or 0
        pct = round((value / enrolment) * 100, 1) if enrolment else 0.0
        grade_display = _display_grade_label(row.grade_label)
        subject_label = row.get_subject_display()
        entry = {
            "grade": grade_display,
            "count": value,
            "enrolment": enrolment,
            "pct": pct,
            # numeric key used only for ordering
            "_order": _grade_number_for_label(grade_display),
        }
        summary.setdefault(subject_label, []).append(entry)

    ordered_subjects: list[tuple[int, str, list[dict[str, int | str]]]] = []
    for subject, entries in summary.items():
        # Select Top 5 by absolute count
        entries.sort(key=lambda entry: entry["count"], reverse=True)
        top5 = entries[:5]
        # Order the Top 5 by grade number for display
        if sort_top_by_grade:
            top5.sort(key=lambda entry: entry.get("_order", 999))
        # Compute a subject ordering key based on the lowest grade in its Top 5
        subject_min_order = min((e.get("_order", 999) for e in top5), default=999)
        # Drop internal ordering key before returning
        for e in top5:
            e.pop("_order", None)
        ordered_subjects.append((subject_min_order, subject, top5))

    # Order subjects by their earliest grade level, then by subject name
    ordered_subjects.sort(key=lambda t: (t[0], t[1]))
    return {subject: top5 for (_ord, subject, top5) in ordered_subjects}


def build_slp_outstanding_summary(slp_rows) -> dict[str, list[dict[str, int | str]]]:
    return build_slp_top_summary(slp_rows, "o")


def rma_grade_labels_for_school(school) -> list[str]:
    labels = []
    for n in grade_numbers_for_school(school):
        if n in smea_constants.RMA_GRADE_LABEL_FOR_NUMBER:
            labels.append(smea_constants.RMA_GRADE_LABEL_FOR_NUMBER[n])
    if not labels:
        return list(smea_constants.RMA_GRADE_LABEL_FOR_NUMBER.values())
    return labels


def ensure_pct_rows(submission: Submission) -> Form1PctHeader:
    header, _ = Form1PctHeader.objects.get_or_create(submission=submission)
    required_areas = {choice[0] for choice in Form1PctRow._meta.get_field("area").choices}
    existing = set(header.rows.values_list("area", flat=True))
    for area in required_areas - existing:
        Form1PctRow.objects.create(header=header, area=area, percent=0, action_points="")
    header.rows.exclude(area__in=required_areas).delete()
    return header


def ensure_slp_rows(submission: Submission, grade_subject_pairs: list[tuple[str, str]]) -> None:
    existing_pairs = {
        (row.grade_label, row.subject)
        for row in Form1SLPRow.objects.filter(submission=submission)
    }
    pairs_set = set(grade_subject_pairs)
    for grade_label, subject_code in grade_subject_pairs:
        if (grade_label, subject_code) not in existing_pairs:
            Form1SLPRow.objects.create(
                submission=submission,
                grade_label=grade_label,
                subject=subject_code,
                enrolment=0,
                dnme=0,
                fs=0,
                s=0,
                vs=0,
                o=0,
                is_offered=True,
            )
    for row in Form1SLPRow.objects.filter(submission=submission):
        if (row.grade_label, row.subject) not in pairs_set:
            row.delete()


def _apply_shs_strand_defaults(submission: Submission) -> None:
    """Default SHS specialized subjects (G11/G12) to not offered based on school profile strands.

    - If the school's profile lists SHS strands (e.g., ["STEM", "ABM"]), keep those strands offered by default.
    - For other strands, mark specialized subjects as not offered ONLY when the row is currently empty
      (enrolment and all proficiency counts are zero), to avoid clobbering existing user data.
    - Core SHS subjects are unaffected; only specialized subjects with a known strand prefix are considered.
    """
    school = submission.school
    profile = getattr(school, "profile", None)
    offered_labels = set((profile.strands or [])) if getattr(profile, "strands", None) else set()
    # Build prefix -> label mapping from constants
    strand_prefix_to_label = {prefix: label for (_code, label, prefix) in smea_constants.SHS_STRANDS}

    def is_row_empty(row: Form1SLPRow) -> bool:
        return (row.enrolment or 0) == 0 and all(
            (getattr(row, f) or 0) == 0 for f in ("dnme", "fs", "s", "vs", "o")
        )

    shs_rows = Form1SLPRow.objects.filter(
        submission=submission,
        grade_label__in=["Grade 11", "Grade 12"],
    )
    updates = []
    for row in shs_rows:
        subject_code = row.subject or ""
        matched_label = None
        for prefix, label in strand_prefix_to_label.items():
            if subject_code.startswith(prefix):
                matched_label = label
                break
        if not matched_label:
            continue  # Not a specialized strand subject
        if matched_label in offered_labels:
            continue  # Keep offered by default
        # Not in offered strands; default to not offered if empty and currently offered
        if row.is_offered and is_row_empty(row):
            row.is_offered = False
            # Counts already zero if empty; ensure enrolment is zero for consistency
            row.enrolment = 0
            updates.append(row)
    if updates:
        Form1SLPRow.objects.bulk_update(updates, ["is_offered", "enrolment"])




def ordered_slp_rows(submission: Submission):
    pairs = slp_grade_subject_pairs(submission.school)
    pair_index = {(grade, subject): index for index, (grade, subject) in enumerate(pairs)}
    order_case = Case(
        *[When(grade_label=grade, subject=subject, then=Value(index)) for (grade, subject), index in pair_index.items()],
        default=Value(len(pair_index)),
        output_field=IntegerField(),
    )
    return (
        submission.form1_slp_rows.select_related("analysis")
        .annotate(_order=order_case)
        .order_by("_order", "grade_label", "subject")
    )


def ensure_slp_top_entries(model, submission: Submission) -> None:
    existing_positions = set(model.objects.filter(submission=submission).values_list("position", flat=True))
    for position in range(1, 6):
        if position not in existing_positions:
            model.objects.create(submission=submission, position=position, grade_label="", count=0)
    model.objects.filter(submission=submission).exclude(position__in=range(1, 6)).delete()


def ensure_fixed_order_interventions(model, submission: Submission) -> None:
    existing_orders = set(model.objects.filter(submission=submission).values_list("order", flat=True))
    for order in range(1, 6):
        if order not in existing_orders:
            model.objects.create(submission=submission, order=order, description="")
    model.objects.filter(submission=submission).exclude(order__in=range(1, 6)).delete()


def ensure_rma_rows(submission: Submission, grade_labels: list[str]) -> None:
    existing = set(Form1RMARow.objects.filter(submission=submission).values_list("grade_label", flat=True))
    for label in grade_labels:
        if label not in existing:
            Form1RMARow.objects.create(submission=submission, grade_label=label, enrolment=0)
    Form1RMARow.objects.filter(submission=submission).exclude(grade_label__in=grade_labels).delete()


def ensure_supervision_rows(submission: Submission) -> None:
    if not Form1SupervisionRow.objects.filter(submission=submission).exists():
        Form1SupervisionRow.objects.create(submission=submission, grade_label="", total_teachers=0, teachers_supervised_observed_ta=0)


def ensure_adm_rows(submission: Submission) -> None:
    # Create ADM header if it doesn't exist
    if not hasattr(submission, 'form1_adm_header'):
        Form1ADMHeader.objects.create(submission=submission, is_offered=True)
    
    # Create default ADM row if none exist
    if not Form1ADMRow.objects.filter(submission=submission).exists():
        Form1ADMRow.objects.create(submission=submission)


def ensure_reading_assessments_new(submission: Submission, period: str) -> None:
    """
    Ensure CRLA and PHILIRI assessment records exist for the given period.
    Creates one record per proficiency/reading level for the selected assessment period.
    """
    from submissions.constants import CRLAProficiencyLevel, PHILIRIReadingLevel
    from submissions.models import ReadingAssessmentCRLA, ReadingAssessmentPHILIRI
    
    # Ensure CRLA records (all 4 proficiency levels: Low Emerging, High Emerging, Developing, Transitioning)
    for level_code, level_display in CRLAProficiencyLevel.CHOICES:
        ReadingAssessmentCRLA.objects.get_or_create(
            submission=submission,
            period=period,
            level=level_code,
            defaults={
                'mt_grade_1': 0,
                'mt_grade_2': 0,
                'mt_grade_3': 0,
                'fil_grade_2': 0,
                'fil_grade_3': 0,
                'eng_grade_3': 0,
            }
        )
    
    # Ensure PHILIRI records (3 reading levels)
    for level_code, level_display in PHILIRIReadingLevel.CHOICES:
        ReadingAssessmentPHILIRI.objects.get_or_create(
            submission=submission,
            period=period,
            level=level_code,
            defaults={
                'eng_grade_4': 0,
                'eng_grade_5': 0,
                'eng_grade_6': 0,
                'eng_grade_7': 0,
                'eng_grade_8': 0,
                'eng_grade_9': 0,
                'eng_grade_10': 0,
                'fil_grade_4': 0,
                'fil_grade_5': 0,
                'fil_grade_6': 0,
                'fil_grade_7': 0,
                'fil_grade_8': 0,
                'fil_grade_9': 0,
                'fil_grade_10': 0,
            }
        )


def ensure_reading_interventions_new(submission: Submission) -> None:
    """Ensure 5 intervention records exist for the submission"""
    from submissions.models import ReadingInterventionNew
    
    existing_orders = set(ReadingInterventionNew.objects.filter(submission=submission).values_list("order", flat=True))
    for order in range(1, 6):
        if order not in existing_orders:
            ReadingInterventionNew.objects.create(submission=submission, order=order, description="")
    ReadingInterventionNew.objects.filter(submission=submission).exclude(order__in=range(1, 6)).delete()


def ensure_reading_difficulty_plans(submission: Submission, period: str, grade_numbers: list[int]) -> None:
    """Ensure a ReadingDifficultyPlan row exists for each grade for the selected period.
    Grade numbers are mapped to RMAGradeLabel choices where possible (k, g1..g12)."""
    from submissions.models import ReadingDifficultyPlan
    # Map numeric grades to existing RMAGradeLabel codes
    number_to_label = {
        0: 'k', 1: 'g1', 2: 'g2', 3: 'g3', 4: 'g4', 5: 'g5', 6: 'g6',
        7: 'g7', 8: 'g8', 9: 'g9', 10: 'g10'
    }
    for g in grade_numbers:
        label = number_to_label.get(g)
        if not label:
            continue
        ReadingDifficultyPlan.objects.get_or_create(
            submission=submission,
            period=period,
            grade_label=label,
            defaults={"data": []}
        )


def _reading_period_for_submission(submission: Submission) -> str:
    """Return reading assessment period (bosy/mosy/eosy) applying override if present."""
    quarter_to_period = {
        'Q1': 'eosy',
        'Q2': 'bosy',
        'Q3': 'bosy',
        'Q4': 'mosy',
    }
    base = quarter_to_period.get(getattr(getattr(submission, 'period', None), 'quarter_tag', ''), 'bosy')
    try:
        override = getattr(getattr(submission, 'form_template', None), 'reading_timing_override', '') or ''
        if override in {'bosy', 'mosy', 'eosy'}:
            return override
    except Exception:
        pass
    return base


def update_reading_difficulty_plans(submission: Submission, period: str, rd_entries: list[dict]) -> None:
    """Sync parsed reading difficulties JSON into ReadingDifficultyPlan rows.

    rd_entries structure:
    [{"grade": "4", "pairs": [{"difficulty": str, "intervention": str}, ...]}, ...]
    Only first 5 non-empty pairs retained. Blank (both fields empty) pairs ignored.
    Lengths trimmed to 500 chars per field.
    """
    from submissions.models import ReadingDifficultyPlan
    # Map displayed grade numbers (Kinder=0, 1..12) to rma grade label codes
    number_to_label = {
        0: 'k', 1: 'g1', 2: 'g2', 3: 'g3', 4: 'g4', 5: 'g5', 6: 'g6',
        7: 'g7', 8: 'g8', 9: 'g9', 10: 'g10'
    }
    for entry in rd_entries:
        grade_raw = entry.get('grade')
        try:
            grade_num = int(str(grade_raw).strip())
        except Exception:
            continue
        label = number_to_label.get(grade_num)
        if not label:
            continue  # skip unsupported grades
        pairs_in = entry.get('pairs') or []
        cleaned: list[dict] = []
        for pair in pairs_in[:5]:  # enforce max 5
            if not isinstance(pair, dict):
                continue
            diff = (pair.get('difficulty') or '').strip()
            interv = (pair.get('intervention') or '').strip()
            if not diff and not interv:
                continue
            # Trim excessive length to prevent bloat
            diff = diff[:500]
            interv = interv[:500]
            cleaned.append({'difficulty': diff, 'intervention': interv})
        try:
            plan, _ = ReadingDifficultyPlan.objects.get_or_create(
                submission=submission,
                period=period,
                grade_label=label,
                defaults={'data': cleaned}
            )
            # Update only if changed to avoid unnecessary writes
            if plan.data != cleaned:
                plan.data = cleaned
                plan.save(update_fields=['data', 'updated_at'])
        except Exception:
            # Non-fatal; continue with other grades
            continue


def ensure_signatories(submission: Submission) -> Form1Signatories:
    signatories, _ = Form1Signatories.objects.get_or_create(submission=submission)
    return signatories


def _submission_tabs(submission: Submission) -> list[dict[str, str]]:
    """Return ordered tabs, optionally filtered by template schema.

    Defaults to all tabs for backward compatibility. If
    submission.form_template.schema_descriptor["enabled_tabs"] exists,
    filter to that set while preserving the default order.
    """
    all_tabs = [
        {"key": "projects", "label": "Projects & Activities"},
        {"key": "pct", "label": "% Implementation"},
        {"key": "slp", "label": "SLP"},
        {"key": "reading", "label": "Reading (CRLA/PHILIRI)"},
        {"key": "rma", "label": "RMA"},
        {"key": "supervision", "label": "Instructional Supervision & TA"},
        {"key": "adm", "label": "ADM One-Stop-Shop & EiE"},
    ]
    try:
        schema = submission.form_template.schema_descriptor or {}
        enabled = schema.get("enabled_tabs") or []
        if not enabled:
            return all_tabs
        enabled_set = set(enabled)
        return [t for t in all_tabs if t["key"] in enabled_set]
    except Exception:
        return all_tabs


def disable_form(form):
    for field in form.fields.values():
        field.disabled = True


def disable_formset(formset):
    for form in formset.forms:
        disable_form(form)
    if hasattr(formset, "can_delete"):
        formset.can_delete = False


@login_required
def open_forms_list(request, section_code):
    section = get_object_or_404(Section, code__iexact=section_code)
    user = request.user

    today = timezone.now().date()
    forms = list(
        FormTemplate.objects.open_on(today)
        .filter(section=section)
        .order_by("title")
    )

    period = (
        Period.objects.filter(is_active=True)
        .order_by("-school_year_start", "-display_order")
        .first()
        or Period.objects.order_by("-school_year_start", "-display_order").first()
    )

    school = account_services.get_primary_school(user)
    allowed_section_codes = account_services.allowed_section_codes(user)
    if not school and section.code.upper() not in allowed_section_codes:
        raise PermissionDenied("No access to this section.")

    submissions_map = {}
    if school and period:
        existing = (
            Submission.objects.for_school(school)
            .filter(period=period, form_template__in=forms)
            .select_related("form_template")
        )
        submissions_map = {s.form_template_id: s for s in existing}

    form_rows = [(form, submissions_map.get(form.id)) for form in forms]

    ctx = {
        "section": section,
        "forms": forms,
        "form_rows": form_rows,
        "today": today,
        "period": period,
        "school": school,
        "submissions_map": submissions_map,
        "can_start": bool(school and period and account_services.user_is_school_head(user, school)),
    }
    return render(request, "submissions/open_forms_list.html", ctx)


@login_required
@require_section_admin(section_kwarg=None)
def manage_section_forms(request):
    user = request.user
    allowed_codes = sorted(account_services.allowed_section_codes(user))
    if not allowed_codes:
        messages.error(request, "No sections are assigned to your account.")
        return redirect("school_home")

    sections_qs = Section.objects.filter(code__iregex=r'^(' + '|'.join(allowed_codes) + ')$').order_by("name")
    selected_section_code = request.GET.get("section")
    if selected_section_code and selected_section_code.upper() not in allowed_codes:
        selected_section_code = None

    forms_qs = FormTemplate.objects.filter(section__in=sections_qs)
    if selected_section_code:
        forms_qs = forms_qs.filter(section__code__iexact=selected_section_code)
    forms_qs = forms_qs.select_related("section").order_by("-open_at", "-close_at", "title")

    action = request.POST.get("action") if request.method == "POST" else None
    create_form = None
    schedule_error_form = None
    schedule_error_id = None

    if request.method == "POST":
        if action == "create":
            create_form = FormTemplateCreateForm(
                request.POST,
                section_queryset=sections_qs,
            )
            if create_form.is_valid():
                template = create_form.save()
                messages.success(
                    request,
                    f"Created form {template.title} ({template.code}) for {template.section.name}.",
                )
                redirect_url = reverse("manage_section_forms")
                if selected_section_code:
                    redirect_url = f"{redirect_url}?section={selected_section_code}"
                return redirect(redirect_url)
        else:
            create_form = FormTemplateCreateForm(section_queryset=sections_qs)

        if action in {"update_schedule", "close_today", "open_today", "delete_form", "extend_close_7"}:
            # Fetch by ID first, then permission-check to avoid case-sensitivity issues
            template = (
                FormTemplate.objects.select_related("section").filter(pk=request.POST.get("form_id")).first()
            )
            if not template:
                messages.warning(request, "Selected form was not found or has already been removed.")
                redirect_url = reverse("manage_section_forms")
                if selected_section_code:
                    redirect_url = f"{redirect_url}?section={selected_section_code}"
                return redirect(redirect_url)
            if template.section.code.upper() not in {c.upper() for c in allowed_codes}:
                raise PermissionDenied("You cannot manage this form.")
            redirect_url = reverse("manage_section_forms")
            if selected_section_code:
                redirect_url = f"{redirect_url}?section={selected_section_code}"

            if action == "update_schedule":
                schedule_form = FormTemplateScheduleForm(request.POST, instance=template)
                if schedule_form.is_valid():
                    schedule_form.save()
                    messages.success(request, f"Updated schedule for {template.title}.")
                    return redirect(redirect_url)
                schedule_error_form = schedule_form
                schedule_error_id = template.id
            elif action == "close_today":
                today = timezone.localdate()
                if template.open_at and template.open_at > today:
                    template.open_at = today
                template.close_at = today
                template.save(update_fields=["open_at", "close_at"])
                messages.success(request, f"Closed {template.title} as of today.")
                return redirect(redirect_url)
            elif action == "open_today":
                today = timezone.localdate()
                template.open_at = today
                if template.close_at and template.close_at < today:
                    template.close_at = today
                template.is_active = True
                template.save(update_fields=["open_at", "close_at", "is_active"])
                messages.success(request, f"Opened {template.title} effective today.")
                return redirect(redirect_url)
            elif action == "extend_close_7":
                today = timezone.localdate()
                # Move close date 7 days from the later of today or existing close date
                base = template.close_at if template.close_at and template.close_at > today else today
                new_close = base + datetime.timedelta(days=7)
                template.close_at = new_close
                template.is_active = True
                template.save(update_fields=["close_at", "is_active"])
                messages.success(request, f"Extended {template.title} until {new_close:%b %d, %Y}.")
                return redirect(redirect_url)
            elif action == "delete_form":
                from dashboards.performance import DashboardCache
                with transaction.atomic():
                    submissions_qs = Submission.objects.filter(form_template=template)
                    # Capture affected schools for cache invalidation before delete
                    affected_school_ids = list(submissions_qs.values_list("school_id", flat=True).distinct())
                    submission_count = submissions_qs.count()
                    submissions_qs.delete()
                    template_title = template.title
                    template.delete()
                # Invalidate cache for affected schools so KPIs reflect deletions immediately
                for sid in affected_school_ids:
                    DashboardCache.invalidate_school_cache(sid)
                messages.warning(
                    request,
                    f"Deleted form {template_title} and {submission_count} related submission{'s' if submission_count != 1 else ''}.",
                )
                return redirect(redirect_url)
    else:
        create_form = FormTemplateCreateForm(
            section_queryset=sections_qs,
            initial={"section": sections_qs.first()},
        )

    schedule_forms = []
    for template in forms_qs:
        if schedule_error_id == template.id and schedule_error_form is not None:
            schedule_forms.append((template, schedule_error_form))
        else:
            schedule_forms.append((template, FormTemplateScheduleForm(instance=template)))

    return render(
        request,
        "submissions/manage_section_forms.html",
        {
            "sections": sections_qs,
            "selected_section_code": selected_section_code,
            "create_form": create_form,
            "form_rows": schedule_forms,
            "allowed_section_codes": allowed_codes,
        },
    )


@login_required
@require_school_head()
def start_submission(request, form_code, period_id):
    form_template = get_object_or_404(FormTemplate, code=form_code, is_active=True)
    period = get_object_or_404(Period, pk=period_id)
    school = account_services.get_primary_school(request.user)

    if not school:
        messages.error(request, "No school is associated with your account.")
        return redirect("open_forms_list", section_code=form_template.section.code)

    submission, created = Submission.objects.get_or_create(
        school=school,
        form_template=form_template,
        period=period,
        defaults={
            "status": Submission.Status.DRAFT,
            "last_modified_by": request.user,
        },
    )
    if created:
        messages.success(request, "Draft submission created. You can start filling it out.")
    return redirect("edit_submission", submission_id=submission.pk)


@login_required
@require_school_head(submission_kwarg="submission_id")
def edit_submission(request, submission_id, submission_obj=None):
    submission = submission_obj or get_object_or_404(
        Submission.objects.select_related("form_template", "period", "school"),
        pk=submission_id,
    )

    school = submission.school
    can_edit = submission.is_editable_by_school()
    can_submit = submission.can_submit()

    tabs = _submission_tabs(submission)

    tab_keys = [tab["key"] for tab in tabs]
    current_tab = request.GET.get("tab") or tab_keys[0]

    if request.method == "POST":
        current_tab = request.POST.get("tab", current_tab)
    if current_tab not in tab_keys:
        current_tab = tab_keys[0]

    next_tab = current_tab
    is_autosave = False
    action = request.POST.get("action") if request.method == "POST" else None
    current_subject_id = request.POST.get("current_subject_id") if request.method == "POST" else None
    current_subject_prefix = request.POST.get("current_subject_prefix") if request.method == "POST" else None
    current_subject_index = request.POST.get("current_subject_index") if request.method == "POST" else None

    slp_grade_labels = slp_grade_labels_for_school(school)
    slp_pairs = slp_grade_subject_pairs(school)
    rma_grade_labels = rma_grade_labels_for_school(school)

    header = ensure_pct_rows(submission)
    ensure_slp_rows(submission, slp_pairs)
    # Apply strand defaults for SHS based on school profile (safe: only empties)
    try:
        _apply_shs_strand_defaults(submission)
    except Exception:
        # Non-fatal: proceed even if profile data is unavailable
        pass
    ensure_slp_top_entries(Form1SLPTopDNME, submission)
    ensure_slp_top_entries(Form1SLPTopOutstanding, submission)
    ensure_fixed_order_interventions(Form1ReadingIntervention, submission)
    ensure_rma_rows(submission, rma_grade_labels)
    ensure_fixed_order_interventions(Form1RMAIntervention, submission)
    ensure_supervision_rows(submission)
    # Do not auto-create ADM rows; user adds PPAs explicitly
    signatories = ensure_signatories(submission)
    
    # Determine assessment timing for Reading based strictly on the submission's Quarter
    # This is enforced (no user choice) to ensure data consistency with the dashboard/API/export.
    selected_reading_period = _reading_period_for_submission(submission)
    
    # Ensure reading assessment records exist for the selected period
    ensure_reading_assessments_new(submission, selected_reading_period)
    ensure_reading_interventions_new(submission)
    # Compute school grades early for Reading Difficulty Plans (may be used later again)
    try:
        school_grades = grade_numbers_for_school(school) if school else []
    except Exception:
        school_grades = []
    # Reading assessments limited to Grades 1-10; exclude Kinder (0) & SHS (11-12)
    reading_grade_numbers = [g for g in school_grades if 1 <= g <= 10]
    ensure_reading_difficulty_plans(submission, selected_reading_period, reading_grade_numbers or [])

    # Order PCT rows by correct sequence: Access, Quality, Equity, Enabling Mechanisms
    from django.db.models import Case, When, Value, IntegerField
    pct_ordering = Case(
        When(area='access', then=Value(1)),
        When(area='quality', then=Value(2)),
        When(area='equity', then=Value(3)),
        When(area='enabling_mechanisms', then=Value(4)),
        output_field=IntegerField(),
    )
    
    pct_formset = Form1PctRowFormSet(
        data=request.POST if request.method == "POST" and current_tab == "pct" else None,
        queryset=header.rows.annotate(sort_order=pct_ordering).order_by("sort_order"),
        prefix="pct",
    )
    slp_formset = Form1SLPRowFormSet(
        data=request.POST if request.method == "POST" and current_tab == "slp" and action != "save_subject" else None,
        queryset=ordered_slp_rows(submission),
        prefix="slp_rows",
    )
    # Bind SLP Top lists only if their management forms are present in POST
    slp_top_dnme_formset = Form1SLPTopDNMEFormSet(
        data=(request.POST if request.method == "POST" and current_tab == "slp" and request.POST.get('slp_top_dnme-TOTAL_FORMS') is not None else None),
        queryset=Form1SLPTopDNME.objects.filter(submission=submission).order_by("position"),
        prefix="slp_top_dnme",
    )
    slp_top_outstanding_formset = Form1SLPTopOutstandingFormSet(
        data=(request.POST if request.method == "POST" and current_tab == "slp" and request.POST.get('slp_top_outstanding-TOTAL_FORMS') is not None else None),
        queryset=Form1SLPTopOutstanding.objects.filter(submission=submission).order_by("position"),
        prefix="slp_top_outstanding",
    )
    reading_crla_formset = Form1ReadingCRLAFormSet(
        data=request.POST if request.method == "POST" and current_tab == "reading" else None,
        queryset=Form1ReadingCRLA.objects.filter(submission=submission).order_by("level", "timing", "subject", "band"),
        prefix="reading_crla",
    )
    reading_philiri_formset = Form1ReadingPHILIRIFormSet(
        data=request.POST if request.method == "POST" and current_tab == "reading" else None,
        queryset=Form1ReadingPHILIRI.objects.filter(submission=submission).order_by("level", "timing", "language"),
        prefix="reading_philiri",
    )
    reading_intervention_formset = Form1ReadingInterventionFormSet(
        data=request.POST if request.method == "POST" and current_tab == "reading" else None,
        queryset=Form1ReadingIntervention.objects.filter(submission=submission).order_by("order"),
        prefix="reading_interventions",
    )
    
    # Custom ordering for CRLA levels: Low Emerging, High Emerging, Developing, Transitioning (all 4 levels)
    crla_ordering = Case(
        When(level='low_emerging', then=Value(1)),
        When(level='high_emerging', then=Value(2)),
        When(level='developing', then=Value(3)),
        When(level='transitioning', then=Value(4)),
        output_field=IntegerField(),
    )
    
    # Custom ordering for PHILIRI levels: Frustration, Instructional, Independent
    philiri_ordering = Case(
        When(level='frustration', then=Value(1)),
        When(level='instructional', then=Value(2)),
        When(level='independent', then=Value(3)),
        output_field=IntegerField(),
    )
    
    # New Reading Assessment Formsets (Matrix-based)
    reading_crla_new_formset = ReadingAssessmentCRLAFormSet(
        data=(request.POST if request.method == "POST" and current_tab == "reading" and request.POST.get('reading_crla_new-TOTAL_FORMS') is not None else None),
        queryset=ReadingAssessmentCRLA.objects.filter(
            submission=submission,
            period=selected_reading_period
        ).annotate(sort_order=crla_ordering).order_by("sort_order"),
        prefix="reading_crla_new",
    )
    reading_philiri_new_formset = ReadingAssessmentPHILIRIFormSet(
        data=(request.POST if request.method == "POST" and current_tab == "reading" and request.POST.get('reading_philiri_new-TOTAL_FORMS') is not None else None),
        queryset=ReadingAssessmentPHILIRI.objects.filter(
            submission=submission,
            period=selected_reading_period
        ).annotate(sort_order=philiri_ordering).order_by("sort_order"),
        prefix="reading_philiri_new",
    )
    reading_interventions_new_formset = ReadingInterventionNewFormSet(
        data=(request.POST if request.method == "POST" and current_tab == "reading" and request.POST.get('reading_interventions_new-TOTAL_FORMS') is not None else None),
        queryset=ReadingInterventionNew.objects.filter(submission=submission).order_by("order"),
        prefix="reading_interventions_new",
    )
    
    from django.db.models import Case, When, IntegerField
    
    # Create custom ordering for RMA rows based on grade number
    rma_ordering = Case(
        When(grade_label='k', then=0),
        When(grade_label='g1', then=1),
        When(grade_label='g2', then=2),
        When(grade_label='g3', then=3),
        When(grade_label='g4', then=4),
        When(grade_label='g5', then=5),
        When(grade_label='g6', then=6),
        When(grade_label='g7', then=7),
        When(grade_label='g8', then=8),
        When(grade_label='g9', then=9),
        When(grade_label='g10', then=10),
        default=99,
        output_field=IntegerField(),
    )
    
    rma_row_formset = Form1RMARowFormSet(
        data=request.POST if request.method == "POST" and current_tab == "rma" else None,
        queryset=Form1RMARow.objects.filter(submission=submission).annotate(
            grade_order=rma_ordering
        ).order_by("grade_order"),
        prefix="rma_rows",
    )
    rma_intervention_formset = Form1RMAInterventionFormSet(
        data=request.POST if request.method == "POST" and current_tab == "rma" else None,
        queryset=Form1RMAIntervention.objects.filter(submission=submission).order_by("order"),
        prefix="rma_interventions",
    )
    supervision_formset = Form1SupervisionRowFormSet(
        data=request.POST if request.method == "POST" and current_tab == "supervision" else None,
        queryset=Form1SupervisionRow.objects.filter(submission=submission).order_by("grade_label", "id"),
        prefix="supervision_rows",
    )
    signatories_initial = {}
    if not signatories.prepared_by:
        school_profile = getattr(school, "profile", None)
        if school_profile and getattr(school_profile, "head_name", None):
            signatories_initial["prepared_by"] = school_profile.head_name
        else:
            signatories_initial["prepared_by"] = ""
    profile = account_roles.get_profile(request.user)
    if not signatories.submitted_to and profile and profile.districts.exists():
        signatories_initial["submitted_to"] = profile.districts.first().name
    signatories_form = Form1SignatoriesForm(
        data=request.POST if request.method == "POST" and current_tab in {"supervision", "adm"} else None,
        instance=signatories,
        initial=signatories_initial,
        prefix="signatories",
    )
    
    # ADM Header Form (for is_offered checkbox)
    # Always create/get the ADM header regardless of current tab or school.implements_adm
    adm_header, _ = Form1ADMHeader.objects.get_or_create(
        submission=submission,
        defaults={'is_offered': True}
    )
    adm_header_form = Form1ADMHeaderForm(
        data=request.POST if request.method == "POST" and current_tab == "adm" else None,
        instance=adm_header,
        prefix="adm_header"
    )
    
    # ADM Row Formset - create if school implements ADM OR if the checkbox says it's offered
    # This allows all schools to access the ADM section and use the checkbox
    adm_formset = Form1ADMRowFormSet(
        data=request.POST if request.method == "POST" and current_tab == "adm" else None,
        queryset=Form1ADMRow.objects.filter(submission=submission).order_by("id"),
        prefix="adm_rows",
    ) if school else None
    if adm_formset is not None:
        for form in adm_formset.forms:
            form.instance.submission = submission

    adm_is_offered = bool(getattr(adm_header, "is_offered", True))
    if adm_header_form:
        raw_value = adm_header_form["is_offered"].value()
        if isinstance(raw_value, str):
            adm_is_offered = raw_value.lower() in {"1", "true", "on", "checked", "yes"}
        elif raw_value is not None:
            adm_is_offered = bool(raw_value)

    # Projects Formset - inline formset for projects
    projects_formset = SMEAProjectFormSet(
        data=request.POST if request.method == "POST" and current_tab == "projects" else None,
        instance=submission,
        prefix="projects",
    )
    
    # Create activity formsets for each existing project
    activity_formsets = []
    if current_tab == "projects":
        for i, project_form in enumerate(projects_formset):
            if project_form.instance.pk:
                activity_formset = SMEAActivityRowFormSet(
                    data=request.POST if request.method == "POST" else None,
                    instance=project_form.instance,
                    prefix=f"activities_{project_form.instance.pk}",
                )
                activity_formsets.append({
                    'project_form': project_form,
                    'formset': activity_formset,
                    'project_index': i,
                })

    if not can_edit:
        # On locked submissions, disable all formsets for GET; for POST, return 403
        disable_formset(pct_formset)
        disable_formset(slp_formset)
        disable_formset(slp_top_dnme_formset)
        disable_formset(slp_top_outstanding_formset)
        disable_formset(reading_crla_formset)
        disable_formset(reading_philiri_formset)
        disable_formset(reading_intervention_formset)
        disable_formset(reading_crla_new_formset)
        disable_formset(reading_philiri_new_formset)
        disable_formset(reading_interventions_new_formset)
        disable_formset(rma_row_formset)
        disable_formset(rma_intervention_formset)
        disable_formset(supervision_formset)
        disable_formset(projects_formset)
        # Also disable activity formsets
        for activity_formset_data in activity_formsets:
            disable_formset(activity_formset_data['formset'])
        disable_form(signatories_form)
        if adm_formset:
            disable_formset(adm_formset)
        if request.method == "POST":
            # Explicitly forbid modifying a submitted/locked report
            raise PermissionDenied("Submission is read-only.")

    success = False

    if request.method == "POST":
        next_tab = request.POST.get("next_tab") or current_tab
        if next_tab not in tab_keys:
            next_tab = current_tab
        is_autosave = request.POST.get("autosave") == "1"

        if action == "submit_submission":
            if not can_submit:
                messages.error(request, "Submission cannot be submitted in its current state.")
            else:
                try:
                    submission.mark_submitted(request.user)
                except ValidationError as exc:
                    messages.error(request, '\n'.join(exc.messages if hasattr(exc, 'messages') else [str(exc)]))
                else:
                    messages.success(request, "Submission sent to the section for review.")
                    return redirect("edit_submission", submission_id=submission.id)
        else:
            if not can_edit:
                # Handled earlier with a 403; keep this branch as a safety net
                raise PermissionDenied("Submission is read-only.")

            if current_tab == "projects":
                if is_autosave:
                    # Quick save scope: persist only the project formset, ignore activities validation
                    # DIAGNOSTIC: Log POST data
                    print("[DIAGNOSTIC] AUTOSAVE POST DATA:", dict(request.POST))
                    if projects_formset.is_valid():
                        project_instances = projects_formset.save(commit=False)
                        # Delete flagged projects explicitly
                        for obj in getattr(projects_formset, 'deleted_objects', []):
                            print(f"[DIAGNOSTIC] Deleting project (autosave): {obj.pk}")
                            obj.delete()
                        for inst in project_instances:
                            inst.submission = submission
                            inst.save()
                        # Save M2M if present (not expected here, but safe)
                        try:
                            projects_formset.save_m2m()
                        except Exception:
                            pass
                        success = True
                else:
                    # Validate all formsets (projects + activities)
                    all_valid = projects_formset.is_valid()
                    # Track if any deletions were performed
                    any_activity_deleted = False
                    # Always process deletions for activities, even if formset is invalid
                    for formset_data in activity_formsets:
                        fs = formset_data['formset']
                        # Delete flagged rows first (even if formset is invalid)
                        for obj in getattr(fs, 'deleted_objects', []):
                            obj.delete()
                            any_activity_deleted = True
                    # Now validate all activity formsets
                    for formset_data in activity_formsets:
                        if not formset_data['formset'].is_valid():
                            all_valid = False

                    if all_valid:
                        # Save projects (commit=False to ensure deletes apply)
                        proj_instances = projects_formset.save(commit=False)
                        for obj in getattr(projects_formset, 'deleted_objects', []):
                            obj.delete()
                        for inst in proj_instances:
                            inst.submission = submission
                            inst.save()
                        try:
                            projects_formset.save_m2m()
                        except Exception:
                            pass
                        # Then save activities for each project (apply deletes first)
                        for formset_data in activity_formsets:
                            fs = formset_data['formset']
                            act_instances = fs.save(commit=False)
                            for inst in act_instances:
                                inst.save()
                            try:
                                fs.save_m2m()
                            except Exception:
                                pass
                        success = True
                    else:
                        # Log all errors for projects_formset
                        for form in projects_formset:
                            # Suppress global error banners for project form errors
                            pass
                        # Log all errors for each activity formset
                        for formset_data in activity_formsets:
                            fs = formset_data['formset']
                            # Suppress global error banners for activity formset errors
                            pass
                        # If any deletions were performed, show a message
                        if any_activity_deleted:
                            messages.info(request, "Some activities were deleted even though other errors prevented saving. Please review remaining errors.")

                # Always apply any posted deletes as a safety net
                ids_to_delete: list[int] = []
                any_activity_delete_flag = False
                print("[DIAGNOSTIC] POST KEYS:", list(request.POST.keys()))
                for key, val in request.POST.items():
                    if not key.endswith('-DELETE'):
                        continue
                    if not key.startswith('activities_'):
                        continue
                    sval = str(val).lower()
                    if sval not in {"1", "true", "on", "yes", "checked"}:
                        continue
                    any_activity_delete_flag = True
                    id_name = key[:-7] + '-id'  # replace -DELETE with -id
                    obj_id = request.POST.get(id_name)
                    print(f"[DIAGNOSTIC] Found DELETE: {key} (id field: {id_name} = {obj_id})")
                    try:
                        obj_pk = int(obj_id) if obj_id is not None else None
                    except (TypeError, ValueError):
                        obj_pk = None
                    if obj_pk:
                        ids_to_delete.append(obj_pk)

                # Fallback: if TOTAL_FORMS < INITIAL_FORMS and a row id has no matching DELETE,
                # treat it as a deletion (some browsers may not post the DELETE field reliably)
                try:
                    import re
                    totals: dict[str, int] = {}
                    initials: dict[str, int] = {}
                    for k, v in request.POST.items():
                        if k.startswith('activities_') and k.endswith('-TOTAL_FORMS'):
                            totals[k[:-12]] = int(v) if str(v).isdigit() else 0
                        elif k.startswith('activities_') and k.endswith('-INITIAL_FORMS'):
                            initials[k[:-14]] = int(v) if str(v).isdigit() else 0
                    id_row_re = re.compile(r'^(activities_\d+)-(\d+)-id$')
                    for k, v in request.POST.items():
                        m = id_row_re.match(k)
                        if not m:
                            continue
                        prefix, idx = m.group(1), m.group(2)
                        tot = totals.get(prefix)
                        ini = initials.get(prefix)
                        if tot is None or ini is None:
                            continue
                        if tot < ini:
                            del_key = f"{prefix}-{idx}-DELETE"
                            if del_key not in request.POST:
                                try:
                                    obj_pk = int(v) if v is not None else None
                                except (TypeError, ValueError):
                                    obj_pk = None
                                if obj_pk:
                                    ids_to_delete.append(obj_pk)
                except Exception as e:
                    print(f"[DIAGNOSTIC] Exception in fallback delete logic: {e}")
                print(f"[DIAGNOSTIC] ids_to_delete: {ids_to_delete}")
                print(f"[DIAGNOSTIC] Activities before delete: {list(SMEAActivityRow.objects.filter(project__submission=submission).values_list('id', flat=True))}")
                if ids_to_delete:
                    # Diagnostic: show activities to be deleted
                    print(f"[DIAGNOSTIC] Attempting to delete activities with ids: {ids_to_delete}")
                    before_qs = list(SMEAActivityRow.objects.filter(id__in=ids_to_delete, project__submission=submission).values('id', 'activity', 'project_id'))
                    print(f"[DIAGNOSTIC] Activities found before delete: {before_qs}")
                    SMEAActivityRow.objects.filter(id__in=ids_to_delete, project__submission=submission).delete()
                    after_qs = list(SMEAActivityRow.objects.filter(id__in=ids_to_delete, project__submission=submission).values('id', 'activity', 'project_id'))
                    print(f"[DIAGNOSTIC] Activities found after delete: {after_qs}")
                    print(f"[DIAGNOSTIC] All activities after delete: {list(SMEAActivityRow.objects.filter(project__submission=submission).values_list('id', flat=True))}")
                    success = True
                elif any_activity_delete_flag:
                    # All flagged were unsaved rows; still treat as success to redirect away
                    print("[DIAGNOSTIC] All flagged for delete were unsaved rows.")
                    success = True

                # Safety net for project deletions as well (in case formset save didn't run)
                proj_ids_to_delete: list[int] = []
                any_project_delete_flag = False
                for key, val in request.POST.items():
                    if not key.startswith('projects-') or not key.endswith('-DELETE'):
                        continue
                    sval = str(val).lower()
                    if sval not in {"1", "true", "on", "yes", "checked"}:
                        continue
                    any_project_delete_flag = True
                    id_name = key[:-7] + '-id'  # projects-<idx>-id (corrected)
                    obj_id = request.POST.get(id_name)
                    try:
                        obj_pk = int(obj_id) if obj_id is not None else None
                    except (TypeError, ValueError):
                        obj_pk = None
                    if obj_pk:
                        proj_ids_to_delete.append(obj_pk)
                if proj_ids_to_delete:
                    SMEAProject.objects.filter(id__in=proj_ids_to_delete, submission=submission).delete()
                    success = True
                elif any_project_delete_flag:
                    # Deleted forms were new/unsaved; still consider operation successful
                    success = True
            elif current_tab == "pct":
                if pct_formset.is_valid():
                    pct_formset.save()
                    success = True
            elif current_tab == "slp" and action == "save_subject":
                next_tab = "slp"
                subject_row = None
                subject_form = None
                slp_rows_list = list(slp_formset.queryset)
                idx_value = None
                if current_subject_id:
                    subject_row = Form1SLPRow.objects.filter(submission=submission, pk=current_subject_id).first()
                if current_subject_index:
                    try:
                        idx_value = int(current_subject_index)
                    except (TypeError, ValueError):
                        idx_value = None
                if idx_value is None and current_subject_prefix:
                    try:
                        idx_value = int(current_subject_prefix.split('-')[1])
                    except (IndexError, ValueError):
                        idx_value = None
                if subject_row is None and idx_value is not None and 0 <= idx_value < len(slp_rows_list):
                    subject_row = slp_rows_list[idx_value]
                if subject_row:
                    prefix = current_subject_prefix or f"slp_rows-{idx_value if idx_value is not None else 0}"
                    subject_form = Form1SLPRowForm(
                        data=request.POST,
                        instance=subject_row,
                        prefix=prefix,
                    )
                    if subject_form.is_valid():
                        # Enforce enrolment equality rule only on explicit draft save / submit (not autosave)
                        if not is_autosave and action in {"save_draft", "submit_submission", "save_subject"}:
                            cd = subject_form.cleaned_data
                            if cd.get("is_offered", True):
                                enrol = cd.get("enrolment") or 0
                                total = sum([
                                    cd.get("dnme") or 0,
                                    cd.get("fs") or 0,
                                    cd.get("s") or 0,
                                    cd.get("vs") or 0,
                                    cd.get("o") or 0,
                                ])
                                if enrol and total != enrol:
                                    subject_form.add_error(None, f"Sum of proficiency counts ({total}) must equal enrolment ({enrol}) for {subject_form.instance.grade_label} - {subject_form.instance.get_subject_display()}.")
                        if subject_form.errors:
                            success = False
                            for errs in subject_form.errors.values():
                                for e in errs:
                                    messages.error(request, e)
                        else:
                            saved_row = subject_form.save()
                            # Persist non-mastery reasons & other (already handled in form.save but ensure post-processing if needed)
                            try:
                                nm_codes = request.POST.get(f'{prefix}-non_mastery_reasons', '')
                                nm_other = request.POST.get(f'{prefix}-non_mastery_other', '')
                                if nm_codes is not None:
                                    saved_row.non_mastery_reasons = nm_codes
                                if nm_other is not None:
                                    saved_row.non_mastery_other = nm_other
                                saved_row.save(update_fields=['non_mastery_reasons','non_mastery_other'])
                            except Exception:
                                pass
                            if idx_value is None:
                                try:
                                    idx_value = int(prefix.split('-')[1])
                                except (IndexError, ValueError):
                                    idx_value = None
                            if idx_value is not None:
                                dnme_factors = request.POST.get(f'slp_analysis_{idx_value}_dnme_factors', '')
                                fs_factors = request.POST.get(f'slp_analysis_{idx_value}_fs_factors', '')
                                s_practices = request.POST.get(f'slp_analysis_{idx_value}_s_practices', '')
                                vs_practices = request.POST.get(f'slp_analysis_{idx_value}_vs_practices', '')
                                o_practices = request.POST.get(f'slp_analysis_{idx_value}_o_practices', '')
                                overall_strategy = request.POST.get(f'slp_analysis_{idx_value}_overall_strategy', '')
                                Form1SLPAnalysis.objects.update_or_create(
                                    slp_row=saved_row,
                                    defaults={
                                        'dnme_factors': dnme_factors,
                                        'fs_factors': fs_factors,
                                        's_practices': s_practices,
                                        'vs_practices': vs_practices,
                                        'o_practices': o_practices,
                                        'overall_strategy': overall_strategy,
                                    },
                                )
                            success = True
                            if not is_autosave:
                                messages.success(
                                    request,
                                    f"Saved {saved_row.grade_label} - {saved_row.get_subject_display()}",
                                )
                    else:
                        success = False
                        for errors in subject_form.errors.values():
                            for error in errors:
                                messages.error(request, error)
                else:
                    messages.error(request, "Unable to determine which subject to save.")
            
            elif current_tab == "slp":
                # Validate core SLP rows; top lists are optional (not rendered in current UI)
                core_valid = slp_formset.is_valid()
                # Enforce aggregate equality only on explicit draft save / submit (not autosave)
                if core_valid and not is_autosave and action in {"save_draft", "submit_submission"}:
                    for form in slp_formset.forms:
                        if not hasattr(form, "cleaned_data"):
                            continue
                        cd = getattr(form, "cleaned_data", {}) or {}
                        if not cd.get("is_offered", True):
                            continue
                        enrol = cd.get("enrolment") or 0
                        if not enrol:
                            continue
                        total = sum([
                            cd.get("dnme") or 0,
                            cd.get("fs") or 0,
                            cd.get("s") or 0,
                            cd.get("vs") or 0,
                            cd.get("o") or 0,
                        ])
                        if total != enrol:
                            form.add_error(None, f"Sum of proficiency counts ({total}) must equal enrolment ({enrol}) for {form.instance.grade_label} - {form.instance.get_subject_display()}.")
                            core_valid = False
                dnme_valid = (not slp_top_dnme_formset.is_bound) or slp_top_dnme_formset.is_valid()
                out_valid = (not slp_top_outstanding_formset.is_bound) or slp_top_outstanding_formset.is_valid()
                if core_valid and dnme_valid and out_valid:
                    # Save SLP row data
                    slp_rows = slp_formset.save()
                    
                    # Save per-row analysis data
                    for idx, slp_row in enumerate(slp_rows):
                        # Get analysis fields for this row
                        dnme_factors = request.POST.get(f'slp_analysis_{idx}_dnme_factors', '')
                        fs_factors = request.POST.get(f'slp_analysis_{idx}_fs_factors', '')
                        s_practices = request.POST.get(f'slp_analysis_{idx}_s_practices', '')
                        vs_practices = request.POST.get(f'slp_analysis_{idx}_vs_practices', '')
                        o_practices = request.POST.get(f'slp_analysis_{idx}_o_practices', '')
                        overall_strategy = request.POST.get(f'slp_analysis_{idx}_overall_strategy', '')
                        
                        # Persist non-mastery reasons (Q2) posted via hidden fields alongside row
                        try:
                            nm_codes = request.POST.get(f'{slp_formset.prefix}-{idx}-non_mastery_reasons', '')
                            nm_other = request.POST.get(f'{slp_formset.prefix}-{idx}-non_mastery_other', '')
                            if nm_codes is not None:
                                slp_row.non_mastery_reasons = nm_codes
                            if nm_other is not None:
                                slp_row.non_mastery_other = nm_other
                            slp_row.save(update_fields=['non_mastery_reasons','non_mastery_other'])
                        except Exception:
                            pass
                        # Create or update analysis record
                        analysis, created = Form1SLPAnalysis.objects.update_or_create(
                            slp_row=slp_row,
                            defaults={
                                'dnme_factors': dnme_factors,
                                'fs_factors': fs_factors,
                                's_practices': s_practices,
                                'vs_practices': vs_practices,
                                'o_practices': o_practices,
                                'overall_strategy': overall_strategy,
                            }
                        )
                    
                    if slp_top_dnme_formset.is_bound:
                        slp_top_dnme_formset.save()
                    if slp_top_outstanding_formset.is_bound:
                        slp_top_outstanding_formset.save()
                    success = True
            elif current_tab == "reading":
                # Use new matrix-based formsets; treat absent sections as optional
                crla_valid = (not reading_crla_new_formset.is_bound) or reading_crla_new_formset.is_valid()
                philiri_valid = (not reading_philiri_new_formset.is_bound) or reading_philiri_new_formset.is_valid()
                interventions_valid = (not reading_interventions_new_formset.is_bound) or reading_interventions_new_formset.is_valid()
                if crla_valid and philiri_valid and interventions_valid:
                    for formset in [reading_crla_new_formset, reading_philiri_new_formset, reading_interventions_new_formset]:
                        if not formset.is_bound:
                            continue
                        instances = formset.save(commit=False)
                        for instance in instances:
                            instance.submission = submission
                            instance.save()
                        formset.save_m2m()
                    # Persist reading difficulties JSON (paired difficulties/interventions per grade)
                    rd_json = request.POST.get('reading_difficulties_json')
                    if rd_json is not None:
                        try:
                            parsed = json.loads(rd_json) if rd_json.strip() else []
                        except Exception:
                            parsed = []
                        # Persist raw JSON first
                        try:
                            data = dict(submission.data or {})
                            data['reading_difficulties_json'] = parsed
                            submission.data = data
                            submission.save(update_fields=['data'])
                        except Exception:
                            pass
                        # Sync into structured model rows
                        try:
                            update_reading_difficulty_plans(submission, selected_reading_period, parsed)
                        except Exception:
                            pass
                    success = True
                else:
                    # Keep errors inline near the forms only (no global banner)
                    pass
            elif current_tab == "rma":
                rows_valid = rma_row_formset.is_valid()
                interventions_valid = rma_intervention_formset.is_valid()
                if rows_valid and not is_autosave and action in {"save_draft", "submit_submission"}:
                    for form in rma_row_formset.forms:
                        if not hasattr(form, "cleaned_data"):
                            continue
                        cd = getattr(form, "cleaned_data", {}) or {}
                        enrol = cd.get("enrolment") or 0
                        if not enrol:
                            continue
                        total = sum([
                            cd.get("emerging_not_proficient") or 0,
                            cd.get("emerging_low_proficient") or 0,
                            cd.get("developing_nearly_proficient") or 0,
                            cd.get("transitioning_proficient") or 0,
                            cd.get("at_grade_level") or 0,
                        ])
                        if total != enrol:
                            # Attempt to get display label
                            try:
                                grade_display = form.instance.get_grade_label_display()
                            except Exception:
                                grade_display = form.instance.grade_label
                            form.add_error(None, f"Sum of proficiency counts ({total}) must equal enrolment ({enrol}) for grade {grade_display}.")
                            rows_valid = False
                if rows_valid and interventions_valid:
                    rma_row_formset.save()
                    # Persist new RMA structured difficulties/interventions JSON (optional)
                    try:
                        pre_json = request.POST.get('rma_pretest_json')
                        eosy_json = request.POST.get('rma_eosy_json')
                        data = dict(submission.data or {})
                        if pre_json is not None:
                            try:
                                data['rma_pretest_json'] = json.loads(pre_json) if pre_json.strip() else []
                            except Exception:
                                data['rma_pretest_json'] = []
                        if eosy_json is not None:
                            try:
                                data['rma_eosy_json'] = json.loads(eosy_json) if eosy_json.strip() else []
                            except Exception:
                                data['rma_eosy_json'] = []
                        if pre_json is not None or eosy_json is not None:
                            submission.data = data
                            submission.save(update_fields=['data'])
                    except Exception:
                        pass
                    # Keep saving legacy interventions if posted/bound
                    try:
                        rma_intervention_formset.save()
                    except Exception:
                        pass
                    success = True
            elif current_tab == "supervision":
                if supervision_formset.is_valid() and signatories_form.is_valid():
                    # Save supervision formset with proper submission assignment
                    instances = supervision_formset.save(commit=False)
                    for instance in instances:
                        instance.submission = submission
                        instance.save()
                    supervision_formset.save_m2m()
                    signatories_form.save()
                    success = True
            elif current_tab == "adm":
                # Save ADM header form first
                if adm_header_form and adm_header_form.is_valid():
                    adm_header_form.save()
                # Then save ADM formset if it exists
                if adm_formset is not None and adm_formset.is_valid():
                    # Save ADM formset with proper submission assignment
                    instances = adm_formset.save(commit=False)
                    for instance in instances:
                        instance.submission = submission
                        instance.save()
                    for obj in adm_formset.deleted_objects:
                        obj.delete()
                    adm_formset.save_m2m()
                    success = True
                elif adm_formset is None:
                    # If ADM formset doesn't exist but header form was valid, still count as success
                    success = adm_header_form and adm_header_form.is_valid()

            if success:
                submission.last_modified_by = request.user
                submission.save(update_fields=["last_modified_by", "updated_at"])
                if not is_autosave:
                    messages.success(request, "Changes saved.")
                # Preserve reading period when navigating to the Reading tab
                if next_tab == "reading" and selected_reading_period:
                    return redirect(f"{reverse('edit_submission', args=[submission.id])}?tab={next_tab}&reading_period={selected_reading_period}")
                return redirect(f"{reverse('edit_submission', args=[submission.id])}?tab={next_tab}")
            elif is_autosave and next_tab in tab_keys:
                if next_tab == "reading" and selected_reading_period:
                    return redirect(f"{reverse('edit_submission', args=[submission.id])}?tab={next_tab}&reading_period={selected_reading_period}")
                return redirect(f"{reverse('edit_submission', args=[submission.id])}?tab={next_tab}")

    projects = submission.smea_projects.prefetch_related("activities").all()
    timeline_entries = list(submission.timeline.all()[:10])
    school_profile = getattr(school, "profile", None)
    school_profile_strands = ", ".join(school_profile.strands) if getattr(school_profile, "strands", None) else ""
    # Compute SHS selected/unselected strand prefixes for UI filtering (Grade 11/12 specialized subjects)
    try:
        raw_selected = set(getattr(school_profile, "strands", []) or [])
    except Exception:
        raw_selected = set()
    code_to_prefix = {c: p for (c, _label, p) in smea_constants.SHS_STRANDS}
    code_to_label = {c: l for (c, l, _p) in smea_constants.SHS_STRANDS}
    label_to_code = {l: c for (c, l, _p) in smea_constants.SHS_STRANDS}
    # Normalize selections: allow either codes (e.g., 'stem') or labels (e.g., 'STEM')
    selected_codes = set()
    for item in raw_selected:
        if item in code_to_prefix:
            selected_codes.add(item)
        elif item in label_to_code:
            selected_codes.add(label_to_code[item])
    shs_selected_prefixes = [code_to_prefix[c] for c in selected_codes if c in code_to_prefix]
    shs_unselected_prefixes = [p for (c, _l, p) in smea_constants.SHS_STRANDS if c not in selected_codes]
    shs_selected_labels = [code_to_label[c] for c in selected_codes if c in code_to_label]

    expected_timings = EXPECTED_TIMINGS_BY_QUARTER.get(submission.period.quarter_tag, [])

    # Add grade span information for reading assessment tables
    grade_span_start, grade_span_end = _resolve_grade_span(school)
    school_grades = grade_numbers_for_school(school) if school else []
    
    # Determine which CRLA grades to show (1-3 are the CRLA grades)
    crla_grades = [g for g in [1, 2, 3] if g in school_grades] if school_grades else [1, 2, 3]
    
    # Determine which PHILIRI grades to show
    # Elementary: 4-6, Junior High: 7-9, Senior High: 10
    philiri_elementary_grades = [g for g in [4, 5, 6] if g in school_grades] if school_grades else []
    # Include Grade 10 with the junior high grouping so the matrix renders its inputs
    philiri_junior_grades = [g for g in [7, 8, 9, 10] if g in school_grades] if school_grades else []
    philiri_senior_grades = [g for g in [10] if g in school_grades] if school_grades else []
    
    slp_rows_queryset = list(slp_formset.queryset)
    slp_dnme_summary = build_slp_dnme_summary(slp_rows_queryset)
    slp_outstanding_summary = build_slp_outstanding_summary(slp_rows_queryset)
    slp_dnme_recommendations = build_slp_dnme_recommendations(slp_rows_queryset)

    # Compute dynamic progress width for current tab
    try:
        current_index = next((i for i, t in enumerate(tabs) if t["key"] == current_tab), 0)
    except Exception:
        current_index = 0
    denom = max(1, len(tabs) - 1)
    progress_width = int(round((current_index / denom) * 100)) if denom else 100

    ctx = {
        "submission": submission,
        "timeline_entries": timeline_entries,
        "projects": projects,
        "tabs": tabs,
        "current_tab": current_tab,
        "can_edit": can_edit,
        "can_submit": can_submit,
        "pct_formset": pct_formset,
        "slp_formset": slp_formset,
        "slp_top_dnme_formset": slp_top_dnme_formset,
        "slp_top_outstanding_formset": slp_top_outstanding_formset,
        "reading_crla_formset": reading_crla_formset,
        "reading_philiri_formset": reading_philiri_formset,
        "reading_intervention_formset": reading_intervention_formset,
        "reading_crla_new_formset": reading_crla_new_formset,
        "reading_philiri_new_formset": reading_philiri_new_formset,
        "reading_interventions_new_formset": reading_interventions_new_formset,
        "selected_reading_period": selected_reading_period,
        "rma_row_formset": rma_row_formset,
        "rma_intervention_formset": rma_intervention_formset,
        "supervision_formset": supervision_formset,
        "signatories_form": signatories_form,
        "adm_header_form": adm_header_form,
        "adm_formset": adm_formset,
        "adm_is_offered": adm_is_offered,
        "projects_formset": projects_formset,
        "activity_formsets": activity_formsets,
        "expected_timings": json.dumps(expected_timings),
        "expected_timings_json": json.dumps(expected_timings),
        "grade_span_label": school.grade_span_label if school else "",
        "school_profile": school_profile,
        "school_profile_strands": school_profile_strands,
    # JSON for client-side hiding of unselected specializations
    "shs_selected_prefixes_json": json.dumps(shs_selected_prefixes),
    "shs_unselected_prefixes_json": json.dumps(shs_unselected_prefixes),
    "shs_selected_labels": shs_selected_labels,
    "shs_selected_labels_join": ", ".join(shs_selected_labels) if shs_selected_labels else "",
        "crla_grades": crla_grades,
        "philiri_elementary_grades": philiri_elementary_grades,
        "philiri_junior_grades": philiri_junior_grades,
        "philiri_senior_grades": philiri_senior_grades,
        "school_grades": school_grades,
        "slp_dnme_summary": slp_dnme_summary,
        "slp_dnme_recommendations": slp_dnme_recommendations,
        "slp_outstanding_summary": slp_outstanding_summary,
    # SHS strands: bulk actions removed; School Profile governs defaults
        # Helper list for template condition (avoid parentheses in template logic)
        "shs_grades": ["Grade 11", "Grade 12"],
        # Provide tabs JSON for dynamic JS ordering
        "tabs_json": json.dumps(tabs),
        "progress_width": progress_width,
        # Reading difficulties serialized storage
        "reading_difficulties_json_dump": json.dumps(submission.data.get('reading_difficulties_json', [])),
        "reading_difficulties_json": submission.data.get('reading_difficulties_json', []),
        # RMA structured difficulties storage (Pre-Test/Q3, EOSY/Q1)
        "rma_pretest_json_dump": json.dumps(submission.data.get('rma_pretest_json', [])),
        "rma_eosy_json_dump": json.dumps(submission.data.get('rma_eosy_json', [])),
        # Provide simple grade range for Reading Difficulties builder
    # Provide only Grades 1-10 actually offered by the school for Reading Difficulties builder
    "reading_grade_range": [g for g in school_grades if 1 <= g <= 10],
    }
    return render(request, "submissions/edit_submission.html", ctx)


@login_required
@require_school_head(submission_kwarg="submission_id")
def add_project(request, submission_id, submission_obj=None):
    submission = submission_obj or get_object_or_404(Submission, pk=submission_id)

    if not submission.is_editable_by_school():
        raise PermissionDenied("Returned or draft reports only can be edited.")

    if request.method == "POST":
        form = SMEAProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.submission = submission
            project.save()
            messages.success(request, "Project added.")
            return redirect("edit_submission", submission_id=submission.pk)
    else:
        form = SMEAProjectForm()

    return render(request, "submissions/add_project.html", {"form": form, "submission": submission})


@login_required
def add_activity(request, project_id):
    project = get_object_or_404(
        SMEAProject.objects.select_related("submission", "submission__school"),
        pk=project_id,
    )
    if not account_services.user_is_school_head(request.user, project.submission.school):
        raise PermissionDenied("SchoolHead role required for this submission.")
    if not project.submission.is_editable_by_school():
        raise PermissionDenied("Returned or draft reports only can be edited.")

    if request.method == "POST":
        form = SMEAActivityRowForm(request.POST)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.project = project
            activity.save()
            messages.success(request, "Activity added.")
            return redirect("edit_submission", submission_id=project.submission.pk)
    else:
        form = SMEAActivityRowForm()

    return render(
        request,
        "submissions/add_activity.html",
        {
            "form": form,
            "project": project,
        },
    )


@login_required
@require_school_head(submission_kwarg="submission_id")
def delete_attachment(request, submission_id, attachment_id, submission_obj=None):
    submission = submission_obj or get_object_or_404(Submission, pk=submission_id)
    attachment = get_object_or_404(SubmissionAttachment, pk=attachment_id, submission=submission)

    if request.method == "POST":
        attachment.delete()
        messages.info(request, "Attachment removed.")
        return redirect("edit_submission", submission_id=submission.pk)

    cancel_href = reverse("edit_submission", kwargs={"submission_id": submission.pk})
    return render(
        request,
        "submissions/confirm_delete.html",
        {
            "what": attachment.original_name,
            "cancel_href": cancel_href,
        },
    )


@login_required
def review_queue(request, section_code):
    section = get_object_or_404(Section, code__iexact=section_code)
    user = request.user

    is_section_admin = account_services.user_is_section_admin(user, section)
    is_psds = account_services.user_is_psds(user)
    is_sgod_admin = account_services.user_is_sgod_admin(user)

    if not (is_section_admin or is_psds or is_sgod_admin):
        raise PermissionDenied("Reviewer role required.")

    tab = request.GET.get("tab", "pending")
    status_map = {
        "pending": Submission.Status.SUBMITTED,
        "returned": Submission.Status.RETURNED,
        "noted": Submission.Status.NOTED,
    }
    status = status_map.get(tab, Submission.Status.SUBMITTED)

    base_qs = (
        account_scope.scope_submissions(user)
        .filter(form_template__section=section)
        .select_related("school", "form_template", "period")
        .order_by("-submitted_at", "-updated_at")
    )

    # Handle separate school year and quarter filters
    school_year = request.GET.get("school_year")
    quarter = request.GET.get("quarter")
    
    if school_year:
        base_qs = base_qs.filter(period__school_year_start=school_year)
    
    if quarter:
        base_qs = base_qs.filter(period__quarter_tag=quarter)

    # Legacy period_id filter support (for backwards compatibility)
    period_id = request.GET.get("period_id")
    if period_id:
        base_qs = base_qs.filter(period_id=period_id)

    search_query = request.GET.get("q", "").strip()
    if search_query:
        base_qs = base_qs.filter(
            Q(school__name__icontains=search_query)
            | Q(form_template__title__icontains=search_query)
        )

    submissions = base_qs.filter(status=status)

    tab_counts = {
        key: base_qs.filter(status=value).count()
        for key, value in status_map.items()
    }

    # Get available school years and quarters for filters
    available_periods = Period.objects.filter(is_active=True).order_by("-school_year_start", "-display_order")
    available_school_years = sorted(set(p.school_year_start for p in available_periods), reverse=True)
    available_quarters = [
        ("Q1", "1st Quarter"),
        ("Q2", "2nd Quarter"), 
        ("Q3", "3rd Quarter"),
        ("Q4", "4th Quarter"),
    ]

    selected_period = None
    if period_id:
        try:
            selected_period = Period.objects.get(pk=period_id)
        except Period.DoesNotExist:
            selected_period = None

    quick_stats = {}
    reviewer_role = (
        is_section_admin
        or is_psds
        or is_sgod_admin
    )
    if reviewer_role:
        today = timezone.localdate()
        week_start = today - datetime.timedelta(days=today.weekday())
        quick_stats = {
            "pending_total": tab_counts.get("pending", 0),
            "submitted_today": base_qs.filter(status=Submission.Status.SUBMITTED, submitted_at__date=today).count(),
            "returned_total": tab_counts.get("returned", 0),
            "noted_this_week": base_qs.filter(status=Submission.Status.NOTED, noted_at__date__gte=week_start).count(),
        }

    ctx = {
        "section": section,
        "tab": tab,
        "submissions": submissions,
        "periods": Period.objects.order_by("-school_year_start", "-display_order"),
        "period_id": period_id or "",
        "search_query": search_query,
        "selected_period": selected_period,
        "tab_counts": tab_counts,
        "district_dashboard_url": reverse("district_submission_gaps"),
        "smme_dashboard_url": reverse("smme_kpi_dashboard"),
        "quick_stats": quick_stats,
        # New filter data
        "available_school_years": available_school_years,
        "available_quarters": available_quarters,
        "selected_school_year": school_year,
        "selected_quarter": quarter,
    }
    return render(request, "submissions/review_queue.html", ctx)


@login_required
@require_section_admin(submission_kwarg="submission_id")
def review_detail(request, submission_id, submission_obj=None):
    project_prefetch = Prefetch(
        "smea_projects",
        queryset=SMEAProject.objects.prefetch_related("activities").order_by("id"),
    )
    slp_llc_prefetch = Prefetch(
        "slp_llc_entries",
        queryset=Form1SLPLLCEntry.objects.order_by("order"),
    )
    slp_top_dnme_prefetch = Prefetch(
        "form1_slp_top_dnme",
        queryset=Form1SLPTopDNME.objects.order_by("position"),
    )
    slp_top_outstanding_prefetch = Prefetch(
        "form1_slp_top_outstanding",
        queryset=Form1SLPTopOutstanding.objects.order_by("position"),
    )
    pct_row_prefetch = Prefetch(
        "form1_pct__rows",
        queryset=Form1PctRow.objects.order_by("area"),
    )
    legacy_crla_prefetch = Prefetch(
        "form1_crla",
        queryset=Form1ReadingCRLA.objects.order_by("level", "timing", "subject", "band"),
    )
    legacy_philiri_prefetch = Prefetch(
        "form1_philiri",
        queryset=Form1ReadingPHILIRI.objects.order_by("level", "timing", "language"),
    )
    legacy_reading_interventions_prefetch = Prefetch(
        "form1_reading_interventions",
        queryset=Form1ReadingIntervention.objects.order_by("order"),
    )
    crla_level_order = Case(
        When(level="low_emerging", then=1),
        When(level="high_emerging", then=2),
        When(level="developing", then=3),
        When(level="transitioning", then=4),
        default=99,
        output_field=IntegerField(),
    )
    philiri_level_order = Case(
        When(level="frustration", then=1),
        When(level="instructional", then=2),
        When(level="independent", then=3),
        default=99,
        output_field=IntegerField(),
    )
    assessment_period_order = Case(
        When(period="bosy", then=0),
        When(period="mosy", then=1),
        When(period="eosy", then=2),
        default=99,
        output_field=IntegerField(),
    )
    matrix_crla_prefetch = Prefetch(
        "crla_assessments",
        queryset=ReadingAssessmentCRLA.objects.annotate(
            period_order=assessment_period_order,
            level_order=crla_level_order,
        ).order_by("period_order", "level_order"),
    )
    matrix_philiri_prefetch = Prefetch(
        "philiri_assessments",
        queryset=ReadingAssessmentPHILIRI.objects.annotate(
            period_order=assessment_period_order,
            level_order=philiri_level_order,
        ).order_by("period_order", "level_order"),
    )
    matrix_interventions_prefetch = Prefetch(
        "reading_interventions_new",
        queryset=ReadingInterventionNew.objects.order_by("order"),
    )
    rma_grade_order = Case(
        When(grade_label="k", then=0),
        When(grade_label="g1", then=1),
        When(grade_label="g2", then=2),
        When(grade_label="g3", then=3),
        When(grade_label="g4", then=4),
        When(grade_label="g5", then=5),
        When(grade_label="g6", then=6),
        When(grade_label="g7", then=7),
        When(grade_label="g8", then=8),
        When(grade_label="g9", then=9),
        When(grade_label="g10", then=10),
        default=99,
        output_field=IntegerField(),
    )
    rma_rows_prefetch = Prefetch(
        "form1_rma_rows",
        queryset=Form1RMARow.objects.annotate(order_key=rma_grade_order).order_by("order_key", "id"),
    )
    rma_interventions_prefetch = Prefetch(
        "form1_rma_interventions",
        queryset=Form1RMAIntervention.objects.order_by("order"),
    )
    supervision_prefetch = Prefetch(
        "form1_supervision_rows",
        queryset=Form1SupervisionRow.objects.order_by("grade_label", "id"),
    )
    adm_rows_prefetch = Prefetch(
        "form1_adm_rows",
        queryset=Form1ADMRow.objects.order_by("id"),
    )

    submission_qs = (
        Submission.objects.select_related(
            "school",
            "form_template",
            "period",
            "form1_pct",
            "form1_slp_analysis",
            "form1_signatories",
            "form1_adm_header",
        )
        .prefetch_related(
            "timeline__actor",
            "attachments",
            project_prefetch,
            slp_llc_prefetch,
            slp_top_dnme_prefetch,
            slp_top_outstanding_prefetch,
            pct_row_prefetch,
            legacy_crla_prefetch,
            legacy_philiri_prefetch,
            legacy_reading_interventions_prefetch,
            matrix_crla_prefetch,
            matrix_philiri_prefetch,
            matrix_interventions_prefetch,
            rma_rows_prefetch,
            rma_interventions_prefetch,
            supervision_prefetch,
            adm_rows_prefetch,
        )
    )
    submission = submission_obj or get_object_or_404(
        submission_qs,
        pk=submission_id,
    )

    review_form = SubmissionReviewForm()

    if request.method == "POST":
        review_form = SubmissionReviewForm(request.POST)
        if review_form.is_valid():
            action = review_form.cleaned_data["action"]
            remarks = review_form.cleaned_data["remarks"]
            try:
                if action == SubmissionReviewForm.ACTION_NOTE:
                    submission.mark_noted(request.user, remarks)
                    messages.success(request, "Submission marked as noted.")
                else:
                    submission.mark_returned(request.user, remarks)
                    messages.warning(request, "Submission returned to the school.")
            except ValidationError as exc:
                review_form.add_error(None, exc.message)
            else:
                return redirect("review_queue", section_code=submission.form_template.section.code)

    projects = list(submission.smea_projects.all())
    attachments = list(submission.attachments.all())
    school_profile = getattr(submission.school, "profile", None)
    # --- Clean & normalize SHS strands for display (avoid serialized noise) ---
    def _clean_strands(raw):
        if not raw:
            return []
        valid_codes = {c for (c, _l, _p) in smea_constants.SHS_STRANDS}
        label_for_code = {c: l for (c, l, _p) in smea_constants.SHS_STRANDS}
        # Accept either codes or labels; ignore malformed entries containing excessive quoting/brackets
        cleaned_codes = []
        for item in raw:
            if not item:
                continue
            s = str(item).strip()
            if any(ch in s for ch in ['\\\\\\\\', '[', ']', '""', "']"]):
                # Skip obviously corrupted serialized artifacts
                continue
            lower = s.lower()
            if lower in valid_codes:
                cleaned_codes.append(lower)
            else:
                # Match by label (case-insensitive)
                for code, label in label_for_code.items():
                    if lower == label.lower():
                        cleaned_codes.append(code)
                        break
        # De-duplicate preserving original order
        seen = set()
        ordered = []
        for code in cleaned_codes:
            if code not in seen:
                seen.add(code)
                ordered.append(code)
        return [label_for_code[c] for c in ordered]
    raw_strands = getattr(school_profile, 'strands', None) if school_profile else None
    school_profile_strands_list = _clean_strands(raw_strands)
    school_profile_strands = ", ".join(school_profile_strands_list)

    slp_rows = list(ordered_slp_rows(submission))
    # Contextualize SLP: limit to school's grade span and SHS-offered specializations
    try:
        allowed_grades = set(grade_numbers_for_school(submission.school))
    except Exception:
        allowed_grades = None
    # Build SHS strand prefix allow-list if the school has declared strands
    try:
        profile = getattr(submission.school, "profile", None)
        raw_strands = set(getattr(profile, "strands", []) or [])
        code_to_prefix = {c: p for (c, _l, p) in smea_constants.SHS_STRANDS}
        label_to_code = {l: c for (c, l, _p) in smea_constants.SHS_STRANDS}
        selected_codes = set()
        for item in raw_strands:
            if item in code_to_prefix:
                selected_codes.add(item)
            elif item in label_to_code:
                selected_codes.add(label_to_code[item])
        allowed_prefixes = {code_to_prefix[c] for c in selected_codes if c in code_to_prefix}
        all_spec_prefixes = tuple(p for (_c, _l, p) in smea_constants.SHS_STRANDS)
    except Exception:
        allowed_prefixes = set()
        all_spec_prefixes = tuple()

    def _gnum(label: str):
        return smea_constants.GRADE_LABEL_TO_NUMBER.get(label)

    def _is_specialized(code: str) -> bool:
        sc = (code or '').strip()
        return any(sc.startswith(p) for p in all_spec_prefixes)

    filtered_slp_rows = []
    for r in slp_rows:
        # Respect offered flag
        if hasattr(r, 'is_offered') and not r.is_offered:
            continue
        gnum = _gnum(r.grade_label)
        if allowed_grades is not None and gnum is not None and gnum not in allowed_grades:
            continue
        # If the school declared SHS strands, restrict specialized G11/G12 subjects to those strands only
        if gnum in (11, 12) and _is_specialized(r.subject) and allowed_prefixes:
            if not any((r.subject or '').startswith(p) for p in allowed_prefixes):
                continue
        filtered_slp_rows.append(r)

    slp_rows = filtered_slp_rows
    slp_dnme_summary = build_slp_dnme_summary(slp_rows)
    slp_outstanding_summary = build_slp_outstanding_summary(slp_rows)
    slp_dnme_recommendations = build_slp_dnme_recommendations(slp_rows)
    slp_llc_entries = list(submission.slp_llc_entries.all())
    slp_top_dnme = list(submission.form1_slp_top_dnme.all())
    slp_top_outstanding = list(submission.form1_slp_top_outstanding.all())
    slp_analysis = getattr(submission, "form1_slp_analysis", None)

    pct_header = getattr(submission, "form1_pct", None)
    pct_rows = list(pct_header.rows.all()) if pct_header else []

    legacy_crla_entries = list(submission.form1_crla.all())
    legacy_philiri_entries = list(submission.form1_philiri.all())
    legacy_reading_interventions = list(submission.form1_reading_interventions.all())

    matrix_crla_entries = list(submission.crla_assessments.all())
    matrix_philiri_entries = list(submission.philiri_assessments.all())
    matrix_reading_interventions = list(submission.reading_interventions_new.all())

    # --- Contextual RMA rows: restrict to school's grade span & ordered lowest→highest ---
    rma_rows_all = list(submission.form1_rma_rows.all())
    try:
        allowed_grade_numbers = set(grade_numbers_for_school(submission.school))
    except Exception:
        allowed_grade_numbers = None
    rma_code_to_num = {"k": 0, "g1": 1, "g2": 2, "g3": 3, "g4": 4, "g5": 5, "g6": 6, "g7": 7, "g8": 8, "g9": 9, "g10": 10}
    def _include_rma_row(row):
        num = rma_code_to_num.get(row.grade_label)
        if num is None:
            return False
        if allowed_grade_numbers is not None and num not in allowed_grade_numbers:
            return False
        return True
    rma_rows = sorted([r for r in rma_rows_all if _include_rma_row(r)], key=lambda r: rma_code_to_num.get(r.grade_label, 999))
    rma_interventions = list(submission.form1_rma_interventions.all())
    supervision_rows = list(submission.form1_supervision_rows.all())
    adm_rows = list(submission.form1_adm_rows.all())
    adm_header = getattr(submission, "form1_adm_header", None)
    signatories = getattr(submission, "form1_signatories", None)

    ctx = {
        "submission": submission,
        "projects": projects,
        "attachments": attachments,
        "timeline_entries": submission.timeline.all(),
        "review_form": review_form,
        "school_profile": school_profile,
        "school_profile_strands": school_profile_strands,
        "slp_rows": slp_rows,
        "slp_llc_entries": slp_llc_entries,
        "pct_rows": pct_rows,
        "slp_dnme_summary": slp_dnme_summary,
        "slp_dnme_recommendations": slp_dnme_recommendations,
        "slp_outstanding_summary": slp_outstanding_summary,
        "legacy_crla_entries": legacy_crla_entries,
        "legacy_philiri_entries": legacy_philiri_entries,
        "legacy_reading_interventions": legacy_reading_interventions,
        "matrix_crla_entries": matrix_crla_entries,
        "matrix_philiri_entries": matrix_philiri_entries,
        "matrix_reading_interventions": matrix_reading_interventions,
        "rma_rows": rma_rows,
        "rma_interventions": rma_interventions,
        "supervision_rows": supervision_rows,
        "adm_rows": adm_rows,
        "adm_header": adm_header,
        "signatories": signatories,
    }
    return render(request, "submissions/review_detail.html", ctx)



@login_required
def review_submission_tabs(request, submission_id):
    submission_qs = account_scope.scope_submissions(request.user).select_related("school", "form_template__section", "period")
    submission_qs = submission_qs.select_related("form1_pct", "form1_slp_analysis", "form1_signatories")
    submission_qs = submission_qs.prefetch_related(
        "timeline__actor",
        "smea_projects__activities",
        "form1_pct__rows",
        "form1_slp_rows",
        "form1_slp_top_dnme",
        "form1_slp_top_outstanding",
        "form1_crla",
        "form1_philiri",
        "form1_reading_interventions",
        "form1_rma_rows",
        "form1_rma_interventions",
        "form1_supervision_rows",
        "form1_adm_rows",
        "attachments",
    )

    submission = get_object_or_404(submission_qs, pk=submission_id)
    section = submission.form_template.section

    if not (
        account_services.user_is_section_admin(request.user, section)
        or account_services.user_is_psds(request.user)
    ):
        raise PermissionDenied("Reviewer role required.")

    tabs = _submission_tabs(submission)
    tab_keys = [tab["key"] for tab in tabs]
    current_tab = request.GET.get("tab") or tab_keys[0]
    if current_tab not in tab_keys:
        current_tab = tab_keys[0]

    timeline_entries = submission.timeline.all()
    projects = submission.smea_projects.all()
    pct_header = getattr(submission, "form1_pct", None)
    pct_rows = list(pct_header.rows.all()) if pct_header else []

    slp_rows = list(ordered_slp_rows(submission))
    # Contextualize SLP similarly in tabs view
    try:
        allowed_grades = set(grade_numbers_for_school(submission.school))
    except Exception:
        allowed_grades = None
    try:
        profile = getattr(submission.school, 'profile', None)
        raw_strands = set(getattr(profile, 'strands', []) or [])
        code_to_prefix = {c: p for (c, _l, p) in smea_constants.SHS_STRANDS}
        label_to_code = {l: c for (c, l, _p) in smea_constants.SHS_STRANDS}
        selected_codes = set()
        for item in raw_strands:
            if item in code_to_prefix:
                selected_codes.add(item)
            elif item in label_to_code:
                selected_codes.add(label_to_code[item])
        allowed_prefixes = {code_to_prefix[c] for c in selected_codes if c in code_to_prefix}
        all_spec_prefixes = tuple(p for (_c, _l, p) in smea_constants.SHS_STRANDS)
    except Exception:
        allowed_prefixes = set()
        all_spec_prefixes = tuple()

    def _gnum2(label: str):
        return smea_constants.GRADE_LABEL_TO_NUMBER.get(label)

    def _is_spec2(code: str) -> bool:
        sc = (code or '').strip()
        return any(sc.startswith(p) for p in all_spec_prefixes)

    slp_rows = [
        r for r in slp_rows
        if (not hasattr(r, 'is_offered') or r.is_offered)
        and (allowed_grades is None or (_gnum2(r.grade_label) is None or _gnum2(r.grade_label) in allowed_grades))
        and (not (_gnum2(r.grade_label) in (11, 12) and _is_spec2(r.subject) and allowed_prefixes and not any((r.subject or '').startswith(p) for p in allowed_prefixes)))
    ]

    slp_dnme_summary = build_slp_dnme_summary(slp_rows)
    slp_outstanding_summary = build_slp_outstanding_summary(slp_rows)
    slp_dnme_recommendations = build_slp_dnme_recommendations(slp_rows)
    slp_analysis = getattr(submission, "form1_slp_analysis", None)
    slp_top_dnme = list(submission.form1_slp_top_dnme.all())
    slp_top_outstanding = list(submission.form1_slp_top_outstanding.all())

    reading_crla = list(submission.form1_crla.all())
    reading_philiri = list(submission.form1_philiri.all())
    reading_interventions = list(submission.form1_reading_interventions.all())
    school_profile = getattr(submission.school, "profile", None)
    # Clean strands again for tabs view
    def _clean_strands_tabs(raw):
        if not raw:
            return []
        valid_codes = {c for (c, _l, _p) in smea_constants.SHS_STRANDS}
        label_for_code = {c: l for (c, l, _p) in smea_constants.SHS_STRANDS}
        cleaned_codes = []
        for item in raw:
            if not item:
                continue
            s = str(item).strip()
            if any(ch in s for ch in ['\\\\\\\\', '[', ']', '""', "']"]):
                continue
            lower = s.lower()
            if lower in valid_codes:
                cleaned_codes.append(lower)
            else:
                for code, label in label_for_code.items():
                    if lower == label.lower():
                        cleaned_codes.append(code)
                        break
        seen = set(); ordered=[]
        for code in cleaned_codes:
            if code not in seen:
                seen.add(code); ordered.append(code)
        return ", ".join(label_for_code[c] for c in ordered)
    school_profile_strands = _clean_strands_tabs(getattr(school_profile, 'strands', None))

    # Contextual + ordered RMA rows for tabs view
    rma_rows_all = list(submission.form1_rma_rows.all())
    try:
        allowed_grade_numbers = set(grade_numbers_for_school(submission.school))
    except Exception:
        allowed_grade_numbers = None
    rma_code_to_num = {"k": 0, "g1": 1, "g2": 2, "g3": 3, "g4": 4, "g5": 5, "g6": 6, "g7": 7, "g8": 8, "g9": 9, "g10": 10}
    def _include_rma_row(row):
        num = rma_code_to_num.get(row.grade_label)
        if num is None:
            return False
        if allowed_grade_numbers is not None and num not in allowed_grade_numbers:
            return False
        return True
    rma_rows = sorted([r for r in rma_rows_all if _include_rma_row(r)], key=lambda r: rma_code_to_num.get(r.grade_label, 999))
    rma_interventions = list(submission.form1_rma_interventions.all())

    supervision_rows = list(submission.form1_supervision_rows.all())
    signatories = getattr(submission, "form1_signatories", None)

    adm_rows = list(submission.form1_adm_rows.all())  # Show ADM rows for all schools
    adm_header = getattr(submission, "form1_adm_header", None)

    attachments = list(submission.attachments.all())

    ctx = {
        "submission": submission,
        "tabs": tabs,
        "current_tab": current_tab,
        "timeline_entries": timeline_entries,
        "projects": projects,
        "pct_header": pct_header,
        "pct_rows": pct_rows,
        "slp_rows": slp_rows,
        "slp_dnme_recommendations": slp_dnme_recommendations,
        "slp_dnme_summary": slp_dnme_summary,
        "slp_outstanding_summary": slp_outstanding_summary,
        "slp_analysis": slp_analysis,
        "slp_top_dnme": slp_top_dnme,
        "slp_top_outstanding": slp_top_outstanding,
        "reading_crla": reading_crla,
        "reading_philiri": reading_philiri,
        "reading_interventions": reading_interventions,
        "rma_rows": rma_rows,
        "rma_interventions": rma_interventions,
        "supervision_rows": supervision_rows,
        "signatories": signatories,
        "adm_rows": adm_rows,
        "adm_header": adm_header,
        "attachments": attachments,
        "is_section_admin": account_services.user_is_section_admin(request.user, section),
        "is_psds": account_services.user_is_psds(request.user),
        "grade_span_label": submission.school.grade_span_label if submission.school else "",
        "review_url": reverse("review_detail", args=[submission.id]),
        "queue_url": reverse("review_queue", args=[section.code]),
        "district_dashboard_url": reverse("district_submission_gaps"),
        "smme_dashboard_url": reverse("smme_kpi_dashboard"),
        "school_profile": school_profile,
        "school_profile_strands": school_profile_strands,
        "export_urls": {
            "csv": f"{reverse('review_submission_export', args=[submission.id, 'csv'])}?tab={current_tab}",
            "xlsx": f"{reverse('review_submission_export', args=[submission.id, 'xlsx'])}?tab={current_tab}",
        },
    }
    return render(request, "submissions/review_tabs.html", ctx)


@login_required
def review_submission_export(request, submission_id, file_format):
    allowable_formats = {"csv", "xlsx"}
    file_format = file_format.lower()
    if file_format not in allowable_formats:
        raise PermissionDenied("Unsupported export format.")

    submission_qs = account_scope.scope_submissions(request.user).select_related("school", "period", "form_template__section")
    submission = get_object_or_404(submission_qs, pk=submission_id)
    section = submission.form_template.section

    if not (account_services.user_is_section_admin(request.user, section) or account_services.user_is_psds(request.user)):
        raise PermissionDenied("Reviewer role required.")

    tab = request.GET.get("tab", "slp")
    try:
        export_bundle = submission_exports.build_export_for_tab(submission, tab)
    except Exception as e:
        messages.error(request, f"Error generating export: {str(e)}")
        return redirect('submission_detail', submission_id=submission_id)

    # Render and return the export file
    if file_format == "csv":
        payload = submission_exports.render_export_to_csv(export_bundle)
        response = HttpResponse(payload, content_type="text/csv")
        filename = f"{export_bundle.filename_prefix}-{tab}.csv"
        response["Content-Disposition"] = f"attachment; filename=\"{filename}\""
        return response
    elif file_format == "xlsx":
        try:
            payload = submission_exports.render_export_to_xlsx(export_bundle)
        except ImportError as exc:
            messages.error(request, str(exc))
            return redirect('submission_detail', submission_id=submission_id)
        response = HttpResponse(
            payload,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        filename = f"{export_bundle.filename_prefix}-{tab}.xlsx"
        response["Content-Disposition"] = f"attachment; filename=\"{filename}\""
        return response

# ---- SLP (School Learning Progress) Views ----

@login_required
def slp_wizard(request, submission_id):
    """
    Handle the SLP form wizard steps:
    1. Proficiency Data Entry
    2. LLC Analysis
    3. Root Causes
    4. Best Practices
    5. Review
    """
    submission = get_object_or_404(Submission, pk=submission_id)
    current_step = int(request.POST.get('step', 1))
    
    # Get or create SLP analysis
    analysis, _ = Form1SLPAnalysis.objects.get_or_create(submission=submission)
    
    if request.method == 'POST':
        if current_step == 1:
            # Handle proficiency data
            formset = forms.modelformset_factory(Form1SLPRow)(
                request.POST, queryset=submission.form1_slp_rows.all()
            )
            if formset.is_valid():
                formset.save()
                return redirect('slp_wizard', submission_id=submission_id, step=2)
                
        elif current_step == 2:
            # Handle LLC entries
            llc_formset = SLPLLCEntryFormSet(
                request.POST,
                queryset=Form1SLPLLCEntry.objects.filter(submission=submission)
            )
            if llc_formset.is_valid():
                instances = llc_formset.save(commit=False)
                for i, instance in enumerate(instances, 1):
                    instance.submission = submission
                    instance.order = i
                    instance.save()
                return redirect('slp_wizard', submission_id=submission_id, step=3)
                
        elif current_step == 3:
            # Handle root causes
            form = SLPAnalysisForm(request.POST, instance=analysis)
            if form.is_valid():
                form.save()
                return redirect('slp_wizard', submission_id=submission_id, step=4)
                
        elif current_step == 4:
            # Handle best practices
            form = SLPAnalysisForm(request.POST, instance=analysis)
            if form.is_valid():
                form.save()
                return redirect('slp_wizard', submission_id=submission_id, step=5)
                
        elif current_step == 5:
            # Final submission
            try:
                with transaction.atomic():
                    # Validate all required data is present
                    if not submission.form1_slp_rows.exists():
                        raise ValidationError("Proficiency data is required")
                    if not Form1SLPLLCEntry.objects.filter(submission=submission).count() == 3:
                        raise ValidationError("Three LLC entries are required")
                    
                    # Calculate rankings
                    top_dnme = (Form1SLPRow.objects.filter(submission=submission)
                               .values('grade_label')
                               .annotate(dnme_count=Sum('dnme'))
                               .order_by('-dnme_count')[:5])
                               
                    top_outstanding = (Form1SLPRow.objects.filter(submission=submission)
                                     .values('grade_label')
                                     .annotate(o_count=Sum('o'))
                                     .order_by('-o_count')[:5])
                    
                    # Mark submission as complete
                    submission.status = Submission.Status.SUBMITTED
                    submission.save()
                    
                    messages.success(request, "SLP form completed successfully!")
                    return redirect('submission_detail', submission_id=submission_id)
                    
            except ValidationError as e:
                messages.error(request, str(e))
                return redirect('slp_wizard', submission_id=submission_id, step=5)

    # Render the appropriate template based on current step
    context = {
        'submission': submission,
        'current_step': current_step,
    }
    
    if current_step == 1:
        formset = forms.modelformset_factory(Form1SLPRow)(
            queryset=submission.form1_slp_rows.all()
        )
        context['formset'] = formset
        
    elif current_step == 2:
        llc_formset = SLPLLCEntryFormSet(
            queryset=Form1SLPLLCEntry.objects.filter(submission=submission)
        )
        context['llc_formset'] = llc_formset
        
    elif current_step == 3:
        context['form'] = SLPAnalysisForm(instance=analysis)
        
    elif current_step == 4:
        context['form'] = SLPAnalysisForm(instance=analysis)
        
    elif current_step == 5:
        context.update({
            'rows': submission.form1_slp_rows.all(),
            'llc_entries': Form1SLPLLCEntry.objects.filter(submission=submission),
            'analysis': analysis,
        })
    
    return render(request, f'submissions/slp/step_{current_step}.html', context)

    filename = f"{export_bundle.filename_prefix}-{tab}.{file_format}"
    response = HttpResponse(payload, content_type=content_type)
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response
