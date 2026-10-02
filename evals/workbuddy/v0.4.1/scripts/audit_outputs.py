#!/usr/bin/env python3
"""Audit source/table/export facts, without treating them as visual quality proof."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image
from pypdf import PdfReader
from pypdf.generic import ContentStream

BASE = Path(__file__).resolve().parents[1]


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def finite(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("A measured value is not finite")
    return parsed


def number_mm(value: str) -> float:
    match = re.fullmatch(r"\s*([0-9.eE+-]+)\s*(mm|cm|in|pt|px)?\s*", value)
    if not match:
        raise ValueError(f"Unknown SVG physical length: {value}")
    unit = match[2] or "px"
    return float(match[1]) * {"mm": 1, "cm": 10, "in": 25.4,
                            "pt": 25.4 / 72, "px": 25.4 / 96}[unit]


def font_details(page, reader) -> dict:
    def resolve(value):
        return value.get_object() if hasattr(value, "get_object") else value
    resources = resolve(page.get("/Resources", {}))
    fonts = resolve(resources.get("/Font", {}))
    details = []
    for key, indirect in fonts.items():
        font = indirect.get_object()
        descendants = font.get("/DescendantFonts", [])
        concrete = descendants[0].get_object() if descendants else font
        descriptor = concrete.get("/FontDescriptor")
        descriptor = descriptor.get_object() if descriptor else {}
        embedded_file = any(name in descriptor for name in ["/FontFile", "/FontFile2", "/FontFile3"])
        embedded_type3 = font.get("/Subtype") == "/Type3" and bool(font.get("/CharProcs"))
        embedded = embedded_file or embedded_type3
        details.append({"resource": str(key), "basefont": str(font.get("/BaseFont", "")),
                        "subtype": str(font.get("/Subtype", "")), "embedded": embedded,
                        "embedding": "font_file" if embedded_file else "type3_charprocs" if embedded_type3 else None})
    sizes = sorted({float(operands[1]) for operands, operator in ContentStream(page.get_contents(), reader).operations
                    if operator == b"Tf" and len(operands) >= 2})
    return {"fonts": details, "direct_text_operator_sizes_pt": sizes,
            "limitation": "Direct page operators only; transformed form text requires manual inspection."}


def artifact_path(project: Path, requested: Path | str) -> dict:
    """Resolve a declared relative artifact without following an escape for reads."""
    requested = Path(requested)
    root = project.resolve()
    record = {"requested": str(requested), "resolved": None,
              "inside_project": False, "exists": False, "nonempty": False}
    try:
        if requested.is_absolute():
            raise ValueError("Artifact overrides must be relative to the project")
        resolved = (root / requested).resolve()
        record["resolved"] = str(resolved)
        if not resolved.is_relative_to(root):
            raise ValueError("Artifact path escapes the project, including through a symlink")
        record["inside_project"] = True
        record["exists"] = resolved.is_file()
        record["nonempty"] = resolved.is_file() and resolved.stat().st_size > 0
    except (OSError, RuntimeError, ValueError) as error:
        record["error"] = f"{type(error).__name__}: {error}"
    return record


def audit(project: Path, task: str, *, settings: Path | str | None = None,
          script: Path | str | None = None, reading: Path | str | None = None) -> dict:
    output = project / "output"
    checks = []
    facts = {}

    def check(name: str, ok: bool, detail) -> None:
        checks.append({"name": name, "pass": bool(ok), "detail": detail})

    expected_files = {str(p.relative_to(BASE / "fixtures" / task)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted((BASE / "fixtures" / task).rglob("*")) if p.is_file()}
    actual_files = {str(p.relative_to(project / "input")): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted((project / "input").rglob("*")) if p.is_file()}
    check("source_inputs_unchanged", expected_files == actual_files,
          {"expected_files": len(expected_files), "actual_files": len(actual_files)})
    try:
        actual = rows(output / "plotting_data.csv")
        if task == "create":
            expected = rows(BASE / "evaluator/expected-create.csv")
            indexed = {row["specimen_id"]: row for row in actual}
            expected_index = {row["specimen_id"]: row for row in expected}
            check("all_independent_units_once", len(actual) == len(indexed) == 36 and set(indexed) == set(expected_index),
                  {"rows": len(actual), "unique_units": len(indexed), "expected_units": 36})
            mismatches = []
            for key, row in expected_index.items():
                other = indexed.get(key)
                if other is None or other.get("group") != row["group"] or not math.isclose(
                        finite(other["mean_signal"]), finite(row["mean_signal"]), abs_tol=1e-7, rel_tol=0):
                    mismatches.append(key)
            check("literal_join_groups_and_technical_means", not mismatches, {"mismatched_units": mismatches})
            counts = {group: sum(row.get("group") == group for row in actual)
                      for group in ["Vehicle", "Low dose", "High dose"]}
            check("biological_n_is_twelve_per_arm", all(count == 12 for count in counts.values()), counts)
            facts["plotting_rows"] = len(actual)
        else:
            expected = rows(BASE / "evaluator/expected-reproduce.csv")
            indexed = {(row["analyte"], row["specimen"]): row for row in actual}
            expected_index = {(row["analyte"], row["specimen"]): row for row in expected}
            check("all_target_coordinates_once", len(actual) == len(indexed) == 72 and set(indexed) == set(expected_index),
                  {"rows": len(actual), "unique_coordinates": len(indexed)})
            mismatches, state_errors = [], []
            for key, row in expected_index.items():
                other = indexed.get(key)
                if other is None:
                    mismatches.append(key)
                    continue
                if other.get("measurement_state") != row["measurement_state"]:
                    state_errors.append(key)
                if row["measurement_state"] == "unmeasured":
                    if other.get("z_score", "").strip().lower() not in ["", "nan", "na", "null"]:
                        mismatches.append(key)
                elif not math.isclose(finite(other["z_score"]), finite(row["z_score"]), abs_tol=1e-9, rel_tol=0):
                    mismatches.append(key)
            check("target_scores_unchanged_not_reference_pixels", not mismatches, {"mismatched_coordinates": mismatches})
            check("missing_states_distinct_from_measured_zero", not state_errors,
                  {"state_errors": state_errors, "expected_unmeasured": 3, "expected_measured_zero": 1})
            actual_means = rows(output / "feature-means.csv")
            expected_means = rows(BASE / "evaluator/expected-reproduce-means.csv")
            indexed_means = {row["analyte"]: row for row in actual_means}
            mean_errors = []
            for row in expected_means:
                other = indexed_means.get(row["analyte"])
                if other is None or int(other["measured_count"]) != int(row["measured_count"]) or not math.isclose(
                        finite(other["mean_z_score"]), finite(row["mean_z_score"]), abs_tol=1e-6, rel_tol=0):
                    mean_errors.append(row["analyte"])
            check("feature_means_skip_only_explicitly_unmeasured", not mean_errors and len(actual_means) == 8,
                  {"mismatched_features": mean_errors, "rows": len(actual_means)})
            facts["plotting_rows"] = len(actual)
    except Exception as error:
        check("plotting_tables_parse_and_validate", False, f"{type(error).__name__}: {error}")

    try:
        svg = ET.parse(output / "panel.svg").getroot()
        svg_mm = [number_mm(svg.attrib[axis]) for axis in ["width", "height"]]
        text_nodes = [node for node in svg.iter() if node.tag.split("}")[-1] == "text"]
        check("svg_full_canvas_120x90mm", all(abs(a - b) <= .02 for a, b in zip(svg_mm, [120, 90])), svg_mm)
        check("svg_retains_text_elements", bool(text_nodes), {"text_nodes": len(text_nodes)})
        facts["svg_viewbox"] = svg.get("viewBox")
    except Exception as error:
        check("svg_readable", False, f"{type(error).__name__}: {error}")
    try:
        reader = PdfReader(output / "panel.pdf")
        dims = [[float(page.mediabox.width) * 25.4 / 72, float(page.mediabox.height) * 25.4 / 72]
                for page in reader.pages]
        check("pdf_one_full_canvas_120x90mm", len(dims) == 1 and all(abs(a - b) <= .02 for a, b in zip(dims[0], [120, 90])), dims)
        details = font_details(reader.pages[0], reader)
        facts["pdf_text"] = details
        check("pdf_direct_page_Arial_embedded", bool(details["fonts"]) and all(
            "Arial" in font["basefont"] and font["embedded"] for font in details["fonts"]), details["fonts"])
        check("pdf_direct_text_sizes_8pt", bool(details["direct_text_operator_sizes_pt"]) and all(
            abs(size - 8) < .01 for size in details["direct_text_operator_sizes_pt"]), details["direct_text_operator_sizes_pt"])
    except Exception as error:
        check("pdf_readable", False, f"{type(error).__name__}: {error}")
    try:
        with Image.open(output / "panel.png") as png:
            size = list(png.size)
            dpi = png.info.get("dpi")
        check("png_dimensions_match_300dpi_full_canvas", all(abs(a - b) <= 1 for a, b in zip(size, [1417, 1063])), size)
        check("png_records_300dpi", dpi is not None and all(abs(item - 300) <= .05 for item in dpi), dpi)
    except Exception as error:
        check("png_readable", False, f"{type(error).__name__}: {error}")
    declared_paths = {"settings": artifact_path(project, settings if settings is not None else "output/settings.json")}
    declared_paths["settings"]["override"] = settings is not None
    check("has_settings.json", declared_paths["settings"]["nonempty"], declared_paths["settings"])
    for name in ["caption.md", "review.md"]:
        record = artifact_path(project, Path("output") / name)
        check(f"has_{name}", record["nonempty"], record)
    script_paths = [artifact_path(project, script)] if script is not None else [
        artifact_path(project, path.relative_to(project)) for path in sorted(output.glob("*.py"))]
    declared_paths["script"] = {"override": script is not None, "candidates": script_paths}
    check("has_python_plot_script", any(record["exists"] for record in script_paths),
          {**declared_paths["script"], "limitation": "Existence only; code semantics and rerun portability require separate checks."})
    if task == "reproduce":
        reading_paths = [artifact_path(project, reading)] if reading is not None else [
            artifact_path(project, name) for name in ["output/reference-reading.md", "reference-reading.md"]]
        declared_paths["reading"] = {"override": reading is not None, "candidates": reading_paths}
        check("has_reference_reading", any(record["exists"] for record in reading_paths),
              {**declared_paths["reading"], "limitation": "Existence only; content and independence require actual log/image evidence."})
    facts["artifact_paths"] = declared_paths
    artifacts = {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(output.rglob("*")) if p.is_file() and "__pycache__" not in p.parts
                 and artifact_path(project, p.relative_to(project))["inside_project"]}
    return {"task": task, "project": str(project), "checks": checks, "pass": all(item["pass"] for item in checks),
            "facts": facts, "output_sha256": artifacts,
            "limits": ["Tables do not prove marks use those values: inspect code/rendered layer mappings.",
                       "No automatic statistical-method correctness or aesthetics verdict.",
                       "Input restrictions are instructions, not OS-enforced access isolation.",
                       "No rerun claim until an isolated rerun has actually succeeded."]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--task", required=True, choices=["create", "reproduce"])
    parser.add_argument("--report", type=Path)
    parser.add_argument("--settings", type=Path, help="Explicit settings artifact, relative to the project")
    parser.add_argument("--script", type=Path, help="Explicit plotting script, relative to the project")
    parser.add_argument("--reading", type=Path, help="Explicit reference-reading artifact, relative to the project")
    args = parser.parse_args()
    report = audit(args.project, args.task, settings=args.settings, script=args.script, reading=args.reading)
    encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded, encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
