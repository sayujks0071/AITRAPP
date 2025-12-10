#!/usr/bin/env bash
# Daily database backup
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
DATE=$(date +%Y%m%d)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATABASE_URL="${DATABASE_URL:-postgresql+psycopg2://trader:trader@localhost:5432/aitrapp}"

mkdir -p "$BACKUP_DIR"

# Extract connection details
DB_CONN="${DATABASE_URL#postgresql+psycopg2://}"

# Full database dump (compressed)
BACKUP_FILE="$BACKUP_DIR/aitrapp_backup_${TIMESTAMP}.sql.gz"

echo "Creating backup: $BACKUP_FILE"
pg_dump "$DB_CONN" | gzip > "$BACKUP_FILE"

# Verify backup was created and is not empty
if [ ! -f "$BACKUP_FILE" ] || [ ! -s "$BACKUP_FILE" ]; then
    echo "❌ Backup failed: file not created or empty"
    exit 1
fi

# Keep only last 7 days of daily backups
find "$BACKUP_DIR" -name "aitrapp_backup_*.sql.gz" -mtime +7 -delete

echo "✅ Backup complete: $BACKUP_FILE"
echo "Size: $(du -h "$BACKUP_FILE" | cut -f1)"
