# Authentication Quick Start Guide

**UC-003 Authentication System** - Ready to use! ✅

---

## 🚀 Getting Started (Local Development)

### **1. Start the Server**

```bash
cd /Users/christianmoser/ChrisBuilds64/develop/core
source venv/bin/activate
uvicorn main:app --reload
```

The server will automatically:
- Load `.env` file (ENV=development)
- Use MockAuthAdapter (no Clerk account needed)
- Start on http://localhost:8000

---

## 🔑 Mock Authentication Tokens

Use these tokens for local development:

### **Available Test Users:**

| Token | User ID | Email | Name |
|-------|---------|-------|------|
| `test-chris` | mock-user-chris-123 | chris@test.com | Chris (Mock) |
| `test-lars` | mock-user-lars-456 | lars@test.com | Lars (Mock) |
| `test-lily` | mock-user-lily-789 | lily@test.com | Lily (Mock) |

You can also use:
- `mock-chris`, `mock-lars`, `mock-lily`
- Any token starting with `test-*` or `mock-*` will work

---

## 📝 API Examples

### **1. Health Check (No Auth Required)**

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "ok",
  "service": "tweight-core",
  "version": "0.3.0"
}
```

---

### **2. Create Video (Auth Required)**

```bash
curl -X POST http://localhost:8000/videos \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-chris" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "tags": ["workout", "triceps"]
  }'
```

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "title": null,
  "thumbnail_url": "https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
  "tags": "workout,triceps",
  "created_at": "2026-01-03T10:57:04.958112"
}
```

---

### **3. List Videos (User-Specific)**

```bash
# Chris's videos
curl http://localhost:8000/videos \
  -H "Authorization: Bearer test-chris"

# Lars's videos (different user = different data!)
curl http://localhost:8000/videos \
  -H "Authorization: Bearer test-lars"
```

**Response:**
```json
{
  "videos": [
    {
      "id": 1,
      "user_id": 1,
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "title": null,
      "thumbnail_url": "https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
      "tags": "workout,triceps",
      "created_at": "2026-01-03T10:57:04.958112"
    }
  ],
  "count": 1
}
```

---

### **4. Delete Video (Authorization Check)**

```bash
# Delete own video (works)
curl -X DELETE http://localhost:8000/videos/1 \
  -H "Authorization: Bearer test-chris"

# Try to delete another user's video (fails with 404)
curl -X DELETE http://localhost:8000/videos/1 \
  -H "Authorization: Bearer test-lars"
```

**Success Response:** 204 No Content

**Unauthorized Response:**
```json
{
  "detail": "Video not found or not authorized to delete"
}
```

---

## ❌ Error Responses

### **Missing Authorization Header:**

```bash
curl http://localhost:8000/videos
```

**Response: 401 Unauthorized**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["header", "authorization"],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

---

### **Invalid Token:**

```bash
curl http://localhost:8000/videos \
  -H "Authorization: Bearer invalid-token"
```

**Response: 401 Unauthorized**
```json
{
  "detail": "Invalid mock token. Use 'test-*' or 'mock-*' for local development."
}
```

---

## 🔄 Database Migrations

### **View Current Migration Status:**

```bash
alembic current
```

### **Apply Migrations:**

```bash
alembic upgrade head
```

### **Create New Migration:**

```bash
alembic revision --autogenerate -m "Description of changes"
```

### **Rollback Migration:**

```bash
alembic downgrade -1
```

---

## 🌍 Environment Configuration

### **Local Development (.env):**

```bash
ENV=development
DATABASE_URL=sqlite:///./tweight.db
# CLERK_SECRET_KEY not needed for development
```

### **Production (.env):**

```bash
ENV=production
DATABASE_URL=sqlite:////app/data/tweight.db
CLERK_SECRET_KEY=sk_test_your_secret_key_here
```

---

## 🧪 Testing

### **Run Comprehensive Test Suite:**

```bash
# Start server first
uvicorn main:app --host 127.0.0.1 --port 8000 &

# Run tests
/tmp/test-auth-complete.sh
```

### **Manual Testing Checklist:**

- [ ] Health check works (no auth)
- [ ] Create video with test-chris
- [ ] List videos as test-chris (see video)
- [ ] List videos as test-lars (empty list)
- [ ] Try to delete chris's video as lars (404)
- [ ] Delete own video as chris (success)

---

## 🐛 Troubleshooting

### **Server won't start:**

```bash
# Check if port is in use
lsof -i :8000

# Kill existing process
pkill -f uvicorn

# Check .env file exists and has ENV=development
cat .env
```

### **"Invalid token" errors:**

- Make sure token starts with `test-` or `mock-`
- Check ENV=development in .env file
- Restart server after changing .env

### **Database errors:**

```bash
# Reset database (WARNING: Deletes all data)
rm tweight.db
alembic upgrade head
```

---

## 📚 Additional Resources

- **Full Implementation Docs:** `usecases/UC-003-COMPLETION-SUMMARY.md`
- **Architecture Review:** `usecases/UC-003-ARCHITECTURE-REVIEW.md`
- **Implementation Status:** `usecases/UC-003-IMPLEMENTATION-STATUS.md`
- **Main Code:** `main.py`, `auth/middleware.py`, `models.py`

---

## ✅ Quick Verification

Run this to verify everything works:

```bash
# 1. Start server
uvicorn main:app --host 127.0.0.1 --port 8000 &

# 2. Health check
curl http://localhost:8000/health

# 3. Create video
curl -X POST http://localhost:8000/videos \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-chris" \
  -d '{"url": "https://youtube.com/watch?v=test", "tags": ["test"]}'

# 4. List videos
curl http://localhost:8000/videos \
  -H "Authorization: Bearer test-chris"

# 5. Stop server
pkill -f uvicorn
```

If all 4 commands work → **Everything is set up correctly!** ✅

---

**Happy coding! 🚀**
