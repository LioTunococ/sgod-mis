from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0002_district_school_implements_adm_school_max_grade_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="school",
            name="district",
        ),
        migrations.RenameField(
            model_name="school",
            old_name="district_fk",
            new_name="district",
        ),
    ]
