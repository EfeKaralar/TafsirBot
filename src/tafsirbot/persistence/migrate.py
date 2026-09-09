"""Apply SQL migrations to Postgres.

Owns ``db/migrations/*.sql`` only, tracked in the ``schema_migrations`` table.
The LangGraph checkpointer owns its own ``checkpoints*`` tables via its own
``setup()`` and its own ``checkpoint_migrations`` table — never hand-write that DDL
here, because the library's internal migration list changes between releases and
will re-run against tables it did not create.

Invoked as ``tafsirbot migrate``.
"""

from __future__ import annotations

from tafsirbot.logging_config import get_logger
from tafsirbot.persistence.config import PostgresConfig
from tafsirbot.persistence.migrations import MigrationRunner
from tafsirbot.settings import Settings, get_settings

logger = get_logger(__name__)


def run_migrations(settings: Settings | None = None) -> list[str]:
    """Apply pending migrations and return the names applied."""
    settings = settings or get_settings()
    runner = MigrationRunner(PostgresConfig.from_settings(settings))
    return runner.apply()


def main() -> int:
    from tafsirbot.logging_config import configure_logging

    configure_logging()
    applied = run_migrations()
    if applied:
        logger.info("Applied %d migration(s):", len(applied))
        for name in applied:
            logger.info("  - %s", name)
    else:
        logger.info("No pending migrations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
