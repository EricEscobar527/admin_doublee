"""Avisos en vivo al panel (WebSocket) cuando llega o cambia un ticket."""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Count
from django.template.loader import render_to_string

from .models import SupportTicket
from .stats import ticket_stats

logger = logging.getLogger(__name__)

GROUP = "support_tickets"


def _payload(event, ticket_id):
    ticket = (
        SupportTicket.objects.select_related("application")
        .annotate(image_count=Count("attachments"))
        .get(pk=ticket_id)
    )
    return {
        "event": event,
        "ticket": {
            "id": ticket.pk,
            "folio": ticket.folio,
            "application_id": ticket.application_id,
            "application": ticket.application.name,
            "issue": ticket.issue,
            "issue_display": ticket.get_issue_display(),
            "status": ticket.status,
            "email": ticket.email,
        },
        "stats": ticket_stats(),
        # HTML renderizado con las mismas plantillas de la página (ya escapado).
        "html": {
            "row": render_to_string("support/_row.html", {"ticket": ticket}),
            "latest": render_to_string("dashboard/_latest_item.html", {"ticket": ticket}),
        },
    }


def _send(payload):
    async_to_sync(get_channel_layer().group_send)(GROUP, {"type": "ticket.event", "payload": payload})


def broadcast(event, ticket_id):
    """Nunca rompe la petición: si Redis no responde, solo se registra el error."""
    try:
        _send(_payload(event, ticket_id))
    except Exception:
        logger.exception("No se pudo enviar el aviso en vivo del ticket %s", ticket_id)


def broadcast_deleted(ticket_id, folio):
    try:
        _send({"event": "ticket.deleted", "ticket": {"id": ticket_id, "folio": folio}, "stats": ticket_stats()})
    except Exception:
        logger.exception("No se pudo enviar el aviso en vivo del ticket %s", ticket_id)
