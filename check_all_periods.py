#!/usr/bin/env python
"""
Check all Period records in the database
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgod_mis.settings.dev')
django.setup()

from submissions.models import Period

print("=" * 70)
print("ALL PERIOD RECORDS IN DATABASE")
print("=" * 70)

periods = Period.objects.all().order_by('school_year_start', 'display_order')

print(f"\nTotal periods: {periods.count()}\n")

for period in periods:
    active_status = "✅ ACTIVE" if period.is_active else "❌ inactive"
    print(f"ID {period.id:2d} | {active_status} | quarter_tag: {period.quarter_tag:4s} | label: {period.label}")

print("\n" + "=" * 70)
print("ISSUE FOUND:")
print("=" * 70)
print("Both active periods have quarter_tag='Q1'")
print("This causes the chart to show 'Q1-Q1' instead of 'Q1', 'Q2', 'Q3', 'Q4'")
print("\n✅ SOLUTION: Update Period records with correct quarter_tags")
