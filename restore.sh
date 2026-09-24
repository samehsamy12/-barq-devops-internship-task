#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "[-] Error: Please specify the backup archive file to restore."
    echo "Usage: ./restore.sh ./backups/backup_TIMESTAMP.tar.gz"
    exit 1
fi

BACKUP_ARCHIVE="$1"

if [ ! -f "$BACKUP_ARCHIVE" ]; then
    echo "[-] Error: Backup file '$BACKUP_ARCHIVE' not found!"
    exit 1
fi

TEMP_DIR="./backups/temp_restore"
mkdir -p "$TEMP_DIR"

echo "[*] Extracting backup archive..."
tar -xzf "$BACKUP_ARCHIVE" -C "$TEMP_DIR"

EXTRACTED_DIR=$(find "$TEMP_DIR" -mindepth 1 -maxdepth 1 -type d)

echo "[*] Starting restore process..."

# 1. Restore PostgreSQL Database
if [ -f "$EXTRACTED_DIR/database.sql" ]; then
    if docker compose ps --services --filter "status=running" | grep -q "postgres"; then
        echo "[+] Resetting and restoring PostgreSQL database..."
        docker compose exec -T -e PGPASSWORD="BarqLabOnly_7qN2vK8c" postgres psql -h localhost -U barq_app -d barq_tasks -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
        docker compose exec -T -e PGPASSWORD="BarqLabOnly_7qN2vK8c" postgres psql -h localhost -U barq_app -d barq_tasks < "$EXTRACTED_DIR/database.sql"
    else
        echo "[-] Database container is not running!"
    fi
fi

# 2. Restore Redis Data
if [ -f "$EXTRACTED_DIR/dump.rdb" ]; then
    echo "[+] Restoring Redis data..."
    docker compose start redis || true
    REDIS_CONTAINER=$(docker compose ps -q redis)
    if [ -n "$REDIS_CONTAINER" ]; then
        docker compose exec -T redis redis-cli FLUSHALL || true
        docker cp "$EXTRACTED_DIR/dump.rdb" "$REDIS_CONTAINER:/data/dump.rdb"
        docker compose restart redis
        echo "[+] Redis data restored successfully."
    fi
fi

rm -rf "$TEMP_DIR"
echo "[+] Restore completed successfully!"
