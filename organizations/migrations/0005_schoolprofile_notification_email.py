from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0004_schoolprofile"),
    ]

    operations = [
        migrations.AddField(
            model_name="schoolprofile",
            name="notification_email",
            field=models.EmailField(blank=True, max_length=254),
        ),
    ]
