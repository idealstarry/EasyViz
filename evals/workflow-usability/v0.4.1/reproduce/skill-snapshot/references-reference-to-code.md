# From a reference image to new plotting code

Use this workflow in **reproduce** when a reference establishes visual structure,
including a chart family or arrangement not covered by EasyViz's recipes. The
runtime inputs are the supplied reference and the user's real data. The paper
does not need to publish Source Data or author plotting code. Literature Source
Data cases help test numerical fidelity and teach transferable patterns; their
availability is not an entry requirement for a new reproduction.

## 1. Stage inputs without interpreting them

The standard-library [reference_packet.py](../scripts/reference_packet.py) creates
a new directory, copies the explicit inputs byte for byte, records SHA-256
hashes, and prepares an unresolved layer-to-code plan. It does not decode or
describe images, inspect data semantics, infer statistics or certify a review.

```sh
python /path/to/easyviz/scripts/reference_packet.py \
  --reference reference.png \
  --data user-measurements.csv \
  --data group-metadata.xlsx \
  --caption supplied-caption.txt \
  --out reproduction-inputs
```

`--caption` and `--methods` are optional and repeatable. Give `--data` explicit
files selected from the user's directory; a whole directory is not silently
treated as a prepared plotting table. The shared directory inspection with
`inspect_data.py --inventory-only` can inventory files without generating create
recommendations or changing the reproduce track's visual objective.
No author code is searched, copied as a plotting implementation or executed.

| Output | Meaning |
| --- | --- |
| `reader-inputs/` | Reference and optional caption/method excerpts; excludes user tables and implementations. |
| `reader-request.md` | A request restricted to fresh image reading; pass the Reference Reader instructions separately. |
| `reading-template.json` | Exact reference hash and empty evidence/layer lists; no inspection claim. |
| `data/` | Byte-identical snapshots of the explicit user files. |
| `packet.json` | Original paths, staged paths, sizes, hashes, evidence identities and tool limitations. |
| `implementation-plan.json` | An unresolved scaffold, **not** a renderer spec or an adopted plan. |

The separation is an input contract, not a security sandbox. A fresh reader must
receive only the permitted image/text files, the template's structure/hash, and
the Reference Reader instructions. Do not give it the packet directory to
explore freely or fork a context containing previous implementations.

## 2. Read first; adopt decisions second

Follow [Reproduce](reproduce.md) and [Reference specification](reference-spec.md).
The independent reader opens the actual image, identifies the selected panel,
and distinguishes `observed`, `inferred` and `unknown` evidence. The main Agent
inspects the real user data in parallel and owns the adopted decisions.

```sh
python /path/to/easyviz/scripts/reference_packet.py --describe-reading
```

The machine-readable contract uses `state` for the evidence label. For example,
after an actual image reading, an observed point layer and an unknown interval
definition can be represented as follows; substitute the exact supplied image
hash and the actual reader's provenance.

```json
{
  "version": 1,
  "reader": {
    "agent_id": "actual-reader-identity",
    "independence": "independent",
    "image_viewed": true,
    "limitations": []
  },
  "reference": {"sha256": "EXACT_IMAGE_SHA256", "region": "selected panel B"},
  "evidence": [
    {"id": "E1", "property": "layers.points", "description": "Points are visible for each displayed group.", "state": "observed", "source": "reference", "uncertainty": "Point overlap limits visual counting."},
    {"id": "E2", "property": "statistics.interval", "description": "The interval definition is unavailable.", "state": "unknown", "source": null, "uncertainty": "Neither the image nor a supplied excerpt identifies SD, SEM or CI."}
  ],
  "layers": [
    {"id": "points", "evidence_ids": ["E1"], "description": "Raw observation marks", "required_data_meanings": ["group", "measurement", "observation identifier"]},
    {"id": "intervals", "evidence_ids": ["E2"], "description": "Intervals requiring clarification", "required_data_meanings": ["supplied endpoints or a supported uncertainty calculation"]}
  ]
}
```

`source` is `reference`, `caption-1`, `methods-1`, etc. according to the staged
inputs; an unknown item may have a null source. Inferred/unknown evidence needs
a nonempty uncertainty explanation. Evidence IDs are unique and each declared
layer cites existing evidence IDs. Reader independence may be `independent`,
`main-agent`, `not-independent` or `unreported`; record inherited knowledge and
access limitations. Schema validation checks identity and structure, not whether
the interpretation is correct or the reader was actually independent.

To validate that reading and obtain a populated layer scaffold, make a **new**
packet; an accepted packet is never overwritten:

```sh
python /path/to/easyviz/scripts/reference_packet.py \
  --reference reference.png --data user-measurements.csv \
  --caption supplied-caption.txt --reading reading.json \
  --custom-script implementation/panel.py --out reproduction-adoption
```

`--custom-script` declares a planned relative Python file inside the packet. It
does not create or execute code. Omit it while route selection is unresolved.
The tool accepts every declared layer into the scaffold while leaving its data
mapping, transform, artist, backend, verification and adoption decision blank.
Do not treat those blanks as permission to drop a visible layer.

## 3. Search progressively for implementation patterns

Start this step only after the fresh image reading and adoption. Search for the
reference's **layers and visual relationships**, then inspect matching input
contracts. A familiar example filename is not evidence that a whole chart fits.

1. Inspect the supported API with `render.py --describe-spec`. Use the core or a
   focused recipe only if its data meanings, required layers and geometry fit.
