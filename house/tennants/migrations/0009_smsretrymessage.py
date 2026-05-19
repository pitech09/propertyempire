from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tennants", "0008_landlordprofile_passwordresetcode"),
    ]

    operations = [
        migrations.CreateModel(
            name="SMSRetryMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("to_number", models.CharField(db_index=True, max_length=128)),
                ("message", models.TextField()),
                ("provider", models.CharField(default="textbee", max_length=32)),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed")],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("max_attempts", models.PositiveIntegerField(default=5)),
                ("next_attempt_at", models.DateTimeField(db_index=True)),
                ("last_error", models.TextField(blank=True)),
                ("external_id", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ("next_attempt_at", "created_at"),
            },
        ),
    ]
