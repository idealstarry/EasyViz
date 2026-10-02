# Synthetic annotated-matrix fixtures

These are engineering inputs, not scientific observations. The first fixture
is a 3 × 2 matrix with literal `001`, `NA` and `null` IDs, source rows in a
different order, observed zero/negative values, one explicit unmeasured cell
and one absent coordinate. Metadata rows are deliberately shuffled. Both
marginal axes and both supplied dendrograms are included.

```sh
python skills/easyviz/scripts/annotated_matrix.py \
  --data skills/easyviz/assets/fixtures/annotated-matrix/input.csv \
  --spec skills/easyviz/assets/fixtures/annotated-matrix/spec.json \
  --row-metadata skills/easyviz/assets/fixtures/annotated-matrix/row.csv \
  --column-metadata skills/easyviz/assets/fixtures/annotated-matrix/column.csv \
  --row-linkage skills/easyviz/assets/fixtures/annotated-matrix/row.json \
  --column-linkage skills/easyviz/assets/fixtures/annotated-matrix/column.json \
  --out /tmp/easyviz-annotated-matrix-complex --track create
```

The changed-schema fixture has 5 × 4 cells, renamed fields with spaces,
different literal IDs and order, independently renamed metadata keys,
negative and zero values, both missing states, value annotations, a declared
diverging scale and both mean marginals. No tree is supplied in this fixture.

```sh
python skills/easyviz/scripts/annotated_matrix.py \
  --data skills/easyviz/assets/fixtures/annotated-matrix/changed-schema.csv \
  --spec skills/easyviz/assets/fixtures/annotated-matrix/changed-spec.json \
  --row-metadata skills/easyviz/assets/fixtures/annotated-matrix/changed-rows.csv \
  --column-metadata skills/easyviz/assets/fixtures/annotated-matrix/changed-columns.csv \
  --out /tmp/easyviz-annotated-matrix-changed --track create
```

Both fixtures were rendered and their actual PNGs inspected at the specified
120 × 105 mm and 145 × 115 mm canvases with 8 pt text. Labels, metadata strips,
missing-state hatches, annotations, marginal bars and guides were readable
without clipping. Source-to-artist and transformed alignment checks passed;
the compound guide footprint remains recorded for review. These checks are
limited to the supplied fixtures and do not establish arbitrary-data or
upstream scientific validity.

`tests/test_annotated_matrix.py` separately checks changed-schema ordering and
stable IDs; mutation of actual cell colors, transforms/visibility and main
or track domains; keyed strip and marginal/tree artists; malformed trees;
missing and duplicate inputs; aggregation failure; and truthful failed
fixed-font/fixed-canvas QA.
