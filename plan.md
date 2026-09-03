# Plan: implement richer cantillation structure and reproducible analyses

## Goal

Extend `BHSA-cantillation-trees` from a feature-only verse-tree module into a project that can
also expose the cantillation hierarchy as a queryable graph, while preserving the existing
lightweight `tf/2021` module and its loading interface.

The implementation is deliberately staged. Canonical source-derived structure comes first;
quantitative and interpretive analyses build on that structure later.

## Non-goals for the first implementation cycle

- Do not replace or rewrite the existing tree-building algorithm.
- Do not remove `cantillation_tree` JSON or any existing TF feature.
- Do not declare a single “correct” poetic colometry.
- Do not materialize every possible overlap relation with BHSA syntax.
- Do not add generic tree-shape indexes merely because they are easy to compute.
- Do not silently normalize fuzzy MorphHB/BHSA alignments or uncatalogued accent patterns.

## Phase 0 — lock the schema with tests and fixtures

### Deliverables

1. Add a small set of canonical verse fixtures covering:
   - one simple prose verse;
   - one prose verse with several tree levels;
   - one poetic verse;
   - a one-unit verse if present;
   - a maqqef case;
   - a known BHSA/MorphHB many-to-one or crossing alignment case;
   - at least one `unicode-fallback` accent case.
2. Define stable identifiers for all future graph objects.
3. Document graph edge direction and ordering semantics.

### Proposed identifiers

- `cant_word_id`: MorphHB source ID.
- `cant_unit_id`: `<osis-id>#u<ordinal>`.
- `cant_phrase_id`: `<osis-id>#p<first-unit>-<last-unit>`.

Phrase span IDs must be unique within each verse; add a corpus-wide assertion before relying on
this format.

### Edge conventions

Use:

- `cant_parent`: child -> parent `cant_phrase`, valued `1`/`2` for first/second child in textual
  order;
- `cant_cut_after`: `cant_phrase` -> the `cant_unit` immediately before the split;
- `cant_terminal`: `cant_unit` -> its final `cant_word`.

The test suite must verify that `1`/`2` means first/second in textual order, never visual
left/right.

### Acceptance tests

For every fixture:

- graph leaves have the same unit spans as JSON leaves;
- each internal graph node has exactly two children;
- graph cut labels equal JSON internal-node accent labels;
- `cant_cut_after` points to the unit that supplies the internal-node label;
- `cant_terminal` points to the source word with the closing disjunctive;
- all new nodes’ `oslots` equal the union of the slots of the source objects they dominate.

## Phase 1 — preserve raw MorphHB catalogue metadata

This is low-risk and should land before the graph work if convenient.

### Model changes

Extend `SourceWord` with explicit catalogue metadata, at minimum:

```text
accent_rank: int | None
accent_final: bool | None
```

Do not infer these values for `unicode-fallback` entries.

### TF features

Add backwards-compatible endpoint features on BHSA slots:

- `cantillation_catalog_rank`
- `cantillation_catalog_final`

`cantillation_catalog_final` should use an unambiguous serialization accepted by TF, e.g.
`1`/`0` or `true`/`false`, documented in metadata.

### Tests

- known prose catalogue entries retain expected rank/final;
- known poetic entries demonstrate that the poetic hierarchy is independent of prose;
- fallbacks have no invented rank/final value;
- generated feature metadata identifies these as upstream MorphHB catalogue fields.

## Phase 2 — add real orthographic-word and main-cut measurements

### Verse features

Add:

- `cantillation_word_count`
- `cantillation_main_cut_word_index`
- `cantillation_main_first_word_count`
- `cantillation_main_second_word_count`
- `cantillation_main_cut_fraction`
- `cantillation_main_signed_split`

Definitions:

```text
main_cut_fraction = first_word_count / total_word_count
main_signed_split = (second_word_count - first_word_count) / total_word_count
```

Use MorphHB orthographic/graphematic words as the counting unit. Do not substitute BHSA
morphological slots or accentual-unit leaves.

### Reproduction report

Add a script/report that reproduces at least one published Hitin-Mashiah-style table from the
available corpus definition, with explicit selection criteria and verse references.

The purpose is not to force exact agreement if editions or exclusion rules differ. The report
must expose:

- query definition;
- denominator;
- counts;
- exclusions;
- verse list for discrepancies.

## Phase 3 — generate the canonical cantillation graph

### Architectural decision

Keep `tf/2021` unchanged as a feature-only module.

Generate a separate graph artifact from the pinned BHSA dataset using Text-Fabric’s supported
node-type modification path (`tf.dataset.modify(..., addTypes=...)`) or an equivalent documented
TF conversion path that produces a full derived dataset.

The graph artifact must preserve:

