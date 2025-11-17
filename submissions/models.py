from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Count
from django.utils import timezone
from django.utils.text import slugify

from organizations.models import Section, School

from . import constants as smea_constants



class Period(models.Model):
    """Period model - simplified for categorical filtering only (no dates)"""
    
    label = models.CharField(
        max_length=100,
        help_text="e.g., 'Q1', 'Q2', 'Q3', 'Q4'"
    )
    
    school_year_start = models.PositiveIntegerField(
        help_text="e.g., 2025 for SY 2025-2026"
    )
    
    quarter_tag = models.CharField(
        max_length=20,
        help_text="Quarter tag (Q1, Q2, Q3, Q4)"
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order for sorting in charts and dropdowns"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this period is active"
    )

    class Meta:
        ordering = ["school_year_start", "display_order", "id"]
        unique_together = [['school_year_start', 'quarter_tag']]

    def __str__(self) -> str:
        return f"SY {self.school_year_start}-{self.school_year_end} {self.label}"
    
    @property
    def school_year_end(self):
        """Calculate school year end"""
        return self.school_year_start + 1
    
    @property
    def is_open(self):
        """Return active status (no date checking since dates removed)"""
        return self.is_active
    
    def contains(self, date) -> bool:
        """Backward compatibility - always return True since no dates"""
        return self.is_active


class FormTemplateQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def open_on(self, date):
        return self.active().filter(open_at__lte=date, close_at__gte=date)


class FormTemplate(models.Model):
    class PeriodType(models.TextChoices):
        MONTH = "month", "Month"
        QUARTER = "quarter", "Quarter"
        SEMESTER = "semester", "Semester"

    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name="forms")
    code = models.SlugField(max_length=64, unique=True)
    title = models.CharField(max_length=255)
    version = models.CharField(max_length=16, blank=True)
    period_type = models.CharField(max_length=16, choices=PeriodType.choices, default=PeriodType.QUARTER)
    open_at = models.DateField()
    close_at = models.DateField()
    is_active = models.BooleanField(default=True)
    schema_descriptor = models.JSONField(default=dict, blank=True)
    
    # NEW: Period classification fields for KPI filtering
    school_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="School year start (e.g., 2025 for SY 2025-2026)"
    )
    quarter_filter = models.CharField(
        max_length=10,
        blank=True,
        default='',
        help_text="Quarter tag for filtering (Q1, Q2, Q3, Q4)"
    )
    # Optional override for Reading assessment timing (bosy/mosy/eosy)
    reading_timing_override = models.CharField(
        max_length=10,
        blank=True,
        default='',
        choices=[
            ('', 'Auto (derive from quarter)'),
            ('bosy', 'BOSY'),
            ('mosy', 'MOSY'),
            ('eosy', 'EOSY'),
        ],
        help_text="Override automatic quarter→reading period mapping. Leave blank to use: Q1→eosy, Q2/Q3→bosy, Q4→mosy."
    )

    objects = FormTemplateQuerySet.as_manager()

    class Meta:
        ordering = ["section__code", "code"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.title} ({self.code})"

    def is_open_today(self) -> bool:
        return self.is_open_on(timezone.localdate())

    def is_open_on(self, target_date) -> bool:
        return self.is_active and self.open_at <= target_date <= self.close_at


class SubmissionQuerySet(models.QuerySet):
    def for_section(self, section: Section):
        return self.filter(form_template__section=section)

    def for_school(self, school: School):
        return self.filter(school=school)

    def with_status(self, *statuses: str):
        return self.filter(status__in=statuses)

    def submitted(self):
        return self.with_status(Submission.Status.SUBMITTED)

    def returned(self):
        return self.with_status(Submission.Status.RETURNED)

    def noted(self):
        return self.with_status(Submission.Status.NOTED)


