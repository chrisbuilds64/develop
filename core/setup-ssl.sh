#!/bin/bash
# SSL Certificate Setup for api.chrisbuilds64.com
# Run this script on the Strato VPS server

set -e  # Exit on error

echo "========================================="
echo "SSL Certificate Setup for api.chrisbuilds64.com"
echo "========================================="
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script needs sudo privileges. Please run with sudo or as root."
    exit 1
fi

# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "Error: nginx is not installed. Please install nginx first."
    exit 1
fi

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    echo "Certbot not found. Installing certbot..."
    apt update
    apt install -y certbot python3-certbot-nginx
fi

# Test nginx configuration
echo "Testing nginx configuration..."
nginx -t

if [ $? -ne 0 ]; then
    echo "Error: nginx configuration test failed. Please fix nginx config first."
    exit 1
fi

# Check DNS resolution
echo ""
echo "Checking DNS resolution for api.chrisbuilds64.com..."
RESOLVED_IP=$(dig +short api.chrisbuilds64.com A | tail -n1)
SERVER_IP=$(curl -4 -s ifconfig.me)

echo "Domain resolves to: $RESOLVED_IP"
echo "Server IP is: $SERVER_IP"

if [ "$RESOLVED_IP" != "$SERVER_IP" ]; then
    echo "Warning: DNS does not point to this server!"
    echo "Expected: $SERVER_IP"
    echo "Got: $RESOLVED_IP"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Obtain SSL certificate
echo ""
echo "Obtaining SSL certificate from Let's Encrypt..."
echo "This will:"
echo "  1. Request a certificate for api.chrisbuilds64.com"
echo "  2. Automatically configure nginx"
echo "  3. Set up auto-renewal"
echo ""

# Email for Let's Encrypt notifications
EMAIL="chris@chrisbuilds64.com"

certbot --nginx -d api.chrisbuilds64.com --non-interactive --agree-tos --email "$EMAIL"

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo "✅ SSL Certificate successfully installed!"
    echo "========================================="
    echo ""
    echo "Your API is now available at:"
    echo "  https://api.chrisbuilds64.com"
    echo ""
    echo "Certificate will auto-renew via cron job."
    echo ""
    echo "Test auto-renewal with:"
    echo "  sudo certbot renew --dry-run"
    echo ""
    echo "Next steps:"
    echo "  1. Test HTTPS endpoint: curl https://api.chrisbuilds64.com/health"
    echo "  2. Update Flutter app to use https://api.chrisbuilds64.com"
    echo "  3. Test from mobile app"
    echo ""
else
    echo ""
    echo "❌ SSL certificate installation failed!"
    echo "Check the error messages above."
    exit 1
fi
