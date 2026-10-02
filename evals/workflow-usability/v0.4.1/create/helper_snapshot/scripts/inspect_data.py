#!/usr/bin/env python3
"""Inventory local tables and propose bounded create-track reading tasks.

Source cells remain strings. Type hints do not establish scientific meanings,
experimental units or an inferential analysis. This command runs no inferential tests.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import date, datetime
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile


SCHEMA_VERSION = 1
LIMITS = {"tables": 100, "file_bytes": 20 * 1024 * 1024,
          "total_bytes": 100 * 1024 * 1024, "rows_per_table": 100_000,
          "columns": 200, "directory_entries": 10_000, "depth": 8}
EXCLUDED_DIRS = {".git", "__pycache__", "node_modules", "venv", ".venv", "env",
                 "dist", "build", "out", "output", "outputs"}
TABLE_SUFFIXES = {".csv", ".tsv", ".xlsx"}
DEFAULT_MISSING = ["", "NA", "N/A", "NaN", "nan", "NULL", "null", "None"]
ID_NAME = re.compile(r"(^|[_ .-])(id|sample|subject|patient|donor|replicate)([_ .-]|$)", re.I)
LEADING_ZERO = re.compile(r"^[+-]?0\d+$")
GENERIC_NAME = re.compile(r"^(?:x|y|z|a|b|c|value|values|data|variable|column|col|var|v)(?:[_ .-]?\d+)?$", re.I)
COORDINATE_NAME = re.compile(r"(^|[_ .-])(x|time|timepoint|dose|concentration)([_ .-]|$)", re.I)
NAME_ROLES = {
    "estimate": {"mean", "median", "estimate", "effect", "coefficient", "coef"},
    "spread": {"sd", "std", "stdev"},
    "standard_error": {"se", "sem", "stderr"},
    "lower_bound": {"lower", "low", "lcl"},
    "upper_bound": {"upper", "high", "ucl"},
    "count": {"n", "count", "size"},
}


class IntakeError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise IntakeError(message)


def _finite_number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _date_hint(value):
    try:
        if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            date.fromisoformat(value)
        elif re.match(r"^\d{4}-\d{2}-\d{2}[T ]", value):
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            return False
        return True
    except ValueError:
        return False


def _bare_column_name(name):
    return re.sub(r"(?:\([^()]+\)|\[[^\[\]]+\])\s*$", "", name).strip()


def _inclusive_quantile(ordered, numerator, denominator):
    """Interpolate original finite floats with exact rational weights.

    Global normalization can erase tiny observations; a direct (a + b) / 2
    can overflow. The weighted result lies between its finite endpoints.
    """
    index, remainder = divmod((len(ordered) - 1) * numerator, denominator)
    if remainder == 0:
        return ordered[index]
    return float((Fraction(ordered[index]) * (denominator - remainder) +
                  Fraction(ordered[index + 1]) * remainder) / denominator)


def _hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _discovery(root, out):
    skipped, found, visited = [], [], 0

    def walk(directory, depth):
        nonlocal visited
        if depth > LIMITS["depth"]:
            skipped.append({"path": str(directory.relative_to(root)), "reason": "directory depth limit"})
            return
        try:
            entries = sorted(directory.iterdir(), key=lambda path: path.name.casefold())
        except OSError as exc:
            skipped.append({"path": str(directory.relative_to(root)), "reason": f"cannot list directory: {exc}"})
            return
        for path in entries:
            visited += 1
            if visited > LIMITS["directory_entries"]:
                return
            relative = str(path.relative_to(root))
            if path.is_symlink():
                skipped.append({"path": relative, "reason": "symlink; inspect an explicit real path instead"})
            elif path.name.startswith(".") or path.name in EXCLUDED_DIRS or path.resolve() == out:
                skipped.append({"path": relative, "reason": "hidden, generated output or dependency directory"})
            elif path.is_dir():
                walk(path, depth + 1)
            elif path.is_file() and path.suffix.lower() in TABLE_SUFFIXES:
                found.append(path)
    walk(root, 0)
    if visited > LIMITS["directory_entries"]:
        skipped.append({"path": ".", "reason": "directory entry limit; inspect a narrower input directory"})
    return found, skipped


def _headers(raw, source):
    require(bool(raw), f"{source}: empty table; supply a header and observation rows")
    require(len(raw) <= LIMITS["columns"], f"{source}: more than {LIMITS['columns']} columns; inspect a narrower table")
    headers = [str(value) if value is not None else "" for value in raw]
    require(all(value.strip() for value in headers), f"{source}: empty column name; name every column explicitly")
    require(len(set(headers)) == len(headers), f"{source}: duplicate column names; disambiguate the header first")
    return headers


def _read_rows(iterator, headers, source, *, spreadsheet=False):
    rows, truncated = [], False
    for source_row, raw in enumerate(iterator, start=2):
        if spreadsheet and all(value is None for value in raw):
            # Empty Excel rows do not supply observations; this is explicit in
            # table notes. CSV blank records are likewise skipped by csv.reader.
            continue
        if not raw:
            continue
        require(len(raw) == len(headers), f"{source}: row {source_row} has {len(raw)} cells; expected {len(headers)}")
        if len(rows) >= LIMITS["rows_per_table"]:
            truncated = True
            break
        converted = []
        for value in raw:
            if value is None:
                converted.append("")
            elif isinstance(value, (datetime, date)):
                converted.append(value.isoformat())
            elif isinstance(value, bool):
                converted.append("true" if value else "false")
            else:
                converted.append(str(value))
        rows.append(converted)
    return rows, truncated


def _read_csv(path):
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, delimiter="\t" if path.suffix.lower() == ".tsv" else ",", strict=True)
            headers = _headers(next(reader, None), path.name)
            rows, truncated = _read_rows(reader, headers, path.name)
        return [(None, headers, rows, truncated, [])]
    except UnicodeError:
        raise IntakeError(f"{path.name}: not UTF-8 text; save a UTF-8 CSV/TSV before inspection") from None
    except csv.Error as exc:
        raise IntakeError(f"{path.name}: malformed delimited text: {exc}") from None


def _read_xlsx(path):
    try:
        import openpyxl
    except ImportError:
        raise IntakeError("XLSX needs openpyxl; install the EasyViz runtime requirements or export UTF-8 CSV") from None
    tables, errors = [], []
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=False)
    try:
        for sheet in workbook.worksheets[:LIMITS["tables"]]:
            iterator = sheet.iter_rows(values_only=True)
            raw = next(iterator, None)
            if not raw or all(value is None for value in raw):
                continue
            try:
                headers = _headers(raw, f"{path.name}:{sheet.title}")
                rows, truncated = _read_rows(iterator, headers, f"{path.name}:{sheet.title}", spreadsheet=True)
            except IntakeError as exc:
                errors.append({"path": f"{path.name}::{sheet.title}", "reason": str(exc)})
                continue
            notes = ["Excel stored values are converted to strings; number formats are not applied.",
                     "Formulas remain formula text and are never executed; blank worksheet rows are skipped."]
            tables.append((sheet.title, headers, rows, truncated, notes))
    finally:
        workbook.close()
    return tables, errors


def _column(name, values, missing_tokens):
    present = [value for value in values if value not in missing_tokens]
    distinct = list(dict.fromkeys(present))
    leading_zero = any(LEADING_ZERO.fullmatch(value.strip()) for value in present)
    formula_count = sum(value.startswith("=") for value in present)
    numerical = [_finite_number(value.strip()) for value in present]
    n_numeric = sum(value is not None for value in numerical)
    identifier_hint = bool(ID_NAME.search(name)) or name.lower().endswith("_id") or leading_zero
    if not present:
        hint = "empty"
    elif identifier_hint:
        hint = "identifier_candidate"
    elif n_numeric == len(present):
        hint = "numeric"
    elif all(_date_hint(value.strip()) for value in present):
        hint = "date_time_candidate"
    elif set(value.casefold().strip() for value in present) <= {"true", "false", "yes", "no"}:
        hint = "boolean_candidate"
    elif len(distinct) <= 30:
        hint = "categorical_candidate"
    else:
        hint = "text"
    result = {"name": name, "storage": "string", "type_hint": hint,
              "missing": len(values) - len(present), "nonmissing": len(present),
              "unique_nonmissing": len(distinct), "duplicate_nonmissing": len(present) - len(distinct),
              "leading_zero_values": leading_zero, "formula_cells": formula_count,
              "examples": [value[:160] for value in distinct[:5]],
              "numeric_parseable": n_numeric}
    words = set(re.findall(r"[a-z]+", _bare_column_name(name).casefold()))
    result["role_name_hints"] = [role for role, markers in NAME_ROLES.items() if words & markers]
    # Preserve only an explicit bracketed label. Its scientific meaning and
    # whether it is a measurement unit still require source context.
    unit_match = re.search(r"(?:\(([^()]+)\)|\[([^\[\]]+)\])\s*$", name)
    result["unit_label_hint"] = (unit_match.group(1) or unit_match.group(2)).strip() if unit_match else None
    if len(distinct) <= 30:
        result["levels"] = distinct
    if hint == "numeric":
        numbers = [value for value in numerical if value is not None]
        ordered = sorted(numbers)
        try:
            sample_sd = statistics.stdev(numbers) if len(numbers) > 1 else None
        except OverflowError:
            # A spread can exceed float range even though every source value
            # is finite. Do not emit Infinity or rescale the source values.
            sample_sd = None
        result["descriptive"] = {"n": len(numbers), "min": min(numbers), "max": max(numbers),
                                 "mean": statistics.mean(numbers), "median": _inclusive_quantile(ordered, 1, 2),
                                 "sample_sd": sample_sd,
                                 "q1": _inclusive_quantile(ordered, 1, 4), "q3": _inclusive_quantile(ordered, 3, 4)}
    return result


def _intake_signals(columns, rows, headers, missing_tokens):
    """Record observable hints without deciding table grain or matching tables."""
    numeric = [column for column in columns if column["type_hint"] == "numeric"]
    roles = {role: [column["name"] for column in numeric if role in column["role_name_hints"]]
             for role in NAME_ROLES}
    metadata = set().union(*(set(roles[role]) for role in NAME_ROLES if role != "estimate"))
    other_values = [column["name"] for column in numeric if column["name"] not in metadata]
    coordinates = [name for name in other_values if COORDINATE_NAME.search(_bare_column_name(name))]
    estimates = roles["estimate"] or [name for name in other_values if name not in coordinates] or other_values
    uncertainty = set(roles["spread"] + roles["standard_error"] + roles["lower_bound"] + roles["upper_bound"])
    # Require separate evidence columns; e.g. mean_cell_size by itself does
    # not become a summary table merely because "size" resembles a count.
    suspected_summary = bool((estimates and (uncertainty - set(estimates) or
                                            (roles["estimate"] and set(roles["count"]) - set(estimates)))) or
                             (roles["lower_bound"] and roles["upper_bound"]))
    groups = [column["name"] for column in columns if column["type_hint"] in {"categorical_candidate", "boolean_candidate"}
              and 2 <= column["unique_nonmissing"] <= 30]
    units = []
    identifiers = [column for column in columns if column["type_hint"] == "identifier_candidate"]
    for column in identifiers[:6]:
        index = headers.index(column["name"])
        counts = Counter(row[index] for row in rows if row[index] not in missing_tokens)
        repeated_groups = []
        for group in groups[:6]:
            group_index = headers.index(group)
            pairs = Counter((row[index], row[group_index]) for row in rows
                            if row[index] not in missing_tokens and row[group_index] not in missing_tokens)
            levels_by_id = {}
            for identifier, level in pairs:
                levels_by_id.setdefault(identifier, set()).add(level)
            spanning = sum(len(levels) > 1 for levels in levels_by_id.values())
            if spanning or any(count > 1 for count in pairs.values()):
                repeated_groups.append({"group_column": group, "identifiers_in_multiple_levels": spanning,
                                        "repeated_identifier_level_cells": sum(count > 1 for count in pairs.values())})
        units.append({"column": column["name"], "unique_nonmissing": len(counts),
                      "repeated_identifiers": sum(count > 1 for count in counts.values()),
                      "rows_per_identifier_min": min(counts.values()) if counts else None,
                      "rows_per_identifier_max": max(counts.values()) if counts else None,
                      "group_patterns": repeated_groups})
    return {"evidence_status": "observed names and values; scientific roles remain unconfirmed",
            "ambiguous_headers": [column["name"] for column in columns if GENERIC_NAME.fullmatch(_bare_column_name(column["name"]))],
            "identifier_pattern_scope": {"identifier_columns_profiled": min(len(identifiers), 6),
                                         "identifier_columns_total": len(identifiers), "group_columns_per_identifier_limit": 6},
            "identifier_candidates": units,
            "summary_data": {"status": "suspected" if suspected_summary else "not_established",
                             "estimate_candidates": estimates if suspected_summary else roles["estimate"],
                             "coordinate_name_candidates": coordinates,
                             "named_role_candidates": roles,
                             "evidence": "Column-name hints do not establish summaries, SD, SEM, CI or raw observations."}}


def _profile(path, relative, sha256, table, missing_tokens):
    sheet, headers, rows, truncated, notes = table
    table_id = relative + (f"::{sheet}" if sheet is not None else "")
    columns = [_column(name, [row[index] for row in rows], missing_tokens) for index, name in enumerate(headers)]
    require(rows, f"{table_id}: no observations after the header")
    return {"table_id": table_id, "path": relative, "sheet": sheet, "sha256": sha256,
            "file_bytes": path.stat().st_size, "rows_inspected": len(rows),
            "rows_complete": not truncated, "row_count": len(rows) if not truncated else None,
            "duplicate_rows_in_inspected_scope": len(rows) - len(set(map(tuple, rows))),
            "grain": {"observed": "one source table row", "scientific_unit": "unconfirmed",
                      "warning": "Row counts do not establish independent experimental units."},
            "intake_signals": _intake_signals(columns, rows, headers, missing_tokens),
            "columns": columns, "sample_rows": [dict(zip(headers, [value[:160] for value in row])) for row in rows[:3]],
            "sample_values_max_chars": 160,
            "notes": notes + (["Row limit reached; every profile and summary covers only the inspected prefix."] if truncated else [])}


def _load_design(path):
    if path is None:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise IntakeError(f"Cannot read --design JSON: {exc}") from None
    require(isinstance(payload, dict), "--design must contain a JSON object")
    allowed = {"table", "sheet", "question", "fields", "design", "row_kind", "missing_tokens", "missing_policy"}
    require(not set(payload) - allowed, f"Unknown --design keys: {', '.join(sorted(set(payload) - allowed))}; use fields and design explicitly")
    require(isinstance(payload.get("table"), str) and payload["table"], "--design requires table: relative path or table_id from manifest.json")
    require(isinstance(payload.get("row_kind", "unknown"), str) and payload.get("row_kind", "unknown") in {"observations", "summaries", "unknown"},
            "row_kind must be observations, summaries or unknown; declare it from source context")
    fields = payload.get("fields", {})
    require(isinstance(fields, dict), "--design fields must be an object")
    require(not set(fields) - {"group", "value", "x", "y"}, "--design fields supports group, value, x and y; set the experimental unit in design.unit")
    require(all(isinstance(value, str) and value for value in fields.values()), "Every declared field must name a column")
    design = payload.get("design", {})
    require(isinstance(design, dict), "--design design must be an object")
    require(not set(design) - {"unit", "unit_definition", "structure", "confirmed"}, "Unknown design keys; use unit, unit_definition, structure and confirmed")
    if design:
        require(set(design) == {"unit", "unit_definition", "structure", "confirmed"}, "Declared design requires unit, unit_definition, structure and confirmed")
        require(design.get("unit") is None or isinstance(design.get("unit"), str) and design["unit"], "design.unit must name a column or be null for unknown row-level units")
        require(design.get("structure") in {"independent", "paired", "unknown"}, "design.structure must be independent, paired or unknown")
        require(isinstance(design.get("confirmed", False), bool), "design.confirmed must be true or false")
        require(isinstance(design.get("unit_definition"), str) and design["unit_definition"].strip(), "Declared design requires a scientific unit_definition or an explicit unknown row-level definition")
        if design.get("confirmed"):
            require(design.get("unit") and design.get("structure") != "unknown", "Confirmed design requires a known unit column and structure")
            require(isinstance(design.get("unit_definition"), str) and design["unit_definition"].strip(), "Confirmed design requires a scientific unit_definition")
    require(payload.get("missing_policy", "error") in {"error", "complete_case"}, "missing_policy must be error or complete_case")
    tokens = payload.get("missing_tokens", DEFAULT_MISSING)
    require(isinstance(tokens, list) and all(isinstance(token, str) for token in tokens), "missing_tokens must be a list of strings")
    require("" in tokens and len(tokens) == len(set(tokens)), "missing_tokens must include the empty string and have no duplicates")
    return payload


def _descriptive_plan(fields, design, question, tokens, policy):
    unknown_design = {"unit": None, "unit_definition": "unknown; row-level descriptive summaries only", "structure": "unknown", "confirmed": False}
    return {"schema_version": 1, "question": question, "design": design or unknown_design,
            "missing_policy": policy, "missing_tokens": tokens,
            "comparisons": [{"name": "descriptive_preview", "method": "descriptive", "fields": fields}]}


def _intake_guidance(table, declaration):
    signals = table["intake_signals"]
    design = (declaration or {}).get("design", {})
    row_kind = (declaration or {}).get("row_kind", "unknown")
    summary = row_kind == "summaries" or (signals["summary_data"]["status"] == "suspected" and row_kind != "observations")
    repeated = [unit for unit in signals["identifier_candidates"] if unit["repeated_identifiers"]]
    questions, cautions = [], []
    if summary:
        questions.append({"id": "summary_meaning", "question": "Does each row contain a supplied summary or one experimental observation? What do the estimate, uncertainty and any n columns mean (SD, SEM, CI level or other bounds)?",
                          "evidence_columns": signals["summary_data"]["estimate_candidates"] + list(dict.fromkeys(
                              name for names in signals["summary_data"]["named_role_candidates"].values() for name in names))})
        cautions.append({"id": "summary_rows", "message": "Keep supplied estimates and uncertainty as summaries. Row counts and a named n column do not establish independent sample size; do not test summary rows as raw replicates or convert SD to SEM/CI without explicit supporting data."})
    if not design.get("confirmed"):
        if repeated:
            questions.append({"id": "repeated_unit", "question": "Which identifier is the scientific unit, and do its repeated rows represent the same unit over conditions/time, technical repeats, or reused labels? Explain any repeated unit-condition cells before pairing or inference.",
                              "evidence_columns": [unit["column"] for unit in repeated]})
        else:
            questions.append({"id": "row_grain", "question": "What does one row represent, which field identifies the independently sampled unit, and are measurements independent or paired/repeated?",
                              "evidence_columns": [unit["column"] for unit in signals["identifier_candidates"]]})
        cautions.append({"id": "unknown_design", "message": "No inferential design has been established. Descriptive previews must identify counts as source rows until scientific units and their dependence are confirmed."})
    elif design.get("structure") == "independent" and any(column["name"] == design.get("unit") and column["duplicate_nonmissing"]
                                                          for column in table["columns"]):
        cautions.append({"id": "declared_unit_repeated", "message": "The declared independent unit appears more than once in the inspected rows. Resolve row grain explicitly before inference; the declaration does not make repeated rows independent."})
    declared_fields = (declaration or {}).get("fields", {})
    unresolved_names = signals["ambiguous_headers"] if not declared_fields else []
    questions.append({"id": "field_meaning", "question": "Which table and measurement answer the intended question, what do their fields mean, and what are the measurement units? Read project notes or a data dictionary before choosing fields; do not join tables merely because IDs or headers look alike.",
                      "evidence_columns": unresolved_names})
    if unresolved_names:
        cautions.append({"id": "ambiguous_headers", "message": "Generic headers leave field meanings unresolved; numeric parseability alone does not identify measurements, time or biological effects.",
                         "columns": unresolved_names})
    identifiers = [column for column in table["columns"] if column["type_hint"] == "identifier_candidate" and column["numeric_parseable"]]
    if identifiers:
        cautions.append({"id": "numeric_identifiers", "message": "Numeric-looking identifiers stay strings and are excluded from automatic measurement candidates. Preserve leading zeros and explicitly declare a measurement role only when source context supports it.",
                         "columns": [column["name"] for column in identifiers]})
    if table["duplicate_rows_in_inspected_scope"]:
        cautions.append({"id": "duplicate_rows", "message": "Exact duplicate rows are recorded and retained. Determine whether they are legitimate repeats or duplicated records before choosing an exclusion or aggregation."})
    missing = [column["name"] for column in table["columns"] if column["missing"]]
    if missing:
        cautions.append({"id": "missing_values", "message": "Missing-token counts use the recorded exact strings. Verify whether labels such as NA/null are real categories and adopt a missing-value policy explicitly.", "columns": missing})
    if summary and row_kind == "unknown":
        status = "suspected_summary_needs_context"
    else:
        status = "declared_summaries" if summary else ("design_declared" if design.get("confirmed") else "needs_context")
    return {"status": status, "row_kind": row_kind, "priority_questions": questions[:3], "cautions": cautions}, summary


def _options(table, declaration, tokens):
    columns = table["columns"]
    declared_fields = (declaration or {}).get("fields", {})
    design = (declaration or {}).get("design", {})
    declared_unit = design.get("unit")
    numeric = [column["name"] for column in columns if column["type_hint"] == "numeric" and column["name"] != declared_unit]
    groups = [column["name"] for column in columns if column["type_hint"] in {"categorical_candidate", "boolean_candidate"}
              and column["name"] != declared_unit and 2 <= column["unique_nonmissing"] <= 30]
    ids = [column["name"] for column in columns if column["type_hint"] == "identifier_candidate"]
    if declared_unit and declared_unit not in ids:
        ids.insert(0, declared_unit)
    dates = [column["name"] for column in columns if column["type_hint"] == "date_time_candidate" and column["name"] != declared_unit]
    intake, summary = _intake_guidance(table, declaration)
    common_questions = ["What does one row represent, and which column identifies the independently sampled unit?",
                        "What do the selected measurements mean, and what are their units?",
                        "Are observations independent, paired, or repeated within a unit?",
                        "Which comparisons were intended, and which missing-value tokens and exclusions are valid?"]
    if design.get("confirmed"):
        common_questions = common_questions[1:2] + common_questions[3:]
    plans = []
    comparison_methods = ["welch or mannwhitney for independent two-group questions", "paired_t or wilcoxon for explicitly paired two-condition questions"]
    if design.get("confirmed"):
        comparison_methods = [comparison_methods[1 if design["structure"] == "paired" else 0]]
    values = [declared_fields["value"]] if "value" in declared_fields else numeric[:6]
    selected_group = declared_fields.get("group")
    if summary:
        signals = table["intake_signals"]["summary_data"]
        roles = {role: [name for name in names if name != declared_unit]
                 for role, names in signals["named_role_candidates"].items()}
        adopted_estimate = declared_fields.get("value", declared_fields.get("y"))
        estimate = [adopted_estimate] if adopted_estimate else [name for name in signals["estimate_candidates"] if name != declared_unit][:6]
        metadata = set(name for role, names in roles.items() if role != "estimate" for name in names)
        x_candidates = [name for name in numeric if name not in metadata and name not in estimate]
        if "x" in declared_fields:
            x_candidates = [declared_fields["x"]]
        has_bounds = bool(roles["lower_bound"] and roles["upper_bound"])
        charts = (["interval"] if has_bounds and estimate else []) + (["timecourse"] if estimate and x_candidates and (roles["spread"] or has_bounds) else [])
        if not charts and estimate:
            charts = ["custom supplied-summary plot"]
        plans.append({"id": "supplied_summary", "reading_task": "Read supplied estimates with their explicitly defined uncertainty",
                      "recommended_charts": charts,
                      "field_candidates": {"estimate": estimate, "x": [declared_fields["x"]] if "x" in declared_fields else x_candidates[:6],
                                           "group": [selected_group] if selected_group else groups[:6],
                                           "uncertainty": {role: roles[role] for role in ("spread", "standard_error", "lower_bound", "upper_bound")},
                                           "supplied_n": roles["count"]},
                      "mapping_status": "requires confirmed summary grain, estimate meaning and uncertainty semantics",
                      "inference": {"status": "blocked", "questions": [item["question"] for item in intake["priority_questions"]]},
                      "notes": ["Use literal supplied estimates and bounds after verifying their meaning; do not reconstruct raw replicates.",
                                "No raw-observation analysis plan is emitted for summary-like rows. A declared row_kind of observations can resolve a false name-based summary hint from source evidence.",
                                "The interval recipe requires explicit lower/upper bounds. The timecourse recipe requires numeric x and declared SD or supplied bounds; SEM columns are not SD."]})
    if values and not summary:
        fields = {"value": values[0]}
        if selected_group:
            fields["group"] = selected_group
        elif groups:
            fields["group"] = groups[0]
        plans.append({"id": "distribution", "reading_task": "Read the spread, skew and raw observations of a measurement",
                      "recommended_charts": ["distribution", "ecdf"], "field_candidates": {"value": values, "group": [selected_group] if selected_group else groups[:6]},
                      "proposed_fields": fields, "mapping_status": "declared" if "value" in declared_fields else "candidate; confirm field meanings before plotting",
                      "descriptive_analysis_plan": _descriptive_plan(fields, design, (declaration or {}).get("question") or "Describe the supplied measurement distribution", tokens, (declaration or {}).get("missing_policy", "error")),
                      "inference": {"status": "not_selected", "methods_to_consider_after_design": comparison_methods, "questions": common_questions},
                      "notes": ["Display raw observations and summary definitions explicitly; an observed row is not automatically a biological replicate."]})
    if not summary and (len(numeric) >= 2 or {"x", "y"} <= set(declared_fields)):
        x = declared_fields.get("x", numeric[0] if numeric else "")
        y = declared_fields.get("y", next((name for name in numeric if name != x), numeric[-1] if numeric else ""))
        plans.append({"id": "association", "reading_task": "Read whether two supplied numeric measurements vary together",
                      "recommended_charts": ["scatter"], "field_candidates": {"x": numeric[:6], "y": numeric[:6], "group": groups[:6]},
                      "proposed_fields": {"x": x, "y": y}, "mapping_status": "declared" if {"x", "y"} <= set(declared_fields) else "candidate; confirm field meanings before plotting",
                      "inference": {"status": "not_selected", "methods_to_consider_after_design": ["pearson for an adopted linear association question", "spearman for an adopted monotonic association question"], "questions": common_questions + ["Are scales or transformations required, and does each unit contribute one independent pair?"]},
                      "notes": ["A scatter preview does not establish causation or justify a fitted curve."]})
    repeated_ids = [unit["column"] for unit in table["intake_signals"]["identifier_candidates"] if unit["repeated_identifiers"]]
    if not summary and ids and values and (selected_group or groups) and (repeated_ids or design.get("structure") == "paired") and not (design.get("confirmed") and design["structure"] == "independent"):
        plans.append({"id": "paired_candidate", "reading_task": "Check whether an explicit unit has measurements in multiple conditions",
                      "recommended_charts": ["paired"], "field_candidates": {"unit": [design["unit"]] if design.get("unit") else repeated_ids[:6], "group": [selected_group] if selected_group else groups[:6], "value": values},
                      "mapping_status": "requires explicit pairing verification",
                      "inference": {"status": "blocked", "questions": ["Does this identifier refer to the same unit across conditions?", "Is there one value per unit and condition, or are technical repeats present?", "How should unmatched units be handled without silently dropping them?"]},
                      "notes": ["Matching-looking identifiers are a candidate relationship; the command has not established or created pairs."]})
    if not plans:
        plans.append({"id": "table_structure", "reading_task": "Establish table grain and which fields can answer a quantitative question",
                      "recommended_charts": [], "field_candidates": {"identifier": ids[:6], "category": groups[:6], "date_time": dates[:6]},
                      "mapping_status": "needs measurement roles or a prepared quantitative table",
                      "inference": {"status": "blocked", "questions": common_questions},
                      "notes": ["No fully numeric measurement column was found; do not coerce identifiers or formula strings into values."]})
    return {"table_id": table["table_id"], "profile_scope": "complete source rows" if table["rows_complete"] else "bounded inspected prefix only",
            "candidate_columns": {"numeric": numeric, "group": groups, "identifier": ids, "date_time": dates},
            "declared_design": declaration, "intake": intake, "options": plans[:3]}


def _report(manifest, recommendations):
    inventory_only = recommendations is None
    title = "# Data inventory" if inventory_only else "# Create-track data exploration"
    purpose = ("This inventory contains descriptive profiles. It does not select or change the active plotting track, chart or statistical analysis."
               if inventory_only else "This inventory contains descriptive profiles and candidate reading tasks. No inferential tests were run.")
    lines = [title, "", purpose, "",
             f"Inspected {len(manifest['tables'])} table(s). Source cells remain strings; type hints do not establish scientific meanings.", ""]
    for index, table in enumerate(manifest["tables"]):
        lines.extend([f"## `{table['table_id']}`", "", f"Rows inspected: {table['rows_inspected']}; full row coverage: {table['rows_complete']}; duplicate rows: {table['duplicate_rows_in_inspected_scope']}.", "",
                      "| Column | Type hint | Missing | Unique nonmissing |", "| --- | --- | ---: | ---: |"])
        for column in table["columns"]:
            name = column["name"].replace("|", "\\|").replace("\n", " ")
            lines.append(f"| `{name}` | {column['type_hint']} | {column['missing']} | {column['unique_nonmissing']} |")
        lines.append("")
        signals = table["intake_signals"]
        if signals["summary_data"]["status"] == "suspected":
            lines.extend(["Profile signal: summary-like column names coexist with numeric estimates; table grain and uncertainty meanings are unconfirmed.", ""])
        for unit in signals["identifier_candidates"]:
            if unit["repeated_identifiers"]:
                lines.extend([f"Profile signal: `{unit['column']}` has {unit['repeated_identifiers']} repeated identifier(s), with up to {unit['rows_per_identifier_max']} source rows per identifier. Identity and dependence are unconfirmed.", ""])
        if inventory_only:
            lines.extend(["Recorded values and source profiles are descriptive. The active plotting track remains unchanged.", ""])
        else:
            for option in recommendations["tables"][index]["options"]:
                lines.extend([f"- **{option['reading_task']}**: {', '.join(option['recommended_charts']) or 'clarify quantitative fields first'}. {option['mapping_status']}."])
            guidance = recommendations["tables"][index]["intake"]
            lines.extend(["", "Resolve these points from project context or the user:", ""])
            for item in guidance["priority_questions"]:
                lines.append(f"- {item['question']}")
            lines.append("")
            for item in guidance["cautions"][:4]:
                lines.append(f"- Caution: {item['message']}")
            lines.extend(["", "See `analysis-options.json` for evidence columns, all cautions and candidate mappings. No inferential method was selected.", ""])
    if manifest["errors"] or manifest["skipped"]:
        lines.extend(["## Files not inspected", ""])
        for entry in manifest["errors"] + manifest["skipped"]:
            lines.append(f"- `{entry['path']}`: {entry['reason']}")
    return "\n".join(lines) + "\n"


def inspect(input_path, out, design_path=None, *, inventory_only=False):
    input_path, out = Path(input_path).absolute(), Path(out).absolute()
    require(not input_path.is_symlink(), "Input is a symlink; pass its explicit real directory or table path")
    require(input_path.exists(), f"Input does not exist: {input_path}")
    require(input_path.is_dir() or input_path.is_file(), "Input must be a directory or local table")
    require(not out.is_symlink(), "Output directory cannot be a symlink")
    root = input_path.resolve() if input_path.is_dir() else input_path.resolve().parent
    out = out.resolve()
    require(out != root, "Use a dedicated --out directory; source directory cannot also be the output directory")
    require(not out.exists(), f"Output already exists; choose a fresh directory: {out}")
    declaration = _load_design(Path(design_path) if design_path else None)
    tokens = (declaration or {}).get("missing_tokens", DEFAULT_MISSING)
    if input_path.is_dir():
        paths, skipped = _discovery(root, out)
    else:
        require(input_path.suffix.lower() in TABLE_SUFFIXES, "Supported inputs are UTF-8 CSV, TSV or XLSX; supply a supported table or directory")
        paths, skipped = [input_path.resolve()], []
    tables, errors, total_bytes = [], [], 0
    for path in paths:
        relative = str(path.relative_to(root))
        try:
            size = path.stat().st_size
            if len(tables) >= LIMITS["tables"] or size > LIMITS["file_bytes"] or total_bytes + size > LIMITS["total_bytes"]:
                skipped.append({"path": relative, "reason": "table count or byte limit; inspect a narrower input"})
                continue
            total_bytes += size
            sha = _hash(path)
            if path.suffix.lower() == ".xlsx":
                raw_tables, sheet_errors = _read_xlsx(path)
                for error in sheet_errors:
                    error["path"] = relative + error["path"][len(path.name):]
                errors.extend(sheet_errors)
            else:
                raw_tables = _read_csv(path)
            require(_hash(path) == sha, f"{relative}: source changed during inspection; rerun against a stable input")
            for raw_table in raw_tables:
                if len(tables) >= LIMITS["tables"]:
                    skipped.append({"path": relative, "reason": "worksheet/table count limit"})
                    break
                try:
                    tables.append(_profile(path, relative, sha, raw_table, tokens))
                except IntakeError as exc:
                    errors.append({"path": relative, "reason": str(exc)})
        except (OSError, ValueError, KeyError, BadZipFile, ParseError) as exc:
            errors.append({"path": relative, "reason": str(exc)})
    require(tables, "No usable tables found. Supply a CSV/TSV with unique headers and observation rows, or an XLSX workbook. " + "; ".join(error["reason"] for error in errors[:3]))
    selected = None
    if declaration:
        candidates = [table for table in tables if declaration["table"] in {table["table_id"], table["path"]}
                      and ("sheet" not in declaration or declaration["sheet"] == table["sheet"])]
        require(len(candidates) == 1, "--design table/sheet must select exactly one inspected table; use table_id from manifest.json")
        selected = candidates[0]
        names = {column["name"] for column in selected["columns"]}
        required_fields = set(declaration.get("fields", {}).values())
        if declaration.get("design", {}).get("unit"):
            required_fields.add(declaration["design"]["unit"])
        require(required_fields <= names, f"Declared columns not found: {', '.join(sorted(required_fields - names))}")
        fields = declaration.get("fields", {})
        require(len(set(fields.values())) == len(fields), "Distinct declared field roles must name distinct columns")
        require(declaration.get("design", {}).get("unit") not in fields.values(), "Unit IDs cannot also be declared as measurements or grouping fields")
        for role in {"value", "x", "y"} & set(fields):
            column = next(column for column in selected["columns"] if column["name"] == fields[role])
            require(column["numeric_parseable"] == column["nonmissing"] and column["nonmissing"] > 0,
                    f"Declared {role} column must contain finite numeric values or declared missing tokens; prepare a numeric table explicitly")
        selected["grain"]["declared_design"] = declaration.get("design", {})
    manifest = {"schema_version": SCHEMA_VERSION, "tool": "easyviz.inspect_data", "track": None if inventory_only else "create",
                "mode": "inventory" if inventory_only else "create_recommendations",
                "input": str(input_path.resolve()), "input_root": str(root), "limits": LIMITS,
                "missing_tokens": tokens, "missing_note": "Tokens are treated as missing for profiles only; no source cell is replaced or omitted.",
                "tables": tables, "skipped": skipped, "errors": errors,
                "inference_run": False, "sources_modified": False}
    recommendations = None if inventory_only else {"schema_version": SCHEMA_VERSION, "track": "create", "status": "candidate_reading_tasks",
                       "inference_run": False, "selection_rule": "Data-type hints propose readings; scientific roles and study design require explicit evidence.",
                       "tables": [_options(table, declaration if table is selected else None, tokens) for table in tables]}
    # A fresh directory and exclusive writes protect original files and prior
    # review artifacts. A rerun deliberately uses a new output path.
    out.mkdir(parents=True, exist_ok=False)
    payloads = {"manifest.json": manifest}
    if recommendations is not None:
        payloads["analysis-options.json"] = recommendations
    for name, payload in payloads.items():
        with (out / name).open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
    with (out / "exploration.md").open("x", encoding="utf-8") as stream:
        stream.write(_report(manifest, recommendations))
    return manifest, recommendations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Local directory or CSV/TSV/XLSX table")
    parser.add_argument("--out", required=True, type=Path, help="Fresh dedicated output directory; sources and prior runs are preserved")
    parser.add_argument("--design", type=Path, help="Optional explicit table, field mappings and study-design JSON; see references/data-exploration.md")
    parser.add_argument("--inventory-only", action="store_true", help="Inventory sources without choosing a track or generating chart/statistical recommendations")
    args = parser.parse_args()
    try:
        manifest, recommendations = inspect(args.input, args.out, args.design, inventory_only=args.inventory_only)
    except (OSError, ValueError, ImportError) as exc:
        parser.exit(2, f"EasyViz: {exc}\n")
    print(json.dumps({"status": "inspected", "track": manifest["track"], "mode": manifest["mode"], "tables": len(manifest["tables"]),
                      "errors": len(manifest["errors"]), "out": str(args.out.resolve()), "inference_run": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
