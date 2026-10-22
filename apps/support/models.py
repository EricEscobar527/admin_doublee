import uuid

from django.db import models


def attachment_upload_to(instance, filename):
    # El nombre lo decide el servidor; nunca se usa el nombre que manda el cliente.
    ext = filename.rsplit(".", 1)[-1].lower()
    return f"support/{instance.ticket.created_at:%Y/%m}/{instance.ticket.public_id}/{uuid.uuid4().hex}.{ext}"


class SupportTicket(models.Model):
    class Issue(models.TextChoices):
        # TODO: ajustar a los 3 valores exactos que envía la app.
        APP_ERROR = "app_error", "Error en la app"
        ACCOUNT = "account", "Cuenta / acceso"
        OTHER = "other", "Otro"

    class Status(models.TextChoices):
        NEW = "new", "Nuevo"
        IN_REVIEW = "in_review", "En revisión"
        RESOLVED = "resolved", "Resuelto"

    public_id = models.UUIDField("folio", default=uuid.uuid4, unique=True, editable=False)
    # Se asigna según el token Bearer con el que llegó el ticket.
    application = models.ForeignKey(
        "applications.Application",
        on_delete=models.PROTECT,
        related_name="support_tickets",
        verbose_name="aplicación",
    )
    issue = models.CharField("tipo", max_length=30, choices=Issue.choices)
    email = models.EmailField("correo")
    name = models.CharField("nombre", max_length=150, blank=True)
    phone = models.CharField("teléfono", max_length=30, blank=True)
    message = models.TextField("mensaje", blank=True)

    # Información del dispositivo que envía la app
    device_time = models.DateTimeField("hora del dispositivo", null=True, blank=True)
    device_time_raw = models.CharField("hora del dispositivo (original)", max_length=40, blank=True)
    app_version = models.CharField("versión app", max_length=30, blank=True)
    app_build = models.CharField("build app", max_length=30, blank=True)
    android_version = models.CharField("versión Android", max_length=30, blank=True)
    android_sdk = models.CharField("SDK Android", max_length=10, blank=True)
    device_manufacturer = models.CharField("fabricante", max_length=80, blank=True)
    device_brand = models.CharField("marca", max_length=80, blank=True)
    device_model = models.CharField("modelo", max_length=80, blank=True)

    # Todos los campos de texto recibidos, para no perder nada que la app agregue después.
    payload = models.JSONField("datos recibidos", default=dict, blank=True)
    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.CharField("user agent", max_length=255, blank=True)

    status = models.CharField("estatus", max_length=20, choices=Status.choices, default=Status.NEW)
    admin_notes = models.TextField("notas internas", blank=True)
    created_at = models.DateTimeField("recibido", auto_now_add=True)
    updated_at = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        db_table = "soporte"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["email", "created_at"]),
            models.Index(fields=["ip_address", "created_at"]),
        ]

    def __str__(self):
        return f"#{self.pk} {self.get_issue_display()} - {self.email}"

    @property
    def folio(self):
        return f"SOP-{self.pk:06d}"


class SupportAttachment(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="attachments")
    file = models.ImageField("imagen", upload_to=attachment_upload_to, width_field="width", height_field="height")
    original_name = models.CharField("nombre original", max_length=255, blank=True)
    content_type = models.CharField("tipo", max_length=50)
    size = models.PositiveIntegerField("tamaño (bytes)")
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "soporte_imagenes"
        ordering = ["id"]

    def __str__(self):
        return self.original_name or self.file.name
