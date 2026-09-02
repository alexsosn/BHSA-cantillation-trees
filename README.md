# BHSA cantillation trees

Text-Fabric add-on for the 2021 release of the
[ETCBC BHSA](https://github.com/ETCBC/bhsa). It aligns the cantillation
structure encoded in the [Open Scriptures Hebrew Bible
(MorphHB)](https://github.com/openscriptures/morphhb) with BHSA nodes and
reconstructs a prosodic tree for every verse.

The generated module covers the complete Hebrew Bible, including the poetic
accentuation system of Psalms, Proverbs, and the poetic portion of Job.

## Features

| Feature | Node type | Value |
| --- | --- | --- |
| `cantillation_accent` | `word` | Interpreted accent name |
| `cantillation_accent_type` | `word` | `conjunctive` or `disjunctive` |
| `cantillation_marks` | `word` | Raw Unicode cantillation sequence |
| `cantillation_accent_status` | `word` | `catalogued` or `unicode-fallback` |
| `cantillation_source_id` | `word` | MorphHB word identifier |
| `cantillation_path` | `word` | MorphHB structural path on a unit-final word |
| `cantillation_unit` | `word` | Accentual-unit number within the verse |
| `cantillation_unit_path` | `word` | Structural path copied to every slot in the unit |
| `cantillation_system` | `verse` | `prose` or `poetic` |
| `cantillation_tree` | `verse` | Compact JSON binary tree |
| `cantillation_alignment` | `verse` | `exact` or `fuzzy` |
| `cantillation_shape` | `verse` | Unlabelled shape, e.g. `((L,L),(L,L))` |
| `cantillation_branch_signature` | `verse` | Shape with internal accent labels |
| `cantillation_accent_signature` | `verse` | Shape with internal and leaf accents |
| `cantillation_depth` | `verse` | Maximum root-to-leaf depth in edges |
| `cantillation_leaf_count` | `verse` | Number of accentual-unit leaves |
| `cantillation_mean_leaf_depth` | `verse` | Mean root-to-leaf depth |
| `cantillation_colless` | `verse` | Colless imbalance index |
| `cantillation_colless_normalized` | `verse` | Colless divided by its maximum for the leaf count |
| `cantillation_sackin` | `verse` | Sum of all leaf depths |
| `cantillation_longest_ladder` | `verse` | Longest run of nested `1:(n-1)` splits |
| `cantillation_longest_accent_run` | `verse` | Longest same-accent run on a root-to-leaf path |
| `cantillation_depth_leaf_ratio` | `verse` | Maximum depth divided by leaf count |

Because BHSA slots represent morphological words, an orthographic MorphHB word
can correspond to several BHSA `word` nodes. Accent features are placed on the
last matching BHSA slot. Unit features are copied to all slots belonging to the
accentual unit.

At the few places where one BHSA slot crosses a MorphHB word or unit boundary,
all values are retained in source order and separated by ` | `. The JSON tree
remains unambiguous because its leaves preserve the individual source units.

## Build

Python 3.10 or later is required.

```bash
python -m pip install -e '.[dev]'
bhsa-cantillation build \
  --bhsa /path/to/bhsa/tf/2021 \
  --morphhb /path/to/morphhb \
  --output tf/2021
```

`--morphhb` must point to a checkout containing `wlc/*.xml` and
`structure/OshbVerse/Script/AccentCatalog.js`. The command stops if a verse
cannot be aligned within the configured edit-distance threshold. All non-exact
alignments and uncatalogued mark combinations are written to
`alignment-report.json` for review.

Run the tests with:

```bash
python -m pytest
```

## Data quality of the pinned build

The checked-in build contains 23,213 verse trees and 165,747 accentual units.
Of the verse alignments, 23,203 are exact at the consonantal level. The other
ten have Levenshtein distance 1; every difference is retained in
`alignment-report.json` rather than normalized away.

MorphHB's accent catalogue does not contain 308 mark-and-role combinations
found in its own XML. These receive an explicit `unicode-fallback` status and a
name assembled from Unicode character names. There are also 702 BHSA slots
aligned to more than one MorphHB orthographic word and 26 slots belonging to
more than one accentual unit. Their scalar feature values use the documented
` | ` separator.

## Load in Text-Fabric

Once the generated `tf/2021` directory is available beside BHSA:

```python
from tf.app import use

A = use(
    "ETCBC/bhsa",
    mod="alexsosn/BHSA-cantillation-trees/tf",
    hoist=globals(),
)

verse = T.nodeFromSection(("Genesis", 1, 1))
tree = F.cantillation_tree.v(verse)
```

The value of `cantillation_tree` is JSON. Each internal node has two children
and is labelled by the disjunctive accent at the cut. Each leaf records the
MorphHB path, the inclusive BHSA slot range, the unit text, and its final
accent.

The mean-depth, normalized-Colless, and depth/leaf features are stored as
decimal strings because Text-Fabric node features support integer and string
values. Decimal output is rounded to at most six places. For one or two leaves,
where the maximum Colless value `(n-1)(n-2)/2` is zero, the normalized value is
defined as zero. `cantillation_longest_ladder` counts consecutive internal
nodes where exactly one child is a leaf; `cantillation_longest_accent_run`
includes both internal nodes and leaves.

## Export and ASCII rendering

Export the whole module as JSON Lines, or select verses into a JSON array:

```bash
python scripts/export_trees.py \
  --bhsa /path/to/bhsa/tf/2021 \
  --module tf/2021 \
  --jsonl --output cantillation-trees.jsonl

python scripts/export_trees.py \
  --bhsa /path/to/bhsa/tf/2021 \
  --verse Gen.1.1 --verse Ps.117.1 \
  --pretty --output selected-trees.json
```

Render one tree from that export or directly from Text-Fabric:

```bash
python scripts/render_tree.py --input selected-trees.json --verse Gen.1.1
python scripts/render_tree.py --bhsa /path/to/bhsa/tf/2021 --verse Job.3.2
```

### Corpus record holders

These examples are generated by `render_tree.py`. They cover every unique
verse holding one of the current corpus records for depth, leaf count, Sackin
index, longest ladder, or longest same-accent run.

<details>
<summary><strong>1 Chronicles 15:18</strong> — maximum depth 13 and maximum ladder 11</summary>

```text
Atnach
|-- Tipcha
|   |-- Tipcha: וְעִמָּהֶ֖ם
|   `-- Atnach: אֲחֵיהֶ֣ם הַמִּשְׁנִ֑ים
`-- Tipcha
    |-- Tevir
    |   |-- Pazer
    |   |   |-- Pazer: זְכַרְיָ֡הוּ
    |   |   `-- Pazer
    |   |       |-- Pazer: בֵּ֡ן
    |   |       `-- Pazer
    |   |           |-- Pazer: וְיַֽעֲזִיאֵ֡ל
    |   |           `-- Pazer
    |   |               |-- Pazer: וּשְׁמִֽירָמ֡וֹת
    |   |               `-- Legarmeh
    |   |                   |-- Legarmeh: וִיחִיאֵ֣ל׀
    |   |                   `-- Pazer
    |   |                       |-- Pazer: וְעֻנִּ֡י
    |   |                       `-- Pazer
    |   |                           |-- Pazer: אֱלִיאָ֡ב
    |   |                           `-- Pazer
    |   |                               |-- Pazer: וּבְנָיָ֡הוּ
    |   |                               `-- Pazer
    |   |                                   |-- Pazer: וּמַֽעֲשֵׂיָ֡הוּ
    |   |                                   `-- Qadma with Geresh
    |   |                                       |-- Qadma with Geresh: וּמַתִּתְיָהוּ֩ וֶאֱלִ֨יפְלֵ֜הוּ
    |   |                                       `-- Tevir: וּמִקְנֵיָ֨הוּ וְעֹבֵ֥ד אֱדֹ֛ם
    |   `-- Tipcha: וִֽיעִיאֵ֖ל
    `-- Sof Pasuq: הַשֹּׁעֲרִֽים׃
```

</details>

<details>
<summary><strong>2 Kings 6:32</strong> — maximum leaf count 22</summary>

```text
Atnach
|-- Zaqef Qatan
|   |-- Pashta
|   |   |-- Pashta: וֶאֱלִישָׁע֙
|   |   `-- Zaqef Qatan: יֹשֵׁ֣ב בְּבֵית֔וֹ
|   `-- Tipcha
|       |-- Tipcha: וְהַזְּקֵנִ֖ים
|       `-- Atnach: יֹשְׁבִ֣ים אִתּ֑וֹ
`-- Zaqef Qatan
    |-- Revia
    |   |-- Geresh
    |   |   |-- Geresh: וַיִּשְׁלַ֨ח אִ֜ישׁ
    |   |   `-- Revia: מִלְּפָנָ֗יו
    |   `-- Revia
    |       |-- Geresh
    |       |   |-- Geresh: בְּטֶ֣רֶם יָבֹא֩ הַמַּלְאָ֨ךְ אֵלָ֜יו
    |       |   `-- Legarmeh
    |       |       |-- Legarmeh: וְה֣וּא׀
    |       |       `-- Revia: אָמַ֣ר אֶל־ הַזְּקֵנִ֗ים
    |       `-- Pashta
    |           |-- Pashta: הַרְּאִיתֶם֙
    |           `-- Pashta
    |               |-- Gershayim
    |               |   |-- Gershayim: כִּֽי־ שָׁלַ֞ח
    |               |   `-- Pashta: בֶּן־ הַֽמְרַצֵּ֤חַ הַזֶּה֙
    |               `-- Zaqef Qatan: לְהָסִ֣יר אֶת־ רֹאשִׁ֔י
    `-- Zaqef Qatan
        |-- Revia
        |   |-- Legarmeh
        |   |   |-- Legarmeh: רְא֣וּ׀
        |   |   `-- Revia: כְּבֹ֣א הַמַּלְאָ֗ךְ
        |   `-- Pashta
        |       |-- Pashta: סִגְר֤וּ הַדֶּ֨לֶת֙
        |       `-- Pashta
        |           |-- Pashta: וּלְחַצְתֶּ֤ם אֹתוֹ֙
        |           `-- Zaqef Qatan: בַּדֶּ֔לֶת
        `-- Tipcha
            |-- Revia
            |   |-- Revia: הֲל֗וֹא
            |   `-- Tevir
            |       |-- Tevir: ק֛וֹל
            |       `-- Tipcha: רַגְלֵ֥י אֲדֹנָ֖יו
            `-- Sof Pasuq: אַחֲרָֽיו׃
```

</details>

<details>
<summary><strong>Joshua 8:33</strong> — maximum Sackin index 126</summary>

```text
Atnach
|-- Zaqef Qatan
|   |-- Revia
|   |   |-- Pazer
|   |   |   |-- Pazer: וְכָל־ יִשְׂרָאֵ֡ל
|   |   |   `-- Pazer
|   |   |       |-- Pazer: וּזְקֵנָ֡יו
|   |   |       `-- Legarmeh
|   |   |           |-- Legarmeh: וְשֹׁטְרִ֣ים׀
|   |   |           `-- Pazer
|   |   |               |-- Pazer: וְשֹׁפְטָ֡יו
|   |   |               `-- Legarmeh
|   |   |                   |-- Legarmeh: עֹמְדִ֣ים מִזֶּ֣ה׀
|   |   |                   `-- Legarmeh
|   |   |                       |-- Legarmeh: וּמִזֶּ֣ה׀
|   |   |                       `-- Pazer
|   |   |                           |-- Pazer: לָאָר֡וֹן
|   |   |                           `-- Geresh
|   |   |                               |-- Geresh: נֶגֶד֩ הַכֹּהֲנִ֨ים הַלְוִיִּ֜ם
|   |   |                               `-- Legarmeh
|   |   |                                   |-- Legarmeh: נֹשְׂאֵ֣י׀
|   |   |                                   `-- Revia: אֲר֣וֹן בְּרִית־ יְהוָ֗ה
|   |   `-- Pashta
|   |       |-- Pashta: כַּגֵּר֙
|   |       `-- Zaqef Qatan: כָּֽאֶזְרָ֔ח
|   `-- Zaqef Qatan
|       |-- Pashta
|       |   |-- Pashta: חֶצְיוֹ֙
|       |   `-- Zaqef Qatan: אֶל־ מ֣וּל הַר־ גְּרִזִ֔ים
|       `-- Tipcha
|           |-- Tipcha: וְהַֽחֶצְי֖וֹ
|           `-- Atnach: אֶל־ מ֣וּל הַר־ עֵיבָ֑ל
`-- Tipcha
    |-- Revia
    |   |-- Geresh
    |   |   |-- Geresh: כַּאֲשֶׁ֨ר צִוָּ֜ה
    |   |   `-- Revia: מֹשֶׁ֣ה עֶֽבֶד־ יְהוָ֗ה
    |   `-- Tevir
    |       |-- Tevir: לְבָרֵ֛ךְ
    |       `-- Tipcha: אֶת־ הָעָ֥ם יִשְׂרָאֵ֖ל
    `-- Sof Pasuq: בָּרִאשֹׁנָֽה׃
```

</details>

The maximum same-accent run is six nodes and is shared by three verses:

<details>
<summary><strong>Nehemiah 12:36</strong> — same-accent run 6</summary>

```text
Atnach
|-- Zaqef Qatan
|   |-- Pashta
|   |   |-- Pazer
|   |   |   |-- Pazer: וְֽאֶחָ֡יו
|   |   |   `-- Pazer
|   |   |       |-- Pazer: שְֽׁמַעְיָ֡ה
|   |   |       `-- Pazer
|   |   |           |-- Pazer: וַעֲזַרְאֵ֡ל
|   |   |           `-- Pazer
|   |   |               |-- Pazer: מִֽלֲלַ֡י
|   |   |               `-- Pazer
|   |   |                   |-- Pazer: גִּֽלֲלַ֡י
|   |   |                   `-- Gershayim
|   |   |                       |-- Gershayim: מָעַ֞י
|   |   |                       `-- Pashta: נְתַנְאֵ֤ל וִֽיהוּדָה֙
|   |   `-- Zaqef Qatan: חֲנָ֔נִי
|   `-- Tipcha
|       |-- Tipcha: בִּכְלֵי־ שִׁ֥יר דָּוִ֖יד
|       `-- Atnach: אִ֣ישׁ הָאֱלֹהִ֑ים
`-- Tipcha
    |-- Tipcha: וְעֶזְרָ֥א הַסּוֹפֵ֖ר
    `-- Sof Pasuq: לִפְנֵיהֶֽם׃
```

</details>

<details>
<summary><strong>1 Chronicles 16:5</strong> — same-accent run 6</summary>

```text
Atnach
|-- Tipcha
|   |-- Tipcha: אָסָ֥ף הָרֹ֖אשׁ
|   `-- Atnach: וּמִשְׁנֵ֣הוּ זְכַרְיָ֑ה
`-- Zaqef Qatan
    |-- Revia
    |   |-- Pazer
    |   |   |-- Pazer: יְעִיאֵ֡ל
    |   |   `-- Pazer
    |   |       |-- Pazer: וּשְׁמִֽירָמ֡וֹת
    |   |       `-- Pazer
    |   |           |-- Pazer: וִֽיחִיאֵ֡ל
    |   |           `-- Pazer
    |   |               |-- Pazer: וּמַתִּתְיָ֡ה
    |   |               `-- Pazer
    |   |                   |-- Pazer: וֶאֱלִיאָ֡ב
    |   |                   `-- Geresh
    |   |                       |-- Geresh: וּבְנָיָהוּ֩ וְעֹבֵ֨ד אֱדֹ֜ם
    |   |                       `-- Revia: וִֽיעִיאֵ֗ל
    |   `-- Pashta
    |       |-- Pashta: בִּכְלֵ֤י נְבָלִים֙
    |       `-- Zaqef Qatan: וּבְכִנֹּר֔וֹת
    `-- Tipcha
        |-- Tipcha: וְאָסָ֖ף
        `-- Sof Pasuq: בַּֽמְצִלְתַּ֥יִם מַשְׁמִֽיעַ׃
```

</details>

<details>
<summary><strong>2 Chronicles 17:8</strong> — same-accent run 6</summary>

```text
Atnach
|-- Tipcha
|   |-- Revia
|   |   |-- Revia: וְעִמָּהֶ֣ם הַלְוִיִּ֗ם
|   |   `-- Tevir
|   |       |-- Pazer
|   |       |   |-- Pazer: שְֽׁמַֽעְיָ֡הוּ
|   |       |   `-- Pazer
|   |       |       |-- Pazer: וּנְתַנְיָ֡הוּ
|   |       |       `-- Pazer
|   |       |           |-- Pazer: וּזְבַדְיָ֡הוּ
|   |       |           `-- Pazer
|   |       |               |-- Pazer: וַעֲשָׂהאֵ֡ל
|   |       |               `-- Pazer
|   |       |                   |-- Pazer: וּשְׁמִֽירָמ֡וֹת
|   |       |                   `-- Tevir: וִֽיהוֹנָתָן֩ וַאֲדֹ֨נִיָּ֧הוּ וְטֽוֹבִיָּ֛הוּ
|   |       `-- Tipcha: וְט֥וֹב אֲדוֹנִיָּ֖ה
|   `-- Atnach: הַלְוִיִּ֑ם
`-- Tipcha
    |-- Tevir
    |   |-- Tevir: וְעִמָּהֶ֛ם
    |   `-- Tipcha: אֱלִישָׁמָ֥ע וִֽיהוֹרָ֖ם
    `-- Sof Pasuq: הַכֹּהֲנִֽים׃
```

</details>

Add `--details` to show MorphHB paths and inclusive BHSA slot ranges, or
`--unicode-lines` to use box-drawing connectors.

## Provenance and licensing

The conversion code is MIT licensed. Generated cantillation features are an
adaptation of MorphHB and remain subject to
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution:
“Original work of the Open Scriptures Hebrew Bible available at
https://github.com/openscriptures/morphhb”. BHSA has its own
[licensing terms](https://github.com/ETCBC/bhsa/blob/master/LICENSE).

The structural paths are supplied by MorphHB; they are not inferred anew from
the Unicode accents. Accent labels are read from MorphHB's own prose and poetic
catalogues during the build.

## Related work

[Josh Waxman's cantillation repository](https://github.com/joshwaxman/cantillation)
contains serialized prosodic parses for the 36 books that use the prose accent
system. This module uses
MorphHB instead so that the source structure, poetic books, licensing, and
alignment provenance remain available.

The two corpora have now been compared over all 18,694 Waxman verses. On the
18,139 verses with identical consonantal text, 268,351 of 268,685 module
constituent spans (99.876%) and 124,941 of 125,273 binary cuts (99.735%) occur
in the Waxman trees. Of 124,941 comparable cut labels, 124,940 agree after
normalizing accent-name spelling. See the
[full method, caveats, and reproducible results](comparison/waxman-comparison.md).
