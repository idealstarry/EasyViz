#!/usr/bin/env python3
"""Render Figure 2b's traced observations with the generic paired recipe.

Use connectors-spec.json for an explicitly added within-person connector view.
Pass --runtime /path/to/easyviz/scripts after copying this case out of a plugin.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

BASE = Path(__file__).resolve().parent


def locate_runtime(explicit):
    if explicit is not None:
        script = explicit / "paired_plot.py" if explicit.is_dir() else explicit
        if script.is_file():
            return script.resolve()
        raise ValueError(f"No paired_plot.py runtime at {explicit}")
    for parent in (BASE, *BASE.parents):
        for relative in ("runtime/paired_plot.py", "scripts/paired_plot.py", "skills/easyviz/scripts/paired_plot.py"):
            candidate = parent / relative
            if candidate.is_file():
                return candidate
    raise ValueError("Pass --runtime /path/to/easyviz/scripts; keep its sibling helpers together.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=BASE / "source-data.csv")
    parser.add_argument("--spec", type=Path, default=BASE / "spec.json")
    parser.add_argument("--out", type=Path, default=BASE / "output")
    parser.add_argument("--font", help="Explicitly adopt an installed font; recorded in resolved settings")
    parser.add_argument("--runtime", type=Path)
    args = parser.parse_args()
    try:
        runtime = locate_runtime(args.runtime)
    except ValueError as exc:
        parser.error(str(exc))
    if args.font:
        spec = json.loads(args.spec.read_text())
        spec.setdefault("layout", {})["font"] = args.font
        with tempfile.TemporaryDirectory(prefix="easyviz-urschel-spec-") as temp:
            path = Path(temp) / "adopted-font-spec.json"
            path.write_text(json.dumps(spec, indent=2) + "\n")
            result = subprocess.call([sys.executable, str(runtime), "--data", str(args.data), "--spec", str(path), "--out", str(args.out)])
    else:
        result = subprocess.call([sys.executable, str(runtime), "--data", str(args.data), "--spec", str(args.spec), "--out", str(args.out)])
    raise SystemExit(result)


if __name__ == "__main__":
    main()
