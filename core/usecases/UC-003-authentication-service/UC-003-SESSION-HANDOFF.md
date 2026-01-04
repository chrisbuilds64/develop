# UC-003: Authentication Service - Session Handoff

**Date:** January 4, 2026
**Status:** ✅ LOCAL COMPLETE | ⏳ PRODUCTION DEPLOYMENT READY
**Next Action:** Deploy to Strato VPS

---

## 🎯 CURRENT STATE

### What's Done ✅

**Backend (100% Complete):**
- ✅ Auth module with Adapter Pattern (Clerk + Mock)
- ✅ User model + Video.user_id foreign key
- ✅ Alembic migrations configured
- ✅ All 10 integration tests passing
- ✅ Docker local deployment verified
- ✅ Migrations run automatically on container startup
- ✅ Health checks passing
- ✅ Authentication endpoints working correctly

**Configuration:**
- ✅ SERVER-CONFIG.md - Central server configuration reference
- ✅ .env configured for local dev
- ✅ .env.docker configured for production
- ✅ Clerk account active with 3 test users
- ✅ docker-entrypoint.sh runs migrations on startup
- ✅ deploy-uc003.sh ready for production deployment

**Testing:**
- ✅ All authentication flows tested locally
- ✅ Data isolation verified (users see only their own videos)
- ✅ Authorization verified (users can only delete their own data)
- ✅ Docker container healthy and stable

---

## 🚀 NEXT STEPS

### 1. Production Deployment to Strato VPS

**Command:**
```bash
cd ~/ChrisBuilds64/develop/core
./deploy-uc003.sh
```

**What it does:**
1. SSH to server: `root@82.165.165.199` (via `~/.ssh/strato_vps`)
2. Stops running container
3. Backs up existing database
4. Copies UC-003 files (auth/, alembic/, etc.)
5. Configures environment (.env.docker → .env)
6. Rebuilds Docker image
7. Starts container with migrations
8. Verifies health and authentication

**Expected outcome:**
- Container running with UC-003 auth enabled
- Database migrated with users + user_id
- API requires authentication
- https://api.chrisbuilds64.com/health returns 200 OK
- https://api.chrisbuilds64.com/videos returns 401/422 (auth required)

---

### 2. Flutter App Integration

**Add Clerk SDK:**
```yaml
# pubspec.yaml
dependencies:
  clerk_flutter: ^latest_version  # Check pub.dev for latest
```

**Create LoginScreen:**
- Email/password form
- Clerk sign-in API call
- Store JWT token in FlutterSecureStorage
- Navigate to main app on success

**Update VideoService:**
```dart
// Add auth headers to all API calls
final token = await _authService.getToken();
headers: {
  'Authorization': 'Bearer $token',
  'Content-Type': 'application/json',
}
```

**Files to create/modify:**
- `lib/services/auth_service.dart` - Clerk authentication
- `lib/screens/login_screen.dart` - Login UI
- `lib/main.dart` - Auth check on startup
- Update `lib/services/video_service.dart` - Add auth headers

**Reference:**
See `/develop/tweight/CLERK-INTEGRATION.md` for detailed Flutter integration steps.

---

### 3. End-to-End Testing

1. Deploy backend to production (deploy-uc003.sh)
2. Update Flutter app with Clerk integration
3. Build and deploy to iPhone
4. Test complete flow:
   - App opens → Login screen shows
   - Sign in with chris@chrisbuilds64.com
   - Main app loads
   - Save a video → API call succeeds
   - Video appears in list
   - Sign out → Login screen returns
   - Sign in as lars@chrisbuilds64.com
   - Verify Lars doesn't see Chris's videos

---

## 📁 KEY FILES REFERENCE

### Backend Files

**Authentication Module:**
- `/develop/core/auth/base.py` - Abstract AuthProvider interface
- `/develop/core/auth/clerk_adapter.py` - Clerk JWT verification
- `/develop/core/auth/mock_adapter.py` - Local testing adapter
- `/develop/core/auth/middleware.py` - FastAPI dependency injection

**Database:**
- `/develop/core/models.py` - User model + Video.user_id
- `/develop/core/alembic/versions/28cddbbc2522_*.py` - UC-003 migration
- `/develop/core/database.py` - SQLAlchemy setup

**Deployment:**
- `/develop/core/deploy-uc003.sh` - **Main deployment script**
- `/develop/core/docker-entrypoint.sh` - Container startup (runs migrations)
- `/develop/core/Dockerfile` - Updated with auth/, alembic/
- `/develop/core/docker-compose.yml` - Updated with Clerk env vars
- `/develop/core/.env.docker` - Production environment template

**Documentation:**
- `/develop/core/usecases/UC-003-COMPLETION-SUMMARY.md` - Complete implementation details
- `/develop/core/UC-003-DEPLOYMENT.md` - Deployment guide
- `/control/SERVER-CONFIG.md` - Server configuration reference

