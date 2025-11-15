"""Utility helpers for seeding a demo dataset that is safe to rerun."""

import csv
import datetime
import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from accounts.models import UserProfile
from organizations.models import District, Section, School, SchoolProfile
from submissions import constants as smea_constants
from submissions.models import (
    Form1ADMRow,
    Form1PctHeader,
    Form1PctRow,
    Form1ReadingCRLA,
    Form1ReadingIntervention,
    Form1ReadingPHILIRI,
    Form1RMARow,
    Form1RMAIntervention,
    Form1SLPAnalysis,
    Form1SLPRow,
    Form1SLPTopDNME,
    Form1SLPTopOutstanding,
    Form1SupervisionRow,
    FormTemplate,
    Period,
    Submission,
    SMEAActivityRow,
    SMEAProject,
)

ROLE_GROUPS = [
    "SchoolHead",
    "SectionAdmin:yfs",
    "SectionAdmin:pr",
    "SectionAdmin:smme",
    "SectionAdmin:hrd",
    "SectionAdmin:smn",
    "SectionAdmin:drrm",
    "SGODAdmin",
    "ASDS",
    "SDS",
]

GRADE_SPANS = {
    "elementary": (1, 6),
    "secondary": (7, 12),
}

DEMO_PASSWORD = "demo12345"


def seed_groups() -> None:
    """Ensure role groups exist."""

    for name in ROLE_GROUPS:
        Group.objects.get_or_create(name=name)


def _load_school_rows(base_path: Path) -> list[dict]:
    rows: list[dict] = []
    path = base_path / "schools.sample.csv"
    if not path.exists():
        return rows
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = [row for row in reader]
    return rows


def seed_districts(base_path: Path) -> list[str]:
    """Create districts from the sample CSV."""

    created_codes: list[str] = []
    for row in _load_school_rows(base_path):
        name = (row.get("district") or "").strip()
        if not name:
            continue
        code = slugify(name)
        district, _ = District.objects.update_or_create(
            code=code,
            defaults={"name": name},
        )
        created_codes.append(district.code)
    return created_codes


def seed_sections(base_path: Path) -> None:
    with open(base_path / "sections.seed.json", "r", encoding="utf-8") as handle:
        for item in json.load(handle):
            Section.objects.update_or_create(
                code=item["code"],
                defaults={"name": item["name"]},
            )


def seed_schools(base_path: Path) -> None:
    for row in _load_school_rows(base_path):
        School.objects.update_or_create(
            code=row["code"],
            defaults={
                "name": row.get("name", row["code"]).strip(),
                "division": row.get("division", ""),
                "school_type": row.get("school_type", ""),
            },
        )


def seed_school_props(base_path: Path) -> dict[str, int]:
    """Attach districts and grade spans to schools."""

    rows = {row["code"]: row for row in _load_school_rows(base_path)}
    updated = 0
    assigned_districts = 0
    profiles_created = 0
    profiles_updated = 0

    for school in School.objects.all():
        row = rows.get(school.code)
        updates: list[str] = []

        if row:
            district_name = (row.get("district") or "").strip()
            if district_name:
                district = District.objects.filter(name=district_name).first()
                if district and school.district_id != district.id:
                    school.district = district
                    updates.append("district")
                    assigned_districts += 1

            school_type = (row.get("school_type") or school.school_type or "").lower()
        else:
            school_type = (school.school_type or "").lower()

        if school_type in GRADE_SPANS:
            min_grade, max_grade = GRADE_SPANS[school_type]
            if school.min_grade != min_grade:
                school.min_grade = min_grade
                updates.append("min_grade")
            if school.max_grade != max_grade:
                school.max_grade = max_grade
                updates.append("max_grade")
            implements = school_type == "secondary"
            if school.implements_adm != implements:
                school.implements_adm = implements
                updates.append("implements_adm")

        if updates:
            school.save(update_fields=updates)
            updated += 1

        profile, created = SchoolProfile.objects.get_or_create(school=school)
        if created:
            profiles_created += 1
        profile_updates: list[str] = []
        if school.min_grade is not None and profile.grade_span_start != school.min_grade:
            profile.grade_span_start = school.min_grade
            profile_updates.append("grade_span_start")
        if school.max_grade is not None and profile.grade_span_end != school.max_grade:
            profile.grade_span_end = school.max_grade
            profile_updates.append("grade_span_end")
        if profile_updates:
            profile.save(update_fields=profile_updates + ["updated_at"])
            profiles_updated += 1

    return {
        "updated": updated,
        "district_assignments": assigned_districts,
        "profiles_created": profiles_created,
        "profiles_updated": profiles_updated,
    }


