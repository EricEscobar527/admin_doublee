from http.cookies import SimpleCookie

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from django.contrib.auth.models import AnonymousUser

from .jwt_auth import user_from_jwt_cookies
from .jwt_cookies import set_access_cookie


class JWTCookieAuthenticationMiddleware:
    """Autentica el panel web con el JWT guardado en cookies HttpOnly.

    Si el access token expiró pero el refresh sigue vigente, emite un access
    nuevo de forma transparente.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user, new_access = user_from_jwt_cookies(request.COOKIES)
        request.user = user or AnonymousUser()
        response = self.get_response(request)
        if new_access is not None:
            set_access_cookie(response, new_access)
        return response


class JWTCookieWebSocketMiddleware(BaseMiddleware):
    """Lo mismo para WebSockets: el navegador manda las cookies en el handshake."""

    async def __call__(self, scope, receive, send):
        cookies = SimpleCookie()
        for name, value in scope.get("headers", []):
            if name == b"cookie":
                cookies.load(value.decode("latin-1"))
        user, _ = await database_sync_to_async(user_from_jwt_cookies)({k: m.value for k, m in cookies.items()})
        scope["user"] = user or AnonymousUser()
        return await super().__call__(scope, receive, send)
