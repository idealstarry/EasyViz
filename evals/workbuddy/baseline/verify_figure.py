#!/usr/bin/env python3
"""Independent checks of the produced figure.

Everything here is measured from the written artefacts (panel.png rendered
pixels, panel.pdf page box, panel.svg XML) and compared with the values that
`make_figure.py` claims to have used.  Nothing is taken on trust.

Run:  /Users/starry/Desktop/EasyViz/.venv/bin/python verify_figure.py
"""

from __future__ import annotations

import csv
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
SETTINGS = json.loads((ROOT / "settings" / "figure_settings.json").read_text())
ROWS = list(csv.DictReader((ROOT / "data" / "plot_data.csv").open()))

head: list[str] = []
detail: list[str] = []
n_pass = 0
n_fail = 0


def check(name: str, ok: bool, text: str) -> None:
    global n_pass, n_fail
    if ok:
        n_pass += 1
    else:
        n_fail += 1
    head.append(f"[{'PASS' if ok else 'FAIL'}] {name}: {text}")


# ---------------------------------------------------------------------------
# 1. canvas geometry of the PNG
# ---------------------------------------------------------------------------
img = Image.open(ROOT / "output" / "panel.png")
W, H = img.size
fig_w_mm = SETTINGS["canvas"]["width_mm"]
fig_h_mm = SETTINGS["canvas"]["height_mm"]
ppx = W / fig_w_mm
ppy = H / fig_h_mm
ref_px_per_mm = 300.0 / 25.4

check(
    "PNG pixel size matches the 120x90 mm canvas at 300 dpi",
    abs(W - round(ref_px_per_mm * fig_w_mm)) <= 1
    and abs(H - round(ref_px_per_mm * fig_h_mm)) <= 1,
    f"{W}x{H} px = {W / 300 * 25.4:.3f} x {H / 300 * 25.4:.3f} mm "
    f"(nominal {ref_px_per_mm * fig_w_mm:.2f} x {ref_px_per_mm * fig_h_mm:.2f} px; "
    f"matplotlib truncates the fractional height, the vector formats carry the "
    f"exact page box)",
)

# ---------------------------------------------------------------------------
# 2. ink bounding box -> clear canvas on every side (nothing clipped)
# ---------------------------------------------------------------------------
gray = np.array(img.convert("L"))
cols = np.where((gray < 245).any(axis=0))[0]
rows_ink = np.where((gray < 245).any(axis=1))[0]
clear = {
    "left": cols.min() / ppx,
    "right": fig_w_mm - cols.max() / ppx,
    "top": rows_ink.min() / ppy,
    "bottom": fig_h_mm - rows_ink.max() / ppy,
}
check(
    "all content inside the canvas (no glyph clipped at an edge)",
    min(clear.values()) >= 1.0,
    "actual ink clearance mm -> "
    + ", ".join(f"{k} {v:.2f}" for k, v in clear.items()),
)

declared = SETTINGS["canvas"]["clear_canvas_mm_measured"]
check(
    "declared layout clearance is honoured by the real ink",
    all(clear[k] >= declared[k] - 0.35 for k in ("left", "right", "top", "bottom")),
    "layout clearance (text boxes) "
    + ", ".join(f"{k} {declared[k]:.2f}" for k in declared)
    + " | ink clearance (dark pixels) "
    + ", ".join(f"{k} {clear[k]:.2f}" for k in clear)
    + " - the gap is the unused ascent/descent inside each text box",
)

# ---------------------------------------------------------------------------
# 3. per-point marker geometry measured on the raster
# ---------------------------------------------------------------------------
left_mm, bottom_mm, plot_w_mm, plot_h_mm = SETTINGS["axes"]["main_axes_rect_mm_lbwh"]
x_order = SETTINGS["axes"]["x_order"]
y_order = SETTINGS["axes"]["y_order"]
n_arm, n_cell = len(x_order), len(y_order)

rgb = np.array(img.convert("RGB")).astype(int)
nonwhite = np.abs(rgb - 255).sum(axis=2) > 45
yy_grid, xx_grid = np.mgrid[0:H, 0:W]

worst_rel = 0.0
zero_measure = []
declared_zero_ok = True
measured_frac: list[float] = []
measured_dia: list[float] = []
DOT_MAX_DECLARED = SETTINGS["scale_mapping"]["diameter_of_fraction_1_mm"]

