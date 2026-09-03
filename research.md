# Research: richer cantillation graph and reproducible analysis features

## Status

This document records research recommendations for extending `BHSA-cantillation-trees`
beyond verse-level tree-shape metrics. It is intentionally broader than an implementation
specification. `plan.md` turns the recommendations into staged work.

The central recommendation is to distinguish three layers:

1. **Canonical source-derived structure**: objects and relations that are determined by the
   pinned MorphHB data, the current MorphHB-to-BHSA alignment, and the existing deterministic
   tree builder.
2. **Derived quantitative descriptors**: reproducible metrics over the canonical structure,
   with explicit formulas and source/method metadata.
3. **Interpretive analysis profiles**: named scholarly models, especially competing proposals
   for poetic colometry. These must remain identifiable as interpretations rather than being
   folded into a single allegedly definitive segmentation.

This separation makes the data useful for both traditional accent research and quantitative
syntax/prosody work while keeping provenance inspectable.

## Current model and its main limitation

The converter already has richer objects internally than the generated Text-Fabric module
exposes:

- `SourceWord` represents a MorphHB orthographic/graphematic word.
- `AccentUnit` groups zero or more conjunctive words through the following disjunctive word.
- `build_tree()` creates a full binary tree whose leaves are `AccentUnit`s and whose internal
  nodes are labelled by the disjunctive accent at the cut.

The generated TF module currently serializes the whole tree as JSON on the BHSA `verse` node,
copies unit identity/path features onto BHSA word slots, and saves no edge features. This is
compact, but it makes several natural research objects implicit:

- a MorphHB word is represented only indirectly on one or more BHSA slots;
- an accentual unit must be reconstructed from repeated scalar features;
- an internal prosodic constituent exists only inside JSON;
- a branch cut is not directly queryable as a graph relation.

The pinned build currently contains 23,213 verse trees, 305,507 MorphHB source words, and
165,747 accentual units. Because every verse tree is full binary, the present data imply
`165,747 - 23,213 = 142,534` internal tree nodes. Promoting the three already-determined
levels to TF objects would therefore add about 613,788 nodes. That is a meaningful increase,
but still a modest graph relative to a BHSA 2021 corpus with roughly 1.44 million existing
nodes.

The richer object model also represents rare alignment cases more honestly. The current README
reports BHSA slots aligned to multiple MorphHB orthographic words and a smaller set of slots
belonging to multiple accentual units. Scalar features currently preserve these with a ` | `
separator. Overlapping non-slot nodes with `oslots` can preserve the same facts without
encoding multiplicity inside strings.

## Scholarly basis

### Hierarchical tree structure should be first-class data

Aronoff describes the Masoretic punctuation system as providing a complete binary
phrase-structure analysis of each verse. Dresher argues that the accentual representation is
best understood as prosodic structure: it is systematically related to syntax but can diverge
from syntactic constituency in ways expected of prosodic representations.

Wu and Lowery made this computationally explicit in 2006. Their cantillation treebank exposes
the hierarchy that is otherwise encoded in diacritics, and their follow-up work shows that many
prosodic boundaries correspond directly or indirectly to syntactic phrase boundaries. This is a
strong precedent for representing internal cantillation constituents as nodes rather than only
as a serialized verse feature.

References:

- Mark Aronoff, “Orthography and Linguistic Theory: The Syntactic Basis of Masoretic Hebrew
  Punctuation,” *Language* 61/1 (1985), 28–72. DOI: https://doi.org/10.2307/413420
- B. Elan Dresher, “The Prosodic Basis of the Tiberian Hebrew System of Accents,” *Language*
  70/1 (1994), 1–52. Overview: https://www.cambridge.org/core/journals/language/article/abs/prosodic-basis-of-the-tiberian-hebrew-system-of-accents/4B9357970E8D5222D7F3865F46640EC4
- Andi Wu and Kirk Lowery, “A Hebrew Tree Bank Based on Cantillation Marks,” LREC 2006:
  https://aclanthology.org/L06-1002/
- Andi Wu and Kirk Lowery, “From Prosodic Trees to Syntactic Trees,” COLING/ACL 2006:
  https://aclanthology.org/P06-2115/

