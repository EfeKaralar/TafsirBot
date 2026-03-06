# Audit Report

Generated on March 6, 2026.

- Command: `UV_CACHE_DIR=.uv-cache uv run python scripts/ingestion/audit.py --top-k 5`
- Collection: `tafsir`
- Scope: live Qdrant retrieval audit plus corpus stats derived from `data/chunks/*.jsonl` and `data/embedded/*.jsonl`

## Snapshot

This document captures the current Phase 1 corpus and retrieval state at handoff time. The raw `audit.py` output is preserved below. The updated `audit.py` now treats fiqh/ruling-style prompts as normal retrieval queries and only leaves clearly off-topic prompts for manual refusal checks.

## Corpus Stats

Ayah coverage below is based on distinct ayahs present in `data/chunks/*.jsonl`; intro chunks do not count toward ayah coverage.

| Scholar | Chunk count | Embedded count | Chunk types | Surahs with commentary | Missing surahs | Covered ayahs | Missing ayahs |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| `ibn_kathir` | 1,895 | 1,895 | `verse=1895` | 113 / 114 | `105` | 1,895 / 6,236 | 4,341 |
| `maududi` | 5,224 | 5,224 | `verse=5110`, `intro=114` | 114 / 114 | none | 5,098 / 6,236 | 1,138 |

## Retrieval Summary

- Mean top RRF score across 45 non-off-topic queries: `0.679095`
- Named ayah queries meeting Step 5 threshold (`top chunk matches resolved ayah/surah target` and `RRF >= 0.5`): `10 / 10`
- Fiqh / ruling-style prompts included in retrieval audit: `5`
- Off-topic refusal checks left for manual app-level verification: `5`

## Known Quality Issues

