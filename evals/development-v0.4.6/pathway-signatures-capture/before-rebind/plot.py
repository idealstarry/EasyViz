#!/usr/bin/env python3
"""A purpose-led Create view of published PROGENy model coefficients.

Requires the EasyViz runtime helpers, Matplotlib and its existing export
dependencies. The scientific derivation uses the complete local CSV; no pathway
activity, clustering, correlation or significance test is computed.
"""
import argparse
import csv
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="easyviz-signatures-mpl-"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent


def runtime_path(explicit=None):
    if explicit:
        path = Path(explicit).resolve()
        if not (path / "figure_elements.py").is_file() or not (path / "render.py").is_file():
            raise FileNotFoundError("Pass the EasyViz scripts directory with its sibling helpers intact.")
        return path
    for parent in HERE.parents:
        for relative in ("scripts", "skills/easyviz/scripts"):
            path = parent / relative
            if (path / "figure_elements.py").is_file() and (path / "render.py").is_file():
                return path
    raise FileNotFoundError("Supply --tools /path/to/easyviz/scripts.")


def load_source(path, contract):
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    cells = {}
    for row in rows:
        key = (row["gene"], row["pathway"])
        value = float(row["coefficient"])
        if key in cells or not math.isfinite(value):
            raise ValueError("Duplicate or nonfinite source coefficient.")
        cells[key] = row
    genes = list(dict.fromkeys(row["gene"] for row in rows))
    pathways = contract["pathways"]
    if len(rows) != contract["observations"] or len(genes) != contract["genes"]:
        raise ValueError("Source dimensions differ from the adopted input contract.")
    if set(cells) != {(gene, pathway) for gene in genes for pathway in pathways}:
        raise ValueError("The supplied coefficient matrix is incomplete.")
    signatures = {pathway: {gene for gene in genes if float(cells[gene, pathway]["coefficient"]) != 0} for pathway in pathways}
    if any(len(values) != contract["nonzero_per_pathway"] for values in signatures.values()):
        raise ValueError("A pathway signature has a different nonzero denominator.")
    membership = {gene: sum(gene in values for values in signatures.values()) for gene in genes}
    if sum(value > 1 for value in membership.values()) != contract["shared_genes"] or max(membership.values()) != contract["shared_gene_degree"]:
        raise ValueError("Shared-gene cardinality differs from the adopted contract.")
    pairs = []
    for ia, a in enumerate(pathways):
        for b in pathways[ia + 1:]:
            shared = sorted(signatures[a] & signatures[b])
            concordant = sum(float(cells[gene, a]["coefficient"]) * float(cells[gene, b]["coefficient"]) > 0 for gene in shared)
            union = len(signatures[a] | signatures[b])
            pairs.append({"pathway_a": a, "pathway_b": b, "shared_nonzero_genes": len(shared), "nonzero_union_genes": union,
                          "jaccard": len(shared) / union, "concordant_nonzero_genes": concordant,
                          "sign_agreement": concordant / len(shared) if shared else None, "source_genes": shared})
    return rows, cells, genes, pairs


def source_key(row):
    return {key: row[key] for key in ("gene", "pathway", "source_sheet", "source_cell")}


def pair_keys(pair, cells):
    # Complete column scopes preserve the denominator and absence reasoning.
    # Exact shared source cells then identify the contributors, without copying
    # the entire 11,143-cell matrix into every selectable SVG group.
    scopes = [{"kind": "coefficient-column", "pathway": pathway, "selection": "all supplied coefficients"}
              for pathway in (pair["pathway_a"], pair["pathway_b"])]
    return scopes + [source_key(cells[gene, pathway]) for gene in pair["source_genes"] for pathway in (pair["pathway_a"], pair["pathway_b"])]


