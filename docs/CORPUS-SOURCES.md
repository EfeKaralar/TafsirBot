# Corpus Sources

> Sources and acquisition methods for the tafsir texts used in the ingestion pipeline.
> Update this file whenever a source is added, changed, or re-evaluated.

---

## Phase 1 — Primary Corpus

### 1. Ibn Kathir — *Tafsir al-Quran al-Azim*

| Field | Value |
|---|---|
| **Full title** | Tafsīr al-Qurʾān al-ʿAẓīm |
| **Author** | Ismāʿīl ibn Kathīr (d. 774 AH / 1373 CE) |
| **Edition** | Dar-us-Salam, 10-volume abridged English translation |
| **Abridgment note** | This is an abridgment. Isnad chains are significantly compressed or absent compared to the full Arabic. The ingestion pipeline's isnad-stripping step is less critical for this edition but is still applied to catch any remaining chains. |
| **Recommended source** | quran.com API v4 — tafsir ID `169` (slug: `en-tafsir-ibn-kathir`) |
| **Fallback source** | quranx.com — URL pattern: `https://quranx.com/tafsir/IbnKathir/{surah}.{ayah}` |
| **Format** | JSON (quran.com) or structured HTML (quranx.com) |
| **Coverage** | Complete — all 114 surahs, 6,236 ayahs |
| **Language** | English |
| **License** | Commercial copyright (Dar-us-Salam Publications). The quran.com API is free for personal/non-commercial use. For a public-facing product, written permission from Dar-us-Salam is required before redistribution. |
| **Download method** | See `scripts/acquisition/download_qurancom.py` (to be created). Iterate `GET https://api.quran.com/api/v4/tafsirs/169/by_chapter/{1..114}` — one request per surah. Strip HTML from the `text` field. |

**Verify the tafsir ID before running:**
```bash
curl -s "https://api.quran.com/api/v4/resources/tafsirs" | python3 -m json.tool | grep -A3 "kathir"
```

---

### 2. Maududi — *Tafhim al-Quran*

| Field | Value |
|---|---|
| **Full title** | Tafhīm al-Qurʾān (Towards Understanding the Quran) |
| **Author** | Abū al-Aʿlā Mawdūdī (1903–1979 CE) |
| **Translator** | Zafar Ishaq Ansari (The Islamic Foundation, Leicester) |
| **Translation note** | English is a translation of an Urdu original, adding one layer of interpretive distance from the Arabic Quran. This is the complete, unabridged edition. |
| **Recommended source** | quran.com API v4 — tafsir ID `95` (slug: `en-maududi-tafhim-ul-quran` — verify) |
| **Fallback source** | islamicstudies.info — URL pattern: `https://www.islamicstudies.info/tafheem.php?sura={1..114}` (per-surah HTML, includes surah introductions + footnotes) |
| **Format** | JSON (quran.com) or HTML per surah (islamicstudies.info) |
| **Coverage** | Complete — all 114 surahs |
| **Language** | English |
| **License** | Commercial copyright (The Islamic Foundation, Leicester). Same personal/non-commercial API usage tolerance as Ibn Kathir. Written permission required for public redistribution. |
| **Download method** | Same quran.com approach as Ibn Kathir; OR scrape islamicstudies.info with 114 requests (preferred if surah-level chunking with introductions is needed — the intro sections are on the surah page and are not per-ayah). |

**Why islamicstudies.info may be preferred for Maududi:**
The quran.com API returns Maududi commentary per-ayah, which loses the surah introduction sections that are a key feature of Tafhim. The islamicstudies.info HTML pages present the full surah content including the introduction, allowing us to extract `chunk_type: intro` records alongside `chunk_type: verse` records. If surah introductions are important (and they are — they are goldmines for thematic context), scrape islamicstudies.info rather than using the quran.com API.

**Verify the tafsir ID before running:**
```bash
curl -s "https://api.quran.com/api/v4/resources/tafsirs" | python3 -m json.tool | grep -A3 -i "maududi"
```

---

## Raw Data Format

Acquisition scripts must output JSONL to `data/raw/<scholar>/` with one record per line:

```json
{
    "surah": 2,
    "ayah_start": 255,
    "ayah_end": 255,
    "raw_text": "...",
    "chunk_type": "verse"
}
```

For Maududi surah introductions:
```json
{
    "surah": 2,
    "ayah_start": 0,
    "ayah_end": 0,
    "raw_text": "...",
    "chunk_type": "intro"
}
```

Files should be named by surah number, e.g. `001.jsonl`, `002.jsonl`, …, `114.jsonl`.

---

## Phase 2+ Corpus (Future)

| Scholar | Source | Language | Status |
|---|---|---|---|
| Al-Tabari | altafsir.com (Arabic) or digitised Arabic texts | Arabic | Not started |
| Al-Qurtubi | altafsir.com (Arabic) | Arabic | Not started |
| Al-Jalalayn | quranx.com or Feras Hamza translation (EN) | English | Not started |
| Ibn Ashur | Arabic-only; no complete English translation | Arabic | Not started |

---

## Licensing Summary

Neither Ibn Kathir (Dar-us-Salam) nor Maududi (The Islamic Foundation) are available under open licenses in English. Both are commercially copyrighted translations. The quran.com API and quranx.com tolerate personal/research use without formal licensing, but:

- Do **not** redistribute the raw or processed tafsir text in this repository.
- Do **not** commit `data/raw/`, `data/cleaned/`, `data/chunks/`, or `data/embedded/` to git (all are gitignored).
- For a public-facing commercial product, contact Dar-us-Salam Publications and The Islamic Foundation separately.

The Arabic originals of Ibn Kathir and Al-Tabari are in the public domain (medieval works).
