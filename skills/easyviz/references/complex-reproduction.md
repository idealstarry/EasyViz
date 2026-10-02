# Complex reference layers and alignment

Read this when a **reproduce** reference combines coordinate systems, aligned
tracks, marginal summaries, multiple encodings or unsupported custom layers.
The reference and user data are sufficient inputs; paper Source Data and author
code are optional evidence, not prerequisites. A simple one-axis panel can keep
its existing settings and checks without adopting the JSON audit below.

## Resolve relationships before selecting a recipe

Turn the image reading into a small dependency graph. A heatmap with an aligned
condition strip and a marginal mean, for example, is not three interchangeable
plots: the strip inherits the heatmap's column order, the marginal inherits its
row IDs, and the mean requires a declared missing-value rule. A categorical
color legend cannot replace the continuous heatmap scale or quantitative area
guide. Preserve these relationships even when user values, names or category
counts differ from the reference.

| Relationship | Decide and verify |
| --- | --- |
| Shared coordinates | Explicit order/domain, scale and units; share the data-to-position mapping as well as the physical plot span. |
| Cross-file IDs | Join on literal keys, preserve `001`, `NA` and similar identifiers; establish uniqueness/cardinality and record unmatched keys before plotting. Row order is not an ID join. |
| Marginals and summaries | Derive from the retained plotting table, with explicit aggregation, observation grain and missingness; preserve full source counts and supplied uncertainty meanings. |
| Encodings and guides | Use one resolved mapping for marks and their matching legend/colorbar. Area means area, with consistent point-squared values; category colors keep literal category keys. |
| Missing/zero/omitted | Establish the user's measurement states; mark missing cells separately from numeric zero and explain the state in the caption or data-reading key. |
| Coordinate spaces | Record data/axes/canvas/mm coordinates for each layer. Reserve annotation and guide space without changing the agreed canvas or shrinking the agreed font. |
| Unsupported layer | Implement a primitive explicitly, or record a supported intentional adaptation/unresolved requirement. A recipe name never authorizes dropping it. |

Preserve every material reader layer in the adoption plan. `implemented` /
`preserve` retains the adopted relationship; `adapted` / `adapt` records a
deliberate change; `omitted` / `omit` states why it is absent; `unresolved` /
`unresolved` leaves the requirement open. Use `required`, `preferred` or
`flexible` priority. A required omitted layer remains incomplete, even with an
explanation. If the user removes a requirement, record that change and revise
its adopted priority instead of claiming the previous requirement is satisfied.

## Optional audit of an adopted layer plan

[audit_reproduction.py](../scripts/audit_reproduction.py) is a standard-library
companion to [reference_packet.py](../scripts/reference_packet.py). Use it when
the layer dependencies or source-to-artist checks justify machine-readable
evidence. It reads a saved packet and the completed version 1 scaffold; it
executes no plotting code and never changes `execution_ready` or the plan.

```sh
python /path/to/easyviz/scripts/audit_reproduction.py --describe-contract
python /path/to/easyviz/scripts/audit_reproduction.py \
  --packet reproduction-adoption \
  --plan reproduction-adoption/implementation-plan.json \
  --out reproduction-adoption/output/audit-01.json
```

The output file must be new. Without `--out`, the report is printed only. Exit
`0` means the recorded checks passed, `1` means incomplete evidence or a failed
check, and `2` means malformed/unreadable input. The report distinguishes
`missing_evidence` from actual `errors`; inspect both before deciding what
remains to do.

Complete the original layer entries with actual `data_artifacts`, mappings,
transform/missingness policy, artist and backend. For this audit, field mappings
use `{artifact, field, unit}` objects; use `category` or `dimensionless` explicitly
where appropriate. A data-bearing reader layer needs staged user data. A
nonnumeric annotation with no required data meanings can use no data artifacts.

```json
{
  "source_layer_id": "points",
  "evidence_ids": ["E1"],
  "status": "implemented",
  "adoption": {"decision": "preserve", "priority": "required", "reason": "Retain all raw observations"},
  "data_artifacts": ["data-1"],
  "field_mapping": {
    "x": {"artifact": "data-1", "field": "time", "unit": "h"},
    "y": {"artifact": "data-1", "field": "signal", "unit": "a.u."}
  },
  "transform": "none; all rows retained; no missing measurements",
  "artist": "scatter collection with gid raw-points",
  "backend": "matplotlib Axes.scatter in data coordinates",
  "verification": [{
    "kind": "numeric",
    "source_artifact": "data-1",
    "source_keys": ["observation_id"],
    "source_fields": ["time", "signal"],
    "target": "output/artist-values.csv",
    "target_sha256": "EXACT_ARTIST_TABLE_SHA256",
    "target_keys": ["observation_id"],
    "target_fields": ["artist_x", "artist_y"],
    "atol": 1e-12
  }]
}
```

