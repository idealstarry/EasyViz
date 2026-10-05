"""Actual before/after consumer evidence using an unchanged repaired core."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]


def load(name, script):
    loader = importlib.util.spec_from_file_location(name, script)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    destination = BASE / "focused-integration/actual-exports"
    if destination.exists():
        raise RuntimeError("Existing focused before/after evidence is immutable")
    destination.mkdir()
    before_scripts = destination / "before-runtime"
    shutil.copytree(REPO / "skills/easyviz/scripts", before_scripts, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("preview_choices", "replicate_plot"):
        shutil.copyfile(BASE / ("focused-integration/" + name + "-before.py"), before_scripts / (name + ".py"))
    recipes = {label: {name: load("focused_proof_" + label + name, folder / (name + ".py"))
                       for name in ("preview_choices", "replicate_plot")}
               for label, folder in (("before", before_scripts), ("after", REPO / "skills/easyviz/scripts"))}
    preview_request = {"row_kind": "observations", "fields": {"group": "group", "value": "value"},
                       "design": {"structure": "unknown", "confirmed": False, "unit_definition": "Unknown supplied observation"},
                       "measurement_units": "a.u.", "colors": {"A": "#29ACF3"},
                       "layout": {"width_mm": 88, "height_mm": 66, "font": "DejaVu Sans", "dpi": 160},
                       "formats": ["png", "pdf", "svg"]}
    radius = math.sqrt(7 / math.pi) * 25.4 / 72
    vector_safe_high = 3 / (1 - radius * 1.0001 / (.65 * 66.1))
    replicate_spec = {"chart": "replicate", "fields": {"condition": "condition", "unit": "unit", "value": "value"},
                      "colors": {"A": "#29ACF3"}, "labels": {"y": "Value"},
                      "layout": {"width_mm": 88, "height_mm": 66.1, "font": "DejaVu Sans", "dpi": 160,
                                 "auto_fit": False, "margins": {"left": .19, "right": .77, "bottom": .23, "top": .88}},
                      "formats": ["png", "pdf", "svg"]}
    cases = [("preview-endpoints", "preview_choices", b"group,value\nA,1\nA,2\nA,3\n", preview_request,
              {"value_limits": [1, 3]}, True),
             ("preview-inside", "preview_choices", b"group,value\nA,1\nA,2\nA,3\n", preview_request,
              {"value_limits": [0, 4]}, False),
             ("replicate-raster-only", "replicate_plot", b"condition,unit,value\nA,u1,1\nA,u2,3\n", replicate_spec,
              {"mode": "summary", "uncertainty": "none", "marker_area_pt2": 7, "y_limits": [0, vector_safe_high]}, True),
             ("replicate-inside", "replicate_plot", b"condition,unit,value\nA,u1,1\nA,u2,3\n", replicate_spec,
              {"mode": "summary", "uncertainty": "none", "marker_area_pt2": 7, "y_limits": [0, 4]}, False)]
    result = {"core_sha256": digest(REPO / "skills/easyviz/scripts/render.py"),
              "clipping_helper_sha256": digest(REPO / "skills/easyviz/scripts/observation_clipping.py"),
              "cases": []}
    for case_name, recipe_name, raw, base, options, should_fail in cases:
        case = destination / case_name
        case.mkdir()
        source = case / "source.csv"
        source.write_bytes(raw)
        adopted = {**deepcopy(base), "options": options}
        spec_path = case / "adopted.json"
        spec_path.write_text(json.dumps(adopted, indent=2) + "\n")
        entry = {"case": case_name, "expected_clipping": should_fail, "source_sha256": digest(source), "adopted": adopted}
        for label in ("before", "after"):
            recipe = recipes[label][recipe_name]
            out = case / label
            try:
                if recipe_name == "preview_choices":
                    recipe.preview(source, spec_path, out)
                else:
                    recipe.render(source, adopted, out)
                exception = None
            except recipe.SpecError as exc:
                exception = str(exc)
            figure_out = out / "box-points" if recipe_name == "preview_choices" else out
            qa = json.loads((figure_out / "qa.json").read_text())
            settings = json.loads((figure_out / "settings.json").read_text())
            entry[label] = {"exception": exception, "valid_outputs": qa["valid_outputs"], "qa_status": qa["status"],
                            "old_geometry": qa.get("mark_geometry"), "point_layout": qa.get("point_layout"),
                            "source_to_artist_audit": qa["source_to_artist_audit"], "adopted_options": settings["options"],
                            "exports": {suffix: digest(figure_out / ("panel." + suffix)) for suffix in adopted["formats"]}}
            if label == "after":
                entry[label]["observation_clipping"] = qa["observation_clipping"]
                assert qa["observation_clipping"] == settings["observation_clipping"]
        entry["unchanged_exports"] = {suffix: entry["before"]["exports"][suffix] == entry["after"]["exports"][suffix]
                                      for suffix in adopted["formats"]}
        assert entry["before"]["valid_outputs"] is True
        assert entry["after"]["valid_outputs"] is not should_fail
        assert entry["before"]["adopted_options"] == entry["after"]["adopted_options"]
        assert all(entry["unchanged_exports"].values())
        assert source.read_bytes() == raw
        if recipe_name == "replicate_plot":
            assert entry["after"]["old_geometry"]["status"] == "pass"
        result["cases"].append(entry)
    result["all_cases_pass"] = True
    (destination / "evidence.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"cases": len(cases), "all_cases_pass": True, "evidence": str(destination / "evidence.json")}))


if __name__ == "__main__":
    main()
