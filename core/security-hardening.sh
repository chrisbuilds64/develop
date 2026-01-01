#!/bin/bash
# Security Hardening Script for Strato VPS
# Run as root: sudo ./security-hardening.sh

set -e

echo "========================================="
echo "Security Hardening - api.chrisbuilds64.com"
echo "========================================="
echo ""
echo "This script will:"
echo "  1. Enable UFW firewall (allow 80, 443, 22 only)"
echo "  2. Install and configure fail2ban (SSH protection)"
echo "  3. Add security headers to nginx"
echo "  4. Review open ports"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with sudo"
    exit 1
fi

echo ""
echo "========================================="
echo "Step 1: UFW Firewall"
echo "========================================="

# Install UFW if not present
if ! command -v ufw &> /dev/null; then
    echo "Installing UFW..."
    apt update
    apt install -y ufw
fi

# Configure UFW
echo "Configuring firewall rules..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS

echo "Enabling UFW..."
ufw --force enable

echo "✅ Firewall configured"
ufw status verbose

echo ""
echo "========================================="
echo "Step 2: fail2ban (SSH Protection)"
echo "========================================="

# Install fail2ban
if ! command -v fail2ban-client &> /dev/null; then
    echo "Installing fail2ban..."
    apt install -y fail2ban
fi

# Create fail2ban configuration
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
bantime = 7200
EOF

# Restart fail2ban
systemctl restart fail2ban
systemctl enable fail2ban

echo "✅ fail2ban configured"
fail2ban-client status

echo ""
echo "========================================="
echo "Step 3: nginx Security Headers"
echo "========================================="

# Check if nginx config exists
NGINX_CONF="/etc/nginx/sites-enabled/tweight-api"

if [ -f "$NGINX_CONF" ]; then
    echo "Adding security headers to nginx..."

    # Backup original config
    cp $NGINX_CONF ${NGINX_CONF}.backup

    # Check if security headers already exist
    if ! grep -q "X-Content-Type-Options" $NGINX_CONF; then
        # Add security headers in the location / block
        sed -i '/location \/ {/a \        # Security Headers\n        add_header X-Content-Type-Options "nosniff" always;\n        add_header X-Frame-Options "SAMEORIGIN" always;\n        add_header X-XSS-Protection "1; mode=block" always;\n        add_header Referrer-Policy "strict-origin-when-cross-origin" always;' $NGINX_CONF

        echo "Testing nginx configuration..."
        nginx -t

        if [ $? -eq 0 ]; then
            echo "Reloading nginx..."
            systemctl reload nginx
            echo "✅ Security headers added"
        else
            echo "❌ nginx config test failed, restoring backup"
            mv ${NGINX_CONF}.backup $NGINX_CONF
            exit 1
        fi
    else
        echo "✅ Security headers already configured"
    fi
else
    echo "⚠️  nginx config not found at $NGINX_CONF"
    echo "   Manual configuration needed"
fi

echo ""
echo "========================================="
echo "Step 4: Review Open Ports"
echo "========================================="

echo "Listening ports:"
ss -tulpn | grep LISTEN

echo ""
echo "========================================="
echo "✅ Security Hardening Complete!"
echo "========================================="
echo ""
echo "Summary:"
echo "  ✅ UFW Firewall enabled (SSH, HTTP, HTTPS only)"
echo "  ✅ fail2ban protecting SSH (3 failed attempts = 2h ban)"
echo "  ✅ nginx security headers configured"
echo ""
echo "Next steps:"
echo "  1. Monitor fail2ban: sudo fail2ban-client status sshd"
echo "  2. Check firewall: sudo ufw status"
echo "  3. Review nginx logs: sudo tail -f /var/log/nginx/access.log"
echo ""
echo "⚠️  IMPORTANT: Make sure you can still SSH in!"
echo "   Test in a NEW terminal before closing this one."
echo ""
