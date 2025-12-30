#!/bin/bash
# Deploy Tweight Core API to Strato VPS
# Run this from your Mac to deploy to production server
#
# Usage: ./deploy-to-server.sh SERVER_IP

set -e

# Check if server IP provided
if [ -z "$1" ]; then
    echo "❌ Error: Server IP required"
    echo "Usage: ./deploy-to-server.sh SERVER_IP"
    echo "Example: ./deploy-to-server.sh 123.456.789.012"
    exit 1
fi

SERVER_IP="$1"
SSH_KEY="$HOME/.ssh/strato_vps"
SERVER_USER="root"
SERVER_DIR="/opt/tweight-core"

echo "🚀 Deploying Tweight Core API to Production"
echo "============================================"
echo "Server: $SERVER_IP"
echo "User: $SERVER_USER"
echo "Directory: $SERVER_DIR"
echo ""

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ SSH key not found: $SSH_KEY"
    echo "Run ./setup-ssh-key.sh first"
    exit 1
fi

# Test SSH connection
echo "🔐 Testing SSH connection..."
if ! ssh -i "$SSH_KEY" -o ConnectTimeout=5 "$SERVER_USER@$SERVER_IP" "echo 'SSH connection successful'" 2>/dev/null; then
    echo "❌ SSH connection failed"
    echo "Make sure:"
    echo "  1. Server IP is correct"
    echo "  2. SSH key is configured on server"
    echo "  3. Server is accessible"
    exit 1
fi
echo "✅ SSH connection successful"
echo ""

# Copy application files
echo "📦 Copying application files..."
scp -i "$SSH_KEY" \
    Dockerfile \
    docker-compose.yml \
    main.py \
    database.py \
    models.py \
    schemas.py \
    requirements.txt \
    deploy.sh \
    "$SERVER_USER@$SERVER_IP:$SERVER_DIR/"

echo "✅ Files copied"
echo ""

# Make deploy script executable
echo "🔧 Setting permissions..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" "chmod +x $SERVER_DIR/deploy.sh"
echo "✅ Permissions set"
echo ""

# Deploy application
echo "🚀 Deploying application on server..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" "cd $SERVER_DIR && ./deploy.sh"
echo ""

# Test deployment
echo "🧪 Testing deployment..."
sleep 3
if ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" "curl -s http://localhost:8000/health" | grep -q "ok"; then
    echo "✅ Deployment successful!"
    echo ""
    echo "🌐 API is running at http://$SERVER_IP:8000"
    echo ""
    echo "📝 Next steps:"
    echo "1. Configure nginx reverse proxy"
    echo "2. Setup SSL with certbot"
    echo "3. Point DNS to this server"
else
    echo "❌ Deployment test failed"
    echo "Check logs on server: ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP 'cd $SERVER_DIR && docker compose logs'"
    exit 1
fi
