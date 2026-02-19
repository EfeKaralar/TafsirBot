# AI Tafsir Bot

An AI-powered Quranic commentary assistant built on a Retrieval-Augmented Generation (RAG) pipeline, orchestrated through self-hosted n8n, and delivered across multiple channels including a web chat interface, Telegram, WhatsApp, and X (Twitter).

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

- Provide accurate, source-cited Quranic commentary by surfacing responses from established classical and modern Tafsir works.
- Support multi-channel interaction: web chat, Telegram, WhatsApp, and X auto-reply.
- Maintain scholarly integrity through transparent sourcing, clear disclaimers, and refusal of fatwa-style rulings.
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

**Chunking strategy:** Chunks are scoped to individual Ayahs or contiguous Ayah ranges, not fixed token windows. This is a deliberate departure from general-purpose RAG design. Ayah-scoped chunking ensures retrieval results map cleanly to citable scripture references and prevents a chunk from straddling thematically unrelated verses.

Each chunk carries the following metadata:

| Field | Description |
|---|---|
| `surah_number` | Integer (1–114) |
| `ayah_start` | First Ayah in chunk |
| `ayah_end` | Last Ayah in chunk (same as start for single-Ayah chunks) |
| `scholar` | Identifier string, e.g. `ibn_kathir`, `maududi` |
| `language` | `ar`, `en`, or other ISO 639-1 code |
| `source_title` | Full title of the Tafsir work |
| `english_text` | The English translation of the Ayah(s) covered | 
| `arabic_text` | Raw Arabic text of the Ayah(s) covered |

**Ingestion pipeline scripts:**

```
scripts/ingestion/
  clean.py       -- Remove OCR artifacts, headers, footers, diacritical normalization
  chunk.py       -- Split source text into Ayah-scoped chunks with metadata
  embed.py       -- Generate embeddings via the configured embedding model
  upsert.py      -- Push chunks into Qdrant
  audit.py       -- Spot-check retrieval quality for a set of test queries
```

**Embedding model:** For an English-first corpus, `text-embedding-3-large` (OpenAI) is the default. If Arabic-language Tafsir texts are ingested, switch to a multilingual model such as `intfloat/multilingual-e5-large` and re-embed the entire corpus. Do not mix embeddings from different models in the same Qdrant collection.

For discussion of which Tafsir works to ingest and in which priority order, see [docs/TAFSIR-CHOICE.md](docs/TAFSIR-CHOICE.md).

---

### 2. Vector Storage

**Database:** Qdrant, self-hosted via Docker.

Qdrant is chosen for its native metadata filtering, strong n8n integration, and low operational overhead compared to Weaviate. All retrieval requests apply a metadata pre-filter on `surah_number` and `ayah_start`/`ayah_end` when the query contains a specific Ayah reference, significantly narrowing the candidate set before semantic ranking.

**Collection design:**

A single collection named `tafsir` is used initially, with scholar and language as filterable metadata fields. If corpus size grows beyond roughly 500,000 vectors or if per-scholar latency becomes an issue, split into per-scholar collections.

**Retrieval parameters:**

- Top-K: 5–8 chunks per query
- Distance metric: Cosine
- Metadata filter applied before vector search when Ayah reference is detected

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

**Step 2 — Intent Classification.** (**TODO:** Could be improved) A fast, low-cost LLM call (GPT-4o-mini or equivalent) classifies the query into one of four intents: `tafsir`, `general_islamic`, `fiqh_ruling`, or `off_topic`. Queries classified as `fiqh_ruling` are short-circuited with a standard message directing the user to consult a qualified scholar. Queries classified as `off_topic` are refused politely.

**Step 3 — Ayah Reference Resolution.** A regex pass and then a lookup against a static Quran JSON file resolves any Ayah references in the query (e.g. "2:255", "Ayat al-Kursi", "Al-Fatiha") to normalized `surah_number` / `ayah_start` / `ayah_end` values. These become hard filters in the retrieval step. If no reference is detected, retrieval proceeds without a metadata filter.

