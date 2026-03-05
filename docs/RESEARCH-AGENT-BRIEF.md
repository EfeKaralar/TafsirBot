# Research Agent Brief — Islamic Scholarly Corpus Expansion

> **Instructions for the research agent:** You will receive this brief together with
> `docs/TAFSIR-CHOICES.md`. Your task is to expand that document to cover fiqh and
> fatwa sources. Read the brief fully before starting. Follow the output format exactly.

---

## Project Context

This is an AI-powered Islamic scholarly assistant built on a RAG pipeline. It answers
questions about Quranic commentary, Islamic jurisprudence, and scholarly opinion by
retrieving relevant passages from a curated corpus and generating a cited, disclaimed
response via an LLM.

The current corpus is Tafsir-only (Ibn Kathir EN + Maududi EN). The project is
expanding to cover fiqh (Islamic jurisprudence) and fatawa (legal opinions) so that
the bot can present scholarly opinions on jurisprudential questions without issuing
personal rulings.

**The bot never issues fatwas.** It presents what scholars say, with the disclaimer
that the user should consult a qualified scholar for personal guidance. Understanding
this distinction is essential for evaluating sources: we want sources that capture
*scholarly reasoning and disagreement*, not just conclusions.

---

## Hard Constraints

These are non-negotiable technical and editorial constraints the research agent must
respect when evaluating sources:

### Language and Embedding Architecture

- **Phase 1–2 corpus: English only.** The current embedding model is
  `text-embedding-3-large` (OpenAI, 3072 dims). The sparse model is
  `Qdrant/bm42-all-minilm-l6-v2-attentions` (BM42, English-focused).
- **Arabic sources require a separate Qdrant collection.** Mixing dense embeddings
  from different models in the same collection makes vectors incomparable and
  retrieval meaningless. When Arabic sources are ingested (Phase 3+), a second
  collection (`tafsir_ar`) will be created using `intfloat/multilingual-e5-large`
  with a language-routing layer in the query pipeline. BM42 does not handle Arabic
  well; an Arabic-capable sparse model will need to be evaluated at that point.
- **Consequence for source evaluation:** Prioritize English sources for Phase 2.
  Arabic-only sources are valid candidates but must be explicitly flagged as
  Phase 3+ and noted as requiring the separate-collection architecture.

### Madhab Coverage