def seed_period() -> None:
    Period.objects.update_or_create(
        school_year_start=2025,
        quarter_tag='Q1',
        defaults={
            "label": "Q1",
            "display_order": 1,
            "is_active": True,
        },
    )


def seed_form_templates(base_path: Path) -> None:
    with open(base_path / "formtemplates.seed.json", "r", encoding="utf-8") as handle:
        for entry in json.load(handle):
            section = Section.objects.get(code=entry["section"])
            FormTemplate.objects.update_or_create(
                code=entry["code"],
                defaults={
                    "section": section,
                    "title": entry["title"],
                    "version": entry.get("version", ""),
                    "period_type": entry.get("period_type", FormTemplate.PeriodType.QUARTER),
                    "open_at": datetime.date.fromisoformat(entry["open_at"]),
                    "close_at": datetime.date.fromisoformat(entry["close_at"]),
                    "is_active": entry.get("is_active", True),
                    "schema_descriptor": entry.get("schema_descriptor", {}),
                },
            )


def seed_roles() -> list[dict[str, str]]:
    """Create demo users representing common roles."""

    seed_groups()
    User = get_user_model()

    primary_school = School.objects.order_by("code").first()
    secondary_school = School.objects.filter(school_type__iexact="Secondary").order_by("code").first() or primary_school
    district = District.objects.order_by("name").first()
    section_smme = Section.objects.filter(code="smme").first()

    demo_specs: list[dict] = [
        {
            "username": "demo_sgod_admin",
            "email": "sgod.admin@example.com",
            "label": "SGOD Admin",
            "profile": {"is_sgod_admin": True},
            "groups": ["SGODAdmin"],
        },
    ]

    if section_smme:
        demo_specs.append(
            {
                "username": "demo_section_admin",
                "email": "section.admin@example.com",
                "label": "Section Admin (SMME)",
                "profile": {"section_admin_codes": [section_smme.code]},
                "groups": ["SectionAdmin:smme"],
            }
        )

    if district:
        demo_specs.append(
            {
                "username": "demo_psds",
                "email": "psds@example.com",
                "label": "PSDS",
                "profile": {"districts": [district]},
                "groups": [],
            }
        )

    if primary_school:
        demo_specs.append(
            {
                "username": "demo_school_head",
                "email": "school.head@example.com",
                "label": "School Head",
                "profile": {"school": primary_school},
                "groups": ["SchoolHead"],
            }
        )

    if secondary_school and secondary_school != primary_school:
        demo_specs.append(
            {
                "username": "demo_secondary_head",
                "email": "secondary.head@example.com",
                "label": "Secondary School Head",
                "profile": {"school": secondary_school},
                "groups": ["SchoolHead"],
            }
        )

    demo_accounts: list[dict[str, str]] = []

    for spec in demo_specs:
        user, _ = User.objects.get_or_create(
            username=spec["username"],
            defaults={"email": spec["email"]},
        )
        user.email = spec["email"]
        user.set_password(DEMO_PASSWORD)
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile_updates: list[str] = []
        profile_data = spec.get("profile", {})

        if profile_data.get("is_sgod_admin") and not profile.is_sgod_admin:
            profile.is_sgod_admin = True
            profile_updates.append("is_sgod_admin")

        if profile_data.get("school") and profile.school_id != profile_data["school"].id:
            profile.school = profile_data["school"]
            profile_updates.append("school")

        section_codes = profile_data.get("section_admin_codes")
        if section_codes is not None and profile.section_admin_codes != section_codes:
            profile.section_admin_codes = section_codes
            profile_updates.append("section_admin_codes")

        if profile_updates:
            profile_updates.append("updated_at")
            profile.save(update_fields=profile_updates)
        else:
            profile.save(update_fields=["updated_at"])

        districts = profile_data.get("districts")
        if districts is not None:
            profile.districts.set(districts)

        for group_name in spec.get("groups", []):
            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)

        demo_accounts.append(
            {
                "label": spec["label"],
                "email": user.email,
                "password": DEMO_PASSWORD,
            }
        )

    return demo_accounts


