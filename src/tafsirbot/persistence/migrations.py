from __future__ import annotations

from pathlib import Path

import psycopg

from tafsirbot.settings import REPO_ROOT

from .config import PostgresConfig


class MigrationRunner:
    def __init__(self, config: PostgresConfig, migrations_dir: Path | None = None) -> None:
        self.config = config
        # REPO_ROOT rather than a parents[N] count: this file moved from
        # scripts/persistence/ to src/tafsirbot/persistence/, which silently changed
        # the depth. Sourcing it from settings means the next move cannot break it.
        self.migrations_dir = migrations_dir or (REPO_ROOT / "db" / "migrations")

    def apply(self) -> list[str]:
        applied: list[str] = []
        with psycopg.connect(self.config.conninfo()) as conn, conn.cursor() as cur:
            cur.execute(
                """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version TEXT PRIMARY KEY,
                        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
            )
            conn.commit()

            for path in sorted(self.migrations_dir.glob("*.sql")):
                cur.execute(
                    "SELECT 1 FROM schema_migrations WHERE version = %s",
                    (path.name,),
                )
                if cur.fetchone():
                    continue

                cur.execute(path.read_text())
                cur.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)",
                    (path.name,),
                )
                conn.commit()
                applied.append(path.name)

        return applied
