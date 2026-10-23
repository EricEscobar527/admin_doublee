from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .realtime import GROUP


class SupportTicketsConsumer(AsyncJsonWebsocketConsumer):
    """Canal en vivo del panel: solo admins con sesión JWT válida."""

    async def connect(self):
        user = self.scope.get("user")
        if not (user and user.is_authenticated and user.is_admin):
            await self.close(code=4401)
            return
        await self.channel_layer.group_add(GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(GROUP, self.channel_name)

    async def ticket_event(self, event):
        await self.send_json(event["payload"])
