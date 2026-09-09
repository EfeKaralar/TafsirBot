"""Shared fixtures.

There was no conftest.py before this: every test file hand-rolled its own
``sys.path.insert`` because the project was not installable. Those inserts remain in
the legacy ingestion tests (they exercise modules that have not moved yet) but new
tests import ``tafsirbot`` directly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tafsirbot.corpus.registry import Registry, load_registry
from tafsirbot.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def settings() -> Settings:
    """Settings with every value supplied explicitly.

    ``_env_file=None`` is essential: without it the developer's real ``.env`` leaks
    into tests and results differ per machine.
    """
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        anthropic_api_key="test-anthropic-key",
        openai_api_key="test-openai-key",
        llm_provider="anthropic",
        qdrant_host="localhost",
        qdrant_port=6333,
        qdrant_collection="test_tafsir",
        qdrant_hadith_collection="test_hadith",
        postgres_host="localhost",
        postgres_db="test_tafsir_bot",
        postgres_user="test_user",
        postgres_password="test_password",
    )


@pytest.fixture(scope="session")
def registry() -> Registry:
    """The real corpus registry — small, static, and worth testing against directly."""
    return load_registry()
