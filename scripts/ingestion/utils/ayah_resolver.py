"""Compatibility shim — moved to ``tafsirbot.corpus.refs``.

Re-export only, zero logic. Kept so the ingestion scripts and existing unit tests
keep working unchanged during epic #38. Deleted when ingestion moves into the
package (PR #37).

New code must import from ``tafsirbot.corpus.refs``.
"""

from tafsirbot.corpus.refs import (
    NAMED_VERSES,
    SURAH_NAMES,
    AyahRef,
    AyahResolver,
)

__all__ = ["NAMED_VERSES", "SURAH_NAMES", "AyahRef", "AyahResolver"]
