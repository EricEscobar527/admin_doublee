import secrets

from django.core.validators import RegexValidator
from django.db import models


def generate_api_token():
    return secrets.token_urlsafe(32)


class Application(models.Model):
    name = models.CharField("nombre", max_length=100)
    code = models.SlugField(
        "identificador",
        max_length=50,
        unique=True,
        help_text="Clave corta y única, ej. analisis-viaje. Solo minúsculas, números y guiones.",
    )
    package_name = models.CharField(
        "paquete Android",
        max_length=150,
        blank=True,
        help_text="Ej. com.doublee.analisisviaje",
    )
    description = models.TextField("descripción", blank=True)
    color = models.CharField(
        "color",
        max_length=7,
        default="#2563eb",
        validators=[RegexValidator(r"^#[0-9a-fA-F]{6}$", "Usa un color hexadecimal, ej. #2563eb.")],
        help_text="Color de la etiqueta en los tickets.",
    )
    api_token = models.CharField("token API", max_length=64, unique=True, default=generate_api_token, editable=False)
    is_active = models.BooleanField("activa", default=True, help_text="Si se desactiva, la API rechaza sus envíos.")
    created_at = models.DateTimeField("creada", auto_now_add=True)
    updated_at = models.DateTimeField("actualizada", auto_now=True)

    class Meta:
        db_table = "aplicaciones"
        ordering = ["name"]
        verbose_name = "aplicación"
        verbose_name_plural = "aplicaciones"

    def __str__(self):
        return self.name

    def regenerate_token(self):
        self.api_token = generate_api_token()
        self.save(update_fields=["api_token", "updated_at"])