### Boundary strength, word count, cut position, and syntax are more useful than more abstract tree indexes

The repository already contains depth, mean leaf depth, Sackin, Colless, ladder length,
accent-run length, and shape signatures. Additional generic binary-tree indexes are possible,
but the cantillation literature more often asks about the hierarchy and position of boundaries,
word counts, accent sequences, and the relation between accentual and syntactic structure.

Rachel Hitin-Mashiah’s quantitative study of the main division in the Twenty-One Books is a
particularly useful model for reproducible corpus work. It starts from continuous dichotomy but
shows that the choice of the main disjunctive is also correlated with verse length, location of
the cut, additional division, and syntax. Her study explicitly counts Hebrew words, not
accentual-unit leaves. This means that the current `cantillation_leaf_count` cannot stand in for
verse length in this kind of analysis.

Ronit Shoshany’s Hebrew-language work on the historical development of accentual division
uses the distinction between **iambic division** (shorter first part, longer second part) and
**trochaic division** (longer first part, shorter second part). This supports retaining the
*direction* of a split. The current Colless index uses an absolute difference and therefore
intentionally discards direction.

Robert Crellin’s 2025 quantitative study demonstrates the value of a word-level and
boundary-strength representation. Using a prosodic treebank aligned to morphosyntax, he tests
prosodic strength against parts of speech and high-level clause constituent order in Genesis,
Exodus, and 1 Kings. This is exactly the kind of analysis a BHSA-aligned cantillation graph
should make straightforward.

References:

- Rachel Hitin-Mashiah, “Main Division in the Verse in the 21 Prose Books: Syntactic Study,”
  *Textus* 26 (2016), 199–208. Open PDF:
  https://openscholar.huji.ac.il/sites/default/files/he_bible_project/files/main_division_in_the_verse_in_the_21.pdf
- Ronit Shoshany, “תפקידם המקורי של טעמי המקרא,” in *משאת אהרן* (Jerusalem, 2010),
  469–486. Bibliographic/preview entry:
  https://kotar.cet.ac.il/kotarapp/index/Chapter.aspx?nBookID=99094791&nTocEntryID=99099862
- Robert S. D. Crellin, “Main Clause Verbs are Prosodically Weaker than Nouns in the Tiberian
  Cantillation of Biblical Hebrew Prose Books,” in *The Intertwined World of the Oral and
  Written Transmission of Sacred Traditions in the Middle East* (2025), 173–228.
  DOI: https://doi.org/10.11647/obp.0498.05

### Poetry should expose named segmentation profiles, not one flattened colometry

The Three Books require their own treatment. The literature does not justify replacing the
poetic cantillation system with a single threshold such as “every accent at rank X ends a
colon.” Different authors formulate different operational criteria and, in some cases, address
different research questions.

Raymond de Hoop argues that the value of a disjunctive depends on its position in the complete
accentual syntax; merely calling an accent “major” is insufficient. His Part I focuses on the
poetic/Three-Books system and explicitly evaluates the use of Masoretic accentuation for
colometry.

Sung Jin Park gives unusually operational guidance for colometry. The published abstract lists
four core rules: major disjunctives function as main colon dividers; certain minor disjunctives
may also end a colon under specified conditions; a colon normally contains two disjunctives;
a sequence of three disjunctives whose first two are not major may form one monocolon; and a
conjunctive accent does not end a colon. The full article must be transcribed into tests before
implementation; the abstract alone is not sufficient to encode every exception.

Kevin Trompelt’s German-language study gives a detailed account of the hierarchy of accents in
Psalms, Job, and Proverbs and foregrounds the law of continuous dichotomy. It is particularly
relevant to validating the canonical poetic tree structure.

Tania Notarius addresses a different problem. Her “double segmentation” model treats poetic
and syntactic segmentation as distinct interacting layers. In selected Psalms the cantillation
system is sensitive to poetic segmentation but can also follow syntax when the two conflict.
This should not be implemented as a simple alternate list of colon boundaries. A Notarius-style
analysis is better represented as a diagnostic comparison between a poetic segmentation and
BHSA syntactic segmentation, with explicit conflict/alignment classes.

References:

