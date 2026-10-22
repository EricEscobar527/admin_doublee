from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .jwt_cookies import set_access_cookie


class JWTCookieAuthenticationMiddleware:
    """Autentica el panel web con el JWT guardado en cookies HttpOnly.

    Si el access token expiró pero el refresh sigue vigente, emite un access
    nuevo de forma transparente.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request):
        new_access = None
        user = self._user_from_access(request.COOKIES.get(settings.JWT_ACCESS_COOKIE))
        if user is None:
            user, new_access = self._user_from_refresh(request.COOKIES.get(settings.JWT_REFRESH_COOKIE))

        request.user = user or AnonymousUser()
        response = self.get_response(request)
        if new_access is not None and settings.JWT_REFRESH_COOKIE in request.COOKIES:
            set_access_cookie(response, new_access)
        return response

    def _user_from_access(self, raw):
        if not raw:
            return None
        try:
            return self.jwt_auth.get_user(self.jwt_auth.get_validated_token(raw.encode()))
        except (TokenError, AuthenticationFailed):
            return None

    def _user_from_refresh(self, raw):
        if not raw:
            return None, None
        try:
            refresh = RefreshToken(raw)
        except TokenError:
            return None, None
        user_id = refresh.get(settings.SIMPLE_JWT.get("USER_ID_CLAIM", "user_id"))
        user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
        if user is None:
            return None, None
        return user, refresh.access_token
