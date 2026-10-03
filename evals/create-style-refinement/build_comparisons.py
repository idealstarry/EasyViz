"""Build review boards from exact baseline/current PNGs; no chart edits.

Run from the development checkout. Each source panel remains available in its
original manuscript export; these boards show the same 720 px presentation
width used by the main README, without changing manuscript dimensions.
"""
from pathlib import Path
import hashlib
import io
import json
import os
import subprocess
import tempfile

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "easyviz-create-review-mpl"))
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASELINE = "3e0a42d"
PANELS = {
    "paired-myeloid-remodeling": "examples/create/paired-myeloid-remodeling/output/distribution-ledger/panel.png",
    "annotated-inhibition": "examples/create/annotated-inhibition/panel.png",
    "cell-atlas-dotplot": "examples/create/cell-atlas-dotplot/output/figure.png",
    "paired-effects": "examples/create/paired-effects/panel.png",
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    font = ImageFont.truetype(font_manager.findfont("Arial"), 18)
    records = {}
    for key, relative in PANELS.items():
        old_bytes = subprocess.check_output(["git", "show", f"{BASELINE}:{relative}"], cwd=ROOT)
        new_bytes = (ROOT / relative).read_bytes()
        (HERE / "baseline").mkdir(exist_ok=True)
        old_path = HERE / "baseline" / f"{key}.png"
        old_path.write_bytes(old_bytes)
        images = [Image.open(io.BytesIO(raw)).convert("RGB") for raw in (old_bytes, new_bytes)]
        assert images[0].size == images[1].size, f"Changed pixel canvas: {key}"
        width = 720
        height = round(width * images[0].height / images[0].width)
        board = Image.new("RGB", (width * 2 + 48, height + 64), "white")
        draw = ImageDraw.Draw(board)
        draw.text((16, 14), f"Before · {BASELINE}", font=font, fill="#53636F")
        draw.text((width + 32, 14), "After · same source and canvas", font=font, fill="#25343F")
        for image, x in zip(images, (16, width + 32)):
            board.paste(image.resize((width, height), Image.Resampling.LANCZOS), (x, 48))
        (HERE / "comparisons").mkdir(exist_ok=True)
        board_path = HERE / "comparisons" / f"{key}.png"
        board.save(board_path)
        records[key] = {
            "baseline": str(old_path.relative_to(ROOT)), "baseline_sha256": digest(old_bytes),
            "candidate": relative, "candidate_sha256": digest(new_bytes),
            "original_pixels": list(images[0].size), "display_width_px_each": width,
            "comparison": str(board_path.relative_to(ROOT)), "comparison_sha256": digest(board_path.read_bytes()),
        }
    (HERE / "manifest.json").write_text(json.dumps({
        "baseline_commit": BASELINE,
        "scope": "Four README Create panels, exact before/after PNGs at equal display width; no model benchmark.",
        "panels": records,
    }, indent=2) + "\n")
    print(json.dumps({"panels": len(records), "manifest": str(HERE / "manifest.json")}))


if __name__ == "__main__":
    main()