### Flutter Files (To Be Created)

- `/develop/tweight/lib/services/auth_service.dart`
- `/develop/tweight/lib/screens/login_screen.dart`
- `/develop/tweight/CLERK-INTEGRATION.md` - Flutter integration guide

---

## 🔧 TROUBLESHOOTING

### If Deployment Fails

**Check SSH connection:**
```bash
ssh -i ~/.ssh/strato_vps root@82.165.165.199 "echo 'Connection OK'"
```

**Check container logs:**
```bash
ssh -i ~/.ssh/strato_vps root@82.165.165.199 "cd /opt/tweight-core && docker compose logs"
```

**Manual deployment steps:**
```bash
# SSH to server
ssh -i ~/.ssh/strato_vps root@82.165.165.199

# Navigate to app directory
cd /opt/tweight-core

# Stop container
docker compose down

# Backup database
cp data/tweight.db data/tweight.db.backup-$(date +%Y%m%d-%H%M%S)

# Check files are present
ls -la auth/ alembic/ docker-entrypoint.sh

# Rebuild
docker compose build

# Start
docker compose up -d

# Watch logs
docker compose logs -f
```

### If Migrations Fail

```bash
# Access container
docker exec -it tweight-core bash

# Check Alembic status
alembic current

# Run migrations manually
alembic upgrade head

# Check database schema
sqlite3 /app/data/tweight.db ".schema"
```

### If Authentication Doesn't Work

**Check environment variables:**
```bash
docker exec tweight-core env | grep -E "ENV|CLERK"
```

**Expected:**
```
ENV=production
CLERK_SECRET_KEY=sk_test_reM1dE57Mgu0QleqC1ZBjonz09YvUBAZtFGITLVMVJ
```

**Test with curl:**
```bash
# Should return 401 or 422
curl https://api.chrisbuilds64.com/videos

# Should return 200
curl https://api.chrisbuilds64.com/health
```

---

## 🎓 KEY DECISIONS

**Adapter Pattern:**
- Enables local development without Clerk account
- Makes testing fast and reliable
- Allows future auth provider changes (Auth0, Supabase, etc.)

**Monolith Architecture:**
- Start simple with single container
- Code structured in clear modules (auth/, models, etc.)
- Easy to split into microservices later if needed

**Alembic Migrations:**
- Automatic migrations on container startup
- Database schema versioned
- Safe rollback capability

**Environment-Based Auth:**
- ENV=development → MockAdapter (test-chris, test-lars, test-lily)
- ENV=production → ClerkAdapter (real JWT verification)
- Automatic switching, no code changes

---

## 📊 METRICS

**Implementation Time:** ~1h 45min (vs. 2.5h estimate)
**Code Added:** ~570 lines total
**Tests:** 10/10 passing
**Local Docker:** ✅ Verified
**Production:** ⏳ Ready to deploy

---

## ✅ PRE-DEPLOYMENT CHECKLIST

Before running `./deploy-uc003.sh`:

- [ ] SSH key exists: `ls -la ~/.ssh/strato_vps`
- [ ] SSH connection works: `ssh -i ~/.ssh/strato_vps root@82.165.165.199 "echo OK"`
- [ ] Local Docker tested: `docker ps | grep tweight-core`
- [ ] All scripts executable: `ls -la deploy-uc003.sh docker-entrypoint.sh`
- [ ] .env.docker has correct Clerk keys
- [ ] Backup of production database recommended

**Ready to deploy!** 🚀

---

## 🔄 POST-DEPLOYMENT CHECKLIST

After running `./deploy-uc003.sh`:

- [ ] Container started: `docker ps`
- [ ] Migrations ran: Check logs for "Database migrations completed successfully"
- [ ] Health check passes: `curl https://api.chrisbuilds64.com/health`
- [ ] Auth required: `curl https://api.chrisbuilds64.com/videos` returns 401/422
- [ ] No errors in logs: `docker compose logs | grep -i error`
- [ ] Database has users table: `sqlite3 data/tweight.db ".tables"`
- [ ] Clerk keys loaded: `docker exec tweight-core env | grep CLERK`

---

## 📞 SUPPORT & REFERENCE

**Strato VPS:**
- IP: 82.165.165.199
- Domain: api.chrisbuilds64.com
- User: root
- SSH Key: ~/.ssh/strato_vps
- App Directory: /opt/tweight-core

**Clerk:**
- Dashboard: https://dashboard.clerk.com/
- Test Users: chris@, lars@, lily@ @chrisbuilds64.com
- API Key: In .env.docker

**Documentation:**
- Server Config: `/control/SERVER-CONFIG.md`
- Project Context: `/control/PROJECT-CONTEXT.md`
- Architecture: `/develop/ARCHITECTURE.md`
- Security: `/develop/core/SECURITY.md`

---

**Last Updated:** January 4, 2026
**Next Session:** Deploy to production + Flutter integration
**Status:** ✅ Ready for deployment
