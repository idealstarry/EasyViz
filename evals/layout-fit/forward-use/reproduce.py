#!/usr/bin/env python3
"""Render the delivered dot plot from the unchanged prepared table."""
from pathlib import Path
import os, subprocess, sys
root = Path(__file__).resolve().parent
output = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / "reproduced"
env = os.environ.copy()
env["MPLCONFIGDIR"] = str(root / ".mplconfig")
subprocess.run([sys.executable, str(root / "easyviz/scripts/render.py"),
    "--data", str(root / "prepared.csv"), "--spec", str(root / "plot.json"),
    "--out", str(output)], check=True, env=env)
