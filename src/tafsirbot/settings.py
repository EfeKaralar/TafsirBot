"""The one environment surface.

Before this module, config was read ad hoc with ``os.environ.get`` at four different
call sites: the Qdrant client was constructed 4x, ``QDRANT_COLLECTION`` defaulted 4x,
the sparse model name was declared 3x, and the embedding model was read 3x while its
``VECTOR_SIZE`` lived in an unrelated file — so changing the model silently left the
dimension wrong.

Everything is declared here once. ``Settings`` is constructed by entry points and
passed down; library modules never read ``os.environ`` themselves.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from tafsirbot.errors import ConfigError

Provider = Literal["anthropic", "openai"]

REPO_ROOT = Path(__file__).resolve().parents[2]

# Dense embedding model -> (vector dimensions, max input tokens).
# Both are properties of the model, so they must not be configured independently.
EMBEDDING_SPECS: dict[str, tuple[int, int]] = {
    "text-embedding-3-large": (3072, 8191),
    "text-embedding-3-small": (1536, 8191),
    "text-embedding-ada-002": (1536, 8191),
}


class Settings(BaseSettings):
    """Runtime configuration, resolved from the environment and ``.env``."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── LLM ───────────────────────────────────────────────────────────────────
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    llm_provider: Provider = "anthropic"

    # Model per role. The answer model is the expensive one; everything else
    # (classify, rewrite, grade, verify) runs on the fast tier. Before this split,
    # intent classification burned a full Sonnet call for a 10-token answer on
    # every request, including every off-topic one.
    model_primary_anthropic: str = "claude-sonnet-5"
    model_fast_anthropic: str = "claude-haiku-4-5-20251001"
    model_primary_openai: str = "gpt-4o"
    model_fast_openai: str = "gpt-4o-mini"

    generation_temperature: float = 0.3
    generation_max_tokens: int = 800

    # ── Embeddings ────────────────────────────────────────────────────────────
    # Changing this after the first upsert invalidates the collection — vectors from
    # different models are not comparable.
    embedding_model: str = "text-embedding-3-large"
    sparse_model: str = "Qdrant/bm42-all-minilm-l6-v2-attentions"

    # ── Vector DB ─────────────────────────────────────────────────────────────
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "tafsir"
    qdrant_hadith_collection: str = "hadith"

    top_k: int = 5
    # Candidates pulled per prefetch branch before fusion, as a multiple of top_k.
    prefetch_multiplier: int = 4

    # ── Postgres ──────────────────────────────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "tafsir_bot"
    postgres_user: str = "tafsirbot"
    postgres_password: str = ""
    postgres_sslmode: str = "prefer"
    postgres_connect_timeout: int = 5

    # On in dev; off in prod, where a deploy step runs migrations. Prevents N uvicorn
    # workers racing on DDL.
    tafsirbot_run_migrations: bool = True

    # ── API ───────────────────────────────────────────────────────────────────
    # Was hardcoded in scripts/api.py, which broke any non-dev deployment.
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"]
    )

    # ── Ingestion ─────────────────────────────────────────────────────────────
    quran_json_dist: Path = REPO_ROOT / "sources" / "quran-json" / "dist"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        """Accept a comma-separated string as well as a list."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator("quran_json_dist", mode="before")
    @classmethod
    def _resolve_quran_path(cls, v: object) -> object:
        """Resolve a relative QURAN_JSON_DIST against the repo root, not the cwd."""
        if isinstance(v, str):
            p = Path(v)
            return p if p.is_absolute() else REPO_ROOT / p
        return v

    # ── Derived ───────────────────────────────────────────────────────────────

    @computed_field  # type: ignore[prop-decorator]
    @property
    def vector_size(self) -> int:
        """Dense vector dimensions for the configured embedding model."""
        return self._embedding_spec()[0]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def embedding_token_limit(self) -> int:
        """Max input tokens for the configured embedding model."""
        return self._embedding_spec()[1]

    def _embedding_spec(self) -> tuple[int, int]:
        try:
            return EMBEDDING_SPECS[self.embedding_model]
        except KeyError:
            raise ConfigError(
                f"Unknown embedding model {self.embedding_model!r}. "
                f"Add it to EMBEDDING_SPECS with its (dimensions, token_limit) — "
                f"these cannot be inferred, and guessing corrupts the collection. "
                f"Known: {sorted(EMBEDDING_SPECS)}"
            ) from None

    def model_for(self, role: Literal["primary", "fast"], provider: Provider | None = None) -> str:
        """Return the model id for a role on a provider (defaults to ``llm_provider``)."""
        provider = provider or self.llm_provider
        return {
            ("primary", "anthropic"): self.model_primary_anthropic,
            ("fast", "anthropic"): self.model_fast_anthropic,
            ("primary", "openai"): self.model_primary_openai,
            ("fast", "openai"): self.model_fast_openai,
        }[(role, provider)]

    def postgres_conninfo(self) -> str:
        """Build a libpq keyword conninfo string."""
        return " ".join(
            [
                f"host={self.postgres_host}",
                f"port={self.postgres_port}",
                f"dbname={self.postgres_db}",
                f"user={self.postgres_user}",
                f"password={self.postgres_password}",
                f"sslmode={self.postgres_sslmode}",
                f"connect_timeout={self.postgres_connect_timeout}",
            ]
        )

    def require_openai_key(self) -> str:
        """Return the OpenAI key, or raise — it is required for dense embeddings."""
        if not self.openai_api_key:
            raise ConfigError("OPENAI_API_KEY is required (used for dense embeddings).")
        return self.openai_api_key

    def available_providers(self) -> list[Provider]:
        """Providers with a configured API key."""
        out: list[Provider] = []
        if self.anthropic_api_key:
            out.append("anthropic")
        if self.openai_api_key:
            out.append("openai")
        return out


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide cached settings.

    Tests should construct ``Settings(...)`` directly, or call
    ``get_settings.cache_clear()`` after mutating the environment.
    """
    return Settings()
