from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models

DISTRICTS = [
    ("flora", "Flora"),
    ("sta-marcela", "Sta. Marcela"),
    ("luna", "Luna"),
    ("pudtol", "Pudtol"),
    ("kabugao-1", "Kabugao 1"),
    ("kabugao-2", "Kabugao 2"),
    ("northern-conner", "Northern Conner"),
    ("southern-conner", "Southern Conner"),
    ("upper-calanasan", "Upper Calanasan"),
    ("lower-calanasan", "Lower Calanasan"),
]

# Best-effort mapping from legacy district labels to the new canonical list.
DISTRICT_MAP = {
    "Apayao District 1": "flora",
    "Apayao District 2": "sta-marcela",
    "Apayao District 3": "upper-calanasan",
    "Apayao District 4": "southern-conner",
}


def seed_districts_and_map_schools(apps, schema_editor):
    District = apps.get_model("organizations", "District")
    School = apps.get_model("organizations", "School")

    slug_to_district = {}
    for code, name in DISTRICTS:
        district, _ = District.objects.get_or_create(code=code, defaults={"name": name})
        slug_to_district[code] = district

    for school in School.objects.all():
        slug = DISTRICT_MAP.get(school.district)
        if not slug:
            continue
        district = slug_to_district.get(slug)
        if district:
            school.district_fk = district
            school.save(update_fields=["district_fk"])


def reverse_noop(apps, schema_editor):  # pragma: no cover - required for reversible migration
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="District",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=64, unique=True)),
                ("name", models.CharField(max_length=255)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="school",
            name="district_fk",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="schools", to="organizations.district"),
        ),
        migrations.AddField(
            model_name="school",
            name="implements_adm",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="school",
            name="max_grade",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="school",
            name="min_grade",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(seed_districts_and_map_schools, reverse_noop),
    ]
