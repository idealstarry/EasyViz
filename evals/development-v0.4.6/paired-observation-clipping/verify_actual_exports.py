"""Persist real paired before/after exports without altering locked geometry."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
RUNTIME = BASE / "staged-runtime"
if not RUNTIME.is_dir():
    RUNTIME = BASE.parents[2] / "skills/easyviz/scripts"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name, script):
    loader = importlib.util.spec_from_file_location(name, script)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


def normalized_svg(path, raw_group_ids):
    root = ET.fromstring(path.read_bytes())
    for item in root.iter():
        if item.attrib.get("id") in raw_group_ids:
            del item.attrib["id"]
    return ET.tostring(root)


def main():
    destination = BASE / "actual-exports"
    if destination.exists():
        raise RuntimeError("Existing actual export evidence is immutable")
    destination.mkdir()
    before_runtime = destination / "before-runtime"
    shutil.copytree(RUNTIME, before_runtime,
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(BASE / "paired_plot-before.py", before_runtime / "paired_plot.py")
    recipes = {name: load("paired_evidence_" + name, folder / "paired_plot.py")
               for name, folder in (("before", before_runtime), ("after", RUNTIME))}
    base_spec = {"chart": "paired", "fields": {"unit": "id", "condition": "condition", "value": "value"},
                 "options": {"point_layout": "swarm", "point_area_pt2": 10, "point_alpha": 1,
                             "connect_pairs": True, "y_limits": [0, 4]},
                 "layout": {"width_mm": 88, "height_mm": 66.1, "font": "DejaVu Sans", "dpi": 160,
                            "auto_fit": False, "margins": {"left": .19, "right": .77, "bottom": .23, "top": .88}},
                 "formats": ["png", "pdf", "svg"], "labels": {"y": "Value"}}
    radius_mm = math.sqrt(10 / math.pi) * 25.4 / 72
    vector_safe_high = 3 / (1 - radius_mm * 1.0001 / (.65 * 66.1))
    linear_raw = b"id,condition,value\nu1,A,1\nu1,B,2\nu2,A,3\nu2,B,2.5\n"
    cases = [("inside-safe", linear_raw, {}, True, True),
             ("png-only-clipping", linear_raw, {"y_limits": [0, vector_safe_high]}, True, False),
             ("locked-endpoints", linear_raw, {"y_limits": [1, 3]}, False, False),
             ("log-endpoints", b"id,condition,value\nu1,A,1\nu1,B,10\nu2,A,100\nu2,B,30\n",
              {"y_scale": "log", "y_limits": [1, 100]}, False, False)]
    evidence = {"runtime_source_sha256": {name: digest(RUNTIME / name)
                                          for name in recipes["after"].HELPERS + ("paired_plot.py",)},
                "before_paired_sha256": digest(BASE / "paired_plot-before.py"),
                "scope": "Raw circular paired observations only; summary and connector footprints remain outside this check.",
                "cases": []}
    for name, raw, options, before_valid, after_valid in cases:
        case = destination / name
        case.mkdir()
        source = case / "source.csv"
        source.write_bytes(raw)
        adopted = deepcopy(base_spec)
        adopted["options"].update(options)
        spec_path = case / "adopted.json"
        spec_path.write_text(json.dumps(adopted, indent=2) + "\n")
        entry = {"case": name, "source_sha256": digest(source), "adopted": adopted}
        for label in ("before", "after"):
            recipe = recipes[label]
            out = case / label
            try:
                recipe.render(source, deepcopy(adopted), out, spec_path=spec_path)
                error = None
            except recipe.SpecError as exc:
                error = str(exc)
            qa = json.loads((out / "qa.json").read_text())
            settings = json.loads((out / "settings.json").read_text())
            elements = json.loads((out / "elements.json").read_text())
            raw_groups = [item for item in elements["elements"] if item["role"] == "point-group"]
            entry[label] = {"valid_outputs": qa["valid_outputs"], "exception": error,
                            "source_to_artist_audit": qa["source_to_artist_audit"],
                            "mark_geometry": qa["mark_geometry"], "adopted_options": settings["options"],
                            "axis": settings["axis"], "mark_policy": settings["mark_policy"],
                            "raw_groups": raw_groups,
                            "exports": {suffix: digest(out / ("panel." + suffix)) for suffix in adopted["formats"]}}
            if label == "after":
                entry[label]["observation_clipping"] = qa["observation_clipping"]
                assert qa["observation_clipping"] == settings["observation_clipping"]
            recipe.plt.close("all")
        assert entry["before"]["valid_outputs"] is before_valid
        assert entry["after"]["valid_outputs"] is after_valid
        for key in ("adopted_options", "axis", "mark_policy", "source_to_artist_audit", "mark_geometry"):
            assert entry["before"][key] == entry["after"][key], (name, key)
        entry["byte_identical_exports"] = {suffix: entry["before"]["exports"][suffix] == entry["after"]["exports"][suffix]
                                            for suffix in adopted["formats"]}
        assert entry["byte_identical_exports"]["png"]
        assert entry["byte_identical_exports"]["pdf"]
        before_root = ET.parse(case / "before/panel.svg").getroot()
        baseline_raw_ids = {item.attrib["id"] for item in before_root.iter()
                            if item.attrib.get("id", "").startswith("PathCollection_")}
        after_raw_ids = {item["id"] for item in entry["after"]["raw_groups"]}
        assert len(baseline_raw_ids) == len(after_raw_ids) == 2
        entry["svg_geometry_identical_after_removing_only_raw_collection_group_ids"] = (
            normalized_svg(case / "before/panel.svg", baseline_raw_ids) ==
            normalized_svg(case / "after/panel.svg", after_raw_ids))
        assert entry["svg_geometry_identical_after_removing_only_raw_collection_group_ids"]
        entry["byte_identical_numeric_tables"] = {filename: (case / "before" / filename).read_bytes() ==
                                                   (case / "after" / filename).read_bytes()
                                                   for filename in ("plotting-data.csv", "summary-data.csv", "stats.json")}
        assert all(entry["byte_identical_numeric_tables"].values())
        assert source.read_bytes() == raw
        evidence["cases"].append(entry)
    evidence["all_cases_pass"] = True
    (destination / "evidence.json").write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"cases": len(cases), "all_cases_pass": True, "evidence": str(destination / "evidence.json")}))


if __name__ == "__main__":
    main()
