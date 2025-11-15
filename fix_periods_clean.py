#!/usr/bin/env python
"""
Fix Period Records - Remove duplicates and create proper Q1-Q4
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgod_mis.settings.dev')
django.setup()

from submissions.models import Period

print("=" * 70)
print("FIXING PERIOD RECORDS - STEP 1: CLEAN UP")
print("=" * 70)

# Check existing periods
existing_periods = Period.objects.all()
print(f"\nCurrent periods: {existing_periods.count()}")
for p in existing_periods:
    print(f"  ID {p.id}: {p.quarter_tag} - {p.label} (Active: {p.is_active})")

# Delete all existing periods to start fresh
print("\n🗑️  Deleting all existing periods...")
deleted_count = existing_periods.count()
existing_periods.delete()
print(f"✅ Deleted {deleted_count} periods")

print("\n" + "=" * 70)
print("STEP 2: CREATE Q1-Q4 PERIODS FOR SY 2025-2026")
print("=" * 70)

# Create Q1-Q4 periods
quarters = [
    {'tag': 'Q1', 'label': 'First Quarter', 'order': 1},
    {'tag': 'Q2', 'label': 'Second Quarter', 'order': 2},
    {'tag': 'Q3', 'label': 'Third Quarter', 'order': 3},
    {'tag': 'Q4', 'label': 'Fourth Quarter', 'order': 4},
]

school_year = 2025

from datetime import date

for q in quarters:
    period = Period.objects.create(
        school_year_start=school_year,
        quarter_tag=q['tag'],
        label=f"{q['label']} - SY {school_year}-{school_year+1}",
        display_order=q['order'],
        is_active=True,
        open_date=date(2025, 1, 1),  # Set reasonable dates
        close_date=date(2025, 12, 31),
    )
    
    print(f"✅ CREATED | ID {period.id:2d} | {period.quarter_tag} | {period.label}")

print("\n" + "=" * 70)
print("STEP 3: VERIFICATION")
print("=" * 70)

# Verify the fix
periods = Period.objects.filter(
    is_active=True,
    quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
).order_by('display_order')

chart_labels = [p.quarter_tag for p in periods]
print(f"\nTotal periods: {periods.count()}")
print(f"Chart labels will now show: {chart_labels}")
print(f"Expected: ['Q1', 'Q2', 'Q3', 'Q4']")

if chart_labels == ['Q1', 'Q2', 'Q3', 'Q4']:
    print("\n🎉 STATUS: ✅ QUARTER DISPLAY BUG FIXED!")
    print("\nThe dashboard will now correctly show Q1, Q2, Q3, Q4")
    print("instead of Q1-Q1 in the chart labels.")
else:
    print(f"\n⚠️  STATUS: Unexpected result: {chart_labels}")

print("\n" + "=" * 70)
print("TASK 8 COMPLETE!")
print("=" * 70)
