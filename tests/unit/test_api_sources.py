"""Tests for GET /api/sources and the Qdrant index probe.

First tests to touch ``scripts/api.py`` — it had none, because it constructed its own
clients at startup. These stub the runtime instead, which also lets us exercise the
probe's degraded path without Docker.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingestion"))


class FakeCount:
    def __init__(self, count: int) -> None:
        self.count = count


class FakeQdrant:
    """Reports points only for the source ids it was constructed with."""

    def __init__(self, populated: set[str], *, raises: bool = False) -> None:
        self.populated = populated
        self.raises = raises
        self.calls: list[tuple[str, str]] = []

    def count(self, *, collection_name, count_filter, exact):
        if self.raises:
            raise ConnectionError("qdrant unreachable")
        condition = count_filter.must[0]
        value = condition.match.value
        self.calls.append((collection_name, value))
        return FakeCount(1 if value in self.populated else 0)


def _runtime(qdrant) -> dict:
    return {
        "clients": {"anthropic": object(), "openai": object()},
        "qdrant_client": qdrant,
        "collection": "tafsir",
        "hadith_collection": "hadith",
        "resolver": object(),
        "sparse_model": object(),
    }


@pytest.fixture
def api():
    import api as api_module

    return api_module


class TestProbeIndexedSources:
    def test_reports_populated_sources(self, api) -> None:
        probe = api._probe_indexed_sources(_runtime(FakeQdrant({"ibn_kathir", "maududi"})))
        assert probe["ibn_kathir"] is True
        assert probe["maududi"] is True
        assert probe["qurtubi"] is False

    def test_probes_correct_collection_and_payload_key(self, api) -> None:
        """Tafsir is keyed on `scholar`; hadith on `collection`. Mixing them silently
        reports everything as unindexed."""
        fake = FakeQdrant({"ibn_kathir"})
        api._probe_indexed_sources(_runtime(fake))
        assert ("tafsir", "ibn_kathir") in fake.calls
        assert ("hadith", "bukhari") in fake.calls

    def test_degrades_to_false_when_qdrant_is_down(self, api) -> None:
        """Must not block startup — the API still serves with Qdrant unreachable."""
        probe = api._probe_indexed_sources(_runtime(FakeQdrant(set(), raises=True)))
        assert probe
        assert all(v is False for v in probe.values())

    def test_handles_missing_hadith_collection(self, api) -> None:
        runtime = _runtime(FakeQdrant({"ibn_kathir"}))
        runtime["hadith_collection"] = None
        probe = api._probe_indexed_sources(runtime)
        assert probe["bukhari"] is False
        assert probe["ibn_kathir"] is True


class TestSourcesEndpoint:
    def _client(self, api, qdrant):
        from fastapi.testclient import TestClient

        api.app.state.runtime = _runtime(qdrant)
        api.app.state.persistence = None
        api.app.state.indexed_sources = api._probe_indexed_sources(api.app.state.runtime)
        # Bypass lifespan: it would call build_runtime() and need live services.
        return TestClient(api.app)

    def test_returns_both_kinds(self, api) -> None:
        client = self._client(api, FakeQdrant({"ibn_kathir", "maududi"}))
        body = client.get("/api/sources").json()
        assert {s["id"] for s in body["tafsir"]} >= {"ibn_kathir", "maududi", "qurtubi"}
        assert {s["id"] for s in body["hadith"]} >= {"bukhari", "muslim"}

    def test_available_scholars_are_marked_indexed(self, api) -> None:
        client = self._client(api, FakeQdrant({"ibn_kathir", "maududi"}))
        by_id = {s["id"]: s for s in client.get("/api/sources").json()["tafsir"]}
        assert by_id["ibn_kathir"]["status"] == "available"
        assert by_id["ibn_kathir"]["indexed"] is True
        assert by_id["qurtubi"]["status"] == "planned"
        assert by_id["qurtubi"]["indexed"] is False

    def test_status_and_indexed_can_disagree(self, api) -> None:
        """A source declared available but not upserted. The UI trusts `indexed`."""
        client = self._client(api, FakeQdrant(set()))
        by_id = {s["id"]: s for s in client.get("/api/sources").json()["tafsir"]}
        assert by_id["ibn_kathir"]["status"] == "available"
        assert by_id["ibn_kathir"]["indexed"] is False

    def test_includes_display_labels_from_registry(self, api) -> None:
        client = self._client(api, FakeQdrant({"ibn_kathir"}))
        by_id = {s["id"]: s for s in client.get("/api/sources").json()["tafsir"]}
        assert by_id["ibn_kathir"]["label"] == "Ibn Kathir"
        assert by_id["qurtubi"]["label"] == "Al-Qurtubi"

    def test_reports_providers_and_defaults(self, api) -> None:
        client = self._client(api, FakeQdrant({"ibn_kathir"}))
        body = client.get("/api/sources").json()
        assert set(body["providers"]) == {"anthropic", "openai"}
        assert body["defaults"]["top_k"] == 5

    def test_hadith_ordering_is_stable(self, api) -> None:
        """Generated docs and UI both depend on deterministic ordering."""
        client = self._client(api, FakeQdrant(set()))
        ids = [s["id"] for s in client.get("/api/sources").json()["hadith"]]
        assert ids == sorted(ids)
