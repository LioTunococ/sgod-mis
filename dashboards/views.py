from __future__ import annotations

import csv
import datetime
from collections import defaultdict
from typing import Iterable

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Max, F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse

from accounts import scope as account_scope
from accounts import services as account_services
from organizations.models import District, Section
from dashboards.performance import PerformanceMonitor
from submissions.models import (
    Form1SLPRow,
    FormTemplate,
    Period,
    Submission,
    SubmissionTimeline,
)


_COMPLETED_STATUSES = {
    Submission.Status.SUBMITTED,
    Submission.Status.NOTED,
}


def _extract_grade_number(label: str | None) -> int | None:
    if not label:
        return None
    label_lower = str(label).lower()
    if "kinder" in label_lower or label_lower.startswith("k"):
        return 0
    digits = "".join(ch for ch in label_lower if ch.isdigit())
    if digits:
        try:
            return int(digits)
        except ValueError:
            return None
    return None


@login_required
def school_home(request):
    user = request.user
    today = timezone.localdate()
    
    # Get selected school year, quarter, and section from query params
    selected_school_year = request.GET.get('school_year', '2025-2026')
    selected_quarter = request.GET.get('quarter', None)  # None means "All Quarters"
    selected_section_code = request.GET.get('section', None)  # None means auto-select first

    if account_services.user_is_sgod_admin(user):
        return redirect("division_overview")
    if account_services.user_is_psds(user):
        return redirect("smme_kpi_dashboard")
    section_codes_redirect = account_services.get_section_codes(user)
    if (
        account_services.user_is_section_admin(user)
        and not account_services.user_is_school_head(user)
        and section_codes_redirect
    ):
        return redirect("review_queue", section_code=section_codes_redirect[0])

    sections_qs = Section.objects.order_by("code")
    section_codes = account_services.allowed_section_codes(user)

    if section_codes and not account_services.user_is_school_head(user):
        sections_qs = sections_qs.filter(code__in=section_codes)

    sections = list(sections_qs)
    section_cards: list[dict[str, object]] = []
    first_section_code = None
    
    # Get school and drafts first (if school user)
    school = None
    drafts_by_section: dict[int, list] = defaultdict(list)
    
    if account_services.user_is_school_head(user):
        profile = getattr(user, "profile", None)
        school = getattr(profile, "school", None)
        
        if school:
            # Fetch all drafts with progress data
            draft_qs = (
                Submission.objects.filter(
                    school=school,
                    status__in=[Submission.Status.DRAFT, Submission.Status.RETURNED],
                )
                .select_related("form_template", "form_template__section", "period")
                .prefetch_related(
                    "smea_projects__activities",
                    "form1_slp_rows",
                )
                .order_by("-updated_at")
            )
            
            for submission in draft_qs:
                completion = submission.get_completion_summary()
                draft_data = {
                    'submission': submission,
                    'progress': completion['overall_progress'],
                    'sections': completion['sections'],
                    'completed_count': completion['completed_sections'],
                    'total_sections': completion['total_sections'],
                }
                section_id = submission.form_template.section_id
                drafts_by_section[section_id].append(draft_data)

    # Get all active periods (we'll match specific quarters to forms later)
    active_periods = list(
        Period.objects.filter(is_active=True)
        .order_by("-school_year_start", "display_order")
    )
    
    # Fallback to latest period if no active periods
    if not active_periods:
        active_periods = list(
            Period.objects.order_by("-school_year_start", "display_order")[:4]
        )

    if sections:
        section_ids = [section.id for section in sections]
        open_counts: dict[int, int] = defaultdict(int)
        due_dates: dict[int, datetime.date | None] = {}
        available_forms_by_section: dict[int, list] = defaultdict(list)
        # Track submitted/noted items to display on the portal
        submitted_items_by_section: dict[int, list] = defaultdict(list)
        
        active_forms = FormTemplate.objects.open_on(today).filter(
            section_id__in=section_ids
        ).select_related("section")
        
        # Preload existing submissions for this school and active periods so we can
        # 1) exclude them from the "Available Forms" list, and
        # 2) show them under a new "Submitted" section (pending review or noted)
        existing_submission_pairs: set[tuple[int, int]] = set()
        existing_submissions: list[Submission] = []
        if school and active_periods:
            existing_submissions = list(
                Submission.objects.filter(
                    school=school,
                    period__in=active_periods,
                    status__in=[
                        Submission.Status.DRAFT,
                        Submission.Status.RETURNED,
                        Submission.Status.SUBMITTED,
                        Submission.Status.NOTED,
                    ],
                )
                .select_related("form_template", "form_template__section", "period")
                .order_by("-updated_at")
            )
            existing_submission_pairs = {
                (s.form_template_id, s.period_id) for s in existing_submissions if s.period_id
            }

            # Group submitted/noted items by section for display
            for s in existing_submissions:
                if s.status in [Submission.Status.SUBMITTED, Submission.Status.NOTED]:
                    submitted_items_by_section[s.form_template.section_id].append(s)
        
        # Build available forms list and count per section
        for form in active_forms:
            # Match form's quarter_filter with appropriate Period
            matched_period = None
            if form.quarter_filter and active_periods:
                # Try to find a period with matching quarter_tag
                for period in active_periods:
                    if period.quarter_tag == form.quarter_filter:
                        matched_period = period
                        break

            # Fallback to first active period if no match
            if not matched_period and active_periods:
                matched_period = active_periods[0]

            # Exclude from "Available" if there is already a submission for this form+period
            if matched_period and (form.id, matched_period.id) not in existing_submission_pairs:
                open_counts[form.section_id] += 1
                available_forms_by_section[form.section_id].append({
                    'form_template': form,
                    'deadline': form.close_at,
                    'period': matched_period,  # Use matched period based on quarter_filter
                })
            if form.close_at:
                current_due = due_dates.get(form.section_id)
                if current_due is None or form.close_at < current_due:
                    due_dates[form.section_id] = form.close_at

        for section in sections:
            drafts_count = len(drafts_by_section.get(section.id, []))
            open_count = open_counts.get(section.id, 0)
            submitted_list = submitted_items_by_section.get(section.id, [])
            pending_count = sum(1 for s in submitted_list if s.status == Submission.Status.SUBMITTED)
            noted_count = sum(1 for s in submitted_list if s.status == Submission.Status.NOTED)
            
            # Always include section card to show all units (even with empty state)
            section_cards.append(
                {
                    "section": section,
                    "open_count": open_count,
                    "drafts_count": drafts_count,
                    "drafts": drafts_by_section.get(section.id, []),
                    "available_forms": available_forms_by_section.get(section.id, []),
                    "submitted": submitted_list,
                    "submitted_count": len(submitted_list),
                    "submitted_pending_count": pending_count,
                    "noted_count": noted_count,
                    "next_due": due_dates.get(section.id),
                }
            )

    open_forms_total = sum(card["open_count"] for card in section_cards)
    upcoming_deadlines = sorted(
        [card["next_due"] for card in section_cards if card["next_due"] is not None]
    )
    next_deadline = upcoming_deadlines[0] if upcoming_deadlines else None

    if section_cards:
        first_section_code = section_cards[0]["section"].code

    reviewer_access = (
        account_services.user_is_section_admin(user)
        or account_services.user_is_psds(user)
        or account_services.user_is_sgod_admin(user)
    )

    draft_submissions = []
    school_portal: dict[str, object] | None = None
    section_admin_summary: dict[str, int] | None = None
    section_admin_recent_actions = []
    if account_services.user_is_school_head(user) and school:
        # Collect all drafts from section cards for statistics
        for section_card in section_cards:
            draft_submissions.extend(section_card.get("drafts", []))
        
        school_profile = getattr(school, "profile", None)
        current_submission = (
            Submission.objects.filter(school=school)
            .select_related("form_template", "period")
            .prefetch_related("timeline__actor")
            .order_by("-updated_at")
            .first()
        )
        current_submission_timeline = []
        if current_submission:
            current_submission_timeline = list(
                current_submission.timeline.select_related("actor")[:6]
            )

        returned_qs = (
            Submission.objects.filter(
                school=school,
                status=Submission.Status.RETURNED,
            )
            .select_related("form_template", "period", "returned_by")
            .order_by("-updated_at")
        )
        outstanding_returns = list(returned_qs[:5])

        action_items = []
        seen_submission_ids: set[int] = set()
        for submission in outstanding_returns:
            action_items.append(
                {
                    "id": submission.id,
                    "title": submission.form_template.title,
                    "period": submission.period.label if submission.period else "",
                    "updated_at": submission.updated_at,
                    "note": submission.returned_remarks,
                    "status_code": submission.status,
                    "status_label": submission.get_status_display(),
                    "cta_label": "Review & resubmit",
                    "url": reverse("edit_submission", args=[submission.id]),
                }
            )
            seen_submission_ids.add(submission.id)
        for draft_item in draft_submissions:
            submission = draft_item['submission']
            if submission.id in seen_submission_ids:
                continue
            action_items.append(
                {
                    "id": submission.id,
                    "title": submission.form_template.title,
                    "period": submission.period.label if submission.period else "",
                    "updated_at": submission.updated_at,
                    "note": "",
                    "status_code": submission.status,
                    "status_label": submission.get_status_display(),
                    "cta_label": "Resume draft",
                    "url": reverse("edit_submission", args=[submission.id]),
                    "progress": draft_item['progress'],
                }
            )

        draft_only_count = sum(
            1 for draft_item in draft_submissions if draft_item['submission'].status == Submission.Status.DRAFT
        )
        
        # Calculate dashboard statistics
        all_submissions = Submission.objects.filter(school=school).select_related("form_template", "period")
        total_submitted = all_submissions.filter(status__in=[Submission.Status.SUBMITTED, Submission.Status.NOTED]).count()
        total_in_progress = all_submissions.filter(status__in=[Submission.Status.DRAFT, Submission.Status.RETURNED]).count()
        
        # Calculate average completion for in-progress forms
        avg_completion = 0
        if draft_submissions:
            avg_completion = sum(d['progress'] for d in draft_submissions) // len(draft_submissions)
        
        summary_metrics = {
            "returns": len(outstanding_returns),
            "drafts": draft_only_count,
            "open_forms": open_forms_total,
            "next_deadline": next_deadline,
            "total_submitted": total_submitted,
            "total_in_progress": total_in_progress,
            "avg_completion": avg_completion,
        }

        profile_prompt = None
        if not school_profile:
            profile_prompt = "School profile is incomplete. Coordinate with your division office to update contact details."
        else:
            missing_bits: list[str] = []
            if not getattr(school_profile, "head_contact", "").strip():
                missing_bits.append("school head contact")
            if (
                getattr(school_profile, "grade_span_start", None) is None
                or getattr(school_profile, "grade_span_end", None) is None
            ):
                missing_bits.append("grade span")
            if missing_bits:
                joined = ", ".join(missing_bits)
                profile_prompt = f"Complete your profile: missing {joined}."

        school_portal = {
            "school": school,
            "profile": school_profile,
            "profile_prompt": profile_prompt,
            "current_submission": current_submission,
            "current_submission_timeline": current_submission_timeline,
            "outstanding_returns": outstanding_returns,
            "action_items": action_items,
            "summary": summary_metrics,
        }

    if account_services.user_is_section_admin(user):
        section_codes = sorted(section_codes or [])
        if section_codes:
            queue_qs = Submission.objects.filter(
                form_template__section__code__in=section_codes
            ).select_related("school", "form_template", "period")
            pending_total = queue_qs.filter(status=Submission.Status.SUBMITTED).count()
            returned_total = queue_qs.filter(status=Submission.Status.RETURNED).count()

            today = timezone.localdate()
            week_start = today - datetime.timedelta(days=today.weekday())
            handled_entries = SubmissionTimeline.objects.filter(
                submission__form_template__section__code__in=section_codes,
                actor=user,
                to_status__in=[
                    Submission.Status.RETURNED,
                    Submission.Status.NOTED,
                ],
                created_at__date__gte=week_start,
            )
            section_admin_summary = {
                "pending_total": pending_total,
                "returned_total": returned_total,
                "handled_this_week": handled_entries.count(),
            }

            section_admin_recent_actions = list(
                handled_entries.select_related(
                    "submission__school",
                    "submission__period",
                    "submission__form_template",
                )
                .order_by("-created_at")[:5]
            )

    profile_alerts = {
        "missing_profiles": 0,
        "missing_contacts": 0,
        "span_mismatches": 0,
        "critical_schools": [],
    }
    if account_services.user_is_sgod_admin(user):
        schools_qs = account_scope.scope_schools(user).select_related("profile", "district")
        critical = []
        for school in schools_qs:
            profile = getattr(school, "profile", None)
            missing_profile = profile is None
            missing_contact = not getattr(profile, "head_contact", "").strip() if profile else True
            profile_alerts["missing_profiles"] += int(missing_profile)
            profile_alerts["missing_contacts"] += int(missing_contact)
            grade_span_warning = False
            if profile and profile.grade_span_start and profile.grade_span_end:
                start = profile.grade_span_start
                end = profile.grade_span_end
                slp_rows = school.submissions.filter(status__in=["submitted", "noted"]).values_list("form1_slp_rows__grade_label", flat=True)
                for label in slp_rows:
                    digits = "".join(ch for ch in str(label) if ch.isdigit())
                    if digits:
                        grade = int(digits)
                        if not (start <= grade <= end):
                            grade_span_warning = True
                            break
            if grade_span_warning:
                profile_alerts["span_mismatches"] += 1
            if missing_profile or missing_contact or grade_span_warning:
                critical.append(
                    {
                        "school": school,
                        "missing_profile": missing_profile,
                        "missing_contact": missing_contact,
                        "grade_span_warning": grade_span_warning,
                    }
                )
        profile_alerts["critical_schools"] = critical[:5]
    
    # Calculate quarter statistics per section for school
    quarter_stats_by_section = {}
    available_school_years = ['2025-2026', '2024-2025', '2023-2024']
    
    if school:
        # Parse selected school year to get start year
        try:
            school_year_start = int(selected_school_year.split('-')[0])
        except (ValueError, IndexError):
            school_year_start = 2025
        
        # Build quarter stats for each section
        for section in sections:
            section_quarter_stats = []
            
            for q in range(1, 5):
                q_submissions = Submission.objects.filter(
                    school=school,
                    form_template__section=section,
                    period__quarter_tag=f'Q{q}',
                    period__school_year_start=school_year_start
                ).select_related('form_template', 'period')
                
                total_forms = q_submissions.count()
                completed_forms = q_submissions.filter(
                    status__in=[Submission.Status.SUBMITTED, Submission.Status.NOTED]
                ).count()
                draft_forms = q_submissions.filter(
                    status__in=[Submission.Status.DRAFT, Submission.Status.RETURNED]
                ).count()
                
                # Calculate average completion for drafts in this quarter
                q_completion = 0
                if draft_forms > 0:
                    q_drafts = q_submissions.filter(
                        status__in=[Submission.Status.DRAFT, Submission.Status.RETURNED]
                    )
                    q_progress_sum = 0
                    q_progress_count = 0
                    for sub in q_drafts:
                        try:
                            completion_data = sub.get_completion_summary()
                            q_progress_sum += completion_data.get('overall_progress', 0)
                            q_progress_count += 1
                        except:
                            pass
                    
                    if q_progress_count > 0:
                        q_completion = q_progress_sum // q_progress_count
                
                section_quarter_stats.append({
                    'quarter': q,
                    'total': total_forms,
                    'completed': completed_forms,
                    'in_progress': draft_forms,
                    'completion_rate': (completed_forms * 100 // total_forms) if total_forms > 0 else 0,
                    'avg_progress': q_completion,
                    'is_current': q == 3,  # TODO: Calculate actual current quarter
                    'is_selected': selected_quarter == f'Q{q}' if selected_quarter else False,
                })
            
            quarter_stats_by_section[section.code] = section_quarter_stats
        
        # Auto-select first section with forms if none selected
        if not selected_section_code and section_cards:
            selected_section_code = section_cards[0]['section'].code

    return render(
        request,
        "dashboards/school_home.html",
        {
            "sections": sections,
            "section_cards": section_cards,
            "today": today,
            "first_section_code": first_section_code,
            "show_reviewer_dashboards": reviewer_access,
            "draft_submissions": draft_submissions,
            "school_portal": school_portal,
            "section_admin_summary": section_admin_summary,
            "section_admin_recent_actions": section_admin_recent_actions,
            "district_dashboard_url": reverse("district_submission_gaps"),
            "smme_dashboard_url": reverse("smme_kpi_dashboard"),
            "profile_alerts": profile_alerts,
            "selected_school_year": selected_school_year,
            "selected_quarter": selected_quarter,
            "selected_section_code": selected_section_code,
            "quarter_stats_by_section": quarter_stats_by_section,
            "available_school_years": available_school_years,
        },
    )


def _require_reviewer_access(user) -> None:
    if not (
        account_services.user_is_section_admin(user)
        or account_services.user_is_psds(user)
        or account_services.user_is_sgod_admin(user)
    ):
        raise PermissionDenied("Reviewer role required.")


def _require_sgod_access(user) -> None:
    if not account_services.user_is_sgod_admin(user):
        raise PermissionDenied("SGOD access required.")


def _latest_period() -> Period | None:
    return (
        Period.objects.order_by("-school_year_start", "-display_order").first()
    )


@login_required
def district_submission_gaps(request):
    user = request.user
    _require_reviewer_access(user)

    sections = list(Section.objects.order_by("name"))
    section_code = request.GET.get("section") or (sections[0].code if sections else "")
    section = None
    if section_code:
        section = get_object_or_404(Section, code__iexact=section_code)

    form_templates = (
        FormTemplate.objects.filter(section=section).order_by("-open_at")
        if section
        else FormTemplate.objects.none()
    )
    form_code = request.GET.get("form_code") or (
        form_templates[0].code if form_templates else ""
    )
    form_template = None
    if form_code and section:
        form_template = get_object_or_404(
            FormTemplate,
            code=form_code,
            section=section,
        )

    periods = list(Period.objects.order_by("-school_year_start", "-display_order"))
    period_id = request.GET.get("period_id") or (
        periods[0].id if periods else None
    )
    period = get_object_or_404(Period, pk=period_id) if period_id else None

    district_id = request.GET.get("district_id")
    school_scope = account_scope.scope_schools(user).select_related("district", "profile")
    if district_id:
        school_scope = school_scope.filter(district_id=district_id)
    if section:
        # No explicit mapping between sections and schools yet, but keep hook.
        pass
    schools = list(school_scope)

    school_ids = [school.id for school in schools]
    districts_map: dict[int | None, dict[str, object]] = {}
    for school in schools:
        entry = districts_map.setdefault(
            school.district_id,
            {
                "district": school.district,
                "schools": [],
            },
        )
        entry["schools"].append(school)

    submissions = []
    if school_ids and form_template and period:
        submissions = list(
            Submission.objects.filter(
                school_id__in=school_ids,
                form_template=form_template,
                period=period,
            ).only("school_id", "status")
        )

    submitted_school_ids = {
        submission.school_id
        for submission in submissions
        if submission.status in _COMPLETED_STATUSES
    }

    district_rows = []
    total_schools = 0
    total_submitted = 0
    for district_id_value, payload in districts_map.items():
        district_schools: Iterable = payload["schools"]
        schools_list = list(district_schools)
        submitted_count = sum(
            1 for school in schools_list if school.id in submitted_school_ids
        )
        missing_schools = []
        for school in schools_list:
            if school.id in submitted_school_ids:
                continue
            profile = getattr(school, "profile", None)
            head_name = getattr(profile, "head_name", "") if profile else ""
            head_contact = getattr(profile, "head_contact", "") if profile else ""
            strands = ", ".join(profile.strands) if getattr(profile, "strands", None) else ""
            mismatched_ids = payload.get("grade_span_mismatches", set())
            missing_schools.append(
                {
                    "school": school,
                    "head_name": head_name,
                    "head_contact": head_contact,
                    "strands": strands,
                    "missing_profile": profile is None,
                    "missing_head_name": not bool(head_name.strip()),
                    "missing_head_contact": not bool(head_contact.strip()),
                    "grade_span_warning": school.id in mismatched_ids,
                }
            )
        district_rows.append(
            {
                "district": payload["district"],
                "total_schools": len(schools_list),
                "submitted_count": submitted_count,
                "missing_count": len(missing_schools),
                "missing_schools": missing_schools,
            }
        )
        total_schools += len(schools_list)
        total_submitted += submitted_count

    district_rows.sort(key=lambda row: (row["district"].name if row["district"] else ""))

    scoped_district_ids = {
        school.district_id for school in schools if school.district_id is not None
    }
    available_districts = list(
        District.objects.filter(pk__in=scoped_district_ids).order_by("name")
    )

    return render(
        request,
        "dashboards/district_submission_gaps.html",
        {
            "sections": sections,
            "selected_section": section,
            "form_templates": form_templates,
            "selected_form": form_template,
            "periods": periods,
            "selected_period": period,
            "districts": available_districts,
            "selected_district_id": int(district_id) if district_id else None,
            "district_rows": district_rows,
            "total_schools": total_schools,
            "total_submitted": total_submitted,
            "total_missing": total_schools - total_submitted,
        },
    )


@login_required
@PerformanceMonitor.profile_view
def smme_kpi_dashboard(request):
    """SMME KPI Dashboard - Enhanced with advanced filtering capabilities and performance optimization"""
    from dashboards.performance import DashboardCache, QueryOptimizer, PerformanceMonitor
    from django.core.cache import cache
    import time
    
    start_time = time.time()
    user = request.user
    _require_reviewer_access(user)
    
    from organizations.models import Section, School, District
    from submissions.models import Period, Form1SLPRow, FormTemplate
    from dashboards.kpi_calculators import calculate_all_kpis_for_period
    from submissions.constants import SLP_SUBJECT_LABELS, GRADE_NUMBER_TO_LABEL, RMAGradeLabel
    
    # Get SMME section
    try:
        smme_section = Section.objects.get(code__iexact='smme')
    except Section.DoesNotExist:
        messages.error(request, "SMME section not found")
        return redirect('school_home')
    
    # Get basic filters from request  
    school_year = request.GET.get('school_year')
    quarter = request.GET.get('quarter', 'all')  # all, Q1, Q2, Q3, Q4
    form_period = request.GET.get('form_period', 'all')  # legacy: specific Period id or 'all'
    form_template_code = request.GET.get('form_template', 'all')  # new: SMEA Form name/code (e.g., 'smea-form-1')
    district_id = request.GET.get('district')  # all or district_id
    school_id = request.GET.get('school')  # all or school_id
    # Persist last selected KPI part in session to avoid falling back to "All Parts" on fresh loads
    kpi_part = request.GET.get('kpi_part')  # all, implementation, slp, reading, rma, supervision, adm
    if not kpi_part:
        kpi_part = request.session.get('kpi_part', 'slp')  # sensible default: SLP view
    sort_dir = request.GET.get('sort_dir', 'asc')  # asc | desc
    school_level = request.GET.get('school_level', 'all')  # all, elementary, secondary
    
    # Advanced filters
    subject_filter = request.GET.get('subject', 'all')  # all or specific subject
    grade_range = request.GET.get('grade_range', 'all')  # all, k-3, 4-6, 7-9, 10-12
    performance_threshold = request.GET.get('performance_threshold', 'all')  # all, high, medium, low
    min_enrollment = request.GET.get('min_enrollment', '')  # minimum enrollment filter
    has_intervention = request.GET.get('has_intervention', 'all')  # all, yes, no
    # New multi-selects (subjects[], grades[]). When provided, they take precedence.
    selected_subjects = [s for s in request.GET.getlist('subjects') if s]
    selected_grades = [g for g in request.GET.getlist('grades') if g]
    # Choose a smart default sort when none provided
    if 'sort_by' in request.GET:
        sort_by = request.GET.get('sort_by', 'school_name')
    else:
        if kpi_part == 'implementation':
            sort_by = 'implementation'
        elif kpi_part in ['reading','reading_crla','reading_philiri']:
            # Prefer top proficiency bands as default sort
            sort_by = 'transitioning' if request.GET.get('reading_type', 'crla') == 'crla' else 'independent'
        elif kpi_part == 'supervision':
            sort_by = 'percent_ta'
        else:
            sort_by = 'school_name'  # sensible global default
    
    # Get available school years
    school_years = Period.objects.values_list(
        'school_year_start', flat=True
    ).distinct().order_by('-school_year_start')

    # (Deprecated) Removed client-side period index for 'Who Didn’t Submit'
    
    # Default to latest school year if not specified
    if not school_year and school_years:
        school_year = str(school_years[0])
    
    # Get periods based on quarter filter
    if quarter == 'all' and school_year:
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
        ).order_by('display_order')
    elif quarter != 'all' and school_year:
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__iexact=quarter
        ).order_by('display_order')
    else:
        periods = Period.objects.none()

    # If a specific SMEA Form period is chosen, override periods to just that one
    selected_form_period = None
    if form_period and form_period != 'all':
        try:
            selected_form_period = Period.objects.get(id=int(form_period))
            periods = Period.objects.filter(id=selected_form_period.id)
            # Also align the quarter to the selected form for consistency in the UI
            quarter = selected_form_period.quarter_tag
            school_year = str(selected_form_period.school_year_start)
        except (Period.DoesNotExist, ValueError):
            selected_form_period = None
    
    # Get districts for filter
    all_districts = District.objects.all().order_by('name')
    
    # Get schools based on filters with optimized queries
    schools_qs = School.objects.select_related('district', 'profile').order_by('name')
    if district_id and district_id != 'all':
        schools_qs = schools_qs.filter(district_id=district_id)
    if school_id and school_id != 'all':
        schools_qs = schools_qs.filter(id=school_id)
    
    # Apply school level filter (elementary/secondary)
    if school_level and school_level != 'all':
        if school_level == 'elementary':
            # Elementary: grades K-6 (grade_span_end <= 6)
            schools_qs = schools_qs.filter(profile__grade_span_end__lte=6)
        elif school_level == 'secondary':
            # Secondary: grades 7-12 (grade_span_start >= 7)
            schools_qs = schools_qs.filter(profile__grade_span_start__gte=7)
    
    # Helper function to apply advanced filters to SLP data
    def apply_advanced_slp_filters(slp_qs):
        """Apply advanced filters to SLP queryset"""
        # Multi-select subjects takes precedence
        if selected_subjects:
            slp_qs = slp_qs.filter(subject__in=selected_subjects)
        elif subject_filter and subject_filter != 'all':
            slp_qs = slp_qs.filter(subject=subject_filter)
        
        # Multi-select grades takes precedence
        if selected_grades:
            slp_qs = slp_qs.filter(grade_label__in=selected_grades)
        elif grade_range and grade_range != 'all':
            # Support legacy grouped ranges AND individual grade labels
            if grade_range == 'k-3':
                slp_qs = slp_qs.filter(grade_label__in=['Kinder', 'Grade 1', 'Grade 2', 'Grade 3'])
            elif grade_range == '4-6':
                slp_qs = slp_qs.filter(grade_label__in=['Grade 4', 'Grade 5', 'Grade 6'])
            elif grade_range == '7-9':
                slp_qs = slp_qs.filter(grade_label__in=['Grade 7', 'Grade 8', 'Grade 9'])
            elif grade_range == '10-12':
                slp_qs = slp_qs.filter(grade_label__in=['Grade 10', 'Grade 11', 'Grade 12'])
            else:
                # Individual grade label
                slp_qs = slp_qs.filter(grade_label=grade_range)
        
        if min_enrollment:
            try:
                min_enroll = int(min_enrollment)
                slp_qs = slp_qs.filter(enrolment__gte=min_enroll)
            except ValueError:
                pass
        
        if has_intervention and has_intervention != 'all':
            if has_intervention == 'yes':
                slp_qs = slp_qs.exclude(intervention_plan__isnull=True).exclude(intervention_plan__exact='')
            elif has_intervention == 'no':
                slp_qs = slp_qs.filter(intervention_plan__isnull=True) | slp_qs.filter(intervention_plan__exact='')
        
        return slp_qs
    
    # Get available filter options (cached)
    filter_cache_key = DashboardCache.generate_cache_key('filter_options', 
                                                         school_year=school_year, 
                                                         quarter=quarter)
    cached_filters = DashboardCache.get_cached_filter_options('dashboard_filters')
    
    if cached_filters:
        available_subjects, available_grades = cached_filters.get('subjects'), cached_filters.get('grades')
        # Robust normalization: guard against accidentally cached strings or unexpected shapes
        from submissions.constants import SLP_SUBJECT_LABELS
        # Subjects
        if isinstance(available_subjects, str) or available_subjects is None:
            # Invalid cache shape (string/None) → reset to empty so we rebuild below if needed
            available_subjects = []
        elif isinstance(available_subjects, (list, tuple)):
            available_subjects = list(available_subjects)
            if available_subjects and not isinstance(available_subjects[0], (list, tuple)):
                # Convert list of raw codes into (code,label) tuples
                available_subjects = [(s, SLP_SUBJECT_LABELS.get(s, s)) for s in available_subjects if s]
        else:
            # Unknown type → reset to empty
            available_subjects = []
        # Grades
        if isinstance(available_grades, str) or available_grades is None:
            available_grades = []
        elif not isinstance(available_grades, (list, tuple)):
            available_grades = []
        else:
            available_grades = [g for g in list(available_grades) if g]
        # If cache was malformed leading to empty options but we have periods, rebuild from DB and refresh cache
        if periods.exists() and (not available_subjects or not available_grades):
            qs = Form1SLPRow.objects.filter(
                submission__period__in=periods,
                submission__status__in=['submitted', 'noted']
            )
            if not available_subjects:
                subs = qs.values_list('subject', flat=True).distinct().order_by('subject')
                available_subjects = [(s, SLP_SUBJECT_LABELS.get(s, s)) for s in subs if s]
            if not available_grades:
                grades_q = qs.values_list('grade_label', flat=True).distinct().order_by('grade_label')
                available_grades = [g for g in grades_q if g]
            DashboardCache.set_cached_filter_options('dashboard_filters', {
                'subjects': available_subjects,
                'grades': available_grades,
                'districts': cached_filters.get('districts', []),
            })
    else:
        available_subjects = []
        available_grades = []
        if periods.exists():
            # Get subjects from actual data
            available_subjects = Form1SLPRow.objects.filter(
                submission__period__in=periods,
                submission__status__in=['submitted', 'noted']
            ).values_list('subject', flat=True).distinct().order_by('subject')
            available_subjects = [(s, SLP_SUBJECT_LABELS.get(s, s)) for s in available_subjects if s]
            
            # Get grade levels from actual data
            available_grades = Form1SLPRow.objects.filter(
                submission__period__in=periods,
                submission__status__in=['submitted', 'noted']
            ).values_list('grade_label', flat=True).distinct().order_by('grade_label')
            available_grades = [g for g in available_grades if g]

    # Final defensive normalization: coerce any remaining shapes into (code,label) tuples
    from submissions.constants import SLP_SUBJECT_LABELS as _SLP_LABELS
    def _to_pairs(seq):
        pairs = []
        try:
            for it in seq or []:
                if isinstance(it, (list, tuple)):
                    code = it[0] if len(it) > 0 else ''
                    label = it[1] if len(it) > 1 else _SLP_LABELS.get(code, code)
                else:
                    code = it
                    label = _SLP_LABELS.get(it, it)
                if code:
                    pairs.append((code, label))
        except Exception:
            # Fail-safe: fallback to empty list to avoid rendering per-character options
            pairs = []
        return pairs
    available_subjects = _to_pairs(available_subjects)

    # Ensure cache holds normalized shapes so subsequent loads don't regress
    try:
        DashboardCache.set_cached_filter_options('dashboard_filters', {
            'subjects': available_subjects,
            'grades': available_grades,
            'districts': cached_filters.get('districts', []) if cached_filters else [],
        })
    except Exception:
        pass

    # Sanitize user-provided filter values to avoid invalid errors
    # Quarter validation
    if quarter not in ['all', 'Q1', 'Q2', 'Q3', 'Q4']:
        quarter = 'all'
    # KPI part validation
    if kpi_part not in ['all', 'implementation', 'slp', 'reading', 'reading_crla', 'reading_philiri', 'rma', 'supervision', 'adm']:
        kpi_part = 'slp'
    # Pre-parse toggles used in validation
    reading_type = request.GET.get('reading_type', 'crla')  # crla | philiri
    # Derive reading timing from Quarter when not provided explicitly
    def _timing_from_quarter(q):
        # Mapping per latest policy:
        # Q1 → EOSY, Q2/Q3 → BOSY, Q4 → MOSY
        if q == 'Q1':
            return 'eosy'
        if q in ('Q2', 'Q3'):
            return 'bosy'
        if q == 'Q4':
            return 'mosy'
        return 'eosy'
    raw_timing = request.GET.get('assessment_timing')
    assessment_timing = raw_timing if raw_timing else _timing_from_quarter(quarter)
    rma_grade = request.GET.get('rma_grade', 'all')
    # Derive detail view flags early for validation
    is_slp_detail = (kpi_part == 'slp')
    is_rma_detail = (kpi_part == 'rma')
    # Sort dir validation
    if sort_dir not in ['asc', 'desc']:
        sort_dir = 'asc'
    # School level validation
    if school_level not in ['all', 'elementary', 'secondary']:
        school_level = 'all'
    # Advanced filters validation (SLP context)
    if subject_filter and subject_filter != 'all' and is_slp_detail and not selected_subjects:
        # available_subjects may be tuples in cache; normalize to raw values
        _subs = [s[0] if isinstance(s, (list, tuple)) and len(s) > 0 else s for s in available_subjects]
        if subject_filter not in _subs:
            subject_filter = 'all'
    # Validate multi-select subjects
    if selected_subjects and is_slp_detail:
        _subs_set = {s[0] if isinstance(s, (list, tuple)) and len(s) > 0 else s for s in available_subjects}
        selected_subjects = [s for s in selected_subjects if s in _subs_set]
    if grade_range and grade_range != 'all' and is_slp_detail:
        legacy_groups = {'k-3', '4-6', '7-9', '10-12'}
        if grade_range not in legacy_groups and grade_range not in set(available_grades):
            grade_range = 'all'
    # Validate multi-select grades
    if selected_grades and is_slp_detail:
        _grades_set = set(available_grades)
        selected_grades = [g for g in selected_grades if g in _grades_set]

    # Persist validated KPI part in session for subsequent loads without query params
    try:
        request.session['kpi_part'] = kpi_part
    except Exception:
        # Session may be unavailable in some contexts; fail silently
        pass
    # SLP mode validation
    slp_mode = request.GET.get('slp_mode', 'summary')
    if slp_mode not in ['summary', 'detail']:
        slp_mode = 'summary'
    # Performance threshold validation
    if performance_threshold not in ['all', 'high', 'medium', 'low']:
        performance_threshold = 'all'
    # has_intervention validation
    if has_intervention not in ['all', 'yes', 'no']:
        has_intervention = 'all'
    # Implementation focus (for implementation KPI view)
    impl_focus = request.GET.get('impl_focus', 'access')
    if impl_focus not in ['access', 'quality', 'equity', 'enabling']:
        impl_focus = 'access'
    # reading toggles validation
    if reading_type not in ['crla', 'philiri']:
        reading_type = 'crla'
    if assessment_timing not in ['bosy', 'mosy', 'eosy']:
        assessment_timing = _timing_from_quarter(quarter)
    # If KPI Part explicitly chooses reading subtype, override reading_type
    if kpi_part == 'reading_crla':
        reading_type = 'crla'
    elif kpi_part == 'reading_philiri':
        reading_type = 'philiri'
    # rma grade validation (accept 'all' or in choices)
    if is_rma_detail and rma_grade not in dict(RMAGradeLabel.CHOICES).keys() and rma_grade != 'all':
        rma_grade = 'all'
    
    # Graph-specific school year (for analytics only)
    graph_school_year = request.GET.get('graph_school_year')
    if not graph_school_year:
        graph_school_year = school_year
    else:
        try:
            if school_years and int(graph_school_year) not in set(school_years):
                graph_school_year = school_year
        except (ValueError, TypeError):
            graph_school_year = school_year

    # Build list of SMEA Form options (names only)
    available_forms = [
        {"code": f.code, "label": f.title}
        for f in FormTemplate.objects.filter(section=smme_section, is_active=True).order_by("code")
    ]

    # Build list of legacy SMEA Form period options for the current school year (kept for backward compatibility)
    available_periods = []
    if school_year:
        for p in Period.objects.filter(school_year_start=int(school_year)).order_by('display_order'):
            label = f"SMEA Form 1 — SY{p.school_year_start}-{p.school_year_start + 1} {p.quarter_tag}"
            available_periods.append({'id': p.id, 'label': label})

    # Use optimized school queryset
    filter_params = {
        'district_id': district_id,
        'school_id': school_id,
        'school_level': school_level,
    }
    schools_qs = QueryOptimizer.get_optimized_schools_queryset(filter_params)
    
    # Check if this is SLP subject detail view
    is_slp_detail = kpi_part == 'slp'
    is_rma_detail = kpi_part == 'rma'
    is_supervision_detail = kpi_part == 'supervision'
    is_adm_detail = kpi_part == 'adm'
    is_reading_detail = kpi_part in ['reading','reading_crla','reading_philiri']
    is_reading_crla_detail = (kpi_part == 'reading_crla') or (kpi_part == 'reading' and reading_type == 'crla')
    is_reading_philiri_detail = (kpi_part == 'reading_philiri') or (kpi_part == 'reading' and reading_type == 'philiri')
    is_implementation_detail = kpi_part == 'implementation'
    # reading_type and assessment_timing already parsed earlier for validation
    slp_mode = request.GET.get('slp_mode', 'summary')  # summary | detail
    slp_subject_data = []
    slp_distribution_data = []
    slp_district_averages = {}
    
    if is_slp_detail:
        if slp_mode == 'detail':
            # Subject-level detail per school
            slp_rows_qs = Form1SLPRow.objects.filter(
                submission__period__in=periods,
                submission__school__in=schools_qs,
                submission__status__in=['submitted', 'noted']
            ).select_related('submission__school', 'submission__school__district')
            slp_rows_qs = apply_advanced_slp_filters(slp_rows_qs)

            # Group by school then by subject
            schools_map = {}
            for row in slp_rows_qs:
                school = row.submission.school
                sdict = schools_map.setdefault(school.id, {
                    'school': school,
                    'district': school.district.name if school.district else 'N/A',
                    'subjects': {},
                })
                subj = (row.subject or 'Unknown').strip()
                subj_entry = sdict['subjects'].setdefault(subj, {
                    'subject': subj,
                    'grade_levels': set(),
                    'enrolment': 0,
                    'proficient_count': 0,
                    'dnme_count': 0,
                })
                enrol = row.enrolment or 0
                subj_entry['enrolment'] += enrol
                subj_entry['proficient_count'] += (row.s or 0) + (row.vs or 0) + (row.o or 0)
                subj_entry['dnme_count'] += (row.dnme or 0)
                if row.grade_label:
                    subj_entry['grade_levels'].add(row.grade_label)

            # Build per-school subject arrays with computed rates and classes
            def perf_class(p):
                if p < 50:
                    return 'performance-low'
                if p < 75:
                    return 'performance-medium'
                return 'performance-high'

            for sdict in schools_map.values():
                subjects_out = []
                for data in sdict['subjects'].values():
                    den = data['enrolment'] or 0
                    prof_rate = round((data['proficient_count']/den)*100, 1) if den else 0.0
                    dnme_rate = round((data['dnme_count']/den)*100, 1) if den else 0.0
                    subjects_out.append({
                        'subject': data['subject'],
                        'grade_levels': ', '.join(sorted(data['grade_levels'])) if data['grade_levels'] else '',
                        'enrolment': den,
                        'proficient_count': data['proficient_count'],
                        'proficiency_rate': prof_rate,
                        'dnme_count': data['dnme_count'],
                        'dnme_rate': dnme_rate,
                        'performance_class': perf_class(prof_rate),
                    })

                # Apply subject-level sort within a school
                reverse_subject_sort = (sort_dir == 'desc')
                if sort_by == 'subject_proficiency':
                    subjects_out.sort(key=lambda x: x['proficiency_rate'], reverse=reverse_subject_sort)
                elif sort_by == 'subject_name':
                    subjects_out.sort(key=lambda x: x['subject'] or '', reverse=reverse_subject_sort)
                else:
                    subjects_out.sort(key=lambda x: x['subject'] or '')

                # Compute school level label
                profile = getattr(sdict['school'], 'profile', None)
                level = 'Mixed'
                if profile:
                    if profile.grade_span_end and profile.grade_span_end <= 6:
                        level = 'Elementary'
                    elif profile.grade_span_start and profile.grade_span_start >= 7:
                        level = 'Secondary'

                if subjects_out:
                    slp_subject_data.append({
                        'school': sdict['school'],
                        'district': sdict['district'],
                        'school_level': level,
                        'subjects': subjects_out,
                        'total_subjects': len(subjects_out),
                    })

        else:
            # Build per-school SLP category distribution (DNME, FS, S, VS, O)
            from django.db.models import F
            slp_rows_qs = Form1SLPRow.objects.filter(
                submission__period__in=periods,
                submission__school__in=schools_qs,
                submission__status__in=['submitted', 'noted']
            ).select_related('submission__school', 'submission__school__district')
            slp_rows_qs = apply_advanced_slp_filters(slp_rows_qs)

            schools_map = {}
            for row in slp_rows_qs:
                school = row.submission.school
                entry = schools_map.setdefault(school.id, {
                    'school': school,
                    'district': school.district.name if school.district else 'N/A',
                    'enrolment': 0,
                    'dnme': 0,
                    'fs': 0,
                    's': 0,
                    'vs': 0,
                    'o': 0,
                })
                entry['enrolment'] += (row.enrolment or 0)
                entry['dnme'] += (row.dnme or 0)
                entry['fs'] += (row.fs or 0)
                entry['s'] += (row.s or 0)
                entry['vs'] += (row.vs or 0)
                entry['o'] += (row.o or 0)

            for entry in schools_map.values():
                total = entry['enrolment'] or 0
                def pct(v):
                    return round((v / total) * 100, 1) if total > 0 else 0.0
                overall = pct(entry['s'] + entry['vs'] + entry['o'])
                def _perf_class(p):
                    if p < 50:
                        return 'performance-low'
                    elif p < 75:
                        return 'performance-medium'
                    else:
                        return 'performance-high'
                slp_distribution_data.append({
                    'school': entry['school'],
                    'district': entry['district'],
                    'enrolment': total,
                    'dnme_pct': pct(entry['dnme']),
                    'fs_pct': pct(entry['fs']),
                    's_pct': pct(entry['s']),
                    'vs_pct': pct(entry['vs']),
                    'o_pct': pct(entry['o']),
                    'slp_overall': overall,
                    'overall_class': _perf_class(overall),
                })

            # Compute district averages for distribution view
            district_totals = {}
            for e in schools_map.values():
                dname = e['district'] or 'N/A'
                agg = district_totals.setdefault(dname, {'enrolment':0,'dnme':0,'fs':0,'s':0,'vs':0,'o':0})
                agg['enrolment'] += e['enrolment']
                agg['dnme'] += e['dnme']
                agg['fs'] += e['fs']
                agg['s'] += e['s']
                agg['vs'] += e['vs']
                agg['o'] += e['o']
            for dname, agg in district_totals.items():
                den = agg['enrolment'] or 0
                def dp(v):
                    return round((v/den)*100,1) if den>0 else 0.0
                slp_district_averages[dname] = {
                    'dnme_pct': dp(agg['dnme']),
                    'fs_pct': dp(agg['fs']),
                    's_pct': dp(agg['s']),
                    'vs_pct': dp(agg['vs']),
                    'o_pct': dp(agg['o']),
                    'slp_overall': dp(agg['s']+agg['vs']+agg['o']),
                    'enrolment': den,
                }

    # Build SLP trend data across quarters for analytics charts
    slp_trend_data = []
    if periods.exists() or school_years:
        # Determine periods for graph year (always Q1..Q4 of graph_school_year)
        graph_periods = Period.objects.filter(
            school_year_start=int(graph_school_year),
            quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
        ).order_by('display_order')

        # Base SLP rows for graph, respecting district/school and advanced SLP filters
        if graph_periods.exists():
            slp_rows_graph = Form1SLPRow.objects.filter(
                submission__period__in=graph_periods,
                submission__school__in=schools_qs,
                submission__status__in=['submitted', 'noted']
            ).select_related('submission__school', 'submission__school__district')
            slp_rows_graph = apply_advanced_slp_filters(slp_rows_graph)

            # Aggregate by quarter
            quarters = ['Q1','Q2','Q3','Q4']
            for q in quarters:
                q_rows = slp_rows_graph.filter(submission__period__quarter_tag__iexact=q)
                totals = {'enrolment':0,'dnme':0,'fs':0,'s':0,'vs':0,'o':0}
                for r in q_rows:
                    totals['enrolment'] += r.enrolment or 0
                    totals['dnme'] += r.dnme or 0
                    totals['fs'] += r.fs or 0
                    totals['s'] += r.s or 0
                    totals['vs'] += r.vs or 0
                    totals['o'] += r.o or 0
                den = totals['enrolment'] or 0
                def pct(v):
                    return round((v/den)*100,1) if den>0 else 0.0
                slp_trend_data.append({
                    'quarter': q,
                    'dnme_pct': pct(totals['dnme']),
                    'fs_pct': pct(totals['fs']),
                    's_pct': pct(totals['s']),
                    'vs_pct': pct(totals['vs']),
                    'o_pct': pct(totals['o']),
                    'enrolment': den,
                })

    # RMA detail view (per school, per grade) percentages
    rma_detail_data = []
    rma_grade = request.GET.get('rma_grade', 'all')  # k, g1..g10 or all
    if is_rma_detail and periods.exists():
        from submissions.models import Form1RMARow
        from submissions.constants import RMAGradeLabel

        # Gather all RMA rows for selected schools and periods
        rma_rows = Form1RMARow.objects.filter(
            submission__period__in=periods,
            submission__school__in=schools_qs,
            submission__status__in=['submitted','noted'],
            submission__form_template__is_active=True,
        ).select_related('submission__school', 'submission__school__district')
        if rma_grade and rma_grade != 'all':
            rma_rows = rma_rows.filter(grade_label=rma_grade)

        # Group by (school_id, grade_label)
        grouped = {}
        for row in rma_rows:
            key = (row.submission.school_id, row.grade_label)
            entry = grouped.setdefault(key, {
                'school': row.submission.school,
                'district': row.submission.school.district.name if row.submission.school.district else 'N/A',
                'grade_label': row.grade_label,
                'enrolment': 0,
                'emerging_not_proficient': 0,
                'emerging_low_proficient': 0,
                'developing_nearly_proficient': 0,
                'transitioning_proficient': 0,
                'at_grade_level': 0,
            })
            entry['enrolment'] += row.enrolment or 0
            entry['emerging_not_proficient'] += row.emerging_not_proficient or 0
            entry['emerging_low_proficient'] += row.emerging_low_proficient or 0
            entry['developing_nearly_proficient'] += row.developing_nearly_proficient or 0
            entry['transitioning_proficient'] += row.transitioning_proficient or 0
            entry['at_grade_level'] += row.at_grade_level or 0

        # Compute percentages per grouped entry
        def pct(num, den):
            return round((num / den) * 100, 1) if den and den > 0 else 0.0

        for (_, _), data in grouped.items():
            den = data['enrolment']
            rma_detail_data.append({
                'school': data['school'],
                'district': data['district'],
                'grade_label': data['grade_label'],
                'enrolment': den,
                'not_proficient_pct': pct(data['emerging_not_proficient'], den),
                'low_proficient_pct': pct(data['emerging_low_proficient'], den),
                'nearly_proficient_pct': pct(data['developing_nearly_proficient'], den),
                'proficient_pct': pct(data['transitioning_proficient'], den),
                'at_grade_level_pct': pct(data['at_grade_level'], den),
            })

        # Apply sorting
        reverse_sort = (sort_dir == 'desc')
        if sort_by == 'district':
            rma_detail_data.sort(
                key=lambda x: (
                    x['district'] or '',
                    x['school'].name if x.get('school') else '',
                    x.get('grade_label') or ''
                ),
                reverse=reverse_sort,
            )
        elif sort_by == 'grade':
            rma_detail_data.sort(key=lambda x: x['grade_label'] or '', reverse=reverse_sort)
        elif sort_by == 'not_proficient':
            rma_detail_data.sort(key=lambda x: x['not_proficient_pct'], reverse=reverse_sort)
        elif sort_by == 'low_proficient':
            rma_detail_data.sort(key=lambda x: x['low_proficient_pct'], reverse=reverse_sort)
        elif sort_by == 'nearly_proficient':
            rma_detail_data.sort(key=lambda x: x['nearly_proficient_pct'], reverse=reverse_sort)
        elif sort_by == 'proficient':
            rma_detail_data.sort(key=lambda x: x['proficient_pct'], reverse=reverse_sort)
        elif sort_by == 'at_grade_level':
            rma_detail_data.sort(key=lambda x: x['at_grade_level_pct'], reverse=reverse_sort)
        else:  # school_name default
            rma_detail_data.sort(key=lambda x: x['school'].name if x['school'] else '', reverse=reverse_sort)

    # Instructional Supervision detail view
    supervision_detail_data = []
    if is_supervision_detail and periods.exists():
        from submissions.models import Form1SupervisionRow
        supervision_rows = Form1SupervisionRow.objects.filter(
            submission__period__in=periods,
            submission__school__in=schools_qs,
            submission__status__in=['submitted','noted'],
            submission__form_template__is_active=True,
        ).select_related('submission__school', 'submission__school__district')

        grouped = {}
        for row in supervision_rows:
            school = row.submission.school
            entry = grouped.setdefault(school.id, {
                'school': school,
                'district': school.district.name if school.district else 'N/A',
                'total_teachers': 0,
                'teachers_supervised_ta': 0,
            })
            entry['total_teachers'] += row.total_teachers or 0
            entry['teachers_supervised_ta'] += row.teachers_supervised_observed_ta or 0

        for _, data in grouped.items():
            total = data['total_teachers']
            supervised = data['teachers_supervised_ta']
            pct_ta = round((supervised / total) * 100, 1) if total and total > 0 else 0.0
            supervision_detail_data.append({
                'school': data['school'],
                'district': data['district'],
                'total_teachers': total,
                'teachers_supervised_ta': supervised,
                'percent_ta': pct_ta,
            })

        reverse_sort = (sort_dir == 'desc')
        if sort_by == 'district':
            supervision_detail_data.sort(
                key=lambda x: (
                    x['district'] or '',
                    x['school'].name if x.get('school') else ''
                ),
                reverse=reverse_sort,
            )
        elif sort_by == 'percent_ta':
            supervision_detail_data.sort(key=lambda x: x['percent_ta'], reverse=reverse_sort)
        elif sort_by == 'total_teachers':
            supervision_detail_data.sort(key=lambda x: x['total_teachers'], reverse=reverse_sort)
        elif sort_by == 'teachers_supervised_ta':
            supervision_detail_data.sort(key=lambda x: x['teachers_supervised_ta'], reverse=reverse_sort)
        else:
            supervision_detail_data.sort(key=lambda x: x['school'].name if x['school'] else '', reverse=reverse_sort)

    # ADM detail view (per school) – One-Stop-Shop & EiE
    adm_detail_data = []
    if is_adm_detail and periods.exists():
        from submissions.models import Form1ADMHeader, Form1ADMRow
        # Determine schools offering ADM (via header)
        headers = Form1ADMHeader.objects.filter(
            submission__period__in=periods,
            submission__school__in=schools_qs,
            is_offered=True
        ).select_related('submission__school', 'submission__school__district')

        offered_school_ids = {h.submission.school_id for h in headers}
        # Aggregate ADM rows for offered schools
        rows = Form1ADMRow.objects.filter(
            submission__period__in=periods,
            submission__school__in=schools_qs,
            submission__form1_adm_header__is_offered=True
        ).select_related('submission__school', 'submission__school__district')

        grouped = {}
        for row in rows:
            school = row.submission.school
            g = grouped.setdefault(school.id, {
                'school': school,
                'district': school.district.name if school.district else 'N/A',
                'program_count': 0,
                'physical_sum': 0.0,
                'funds_sum': 0.0,
            })
            g['program_count'] += 1
            try:
                g['physical_sum'] += float(row.ppas_physical_percent or 0)
            except Exception:
                g['physical_sum'] += 0.0
            try:
                g['funds_sum'] += float(row.funds_percent_obligated or 0)
            except Exception:
                g['funds_sum'] += 0.0

        # Build per-school entries including schools that offer ADM but have no rows
        for school in schools_qs:
            offers_adm = school.id in offered_school_ids
            data = grouped.get(school.id)
            if offers_adm or data:
                program_count = data['program_count'] if data else 0
                phys_avg = round((data['physical_sum'] / program_count), 1) if data and program_count else 0.0
                funds_avg = round((data['funds_sum'] / program_count), 1) if data and program_count else 0.0
                overall = round(((phys_avg + funds_avg) / 2), 1) if (phys_avg or funds_avg) else 0.0
                adm_detail_data.append({
                    'school': data['school'] if data else school,
                    'district': (data['district'] if data else (school.district.name if school.district else 'N/A')),
                    'offers_adm': offers_adm,
                    'program_count': program_count,
                    'physical_avg': phys_avg,
                    'funds_avg': funds_avg,
                    'overall_adm': overall,
                })

        # Sorting for ADM
        reverse_sort = (sort_dir == 'desc')
        if sort_by == 'district':
            adm_detail_data.sort(
                key=lambda x: (
                    x['district'] or '',
                    x['school'].name if x.get('school') else ''
                ),
                reverse=reverse_sort,
            )
        elif sort_by == 'overall_adm':
            adm_detail_data.sort(key=lambda x: x['overall_adm'], reverse=reverse_sort)
        elif sort_by == 'physical':
            adm_detail_data.sort(key=lambda x: x['physical_avg'], reverse=reverse_sort)
        elif sort_by == 'funds':
            adm_detail_data.sort(key=lambda x: x['funds_avg'], reverse=reverse_sort)
        elif sort_by == 'programs':
            adm_detail_data.sort(key=lambda x: x['program_count'], reverse=reverse_sort)
        else:
            adm_detail_data.sort(key=lambda x: x['school'].name if x.get('school') else '', reverse=reverse_sort)

    # Reading detail view (CRLA/PHILIRI) per school
    reading_detail_data = []
    if is_reading_detail and periods.exists():
        from submissions.models import ReadingAssessmentCRLA, ReadingAssessmentPHILIRI
        from submissions.constants import CRLAProficiencyLevel, PHILIRIReadingLevel

        if reading_type == 'crla':
            # For reading assessments, bind by school year and derived timing
            rows = ReadingAssessmentCRLA.objects.filter(
                submission__period__school_year_start=int(school_year),
                submission__school__in=schools_qs,
                submission__status__in=['submitted','noted'],
                submission__form_template__is_active=True,
                period=assessment_timing
            ).select_related('submission__school', 'submission__school__district')

            grouped = {}
            for row in rows:
                school = row.submission.school
                entry = grouped.setdefault(school.id, {
                    'school': school,
                    'district': school.district.name if school.district else 'N/A',
                    'low_emerging': 0,
                    'high_emerging': 0,
                    'developing': 0,
                    'transitioning': 0,
                    'total': 0,
                })
                total = row.total_learners()
                entry['total'] += total
                if row.level == CRLAProficiencyLevel.LOW_EMERGING:
                    entry['low_emerging'] += total
                elif row.level == CRLAProficiencyLevel.HIGH_EMERGING:
                    entry['high_emerging'] += total
                elif row.level == CRLAProficiencyLevel.DEVELOPING:
                    entry['developing'] += total
                elif row.level == CRLAProficiencyLevel.TRANSITIONING:
                    entry['transitioning'] += total

            def pct(n, d):
                return round((n / d) * 100, 1) if d and d > 0 else 0.0

            for _, data in grouped.items():
                d = data['total']
                reading_detail_data.append({
                    'school': data['school'],
                    'district': data['district'],
                    'low_emerging_pct': pct(data['low_emerging'], d),
                    'high_emerging_pct': pct(data['high_emerging'], d),
                    'developing_pct': pct(data['developing'], d),
                    'transitioning_pct': pct(data['transitioning'], d),
                    'total': d,
                })

            reverse_sort = (sort_dir == 'desc')
            if sort_by == 'district':
                reading_detail_data.sort(
                    key=lambda x: (
                        x['district'] or '',
                        x['school'].name if x.get('school') else ''
                    ),
                    reverse=reverse_sort,
                )
            elif sort_by == 'low_emerging':
                reading_detail_data.sort(key=lambda x: x['low_emerging_pct'], reverse=reverse_sort)
            elif sort_by == 'high_emerging':
                reading_detail_data.sort(key=lambda x: x['high_emerging_pct'], reverse=reverse_sort)
            elif sort_by == 'developing':
                reading_detail_data.sort(key=lambda x: x['developing_pct'], reverse=reverse_sort)
            elif sort_by == 'transitioning':
                reading_detail_data.sort(key=lambda x: x['transitioning_pct'], reverse=reverse_sort)
            else:
                reading_detail_data.sort(key=lambda x: x['school'].name if x['school'] else '', reverse=reverse_sort)
        else:  # philiri
            rows = ReadingAssessmentPHILIRI.objects.filter(
                submission__period__school_year_start=int(school_year),
                submission__school__in=schools_qs,
                submission__status__in=['submitted','noted'],
                submission__form_template__is_active=True,
                period=assessment_timing
            ).select_related('submission__school', 'submission__school__district')

            grouped = {}
            # Helper to sum all grade fields from PHILIRI row
            def total_philiri_row(r):
                return (
                    (r.eng_grade_4 or 0) + (r.eng_grade_5 or 0) + (r.eng_grade_6 or 0) + (r.eng_grade_7 or 0) +
                    (r.eng_grade_8 or 0) + (r.eng_grade_9 or 0) + (r.eng_grade_10 or 0) +
                    (r.fil_grade_4 or 0) + (r.fil_grade_5 or 0) + (r.fil_grade_6 or 0) + (r.fil_grade_7 or 0) +
                    (r.fil_grade_8 or 0) + (r.fil_grade_9 or 0) + (r.fil_grade_10 or 0)
                )

            for row in rows:
                school = row.submission.school
                entry = grouped.setdefault(school.id, {
                    'school': school,
                    'district': school.district.name if school.district else 'N/A',
                    'frustration': 0,
                    'instructional': 0,
                    'independent': 0,
                    'total': 0,
                })
                total = total_philiri_row(row)
                entry['total'] += total
                if row.level == PHILIRIReadingLevel.FRUSTRATION:
                    entry['frustration'] += total
                elif row.level == PHILIRIReadingLevel.INSTRUCTIONAL:
                    entry['instructional'] += total
                elif row.level == PHILIRIReadingLevel.INDEPENDENT:
                    entry['independent'] += total

            def pct2(n, d):
                return round((n / d) * 100, 1) if d and d > 0 else 0.0

            for _, data in grouped.items():
                d = data['total']
                reading_detail_data.append({
                    'school': data['school'],
                    'district': data['district'],
                    'frustration_pct': pct2(data['frustration'], d),
                    'instructional_pct': pct2(data['instructional'], d),
                    'independent_pct': pct2(data['independent'], d),
                    'total': d,
                })

            reverse_sort = (sort_dir == 'desc')
            if sort_by == 'district':
                reading_detail_data.sort(
                    key=lambda x: (
                        x['district'] or '',
                        x['school'].name if x.get('school') else ''
                    ),
                    reverse=reverse_sort,
                )
            elif sort_by == 'frustration':
                reading_detail_data.sort(key=lambda x: x['frustration_pct'], reverse=reverse_sort)
            elif sort_by == 'instructional':
                reading_detail_data.sort(key=lambda x: x['instructional_pct'], reverse=reverse_sort)
            elif sort_by == 'independent':
                reading_detail_data.sort(key=lambda x: x['independent_pct'], reverse=reverse_sort)
            else:
                reading_detail_data.sort(key=lambda x: x['school'].name if x['school'] else '', reverse=reverse_sort)
    
    # Build regular KPI table data (for non-SLP detail views) with caching
    kpi_table_data = []
    if not is_slp_detail:
        # Try to get cached KPI data for all schools
        kpi_cache_key = DashboardCache.generate_cache_key(
            'kpi_bulk',
            periods=str(list(periods.values_list('id', flat=True))),
            schools=str(list(schools_qs.values_list('id', flat=True)))
        )

        cached_kpi_data = cache.get(kpi_cache_key)

        if cached_kpi_data:
            kpi_table_data = cached_kpi_data
        else:
            # Helper for performance class
            def get_performance_class(percentage):
                if percentage < 50:
                    return 'performance-low'
                elif percentage < 75:
                    return 'performance-medium'
                else:
                    return 'performance-high'

            for school in schools_qs:
                # Check individual school cache first
                cached_school_kpis = DashboardCache.get_cached_kpi_data(school.id, periods, 'smme')
                if cached_school_kpis:
                    school_kpis = cached_school_kpis
                else:
                    from dashboards.kpi_calculators import calculate_school_kpis_simple
                    school_kpis = calculate_school_kpis_simple(school, periods, 'smme')
                    DashboardCache.set_cached_kpi_data(school.id, periods, 'smme', school_kpis)

                # Determine school level for this school
                school_level_label = 'Mixed'
                profile = getattr(school, 'profile', None)
                if profile:
                    if getattr(profile, 'grade_span_end', None) and profile.grade_span_end <= 6:
                        school_level_label = 'Elementary'
                    elif getattr(profile, 'grade_span_start', None) and profile.grade_span_start >= 7:
                        school_level_label = 'Secondary'

                kpi_table_data.append({
                    'school': school,
                    'district': school.district.name if school.district else 'N/A',
                    'school_level': school_level_label,
                    'implementation': school_kpis['implementation'],
                    'implementation_class': get_performance_class(school_kpis['implementation']),
                    'impl_access': school_kpis.get('implementation_access', 0),
                    'impl_access_class': get_performance_class(school_kpis.get('implementation_access', 0)),
                    'impl_quality': school_kpis.get('implementation_quality', 0),
                    'impl_quality_class': get_performance_class(school_kpis.get('implementation_quality', 0)),
                    'impl_equity': school_kpis.get('implementation_equity', 0),
                    'impl_equity_class': get_performance_class(school_kpis.get('implementation_equity', 0)),
                    'impl_enabling': school_kpis.get('implementation_enabling', 0),
                    'impl_enabling_class': get_performance_class(school_kpis.get('implementation_enabling', 0)),
                    'slp': school_kpis['slp'],
                    'slp_class': get_performance_class(school_kpis['slp']),
                    'reading_crla': school_kpis['reading_crla'],
                    'reading_crla_class': get_performance_class(school_kpis['reading_crla']),
                    'reading_philiri': school_kpis['reading_philiri'],
                    'reading_philiri_class': get_performance_class(school_kpis['reading_philiri']),
                    'rma': school_kpis['rma'],
                    'rma_class': get_performance_class(school_kpis['rma']),
                    'supervision': school_kpis['supervision'],
                    'supervision_class': get_performance_class(school_kpis['supervision']),
                    'adm': school_kpis['adm'],
                    'adm_class': get_performance_class(school_kpis['adm']),
                    'has_data': school_kpis['has_data'],
                })

            # Cache the bulk table for later requests
            cache.set(kpi_cache_key, kpi_table_data, 60)  # cache for 1 minute (tune as needed)
    
    # Apply performance threshold filter to both views
    if performance_threshold and performance_threshold != 'all':
        if is_slp_detail and slp_mode != 'detail':
            # Filter SLP distribution rows by overall SLP (S+VS+O)
            def pass_threshold(row):
                val = row['slp_overall']
                if performance_threshold == 'high':
                    return val >= 75
                if performance_threshold == 'medium':
                    return 50 <= val < 75
                if performance_threshold == 'low':
                    return val < 50
                return True
            slp_distribution_data = [r for r in slp_distribution_data if pass_threshold(r)]
        elif is_slp_detail and slp_mode == 'detail':
            # Filter subjects within schools by subject proficiency
            filtered_schools = []
            for school_data in slp_subject_data:
                kept_subjects = []
                for subj in school_data['subjects']:
                    val = subj['proficiency_rate']
                    if performance_threshold == 'high' and val >= 75:
                        kept_subjects.append(subj)
                    elif performance_threshold == 'medium' and 50 <= val < 75:
                        kept_subjects.append(subj)
                    elif performance_threshold == 'low' and val < 50:
                        kept_subjects.append(subj)
                if kept_subjects:
                    school_copy = school_data.copy()
                    school_copy['subjects'] = kept_subjects
                    school_copy['total_subjects'] = len(kept_subjects)
                    filtered_schools.append(school_copy)
            slp_subject_data = filtered_schools
        else:
            # Filter KPI table data by performance threshold (using SLP performance as main metric)
            if performance_threshold == 'high':
                kpi_table_data = [row for row in kpi_table_data if row['slp'] >= 75]
            elif performance_threshold == 'medium':
                kpi_table_data = [row for row in kpi_table_data if 50 <= row['slp'] < 75]
            elif performance_threshold == 'low':
                kpi_table_data = [row for row in kpi_table_data if row['slp'] < 50]
    
    # Apply sorting
    if is_slp_detail:
        reverse_sort = (sort_dir == 'desc')
        if slp_mode == 'detail':
            # Sort schools for subject-detail
            if sort_by == 'school_name':
                slp_subject_data.sort(key=lambda x: x['school'].name, reverse=reverse_sort)
            elif sort_by == 'district':
                slp_subject_data.sort(key=lambda x: (x['district'] or '', x['school'].name), reverse=reverse_sort)
            elif sort_by == 'performance':
                # Sort by best subject proficiency in each school
                slp_subject_data.sort(key=lambda x: max([s['proficiency_rate'] for s in x['subjects']] or [0]), reverse=reverse_sort)
            elif sort_by == 'enrollment':
                slp_subject_data.sort(key=lambda x: sum([s['enrolment'] for s in x['subjects']] or [0]), reverse=reverse_sort)
            else:
                slp_subject_data.sort(key=lambda x: x['school'].name)
        else:
            # Sort SLP distribution data (summary)
            if sort_by == 'school_name':
                slp_distribution_data.sort(key=lambda x: x['school'].name, reverse=reverse_sort)
            elif sort_by == 'district':
                slp_distribution_data.sort(key=lambda x: (x['district'] or '', x['school'].name), reverse=reverse_sort)
            elif sort_by in ['dnme','fs','s','vs','o','performance','enrollment']:
                key_map = {
                    'dnme': 'dnme_pct',
                    'fs': 'fs_pct',
                    's': 's_pct',
                    'vs': 'vs_pct',
                    'o': 'o_pct',
                    'performance': 'slp_overall',
                    'enrollment': 'enrolment',
                }
                slp_distribution_data.sort(key=lambda x: x[key_map.get(sort_by, 'slp_overall')], reverse=reverse_sort)
    else:
        # Sort KPI table data
        reverse_sort = (sort_dir == 'desc')
        if sort_by == 'school_name':
            kpi_table_data.sort(key=lambda x: x['school'].name, reverse=reverse_sort)
        elif sort_by == 'district':
            kpi_table_data.sort(
                key=lambda x: (
                    x['district'] or '',
                    x['school'].name
                ),
                reverse=reverse_sort,
            )
        elif sort_by == 'performance':
            # Default performance metric is SLP; if implementation tab is selected, use overall implementation
            if kpi_part == 'implementation':
                kpi_table_data.sort(key=lambda x: x['implementation'], reverse=reverse_sort)
            else:
                kpi_table_data.sort(key=lambda x: x['slp'], reverse=reverse_sort)
        elif kpi_part == 'implementation' and sort_by in ['implementation','impl_access','impl_quality','impl_equity','impl_enabling']:
            kpi_table_data.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse_sort)
        elif sort_by == 'enrollment':
            # For KPI view, sort by average SLP performance since we don't have direct enrollment
            kpi_table_data.sort(key=lambda x: x['slp'], reverse=reverse_sort)
    
    # Get available subjects for filter (when in SLP detail mode)
    # Do not overwrite if already populated via cache/normalization above.
    if is_slp_detail and periods.exists() and not available_subjects:
        _subs_qs = Form1SLPRow.objects.filter(
            submission__period__in=periods,
            submission__status__in=['submitted', 'noted']
        ).values_list('subject', flat=True).distinct().order_by('subject')
        available_subjects = [(s, SLP_SUBJECT_LABELS.get(s, s)) for s in _subs_qs if s]
    
    # Build sort options depending on view
    sort_options = [
        ('school_name', 'School Name'),
        ('district', 'District'),
    ]
    if is_slp_detail:
        if slp_mode == 'detail':
            sort_options += [
                ('performance', 'Subject Performance (max)'),
                ('enrollment', 'Total Enrollment'),
                ('subject_proficiency', 'Subject Proficiency (within school)'),
                ('subject_name', 'Subject Name (within school)'),
            ]
        else:
            sort_options += [
                ('performance', 'Overall SLP % (S+VS+O)'),
                ('dnme', 'DNME %'),
                ('fs', 'FS %'),
                ('s', 'S %'),
                ('vs', 'VS %'),
                ('o', 'O %'),
                ('enrollment', 'Enrollment'),
            ]
    elif is_rma_detail:
        sort_options += [
            ('grade', 'Grade'),
            ('not_proficient', 'Not Proficient %'),
            ('low_proficient', 'Low Proficient %'),
            ('nearly_proficient', 'Nearly Proficient %'),
            ('proficient', 'Proficient %'),
            ('at_grade_level', 'At Grade Level %'),
        ]
    elif is_supervision_detail:
        sort_options += [
            ('percent_ta', '% Provided TA'),
            ('total_teachers', 'Total Teachers'),
            ('teachers_supervised_ta', 'Teachers Supervised & TA'),
        ]
    elif is_adm_detail:
        sort_options += [
            ('overall_adm', 'Overall ADM %'),
            ('physical', 'Physical Accomplishment %'),
            ('funds', 'Funds Utilization %'),
            ('programs', 'Programs Count'),
        ]
    elif is_reading_detail:
        if reading_type == 'crla':
            sort_options += [
                ('low_emerging', 'Low Emerging %'),
                ('high_emerging', 'High Emerging %'),
                ('developing', 'Developing %'),
                ('transitioning', 'Transitioning %'),
            ]
        else:
            sort_options += [
                ('frustration', 'Frustration %'),
                ('instructional', 'Instructional %'),
                ('independent', 'Independent %'),
            ]
    else:
        if kpi_part == 'implementation':
            sort_options += [
                ('implementation', 'Overall % Implementation'),
                ('impl_access', 'Access %'),
                ('impl_quality', 'Quality %'),
                ('impl_equity', 'Equity %'),
                ('impl_enabling', 'Enabling Mechanisms %'),
            ]
        sort_options += [
            ('performance', 'Performance'),
            ('enrollment', 'Enrollment'),
        ]

    # Missing-only toggle (Who Didn't Submit)
    only_missing = str(request.GET.get('only_missing', '0')).lower() in ('1', 'true', 'yes', 'on')
    # Apply only when a specific form and exactly one period are selected
    can_apply_missing = (
        form_template_code and form_template_code != 'all' and periods.exists() and periods.count() == 1
    )
    # Control visibility: only in overview (not detail sub-views)
    missing_filter_applicable = (
        can_apply_missing and not (is_slp_detail or is_rma_detail or is_supervision_detail or is_adm_detail or is_reading_detail)
    )

    # Validate sort_by against the available options for the current view
    valid_sort_keys = {k for k, _ in sort_options}
    if sort_by not in valid_sort_keys:
        sort_by = 'school_name'

    # Analytics visibility (opt-in via query string)
    show_analytics = str(request.GET.get('show_analytics', '0')).lower() in ('1', 'true', 'yes', 'on')

    # Apply Missing-only filter to overview table when eligible
    missing_count = None
    if (only_missing and missing_filter_applicable):
        try:
            from submissions.models import Submission, FormTemplate as _FT
            form_template_obj = _FT.objects.filter(section=smme_section, code=form_template_code).first()
            if form_template_obj:
                school_ids = list(schools_qs.values_list('id', flat=True))
                period_ids = list(periods.values_list('id', flat=True))
                submitted_ids = set(
                    Submission.objects.filter(
                        school_id__in=school_ids,
                        form_template=form_template_obj,
                        period_id__in=period_ids,
                        status__in=['submitted', 'noted'],
                    ).values_list('school_id', flat=True)
                )
                missing_ids = set(school_ids) - submitted_ids
                missing_count = len(missing_ids)
                if isinstance(kpi_table_data, list):
                    kpi_table_data = [row for row in kpi_table_data if getattr(row.get('school'), 'id', None) in missing_ids]
        except Exception:
            # Fail-open: keep full dataset if any issue occurs
            missing_count = None

    context = {
        'section': smme_section,
        'school_years': school_years,
        'selected_school_year': school_year,
    'selected_quarter': quarter,
    'selected_form_period': str(selected_form_period.id) if selected_form_period else 'all',
    'selected_form_template': form_template_code,
        'selected_district': district_id,
        'selected_school': school_id,
        'selected_kpi_part': kpi_part,
        'selected_school_level': school_level,
    'selected_subject': subject_filter,
    'selected_subjects': selected_subjects,
    'selected_grade_range': grade_range,
    'selected_grades': selected_grades,
    'slp_mode': slp_mode,
        'selected_performance_threshold': performance_threshold,
        'selected_min_enrollment': min_enrollment,
        'selected_has_intervention': has_intervention,
        'selected_sort_by': sort_by,
        'selected_sort_dir': sort_dir,
    'all_districts': all_districts,
        'all_schools': School.objects.all().order_by('name'),
    'available_periods': available_periods,
    'available_forms': available_forms,
        'kpi_table_data': kpi_table_data,
        'periods': periods,
    'school_years': school_years,
    'graph_school_year': graph_school_year,
    'slp_trend_data': slp_trend_data,
    'is_slp_detail': is_slp_detail,
    'slp_subject_data': slp_subject_data,
    'slp_distribution_data': slp_distribution_data,
    'slp_district_averages': slp_district_averages,
    'is_reading_detail': is_reading_detail,
    'is_reading_crla_detail': is_reading_crla_detail,
    'is_reading_philiri_detail': is_reading_philiri_detail,
    'reading_type': reading_type,
    'assessment_timing': assessment_timing,
    'reading_detail_data': reading_detail_data,
    'is_implementation_detail': is_implementation_detail,
    'impl_focus': impl_focus,
        'is_rma_detail': is_rma_detail,
        'rma_detail_data': rma_detail_data,
        'rma_grade': rma_grade,
    'rma_grade_choices': [('all', 'All Grades')] + list(RMAGradeLabel.CHOICES),
        'is_supervision_detail': is_supervision_detail,
        'supervision_detail_data': supervision_detail_data,
    'is_adm_detail': is_adm_detail,
    'adm_detail_data': adm_detail_data,
        'available_subjects': available_subjects,
        'available_grades': available_grades,
        'grade_range_options': [
            ('all', 'All Grades'),
            ('k-3', 'Kindergarten - Grade 3'),
            ('4-6', 'Grade 4 - 6'),
            ('7-9', 'Grade 7 - 9'),
            ('10-12', 'Grade 10 - 12'),
        ],
        'performance_options': [
            ('all', 'All Performance Levels'),
            ('high', 'High Performance (75%+)'),
            ('medium', 'Medium Performance (50-74%)'),
            ('low', 'Low Performance (<50%)'),
        ],
        'sort_options': sort_options,
        'show_analytics': show_analytics,
    'selected_only_missing': only_missing if missing_filter_applicable else False,
    'missing_filter_applicable': missing_filter_applicable,
    'missing_count': missing_count,
    }
    
    # Performance monitoring
    end_time = time.time()
    execution_time = end_time - start_time
    from django.conf import settings as _dj_settings
    from django.db import connection
    query_count = len(connection.queries) if hasattr(connection, 'queries') else 0
    if execution_time > 1.0:
        PerformanceMonitor.log_query_performance('smme_kpi_dashboard', query_count, execution_time)
    # Expose lightweight perf info in DEBUG for optional UI badges
    if getattr(_dj_settings, 'DEBUG', False):
        context['debug_perf'] = {
            'execution_time': round(execution_time, 3),
            'query_count': int(query_count),
        }
    
    return render(request, 'dashboards/smme_kpi_dashboard.html', context)