- Raymond de Hoop, “The Colometry of Hebrew Verse and the Masoretic Accents: Evaluation of a
  Recent Approach (Part I),” *Journal of Northwest Semitic Languages* 26/1 (2000), 47–73.
  Author-deposited full text:
  https://www.researchgate.net/publication/311903418_THE_COLOMETRY_OF_HEBREW_VERSE_AND_THE_MASORETIC_ACCENTS_EVALUATION_OF_A_RECENT_APPROACH_PART_1
- Raymond de Hoop, Part II, *JNSL* 26/2 (2000):
  https://journals.co.za/doi/10.10520/EJC101218
- Sung Jin Park, “Application of the Tiberian Accentuation System for Colometry of Biblical
  Hebrew Poetry,” *JNSL* 39/2 (2013), 113–128. Journal abstract:
  https://academic.sun.ac.za/jnsl/Volumes/JNSL%2039%202%20abstracts%20and%20bookreviews.pdf
- Kevin Trompelt, “Die masoretische Akzentuation in den poetischen Büchern (ספרי אמ״ת),”
  *Vetus Testamentum* 73/3 (2023), 445–480. DOI:
  https://doi.org/10.1163/15685330-00001152
- Tania Notarius, “‘Double Segmentation’ in Biblical Hebrew Poetry and the Poetic
  Cantillation System,” *Zeitschrift der Deutschen Morgenländischen Gesellschaft* 168/2
  (2018), 333–362. DOI: https://doi.org/10.13173/zeitdeutmorggese.168.2.0333

A recent broad introduction is also useful for terminology and for keeping the two Tiberian
subsystems distinct:

- Raymond de Hoop and Paul Sanders, “The System of Masoretic Accentuation: Some Introductory
  Issues,” *Journal of Hebrew Scriptures* 22 (2022). DOI: https://doi.org/10.5508/jhs29622

## Recommended canonical graph

### 1. `cant_word`: MorphHB orthographic/graphematic word

This should be the lowest new non-slot level. BHSA slots are morphological words; a MorphHB
orthographic word can correspond to one or several BHSA slots. `cant_word` makes that alignment
queryable without pretending the two tokenizations are identical.

Recommended node features:

| Feature | Meaning |
| --- | --- |
| `cant_word_id` | stable MorphHB source identifier |
| `cant_word_ordinal` | 1-based textual ordinal within the verse |
| `cant_word_text` | MorphHB vocalized/marked text used by the build |
| `cantillation_marks` | raw cantillation/punctuation marks |
| `cantillation_accent` | interpreted catalogue/fallback accent name |
| `cantillation_accent_type` | conjunctive/disjunctive |
| `cantillation_catalog_rank` | upstream MorphHB catalogue `rank` where available |
| `cantillation_catalog_final` | upstream MorphHB catalogue `final` flag where available |
| `cantillation_accent_status` | `catalogued` / `unicode-fallback` |
| `cantillation_path` | MorphHB structural path when present |

The current endpoint features on BHSA slots should remain for backwards compatibility; the new
node becomes the canonical home for source-word metadata.

`cant_word_id` should be stable across rebuilds as long as the pinned MorphHB source ID is
stable. TF numeric node IDs should never be treated as external identifiers.

### 2. `cant_unit`: accentual unit

This is the existing `AccentUnit` promoted to a TF node. Its `oslots` are the union of the BHSA
slots occupied by its source words.

Recommended node features:

| Feature | Meaning |
| --- | --- |
| `cant_unit_id` | deterministic stable ID, e.g. `Gen.1.1#u3` |
| `cant_unit_ordinal` | textual ordinal within verse |
| `cantillation_path` | structural path from the terminal source word |
| `cant_terminal_accent` | disjunctive accent that closes the unit |
| `cant_unit_word_count` | number of `cant_word` children |
| `cant_unit_slot_count` | number of BHSA slots covered |

The existing BHSA-slot feature `cantillation_unit` can remain as a convenience projection.

### 3. `cant_phrase`: every internal binary tree node

This is the most important structural addition. A `cant_phrase` spans all slots dominated by an
internal node in the current JSON tree. It exposes the continuous-dichotomy hierarchy to normal
TF graph queries.

Recommended node features:

