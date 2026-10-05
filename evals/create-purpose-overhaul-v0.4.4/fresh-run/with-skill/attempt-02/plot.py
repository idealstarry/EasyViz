#!/usr/bin/env python3
"""Create the supplied cell-number panel with all observations and mean ± SEM.

Run with the project's .venv Python. The default source paths are the supplied
fresh exercise files; --data, --contract and --out can be supplied explicitly.
Only categorical plotting positions change. Source text and cells are retained.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path

TRIAL = Path(__file__).resolve().parent.parent
os.environ.setdefault("MPLCONFIGDIR", str(TRIAL / ".mplconfig"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
import numpy as np
from PIL import Image
from pypdf import PdfReader
import xml.etree.ElementTree as ET

SOURCE = Path("/Users/starry/Desktop/EasyViz/evals/create-purpose-overhaul-v0.4.4/source-intake")
WIDTH_MM, HEIGHT_MM, DPI = 120.0, 60.0, 300
PT_PER_MM = 72.0 / 25.4
POINT_DIAMETER_PT = 2.5
POINT_GAP_PT = 0.22
RAW_MAX_OFFSET_MM = 1.3
COLORS = {"-DT": "#454545", "+DT": "#0072B2"}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dump(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")

def pack(values_y_pt, max_offset_pt):
    """Bounded categorical-only constrained circle packing, deterministic.

    Numeric display coordinates are fixed. For each small source group,
    minimize squared categorical displacement while requiring physical circle
    clearance. Multiple deterministic initial placements address local minima.
    Retain every observation and report infeasibility rather than move y.
    """
    from scipy.optimize import minimize
    y = np.asarray(values_y_pt, dtype=float)
    n = len(y)
    sep = POINT_DIAMETER_PT + POINT_GAP_PT
    pairs = [(i, j) for i in range(n) for j in range(i+1, n) if abs(y[i]-y[j]) < sep]
    if not pairs:
        return np.zeros(n), []
    ii = np.array([p[0] for p in pairs]); jj = np.array([p[1] for p in pairs])
    dy2 = (y[ii]-y[jj])**2
    def clearance(x):
        return (x[ii]-x[jj])**2 + dy2 - sep**2
    def jac(x):
        result = np.zeros((len(pairs), n))
        delta = 2*(x[ii]-x[jj])
        result[np.arange(len(pairs)),ii] = delta
        result[np.arange(len(pairs)),jj] = -delta
        return result
    rng = np.random.default_rng(231)
    starts = [rng.uniform(-max_offset_pt,max_offset_pt,n) for _ in range(18)]
    rank = np.argsort(np.argsort(y,kind="stable"),kind="stable")
    starts.insert(0, np.array([-max_offset_pt,0,max_offset_pt])[rank%3])
    candidates = []
    for init in starts:
        fit = minimize(lambda x: float(np.dot(x,x)), init,
                       jac=lambda x: 2*x, method="SLSQP",
                       bounds=[(-max_offset_pt,max_offset_pt)]*n,
                       constraints={"type":"ineq","fun":clearance,"jac":jac},
                       options={"maxiter":700,"ftol":1e-10})
        if clearance(fit.x).min() >= -1e-6:
            candidates.append(fit.x)
    if candidates:
        return min(candidates,key=lambda x:float(np.dot(x,x))), []
    # No silent failure: retain every point and make failed placement explicit.
    fallback = starts[0]
    bad = sorted(set(k for k,p in enumerate(pairs) if clearance(fallback)[k]<0 for k in p))
    return fallback,bad

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=SOURCE / "observations.csv")
    ap.add_argument("--contract", type=Path, default=SOURCE / "input-contract.json")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if any((args.out / f"panel.{fmt}").exists() for fmt in ["png", "pdf", "svg"]):
        raise SystemExit("Exports already exist; use a fresh attempt directory.")
    rows = list(csv.DictReader(args.data.open(newline="")))
    contract = json.loads(args.contract.read_text())
    populations, conditions = contract["population_order"], contract["condition_order"]
    assert len(rows) == contract["observation_count"] == 156
    assert set(r["population"] for r in rows) == set(populations)
    assert set(r["condition"] for r in rows) == set(conditions)
    assert len(set((r["source_sheet"], r["source_cell"]) for r in rows)) == len(rows)
    expected_counts = {r["population"]: r for r in contract["counts"]}
    plt.rcParams.update({
        "font.family": "Arial", "font.size": 8,
        "axes.labelsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
        "legend.fontsize": 8, "axes.linewidth": .55,
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
        "savefig.facecolor": "white", "figure.facecolor": "white",
        "axes.unicode_minus": True,
    })
    font_path = font_manager.findfont(font_manager.FontProperties(family="Arial"), fallback_to_default=False)
    fig = plt.figure(figsize=(WIDTH_MM/25.4, HEIGHT_MM/25.4), dpi=DPI)
    ax = fig.add_axes([16/120, 11/60, 101/120, 38/60])
    ax.set_xlim(-.5, 8.5)
    ax.set_ylim(0, 4)
    ax.set_xticks(range(9), populations)
    ax.set_yticks([0, 1, 2, 3, 4])
    ax.set_ylabel("Normalized cell number", labelpad=4)
    ax.tick_params(axis="both", direction="out", length=2.3, width=.55, pad=3, colors="#222222")
    for name in ["top", "right"]:
        ax.spines[name].set_visible(False)
    for name in ["bottom", "left"]:
        ax.spines[name].set_color("#222222")
    ax.grid(False)
    ax.set_axisbelow(True)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    pitch_mm = 101/9
    summaries, plotting, points, layout_groups, summary_segments = [], [], [], [], []
    drawn_values = []
    for p_i, population in enumerate(populations):
        for c_i, condition in enumerate(conditions):
            group = [r for r in rows if r["population"] == population and r["condition"] == condition]
            assert len(group) == expected_counts[population][condition]
            values = np.array([float(r["normalized_count"]) for r in group], dtype=float)
            assert np.isfinite(values).all()
            mean = float(values.mean())
            sd = float(values.std(ddof=1))
            sem = sd / math.sqrt(len(values))
            condition_center = p_i + (-2.65 if c_i == 0 else 2.65) / pitch_mm
            raw_anchor = condition_center - .85 / pitch_mm
            summary_x = condition_center + 1.75 / pitch_mm
            y_px = ax.transData.transform(np.column_stack([np.full(len(values), raw_anchor), values]))[:,1]
            y_pt = y_px * 72 / DPI
            offsets, failures = pack(y_pt, RAW_MAX_OFFSET_MM * PT_PER_MM)
            raw_x = raw_anchor + offsets / PT_PER_MM / pitch_mm
            raw_artist = ax.scatter(raw_x, values, s=POINT_DIAMETER_PT**2, c=COLORS[condition], alpha=1, marker="o", linewidths=0, zorder=3)
            drawn_values += raw_artist.get_offsets()[:,1].tolist()
            cap_dx = .46 / pitch_mm
            mean_dx = .58 / pitch_mm
            lo, hi = mean-sem, mean+sem
            for xs, ys, lw in [([summary_x,summary_x],[lo,hi],.65),([summary_x-cap_dx,summary_x+cap_dx],[lo,lo],.65),([summary_x-cap_dx,summary_x+cap_dx],[hi,hi],.65),([summary_x-mean_dx,summary_x+mean_dx],[mean,mean],1.05)]:
                ax.plot(xs, ys, color=COLORS[condition], linewidth=lw, solid_capstyle="butt", zorder=4)
                ends = ax.transData.transform(np.column_stack([xs,ys])) * 72/DPI
                summary_segments.append({"population":population,"condition":condition,"ends_pt":ends.tolist(),"width_pt":lw})
            coordinates_pt = ax.transData.transform(np.column_stack([raw_x,values]))*72/DPI
            for i, r in enumerate(group):
                record = dict(r)
                record.update({"_source_value_text":r["normalized_count"],"_population_index":p_i,"_condition_index":c_i,"_raw_x":float(raw_x[i]),"_categorical_offset_pt":float(offsets[i]),"_summary_x":float(summary_x)})
                plotting.append(record)
                points.append({"population":population,"condition":condition,"source_cell":r["source_cell"],"center_pt":coordinates_pt[i].tolist()})
            summaries.append({"population":population,"condition":condition,"n":len(values),"mean":mean,"sample_sd":sd,"sem":sem,"lower_mean_minus_sem":lo,"upper_mean_plus_sem":hi,"source_cells":[r["source_cell"] for r in group]})
            layout_groups.append({"population":population,"condition":condition,"lane_anchor":raw_anchor,"max_allowed_offset_mm":RAW_MAX_OFFSET_MM,"max_actual_offset_mm":float(np.max(abs(offsets)))/PT_PER_MM,"fallback_rows":[group[k]["source_cell"] for k in failures]})
    handles = [Line2D([],[],linestyle="none",marker="o",markersize=POINT_DIAMETER_PT,markeredgewidth=0,color=COLORS[c],label="−DT" if c=="-DT" else "+DT") for c in conditions]
    legend = fig.legend(handles=handles,loc="upper right",bbox_to_anchor=(116/120,56.5/60),ncol=2,frameon=False,handlelength=.6,handletextpad=.45,columnspacing=1.2,borderaxespad=0)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    text_records = []
    clipping = []
    all_texts = [ax.yaxis.label,*ax.get_xticklabels(),*ax.get_yticklabels(),*legend.get_texts()]
    for t in all_texts:
        bounds = t.get_window_extent(renderer)
        bbox_mm = [bounds.x0/DPI*25.4,bounds.y0/DPI*25.4,bounds.width/DPI*25.4,bounds.height/DPI*25.4]
        text_records.append({"text":t.get_text(),"size_pt":t.get_fontsize(),"family":t.get_fontfamily(),"bbox_mm":bbox_mm})
        if bounds.x0<0 or bounds.y0<0 or bounds.x1>fig.bbox.width or bounds.y1>fig.bbox.height:
            clipping.append(t.get_text())
    xboxes = [t.get_window_extent(renderer) for t in ax.get_xticklabels()]
    tick_overlaps = [(i,i+1) for i in range(len(xboxes)-1) if xboxes[i].overlaps(xboxes[i+1])]
    collision_pairs = []
    min_center_sep_pt = float("inf")
    for i, p in enumerate(points):
        for q in points[i+1:]:
            distance = math.dist(p["center_pt"],q["center_pt"])
            min_center_sep_pt = min(min_center_sep_pt,distance)
            if distance < POINT_DIAMETER_PT+POINT_GAP_PT-1e-6:
                collision_pairs.append([p["source_cell"],q["source_cell"],distance])
    def distance_to_segment(point, segment):
        a,b = np.array(segment["ends_pt"])
        v = b-a
        t = np.clip(np.dot(np.array(point)-a,v)/np.dot(v,v),0,1) if np.dot(v,v)>0 else 0
        return float(np.linalg.norm(np.array(point)-(a+t*v)))
    summary_crossings = []
    for p in points:
        for seg in summary_segments:
            if distance_to_segment(p["center_pt"],seg)<POINT_DIAMETER_PT/2+seg["width_pt"]/2-1e-7:
                summary_crossings.append([p["source_cell"],seg["population"],seg["condition"]])
    data_box = ax.get_window_extent(renderer)
    point_boundary_violations = [p["source_cell"] for p in points if p["center_pt"][0]-POINT_DIAMETER_PT/2 < data_box.x0*72/DPI or p["center_pt"][0]+POINT_DIAMETER_PT/2 > data_box.x1*72/DPI or p["center_pt"][1]-POINT_DIAMETER_PT/2 < data_box.y0*72/DPI or p["center_pt"][1]+POINT_DIAMETER_PT/2 > data_box.y1*72/DPI]
    legend_box = legend.get_window_extent(renderer)
    spec = {"track":"create","implementation":"custom grouped observations and mean ± SEM","question":"How do supplied normalized cell-number distributions differ between −DT and +DT within the nine populations?","order":{"population":populations,"condition":conditions},"fields":{"population":"population","condition":"condition","value":"normalized_count","source":"source_cell"},"layout":{"width_mm":WIDTH_MM,"height_mm":HEIGHT_MM,"font":"Arial","font_size_pt":8,"dpi":DPI,"data_region_mm":[16,11,101,38]},"colors":COLORS,"mark_roles":{"raw_observation":{"shape":"circle","diameter_pt":POINT_DIAMETER_PT,"matplotlib_s_pt2":POINT_DIAMETER_PT**2,"fill":"opaque","edge":"none"},"mean":{"horizontal_width_mm":1.16,"line_width_pt":1.05},"sem":{"cap_width_mm":.92,"line_width_pt":.65},"axes":{"line_width_pt":.55}},"numeric_axis":{"scale":"linear","limits":[0,4],"ticks":[0,1,2,3,4]},"summaries":{"center":"arithmetic mean","uncertainty":"sample SD with ddof=1 divided by sqrt(n)"},"changes":"Categorical-only circle packing. No numeric jitter, normalization, inference, filtering, pairing, or invented unit IDs.","formats":["png","pdf","svg"]}
    dump(args.out/"spec.json",spec)
    (args.out/"source.csv").write_bytes(args.data.read_bytes())
    (args.out/"input-contract.json").write_bytes(args.contract.read_bytes())
    with (args.out/"plotting-data.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(plotting[0]))
        writer.writeheader(); writer.writerows(plotting)
    dump(args.out/"summary-data.json",summaries)
    for fmt in ["png","pdf","svg"]:
        fig.savefig(args.out/f"panel.{fmt}",format=fmt,dpi=DPI,facecolor="white")
    # Use the mathematically rounded full raster canvas. Agg truncates pixel
    # dimensions; a missing white edge pixel is padded without resampling,
    # cropping, changing data coordinates, or scaling the 8 pt text.
    target_px = (round(WIDTH_MM/25.4*DPI),round(HEIGHT_MM/25.4*DPI))
    with Image.open(args.out/"panel.png") as im:
        original_px = im.size
        if any(a>b for a,b in zip(original_px,target_px)):
            raise ValueError("Raster rounding would require cropping")
        if original_px != target_px:
            rounded_canvas=Image.new("RGBA",target_px,"white")
            rounded_canvas.paste(im,(0,0))
            rounded_canvas.save(args.out/"panel.png",dpi=(DPI,DPI))
    with Image.open(args.out/"panel.png") as im:
        png_size=list(im.size); png_dpi=list(im.info["dpi"])
    pdf=PdfReader(args.out/"panel.pdf")
    page=pdf.pages[0]
    pdf_dims=[float(page.mediabox.width)*25.4/72,float(page.mediabox.height)*25.4/72]
    fonts=[]
    for item in page["/Resources"]["/Font"].values():
        font=item.get_object(); descendant=font.get("/DescendantFonts")
        fd=(descendant[0].get_object().get("/FontDescriptor") if descendant else font.get("/FontDescriptor"))
        descriptor=fd.get_object() if fd else {}
        fonts.append({"base_font":str(font.get("/BaseFont")),"embedded":any(k in descriptor for k in ["/FontFile","/FontFile2","/FontFile3"])})
    root=ET.parse(args.out/"panel.svg").getroot()
    def physical_mm(value):
        if value.endswith("pt"):return float(value[:-2])*25.4/72
        if value.endswith("mm"):return float(value[:-2])
        raise ValueError(value)
    svg_dims=[physical_mm(root.attrib[k]) for k in ["width","height"]]
    # Independent numerical audit: Python statistics parses the original CSV
    # again rather than trusting NumPy summary arrays or the plotted metadata.
    import statistics
    reread=list(csv.DictReader(args.data.open(newline="")))
    summary_audit=[]
    for s in summaries:
        vv=[float(r["normalized_count"]) for r in reread if r["population"]==s["population"] and r["condition"]==s["condition"]]
        expected_mean=statistics.mean(vv); expected_sem=statistics.stdev(vv)/math.sqrt(len(vv))
        summary_audit.append({"population":s["population"],"condition":s["condition"],"mean_abs_error":abs(s["mean"]-expected_mean),"sem_abs_error":abs(s["sem"]-expected_sem)})
    summary_ok=all(r["mean_abs_error"]<1e-12 and r["sem_abs_error"]<1e-12 for r in summary_audit)
    original_sorted=sorted(float(r["normalized_count"]) for r in rows)
    raw_ok=sorted(drawn_values)==original_sorted
    dims_ok=all(abs(a-b)<1e-6 for dims in [pdf_dims,svg_dims] for a,b in zip(dims,[WIDTH_MM,HEIGHT_MM])) and all(abs(a-b)<=1 for a,b in zip(png_size,[round(WIDTH_MM/25.4*DPI),round(HEIGHT_MM/25.4*DPI)])) and all(abs(d-DPI)<.02 for d in png_dpi)
    font_ok=all(t["size_pt"]==8 and t["family"]==["Arial"] for t in text_records) and all(f["embedded"] and "Arial" in f["base_font"] for f in fonts)
    point_layout={"policy":"deterministic constrained categorical-only circle packing","diameter_pt":POINT_DIAMETER_PT,"gap_pt":POINT_GAP_PT,"groups":layout_groups,"unresolved_pair_count":len(collision_pairs),"unresolved_pairs":collision_pairs,"min_center_separation_pt":min_center_sep_pt,"summary_crossing_count":len(summary_crossings),"summary_crossings":summary_crossings,"boundary_violations":point_boundary_violations}
    geometry={"data_region_mm":[16,11,101,38],"data_region_aspect":101/38,"population_pitch_mm":pitch_mm,"condition_center_separation_mm":5.3,"raw_anchor_relative_to_condition_mm":-.85,"summary_center_relative_to_condition_mm":1.75,"point_layout":point_layout,"legend_bounds_mm":[legend_box.x0/DPI*25.4,legend_box.y0/DPI*25.4,legend_box.width/DPI*25.4,legend_box.height/DPI*25.4],"legend_reserved_region_mm":[91,50.5,26,7],"legend_area_fraction_of_data_region":legend_box.width*legend_box.height/(data_box.width*data_box.height),"text":text_records}
    dump(args.out/"geometry-evidence.json",geometry)
    script=Path(__file__).resolve()
    settings={"track":"create","input":{"data_file":str(args.data.resolve()),"contract_file":str(args.contract.resolve()),"source_script":str(script),"spec_file":str((args.out/"spec.json").resolve()),"supplied_spec_sha256":sha(args.out/"spec.json")},"version":{"input_sha256":sha(args.data),"contract_sha256":sha(args.contract),"source_script_sha256":sha(script)},"layout":{"width_mm":WIDTH_MM,"height_mm":HEIGHT_MM,"dpi":DPI,"actual_font":"Arial","font_substituted":False,"font_path":font_path},"typography":{"axis":8,"tick":8,"legend":8,"annotation":8},"formats":["png","pdf","svg"],"point_layout":point_layout,"colors":COLORS,"caption_file":str((args.out/"caption.md").resolve()),"font_exports":{"pdf":fonts,"svg":"Editable Arial 8 pt text; font is not embedded in SVG."}}
    dump(args.out/"settings.json",settings)
    checks={"source_rows_retained":raw_ok and len(plotting)==156,"source_values_and_cells_retained":all(r["normalized_count"]==r["_source_value_text"] for r in plotting),"source_counts_match_contract":True,"summary_recomputation":summary_ok,"same_canvas_formats":dims_ok,"all_text_Arial_8pt_and_PDF_embedding":font_ok,"canvas_text_clipping":not clipping,"x_tick_collision":not tick_overlaps,"raw_circle_separation":not collision_pairs,"raw_summary_clearance":not summary_crossings,"raw_full_glyph_within_axes":not point_boundary_violations,"packing_no_fallback":not any(g["fallback_rows"] for g in layout_groups)}
    qa={"status":"pass" if all(checks.values()) else "needs_revision","valid_outputs":all(checks.values()),"input_sha256":sha(args.data),"input_rows":len(rows),"checks":checks,"exports":{"png":{"pixels":png_size,"dpi":png_dpi,"sha256":sha(args.out/"panel.png")},"pdf":{"width_mm":pdf_dims[0],"height_mm":pdf_dims[1],"sha256":sha(args.out/"panel.pdf")},"svg":{"width_mm":svg_dims[0],"height_mm":svg_dims[1],"sha256":sha(args.out/"panel.svg")}},"text_clipping":clipping,"x_tick_overlaps":tick_overlaps,"point_layout":point_layout,"summary_audit":summary_audit,"raster_rounding":{"renderer_pixels":list(original_px),"rounded_canvas_pixels":list(target_px),"method":"White-edge canvas padding; no resampling or cropping."},"limitation":"Numeric and export checks are not actual-image review, aesthetic judgment, or scientific inference."}
    dump(args.out/"qa.json",qa)
    caption="""Normalized cell numbers for the nine supplied populations in −DT and +DT conditions, measured 24 h after 50 ng DT. Each circular point shows one supplied mouse observation; observations are not connected. Short horizontal strokes show arithmetic means and capped vertical intervals show mean ± SEM (sample SD, ddof = 1, divided by √n), calculated separately within each population and condition. Population abbreviations and both orders are retained as supplied. Group sample sizes (−DT, +DT) are: cMo (8, 10), pMo (8, 10), SPM (9, 8), LPM (9, 8), RPM (8, 10), KC (10, 10), SILPM (8, 8), CLPM (8, 8), and MG (8, 8). All 156 supplied observations are displayed. Empty source slots are absent observations, not zeros. The author-supplied dimensionless normalized values are preserved without re-normalization; the exact normalization denominator is unavailable. Mouse identifiers and experiment batches are absent, so no pairing or additional statistical inference is made. Source: supplied observations extracted from sheet 2h of `41590_2023_1468_MOESM4_ESM.xlsx`, DOI [10.1038/s41590-023-01468-3](https://doi.org/10.1038/s41590-023-01468-3), CC BY 4.0, as recorded in the supplied input contract.\n"""
    (args.out/"caption.md").write_text(caption)
    plt.close(fig)
    print(json.dumps({"output":str(args.out.resolve()),"qa_status":qa["status"],"checks":checks,"exports":qa["exports"]},indent=2))

if __name__ == "__main__":
    main()
