"""Internal pass-2 corrections after the recorded first-render review.

These are task-specific code/layout repairs, not unseen engine successes.
Keep the original proposals and their failures. Quantitative coordinates,
source rows, statistics, point sizes, fonts, canvas sizes and limits are fixed.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import json
import os
import shutil
import tempfile

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "easyviz-matplotlib"))
import pymupdf as fitz
from matplotlib.collections import PathCollection, PolyCollection

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, choices=("six-long-label-boxes", "dense-unequal-violins", "three-class-scatter"))
    args = parser.parse_args()
    case = args.case
    selected = "candidate-02" if case == "dense-unequal-violins" else "candidate-01"
    source = HERE / "outputs" / case / selected
    out = HERE / "internal-pass-02" / case
    out.mkdir(parents=True, exist_ok=False)
    spec = json.loads((source / "spec.json").read_text())
    original = copy.deepcopy(spec)
    if case == "six-long-label-boxes":
        spec["options"].update(point_category_offset=.1, point_max_offset_mm=4.5,
                               point_gap_pt=.1, box_width=.14)
    elif case == "dense-unequal-violins":
        spec["options"].update(point_category_offset=.1, point_max_offset_mm=7,
                               point_gap_pt=.1, violin_width=.16, violin_inner_width=.10,
                               violin_fill_alpha=1)
    else:
        spec["legends"] = {"categorical": {"position": "top", "ncol": 3}}
        spec["layout"]["margins"]["top"] = .89
    shutil.copy2(HERE / "inputs" / case / "data.csv", out / "data.csv")
    shutil.copy2(HERE / "inputs" / case / "caption.md", out / "caption.md")
    (out / "spec.json").write_text(json.dumps(spec, indent=2) + "\n")
    module_spec = importlib.util.spec_from_file_location("pass_two_core", ROOT / "skills/easyviz/scripts/render.py")
    core = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(core)
    original_draw, original_export = core.draw, core.export
    offset = -.32 if case == "six-long-label-boxes" else -.33

    def draw(*positional, **keywords):
        fig, colors = original_draw(*positional, **keywords)
        ax = fig.axes[0]
        if case == "three-class-scatter":
            for collection in ax.collections:
                if isinstance(collection, PathCollection):
                    centers = collection.get_offsets()
                    assert all(0 <= x <= 12 and -4 <= y <= 15 for x, y in centers)
                    collection.set_clip_on(False)
        else:
            # Side-by-side summary and raw lanes, rather than placing a dense
            # swarm over the quartiles. Only categorical summary positions move.
            for patch in ax.patches:
                if case == "six-long-label-boxes":
                    patch.get_path().vertices[:, 0] += offset
                else:
                    patch.set_x(patch.get_x() + offset)
            for line in ax.lines:
                line.set_xdata(core.np.asarray(line.get_xdata()) + offset)
            if case == "dense-unequal-violins":
                for collection in ax.collections:
                    if isinstance(collection, PolyCollection):
                        for path in collection.get_paths():
                            path.vertices[:, 0] += offset
        fig.canvas.draw()
        return fig, colors

    def export(fig, *positional, **keywords):
        # Bind the actual custom drawing code, not just the shared exporter.
        fig._easyviz_source_script = Path(__file__).resolve()
        return original_export(fig, *positional, **keywords)

    core.draw, core.export = draw, export
    qa = core.render(out / "data.csv", spec, out, spec_path=out / "spec.json", track="create")
    settings_path = out / "settings.json"
    settings = json.loads(settings_path.read_text())
    settings["shared_renderer"] = settings["renderer"]
    settings["renderer"] = {"version": "internal-pass-02", "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                            "scope": "This actual task-specific drawing wrapper; shared exporter identity is recorded separately."}
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
    assert original["layout"]["width_mm"] == spec["layout"]["width_mm"]
    assert original["layout"]["height_mm"] == spec["layout"]["height_mm"]
    assert original["layout"]["font_size_pt"] == spec["layout"]["font_size_pt"]
    for name in ("y_limits", "x_limits", "point_area_pt2", "kind", "violin_inner"):
        assert original["options"].get(name) == spec["options"].get(name)
    document = fitz.open(out / "panel.pdf")
    document[0].get_pixmap(dpi=96).save(out / "preview-96dpi.png")
    document.close()
    note = {"case": case, "visual_pass": 2, "baseline": selected,
            "technical_status": qa["status"], "custom_code": str(Path(__file__).resolve()),
            "custom_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "summary_category_shift": offset if case != "three-class-scatter" else None,
            "quantitative_point_coordinates_and_scales_preserved": True,
            "classification": "Internal correction after observed failures; not a new unseen engine test."}
    (out / "correction.json").write_text(json.dumps(note, indent=2) + "\n")
    print(json.dumps(note))


if __name__ == "__main__":
    main()
