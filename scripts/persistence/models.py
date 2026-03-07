from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class ChatSessionRecord:
    id: UUID
    channel: str
    user_id: str
    title: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ChatMessageRecord:
    id: UUID
    session_id: UUID
    role: str
    content: str
    intent: str | None
    confidence: str | None
    citations_json: list[str]
    metadata_json: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class TestRunRecord:
    id: UUID
    suite_name: str
    provider: str
    status: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    metadata_json: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class TestRunCaseRecord:
    id: UUID
    run_id: UUID
    query: str
    expected: str
    actual_intent: str | None
    status: str
    reason: str | None
    response_text: str | None
    metadata_json: dict[str, Any]
    created_at: datetime
