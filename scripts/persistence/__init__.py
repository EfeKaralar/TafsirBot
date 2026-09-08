"""Compatibility shim — moved to ``tafsirbot.persistence``.

Re-export only, zero logic. ``scripts/api.py``, ``scripts/rag_poc.py`` and
``scripts/test_poc.py`` do ``from persistence import PostgresPersistence`` with
``scripts/`` on ``sys.path``; this keeps that working during epic #38. Deleted with
the rest of ``scripts/`` in PR #37.

New code must import from ``tafsirbot.persistence``.
"""

from tafsirbot.persistence import (
    ChatMessageRecord,
    ChatSessionRecord,
    ChatStore,
    MigrationRunner,
    PostgresConfig,
    PostgresPersistence,
    TestRunCaseRecord,
    TestRunRecord,
    TestRunStore,
)

__all__ = [
    "ChatMessageRecord",
    "ChatSessionRecord",
    "ChatStore",
    "MigrationRunner",
    "PostgresConfig",
    "PostgresPersistence",
    "TestRunCaseRecord",
    "TestRunRecord",
    "TestRunStore",
]
