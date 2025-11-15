import io

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts import roles, scope
from organizations.models import District, School, Section
from submissions.models import (
    Form1PctHeader,
    Form1PctRow,
    Form1SLPRow,
    FormTemplate,
    Period,
    Submission,
    SMEAActivityRow,
    SMEAProject,
)
from submissions.views import (
    rma_grade_labels_for_school,
    slp_grade_labels_for_school,
)


@pytest.fixture
def sample_env():
    User = get_user_model()

    section_smme = Section.objects.create(code="smme", name="School Management")
    section_other = Section.objects.create(code="hrd", name="HRD")

    district_north = District.objects.create(code="north", name="North District")
    district_south = District.objects.create(code="south", name="South District")

    school_primary = School.objects.create(
        code="north-es",
        name="North Elementary",
        district=district_north,
        school_type="Elementary",
        min_grade=1,
        max_grade=6,
    )
    school_secondary = School.objects.create(
        code="north-hs",
        name="North High",
        district=district_north,
        school_type="Secondary",
        min_grade=7,
        max_grade=12,
        implements_adm=True,
    )
    school_other = School.objects.create(
        code="south-es",
        name="South Elementary",
        district=district_south,
        school_type="Elementary",
        min_grade=1,
        max_grade=6,
    )

    today = timezone.now().date()
    period = Period.objects.create(
        label="Q1",
        school_year_start=2025,
        quarter_tag='Q1',
        display_order=1,
        is_active=True,
    )

    form_smme = FormTemplate.objects.create(
        section=section_smme,
        code="smea-form-1",
        title="SMEA Form 1",
        open_at=today,
        close_at=today,
        period_type=FormTemplate.PeriodType.QUARTER,
    )
    form_other = FormTemplate.objects.create(
        section=section_other,
        code="hrd-form-1",
        title="HRD Form 1",
        open_at=today,
        close_at=today,
        period_type=FormTemplate.PeriodType.QUARTER,
    )

    submission_smme = Submission.objects.create(
        school=school_primary,
        form_template=form_smme,
        period=period,
    )
    submission_other = Submission.objects.create(
        school=school_other,
        form_template=form_other,
        period=period,
    )
    project = SMEAProject.objects.create(
        submission=submission_smme,
        project_title="Project Alpha",
        area_of_concern="Reading",
    )
    SMEAActivityRow.objects.create(project=project, activity="Baseline")


    school_head = User.objects.create_user(username="school_head", password="pass")
    head_profile = roles.get_profile(school_head)
    head_profile.school = school_primary
    head_profile.save(update_fields=["school", "updated_at"])

    psds = User.objects.create_user(username="psds_user", password="pass")
    psds_profile = roles.get_profile(psds)
    psds_profile.districts.set([district_north])
    psds_profile.save(update_fields=["updated_at"])

    section_admin = User.objects.create_user(username="section_admin", password="pass")
    section_admin_profile = roles.get_profile(section_admin)
    section_admin_profile.section_admin_codes = [section_smme.code]
    section_admin_profile.save(update_fields=["section_admin_codes", "updated_at"])

    sgod_admin = User.objects.create_user(username="sgod_admin", password="pass")
    sgod_profile = roles.get_profile(sgod_admin)
    sgod_profile.is_sgod_admin = True
    sgod_profile.save(update_fields=["is_sgod_admin", "updated_at"])

    header = Form1PctHeader.objects.create(submission=submission_smme)
    area = Form1PctRow._meta.get_field("area").choices[0][0]
    Form1PctRow.objects.create(header=header, area=area, percent=10, action_points="Plan")
    Form1SLPRow.objects.create(
        submission=submission_smme,
        grade_label="Grade 3",
        enrolment=30,
        dnme=5,
        fs=5,
        s=10,
        vs=5,
        o=5,
    )

    return {
        "section_smme": section_smme,
        "section_other": section_other,
        "district_north": district_north,
        "district_south": district_south,
        "school_primary": school_primary,
        "school_secondary": school_secondary,
        "school_other": school_other,
        "submission_smme": submission_smme,
        "submission_other": submission_other,
        "school_head": school_head,
        "psds": psds,
        "section_admin": section_admin,
        "sgod_admin": sgod_admin,
    }


@pytest.mark.django_db
def test_school_head_scoping(sample_env):
    schools = set(scope.scope_schools(sample_env["school_head"]).values_list("code", flat=True))
    submissions = set(scope.scope_submissions(sample_env["school_head"]).values_list("id", flat=True))
    assert schools == {sample_env["school_primary"].code}
    assert submissions == {sample_env["submission_smme"].id}


@pytest.mark.django_db
def test_psds_scoping(sample_env):
    schools = set(scope.scope_schools(sample_env["psds"]).values_list("code", flat=True))
    assert schools == {sample_env["school_primary"].code, sample_env["school_secondary"].code}


@pytest.mark.django_db
def test_section_admin_review_permissions(sample_env, client: Client):
    client.force_login(sample_env["section_admin"])
    ok_response = client.get(reverse("review_detail", args=[sample_env["submission_smme"].id]))
    assert ok_response.status_code == 200

    forbidden = client.get(reverse("review_detail", args=[sample_env["submission_other"].id]))
    assert forbidden.status_code == 403


@pytest.mark.django_db
def test_sgod_admin_sees_all(sample_env):
    schools = set(scope.scope_schools(sample_env["sgod_admin"]).values_list("code", flat=True))
    assert schools == {sample_env["school_primary"].code, sample_env["school_secondary"].code, sample_env["school_other"].code}


@pytest.mark.django_db
def test_pct_row_validation(sample_env):
    header = Form1PctHeader.objects.get(submission=sample_env["submission_smme"])
    choices = [choice[0] for choice in Form1PctRow._meta.get_field("area").choices]
    existing = set(header.rows.values_list("area", flat=True))
    area = next(choice for choice in choices if choice not in existing)
    row = Form1PctRow(header=header, area=area, percent=150, action_points="Overflow")
    with pytest.raises(ValidationError):
        row.full_clean()


@pytest.mark.django_db
def test_slp_row_validation(sample_env):
    row = Form1SLPRow(
        submission=sample_env["submission_smme"],
        grade_label="Grade 4",
        enrolment=5,
        dnme=3,
        fs=3,
        s=0,
        vs=0,
        o=0,
    )
    with pytest.raises(ValidationError):
        row.full_clean()


@pytest.mark.django_db
def test_grade_label_helpers(sample_env):
    slp_labels = slp_grade_labels_for_school(sample_env["school_primary"])
    assert slp_labels[0] == "Grade 1"
    rma_labels = rma_grade_labels_for_school(sample_env["school_primary"])
    assert "g1" in rma_labels


@pytest.mark.django_db
def test_export_csv_has_expected_columns(sample_env, client: Client):
    client.force_login(sample_env["section_admin"])
    url = reverse("review_submission_export", args=[sample_env["submission_smme"].id, "csv"])
    response = client.get(f"{url}?tab=slp")
    assert response.status_code == 200
    assert b"Grade,Enrolment" in response.content


@pytest.mark.django_db
def test_locking_blocks_post_when_submitted(sample_env, client: Client):
    submission = sample_env["submission_smme"]
    submission.mark_submitted(sample_env["school_head"])
    client.force_login(sample_env["school_head"])
    response = client.post(
        reverse("edit_submission", args=[submission.id]),
        {"tab": "pct", "action": "save"},
    )
    assert response.status_code == 403
