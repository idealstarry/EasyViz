"""Compare fixed and measured layouts on explicitly synthetic transfer inputs."""
from copy import deepcopy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
loader = importlib.util.spec_from_file_location("easyviz_layout_evaluation", REPO / "skills/easyviz/scripts/render.py")
renderer = importlib.util.module_from_spec(loader)
loader.loader.exec_module(renderer)


def cases():
    yield "scatter", ["dose", "response"], [[i, 2 + .7 * i + (i % 3) * .4] for i in range(1, 18)], {
        "chart": "scatter", "fields": {"x": "dose", "y": "response"},
        "labels": {"x": "Dose (a.u.)", "y": "Prepared response (a.u.)"}}
    groups = ["Resident macrophages", "Activated monocytes", "Interferon macrophages", "Antigen-presenting cells"]
    yield "long-label-distribution", ["group", "score"], [[group, .3 * i + (j - 3) * .07 + (j % 2) * .02]
        for i, group in enumerate(groups) for j in range(8)], {
        "chart": "distribution", "fields": {"group": "group", "value": "score"},
        "options": {"orientation": "horizontal"}, "labels": {"x": "Prepared score (a.u.)"}}
    yield "rectangular-heatmap", ["row", "column", "value"], [[f"Gene {i+1}", f"Sample {j+1}", ((i * 7 + j * 3) % 17) / 4 - 2]
        for i in range(7) for j in range(9)], {
        "chart": "heatmap", "fields": {"row": "row", "column": "column", "value": "value"},
        "labels": {"x": "Sample", "y": "Gene", "color": "Score"},
        "options": {"color_limits": [-2, 2], "color_center": 0}, "colormap": "somerville-blue-coral"}


def main():
    summary = {"evidence": "synthetic layout transfer, not biological or model-performance evidence", "cases": []}
    for name, columns, rows, spec in cases():
        root = ROOT / name
        root.mkdir(exist_ok=True)
        source = root / "source.csv"
        with source.open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(columns)
            writer.writerows(rows)
        spec.update(layout={"width_mm": 88, "height_mm": 70, "font": "Arial", "font_size_pt": 8, "dpi": 300}, formats=["pdf", "svg", "png"])
        record = {"case": name, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "input_rows": len(rows)}
        for mode in ("fixed", "measured"):
            current = deepcopy(spec)
            if mode == "measured":
                current["layout"]["auto_fit"] = True
            renderer.write_json(root / f"{mode}-spec.json", current)
            try:
                renderer.render(source, current, root / mode)
                error = None
            except renderer.SpecError as exc:
                error = str(exc)
            qa = json.loads((root / mode / "qa.json").read_text())
            settings = json.loads((root / mode / "settings.json").read_text())
            margins = settings["layout"]["margins"]
            record[mode] = {"status": qa["status"], "error": error,
                            "data_area_fraction": (margins["right"] - margins["left"]) * (margins["top"] - margins["bottom"]),
                            "clipped_text": len(qa["clipped_text"]), "tick_collisions": len(qa["overlapping_tick_labels"]),
                            "legend_issues": len(qa["legend_layout"]["issues"]), "font": settings["layout"]["actual_font"],
                            "font_size_pt": settings["layout"]["font_size_pt"], "width_mm": qa["width_mm"], "height_mm": qa["height_mm"]}
        summary["cases"].append(record)
    renderer.write_json(ROOT / "summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
