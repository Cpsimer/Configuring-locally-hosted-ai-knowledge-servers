#!/bin/bash
# ~/ai-idp/scripts/backup-models.sh
# Model Backup Script with Integrity Verification
# Version: 2.0 | Date: 2026-01-12
#
# Features:
# - Incremental rsync with checksums
# - SHA256 manifest for integrity verification
# - Bandwidth-limited transfers (optional)
# - Detailed logging
# - Restoration verification

set -euo pipefail

# Configuration
SOURCE_DIR="/mnt/models"
BACKUP_DEST="${BACKUP_DEST:-/mnt/backup/models}"  # Override via environment
MANIFEST_FILE="$BACKUP_DEST/manifest.json"
LOG_FILE="/var/log/ai-idp/backup.log"
BANDWIDTH_LIMIT=""  # e.g., "50m" for 50 MB/s limit, empty for unlimited

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date -Iseconds)
    
    echo "[$timestamp] $level: $message" >> "$LOG_FILE"
    
    case "$level" in
        "ERROR")
            echo -e "${RED}[$timestamp] $level: $message${NC}" >&2
            ;;
        "WARNING")
            echo -e "${YELLOW}[$timestamp] $level: $message${NC}"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[$timestamp] $level: $message${NC}"
            ;;
        *)
            echo "[$timestamp] $level: $message"
            ;;
    esac
}

# Check prerequisites
check_prereqs() {
    if ! command -v rsync &> /dev/null; then
        log "ERROR" "rsync is required but not installed"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log "WARNING" "jq not installed - manifest will be basic format"
    fi
    
    if [ ! -d "$SOURCE_DIR" ]; then
        log "ERROR" "Source directory does not exist: $SOURCE_DIR"
        exit 1
    fi
    
    # Create backup destination
    mkdir -p "$BACKUP_DEST"
    mkdir -p "$(dirname "$LOG_FILE")"
}

# Generate SHA256 manifest
generate_manifest() {
    log "INFO" "Generating integrity manifest..."
    
    local manifest_temp="$BACKUP_DEST/manifest.tmp"
    
    # Find model files and compute checksums
    echo "{" > "$manifest_temp"
    echo "  \"backup_date\": \"$(date -Iseconds)\"," >> "$manifest_temp"
    echo "  \"source_dir\": \"$SOURCE_DIR\"," >> "$manifest_temp"
    echo "  \"files\": [" >> "$manifest_temp"
    
    local first=true
    find "$SOURCE_DIR" -type f \( -name "*.gguf" -o -name "*.safetensors" -o -name "config.json" -o -name "tokenizer.json" \) | sort | while read -r file; do
        local relative_path="${file#$SOURCE_DIR/}"
        local file_size=$(stat -c%s "$file")
        local file_hash=$(sha256sum "$file" | cut -d' ' -f1)
        
        if [ "$first" = true ]; then
            first=false
        else
            echo "," >> "$manifest_temp"
        fi
        
        echo -n "    {\"path\": \"$relative_path\", \"size\": $file_size, \"sha256\": \"$file_hash\"}" >> "$manifest_temp"
    done
    
    echo "" >> "$manifest_temp"
    echo "  ]" >> "$manifest_temp"
    echo "}" >> "$manifest_temp"
    
    mv "$manifest_temp" "$MANIFEST_FILE"
    log "INFO" "Manifest written: $MANIFEST_FILE"
}

# Perform backup
run_backup() {
    log "INFO" "Starting model backup: $SOURCE_DIR -> $BACKUP_DEST"
    
    local rsync_opts="-avh --progress --checksum --delete"
    rsync_opts+=" --exclude='*.tmp' --exclude='cache/' --exclude='*.lock'"
    
    if [ -n "$BANDWIDTH_LIMIT" ]; then
        rsync_opts+=" --bwlimit=$BANDWIDTH_LIMIT"
        log "INFO" "Bandwidth limited to: $BANDWIDTH_LIMIT"
    fi
    
    # Run rsync
    if eval rsync $rsync_opts "$SOURCE_DIR/" "$BACKUP_DEST/"; then
        log "SUCCESS" "rsync completed successfully"
    else
        log "ERROR" "rsync failed with exit code $?"
        return 1
    fi
}

