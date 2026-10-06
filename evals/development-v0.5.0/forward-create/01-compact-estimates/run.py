from pathlib import Path
import argparse, subprocess
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[3]
parser=argparse.ArgumentParser();parser.add_argument('--out',default='replay');args=parser.parse_args()
out=(ROOT/args.out).resolve()
if out.exists():raise SystemExit('Use a fresh --out directory to preserve existing artifacts.')
subprocess.run([str(REPO/'.venv/bin/python'),str(REPO/'skills/easyviz/scripts/replicate_plot.py'),'--data','/Users/starry/Desktop/EasyViz/evals/development-v0.5.0/forward-inputs/01-compact-estimates/measurements.csv','--spec',str(ROOT/'adopted-spec.json'),'--out',str(out)]+[],check=True)
