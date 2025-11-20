#!/usr/bin/env python3
"""Test adding a new project via dynamic formset POST.
Ensures server processes newly added project row fields on save_draft.
"""
import os, sys, datetime as dt
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
from submissions.models import Period, FormTemplate, Submission, SMEAProject  # noqa: E402
from accounts.roles import get_profile  # noqa: E402

User = get_user_model()


def _make_submission():
    section = Section.objects.create(code="proj", name="Projects Section")
    school = School.objects.create(code="sch-proj", name="Proj School", min_grade=1, max_grade=10)
    period = Period.objects.create(label="Q1", school_year_start=2025, quarter_tag="Q1")
    template = FormTemplate.objects.create(
        section=section,
        code="form1",
        title="Form 1",
        version="v1",
        period_type="quarter",
        open_at=dt.date.today(),
        close_at=dt.date.today() + dt.timedelta(days=30),
        school_year=2025,
        quarter_filter="Q1",
    )
    submission = Submission.objects.create(school=school, form_template=template, period=period)
    return submission


def _login(client, submission: Submission):
    user = User.objects.create_user(username="projuser", password="pass123")
    profile = get_profile(user)
    profile.school = submission.school
    profile.save(update_fields=["school", "updated_at"])
    assert client.login(username="projuser", password="pass123")
    return user


@pytest.mark.django_db
def test_dynamic_project_add(client):
    submission = _make_submission()
    _login(client, submission)
    url = reverse("edit_submission", args=[submission.id])
    # Initial GET to render formset
    client.get(url + "?tab=projects")
    # POST new project (index 0) using management form values
    payload = {
        "tab": "projects",
        "action": "save_draft",
        "projects-TOTAL_FORMS": "1",
        "projects-INITIAL_FORMS": "0",
        "projects-MIN_NUM_FORMS": "0",
        "projects-MAX_NUM_FORMS": "1000",
        "projects-0-id": "",
        "projects-0-project_title": "Literacy Improvement",
        "projects-0-area_of_concern": "Quality",
        "projects-0-conference_date": "2025-07-01",
    }
    resp = client.post(url, payload, follow=True)
    assert resp.status_code in (200, 302)
    projects = list(SMEAProject.objects.filter(submission=submission))
    assert len(projects) == 1, "Project not created from dynamic POST"
    assert projects[0].project_title == "Literacy Improvement"
