# TafsirBot

An AI-powered Islamic scholarly assistant that retrieves and synthesizes source-cited scholarly context across Tafsir and adjacent Islamic questions using a RAG (Retrieval-Augmented Generation) pipeline.

Delivered via a web chat interface, with Telegram, WhatsApp, and X planned for later phases.

## What It Does

A user asks a question about a Quranic verse or an Islamic topic — e.g. "What does 2:255 (Ayat al-Kursi) mean?", "What do scholars say about tawakkul?", or "Can I pray with nail polish?" — and TafsirBot retrieves relevant scholarly passages, synthesizes a cited response, and returns it with source attribution and a scholarly disclaimer.

It does not issue personal fatwas or religious rulings. It presents scholarly context with citations.

## Tafsir Corpus

**Phase 1 (current):**
- Ibn Kathir — *Tafsir al-Quran al-Azim* (14th c.) — hadith-grounded, widely trusted
- Maududi — *Tafhim al-Quran* (20th c.) — accessible modern contextual commentary

Later phases add Al-Tabari, Al-Qurtubi, Al-Jalalayn, and Ibn Ashur.

See [docs/TAFSIR-CHOICES.md](docs/TAFSIR-CHOICES.md) for per-tafsir analysis and RAG pipeline considerations.

## Architecture

**Ingestion (offline)**
```
Raw tafsir text → clean.py → chunk.py → embed.py → upsert.py → Qdrant
```

**Query path (current — Python POC)**
```
User message → FastAPI webhook (scripts/api.py)
  1. Input normalization
  2. Intent classification (tafsir / general_islamic / fiqh_ruling / off_topic)
  3. Ayah reference resolution
  4. Hybrid vector retrieval from Qdrant (BM42 + dense, RRF fusion)
  5. Prompt assembly
  6. LLM generation (Claude Sonnet or GPT-4o)
  7. Post-processing + citation formatting
→ Response delivered via web chat (web/) or direct API call
```

Infrastructure: Docker Compose (Qdrant + Postgres). n8n orchestration is planned for Phase 2.

## Getting Started

**Prerequisites:** Docker, Docker Compose, Python 3.12, Node.js 18+, uv

**1. Clone with submodules:**
```bash
git clone --recurse-submodules <repo-url>
cd TafsirBot
```

**2. Install Python dependencies:**
```bash
uv sync
```

**3. Build Quran JSON data:**
```bash
cd sources/quran-json && npm install && npm run build && cd ../..
```

**4. Copy and fill environment variables:**
```bash
cp .env.example .env
# Edit .env with your API keys
```

**5. Start infrastructure:**
```bash
docker compose up -d
```

**6. Apply database migrations:**
```bash
uv run python scripts/persistence/migrate.py
```

**7. Run ingestion pipeline** (after sourcing tafsir texts — see [docs/CORPUS-SOURCES.md](docs/CORPUS-SOURCES.md)):
```bash
uv run python scripts/ingestion/clean.py --scholar ibn_kathir
uv run python scripts/ingestion/chunk.py --scholar ibn_kathir
uv run python scripts/ingestion/embed.py --scholar ibn_kathir
uv run python scripts/ingestion/upsert.py --scholar ibn_kathir
```

**8. Start the API and web frontend** in separate terminals:
```bash
uv run uvicorn scripts.api:app --host 0.0.0.0 --port 8000
cd web && npm install && npm run dev
```
Open the Vite URL shown in the terminal. Set `VITE_API_BASE_URL` if the API is not running on `http://127.0.0.1:8000`.

Full architecture documentation: [sources/README.md](sources/README.md)
Agent/coding guidelines: [AGENTS.md](AGENTS.md), [CLAUDE.md](CLAUDE.md)

## Guardrails

- Every response includes a disclaimer: responses are AI-assisted summaries, not fatwas.
- Fiqh / ruling questions are answered with scholarly context and an explicit note that the response is not a personal fatwa.
- Off-topic queries are politely declined.
- Low-confidence responses are held for human review before publication on X.
- All published responses cite at least one Tafsir source.

## Project Status

Phase 1 complete. Phase 2 (n8n orchestration, Telegram, fiqh corpus expansion) in planning.
See [sources/README.md](sources/README.md) for the full TODO list.
