from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("tickets", "0002_ticketcomment"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="ticket",
            options={"ordering": ["-updated_at", "-created_at"]},
        ),
        migrations.AddIndex(
            model_name="ticket",
            index=models.Index(fields=["status", "priority"], name="hdp_t_status_prio_idx"),
        ),
        migrations.AddIndex(
            model_name="ticket",
            index=models.Index(fields=["created_by", "-created_at"], name="hdp_t_creator_date_idx"),
        ),
        migrations.AddIndex(
            model_name="ticket",
            index=models.Index(fields=["assigned_to", "status"], name="hdp_t_assignee_status_idx"),
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("message", models.CharField(max_length=240)),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="helpdesk_notifications", to=settings.AUTH_USER_MODEL)),
                ("ticket", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="tickets.ticket")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["recipient", "is_read", "-created_at"], name="hdp_n_recipient_read_idx"),
        ),
    ]
