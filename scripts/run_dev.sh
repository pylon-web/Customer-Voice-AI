#!/usr/bin/env bash
set -e

echo "=== Starting Customer Voice AI Backend Dev Server ==="
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
uvicorn app.main:app --app-dir backend --reload --port 8000 --host 0.0.0.0