class Submission(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        RETURNED = "returned", "Returned"
        NOTED = "noted", "Noted"

    school = models.ForeignKey(School, on_delete=models.PROTECT, related_name="submissions")
    form_template = models.ForeignKey(FormTemplate, on_delete=models.PROTECT, related_name="submissions")
    period = models.ForeignKey(Period, on_delete=models.PROTECT, related_name="submissions")

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)

    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submitted_reports",
    )

    returned_at = models.DateTimeField(null=True, blank=True)
    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="returned_reports",
    )
    returned_remarks = models.TextField(blank=True)

    noted_at = models.DateTimeField(null=True, blank=True)
    noted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="noted_reports",
    )
    noted_remarks = models.TextField(blank=True)

    data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="edited_reports",
    )

    objects = SubmissionQuerySet.as_manager()

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=("school", "form_template", "period"),
                name="submission_unique_school_form_period",
            ),
        ]
        indexes = [
            models.Index(fields=("status", "updated_at")),
            models.Index(fields=("form_template", "period")),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.school} - {self.form_template} - {self.period} [{self.status}]"

    # --- lifecycle helpers -------------------------------------------------
    def mark_draft(self, user) -> None:
        self._transition(target_status=self.Status.DRAFT, actor=user, remarks="")

    def validate_ready_for_submission(self) -> None:
        errors: list[str] = []
        project_qs = self.smea_projects.all()
        if not project_qs.exists():
            errors.append("Add at least one project before submitting.")
        else:
            empty_titles = (
                project_qs.annotate(activity_total=Count("activities"))
                .filter(activity_total=0)
                .values_list("project_title", flat=True)
            )
            if empty_titles:
                titles = [title or "Untitled project" for title in empty_titles]
                readable = ", ".join(titles)
                errors.append("Each project must have at least one activity. Missing activities for: " + readable)
        if errors:
            raise ValidationError(errors)


    def mark_submitted(self, user) -> None:
        if not self.can_submit():
            raise ValidationError("Submission cannot be submitted in its current state.")
        self.validate_ready_for_submission()
        self.submitted_at = timezone.now()
        self.submitted_by = user
        self._transition(target_status=self.Status.SUBMITTED, actor=user, remarks="")

    def mark_returned(self, user, remarks: str) -> None:
        if self.status != self.Status.SUBMITTED:
            raise ValidationError("Only submitted reports may be returned.")
        if not remarks:
            raise ValidationError("Remarks are required when returning a submission.")
        self.returned_at = timezone.now()
        self.returned_by = user
        self.returned_remarks = remarks
        self._transition(target_status=self.Status.RETURNED, actor=user, remarks=remarks)

    def mark_noted(self, user, remarks: Optional[str] = None) -> None:
        if self.status != self.Status.SUBMITTED:
            raise ValidationError("Only submitted reports may be marked as noted.")
        self.noted_at = timezone.now()
        self.noted_by = user
        self.noted_remarks = remarks or ""
        self._transition(target_status=self.Status.NOTED, actor=user, remarks=remarks or "")

    def can_submit(self) -> bool:
        return self.status in {self.Status.DRAFT, self.Status.RETURNED}

    def is_editable_by_school(self) -> bool:
        return self.status in {self.Status.DRAFT, self.Status.RETURNED}

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        actor = getattr(self, "last_modified_by", None)
        super().save(*args, **kwargs)
        if is_new:
            SubmissionTimeline.objects.create(
                submission=self,
                actor=actor if actor and getattr(actor, "is_authenticated", False) else None,
                from_status="",
                to_status=self.status,
                remarks="Submission created" if self.status == self.Status.DRAFT else "Status initialized",
            )

    def _transition(self, target_status: str, actor, remarks: str = "") -> None:
        previous_status = self.status
        if previous_status == target_status:
            return
        # Keep remarks from previous cycle when moving out of RETURNED state.
        if target_status != self.Status.RETURNED:
            self.returned_at = None
            self.returned_by = None
        if target_status != self.Status.NOTED:
            self.noted_at = None
            self.noted_by = None
        self.status = target_status
        self.last_modified_by = actor
        self.updated_at = timezone.now()
        self.save()
        SubmissionTimeline.objects.create(
            submission=self,
            actor=actor if actor and getattr(actor, "is_authenticated", False) else None,
            from_status=previous_status,
            to_status=target_status,
            remarks=remarks or "",
        )
        # Notification hook: email school on important transitions
        try:
            profile = getattr(self.school, "profile", None)
            to_email = getattr(profile, "notification_email", None)
            if to_email:
                form_title = getattr(self.form_template, "title", "Form")
                section_name = getattr(getattr(self.form_template, "section", None), "name", "Section")
                period_label = getattr(self.period, "label", "")
                from django.template.loader import render_to_string
                from django.utils.html import strip_tags
                site_url = getattr(settings, 'SITE_URL', '')
                submission_path = f"/submissions/submission/{self.id}/"  # matches submissions.urls pattern name edit_submission
                submission_url = f"{site_url}{submission_path}" if site_url else submission_path
                if target_status == self.Status.RETURNED:
                    subject = f"Returned: {form_title} — {section_name} ({period_label})"
                    ctx = {
                        "title": form_title,
                        "section": section_name,
                        "period": period_label,
                        "remarks": remarks or "No remarks provided.",
                        "status": "returned",
                        "site_url": site_url,
                        "submission_url": submission_url,
                    }
                elif target_status == self.Status.NOTED:
                    subject = f"Noted: {form_title} — {section_name} ({period_label})"
                    ctx = {
                        "title": form_title,
                        "section": section_name,
                        "period": period_label,
                        "remarks": remarks or "No remarks.",
                        "status": "noted",
                        "site_url": site_url,
                        "submission_url": submission_url,
                    }
                elif target_status == self.Status.SUBMITTED:
                    # Optional: notify school confirmation of submission
                    subject = f"Submitted: {form_title} — {section_name} ({period_label})"
                    ctx = {
                        "title": form_title,
                        "section": section_name,
                        "period": period_label,
                        "remarks": "",
                        "status": "submitted",
                        "site_url": site_url,
                        "submission_url": submission_url,
                    }
                else:
                    subject = None
                    ctx = None
                if subject and ctx is not None:
                    template_map = {
                        "returned": "emails/submission_returned.html",
                        "noted": "emails/submission_noted.html",
                        "submitted": "emails/submission_submitted.html",
                    }
                    tpl = template_map.get(ctx["status"]) or "emails/submission_generic.html"
                    html_body = render_to_string(tpl, ctx)
                    text_body = strip_tags(html_body)
                    from notifications.services import queue_email  # type: ignore
                    queue_email(to_email=to_email, subject=subject, body=text_body, html_body=html_body)
        except Exception:
            # Non-blocking: never fail the transition due to notification issues
            pass

    # --- Progress tracking methods -----------------------------------------
    
    def get_section_completion(self) -> dict:
        """
        Calculate completion status for each section.
        Returns dict with section keys and completion data.
        """
        sections = {}
        
        # Projects & Activities
        project_count = self.smea_projects.count()
        activity_count = sum(p.activities.count() for p in self.smea_projects.all())
        sections['projects'] = {
            'complete': project_count > 0 and activity_count > 0,
            'status': 'complete' if (project_count > 0 and activity_count > 0) else 'incomplete',
            'detail': f"{project_count} project{'s' if project_count != 1 else ''}, {activity_count} activit{'ies' if activity_count != 1 else 'y'}",
            'progress': 100 if (project_count > 0 and activity_count > 0) else 0,
        }
        
        # % Implementation (PCT)
        try:
            pct_header = self.form1_pct_header
            pct_rows = pct_header.rows.all()
            filled_rows = sum(1 for row in pct_rows if row.percent is not None or row.action_points)
            total_rows = pct_rows.count()
            pct_progress = int((filled_rows / total_rows * 100)) if total_rows > 0 else 0
            sections['pct'] = {
                'complete': pct_progress == 100,
                'status': 'complete' if pct_progress == 100 else ('in-progress' if pct_progress > 0 else 'not-started'),
                'detail': f"{filled_rows} of {total_rows} areas completed",
                'progress': pct_progress,
            }
        except Exception:
            sections['pct'] = {
                'complete': False,
                'status': 'not-started',
                'detail': 'Not started',
                'progress': 0,
            }
        
        # SLP
        slp_rows = self.form1_slp_rows.all()
        offered_rows = slp_rows.filter(is_offered=True)
        offered_count = offered_rows.count()
        
        if offered_count == 0:
            sections['slp'] = {
                'complete': False,
                'status': 'not-started',
                'detail': 'No subjects marked as offered',
                'progress': 0,
            }
        else:
            # Check if offered subjects have data
            completed_rows = 0
            for row in offered_rows:
                # Consider complete if proficiency data and LLC/intervention are filled
                has_proficiency = any([
                    row.dnme, row.fs, row.s, row.vs, row.o
                ])
                has_llc = bool(row.top_three_llc and row.top_three_llc.strip())
                has_intervention = bool(row.intervention_plan and row.intervention_plan.strip())
                # Count as complete if it has proficiency data AND (LLC or intervention)
                if has_proficiency and (has_llc or has_intervention):
                    completed_rows += 1
            
            slp_progress = int((completed_rows / offered_count * 100)) if offered_count > 0 else 0
            sections['slp'] = {
                'complete': slp_progress == 100,
                'status': 'complete' if slp_progress == 100 else ('in-progress' if slp_progress > 0 else 'not-started'),
                'detail': f"{completed_rows} of {offered_count} offered subjects completed",
                'progress': slp_progress,
            }
        
        # Reading Assessment
        crla_count = self.form1_crla.count()
        philiri_count = self.form1_philiri.count()
        reading_interventions = self.form1_reading_interventions.count()
        
        has_reading_data = crla_count > 0 or philiri_count > 0
        reading_complete = has_reading_data and reading_interventions > 0
        
        if reading_complete:
            reading_status = 'complete'
            reading_detail = f'CRLA: {crla_count}, PHILIRI: {philiri_count}, Interventions: {reading_interventions}'
            reading_progress = 100
        elif has_reading_data:
            reading_status = 'in-progress'
            reading_detail = f'Assessment data entered, {reading_interventions}/5 interventions'
            reading_progress = 60
        else:
            reading_status = 'not-started'
            reading_detail = 'Not started'
            reading_progress = 0
        
        sections['reading'] = {
            'complete': reading_complete,
            'status': reading_status,
            'detail': reading_detail,
            'progress': reading_progress,
        }
        
        # RMA
        rma_rows_count = self.form1_rma_rows.count()
        rma_interventions = self.form1_rma_interventions.count()
        
        has_rma_data = rma_rows_count > 0
        rma_complete = has_rma_data and rma_interventions > 0
        
        if rma_complete:
            rma_status = 'complete'
            rma_detail = f'{rma_rows_count} grade levels, {rma_interventions} interventions'
            rma_progress = 100
        elif has_rma_data:
            rma_status = 'in-progress'
            rma_detail = f'{rma_rows_count} grade levels, {rma_interventions}/5 interventions'
            rma_progress = 60
        else:
            rma_status = 'not-started'
            rma_detail = 'Not started'
            rma_progress = 0
        
        sections['rma'] = {
            'complete': rma_complete,
            'status': rma_status,
            'detail': rma_detail,
            'progress': rma_progress,
        }
        
        # Instructional Supervision
        supervision_rows_count = self.form1_supervision_rows.count()
        
        # Check if any supervision rows have meaningful data
        has_supervision_data = False
        if supervision_rows_count > 0:
            for row in self.form1_supervision_rows.all():
                if (row.teachers_supervised_observed_ta > 0 or 
                    (row.intervention_support_provided and row.intervention_support_provided.strip()) or
                    (row.result and row.result.strip())):
                    has_supervision_data = True
                    break
        
        if has_supervision_data:
            supervision_status = 'complete'
            supervision_detail = f'{supervision_rows_count} supervision records'
            supervision_progress = 100
        elif supervision_rows_count > 0:
            supervision_status = 'in-progress'
            supervision_detail = f'{supervision_rows_count} records (incomplete)'
            supervision_progress = 50
        else:
            supervision_status = 'not-started'
            supervision_detail = 'Not started'
            supervision_progress = 0
        
        sections['supervision'] = {
            'complete': has_supervision_data,
            'status': supervision_status,
            'detail': supervision_detail,
            'progress': supervision_progress,
        }
        
        return sections
    
    def get_overall_progress(self) -> int:
        """
        Calculate overall completion percentage (0-100).
        Averages progress across all sections.
        """
        sections = self.get_section_completion()
        total_progress = sum(section['progress'] for section in sections.values())
        section_count = len(sections)
        return int(total_progress / section_count) if section_count > 0 else 0
    
    def get_completion_summary(self) -> dict:
        """
        Get high-level completion summary for dashboard display.
        """
        sections = self.get_section_completion()
        completed = sum(1 for s in sections.values() if s['complete'])
        in_progress = sum(1 for s in sections.values() if s['status'] == 'in-progress')
        not_started = sum(1 for s in sections.values() if s['status'] == 'not-started')
        
        return {
            'overall_progress': self.get_overall_progress(),
            'completed_sections': completed,
            'in_progress_sections': in_progress,
            'not_started_sections': not_started,
            'total_sections': len(sections),
            'sections': sections,
        }


