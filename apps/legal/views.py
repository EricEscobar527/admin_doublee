from django.conf import settings
from django.shortcuts import render
from django.views.decorators.cache import cache_control


@cache_control(public=True, max_age=3600)
def viajeok_privacy(request):
    """Política de privacidad pública de ViajeOK (la pide Play Console)."""
    return render(request, "legal/viajeok_privacidad.html", {"contact_email": settings.PRIVACY_CONTACT_EMAIL})
