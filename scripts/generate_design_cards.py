#!/usr/bin/env python3
"""Render original synthetic teaching cards with the public plotting APIs.

Each pair keeps the same inputs, numeric scale, font, marker sizes and canvas.
The intentionally flawed view illustrates a specific design failure; it is not
a performance baseline. Literature-inspired cosmetics do not inherit analysis.
"""

from copy import deepcopy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pymupdf as fitz


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "skills/easyviz/scripts"
OUT = ROOT / "skills/easyviz/assets/design-cards"
SEED = 440
LINE_ROLES = {
    "data": {"line_width_pt": 0.5, "color": "#333333"},
    "summary": {"line_width_pt": 0.7, "color": "#333333"},
    "axis": {"line_width_pt": 0.55, "color": "#222222"},
    "reference": {"line_width_pt": 0.4, "color": "#777777"},
    "grid": {"line_width_pt": 0.3, "color": "#E8E8E8"},
}


def load_renderer(name):
    """Load a repository renderer without requiring package installation."""
    loader = importlib.util.spec_from_file_location(
        "card_" + name, TOOLS / (name + ".py")
    )
    result = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(result)
    return result


def spec(chart, width=66, height=68):
    """Return the shared, explicitly adopted manuscript-panel settings."""
    return {
        "chart": chart,
        "layout": {
            "width_mm": width,
            "height_mm": height,
            "font": "Arial",
            "font_size_pt": 8,
            "dpi": 300,
            "auto_fit": False,
            "margins": {
                "left": 0.21,
                "right": 0.94,
                "bottom": 0.18,
                "top": 0.94,
            },
        },
        "formats": ["svg", "pdf", "png"],
        "line_roles": deepcopy(LINE_ROLES),
        "seed": SEED,
    }


def write_json(path, data):
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    )


def geometry_notes(adopted):
    """Describe declared canvas and mark geometry, rather than measured QA."""
    layout = adopted["layout"]
    margins = layout["margins"]
    width = layout["width_mm"]
    height = layout["height_mm"]
    body_width = width * (margins["right"] - margins["left"])
    body_height = height * (margins["top"] - margins["bottom"])
    canvas_note = (
        f"Adopted canvas: {width:g} × {height:g} mm; declared data region: "
        f"{body_width:.2f} × {body_height:.2f} mm from the fixed margins."
    )
    options = adopted["options"]
    if adopted["chart"] == "replicate":
        body_note = (
            f"Four categorical summaries use bar width {options['bar_width']:g} "
            "category-spacing units, leaving room for intervals and raw marks."
        )
    elif adopted["chart"] == "distribution":
        if options["kind"] == "box":
            body_note = (
                f"Three category centers use box width {options['box_width']:g} "
                "category-spacing units."
            )
        else:
            body_note = (
                f"Three category centers use violin width "
                f"{options['violin_width']:g} and inner-box width "
                f"{options['violin_inner_width']:g} category-spacing units."
            )
        body_note += (
            f" Raw lanes are shifted by {options['point_category_offset']:g} "
            f"category-spacing units, with a maximum packing spread of "
            f"{options['point_max_offset_mm']:g} mm around each shifted anchor."
        )
    elif adopted["chart"] == "heatmap":
        body_note = (
            "The fixed margins allocate a tall, narrow data region to twelve "
            "rows and three columns; automatic cell aspect follows that region. "
            "A vertical colorbar uses the space reserved on the right."
        )
    else:
        body_note = (
            "Two classes share the same coordinate field and mark area; the "
            "upper margin reserves space for the two-key categorical legend."
        )
    return [canvas_note, body_note]


