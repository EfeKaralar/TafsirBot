# TafsirBot Corpus Registry

> **Purpose:** Single source of truth for all Tafsir scholars and Hadith collections
> supported or planned by TafsirBot. The frontend SourceFilter component reads from
> this registry to determine which sources to display as selectable vs planned.
>
> **Status values:**
> - `available` — ingested, embedded, and queryable via the live RAG pipeline
> - `planned` — scheduled for a future phase; not yet ingested

---

## Tafsir Scholars

| ID | Display Name | Language | Phase | Status | Qdrant Scholar Key |
|----|-------------|----------|-------|--------|--------------------|
| `ibn_kathir` | Ibn Kathir | English | 1 | **available** | `ibn_kathir` |
| `maududi` | Maududi | English | 1 | **available** | `maududi` |
| `qurtubi` | Al-Qurtubi | Arabic | 2 | planned | `qurtubi` |
| `tabari` | Al-Tabari | Arabic | 2 | planned | `tabari` |
| `jalalayn` | Al-Jalalayn | English | 3 | planned | `jalalayn` |
| `ibn_ashur` | Ibn Ashur | Arabic | 3 | planned | `ibn_ashur` |

### Ibn Kathir — *Tafsir al-Qur'an al-Azim* (14th c.)

- **Full title:** Tafsir al-Quran al-Azim (Dar-us-Salam, 10-vol. abridged English translation)
- **Author:** Ibn Kathir (c. 1300–1373 CE / d. 774 AH)
- **Method:** *Tafsir bil-ma'thur* — interprets Quran with Quran, then hadith, then companion reports
- **Fiqh school:** Shafi'i (commonly misidentified as Hanbali; his *theological* methodology was shaped by his teacher Ibn Taymiyya who was Hanbali)
- **Theology:** Athari-leaning
- **Strengths:** Hadith grading and cross-referencing; widely trusted for legal and theological rulings; famous for critical stance against Isra'iliyyat
- **Weaknesses:** Repetitive; isnad chains dominate passages; occasional acceptance of *hadith da'if* outside the Isra'iliyyat category
- **Chunk type:** `verse`
- **RAG notes:** Strip isnad chains before embedding — they pollute dense embeddings. The Dar-us-Salam English translation is an abridgment; chains are often compressed or absent.
- **Source file:** `data/chunks/ibn_kathir.jsonl`

### Maududi — *Tafhim al-Quran* (20th c.)

- **Full title:** Tafhim al-Quran / Towards Understanding the Quran (The Islamic Foundation, English)
- **Author:** Abul A'la Maududi (1903–1979 CE)
- **Method:** Thematic/contextual; *tafsir bil-ra'y* with a socio-political lens
- **Fiqh school:** Not traditionally madhab-aligned; Jamaat-e-Islami ideological framework
- **Strengths:** Superb surah introductions; accessible to modern English readers; connects Quran to contemporary issues
- **Weaknesses:** Ideological bias (Islamist political philosophy); downplays classical scholarly disagreement; translation is from Urdu, adding an interpretive layer from the Arabic
- **Chunk types:** `verse` (commentary), `intro` (surah introductions — separate chunk type)
- **RAG notes:** Surah introductions are high-value context chunks and must be ingested as `chunk_type: intro`. Verse commentary is paragraph-length and self-contained — very RAG-friendly.
- **Source file:** `data/chunks/maududi.jsonl`

### Al-Qurtubi — *Al-Jami' li-Ahkam al-Quran* (13th c.)

- **Full title:** Al-Jami' li-Ahkam al-Quran (The Comprehensive Collection of Quranic Rulings)
- **Author:** Al-Qurtubi (1214–1273 CE / d. 671 AH)
- **Method:** *Tafsir al-ahkam* — legal-focused; Maliki jurisprudential lens
- **Fiqh school:** Maliki
- **Strengths:** Best source for deriving rulings (*ahkam*) from Quranic verses; compares madhabs; covers social and ethical context
- **Weaknesses:** Non-legal verses receive less depth
- **Chunk type:** `verse`, `legal`
- **RAG notes:** Dense legal reasoning sections; tag chunks with fiqh topic metadata (prayer, marriage, inheritance, etc.)
- **Source file:** `data/chunks/qurtubi.jsonl` *(not yet generated)*

