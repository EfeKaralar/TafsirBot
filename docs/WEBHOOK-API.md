# TafsirBot Webhook API

Thin HTTP API wrapping the existing `rag_poc` RAG pipeline. Designed to be
structurally close to the intended n8n webhook model so the interface can be
adopted by channel-specific n8n workflows with no changes.

---

## Setup

```bash
# 1. Install dependencies (adds fastapi + uvicorn)
uv sync

# 2. Copy and fill in your .env
cp .env.example .env
# Required: OPENAI_API_KEY, ANTHROPIC_API_KEY (if using Anthropic provider)
# Required: Qdrant running — docker compose up -d qdrant

# 3. Start the API server
uv run uvicorn scripts.api:app --host 0.0.0.0 --port 8000

# Development (auto-reload on file changes)
uv run uvicorn scripts.api:app --host 0.0.0.0 --port 8000 --reload
```

The server initialises the sparse embedding model, Qdrant client, and LLM
clients on startup. First startup may take a few seconds if the BM42 model
cache is cold (~130 MB download).

> **Git worktree note:** If running from a worktree that does not have the
> `sources/quran-json/dist/` directory, set `QURAN_JSON_DIST` to an absolute
> path in your `.env`:
> ```
> QURAN_JSON_DIST=/absolute/path/to/TafsirBot/sources/quran-json/dist
> ```

---

## Endpoints

### `GET /health`

Liveness check. Returns available LLM providers.

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "version": "0.1.0",
  "providers": ["openai", "anthropic"],
  "persistence": true
}
```

---

### `POST /api/webhook`

Run the full RAG pipeline for a user message.

**Request body:**

```json
{
  "channel": "web",
  "session_id": "local-session-id",
  "user_id": "local-user",
  "message": "What does Ibn Kathir say about Ayat al-Kursi?",
  "conversation_history": [
    {"role": "user", "content": "Tell me about Surah Al-Baqarah."},
    {"role": "assistant", "content": "..."}
  ],
  "options": {
    "provider": "anthropic",
    "scholar": null,
    "top_k": 5,
    "save": true
  }
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `channel` | string | `"web"` | Channel identifier (informational; included in `meta`) |
| `session_id` | string | `"local-session"` | Session identifier echoed back in the response |
| `user_id` | string | `"local-user"` | User identifier (informational) |
| `message` | string | required | The raw user query |
| `conversation_history` | array | `[]` | Prior turns; last 3 pairs (6 messages) are included in the LLM call |
| `options.provider` | `"anthropic"` \| `"openai"` | `LLM_PROVIDER` env | LLM provider for intent classification and generation |
| `options.scholar` | string \| null | `null` | Restrict retrieval to a scholar slug (e.g. `"ibn_kathir"`) |
| `options.top_k` | int 1–20 | `5` | Number of chunks to retrieve |
| `options.save` | bool | `true` | Persist the user/assistant exchange to Postgres when persistence is configured |

**Response body:**

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "local-session-id",
  "intent": "tafsir",
  "normalized_message": "What does Ibn Kathir say about Ayat al-Kursi?",
  "answer": "Ibn Kathir explains that Ayat al-Kursi (2:255)...\n\n**Sources:**\n- Ibn Kathir on 2:255...\n\n---\n*This response is an AI-assisted summary...*",
  "citations": ["[Ibn Kathir on 2:255]"],
  "confidence": "high",
  "disclaimer_applied": true,
  "fiqh_note_applied": false,
  "chunks": [
    {
      "scholar": "ibn_kathir",
      "surah_number": 2,
      "ayah_start": 255,
      "ayah_end": 255,
      "source_title": "Tafsir Ibn Kathir",
      "score": 1.0,
      "content_preview": "This is the greatest verse in the Quran..."
    }
  ],
  "meta": {
    "channel": "web",
    "user_id": "local-user",
    "provider": "anthropic",
    "top_k": 5,
    "scholar_filter": null,
    "elapsed_ms": 2341
  }
}
```

**Intent behaviour:**

| Intent | Behaviour |
|---|---|
| `tafsir` | Normal retrieval + generation + disclaimer |
| `general_islamic` | Normal retrieval + generation + disclaimer |
| `fiqh_ruling` | Retrieval + generation; `fiqh_note_applied: true`; answer prefixed with fiqh note |
| `off_topic` | Polite refusal; no retrieval; `disclaimer_applied: false` |

**curl example:**

```bash
curl -s -X POST http://localhost:8000/api/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain Quran 2:255",
    "options": {"provider": "anthropic"}
  }' | python3 -m json.tool
```

`POST /query` is also available as a compatibility alias during local development.

---

### `GET /api/sessions`

List recent saved chat sessions.

### `GET /api/sessions/{session_id}`

Return one saved chat session plus its messages.

### `GET /api/test-runs`

List recent saved `test_poc` runs.

### `GET /api/test-runs/{run_id}`

Return one saved test run plus its per-case outputs.

---

## Interactive docs

FastAPI auto-generates OpenAPI docs at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Local web client

A simple React + Vite client lives in [`web/`](/Users/alp/Projects/TafsirBot/web).

```bash
cd web
npm install
npm run dev
```

By default the client calls `http://127.0.0.1:8000`. Override that with:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

The UI currently supports:

- live chat against `POST /api/webhook`
- saved session browsing via `GET /api/sessions` and `GET /api/sessions/{session_id}`
- saved test-run browsing via `GET /api/test-runs` and `GET /api/test-runs/{run_id}`
- retrieval chunk inspection for the latest live response

Current backend caveat:

- persisted local session IDs should be UUID-shaped until the string session ID fix is merged to `master`

---

## CLI (unchanged)

The `rag_poc.py` CLI continues to work exactly as before:

```bash
uv run python scripts/rag_poc.py "What does Ibn Kathir say about 2:255?"
uv run python scripts/rag_poc.py --scholar maududi "What is the theme of Surah Al-Baqarah?"
uv run python scripts/rag_poc.py --provider openai --verbose "Explain tawakkul"
```

---

## Assumptions and design notes

- **Single-user / local use:** No authentication or rate-limiting is implemented.
  Add an auth middleware before exposing to the internet.
- **Postgres persistence:** If Postgres is configured and migrations were applied,
  `options.save` persists the current user/assistant exchange. The read endpoints
  expose saved sessions and test runs for the local UI.
- **Synchronous handlers:** Pipeline steps (embedding, LLM calls, Qdrant) are
  blocking. For concurrent load, run with multiple uvicorn workers:
  `uvicorn scripts.api:app --workers 4`.
- **Conversation history:** The last 6 messages (3 turn-pairs) from
  `conversation_history` are included in the LLM generation call. Intent
  classification always uses only the current message.
- **Provider per request:** The `options.provider` field controls which LLM is
  used for both intent classification and generation. Both providers are
  initialised at startup if their API keys are present; a missing key causes a
  422 error if that provider is requested.
- **`chunks` in response:** Retrieved chunk summaries (first 200 chars) are
  included for UI rendering and debugging. Strip this field if response size
  is a concern.
