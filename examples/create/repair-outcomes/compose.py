"""Place already exported PDF/SVG panels side by side at their original size.

Composition never rescales fonts, redraws data or adds statistical layers.
Individual public-renderer exports remain the manuscript deliverables.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pymupdf

SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)


def compose(outputs, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    pdf = pymupdf.open()
    sources = [pymupdf.open(folder / "panel.pdf") for folder in outputs]
    try:
        widths = [source[0].rect.width for source in sources]
        height = max(source[0].rect.height for source in sources)
        page = pdf.new_page(width=sum(widths), height=height)
        combined = ET.Element(f"{{{SVG}}}svg", {"version": "1.1", "width": f"{sum(widths)}pt",
                             "height": f"{height}pt", "viewBox": f"0 0 {sum(widths)} {height}"})
        left = 0
        records = []
        for index, (folder, source, width) in enumerate(zip(outputs, sources, widths)):
            rect = pymupdf.Rect(left, 0, left + width, source[0].rect.height)
            page.show_pdf_page(rect, source, 0)
            root = ET.parse(folder / "panel.svg").getroot()
            view = list(map(float, root.attrib["viewBox"].split()))
            assert abs(view[2] - width) < .001 and abs(view[3] - source[0].rect.height) < .001
            # Renderer-generated SVG only. Distinct prefixes prevent clip-path
            # and marker definitions from referring to another panel's IDs.
            ids = {node.attrib["id"]: f"p{index}-{node.attrib['id']}" for node in root.iter() if "id" in node.attrib}
            group = ET.SubElement(combined, f"{{{SVG}}}g", {"transform": f"translate({left} 0)"})
            for child in root:
                clone = deepcopy(child)
                for node in clone.iter():
                    for key, value in list(node.attrib.items()):
                        if key == "id":
                            node.attrib[key] = ids[value]
                        elif value.startswith("#") and value[1:] in ids:
                            node.attrib[key] = "#" + ids[value[1:]]
                        else:
                            node.attrib[key] = re.sub(r"url\(#([^)]*)\)", lambda m: "url(#" + ids.get(m[1], m[1]) + ")", value)
                group.append(clone)
            records.append({"panel": str(folder), "offset_pt": left, "width_pt": width,
                            "height_pt": source[0].rect.height,
                            "pdf_sha256": hashlib.sha256((folder / "panel.pdf").read_bytes()).hexdigest()})
            left += width
        pdf.save(destination / "panel.pdf", garbage=4, deflate=True, no_new_id=True)
        ET.ElementTree(combined).write(destination / "panel.svg", encoding="utf-8", xml_declaration=True)
        page.get_pixmap(dpi=300).save(destination / "panel.png")
        page.get_pixmap(dpi=96).save(destination / "pdf-preview-96dpi.png")
        (destination / "composition.json").write_text(json.dumps({"status": "pass", "source_panels": records,
            "data_redrawn": False, "panels_rescaled": False, "font_size_changed": False,
            "caption_separate": True, "note": "Nominal-size vector row preview; compare treatment effects within each separately labeled outcome range."}, indent=2) + "\n")
    finally:
        pdf.close()
        for source in sources:
            source.close()
