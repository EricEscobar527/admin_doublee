import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.applications.authentication import AppBearerTokenAuthentication, HasAppToken

from .images import InvalidImage, inspect_image
from .models import SupportAttachment, SupportTicket
from .realtime import broadcast
from .serializers import SupportTicketSerializer

logger = logging.getLogger(__name__)


def client_ip(request):
    if settings.TRUST_X_FORWARDED_FOR:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class SupportTicketCreateAPIView(APIView):
    authentication_classes = [AppBearerTokenAuthentication]
    permission_classes = [HasAppToken]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        files = [f for name in request.FILES for f in request.FILES.getlist(name)]
        if len(files) > settings.SUPPORT_MAX_FILES:
            return Response(
                {"files": [f"Máximo {settings.SUPPORT_MAX_FILES} imágenes."]}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SupportTicketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        checked = []
        for upload in files:
            try:
                checked.append((upload, *inspect_image(upload)))
            except InvalidImage as exc:
                return Response({"files": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

        ip = client_ip(request)
        if self._rate_limited(ip, serializer.validated_data["email"]):
            return Response(
                {"detail": "Demasiados reportes enviados. Intenta más tarde."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        payload = {key: request.data.get(key) for key in request.data if key not in request.FILES}
        with transaction.atomic():
            ticket = serializer.save(
                application=request.auth,
                payload=payload,
                ip_address=ip,
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
            )
            for upload, ext, content_type in checked:
                attachment = SupportAttachment(
                    ticket=ticket,
                    original_name=upload.name[:255],
                    content_type=content_type,
                    size=upload.size,
                )
                attachment.file.save(f"image.{ext}", upload, save=False)
                attachment.save()
            transaction.on_commit(lambda: broadcast("ticket.created", ticket.pk))

        logger.info("Ticket %s de %s creado (%s imágenes)", ticket.folio, ticket.application.code, len(checked))
        return Response({"id": str(ticket.public_id), "folio": ticket.folio}, status=status.HTTP_201_CREATED)

    def _rate_limited(self, ip, email):
        since = timezone.now() - timedelta(hours=1)
        recent = SupportTicket.objects.filter(created_at__gte=since)
        if ip and recent.filter(ip_address=ip).count() >= settings.SUPPORT_RATE_LIMIT_IP_PER_HOUR:
            return True
        return recent.filter(email=email).count() >= settings.SUPPORT_RATE_LIMIT_EMAIL_PER_HOUR
