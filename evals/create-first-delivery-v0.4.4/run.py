"""Render frozen new-data proposals without choosing an aesthetic winner."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RENDER_DEPENDENCIES = {
    "create_candidates.py", "create_style.py", "create_review.py", "render.py",
    "replicate_plot.py", "legend_layout.py", "figure_profile.py", "auto_layout.py",
    "annotation_review.py", "figure_elements.py", "panel_readability.py",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "outputs", help="A fresh replay directory; original evidence is never overwritten")
    parser.add_argument("--verify-frozen-only", action="store_true")
    parser.add_argument("--runtime-root", type=Path, default=HERE / "frozen-runtime",
                        help="Original frozen dependency tree; later engine changes do not rewrite this evaluation")
    args = parser.parse_args()
    runtime = args.runtime_root.resolve()
    frozen = json.loads((HERE / "input-freeze.json").read_text())
    for name, expected in frozen["implementation_hashes"].items():
        if Path(name).name in RENDER_DEPENDENCIES or name.endswith("assets/palettes/palettes.json"):
            assert hashlib.sha256((runtime / name).read_bytes()).hexdigest() == expected, name
    for case in frozen["cases"]:
        source = HERE / "inputs" / case["id"]
        for name, key in (("data.csv", "data_sha256"), ("spec.json", "spec_sha256"), ("caption.md", "caption_sha256")):
            assert hashlib.sha256((source / name).read_bytes()).hexdigest() == case[key]
    if args.verify_frozen_only:
        print(json.dumps({"status": "pass", "runtime_root": str(runtime), "scope": "Original frozen candidate/render/review dependency closure and palette; all original runtime hashes retained separately.", "cases": len(frozen["cases"])}))
        return
    path = runtime / "skills/easyviz/scripts/create_candidates.py"
    loader = importlib.util.spec_from_file_location("first_delivery_engine", path)
    engine = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(engine)
    outputs = args.out
    outputs.mkdir(parents=True, exist_ok=False)
    results = []
    for case in frozen["cases"]:
        source = HERE / "inputs" / case["id"]
        for name, key in (("data.csv", "data_sha256"), ("spec.json", "spec_sha256"),
                          ("caption.md", "caption_sha256")):
            assert hashlib.sha256((source / name).read_bytes()).hexdigest() == case[key]
        try:
            manifest = engine.create_candidates(source / "data.csv", source / "spec.json",
                                                outputs / case["id"], new_draft=True)
            result = {"id": case["id"], "status": manifest["status"],
                      "input_rows": manifest["features"]["input_rows"],
                      "inputs_unchanged": manifest["inputs_unchanged"],
                      "candidates": [{"id": item["id"], "technical_status": item["technical_review"]["status"],
                                      "aesthetic_review": "pending"} for item in manifest["candidates"]]}
        except (ValueError, OSError, ImportError) as exc:
            result = {"id": case["id"], "status": "failed", "error": str(exc)}
        results.append(result)
        (outputs / "results.json").write_text(json.dumps(results, indent=2) + "\n")
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
