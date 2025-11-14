#!/bin/bash
set -e

BACKUP_DIR="/opt/dreamops/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/dreamops_backup_${DATE}.sql.gz"

echo "Starting backup at $(date)"

# Create backup
docker-compose exec -T postgres pg_dump -U dreamops dreamops | gzip > "$BACKUP_FILE"

echo "Backup created: $BACKUP_FILE"

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "dreamops_backup_*.sql.gz" -mtime +7 -delete

echo "Old backups cleaned up"

# Upload to S3 (optional)
# aws s3 cp "$BACKUP_FILE" s3://your-backup-bucket/dreamops/

echo "Backup complete at $(date)"