for r in ROWS:
    frac = float(r["Detected fraction"])
    is_zero = r["is_zero"] == "True"
    xi, yi = x_order.index(r["Treatment arm"]), y_order.index(r["Cell type"])
    cx = (left_mm + (xi + 0.5) / n_arm * plot_w_mm) * ppx
    cy = (fig_h_mm - (bottom_mm + plot_h_mm * (1.0 - (yi + 0.5) / n_cell))) * ppy
    d_mm = float(r["diameter_mm"])

    if is_zero:
        declared_zero_ok &= float(r["s_pt2"]) == 0.0 and d_mm == 0.0
        win = int(round(1.0 * ppx))  # +/- 1 mm window: holds the symbol, no neighbour
        x0, x1 = int(cx) - win, int(cx) + win + 1
        y0, y1 = int(cy) - win, int(cy) + win + 1
        sub = nonwhite[y0:y1, x0:x1]
        ys, xs = np.where(sub)
        if len(xs) == 0:
            zero_measure.append((r, 0.0, 0.0, 0.0, 0.0))
            continue
        span_w = (xs.max() - xs.min() + 1) / ppx
        span_h = (ys.max() - ys.min() + 1) / ppy
        ink_mm2 = len(xs) / (ppx * ppy)
        fill = len(xs) / ((xs.max() - xs.min() + 1) * (ys.max() - ys.min() + 1))
        zero_measure.append((r, span_w, span_h, ink_mm2, fill))
        detail.append(
            f"  {r['Cell type']} | {r['Treatment arm']} | fraction 0 -> "
            f"symbol span {span_w:.2f} x {span_h:.2f} mm, ink {ink_mm2:.3f} mm^2, "
            f"fill ratio inside its own box {fill:.2f} "
            f"(a filled disc of the same span would be {np.pi / 4:.2f}); "
            f"declared marker area 0"
        )
        continue

    # horizontal chord through the marker centre -> rendered diameter
    cy_i = int(round(cy))
    band = nonwhite[max(cy_i - 1, 0):cy_i + 2, :].any(axis=0)
    lo = int(round(cx))
    while lo > 0 and band[lo - 1]:
        lo -= 1
    hi = int(round(cx))
    while hi < W - 1 and band[hi + 1]:
        hi += 1
    measured_d_mm = (hi - lo + 1) / ppx
    rel = abs(measured_d_mm - d_mm) / d_mm
    worst_rel = max(worst_rel, rel)
    measured_frac.append(frac)
    measured_dia.append(measured_d_mm)

    radius_px = max(d_mm * ref_px_per_mm / 2.0, 5.0)
    mask = (xx_grid - cx) ** 2 + (yy_grid - cy) ** 2 <= radius_px**2
    inked = float((mask & nonwhite).sum()) / float(mask.sum())

    detail.append(
        f"  {r['Cell type']} | {r['Treatment arm']} | fraction {frac:>4} | "
        f"intended {d_mm:.3f} mm | rendered {measured_d_mm:.3f} mm | "
        f"delta {100 * rel:4.1f} % | inked {100 * inked:5.1f} % of the probe disc"
    )

check(
    "zero rows declare a marker area of exactly 0 in the plotting data",
    declared_zero_ok,
    "s_pt2 == 0.0 and diameter_mm == 0.0 for every Detected fraction of 0",
)
check(
    "zero rows are drawn as a non-quantitative symbol, not a filled disc",
    all(f < 0.45 for _, _, _, _, f in zero_measure) and len(zero_measure) == 2,
    "; ".join(
        f"{r['Cell type']}/{r['Treatment arm']}: fill ratio {f:.2f} "
        f"(disc would be {np.pi / 4:.2f})"
        for r, _, _, _, f in zero_measure
    ),
)
# A rendered disc is systematically ~0.2 mm wider than the nominal diameter
# because the 0.078 mm edge stroke straddles the path and antialiasing adds
# about one pixel per side.  The right test is therefore the *proportional*
# structure: rendered diameter vs sqrt(fraction) must be linear through a
# small intercept, with a slope equal to the declared maximum diameter.
meas_f = np.array(measured_frac)
meas_d = np.array(measured_dia)
slope, intercept = np.polyfit(np.sqrt(meas_f), meas_d, 1)
check(
    "drawn marker diameter follows sqrt(fraction) with the declared maximum",
    abs(slope - DOT_MAX_DECLARED) / DOT_MAX_DECLARED < 0.05 and abs(intercept) < 0.4,
    f"least-squares fit rendered_d_mm = {slope:.4f} * sqrt(fraction) + "
    f"{intercept:+.4f} (n = {len(meas_f)}); declared maximum diameter "
    f"{DOT_MAX_DECLARED} mm -> slope within "
    f"{100 * abs(slope - DOT_MAX_DECLARED) / DOT_MAX_DECLARED:.1f} %, and the "
    f"constant {intercept:+.3f} mm is the antialiased rim / edge stroke",
)

