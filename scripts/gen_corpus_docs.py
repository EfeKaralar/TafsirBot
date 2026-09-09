"""Regenerate the registry tables in docs/CORPUS-REGISTRY.md from registry.yaml.

The prose in that document is hand-written and preserved. Only the tables between
the generated markers are replaced, so the per-scholar analysis sections stay put.

    uv run python scripts/gen_corpus_docs.py          # rewrite
    uv run python scripts/gen_corpus_docs.py --check  # verify in sync (CI)

A test asserts the file is in sync, so editing registry.yaml without running this
fails the suite rather than silently leaving the docs stale.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tafsirbot.corpus.registry import Registry, get_registry
from tafsirbot.settings import REPO_ROOT

DOC_PATH = REPO_ROOT / "docs" / "CORPUS-REGISTRY.md"

BEGIN = "<!-- BEGIN GENERATED: {name} -->"
END = "<!-- END GENERATED: {name} -->"


def _tafsir_table(registry: Registry) -> str:
    rows = [
        "| ID | Display Name | Language | Phase | Status | Madhab |",
        "|----|-------------|----------|-------|--------|--------|",
    ]
    for s in registry.tafsir:
        status = f"**{s.status}**" if s.is_available else s.status
        rows.append(
            f"| `{s.id}` | {s.display_name} | {s.language} | {s.phase} | {status} | {s.madhab} |"
        )
    return "\n".join(rows)


def _hadith_table(registry: Registry) -> str:
    rows = [
        "| ID | Display Name | Language | Phase | Status |",
        "|----|-------------|----------|-------|--------|",
    ]
    for s in registry.hadith:
        status = f"**{s.status}**" if s.is_available else s.status
        rows.append(f"| `{s.id}` | {s.display_name} | {s.language} | {s.phase} | {status} |")
    return "\n".join(rows)


def _replace_block(text: str, name: str, body: str) -> str:
    begin, end = BEGIN.format(name=name), END.format(name=name)
    if begin not in text or end not in text:
        raise SystemExit(
            f"Markers for {name!r} not found in {DOC_PATH}. "
            f"Add:\n{begin}\n{end}\naround the table this script owns."
        )
    head, rest = text.split(begin, 1)
    _, tail = rest.split(end, 1)
    return f"{head}{begin}\n<!-- Generated from src/tafsirbot/corpus/registry.yaml — do not edit by hand. -->\n{body}\n{end}{tail}"


def render(registry: Registry, current: str) -> str:
    out = _replace_block(current, "tafsir-table", _tafsir_table(registry))
    return _replace_block(out, "hadith-table", _hadith_table(registry))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if out of sync")
    args = parser.parse_args(argv)

    current = DOC_PATH.read_text(encoding="utf-8")
    expected = render(get_registry(), current)

    if current == expected:
        print(f"{DOC_PATH.relative_to(REPO_ROOT)} is in sync.")
        return 0

    if args.check:
        print(
            f"{DOC_PATH.relative_to(REPO_ROOT)} is OUT OF SYNC with registry.yaml.\n"
            f"Run: uv run python scripts/gen_corpus_docs.py",
            file=sys.stderr,
        )
        return 1

    DOC_PATH.write_text(expected, encoding="utf-8")
    print(f"Rewrote {DOC_PATH.relative_to(REPO_ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
