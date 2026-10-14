from django.urls import path
from . import views

app_name = "tickets"
urlpatterns = [
    path("", views.ticket_list, name="list"),
    path("export/csv/", views.export_tickets_csv, name="export-csv"),
    path("new/", views.ticket_create, name="create"),
    path("notifications/", views.notification_list, name="notifications"),
    path("notifications/read-all/", views.notification_mark_all_read, name="notification-read-all"),
    path("notifications/<int:pk>/open/", views.notification_open, name="notification-open"),
    path("<int:pk>/", views.ticket_detail, name="detail"),
    path("<int:pk>/comment/", views.ticket_comment, name="comment"),
    path("<int:pk>/update/", views.ticket_update, name="update"),
]