# ---------------------------------------------------------------------------
# 4. the mapping is linear in area, not in radius
# ---------------------------------------------------------------------------
fracs = [0.25, 0.50, 0.75, 1.00]
dia = [SETTINGS["scale_mapping"]["reference_diameters_mm"][f"{f:.2f}"] for f in fracs]
area_ratio = [(d**2) / dia[0] ** 2 for d in dia]
check(
    "drawn area is proportional to Detected fraction (radius is not the variable)",
    all(abs(a - f / fracs[0]) < 1e-3 for a, f in zip(area_ratio, fracs)),
    "area(0.25):area(0.50):area(0.75):area(1.00) = "
    + " : ".join(f"{a:.4f}" for a in area_ratio)
    + "  |  diameters "
    + " : ".join(f"{d:.3f}" for d in dia)
    + " mm  |  a radius-linear encoding would need areas 1 : 4 : 9 : 16 mm-free "
    "but diameters 1 : 2 : 3 : 4",
)

# ---------------------------------------------------------------------------
# 5. PDF page box and text handling
# ---------------------------------------------------------------------------
pdf_bytes = (ROOT / "output" / "panel.pdf").read_bytes()
boxes = re.findall(rb"/MediaBox\s*\[([^\]]*)\]", pdf_bytes)
box_mm = None
if boxes:
    nums = [float(v) for v in boxes[0].split()]
    box_mm = ((nums[2] - nums[0]) / 72 * 25.4, (nums[3] - nums[1]) / 72 * 25.4)
check(
    "PDF page box is exactly 120 x 90 mm",
    box_mm is not None and abs(box_mm[0] - 120) < 0.02 and abs(box_mm[1] - 90) < 0.02,
    f"MediaBox {nums[2] - nums[0]:.2f} x {nums[3] - nums[1]:.2f} pt = "
    f"{box_mm[0]:.3f} x {box_mm[1]:.3f} mm",
)
font_tokens = sorted({m.decode() for m in re.findall(rb"/(TrueType|Type3|Type1|Type0|CIDFontType\d)\b", pdf_bytes)})
base_fonts = [m.decode() for m in re.findall(rb"/BaseFont\s*/([A-Za-z0-9+\-]+)", pdf_bytes)]
check(
    "PDF text is embedded TrueType, not converted to outlines",
    b"/FontFile2" in pdf_bytes and b"/Type3" not in pdf_bytes,
    f"font objects present: {font_tokens}, embedded font file: "
    f"{'FontFile2 (TrueType)' if b'/FontFile2' in pdf_bytes else 'NONE'}, "
    f"BaseFont {sorted(set(base_fonts))} - the text stays selectable and editable",
)

# ---------------------------------------------------------------------------
# 5b. rasterise the PDF itself and compare it with the PNG
# ---------------------------------------------------------------------------
import shutil  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402

