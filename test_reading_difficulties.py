import json

import pytest
from django.utils import timezone

from submissions.models import FormTemplate, Period, Submission, ReadingDifficultyPlan
from organizations.models import School, Section
from submissions.views import _reading_period_for_submission, update_reading_difficulty_plans, ensure_reading_difficulty_plans


@pytest.mark.django_db
def test_reading_period_override_precedence():
    section = Section.objects.create(code='sec', name='Section')
    period = Period.objects.create(label='Q1', school_year_start=2025, quarter_tag='Q1', display_order=1, is_active=True)
    # Quarter Q1 would normally map to EOSY; override should force BOSY
    ft = FormTemplate.objects.create(
        section=section,
        code='ft1',
        title='Template',
        period_type='quarter',
        open_at=timezone.now().date(),
        close_at=timezone.now().date(),
        reading_timing_override='bosy'
    )
    school = School.objects.create(code='sch', name='School', min_grade=4, max_grade=5)
    submission = Submission.objects.create(school=school, form_template=ft, period=period)
    period_resolved = _reading_period_for_submission(submission)
    assert period_resolved == 'bosy'


@pytest.mark.django_db
def test_reading_difficulties_sync_model_rows():
    section = Section.objects.create(code='sec2', name='Section 2')
    period = Period.objects.create(label='Q2', school_year_start=2025, quarter_tag='Q2', display_order=2, is_active=True)
    ft = FormTemplate.objects.create(
        section=section,
        code='ft2',
        title='Template 2',
        period_type='quarter',
        open_at=timezone.now().date(),
        close_at=timezone.now().date(),
    )
    school = School.objects.create(code='sch2', name='School 2', min_grade=4, max_grade=4)
    submission = Submission.objects.create(school=school, form_template=ft, period=period)
    # Ensure base rows exist for derived period (Q2->BOSY)
    derived_period = _reading_period_for_submission(submission)
    ensure_reading_difficulty_plans(submission, derived_period, [4])
    raw = [
        {
            'grade': '4',
            'pairs': [
                {'difficulty': 'Low decoding accuracy', 'intervention': 'Daily guided reading'},
                {'difficulty': 'Limited vocabulary', 'intervention': 'Vocabulary station work'},
            ]
        }
    ]
    # Persist raw JSON to submission (simulating view behavior)
    data = dict(submission.data or {})
    data['reading_difficulties_json'] = raw
    submission.data = data
    submission.save(update_fields=['data'])
    # Sync
    update_reading_difficulty_plans(submission, derived_period, raw)
    plan = ReadingDifficultyPlan.objects.get(submission=submission, period=derived_period, grade_label='g4')
    assert len(plan.data) == 2
    assert plan.data[0]['difficulty'].startswith('Low decoding')
    assert plan.data[1]['intervention'].startswith('Vocabulary')