def _submission_attachment_upload_to(instance: "SubmissionAttachment", filename: str) -> str:
    base_name = slugify(Path(filename).stem) or "file"
    ext = Path(filename).suffix.lower()
    sanitized = f"{base_name}{ext}"
    # UUID prefix keeps filenames unique per submission.
    return f"submissions/{instance.submission.school.code}/{instance.submission_id}/{uuid.uuid4().hex}_{sanitized}"


class SubmissionAttachment(models.Model):
    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".jpg", ".jpeg", ".png"}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to=_submission_attachment_upload_to)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=127, blank=True)
    size = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.original_name

    def clean(self) -> None:
        ext = Path(self.file.name).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValidationError("Unsupported file type for submission attachment.")
        if self.file and self.file.size > self.MAX_FILE_SIZE:
            raise ValidationError("Attachment exceeds the 10 MB size limit.")

    def save(self, *args, **kwargs):  # pragma: no cover - exercised via forms
        if not self.original_name:
            self.original_name = Path(self.file.name).name
        self.size = getattr(self.file, "size", 0)
        if not self.content_type:
            self.content_type = self._detect_content_type()
        self.full_clean()
        super().save(*args, **kwargs)

    def _detect_content_type(self) -> str:
        content_type, _ = mimetypes.guess_type(self.original_name)
        return content_type or "application/octet-stream"





