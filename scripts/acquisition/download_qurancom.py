"""
download_qurancom.py — Download tafsir commentary from the quran.com API v4.

Outputs one JSONL file per surah to data/raw/<scholar>/, in the format
expected by scripts/ingestion/clean.py.

No API key required. The quran.com v4 API is publicly accessible.

Usage:
    # Discover available tafsir IDs first
    uv run python scripts/acquisition/download_qurancom.py --list-tafsirs

    # Download Ibn Kathir (EN) — verify ID with --list-tafsirs first
    uv run python scripts/acquisition/download_qurancom.py --scholar ibn_kathir

    # Download Maududi (EN)
    uv run python scripts/acquisition/download_qurancom.py --scholar maududi

    # Download both
    uv run python scripts/acquisition/download_qurancom.py --scholar all

    # Re-download even if files exist
    uv run python scripts/acquisition/download_qurancom.py --scholar ibn_kathir --force

    # Single surah (useful for testing)
    uv run python scripts/acquisition/download_qurancom.py --scholar ibn_kathir --surah 1
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
from pathlib import Path

import requests
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("download")

_REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = _REPO_ROOT / "data" / "raw"

BASE_URL = "https://api.quran.com/api/v4"

# Known tafsir IDs on quran.com v4.
# Run with --list-tafsirs to verify or find others.
# NOTE: Maududi (Tafhim al-Quran) is NOT available on quran.com.
#       Use download_islamicstudies.py for Maududi instead.
TAFSIR_IDS: dict[str, int] = {
    "ibn_kathir": 169,   # en-tafisr-ibn-kathir (Dar-us-Salam abridged EN)
}

REQUEST_DELAY = 0.25   # seconds between requests — be a polite client
RETRY_ATTEMPTS = 3
RETRY_DELAY = 5.0      # seconds before retrying a failed request


# ── HTML stripping ────────────────────────────────────────────────────────────

_HTML_TAG = re.compile(r"<[^>]+>")
_MULTIPLE_SPACES = re.compile(r"[ \t]{2,}")
_MULTIPLE_NEWLINES = re.compile(r"\n{3,}")


def strip_html(text: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    text = _HTML_TAG.sub(" ", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&nbsp;", " ").replace("&#39;", "'").replace("&quot;", '"')
    text = _MULTIPLE_SPACES.sub(" ", text)
    text = _MULTIPLE_NEWLINES.sub("\n\n", text)
    return text.strip()


# ── API helpers ───────────────────────────────────────────────────────────────

def _get(url: str, params: dict | None = None) -> dict:
    """GET with retry on transient errors."""
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                raise  # don't retry 404s
            if attempt == RETRY_ATTEMPTS:
                raise
            logger.warning("HTTP error (attempt %d/%d): %s — retrying in %.0fs",
                           attempt, RETRY_ATTEMPTS, exc, RETRY_DELAY)
            time.sleep(RETRY_DELAY)
        except requests.RequestException as exc:
            if attempt == RETRY_ATTEMPTS:
                raise
            logger.warning("Request error (attempt %d/%d): %s — retrying in %.0fs",
                           attempt, RETRY_ATTEMPTS, exc, RETRY_DELAY)
            time.sleep(RETRY_DELAY)

    raise RuntimeError("All retries exhausted")  # unreachable


def list_tafsirs(language: str = "en") -> list[dict]:
    """Return all tafsirs available on quran.com for a given language."""
    data = _get(f"{BASE_URL}/resources/tafsirs", params={"language": language})
    return data.get("tafsirs", [])


# ── Download ──────────────────────────────────────────────────────────────────

def download_surah(tafsir_id: int, surah: int) -> list[dict]:
    """
    Fetch all verse-level tafsir records for one surah, handling pagination.

    The quran.com API returns 10 records per page by default. We iterate
    through all pages until exhausted.

    Returns a list of dicts with keys: verse_key, text (stripped HTML).
    """
    url = f"{BASE_URL}/tafsirs/{tafsir_id}/by_chapter/{surah}"
    results: list[dict] = []
    page = 1

    while True:
        data = _get(url, params={"page": page})
        records = data.get("tafsirs", [])
        results.extend(
            {
                "verse_key": r["verse_key"],
                "text": strip_html(r.get("text") or ""),
            }
            for r in records
            if r.get("text")
        )

        pagination = data.get("pagination", {})
        if pagination.get("next_page") is None:
            break
        page = pagination["next_page"]
        time.sleep(REQUEST_DELAY)

    return results


def parse_verse_key(verse_key: str) -> tuple[int, int]:
    """Parse '2:255' → (2, 255)."""
    parts = verse_key.split(":")
    return int(parts[0]), int(parts[1])


def download_scholar(scholar: str, surah_range: range, force: bool) -> None:
    tafsir_id = TAFSIR_IDS.get(scholar)
    if tafsir_id is None:
        raise ValueError(f"Unknown scholar '{scholar}'. Valid: {list(TAFSIR_IDS)}")

    output_dir = RAW_DIR / scholar
    output_dir.mkdir(parents=True, exist_ok=True)

    skipped = downloaded = 0

    for surah in tqdm(surah_range, desc=scholar, unit="surah"):
        outfile = output_dir / f"{surah:03d}.jsonl"

        if outfile.exists() and not force:
            skipped += 1
            continue

        try:
            verses = download_surah(tafsir_id, surah)
        except requests.HTTPError as exc:
            logger.error("Failed to download surah %d: %s", surah, exc)
            continue

        if not verses:
            logger.warning("No tafsir text returned for surah %d (tafsir_id=%d)", surah, tafsir_id)
            continue

        with outfile.open("w", encoding="utf-8") as f:
            for verse in verses:
                surah_num, ayah_num = parse_verse_key(verse["verse_key"])
                record = {
                    "surah": surah_num,
                    "ayah_start": ayah_num,
                    "ayah_end": ayah_num,
                    "raw_text": verse["text"],
                    "chunk_type": "verse",
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        downloaded += 1
        time.sleep(REQUEST_DELAY)

    logger.info(
        "download [%s] — %d surahs downloaded, %d skipped (already exist)",
        scholar, downloaded, skipped,
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download tafsir commentary from the quran.com API."
    )
    parser.add_argument(
        "--scholar",
        choices=[*TAFSIR_IDS.keys(), "all"],
        default="all",
        help="Which scholar to download (default: all).",
    )
    parser.add_argument(
        "--surah",
        type=int,
        default=None,
        metavar="N",
        help="Download a single surah only (1–114). Useful for testing.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if the output file already exists.",
    )
    parser.add_argument(
        "--list-tafsirs",
        action="store_true",
        help="Print all English tafsirs available on quran.com and exit.",
    )
    args = parser.parse_args()

    if args.list_tafsirs:
        print("\nAvailable English tafsirs on quran.com:\n")
        tafsirs = list_tafsirs(language="en")
        for t in tafsirs:
            print(f"  ID {t['id']:>4}  slug={t.get('slug', '?'):<40}  {t.get('name', '?')}")
        print()
        return

    surah_range = range(args.surah, args.surah + 1) if args.surah else range(1, 115)
    scholars = list(TAFSIR_IDS.keys()) if args.scholar == "all" else [args.scholar]

    for scholar in scholars:
        download_scholar(scholar, surah_range, args.force)


if __name__ == "__main__":
    main()