def save(
    card_id,
    rows,
    good,
    failure,
    *,
    applies,
    mechanism,
    failure_reason,
    scientific_definition,
    source_anchors,
    core,
    replicate,
):
    """Write one pair of inputs, exports, captions and inspectable metadata."""
    folder = OUT / card_id
    folder.mkdir(parents=True, exist_ok=True)
    data_path = folder / "data.csv"
    with data_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    records = []
    for name, adopted in [("good", good), ("failure", failure)]:
        spec_path = folder / (name + "-spec.json")
        write_json(spec_path, adopted)
        renderer = replicate if adopted["chart"] == "replicate" else core
        kwargs = {"spec_path": spec_path}
        if renderer is core:
            kwargs["track"] = "create"
        qa = renderer.render(data_path, adopted, folder / name, **kwargs)
        with fitz.open(folder / name / "panel.pdf") as document:
            preview = document[0].get_pixmap(
                matrix=fitz.Matrix(96 / 72, 96 / 72), alpha=False
            )
            preview.save(folder / name / "preview-96dpi.png")
        records.append(
            {
                "variant": name,
                "technical_status": qa["status"],
                "png_sha256": hashlib.sha256(
                    (folder / name / "panel.png").read_bytes()
                ).hexdigest(),
            }
        )

    caption = (
        "Original deterministic synthetic teaching data; not observations from "
        "a biological study. "
        + scientific_definition
        + " Both views retain all observations and the same numeric scale, "
        "font, marker sizes and canvas. The failure view intentionally "
        "demonstrates: "
        + failure_reason
        + " Literature sources motivate visual mechanisms only; no source "
        "test, fit, filtering or biological category is inherited.\n"
    )
    (folder / "caption.md").write_text(caption)
    card = {
        "id": card_id,
        "chart": good["chart"],
        "applies_when": applies,
        "good_image": card_id + "/good/panel.png",
        "failure_image": card_id + "/failure/panel.png",
        "final_size_preview": card_id + "/good/preview-96dpi.png",
        "data": card_id + "/data.csv",
        "good_spec": card_id + "/good-spec.json",
        "failure_spec": card_id + "/failure-spec.json",
        "caption": card_id + "/caption.md",
        "mechanism": mechanism,
        "avoid": failure_reason,
        "source_anchors": source_anchors,
        "synthetic": True,
        "comparisons_are_intentional_teaching_not_effectiveness_evidence": True,
        "rendered": records,
        "geometry_notes": geometry_notes(good),
    }
    write_json(folder / "card.json", card)
    print(card_id, [record["technical_status"] for record in records], flush=True)
    return card


def build_replicate_card():
    # These unit IDs describe synthetic values, not real experiments.
    treatments = [
        ("A", [4.5, 5.2, 5.5]),
        ("B", [8.4, 9.1, 10.2]),
        ("C", [6.0, 6.3, 7.0]),
        ("D", [11.0, 12.4, 11.8]),
    ]
    rows = [
        {"treatment": group, "unit": f"{group}-{j + 1}", "response": float(value)}
        for group, values in treatments
        for j, value in enumerate(values)
    ]
    good = spec("replicate", 60, 62)
    good.update(
        fields={"condition": "treatment", "unit": "unit", "value": "response"},
        labels={"x": "Treatment", "y": "Response (a.u.)"},
        order={"condition": ["A", "B", "C", "D"]},
        options={
            "mode": "summary",
            "uncertainty": "sample_sd",
            "y_limits": [0, 15],
            "y_ticks": [0, 5, 10, 15],
            "bar_style": "outline",
            "bar_width": 0.36,
            "bar_color": "#CACACA",
            "bar_edge_color": "#333333",
            "bar_edge_width_pt": 0.7,
            "point_color": "#333333",
            "marker_area_pt2": 7,
        },
    )
    good.pop("line_roles")
    good.pop("seed")
    failure = deepcopy(good)
    failure["options"].update(
        bar_width=0.82, bar_style="filled", bar_color="#CACACA"
    )
    return {
        "card_id": "replicate-neutral-compact",
        "rows": rows,
        "good": good,
        "failure": failure,
        "applies": [
            "One measured quantity across a few x-labeled treatments",
            "An adopted mean and sample-SD definition with all raw units",
        ],
        "mechanism": (
            "Compact open summaries leave definite intervals and raw observations "
            "visible; x positions decode the single quantity."
        ),
        "failure_reason": (
            "Broad filled summaries dominate the sparse replicate layer; choosing "
            "a bar width is a geometry decision as well as a hue decision."
        ),
        "scientific_definition": (
            "Means and sample SD of three synthetic independent values per "
            "treatment; no hypothesis test."
        ),
        "source_anchors": [
            "PROGENy Fig.2d PDF p4: neutral single-series bars",
            "scWAT Fig.3j PDF p5: bounded open bars and raw marks",
        ],
    }