PERCENT_VALIDATORS = (MinValueValidator(0), MaxValueValidator(100))



class SubmissionTimeline(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="timeline")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submission_timeline_entries",
    )
    from_status = models.CharField(max_length=16, choices=Submission.Status.choices, blank=True)
    to_status = models.CharField(max_length=16, choices=Submission.Status.choices)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        actor = self.actor or "System"
        return f"{self.submission_id} {self.from_status}->{self.to_status} by {actor}"

# ---- SMME: SMEA Form 1 (v2) specific tables ----


class SMEAProject(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="smea_projects")
    project_title = models.CharField(max_length=255)
    area_of_concern = models.CharField(max_length=255, blank=True)
    conference_date = models.DateField(null=True, blank=True)  # 'Date:' on the form

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.project_title


class SMEAActivityRow(models.Model):
    project = models.ForeignKey(SMEAProject, on_delete=models.CASCADE, related_name="activities")

    activity = models.TextField()

    # Findings: Target (T) / Actual (A)
    output_target = models.TextField(blank=True)
    output_actual = models.TextField(blank=True)

    timeframe_target = models.TextField(blank=True)  # allow ranges like 'Aug-Oct'
    timeframe_actual = models.TextField(blank=True)

    budget_target = models.CharField(max_length=64, blank=True)  # text for flexibility; change to Decimal if needed
    budget_actual = models.CharField(max_length=64, blank=True)

    interpretation = models.TextField(blank=True)  # 'Interpretation of Findings & Analysis'
    issues_unaddressed = models.TextField(blank=True)
    facilitating_factors = models.TextField(blank=True)
    agreements = models.TextField(blank=True)

    row_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["row_order", "id"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.activity[:60]


class Form1PctHeader(models.Model):
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name="form1_pct")

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Implementation & Action Points for {self.submission_id}"


