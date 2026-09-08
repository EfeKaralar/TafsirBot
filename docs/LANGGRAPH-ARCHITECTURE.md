# LangGraph Architecture — Frozen Contract

> **Status:** Authoritative as of 2026-09-08. This document supersedes all n8n orchestration
> descriptions in `CLAUDE.md`, `AGENTS.md`, `sources/README.md`, and `docs/PHASE-1-PLAN.md`.
>
> **Purpose:** parallel worktrees code against this contract. If an implementation PR needs to
> diverge from it, change this document in that PR and say so in the PR description — do not
> let the code and the contract drift.
>
> Tracking epic: [#38](https://github.com/EfeKaralar/TafsirBot/issues/38).

---

## 1. Orchestration decision

**LangGraph replaces n8n.** The RAG core is a Python `StateGraph` compiled once at process start.
Channels (web, Telegram, WhatsApp, X) are thin adapters that call one FastAPI surface; they hold
no pipeline logic.

Why the change: the pipeline needs query decomposition, an adaptive retrieval loop, and citation
verification. Expressing conditional loops and parallel fan-out in n8n nodes would have meant
maintaining a second, divergent implementation of logic that already exists in Python — and the
n8n copy could not be unit-tested.

What this does **not** change: the HTTP contract. `POST /api/webhook` and `POST /query` keep their
exact request and response shapes (see `docs/WEBHOOK-API.md`), so channel adapters are unaffected.

---

## 2. Version pins

Pin these **exactly**, not as ranges. LangGraph crossed 1.0 recently and the 0.x→1.x transition
renamed `config_schema`→`context_schema` and changed how runtime config reaches nodes.

| Package | Pin | Note |
|---|---|---|
| `langgraph` | 1.2.x | |
| `langchain-core` | 1.6.x | already a transitive dep of `langgraph` |
| `langchain` | 1.x | `from langchain.chat_models import init_chat_model` |
| `langgraph-checkpoint-postgres` | 3.1.x | needs `psycopg>=3.2` + `psycopg-pool` |
| `langchain-anthropic` | 1.7.x | |
| `langchain-openai` | 1.6.x | |
| `sse-starlette` | latest | correct SSE pings + disconnect handling |
| `psycopg` | `[binary,pool]>=3.2` | bumped from `[binary]` |

**Python stays pinned to 3.12.** `fastembed`→`onnxruntime` is the only constraint; every package
above supports ≥3.10. `requires-python` is tightened to `>=3.12,<3.13` so `uv sync` fails fast.

### Import seams (CI-enforced)

- `langgraph` may be imported **only** from `graph/` and `persistence/checkpointer.py`
- `langchain_anthropic` / `langchain_openai` may be imported **only** from `llm/factory.py`

A grep in CI enforces both. If we ever need to leave LangChain, we replace one file.

---

## 3. Package tree

```
src/tafsirbot/
  settings.py              # pydantic-settings Settings — the ONE env surface
  logging_config.py        # configure_logging(); called by entrypoints ONLY
  errors.py                # TafsirBotError > ConfigError | RetrievalError | ProviderError | PersistenceError

  corpus/
    registry.yaml          # canonical scholar + hadith source data
    registry.py            # Source dataclass, load_registry(), display_name()
    quran.py               # QuranRef
    refs.py                # AyahRef, AyahResolver
    cleaning.py            # was ingestion/clean.py
    chunking.py            # was ingestion/chunk.py — renamed, see §9
    embedding.py           # was ingestion/embed.py (offline batch)
    indexing.py            # was ingestion/upsert.py — owns VECTOR_SIZE
    audit.py               # retrieval-quality report; calls HybridRetriever

  retrieval/
    models.py              # Chunk, SubQuery, RetrievalTask, RetrievalEvent
    client.py              # (async) Qdrant client factories
    sparse.py              # SparseEncoder — fastembed behind a 1-worker executor
    dense.py               # DenseEmbedder protocol + OpenAI impl
    filters.py             # build_scholar_filter / build_ayah_filter / build_hadith_filter
    hybrid.py              # hybrid_search() — the ONE dense+sparse→RRF implementation
    fusion.py              # rank_fuse() across independent retrieval calls

  llm/
    factory.py             # get_model(role, provider) / get_structured(role, provider, schema)
    prompts.py             # all prompt constants + DISCLAIMER / FIQH_NOTE / OFF_TOPIC_REFUSAL
    schemas.py             # IntentDecision, QueryPlan, GradeReport, CitationReport

  graph/
    state.py               # TafsirState / InputState / OutputState + reducers
    context.py             # RuntimeConfig (the context_schema)
    builder.py             # build_graph(models, retriever, store) -> StateGraph
    routing.py             # conditional-edge predicates
    runner.py              # to_query_response(state) — THE state→response mapper
    nodes/                 # one module per node

  persistence/
    config.py models.py interfaces.py migrations.py postgres.py
    postgres_async.py      # async twin for the API path
    checkpointer.py        # AsyncPostgresSaver lifecycle
    readmodel.py           # ChatReadModel.record_turn()

  api/
    app.py context.py schemas.py sse.py errors.py
    routes/{health,query,stream,sessions,test_runs,sources,review}.py

  channels/
    base.py                # ChannelAdapter protocol
    web.py telegram.py

  cli/
    __main__.py ask.py evals.py ingest.py migrate.py
```

`scripts/` is deleted; entry points are console scripts (`tafsirbot ask|eval|ingest|migrate`).

---

## 4. LangGraph 1.x API

Verified against current docs. **This is the most likely source of upgrade breakage.**

```python
StateGraph(
    TafsirState,
    input_schema=InputState,      # not `input=`
    output_schema=OutputState,    # not `output=`
    context_schema=RuntimeConfig, # not `config_schema=`
)
```

Nodes take `(state, runtime: Runtime[RuntimeConfig])` and read **`runtime.context`** — *not*
`config["configurable"]`.

Per-request knobs live on `RuntimeConfig`, **not** in state:

```python
@dataclass
class RuntimeConfig:
    provider: Provider = "anthropic"
    scholars: list[str] | None = None
    hadith_enabled: bool = False
    hadith_collections: list[str] | None = None
    top_k: int = 5
    decompose: bool = True
    max_retrieval_attempts: int = 2
    max_verification_attempts: int = 1
    relevance_threshold: float = 0.5
    enable_review: bool = False
    channel: str = "web"
    user_id: str = "local-user"
```

Invoked as:

```python
await graph.ainvoke(
    input_state,
    config={"configurable": {"thread_id": tid}, "recursion_limit": 40},
    context=RuntimeConfig(...),
)
```

Only `thread_id` and `recursion_limit` belong in `config`.

---

## 5. State schema

```python
class Chunk(TypedDict):
    chunk_id: str        # f"{collection}:{point_id}" — the fusion + verification key
    collection: str      # "tafsir" | "hadith"
    source_id: str       # scholar id, or hadith collection id
    surah_number: int | None
    ayah_start: int | None
    ayah_end: int | None
    preview: str         # first 400 chars — full text NEVER enters state, see §8
    source_title: str
    english_text: str
    score: float         # raw per-call RRF — NOT comparable across calls
    rank: int            # 1-based within its own retrieval call
    query_id: str        # which sub-query produced it
    fused_score: float | None
    grade: bool | None

class TafsirState(TypedDict, total=False):
    turn_id: str                 # minted in `normalize`; the read-model idempotency key
    messages: Annotated[list[AnyMessage], add_messages]
    question: str
    normalized_question: str
    intent: Intent
    standalone_question: str
    sub_queries: list[SubQuery]
    retrieval_tasks: list[RetrievalTask]

    candidates: Annotated[list[Chunk], merge_chunks]
    retrieval_events: Annotated[list[RetrievalEvent], operator.add]
    chunks: list[Chunk]
    relevance_ratio: float
    retrieval_attempts: int      # NO reducer
    relaxation: Relaxation

    draft_answer: str
    citations: list[str]
    citation_report: dict
    verification_attempts: int   # NO reducer

    answer: str
    confidence: Confidence       # "high" | "medium" | "low"
    disclaimer_applied: bool
    fiqh_note_applied: bool
    review_required: bool
    errors: Annotated[list[str], operator.add]
```

### Reducers — and where one would be a bug

| Field | Reducer | Why |
|---|---|---|
| `candidates` | `merge_chunks` | **Mandatory.** Parallel `Send`-dispatched `retrieve` nodes write it concurrently; without a reducer LangGraph raises `InvalidUpdateError: Can receive only one value per step`. |
| `retrieval_events` | `operator.add` | Carries each call's *ordered* chunk-id list, which `fuse` needs and which `merge_chunks`' dedupe destroys. |
| `errors` | `operator.add` | Any node may append. |
| `messages` | `add_messages` | Standard. |
| `retrieval_attempts` | **none** | Last-write-wins from a single node. With `add`, parallel branches double-increment and the loop bound silently halves. |
| `verification_attempts` | **none** | Same. |

```python
RESET = object()   # sentinel: clear candidates between grading rounds

def merge_chunks(left, right):
    """Fan-in for parallel sub-query retrieval. Dedupe on chunk_id, keep best rank."""
    if right is RESET:
        return []
    by_id = {c["chunk_id"]: c for c in left}
    for c in right:
        prev = by_id.get(c["chunk_id"])
        if prev is None or c["rank"] < prev["rank"]:
            by_id[c["chunk_id"]] = c
    return list(by_id.values())
```

Plain `operator.add` is **not** sufficient for `candidates`: it duplicates chunks found by multiple
sub-queries and offers no way to clear state between grading rounds. `broaden` returns
`{"candidates": RESET}`.

> **The trap:** a missing `candidates` reducer fails *only* when decomposition yields more than one
> sub-query. It passes every single-question test and breaks in production. The 3-sub-query test in
> #32 is mandatory for this reason.

---

## 6. Graph topology

```
START ─> normalize ─> classify
classify ─[route_intent]─> off_topic ? refuse : plan_query
refuse ─> persist ─> END
plan_query ─> plan_retrieval
plan_retrieval ─[fan_out]─> Send("retrieve") x N   |  "no_chunks" if N == 0
retrieve ─> fuse                                    (implicit join)
fuse ─[has_chunks]─> grade | no_chunks
grade ─[route_after_grade]─> generate | broaden | no_chunks
broaden ─> plan_retrieval                           (the loop)
generate ─> verify
verify ─[route_after_verify]─> finalize | generate  (the retry)
finalize ─[needs_review]─> human_review | persist
human_review ─[on resume]─> persist | generate | END
persist ─> END
no_chunks ─> persist ─> END
```

| Node | Model role | Returns |
|---|---|---|
| `normalize` | — | `normalized_question`, `turn_id`, `messages` |
| `classify` | fast | `intent` |
| `refuse` | — | `answer=OFF_TOPIC_REFUSAL`, `confidence="high"` |
| `plan_query` | fast | `standalone_question`, `sub_queries` |
| `plan_retrieval` | — | `retrieval_tasks` (sub-queries × collections, with relaxation applied) |
| `retrieve` | — | `candidates`, `retrieval_events` — **fan-out target** |
| `fuse` | — | `chunks` (rank-fused, truncated) |
| `grade` | fast | `chunks` (filtered), `relevance_ratio`, `retrieval_attempts + 1` |
| `broaden` | — | `relaxation` (next rung), `candidates: RESET` |
| `generate` | **primary** | `draft_answer` — the only streaming node |
| `verify` | fast + deterministic | `citation_report`, `verification_attempts + 1` |
| `finalize` | — | `answer`, `confidence`, `*_applied`, `review_required` |
| `human_review` | — | `interrupt(...)` |
| `persist` | — | side effect only; best-effort, never raises |
| `no_chunks` | — | "No relevant Tafsir passages found…" + disclaimer |

### Routing predicates

```python
def route_intent(state):
    return "refuse" if state["intent"] == "off_topic" else "plan_query"

def fan_out(state):
    tasks = state["retrieval_tasks"]
    if not tasks:
        return "no_chunks"
    return [Send("retrieve", {"task": t}) for t in tasks]

def route_after_grade(state, runtime):
    if state["relevance_ratio"] >= runtime.context.relevance_threshold:
        return "generate"
    if state["retrieval_attempts"] >= runtime.context.max_retrieval_attempts:
        return "generate" if state["chunks"] else "no_chunks"   # degrade, never spin
    return "broaden"

def route_after_verify(state, runtime):
    if (not state["citation_report"]["any_grounded"]
            and state["verification_attempts"] <= runtime.context.max_verification_attempts):
        return "generate"
    return "finalize"

def needs_review(state):
    return "human_review" if state["review_required"] else "persist"
```

**Loop bounds:** `max_retrieval_attempts=2`, `max_verification_attempts=1`, `recursion_limit=40`
as a hard backstop.

**Relaxation ladder** (`broaden`), applied in order — each rung is a pure function of the previous
value, so the loop is deterministic and snapshot-testable:
`widen_k` (top_k×3) → `drop_ayah` → `neighbour_ayat` (±3) → `drop_scholar`.

**Degrade open, not closed.** `route_after_grade` falls back to `generate` whenever `chunks` is
non-empty: a low-confidence answer beats "found nothing" after retrieval has already been paid for.
A grader *parse failure* treats all chunks as relevant and skips the loop — a broken grader must not
turn every request into three retrieval rounds. All degradations append to `errors` and surface in
`meta.errors`.

---

## 7. `Send` fan-out semantics

**`Send`, not a subgraph.** Fan-out width is runtime-determined (exactly `Send`'s purpose), and a
subgraph would get its own checkpoint namespace, inflating Postgres rows for no gain.

**Join:** all `Send`-ed `retrieve` invocations run in **one superstep**. `retrieve` has a single
static edge to `fuse`, so `fuse` runs exactly once in the next superstep with every write already
reduced. There is no explicit join node, and adding one is a mistake.

**Payload discipline:** `retrieve` gets its own input schema, and everything it needs travels in the
`Send` payload. With `Send` the payload *replaces* the state view — a node reading `state["top_k"]`
raises `KeyError` in production while passing every unit test that constructs a full state dict.
Cross-cutting config comes from `runtime.context`.

**Fusion.** Per-call RRF scores are **not comparable across calls**: with two prefetches and k=60
the top score is ≈0.0328 regardless of result quality, so comparing magnitudes across
`query_points` calls compares two arbitrary constants. Merge by rank instead:

```python
K = 60
score(chunk) = Σ over result lists of  weight[collection] / (K + rank_in_list)
```

Weights `{"tafsir": 1.0, "hadith": 0.6}` so hadith cannot crowd out tafsir by score luck. Ties break
on `chunk_id`, making output byte-deterministic — which is what makes the graph snapshot-testable.

Rejected alternative: per-source min-max normalization. The RRF range is tiny and near-constant, so
normalizing amplifies noise. Ranks are the honest signal.

---

## 8. Checkpointing and state size

`AsyncPostgresSaver` over an `AsyncConnectionPool`. `autocommit=True` and `prepare_threshold=0` are
**both required** by the saver.

**Schema ownership — do not get this wrong:**

1. **Never** hand-write checkpointer DDL into `db/migrations/*.sql`. The library's internal migration
   list changes between releases and will re-run against tables it did not create.
2. Startup order: `MigrationRunner.apply()` (app tables → `schema_migrations`) **then**
   `await saver.setup()` (`checkpoints*` → `checkpoint_migrations`). Both idempotent.
3. Gate both behind `TAFSIRBOT_RUN_MIGRATIONS` so N uvicorn workers do not race on DDL.

**`thread_id` is `chat_sessions.id`** (the UUID), not the client's raw `session_id` — clients send
arbitrary strings (`QueryRequest.session_id` defaults to the literal `"local-session"`), and the
existing `id`/`client_session_id` split already absorbs exactly that.

**`conversation_history` becomes advisory:** checkpointed `messages` win; a cold thread seeds from
the request. Existing clients keep working unchanged.

**Keep state small.** ~14 nodes plus fan-out means 20–40 checkpoint rows per turn. Chunk `preview`
is capped at 400 chars and **full chunk text never enters state** — it lives in a per-request cache
keyed by `chunk_id`. This is expensive to retrofit, so it is settled from the first graph PR.

---

## 9. Naming constraint

`corpus/chunking.py` is **not** named `chunk.py`. `chunk` is a real stdlib module (deprecated in
3.12, **removed in 3.13**), and the current `scripts/ingestion/chunk.py` shadows it — resolving only
via the `sys.path` hack. The rename is a prerequisite for ever unpinning Python.

---

## 10. Streaming

`graph.astream(..., stream_mode=["updates", "messages", "custom"])` — a list, so all three modes
multiplex from one iterator.

**Filter `messages` on `metadata["langgraph_node"] == "generate"`.** Mandatory: without it the
classifier's and grader's tokens stream to the user.

### SSE event vocabulary

| Event | Payload | Notes |
|---|---|---|
| `meta` | `{request_id, session_id, thread_id}` | first |
| `status` | `{node, state, ...}` | drives the progress rail |
| `chunks` | `{chunks: [ChunkSummary]}` | emitted from `fuse`, before generation |
| `token` | `{text}` | `generate` only |
| `reset` | `{reason}` | draft invalidated (verification retry) — client clears its buffer |
| `review` | `{thread_id, reason}` | **terminal**, no `final` follows |
| `final` | the complete `QueryResponse` | terminal |
| `error` | `{code, message}` | terminal; never contains upstream provider text |

**Contract preservation:** `final` carries the *exact* `QueryResponse` produced by
`graph/runner.py:to_query_response(state)` — the same mapper `POST /query` uses. The two paths
cannot drift. A test asserts `stream.final == query.body` for identical input.

**Streamed tokens are the draft.** `finalize` appends the Sources block and disclaimer afterwards,
and a verification retry replaces the draft entirely. Clients must treat streamed text as
provisional, clear on `reset`, and take `final.answer` as truth.

**Deployment:** SSE behind Nginx needs `proxy_buffering off; proxy_read_timeout 300s;`. CORS origins
come from `Settings`.

---

## 11. Model roles

| Role | anthropic | openai |
|---|---|---|
| `ANSWER` | `claude-sonnet-5` | `gpt-4o` |
| `CLASSIFY` / `REWRITE` / `GRADE` / `VERIFY` | `claude-haiku-4-5-20251001` | `gpt-4o-mini` |

All env-overridable via `settings.py`. Structured output uses
`.with_structured_output(Schema, include_raw=True)` — `include_raw` matters, so a parse failure
returns the raw message instead of raising inside a node.

**Degradation policy per node** (a correctness decision, not an implementation detail):

| Node | On parse failure |
|---|---|
| `classify` | default `"tafsir"` (matches current behaviour) |
| `plan_query` | single sub-query = `normalized_question`; never fail the request |
| `grade` | **degrade open** — all chunks relevant, `relevance_ratio=1.0`, skip the loop |
| `verify` | skip verification, drop `confidence` one notch; never regenerate on a parse error |

---

## 12. Guardrails (unchanged in substance, now enforced)

| Guardrail | Where |
|---|---|
| Standard disclaimer on every response | `finalize` |
| `fiqh_ruling` → scholarly context + note, never a personal ruling | `generate` prompt variant + `finalize` prepends `FIQH_NOTE` |
| `off_topic` → refusal, the only intent that short-circuits retrieval | `route_intent` → `refuse` (zero embedding, zero Qdrant calls) |
| Low-confidence on X held for human review | `finalize` sets `review_required`; `human_review` interrupts |
| Every published response cites ≥1 source | `verify` — **mechanically enforced for the first time** |

`confidence` becomes a real signal in #33. It is currently a constant `"high"` because
`post_process` is called with `threshold=0.0`, which makes the review guardrail unimplementable.
