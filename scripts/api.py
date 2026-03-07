"""
api.py — Thin webhook-compatible HTTP API for TafsirBot.

Wraps the rag_poc pipeline in a FastAPI app.  All expensive resources
(LLM clients, sparse embedding model, Qdrant connection, AyahResolver)
are initialised once at startup via rag_poc.build_runtime() and reused
across requests.

Run:
    uv run uvicorn scripts.api:app --host 0.0.0.0 --port 8000
    uv run uvicorn scripts.api:app --host 0.0.0.0 --port 8000 --reload  # dev

From inside the scripts/ directory:
    cd scripts && uv run uvicorn api:app --port 8000

See docs/WEBHOOK-API.md for endpoint documentation and curl examples.
"""

from __future__ import annotations

import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

# Allow imports from scripts/ingestion/utils/ and from rag_poc (same directory)
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "ingestion"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import rag_poc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("tafsirbot.api")


# ── Pydantic request / response models ────────────────────────────────────────


class QueryOptions(BaseModel):
    provider: Literal["anthropic", "openai"] = Field(
        default_factory=lambda: os.environ.get("LLM_PROVIDER", "anthropic")
    )
    scholar: str | None = None
    top_k: int = Field(default=rag_poc.TOP_K, ge=1, le=20)
    save: bool = True


class ConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class QueryRequest(BaseModel):
    channel: str = "web"
    session_id: str = "local-session"
    user_id: str = "local-user"
    message: str
    conversation_history: list[ConversationTurn] = Field(default_factory=list)
    options: QueryOptions = Field(default_factory=QueryOptions)


class ChunkSummary(BaseModel):
    scholar: str
    surah_number: int | None
    ayah_start: int | None
    ayah_end: int | None
    source_title: str
    score: float
    content_preview: str  # first 200 chars of chunk content


class QueryResponse(BaseModel):
    request_id: str
    session_id: str
    intent: str
    normalized_message: str
    answer: str
    citations: list[str]
    confidence: str
    disclaimer_applied: bool
    fiqh_note_applied: bool
    chunks: list[ChunkSummary]
    meta: dict


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"
    providers: list[str]
    persistence: bool


class ChatSessionSummary(BaseModel):
    id: str
    channel: str
    user_id: str
    title: str | None
    created_at: str
    updated_at: str


class ChatMessageItem(BaseModel):
    id: str
    role: str
    content: str
    intent: str | None
    confidence: str | None
    citations: list[str]
    metadata: dict
    created_at: str


class ChatSessionDetail(BaseModel):
    session: ChatSessionSummary
    messages: list[ChatMessageItem]


class TestRunSummary(BaseModel):
    id: str
    suite_name: str
    provider: str
    status: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    metadata: dict
    created_at: str


class TestRunCaseItem(BaseModel):
    id: str
    query: str
    expected: str
    actual_intent: str | None
    status: str
    reason: str | None
    response_text: str | None
    metadata: dict
    created_at: str


class TestRunDetail(BaseModel):
    run: TestRunSummary
    cases: list[TestRunCaseItem]


# ── App lifespan (startup / shutdown) ────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initialising TafsirBot runtime…")
    runtime = rag_poc.build_runtime()
    app.state.runtime = runtime
    app.state.persistence = None
    try:
        from persistence import PostgresPersistence

        persistence = PostgresPersistence.from_env()
        persistence.apply_migrations()
        app.state.persistence = persistence
        logger.info("Persistence ready.")
    except Exception as exc:
        logger.warning("Persistence unavailable: %s", exc)
    logger.info("Runtime ready — providers: %s", list(runtime["clients"].keys()))
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="TafsirBot Webhook API",
    description=(
        "Webhook-compatible HTTP API wrapping the TafsirBot RAG pipeline. "
        "Accepts queries in a channel-agnostic envelope and returns structured JSON "
        "including the generated answer, citations, retrieved chunks, and metadata."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse, tags=["ops"])
def health() -> HealthResponse:
    """Liveness check. Returns available LLM providers."""
    runtime = app.state.runtime
    return HealthResponse(
        status="ok",
        providers=list(runtime["clients"].keys()),
        persistence=app.state.persistence is not None,
    )


def _require_persistence():
    persistence = app.state.persistence
    if persistence is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Persistence is not configured or migrations have not been applied. "
                "Check Postgres settings and run scripts/persistence/migrate.py."
            ),
        )
    return persistence


def _save_chat_exchange(
    req: QueryRequest,
    response: QueryResponse,
) -> None:
    persistence = _require_persistence()
    session = persistence.ensure_chat_session(
        session_id=req.session_id,
        channel=req.channel,
        user_id=req.user_id,
        title=req.message[:80],
    )
    persistence.add_chat_message(
        session_id=session.id,
        role="user",
        content=response.normalized_message,
        metadata={
            "provider": req.options.provider,
            "scholar_filter": req.options.scholar,
            "top_k": req.options.top_k,
        },
    )
    persistence.add_chat_message(
        session_id=session.id,
        role="assistant",
        content=response.answer,
        intent=response.intent,
        confidence=response.confidence,
        citations=response.citations,
        metadata={
            "request_id": response.request_id,
            **response.meta,
            "chunks": [chunk.model_dump() for chunk in response.chunks],
            "disclaimer_applied": response.disclaimer_applied,
            "fiqh_note_applied": response.fiqh_note_applied,
        },
    )


