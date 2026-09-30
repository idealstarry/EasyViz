#!/usr/bin/env python3
"""Independent physical-export and source-snapshot checks for this fixed pilot.

This is an evaluation companion, not a plugin runtime or installer dependency.
Source fidelity in figure artist arrays is checked by the separate recorded audit.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
EXPECTED_MM = (90.0, 70.0)
EXPECTED_PT = tuple(x / 25.4 * 72.0 for x in EXPECTED_MM)


def svg_points(value: str) -> float:
    match = re.fullmatch(r"([\d.]+)(pt|mm|in|px)?", value)
    if not match:
        raise ValueError(f"Unsupported SVG physical dimension: {value}")
    amount = float(match[1])
    return amount * {"pt": 1.0, "mm": 72 / 25.4, "in": 72.0, "px": 0.75, None: 0.75}[match[2]]


def measure(path: Path) -> dict:
    result = {"path": str(path.relative_to(ROOT))}
    if path.suffix == ".png":
        with Image.open(path) as im:
            dpi = im.info.get("dpi")
            result.update(pixels=list(im.size), dpi=list(dpi) if dpi else None)
            if dpi:
                result["physical_mm"] = [round(n / d * 25.4, 6) for n, d in zip(im.size, dpi)]
                # Raster rounding can move a boundary by up to one 300-dpi pixel.
                result["size_pass"] = all(abs(a - b) <= 25.4 / 300 for a, b in zip(result["physical_mm"], EXPECTED_MM))
                result["dpi_pass"] = all(abs(d - 300) < 0.05 for d in dpi)
            else:
                result.update(size_pass=False, dpi_pass=False)
    elif path.suffix == ".pdf":
        pdf = PdfReader(path)
        dims = [float(pdf.pages[0].mediabox.width), float(pdf.pages[0].mediabox.height)]
        result.update(pages=len(pdf.pages), physical_points=dims, size_pass=len(pdf.pages) == 1 and all(abs(a - b) < 0.01 for a, b in zip(dims, EXPECTED_PT)))
        resources = pdf.pages[0].get("/Resources", {})
        font_objects = resources.get("/Font", {})
        fonts = [str(font.get_object().get("/BaseFont", "")) for font in font_objects.values()]
        result["embedded_font_names"] = fonts
        result["arial_font_pass"] = bool(fonts) and all("Arial" in font for font in fonts)
    elif path.suffix == ".svg":
        xml = ET.parse(path).getroot()
        dims = [svg_points(xml.attrib[k]) for k in ("width", "height")]
        result.update(physical_points=dims, view_box=xml.attrib.get("viewBox"), size_pass=all(abs(a - b) < 0.01 for a, b in zip(dims, EXPECTED_PT)))
        text_nodes = list(xml.iter("{http://www.w3.org/2000/svg}text"))
        result["text_nodes"] = len(text_nodes)
        style = " ".join(n.attrib.get("style", "") for n in text_nodes)
        explicit_sizes = re.findall(r"font-size:\s*([\d.]+)px", style)
        result["explicit_text_sizes_px"] = sorted(set(float(s) for s in explicit_sizes))
        result["arial_in_svg_text_style"] = "Arial" in style if text_nodes else None
    return result


def verify() -> dict:
    source_provenance = json.loads((ROOT / "inputs/provenance.json").read_text())
    sources = []
    for item in source_provenance:
        path = ROOT / item["derived_file"]
        rows = list(csv.DictReader(path.open()))
        sources.append({"path": item["derived_file"], "sha256_pass": hashlib.sha256(path.read_bytes()).hexdigest() == item["derived_sha256"], "rows": len(rows), "row_count_pass": len(rows) == item["rows"]})
    paths = sorted(p for arm in ("baseline", "easyviz") for p in (ROOT / arm).rglob("*") if p.suffix in (".png", ".pdf", ".svg") and "96dpi" not in p.name and ("initial" in p.parts or "final" in p.parts))
    exports = [measure(path) for path in paths]
    final_exports = [r for r in exports if "/final/" in r["path"]]
    passed = len(final_exports) == 12 and all(r["size_pass"] and r.get("dpi_pass", True) and r.get("arial_font_pass", True) for r in final_exports) and all(r["sha256_pass"] and r["row_count_pass"] for r in sources)
    return {"expected_canvas_mm": list(EXPECTED_MM), "expected_font_pt": 8, "sources": sources, "exports": exports, "final_export_count": len(final_exports), "physical_size_dpi_pdf_font_and_source_hash_pass": passed, "scope_note": "This check confirms files, physical dimensions, PNG resolution, PDF font identities and frozen source integrity. Scientific artist-array checks and actual 8 pt typography are recorded separately; editable SVG text may be absent when text is outlined."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "export-verification.json")
    args = parser.parse_args()
    result = verify()
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"final_export_count": result["final_export_count"], "pass": result["physical_size_dpi_pdf_font_and_source_hash_pass"]}))
    raise SystemExit(0 if result["physical_size_dpi_pdf_font_and_source_hash_pass"] else 1)
