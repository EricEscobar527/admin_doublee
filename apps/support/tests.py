import io
import os
import shutil
import tempfile
from datetime import timezone

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.applications.models import Application

from .models import SupportAttachment, SupportTicket

TOKEN = "test-token"
MEDIA = tempfile.mkdtemp()


def png(name="captura.png"):
    buf = io.BytesIO()
    Image.new("RGB", (40, 60), "red").save(buf, "PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def payload(**extra):
    data = {
        "issue": SupportTicket.Issue.WRONG_CALCULATION,
        "email": "Cliente@Example.com",
        "phone_model": "Samsung Galaxy A54",
        "device_time": "2026-10-22T13:05:09-06:00",
        "app_version": "1.0.0",
        "app_build": "1",
        "android_version": "16",
        "android_sdk": "36",
        "device_manufacturer": "realme",
        "device_brand": "realme",
        "device_model": "RMX5101",
    }
    data.update(extra)
    return data


@override_settings(
    MEDIA_ROOT=MEDIA,
    SUPPORT_RATE_LIMIT_IP_PER_HOUR=100,
    SUPPORT_RATE_LIMIT_EMAIL_PER_HOUR=100,
)
class SupportTicketAPITests(TestCase):
    url = "/api/support/tickets"

    @classmethod
    def setUpTestData(cls):
        cls.app = Application.objects.create(name="Pruebas", code="pruebas", api_token=TOKEN)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def post(self, data, token=TOKEN):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
        return self.client.post(self.url, data, **headers)

    def test_requires_bearer_token(self):
        self.assertEqual(self.post(payload(), token=None).status_code, 401)
        self.assertEqual(self.post(payload(), token="otro").status_code, 401)

    def test_inactive_application_is_rejected(self):
        Application.objects.filter(pk=self.app.pk).update(is_active=False)
        self.assertEqual(self.post(payload()).status_code, 401)

    def test_ticket_belongs_to_token_application(self):
        other = Application.objects.create(name="Otra", code="otra")
        response = self.post(payload(), token=other.api_token)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(SupportTicket.objects.get(public_id=response.json()["id"]).application, other)

    def test_creates_ticket_with_images_and_device_info(self):
        response = self.post(payload(images=[png(), png("b.png")]))
        self.assertEqual(response.status_code, 201, response.content)
        ticket = SupportTicket.objects.get(public_id=response.json()["id"])
        self.assertEqual(ticket.application, self.app)
        self.assertEqual(ticket.email, "cliente@example.com")
        self.assertEqual(ticket.device_model, "RMX5101")
        self.assertEqual(ticket.device_time_raw, "2026-10-22T13:05:09-06:00")
        self.assertEqual(ticket.device_time.astimezone(timezone.utc).hour, 19)
        self.assertEqual(ticket.attachments.count(), 2)
        self.assertEqual(ticket.attachments.first().content_type, "image/png")
        self.assertEqual(ticket.payload["android_sdk"], "36")

    def test_accepts_trailing_slash(self):
        response = self.client.post(self.url + "/", payload(), HTTP_AUTHORIZATION=f"Bearer {TOKEN}")
        self.assertEqual(response.status_code, 201)

    def test_rejects_invalid_issue_and_email(self):
        response = self.post(payload(issue="nope", email="no-es-correo"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("issue", response.json())
        self.assertIn("email", response.json())

    def test_message_required_only_for_other(self):
        response = self.post(payload(issue=SupportTicket.Issue.OTHER, message=""))
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.json())
        self.assertEqual(self.post(payload(issue=SupportTicket.Issue.OTHER, message="Ayuda")).status_code, 201)
        self.assertEqual(self.post(payload(issue=SupportTicket.Issue.ALERT_NOT_SHOWN)).status_code, 201)

    def test_message_and_phone_model_max_length(self):
        self.assertEqual(self.post(payload(message="x" * 1001)).status_code, 400)
        self.assertEqual(self.post(payload(phone_model="x" * 101)).status_code, 400)

    def test_saves_phone_model(self):
        response = self.post(payload())
        ticket = SupportTicket.objects.get(public_id=response.json()["id"])
        self.assertEqual(ticket.phone_model, "Samsung Galaxy A54")
        self.assertEqual(ticket.message, "")

    def test_rejects_fake_image(self):
        fake = SimpleUploadedFile("foto.jpg", b"<?php echo 1; ?>", content_type="image/jpeg")
        self.assertEqual(self.post(payload(images=[fake])).status_code, 400)
        self.assertFalse(SupportTicket.objects.exists())

    def test_rejects_more_than_five_files(self):
        self.assertEqual(self.post(payload(images=[png() for _ in range(6)])).status_code, 400)

    @override_settings(SUPPORT_MAX_FILE_SIZE=100)
    def test_rejects_big_file(self):
        self.assertEqual(self.post(payload(images=[png()])).status_code, 400)

    @override_settings(SUPPORT_RATE_LIMIT_EMAIL_PER_HOUR=2)
    def test_rate_limit_by_email(self):
        self.assertEqual(self.post(payload()).status_code, 201)
        self.assertEqual(self.post(payload()).status_code, 201)
        self.assertEqual(self.post(payload()).status_code, 429)


@override_settings(MEDIA_ROOT=MEDIA, SUPPORT_RATE_LIMIT_IP_PER_HOUR=100, SUPPORT_RATE_LIMIT_EMAIL_PER_HOUR=100)
class TicketDeleteTests(TestCase):
    def setUp(self):
        Application.objects.create(name="Pruebas", code="pruebas", api_token=TOKEN)
        get_user_model().objects.create_user("admin", "admin@example.com", "S3gura!pass")
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/support/tickets", payload(images=[png(), png("b.png")]), HTTP_AUTHORIZATION=f"Bearer {TOKEN}"
            )
        self.ticket = SupportTicket.objects.get(public_id=response.json()["id"])
        self.paths = [a.file.path for a in self.ticket.attachments.all()]
        self.url = reverse("support:delete", args=[self.ticket.pk])

    def login(self):
        self.client.post(reverse("accounts:login"), {"username": "admin", "password": "S3gura!pass"})

    def test_deletes_ticket_images_and_files(self):
        self.assertTrue(all(os.path.exists(p) for p in self.paths))
        self.login()
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url)
        self.assertRedirects(response, reverse("support:list"))
        self.assertFalse(SupportTicket.objects.filter(pk=self.ticket.pk).exists())
        self.assertFalse(SupportAttachment.objects.exists())
        self.assertFalse(any(os.path.exists(p) for p in self.paths))
        self.assertFalse(os.path.exists(os.path.dirname(self.paths[0])))

    def test_get_is_not_allowed(self):
        self.login()
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertTrue(SupportTicket.objects.filter(pk=self.ticket.pk).exists())

    def test_requires_login(self):
        self.assertEqual(self.client.post(self.url).status_code, 302)
        self.assertTrue(SupportTicket.objects.filter(pk=self.ticket.pk).exists())


class PanelAuthTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("admin", "admin@example.com", "S3gura!pass")

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("support:list"))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('support:list')}")

    def test_login_sets_jwt_cookies_and_opens_dashboard(self):
        response = self.client.post(reverse("accounts:login"), {"username": "admin", "password": "S3gura!pass"})
        self.assertRedirects(response, reverse("dashboard:home"))
        self.assertIn("access_token", response.cookies)
        self.assertTrue(response.cookies["access_token"]["httponly"])
        self.assertEqual(self.client.get(reverse("support:list")).status_code, 200)

    def test_refresh_cookie_renews_expired_access(self):
        self.client.post(reverse("accounts:login"), {"username": "admin", "password": "S3gura!pass"})
        self.client.cookies["access_token"] = "expirado"
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.cookies["access_token"].value, "expirado")

    def test_wrong_password(self):
        response = self.client.post(reverse("accounts:login"), {"username": "admin", "password": "mala"})
        self.assertContains(response, "incorrectos")

    def test_logout_blacklists_refresh(self):
        self.client.post(reverse("accounts:login"), {"username": "admin", "password": "S3gura!pass"})
        self.client.post(reverse("accounts:logout"))
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 302)

    def test_ticket_detail_shows_device_info(self):
        application = Application.objects.create(name="Mi App", code="mi-app")
        ticket = SupportTicket.objects.create(
            application=application, issue="other", email="x@example.com", device_model="RMX5101"
        )
        self.client.post(reverse("accounts:login"), {"username": "admin", "password": "S3gura!pass"})
        response = self.client.get(reverse("support:detail", args=[ticket.pk]))
        self.assertContains(response, "RMX5101")
        self.assertContains(response, "Mi App")
        list_response = self.client.get(reverse("support:list"), {"app": application.pk})
        self.assertContains(list_response, ticket.folio)
