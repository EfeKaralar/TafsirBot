"""
upsert.py — Push embedded chunks into Qdrant.

Reads data/embedded/<scholar>.jsonl and upserts vectors into the 'tafsir'
Qdrant collection. The operation is idempotent: a deterministic point ID is
derived from (scholar, surah_number, ayah_start, chunk_type), so re-runs
overwrite existing points cleanly.

IMPORTANT: The collection uses named dense+sparse vectors for hybrid BM42+cosine
retrieval. If you switch embedding models, use --recreate to drop and rebuild.

Usage:
    python upsert.py --scholar ibn_kathir
    python upsert.py --scholar maududi
    python upsert.py --scholar all
    python upsert.py --scholar all --recreate
    python upsert.py --scholar ibn_kathir --batch-size 200
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("upsert")

_REPO_ROOT = Path(__file__).resolve().parents[2]
EMBEDDED_DIR = _REPO_ROOT / "data" / "embedded"

KNOWN_SCHOLARS = ["ibn_kathir", "maududi", "tabari", "jalalayn", "qurtubi", "ibn_ashur"]

VECTOR_SIZE = 3072       # text-embedding-3-large output dimensions
DEFAULT_BATCH_SIZE = 200
SPARSE_MODEL_NAME = "Qdrant/bm42-all-minilm-l6-v2-attentions"


def _point_id(scholar: str, surah: int, ayah_start: int, chunk_type: str) -> int:
    """Deterministic point ID as a positive 64-bit integer hash."""
    key = f"{scholar}:{surah}:{ayah_start}:{chunk_type}"
    digest = hashlib.sha256(key.encode()).hexdigest()
    # Take first 15 hex digits to stay within Qdrant's uint64 range
    return int(digest[:15], 16)


def _ensure_collection(client, collection: str, recreate: bool) -> None:
    """Create the Qdrant collection, optionally dropping an existing one first."""
    from qdrant_client.models import (
        Distance,
        SparseIndexParams,
        SparseVectorParams,
        VectorParams,
    )

    existing = {c.name for c in client.get_collections().collections}

    if recreate and collection in existing:
        logger.info("--recreate: dropping existing collection '%s'", collection)
        client.delete_collection(collection_name=collection)
        existing.discard(collection)

    if collection in existing:
        logger.debug("Collection '%s' already exists", collection)
        return

    logger.info(
        "Creating Qdrant collection '%s' (dense size=%d cosine + sparse BM42)",
        collection,
        VECTOR_SIZE,
    )
    client.create_collection(
        collection_name=collection,
        vectors_config={"dense": VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)},
        sparse_vectors_config={
            "sparse": SparseVectorParams(
                index=SparseIndexParams(on_disk=False)
            )
        },
    )


def process_scholar(
    scholar: str,
    client,
    collection: str,
    batch_size: int,
    sparse_model,
) -> None:
    input_file = EMBEDDED_DIR / f"{scholar}.jsonl"
    if not input_file.exists():
        logger.warning("Embedded file not found: %s — skipping", input_file)
        return

    from qdrant_client.models import PointStruct, SparseVector

    records: list[dict] = []
    with input_file.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    if not records:
        logger.warning("No records in %s", input_file)
        return

    total_batches = (len(records) + batch_size - 1) // batch_size
    upserted = 0

    for batch_idx in range(0, len(records), batch_size):
        batch = records[batch_idx: batch_idx + batch_size]

        # Compute sparse embeddings for the whole batch at once
        contents = [r.get("content", "") for r in batch]
        sparse_embeddings = list(sparse_model.embed(contents))

        points: list[PointStruct] = []
        for r, sparse in zip(batch, sparse_embeddings):
            dense_embedding = r.pop("embedding")  # don't store vector in payload
            point_id = _point_id(
                r["scholar"],
                r["surah_number"],
                r["ayah_start"],
                r.get("chunk_type", "verse"),
            )
            payload = {k: v for k, v in r.items() if k != "embedding"}
            points.append(
                PointStruct(
                    id=point_id,
                    vector={
                        "dense": dense_embedding,
                        "sparse": SparseVector(
                            indices=sparse.indices.tolist(),
                            values=sparse.values.tolist(),
                        ),
                    },
                    payload=payload,
                )
            )

        batch_num = batch_idx // batch_size + 1
        logger.info(
            "[%s] upserting batch %d/%d (%d points)",
            scholar, batch_num, total_batches, len(points),
        )
        client.upsert(collection_name=collection, points=points, wait=True)
        upserted += len(points)

    logger.info("upsert [%s] — %d points upserted into '%s'", scholar, upserted, collection)


def main() -> None:
    parser = argparse.ArgumentParser(description="Upsert embedded chunks into Qdrant.")
    parser.add_argument(
        "--scholar",
        default="all",
        choices=[*KNOWN_SCHOLARS, "all"],
        help="Which scholar to upsert (default: all).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Points per Qdrant upsert call (default: {DEFAULT_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop and recreate the Qdrant collection before upserting.",
    )
    args = parser.parse_args()

    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient

    host = os.environ.get("QDRANT_HOST", "localhost")
    port = int(os.environ.get("QDRANT_PORT", 6333))
    collection = os.environ.get("QDRANT_COLLECTION", "tafsir")

    logger.info("Loading sparse model '%s' (downloads ~130MB on first run)…", SPARSE_MODEL_NAME)
    sparse_model = SparseTextEmbedding(SPARSE_MODEL_NAME)

    client = QdrantClient(host=host, port=port)
    _ensure_collection(client, collection, recreate=args.recreate)

    scholars = KNOWN_SCHOLARS if args.scholar == "all" else [args.scholar]
    for scholar in scholars:
        process_scholar(scholar, client, collection, args.batch_size, sparse_model)


if __name__ == "__main__":
    main()
