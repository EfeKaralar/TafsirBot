"""
ayah_resolver.py — Resolve Quranic references from natural-language text.

Handles:
  - Numeric references:   "2:255", "2:255-257", "Surah 2:255"
  - Surah-only:          "Surah Al-Fatiha", "Surat Al-Baqarah"
  - Named verses:         "Ayat al-Kursi", "Ayat al-Nur", "Ayat al-Throne"

Returns a list of (surah_number, ayah_start, ayah_end) triples.
When only a surah is identified (no specific ayah), ayah_start and ayah_end are
both 0, indicating a surah-level match.

Usage:
    from utils.ayah_resolver import AyahResolver
    from utils.quran_ref import QuranRef
    qr = QuranRef()
    resolver = AyahResolver(qr)
    refs = resolver.resolve("What does Ibn Kathir say about Ayat al-Kursi?")
    # [(2, 255, 255)]
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from .quran_ref import QuranRef

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AyahRef:
    surah: int
    ayah_start: int  # 0 means surah-level only
    ayah_end: int    # 0 means surah-level only

    def is_surah_only(self) -> bool:
        return self.ayah_start == 0

    def as_filter(self) -> dict:
        """Return a Qdrant metadata filter dict for this reference."""
        conditions = [{"key": "surah_number", "match": {"value": self.surah}}]
        if not self.is_surah_only():
            conditions.append({"key": "ayah_start", "range": {"gte": self.ayah_start}})
            conditions.append({"key": "ayah_end", "range": {"lte": self.ayah_end}})
        return {"must": conditions}


# ── Named verse lookup ────────────────────────────────────────────────────────
# Maps common English and transliterated names → (surah, ayah_start, ayah_end).
# Extend this table as more named verses become relevant.

NAMED_VERSES: dict[str, tuple[int, int, int]] = {
    # Ayat al-Kursi — The Throne Verse
    "ayat al-kursi": (2, 255, 255),
    "ayat al kursi": (2, 255, 255),
    "ayatul kursi": (2, 255, 255),
    "ayat ul kursi": (2, 255, 255),
    "throne verse": (2, 255, 255),
    "verse of the throne": (2, 255, 255),
    # Ayat al-Nur — The Light Verse
    "ayat al-nur": (24, 35, 35),
    "ayat al nur": (24, 35, 35),
    "verse of light": (24, 35, 35),
    "light verse": (24, 35, 35),
    # Al-Fatiha — The Opening
    "al-fatiha": (1, 1, 7),
    "al fatiha": (1, 1, 7),
    "surah fatiha": (1, 1, 7),
    "surat al-fatiha": (1, 1, 7),
    "the opening": (1, 1, 7),
    "al-fatihah": (1, 1, 7),
    # Al-Ikhlas
    "al-ikhlas": (112, 1, 4),
    "al ikhlas": (112, 1, 4),
    "surah ikhlas": (112, 1, 4),
    "surah al-ikhlas": (112, 1, 4),
    "surah of sincerity": (112, 1, 4),
    # Al-Falaq and Al-Nas (the two protective surahs)
    "al-falaq": (113, 1, 5),
    "surah al-falaq": (113, 1, 5),
    "al-nas": (114, 1, 6),
    "surah al-nas": (114, 1, 6),
    # Al-Kahf — specific famous passages
    "people of the cave": (18, 9, 26),
    "ashab al-kahf": (18, 9, 26),
    # Verse of Light (alternative)
    "nour": (24, 35, 35),
}

# Surah name → surah number mapping (transliterations and common variants).
SURAH_NAMES: dict[str, int] = {
    "al-fatihah": 1, "al-fatiha": 1, "fatihah": 1, "fatiha": 1,
    "al-baqarah": 2, "al-baqara": 2, "baqarah": 2,
    "al-imran": 3, "ali imran": 3, "al-i-imran": 3,
    "an-nisa": 4, "an-nisaa": 4, "nisa": 4,
    "al-maidah": 5, "al-ma'idah": 5, "maidah": 5,
    "al-anam": 6, "al-an'am": 6,
    "al-araf": 7, "al-a'raf": 7,
    "al-anfal": 8,
    "at-tawbah": 9, "al-tawba": 9, "tawbah": 9,
    "yunus": 10,
    "hud": 11,
    "yusuf": 12,
    "ar-rad": 13, "al-ra'd": 13,
    "ibrahim": 14,
    "al-hijr": 15,
    "an-nahl": 16, "al-nahl": 16,
    "al-isra": 17, "bani isra'il": 17,
    "al-kahf": 18, "al-kahf": 18,
    "maryam": 19,
    "ta-ha": 20, "ta ha": 20, "taha": 20,
    "al-anbiya": 21,
    "al-hajj": 22,
    "al-muminun": 23,
    "an-nur": 24, "al-nur": 24,
    "al-furqan": 25,
    "ash-shuara": 26, "al-shu'ara": 26,
    "an-naml": 27,
    "al-qasas": 28,
    "al-ankabut": 29,
    "ar-rum": 30,
    "luqman": 31,
    "as-sajdah": 32, "al-sajda": 32,
    "al-ahzab": 33,
    "saba": 34,
    "fatir": 35,
    "ya-sin": 36, "ya sin": 36, "yasin": 36,
    "as-saffat": 37,
    "sad": 38,
    "az-zumar": 39,
    "ghafir": 40, "al-mumin": 40,
    "fussilat": 41, "ha mim": 41,
    "ash-shura": 42,
    "az-zukhruf": 43,
    "ad-dukhan": 44,
    "al-jathiyah": 45,
    "al-ahqaf": 46,
    "muhammad": 47,
    "al-fath": 48,
    "al-hujurat": 49,
    "qaf": 50,
    "adh-dhariyat": 51,
    "at-tur": 52,
    "an-najm": 53,
    "al-qamar": 54,
    "ar-rahman": 55, "al-rahman": 55,
    "al-waqiah": 56, "al-waqi'ah": 56,
    "al-hadid": 57,
    "al-mujadila": 58,
    "al-hashr": 59,
    "al-mumtahanah": 60,
    "as-saf": 61,
    "al-jumuah": 62,
    "al-munafiqun": 63,
    "at-taghabun": 64,
    "at-talaq": 65,
    "at-tahrim": 66,
    "al-mulk": 67,
    "al-qalam": 68,
    "al-haqqah": 69,
    "al-maarij": 70, "al-ma'arij": 70,
    "nuh": 71,
    "al-jinn": 72,
    "al-muzzammil": 73,
    "al-muddaththir": 74,
    "al-qiyamah": 75,
    "al-insan": 76, "al-dahr": 76,
    "al-mursalat": 77,
    "an-naba": 78,
    "an-naziat": 79,
    "abasa": 80,
    "at-takwir": 81,
    "al-infitar": 82,
    "al-mutaffifin": 83,
    "al-inshiqaq": 84,
    "al-buruj": 85,
    "at-tariq": 86,
    "al-ala": 87, "al-a'la": 87,
    "al-ghashiyah": 88,
    "al-fajr": 89,
    "al-balad": 90,
    "ash-shams": 91,
    "al-layl": 92,
    "ad-duha": 93,
    "ash-sharh": 94, "al-inshirah": 94,
    "at-tin": 95,
    "al-alaq": 96, "al-'alaq": 96,
    "al-qadr": 97,
    "al-bayyinah": 98,
    "az-zalzalah": 99,
    "al-adiyat": 100, "al-'adiyat": 100,
    "al-qariah": 101, "al-qari'ah": 101,
    "at-takathur": 102,
    "al-asr": 103,
    "al-humazah": 104,
    "al-fil": 105,
    "quraysh": 106,
    "al-maun": 107, "al-ma'un": 107,
    "al-kawthar": 108,
    "al-kafirun": 109,
    "an-nasr": 110,
    "al-masad": 111, "al-lahab": 111,
    "al-ikhlas": 112,
    "al-falaq": 113,
    "an-nas": 114, "al-nas": 114,
}


class AyahResolver:
    """Resolves Quranic references from free-text queries."""

    # Numeric patterns: "2:255", "2:255-257", "Surah 2, Verse 255"
    _NUMERIC = re.compile(
        r"\b(?:surah?\s+)?(\d{1,3})\s*[:/،]\s*(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?",
        re.IGNORECASE,
    )
    # Surah-only numeric: "Surah 112", "Sura 2"
    _SURAH_ONLY = re.compile(r"\bsur[ah]+\s+(\d{1,3})\b", re.IGNORECASE)

    def __init__(self, quran_ref: QuranRef) -> None:
        self._qr = quran_ref

    def resolve(self, text: str) -> list[AyahRef]:
        """Extract all Quranic references from a free-text query.

        Returns a deduplicated list of AyahRef objects.  If no references
        are found, returns an empty list (caller proceeds without a filter).
        """
        refs: list[AyahRef] = []
        seen: set[AyahRef] = set()
        lower = text.lower()

        # 1. Named verses (checked first — highest specificity)
        for name, (surah, start, end) in NAMED_VERSES.items():
            if name in lower:
                ref = AyahRef(surah=surah, ayah_start=start, ayah_end=end)
                if ref not in seen:
                    refs.append(ref)
                    seen.add(ref)

        # 2. Numeric surah:ayah references
        for m in self._NUMERIC.finditer(text):
            surah = int(m.group(1))
            ayah_start = int(m.group(2))
            ayah_end = int(m.group(3)) if m.group(3) else ayah_start
            if not self._valid(surah, ayah_start, ayah_end):
                logger.debug("Skipping out-of-range reference: %s", m.group(0))
                continue
            ref = AyahRef(surah=surah, ayah_start=ayah_start, ayah_end=ayah_end)
            if ref not in seen:
                refs.append(ref)
                seen.add(ref)

        # 3. Named surah references (e.g. "Al-Baqarah", "Surah Al-Ikhlas")
        for name, surah in SURAH_NAMES.items():
            if name in lower:
                # Only add a surah-level ref if no verse-level ref for same surah
                has_verse_level = any(r.surah == surah and not r.is_surah_only() for r in refs)
                if not has_verse_level:
                    ref = AyahRef(surah=surah, ayah_start=0, ayah_end=0)
                    if ref not in seen:
                        refs.append(ref)
                        seen.add(ref)

        # 4. Surah-only numeric (e.g. "Surah 112")
        for m in self._SURAH_ONLY.finditer(text):
            surah = int(m.group(1))
            if 1 <= surah <= 114:
                has_verse_level = any(r.surah == surah and not r.is_surah_only() for r in refs)
                if not has_verse_level:
                    ref = AyahRef(surah=surah, ayah_start=0, ayah_end=0)
                    if ref not in seen:
                        refs.append(ref)
                        seen.add(ref)

        if refs:
            logger.debug("Resolved %d reference(s) from query: %s", len(refs), refs)
        return refs

    def _valid(self, surah: int, ayah_start: int, ayah_end: int) -> bool:
        """Check that surah/ayah values are within the Quran's bounds."""
        try:
            total = self._qr.total_verses(surah)
            return 1 <= ayah_start <= total and 1 <= ayah_end <= total
        except KeyError:
            return False
