from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.shortcuts import render
from tickets.models import Ticket, Notification
from django.core.paginator import Paginator
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from .models import KnowledgeArticle
from .forms import KnowledgeArticleForm


@login_required
def home(request):
    qs = Ticket.objects.all()
    if not request.user.is_staff:
        qs = qs.filter(created_by=request.user)
    total_count = qs.count()
    open_count = qs.filter(status=Ticket.Status.OPEN).count()
    progress_count = qs.filter(status=Ticket.Status.IN_PROGRESS).count()
    waiting_count = qs.filter(status=Ticket.Status.WAITING).count()
    resolved_count = qs.filter(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]).count()
    status_summary = list(qs.values("status").annotate(total=Count("id")).order_by("status"))
    status_totals = {item["status"]: item["total"] for item in status_summary}
    status_chart = [{"key": key, "label": label, "total": status_totals.get(key, 0), "percent": round(status_totals.get(key, 0) * 100 / total_count) if total_count else 0} for key, label in Ticket.Status.choices]
    recent_tickets = qs.select_related("created_by", "assigned_to")[:6]
    unread_notifications = Notification.objects.filter(recipient=request.user, is_read=False).count()
    recent_notifications = Notification.objects.filter(recipient=request.user).select_related("ticket")[:5]
    context = {
        "total_count": total_count,
        "open_count": open_count,
        "progress_count": progress_count,
        "waiting_count": waiting_count,
        "resolved_count": resolved_count,
        "recent_tickets": recent_tickets,
        "status_chart": status_chart,
        "unread_notifications": unread_notifications,
        "recent_notifications": recent_notifications,
    }
    if request.user.is_staff:
        context["unassigned_count"] = qs.filter(assigned_to__isnull=True).exclude(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]).count()
        context["urgent_count"] = qs.filter(priority=Ticket.Priority.URGENT).exclude(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]).count()
        context["overdue_count"] = qs.filter(due_at__lt=timezone.now()).exclude(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]).count()
    return render(request, "dashboard/home.html", context)


@login_required
def knowledge_list(request):
    articles = KnowledgeArticle.objects.filter(is_published=True)
    if request.user.is_staff:
        articles = KnowledgeArticle.objects.all()
    query = request.GET.get("q", "").strip()[:120]
    category = request.GET.get("category", "").strip()[:80]
    if query:
        from django.db.models import Q
        articles = articles.filter(Q(title__icontains=query) | Q(summary__icontains=query) | Q(body__icontains=query) | Q(category__icontains=query))
    if category:
        articles = articles.filter(category__iexact=category)
    categories = articles.values_list("category", flat=True).distinct().order_by("category")
    page_obj = Paginator(articles, 10).get_page(request.GET.get("page"))
    return render(request, "dashboard/knowledge_list.html", {"articles": page_obj.object_list, "page_obj": page_obj, "query": query, "selected_category": category, "categories": categories})


@login_required
def knowledge_detail(request, slug):
    article = get_object_or_404(KnowledgeArticle, slug=slug)
    if not article.is_published and not request.user.is_staff:
        raise PermissionDenied
    return render(request, "dashboard/knowledge_detail.html", {"article": article})


def _require_staff(request):
    if not request.user.is_staff:
        raise PermissionDenied


@login_required
@require_http_methods(["GET", "POST"])
def knowledge_create(request):
    _require_staff(request)
    form = KnowledgeArticleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        article = form.save(commit=False)
        article.author = request.user
        article.save()
        messages.success(request, "Knowledge article created.")
        return redirect("dashboard:knowledge-detail", slug=article.slug)
    return render(request, "dashboard/knowledge_form.html", {"form": form, "page_title": "Create knowledge article"})


@login_required
@require_http_methods(["GET", "POST"])
def knowledge_edit(request, slug):
    _require_staff(request)
    article = get_object_or_404(KnowledgeArticle, slug=slug)
    form = KnowledgeArticleForm(request.POST or None, instance=article)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Knowledge article updated.")
        return redirect("dashboard:knowledge-detail", slug=article.slug)
    return render(request, "dashboard/knowledge_form.html", {"form": form, "page_title": "Edit knowledge article", "article": article})


@login_required
def reports(request):
    if not request.user.is_staff:
        raise PermissionDenied
    now = timezone.now()
    start_date = now - timedelta(days=30)
    all_tickets = Ticket.objects.select_related("created_by", "assigned_to")
    active_tickets = all_tickets.exclude(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED])
    overdue_tickets = active_tickets.filter(due_at__lt=now)
    recent_tickets = all_tickets.filter(created_at__gte=start_date)
    status_report = list(all_tickets.values("status").annotate(total=Count("id")).order_by("status"))
    priority_report = list(all_tickets.values("priority").annotate(total=Count("id")).order_by("priority"))
    agent_workload = get_user_model().objects.filter(is_staff=True, is_active=True, is_superuser=False).annotate(
        active_assigned=Count("assigned_helpdesk_tickets", filter=Q(assigned_helpdesk_tickets__status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS, Ticket.Status.WAITING])),
        resolved_total=Count("assigned_helpdesk_tickets", filter=Q(assigned_helpdesk_tickets__status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED])),
    ).order_by("-active_assigned", "username")
    monthly_report = []
    current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for offset in range(5, -1, -1):
        month_index = current_month.month - 1 - offset
        year = current_month.year + month_index // 12
        month = month_index % 12 + 1
        month_start = current_month.replace(year=year, month=month)
        if month == 12:
            next_month = month_start.replace(year=year + 1, month=1)
        else:
            next_month = month_start.replace(month=month + 1)
        monthly_report.append({"label": month_start.strftime("%b %Y"), "created": all_tickets.filter(created_at__gte=month_start, created_at__lt=next_month).count(), "resolved": all_tickets.filter(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED], updated_at__gte=month_start, updated_at__lt=next_month).count()})
    context = {
        "total_count": all_tickets.count(),
        "active_count": active_tickets.count(),
        "overdue_count": overdue_tickets.count(),
        "resolved_count": all_tickets.filter(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]).count(),
        "last_30_days": recent_tickets.count(),
        "status_report": status_report,
        "priority_report": priority_report,
        "agent_workload": agent_workload,
        "monthly_report": monthly_report,
        "overdue_tickets": overdue_tickets.order_by("due_at")[:12],
    }
    return render(request, "dashboard/reports.html", context)
