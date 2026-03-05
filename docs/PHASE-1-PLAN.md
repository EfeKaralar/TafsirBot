# Phase 1 Implementation Plan

> **Scope:** Local-only Python POC. n8n, VPS deployment, and Telegram channel are deferred to Phase 2.
> **Primary corpus:** Ibn Kathir (EN) + Maududi (EN).
> **Blocker:** Corpus source must be decided before any ingestion work begins (see Step 0).

---

## Step 0 — Corpus Acquisition (Blocker)

No ingestion code can run until we have raw text. This must be resolved first.

### Candidate sources

**Ibn Kathir — *Tafsir al-Quran al-Azim***
- Translation: Dar-us-Salam (10-volume abridged English edition). This is the most widely used and quality-checked English translation — however it is an **abridgment**; isnad chains are often compressed or removed entirely compared to the full Arabic.
- Potential sources: `quranx.com`, `altafsir.com`, community plaintext mirrors on GitHub (copyright status varies), direct PDF purchase and OCR.
- Decision needed: abridged English vs. full Arabic? The English abridgment is easier to embed and serves English-first users better in Phase 1.

**Maududi — *Tafhim al-Quran***
- Translation: *Towards Understanding the Quran* (The Islamic Foundation). Well-regarded; note it is a translation of an Urdu original, adding one layer of interpretive distance from the Arabic.
- Potential sources: `islamicstudies.info` (hosts the complete text), structured JSON datasets on GitHub.

### Deliverable
Create `docs/CORPUS-SOURCES.md` documenting for each tafsir:
- Chosen source URL or file
- License / usage status
- Download or extraction method
- Specific edition and abridgment status

---

## Step 1 — Project Scaffolding

Create the directory structure, Docker Compose, and environment template.

```
scripts/
  ingestion/
    requirements.txt          # qdrant-client, openai, python-dotenv, tqdm
    clean.py
    chunk.py
    embed.py
    upsert.py
    audit.py
    utils/
      quran_ref.py            # loads quran-json dist/ for english/arabic text lookup
      ayah_resolver.py        # resolves "2:255", "Ayat al-Kursi", etc. → (surah, ayah)
docker-compose.yml            # Qdrant + Postgres (no n8n yet)
.env.example                  # all required env vars, no values
```

### `docker-compose.yml` services (Phase 1 subset)

| Service | Image | Port | Notes |
|---|---|---|---|
| Qdrant | `qdrant/qdrant` | 6333 | Vector store |
| Postgres | `postgres:15` | 5432 | Future: sessions, review queue |

### `.env.example` variables (Phase 1 subset)

```env
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
LLM_PROVIDER=anthropic         # "anthropic" or "openai"
EMBEDDING_MODEL=text-embedding-3-large
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=tafsir
POSTGRES_DB=tafsir_bot
POSTGRES_USER=
POSTGRES_PASSWORD=
```

---

## Step 2 — Quran Reference Layer

`scripts/ingestion/utils/quran_ref.py` loads `sources/quran-json/dist/quran_en.json` and `quran.json` to provide Arabic and English Ayah text for the metadata fields on every chunk.

```python
def get_ayah(surah: int, ayah: int) -> dict:
    """Returns {"arabic_text": str, "english_text": str}"""

def get_surah_name(surah: int) -> dict:
    """Returns {"arabic": str, "english": str, "transliteration": str}"""
```

`scripts/ingestion/utils/ayah_resolver.py` extracts Ayah references from free text:

```python
def resolve(text: str) -> list[tuple[int, int]]:
    """
    Handles: "2:255", "Surah Al-Baqarah verse 255", "Ayat al-Kursi",
             "Al-Fatiha", named surahs, etc.
    Returns: [(surah_number, ayah_number), ...]
    """
```

The resolver uses a combination of regex patterns and a static lookup table of ~30 commonly referenced named verses and surah names built from the quran-json data.

---

## Step 3 — Ingestion Pipeline

All scripts are run sequentially offline. Each script reads from the previous step's output.

### `clean.py`

Per-tafsir normalization. Input: raw text files. Output: `data/cleaned/<scholar>/<surah>.txt`

**Ibn Kathir:**
- Separate *matn* (commentary body) from *isnad* chains using pattern-based extraction. Isnad markers include: "It was narrated by...", "Reported by...", chain formulae in Arabic/English transliteration.
- Store stripped isnads in a separate `isnad` field (not embedded, but preserved in metadata for potential future use).
- Normalize Unicode, smart quotes, em-dashes, ligatures.
- Remove page headers, footers, footnotes, volume/page markers.

**Maududi:**
- Split surah introductions from verse-level commentary at structural markers.
- Normalize Unicode.
- No isnad handling needed.

### `chunk.py`

Ayah-scoped chunking. Input: `data/cleaned/`. Output: `data/chunks/<scholar>.jsonl`

Each line is a JSON object conforming to the chunk metadata schema:

```json
{
  "content": "...",
  "surah_number": 2,
  "ayah_start": 255,
  "ayah_end": 255,
  "scholar": "ibn_kathir",
  "language": "en",
  "source_title": "Tafsir al-Quran al-Azim (Dar-us-Salam, abridged EN)",
  "english_text": "...",
  "arabic_text": "...",
  "chunk_type": "verse"
}
```

