from django.urls import include, path, re_path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from apps.support.api import SupportTicketCreateAPIView

urlpatterns = [
    path("", include("apps.dashboard.urls")),
    path("", include("apps.accounts.urls")),
    path("soporte/", include("apps.support.urls")),
    path("aplicaciones/", include("apps.applications.urls")),
    # API JWT (para clientes que no usan el panel web)
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # API para las apps móviles; acepta la ruta con o sin "/" final.
    re_path(r"^api/support/tickets/?$", SupportTicketCreateAPIView.as_view(), name="api_support_tickets"),
]
