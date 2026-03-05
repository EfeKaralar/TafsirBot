# The Six Tafsirs — Key Differences
> **Document Version:** Revised & Fact-Checked  
> **Changes from original are noted inline with ⚠️ correction flags for transparency.**

---

## 1. Ibn Kathir (Tafsir al-Qur'an al-Azim, 14th c.)
*Ibn Kathir (c. 1300–1373 CE / d. 774 AH)*

- **Method:** Primarily *tafsir bil-ma'thur* — interprets Quran with Quran, then hadith, then companion reports
- **Tone:** Traditional Sunni, Athari-leaning in theology; strongly hadith-oriented
- **Strength:** Hadith grading and cross-referencing; widely trusted for legal and theological rulings
- **Weakness:** Repetitive; chains of transmission (*isnad*) dominate passages and can overwhelm the main commentary text
- **Chunk behavior:** Long, chain-heavy passages; you'll need to strip *isnad* chains or preprocess them separately, as they will pollute your embeddings
- **Audience fit:** General Sunni learners, students of hadith

> ⚠️ **Correction 1 — Madhab:** The original document describes Ibn Kathir as "Hanbali-leaning." This is a common misconception. Ibn Kathir belonged to the **Shafi'i** school of jurisprudence — he is listed in classical Shafi'i biographical dictionaries (*tabaqat al-Shafi'iyya*) and his own tafsir identifies him as such. His *theological* methodology was heavily shaped by his teacher Ibn Taymiyya (who was Hanbali), which may be the source of the confusion. Describing him as "Hanbali-leaning" risks misleading readers about his legal affiliation. A more accurate framing: **Shafi'i in fiqh, Athari/Salafi-adjacent in 'aqida methodology due to Ibn Taymiyya's influence.**

> ⚠️ **Correction 2 — Isra'iliyyat:** The original document states he "sometimes accepts weak narrations (Isra'iliyyat) with commentary." This badly misrepresents one of Ibn Kathir's most defining characteristics. His tafsir is in fact **famous for its critical stance against Isra'iliyyat** — Jewish and Christian narratives that entered the exegetical tradition — and is widely described as "almost devoid" of them. He actively flags and challenges such narrations where other mufassirun accepted them. The weakness to note instead is his *isnad*-heavy presentation style and occasional acceptance of *hadith da'if* (weak hadith) outside the Isra'iliyyat category.

---

## 2. Al-Tabari (Jami' al-Bayan, 10th c.)
*Ibn Jarir al-Tabari (838–923 CE / d. 310 AH)*

- **Method:** Most comprehensive classical *ma'thur* tafsir; collects all narrated opinions then adjudicates
- **Tone:** Encyclopedic, scholarly, quasi-judicial
- **Strength:** Unmatched breadth of early opinions; preserves opinions not found elsewhere; strong Arabic linguistic analysis
- **Weakness:** Enormous (30+ volumes); many opinions contradict each other; requires expertise to navigate
- **Chunk behavior:** Very long entries per *ayah*; multiple opinions per verse means RAG needs to preserve opinion markers ("some said X, others said Y"). Consider chunking by opinion unit, not by verse.
- **Audience fit:** Researchers, scholars, comparative analysis

---

## 3. Al-Qurtubi (Al-Jami' li-Ahkam al-Qur'an, 13th c.)
*Al-Qurtubi (1214–1273 CE / d. 671 AH)*

- **Method:** *Tafsir al-ahkam* — legal-focused; Maliki jurisprudential lens
- **Tone:** Legal, analytical, comparative fiqh
- **Strength:** Best source for deriving rulings (*ahkam*) from Quranic verses; compares madhabs; covers social/ethical context
- **Weakness:** Non-legal verses receive relatively less depth
- **Chunk behavior:** Dense legal reasoning sections; strong candidate for metadata tagging by topic (prayer, marriage, inheritance, etc.)
- **Audience fit:** Students of Islamic law, fiqh comparativists

---

## 4. Tafsir al-Jalalayn (15th–16th c.)
*Jalal al-Din al-Mahalli (d. 1459 CE) and Jalal al-Din al-Suyuti (d. 1505 CE)*

- **Method:** Grammatical/semantic explanation with deliberate brevity; minimal elaboration
- **Tone:** Extremely terse; often one or two sentences per Quranic phrase
- **Strength:** Fast reference; excellent for Arabic grammar and basic meaning; covers the entire Quran in one slim volume
- **Weakness:** No depth on hadith, fiqh, or historical context; occasional errors flagged by later scholars
- **Chunk behavior:** Very short chunks; RAG retrieval will yield high precision but low depth — best used as a "quick gloss" or semantic disambiguation layer alongside richer tafsirs
- **Audience fit:** Arabic students, those wanting quick lexical clarity

> ⚠️ **Correction 3 — Authorship:** The original document attributes this tafsir to "Suyuti + father." This is factually wrong. The two authors are **Jalal al-Din al-Mahalli** (the teacher, d. 1459) and his *student* **Jalal al-Din al-Suyuti** (d. 1505) — hence the name "Jalalayn" (the Two Jalals). Al-Mahalli was not Suyuti's father; he was his scholarly teacher. Al-Mahalli initiated the work (beginning with Surat al-Kahf), died before completing it, and Suyuti finished the remaining half. This is a significant biographical error that could undermine the document's credibility with readers familiar with Islamic scholarship.

---

## 5. Maududi — Tafhim al-Quran (20th c.)
*Abul A'la Maududi (1903–1979 CE)*

- **Method:** Thematic/contextual; *tafsir bil-ra'y* with a heavy socio-political lens
- **Tone:** Modern, accessible, occasionally polemical; Islamist political philosophy embedded throughout
- **Strength:** Superb surah introductions explaining historical and thematic context; readable for English audiences; connects the Quran to modern life
- **Weakness:** Ideological bias (Jamaat-e-Islami worldview); downplays classical scholarly disagreements; not a substitute for classical sources
- **Chunk behavior:** Surah introductions are goldmines for metadata/context and deserve their own chunk type. Verse-level commentary is paragraph-length and self-contained — very RAG-friendly.
- **Audience fit:** General modern readers, those seeking relevance to contemporary issues

---

## 6. Ibn Ashur (Al-Tahrir wal-Tanwir, 20th c.)
*Muhammad al-Tahir ibn Ashur (1879–1973 CE)*

- **Method:** Linguistic, *maqasid*-based, reformist; *tafsir bil-ra'y* at its most rigorous
- **Tone:** Academic, rationalist, nuanced; engages classical tradition deeply and addresses modern epistemological questions
- **Strength:** *Maqasid al-Shari'ah* framework applied systematically; extraordinary Arabic linguistic precision; challenges weak narrations; addresses modernist questions without abandoning classical method
- **Weakness:** Very demanding; requires strong Arabic proficiency for full benefit; English translation is incomplete and hard to source
- **Chunk behavior:** Discursive, essay-style commentary — chunks need to be larger to preserve argument coherence. Avoid splitting mid-argument.
- **Audience fit:** Advanced students, academics, reform-oriented scholarship

---

## Comparison Table