@login_required
@PerformanceMonitor.profile_view
def smme_kpi_api(request):
    """JSON API endpoint for SMME dashboard data with pagination and caching.
    Accepts the same query parameters as the HTML dashboard and returns the current view's dataset.
    Query params: kpi_part in [all(default)/implementation, slp, reading, rma, supervision],
    plus existing filters (school_year, quarter, form_period, district, school, sort_by, sort_dir,
    reading_type, assessment_timing, rma_grade, subject/min_enrollment/grade_range/has_intervention, performance_threshold).
    Pagination: page (1-based), page_size (default 50).
    """
    from dashboards.performance import DashboardCache, QueryOptimizer
    from organizations.models import Section, School, District
    from submissions.models import Period, Form1SLPRow

    # Parse filters
    school_year = request.GET.get('school_year')
    quarter = request.GET.get('quarter', 'all')
    form_period = request.GET.get('form_period', 'all')
    district_id = request.GET.get('district')
    school_id = request.GET.get('school')
    kpi_part = request.GET.get('kpi_part', 'all')
    sort_by = request.GET.get('sort_by', 'school_name')
    sort_dir = request.GET.get('sort_dir', 'asc')
    school_level = request.GET.get('school_level', 'all')
    performance_threshold = request.GET.get('performance_threshold', 'all')

    # SLP/Reading/RMA specifics
    subject_filter = request.GET.get('subject', 'all')
    selected_subjects = [s for s in request.GET.getlist('subjects') if s]
    grade_range = request.GET.get('grade_range', 'all')
    selected_grades = [g for g in request.GET.getlist('grades') if g]
    min_enrollment = request.GET.get('min_enrollment', '')
    has_intervention = request.GET.get('has_intervention', 'all')
    reading_type = request.GET.get('reading_type', 'crla')
    # Derive reading timing from Quarter when not present
    def _timing_from_quarter(q):
        # Mapping per latest policy:
        # Q1 → EOSY, Q2/Q3 → BOSY, Q4 → MOSY
        if q == 'Q1':
            return 'eosy'
        if q in ('Q2', 'Q3'):
            return 'bosy'
        if q == 'Q4':
            return 'mosy'
        return 'eosy'
    raw_timing = request.GET.get('assessment_timing')
    assessment_timing = raw_timing if raw_timing else _timing_from_quarter(quarter)
    rma_grade = request.GET.get('rma_grade', 'all')

    # Pagination
    try:
        page = max(int(request.GET.get('page', '1')), 1)
    except ValueError:
        page = 1
    try:
        page_size = max(min(int(request.GET.get('page_size', '50')), 500), 1)
    except ValueError:
        page_size = 50

    # Determine periods
    school_years = Period.objects.values_list('school_year_start', flat=True).distinct().order_by('-school_year_start')
    if not school_year and school_years:
        school_year = str(school_years[0])

    if quarter == 'all' and school_year:
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
        ).order_by('display_order')
    elif quarter != 'all' and school_year:
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__iexact=quarter
        ).order_by('display_order')
    else:
        periods = Period.objects.none()

    selected_form_period = None
    if form_period and form_period != 'all':
        try:
            selected_form_period = Period.objects.get(id=int(form_period))
            periods = Period.objects.filter(id=selected_form_period.id)
            quarter = selected_form_period.quarter_tag
            school_year = str(selected_form_period.school_year_start)
        except (Period.DoesNotExist, ValueError):
            selected_form_period = None

    # Schools queryset via optimizer
    filter_params = {
        'district_id': district_id,
        'school_id': school_id,
        'school_level': school_level,
    }
    schools_qs = QueryOptimizer.get_optimized_schools_queryset(filter_params)

    # Helper: apply SLP advanced filters
    def apply_advanced_slp_filters(slp_qs):
        if subject_filter and subject_filter != 'all':
            slp_qs = slp_qs.filter(subject=subject_filter)
        if grade_range and grade_range != 'all':
            if grade_range == 'k-3':
                slp_qs = slp_qs.filter(grade_label__in=['Kinder', 'Grade 1', 'Grade 2', 'Grade 3'])
            elif grade_range == '4-6':
                slp_qs = slp_qs.filter(grade_label__in=['Grade 4', 'Grade 5', 'Grade 6'])
            elif grade_range == '7-9':
                slp_qs = slp_qs.filter(grade_label__in=['Grade 7', 'Grade 8', 'Grade 9'])
            elif grade_range == '10-12':
                slp_qs = slp_qs.filter(grade_label__in=['Grade 10', 'Grade 11', 'Grade 12'])
            else:
                slp_qs = slp_qs.filter(grade_label=grade_range)
        if min_enrollment:
            try:
                slp_qs = slp_qs.filter(enrolment__gte=int(min_enrollment))
            except ValueError:
                pass
        if has_intervention and has_intervention != 'all':
            if has_intervention == 'yes':
                slp_qs = slp_qs.exclude(intervention_plan__isnull=True).exclude(intervention_plan__exact='')
            elif has_intervention == 'no':
                slp_qs = slp_qs.filter(intervention_plan__isnull=True) | slp_qs.filter(intervention_plan__exact='')
        return slp_qs

    results = []
    total = 0

    # Build data per view
    if kpi_part == 'slp':
        from dashboards.performance import QueryOptimizer
        # Pull all SLP rows once
        filter_params = {
            'subject_filter': subject_filter,
            'grade_range': grade_range,
            'min_enrollment': min_enrollment,
            'has_intervention': has_intervention,
        }
        slp_rows = QueryOptimizer.get_optimized_slp_queryset(periods, filter_params)
        # Apply multi-selects if present
        if selected_subjects:
            slp_rows = slp_rows.filter(subject__in=selected_subjects)
        if selected_grades:
            slp_rows = slp_rows.filter(grade_label__in=selected_grades)
        # Group by school
        slp_by_school = {}
        for row in slp_rows:
            sid = row.submission.school_id
            slp_by_school.setdefault(sid, []).append(row)

        # Build school blocks (include all schools, mark those without data)
        for school in schools_qs:
            rows = slp_by_school.get(school.id, [])
            subjects = {}
            # per-school totals to support summary view without full reload
            school_totals = {
                'enrolment': 0,
                'dnme': 0,
                'fs': 0,
                's': 0,
                'vs': 0,
                'o': 0,
            }
            for r in rows:
                s = r.subject or 'Unknown Subject'
                d = subjects.setdefault(s, {
                    'subject': s,
                    'enrolment': 0,
                    'fs': 0, 's': 0, 'vs': 0, 'o': 0,
                    'dnme': 0,
                    'grade_levels': set(),
                })
                d['enrolment'] += r.enrolment or 0
                d['fs'] += getattr(r, 'fs', 0) or 0
                d['s'] += r.s or 0
                d['vs'] += r.vs or 0
                d['o'] += r.o or 0
                d['dnme'] += r.dnme or 0
                d['grade_levels'].add(r.grade_label or 'Unknown')
                # accumulate school totals
                school_totals['enrolment'] += r.enrolment or 0
                school_totals['fs'] += getattr(r, 'fs', 0) or 0
                school_totals['s'] += r.s or 0
                school_totals['vs'] += r.vs or 0
                school_totals['o'] += r.o or 0
                school_totals['dnme'] += r.dnme or 0
            subj_list = []
            for s, d in subjects.items():
                proficient = (d['s'] + d['vs'] + d['o'])
                pr = round((proficient / d['enrolment'] * 100), 1) if d['enrolment'] else 0
                dr = round((d['dnme'] / d['enrolment'] * 100), 1) if d['enrolment'] else 0
                subj_list.append({
                    'subject': s,
                    'grade_levels': ', '.join(sorted(d['grade_levels'])),
                    'enrolment': d['enrolment'],
                    'fs_count': d['fs'],
                    'proficient_count': proficient,
                    'proficiency_rate': pr,
                    'dnme_count': d['dnme'],
                    'dnme_rate': dr,
                })
            # Inner sort
            reverse_subject_sort = (sort_dir == 'desc')
            if sort_by == 'subject_proficiency':
                subj_list.sort(key=lambda x: x['proficiency_rate'], reverse=reverse_subject_sort)
            elif sort_by == 'subject_name':
                subj_list.sort(key=lambda x: x['subject'], reverse=reverse_subject_sort)
            else:
                subj_list.sort(key=lambda x: x['subject'])

            # derive overall school-level SLP summary figures
            enrol = school_totals['enrolment'] or 0
            slp_overall = round(((school_totals['s'] + school_totals['vs'] + school_totals['o']) / enrol * 100), 1) if enrol else 0

            results.append({
                'school_id': school.id,
                'school_name': school.name,
                'district': school.district.name if school.district else 'N/A',
                'school_level': (
                    'Elementary' if (school.profile and school.profile.grade_span_end and school.profile.grade_span_end <= 6)
                    else 'Secondary' if (school.profile and school.profile.grade_span_start and school.profile.grade_span_start >= 7)
                    else 'Mixed'
                ),
                'total_subjects': len(subj_list),
                'subjects': subj_list,
                'school_totals': school_totals,
                'slp_overall': slp_overall,
                'has_data': bool(rows),
            })

        # School-level sort
        if sort_by == 'school_name':
            results.sort(key=lambda x: x['school_name'], reverse=(sort_dir=='desc'))
        elif sort_by == 'district':
            results.sort(key=lambda x: (x['district'] or '', x['school_name']), reverse=(sort_dir=='desc'))
        elif sort_by == 'performance':
            results.sort(key=lambda x: max([s['proficiency_rate'] for s in x['subjects']] or [0]), reverse=True)
        elif sort_by == 'enrollment':
            results.sort(key=lambda x: sum([s['enrolment'] for s in x['subjects']] or [0]), reverse=True)

        # Threshold filter (by SLP proficiency per subject)
        if performance_threshold != 'all':
            filtered = []
            for school_data in results:
                filt_subjects = []
                for s in school_data['subjects']:
                    if performance_threshold == 'high' and s['proficiency_rate'] >= 75:
                        filt_subjects.append(s)
                    elif performance_threshold == 'medium' and 50 <= s['proficiency_rate'] < 75:
                        filt_subjects.append(s)
                    elif performance_threshold == 'low' and s['proficiency_rate'] < 50:
                        filt_subjects.append(s)
                if filt_subjects:
                    sd = dict(school_data)
                    sd['subjects'] = filt_subjects
                    sd['total_subjects'] = len(filt_subjects)
                    filtered.append(sd)
            results = filtered

    elif kpi_part in ['reading','reading_crla','reading_philiri']:
        # Build per-school reading dataset
        from submissions.models import ReadingAssessmentCRLA, ReadingAssessmentPHILIRI
        from submissions.constants import CRLAProficiencyLevel, PHILIRIReadingLevel
        reading_detail = []
        # Ensure subtype aligns with kpi_part, if applicable
        if kpi_part == 'reading_crla':
            reading_type = 'crla'
        elif kpi_part == 'reading_philiri':
            reading_type = 'philiri'
        if reading_type == 'crla':
            rows = ReadingAssessmentCRLA.objects.filter(
                submission__period__school_year_start=int(school_year),
                submission__school__in=schools_qs,
                submission__status__in=['submitted','noted'],
                submission__form_template__is_active=True,
                period=assessment_timing
            ).select_related('submission__school', 'submission__school__district')
            grouped = {}
            for row in rows:
                school = row.submission.school
                entry = grouped.setdefault(school.id, {
                    'school': school,
                    'district': school.district.name if school.district else 'N/A',
                    'low_emerging': 0, 'high_emerging':0, 'developing':0, 'transitioning':0,
                    'total': 0,
                })
                total = row.total_learners()
                entry['total'] += total
                if row.level == CRLAProficiencyLevel.LOW_EMERGING:
                    entry['low_emerging'] += total
                elif row.level == CRLAProficiencyLevel.HIGH_EMERGING:
                    entry['high_emerging'] += total
                elif row.level == CRLAProficiencyLevel.DEVELOPING:
                    entry['developing'] += total
                elif row.level == CRLAProficiencyLevel.TRANSITIONING:
                    entry['transitioning'] += total
            def pct(n, d):
                return round((n/d)*100,1) if d else 0.0
            for _, data in grouped.items():
                d = data['total']
                reading_detail.append({
                    'school_id': data['school'].id,
                    'school_name': data['school'].name,
                    'district': data['district'],
                    'low_emerging_pct': pct(data['low_emerging'], d),
                    'high_emerging_pct': pct(data['high_emerging'], d),
                    'developing_pct': pct(data['developing'], d),
                    'transitioning_pct': pct(data['transitioning'], d),
                })
            results = reading_detail
            # Ensure all schools are present; add placeholders for no data
            have_ids = {r['school_id'] for r in results}
            for school in schools_qs:
                if school.id not in have_ids:
                    results.append({
                        'school_id': school.id,
                        'school_name': school.name,
                        'district': school.district.name if school.district else 'N/A',
                        'low_emerging_pct': 0.0,
                        'high_emerging_pct': 0.0,
                        'developing_pct': 0.0,
                        'transitioning_pct': 0.0,
                        'has_data': False,
                    })
            # Sorting
            reverse = (sort_dir=='desc')
            if sort_by == 'district':
                results.sort(key=lambda x:(x['district'] or '', x['school_name']), reverse=reverse)
            elif sort_by in ['low_emerging','high_emerging','developing','transitioning']:
                results.sort(key=lambda x: x.get(f"{sort_by}_pct", 0), reverse=reverse)
            else:
                results.sort(key=lambda x: x['school_name'], reverse=reverse)
        else:
            rows = ReadingAssessmentPHILIRI.objects.filter(
                submission__period__school_year_start=int(school_year),
                submission__school__in=schools_qs,
                submission__status__in=['submitted','noted'],
                submission__form_template__is_active=True,
                period=assessment_timing
            ).select_related('submission__school', 'submission__school__district')
            grouped = {}
            def total_row(r):
                return ((r.eng_grade_4 or 0)+(r.eng_grade_5 or 0)+(r.eng_grade_6 or 0)+(r.eng_grade_7 or 0)+
                        (r.eng_grade_8 or 0)+(r.eng_grade_9 or 0)+(r.eng_grade_10 or 0)+
                        (r.fil_grade_4 or 0)+(r.fil_grade_5 or 0)+(r.fil_grade_6 or 0)+(r.fil_grade_7 or 0)+
                        (r.fil_grade_8 or 0)+(r.fil_grade_9 or 0)+(r.fil_grade_10 or 0))
            for row in rows:
                school = row.submission.school
                entry = grouped.setdefault(school.id, {
                    'school': school,
                    'district': school.district.name if school.district else 'N/A',
                    'frustration': 0,'instructional':0,'independent':0,'total':0,
                })
                t = total_row(row)
                entry['total'] += t
                from submissions.constants import PHILIRIReadingLevel
                if row.level == PHILIRIReadingLevel.FRUSTRATION:
                    entry['frustration'] += t
                elif row.level == PHILIRIReadingLevel.INSTRUCTIONAL:
                    entry['instructional'] += t
                elif row.level == PHILIRIReadingLevel.INDEPENDENT:
                    entry['independent'] += t
            def pct2(n,d):
                return round((n/d)*100,1) if d else 0.0
            for _, data in grouped.items():
                d = data['total']
                results.append({
                    'school_id': data['school'].id,
                    'school_name': data['school'].name,
                    'district': data['district'],
                    'frustration_pct': pct2(data['frustration'], d),
                    'instructional_pct': pct2(data['instructional'], d),
                    'independent_pct': pct2(data['independent'], d),
                })
            # Add placeholders for schools with no data
            have_ids = {r['school_id'] for r in results}
            for school in schools_qs:
                if school.id not in have_ids:
                    results.append({
                        'school_id': school.id,
                        'school_name': school.name,
                        'district': school.district.name if school.district else 'N/A',
                        'frustration_pct': 0.0,
                        'instructional_pct': 0.0,
                        'independent_pct': 0.0,
                        'has_data': False,
                    })
            reverse = (sort_dir=='desc')
            if sort_by == 'district':
                results.sort(key=lambda x:(x['district'] or '', x['school_name']), reverse=reverse)
            elif sort_by in ['frustration','instructional','independent']:
                results.sort(key=lambda x: x.get(f"{sort_by}_pct", 0), reverse=reverse)
            else:
                results.sort(key=lambda x: x['school_name'], reverse=reverse)

    elif kpi_part == 'rma':
        from submissions.models import Form1RMARow
        rma_rows = Form1RMARow.objects.filter(
            submission__period__in=periods,
            submission__school__in=schools_qs,
            submission__status__in=['submitted','noted'],
            submission__form_template__is_active=True,
        ).select_related('submission__school', 'submission__school__district')
        if rma_grade and rma_grade != 'all':
            rma_rows = rma_rows.filter(grade_label=rma_grade)
        grouped = {}
        for row in rma_rows:
            key = (row.submission.school_id, row.grade_label)
            entry = grouped.setdefault(key, {
                'school': row.submission.school,
                'district': row.submission.school.district.name if row.submission.school.district else 'N/A',
                'grade_label': row.grade_label,
                'enrolment': 0,
                'emerging_not_proficient': 0,
                'emerging_low_proficient': 0,
                'developing_nearly_proficient': 0,
                'transitioning_proficient': 0,
                'at_grade_level': 0,
            })
            entry['enrolment'] += row.enrolment or 0
            entry['emerging_not_proficient'] += row.emerging_not_proficient or 0
            entry['emerging_low_proficient'] += row.emerging_low_proficient or 0
            entry['developing_nearly_proficient'] += row.developing_nearly_proficient or 0
            entry['transitioning_proficient'] += row.transitioning_proficient or 0
            entry['at_grade_level'] += row.at_grade_level or 0
        def pct(n,d):
            return round((n/d)*100,1) if d else 0.0
        for (_, _), data in grouped.items():
            den = data['enrolment']
            results.append({
                'school_id': data['school'].id,
                'school_name': data['school'].name,
                'district': data['district'],
                'grade_label': data['grade_label'],
                'not_proficient_pct': pct(data['emerging_not_proficient'], den),
                'low_proficient_pct': pct(data['emerging_low_proficient'], den),
                'nearly_proficient_pct': pct(data['developing_nearly_proficient'], den),
                'proficient_pct': pct(data['transitioning_proficient'], den),
                'at_grade_level_pct': pct(data['at_grade_level'], den),
                'has_data': True,
            })
        # Add placeholder rows for schools with no data
        have_ids = {r['school_id'] for r in results}
        for school in schools_qs:
            if school.id not in have_ids:
                results.append({
                    'school_id': school.id,
                    'school_name': school.name,
                    'district': school.district.name if school.district else 'N/A',
                    'grade_label': '',
                    'not_proficient_pct': 0.0,
                    'low_proficient_pct': 0.0,
                    'nearly_proficient_pct': 0.0,
                    'proficient_pct': 0.0,
                    'at_grade_level_pct': 0.0,
                    'has_data': False,
                })
        reverse = (sort_dir=='desc')
        if sort_by == 'district':
            results.sort(key=lambda x:(x['district'] or '', x['school_name'], x.get('grade_label') or ''), reverse=reverse)
        elif sort_by == 'grade':
            results.sort(key=lambda x: x.get('grade_label') or '', reverse=reverse)
        elif sort_by in ['not_proficient','low_proficient','nearly_proficient','proficient','at_grade_level']:
            results.sort(key=lambda x: x.get(f"{sort_by}_pct", 0), reverse=reverse)
        else:
            results.sort(key=lambda x: x['school_name'], reverse=reverse)

    elif kpi_part == 'supervision':
        from submissions.models import Form1SupervisionRow
        supervision_rows = Form1SupervisionRow.objects.filter(
            submission__period__in=periods,
            submission__school__in=schools_qs,
            submission__status__in=['submitted','noted'],
            submission__form_template__is_active=True,
        ).select_related('submission__school', 'submission__school__district')
        grouped = {}
        for row in supervision_rows:
            school = row.submission.school
            entry = grouped.setdefault(school.id, {
                'school': school,
                'district': school.district.name if school.district else 'N/A',
                'total_teachers': 0,
                'teachers_supervised_ta': 0,
            })
            entry['total_teachers'] += row.total_teachers or 0
            entry['teachers_supervised_ta'] += row.teachers_supervised_observed_ta or 0
        for _, data in grouped.items():
            total_t = data['total_teachers']
            supervised = data['teachers_supervised_ta']
            pct_ta = round((supervised/total_t)*100,1) if total_t else 0.0
            results.append({
                'school_id': data['school'].id,
                'school_name': data['school'].name,
                'district': data['district'],
                'total_teachers': total_t,
                'teachers_supervised_ta': supervised,
                'percent_ta': pct_ta,
                'has_data': True,
            })
        # Add placeholders for schools with no data
        have_ids = {r['school_id'] for r in results}
        for school in schools_qs:
            if school.id not in have_ids:
                results.append({
                    'school_id': school.id,
                    'school_name': school.name,
                    'district': school.district.name if school.district else 'N/A',
                    'total_teachers': 0,
                    'teachers_supervised_ta': 0,
                    'percent_ta': 0.0,
                    'has_data': False,
                })
        reverse = (sort_dir=='desc')
        if sort_by == 'district':
            results.sort(key=lambda x:(x['district'] or '', x['school_name']), reverse=reverse)
        elif sort_by in ['percent_ta','total_teachers','teachers_supervised_ta']:
            results.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)
        else:
            results.sort(key=lambda x: x['school_name'], reverse=reverse)

    elif kpi_part == 'adm':
        from submissions.models import Form1ADMHeader, Form1ADMRow
        # Identify schools offering ADM
        headers = Form1ADMHeader.objects.filter(
            submission__period__in=periods,
            submission__school__in=schools_qs,
            submission__status__in=['submitted','noted'],
            submission__form_template__is_active=True,
            is_offered=True
        ).select_related('submission__school', 'submission__school__district')
        offered_school_ids = {h.submission.school_id for h in headers}

        rows = Form1ADMRow.objects.filter(
            submission__period__in=periods,
            submission__school__in=schools_qs,
            submission__status__in=['submitted','noted'],
            submission__form_template__is_active=True,
            submission__form1_adm_header__is_offered=True
        ).select_related('submission__school', 'submission__school__district')

        grouped = {}
        for r in rows:
            sid = r.submission.school_id
            entry = grouped.setdefault(sid, {
                'school': r.submission.school,
                'district': r.submission.school.district.name if r.submission.school.district else 'N/A',
                'program_count': 0,
                'physical_sum': 0.0,
                'funds_sum': 0.0,
            })
            entry['program_count'] += 1
            try:
                entry['physical_sum'] += float(r.ppas_physical_percent or 0)
            except Exception:
                entry['physical_sum'] += 0.0
            try:
                entry['funds_sum'] += float(r.funds_percent_obligated or 0)
            except Exception:
                entry['funds_sum'] += 0.0

        # Build results for all schools with ADM offered or data
        for school in schools_qs:
            data = grouped.get(school.id)
            offers = school.id in offered_school_ids
            pc = data['program_count'] if data else 0
            phys_avg = round((data['physical_sum'] / pc), 1) if data and pc else 0.0
            funds_avg = round((data['funds_sum'] / pc), 1) if data and pc else 0.0
            overall = round(((phys_avg + funds_avg) / 2), 1) if (phys_avg or funds_avg) else 0.0
            results.append({
                'school_id': school.id,
                'school_name': (data['school'].name if data else school.name),
                'district': (data['district'] if data else (school.district.name if school.district else 'N/A')),
                'offers_adm': offers,
                'program_count': pc,
                'physical_avg': phys_avg,
                'funds_avg': funds_avg,
                'overall_adm': overall,
                'has_data': bool(data),
            })

        reverse = (sort_dir=='desc')
        if sort_by == 'district':
            results.sort(key=lambda x:(x['district'] or '', x['school_name']), reverse=reverse)
        elif sort_by == 'overall_adm':
            results.sort(key=lambda x: x.get('overall_adm', 0), reverse=reverse)
        elif sort_by == 'physical':
            results.sort(key=lambda x: x.get('physical_avg', 0), reverse=reverse)
        elif sort_by == 'funds':
            results.sort(key=lambda x: x.get('funds_avg', 0), reverse=reverse)
        elif sort_by == 'programs':
            results.sort(key=lambda x: x.get('program_count', 0), reverse=reverse)
        else:
            results.sort(key=lambda x: x['school_name'], reverse=reverse)

    else:
        # KPI overview table
        from dashboards.kpi_calculators import calculate_school_kpis_simple
        def perf_class(p):
            return 'performance-low' if p < 50 else ('performance-medium' if p < 75 else 'performance-high')
        from submissions.models import Form1RMARow
        for school in schools_qs:
            school_kpis = DashboardCache.get_cached_kpi_data(school.id, periods, 'smme')
            if not school_kpis:
                school_kpis = calculate_school_kpis_simple(school, periods, 'smme')
                DashboardCache.set_cached_kpi_data(school.id, periods, 'smme', school_kpis)
            else:
                # Defensive cache refresh: if cache reports RMA > 0 but no underlying rows remain, recalc.
                rma_exists = Form1RMARow.objects.filter(
                    submission__school=school,
                    submission__period__in=periods,
                    submission__status__in=['submitted','noted'],
                    submission__form_template__is_active=True,
                ).exists()
                if not rma_exists and (school_kpis.get('rma') or 0) > 0:
                    school_kpis = calculate_school_kpis_simple(school, periods, 'smme')
                    DashboardCache.set_cached_kpi_data(school.id, periods, 'smme', school_kpis)
            level = 'Mixed'
            if school.profile:
                if getattr(school.profile, 'grade_span_end', None) and school.profile.grade_span_end <= 6:
                    level = 'Elementary'
                elif getattr(school.profile, 'grade_span_start', None) and school.profile.grade_span_start >= 7:
                    level = 'Secondary'
            results.append({
                'school_id': school.id,
                'school_name': school.name,
                'district': school.district.name if school.district else 'N/A',
                'school_level': level,
                'implementation': school_kpis['implementation'],
                'impl_access': school_kpis.get('implementation_access', 0),
                'impl_quality': school_kpis.get('implementation_quality', 0),
                'impl_equity': school_kpis.get('implementation_equity', 0),
                'impl_enabling': school_kpis.get('implementation_enabling', 0),
                'slp': school_kpis['slp'],
                'reading_crla': school_kpis['reading_crla'],
                'reading_philiri': school_kpis['reading_philiri'],
                'rma': school_kpis['rma'],
                'supervision': school_kpis['supervision'],
                'adm': school_kpis['adm'],
                'has_data': bool(school_kpis.get('has_data', False)),
            })
        # Threshold filter (using SLP as key metric for overview)
        if performance_threshold != 'all':
            if performance_threshold == 'high':
                results = [r for r in results if r['slp'] >= 75]
            elif performance_threshold == 'medium':
                results = [r for r in results if 50 <= r['slp'] < 75]
            elif performance_threshold == 'low':
                results = [r for r in results if r['slp'] < 50]
        reverse = (sort_dir=='desc')
        if sort_by == 'school_name':
            results.sort(key=lambda x: x['school_name'], reverse=reverse)
        elif sort_by == 'district':
            results.sort(key=lambda x:(x['district'] or '', x['school_name']), reverse=reverse)
        elif sort_by == 'performance':
            if kpi_part == 'implementation':
                results.sort(key=lambda x: x['implementation'], reverse=reverse)
            else:
                results.sort(key=lambda x: x['slp'], reverse=reverse)
        elif kpi_part == 'implementation' and sort_by in ['implementation','impl_access','impl_quality','impl_equity','impl_enabling']:
            results.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)
        elif sort_by == 'enrollment':
            results.sort(key=lambda x: x['slp'], reverse=reverse)

    # Pagination slicing
    total = len(results)
    start = (page - 1) * page_size
    end = start + page_size
    paged = results[start:end]

    from django.conf import settings as _dj_settings
    from django.db import connection
    import time as _time
    _t1 = _time.time()
    resp = JsonResponse({
        'view': kpi_part,
        'page': page,
        'page_size': page_size,
        'total': total,
        'results': paged,
    })
    # Attach perf headers in DEBUG for quick inspection
    if getattr(_dj_settings, 'DEBUG', False):
        _elapsed = _time.time() - _t1
        _q = len(connection.queries) if hasattr(connection, 'queries') else 0
        resp['X-Perf-Elapsed'] = f"{_elapsed:.3f}s"
        resp['X-Perf-Queries'] = str(_q)
    return resp


