"""``tafsirbot`` console entry point.

Subcommands are added as the epic progresses — ``ask`` and ``eval`` arrive with the
graph (PR #31) and the eval suite (PR #37). For now this covers the pieces PR #28
delivers, which is enough to verify the package is installed and configured.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from tafsirbot import __version__
from tafsirbot.logging_config import configure_logging


def _cmd_sources(args: argparse.Namespace) -> int:
    """Print the corpus registry — proves the package imports and the YAML parses."""
    from tafsirbot.corpus.registry import get_registry

    registry = get_registry()

    if args.json:
        payload = {
            kind: [
                {
                    "id": s.id,
                    "label": s.display_name,
                    "language": s.language,
                    "phase": s.phase,
                    "status": s.status,
                }
                for s in registry.of_kind(kind)
            ]
            for kind in ("tafsir", "hadith")
        }
        print(json.dumps(payload, indent=2))
        return 0

    for kind in ("tafsir", "hadith"):
        sources = registry.of_kind(kind)
        print(f"\n{kind.upper()} ({len(sources)})")
        for s in sources:
            mark = "✓" if s.is_available else " "
            print(f"  [{mark}] {s.id:<12} {s.display_name:<20} {s.language}  phase {s.phase}  {s.status}")
    print()
    return 0


def _cmd_migrate(args: argparse.Namespace) -> int:
    from tafsirbot.persistence.migrate import main as migrate_main

    return migrate_main()


def _cmd_config(args: argparse.Namespace) -> int:
    """Show resolved settings, with secrets redacted."""
    from tafsirbot.settings import get_settings

    settings = get_settings()
    dumped = settings.model_dump()
    for key in list(dumped):
        if "key" in key or "password" in key:
            dumped[key] = "***set***" if dumped[key] else None
    dumped["quran_json_dist"] = str(dumped["quran_json_dist"])
    dumped["_derived"] = {
        "vector_size": settings.vector_size,
        "embedding_token_limit": settings.embedding_token_limit,
        "available_providers": settings.available_providers(),
    }
    print(json.dumps(dumped, indent=2, default=str))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tafsirbot", description="TafsirBot CLI.")
    parser.add_argument("--version", action="version", version=f"tafsirbot {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sources = sub.add_parser("sources", help="list the corpus registry")
    p_sources.add_argument("--json", action="store_true", help="emit JSON")
    p_sources.set_defaults(func=_cmd_sources)

    p_config = sub.add_parser("config", help="show resolved settings (secrets redacted)")
    p_config.set_defaults(func=_cmd_config)

    p_migrate = sub.add_parser("migrate", help="apply Postgres migrations")
    p_migrate.set_defaults(func=_cmd_migrate)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