| Tafsir | Era | Author's Madhab | Method | Length | English? | Best RAG Use Case |
|---|---|---|---|---|---|---|
| Ibn Kathir | 14th c. | **Shafi'i** (fiqh); Athari-leaning (theology) | Ma'thur (hadith) | Long | ✅ Full | General Q&A, hadith linkage |
| Al-Tabari | 10th c. | — | Ma'thur (encyclopedic) | Very long | Partial | Scholarly opinion retrieval |
| Al-Qurtubi | 13th c. | Maliki | Ahkam (legal) | Long | Partial | Fiqh/legal queries |
| Jalalayn | 15th–16th c. | Shafi'i | Ra'y (brief, grammatical) | Short | ✅ Full | Quick gloss / disambiguation layer |
| Maududi | 20th c. | — | Contextual/modern | Medium | ✅ Full | Modern relevance, surah context |
| Ibn Ashur | 20th c. | Maliki | Linguistic/maqasid | Long | Partial | Academic/linguistic queries |

---

## RAG Pipeline Recommendations

**Chunking strategy should differ per tafsir.** Al-Jalalayn warrants small chunks (per verse phrase); Al-Tabari and Ibn Ashur need larger chunks to preserve argumentative flow. Tag each chunk with `surah`, `ayah_range`, `tafsir_name`, and `topic_type` (legal, linguistic, narrative, theological, etc.).

**Metadata tagging matters.** Al-Qurtubi chunks should be tagged with fiqh topics; Maududi's surah introductions deserve their own chunk type (e.g., `chunk_type: surah_intro`). This lets you route queries — a fiqh question can preferentially hit Al-Qurtubi, while a "what does this surah mean broadly" query hits Maududi's introductions.

**Consider a routing/blending layer.** Rather than dumping all tafsirs into one vector store and hoping retrieval sorts it out, consider query classification first:
- Legal question → weight Al-Qurtubi
- Hadith-context question → weight Ibn Kathir
- Linguistic/grammatical question → weight Jalalayn + Ibn Ashur
- Scholarly opinion survey → weight Al-Tabari
- Modern relevance → weight Maududi

**Handle isnads carefully.** Ibn Kathir and Al-Tabari contain extensive hadith chains. You may want to either strip them to a separate metadata field or create a preprocessing step that separates the *matn* (text body) from the *isnad* (chain of transmission) before embedding — otherwise chains will dominate the semantic space of chunks and degrade retrieval quality.

**Language alignment.** If you're serving English users, Ibn Kathir (Dar-us-Salam translation), Jalalayn (Feras Hamza translation), and Maududi (*Towards Understanding the Quran*) are the most complete and reliable. For Al-Tabari, Al-Qurtubi, and Ibn Ashur, you'll largely be working with Arabic source texts. Decide whether to embed Arabic, English, or both, and whether to use multilingual embeddings (e.g., `text-embedding-3-large` with multilingual fine-tuning or a dedicated Arabic model).

---

## Overall Integrity Notes & Suggestions

### Factual corrections summary
Three factual errors were identified and corrected above:
1. Ibn Kathir's madhab (Shafi'i, not Hanbali)
2. Ibn Kathir's treatment of Isra'iliyyat (he *criticizes* them, not accepts them)
3. Tafsir al-Jalalayn authorship (al-Mahalli + al-Suyuti, teacher-student, not father-son)

### Additional suggestions for project integrity

