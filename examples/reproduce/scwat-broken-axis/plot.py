#!/usr/bin/env python3
"""Reproduce a segmented-axis panel from real data without author plotting code.

Custom route: two linear y segments share a categorical frame. Values/SEM
endpoints in the omitted numeric interval are rejected, never silently hidden.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent


def tools_path(explicit=None):
    if explicit:
        candidate = Path(explicit).resolve()
        if not (candidate / "render.py").is_file(): raise ValueError("--tools must contain the EasyViz plotting scripts")
        return candidate
    for parent in (HERE, *HERE.parents):
        for candidate in (parent / "scripts", parent / "skills/easyviz/scripts"):
            if (candidate / "render.py").is_file(): return candidate
    raise ValueError("Locate EasyViz scripts with --tools /path/to/easyviz/scripts")


def load(name, file, raw=None):
    loader = importlib.util.spec_from_file_location(name, file)
    module = importlib.util.module_from_spec(loader)
    sys.modules[name] = module
    if raw is None: loader.loader.exec_module(module)
    else: exec(compile(raw, str(file), "exec"), module.__dict__)
    return module


def csv_records(raw):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError("CSV headers must be nonempty and unique")
    rows = list(reader)
    if not rows or any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("CSV must have nonempty rectangular records")
    return rows


def segment_for(value, segments):
    number = float(value)
    if not math.isfinite(number): raise ValueError("All plotted quantities must be finite")
    found = [i for i, (low, high) in enumerate(segments) if low <= number <= high]
    if len(found) != 1:
        raise ValueError(f"Value/endpoint {number:g} would disappear outside the displayed axis segments; explicitly adopt a new scale")
    return found[0]


def parse(raw, spec):
    rows = csv_records(raw)
    required = {"observation_id", "gene", "display_gene", "group", "relative_expression"}
    if not required <= set(rows[0]): raise ValueError("Data requires observation_id, gene, display_gene, group, relative_expression")
    if len({row["observation_id"] for row in rows}) != len(rows) or any(not row["observation_id"].strip() for row in rows):
        raise ValueError("Observation identities must be nonempty and unique; do not infer pairing from row order")
    genes, groups = spec["gene_order"], spec["group_order"]
    if len(genes) != len(set(genes)) or len(groups) != 2 or len(set(groups)) != 2:
        raise ValueError("Adopt unique gene order and exactly two group identities")
    if set(row["gene"] for row in rows) != set(genes) or set(row["group"] for row in rows) != set(groups):
        raise ValueError("Data categories differ from the explicitly adopted category/group domain")
    segments = spec["segments"]
    if len(segments) != 2 or any(len(pair) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in pair) or pair[0] >= pair[1] for pair in segments) or segments[0][1] >= segments[1][0] or segments[0][0] != 0:
        raise ValueError("This bar contract requires two finite increasing nonoverlapping segments and a numeric zero baseline")
    if spec["style"]["bar_width"] <= 0 or spec["style"]["bar_gap"] <= 0 or 2 * spec["style"]["bar_width"] + spec["style"]["bar_gap"] >= .85:
        raise ValueError("Adopt positive slender bars, a visible pair gap and clear inter-category gaps")
    summaries = []
    for gene in genes:
        aliases = {row["display_gene"] for row in rows if row["gene"] == gene}
        if len(aliases) != 1: raise ValueError("A gene must have one explicit display alias")
        for group in groups:
            selected = [row for row in rows if row["gene"] == gene and row["group"] == group]
            if len(selected) < 2: raise ValueError("Each mean/SEM requires at least two supplied independent observations")
            values = [float(row["relative_expression"]) for row in selected]
            for value in values: segment_for(value, segments)
            mean = statistics.mean(values)
            sem = statistics.stdev(values) / math.sqrt(len(values))
            segment = segment_for(mean, segments)
            for endpoint in (mean - sem, mean + sem):
                if segment_for(endpoint, segments) != segment:
                    raise ValueError("An uncertainty interval crosses the omitted numeric range; use a different adopted scale")
            summaries.append({"gene": gene, "group": group, "n": len(values), "mean": mean, "sem": sem, "lower": mean - sem, "upper": mean + sem,
                              "segment": segment, "observation_ids": [row["observation_id"] for row in selected]})
    return rows, summaries


def p_class(text):
    value = text.strip()
    if value.startswith("<"):
        bound = float(value[1:].strip())
        if not math.isfinite(bound) or not 0 < bound <= 1:
            raise ValueError("Reported strict P bounds must be finite and in (0, 1]")
        if bound <= .001: return "***"
        if bound <= .01: return "**"
        if bound <= .05: return "*"
        raise ValueError("An upper P bound above .05 does not establish a significance class")
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1: raise ValueError("Reported P values must be in [0, 1]")
    return "***" if number < .001 else "**" if number < .01 else "*" if number < .05 else ""


def draw(core, mapper, rows, summaries, p_rows, spec):
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    import matplotlib.font_manager as font_manager
    # A missing font is explicit; this case does not silently substitute one.
    font_manager.findfont(font_manager.FontProperties(family=spec["layout"]["font"]), fallback_to_default=False)
    layout, type_roles, rc = core.setup(spec)
    with core.plt.rc_context(rc):
        fig = core.plt.figure(figsize=(layout["width_mm"] / 25.4, layout["height_mm"] / 25.4), dpi=layout["dpi"])
        g = spec["geometry_mm"]
        axes = [fig.add_axes([g["left"] / layout["width_mm"], (g["bottom"] + i * (g["segment_height"] + g["gap"])) / layout["height_mm"],
                              g["width"] / layout["width_mm"], g["segment_height"] / layout["height_mm"]]) for i in range(2)]
        for i, ax in enumerate(axes):
            ax.set_xlim(-.6, len(spec["gene_order"]) - .4)
            ax.set_ylim(*spec["segments"][i]); ax.set_yticks(spec["segment_ticks"][i])
            ax.spines[["top", "right"]].set_visible(False)
            ax.tick_params(axis="y", length=2.8, pad=2)
            ax.set_axisbelow(True)
            ax.patch.set_gid(f"axis-segment-{i}")
            if i: ax.spines["bottom"].set_visible(False); ax.tick_params(axis="x", bottom=False, labelbottom=False)
            else:
                labels = [next(row["display_gene"] for row in rows if row["gene"] == gene) for gene in spec["gene_order"]]
                ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right", rotation_mode="anchor", fontsize=type_roles["axis"])
                ax.tick_params(axis="x", length=2.8, pad=3)
        y_label = fig.text(3 / layout["width_mm"], (g["bottom"] + g["segment_height"] + g["gap"] / 2) / layout["height_mm"], spec["labels"]["y"], rotation=90, va="center", ha="center", fontsize=type_roles["axis"])
        mapper.register(fig, y_label, "axis-label", spec["labels"]["y"], key="shared-y", spec_paths=["/labels/y"], editable={"text": "/labels/y"})
        width, gap = spec["style"]["bar_width"], spec["style"]["bar_gap"]
        raw_artists, summary_artists, annotation_artists = [], [], []
        for record in summaries:
            gene, group = record["gene"], record["group"]
            index, group_index = spec["gene_order"].index(gene), spec["group_order"].index(group)
            center = index + (-1 if group_index == 0 else 1) * (width + gap) / 2
            color = spec["colors"][group]
            paths = [f"/colors/{group}", "/style/bar_linewidth_pt"]
            source_keys = [{"observation_id": identity} for identity in record["observation_ids"]]
            bar_artists = []
            for segment_index, ax in enumerate(axes):
                if segment_index > record["segment"]: continue
                bar = ax.bar(center, record["mean"], width=width, color="white", edgecolor=color, linewidth=spec["style"]["bar_linewidth_pt"], zorder=2)[0]
                mapper.register(fig, bar, "mean-bar", f"{gene} · {group} mean · segment {segment_index + 1}", key=[gene, group, segment_index], source_keys=source_keys,
                                spec_paths=paths, editable={"color": paths[0], "linewidth": paths[1]})
                bar_artists.append(bar)
            # Preserve the observed continuous vertical outline across the axis gap.
            if record["segment"] == 1:
                for edge_index, edge in enumerate((center - width / 2, center + width / 2)):
                    a = fig.transFigure.inverted().transform(axes[0].transData.transform((edge, spec["segments"][0][1])))
                    b = fig.transFigure.inverted().transform(axes[1].transData.transform((edge, spec["segments"][1][0])))
                    connector = Line2D([a[0], b[0]], [a[1], b[1]], transform=fig.transFigure, color=color, lw=spec["style"]["bar_linewidth_pt"], zorder=2)
                    fig.add_artist(connector)
                    mapper.register(fig, connector, "broken-bar-outline", f"{gene} · {group} continuous outline", key=[gene, group, edge_index], source_keys=source_keys, spec_paths=paths, editable={"color": paths[0], "linewidth": paths[1]})
            ax = axes[record["segment"]]
            # Reference shows upper SEM whiskers. Keep full endpoints in evidence;
            # rendering both provides an explicit complete uncertainty layer.
            interval = ax.plot([center, center], [record["lower"], record["upper"]], color=color, lw=spec["style"]["error_linewidth_pt"], zorder=3)[0]
            caps = []
            for endpoint in (record["lower"], record["upper"]):
                caps.append(ax.plot([center - width * .22, center + width * .22], [endpoint, endpoint], color=color, lw=spec["style"]["error_linewidth_pt"], zorder=3)[0])
            for cap_index, artist in enumerate([interval, *caps]):
                mapper.register(fig, artist, "sem-interval", f"{gene} · {group} SEM", key=[gene, group, cap_index], source_keys=source_keys,
                                spec_paths=[f"/colors/{group}", "/style/error_linewidth_pt"], editable={"color": f"/colors/{group}", "linewidth": "/style/error_linewidth_pt"})
            summary_artists.append({**record, "center_x": center, "bars": bar_artists, "interval": interval, "caps": caps})
            selected = [row for row in rows if row["gene"] == gene and row["group"] == group]
            for row_index, row in enumerate(selected):
                jitter = 0 if len(selected) == 1 else (row_index / (len(selected) - 1) - .5) * width * .65
                value = float(row["relative_expression"])
                segment_index = segment_for(value, spec["segments"])
                point = axes[segment_index].plot(center + jitter, value, "o", markersize=spec["style"]["point_size_pt"], color=color, markeredgewidth=0, clip_on=False, zorder=4)[0]
                mapper.register(fig, point, "observation", f"{row['display_gene']} · {group} · {row['observation_id']}", key=row["observation_id"],
                                source_keys=[{"observation_id": row["observation_id"], "gene": gene, "group": group, "source_cell": row.get("source_cell", "")}],
                                spec_paths=[f"/colors/{group}", "/style/point_size_pt"], editable={"color": f"/colors/{group}", "size": "/style/point_size_pt"})
                raw_artists.append({"row": row, "artist": point, "segment": segment_index, "x": center + jitter})
        reported = {row["gene"]: row for row in p_rows}
        if len(reported) != len(p_rows) or set(reported) != set(spec["gene_order"]): raise ValueError("Exactly one reported P entry is required per adopted gene")
        for index, gene in enumerate(spec["gene_order"]):
            label = p_class(reported[gene]["reported_p"])
            if not label: continue
            selected = [row for row in rows if row["gene"] == gene]
            local = [record for record in summaries if record["gene"] == gene]
            max_value = max([float(row["relative_expression"]) for row in selected] + [record["upper"] for record in local])
            segment_index = segment_for(max_value, spec["segments"])
            ax = axes[segment_index]
            span = spec["segments"][segment_index][1] - spec["segments"][segment_index][0]
            y = max_value + span * .07
            # Comparison guides are display annotations, not measurements. A
            # lower-segment guide may use the physical axis gap, as the source
            # does for Dio2; raw values and SEM endpoints still cannot do so.
            extra = (g["gap"] / g["segment_height"] * span) if segment_index == 0 else 0
            if y + span * .09 > spec["segments"][segment_index][1] + extra:
                raise ValueError("Comparison label lacks adopted segment clearance; increase the agreed segment explicitly")
            line = ax.plot([index - (width + gap) / 2, index + (width + gap) / 2], [y, y], color="#222222", lw=spec["style"]["annotation_linewidth_pt"], clip_on=False, zorder=5)[0]
            text = ax.text(index, y + span * .015, label, ha="center", va="bottom", fontsize=type_roles["annotation"], zorder=5)
            for kind, artist in (("line", line), ("stars", text)):
                mapper.register(fig, artist, "reported-comparison", f"{gene} reported {label}", key=[gene, kind],
                                source_keys=[{"gene": gene, "reported_p": reported[gene]["reported_p"], "source_cell": reported[gene].get("source_cell", "")}], editable=["position", "color"])
            annotation_artists.append({"gene": gene, "reported_p": reported[gene]["reported_p"], "stars": label, "segment": segment_index, "y": y})
        # Horizontal terminal ticks reproduce the observed axis-break convention.
        for segment_index, edge_y in ((0, 1), (1, 0)):
            mark = axes[segment_index].plot([-.018, .018], [edge_y, edge_y], transform=axes[segment_index].transAxes, color="#222222", lw=.6, clip_on=False, zorder=6)[0]
            mapper.register(fig, mark, "axis-break", "Discontinuous y axis", key=segment_index, editable=["color", "linewidth"])
        handles = [Patch(facecolor="white", edgecolor=spec["colors"][group], linewidth=spec["style"]["bar_linewidth_pt"], label=group) for group in spec["group_order"]]
        legend = fig.legend(handles=handles, loc="upper right", bbox_to_anchor=(.985, .90), frameon=False, handlelength=1.15, handleheight=.72, handletextpad=.45, borderaxespad=0, labelspacing=.35, fontsize=type_roles["legend"])
        mapper.register(fig, legend, "legend", "Genotype key", key="genotypes", editable=["position"])
        for handle, group in zip(legend.legend_handles, spec["group_order"]):
            mapper.register(fig, handle, "legend-key", group, key=group, source_keys=[{"group": group}], spec_paths=[f"/colors/{group}"], editable={"color": f"/colors/{group}"})
        fig.canvas.draw()
    return fig, axes, raw_artists, summary_artists, annotation_artists, layout, type_roles, rc


def actual_evidence(fig, axes, raw_artists, summary_artists, spec):
    raw_records, summaries = [], []
    for item in raw_artists:
        row, artist = item["row"], item["artist"]
        actual = float(artist.get_ydata()[0])
        if actual != float(row["relative_expression"]): raise ValueError("Rendered point differs from source")
        raw_records.append({**row, "display_x": float(artist.get_xdata()[0]), "artist_y": actual, "segment": item["segment"], "artist_id": artist.get_gid()})
    for item in summary_artists:
        center = float(item["bars"][-1].get_height())
        low, high = map(float, item["interval"].get_ydata())
        if not math.isclose(center, item["mean"], abs_tol=1e-12) or not math.isclose(low, item["lower"], abs_tol=1e-12) or not math.isclose(high, item["upper"], abs_tol=1e-12):
            raise ValueError("Rendered mean/SEM differs from the descriptive summary")
        summaries.append({key: item[key] for key in ("gene", "group", "n", "mean", "sem", "lower", "upper", "segment", "center_x")}
                         | {"artist_mean": center, "artist_lower": low, "artist_upper": high})
    renderer, factor = fig.canvas.get_renderer(), 25.4 / fig.dpi
    actual_axes = [[value * factor for value in (ax.get_window_extent(renderer).x0, ax.get_window_extent(renderer).width)] for ax in axes]
    if not all(math.isclose(a, b, abs_tol=1e-6) for a, b in zip(*actual_axes)): raise ValueError("Segment category frames are not actually aligned")
    text_boxes = []
    for text in fig.findobj(__import__("matplotlib").text.Text):
        if not text.get_visible() or not text.get_text().strip(): continue
        bounds = text.get_window_extent(renderer)
        box = [value * factor for value in (bounds.x0, bounds.y0, bounds.x1, bounds.y1)]
        if box[0] < -.05 or box[1] < -.05 or box[2] > spec["layout"]["width_mm"] + .05 or box[3] > spec["layout"]["height_mm"] + .05:
            raise ValueError(f"Required text clips the fixed canvas: {text.get_text()}")
        text_boxes.append({"text": text.get_text(), "font_pt": text.get_fontsize(), "bbox_mm": box})
    return raw_records, summaries, {"source_rows": len(raw_records), "summary_rows": len(summaries), "shared_x_plot_box_mm": actual_axes,
                                    "segments": spec["segments"], "text_boxes": text_boxes, "numeric_values_checked_from_artists": True,
                                    "omitted_interval_contains_source_values_or_endpoints": False, "cross_gene_mouse_pairing_inferred": False}


def write_csv(path, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=HERE / "inputs/observations.csv")
    parser.add_argument("--p-values", type=Path, default=HERE / "inputs/author-p-values.csv")
    parser.add_argument("--spec", type=Path, default=HERE / "spec.json")
    parser.add_argument("--out", type=Path, default=HERE / "output")
    parser.add_argument("--tools", type=Path)
    parser.add_argument("--font", help="Explicit installed-font override; the consumed adopted spec records this change")
    args = parser.parse_args()
    tools = tools_path(args.tools); sys.path.insert(0, str(tools))
    handoff = load("scwat_handoff", tools / "figure_handoff.py")
    aux = {"author_p_values": args.p_values, "render_helper": tools / "render.py", "figure_elements_helper": tools / "figure_elements.py", "figure_handoff_helper": tools / "figure_handoff.py"}
    if args.font:
        # The canonical original and explicitly adopted override remain distinct
        # captured inputs. Do not pretend the Arial spec generated another font.
        original_path, original_bytes = args.spec, args.spec.read_bytes()
        adopted = json.loads(original_bytes)
        adopted["explicit_overrides"] = {"font": {"original": adopted["layout"]["font"], "requested": args.font}}
        adopted["layout"]["font"] = args.font
        if any((args.out / name).exists() for name in ("panel.svg", "panel.pdf", "panel.png", "handoff.json", "adopted-spec.json")):
            raise FileExistsError("Font override needs a fresh output directory")
        args.out.mkdir(parents=True, exist_ok=True)
        args.spec = args.out / "adopted-spec.json"
        args.spec.write_text(json.dumps(adopted, indent=2, ensure_ascii=False) + "\n")
        aux["original_spec_file"] = original_path
    capture = handoff.capture_inputs(args.out, data_file=args.data, source_script=Path(__file__), spec_file=args.spec, auxiliary_inputs=aux)
    if args.font and capture.read_auxiliary("original_spec_file") != original_bytes:
        raise ValueError("Original specification changed during explicit font adoption")
    core = load("scwat_core", tools / "render.py", capture.read_auxiliary("render_helper")); mapper = core.figure_elements
    spec = json.loads(capture.read("spec_file")); rows, summaries = parse(capture.read("data_file"), spec)
    p_rows = csv_records(capture.read_auxiliary("author_p_values"))
    fig = None
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        fig, axes, points, bars, annotations, layout, typography, rc = draw(core, mapper, rows, summaries, p_rows, spec)
        fig._easyviz_track = "reproduce"
        fig._easyviz_data_file = capture.paths["data_file"]
        fig._easyviz_source_script = capture.paths["source_script"]
        fig._easyviz_spec_file = capture.paths["spec_file"]
        bindings = {key: {"path": str(path), "sha256": hashlib.sha256(capture.read(key)).hexdigest()} for key, path in capture.paths.items()}
        bindings.update({key: {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()} for key, (path, raw) in capture.auxiliary.items()})
        fig._easyviz_source_bindings = bindings
        raw_records, summary_records, evidence = actual_evidence(fig, axes, points, bars, spec)
        with core.plt.rc_context(rc): exports = core.export(fig, args.out, spec, layout)
        write_csv(args.out / "plotting-data.csv", raw_records); write_csv(args.out / "summary-data.csv", summary_records)
        settings = {**spec, "layout": layout, "typography": typography, "source_bindings": bindings, "resolved_colors": spec["colors"], "version": {"input_sha256": bindings["data_file"]["sha256"], "source_script_sha256": bindings["source_script"]["sha256"]}}
        (args.out / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
        report = {"status": "pass", "valid_outputs": True, "track": "reproduce", "plotted_input_rows": len(rows), "summary_definition": "Mean ± SEM (sample SD / sqrt(n)); experimental-unit meaning comes from the caption/data contract",
                  "source_bindings": bindings, "layout_mm": [layout["width_mm"], layout["height_mm"]], "exports": exports, "artist_evidence": evidence, "reported_comparisons": annotations,
                  "statistical_tests_recomputed": False, "source_unknowns": ["Cross-gene mouse identities", "Upstream normalization/calibrator values", "Multiplicity handling"], "visual_review_status": "not_reviewed"}
        (args.out / "qa.json").write_text(json.dumps(report, indent=2) + "\n")
        handoff.write_receipt(args.out, capture=capture, formats=spec["formats"], resolved_spec=spec, track="reproduce")
        print(json.dumps({"status": "rendered-and-numerically-checked", "source_rows": len(rows), "out": str(args.out), "visual_review_passed": False}))
    except Exception as exc:
        (args.out / "qa.json").write_text(json.dumps({"status": "needs_revision", "valid_outputs": False, "error": str(exc)}) + "\n")
        if (args.out / "elements.json").exists(): (args.out / "elements.json").rename(args.out / "failed-elements.json")
        raise
    finally:
        if fig is not None: core.plt.close(fig)


if __name__ == "__main__": main()
