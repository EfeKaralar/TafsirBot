# The Six Tafsirs — Key Differences
## 1. Ibn Kathir (Tafsir al-Qur'an al-Azim, 14th c.)

- Method: Primarily tafsir bil-ma'thur — interprets Quran with Quran, then hadith, then companion reports
- Tone: Traditional Sunni, Hanbali-leaning, strong hadith criticism
- Strength: Hadith grading and cross-referencing; widely trusted for legal and theological rulings
- Weakness: Repetitive; sometimes accepts weak narrations (Isra'iliyyat) with commentary
- Chunk behavior: Long, chain-heavy passages; you'll need to strip isnad chains or they'll pollute your embeddings
- Audience fit: General Sunni learners, students of hadith


## 2. Al-Tabari (Jami' al-Bayan, 10th c.)

- Method: Most comprehensive classical ma'thur tafsir; collects all narrated opinions then adjudicates
- Tone: Encyclopedic, scholarly, quasi-judicial
- Strength: Unmatched breadth of early opinions; preserves opinions not found elsewhere; strong Arabic linguistic analysis
- Weakness: Enormous (30+ volumes); many opinions contradict each other; requires expertise to navigate
- Chunk behavior: Very long entries per ayah; multiple opinions per verse means RAG needs to preserve opinion markers ("some said X, others said Y")
- Audience fit: Researchers, scholars, comparative analysis


## 3. Al-Qurtubi (Al-Jami' li-Ahkam al-Qur'an, 13th c.)

- Method: Tafsir al-ahkam — legal-focused; Maliki jurisprudential lens
- Tone: Legal, analytical, comparative fiqh
- Strength: Best source for deriving rulings (ahkam) from Quranic verses; compares madhabs; covers social/ethical context
- Weakness: Non-legal verses get relatively less depth
- Chunk behavior: Dense legal reasoning sections; good candidate for metadata tagging by topic (prayer, marriage, inheritance, etc.)
- Audience fit: Students of Islamic law, fiqh comparativists


## 4. Tafsir al-Jalalayn (15th–16th c., Suyuti + father)

- Method: Tafsir bil-ra'y meets brevity — grammatical/semantic explanation, minimal elaboration
- Tone: Extremely terse; one or two sentences per phrase
- Strength: Fast reference; excellent for Arabic grammar and basic meaning; covers entire Quran in one slim volume
- Weakness: No depth on hadith, fiqh, or context; occasional errors flagged by later scholars
- Chunk behavior: Very short chunks; your RAG retrieval will get high precision but low depth — good as a "quick gloss" layer
- Audience fit: Arabic students, those wanting quick lexical clarity


## 5. Maududi — Tafhim al-Quran (20th c.)

- Method: Thematic/contextual; tafsir bil-ra'y with heavy socio-political lens
- Tone: Modern, accessible, occasionally polemical; Islamist political philosophy embedded
- Strength: Superb surah introductions explaining historical/thematic context; readable for English audiences; connects Quran to modern life
- Weakness: Ideological bias (Jamaat-e-Islami worldview); downplays classical scholarly disagreements; not a substitute for classical sources
- Chunk behavior: Surah introductions are goldmines for metadata/context; verse commentary is paragraph-length and self-contained — very RAG-friendly
- Audience fit: General modern readers, those seeking relevance to contemporary issues


## 6. Ibn Ashur (Al-Tahrir wal-Tanwir, 20th c.)

- Method: Linguistic, maqasid-based, reformist; tafsir bil-ra'y at its most rigorous
- Tone: Academic, rationalist, nuanced; engages Western scholarship and modern epistemology
- Strength: Maqasid al-Shariah framework; extraordinary Arabic linguistic precision; challenges weak narrations; addresses modernist questions
- Weakness: Very demanding; requires Arabic proficiency for full benefit; limited English translation availability
- Chunk behavior: Discursive, essay-style commentary — chunks need to be larger to preserve argument coherence
- Audience fit: Advanced students, academics, reform-oriented scholarship


## Comparison Table
| Tafsir | Era | Method | Length | English? | Best For RAG Use Case |
|---|---|---|---|---|---|
| Ibn Kathir | 14th c. | Ma'thur (hadith) | Long | ✅ Full | General Q&A, hadith linkage |
| Al-Tabari | 10th c. | Ma'thur (encyclopedic) | Very long | Partial | Scholarly opinion retrieval |
| Al-Qurtubi | 13th c. | Ahkam (legal) | Long | Partial | Fiqh/legal queries |
| Jalalayn | 15th c. | Ra'y (brief) | Short | ✅ Full | Quick gloss layer |
| Maududi | 20th c. | Contextual/modern | Medium | ✅ Full | Modern relevance, surah context |
| Ibn Ashur | 20th c. | Linguistic/maqasid | Long | Partial | Academic/linguistic queries |

## RAG Pipeline Recommendations Based on These Differences
- Chunking strategy should differ per tafsir. Al-Jalalayn warrants small chunks (per verse phrase); Al-Tabari and Ibn Ashur need larger chunks to preserve argumentative flow. Tag each chunk with surah, ayah_range, tafsir_name, topic_type (legal, linguistic, narrative, etc.).
- Metadata tagging matters. Al-Qurtubi chunks should be tagged with fiqh topics; Maududi's surah introductions deserve their own chunk type. This lets you route queries — a fiqh question can preferentially hit Qurtubi, a "what does this surah mean broadly" query hits Maududi's introductions.
- Consider a routing/blending layer. Rather than dumping all tafsirs into one vector store and hoping retrieval sorts it out, consider query classification first: is this a legal question? → weight Qurtubi. A hadith-context question? → weight Ibn Kathir. A linguistic question? → weight Jalalayn + Ibn Ashur.
- Handle isnads carefully. Ibn Kathir and Al-Tabari contain extensive hadith chains. You may want to either strip them to a separate metadata field or create a preprocessing step that separates the matn (text) from the isnad (chain) before embedding — otherwise chains will dominate the semantic space of chunks.
- Language alignment. If you're serving English users, Ibn Kathir (Dar-us-Salam translation), Jalalayn (Feras Hamza translation), and Maududi are the most complete. For the others, you'll likely be working with Arabic source texts and should decide whether to embed Arabic, English, or both, and whether to use multilingual embeddings.
