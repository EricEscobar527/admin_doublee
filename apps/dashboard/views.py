from django.shortcuts import render

from apps.accounts.decorators import admin_required
from apps.support.models import SupportTicket
from apps.support.stats import ticket_stats


@admin_required
def home(request):
    latest = SupportTicket.objects.select_related("application").order_by("-created_at")[:8]
    return render(request, "dashboard/home.html", {"stats": ticket_stats(), "latest": latest, "active_menu": "dashboard"})
