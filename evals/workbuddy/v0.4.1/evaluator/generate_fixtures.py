#!/usr/bin/env python3
"""Build synthetic fixtures and evaluator truth; never expose this to a run."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/easyviz-v041-fixture-mpl")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np

BASE = Path(__file__).resolve().parents[1]


def table(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def create_fixture() -> dict:
    root = BASE / "fixtures/create/data"
    rng = np.random.default_rng(740103)
    groups = ["Vehicle", "Low dose", "High dose"]
    metadata, measurements, truth = [], [], []
    for index in range(36):
        key = f"{index + 1:04d}"
        group = groups[index // 12]
        # Substantial overlap avoids a cartoonishly effortless comparison.
        biological = [92, 105, 122][index // 12] + rng.normal(0, 15)
        tech_values = []
        for repeat in range(2):
            read_key = f"R{index + 1:03d}_{repeat + 1}"
            missing = index == 7 and repeat == 1
            value = round(biological + rng.normal(0, 2.1), 4)
            if not missing:
                tech_values.append(value)
            measurements.append({"read_key": read_key, "tube_key": key,
                                 "signal_au": "" if missing else f"{value:.4f}",
                                 "read_state": "instrument_failure" if missing else "measured",
                                 "scan_order": 72 - (index * 2 + repeat)})
        metadata.append({"tube_key": key, "arm_name": group,
                         "rack": f"B{index % 3 + 1}", "unit_type": "individual_mouse"})
        truth.append({"specimen_id": key, "group": group,
                      "mean_signal": f"{np.mean(tech_values):.10f}",
                      "measured_technical_reads": len(tech_values)})
    # Deliberately different row orders prevent positional joins.
    rng.shuffle(metadata)
    rng.shuffle(measurements)
    table(root / "A_export__final2.csv", list(measurements[0]), measurements)
    table(root / "sample-index__2026.tsv.csv", list(metadata[0]), metadata)
    table(root / "old-pilot_DO_NOT_POOL.csv", ["tube_key", "arm_name", "signal_au"],
          [{"tube_key": f"{i:04d}", "arm_name": "Vehicle", "signal_au": 400 + i}
           for i in range(1, 7)])
    table(root / "plate-blank_readings.csv", ["tube_key", "signal_au", "meaning"],
          [{"tube_key": "blank", "signal_au": 2.6, "meaning": "daily instrument blank"}])
    table(root / "instrument-log.csv", ["date", "message"],
          [{"date": "2026-09-30", "message": "one reading failed; raw values already background corrected"}])
    (root / "DATA_DICTIONARY.md").write_text(
        "# Study and field meanings\n\n"
        "This is a synthetic teaching dataset. Current experiment: 36 independently sampled mice, "
        "12 mice in each of Vehicle, Low dose, High dose. Each mouse belongs to exactly one arm. "
        "There is no pairing or longitudinal design. Each mouse has two technical instrument reads; "
        "one read failed.\n\n"
        "- `A_export__final2.csv`: current technical reads. `tube_key` is a literal identifier, "
        "including leading zeros; `signal_au` is background-corrected fluorescence in arbitrary "
        "units. Empty failed read is missing, never zero. `scan_order` is instrument order, not time.\n"
        "- `sample-index__2026.tsv.csv`: current sample-to-arm lookup. Join on literal `tube_key`; "
        "row order differs. `rack` is a handling batch balanced across arms, not another experimental unit.\n"
        "- `old-pilot_DO_NOT_POOL.csv`: separate historical pilot, with reused identifiers; do not combine.\n"
        "- `plate-blank_readings.csv`: instrument QC only; do not subtract again or count as specimens.\n"
        "- `instrument-log.csv`: notes only.\n\n"
        "The analysis unit is one mouse. Average its available measured technical reads first; "
        "retain all 36 mice, including the mouse with one measured read. The main question is whether "
        "the distributions shift with dose relative to Vehicle. Describe all arms and, if doing "
        "inference, justify the independent-unit method, state effect direction, and correct the "
        "two comparisons to Vehicle as one family. No other covariate analysis is required.\n",
        encoding="utf-8")
    table(BASE / "evaluator/expected-create.csv", list(truth[0]), truth)
    return {"unit_count": 36, "group_counts": dict.fromkeys(groups, 12),
            "technical_rows": 72, "measured_reads": 71,
            "failed_read_unit": "0008", "mean_rule": "mean of available measured technical reads"}


def reproduce_fixture() -> dict:
    root = BASE / "fixtures/reproduce"
    data_root = root / "data"
    samples = [f"S{i:02d}" for i in range(1, 10)]
    features = ["Signal_A", "Signal_B", "Signal_C", "Signal_D", "Signal_E", "Signal_F", "Signal_G", "Signal_H"]
    groups = ["Baseline"] * 3 + ["Compound X"] * 3 + ["Compound Y"] * 3
    rng = np.random.default_rng(740104)
    values = np.round(rng.normal(0, 0.85, (8, 9)), 3)
    values[0, 3:6] += 0.70
    values[3, 6:] -= 0.70
    values = np.clip(np.round(values, 3), -2, 2)
    values[1, 4] = np.nan
    values[6, 0] = np.nan
    values[7, 8] = np.nan
    values[4, 6] = 0.0
    rows = []
    for i, feature in enumerate(features):
        for j, sample in enumerate(samples):
            val = values[i, j]
            rows.append({"analyte": feature, "specimen": sample,
                         "z_score": "" if np.isnan(val) else f"{val:.3f}",
                         "measurement_state": "unmeasured" if np.isnan(val) else "measured"})
    shuffled = rows.copy()
    rng.shuffle(shuffled)
    table(data_root / "target-values.csv", list(rows[0]), shuffled)
    table(data_root / "target-samples.csv", ["specimen", "condition", "display_order"],
          [{"specimen": samples[i], "condition": groups[i], "display_order": i + 1}
           for i in [6, 1, 8, 0, 5, 2, 7, 3, 4]])
    (data_root / "DATA_DICTIONARY.md").write_text(
        "# Supplied target data\n\nThis synthetic dataset supplies 72 feature/sample coordinates. "
        "`z_score` is an already computed upstream standardized score, dimensionless. "
        "Do not recompute normalization. Three coordinates are explicitly unmeasured with empty scores; "
        "one measured score is exactly zero. There are no absent coordinates.\n\n"
        "Join `specimen` to `target-samples.csv`; sort columns by its numeric `display_order` "
        "and rows Signal_A through Signal_H. Use the same order in every layer. "
        "Group mapping is Baseline (S01–S03), Compound X (S04–S06), Compound Y (S07–S09). "
        "For the right marginal summary, use each feature's arithmetic mean across all its measured "
        "target samples (do not replace missing with zero). This is a descriptive mean, without "
        "an uncertainty interval or inferential test. The main heatmap uses fixed symmetric limits "
        "−2 and +2 with zero at the neutral center. Explicitly decode unmeasured cells separately.\n\n"
        "The supplied reference is an original synthetic style target created for this evaluation; "
        "its numeric values and displayed names are not target data. Read its visible structure, "
        "then reproduce the aligned top condition strip, main heatmap, right feature means, "
        "diverging colorbar, and compact category guide using the target data. "
        "No author code or paper Source Data is available or required.\n", encoding="utf-8")
    table(BASE / "evaluator/expected-reproduce.csv", list(rows[0]), rows)
    means = [{"analyte": name, "mean_z_score": f"{np.nanmean(values[i]):.10f}",
              "measured_count": int(np.isfinite(values[i]).sum())} for i, name in enumerate(features)]
    table(BASE / "evaluator/expected-reproduce-means.csv", list(means[0]), means)

    # Reference values/names are independent of target data. Only the PNG is exposed.
    reference_values = np.round(rng.normal(0, .80, (8, 9)), 3)
    reference_values[1, 2] = np.nan
    reference_values[5, 7] = np.nan
    reference_values[2, 3:6] += .75
    reference_values = np.clip(reference_values, -2, 2)
    plt.rcParams.update({"font.family": "Arial", "font.size": 8, "axes.labelsize": 8,
                         "xtick.labelsize": 8, "ytick.labelsize": 8, "svg.fonttype": "none"})
    fig = plt.figure(figsize=(120 / 25.4, 90 / 25.4), dpi=300, facecolor="white")
    heat = fig.add_axes([.225, .235, .49, .56])
    strip = fig.add_axes([.225, .815, .49, .035])
    mean_ax = fig.add_axes([.755, .235, .17, .56], sharey=heat)
    color_ax = fig.add_axes([.225, .090, .27, .026])
    cmap = matplotlib.colormaps["RdBu_r"].copy()
    cmap.set_bad("#D6D9DE")
    im = heat.imshow(reference_values, cmap=cmap, vmin=-2, vmax=2, aspect="auto", interpolation="none")
    heat.set_xticks(range(9), [f"R{i:02d}" for i in range(1, 10)], rotation=90)
    heat.set_yticks(range(8), [f"Marker {c}" for c in "ABCDEFGH"])
    heat.tick_params(length=0, pad=3)
    for edge in heat.spines.values():
        edge.set_visible(False)
    categorical = ["#5F789D", "#D6A052", "#438E83"]
    strip.imshow(np.array([[0, 0, 0, 1, 1, 1, 2, 2, 2]]), cmap=ListedColormap(categorical),
                 vmin=0, vmax=2, aspect="auto", interpolation="none")
    strip.set_axis_off()
    means_ref = np.nanmean(reference_values, axis=1)
    mean_ax.barh(range(8), means_ref, height=.55, color="#6F7D8C", edgecolor="none")
    mean_ax.axvline(0, color="#B8BDC5", linewidth=.6, zorder=0)
    mean_ax.set_ylim(7.5, -.5)
    mean_ax.set_xlim(-1, 1)
    mean_ax.set_xticks([-1, 0, 1])
    mean_ax.set_xlabel("Mean score", labelpad=4)
    mean_ax.tick_params(axis="y", left=False, labelleft=False)
    mean_ax.tick_params(axis="x", length=2, width=.6)
    for edge in ["top", "left", "right"]:
        mean_ax.spines[edge].set_visible(False)
    mean_ax.spines["bottom"].set_linewidth(.6)
    cb = fig.colorbar(im, cax=color_ax, orientation="horizontal", ticks=[-2, 0, 2])
    cb.set_label("Standardized score", labelpad=3)
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=2, width=.6)
    from matplotlib.patches import Patch
    fig.legend([Patch(facecolor=c, edgecolor="none") for c in categorical],
               ["Control", "Treatment A", "Treatment B"], frameon=False, ncol=3,
               loc="upper left", bbox_to_anchor=(.205, .972), handlelength=1,
               handleheight=.65, handletextpad=.4, columnspacing=1.1, borderaxespad=0)
    fig.legend([Patch(facecolor="#D6D9DE", edgecolor="none")], ["Unmeasured"],
               frameon=False, loc="upper left", bbox_to_anchor=(.62, .14),
               handlelength=1, handleheight=.65, handletextpad=.4, borderaxespad=0)
    fig.savefig(root / "reference.png", dpi=300)
    plt.close(fig)
    return {"coordinates": 72, "measured_count": 69, "unmeasured_count": 3,
            "measured_zero": {"analyte": "Signal_E", "specimen": "S07"},
            "row_order": features, "column_order": samples,
            "color_limits": [-2, 2], "mean_rule": "feature mean of measured target samples"}


def main() -> None:
    truth = {"synthetic": True, "create": create_fixture(), "reproduce": reproduce_fixture(),
             "export": {"width_mm": 120, "height_mm": 90, "font_family": "Arial", "font_pt": 8,
                        "dpi": 300, "formats": ["pdf", "svg", "png"]}}
    (BASE / "evaluator/expectations.json").write_text(json.dumps(truth, indent=2) + "\n")
    hashes = {str(path.relative_to(BASE)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted((BASE / "fixtures").rglob("*")) if path.is_file()}
    (BASE / "fixture-hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")
    print(BASE / "fixtures")


if __name__ == "__main__":
    main()
