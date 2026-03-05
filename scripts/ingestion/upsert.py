"""
upsert.py — Push embedded chunks into Qdrant.

Reads data/embedded/<scholar>.jsonl and upserts vectors into the 'tafsir'
Qdrant collection. The operation is idempotent: a deterministic point ID is
derived from (scholar, surah_number, ayah_start, chunk_type), so re-runs
overwrite existing points cleanly.

IMPORTANT: The collection is created on first run with the correct vector size
(3072 for text-embedding-3-large). If you switch embedding models, drop and
recreate the collection — never mix vector sizes.

Usage:
    python upsert.py --scholar ibn_kathir
    python upsert.py --scholar maududi
    python upsert.py --scholar all
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


def _point_id(scholar: str, surah: int, ayah_start: int, chunk_type: str) -> int:
    """Deterministic point ID as a positive 64-bit integer hash."""
    key = f"{scholar}:{surah}:{ayah_start}:{chunk_type}"
    digest = hashlib.sha256(key.encode()).hexdigest()
    # Take first 15 hex digits to stay within Qdrant's uint64 range
    return int(digest[:15], 16)


def _ensure_collection(client, collection: str) -> None:
    """Create the Qdrant collection if it does not already exist."""
    from qdrant_client.models import Distance, VectorParams

    existing = {c.name for c in client.get_collections().collections}
    if collection in existing:
        logger.debug("Collection '%s' already exists", collection)
        return

    logger.info("Creating Qdrant collection '%s' (size=%d, cosine)", collection, VECTOR_SIZE)
    client.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )


def process_scholar(scholar: str, client, collection: str, batch_size: int) -> None:
    input_file = EMBEDDED_DIR / f"{scholar}.jsonl"
    if not input_file.exists():
        logger.warning("Embedded file not found: %s — skipping", input_file)
        return

    from qdrant_client.models import PointStruct

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
        points: list[PointStruct] = []

        for r in batch:
            embedding = r.pop("embedding")  # don't store vector in payload
            point_id = _point_id(
                r["scholar"],
                r["surah_number"],
                r["ayah_start"],
                r.get("chunk_type", "verse"),
            )
            # Payload is everything except the raw content and isnad (stored separately)
            payload = {k: v for k, v in r.items() if k != "embedding"}
            points.append(PointStruct(id=point_id, vector=embedding, payload=payload))

        batch_num = batch_idx // batch_size + 1
        logger.info("[%s] upserting batch %d/%d (%d points)", scholar, batch_num, total_batches, len(points))
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
    args = parser.parse_args()

    from qdrant_client import QdrantClient

    host = os.environ.get("QDRANT_HOST", "localhost")
    port = int(os.environ.get("QDRANT_PORT", 6333))
    collection = os.environ.get("QDRANT_COLLECTION", "tafsir")

    client = QdrantClient(host=host, port=port)
    _ensure_collection(client, collection)

    scholars = KNOWN_SCHOLARS if args.scholar == "all" else [args.scholar]
    for scholar in scholars:
        process_scholar(scholar, client, collection, args.batch_size)


if __name__ == "__main__":
    main()
