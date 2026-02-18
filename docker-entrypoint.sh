#!/bin/bash
set -e

echo "🚀 Starting Container Entrypoint..."

# 1. Environment Validation
if [ ! -f "$CONFIG_PATH" ]; then
    echo "⚠️  Warning: Config file not found at $CONFIG_PATH. Using defaults."
fi

# 2. Start Backend (Uvicorn)
# Using 'exec' to ensure uvicorn receives signals (PID 1)
# Note: WORKDIR is already set to /backend in Dockerfile
echo "🔥 Igniting Uvicorn Server..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info
