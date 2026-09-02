# Comparison with Josh Waxman's cantillation trees

This report compares the generated MorphHB-based Text-Fabric trees with
[`joshwaxman/cantillation`](https://github.com/joshwaxman/cantillation) at commit
`451f1ca91b7627c84023080e1a7baa18c3b31d89`. The machine-readable results are
in [`waxman-comparison.json`](waxman-comparison.json).

## Result

| Test | Result |
| --- | ---: |
| Waxman verses found in MorphHB | 18,694 / 18,694 (100%) |
| Exact consonantal verse text | 18,139 / 18,694 (97.031%) |
| Exact orthographic/maqqef leaf segmentation | 16,397 / 18,694 (87.713%) |
| All module spans present in Waxman, on identical text | 17,989 / 18,139 (99.173%) |
| Exact set of distinct spans, on identical text | 17,935 / 18,139 (98.875%) |
| Individual module spans present in Waxman | 268,351 / 268,685 (99.876%) |
| Binary branch cuts found in Waxman | 124,941 / 125,273 (99.735%) |
| Cut labels agreeing where a cut was found | 124,940 / 124,941 (99.999%) |

The only mapped cut-label disagreement is 2 Chronicles 17:11: MorphHB reads
`Zaqef Gadol`, while Waxman labels the corresponding cut `ZAKEF_KATON`.

## What is, and is not, identical

The two serializations are not directly isomorphic. A leaf in this module is
an entire accentual unit: zero or more conjunctive words ending in a
disjunctive word. A Waxman leaf is normally an orthographic word or a chain
joined by maqqef. Waxman also retains unary wrappers and sometimes emits nodes
with more than two children. Comparing the JSON objects literally would
therefore measure formatting choices rather than prosodic agreement.

For the structural test, both trees are converted to sets of half-open spans
over the normalized consonantal verse text. The module contributes one span
for every accentual-unit leaf and every binary branch. A match means that
Waxman has a constituent covering the same consonantal interval. For a branch
cut, the accent on the Waxman child ending at that cut is compared with the
module's cut accent. Spelling variants such as `Atnach`/`ETNACHTA` and
`Segol`/`SEGOLTA` are normalized; Waxman's two `MUNACH_LEGARMEIH` labels are
both compared with MorphHB's single `Legarmeh` category.

Only the 18,139 verses with identical normalized consonantal text enter the
span and cut comparison. The remaining 555 verses cannot be compared by raw
character offsets without introducing an editorial alignment model. They stay
visible in the JSON report through their edit-distance distribution and sample
references.

## Waxman corpus diagnostics

Waxman's file covers the 36 books using the prose accentuation system. It does
not include Psalms, Proverbs, or Job; the Text-Fabric module has 4,519
additional verses and covers all 39 books, including the poetic system.

The Waxman serialization has 234,286 leaves. Of those, 169 contain no Hebrew
letter. There are 71,207 unary internal nodes and 5,849 internal nodes with
three to seven children. A recurrent tokenizer artifact splits a Hebrew word
at a cantillation mark; for example, one serialized word can become two leaves
such as `האמר` + `י`. These facts explain much of the lower raw leaf-segmentation
agreement and are why the span-level comparison is the primary result.

The Waxman repository contains only `prodosic_trees.txt`, with no generator,
documentation, tests, or declared license at the pinned commit. Its data is
used as an external comparison input and is not copied into this repository.

## Reproduce

Check out the pinned Waxman and MorphHB commits, install this package, and run:

```bash
python scripts/compare_waxman.py \
  --waxman /path/to/cantillation/prodosic_trees.txt \
  --morphhb /path/to/morphhb \
  --json comparison/waxman-comparison.json
```

The script parses Waxman's Python literals with `ast.literal_eval`; it does not
execute the input file.