@login_required
def smme_kpi_dashboard_data(request):
    """AJAX API endpoint for SMME KPI Dashboard data (returns JSON)"""
    from django.http import JsonResponse
    from organizations.models import Section, School
    from dashboards.kpi_calculators import calculate_all_kpis_for_period
    
    user = request.user
    _require_reviewer_access(user)
    
    # Get filters from request
    school_year = request.GET.get('school_year')
    quarter_filter = request.GET.get('quarter', 'all')
    school_filter = request.GET.get('school', 'all')
    kpi_metric = request.GET.get('kpi_metric', 'dnme')
    
    # Get available school years
    school_years = Period.objects.values_list(
        'school_year_start', flat=True
    ).distinct().order_by('-school_year_start')
    
    # Default to latest school year if not specified
    if not school_year and school_years:
        school_year = str(school_years[0])
    
    # Get periods based on quarter filter
    if quarter_filter == 'all' and school_year:
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
        ).order_by('display_order')
    elif quarter_filter != 'all' and school_year:
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__iexact=quarter_filter
        ).order_by('display_order')
    else:
        periods = Period.objects.none()
    
    # Get schools based on filter
    if school_filter == 'all':
        schools = School.objects.all().order_by('name')
    else:
        schools = School.objects.filter(id=int(school_filter))
    
    total_schools = School.objects.count()
    
    # Calculate KPIs for each period
    kpi_data = []
    
    for period in periods:
        if school_filter == 'all':
            period_kpis = calculate_all_kpis_for_period(period, 'smme')
        else:
            from dashboards.kpi_calculators import calculate_all_kpis
            school_obj = schools.first()
            submissions = Form1SLPRow.objects.filter(
                submission__period=period,
                submission__school=school_obj
            )
            
            if submissions.exists():
                period_kpis = calculate_all_kpis(submissions)
            else:
                period_kpis = {
                    'dnme': {'dnme_percentage': 0, 'dnme_count': 0, 'total_schools': 0},
                    'implementation_areas': {
                        'access_percentage': 0,
                        'quality_percentage': 0,
                        'equity_percentage': 0,
                        'governance_percentage': 0,
                        'management_percentage': 0,
                        'leadership_percentage': 0,
                    }
                }
        
        # Extract metric value
        if kpi_metric == 'dnme':
            metric_value = period_kpis['dnme']['dnme_percentage']
        elif kpi_metric == 'access':
            metric_value = period_kpis['implementation_areas']['access_percentage']
        elif kpi_metric == 'quality':
            metric_value = period_kpis['implementation_areas']['quality_percentage']
        elif kpi_metric == 'governance':
            metric_value = period_kpis['implementation_areas']['governance_percentage']
        elif kpi_metric == 'management':
            metric_value = period_kpis['implementation_areas']['management_percentage']
        elif kpi_metric == 'leadership':
            metric_value = period_kpis['implementation_areas']['leadership_percentage']
        else:
            metric_value = 0
        
        kpi_data.append({
            'label': period.quarter_tag or period.label,
            'kpis': period_kpis,
            'metric_value': metric_value,
        })
    
    # Calculate summary statistics
    if kpi_data:
        avg_dnme = round(sum(d['kpis']['dnme']['dnme_percentage'] for d in kpi_data) / len(kpi_data), 1)
        avg_access = round(sum(d['kpis']['implementation_areas']['access_percentage'] for d in kpi_data) / len(kpi_data), 1)
        avg_quality = round(sum(d['kpis']['implementation_areas']['quality_percentage'] for d in kpi_data) / len(kpi_data), 1)
        avg_governance = round(sum(d['kpis']['implementation_areas']['governance_percentage'] for d in kpi_data) / len(kpi_data), 1)
        avg_management = round(sum(d['kpis']['implementation_areas']['management_percentage'] for d in kpi_data) / len(kpi_data), 1)
        avg_leadership = round(sum(d['kpis']['implementation_areas']['leadership_percentage'] for d in kpi_data) / len(kpi_data), 1)
    else:
        avg_dnme = avg_access = avg_quality = avg_governance = avg_management = avg_leadership = 0
    
    # Prepare response data
    response_data = {
        'chart_data': {
            'labels': [d['label'] for d in kpi_data],
            'values': [d['metric_value'] for d in kpi_data],
        },
        'summary': {
            'total_schools': total_schools,
            'avg_dnme': avg_dnme,
            'avg_access': avg_access,
            'avg_quality': avg_quality,
            'avg_governance': avg_governance,
            'avg_management': avg_management,
            'avg_leadership': avg_leadership,
            'periods_count': len(kpi_data),
        }
    }
    
    return JsonResponse(response_data)


