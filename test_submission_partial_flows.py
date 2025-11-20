#!/usr/bin/env python3
"""Tests for partial save flows (RMA JSON + ADM dynamic rows + readiness summary).

These are light integration tests exercising the `edit_submission` view with
minimal POST payloads to confirm that:
1. RMA structured JSON persists even when other RMA formsets may be invalid.
2. ADM dynamic row data posts correctly for the last (new) row.

They intentionally avoid exhaustive validation logic – coverage focuses on
recent regression‑prone areas (lost last ADM row, missing RMA JSON persistence).
"""

import os
import sys
import json
import datetime as dt

import django
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

# Django setup (mirrors existing test files)
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.append(project_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sgod_mis.settings.dev")
django.setup()

from organizations.models import Section, School  # noqa: E402
from submissions.models import Period, FormTemplate, Submission, Form1ADMRow  # noqa: E402
from accounts.roles import get_profile  # noqa: E402

User = get_user_model()


def _make_submission(quarter_tag: str = "Q3") -> Submission:
    """Factory helper: create minimal objects for a test submission."""
    section = Section.objects.create(code="slp", name="SLP Section")
    school = School.objects.create(code="sch-1", name="Test School", min_grade=1, max_grade=10)
    period = Period.objects.create(label=quarter_tag, school_year_start=2025, quarter_tag=quarter_tag)
    template = FormTemplate.objects.create(
        section=section,
        code="form1",
        title="Form 1",
        version="v1",
        period_type="quarter",
        open_at=dt.date.today(),
        close_at=dt.date.today() + dt.timedelta(days=30),
        school_year=2025,
        quarter_filter=quarter_tag,
    )
    submission = Submission.objects.create(school=school, form_template=template, period=period)
    return submission


def _login_school_head(client, submission: Submission) -> User:
    """Create & login a user assigned to the submission school (school head)."""
    user = User.objects.create_user(username="head", password="pass123")
    profile = get_profile(user)
    profile.school = submission.school
    profile.save(update_fields=["school", "updated_at"])
    assert client.login(username="head", password="pass123"), "Login failed"
    return user


@pytest.mark.django_db
def test_rma_partial_json_persists(client):
    submission = _make_submission(quarter_tag="Q3")  # Q3 exposes Pre-Test block
    _login_school_head(client, submission)

    url = reverse("edit_submission", args=[submission.id])
    sample_json = [
        {"grade": 1, "pairs": [{"difficulty": "Basic facts", "intervention": "Daily drill"}]},
        {"grade": 2, "pairs": []},
    ]
    payload = {
        "tab": "rma",
        "action": "save_draft",
        # Minimal management form fields for RMA rows (avoid full form population)
        "rma_rows-TOTAL_FORMS": "0",
        "rma_rows-INITIAL_FORMS": "0",
        "rma_rows-MIN_NUM_FORMS": "0",
        "rma_rows-MAX_NUM_FORMS": "1000",
        # Interventions formset mgmt (empty)
        "rma_interventions-TOTAL_FORMS": "0",
        "rma_interventions-INITIAL_FORMS": "0",
        "rma_interventions-MIN_NUM_FORMS": "0",
        "rma_interventions-MAX_NUM_FORMS": "1000",
        # Structured JSON hidden field
        "rma_pretest_json": json.dumps(sample_json),
    }
    resp = client.post(url, payload, follow=True)
    assert resp.status_code in (200, 302)
    submission.refresh_from_db()
    assert submission.data.get("rma_pretest_json") == sample_json, "RMA JSON not persisted on partial save"


@pytest.mark.django_db
def test_adm_last_row_save(client):
    submission = _make_submission(quarter_tag="Q1")  # Quarter doesn't affect ADM
    _login_school_head(client, submission)

    url = reverse("edit_submission", args=[submission.id])
    # Provide header offered flag and a single ADM row (index 0)
    payload = {
        "tab": "adm",
        "action": "save_draft",
        "adm_header-is_offered": "on",
        # Mgmt form
        "adm_rows-TOTAL_FORMS": "1",
        "adm_rows-INITIAL_FORMS": "0",
        "adm_rows-MIN_NUM_FORMS": "0",
        "adm_rows-MAX_NUM_FORMS": "1000",
        # Row fields (prefix adm_rows-0-*)
        "adm_rows-0-id": "",
        "adm_rows-0-ppas_conducted": "Storm damage to classrooms",
        "adm_rows-0-ppas_physical_target": "5",
        "adm_rows-0-ppas_physical_actual": "3",
        "adm_rows-0-ppas_physical_percent": "60",
        "adm_rows-0-funds_downloaded": "1000.00",
        "adm_rows-0-funds_obligated": "600.00",
        "adm_rows-0-funds_unobligated": "400.00",
        "adm_rows-0-funds_percent_obligated": "60",
        "adm_rows-0-funds_percent_burn_rate": "10",
        "adm_rows-0-q1_response": "Rapid coordination enabled quick setup",
        "adm_rows-0-q2_response": "Partially addresses continuity",
        "adm_rows-0-q3_response": "Expand blended modules",
        "adm_rows-0-q4_response": "Improve tracking",
        "adm_rows-0-q5_response": "Ensures learners keep pace",
    }
    resp = client.post(url, payload, follow=True)
    assert resp.status_code in (200, 302)
    # Row should be created
    rows = list(Form1ADMRow.objects.filter(submission=submission))
    assert len(rows) == 1, "ADM row not saved"
    row = rows[0]
    assert row.ppas_conducted.startswith("Storm"), "Field values not persisted for last row"
    assert row.q1_response, "Narrative field missing"
