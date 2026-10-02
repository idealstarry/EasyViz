# Independent numerical and export audit

Both frozen WorkBuddy results preserve all 24 supplied rows, both measured zeros, and first-appearance category order. Actual SVG geometry confirms a linear area mapping and the declared color map for every positive marker. This conclusion comes from the written paths and source tables, not either author's self-produced QA.

| Actual artifact check | Baseline | With EasyViz |
|---|---|---|
| Source values, row count and order | 24 retained; 2 zeros | 24 retained; 2 zeros |
| Quantitative markers | 22 circles + 2 separate crosses | 22 positive circles + 2 zero-size circle paths + 2 separate ticks |
| PDF physical page | 119.999997 × 89.999997 mm | 119.999997 × 89.999997 mm |
| Raster export | 1417 × 1062 px; 299.9994 dpi | 1417 × 1063 px; 299.9994 dpi |
| Fonts and editable text | Embedded Arial 8 pt; SVG text nodes | Embedded Arial 8 pt; SVG text nodes |
| Clean rerun from relocated directory | Exit 0; identical PNG pixels | Exit 0; identical PNG pixels |

42 independent checks passed; 0 failed. 207 frozen-file hashes matched the freeze manifest and remained unchanged during the audit.

The one-pixel raster height rounding allowed by the audit does not imply a canvas failure: both vector exports carry the same exact 120 × 90 mm page. Circle areas are compared without the baseline's thin outline; a constant stroke rim does not convert its intended area encoding to a radius encoding.

Two documentation errors remain in the frozen results. The baseline caption assigns zero area to the visible cross itself; only the quantitative circle area is zero. The EasyViz caption calls 165 pt² the largest plotted area, although 165 is its maximum scatter-size parameter at fraction 1 and the largest supplied value is 0.85. Its diameter calculation also assumes s is literal geometric circle area: actual exported diameter is sqrt(s) pt, so the reported diameter is about 12.8% too large. These findings concern descriptions and self-checks; the actual proportional mapping passes in both arms.

The audit confirms local rerun portability with the supplied environment and frozen snapshot, not an installation test on another machine. It does not measure actual backend model identity, credits as money, true isolation, runtime/token equivalence, or general performance. The experiment has one task and one run per arm, and its prompt explicitly supplied the chart, fields, dimensions, font, mapping and statistical limits.

No blind visual review was read before these conclusions. No frozen export was repaired. The baseline's verify_figure.py and the EasyViz QA are author-produced checks; they are treated as claims to compare, not independent certification.

See independent-numeric-audit.json for per-row written-SVG measurements, PDF font evidence, raster metadata, rerun logs and hash checks.