**Special cases:**
- Maududi surah introductions → `chunk_type: "intro"`, `ayah_start: 0`, `ayah_end: 0`
- Al-Tabari (Phase 2+) → per-opinion chunking; preserve opinion markers

### `embed.py`

Generates embeddings for the `content` field of each chunk.

- Model: `text-embedding-3-large` (3072 dimensions, cosine)
- Batches requests (max 100 texts / request per OpenAI limits)
- Exponential backoff on rate limit errors
- Input: `data/chunks/<scholar>.jsonl`
- Output: `data/embedded/<scholar>.jsonl` (same schema + `embedding` field)
- **Never mix embedding models in the same Qdrant collection**

### `upsert.py`

Pushes embedded chunks into Qdrant.

- Collection: `tafsir`, cosine distance, 3072 dims — created if not present
- Point ID: deterministic hash of `scholar + surah_number + ayah_start + chunk_type` (idempotent re-runs)
- All metadata fields stored as Qdrant payload for filtering
- Input: `data/embedded/<scholar>.jsonl`

### `audit.py`

Retrieval quality validation.

- Runs a hard-coded test query set (see Step 5)
- Prints top-5 retrieved chunks per query with cosine scores
- Flags queries where best score < 0.70 (configurable threshold)
- Summary report: mean score, score distribution, low-confidence query list

---

## Step 4 — Python POC RAG Script

`scripts/rag_poc.py` — a CLI tool that runs the full query pipeline end-to-end.

```
$ python scripts/rag_poc.py "What does Ibn Kathir say about 2:255?"
$ python scripts/rag_poc.py --scholar maududi "What is the theme of Surah Al-Baqarah?"
$ python scripts/rag_poc.py --provider openai "What do scholars say about tawakkul?"
```

### Pipeline steps

**1. Normalize input**
Strip excess whitespace; detect language.

**2. Intent classification**
Single LLM call (low-temperature, fast). Classifies into:
- `tafsir` — proceed
- `general_islamic` — proceed with lower confidence flag
- `fiqh_ruling` — refuse; return standard redirect message
- `off_topic` — polite refusal

**3. Ayah reference resolution**
Call `ayah_resolver.resolve(query)`. If references found, build Qdrant metadata filter:
```python
{"must": [{"key": "surah_number", "match": {"value": surah}},
           {"key": "ayah_start", "range": {"gte": start, "lte": end}}]}
```

**4. Vector retrieval**
Embed query → Qdrant search, top-K=5 (with metadata filter if resolved). Request at least 2 scholars where possible.

**5. Prompt assembly**
System prompt: scholarly assistant role, citation requirements, disclaimer obligation.
Context: retrieved chunks as labeled blocks (`[Ibn Kathir on 2:255]: ...`).

**6. LLM generation**
Provider selected by `LLM_PROVIDER` env var or `--provider` flag:
- `anthropic` → Claude Sonnet (`claude-sonnet-4-6`)
- `openai` → GPT-4o

Temperature: 0.3, max tokens: 800.

**7. Post-process + format**
Extract citations. Append standard disclaimer. Print response.

### Standard disclaimer
> *This response is an AI-assisted summary of classical Tafsir commentary. It is not a fatwa or religious ruling. Please consult a qualified Islamic scholar for guidance on religious practice.*

---

## Step 5 — Evaluation

### Test query set (~50 queries)

| Category | Count | Examples |
|---|---|---|
| Specific ayah — named | 10 | "Ayat al-Kursi", "Al-Fatiha", "Surah Al-Ikhlas" |
| Specific ayah — numbered | 10 | "2:255", "24:35", "112:1-4" |
| Thematic | 10 | "What does the Quran say about tawakkul?", "Justice in the Quran" |
| Cross-verse | 5 | "Verses about the Day of Judgment", "Descriptions of Jannah" |
| Linguistic | 5 | "What does 'taqwa' mean in 2:2?", "Root meaning of 'khalifa' in 2:30" |
| Edge cases — refuse | 10 | Fiqh rulings, off-topic, politically charged, sectarian framing |

### Pass criteria
- Specific ayah queries: top retrieved chunk matches the referenced surah/ayah
- Thematic queries: at least 3 of 5 retrieved chunks are relevantly topical
- Edge cases: 100% refused correctly (no tafsir content returned for fiqh/off-topic)
- Mean cosine score across non-refused queries: > 0.72

---

## Step 6 — Handoff Checklist (before Phase 2 begins)

- [ ] `docs/CORPUS-SOURCES.md` created and approved
- [ ] `docker compose up -d` runs cleanly locally
- [ ] Full corpus for Ibn Kathir + Maududi ingested into Qdrant
- [ ] `audit.py` run; all pass criteria met
- [ ] `rag_poc.py` tested against all 50 evaluation queries
- [ ] All 10 edge-case queries correctly refused
- [ ] `data/` directory added to `.gitignore` (raw and processed tafsir text must not be committed)
- [ ] Chunk counts, mean scores, and any quality issues documented in `docs/AUDIT-REPORT.md`

---

## What is Deferred to Phase 2

- n8n workflow development
- Telegram channel integration
- Conversation history persistence (Postgres)
- External user testing
- Human review queue for low-confidence responses
- Secondary corpus (Al-Qurtubi, Al-Tabari)
