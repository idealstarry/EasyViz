# WorkBuddy generalization pilot

The purpose is to test whether EasyViz improves an external local Agent's figure
quality on unfamiliar inputs. Running the script successfully is only one part
of that question. Each pair receives the same source bytes, scientific request,
physical canvas, font and allowed visual-revision budget; one writes its own
code and one uses a frozen EasyViz skill snapshot. Original outputs are retained
without evaluator repairs, followed by source/export auditing and anonymous
visual comparison.

## Completed Deepseek dot task

WorkBuddy 5.6.2 displayed **Deepseek-V4.1-Flash**. This identifies the app's label,
not an independently verified backend model. Both tasks used the same synthetic
24-row 8 × 3 matrix, two measured zeros, and 120 × 90 mm / Arial 8 pt / 300 dpi.

| Finding | Direct code | EasyViz |
| --- | --- | --- |
| Source rows / measured zeros | 24 / 2 retained | 24 / 2 retained |
| Written area/color mapping | Correct proportional areas, source colors | Correct proportional areas, source colors |
| PDF/SVG canvas and text | 120 × 90 mm, embedded Arial 8 pt; editable SVG | Same |
| Clean relocated rerun | Byte-identical PNG pixels | Byte-identical PNG pixels |
| UI duration | 9m3s | 3m30s |
| UI consumption | 14.46 unspecified app units | 6.09 unspecified app units |
| Blind visual result | **Preferred**, conditional on clearer zero-caption wording | Clear decoding, but pale small marks and short zero ticks are weaker |

All 42 independent numeric/export/reuse checks passed. The blind reviewer
preferred the direct-code panel at a nominal final-size screen proxy. EasyViz
reduced displayed effort in this task, but **did not win visual quality**.
Neither result establishes calibrated print quality, journal acceptance or a
general advantage for novice users or other models.

The original direct-code caption ambiguously describes the visible cross as
zero-area. The original EasyViz caption/report confuses Matplotlib's circle-size
parameter with geometric area, overstates physical diameter, and calls its
scale maximum the largest observed point. These are retained as evaluation
findings. The canonical renderer was subsequently corrected to record actual
circle fill area, Matplotlib size parameter and physical diameter separately;
size legends use the same conversion. Original snapshots/results were not
retouched. Guidance now explicitly requires checking tiny/pale marks and zero
glyphs at final proportions.

Read [protocol](protocol.md), [UI observations](ui-observations.json),
[independent numeric audit](independent-numeric-audit.md),
[blind visual review](independent-visual-review.md), and
[artifact hashes](freeze-manifest.json). Anonymous exports are under `blind/`;
A = EasyViz, B = direct code. The reviewer did not receive this identity mapping.

## Limits and further comparisons

This is one task per arm, with detailed matched instructions and a shared
logged-in app session. Input-access restrictions were instructions rather than
an operating-system sandbox. Sampling, backend routing, global memory and hidden
prompts were not controlled. An older English request was briefly accessible to
the baseline before removal; observed early reads were only of the CSV, but
complete hidden-access exclusion cannot be claimed. Displayed consumption is
not a verified currency or token count.

A separate [completed GLM pair](../workbuddy-glm/README.md) uses unseen renamed fields, 11 supplied asymmetric ratio
intervals, seven labels, two batches and three absent combinations. Its skill
snapshot includes later tool fixes, so it must not be used as a model-to-model
comparison with the earlier Deepseek task. Record its completed evidence
separately and compare with/without skill within that same pair. The canonical
figures and generic-script transfer checks are separate from external-model
quality evidence. Its direct-code panel was also preferred visually, while
EasyViz retained the requested canvas more accurately. This finding prompted
separate multiple-guide layout work rather than a repaired model output.
