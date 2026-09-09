from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import DictRow, dict_row
from psycopg.types.json import Json

from tafsirbot.errors import PersistenceError

from .config import PostgresConfig
from .migrations import MigrationRunner
from .models import ChatMessageRecord, ChatSessionRecord, TestRunCaseRecord, TestRunRecord


def _coerce_uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


def _maybe_uuid(value: UUID | str) -> UUID | None:
    try:
        return _coerce_uuid(value)
    except (TypeError, ValueError, AttributeError):
        return None


def _require_row(row: DictRow | None, what: str) -> DictRow:
    """Assert a RETURNING clause actually produced a row.

    Without this, ``Record(**cur.fetchone())`` raises
    ``TypeError: argument after ** must be a mapping, not NoneType`` — which says
    nothing about what failed. A plain ``INSERT ... RETURNING`` always yields a row,
    but ``ON CONFLICT DO NOTHING ... RETURNING`` does not, so this guards a change
    that is easy to make and hard to debug.
    """
    if row is None:
        raise PersistenceError(f"{what} returned no row — the write did not take effect")
    return row


class PostgresPersistence:
    def __init__(self, config: PostgresConfig) -> None:
        self.config = config

    @classmethod
    def from_env(cls) -> PostgresPersistence:
        return cls(PostgresConfig.from_env())

    def apply_migrations(self) -> list[str]:
        return MigrationRunner(self.config).apply()

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection[DictRow]]:
        """Yield a connection whose cursors return dicts, not tuples.

        The ``DictRow`` parameter is load-bearing: every query here does
        ``Record(**row)``, which requires a mapping. Annotating this as a bare
        ``psycopg.Connection`` silently types rows as tuples and hides that.
        """
        with psycopg.connect(self.config.conninfo(), row_factory=dict_row) as conn:
            yield conn

    def list_chat_sessions(self, *, limit: int = 20) -> list[ChatSessionRecord]:
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, client_session_id, channel, user_id, title, created_at, updated_at
                FROM chat_sessions
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [ChatSessionRecord(**row) for row in rows]

    def get_chat_session(self, *, session_id: UUID | str) -> ChatSessionRecord | None:
        with self.connection() as conn, conn.cursor() as cur:
            session_uuid = _maybe_uuid(session_id)
            if session_uuid is not None:
                cur.execute(
                    """
                    SELECT id, client_session_id, channel, user_id, title, created_at, updated_at
                    FROM chat_sessions
                    WHERE id = %s OR client_session_id = %s
                    """,
                    (session_uuid, str(session_id)),
                )
            else:
                cur.execute(
                    """
                    SELECT id, client_session_id, channel, user_id, title, created_at, updated_at
                    FROM chat_sessions
                    WHERE client_session_id = %s
                    """,
                    (str(session_id),),
                )
            row = cur.fetchone()
        return ChatSessionRecord(**row) if row else None

    def ensure_chat_session(
        self,
        *,
        session_id: UUID | str | None = None,
        channel: str,
        user_id: str,
        title: str | None = None,
    ) -> ChatSessionRecord:
        with self.connection() as conn, conn.cursor() as cur:
            if session_id is None:
                cur.execute(
                    """
                    INSERT INTO chat_sessions (channel, user_id, title)
                    VALUES (%s, %s, %s)
                    RETURNING id, client_session_id, channel, user_id, title, created_at, updated_at
                    """,
                    (channel, user_id, title),
                )
            else:
                session_uuid = _maybe_uuid(session_id)
                session_token = str(session_id)
                if session_uuid is not None:
                    cur.execute(
                        """
                        INSERT INTO chat_sessions (id, client_session_id, channel, user_id, title)
                        VALUES (%s, %s, %s, %s, COALESCE(%s, %s))
                        ON CONFLICT (id) DO UPDATE
                        SET client_session_id = COALESCE(EXCLUDED.client_session_id, chat_sessions.client_session_id),
                            channel = EXCLUDED.channel,
                            user_id = EXCLUDED.user_id,
                            title = COALESCE(EXCLUDED.title, chat_sessions.title),
                            updated_at = NOW()
                        RETURNING id, client_session_id, channel, user_id, title, created_at, updated_at
                        """,
                        (session_uuid, session_token, channel, user_id, title, title or "Untitled session"),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO chat_sessions (client_session_id, channel, user_id, title)
                        VALUES (%s, %s, %s, COALESCE(%s, %s))
                        ON CONFLICT (client_session_id) DO UPDATE
                        SET channel = EXCLUDED.channel,
                            user_id = EXCLUDED.user_id,
                            title = COALESCE(EXCLUDED.title, chat_sessions.title),
                            updated_at = NOW()
                        RETURNING id, client_session_id, channel, user_id, title, created_at, updated_at
                        """,
                        (session_token, channel, user_id, title, title or "Untitled session"),
                    )
            row = cur.fetchone()
            conn.commit()
        return ChatSessionRecord(**_require_row(row, "ensure_chat_session"))

    def add_chat_message(
        self,
        *,
        session_id: UUID | str,
        role: str,
        content: str,
        intent: str | None = None,
        confidence: str | None = None,
        citations: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChatMessageRecord:
        session_uuid = _coerce_uuid(session_id)
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_messages (
                    session_id,
                    role,
                    content,
                    intent,
                    confidence,
                    citations_json,
                    metadata_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING
                    id,
                    session_id,
                    role,
                    content,
                    intent,
                    confidence,
                    citations_json,
                    metadata_json,
                    created_at
                """,
                (
                    session_uuid,
                    role,
                    content,
                    intent,
                    confidence,
                    Json(citations or []),
                    Json(metadata or {}),
                ),
            )
            row = cur.fetchone()
            cur.execute(
                "UPDATE chat_sessions SET updated_at = NOW() WHERE id = %s",
                (session_uuid,),
            )
            conn.commit()
        return ChatMessageRecord(**_require_row(row, "add_chat_message"))

    def list_chat_messages(
        self,
        *,
        session_id: UUID | str,
        limit: int = 50,
    ) -> list[ChatMessageRecord]:
        session = self.get_chat_session(session_id=session_id)
        if session is None:
            return []
        session_uuid = session.id
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    session_id,
                    role,
                    content,
                    intent,
                    confidence,
                    citations_json,
                    metadata_json,
                    created_at
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (session_uuid, limit),
            )
            rows = cur.fetchall()
        return [ChatMessageRecord(**row) for row in rows]

    def create_test_run(
        self,
        *,
        suite_name: str,
        provider: str,
        total_cases: int,
        metadata: dict[str, Any] | None = None,
        status: str = "running",
    ) -> TestRunRecord:
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO test_runs (
                    suite_name,
                    provider,
                    status,
                    total_cases,
                    passed_cases,
                    failed_cases,
                    metadata_json
                )
                VALUES (%s, %s, %s, %s, 0, 0, %s)
                RETURNING
                    id,
                    suite_name,
                    provider,
                    status,
                    total_cases,
                    passed_cases,
                    failed_cases,
                    metadata_json,
                    created_at
                """,
                (suite_name, provider, status, total_cases, Json(metadata or {})),
            )
            row = cur.fetchone()
            conn.commit()
        return TestRunRecord(**_require_row(row, "create_test_run / complete_test_run"))

    def list_test_runs(self, *, limit: int = 20) -> list[TestRunRecord]:
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    suite_name,
                    provider,
                    status,
                    total_cases,
                    passed_cases,
                    failed_cases,
                    metadata_json,
                    created_at
                FROM test_runs
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [TestRunRecord(**row) for row in rows]

    def get_test_run(self, *, run_id: UUID | str) -> TestRunRecord | None:
        run_uuid = _coerce_uuid(run_id)
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    suite_name,
                    provider,
                    status,
                    total_cases,
                    passed_cases,
                    failed_cases,
                    metadata_json,
                    created_at
                FROM test_runs
                WHERE id = %s
                """,
                (run_uuid,),
            )
            row = cur.fetchone()
        return TestRunRecord(**row) if row else None

    def complete_test_run(
        self,
        *,
        run_id: UUID | str,
        status: str,
        passed_cases: int,
        failed_cases: int,
        metadata: dict[str, Any] | None = None,
    ) -> TestRunRecord:
        run_uuid = _coerce_uuid(run_id)
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE test_runs
                SET status = %s,
                    passed_cases = %s,
                    failed_cases = %s,
                    metadata_json = metadata_json || %s::jsonb
                WHERE id = %s
                RETURNING
                    id,
                    suite_name,
                    provider,
                    status,
                    total_cases,
                    passed_cases,
                    failed_cases,
                    metadata_json,
                    created_at
                """,
                (status, passed_cases, failed_cases, Json(metadata or {}), run_uuid),
            )
            row = cur.fetchone()
            conn.commit()
        return TestRunRecord(**_require_row(row, "create_test_run / complete_test_run"))

    def add_test_run_case(
        self,
        *,
        run_id: UUID | str,
        query: str,
        expected: str,
        actual_intent: str | None,
        status: str,
        reason: str | None = None,
        response_text: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TestRunCaseRecord:
        run_uuid = _coerce_uuid(run_id)
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO test_run_cases (
                    run_id,
                    query,
                    expected,
                    actual_intent,
                    status,
                    reason,
                    response_text,
                    metadata_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING
                    id,
                    run_id,
                    query,
                    expected,
                    actual_intent,
                    status,
                    reason,
                    response_text,
                    metadata_json,
                    created_at
                """,
                (
                    run_uuid,
                    query,
                    expected,
                    actual_intent,
                    status,
                    reason,
                    response_text,
                    Json(metadata or {}),
                ),
            )
            row = cur.fetchone()
            conn.commit()
        return TestRunCaseRecord(**_require_row(row, "add_test_run_case"))

    def list_test_run_cases(
        self,
        *,
        run_id: UUID | str,
        limit: int = 200,
    ) -> list[TestRunCaseRecord]:
        run_uuid = _coerce_uuid(run_id)
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    run_id,
                    query,
                    expected,
                    actual_intent,
                    status,
                    reason,
                    response_text,
                    metadata_json,
                    created_at
                FROM test_run_cases
                WHERE run_id = %s
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (run_uuid, limit),
            )
            rows = cur.fetchall()
        return [TestRunCaseRecord(**row) for row in rows]
