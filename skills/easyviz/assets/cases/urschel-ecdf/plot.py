#!/usr/bin/env python3
"""Run the generic empirical cumulative-distribution recipe."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent


def runtime(explicit):
    if explicit:
        candidate = Path(explicit)
        return candidate / "ecdf_plot.py" if candidate.is_dir() else candidate
    for parent in HERE.parents:
        for candidate in (parent / "scripts/ecdf_plot.py", parent / "skills/easyviz/scripts/ecdf_plot.py"):
            if candidate.is_file():
                return candidate
    raise SystemExit("Provide --runtime /path/to/easyviz/scripts; keep copied cases in a writable project.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", type=Path, default=HERE / "source-data.csv")
    p.add_argument("--spec", type=Path, default=HERE / "spec.json")
    p.add_argument("--out", type=Path, default=HERE / "output")
    p.add_argument("--runtime", type=Path)
    p.add_argument("--font", help="Explicit font override, recorded in actual settings")
    a = p.parse_args()
    renderer = runtime(a.runtime)
    with tempfile.TemporaryDirectory(prefix="easyviz-case-spec-") as temporary:
        spec = a.spec
        if a.font:
            value = json.loads(spec.read_text())
            value.setdefault("layout", {})["font"] = a.font
            spec = Path(temporary) / "spec.json"
            spec.write_text(json.dumps(value, ensure_ascii=False))
        subprocess.run([sys.executable, str(renderer), "--data", str(a.data), "--spec", str(spec), "--out", str(a.out)], check=True)


if __name__ == "__main__":
    main()
