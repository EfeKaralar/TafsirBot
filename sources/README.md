# AI Islamic Scholarly Assistant (TafsirBot)

An AI-powered Islamic scholarly assistant built on a Retrieval-Augmented Generation (RAG) pipeline, orchestrated through self-hosted n8n, and delivered across multiple channels including a web chat interface, Telegram, WhatsApp, and X (Twitter).

The corpus covers Quranic commentary (Tafsir), Islamic jurisprudence (fiqh), and scholarly legal opinions (fatawa). The bot presents what scholars say on any Islamic topic — including jurisprudential questions — with a clear disclaimer that responses are not personal rulings. Only queries entirely unrelated to Islam are declined.

---

## Table of Contents

- [Project Goals](#project-goals)
- [System Architecture](#system-architecture)
  - [Overview](#overview)
  - [1. Corpus Ingestion Layer](#1-corpus-ingestion-layer)
  - [2. Vector Storage](#2-vector-storage)
  - [3. RAG Core — n8n Orchestration](#3-rag-core--n8n-orchestration)
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

The system is divided into four layers: ingestion, storage, RAG orchestration, and delivery. All query processing flows through a single canonical n8n workflow regardless of which channel initiated the request. Channel-specific n8n workflows handle platform normalization and then call the core RAG workflow as a sub-workflow.

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
|              RAG CORE WORKFLOW (n8n sub-workflow)            |
|  1. Input normalization                                      |
|  2. Intent classification                                    |
|  3. Ayah reference resolution                                |
|  4. Vector retrieval (with metadata filtering)               |
|  5. Prompt assembly                                          |
|  6. LLM generation                                           |
|  7. Post-processing & citation formatting                    |
+--------------------------------------------------------------+
                             |
          +------------------+------------------+
          |                  |                  |
          v                  v                  v
  +---------------+  +---------------+  +---------------+
  |  Web / Tele-  |  |  X (Twitter)  |  |  WhatsApp     |
  |  gram Chat    |  |  Auto-reply   |  |  (Meta Cloud  |
  |  (Webhook     |  |  (Scheduled   |  |   API)        |
  |   trigger)    |  |   polling)    |  |               |
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

**Embedding models:**
- **Dense:** `text-embedding-3-large` (OpenAI, 3072 dims, cosine) — English-first corpus default.
- **Sparse:** `Qdrant/bm42-all-minilm-l6-v2-attentions` via `fastembed` — BM42 sparse vectors for exact-term retrieval (verse refs, transliterated Arabic, scholar names). Downloaded ~130 MB on first run, cached in `~/.cache/fastembed/`.

**Never mix dense embedding models in the same Qdrant collection.** Vectors from different models are not comparable, making cross-vector retrieval meaningless. Arabic sources require a separate collection (see Vector Storage below).

For the full corpus selection discussion — Tafsir, fiqh, and fatawa — see [docs/TAFSIR-CHOICES.md](docs/TAFSIR-CHOICES.md) and [docs/RESEARCH-AGENT-BRIEF.md](docs/RESEARCH-AGENT-BRIEF.md).

---

### 2. Vector Storage

**Database:** Qdrant, self-hosted via Docker.

Qdrant is chosen for its native metadata filtering, strong n8n integration, and low operational overhead compared to Weaviate. All retrieval requests apply a metadata pre-filter on `surah_number` and `ayah_start`/`ayah_end` when the query contains a specific Ayah reference, significantly narrowing the candidate set before semantic ranking.

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

### 3. RAG Core — n8n Orchestration

This is the central n8n sub-workflow. It is channel-agnostic: every channel workflow calls it with a normalized input object and receives a normalized response object.

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

**Workflow steps:**

**Step 1 — Input Normalization.** Strip @mentions, hashtags, excess whitespace, and platform-specific formatting. Detect language.

**Step 2 — Intent Classification.** A fast, low-cost LLM call classifies the query into one of four intents: `tafsir`, `general_islamic`, `fiqh_ruling`, or `off_topic`. Only `off_topic` queries are refused. `fiqh_ruling` queries — including first-person questions like "Can I pray with nail polish?" — proceed to retrieval and generation; the response is prefixed with a note that it presents scholarly perspectives, not a personal ruling. `general_islamic` queries proceed with a lower-confidence flag.

**Step 3 — Ayah Reference Resolution.** A regex pass and then a lookup against a static Quran JSON file resolves any Ayah references in the query (e.g. "2:255", "Ayat al-Kursi", "Al-Fatiha") to normalized `surah_number` / `ayah_start` / `ayah_end` values. These become hard filters in the retrieval step. If no reference is detected, retrieval proceeds without a metadata filter.

**Step 4 — Hybrid Retrieval.** The query is embedded with both the dense model (OpenAI) and the sparse BM42 model (fastembed). Qdrant runs two prefetch branches (dense + sparse) and fuses results via server-side RRF. Metadata pre-filters are applied inside each prefetch block when an Ayah reference was resolved.

**Step 5 — Prompt Assembly.** The system prompt establishes the bot's role (scholarly assistant, not a mufti), its citation requirements, and the disclaimer obligation. Retrieved chunks are inserted as labeled context blocks. The last three to five turns of conversation history are appended for follow-up coherence.

**Step 6 — LLM Generation.** Primary model: GPT-4o or Claude Sonnet. Temperature: 0.3. Max tokens: 800 for most channels, 500 for X to allow room for threading logic. The model is instructed to cite sources using the format `[Scholar Name on Surah:Ayah]`.

**Step 7 — Post-Processing.** Citations are extracted and structured. If retrieval scores were uniformly low (confidence = low), the response is flagged and optionally routed to a human moderation queue rather than auto-published (especially relevant for the X channel). The platform-specific length limit is enforced. The standard disclaimer is appended.

**Standard disclaimer (appended to every response):**

> This response is an AI-assisted summary of classical Tafsir commentary. It is not a fatwa or religious ruling. Please consult a qualified Islamic scholar for guidance on religious practice.

---

### 4. Channel Delivery Layer

#### Web Chat

A lightweight frontend (React or a hosted no-code alternative during early prototyping) communicates with n8n via a webhook POST endpoint. The n8n webhook node acts as the backend API. Session-based conversation history is maintained either in the frontend state or in a simple Postgres table keyed on session ID.

#### Telegram

n8n's native Telegram Trigger node listens for incoming messages via webhook. The message is passed to the core RAG sub-workflow. The response is returned via the Telegram Send Message node. Telegram is the recommended prototyping channel due to the simplicity of the n8n integration and the lack of API approval overhead.

#### WhatsApp

The Meta Cloud API (or a middleware provider such as Twilio or 360dialog) is used for WhatsApp. The integration pattern is identical to Telegram: inbound webhook trigger, core RAG sub-workflow call, outbound send node.

#### X (Twitter) Auto-Reply

X requires a polling approach rather than a webhook, as filtered stream access requires elevated API access tiers.

```
n8n Schedule Trigger (every 60–120 seconds)
  --> Twitter Search node: query "@YourBotHandle"
  --> Filter: exclude already-processed tweet IDs
       (last processed ID stored in n8n static data or Postgres)
  --> For each new mention:
        --> Core RAG sub-workflow
        --> Format response (thread if > 280 characters)
        --> Twitter Post node: reply to original tweet
        --> Store tweet ID as processed
```

X API tier requirements: Basic tier ($100/month) is the minimum for write access at any meaningful volume. During prototyping, volume is low enough that manual rate limit management is feasible. The free tier does not support write access.

If response confidence is flagged as low, the tweet is held in a review queue (a Postgres table) rather than published automatically.

---

### 5. Infrastructure & Deployment

All components run on a single VPS using Docker Compose. The recommended minimum specification is 4 vCPU and 8 GB RAM. Qdrant's memory usage scales with corpus size; budget additional RAM as the corpus grows.

**Services in docker-compose.yml:**

| Service | Image | Notes |
|---|---|---|
| n8n | n8nio/n8n | Workflow orchestrator |
| Qdrant | qdrant/qdrant | Vector database |
| Postgres | postgres:15 | n8n metadata, session history, review queue |
| Nginx | nginx:alpine | Reverse proxy, TLS termination |

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
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION=tafsir

# n8n
N8N_BASIC_AUTH_USER=
N8N_BASIC_AUTH_PASSWORD=
N8N_HOST=
WEBHOOK_URL=

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
POSTGRES_DB=tafsir_bot
POSTGRES_USER=
POSTGRES_PASSWORD=
```

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
- [ ] Add conversation history persistence to Postgres (keyed on channel + user ID)
- [ ] Port RAG pipeline to n8n; build Telegram channel workflow
- [ ] Onboard a small group of external testers on Telegram
- [ ] Establish a human review queue for low-confidence responses
- [ ] Have a person with Islamic scholarly knowledge audit a sample of responses for accuracy

### Phase 3 — Arabic Corpus + Additional Channels

- [ ] Research Arabic-capable sparse embedding model to pair with `multilingual-e5-large`
- [ ] Create `tafsir_ar` Qdrant collection; ingest first Arabic source (e.g. Kuwaiti Fiqh Encyclopedia)
- [ ] Build language-routing layer in query pipeline (detect language → fan out to EN + AR collections)
- [ ] Build the web chat frontend and connect it to the n8n webhook endpoint
- [ ] Build the X auto-reply polling workflow; acquire X Basic API tier access
- [ ] Build the WhatsApp channel workflow (Meta Cloud API or middleware)
- [ ] Test all channels end-to-end with the production corpus

### Phase 4 — Scale & Quality

- [ ] Expand Arabic corpus (Al-Qurtubi, Al-Tabari, Zuhayli, Ibn Ashur)
- [ ] Implement usage analytics (query volume, confidence distribution, channel breakdown, madhab distribution of retrieved chunks)
- [ ] Set up automated alerting for n8n workflow failures and API quota thresholds
- [ ] Periodic review of guardrail effectiveness and scholarly accuracy
- [ ] Assess whether a fine-tuned embedding model on Islamic text improves retrieval quality

### Ongoing

- [ ] Monitor X API rate limit consumption and upgrade tier if needed
- [ ] Keep Tafsir corpus attribution and licensing documentation up to date
- [ ] Regular review of LLM-generated responses for theological accuracy
- [ ] Maintain the standard disclaimer language in line with any legal or community feedback
