"""
Unit tests for utils/quran_ref.py.

All tests run offline — data loaded from sources/quran-json/dist/quran_en.json
which is gittracked via the quran-json submodule.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ingestion"))

from utils.quran_ref import QuranRef


@pytest.fixture(scope="module")
def qr() -> QuranRef:
    return QuranRef()


# ── Loading ───────────────────────────────────────────────────────────────────

class TestLoading:
    def test_surah_count(self, qr):
        assert qr.surah_count == 114

    def test_ayah_count(self, qr):
        # Full Quran has 6,236 ayahs
        assert qr.ayah_count == 6236

    def test_bad_path_raises(self):
        with pytest.raises(FileNotFoundError):
            QuranRef(dist_dir="/nonexistent/path")


# ── get_ayah ──────────────────────────────────────────────────────────────────

class TestGetAyah:
    def test_returns_arabic_and_english(self, qr):
        ayah = qr.get_ayah(1, 1)
        assert "arabic_text" in ayah
        assert "english_text" in ayah
        assert len(ayah["arabic_text"]) > 0
        assert len(ayah["english_text"]) > 0

    def test_al_fatiha_first_ayah(self, qr):
        ayah = qr.get_ayah(1, 1)
        # Bismillah — should contain "Rahman" or "Merciful" in translation
        assert "merci" in ayah["english_text"].lower() or "rahman" in ayah["english_text"].lower()

    def test_ayat_al_kursi(self, qr):
        ayah = qr.get_ayah(2, 255)
        assert len(ayah["arabic_text"]) > 0
        # Should mention Throne or Kursi
        assert "throne" in ayah["english_text"].lower() or "kursi" in ayah["english_text"].lower()

    def test_last_ayah_of_last_surah(self, qr):
        # An-Nas has 6 ayahs
        ayah = qr.get_ayah(114, 6)
        assert len(ayah["arabic_text"]) > 0

    def test_invalid_surah_raises(self, qr):
        with pytest.raises(KeyError):
            qr.get_ayah(115, 1)

    def test_invalid_ayah_raises(self, qr):
        with pytest.raises(KeyError):
            qr.get_ayah(1, 99)  # Al-Fatiha has only 7 ayahs


# ── get_ayah_range ────────────────────────────────────────────────────────────

class TestGetAyahRange:
    def test_range_length(self, qr):
        ayahs = qr.get_ayah_range(1, 1, 7)
        assert len(ayahs) == 7

    def test_single_ayah_range(self, qr):
        ayahs = qr.get_ayah_range(2, 255, 255)
        assert len(ayahs) == 1

    def test_range_order(self, qr):
        ayahs = qr.get_ayah_range(112, 1, 4)
        assert len(ayahs) == 4
        # All should have content
        for a in ayahs:
            assert a["arabic_text"]

    def test_range_invalid_ayah_raises(self, qr):
        with pytest.raises(KeyError):
            qr.get_ayah_range(1, 1, 99)  # Al-Fatiha only has 7


# ── get_surah ─────────────────────────────────────────────────────────────────

class TestGetSurah:
    def test_al_fatiha(self, qr):
        s = qr.get_surah(1)
        assert s["id"] == 1
        assert s["total_verses"] == 7
        assert "fatiha" in s["transliteration"].lower() or "fatihah" in s["transliteration"].lower()

    def test_al_baqarah(self, qr):
        s = qr.get_surah(2)
        assert s["id"] == 2
        assert s["total_verses"] == 286

    def test_al_ikhlas(self, qr):
        s = qr.get_surah(112)
        assert s["total_verses"] == 4

    def test_an_nas(self, qr):
        s = qr.get_surah(114)
        assert s["total_verses"] == 6

    def test_invalid_surah_raises(self, qr):
        with pytest.raises(KeyError):
            qr.get_surah(115)


# ── total_verses / surah_name ─────────────────────────────────────────────────

class TestHelpers:
    def test_total_verses_al_fatiha(self, qr):
        assert qr.total_verses(1) == 7

    def test_total_verses_al_baqarah(self, qr):
        assert qr.total_verses(2) == 286

    def test_surah_name_returns_string(self, qr):
        name = qr.surah_name(2)
        assert isinstance(name, str)
        assert len(name) > 0

    def test_all_surahs_have_positive_verse_count(self, qr):
        for i in range(1, 115):
            assert qr.total_verses(i) > 0, f"Surah {i} has no verses"
