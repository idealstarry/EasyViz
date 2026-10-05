#!/usr/bin/env python3
"""Preserve actual post-repair exports for the three publication-blocking P1s."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / (sys.argv[1] if len(sys.argv) > 1 else "repaired")
SCRIPTS = ROOT / "skills/easyviz/scripts"


def module(name, filename):
    loader = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    result = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(result)
    return result


core = module("runtime_repair_core", "render.py")
review = module("runtime_repair_review", "create_review.py")


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def case(name, body, spec):
    folder = OUT / name
    folder.mkdir(exist_ok=False)
    source = folder / "input.csv"
    source.write_text(body)
    save(folder / "spec.json", spec)
    (folder / "caption.md").write_text("Repair verification only; no inferential tests or aesthetic efficacy claim.\n")
    return folder, source


SCATTER = {"chart": "scatter", "fields": {"x": "x", "y": "y"},
           "layout": {"width_mm": 88, "height_mm": 66, "font": "DejaVu Sans", "dpi": 160},
           "labels": {"x": "X", "y": "Y"}, "formats": ["png", "svg", "pdf"]}


def main():
    OUT.mkdir(exist_ok=False)
    results = {}
    folder, source = case("source-race", "x,y\n1,2\n2,3\n3,5\n4,4\n", SCATTER)
    before = source.read_bytes()
    original_export = core.export
    def changed(fig, out, spec, layout):
        source.write_text("x,y\n1,200\n2,300\n3,500\n4,400\n")
        return original_export(fig, out, spec, layout)
    core.export = changed
    try:
        core.render(source, deepcopy(SCATTER), folder / "output", spec_path=folder / "spec.json", track="create")
        raise AssertionError("Source replacement must fail")
    except core.SpecError as exc:
        error = str(exc)
    finally:
        core.export = original_export
    snapshot = review.snapshot(folder / "output", caption=folder / "caption.md")
    save(folder / "review-snapshot.json", snapshot)
    qa = json.loads((folder / "output/qa.json").read_text())
    elements = json.loads((folder / "output/elements.json").read_text())
    captured = hashlib.sha256(before).hexdigest()
    assert qa["valid_outputs"] is False
    assert elements["version"]["input_sha256"] == captured
    assert (folder / "output/source-data.csv").read_bytes() == before
    assert snapshot["measured_checks"]["source_provenance"]["status"] == "failed"
    results["source-race"] = {"error": error, "qa_status": qa["status"], "valid_outputs": qa["valid_outputs"],
                              "captured_old_source_hash": captured, "saved_element_source_hash": elements["version"]["input_sha256"],
                              "review_source_provenance": snapshot["measured_checks"]["source_provenance"]["status"]}
    for name, body in (("ragged", "x,y\n1,2,9\n2,4,8\n3,6,7\n"),
                       ("duplicate-header", "x,y,y\n1,2,200\n2,3,300\n")):
        folder, source = case(name, body, SCATTER)
        try:
            core.render(source, deepcopy(SCATTER), folder / "output", spec_path=folder / "spec.json")
            raise AssertionError("Malformed CSV must fail")
        except core.SpecError as exc:
            error = str(exc)
        qa = json.loads((folder / "output/qa.json").read_text())
        assert qa["valid_outputs"] is False and not (folder / "output/panel.png").exists()
        results[name] = {"error": error, "qa_status": qa["status"], "valid_outputs": qa["valid_outputs"], "panel_exported": False}
    spec = {"chart": "composition", "fields": {"sample": "sample", "category": "category", "value": "value"},
            "options": {"normalization": "sample_sum"}, "layout": {**SCATTER["layout"], "auto_fit": True},
            "formats": ["png", "svg", "pdf"]}
    for name, first, second, expected in (("float-sum", "1e308", "1e308", [.5, .5]),
                                          ("integer-sum", "18000000000000000000", "1000000000000000000", [18 / 19, 1 / 19])):
        folder, source = case(name, f"sample,category,value\nA,c1,{first}\nA,c2,{second}\n", spec)
        raw = source.read_bytes()
        qa = core.render(source, deepcopy(spec), folder / "output", spec_path=folder / "spec.json", track="create")
        data = core.pd.read_csv(folder / "output/plotting-data.csv", dtype={"_easyviz_denominator_text": str}, keep_default_na=False)
        actual = data["_easyviz_plotted_value"].tolist()
        assert core.np.allclose(actual, expected, rtol=1e-14, atol=0)
        assert qa["valid_outputs"] and (folder / "output/source-data.csv").read_bytes() == raw
        with core.Image.open(folder / "output/panel.png") as image:
            image.load()
        results[name] = {"qa_status": qa["status"], "valid_outputs": qa["valid_outputs"], "fractions": actual,
                         "expected_fractions": expected, "fraction_sum": sum(actual),
                         "exact_denominator_text": data["_easyviz_denominator_text"].astype(str).tolist(),
                         "literal_source_snapshot_matches": True}
    save(OUT / "results.json", {"scope": "Actual P1 repair evidence, not an aesthetic or generalization benchmark",
                                "runtime_hashes": {name: hashlib.sha256((SCRIPTS / name).read_bytes()).hexdigest() for name in ("render.py", "figure_elements.py", "create_review.py")},
                                "results": results})
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
