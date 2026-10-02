#!/usr/bin/env python3
"""Independent source/XML and actual-export checks for the new plot families.

This evaluator never imports the extraction code or plotting implementation.
The official workbooks are local audit inputs, not bundled plugin assets.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
from statistics import mean, stdev
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
SVG = "{http://www.w3.org/2000/svg}"
CHECKS = []


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check(name, passed, **evidence):
    CHECKS.append({"check": name, "status": "pass" if passed else "fail", **evidence})


def rows(path):
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def worksheet(path, sheet_name):
    """Resolve workbook relationships and retain exact XML numeric lexemes."""
    with zipfile.ZipFile(path) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            for entry in ET.fromstring(archive.read("xl/sharedStrings.xml")):
                strings.append("".join(entry.itertext()))
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        ident = next(sheet.attrib[RID] for sheet in workbook.find("s:sheets", NS) if sheet.attrib["name"] == sheet_name)
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = next(item.attrib["Target"] for item in relationships if item.attrib["Id"] == ident)
        member = target.lstrip("/") if target.startswith("/") else str(PurePosixPath("xl") / target)
        result = {}
        for cell in ET.fromstring(archive.read(member)).findall(".//s:c", NS):
            value = cell.findtext("s:v", default="", namespaces=NS)
            kind = cell.attrib.get("t")
            if kind == "s":
                value = strings[int(value)]
            elif kind == "inlineStr":
                value = "".join(cell.find("s:is", NS).itertext())
            result[cell.attrib["r"]] = {"value": value, "kind": kind, "formula": cell.find("s:f", NS) is not None}
        return result


def audit_urschel(path):
    data_path = ROOT / "evals/reproduce-inputs/urschel-paired/source-data.csv"
    data, cells = rows(data_path), worksheet(path, "figure 2")
    master = worksheet(path, "Urschel et al NatCom all data")
    master_by_id = {cell["value"]: int(coord[1:]) for coord, cell in master.items() if re.fullmatch(r"A\d+", coord) and cell["value"].startswith("NatCom_2024_")}
    expected, statuses = {}, Counter()
    for number in range(4, 131):
        ident, status = cells[f"A{number}"]["value"], cells[f"B{number}"]["value"]
        statuses[status] += 1
        for timepoint, column in (("Before", "C"), ("After", "D")):
            expected[ident, timepoint] = (f"{column}{number}", cells[f"{column}{number}"]["value"], status)
    actual = {(row["participant_id"], row["timepoint"]): row for row in data}
    check("Urschel: all 127 pairs retained exactly once", len(data) == len(actual) == len(expected) == 254 and set(actual) == set(expected), rows=len(data), pairs=len(expected) // 2)
    wrong_values, lexeme_changes, wrong_coordinates, wrong_classifications, master_errors = [], [], [], [], []
    for key, (coord, value, status) in expected.items():
        row = actual[key]
        if Decimal(row["igg_bau_ml"]) != Decimal(value):
            wrong_values.append(key)
        if row["igg_bau_ml"] != value:
            lexeme_changes.append({"unit": key[0], "timepoint": key[1], "xml": value, "csv": row["igg_bau_ml"]})
        if row["source_cell"] != coord or row["source_row"] != coord[1:] or row["source_sheet"] != "figure 2":
            wrong_coordinates.append(key)
        group = "No prior infection" if status == "no" else "Prior infection" if status in ("yes", "yes/NCAP+") else None
        if row["source_infection_status"] != status or row["infection_group"] != group:
            wrong_classifications.append(key)
        number = master_by_id[key[0]]
        col = "AE" if key[1] == "Before" else "AF"
        if Decimal(master[f"{col}{number}"]["value"]) != Decimal(value) or master[f"B{number}"]["value"] != status:
            master_errors.append(key)
    check("Urschel: all raw decimal measurements preserved", not wrong_values, mismatches=wrong_values, literal_lexeme_changes=lexeme_changes)
    check("Urschel: worksheet-cell trace is correct", not wrong_coordinates, mismatches=wrong_coordinates)
    check("Urschel: infection classes including NCAP+ preserved", not wrong_classifications and statuses == Counter({"yes": 60, "no": 63, "yes/NCAP+": 4}), source_classes=dict(statuses), mismatches=wrong_classifications)
    check("Urschel: selected sheet agrees with independent master sheet", not master_errors, audited_measurements=254, mismatches=master_errors)
    check("Urschel: no selected formula, missing or nonpositive measurement", all(not cells[coord]["formula"] and Decimal(value) > 0 for coord, value, _ in expected.values()))
    ecdf_data = ROOT / "examples/create/urschel-ecdf/source-data.csv"
    check("ECDF: real-data adaptation uses same complete source table", ecdf_data.exists() and ecdf_data.read_bytes() == data_path.read_bytes(), input_sha256=digest(data_path))
    paired_data = ROOT / "examples/no-author-code/urschel-paired/source-data.csv"
    if paired_data.exists():
        check("Paired: final case input matches independently traced source table", paired_data.read_bytes() == data_path.read_bytes(), sha256=digest(paired_data))
    return data


def audit_truong(path):
    folder = ROOT / "evals/reproduce-inputs/truong-components"
    cells, data = worksheet(path, "Fig. 1b"), rows(folder / "source-data.csv")
    components, ratios = rows(folder / "components.csv"), rows(folder / "ratios.csv")
    cols = {"HDR": "HIJ", "HDR and mutEJ": "EFG", "mutEJ": "BCD", "ratio": "KLM"}
    expected = {}
    for number in range(2, 9):
        for metric, columns in cols.items():
            for ordinal, column in enumerate(columns, 1):
                expected[number, ordinal, metric] = (f"{column}{number}", cells[f"{column}{number}"]["value"])
    component_lookup = {(int(row["source_row"]), int(row["replicate_ordinal"]), row["component"]): row for row in components}
    ratio_lookup = {(int(row["source_row"]), int(row["replicate_ordinal"]), "ratio"): row for row in ratios}
    long_lookup = {**component_lookup, **ratio_lookup}
    check("Truong: all 84 selected numeric cells retained once", len(components) == len(component_lookup) == 63 and len(ratios) == len(ratio_lookup) == 21 and set(long_lookup) == set(expected), component_rows=len(components), supplied_ratio_rows=len(ratios))
    wrong, coordinates, zeros = [], [], 0
    for key, (coord, value) in expected.items():
        row = long_lookup[key]
        zeros += int(Decimal(value) == 0)
        if row["value"] != value:
            wrong.append({"cell": coord, "xml": value, "csv": row["value"]})
        if row["source_cell"] != coord or row["source_sheet"] != "Fig. 1b" or row["source_label"] != cells[f"A{key[0]}"]["value"]:
            coordinates.append(key)
    check("Truong: exact numeric lexemes and true zeros preserved", not wrong and zeros == 3, source_zeros=zeros, mismatches=wrong)
    check("Truong: all cell coordinates and literal labels traced", not coordinates, mismatches=coordinates)
    wide_lookup = {(int(row["source_row"]), int(row["replicate_ordinal"])): row for row in data}
    wide_errors = []
    for (number, ordinal, metric), (coord, value) in expected.items():
        key = {"HDR": "HDR_percent", "HDR and mutEJ": "both_percent", "mutEJ": "mutEJ_percent", "ratio": "HDR_mutEJ_ratio"}[metric]
        if wide_lookup[number, ordinal][key] != value:
            wide_errors.append(coord)
    check("Truong: wide and both long tables agree with raw source", len(data) == len(wide_lookup) == 21 and not wide_errors, mismatches=wide_errors)
    residuals = []
    for row in data:
        numerator = float(row["HDR_percent"]) + float(row["both_percent"])
        denominator = float(row["mutEJ_percent"]) + float(row["both_percent"])
        residuals.append(abs(numerator / denominator - float(row["HDR_mutEJ_ratio"])))
    check("Truong: supplied ratio semantics include shared component", max(residuals) < 1e-12, maximum_absolute_residual=max(residuals), formula_checked="(HDR-only + shared)/(mutEJ-only + shared)", ratio_values_recomputed=False)
    check("Truong: control ambiguity explicit and ratio states retained", all(row["state"] == ("uninterpretable" if int(row["source_row"]) in (2, 3) else "interpretable") for row in ratios) and cells["A2"]["value"] == cells["A3"]["value"] == "-", note="Control display names resolved by figure/caption; workbook alone has duplicate '-'.")
    check("Truong: complete components for each condition-local unit", len({row["unit"] for row in components}) == 21 and all(len(group) == 3 and {row["component"] for row in group} == set(cols) - {"ratio"} for group in _by(components, "unit").values()), cross_condition_pairing_inferred=False)
    summaries, summary_errors = rows(folder / "source-summary.csv"), []
    for summary in summaries:
        selected = [row for row in data if row["condition"] == summary["condition"]]
        metric = summary["metric"]
        if metric == "total measured components":
            values = [float(r["HDR_percent"]) + float(r["both_percent"]) + float(r["mutEJ_percent"]) for r in selected]
        else:
            field = {"HDR": "HDR_percent", "HDR and mutEJ": "both_percent", "mutEJ": "mutEJ_percent", "supplied HDR/mutEJ ratio": "HDR_mutEJ_ratio"}[metric]
            values = [float(r[field]) for r in selected]
        if summary["n_units"] != "3" or not math.isclose(float(summary["mean"]), mean(values), rel_tol=1e-12, abs_tol=1e-12) or not math.isclose(float(summary["sample_sd"]), stdev(values), rel_tol=1e-12, abs_tol=1e-12):
            summary_errors.append({"condition": summary["condition"], "metric": metric})
    check("Truong: means and sample SD derived from correct quantities", len(summaries) == 35 and not summary_errors, mismatches=summary_errors, sd_ddof=1, total_sd="SD of per-unit sums, not sum of component SDs")
    check("Truong: no formulas in selected numeric cells", all(not cells[coord]["formula"] for coord, _ in expected.values()))
    case_inputs = ROOT / "examples/no-author-code/truong-components/inputs"
    if case_inputs.exists():
        check("Truong: final case inputs match independently traced tables", all((case_inputs / name).read_bytes() == (folder / name).read_bytes() for name in ("source-data.csv", "components.csv", "ratios.csv", "source-summary.csv")), hashes={name: digest(case_inputs / name) for name in ("components.csv", "ratios.csv")})
    return components, ratios


def _by(items, field):
    result = defaultdict(list)
    for row in items:
        result[row[field]].append(row)
    return result


def export_canvas(folder, spec):
    """Measure files independently of their settings and QA claims."""
    from PIL import Image
    import pymupdf
    sizes, texts = {}, []
    width, height = [float(spec["layout"][key]) for key in ("width_mm", "height_mm")]
    font = spec["layout"].get("font_size_pt", 8)
    expected_pixels = [round(width / 25.4 * spec["layout"].get("dpi", 300)), round(height / 25.4 * spec["layout"].get("dpi", 300))]
    with Image.open(folder / "panel.png") as img:
        png_ok = list(img.size) == expected_pixels
        sizes["png_pixels"] = list(img.size)
    with pymupdf.open(folder / "panel.pdf") as pdf:
        page = pdf[0]
        sizes["pdf_mm"] = [page.rect.width * 25.4 / 72, page.rect.height * 25.4 / 72]
        spans = [span for block in page.get_text("dict")["blocks"] if "lines" in block for line in block["lines"] for span in line["spans"] if span["text"].strip()]
        log_display = any(spec.get("options", {}).get(key) == "log" for key in ("x_scale", "y_scale"))
        font_ok = all(math.isclose(span["size"], font, abs_tol=1e-4) or (log_display and math.isclose(span["size"], font * .7, abs_tol=1e-4) and re.fullmatch(r"[−-]?\d+", span["text"])) for span in spans)
        sizes["pdf_font_sizes"] = sorted(set(round(s["size"], 4) for s in spans))
        sizes["pdf_fonts"] = sorted(set(s["font"] for s in spans))
        texts = [s["text"] for s in spans]
    svg_root = ET.parse(folder / "panel.svg").getroot()
    sizes["svg_mm"] = [float(svg_root.attrib[key][:-2]) * 25.4 / 72 for key in ("width", "height")]
    check(f"{folder.parent.name}/{folder.name}: actual fixed canvas", png_ok and all(abs(actual - expected) < .001 for target in ("pdf_mm", "svg_mm") for actual, expected in zip(sizes[target], (width, height))), **sizes)
    check(f"{folder.parent.name}/{folder.name}: actual PDF text size", bool(texts) and font_ok, requested_font_size_pt=font, mathematical_superscript_size_pt=font * .7 if log_display else None)
    return svg_root


def path_points(path):
    """The authored data paths use absolute M/L commands; reject ambiguity."""
    text = path.attrib["d"]
    if re.sub(r"[MLZz0-9eE+.\-\s,]", "", text):
        raise ValueError("Expected a polygon or unsimplified empirical M/L path")
    numbers = [float(v) for v in re.findall(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text)]
    if len(numbers) % 2:
        raise ValueError("Unpaired SVG path coordinate")
    return list(zip(numbers[::2], numbers[1::2]))


def near_points(actual, expected, tolerance=.002):
    return len(actual) == len(expected) and all(abs(a - e) <= tolerance for point, wanted in zip(actual, expected) for a, e in zip(point, wanted))


def plot_box(svg):
    clips = list(svg.iter(SVG + "clipPath"))
    if len(clips) != 1:
        raise ValueError("Expected one Cartesian data clipping rectangle")
    return {key: float(value) for key, value in list(clips[0])[0].attrib.items()}


def svg_transform(box, x_limits, y_limits, *, x_log=False, y_log=False):
    def normal(value, limits, logarithmic):
        low, high = limits
        return (math.log(value / low) / math.log(high / low)) if logarithmic else (value - low) / (high - low)
    return lambda x, y: (box["x"] + box["width"] * normal(x, x_limits, x_log), box["y"] + box["height"] * (1 - normal(y, y_limits, y_log)))


def pdf_drawings(folder):
    import pymupdf
    with pymupdf.open(folder / "panel.pdf") as document:
        return document[0].get_drawings()


def rgb(hex_color):
    return tuple(int(hex_color.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))


def same_color(a, b):
    # MuPDF's color conversion can differ from PDF DeviceRGB by about 5e-5.
    # SVG color tokens are checked literally elsewhere.
    return a is not None and len(a) == 3 and all(abs(x - y) < 1e-4 for x, y in zip(a, b))


def audit_ecdf(folder, data_path, spec_path):
    spec, data = json.loads(spec_path.read_text()), rows(data_path)
    svg = export_canvas(folder, spec)
    box = plot_box(svg)
    xy = svg_transform(box, spec["options"]["x_limits"], [-.02, 1.02], x_log=spec["options"].get("x_scale") == "log")
    curves, coordinates, pdf_coordinates, fractions = [], [], [], []
    for group in spec["order"]["group"]:
        observed = [float(row[spec["fields"]["value"]]) for row in data if row[spec["fields"]["group"]] == group]
        freq, count = Counter(observed), 0
        domain = [(spec["options"]["x_limits"][0], 0.)]
        for value in sorted(freq):
            domain.append((value, count / len(observed)))
            count += freq[value]
            domain.append((value, count / len(observed)))
        domain.extend([(spec["options"]["x_limits"][1], 1.), (spec["options"]["x_limits"][1], 1.)])
        expected = [xy(x, y) for x, y in domain]
        color = spec["colors"][group].lower()
        paths = [path for path in svg.iter(SVG + "path") if path.get("clip-path") and f"stroke: {color}" in path.get("style", "")]
        curves.append(len(paths) == 1)
        if len(paths) == 1:
            actual = path_points(paths[0])
            # SVG may omit an identical final endpoint without changing the path.
            if len(actual) == len(expected) - 1 and expected[-1] == expected[-2]:
                expected.pop()
            coordinates.append(near_points(actual, expected))
        candidates = [d for d in pdf_drawings(folder) if same_color(d.get("color"), rgb(color)) and d["rect"].y0 < box["y"] + box["height"] and d["rect"].y1 >= box["y"]]
        if len(candidates) == 1:
            drawing = candidates[0]
            vertices = [(drawing["items"][0][1].x, drawing["items"][0][1].y)] + [(item[2].x, item[2].y) for item in drawing["items"] if item[0] == "l"]
            # PDF can omit exact duplicated vertices; discard adjacent repeats
            # from both paths before comparing their visible segments.
            clean = lambda points: [p for i, p in enumerate(points) if i == 0 or not near_points([p], [points[i - 1]], 1e-6)]
            pdf_coordinates.append(near_points(clean(vertices), clean(expected)))
        else:
            pdf_coordinates.append(False)
        fractions.append({"group": group, "observations": len(observed), "distinct_values": len(freq), "maximum_tie": max(freq.values())})
    name = f"{folder.parent.name}/{folder.name}"
    check(f"{name}: SVG exact right-continuous empirical jumps", all(curves) and all(coordinates), source_counts=fractions, smoothing_applied=False)
    check(f"{name}: PDF exact empirical curve segments", all(pdf_coordinates), numerical_tolerance_pt=.002)


def audit_replicate(folder, data_path, spec_path):
    spec, data = json.loads(spec_path.read_text()), rows(data_path)
    svg = export_canvas(folder, spec)
    f, opts = spec["fields"], spec["options"]
    conditions, components = spec["order"]["condition"], spec.get("order", {}).get("component", [])
    box, width = plot_box(svg), opts["bar_width"]
    xy = svg_transform(box, [-.55, len(conditions) - .45], opts["y_limits"])
    mode = opts["mode"]
    step_width = width / len(components) if mode == "grouped" else width
    bars, intervals, observations = [], [], []
    for i, condition in enumerate(conditions):
        selected = [row for row in data if row[f["condition"]] == condition]
        units, base = sorted({row[f["unit"]] for row in selected}), 0.
        for j, component in enumerate(components or [None]):
            values = [float(row[f["value"]]) for row in selected if component is None or row[f["component"]] == component]
            center = i + (-width / 2 + step_width * (j + .5) if mode == "grouped" else 0)
            bottom = base if mode == "stacked" else 0.
            bars.append({"vertices": [xy(center - step_width / 2, bottom), xy(center + step_width / 2, bottom), xy(center + step_width / 2, bottom + mean(values)), xy(center - step_width / 2, bottom + mean(values))], "color": spec.get("colors", {}).get(component or condition, opts.get("bar_color", "#C5C5C5")), "state": selected[0].get(f.get("state"))})
            base += mean(values)
            if mode != "stacked":
                intervals.append([xy(center, mean(values) - stdev(values)), xy(center, mean(values) + stdev(values))])
        for j, unit in enumerate(units):
            shift = -step_width * .25 + step_width * .5 * j / (len(units) - 1) if len(units) > 1 else 0.
            raw = [row for row in selected if row[f["unit"]] == unit]
            if mode == "stacked":
                observations.append(xy(i + shift, sum(float(row[f["value"]]) for row in raw)))
            else:
                for component in components or [None]:
                    raw_value = next(float(row[f["value"]]) for row in raw if component is None or row[f["component"]] == component)
                    offset = -width / 2 + step_width * (components.index(component) + .5) if mode == "grouped" else 0.
                    observations.append(xy(i + offset + shift, raw_value))
        if mode == "stacked":
            totals = [sum(float(row[f["value"]]) for row in selected if row[f["unit"]] == unit) for unit in units]
            intervals.append([xy(i, mean(totals) - stdev(totals)), xy(i, mean(totals) + stdev(totals))])
    groups = {node.get("id"): node for node in svg.iter(SVG + "g")}
    bar_errors, interval_errors, point_errors, color_errors, hatch_errors = [], [], [], [], []
    for index, expected in enumerate(bars, 1):
        node = groups[f"easyviz-bar-{index}"]
        path = next(node.iter(SVG + "path"))
        if not near_points(path_points(path), expected["vertices"]):
            bar_errors.append(index)
        style = path.get("style", "")
        state = expected["state"]
        if state is None or not opts.get("state_hatches", {}).get(state):
            if f"fill: {expected['color'].lower()}" not in style:
                color_errors.append(index)
        else:
            if "fill: url(" not in style:
                hatch_errors.append(index)
    for index, expected in enumerate(intervals, 1):
        path = next(groups[f"easyviz-sd-{index}"].iter(SVG + "path"))
        if not near_points(path_points(path), expected):
            interval_errors.append(index)
    actual_points, marker_errors = [], []
    for index in range(1, len(observations) + 1):
        node = groups[f"easyviz-observation-{index}"]
        use = next(node.iter(SVG + "use"), None)
        if use is not None:
            actual_points.append((float(use.get("x")), float(use.get("y"))))
        else:
            path = next(node.iter(SVG + "path"))
            numbers = [float(v) for v in re.findall(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", path.get("d"))]
            xs, ys = numbers[::2], numbers[1::2]
            actual_points.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
            radius = math.sqrt(opts.get("marker_area_pt2", 7) / math.pi)
            if abs(max(xs) - min(xs) - radius * 2) > .000003 or abs(max(ys) - min(ys) - radius * 2) > .000003 or "stroke:" in path.get("style", ""):
                marker_errors.append(index)
    if not near_points(sorted(actual_points), sorted(observations)):
        point_errors.append("actual exported point multiset differs")
    name = f"{folder.parent.name}/{folder.name}"
    check(f"{name}: SVG bars are exact unnormalized supplied-value means", not bar_errors, bars=len(bars), mismatches=bar_errors)
    check(f"{name}: SVG intervals use correct sample SD endpoints", not interval_errors, intervals=len(intervals), mismatches=interval_errors, quantity="per-unit total" if mode == "stacked" else "supplied values")
    check(f"{name}: SVG raw-point positions match every source unit", not point_errors, points=len(observations), mismatches=point_errors)
    check(f"{name}: actual SVG circle size and borderless policy", not marker_errors, geometric_fill_area_pt2=opts.get("marker_area_pt2", 7), mismatches=marker_errors)
    check(f"{name}: SVG component colors and declared control hatches", not color_errors and not hatch_errors, color_mismatches=color_errors, hatch_mismatches=hatch_errors)
    drawings = pdf_drawings(folder)
    pdf_point_centers = [(float(d["rect"].x0 + d["rect"].x1) / 2, float(d["rect"].y0 + d["rect"].y1) / 2) for d in drawings if same_color(d.get("fill"), rgb(opts.get("point_color", "#333333"))) and any(item[0] == "c" for item in d["items"])]
    check(f"{name}: PDF raw-point centers independently match SVG/source", near_points(sorted(pdf_point_centers), sorted(observations)), audited_points=len(pdf_point_centers), numerical_tolerance_pt=.002)
    pdf_intervals = [[(item[1].x, item[1].y), (item[2].x, item[2].y)] for drawing in drawings if same_color(drawing.get("color"), rgb("#444444")) for item in drawing["items"] if item[0] == "l"]
    check(f"{name}: actual PDF sample SD endpoints", len(pdf_intervals) == len(intervals) and all(near_points(actual, expected) for actual, expected in zip(pdf_intervals, intervals)), audited_intervals=len(pdf_intervals), numerical_tolerance_pt=.002)


def raw_quantile(values, fraction, method):
    """Order-statistic interpolation; no NumPy or renderer summary used."""
    values = sorted(values)
    position = (len(values) - 1) * fraction if method == "linear" else (len(values) + 1) * fraction - 1
    position = min(len(values) - 1, max(0., position))
    lower, upper = math.floor(position), math.ceil(position)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def audit_paired(folder, data_path, spec_path):
    spec, data = json.loads(spec_path.read_text()), rows(data_path)
    svg = export_canvas(folder, spec)
    f, opts, box = spec["fields"], spec["options"], plot_box(svg)
    conditions = spec["order"]["condition"]
    blocks = spec.get("order", {}).get("block", ["Observations"])
    centers = {(block, condition): i * (len(conditions) + opts.get("block_gap", .4)) + j for i, block in enumerate(blocks) for j, condition in enumerate(conditions)}
    xy = svg_transform(box, [-.65, max(centers.values()) + .65], opts["y_limits"], y_log=opts.get("y_scale") == "log")
    colors = spec.get("colors", {"Observations": opts.get("point_color", "#0072B2")})
    point_groups = [node for node in svg.iter(SVG + "g") if node.get("id", "").startswith("PathCollection_")]
    point_errors, point_counts, summary_expected = [], [], []
    pdf_points = [d for d in pdf_drawings(folder) if any(item[0] == "c" for item in d["items"]) and d["rect"].y0 >= box["y"] - .01 and d["rect"].y1 <= box["y"] + box["height"] + .01]
    for (block, condition), center in centers.items():
        selected = [r for r in data if (r[f["block"]] if "block" in f else "Observations") == block and r[f["condition"]] == condition]
        values = [float(r[f["value"]]) for r in selected]
        cx = xy(center, values[0])[0]
        tolerance_x = abs(xy(center + opts.get("point_spread", .7) / 2, values[0])[0] - cx) + .002
        actual = []
        for node in point_groups:
            for use in node.iter(SVG + "use"):
                if f"fill: {colors[block].lower()}" in use.get("style", "") and abs(float(use.get("x")) - cx) <= tolerance_x:
                    actual.append(float(use.get("y")))
        wanted = [xy(center, value)[1] for value in values]
        if len(actual) != len(wanted) or any(abs(a - b) > .002 for a, b in zip(sorted(actual), sorted(wanted))):
            point_errors.append({"block": block, "condition": condition, "actual": len(actual), "expected": len(wanted)})
        matching_pdf = [(d["rect"].y0 + d["rect"].y1) / 2 for d in pdf_points if same_color(d.get("fill"), rgb(colors[block])) and abs((d["rect"].x0 + d["rect"].x1) / 2 - cx) <= tolerance_x]
        if len(matching_pdf) != len(wanted) or any(abs(a - b) > .002 for a, b in zip(sorted(matching_pdf), sorted(wanted))):
            point_errors.append({"file": "PDF", "block": block, "condition": condition, "actual": len(matching_pdf), "expected": len(wanted)})
        point_counts.append({"block": block, "condition": condition, "n": len(wanted)})
        q1, median, q3 = [raw_quantile(values, q, opts.get("quantile_method", "linear")) for q in (.25, .5, .75)]
        width, cap = opts.get("summary_width", .7), opts.get("summary_cap_width", .22)
        summary_expected.extend([[xy(center - width / 2, median), xy(center + width / 2, median)], [xy(center - cap / 2, q1), xy(center + cap / 2, q1)], [xy(center - cap / 2, q3), xy(center + cap / 2, q3)], [xy(center, q1), xy(center, q3)]])
    summary_color = opts.get("summary_color", "#222222").lower()
    summary_actual = [path_points(path) for path in svg.iter(SVG + "path") if path.get("clip-path") and f"stroke: {summary_color}" in path.get("style", "")]
    summary_pdf = [[(item[1].x, item[1].y), (item[2].x, item[2].y)] for drawing in pdf_drawings(folder) if same_color(drawing.get("color"), rgb(summary_color)) for item in drawing["items"] if item[0] == "l"]
    flatten = lambda segments: sorted(tuple(v for point in segment for v in point) for segment in segments)
    expected_flat = flatten(summary_expected)
    match = lambda segments: len(segments) == len(expected_flat) and all(abs(a - b) <= .002 for actual, expected in zip(flatten(segments), expected_flat) for a, b in zip(actual, expected))
    name = f"{folder.parent.name}/{folder.name}"
    check(f"{name}: SVG/PDF all source points retain cohort, condition and raw value", not point_errors and sum(item["n"] for item in point_counts) == len(data), cell_counts=point_counts, mismatches=point_errors)
    check(f"{name}: SVG/PDF medians and IQRs computed on raw scale", match(summary_actual) and match(summary_pdf), intervals=len(centers), quantile_method=opts.get("quantile_method", "linear"), interval_meaning="IQR of observations, not CI")
    if opts.get("connect_pairs"):
        pair_errors = []
        for block in blocks:
            raw_pairs = _by([row for row in data if (row[f["block"]] if "block" in f else "Observations") == block], f["unit"])
            expected = []
            for unit_rows in raw_pairs.values():
                values = {r[f["condition"]]: float(r[f["value"]]) for r in unit_rows}
                for first, second in zip(conditions, conditions[1:]):
                    expected.append((xy(centers[block, first], values[first])[1], xy(centers[block, second], values[second])[1]))
            paths = [path for path in svg.iter(SVG + "path") if path.get("clip-path") and f"stroke: {colors[block].lower()}" in path.get("style", "")]
            actual = [(points[0][1], points[1][1]) for path in paths if len(points := path_points(path)) == 2]
            if not near_points(sorted(actual), sorted(expected)):
                pair_errors.append({"block": block, "actual": len(actual), "expected": len(expected)})
        check(f"{name}: actual SVG connectors retain declared within-unit pairs", not pair_errors, mismatches=pair_errors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--urschel-workbook", type=Path, default=Path("/private/tmp/easyviz_nature_b/41467_2024_47429_MOESM4_ESM.xlsx"))
    parser.add_argument("--truong-workbook", type=Path, default=Path("/private/tmp/easyviz_nature_b/41592_2023_2162_MOESM6_ESM.xlsx"))
    parser.add_argument("--report", type=Path, default=HERE / "source-verification.json")
    parser.add_argument("--exports", action="store_true", help="Also inspect current case SVG/PDF/PNG exports")
    args = parser.parse_args()
    check("Official Urschel workbook identity", digest(args.urschel_workbook) == "d902e7608caa56172bac12515bb0e0b79efb075b669424b8b63858ad21d371be", sha256=digest(args.urschel_workbook))
    check("Official Truong workbook identity", digest(args.truong_workbook) == "5a9283a1a16e5ca2f8fe0db16af0656e06ddb275dbfe64751643eb2a6dd8cc51", sha256=digest(args.truong_workbook))
    audit_urschel(args.urschel_workbook)
    audit_truong(args.truong_workbook)
    if args.exports:
        ecdf = ROOT / "examples/create/urschel-ecdf"
        audit_ecdf(ecdf / "output", ecdf / "source-data.csv", ecdf / "spec.json")
        components = ROOT / "examples/no-author-code/truong-components"
        for name in ("components", "ratios", "grouped"):
            if (components / f"output-{name}" / "panel.svg").exists():
                audit_replicate(components / f"output-{name}", components / "inputs" / ("ratios.csv" if name == "ratios" else "components.csv"), components / f"{name}-spec.json")
        paired = ROOT / "examples/no-author-code/urschel-paired"
        if (paired / "output/panel.svg").exists():
            audit_paired(paired / "output", paired / "source-data.csv", paired / "spec.json")
        if (paired / "output-connectors/panel.svg").exists():
            audit_paired(paired / "output-connectors", paired / "source-data.csv", paired / "connectors-spec.json")
    exported_paths = list((ROOT / "examples/create/urschel-ecdf/output").glob("panel.*")) + list((ROOT / "examples/no-author-code/truong-components").glob("output-*/panel.*")) + list((ROOT / "examples/no-author-code/urschel-paired").glob("output*/panel.*"))
    result = {"status": "pass" if all(item["status"] == "pass" for item in CHECKS) else "fail", "independence": "Independent raw XLSX XML parsing, decimal-value/cell/classification checks, Python statistics, and actual SVG/PDF geometry; no extraction or plotting implementation imported.", "checks": CHECKS, "passed": sum(c["status"] == "pass" for c in CHECKS), "total": len(CHECKS), "scope": "Source integrity and selected actual export geometry. Aesthetic review is separate.", "current_export_hashes": {str(p.relative_to(ROOT)): digest(p) for p in exported_paths} if args.exports else {}}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "passed", "total")}))
    raise SystemExit(0 if result["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
