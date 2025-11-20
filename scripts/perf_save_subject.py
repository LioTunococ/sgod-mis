#!/usr/bin/env python3
"""Micro benchmark for targeted SLP subject save (action=save_subject).

Creates a submission with many SLP rows then performs repeated POSTs that
save a single subject to exercise the fast-path. Reports avg/median timings.

Run:
  python scripts/perf_save_subject.py
"""
import os, sys, time, statistics, json, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.append(ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sgod_mis.settings.dev")
import django  # noqa: E402

django.setup()

from django.test import Client  # noqa: E402
from django.urls import reverse  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from organizations.models import Section, School  # noqa: E402
from submissions.models import Period, FormTemplate, Submission, Form1SLPRow  # noqa: E402
from accounts.roles import get_profile  # noqa: E402

User = get_user_model()

ROW_COUNT = 120  # simulate large SLP formset
ITERATIONS = 8


def build_submission():
    # Use perf-specific codes; mark template inactive so it never surfaces in UI listings.
    section = Section.objects.create(code=f"perf_slp_{int(time.time()*1000)}", name="(Perf) Temp SLP")
    school, _ = School.objects.get_or_create(code="perf-sch", defaults={"name": "Perf School", "min_grade": 1, "max_grade": 10})
    period, _ = Period.objects.get_or_create(label="Q3", school_year_start=2025, quarter_tag="Q3")
    uniq_code = f"perf_form1_{int(time.time()*1000)}"
    template = FormTemplate.objects.create(
        section=section,
        code=uniq_code,
        title="(Perf) Form 1",
        version="v1",
        period_type="quarter",
        open_at=dt.date.today(),
        close_at=dt.date.today() + dt.timedelta(days=30),
        is_active=False,
        school_year=2025,
        quarter_filter="Q3",
    )
    submission = Submission.objects.create(school=school, form_template=template, period=period)
    # Create many SLP rows (offered) with neutral values
    for i in range(ROW_COUNT):
        Form1SLPRow.objects.create(
            submission=submission,
            grade_label=f"Grade {1 + (i % 10)}",
            subject=f"subj_{i}",
            enrolment=30,
            dnme=5,
            fs=5,
            s=5,
            vs=5,
            o=10,
            top_three_llc="1. competency A\n2. competency B",
            non_mastery_reasons="a",
            intervention_plan=json.dumps([{"code": "a", "intervention": "Drill"}]),
        )
    return submission


def login_client(submission):
    uname = f"perf_user_{int(time.time()*1000)}"
    user = User.objects.create_user(username=uname, password="pass123")
    profile = get_profile(user)
    profile.school = submission.school
    profile.save(update_fields=["school", "updated_at"])
    c = Client()
    assert c.login(username="perf_user", password="pass123")
    return c


def benchmark(submission):
    c = login_client(submission)
    url = reverse("edit_submission", args=[submission.id])
    # Choose target row id & prefix (row 0)
    first_row = Form1SLPRow.objects.filter(submission=submission).order_by("id").first()
    target_prefix = "slp_rows-0"
    target_id = first_row.id if first_row else None
    times = []
    for n in range(ITERATIONS):
        payload = {
            "tab": "slp",
            "action": "save_subject",
            "current_subject_prefix": target_prefix,
            "current_subject_index": "0",
            "current_subject_id": str(target_id) if target_id else "",
            # Minimal fields for targeted subject (fast path should avoid others)
            f"{target_prefix}-enrolment": "30",
            f"{target_prefix}-dnme": "5",
            f"{target_prefix}-fs": "5",
            f"{target_prefix}-s": "5",
            f"{target_prefix}-vs": "5",
            f"{target_prefix}-o": "10",
            f"{target_prefix}-top_three_llc": "1. competency A\n2. competency B",
            f"{target_prefix}-non_mastery_reasons": "a",
            f"{target_prefix}-non_mastery_other": "",
            f"{target_prefix}-intervention_plan": json.dumps([{"code": "a", "intervention": "Updated Drill"}]),
        }
        t0 = time.perf_counter()
        resp = c.post(url, payload, follow=True)
        dt_ms = (time.perf_counter() - t0) * 1000
        times.append(dt_ms)
        assert resp.status_code in (200, 302)
    print("SLP save_subject timings (ms):", ", ".join(f"{t:.1f}" for t in times))
    print(f"avg={statistics.mean(times):.1f} ms median={statistics.median(times):.1f} ms max={max(times):.1f} ms")
    # Cleanup to avoid polluting UI
    submission.delete()  # cascades rows
    template = submission.form_template
    section = template.section
    # Delete template & section if no other submissions reference them
    if not Submission.objects.filter(form_template=template).exists():
        template.delete()
    if not Submission.objects.filter(form_template__section=section).exists():
        section.delete()


if __name__ == "__main__":
    submission = build_submission()
    benchmark(submission)
