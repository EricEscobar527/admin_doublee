from django.db import migrations, models
from django.utils import timezone


def to_local_date(apps, schema_editor):
    """Pasa cada fecha/hora (guardada en UTC) a la fecha de México, p. ej. 2026-12-08 05:59 UTC -> 2026-12-07."""
    Application = apps.get_model("applications", "Application")
    for app in Application.objects.exclude(beta_ends_at=None):
        app.beta_ends_on = timezone.localtime(app.beta_ends_at).date()
        app.save(update_fields=["beta_ends_on"])


def to_datetime(apps, schema_editor):
    Application = apps.get_model("applications", "Application")
    for app in Application.objects.exclude(beta_ends_on=None):
        app.beta_ends_at = timezone.make_aware(timezone.datetime.combine(app.beta_ends_on, timezone.datetime.min.time()))
        app.save(update_fields=["beta_ends_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0002_application_beta_ends_at_application_beta_message_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="beta_ends_on",
            field=models.DateField(null=True, blank=True),
        ),
        migrations.RunPython(to_local_date, to_datetime),
        migrations.RemoveField(model_name="application", name="beta_ends_at"),
        migrations.RenameField(model_name="application", old_name="beta_ends_on", new_name="beta_ends_at"),
        migrations.AlterField(
            model_name="application",
            name="beta_ends_at",
            field=models.DateField(
                blank=True,
                help_text="Informativa: se muestra en el aviso, no activa el cobro.",
                null=True,
                verbose_name="fin de la beta",
            ),
        ),
    ]