@login_required
def smme_kpi_comparison(request):
    """API endpoint for school comparison data (returns JSON)"""
    from django.http import JsonResponse
    from organizations.models import School
    from submissions.models import Form1SLPLLCEntry
    from dashboards.kpi_calculators import calculate_all_kpis
    
    user = request.user
    _require_reviewer_access(user)
    
    # Get filters
    school_year = request.GET.get('school_year')
    quarter = request.GET.get('quarter', 'all')
    kpi_metric = request.GET.get('kpi_metric', 'dnme')
    school_ids = request.GET.get('school_ids', '').split(',')
    
    if not school_year or not school_ids or school_ids == ['']:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        school_year_int = int(school_year)
    except ValueError:
        return JsonResponse({'error': 'Invalid school year'}, status=400)
    
    # Get periods based on quarter filter
    if quarter == 'all':
        periods = Period.objects.filter(
            school_year_start=school_year_int,
            quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
        ).order_by('display_order')
    else:
        periods = Period.objects.filter(
            school_year_start=school_year_int,
            quarter_tag__iexact=quarter
        ).order_by('display_order')
    
    if not periods.exists():
        return JsonResponse({'error': 'No periods found'}, status=404)
    
    # Get schools
    try:
        school_ids_int = [int(sid) for sid in school_ids if sid]
    except ValueError:
        return JsonResponse({'error': 'Invalid school IDs'}, status=400)
    
    schools = School.objects.filter(id__in=school_ids_int).order_by('name')
    
    if not schools.exists():
        return JsonResponse({'error': 'No schools found'}, status=404)
    
    # Calculate KPIs for each school across periods
    comparison_data = []
    
    for school in schools:
        school_kpi_values = []
        
        for period in periods:
            # Get SLP rows for this school and period
            submissions = Form1SLPRow.objects.filter(
                submission__school=school,
                submission__period=period
            )
            
            if submissions.exists():
                kpis = calculate_all_kpis(submissions)
                
                # Extract the specific metric value
                if kpi_metric == 'dnme':
                    value = kpis['dnme']['dnme_percentage']
                elif kpi_metric == 'access':
                    value = kpis['implementation_areas']['access_percentage']
                elif kpi_metric == 'quality':
                    value = kpis['implementation_areas']['quality_percentage']
                elif kpi_metric == 'equity':
                    value = kpis['implementation_areas']['equity_percentage']
                elif kpi_metric == 'governance':
                    value = kpis['implementation_areas']['governance_percentage']
                elif kpi_metric == 'management':
                    value = kpis['implementation_areas']['management_percentage']
                elif kpi_metric == 'leadership':
                    value = kpis['implementation_areas']['leadership_percentage']
                else:
                    value = 0
                
                school_kpi_values.append(round(value, 1))
            else:
                school_kpi_values.append(0)
        
        comparison_data.append({
            'name': school.name,
            'kpi_values': school_kpi_values
        })
    
    # Get KPI display name
    kpi_names = {
        'dnme': 'DNME Percentage',
        'access': 'Access Implementation Area',
        'quality': 'Quality Implementation Area',
        'equity': 'Equity Implementation Area',
        'governance': 'Governance Implementation Area',
        'management': 'Management Implementation Area',
        'leadership': 'Leadership Implementation Area',
    }
    
    return JsonResponse({
        'schools': comparison_data,
        'quarters': [p.quarter_tag or p.label for p in periods],
        'kpi_name': kpi_names.get(kpi_metric, 'Unknown KPI')
    })


