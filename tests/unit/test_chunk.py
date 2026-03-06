"""
Unit tests for ingestion/chunk.py.

All tests run offline — QuranRef loaded from gittracked quran-json submodule.
Tests the chunk assembly logic (_quran_texts, process_scholar) directly.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ingestion"))

from chunk import _quran_texts, process_scholar, SCHOLAR_META
from utils.quran_ref import QuranRef


@pytest.fixture(scope="module")
def qr() -> QuranRef:
    return QuranRef()


# ── _quran_texts ──────────────────────────────────────────────────────────────

class TestQuranTexts:
    def test_single_ayah_returns_texts(self, qr):
        arabic, english = _quran_texts(qr, 2, 255, 255)
        assert len(arabic) > 0
        assert len(english) > 0

    def test_intro_chunk_returns_empty_strings(self, qr):
        arabic, english = _quran_texts(qr, 2, 0, 0)
        assert arabic == ""
        assert english == ""

    def test_range_concatenates_texts(self, qr):
        arabic, english = _quran_texts(qr, 1, 1, 7)
        # Al-Fatiha has 7 ayahs; joined with spaces → longer than any single ayah
        arabic_single, _ = _quran_texts(qr, 1, 1, 1)
        assert len(arabic) > len(arabic_single)

    def test_range_returns_space_separated(self, qr):
        arabic, english = _quran_texts(qr, 112, 1, 4)
        # Multiple ayahs joined with spaces — should have multiple words
        assert " " in english

    def test_invalid_ayah_skipped_gracefully(self, qr):
        # Ayah 99 doesn't exist in Al-Fatiha (7 ayahs) — should not raise
        arabic, english = _quran_texts(qr, 1, 1, 8)
        # Should return texts for ayahs 1-7, silently skip 8
        assert len(arabic) > 0


# ── SCHOLAR_META ──────────────────────────────────────────────────────────────

class TestScholarMeta:
    def test_all_required_keys_present(self):
        required = {"scholar", "language", "source_title"}
        for name, meta in SCHOLAR_META.items():
            missing = required - set(meta.keys())
            assert not missing, f"Scholar '{name}' missing keys: {missing}"

    def test_phase1_scholars_present(self):
        assert "ibn_kathir" in SCHOLAR_META
        assert "maududi" in SCHOLAR_META

    def test_ibn_kathir_is_english(self):
        assert SCHOLAR_META["ibn_kathir"]["language"] == "en"

    def test_maududi_is_english(self):
        assert SCHOLAR_META["maududi"]["language"] == "en"


# ── process_scholar (integration with temp dirs) ──────────────────────────────

def _write_cleaned_record(directory: Path, filename: str, records: list[dict]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / filename).open("w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


class TestProcessScholar:
    def test_verse_chunk_has_all_fields(self, qr, tmp_path):
        cleaned_dir = tmp_path / "cleaned" / "ibn_kathir"
        chunks_dir = tmp_path / "chunks"
        _write_cleaned_record(cleaned_dir, "002.jsonl", [
            {
                "surah": 2,
                "ayah_start": 255,
                "ayah_end": 255,
                "clean_text": "Allah — there is no deity except Him, the Ever-Living.",
                "chunk_type": "verse",
                "isnad_text": "",
            }
        ])

        # Patch the module-level dirs temporarily
        import chunk as chunk_mod
        orig_cleaned = chunk_mod.CLEANED_DIR
        orig_chunks = chunk_mod.CHUNKS_DIR
        chunk_mod.CLEANED_DIR = tmp_path / "cleaned"
        chunk_mod.CHUNKS_DIR = chunks_dir
        try:
            process_scholar("ibn_kathir", qr)
        finally:
            chunk_mod.CLEANED_DIR = orig_cleaned
            chunk_mod.CHUNKS_DIR = orig_chunks

        output = chunks_dir / "ibn_kathir.jsonl"
        assert output.exists()
        records = [json.loads(line) for line in output.read_text().splitlines()]
        assert len(records) == 1

        rec = records[0]
        required_fields = {
            "content", "surah_number", "ayah_start", "ayah_end",
            "scholar", "language", "source_title",
            "english_text", "arabic_text", "chunk_type", "isnad_text",
        }
        assert required_fields.issubset(rec.keys())

    def test_intro_chunk_has_empty_quran_texts(self, qr, tmp_path):
        cleaned_dir = tmp_path / "cleaned" / "maududi"
        chunks_dir = tmp_path / "chunks"
        _write_cleaned_record(cleaned_dir, "002.jsonl", [
            {
                "surah": 2,
                "ayah_start": 0,
                "ayah_end": 0,
                "clean_text": "This surah was revealed in Madinah and covers themes of...",
                "chunk_type": "intro",
                "isnad_text": "",
            }
        ])

        import chunk as chunk_mod
        orig_cleaned = chunk_mod.CLEANED_DIR
        orig_chunks = chunk_mod.CHUNKS_DIR
        chunk_mod.CLEANED_DIR = tmp_path / "cleaned"
        chunk_mod.CHUNKS_DIR = chunks_dir
        try:
            process_scholar("maududi", qr)
        finally:
            chunk_mod.CLEANED_DIR = orig_cleaned
            chunk_mod.CHUNKS_DIR = orig_chunks

        output = chunks_dir / "maududi.jsonl"
        records = [json.loads(line) for line in output.read_text().splitlines()]
        assert len(records) == 1
        rec = records[0]
        assert rec["chunk_type"] == "intro"
        assert rec["arabic_text"] == ""
        assert rec["english_text"] == ""
        assert rec["ayah_start"] == 0

    def test_empty_clean_text_skipped(self, qr, tmp_path):
        cleaned_dir = tmp_path / "cleaned" / "ibn_kathir"
        chunks_dir = tmp_path / "chunks"
        _write_cleaned_record(cleaned_dir, "002.jsonl", [
            {
                "surah": 2,
                "ayah_start": 255,
                "ayah_end": 255,
                "clean_text": "",
                "chunk_type": "verse",
                "isnad_text": "",
            }
        ])

        import chunk as chunk_mod
        orig_cleaned = chunk_mod.CLEANED_DIR
        orig_chunks = chunk_mod.CHUNKS_DIR
        chunk_mod.CLEANED_DIR = tmp_path / "cleaned"
        chunk_mod.CHUNKS_DIR = chunks_dir
        try:
            process_scholar("ibn_kathir", qr)
        finally:
            chunk_mod.CLEANED_DIR = orig_cleaned
            chunk_mod.CHUNKS_DIR = orig_chunks

        output = chunks_dir / "ibn_kathir.jsonl"
        if output.exists():
            records = [json.loads(line) for line in output.read_text().splitlines() if line.strip()]
            assert len(records) == 0

    def test_scholar_metadata_applied(self, qr, tmp_path):
        cleaned_dir = tmp_path / "cleaned" / "maududi"
        chunks_dir = tmp_path / "chunks"
        _write_cleaned_record(cleaned_dir, "001.jsonl", [
            {
                "surah": 1,
                "ayah_start": 1,
                "ayah_end": 1,
                "clean_text": "Maududi explains the opening.",
                "chunk_type": "verse",
                "isnad_text": "",
            }
        ])

        import chunk as chunk_mod
        orig_cleaned = chunk_mod.CLEANED_DIR
        orig_chunks = chunk_mod.CHUNKS_DIR
        chunk_mod.CLEANED_DIR = tmp_path / "cleaned"
        chunk_mod.CHUNKS_DIR = chunks_dir
        try:
            process_scholar("maududi", qr)
        finally:
            chunk_mod.CLEANED_DIR = orig_cleaned
            chunk_mod.CHUNKS_DIR = orig_chunks

        output = chunks_dir / "maududi.jsonl"
        rec = json.loads(output.read_text().strip())
        assert rec["scholar"] == "maududi"
        assert rec["language"] == "en"
        assert "Tafhim" in rec["source_title"]
