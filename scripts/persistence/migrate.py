from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from persistence import MigrationRunner, PostgresConfig


def main() -> None:
    runner = MigrationRunner(PostgresConfig.from_env())
    applied = runner.apply()
    if applied:
        print("Applied migrations:")
        for name in applied:
            print(f"  - {name}")
        return
    print("No pending migrations.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        raise
