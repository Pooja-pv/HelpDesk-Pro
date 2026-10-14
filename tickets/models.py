from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta


class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        WAITING = "waiting", "Waiting for employee"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    title = models.CharField(max_length=180)
    description = models.TextField()
    category = models.CharField(max_length=80, default="General")
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="helpdesk_tickets")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_helpdesk_tickets")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "priority"], name="hdp_t_status_prio_idx"),
            models.Index(fields=["created_by", "-created_at"], name="hdp_t_creator_date_idx"),
            models.Index(fields=["assigned_to", "status"], name="hdp_t_assignee_status_idx"),
        ]

    SLA_HOURS = {"urgent": 4, "high": 24, "medium": 72, "low": 120}

    def save(self, *args, **kwargs):
        if self.due_at is None and self._state.adding:
            self.due_at = timezone.now() + timedelta(hours=self.SLA_HOURS.get(self.priority, 72))
        super().save(*args, **kwargs)

    @property
    def sla_deadline(self):
        if self.due_at:
            return self.due_at
        return self.created_at + timedelta(hours=self.SLA_HOURS.get(self.priority, 72))

    @property
    def is_overdue(self):
        return self.status not in {self.Status.RESOLVED, self.Status.CLOSED} and self.sla_deadline < timezone.now()

    def __str__(self):
        return f"HD-{self.pk or 'NEW'}: {self.title}"


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="helpdesk_comments")
    message = models.TextField(max_length=3000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment on HD-{self.ticket_id} by {self.author}"


class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="helpdesk_notifications")
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=240)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read", "-created_at"], name="hdp_n_recipient_read_idx")]

    def __str__(self):
        return f"Notification for {self.recipient}: {self.message}"


class TicketAuditLog(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="audit_events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="helpdesk_audit_events")
    action = models.CharField(max_length=80)
    details = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["ticket", "-created_at"], name="hdp_audit_ticket_date_idx")]

    def __str__(self):
        return f"HD-{self.ticket_id}: {self.action}"
