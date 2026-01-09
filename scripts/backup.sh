#!/bin/bash
# Database backup script

set -e

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/botcreator_$TIMESTAMP.sql.gz"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "Creating backup: $BACKUP_FILE"

# Run pg_dump inside container and compress
docker compose exec -T db pg_dump -U postgres botcreator | gzip > "$BACKUP_FILE"

echo "Backup created successfully"

# Keep last N backups (default 7)
KEEP_BACKUPS="${KEEP_BACKUPS:-7}"
echo "Cleaning old backups (keeping last $KEEP_BACKUPS)"

ls -t "$BACKUP_DIR"/botcreator_*.sql.gz | tail -n +$((KEEP_BACKUPS + 1)) | xargs -r rm

echo "Done"
