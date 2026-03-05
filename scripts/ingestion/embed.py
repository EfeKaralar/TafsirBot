"""
embed.py — Generate embeddings for chunked tafsir text.

Reads data/chunks/<scholar>.jsonl, calls OpenAI text-embedding-3-large,
and writes data/embedded/<scholar>.jsonl with an 'embedding' field added.

IMPORTANT: Never change EMBEDDING_MODEL after upsert — mixing models in the
same Qdrant collection destroys retrieval quality. If you need to re-embed,
drop and recreate the collection.

Usage:
    python embed.py --scholar ibn_kathir
    python embed.py --scholar maududi
    python embed.py --scholar all
    python embed.py --scholar ibn_kathir --batch-size 50
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import tiktoken

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

load_dotenv(_DOTENV := Path(__file__).resolve().parents[2] / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("embed")

_REPO_ROOT = Path(__file__).resolve().parents[2]
CHUNKS_DIR = _REPO_ROOT / "data" / "chunks"
EMBEDDED_DIR = _REPO_ROOT / "data" / "embedded"

KNOWN_SCHOLARS = ["ibn_kathir", "maududi", "tabari", "jalalayn", "qurtubi", "ibn_ashur"]

DEFAULT_BATCH_SIZE = 100
DEFAULT_RETRY_ATTEMPTS = 5
DEFAULT_RETRY_BASE_DELAY = 2.0  # seconds; doubles on each retry
TOKEN_LIMIT = 8191  # text-embedding-3-large max input tokens

_tokenizer = tiktoken.get_encoding("cl100k_base")


def _truncate(text: str) -> str:
    """Truncate text to TOKEN_LIMIT tokens if necessary."""
    tokens = _tokenizer.encode(text)
    if len(tokens) <= TOKEN_LIMIT:
        return text
    logger.warning("Truncating chunk from %d to %d tokens", len(tokens), TOKEN_LIMIT)
    return _tokenizer.decode(tokens[:TOKEN_LIMIT])


def _embed_batch(client, texts: list[str], model: str) -> list[list[float]]:
    """Call the OpenAI embedding API with exponential-backoff retries."""
    import openai

    delay = DEFAULT_RETRY_BASE_DELAY
    for attempt in range(1, DEFAULT_RETRY_ATTEMPTS + 1):
        try:
            response = client.embeddings.create(input=texts, model=model)
            return [item.embedding for item in response.data]
        except openai.RateLimitError as exc:
            if attempt == DEFAULT_RETRY_ATTEMPTS:
                raise
            logger.warning("Rate limited (attempt %d/%d): %s — sleeping %.1fs",
                           attempt, DEFAULT_RETRY_ATTEMPTS, exc, delay)
            time.sleep(delay)
            delay *= 2
        except openai.APIError as exc:
            if attempt == DEFAULT_RETRY_ATTEMPTS:
                raise
            logger.warning("API error (attempt %d/%d): %s — sleeping %.1fs",
                           attempt, DEFAULT_RETRY_ATTEMPTS, exc, delay)
            time.sleep(delay)
            delay *= 2

    raise RuntimeError("Embedding failed after all retries")  # unreachable


def process_scholar(scholar: str, client, model: str, batch_size: int) -> None:
    input_file = CHUNKS_DIR / f"{scholar}.jsonl"
    EMBEDDED_DIR.mkdir(parents=True, exist_ok=True)
    output_file = EMBEDDED_DIR / f"{scholar}.jsonl"

    if not input_file.exists():
        logger.warning("Chunk file not found: %s — skipping", input_file)
        return

    # Load all records; skip already-embedded ones if resuming
    records: list[dict] = []
    with input_file.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    # Check if output already has some records (allows resume after interruption)
    already_done = 0
    if output_file.exists():
        with output_file.open(encoding="utf-8") as f:
            already_done = sum(1 for line in f if line.strip())
        logger.info("Resuming: %d / %d already embedded", already_done, len(records))

    records_to_embed = records[already_done:]
    if not records_to_embed:
        logger.info("All records already embedded for %s", scholar)
        return

    total_batches = (len(records_to_embed) + batch_size - 1) // batch_size
    embedded_count = 0

    with output_file.open("a", encoding="utf-8") as fout:
        for batch_idx in range(0, len(records_to_embed), batch_size):
            batch = records_to_embed[batch_idx: batch_idx + batch_size]
            texts = [_truncate(r["content"]) for r in batch]
            batch_num = batch_idx // batch_size + 1

            logger.info(
                "[%s] batch %d/%d (%d texts)",
                scholar, batch_num, total_batches, len(texts),
            )

            embeddings = _embed_batch(client, texts, model)

            for record, embedding in zip(batch, embeddings):
                record["embedding"] = embedding
                fout.write(json.dumps(record, ensure_ascii=False) + "\n")
                embedded_count += 1

            # Small courtesy delay to avoid aggressive rate-limit hits
            time.sleep(0.1)

    logger.info(
        "embed [%s] — %d new records embedded → %s",
        scholar, embedded_count, output_file,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate embeddings for chunked tafsir text.")
    parser.add_argument(
        "--scholar",
        default="all",
        choices=[*KNOWN_SCHOLARS, "all"],
        help="Which scholar to embed (default: all).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Texts per API request (default: {DEFAULT_BATCH_SIZE}).",
    )
    args = parser.parse_args()

    import openai

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set. Copy .env.example → .env and fill in the key.")

    model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-large")
    client = openai.OpenAI(api_key=api_key)

    scholars = KNOWN_SCHOLARS if args.scholar == "all" else [args.scholar]
    for scholar in scholars:
        process_scholar(scholar, client, model, args.batch_size)


if __name__ == "__main__":
    main()
