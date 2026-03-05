"""
clean.py — Normalize raw tafsir source text.

Reads raw JSONL files from data/raw/<scholar>/ and writes cleaned JSONL
to data/cleaned/<scholar>/.

Expected input format (one JSON object per line):
    {
        "surah": <int>,
        "ayah_start": <int>,
        "ayah_end": <int>,
        "raw_text": "<str>",
        "chunk_type": "verse" | "intro"   (optional, defaults to "verse")
    }

Output format (same fields, raw_text replaced by clean_text):
    {
        "surah": <int>,
        "ayah_start": <int>,
        "ayah_end": <int>,
        "clean_text": "<str>",
        "chunk_type": "verse" | "intro",
        "isnad_text": "<str>"   (ibn_kathir / tabari only — stripped chains)
    }

Usage:
    python clean.py --scholar ibn_kathir
    python clean.py --scholar maududi
    python clean.py --scholar all
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import unicodedata
from pathlib import Path

# ── Project root on sys.path so sibling packages resolve ────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("clean")

_REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = _REPO_ROOT / "data" / "raw"
CLEANED_DIR = _REPO_ROOT / "data" / "cleaned"

# ── Isnad chain patterns (Ibn Kathir / Al-Tabari) ────────────────────────────
# These regex patterns identify the START of an isnad chain segment so we can
# split matn (commentary body) from isnad (transmission chain).

_ISNAD_STARTERS = re.compile(
    r"""
    (?:
        It\s+was\s+(?:narrated|reported|said|mentioned)\s+(?:to\s+us\s+)?(?:by|from)\b
        | (?:Imam\s+)?(?:Al-|Ash-|An-|At-)?
          (?:Bukhari|Muslim|Tirmidhi|Abu\s+Dawud|Nasa['\u2019]i|Ibn\s+Majah|Ahmad|
             Hakim|Bayhaqi|Tabarani|Daraqutni|Darimi)\s+(?:recorded|narrated|reported)
        | (?:Ibn\s+(?:Abbas|Masud|Umar|Kathir|Jarir)\s+(?:said|narrated|reported))
        | (?:Al-)?(?:Suddi|Mujahid|Qatadah|Hasan(?:\s+al-Basri)?|Dahhak)\s+said
        | (?:(?:Abu|Umm)\s+\w+\s+(?:narrated|reported|said))\b
        | \(Recorded\s+by\b
        | \(Narrated\s+by\b
        | \bchain\s+of\s+narrators\b
        | \bisnad\b
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# ── Unicode / typography normalization ───────────────────────────────────────

_SMART_QUOTES = str.maketrans({
    "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-",
    "\u00a0": " ",
})

_MULTIPLE_SPACES = re.compile(r"[ \t]{2,}")
_MULTIPLE_NEWLINES = re.compile(r"\n{3,}")
_PAGE_MARKERS = re.compile(
    r"(?:\[?[Pp]age\s*\d+\]?|\[?\d+\]|\[Vol\.\s*\d+[^\]]*\])", re.IGNORECASE
)
_FOOTNOTE_MARKERS = re.compile(r"\[\d+\]|\(\d+\)")


def _normalize_unicode(text: str) -> str:
    """NFC normalize and replace problematic Unicode typographic characters."""
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_SMART_QUOTES)
    return text


def _strip_layout_artifacts(text: str) -> str:
    """Remove page numbers, footnote markers, and excess whitespace."""
    text = _PAGE_MARKERS.sub("", text)
    text = _FOOTNOTE_MARKERS.sub("", text)
    text = _MULTIPLE_SPACES.sub(" ", text)
    text = _MULTIPLE_NEWLINES.sub("\n\n", text)
    return text.strip()


# ── Scholar-specific cleaners ─────────────────────────────────────────────────

def _split_isnad(text: str) -> tuple[str, str]:
    """
    Split commentary text into (matn, isnad) for Ibn Kathir / Al-Tabari.

    Sentences that match isnad starter patterns are moved to the isnad field.
    The matn keeps the interpretive content; isnad chains go to the separate field.

    Returns (matn_text, isnad_text). If no isnad patterns found, isnad_text is "".
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    matn_parts: list[str] = []
    isnad_parts: list[str] = []

    in_isnad = False
    for sentence in sentences:
        if _ISNAD_STARTERS.search(sentence):
            in_isnad = True
        if in_isnad:
            isnad_parts.append(sentence)
            # Reset when we see a clean interpretive sentence starting after isnads
            if re.match(r"^(?:This\s+means|Allah\s+says|The\s+meaning|In\s+other\s+words)", sentence):
                in_isnad = False
        else:
            matn_parts.append(sentence)

    return " ".join(matn_parts).strip(), " ".join(isnad_parts).strip()


def clean_ibn_kathir(record: dict) -> dict:
    text = _normalize_unicode(record["raw_text"])
    text = _strip_layout_artifacts(text)
    matn, isnad = _split_isnad(text)
    return {**record, "clean_text": matn or text, "isnad_text": isnad, "chunk_type": record.get("chunk_type", "verse")}


def clean_maududi(record: dict) -> dict:
    text = _normalize_unicode(record["raw_text"])
    text = _strip_layout_artifacts(text)
    # Maududi has no isnads; just strip footnote reference numbers
    text = re.sub(r"\bNote\s+\d+\b", "", text, flags=re.IGNORECASE)
    return {**record, "clean_text": text, "isnad_text": "", "chunk_type": record.get("chunk_type", "verse")}


def clean_tabari(record: dict) -> dict:
    text = _normalize_unicode(record["raw_text"])
    text = _strip_layout_artifacts(text)
    matn, isnad = _split_isnad(text)
    return {**record, "clean_text": matn or text, "isnad_text": isnad, "chunk_type": record.get("chunk_type", "verse")}


def clean_jalalayn(record: dict) -> dict:
    text = _normalize_unicode(record["raw_text"])
    text = _strip_layout_artifacts(text)
    return {**record, "clean_text": text, "isnad_text": "", "chunk_type": record.get("chunk_type", "verse")}


def clean_qurtubi(record: dict) -> dict:
    text = _normalize_unicode(record["raw_text"])
    text = _strip_layout_artifacts(text)
    return {**record, "clean_text": text, "isnad_text": "", "chunk_type": record.get("chunk_type", "legal")}


def clean_ibn_ashur(record: dict) -> dict:
    text = _normalize_unicode(record["raw_text"])
    text = _strip_layout_artifacts(text)
    return {**record, "clean_text": text, "isnad_text": "", "chunk_type": record.get("chunk_type", "verse")}


CLEANERS: dict[str, callable] = {
    "ibn_kathir": clean_ibn_kathir,
    "maududi": clean_maududi,
    "tabari": clean_tabari,
    "jalalayn": clean_jalalayn,
    "qurtubi": clean_qurtubi,
    "ibn_ashur": clean_ibn_ashur,
}


# ── Main ─────────────────────────────────────────────────────────────────────

def process_scholar(scholar: str) -> None:
    cleaner = CLEANERS.get(scholar)
    if cleaner is None:
        raise ValueError(f"Unknown scholar '{scholar}'. Valid options: {list(CLEANERS)}")

    input_dir = RAW_DIR / scholar
    output_dir = CLEANED_DIR / scholar
    output_dir.mkdir(parents=True, exist_ok=True)

    input_files = sorted(input_dir.glob("*.jsonl")) if input_dir.exists() else []
    if not input_files:
        logger.warning("No .jsonl files found in %s — skipping", input_dir)
        return

    total_in = total_out = 0
    for infile in input_files:
        outfile = output_dir / infile.name
        with infile.open(encoding="utf-8") as fin, outfile.open("w", encoding="utf-8") as fout:
            for lineno, line in enumerate(fin, 1):
                line = line.strip()
                if not line:
                    continue
                total_in += 1
                try:
                    record = json.loads(line)
                    cleaned = cleaner(record)
                    # Validate required output fields
                    if not cleaned.get("clean_text"):
                        logger.warning("%s:%d — empty clean_text, skipping", infile.name, lineno)
                        continue
                    fout.write(json.dumps(cleaned, ensure_ascii=False) + "\n")
                    total_out += 1
                except (json.JSONDecodeError, KeyError) as exc:
                    logger.error("%s:%d — %s", infile.name, lineno, exc)

    logger.info(
        "clean [%s] — %d records in, %d records out → %s",
        scholar, total_in, total_out, output_dir,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean raw tafsir text files.")
    parser.add_argument(
        "--scholar",
        default="all",
        choices=[*CLEANERS.keys(), "all"],
        help="Which scholar's raw data to clean (default: all).",
    )
    args = parser.parse_args()

    scholars = list(CLEANERS.keys()) if args.scholar == "all" else [args.scholar]
    for scholar in scholars:
        process_scholar(scholar)


if __name__ == "__main__":
    main()
