from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.support.models import SupportTicket

from .models import Application


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
