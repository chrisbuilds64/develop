# Tweight Core API - Production Deployment Guide

**Target Server:** Strato VPS Linux VC8-32
**Domain:** api.chrisbuilds64.com
**SSL:** Let's Encrypt

---

## Prerequisites

- Strato VPS Linux VC8-32 running
- SSH access to server
- Docker not yet installed (will be installed)
- Domain api.chrisbuilds64.com pointing to server IP

---

## Step 1: Install Docker on Strato VPS

SSH into your server and run:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add current user to docker group (to run docker without sudo)
sudo usermod -aG docker $USER

# Start Docker service
sudo systemctl enable docker
sudo systemctl start docker

# Install Docker Compose (if not included)
sudo apt install docker-compose-plugin -y

# Verify installation
docker --version
docker compose version

# Log out and back in for group changes to take effect
exit
```

---

## Step 2: Prepare Server Directory

```bash
# Create application directory
mkdir -p ~/tweight-core
cd ~/tweight-core

# Create data directory for SQLite database
mkdir -p data
```

---

## Step 3: Copy Files to Server

From your local Mac, copy the application files:

```bash
# From ~/ChrisBuilds64/develop/core/ directory
scp Dockerfile docker-compose.yml main.py database.py models.py schemas.py requirements.txt user@YOUR_SERVER_IP:~/tweight-core/

# Copy deployment script
scp deploy.sh user@YOUR_SERVER_IP:~/tweight-core/
ssh user@YOUR_SERVER_IP "chmod +x ~/tweight-core/deploy.sh"
```

---

## Step 4: Deploy Application

SSH into server and run:

```bash
cd ~/tweight-core
./deploy.sh
```

This will:
- Build the Docker image
- Start the container
- Run health checks
- Bind to port 8000

Test locally on server:
```bash
curl http://localhost:8000/health
```

Should return: `{"status":"ok","service":"tweight-core","version":"0.2.0"}`

---

## Step 5: Install and Configure Nginx

```bash
# Install nginx
sudo apt install nginx -y

# Install certbot for Let's Encrypt
sudo apt install certbot python3-certbot-nginx -y

# Copy nginx configuration
sudo cp ~/tweight-core/nginx.conf /etc/nginx/sites-available/tweight-api

# Create symlink
sudo ln -s /etc/nginx/sites-available/tweight-api /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

---

## Step 6: Obtain SSL Certificate

**IMPORTANT:** Before running this, ensure DNS is configured (see Step 7)!

```bash
# Obtain SSL certificate from Let's Encrypt
sudo certbot --nginx -d api.chrisbuilds64.com

# Follow prompts:
# - Enter email address
# - Agree to terms
# - Choose to redirect HTTP to HTTPS (recommended)

# Test auto-renewal
sudo certbot renew --dry-run
```

---

## Step 7: DNS Configuration

Contact Alex to configure DNS:

**Record Type:** A Record
**Hostname:** api.chrisbuilds64.com
**Points to:** [Your Strato VPS IP Address]
**TTL:** 3600 (or default)

Get your server IP:
```bash
curl ifconfig.me
```

---

## Step 8: Verify Deployment

```bash
# From server
curl https://api.chrisbuilds64.com/health

# From local Mac
curl https://api.chrisbuilds64.com/health

# Test timer endpoint
curl https://api.chrisbuilds64.com/timer

# Test videos endpoint
curl https://api.chrisbuilds64.com/videos
```

---

## Monitoring & Maintenance

### View Logs
```bash
# Application logs
docker compose logs -f

# Nginx logs
sudo tail -f /var/log/nginx/tweight-api-access.log
sudo tail -f /var/log/nginx/tweight-api-error.log
```

### Restart Application
```bash
cd ~/tweight-core
docker compose restart
```

### Update Application
```bash
cd ~/tweight-core

# Pull new code (if using git)
git pull

# Or re-copy files from local
# Then redeploy:
./deploy.sh
```

### Database Backup
```bash
# Backup SQLite database
cp ~/tweight-core/data/tweight.db ~/tweight-core/data/tweight.db.backup-$(date +%Y%m%d-%H%M%S)

# Automated backup (add to crontab)
# Daily at 3am:
# 0 3 * * * cp ~/tweight-core/data/tweight.db ~/tweight-core/data/tweight.db.backup-$(date +\%Y\%m\%d)
```

---

## Troubleshooting

### Container not starting
```bash
docker compose logs
docker compose ps
```

### Port already in use
```bash
sudo lsof -i :8000
sudo systemctl status nginx
```

### SSL certificate issues
```bash
sudo certbot certificates
sudo certbot renew --dry-run
```

### Nginx issues
```bash
sudo nginx -t
sudo systemctl status nginx
sudo journalctl -u nginx -f
```

---

## Security Notes

1. **Firewall:** Consider configuring UFW:
```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

2. **SSH:** Use key-based authentication, disable password login
3. **Updates:** Keep system updated regularly
4. **Backups:** Automate database backups

---

## Next Steps

After successful deployment:

1. ✅ Update Flutter app to use `https://api.chrisbuilds64.com`
2. ✅ Test all endpoints from mobile app
3. ✅ Monitor logs for first few days
4. ✅ Set up automated backups
5. ✅ Document in UC-001

---

**Deployed:** [Date]
**Server IP:** [Your IP]
**SSL Valid Until:** [Auto-renewed by certbot]
