import django.db.models.deletion
from decouple import Csv, config
from django.db import migrations, models


def create_default_application(apps, schema_editor):
    """Crea «Análisis Viaje» (la única app actual) y le asigna los tickets existentes.

    Reutiliza el token que antes vivía en SUPPORT_API_TOKENS para que la app
    móvil siga funcionando sin cambios.
    """
    Application = apps.get_model("applications", "Application")
    SupportTicket = apps.get_model("support", "SupportTicket")

    defaults = {"name": "Análisis Viaje"}
    legacy_tokens = [t for t in config("SUPPORT_API_TOKENS", default="", cast=Csv()) if t]
    if legacy_tokens:
        defaults["api_token"] = legacy_tokens[0]
    application, _ = Application.objects.get_or_create(code="analisis-viaje", defaults=defaults)
    SupportTicket.objects.filter(application__isnull=True).update(application=application)


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0001_initial"),
        ("support", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="supportticket",
            name="application",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="support_tickets",
                to="applications.application",
                verbose_name="aplicación",
            ),
        ),
        migrations.RunPython(create_default_application, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="supportticket",
            name="application",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="support_tickets",
                to="applications.application",
                verbose_name="aplicación",
            ),
        ),
    ]
