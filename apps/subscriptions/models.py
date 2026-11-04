import hashlib

from django.db import models
from django.utils import timezone


def hash_token(purchase_token):
    return hashlib.sha256(purchase_token.encode()).hexdigest()


class Subscription(models.Model):
    """Una compra de Google Play, identificada por su purchase_token (la app no tiene login)."""

    # state guarda SubscriptionPurchaseV2.subscriptionState, o INVALID si Google rechaza el token.
    INVALID = "INVALID"

    application = models.ForeignKey(
        "applications.Application", on_delete=models.PROTECT, related_name="subscriptions", verbose_name="aplicación"
    )
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    purchase_token = models.TextField("token de compra")
    package_name = models.CharField("paquete", max_length=150)
    product_id = models.CharField("producto", max_length=100)
    # lineItems[].offerDetails: plan base (mensual, trimestral, anual) y oferta (p. ej. prueba-1-mes)
    base_plan_id = models.CharField("plan base", max_length=100, blank=True)
    offer_id = models.CharField("oferta", max_length=100, blank=True)
    install_id = models.CharField("install_id", max_length=64, blank=True)

    state = models.CharField("estado", max_length=50)
    active = models.BooleanField("activa", default=False)
    in_trial = models.BooleanField("en prueba", default=False)
    auto_renewing = models.BooleanField("renovación automática", default=False)
    acknowledged = models.BooleanField("reconocida", default=False)
    test_purchase = models.BooleanField("compra de prueba", default=False)
    expires_at = models.DateTimeField("vence", null=True, blank=True)
    latest_order_id = models.CharField("orden", max_length=100, blank=True)
    linked_purchase_token = models.TextField(blank=True)
    google_response = models.JSONField("respuesta de Google", default=dict, blank=True)

    last_verified_at = models.DateTimeField("última verificación", default=timezone.now)
    created_at = models.DateTimeField("creada", auto_now_add=True)
    updated_at = models.DateTimeField("actualizada", auto_now=True)

    class Meta:
        db_table = "suscripciones"
        ordering = ["-last_verified_at"]
        indexes = [
            models.Index(fields=["application", "active"]),
            models.Index(fields=["install_id"]),
        ]

    def __str__(self):
        return f"{self.product_id} · {self.state}"

    def save(self, *args, **kwargs):
        self.token_hash = hash_token(self.purchase_token)
        super().save(*args, **kwargs)

    @property
    def short_token(self):
        return f"{self.purchase_token[:10]}…{self.purchase_token[-6:]}"

    @property
    def state_display(self):
        return {
            "SUBSCRIPTION_STATE_ACTIVE": "Activa",
            "SUBSCRIPTION_STATE_IN_GRACE_PERIOD": "Periodo de gracia",
            "SUBSCRIPTION_STATE_ON_HOLD": "En espera (pago fallido)",
            "SUBSCRIPTION_STATE_PAUSED": "Pausada",
            "SUBSCRIPTION_STATE_CANCELED": "Cancelada",
            "SUBSCRIPTION_STATE_EXPIRED": "Vencida",
            "SUBSCRIPTION_STATE_PENDING": "Pago pendiente",
            "SUBSCRIPTION_STATE_PENDING_PURCHASE_CANCELED": "Compra pendiente cancelada",
            self.INVALID: "Token inválido",
        }.get(self.state, self.state)
