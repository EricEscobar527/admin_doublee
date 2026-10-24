from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import AppBearerTokenAuthentication, HasAppToken


class AppConfigAPIView(APIView):
    """Configuración remota de la app que hace la petición (identificada por su token)."""

    authentication_classes = [AppBearerTokenAuthentication]
    permission_classes = [HasAppToken]

    def get(self, request):
        app = request.auth
        beta_ends_at = timezone.localtime(app.beta_ends_at).isoformat(timespec="seconds") if app.beta_ends_at else None
        response = Response(
            {
                "paywall_enabled": app.paywall_enabled,
                "beta_ends_at": beta_ends_at,
                "beta_message": app.beta_message,
                "subscription_product_id": app.subscription_product_id,
                "min_supported_build": app.min_supported_build,
            }
        )
        response["Cache-Control"] = "private, max-age=300"
        return response
