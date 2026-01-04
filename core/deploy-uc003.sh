#!/bin/bash
# Deploy UC-003 Authentication Service to Strato VPS
# This script deploys the updated Tweight Core API with Clerk authentication
#
# Usage: ./deploy-uc003.sh

set -e

SERVER_IP="82.165.165.199"
SSH_KEY="$HOME/.ssh/strato_vps"
SERVER_USER="root"
SERVER_DIR="/opt/tweight-core"

echo "🚀 Deploying UC-003: Authentication Service"
echo "============================================"
echo "Server: $SERVER_IP (api.chrisbuilds64.com)"
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
    echo "Make sure SSH key is configured on server"
    exit 1
fi
echo "✅ SSH connection successful"
echo ""

# Step 1: Stop running container
echo "⏹️  Stopping running container..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" "cd $SERVER_DIR && docker compose down" || true
echo "✅ Container stopped"
echo ""

# Step 2: Backup existing database
echo "💾 Backing up existing database..."
BACKUP_NAME="tweight.db.backup-before-uc003-$(date +%Y%m%d-%H%M%S)"
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" "
    if [ -f $SERVER_DIR/data/tweight.db ]; then
        cp $SERVER_DIR/data/tweight.db $SERVER_DIR/data/$BACKUP_NAME
        echo 'Database backed up to: $BACKUP_NAME'
    else
        echo 'No existing database found - fresh install'
    fi
"
echo "✅ Backup completed"
echo ""

# Step 3: Copy application files
echo "📦 Copying application files..."

# Copy individual files
scp -i "$SSH_KEY" \
    Dockerfile \
    docker-compose.yml \
    main.py \
    database.py \
    models.py \
    schemas.py \
    requirements.txt \
    alembic.ini \
    docker-entrypoint.sh \
    .env.docker \
    "$SERVER_USER@$SERVER_IP:$SERVER_DIR/"

# Copy directories
scp -i "$SSH_KEY" -r auth/ "$SERVER_USER@$SERVER_IP:$SERVER_DIR/"
scp -i "$SSH_KEY" -r alembic/ "$SERVER_USER@$SERVER_IP:$SERVER_DIR/"

echo "✅ Files copied"
echo ""

# Step 4: Configure environment
echo "🔧 Configuring environment..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" "
    cd $SERVER_DIR

    # Copy .env.docker to .env (contains Clerk keys)
    cp .env.docker .env

    # Make entrypoint executable
    chmod +x docker-entrypoint.sh

    echo 'Environment configured'
"
echo "✅ Configuration complete"
echo ""

# Step 5: Rebuild and start container
echo "🔨 Rebuilding Docker image..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" "cd $SERVER_DIR && docker compose build"
echo "✅ Image rebuilt"
echo ""

echo "🚀 Starting container..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" "cd $SERVER_DIR && docker compose up -d"
echo "✅ Container started"
echo ""

# Step 6: Watch migration logs
echo "📋 Checking migration logs..."
sleep 3
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" "cd $SERVER_DIR && docker compose logs --tail=50" | grep -A 10 "Running database migrations"
echo ""

# Step 7: Test deployment
echo "🧪 Testing deployment..."
sleep 5

# Test health endpoint
echo "Testing health endpoint..."
HEALTH_RESPONSE=$(ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" "curl -s http://localhost:8000/health")
if echo "$HEALTH_RESPONSE" | grep -q "ok"; then
    echo "✅ Health check passed: $HEALTH_RESPONSE"
else
    echo "❌ Health check failed: $HEALTH_RESPONSE"
    exit 1
fi

# Test authentication requirement
echo "Testing authentication requirement..."
AUTH_RESPONSE=$(ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" "curl -s -w '\n%{http_code}' http://localhost:8000/videos" | tail -1)
if [ "$AUTH_RESPONSE" = "422" ] || [ "$AUTH_RESPONSE" = "401" ]; then
    echo "✅ Authentication is required (HTTP $AUTH_RESPONSE)"
else
    echo "❌ Expected 401/422, got HTTP $AUTH_RESPONSE"
fi

echo ""
echo "🎉 UC-003 Deployment Complete!"
echo "================================"
echo ""
echo "✅ Backend deployed: https://api.chrisbuilds64.com"
echo "✅ Health endpoint: https://api.chrisbuilds64.com/health"
echo "✅ Authentication: Clerk (production)"
echo "✅ Database: Migrated with users + user_id"
echo ""
echo "📝 Next steps:"
echo "1. Test from browser: https://api.chrisbuilds64.com/health"
echo "2. Update Flutter app with production URL"
echo "3. Test authentication from iPhone"
echo ""
echo "📊 Monitor logs:"
echo "   ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP 'cd $SERVER_DIR && docker compose logs -f'"
echo ""
