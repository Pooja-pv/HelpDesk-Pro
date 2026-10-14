def notification_summary(request):
    if not request.user.is_authenticated:
        return {"unread_notification_count": 0}
    from tickets.models import Notification
    return {"unread_notification_count": Notification.objects.filter(recipient=request.user, is_read=False).count()}
