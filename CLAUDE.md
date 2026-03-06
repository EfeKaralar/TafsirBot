# CLAUDE.md — TafsirBot

## Project Purpose

TafsirBot is an AI-powered Quranic commentary assistant built on a RAG pipeline over classical and modern Tafsir texts, orchestrated through n8n, and delivered via Telegram, web chat, WhatsApp, and X.

## Key Architecture Decisions (Locked In)

- **Vector DB:** Qdrant (self-hosted via Docker Compose) — single `tafsir` collection with named dense+sparse vector fields; hybrid RRF retrieval
- **Retrieval:** Hybrid BM42+dense via Qdrant server-side RRF fusion (`prefetch` dense + sparse → `FusionQuery(RRF)`); scores are rank-based (not cosine)
- **Orchestration:** n8n (self-hosted) — one canonical RAG sub-workflow, called by channel-specific workflows
- **Ingestion:** Python scripts under `scripts/ingestion/` — offline pipeline, not on the live query path
- **Quran data:** `sources/quran-json/` submodule provides Quran text and chapter metadata in JSON
- **Chunking:** Ayah-scoped (not fixed token windows); each chunk maps to a citable scripture reference
- **Dense embedding:** `text-embedding-3-large` (OpenAI, 3072 dims) for English-first corpus; switch to `intfloat/multilingual-e5-large` only if Arabic ingestion is needed — never mix dense models in the same collection
- **Sparse embedding:** `Qdrant/bm42-all-minilm-l6-v2-attentions` via `fastembed` — handles exact-term queries (verse refs, transliterated Arabic, scholar names)
- **Python version:** Pinned to 3.12 (`.python-version`); `onnxruntime` (fastembed dependency) is incompatible with Python 3.14
- **LLM:** Claude Sonnet (primary) or GPT-4o; temperature 0.3, max 800 tokens (500 for X)
- **Infrastructure:** Docker Compose on a single VPS (Hetzner CX31 / DO 4GB minimum)

## Tafsir Corpus Priorities

**Primary (Phase 1):**
- Ibn Kathir — English (Dar-us-Salam, 10-vol. abridged translation); strip isnad chains before embedding. Note: the English is an abridgment — chains are often compressed or absent. He is **Shafi'i in fiqh** and Athari-leaning in theology (shaped by Ibn Taymiyya); do not describe him as Hanbali. He actively criticises Isra'iliyyat; his weakness is occasional acceptance of *hadith da'if* outside that category.
- Maududi (Tafhim al-Quran) — English (*Towards Understanding the Quran*, The Islamic Foundation); surah introductions are a separate chunk type. Translation is from Urdu, adding one layer of interpretive distance from the Arabic.

**Secondary (Phase 2+):**
- Al-Qurtubi — Arabic; tag chunks with fiqh topics
- Al-Tabari — Arabic; preserve opinion markers per verse

**Supporting (Phase 3+):**
- Jalalayn — English (Feras Hamza translation); small per-phrase chunks. Authors are Jalal al-Din al-Mahalli (teacher, initiated) and Jalal al-Din al-Suyuti (student, completed) — teacher-student, not father-son.
- Ibn Ashur — Arabic; large chunks to preserve argumentative flow. Maliki in fiqh.

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
- `fiqh_ruling` intent → retrieve and generate a response with scholarly perspectives; prepend a note that this is not a personal fatwa and the user should consult a qualified scholar
- `off_topic` intent → polite refusal (only intent that short-circuits retrieval)
- Low-confidence responses on X → hold for human review, never auto-publish
- Every published response must cite at least one source

## Coding Style

### Python (ingestion scripts)
- Python 3.11+; use `uv` for all dependency management (`uv sync`, `uv run`)
- Never use `pip install` directly; declare all deps in `pyproject.toml`
- Type hints on all function signatures
- `snake_case` for variables and functions, `PascalCase` for classes
- Structured logging with the standard `logging` module
- No secrets in code; read from environment variables or `.env` (never commit `.env`)
- Raise specific exceptions; never bare `except: pass`

### JavaScript (quran-json submodule)
- CommonJS (`require`), async/await, 2-space indent, semicolons, single quotes
- Match existing style exactly; see `sources/quran-json/scripts/`

## Key File Paths

- `docs/TAFSIR-CHOICES.md` — per-tafsir analysis and RAG considerations (fact-checked)
- `docs/TAFSIR-CORPUS.mdx` — interactive corpus dashboard (React component)
- `docs/PHASE-1-PLAN.md` — detailed Phase 1 implementation plan
- `sources/README.md` — full system architecture, environment variables, TODO list
- `sources/quran-json/dist/quran_en.json` — full English Quran (used by ingestion for `english_text` field)
- `sources/quran-json/dist/quran.json` — full Arabic Quran (used for `arabic_text` field)
- `scripts/ingestion/` — ingestion pipeline (to be created in Phase 1)
- `docker-compose.yml` — infrastructure (to be created in Phase 1)
- `.env.example` — environment variable template (to be created in Phase 1)

## Development Phases

- **Phase 1:** Corpus acquisition + ingestion pipeline (clean/chunk/embed/upsert) + Qdrant (local Docker) + Python POC RAG script. No n8n yet.
- **Phase 2:** Port to n8n; Telegram channel; conversation history; intent classifier tuning; external testers
- **Phase 3:** Web chat, X auto-reply, WhatsApp
- **Phase 4:** Corpus expansion (Al-Qurtubi, Al-Tabari, Jalalayn, Ibn Ashur), Arabic support, analytics

## What to Avoid

- Do not mix embedding models in the same Qdrant collection
- Do not commit `.env` files or API keys
- Do not generate personal fatwa/ruling responses; `fiqh_ruling` queries get scholarly context with a disclaimer, not a direct ruling
- Do not auto-publish low-confidence responses on X
- Do not use fixed token-window chunking — always chunk by ayah boundaries
- Do not use `git submodule` commands destructively on `sources/quran-json/`