### Al-Tabari — *Jami' al-Bayan* (10th c.)

- **Full title:** Jami' al-Bayan 'an Ta'wil Ay al-Quran (The Comprehensive Clarification of the Interpretation of the Verses of the Quran)
- **Author:** Ibn Jarir al-Tabari (838–923 CE / d. 310 AH). Founded the Jariri school of jurisprudence (short-lived, no surviving followers).
- **Method:** Most comprehensive classical *ma'thur* tafsir; collects all narrated opinions then adjudicates
- **Strengths:** Unmatched breadth of early opinions; preserves opinions not found elsewhere; strong Arabic linguistic analysis
- **Weaknesses:** 30+ volumes; many contradictory opinions per verse; requires expertise to navigate
- **Chunk type:** `verse`
- **RAG notes:** Multiple opinions per verse — preserve opinion markers ("some said X, others said Y"). Consider chunking by opinion unit rather than full verse. Strip isnad chains before embedding.
- **Source file:** `data/chunks/tabari.jsonl` *(not yet generated)*

### Al-Jalalayn — *Tafsir al-Jalalayn* (15th–16th c.)

- **Full title:** Tafsir al-Jalalayn (Feras Hamza English translation)
- **Authors:** Jalal al-Din al-Mahalli (teacher, d. 1459 CE) and his student Jalal al-Din al-Suyuti (d. 1505 CE). Al-Mahalli initiated the work, died before finishing; al-Suyuti completed it. Not father and son — teacher and student.
- **Method:** Grammatical/semantic explanation with deliberate brevity; minimal elaboration
- **Strengths:** Fast reference; excellent for Arabic grammar and basic meaning; covers entire Quran in one slim volume
- **Weaknesses:** No depth on hadith, fiqh, or historical context; occasional errors flagged by later scholars
- **Chunk type:** `verse`
- **RAG notes:** Very short chunks (often 1–2 sentences per phrase). High retrieval precision, low depth. Best used as a "quick gloss" or semantic disambiguation layer alongside richer tafsirs.
- **Source file:** `data/chunks/jalalayn.jsonl` *(not yet generated)*

### Ibn Ashur — *Al-Tahrir wa-al-Tanwir* (20th c.)

- **Full title:** Al-Tahrir wa-al-Tanwir (Liberation and Enlightenment)
- **Author:** Muhammad al-Tahir ibn Ashur (1879–1973 CE)
- **Fiqh school:** Maliki
- **Method:** Linguistic, *maqasid*-based, reformist; *tafsir bil-ra'y* at its most rigorous
- **Strengths:** *Maqasid al-Shari'ah* framework applied systematically; extraordinary Arabic linguistic precision; addresses modernist questions without abandoning classical method
- **Weaknesses:** Very demanding; requires strong Arabic proficiency; English translation is incomplete and hard to source
- **Chunk type:** `verse`
- **RAG notes:** Discursive, essay-style commentary — chunks must be larger to preserve argument coherence. Avoid splitting mid-argument.
- **Source file:** `data/chunks/ibn_ashur.jsonl` *(not yet generated)*

---

## Hadith Collections

All Hadith collections are **planned** (Phase 3+). No Hadith data has been ingested yet.
When added, Hadith chunks will live in a **separate Qdrant collection** (`hadith`) distinct
from the `tafsir` collection, because their metadata schema differs significantly
(book/chapter/hadith_number/narrator_chain/grading vs surah_number/ayah_start/ayah_end/scholar).

### Kutub al-Sitta (The Six Books)

| ID | Display Name | Language | Phase | Status |
|----|-------------|----------|-------|--------|
| `bukhari` | Sahih al-Bukhari | Arabic / English | 3 | planned |
| `muslim` | Sahih Muslim | Arabic / English | 3 | planned |
| `abu_dawud` | Sunan Abu Dawud | Arabic / English | 3 | planned |
| `tirmidhi` | Jami' at-Tirmidhi | Arabic / English | 3 | planned |
| `nasai` | Sunan an-Nasa'i | Arabic / English | 3 | planned |
| `ibn_majah` | Sunan Ibn Majah | Arabic / English | 3 | planned |

