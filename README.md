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

Genesis 1:1:

```text
Atnach
|-- Tipcha
|   |-- Tipcha: בְּרֵאשִׁ֖ית
|   `-- Atnach: בָּרָ֣א אֱלֹהִ֑ים
`-- Tipcha
    |-- Tipcha: אֵ֥ת הַשָּׁמַ֖יִם
    `-- Sof Pasuq: וְאֵ֥ת הָאָֽרֶץ׃
```

1 Chronicles 1:1:

```text
Tipcha
|-- Tipcha: אָדָ֥ם שֵׁ֖ת
`-- Sof Pasuq: אֱנֽוֹשׁ׃
```

Job 3:2, using the poetic accent system:

```text
Revia
|-- Revia: וַיַּ֥עַן אִיּ֗וֹב
`-- Sof Pasuq: וַיֹּאמַֽר׃
```

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
