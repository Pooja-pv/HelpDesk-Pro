from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Department, EmployeeID

User = get_user_model()


class ApprovedEmployeeRegistrationTests(TestCase):
    def setUp(self):
        self.employee_record = EmployeeID.objects.create(
            employee_id="EMP-1001",
            full_name="Alex Morgan",
            email="alex.morgan@example.com",
        )

    def test_approved_employee_can_register(self):
        response = self.client.post(reverse("accounts:signup"), {
            "employee_id": "EMP-1001",
            "username": "alexmorgan",
            "first_name": "Alex",
            "last_name": "Morgan",
            "email": "alex.morgan@example.com",
            "password1": "Strong-test-password-784!",
            "password2": "Strong-test-password-784!",
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="alexmorgan")
        self.employee_record.refresh_from_db()
        self.assertEqual(self.employee_record.registered_user, user)

    def test_unapproved_employee_cannot_register(self):
        response = self.client.post(reverse("accounts:signup"), {
            "employee_id": "EMP-9999",
            "username": "unknownemployee",
            "first_name": "Unknown",
            "last_name": "Employee",
            "email": "unknown@example.com",
            "password1": "Strong-test-password-784!",
            "password2": "Strong-test-password-784!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="unknownemployee").exists())

    def test_approved_employee_email_must_match(self):
        response = self.client.post(reverse("accounts:signup"), {
            "employee_id": "EMP-1001",
            "username": "alexmorgan",
            "first_name": "Alex",
            "last_name": "Morgan",
            "email": "other@example.com",
            "password1": "Strong-test-password-784!",
            "password2": "Strong-test-password-784!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="alexmorgan").exists())


class DepartmentManagementTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="opsadmin", password="StrongPass123!", is_staff=True)
        self.employee = User.objects.create_user(username="employee", password="StrongPass123!")

    def test_staff_can_create_department(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse("accounts:department-create"), {"name": "IT Support", "description": "Technical help", "is_active": "on"})
        self.assertRedirects(response, reverse("accounts:departments"))
        self.assertTrue(Department.objects.filter(name="IT Support", is_active=True).exists())

    def test_employee_cannot_access_department_management(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse("accounts:departments"))
        self.assertEqual(response.status_code, 403)


class UserManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="siteadmin", email="admin@example.com", password="Strong-test-password-784!")
        self.employee = User.objects.create_user(username="teamemployee", password="Strong-test-password-784!")

    def test_user_management_is_superuser_only(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse("accounts:user-management"))
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_promote_employee_to_support_agent(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("accounts:user-toggle-support", args=[self.employee.pk]))
        self.assertRedirects(response, reverse("accounts:user-management"))
        self.employee.refresh_from_db()
        self.assertTrue(self.employee.is_staff)
