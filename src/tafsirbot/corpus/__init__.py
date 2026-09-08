"""Corpus domain: the source registry, Quran text lookup, and ayah reference parsing."""

from tafsirbot.corpus.quran import QuranRef
from tafsirbot.corpus.refs import AyahRef, AyahResolver
from tafsirbot.corpus.registry import Registry, Source, get_registry, load_registry

__all__ = [
    "AyahRef",
    "AyahResolver",
    "QuranRef",
    "Registry",
    "Source",
    "get_registry",
    "load_registry",
]