@login_required
def smme_kpi_export_csv(request):
    """Export SMME KPI data for the current dashboard view and filters."""
    user = request.user
    _require_reviewer_access(user)

    # Align filters with dashboard
    from organizations.models import School, District
    from submissions.models import Form1SLPRow, Form1RMARow, ReadingAssessmentCRLA, ReadingAssessmentPHILIRI, Form1SupervisionRow
    from submissions.constants import CRLAProficiencyLevel, PHILIRIReadingLevel, RMAGradeLabel

    school_year = request.GET.get('school_year')
    quarter = request.GET.get('quarter', 'all')
    form_period = request.GET.get('form_period', 'all')
    district_id = request.GET.get('district')
    school_id = request.GET.get('school')
    school_level = request.GET.get('school_level', 'all')
    kpi_part = request.GET.get('kpi_part', 'all')
    # Support missing-only export for overview when a specific form and single quarter are selected
    only_missing = str(request.GET.get('only_missing', '0')).lower() in ('1', 'true', 'yes', 'on')
    form_template_code = request.GET.get('form_template', 'all')

    # Advanced filters for views
    subject_filter = request.GET.get('subject', 'all')
    # Multi-select subjects/grades take precedence when provided
    selected_subjects = [s for s in request.GET.getlist('subjects') if s]
    grade_range = request.GET.get('grade_range', 'all')
    selected_grades = [g for g in request.GET.getlist('grades') if g]
    min_enrollment = request.GET.get('min_enrollment', '')
    has_intervention = request.GET.get('has_intervention', 'all')
    reading_type = request.GET.get('reading_type', 'crla')
    assessment_timing = request.GET.get('assessment_timing', 'eosy')

    # Determine periods
    if quarter == 'all' and school_year:
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
        ).order_by('display_order')
    elif quarter != 'all' and school_year:
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__iexact=quarter
        ).order_by('display_order')
    else:
        periods = Period.objects.none()

    if form_period and form_period != 'all':
        try:
            selected_form_period = Period.objects.get(id=int(form_period))
            periods = Period.objects.filter(id=selected_form_period.id)
        except (Period.DoesNotExist, ValueError):
            pass

    # Determine schools
    schools_qs = School.objects.select_related('district', 'profile').order_by('name')
    if district_id and district_id != 'all':
        schools_qs = schools_qs.filter(district_id=district_id)
    if school_id and school_id != 'all':
        schools_qs = schools_qs.filter(id=school_id)
    if school_level and school_level != 'all':
        if school_level == 'elementary':
            schools_qs = schools_qs.filter(profile__grade_span_end__lte=6)
        elif school_level == 'secondary':
            schools_qs = schools_qs.filter(profile__grade_span_start__gte=7)

    # Prepare CSV
    # Build a descriptive filename reflecting filters
    district_label = 'all-districts'
    if district_id and district_id != 'all':
        try:
            district_label = District.objects.get(id=int(district_id)).name.replace(' ', '-')
        except Exception:
            district_label = f'district-{district_id}'
    year_label = f"sy{school_year}-{int(school_year)+1}" if school_year else 'sy-all'
    quarter_label = quarter.lower() if quarter and quarter != 'all' else 'all-quarters'
    # Enrich filename with subject/grade/slp_mode when applicable
    def _slug(s: str) -> str:
        import re
        s = (s or '').strip().lower()
        s = re.sub(r'\s+', '-', s)
        s = re.sub(r'[^a-z0-9\-]+', '', s)
        return s or 'na'

    filename_suffix = f"{kpi_part}-{year_label}-{quarter_label}-{district_label}"
    if kpi_part == 'slp':
        if subject_filter and subject_filter != 'all':
            filename_suffix += f"-subject-{_slug(subject_filter)}"
        if grade_range and grade_range != 'all':
            filename_suffix += f"-grade-{_slug(grade_range)}"
        slp_mode = request.GET.get('slp_mode', 'summary')
        if slp_mode and slp_mode != 'summary':
            filename_suffix += f"-mode-{_slug(slp_mode)}"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="smme_{filename_suffix}.csv"'
    writer = csv.writer(response)

    # Helper
    def perf_class(percent: float) -> str:
        if percent < 50:
            return 'low'
        if percent < 75:
            return 'medium'
        return 'high'

    # Export based on selected KPI part
    if kpi_part == 'slp':
        slp_mode = request.GET.get('slp_mode', 'summary')

        # Filters
        slp_qs = Form1SLPRow.objects.filter(
            submission__period__in=periods,
            submission__school__in=schools_qs,
            submission__status__in=['submitted', 'noted']
        ).select_related('submission__school', 'submission__school__district')
        # Apply multi-selects if present; otherwise use legacy filters
        if selected_subjects:
            slp_qs = slp_qs.filter(subject__in=selected_subjects)
        elif subject_filter and subject_filter != 'all':
            slp_qs = slp_qs.filter(subject=subject_filter)
        if selected_grades:
            slp_qs = slp_qs.filter(grade_label__in=selected_grades)
        elif grade_range and grade_range != 'all':
            if grade_range == 'k-3':
                slp_qs = slp_qs.filter(grade_label__in=['Kinder', 'Grade 1', 'Grade 2', 'Grade 3'])
            elif grade_range == '4-6':
                slp_qs = slp_qs.filter(grade_label__in=['Grade 4', 'Grade 5', 'Grade 6'])
            elif grade_range == '7-9':
                slp_qs = slp_qs.filter(grade_label__in=['Grade 7', 'Grade 8', 'Grade 9'])
            elif grade_range == '10-12':
                slp_qs = slp_qs.filter(grade_label__in=['Grade 10', 'Grade 11', 'Grade 12'])
        if min_enrollment:
            try:
                slp_qs = slp_qs.filter(enrolment__gte=int(min_enrollment))
            except ValueError:
                pass
        if has_intervention and has_intervention != 'all':
            if has_intervention == 'yes':
                slp_qs = slp_qs.exclude(intervention_plan__isnull=True).exclude(intervention_plan__exact='')
            elif has_intervention == 'no':
                slp_qs = slp_qs.filter(intervention_plan__isnull=True) | slp_qs.filter(intervention_plan__exact='')

        if slp_mode == 'detail':
            # Subject-detail export
            writer.writerow(['School', 'District', 'Subject', 'Grade Levels', 'Enrolment', 'Proficient Count', 'Proficiency %', 'DNME Count', 'DNME %'])
            rows = slp_qs.order_by('submission__school__name','subject','grade_label')
            # Group per (school, subject)
            from collections import defaultdict
            grouped = {}
            for r in rows:
                key = (r.submission.school_id, (r.subject or 'Unknown').strip())
                e = grouped.setdefault(key, {
                    'school': r.submission.school,
                    'district': r.submission.school.district.name if r.submission.school.district else 'N/A',
                    'subject': (r.subject or 'Unknown').strip(),
                    'grades': set(),
                    'enrolment': 0,
                    'prof': 0,
                    'dnme': 0,
                })
                e['enrolment'] += (r.enrolment or 0)
                e['prof'] += (r.s or 0) + (r.vs or 0) + (r.o or 0)
                e['dnme'] += (r.dnme or 0)
                if r.grade_label:
                    e['grades'].add(r.grade_label)
            def pct(n,d):
                return round((n/d)*100,1) if d else 0.0
            for e in grouped.values():
                d = e['enrolment']
                writer.writerow([
                    e['school'].name,
                    e['district'],
                    e['subject'],
                    ', '.join(sorted(e['grades'])) if e['grades'] else '',
                    d,
                    e['prof'],
                    pct(e['prof'], d),
                    e['dnme'],
                    pct(e['dnme'], d),
                ])
        else:
            # Summary (per-school distribution)
            writer.writerow(['School', 'District', 'DNME %', 'FS %', 'S %', 'VS %', 'O %', 'Overall SLP % (S+VS+O)', 'Enrollment'])
            grouped = {}
            for r in slp_qs:
                s = r.submission.school
                e = grouped.setdefault(s.id, {
                    'school': s,
                    'district': s.district.name if s.district else 'N/A',
                    'enrolment': 0,
                    'dnme': 0,
                    'fs': 0,
                    's': 0,
                    'vs': 0,
                    'o': 0,
                })
                e['enrolment'] += (r.enrolment or 0)
                e['dnme'] += (r.dnme or 0)
                e['fs'] += (r.fs or 0)
                e['s'] += (r.s or 0)
                e['vs'] += (r.vs or 0)
                e['o'] += (r.o or 0)
            def pct(n, d):
                return round((n / d) * 100, 1) if d else 0.0
            for e in grouped.values():
                d = e['enrolment']
                writer.writerow([
                    e['school'].name,
                    e['district'],
                    pct(e['dnme'], d),
                    pct(e['fs'], d),
                    pct(e['s'], d),
                    pct(e['vs'], d),
                    pct(e['o'], d),
                    pct(e['s'] + e['vs'] + e['o'], d),
                    d,
                ])

    elif kpi_part == 'reading':
        if reading_type == 'crla':
            writer.writerow(['School', 'District', 'Low Emerging %', 'High Emerging %', 'Developing %', 'Transitioning %', 'Total Learners'])
            rows = ReadingAssessmentCRLA.objects.filter(
                submission__period__school_year_start=int(school_year) if school_year else F('submission__period__school_year_start'),
                submission__school__in=schools_qs,
                period=assessment_timing
            ).select_related('submission__school', 'submission__school__district')
            grouped = {}
            for r in rows:
                school = r.submission.school
                e = grouped.setdefault(school.id, {'school': school, 'district': school.district.name if school.district else 'N/A', 'low':0,'high':0,'dev':0,'tran':0,'total':0})
                total = r.total_learners()
                e['total'] += total
                if r.level == CRLAProficiencyLevel.LOW_EMERGING:
                    e['low'] += total
                elif r.level == CRLAProficiencyLevel.HIGH_EMERGING:
                    e['high'] += total
                elif r.level == CRLAProficiencyLevel.DEVELOPING:
                    e['dev'] += total
                elif r.level == CRLAProficiencyLevel.TRANSITIONING:
                    e['tran'] += total
            def pct(n,d):
                return round((n/d)*100,1) if d else 0.0
            for e in grouped.values():
                d=e['total']
                writer.writerow([e['school'].name, e['district'], pct(e['low'],d), pct(e['high'],d), pct(e['dev'],d), pct(e['tran'],d), d])
        else:
            writer.writerow(['School', 'District', 'Frustration %', 'Instructional %', 'Independent %', 'Total Learners'])
            rows = ReadingAssessmentPHILIRI.objects.filter(
                submission__period__school_year_start=int(school_year) if school_year else F('submission__period__school_year_start'),
                submission__school__in=schools_qs,
                period=assessment_timing
            ).select_related('submission__school', 'submission__school__district')
            grouped = {}
            def total_row(r):
                return ((r.eng_grade_4 or 0)+(r.eng_grade_5 or 0)+(r.eng_grade_6 or 0)+(r.eng_grade_7 or 0)+(r.eng_grade_8 or 0)+(r.eng_grade_9 or 0)+(r.eng_grade_10 or 0)+
                        (r.fil_grade_4 or 0)+(r.fil_grade_5 or 0)+(r.fil_grade_6 or 0)+(r.fil_grade_7 or 0)+(r.fil_grade_8 or 0)+(r.fil_grade_9 or 0)+(r.fil_grade_10 or 0))
            for r in rows:
                school=r.submission.school
                e=grouped.setdefault(school.id, {'school':school,'district': school.district.name if school.district else 'N/A','frus':0,'inst':0,'indep':0,'total':0})
                total=total_row(r)
                e['total']+=total
                if r.level == PHILIRIReadingLevel.FRUSTRATION:
                    e['frus']+=total
                elif r.level == PHILIRIReadingLevel.INSTRUCTIONAL:
                    e['inst']+=total
                elif r.level == PHILIRIReadingLevel.INDEPENDENT:
                    e['indep']+=total
            def pct2(n,d):
                return round((n/d)*100,1) if d else 0.0
            for e in grouped.values():
                d=e['total']
                writer.writerow([e['school'].name, e['district'], pct2(e['frus'],d), pct2(e['inst'],d), pct2(e['indep'],d), d])

    elif kpi_part == 'rma':
        writer.writerow(['School', 'District', 'Grade', 'Not Proficient %', 'Low Proficient %', 'Nearly Proficient %', 'Proficient %', 'At Grade Level %', 'Enrollment'])
        rma_rows = Form1RMARow.objects.filter(
            submission__period__in=periods,
            submission__school__in=schools_qs
        ).select_related('submission__school', 'submission__school__district')
        rma_grade = request.GET.get('rma_grade', 'all')
        if rma_grade and rma_grade != 'all':
            rma_rows = rma_rows.filter(grade_label=rma_grade)
        for row in rma_rows.order_by('submission__school__name','grade_label'):
            total = row.enrolment or 0
            def pct(n):
                return round((n/total)*100,1) if total else 0.0
            writer.writerow([
                row.submission.school.name,
                row.submission.school.district.name if row.submission.school.district else 'N/A',
                row.grade_label,
                pct(row.emerging_not_proficient + row.low_proficient_below25),
                pct(row.low_proficient_25_49),
                pct(row.nearly_proficient_50_74),
                pct(row.proficient_75_84),
                pct(row.at_grade_level_85_100),
                total,
            ])

    elif kpi_part == 'supervision':
        writer.writerow(['School', 'District', 'Total Teachers', 'Teachers Supervised & TA', '% Provided TA'])
        rows = Form1SupervisionRow.objects.filter(
            submission__period__in=periods,
            submission__school__in=schools_qs
        ).select_related('submission__school', 'submission__school__district')
        data = {}
        for r in rows:
            s=r.submission.school
            e=data.setdefault(s.id, {'school':s,'district': s.district.name if s.district else 'N/A','total_teachers':0,'teachers_supervised_ta':0})
            e['total_teachers'] += (r.total_teachers or 0)
            e['teachers_supervised_ta'] += (r.teachers_supervised_observed_ta or 0)
        for e in data.values():
            total=e['total_teachers']; ta=e['teachers_supervised_ta']
            pct = round((ta/total)*100,1) if total else 0.0
            writer.writerow([e['school'].name, e['district'], total, ta, pct])

    else:
        # Overall per-school KPI snapshot
        # If missing-only is requested and eligible, limit to missing schools only
        can_apply_missing = (
            only_missing and form_template_code and form_template_code != 'all' and periods.exists() and periods.count() == 1
        )
        if can_apply_missing:
            try:
                from submissions.models import Submission, FormTemplate as _FT
                ft = _FT.objects.filter(code=form_template_code).first()
                if ft:
                    all_ids = list(schools_qs.values_list('id', flat=True))
                    period_ids = list(periods.values_list('id', flat=True))
                    submitted_ids = set(
                        Submission.objects.filter(
                            school_id__in=all_ids,
                            form_template=ft,
                            period_id__in=period_ids,
                            status__in=['submitted', 'noted']
                        ).values_list('school_id', flat=True)
                    )
                    missing_ids = list(set(all_ids) - submitted_ids)
                    if missing_ids:
                        schools_qs = schools_qs.filter(id__in=missing_ids)
                    else:
                        schools_qs = schools_qs.none()
            except Exception:
                # Fail-open; keep full queryset
                pass
        from dashboards.kpi_calculators import calculate_school_kpis_simple
        writer.writerow(['School', 'District', 'Level', '% Implementation', 'SLP %', 'Reading (CRLA) %', 'Reading (PHILIRI) %', 'RMA %', 'Supervision %', 'ADM %'])
        for school in schools_qs:
            kpis = calculate_school_kpis_simple(school, periods, 'smme')
            # Determine school level
            level = 'Mixed'
            if school.profile:
                if school.profile.grade_span_end and school.profile.grade_span_end <= 6:
                    level = 'Elementary'
                elif school.profile.grade_span_start and school.profile.grade_span_start >= 7:
                    level = 'Secondary'
            writer.writerow([
                school.name,
                school.district.name if school.district else 'N/A',
                level,
                kpis['implementation'],
                kpis['slp'],
                kpis['reading_crla'],
                kpis['reading_philiri'],
                kpis['rma'],
                kpis['supervision'],
                kpis['adm'],
            ])

    return response


