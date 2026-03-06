"""
Unit tests for ingestion/clean.py.

All tests run offline — no external services required.
Tests the per-scholar cleaning functions and shared utilities directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ingestion"))

from clean import (
    clean_ibn_kathir,
    clean_maududi,
    clean_tabari,
    clean_jalalayn,
    clean_qurtubi,
    _normalize_unicode,
    _strip_layout_artifacts,
    _split_isnad,
)


def _record(raw_text: str, chunk_type: str = "verse") -> dict:
    return {
        "surah": 2,
        "ayah_start": 255,
        "ayah_end": 255,
        "raw_text": raw_text,
        "chunk_type": chunk_type,
    }


# ── _normalize_unicode ────────────────────────────────────────────────────────

class TestNormalizeUnicode:
    def test_smart_quotes_replaced(self):
        result = _normalize_unicode("\u2018hello\u2019 and \u201cworld\u201d")
        assert result == "'hello' and \"world\""

    def test_em_dash_replaced(self):
        result = _normalize_unicode("word\u2014another")
        assert result == "word-another"

    def test_non_breaking_space_replaced(self):
        result = _normalize_unicode("hello\u00a0world")
        assert result == "hello world"

    def test_plain_ascii_unchanged(self):
        text = "Hello, world. This is a test."
        assert _normalize_unicode(text) == text


# ── _strip_layout_artifacts ───────────────────────────────────────────────────

class TestStripLayoutArtifacts:
    def test_removes_page_numbers(self):
        text = "Commentary here. [Page 42] More text."
        result = _strip_layout_artifacts(text)
        assert "Page 42" not in result
        assert "Commentary here" in result

    def test_removes_volume_markers(self):
        text = "Ibn Kathir said [Vol. 2, p. 100] that..."
        result = _strip_layout_artifacts(text)
        assert "Vol. 2" not in result

    def test_removes_footnote_brackets(self):
        text = "This is important.[1] See also note.[23]"
        result = _strip_layout_artifacts(text)
        assert "[1]" not in result
        assert "[23]" not in result

    def test_collapses_multiple_spaces(self):
        result = _strip_layout_artifacts("word     another")
        assert "  " not in result

    def test_collapses_excessive_newlines(self):
        result = _strip_layout_artifacts("para1\n\n\n\n\npara2")
        assert "\n\n\n" not in result

    def test_strips_leading_trailing_whitespace(self):
        result = _strip_layout_artifacts("   text   ")
        assert result == "text"


# ── _split_isnad ──────────────────────────────────────────────────────────────

class TestSplitIsnad:
    def test_clean_commentary_has_no_isnad(self):
        text = "Allah says in this verse that He is the Ever-Living. This is a statement of His eternal nature."
        matn, isnad = _split_isnad(text)
        assert len(matn) > 0
        assert isnad == ""

    def test_isnad_starter_splits_text(self):
        text = (
            "This verse refers to the greatness of Allah. "
            "It was narrated by Ibn Abbas that the Prophet said this is the greatest verse."
        )
        matn, isnad = _split_isnad(text)
        assert "This verse refers" in matn
        assert "Ibn Abbas" in isnad

    def test_recorded_by_pattern(self):
        text = "The meaning here is clear. (Recorded by Bukhari and Muslim.)"
        matn, isnad = _split_isnad(text)
        assert "Recorded by" in isnad

    def test_returns_full_text_when_no_isnad(self):
        text = "Allah is the Light of the heavens and the earth."
        matn, isnad = _split_isnad(text)
        assert matn == text
        assert isnad == ""

    def test_isnad_chain_text_not_in_matn(self):
        text = (
            "The word khalifa means successor. "
            "Ibn Masud said that this refers to Adam."
        )
        matn, isnad = _split_isnad(text)
        # Ibn Masud said... should go to isnad
        assert "Ibn Masud" not in matn or "Ibn Masud" in isnad


# ── clean_ibn_kathir ──────────────────────────────────────────────────────────

class TestCleanIbnKathir:
    def test_output_keys(self):
        result = clean_ibn_kathir(_record("Allah says this is the greatest verse."))
        assert "clean_text" in result
        assert "isnad_text" in result
        assert "chunk_type" in result

    def test_chunk_type_preserved(self):
        result = clean_ibn_kathir(_record("Some text."))
        assert result["chunk_type"] == "verse"

    def test_smart_quotes_normalized(self):
        result = clean_ibn_kathir(_record("He said \u2018this\u2019 clearly."))
        assert "\u2018" not in result["clean_text"]
        assert "\u2019" not in result["clean_text"]

    def test_page_markers_removed(self):
        result = clean_ibn_kathir(_record("Commentary. [Page 5] More commentary."))
        assert "Page 5" not in result["clean_text"]

    def test_isnad_stripped_to_isnad_field(self):
        text = (
            "Allah is described as Al-Hayy. "
            "It was narrated by Ibn Abbas that the Prophet explained this verse."
        )
        result = clean_ibn_kathir(_record(text))
        assert "Ibn Abbas" not in result["clean_text"] or "Ibn Abbas" in result["isnad_text"]

    def test_empty_text_falls_back_to_original(self):
        # If stripping produces empty matn, falls back to full text
        result = clean_ibn_kathir(_record("It was narrated by Ibn Abbas."))
        assert result["clean_text"]  # must not be empty

    def test_original_fields_preserved(self):
        record = _record("Some commentary.")
        result = clean_ibn_kathir(record)
        assert result["surah"] == 2
        assert result["ayah_start"] == 255


# ── clean_maududi ─────────────────────────────────────────────────────────────

class TestCleanMaududi:
    def test_output_keys(self):
        result = clean_maududi(_record("Maududi explains this verse."))
        assert "clean_text" in result
        assert result["isnad_text"] == ""

    def test_no_isnad_processing(self):
        text = "It was narrated by Ibn Abbas. Maududi says this means..."
        result = clean_maududi(_record(text))
        # Maududi cleaner does not strip isnads — full text goes to clean_text
        assert "Ibn Abbas" in result["clean_text"]
        assert result["isnad_text"] == ""

    def test_note_references_removed(self):
        result = clean_maududi(_record("This is Note 3 important context. Note 12 also see here."))
        assert "Note 3" not in result["clean_text"]
        assert "Note 12" not in result["clean_text"]

    def test_intro_chunk_type_preserved(self):
        record = {**_record("Intro text."), "chunk_type": "intro"}
        result = clean_maududi(record)
        assert result["chunk_type"] == "intro"

    def test_unicode_normalized(self):
        result = clean_maududi(_record("He said \u201cthis\u201d clearly."))
        assert "\u201c" not in result["clean_text"]


# ── clean_qurtubi chunk_type ──────────────────────────────────────────────────

class TestCleanQurtubi:
    def test_default_chunk_type_is_legal(self):
        # Pass a record without chunk_type so the cleaner's default ("legal") applies
        record = {"surah": 2, "ayah_start": 255, "ayah_end": 255, "raw_text": "Al-Qurtubi discusses the ruling on..."}
        result = clean_qurtubi(record)
        assert result["chunk_type"] == "legal"

    def test_explicit_chunk_type_preserved(self):
        record = {**_record("Text."), "chunk_type": "verse"}
        result = clean_qurtubi(record)
        assert result["chunk_type"] == "verse"


# ── cross-scholar: all cleaners produce required fields ──────────────────────

@pytest.mark.parametrize("cleaner", [
    clean_ibn_kathir,
    clean_maududi,
    clean_tabari,
    clean_jalalayn,
    clean_qurtubi,
])
def test_all_cleaners_produce_required_fields(cleaner):
    result = cleaner(_record("This is some commentary text about the verse."))
    assert "clean_text" in result
    assert "isnad_text" in result
    assert "chunk_type" in result
    assert isinstance(result["clean_text"], str)
    assert isinstance(result["isnad_text"], str)
