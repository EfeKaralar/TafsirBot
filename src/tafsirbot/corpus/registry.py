"""The corpus registry — one source of truth for scholars and hadith collections.

Loads ``registry.yaml``. Kept deliberately import-cheap: no BeautifulSoup, no
Qdrant, no OpenAI. The API imports this to serve ``GET /api/sources``, so it must
not drag in the ingestion stack.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml

from tafsirbot.errors import RegistryError

REGISTRY_PATH = Path(__file__).parent / "registry.yaml"

Kind = Literal["tafsir", "hadith"]
Status = Literal["available", "planned"]
Language = Literal["en", "ar"]


@dataclass(frozen=True, slots=True)
class Source:
    """One tafsir scholar or hadith collection."""

    id: str
    kind: Kind
    display_name: str
    source_title: str
    language: Language
    phase: int
    status: Status
    chunk_types: tuple[str, ...] = ()
    strip_isnad: bool = False
    madhab: str = "unspecified"

    @property
    def is_available(self) -> bool:
        return self.status == "available"


@dataclass(frozen=True, slots=True)
class Registry:
    """All known sources, indexed by id."""

    sources: dict[str, Source]

    def __getitem__(self, source_id: str) -> Source:
        try:
            return self.sources[source_id]
        except KeyError:
            raise RegistryError(
                f"Unknown source {source_id!r}. Known: {sorted(self.sources)}"
            ) from None

    def get(self, source_id: str) -> Source | None:
        return self.sources.get(source_id)

    def of_kind(self, kind: Kind) -> list[Source]:
        """Sources of one kind, ordered by phase then id for stable output."""
        return sorted(
            (s for s in self.sources.values() if s.kind == kind),
            key=lambda s: (s.phase, s.id),
        )

    @property
    def tafsir(self) -> list[Source]:
        return self.of_kind("tafsir")

    @property
    def hadith(self) -> list[Source]:
        return self.of_kind("hadith")

    def available_ids(self, kind: Kind | None = None) -> list[str]:
        """Ids of sources marked available, optionally restricted to one kind.

        Note this reflects the registry's *declaration*, not what is actually in
        Qdrant right now — the API cross-checks that separately.
        """
        return [
            s.id
            for s in sorted(self.sources.values(), key=lambda s: (s.phase, s.id))
            if s.is_available and (kind is None or s.kind == kind)
        ]

    def display_name(self, source_id: str) -> str:
        """Human-readable name, falling back to a titled id for unknown sources.

        Retrieval must never crash on an unexpected payload value, so this does not
        raise the way ``__getitem__`` does.
        """
        source = self.sources.get(source_id)
        if source is not None:
            return source.display_name
        return source_id.replace("_", " ").title()

    def validate_ids(self, source_ids: list[str], kind: Kind | None = None) -> list[str]:
        """Return ``source_ids`` unchanged, or raise if any is unknown or wrong-kind."""
        for sid in source_ids:
            source = self[sid]
            if kind is not None and source.kind != kind:
                raise RegistryError(f"Source {sid!r} is {source.kind}, expected {kind}")
        return source_ids


_REQUIRED = ("id", "display_name", "source_title", "language", "phase", "status")


def _parse_source(raw: dict, kind: Kind) -> Source:
    missing = [k for k in _REQUIRED if k not in raw]
    if missing:
        raise RegistryError(f"{kind} entry {raw.get('id', '<no id>')!r} missing keys: {missing}")

    status = raw["status"]
    if status not in ("available", "planned"):
        raise RegistryError(f"{raw['id']!r} has invalid status {status!r}")

    language = raw["language"]
    if language not in ("en", "ar"):
        raise RegistryError(f"{raw['id']!r} has invalid language {language!r}")

    return Source(
        id=raw["id"],
        kind=kind,
        display_name=raw["display_name"],
        source_title=raw["source_title"],
        language=language,
        phase=int(raw["phase"]),
        status=status,
        chunk_types=tuple(raw.get("chunk_types", ())),
        strip_isnad=bool(raw.get("strip_isnad", False)),
        madhab=raw.get("madhab", "unspecified"),
    )


def load_registry(path: Path | None = None) -> Registry:
    """Parse the registry YAML. Raises :class:`RegistryError` on any malformed entry."""
    path = path or REGISTRY_PATH
    if not path.is_file():
        raise RegistryError(f"Registry not found at {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RegistryError(f"Registry at {path} is not valid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise RegistryError(f"Registry at {path} must be a mapping of kind -> list")

    sources: dict[str, Source] = {}
    for kind in ("tafsir", "hadith"):
        for entry in raw.get(kind, []) or []:
            source = _parse_source(entry, kind)
            if source.id in sources:
                raise RegistryError(f"Duplicate source id {source.id!r}")
            sources[source.id] = source

    if not sources:
        raise RegistryError(f"Registry at {path} defines no sources")

    return Registry(sources=sources)


@lru_cache(maxsize=1)
def get_registry() -> Registry:
    """Process-wide cached registry."""
    return load_registry()


def display_name(source_id: str) -> str:
    """Convenience wrapper over the cached registry."""
    return get_registry().display_name(source_id)
