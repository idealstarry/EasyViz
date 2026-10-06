from pathlib import Path
import argparse, subprocess
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[3]
parser=argparse.ArgumentParser();parser.add_argument('--out',default='replay');args=parser.parse_args()
subprocess.run([str(REPO/'.venv/bin/python'),str(ROOT/'plot.py'),'--out',args.out],check=True)