Retain the scaffold's other fields and reading descriptions. The illustrative
field names and IDs above are not defaults. Export the verification values from
the actual artists, for example `collection.get_offsets()` or a line's actual
x/y arrays, retaining the source keys. An independent source recalculation
adds stronger evidence than writing the input table again under artist names.

Supported checks are deliberately small:

- `numeric`: identical one-to-one key sets, finite source/target values and a
  declared absolute tolerance; compares the original numeric strings with
  decimal arithmetic, preserving differences above binary-float integer
  precision. No automatic aggregation or filtering. An exponent/precision span
  above 10,000 digits is rejected instead of rounded into a false match.
- `records`: the same key requirements with exact literal field equality.
- `bounds`: a hashed target CSV, `target_keys`, and
  `target_fields: [lower, center, upper]`; checks finite values and interval
  ordering. Combine it with a source-value check for fidelity.
- `svg-presence`: `svg_ids` belonging to the layer binding and present in the
  exported SVG. Useful for a nonnumeric annotation or guide; establishes
  presence only.

Each data artifact used by an active layer needs a source-bound `numeric` or
`records` check; presence and interval ordering alone cannot substitute for data
fidelity. Header-only tables provide no numeric/join evidence and leave the
audit incomplete.

CSV/TSV checks preserve strings and parsed records, with explicit unique keys;
they support UTF-8 files up to 25 MiB and 100,000 records. If an input is XLSX,
stage an explicit CSV with extraction provenance for these checks; the tool
does not guess workbook sheets or reinterpret Excel data. Computed statistics
and transformed quantities require a separate supported calculation check; a
source-to-table comparison alone does not establish their correctness.

Add an `audit` block only after the script and exports exist:

```json
{
  "version": 1,
  "script": {"path": "implementation/panel.py", "sha256": "EXACT_SCRIPT_SHA256"},
  "outputs": [
    {"format": "svg", "path": "output/panel.svg", "sha256": "EXACT_SVG_SHA256"},
    {"format": "pdf", "path": "output/panel.pdf", "sha256": "EXACT_PDF_SHA256"},
    {"format": "png", "path": "output/panel.png", "sha256": "EXACT_PNG_SHA256"}
  ],
  "axes": [
    {"id": "main-x", "dimension": "x", "scale": "linear", "unit": "h", "domain": [0, 6], "plot_box_svg_id": "main-box", "shared_with": ["track-x"]},
    {"id": "track-x", "dimension": "x", "scale": "linear", "unit": "h", "domain": [0, 6], "plot_box_svg_id": "track-box", "shared_with": []}
  ],
  "joins": [],
  "guides": [{"id": "condition-color", "kind": "categorical", "svg_ids": ["condition-legend"], "meaning": "Condition color", "mapping": {"Control": "#2581B9", "Treatment": "#DF9A3C"}}],
  "bindings": [
    {"layer": "points", "svg_ids": ["raw-points"], "axes": ["main-x"], "joins": [], "guides": ["condition-color"]},
    {"layer": "condition-strip", "svg_ids": ["strip-cells"], "axes": ["track-x"], "joins": [], "guides": ["condition-color"]}
  ]
}
```

All evidence file paths are relative to and contained inside the packet.
Bindings cover exactly the implemented/adapted reader layers. The complete
`--describe-contract` output also specifies one-to-one/many-to-one joins,
continuous mappings and linear-area guides; omit relationships that do not
apply. Category domains are ordered literal lists; numeric domains must
increase and logarithmic domains must be positive. `x`/`y` field units must
agree with their bound axes when those mapping roles are present.

For actual shared-axis geometry checks, assign the axes patches stable SVG IDs:

```python
main_ax.patch.set_gid("main-box")
track_ax.patch.set_gid("track-box")
points.set_gid("raw-points")
```

The auditor measures bound, untransformed rectangular SVG patches in final
canvas mm. Shared x compares actual left/width; shared y compares top/height,
with a 0.01 mm tolerance. It also compares actual SVG physical dimensions with
the adopted canvas. Transformed/nonrectangular patches are reported as missing
geometry evidence, as do nested SVG viewports and letterboxed viewBox mappings;
use a dedicated verifier rather than guessing a bounding
box. Matching physical spans are insufficient unless their data domains,
scales, units and category orders also agree.

## What a passed report establishes

`passed-recorded-checks` establishes covered **recorded** layers, matching file
hashes/IDs, executed table checks, declared relationships and supported SVG
alignment. It does not verify that the reader found every visible feature, that
a mapping was scientifically appropriate or used correctly, that a table was
honestly extracted from artists, or that all formats came from the same run.
PDF/PNG bindings check bytes, not dimensions or visual contents. Keep export
measurements and actual image/PDF review alongside the report. Compare custom
layers, guide values, labels, missingness and density at the agreed final size.
Reader independence, statistical validity, semantic correctness and visual
quality remain separate evidence.
