# UC-002: Personal Knowledge RAG

**Created:** December 30, 2025
**Status:** 📋 Planned (Not Started)
**Goal:** Self-hosted RAG system for personal content and books
**Principle:** Concrete implementation > Abstract AI framework
**Dependency:** UC-001 must be live via domain + SSL + TestFlight beta active

---

## 🎯 The Problem

**Current situation:**
- I've written 6 days of content (DAY-001 through DAY-006)
- Published books: "1LIVE No Limits"
- Upcoming book: "Do Less, Be More" (with Akhil)
- Growing body of knowledge scattered across files
- No way to query/search this knowledge intelligently
- Writing new posts = manual re-reading of old content
- Can't answer questions like "What did I say about breathwork?" without manual search

**What annoys me most:**
- Can't find specific insights across all my content
- Writing new posts requires manual research through old posts
- No intelligent assistant that knows my writing style and philosophy
- Knowledge locked in static markdown files
- Can't provide value to readers beyond static posts

---

## ✅ Today's Goal (Concrete, Achievable)

**Build a simple RAG system where I can:**
1. Ingest all DAY-XXX posts into a vector database
2. Ingest published books (PDFs or text)
3. Query the system: "What did I write about AI productivity?"
4. Get relevant excerpts from my content
5. Later: "Ask Chris" chatbot on website

**That's it. Nothing more.**

---

## 🚫 What I'm NOT Building Today

- ❌ Generic multi-tenant RAG platform
- ❌ Complex orchestration with LangChain/LlamaIndex
- ❌ Advanced chunking strategies (semantic, recursive, etc.)
- ❌ Multiple embedding models comparison
- ❌ Real-time collaborative knowledge base
- ❌ Full-text search + vector hybrid
- ❌ Web scraping for external sources
- ❌ Authentication system for RAG API
- ❌ Fancy UI with chat history, citations, etc.

