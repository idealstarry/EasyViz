#!/usr/bin/env python3
"""Run the five basic panels through the public EasyViz plotting APIs.

Default: render the final candidate panels. --comparisons also reruns the
declared legacy-spec baseline and one bounded, real-source transfer per case.
No custom figure renderer, new test, value imputation, or inferred pairing.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def runtime_path(explicit):
    if explicit:
        path = Path(explicit).resolve()
        if (path / "render.py").is_file():
            return path
        raise FileNotFoundError(f"No render.py in supplied --tools directory: {path}")
    for parent in HERE.parents:
        for relative in ("scripts", "skills/easyviz/scripts"):
            candidate = parent / relative
            if (candidate / "render.py").is_file():
                return candidate
    raise FileNotFoundError("Pass --tools /path/to/easyviz/scripts with sibling helpers intact.")


def module(path, name):
    loader = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", type=Path)
    parser.add_argument("--case", default="all")
    parser.add_argument("--font", help="Explicit installed font override; saved settings record the choice.")
    parser.add_argument("--out", type=Path, help="Write case outputs under this writable directory.")
    parser.add_argument("--comparisons", action="store_true")
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument("--transfers", action="store_true", help="Render candidates and transfer probes while preserving the frozen baseline.")
    args = parser.parse_args()
    tools = runtime_path(args.tools)
    core = module(tools / "render.py", "basic_panel_core")
    replicate = module(tools / "replicate_plot.py", "basic_panel_replicate")
    cases = json.loads((HERE / "manifest.json").read_text())["cases"]
    if args.case != "all":
        cases = [case for case in cases if case["id"] == args.case]
        if not cases:
            parser.error(f"Unknown case: {args.case}")
    records = []
    for case in cases:
        folder = HERE / case["id"]
        destination = (args.out.resolve() / case["id"]) if args.out else folder
        runs = [("candidate", folder / "source-data.csv", folder / "candidate-spec.json", destination / "output")]
        if args.comparisons or args.baseline_only:
            runs.insert(0, ("baseline", folder / "source-data.csv", folder / "baseline-spec.json", destination / "first-render"))
        if args.baseline_only:
            runs = runs[:1]
        elif args.comparisons or args.transfers:
            runs.append(("transfer", folder / "transfer/source-data.csv", folder / "transfer/spec.json", destination / "transfer/output"))
        renderer = replicate if case["renderer"] == "replicate_plot.py" else core
        for role, data, spec_path, out in runs:
            spec = deepcopy(json.loads(spec_path.read_text()))
            if args.font:
                spec["layout"]["font"] = args.font
            kwargs = {"spec_path": spec_path}
            if renderer is core:
                kwargs["track"] = "create"
            qa = renderer.render(data, spec, out, **kwargs)
            record = {"case": case["id"], "run": role, "status": qa["status"], "input_rows": qa["input_rows"], "output": str(out)}
            print(json.dumps(record), flush=True)
            records.append(record)
    return records


if __name__ == "__main__":
    main()
