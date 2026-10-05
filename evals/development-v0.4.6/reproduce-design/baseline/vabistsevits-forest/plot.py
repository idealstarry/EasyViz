#!/usr/bin/env python3
"""Render supplied estimates with the shared EasyViz interval recipe.

The default is the total-effect panel. Select panel b's CSV and spec explicitly.
Use --runtime /path/to/easyviz/scripts after copying this case out of a plugin.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent


def locate_runtime(explicit: Path | None) -> Path:
    if explicit is not None:
        script = explicit / "interval_plot.py" if explicit.is_dir() else explicit
        if script.is_file():
            return script.resolve()
        raise ValueError(f"No interval_plot.py runtime at {explicit}")
    for parent in (BASE, *BASE.parents):
        for relative in ("runtime/interval_plot.py", "scripts/interval_plot.py",
                         "skills/easyviz/scripts/interval_plot.py"):
            candidate = parent / relative
            if candidate.is_file():
                return candidate
    raise ValueError("Pass --runtime /path/to/easyviz/scripts; keep its sibling helpers together.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=BASE / "inputs/source-data-a.csv")
    parser.add_argument("--spec", type=Path, default=BASE / "panel-a-spec.json")
    parser.add_argument("--out", type=Path, default=BASE / "output-a")
    parser.add_argument("--runtime", type=Path, help="EasyViz scripts directory, or interval_plot.py")
    args = parser.parse_args()
    try:
        runtime = locate_runtime(args.runtime)
    except ValueError as exc:
        parser.error(str(exc))
    raise SystemExit(subprocess.call([sys.executable, str(runtime), "--data", str(args.data),
                                      "--spec", str(args.spec), "--out", str(args.out)]))


if __name__ == "__main__":
    main()
