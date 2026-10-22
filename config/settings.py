from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

ENTORNO = config("ENTORNO", default="dev")
DEBUG = config("DEBUG", default=ENTORNO != "prod", cast=bool)
SECRET_KEY = config("SECRET_KEY")
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "storages",
    "apps.accounts",
    "apps.dashboard",
    "apps.applications",
    "apps.support",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "apps.accounts.middleware.JWTCookieAuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Base de datos: MySQL en Docker, SQLite para pruebas locales rápidas.
if config("DB_ENGINE", default="mysql") == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "config.mysql57",
            "NAME": config("DB_NAME"),
            "USER": config("DB_USER"),
            "PASSWORD": config("DB_PASSWORD"),
            "HOST": config("DB_HOST"),
            "PORT": config("DB_PORT", default="3306"),
            "CONN_MAX_AGE": 60,
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "accounts:login"

LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Archivos estáticos y media
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "media/"

AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME", default="")
if AWS_STORAGE_BUCKET_NAME:
    # S3 o compatible (DigitalOcean Spaces, MinIO...). Bucket privado + URLs firmadas.
    AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
    AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default=None)
    AWS_S3_ENDPOINT_URL = config("AWS_S3_ENDPOINT_URL", default=None)
    AWS_DEFAULT_ACL = "private"
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = 600
    AWS_S3_FILE_OVERWRITE = False
    AWS_LOCATION = config("AWS_LOCATION", default="admin-doublee")
    DEFAULT_FILE_STORAGE_BACKEND = "storages.backends.s3.S3Storage"
else:
    DEFAULT_FILE_STORAGE_BACKEND = "django.core.files.storage.FileSystemStorage"

STORAGES = {
    "default": {"BACKEND": DEFAULT_FILE_STORAGE_BACKEND},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if ENTORNO == "prod"
        else "whitenoise.storage.CompressedStaticFilesStorage"
    },
}

# Límites de subida (la API admite hasta 5 imágenes de 10 MB).
DATA_UPLOAD_MAX_NUMBER_FILES = 10
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024

MESSAGE_STORAGE = "django.contrib.messages.storage.cookie.CookieStorage"

# REST Framework + JWT
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=config("JWT_ACCESS_MINUTES", default=15, cast=int)),
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=config("JWT_REFRESH_HOURS", default=12, cast=int)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

JWT_ACCESS_COOKIE = "access_token"
JWT_REFRESH_COOKIE = "refresh_token"
JWT_COOKIE_SECURE = config("JWT_COOKIE_SECURE", default=not DEBUG, cast=bool)

# API pública de soporte (apps móviles). Cada app usa el token de su registro en "Aplicaciones".
SUPPORT_MAX_FILES = 5
SUPPORT_MAX_FILE_SIZE = 10 * 1024 * 1024
SUPPORT_RATE_LIMIT_IP_PER_HOUR = config("SUPPORT_RATE_LIMIT_IP_PER_HOUR", default=10, cast=int)
SUPPORT_RATE_LIMIT_EMAIL_PER_HOUR = config("SUPPORT_RATE_LIMIT_EMAIL_PER_HOUR", default=5, cast=int)
# Detrás de un proxy (nginx, load balancer) la IP real llega en X-Forwarded-For.
TRUST_X_FORWARDED_FOR = config("TRUST_X_FORWARDED_FOR", default=False, cast=bool)

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
