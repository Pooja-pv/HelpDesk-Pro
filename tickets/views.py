from datetime import timedelta
import csv

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .forms import TicketCommentForm, TicketCreateForm, TicketUpdateForm
from .models import Notification, Ticket, TicketAuditLog


def _notify_users(users, ticket, message):
    notifications = [
        Notification(recipient=user, ticket=ticket, message=message)
        for user in users
        if user and user.is_active
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)


def _support_users(exclude_id=None):
    users = get_user_model().objects.filter(is_staff=True, is_active=True)
    if exclude_id:
        users = users.exclude(pk=exclude_id)
    return users


@login_required
def ticket_list(request):
    tickets = Ticket.objects.select_related("created_by", "assigned_to")

    if not request.user.is_staff:
        tickets = tickets.filter(created_by=request.user)

    search = request.GET.get("q", "").strip()[:120]
    status = request.GET.get("status", "").strip()
    priority = request.GET.get("priority", "").strip()
    category = request.GET.get("category", "").strip()[:80]

    if search:
        search_filter = (
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(category__icontains=search)
            | Q(created_by__username__icontains=search)
        )

        if search.upper().startswith("HD-") and search[3:].isdigit():
            search_filter |= Q(pk=int(search[3:]))
        elif search.isdigit():
            search_filter |= Q(pk=int(search))

        tickets = tickets.filter(search_filter)

    valid_statuses = {choice[0] for choice in Ticket.Status.choices}
    valid_priorities = {choice[0] for choice in Ticket.Priority.choices}

    if status in valid_statuses:
        tickets = tickets.filter(status=status)
    else:
        status = ""

    if priority in valid_priorities:
        tickets = tickets.filter(priority=priority)
    else:
        priority = ""

    if category:
        tickets = tickets.filter(category__iexact=category)

    categories = (
        Ticket.objects.values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )

    page_obj = Paginator(tickets, 12).get_page(request.GET.get("page"))

    return render(
        request,
        "tickets/list.html",
        {
            "tickets": page_obj.object_list,
            "page_obj": page_obj,
            "search_query": search,
            "selected_status": status,
            "selected_priority": priority,
            "selected_category": category,
            "statuses": Ticket.Status.choices,
            "priorities": Ticket.Priority.choices,
            "categories": categories,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def ticket_create(request):
    if request.user.is_staff:
        raise PermissionDenied

    form = TicketCreateForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            ticket = form.save(commit=False)
            ticket.created_by = request.user
            ticket.save()

            TicketAuditLog.objects.create(
                ticket=ticket,
                actor=request.user,
                action="Ticket created",
                details=(
                    f"Created with {ticket.get_priority_display()} priority."
                ),
            )

            _notify_users(
                _support_users(),
                ticket,
                f"New ticket HD-{ticket.pk}: {ticket.title}",
            )

        messages.success(
            request,
            f"Ticket HD-{ticket.pk} was created successfully.",
        )
        return redirect("tickets:detail", pk=ticket.pk)

    return render(request, "tickets/create.html", {"form": form})


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(
        Ticket.objects.select_related("created_by", "assigned_to"),
        pk=pk,
    )

    if not request.user.is_staff and ticket.created_by_id != request.user.id:
        raise PermissionDenied

    form = TicketUpdateForm(instance=ticket) if request.user.is_staff else None
    comment_form = TicketCommentForm()
    comments = ticket.comments.select_related("author").all()
    audit_events = ticket.audit_events.select_related("actor")[:20]

    return render(
        request,
        "tickets/detail.html",
        {
            "ticket": ticket,
            "form": form,
            "comment_form": comment_form,
            "comments": comments,
            "audit_events": audit_events,
        },
    )


@login_required
@require_POST
def ticket_comment(request, pk):
    ticket = get_object_or_404(
        Ticket.objects.select_related("created_by", "assigned_to"),
        pk=pk,
    )

    if not request.user.is_staff and ticket.created_by_id != request.user.id:
        raise PermissionDenied

    form = TicketCommentForm(request.POST)

    if form.is_valid():
        with transaction.atomic():
            comment = form.save(commit=False)
            comment.ticket = ticket
            comment.author = request.user
            comment.save()

            TicketAuditLog.objects.create(
                ticket=ticket,
                actor=request.user,
                action="Comment added",
                details="A conversation update was posted.",
            )

            if request.user.is_staff:
                recipients = [ticket.created_by]
                notification_message = (
                    f"Support replied to ticket HD-{ticket.pk}."
                )
            else:
                recipients = (
                    [ticket.assigned_to]
                    if ticket.assigned_to_id
                    else list(_support_users())
                )
                notification_message = (
                    f"New employee reply on ticket HD-{ticket.pk}."
                )

            _notify_users(recipients, ticket, notification_message)

        messages.success(request, "Your comment was added.")
    else:
        messages.error(
            request,
            "Please enter a comment of up to 3000 characters.",
        )

    return redirect("tickets:detail", pk=pk)


@login_required
@user_passes_test(lambda user: user.is_staff)
@require_POST
def ticket_update(request, pk):
    with transaction.atomic():
        ticket = get_object_or_404(
            Ticket.objects.select_for_update(of=("self",)).select_related(
                "created_by",
                "assigned_to",
            ),
            pk=pk,
        )

        previous_status = ticket.status
        previous_priority = ticket.priority
        previous_assignee_id = ticket.assigned_to_id

        form = TicketUpdateForm(request.POST, instance=ticket)

        if form.is_valid():
            updated_ticket = form.save(commit=False)

            if updated_ticket.priority != previous_priority:
                updated_ticket.due_at = updated_ticket.created_at + timedelta(
                    hours=Ticket.SLA_HOURS.get(updated_ticket.priority, 72)
                )

            updated_ticket.save()

            if updated_ticket.priority != previous_priority:
                TicketAuditLog.objects.create(
                    ticket=updated_ticket,
                    actor=request.user,
                    action="Priority changed",
                    details=(
                        f"{previous_priority} → {updated_ticket.priority}; "
                        "SLA deadline recalculated."
                    ),
                )

            if updated_ticket.status != previous_status:
                TicketAuditLog.objects.create(
                    ticket=updated_ticket,
                    actor=request.user,
                    action="Status changed",
                    details=(
                        f"{previous_status} → {updated_ticket.status}"
                    ),
                )

                _notify_users(
                    [updated_ticket.created_by],
                    updated_ticket,
                    (
                        f"Ticket HD-{updated_ticket.pk} status changed to "
                        f"{updated_ticket.get_status_display()}."
                    ),
                )

            if updated_ticket.assigned_to_id != previous_assignee_id:
                assignee = (
                    updated_ticket.assigned_to.get_username()
                    if updated_ticket.assigned_to_id
                    else "Unassigned"
                )

                TicketAuditLog.objects.create(
                    ticket=updated_ticket,
                    actor=request.user,
                    action="Assignment changed",
                    details=f"Assigned to {assignee}.",
                )

            if (
                updated_ticket.assigned_to_id
                and updated_ticket.assigned_to_id != previous_assignee_id
            ):
                _notify_users(
                    [updated_ticket.assigned_to],
                    updated_ticket,
                    f"Ticket HD-{updated_ticket.pk} was assigned to you.",
                )

            messages.success(request, "Ticket details updated.")
        else:
            messages.error(request, "Please check the ticket update form.")

    return redirect("tickets:detail", pk=pk)


@login_required
def notification_list(request):
    notifications = (
        Notification.objects.filter(recipient=request.user)
        .select_related("ticket")
    )

    return render(
        request,
        "tickets/notifications.html",
        {"notifications": notifications[:100]},
    )


@login_required
@require_POST
def notification_mark_all_read(request):
    Notification.objects.filter(
        recipient=request.user,
        is_read=False,
    ).update(is_read=True)

    messages.success(request, "All notifications marked as read.")
    return redirect("tickets:notifications")


@login_required
@require_POST
def notification_open(request, pk):
    notification = get_object_or_404(
        Notification.objects.select_related("ticket"),
        pk=pk,
        recipient=request.user,
    )

    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])

    return redirect("tickets:detail", pk=notification.ticket_id)


@login_required
@user_passes_test(lambda user: user.is_staff)
def export_tickets_csv(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        'attachment; filename="helpdesk-tickets.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(
        [
            "Ticket ID",
            "Title",
            "Requester",
            "Assignee",
            "Category",
            "Priority",
            "Status",
            "SLA deadline",
            "Overdue",
            "Created",
            "Last updated",
        ]
    )

    tickets = (
        Ticket.objects.select_related("created_by", "assigned_to")
        .order_by("-created_at")
    )

    for ticket in tickets.iterator():
        writer.writerow(
            [
                f"HD-{ticket.pk}",
                ticket.title,
                ticket.created_by.get_username(),
                (
                    ticket.assigned_to.get_username()
                    if ticket.assigned_to_id
                    else "Unassigned"
                ),
                ticket.category,
                ticket.get_priority_display(),
                ticket.get_status_display(),
                ticket.sla_deadline.isoformat(),
                "Yes" if ticket.is_overdue else "No",
                ticket.created_at.isoformat(),
                ticket.updated_at.isoformat(),
            ]
        )

    return response