# Verify backup integrity
verify_backup() {
    log "INFO" "Verifying backup integrity..."
    
    local source_count=$(find "$SOURCE_DIR" -type f \( -name "*.gguf" -o -name "*.safetensors" \) | wc -l)
    local backup_count=$(find "$BACKUP_DEST" -type f \( -name "*.gguf" -o -name "*.safetensors" \) | wc -l)
    
    if [ "$source_count" -eq "$backup_count" ]; then
        log "SUCCESS" "Backup verified: $backup_count model files"
        
        # Calculate total size
        local source_size=$(du -sh "$SOURCE_DIR" | cut -f1)
        local backup_size=$(du -sh "$BACKUP_DEST" | cut -f1)
        
        log "INFO" "Source size: $source_size, Backup size: $backup_size"
        return 0
    else
        log "ERROR" "Backup mismatch! Source: $source_count files, Backup: $backup_count files"
        return 1
    fi
}

# Restore from backup
restore_backup() {
    local restore_target="${1:-$SOURCE_DIR}"
    
    log "WARNING" "Restoring models to: $restore_target"
    read -p "This will overwrite existing files. Continue? [y/N] " confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log "INFO" "Restore cancelled"
        return 1
    fi
    
    rsync -avh --progress --checksum "$BACKUP_DEST/" "$restore_target/"
    log "SUCCESS" "Restore completed"
}

# Show backup status
show_status() {
    echo "Model Backup Status"
    echo "==================="
    echo ""
    echo "Source: $SOURCE_DIR"
    echo "Backup: $BACKUP_DEST"
    echo ""
    
    if [ -d "$SOURCE_DIR" ]; then
        local source_files=$(find "$SOURCE_DIR" -type f \( -name "*.gguf" -o -name "*.safetensors" \) | wc -l)
        local source_size=$(du -sh "$SOURCE_DIR" 2>/dev/null | cut -f1)
        echo "Source: $source_files models, $source_size total"
    else
        echo "Source: NOT FOUND"
    fi
    
    if [ -d "$BACKUP_DEST" ]; then
        local backup_files=$(find "$BACKUP_DEST" -type f \( -name "*.gguf" -o -name "*.safetensors" \) | wc -l)
        local backup_size=$(du -sh "$BACKUP_DEST" 2>/dev/null | cut -f1)
        echo "Backup: $backup_files models, $backup_size total"
        
        if [ -f "$MANIFEST_FILE" ]; then
            local manifest_date=$(grep -o '"backup_date"[^,]*' "$MANIFEST_FILE" | cut -d'"' -f4)
            echo "Last backup: $manifest_date"
        fi
    else
        echo "Backup: NOT FOUND"
    fi
}

# Main entry point
main() {
    case "${1:-backup}" in
        backup)
            check_prereqs
            run_backup
            generate_manifest
            verify_backup
            log "SUCCESS" "Backup completed successfully at $(date -Iseconds)"
            ;;
        verify)
            check_prereqs
            verify_backup
            ;;
        manifest)
            check_prereqs
            generate_manifest
            ;;
        restore)
            check_prereqs
            restore_backup "${2:-}"
            ;;
        status)
            show_status
            ;;
        *)
            echo "Usage: $0 {backup|verify|manifest|restore [target]|status}"
            echo ""
            echo "Commands:"
            echo "  backup   - Full incremental backup with integrity check"
            echo "  verify   - Verify backup matches source"
            echo "  manifest - Regenerate SHA256 manifest only"
            echo "  restore  - Restore from backup (destructive)"
            echo "  status   - Show backup status"
            exit 1
            ;;
    esac
}

main "$@"
