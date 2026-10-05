"""Persist actual frozen-core/staged-core exports; compare geometry and QA."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]


def load(name, path):
    loader = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    destination = BASE / (sys.argv[1] if len(sys.argv) > 1 else "actual-export-verification")
    if destination.exists():
        raise RuntimeError("Use a new evidence directory; existing before/after records are immutable")
    before = load("endpoint_before", REPO / "skills/easyviz/scripts/render.py")
    after = load("endpoint_after", BASE / "staged-runtime/render.py")
    original = REPO / "evals/development-v0.4.5/runtime-audit/reproduced/06-numeric-marker-clipping"
    common = json.loads((original / "spec.json").read_text())
    common["formats"] = ["png", "svg", "pdf"]
    log = deepcopy(common)
    log["options"].update(x_scale="log", y_scale="log", x_limits=[1, 100], y_limits=[1, 100])
    hollow = deepcopy(common)
    hollow["options"].update(point_style="hollow", point_area_pt2=64, point_edge_width_pt=4)
    mapped = deepcopy(common)
    mapped["fields"]["size"] = "area"
    mapped["options"].pop("point_area_pt2")
    mapped["options"].update(size_max=1, max_area_pt2=100, size_legend=[.25, 1])
    cases = [("original-endpoints", (original / "input.csv").read_text(), common, True),
             ("inside-control", "x,y\n0.1,0.1\n0.5,0.5\n0.9,0.9\n", common, False),
             ("log-endpoints", "x,y\n1,1\n10,10\n100,100\n", log, True),
             ("hollow-edge", f"x,y\n{1.75 / (.58 * 88)},0.5\n", hollow, True),
             ("mapped-area", "x,y,area\n0,0,1\n0.5,0.5,0.25\n1,1,0\n", mapped, True)]
    record = {"before_renderer_sha256": digest(Path(before.__file__)),
              "after_renderer_sha256": digest(Path(after.__file__)),
              "after_clipping_helper_sha256": digest(BASE / "staged-runtime/observation_clipping.py"),
              "original_reproduction_qa_sha256": digest(original / "output/qa.json"), "cases": []}
    for name, text, spec, should_fail in cases:
        case = destination / name
        case.mkdir(parents=True)
        data, spec_path = case / "input.csv", case / "spec.json"
        data.write_text(text)
        spec_path.write_text(json.dumps(spec, indent=2) + "\n")
        row = {"case": name, "expected_confirmed_clipping": should_fail}
        for label, renderer in [("before", before), ("after", after)]:
            out = case / label
            try:
                renderer.render_spec_file(data, spec_path, out)
                row[label + "_exception"] = None
            except renderer.SpecError as exc:
                row[label + "_exception"] = str(exc)
            qa = json.loads((out / "qa.json").read_text())
            settings = json.loads((out / "settings.json").read_text())
            row[label] = {"qa_status": qa["status"], "valid_outputs": qa["valid_outputs"],
                          "source_csv_sha256": digest(out / "source-data.csv"),
                          "input_sha256": qa["input_sha256"],
                          "options": settings["options"], "mark_geometry": settings["mark_geometry"],
                          "exports": {suffix: digest(out / ("panel." + suffix)) for suffix in common["formats"]}}
            if label == "after":
                row[label]["observation_clipping"] = qa["observation_clipping"]
        row["unchanged_exports"] = {suffix: row["before"]["exports"][suffix] == row["after"]["exports"][suffix]
                                    for suffix in common["formats"]}
        assert row["before"]["valid_outputs"] is True
        assert row["after"]["valid_outputs"] is not should_fail
        assert row["before"]["options"] == row["after"]["options"] == spec["options"]
        assert row["before"]["mark_geometry"] == row["after"]["mark_geometry"]
        assert row["before"]["source_csv_sha256"] == row["after"]["source_csv_sha256"] == digest(data)
        assert all(row["unchanged_exports"].values()), row["unchanged_exports"]
        record["cases"].append(row)
    record["all_cases_pass"] = True
    (destination / "evidence.json").write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"all_cases_pass": True, "cases": len(cases), "evidence": str(destination / "evidence.json")}))


if __name__ == "__main__":
    main()
