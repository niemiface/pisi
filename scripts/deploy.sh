#!/usr/bin/env bash
# Deploy project files to Raspberry Pi over rsync / SSH
# Usage: ./scripts/deploy.sh

TARGET_HOST="10.0.0.212"
TARGET_USER="niemiface"
TARGET_DIR="~/pisi/"

echo "Syncing local files to ${TARGET_USER}@${TARGET_HOST}:${TARGET_DIR}..."

rsync -avz --exclude='venv' --exclude='.git' --exclude='__pycache__' --exclude='.DS_Store' \
    ./ ${TARGET_USER}@${TARGET_HOST}:${TARGET_DIR}

echo "Deployment finished."
