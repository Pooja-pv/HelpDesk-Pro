from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

app_name = "accounts"
urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("profile/", views.profile, name="profile"),
    path("users/", views.user_management, name="user-management"),
    path("users/employee-ids/new/", views.employee_id_create, name="employee-id-create"),
    path("users/employee-ids/<int:pk>/toggle/", views.employee_id_toggle, name="employee-id-toggle"),
    path("users/<int:pk>/toggle-support/", views.user_toggle_support, name="user-toggle-support"),
    path("users/<int:pk>/toggle-active/", views.user_toggle_active, name="user-toggle-active"),
    path("departments/", views.department_list, name="departments"),
    path("departments/new/", views.department_create, name="department-create"),
    path("departments/<int:pk>/edit/", views.department_edit, name="department-edit"),
    path("departments/<int:pk>/toggle/", views.department_toggle, name="department-toggle"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
