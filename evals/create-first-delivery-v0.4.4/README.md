# Create first-delivery validation and workflow audit — 0.4.4

This evaluation checks a reviewed first delivery, including internal corrections
before human aesthetic feedback. It does not equate an engine's first render
with a finished figure. The candidate engine was frozen before the five probe
inputs were prepared; the [original freeze](input-freeze.json) and
[first outputs](outputs/) remain unchanged. Later workbench/install fixes do
not change that rendering dependency closure. `run.py --verify-frozen-only`
checks the original candidate/renderer/review/palette hashes and input bytes;
`run.py --out /absolute/fresh/directory` replays without replacing the evidence.

## What was actually tried

The probes retain **581 observations/cells** in total: one newly introduced
public Source Data case and four explicitly synthetic stress cases. Two actual
candidates were rendered for each task, with locked dimensions, Arial 8 pt,
numeric scales, marker sizes, source keys and adopted methods. The independent
reviewer opened all ten full PNGs and ten nominal 96 dpi PDF previews.

| Task | Rows | First proposed output | Internal correction |
| --- | ---: | --- | --- |
| Yen relative m6A | 6 | Both technical checks pass; no required visual repair | Candidate 02 selected; no internal repair |
| Six long-label box groups | 153 | Both fail point-spacing QA; raw lanes merge | Separate narrow summary/raw lanes; widen categorical packing space |
| Dense unequal violins | 235 | Both fail point-spacing QA; raw rings cross contours and quartiles | Separate summary/raw lanes with actual contour clearance; preserve Scott KDE |
| Wide annotated matrix | 52 | Both technical checks pass; candidate 02 has clearer padding/seams | Candidate 02 selected; no internal repair |
| Three-class scatter | 135 | Technical checks pass, but image review finds clipped edge circles | Draw complete in-range symbols, retain fixed coordinates/limits, compact the legend |

The original [numerical results](first-render-results.json) and
[independent first review](first-render-visual-review.json) retain these failures.
Three task-specific code corrections in [refine.py](refine.py) are explicitly
**repairs after inspecting those outputs**, rather than new unseen engine
successes. Numerical packing proposals and failed technical attempts are also
retained. Only actual image inspections count as visual passes. The repair
images are in [internal pass 2](internal-pass-02/); independent review and
current-file readiness records accompany them. All original input columns,
values, rows, keys and explicit physical/scientific constraints are checked in
[invariants.json](invariants.json), with only normal numeric CSV round-trip
tolerance. No normalization, statistical test, point-size reduction or
quantitative jitter was added.

The [second independent review](internal-pass-02-visual-review.json) resolves
the three repaired tasks as `ready_with_notes`. All five selected current
outputs have [recorded readiness](delivery-readiness.json), on pass 1 for the
two unchanged choices and pass 2 for the repairs. `complete_reviews.py` only
transcribes the already retained actual review and refuses an image whose hash
differs; it does not open images or produce a new visual judgment. A staged
but incomplete record was correctly blocked before this transcription.

The real-data input comes from Yen et al., *Nature Communications* 16, 4063
(2025), [article and Source Data](https://www.nature.com/articles/s41467-025-59117-2),
under CC BY 4.0. The retained workbook and cell trace identify worksheet
`Fig.1i,j`, B7:B9 and C7:C9. The supplied values are already relative m6A
measurements; this figure compares means, three supplied experimental repeats
and sample SD without re-normalizing or inferring significance/independence.
The remaining four tasks are synthetic and do not add biological evidence.

## Teaching cards

Five original synthetic pairs demonstrate specific mechanisms rather than
claim a Skill effect against weak defaults. All **248 teaching observations**
are byte-identical through the generator refactor; the final preservation
check is [recorded](generator-preservation-final.json). The initial independent
review found raw points crossing the supposedly recommended violin contour.
The first proposed geometric repair then failed packing. Narrowing the KDE
body within the original canvas, while preserving all values, KDE settings,
point area and font, resolved the visible crossings. The original report and
failed attempt remain separate from the
[final independent review](design-card-review-final.json). Ten current card
exports pass technical QA and have complete full/96 dpi image review.

## Process and code review

The audit covers reproduced correctness and boundary failures, their repairs,
and focused negative/positive tests. It is not a blanket security certification.

- [Create/export code audit](code-audit.md): late profile changes, misleading
  post-export success, and export measurements detached from actual PDF/TIFF bytes.
- [Workbench audit](workbench-audit.md) and
  [independent fix review](workbench-fix-review.md): cross-process request loss,
  ordinary two-ledger write failure, acceptance rollback, restored source
  bindings, and stale QA at publication.
- [Installation/package audit](install-package-audit.md) and
  [independent fix review](install-fix-review.md): source/output symlinks,
  same-version cache rollback, concurrent catalog updates, normalized ZIP
  aliases and bounded extraction.
- [Portable documentation audit](portable-resource-audit.md): four real links
  to omitted or relocated resources, corrected at the distribution boundary.
- [Release checks](../release-qa/v0.4.4/README.md): complete regression,
  extracted-package execution and local installed-content verification.

## Limits

This is a small prospective workflow check by local Agents. It measures neither
an external model advantage nor a human correction rate. Initial defaults
still need substantial code/layout repair for the two dense distribution tasks;
the review workflow catches that gap and does not manufacture a first-render
pass. At nominal 96 dpi, the 115-point group is still dense and not quickly
countable, and fixed scatter coordinates naturally overlap. No grayscale or
color-vision validation or journal-acceptance claim follows from these checks.
Three visual passes are a bounded review policy; failure after that budget
must stay explicit.
