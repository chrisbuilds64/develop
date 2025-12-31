# SSL Certificate Setup - api.chrisbuilds64.com

Quick guide to enable HTTPS for the production API.

## Prerequisites

✅ DNS configured (api.chrisbuilds64.com → 82.165.165.199)
✅ nginx running on server
✅ API responding on HTTP (port 80)

## Step 1: Copy SSL Setup Script to Server

From your Mac:

```bash
cd ~/ChrisBuilds64/develop/core
scp setup-ssl.sh root@82.165.165.199:~/tweight-core/
```

## Step 2: Run SSL Setup on Server

SSH into your server:

```bash
ssh root@82.165.165.199
cd ~/tweight-core
chmod +x setup-ssl.sh
sudo ./setup-ssl.sh
```

The script will:
1. Check if certbot is installed (install if needed)
2. Verify nginx configuration
3. Check DNS resolution
4. Request SSL certificate from Let's Encrypt
5. Configure nginx for HTTPS
6. Set up auto-renewal

**You will be asked for:**
- Email address (for Let's Encrypt notifications)
- Agreement to Terms of Service
- Whether to redirect HTTP to HTTPS (choose Yes)

## Step 3: Verify SSL Works

```bash
# From server
curl https://api.chrisbuilds64.com/health

# From your Mac
curl https://api.chrisbuilds64.com/health
```

Expected response:
```json
{"status":"ok","service":"tweight-core","version":"0.2.0"}
```

## Step 4: Update Flutter App

Now update the Flutter app to use the production domain with HTTPS:

```bash
cd ~/ChrisBuilds64/develop/tweight
# Edit lib/config/environment.dart
# Change apiUrl to: https://api.chrisbuilds64.com
```

See [Flutter App Update Instructions](#flutter-app-update) below.

---

## Troubleshooting

### "DNS does not point to this server"

Wait a few minutes for DNS propagation, then try again:

```bash
dig +short api.chrisbuilds64.com
# Should return: 82.165.165.199
```

### "nginx configuration test failed"

Check nginx config:

```bash
sudo nginx -t
sudo tail -f /var/log/nginx/error.log
```

### Certificate renewal

Certificates auto-renew. Test renewal:

```bash
sudo certbot renew --dry-run
```

View certificates:

```bash
sudo certbot certificates
```

---

## Flutter App Update

After SSL is working, update the Flutter app:

### 1. Edit environment.dart

```dart
// lib/config/environment.dart
class Environment {
  static const String apiUrl = 'https://api.chrisbuilds64.com';  // Changed from http://192.168...
}
```

### 2. Test on iPhone

```bash
cd ~/ChrisBuilds64/develop/tweight
flutter run
```

- Add a video from YouTube
- Verify it saves
- Check tag filtering works

### 3. Rebuild and deploy

```bash
flutter build ios
# Then deploy to TestFlight or install on device
```

---

## Next Steps

After SSL is working:

1. ✅ Update Flutter app to production domain
2. ✅ Test all endpoints from mobile
3. ✅ Deploy to TestFlight (Apple Developer Account ready!)
4. ✅ Update UC-001 documentation
5. ✅ Write Day 7 post about production deployment

---

**Created:** December 31, 2025
**DNS Ready:** ✅ Yes
**SSL Status:** Pending (run setup-ssl.sh)
