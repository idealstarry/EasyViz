# Adopted plotting specification

Track: reproduce, image-data. A fresh independent reader inspected only the official PDF crop and supplied caption facts before this case's implementation was selected. The implementer separately inspected numerical Source Data and was already familiar with the core renderer; no author plotting code was sought, read or executed. Access restrictions were instructions, not an enforced sandbox.

Retain the reference's two-sided scatter geometry, dark blue/red directional classes, grey central cloud, proportional circle sizes, dashed references and separate class/size guides. Preserve all 1,457 supplied rows. Use unchanged `mdd`, `logq`, `prob` and the retained source `color` classification. Display aliases clarify the grey class. The original figure's original physical size, exact font, point mapping, colors and draw order are unknown; the selected 88 × 120 mm canvas, Arial 8 pt, 18 pt² maximum geometric circle fill area, approximate colors and source-order marks are declared choices. They are not recovered journal defaults.

Intentional adaptations:

- Omit the E letter and adjacent pathway tables; export only the quantitative subcomponent. Put attribution, explanations and filtering caveats in a separate caption.
- Source `mdd` numerically equals `md3 − md5`; use the explicit x label C3 − C5 rather than ambiguous reference wording. `logq` is supplied −log10(FDR), not a recalculated test.
- All rows have supplied FDR < 0.01. Grey `Not_sig` rows have |mdd| < 0.2 and are labeled **Small effect** (small absolute median difference), with no P-nonsignificant claim. Add their missing decoding legend.
- Reference positions −0.2, +0.2 and 2 are supplied adopted display positions. The renderer draws them without classifying observations or computing significance. Use complete axes [−6,3] and [0,55].
- Place both legends in the empty upper-right plot region. The categorical guide is outside the tall negative-side cloud; the size guide is above the positive-side maximum. Shorter class labels keep text clear of the vertical references, a visual correction after the first render. This deliberate plot overlap requires actual visual review; machine fit alone is insufficient.
- Use positive size keys 0.25/0.5/1.0. All 37 zero-probability rows retain zero quantitative area and remain in plotting data; do not invent a positive size to make them visible. Their coordinates may be visually unmarked, which the caption states. No zero-size quantitative circle can have visible area.
- Convert true circle fill areas to Matplotlib s consistently for plot and legend; outline stroke is excluded. No new test, aggregation, filtering, imputation or biological analysis.

Implementation: generic `render.py` scatter with optional size/group roles. `plot.py` only locates that runtime and forwards explicit inputs; the worksheet schema, filtering/class rules and thresholds do not become core defaults. Numerical source-to-artist and export checks, plus independent visual review, apply only to the saved candidate hashes.