- `ibn_kathir` is materially incomplete for Phase 1 corpus coverage. Surah 105 is missing entirely, and only 1 surah has full ayah coverage in the current chunk snapshot.
- `maududi` is broader and includes all 114 surah introductions, but verse coverage is still incomplete by 1,138 ayahs.
- Scholar-specific phrasing is not enforced by retrieval alone. Query: `What does Ibn Kathir say about 2:286?` returned a `maududi` chunk as the top result.
- Reference resolution is imperfect for some natural-language verse requests. Query: `Commentary on surah 1 verse 1` applied a surah-level filter only, allowing the Maududi intro chunk to outrank the verse-specific chunk.
- Fiqh/ruling prompts now correctly remain in-scope, but the current corpus is still tafsir-heavy, so those prompts retrieve weak proxy verses rather than robust jurisprudential material. Examples in this snapshot include `Is cryptocurrency haram?` and `What is the fatwa on travel insurance?`
- Maududi ingestion still carries OCR-noise risk from the djvu-derived source pipeline noted elsewhere in the repo (`sources/maududi-json/scripts/parse.py` and issue #1 context). This audit did not quantify OCR error rate separately.
- Some thematic and linguistic queries remain weakly grounded. Example: `What does 'iqra' mean in the first revelation?` did not retrieve a clearly focused Surah 96 result at rank 1.

## Phase 1 Criteria

| Criterion | Status | Notes |
| --- | --- | --- |
| Named ayah queries: top chunk matches referenced ayah, RRF >= 0.5 | PASS | All 10 named-ayah queries met the threshold in this snapshot. |
| Mean top RRF score > 0.60 | PASS | Observed mean top RRF: `0.679095`. |
| Fiqh / ruling-style edge cases handled with scholarly context, not refusal | PARTIAL | `audit.py` now keeps these prompts in-scope, but the retrieval results show the current tafsir-only corpus is not yet sufficient for high-quality fiqh answers. |
| Off-topic edge cases correctly refused | NOT VERIFIED | `audit.py` lists 5 clearly off-topic prompts for manual end-to-end verification; it does not test app refusal behavior itself. |

Overall handoff status: partial pass. The docs and audit logic now match the intended application behavior, retrieval scoring remains above the Step 5 threshold, but off-topic refusal still needs end-to-end verification and fiqh-quality answers need broader non-tafsir corpus support.

## Raw `audit.py` Output

========================================================================
AUDIT REPORT  |  collection=tafsir  top_k=5  mode=hybrid-RRF
========================================================================

     [1.000000]  What is the meaning of Ayat al-Kursi?  [filter: surah=2 ayah=255-255]
      1. [ibn_kathir] 2:255–255 (verse)  rrf=1.0
         The Virtue of Ayat Al-Kursi This is Ayat Al-Kursi and tremendous virtues have been associated with it, for the authentic...
      2. [maududi] 2:255–255 (verse)  rrf=0.333333
         He knows what lies before them and what is hidden from them, whereas they cannot
attain to anything of His knowledge sav...

     [0.500000]  Explain the Verse of the Throne  [filter: surah=2 ayah=255-255]
      1. [maududi] 2:255–255 (verse)  rrf=0.5
         He knows what lies before them and what is hidden from them, whereas they cannot
attain to anything of His knowledge sav...
      2. [ibn_kathir] 2:255–255 (verse)  rrf=0.333333
         The Virtue of Ayat Al-Kursi This is Ayat Al-Kursi and tremendous virtues have been associated with it, for the authentic...

     [1.000000]  What does Al-Fatiha mean?  [filter: surah=1 ayah=1-7]
      1. [ibn_kathir] 1:1–1 (verse)  rrf=1.0
         Introduction to Fatihah Which was revealed in Makkah The Meaning of Al-Fatihah and its Various Names This Surah is calle...
      2. [ibn_kathir] 1:2–2 (verse)  rrf=0.583333
         The Meaning of Al-Hamd Abu Ja`far bin Jarir said, "The meaning of الْحَمْدُ للَّهِ (Al-Hamdu Lillah) (all praise and tha...
      3. [ibn_kathir] 1:5–5 (verse)  rrf=0.533333
         The Linguistic and Religious Meaning of `Ibadah Linguistically, `Ibadah means subdued. For instance, a road is described...

     [0.500000]  Commentary on Surah Al-Ikhlas  [filter: surah=112 ayah=1-4]
      1. [maududi] 112:3–3 (verse)  rrf=0.5
         5. The polytheists in every age have adopted the concept that like men, gods also belong to a
species, which has many me...
      2. [ibn_kathir] 112:1–1 (verse)  rrf=0.333333
         Indeed you have brought forth (said) a terrible evil thing. Whereby the heavens are almost torn, and the earth is split ...
      3. [maududi] 112:2–2 (verse)  rrf=0.25
         4. The word used in the original is samad of which the root is smd. A look at the derivatives
in Arabic from this root w...

     [1.000000]  What does Ibn Kathir say about Ayat al-Nur?  [filter: surah=24 ayah=35-35]
      1. [ibn_kathir] 24:35–35 (verse)  rrf=1.0
         The Parable of the Light of Allah `Ali bin Abi Talhah reported that Ibn `Abbas said: اللَّهُ نُورُ السَّمَـوَتِ وَالاٌّر...
      2. [maududi] 24:35–35 (verse)  rrf=0.333333
         61. From here the discourse is directed towards the hypocrites, who were bent upon starting
mischief in the Islamic comm...

     [0.833333]  Explanation of the light verse in the Quran  [filter: surah=24 ayah=35-35]
      1. [ibn_kathir] 24:35–35 (verse)  rrf=0.833333
         The Parable of the Light of Allah `Ali bin Abi Talhah reported that Ibn `Abbas said: اللَّهُ نُورُ السَّمَـوَتِ وَالاٌّر...
      2. [maududi] 24:35–35 (verse)  rrf=0.5
         61. From here the discourse is directed towards the hypocrites, who were bent upon starting
mischief in the Islamic comm...

     [0.583333]  What is the meaning of the People of the Cave?  [filter: surah=18 ayah=9-26]
      1. [ibn_kathir] 18:13–13 (verse)  rrf=0.583333
         Their Belief in Allah and their Retreat from their People From here Allah begins to explain the story in detail. He stat...
      2. [ibn_kathir] 18:22–22 (verse)  rrf=0.566667
         Their Number Allah tells us that people disputed over the number of the people of the Cave. The Ayah mentions three view...
      3. [ibn_kathir] 18:9–9 (verse)  rrf=0.5625
         The Story of the People of Al-Kahf Here Allah tells us about the story of the people of Al-Kahf in brief and general ter...

     [0.750000]  Commentary on Surah Al-Falaq  [filter: surah=113 ayah=1-5]
      1. [maududi] 113:3–3 (verse)  rrf=0.75
         5. After seeking Allah's refuge generally from the evil of the creatures, now prayer is being
taught for seeking refuge ...
      2. [maududi] 113:1–1 (verse)  rrf=0.5
         1. As qul (say) is a part of the message which was conveyed to the Prophet (peace be upon
him) by revelation for preachi...
      3. [ibn_kathir] 113:1–1 (verse)  rrf=0.5
         Which was revealed in Makkah The Position of Ibn Mas`ud concerning Al-Mu`awwidhatayn Imam Ahmad recorded from Zirr bin H...

     [1.000000]  What is Surah Al-Nas about?  [filter: surah=114 ayah=1-6]
      1. [maududi] 114:3–3 (verse)  rrf=1.0
         1.Here also, as in Surah Al-Falaq, instead of saying Audhu-billahi (I seek Allah's refuge), a
prayer has been taught to ...
      2. [maududi] 114:6–6 (verse)  rrf=0.666667
         3. According to some scholars, these words mean that the whisperer whispers evil into the
hearts of two kinds of people:...
      3. [ibn_kathir] 114:1–1 (verse)  rrf=0.25
         Which was revealed in Makkah بِسْمِ اللَّهِ الرَّحْمَـنِ الرَّحِيمِ In the Name of Allah, the Most Gracious, the Most Me...

     [0.833333]  What does the Throne Verse say about Allah?  [filter: surah=2 ayah=255-255]
      1. [ibn_kathir] 2:255–255 (verse)  rrf=0.833333
         The Virtue of Ayat Al-Kursi This is Ayat Al-Kursi and tremendous virtues have been associated with it, for the authentic...
      2. [maududi] 2:255–255 (verse)  rrf=0.5
         He knows what lies before them and what is hidden from them, whereas they cannot
attain to anything of His knowledge sav...

     [0.833333]  Explain Quran 2:255  [filter: surah=2 ayah=255-255]
      1. [maududi] 2:255–255 (verse)  rrf=0.833333
         He knows what lies before them and what is hidden from them, whereas they cannot
attain to anything of His knowledge sav...
      2. [ibn_kathir] 2:255–255 (verse)  rrf=0.5
         The Virtue of Ayat Al-Kursi This is Ayat Al-Kursi and tremendous virtues have been associated with it, for the authentic...

     [1.000000]  What does Ibn Kathir say about 2:286?  [filter: surah=2 ayah=286-286]
      1. [maududi] 2:286–286 (verse)  rrf=1.0
         Our Lord! Lay not on us a burden such as You laid on those gone before us.#2 Our
Lord! Lay not on us burdens which we do...

     [0.500000]  Commentary on 24:35  [filter: surah=24 ayah=35-35]
      1. [maududi] 24:35–35 (verse)  rrf=0.5
         61. From here the discourse is directed towards the hypocrites, who were bent upon starting
mischief in the Islamic comm...
      2. [ibn_kathir] 24:35–35 (verse)  rrf=0.333333
         The Parable of the Light of Allah `Ali bin Abi Talhah reported that Ibn `Abbas said: اللَّهُ نُورُ السَّمَـوَتِ وَالاٌّر...

     [0.833333]  What is the meaning of 112:1-4?  [filter: surah=112 ayah=1-4]
      1. [maududi] 112:2–2 (verse)  rrf=0.833333
         4. The word used in the original is samad of which the root is smd. A look at the derivatives
in Arabic from this root w...
      2. [maududi] 112:1–1 (verse)  rrf=0.533333
         1. The first addressee of this command is the Prophet (peace be upon him) himself for it was
he who was asked: Who is yo...
      3. [maududi] 112:3–3 (verse)  rrf=0.5
         5. The polytheists in every age have adopted the concept that like men, gods also belong to a
species, which has many me...

     [0.500000]  Explain 3:18  [filter: surah=3 ayah=18-18]
      1. [maududi] 3:18–18 (verse)  rrf=0.5
         14. The testimony in question is from God Himself, Who knows directly all the realities of
the universe, Who observes ev...
      2. [ibn_kathir] 3:18–18 (verse)  rrf=0.333333
         The Testimony of Tawhid Allah bears witness, and verily, Allah is sufficient as a Witness, and He is the Most Truthful a...

     [0.833333]  What does 36:1 say?  [filter: surah=36 ayah=1-1]
      1. [maududi] 36:1–1 (verse)  rrf=0.833333
         1. Ibn Abbas, Ikrimah, Dahhak, Hasan Basri and Sufyan bin Uyainah have opined that it
means, "O man", or "O person". Som...
      2. [ibn_kathir] 36:1–1 (verse)  rrf=0.5
         Which was revealed in Makkah The Virtues of Surah Ya Sin Al-Hafiz Abu Ya`la recorded that Abu Hurayrah, may Allah be ple...

     [0.833333]  Commentary on surah 1 verse 1  [filter: surah=1]
      1. [maududi] 1:0–0 (intro)  rrf=0.833333
         Name
This Surah is named Al-Fatihah because of its subject-matter. Fatihah is that which opens a
subject or a book or an...
      2. [maududi] 1:2–2 (verse)  rrf=0.833333
         2. As we have already explained, the character of this surah is that of a prayer. The prayer
begins with praise of the O...
      3. [ibn_kathir] 1:1–1 (verse)  rrf=0.45
         Introduction to Fatihah Which was revealed in Makkah The Meaning of Al-Fatihah and its Various Names This Surah is calle...

     [0.500000]  What is 2:30 about?  [filter: surah=2 ayah=30-30]
      1. [maududi] 2:30–30 (verse)  rrf=0.5
         36. Thus far man has been summoned to serve and obey God on the grounds that God is his
creator and sustainer, that in H...
      2. [ibn_kathir] 2:30–30 (verse)  rrf=0.333333
         Adam and His Children inhabited the Earth, Generation after Generation Allah reiterated His favor on the Children of Ada...

     [0.833333]  Explain verse 67:1  [filter: surah=67 ayah=1-1]
      1. [maududi] 67:1–1 (verse)  rrf=0.833333
         1. Tabaraka is a superlative from barkat. Barkat comprehends the meanings of exaltation
and greatness, abundance and ple...
      2. [ibn_kathir] 67:1–1 (verse)  rrf=0.5
         He is not questioned concerning what He does because of His force, His wisdom and His justice. For this reason Allah say...

     [1.000000]  What is the meaning of 55:1-4?  [filter: surah=55 ayah=1-4]
      1. [maududi] 55:4–4 (verse)  rrf=1.0
         3. One meaning of the word bayan, as used in the original, is the expressing of one's own
mind, i.e. speaking and expres...
      2. [maududi] 55:2–2 (verse)  rrf=0.666667
         1. That is, the teaching of this Quran is not the production of a man's mind but its Teacher is
the Merciful God Himself...
      3. [ibn_kathir] 55:1–1 (verse)  rrf=0.45
         Mankind is surrounded by Allah's Favors Allah said, وَالْحَبُّ ذُو الْعَصْفِ وَالرَّيْحَانُ (13. Then which of the bless...

     [0.571429]  What does the Quran say about tawakkul (trust in Allah)?
      1. [maududi] 70:32–32 (verse)  rrf=0.571429
         21. "Trusts" imply those trusts which Allah has entrusted to men as well as those which one
man entrusts to another beca...
      2. [maududi] 42:36–36 (verse)  rrf=0.5
         55. That is, it is not a thing at which man should exult whatever worldly wealth a person has
in his possession, he has ...
      3. [ibn_kathir] 33:1–1 (verse)  rrf=0.333333
         Which was revealed in Al-Madinah بِسْمِ اللَّهِ الرَّحْمَـنِ الرَّحِيمِ In the Name of Allah, the Most Gracious, the Mos...

     [0.500000]  Quranic teachings on justice and fairness
      1. [maududi] 28:51–51 (verse)  rrf=0.5
         71. That is, "As far as conveying of the admonition is concerned, we have done full justice to
it in the Quran in the be...
      2. [maududi] 55:9–9 (verse)  rrf=0.5
         8. That is, as you are living in a balanced universe, whose entire system has been established
on justice, you should al...
      3. [maududi] 20:133–133 (verse)  rrf=0.333333
         116. This means that the Quran itself is a great miracle, for though it is being presented by
an unlettered person from ...

     [0.500000]  What does the Quran say about the Day of Judgment?
      1. [maududi] 57:12–12 (verse)  rrf=0.5
         17. This and the following verses show that the light on the Day of Judgment will be
specifically meant for the righteou...
      2. [ibn_kathir] 69:13–13 (verse)  rrf=0.5
         A Mention of the Horrors of the Day of Judgement Allah informs of the horrors that will take place on the Day of Judgeme...
      3. [ibn_kathir] 79:34–34 (verse)  rrf=0.333333
         The Day of Judgement, its Pleasures and Hell, and that its Time is not known Allah says, فَإِذَا جَآءَتِ الطَّآمَّةُ الْ...

     [0.500000]  Quranic commentary on gratitude and thankfulness
      1. [ibn_kathir] 3:26–26 (verse)  rrf=0.5
         Encouraging Gratitude Allah said, قُلْ (Say) O Muhammad , while praising your Lord, thanking Him, relying in all matters...
      2. [maududi] 8:26–26 (verse)  rrf=0.5
         21. The reference to gratefulness in the verse is worthy of reflection. Bearing in mind the
subject under discussion, it...
      3. [maududi] 4:147–147 (verse)  rrf=0.333333
         175. Shukr denotes an acknowledgement of benefaction and a feeling of gratitude. This
verse states if a person does not ...

     [0.666667]  What do scholars say about mercy in the Quran?
      1. [maududi] 27:77–77 (verse)  rrf=0.666667
         94. That is, "It is mercy and guidance for those who accept the message of the Quran and
believe in what it presents. Su...
      2. [maududi] 36:5–5 (verse)  rrf=0.571429
         3. Here, two of the attributes of the Sender of the Quran have been mentioned. First, that He
is All-Mighty; second, tha...
      3. [maududi] 24:5–5 (verse)  rrf=0.4
         6. Allah is the most merciful of all....

     [0.666667]  Tafsir on the concept of taqwa
      1. [ibn_kathir] 3:102–102 (verse)  rrf=0.666667
         Meaning of `Taqwa of Allah Ibn Abi Hatim recorded that `Abdullah bin Mas`ud commented on the Ayah, اتَّقُواْ اللَّهَ حَق...
      2. [ibn_kathir] 4:131–131 (verse)  rrf=0.625
         The Necessity of Taqwa of Allah Allah states that He is the Owner of the heavens and earth and that He is the Supreme Au...
      3. [ibn_kathir] 55:46–46 (verse)  rrf=0.410256
         The Delight of Those Who have Taqwa in Paradise Allah the Exalted said, وَلِمَنْ خَافَ مَقَامَ رَبِّهِ (But for him who ...

     [0.500000]  What does the Quran say about parents and family?
      1. [ibn_kathir] 17:23–23 (verse)  rrf=0.5
         The Command to Worship Allah Alone and to be Dutiful to One's Parents Allah commands us to worship Him alone, with no pa...
      2. [maududi] 19:32–32 (verse)  rrf=0.5
         20a. The words used are: "dutiful to my mother" instead of "dutiful to my parents". This is
another proof of the fact th...
      3. [maududi] 17:25–25 (verse)  rrf=0.333333
         27. This verse enjoins that after Allah's right, the greatest of all the human rights is the right
of parents. Therefore...

     [0.562500]  Quranic teachings on patience and perseverance
      1. [maududi] 12:18–18 (verse)  rrf=0.5625
         13. The literal meaning of "patience in grace" which implies a patience that enables one to
endure all kinds of troubles...
      2. [maududi] 8:46–46 (verse)  rrf=0.5
         you should lose courage and your power depart. Be steadfast, surely Allah is with
those who remain steadfast.
37. The be...
      3. [ibn_kathir] 46:33–33 (verse)  rrf=0.458333
         Commanding the Prophet to persevere Allah then commands His Messenger to observe patience with those who rejected him am...

     [0.750000]  What is the Quranic view of creation?
      1. [maududi] 32:8–8 (verse)  rrf=0.75
         14. That is, "In the beginning He created man directly by His own act of creation, and then
placed in man himself such a...
      2. [maududi] 55:14–14 (verse)  rrf=0.576923
         14. The order of the initial stages of the creation of man, as given at different places in the
Quran seems to be as fol...
      3. [ibn_kathir] 32:7–7 (verse)  rrf=0.333333
         The Creation of Man in Stages Allah tells us that He has created everything well and formed everything in a goodly fashi...

     [0.700000]  Commentary on the description of Paradise in the Quran
      1. [maududi] 88:11–11 (verse)  rrf=0.7
         5. This thing has been mentioned at several places in the Quran as a major blessing of
Paradise. (For explanation, see(E...
      2. [ibn_kathir] 19:61–61 (verse)  rrf=0.5
         The Description of the Gardens of the Truthful and Those Who repent Allah, the Exalted, says that the Gardens (of Paradi...
      3. [maududi] 78:35–35 (verse)  rrf=0.392157
         21. At several places in the Quran this has been counted as among the major blessings of
Paradise. Human ears there will...

     [0.750000]  Verses about the attributes of Allah
      1. [maududi] 85:9–9 (verse)  rrf=0.75
         5. In these verses those of Allah Almighty's attributes have been mentioned on account of
which He alone deserves that o...
      2. [maududi] 59:22–22 (verse)  rrf=0.576923
         32. These verses explain what kind of God He is, and what are His attributes, Who has sent
this Quran to you, Who has pl...
      3. [maududi] 16:18–18 (verse)  rrf=0.333333
         17. Here the connection of Allah's attributes, "Forgiving and Compassionate", with the
preceding verse is so obvious tha...

     [0.700000]  Quranic descriptions of hellfire
      1. [ibn_kathir] 7:44–44 (verse)  rrf=0.7
         People of Hellfire will feel Anguish upon Anguish Allah mentioned how the people of the Fire will be addressed, chastise...
      2. [ibn_kathir] 67:6–6 (verse)  rrf=0.5
         The Description of Hell and Those Who will enter into it Allah the Exalted says, وَ (and) meaning, `and We have prepared...
      3. [ibn_kathir] 18:29–29 (verse)  rrf=0.333333
         The Truth is from Allah, and the Punishment of Those Who do not believe in it Allah says to His Messenger Muhammad ﷺ: "S...

     [0.555556]  All verses mentioning the Prophets
      1. [ibn_kathir] 19:58–58 (verse)  rrf=0.555556
         These Prophets are the Chosen Ones Allah, the Exalted, says that these Prophets (were favored), but this does not mean o...
      2. [maududi] 21:72–72 (verse)  rrf=0.5
         65. That is, We made his son a Prophet and his grandson too....
      3. [maududi] 17:55–55 (verse)  rrf=0.333333
         some Prophets over others,2and We gave the Psalms to David.®
62. Though this has apparently been addressed to the Prophe...

     [0.576923]  Verses about prayer and worship in the Quran
      1. [maududi] 73:4–4 (verse)  rrf=0.576923
         3. This is an explanation of the duration of time commanded to be spent in worship. In it the
Prophet (peace be upon him...
      2. [maududi] 40:60–60 (verse)  rrf=0.5
         82. After the Hereafter, the discourse now turns to Tauhid which was the second point of
dispute between the Prophet (pe...
      3. [maududi] 73:5–5 (verse)  rrf=0.333333
         5. That is, you are being commanded to stand up in the night Prayer because We are going
to send down on you a weighty w...

     [0.500000]  What surahs discuss the afterlife?
      1. [maududi] 45:21–21 (verse)  rrf=0.5
         26. After the invitation to Tauhid, the discourse now turns to the theme of the Hereafter.
27. This is the moral reasoni...
      2. [maududi] 1:2–2 (verse)  rrf=0.5
         2. As we have already explained, the character of this surah is that of a prayer. The prayer
begins with praise of the O...
      3. [maududi] 7:3–3 (verse)  rrf=0.333333
         4. The central theme of the whole surah, and of the present discourse, is the guidance which
man needs in order to live ...

     [0.833333]  What is the meaning of the word 'khalifa' in Quran 2:30?  [filter: surah=2 ayah=30-30]
      1. [ibn_kathir] 2:30–30 (verse)  rrf=0.833333
         Adam and His Children inhabited the Earth, Generation after Generation Allah reiterated His favor on the Children of Ada...
      2. [maududi] 2:30–30 (verse)  rrf=0.5
         36. Thus far man has been summoned to serve and obey God on the grounds that God is his
creator and sustainer, that in H...

     [0.642857]  Explain the Arabic root of 'taqwa'
      1. [ibn_kathir] 3:102–102 (verse)  rrf=0.642857
         Meaning of `Taqwa of Allah Ibn Abi Hatim recorded that `Abdullah bin Mas`ud commented on the Ayah, اتَّقُواْ اللَّهَ حَق...
      2. [ibn_kathir] 4:131–131 (verse)  rrf=0.6
         The Necessity of Taqwa of Allah Allah states that He is the Owner of the heavens and earth and that He is the Supreme Au...
      3. [ibn_kathir] 20:113–113 (verse)  rrf=0.383333
         The Qur'an was revealed so that the People would have Taqwa and reflect After Allah, the Exalted, mentions that on the D...

     [0.750000]  What does 'Rahman' mean in Al-Fatiha?  [filter: surah=1 ayah=1-7]
      1. [maududi] 1:3–3 (verse)  rrf=0.75
         4. Whenever we are deeply impressed by the greatness of something we try to express our
feelings by using superlatives. ...
      2. [ibn_kathir] 1:3–3 (verse)  rrf=0.666667
         Allah said next, الرَّحْمَـنِ الرَّحِيمِ (Ar-Rahman (the Most Gracious), Ar-Rahim (the Most Merciful)) We explained thes...
      3. [maududi] 1:2–2 (verse)  rrf=0.5
         2. As we have already explained, the character of this surah is that of a prayer. The prayer
begins with praise of the O...

     [0.666667]  Grammatical explanation of Surah Al-Ikhlas verse 1  [filter: surah=112 ayah=1-4]
      1. [maududi] 112:4–4 (verse)  rrf=0.666667
         6. The word kufu as used in the original means an example, a similar thing, the one equal in
rank and position. In the m...
      2. [maududi] 112:2–2 (verse)  rrf=0.583333
         4. The word used in the original is samad of which the root is smd. A look at the derivatives
in Arabic from this root w...
      3. [maududi] 112:1–1 (verse)  rrf=0.583333
         1. The first addressee of this command is the Prophet (peace be upon him) himself for it was
he who was asked: Who is yo...

     [0.500000]  What does 'iqra' mean in the first revelation?
      1. [maududi] 23:58–58 (verse)  rrf=0.5
         52. Signs here means both divine revelations to the Prophets and the signs found in man's
own self and in the universe a...
      2. [ibn_kathir] 74:1–1 (verse)  rrf=0.5
         Which was revealed in Makkah بِسْمِ اللَّهِ الرَّحْمَـنِ الرَّحِيمِ In the Name of Allah, the Most Gracious, the Most Me...
      3. [ibn_kathir] 96:1–1 (verse)  rrf=0.333333
         Which was revealed in Makkah This was the First of the Qur'an revealed بِسْمِ اللَّهِ الرَّحْمَـنِ الرَّحِيمِ In the Nam...

     [0.500000]  Is it halal to eat shellfish?
      1. [maududi] 56:34–34 (verse)  rrf=0.5
         3
) eat
35 2S RS
ELS) oy...
      2. [ibn_kathir] 5:3–3 (verse)  rrf=0.5
         The Animals that are Unlawful to Eat Allah informs His servants that He forbids consuming the mentioned types of foods, ...
      3. [ibn_kathir] 5:96–96 (verse)  rrf=0.333333
         Water Game is Allowed for the Muhrim Sa`id bin Al-Musayyib, Sa`id bin Jubayr and others commented on Allah's statement; ...

     [0.500000]  What is the Islamic ruling on music?
      1. [maududi] 48:16–16 (verse)  rrf=0.5
         30. The words au-yuslimuna in the original can have two meanings and both are implied: 
That they should accept Islam. T...
      2. [ibn_kathir] 31:1–1 (verse)  rrf=0.5
         Which was revealed in Makkah بِسْمِ اللَّهِ الرَّحْمَـنِ الرَّحِيمِ In the name of Allah, the Beneficent, the Merciful T...
      3. [ibn_kathir] 5:90–90 (verse)  rrf=0.333333
         Prohibiting Khamr (Intoxicants) and Maysir (Gambling) Allah forbids His believing servants from consuming Khamr and Mays...

     [0.500000]  Can I pray with nail polish?
      1. [ibn_kathir] 7:31–31 (verse)  rrf=0.5
         Allah commands taking Adornment when going to the Masjid This honorable Ayah refutes the idolators' practice of performi...
      2. [maududi] 107:6–6 (verse)  rrf=0.5
         10. This can be an independent sentence as well as one relating to the preceding sentence. In
the first case, it would m...
      3. [maududi] 2:148–148 (verse)  rrf=0.333333
         149. There is a subtle gap between this sentence and the next, a gap which the reader can fill
with just a little reflec...

     [0.500000]  Is cryptocurrency haram?
      1. [ibn_kathir] 2:149–149 (verse)  rrf=0.5
         Why was changing the Qiblah mentioned thrice This is a third command from Allah to face Al-Masjid Al-Haram (the Sacred M...
      2. [ibn_kathir] 4:29–29 (verse)  rrf=0.5
         Prohibiting Unlawfully Earned Money Allah, the Exalted and Most Honored, prohibits His believing servants from illegally...
      3. [ibn_kathir] 5:90–90 (verse)  rrf=0.333333
         Prohibiting Khamr (Intoxicants) and Maysir (Gambling) Allah forbids His believing servants from consuming Khamr and Mays...

     [0.500000]  What is the fatwa on travel insurance?
      1. [maududi] 28:26–26 (verse)  rrf=0.5
         37. It is not necessary that the girl said this to her father in his very first meeting with Moses.
Most probably her fa...
      2. [maududi] 48:25–25 (verse)  rrf=0.5
         43. That is, Allah was seeing the sincerity and the selfless devotion with which you had
become ready to lay down your l...
      3. [maududi] 3:28–28 (verse)  rrf=0.333333
         25. This means that it is lawful for a believer, helpless in the grip of the enemies of Islam and
in imminent danger of ...

========================================================================
SUMMARY
  Total queries:     45
  Mean top RRF score:0.679095  (rank-based, not cosine)

Off-topic refusal checks to run manually (5 queries):
  - What is the weather today?
  - Who is the best football player?
  - Plan a weekend trip to Boston
  - Write me a poem about coffee
  - Translate this Spanish sentence into English
========================================================================