- BHSA word slots and their numeric IDs;
- all original BHSA node IDs;
- all original BHSA features and edges;
- new nodes appended after the original BHSA node range.

Before committing to a public artifact layout, prototype and test loading with the supported TF
APIs used by this repository. Do not rely on a feature module overriding `otype`/`oslots` unless
that behavior is explicitly tested and documented.

### New node type: `cant_word`

Create one node per MorphHB `SourceWord`.

`oslots` = all BHSA slots aligned to that source word.

Recommended node features:

- `cant_word_id`
- `cant_word_ordinal`
- `cant_word_text`
- `cantillation_source_id`
- `cantillation_accent`
- `cantillation_accent_type`
- `cantillation_marks`
- `cantillation_accent_status`
- `cantillation_catalog_rank`
- `cantillation_catalog_final`
- `cantillation_path`

### New node type: `cant_unit`

Create one node per existing `AccentUnit`.

`oslots` = union of slots of its source words.

Features:

- `cant_unit_id`
- `cant_unit_ordinal`
- `cantillation_path`
- `cant_terminal_accent`
- `cant_unit_word_count`
- `cant_unit_slot_count`

Edge:

- `cant_terminal` -> closing `cant_word`.

### New node type: `cant_phrase`

Create one node for every internal node of the existing binary tree.

`oslots` = all slots dominated by the node.

Features:

- `cant_phrase_id`
- `cant_cut_accent`
- `cant_phrase_depth`
- `cant_phrase_unit_count`
- `cant_phrase_word_count`
- `cant_first_unit`
- `cant_last_unit`
- `cant_cut_after_unit`

Edges:

- `cant_parent` from each child (`cant_phrase` or `cant_unit`) to the parent;
- `cant_cut_after` from each `cant_phrase` to the preceding `cant_unit` at its split.

### Corpus invariants

The generated graph must satisfy:

```text
number(cant_word) == source_words
number(cant_unit) == units
number(cant_phrase) == units - verses
```

for the current full-binary representation.

Current expected pinned counts are:

```text
cant_word   305,507
cant_unit   165,747
cant_phrase 142,534
```

Tests should derive expectations from generated statistics where possible rather than scattering
magic numbers through the code.

### Round-trip tests

Implement a graph -> JSON-tree reconstruction in tests or a dedicated utility. For every verse,
the reconstructed tree must preserve:

- unit order;
- unit spans;
- internal spans;
- cut accents;
- shape signature;
- branch signature;
- accent signature.

This is the strongest guard against an accidental semantic divergence between the old and new
representations.

## Phase 4 — boundary projection and node-level quantitative metrics

Once `cant_phrase` exists, treat each internal phrase as a boundary event.

### `cant_phrase` metrics

Add:

- first/second child unit counts;
- first/second child word counts;
- `cant_signed_split_words`;
- raw catalogue rank associated with the cut word where available;
- documented derived disjunctive level when implemented;
- documented derived boundary strength when implemented.

### Flat export

Add:

```bash
bhsa-cantillation boundaries ...
```

or a script with equivalent functionality producing TSV and/or JSONL.

Required fields include stable IDs, verse, system, cut accent, span, cut location, word counts,
slot range, alignment status, and source provenance.

The export must be reconstructible from the graph artifact; do not maintain a second manually
computed boundary model.

### Tests

- every `cant_phrase` produces exactly one boundary row;
- row cut position equals `cant_cut_after`;
- row counts agree with node/slot containment;
- sorting is deterministic across rebuilds.

## Phase 5 — BHSA syntax and half-verse comparison

Start with computed span relations. Do not add a large cross-layer edge inventory yet.

### Analysis output

For each cantillation cut record, compute flags such as:

- `ends_phrase`
- `ends_phrase_atom`
- `ends_clause_atom`
- `ends_clause`
- `matches_half_verse_boundary`

For each `cant_phrase`, optionally compute relation classes to selected BHSA object types:

- `exact`
- `contains`
- `inside`
- `crosses`
- `disjoint` only where needed for validation, not as a stored relation.

### Reports

Produce at least:

1. distribution of exact span matches by BHSA object type;
2. boundary coincidence by cantillation rank/level;
3. root split vs BHSA `half_verse` comparison;
4. complete list of crossing cantillation/syntax spans.

Crossing cases should be exported as examples, not hidden inside a summary percentage.

### Materialized edges

Only add an edge such as `cant_exact_match` if repeated real-world queries or performance
benchmarks demonstrate a benefit. Otherwise `oslots` remains the source of truth for
cross-layer containment.

## Phase 6 — implement named poetry profiles

Profiles live outside the canonical source-derived layer.

### Profile interface

Define an interface that returns boundary decisions with explanations:

