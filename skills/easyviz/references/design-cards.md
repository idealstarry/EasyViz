# Scenario design cards

These visual examples demonstrate specific color-role, mark-hierarchy and
geometry decisions for Create. Each has input features, a rendered example,
a constructed failure illustration and applicability limits. They are original synthetic or
attributed public-data examples, not a universal manuscript template or proof
of publication quality. Create can learn their mechanisms without a runtime
reference; Reproduce follows the reference the user adopted.
Each current card illustrates one successful treatment and one local failure;
it does not establish a single correct solution for its chart family.

## Choose by the data and reading task

First choose the reading task, organization and visual roles with
[Create design paths](design-space.md). Use cards to investigate a relevant
mechanism, rather than selecting a finished layout before that decision.

Read the [card index](../assets/design-cards/index.json)
and actually open the applicable `good_image` and available `failure_image`.
Resolve asset paths relative to the index directory. Check `applies_when`,
`mechanism`, `avoid` and the visible geometry. Match category/
series count, density, matrix aspect, label length and the supported summary;
matching a biological filename or favorite palette is insufficient.

Saved card exports and their QA are build-time teaching evidence. Their source
pointers describe that rendering workspace. To adapt a card, rerender its
supplied data/spec in the current project and bind fresh local sources before
opening a workbench or recording delivery readiness; old QA cannot approve
the adaptation.

| Card | Transferable mechanism | Applicability limit |
| --- | --- | --- |
| `replicate-neutral-compact` | Neutral single-quantity bars with definite intervals/observations and compact repeated category spacing. | Establish what heights and uncertainty mean; do not invent means, error bars or a composition. |
| `distribution-summary-lane` | Clear summary boundaries and category-associated raw lanes; color may belong to bounded areas. | Preserve values, category identity and all observations; lane separation must help actual crossings. |
| `violin-summary-hierarchy` | Deliberate contrast between density contour, inner summary and raw points. | KDE needs an adopted purpose, bandwidth and normalization; a wider body is not a larger sample. |
| `heatmap-tall-narrow` | Cell proportions follow matrix shape; visible seams and a proportionate numeric guide. | Preserve identifier order, missing states and scientific normalization; short aliases must remain unambiguous. |
| `scatter-small-mark-color` | Distinguishable categorical color on small observations and subordinate guides. | Validate both categories on white at real point size; source regression does not authorize a fit. |

For grouped real comparisons, repeat the adopted series order and compact
within-category spacing, with a clearer gap between categories. Different units
or incomparable outcomes may need separate panels. Sparse data must not be
padded with decorative layers to resemble a more populated paper figure.

Use the card's mechanism only where the input features justify it. Preserve
explicit project/category assignments and user settings. Suggested new-task
dimensions apply only where unspecified; they do not authorize resizing an
accepted panel or shrinking its font. Evaluate physical mark thickness,
category gaps, data-to-guide ratio and labels together on the user's data.
Mechanisms can be used separately: clearer summary boundaries do not require
the card's palette or side lane; readable small scatter colors do not prescribe
one pair of hues. Neutral/open bars are one role treatment, not every bar's rule.

## Adapt and verify

Use [First reviewed delivery](first-draft.md) with eligible actual candidates
or a designed spec/focused/custom implementation. Missing card coverage or a
helper's narrow proposals are reasons to design within the scientific contract,
not to copy the nearest card. A viewed card
cannot approve an unseen adaptation. Open the new exports and record concrete
findings before the first finished delivery.

When a failure repeats, record its input features, visible defect, correction
and applicability boundary. Promote a correction to reusable guidance only
after checking a different category count, label length or density where
relevant. Evaluate on unseen tasks and freeze the first finished output before
human aesthetic feedback; more layers or software passes do not establish
better visual quality.
