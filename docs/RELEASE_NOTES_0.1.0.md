# v0.1.0 — release notes

The release distributes the Python package (wheel and source archive) together
with source-pinned instructions for regenerating the full BHSA cantillation graph.

## What researchers can use

The pinned ETCBC BHSA 2021 + MorphHB cantillation module supplies the
existing Text-Fabric word and verse features, including reconstructed
binary prosodic trees, accent classifications, source IDs and structural
metrics. The separate full cantillation graph is **generated locally**,
not included as a published derived dataset or as part of the lightweight
`tf/2021` feature module.

The `bhsa-cantillation` command provides:

- `build-graph`: construct a separately verified TF dataset with
  `cant_word`, `cant_unit` and `cant_phrase` nodes, preserving original
  BHSA node/slot IDs, source identity and provenance.
- `boundaries`: export every saved accentual split as JSONL or TSV,
  including source-word coordinates and the BHSA slot projection.
- `compare-halves`: compare the cantillation root split with the
  original BHSA `half_verse` division, including ambiguous/nonbinary cases.
- `compare-syntax`: compare each saved cut endpoint with the last
  occupied slot of original BHSA `phrase`, `phrase_atom`,
  `clause_atom` and `clause` objects.
- `syntax-relations`: classify exact occupied-slot relations of selected
  saved cantillation constituents to original BHSA syntax nodes as
  `exact`, `inside`, `contains`, `crossing` or `disjoint`.
  A `--verse` selection is required to bound this pairwise report.

The README's [researcher quickstart](../README.md#researcher-quickstart-pinned-2021-corpus)
provides the copyable source checkout, install, graph-build and initial
Genesis 1:1 analysis workflow. Use the end-boundary report for a quick
question about a cantillation cut, and `syntax-relations` for exact
constituent comparisons.

## Reproducibility evidence

- Original BHSA: `ETCBC/bhsa@4db00e2157915495e1a4d3d57e41223df24775da`.
- MorphHB: `openscriptures/morphhb@3d15126fb1ef74867fc1434be1942e837932691f`.
- The pinned full graph contains **23,213 verses**, 305,507 source words,
  165,747 accent units and **142,534 saved accentual phrases**.
- A pinned corpus E2E independently compared 6,776 cantillation/original
  BHSA syntax pairs over 31 Genesis 1 verses. A verified crossing occurs
  between `Gen.1.7#p3-6` and original BHSA phrase **651638**, with
  the relation independently reconstructed from original `oslots` and
  re-exported through the selected-verse TSV CLI.
- A separate README smoke test verifies the original BHSA phrase
  **651573** matches a Genesis 1:1 cut, checks a nonmatching cut and
  confirms the cantillation root is aligned with the original `half_verse`.
- Canonical graph invariants, full-verse round-tripping, pinned data
  regeneration, deterministic boundary exports and selected TSV/JSONL
  equivalence are enforced in CI.

## Known limitations and interpretation

- **10 verses** have fuzzy BHSA/MorphHB consonantal alignments. Fuzzy or
  ambiguous original-slot projections are **inconclusive**, not negative
  evidence for syntactic agreement. Some originals span verses and are
  excluded with explicit count denominators.
- There are **308** source-word accent combinations absent from the
  MorphHB catalogue. They remain marked as Unicode fallbacks.
- MorphHB orthographic word positions and BHSA morphological word-slot
  IDs have different coordinate systems. Equal numeric values do not
  imply they are interchangeable.
- Named scholarly colometry profiles such as **de Hoop 2000** and
  **Park 2013** are **not implemented** in v0.1.0.
  Contextual boundary strength/D-level research features and automatic
  interpretive prosodic segmentation are likewise not implemented.
  The outputs are descriptive source-derived comparisons, not ground truth
  for a single poetic colometry.
- The full queryable graph must be built from the two pinned source
  checkouts. The command rejects a nonempty output folder to prevent
  silently reusing stale derived TF files.

## Release verification

The publishing workflow requires a clean non-editable wheel/source install,
the installed console-script help commands, and a successful complete pinned
BHSA corpus integration run before creating the version tag. The source data
and full derived TF graph are not included in the binary wheel. Every released
archive is accompanied by SHA-256 checksums for download verification.
