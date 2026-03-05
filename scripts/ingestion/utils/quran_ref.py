"""
quran_ref.py — Quran text lookup from the quran-json dist files.

Provides fast O(1) access to Arabic and English text for any surah/ayah,
and surah metadata (name, transliteration, type, total_verses).

Data source: sources/quran-json/dist/quran_en.json
  - Each entry has both 'text' (Arabic) and 'translation' (English) per verse.

Usage:
    from utils.quran_ref import QuranRef
    qr = QuranRef()
    ayah = qr.get_ayah(2, 255)
    # {"arabic_text": "...", "english_text": "..."}
    surah = qr.get_surah(2)
    # {"id": 2, "name": "البقرة", "transliteration": "Al-Baqarah", ...}
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)


class AyahData(TypedDict):
    arabic_text: str
    english_text: str


class SurahData(TypedDict):
    id: int
    name: str
    transliteration: str
    translation: str
    type: str
    total_verses: int


# Locate the dist directory relative to this file or via env var.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DIST = _REPO_ROOT / "sources" / "quran-json" / "dist"


class QuranRef:
    """Immutable in-memory Quran reference loaded from quran_en.json."""

    def __init__(self, dist_dir: str | Path | None = None) -> None:
        dist = Path(
            dist_dir
            or os.environ.get("QURAN_JSON_DIST", "")
            or _DEFAULT_DIST
        )
        quran_file = dist / "quran_en.json"

        if not quran_file.exists():
            raise FileNotFoundError(
                f"quran_en.json not found at {quran_file}. "
                "Run: cd sources/quran-json && npm install && npm run build"
            )

        logger.debug("Loading Quran reference data from %s", quran_file)
        with quran_file.open(encoding="utf-8") as f:
            raw: list[dict] = json.load(f)

        # Build lookup tables keyed by (surah_id, ayah_id).
        # surah and ayah IDs are 1-indexed.
        self._surahs: dict[int, SurahData] = {}
        self._ayahs: dict[tuple[int, int], AyahData] = {}

        for surah in raw:
            sid = surah["id"]
            self._surahs[sid] = SurahData(
                id=sid,
                name=surah["name"],
                transliteration=surah["transliteration"],
                translation=surah.get("translation", ""),
                type=surah.get("type", ""),
                total_verses=surah["total_verses"],
            )
            for verse in surah["verses"]:
                self._ayahs[(sid, verse["id"])] = AyahData(
                    arabic_text=verse["text"],
                    english_text=verse["translation"],
                )

        logger.info(
            "QuranRef loaded: %d surahs, %d ayahs",
            len(self._surahs),
            len(self._ayahs),
        )

    def get_ayah(self, surah: int, ayah: int) -> AyahData:
        """Return Arabic and English text for a single ayah.

        Args:
            surah: Surah number (1–114).
            ayah: Ayah number (1-indexed within the surah).

        Returns:
            AyahData with 'arabic_text' and 'english_text'.

        Raises:
            KeyError: If the surah/ayah combination does not exist.
        """
        key = (surah, ayah)
        if key not in self._ayahs:
            raise KeyError(f"Ayah not found: surah={surah}, ayah={ayah}")
        return self._ayahs[key]

    def get_ayah_range(self, surah: int, ayah_start: int, ayah_end: int) -> list[AyahData]:
        """Return a list of AyahData for a contiguous ayah range (inclusive)."""
        return [self.get_ayah(surah, a) for a in range(ayah_start, ayah_end + 1)]

    def get_surah(self, surah: int) -> SurahData:
        """Return surah metadata.

        Args:
            surah: Surah number (1–114).

        Raises:
            KeyError: If the surah number is out of range.
        """
        if surah not in self._surahs:
            raise KeyError(f"Surah not found: {surah}")
        return self._surahs[surah]

    def surah_name(self, surah: int) -> str:
        """Return the transliterated surah name (e.g. 'Al-Baqarah')."""
        return self._surahs[surah]["transliteration"]

    def total_verses(self, surah: int) -> int:
        """Return the total number of verses in a surah."""
        return self._surahs[surah]["total_verses"]

    @property
    def surah_count(self) -> int:
        return len(self._surahs)

    @property
    def ayah_count(self) -> int:
        return len(self._ayahs)
