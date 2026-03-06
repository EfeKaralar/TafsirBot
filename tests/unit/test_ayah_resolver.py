"""
Unit tests for utils/ayah_resolver.py.

All tests run offline — no Qdrant, no API keys required.
QuranRef is loaded from the gittracked sources/quran-json/dist/ submodule.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Allow imports from scripts/ingestion/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ingestion"))

from utils.ayah_resolver import AyahRef, AyahResolver, NAMED_VERSES
from utils.quran_ref import QuranRef


@pytest.fixture(scope="module")
def resolver() -> AyahResolver:
    return AyahResolver(QuranRef())


# ── AyahRef dataclass ─────────────────────────────────────────────────────────

class TestAyahRef:
    def test_is_surah_only_true(self):
        assert AyahRef(surah=2, ayah_start=0, ayah_end=0).is_surah_only()

    def test_is_surah_only_false(self):
        assert not AyahRef(surah=2, ayah_start=255, ayah_end=255).is_surah_only()

    def test_as_filter_surah_only(self):
        f = AyahRef(surah=2, ayah_start=0, ayah_end=0).as_filter()
        assert f == {"must": [{"key": "surah_number", "match": {"value": 2}}]}

    def test_as_filter_single_ayah(self):
        f = AyahRef(surah=2, ayah_start=255, ayah_end=255).as_filter()
        assert {"key": "surah_number", "match": {"value": 2}} in f["must"]
        assert {"key": "ayah_start", "range": {"gte": 255}} in f["must"]
        assert {"key": "ayah_end", "range": {"lte": 255}} in f["must"]

    def test_as_filter_range(self):
        f = AyahRef(surah=55, ayah_start=1, ayah_end=4).as_filter()
        assert {"key": "ayah_start", "range": {"gte": 1}} in f["must"]
        assert {"key": "ayah_end", "range": {"lte": 4}} in f["must"]

    def test_frozen(self):
        ref = AyahRef(surah=2, ayah_start=255, ayah_end=255)
        with pytest.raises((AttributeError, TypeError)):
            ref.surah = 3  # type: ignore[misc]


# ── Named verse lookups ───────────────────────────────────────────────────────

class TestNamedVerses:
    @pytest.mark.parametrize("query,expected", [
        ("What is the meaning of Ayat al-Kursi?", AyahRef(2, 255, 255)),
        ("Explain the Verse of the Throne",       AyahRef(2, 255, 255)),
        ("Tell me about Ayatul Kursi",             AyahRef(2, 255, 255)),
        ("What is Ayat al Kursi?",                AyahRef(2, 255, 255)),
    ])
    def test_throne_verse_variants(self, resolver, query, expected):
        refs = resolver.resolve(query)
        assert expected in refs, f"Expected {expected} in {refs} for: {query!r}"

    @pytest.mark.parametrize("query,expected", [
        ("Commentary on Ayat al-Nur",   AyahRef(24, 35, 35)),
        ("What does the light verse say?", AyahRef(24, 35, 35)),
        ("Explain verse of light",      AyahRef(24, 35, 35)),
    ])
    def test_light_verse_variants(self, resolver, query, expected):
        refs = resolver.resolve(query)
        assert expected in refs, f"Expected {expected} in {refs} for: {query!r}"

    def test_al_fatiha_named(self, resolver):
        refs = resolver.resolve("What does Al-Fatiha mean?")
        assert AyahRef(1, 1, 7) in refs

    def test_al_ikhlas_named(self, resolver):
        refs = resolver.resolve("Commentary on Surah Al-Ikhlas")
        assert AyahRef(112, 1, 4) in refs

    def test_people_of_the_cave(self, resolver):
        refs = resolver.resolve("What is the meaning of the People of the Cave?")
        assert AyahRef(18, 9, 26) in refs

    def test_case_insensitive(self, resolver):
        refs_lower = resolver.resolve("ayat al-kursi")
        refs_upper = resolver.resolve("AYAT AL-KURSI")
        assert AyahRef(2, 255, 255) in refs_lower
        assert AyahRef(2, 255, 255) in refs_upper

    def test_named_verses_table_integrity(self):
        """Every entry in NAMED_VERSES must have valid surah (1-114) and non-negative ayahs."""
        for name, (surah, start, end) in NAMED_VERSES.items():
            assert 1 <= surah <= 114, f"{name!r}: surah={surah} out of range"
            assert 0 <= start <= end, f"{name!r}: start={start} end={end} invalid"


# ── Numeric references ────────────────────────────────────────────────────────

class TestNumericReferences:
    @pytest.mark.parametrize("query,expected", [
        ("Explain Quran 2:255",              AyahRef(2, 255, 255)),
        ("What does Ibn Kathir say about 2:286?", AyahRef(2, 286, 286)),
        ("Commentary on 24:35",             AyahRef(24, 35, 35)),
        ("Explain verse 67:1",              AyahRef(67, 1, 1)),
        ("What is 2:30 about?",             AyahRef(2, 30, 30)),
    ])
    def test_single_ayah_numeric(self, resolver, query, expected):
        refs = resolver.resolve(query)
        assert expected in refs, f"Expected {expected} in {refs} for: {query!r}"

    @pytest.mark.parametrize("query,expected", [
        ("What is the meaning of 112:1-4?", AyahRef(112, 1, 4)),
        ("What is 55:1-4 about?",           AyahRef(55, 1, 4)),
        ("Commentary on 2:255-257",         AyahRef(2, 255, 257)),
    ])
    def test_ayah_range_numeric(self, resolver, query, expected):
        refs = resolver.resolve(query)
        assert expected in refs, f"Expected {expected} in {refs} for: {query!r}"

    def test_out_of_range_surah_ignored(self, resolver):
        """Surah 115 does not exist — should be silently skipped."""
        refs = resolver.resolve("What is 115:1?")
        assert not any(r.surah == 115 for r in refs)

    def test_out_of_range_ayah_ignored(self, resolver):
        """Al-Fatiha has 7 ayahs — ayah 99 should be skipped."""
        refs = resolver.resolve("Explain 1:99")
        assert not any(r.surah == 1 and r.ayah_start == 99 for r in refs)

    def test_no_false_positive_plain_numbers(self, resolver):
        """A sentence like 'the 4 imams' should not resolve to surah:ayah."""
        refs = resolver.resolve("What did the 4 imams say about this?")
        # Should not produce any numeric verse refs
        verse_refs = [r for r in refs if not r.is_surah_only()]
        assert not verse_refs


# ── Surah-name references ─────────────────────────────────────────────────────

class TestSurahNameReferences:
    def test_al_baqarah_surah_level(self, resolver):
        refs = resolver.resolve("What is the theme of Al-Baqarah?")
        surah_refs = [r for r in refs if r.surah == 2]
        assert surah_refs, "Expected a surah-2 reference"
        # Should be surah-level (no specific ayah)
        assert any(r.is_surah_only() for r in surah_refs)

    def test_surah_name_does_not_override_verse_ref(self, resolver):
        """When a query has both 'Al-Baqarah' and '2:255', the verse ref wins; no surah-only for same surah."""
        refs = resolver.resolve("What does Al-Baqarah 2:255 say?")
        verse_ref = AyahRef(2, 255, 255)
        assert verse_ref in refs
        surah_only = AyahRef(2, 0, 0)
        assert surah_only not in refs

    def test_surah_only_numeric(self, resolver):
        refs = resolver.resolve("Commentary on Surah 112")
        assert AyahRef(112, 0, 0) in refs

    def test_surah_only_numeric_does_not_fire_without_keyword(self, resolver):
        """'112' alone should not resolve to surah 112."""
        refs = resolver.resolve("Tell me about 112 scholars")
        assert not any(r.surah == 112 and r.is_surah_only() for r in refs)


# ── Deduplication ─────────────────────────────────────────────────────────────

class TestDeduplication:
    def test_no_duplicate_refs(self, resolver):
        """Same reference mentioned twice should appear once."""
        refs = resolver.resolve("Explain 2:255 — also what does 2:255 mean?")
        count_255 = sum(1 for r in refs if r == AyahRef(2, 255, 255))
        assert count_255 == 1

    def test_named_and_numeric_same_verse_deduped(self, resolver):
        """Ayat al-Kursi and 2:255 in the same query → one entry."""
        refs = resolver.resolve("Ayat al-Kursi is 2:255 — explain it")
        count = sum(1 for r in refs if r == AyahRef(2, 255, 255))
        assert count == 1


# ── Empty / no-reference queries ─────────────────────────────────────────────

class TestNoReference:
    @pytest.mark.parametrize("query", [
        "What does the Quran say about tawakkul?",
        "Who was Ibn Kathir?",
        "What is Tafsir?",
        "What is the weather today?",
    ])
    def test_thematic_queries_return_empty(self, resolver, query):
        refs = resolver.resolve(query)
        assert refs == [], f"Expected no refs for: {query!r}, got {refs}"
