from django.contrib import messages
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods
from .forms import SignUpForm, EmployeeIDForm
from .models import EmployeeID


@require_http_methods(["GET", "POST"])
def signup_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            record = EmployeeID.objects.select_for_update().filter(
                employee_id__iexact=form.cleaned_data["employee_id"],
                is_active=True,
                registered_user__isnull=True,
            ).first()
            if record is None:
                form.add_error("employee_id", "This employee ID has already been registered or is no longer active.")
            else:
                user = form.save()
                record.registered_user = user
                record.save(update_fields=["registered_user"])
                login(request, user)
                messages.success(request, "Your employee account is ready. Welcome to HelpDesk Pro.")
                return redirect("dashboard:home")
    return render(request, "accounts/signup.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        next_url = request.POST.get("next") or request.GET.get("next", "")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            return redirect(next_url)
        return redirect("dashboard:home")
    return render(request, "accounts/login.html", {"form": form, "next": request.GET.get("next", "")})


@login_required
def profile(request):
    employee_record = EmployeeID.objects.filter(registered_user=request.user).first()
    return render(request, "accounts/profile.html", {"employee_record": employee_record})


from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from .forms import DepartmentForm
from .models import Department


def _staff_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        if not request.user.is_staff:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapped


@login_required
@_staff_required
def department_list(request):
    departments = Department.objects.all()
    query = request.GET.get("q", "").strip()[:100]
    if query:
        departments = departments.filter(name__icontains=query) | departments.filter(description__icontains=query)
    page_obj = Paginator(departments, 12).get_page(request.GET.get("page"))
    return render(request, "accounts/departments.html", {"departments": page_obj.object_list, "page_obj": page_obj, "query": query})


@login_required
@_staff_required
@require_http_methods(["GET", "POST"])
def department_create(request):
    form = DepartmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Department created successfully.")
        return redirect("accounts:departments")
    return render(request, "accounts/department_form.html", {"form": form, "page_title": "Create department"})


@login_required
@_staff_required
@require_http_methods(["GET", "POST"])
def department_edit(request, pk):
    department = get_object_or_404(Department, pk=pk)
    form = DepartmentForm(request.POST or None, instance=department)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Department changes saved.")
        return redirect("accounts:departments")
    return render(request, "accounts/department_form.html", {"form": form, "page_title": "Edit department", "department": department})


@login_required
@_staff_required
@require_POST
def department_toggle(request, pk):
    department = get_object_or_404(Department, pk=pk)
    department.is_active = not department.is_active
    department.save(update_fields=["is_active", "updated_at"])
    messages.success(request, f"{department.name} is now {'active' if department.is_active else 'inactive'}.")
    return redirect("accounts:departments")


def _superuser_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        if not request.user.is_superuser:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapped


@login_required
@_superuser_required
def user_management(request):
    from django.core.paginator import Paginator
    User = get_user_model()
    query = request.GET.get("q", "").strip()[:100]
    users = User.objects.all().order_by("username")
    if query:
        from django.db.models import Q
        users = users.filter(Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query))
    page_obj = Paginator(users, 15).get_page(request.GET.get("page"))
    employee_ids = EmployeeID.objects.select_related("registered_user").order_by("employee_id")
    employee_form = EmployeeIDForm()
    return render(request, "accounts/user_management.html", {"page_obj": page_obj, "managed_users": page_obj.object_list, "query": query, "employee_ids": employee_ids, "employee_form": employee_form})


@login_required
@_superuser_required
@require_http_methods(["POST"])
def employee_id_create(request):
    form = EmployeeIDForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Approved employee ID added.")
    else:
        messages.error(request, "Could not add the employee ID. Check the values and try again.")
    return redirect("accounts:user-management")


@login_required
@_superuser_required
@require_POST
def employee_id_toggle(request, pk):
    record = get_object_or_404(EmployeeID, pk=pk)
    record.is_active = not record.is_active
    record.save(update_fields=["is_active"])
    messages.success(request, f"Employee ID {record.employee_id} is now {'active' if record.is_active else 'inactive'}.")
    return redirect("accounts:user-management")


@login_required
@_superuser_required
@require_POST
def user_toggle_support(request, pk):
    User = get_user_model()
    target = get_object_or_404(User, pk=pk)
    if target.is_superuser or target.pk == request.user.pk:
        messages.error(request, "Superuser accounts cannot be changed from this page.")
        return redirect("accounts:user-management")
    target.is_staff = not target.is_staff
    target.save(update_fields=["is_staff"])
    role = "support agent" if target.is_staff else "employee"
    messages.success(request, f"{target.get_username()} is now configured as {role}.")
    return redirect("accounts:user-management")


@login_required
@_superuser_required
@require_POST
def user_toggle_active(request, pk):
    User = get_user_model()
    target = get_object_or_404(User, pk=pk)
    if target.is_superuser or target.pk == request.user.pk:
        messages.error(request, "You cannot deactivate your own account or another superuser here.")
        return redirect("accounts:user-management")
    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])
    messages.success(request, f"{target.get_username()} is now {'active' if target.is_active else 'inactive'}.")
    return redirect("accounts:user-management")
