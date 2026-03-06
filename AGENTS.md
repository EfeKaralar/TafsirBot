# Repository Guidelines

## Project Structure & Module Organization

- `docs/` — planning and corpus-selection documents
  - `docs/TAFSIR-CHOICES.md` — per-tafsir analysis, RAG chunking strategy, audience fit
  - `docs/TAFSIR-CORPUS.mdx` — interactive React corpus dashboard component
- `sources/` — source datasets and upstream content
  - `sources/quran-json/` — Git submodule: Quran JSON generation scripts and data pipeline
  - `sources/quran-json/dist/` — generated build artifacts (quran.json, quran_en.json, chapters/, verses/)
  - `sources/README.md` — full system architecture, environment variables, and phase TODO list
- `scripts/` — ingestion and tooling scripts (to be created in Phase 1)
  - `scripts/ingestion/` — offline pipeline: clean.py, chunk.py, embed.py, upsert.py, audit.py
- `n8n/` — n8n workflow exports (to be created in Phase 1)
  - `n8n/workflows/` — JSON exports of all n8n workflow definitions
- `docker-compose.yml` — infrastructure: Qdrant, n8n, Postgres, Nginx (to be created in Phase 1)
- `.env.example` — environment variable template (secrets never committed)
- `CLAUDE.md` — project-specific guidance for AI coding assistants


## Build, Test, and Development Commands

### Quran JSON submodule
- `git submodule update --init --recursive` — fetch the quran-json submodule
- `cd sources/quran-json && npm install` — install Node dependencies
- `cd sources/quran-json && npm run build` — regenerate dist/ from data/
- `cd sources/quran-json && node scripts/download.js` — fetch source data (skips existing)
- `cd sources/quran-json && node scripts/download.js --clean` — clear and re-download

### Python setup
- `uv sync` — install all dependencies and create/update `uv.lock`
- Never use `pip install` directly; add new deps to `pyproject.toml` then re-run `uv sync`
- Python is pinned to **3.12** (`.python-version`). Do not upgrade to 3.13+ until `onnxruntime` (used by `fastembed`) confirms support.

### Ingestion pipeline (Python)
- `uv run python scripts/ingestion/clean.py --scholar ibn_kathir`
- `uv run python scripts/ingestion/chunk.py --scholar ibn_kathir`
- `uv run python scripts/ingestion/embed.py --scholar ibn_kathir`
- `uv run python scripts/ingestion/upsert.py --scholar ibn_kathir` — upsert with dense+sparse vectors
- `uv run python scripts/ingestion/upsert.py --scholar all --recreate` — drop and rebuild collection (required after schema changes)
- `uv run python scripts/ingestion/audit.py` — hybrid retrieval quality report

### Infrastructure
- `docker compose up -d` — start Qdrant, n8n, Postgres, Nginx
- `docker compose down` — stop all services
- `docker compose logs -f n8n` — tail n8n logs


## Coding Style & Naming Conventions

### Python (scripts/ingestion/)
- Python 3.11+; `snake_case` for variables and functions, `PascalCase` for classes
- Type hints on all function signatures
- Structured logging via the standard `logging` module (not `print`)
- No secrets in source; read all credentials from environment variables
- Raise specific exceptions; never bare `except: pass`
- Dependencies declared in `scripts/ingestion/requirements.txt` or `pyproject.toml`

### JavaScript (sources/quran-json/scripts/)
- CommonJS (`require`), async/await, 2-space indentation, semicolons, single quotes
- lowerCamelCase for variables and functions
- Keep generated filenames consistent: `quran_<lang>.json`, `chapters/<lang>/<id>.json`, `verses/<id>.json`

### n8n Workflows
- Export workflows as JSON to `n8n/workflows/` after any structural change
- Name workflows consistently: `tafsir-rag-core`, `channel-telegram`, `channel-web`, etc.
- Use n8n sub-workflow pattern: channel workflows call the core RAG sub-workflow


## Data & Chunking Conventions

- **Chunk by ayah boundaries, never by fixed token windows.** Each chunk must map to a citable ayah range.
- Required metadata on every chunk: `surah_number`, `ayah_start`, `ayah_end`, `scholar`, `language`, `source_title`, `english_text`, `arabic_text`, `chunk_type`
- `chunk_type` values: `verse` (standard commentary), `intro` (Maududi surah introductions), `legal` (Qurtubi legal reasoning blocks)
- Never mix embeddings from different models in the same Qdrant collection
- Strip isnad chains from Ibn Kathir and Al-Tabari before embedding (or move to a separate metadata field)
- Maududi surah introductions are a distinct chunk type and should not be merged with verse-level chunks


## Testing Guidelines

- No formal automated test framework is configured yet
- For ingestion changes: run the full pipeline (`clean → chunk → embed → upsert`) on a single surah (e.g. Al-Fatiha, surah 1) before running on the full corpus
- Run `audit.py` with a test query set (~50 queries) to validate retrieval quality
- Spot-check representative chunks from `dist/` after any quran-json build change


## Commit & Pull Request Guidelines

- Short, imperative commit subjects: `Add chunk.py ingestion script`, `Fix isnad stripping regex`
- Add a commit body when changing data-generation behavior or chunking logic
- PRs must include: purpose, impacted paths, any schema changes, and sample output diffs when dist/ or chunk output changes
- Update `sources/README.md` and relevant `docs/` files in the same PR when architecture or schema assumptions change


## Security & Configuration

- Never commit `.env` files, API keys, or credentials of any kind
- All secrets live in `.env` (gitignored); reference `.env.example` for the variable list
- Review third-party source URLs in ingestion scripts before modifying data fetch logic
- Qdrant and n8n admin interfaces must be behind Nginx with auth in production


## Guardrails Reference (for n8n workflow development)

- `fiqh_ruling` intent → retrieve and generate; prepend FIQH_NOTE disclaimer that response is scholarly context, not a personal ruling
- `off_topic` intent → polite refusal, do not retrieve
- Low retrieval confidence on X channel → hold response in Postgres review queue, do not auto-publish
- Standard disclaimer is appended to every published response (hardcoded, not LLM-generated)
- Every published response must include at least one `[Scholar on Surah:Ayah]` citation
