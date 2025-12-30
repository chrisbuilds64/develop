#!/bin/bash
# Tweight Core API - Deployment Script
# Usage: ./deploy.sh

set -e  # Exit on error

echo "🚀 Deploying Tweight Core API..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Stop existing containers
echo "⏹️  Stopping existing containers..."
docker compose down || true

# Build new image
echo "🔨 Building Docker image..."
docker compose build

# Start containers
echo "▶️  Starting containers..."
docker compose up -d

# Wait for health check
echo "⏳ Waiting for API to be healthy..."
sleep 5

# Check health
if docker compose ps | grep -q "healthy\|Up"; then
    echo "✅ Deployment successful!"
    echo "📡 API is running at http://localhost:8000"
    echo "🏥 Health check: http://localhost:8000/health"
    echo ""
    echo "📊 Container status:"
    docker compose ps
else
    echo "❌ Deployment failed. Check logs:"
    docker compose logs
    exit 1
fi
