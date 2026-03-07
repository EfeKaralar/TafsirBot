"""
rag_poc.py — Python proof-of-concept RAG pipeline for TafsirBot.

Runs the full query path end-to-end without n8n:
  1. Input normalization
  2. Intent classification
  3. Ayah reference resolution → Qdrant metadata filter
  4. Vector retrieval (top-K chunks)
  5. Prompt assembly
  6. LLM generation (Claude Sonnet or GPT-4o, configurable)
  7. Post-processing: citation extraction + disclaimer

Usage:
    python scripts/rag_poc.py "What does Ibn Kathir say about 2:255?"
    python scripts/rag_poc.py --scholar maududi "What is the theme of Surah Al-Baqarah?"
    python scripts/rag_poc.py --provider openai "What do scholars say about tawakkul?"
    python scripts/rag_poc.py --top-k 8 --verbose "Explain Ayat al-Kursi"
    uv run python scripts/rag_poc.py --persist "Explain Quran 2:255"
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Allow imports from scripts/ingestion/utils/
sys.path.insert(0, str(Path(__file__).resolve().parent / "ingestion"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("rag_poc")

# ── Types ─────────────────────────────────────────────────────────────────────

Intent = Literal["tafsir", "general_islamic", "fiqh_ruling", "off_topic"]
Provider = Literal["anthropic", "openai"]

DISCLAIMER = (
    "\n\n---\n"
    "*This response is an AI-assisted summary of classical Tafsir commentary. "
    "It is not a fatwa or religious ruling. Please consult a qualified Islamic "
    "scholar for guidance on religious practice.*"
)

FIQH_NOTE = (
    "*(This question touches on Islamic jurisprudence (fiqh). "
    "The following presents what Tafsir scholars say on the relevant Quranic passages — "
    "it is not a fatwa or personal ruling. For a ruling on your specific situation, "
    "please consult a qualified Islamic scholar.)*\n\n"
)

OFF_TOPIC_REFUSAL = (
    "I can only answer questions about Quranic commentary and Islamic topics. "
    "If you have a question about a Quranic verse or concept, I'm happy to help."
)

TOP_K = 5
MAX_TOKENS = 800
TEMPERATURE = 0.3

CLAUDE_MODEL = "claude-sonnet-4-6"
OPENAI_MODEL = "gpt-4o"


# ── Step 1: Normalize input ───────────────────────────────────────────────────

def normalize(query: str) -> str:
    """Strip @mentions, hashtags, excess whitespace, and platform noise."""
    query = re.sub(r"@\w+", "", query)
    query = re.sub(r"#\w+", "", query)
    query = re.sub(r"\s{2,}", " ", query)
    return query.strip()


# ── Step 2: Intent classification ────────────────────────────────────────────

INTENT_SYSTEM = """\
You are an intent classifier for an Islamic Quran commentary assistant.
Classify the user's query into exactly one of these four intents:

- tafsir: Questions about the meaning, interpretation, or commentary of Quranic verses
  or Islamic concepts that can be answered from Tafsir literature.
- general_islamic: General questions about Islam that are informational. This includes
  asking what scholars say on a topic, historical or legal positions, or how a concept
  is treated in Islamic tradition — even if the topic is sensitive or jurisprudential
  in nature (e.g. abortion, alcohol, dogs, music). These are answerable with scholarly
  information even if they cannot be given a personal ruling.
- fiqh_ruling: Personal requests for a fatwa framed as a direct question about the
  user's own action — "Am I allowed to Z?", "Can I do X?", "Is this permissible for
  me?". The key marker is first-person actionable guidance the user will act on,
  as opposed to asking what scholars or the Quran say.
- off_topic: Completely unrelated to Islam or the Quran.

Examples:
  "Is it halal to eat shellfish?"             → general_islamic
  "Can I eat shellfish? Is it allowed for me?"→ fiqh_ruling
  "Can I pray with nail polish?"              → fiqh_ruling
  "What is the Islamic view on nail polish?"  → general_islamic
  "What is the position of scholars on dogs?" → general_islamic
  "What do scholars say about abortion?"      → general_islamic
  "What does the Quran say about wine?"       → tafsir
  "Who was Ibn Kathir?"                       → general_islamic
  "What is the weather today?"                → off_topic

