from datetime import timedelta

from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.decorators import admin_required
from apps.support.models import SupportTicket


@admin_required
def home(request):
    week_ago = timezone.now() - timedelta(days=7)
    stats = SupportTicket.objects.aggregate(
        total=Count("id"),
        new=Count("id", filter=Q(status=SupportTicket.Status.NEW)),
        in_review=Count("id", filter=Q(status=SupportTicket.Status.IN_REVIEW)),
        last_week=Count("id", filter=Q(created_at__gte=week_ago)),
    )
    latest = SupportTicket.objects.select_related("application").order_by("-created_at")[:8]
    return render(request, "dashboard/home.html", {"stats": stats, "latest": latest, "active_menu": "dashboard"})
