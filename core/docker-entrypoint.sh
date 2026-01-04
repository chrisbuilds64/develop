#!/bin/bash
# Tweight Core - Docker Entrypoint Script
# Runs database migrations before starting the application

set -e

echo "🚀 Starting Tweight Core API..."

# Wait a moment for volume to be mounted
sleep 1

# Run Alembic migrations
echo "📦 Running database migrations..."
alembic upgrade head

# Check if migration succeeded
if [ $? -eq 0 ]; then
    echo "✅ Database migrations completed successfully"
else
    echo "❌ Database migration failed!"
    exit 1
fi

# Start the application
echo "🌐 Starting FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