class Form1PctRow(models.Model):
    header = models.ForeignKey(Form1PctHeader, on_delete=models.CASCADE, related_name="rows")
    area = models.CharField(max_length=32, choices=smea_constants.SMEAActionArea.CHOICES)
    percent = models.PositiveSmallIntegerField(validators=PERCENT_VALIDATORS)
    action_points = models.TextField()

    class Meta:
        unique_together = ("header", "area")
        ordering = ["area"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.get_area_display()} - {self.percent}%"


class Form1SLPRow(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="form1_slp_rows")
    grade_label = models.CharField(max_length=32)
    subject = models.CharField(max_length=64, blank=True, default=smea_constants.SLP_DEFAULT_SUBJECT[0])
    enrolment = models.PositiveIntegerField()
    dnme = models.PositiveIntegerField(default=0)
    fs = models.PositiveIntegerField(default=0)
    s = models.PositiveIntegerField(default=0)
    vs = models.PositiveIntegerField(default=0)
    o = models.PositiveIntegerField(default=0)
    is_offered = models.BooleanField(default=True)
    top_three_llc = models.TextField(blank=True)
    # New: SLP Q2 reasons for non-mastery (comma-separated codes a-f)
    non_mastery_reasons = models.CharField(max_length=255, blank=True, default="")
    # New: SLP Q2 other reasons (required when 'f' is selected)
    non_mastery_other = models.TextField(blank=True, default="")
    intervention_plan = models.TextField(blank=True)

    class Meta:
        ordering = ["grade_label", "subject"]
        unique_together = ("submission", "grade_label", "subject")

    def clean(self):
        super().clean()
        if not self.is_offered:
            self.enrolment = 0
            self.dnme = 0
            self.fs = 0
            self.s = 0
            self.vs = 0
            self.o = 0
            return
        total = sum([self.dnme, self.fs, self.s, self.vs, self.o])
        if total > self.enrolment:
            raise ValidationError("Total learner counts cannot exceed enrolment.")

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"SLP {self.grade_label} - {self.get_subject_display()}"

    def get_subject_display(self) -> str:
        return smea_constants.SLP_SUBJECT_LABELS.get(
            self.subject or smea_constants.SLP_DEFAULT_SUBJECT[0],
            self.subject or smea_constants.SLP_DEFAULT_SUBJECT[1],
        )
    
    def get_proficiency_percentages(self):
        """Calculate percentage distribution of proficiency levels"""
        if not self.enrolment or self.enrolment == 0:
            return {
                'dnme_pct': 0,
                'fs_pct': 0,
                's_pct': 0,
                'vs_pct': 0,
                'o_pct': 0
            }
        
        return {
            'dnme_pct': round((self.dnme / self.enrolment) * 100, 2),
            'fs_pct': round((self.fs / self.enrolment) * 100, 2),
            's_pct': round((self.s / self.enrolment) * 100, 2),
            'vs_pct': round((self.vs / self.enrolment) * 100, 2),
            'o_pct': round((self.o / self.enrolment) * 100, 2)
        }


class Form1SLPAnalysis(models.Model):
    """
    Analysis questions for each learning area (per Form1SLPRow).
    Contains essay-type responses for hindering factors, best practices, and strategies.
    """
    slp_row = models.OneToOneField(
        Form1SLPRow,
        on_delete=models.CASCADE,
        related_name='analysis',
        help_text="The SLP row this analysis belongs to",
        null=True,
        blank=True
    )
    
    # Question 2: Hindering factors
    dnme_factors = models.TextField(
        verbose_name="Hindering factors for DNME learners",
        help_text="What are the root causes why learners did not meet expectations?",
        blank=True,
        default=""
    )
    fs_factors = models.TextField(
        verbose_name="Hindering factors for FS learners",
        help_text="What are the root causes why learners are fairly satisfactory?",
        blank=True,
        default=""
    )
    
    # Question 3: Best practices
    s_practices = models.TextField(
        verbose_name="Best practices for Satisfactory learners",
        help_text="What facilitating factors helped these learners?",
        blank=True,
        default=""
    )
    vs_practices = models.TextField(
        verbose_name="Best practices for Very Satisfactory learners",
        help_text="What facilitating factors helped these learners?",
        blank=True,
        default=""
    )
    o_practices = models.TextField(
        verbose_name="Best practices for Outstanding learners",
        help_text="What facilitating factors helped these learners?",
        blank=True,
        default=""
    )
    
    # Question 6: Overall strategy
    overall_strategy = models.TextField(
        verbose_name="Overall intervention strategy for DNME learners",
        help_text="At your level, what particular strategy or intervention can you implement to address learners under DNME?",
        blank=True,
        default=""
    )
    
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    class Meta:
        verbose_name = "SLP Analysis"
        verbose_name_plural = "SLP Analyses"
        ordering = ['slp_row__grade_label', 'slp_row__subject']
    
    def __str__(self):
        return f"Analysis: {self.slp_row.grade_label} - {self.slp_row.get_subject_display()}"
    
    def is_complete(self):
        """Check if all required fields are filled"""
        if not self.slp_row.is_offered:
            return True  # Non-offered subjects don't need analysis
        
        # Check if at least one field is filled (flexible requirement)
        return bool(
            self.dnme_factors.strip() or
            self.fs_factors.strip() or
            self.s_practices.strip() or
            self.vs_practices.strip() or
            self.o_practices.strip() or
            self.overall_strategy.strip()
        )


