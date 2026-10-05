# Staged final observation clipping check

This is isolated v0.4.5 development work against the frozen v0.4.4 renderer
`05981e39daf33cf71af6d0d421beb678a18076974f2af59cfd53418d932746a8`.
No production runtime, package, tag or installed plugin is changed here.

## Actual failure and result

The original scatter uses source centers `(0, 0)`, `(0.5, 0.5)`, `(1, 1)`,
locked x/y limits `[0, 1]`, and fixed Matplotlib `s = 100` at 88 × 66 mm.
Its first and last observations are quarter circles. The former QA declared
the actual PNG, PDF and SVG valid. The new check measures the actual displayed
outer path at the final transform: each endpoint extends **1.763889 mm** beyond
both adjacent axes clip edges and therefore invalidates delivery.

Both versions' actual PNG/PDF/SVG files are retained under
[`actual-export-verification/`](actual-export-verification/).
[The five-case evidence](actual-export-verification/evidence.json) verifies
that every before/after image and vector file is **byte identical**, while
confirmed clipping changes QA from `valid_outputs: true` to `false`.
The safe inside control remains valid. Actual source CSV bytes, quantitative
areas, limits, linewidths and adopted physical dimensions remain unchanged.
The original pre-repair evidence remains untouched in
[`../runtime-audit/reproduced/06-numeric-marker-clipping/`](../runtime-audit/reproduced/06-numeric-marker-clipping/).

This check deliberately reports a bad locked layout; it does not repair the
picture by changing numeric limits, shrinking points or removing observations.
The caller must explicitly adopt an appropriate range/layout or divide the panel.

## Checked geometry

- Only registered `point-group` **circular PathCollection observation layers**
  are measured. The core scatter, distribution and dotplot paths are covered.
- Final collection marker transforms and offset transforms are used, including
  logarithmic axes, grouped collections, mapped areas and beeswarm positions.
- The actual closed Bézier path envelope includes half the visible solid edge
  linewidth. Invisible edges add no thickness. Filled and hollow points retain
  their original size semantics.
- Each export is measured at its actual canvas size. PNG/TIFF use the rounded
  raster canvas; PDF/SVG use the adopted physical page. A vector-safe point can
  still fail if its geometric envelope is cut by a slightly smaller raster.
- Artist rectangular clip boxes and the physical figure canvas are checked.
  An artist with `clip_on=False` may extend across the axes boundary, but is
  still checked against the exported page boundary.
- The report preserves the actual axes limits/scales and semantic element ID.
  Each offending observation uses its registered source key or 1-based **data
  record ordinal**, never a fabricated source line number.
- Exactly tangent envelopes are allowed. The tolerance is solely scaled machine
  roundoff; there is no aesthetic clearance ratio or pixel-sized exemption.

Zero-area dots, masked/nonfinite offsets and fully invisible points are counted
explicitly. Noncircular glyphs, custom/nonrectangular clip paths, path effects,
sketching or dashed outlines receive an **advisory/unmeasured** result. Bars,
baseline contacts, summaries, state glyphs and legend handles are outside this
observation contract. Other mark collisions and publication aesthetics still
require inspection.

## Runtime and verification scope

The only candidate production changes are
[`staged-runtime/render.py`](staged-runtime/render.py) and the new captured,
executed and source-bound helper
[`staged-runtime/observation_clipping.py`](staged-runtime/observation_clipping.py).
Other staged runtime files are unchanged frozen dependencies. The asset symlink
is a local test adapter, not a production patch.

Core QA stores the per-format report in `settings.json` and `qa.json`, binds the
helper's actual executed source hash, and refuses valid delivery on confirmed
clipping. Failed exports, exact source bytes and settings remain reviewable.

Focused/custom renderers calling `core.export` receive
`fig._easyviz_observation_clipping`; they must explicitly combine its
`status != "needs_revision"` with their own QA and save the report. Their
individual acceptance logic is outside the current staged file scope. The
existing focused replicate check still independently checks its mark geometry.
The package/installer required-helper lists must include `observation_clipping.py`
when this candidate is integrated; those files have not been changed here.

**Verification:** 14 new substantive tests passed, covering real multi-format
exports, normal/log axes, filled/hollow linewidth, safe controls, mapped scatter
area, dotplot area, numeric endpoints after beeswarm, raster quantization,
figure clipping without axes clipping, tangent vs positive excess, masked/zero/
invisible marks, bar baseline exemption and unsupported custom geometry.
All 46 existing renderer tests also passed against the isolated candidate.

Run from the repository root:

```sh
MPLCONFIGDIR=/private/tmp/easyviz-endpoint-mpl .venv/bin/python -m unittest discover \
  -s evals/development-v0.4.5/endpoint-clipping/staged-tests -p 'test*.py' -v
MPLCONFIGDIR=/private/tmp/easyviz-endpoint-mpl .venv/bin/python \
  evals/development-v0.4.5/endpoint-clipping/verify_endpoint_exports.py fresh-evidence-name
```

The export proof refuses to overwrite an existing evidence directory. Logs and
the frozen-source manifest accompany the artifacts. Automated counts support
the tested geometric contract; they do not establish aesthetic superiority.
