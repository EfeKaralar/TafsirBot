"""Exception hierarchy for TafsirBot.

Every error the package raises deliberately derives from :class:`TafsirBotError` so
callers can catch the whole family, and each subclass maps to a distinct handling
policy at the API boundary (see ``api/errors.py``).

Never raise bare ``Exception``, and never ``except: pass``.
"""

from __future__ import annotations


class TafsirBotError(Exception):
    """Base class for all TafsirBot errors."""


class ConfigError(TafsirBotError):
    """Configuration is missing or invalid — a required env var, a bad path.

    Raised at startup, not per request. Not retryable.
    """


class RegistryError(ConfigError):
    """The corpus registry is missing, malformed, or references an unknown source."""


class RetrievalError(TafsirBotError):
    """Qdrant or an embedding model failed while serving a query."""


class ProviderError(TafsirBotError):
    """An upstream LLM provider failed.

    ``status`` carries the HTTP status the API should surface. ``detail`` is for logs
    only — it may contain provider text and must never reach a client response body.
    """

    def __init__(self, message: str, *, status: int = 502, detail: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.detail = detail


class PersistenceError(TafsirBotError):
    """Postgres was unreachable or a write failed.

    Persistence is best-effort on the query path: this must never cause an
    already-generated answer to be discarded.
    """
