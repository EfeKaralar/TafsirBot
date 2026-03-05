"""
audit.py — Spot-check retrieval quality against a test query set.

Embeds each test query, retrieves top-K chunks from Qdrant, and prints a
report. Flags queries where the best cosine score falls below the configured
threshold (default: 0.70).

Usage:
    python audit.py
    python audit.py --top-k 8 --threshold 0.65
    python audit.py --query "What does Ibn Kathir say about 2:255?"
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("audit")

DEFAULT_TOP_K = 5
DEFAULT_THRESHOLD = float(os.environ.get("AUDIT_SCORE_THRESHOLD", "0.70"))

# ── Test query set ────────────────────────────────────────────────────────────
# 50 queries spanning: named ayahs, numeric refs, thematic, cross-verse,
# linguistic, and edge cases that should be refused.
# Queries prefixed with "REFUSE:" must NOT return tafsir chunks (tested separately).

TEST_QUERIES: list[str] = [
    # Named ayah lookups (10)
    "What is the meaning of Ayat al-Kursi?",
    "Explain the Verse of the Throne",
    "What does Al-Fatiha mean?",
    "Commentary on Surah Al-Ikhlas",
    "What does Ibn Kathir say about Ayat al-Nur?",
    "Explanation of the light verse in the Quran",
    "What is the meaning of the People of the Cave?",
    "Commentary on Surah Al-Falaq",
    "What is Surah Al-Nas about?",
    "What does the Throne Verse say about Allah?",

    # Numeric ayah references (10)
    "Explain Quran 2:255",
    "What does Ibn Kathir say about 2:286?",
    "Commentary on 24:35",
    "What is the meaning of 112:1-4?",
    "Explain 3:18",
    "What does 36:1 say?",
    "Commentary on surah 1 verse 1",
    "What is 2:30 about?",
    "Explain verse 67:1",
    "What is the meaning of 55:1-4?",

    # Thematic queries (10)
    "What does the Quran say about tawakkul (trust in Allah)?",
    "Quranic teachings on justice and fairness",
    "What does the Quran say about the Day of Judgment?",
    "Quranic commentary on gratitude and thankfulness",
    "What do scholars say about mercy in the Quran?",
    "Tafsir on the concept of taqwa",
    "What does the Quran say about parents and family?",
    "Quranic teachings on patience and perseverance",
    "What is the Quranic view of creation?",
    "Commentary on the description of Paradise in the Quran",

    # Cross-verse / survey queries (5)
    "Verses about the attributes of Allah",
    "Quranic descriptions of hellfire",
    "All verses mentioning the Prophets",
    "Verses about prayer and worship in the Quran",
    "What surahs discuss the afterlife?",

    # Linguistic queries (5)
    "What is the meaning of the word 'khalifa' in Quran 2:30?",
    "Explain the Arabic root of 'taqwa'",
    "What does 'Rahman' mean in Al-Fatiha?",
    "Grammatical explanation of Surah Al-Ikhlas verse 1",
    "What does 'iqra' mean in the first revelation?",

    # Edge cases — these should be refused or handled carefully (10)
    "REFUSE: Is it halal to eat shellfish?",
    "REFUSE: What is the Islamic ruling on music?",
    "REFUSE: Can I pray with nail polish?",
    "REFUSE: Is cryptocurrency haram?",
    "REFUSE: What is the fatwa on travel insurance?",
    "REFUSE: Tell me about the history of Islam",
    "REFUSE: What is the weather today?",
    "REFUSE: Who is the best football player?",
    "REFUSE: Write me a poem about the Quran",
    "REFUSE: Translate this Arabic text for me",
]


@dataclass
class QueryResult:
    query: str
    top_score: float
    top_chunks: list[dict] = field(default_factory=list)
    low_confidence: bool = False


def embed_query(client, text: str, model: str) -> list[float]:
    response = client.embeddings.create(input=[text], model=model)
    return response.data[0].embedding


def retrieve(qdrant_client, collection: str, embedding: list[float], top_k: int) -> list[dict]:
    hits = qdrant_client.search(
        collection_name=collection,
        query_vector=embedding,
        limit=top_k,
        with_payload=True,
    )
    return [
        {
            "score": round(hit.score, 4),
            "scholar": hit.payload.get("scholar"),
            "surah": hit.payload.get("surah_number"),
            "ayah_start": hit.payload.get("ayah_start"),
            "ayah_end": hit.payload.get("ayah_end"),
            "chunk_type": hit.payload.get("chunk_type"),
            "snippet": (hit.payload.get("content") or "")[:120],
        }
        for hit in hits
    ]


def run_audit(
    openai_client,
    qdrant_client,
    collection: str,
    model: str,
    queries: list[str],
    top_k: int,
    threshold: float,
) -> None:
    results: list[QueryResult] = []
    refuse_queries = [q for q in queries if q.startswith("REFUSE:")]
    normal_queries = [q for q in queries if not q.startswith("REFUSE:")]

    # ── Normal queries ────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print(f"AUDIT REPORT  |  collection={collection}  top_k={top_k}  threshold={threshold}")
    print("=" * 72)

    low_confidence_queries: list[str] = []

    for query in normal_queries:
        embedding = embed_query(openai_client, query, model)
        chunks = retrieve(qdrant_client, collection, embedding, top_k)
        top_score = chunks[0]["score"] if chunks else 0.0
        low_conf = top_score < threshold

        result = QueryResult(
            query=query,
            top_score=top_score,
            top_chunks=chunks,
            low_confidence=low_conf,
        )
        results.append(result)

        flag = " ⚠  LOW" if low_conf else "    OK"
        print(f"\n{flag}  [{top_score:.3f}]  {query}")
        for i, chunk in enumerate(chunks[:3], 1):
            print(
                f"      {i}. [{chunk['scholar']}] "
                f"{chunk['surah']}:{chunk['ayah_start']}–{chunk['ayah_end']} "
                f"({chunk['chunk_type']})  score={chunk['score']}"
            )
            print(f"         {chunk['snippet']}...")

        if low_conf:
            low_confidence_queries.append(query)

    # ── Summary ───────────────────────────────────────────────────────────────
    total = len(results)
    low = len(low_confidence_queries)
    scores = [r.top_score for r in results]
    mean_score = sum(scores) / len(scores) if scores else 0.0

    print("\n" + "=" * 72)
    print("SUMMARY")
    print(f"  Total queries:     {total}")
    print(f"  Low-confidence:    {low} ({100*low/total:.0f}%)")
    print(f"  Mean top score:    {mean_score:.3f}")
    print(f"  Threshold:         {threshold}")

    if low_confidence_queries:
        print("\nLow-confidence queries to investigate:")
        for q in low_confidence_queries:
            print(f"  - {q}")

    print(f"\nRefusal edge cases to test manually ({len(refuse_queries)} queries):")
    for q in refuse_queries:
        print(f"  - {q[len('REFUSE:'):].strip()}")
    print("=" * 72 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit retrieval quality.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument(
        "--query",
        help="Run a single ad-hoc query instead of the full test set.",
    )
    args = parser.parse_args()

    import openai
    from qdrant_client import QdrantClient

    openai_client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    qdrant_client = QdrantClient(
        host=os.environ.get("QDRANT_HOST", "localhost"),
        port=int(os.environ.get("QDRANT_PORT", 6333)),
    )
    collection = os.environ.get("QDRANT_COLLECTION", "tafsir")
    model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-large")

    queries = [args.query] if args.query else TEST_QUERIES

    run_audit(
        openai_client=openai_client,
        qdrant_client=qdrant_client,
        collection=collection,
        model=model,
        queries=queries,
        top_k=args.top_k,
        threshold=args.threshold,
    )


if __name__ == "__main__":
    main()
