"""Adapt the archived epithelial composition example to individual replicates."""
from pathlib import Path
import csv
import json
import math
import os

BASE = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", "/tmp/easyviz-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager


def main():
    cfg = json.loads((BASE / "figure-settings.json").read_text())
    rows = list(csv.DictReader((BASE / cfg["input"]).open()))
    lookup = {}
    for row in rows:
        key = (row["replicate"], row["cell_type"])
        if key in lookup:
            raise ValueError(f"Duplicate observation: {key}")
        count = int(row["cell_count"])
        if count < 0 or row["group"] != row["replicate"].split("_")[0]:
            raise ValueError(f"Invalid count or group: {row}")
        lookup[key] = count
    replicates = sorted({r["replicate"] for r in rows},
                        key=lambda x: (cfg["group_order"].index(x.split("_")[0]),
                                       int(x.split("rep")[1])))
    types = cfg["stack_order"]
    percentages = {}
    derived = []
    for rep in replicates:
        total = sum(lookup[rep, ct] for ct in types)
        if total <= 0:
            raise ValueError(f"No epithelial cells: {rep}")
        percentages[rep] = [100 * lookup[rep, ct] / total for ct in types]
        assert math.isclose(sum(percentages[rep]), 100, abs_tol=1e-9)
        for ct, pct in zip(types, percentages[rep]):
            derived.append([rep, rep.split('_')[0], ct, lookup[rep, ct], total, pct])
    with (BASE / "derived-data.csv").open("w") as handle:
        writer = csv.writer(handle)
        writer.writerow(["replicate", "group", "cell_type", "cell_count",
                         "epithelial_total", "percent_of_epithelial"])
        writer.writerows(derived)

    try:
        font_path = font_manager.findfont(cfg["font_family"], fallback_to_default=False)
    except ValueError:
        font_path = font_manager.findfont("DejaVu Sans", fallback_to_default=False)
    font = font_manager.FontProperties(fname=font_path).get_name()
    plt.rcParams.update({"font.family": font, "font.size": cfg["font_size_pt"],
                         "axes.labelsize": cfg["font_size_pt"],
                         "xtick.labelsize": cfg["font_size_pt"],
                         "ytick.labelsize": cfg["font_size_pt"],
                         "legend.fontsize": cfg["font_size_pt"],
                         "axes.linewidth": cfg["line_width_pt"],
                         "pdf.fonttype": 42})
    fig, ax = plt.subplots(figsize=(cfg["width_mm"] / 25.4, cfg["height_mm"] / 25.4))
    fig.subplots_adjust(left=.19, right=.98, bottom=.23, top=.91)
    positions = []
    for group_index, group in enumerate(cfg["group_order"]):
        positions.extend([len(positions) + j + group_index for j in range(
            sum(r.startswith(group + "_") for r in replicates))])
    bottom = [0.] * len(replicates)
    handles = []
    for index, ct in enumerate(types):
        values = [percentages[rep][index] for rep in replicates]
        bars = ax.bar(positions, values, bottom=bottom, width=.78,
                      color=cfg["colors"][ct], edgecolor="black", linewidth=.35,
                      label=ct)
        handles.append(bars)
        bottom = [b + v for b, v in zip(bottom, values)]
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel("Epithelial cells (%)")
    ax.set_xticks(positions, [r.split("rep")[1] for r in replicates])
    ax.set_xlabel("Replicate")
    ax.tick_params(width=cfg["line_width_pt"], length=2.5)
    ax.spines[["top", "right"]].set_visible(False)
    for group in cfg["group_order"]:
        xx = [x for x, rep in zip(positions, replicates) if rep.startswith(group + "_")]
        ax.text(sum(xx) / len(xx), 1.035, group, ha="center", va="bottom",
                transform=ax.get_xaxis_transform())
    fig.legend(handles[::-1], types[::-1], loc="lower center", bbox_to_anchor=(.55, .005),
               ncol=2, frameon=False, handlelength=1, handletextpad=.4, columnspacing=1)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    canvas = fig.bbox
    from matplotlib.text import Text
    checked = 0
    for artist in fig.findobj(Text):
        if artist.get_visible() and artist.get_text():
            box = artist.get_window_extent(renderer)
            assert box.x0 >= -1 and box.y0 >= -1 and box.x1 <= canvas.width + 1 and box.y1 <= canvas.height + 1, artist.get_text()
            checked += 1
    for fmt in cfg["formats"]:
        fig.savefig(BASE / f"panel.{fmt}", dpi=cfg["dpi"], facecolor="white")
    actual = dict(cfg, actual_font_family=font, actual_font_path=font_path)
    (BASE / "render-settings.json").write_text(json.dumps(actual, indent=2) + "\n")
    report = {"input_rows": len(rows), "source_cell_total": sum(lookup.values()),
              "replicates": len(replicates), "derived_rows": len(derived),
              "epithelial_cell_total": sum(row[3] for row in derived),
              "percent_sums": {rep: sum(percentages[rep]) for rep in replicates},
              "visible_text_boundaries_checked": checked,
              "canvas_inches": list(fig.get_size_inches()),
              "matplotlib_version": matplotlib.__version__}
    (BASE / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    plt.close(fig)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
