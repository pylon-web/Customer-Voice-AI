#!/usr/bin/env bash
set -e

echo "=== Customer Voice AI — Local Environment Setup ==="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is required but not installed."
    exit 1
fi

echo "✅ Python $(python3 --version) detected."

# Setup .env if missing
if [ ! -f .env ]; then
    echo "📋 Copying .env.example -> .env"
    cp .env.example .env
else
    echo "✅ .env file already exists."
fi

# Create virtualenv if needed
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment in .venv..."
    python3 -m venv .venv
fi

echo "✅ Setup complete. Activate with: source .venv/bin/activate"
