# DoubleE Admin

Panel en Django para administrar las apps móviles. Por ahora: login (JWT), dashboard y soporte.

## Levantar

La base vive en tu MySQL (MAMP en local). Crea la base y un usuario que acepte conexiones desde Docker:

```sql
CREATE DATABASE admin_doublee CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'admin_doublee'@'%' IDENTIFIED BY '...';
GRANT ALL PRIVILEGES ON admin_doublee.* TO 'admin_doublee'@'%';
```

```bash
cp .env.example .env                       # y llenar secretos
docker network create network_mas_docker   # solo si no existe
docker compose up -d --build               # aplica las migraciones (crea las tablas)
docker compose exec admin_doublee python manage.py createsuperuser
```

Panel: http://localhost:8010

### Servicios

| Servicio | Qué hace |
|---|---|
| `admin_doublee_nginx` | Balanceador y única entrada (`PUERTO` → 80). Sirve `/static/`, límite de subida 60 MB, pasa la IP real en `X-Forwarded-For`. Config en `nginx/default.conf` |
| `admin_doublee` | Django + gunicorn, `REPLICAS` réplicas en el puerto interno 8000 |
| `admin_doublee_migrate` | Corre `migrate` y `collectstatic` una vez antes de las réplicas y termina |
| `admin_doublee_redis` | Comparte los avisos en vivo (WebSockets) entre las réplicas |

### En vivo

Django corre como ASGI (gunicorn + uvicorn) con Django Channels. El panel abre un WebSocket en `/ws/support/` (solo admins con sesión, Origin validado contra `ALLOWED_HOSTS`). Cuando la API crea un ticket o un admin cambia su estatus, se manda a todos los navegadores conectados: el dashboard actualiza contadores y "Soportes recientes", la lista de tickets agrega la fila (si entra en los filtros actuales) y aparece una notificación. El indicador "En vivo" de la barra superior muestra el estado de la conexión, que se reconecta sola.

Comandos de Django: `docker compose exec admin_doublee python manage.py <comando>`.
Si cambias `REPLICAS`, reinicia nginx para que las detecte: `docker compose restart admin_doublee_nginx`.

En Windows/Mac, Docker Desktop oculta la IP real del cliente (todas llegan como `172.x.x.x`), así que el límite por IP solo es útil en el servidor Linux.

Soporta MySQL 5.7 (el de MAMP) mediante `config/mysql57`; para producción se recomienda MySQL 8.

Pruebas (SQLite y canales en memoria): `docker compose run --rm --no-deps admin_doublee python manage.py test --settings=config.settings_test`

## API de las apps

| Endpoint | Para qué |
|---|---|
| `POST /api/support/tickets` | Tickets de soporte (abajo) |
| `GET /api/app/config` | Configuración remota (cobro, beta, build mínimo). Se edita en **Aplicaciones → editar → Configuración remota** |
| `POST /api/subscriptions/verify` | Verifica una compra con Google Play, la reconoce y la guarda (panel → **Suscripciones**). Responde `503` si Google no responde: la app debe conservar su último resultado |

Política de privacidad pública: `/viajeok/privacidad/` (usa `PRIVACY_CONTACT_EMAIL`).

## Autenticación

- **Panel web**: login con usuario/contraseña. Se emite un JWT (access 15 min + refresh 12 h) guardado en cookies HttpOnly; el access se renueva solo mientras el refresh siga vigente. Cerrar sesión invalida el refresh (blacklist).
- **API JWT**: `POST /api/auth/token/`, `/api/auth/token/refresh/`, `/api/auth/token/verify/`.
- **API de las apps**: `Authorization: Bearer <token>`. Cada app tiene su propio token en **panel > Aplicaciones**; el token identifica de qué app viene cada ticket, no hace falta otro parámetro.

## Aplicaciones

Alta, edición y baja de las apps móviles (tabla `aplicaciones`). Al crear una se genera su token, que se puede copiar o regenerar desde la edición. Una app desactivada deja de poder enviar tickets. Una app con tickets no se puede eliminar (para no perder el historial): se desactiva.

## API de soporte

`POST {baseUrl}/support/tickets` (`baseUrl` = `https://host/api`), `multipart/form-data`.

| Campo | Notas |
|---|---|
| `issue` | Uno de `SupportTicket.Issue` (`apps/support/models.py`) |
| `email` | Obligatorio, se valida |
| `message`, `name`, `phone` | Obligatorios según el tipo (`REQUIRED_FIELDS_BY_ISSUE` en `apps/support/serializers.py`) |
| `device_time` | ISO 8601 con zona, ej. `2026-10-22T13:05:09-06:00` |
| `app_version`, `app_build`, `android_version`, `android_sdk`, `device_manufacturer`, `device_brand`, `device_model` | Opcionales |
| archivos | Cualquier nombre de campo; máx. 5, solo JPEG/PNG/WEBP/GIF (tipo real), 10 MB c/u |

Respuestas: `201 {"id": "<uuid>", "folio": "SOP-000001"}` · `400` validación · `401` token · `429` límite (por IP y por correo, por hora).

Cualquier campo de texto extra que mande la app se guarda en `payload` y se ve en el detalle del ticket.

## Imágenes

Sin `AWS_STORAGE_BUCKET_NAME` se guardan en `./media`. Con S3 (o compatible vía `AWS_S3_ENDPOINT_URL`) el bucket es privado y el panel usa URLs firmadas. En ambos casos solo un admin logueado puede verlas.

## Producción

`ENTORNO=prod`, `GUNICORN_EXTRA=` (sin `--reload`), `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` con tu dominio, y HTTPS (certificado en nginx o en el balanceador del proveedor). Si hay otro proxy delante de este nginx, ajusta `X-Forwarded-For` en `nginx/default.conf` para no perder la IP real.
