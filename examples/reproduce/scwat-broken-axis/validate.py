#!/usr/bin/env python3
"""Independently check source values against exported SVG/PDF circle geometry."""
import argparse
import csv
from decimal import Decimal, localcontext
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
SVG = "http://www.w3.org/2000/svg"


def rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as stream: return list(csv.DictReader(stream))


def validate_summary_domain(source, summaries):
    expected = {(row["gene"], row["group"]) for row in source}
    actual = [(row["gene"], row["group"]) for row in summaries]
    if not expected or len(set(actual)) != len(actual) or set(actual) != expected:
        raise ValueError("Actual mean/SEM summary identities are incomplete, duplicate or outside the source domain")


def validate(folder, inputs=None):
    import pymupdf
    from PIL import Image
    folder, inputs = Path(folder), Path(inputs) if inputs else HERE / "inputs"
    spec = json.loads((folder / "settings.json").read_text())
    source = rows(inputs / "observations.csv"); plotted = rows(folder / "plotting-data.csv"); summaries = rows(folder / "summary-data.csv")
    source_ids = {row["observation_id"]: row for row in source}
    plotted_ids = {row["observation_id"]: row for row in plotted}
    if len(source_ids) != len(source) or len(plotted_ids) != len(plotted) or set(source_ids) != set(plotted_ids): raise ValueError("Actual plotted observation identity/count changed")
    validate_summary_domain(source, summaries)
    numeric_errors, svg_errors, pdf_errors, summary_errors = [], [], [], []
    root = ET.parse(folder / "panel.svg").getroot(); nodes = {node.attrib["id"]: node for node in root.iter() if "id" in node.attrib}
    w, h = spec["layout"]["width_mm"], spec["layout"]["height_mm"]
    svg_mm = [float(root.attrib[key].removesuffix("pt")) / 72 * 25.4 for key in ("width", "height")]
    if not all(math.isclose(a, b, abs_tol=1e-5) for a, b in zip(svg_mm, (w, h))): raise ValueError("SVG changed physical dimensions")
    if not root.findall(f".//{{{SVG}}}text"): raise ValueError("SVG text is not editable")
    with pymupdf.open(folder / "panel.pdf") as doc:
        page = doc[0]
        pdf_mm = [page.rect.width / 72 * 25.4, page.rect.height / 72 * 25.4]
        if not all(math.isclose(a, b, abs_tol=1e-4) for a, b in zip(pdf_mm, (w, h))): raise ValueError("PDF changed physical dimensions")
        fonts = page.get_fonts()
        if not fonts or not all(doc.extract_font(item[0])[3] for item in fonts): raise ValueError("PDF fonts were not actually embedded")
        pdf_fonts = [{"name": item[3], "format": item[1], "type": item[2], "embedded_bytes": len(doc.extract_font(item[0])[3])} for item in fonts]
        font_sizes = sorted({round(span["size"], 4) for block in page.get_text("dict")["blocks"] if "lines" in block for line in block["lines"] for span in line["spans"] if span["text"].strip()})
        adopted_sizes = set(spec["typography"].values())
        if any(not any(math.isclose(size, adopted, abs_tol=.001) for adopted in adopted_sizes) for size in font_sizes):
            raise ValueError("Actual PDF text sizes differ from the explicitly adopted typography")
        circles = [drawing for drawing in page.get_drawings() if drawing.get("fill") and abs(drawing["rect"].width - drawing["rect"].height) < .01 and abs(drawing["rect"].width - spec["style"]["point_size_pt"]) < .02]
        if len(circles) != len(source): raise ValueError(f"PDF circle count {len(circles)} differs from all {len(source)} observations")
        unmatched = list(circles)
        g = spec["geometry_mm"]
        for row in source:
            identity = row["observation_id"]; actual = plotted_ids[identity]
            if Decimal(row["relative_expression"]) != Decimal(actual["relative_expression"]) or not math.isclose(float(actual["artist_y"]), float(row["relative_expression"]), abs_tol=1e-12): numeric_errors.append(identity)
            gene, group = row["gene"], row["group"]
            group_rows = [item for item in source if item["gene"] == gene and item["group"] == group]
            position = next(i for i, item in enumerate(group_rows) if item["observation_id"] == identity)
            bar_width, pair_gap = spec["style"]["bar_width"], spec["style"]["bar_gap"]
            x = spec["gene_order"].index(gene) + (-1 if spec["group_order"].index(group) == 0 else 1) * (bar_width + pair_gap) / 2
            x += (position / (len(group_rows) - 1) - .5) * bar_width * .65
            y = float(row["relative_expression"])
            segment = next((i for i, (a, b) in enumerate(spec["segments"]) if a <= y <= b), None)
            if segment is None: raise ValueError("A source point is hidden in the numeric gap")
            low, high = spec["segments"][segment]
            expected_x = g["left"] + (x + .6) / (len(spec["gene_order"]) + .2) * g["width"]
            expected_y = h - (g["bottom"] + segment * (g["segment_height"] + g["gap"]) + (y - low) / (high - low) * g["segment_height"])
            use = nodes[actual["artist_id"]].find(f".//{{{SVG}}}use")
            if use is None or not all(math.isclose(a, b, abs_tol=1e-4) for a, b in zip([float(use.attrib[key]) / 72 * 25.4 for key in ("x", "y")], (expected_x, expected_y))): svg_errors.append(identity)
            color = tuple(int(spec["colors"][group][i:i+2], 16) / 255 for i in (1, 3, 5))
            matched = next((circle for circle in unmatched if math.isclose((circle["rect"].x0 + circle["rect"].x1) / 2 / 72 * 25.4, expected_x, abs_tol=1e-4)
                            and math.isclose((circle["rect"].y0 + circle["rect"].y1) / 2 / 72 * 25.4, expected_y, abs_tol=1e-4)
                            and all(math.isclose(a, b, abs_tol=1e-5) for a, b in zip(color, circle["fill"]))), None)
            if matched is None: pdf_errors.append(identity)
            else: unmatched.remove(matched)
        with localcontext() as ctx:
            ctx.prec = 40
            for record in summaries:
                values = [Decimal(row["relative_expression"]) for row in source if row["gene"] == record["gene"] and row["group"] == record["group"]]
                mean = sum(values) / len(values); sem = (sum((value - mean) ** 2 for value in values) / (len(values) - 1)).sqrt() / Decimal(len(values)).sqrt()
                if int(record["n"]) != len(values) or any(not math.isclose(float(record[key]), float(value), abs_tol=1e-10) for key, value in (("artist_mean", mean), ("artist_lower", mean - sem), ("artist_upper", mean + sem))): summary_errors.append([record["gene"], record["group"]])
        pdf_text = page.get_text()
        if "Relative expression" not in pdf_text or any(group not in pdf_text for group in spec["group_order"]): raise ValueError("Actual PDF lost required labels")
    if numeric_errors or svg_errors or pdf_errors or summary_errors: raise ValueError(f"Source/vector fidelity failed: {numeric_errors, svg_errors, pdf_errors, summary_errors}")
    with Image.open(folder / "panel.png") as im:
        expected = tuple(round(v / 25.4 * spec["layout"]["dpi"]) for v in (w, h))
        if im.size != expected: raise ValueError("PNG pixel dimensions differ from physical size/dpi")
        png_size = list(im.size)
    manifest = json.loads((folder / "elements.json").read_text())
    observations = [element for element in manifest["elements"] if element["role"] == "observation"]
    if len(observations) != len(source) or {element["source_keys"][0]["observation_id"] for element in observations} != set(source_ids): raise ValueError("Selectable observations lost their source bindings")
    return {"status": "passed", "source_observations_checked": len(source), "actual_svg_circle_positions_checked": len(source), "actual_pdf_circle_positions_and_colors_checked": len(source),
            "summary_mean_sem_checked_independently": len(summaries), "selectable_source_observations": len(observations), "svg_mm": svg_mm, "pdf_mm": pdf_mm, "png_pixels": png_size,
            "pdf_fonts_embedded": True, "svg_text_editable": True, "cross_gene_pairing_inferred": False,
            "actual_pdf_fonts": pdf_fonts, "actual_pdf_text_sizes_pt": font_sizes, "adopted_typography": spec["typography"],
            "export_hashes": {fmt: hashlib.sha256((folder / f"panel.{fmt}").read_bytes()).hexdigest() for fmt in ("svg", "pdf", "png")},
            "limits": "Checks actual geometry/value fidelity, source identity and export properties; does not certify biological independence, upstream normalization, reported P calculations or aesthetic quality"}


