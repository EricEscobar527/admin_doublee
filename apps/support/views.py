from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import admin_required
from apps.applications.models import Application

from .models import SupportAttachment, SupportTicket
from .realtime import broadcast


@admin_required
def ticket_list(request):
    tickets = (
        SupportTicket.objects.select_related("application")
        .annotate(image_count=Count("attachments"))
        .order_by("-created_at")
    )

    status = request.GET.get("status", "")
    issue = request.GET.get("issue", "")
    app = request.GET.get("app", "")
    q = request.GET.get("q", "").strip()
    if app.isdigit():
        tickets = tickets.filter(application_id=int(app))
    if status in SupportTicket.Status.values:
        tickets = tickets.filter(status=status)
    if issue in SupportTicket.Issue.values:
        tickets = tickets.filter(issue=issue)
    if q:
        search = (
            Q(email__icontains=q)
            | Q(message__icontains=q)
            | Q(name__icontains=q)
            | Q(phone_model__icontains=q)
            | Q(device_model__icontains=q)
        )
        if q.upper().startswith("SOP-") and q[4:].isdigit():
            search |= Q(pk=int(q[4:]))
        elif q.isdigit():
            search |= Q(pk=int(q))
        tickets = tickets.filter(search)

    page = Paginator(tickets, 20).get_page(request.GET.get("page"))
    filters = request.GET.copy()
    filters.pop("page", None)
    return render(
        request,
        "support/list.html",
        {
            "page": page,
            "status": status,
            "issue": issue,
            "app": app,
            "applications": Application.objects.order_by("name"),
            "q": q,
            "querystring": filters.urlencode(),
            "statuses": SupportTicket.Status.choices,
            "issues": SupportTicket.Issue.choices,
            "active_menu": "support",
        },
    )


@admin_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(
        SupportTicket.objects.select_related("application").prefetch_related("attachments"), pk=pk
    )
    return render(
        request,
        "support/detail.html",
        {"ticket": ticket, "statuses": SupportTicket.Status.choices, "active_menu": "support"},
    )


@admin_required
@require_POST
def ticket_update(request, pk):
    ticket = get_object_or_404(SupportTicket, pk=pk)
    status = request.POST.get("status")
    if status in SupportTicket.Status.values:
        ticket.status = status
    ticket.admin_notes = request.POST.get("admin_notes", ticket.admin_notes)
    ticket.save(update_fields=["status", "admin_notes", "updated_at"])
    broadcast("ticket.updated", ticket.pk)
    return redirect("support:detail", pk=pk)


@admin_required
def attachment_file(request, pk):
    """Sirve las imágenes solo a admins: local por streaming, S3 con URL firmada."""
    attachment = get_object_or_404(SupportAttachment, pk=pk)
    storage = attachment.file.storage
    try:
        storage.path(attachment.file.name)
    except NotImplementedError:
        return redirect(attachment.file.url)
    try:
        return FileResponse(attachment.file.open("rb"), content_type=attachment.content_type)
    except FileNotFoundError:
        raise Http404
