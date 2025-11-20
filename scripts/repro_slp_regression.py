#!/usr/bin/env python3
"""Enhanced SLP regression reproduction & verification.

Objective:
    Sequentially save multiple SLP subjects via the fast-path (action=save_subject)
    and assert that previously saved subjects retain narrative & proficiency fields.

Features:
    - Builds a submission using canonical grade/subject pairs from view logic.
    - Iterates through first N subjects, mutating only the target subject per save.
    - Captures snapshots before each save and diff-checks all other rows afterward.
    - Emits a concise JSON summary of any unexpected cross-row modifications.

Usage:
    python scripts/repro_slp_regression.py [submission_id] [limit]
        submission_id (optional): existing submission to reuse; if absent a new one is created.
        limit (optional int): number of subjects to exercise (default 5).

Exit code:
    0 if no unintended modifications detected; 1 otherwise.
"""
import os, sys, json, traceback
import time
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.append(ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sgod_mis.settings.dev")
import django

django.setup()
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from organizations.models import School, Section
from submissions.models import Period, FormTemplate, Submission, Form1SLPRow, Form1SLPAnalysis
from submissions import views as submission_views
from accounts.roles import get_profile

User = get_user_model()

def create_submission_with_pairs():
    school, _ = School.objects.get_or_create(code="reg-sch", defaults={"name":"Reg School","min_grade":1,"max_grade":6})
    period, _ = Period.objects.get_or_create(label="Q2", school_year_start=2025, quarter_tag="Q2")
    section, _ = Section.objects.get_or_create(code="reg-sec", defaults={"name":"Reg Section"})
    template = FormTemplate.objects.create(
        section=section,
        code=f"reg_form_{int(time.time()*1000)}",
        title="Regression Form 1",
        version="v1",
        period_type="quarter",
        open_at=time.strftime("%Y-%m-%d"),
        close_at=time.strftime("%Y-%m-%d"),
        is_active=False,
        school_year=2025,
        quarter_filter="Q2",
    )
    submission = Submission.objects.create(school=school, form_template=template, period=period)
    # Use canonical pairs from view helper
    pairs = submission_views.slp_grade_subject_pairs(school)
    created_rows = []
    base_enrol = 40
    for i, (grade_label, subject_code) in enumerate(pairs):
        r = Form1SLPRow.objects.create(
            submission=submission,
            grade_label=grade_label,
            subject=subject_code,
            enrolment=base_enrol,
            dnme=5, fs=5, s=10, vs=10, o=10,
            top_three_llc=f"Initial LLC {i}",
            intervention_plan=json.dumps([{"code":"ap","intervention":f"Plan {i}"}]),
            non_mastery_reasons="R1,R2",
            non_mastery_other="",
        )
        Form1SLPAnalysis.objects.update_or_create(
            slp_row=r,
            defaults={
                'dnme_factors': f'DNME factors {i}',
                'fs_factors': f'FS factors {i}',
                's_practices': f'S practices {i}',
                'vs_practices': f'VS practices {i}',
                'o_practices': f'O practices {i}',
                'overall_strategy': f'Strategy {i}',
            }
        )
        created_rows.append(r)
    return submission, created_rows

def login(submission):
    u = User.objects.create_user(username=f"reg_user_{int(time.time()*1000)}", password="pass123")
    p = get_profile(u); p.school = submission.school; p.save(update_fields=["school","updated_at"])
    c = Client(); assert c.login(username=u.username, password="pass123")
    return c

def save_subject(client, submission, row, idx, mutate=False):
    url = reverse("edit_submission", args=[submission.id])
    prefix = f"slp_rows-{idx}"
    top_llc = row.top_three_llc
    plan_val = row.intervention_plan
    if mutate:
        top_llc = f"Mutated LLC {idx}"
        plan_val = json.dumps([{"code":"x","intervention":f"Mutated Plan {idx}"}])
    payload = {
        "tab":"slp",
        "action":"save_subject",
        "current_subject_prefix":prefix,
        "current_subject_index":str(idx),
        "current_subject_id":str(row.id),
        f"{prefix}-enrolment":"30",
        f"{prefix}-dnme":"5",
        f"{prefix}-fs":"5",
        f"{prefix}-s":"5",
        f"{prefix}-vs":"5",
        f"{prefix}-o":"10",
        f"{prefix}-top_three_llc": top_llc,
        f"{prefix}-intervention_plan": plan_val,
        f"{prefix}-non_mastery_reasons":"a",
        f"{prefix}-non_mastery_other":"",
    }
    resp = client.post(url, payload, follow=True)
    return resp.status_code

def diff_row(pre, post, exclude=None):
    exclude = set(exclude or [])
    diffs = {}
    for k, v in pre.items():
        if k in exclude:
            continue
        if post.get(k) != v:
            diffs[k] = (v, post.get(k))
    return diffs

def snapshot_rows(submission):
    rows = Form1SLPRow.objects.filter(submission=submission).order_by('id')
    snap = {}
    for r in rows:
        snap[r.id] = {
            'id': r.id,
            'grade_label': r.grade_label,
            'subject': r.subject,
            'enrolment': r.enrolment,
            'top_three_llc': r.top_three_llc,
            'intervention_plan': r.intervention_plan,
            'non_mastery_reasons': r.non_mastery_reasons,
            'non_mastery_other': r.non_mastery_other,
            'dnme': r.dnme,'fs': r.fs,'s': r.s,'vs': r.vs,'o': r.o,
        }
    return snap

def main():
    submission_id = None
    limit = 5
    if len(sys.argv) > 1:
        try:
            submission_id = int(sys.argv[1])
        except Exception:
            submission_id = None
    if len(sys.argv) > 2:
        try:
            limit = int(sys.argv[2])
        except Exception:
            pass
    if submission_id:
        submission = Submission.objects.get(pk=submission_id)
        rows = list(Form1SLPRow.objects.filter(submission=submission).order_by('id'))
    else:
        submission, rows = create_submission_with_pairs()
    client = login(submission)
    rows = rows[:limit]
    anomalies = []
    for idx, row in enumerate(rows):
        pre_snap = snapshot_rows(submission)
        status = save_subject(client, submission, row, idx, mutate=True)
        post_snap = snapshot_rows(submission)
        # Analyze unintended diffs in rows other than target
        for other_id, pre_row in pre_snap.items():
            if other_id == row.id:
                continue
            diffs = diff_row(pre_row, post_snap.get(other_id, {}), exclude={'id'})
            if diffs:
                anomalies.append({'target_idx': idx, 'target_row': row.id, 'affected_row': other_id, 'diffs': diffs})
        print(f"Saved subject idx={idx} row_id={row.id} status={status}")
    summary = {
        'submission_id': submission.id,
        'tested_rows': [r.id for r in rows],
        'anomaly_count': len(anomalies),
        'anomalies': anomalies,
    }
    print(json.dumps(summary, indent=2))
    if anomalies:
        print("UNINTENDED MODIFICATIONS DETECTED")
        sys.exit(1)
    print("No unintended cross-row modifications detected")
    sys.exit(0)

if __name__ == "__main__":
    main()
