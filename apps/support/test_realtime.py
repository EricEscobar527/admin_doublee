import io
import shutil
import tempfile

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.jwt_auth import user_from_jwt_cookies
from apps.applications.models import Application

from .consumers import SupportTicketsConsumer
from .models import SupportTicket
from .realtime import GROUP

IN_MEMORY = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
MEDIA = tempfile.mkdtemp()


class AdminStub:
    is_authenticated = True
    is_admin = True


@override_settings(CHANNEL_LAYERS=IN_MEMORY)
class ConsumerTests(SimpleTestCase):
    async def test_rejects_anonymous(self):
        communicator = WebsocketCommunicator(SupportTicketsConsumer.as_asgi(), "/ws/support/")
        communicator.scope["user"] = AnonymousUser()
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4401)

    async def test_admin_receives_group_events(self):
        communicator = WebsocketCommunicator(SupportTicketsConsumer.as_asgi(), "/ws/support/")
        communicator.scope["user"] = AdminStub()
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await get_channel_layer().group_send(GROUP, {"type": "ticket.event", "payload": {"event": "ticket.created"}})
        self.assertEqual(await communicator.receive_json_from(), {"event": "ticket.created"})
        await communicator.disconnect()


@override_settings(
    CHANNEL_LAYERS=IN_MEMORY,
    MEDIA_ROOT=MEDIA,
    SUPPORT_RATE_LIMIT_IP_PER_HOUR=100,
    SUPPORT_RATE_LIMIT_EMAIL_PER_HOUR=100,
)
class BroadcastTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.app = Application.objects.create(name="App en vivo", code="app-en-vivo", api_token="tok")
        self.layer = get_channel_layer()
        self.channel = async_to_sync(self.layer.new_channel)()
        async_to_sync(self.layer.group_add)(GROUP, self.channel)

    def receive(self):
        return async_to_sync(self.layer.receive)(self.channel)["payload"]

    def test_api_ticket_is_broadcast(self):
        buf = io.BytesIO()
        Image.new("RGB", (10, 10)).save(buf, "PNG")
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/support/tickets",
                {
                    "issue": "wrong_calculation",
                    "email": "a@example.com",
                    "phone_model": "Realme 12",
                    "images": SimpleUploadedFile("a.png", buf.getvalue(), "image/png"),
                },
                HTTP_AUTHORIZATION="Bearer tok",
            )
        self.assertEqual(response.status_code, 201)
        payload = self.receive()
        self.assertEqual(payload["event"], "ticket.created")
        self.assertEqual(payload["ticket"]["application"], "App en vivo")
        self.assertEqual(payload["stats"]["total"], 1)
        self.assertIn("Realme 12", payload["html"]["row"])
        self.assertIn('data-ticket-id="%s"' % payload["ticket"]["id"], payload["html"]["latest"])

    def test_status_change_is_broadcast(self):
        user = get_user_model().objects.create_user("admin", "admin@example.com", "S3gura!pass")
        ticket = SupportTicket.objects.create(application=self.app, issue="other", email="b@example.com")
        refresh = RefreshToken.for_user(user)
        self.client.cookies["access_token"] = str(refresh.access_token)
        self.client.post(reverse("support:update", args=[ticket.pk]), {"status": "resolved"})
        payload = self.receive()
        self.assertEqual(payload["event"], "ticket.updated")
        self.assertEqual(payload["ticket"]["status"], "resolved")

    def test_delete_is_broadcast(self):
        user = get_user_model().objects.create_user("admin", "admin@example.com", "S3gura!pass")
        ticket = SupportTicket.objects.create(application=self.app, issue="other", email="b@example.com")
        self.client.cookies["access_token"] = str(RefreshToken.for_user(user).access_token)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("support:delete", args=[ticket.pk]))
        payload = self.receive()
        self.assertEqual(payload, {"event": "ticket.deleted", "ticket": {"id": ticket.pk, "folio": ticket.folio}, "stats": payload["stats"]})
        self.assertEqual(payload["stats"]["total"], 0)


class WebSocketCookieAuthTests(TestCase):
    def test_user_from_cookies(self):
        user = get_user_model().objects.create_user("admin", "admin@example.com", "S3gura!pass")
        refresh = RefreshToken.for_user(user)
        self.assertEqual(user_from_jwt_cookies({"access_token": str(refresh.access_token)})[0], user)
        found, new_access = user_from_jwt_cookies({"access_token": "expirado", "refresh_token": str(refresh)})
        self.assertEqual(found, user)
        self.assertIsNotNone(new_access)
        self.assertEqual(user_from_jwt_cookies({}), (None, None))
