"""Check that this styling revision preserves source and plotted quantities."""
from pathlib import Path
import io
import json
import subprocess

import numpy as np
import pandas as pd
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASELINE = "3e0a42d"
UNCHANGED_TABLES = [
    "examples/create/paired-effects/source.csv",
    "examples/create/paired-myeloid-remodeling/source-data.csv",
    "examples/create/paired-myeloid-remodeling/output/paired-changes.csv",
    "examples/create/paired-myeloid-remodeling/output/summary.csv",
    "examples/create/paired-myeloid-remodeling/output/participant-order.csv",
    "examples/create/paired-myeloid-remodeling/transfer-five-year/paired-changes.csv",
    "examples/create/paired-myeloid-remodeling/transfer-five-year/participant-order.csv",
    "examples/create/paired-myeloid-remodeling/transfer-five-year/summary.csv",
    "examples/create/annotated-inhibition/source-data.csv",
    "examples/create/annotated-inhibition/plotting-data.csv",
    "examples/create/annotated-inhibition/summary-data.csv",
    "examples/create/annotated-inhibition/genome-status.csv",
    "examples/create/annotated-inhibition/selection.csv",
    "examples/create/cell-atlas-dotplot/source-data.csv",
    "examples/create/cell-atlas-dotplot/output/plotted-data.csv",
]


def original(relative):
    return subprocess.check_output(["git", "show", f"{BASELINE}:{relative}"], cwd=ROOT)


def main():
    for relative in UNCHANGED_TABLES:
        assert original(relative) == (ROOT / relative).read_bytes(), f"Changed data: {relative}"
    forest = "examples/create/paired-effects/plotting-data.csv"
    old = pd.read_csv(io.BytesIO(original(forest)))
    new = pd.read_csv(ROOT / forest)
    pd.testing.assert_frame_equal(old.drop(columns="color"), new.drop(columns="color"))
    assert len(new) == 28 and new.term_id.nunique() == 14
    # Check the new non-size-weighted estimates still use the exact supplied CI.
    source = pd.read_csv(ROOT / "examples/create/paired-effects/source.csv")
    quantities = ["estimate", "ci_lower", "ci_upper", "n"]
    pd.testing.assert_frame_equal(new.set_index(["term_id", "cohort"])[quantities].sort_index(),
                                  source.set_index(["term_id", "cohort"])[quantities].sort_index())
    manifest = json.loads((HERE / "manifest.json").read_text())
    exports = {}
    for key, panel in manifest["panels"].items():
        pdf_path = (ROOT / panel["candidate"]).with_suffix(".pdf")
        # The four custom recipes retain the same declared canvas and all 8 pt text.
        expected = [180, 160 if key == "annotated-inhibition" else 125 if key == "paired-myeloid-remodeling" else 120]
        with pymupdf.open(pdf_path) as doc:
            assert len(doc) == 1
            page = doc[0]
            dimensions = [page.rect.width * 25.4 / 72, page.rect.height * 25.4 / 72]
            np.testing.assert_allclose(dimensions, expected, atol=.001)
            spans = [span for block in page.get_text("dict")["blocks"] if "lines" in block
                     for line in block["lines"] for span in line["spans"] if span["text"].strip()]
            assert spans and all(abs(span["size"] - 8) < .01 for span in spans)
            assert all(page.rect.contains(pymupdf.Rect(span["bbox"])) for span in spans)
            assert all(doc.extract_font(font[0])[3] for font in page.get_fonts())
        exports[key] = {"dimensions_mm": dimensions, "text_pt": 8, "text_within_canvas": True, "fonts_embedded": True}
    # Update the paired case's existing dimension record after the rerender.
    folder = ROOT / "examples/create/paired-myeloid-remodeling"
    verified = {}
    for relative in ["output/baseline/panel.pdf", "output/participant-matrix/panel.pdf",
                     "output/distribution-ledger/panel.pdf", "transfer-five-year/participant-matrix/panel.pdf"]:
        with pymupdf.open(folder / relative) as doc:
            page = doc[0]
            spans = [span for block in page.get_text("dict")["blocks"] if "lines" in block
                     for line in block["lines"] for span in line["spans"] if span["text"].strip()]
            sizes = sorted({round(span["size"], 3) for span in spans})
            assert sizes == [8.0]
            verified[relative] = {"font_sizes_pt": sizes, "fonts": sorted({span["font"] for span in spans}),
                                  "page_mm": [page.rect.width * 25.4 / 72, page.rect.height * 25.4 / 72]}
    (folder / "pdf-verification.json").write_text(json.dumps(verified, indent=2) + "\n")
    report = {
        "status": "pass", "baseline_commit": BASELINE,
        "unchanged_source_and_derived_tables": UNCHANGED_TABLES,
        "cohort_effect_plotting_table": "All columns except cosmetic color are identical; 28 supplied estimates and CIs retained.",
        "exports": exports,
        "scope": "Saved quantities and export correctness for these four cases. Independent image review assesses styling; this check is not an aesthetic or model benchmark.",
    }
    (HERE / "numeric-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": "pass", "unchanged_tables": len(UNCHANGED_TABLES), "exports": len(exports)}))


if __name__ == "__main__":
    main()
