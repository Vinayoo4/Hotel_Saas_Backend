#!/bin/bash

# Hotel Management Backend Backup Script
# This script creates backups of the database and important files

# Configuration
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="hotel_management"
DB_USER="hotel_user"
DB_HOST="localhost"
DB_PORT="5432"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    log "Creating backup directory: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
fi

# Function to backup database
backup_database() {
    log "Starting database backup..."
    
    # Check if PostgreSQL is accessible
    if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; then
        error "Cannot connect to PostgreSQL. Check your database settings."
        return 1
    fi
    
    # Create database backup
    BACKUP_FILE="$BACKUP_DIR/db_backup_$DATE.sql"
    
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_FILE" 2>/dev/null; then
        log "Database backup created: $BACKUP_FILE"
        
        # Compress the backup
        gzip "$BACKUP_FILE"
        log "Database backup compressed: $BACKUP_FILE.gz"
        
        # Get file size
        SIZE=$(du -h "$BACKUP_FILE.gz" | cut -f1)
        log "Backup size: $SIZE"
        
        return 0
    else
        error "Database backup failed"
        return 1
    fi
}

# Function to backup files
backup_files() {
    log "Starting file backup..."
    
    # Create file backup
    BACKUP_FILE="$BACKUP_DIR/files_backup_$DATE.tar.gz"
    
    # Backup important directories
    if tar -czf "$BACKUP_FILE" uploads/ ml_models/ data/ 2>/dev/null; then
        log "File backup created: $BACKUP_FILE"
        
        # Get file size
        SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        log "Backup size: $SIZE"
        
        return 0
    else
        error "File backup failed"
        return 1
    fi
}

# Function to cleanup old backups
cleanup_old_backups() {
    log "Cleaning up old backups..."
    
    # Keep backups for 30 days
    find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete 2>/dev/null
    find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete 2>/dev/null
    
    log "Old backups cleaned up"
}

# Function to check disk space
check_disk_space() {
    log "Checking disk space..."
    
    # Get available space in backup directory
    AVAILABLE_SPACE=$(df "$BACKUP_DIR" | awk 'NR==2 {print $4}')
    AVAILABLE_SPACE_MB=$((AVAILABLE_SPACE / 1024))
    
    if [ "$AVAILABLE_SPACE_MB" -lt 1000 ]; then
        warning "Low disk space: ${AVAILABLE_SPACE_MB}MB available"
        return 1
    else
        log "Available disk space: ${AVAILABLE_SPACE_MB}MB"
        return 0
    fi
}

# Main execution
main() {
    log "Starting backup process..."
    
    # Check disk space
    if ! check_disk_space; then
        error "Insufficient disk space for backup"
        exit 1
    fi
    
    # Backup database
    if backup_database; then
        log "Database backup completed successfully"
    else
        error "Database backup failed"
        exit 1
    fi
    
    # Backup files
    if backup_files; then
        log "File backup completed successfully"
    else
        error "File backup failed"
        exit 1
    fi
    
    # Cleanup old backups
    cleanup_old_backups
    
    log "Backup process completed successfully"
    
    # List all backups
    log "Available backups:"
    ls -lh "$BACKUP_DIR"/*.gz 2>/dev/null | while read -r line; do
        log "  $line"
    done
}

# Check if script is run with correct permissions
if [ "$EUID" -eq 0 ]; then
    error "This script should not be run as root"
    exit 1
fi

# Run main function
main "$@"
