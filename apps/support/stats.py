from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from .models import SupportTicket


def ticket_stats():
    week_ago = timezone.now() - timedelta(days=7)
    return SupportTicket.objects.aggregate(
        total=Count("id"),
        new=Count("id", filter=Q(status=SupportTicket.Status.NEW)),
        in_review=Count("id", filter=Q(status=SupportTicket.Status.IN_REVIEW)),
        last_week=Count("id", filter=Q(created_at__gte=week_ago)),
    )
