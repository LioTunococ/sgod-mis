from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0003_swap_school_district_fk"),
    ]

    operations = [
        migrations.CreateModel(
            name="SchoolProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("head_name", models.CharField(blank=True, max_length=255)),
                ("head_contact", models.CharField(blank=True, max_length=255)),
                (
                    "grade_span_start",
                    models.PositiveSmallIntegerField(blank=True, null=True),
                ),
                (
                    "grade_span_end",
                    models.PositiveSmallIntegerField(blank=True, null=True),
                ),
                ("strands", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "school",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to="organizations.school",
                    ),
                ),
            ],
            options={
                "ordering": ["school__name"],
            },
        ),
    ]
