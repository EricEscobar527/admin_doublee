from django.urls import path

from .consumers import SupportTicketsConsumer

websocket_urlpatterns = [
    path("ws/support/", SupportTicketsConsumer.as_asgi()),
]