@login_required
def division_overview(request):
    user = request.user
    _require_sgod_access(user)

    period_options = list(Period.objects.order_by("-school_year_start", "-display_order"))
    period_id = request.GET.get("period_id") or (
        period_options[0].id if period_options else None
    )
    period = get_object_or_404(Period, pk=period_id) if period_id else _latest_period()

    district_id = request.GET.get("district_id")
    section_code = request.GET.get("section_code")

    kpi_context = _build_kpi_context(
        user=user,
        period=period,
        section_code=section_code,
        district_id=district_id,
        include_all_sections=True,
    )

    summary_cards = _build_summary_cards(kpi_context["summary_metrics"])

    return render(
        request,
        "dashboards/division_overview.html",
        {
            "periods": period_options,
            "selected_period": period,
            "districts": kpi_context["districts"],
            "selected_district_id": kpi_context["selected_district_id"],
            "sections": kpi_context["sections"],
            "selected_section_code": kpi_context["selected_section_code"],
            "kpi_rows": kpi_context["kpi_rows"],
            "summary_metrics": kpi_context["summary_metrics"],
            "summary_cards": summary_cards,
        },
    )


def _build_kpi_context(
    *,
    user,
    period: Period,
    section_code: str | None,
    district_id: str | None,
    include_all_sections: bool = False,
) -> dict:
    sgod_access = account_services.user_is_sgod_admin(user)
    allowed_section_codes = account_services.allowed_section_codes(user)

    section_qs = Section.objects.order_by("name")
    if not include_all_sections and not sgod_access:
        if allowed_section_codes:
            section_qs = section_qs.filter(code__iregex=r'^(' + '|'.join(allowed_section_codes) + ')$')
        else:
            section_qs = section_qs.filter(code="smme")

    sections_list = list(section_qs)
    if not sections_list:
        sections_list = list(Section.objects.filter(code="smme"))

    if section_code and not any(section.code.upper() == section_code.upper() for section in sections_list):
        section_code = None
    if not section_code:
        section_code = sections_list[0].code if sections_list else "smme"

    school_scope = account_scope.scope_schools(user).select_related("district", "profile")
    if district_id:
        school_scope = school_scope.filter(district_id=district_id)
        selected_district_id = int(district_id)
    else:
        selected_district_id = None

    schools = list(school_scope)
    school_ids = [school.id for school in schools]

    districts_map: dict[int | None, dict[str, object]] = {}
    for school in schools:
        entry = districts_map.setdefault(
            school.district_id,
            {
                "district": school.district,
                "schools": [],
                "submitted_schools": set(),
                "total_dnme": 0,
                "total_enrolment": 0,
                "adm_burn_rate_sum": 0.0,
                "adm_records": 0,
                "philiri_band10": 0,
                "profile_entries": [],
                "missing_profile": set(),
                "missing_head_name": set(),
                "missing_head_contact": set(),
                "grade_span_mismatches": set(),
            },
        )
        entry["schools"].append(school)
        profile = getattr(school, "profile", None)
        head_name = getattr(profile, "head_name", "") if profile else ""
        head_contact = getattr(profile, "head_contact", "") if profile else ""
        strands = ", ".join(profile.strands) if getattr(profile, "strands", None) else ""
        missing_profile = profile is None
        missing_head_name = not bool(head_name.strip())
        missing_head_contact = not bool(head_contact.strip())
        if missing_profile:
            entry["missing_profile"].add(school.id)
        if missing_head_name:
            entry["missing_head_name"].add(school.id)
        if missing_head_contact:
            entry["missing_head_contact"].add(school.id)
        entry["profile_entries"].append(
            {
                "school": school,
                "head_name": head_name,
                "head_contact": head_contact,
                "grade_span": school.grade_span_label,
                "strands": strands,
                "missing_profile": missing_profile,
                "missing_head_name": missing_head_name,
                "missing_head_contact": missing_head_contact,
            }
        )

    submissions = []
    if school_ids and period:
        submissions = list(
            Submission.objects.filter(
                school_id__in=school_ids,
                form_template__section__code__iexact=section_code,
                period=period,
            )
            .select_related("school__district")
            .prefetch_related(
                "form1_slp_rows",
                "form1_philiri",
                "form1_adm_rows",
            )
        )

    for submission in submissions:
        district_value = submission.school.district_id
        stats = districts_map.get(district_value)
        if not stats or submission.status not in _COMPLETED_STATUSES:
            continue
        slp_rows = submission.form1_slp_rows.all()
        profile = getattr(submission.school, "profile", None)
        start = getattr(profile, "grade_span_start", None)
        end = getattr(profile, "grade_span_end", None)
        if start is None:
            start = submission.school.min_grade
        if end is None:
            end = submission.school.max_grade
        if start is not None and end is not None:
            mismatch_detected = False
            for row in slp_rows:
                grade_number = _extract_grade_number(row.grade_label)
                if grade_number is not None and not (start <= grade_number <= end):
                    mismatch_detected = True
                    break
            if not mismatch_detected:
                rma_rows = submission.form1_rma_rows.all()
                for row in rma_rows:
                    grade_number = _extract_grade_number(getattr(row, "grade_label", ""))
                    if grade_number is not None and not (start <= grade_number <= end):
                        mismatch_detected = True
                        break
            if mismatch_detected:
                stats["grade_span_mismatches"].add(submission.school_id)
        stats["submitted_schools"].add(submission.school_id)
        stats["total_dnme"] += sum(row.dnme for row in slp_rows)
        stats["total_enrolment"] += sum(row.enrolment for row in slp_rows)
        stats["philiri_band10"] += sum(row.band_10 for row in submission.form1_philiri.all())
        for adm_row in submission.form1_adm_rows.all():
            if adm_row.funds_percent_burn_rate is not None:
                stats["adm_burn_rate_sum"] += float(adm_row.funds_percent_burn_rate)
            stats["adm_records"] += 1

    kpi_rows = []
    for stats in districts_map.values():
        total_schools = len(stats["schools"])
        submitted_count = len(stats["submitted_schools"])
        missing_count = total_schools - submitted_count
        completion_rate = round((submitted_count / total_schools) * 100, 2) if total_schools else 0.0
        dnme_percent = round((stats["total_dnme"] / stats["total_enrolment"]) * 100, 2) if stats["total_enrolment"] else 0.0
        average_burn_rate = round(stats["adm_burn_rate_sum"] / stats["adm_records"], 2) if stats["adm_records"] else 0.0
        profile_entries = []
        for entry in sorted(
            stats["profile_entries"],
            key=lambda e: (e["school"].name if e["school"] else ""),
        ):
            school = entry["school"]
            profile_entry = {
                "school": school,
                "head_name": entry["head_name"],
                "head_contact": entry["head_contact"],
                "grade_span": entry["grade_span"],
                "strands": entry["strands"],
                "missing_profile": entry["missing_profile"],
                "missing_head_name": entry["missing_head_name"],
                "missing_head_contact": entry["missing_head_contact"],
                "grade_span_warning": bool(
                    school and school.id in stats["grade_span_mismatches"]
                ),
            }
            profile_entries.append(profile_entry)
        kpi_rows.append(
            {
                "district": stats["district"],
                "total_schools": total_schools,
                "submitted_count": submitted_count,
                "missing_count": missing_count,
                "completion_rate": completion_rate,
                "dnme_percent": dnme_percent,
                "total_dnme": stats["total_dnme"],
                "total_enrolment": stats["total_enrolment"],
                "average_burn_rate": average_burn_rate,
                "philiri_band10_total": stats["philiri_band10"],
                "adm_burn_rate_sum": stats["adm_burn_rate_sum"],
                "adm_records": stats["adm_records"],
                "school_profiles": profile_entries,
            }
        )

    kpi_rows.sort(key=lambda row: (row["district"].name if row["district"] else ""))

    scoped_district_ids = {
        school.district_id for school in schools if school.district_id is not None
    }
    available_districts = list(
        District.objects.filter(pk__in=scoped_district_ids).order_by("name")
    )

    total_summary = {}
    if kpi_rows:
        total_schools = sum(row["total_schools"] for row in kpi_rows)
        total_submitted = sum(row["submitted_count"] for row in kpi_rows)
        total_dnme = sum(row["total_dnme"] for row in kpi_rows)
        total_enrolment = sum(row["total_enrolment"] for row in kpi_rows)
        total_band10 = sum(row["philiri_band10_total"] for row in kpi_rows)
        total_adm_records = sum(row["adm_records"] for row in kpi_rows)
        total_burn_sum = sum(row["adm_burn_rate_sum"] for row in kpi_rows)

        total_summary = {
            "total_schools": total_schools,
            "submitted_count": total_submitted,
            "completion_rate": round((total_submitted / total_schools) * 100, 2) if total_schools else 0.0,
            "dnme_percent": round((total_dnme / total_enrolment) * 100, 2) if total_enrolment else 0.0,
            "average_burn_rate": round(total_burn_sum / total_adm_records, 2) if total_adm_records else 0.0,
            "philiri_band10_total": total_band10,
        }

    return {
        "sections": sections_list,
        "selected_section_code": section_code,
        "districts": available_districts,
        "selected_district_id": selected_district_id,
        "kpi_rows": kpi_rows,
        "summary_metrics": total_summary,
    }


