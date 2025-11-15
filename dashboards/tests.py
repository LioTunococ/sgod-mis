from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from organizations.models import District, School, Section, SchoolProfile
from submissions import constants as smea_constants
from submissions.models import (
    Form1ADMRow,
    Form1RMARow,
    Form1RMAIntervention,
    Form1ReadingCRLA,
    Form1ReadingIntervention,
    Form1ReadingPHILIRI,
    Form1SLPAnalysis,
    Form1SLPRow,
    Form1SLPTopDNME,
    Form1SLPTopOutstanding,
    FormTemplate,
    Period,
    Submission,
    SubmissionTimeline,
    SMEAActivityRow,
    SMEAProject,
)


class DashboardViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.section = Section.objects.create(code="smme", name="School Management" )
        self.period = Period.objects.create(
            label="Q1",
            school_year_start=2025,
            quarter_tag='Q1',
            display_order=1,
            is_active=True,
        )
        self.form = FormTemplate.objects.create(
            section=self.section,
            code="smea-form-1",
            title="SMEA Form 1",
            period_type=FormTemplate.PeriodType.QUARTER,
            open_at=timezone.now().date(),
            close_at=timezone.now().date(),
        )

        self.district_north = District.objects.create(code="north", name="North District")
        self.district_south = District.objects.create(code="south", name="South District")

        self.school_submitted = School.objects.create(
            code="north-submitted",
            name="North Submitted School",
            district=self.district_north,
            implements_adm=True,
        )
        self.school_pending = School.objects.create(
            code="north-pending",
            name="North Pending School",
            district=self.district_north,
            implements_adm=True,
        )
        self.school_other = School.objects.create(
            code="south-school",
            name="South School",
            district=self.district_south,
        )
        SchoolProfile.objects.create(
            school=self.school_submitted,
            head_name="Pat Reyes",
            head_contact="pat@example.com",
            grade_span_start=1,
            grade_span_end=6,
            strands=["STEM"],
        )
        SchoolProfile.objects.create(
            school=self.school_pending,
            head_name="Alex Cruz",
            head_contact="alex@example.com",
            grade_span_start=1,
            grade_span_end=6,
            strands=["ICT"],
        )
        SchoolProfile.objects.create(
            school=self.school_other,
            head_name="Jamie Santos",
            head_contact="jamie@example.com",
            grade_span_start=7,
            grade_span_end=10,
            strands=["ALS"],
        )
        pending_profile = SchoolProfile.objects.get(school=self.school_pending)
        pending_profile.grade_span_end = 3
        pending_profile.head_contact = ""
        pending_profile.save(update_fields=["grade_span_end", "head_contact", "updated_at"])
        other_profile = SchoolProfile.objects.get(school=self.school_other)
        other_profile.head_contact = ""
        other_profile.save(update_fields=["head_contact", "updated_at"])
        self.section_admin = User.objects.create_user(
            username="sectionadmin",
            email="sectionadmin@example.com",
            password="password",
        )
        section_profile = UserProfile.objects.get(user=self.section_admin)
        section_profile.section_admin_codes = [self.section.code]
        section_profile.save(update_fields=["section_admin_codes", "updated_at"])

        self.psds = User.objects.create_user(
            username="psds",
            email="psds@example.com",
            password="password",
        )
        psds_profile = UserProfile.objects.get(user=self.psds)
        psds_profile.districts.add(self.district_north)

        self.sgod_admin = User.objects.create_user(
            username="sgod",
            email="sgod@example.com",
            password="password",
        )
        sgod_profile = UserProfile.objects.get(user=self.sgod_admin)
        sgod_profile.is_sgod_admin = True
        sgod_profile.save(update_fields=["is_sgod_admin", "updated_at"])

        self.school_head = User.objects.create_user(
            username="schoolhead",
            email="head@example.com",
            password="password",
        )
        head_profile = UserProfile.objects.get(user=self.school_head)
        head_profile.school = self.school_submitted
        head_profile.save(update_fields=["school", "updated_at"])

        self.submission = Submission.objects.create(
            school=self.school_submitted,
            form_template=self.form,
            period=self.period,
        )
        project = SMEAProject.objects.create(
            submission=self.submission,
            project_title="Project Alpha",
            area_of_concern="Reading",
        )
        SMEAActivityRow.objects.create(project=project, activity="Baseline")
        self.submission.mark_submitted(self.section_admin)

        Form1SLPRow.objects.create(
            submission=self.submission,
            grade_label="Grade 3",
            enrolment=30,
            dnme=5,
            fs=5,
            s=10,
            vs=5,
            o=5,
            top_three_llc="Reading",
            intervention_plan="Conduct remedial classes",
        )
        Form1SLPAnalysis.objects.create(
            submission=self.submission,
            q1a_summary_text="Summary",
            root_causes="Root Causes",
            best_practices="Practices",
        )
        Form1SLPTopDNME.objects.create(
            submission=self.submission,
            position=1,
            grade_label="Grade 3",
            count=5,
        )
        Form1SLPTopOutstanding.objects.create(
            submission=self.submission,
            position=1,
            grade_label="Grade 6",
            count=3,
        )

        Form1ReadingCRLA.objects.create(
            submission=self.submission,
            level=smea_constants.CRLALevel.GRADE3,
            timing=smea_constants.CRLATiming.BOY,
            subject=smea_constants.CRLASubject.ENGLISH,
            band=smea_constants.CRLABand.INSTRUCTIONAL,
            count=12,
        )
        Form1ReadingPHILIRI.objects.create(
            submission=self.submission,
            level=smea_constants.CRLALevel.GRADE3,
            timing=smea_constants.AssessmentTiming.BOY,
            language=smea_constants.PHILIRILanguage.ENGLISH,
            band_4_7=1,
            band_5_8=1,
            band_6_9=1,
            band_10=1,
        )
        Form1ReadingIntervention.objects.create(
            submission=self.submission,
            order=1,
            description="Reading club",
        )

        Form1RMARow.objects.create(
            submission=self.submission,
            grade_label=smea_constants.RMAGradeLabel.GRADE3,
            enrolment=40,
            band_below_75=5,
            band_75_79=5,
            band_80_84=10,
            band_85_89=10,
            band_90_100=10,
        )
        Form1RMAIntervention.objects.create(
            submission=self.submission,
            order=1,
            description="Focused review",
        )

        Form1ADMRow.objects.create(
            submission=self.submission,
            ppas_conducted="Orientation",
            ppas_physical_target=10,
            ppas_physical_actual=8,
            ppas_physical_percent=80,
            funds_downloaded=1000,
            funds_obligated=800,
            funds_unobligated=200,
            funds_percent_obligated=80,
            funds_percent_burn_rate=60,
            q1_response="Q1",
            q2_response="Q2",
            q3_response="Q3",
            q4_response="Q4",
            q5_response="Q5",
        )

    def _gap_url(self, **params):
        base = reverse("district_submission_gaps")
        if params:
            query = "&".join(f"{key}={value}" for key, value in params.items())
            return f"{base}?{query}"
        return base

    def _kpi_url(self, **params):
        base = reverse("smme_kpi_dashboard")
        if params:
            query = "&".join(f"{key}={value}" for key, value in params.items())
            return f"{base}?{query}"
        return base

    def test_district_submission_gaps_identifies_missing_schools(self):
        self.client.force_login(self.section_admin)
        url = self._gap_url(
            section=self.section.code,
            form_code=self.form.code,
            period_id=self.period.id,
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        rows = response.context["district_rows"]
        north_row = next(row for row in rows if row["district"] == self.district_north)
        self.assertEqual(north_row["submitted_count"], 1)
        self.assertEqual(north_row["missing_count"], 1)
        missing_entry = next(entry for entry in north_row["missing_schools"] if entry["school"].code == self.school_pending.code)
        self.assertTrue(missing_entry["missing_head_contact"])
        self.assertContains(response, "Contact missing")

    def test_district_submission_gaps_psds_scope(self):
        self.client.force_login(self.psds)
        url = self._gap_url(
            section=self.section.code,
            form_code=self.form.code,
            period_id=self.period.id,
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        rows = response.context["district_rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["district"], self.district_north)

    def test_district_submission_gaps_requires_reviewer(self):
        self.client.force_login(self.school_head)
        url = self._gap_url(
            section=self.section.code,
            form_code=self.form.code,
            period_id=self.period.id,
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_smme_kpi_dashboard_reports_metrics(self):
        self.client.force_login(self.section_admin)
        url = self._kpi_url(period_id=self.period.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        rows = response.context["kpi_rows"]
        north_row = next(row for row in rows if row["district"] == self.district_north)
        self.assertEqual(north_row["total_schools"], 2)
        self.assertEqual(north_row["submitted_count"], 1)
        self.assertAlmostEqual(north_row["completion_rate"], 50.0)
        self.assertAlmostEqual(round(north_row["dnme_percent"], 2), round((5 / 30) * 100, 2))
        self.assertEqual(north_row["average_burn_rate"], 60.0)
        self.assertEqual(north_row["philiri_band10_total"], 1)
        summary = response.context["summary_metrics"]
        self.assertEqual(summary["total_schools"], 3)
        self.assertEqual(summary["submitted_count"], 1)
        self.assertAlmostEqual(summary["completion_rate"], round((1 / 3) * 100, 2), places=2)
        self.assertAlmostEqual(summary["dnme_percent"], round((5 / 30) * 100, 2), places=2)
        self.assertEqual(summary["average_burn_rate"], 60.0)
        self.assertEqual(summary["philiri_band10_total"], 1)


    def test_school_home_lists_recent_drafts(self):
        self.client.force_login(self.school_head)
        draft_form = FormTemplate.objects.create(
            section=self.section,
            code="smea-form-draft",
            title="SMEA Form Draft",
            period_type=FormTemplate.PeriodType.QUARTER,
            open_at=timezone.now().date(),
            close_at=timezone.now().date(),
        )
        returned_form = FormTemplate.objects.create(
            section=self.section,
            code="smea-form-returned",
            title="SMEA Form Returned",
            period_type=FormTemplate.PeriodType.QUARTER,
            open_at=timezone.now().date(),
            close_at=timezone.now().date(),
        )
        draft_submission = Submission.objects.create(
            school=self.school_submitted,
            form_template=draft_form,
            period=self.period,
            status=Submission.Status.DRAFT,
        )
        returned_submission = Submission.objects.create(
            school=self.school_submitted,
            form_template=returned_form,
            period=self.period,
            status=Submission.Status.RETURNED,
        )

        response = self.client.get(reverse("school_home"))
        self.assertEqual(response.status_code, 200)
        draft_list = response.context["draft_submissions"]
        draft_ids = {submission.id for submission in draft_list}
        self.assertSetEqual(draft_ids, {draft_submission.id, returned_submission.id})
        self.assertContains(response, "Drafts &amp; Returns")
        self.assertContains(response, draft_form.title)
        self.assertContains(response, returned_form.title)

    def test_section_admin_landing_shows_queue_summary_and_recent_actions(self):
        self.client.force_login(self.section_admin)

        response = self.client.get(reverse("school_home"))
        expected_url = reverse("review_queue", kwargs={"section_code": self.section.code})
        self.assertRedirects(response, expected_url, status_code=302, target_status_code=200)

    def test_school_head_with_section_admin_scope_sees_portal_and_reviewer_panels(self):
        profile = UserProfile.objects.get(user=self.school_head)
        profile.section_admin_codes = [self.section.code]
        profile.save(update_fields=["section_admin_codes", "updated_at"])

        # create pending and returned submissions within the scoped section
        pending_form = FormTemplate.objects.create(
            section=self.section,
            code="smea-form-combined",
            title="SMEA Form Combined",
            period_type=FormTemplate.PeriodType.QUARTER,
            open_at=timezone.now().date(),
            close_at=timezone.now().date(),
        )
        returned_form = FormTemplate.objects.create(
            section=self.section,
            code="smea-form-combined-return",
            title="SMEA Form Combined Return",
            period_type=FormTemplate.PeriodType.QUARTER,
            open_at=timezone.now().date(),
            close_at=timezone.now().date(),
        )
        Submission.objects.create(
            school=self.school_pending,
            form_template=pending_form,
            period=self.period,
            status=Submission.Status.SUBMITTED,
            submitted_at=timezone.now(),
            submitted_by=self.school_head,
        )
        returned_submission = Submission.objects.create(
            school=self.school_pending,
            form_template=returned_form,
            period=self.period,
            status=Submission.Status.RETURNED,
            submitted_at=timezone.now(),
            submitted_by=self.school_head,
            returned_at=timezone.now(),
            returned_by=self.school_head,
        )
        SubmissionTimeline.objects.create(
            submission=returned_submission,
            actor=self.school_head,
            from_status=Submission.Status.SUBMITTED,
            to_status=Submission.Status.RETURNED,
            remarks="Resubmit with corrected data.",
        )

        self.client.force_login(self.school_head)
        response = self.client.get(reverse("school_home"))

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["school_portal"])
        self.assertIsNotNone(response.context["section_admin_summary"])
        self.assertContains(response, "Outstanding Returns")
        self.assertContains(response, "Drafts &amp; Returns")
        self.assertContains(response, "Review Queue Snapshot")
        self.assertContains(response, "Resubmit with corrected data.")

    def test_smme_kpi_requires_reviewer(self):
        self.client.force_login(self.school_head)
        url = self._kpi_url(period_id=self.period.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_smme_kpi_allows_section_selector_for_sgod(self):
        other_section = Section.objects.create(code="hrd", name="Human Resource Development")
        other_form = FormTemplate.objects.create(
            section=other_section,
            code="hrd-form-1",
            title="HRD Form 1",
            period_type=FormTemplate.PeriodType.QUARTER,
            open_at=timezone.now().date(),
            close_at=timezone.now().date(),
        )
        other_submission = Submission.objects.create(
            school=self.school_pending,
            form_template=other_form,
            period=self.period,
            status=Submission.Status.SUBMITTED,
            submitted_at=timezone.now(),
            submitted_by=self.section_admin,
        )
        Form1SLPRow.objects.create(
            submission=other_submission,
            grade_label="Grade 4",
            enrolment=20,
            dnme=2,
            fs=3,
            s=5,
            vs=5,
            o=5,
            top_three_llc="Leadership",
            intervention_plan="Peer mentoring",
        )

        self.client.force_login(self.sgod_admin)
        url = self._kpi_url(period_id=self.period.id, section_code=other_section.code)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_section_code"], other_section.code)
        rows = response.context["kpi_rows"]
        north_row = next(row for row in rows if row["district"] == self.district_north)
        self.assertTrue(any(entry["head_name"] == "Pat Reyes" for entry in north_row["school_profiles"]))
        self.assertContains(response, other_section.name)
        self.assertTrue(any(row["district"] == self.district_north for row in rows))

    def test_division_overview_requires_sgod(self):
        self.client.force_login(self.section_admin)
        response = self.client.get(reverse("division_overview"))
        self.assertEqual(response.status_code, 403)

    def test_division_overview_renders_metrics(self):
        other_section = Section.objects.create(code="hrd2", name="HRD 2")
        other_form = FormTemplate.objects.create(
            section=other_section,
            code="hrd2-form-1",
            title="HRD2 Form 1",
            period_type=FormTemplate.PeriodType.QUARTER,
            open_at=timezone.now().date(),
            close_at=timezone.now().date(),
        )
        new_submission = Submission.objects.create(
            school=self.school_pending,
            form_template=other_form,
            period=self.period,
            status=Submission.Status.SUBMITTED,
            submitted_at=timezone.now(),
            submitted_by=self.section_admin,
        )
        Form1SLPRow.objects.create(
            submission=new_submission,
            grade_label="Grade 4",
            enrolment=15,
            dnme=2,
            fs=3,
            s=4,
            vs=3,
            o=3,
            top_three_llc="Math",
            intervention_plan="Remediation",
        )

        self.client.force_login(self.sgod_admin)
        response = self.client.get(
            reverse("division_overview"),
            {"period_id": self.period.id, "section_code": other_section.code},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("kpi_rows", response.context)
        self.assertEqual(response.context["selected_section_code"], other_section.code)
        rows = response.context["kpi_rows"]
        north_row = next(row for row in rows if row["district"] == self.district_north)
        self.assertTrue(any(entry["head_name"] == "Pat Reyes" for entry in north_row["school_profiles"]))
        pending_entry = next(entry for entry in north_row["school_profiles"] if entry["school"] == self.school_pending)
        self.assertTrue(pending_entry["grade_span_warning"])
        self.assertTrue(pending_entry["missing_head_contact"])
        self.assertContains(response, "Check grade span")
        self.assertContains(response, "Contact missing")
        self.assertContains(response, other_section.name)

