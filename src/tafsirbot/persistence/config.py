from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tafsirbot.settings import Settings


@dataclass(frozen=True)
class PostgresConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str
    sslmode: str = "prefer"
    connect_timeout: int = 5

    @classmethod
    def from_settings(cls, settings: Settings) -> PostgresConfig:
        """Build from :class:`~tafsirbot.settings.Settings` — preferred for new code.

        ``Settings`` parses ``.env`` itself, so this works without ``load_dotenv``.
        """
        return cls(
            host=settings.postgres_host,
            port=settings.postgres_port,
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
            sslmode=settings.postgres_sslmode,
            connect_timeout=settings.postgres_connect_timeout,
        )

    @classmethod
    def from_env(cls) -> PostgresConfig:
        """Build from ``os.environ`` directly.

        Retained for the legacy ``scripts/`` entry points, which call ``load_dotenv()``
        at import. Note this does *not* see ``.env`` on its own — prefer
        :meth:`from_settings`.
        """
        return cls(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            dbname=os.environ.get("POSTGRES_DB", "tafsir_bot"),
            user=os.environ.get("POSTGRES_USER", ""),
            password=os.environ.get("POSTGRES_PASSWORD", ""),
            sslmode=os.environ.get("POSTGRES_SSLMODE", "prefer"),
            connect_timeout=int(os.environ.get("POSTGRES_CONNECT_TIMEOUT", "5")),
        )

    def validate(self) -> None:
        missing = [
            name
            for name, value in (
                ("POSTGRES_USER", self.user),
                ("POSTGRES_PASSWORD", self.password),
                ("POSTGRES_DB", self.dbname),
                ("POSTGRES_HOST", self.host),
            )
            if not value
        ]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Missing required Postgres settings: {joined}")

    def conninfo(self) -> str:
        self.validate()
        return (
            f"host={self.host} "
            f"port={self.port} "
            f"dbname={self.dbname} "
            f"user={self.user} "
            f"password={self.password} "
            f"sslmode={self.sslmode} "
            f"connect_timeout={self.connect_timeout}"
        )
