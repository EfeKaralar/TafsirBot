from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from .models import ChatMessageRecord, ChatSessionRecord, TestRunCaseRecord, TestRunRecord


class ChatStore(Protocol):
    def list_chat_sessions(self, *, limit: int = 20) -> list[ChatSessionRecord]: ...

    def get_chat_session(self, *, session_id: UUID | str) -> ChatSessionRecord | None: ...

    def ensure_chat_session(
        self,
        *,
        session_id: UUID | str | None = None,
        channel: str,
        user_id: str,
        title: str | None = None,
    ) -> ChatSessionRecord: ...

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
    ) -> ChatMessageRecord: ...

    def list_chat_messages(
        self,
        *,
        session_id: UUID | str,
        limit: int = 50,
    ) -> list[ChatMessageRecord]: ...


class TestRunStore(Protocol):
    def list_test_runs(self, *, limit: int = 20) -> list[TestRunRecord]: ...

    def get_test_run(self, *, run_id: UUID | str) -> TestRunRecord | None: ...

    def list_test_run_cases(
        self,
        *,
        run_id: UUID | str,
        limit: int = 200,
    ) -> list[TestRunCaseRecord]: ...

    def create_test_run(
        self,
        *,
        suite_name: str,
        provider: str,
        total_cases: int,
        metadata: dict[str, Any] | None = None,
        status: str = "running",
    ) -> TestRunRecord: ...

    def complete_test_run(
        self,
        *,
        run_id: UUID | str,
        status: str,
        passed_cases: int,
        failed_cases: int,
        metadata: dict[str, Any] | None = None,
    ) -> TestRunRecord: ...

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
    ) -> TestRunCaseRecord: ...