2. Search the [chart library](chart-library.md) and [worked cases](examples.md)
   for primitives: supplied intervals, aligned tracks, paired marks, marginal
   summaries, categorical/continuous legends, custom paths or annotations.
3. Read the relevant script's validation, drawing and audit boundaries. Reuse
   only compatible parts; strip case-specific filtering, ordering, statistics
   and labeling assumptions from a new implementation.
4. If an adopted layer or geometry is unsupported, choose `custom-script` and
   implement it explicitly. Extend a recipe only if its existing contract stays
   valid. Do not force the reference into a listed chart family, invent a JSON
   option the renderer does not accept, or substitute a simpler plot.

A reference can combine marks from several families or use an unfamiliar visual
grammar. Decompose it into coordinate systems, data encodings, graphical
primitives, alignment constraints and legends before naming the overall chart.
For aligned tracks, marginal summaries, multi-file joins or several guide roles,
read [Complex reproduction](complex-reproduction.md). Establish the dependency
relationships and literal ID joins before implementing the layers.

## 4. Map each layer to data and code

Complete the scaffold using actual fields, scientific definitions, and the
adopted visual specification. Cover data marks **and** summaries, annotations,
axis structures, guides and legends that are material to the reference.

| Layer plan field | Required decision |
| --- | --- |
| `data_artifacts`, `field_mapping` | Exact input/table IDs, fields, units, keys and observation grain; a decoration may explicitly use no data. |
| `transform` | Saved selection, joins, aggregation, scale transform or derived quantity, with a reason and missingness policy; explicitly state none where appropriate. |
| `artist` | Graphical primitive and stable identifier: scatter collection, line/path, patch, image, text, annotation axis, etc. |
| `backend` | Actual drawing call/module and coordinates: data, axes, canvas or physical units. |
| `verification` | A check of the rendered layer against independently read input values/counts and adopted geometry; include visual inspection where needed. |
| `adoption` | Preserve, adapt, omit intentionally, or unresolved; priority and evidence-based reason. |

Examples: test interval endpoints against supplied low/high values; compare raw
point count and IDs against retained source rows; verify a marginal summary
against its saved summary table; verify color/area legends against the same
mapping as the data artists; measure complete legend bounds after drawing.
For an annotation with no numeric data, check its target, text and adopted
geometry. An unknown statistic remains unresolved until evidence establishes
it, even when its appearance is easy to mimic.

For complex plans, the optional
[audit_reproduction.py](../scripts/audit_reproduction.py) checks every saved
reader layer's adoption, staged fields/hashes, actual SVG bindings, keyed
numerical evidence and shared rectangular SVG plot-box alignment. See
[Complex reproduction](complex-reproduction.md) for the opt-in contract. A
passed report establishes recorded checks only; image semantics, derived
statistics and visual quality still need their own evidence. Ordinary panels
can keep their existing lightweight settings and validation.

## 5. Use common helpers in a new implementation

Custom code can import `render.py` by its actual skill path, call
`setup(spec)` for validated physical layout/typography, and call
`export(fig, output_dir, spec, layout)` for checked PDF/SVG/PNG dimensions.
These helpers do not implement or verify custom scientific layers.

```python
import importlib.util
from pathlib import Path

scripts = Path("/actual/path/to/easyviz/scripts")
loader = importlib.util.spec_from_file_location("easyviz_core", scripts / "render.py")
core = importlib.util.module_from_spec(loader)
loader.loader.exec_module(core)

# Fill from the adopted specification, never from screenshot pixels alone.
spec = {"layout": {"width_mm": 120, "height_mm": 90,
                   "font": "DejaVu Sans", "font_size_pt": 8},
        "formats": ["pdf", "svg", "png"]}
layout, typography, rc = core.setup(spec)
output_dir = Path("output")
output_dir.mkdir(parents=True, exist_ok=True)
with core.plt.rc_context(rc):
    fig = core.plt.figure(figsize=(layout["width_mm"] / 25.4,
                                   layout["height_mm"] / 25.4), dpi=layout["dpi"])
    ax = fig.add_axes([.16, .18, .65, .70])
    ax.set_axisbelow(True)
    # Implement every adopted layer from the user's data, assign stable gids,
    # and run independent source-to-artist and geometry checks before export.
    raise NotImplementedError("Implement and audit the adopted layer plan first")
    exports = core.export(fig, output_dir, spec, layout)
    core.plt.close(fig)
```

The numbers in this scaffold are examples, not required sizes or recovered
reference settings. Reuse `legend_layout.py` to measure complete key/text bounds
and `auto_layout.py` where its single-main-axis contract fits. Integrated axes
need their own alignment/layout checks. Preserve the final canvas and point
sizes; fitting with `bbox_inches="tight"` or shrinking fonts changes the agreed
output. Set explicit mark outline policies, layer order and grid position.

## 6. Review a baseline and record necessary adaptations

First render the adopted baseline using the user's real data. Preserve useful
visual relationships without making new numerical ranges, category counts or
distributions resemble the paper's values. Compare later adaptations at the
same physical size and typography. Record long-label wrapping, legend changes,
unsupported statistical layers and omission of reference prose moved to the
separate caption as intentional differences.

Check the plan's implementation gaps before claiming completion. Save the
custom script/actual recipe, settings, plotting and derived tables, evidence
reading, adopted decisions, hashes, exports, `caption.md` and review evidence.
Delegate independent comparison when available; disclose main-Agent review
when it is not. Packet creation, existing case tests and export-size checks do
not establish faithful reproduction or publication quality for this new case.
