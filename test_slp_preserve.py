#!/usr/bin/env python3
"""Sequential SLP subject save preservation test.
Ensures saving a second subject does not clear competencies/interventions of the first.
"""
import os, sys, json, datetime as dt
import django
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.append(project_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sgod_mis.settings.dev")
django.setup()

from organizations.models import Section, School  # noqa: E402
from submissions.models import Period, FormTemplate, Submission, Form1SLPRow  # noqa: E402
from accounts.roles import get_profile  # noqa: E402

User = get_user_model()


def _make_submission() -> Submission:
    section = Section.objects.create(code="slp", name="SLP Section")
    school = School.objects.create(code="sch-seq", name="Seq School", min_grade=1, max_grade=10)
    period = Period.objects.create(label="Q2", school_year_start=2025, quarter_tag="Q2")
    template = FormTemplate.objects.create(
        section=section,
        code="form1",
        title="Form 1",
        version="v1",
        period_type="quarter",
        open_at=dt.date.today(),
        close_at=dt.date.today() + dt.timedelta(days=30),
        school_year=2025,
        quarter_filter="Q2",
    )
    submission = Submission.objects.create(school=school, form_template=template, period=period)
    return submission


def _login(client, submission: Submission):
    user = User.objects.create_user(username="slpuser", password="pass123")
    profile = get_profile(user)
    profile.school = submission.school
    profile.save(update_fields=["school", "updated_at"])
    assert client.login(username="slpuser", password="pass123")
    return user


@pytest.mark.django_db
def test_sequential_slp_preserves_first_subject(client):
    submission = _make_submission()
    _login(client, submission)
    url = reverse("edit_submission", args=[submission.id])
    # Initial GET to materialize SLP rows
    client.get(url + "?tab=slp")
    rows = list(Form1SLPRow.objects.filter(submission=submission).order_by("id")[:2])
    assert len(rows) >= 2, "Need at least two SLP rows for test"
    first, second = rows[0], rows[1]

    # Save first subject
    prefix_first = "slp_rows-0"  # ordering assumed by view ensure
    payload_first = {
        "tab": "slp",
        "action": "save_subject",
        "current_subject_id": str(first.id),
        "current_subject_prefix": prefix_first,
        f"{prefix_first}-enrolment": "30",
        f"{prefix_first}-dnme": "5",
        f"{prefix_first}-fs": "5",
        f"{prefix_first}-s": "5",
        f"{prefix_first}-vs": "5",
        f"{prefix_first}-o": "10",
        f"{prefix_first}-is_offered": "on",
        f"{prefix_first}-top_three_llc": "Comp1\nComp2\nComp3",
        f"{prefix_first}-non_mastery_reasons": "R1,R2",
        f"{prefix_first}-non_mastery_other": "Other reason",
        f"{prefix_first}-intervention_plan": json.dumps([
            {"code": "R1", "reason": "Reason 1", "intervention": "Intervention A"},
            {"code": "R2", "reason": "Reason 2", "intervention": "Intervention B"},
        ]),
    }
    resp1 = client.post(url, payload_first)
    assert resp1.status_code in (200, 302)
    first.refresh_from_db()
    preserved_llc = first.top_three_llc
    preserved_plan = first.intervention_plan
    assert preserved_llc.startswith("Comp1"), "First subject LLC not saved"
    assert "Intervention A" in preserved_plan, "First subject interventions not saved"

    # Save second subject with different content
    prefix_second = "slp_rows-1"
    payload_second = {
        "tab": "slp",
        "action": "save_subject",
        "current_subject_id": str(second.id),
        "current_subject_prefix": prefix_second,
        f"{prefix_second}-enrolment": "25",
        f"{prefix_second}-dnme": "5",
        f"{prefix_second}-fs": "5",
        f"{prefix_second}-s": "5",
        f"{prefix_second}-vs": "5",
        f"{prefix_second}-o": "5",
        f"{prefix_second}-is_offered": "on",
        f"{prefix_second}-top_three_llc": "X1\nX2",
        f"{prefix_second}-non_mastery_reasons": "R3",
        f"{prefix_second}-non_mastery_other": "",
        f"{prefix_second}-intervention_plan": json.dumps([
            {"code": "R3", "reason": "Reason 3", "intervention": "Intervention C"},
        ]),
    }
    resp2 = client.post(url, payload_second)
    assert resp2.status_code in (200, 302)

    # Re-fetch first subject and ensure fields unchanged
    first.refresh_from_db()
    assert first.top_three_llc == preserved_llc, "First subject LLC altered after second save"
    assert first.intervention_plan == preserved_plan, "First subject interventions altered after second save"
    # Confirm second subject saved
    second.refresh_from_db()
    assert second.top_three_llc.startswith("X1"), "Second subject LLC not saved"
    assert "Intervention C" in second.intervention_plan, "Second subject intervention not saved"
