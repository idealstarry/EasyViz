#!/usr/bin/env python3
"""Rank bounded literature mechanisms for an adopted Create reading task.

This stdlib-only helper plans design, not analysis. A match is an applicability
hint, never an aesthetic score or permission to change scientific settings.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import math
from pathlib import Path

VERSION = "0.1.0"
TASKS = {
    "compare_estimates", "compare_distributions", "inspect_observations",
    "inspect_density", "assess_association", "read_matrix_values",
    "read_matrix_pattern", "compare_composition", "compare_within_unit_change",
    "compare_trajectories",
}
LEADING_LAYERS = {"observations", "summary", "density", "values"}
ORGANIZATIONS = {"compact", "overlay", "separate_lanes", "aligned_facets", "repeated_groups"}
COLOR_ROLES = {"labels", "summary_areas", "observations", "series", "focus", "magnitude", "direction"}
INTENT_KEYS = {"schema_version", "question", "reading_task", "leading_layer", "organization", "color_role", "mechanism_id"}


def _mechanism(key, families, tasks, source, observation, adaptation, boundary, *, layers=(), conditions=None):
    return {"id": key, "families": families, "reading_tasks": tasks,
            "leading_layers": list(layers), "source": source,
            "observed": observation, "adaptation": adaptation, "boundary": boundary,
            "conditions": conditions or {},
            "evidence": "Observed in the inspected supplied PDF; adaptations are proposed for new data. See references/literature-style.md."}


CATALOG = [
    _mechanism("neutral-single-quantity", ["replicate", "composition"], ["compare_estimates", "compare_composition"],
               "PROGENy Fig. 2d, PDF p. 4; Vanneste Fig. 3e,g, PDF p. 5",
               "Uniform gray bars or decoded black/white/gray compositions have definite boundaries.",
               "Use labels/positions to decode a single quantity; reserve categorical colors for a required second variable.",
               "Multiple series need distinct decoding; neutral is optional, and supplied project colors remain authoritative.",
               layers=("summary",), conditions={"single_series": True}),
    _mechanism("replicate-layer-clearance", ["replicate"], ["compare_estimates", "inspect_observations"],
               "scWAT Fig. 2c,i,j, PDF p. 4; Vanneste Fig. 2e–h, PDF p. 4",
               "Open bars, small observations and visible uncertainty endpoints remain associated.",
               "Plan bar width, sample span and intervals together; open or filled summaries depend on the leading layer.",
               "Summary and uncertainty meanings must already be adopted; hollow is not a universal style.",
               layers=("observations", "summary")),
    _mechanism("repeated-series-rhythm", ["replicate"], ["compare_estimates", "inspect_observations"],
               "scWAT Fig. 3g,m, PDF p. 5; Vanneste Fig. 2g,h, PDF p. 4",
               "Tight within-category series and wider category gaps repeat with a compact shared guide.",
               "Plan stroke clearance, series gap and category pitch separately; adapt the data region to the real comparison.",
               "Do not copy a source aspect ratio, axis break, reference value or significance layer.",
               layers=("summary", "observations"), conditions={"multiple_series": True}),
    _mechanism("compact-one-pair", ["replicate", "distribution"], ["compare_estimates", "compare_distributions", "inspect_observations"],
               "scWAT Fig. 2j, PDF p. 4",
               "One treatment pair occupies a narrow region with readable samples, summaries and uncertainty.",
               "Allocate width from actual mark/label capacity instead of stretching two categories across a broad canvas.",
               "A narrow plot is useful only if labels and every observation still fit at the adopted size.",
               conditions={"maximum_categories": 2}),
    _mechanism("distribution-summary-hierarchy", ["distribution"], ["compare_distributions", "compare_estimates"],
               "PROGENy Fig. 4c, PDF p. 6",
               "Fine neutral density contours, categorical areas and definite inner summaries coexist in compact groups.",
               "Emphasize the adopted summary; raw points and area-color reassignment are explicit adaptations.",
               "Preserve quartiles, KDE and bandwidth; adding an inner summary requires separate adoption.",
               layers=("summary",)),
    _mechanism("distribution-observation-lane", ["distribution"], ["inspect_observations", "compare_distributions"],
               "Vanneste Fig. 5d, PDF p. 7",
               "Repeated aligned plot boxes, shared labels and class blocks separate related populations.",
               "Compare an associated sample lane or shared-scale facets when overlay obscures the adopted comparison.",
               "A neighboring lane is an adaptation; it must retain group association and numeric values, and cannot erase needed pairing.",
               layers=("observations",), conditions={"multiple_categories": True}),
    _mechanism("density-contour-hierarchy", ["distribution"], ["inspect_density", "compare_distributions"],
               "PROGENy Fig. 4c, PDF p. 6",
               "Density silhouettes remain distinct from bounded inner summaries.",
               "Let the adopted density lead only when shape is part of the question; subordinate existing points/summaries without erasing them.",
               "Density must already exist. Small or tied groups may not justify KDE; do not tune bandwidth for a prettier silhouette.",
               layers=("density",), conditions={"kind": "violin"}),
    _mechanism("small-point-class-decoding", ["scatter"], ["assess_association", "inspect_observations"],
               "scWAT Fig. 2g, PDF p. 4",
               "Blue/pink observations and fitted strokes differ from the blue/coral bar treatment elsewhere on the page.",
               "Choose class colors on actual small marks and keys; a usable area palette need not work for tiny points.",
               "A scatter needs a relationship question; a fitted line requires an adopted model. Source hues are not compulsory.",
               layers=("observations",), conditions={"grouped_scatter": True}),
    _mechanism("matrix-shape-first", ["heatmap", "annotated_matrix"], ["read_matrix_values", "read_matrix_pattern"],
               "scWAT Fig. 2b, PDF p. 4",
               "A tall expression matrix retains its few columns as compact reading units.",
               "Plan cell width/height and label capacity from matrix shape before choosing the ramp.",
               "Square cells are optional. Preserve values, ordering and normalization; few columns should not become decorative horizontal ribbons.",
               layers=("values",), conditions={"narrow_matrix": True}),
    _mechanism("matrix-value-seams", ["heatmap", "annotated_matrix"], ["read_matrix_values"],
               "PROGENy Fig. 2b,c, PDF p. 4; Vanneste Fig. 4d, PDF p. 6",
               "Separators vary with cell density; dense tiny-cell heatmaps do not frame every cell equally.",
               "Use subordinate seams for large direct-lookup cells; reserve enough physical space for adopted value labels.",
               "A seam policy is conditional. Colors cannot invent a meaningful center, endpoints or missing-state meaning.",
               layers=("values",)),
    _mechanism("dense-field-summary-separation", ["scatter", "distribution"], ["assess_association", "compare_distributions", "inspect_observations"],
               "Vanneste Fig. 5d, PDF p. 7",
               "A wider declared curve and local white separation remain visible over tiny points.",
               "Give an existing summary enough local contrast or choose separate lanes rather than fading all data.",
               "No curve/model is introduced; a contrasting under-stroke or raw lane is a task-specific adaptation.",
               conditions={"dense_raw_layer": True}),
]

CONTRACT = {
    "version": VERSION,
    "command": "design_mechanisms.py --features FILE [--intent FILE] | --describe-contract",
    "create_intent": {"schema_version": 1, "question": "Adopted scientific reading purpose", "reading_task": sorted(TASKS),
                      "leading_layer": sorted(LEADING_LAYERS), "organization": sorted(ORGANIZATIONS), "color_role": sorted(COLOR_ROLES),
                      "mechanism_id": "Optional selected applicable mechanism; never a whole-paper template"},
    "required_intent_keys": ["schema_version", "question", "reading_task"],
    "features": "Observed prepared-data facts: chart, category_count/group_count, component_count, kind, matrix_rows/columns, dense_raw_layer. Unknown features remain unresolved.",
    "outputs": "ranked applicable and nonapplicable mechanisms with reasons, observed source, proposed adaptation and boundaries; no automatic aesthetic winner",
    "preserved": "Track, rows, experimental units, summaries, models, transforms, scales, explicit colors, fonts and dimensions remain authoritative. Intent is planning metadata, not a renderer or analysis schema.",
}


def validate_intent(value):
    if not isinstance(value, dict) or set(value) - INTENT_KEYS:
        raise ValueError("create_intent must be an object with only the --describe-contract keys")
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise ValueError("create_intent.schema_version must be 1")
    if not isinstance(value.get("question"), str) or not value["question"].strip() or len(value["question"]) > 4000:
        raise ValueError("create_intent.question must name a nonempty adopted purpose (at most 4000 characters)")
    if not isinstance(value.get("reading_task"), str) or value["reading_task"] not in TASKS:
        raise ValueError("Unknown create_intent.reading_task; inspect --describe-contract")
    for key, choices in (("leading_layer", LEADING_LAYERS), ("organization", ORGANIZATIONS), ("color_role", COLOR_ROLES)):
        if key in value and (not isinstance(value[key], str) or value[key] not in choices):
            raise ValueError("Unknown create_intent." + key + "; inspect --describe-contract")
    if "mechanism_id" in value and (not isinstance(value["mechanism_id"], str) or value["mechanism_id"] not in {m["id"] for m in CATALOG}):
        raise ValueError("Unknown create_intent.mechanism_id")
    return deepcopy(value)


def _condition_reasons(conditions, features):
    reasons, unknown = [], []
    count = features.get("category_count", features.get("group_count"))
    for key, wanted in conditions.items():
        if key == "single_series":
            actual = features.get("component_count", 1 if features.get("mode") == "summary" else None)
            fits = actual == 1
        elif key == "multiple_series":
            actual = features.get("component_count")
            fits = actual is not None and actual > 1
        elif key == "maximum_categories":
            actual, fits = count, count is not None and count <= wanted
        elif key == "multiple_categories":
            actual, fits = count, count is not None and count > 1
        elif key == "narrow_matrix":
            actual = features.get("matrix_columns")
            rows = features.get("matrix_rows")
            fits = actual is not None and rows is not None and actual <= 4 and rows >= actual * 2
            if rows is None:
                actual = None
        elif key == "grouped_scatter":
            actual = features.get("group_count")
            fits = actual is not None and actual > 1
        else:
            actual = features.get(key)
            fits = actual == wanted
        if actual is None:
            unknown.append("Need observed " + key + " before this mechanism's applicability is established")
        elif not fits:
            reasons.append("Observed data do not meet " + key + "=" + str(wanted))
    return reasons, unknown


def rank_mechanisms(features, intent=None):
    if not isinstance(features, dict) or not isinstance(features.get("chart"), str):
        raise ValueError("features must declare the observed chart family")
    # Counts are observed facts, not permissive coercions or inference from names.
    for key in ("category_count", "group_count", "component_count", "matrix_rows", "matrix_columns"):
        if key in features and (type(features[key]) is not int or features[key] < 0):
            raise ValueError("features." + key + " must be a nonnegative integer")
    if "dense_raw_layer" in features and type(features["dense_raw_layer"]) is not bool:
        raise ValueError("features.dense_raw_layer must be an observed boolean")
    intent = validate_intent(intent) if intent is not None else None
    records = []
    for mechanism in CATALOG:
        item = deepcopy(mechanism)
        reasons, unknown = _condition_reasons(item.pop("conditions"), features)
        if features["chart"] not in item["families"]:
            reasons.append("Different chart family")
        if intent and intent["reading_task"] not in item["reading_tasks"]:
            reasons.append("Does not address the adopted reading task")
        applicable = not reasons and not unknown
        score = (2 if intent else 0) + (1 if intent and intent.get("leading_layer") in item["leading_layers"] else 0)
        if intent and intent.get("mechanism_id") == item["id"]:
            score += 10
        item.update(applicability="applicable" if applicable else "unresolved" if not reasons else "not_applicable",
                    applicability_score=score if applicable else 0,
                    reasons=reasons + unknown or ["Observed family/burden fit" + (" and adopted purpose fit" if intent else "; scientific purpose remains to be adopted")])
        records.append(item)
    records.sort(key=lambda item: (-item["applicability_score"], item["applicability"] != "applicable", item["id"]))
    if intent and "mechanism_id" in intent:
        selected = next(item for item in records if item["id"] == intent["mechanism_id"])
        if selected["applicability"] != "applicable":
            raise ValueError("Selected mechanism is not established as applicable: " + "; ".join(selected["reasons"]))
    return {"version": VERSION, "adopted_intent": intent, "mechanisms": records,
            "ranking_scope": "Applicability to observed burden and adopted purpose; no beauty score, method selection or automatic winner."}


def physical_preflight(features, geometry):
    """Describe measured capacity separately from task-dependent aesthetics."""
    region = geometry["data_region_mm"]
    width, height = region[2:4]
    if not all(isinstance(x, (float, int)) and not isinstance(x, bool) and math.isfinite(x) and x > 0 for x in (width, height)):
        raise ValueError("Physical preflight needs a finite positive measured data region")
    failures, advisory = [], []
    measured = {"data_region_width_mm": width, "data_region_height_mm": height,
                "data_region_aspect": width / height,
                "category_pitch_mm": geometry.get("category_pitch_mm"),
                "summary_thickness_mm": geometry.get("summary_thickness_mm"),
                "cell_dimensions_mm": geometry.get("cell_dimensions_mm"),
                "guide_geometry": deepcopy(geometry.get("guide_geometry"))}
    if geometry.get("technical_measurement_status") == "needs_revision":
        failures.extend(geometry.get("issues", []))
    if features["chart"] == "distribution":
        crossings = geometry.get("raw_summary_categorical_envelope_crossings", 0)
        if crossings:
            advisory.append({"kind": "raw_summary_association", "observed_crossings": crossings,
                             "action": "Inspect actual median/contour visibility; envelope crossings alone do not mean a collision or require a separate lane."})
    if features["chart"] == "heatmap":
        cells = geometry.get("cell_dimensions_mm", [])
        if len(cells) == 2:
            measured["cell_aspect"] = cells[0] / cells[1]
            advisory.append({"kind": "matrix_shape", "action": "Judge cells and label capacity against the reading task; no square-cell or literature-ratio requirement."})
    advisory.extend(geometry.get("mark_visibility_advisories", []))
    return {"status": "needs_revision" if failures else "capacity_checked",
            "capacity_failures": list(dict.fromkeys(failures)), "measurements": measured,
            "design_advisories": advisory,
            "scope": "Actual artist capacity evidence; ratios and contrast hints are not universal publication rules. Open the final-size exports to judge hierarchy and aesthetics."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path)
    parser.add_argument("--intent", type=Path)
    parser.add_argument("--describe-contract", action="store_true")
    args = parser.parse_args()
    if args.describe_contract:
        print(json.dumps(CONTRACT, indent=2))
        return
    if not args.features:
        parser.error("--features is required")
    try:
        result = rank_mechanisms(json.loads(args.features.read_text()), json.loads(args.intent.read_text()) if args.intent else None)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"EasyViz design: {exc}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
