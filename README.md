# HUMANA Platform — Backend

Full Python/FastAPI backend for the HUMANA multi-tenant AI avatar admin panel.

---

## Architecture

```
Browser (Admin UI)
    │
    │  REST (CRUD)         WebSocket (live avatar)
    ▼                           ▼
┌──────────────────────────────────────────────────┐
│                  FastAPI App                      │
│                                                   │
│  /customers  ──► Customer CRUD Router             │
│  /api/health ──► Health & Stats Router            │
│  /api/business/{id}/knowledge ──► KB Router       │
│  /ws/avatar/{id} ──► WebSocket Router             │
│                           │                       │
│                    AvatarPipeline                 │
│                           │                       │
│    ┌──────────────────────┼────────────────────┐  │
│    │ Stage 1  RAG         │ ChromaDB            │  │
│    │ Stage 2  LLM         │ OpenAI / Anthropic  │  │
│    │ Stage 3  Emotion     │ (keyword heuristic) │  │
│    │ Stage 4  TTS         │ ElevenLabs          │  │
│    │ Stage 5  Viseme      │ (phoneme mapper)    │  │
│    └──────────────────────┘                     │  │
└──────────────────────────────────────────────────┘
         │               │              │
      SQLite           Chroma         Redis
     /Postgres         (vectors)    (sessions)
```

---

## Quick Start (SQLite dev mode — no Docker needed)

```bash
# 1. Clone / navigate
cd humana

# 2. Create virtualenv
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY or ANTHROPIC_API_KEY

# 5. Run the server
python -m uvicorn app.main:app --reload --port 8000

# 6. Open the admin UI
# Open index.html in browser (or serve via Live Server at port 5500)
# Docs: http://localhost:8000/docs
```

---

## Docker Compose (Postgres + Chroma + Redis)

```bash
cp .env.example .env          # fill in API keys
docker compose up --build -d
# API at http://localhost:8000
# Chroma at http://localhost:8001
```

---

## REST API Reference

### Customers

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/customers` | List all tenants |
| `POST` | `/customers/` | Create new tenant |
| `GET` | `/customers/{id}` | Get single tenant |
| `PUT` | `/customers/{id}` | Update tenant |
| `DELETE` | `/customers/{id}` | Hard delete |
| `POST` | `/customers/{id}/toggle` | Activate / pause |

### Knowledge Base

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/business/{id}/knowledge/text` | Ingest pasted text |
| `POST` | `/api/business/{id}/knowledge/file` | Upload PDF/TXT/DOCX/MD |
| `DELETE` | `/api/business/{id}/knowledge` | Wipe entire KB |
| `GET` | `/api/business/{id}/knowledge/stats` | Doc list + chunk count |

### Health & Analytics

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Full system health check |
| `GET` | `/api/stats` | Live session count, LLM config |
| `GET` | `/api/analytics?period=7d` | Per-customer analytics |

### WebSocket

```
ws://localhost:8000/ws/avatar/{business_id}
```

**Client → Server:**
```json
{ "type": "message", "text": "What are your opening hours?", "session_id": "uuid" }
{ "type": "ping" }
```

**Server → Client:**
```json
// On connect:
{ "type": "connected", "session_id": "uuid", "avatar_name": "Aria",
  "primary_color": "#f59e0b", "welcome_message": "Hi! How can I help?" }

// On response:
{
  "type": "response",
  "text": "We're open Monday to Friday, 9am to 6pm.",
  "audio_base64": "//uQxAAA...",
  "visemes": [{"t": 0.0, "v": "WW"}, {"t": 0.065, "v": "EH"}, ...],
  "emotion": "happy",
  "pipeline": [
    {"name": "RAG",    "latency_ms": 18.4,  "status": "ok"},
    {"name": "LLM",    "latency_ms": 892.1, "status": "ok"},
    {"name": "Emotion","latency_ms": 0.3,   "status": "ok"},
    {"name": "TTS",    "latency_ms": 423.7, "status": "ok"},
    {"name": "Viseme", "latency_ms": 1.2,   "status": "ok"}
  ],
  "latency_ms": 1336.2,
  "tokens_in": 284,
  "tokens_out": 62
}
```

---

## Pipeline Stages Detail

