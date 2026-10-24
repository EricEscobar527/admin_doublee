from django.urls import include, path, re_path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from apps.applications.api import AppConfigAPIView
from apps.legal.views import viajeok_privacy
from apps.subscriptions.api import SubscriptionVerifyAPIView
from apps.support.api import SupportTicketCreateAPIView

urlpatterns = [
    path("", include("apps.dashboard.urls")),
    path("", include("apps.accounts.urls")),
    path("soporte/", include("apps.support.urls")),
    path("suscripciones/", include("apps.subscriptions.urls")),
    path("aplicaciones/", include("apps.applications.urls")),
    # Páginas públicas (sin sesión), p. ej. la política de privacidad que pide Play Console
    path("viajeok/privacidad/", viajeok_privacy, name="viajeok_privacy"),
    # API JWT (para clientes que no usan el panel web)
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # API para las apps móviles (Bearer token de cada app); aceptan la ruta con o sin "/" final.
    re_path(r"^api/support/tickets/?$", SupportTicketCreateAPIView.as_view(), name="api_support_tickets"),
    re_path(r"^api/app/config/?$", AppConfigAPIView.as_view(), name="api_app_config"),
    re_path(r"^api/subscriptions/verify/?$", SubscriptionVerifyAPIView.as_view(), name="api_subscriptions_verify"),
]
