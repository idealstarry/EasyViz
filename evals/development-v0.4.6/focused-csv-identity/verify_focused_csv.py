"""Real focused exports prove literal-column shift rejection and legal parity."""
import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
LAYOUT = {"width_mm": 100, "height_mm": 80, "font": "DejaVu Sans", "font_size_pt": 8,
          "dpi": 160, "auto_fit": False, "margins": {"left": .22, "right": .83, "bottom": .23, "top": .86}}
CASES = {
    "replicate_plot": ("id,condition,value\n001,A,1.0\n002,A,3.00\n003,B,2.000\n004,B,2.500\n",
        {"chart": "replicate", "fields": {"unit": "id", "condition": "condition", "value": "value"},
         "options": {"mode": "summary", "uncertainty": "none", "y_limits": [0, 4]},
         "colors": {"A": "#29ACF3", "B": "#FF7D86"}}),
    "ecdf_plot": ("id,group,value\n001,A,1.0\n002,A,3.00\n003,B,2.000\n004,B,2.500\n",
        {"chart": "ecdf", "fields": {"unit": "id", "group": "group", "value": "value"},
         "options": {"x_limits": [0, 4]}, "colors": {"A": "#29ACF3", "B": "#FF7D86"}}),
    "interval_plot": ("label,est,lo,hi\nAlpha,1.0,0.50,1.500\nBeta,2.0,1.50,2.500\n",
        {"chart": "interval", "fields": {"label": "label", "estimate": "est", "lower": "lo", "upper": "hi"},
         "options": {"x_limits": [0, 3]}}),
    "timecourse_plot": ("minute,mean,sd,series\n1.0,1.0,0.20,A\n3.0,3.00,0.30,A\n1.0,2.000,0.20,B\n3.0,2.500,0.30,B\n",
        {"chart": "timecourse", "fields": {"x": "minute", "estimate": "mean", "sd": "sd", "series": "series"},
         "uncertainty": {"kind": "sd", "label": "Supplied SD"},
         "options": {"x_limits": [0, 4], "y_limits": [0, 4]},
         "colors": {"A": "#29ACF3", "B": "#FF7D86"}}),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name, root):
    loader = importlib.util.spec_from_file_location("csv_identity_" + root.name + name, root / (name + ".py"))
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


def specification(spec):
    return {**deepcopy(spec), "layout": deepcopy(LAYOUT), "formats": ["png", "pdf", "svg"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expect-refusal", action="store_true")
    args = parser.parse_args()
    if args.out.exists():
        raise RuntimeError("Existing evidence is immutable; choose a fresh folder")
    args.out.mkdir()
    result = {"runtime": str(args.runtime.resolve()), "cases": []}
    for name, (raw, base_spec) in CASES.items():
        module = load(name, args.runtime)
        spec = specification(base_spec)
        for variant in ("legal", "extra-leading-cell"):
            case = args.out / (name + "-" + variant)
            case.mkdir()
            content = raw if variant == "legal" else "\n".join(
                line if i == 0 else "extra," + line for i, line in enumerate(raw.rstrip().splitlines())) + "\n"
            source = case / "source.csv"
            source.write_text(content)
            path = case / "spec.json"
            path.write_text(json.dumps(spec, indent=2) + "\n")
            out = case / "output"
            preparation_error = None
            try:
                prepared = module.prepare(source, deepcopy(spec))
                parsed = prepared.to_csv(index=False)
            except module.SpecError as exc:
                preparation_error, parsed = str(exc), None
            error = None
            try:
                module.render(source, deepcopy(spec), out, spec_path=path)
            except module.SpecError as exc:
                error = str(exc)
            qa = json.loads((out / "qa.json").read_text())
            entry = {"recipe": name, "variant": variant, "runtime_sha256": digest(args.runtime / (name + ".py")),
                     "source_sha256": digest(source), "valid_outputs": qa["valid_outputs"], "error": error,
                     "prepared_table": parsed,
                     "preparation_error": preparation_error,
                     "exports": {suffix: digest(out / ("panel." + suffix))
                                 for suffix in spec["formats"] if (out / ("panel." + suffix)).exists()}}
            if (out / "elements.json").exists():
                entry["elements"] = json.loads((out / "elements.json").read_text())
            if (out / "plotting-data.csv").exists():
                entry["plotting_data"] = (out / "plotting-data.csv").read_text()
            if variant == "legal":
                assert error is None and qa["valid_outputs"], entry
            elif args.expect_refusal:
                assert error is not None and not qa["valid_outputs"] and not entry["exports"], entry
            result["cases"].append(entry)
            module.plt.close("all")
    result["all_cases_pass"] = True
    (args.out / "evidence.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"cases": len(result["cases"]), "all_cases_pass": True, "evidence": str(args.out / "evidence.json")}))


if __name__ == "__main__":
    main()
