from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.applications.models import Application

from . import google_play
from .models import Subscription

URL = "/api/subscriptions/verify"
PACKAGE = "cloud.doublee.viajeok"
PRODUCT = "viajeok_mensual"


def google_response(
    state="SUBSCRIPTION_STATE_ACTIVE", days=30, trial=False, acknowledged=True, product=PRODUCT, plan="mensual"
):
    expiry = (timezone.now() + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.123Z")
    offer = {"basePlanId": plan, "offerId": "prueba-1-mes"} if trial else {"basePlanId": plan}
    item = {
        "productId": product,
        "expiryTime": expiry,
        "offerDetails": offer,
        "autoRenewingPlan": {"autoRenewEnabled": state == "SUBSCRIPTION_STATE_ACTIVE"},
        "offerPhase": {"freeTrial": {}} if trial else {"basePrice": {}},
        "latestSuccessfulOrderId": "GPA.1234-5678",
    }
    return {
        "subscriptionState": state,
        "acknowledgementState": "ACKNOWLEDGEMENT_STATE_ACKNOWLEDGED" if acknowledged else "ACKNOWLEDGEMENT_STATE_PENDING",
        "lineItems": [item],
    }


class VerifyTests(TestCase):
    def setUp(self):
        self.app = Application.objects.create(
            name="ViajeOK", code="viajeok", api_token="tok", package_name=PACKAGE, subscription_product_id=PRODUCT
        )

    def post(self, token="purchase-token-abc", **extra):
        body = {"package_name": PACKAGE, "product_id": PRODUCT, "purchase_token": token, "install_id": "inst-1", **extra}
        return self.client.post(URL, body, content_type="application/json", HTTP_AUTHORIZATION="Bearer tok")

    @mock.patch.object(google_play, "acknowledge")
    @mock.patch.object(google_play, "get_subscription")
    def test_active_trial_purchase(self, get_sub, ack):
        get_sub.return_value = google_response(trial=True)
        response = self.post()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["active"])
        self.assertTrue(body["in_trial"])
        self.assertRegex(body["expires_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        get_sub.assert_called_once_with(PACKAGE, "purchase-token-abc")
        ack.assert_not_called()
        sub = Subscription.objects.get()
        self.assertEqual((sub.install_id, sub.latest_order_id, sub.application), ("inst-1", "GPA.1234-5678", self.app))

    @mock.patch.object(google_play, "acknowledge")
    @mock.patch.object(google_play, "get_subscription")
    def test_all_base_plans_are_accepted(self, get_sub, ack):
        cases = [  # (plan base, días hasta el vencimiento que da Google, ¿prueba gratis?)
            ("mensual", 30, True),
            ("trimestral", 91, False),
            ("anual", 365, False),
        ]
        for plan, days, trial in cases:
            with self.subTest(plan=plan):
                get_sub.return_value = google_response(plan=plan, days=days, trial=trial)
                body = self.post(token=f"token-{plan}").json()
                self.assertTrue(body["active"])
                self.assertEqual(body["in_trial"], trial)
                expires = timezone.datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00"))
                self.assertAlmostEqual((expires - timezone.now()).days, days, delta=1)
                sub = Subscription.objects.get(purchase_token=f"token-{plan}")
                self.assertEqual(sub.base_plan_id, plan)
                self.assertEqual(sub.offer_id, "prueba-1-mes" if trial else "")

    @mock.patch.object(google_play, "acknowledge")
    @mock.patch.object(google_play, "get_subscription")
    def test_acknowledges_pending_purchase(self, get_sub, ack):
        get_sub.return_value = google_response(acknowledged=False)
        self.assertTrue(self.post().json()["active"])
        ack.assert_called_once_with(PACKAGE, PRODUCT, "purchase-token-abc")
        self.assertTrue(Subscription.objects.get().acknowledged)

    @mock.patch.object(google_play, "get_subscription")
    def test_canceled_but_paid_keeps_access(self, get_sub):
        get_sub.return_value = google_response(state="SUBSCRIPTION_STATE_CANCELED", days=5)
        self.assertTrue(self.post().json()["active"])

    @mock.patch.object(google_play, "get_subscription")
    def test_expired_is_inactive(self, get_sub):
        get_sub.return_value = google_response(state="SUBSCRIPTION_STATE_EXPIRED", days=-1)
        self.assertEqual(self.post().json(), {"active": False})

    @mock.patch.object(google_play, "get_subscription")
    def test_invalid_token(self, get_sub):
        get_sub.side_effect = google_play.InvalidPurchase("404")
        self.assertEqual(self.post().json(), {"active": False})
        self.assertEqual(Subscription.objects.get().state, Subscription.INVALID)

    @mock.patch.object(google_play, "get_subscription")
    def test_other_product_is_invalid(self, get_sub):
        get_sub.return_value = google_response(product="otro_producto")
        self.assertEqual(self.post().json(), {"active": False})

    @mock.patch.object(google_play, "get_subscription")
    def test_google_down_returns_503(self, get_sub):
        get_sub.side_effect = google_play.GooglePlayError("timeout")
        self.assertEqual(self.post().status_code, 503)
        self.assertFalse(Subscription.objects.exists())

    @mock.patch.object(google_play, "get_subscription")
    def test_rejects_wrong_package_or_product(self, get_sub):
        self.assertEqual(self.post(package_name="com.otra.app").status_code, 400)
        self.assertEqual(self.post(product_id="otro").status_code, 400)
        get_sub.assert_not_called()

    @mock.patch.object(google_play, "get_subscription")
    def test_recent_verification_is_cached(self, get_sub):
        get_sub.return_value = google_response()
        self.post()
        self.post()
        self.assertEqual(get_sub.call_count, 1)
        Subscription.objects.update(last_verified_at=timezone.now() - timedelta(minutes=5))
        self.post()
        self.assertEqual(get_sub.call_count, 2)

    def test_requires_token(self):
        response = self.client.post(URL, {}, content_type="application/json")
        self.assertEqual(response.status_code, 401)

    def test_missing_service_account_is_503(self):
        google_play._credentials.cache_clear()
        with self.settings(GOOGLE_PLAY_SERVICE_ACCOUNT_FILE="/no/existe.json"):
            self.assertEqual(self.post().status_code, 503)
        google_play._credentials.cache_clear()


class PanelTests(TestCase):
    def test_list_and_detail(self):
        app = Application.objects.create(name="ViajeOK", code="viajeok")
        sub = Subscription.objects.create(
            application=app, purchase_token="t" * 40, package_name=PACKAGE, product_id=PRODUCT,
            state="SUBSCRIPTION_STATE_ACTIVE", active=True, in_trial=True,
        )
        get_user_model().objects.create_user("admin", "admin@example.com", "S3gura!pass")
        self.client.post(reverse("accounts:login"), {"username": "admin", "password": "S3gura!pass"})
        response = self.client.get(reverse("subscriptions:list"))
        self.assertContains(response, "En prueba")
        self.assertEqual(response.context["stats"]["trial"], 1)
        self.assertContains(self.client.get(reverse("subscriptions:detail", args=[sub.pk])), PRODUCT)