def write_csv(path, rows, fields=None):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def draw(spec, contract, data_file, spec_file, tools):
    sys.path.insert(0, str(tools))
    core = importlib.import_module("render")
    elements = importlib.import_module("figure_elements")
    rows, cells, genes, pairs = load_source(data_file, contract)
    order = spec["pathway_order"]
    if set(order) != set(contract["pathways"]) or len(order) != len(set(order)):
        raise ValueError("Pathway order must contain each supplied pathway exactly once.")
    indexed = {frozenset((pair["pathway_a"], pair["pathway_b"])): pair for pair in pairs}
    selected = [pair for pair in pairs if pair["shared_nonzero_genes"] > spec["coefficient_selection"]["minimum_shared_exclusive"]]
    views = spec["coefficient_views"]
    if {frozenset(view["pair"]) for view in views} != {frozenset((pair["pathway_a"], pair["pathway_b"])) for pair in selected}:
        raise ValueError("Coefficient views do not implement the declared pair selection exactly.")
    layout, typography, rc = core.setup(spec)
    if layout["font_substituted"]:
        raise ValueError("Requested font is unavailable. Re-run with an explicit --font override and review its actual exports.")
    width, height = layout["width_mm"], layout["height_mm"]
    alias = lambda pathway: spec.get("display_aliases", {}).get(pathway, pathway)
    matrix_records, point_records, agreement_records = [], [], []
    with plt.rc_context(rc):
        fig = plt.figure(figsize=(width / 25.4, height / 25.4), dpi=layout["dpi"])
        fig._easyviz_track = "create"
        fig._easyviz_source_script = Path(__file__).resolve()
        fig._easyviz_data_file = data_file.resolve()
        fig._easyviz_spec_file = spec_file.resolve()
        fig._easyviz_resolved_colors = {"paired-coefficients": spec["point"]["face"], "agreement": spec["agreement"]["color"]}

        def axis(name):
            x, y, w, h = spec["geometry_mm"][name]
            return fig.add_axes([x / width, y / height, w / width, h / height])

        matrix = axis("overlap")
        matrix.set_xlim(0, len(order)); matrix.set_ylim(len(order), 0)
        matrix.set_xticks([]); matrix.set_yticks([])
        for spine in matrix.spines.values(): spine.set_visible(False)
        cmap = LinearSegmentedColormap.from_list("shared-count", spec["overlap_scale"]["anchors"], N=65536)
        norm = Normalize(*spec["overlap_scale"]["limits"])
        for index, pathway in enumerate(order):
            left = matrix.text(-.14, index + .5, alias(pathway), ha="right", va="center", clip_on=False)
            lower = matrix.text(index + .5, len(order) + .18, alias(pathway), ha="right", va="top", rotation=55, rotation_mode="anchor", clip_on=False)
            for location, label in (("row", left), ("column", lower)):
                elements.register(fig, label, "pathway-label", f"{location} · {pathway}", key=[location, pathway],
                                  source_keys=[{"kind": "coefficient-column", "pathway": pathway, "selection": "all supplied coefficients"}], editable=["color", "text"])
            for column in range(index):
                pair = indexed[frozenset((order[column], pathway))]
                count = pair["shared_nonzero_genes"]
                if not norm.vmin <= count <= norm.vmax:
                    raise ValueError("An overlap exceeds the adopted color scale; do not clip.")
                patch = Rectangle((column, index), 1, 1, facecolor=cmap(norm(count)),
                                  edgecolor=spec["strokes"]["seam"], linewidth=spec["strokes"]["seam_width_pt"], antialiased=False)
                matrix.add_patch(patch)
                gid = elements.register(fig, patch, "shared-count-cell", f"{pair['pathway_a']} · {pair['pathway_b']} · {count} shared genes",
                                        key=[pair["pathway_a"], pair["pathway_b"]], source_keys=pair_keys(pair, cells),
                                        spec_paths=["/overlap_scale/anchors", "/strokes/seam", "/strokes/seam_width_pt"],
                                        editable={"palette": "/overlap_scale/anchors", "seam_color": "/strokes/seam", "seam_width": "/strokes/seam_width_pt"})
                count_label = matrix.text(column + .5, index + .5, str(count), ha="center", va="center", color="#20272C" if count else "#9AA2A8")
                elements.register(fig, count_label, "shared-count-label", f"{pair['pathway_a']} · {pair['pathway_b']} · {count}",
                                  key=[pair["pathway_a"], pair["pathway_b"]], source_keys=pair_keys(pair, cells), editable=["color"])
                matrix_records.append({**pair, "source_genes": ";".join(pair["source_genes"]), "row_index": index, "column_index": column, "artist_id": gid})

        guide = axis("count_guide")
        guide.set_xlim(norm.vmin, norm.vmax); guide.set_ylim(0, 1); guide.set_yticks([])
        guide.set_xticks(spec["overlap_scale"]["ticks"]); guide.tick_params(length=2, width=.45, pad=2)
        for spine in guide.spines.values(): spine.set_visible(False)
        for index in range(256):
            value = norm.vmin + (norm.vmax - norm.vmin) * index / 256
            guide.add_patch(Rectangle((value, 0), (norm.vmax - norm.vmin) / 256, 1, facecolor=cmap(norm(value)), edgecolor="none"))
        guide.set_xlabel(spec["labels"]["count"], labelpad=2)
        elements.register(fig, guide, "shared-count-guide", "Shared nonzero genes color scale", key="count-guide", spec_paths=["/overlap_scale/anchors"], editable={"palette": "/overlap_scale/anchors"})

        for view in views:
            a, b = view["pair"]
            pair = indexed[frozenset((a, b))]
            ax = axis(view["geometry"])
            ax.set_xlim(*view["x_limits"]); ax.set_ylim(*view["y_limits"])
            ax.set_xticks(view["x_ticks"]); ax.set_yticks(view["y_ticks"])
            ax.tick_params(length=2.4, width=.55, pad=2)
            for side in ("top", "right"): ax.spines[side].set_visible(False)
            for side in ("left", "bottom"): ax.spines[side].set_color(spec["strokes"]["axis"])
            ax.set_xlabel(f"{alias(a)} {spec['labels']['coefficient']}", labelpad=3)
            ax.set_ylabel(f"{alias(b)} {spec['labels']['coefficient']}", labelpad=3)
            for coordinate in ("x", "y"):
                low, high = view[f"{coordinate}_limits"]
                if low < 0 < high:
                    line = (ax.axvline if coordinate == "x" else ax.axhline)(0, color=spec["strokes"]["zero"], linewidth=spec["strokes"]["zero_width_pt"], zorder=0)
                    elements.register(fig, line, "zero-coefficient-guide", f"{coordinate} coefficient = 0 · {a} · {b}", key=[a, b, coordinate], editable=["color", "linewidth"])
            low = max(view["x_limits"][0], view["y_limits"][0]); high = min(view["x_limits"][1], view["y_limits"][1])
            equality = ax.plot([low, high], [low, high], color=spec["strokes"]["equality"], linewidth=spec["strokes"]["equality_width_pt"], linestyle=(0, (2, 2)), zorder=0)[0]
            elements.register(fig, equality, "equal-coefficient-guide", f"Equal coefficients · {a} · {b}", key=[a, b], editable=["color", "linewidth"])
            labels = set(sorted(pair["source_genes"], key=lambda gene: -(abs(float(cells[gene, a]["coefficient"])) + abs(float(cells[gene, b]["coefficient"]))))[:spec["gene_labels"]["count_per_pair"]])
            for gene in pair["source_genes"]:
                first, second = cells[gene, a], cells[gene, b]
                x, y = float(first["coefficient"]), float(second["coefficient"])
                if not view["x_limits"][0] <= x <= view["x_limits"][1] or not view["y_limits"][0] <= y <= view["y_limits"][1]:
                    raise ValueError("An actual coefficient would be clipped by a view.")
                point = ax.plot(x, y, marker="o", linestyle="none", markersize=spec["point"]["diameter_pt"],
                                markerfacecolor=spec["point"]["face"], markeredgecolor=spec["point"]["edge"], markeredgewidth=spec["point"]["edge_width_pt"], zorder=3)[0]
                keys = [source_key(first), source_key(second)]
                gid = elements.register(fig, point, "paired-coefficient-gene", f"{gene} · {a} / {b}", key=[a, b, gene], source_keys=keys,
                                        spec_paths=["/point/face", "/point/diameter_pt", "/point/edge", "/point/edge_width_pt"],
                                        editable={"color": "/point/face", "diameter": "/point/diameter_pt", "edge_color": "/point/edge", "edge_width": "/point/edge_width_pt"})
                point_records.append({"gene": gene, "pathway_x": a, "pathway_y": b, "coefficient_x": first["coefficient"], "coefficient_y": second["coefficient"],
                                      "source_cell_x": first["source_cell"], "source_cell_y": second["source_cell"], "artist_id": gid})
                if gene in labels:
                    offset = spec["gene_labels"].get("pair_offsets", {}).get(f"{a}/{b}", spec["gene_labels"]["offset_points"])
                    label = ax.annotate(gene, (x, y), xytext=offset, textcoords="offset points", ha="right", va="bottom" if offset[1] > 0 else "top", fontstyle="italic")
                    elements.register(fig, label, "shared-gene-label", gene, key=[a, b, gene], source_keys=keys, editable=["color", "text"])

        agreement = axis("agreement")
        nonempty = sorted((pair for pair in pairs if pair["shared_nonzero_genes"]), key=lambda pair: (-pair["shared_nonzero_genes"], order.index(pair["pathway_a"]), order.index(pair["pathway_b"])))
        agreement.set_xlim(*spec["agreement"]["limits"]); agreement.set_ylim(len(nonempty), 0)
        agreement.set_xticks(spec["agreement"]["ticks"]); agreement.set_yticks([])
        agreement.tick_params(length=2, width=.5, pad=2)
        for side in ("left", "right", "top"): agreement.spines[side].set_visible(False)
        agreement.spines["bottom"].set_bounds(0, 1); agreement.spines["bottom"].set_linewidth(.5)
        agreement.set_xlabel(spec["labels"]["agreement"], labelpad=2)
        for index, pair in enumerate(nonempty):
            a, b = pair["pathway_a"], pair["pathway_b"]
            label = agreement.text(-.13, index + .5, f"{alias(a)} / {alias(b)}", ha="right", va="center", clip_on=False)
            keys = pair_keys(pair, cells)
            elements.register(fig, label, "agreement-pair-label", f"{a} / {b}", key=[a, b], source_keys=keys, editable=["color", "text"])
            agreement.plot([0, 1], [index + .5] * 2, color="#E3E7EA", linewidth=.45, zorder=0)
            point = agreement.plot(pair["sign_agreement"], index + .5, marker="o", linestyle="none", markersize=spec["agreement"]["point_diameter_pt"], color=spec["agreement"]["color"], clip_on=False)[0]
            gid = elements.register(fig, point, "coefficient-sign-agreement", f"{a} / {b} · same-sign fraction", key=[a, b], source_keys=keys,
                                    spec_paths=["/agreement/color", "/agreement/point_diameter_pt"], editable={"color": "/agreement/color", "diameter": "/agreement/point_diameter_pt"})
            fraction = agreement.text(1.1, index + .5, f"{pair['concordant_nonzero_genes']}/{pair['shared_nonzero_genes']}", ha="left", va="center", clip_on=False)
            elements.register(fig, fraction, "sign-count-label", f"{a} / {b} · concordant / shared", key=[a, b], source_keys=keys, editable=["color"])
            agreement_records.append({**pair, "source_genes": ";".join(pair["source_genes"]), "row_index": index, "artist_id": gid})
        fig.canvas.draw()
        bounds = []
        renderer = fig.canvas.get_renderer()
        for label in fig.findobj(match=matplotlib.text.Text):
            if label.get_visible() and label.get_text().strip():
                box = label.get_window_extent(renderer)
                bounds.append({"text": label.get_text(), "bounds_mm": [v * 25.4 / fig.dpi for v in (box.x0, box.y0, box.width, box.height)]})
        fig._case_records = (matrix_records, point_records, agreement_records)
        selected_marks = {(record["pathway_x"], record["pathway_y"], record["gene"]): record["artist_id"] for record in point_records}
        all_shared = []
        for pair in pairs:
            a, b = pair["pathway_a"], pair["pathway_b"]
            for gene in pair["source_genes"]:
                displayed_id = selected_marks.get((a, b, gene), selected_marks.get((b, a, gene), ""))
                all_shared.append({"gene": gene, "pathway_a": a, "pathway_b": b,
                                   "coefficient_a": cells[gene, a]["coefficient"], "coefficient_b": cells[gene, b]["coefficient"],
                                   "source_cell_a": cells[gene, a]["source_cell"], "source_cell_b": cells[gene, b]["source_cell"],
                                   "shown_in_coefficient_view": bool(displayed_id), "coefficient_artist_id": displayed_id})
        fig._case_shared = all_shared
        fig._case_bounds = bounds
    return fig, layout, core, rc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", type=Path)
    parser.add_argument("--data", type=Path, default=HERE / "inputs/coefficients.csv")
    parser.add_argument("--contract", type=Path, default=HERE / "inputs/input-contract.json")
    parser.add_argument("--spec", type=Path, default=HERE / "spec.json")
    parser.add_argument("--out", type=Path, default=HERE / "output")
    parser.add_argument("--font", help="Explicit recorded font override.")
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise FileExistsError("Choose a fresh output directory; visual attempts are preserved.")
    args.out.mkdir(parents=True, exist_ok=True)
    spec = json.loads(args.spec.read_text())
    if args.font: spec["layout"]["font"] = args.font
    contract = json.loads(args.contract.read_text())
    fig, layout, core, rc = draw(spec, contract, args.data, args.spec, runtime_path(args.tools))
    try:
        with plt.rc_context(rc): sizes = core.export(fig, args.out, spec, layout)
        overlaps, points, agreements = fig._case_records
        for name, records in (("all-pair-overlaps.csv", overlaps), ("selected-paired-coefficients.csv", points), ("nonempty-sign-agreement.csv", agreements)):
            write_csv(args.out / name, records)
        write_csv(args.out / "all-shared-gene-coefficients.csv", fig._case_shared)
        typography = {"axis": rc["axes.labelsize"], "tick": rc["xtick.labelsize"], "legend": rc["legend.fontsize"], "annotation": rc["font.size"]}
        (args.out / "settings.json").write_text(json.dumps({"spec": spec, "layout": layout, "typography": typography, "formats": spec["formats"],
                                                           "resolved_colors": fig._easyviz_resolved_colors,
                                                           "coefficient_unit": contract["unit"], "selection": spec["coefficient_selection"]}, indent=2) + "\n")
        metadata = {"status": "rendered_pending_validation_and_independent_review", "track": "create", "chart": spec["chart"],
                    "input_rows": contract["observations"], "unordered_pairs": len(overlaps), "nonempty_pairs": len(agreements),
                    "paired_gene_marks": len(points), "actual_font": layout["actual_font"], "font_substituted": layout["font_substituted"],
                    "canvas_mm": [layout["width_mm"], layout["height_mm"]], "exports": sizes,
                    "input_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(), "source_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    "resolved_spec_sha256": hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                    "source_paths": {"data_file": str(args.data.resolve()), "source_script": str(Path(__file__).resolve()), "spec_file": str(args.spec.resolve()), "contract_file": str(args.contract.resolve())},
                    "text_bounds": fig._case_bounds,
                    "scope": "Actual source-bound artist export; validate.py independently checks the copied workbook, derived quantities, vector coordinates and page dimensions. Image inspection is separate."}
        (args.out / "qa.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(json.dumps({"status": "rendered", "out": str(args.out.resolve()), "pairs": len(overlaps), "paired_gene_marks": len(points)}))
    finally:
        plt.close(fig)


if __name__ == "__main__": main()
