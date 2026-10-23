#!/bin/sh
# Respaldo diario en el VPS: base de datos + imágenes de soporte. Conserva 14 días.
# Cron (como root):  0 3 * * * sh /opt/admin-doublee/scripts/backup.sh >> /var/log/admin-doublee-backup.log 2>&1
set -eu
cd "$(dirname "$0")/.."
DEST=/opt/backups/admin-doublee
STAMP=$(date +%Y%m%d-%H%M)
mkdir -p "$DEST"

. ./.env
docker compose -f docker-compose.prod.yml exec -T db \
  mysqldump -u root -p"$DB_ROOT_PASSWORD" --single-transaction --routines "$DB_NAME" | gzip > "$DEST/db-$STAMP.sql.gz"

docker compose -f docker-compose.prod.yml exec -T admin_doublee \
  tar -czf - -C /home/admin-doublee media > "$DEST/media-$STAMP.tar.gz"

find "$DEST" -type f -mtime +14 -delete
echo "$(date) respaldo OK: $DEST/*-$STAMP.*"