def _seed_pct_rows(submission):
    header, _ = Form1PctHeader.objects.get_or_create(submission=submission)
    choices = [choice[0] for choice in Form1PctRow._meta.get_field("area").choices]
    sample_percents = {choices[0]: 85, choices[1]: 78, choices[2]: 90, choices[3]: 70}
    for area in choices:
        # Provide defaults to satisfy NOT NULL constraints during initial insert
        row, _ = Form1PctRow.objects.get_or_create(
            header=header,
            area=area,
            defaults={"percent": 0, "action_points": ""},
        )
        row.percent = sample_percents.get(area, 60)
        row.action_points = row.action_points or "Continue monitoring implementation."
        row.save()


def _seed_slp_rows(submission, school):
    labels = ["Grade 3", "Grade 4"]
    for label in labels:
        row, _ = Form1SLPRow.objects.get_or_create(
            submission=submission,
            grade_label=label,
            defaults={"enrolment": 30, "dnme": 5, "fs": 6, "s": 8, "vs": 6, "o": 5},
        )
        if row.enrolment == 0:
            row.enrolment = 30
        row.dnme = row.dnme or 5
        row.fs = row.fs or 6
        row.s = row.s or 8
        row.vs = row.vs or 6
        row.o = row.o or 5
        row.top_three_llc = row.top_three_llc or "Comprehension, Fluency, Vocabulary"
        row.intervention_plan = row.intervention_plan or "Reading camp and peer tutoring"
        row.save()
    # Ensure analysis objects exist for SLP rows
    for slp in Form1SLPRow.objects.filter(submission=submission):
        Form1SLPAnalysis.objects.update_or_create(
            slp_row=slp,
            defaults={
                "dnme_factors": "Limited access to supplementary reading materials.",
                "fs_factors": "Irregular study habits.",
                "s_practices": "Peer learning and guided reading.",
                "vs_practices": "Enrichment activities and mentoring.",
                "o_practices": "Advanced modules and competitions.",
                "overall_strategy": "Reading camp and parent coaching",
            },
        )
    Form1SLPTopDNME.objects.update_or_create(
        submission=submission,
        position=1,
        defaults={"grade_label": "Grade 3", "count": 5},
    )
    Form1SLPTopOutstanding.objects.update_or_create(
        submission=submission,
        position=1,
        defaults={"grade_label": "Grade 6", "count": 4},
    )


def _seed_reading_blocks(submission):
    Form1ReadingCRLA.objects.update_or_create(
        submission=submission,
        level=smea_constants.CRLALevel.GRADE3,
        timing=smea_constants.CRLATiming.BOY,
        subject=smea_constants.CRLASubject.ENGLISH,
        band=smea_constants.CRLABand.INSTRUCTIONAL,
        defaults={"count": 12},
    )
    Form1ReadingPHILIRI.objects.update_or_create(
        submission=submission,
        level=smea_constants.CRLALevel.GRADE3,
        timing=smea_constants.AssessmentTiming.BOY,
        language=smea_constants.PHILIRILanguage.ENGLISH,
        defaults={"band_4_7": 1, "band_5_8": 2, "band_6_9": 3, "band_10": 4},
    )
    Form1ReadingIntervention.objects.update_or_create(
        submission=submission,
        order=1,
        defaults={"description": "Reading buddy system"},
    )


def _seed_rma_blocks(submission):
    Form1RMARow.objects.update_or_create(
        submission=submission,
        grade_label=smea_constants.RMAGradeLabel.GRADE3,
        defaults={
            "enrolment": 35,
            "emerging_not_proficient": 6,
            "emerging_low_proficient": 7,
            "developing_nearly_proficient": 8,
            "transitioning_proficient": 7,
            "at_grade_level": 7,
        },
    )
    Form1RMAIntervention.objects.update_or_create(
        submission=submission,
        order=1,
        defaults={"description": "Focused math clinics"},
    )


def _seed_supervision(submission):
    Form1SupervisionRow.objects.update_or_create(
        submission=submission,
        grade_label="Grade 5",
        defaults={
            "teachers_supervised_observed_ta": 5,
            "intervention_support_provided": "Conducted coaching sessions",
            "result": "Improved lesson preparation",
        },
    )