class Form1SLPLLCEntry(models.Model):
    submission = models.ForeignKey('Submission', on_delete=models.CASCADE, related_name='slp_llc_entries')
    llc_description = models.TextField(help_text="Description of the Least Learned Competency")
    intervention = models.TextField(help_text="Intervention plan for this LLC")
    order = models.PositiveSmallIntegerField(help_text="Order of LLC (1-3)")
    
    class Meta:
        ordering = ['order']
        unique_together = ('submission', 'order')

    def __str__(self):
        return f"LLC {self.order} for {self.submission}"


class Form1SLPTopDNME(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="form1_slp_top_dnme")
    grade_label = models.CharField(max_length=32)
    count = models.PositiveIntegerField(default=0)
    position = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(5)])

    class Meta:
        unique_together = ("submission", "position")
        ordering = ["position"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Top DNME {self.grade_label}"


class Form1SLPTopOutstanding(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="form1_slp_top_outstanding")
    grade_label = models.CharField(max_length=32)
    count = models.PositiveIntegerField(default=0)
    position = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(5)])

    class Meta:
        unique_together = ("submission", "position")
        ordering = ["position"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Top Outstanding {self.grade_label}"


class Form1ReadingCRLA(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="form1_crla")
    level = models.CharField(max_length=8, choices=smea_constants.CRLALevel.CHOICES)
    timing = models.CharField(max_length=8, choices=smea_constants.CRLATiming.CHOICES)
    subject = models.CharField(max_length=16, choices=smea_constants.CRLASubject.CHOICES)
    band = models.CharField(max_length=16, choices=smea_constants.CRLABand.CHOICES)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("submission", "level", "timing", "subject", "band")
        ordering = ["level", "timing", "subject", "band"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"CRLA {self.get_level_display()} {self.get_band_display()}"


class Form1ReadingPHILIRI(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="form1_philiri")
    level = models.CharField(max_length=8, choices=smea_constants.CRLALevel.CHOICES)
    timing = models.CharField(max_length=8, choices=smea_constants.AssessmentTiming.CHOICES)
    language = models.CharField(max_length=32, choices=smea_constants.PHILIRILanguage.CHOICES)
    band_4_7 = models.PositiveIntegerField(default=0)
    band_5_8 = models.PositiveIntegerField(default=0)
    band_6_9 = models.PositiveIntegerField(default=0)
    band_10 = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("submission", "level", "timing", "language")
        ordering = ["level", "timing", "language"]

    def clean(self):
        super().clean()
        total = self.band_4_7 + self.band_5_8 + self.band_6_9 + self.band_10
        if total == 0:
            raise ValidationError("At least one PHILIRI band count must be provided.")


class Form1ReadingIntervention(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="form1_reading_interventions")
    order = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    description = models.TextField()

    class Meta:
        unique_together = ("submission", "order")
        ordering = ["order"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Reading Intervention {self.order}"


# New CRLA Model - Matrix Based (2025-26)
class ReadingAssessmentCRLA(models.Model):
    """
    CRLA Assessment Results organized by period and proficiency level.
    Each row represents one assessment period × proficiency level combination.
    """
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="crla_assessments")
    period = models.CharField(max_length=10, choices=smea_constants.AssessmentPeriod.CHOICES)
    level = models.CharField(max_length=20, choices=smea_constants.CRLAProficiencyLevel.CHOICES)
    
    # Mother Tongue counts for all three grades
    mt_grade_1 = models.PositiveIntegerField(default=0, verbose_name="Mother Tongue - Grade I")
    mt_grade_2 = models.PositiveIntegerField(default=0, verbose_name="Mother Tongue - Grade II")
    mt_grade_3 = models.PositiveIntegerField(default=0, verbose_name="Mother Tongue - Grade III")
    
    # Filipino counts (Grades II and III only)
    fil_grade_2 = models.PositiveIntegerField(default=0, verbose_name="Filipino - Grade II")
    fil_grade_3 = models.PositiveIntegerField(default=0, verbose_name="Filipino - Grade III")
    
    # English count (Grade III only)
    eng_grade_3 = models.PositiveIntegerField(default=0, verbose_name="English - Grade III")

    class Meta:
        unique_together = ("submission", "period", "level")
        ordering = ["period", "level"]
        verbose_name = "CRLA Assessment"
        verbose_name_plural = "CRLA Assessments"

    def __str__(self) -> str:
        return f"CRLA {self.get_period_display()} - {self.get_level_display()}"
    
    def total_learners(self) -> int:
        """Calculate total learners across all subjects/grades for this level"""
        return (
            self.mt_grade_1 + self.mt_grade_2 + self.mt_grade_3 +
            self.fil_grade_2 + self.fil_grade_3 +
            self.eng_grade_3
        )


# New PHILIRI Model - Matrix Based (2025-26)
class ReadingAssessmentPHILIRI(models.Model):
    """
    PHILIRI Assessment Results organized by period and reading level.
    Each row represents one assessment period × reading level combination.
    Separate fields for each grade level to support integrated schools.
    """
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="philiri_assessments")
    period = models.CharField(max_length=10, choices=smea_constants.AssessmentPeriod.CHOICES)
    level = models.CharField(max_length=20, choices=smea_constants.PHILIRIReadingLevel.CHOICES)
    
    # English counts per individual grade level
    eng_grade_4 = models.PositiveIntegerField(default=0, verbose_name="English - Grade 4")
    eng_grade_5 = models.PositiveIntegerField(default=0, verbose_name="English - Grade 5")
    eng_grade_6 = models.PositiveIntegerField(default=0, verbose_name="English - Grade 6")
    eng_grade_7 = models.PositiveIntegerField(default=0, verbose_name="English - Grade 7")
    eng_grade_8 = models.PositiveIntegerField(default=0, verbose_name="English - Grade 8")
    eng_grade_9 = models.PositiveIntegerField(default=0, verbose_name="English - Grade 9")
    eng_grade_10 = models.PositiveIntegerField(default=0, verbose_name="English - Grade 10")
    
    # Filipino counts per individual grade level
    fil_grade_4 = models.PositiveIntegerField(default=0, verbose_name="Filipino - Grade 4")
    fil_grade_5 = models.PositiveIntegerField(default=0, verbose_name="Filipino - Grade 5")
    fil_grade_6 = models.PositiveIntegerField(default=0, verbose_name="Filipino - Grade 6")
    fil_grade_7 = models.PositiveIntegerField(default=0, verbose_name="Filipino - Grade 7")
    fil_grade_8 = models.PositiveIntegerField(default=0, verbose_name="Filipino - Grade 8")
    fil_grade_9 = models.PositiveIntegerField(default=0, verbose_name="Filipino - Grade 9")
    fil_grade_10 = models.PositiveIntegerField(default=0, verbose_name="Filipino - Grade 10")

    class Meta:
        unique_together = ("submission", "period", "level")
        ordering = ["period", "level"]
        verbose_name = "PHILIRI Assessment"
        verbose_name_plural = "PHILIRI Assessments"

    def __str__(self) -> str:
        return f"PHILIRI {self.get_period_display()} - {self.get_level_display()}"
    
    def total_learners(self) -> int:
        """Calculate total learners across all subjects/grades for this level"""
        return (
            self.eng_grade_4 + self.eng_grade_5 + self.eng_grade_6 + self.eng_grade_7 + 
            self.eng_grade_8 + self.eng_grade_9 + self.eng_grade_10 +
            self.fil_grade_4 + self.fil_grade_5 + self.fil_grade_6 + self.fil_grade_7 + 
            self.fil_grade_8 + self.fil_grade_9 + self.fil_grade_10
        )


# Update Reading Interventions model to use new related name
class ReadingInterventionNew(models.Model):
    """
    Reading interventions developed based on CRLA and PHILIRI assessment results.
    Maximum of 5 interventions per submission.
    """
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="reading_interventions_new")
    order = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    description = models.TextField(verbose_name="Intervention Description")

    class Meta:
        unique_together = ("submission", "order")
        ordering = ["order"]
        verbose_name = "Reading Intervention"
        verbose_name_plural = "Reading Interventions"

    def __str__(self) -> str:
        return f"Intervention {self.order}: {self.description[:50]}"


