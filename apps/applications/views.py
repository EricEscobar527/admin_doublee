from django.contrib import messages
from django.db.models import Count, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import admin_required

from .forms import ApplicationForm
from .models import Application


@admin_required
def app_list(request):
    applications = Application.objects.annotate(ticket_count=Count("support_tickets")).order_by("name")
    return render(request, "applications/list.html", {"applications": applications, "active_menu": "applications"})


@admin_required
def app_create(request):
    form = ApplicationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        application = form.save()
        messages.success(request, f"Aplicación «{application.name}» creada. Copia su token para configurarla.")
        return redirect("applications:edit", pk=application.pk)
    return render(request, "applications/form.html", {"form": form, "active_menu": "applications"})


@admin_required
def app_edit(request, pk):
    application = get_object_or_404(Application, pk=pk)
    form = ApplicationForm(request.POST or None, instance=application)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Cambios guardados.")
        return redirect("applications:list")
    return render(
        request,
        "applications/form.html",
        {"form": form, "application": application, "active_menu": "applications"},
    )


@admin_required
@require_POST
def app_regenerate_token(request, pk):
    application = get_object_or_404(Application, pk=pk)
    application.regenerate_token()
    messages.warning(request, "Token regenerado. El anterior dejó de funcionar: actualiza la app.")
    return redirect("applications:edit", pk=pk)


@admin_required
def app_delete(request, pk):
    application = get_object_or_404(Application.objects.annotate(ticket_count=Count("support_tickets")), pk=pk)
    if request.method == "POST":
        try:
            application.delete()
        except ProtectedError:
            messages.error(
                request,
                f"«{application.name}» tiene tickets de soporte y no se puede eliminar. Desactívala en su lugar.",
            )
            return redirect("applications:list")
        messages.success(request, f"Aplicación «{application.name}» eliminada.")
        return redirect("applications:list")
    return render(
        request,
        "applications/confirm_delete.html",
        {"application": application, "active_menu": "applications"},
    )