def _seed_adm(submission):
    Form1ADMRow.objects.update_or_create(
        submission=submission,
        defaults={
            "ppas_conducted": "School DRRM orientation",
            "ppas_physical_target": 10,
            "ppas_physical_actual": 8,
            "ppas_physical_percent": 80,
            "funds_downloaded": 150000,
            "funds_obligated": 120000,
            "funds_unobligated": 30000,
            "funds_percent_obligated": 80,
            "funds_percent_burn_rate": 65,
            "q1_response": "Completed procurement of learning materials.",
            "q2_response": "Need additional laptops.",
            "q3_response": "Coordinated with LGU for support.",
            "q4_response": "",
            "q5_response": "",
        },
    )


def seed_demo_submission() -> dict[str, str] | None:
    section = Section.objects.filter(code="smme").first()
    period = Period.objects.order_by("-school_year_start", "-display_order").first()
    school = School.objects.order_by("code").first()
    if not (section and period and school):
        return None

    User = get_user_model()
    school_head = User.objects.filter(username="demo_school_head").first()
    if school_head:
        profile = UserProfile.objects.get(user=school_head)
        if profile.school_id != school.id:
            profile.school = school
            profile.save(update_fields=["school", "updated_at"])

    section_admin = User.objects.filter(username="demo_section_admin").first()

    form = FormTemplate.objects.filter(section=section).order_by("code").first()
    if not form:
        return None

    submission, created = Submission.objects.get_or_create(
        school=school,
        form_template=form,
        period=period,
        defaults={"status": Submission.Status.DRAFT},
    )
    submission.status = Submission.Status.DRAFT
    submission.last_modified_by = school_head or section_admin
    submission.save(update_fields=["status", "last_modified_by", "updated_at"])

    project, _ = SMEAProject.objects.get_or_create(
        submission=submission,
        project_title="Reading Recovery Program",
        defaults={"area_of_concern": "Reading", "conference_date": datetime.date(period.school_year_start, 9, 5)},
    )
    SMEAActivityRow.objects.update_or_create(
        project=project,
        activity="Conduct weekend reading camp",
        defaults={
            "output_target": "50 learners",
            "output_actual": "45 learners",
            "timeframe_target": "Sept Week 1",
            "timeframe_actual": "Sept Week 2",
            "budget_target": "25,000",
            "budget_actual": "22,500",
            "interpretation": "Slight delay but targets achieved",
            "issues_unaddressed": "Attendance dip on Sundays",
            "facilitating_factors": "LGU support",
            "agreements": "Provide snacks to sustain attendance",
        },
    )

    _seed_pct_rows(submission)
    _seed_slp_rows(submission, school)
    _seed_reading_blocks(submission)
    _seed_rma_blocks(submission)
    _seed_supervision(submission)
    if school.implements_adm:
        _seed_adm(submission)

    try:
        if section_admin:
            submission.mark_submitted(section_admin)
            submission.mark_returned(section_admin, "Please update data for Q2 before noting.")
    except ValidationError:
        pass

    return {"submission_id": submission.id, "status": submission.status}


def run() -> None:
    base = Path("data")

    district_codes = seed_districts(base)
    seed_sections(base)
    seed_schools(base)
    school_stats = seed_school_props(base)
    seed_period()
    seed_form_templates(base)
    demo_accounts = seed_roles()
    demo_submission = seed_demo_submission()

    print("Seed complete.")
    print(f"  Districts processed: {len(set(district_codes))}")
    print(f"  Schools updated with grade spans: {school_stats['updated']}")
    print(f"  School profiles created: {school_stats['profiles_created']}, updated: {school_stats['profiles_updated']}")
    if demo_accounts:
        print("Demo accounts (default password: demo12345):")
        for account in demo_accounts:
            print(f"  - {account['label']}: {account['email']}")
        print("Use these credentials to sign in locally once runserver is running.")

    if demo_submission:
        status_value = demo_submission.get("status")
        try:
            status_label = Submission.Status(status_value).label if status_value else 'n/a'
        except ValueError:
            status_label = status_value
        print(f"Demo SMME submission ready (ID: {demo_submission['submission_id']}, status: {status_label}).")
    else:
        print("Demo SMME submission skipped (seed core reference data first).")

if __name__ == "__main__":
    run()