def _build_summary_cards(summary_metrics: dict[str, object]) -> list[dict[str, object]]:
    if not summary_metrics:
        return []
    return [
        {
            "label": "Total schools",
            "value": summary_metrics.get("total_schools", 0),
            "hint": "Across selected filters",
        },
        {
            "label": "Submitted",
            "value": summary_metrics.get("submitted_count", 0),
            "hint": f"Completion rate {summary_metrics.get('completion_rate', 0)}%",
            "tone": "success",
        },
        {
            "label": "DNME %",
            "value": summary_metrics.get("dnme_percent", 0),
            "hint": "Learners who did not meet expectations",
        },
        {
            "label": "Avg ADM burn rate %",
            "value": summary_metrics.get("average_burn_rate", 0),
            "hint": "Weighted by ADM records",
        },
        {
            "label": "PHILIRI band 10 total",
            "value": summary_metrics.get("philiri_band10_total", 0),
            "hint": "Highest proficiency learners",
        },
    ]


# ===== REST API ENDPOINTS =====

from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
import json

@login_required
@require_http_methods(["GET"])
@cache_page(60 * 5)  # Cache for 5 minutes
def api_kpi_schools(request):
    """
    REST API endpoint for school KPI data with pagination and filtering
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - school_year: School year filter
    - quarter: Quarter filter (all, Q1, Q2, Q3, Q4)
    - district: District ID filter
    - school_level: School level filter (all, elementary, secondary)
    - performance_threshold: Performance filter (all, high, medium, low)
    - sort_by: Sort field (school_name, district, performance)
    """
    user = request.user
    try:
        _require_reviewer_access(user)
    except PermissionDenied:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    from organizations.models import Section, School, District
    from submissions.models import Period, Form1SLPRow
    from dashboards.kpi_calculators import calculate_school_kpis_simple
    
    # Get pagination parameters
    page = int(request.GET.get('page', 1))
    page_size = min(int(request.GET.get('page_size', 20)), 100)
    
    # Get filter parameters
    school_year = request.GET.get('school_year')
    quarter = request.GET.get('quarter', 'all')
    district_id = request.GET.get('district')
    school_level = request.GET.get('school_level', 'all')
    performance_threshold = request.GET.get('performance_threshold', 'all')
    sort_by = request.GET.get('sort_by', 'school_name')
    
    # Get periods (reuse logic from dashboard view)
    school_years = Period.objects.values_list('school_year_start', flat=True).distinct().order_by('-school_year_start')
    if not school_year and school_years:
        school_year = str(school_years[0])
    
    if quarter == 'all' and school_year:
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
        ).order_by('display_order')
    elif quarter != 'all' and school_year:
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__iexact=quarter
        ).order_by('display_order')
    else:
        periods = Period.objects.none()
    
    # Get schools with filters
    schools_qs = School.objects.select_related('district', 'profile').order_by('name')
    
    if district_id and district_id != 'all':
        schools_qs = schools_qs.filter(district_id=district_id)
    
    if school_level and school_level != 'all':
        if school_level == 'elementary':
            schools_qs = schools_qs.filter(profile__grade_span_end__lte=6)
        elif school_level == 'secondary':
            schools_qs = schools_qs.filter(profile__grade_span_start__gte=7)
    
    # Build KPI data
    kpi_data = []
    for school in schools_qs:
        school_kpis = calculate_school_kpis_simple(school, periods, 'smme')
        
        # Helper function to get performance class
        def get_performance_class(percentage):
            if percentage < 50:
                return 'low'
            elif percentage < 75:
                return 'medium'
            else:
                return 'high'
        
        school_level_label = 'mixed'
        if school.profile:
            if school.profile.grade_span_end and school.profile.grade_span_end <= 6:
                school_level_label = 'elementary'
            elif school.profile.grade_span_start and school.profile.grade_span_start >= 7:
                school_level_label = 'secondary'
        
        school_data = {
            'id': school.id,
            'name': school.name,
            'district': school.district.name if school.district else None,
            'district_id': school.district.id if school.district else None,
            'school_level': school_level_label,
            'kpis': {
                'implementation': {
                    'value': school_kpis['implementation'],
                    'performance_class': get_performance_class(school_kpis['implementation'])
                },
                'slp': {
                    'value': school_kpis['slp'],
                    'performance_class': get_performance_class(school_kpis['slp'])
                },
                'reading_crla': {
                    'value': school_kpis['reading_crla'],
                    'performance_class': get_performance_class(school_kpis['reading_crla'])
                },
                'reading_philiri': {
                    'value': school_kpis['reading_philiri'],
                    'performance_class': get_performance_class(school_kpis['reading_philiri'])
                },
                'rma': {
                    'value': school_kpis['rma'],
                    'performance_class': get_performance_class(school_kpis['rma'])
                },
                'supervision': {
                    'value': school_kpis['supervision'],
                    'performance_class': get_performance_class(school_kpis['supervision'])
                },
                'adm': {
                    'value': school_kpis['adm'],
                    'performance_class': get_performance_class(school_kpis['adm'])
                }
            },
            'has_data': school_kpis['has_data']
        }
        
        kpi_data.append(school_data)
    
    # Apply performance threshold filter
    if performance_threshold and performance_threshold != 'all':
        if performance_threshold == 'high':
            kpi_data = [row for row in kpi_data if row['kpis']['slp']['value'] >= 75]
        elif performance_threshold == 'medium':
            kpi_data = [row for row in kpi_data if 50 <= row['kpis']['slp']['value'] < 75]
        elif performance_threshold == 'low':
            kpi_data = [row for row in kpi_data if row['kpis']['slp']['value'] < 50]
    
    # Apply sorting
    if sort_by == 'school_name':
        kpi_data.sort(key=lambda x: x['name'])
    elif sort_by == 'district':
        kpi_data.sort(key=lambda x: x['district'] or '')
    elif sort_by == 'performance':
        kpi_data.sort(key=lambda x: x['kpis']['slp']['value'], reverse=True)
    
    # Paginate results
    paginator = Paginator(kpi_data, page_size)
    page_obj = paginator.get_page(page)
    
    response_data = {
        'data': list(page_obj),
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        },
        'filters': {
            'school_year': school_year,
            'quarter': quarter,
            'district': district_id,
            'school_level': school_level,
            'performance_threshold': performance_threshold,
            'sort_by': sort_by
        },
        'meta': {
            'available_school_years': list(school_years),
            'available_quarters': ['all', 'Q1', 'Q2', 'Q3', 'Q4'],
            'available_school_levels': ['all', 'elementary', 'secondary'],
            'available_performance_thresholds': ['all', 'high', 'medium', 'low'],
            'sort_options': ['school_name', 'district', 'performance']
        }
    }
    
    return JsonResponse(response_data)


