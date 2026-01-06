# Environment Configuration System

**Status:** ✅ BULLETPROOF - Never touch .env files manually again!
**Created:** January 6, 2026
**Purpose:** One command to switch between dev/prod environments

---

## 🎯 The Problem This Solves

**Before (TERRIBLE):**
```bash
# Backend
ENV=development docker-compose up  # Easy to forget!
# Flutter
# Manually edit lib/config/environment.dart
# Hope you didn't forget to switch back...
```

**Result:** Production bugs, wrong API calls, environment confusion!

---

## ✅ The Solution (ONE COMMAND)

```bash
./env.sh dev    # Development (localhost)
./env.sh prod   # Production (api.chrisbuilds64.com)
```

**That's it!** Everything is set correctly:
- Backend .env file
- Flutter environment.dart
- All API URLs
- Auth settings

---

## 🚀 Usage

### Development (Local)
```bash
cd /Users/christianmoser/ChrisBuilds64/develop

# Switch to dev
./env.sh dev

# Start backend
cd core && docker-compose up -d

# Run Flutter app
cd ../tweight && flutter run
```

### Production (Deploy)
```bash
cd /Users/christianmoser/ChrisBuilds64/develop

# Switch to prod
./env.sh prod

# Deploy backend (see DEPLOY.md)
cd core && ./deploy.sh

# Build Flutter for release
cd ../tweight && flutter build ios --release
```

---

## 📁 What It Does

### 1. Loads Config
Reads from `config/{env}.env`:
- `config/dev.env` - Development settings
- `config/prod.env` - Production settings

### 2. Generates Backend Config
Creates `core/.env` for Docker:
```env
ENV=development  (or production)
CLERK_SECRET_KEY=...
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=...
```

### 3. Generates Flutter Config
Creates `tweight/lib/config/environment.dart`:
```dart
class Environment {
  static const String env = 'development';
  static const String baseUrl = 'http://localhost:8000';
  static const bool isDevelopment = true;
  static const bool isProduction = false;
}
```

---

## 🏗️ File Structure

```
/develop/
├── env.sh                    # ← THE MASTER SCRIPT
├── config/
│   ├── dev.env              # Development settings
│   └── prod.env             # Production settings
├── core/
│   ├── .env                 # ← Auto-generated (DO NOT EDIT!)
│   └── docker-compose.yml   # Uses env_file: .env
└── tweight/
    └── lib/config/
        └── environment.dart # ← Auto-generated (DO NOT EDIT!)
```

---

## ⚠️ Important Rules

### ✅ DO:
- Use `./env.sh dev` or `./env.sh prod` to switch
- Edit `config/dev.env` or `config/prod.env` if you need to change settings
- Commit `config/*.env` to version control

### ❌ DON'T:
- **NEVER** edit `core/.env` manually (auto-generated!)
- **NEVER** edit `tweight/lib/config/environment.dart` manually (auto-generated!)
- **NEVER** commit `core/.env` or `tweight/lib/config/environment.dart` (gitignored)

---

## 🔧 Configuration Options

### config/dev.env
```bash
# Backend Settings
ENV=development
BACKEND_URL=http://localhost:8000

# Flutter Settings
FLUTTER_ENV=development
API_URL=http://localhost:8000

# Auth (Mock for development)
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
```

### config/prod.env
```bash
# Backend Settings
ENV=production
BACKEND_URL=https://api.chrisbuilds64.com

# Flutter Settings
FLUTTER_ENV=production
API_URL=https://api.chrisbuilds64.com

# Auth (Clerk for production)
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
```

---

## 🐛 Troubleshooting

### "Command not found: ./env.sh"
```bash
chmod +x env.sh
```

### "Config file not found"
```bash
# Check available configs
ls -1 config/*.env

# Make sure you're in /develop/ directory
cd /Users/christianmoser/ChrisBuilds64/develop
```

### Backend still using old env
```bash
# Restart Docker to pick up new .env
cd core
docker-compose down
docker-compose up -d
```

### Flutter still using old URL
```bash
# env.sh already regenerated environment.dart
# Just rebuild/restart Flutter app
flutter run
```

---

## 📝 Adding New Environments

Want to add staging? Easy:

1. Create `config/staging.env`:
```bash
ENV=staging
BACKEND_URL=https://staging.chrisbuilds64.com
FLUTTER_ENV=staging
API_URL=https://staging.chrisbuilds64.com
```

2. Use it:
```bash
./env.sh staging
```

Done! No script changes needed.

---

## 🎯 Quick Reference

| Command | Backend URL | Flutter URL | Use Case |
|---------|-------------|-------------|----------|
| `./env.sh dev` | localhost:8000 | localhost:8000 | Local development |
| `./env.sh prod` | api.chrisbuilds64.com | api.chrisbuilds64.com | Production deploy |

---

## 🔒 Security Notes

- **Secrets in config files:** Currently using test Clerk keys
- **Production secrets:** Will need to be updated in `config/prod.env`
- **Never commit real secrets:** Use environment variables or secrets manager
- **.gitignore:** `core/.env` and `tweight/lib/config/environment.dart` are ignored

---

## 📚 Related Documentation

- [DEPLOY.md](core/DEPLOY.md) - How to deploy to production
- [CLAUDE.md](../control/CLAUDE.md) - Development principles
- [PROJECT-CONTEXT.md](../control/PROJECT-CONTEXT.md) - Project overview

---

## ✨ Benefits

**Before this system:**
- ❌ Manual env switching
- ❌ Easy to forget steps
- ❌ Production bugs from wrong config
- ❌ Confusion about which env is active

**With this system:**
- ✅ One command switches everything
- ✅ Impossible to forget a step
- ✅ Clear indication of active environment
- ✅ No more config-related bugs!

---

**Remember:**

**ONE COMMAND. EVERYTHING SET. ZERO MISTAKES.**

```bash
./env.sh dev    # or prod
```

---

**Author:** chrisbuilds64
**Created:** January 6, 2026 (after config confusion)
**Purpose:** Never let environment confusion happen again
**Status:** Production-ready ✅