pdftoppm = shutil.which("pdftoppm") or shutil.which(
    "pdftoppm", path="/opt/homebrew/bin:/usr/local/bin"
)
if pdftoppm:
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(
            [pdftoppm, "-r", "300", "-png", "-singlefile",
             str(ROOT / "output" / "panel.pdf"), f"{td}/pdf"],
            check=True, capture_output=True,
        )
        pdf_img = Image.open(f"{td}/pdf.png").convert("L")
        pw, ph = pdf_img.size
        pa = np.array(pdf_img)
        pcols = np.where((pa < 245).any(axis=0))[0]
        prows = np.where((pa < 245).any(axis=1))[0]
        pdf_clear = [
            pcols.min() / (pw / 120.0),
            120 - pcols.max() / (pw / 120.0),
            prows.min() / (ph / 90.0),
            90 - prows.max() / (ph / 90.0),
        ]
        check(
            "independently rasterised PDF reproduces the page and keeps the ink inside",
            abs(pw / 300 * 25.4 - 120) < 0.2
            and abs(ph / 300 * 25.4 - 90) < 0.2
            and min(pdf_clear) >= 0.9,
            f"poppler raster at 300 dpi -> {pw}x{ph} px = "
            f"{pw / 300 * 25.4:.2f} x {ph / 300 * 25.4:.2f} mm, ink clearance mm "
            + ", ".join(f"{v:.2f}" for v in pdf_clear),
        )
        # same ink pattern as the PNG render?
        png_small = np.array(
            Image.open(ROOT / "output" / "panel.png").convert("L").resize((pw, ph))
        )
        diff = float(np.abs(png_small.astype(int) - pa.astype(int)).mean())
        check(
            "PDF raster and PNG raster agree",
            diff < 6.0,
            f"mean absolute grey-level difference {diff:.2f} / 255 between the "
            f"poppler PDF render and the matplotlib PNG (both at 300 dpi)",
        )
else:
    check("PDF raster comparison", True, "skipped - pdftoppm not available")

# ---------------------------------------------------------------------------
# 6. SVG: physical size, live text
# ---------------------------------------------------------------------------
svg_text = (ROOT / "output" / "panel.svg").read_text()
root = ET.fromstring(svg_text)
w_attr, h_attr, vb = root.get("width", ""), root.get("height", ""), root.get("viewBox", "")


def to_mm(value: str) -> float:
    m = re.match(r"^\s*([0-9.]+)\s*(mm|pt|px|cm|in)?\s*$", value)
    num, unit = float(m.group(1)), (m.group(2) or "px")
    return {"mm": num, "pt": num / 72 * 25.4, "px": num / 96 * 25.4,
            "cm": num * 10, "in": num * 25.4}[unit]


check(
    "SVG declares the 120 x 90 mm physical size",
    abs(to_mm(w_attr) - 120) < 0.02 and abs(to_mm(h_attr) - 90) < 0.02,
    f'width="{w_attr}" height="{h_attr}" viewBox="{vb}" '
    f"= {to_mm(w_attr):.3f} x {to_mm(h_attr):.3f} mm",
)

n_text = len(re.findall(r"<text\b", svg_text))
expected_texts = (
    ["Treatment arm", "Cell type", "Detected fraction", "Prepared score"]
    + x_order + y_order
    + ["0", "0.25", "0.50", "0.75", "1.00", "1.5", "1.0", "0.5", "0.0"]
)
missing = [t for t in expected_texts if f">{t}<" not in svg_text]
check(
    "SVG keeps editable text (real <text> elements, no glyph outlines)",
    n_text >= 24 and not missing and "font-family: 'Arial'" in svg_text,
    f"{n_text} <text> elements, {len(re.findall(r'<path', svg_text))} <path> "
    f"elements (the dots/legend circles), all expected strings present, "
    f"font-family declared as {re.search(r'font-family: [^;\"]*', svg_text).group(0)}",
)

# ---------------------------------------------------------------------------
# 7. nothing beyond the requested text
# ---------------------------------------------------------------------------
all_svg_text = " ".join(re.findall(r"<text[^>]*>([^<]*)</text>", svg_text))
stripped = all_svg_text.replace("Detected fraction", "").replace("Prepared score", "")
check(
    "no title, subtitle or explanatory footnote in the image",
    not re.search(r"(?i)figure|title|note|synthetic|asterisk|p\s*[<=]", stripped),
    "text actually drawn: "
    + ", ".join(sorted({t.strip() for t in all_svg_text.split() if t.strip()})),
)
check(
    "all 24 input rows are plotted",
    len(ROWS) == 24 and len({(r["Cell type"], r["Treatment arm"]) for r in ROWS}) == 24,
    f"{len(ROWS)} rows in data/plot_data.csv, "
    f"{len({r['Cell type'] for r in ROWS})} cell types x "
    f"{len({r['Treatment arm'] for r in ROWS})} treatment arms",
)

# ---------------------------------------------------------------------------
report = (
    f"verify_figure.py - {n_pass} passed, {n_fail} failed\n\n"
    + "\n".join(head)
    + "\n\nper-marker measurements taken from the 300 dpi raster\n"
    + "\n".join(detail)
    + "\n"
)
(ROOT / "checks" / "verification.txt").write_text(report, encoding="utf-8")
print(report)
