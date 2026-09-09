"""Logging setup.

Called by entry points **only** — never at import time from a library module.
The legacy ``scripts/`` tree calls ``logging.basicConfig()`` at import, which means
importing the API reconfigures root logging as a side effect. This module exists so
the package never does that.
"""

from __future__ import annotations

import logging

_FORMAT = "%(asctime)s %(levelname)s %(name)s — %(message)s"
_DATEFMT = "%H:%M:%S"

_configured = False


def configure_logging(level: int | str = logging.INFO, *, force: bool = False) -> None:
    """Configure root logging once.

    Idempotent: repeated calls are no-ops unless ``force`` is set. This matters because
    both a CLI entry point and a uvicorn worker may try to configure logging in the
    same process.
    """
    global _configured
    if _configured and not force:
        return

    logging.basicConfig(level=level, format=_FORMAT, datefmt=_DATEFMT, force=force)

    # These are chatty at INFO and drown out our own logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a package-namespaced logger.

    ``get_logger("retrieval.hybrid")`` -> ``tafsirbot.retrieval.hybrid``.
    """
    return logging.getLogger(name if name.startswith("tafsirbot") else f"tafsirbot.{name}")
