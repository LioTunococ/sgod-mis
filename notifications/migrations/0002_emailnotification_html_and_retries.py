from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="emailnotification",
            name="html_body",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="emailnotification",
            name="last_attempt_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="emailnotification",
            name="retry_count",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