@login_required
@require_http_methods(["GET"])
@cache_page(60 * 5)
def api_kpi_school_detail(request, school_id):
    """
    REST API endpoint for detailed school KPI data including historical trends
    """
    user = request.user
    try:
        _require_reviewer_access(user)
    except PermissionDenied:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    from organizations.models import School
    from submissions.models import Period
    from dashboards.kpi_calculators import calculate_school_kpis_simple
    
    try:
        school = School.objects.select_related('district', 'profile').get(id=school_id)
    except School.DoesNotExist:
        return JsonResponse({'error': 'School not found'}, status=404)
    
    # Get all periods for historical data
    periods_by_year = {}
    all_periods = Period.objects.filter(is_active=True).order_by('-school_year_start', 'display_order')
    
    for period in all_periods:
        year = period.school_year_start
        if year not in periods_by_year:
            periods_by_year[year] = []
        periods_by_year[year].append(period)
    
    # Calculate KPIs for each year
    historical_data = []
    for year, periods in periods_by_year.items():
        year_kpis = calculate_school_kpis_simple(school, periods, 'smme')
        historical_data.append({
            'school_year': year,
            'school_year_label': f"SY {year}-{year+1}",
            'kpis': year_kpis
        })
    
    # Get current year detailed SLP data
    current_year = max(periods_by_year.keys()) if periods_by_year else None
    slp_subjects = []
    
    if current_year:
        current_periods = periods_by_year[current_year]
        slp_rows = Form1SLPRow.objects.filter(
            submission__school=school,
            submission__period__in=current_periods,
            submission__status__in=['submitted', 'noted']
        ).select_related('submission__period')
        
        # Group by subject
        subjects_data = {}
        for row in slp_rows:
            subject = row.subject or 'Unknown Subject'
            if subject not in subjects_data:
                subjects_data[subject] = {
                    'subject': subject,
                    'total_enrolment': 0,
                    'total_s': 0,
                    'total_vs': 0,
                    'total_o': 0,
                    'total_dnme': 0,
                    'grade_levels': set(),
                }
            
            data = subjects_data[subject]
            data['total_enrolment'] += row.enrolment or 0
            data['total_s'] += row.s or 0
            data['total_vs'] += row.vs or 0
            data['total_o'] += row.o or 0
            data['total_dnme'] += row.dnme or 0
            data['grade_levels'].add(row.grade_label or 'Unknown')
        
        # Calculate proficiency for each subject
        for subject, data in subjects_data.items():
            proficient = data['total_s'] + data['total_vs'] + data['total_o']
            proficiency_rate = (proficient / data['total_enrolment'] * 100) if data['total_enrolment'] > 0 else 0
            
            slp_subjects.append({
                'subject': subject,
                'enrolment': data['total_enrolment'],
                'proficient_count': proficient,
                'proficiency_rate': round(proficiency_rate, 1),
                'dnme_count': data['total_dnme'],
                'dnme_rate': round((data['total_dnme'] / data['total_enrolment'] * 100) if data['total_enrolment'] > 0 else 0, 1),
                'grade_levels': sorted(list(data['grade_levels']))
            })
    
    # School metadata
    school_level = 'mixed'
    if school.profile:
        if school.profile.grade_span_end and school.profile.grade_span_end <= 6:
            school_level = 'elementary'
        elif school.profile.grade_span_start and school.profile.grade_span_start >= 7:
            school_level = 'secondary'
    
    response_data = {
        'school': {
            'id': school.id,
            'name': school.name,
            'district': school.district.name if school.district else None,
            'district_id': school.district.id if school.district else None,
            'school_level': school_level,
            'grade_span': {
                'start': school.profile.grade_span_start if school.profile else None,
                'end': school.profile.grade_span_end if school.profile else None
            }
        },
        'historical_kpis': historical_data,
        'current_slp_subjects': slp_subjects,
        'meta': {
            'data_years': list(periods_by_year.keys()),
            'last_updated': max([p.id for periods in periods_by_year.values() for p in periods]) if periods_by_year else None
        }
    }
    
    return JsonResponse(response_data)


@login_required
@require_http_methods(["GET"])
@cache_page(60 * 5)
def api_slp_subjects(request):
    """
    REST API endpoint for SLP subject-level data across all schools
    """
    user = request.user
    try:
        _require_reviewer_access(user)
    except PermissionDenied:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    from submissions.models import Form1SLPRow, Period
    from submissions.constants import SLP_SUBJECT_LABELS
    
    # Get filters
    school_year = request.GET.get('school_year')
    quarter = request.GET.get('quarter', 'all')
    subject_filter = request.GET.get('subject', 'all')
    grade_range = request.GET.get('grade_range', 'all')
    page = int(request.GET.get('page', 1))
    page_size = min(int(request.GET.get('page_size', 20)), 100)
    
    # Get periods
    school_years = Period.objects.values_list('school_year_start', flat=True).distinct().order_by('-school_year_start')
    if not school_year and school_years:
        school_year = str(school_years[0])
    
    if quarter == 'all' and school_year:
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
        )
    elif quarter != 'all' and school_year:
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__iexact=quarter
        )
    else:
        periods = Period.objects.none()
    
    # Get SLP data with filters
    slp_rows = Form1SLPRow.objects.filter(
        submission__period__in=periods,
        submission__status__in=['submitted', 'noted']
    ).select_related('submission__school', 'submission__period')
    
    if subject_filter and subject_filter != 'all':
        slp_rows = slp_rows.filter(subject=subject_filter)
    
    if grade_range and grade_range != 'all':
        if grade_range == 'k-3':
            slp_rows = slp_rows.filter(grade_label__in=['Kinder', 'Grade 1', 'Grade 2', 'Grade 3'])
        elif grade_range == '4-6':
            slp_rows = slp_rows.filter(grade_label__in=['Grade 4', 'Grade 5', 'Grade 6'])
        elif grade_range == '7-9':
            slp_rows = slp_rows.filter(grade_label__in=['Grade 7', 'Grade 8', 'Grade 9'])
        elif grade_range == '10-12':
            slp_rows = slp_rows.filter(grade_label__in=['Grade 10', 'Grade 11', 'Grade 12'])
    
    # Group and aggregate data
    subject_data = []
    for row in slp_rows:
        proficient = (row.s or 0) + (row.vs or 0) + (row.o or 0)
        proficiency_rate = (proficient / row.enrolment * 100) if row.enrolment > 0 else 0
        
        subject_data.append({
            'id': row.id,
            'school_id': row.submission.school.id,
            'school_name': row.submission.school.name,
            'subject': row.subject,
            'subject_display': SLP_SUBJECT_LABELS.get(row.subject, row.subject),
            'grade_label': row.grade_label,
            'enrolment': row.enrolment,
            'proficient_count': proficient,
            'proficiency_rate': round(proficiency_rate, 1),
            'dnme_count': row.dnme or 0,
            'dnme_rate': round((row.dnme / row.enrolment * 100) if row.enrolment > 0 else 0, 1),
            'performance_breakdown': {
                'dnme': row.dnme or 0,
                'fs': row.fs or 0,
                's': row.s or 0,
                'vs': row.vs or 0,
                'o': row.o or 0
            },
            'has_intervention': bool(row.intervention_plan and row.intervention_plan.strip()),
            'period': {
                'id': row.submission.period.id,
                'label': row.submission.period.label,
                'quarter': row.submission.period.quarter_tag
            }
        })
    
    # Paginate
    paginator = Paginator(subject_data, page_size)
    page_obj = paginator.get_page(page)
    
    # Get available subjects for filter metadata
    available_subjects = Form1SLPRow.objects.filter(
        submission__period__in=periods,
        submission__status__in=['submitted', 'noted']
    ).values_list('subject', flat=True).distinct()
    available_subjects = [(s, SLP_SUBJECT_LABELS.get(s, s)) for s in available_subjects if s]
    
    response_data = {
        'data': list(page_obj),
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        },
        'filters': {
            'school_year': school_year,
            'quarter': quarter,
            'subject': subject_filter,
            'grade_range': grade_range
        },
        'meta': {
            'available_subjects': available_subjects,
            'available_quarters': ['all', 'Q1', 'Q2', 'Q3', 'Q4'],
            'grade_range_options': [
                ('all', 'All Grades'),
                ('k-3', 'Kindergarten - Grade 3'),
                ('4-6', 'Grade 4 - 6'),
                ('7-9', 'Grade 7 - 9'),
                ('10-12', 'Grade 10 - 12'),
            ]
        }
    }
    
    return JsonResponse(response_data)


@login_required
@require_http_methods(["GET"])
@cache_page(60 * 10)  # Cache for 10 minutes
def api_kpi_analytics(request):
    """
    REST API endpoint for KPI analytics and aggregated statistics
    """
    user = request.user
    try:
        _require_reviewer_access(user)
    except PermissionDenied:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    from organizations.models import School, District
    from submissions.models import Period
    from dashboards.kpi_calculators import calculate_school_kpis_simple
    
    # Get filters
    school_year = request.GET.get('school_year')
    quarter = request.GET.get('quarter', 'all')
    
    # Get periods
    school_years = Period.objects.values_list('school_year_start', flat=True).distinct().order_by('-school_year_start')
    if not school_year and school_years:
        school_year = str(school_years[0])
    
    if quarter == 'all' and school_year:
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
        ).order_by('display_order')
    elif quarter != 'all' and school_year:
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__iexact=quarter
        ).order_by('display_order')
    else:
        periods = Period.objects.none()
    
    # Calculate KPIs for all schools
    all_schools = School.objects.select_related('district', 'profile').all()
    analytics_data = {
        'overall_stats': {
            'total_schools': all_schools.count(),
            'schools_with_data': 0,
            'avg_kpis': {
                'implementation': 0,
                'slp': 0,
                'reading_crla': 0,
                'reading_philiri': 0,
                'rma': 0,
                'supervision': 0,
                'adm': 0
            }
        },
        'performance_distribution': {
            'high': {'count': 0, 'percentage': 0},
            'medium': {'count': 0, 'percentage': 0},
            'low': {'count': 0, 'percentage': 0}
        },
        'district_breakdown': [],
        'school_level_breakdown': {
            'elementary': {'count': 0, 'avg_slp': 0},
            'secondary': {'count': 0, 'avg_slp': 0},
            'mixed': {'count': 0, 'avg_slp': 0}
        }
    }
    
    kpi_totals = {
        'implementation': 0,
        'slp': 0,
        'reading_crla': 0,
        'reading_philiri': 0,
        'rma': 0,
        'supervision': 0,
        'adm': 0
    }
    
    schools_with_data = 0
    district_stats = {}
    school_level_stats = {'elementary': [], 'secondary': [], 'mixed': []}
    
    for school in all_schools:
        school_kpis = calculate_school_kpis_simple(school, periods, 'smme')
        
        if school_kpis['has_data']:
            schools_with_data += 1
            
            # Accumulate KPI totals
            for kpi_name in kpi_totals.keys():
                kpi_totals[kpi_name] += school_kpis[kpi_name]
            
            # Performance distribution
            slp_performance = school_kpis['slp']
            if slp_performance >= 75:
                analytics_data['performance_distribution']['high']['count'] += 1
            elif slp_performance >= 50:
                analytics_data['performance_distribution']['medium']['count'] += 1
            else:
                analytics_data['performance_distribution']['low']['count'] += 1
            
            # District breakdown
            district_name = school.district.name if school.district else 'No District'
            if district_name not in district_stats:
                district_stats[district_name] = {
                    'school_count': 0,
                    'total_slp': 0,
                    'schools': []
                }
            district_stats[district_name]['school_count'] += 1
            district_stats[district_name]['total_slp'] += slp_performance
            district_stats[district_name]['schools'].append({
                'id': school.id,
                'name': school.name,
                'slp': slp_performance
            })
            
            # School level breakdown
            school_level = 'mixed'
            if school.profile:
                if school.profile.grade_span_end and school.profile.grade_span_end <= 6:
                    school_level = 'elementary'
                elif school.profile.grade_span_start and school.profile.grade_span_start >= 7:
                    school_level = 'secondary'
            
            school_level_stats[school_level].append(slp_performance)
    
    # Calculate averages and percentages
    analytics_data['overall_stats']['schools_with_data'] = schools_with_data
    
    if schools_with_data > 0:
        for kpi_name in kpi_totals.keys():
            analytics_data['overall_stats']['avg_kpis'][kpi_name] = round(kpi_totals[kpi_name] / schools_with_data, 1)
        
        # Performance distribution percentages
        total_schools = schools_with_data
        analytics_data['performance_distribution']['high']['percentage'] = round(
            (analytics_data['performance_distribution']['high']['count'] / total_schools) * 100, 1
        )
        analytics_data['performance_distribution']['medium']['percentage'] = round(
            (analytics_data['performance_distribution']['medium']['count'] / total_schools) * 100, 1
        )
        analytics_data['performance_distribution']['low']['percentage'] = round(
            (analytics_data['performance_distribution']['low']['count'] / total_schools) * 100, 1
        )
    
    # District breakdown
    for district_name, stats in district_stats.items():
        avg_slp = stats['total_slp'] / stats['school_count'] if stats['school_count'] > 0 else 0
        analytics_data['district_breakdown'].append({
            'district': district_name,
            'school_count': stats['school_count'],
            'avg_slp': round(avg_slp, 1),
            'schools': sorted(stats['schools'], key=lambda x: x['slp'], reverse=True)[:5]  # Top 5 schools
        })
    
    # School level breakdown
    for level, performances in school_level_stats.items():
        count = len(performances)
        avg_slp = sum(performances) / count if count > 0 else 0
        analytics_data['school_level_breakdown'][level] = {
            'count': count,
            'avg_slp': round(avg_slp, 1)
        }
    
    # Sort district breakdown by average SLP performance
    analytics_data['district_breakdown'].sort(key=lambda x: x['avg_slp'], reverse=True)
    
    return JsonResponse(analytics_data)


@login_required
@require_http_methods(["GET"])
def api_kpi_filters(request):
    """
    REST API endpoint to get available filter options
    """
    user = request.user
    try:
        _require_reviewer_access(user)
    except PermissionDenied:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    from organizations.models import District
    from submissions.models import Period, Form1SLPRow
    from submissions.constants import SLP_SUBJECT_LABELS
    
    # Get available school years
    school_years = Period.objects.values_list(
        'school_year_start', flat=True
    ).distinct().order_by('-school_year_start')
    
    # Get districts
    districts = District.objects.all().order_by('name').values('id', 'name')
    
    # Get available subjects
    available_subjects = Form1SLPRow.objects.values_list(
        'subject', flat=True
    ).distinct().order_by('subject')
    subjects = [(s, SLP_SUBJECT_LABELS.get(s, s)) for s in available_subjects if s]
    
    filter_options = {
        'school_years': [
            {
                'value': year,
                'label': f'SY {year}-{year+1}'
            } for year in school_years
        ],
        'quarters': [
            {'value': 'all', 'label': 'All Quarters'},
            {'value': 'Q1', 'label': 'Quarter 1'},
            {'value': 'Q2', 'label': 'Quarter 2'},
            {'value': 'Q3', 'label': 'Quarter 3'},
            {'value': 'Q4', 'label': 'Quarter 4'},
        ],
        'districts': [
            {'value': 'all', 'label': 'All Districts'}
        ] + [
            {'value': district['id'], 'label': district['name']}
            for district in districts
        ],
        'school_levels': [
            {'value': 'all', 'label': 'All Levels'},
            {'value': 'elementary', 'label': 'Elementary (K-6)'},
            {'value': 'secondary', 'label': 'Secondary (7-12)'},
        ],
        'subjects': [
            {'value': 'all', 'label': 'All Subjects'}
        ] + [
            {'value': code, 'label': label}
            for code, label in subjects
        ],
        'grade_ranges': [
            {'value': 'all', 'label': 'All Grades'},
            {'value': 'k-3', 'label': 'Kindergarten - Grade 3'},
            {'value': '4-6', 'label': 'Grade 4 - 6'},
            {'value': '7-9', 'label': 'Grade 7 - 9'},
            {'value': '10-12', 'label': 'Grade 10 - 12'},
        ],
        'performance_thresholds': [
            {'value': 'all', 'label': 'All Performance Levels'},
            {'value': 'high', 'label': 'High Performance (75%+)'},
            {'value': 'medium', 'label': 'Medium Performance (50-74%)'},
            {'value': 'low', 'label': 'Low Performance (<50%)'},
        ],
        'sort_options': [
            {'value': 'school_name', 'label': 'School Name'},
            {'value': 'district', 'label': 'District'},
            {'value': 'performance', 'label': 'Performance'},
        ]
    }
    
    return JsonResponse(filter_options)


@login_required
def api_documentation(request):
    """API Documentation page"""
    user = request.user
    try:
        _require_reviewer_access(user)
    except PermissionDenied:
        messages.error(request, "You don't have permission to access API documentation")
        return redirect('school_home')
    
    return render(request, 'dashboards/api_docs.html')

