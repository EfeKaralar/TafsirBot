"""
audit.py — Spot-check retrieval quality against a test query set.

Embeds each test query with both dense (OpenAI) and sparse (BM42) models,
then retrieves top-K chunks via Qdrant hybrid prefetch+RRF fusion.

Scores are RRF rank-based (not cosine similarity), so they are shown as
rank indicators only — no hard threshold is applied in hybrid mode.

Usage:
    python audit.py
    python audit.py --top-k 8
    python audit.py --query "What does Ibn Kathir say about 2:255?"
"""

from __future__ import annotations

import argparse
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
SPARSE_MODEL_NAME = "Qdrant/bm42-all-minilm-l6-v2-attentions"


def _build_filter(refs) -> dict | None:
    """Build a Qdrant must-filter from the first resolved AyahRef."""
    if not refs:
        return None
    ref = refs[0]
    conditions: list[dict] = [{"key": "surah_number", "match": {"value": ref.surah}}]
    if not ref.is_surah_only():
        conditions.append({"key": "ayah_start", "range": {"gte": ref.ayah_start}})
        conditions.append({"key": "ayah_end", "range": {"lte": ref.ayah_end}})
    return {"must": conditions}

# ── Test query set ────────────────────────────────────────────────────────────
# 50 queries spanning: named ayahs, numeric refs, thematic, cross-verse,
# linguistic, fiqh/general-Islamic prompts that should still be answered,
# and clearly off-topic prompts that should be refused.
# Queries prefixed with "OFF_TOPIC:" are not retrieved here; they are listed
# for manual refusal checks against the end-to-end app workflow.

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

    # Edge cases — these should still be answered with guardrails (5)
    "Is it halal to eat shellfish?",
    "What is the Islamic ruling on music?",
    "Can I pray with nail polish?",
    "Is cryptocurrency haram?",
    "What is the fatwa on travel insurance?",

    # Off-topic refusal checks — manual in the app / rag_poc layer (5)
    "OFF_TOPIC: What is the weather today?",
    "OFF_TOPIC: Who is the best football player?",
    "OFF_TOPIC: Plan a weekend trip to Boston",
    "OFF_TOPIC: Write me a poem about coffee",
    "OFF_TOPIC: Translate this Spanish sentence into English",
]


@dataclass
class QueryResult:
    query: str
    top_score: float
    top_chunks: list[dict] = field(default_factory=list)


def embed_dense(openai_client, text: str, model: str) -> list[float]:
    response = openai_client.embeddings.create(input=[text], model=model)
    return response.data[0].embedding


def embed_sparse(sparse_model, text: str):
    return next(sparse_model.embed([text]))


def retrieve(
    qdrant_client,
    collection: str,
    dense_emb: list[float],
    sparse_emb,
    top_k: int,
    filter_: dict | None = None,
) -> list[dict]:
    from qdrant_client.models import Filter, Fusion, FusionQuery, Prefetch, SparseVector

    filt = Filter(**filter_) if filter_ else None

    result = qdrant_client.query_points(
        collection_name=collection,
        prefetch=[
            Prefetch(query=dense_emb, using="dense", limit=top_k * 4, filter=filt),
            Prefetch(
                query=SparseVector(
                    indices=sparse_emb.indices.tolist(),
                    values=sparse_emb.values.tolist(),
                ),
                using="sparse",
                limit=top_k * 4,
                filter=filt,
            ),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=top_k,
        with_payload=True,
    )
    hits = result.points
    return [
        {
            "score": round(hit.score, 6),
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
    sparse_model,
    queries: list[str],
    top_k: int,
    resolver=None,
) -> None:
    off_topic_queries = [q for q in queries if q.startswith("OFF_TOPIC:")]
    normal_queries = [q for q in queries if not q.startswith("OFF_TOPIC:")]

    print("\n" + "=" * 72)
    print(f"AUDIT REPORT  |  collection={collection}  top_k={top_k}  mode=hybrid-RRF")
    print("=" * 72)

    results: list[QueryResult] = []

    for query in normal_queries:
        filter_ = None
        filter_tag = ""
        if resolver is not None:
            refs = resolver.resolve(query)
            filter_ = _build_filter(refs)
            if filter_:
                ref = refs[0]
                ayah_part = f" ayah={ref.ayah_start}-{ref.ayah_end}" if not ref.is_surah_only() else ""
                filter_tag = f"  [filter: surah={ref.surah}{ayah_part}]"

        dense_emb = embed_dense(openai_client, query, model)
        sparse_emb = embed_sparse(sparse_model, query)
        chunks = retrieve(qdrant_client, collection, dense_emb, sparse_emb, top_k, filter_)
        top_score = chunks[0]["score"] if chunks else 0.0

        result = QueryResult(query=query, top_score=top_score, top_chunks=chunks)
        results.append(result)

        print(f"\n     [{top_score:.6f}]  {query}{filter_tag}")
        for i, chunk in enumerate(chunks[:3], 1):
            print(
                f"      {i}. [{chunk['scholar']}] "
                f"{chunk['surah']}:{chunk['ayah_start']}–{chunk['ayah_end']} "
                f"({chunk['chunk_type']})  rrf={chunk['score']}"
            )
            print(f"         {chunk['snippet']}...")

    # ── Summary ───────────────────────────────────────────────────────────────
    total = len(results)
    scores = [r.top_score for r in results]
    mean_score = sum(scores) / len(scores) if scores else 0.0

    print("\n" + "=" * 72)
    print("SUMMARY")
    print(f"  Total queries:     {total}")
    print(f"  Mean top RRF score:{mean_score:.6f}  (rank-based, not cosine)")

    print(f"\nOff-topic refusal checks to run manually ({len(off_topic_queries)} queries):")
    for q in off_topic_queries:
        print(f"  - {q[len('OFF_TOPIC:'):].strip()}")
    print("=" * 72 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit retrieval quality (hybrid RRF).")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument(
        "--query",
        help="Run a single ad-hoc query instead of the full test set.",
    )
    args = parser.parse_args()

    import openai
    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient

    from utils.quran_ref import QuranRef
    from utils.ayah_resolver import AyahResolver

    openai_client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    qdrant_client = QdrantClient(
        host=os.environ.get("QDRANT_HOST", "localhost"),
        port=int(os.environ.get("QDRANT_PORT", 6333)),
    )
    collection = os.environ.get("QDRANT_COLLECTION", "tafsir")
    model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-large")

    logger.info("Loading sparse model '%s'…", SPARSE_MODEL_NAME)
    sparse_model = SparseTextEmbedding(SPARSE_MODEL_NAME)

    resolver = AyahResolver(QuranRef())

    queries = [args.query] if args.query else TEST_QUERIES

    run_audit(
        openai_client=openai_client,
        qdrant_client=qdrant_client,
        collection=collection,
        model=model,
        sparse_model=sparse_model,
        queries=queries,
        top_k=args.top_k,
        resolver=resolver,
    )


if __name__ == "__main__":
    main()
