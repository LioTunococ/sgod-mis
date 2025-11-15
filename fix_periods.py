#!/usr/bin/env python
"""
Fix Period Records - Create Q1, Q2, Q3, Q4 for School Year 2025-2026
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgod_mis.settings.dev')
django.setup()

from submissions.models import Period

print("=" * 70)
print("FIXING PERIOD RECORDS")
print("=" * 70)

# Check existing periods
existing_periods = Period.objects.all()
print(f"\nCurrent periods: {existing_periods.count()}")
for p in existing_periods:
    print(f"  ID {p.id}: {p.quarter_tag} - {p.label}")

# Ask for confirmation
print("\n" + "=" * 70)
print("ACTION: Will create/update Q1-Q4 periods for SY 2025-2026")
print("=" * 70)

# Create or update Q1-Q4 periods
quarters = [
    {'tag': 'Q1', 'label': 'First Quarter', 'order': 1},
    {'tag': 'Q2', 'label': 'Second Quarter', 'order': 2},
    {'tag': 'Q3', 'label': 'Third Quarter', 'order': 3},
    {'tag': 'Q4', 'label': 'Fourth Quarter', 'order': 4},
]

school_year = 2025

for q in quarters:
    period, created = Period.objects.update_or_create(
        school_year_start=school_year,
        quarter_tag=q['tag'],
        defaults={
            'label': f"{q['label']} - SY {school_year}-{school_year+1}",
            'display_order': q['order'],
            'is_active': True,
            'is_open': True,
        }
    )
    
    status = "✅ CREATED" if created else "♻️  UPDATED"
    print(f"{status} | ID {period.id:2d} | {period.quarter_tag} | {period.label}")

print("\n" + "=" * 70)
print("VERIFICATION")
print("=" * 70)

# Verify the fix
periods = Period.objects.filter(
    is_active=True,
    quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
).order_by('display_order')

chart_labels = [p.quarter_tag for p in periods]
print(f"\nChart labels will now show: {chart_labels}")
print(f"Expected: ['Q1', 'Q2', 'Q3', 'Q4']")

if chart_labels == ['Q1', 'Q2', 'Q3', 'Q4']:
    print("\n🎉 STATUS: ✅ QUARTER DISPLAY BUG FIXED!")
else:
    print(f"\n⚠️  STATUS: Unexpected result: {chart_labels}")

print("\n" + "=" * 70)
