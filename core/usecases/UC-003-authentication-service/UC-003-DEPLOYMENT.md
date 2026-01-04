# UC-003: Authentication Service - Deployment Guide

**Date:** January 3, 2026
**Status:** Ready for Deployment
**Target:** Strato VPS (api.chrisbuilds64.com)

---

## What's New in This Deployment

### UC-003 Authentication Features:
- ✅ Clerk authentication integration
- ✅ User management with auto-sync from Clerk
- ✅ JWT token verification
- ✅ User-specific video data (multi-user support)
- ✅ Database migrations with Alembic
- ✅ MockAdapter for testing (ENV=development)

### Files Added/Modified:
```
auth/                           # NEW - Auth module
├── __init__.py
├── base.py
├── clerk_adapter.py
├── mock_adapter.py
└── middleware.py

alembic/                        # NEW - Database migrations
├── versions/
│   └── 28cddbbc2522_*.py
├── env.py
└── script.py.mako

alembic.ini                     # NEW - Alembic config
docker-entrypoint.sh            # NEW - Runs migrations on startup
.env.docker                     # NEW - Docker environment template

Dockerfile                      # UPDATED - Includes auth + alembic
docker-compose.yml              # UPDATED - Clerk env vars
main.py                         # UPDATED - Protected endpoints
models.py                       # UPDATED - User model added
requirements.txt                # UPDATED - New dependencies
```

---

## Deployment Steps

### Step 1: Update Files on Server

From your local Mac:

```bash
cd ~/ChrisBuilds64/develop/core

# Stop the running container
ssh user@YOUR_SERVER_IP "cd ~/tweight-core && docker compose down"

# Copy new/updated files
scp -r auth/ user@YOUR_SERVER_IP:~/tweight-core/
scp -r alembic/ user@YOUR_SERVER_IP:~/tweight-core/
scp alembic.ini user@YOUR_SERVER_IP:~/tweight-core/
scp docker-entrypoint.sh user@YOUR_SERVER_IP:~/tweight-core/
scp .env.docker user@YOUR_SERVER_IP:~/tweight-core/.env
scp Dockerfile docker-compose.yml user@YOUR_SERVER_IP:~/tweight-core/
scp main.py models.py requirements.txt user@YOUR_SERVER_IP:~/tweight-core/

# Make entrypoint executable
ssh user@YOUR_SERVER_IP "chmod +x ~/tweight-core/docker-entrypoint.sh"
```

### Step 2: Verify Environment Variables on Server

SSH into server and check `.env` file:

```bash
ssh user@YOUR_SERVER_IP
cd ~/tweight-core
cat .env
```

Should contain:
```bash
CLERK_SECRET_KEY=sk_test_reM1dE57Mgu0QleqC1ZBjonz09YvUBAZtFGITLVMVJ
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_c21vb3RoLWxpb25maXNoLTg1LmNsZXJrLmFjY291bnRzLmRldiQ
```

### Step 3: Backup Existing Database

```bash
# On server
cd ~/tweight-core
cp data/tweight.db data/tweight.db.backup-before-uc003-$(date +%Y%m%d-%H%M%S)
```

### Step 4: Deploy Updated Application

```bash
# On server
cd ~/tweight-core

# Rebuild and start
docker compose build
docker compose up -d

# Watch logs
docker compose logs -f
```

You should see:
```
🚀 Starting Tweight Core API...
📦 Running database migrations...
INFO  [alembic.runtime.migration] Running upgrade  -> 28cddbbc2522, UC-003: Add User model and user_id to videos
✅ Database migrations completed successfully
🌐 Starting FastAPI server...
INFO:     Uvicorn running on http://0.0.0.0:8000
✅ Database initialized
```

### Step 5: Verify Deployment

```bash
# From server
curl http://localhost:8000/health
# Expected: {"status":"ok","service":"tweight-core","version":"0.3.0"}

# From your Mac
curl https://api.chrisbuilds64.com/health
# Expected: {"status":"ok","service":"tweight-core","version":"0.3.0"}

# Test auth is required (should get 401)
curl https://api.chrisbuilds64.com/videos
# Expected: 401 Unauthorized
```

