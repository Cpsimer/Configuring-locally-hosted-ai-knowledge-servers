#!/bin/bash
# ~/ai-idp/scripts/backup-models.sh
# Incremental backup for AI model files
# Version: 1.0 | Date: 2026-01-12
#
# Backs up /mnt/models to external storage with checksum verification
# Schedule with cron: 0 3 * * 0 /home/ubuntu/ai-idp/scripts/backup-models.sh

set -euo pipefail

# Configuration
SOURCE="${SOURCE:-/mnt/models}"
BACKUP_DEST="${BACKUP_DEST:-/mnt/backup/models}"
LOG_DIR="/var/log/ai-idp"
LOG_FILE="${LOG_DIR}/backup.log"
MANIFEST="${BACKUP_DEST}/manifest.json"

# Create directories
mkdir -p "$BACKUP_DEST" "$LOG_DIR"

log() {
    echo "[$(date -Iseconds)] $*" | tee -a "$LOG_FILE"
}

log "=== Model Backup Started ==="
log "Source: $SOURCE"
log "Destination: $BACKUP_DEST"

# Check source exists
if [ ! -d "$SOURCE" ]; then
    log "ERROR: Source directory does not exist: $SOURCE"
    exit 1
fi

# Check destination is writable
if ! touch "$BACKUP_DEST/.write_test" 2>/dev/null; then
    log "ERROR: Cannot write to backup destination: $BACKUP_DEST"
    exit 1
fi
rm -f "$BACKUP_DEST/.write_test"

# Calculate source size
SOURCE_SIZE=$(du -sh "$SOURCE" 2>/dev/null | cut -f1)
log "Source size: $SOURCE_SIZE"

# Check available space at destination
DEST_AVAIL=$(df -h "$BACKUP_DEST" | awk 'NR==2 {print $4}')
log "Destination available: $DEST_AVAIL"

# Create manifest of current models with checksums
log "Creating manifest..."
MANIFEST_TMP="${MANIFEST}.tmp"
echo "[" > "$MANIFEST_TMP"

FIRST=true
find "$SOURCE" -type f \( -name "*.gguf" -o -name "*.safetensors" -o -name "config.json" -o -name "*.bin" \) | \
    while read -r file; do
        REL_PATH="${file#$SOURCE/}"
        SIZE=$(stat -c%s "$file" 2>/dev/null || echo "0")
        
        # Calculate SHA256 for smaller files, skip for >10GB
        if [ "$SIZE" -lt 10737418240 ]; then
            HASH=$(sha256sum "$file" 2>/dev/null | cut -d' ' -f1 || echo "skipped")
        else
            HASH="skipped-large-file"
        fi
        
        if [ "$FIRST" = true ]; then
            FIRST=false
        else
            echo "," >> "$MANIFEST_TMP"
        fi
        
        echo "  {\"path\": \"$REL_PATH\", \"size\": $SIZE, \"sha256\": \"$HASH\"}" >> "$MANIFEST_TMP"
    done

echo "]" >> "$MANIFEST_TMP"
mv "$MANIFEST_TMP" "$MANIFEST"
log "Manifest created: $MANIFEST"

# Perform incremental rsync with checksums
log "Starting rsync..."
rsync -avh --progress --checksum \
    --exclude='*.tmp' \
    --exclude='cache/' \
    --exclude='.cache/' \
    --exclude='__pycache__/' \
    --log-file="${LOG_DIR}/rsync-$(date +%Y%m%d).log" \
    "$SOURCE/" "$BACKUP_DEST/" 2>&1 | tee -a "$LOG_FILE"

RSYNC_EXIT=${PIPESTATUS[0]}

if [ $RSYNC_EXIT -ne 0 ]; then
    log "ERROR: rsync failed with exit code $RSYNC_EXIT"
    exit $RSYNC_EXIT
fi

log "rsync completed successfully"

# Verify backup integrity
log "Verifying backup..."
BACKUP_COUNT=$(find "$BACKUP_DEST" -type f \( -name "*.gguf" -o -name "*.safetensors" \) 2>/dev/null | wc -l)
SOURCE_COUNT=$(find "$SOURCE" -type f \( -name "*.gguf" -o -name "*.safetensors" \) 2>/dev/null | wc -l)

log "Source models: $SOURCE_COUNT"
log "Backup models: $BACKUP_COUNT"

if [ "$BACKUP_COUNT" -eq "$SOURCE_COUNT" ]; then
    log "✓ Backup verification PASSED: $BACKUP_COUNT models"
else
    log "⚠️  WARNING: Backup mismatch - Source: $SOURCE_COUNT, Backup: $BACKUP_COUNT"
    log "Some files may have been excluded or failed to transfer"
fi

# Calculate backup size
BACKUP_SIZE=$(du -sh "$BACKUP_DEST" 2>/dev/null | cut -f1)
log "Backup size: $BACKUP_SIZE"

# Cleanup old rsync logs (keep last 7)
find "$LOG_DIR" -name "rsync-*.log" -mtime +7 -delete 2>/dev/null || true

log "=== Model Backup Complete ==="
log ""