**Cite editions used.** For a RAG project especially, the specific edition and translation of each tafsir matters enormously for consistency. Specify which edition you are using (e.g., Dar-us-Salam for Ibn Kathir, Feras Hamza's translation for Jalalayn) and whether the text has been abridged, since abridgments can remove material relevant to retrieval.

**Note the abridgment problem for Ibn Kathir specifically.** The widely available English translation (Dar-us-Salam, 10 volumes) is an abridgment. The full Arabic is substantially longer. If you're embedding the English, be aware that hadith chains are often compressed or removed entirely — which affects the "Weakness" profile noted above.

**Be cautious about characterizing Maududi as ideologically biased without nuance.** While the ideological concern is valid and commonly noted by scholars, flagging it without context could be read as dismissive. Consider framing it as: his political philosophy is embedded in the commentary, which is both a strength (makes the Quran feel relevant) and a weakness (can skew readings away from classical scholarly consensus). This is more useful for a practitioner deciding how to weight his tafsir.

**Al-Tabari's madhab note.** Al-Tabari actually founded his own short-lived school of fiqh (the Jariri school), a detail worth noting in the table if thoroughness matters, rather than leaving his madhab column blank.

**Consider adding a "Theological Lens" field** to the comparison table. The difference between Ash'ari, Athari, and Maturidi creedal positions across these tafsirs affects how they handle certain verses (especially those touching on divine attributes). This is practically relevant for query routing.

**On translation quality for Maududi:** The English translation (*Towards Understanding the Quran*, published by The Islamic Foundation) is well-regarded and largely complete, but readers should be aware it is a translation of an Urdu original, adding one layer of interpretive distance from the Arabic source.

---

## Fiqh Manuals

### Reliance of the Traveller (*Umdat al-Salik*)

| Field | Details |
|---|---|
| **Phase** | **Phase 2 — Priority 1** |
| **Full title** | *Umdat al-Salik wa 'Uddat al-Nasik* (Reliance of the Traveller and Tools of the Worshipper) |
| **Author** | Ahmad ibn an-Naqib al-Misri (1302–1367 CE / d. 769 AH) |
| **Translator** | Nuh Ha Mim Keller (1991 edition, Amana Publications) |
| **Edition notes** | ~1,200 pages; bilingual Arabic/English; Al-Azhar certified — the first Islamic legal work in a European language to receive this certification. Includes extensive appendices from classical scholars (al-Ghazali, Ibn Qudama, al-Nawawi, al-Qurtubi, al-Dhahabi, Ibn Hajar), 391 biographical notes, 136 works cited, and a 95-page subject index. |
| **Madhab coverage** | **Shafi'i** (single madhab). The text follows the conclusions of Imam Nawawi's *Minhaj al-Talibin* and *al-Majmu'*. Keller's commentary occasionally notes positions of other madhabs, but the core legal text is Shafi'i throughout. |
| **Language / translation quality** | English (high quality). Keller's translation is precise and widely regarded as the standard English-language Shafi'i fiqh reference. The facing Arabic text allows cross-checking. |
| **Access method** | PDF scans available on Internet Archive (multiple uploads). The published book is commercially available (~$45). OCR quality on Archive scans is generally good given the clean typesetting of the Amana edition. |
| **Licensing status** | **Copyrighted** (Amana Publications). The original Arabic *matn* by al-Misri is public domain (14th-century text), but Keller's translation, commentary, and appendices are under copyright. Internet Archive uploads exist but their legal status is ambiguous. For a production RAG system, the copyright risk is moderate — the underlying rulings are not copyrightable, but Keller's specific English expression is. Consider ingesting the Arabic matn separately (Phase 3) and treating the English as a research/fair-use reference, or seeking publisher permission. |
| **Chunking strategy** | Excellent structure for chunking. The text is organized by topic heading (e.g., E: Purification, F: Prayer, K: Trade, M: Marriage, N: Divorce) with numbered subsections (e.g., e4.1, e4.2). Each numbered entry is typically a self-contained ruling of 1–5 sentences. **Chunk unit: individual numbered ruling** (e.g., `f8.17`), with section heading as metadata. This produces tight, well-scoped chunks with low ambiguity. |
| **RAG suitability** | **Excellent.** Serves queries like "What is the Shafi'i ruling on X?" with high precision. The numbered reference system is ideal for citation. **Weaknesses:** single-madhab only; does not present comparative positions systematically; Keller's commentary is interspersed and must be distinguished from al-Misri's original rulings. Estimated chunk size: 50–200 tokens per ruling. |

---

### Al-Hidaya (*The Guidance*)

| Field | Details |
|---|---|
| **Phase** | **Phase 2 — Priority 2** |
| **Full title** | *Al-Hidaya fi Sharh Bidayat al-Mubtadi* (The Guidance: A Commentary on the Beginning for the Beginner) |
| **Author** | Burhan al-Din al-Marghinani (1135–1197 CE / d. 593 AH) |
| **Translations** | Two English translations exist: (1) **Charles Hamilton** (1791) — translated from a Persian intermediary, not directly from Arabic; public domain; available on Internet Archive; archaic English. (2) **Imran Ahsan Khan Nyazee** (modern) — translated directly from Arabic; 2 volumes, ~1,066 pages total; published by Dar ul-Thaqafah / Istinarah Press; copyrighted. |
| **Edition notes** | Hamilton's translation was commissioned by the East India Company for colonial legal administration. It is the earliest English translation of any major Islamic legal text. The Nyazee translation is superior in accuracy and readability but is under copyright. |
| **Madhab coverage** | **Hanafi** (single madhab). Al-Hidaya is the most authoritative Hanafi fiqh manual in the classical curriculum. It systematically presents the positions of Abu Hanifa, Abu Yusuf, and Muhammad al-Shaybani, noting where they differ. It also references Shafi'i and Maliki positions for comparative purposes within its argumentation. |
| **Language / translation quality** | Hamilton (1791): archaic, indirect (Arabic → Persian → English), sometimes unreliable on technical terms, but serviceable and **public domain**. Nyazee (modern): accurate, clear, with scholarly footnotes — but **copyrighted**. |
| **Access method** | Hamilton: Internet Archive (multiple scans, OCR available via Tesseract 4.x). Cambridge University Press also published a scholarly edition. Nyazee: commercially available (~$30–50 per volume); no known open digital access. |
| **Licensing status** | Hamilton translation: **Public domain** (1791, well beyond any copyright term). Nyazee translation: **Copyrighted**. For Phase 2, the Hamilton translation is the viable option. Its archaic language will affect embedding quality — consider a preprocessing step to normalize 18th-century English spellings and legal vocabulary. |
| **Chunking strategy** | Al-Hidaya is organized by *kitab* (book) → *bab* (chapter) → individual *mas'ala* (legal question). Each *mas'ala* presents the ruling, the evidence, and often the counter-arguments of other scholars. **Chunk unit: individual mas'ala or sub-section**, tagged with the *kitab/bab* hierarchy. Hamilton's text has clear section breaks that map well to this structure. |
| **RAG suitability** | **Good for Hanafi coverage, with caveats.** The Hamilton translation fills a critical gap (Hanafi representation) using a public-domain source. **Weaknesses:** archaic language will degrade embedding-to-query similarity for modern English queries; the indirect translation chain introduces some inaccuracies; OCR quality on 230-year-old scans varies. Estimated chunk size: 100–400 tokens per mas'ala. A preprocessing pipeline should normalize archaic spellings ("Mussulman" → "Muslim", etc.) and strip colonial-era editorial apparatus. |

---

### Al-Fiqh al-Islami wa Adillatuh (Wahbah al-Zuhayli)

| Field | Details |
|---|---|
| **Phase** | **Phase 3 — Priority 1** |
| **Full title** | *Al-Fiqh al-Islami wa Adillatuh* (Islamic Jurisprudence and Its Evidences) |
| **Author** | Wahbah al-Zuhayli (1932–2015 CE) |
| **Edition notes** | 8 volumes in Arabic; first published 1984 by Dar al-Fikr (Damascus). Considered the most comprehensive modern multi-madhab fiqh reference. Covers all four Sunni schools systematically on every major topic, presenting the evidence (*adilla*) for each position. |
| **Madhab coverage** | **Multi-madhab** (all four Sunni schools). This is Al-Zuhayli's distinguishing feature: every topic presents the Hanafi, Maliki, Shafi'i, and Hanbali positions side by side with their respective evidences. This makes it the single most valuable source for the project's madhab-agnostic approach. |
| **Language / translation quality** | Arabic original. **No complete English translation exists.** Partial translations of selected chapters have appeared in academic journals and dissertations. Dar al-Fikr published a partial English edition of some volumes, but availability is extremely limited and quality is uneven. |
| **Access method** | Arabic PDF widely available (Dar al-Fikr edition scanned and freely distributed in Arabic-language Islamic digital libraries). For English, no viable path currently exists without commissioning translation or using machine translation with expert review. |
| **Licensing status** | **Copyrighted** (Dar al-Fikr). The Arabic PDF circulates freely in practice, but technically remains under copyright. |
| **Chunking strategy** | Superbly structured for RAG. Each topic is organized as: definition → Quranic evidence → hadith evidence → scholarly positions by madhab → preferred opinion → practical notes. **Chunk unit: per-topic, per-madhab position** — or the entire topic section if cross-madhab comparison is the goal. |
| **RAG suitability** | **The ideal fiqh source if the language barrier can be solved.** The multi-madhab, evidence-based structure maps perfectly to the project's requirements. **Phase 3 assignment** is due entirely to the language constraint. When Arabic ingestion is implemented (using `intfloat/multilingual-e5-large` and the separate `tafsir_ar` collection), this should be the first fiqh source ingested. Estimated chunk size: 300–800 tokens per madhab position within a topic. |

---

### Al-Mughni (Ibn Qudama)

| Field | Details |
|---|---|
| **Phase** | **Phase 3 — Priority 3** |
| **Full title** | *Al-Mughni* (The Enricher) |
| **Author** | Muwaffaq al-Din Ibn Qudama al-Maqdisi (1147–1223 CE / d. 620 AH) |
| **Edition notes** | 10+ volumes in Arabic. A comprehensive Hanbali fiqh encyclopedia that also extensively discusses and compares positions of other madhabs. One of the most respected works in all of Islamic jurisprudence. |
| **Madhab coverage** | **Hanbali** (primary), with extensive **multi-madhab comparison**. Ibn Qudama presents the Hanbali position then systematically engages Hanafi, Maliki, and Shafi'i positions — often more thoroughly than single-madhab manuals. |
| **Language / translation quality** | Arabic only. **No complete English translation exists.** Some chapters have been translated in academic contexts, but nothing approaching a usable corpus for RAG. |
| **Access method** | Arabic PDF freely available from multiple Islamic digital libraries (e.g., al-Maktaba al-Shamila, Internet Archive). |
| **Licensing status** | Original text is **public domain** (13th century). Modern critical editions may carry editorial copyright on footnotes and apparatus, but the *matn* itself is free. |
| **Chunking strategy** | Organized by *kitab* → *bab* → *mas'ala*. Each mas'ala presents the ruling, variant opinions, and evidence. Chunk by mas'ala. |
| **RAG suitability** | **Excellent for Hanbali coverage and comparative fiqh, but Arabic-only.** Phase 3 candidate. When ingested alongside Al-Zuhayli, provides deep Hanbali representation with rich comparative material. Estimated chunk size: 200–600 tokens per mas'ala. |

---

### Mukhtasar Khalil

| Field | Details |
|---|---|
| **Phase** | **Phase 3 — Priority 4** |
| **Full title** | *Mukhtasar* (Epitome) of Khalil ibn Ishaq al-Jundi |
| **Author** | Khalil ibn Ishaq al-Jundi (d. 1365 CE / d. 767 AH) |
| **Edition notes** | A highly compressed Maliki legal code. The standard Maliki teaching text for centuries, especially in North and West Africa. Extremely terse — designed to be memorized and unpacked by commentary. |
| **Madhab coverage** | **Maliki** (single madhab). Presents only the authoritative (*mashhur*) Maliki position with minimal elaboration. |
| **Language / translation quality** | Arabic only. **No complete English translation exists.** The text's extreme terseness makes it nearly unintelligible without its commentaries (*shuruh*), which are also Arabic-only. A 2014 partial English translation by David Santillana of a related Maliki mukhtasar exists but does not cover Khalil's text specifically. |
| **Access method** | Arabic text freely available in digital libraries. The commentaries (especially al-Dardir's *al-Sharh al-Kabir* and al-Dasuqi's *Hashiya*) would need to be ingested alongside the *matn* for the text to be meaningful. |
| **Licensing status** | **Public domain** (14th century). |
| **Chunking strategy** | The *matn* alone is too terse for useful RAG chunks. Ingestion would need to pair each *matn* phrase with its commentary expansion. This is a complex preprocessing challenge requiring Arabic NLP expertise. |
| **RAG suitability** | **Poor as a standalone source; useful only with commentary.** The terse style means isolated chunks would be cryptic even to Arabic-literate users. Lower priority than Al-Zuhayli (which already covers Maliki positions with evidence) unless comprehensive Maliki-specific detail is needed. Phase 3, lower priority. |

---

### Additional: Nur al-Idah (Hanafi Primer)

| Field | Details |
|---|---|
| **Phase** | **Phase 2 — Priority 4** |
| **Full title** | *Nur al-Idah wa Najat al-Arwah* (The Light of Clarification and the Salvation of Souls) |
| **Author** | Hasan ibn Ammar al-Shurunbulali (d. 1069 AH / 1659 CE) |
| **Translator** | Wesam Charkawi (2004, English translation available) |
| **Madhab coverage** | **Hanafi** (single madhab). Covers worship (*ibadat*) only — purification, prayer, fasting, hajj, zakat. Does not cover transactions, marriage, or other *mu'amalat*. |
| **Language / translation quality** | English translation is readable and reasonably accurate. Also available in bilingual format. |
| **Access method** | PDF freely available online; also commercially sold. |
| **Licensing status** | English translation is **copyrighted** but widely distributed digitally. Original Arabic is **public domain**. |
| **Chunking strategy** | Well-structured by topic with clear section headings. Chunk by ruling or sub-topic. |
| **RAG suitability** | **Good for worship-related Hanafi queries.** Supplements Al-Hidaya for the worship domain with clearer, more accessible language. Does not cover the full scope of fiqh. Estimated chunk size: 50–200 tokens per ruling. Useful as a supplement, not a standalone source. |

---

## Fiqh Encyclopedias

### Kuwaiti Fiqh Encyclopedia (*Al-Mawsu'a al-Fiqhiyya al-Kuwaitiyya*)

| Field | Details |
|---|---|
| **Phase** | **Phase 3 — Priority 2** |
| **Full title** | *Al-Mawsu'a al-Fiqhiyya al-Kuwaitiyya* (The Kuwaiti Encyclopedia of Islamic Jurisprudence) |
| **Institution** | Kuwait Ministry of Awqaf and Islamic Affairs |
| **Edition notes** | 45 volumes, approximately 17,650 pages. Compiled over 40 years (1965–2005) by a large committee of scholars. Organized alphabetically by jurisprudential term (*mustalah*). Each entry defines the term, surveys its treatment across all four Sunni madhabs, presents the relevant evidences, and notes points of scholarly agreement and disagreement. |
| **Madhab coverage** | **Multi-madhab** (all four Sunni schools). Consistently presents all four positions on each topic. This is its greatest strength for a madhab-agnostic RAG system. |
| **Language / translation quality** | Arabic only. **No English translation exists.** An Urdu translation was published in 2009 by the Islamic Fiqh Academy (India). No other translations are known. |
| **Access method** | Arabic PDF available from the Kuwait Ministry of Awqaf website and on Internet Archive. Also available as a mobile app and CD-ROM from the Ministry. The digital version published by Harf includes a thematic thesaurus with 27,000+ topics linked to the encyclopedia entries, making it highly navigable. |
| **Licensing status** | **Government publication (Kuwait Ministry of Awqaf).** The Ministry has made the text freely available digitally through its website and apps, which strongly suggests permissive intent for non-commercial scholarly use. No explicit open license has been identified, but government-produced educational works in many jurisdictions carry implied public access rights. This should be confirmed before production use. |
| **Chunking strategy** | The alphabetical-by-term structure is ideal for RAG. Each term entry is self-contained and structured as: linguistic definition → technical definition → madhab positions → evidence → related rulings. **Chunk unit: per-term entry**, or for longer entries, per-madhab-position within an entry. Metadata should include the term name, all madhabs discussed, and the relevant fiqh domain (worship, transactions, family law, etc.). |
| **RAG suitability** | **The strongest Phase 3 candidate for fiqh.** The alphabetical structure, multi-madhab coverage, and evidence-based approach make it the closest thing to a structured fiqh database. Its encyclopedic scope (covering terms from across all domains of fiqh) means it can answer an extremely wide range of jurisprudential queries. **Weaknesses:** Arabic-only; very large corpus requiring significant processing; some entries are extremely long and will need careful sub-chunking. Estimated chunk size: 200–1,000 tokens per madhab position within an entry; full entries can run to several thousand tokens. |

---

## Fatwa Databases

### IslamQA (islamqa.info)

| Field | Details |
|---|---|
| **Phase** | **Phase 2 — Priority 3** |
| **Full title** | Islam Question & Answer (islamqa.info) |
| **Institution** | International Islamic Academy Society (registered in Canada); originally founded by Sheikh Muhammad Salih al-Munajjid |
| **Content scope** | Large Q&A database covering creed, worship, transactions, family law, ethics, contemporary issues. Estimated 100,000+ answers in English and Arabic. Each entry follows a question-then-detailed-answer format with Quran/hadith citations. |
| **Madhab coverage** | **Hanbali-leaning** with Salafi theological orientation. The majority of rulings follow the Hanbali school or the positions of Ibn Taymiyya and Ibn al-Qayyim. Occasionally references other madhabs for comparison but is not systematically multi-madhab. The bot would need to tag these responses with `madhab: hanbali` (or `unspecified` for general answers) and ensure they are balanced against other sources. |
| **Language / translation quality** | English and Arabic. The English content is generally well-written and accessible, though the quality varies as the site has grown. Scholarly citations are usually precise. |
| **Access method** | No public API. The site has a clear URL structure (e.g., `islamqa.info/en/answers/XXXXX`) that is amenable to structured scraping. An existing Kaggle dataset and several GitHub scraping tools exist, suggesting the site has been successfully scraped before. |
| **Licensing status** | **Copyrighted.** The Terms of Use explicitly claim intellectual property protection over the site's content. However, the terms also state the site's mission is to spread Islamic knowledge. The copyright claim primarily targets commercial reproduction and plagiarism, not research use. The user-submitted questions grant the site a broad license. **Risk assessment:** moderate. Using scraped content in a non-commercial, attribution-preserving, scholarly-context RAG system is legally gray but arguably aligned with the site's educational mission. Proceed with caution; attribution is essential. |
| **Chunking strategy** | Each Q&A is a natural chunk unit. The question provides the query context; the answer provides the ruling and reasoning. **Chunk unit: one Q&A pair** (question + full answer). Longer answers (3,000+ words) may need sub-chunking by sub-topic, preserving the original question as metadata. |
| **RAG suitability** | **Good for Hanbali-perspective answers to practical questions.** The Q&A format is highly RAG-friendly — the question text closely matches how users phrase queries. **Weaknesses:** strong Hanbali/Salafi bias means it cannot be the sole fatwa source; the site's framing sometimes presents one opinion as definitive when scholarly disagreement exists; some answers are lengthy and discursive. Estimated chunk size: 200–800 tokens for typical answers; some exceed 2,000 tokens. |

---

### SeekersGuidance Answers Archive

| Field | Details |
|---|---|
| **Phase** | **Phase 2 — Priority 2** |
| **Full title** | SeekersGuidance Answers (seekersguidance.org/answers/) |
| **Institution** | SeekersGuidance Global, founded by Shaykh Faraz Rabbani |
| **Content scope** | Over 20,000 Q&A responses (per their site header). Answers are written by qualified scholars with clear attribution. Topics span worship, transactions, family law, ethics, spirituality, and contemporary issues. Organized by category (Hanafi Fiqh, Shafi'i Fiqh, Maliki Fiqh, General Counsel, etc.). |
| **Madhab coverage** | **Multi-madhab.** Answers are categorized by school: primarily Hanafi (the largest category) and Shafi'i, with smaller Maliki and Hanbali sections. Each answer is typically grounded in a specific madhab and attributed to a named scholar. This explicit madhab-tagging is extremely valuable for metadata. |
| **Language / translation quality** | English (native quality). Answers are written by English-fluent scholars, many of whom trained in traditional Islamic institutions. The writing is accessible, well-structured, and consistently includes question restatement + detailed reasoning + conclusion. |
| **Access method** | No public API. Standard WordPress site with category-based URL structure (`/answers/hanafi-fiqh/`, `/answers/shafii-fiqh/`, etc.). Amenable to structured scraping via category pages with pagination. Individual answer pages are clean HTML with minimal JavaScript rendering. |
| **Licensing status** | **Copyrighted** (SeekersGuidance). No explicit open license. However, SeekersGuidance operates as a non-profit educational organization with a stated mission to make Islamic knowledge freely accessible. Their content is freely viewable online without registration. **Risk assessment:** similar to IslamQA — non-commercial, attributed use in an educational RAG system is likely within the spirit of their mission, but formal permission should be sought. Contacting Shaykh Faraz Rabbani's team for partnership or permission is recommended given the aligned missions. |
| **Chunking strategy** | Each Q&A is a natural chunk. Answers follow a consistent template: Bismillah → question reference → detailed ruling → evidence → practical advice → closing du'a. **Chunk unit: one Q&A.** The madhab category of the URL should be captured as metadata. Scholar attribution should be preserved. |
| **RAG suitability** | **Excellent.** The multi-madhab coverage, consistent format, English-native quality, and scholar attribution make this one of the best fatwa sources for the project. The existing category structure maps directly to the `madhab` metadata field. **Weaknesses:** smaller corpus than IslamQA; some answers are pastoral/spiritual rather than strictly legal (these should be tagged as `corpus_type: general_counsel` rather than `fatwa`). Estimated chunk size: 150–500 tokens for typical answers. |

---

### Dar al-Ifta al-Misriyya

| Field | Details |
|---|---|
| **Phase** | **Phase 2 — Priority 5** (English portal); **Phase 3 — Priority 3** (Arabic corpus) |
| **Full title** | Dar al-Ifta al-Misriyya (The Egyptian House of Fatwa) |
| **Institution** | Official Egyptian government fatwa body, affiliated with the Grand Mufti of Egypt |
| **Content scope** | One of the oldest and most authoritative fatwa institutions in the Sunni world (established 1895). Issues rulings on contemporary issues. Maintains an English portal with selected translated fatwas. |
| **Madhab coverage** | Historically **Hanafi** (as the official madhab of the Ottoman and later Egyptian legal system), but modern fatwas draw from all four madhabs and often present a multi-madhab perspective. The institution takes a *tarjih* (preference-based) approach rather than strict adherence to a single school. Tag as `madhab: multi` for most modern fatwas. |
| **Language / translation quality** | Arabic (primary) and English (selected translations). The English portal (dar-alifta.org/en) has a curated selection of translated fatwas. English quality is adequate but sometimes stilted (non-native translation). The Arabic corpus is substantially larger and higher quality. |
| **Access method** | The English portal has a browsable, paginated structure. No public API. The Arabic site has a more extensive database. Web scraping is technically feasible but should be approached respectfully given its governmental status. |
| **Licensing status** | **Government publication.** Fatwas issued by a government body in the course of its official function carry a strong argument for public domain or permissive use. However, no explicit open license has been found. The institution's public mission (providing accessible Islamic legal guidance) supports non-commercial educational use. |
| **Chunking strategy** | Each fatwa is a natural chunk: question + ruling + reasoning. The English translations tend to be concise (200–500 words). The Arabic originals are often longer with more detailed evidence. |
| **RAG suitability** | **Moderate for Phase 2 (English), strong for Phase 3 (Arabic).** The English portal is too small to be a primary source but adds institutional authority and multi-madhab perspective. The Arabic corpus is large and authoritative. **Weaknesses (English):** limited corpus size; translation quality is uneven; not all fatwas include detailed reasoning. Estimated chunk size: 100–400 tokens (English); 200–800 tokens (Arabic). |

---

### Islamweb Fatawa (islamweb.net)

| Field | Details |
|---|---|
| **Phase** | **Phase 2 — Priority 4** |
| **Full title** | Islamweb Fatwa Center (islamweb.net/en/fatwa) |
| **Institution** | Islamweb, a project of the Qatar Ministry of Awqaf and Islamic Affairs |
| **Content scope** | Large English fatwa database with thousands of Q&A entries. Also has Arabic, French, and other language sections. Covers a wide range of topics including worship, transactions, family law, contemporary issues. |
| **Madhab coverage** | Broadly Sunni, drawing from all four madhabs without strict adherence to one school. Some answers lean toward the majority opinion across schools; others present comparative positions. Madhab attribution is inconsistent — some answers specify the school, others do not. Tag as `madhab: unspecified` unless the answer explicitly identifies a school. |
| **Language / translation quality** | English section is functional but translation quality is mixed — some answers read as direct (sometimes awkward) translations from Arabic. The site has been active since the early 2000s, and quality has improved over time. |
| **Access method** | No public API. Standard web structure with numbered fatwa URLs. Amenable to scraping. |
| **Licensing status** | **Government-affiliated publication** (Qatar Ministry of Awqaf). Similar considerations as the Kuwaiti Fiqh Encyclopedia — government educational publications carry an implied permissive intent. No explicit open license found. |
| **Chunking strategy** | One Q&A per chunk. Answers tend to be concise (100–400 words in English). |
| **RAG suitability** | **Moderate.** Fills out corpus volume and provides a different institutional perspective. **Weaknesses:** inconsistent madhab attribution; uneven English quality; some answers are brief and lack detailed reasoning; less rigorous than IslamQA or SeekersGuidance in scholarly apparatus. Estimated chunk size: 100–300 tokens. Lower priority than SeekersGuidance and IslamQA due to quality concerns. |

---

### Additional: IslamQA.org (Multi-Source Aggregator)

| Field | Details |
|---|---|
| **Phase** | **Phase 2 — Priority 6** (evaluation only) |
| **Full title** | IslamQA.org (distinct from islamqa.info) |
| **Institution** | An independent aggregator that collects Q&A from over 35 Islamic institutions and muftis (including Askimam.org, SeekersGuidance, DarulIftaBirmingham, Muftionline.co.za, etc.) |
| **Content scope** | Over 97,000 Q&A entries aggregated from multiple sources. Organized by madhab: ~90,000 Hanafi, ~6,500 Shafi'i, ~270 Maliki, ~250 Hanbali. |
| **Madhab coverage** | Heavily Hanafi-skewed due to the source institutions (many are Deobandi Hanafi). Multi-madhab in theory but lopsided in practice. |
| **Notes** | **Not recommended as a primary ingestion source.** The aggregated content originates from other sites (many of which are better accessed directly). Using IslamQA.org introduces attribution complexity, potential duplication with SeekersGuidance content already ingested, and licensing issues with the original source institutions. However, it is useful as a **discovery tool** to identify additional high-quality source institutions for direct engagement. |

---

## Hadith Collections

### General Notes on Hadith Ingestion

**Primary acquisition method:** The Sunnah.com API (`sunnah.com/api`, documented at `sunnah.stoplight.io/docs/api/`) provides structured JSON access to all major collections with English translations, Arabic text, hadith numbering, book/chapter metadata, and (where available) grading information. An API key is required and can be requested via their GitHub repository. A Python wrapper (`sunnah-api` on PyPI) is also available. Sunnah.com lists the following **primary collections**: Sahih al-Bukhari, Sahih Muslim, Sunan an-Nasa'i, Sunan Abi Dawud, Jami` at-Tirmidhi, Sunan Ibn Majah, Muwatta Malik, Musnad Ahmad, and Sunan ad-Darimi. **Secondary/selection collections** include: An-Nawawi's 40 Hadith, Riyad as-Salihin, Al-Adab Al-Mufrad, Ash-Shama'il Al-Muhammadiyah, Mishkat al-Masabih, Bulugh al-Maram, and others.

**Grading availability varies by collection.** Sunnah.com provides hadith grades for many but not all entries. Bukhari and Muslim are universally accepted as *sahih* by scholarly consensus, so individual grading is less critical there. For the Sunan collections, per-hadith grading (typically from al-Albani's authentication work) is often included. Musnad Ahmad grading coverage is less complete.

**Chunk metadata for all hadith collections** follows the schema specified in the project brief: `corpus_type: hadith`, `hadith_collection`, `hadith_number`, `chapter_title`, `grade`, `madhab: multi`.

---

### Sahih al-Bukhari

| Field | Details |
|---|---|
| **Phase** | **Phase 2 — Priority 1** |
| **Compiler** | Imam Muhammad al-Bukhari (810–870 CE / d. 256 AH) |
| **Size** | ~7,563 hadith (with repetitions); ~2,602 unique hadith. Sunnah.com lists 7,291 total available with 7,277 accessible via API. |
| **English translation** | Dr. M. Muhsin Khan translation (the standard English reference). Available in full on Sunnah.com. |
| **Sunnah.com API coverage** | **Full.** All books and hadith available. English and Arabic text provided. Grading: all hadith are *sahih* by definition (the entire collection is authenticated). |
| **Chunking notes** | Each hadith is a natural chunk unit. Include: hadith number, book/chapter title, narrator chain summary (or strip for embedding purity — keep full chain in metadata), matn (text body), and grade (`sahih`). Some hadith are repeated across chapters with different chains — decide whether to deduplicate (losing chapter context) or keep duplicates (inflating corpus but preserving thematic placement). **Recommendation:** keep duplicates but add a `is_duplicate_of` metadata field linking to the primary occurrence. |
| **RAG suitability** | **Highest priority hadith source.** The most cited hadith collection in all of Islamic scholarship. Virtually every fiqh and tafsir discussion references Bukhari. The Khan translation is clear and widely accepted. Estimated chunk size: 50–300 tokens per hadith. |

---

### Sahih Muslim

| Field | Details |
|---|---|
| **Phase** | **Phase 2 — Priority 2** |
| **Compiler** | Imam Muslim ibn al-Hajjaj (815–875 CE / d. 261 AH) |
| **Size** | ~7,500 hadith (with repetitions). Sunnah.com provides full coverage. |
| **English translation** | Abdul Hamid Siddiqui translation (the standard English reference on Sunnah.com). |
| **Sunnah.com API coverage** | **Full.** All books and hadith available. All hadith are *sahih* by definition. |
| **Chunking notes** | Same approach as Bukhari. Muslim's arrangement is generally considered more systematically organized by topic than Bukhari's. Less repetition across chapters. |
| **RAG suitability** | **Essential companion to Bukhari.** Together, the "two Sahihs" cover the vast majority of hadith cited in scholarly literature. Muslim often includes variant wordings and longer chains that Bukhari abridges, so including both increases coverage significantly. Estimated chunk size: 50–300 tokens per hadith. |

---

### Sunan Abu Dawud

| Field | Details |
|---|---|
| **Phase** | **Phase 2 — Priority 3** |
| **Compiler** | Imam Abu Dawud al-Sijistani (817–889 CE / d. 275 AH) |
| **Size** | ~5,274 hadith. Sunnah.com provides full coverage. |
| **English translation** | Ahmad Hasan translation (available on Sunnah.com). |
| **Sunnah.com API coverage** | **Full.** Grading is available for most hadith (typically al-Albani's authentication: sahih, hasan, or da'if). |
| **Chunking notes** | Standard hadith chunking. The `grade` metadata field is critical here since the collection includes hadith of varying authenticity. Abu Dawud himself sometimes comments on a hadith's status — these comments should be preserved in the chunk or metadata. |
| **RAG suitability** | **Strong fiqh orientation.** Abu Dawud compiled his collection specifically to gather hadith used as evidence in legal rulings. Many hadith here are directly cited in Hanafi, Maliki, Shafi'i, and Hanbali legal discussions. This makes it the most fiqh-relevant hadith collection after the two Sahihs. **Weakness:** includes more weak hadith than Bukhari/Muslim — grading metadata is essential. Estimated chunk size: 50–250 tokens per hadith. |

---

### Jami at-Tirmidhi

| Field | Details |
|---|---|
| **Phase** | **Phase 2 — Priority 4** |
| **Compiler** | Imam al-Tirmidhi (824–892 CE / d. 279 AH) |
| **Size** | ~3,956 hadith. Sunnah.com provides full coverage. |
| **English translation** | Abu Khaliyl translation (available on Sunnah.com). |
| **Sunnah.com API coverage** | **Full.** Grading available for most hadith. |
| **Chunking notes** | Tirmidhi's collection has a unique feature: he frequently appends his own scholarly commentary after each hadith, noting its grade, which scholars acted upon it, and which madhabs cite it as evidence. **These commentary notes are extremely valuable for RAG** and should be preserved as part of the chunk (or as a separate `scholar_commentary` metadata field). They essentially provide built-in cross-references to fiqh positions. |
| **RAG suitability** | **Excellent due to built-in scholarly apparatus.** Tirmidhi's grading notes and fiqh cross-references make his collection uniquely self-documenting. A query about the scholarly basis for a ruling can surface both the hadith and Tirmidhi's note about which scholars accepted it. **Weakness:** some entries are brief with minimal commentary. Estimated chunk size: 50–350 tokens per hadith (longer when commentary is included). |

---

### Sunan an-Nasa'i

| Field | Details |
|---|---|
| **Phase** | **Phase 2 — Priority 5** |
| **Compiler** | Imam an-Nasa'i (829–915 CE / d. 303 AH) |
| **Size** | ~5,758 hadith. Sunnah.com provides full coverage. |
| **English translation** | Nasiruddin al-Khattab translation (available on Sunnah.com). |
| **Sunnah.com API coverage** | **Full.** Grading available for most hadith. |
| **Chunking notes** | Standard hadith chunking. Nasa'i is known for being particularly strict in his acceptance criteria — his collection is often considered the most rigorously authenticated of the four Sunan. |
| **RAG suitability** | **Good supplementary source.** Adds coverage for hadith not found in the other collections and provides an additional authentication perspective. Significant overlap with Bukhari and Muslim on major hadith, but unique material on more specific legal topics. Estimated chunk size: 50–200 tokens per hadith. |

---

### Sunan Ibn Majah

| Field | Details |
|---|---|
| **Phase** | **Phase 2 — Priority 6** |
| **Compiler** | Imam Ibn Majah (824–887 CE / d. 273 AH) |
| **Size** | ~4,341 hadith. Sunnah.com provides full coverage. |
| **English translation** | Nasiruddin al-Khattab translation (available on Sunnah.com). |
| **Sunnah.com API coverage** | **Full.** Grading available. |
| **Chunking notes** | Standard hadith chunking. Ibn Majah includes a higher proportion of weak and disputed hadith compared to the other five books of the Kutub al-Sittah. The `grade` metadata field is especially important here. |
| **RAG suitability** | **Lower priority within the Kutub al-Sittah.** Completes the "six books" but has the highest weak-hadith ratio. Substantial overlap with Abu Dawud and Tirmidhi. Unique material (~1,300 hadith not found in the other five) includes some weak narrations. **Recommendation:** include for completeness of the Kutub al-Sittah, but flag the higher proportion of weak hadith and ensure grading is always surfaced. Estimated chunk size: 50–200 tokens per hadith. |

---

### Muwatta Malik

| Field | Details |
|---|---|
| **Phase** | **Phase 2 — Priority 3** (tied with Abu Dawud) |
| **Compiler** | Imam Malik ibn Anas (711–795 CE / d. 179 AH) |
| **Size** | ~1,900 entries (hadith + scholar opinions + Medinan practice reports). Sunnah.com provides full coverage. |
| **English translation** | Available on Sunnah.com. Multiple English translations exist (Bewley, Rahimuddin). |
| **Sunnah.com API coverage** | **Full.** |
| **Dual nature note** | The Muwatta is simultaneously a hadith collection and a Maliki fiqh text. Imam Malik includes not only Prophetic hadith but also the opinions of Companions, Successors, and reports of Medinan scholarly practice (*'amal ahl al-Madina*). This dual nature is critical for metadata tagging. **Recommendation:** tag each entry with `corpus_type: hadith` for Prophetic hadith entries, and `corpus_type: fiqh` for entries that report scholarly practice or Malik's own legal opinions. Add `madhab: maliki` for the latter. Many entries combine both — in such cases, consider creating two chunks from a single entry (one hadith chunk, one fiqh chunk) or use `corpus_type: hadith` with a `fiqh_relevance: maliki` metadata flag. |
| **Chunking notes** | The Muwatta's entries are generally shorter than the Sunan collections. Many entries are self-contained legal discussions with hadith evidence. |
| **RAG suitability** | **Uniquely valuable as both hadith and Maliki fiqh.** Fills the Maliki gap in the Phase 2 fiqh corpus while simultaneously adding to the hadith corpus. Malik's legal commentary on the hadith he narrates provides exactly the kind of "scholarly reasoning" the project brief calls for. **Weakness:** the English translation quality varies between editions; choose the Sunnah.com version for consistency. Estimated chunk size: 50–250 tokens per entry. |

---

### Musnad Ahmad

| Field | Details |
|---|---|
| **Phase** | **Phase 2 — Priority 7** |
| **Compiler** | Imam Ahmad ibn Hanbal (780–855 CE / d. 241 AH) |
| **Size** | ~28,199 hadith (Sunnah.com figure). The largest of the major hadith collections. Organized by narrator (Companion), not by topic. |
| **English translation** | Nasir Khattab translation (available on Sunnah.com). |
| **Sunnah.com API coverage** | **Full.** The entire collection is available with English translation. Grading availability is **partial** — not all hadith have grades assigned in the Sunnah.com data. |
| **Selective ingestion recommendation** | Given the collection's massive size and partial grading, **selective ingestion is recommended.** Options: (1) ingest only hadith with confirmed *sahih* or *hasan* grades (requires grading data to be available); (2) ingest only hadith cited in other ingested sources (via cross-referencing — a complex but high-value approach); (3) ingest by chapter and prioritize chapters covering topics not well-covered by the other six collections. **Full ingestion would add ~28K chunks** — feasible technically but may introduce noise from ungraded/weak hadith without proportional retrieval benefit over the already-ingested Kutub al-Sittah. |
| **Chunking notes** | Standard hadith chunking per entry. The narrator-based (rather than topic-based) organization means chapter metadata is less useful for topic routing than in the Sunan collections. |
| **RAG suitability** | **Large but with diminishing returns.** Many hadith in the Musnad overlap with the Kutub al-Sittah. The unique material is substantial (~10,000+ hadith not found elsewhere) but mixed in authentication quality. Lower priority than the six canonical collections unless comprehensive hadith coverage is a project goal. Estimated chunk size: 50–300 tokens per hadith. |

---

### Sunan ad-Darimi

| Field | Details |
|---|---|
| **Phase** | **Phase 2 — Priority 8** |
| **Compiler** | Imam ad-Darimi (797–869 CE / d. 255 AH) |
| **Size** | ~3,500 hadith. Available on Sunnah.com. |
| **English translation** | Available on Sunnah.com. |
| **Sunnah.com API coverage** | **Full.** |
| **RAG suitability** | **Supplementary.** Not part of the Kutub al-Sittah but included in some scholars' "nine books" canon. Contains unique material not found in the six canonical collections. Lower priority than the canonical six. Estimated chunk size: 50–200 tokens per hadith. |

---

### Additional Sunnah.com Collections Worth Noting

| Collection | RAG Value | Phase 2 Priority |
|---|---|---|
| **Riyad as-Salihin** (Imam Nawawi) | High — curated selection of hadith organized by ethical/spiritual topic; excellent for general Islamic guidance queries. Each hadith is pre-categorized by theme. | Priority 9 (supplement) |
| **Bulugh al-Maram** (Ibn Hajar) | High — specifically collects hadith used as evidence for fiqh rulings; organized by fiqh topic. Directly maps to the project's fiqh expansion goals. | Priority 8 (supplement, tied with Darimi) |
| **Mishkat al-Masabih** | Moderate — a compilation from multiple sources organized by topic, with hadith grading. Useful but largely overlaps with the primary collections. | Lower priority |
| **An-Nawawi's 40 Hadith** | Small but iconic — 42 hadith considered foundational to Islamic belief and practice. Every chunk is universally recognized. Good as a "seed" collection for testing the pipeline. | Testing/seeding |

---

## Contemporary Scholarly Works in English

### Yusuf al-Qaradawi

| Field | Details |
|---|---|
| **Phase** | **Phase 2 — Priority 7** (selected works only) |
| **Author** | Yusuf al-Qaradawi (1926–2022 CE) |
| **Key English works** | *The Lawful and the Prohibited in Islam* (*Al-Halal wal-Haram fil-Islam*) — the most widely available English work; covers a broad range of practical rulings on daily life topics in an accessible format. *Fiqh al-Zakat* — comprehensive treatment of zakat, translated into English. *Priorities of the Islamic Movement in the Coming Phase* — less relevant for fiqh but useful for contextual understanding. |
| **Madhab coverage** | Al-Qaradawi takes a **comparative, non-madhab-bound approach** (*fiqh al-muwazanat*). He draws from all four schools and sometimes selects what he considers the strongest opinion regardless of school. Tag as `madhab: multi`. |
| **Access method** | *The Lawful and the Prohibited* is widely available as PDF (multiple editions). The text is structured by topic (food, dress, family, economics, etc.) with clear chapter divisions. OCR-ready. |
| **Licensing status** | **Copyrighted** (various publishers). PDF scans circulate freely online. |
| **Chunking strategy** | Topic-based chapters with sub-headings. Chunk by sub-topic. Each section presents the question, surveys opinions, and gives a reasoned conclusion. |
| **RAG suitability** | **Good for practical, contemporary, multi-madhab guidance.** *The Lawful and the Prohibited* is particularly well-suited because it addresses the kinds of practical questions users actually ask (music, images, food, interest, clothing, etc.) in an accessible, reasoned style. **Weaknesses:** Al-Qaradawi is a polarizing figure — his views are mainstream in much of the Muslim world but controversial in Salafi and some conservative circles. His opinions should be attributed clearly and balanced against other sources. **Note:** some of his positions on political and social issues have generated significant controversy; the bot should not present these as consensus views. |

---

### Mohammad Hashim Kamali

| Field | Details |
|---|---|
| **Phase** | **Phase 2 — Priority 8** (reference/supplementary) |
| **Author** | Mohammad Hashim Kamali (b. 1944), Afghan-born professor of Islamic jurisprudence |
| **Key English works** | *Principles of Islamic Jurisprudence* — the standard English-language textbook on usul al-fiqh (legal methodology). Covers: sources of law, ijtihad, qiyas (analogical reasoning), istihsan, maslaha, 'urf (custom), etc. Published by The Islamic Texts Society (Cambridge). |
| **Madhab coverage** | **Cross-madhab, methodological.** Kamali explains *how* the schools derive rulings rather than presenting the rulings themselves. This is meta-fiqh — useful for the bot to explain *why* scholars disagree, not just *what* they disagree on. |
| **Access method** | Published book, commercially available. PDF scans exist online. |
| **Licensing status** | **Copyrighted** (Islamic Texts Society). |
| **RAG suitability** | **Niche but valuable for methodology queries.** When a user asks "Why do the four schools differ on X?" the bot could retrieve Kamali's explanation of the underlying methodological principle. Not suitable for direct fiqh rulings. Chunk by chapter sub-section. Estimated chunk size: 200–500 tokens. **Lower priority** than direct fiqh sources because the bot's primary use case is presenting rulings, not explaining legal theory. Consider Phase 2 supplementary status. |

---

## Phase Assignment Summary

| # | Source | Category | Phase | Priority | Madhab | RAG Suitability Note |
|---|---|---|---|---|---|---|
| 1 | **Sahih al-Bukhari** | Hadith | 2 | 1 | Multi | Most-cited hadith collection; full API coverage; natural chunk units; highest priority |
| 2 | **Sahih Muslim** | Hadith | 2 | 2 | Multi | Essential companion to Bukhari; full API coverage; together they cover the core hadith canon |
| 3 | **Reliance of the Traveller** | Fiqh Manual | 2 | 1 | Shafi'i | Best-structured English fiqh manual; numbered rulings map perfectly to chunks; copyright concern |
| 4 | **SeekersGuidance Answers** | Fatwa DB | 2 | 2 | Multi | Multi-madhab, English-native, scholar-attributed; excellent Q&A format for RAG |
| 5 | **Sunan Abu Dawud** | Hadith | 2 | 3 | Multi | Strongest fiqh-oriented hadith collection; per-hadith grading available |
| 6 | **Muwatta Malik** | Hadith/Fiqh | 2 | 3 | Maliki | Dual hadith/fiqh nature fills Maliki gap; unique scholarly practice reports |
| 7 | **Al-Hidaya** (Hamilton) | Fiqh Manual | 2 | 2 | Hanafi | Public-domain Hanafi manual; archaic language needs preprocessing; fills critical Hanafi gap |
| 8 | **IslamQA** (islamqa.info) | Fatwa DB | 2 | 3 | Hanbali | Large Q&A corpus; strong Hanbali representation; bias must be balanced |
| 9 | **Jami at-Tirmidhi** | Hadith | 2 | 4 | Multi | Unique built-in grading commentary; fiqh cross-references in each entry |
| 10 | **Islamweb Fatawa** | Fatwa DB | 2 | 4 | Mixed | Government-backed; adds volume; inconsistent madhab attribution |
| 11 | **Sunan an-Nasa'i** | Hadith | 2 | 5 | Multi | Rigorous authentication; completes Kutub al-Sittah |
| 12 | **Dar al-Ifta (English)** | Fatwa DB | 2 | 5 | Multi | Official Egyptian fatwas; authoritative but small English corpus |
| 13 | **Sunan Ibn Majah** | Hadith | 2 | 6 | Multi | Completes the six books; higher weak-hadith ratio; include with grading |
| 14 | **Musnad Ahmad** | Hadith | 2 | 7 | Multi | Very large; selective ingestion recommended; partial grading |
| 15 | **Al-Qaradawi** (selected works) | Contemporary | 2 | 7 | Multi | Practical contemporary rulings; polarizing author; attribute carefully |
| 16 | **Kamali** (Principles) | Contemporary | 2 | 8 | Cross-madhab | Legal methodology reference; niche but explains *why* scholars differ |
| 17 | **Nur al-Idah** | Fiqh Manual | 2 | 4 | Hanafi | Hanafi worship primer; supplements Al-Hidaya for ibadat domain |
| 18 | **Sunan ad-Darimi** | Hadith | 2 | 8 | Multi | Supplementary; not part of canonical six but available via API |
| 19 | **Al-Fiqh al-Islami wa Adillatuh** | Fiqh Manual | 3 | 1 | Multi | The ideal multi-madhab fiqh reference; Arabic-only blocks Phase 2 use |
| 20 | **Kuwaiti Fiqh Encyclopedia** | Fiqh Encyclopedia | 3 | 2 | Multi | Alphabetical structure perfect for RAG; 45 volumes; Arabic-only |
| 21 | **Dar al-Ifta (Arabic)** | Fatwa DB | 3 | 3 | Multi | Much larger Arabic corpus than English portal; government authority |
| 22 | **Al-Mughni** (Ibn Qudama) | Fiqh Manual | 3 | 3 | Hanbali | Deep Hanbali reference with comparative coverage; Arabic-only |
| 23 | **Mukhtasar Khalil** | Fiqh Manual | 3 | 4 | Maliki | Too terse without commentary; requires paired ingestion with *sharh* |
