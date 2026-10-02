#!/usr/bin/env python3
"""Plot selected Source Data using EasyViz's reusable replicate recipe."""
import argparse
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent


def locate_runtime(explicit):
    if explicit is not None:
        script = explicit / "replicate_plot.py" if explicit.is_dir() else explicit
        if script.is_file():
            return script.resolve()
        raise ValueError(f"No replicate_plot.py runtime at {explicit}")
    for parent in (BASE, *BASE.parents):
        for relative in ("runtime/replicate_plot.py", "scripts/replicate_plot.py", "skills/easyviz/scripts/replicate_plot.py"):
            candidate = parent / relative
            if candidate.is_file():
                return candidate
    raise ValueError("Pass --runtime /path/to/easyviz/scripts and preserve its sibling helpers.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=BASE / "inputs/components.csv")
    parser.add_argument("--spec", type=Path, default=BASE / "components-spec.json")
    parser.add_argument("--out", type=Path, default=BASE / "output-components")
    parser.add_argument("--runtime", type=Path)
    args = parser.parse_args()
    try:
        runtime = locate_runtime(args.runtime)
    except ValueError as exc:
        parser.error(str(exc))
    raise SystemExit(subprocess.call([sys.executable, str(runtime), "--data", str(args.data), "--spec", str(args.spec), "--out", str(args.out)]))


if __name__ == "__main__":
    main()