def build_distribution_cards(rng):
    # Both distribution families share exactly the same numerical input.
    rows = []
    for group, count, mean, sd in [
        ("A", 16, 8, 1.8),
        ("B", 22, 11, 2.3),
        ("C", 28, 9.5, 2.1),
    ]:
        for j, value in enumerate(rng.normal(mean, sd, count)):
            rows.append(
                {"group": group, "unit": f"{group}-{j + 1}", "response": float(value)}
            )

    good = spec("distribution")
    good.update(
        fields={"group": "group", "value": "response", "unit": "unit"},
        order={"group": ["A", "B", "C"]},
        labels={"x": "Group", "y": "Response (a.u.)"},
        colors={"A": "#8787DE", "B": "#BFE8C5", "C": "#FF9695"},
        options={
            "kind": "box",
            "y_limits": [0, 20],
            "point_area_pt2": 9,
            "alpha": 1,
            "point_layout": "beeswarm",
            "point_max_offset_mm": 2.8,
            "point_gap_pt": 0.1,
            "point_category_offset": 0.28,
            "point_color": "#333333",
            "box_style": "filled",
            "box_fill_alpha": 1,
            "box_width": 0.24,
        },
    )
    failure = deepcopy(good)
    failure["options"].update(point_category_offset=0, box_width=0.5)
    box_card = {
        "card_id": "distribution-summary-lane",
        "rows": rows,
        "good": good,
        "failure": failure,
        "applies": [
            "A few categorical distributions with raw observations",
            "The median and interval are central to the reading task",
        ],
        "mechanism": (
            "Adjacent category-associated raw lanes keep box/median/whisker "
            "boundaries uninterrupted; area color and graphite strokes have "
            "different roles."
        ),
        "failure_reason": (
            "Centering the raw layer on the summary creates competing dots, "
            "median and whisker strokes; broad summaries add mass."
        ),
        "scientific_definition": (
            "Linear raw-value quartiles and Tukey 1.5 IQR whiskers, retaining "
            "every point including outliers."
        ),
        "source_anchors": [
            "PROGENy Fig.4c PDF p6: neutral boundaries and colored summary/body areas",
            "Separate raw lanes are an EasyViz adaptation, not a source statistical method",
        ],
    }

    good = deepcopy(good)
    for key in ("box_style", "box_width", "box_fill_alpha"):
        good["options"].pop(key)
    good["options"].update(
        kind="violin",
        violin_width=0.24,
        violin_fill_alpha=0,
        violin_inner="box",
        violin_inner_width=0.16,
        violin_inner_fill_alpha=1,
        point_category_offset=0.28,
        point_max_offset_mm=2.8,
    )
    failure = deepcopy(good)
    failure["line_roles"]["data"] = {"line_width_pt": 1.3}
    failure["options"].update(
        violin_width=0.64,
        violin_fill_alpha=0.32,
        point_category_offset=0,
        point_max_offset_mm=2.8,
    )
    violin_card = {
        "card_id": "violin-summary-hierarchy",
        "rows": rows,
        "good": good,
        "failure": failure,
        "applies": [
            "A distribution-shape question where KDE is scientifically adopted",
            "Inner quartiles must remain distinguishable from estimated density",
        ],
        "mechanism": (
            "A subordinate white KDE body and fine contour frame a stronger "
            "colored quartile area; raw points occupy an associated side lane."
        ),
        "failure_reason": (
            "Equally strong colored density boundary, tinted body and central "
            "raw layer compete with the quartile summary."
        ),
        "scientific_definition": (
            "Gaussian KDE with Scott bandwidth and 100 evaluation points, "
            "trimmed to observed range and independently normalized widths; "
            "quartiles are raw-value summaries, not intervals of confidence."
        ),
        "source_anchors": [
            "PROGENy Fig.4c PDF p6: separate contour, inner summaries and area roles",
        ],
    }
    return [box_card, violin_card]


