"""Cliente mínimo de la Google Play Developer API (androidpublisher v3) con cuenta de servicio."""
import os
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

SCOPES = ["https://www.googleapis.com/auth/androidpublisher"]
ACCESS_STATES = {"SUBSCRIPTION_STATE_ACTIVE", "SUBSCRIPTION_STATE_IN_GRACE_PERIOD"}


class GooglePlayError(Exception):
    """Google no respondió o falta configuración: no se sabe el estado real."""


class InvalidPurchase(Exception):
    """Google confirma que el token no existe, no es de este paquete o no es de este producto."""


@lru_cache(maxsize=1)
def _credentials():
    path = settings.GOOGLE_PLAY_SERVICE_ACCOUNT_FILE
    if not path or not os.path.exists(path):
        raise GooglePlayError("Falta la llave de la cuenta de servicio (GOOGLE_PLAY_SERVICE_ACCOUNT_FILE).")
    from google.oauth2 import service_account

    return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)


def _service():
    # Se crea por llamada: los objetos de googleapiclient no son seguros entre hilos.
    from googleapiclient.discovery import build

    return build("androidpublisher", "v3", credentials=_credentials(), cache_discovery=False)


def _call(request):
    from googleapiclient.errors import HttpError

    try:
        return request.execute(num_retries=2)
    except HttpError as exc:
        if exc.resp.status in (400, 404, 410):
            raise InvalidPurchase(str(exc)) from exc
        raise GooglePlayError(str(exc)) from exc
    except OSError as exc:
        raise GooglePlayError(str(exc)) from exc


def get_subscription(package_name, purchase_token):
    return _call(_service().purchases().subscriptionsv2().get(packageName=package_name, token=purchase_token))


def acknowledge(package_name, product_id, purchase_token):
    # subscriptionsv2 no tiene acknowledge; Google indica usar el de purchases.subscriptions.
    _call(
        _service()
        .purchases()
        .subscriptions()
        .acknowledge(packageName=package_name, subscriptionId=product_id, token=purchase_token, body={})
    )


@dataclass
class PurchaseStatus:
    state: str
    active: bool
    in_trial: bool
    auto_renewing: bool
    acknowledged: bool
    test_purchase: bool
    expires_at: datetime | None
    latest_order_id: str
    linked_purchase_token: str


def parse_subscription(data, product_id):
    """Interpreta un SubscriptionPurchaseV2 para el producto pedido."""
    items = [item for item in data.get("lineItems", []) if item.get("productId") == product_id]
    if not items:
        raise InvalidPurchase(f"La compra no incluye el producto {product_id}.")

    expiries = [parse_datetime(item["expiryTime"]) for item in items if item.get("expiryTime")]
    expires_at = max((e for e in expiries if e), default=None)
    state = data.get("subscriptionState", "")
    # Cancelada = ya no se renueva, pero el usuario pagó hasta la fecha de vencimiento.
    still_paid = state == "SUBSCRIPTION_STATE_CANCELED" and expires_at is not None and expires_at > timezone.now()

    return PurchaseStatus(
        state=state,
        active=state in ACCESS_STATES or still_paid,
        in_trial=any("freeTrial" in (item.get("offerPhase") or {}) for item in items),
        auto_renewing=any((item.get("autoRenewingPlan") or {}).get("autoRenewEnabled") for item in items),
        acknowledged=data.get("acknowledgementState") == "ACKNOWLEDGEMENT_STATE_ACKNOWLEDGED",
        test_purchase="testPurchase" in data,
        expires_at=expires_at,
        latest_order_id=items[0].get("latestSuccessfulOrderId") or data.get("latestOrderId", ""),
        linked_purchase_token=data.get("linkedPurchaseToken", ""),
    )