### Stage 1 — RAG (Retrieval-Augmented Generation)
- Embeds user query via `sentence-transformers/all-MiniLM-L6-v2` (local, no API cost)
- Queries per-tenant ChromaDB collection with cosine similarity
- Passes top-K chunks as context to LLM
- Warn threshold: >300ms

### Stage 2 — LLM Generation
- Supports OpenAI (`gpt-4o`, `gpt-4o-mini`) and Anthropic (`claude-sonnet-4-5`)
- Per-tenant model override via `llm_provider` + `llm_model` fields
- Maintains rolling 20-turn history per session (in-memory; Redis in prod)
- Warn threshold: >2000ms

### Stage 3 — Emotion Classification
- Lightweight keyword heuristic — zero latency, no API calls
- Labels: `happy`, `sad`, `excited`, `concerned`, `thinking`, `neutral`
- Used by avatar renderer to select facial expression / animation state

### Stage 4 — TTS (ElevenLabs)
- Synthesises audio if `ELEVENLABS_API_KEY` is configured, skipped otherwise
- Returns MP3 bytes as base64 for browser `<audio>` playback
- Warn threshold: >1500ms

### Stage 5 — Viseme (Lip-Sync)
- Maps each phoneme to a MPEG-4 viseme code at ~15fps
- Pure Python, deterministic, ~1ms latency
- Output: `[{"t": 0.0, "v": "WW"}, ...]` timestamp+viseme pairs

---

## Project Structure

```
humana/
├── app/
│   ├── main.py                  # FastAPI app factory + lifespan
│   ├── api/
│   │   ├── customers.py         # Customer CRUD
│   │   ├── knowledge.py         # KB ingestion / wipe
│   │   ├── health.py            # Health, stats, analytics
│   │   └── websocket.py         # WS avatar endpoint
│   ├── core/
│   │   ├── config.py            # Pydantic settings
│   │   ├── database.py          # Async SQLAlchemy engine
│   │   └── logging.py           # Structlog setup
│   ├── models/
│   │   ├── customer.py          # ORM models
│   │   └── schemas.py           # Pydantic request/response schemas
│   ├── pipeline/
│   │   └── avatar_pipeline.py   # 5-stage pipeline orchestrator
│   └── services/
│       ├── vector_store.py      # ChromaDB wrapper
│       ├── chunker.py           # Text splitter + file parsers
│       └── session_manager.py   # WebSocket session registry
├── alembic/                     # DB migrations
├── tests/
│   ├── test_customers.py
│   └── test_pipeline.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── alembic.ini
└── .env.example
```

---

## Running Tests

```bash
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./humana.db` | DB connection string |
| `LLM_PROVIDER` | `openai` | `openai` or `anthropic` |
| `LLM_MODEL` | `gpt-4o` | Model name |
| `OPENAI_API_KEY` | — | Required for OpenAI |
| `ANTHROPIC_API_KEY` | — | Required for Anthropic |
| `ELEVENLABS_API_KEY` | — | Optional TTS |
| `ELEVENLABS_VOICE_ID` | Rachel | ElevenLabs voice |
| `CHROMA_PATH` | `./chroma_data` | Local vector store path |
| `CHROMA_HOST` | — | Remote Chroma server |
| `CHUNK_SIZE` | `512` | KB chunk character size |
| `CHUNK_OVERLAP` | `64` | Chunk overlap chars |
| `TOP_K_RETRIEVAL` | `5` | RAG top-K results |
| `SIMILARITY_THRESHOLD` | `0.35` | Min cosine similarity |

---

## Production Checklist

- [ ] Set `APP_ENV=production` and a strong `SECRET_KEY`
- [ ] Switch `DATABASE_URL` to Postgres
- [ ] Set `CHROMA_HOST` to a persistent Chroma instance
- [ ] Set `REDIS_URL` for cross-worker session sharing
- [ ] Configure `ALLOWED_ORIGINS` to your actual domain(s)
- [ ] Set `ELEVENLABS_API_KEY` for TTS
- [ ] Add API key authentication middleware for `/customers` routes
- [ ] Set up Alembic for schema migrations: `alembic upgrade head`
- [ ] Use `--workers 4` with Gunicorn/uvicorn in production