- All four Sunni madhabs (Hanafi, Maliki, Shafi'i, Hanbali) should be represented
  roughly equally. The bot is madhab-agnostic and must present multiple positions
  where scholars differ.
- Shia (Ja'fari) jurisprudence is explicitly out of scope for this project.
- When evaluating sources, flag the madhab coverage clearly. A source that covers
  only one madhab is acceptable if it fills a gap; a source that presents
  multi-madhab comparisons is preferred.

### Chunking Strategy

- Tafsir chunks are scoped to individual Ayahs or contiguous Ayah ranges.
- Fiqh chunks should be scoped to individual legal questions (masa'il) or
  topic-level sections — not arbitrary token windows.
- Fatwa chunks should be one fatwa per chunk (question + ruling + reasoning).
- Every chunk must carry: `scholar/source`, `madhab`, `corpus_type`, `language`,
  `source_title`, and where applicable `surah_number`/`ayah_start`/`ayah_end`.

### Single Collection Architecture (English Phase)

All English chunks — Tafsir, fiqh, and fatawa — go into the same Qdrant collection
(`tafsir`, to be renamed in a future release). This enables cross-corpus retrieval:
a question about a verse's legal implication can surface both the Tafsir commentary
and the relevant fiqh ruling in a single query. Two new metadata fields are added:

| Field | Values | Notes |
|---|---|---|
| `corpus_type` | `tafsir`, `fiqh`, `fatwa` | Distinguishes text type for filtering |
| `madhab` | `hanafi`, `maliki`, `shafii`, `hanbali`, `multi`, `unspecified` | For per-madhab filtering |

---

## What to Research and Document

For each candidate source below, evaluate and document:

1. **Full bibliographic details**: title, author/institution, edition, translator (if any)
2. **Madhab coverage**: single madhab or multi-madhab comparison
3. **Language and translation quality**: original language, translation quality notes
4. **Access method**: API, structured download (JSON/XML), PDF + OCR, web scraping
5. **Licensing status**: public domain, open license, copyright, personal/research use only
6. **Chunking strategy**: how to split meaningfully (by masa'la, by topic, by Q&A unit)
7. **RAG suitability assessment**: what query types it serves well and poorly; estimated
   chunk size range; any structural issues (heavily cross-referenced, terse legal Arabic, etc.)
8. **Phase assignment**: Phase 2 (English, accessible now) / Phase 3 (Arabic or complex
   acquisition) / Future (aspirational, no clear access path yet)
9. **Priority rank within its phase**: 1 = highest priority

---

## Candidate Sources to Evaluate

### Fiqh Manuals

- **Reliance of the Traveller** (*Umdat al-Salik*, Nuh Ha Mim Keller EN translation)
  — Shafi'i, comprehensive English, widely available
- ***Al-Hidaya*** (Marghinani; Hamilton EN translation, 1791, public domain)
  — Hanafi, old English, potentially OCR-available
- ***Al-Fiqh al-Islami wa Adillatuh*** (Wahbah al-Zuhayli)
  — Multi-madhab, Arabic; assess whether any usable English translation or
  partial translation exists
- ***Al-Mughni*** (Ibn Qudama) — Hanbali, Arabic; assess English translation status
- ***Mukhtasar Khalil*** — Maliki, Arabic; assess English translation status
- Any other accessible English fiqh manual you identify with good coverage

### Fiqh Encyclopedias

- **Kuwaiti Fiqh Encyclopedia** (*Al-Mawsu'a al-Fiqhiyya al-Kuwaitiyya*)
  — 45 volumes, Arabic, government-published (Kuwait Ministry of Awqaf);
  assess whether it is effectively public domain or permissively licensed;
  well-structured multi-madhab treatment makes it a strong RAG candidate for Phase 3
- Any other structured multi-madhab fiqh reference you identify

### Fatwa Databases

- **IslamQA** (islamqa.info) — Hanbali-leaning, English + Arabic, structured Q&A;
  assess scrapeability and terms of service
- **SeekersGuidance** fatawa archive — multi-madhab, English, structured;
  assess scrapeability
- **Dar al-Ifta al-Misriyya** (darlifta.org) — official Egyptian fatawa body,
  Arabic + English portal; assess API or structured access
- **Islamweb fatawa** (islamweb.net/en/fatwa) — large English database;
  assess quality, madhab distribution, scrapeability
- Any other high-quality fatawa database with English coverage you identify

### Contemporary Scholarly Works in English

- **Yusuf al-Qaradawi** — assess which of his works are available in English and
  in formats suitable for RAG (structured, topic-scoped chapters)
- **Mohammad Hashim Kamali** — principles of Islamic jurisprudence texts in English
- Any other accessible English-language Islamic legal scholarship you identify as
  high-value for this use case

---

## Output Format

Extend `TAFSIR-CHOICES.md` with the following new sections, using the same per-source
table format already present in that document:

1. `## Fiqh Manuals` — one subsection per source
2. `## Fiqh Encyclopedias` — one subsection per source
3. `## Fatwa Databases` — one subsection per source
4. `## Phase Assignment Summary` — a single table ranking all new sources by phase and
   priority, with a one-line RAG suitability note per source

At the top of each new source entry, include a **Phase** and **Priority** badge in the
table (e.g. `Phase 2 — Priority 1`).

Do not modify the existing Tafsir sections except to correct any factual errors you
identify. If you find errors, note them explicitly before making the correction.