| Feature | Meaning |
| --- | --- |
| `cant_phrase_id` | stable verse-local span ID, e.g. `Gen.1.1#p3-7` for unit span 3..7 |
| `cant_cut_accent` | accent labelling the cut |
| `cant_phrase_depth` | root-relative depth |
| `cant_phrase_unit_count` | dominated accentual units |
| `cant_phrase_word_count` | dominated `cant_word`s |
| `cant_first_unit` | first dominated unit ordinal |
| `cant_last_unit` | last dominated unit ordinal |
| `cant_cut_after_unit` | unit ordinal immediately before the split, also represented by an edge |

A span-based stable ID is preferable to preorder numbering because it survives unrelated node
renumbering and is directly interpretable.

### 4. Edge relations

The graph needs only a small number of explicit semantic edges. Containment itself is already
represented by `oslots` and can be recovered through TF locality APIs.

#### `cant_parent`

Child (`cant_phrase` or `cant_unit`) -> parent `cant_phrase`.

This should be a valued edge whose value is `1` or `2`, meaning first or second child in
**textual order**. Avoid `left`/`right`: visual direction is ambiguous in an RTL text while
first/second is not.

The root `cant_phrase` has no parent. A one-unit verse has no `cant_phrase` and its sole
`cant_unit` is directly the verse’s root object for traversal purposes.

#### `cant_cut_after`

`cant_phrase` -> `cant_unit` immediately before the branch cut.

The existing tree builder already determines this unit (`units[split - 1]`) when labelling the
internal node. Making it an edge gives an exact answer to “where does this dichotomy divide the
text?” without parsing JSON.

#### `cant_terminal`

`cant_unit` -> terminal `cant_word` carrying the disjunctive that closes the unit.

This provides a transparent route from an internal phrase cut to the physical source word and
then, through `oslots`, to BHSA slots.

### 5. Relations that should initially stay computed

Do **not** materialize all pairwise overlap/containment relationships between cantillation nodes
and BHSA `phrase`, `phrase_atom`, `clause`, `clause_atom`, `sentence`, or `half_verse` nodes.
Both sides have `oslots`, so exact match, containment, overlap, and crossing can be computed.
Materializing every relation would duplicate the warp and create a large, harder-to-maintain
edge set.

A later `cant_exact_match` edge may be justified for common high-value queries, but only after a
benchmark shows that computed span comparison is inconvenient or slow.

## Optional later node types

### `prosodic_word`

A distinct prosodic-word layer would group orthographic words linked by maqqef and would better
match some modern prosodic analyses. It is promising for phonological/recitation work, but it
should follow the canonical `cant_word`/`cant_unit`/`cant_phrase` graph because the exact
operational treatment of maqqef groups must be specified and tested against the source data.

### `poetic_segment`

Named colometric profiles should materialize their proposed cola/lines as `poetic_segment`
nodes in an **optional analysis artifact**, not in the canonical source-derived graph.

Recommended features:

| Feature | Meaning |
| --- | --- |
| `segmentation_profile` | e.g. `dehoop2000`, `park2013`, `trompelt2023` |
| `segment_level` | `colon`, `line`, or another explicitly defined level |
| `segment_ordinal` | textual order within the verse |
| `rule_id` | exact profile rule that produced the boundary |
| `profile_version` | version of the local formalization |
| `source_citation` | bibliographic reference/pages or rule section |
| `decision_status` | rule / exception / unresolved, as appropriate |

Profiles are allowed to overlap and disagree. Disagreement is data to expose, not an error to
normalize away.

Notarius should initially be implemented as a diagnostic layer rather than a simple segmentation
profile: compare poetic-profile segments against BHSA syntactic constituents and classify
boundaries as aligned, poetic-only, syntactic-only, or crossing/conflicting.

## Recommended quantitative features

### Source/catalogue values

The MorphHB `AccentCatalog.js` already provides `rank` and, for many entries, `final`. The
current parser uses the catalogue name but discards these fields. Preserve them as source-derived
features before defining any modernized “strength” scale.

Recommended additions:

- `cantillation_catalog_rank`
- `cantillation_catalog_final`
- explicit prose/poetic mapping metadata for any derived disjunctive-level feature

