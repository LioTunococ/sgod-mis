#!/usr/bin/env python3
"""Reproduce potential is_offered propagation bug.

Scenario:
  1. Create submission with several SLP rows.
  2. Explicitly turn OFF is_offered for first row (simulate unchecked checkbox by omitting field).
  3. Save second row providing its own is_offered=on, but without sending any data for first row.
  4. Verify first row's is_offered remains False (should not be re-defaulted to True).

Exit code 1 if propagation (unexpected change) detected.
"""
import os, sys, time, json
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.append(ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sgod_mis.settings.dev")
import django

django.setup()
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from submissions.models import Submission, FormTemplate, Period, Form1SLPRow, Form1SLPAnalysis
from accounts.roles import get_profile
from submissions import views as submission_views
from organizations.models import School, Section

User = get_user_model()

def make_submission():
    school, _ = School.objects.get_or_create(code="offer-sch", defaults={"name":"Offer School","min_grade":1,"max_grade":6})
    period, _ = Period.objects.get_or_create(label="Q2", school_year_start=2025, quarter_tag="Q2")
    section, _ = Section.objects.get_or_create(code="offer-sec", defaults={"name":"Offer Section"})
    template = FormTemplate.objects.create(
        section=section,
        code=f"offer_form_{int(time.time()*1000)}",
        title="Offer Test Form 1",
        version="v1",
        period_type="quarter",
        open_at=time.strftime("%Y-%m-%d"),
        close_at=time.strftime("%Y-%m-%d"),
        is_active=False,
        school_year=2025,
        quarter_filter="Q2",
    )
    submission = Submission.objects.create(school=school, form_template=template, period=period)
    pairs = submission_views.slp_grade_subject_pairs(school)
    rows = []
    for i, (grade_label, subject_code) in enumerate(pairs[:3]):
        r = Form1SLPRow.objects.create(
            submission=submission,
            grade_label=grade_label,
            subject=subject_code,
            enrolment=40,
            dnme=5, fs=5, s=10, vs=10, o=10,
            is_offered=True,
            top_three_llc=f"LLC {i}",
            intervention_plan=json.dumps([{"code":"p","intervention":f"Plan {i}"}])
        )
        Form1SLPAnalysis.objects.update_or_create(slp_row=r, defaults={'dnme_factors':f'DNME {i}'})
        rows.append(r)
    return submission, rows

def login(submission):
    u = User.objects.create_user(username=f"offer_user_{int(time.time()*1000)}", password="pass123")
    profile = get_profile(u)
    profile.school = submission.school
    profile.save(update_fields=["school","updated_at"])
    c = Client(); c.login(username=u.username, password="pass123")
    return c

def save_subject(client, submission, row, idx, include_is_offered=True, offered_value=True):
    url = reverse("edit_submission", args=[submission.id])
    prefix = f"slp_rows-{idx}"
    payload = {
        'tab':'slp',
        'action':'save_subject',
        'current_subject_prefix':prefix,
        'current_subject_index':str(idx),
        'current_subject_id':str(row.id),
        f'{prefix}-enrolment':'40',
        f'{prefix}-dnme':'5', f'{prefix}-fs':'5', f'{prefix}-s':'10', f'{prefix}-vs':'10', f'{prefix}-o':'10',
        f'{prefix}-top_three_llc': row.top_three_llc,
        f'{prefix}-intervention_plan': row.intervention_plan,
    }
    if include_is_offered:
        if offered_value:
            payload[f'{prefix}-is_offered'] = 'on'
        else:
            # Simulate unchecked (checkbox absent) => do NOT include key at all
            pass
    resp = client.post(url, payload, follow=True)
    return resp.status_code


def main():
    submission, rows = make_submission()
    client = login(submission)
    # First save: turn OFF is_offered for first row by omitting the field
    status1 = save_subject(client, submission, rows[0], 0, include_is_offered=False, offered_value=False)
    rows[0].refresh_from_db()
    print('After first save row0 is_offered=', rows[0].is_offered)
    # Second save: save next row with is_offered ON
    status2 = save_subject(client, submission, rows[1], 1, include_is_offered=True, offered_value=True)
    rows[0].refresh_from_db(); rows[1].refresh_from_db()
    print('After second save row0 is_offered=', rows[0].is_offered, 'row1 is_offered=', rows[1].is_offered)
    # Third save: save third row with is_offered ON
    status3 = save_subject(client, submission, rows[2], 2, include_is_offered=True, offered_value=True)
    rows[0].refresh_from_db(); rows[2].refresh_from_db()
    print('After third save row0 is_offered=', rows[0].is_offered, 'row2 is_offered=', rows[2].is_offered)

    propagation = rows[0].is_offered  # should remain False if not inadvertently re-set
    summary = {
        'submission_id': submission.id,
        'row0_should_be_false': True,
        'row0_is_offered_final': rows[0].is_offered,
        'statuses': [status1, status2, status3]
    }
    print(json.dumps(summary, indent=2))
    if propagation:
        print('UNEXPECTED PROPAGATION: row0 reverted to True')
        sys.exit(1)
    print('No propagation detected (row0 remained False).')
    sys.exit(0)

if __name__ == '__main__':
    main()
