# Despliegue en el VPS (Hostinger KVM 1, Ubuntu 24.04)

Producción usa `docker-compose.prod.yml`: MySQL 8.4, Redis, Django (2 réplicas) y Caddy (HTTPS automático, balanceo, estáticos). La base y las imágenes viven en volúmenes de Docker en el servidor.

## 1. Preparar el servidor (una sola vez)

Desde tu PC:

```powershell
ssh root@IP_DEL_VPS
```

Ya en el servidor:

```bash
# Docker (omitir si elegiste la plantilla "Ubuntu con Docker")
curl -fsSL https://get.docker.com | sh

# Firewall: solo SSH y web
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable

# Código
git clone https://github.com/EricEscobar527/admin_doublee.git /opt/admin-doublee
```

## 2. Dominio

En el DNS de tu dominio crea un registro **A**: `admin` → `IP_DEL_VPS` (o el subdominio que quieras). Espera a que resuelva (`ping admin.tudominio.com`).

## 3. Primer despliegue

En el servidor, crea el `.env` (nunca se sube a GitHub):

```bash
cd /opt/admin-doublee
cp .env.prod.example .env
nano .env        # llenar los CAMBIAR y poner tu dominio
```

Genera los secretos con `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` (uno para `SECRET_KEY`, otros para las contraseñas de la base).

Levanta todo y crea tu usuario:

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec admin_doublee python manage.py createsuperuser
```

Abre `https://admin.tudominio.com`. Caddy obtiene el certificado solo en el primer acceso (puede tardar unos segundos).

**Sin dominio todavía:** en `.env` usa `SITE_ADDRESS=:80`, `ALLOWED_HOSTS=IP_DEL_VPS`, `CSRF_TRUSTED_ORIGINS=http://IP_DEL_VPS` y `SECURE_COOKIES=False`. Funciona por `http://IP`, pero la app Android en release necesita HTTPS.

## 4. Token de la app

La migración crea "Análisis Viaje" con un token nuevo. Cópialo en **Aplicaciones → Análisis Viaje** y ponlo en la app junto con `baseUrl = https://admin.tudominio.com/api`.

## 5. Actualizar

En tu PC: commit y `git push`. Luego, desde la carpeta del proyecto:

```powershell
.\scripts\deploy.ps1 -Server IP_DEL_VPS
```

Hace `git pull` en el servidor, reconstruye la imagen, aplica migraciones y reinicia sin tocar la base, las imágenes ni el `.env`. (Equivale a entrar por SSH y correr `git pull && docker compose -f docker-compose.prod.yml up -d --build`.)

> El repositorio es **público**: nunca hagas commit de `.env`, tokens ni contraseñas. `.gitignore` ya excluye `.env`, `media/` y `staticfiles/`.

## 6. Respaldos

```bash
crontab -e
# agregar:
0 3 * * * sh /opt/admin-doublee/scripts/backup.sh >> /var/log/admin-doublee-backup.log 2>&1
```

Guarda base e imágenes en `/opt/backups/admin-doublee` (14 días). Copia esos archivos fuera del VPS de vez en cuando.

## Comandos útiles (en el servidor, dentro de /opt/admin-doublee)

| Para | Comando |
|---|---|
| Ver estado | `docker compose -f docker-compose.prod.yml ps` |
| Ver logs | `docker compose -f docker-compose.prod.yml logs -f --tail 100` |
| Reiniciar | `docker compose -f docker-compose.prod.yml restart` |
| Shell de Django | `docker compose -f docker-compose.prod.yml exec admin_doublee python manage.py shell` |
| Entrar a MySQL | `docker compose -f docker-compose.prod.yml exec db mysql -u root -p` |
