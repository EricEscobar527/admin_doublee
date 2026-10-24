import hmac

from django.contrib.auth.models import AnonymousUser
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.permissions import BasePermission

from .models import Application


class AppBearerTokenAuthentication(BaseAuthentication):
    """Authorization: Bearer <token>; el token identifica a la aplicación que llama."""

    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if not parts or parts[0].lower() != b"bearer":
            return None
        if len(parts) != 2:
            raise exceptions.AuthenticationFailed("Encabezado Authorization inválido.")
        token = parts[1].decode(errors="ignore")
        application = Application.objects.filter(api_token=token, is_active=True).first()
        if application is None or not hmac.compare_digest(token, application.api_token):
            raise exceptions.AuthenticationFailed("Token inválido.")
        return AnonymousUser(), application

    def authenticate_header(self, request):
        return "Bearer"


class HasAppToken(BasePermission):
    def has_permission(self, request, view):
        return bool(request.auth)