def comparison(folder, reference=None):
    from PIL import Image, ImageDraw, ImageFont
    reference = Path(reference) if reference else HERE / "inputs/reference.png"
    images = [Image.open(reference).convert("RGB"), Image.open(Path(folder) / "panel.png").convert("RGB")]
    width, padding, header = 760, 22, 45
    previews = [image.resize((width, round(image.height * width / image.width)), Image.Resampling.LANCZOS) for image in images]
    height = max(image.height for image in previews)
    canvas = Image.new("RGB", (2 * width + 3 * padding, height + header + padding), "white")
    draw = ImageDraw.Draw(canvas)
    try: font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 23)
    except OSError: font = ImageFont.load_default(size=23)
    for i, (preview, label) in enumerate(zip(previews, ("Original · Fig. 2c", "Reproduce · 92 × 66 mm"))):
        x = padding + i * (width + padding)
        draw.text((x, 10), label, font=font, fill="#263238")
        canvas.paste(preview, (x, header + (height - preview.height) // 2))
    canvas.save(Path(folder) / "comparison.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "output")
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--comparison", action="store_true")
    args = parser.parse_args(); report = validate(args.out, args.inputs)
    if args.comparison: comparison(args.out)
    if args.report: args.report.parent.mkdir(parents=True, exist_ok=True); args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__": main()
