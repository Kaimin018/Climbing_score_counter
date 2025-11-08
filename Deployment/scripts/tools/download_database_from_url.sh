#!/bin/bash
# Linux/Mac shell script: Download database backup from network URL
# Usage: bash download_database_from_url.sh

# Get script directory and navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

echo "=========================================="
echo "Download Database Backup from URL"
echo "=========================================="
echo ""

LOCAL_DB="db.sqlite3"
BACKUP_DIR="backups"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Ask user for URL
echo "Please enter the URL of the database backup file:"
echo "  Example: https://example.com/backups/db_backup.sqlite3"
echo "  https://github.com/Kaimin018/Climbing_score_counter/blob/main/db.sqlite3"
echo ""
read -p "URL: " DOWNLOAD_URL

if [ -z "$DOWNLOAD_URL" ]; then
    echo "❌ Error: URL cannot be empty"
    exit 1
fi

# Validate URL format (basic check)
if [[ ! "$DOWNLOAD_URL" =~ ^https?:// ]]; then
    echo "⚠️  Warning: URL format may be incorrect. Expected: http:// or https://"
    echo "   Continuing anyway..."
    echo ""
fi

# Backup local database if exists
if [ -f "$LOCAL_DB" ]; then
    BACKUP_NAME="$BACKUP_DIR/db_local_backup_$(date +%Y%m%d_%H%M%S).sqlite3"
    echo "Backing up local database to: $BACKUP_NAME"
    cp "$LOCAL_DB" "$BACKUP_NAME"
    if [ $? -eq 0 ]; then
        echo "✅ Local database backed up"
    else
        echo "⚠️  Warning: Failed to backup local database"
    fi
    echo ""
else
    echo "ℹ️  Local database does not exist, skipping backup"
    echo ""
fi

# Download the database
echo "Downloading database from URL..."
echo "  URL: $DOWNLOAD_URL"
echo ""

# Try using curl first (most common)
if command -v curl &> /dev/null; then
    curl -L -o "$LOCAL_DB" "$DOWNLOAD_URL"
    DOWNLOAD_EXIT_CODE=$?
elif command -v wget &> /dev/null; then
    wget -O "$LOCAL_DB" "$DOWNLOAD_URL"
    DOWNLOAD_EXIT_CODE=$?
else
    echo "❌ Error: Neither curl nor wget is available"
    echo "   Please install one of the following:"
    echo "   1. curl: sudo apt-get install curl (Ubuntu/Debian)"
    echo "   2. wget: sudo apt-get install wget (Ubuntu/Debian)"
    exit 1
fi

# Check if download was successful
if [ $DOWNLOAD_EXIT_CODE -ne 0 ]; then
    echo "❌ Database download failed"
    exit 1
fi

# Verify the downloaded file
if [ -f "$LOCAL_DB" ]; then
    FILE_SIZE=$(stat -f%z "$LOCAL_DB" 2>/dev/null || stat -c%s "$LOCAL_DB" 2>/dev/null || echo "0")
    FILE_SIZE_KB=$((FILE_SIZE / 1024))
    FILE_SIZE_MB=$((FILE_SIZE / 1024 / 1024))
    
    # Check if file size is reasonable (at least 1 KB)
    if [ $FILE_SIZE -lt 1024 ]; then
        echo ""
        echo "⚠️  Warning: Downloaded file is very small ($FILE_SIZE bytes)"
        echo "   This might indicate an error page or empty file"
        echo "   Please verify the URL is correct"
        echo ""
        read -p "Continue anyway? (yes/no): " CONTINUE
        if [ "$CONTINUE" != "yes" ]; then
            echo "Operation cancelled."
            exit 0
        fi
    fi
    
    if [ $FILE_SIZE_MB -gt 0 ]; then
        echo "✅ Database downloaded successfully!"
        echo "   File size: ${FILE_SIZE_MB} MB"
    else
        echo "✅ Database downloaded successfully!"
        echo "   File size: ${FILE_SIZE_KB} KB"
    fi
    echo "   Location: $LOCAL_DB"
    echo ""
    echo "=========================================="
    echo "Download completed!"
    echo "=========================================="
    echo ""
    echo "⚠️  Notes:"
    echo "   1. Local database backed up to: $BACKUP_DIR/ (if existed)"
    echo "   2. If you encounter issues, you can restore from backup"
    echo "   3. It's recommended to stop the local development server before downloading"
    echo "   4. Verify the database is working correctly before using it"
    echo ""
else
    echo "❌ Error: Database file not found after download"
    exit 1
fi

