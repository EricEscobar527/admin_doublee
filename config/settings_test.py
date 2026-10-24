"""Settings para pruebas: SQLite y canales en memoria, sin depender de MySQL ni Redis.

Uso: python manage.py test --settings=config.settings_test
"""
from .settings import *  # noqa: F401,F403
from .settings import BASE_DIR

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "test.sqlite3"}}
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
PRIVACY_CONTACT_EMAIL = ""
GOOGLE_PLAY_SERVICE_ACCOUNT_FILE = ""
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