**Why not?**
- YAGNI (You Ain't Gonna Need It - yet)
- Ship working RAG > Build enterprise platform
- Premature abstraction = Scope creep
- Today: Simple vector search. Tomorrow: Maybe advanced features (if needed)

---

## 🏗️ Architecture (Simple)

### Stack:
- **Vector Database:** Qdrant (Docker on Strato VPS)
- **Embedding Model:** all-MiniLM-L6-v2 (sentence-transformers)
- **API:** FastAPI endpoint at /api/rag/query
- **Storage:** Existing Strato VPS (8 vCores, 32GB RAM)
- **Ingestion:** Python script to chunk + embed + upload

### Why this stack?
- **Qdrant:** Open source, fast, Docker-ready, simple API
- **all-MiniLM-L6-v2:** Fast, good enough, runs locally, no API costs
- **FastAPI:** Already using it, familiar, Python
- **Self-hosted:** No OpenAI API costs, data privacy, full control

---

## 📚 Content Sources (Phase 1)

### 1. Daily Posts
- `/brand/content/posts/DAY-001-Building-Together.md`
- `/brand/content/posts/DAY-002-Full-Stack-in-One-Afternoon.md`
- `/brand/content/posts/DAY-003-When-AI-Makes-You-Think-You-Can-Do-Everything.md`
- `/brand/content/posts/DAY-004-The-Use-Case-Approach.md`
- `/brand/content/posts/DAY-005-From-Localhost-to-Production-One-Morning.md`
- `/brand/content/posts/DAY-006-The-Quiet-Door-Out-of-Overwhelm.md`
- (Future DAY-XXX posts)

### 2. Published Books
- "1LIVE No Limits" (PDF or markdown)
- "Do Less, Be More" (upcoming, with Akhil)

### 3. Strategy Documents (Optional Phase 2)
- TAGS-STRATEGY.md
- PROJECT-CONTEXT.md
- CLAUDE.md
- Use case docs (UC-001, UC-002, etc.)

---

## 🔌 API Endpoints

### 1. Query Knowledge Base
**POST /api/rag/query**

**Request:**
```json
{
    "query": "What did I write about breathwork?",
    "top_k": 5,
    "filter": {
        "source_type": "daily_post"  // Optional: filter by post type, book, etc.
    }
}
```

**Response:**
```json
{
    "query": "What did I write about breathwork?",
    "results": [
        {
            "content": "I stumbled on a YouTube video about breathwork. Tried it. 45 minutes of intense breathing. Everything changed.",
            "source": "DAY-006-The-Quiet-Door-Out-of-Overwhelm.md",
            "score": 0.87,
            "metadata": {
                "date": "2025-12-31",
                "tags": ["Building in Public", "Developer Productivity", "Burnout Prevention", "Breathwork", "Digital Nomad"]
            }
        },
        {
            "content": "45 minutes of controlled hyperventilation followed by breath holds. After 45 minutes, I was crying. Not sad. Release.",
            "source": "DAY-006-The-Quiet-Door-Out-of-Overwhelm.md",
            "score": 0.82,
            "metadata": {
                "date": "2025-12-31",
                "tags": ["Building in Public", "Developer Productivity", "Burnout Prevention", "Breathwork", "Digital Nomad"]
            }
        }
    ]
}
```

---

### 2. Ingest New Content (Admin)
**POST /api/rag/ingest**

**Request:**
```json
{
    "file_path": "/brand/content/posts/DAY-007-New-Post.md",
    "source_type": "daily_post",
    "metadata": {
        "date": "2026-01-01",
        "tags": ["Building in Public", "AI Development"]
    }
}
```

**Response:**
```json
{
    "success": true,
    "chunks_created": 12,
    "vectors_uploaded": 12,
    "message": "Content ingested successfully"
}
```

---

### 3. Health Check
**GET /api/rag/health**

**Response:**
```json
{
    "status": "healthy",
    "qdrant_connected": true,
    "collections": {
        "chrisbuilds64_knowledge": {
            "vectors_count": 247,
            "points_count": 247
        }
    }
}
```

---

## 🗄️ Qdrant Collection Schema

### Collection: `chrisbuilds64_knowledge`

**Vector Config:**
- Dimension: 384 (all-MiniLM-L6-v2 output size)
- Distance: Cosine

**Payload Schema:**
```json
{
    "content": "The actual text chunk",
    "source": "DAY-006-The-Quiet-Door-Out-of-Overwhelm.md",
    "source_type": "daily_post",  // Or "book", "strategy_doc"
    "chunk_index": 5,
    "total_chunks": 12,
    "metadata": {
        "date": "2025-12-31",
        "tags": ["Breathwork", "Developer Productivity"],
        "author": "Chris",
        "location": "Bali, Indonesia"
    }
}
```

---

## 🛠️ Implementation Steps (Order Matters)

### Phase 1: Infrastructure Setup
1. ☐ Install Qdrant on Strato VPS (Docker)
2. ☐ Create docker-compose.yml for Qdrant
3. ☐ Verify Qdrant accessible on localhost:6333
4. ☐ Create collection `chrisbuilds64_knowledge`

### Phase 2: Ingestion Pipeline
5. ☐ Create `ingest.py` script
6. ☐ Parse markdown files (DAY-XXX posts)
7. ☐ Chunk content (simple paragraph split, ~500 chars)
8. ☐ Generate embeddings with sentence-transformers
9. ☐ Upload to Qdrant with metadata
10. ☐ Test with DAY-001 through DAY-006

### Phase 3: Query API
11. ☐ Create FastAPI endpoint `/api/rag/query`
12. ☐ Embed user query with same model
13. ☐ Search Qdrant for top_k results
14. ☐ Return formatted results
15. ☐ Test with curl/Postman

### Phase 4: Integration
16. ☐ Add to existing FastAPI app (or separate service?)
17. ☐ Deploy to Strato VPS
18. ☐ Test from outside
19. ☐ Document API in DEPLOYMENT.md

### Phase 5: Content Assistant (Future)
20. ☐ Create simple chat UI (Flutter or web?)
21. ☐ "Ask Chris" chatbot
22. ☐ Use RAG results + LLM to generate answers
23. ☐ Embed on chrisbuilds64.com/dev

---

## 📝 Ingestion Strategy

### Chunking (Simple First):
- Split by paragraphs (markdown `\n\n`)
- Target: ~500 characters per chunk
- Overlap: 50 characters (to preserve context)
- Metadata: source file, chunk index, date, tags

### Why simple chunking?
- Good enough for V1
- Can improve later with semantic chunking
- KISS principle

### Example Chunks from DAY-006:
```
Chunk 1:
"Yesterday I deployed infrastructure. Docker containers, nginx configs, SSH keys. Today I want to talk about something else entirely."

Chunk 2:
"Five days of AI-assisted development. Five days of shipping features that used to take weeks. Here's what I learned: Speed without recovery is just a faster road to collapse."

Chunk 3:
"I stumbled on a YouTube video about breathwork. Tried it. 45 minutes of intense breathing. Everything changed."
```

---

## 🎯 Success Criteria (Phase 1)

**Done = I can:**
1. ☐ Ingest all DAY-001 through DAY-006 posts
2. ☐ Query: "What did I write about breathwork?" → Get DAY-006 excerpts
3. ☐ Query: "What did I write about Docker?" → Get DAY-005 excerpts
4. ☐ Query: "What did I write about KISS principle?" → Get multiple posts
5. ☐ Results include source file, score, and metadata

**Nice-to-have (if time):**
- Ingest published books
- Filter by source_type or tags
- Simple web UI for testing queries

---

## 🚀 Why This Approach Works

### Principles Applied:
1. **KISS** → Simple chunking, simple search
2. **YAGNI** → No advanced features yet
3. **Self-hosted** → No API costs, full control
4. **Use Case Driven** → Solve real problem (finding my own content)
5. **Building in Public** → RAG for transparency, not secrecy

### What I Can Do LATER (If Needed):
- Advanced chunking (semantic, recursive)
- Hybrid search (vector + full-text)
- Multiple embedding models
- Real-time ingestion (watch file changes)
- Multi-language support
- Citations with page numbers
- Chat history
- User authentication

**But not today.**

---

## 💡 Use Cases (Future)

### 1. Content Writing Assistant
"Show me what I've written about AI productivity"
→ Use RAG results to avoid repeating myself

### 2. "Ask Chris" Chatbot
User: "How does Chris approach AI-assisted development?"
→ RAG retrieves relevant chunks
→ LLM generates answer in my voice

### 3. Documentation Bot
Developer: "How do I deploy to production?"
→ RAG searches DAY-005, DEPLOYMENT.md
→ Returns step-by-step guide

### 4. Book Research
"Find all mentions of 'breathwork' across all books and posts"
→ Cross-reference content sources

---

## 📊 Estimated Costs

### Infrastructure:
- **Qdrant:** Self-hosted on existing Strato VPS (no extra cost)
- **Embedding Model:** Local (all-MiniLM-L6-v2, free)
- **Storage:** ~1-2GB for vectors (DAY-XXX + books)
- **LLM API (optional, later):** Claude API for chatbot (~$0.01 per query)

### Total: ~€0/month for RAG itself
(Strato VPS already paid: €40/month)

---

## 🔒 Security & Privacy

### Data Privacy:
- All content self-hosted (no third-party vector DB)
- No data sent to OpenAI/Anthropic for embeddings
- Query API initially public (no auth)
- Future: Add API key for public chatbot

### Access Control (Future):
- Public: "Ask Chris" chatbot (filtered content)
- Private: Full RAG access for content writing

---

## 📝 Content Opportunities

### Substack Post (When Shipped):
**Title:** "I Built a RAG System for My Own Content (No OpenAI Required)"

**Key Points:**
- Why I needed it (content chaos)
- Self-hosted approach (Qdrant + sentence-transformers)
- No API costs
- KISS in action
- "Ask Chris" chatbot coming soon

### Future Posts:
- "How to Build RAG Without LangChain"
- "Self-Hosted AI: Qdrant + Sentence Transformers"
- "Turning Content into Conversations: RAG for Indie Hackers"

---

## 🎬 Instagram Reel Idea (Later)

**Concept:** "I can now search everything I've ever written"

**Script:**
- 0-3s: "I've written 6 days of content..."
- 3-6s: "...but can't remember what I said about breathwork"
- 6-9s: "So I built a RAG system"
- 9-12s: Show query → instant results
- 12-15s: "Self-hosted. No OpenAI. Building in public from Bali."

**Hook:** Relatable problem (content chaos), technical solution (RAG), indie hacker vibe

---

**Status:** Planned (Not Started)
**Dependency:** UC-001 live via domain + SSL + TestFlight beta active
**Next Step:** Wait for DNS/SSL, then create detailed implementation plan
**Expected Start:** After UC-001 fully deployed (January 2026)

---

*Building in public. Solving real problems. Shipping when ready.* 🚀
