"""
test_poc.py — End-to-end test runner for the TafsirBot RAG POC.

Tests the full pipeline (intent → retrieval → generation) against a curated
query set and asserts expected behaviour:

  - tafsir / general_islamic queries  → response must contain at least one
    [Scholar on X:Y] citation
  - fiqh_ruling / off_topic queries   → must be refused (no tafsir content)

The expected_category column is what *should* happen.  If the intent
classifier disagrees, the test is marked FAIL (classifier error).

Usage:
    uv run python scripts/test_poc.py                   # full suite
    uv run python scripts/test_poc.py --quick           # 12 queries (2 API calls each)
    uv run python scripts/test_poc.py --verbose         # show full responses
    uv run python scripts/test_poc.py --provider openai # use GPT-4o
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Re-use pipeline functions from rag_poc without duplicating them.
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "ingestion"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import rag_poc  # noqa: E402 — imports after path/env setup


# ── Test cases ────────────────────────────────────────────────────────────────

Category = Literal["tafsir", "general_islamic", "refuse"]


@dataclass
class TestCase:
    query: str
    expected: Category
    note: str = ""


# fmt: off
ALL_CASES: list[TestCase] = [
    # Named ayah references
    TestCase("What is the meaning of Ayat al-Kursi?",           "tafsir",          "named verse — Throne Verse"),
    TestCase("Explain the Verse of the Throne",                  "tafsir",          "synonym for Ayat al-Kursi"),
    TestCase("Commentary on Surah Al-Ikhlas",                    "tafsir",          "short surah, all scholars cover it"),
    TestCase("What does Al-Fatiha mean?",                        "tafsir",          "opening surah"),
    TestCase("What does Ibn Kathir say about Ayat al-Nur?",      "tafsir",          "light verse 24:35"),

    # Numeric ayah references
    TestCase("Explain Quran 2:255",                              "tafsir",          "Throne Verse numeric ref"),
    TestCase("What does Ibn Kathir say about 2:286?",            "tafsir",          "last verse of Al-Baqarah"),
    TestCase("Commentary on 24:35",                              "tafsir",          "light verse numeric ref"),
    TestCase("What is 2:30 about?",                              "tafsir",          "khalifa verse"),
    TestCase("Explain verse 67:1",                               "tafsir",          "Al-Mulk opening"),

    # Thematic
    TestCase("What does the Quran say about tawakkul?",          "tafsir",          "trust in Allah — multi-verse"),
    TestCase("What do scholars say about taqwa?",                "tafsir",          "God-consciousness"),
    TestCase("What does the Quran say about the Day of Judgment?","tafsir",         "eschatological theme"),
    TestCase("Commentary on the description of Paradise",         "tafsir",         "cross-verse thematic"),
    TestCase("What is the Quranic view of creation?",            "tafsir",          "cosmological theme"),

    # Linguistic / conceptual
    TestCase("What does 'khalifa' mean in Quran 2:30?",          "tafsir",          "word meaning with ayah ref"),
    TestCase("What does 'iqra' mean in the first revelation?",   "tafsir",          "first word revealed"),

    # General Islamic (not verse-specific but answerable)
    TestCase("Who was Ibn Kathir?",                              "general_islamic", "scholar biography"),
    TestCase("What is Tafsir?",                                  "general_islamic", "discipline overview"),

    # Fiqh-adjacent — should respond with scholarly info, not refuse
    TestCase("Is it halal to eat shellfish?",                    "tafsir",          "fiqh-adjacent, should retrieve relevant verses"),
    TestCase("What is the Islamic view on music?",               "general_islamic", "scholarly perspective, not personal ruling"),
    TestCase("What is the Islamic position on abortion?",        "general_islamic", "multi-madhab scholarly view"),

    # Personal fiqh requests — first-person, actionable
    TestCase("Can I pray with nail polish?",                     "refuse",          "first-person fiqh ruling"),
    TestCase("Am I allowed to take out a mortgage?",             "refuse",          "first-person fiqh ruling"),

    # Off-topic — must be refused
    TestCase("What is the weather today?",                       "refuse",          "off-topic — non-Islamic"),
    TestCase("Who is the best football player?",                 "refuse",          "off-topic — sports"),
]
# fmt: on

QUICK_CASES: list[TestCase] = [
    ALL_CASES[0],   # Ayat al-Kursi (named)
    ALL_CASES[5],   # 2:255 (numeric)
    ALL_CASES[10],  # tawakkul (thematic)
    ALL_CASES[15],  # khalifa meaning (linguistic)
    ALL_CASES[17],  # Who was Ibn Kathir (general)
    ALL_CASES[19],  # Is shellfish halal (fiqh-adjacent, should respond)
    ALL_CASES[20],  # music — scholarly view (fiqh-adjacent)
    ALL_CASES[21],  # abortion — scholarly view (fiqh-adjacent)
    ALL_CASES[22],  # Can I pray with nail polish (first-person → refuse)
    ALL_CASES[24],  # weather (off-topic → refuse)
]


# ── Assertions ────────────────────────────────────────────────────────────────

CITATION_RE = re.compile(r"\[[^\]]+\s+on\s+[^\]]+\]", re.IGNORECASE)

REFUSAL_PHRASES = (
    "can only answer questions about",  # OFF_TOPIC_REFUSAL
)


def check_result(
    case: TestCase,
    intent: str,
    response_text: str | None,
) -> tuple[bool, str]:
    """
    Returns (passed, reason).
    response_text is None when the pipeline refused before LLM generation.
    """
    if case.expected == "refuse":
        # Only off_topic is a hard refusal now; fiqh_ruling still generates a response
        if intent != "off_topic":
            return False, f"expected off_topic refusal but intent={intent!r}"
        if response_text is not None and not any(
            p in response_text.lower() for p in REFUSAL_PHRASES
        ):
            return False, "refusal message not found in output"
        return True, "correctly refused"

    # tafsir / general_islamic / fiqh_ruling — expect a generated response with citations
    if intent == "off_topic":
        return False, f"expected content but off_topic caused refusal"
    if response_text is None:
        return False, "no response generated"
    citations = CITATION_RE.findall(response_text)
    if not citations:
        return False, "response contains no citations"
    return True, f"{len(citations)} citation(s): {citations[0]}"


# ── Runner ────────────────────────────────────────────────────────────────────

def run_tests(cases: list[TestCase], provider: str, verbose: bool) -> None:
    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient
    import openai as _openai

    clients: dict = {}
    clients["openai"] = _openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    if provider == "anthropic":
        import anthropic as _anthropic
        clients["anthropic"] = _anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"]
        )

    qdrant = QdrantClient(
        host=os.environ.get("QDRANT_HOST", "localhost"),
        port=int(os.environ.get("QDRANT_PORT", 6333)),
    )
    collection = os.environ.get("QDRANT_COLLECTION", "tafsir")

    from utils.quran_ref import QuranRef
    from utils.ayah_resolver import AyahResolver

    qr = QuranRef()
    resolver = AyahResolver(qr)
    sparse_model = SparseTextEmbedding(rag_poc.SPARSE_MODEL_NAME
                                       if hasattr(rag_poc, "SPARSE_MODEL_NAME")
                                       else "Qdrant/bm42-all-minilm-l6-v2-attentions")

    passed = 0
    failed = 0
    rows: list[tuple[str, str, str, str]] = []  # status, query, intent, reason

    print(f"\n{'='*72}")
    print(f"TafsirBot POC — End-to-end test  |  provider={provider}  n={len(cases)}")
    print(f"{'='*72}\n")

    for i, case in enumerate(cases, 1):
        query = rag_poc.normalize(case.query)
        intent = rag_poc.classify_intent(query, provider, clients)

        response_text: str | None = None

        if intent == "off_topic":
            response_text = rag_poc.OFF_TOPIC_REFUSAL
        else:
            refs = resolver.resolve(query)
            qdrant_filter = rag_poc.build_qdrant_filter(refs, scholar_filter=None)
            dense_emb = rag_poc.embed_query_text(query, clients)
            chunks = rag_poc.retrieve_chunks(
                qdrant, collection, query, dense_emb, sparse_model,
                rag_poc.TOP_K, qdrant_filter,
            )
            if chunks:
                prompt = rag_poc.assemble_prompt(query, chunks)
                raw = rag_poc.generate(prompt, provider, clients, verbose=False)
                result = rag_poc.post_process(raw, intent, chunks, threshold=0.0)
                response_text = result.text

        ok, reason = check_result(case, intent, response_text)

        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1

        rows.append((status, case.query, intent, reason))

        mark = "+" if ok else "x"
        print(f"  [{mark}] #{i:02d} {status}  intent={intent:<16}  {case.query[:55]}")
        if verbose or not ok:
            print(f"       reason : {reason}")
            if verbose and response_text:
                preview = response_text[:200].replace("\n", " ")
                print(f"       preview: {preview}...")
            print()

        # Small pause to avoid hammering the OpenAI embeddings API
        time.sleep(0.3)

    print(f"\n{'='*72}")
    print(f"RESULTS  |  {passed}/{len(cases)} passed  {failed} failed")
    if failed:
        print("\nFailed queries:")
        for status, query, intent, reason in rows:
            if status == "FAIL":
                print(f"  - [{intent}] {query}")
                print(f"    {reason}")
    print(f"{'='*72}\n")

    if failed:
        sys.exit(1)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="End-to-end POC test runner.")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run a 10-query subset instead of the full suite.",
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai"],
        default=os.environ.get("LLM_PROVIDER", "anthropic"),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show full response previews for every query.",
    )
    args = parser.parse_args()

    cases = QUICK_CASES if args.quick else ALL_CASES
    run_tests(cases, provider=args.provider, verbose=args.verbose)


if __name__ == "__main__":
    main()
