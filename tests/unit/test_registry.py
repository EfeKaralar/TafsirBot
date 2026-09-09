"""Tests for the corpus registry — the single source of truth for sources.

Six places previously duplicated this data. These tests pin the invariants the rest
of the system relies on, and assert the generated docs stay in sync.
"""

from __future__ import annotations

import textwrap

import pytest

from tafsirbot.corpus.registry import Registry, load_registry
from tafsirbot.errors import RegistryError


class TestLoading:
    def test_loads_real_registry(self, registry: Registry) -> None:
        assert registry.sources
        assert "ibn_kathir" in registry.sources
        assert "bukhari" in registry.sources

    def test_phase_1_scholars_are_available(self, registry: Registry) -> None:
        """Ibn Kathir and Maududi are the ingested corpus — see CLAUDE.md."""
        assert registry["ibn_kathir"].is_available
        assert registry["maududi"].is_available

    def test_no_hadith_is_available_yet(self, registry: Registry) -> None:
        """Hadith is Phase 3. If this fails, hadith was ingested and docs need updating."""
        assert all(not s.is_available for s in registry.hadith)

    def test_kinds_are_disjoint(self, registry: Registry) -> None:
        tafsir_ids = {s.id for s in registry.tafsir}
        hadith_ids = {s.id for s in registry.hadith}
        assert not (tafsir_ids & hadith_ids)

    def test_of_kind_is_ordered_by_phase_then_id(self, registry: Registry) -> None:
        """Stable ordering matters: the generated docs and API output depend on it."""
        keys = [(s.phase, s.id) for s in registry.tafsir]
        assert keys == sorted(keys)

    def test_unknown_id_raises(self, registry: Registry) -> None:
        with pytest.raises(RegistryError, match="Unknown source"):
            registry["no_such_scholar"]

    def test_get_returns_none_for_unknown(self, registry: Registry) -> None:
        assert registry.get("no_such_scholar") is None


class TestDisplayName:
    """Replaces rag_poc._scholar_display, which was a hardcoded dict."""

    def test_known_ids(self, registry: Registry) -> None:
        assert registry.display_name("ibn_kathir") == "Ibn Kathir"
        assert registry.display_name("qurtubi") == "Al-Qurtubi"
        assert registry.display_name("ibn_ashur") == "Ibn Ashur"

    def test_unknown_id_falls_back_instead_of_raising(self, registry: Registry) -> None:
        """Retrieval must not crash on an unexpected payload value."""
        assert registry.display_name("some_new_scholar") == "Some New Scholar"


class TestAvailableIds:
    def test_filters_by_status(self, registry: Registry) -> None:
        available = registry.available_ids()
        assert "ibn_kathir" in available
        assert "qurtubi" not in available

    def test_filters_by_kind(self, registry: Registry) -> None:
        assert registry.available_ids(kind="hadith") == []
        assert set(registry.available_ids(kind="tafsir")) == {"ibn_kathir", "maududi"}


class TestValidateIds:
    def test_accepts_known_ids(self, registry: Registry) -> None:
        assert registry.validate_ids(["ibn_kathir", "maududi"]) == ["ibn_kathir", "maududi"]

    def test_rejects_unknown_id(self, registry: Registry) -> None:
        with pytest.raises(RegistryError, match="Unknown source"):
            registry.validate_ids(["ibn_kathir", "nope"])

    def test_rejects_wrong_kind(self, registry: Registry) -> None:
        with pytest.raises(RegistryError, match="is hadith, expected tafsir"):
            registry.validate_ids(["bukhari"], kind="tafsir")


class TestMalformedRegistry:
    def _write(self, tmp_path, body: str):
        path = tmp_path / "registry.yaml"
        path.write_text(textwrap.dedent(body), encoding="utf-8")
        return path

    def test_missing_file(self, tmp_path) -> None:
        with pytest.raises(RegistryError, match="not found"):
            load_registry(tmp_path / "absent.yaml")

    def test_missing_required_key(self, tmp_path) -> None:
        path = self._write(tmp_path, """
            tafsir:
              - id: x
                display_name: X
        """)
        with pytest.raises(RegistryError, match="missing keys"):
            load_registry(path)

    def test_invalid_status(self, tmp_path) -> None:
        path = self._write(tmp_path, """
            tafsir:
              - id: x
                display_name: X
                source_title: X
                language: en
                phase: 1
                status: maybe
        """)
        with pytest.raises(RegistryError, match="invalid status"):
            load_registry(path)

    def test_invalid_language(self, tmp_path) -> None:
        path = self._write(tmp_path, """
            tafsir:
              - id: x
                display_name: X
                source_title: X
                language: fr
                phase: 1
                status: planned
        """)
        with pytest.raises(RegistryError, match="invalid language"):
            load_registry(path)

    def test_duplicate_id_across_kinds(self, tmp_path) -> None:
        path = self._write(tmp_path, """
            tafsir:
              - id: dup
                display_name: A
                source_title: A
                language: en
                phase: 1
                status: planned
            hadith:
              - id: dup
                display_name: B
                source_title: B
                language: en
                phase: 3
                status: planned
        """)
        with pytest.raises(RegistryError, match="Duplicate source id"):
            load_registry(path)

    def test_empty_registry(self, tmp_path) -> None:
        path = self._write(tmp_path, "tafsir: []\nhadith: []\n")
        with pytest.raises(RegistryError, match="defines no sources"):
            load_registry(path)

    def test_not_a_mapping(self, tmp_path) -> None:
        path = self._write(tmp_path, "- just\n- a\n- list\n")
        with pytest.raises(RegistryError, match="must be a mapping"):
            load_registry(path)


class TestGeneratedDocsInSync:
    """docs/CORPUS-REGISTRY.md is generated — editing the YAML without regenerating fails here."""

    def test_corpus_registry_md_is_current(self, registry: Registry, repo_root) -> None:
        import sys

        sys.path.insert(0, str(repo_root / "scripts"))
        from gen_corpus_docs import DOC_PATH, render

        current = DOC_PATH.read_text(encoding="utf-8")
        assert current == render(registry, current), (
            "docs/CORPUS-REGISTRY.md is out of sync with registry.yaml. "
            "Run: uv run python scripts/gen_corpus_docs.py"
        )
