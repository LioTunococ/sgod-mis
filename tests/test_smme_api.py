from django.test import TestCase
from django.urls import reverse

from organizations.models import District, School, Section, SchoolProfile
from submissions.models import (
    Period,
    FormTemplate,
    Submission,
    Form1SLPRow,
    ReadingAssessmentCRLA,
    ReadingAssessmentPHILIRI,
    Form1RMARow,
    Form1SupervisionRow,
)
from django.utils import timezone
from django.contrib.auth import get_user_model


class TestSMMEApi(TestCase):
    def setUp(self):
        # Authenticated user (bypass login_required)
        User = get_user_model()
        self.user = User.objects.create_user(username="tester", password="pass", email="t@example.com")
        self.client.force_login(self.user)
        # Minimal organizational data
        self.dist_a = District.objects.create(code="a", name="A District")
        self.dist_b = District.objects.create(code="b", name="B District")
        self.sch1 = School.objects.create(code="s1", name="Zeta HS", district=self.dist_b)
        self.sch2 = School.objects.create(code="s2", name="Alpha ES", district=self.dist_a)
        # Provide profiles to avoid RelatedObjectDoesNotExist on reverse one-to-one
        SchoolProfile.objects.create(school=self.sch1, grade_span_start=7, grade_span_end=12)
        SchoolProfile.objects.create(school=self.sch2, grade_span_start=1, grade_span_end=6)

        # Period for SY2025-2026 Q1
        self.period = Period.objects.create(
            label="Q1",
            school_year_start=2025,
            quarter_tag="Q1",
            display_order=1,
            is_active=True,
        )

        # Section and form template for SMME
        self.section = Section.objects.create(code="smme", name="SMME")
        today = timezone.localdate()
        self.form = FormTemplate.objects.create(
            section=self.section,
            code="form1",
            title="SMEA Form 1",
            version="v1",
            open_at=today,
            close_at=today,
            is_active=True,
            school_year=2025,
            quarter_filter="Q1",
        )

    def test_api_overview_basic(self):
        url = reverse("smme_kpi_api")
        resp = self.client.get(url, {
            "school_year": 2025,
            "quarter": "all",
            "kpi_part": "all",
            "page": 1,
            "page_size": 50,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert set(["view", "page", "page_size", "total", "results"]) <= set(data.keys())

    def test_api_overview_sort_by_district(self):
        url = reverse("smme_kpi_api")
        # Expect A District (Alpha ES) to appear before B District (Zeta HS)
        resp = self.client.get(url, {
            "school_year": 2025,
            "quarter": "all",
            "kpi_part": "all",
            "sort_by": "district",
            "sort_dir": "asc",
            "page": 1,
            "page_size": 50,
        })
        assert resp.status_code == 200
        results = resp.json()["results"]
        # There may be 0 rows if no periods found; ensure at least the schools are listed
        # The overview returns all schools even if no KPI data (has_data False)
        # Ensure two schools present
        names = [r["school_name"] for r in results]
        assert self.sch2.name in names and self.sch1.name in names
        # Sort order by district then school name
        districts = [r["district"] for r in results]
        # First occurrence of A District should be before B District
        assert districts.index("A District") < districts.index("B District")

    def test_api_slp_subject_sorting(self):
        # Create a submission with two SLP rows (different proficiencies)
        sub = Submission.objects.create(
            school=self.sch2,
            form_template=self.form,
            period=self.period,
            status=Submission.Status.SUBMITTED,
        )
        # Subject with higher proficiency (more S+VS+O)
        Form1SLPRow.objects.create(
            submission=sub,
            grade_label="Grade 4",
            subject="ENG",
            enrolment=100,
            dnme=10, fs=10, s=30, vs=30, o=20,
            is_offered=True,
        )
        # Subject with lower proficiency
        Form1SLPRow.objects.create(
            submission=sub,
            grade_label="Grade 4",
            subject="MATH",
            enrolment=100,
            dnme=40, fs=20, s=20, vs=10, o=10,
            is_offered=True,
        )

        url = reverse("smme_kpi_api")
        resp = self.client.get(url, {
            "school_year": 2025,
            "quarter": "all",
            "kpi_part": "slp",
            "sort_by": "subject_proficiency",
            "sort_dir": "desc",
            "page": 1,
            "page_size": 50,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        school_block = next(r for r in data["results"] if r["school_name"] == self.sch2.name)
        subjects = [s["subject"] for s in school_block["subjects"]]
        # ENG should come before MATH when sorting by proficiency desc
        assert subjects.index("ENG") < subjects.index("MATH")

    def test_api_reading_crla_bosy_sorting(self):
        # Create submission and CRLA rows for BOSY
        sub = Submission.objects.create(
            school=self.sch2,
            form_template=self.form,
            period=self.period,
            status=Submission.Status.SUBMITTED,
        )
        # Low Emerging total 30, Developing 70 → developing_pct higher
        ReadingAssessmentCRLA.objects.create(
            submission=sub, period="bosy", level="low_emerging",
            mt_grade_1=10, mt_grade_2=10, mt_grade_3=10,
            fil_grade_2=0, fil_grade_3=0, eng_grade_3=0,
        )
        ReadingAssessmentCRLA.objects.create(
            submission=sub, period="bosy", level="developing",
            mt_grade_1=20, mt_grade_2=20, mt_grade_3=30,
            fil_grade_2=0, fil_grade_3=0, eng_grade_3=0,
        )
        url = reverse("smme_kpi_api")
        resp = self.client.get(url, {
            "school_year": 2025,
            "quarter": "all",
            "kpi_part": "reading",
            "reading_type": "crla",
            "assessment_timing": "bosy",
            "sort_by": "developing",
            "sort_dir": "desc",
        })
        assert resp.status_code == 200
        data = resp.json()
        row = next(r for r in data["results"] if r["school_name"] == self.sch2.name)
        assert row["developing_pct"] > row["low_emerging_pct"]

    def test_api_reading_philiri_mosy_keys(self):
        # Create submission and PHILIRI rows for MOSY
        sub = Submission.objects.create(
            school=self.sch1,
            form_template=self.form,
            period=self.period,
            status=Submission.Status.SUBMITTED,
        )
        ReadingAssessmentPHILIRI.objects.create(
            submission=sub, period="mosy", level="instructional",
            eng_grade_4=5, eng_grade_5=5, eng_grade_6=5, eng_grade_7=5, eng_grade_8=5, eng_grade_9=5, eng_grade_10=5,
            fil_grade_4=3, fil_grade_5=3, fil_grade_6=3, fil_grade_7=3, fil_grade_8=3, fil_grade_9=3, fil_grade_10=3,
        )
        ReadingAssessmentPHILIRI.objects.create(
            submission=sub, period="mosy", level="independent",
            eng_grade_4=2, eng_grade_5=2, eng_grade_6=2, eng_grade_7=2, eng_grade_8=2, eng_grade_9=2, eng_grade_10=2,
            fil_grade_4=1, fil_grade_5=1, fil_grade_6=1, fil_grade_7=1, fil_grade_8=1, fil_grade_9=1, fil_grade_10=1,
        )
        url = reverse("smme_kpi_api")
        resp = self.client.get(url, {
            "school_year": 2025,
            "quarter": "all",
            "kpi_part": "reading",
            "reading_type": "philiri",
            "assessment_timing": "mosy",
            "sort_by": "independent",
            "sort_dir": "desc",
        })
        assert resp.status_code == 200
        row = next(r for r in resp.json()["results"] if r["school_name"] == self.sch1.name)
        assert set(["frustration_pct","instructional_pct","independent_pct"]).issubset(row.keys())

    def test_api_rma_percentages(self):
        # Create submission and RMA rows
        sub = Submission.objects.create(
            school=self.sch1,
            form_template=self.form,
            period=self.period,
            status=Submission.Status.SUBMITTED,
        )
        Form1RMARow.objects.create(
            submission=sub, grade_label="g4", enrolment=100,
            emerging_not_proficient=10,
            emerging_low_proficient=20,
            developing_nearly_proficient=30,
            transitioning_proficient=25,
            at_grade_level=15,
        )
        url = reverse("smme_kpi_api")
        resp = self.client.get(url, {
            "school_year": 2025,
            "quarter": "all",
            "kpi_part": "rma",
            "rma_grade": "g4",
            "sort_by": "proficient",
            "sort_dir": "desc",
        })
        assert resp.status_code == 200
        row = next(r for r in resp.json()["results"] if r["school_name"] == self.sch1.name)
        # Check one computed percentage
        assert row["proficient_pct"] == 25.0

    def test_api_rma_no_data_placeholder(self):
        """When a school has no submitted/noted RMA rows, it should still appear with has_data False."""
        url = reverse("smme_kpi_api")
        resp = self.client.get(url, {
            "school_year": 2025,
            "quarter": "all",
            "kpi_part": "rma",
            "rma_grade": "g4",
        })
        assert resp.status_code == 200
        results = resp.json()["results"]
        # Both schools should be present even without data
        names = {r["school_name"] for r in results}
        assert self.sch1.name in names and self.sch2.name in names
        # Each row with no data should have has_data False and zero percentages
        placeholders = [r for r in results if r["school_name"] in [self.sch1.name, self.sch2.name] and r.get("has_data") is False]
        assert placeholders, "Expected placeholder rows for schools without RMA data"
        for p in placeholders:
            assert p["proficient_pct"] == 0.0

    def test_api_supervision_percent_ta(self):
        sub = Submission.objects.create(
            school=self.sch2,
            form_template=self.form,
            period=self.period,
            status=Submission.Status.SUBMITTED,
        )
        Form1SupervisionRow.objects.create(
            submission=sub, grade_label="G4", total_teachers=10, teachers_supervised_observed_ta=4
        )
        Form1SupervisionRow.objects.create(
            submission=sub, grade_label="G5", total_teachers=5, teachers_supervised_observed_ta=1
        )
        url = reverse("smme_kpi_api")
        resp = self.client.get(url, {
            "school_year": 2025,
            "quarter": "all",
            "kpi_part": "supervision",
            "sort_by": "percent_ta",
            "sort_dir": "desc",
        })
        assert resp.status_code == 200
        row = next(r for r in resp.json()["results"] if r["school_name"] == self.sch2.name)
        # total supervised = 5 / total teachers = 15 -> 33.3%
        assert round(row["percent_ta"], 1) == 33.3

    def test_api_all_quarters_placeholders_across_parts(self):
        """For quarter=all, schools without finalized data should appear with has_data False across KPI parts."""
        url = reverse("smme_kpi_api")

        # 1) Overview (kpi_part=all): results should include both schools; fields present; no data KPIs are zero-ish
        resp = self.client.get(url, {
            "school_year": 2025,
            "quarter": "all",
            "kpi_part": "all",
            "page": 1,
            "page_size": 50,
        })
        assert resp.status_code == 200
        oresults = resp.json()["results"]
        onames = {r["school_name"] for r in oresults}
        assert self.sch1.name in onames and self.sch2.name in onames

        # 2) SLP: no submissions yet → rows present for each school with has_data False or empty subjects
        resp = self.client.get(url, {
            "school_year": 2025,
            "quarter": "all",
            "kpi_part": "slp",
            "page": 1,
            "page_size": 50,
        })
        assert resp.status_code == 200
        slp_rows = resp.json()["results"]
        slp_names = {r["school_name"] for r in slp_rows}
        assert self.sch1.name in slp_names and self.sch2.name in slp_names
        # Each result should either have has_data False or no subjects listed
        for r in slp_rows:
            if r.get("has_data") is False:
                continue
            # Some views structure SLP as subjects per school
            subjects = r.get("subjects", [])
            assert subjects == [] or r.get("has_data") is False

        # 3) RMA: ensure placeholders exist and have_data False
        resp = self.client.get(url, {
            "school_year": 2025,
            "quarter": "all",
            "kpi_part": "rma",
            "rma_grade": "g4",
        })
        assert resp.status_code == 200
        rma_rows = resp.json()["results"]
        rma_names = {r["school_name"] for r in rma_rows}
        assert self.sch1.name in rma_names and self.sch2.name in rma_names
        placeholders = [r for r in rma_rows if r.get("has_data") is False]
        assert placeholders, "Expected RMA placeholders for schools with no data in 'all' quarter"

    def test_inactive_form_template_excluded(self):
        """Submissions tied to inactive FormTemplate should be ignored in KPI calculations and placeholders only reflect active forms."""
        # Create an additional inactive form template for same section & period
        inactive_form = FormTemplate.objects.create(
            section=self.section,
            code="form1_old",
            title="SMEA Form 1 Old",
            version="v0",
            open_at=self.form.open_at,
            close_at=self.form.close_at,
            is_active=False,  # explicitly inactive
            school_year=2025,
            quarter_filter="Q1",
        )
        # Submission using inactive form (should be ignored)
        sub_inactive = Submission.objects.create(
            school=self.sch1,
            form_template=inactive_form,
            period=self.period,
            status=Submission.Status.SUBMITTED,
        )
        Form1SLPRow.objects.create(
            submission=sub_inactive,
            grade_label="Grade 7",
            subject="MATH",
            enrolment=10,
            dnme=2, fs=2, s=2, vs=2, o=2,
            is_offered=True,
        )
        # Active form submission for other school
        sub_active = Submission.objects.create(
            school=self.sch2,
            form_template=self.form,
            period=self.period,
            status=Submission.Status.SUBMITTED,
        )
        Form1SLPRow.objects.create(
            submission=sub_active,
            grade_label="Grade 4",
            subject="ENG",
            enrolment=20,
            dnme=5, fs=5, s=5, vs=3, o=2,
            is_offered=True,
        )
        url = reverse("smme_kpi_api")
        resp = self.client.get(url, {
            "school_year": 2025,
            "quarter": "all",
            "kpi_part": "slp",
            "page": 1,
            "page_size": 50,
        })
        assert resp.status_code == 200
        results = resp.json()["results"]
        # Find rows for each school
        row_sch1 = next(r for r in results if r["school_name"] == self.sch1.name)
        row_sch2 = next(r for r in results if r["school_name"] == self.sch2.name)
        # School 1 only has inactive form data → should appear as placeholder (has_data False or empty subjects)
        assert row_sch1.get("has_data") is False or row_sch1.get("subjects", []) == []
        # School 2 has active form data → should have has_data True and at least one subject
        assert row_sch2.get("has_data") is True
        assert row_sch2.get("subjects") and any(s.get("subject") == "ENG" for s in row_sch2.get("subjects"))

    def test_inactive_form_template_excluded_rma(self):
        """Inactive form RMA rows must be ignored; school with only inactive data appears as placeholder."""
        inactive_form = FormTemplate.objects.create(
            section=self.section,
            code="form1_old_rma",
            title="SMEA Form 1 Old RMA",
            version="v0",
            open_at=self.form.open_at,
            close_at=self.form.close_at,
            is_active=False,
            school_year=2025,
            quarter_filter="Q1",
        )
        active_sub = Submission.objects.create(
            school=self.sch2,
            form_template=self.form,
            period=self.period,
            status=Submission.Status.SUBMITTED,
        )
        Form1RMARow.objects.create(
            submission=active_sub,
            grade_label="g4",
            enrolment=50,
            emerging_not_proficient=5,
            emerging_low_proficient=10,
            developing_nearly_proficient=15,
            transitioning_proficient=10,
            at_grade_level=10,
        )
        inactive_sub = Submission.objects.create(
            school=self.sch1,
            form_template=inactive_form,
            period=self.period,
            status=Submission.Status.SUBMITTED,
        )
        Form1RMARow.objects.create(
            submission=inactive_sub,
            grade_label="g4",
            enrolment=40,
            emerging_not_proficient=10,
            emerging_low_proficient=10,
            developing_nearly_proficient=10,
            transitioning_proficient=5,
            at_grade_level=5,
        )
        url = reverse("smme_kpi_api")
        resp = self.client.get(url, {
            "school_year": 2025,
            "quarter": "all",
            "kpi_part": "rma",
            "rma_grade": "g4",
        })
        assert resp.status_code == 200
        results = resp.json()["results"]
        sch1_row = next(r for r in results if r["school_name"] == self.sch1.name)
        sch2_row = next(r for r in results if r["school_name"] == self.sch2.name)
        # School 1 only inactive data → placeholder
        assert sch1_row.get("has_data") is False
        # School 2 active data retained
        assert sch2_row.get("has_data") is True
        assert sch2_row["proficient_pct"] > 0.0

    def test_inactive_form_template_excluded_reading_crla(self):
        """Inactive form reading CRLA rows ignored; placeholder for inactive-only school."""
        inactive_form = FormTemplate.objects.create(
            section=self.section,
            code="form1_old_crla",
            title="SMEA Form 1 Old CRLA",
            version="v0",
            open_at=self.form.open_at,
            close_at=self.form.close_at,
            is_active=False,
            school_year=2025,
            quarter_filter="Q1",
        )
        # Active CRLA data for sch2
        active_sub = Submission.objects.create(
            school=self.sch2,
            form_template=self.form,
            period=self.period,
            status=Submission.Status.SUBMITTED,
        )
        ReadingAssessmentCRLA.objects.create(
            submission=active_sub,
            period="bosy",
            level="developing",
            mt_grade_1=5, mt_grade_2=5, mt_grade_3=5,
            fil_grade_2=0, fil_grade_3=0, eng_grade_3=0,
        )
        # Inactive CRLA data for sch1
        inactive_sub = Submission.objects.create(
            school=self.sch1,
            form_template=inactive_form,
            period=self.period,
            status=Submission.Status.SUBMITTED,
        )
        ReadingAssessmentCRLA.objects.create(
            submission=inactive_sub,
            period="bosy",
            level="developing",
            mt_grade_1=10, mt_grade_2=10, mt_grade_3=10,
            fil_grade_2=0, fil_grade_3=0, eng_grade_3=0,
        )
        url = reverse("smme_kpi_api")
        resp = self.client.get(url, {
            "school_year": 2025,
            "quarter": "all",
            "kpi_part": "reading",
            "reading_type": "crla",
            "assessment_timing": "bosy",
            "sort_by": "developing",
            "sort_dir": "desc",
        })
        assert resp.status_code == 200
        results = resp.json()["results"]
        sch1_row = next(r for r in results if r["school_name"] == self.sch1.name)
        sch2_row = next(r for r in results if r["school_name"] == self.sch2.name)
        assert sch1_row.get("has_data") is False
        # sch2 has developing_pct > 0
        assert sch2_row.get("developing_pct", 0) > 0
