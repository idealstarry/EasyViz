# v0.4.4 purpose and geometry overhaul

This folder records the overhaul after the Linux core-check failure,
separately from the frozen first-delivery and choice-space evaluations.
The original publication hold was superseded by the user's subsequent
authorization to complete and release 0.4.4, 0.4.5 and 0.4.6. Current validation
and publication evidence is in [release QA](../release-qa/v0.4.4/README.md).
A successful test or complete review record does not establish aesthetic
improvement or journal acceptance.

## Changes under review

- Data intake distinguishes numeric eligibility from a scientifically useful
  association. It no longer assigns the first two numeric fields to a scatter.
  A confirmed paired-wide design requires verified unit/condition semantics and
  a traceable reshape; it creates neither pairs nor statistical results.
- Create starts with a purpose, actual category/series burden, data-region
  geometry and leading layer. Local literature analogues guide those decisions,
  without imposing a palette, aspect ratio, summary or chart on every input.
  The Skill entry point routes to relevant guidance instead of a long flat
  resource list.
- [Repair-outcome evidence](repair-outcomes/README.md) preserves the previous
  images, a new-size candidate comparison, exact scientific checks and five
  independently reviewed final panels. Its new 72 × 48 mm size was adopted for
  this case; the old 60 × 62 mm size is not a matched-size aesthetic baseline.
- The main README removes the gratuitous scatter preview and compares Shi
  Figure 1d with its matching reconstruction. Scope, source credit and intentional
  changes are stated alongside the comparison.

## Core-check failure

[CI run 37318437850](https://github.com/idealstarry/EasyViz/actions/runs/37318437850)
ran 535 tests and failed the box-summary proportion fixture. Local Arial passed;
Linux's DejaVu Sans fallback consumed slightly more of the default layout margin.
At the retained marker/body floor, one dense group could not satisfy its spacing.
The honest `needs_revision` result conflicted with the fixture's expected success.
[Original CI log](ci-failure.log) preserves the failure; it is not a normal user
step or a released package dependency.

The repair measures the real spread deficit, uses only available omitted
default padding inside the same canvas, and retains at least 1.5 mm canvas
padding. Explicit margins/profile geometry remain authoritative. Actual source,
artist, spacing, summary and export QA remain decisive; the expected assertion
is not relaxed to label a failed layout successful.

[Focused diagnostic](font-layout/diagnosis.md) records 30 passing regression
tests. [Independent code review](code-review.md) reruns 47 intake tests and
seven critical layout/state branches. [Actual image review](font-layout/independent-image-review.md)
checks eight new PNGs: the valid routes remain readable and the explicitly
locked failing layout remains failed. This visual scope includes no PDF.

## Raster review correction

The fresh exercise exposed a separate delivery-check error: a valid Matplotlib
120 × 60 mm PNG at 300 dpi normally uses 1417 × 708 pixels, while the review
expected nearest-integer height 709. The review now accepts supported floor or
nearest raster conversion per axis, checks the actual DPI and any saved PNG
metadata against the current file, and retains vector-canvas and source/QA
checks. TIFF identity remains bound to its measured export record.

[Forward diagnostic](raster-review/owner-forward-diagnostic/diagnostic-summary.json)
records 21 focused passing tests, real four-format exports and untouched trial
files. Correcting the first trial's dimension check leaves its actual point
spacing failure intact. Its passed second attempt and existing review record
remain unchanged. Compatible one-pixel raster boundaries alone cannot prove
the absence of a one-pixel crop; actual content and vector geometry need their
own checks.

## Fresh Source Data exercise

The [predefined task](fresh-task.md) uses 156 already normalized cell counts
from Vanneste et al., Nature Immunology (2023),
[DOI 10.1038/s41590-023-01468-3](https://doi.org/10.1038/s41590-023-01468-3),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The [official workbook](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41590-023-01468-3/MediaObjects/41590_2023_1468_MOESM4_ESM.xlsx)
is preserved in `source-intake/`.

[Extraction](source-intake/extract_figure2h.py) preserves exact numeric strings
and original source cells. [Contract](source-intake/input-contract.json) records
counts, units, already adopted mean ± SEM and unavailable mouse/batch IDs.
No column position becomes a paired mouse, no normalization is recalculated and
no author significance model is reconstructed.

Two fresh local plotting agents receive the same task and inputs, without the
paper figure, previous examples or human aesthetic feedback. One uses ordinary
Python plotting judgment; the other reads the current EasyViz workflow.
Initial renders and any self-corrections remain separate. Both retain the same
120 × 60 mm canvas, Arial 8 pt, all observations and scientific contract.

This is an exploratory execution check on one clearly specified question with
the same model family. It does not quantify Skill efficacy, test beginners or
domestic models, or establish journal-quality generalization. No causal score
is assigned from a pair of images.

The [finished exercise](fresh-run/README.md) preserves both first finished
outputs. Its [independent actual-export review](fresh-run/independent-review.md)
finds clearer mean/SEM separation in the EasyViz result and greater numeric
resolution and shape redundancy in the ordinary workflow. All 156 source
records and 18 summaries match; these local tradeoffs do not establish a general
quality or model-performance advantage.
