#!/bin/bash
# Simple Azure startup script - no bullshit

set -e

echo "🪟 WindX - Starting Simple"
echo "Working Directory: $(pwd)"
echo "Files available:"
ls -la

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Starting app..."
exec python -m uvicorn main:app --host 0.0.0.0 --port 8000