#!/usr/bin/env python3
"""Copy image-only review packets; keep condition mapping outside reviewer packets."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import shutil

BASE = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=Path("/private/tmp/easyviz-v041-workbuddy"))
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--conditions", nargs="+", default=["baseline", "v040", "v041"])
    parser.add_argument("--tasks", nargs="+", choices=["create", "reproduce"], default=["create", "reproduce"])
    args = parser.parse_args()
    if args.destination.exists():
        raise SystemExit(f"Refusing to overwrite prior packet: {args.destination}")
    args.destination.mkdir(parents=True)
    mapping = {}
    for task in args.tasks:
        conditions = args.conditions.copy()
        random.SystemRandom().shuffle(conditions)
        packet = args.destination / task
        packet.mkdir()
        mapping[task] = {}
        for index, condition in enumerate(conditions):
            src = args.run_root / condition / task / "output/panel.png"
            if not src.is_file():
                raise SystemExit(f"Missing unmodified run PNG: {src}")
            name = f"Candidate-{index + 1}.png"
            shutil.copy2(src, packet / name)
            mapping[task][name] = {"condition": condition, "source_path": str(src),
                                   "sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
        if task == "reproduce":
            shutil.copy2(BASE / "fixtures/reproduce/reference.png", packet / "reference.png")
        scope = ("Create: 36 independent specimens in three groups (12 each), technical reads averaged per specimen. "
                 "The figure should communicate raw specimen distributions and changes relative to Vehicle. "
                 "No chart type was selected."
                 if task == "create" else
                 "Reproduce: adapt the supplied reference to 8 features × 9 specimens, with an aligned three-group "
                 "top strip, right per-feature mean layer, symmetric −2 to +2 diverging scale, and a missing-value key. "
                 "Target names differ from reference names; three cells are explicitly unmeasured.")
        (packet / "review-request.txt").write_text(
            "You are an image-only evaluator. The candidate identities, model, timings, code, numeric audit, "
            "and condition mapping are withheld from you. Inspect every actual PNG and the reference when supplied. "
            "Do not access other folders.\n\n" + scope + "\n\n"
            "All requested canvases are 120 × 90 mm and Arial 8 pt. On-screen rendering is not physical print proof. "
            "Rank candidates and score each dimension 0–4 (0 unusable, 1 major repair, 2 usable with repairs, "
            "3 good, 4 excellent): hierarchy, spacing/alignment, labels/readability, color/guide clarity, "
            "and reference-layer fidelity (reproduce only). Give concrete image evidence and at most three "
            "prioritized repairs per candidate. Ties are allowed. Do not infer numerical/statistical correctness "
            "from appearance; report suspected problems as uncertainties. State exactly which images you viewed "
            "and whether any identity information became visible.\n", encoding="utf-8")
    # Mapping is a sibling, outside all image-review task folders.
    key_path = args.destination.parent / f"{args.destination.name}-identity-key.json"
    key_path.write_text(json.dumps(mapping, indent=2) + "\n")
    print(args.destination)
    print(f"Evaluator-only mapping: {key_path}")


if __name__ == "__main__":
    main()
