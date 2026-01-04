# Adapter Principle - Core Architecture Rule

**Date:** January 4, 2026
**Status:** 🔴 FUNDAMENTAL PRINCIPLE - ALWAYS ENFORCE

---

## Core Principle

**Our API encapsulates ALL native/external APIs. Clients NEVER call external services directly.**

### The Rule

> **Frontend (Flutter/Web/Mobile) → Our Core API → External Service**
>
> ❌ **NEVER:** Frontend → External Service (Clerk, OpenAI, etc.)
>
> ✅ **ALWAYS:** Frontend → Core API → External Service

---

## Why This Matters

### 1. **Abstraction = Freedom**
We can swap external services without touching client code:
- Clerk → Supertokens → Custom auth
- OpenAI → Claude → Ollama (local)
- YouTube API → Vimeo API → Custom scraper

### 2. **KISS in Practice**
Clients stay simple:
```dart
// Flutter only knows about OUR API
authService.signIn(email, password)  // ✅ Simple
videoService.getVideos()             // ✅ Simple

// Not this mess:
clerkClient.signIn(...)              // ❌ External dependency
videoService.authenticateWith(...)   // ❌ Client knows too much
```

### 3. **Use Case Driven**
Use case defines WHAT, not HOW:
- UC: "User needs AI chat completion"
- Frontend calls: `POST /ai/complete` with prompt
- Backend decides: Ollama (local), Claude API, or ChatGPT
- Frontend doesn't care, doesn't know, doesn't change

### 4. **Future-Proof**
Technology changes, business needs change, providers change.
- **With adapters:** Change backend config, deploy
- **Without adapters:** Rewrite all clients, redeploy everywhere

---

## Implementation Pattern

### Backend Structure
```
core/
├── api/                    # Public API endpoints (stable interface)
│   ├── auth.py            # POST /auth/login, /auth/logout
│   ├── videos.py          # GET /videos, POST /videos
│   └── ai.py              # POST /ai/complete, /ai/chat
│
├── adapters/              # External service wrappers (swappable)
│   ├── auth/
│   │   ├── base.py        # AuthProvider interface
│   │   ├── clerk.py       # ClerkAdapter
│   │   ├── supertokens.py # SupertokensAdapter
│   │   └── mock.py        # MockAdapter (testing)
│   │
│   ├── ai/
│   │   ├── base.py        # AIProvider interface
│   │   ├── claude.py      # ClaudeAdapter
│   │   ├── openai.py      # OpenAIAdapter
│   │   └── ollama.py      # OllamaAdapter (local)
│   │
│   └── storage/
│       ├── base.py        # StorageProvider interface
│       ├── s3.py          # S3Adapter
│       └── local.py       # LocalFileAdapter
```

### Configuration-Driven Selection
```python
# Environment determines which adapter to use
AUTH_PROVIDER = os.getenv("AUTH_PROVIDER", "clerk")  # clerk, supertokens, mock
AI_PROVIDER = os.getenv("AI_PROVIDER", "claude")     # claude, openai, ollama
STORAGE_PROVIDER = os.getenv("STORAGE_PROVIDER", "local")  # s3, local

# Backend instantiates correct adapter
auth = get_auth_provider(AUTH_PROVIDER)
ai = get_ai_provider(AI_PROVIDER)
storage = get_storage_provider(STORAGE_PROVIDER)
```

### Frontend Stays Dumb (Good!)
```dart
// Flutter ONLY knows about our API
class AuthService {
  Future<String> signIn(String email, String password) async {
    // Calls OUR API, not Clerk/Supertokens/etc
    final response = await http.post(
      Uri.parse('${Environment.baseUrl}/auth/login'),
      body: jsonEncode({'email': email, 'password': password}),
    );
    return response.data['token'];
  }
}

class AIService {
  Future<String> complete(String prompt) async {
    // Calls OUR API, backend decides: Claude, ChatGPT, or Ollama
    final response = await http.post(
      Uri.parse('${Environment.baseUrl}/ai/complete'),
      body: jsonEncode({'prompt': prompt}),
    );
    return response.data['completion'];
  }
}
```

---

## Real-World Examples

