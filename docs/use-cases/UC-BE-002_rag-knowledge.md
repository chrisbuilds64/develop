# UC-BE-002: RAG Knowledge Base (Internal)

**Created:** 2026-01-22
**Revised:** 2026-01-25 (CRISP review with external AI trainer)
**Last Updated:** 2026-04-15 (status check doc audit, no content change)
**Type:** Backend
**Status:** IN PROGRESS (resource allocation waiting on GDPR + briefing agent)
**Phase:** 1 → 2 (Business Understanding complete)
**Owner:** Christian
**Provenance:** Migrated from the private control repo and translated to English, 2026-07-19. Prior revision history remains in the control repo. References to private repositories are generalized as "(internal)".

---

## Meta

**Provides:**
- `POST /api/v1/rag/query` - ask the knowledge base a question
- `POST /api/v1/rag/ingest` - index new documents
- `GET /api/v1/rag/status` - query index status

**Related use cases:**
- UC-BE-002b (chatbot, customer facing) - BLOCKED by this UC
- UC-FE-002 (search UI in tweight) - BLOCKED by this UC

---

## 1. Business Understanding ✓

### Problem Statement

Chris has written two books ("One Life, No Limits", "Do Less, Be More") plus further content (courses, session logs, articles). During content creation he must:
- Be able to reference his own sources
- Ensure consistency between new and existing content
- Retrieve knowledge from his materials quickly

**Without RAG:** manual searching through PDFs/docs, possible inconsistencies, lost time.

### User Story

```
As a CONTENT CREATOR (Chris + Claude Code)
I want to query my own books/courses/docs via AI
so that I create CONSISTENT content
that builds on my published materials
and contains correct source citations
```

### Stakeholders

| Stakeholder | Interest | Priority |
|-------------|----------|----------|
| Chris (creator) | Fast access to own knowledge | HIGH |
| Claude Code | Context for content creation | HIGH |
| Partner community (later) | Chatbot for customers | MEDIUM (UC-BE-002b) |

### Concrete Example Questions (Test Cases)

1. **Chapter summary:**
   "Summarize chapter 3 of 'Do Less, Be More'."

2. **Concept explanation:**
   "How did I define the saboteur in my book?"

3. **Source comparison:**
   "What is the difference between 'One Life, No Limits' and 'Do Less, Be More'? What connects them?"

4. **Reference for content:**
   "I'm writing a post about productivity - what have I already published on it?"

### Success Criteria (Measurable)

| Criterion | Measurement | Target |
|-----------|-------------|--------|
| Relevance | 10 test questions, rated manually | 8/10 correct |
| Source citation | Every answer contains a source | 100% |
| Latency | Time to answer | < 5 seconds |
| Consistency | Same question → similar answer | Yes |

### Scope

**IN SCOPE:**
- Books: "One Life, No Limits", "Do Less, Be More"
- Courses: 30-day career formula, AI tools (5 lessons)
- Session logs (internal)
- AI trainer course material (internal)
- Own articles

**OUT OF SCOPE:**
- External web content (no web search)
- Real-time data
- Audio/video transcription
- Customer-facing chatbot (→ UC-BE-002b)

---

## 2. Data Understanding (IN PROGRESS)

### Data Inventory

| Source | Location | Format | Status | Action Needed |
|--------|----------|--------|--------|---------------|
| AI trainer material | (internal) | Markdown | ✅ READY | — |
| Session logs | (internal) | Markdown | ✅ READY | — |
| Articles | (internal) | Markdown | ✅ READY | — |
| "Do Less, Be More" | (internal archive) | PDF/TXT | ⚠️ PARTIAL | Structure |
| "One Life, No Limits" | ??? | ??? | ❌ MISSING | Provide |
| 30-day career course | Course platform | ??? | ❓ UNCLEAR | Locate |
| AI tools course (5 lessons) | ??? | ??? | ❓ UNCLEAR | Locate |

### BLOCKER: Data Gap

**Status:** Phase 2 paused until data is provided

**Christian's TODO:**
- [ ] Provide books as structured text (Word/Markdown)
- [ ] Locate "One Life, No Limits"
- [ ] Export course materials from the course platform (if available)
- [ ] Target structure: internal knowledge repo (`books/`, `courses/`)

### Existing Data (Details)

**AI trainer course:** 5 Markdown files
- AI/ML overview (491 lines)
- CRISP-DM fundamentals (382 lines)
  - Session transcripts (3x)
- Session logs (internal)
- Code docs: `develop/` READMEs, requirements

**Data quality:**
- ✅ Well structured (headings, tables, lists)
- ✅ Fully converted (PDF/DOCX → MD)
- ⚠️ Transcripts are rough (Whisper output)

**Gaps:**
- Define chunking strategy
- Define metadata schema

---

## 3. Data Preparation

**Transformations:**
- [x] DOCX → Markdown (pandoc)
- [x] PDF → Markdown (structured manually)
- [ ] Chunking for embeddings (strategy: see below)
- [ ] Metadata extraction (topic, source, date)

