"""
convert_maududi.py — Convert sources/maududi-json/dist/maududi.json into
the raw JSONL format expected by scripts/ingestion/clean.py.

Output: data/raw/maududi/{surah:03d}.jsonl  (one file per surah)

Each line is a JSON record:
    {
        "surah":      <int>,
        "ayah_start": <int>,   # 0 for intro chunks
        "ayah_end":   <int>,   # 0 for intro chunks
        "raw_text":   "<str>",
        "chunk_type": "intro" | "verse",
        "verse_text": "<str>"  # Ansari translation, preserved as metadata
    }

Surahs with no introduction and no commentary are written as empty files
(clean.py will simply skip them).

Usage:
    uv run python scripts/acquisition/convert_maududi.py
    uv run python scripts/acquisition/convert_maududi.py --surah 2
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("convert_maududi")

_REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILE = _REPO_ROOT / "sources" / "maududi-json" / "dist" / "maududi.json"
OUTPUT_DIR = _REPO_ROOT / "data" / "raw" / "maududi"


def convert_surah(surah: dict) -> list[dict]:
    """Return a list of raw JSONL records for one surah."""
    records: list[dict] = []
    num = surah["surah"]

    # Surah introduction → one intro chunk
    intro = surah.get("introduction", "").strip()
    if intro:
        records.append({
            "surah": num,
            "ayah_start": 0,
            "ayah_end": 0,
            "raw_text": intro,
            "chunk_type": "intro",
            "verse_text": "",
        })

    # Per-verse commentary → one verse chunk each
    for verse in surah.get("verses", []):
        commentary = verse.get("commentary", "").strip()
        if not commentary:
            continue
        records.append({
            "surah": num,
            "ayah_start": verse["ayah"],
            "ayah_end": verse["ayah"],
            "raw_text": commentary,
            "chunk_type": "verse",
            "verse_text": verse.get("verse_text", ""),
        })

    return records


def write_surah(surah: dict, output_dir: Path) -> int:
    """Write one surah's records to a JSONL file. Returns record count."""
    records = convert_surah(surah)
    outfile = output_dir / f"{surah['surah']:03d}.jsonl"
    with outfile.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert maududi-json dist into ingestion-pipeline JSONL."
    )
    parser.add_argument(
        "--surah",
        type=int,
        default=None,
        help="Convert a single surah only (prints to stdout for inspection).",
    )
    args = parser.parse_args()

    if not SOURCE_FILE.exists():
        logger.error("Source file not found: %s", SOURCE_FILE)
        logger.error("Make sure the maududi-json submodule is initialised:")
        logger.error("  git submodule update --init --recursive")
        sys.exit(1)

    data: list[dict] = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))

    if args.surah:
        match = next((s for s in data if s["surah"] == args.surah), None)
        if not match:
            logger.error("Surah %d not found in dataset.", args.surah)
            sys.exit(1)
        records = convert_surah(match)
        for rec in records:
            print(json.dumps(rec, indent=2, ensure_ascii=False))
        logger.info("%d records for surah %d", len(records), args.surah)
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_intros = total_verses = 0
    for surah in data:
        records = convert_surah(surah)
        outfile = OUTPUT_DIR / f"{surah['surah']:03d}.jsonl"
        with outfile.open("w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                if rec["chunk_type"] == "intro":
                    total_intros += 1
                else:
                    total_verses += 1

    logger.info(
        "Written %d intro + %d verse records across 114 files → %s",
        total_intros, total_verses, OUTPUT_DIR,
    )


if __name__ == "__main__":
    main()