### Example 1: Authentication
**Today:** Clerk
**Tomorrow:** Supertokens
**Next month:** Custom JWT

**Client code changes:** ZERO
**Backend changes:**
1. Add `SupertokensAdapter` implementing `AuthProvider`
2. Change `AUTH_PROVIDER=supertokens` in `.env`
3. Deploy

### Example 2: AI Completion
**Use Case:** User asks AI a question

**Client Request:**
```http
POST /ai/complete
{
  "prompt": "Explain quantum physics in simple terms",
  "max_tokens": 500
}
```

**Backend Decision (via ENV):**
- `AI_PROVIDER=claude` → Use Claude API
- `AI_PROVIDER=openai` → Use ChatGPT API
- `AI_PROVIDER=ollama` → Use local Ollama model

**Client cares:** ZERO

### Example 3: Video Storage
**Today:** Local filesystem
**Tomorrow:** S3 for thumbnails
**Next year:** CDN for global distribution

**Client code:** `videoService.getThumbnail(videoId)`
**Backend handles:** Local file → S3 URL → CDN URL
**Client changes:** ZERO

---

## Anti-Patterns to Avoid

### ❌ DON'T: Direct External API Calls
```dart
// BAD: Client knows about Clerk
import 'package:clerk_flutter/clerk_flutter.dart';

final clerkClient = Clerk(publishableKey: '...');
await clerkClient.signIn(email, password);
```

### ❌ DON'T: Client-Side Provider Selection
```dart
// BAD: Client chooses which AI to use
if (useOpenAI) {
  await openAIClient.complete(prompt);
} else {
  await claudeClient.complete(prompt);
}
```

### ❌ DON'T: Environment-Specific Client Code
```dart
// BAD: Client has production vs development logic
final baseUrl = isProduction
  ? 'https://clerk.com'
  : 'http://localhost:3000';
```

### ✅ DO: Single Abstraction Layer
```dart
// GOOD: Client only knows about OUR API
final authService = AuthService();
await authService.signIn(email, password);

final aiService = AIService();
await aiService.complete(prompt);
```

---

## Benefits Recap

1. **Swap providers in minutes** (config change + deploy)
2. **Clients stay simple** (only know OUR interface)
3. **Test easily** (mock adapters for dev/test)
4. **Scale independently** (backend handles complexity)
5. **Cost optimization** (switch to cheaper provider without client changes)
6. **Multi-provider support** (load balancing, failover)

---

## Enforcement Checklist

Before adding ANY external API integration:

- [ ] Does the client call it directly? **→ NO! Create adapter**
- [ ] Is the external API name in client code? **→ NO! Use generic interface**
- [ ] Can we swap this service without changing clients? **→ YES! That's the goal**
- [ ] Does the adapter implement a base interface? **→ YES! Always**
- [ ] Is provider selection config-driven? **→ YES! Environment variable**

---

## Decision Record

**Decision:** All external services MUST be accessed through Core API adapters.

**Rationale:**
- Abstraction enables flexibility (swap providers)
- KISS for clients (simple, stable interface)
- Use Case driven (client requests WHAT, not HOW)
- Future-proof (technology changes don't cascade)

**Consequences:**
- ✅ Provider changes are backend-only
- ✅ Clients are simpler, more stable
- ✅ Testing is easier (mock adapters)
- ⚠️ Backend is more complex (but that's OUR job)
- ⚠️ Slight latency overhead (acceptable tradeoff)

**Examples:**
- Auth: Clerk → Supertokens → Custom (client unchanged)
- AI: Claude → ChatGPT → Ollama (client unchanged)
- Storage: Local → S3 → CDN (client unchanged)

**Status:** 🔴 FUNDAMENTAL - Never violate this principle

---

**Related Documents:**
- [ARCHITECTURE.md](ARCHITECTURE.md) - Overall architecture vision
- [CLAUDE.md](../control/CLAUDE.md) - Development principles
- [UC-003 Architecture Review](core/usecases/UC-003-authentication-service/UC-003-ARCHITECTURE-REVIEW.md) - Auth adapter implementation

---

*"Abstraction is not about hiding complexity. It's about controlling where complexity lives."*