#### Sahih al-Bukhari
- **Compiler:** Muhammad ibn Ismail al-Bukhari (810–870 CE)
- **Status among scholars:** Considered the most authentic hadith collection after the Quran by the majority of Sunni scholars
- **Size:** ~7,563 hadiths (with repetitions); ~2,602 unique
- **Chunk metadata planned:** `book`, `chapter`, `hadith_number`, `narrator_chain`, `grading` (`sahih`)
- **RAG notes:** High-authority source for legal and theological questions; pairs naturally with Ibn Kathir and Al-Qurtubi retrieval

#### Sahih Muslim
- **Compiler:** Muslim ibn al-Hajjaj (815–875 CE)
- **Status among scholars:** Second most authentic collection; some prefer its organisation over Bukhari's
- **Size:** ~7,500 hadiths (with repetitions); ~3,033 unique
- **Chunk metadata planned:** `book`, `chapter`, `hadith_number`, `narrator_chain`, `grading` (`sahih`)
- **RAG notes:** Often retrieved alongside Bukhari; together they are referred to as *al-Sahihayn* (the Two Sahihs)

#### Sunan Abu Dawud
- **Compiler:** Abu Dawud al-Sijistani (817–889 CE)
- **Size:** ~5,274 hadiths
- **Chunk metadata planned:** `book`, `chapter`, `hadith_number`, `narrator_chain`, `grading`
- **RAG notes:** Strong coverage of fiqh topics; complements Al-Qurtubi retrieval

#### Jami' at-Tirmidhi
- **Compiler:** Muhammad ibn Isa at-Tirmidhi (824–892 CE)
- **Size:** ~3,956 hadiths
- **Chunk metadata planned:** `book`, `chapter`, `hadith_number`, `narrator_chain`, `grading`
- **RAG notes:** Unique grading system inline in the text; includes comparative fiqh commentary by the compiler

#### Sunan an-Nasa'i
- **Compiler:** Ahmad ibn Shu'ayb an-Nasa'i (829–915 CE)
- **Size:** ~5,761 hadiths
- **Chunk metadata planned:** `book`, `chapter`, `hadith_number`, `narrator_chain`, `grading`
- **RAG notes:** Known for strict isnad criticism; the *Sunan al-Kubra* is the larger version; *al-Mujtaba* (al-Sughra) is the standard abridgment

#### Sunan Ibn Majah
- **Compiler:** Ibn Majah al-Qazwini (824–887 CE)
- **Size:** ~4,341 hadiths
- **Chunk metadata planned:** `book`, `chapter`, `hadith_number`, `narrator_chain`, `grading`
- **RAG notes:** Contains some weak and disputed hadiths; grading metadata is especially important for this collection

---

## Planned Hadith Chunk Schema

```jsonc
{
  "content":          "<str>",          // text to embed (hadith matn + translation)
  "collection":       "bukhari",        // hadith collection ID
  "book":             "<str>",          // book name within collection
  "chapter":          "<str>",          // chapter name
  "hadith_number":    "<str>",          // canonical reference number
  "narrator_chain":   "<str>",          // isnad summary (strip before embedding)
  "grading":          "sahih|hasan|daif|...",
  "language":         "en",             // ISO 639-1
  "source_title":     "<str>",          // full collection title
  "arabic_text":      "<str>",          // Arabic matn
  "english_text":     "<str>",          // English translation of matn
  "chunk_type":       "hadith"
}
```

---

## Related Documents

- `docs/TAFSIR-CHOICES.md` — per-tafsir RAG analysis (chunk sizes, warnings, query fit)
- `docs/TAFSIR-CORPUS.mdx` — interactive React corpus dashboard
- `docs/CORPUS-SOURCES.md` — source URLs, license status, acquisition methods
- `CLAUDE.md` — architecture decisions, guardrails, coding conventions