Reply with ONLY the intent word, nothing else.
"""


def classify_intent(query: str, provider: Provider, clients: dict) -> Intent:
    """Return the intent label for a query using a fast single-token LLM call."""
    if provider == "anthropic":
        msg = clients["anthropic"].messages.create(
            model=CLAUDE_MODEL,
            max_tokens=10,
            temperature=0,
            system=INTENT_SYSTEM,
            messages=[{"role": "user", "content": query}],
        )
        intent_raw = msg.content[0].text.strip().lower()
    else:
        resp = clients["openai"].chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=10,
            temperature=0,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM},
                {"role": "user", "content": query},
            ],
        )
        intent_raw = resp.choices[0].message.content.strip().lower()

    valid: set[Intent] = {"tafsir", "general_islamic", "fiqh_ruling", "off_topic"}
    intent = intent_raw if intent_raw in valid else "tafsir"
    logger.debug("Intent: %s (raw=%r)", intent, intent_raw)
    return intent  # type: ignore[return-value]


# ── Step 3: Ayah reference resolution ────────────────────────────────────────

def build_qdrant_filter(refs, scholar_filter: str | None) -> dict | None:
    """
    Build a Qdrant must-filter from resolved AyahRefs and an optional
    scholar restriction.  Returns None if no filters should be applied.
    """
    conditions: list[dict] = []

    if scholar_filter:
        conditions.append({"key": "scholar", "match": {"value": scholar_filter}})

    if refs:
        # Use the first resolved reference for now; future: multi-ref OR filter
        ref = refs[0]
        conditions.append({"key": "surah_number", "match": {"value": ref.surah}})
        if not ref.is_surah_only():
            conditions.append({"key": "ayah_start", "range": {"gte": ref.ayah_start}})
            conditions.append({"key": "ayah_end", "range": {"lte": ref.ayah_end}})

    return {"must": conditions} if conditions else None


# ── Step 4: Hybrid retrieval ──────────────────────────────────────────────────

def embed_query_text(text: str, clients: dict) -> list[float]:
    model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-large")
    resp = clients["openai"].embeddings.create(input=[text], model=model)
    return resp.data[0].embedding


def retrieve_chunks(
    qdrant_client,
    collection: str,
    query_text: str,
    dense_emb: list[float],
    sparse_model,
    top_k: int,
    qdrant_filter: dict | None,
) -> list[dict]:
    from qdrant_client.models import Filter, Fusion, FusionQuery, Prefetch, SparseVector

    sparse_emb = next(sparse_model.embed([query_text]))
    filt = Filter(**qdrant_filter) if qdrant_filter else None

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
    return [
        {
            "score": hit.score,
            "scholar": hit.payload.get("scholar", "unknown"),
            "surah_number": hit.payload.get("surah_number"),
            "ayah_start": hit.payload.get("ayah_start"),
            "ayah_end": hit.payload.get("ayah_end"),
            "content": hit.payload.get("content", ""),
            "source_title": hit.payload.get("source_title", ""),
            "english_text": hit.payload.get("english_text", ""),
        }
        for hit in result.points
    ]


# ── Step 5: Prompt assembly ───────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a scholarly Quran commentary assistant. Your role is to explain the
meaning of Quranic verses by drawing on classical and modern Tafsir sources.

Rules:
1. Always cite your sources using the format [Scholar Name on Surah:Ayah].
   For example: [Ibn Kathir on 2:255] or [Maududi on Al-Baqarah intro].
2. If multiple scholars are in the context, present multiple perspectives.
3. Do not issue religious rulings (fatwas). If asked for one, redirect the
   user to consult a qualified scholar.
4. Be clear when scholars disagree. Do not present one view as the only view.
5. Your response should be clear, informative, and grounded in the provided
   Tafsir excerpts. Do not fabricate citations or commentary.
6. Write in a respectful, scholarly tone appropriate for a diverse audience.
"""


def _scholar_display(scholar: str) -> str:
    mapping = {
        "ibn_kathir": "Ibn Kathir",
        "maududi": "Maududi",
        "tabari": "Al-Tabari",
        "jalalayn": "Al-Jalalayn",
        "qurtubi": "Al-Qurtubi",
        "ibn_ashur": "Ibn Ashur",
    }
    return mapping.get(scholar, scholar.replace("_", " ").title())


