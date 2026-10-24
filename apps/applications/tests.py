from datetime import datetime
from datetime import timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.support.models import SupportTicket

from .models import Application


class AppConfigAPITests(TestCase):
    url = "/api/app/config"

    def test_returns_config_of_token_app(self):
        Application.objects.create(
            name="ViajeOK",
            code="viajeok",
            api_token="tok",
            beta_ends_at=datetime(2026, 12, 1, 6, 0, tzinfo=dt_timezone.utc),
            beta_message="Versión beta gratuita hasta el 1 de diciembre",
            subscription_product_id="viajeok_mensual",
            min_supported_build=3,
        )
        response = self.client.get(self.url, HTTP_AUTHORIZATION="Bearer tok")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "paywall_enabled": False,
                "beta_ends_at": "2026-12-01T00:00:00-06:00",
                "beta_message": "Versión beta gratuita hasta el 1 de diciembre",
                "subscription_product_id": "viajeok_mensual",
                "min_supported_build": 3,
            },
        )
        self.assertIn("max-age=300", response["Cache-Control"])

    def test_empty_config_and_auth(self):
        Application.objects.create(name="B", code="b", api_token="tok2")
        body = self.client.get(self.url + "/", HTTP_AUTHORIZATION="Bearer tok2").json()
        self.assertEqual((body["beta_ends_at"], body["min_supported_build"], body["paywall_enabled"]), (None, None, False))
        self.assertEqual(self.client.get(self.url).status_code, 401)


class PrivacyPageTests(TestCase):
    def test_public_without_login(self):
        response = self.client.get("/viajeok/privacidad/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Política de privacidad de ViajeOK")
        self.assertContains(response, "se descartan al cerrarse la oferta")
        self.assertNotContains(response, "PENDIENTE: texto del aviso")
        self.assertContains(response, "PENDIENTE: correo de contacto")
        with self.settings(PRIVACY_CONTACT_EMAIL="privacidad@doublee.cloud"):
            self.assertContains(self.client.get("/viajeok/privacidad/"), "mailto:privacidad@doublee.cloud")


class ApplicationCRUDTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_user("admin", "admin@example.com", "S3gura!pass")
        self.client.post(reverse("accounts:login"), {"username": "admin", "password": "S3gura!pass"})

    def test_requires_login(self):
        self.client.post(reverse("accounts:logout"))
        self.assertEqual(self.client.get(reverse("applications:list")).status_code, 302)

    def test_create_generates_token(self):
        response = self.client.post(
            reverse("applications:create"),
            {"name": "Nueva App", "code": "Nueva-App", "color": "#ff0000", "is_active": "on"},
        )
        application = Application.objects.get(code="nueva-app")
        self.assertRedirects(response, reverse("applications:edit", args=[application.pk]))
        self.assertGreaterEqual(len(application.api_token), 40)

    def test_edit_remote_config(self):
        application = Application.objects.create(name="A", code="a")
        data = {
            "name": "A", "code": "a", "color": "#000000", "is_active": "on",
            "paywall_enabled": "on", "beta_ends_at": "2026-12-01T00:00", "beta_message": "Beta",
            "subscription_product_id": "viajeok_mensual", "min_supported_build": "3",
        }
        self.client.post(reverse("applications:edit", args=[application.pk]), data)
        application.refresh_from_db()
        self.assertTrue(application.paywall_enabled)
        self.assertEqual(application.min_supported_build, 3)
        self.assertEqual(application.beta_ends_at, datetime(2026, 12, 1, 6, 0, tzinfo=dt_timezone.utc))

    def test_paywall_requires_product(self):
        application = Application.objects.create(name="A", code="a")
        response = self.client.post(
            reverse("applications:edit", args=[application.pk]),
            {"name": "A", "code": "a", "color": "#000000", "paywall_enabled": "on"},
        )
        self.assertIn("subscription_product_id", response.context["form"].errors)

    def test_rejects_duplicate_code_and_bad_color(self):
        Application.objects.create(name="A", code="dup")
        response = self.client.post(reverse("applications:create"), {"name": "B", "code": "dup", "color": "rojo"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("code", response.context["form"].errors)
        self.assertIn("color", response.context["form"].errors)

    def test_edit(self):
        application = Application.objects.create(name="A", code="a")
        self.client.post(
            reverse("applications:edit", args=[application.pk]), {"name": "A2", "code": "a", "color": "#000000"}
        )
        application.refresh_from_db()
        self.assertEqual(application.name, "A2")
        self.assertFalse(application.is_active)

    def test_regenerate_token(self):
        application = Application.objects.create(name="A", code="a")
        old = application.api_token
        self.client.post(reverse("applications:regenerate_token", args=[application.pk]))
        application.refresh_from_db()
        self.assertNotEqual(application.api_token, old)

    def test_delete_without_tickets(self):
        application = Application.objects.create(name="A", code="a")
        self.client.post(reverse("applications:delete", args=[application.pk]))
        self.assertFalse(Application.objects.filter(pk=application.pk).exists())

    def test_delete_with_tickets_is_blocked(self):
        application = Application.objects.create(name="A", code="a")
        SupportTicket.objects.create(application=application, issue="other", email="x@example.com")
        self.client.post(reverse("applications:delete", args=[application.pk]))
        self.assertTrue(Application.objects.filter(pk=application.pk).exists())
