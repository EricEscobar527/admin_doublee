from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from .models import SupportTicket

# Campos obligatorios adicionales según el tipo de reporte.
REQUIRED_FIELDS_BY_ISSUE = {
    SupportTicket.Issue.OTHER: ["message"],
}

DEVICE_FIELDS = [
    "app_version",
    "app_build",
    "android_version",
    "android_sdk",
    "device_manufacturer",
    "device_brand",
    "device_model",
]


class SupportTicketSerializer(serializers.ModelSerializer):
    device_time = serializers.CharField(required=False, allow_blank=True, max_length=40)
    # La app limita el texto a 1000 caracteres; se valida igual aquí.
    message = serializers.CharField(required=False, allow_blank=True, max_length=1000)

    class Meta:
        model = SupportTicket
        fields = ["issue", "email", "name", "phone", "phone_model", "message", "device_time", *DEVICE_FIELDS]
        extra_kwargs = {name: {"required": False} for name in ["name", "phone", "phone_model", *DEVICE_FIELDS]}

    def validate_device_time(self, value):
        if not value:
            return None
        parsed = parse_datetime(value)
        if parsed is None or parsed.tzinfo is None:
            raise serializers.ValidationError("Formato ISO 8601 con zona horaria, ej. 2026-10-22T13:05:09-06:00.")
        return parsed

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        missing = {
            field: "Este campo es obligatorio para este tipo de reporte."
            for field in REQUIRED_FIELDS_BY_ISSUE.get(attrs.get("issue"), [])
            if not str(attrs.get(field) or "").strip()
        }
        if missing:
            raise serializers.ValidationError(missing)
        return attrs

    def create(self, validated_data):
        raw_time = self.initial_data.get("device_time", "")
        validated_data["device_time_raw"] = raw_time[:40] if isinstance(raw_time, str) else ""
        return super().create(validated_data)
