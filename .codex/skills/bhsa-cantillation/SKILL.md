---
name: bhsa-cantillation
description: Export BHSA cantillation trees to portable JSON or JSONL and render individual prose or poetic verse trees as terminal art. Use for inspecting, sharing, debugging, or presenting trees from the BHSA-cantillation-trees Text-Fabric module.
---

# BHSA cantillation trees

Run the repository's tested scripts rather than parsing `.tf` feature files by hand. Both
the BHSA `tf/2021` directory and this repository's `tf/2021` module are required when
reading directly from Text-Fabric.

## Export

Export the complete corpus as streaming JSON Lines when another program will consume it:

```bash
python scripts/export_trees.py \
  --bhsa /path/to/bhsa/tf/2021 \
  --module tf/2021 \
  --jsonl \
  --output cantillation-trees.jsonl
```

Use a JSON array for a small selection or a user-facing artifact. `--verse` is repeatable
and accepts `Gen.1.1`, `Gen 1:1`, or the BHSA book form `Genesis 1:1`.

```bash
python scripts/export_trees.py \
  --bhsa /path/to/bhsa/tf/2021 \
  --verse Gen.1.1 --verse Ps.117.1 \
  --pretty --output selected-trees.json
```

Each record contains `osis_id`, `bhsa_section`, `system`, `alignment`, `signatures`,
`metrics`, and `tree`. Preserve the reference and provenance fields when handing JSON to
another agent or program.

## Render

Render one record from exported JSON or JSONL:

```bash
python scripts/render_tree.py --input selected-trees.json --verse Gen.1.1
```

Or render directly from Text-Fabric:

```bash
python scripts/render_tree.py \
  --bhsa /path/to/bhsa/tf/2021 \
  --module tf/2021 \
  --verse Ps.117.1 --details
```

The default connectors contain ASCII only. Use `--unicode-lines` when box-drawing
characters are safe in the target. Use `--details` when MorphHB paths and BHSA slot ranges
matter; omit it for documentation and ordinary inspection.

## Interpret the tree

- An internal node has `accent` and exactly two `children`; its accent labels the cut.
- A leaf is an accentual unit, not necessarily one orthographic word. It contains `path`,
  inclusive BHSA `slots`, vocalized `text`, and its final disjunctive `accent`.
- `system` is `prose` or `poetic`. Do not apply the prose accent hierarchy to a poetic
  record.
- `alignment=fuzzy` preserves a documented MorphHB/BHSA consonantal difference. Do not
  silently relabel it as exact.
- `signatures` contains the unlabelled shape, branch-labelled shape, and fully
  accent-labelled shape. `metrics` contains depth, leaf count, mean leaf depth, Colless,
  normalized Colless, Sackin, longest ladder, longest accent run, and depth/leaf ratio.

When changing either script or the schema, run `python -m pytest` and
`python -m ruff check src tests scripts` before reporting success.
