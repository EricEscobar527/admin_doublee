from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .jwt_cookies import clear_auth_cookies, set_auth_cookies


@require_http_methods(["GET", "POST"])
def login_view(request):
    next_url = request.POST.get("next") or request.GET.get("next") or ""
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = ""

    if request.user.is_authenticated and request.user.is_admin:
        return redirect(next_url or "dashboard:home")

    error = None
    username = ""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is None or not user.is_admin:
            error = "Usuario o contraseña incorrectos."
        else:
            update_last_login(None, user)
            response = redirect(next_url or "dashboard:home")
            set_auth_cookies(response, RefreshToken.for_user(user))
            return response

    return render(request, "accounts/login.html", {"error": error, "username": username, "next": next_url})


@require_POST
def logout_view(request):
    raw = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
    if raw:
        try:
            RefreshToken(raw).blacklist()
        except TokenError:
            pass
    response = redirect("accounts:login")
    clear_auth_cookies(response)
    return response
