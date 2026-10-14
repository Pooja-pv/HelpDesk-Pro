from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Department, EmployeeID

User = get_user_model()


class SignUpForm(UserCreationForm):
    employee_id = forms.CharField(max_length=40, label="Employee ID")
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("employee_id", "username", "first_name", "last_name", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_employee_id(self):
        employee_id = self.cleaned_data["employee_id"].strip()
        try:
            record = EmployeeID.objects.get(employee_id__iexact=employee_id, is_active=True, registered_user__isnull=True)
        except EmployeeID.DoesNotExist:
            raise forms.ValidationError("This employee ID is not approved, is inactive, or has already been registered.")
        self.employee_record = record
        return record.employee_id

    def clean(self):
        cleaned = super().clean()
        record = getattr(self, "employee_record", None)
        email = cleaned.get("email", "").strip().lower()
        if record and email and record.email.lower() != email:
            self.add_error("email", "Use the email address registered by your administrator for this employee ID.")
        if record:
            full_name = " ".join(part for part in [cleaned.get("first_name", "").strip(), cleaned.get("last_name", "").strip()] if part)
            if full_name and full_name.casefold() != record.full_name.strip().casefold():
                self.add_error("first_name", "Enter the name approved by your administrator.")
        return cleaned


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. IT Support", "class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "What this department handles", "class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class EmployeeIDForm(forms.ModelForm):
    class Meta:
        model = EmployeeID
        fields = ["employee_id", "full_name", "email", "is_active"]
        widgets = {
            "employee_id": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. EMP-1042"}),
            "full_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Employee full name"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "employee@company.com"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_employee_id(self):
        value = self.cleaned_data["employee_id"].strip()
        qs = EmployeeID.objects.filter(employee_id__iexact=value)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This employee ID already exists.")
        return value

    def clean_email(self):
        value = self.cleaned_data["email"].strip().lower()
        qs = EmployeeID.objects.filter(email__iexact=value)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This email is already linked to an approved employee ID.")
        return value