---

## Testing with Mock Adapter (Optional)

If you want to test without Clerk first:

```bash
# On server, edit .env
cd ~/tweight-core
nano .env

# Change ENV to development
ENV=development

# Restart
docker compose restart

# Test with mock token
curl -X POST https://api.chrisbuilds64.com/videos \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-chris" \
  -d '{"url": "https://youtube.com/watch?v=test", "tags": ["test"]}'

# Should work! Returns 201 Created

# Switch back to production
nano .env  # Change ENV=production
docker compose restart
```

---

## Database Migration Details

The migration adds:

### Users Table:
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    provider_user_id VARCHAR UNIQUE NOT NULL,  -- Clerk user ID
    email VARCHAR NOT NULL,
    name VARCHAR,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
```

### Videos Table Update:
```sql
ALTER TABLE videos ADD COLUMN user_id INTEGER NOT NULL;
ALTER TABLE videos ADD FOREIGN KEY(user_id) REFERENCES users(id);
```

**Important:** If you have existing videos, they will be lost (migration creates fresh schema). That's OK for now since it's test data.

---

## Flutter App Update

After backend is deployed, update Flutter app:

### 1. Update environment.dart:

```dart
class Environment {
  static const String baseUrl = 'https://api.chrisbuilds64.com';
}
```

### 2. Deploy to iPhone:

```bash
cd ~/ChrisBuilds64/develop/tweight
flutter build ios
# Then deploy via Xcode or TestFlight
```

---

## Rollback Plan

If something goes wrong:

```bash
# On server
cd ~/tweight-core

# Stop new version
docker compose down

# Restore old database
cp data/tweight.db.backup-before-uc003-* data/tweight.db

# Restore old code (from git or re-copy old files)
# Then rebuild
docker compose up -d
```

---

## Monitoring After Deployment

### Watch logs for errors:
```bash
docker compose logs -f

# Filter for auth errors
docker compose logs | grep -i "auth\|401\|403"
```

### Check database:
```bash
# On server
docker exec -it tweight-core sqlite3 /app/data/tweight.db

# In SQLite:
.tables
SELECT * FROM users;
SELECT * FROM videos;
.quit
```

### Test from Flutter app:
1. Launch app on iPhone
2. Should show login screen
3. Sign in with chris@chrisbuilds64.com
4. Should see user's videos
5. Add a new video
6. Verify it appears in database

---

## Troubleshooting

### Migration fails:
```bash
# Check logs
docker compose logs

# Manual migration
docker exec -it tweight-core alembic upgrade head
```

### Clerk verification fails:
```bash
# Check env vars
docker exec tweight-core env | grep CLERK

# Test with mock adapter
# Edit .env: ENV=development
docker compose restart
```

### "No module named 'auth'":
```bash
# Verify auth/ directory copied
docker exec tweight-core ls -la /app/auth

# Rebuild if needed
docker compose build --no-cache
docker compose up -d
```

---

## Success Criteria

✅ Backend health check returns version 0.3.0
✅ /videos endpoint requires authentication (401 without token)
✅ Database has users and videos tables
✅ Alembic migration ran successfully
✅ Logs show no errors
✅ Flutter app can sign in with Clerk
✅ Videos are user-specific

---

## Next Steps After Deployment

1. Test with all 3 users (Chris, Lars, Lily)
2. Verify data isolation (users can't see each other's videos)
3. Monitor logs for first 24 hours
4. Set up automated database backups
5. Document actual deployment date/time

---

**Deployment Checklist:**
- [ ] Files copied to server
- [ ] .env configured with Clerk keys
- [ ] Database backed up
- [ ] Docker rebuild completed
- [ ] Container started successfully
- [ ] Migration logs show success
- [ ] Health check passes
- [ ] Auth endpoints require token
- [ ] Flutter app updated and tested

**Ready to deploy!** 🚀
