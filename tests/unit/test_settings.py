"""Tests for Settings — the one env surface.

The invariant worth protecting: vector size and token limit are *derived* from the
embedding model, not configured independently. Declaring them separately is how the
old code let EMBEDDING_MODEL change while VECTOR_SIZE silently stayed at 3072.
"""

from __future__ import annotations

import pytest

from tafsirbot.errors import ConfigError
from tafsirbot.settings import Settings


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


class TestEmbeddingDerivation:
    def test_large_model_dimensions(self) -> None:
        s = _settings(embedding_model="text-embedding-3-large")
        assert s.vector_size == 3072
        assert s.embedding_token_limit == 8191

    def test_small_model_dimensions(self) -> None:
        s = _settings(embedding_model="text-embedding-3-small")
        assert s.vector_size == 1536

    def test_unknown_model_raises_rather_than_guessing(self) -> None:
        """Guessing a dimension corrupts the collection irrecoverably."""
        s = _settings(embedding_model="some-future-model")
        with pytest.raises(ConfigError, match="Unknown embedding model"):
            _ = s.vector_size

    def test_error_lists_known_models(self) -> None:
        s = _settings(embedding_model="nope")
        with pytest.raises(ConfigError, match="text-embedding-3-large"):
            _ = s.vector_size


class TestModelRoles:
    def test_primary_and_fast_differ(self) -> None:
        """The whole point of tiering: cheap work must not hit the expensive model."""
        s = _settings()
        assert s.model_for("primary", "anthropic") != s.model_for("fast", "anthropic")
        assert s.model_for("primary", "openai") != s.model_for("fast", "openai")

    def test_defaults_to_configured_provider(self) -> None:
        s = _settings(llm_provider="openai")
        assert s.model_for("primary") == s.model_for("primary", "openai")

    def test_explicit_provider_overrides(self) -> None:
        s = _settings(llm_provider="anthropic")
        assert s.model_for("fast", "openai") == "gpt-4o-mini"


class TestProviders:
    def test_reports_only_configured_providers(self) -> None:
        assert _settings(anthropic_api_key="k", openai_api_key=None).available_providers() == [
            "anthropic"
        ]
        assert _settings(anthropic_api_key=None, openai_api_key="k").available_providers() == [
            "openai"
        ]
        assert _settings(anthropic_api_key=None, openai_api_key=None).available_providers() == []

    def test_require_openai_key_raises_when_absent(self) -> None:
        """OpenAI is required regardless of LLM provider — it serves dense embeddings."""
        with pytest.raises(ConfigError, match="OPENAI_API_KEY is required"):
            _settings(openai_api_key=None).require_openai_key()

    def test_require_openai_key_returns_it(self) -> None:
        assert _settings(openai_api_key="sk-x").require_openai_key() == "sk-x"


class TestCorsOrigins:
    def test_defaults_cover_vite_dev_server(self) -> None:
        origins = _settings().cors_origins
        assert "http://localhost:5173" in origins

    def test_accepts_comma_separated_string(self) -> None:
        """Env vars are strings; a list literal is awkward to express in .env."""
        s = _settings(cors_origins="https://a.example, https://b.example")
        assert s.cors_origins == ["https://a.example", "https://b.example"]

    def test_accepts_list(self) -> None:
        assert _settings(cors_origins=["https://a.example"]).cors_origins == ["https://a.example"]


class TestPaths:
    def test_relative_quran_path_resolves_against_repo_root_not_cwd(self) -> None:
        """QURAN_JSON_DIST is documented relative to the repo root."""
        s = _settings(quran_json_dist="sources/quran-json/dist")
        assert s.quran_json_dist.is_absolute()
        assert s.quran_json_dist.parts[-3:] == ("sources", "quran-json", "dist")

    def test_absolute_quran_path_is_left_alone(self, tmp_path) -> None:
        s = _settings(quran_json_dist=str(tmp_path))
        assert s.quran_json_dist == tmp_path


class TestPostgresConninfo:
    def test_includes_all_fields(self) -> None:
        info = _settings(postgres_password="pw", postgres_db="db").postgres_conninfo()
        for fragment in ("host=", "port=", "dbname=db", "user=", "password=pw", "sslmode="):
            assert fragment in info


class TestIsolation:
    def test_env_file_none_ignores_real_dotenv(self) -> None:
        """Without this, tests read the developer's .env and differ per machine."""
        s = _settings(qdrant_collection="explicit_value")
        assert s.qdrant_collection == "explicit_value"