**Chunking strategy:**
```
Options:
1. Fixed size (500 tokens) + overlap (50)
2. Semantic (by heading)
3. Hybrid (heading-aware + max size)

Recommendation: Option 3 - respects document structure
```

**Pipeline:**
```
knowledge sources (*.md)
         ↓
    [Loader: read Markdown]
         ↓
    [Chunker: heading-aware, max 500 tokens]
         ↓
    [Embedder: OpenAI or local]
         ↓
    [VectorStore: ChromaDB]
         ↓
    Persistent storage (./data/chroma/)
```

---

## 4. Modeling

### Architecture Decision

**Chosen: local-first with ChromaDB**

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Vector store | ChromaDB | Embedded, no server, persistent, Docker-ready |
| Embeddings | OpenAI `text-embedding-3-small` | Quality, 1536 dims, cheap |
| LLM | Claude API (via Anthropic) | Already available, best quality |
| Framework | LangChain or custom | TBD - possibly custom for control |

### Backend Module Structure

```
services/backend/modules/rag/
├── __init__.py
├── config.py           # Environment-based config
├── service.py          # RAGService (query, add_document)
├── embeddings/
│   ├── base.py         # EmbeddingProvider ABC
│   ├── openai.py       # OpenAI embeddings
│   └── local.py        # (later: sentence-transformers)
├── vectorstore/
│   ├── base.py         # VectorStore ABC
│   └── chroma.py       # ChromaDB implementation
├── chunking/
│   ├── base.py         # Chunker ABC
│   └── markdown.py     # Markdown-aware chunker
└── loaders/
    └── markdown.py     # Markdown loader with metadata
```

### API Endpoints

```
POST /api/v1/rag/query
  Body: { "question": "What is CRISP-DM?" }
  Response: { "answer": "...", "sources": [...] }

POST /api/v1/rag/ingest
  Body: { "path": "knowledge/" }
  Response: { "documents_processed": 5 }

GET /api/v1/rag/status
  Response: { "documents": 5, "chunks": 120 }
```

### Adapter Pattern (like Auth)

```python
# Swappable embedding provider
class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        pass

# Swappable vector store
class VectorStore(ABC):
    @abstractmethod
    def add(self, texts, embeddings, metadata): pass
    @abstractmethod
    def query(self, embedding, k=5): pass
```

---

## 5. Evaluation

**Metrics:**
- Relevance of answers (subjective, samples)
- Recall: does the system find the right source?
- Latency: < 3s per query (incl. LLM)

**Acceptance criteria:**
- [ ] Query "What is CRISP-DM?" → correct answer with source
- [ ] Query on trainer material → relevant chunks
- [ ] Add new Markdown file → indexed automatically
- [ ] Works locally AND on the production server

**Test questions:**
1. "What are the phases of CRISP-DM?"
2. "What is the difference between ML and deep learning?"
3. "What is RAG according to the course material?"

---

## 6. Deployment

### Local Development
```yaml
# docker-compose.yml (extend existing)
services:
  backend:
    environment:
      - CHROMA_PATH=./data/chroma
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./data/chroma:/app/data/chroma
      - ./knowledge:/app/knowledge:ro
```

### Production
```bash
# Same code, different config
git pull
docker compose -f docker-compose.prod.yml up -d
```

**Environment variables:**
```
CHROMA_PATH=/data/chroma
OPENAI_API_KEY=<via environment, never committed>
RAG_KNOWLEDGE_PATH=/knowledge
```

### Rollout Phases

| Phase | Goal | Done |
|-------|------|------|
| 1 | CLI tool locally | [ ] |
| 2 | API endpoint in backend | [ ] |
| 3 | Production deployment | [ ] |
| 4 | tweight integration | [ ] |

---

## Implementation Steps (CRISP)

### Phase 1: Core RAG (Local CLI)
1. [ ] ChromaDB setup + Docker integration
2. [ ] Implement Markdown loader
3. [ ] Implement chunking (heading-aware)
4. [ ] OpenAI embeddings adapter
5. [ ] Basic query function
6. [ ] CLI tool for testing

### Phase 2: API Integration
7. [ ] RAG service as backend module
8. [ ] API endpoints (query, ingest, status)
9. [ ] Auth integration (own docs only)

### Phase 3: Production
10. [ ] Production deployment
11. [ ] Persistent storage setup
12. [ ] Monitoring (query logs)

---

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-22 | Markdown as base format | Structured, AI-readable, versionable |
| 2026-01-22 | ChromaDB as vector store | Embedded, no extra server, Docker-ready |
| 2026-01-22 | OpenAI embeddings (start) | Quality, local swappable later |
| 2026-01-22 | Local-first, production-deployable | Develop locally, deploy anywhere |

---

## Status Updates

| Date | Phase | Status | Notes |
|------|-------|--------|-------|
| 2026-01-22 | Data Preparation | Done | 5 files converted |
| 2026-01-22 | Modeling | In Progress | Architecture planned |

---

## Related

- Backend module: `services/backend/modules/rag/` (to be created)
- Docker: `docker-compose.yml`
