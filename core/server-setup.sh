#!/bin/bash
# Tweight Core API - Complete Server Setup Script
# Run this on the Strato VPS after initial SSH connection
#
# Usage: bash server-setup.sh

set -e  # Exit on error

echo "🚀 Tweight Core API - Server Setup"
echo "===================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Please run as root (or use sudo)${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Running as root${NC}"
echo ""

# Step 1: System Update
echo -e "${YELLOW}📦 Step 1: Updating system...${NC}"
apt update && apt upgrade -y
echo -e "${GREEN}✅ System updated${NC}"
echo ""

# Step 2: Install Docker
echo -e "${YELLOW}🐳 Step 2: Installing Docker...${NC}"
if command -v docker &> /dev/null; then
    echo "Docker already installed: $(docker --version)"
else
    # Install prerequisites
    apt install -y ca-certificates curl gnupg lsb-release

    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Add Docker repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Enable and start Docker
    systemctl enable docker
    systemctl start docker

    echo -e "${GREEN}✅ Docker installed: $(docker --version)${NC}"
fi
echo ""

# Step 3: Install nginx
echo -e "${YELLOW}🌐 Step 3: Installing nginx...${NC}"
if command -v nginx &> /dev/null; then
    echo "nginx already installed: $(nginx -v 2>&1)"
else
    apt install -y nginx
    systemctl enable nginx
    systemctl start nginx
    echo -e "${GREEN}✅ nginx installed${NC}"
fi
echo ""

# Step 4: Install certbot for SSL
echo -e "${YELLOW}🔒 Step 4: Installing certbot...${NC}"
if command -v certbot &> /dev/null; then
    echo "certbot already installed: $(certbot --version)"
else
    apt install -y certbot python3-certbot-nginx
    echo -e "${GREEN}✅ certbot installed${NC}"
fi
echo ""

# Step 5: Configure firewall
echo -e "${YELLOW}🔥 Step 5: Configuring firewall...${NC}"
if command -v ufw &> /dev/null; then
    ufw --force enable
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp    # SSH
    ufw allow 80/tcp    # HTTP
    ufw allow 443/tcp   # HTTPS
    ufw --force enable
    echo -e "${GREEN}✅ Firewall configured${NC}"
    ufw status
else
    echo -e "${YELLOW}⚠️  UFW not available, skipping firewall setup${NC}"
fi
echo ""

# Step 6: Create application directory
echo -e "${YELLOW}📁 Step 6: Creating application directory...${NC}"
mkdir -p /opt/tweight-core
mkdir -p /opt/tweight-core/data
echo -e "${GREEN}✅ Application directory created: /opt/tweight-core${NC}"
echo ""

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Server Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "1. Copy application files to /opt/tweight-core/"
echo "2. Run deployment: cd /opt/tweight-core && ./deploy.sh"
echo "3. Configure nginx with SSL"
echo "4. Point DNS to this server"
echo ""
echo -e "${YELLOW}📊 Installed Software:${NC}"
docker --version
docker compose version
nginx -v 2>&1
certbot --version
echo ""
echo -e "${YELLOW}🌐 Server IP:${NC}"
curl -s ifconfig.me
echo ""
echo ""
