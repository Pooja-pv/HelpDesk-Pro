from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import EmployeeID

admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(EmployeeID)
class EmployeeIDAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "full_name", "email", "is_active", "registered_user")
    list_filter = ("is_active",)
    search_fields = ("employee_id", "full_name", "email")
    readonly_fields = ("created_at", "registered_user")
    ordering = ("employee_id",)


from .models import Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")
