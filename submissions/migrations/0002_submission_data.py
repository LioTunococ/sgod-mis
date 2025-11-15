from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="data",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