def _build_query_response(req: QueryRequest) -> QueryResponse:
    """
    Run the full RAG pipeline for a single user message.

    - `off_topic` intent: returns a polite refusal with no retrieval.
    - `fiqh_ruling` intent: retrieves and responds with scholarly context;
      prepends a note that the response is not a personal fatwa.
    - All other intents: normal retrieval + generation + disclaimer.
    """
    runtime = app.state.runtime
    provider = req.options.provider

    if provider not in runtime["clients"]:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Provider {provider!r} is not configured — "
                "add the corresponding API key to .env."
            ),
        )

    conversation_history = [t.model_dump() for t in req.conversation_history] or None

    t0 = time.monotonic()
    try:
        result: rag_poc.PipelineResult = rag_poc.run_pipeline(
            req.message,
            provider=provider,
            scholar=req.options.scholar,
            top_k=req.options.top_k,
            conversation_history=conversation_history,
            clients=runtime["clients"],
            qdrant_client=runtime["qdrant_client"],
            collection=runtime["collection"],
            resolver=runtime["resolver"],
            sparse_model=runtime["sparse_model"],
        )
    except Exception as exc:
        # Surface API provider errors (billing, auth, quota) as 502 so callers
        # get a structured error instead of a plain-text 500 page.
        msg = str(exc)
        status = 502
        # Detect common upstream error patterns
        if any(k in msg for k in ("credit balance", "insufficient", "quota", "rate limit")):
            status = 429
        elif any(k in msg for k in ("authentication", "api key", "unauthorized")):
            status = 401
        logger.error("Pipeline error (%s %s): %s", provider, req.message[:60], msg)
        raise HTTPException(status_code=status, detail=msg) from exc
    elapsed_ms = round((time.monotonic() - t0) * 1000)

    chunk_summaries = [
        ChunkSummary(
            scholar=c["scholar"],
            surah_number=c.get("surah_number"),
            ayah_start=c.get("ayah_start"),
            ayah_end=c.get("ayah_end"),
            source_title=c.get("source_title", ""),
            score=round(c["score"], 4),
            content_preview=c["content"][:200],
        )
        for c in result.chunks
    ]

    response = QueryResponse(
        request_id=str(uuid.uuid4()),
        session_id=req.session_id,
        intent=result.intent,
        normalized_message=result.normalized_message,
        answer=result.answer,
        citations=result.citations,
        confidence=result.confidence,
        disclaimer_applied=result.disclaimer_applied,
        fiqh_note_applied=result.fiqh_note_applied,
        chunks=chunk_summaries,
        meta={
            "channel": req.channel,
            "user_id": req.user_id,
            "provider": provider,
            "top_k": req.options.top_k,
            "scholar_filter": req.options.scholar,
            "elapsed_ms": elapsed_ms,
        },
    )
    if req.options.save:
        _save_chat_exchange(req, response)
    return response


@app.post("/query", response_model=QueryResponse, tags=["rag"])
@app.post("/api/webhook", response_model=QueryResponse, tags=["rag"])
def query(req: QueryRequest) -> QueryResponse:
    return _build_query_response(req)


def _session_summary(record) -> ChatSessionSummary:
    return ChatSessionSummary(
        id=str(record.id),
        channel=record.channel,
        user_id=record.user_id,
        title=record.title,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
    )


def _message_item(record) -> ChatMessageItem:
    return ChatMessageItem(
        id=str(record.id),
        role=record.role,
        content=record.content,
        intent=record.intent,
        confidence=record.confidence,
        citations=record.citations_json,
        metadata=record.metadata_json,
        created_at=record.created_at.isoformat(),
    )


def _test_run_summary(record) -> TestRunSummary:
    return TestRunSummary(
        id=str(record.id),
        suite_name=record.suite_name,
        provider=record.provider,
        status=record.status,
        total_cases=record.total_cases,
        passed_cases=record.passed_cases,
        failed_cases=record.failed_cases,
        metadata=record.metadata_json,
        created_at=record.created_at.isoformat(),
    )


def _test_run_case_item(record) -> TestRunCaseItem:
    return TestRunCaseItem(
        id=str(record.id),
        query=record.query,
        expected=record.expected,
        actual_intent=record.actual_intent,
        status=record.status,
        reason=record.reason,
        response_text=record.response_text,
        metadata=record.metadata_json,
        created_at=record.created_at.isoformat(),
    )


@app.get("/api/sessions", response_model=list[ChatSessionSummary], tags=["persistence"])
def list_sessions(limit: int = 20) -> list[ChatSessionSummary]:
    persistence = _require_persistence()
    return [_session_summary(row) for row in persistence.list_chat_sessions(limit=limit)]


@app.get("/api/sessions/{session_id}", response_model=ChatSessionDetail, tags=["persistence"])
def get_session(session_id: str) -> ChatSessionDetail:
    persistence = _require_persistence()
    session = persistence.get_chat_session(session_id=session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    messages = persistence.list_chat_messages(session_id=session_id)
    return ChatSessionDetail(
        session=_session_summary(session),
        messages=[_message_item(row) for row in messages],
    )


@app.get("/api/test-runs", response_model=list[TestRunSummary], tags=["persistence"])
def list_test_runs(limit: int = 20) -> list[TestRunSummary]:
    persistence = _require_persistence()
    return [_test_run_summary(row) for row in persistence.list_test_runs(limit=limit)]


@app.get("/api/test-runs/{run_id}", response_model=TestRunDetail, tags=["persistence"])
def get_test_run(run_id: str) -> TestRunDetail:
    persistence = _require_persistence()
    run = persistence.get_test_run(run_id=run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Test run not found.")
    cases = persistence.list_test_run_cases(run_id=run_id)
    return TestRunDetail(
        run=_test_run_summary(run),
        cases=[_test_run_case_item(row) for row in cases],
    )
