from datetime import timedelta
from django.db import migrations, models
from django.utils import timezone


def populate_deadlines(apps, schema_editor):
    Ticket = apps.get_model("tickets", "Ticket")
    hours = {"urgent": 4, "high": 24, "medium": 72, "low": 120}
    for ticket in Ticket.objects.filter(due_at__isnull=True).iterator():
        ticket.due_at = ticket.created_at + timedelta(hours=hours.get(ticket.priority, 72))
        ticket.save(update_fields=["due_at"])


class Migration(migrations.Migration):
    dependencies = [("tickets", "0004_ticketauditlog")]
    operations = [
        migrations.AddField(
            model_name="ticket",
            name="due_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.RunPython(populate_deadlines, migrations.RunPython.noop),
    ]
