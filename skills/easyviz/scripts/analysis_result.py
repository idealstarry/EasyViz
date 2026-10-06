"""Bind a frozen planned-analysis result to exact plotting observations.

This helper reads an adopted result; it never recomputes tests or chooses a
population. It is also usable by custom plotting code without Matplotlib.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re


class AnalysisBindingError(ValueError):
    """An adopted analysis no longer describes these plotting inputs."""


BINDING_KEYS = {"schema_version", "results_file", "results_sha256", "comparison", "pvalue", "population"}


def require(condition, message):
    if not condition:
        raise AnalysisBindingError(message)


def validate_binding(binding):
    require(isinstance(binding, dict) and set(binding) == BINDING_KEYS,
            "statistics.analysis requires exactly schema_version, results_file, results_sha256, comparison, pvalue, population")
    require(type(binding["schema_version"]) is int and binding["schema_version"] == 1,
            "statistics.analysis.schema_version must be 1")
    for key in ("results_file", "comparison"):
        require(isinstance(binding[key], str) and bool(binding[key].strip()), f"statistics.analysis.{key} must be a nonempty string")
    require(isinstance(binding["results_sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", binding["results_sha256"]) is not None,
            "statistics.analysis.results_sha256 must identify the exact adopted results.json bytes")
    require(binding["pvalue"] in ("raw", "adjusted"), "statistics.analysis.pvalue must explicitly be raw or adjusted")
    require(binding["population"] in ("all", "included"), "statistics.analysis.population must explicitly be all or included")
    return binding


def _json(raw, name):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate JSON key in {name}: {key}")
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique,
                           parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
        def finite(item):
            if isinstance(item, dict):
                return all(finite(part) for part in item.values())
            if isinstance(item, list):
                return all(finite(part) for part in item)
            return not isinstance(item, float) or math.isfinite(item)
        require(finite(value), f"Non-finite JSON number in {name}")
        return value
    except (UnicodeError, ValueError) as exc:
        raise AnalysisBindingError(f"{name} must be finite UTF-8 JSON without duplicate keys: {exc}") from None


def _csv(raw, name):
    try:
        table = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True))
    except (UnicodeError, csv.Error) as exc:
        raise AnalysisBindingError(f"Cannot read {name}: {exc}") from None
    require(len(table) > 1, f"{name} must contain a header and records")
    header = table[0]
    require(header and len(set(header)) == len(header) and all(v.strip() for v in header), f"{name} headers must be nonempty and unique")
    require(all(len(row) == len(header) for row in table[1:]), f"{name} has an invalid record width")
    return header, [dict(zip(header, row)) for row in table[1:]]


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _probability(value, name):
    require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1, f"{name} must be finite and in [0, 1]")
    return value


def _ptext(value, label):
    return f"{label} < 0.001" if value == 0 else f"{label} = {value:.3g}"


def _caption(report, result, binding, plotted_rows):
    design = report["plan"]["design"]
    count = result["counts"]
    lines = ["# Adopted statistical analysis", "",
             f"Comparison: {result['name']}. Method: {result['method']}.",
             f"Sampling unit: {design['unit_definition']} (column `{design['unit']}`); design: {design['structure']}; confirmed: {design['confirmed']}.",
             f"Analysis includes {count['included_rows']} source rows; excludes {count['excluded_rows']} selected rows; {count['unselected_rows']} other source rows are outside this comparison.",
             f"Plotted population: `{binding['population']}` ({plotted_rows} source rows)."]
    if binding["population"] == "all":
        lines.append("The visible observations are the supplied plotting population. The adopted inference uses only its recorded included subset; visible group summaries must not be interpreted as summaries of that subset unless the populations coincide.")
    else:
        lines.append("Only the explicitly adopted included source records are plotted, retaining their literal values and identities. Excluded and unselected rows remain in the captured source CSV and analysis trace.")
    lines.append(f"Missing policy: {report['plan']['missing_policy']}; exclusion reasons: {json.dumps(result['exclusions'], ensure_ascii=False)}.")
    if result.get("pvalue") is not None:
        lines.append(f"Raw P = {result['pvalue']:.17g}; calculation: {result.get('pvalue_method', 'see adopted methodology')}.")
        if result.get("adjustment"):
            correction = result["adjustment"]
            lines.append(f"Adjusted P = {result['adjusted_pvalue']:.17g}; {correction['method']}, family `{correction['family']}`, {correction['family_size']} hypotheses.")
        lines.append(f"The displayed P value is explicitly `{binding['pvalue']}`; no test or adjustment was recomputed during plotting.")
    if result.get("effect"):
        effect = result["effect"]
        lines.append(f"Effect: {effect['name']} = {effect['estimate']:.17g}; direction: {effect['direction']}.")
    if result.get("interval"):
        interval = result["interval"]
        lines.append(f"Effect interval: {json.dumps(interval, ensure_ascii=False)}. Its scope is retained; P-value adjustment does not adjust this interval.")
    else:
        lines.append(f"Effect interval: not computed. {result.get('interval_note', '')}")
    lines.extend(result.get("notes", []))
    lines += ["", "This is a statistical caption supplement. Combine it with the panel's scientific description and source attribution in caption.md; it is not text to add to the image.", ""]
    return "\n".join(lines)


def load(binding, data_path, fields, chart, *, spec_path=None):
    """Read, validate and freeze one comparison; return exact source-record IDs.

    Core scatter/distribution and equivalent custom layers use this contract.
    Results must be from analyze.py schema 1 with its original companion files.
    The caller explicitly chooses all source rows or the included subset.
    """
    validate_binding(binding)
    path = Path(binding["results_file"])
    if not path.is_absolute():
        path = (Path(spec_path).resolve().parent if spec_path is not None else Path.cwd()) / path
    path = path.resolve()
    raw = path.read_bytes()
    require(_digest(raw) == binding["results_sha256"], "Adopted analysis result changed; inspect and explicitly adopt the current results before plotting")
    report = _json(raw, "results.json")
    require(isinstance(report, dict) and type(report.get("schema_version")) is int and report["schema_version"] == 1
            and report.get("status") == "complete", "Adopted analysis must be a complete analyze.py schema_version=1 report")
    require(isinstance(report.get("plan"), dict) and isinstance(report["plan"].get("design"), dict)
            and isinstance(report.get("provenance"), dict) and isinstance(report.get("comparisons"), list)
            and all(isinstance(item, dict) for item in report["comparisons"]), "Adopted analysis report is missing its plan, provenance or comparisons")
    source_raw = Path(data_path).read_bytes()
    require(_digest(source_raw) == report.get("provenance", {}).get("data", {}).get("sha256"),
            "Plot data bytes do not match the adopted analysis source; never reuse P values on changed or reordered input")
    header, rows = _csv(source_raw, "analysis source CSV")
    require(report["provenance"]["data"].get("csv_records") == len(rows), "Analysis source-record count is inconsistent")
    artifacts = report.get("artifacts")
    expected_artifacts = {"plan.json", "analyzed-data.csv", "summary.csv", "methodology.md"}
    require(isinstance(artifacts, dict) and set(artifacts) == expected_artifacts, "Adopted analysis requires its exact plan, source trace, summaries and methodology companions")
    payloads = {"adopted-analysis/results.json": raw}
    bindings = {"analysis_result": {"path": str(path), "sha256": _digest(raw)}}
    companions = {}
    for name in sorted(expected_artifacts):
        content = (path.parent / name).read_bytes()
        record = artifacts[name]
        require(isinstance(record, dict) and record.get("sha256") == _digest(content) and record.get("bytes") == len(content),
                f"Adopted analysis companion changed: {name}")
        companions[name] = content
        bindings[f"analysis_artifact:{name}"] = {"path": str(path.parent / name), "sha256": _digest(content)}
        payloads[f"adopted-analysis/{name}"] = content
    plan = _json(companions["plan.json"], "plan.json")
    require(plan == report.get("plan") and _digest(companions["plan.json"]) == report["provenance"].get("plan", {}).get("sha256"),
            "Analysis adopted plan differs from the report")
    require(type(plan.get("schema_version")) is int and plan["schema_version"] == 1
            and isinstance(plan.get("comparisons"), list) and all(isinstance(item, dict) for item in plan["comparisons"]),
            "Adopted analysis plan must have schema_version=1 and planned comparisons")
    planned = [item for item in plan.get("comparisons", []) if item.get("name") == binding["comparison"]]
    results = [item for item in report.get("comparisons", []) if item.get("name") == binding["comparison"]]
    require(len(planned) == len(results) == 1, "Adopted analysis comparison must identify one planned result")
    selected_plan, result = planned[0], results[0]
    require(result.get("method") in {"descriptive", "welch", "mannwhitney", "paired_t", "wilcoxon", "friedman", "pearson", "spearman"}
            and isinstance(result.get("fields"), dict), "Adopted comparison is not a supported analyze.py result")
    require(selected_plan.get("method") == result.get("method") and selected_plan.get("fields") == result.get("fields"),
            "Analysis method or fields differ from the planned comparison")
    require(selected_plan.get("groups") == result.get("groups"), "Analysis group order differs from its planned effect direction")
    require(chart in ("scatter", "distribution"), "Adopted statistics currently bind scatter/distribution or equivalent custom layers; other plot transformations need an explicit custom binding")
    roles = {"x", "y"} if chart == "scatter" else ({"group", "value"} if "group" in result["fields"] else {"value"})
    require(set(result["fields"]) == roles and all(fields.get(role) == result["fields"][role] for role in roles),
            "Plot measurement/group fields differ from the adopted analysis comparison")
    design = plan["design"]
    require(set(design) == {"unit", "unit_definition", "structure", "confirmed"}
            and type(design["confirmed"]) is bool and design["structure"] in ("independent", "paired", "unknown")
            and isinstance(design["unit_definition"], str) and bool(design["unit_definition"].strip()),
            "Adopted analysis requires an explicit sampling-unit definition and design")
    unit = design["unit"]
    require(unit is None or isinstance(unit, str) and unit in header, "Adopted sampling unit must name a source column")
    require(all(isinstance(name, str) and name in header for name in result["fields"].values()), "Adopted measurement fields must name source columns")
    if result["method"] != "descriptive":
        require(design["confirmed"] and unit is not None, "Adopted inference requires a confirmed independent sampling unit")
        expected_structure = "paired" if result["method"] in ("paired_t", "wilcoxon", "friedman") else "independent"
        require(design["structure"] == expected_structure, "Adopted method differs from the confirmed experimental design")
    require("unit" not in fields or fields["unit"] == unit, "Plot unit field differs from the adopted analysis sampling unit")
    trace_header, trace = _csv(companions["analyzed-data.csv"], "analyzed-data.csv")
    require(trace_header == ["_easyviz_comparison", "_easyviz_source_record", "_easyviz_status", "_easyviz_exclusion"] + header,
            "Analysis source trace fields differ from its source CSV")
    selected_trace = [row for row in trace if row["_easyviz_comparison"] == binding["comparison"]]
    seen, included, exclusions = set(), [], []
    for row in selected_trace:
        identity = row["_easyviz_source_record"]
        require(identity.isdigit() and str(int(identity)) == identity, "Analysis source-record identity is not canonical")
        record = int(identity)
        require(2 <= record <= len(rows) + 1 and record not in seen, "Analysis source-record identity is duplicate or outside the source")
        seen.add(record)
        source = rows[record - 2]
        require(all(row[name] == source[name] for name in header), f"Analysis trace changed literal source values at record {record}")
        require(row["_easyviz_status"] in ("included", "excluded"), "Invalid analysis inclusion status")
        if row["_easyviz_status"] == "included":
            require(not row["_easyviz_exclusion"], "Included analysis row has an exclusion reason")
            included.append(record)
        else:
            require(bool(row["_easyviz_exclusion"]), "Excluded analysis row has no reason")
            exclusions.append({"source_record": record, "unit": source[unit] if unit else None, "reason": row["_easyviz_exclusion"]})
    expected = {index for index, row in enumerate(rows, start=2)
                if "groups" not in selected_plan or row[selected_plan["fields"]["group"]] in selected_plan["groups"]}
    require(seen == expected, "Analysis trace does not account for every selected source record")
    counts = result.get("counts", {})
    require(counts.get("source_rows") == len(rows) and counts.get("selected_rows") == len(seen)
            and counts.get("included_rows") == len(included) and counts.get("excluded_rows") == len(exclusions)
            and counts.get("unselected_rows") == len(rows) - len(seen), "Analysis row counts do not match the source trace")
    require(result.get("exclusions") == exclusions, "Analysis exclusion reasons differ from the source trace")
    require(included, "Adopted comparison has no included observations")
    included_units = len({rows[record - 2][unit] for record in included}) if unit else None
    require(counts.get("included_units") == included_units
            and counts.get("independent_unit_count") == (included_units if design["confirmed"] else None),
            "Analysis unit counts differ from the literal included source records")
    if result.get("effect") is not None:
        effect = result["effect"]
        require(isinstance(effect, dict) and isinstance(effect.get("name"), str) and isinstance(effect.get("direction"), str)
                and type(effect.get("estimate")) in (int, float) and math.isfinite(effect["estimate"]),
                "Adopted effect must retain a finite estimate and explicit direction")
    plotted_records = list(range(2, len(rows) + 2)) if binding["population"] == "all" else included
    adopted = dict(result)
    if result.get("pvalue") is not None:
        _probability(result["pvalue"], "Raw analysis P value")
        require(type(result.get("statistic")) in (int, float) and math.isfinite(result["statistic"]), "Analysis statistic must be finite")
        mult = plan.get("multiplicity")
        if mult:
            require(result.get("adjustment") == {"family": mult["family"], "method": mult["adjustment"], "family_size": len(mult["comparisons"])}
                    and binding["comparison"] in mult["comparisons"], "Analysis multiplicity differs from the adopted planned family")
            _probability(result.get("adjusted_pvalue"), "Adjusted analysis P value")
        else:
            require(result.get("adjustment") is None and result.get("adjusted_pvalue") is None, "Analysis adjustment is absent from its adopted plan")
        if binding["pvalue"] == "adjusted":
            require(bool(result.get("adjustment")), "Adjusted P requested but this adopted comparison has no multiplicity adjustment")
            pvalue = _probability(result.get("adjusted_pvalue"), "Adjusted analysis P value")
            label = "adjusted P"
        else:
            pvalue, label = result["pvalue"], "P"
        adopted.update(annotation_pvalue=pvalue, annotation_label=label, annotation_text=_ptext(pvalue, label))
    else:
        require(binding["pvalue"] == "raw", "Descriptive analysis has no adjusted P value")
    adopted["adoption"] = {"schema_version": 1, "results_file": str(path), "results_sha256": _digest(raw),
                            "comparison": binding["comparison"], "pvalue": binding["pvalue"], "population": binding["population"],
                            "plotted_source_records": plotted_records, "included_source_records": included,
                            "design": plan["design"], "recomputed": False}
    caption = _caption(report, result, binding, len(plotted_records))
    payloads["analysis-caption.md"] = caption.encode("utf-8")
    return {"result": adopted, "source_records": plotted_records, "source_bindings": bindings, "payloads": payloads,
            "caption": caption, "report": report, "source_sha256": _digest(source_raw), "source_rows": len(rows)}
