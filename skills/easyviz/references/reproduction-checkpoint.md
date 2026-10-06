# Adopt the reference before polishing it

Use this lightweight checkpoint for unfamiliar coordinates, several dependent
layers, or unresolved reference meanings. Ordinary panels may keep their short
adopted specification and direct checks. The default inputs remain a reference
image and the user's real data; paper Source Data and author plotting code are
not required.

## Three decisions that prevent a misleading resemblance

| Decision | Record and act |
| --- | --- |
| Preserve | The useful relationship: shared category order, coordinate scale, aligned tracks, color meaning, repeated/shared decoding or point-to-data-region proportion. |
| Adapt | A relationship changed for the real data or adopted canvas: more categories, longer labels, a different data range or a standalone legend. Never alter source values to recover the paper's visual shape. |
| User change | An explicit requested difference. Keep its scientific meaning and any affected coordinates, guides and companion layers consistent. |

The fresh reading is evidence; adoption is the plotting Agent's decision.
Complete the current packet's `implementation-plan.json`, including the
`adoption_contract`. Each material relationship cites the reader's evidence,
has one of the behaviors above, an explicit adopted value and a reason. Record
actual physical dimensions and text roles; screenshot pixels alone do not
establish millimetres or font points.

Every inferred/unknown reading item remains in `open_items`. State the concrete
question, its affected layers and whether it blocks that layer, delivery, or
neither. A resolved item names supplied evidence or an explicit user decision
and says what was established. A font or margin preference can be explicitly
adopted; an unknown statistical definition cannot be resolved by guessing a
familiar calculation. A source ID and explanation establish traceability, not
that the explanation is scientifically correct.

```sh
python /path/to/easyviz/scripts/reproduction_checkpoint.py --describe-contract
python /path/to/easyviz/scripts/reproduction_checkpoint.py \
  --packet reproduction-adoption --out adoption-check-01.json
```

The tool reads only contained staged files and the adopted plan, checks their
recorded hashes and declarations, and writes a new report if requested. It does
not mutate the scaffold, run plotting code, start an Agent turn or approve a
delivery. Exit `0` means recorded adoption checks passed, including an explicit
partial adoption; inspect the status and remaining questions. Exit `1` means
incomplete/inconsistent adoption, and `2` means malformed or inaccessible input.

| Report | Meaning |
| --- | --- |
| `adoption_complete` | Supported layers and decisions are declared without open items. Rendering, actual artist checks and image review still remain. |
| `partial_adoption` | Supported layers can be rendered while explicit open questions/required omissions remain. `delivery_blocked_by_adoption` states whether those items prevent a finished delivery. |
| `needs_adoption` | A declaration, relationship, source binding or blocking uncertainty is inconsistent/incomplete. Resolve its specific errors before rendering this plan. |

If a visible interval's definition is unavailable, retain the raw point layer,
mark the interval unresolved and ask specifically for SD/SEM/CI meaning and
experimental units. Do not mark a required omitted layer satisfied merely
because its omission was explained. Missing design information may block a
statistical layer without stopping supported raw-data work.

## Geometry preview, then final comparison

Before cosmetic tuning, render the supported adopted geometry using the actual
data: plot boxes and axis segments, shared keys, raw observations, summaries and
guides. Inspect whether the important relationships survived the user's data
range, category count and label length. This intermediate preview belongs to
the same implementation; it does not need a competing template or a synthetic
replacement dataset. Save the baseline if a later adaptation will be compared.

For a broken numeric axis, record every visible segment and omitted interval.
Check raw points and summary endpoints against their union; fail if a source
value or uncertainty endpoint would disappear in the omitted range. Mark the
break clearly and preserve the actual numeric values. A new dataset requiring
different segments needs an explicit adaptation or an unbroken-scale view.

Use [Complex reproduction](complex-reproduction.md) for source-to-artist,
coordinate and guide checks, and [Visual review](visual-review.md) for actual
reference/candidate inspection. Deliver a paired original/output view plus
brief retained, adapted and unresolved relationships. State whether the source
physical scale is measured or unknown. Different datasets cannot be judged by
pixel similarity, and a completed checkpoint is never a visual-review pass.

The [broken-axis literature case](../assets/cases/scwat-broken-axis/README.md)
shows a concrete custom coordinate relationship, real source-value checks and
an attributed original/output comparison. Its dimensions, colors and omitted
numeric interval are case decisions, not defaults for new references.
