#!/usr/bin/env python3
"""Forward checks against unchanged original failure and successful artifacts."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "skills/easyviz/scripts/create_review.py"
loader = importlib.util.spec_from_file_location("current_png_review", SOURCE)
review = importlib.util.module_from_spec(loader)
loader.loader.exec_module(review)

failed = ROOT / "evals/development-v0.4.5/runtime-audit/reproduced/07-png-no-image-payload/output/panel.png"
packet = ROOT / "evals/create-purpose-overhaul-v0.4.4/fresh-run/with-skill/attempt-02/create-review/pass-02/packet.json"
raw = failed.read_bytes()
try:
    review.png_measurement(raw)
except review.ReviewError as exc:
    rejected = str(exc)
else:
    raise AssertionError("The original no-pixel PNG must be rejected")
legacy = review.check(packet)
assert legacy["gate_status"] == "recorded" and not legacy["errors"], legacy
result = {
    "scope": "Scanline/physical-metadata integrity and an unchanged legacy review; no appearance or exhaustive PNG conformance claim.",
    "review_source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "original_no_pixel_png": {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "error": rejected},
    "unchanged_successful_review": legacy,
    "original_artifacts_modified": False,
}
print(json.dumps(result, indent=2))
