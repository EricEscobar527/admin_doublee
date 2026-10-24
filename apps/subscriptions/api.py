import logging
from datetime import timedelta
from datetime import timezone as dt_timezone

from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.applications.authentication import AppBearerTokenAuthentication, HasAppToken

from . import google_play
from .models import Subscription, hash_token

logger = logging.getLogger(__name__)

# Si la misma compra se verificó hace menos de esto, se responde con lo guardado (cuida la cuota de Google).
RECHECK_AFTER = timedelta(minutes=1)


class VerifyRequestSerializer(serializers.Serializer):
    package_name = serializers.CharField(max_length=150)
    product_id = serializers.CharField(max_length=100)
    purchase_token = serializers.CharField(max_length=4096)
    install_id = serializers.CharField(max_length=64, required=False, allow_blank=True)


def _result(subscription):
    if not subscription.active:
        return {"active": False}
    expires = subscription.expires_at
    return {
        "active": True,
        "in_trial": subscription.in_trial,
        "expires_at": expires.astimezone(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if expires else None,
    }


class SubscriptionVerifyAPIView(APIView):
    authentication_classes = [AppBearerTokenAuthentication]
    permission_classes = [HasAppToken]

    def post(self, request):
        app = request.auth
        serializer = VerifyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Solo se consulta a Google por el paquete y el producto registrados para esta app.
        if not app.package_name or data["package_name"] != app.package_name:
            return Response(
                {"package_name": ["No coincide con el paquete registrado para esta aplicación."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if app.subscription_product_id and data["product_id"] != app.subscription_product_id:
            return Response(
                {"product_id": ["No coincide con la suscripción configurada para esta aplicación."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = data["purchase_token"]
        install_id = data.get("install_id", "")
        existing = Subscription.objects.filter(token_hash=hash_token(token)).first()
        if existing and existing.application_id != app.pk:
            return Response({"active": False})
        if existing and timezone.now() - existing.last_verified_at < RECHECK_AFTER:
            if install_id and existing.install_id != install_id:
                existing.install_id = install_id
                existing.save(update_fields=["install_id", "token_hash", "updated_at"])
            return Response(_result(existing))

        subscription = existing or Subscription(application=app, purchase_token=token)
        subscription.package_name = data["package_name"]
        subscription.product_id = data["product_id"]
        subscription.install_id = install_id or subscription.install_id
        subscription.last_verified_at = timezone.now()

        try:
            raw = google_play.get_subscription(app.package_name, token)
            purchase = google_play.parse_subscription(raw, data["product_id"])
        except google_play.InvalidPurchase as exc:
            logger.info("Compra rechazada por Google (%s): %s", app.code, exc)
            subscription.state = Subscription.INVALID
            subscription.active = False
            subscription.save()
            return Response({"active": False})
        except google_play.GooglePlayError:
            # Sin respuesta de Google no se sabe el estado: la app debe conservar el resultado anterior.
            logger.exception("No se pudo consultar Google Play")
            return Response(
                {"detail": "No se pudo verificar con Google Play. Intenta más tarde."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if purchase.active and not purchase.acknowledged:
            # Si no se reconoce en 3 días, Google la reembolsa.
            try:
                google_play.acknowledge(app.package_name, data["product_id"], token)
                purchase.acknowledged = True
            except (google_play.GooglePlayError, google_play.InvalidPurchase):
                logger.exception("No se pudo reconocer la compra; se reintentará en la próxima verificación")

        for field, value in vars(purchase).items():
            setattr(subscription, field, value)
        subscription.google_response = raw
        subscription.save()
        return Response(_result(subscription))
