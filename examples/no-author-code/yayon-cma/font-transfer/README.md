# Explicit font and canvas transfer

This separately adopted variant uses **DejaVu Sans, 7.5 pt, 250 × 111 mm**.
Both matrices and the supplied summary share the same 209 mm categorical span
starting at 34 mm. The original 210 × 111 mm Arial specification and its
reviewed outputs are unchanged.

The source-backed case retains all 1,300 heatmap values, 65 supplied cosine
similarities, 65 adjusted interaction P values, ten literal region IDs, the
original gene order, four orange labels and both outlined ranges. The shorter
guide text, “Interaction / P (adjusted)”, preserves its meaning. The unavailable
dendrogram topology and heights remain omitted; the separate caption documents
the data-supported adaptation and source attribution.

Run from the repository root:

```sh
.venv/bin/python examples/no-author-code/yayon-cma/plot.py \
  --runtime skills/easyviz/scripts \
  --spec examples/no-author-code/yayon-cma/font-transfer/spec.json \
  --out examples/no-author-code/yayon-cma/font-transfer/output
```

The first render passed source-to-artist, transformed alignment, guide fit,
text collision, glyph and whole-canvas export checks. The agent and parent
inspected the actual PNG, PDF and SVG; the PDF embeds DejaVu Sans and its oblique
face, and all extracted text spans remain 7.5 pt. See `visual-review.json` for
the reviewed hashes and measurements. This variant is parent-reviewed; the
independent reviews of the original and synthetic transfer remain separate.

Choosing another font or assembly system requires an explicit agent/user
decision about its final font and canvas, followed by rendering and measured
review. A family override on the narrower original canvas remains a reported
fit failure; the renderer does not shrink its typography to hide that failure.
