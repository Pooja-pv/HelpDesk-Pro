from django.urls import path
from . import views

app_name = "dashboard"
urlpatterns = [
    path("", views.home, name="home"),
    path("reports/", views.reports, name="reports"),
    path("knowledge/", views.knowledge_list, name="knowledge-list"),
    path("knowledge/new/", views.knowledge_create, name="knowledge-create"),
    path("knowledge/<slug:slug>/", views.knowledge_detail, name="knowledge-detail"),
    path("knowledge/<slug:slug>/edit/", views.knowledge_edit, name="knowledge-edit"),
]