**Step 4 — Vector Retrieval.** The query is embedded and the top-K chunks are retrieved from Qdrant. If an Ayah reference was resolved, a metadata pre-filter is applied. Results from multiple scholars are requested where possible to avoid single-source responses.

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
- Queries classified as `fiqh_ruling` (requests for fatwa-style religious rulings) are refused by the intent classifier and redirected to a message advising the user to consult a qualified scholar.
- Every response cites at least one source using the format `[Scholar Name on Surah:Ayah]`. Responses with no retrievable source are not published.
- Low-confidence responses on the X channel are held for human review before publishing. On other channels, a low-confidence flag is noted in the response.
- Politically contentious or sectarian interpretive questions are handled with explicit acknowledgment of scholarly disagreement rather than presenting a single view as authoritative.
- A curated refusal list of query patterns is maintained and reviewed periodically.

---

## Tafsir Corpus Selection

The choice of which Tafsir works to include, in which languages, and in which priority order has significant implications for the theological perspective and scope of the bot. This is treated as a separate ongoing discussion.

See [docs/TAFSIR-CHOICE.md](docs/TAFSIR-CHOICE.md) for the full discussion, including candidate works, inclusion criteria, licensing considerations, and phased ingestion plan.

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

### Phase 1 — Foundation

- [ ] Finalize Tafsir corpus selection (see [docs/TAFSIR-CHOICE.md](docs/TAFSIR-CHOICE.md))
- [ ] Source and clean raw text for the Phase 1 corpus (minimum two works)
- [ ] Build and test `clean.py`, `chunk.py`, `embed.py`, `upsert.py` ingestion scripts
- [ ] Stand up Qdrant and Postgres via Docker Compose on the VPS
- [ ] Build the core RAG n8n sub-workflow (Steps 1–7)
- [ ] Build the Telegram channel workflow and connect to the sub-workflow
- [ ] Internal testing: evaluate retrieval quality across a test set of ~50 queries
- [ ] Run `audit.py` and fix chunking or metadata issues surfaced by testing

### Phase 2 — Refinement

- [ ] Tune the intent classifier prompt; build and evaluate the refusal list
- [ ] Add conversation history persistence to Postgres (keyed on channel + user ID)
- [ ] Evaluate embedding model choice; assess whether multilingual support is needed
- [ ] Onboard a small group of external testers on Telegram
- [ ] Establish a human review queue for low-confidence responses
- [ ] Have a person with Islamic scholarly knowledge audit a sample of responses for accuracy

### Phase 3 — Additional Channels

- [ ] Build the web chat frontend and connect it to the n8n webhook endpoint
- [ ] Build the X auto-reply polling workflow
- [ ] Acquire X Basic API tier access
- [ ] Build the WhatsApp channel workflow (Meta Cloud API or middleware)
- [ ] Test all channels end-to-end with the production corpus

### Phase 4 — Scale & Quality

- [ ] Expand corpus to additional Tafsir works (see [docs/TAFSIR-CHOICE.md](docs/TAFSIR-CHOICE.md))
- [ ] Evaluate per-scholar Qdrant collection split if latency or corpus size warrants it
- [ ] Assess Arabic-language query support; switch embedding model if proceeding
- [ ] Implement usage analytics (query volume, confidence distribution, channel breakdown)
- [ ] Set up automated alerting for n8n workflow failures and API quota thresholds
- [ ] Periodic review of the refusal list and guardrail effectiveness
- [ ] Assess whether a fine-tuned embedding model on Quranic text improves retrieval quality

### Ongoing

- [ ] Monitor X API rate limit consumption and upgrade tier if needed
- [ ] Keep Tafsir corpus attribution and licensing documentation up to date
- [ ] Regular review of LLM-generated responses for theological accuracy
- [ ] Maintain the standard disclaimer language in line with any legal or community feedback
