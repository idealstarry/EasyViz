#!/usr/bin/env python3
"""Custom, standalone scientific panels; no EasyViz renderer dependencies.

Replay: python plot_panels.py --panel noaa-co2 --out noaa-co2/replay
        python plot_panels.py --panel usgs-earthquakes --out usgs-earthquakes/replay
The --inputs option overrides the frozen source directory.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from decimal import Decimal
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, ft2font
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, NullLocator, ScalarFormatter
import numpy as np
from PIL import Image
from pypdf import PdfReader

WIDTH_MM, HEIGHT_MM, DPI, FONT_PT = 90.0, 70.0, 300, 8.0
COLORS = {"mb": "#2581B9", "mww": "#DF9A3C", "mwb": "#1AA781", "mwr": "#CC86B9"}
MARKERS = {"mb": "o", "mww": "s", "mwb": "D", "mwr": "^"}


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def csv_write(path, fields, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def axes_mm(fig, left, bottom, width, height):
    return fig.add_axes([left/WIDTH_MM, bottom/HEIGHT_MM, width/WIDTH_MM, height/HEIGHT_MM])


def base_axes(ax, grid=True):
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    for spine in ["left", "bottom"]:
        ax.spines[spine].set_linewidth(0.6)
        ax.spines[spine].set_color("#333333")
    ax.tick_params(axis="both", which="major", labelsize=FONT_PT, width=0.6, length=2.5, pad=3)
    if grid:
        ax.grid(axis="y", color="#E2E2E2", linewidth=0.4, zorder=0)


def bounds_mm(bbox, fig):
    p = bbox.transformed(fig.transFigure.inverted())
    return [p.x0*WIDTH_MM, p.y0*HEIGHT_MM, p.width*WIDTH_MM, p.height*HEIGHT_MM]


def export(fig, out, settings, required_chars):
    font_path = font_manager.findfont(font_manager.FontProperties(family="Arial"), fallback_to_default=False)
    font = ft2font.FT2Font(font_path)
    missing = [c for c in sorted(set(required_chars)) if not c.isspace() and font.get_char_index(ord(c)) == 0]
    assert not missing, f"Missing glyphs: {missing}"
    settings["font"] = {"requested": "Arial", "actual": "Arial", "path": font_path,
                        "size_pt_all_roles": FONT_PT, "substitution": False,
                        "missing_glyphs": missing}
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    text_bounds = []
    for artist in fig.findobj(matplotlib.text.Text):
        if artist.get_visible() and artist.get_text():
            box = bounds_mm(artist.get_window_extent(renderer), fig)
            text_bounds.append({"text": artist.get_text(), "font_size_pt": artist.get_fontsize(), "bbox_mm": box})
    clipped = [t for t in text_bounds if t["bbox_mm"][0] < -0.05 or t["bbox_mm"][1] < -0.05
               or t["bbox_mm"][0]+t["bbox_mm"][2] > WIDTH_MM+0.05
               or t["bbox_mm"][1]+t["bbox_mm"][3] > HEIGHT_MM+0.05]
    if settings.get("legend_artist"):
        legend = settings.pop("legend_artist")
        box = bounds_mm(legend.get_window_extent(renderer), fig)
        plot_box = settings["axes"][0]["bbox_mm"]
        settings["legend_layout"]["complete_bounds_mm"] = box
        settings["legend_layout"]["relative_area_to_primary_field"] = (box[2]*box[3])/(plot_box[2]*plot_box[3])
    settings["text_bounds_mm"] = text_bounds
    fig.savefig(out/"panel.pdf", format="pdf", bbox_inches=None)
    fig.savefig(out/"panel.svg", format="svg", bbox_inches=None)
    raw = io.BytesIO()
    fig.savefig(raw, format="png", dpi=DPI, bbox_inches=None)
    raw.seek(0)
    png = Image.open(raw).convert("RGB")
    expected = (round(WIDTH_MM/25.4*DPI), round(HEIGHT_MM/25.4*DPI))
    # Matplotlib floors raster canvas pixels. Pad at most one white pixel to the
    # rounded requested canvas, preserving all mark/text geometry at 300 dpi.
    original_pixels = png.size
    assert all(0 <= e-a <= 1 for a,e in zip(png.size, expected))
    canvas = Image.new("RGB", expected, "white")
    canvas.paste(png, (0, 0))
    canvas.save(out/"panel.png", dpi=(DPI,DPI))
    canvas.resize((round(WIDTH_MM/25.4*96), round(HEIGHT_MM/25.4*96)), Image.Resampling.LANCZOS).save(out/"preview-at-96dpi.png", dpi=(96,96))
    page = PdfReader(out/"panel.pdf").pages[0]
    pdf_mm = [float(page.mediabox.width)*25.4/72, float(page.mediabox.height)*25.4/72]
    svg_root = ET.parse(out/"panel.svg").getroot()
    pdf_fonts = []
    for obj in page["/Resources"]["/Font"].values():
        f = obj.get_object()
        descendant = f["/DescendantFonts"][0].get_object() if "/DescendantFonts" in f else f
        descriptor = descendant.get("/FontDescriptor")
        embedded = bool(descriptor and any(k in descriptor.get_object() for k in ["/FontFile", "/FontFile2", "/FontFile3"]))
        pdf_fonts.append({"base_font": str(f.get("/BaseFont")), "embedded": embedded})
    stored = Image.open(out/"panel.png")
    checks = {"png_pixels": list(stored.size), "expected_png_pixels": list(expected),
              "png_dpi_metadata": stored.info.get("dpi"), "pre_padding_pixels": list(original_pixels),
              "raster_rounding": "Pad white right/bottom canvas by at most one pixel; do not rescale plotting geometry",
              "pdf_page_mm": pdf_mm, "svg_width": svg_root.attrib["width"], "svg_height": svg_root.attrib["height"],
              "pdf_fonts": pdf_fonts, "text_clipping": clipped,
              "font_sizes_all_8pt": all(t["font_size_pt"] == FONT_PT for t in text_bounds),
              "missing_glyphs": missing,
              "canvas_size_status": "passed" if all(abs(a-b)<0.001 for a,b in zip(pdf_mm,[WIDTH_MM,HEIGHT_MM])) else "failed",
              "visual_review": "Separate self-review record required; these measurements do not establish legibility"}
    write_json(out/"export-checks.json", checks)
    write_json(out/"settings.json", settings)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", choices=["noaa-co2", "usgs-earthquakes"], required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, default=Path("/Users/starry/Desktop/EasyViz/evals/skill-value/inputs"))
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    source = args.inputs/({"noaa-co2":"noaa-co2-1980-2024.csv", "usgs-earthquakes":"usgs-earthquakes-2024-01.csv"}[args.panel])
    blob = source.read_bytes()
    with source.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    shutil.copyfile(source, out/"source-input.csv")
    if Path(__file__).resolve() != out/"plot.py":
        shutil.copyfile(__file__, out/"plot.py")
    plt.rcParams.update({"font.family":"Arial", "font.size":FONT_PT, "axes.labelsize":FONT_PT,
                        "xtick.labelsize":FONT_PT,"ytick.labelsize":FONT_PT,"legend.fontsize":FONT_PT,
                        "legend.title_fontsize":FONT_PT,"axes.titlesize":FONT_PT,
                        "pdf.fonttype":42,"ps.fonttype":42,"svg.fonttype":"none",
                        "axes.unicode_minus":True,"savefig.bbox":None,"figure.facecolor":"white"})
    fig = plt.figure(figsize=(WIDTH_MM/25.4,HEIGHT_MM/25.4), dpi=DPI)
    settings = {"track":"create","input_mode":"source-data","panel":args.panel,
                "source_path":str(source),"source_sha256":hashlib.sha256(blob).hexdigest(),
                "row_count":len(rows),"implementation":"Custom Matplotlib; no core renderer/profile/legend helper code imported",
                "width_mm":WIDTH_MM,"height_mm":HEIGHT_MM,"dpi":DPI,"formats":["png","pdf","svg"],
                "text_roles_pt":dict.fromkeys(["axis","tick","legend","annotation"],FONT_PT),
                "line_width_pt":0.6,"filled_mark_outline_policy":"borderless; edgecolors=none and linewidths=0",
                "grid":"Under all marks; set_axisbelow(True), grid zorder=0",
                "statistics":"descriptive only; no fitted or significance layer", "filters":[],
                "versions":{"matplotlib":matplotlib.__version__,"numpy":np.__version__},
                "unavailable_checks":["Physical print was not made; screen preview uses nominal 96 dpi",
                                      "Independent reviewer results are not available to the implementer"]}
    if args.panel == "noaa-co2":
        assert len(rows)==45 and [int(r["year"]) for r in rows]==list(range(1980,2025))
        assert all(r["mean_ppm"] and r["uncertainty_ppm"] for r in rows)
        years = np.array([int(r["year"]) for r in rows])
        means = np.array([float(r["mean_ppm"]) for r in rows])
        unc = np.array([float(r["uncertainty_ppm"]) for r in rows])
        assert np.all(unc>=0)
        delta = Decimal(rows[-1]["mean_ppm"])-Decimal(rows[0]["mean_ppm"])
        trace=[]
        for r in rows:
            u,m=Decimal(r["uncertainty_ppm"]),Decimal(r["mean_ppm"])
            trace.append({**r,"uncertainty_lower_ppm":str(m-u),"uncertainty_upper_ppm":str(m+u),
                          "primary_mark":"annual mean point + adjacent-year connector + supplied +/- uncertainty",
                          "supporting_mark":"original supplied uncertainty on aligned lower axis"})
        csv_write(out/"plotted-values.csv", list(trace[0]), trace)
        ax = axes_mm(fig,18,30,68,36)
        uax = axes_mm(fig,18,13,68,10)
        for a in [ax,uax]:
            base_axes(a, grid=(a is ax))
            a.set_xlim(1979,2025)
        ax.set_ylim(330,430)
        ax.set_yticks([340,360,380,400,420])
        ax.set_ylabel("Annual mean CO2 (ppm)",labelpad=5)
        ax.tick_params(axis="x",bottom=False,labelbottom=False)
        ax.errorbar(years,means,yerr=unc,fmt="none",ecolor="#2581B9",elinewidth=0.6,capsize=1.2,capthick=0.6,zorder=2)
        ax.plot(years,means,color="#2581B9",linewidth=0.8,zorder=3)
        ax.scatter(years,means,s=6,color="#2581B9",edgecolors="none",linewidths=0,zorder=4)
        ax.text(1981,416,f"Δ = {delta} ppm",fontsize=FONT_PT,ha="left",va="center")
        ax.text(1981,333,rows[0]["mean_ppm"],fontsize=FONT_PT,ha="left",va="bottom")
        ax.annotate(rows[-1]["mean_ppm"],xy=(2024,means[-1]),xytext=(2016,423),
                    fontsize=FONT_PT,ha="right",va="center",
                    arrowprops={"arrowstyle":"-","color":"#333333","lw":0.6,
                                "shrinkA":2,"shrinkB":2})
        uax.set_ylim(0,0.16)
        uax.set_yticks([0,0.12],labels=["0","0.12"])
        uax.set_xticks([1980,1990,2000,2010,2024])
        uax.set_xlabel("Year",labelpad=4)
        uax.set_ylabel("Uncertainty\n(ppm)",labelpad=5)
        uax.scatter(years,unc,s=6,color="#2581B9",edgecolors="none",linewidths=0,zorder=3)
        settings.update({"chart":"Annual mean time-series with aligned supplied-uncertainty axis",
                         "data_mapping":{"x":"year","main_y":"mean_ppm","errorbar":"mean_ppm +/- uncertainty_ppm","lower_y":"uncertainty_ppm"},
                         "transformations":["Read original decimal strings unchanged","Convert decimals to float only for Matplotlib coordinates",
                                            "Compute exact Decimal endpoint difference and uncertainty bounds; no recomputation of annual means"],
                         "uncertainty_definition":"Standard deviation of differences between annual means independently determined by NOAA/ESRL and Scripps; not CI or temporal spread",
                         "axes":[{"role":"primary mean","bbox_mm":[18,30,68,36],"x_scale":"linear","y_scale":"linear","xlim":[1979,2025],"ylim":[330,430]},
                                 {"role":"supplied uncertainty","bbox_mm":[18,13,68,10],"x_scale":"linear","y_scale":"linear","xlim":[1979,2025],"ylim":[0,0.16]}],
                         "palette":"notch2-balanced blue","colors":{"annual mean and supplied uncertainty":"#2581B9"},
                         "legend_layout":{"role":"none; directly labeled axes","complete_bounds_mm":None,"reserved_region_mm":None},
                         "observations_delivered":45,"noaa_error_bars_visibility":"Faithful +/-0.12 ppm bounds are subpixel on the 100 ppm primary range; lower axis makes uncertainty values readable without inflation"})
        summary={"n_annual_means":45,"start_year":1980,"end_year":2024,"start_mean_ppm":rows[0]["mean_ppm"],
                 "end_mean_ppm":rows[-1]["mean_ppm"],"endpoint_change_ppm":str(delta),
                 "uncertainty_unique_ppm":sorted(set(r["uncertainty_ppm"] for r in rows)),
                 "method":"Decimal endpoint subtraction; no fitted rate, confidence interval or statistical test"}
        caption=("Annual mean atmospheric CO₂ dry-air mole fraction for the NOAA Global Monitoring Laboratory Mauna Loa record, 1980–2024. "
                 "Points show all 45 supplied annual means; connecting segments guide the eye and are not a fitted model. "
                 f"The record increases from {rows[0]['mean_ppm']} ppm in 1980 to {rows[-1]['mean_ppm']} ppm in 2024, an endpoint difference of {delta} ppm. "
                 "Primary-axis error bars show each mean ± NOAA's supplied uncertainty. The lower, year-aligned axis displays that uncertainty itself (0.12 ppm for every supplied year), "
                 "because these error bars are smaller than a raster pixel on the primary range. This uncertainty is the standard deviation of differences between annual means independently determined by NOAA/ESRL and Scripps; "
                 "it is neither a confidence interval nor within-year temporal spread. ppm denotes μmol mol⁻¹. "
                 "Mauna Loa observations paused after 29 November 2022 and resumed in July 2023; observations from December 2022 through 4 July 2023 were obtained at Maunakea. "
                 "No observations were filtered, interpolated or aggregated. Data: NOAA Global Monitoring Laboratory, Boulder, Colorado, USA; Xin Lan (NOAA/GML) and Ralph Keeling (Scripps Institution of Oceanography), "
                 "[Mauna Loa annual means](https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_annmean_mlo.txt), frozen retrieval 30 September 2026. This third-party panel is not endorsed by NOAA.\n")
        chars="Annual mean CO2 (ppm)UncertaintyYearΔ = 85.85 ppm338.76424.610.1219801990200020102024340360380400420"
    else:
        assert len(rows)==131 and len(set(r["id"] for r in rows))==131
        assert all(r["time"]>="2024-01-01" and r["time"]<"2024-02-01" for r in rows)
        assert all(r[k]=="us" for r in rows for k in ["net","locationSource","magSource"])
        assert all(r["status"]=="reviewed" for r in rows)
        assert set(r["magType"] for r in rows)==set(COLORS)
        assert all(float(r["depth"])>0 and float(r["mag"])>=5 for r in rows)
        trace=[{**r,"x_scale":"log10 axis; raw depth unchanged","color":COLORS[r["magType"]],
                "marker":MARKERS[r["magType"]],"marker_area_pt2":"12","alpha":"0.72","edge":"none"} for r in rows]
        csv_write(out/"plotted-values.csv",list(trace[0]),trace)
        ax=axes_mm(fig,16,14,69,42)
        base_axes(ax)
        ax.set_xscale("log")
        ax.set_xlim(3,750)
        ax.set_ylim(4.85,7.7)
        ax.xaxis.set_major_locator(FixedLocator([3,10,30,100,300,700]))
        ax.xaxis.set_minor_locator(NullLocator())
        ax.xaxis.set_major_formatter(ScalarFormatter())
        ax.set_yticks([5,5.5,6,6.5,7,7.5])
        ax.set_xlabel("Hypocentral depth (km, log scale)",labelpad=4)
        ax.set_ylabel("Catalog magnitude",labelpad=5)
        order=["mww","mb","mwb","mwr"]
        for typ in order:
            selected=[r for r in rows if r["magType"]==typ]
            ax.scatter([float(r["depth"]) for r in selected],[float(r["mag"]) for r in selected],
                       s=12,marker=MARKERS[typ],color=COLORS[typ],alpha=0.72,
                       edgecolors="none",linewidths=0,zorder=3+order.index(typ)/10)
        handles=[Line2D([],[],linestyle="none",marker=MARKERS[t],markersize=3.5,
                        markerfacecolor=COLORS[t],markeredgecolor="none",markeredgewidth=0,alpha=0.72,label=t) for t in COLORS]
        legend=fig.legend(handles=handles,loc="upper center",bbox_to_anchor=(0.56,0.98),ncol=4,
                          frameon=False,title="Magnitude type",fontsize=FONT_PT,title_fontsize=FONT_PT,
                          borderpad=0,handlelength=0.8,handletextpad=0.35,columnspacing=0.85,labelspacing=0.35)
        groups=Counter(r["magType"] for r in rows)
        coordinates=Counter((r["depth"],r["mag"]) for r in rows)
        summary={"n_catalog_events":131,"magnitude_type_counts":dict(sorted(groups.items())),
                 "depth_range_km":[min(float(r["depth"]) for r in rows),max(float(r["depth"]) for r in rows)],
                 "magnitude_range":[min(float(r["mag"]) for r in rows),max(float(r["mag"]) for r in rows)],
                 "exact_duplicate_coordinate_groups":[{"depth":d,"mag":m,"events":n} for (d,m),n in coordinates.items() if n>1],
                 "method":"Raw row ranges and category/coordinate counts; no fit, correlation or statistical test"}
        settings.update({"chart":"Magnitude versus hypocentral depth, with redundant categorical color/shape encoding",
                         "data_mapping":{"x":"depth (km)","y":"mag","color_and_shape":"magType","unit":"unique reviewed event id"},
                         "transformations":["No observation filtering, rounding, aggregation or jitter",
                                            "Display depth on logarithmic x axis; retain raw depth in CSV","Convert decimal strings to float only for plotting"],
                         "axes":[{"role":"primary event scatter","bbox_mm":[16,14,69,42],"x_scale":"log10","y_scale":"linear","xlim":[3,750],"ylim":[4.85,7.7]}],
                         "palette":"notch2-balanced; independently evaluated on actual panel","colors":COLORS,"markers":MARKERS,
                         "mark_area_pt2":12,"mark_alpha":0.72,"drawing_order":order,
                         "legend_layout":{"role":"categorical color and shape; size has no quantitative meaning",
                                          "position":"Above primary axes inside fixed canvas","reserved_region_mm":[16,58,69,11],
                                          "key_geometry":"3.5 pt categorical proxy markers; borderless, alpha 0.72",
                                          "font_pt":FONT_PT},"legend_artist":legend,
                         "observations_delivered":131,"missing_or_nonpositive_values":0,
                         "overplotting":"Repeated exact coordinates overlap; all events are drawn without displacement. Rare types drawn last. Alpha aids dense regions but is not a calibrated count encoding.",
                         "event_uncertainty":"No event uncertainty fields were supplied; no error bars invented"})
        caption=("Preferred hypocentral depth and preferred catalog magnitude for 131 reviewed global earthquake events in the supplied January 2024 USGS catalog sample. "
                 "Each symbol is one retained event; horizontal position uses a logarithmic depth axis, vertical position uses catalog magnitude, and color and shape identify the preferred magnitude type. "
                 "mb is a body-wave magnitude; mww, mwb and mwr are moment-magnitude estimates using the respective W-phase, body-wave and regional methods. "
                 "These catalog magnitudes are not uniform measures of energy or intensity. All events are drawn at their original coordinates, without rounding, jitter, weighting or aggregation; "
                 "events with identical depth and magnitude overlap, and transparency is not a calibrated count encoding. No event uncertainty fields were supplied, and no fit or significance layer is shown. "
                 "The frozen sample covers 1 January 2024 00:00 UTC (inclusive) to 1 February 2024 00:00 UTC (exclusive), global earthquakes queried with minmagnitude=5 and contributor=us; "
                 "preferred net, locationSource and magSource were further required to equal us. The supplied table already implements that source restriction, excluding two preferred-source rows before this plotting run. "
                 "Depths span 3.426–621.081 km and magnitudes 5.0–7.5. This is a selected catalog sample, not all earthquakes or a catalog-completeness study. "
                 "Data: U.S. Geological Survey, Department of the Interior/USGS, [ComCat/FDSN catalog](https://earthquake.usgs.gov/fdsnws/event/1/), frozen retrieval 30 September 2026; the exact query and input hashes accompany this panel. "
                 "This third-party panel is not endorsed by USGS.\n")
        chars="Hypocentral depth (km, log scale)Catalog magnitudeMagnitude typembmwwmwbmwr3103010030070055.566.577.5"
    (out/"caption.md").write_text(caption)
    write_json(out/"summary-statistics.json",summary)
    export(fig,out,settings,chars)
    print(json.dumps({"panel":args.panel,"out":str(out),"rows":len(rows),"files":sorted(p.name for p in out.iterdir() if p.is_file())}))


if __name__ == "__main__":
    main()
