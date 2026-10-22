import django.core.validators
from django.db import migrations, models

import apps.applications.models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Application",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, verbose_name="nombre")),
                (
                    "code",
                    models.SlugField(
                        help_text="Clave corta y única, ej. analisis-viaje. Solo minúsculas, números y guiones.",
                        unique=True,
                        verbose_name="identificador",
                    ),
                ),
                (
                    "package_name",
                    models.CharField(
                        blank=True, help_text="Ej. com.doublee.analisisviaje", max_length=150, verbose_name="paquete Android"
                    ),
                ),
                ("description", models.TextField(blank=True, verbose_name="descripción")),
                (
                    "color",
                    models.CharField(
                        default="#2563eb",
                        help_text="Color de la etiqueta en los tickets.",
                        max_length=7,
                        validators=[
                            django.core.validators.RegexValidator(
                                "^#[0-9a-fA-F]{6}$", "Usa un color hexadecimal, ej. #2563eb."
                            )
                        ],
                        verbose_name="color",
                    ),
                ),
                (
                    "api_token",
                    models.CharField(
                        default=apps.applications.models.generate_api_token,
                        editable=False,
                        max_length=64,
                        unique=True,
                        verbose_name="token API",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True, help_text="Si se desactiva, la API rechaza sus envíos.", verbose_name="activa"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="creada")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizada")),
            ],
            options={
                "verbose_name": "aplicación",
                "verbose_name_plural": "aplicaciones",
                "db_table": "aplicaciones",
                "ordering": ["name"],
            },
        ),
    ]
