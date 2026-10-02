"""Independent trial checks using only supplied inputs and this run's outputs."""
from pathlib import Path
import csv
import hashlib
import json
import math
import statistics
import xml.etree.ElementTree as ET

from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
INPUTS, OUTPUT = ROOT / "inputs", ROOT / "attempt-01"


def table(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


source = table(INPUTS / "assay.csv")
plotted = table(OUTPUT / "plotting-data.csv")
cells = table(OUTPUT / "matrix-cells.csv")
marginals = table(OUTPUT / "marginal-data.csv")
settings, qa, stats = [read(OUTPUT / filename) for filename in ("settings.json", "qa.json", "stats.json")]
spec = read(INPUTS / "panel.json")
fields = list(source[0])
assert len(source) == len(plotted) == 41
assert [{field: row[field] for field in fields} for row in plotted] == source
assert [int(row["_easyviz_source_row"]) for row in plotted] == list(range(1, 42))
assert len(cells) == 42
keyed = {(row["row"], row["column"]): row for row in cells}
assert len(keyed) == 42
zero, unmeasured, absent = [keyed[key] for key in (("007", "010"), ("019", "003"), ("null", "025"))]
assert zero["state"] == "observed" and float(zero["value"]) == 0
assert unmeasured["state"] == "unmeasured" and unmeasured["value"] == ""
assert absent["state"] == "unsupplied" and absent["value"] == "" and absent["source_row"] == ""
assert {state: sum(row["state"] == state for row in cells) for state in ("observed", "unmeasured", "unsupplied")} == {"observed": 40, "unmeasured": 1, "unsupplied": 1}

means = {}
actual_means = {row["id"]: row for row in marginals}
assert list(actual_means) == spec["order"]["row"]
for row_id in spec["order"]["row"]:
    selected = [row for row in source if row["vessel_code"] == row_id]
    observed = [float(row["assay_delta"]) for row in selected if row["assay_status"] == "observed"]
    expected = statistics.mean(observed)
    actual = actual_means[row_id]
    assert math.isclose(float(actual["value"]), expected, abs_tol=1e-12)
    assert int(actual["observed_count"]) == len(observed)
    assert int(actual["grid_count"]) == 6
    assert int(actual["unmeasured_count"]) == (1 if row_id == "019" else 0)
    assert int(actual["unsupplied_count"]) == (1 if row_id == "null" else 0)
    assert actual["missing_rule"] == "omit"
    means[row_id] = {"expected_mean": expected, "actual_mean": float(actual["value"]), "denominator": len(observed)}

for binding in settings["inputs"].values():
    assert sha(Path(binding["path"])) == binding["sha256"]
assert sha(INPUTS / "panel.json") == settings["spec_file"]["sha256"]
assert settings["layout"]["actual_font"] == "Arial"
assert not settings["layout"]["font_substituted"]
assert settings["layout"]["font_size_pt"] == 8
assert all(settings["typography"][role] == 8 for role in ("axis", "tick", "legend", "annotation"))
assert qa["status"] == "pass" and qa["valid_outputs"]
assert qa["source_to_artist_audit"]["issues"] == []
assert not stats["tests_performed"] and not stats["clustering_performed"]
tree = read(INPUTS / "constructed-column-tree.json")
supplied = stats["supplied_dendrograms"]["column"]
assert supplied["display_order"] == tree["leaf_ids"] == spec["order"]["column"]
assert [branch["height"] for branch in supplied["branches"]] == [merge[2] for merge in tree["linkage"]]
assert [branch["count"] for branch in supplied["branches"]] == [merge[3] for merge in tree["linkage"]]
with Image.open(OUTPUT / "panel.png") as image:
    raster_pixels = list(image.size)
assert raster_pixels == [round(100 / 25.4 * 300), round(85 / 25.4 * 300)]
page = PdfReader(OUTPUT / "panel.pdf").pages[0]
pdf_dimensions = [float(page.mediabox.width) / 72 * 25.4, float(page.mediabox.height) / 72 * 25.4]
assert all(abs(a - b) < 1e-5 for a, b in zip(pdf_dimensions, [100, 85]))
svg = ET.parse(OUTPUT / "panel.svg").getroot()
svg_dimensions = [float(svg.attrib[k].removesuffix("pt")) / 72 * 25.4 for k in ("width", "height")]
assert all(abs(a - b) < 1e-5 for a, b in zip(svg_dimensions, [100, 85]))
svg_text = (OUTPUT / "panel.svg").read_text()
assert "Arial" in svg_text
assert all(identifier in svg_text for identifier in ["007", "019", "001", "035", "082", "NA", "null", "010", "003", "006", "040", "025"])
result = {"status": "pass", "input_rows": len(source), "plotted_source_rows": len(plotted), "displayed_grid_cells": len(cells), "literal_source_fields_retained": True, "states": {"observed": 40, "unmeasured": 1, "unsupplied": 1}, "observed_zero_preserved": True, "row_means_independently_recomputed": means, "source_bindings_valid": True, "actual_font": "Arial", "font_size_pt": 8, "raster_pixels": raster_pixels, "pdf_dimensions_mm": pdf_dimensions, "svg_dimensions_mm": svg_dimensions, "supplied_tree_preserved": True, "tests_performed": False, "clustering_performed": False, "scope": "Independent comparison of this trial's supplied inputs with its output tables/export dimensions. Source-to-artist strip/tree geometry is additionally covered by executed renderer QA and visual inspection; no implementation was inspected."}
(ROOT / "qa-independent.json").write_text(json.dumps(result, indent=2) + "\n")
(ROOT / "inputs-sha256.json").write_text(json.dumps({str(path.relative_to(ROOT)): sha(path) for path in sorted(INPUTS.iterdir())}, indent=2) + "\n")
print(json.dumps({"status": "pass", "checks": str(ROOT / "qa-independent.json")}))
