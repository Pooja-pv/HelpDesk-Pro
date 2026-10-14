from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Notification, Ticket

User = get_user_model()


class TicketAccessTests(TestCase):
    def setUp(self):
        self.employee = User.objects.create_user(username="employee", password="Test-password-789")
        self.other_employee = User.objects.create_user(username="other", password="Test-password-789")
        self.support = User.objects.create_user(username="support", password="Test-password-789", is_staff=True)
        self.ticket = Ticket.objects.create(
            title="Email access issue",
            description="Cannot access work email.",
            category="IT",
            created_by=self.employee,
        )

    def test_employee_can_view_own_ticket(self):
        self.client.login(username="employee", password="Test-password-789")
        response = self.client.get(reverse("tickets:detail", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 200)

    def test_employee_cannot_view_another_employees_ticket(self):
        self.client.login(username="other", password="Test-password-789")
        response = self.client.get(reverse("tickets:detail", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 403)

    def test_support_can_view_and_update_ticket(self):
        self.client.login(username="support", password="Test-password-789")
        response = self.client.post(reverse("tickets:update", args=[self.ticket.pk]), {
            "status": Ticket.Status.IN_PROGRESS,
            "priority": Ticket.Priority.HIGH,
            "assigned_to": self.support.pk,
        })
        self.assertRedirects(response, reverse("tickets:detail", args=[self.ticket.pk]))
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.IN_PROGRESS)
        self.assertTrue(Notification.objects.filter(recipient=self.employee, ticket=self.ticket).exists())

    def test_employee_ticket_creation_notifies_support(self):
        self.client.login(username="employee", password="Test-password-789")
        response = self.client.post(reverse("tickets:create"), {
            "title": "VPN access",
            "description": "VPN connection fails after sign in.",
            "category": "IT",
            "priority": Ticket.Priority.MEDIUM,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Notification.objects.filter(recipient=self.support, message__contains="New ticket").exists())

    def test_employee_cannot_open_another_users_notification(self):
        notification = Notification.objects.create(recipient=self.employee, ticket=self.ticket, message="Ticket updated")
        self.client.login(username="other", password="Test-password-789")
        response = self.client.post(reverse("tickets:notification-open", args=[notification.pk]))
        self.assertEqual(response.status_code, 404)


class TicketAuditAndExportTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="supportadmin", password="StrongPass123!", is_staff=True)
        self.employee = User.objects.create_user(username="requester", password="StrongPass123!")

    def test_ticket_creation_records_audit_event(self):
        self.client.force_login(self.employee)
        response = self.client.post(reverse("tickets:create"), {"title": "VPN access", "description": "Unable to connect to company VPN.", "category": "IT Support", "priority": "high"})
        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get(title="VPN access")
        self.assertTrue(ticket.audit_events.filter(action="Ticket created", actor=self.employee).exists())

    def test_staff_can_export_csv(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("tickets:export-csv"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])


class ServiceLevelTests(TestCase):
    def setUp(self):
        self.employee = User.objects.create_user(username="slaemployee", password="Test-password-789")

    def test_new_ticket_receives_priority_based_sla_deadline(self):
        ticket = Ticket.objects.create(
            title="Urgent account issue",
            description="Cannot access a business-critical account.",
            priority=Ticket.Priority.URGENT,
            created_by=self.employee,
        )
        self.assertIsNotNone(ticket.due_at)
        self.assertFalse(ticket.is_overdue)

    def test_reports_are_staff_only(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse("dashboard:reports"))
        self.assertEqual(response.status_code, 403)

    def test_support_can_view_reports(self):
        support = User.objects.create_user(username="slasupport", password="Test-password-789", is_staff=True)
        self.client.force_login(support)
        response = self.client.get(reverse("dashboard:reports"))
        self.assertEqual(response.status_code, 200)
