"""Compatibility shim — moved to ``tafsirbot.corpus.quran``.

Re-export only, zero logic. Kept so the ingestion scripts and existing unit tests
keep working unchanged during epic #38. Deleted when ingestion moves into the
package (PR #37).

New code must import from ``tafsirbot.corpus.quran``.
"""

from tafsirbot.corpus.quran import AyahData, QuranRef, SurahData

__all__ = ["AyahData", "QuranRef", "SurahData"]
