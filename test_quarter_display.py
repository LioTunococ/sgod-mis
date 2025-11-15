#!/usr/bin/env python
"""
Test quarter display in Period model.

This is a standalone script intended to be run manually, not as a pytest test.
It is now safe to import without triggering database access.
"""
import os
import sys


def main() -> None:
    import django

    # Ensure project is on path and Django is configured
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgod_mis.settings.dev')
    django.setup()

    from submissions.models import Period

    print("=" * 60)
    print("QUARTER DISPLAY TEST")
    print("=" * 60)

    periods = (
        Period.objects.filter(
            is_active=True,
            quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
        )
        .order_by('display_order')[:4]
    )

    print(f"\nFound {periods.count()} active quarters:\n")

    for period in periods:
        print(f"Period ID: {period.id}")
        print(f"  label: \"{period.label}\"")
        print(f"  quarter_tag: \"{period.quarter_tag}\"")
        print(f"  Chart Display: \"{period.quarter_tag or period.label}\"")
        print()

    # Check what the chart_data would show
    print("=" * 60)
    print("CHART LABELS (What Chart.js will show):")
    print("=" * 60)

    chart_labels = [p.quarter_tag or p.label for p in periods]
    print(chart_labels)

    print("\n✅ Expected: ['Q1', 'Q2', 'Q3', 'Q4']")
    print(f"✅ Actual:   {chart_labels}")

    if chart_labels == ['Q1', 'Q2', 'Q3', 'Q4']:
        print("\n🎉 STATUS: ✅ QUARTERS DISPLAYING CORRECTLY!")
    else:
        print("\n⚠️  STATUS: ❌ QUARTERS NOT DISPLAYING AS EXPECTED")
        print("   This means the bug still exists.")


if __name__ == '__main__':
    main()