Do not rename MorphHB `rank` to “strength”: a scholarly boundary-strength model is a separate
derived interpretation.

### Word-count and main-cut descriptors

For each verse, add quantities based on actual MorphHB orthographic words in addition to the
existing accentual-unit leaf counts:

- `cantillation_word_count`
- `cantillation_main_cut_word_index`
- `cantillation_main_first_word_count`
- `cantillation_main_second_word_count`
- `cantillation_main_cut_fraction`

where

```text
main_cut_fraction = first_word_count / total_word_count
```

These support direct comparison with studies such as Hitin-Mashiah, which use Hebrew word
counts rather than leaf counts.

### Directional split features

For a split into first and second spans with word counts `a` and `b`, retain a signed measure:

```text
signed_split = (b - a) / (a + b)
```

Positive values place the shorter span first; negative values place the longer span first.
Store this at each `cant_phrase` and optionally aggregate the root/main split at verse level.
This complements Colless rather than replacing it: Colless measures imbalance magnitude while
`signed_split` retains textual direction.

### Disjunctive level and boundary strength

A normalized D-level (`D0` ... `D3`, or another documented scheme) and a numeric boundary
strength are useful for quantitative syntax/prosody work, but they are **derived research
features**, not raw MorphHB fields. The implementation must:

1. cite the exact mapping used;
2. keep prose and poetic systems separate;
3. preserve the raw catalogue rank alongside the derived value;
4. version the method if contextual adjustments are implemented.

Crellin 2025 provides a recent concrete model for corpus-level boundary-strength analysis and
should be reproduced on a small published subset before applying the scheme to the whole
corpus.

### Long-form boundary export

Once `cant_phrase` nodes exist, every internal phrase corresponds to a branch-cut event. Generate
a flat `analysis/boundaries.tsv` or JSONL projection so results can be checked without TF:

```text
verse
system
cant_phrase_id
first_unit
last_unit
cut_after_unit
cut_accent
catalog_rank
derived_level
derived_strength
first_word_count
second_word_count
signed_split
bhsa_start_slot
bhsa_end_slot
```

Later syntax columns can be added without changing the canonical graph.

Every aggregate report should be reproducible from this table and return its denominator plus
verse references for exceptional cases.

## BHSA syntax and `half_verse` as an independent comparison layer

BHSA already provides `half_verse`, `phrase`, `phrase_atom`, `clause`, `clause_atom`, `sentence`,
and related node types over the same slots. This is a major advantage of this project over a
standalone cantillation treebank.

The first comparison should be structural and low-assumption:

- exact span match between `cant_phrase` and each BHSA syntactic type;
- whether a cantillation cut coincides with the end of a BHSA `phrase`, `clause_atom`, or
  `clause`;
- relation between the root cantillation split and BHSA `half_verse` spans;
- crossing cases, which are especially informative for syntax/prosody mismatch.

Prefer event-level columns/flags to a single opaque `syntax_alignment_score`:

- `ends_phrase`
- `ends_phrase_atom`
- `ends_clause_atom`
- `ends_clause`
- `matches_half_verse_boundary`

This allows users to define their own aggregate measures and makes the result auditable.

## Poetry segmentation profiles

Profiles should be implemented as deterministic rule engines with explanation traces.
A decision must be able to say not only `split=true`, but also **which published rule caused the
split**.

A useful record shape is:

```json
{
  "verse": "Ps.68.17",
  "profile": "park2013",
  "profile_version": "1.0",
  "boundary_after_word": 7,
  "decision": true,
  "rule_id": "PARK-...",
  "evidence": ["..."],
  "source": {"citation": "Park 2013", "pages": "..."}
}
```

Initial profile targets:

1. **`dehoop2000`** — Three-Books colometry with contextual accentual syntax; implementation
   must encode position/context rather than a simple list of “major” accents.
2. **`park2013`** — operational colometry rules, encoded from the full article and tested on
   its examples before corpus-wide use.
3. **`trompelt2023`** — hierarchy/continuous-dichotomy validation for the poetic system; this
   may initially function more as a structural validator than as an independent colon extractor.
4. **`notarius2018-diagnostic`** — compare poetic and syntactic segmentation; do not pretend
   that pragmatic marking, glossing, pivots, or heavy enjambment can be inferred from
   cantillation alone without additional evidence.

