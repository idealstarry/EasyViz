#!/usr/bin/env python3
"""Render individual outcome panels and a grouped alternative through public APIs."""
import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from compose import compose

HERE = Path(__file__).resolve().parent


def runtime_path(explicit=None):
    if explicit:
        path = Path(explicit).resolve()
        if not (path / "replicate_plot.py").is_file():
            raise FileNotFoundError("Pass the EasyViz scripts directory with sibling helpers intact.")
        return path
    for parent in HERE.parents:
        for relative in ("scripts", "skills/easyviz/scripts"):
            path = parent / relative
            if (path / "replicate_plot.py").is_file():
                return path
    raise FileNotFoundError("Supply --tools /path/to/easyviz/scripts.")


def renderer(tools):
    loader = importlib.util.spec_from_file_location("repair_outcomes_runtime", tools / "replicate_plot.py")
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", type=Path)
    parser.add_argument("--out", type=Path, default=HERE)
    parser.add_argument("--font")
    parser.add_argument("--transfer", action="store_true")
    args = parser.parse_args()
    plotter = renderer(runtime_path(args.tools))
    runs = [("candidate", HERE, args.out)]
    if args.transfer:
        runs.append(("transfer", HERE / "transfer", args.out / "transfer"))
    for name, source, destination in runs:
        spec_path = source / "spec.json"
        spec = deepcopy(json.loads(spec_path.read_text()))
        if args.font:
            spec["layout"]["font"] = args.font
        qa = plotter.render(source / "source-data.csv", spec, destination / "grouped-output", spec_path=spec_path)
        outputs = []
        for panel in json.loads((source / "panel-manifest.json").read_text())["panels"]:
            panel_spec_path = source / panel["spec"]
            panel_spec = json.loads(panel_spec_path.read_text())
            if args.font:
                panel_spec["layout"]["font"] = args.font
            panel_output = destination / "panels" / panel["id"] / "output"
            panel_qa = plotter.render(source / panel["source"], panel_spec, panel_output, spec_path=panel_spec_path)
            if panel_qa["status"] != "pass":
                raise SystemExit(1)
            outputs.append(panel_output)
        compose(outputs, destination / "output")
        print(json.dumps({"run": name, "status": qa["status"], "input_rows": qa["input_rows"], "panels": len(outputs), "output": str(destination.resolve())}))
        if qa["status"] != "pass":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
