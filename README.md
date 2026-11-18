# BHSA cantillation trees

Text-Fabric add-on for the 2021 release of the
[ETCBC BHSA](https://github.com/ETCBC/bhsa). It aligns the cantillation
structure encoded in the [Open Scriptures Hebrew Bible
(MorphHB)](https://github.com/openscriptures/morphhb) with BHSA nodes and
reconstructs a prosodic tree for every verse.

The generated module covers the complete Hebrew Bible, including the poetic
accentuation system of Psalms, Proverbs, and the poetic portion of Job.

## Researcher quickstart (pinned 2021 corpus)

This example answers a concrete research question: **which cantillation cuts
in Genesis 1:1 coincide with the ends of original BHSA syntactic phrases?**
It starts from a fresh clone and uses the same fixed upstream revisions as
the repository's full-corpus CI. Commands below use a POSIX shell
(Linux/macOS, or a compatible shell on Windows), Git and Python 3.10+.

```bash
git clone https://github.com/alexsosn/BHSA-cantillation-trees.git
cd BHSA-cantillation-trees
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .

# Fetch only the files needed for the pinned original BHSA and MorphHB data.
mkdir -p inputs
git clone --filter=blob:none --sparse https://github.com/ETCBC/bhsa.git inputs/bhsa
git -C inputs/bhsa sparse-checkout set tf/2021
git -C inputs/bhsa checkout 4db00e2157915495e1a4d3d57e41223df24775da

git clone --filter=blob:none --sparse https://github.com/openscriptures/morphhb.git inputs/morphhb
git -C inputs/morphhb sparse-checkout set wlc structure/OshbVerse/Script
git -C inputs/morphhb checkout 3d15126fb1ef74867fc1434be1942e837932691f

# Verify all source-word alignments and build the searchable derived TF graph.
bhsa-cantillation build-graph \
  --bhsa inputs/bhsa/tf/2021 \
  --module tf/2021 \
  --morphhb inputs/morphhb \
  --output build/canonical-graph/2021 \
  --source-commit 3d15126fb1ef74867fc1434be1942e837932691f

# Which original BHSA syntactic object ends coincide with each saved cut?
bhsa-cantillation compare-syntax \
  --graph build/canonical-graph/2021 \
  --verse Gen.1.1 \
  --format tsv --output build/genesis-1-1-syntax.tsv

# Compare the principal cantillation division to the BHSA half_verse division.
bhsa-cantillation compare-halves \
  --graph build/canonical-graph/2021 \
  --verse Gen.1.1 \
  --format jsonl --output build/genesis-1-1-halves.jsonl
```

Open `build/genesis-1-1-syntax.tsv` in a spreadsheet or TSV viewer.
Each row is a saved cantillation `cant_phrase` cut, identified by the
`phrase_id` and source verse `osis_id` (**OSIS** reference). Inspect
`slot_status` before comparing the `ends_phrase` flag and
`phrase_nodes` original BHSA IDs. In the pinned data, the cut
`Gen.1.1#p1-2` coincides with original BHSA phrase **651573**, while
`Gen.1.1#p3-4` does not coincide with an original phrase ending.
Inspect the rest of the four syntax types in the same TSV.

`cut_after_word_index` counts MorphHB source orthographic words within
the verse. `bhsa_cut_after_slot` is an original BHSA word-slot ID. The
coordinates are different and must never be compared numerically as if they
referred to the same tokens. Only `slot_status=comparable` has a defined
BHSA cut endpoint. A `fuzzy_alignment` or `ambiguous_slots` is
inconclusive rather than a syntactic disagreement. The second command's
`compare-halves` result compares cantillation's main cut with BHSA's
structural `half_verse` division; it is **not** an independent syntax
validation score.

The complete graph is a separately generated local artifact, **not** the
smaller checked-in `tf/2021` module. **Do not reuse a nonempty**
`build/canonical-graph/2021` output directory: `build-graph` explicitly
rejects this to prevent accidental mixing with stale data. Use a new empty
output path for a new build. These analyses validate the entire persisted
graph, even if you select one verse. Additional commands and field definitions
appear below under *Export saved cantillation boundaries* and
*Compare saved cantillation cuts with BHSA syntax endings*.

## Features

| Feature | Node type | Value |
| --- | --- | --- |
| `cantillation_accent` | `word` | Interpreted accent name |
| `cantillation_accent_type` | `word` | `conjunctive` or `disjunctive` |
| `cantillation_marks` | `word` | Raw Unicode cantillation sequence |
| `cantillation_accent_status` | `word` | `catalogued` or `unicode-fallback` |
| `cantillation_catalog_rank` | `word` | Original MorphHB catalogue rank (decimal string) |
| `cantillation_catalog_final` | `word` | Explicit MorphHB catalogue `final` flag (`1` or `0`) |
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
| `cantillation_word_count` | `verse` | MorphHB orthographic source words |
| `cantillation_main_cut_word_index` | `verse` | 1-based source-word index before the root cut |
| `cantillation_main_first_word_count` | `verse` | Source words in the first root child |
| `cantillation_main_second_word_count` | `verse` | Source words in the second root child |
| `cantillation_main_cut_fraction` | `verse` | First-child words / total source words |
| `cantillation_main_signed_split` | `verse` | (Second-child words - first-child words) / total |
| `cantillation_mean_leaf_depth` | `verse` | Mean root-to-leaf depth |
| `cantillation_colless` | `verse` | Colless imbalance index |
| `cantillation_colless_normalized` | `verse` | Colless divided by its maximum for the leaf count |
| `cantillation_sackin` | `verse` | Sum of all leaf depths |
| `cantillation_longest_ladder` | `verse` | Longest run of nested `1:(n-1)` splits |
| `cantillation_longest_accent_run` | `verse` | Longest same-accent run on a root-to-leaf path |
| `cantillation_depth_leaf_ratio` | `verse` | Maximum depth divided by leaf count |

The checked-in `tf/2021` artifact now includes the catalogue and root-cut
features. It was regenerated against MorphHB commit
`3d15126fb1ef74867fc1434be1942e837932691f` and the BHSA 2021
dataset at ETCBC/bhsa commit `4db00e2157915495e1a4d3d57e41223df24775da`.
The reproducibility gate compares all previously shipped TF feature data and
the full alignment report against the original pinned build before copying
only the eight new feature files.

All 23,213 verses have `cantillation_word_count`; 23,202 verses have
root-cut measurements, while the 11 single-unit verses have no root cut.
The catalogue-rank feature projects 305,199 catalogued MorphHB source words
onto 304,485 BHSA endpoint slots; the remaining 308 source words use the
documented Unicode fallback. The original upstream catalogue has no explicit
`final=false` entries: a missing final flag remains unknown.

Because BHSA slots represent morphological words, an orthographic MorphHB word
can correspond to several BHSA `word` nodes. Accent features are placed on the
last matching BHSA slot. Unit features are copied to all slots belonging to the
accentual unit.

At the few places where one BHSA slot crosses a MorphHB word or unit boundary,
all values are retained in source order and separated by ` | `. The JSON tree
remains unambiguous because its leaves preserve the individual source units.

Catalogue rank and `final` are taken directly from MorphHB's prose/poetic
`AccentCatalog.js`, with no inferred values for unlisted accent combinations.
When the source catalogue omits `final`, the feature is absent (it is **not**
interpreted as false). `1` represents an explicit true and `0` an explicit
false. Both endpoint features have TF `valueType=str` to preserve multiword
slot projections with ` | ` separators. Missing values are omitted
when every source word on the slot lacks that field; when some source words
have a value, `?` preserves the missing positions so entries remain aligned
with `cantillation_source_id`. For unambiguous word-level identity, consult
the MorphHB source IDs and the original alignment report.

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

The six word-count/root-cut features count MorphHB `SourceWord` instances (one
per directly parsed orthographic `<w>`), not BHSA word slots and not accentual units.
A multiword *qere* attached to one *ketiv* `<w>` remains one source record
in the existing parser; it is counted once rather than split on spaces.
For the main cut, the first child of the root binary tree is the first textual
span; its source-word count gives the inclusive word index before that cut.
Fractions are rounded to six decimal places. The signed split is positive
when the first span is shorter than the second, negative when it is longer,
and zero when equal. Verses consisting of one accentual unit have
`cantillation_word_count` but no defined root-cut features, so those five
features are absent on their verse nodes.

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

## Export saved cantillation boundaries

Build the separate, fully verified derived TF graph with `bhsa-cantillation
build-graph` (requires pinned BHSA, the checked-in module and MorphHB; see
`.github/workflows/canonical-graph.yml`). Then export its internal phrase cuts:

```bash
bhsa-cantillation boundaries \
  --graph build/canonical-graph/2021 \
  --format jsonl --output boundaries.jsonl
bhsa-cantillation boundaries \
  --graph build/canonical-graph/2021 \
  --format tsv --output boundaries.tsv
# Export just two exact OSIS verse IDs, retaining canonical graph order:
bhsa-cantillation boundaries \
  --graph build/canonical-graph/2021 \
  --verse Gen.1.2 --verse Gen.1.1 \
  --format jsonl --output genesis-boundaries.jsonl
```

Each boundary corresponds to a persisted `cant_phrase` node; the exporter reads
the saved `cant_parent`, `cant_cut_after`, `cant_terminal` and `cant_root`
edges, rather than parsing and rebuilding a tree. Rows are ordered by numeric
BHSA verse node, then `first_unit`, `last_unit` and phrase node. The 2021
pinned graph contains **142,534** boundary rows across **23,202** verses; the
11 single-unit verses have no cuts.

`cut_after_word_index` is the inclusive **1-based MorphHB source-word index**
from the start of the verse. `phrase_first_word_index` and
`phrase_last_word_index` are also inclusive 1-based source-word coordinates.
`first_child_word_count` and `second_child_word_count` count orthographic
MorphHB source words; the corresponding `*_unit_count` columns count accentual
units. `first_child_fraction` and `signed_split` are rounded to six decimal
places. The split sign is `(second_child_word_count - first_child_word_count) /
phrase_word_count`. `first_bhsa_slot`, `last_bhsa_slot` and
`bhsa_slot_count` describe the BHSA slot projection, which can overlap across
source words or units. They must not be used as source-word counts.

The output also preserves `verse_node`, `osis_id`, `system`, `alignment`,
`phrase_node`, `phrase_id`, `depth`, `cut_accent`, `cut_unit_id`,
`cut_terminal_word_id`, and `source_uri`. JSONL encodes count/index fields
as numbers; TSV uses a header and UTF-8 text. Both formats have fixed field
order. The exporter rejects inconsistent or disconnected persisted graphs and
replaces its output atomically only after every verse validates.
Repeated `--verse` arguments select exact, case-sensitive OSIS IDs. Duplicate
selections are ignored; output remains in canonical graph order, not argument
order. Even with a selection, **the full saved graph is validated**, including
unselected verses and disconnected nodes. Unknown OSIS IDs raise an error without
replacing an existing output file. A known single-unit verse has zero rows:
JSONL is empty, while TSV contains only its header.

## Compare root cantillation splits with BHSA half-verses

The read-only `compare-halves` command inspects the **persisted, derived TF
graph** and the original BHSA `half_verse` nodes included in that graph. It
does not rebuild segmentation or add graph edges.

```bash
bhsa-cantillation compare-halves \
  --graph build/canonical-graph/2021 \
  --format jsonl --output build/half-verse-comparison.jsonl
bhsa-cantillation compare-halves \
  --graph build/canonical-graph/2021 \
  --verse Gen.1.1 --verse Gen.7.11 --verse Gen.35.22 --verse Ps.36.1 \
  --format tsv --output build/half-verse-examples.tsv
```

The exporter writes **one row for every requested OSIS verse**, including
single-unit cantillation verses, in canonical numeric BHSA verse order.
`--verse` takes exact, case-sensitive OSIS IDs and can be repeated. Unknown
IDs fail without replacing an earlier output. As with `boundaries`, the
**entire saved cantillation graph** is validated even for a selection; output
replacement happens atomically after validation.

Each row includes `verse_node`, `osis_id`, `system`, `alignment`,
`root_phrase_node`, the inclusive 1-based MorphHB
`root_cut_after_word_index`, `half_verse_count`, semicolon-delimited
`half_verse_nodes` and `half_verse_spans`, the first BHSA half span, exact
root-left/right BHSA slot sets, and an overlap count. Slot sets use inclusive
ranges separated by commas, e.g. `1-3,5`; no source-word index is compared
as if it were a BHSA word slot.

`status` has mutually exclusive outcomes: `match` (root-left slot set equals
first half-verse slot set), `mismatch` (unambiguous unequal sets),
`no_root_split` (one accentual unit), `missing_half_verse` (no BHSA nodes),
`nonbinary_half_verse` (one or more than two BHSA segments),
`ambiguous_half_verse` (two segments with gaps/overlap/incomplete coverage),
`fuzzy_alignment` (MorphHB/BHSA alignment is not exact), and
`ambiguous_root_slots` (root children overlap, fail to cover the BHSA
verse, interleave, or appear in reverse BHSA slot order). A comparable root
cut must project to two **contiguous, forward-ordered** BHSA slot spans. Conditions are evaluated in that precedence order.
The command prints a JSON summary with `status_counts`, `verses`, and
`comparable`, where the agreement **denominator** is strictly
`match + mismatch`. Inconclusive statuses are never counted as mismatches.

For the pinned 2021 BHSA warp, 1,603 verses have one `half_verse`, 21,254
have two, and 356 have three. The three-segment group includes Gen.35.22
and Ezek.32.30 as prose exceptions; the other 354 are poetic. All pinned
half-verse spans partition their verses exactly. The 11 source single-unit
verses are Psalm superscriptions, and 10 verses have fuzzy alignments.
These cardinalities are validated in the pinned CI workflow. The pinned
comparison reports **20,991 matches, 43 mismatches and 212 ambiguous
root-slot projections**, yielding **21,034 comparable verses** (99.80%
agreement). It also reports 1,948 nonbinary half-verse cases, 11 unsplit
cantillation verses and 8 fuzzy-alignment cases.

For examples, `Gen.1.1` is a match; `Gen.7.11` has an ambiguous root
projection and must not be counted as a mismatch; `Gen.35.22` has three
BHSA segments, while `Ps.36.1` has no root cut. The pinned E2E test also
selects a genuine mismatch from the full exported data and verifies it
independently through the CLI.

## Compare saved cantillation cuts with BHSA syntax endings

The read-only `compare-syntax` command compares **every persisted
`cant_phrase` split** to the final occupied BHSA word slot of the original
`phrase`, `phrase_atom`, `clause_atom` and `clause` objects. No new TF
edges, syntax nodes or reconstructed cantillation trees are introduced.

```bash
bhsa-cantillation compare-syntax \
  --graph build/canonical-graph/2021 \
  --format jsonl --output build/syntax-endings.jsonl
bhsa-cantillation compare-syntax \
  --graph build/canonical-graph/2021 \
  --format tsv --verse Gen.1.1 --verse Gen.7.11 \
  --output build/syntax-examples.tsv
```

One row represents one saved cantillation phrase cut. Rows contain
`cut_after_word_index` (the **1-based MorphHB source-word index**),
`bhsa_cut_after_slot` (the **original BHSA numeric word slot**, when uniquely
projectable), the two exact child slot sets, `slot_status`, and four boolean
`ends_*` fields with the complete semicolon-delimited list of matching
original BHSA syntax node IDs (`phrase_nodes`, `phrase_atom_nodes`,
`clause_atom_nodes`, `clause_nodes`). Distinct syntax nodes can end at
the same slot. Ranges use inclusive notation, e.g. `1-3,5`; a source-word
index must never be interpreted as a BHSA slot.

`slot_status=comparable` requires `alignment=exact` plus two **disjoint,
contiguous, adjacent and forward-ordered** original BHSA child slot sets.
`fuzzy_alignment` and `ambiguous_slots` are **inconclusive**, with all
`ends_*` values `null` in JSONL or empty in TSV. A comparable `ends_*=false`
means no qualifying original BHSA node of that type ends at the cut slot.
A gapped functional `phrase` or `clause` is eligible by its **last
actually occupied slot** without filling its internal gaps. Syntax nodes
that span verses, have no slots, or reference unassigned word slots are
excluded from candidate endings and counted separately.

The JSON summary distinguishes `cuts`, `comparable`,
`status_counts`, and `matches_by_type`. A type's match count counts
**cantillation cuts**, not the possibly larger number of cofinal BHSA syntax
nodes. `syntax_node_exclusions_global` reports original syntax-node
exclusions over the **whole loaded BHSA graph**, even for a selected verse,
and is not part of the cut denominator. As with `boundaries`, repeated
`--verse` selects exact OSIS IDs in graph order, the full persisted graph is
validated, a known singleton verse has zero rows, and validation failures
leave the prior output untouched.

These are descriptive end-boundary coincidences, not independent proof of
syntactic or prosodic validity. The `half_verse` division belongs to a
different BHSA structural tier. See the exact-slot-set research record in
[issue #21](https://github.com/alexsosn/BHSA-cantillation-trees/issues/21).

## Inspect exact cantillation–syntax constituency relations

Use `syntax-relations` to answer whether a saved accentual constituent is
identical to, contained in, contains, crosses, or is disjoint from an original
BHSA `phrase`, `phrase_atom`, `clause_atom`, or `clause`.
The command reads the persisted graph and original BHSA `oslots`; it
neither reconstructs the tree nor materializes pairwise edges.

```bash
bhsa-cantillation syntax-relations \
  --graph build/canonical-graph/2021 \
  --verse Gen.1.1 --verse Gen.1.7 \
  --format jsonl --output build/genesis-syntax-relations.jsonl
bhsa-cantillation syntax-relations \
  --graph build/canonical-graph/2021 \
  --verse Gen.1.7 --format tsv \
  --output build/genesis-syntax-relations.tsv
```

At least one case-sensitive `--verse` is **required**. Repeat it for other
verses. This keeps the potentially large `cant_phrase × BHSA syntax node`
comparison bounded. Duplicate selections are deduplicated and rows are
ordered by canonical verse, saved phrase span, syntax type, and original
syntax node ID. A known singleton verse produces zero rows; an unknown
verse or a corrupt saved graph fails without overwriting an earlier result.
The entire saved cantillation graph is checked even when only one verse
is selected.

Each row identifies the OSIS verse, saved `phrase_id` and `phrase_node`,
its original BHSA slot set (`cantillation_bhsa_slots`), the selected
original BHSA `syntax_type` and numeric `syntax_node`, its **exact**
`syntax_bhsa_slots`, and `relation`. Both slot sets are rendered as
inclusive consecutive runs, e.g. `1-3,5` for a discontinuous node.
`cut_after_word_index` is a MorphHB orthographic word position, **not** a
BHSA slot index.

The mutually exclusive pairwise relations are:

| `relation` | Meaning |
| --- | --- |
| `exact` | Identical occupied BHSA slot sets |
| `inside` | Cantillation phrase is a proper subset of the BHSA syntax node |
| `contains` | Cantillation phrase is a proper superset of the syntax node |
| `crossing` | They overlap in occupied BHSA slots, neither containing the other |
| `disjoint` | They share **no** occupied slots, even when numeric envelopes interleave |

Only `slot_status=comparable` phrases are classified: their verse alignment
must be `exact`, and the two saved children must have disjoint, consecutive,
forward-ordered and adjacent BHSA slot projections. For `fuzzy_alignment`
or `ambiguous_slots` the report emits one row for the affected phrase with
`relation=null` and no syntax node; this is **inconclusive**, not a
disagreement. A comparable phrase with no eligible original syntax nodes also
receives one null row. Original syntax nodes spanning verses, missing slots,
or pointing to unassigned slots are excluded rather than silently attached
to one verse.

The printed JSON summary separates `cuts` (saved cantillation phrases),
`comparable` (eligible phrases), `comparisons` (actual phrase/syntax
pairs), `status_counts` (per phrase), `relation_counts` (per pair),
`relations_by_type` (per pair/type), `candidates_selected_by_type`
(distinct original syntax nodes in selected verses),
`syntax_node_totals_global` and `syntax_node_exclusions_global`.
Do not divide pair counts by the number of cuts or interpret a shared
end-boundary as exact constituency. In the pinned BHSA, functional syntax
nodes may be gapped and even cross verse boundaries, so checking only
`min(oslots)` and `max(oslots)` produces false crossing claims.

This is a descriptive comparison of two source-encoded structures, not
an independent correctness score for either. For simpler cut-end questions,
use `compare-syntax`; for whole-verse main divisions use `compare-halves`.

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

## Canonical graph projection (experimental)

The converter also provides a pure-Python representation of the existing
MorphHB-derived graph, preserving distinct source words and accentual units
when several of them map to the same BHSA word slot:

```python
from bhsa_cantillation.graph import project_graph, reconstruct_tree
from bhsa_cantillation.tree import build_tree, make_units

units = make_units(word_alignments)  # from the existing MorphHB/BHSA aligner
tree = build_tree(units)
graph = project_graph("Gen.1.1", word_alignments, units, tree)

assert reconstruct_tree(graph) == tree
root = graph.phrases[graph.root]
cut_unit_id = graph.cuts[root.id]
```

The graph exposes `words`, `units`, `phrases` and the valued
`parents` (child → parent, `1` or `2` in **textual order**),
`cuts` (phrase → unit immediately before the split), and `terminals`
(unit → source word closing the unit). Source-word IDs are MorphHB IDs;
unit and phrase IDs encode the verse and unit span. Every node's `slots`
is a deduplicated union of BHSA word slots without collapsing source identities.

### Separate full Text-Fabric graph dataset

The canonical graph can also be materialized as a **separate, full derived BHSA
Text-Fabric dataset**. This leaves the lightweight `tf/2021` feature module
and all original BHSA node IDs unchanged. It does **not** add warp nodes to
the existing feature module.

```bash
bhsa-cantillation build-graph \
  --bhsa /path/to/bhsa/tf/2021 \
  --module tf/2021 \
  --morphhb /path/to/pinned/morphhb \
  --output build/canonical-graph/2021 \
  --source-commit 3d15126fb1ef74867fc1434be1942e837932691f
```

Use MorphHB commit `3d15126fb1ef74867fc1434be1942e837932691f` and
ETCBC/bhsa commit `4db00e2157915495e1a4d3d57e41223df24775da` for the
pinned 2021 build. The output must be a new or empty directory; it is **not**
committed into the lightweight module. Building a full BHSA copy requires
substantial RAM and disk space.

New node types: `cant_word` (source-word identity), `cant_unit` (accentual
units), and `cant_phrase` (internal constituents). Graph edges are
`cant_parent` (valued child→parent, 1/2 textual order),
`cant_cut_after` (phrase→closing first-child unit),
`cant_terminal` (unit→terminal word),
`cant_member` (word→unit), and `cant_root` (original BHSA verse→root).
Word, unit and phrase `oslots` preserve overlapping MorphHB/BHSA alignments.

The build compares each source-derived verse tree with the pinned
`cantillation_tree` JSON; reloads the full TF dataset; independently verifies
all original `otype` node IDs, appended type ranges, feature values, slot
unions and edge orientation; and reconstructs **every** verse tree from the
saved graph. Workflow `canonical-graph-integration` performs this against
both pinned source repositories.

This is a derived dataset with BHSA's own licensing terms. A new release
must keep the original BHSA and MorphHB attribution and should not be
distributed as an ordinary feature-only `mod` directory.

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