def build_heatmap_card(rng):
    rows = [
        {
            "feature": f"F{i + 1:02d}",
            "condition": f"C{j + 1}",
            "value": round(float(rng.uniform(0, 100)), 4),
        }
        for i in range(12)
        for j in range(3)
    ]
    good = spec("heatmap", 88, 88)
    good["layout"]["margins"] = {
        "left": 0.3, "right": 0.62, "bottom": 0.16, "top": 0.93
    }
    good.update(
        fields={"row": "feature", "column": "condition", "value": "value"},
        order={"x": ["C1", "C2", "C3"], "y": [f"F{i + 1:02d}" for i in range(12)]},
        labels={"x": "Condition", "y": "Feature", "color": "Value (a.u.)"},
        colormap=["#F6FBFE", "#8CD5F6", "#29ACF3"],
        options={
            "color_limits": [0, 100],
            "cell_aspect": "auto",
            "x_rotation": 0,
            "cell_border_width_pt": 0.35,
            "cell_border_color": "#B7CAD7",
            "annotate_values": True,
            "value_format": ".0f",
        },
        legends={
            "colorbar": {
                "position": "right",
                "orientation": "vertical",
                "length_mm": 32,
                "thickness_mm": 2.2,
                "ticks": [0, 50, 100],
                "gap_mm": 3,
            }
        },
    )
    failure = deepcopy(good)
    failure["layout"]["margins"] = {
        "left": 0.18, "right": 0.8, "bottom": 0.23, "top": 0.89
    }
    failure["options"]["cell_border_width_pt"] = 0
    return {
        "card_id": "heatmap-tall-narrow",
        "rows": rows,
        "good": good,
        "failure": failure,
        "applies": [
            "A matrix with many more rows than columns",
            "Linear magnitude lookup with adopted fixed numeric bounds",
        ],
        "mechanism": (
            "Matrix shape and labels set data-region geometry; visible subordinate "
            "seams separate large cells without changing the scale."
        ),
        "failure_reason": (
            "Stretching a three-column matrix into wide ribbons weakens local "
            "reading; disappearing cell seams make nearby pale values merge."
        ),
        "scientific_definition": (
            "Thirty-six synthetic numeric cells, same linear 0–100 scale and "
            "source order in both views; displayed integer labels do not change "
            "color values."
        ),
        "source_anchors": [
            "scWAT Fig.2b PDF p4: compact narrow matrix",
            "The blue ramp and seams are declared EasyViz adaptations",
        ],
    }


def build_scatter_card(rng):
    rows = []
    for group, count, shift in [("A", 34, 0), ("B", 34, 1.4)]:
        for j in range(count):
            x = float(rng.uniform(0, 10))
            y = float(2 + 0.6 * x + shift + rng.normal(0, 1.5))
            rows.append({"group": group, "unit": f"{group}-{j + 1}", "x": x, "y": y})
    good = spec("scatter", 75, 70)
    good["layout"]["margins"]["top"] = 0.82
    good.update(
        fields={"x": "x", "y": "y", "group": "group"},
        order={"group": ["A", "B"]},
        labels={"x": "Measurement1 (a.u.)", "y": "Measurement2 (a.u.)"},
        colors={"A": "#3795D3", "B": "#FF5FBD"},
        options={
            "point_area_pt2": 12,
            "alpha": 1,
            "x_limits": [0, 10],
            "y_limits": [-5, 15],
        },
        legends={"categorical": {"position": "top", "ncol": 2}},
    )
    failure = deepcopy(good)
    failure["colors"] = {"A": "#BFE8C5", "B": "#E1ECF5"}
    return {
        "card_id": "scatter-small-mark-color",
        "rows": rows,
        "good": good,
        "failure": failure,
        "applies": [
            "Two classes mixed in the same fixed-size point field",
            "Group identity must be decoded from small marks",
        ],
        "mechanism": (
            "Small categorical points need visible whole-panel distinction; pale "
            "bounded-area colors need not work on tiny borderless marks."
        ),
        "failure_reason": (
            "Pale low-contrast colors fail as small marks on white even though "
            "they can be eligible for larger bounded areas."
        ),
        "scientific_definition": (
            "All 68 synthetic paired coordinates, fixed point size, no fit "
            "or hypothesis test."
        ),
        "source_anchors": [
            "scWAT Fig.2g PDF p4: blue/pink fitted-line colors adapted here to raw-class marks",
        ],
    }


def build_card_definitions():
    """Keep one RNG and its draw order stable across all synthetic families."""
    rng = np.random.default_rng(SEED)
    cards = [build_replicate_card()]
    cards.extend(build_distribution_cards(rng))
    cards.append(build_heatmap_card(rng))
    cards.append(build_scatter_card(rng))
    return cards


def main():
    core = load_renderer("render")
    replicate = load_renderer("replicate_plot")
    cards = [
        save(**definition, core=core, replicate=replicate)
        for definition in build_card_definitions()
    ]
    write_json(
        OUT / "index.json",
        {
            "schema_version": 1,
            "track": "create",
            "purpose": (
                "Original synthetic teaching comparisons; inspect images and "
                "applicability before choosing a new-data treatment. These "
                "intentionally flawed comparisons are not a skill-effectiveness "
                "evaluation."
            ),
            "cards": cards,
        },
    )


if __name__ == "__main__":
    main()