```python
SegmentDecision(
    verse=...,
    boundary_after_word=...,
    decision=True,
    rule_id=...,
    evidence=...,
    source_pages=...,
)
```

Every rule engine must provide:

- profile name;
- profile version;
- bibliographic source;
- exact rule IDs;
- scope (books/accent system);
- unsupported/ambiguous-case handling.

### 6A — `dehoop2000`

Before coding:

- transcribe the relevant Part I rules and examples;
- distinguish accent category from context-dependent value;
- encode examples as tests;
- document any rule that cannot be operationalized from available data.

Output `poetic_segment` nodes only after the decision trace is stable.

### 6B — `park2013`

Before coding:

- obtain/use the full article, not only its abstract;
- turn each published rule into an identifier and unit test;
- test three-disjunctive monocolon behavior and minor-disjunctive exceptions explicitly;
- document scope across Three-Books vs Twenty-One-Books poetry.

### 6C — `trompelt2023`

Treat this first as an independent structural validator for the Three-Books hierarchy and
continuous dichotomy. Only call it a distinct segmentation profile if the formalized article
actually yields independent segment decisions beyond validating the canonical hierarchy.

### 6D — `notarius2018-diagnostic`

Do not automate semantic/pragmatic labels that are not encoded in the sources.

Implement the computable portion:

- compare a selected poetic segmentation profile with BHSA syntax;
- classify boundaries as aligned / poetic-only / syntactic-only;
- identify crossing structures;
- expose candidate cases for manual analysis.

### Comparison report

Generate a matrix of profile decisions per candidate boundary. Preserve disagreement and list all
verses supporting each disagreement class.

## Phase 7 — optional `prosodic_word`

Only after the canonical graph and boundary analyses are stable:

1. specify exact maqqef grouping rules from the source representation;
2. build `prosodic_word` nodes spanning one or more `cant_word`s;
3. test maqqef edge cases, qere handling, and punctuation;
4. document how this level relates to `cant_unit`.

Do not infer a prosodic-word layer by simply grouping on visual hyphens without testing MorphHB
semantics.

## Phase 8 — external validation

### Waxman

Keep the existing Waxman comparison. Add graph-level assertions that its span/cut results remain
unchanged after the internal representation grows.

### TanakhML

Investigate terms/licensing and obtain a reproducible pinned input before adding it to CI. If
permitted, compare:

- graphematic-word alignment;
- terminal spans;
- internal constituent spans;
- cut locations;
- cut/accent labels after a documented normalization map.

Do not compare serialized trees literally when tokenization/node conventions differ.

## CI and release changes

### CI

Extend the generated-data workflow in stages:

1. existing unit/lint tests;
2. build lightweight `tf/2021` module;
3. run existing generated-data tests;
4. build graph artifact;
5. run graph invariants and round-trip tests;
6. run small deterministic analysis-profile fixtures;
7. optionally create reproducibility reports as CI artifacts.

Avoid committing large regenerated graph data on every implementation PR until artifact size and
review ergonomics are known. Prefer a release artifact or an explicitly versioned generated-data
location once measured.

### Provenance

Graph metadata must record:

- BHSA version and commit;
- MorphHB commit;
- repository commit/build version;
- tree/schema version;
- profile version for interpretive outputs.

## Suggested PR sequence

Keep implementation PRs small enough for independent review:

1. **Raw catalogue metadata + word/main-cut features**
2. **Graph schema classes and fixture round-trip tests**
3. **`cant_word` + `cant_unit` derived dataset**
4. **`cant_phrase` + parent/cut/terminal edges**
5. **Boundary TSV/JSONL export**
6. **BHSA syntax/half-verse comparison reports**
7. **Documented boundary-level/strength model**
8. **de Hoop profile**
9. **Park profile**
10. **Trompelt validator/profile**
11. **Notarius diagnostic**
12. **Optional prosodic-word layer**

Each PR should include tests, documentation, and regenerated reports relevant only to its scope.

## Definition of done for the core graph milestone

The core graph milestone is complete when all of the following hold:

- current `tf/2021` feature-module consumers remain compatible;
- a documented command deterministically builds the richer graph from pinned BHSA + MorphHB;
- all 305,507 pinned source words and 165,747 units are represented as nodes;
- every current internal JSON node has exactly one corresponding `cant_phrase` node;
- the graph round-trips to the current JSON tree for every verse;
- every branch cut is traceable `cant_phrase -> cant_unit -> cant_word -> BHSA slots`;
- overlapping/crossing source alignments are represented structurally rather than only through
  pipe-joined strings in the graph artifact;
- no prose hierarchy is accidentally applied to poetic verses;
- all fuzzy alignments and catalogue fallbacks remain inspectable;
- the generated artifact carries source and schema provenance.

Only after this milestone should profile-specific poetic segment nodes be considered stable
public data.