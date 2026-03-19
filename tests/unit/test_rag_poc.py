"""
Unit tests for rag_poc.py helper functions.

All tests run offline — no Qdrant, no API keys, no LLM calls required.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ingestion"))

import rag_poc
from rag_poc import build_qdrant_filter
from utils.ayah_resolver import AyahRef


# ── build_qdrant_filter ───────────────────────────────────────────────────────


class TestBuildQdrantFilterNoRefs:
    """Behaviour when no ayah refs are present."""

    def test_no_refs_no_scholars_returns_none(self):
        assert build_qdrant_filter([], scholars=None) is None

    def test_no_refs_empty_scholars_returns_none(self):
        assert build_qdrant_filter([], scholars=[]) is None

    def test_no_refs_single_scholar(self):
        result = build_qdrant_filter([], scholars=["ibn_kathir"])
        assert result == {
            "must": [{"key": "scholar", "match": {"value": "ibn_kathir"}}]
        }

    def test_no_refs_two_scholars_produces_should(self):
        result = build_qdrant_filter([], scholars=["ibn_kathir", "maududi"])
        assert result is not None
        must = result["must"]
        assert len(must) == 1
        should_block = must[0]
        assert "should" in should_block
        values = {c["match"]["value"] for c in should_block["should"]}
        assert values == {"ibn_kathir", "maududi"}

    def test_no_refs_three_scholars_produces_should(self):
        result = build_qdrant_filter([], scholars=["ibn_kathir", "maududi", "qurtubi"])
        should_block = result["must"][0]
        values = {c["match"]["value"] for c in should_block["should"]}
        assert values == {"ibn_kathir", "maududi", "qurtubi"}


class TestBuildQdrantFilterWithRef:
    """Behaviour when an ayah ref is resolved."""

    @pytest.fixture
    def single_ayah_ref(self):
        return [AyahRef(surah=2, ayah_start=255, ayah_end=255)]

    @pytest.fixture
    def surah_only_ref(self):
        return [AyahRef(surah=2, ayah_start=0, ayah_end=0)]

    def test_ref_no_scholars(self, single_ayah_ref):
        result = build_qdrant_filter(single_ayah_ref, scholars=None)
        assert result is not None
        must = result["must"]
        keys = [c["key"] for c in must]
        assert "surah_number" in keys
        assert "ayah_start" in keys
        assert "ayah_end" in keys

    def test_ref_single_scholar_combined(self, single_ayah_ref):
        result = build_qdrant_filter(single_ayah_ref, scholars=["maududi"])
        assert result is not None
        must = result["must"]
        # Scholar condition + surah + ayah_start + ayah_end = 4
        assert len(must) == 4
        scholar_cond = next(c for c in must if c.get("key") == "scholar")
        assert scholar_cond["match"]["value"] == "maududi"

    def test_ref_multi_scholar_combined(self, single_ayah_ref):
        result = build_qdrant_filter(single_ayah_ref, scholars=["ibn_kathir", "maududi"])
        assert result is not None
        must = result["must"]
        # should block + surah + ayah_start + ayah_end = 4
        assert len(must) == 4
        should_block = next(c for c in must if "should" in c)
        values = {c["match"]["value"] for c in should_block["should"]}
        assert values == {"ibn_kathir", "maududi"}

    def test_surah_only_ref_no_ayah_conditions(self, surah_only_ref):
        result = build_qdrant_filter(surah_only_ref, scholars=None)
        assert result is not None
        must = result["must"]
        keys = [c.get("key") for c in must]
        assert "surah_number" in keys
        assert "ayah_start" not in keys
        assert "ayah_end" not in keys

    def test_ref_correct_surah_value(self, single_ayah_ref):
        result = build_qdrant_filter(single_ayah_ref, scholars=None)
        surah_cond = next(c for c in result["must"] if c.get("key") == "surah_number")
        assert surah_cond["match"]["value"] == 2

    def test_ref_correct_ayah_range(self, single_ayah_ref):
        result = build_qdrant_filter(single_ayah_ref, scholars=None)
        start_cond = next(c for c in result["must"] if c.get("key") == "ayah_start")
        end_cond = next(c for c in result["must"] if c.get("key") == "ayah_end")
        assert start_cond["range"]["gte"] == 255
        assert end_cond["range"]["lte"] == 255


# ── normalize ─────────────────────────────────────────────────────────────────


class TestNormalize:
    def test_strips_mentions(self):
        assert "@TafsirBot" not in rag_poc.normalize("@TafsirBot what is 2:255?")

    def test_strips_hashtags(self):
        assert "#Islam" not in rag_poc.normalize("What is tawakkul? #Islam")

    def test_collapses_whitespace(self):
        result = rag_poc.normalize("What   is   this?")
        assert "  " not in result

    def test_strips_leading_trailing(self):
        assert rag_poc.normalize("  hello  ") == "hello"

    def test_empty_string(self):
        assert rag_poc.normalize("") == ""


# ── extract_citations ─────────────────────────────────────────────────────────


class TestExtractCitations:
    def test_finds_single_citation(self):
        text = "According to [Ibn Kathir on 2:255], the verse..."
        assert rag_poc.extract_citations(text) == ["[Ibn Kathir on 2:255]"]

    def test_finds_multiple_citations(self):
        text = "[Ibn Kathir on 2:255] and [Maududi on 2:255]"
        citations = rag_poc.extract_citations(text)
        assert len(citations) == 2

    def test_no_citations(self):
        assert rag_poc.extract_citations("No citations here.") == []

    def test_ignores_malformed(self):
        assert rag_poc.extract_citations("[Ibn Kathir 2:255]") == []
