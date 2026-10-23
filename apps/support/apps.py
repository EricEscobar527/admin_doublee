from django.apps import AppConfig


class SupportConfig(AppConfig):
    name = "apps.support"
    label = "support"
    verbose_name = "Soporte"

    def ready(self):
        from . import signals  # noqa: F401
