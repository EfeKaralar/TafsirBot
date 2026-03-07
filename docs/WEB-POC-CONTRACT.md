# Web PoC Contract

This document freezes the local web PoC contract while the implementation is split across parallel branches.

The local stack is a temporary compatibility layer:

- web UI -> local HTTP API -> Python PoC pipeline
- later: web UI -> n8n webhook -> canonical RAG workflow

The local API should stay structurally close to the n8n input/output model described in `sources/README.md`.

## Goals

- Keep the web client decoupled from direct CLI execution
- Reuse the existing `scripts/rag_poc.py` pipeline rather than reimplementing retrieval/generation
- Persist chat conversations and saved test runs in Postgres
- Leave room for later multi-channel, multi-user expansion without overbuilding now

## Scope

This contract applies to:

- the local HTTP API for ad hoc chat
- persistence of chat sessions and messages
- persistence of `test_poc` runs and per-case outputs
- the local single-user web UI

It does not define:

- final n8n workflow JSON
- production auth or multi-user access control
- Telegram / WhatsApp / X delivery specifics

## Canonical Request

The local HTTP API should accept a POST payload shaped like this:

```json
{
  "channel": "web",
  "session_id": "local-session-id",
  "user_id": "local-user",
  "message": "What does Ibn Kathir say about 2:255?",
  "conversation_history": [
    { "role": "user", "content": "Previous user turn" },
    { "role": "assistant", "content": "Previous assistant turn" }
  ],
  "options": {
    "provider": "anthropic",
    "scholar": null,
    "top_k": 5,
    "save": true
  }
}
```

## Request Field Semantics

- `channel`: fixed to `web` for the local UI, but keep the field because it exists in the intended cross-channel model
- `session_id`: stable identifier for one local conversation thread
- `user_id`: fixed to a local single-user value for now, but required to preserve the future channel/user/session model
- `message`: current user input; this maps to `raw_query` in the eventual n8n workflow
- `conversation_history`: ordered prior turns passed into prompt assembly for follow-up coherence
- `options.provider`: `anthropic` or `openai`
- `options.scholar`: optional scholar filter; `null` means no filter
- `options.top_k`: retrieval depth override; default `5`
- `options.save`: whether the request/response should be persisted

## Canonical Chat Response

The local HTTP API should return JSON shaped like this:

```json
{
  "request_id": "uuid",
  "session_id": "local-session-id",
  "intent": "tafsir",
  "normalized_message": "What does Ibn Kathir say about 2:255?",
  "answer": "Final rendered response text",
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
      "score": 0.82,
      "source_title": "Tafsir Ibn Kathir",
      "english_text": "Allah! There is no god but He..."
    }
  ],
  "meta": {
    "provider": "anthropic",
    "top_k": 5,
    "elapsed_ms": 1234
  }
}
```

## Response Field Semantics

- `request_id`: per-request ID for logs and persistence joins
- `session_id`: echoed from the request
- `intent`: `tafsir | general_islamic | fiqh_ruling | off_topic`
- `normalized_message`: normalized form after stripping platform noise
- `answer`: final user-facing response, including standard disclaimer and any low-confidence note
- `citations`: extracted inline citation markers
- `confidence`: `high | low`
- `disclaimer_applied`: should be `true` for all generated responses; may also be `true` on fallback/error responses if the app includes it there
- `fiqh_note_applied`: `true` only when the output is prefixed with the fiqh guidance note
- `chunks`: retrieved chunk summaries for debugging and UI inspection; exclude full raw prompt assembly details
- `meta`: runtime metadata useful to the UI and saved test results

## Behavioral Rules

- `off_topic` queries are refused and do not retrieve from Qdrant
- `fiqh_ruling` queries are not refused; they retrieve/generate and prepend the fiqh note
- `general_islamic` queries retrieve/generate like `tafsir`
- all generated responses must include at least one citation if relevant chunks were found
- all generated responses must include the standard disclaimer
- low-confidence responses should surface a confidence flag and warning note

## Persistence Contract

When `options.save` is true, the API layer should persist:

- the session row if it does not already exist
- the incoming user message
- the assistant response
- structured metadata needed to inspect retrieval quality later

Minimum chat persistence fields:

- session: `id`, `channel`, `user_id`, `title`, `created_at`, `updated_at`
- message: `id`, `session_id`, `role`, `content`, `intent`, `confidence`, `citations_json`, `metadata_json`, `created_at`

`metadata_json` for assistant chat messages should be able to hold:

- `request_id`
- `provider`
- `top_k`
- `scholar`
- `elapsed_ms`
- `chunks`
- `disclaimer_applied`
- `fiqh_note_applied`

## Test Run Persistence Contract

Saved `test_poc` executions should produce:

- one `test_runs` row per invocation
- one `test_run_cases` row per test case

Minimum test run fields:

- run: `id`, `suite_name`, `provider`, `status`, `total_cases`, `passed_cases`, `failed_cases`, `metadata_json`, `created_at`
- case: `id`, `run_id`, `query`, `expected`, `actual_intent`, `status`, `reason`, `response_text`, `metadata_json`, `created_at`

`metadata_json` for a test case should be able to hold:

- `citations`
- `confidence`
- `chunks`
- `note`
- `timing`

## API Endpoints

The local HTTP API should expose at least:

- `GET /health`
- `POST /api/webhook`
- `GET /api/sessions`
- `GET /api/sessions/{session_id}`
- `GET /api/test-runs`
- `GET /api/test-runs/{run_id}`

Optional but useful:

- `POST /api/test-runs`

This endpoint can trigger a local `test_poc` execution and persist the result, but that is secondary to being able to save and read test outputs.

## Integration Boundaries

### Agent branch: API (`#9`)

Responsible for:

- extracting reusable pipeline functions from `scripts/rag_poc.py`
- defining request/response models
- exposing HTTP endpoints
- preserving current CLI behavior

Should not own:

- Postgres schema design
- UI implementation

### Agent branch: Persistence (`#10`)

Responsible for:

- Postgres bootstrap or migrations
- repository/storage layer
- documenting container/env requirements

Should not own:

- HTTP routing decisions
- frontend implementation

### Integration branch

Responsible for:

- wiring API handlers to persistence
- finalizing saved chat/test flows
- building the local web UI against the stabilized contract

## Frontend Recommendation

The preferred frontend for the local web PoC is React with Vite.

Reasons:

- closer to the intended long-term web channel shape than server-rendered templates
- clean separation between browser client and webhook-like backend
- easier to swap the local API base URL for an n8n webhook later
- better fit for chat state, transcript browsing, and saved test-run views

The frontend should initially remain simple:

- chat transcript panel
- message composer
- retrieval/debug side panel
- saved sessions view
- saved test runs view

## Known Risks

- the current Postgres container may fail locally if `POSTGRES_USER` and `POSTGRES_PASSWORD` are not set
- request/response churn between branches will create merge pain if this contract is not followed
- `test_poc.py` currently prints CLI output; saving structured test runs may require factoring its result model before UI work begins
