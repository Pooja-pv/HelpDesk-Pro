from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("dashboard.urls")),
    path("accounts/password-change/", auth_views.PasswordChangeView.as_view(template_name="accounts/password_change.html", success_url="/accounts/profile/"), name="password_change"),
    path("accounts/", include("accounts.urls")),
    path("tickets/", include("tickets.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
