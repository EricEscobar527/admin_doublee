from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from apps.accounts.decorators import admin_required
from apps.applications.models import Application

from .models import Subscription


@admin_required
def subscription_list(request):
    subscriptions = Subscription.objects.select_related("application")
    app = request.GET.get("app", "")
    active = request.GET.get("active", "")
    if app.isdigit():
        subscriptions = subscriptions.filter(application_id=int(app))
    if active in ("1", "0"):
        subscriptions = subscriptions.filter(active=active == "1")

    stats = subscriptions.aggregate(
        total=Count("id"),
        with_access=Count("id", filter=Q(active=True)),
        trial=Count("id", filter=Q(active=True, in_trial=True)),
        paying=Count("id", filter=Q(active=True, in_trial=False, test_purchase=False)),
    )
    filters = request.GET.copy()
    filters.pop("page", None)
    return render(
        request,
        "subscriptions/list.html",
        {
            "page": Paginator(subscriptions, 25).get_page(request.GET.get("page")),
            "stats": stats,
            "app": app,
            "active": active,
            "applications": Application.objects.order_by("name"),
            "querystring": filters.urlencode(),
            "active_menu": "subscriptions",
        },
    )


@admin_required
def subscription_detail(request, pk):
    subscription = get_object_or_404(Subscription.objects.select_related("application"), pk=pk)
    return render(request, "subscriptions/detail.html", {"subscription": subscription, "active_menu": "subscriptions"})
