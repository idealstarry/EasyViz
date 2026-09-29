#!/usr/bin/env python3
"""Bounded transfer/stress evaluation on new synthetic inputs, not a capability proof.

Writes fixtures, renders, a contact sheet, report.json and report.md. --strict exits
nonzero when a defect or unflagged layout gap remains. No author code is an input.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import textwrap
import traceback

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/easyviz/scripts/render.py"
COLORS = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#575757", "#8064A2", "#8C564B"]
SEED = 731904


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def base(chart, fields, width=160, height=110):
    return {"chart": chart, "fields": fields, "layout": {"width_mm": width, "height_mm": height, "font": "Arial", "font_size_pt": 8, "dpi": 160, "margins": {"left": .22, "right": .75, "bottom": .24, "top": .9}}, "typography": {"axis": 8, "tick": 8, "legend": 8, "annotation": 8, "title": 8, "panel": 8}, "palette": "okabe-ito", "colormap": "viridis", "formats": ["pdf", "png"], "seed": SEED}


def scenarios():
    rng = np.random.default_rng(SEED)
    cases = []

    def add(name, frame, spec, expect, purpose, checks=None, variant=None):
        cases.append({"name": name, "frame": frame, "spec": spec, "expected": expect, "purpose": purpose, "checks": checks or {}, "variant": variant})

    # 01: substantially different matrix shape, values, labels and both-axis order.
    matrix = np.clip(rng.normal(0, 1, (24, 18)) + np.sin(np.arange(24)[:, None] / 3) * .8, -3, 3)
    matrix[::4, ::3] = 0
    heat = pd.DataFrame([(f"Pathway {i + 1:02d}", f"S{j + 1:02d}", matrix[i, j]) for i in range(24) for j in range(18)], columns=["feature", "sample", "score"])
    spec = base("heatmap", {"row": "feature", "column": "sample", "value": "score"}, 180, 160)
    spec.update(options={"color_limits": [-3, 3], "color_center": 0}, colormap="RdBu_r", order={"x": [f"S{i:02d}" for i in range(18, 0, -1)], "y": [f"Pathway {i:02d}" for i in range(24, 0, -1)]}, labels={"x": "Sample", "y": "Pathway", "color": "Score"})
    add("01_rectangular_heatmap", heat, spec, "success", "Transfer to a 24 x 18 matrix, signed values, zeros and independently reversed axes.")

    # 02: retain full labels and font while repairing the physical layout explicitly.
    names = [f"Inflammatory response pathway {i + 1:02d}" for i in range(8)]
    long = pd.DataFrame([(n, f"S{j}", float(rng.uniform(0, 1))) for n in names for j in range(6)], columns=["feature", "sample", "score"])
    small = base("heatmap", {"row": "feature", "column": "sample", "value": "score"}, 88, 88)
    small["labels"] = {"color": "Score"}
    add("02_long_labels_small", long, small, "layout_rejection", "Long biological-style labels must not silently clip at 88 mm.", variant="02_long_label_layout")
    repaired = deepcopy(small)
    repaired["layout"].update(width_mm=180, height_mm=105, margins={"left": .44, "right": .78, "bottom": .2, "top": .9})
    add("02_long_labels_repaired", long, repaired, "success", "The same data and 8 pt labels fit a explicitly larger canvas with a wider left margin.", variant="02_long_label_layout")

    # 03/04/05: denominator semantics and missing-vs-zero are stressed separately.
    groups = [f"Lineage {i}" for i in range(1, 8)]
    comp_rows = []
    for j in range(12):
        counts = rng.multinomial(80, np.full(7, 1 / 7)).astype(float)
        counts[j % 7] = 0
        for g, value in zip(groups, counts):
            if value > 0:
                comp_rows.append((f"D{j + 1:02d}", g, value, 100 + j))
    comp = pd.DataFrame(comp_rows, columns=["sample", "category", "value", "total"])
    cs = base("composition", {"sample": "sample", "category": "category", "value": "value", "denominator": "total"}, 170, 105)
    cs.update(colors=dict(zip(groups, COLORS)), options={"normalization": "denominator", "missing_categories": "zero", "percent_axis": True}, order={"category": list(reversed(groups))}, labels={"x": "Donor", "y": "Fraction of full sample"})
    add("03_sparse_denominator_composition", comp, cs, "success", "12 donors x 7 possible categories, declared structural zeros, unequal full-sample denominators; displayed sums remain below 1.")
    missing = deepcopy(cs); missing["options"].pop("missing_categories")
    add("04_unresolved_composition_missingness", comp, missing, "data_rejection", "Identical absent combinations without a structural-zero declaration must be rejected.")
    zero = pd.DataFrame([(f"D{j}", g, 0 if j == 3 else 1 + i) for j in range(5) for i, g in enumerate(groups)], columns=["sample", "category", "value"])
    zs = deepcopy(cs); zs["fields"].pop("denominator"); zs["options"] = {"normalization": "sample_sum"}
    add("05_zero_sum_composition", zero, zs, "data_rejection", "An otherwise complete composition table with one all-zero sample must not produce NaNs or a fabricated denominator.")

    # 06/07: sparse cells and zero areas are retained; all corruptions must stop.
    dots = pd.DataFrame([(f"G{j + 1:02d}", f"Type {i + 1:02d}", 0 if (i + j) % 7 == 0 else rng.uniform(.03, 1), rng.uniform(-2, 2)) for i in range(10) for j in range(16) if (i * 5 + j) % 4 != 0], columns=["gene", "celltype", "fraction", "score"])
    ds = base("dotplot", {"x": "gene", "y": "celltype", "size": "fraction", "color": "score"}, 180, 130)
    ds.update(colormap="RdBu_r", options={"size_max": 1, "max_area_pt2": 65, "color_limits": [-2, 2], "color_center": 0, "size_legend": [.1, .5, 1]}, labels={"color": "Score", "size": "Fraction", "x": "Gene", "y": "Cell type"})
    add("06_sparse_dot_matrix", dots, ds, "success", "16 x 10 coordinate vocabulary with 120 supplied cells, genuine zero areas and signed colors; no imputation.", {"known_limitation": "A missing combination and a supplied zero-size dot are both visually blank. A custom symbol/legend is needed if that distinction is central."})
    for mutation in ("duplicate", "negative_size", "nonfinite_color", "missing_label"):
        bad = dots.copy()
        if mutation == "duplicate": bad = pd.concat([bad, bad.iloc[[0]]], ignore_index=True)
        elif mutation == "negative_size": bad.loc[5, "fraction"] = -.1
        elif mutation == "nonfinite_color": bad.loc[5, "score"] = float("inf")
        else: bad.loc[5, "celltype"] = ""
        add(f"07_dot_corruption_{mutation}", bad, ds, "data_rejection", f"Large dot table with a single {mutation.replace('_', ' ')} corruption must reject the entire run.", variant="07_dot_corruption")

    # 08/09: thousands of points, log coordinates, ranks and statistical units.
    x = np.exp(rng.uniform(-3, 4, 5000)); y = np.exp(.8 * np.log(x) + rng.normal(0, .55, len(x)))
    scatter = pd.DataFrame({"x": x, "y": y, "group": np.take(["Cohort A", "Cohort B", "Cohort C"], np.arange(len(x)) % 3), "unit": [f"U{i:05d}" for i in range(len(x))]})
    ss = base("scatter", {"x": "x", "y": "y", "group": "group", "unit": "unit"}, 175, 115)
    ss.update(colors=dict(zip(["Cohort A", "Cohort B", "Cohort C"], COLORS)), options={"x_scale": "log", "y_scale": "log", "alpha": .3, "point_area_pt2": 3}, statistics={"method": "spearman", "annotate": True}, labels={"x": "Concentration X", "y": "Response Y"})
    add("08_dense_log_scatter", scatter, ss, "success", "5,000 positive observations, three groups, logarithmic axes, unique units and Spearman correlation.")
    logzero = deepcopy(ss); logzero["options"]["x_limits"] = [0, 100]
    add("08_zero_log_bound", scatter, logzero, "data_rejection", "A logarithmic axis cannot accept an explicit zero lower bound, even when every observation is positive.", variant="08_log_scale_bounds")
    repeated = scatter.iloc[:200].copy(); repeated.loc[1, "unit"] = repeated.loc[0, "unit"]
    add("09_repeated_correlation_unit", repeated, ss, "data_rejection", "Correlation must reject duplicated experimental unit IDs even when all coordinates are valid.")

    # 10/11/12: highly unequal group sizes, descriptive singleton, real pairing boundaries.
    counts = [1, 2, 5, 11, 17, 30, 60, 120, 240]
    dg = [f"Population {i + 1:02d}" for i in range(9)]
    dist = pd.DataFrame([(g, float(rng.gamma(2, 1) + i * .25 - 2), f"{i}-{j}") for i, (g, n) in enumerate(zip(dg, counts)) for j in range(n)], columns=["group", "value", "unit"])
    dis = base("distribution", {"group": "group", "value": "value", "unit": "unit"}, 175, 140)
    dis.update(colors=dict(zip(dg, COLORS)), options={"kind": "box", "orientation": "horizontal", "point_area_pt2": 5, "alpha": .55}, labels={"x": "Measurement", "y": "Population"})
    add("10_unbalanced_nine_group_distribution", dist, dis, "success", "Nine explicit colors, group sizes from 1 to 240, skewed values and a descriptive singleton; all observations must remain visible as points.")
    dd = pd.DataFrame([(g, v, uid) for g in ("A", "B") for v, uid in [(1, "u1"), (2, "u2"), (3, "u2"), (5, "u3")]], columns=["group", "value", "unit"])
    bads = base("distribution", {"group": "group", "value": "value", "unit": "unit"})
    bads.update(colors={"A": COLORS[0], "B": COLORS[1]}, statistics={"method": "welch", "groups": ["A", "B"]})
    add("11_within_group_unit_repetition", dd, bads, "data_rejection", "Replicate rows sharing an experimental unit within each group cannot be treated as independent samples.")
    paired = pd.DataFrame([(g, float(i), f"P{i:02d}") for g in ("Before", "After") for i in range(1, 9)], columns=["group", "value", "unit"]).sample(frac=1, random_state=14)
    ps = base("distribution", {"group": "group", "value": "value", "unit": "unit"})
    ps.update(colors={"Before": COLORS[0], "After": COLORS[1]}, statistics={"method": "wilcoxon", "groups": ["Before", "After"]})
    add("12_zero_paired_differences", paired, ps, "data_rejection", "Correctly paired, shuffled observations with all differences zero must produce an explicit undefined-test error.")

    # 13: a deliberately in-canvas collision that clipping-only QA cannot detect.
    dense_labels = pd.DataFrame([(f"Row {i}", f"Group {j:02d}", float(rng.uniform(0, 1))) for i in range(4) for j in range(12)], columns=["row", "column", "value"])
    crowded = base("heatmap", {"row": "row", "column": "column", "value": "value"}, 88, 88)
    crowded["options"] = {"x_rotation": 0}
    add("13_internal_tick_collisions", dense_labels, crowded, "quality_guard", "Horizontal categorical labels fit inside the canvas but overlap each other. Canvas-only QA must not be confused with publication acceptance.")
    uncrowded = deepcopy(crowded)
    uncrowded["layout"].update(width_mm=132)
    uncrowded["options"]["x_rotation"] = 90
    add("13_tick_collisions_repaired", dense_labels, uncrowded, "success", "The same data and 8 pt text after explicit wider canvas and vertical tick-label placement.", variant="13_internal_tick_layout")

    # 14: a valid categorical label must not be reinterpreted as missing data.
    literals = pd.DataFrame([(g, i + shift) for shift, g in enumerate(["NA", "null", "Control"]) for i in [1, 2, 4, 8]], columns=["group", "value"])
    ls = base("distribution", {"group": "group", "value": "value"}, 132, 100)
    ls.update(colors={"NA": COLORS[0], "null": COLORS[1], "Control": COLORS[2]})
    add("14_literal_category_names", literals, ls, "success", "Literal category names NA and null are valid strings, not blank CSV fields.")

    # 15: a genuine method boundary, not invalid source data.
    repeated_design = pd.DataFrame([(f"Visit {t}", float(i + t / 3), f"Subject {i}") for i in range(12) for t in range(3)], columns=["group", "value", "unit"])
    fs = base("distribution", {"group": "group", "value": "value", "unit": "unit"})
    fs.update(colors={f"Visit {i}": COLORS[i] for i in range(3)}, statistics={"method": "friedman", "groups": ["Visit 0", "Visit 1", "Visit 2"]})
    add("15_repeated_three_visit_test", repeated_design, fs, "unsupported", "Valid three-visit repeated-measures data request a Friedman test, which this renderer does not implement.")
    return cases


def tick_collisions(fig):
    """Independent layout audit: adjacent tick-label intersections inside each axis."""
    fig.canvas.draw()
    painter = fig.canvas.get_renderer()
    collisions = []
    for ax_i, ax in enumerate(fig.axes):
        for direction, axis in [("x", ax.xaxis), ("y", ax.yaxis)]:
            low, high = sorted(axis.get_view_interval())
            ticks = [t for t in axis.get_major_ticks() if low - 1e-9 <= t.get_loc() <= high + 1e-9]
            labels = [t.label1 for t in ticks if t.label1.get_visible() and t.label1.get_text()]
            for i, a in enumerate(labels):
                ra = a.get_window_extent(painter)
                for b in labels[i + 1:]:
                    rb = b.get_window_extent(painter)
                    overlap_w, overlap_h = min(ra.x1, rb.x1) - max(ra.x0, rb.x0), min(ra.y1, rb.y1) - max(ra.y0, rb.y0)
                    if overlap_w > 1 and overlap_h > 1:
                        collisions.append({"axes": ax_i, "axis": direction, "labels": [a.get_text(), b.get_text()], "intersection_px": [round(float(overlap_w), 2), round(float(overlap_h), 2)]})
    return collisions


def verify_success(module, case, data_path, output):
    frame, spec = case["frame"], case["spec"]
    checks = {}
    plotted = pd.read_csv(output / "plotting-data.csv", dtype=object, keep_default_na=False)
    checks["all_source_rows_retained"] = len(plotted) == len(frame)
    for column in frame.columns:
        if pd.api.types.is_numeric_dtype(frame[column]):
            checks[f"source_values:{column}"] = bool(np.allclose(pd.to_numeric(plotted[column]), frame[column].to_numpy(float), rtol=1e-12, atol=1e-12))
        else:
            checks[f"source_labels:{column}"] = plotted[column].tolist() == frame[column].astype(str).tolist()
    page = PdfReader(output / "panel.pdf").pages[0]
    checks["pdf_physical_dimensions"] = bool(np.allclose([float(page.mediabox.width) / 72 * 25.4, float(page.mediabox.height) / 72 * 25.4], [spec["layout"]["width_mm"], spec["layout"]["height_mm"]], atol=1e-5))
    settings = json.loads((output / "settings.json").read_text())
    checks["body_fonts_remain_8pt"] = all(settings["typography"][key] == 8 for key in ["axis", "tick", "legend", "annotation"])
    chart = spec["chart"]
    if chart == "composition":
        expected = frame.value / frame.total
        checks["exact_explicit_denominator"] = bool(np.allclose(pd.to_numeric(plotted["_easyviz_plotted_value"]), expected))
        checks["incomplete_totals_not_renormalized"] = bool((pd.to_numeric(plotted["_easyviz_plotted_value"]).groupby(frame["sample"].to_numpy()).sum() < 1).all())
    if chart == "dotplot":
        areas = pd.to_numeric(plotted["_easyviz_area_pt2"])
        checks["areas_linear_in_supplied_fraction"] = bool(np.allclose(areas, frame.fraction * spec["options"]["max_area_pt2"]))
        checks["zero_areas_remain_zero"] = bool(areas[frame.fraction.to_numpy() == 0].eq(0).all())
    if chart == "scatter":
        independent_rho = np.corrcoef(frame.x.rank(method="average"), frame.y.rank(method="average"))[0, 1]
        stat = json.loads((output / "stats.json").read_text())
        checks["spearman_matches_independent_rank_correlation"] = bool(np.isclose(stat["statistic"], independent_rho))
        checks["full_statistical_n"] = stat["n"] == len(frame)
        if stat["pvalue"] == 0:
            checks["zero_p_value_has_display_bound_metadata"] = stat.get("pvalue_display", {}).get("upper_bound") == .001
    prepared = module.prepare(data_path, spec)
    stats = module.statistics(prepared, spec)
    layout, typography, rc = module.setup(spec)
    with module.plt.rc_context(rc):
        fig, _ = module.draw(prepared, spec, layout, typography, stats)
        try:
            collisions = tick_collisions(fig)
            if chart == "heatmap":
                ax = fig.axes[0]
                xorder = spec.get("order", {}).get("x", frame[spec["fields"]["column"]].drop_duplicates().tolist())
                yorder = spec.get("order", {}).get("y", frame[spec["fields"]["row"]].drop_duplicates().tolist())
                checks["rendered_x_order"] = [l.get_text() for l in ax.get_xticklabels()] == xorder
                checks["rendered_y_order"] = [l.get_text() for l in ax.get_yticklabels()] == yorder
            if chart == "scatter":
                checks["all_point_offsets_present"] = sum(len(c.get_offsets()) for c in fig.axes[0].collections) == len(frame)
                checks["requested_log_axes_applied"] = fig.axes[0].get_xscale() == fig.axes[0].get_yscale() == "log"
                if stats["pvalue"] == 0:
                    texts = [t.get_text() for t in fig.findobj(module.Text)]
                    checks["zero_p_value_annotation_is_a_bound"] = any("p < 0.001" in t for t in texts) and not any("p = 0" in t for t in texts)
            if chart == "distribution":
                checks["all_observations_have_point_offsets"] = sum(len(c.get_offsets()) for c in fig.axes[0].collections) == len(frame)
        finally:
            module.plt.close(fig)
    return checks, collisions


def contact_sheet(root, results):
    items = [r for r in results if (root / "renders" / r["name"] / "panel.png").exists()]
    cell_w, cell_h, cols = 600, 490, 3
    sheet = Image.new("RGB", (cell_w * cols, cell_h * int(np.ceil(len(items) / cols))), "#f1f3f5")
    draw = ImageDraw.Draw(sheet)
    from matplotlib import font_manager
    font = ImageFont.truetype(font_manager.findfont("DejaVu Sans"), 18)
    for i, result in enumerate(items):
        x, y = (i % cols) * cell_w, (i // cols) * cell_h
        text = f"{result['name']}\n{result['outcome']}"
        draw.multiline_text((x + 14, y + 9), text, fill="#1c2630", font=font, spacing=4)
        with Image.open(root / "renders" / result["name"] / "panel.png") as im:
            thumb = im.copy(); thumb.thumbnail((cell_w - 20, cell_h - 70))
            sheet.paste(thumb, (x + (cell_w - thumb.width) // 2, y + 67 + (cell_h - 70 - thumb.height) // 2))
    sheet.save(root / "contact-sheet.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "evals/generalization")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    root = args.out; root.mkdir(parents=True, exist_ok=True)
    loaded_hash = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    loader = importlib.util.spec_from_file_location("easyviz_generalization_subject", SCRIPT)
    module = importlib.util.module_from_spec(loader); loader.loader.exec_module(module)
    results = []
    for case in scenarios():
        name = case["name"]
        folder = root / "inputs" / name; folder.mkdir(parents=True, exist_ok=True)
        data_path, spec_path = folder / "data.csv", folder / "spec.json"
        case["frame"].to_csv(data_path, index=False)
        write_json(spec_path, case["spec"])
        metadata = {k: v for k, v in case.items() if k not in ("frame", "spec")}
        metadata.update(synthetic=True, generator_seed=SEED, source_rows=len(case["frame"]))
        write_json(folder / "case.json", metadata)
        output = root / "renders" / name
        record = dict(metadata)
        record["command"] = f".venv/bin/python skills/easyviz/scripts/render.py --data evals/generalization/inputs/{name}/data.csv --spec evals/generalization/inputs/{name}/spec.json --out /private/tmp/easyviz-generalization-{name}"
        try:
            module.render(data_path, case["spec"], output)
            checks, collisions = verify_success(module, case, data_path, output)
            record.update(checks=checks, independent_tick_collisions=collisions)
            if not all(checks.values()): record["outcome"] = "defect"
            elif collisions: record["outcome"] = "layout_gap"
            elif case["expected"] in ("data_rejection", "unsupported", "layout_rejection"): record["outcome"] = "unexpected_acceptance"
            else: record["outcome"] = "success"
        except module.SpecError as exc:
            record["error"] = str(exc)
            qa = json.loads((output / "qa.json").read_text())
            record["qa_status"] = qa.get("status")
            if case["expected"] == "data_rejection": record["outcome"] = "clear_data_rejection"
            elif case["expected"] == "unsupported": record["outcome"] = "clear_unsupported"
            elif case["expected"] in ("layout_rejection", "quality_guard") and qa.get("status") == "needs_revision": record["outcome"] = "clear_layout_rejection"
            else: record["outcome"] = "unexpected_rejection"
        except Exception as exc:
            record.update(outcome="unexpected_exception", error=str(exc), traceback=traceback.format_exc())
        results.append(record)
        print(f"{name}: {record['outcome']}")
    counts = dict(Counter(r["outcome"] for r in results))
    problems = [r["name"] for r in results if r["outcome"] in ("defect", "layout_gap", "unexpected_acceptance", "unexpected_rejection", "unexpected_exception")]
    scope = f"15 bounded synthetic transfer/stress scenarios; {len(results)} concrete runs including layout repair, logarithmic-bound and data-corruption variants. This does not establish general capability or reference-image reproduction."
    report = {"evaluation_completed": True, "release_acceptance_passed": not problems, "scope": scope, "generator_seed": SEED, "renderer_sha256_loaded": loaded_hash, "renderer_sha256_at_finish": hashlib.sha256(SCRIPT.read_bytes()).hexdigest(), "counts": counts, "open_problem_cases": problems, "results": results}
    if (root / "baseline-report.json").exists():
        baseline = {r["name"]: r for r in json.loads((root / "baseline-report.json").read_text())["results"]}
        report["changed_from_baseline"] = [{"case": r["name"], "before": baseline[r["name"]]["outcome"], "after": r["outcome"]} for r in results if r["name"] in baseline and baseline[r["name"]]["outcome"] != r["outcome"]]
    write_json(root / "report.json", report)
    lines = ["# Bounded generalization evaluation", "", report["scope"], "", "All source tables are newly generated synthetic fixtures. Explicit palettes and 8 pt text stabilize this evaluation independently of changing project defaults. No author code or reference image is used.", "", "## Results", "", "| Scenario | Expected | Observed | Evidence |", "| --- | --- | --- | --- |"]
    for r in results:
        evidence = r.get("error", "All numeric checks pass." if all(r.get("checks", {}).values()) else "See numeric check failures.").replace("|", "/")
        if r.get("independent_tick_collisions"): evidence = f"Renderer returned pass; independent audit found {len(r['independent_tick_collisions'])} tick-label intersections."
        lines.append(f"| {r['name']} | {r['expected']} | **{r['outcome']}** | {evidence} |")
    lines += ["", "## Interpretation", "", "Successful transfers only support the tested families, schema, data scale, layout and method combinations. Clear rejection prevents a misleading output but is not a successful plot. Unsupported statistics require an appropriate custom implementation. Layout gaps remain failures of publication acceptance even when the renderer's canvas-boundary QA passes.", "", "The repaired long-label run preserves the original data and 8 pt text; it explicitly enlarges the canvas and left margin. The sparse dot run retains supplied zero sizes without imputing absent combinations, but those two situations both look blank and need a custom visual distinction when scientifically relevant.", "", "## Reproduce", "", "```sh", ".venv/bin/python tests/check_generalization.py", "# Add --strict to fail on any open defect or unflagged layout gap.", "```", "", "Every exact input and specification is under `inputs/`; exact per-case commands and quantitative checks are in `report.json`. Outputs are under `renders/`. `contact-sheet.png` is an inspection aid, not a manuscript figure. Actual visual-review findings are documented separately in `visual-review.md`."]
    (root / "report.md").write_text("\n".join(lines) + "\n")
    contact_sheet(root, results)
    print(json.dumps({"counts": counts, "open_problem_cases": problems, "report": str(root / "report.json")}))
    if args.strict and problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