class ReadingDifficultyPlan(models.Model):
    """Structured per-grade Reading Difficulties with paired interventions (JSON)."""
    PERIOD_CHOICES = [
        ('bosy', 'BOSY'),
        ('mosy', 'MOSY'),
        ('eosy', 'EOSY'),
    ]
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="reading_difficulty_plans")
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    grade_label = models.CharField(max_length=8, choices=smea_constants.RMAGradeLabel.CHOICES)
    # JSON structure: [{"difficulty": str, "intervention": str}, ...]
    data = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("submission", "period", "grade_label")
        ordering = ["period", "grade_label"]
        verbose_name = "Reading Difficulty Plan"
        verbose_name_plural = "Reading Difficulty Plans"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Reading Difficulty Plan {self.period.upper()} {self.grade_label}"


class Form1RMARow(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="form1_rma_rows")
    grade_label = models.CharField(max_length=8, choices=smea_constants.RMAGradeLabel.CHOICES)
    enrolment = models.PositiveIntegerField()
    
    # Corrected proficiency levels based on actual SMEA Form 1 KPIs
    emerging_not_proficient = models.PositiveIntegerField(
        default=0,
        verbose_name="Emerging - Not Proficient",
        help_text="Below 25%"
    )
    emerging_low_proficient = models.PositiveIntegerField(
        default=0,
        verbose_name="Emerging - Low Proficient",
        help_text="25%-49%"
    )
    developing_nearly_proficient = models.PositiveIntegerField(
        default=0,
        verbose_name="Developing - Nearly Proficient",
        help_text="50%-74%"
    )
    transitioning_proficient = models.PositiveIntegerField(
        default=0,
        verbose_name="Transitioning - Proficient",
        help_text="75%-84%"
    )
    at_grade_level = models.PositiveIntegerField(
        default=0,
        verbose_name="At Grade Level",
        help_text="Above 85%"
    )

    class Meta:
        unique_together = ("submission", "grade_label")
        ordering = ["grade_label"]

    def clean(self):
        super().clean()
        total = sum([
            self.emerging_not_proficient,
            self.emerging_low_proficient,
            self.developing_nearly_proficient,
            self.transitioning_proficient,
            self.at_grade_level,
        ])
        if total > self.enrolment:
            raise ValidationError("Proficiency totals cannot exceed enrolment.")
    
    def get_proficiency_percentages(self):
        """Calculate percentage distribution of proficiency levels"""
        if not self.enrolment or self.enrolment == 0:
            return {
                'emerging_not_proficient_pct': 0,
                'emerging_low_proficient_pct': 0,
                'developing_nearly_proficient_pct': 0,
                'transitioning_proficient_pct': 0,
                'at_grade_level_pct': 0
            }
        
        return {
            'emerging_not_proficient_pct': round((self.emerging_not_proficient / self.enrolment) * 100, 2),
            'emerging_low_proficient_pct': round((self.emerging_low_proficient / self.enrolment) * 100, 2),
            'developing_nearly_proficient_pct': round((self.developing_nearly_proficient / self.enrolment) * 100, 2),
            'transitioning_proficient_pct': round((self.transitioning_proficient / self.enrolment) * 100, 2),
            'at_grade_level_pct': round((self.at_grade_level / self.enrolment) * 100, 2)
        }


