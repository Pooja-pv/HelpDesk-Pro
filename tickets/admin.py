from django.contrib import admin
from .models import Notification, Ticket, TicketComment, TicketAuditLog


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_by", "priority", "status", "assigned_to", "due_at", "created_at", "updated_at")
    list_filter = ("status", "priority", "category", "due_at", "created_at")
    search_fields = ("title", "description", "created_by__username", "assigned_to__username")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("created_by", "assigned_to")
    date_hierarchy = "created_at"


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ("ticket", "author", "created_at")
    search_fields = ("message", "author__username", "ticket__title")
    readonly_fields = ("created_at",)
    list_select_related = ("ticket", "author")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "ticket", "message", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("recipient__username", "message", "ticket__title")
    readonly_fields = ("created_at",)
    list_select_related = ("recipient", "ticket")


@admin.register(TicketAuditLog)
class TicketAuditLogAdmin(admin.ModelAdmin):
    list_display = ("ticket", "actor", "action", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("details", "actor__username", "ticket__title")
    readonly_fields = ("ticket", "actor", "action", "details", "created_at")