A profile-comparison report should preserve disagreement explicitly:

```text
verse | boundary | dehoop2000 | park2013 | trompelt2023 | support
```

`support` can be useful for exploration, but must never be described as probability or ground
truth.

## Text-Fabric packaging implications

This is the main architectural constraint.

Text-Fabric defines a dataset as a **warp** (`otype` + `oslots`, optionally `otext`) plus normal
features. A feature-only module contains wefts that are constructed around the warp of another
dataset. The current repository is such a lightweight module: it saves node features against the
BHSA 2021 node IDs and no edge features.

New node types change `otype` and `oslots`, so they cannot be treated as ordinary feature-only
additions without changing the warp. Text-Fabric has an explicit supported mechanism for this:
`tf.dataset.modify(..., addTypes=...)` can add non-slot node types linked to the existing slots
and write a new derived TF dataset.

References:

- TF data model: https://annotation.github.io/text-fabric/tf/about/datamodel.html
- TF dataset modification / `addTypes`:
  https://annotation.github.io/text-fabric/tf/dataset/modify.html

Recommended packaging strategy:

- **Keep `tf/2021` as the backwards-compatible lightweight feature module.** Existing users
  should still be able to load it with `mod=` exactly as documented today.
- **Generate a separate richer graph artifact from pinned BHSA + MorphHB**, using the same
  source commits and deterministic alignment. It can be distributed as a derived TF dataset or
  release artifact whose warp extends BHSA 2021 with the new node types.
- Do not rely on undocumented/fragile warp overriding through a normal module until a dedicated
  compatibility prototype proves that `tf.app.use`, locality, search, export, and BHSA feature
  access all behave correctly.

A graph build should preserve every original BHSA node ID and slot. New nodes are appended only.
That keeps all original BHSA node and edge features meaningful in the derived dataset.

## Reproducibility requirements

Every proposed addition should satisfy the following:

- BHSA and MorphHB commits remain pinned in `sources.json` and CI.
- Canonical nodes and edges are regenerated; they are not manually curated.
- Every new derived feature has a formula/method identifier in metadata or documentation.
- Poetry profiles carry bibliographic source, profile version, and rule IDs.
- Aggregate results can be expanded to the complete list of verse/boundary records behind them.
- JSON tree and graph representations round-trip to the same unit spans and cut labels.
- Existing Waxman comparison remains valid; a graph representation must not silently change the
  canonical tree algorithm.
- External validation against another explicit treebank (especially TanakhML if its terms permit
  the intended comparison workflow) should compare spans/cuts rather than raw serialization.
- Fuzzy MorphHB/BHSA alignments and catalogue fallbacks stay visible in all relevant exports.

## Priority recommendation

The highest-value sequence is:

| Priority | Work | Rationale |
| --- | --- | --- |
| P0 | Preserve MorphHB catalogue rank/final | source data already available; low ambiguity |
| P0 | Add orthographic word counts/main cut descriptors | immediately reproduces published quantitative questions |
| P0 | Build `cant_word`, `cant_unit`, `cant_phrase` graph artifact | makes latent canonical structure first-class |
| P0 | Add `cant_parent`, `cant_cut_after`, `cant_terminal` | minimal explicit tree relations |
| P1 | Boundary TSV/JSONL projection | makes every statistic independently auditable |
| P1 | BHSA phrase/clause/half-verse comparison | exploits the unique value of a BHSA-aligned treebank |
| P1 | Documented D-level/strength model | enables Crellin-style quantitative work |
| P1 | Signed split metrics | retains directional information lost by Colless |
| P2 | `dehoop2000` and `park2013` profiles | reproducible competing colometries |
| P2 | `trompelt2023` poetic hierarchy validator | independent rule-based validation of the poetic system |
| P2 | Notarius double-segmentation diagnostic | syntax/poetry conflict analysis rather than a simplistic segmentation |
| P3 | `prosodic_word` | valuable for phonological/recitation research after maqqef semantics are fixed |

The main design principle is to keep the canonical graph conservative and source-derived, while
making interpretations richer, named, reproducible, and easy to compare.