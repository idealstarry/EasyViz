# Create · compartment Ccl2 response

Compare the time response within lung and serum using all 88 real Source Data
observations. Exact-time group means lead, capless SEM defines uncertainty,
and compact open observations retain the individual values. Independent
units have independent axes; control circles and IM-DTR squares provide
color-plus-shape decoding.

![Independent lung and serum panels](output/panel.png)

Each manuscript panel is **82 × 65 mm, Arial 8 pt**. The side-by-side preview
places the two original vector panels without rescaling them. Raw x offsets
are display columns, not sampling times; mean/SEM anchors remain at exactly
0, 12, 24 and 48 hours.

- [Lung SVG](panels/lung/output/panel.svg) · [PDF](panels/lung/output/panel.pdf)
- [Serum SVG](panels/serum/output/panel.svg) · [PDF](panels/serum/output/panel.pdf)
- [Caption and semantic limits](caption.md)
- [Design choices and literature comparison](https://github.com/idealstarry/EasyViz/blob/main/examples/create/compartment-ccl2/design-rationale.md)
- [Source contract](inputs/input-contract.json) · [observations](inputs/observations.csv)
- [Source-to-artist/export validation](https://github.com/idealstarry/EasyViz/blob/main/examples/create/compartment-ccl2/validation.json)

The paper-informed Create organization answers a time-course question using
new geometry. It does not reproduce the published bar layout. The eight
author-adjusted P values are retained separately with their source cells;
correction-family scope is not invented. The source caption and workbook
specify hours, correcting the published panel's days label.

From this copied case directory, redraw into a new folder and independently verify
the exported artists:

```sh
python plot.py --out /tmp/ccl2-redraw
python validate.py --outputs /tmp/ccl2-redraw --out /tmp/ccl2-validation.json
```

With a portable EasyViz skill, pass `--tools /path/to/easyviz/scripts` if the
scripts folder is not an ancestor of this copied case. Arial must be installed
for this adopted manuscript specification; it is resolved explicitly instead
of silently substituting another font. This custom case requires the EasyViz
0.4.5 consumed-byte handoff helper. An explicit `--overwrite` archives earlier
output directories before starting a fresh capture and export.

For an explicit portable redraw on a system without Arial, use an installed
font and verify that same adopted font. Physical dimensions, point size and
source values remain fixed; this does not replace the canonical Arial panels:

```sh
python plot.py --font "DejaVu Sans" --out /tmp/ccl2-portable
python validate.py --font "DejaVu Sans" --outputs /tmp/ccl2-portable --out /tmp/ccl2-portable-validation.json
```

The [checked alternate-font redraw](https://github.com/idealstarry/EasyViz/blob/main/examples/create/compartment-ccl2/portable-forward/DejaVu-Sans-final/validation.json)
records the actual DejaVu Sans font and its adopted specification. The
[final captured forward check](https://github.com/idealstarry/EasyViz/blob/main/examples/create/compartment-ccl2/captured-forward-check.json) confirms that the
current Arial PNG/PDF/SVG bytes match the independently inspected mean-tick
refinement and all consumed sources remain current.

Each individual panel registers real source-bound observations, mean ticks,
SEM, trajectories, guides and legend keys for the local review workbench.
Its `handoff.json` records the exact data, adopted specification and executed
helper bytes captured before plotting; it supports saved edit requests without
pretending the side-by-side preview is one manuscript panel.

The [development record](https://github.com/idealstarry/EasyViz/blob/main/examples/create/compartment-ccl2/delivery-review/development-history.json) preserves
three initial visual passes and one independently prompted mean-visibility
refinement. That fourth followup is not evidence of bounded three-pass first
delivery. Numeric checks and this one reviewed case do not establish general
publication-level aesthetics or Agent efficacy.

Source: [Vanneste et al., *Nature Immunology* 2023](https://doi.org/10.1038/s41590-023-01468-3),
Fig. 3c Source Data, under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The [original crop](inputs/literature-reference.png) is retained with attribution
for design inspection. The task, provenance and [development attempts](https://github.com/idealstarry/EasyViz/blob/main/examples/create/compartment-ccl2/design-history)
make the limits of this one exercise inspectable.

The bundled exports are frozen previews. Redraw this copied case into a fresh writable directory to create current source bindings, QA, selectable elements and a handoff receipt. Development review/history links refer to the original repository records.
