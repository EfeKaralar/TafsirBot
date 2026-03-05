# CLAUDE.md — TafsirBot

## Project Purpose

TafsirBot is an AI-powered Quranic commentary assistant built on a RAG pipeline over classical and modern Tafsir texts, orchestrated through n8n, and delivered via Telegram, web chat, WhatsApp, and X.

## Key Architecture Decisions (Locked In)

- **Vector DB:** Qdrant (self-hosted via Docker Compose) — single `tafsir` collection initially, metadata-filtered retrieval
- **Orchestration:** n8n (self-hosted) — one canonical RAG sub-workflow, called by channel-specific workflows
- **Ingestion:** Python scripts under `scripts/ingestion/` — offline pipeline, not on the live query path
- **Quran data:** `sources/quran-json/` submodule provides Quran text and chapter metadata in JSON
- **Chunking:** Ayah-scoped (not fixed token windows); each chunk maps to a citable scripture reference
- **Embedding:** `text-embedding-3-large` (OpenAI) for English-first corpus; switch to `intfloat/multilingual-e5-large` only if Arabic ingestion is needed — never mix models in the same collection
- **LLM:** Claude Sonnet (primary) or GPT-4o; temperature 0.3, max 800 tokens (500 for X)
- **Infrastructure:** Docker Compose on a single VPS (Hetzner CX31 / DO 4GB minimum)

## Tafsir Corpus Priorities

**Primary (Phase 1):**
- Ibn Kathir — English (Dar-us-Salam translation); strip isnad chains before embedding
- Maududi (Tafhim al-Quran) — English; surah introductions are a separate chunk type

**Secondary (Phase 2+):**
- Al-Qurtubi — Arabic; tag chunks with fiqh topics
- Al-Tabari — Arabic; preserve opinion markers per verse

**Supporting (Phase 3+):**
- Jalalayn — English (Feras Hamza); small per-phrase chunks
- Ibn Ashur — Arabic; large chunks to preserve argumentative flow

See `docs/TAFSIR-CHOICES.md` and `docs/TAFSIR-CORPUS.mdx` for full per-tafsir RAG specifications.

## Chunk Metadata Schema

Every chunk must carry:

| Field | Type | Notes |
|---|---|---|
| `surah_number` | int (1–114) | Required |
| `ayah_start` | int | Required |
| `ayah_end` | int | Same as start for single-ayah chunks |
| `scholar` | str | e.g. `ibn_kathir`, `maududi` |
| `language` | str | ISO 639-1: `en`, `ar` |
| `source_title` | str | Full tafsir title |
| `english_text` | str | English translation of the covered ayah(s) |
| `arabic_text` | str | Arabic text of the covered ayah(s) |
| `chunk_type` | str | `verse`, `intro` (Maududi surah intros), `legal` (Qurtubi) |

## Guardrails (Non-Negotiable)

- Every response includes the standard disclaimer (not removable)
- `fiqh_ruling` intent → refuse and redirect to a qualified scholar
- `off_topic` intent → polite refusal
- Low-confidence responses on X → hold for human review, never auto-publish
- Every published response must cite at least one source

## Coding Style

### Python (ingestion scripts)
- Python 3.11+; use `uv` for dependency management if available, else `pip`
- Type hints on all function signatures
- `snake_case` for variables and functions, `PascalCase` for classes
- Structured logging with the standard `logging` module
- No secrets in code; read from environment variables or `.env` (never commit `.env`)
- Raise specific exceptions; never bare `except: pass`

### JavaScript (quran-json submodule)
- CommonJS (`require`), async/await, 2-space indent, semicolons, single quotes
- Match existing style exactly; see `sources/quran-json/scripts/`

## Key File Paths

- `docs/TAFSIR-CHOICES.md` — per-tafsir analysis and RAG considerations
- `docs/TAFSIR-CORPUS.mdx` — interactive corpus dashboard (React component)
- `sources/README.md` — full system architecture, environment variables, TODO list
- `sources/quran-json/dist/quran_en.json` — full English Quran (used by ingestion for `english_text` field)
- `sources/quran-json/dist/quran.json` — full Arabic Quran (used for `arabic_text` field)
- `scripts/ingestion/` — ingestion pipeline (to be created in Phase 1)
- `docker-compose.yml` — infrastructure (to be created in Phase 1)
- `.env.example` — environment variable template (to be created in Phase 1)

## Development Phases

- **Phase 1:** Ingestion pipeline + Qdrant + core n8n RAG workflow + Telegram channel
- **Phase 2:** Refinement, intent classifier tuning, conversation history, external testers
- **Phase 3:** Web chat, X auto-reply, WhatsApp
- **Phase 4:** Corpus expansion, per-scholar collections, Arabic support, analytics

## What to Avoid

- Do not mix embedding models in the same Qdrant collection
- Do not commit `.env` files or API keys
- Do not generate fatwa-style responses; always route `fiqh_ruling` intent to refusal
- Do not auto-publish low-confidence responses on X
- Do not use fixed token-window chunking — always chunk by ayah boundaries
- Do not use `git submodule` commands destructively on `sources/quran-json/`
