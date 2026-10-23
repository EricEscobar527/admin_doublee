import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Django debe inicializarse antes de importar código que use modelos.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

from apps.accounts.middleware import JWTCookieWebSocketMiddleware  # noqa: E402
from apps.support.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        # El Origin se valida contra ALLOWED_HOSTS: evita que otra página use la sesión del admin.
        "websocket": AllowedHostsOriginValidator(JWTCookieWebSocketMiddleware(URLRouter(websocket_urlpatterns))),
    }
)
