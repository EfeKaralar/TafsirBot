# AI Islamic Scholarly Assistant (TafsirBot)

An AI-powered Islamic scholarly assistant built on a Retrieval-Augmented Generation (RAG) pipeline, orchestrated with LangGraph, and delivered across multiple channels including a web chat interface, Telegram, WhatsApp, and X (Twitter).

The corpus covers Quranic commentary (Tafsir), Islamic jurisprudence (fiqh), and scholarly legal opinions (fatawa). The bot presents what scholars say on any Islamic topic — including jurisprudential questions — with a clear disclaimer that responses are not personal rulings. Only queries entirely unrelated to Islam are declined.

---

## Table of Contents

- [Project Goals](#project-goals)
- [System Architecture](#system-architecture)
  - [Overview](#overview)
  - [1. Corpus Ingestion Layer](#1-corpus-ingestion-layer)
  - [2. Vector Storage](#2-vector-storage)
  - [3. RAG Core — LangGraph Orchestration](#3-rag-core--langgraph-orchestration)
  - [4. Channel Delivery Layer](#4-channel-delivery-layer)
  - [5. Infrastructure & Deployment](#5-infrastructure--deployment)
- [Guardrails & Scholarly Integrity](#guardrails--scholarly-integrity)
- [Tafsir Corpus Selection](#tafsir-corpus-selection)
- [Environment Variables](#environment-variables)
- [TODO](#todo)

---

## Project Goals

- Provide accurate, source-cited Islamic scholarly commentary by surfacing responses from established Tafsir works, fiqh manuals, and fatawa databases.
- Present multiple scholarly positions on jurisprudential questions (all four Sunni madhabs weighted equally) — clearly distinguished from issuing personal rulings.
- Support multi-channel interaction: web chat, Telegram, WhatsApp, and X auto-reply.
- Maintain scholarly integrity through transparent sourcing, clear disclaimers, and explicit acknowledgment of scholarly disagreement.
- Keep the system self-hosted and auditable, with no user query data sent to third parties beyond the LLM API.

---

## System Architecture

### Overview

The system is divided into four layers: ingestion, storage, RAG orchestration, and delivery. All query processing flows through a single compiled LangGraph `StateGraph` regardless of which channel initiated the request. Channel adapters handle platform normalization and then call one FastAPI surface; they contain no pipeline logic.

> **Architecture contract:** `docs/LANGGRAPH-ARCHITECTURE.md` is authoritative for graph topology,
> state schema, version pins, and the SSE event vocabulary. The summary below is orientation only.
> n8n was evaluated and dropped on 2026-09-08 — see epic #38.

```
+--------------------------------------------------------------+
|                      INGESTION LAYER                         |
|  Tafsir source texts                                         |
|    --> Cleaning & normalization                              |
|    --> Ayah-scoped chunking                                  |
|    --> Metadata tagging (scholar, surah, ayah, language)     |
|    --> Embedding model                                       |
|    --> Vector DB upsert                                      |
+--------------------------------------------------------------+
                             |
                             v
+--------------------------------------------------------------+
|                  VECTOR STORAGE (Qdrant)                     |
|  Collections per language / per scholar (or combined)        |
|  Metadata filters: surah_number, ayah_start, ayah_end,       |
|  scholar, language                                           |
+--------------------------------------------------------------+
                             |
                             v
+--------------------------------------------------------------+
|              RAG CORE (LangGraph StateGraph)                 |
|  normalize -> classify -> plan_query -> plan_retrieval       |
|      -> retrieve (parallel fan-out) -> fuse -> grade         |
|      -> generate -> verify -> finalize -> persist            |
|                                                              |
|  Loops: grade -> broaden -> retrieve  (adaptive retrieval)   |
|         verify -> generate            (citation retry)       |
|  Held:  finalize -> human_review      (interrupt)            |
+--------------------------------------------------------------+
                             |
                             v
+--------------------------------------------------------------+
|                   FastAPI (one surface)                      |
|  POST /query  |  POST /api/webhook  |  POST /api/query/stream |
+--------------------------------------------------------------+
                             |
          +------------------+------------------+
          |                  |                  |
          v                  v                  v
  +---------------+  +---------------+  +---------------+
  |  Web / Tele-  |  |  X (Twitter)  |  |  WhatsApp     |
  |  gram Chat    |  |  Auto-reply   |  |  (Meta Cloud  |
  |               |  |  (polling)    |  |   API)        |
  +---------------+  +---------------+  +---------------+
```

---

### 1. Corpus Ingestion Layer

The ingestion layer is a set of Python scripts run offline to build and maintain the vector database. This is not part of the live query path.

**Chunking strategy:** Chunk boundaries depend on corpus type:

- **Tafsir:** Scoped to individual Ayahs or contiguous Ayah ranges — never fixed token windows. Ensures retrieval results map cleanly to citable scripture references.
- **Fiqh:** Scoped to individual legal questions (*masa'il*) or topic-level sections.
- **Fatawa:** One fatwa per chunk (question + ruling + reasoning).

Each chunk carries the following metadata:

| Field | Description |
|---|---|
| `surah_number` | Integer (1–114); null for fiqh/fatwa chunks not tied to a specific verse |
| `ayah_start` | First Ayah in chunk; null for non-verse chunks |
| `ayah_end` | Last Ayah in chunk; null for non-verse chunks |
| `scholar` | Identifier string, e.g. `ibn_kathir`, `maududi`, `nuh_keller` |
| `language` | ISO 639-1 code: `en`, `ar` |
| `source_title` | Full title of the source work |
| `corpus_type` | `tafsir`, `fiqh`, `fatwa`, or `hadith` |
| `madhab` | `hanafi`, `maliki`, `shafii`, `hanbali`, `multi`, or `unspecified` |
| `english_text` | English translation of the Ayah(s) covered (Tafsir chunks only) |
| `arabic_text` | Arabic text of the Ayah(s) covered (Tafsir chunks only) |

**Ingestion pipeline scripts:**

```
scripts/ingestion/
  clean.py       -- Remove OCR artifacts, headers, footers, diacritical normalization
  chunk.py       -- Split source text into Ayah-scoped chunks with metadata
  embed.py       -- Generate embeddings via the configured embedding model
  upsert.py      -- Push chunks into Qdrant
  audit.py       -- Spot-check retrieval quality for a set of test queries
```

**Local persistence scripts:**

```
scripts/persistence/
  migrate.py     -- Apply SQL migrations to the local Postgres database
  postgres.py    -- Minimal repository layer for sessions, messages, and test runs
```

**Embedding models:**
- **Dense:** `text-embedding-3-large` (OpenAI, 3072 dims, cosine) — English-first corpus default.
- **Sparse:** `Qdrant/bm42-all-minilm-l6-v2-attentions` via `fastembed` — BM42 sparse vectors for exact-term retrieval (verse refs, transliterated Arabic, scholar names). Downloaded ~130 MB on first run, cached in `~/.cache/fastembed/`.

**Never mix dense embedding models in the same Qdrant collection.** Vectors from different models are not comparable, making cross-vector retrieval meaningless. Arabic sources require a separate collection (see Vector Storage below).

For the full corpus selection discussion — Tafsir, fiqh, and fatawa — see [docs/TAFSIR-CHOICES.md](docs/TAFSIR-CHOICES.md) and [docs/RESEARCH-AGENT-BRIEF.md](docs/RESEARCH-AGENT-BRIEF.md).

---

### 2. Vector Storage

**Database:** Qdrant, self-hosted via Docker.

Qdrant is chosen for its native metadata filtering, server-side RRF fusion of dense and sparse prefetch branches, and low operational overhead compared to Weaviate. All retrieval requests apply a metadata pre-filter on `surah_number` and `ayah_start`/`ayah_end` when the query contains a specific Ayah reference, significantly narrowing the candidate set before semantic ranking.

**Collection architecture:**

| Phase | Collection | Embedding model | Corpus |
|---|---|---|---|
| 1–2 (now) | `tafsir` | `text-embedding-3-large` + BM42 | All English sources: Tafsir, fiqh, fatawa |
| 3+ (Arabic) | `tafsir_ar` | `intfloat/multilingual-e5-large` + Arabic sparse model | Arabic-primary sources |

A **single collection** is used for all English content regardless of corpus type (Tafsir, fiqh, fatawa, hadith). This enables natural cross-corpus retrieval: a question about a verse's legal implication can surface both a Tafsir chunk and a fiqh ruling in one query. The `corpus_type` and `madhab` metadata fields allow filtering when needed.

When Arabic sources are added (Phase 3+), a **separate collection** (`tafsir_ar`) is required — not optional — because mixing dense embeddings from different models in one collection makes retrieval meaningless. A language-routing layer in the query pipeline will fan out to both collections and merge results.

The `tafsir` collection uses **named vector fields**:

| Field | Type | Config |
|---|---|---|
| `dense` | `VectorParams` | size=3072, distance=Cosine |
| `sparse` | `SparseVectorParams` | BM42, on-disk=False |

To rebuild the collection with a new schema, run `upsert.py --recreate`.

**Retrieval parameters:**

- Top-K: 5 chunks per query (each prefetch branch fetches top_k × 4 candidates)
- Retrieval mode: **Hybrid** — dense cosine prefetch + BM42 sparse prefetch, fused via server-side **Reciprocal Rank Fusion (RRF)**
- Scores returned are RRF rank-based (not cosine similarity); rank-1 from both branches yields score 1.0
- Metadata filter applied inside each prefetch block when an Ayah reference is detected

---

### 3. RAG Core — LangGraph Orchestration

This is the compiled `StateGraph`. It is channel-agnostic: every channel adapter calls the same FastAPI endpoint with a normalized input object and receives a normalized response object.

Full topology, state schema, and reducer rules live in `docs/LANGGRAPH-ARCHITECTURE.md`.

**Input schema:**

```json
{
  "raw_query": "string",
  "channel": "telegram | web | x | whatsapp",
  "conversation_history": [ { "role": "user|assistant", "content": "string" } ],
  "user_id": "string"
}
```

**Output schema:**

```json
{
  "response_text": "string",
  "citations": [ { "scholar": "string", "surah": "int", "ayah_start": "int", "ayah_end": "int" } ],
  "confidence": "high | low",
  "intent": "tafsir | general_islamic | off_topic | fiqh_ruling"
}
```

**Graph nodes:**

**`normalize`.** Strip @mentions, hashtags, excess whitespace, and platform-specific formatting. Mints the `turn_id` used as the read-model idempotency key.

**`classify`.** A fast, low-cost LLM call classifies the query into one of four intents: `tafsir`, `general_islamic`, `fiqh_ruling`, or `off_topic`. Only `off_topic` short-circuits — it routes straight to `refuse` with zero embedding and zero Qdrant calls. `fiqh_ruling` queries — including first-person questions like "Can I pray with nail polish?" — proceed to retrieval and generation; `finalize` prepends a note that the response presents scholarly perspectives, not a personal ruling.

**`plan_query`.** Rewrites conversational follow-ups into a standalone question using checkpointed history, and decomposes multi-part questions into up to three sub-queries. Then resolves Ayah references per sub-query ("2:255", "Ayat al-Kursi", "Al-Fatiha") to `surah_number` / `ayah_start` / `ayah_end`, which become metadata filters. **Overlap semantics**, not containment — a chunk spanning 2:253–260 must match a query for 2:255.

**`retrieve` (parallel fan-out).** One `Send` per sub-query × collection. Each embeds with both the dense model (OpenAI) and the sparse BM42 model (fastembed); Qdrant runs two prefetch branches and fuses via server-side RRF.

**`fuse`.** Per-call RRF scores are not comparable across calls, so results are merged by **client-side rank fusion** (`Σ weight / (60 + rank)`), not by sorting on score.

**`grade`.** One cheap structured call scores all retrieved chunks for relevance. A weak batch routes to `broaden`, which walks a relaxation ladder (`widen_k` → `drop_ayah` → `neighbour_ayat` → `drop_scholar`) and retries, bounded at two attempts. This produces the real `confidence` signal.

**`generate`.** Primary model: Claude Sonnet or GPT-4o. Temperature 0.3, max tokens 800 (500 for X). Retrieved chunks are inserted as labeled context blocks; the system prompt establishes the scholarly-assistant role, citation format `[Scholar Name on Surah:Ayah]`, and the disclaimer obligation. This is the only node that streams tokens.

**`verify`.** Each citation is resolved against the chunks actually retrieved. Ungrounded citations are stripped and confidence drops; if *zero* citations are grounded the guardrail is violated and the answer is regenerated once. This is what makes "every response cites at least one source" enforceable rather than aspirational.

**`finalize`.** Computes `confidence` from grading and verification, appends the Sources block and standard disclaimer, prepends `FIQH_NOTE` when applicable, and sets `review_required` for low-confidence responses on channels that require human approval.

**`human_review` / `persist`.** Held responses interrupt before anything is written. Approved ones are recorded to the `chat_messages` read-model, best-effort — a persistence failure never discards a generated answer.

**Standard disclaimer (appended to every response):**

> This response is an AI-assisted summary of classical Tafsir commentary. It is not a fatwa or religious ruling. Please consult a qualified Islamic scholar for guidance on religious practice.

---

### 4. Channel Delivery Layer

#### Web Chat

A React/Vite frontend posts to the FastAPI surface — `POST /api/query/stream` for token streaming, falling back to `POST /api/webhook`. Conversation history is owned by the LangGraph checkpointer and keyed on `thread_id`; the frontend no longer needs to replay it.

For the web implementation contract, see `docs/WEB-POC-CONTRACT.md`.

#### Telegram

A `python-telegram-bot` polling adapter maps `chat_id` → `session_id` and posts to the same endpoint with `channel: "telegram"`. Telegram is the recommended prototyping channel: no API approval overhead, and its message-editing support makes streaming genuinely usable. See issue #17.

#### WhatsApp

The Meta Cloud API (or a middleware provider such as Twilio or 360dialog) is used for WhatsApp. The pattern is identical to Telegram: inbound webhook → the same endpoint → outbound send.

#### X (Twitter) Auto-Reply

X requires a polling approach rather than a webhook, as filtered stream access requires elevated API access tiers.

```
Scheduled poller (every 60–120 seconds)
  --> Search: "@YourBotHandle"
  --> Filter: exclude already-processed tweet IDs
       (last processed ID stored in Postgres)
  --> For each new mention:
        --> POST /api/webhook with channel: "x"
        --> Format response (thread if > 280 characters)
        --> Reply to original tweet
        --> Store tweet ID as processed
```

X API tier requirements: Basic tier ($100/month) is the minimum for write access at any meaningful volume. During prototyping, volume is low enough that manual rate limit management is feasible. The free tier does not support write access.

If response confidence is flagged as low, the graph interrupts before persisting and the response is held for human approval rather than published automatically.

---

### 5. Infrastructure & Deployment

All components run on a single VPS using Docker Compose. The recommended minimum specification is 4 vCPU and 8 GB RAM. Qdrant's memory usage scales with corpus size; budget additional RAM as the corpus grows.

**Services in docker-compose.yml:**

| Service | Image | Notes |
|---|---|---|
| API | built from repo | FastAPI + the compiled LangGraph graph, via uvicorn |
| Qdrant | qdrant/qdrant | Vector database |
| Postgres | postgres:15 | LangGraph checkpoints, session history, review queue, eval runs |
| Nginx | nginx:alpine | Reverse proxy, TLS termination. **SSE needs `proxy_buffering off; proxy_read_timeout 300s;`** |

For the current local PoC, Postgres is used for:

- chat session metadata
- persisted chat messages
- saved test run summaries
- per-case test outputs

### Local Postgres setup

1. Copy `.env.example` to `.env` and set the Postgres values.
2. Start infrastructure with `docker compose up -d postgres qdrant`.
3. Apply schema migrations with `uv run python scripts/persistence/migrate.py`.
4. Run the PoC normally, or add persistence flags:
   - `uv run python scripts/rag_poc.py --persist "Explain Quran 2:255"`
   - `uv run python scripts/test_poc.py --quick --persist`

The Python scripts run on the host by default, so `POSTGRES_HOST` should be `localhost`.
If a future API layer or worker runs inside Docker Compose, it should use `POSTGRES_HOST=postgres`
instead.

**Recommended providers:** Hetzner CX31 or DigitalOcean 4GB Droplet for initial deployment. Upgrade to 8GB when the corpus exceeds approximately 100,000 chunks.

**External API dependencies:**

- OpenAI API (embeddings and LLM generation) or Anthropic API
- Telegram Bot API
- X API (Basic tier)
- Meta Cloud API or WhatsApp middleware provider

---

## Guardrails & Scholarly Integrity

- Every response includes the standard disclaimer (see Step 7 above). This cannot be disabled.
- Jurisprudential questions (`fiqh_ruling` intent) are answered with scholarly perspectives from the corpus, prefixed with a note that the response is not a personal fatwa. Only queries entirely unrelated to Islam (`off_topic`) are refused.
- Every response cites at least one source using the format `[Scholar Name on Surah:Ayah]` (for Tafsir chunks) or `[Scholar Name on Topic]` (for fiqh/fatawa chunks). Responses with no retrievable source are not published.
- Low-confidence responses on the X channel are held for human review before publishing. On other channels, a low-confidence flag is noted in the response.
- Scholarly disagreement is surfaced explicitly — multiple madhab positions are presented where they exist rather than a single view being presented as authoritative.
- A curated refusal list of query patterns is maintained and reviewed periodically.

---

## Corpus Selection

The corpus covers four text types: **Tafsir** (Quranic commentary), **fiqh** (jurisprudence manuals and encyclopedias), **fatawa** (legal opinions), and **hadith** (prophetic traditions with grading). All four Sunni madhabs are represented; the bot is madhab-agnostic and presents multiple positions where scholars differ.

- See [docs/TAFSIR-CHOICES.md](docs/TAFSIR-CHOICES.md) for per-source analysis of Tafsir works (current) and fiqh/fatawa sources (in progress).
- See [docs/RESEARCH-AGENT-BRIEF.md](docs/RESEARCH-AGENT-BRIEF.md) for the brief used to research and evaluate fiqh/fatawa candidate sources.

---

## Environment Variables

```env
# LLM
OPENAI_API_KEY=
ANTHROPIC_API_KEY=           # if using Claude

# Embedding
EMBEDDING_MODEL=text-embedding-3-large

# Vector DB
QDRANT_HOST=localhost        # `qdrant` from inside the Compose network
QDRANT_PORT=6333
QDRANT_COLLECTION=tafsir
QDRANT_HADITH_COLLECTION=hadith

# Telegram
TELEGRAM_BOT_TOKEN=

# X (Twitter)
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_SECRET=
TWITTER_BOT_HANDLE=

# WhatsApp
WHATSAPP_API_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=tafsir_bot
POSTGRES_USER=tafsirbot
POSTGRES_PASSWORD=tafsirbot_dev_password
POSTGRES_SSLMODE=prefer
POSTGRES_CONNECT_TIMEOUT=5

# Migrations — on in dev; off in prod, where a deploy step runs them
# (prevents N uvicorn workers racing on DDL)
TAFSIRBOT_RUN_MIGRATIONS=1
```

> This list is aspirational for the channel variables. `.env.example` is the authoritative set of
> variables the code actually reads today; after epic #38, `src/tafsirbot/settings.py` is.

## Postgres failure modes in the current repo

- Empty `POSTGRES_USER` or `POSTGRES_PASSWORD` values can prevent the Postgres container from initializing cleanly.
- Using `POSTGRES_HOST=postgres` from a host-run Python script will fail, because that hostname only resolves inside the Compose network.
- Changing `POSTGRES_DB`, `POSTGRES_USER`, or `POSTGRES_PASSWORD` after the `postgres_data` volume already exists can leave the container healthy but make logins fail with old credentials still persisted in the volume.
- Starting the Python scripts before Postgres is ready can cause connection failures; the compose healthcheck helps, but migrations and app scripts still need the container to be up first.
- Schema changes are not automatic unless `scripts/persistence/migrate.py` is run, so a fresh container without migrations will connect successfully but fail on missing tables.

---

## TODO

### Phase 1 — Foundation (complete)

- [x] Finalize Tafsir corpus selection (see [docs/TAFSIR-CHOICES.md](docs/TAFSIR-CHOICES.md))
- [x] Source and clean raw text for Phase 1 corpus (Ibn Kathir EN + Maududi EN)
- [x] Build and test `clean.py`, `chunk.py`, `embed.py`, `upsert.py` ingestion scripts
- [x] Stand up Qdrant via Docker Compose locally
- [x] Build Python POC RAG script (`scripts/rag_poc.py`) with hybrid BM42+dense retrieval
- [x] Internal testing: `audit.py` + `test_poc.py` against a curated query set
- [ ] Run `test_poc.py` full suite and document results in `docs/AUDIT-REPORT.md`

### Phase 2 — Fiqh Corpus + Refinement

- [ ] Research and select fiqh/fatawa sources (see [docs/RESEARCH-AGENT-BRIEF.md](docs/RESEARCH-AGENT-BRIEF.md)); update [docs/TAFSIR-CHOICES.md](docs/TAFSIR-CHOICES.md)
- [ ] Extend chunk metadata schema with `corpus_type` and `madhab` fields; run `upsert.py --recreate`
- [ ] Build acquisition + ingestion scripts for Phase 2 fiqh/fatawa sources
- [ ] Tune intent classifier; validate fiqh-adjacent queries return scholarly content with correct disclaimer
- [x] Add conversation history persistence to Postgres (keyed on channel + user ID)
- [ ] **LangGraph rearchitecture + `src/tafsirbot/` package overhaul — epic #38, PRs #27–#37**
- [ ] Build the Telegram channel adapter (#17)
- [ ] Onboard a small group of external testers on Telegram
- [ ] Establish a human review queue for low-confidence responses (#36)
- [ ] Have a person with Islamic scholarly knowledge audit a sample of responses for accuracy

### Phase 3 — Arabic Corpus + Additional Channels

- [ ] Research Arabic-capable sparse embedding model to pair with `multilingual-e5-large`
- [ ] Create `tafsir_ar` Qdrant collection; ingest first Arabic source (e.g. Kuwaiti Fiqh Encyclopedia)
- [ ] Build language-routing layer in query pipeline (detect language → fan out to EN + AR collections)
- [ ] Build the X auto-reply poller; acquire X Basic API tier access
- [ ] Build the WhatsApp channel adapter (Meta Cloud API or middleware)
- [ ] Test all channels end-to-end with the production corpus

### Phase 4 — Scale & Quality

- [ ] Expand Arabic corpus (Al-Qurtubi, Al-Tabari, Zuhayli, Ibn Ashur)
- [ ] Implement usage analytics (query volume, confidence distribution, channel breakdown, madhab distribution of retrieved chunks)
- [ ] Set up automated alerting for graph node failures and API quota thresholds
- [ ] Checkpoint retention job (20–40 rows per turn accumulates quickly)
- [ ] Periodic review of guardrail effectiveness and scholarly accuracy
- [ ] Assess whether a fine-tuned embedding model on Islamic text improves retrieval quality

### Ongoing

- [ ] Monitor X API rate limit consumption and upgrade tier if needed
- [ ] Keep Tafsir corpus attribution and licensing documentation up to date
- [ ] Regular review of LLM-generated responses for theological accuracy
- [ ] Maintain the standard disclaimer language in line with any legal or community feedback