def assemble_prompt(query: str, chunks: list[dict]) -> str:
    context_blocks: list[str] = []
    for chunk in chunks:
        scholar = _scholar_display(chunk["scholar"])
        surah = chunk["surah_number"]
        start = chunk["ayah_start"]
        end = chunk["ayah_end"]
        ref = f"{surah}:{start}" if start == end else f"{surah}:{start}-{end}"
        header = f"[{scholar} on {ref}]"
        if chunk.get("english_text"):
            header += f'\nAyah translation: "{chunk["english_text"]}"'
        context_blocks.append(f"{header}\n{chunk['content']}")

    context = "\n\n---\n\n".join(context_blocks)
    return f"Tafsir context:\n\n{context}\n\nUser question: {query}"


# ── Step 6: LLM generation ────────────────────────────────────────────────────

def generate(prompt: str, provider: Provider, clients: dict, verbose: bool) -> str:
    if verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Prompt length: %d chars", len(prompt))

    if provider == "anthropic":
        msg = clients["anthropic"].messages.create(
            model=CLAUDE_MODEL,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    else:
        resp = clients["openai"].chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content.strip()


# ── Step 7: Post-processing ───────────────────────────────────────────────────

@dataclass
class RAGResponse:
    text: str
    citations: list[str]
    intent: str
    confidence: Literal["high", "low"]
    chunks_used: int


def extract_citations(text: str) -> list[str]:
    """Extract [Scholar on Surah:Ayah] citation markers from the response."""
    return re.findall(r"\[[^\]]+on\s+[^\]]+\]", text)


def format_sources(chunks: list[dict]) -> str:
    """Build a deduplicated Sources section from retrieved chunks."""
    seen: set[str] = set()
    lines: list[str] = []
    for chunk in chunks:
        scholar = _scholar_display(chunk["scholar"])
        surah = chunk["surah_number"]
        start = chunk["ayah_start"]
        end = chunk["ayah_end"]
        title = chunk.get("source_title", "")
        if start == 0:
            ref = f"{scholar} — {title} (surah {surah} introduction)"
        elif start == end:
            ref = f"{scholar} on {surah}:{start} — {title}"
        else:
            ref = f"{scholar} on {surah}:{start}–{end} — {title}"
        if ref not in seen:
            seen.add(ref)
            lines.append(f"- {ref}")
    return "\n**Sources:**\n" + "\n".join(lines)


def post_process(
    raw_text: str,
    intent: str,
    chunks: list[dict],
    threshold: float = 0.70,
) -> RAGResponse:
    citations = extract_citations(raw_text)
    top_score = max((c["score"] for c in chunks), default=0.0)
    confidence: Literal["high", "low"] = "high" if top_score >= threshold else "low"

    sources_section = format_sources(chunks)
    final_text = raw_text + sources_section + DISCLAIMER
    if confidence == "low":
        final_text = (
            "*(Note: retrieval confidence is low for this query — "
            "the following summary may be incomplete.)*\n\n" + final_text
        )

    return RAGResponse(
        text=final_text,
        citations=citations,
        intent=intent,
        confidence=confidence,
        chunks_used=len(chunks),
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="TafsirBot Python POC RAG pipeline.")
    parser.add_argument("query", help="The question to ask.")
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai"],
        default=os.environ.get("LLM_PROVIDER", "anthropic"),
        help="LLM provider (default: LLM_PROVIDER env var or 'anthropic').",
    )
    parser.add_argument(
        "--scholar",
        default=None,
        help="Restrict retrieval to a specific scholar (e.g. ibn_kathir, maududi). Use 'all' or omit for no filter.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=TOP_K,
        help=f"Number of chunks to retrieve (default: {TOP_K}).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print debug information including retrieved chunks.",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Persist the chat session and messages to Postgres.",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Existing chat session UUID. Omit to create a new session when --persist is used.",
    )
    parser.add_argument(
        "--channel",
        default="local_cli",
        help="Channel identifier stored with persisted sessions (default: local_cli).",
    )
    parser.add_argument(
        "--user-id",
        default="local_user",
        help="User identifier stored with persisted sessions (default: local_user).",
    )
    parser.add_argument(
        "--session-title",
        default=None,
        help="Optional title for a newly created or updated persisted session.",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # ── Build clients ─────────────────────────────────────────────────────────
    from fastembed import SparseTextEmbedding

    clients: dict = {}

    if args.provider == "anthropic" or True:  # always need openai for embeddings
        import openai as _openai
        clients["openai"] = _openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    if args.provider == "anthropic":
        import anthropic as _anthropic
        clients["anthropic"] = _anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    from qdrant_client import QdrantClient
    qdrant = QdrantClient(
        host=os.environ.get("QDRANT_HOST", "localhost"),
        port=int(os.environ.get("QDRANT_PORT", 6333)),
    )
    collection = os.environ.get("QDRANT_COLLECTION", "tafsir")

    from utils.quran_ref import QuranRef
    from utils.ayah_resolver import AyahResolver

    qr = QuranRef()
    resolver = AyahResolver(qr)

    sparse_model = SparseTextEmbedding("Qdrant/bm42-all-minilm-l6-v2-attentions")
    persistence = None

    # ── Pipeline ──────────────────────────────────────────────────────────────
    print()

    # Step 1: Normalize
    query = normalize(args.query)

    session_record = None
    if args.persist:
        from persistence import PostgresPersistence

        persistence = PostgresPersistence.from_env()
        persistence.apply_migrations()
        session_record = persistence.ensure_chat_session(
            session_id=args.session_id,
            channel=args.channel,
            user_id=args.user_id,
            title=args.session_title or query[:80],
        )
        persistence.add_chat_message(
            session_id=session_record.id,
            role="user",
            content=query,
            metadata={
                "provider": args.provider,
                "scholar_filter": args.scholar,
                "top_k": args.top_k,
            },
        )

    # Step 2: Classify intent
    intent = classify_intent(query, args.provider, clients)

    if intent == "off_topic":
        if persistence and session_record:
            persistence.add_chat_message(
                session_id=session_record.id,
                role="assistant",
                content=OFF_TOPIC_REFUSAL,
                intent=intent,
                confidence="high",
                metadata={"path": "off_topic_refusal"},
            )
        print(OFF_TOPIC_REFUSAL)
        return

    # fiqh_ruling: do not refuse — retrieve and respond with scholarly context,
    # but prepend FIQH_NOTE so the user knows it is not a personal ruling.

    # Step 3: Resolve Ayah references
    refs = resolver.resolve(query)
    if args.verbose and refs:
        print(f"[refs] {refs}\n")

    scholar_filter = args.scholar if args.scholar and args.scholar.lower() != "all" else None
    qdrant_filter = build_qdrant_filter(refs, scholar_filter)

    # Step 4: Embed + retrieve
    dense_emb = embed_query_text(query, clients)
    chunks = retrieve_chunks(qdrant, collection, query, dense_emb, sparse_model, args.top_k, qdrant_filter)

    if args.verbose:
        print(f"[retrieved {len(chunks)} chunks]")
        for c in chunks:
            print(
                f"  [{c['scholar']}] {c['surah_number']}:{c['ayah_start']} "
                f"score={c['score']:.3f} — {c['content'][:80]}..."
            )
        print()

    if not chunks:
        if persistence and session_record:
            persistence.add_chat_message(
                session_id=session_record.id,
                role="assistant",
                content="No relevant Tafsir passages found for this query.\n" + DISCLAIMER,
                intent=intent,
                confidence="low",
                metadata={"path": "no_chunks"},
            )
        print("No relevant Tafsir passages found for this query.")
        print(DISCLAIMER)
        return

    # Step 5: Assemble prompt
    prompt = assemble_prompt(query, chunks)

    # Step 6: Generate
    raw_response = generate(prompt, args.provider, clients, args.verbose)

    # Step 7: Post-process (threshold=0 — RRF scores are rank-based, not cosine)
    result = post_process(raw_response, intent, chunks, threshold=0.0)

    output = result.text
    if intent == "fiqh_ruling":
        output = FIQH_NOTE + output

    if persistence and session_record:
        persistence.add_chat_message(
            session_id=session_record.id,
            role="assistant",
            content=output,
            intent=result.intent,
            confidence=result.confidence,
            citations=result.citations,
            metadata={
                "chunks_used": result.chunks_used,
                "refs": [repr(ref) for ref in refs],
                "scholar_filter": scholar_filter,
            },
        )
    print(output)

    if args.verbose:
        if session_record:
            print(f"[session_id: {session_record.id}]")
        print(f"\n[citations: {result.citations}]")
        print(f"[confidence: {result.confidence}  chunks: {result.chunks_used}  intent: {result.intent}]")


if __name__ == "__main__":
    main()