class Form1RMAIntervention(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="form1_rma_interventions")
    order = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    description = models.TextField()

    class Meta:
        unique_together = ("submission", "order")
        ordering = ["order"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"RMA Intervention {self.order}"



class Form1SupervisionRow(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="form1_supervision_rows")
    grade_label = models.CharField(max_length=32, blank=True)
    total_teachers = models.PositiveIntegerField(default=0, verbose_name="Total number of teachers", help_text="Total number of teachers in the grade/area")
    teachers_supervised_observed_ta = models.PositiveIntegerField(default=0)
    intervention_support_provided = models.TextField(blank=True)
    result = models.TextField(blank=True)

    class Meta:
        ordering = ["grade_label", "id"]


class Form1ADMHeader(models.Model):
    """Header for ADM section to track if school offers ADM"""
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name="form1_adm_header")
    is_offered = models.BooleanField(
        default=True,
        verbose_name="School implements ADM (Alternative Delivery Mode)",
        help_text="Check if your school implements ADM programs"
    )

    def __str__(self) -> str:
        return f"ADM Header for {self.submission_id} - {'Offered' if self.is_offered else 'Not Offered'}"


class Form1ADMRow(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="form1_adm_rows")
    ppas_conducted = models.TextField(blank=True, verbose_name="PPAs Conducted")
    ppas_physical_target = models.PositiveIntegerField(default=0, verbose_name="Physical Target")
    ppas_physical_actual = models.PositiveIntegerField(default=0, verbose_name="Physical Actual")
    ppas_physical_percent = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=PERCENT_VALIDATORS, 
        default=0,
        verbose_name="% of Actual Accomplishment"
    )

    funds_downloaded = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Downloaded")
    funds_obligated = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Obligated")
    funds_unobligated = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Unobligated")
    funds_percent_obligated = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=PERCENT_VALIDATORS, 
        default=0,
        verbose_name="% Obligated"
    )
    funds_percent_burn_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=PERCENT_VALIDATORS, 
        default=0,
        verbose_name="% Age/BUR (Burn Rate)"
    )

    q1_response = models.TextField(blank=True, verbose_name="Q1: Factors that helped facilitate PPAs")
    q2_response = models.TextField(blank=True, verbose_name="Q2: Do PPAs address intended purpose?")
    q3_response = models.TextField(blank=True, verbose_name="Q3: PPAs to sustain/enhance")
    q4_response = models.TextField(blank=True, verbose_name="Q4: PPAs to drop/improve")
    q5_response = models.TextField(blank=True, verbose_name="Q5: Overall significance of ADM implementation")

    class Meta:
        ordering = ["id"]
    
    def clean(self):
        """Validate that if ADM is not offered, all fields should be empty/zero"""
        super().clean()
        try:
            adm_header = self.submission.form1_adm_header
            if not adm_header.is_offered:
                # If ADM is not offered, clear all data
                self.ppas_conducted = ""
                self.ppas_physical_target = 0
                self.ppas_physical_actual = 0
                self.ppas_physical_percent = 0
                self.funds_downloaded = 0
                self.funds_obligated = 0
                self.funds_unobligated = 0
                self.funds_percent_obligated = 0
                self.funds_percent_burn_rate = 0
                self.q1_response = ""
                self.q2_response = ""
                self.q3_response = ""
                self.q4_response = ""
                self.q5_response = ""
        except Form1ADMHeader.DoesNotExist:
            pass  # Header not yet created


class Form1Signatories(models.Model):
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name="form1_signatories")
    prepared_by = models.CharField(max_length=255, blank=True)
    submitted_to = models.CharField(max_length=255, blank=True)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Signatories for {self.submission_id}"










