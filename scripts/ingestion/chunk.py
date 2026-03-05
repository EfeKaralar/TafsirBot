"""
chunk.py — Produce ayah-scoped chunks with full metadata.

Reads cleaned JSONL from data/cleaned/<scholar>/ and writes final chunk
JSONL to data/chunks/<scholar>.jsonl, enriched with Arabic/English Ayah text
from the quran-json reference data.

Each output chunk is a JSON object ready for embedding and Qdrant upsert:

    {
        "content":        "<str>",       # text to embed
        "surah_number":   <int>,
        "ayah_start":     <int>,         # 0 for surah intro chunks
        "ayah_end":       <int>,         # 0 for surah intro chunks
        "scholar":        "<str>",
        "language":       "<str>",
        "source_title":   "<str>",
        "english_text":   "<str>",       # Quran translation of the covered ayahs
        "arabic_text":    "<str>",
        "chunk_type":     "verse"|"intro"|"legal",
        "isnad_text":     "<str>"        # stripped isnads (may be empty)
    }

Usage:
    python chunk.py --scholar ibn_kathir
    python chunk.py --scholar maududi
    python chunk.py --scholar all
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.quran_ref import QuranRef

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("chunk")

_REPO_ROOT = Path(__file__).resolve().parents[2]
CLEANED_DIR = _REPO_ROOT / "data" / "cleaned"
CHUNKS_DIR = _REPO_ROOT / "data" / "chunks"

# ── Scholar metadata ─────────────────────────────────────────────────────────

SCHOLAR_META: dict[str, dict] = {
    "ibn_kathir": {
        "scholar": "ibn_kathir",
        "language": "en",
        "source_title": "Tafsir al-Quran al-Azim (Dar-us-Salam, abridged EN)",
    },
    "maududi": {
        "scholar": "maududi",
        "language": "en",
        "source_title": "Tafhim al-Quran / Towards Understanding the Quran (Islamic Foundation EN)",
    },
    "tabari": {
        "scholar": "tabari",
        "language": "ar",
        "source_title": "Jami' al-Bayan 'an Ta'wil Ay al-Quran",
    },
    "jalalayn": {
        "scholar": "jalalayn",
        "language": "en",
        "source_title": "Tafsir al-Jalalayn (Feras Hamza EN)",
    },
    "qurtubi": {
        "scholar": "qurtubi",
        "language": "ar",
        "source_title": "Al-Jami' li-Ahkam al-Quran",
    },
    "ibn_ashur": {
        "scholar": "ibn_ashur",
        "language": "ar",
        "source_title": "Al-Tahrir wa-al-Tanwir",
    },
}


def _quran_texts(qr: QuranRef, surah: int, ayah_start: int, ayah_end: int) -> tuple[str, str]:
    """
    Return (arabic_text, english_text) for a single ayah or a range of ayahs.

    For a range, texts are concatenated with a space separator.
    For surah-intro chunks (ayah_start == 0), returns empty strings.
    """
    if ayah_start == 0:
        return "", ""

    arabic_parts: list[str] = []
    english_parts: list[str] = []
    for ayah in range(ayah_start, ayah_end + 1):
        try:
            data = qr.get_ayah(surah, ayah)
            arabic_parts.append(data["arabic_text"])
            english_parts.append(data["english_text"])
        except KeyError:
            logger.warning("Ayah not found in reference data: %d:%d", surah, ayah)
    return " ".join(arabic_parts), " ".join(english_parts)


def process_scholar(scholar: str, qr: QuranRef) -> None:
    meta = SCHOLAR_META.get(scholar)
    if meta is None:
        raise ValueError(f"Unknown scholar '{scholar}'. Valid: {list(SCHOLAR_META)}")

    input_dir = CLEANED_DIR / scholar
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = CHUNKS_DIR / f"{scholar}.jsonl"

    input_files = sorted(input_dir.glob("*.jsonl")) if input_dir.exists() else []
    if not input_files:
        logger.warning("No cleaned files found in %s — skipping", input_dir)
        return

    total_in = total_out = 0
    with output_file.open("w", encoding="utf-8") as fout:
        for infile in input_files:
            with infile.open(encoding="utf-8") as fin:
                for lineno, line in enumerate(fin, 1):
                    line = line.strip()
                    if not line:
                        continue
                    total_in += 1
                    try:
                        record = json.loads(line)
                        surah = int(record["surah"])
                        ayah_start = int(record.get("ayah_start", 0))
                        ayah_end = int(record.get("ayah_end", ayah_start))
                        clean_text = record.get("clean_text", "").strip()

                        if not clean_text:
                            logger.warning("%s:%d — empty clean_text, skipping", infile.name, lineno)
                            continue

                        arabic_text, english_text = _quran_texts(qr, surah, ayah_start, ayah_end)

                        chunk = {
                            "content": clean_text,
                            "surah_number": surah,
                            "ayah_start": ayah_start,
                            "ayah_end": ayah_end,
                            "scholar": meta["scholar"],
                            "language": meta["language"],
                            "source_title": meta["source_title"],
                            "english_text": english_text,
                            "arabic_text": arabic_text,
                            "chunk_type": record.get("chunk_type", "verse"),
                            "isnad_text": record.get("isnad_text", ""),
                        }
                        fout.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                        total_out += 1

                    except (json.JSONDecodeError, KeyError, ValueError) as exc:
                        logger.error("%s:%d — %s", infile.name, lineno, exc)

    logger.info(
        "chunk [%s] — %d in, %d out → %s",
        scholar, total_in, total_out, output_file,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Produce ayah-scoped chunks with metadata.")
    parser.add_argument(
        "--scholar",
        default="all",
        choices=[*SCHOLAR_META.keys(), "all"],
        help="Which scholar to chunk (default: all).",
    )
    args = parser.parse_args()

    qr = QuranRef()
    scholars = list(SCHOLAR_META.keys()) if args.scholar == "all" else [args.scholar]
    for scholar in scholars:
        process_scholar(scholar, qr)


if __name__ == "__main__":
    main()
