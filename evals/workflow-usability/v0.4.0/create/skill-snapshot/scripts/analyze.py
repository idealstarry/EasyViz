#!/usr/bin/env python3
"""Run a planned, explicitly designed analysis on one prepared CSV.

This create-track helper does not infer independent samples, choose significant
comparisons, perform upstream bioinformatics, or change source measurements.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import shutil
import tempfile
from importlib.metadata import version

import numpy as np
from scipy import stats


class AnalysisError(ValueError):
    """A plan or data problem that must be resolved before analysis."""


def require(condition, message):
    if not condition:
        raise AnalysisError(message)


METHODS = {"descriptive", "welch", "mannwhitney", "paired_t", "wilcoxon", "pearson", "spearman"}
PAIRED = {"paired_t", "wilcoxon"}
CORRELATION = {"pearson", "spearman"}
TOP_KEYS = {"schema_version", "question", "design", "missing_policy", "missing_tokens", "comparisons", "multiplicity"}
PLAN_DESCRIPTION = {
    "schema_version": 1,
    "track": "create",
    "question": "A scientific question fixed before examining test results",
    "design": {
        "unit": "column containing an independent sample or paired subject ID; null for unconfirmed row-only descriptions",
        "unit_definition": "Describe the actual sampling unit, not simply one spreadsheet row",
        "structure": "independent | paired | unknown (unknown is descriptive-only)",
        "confirmed": "boolean; true is required for every inferential method",
    },
    "missing_policy": "error | complete_case (required)",
    "missing_tokens": ["", "NA", "NaN"],
    "comparisons": [{
        "name": "primary (unique, planned name)",
        "method": "descriptive | welch | mannwhitney | paired_t | wilcoxon | pearson | spearman",
        "fields": {"group": "condition", "value": "measurement"},
        "groups": ["A", "B"],
        "confidence_level": 0.95,
    }],
    "field_rules": {
        "descriptive": "value plus optional group; groups restriction not supported",
        "welch | mannwhitney | paired_t | wilcoxon": "group,value plus exactly two explicit string groups",
        "pearson | spearman": "x,y; one row per confirmed independent unit",
    },
    "multiplicity": {
        "family": "Predeclared family of hypotheses",
        "adjustment": "holm | benjamini_hochberg",
        "comparisons": ["primary", "secondary"],
    },
    "multiplicity_rules": "Required for multiple inferential comparisons; list exactly all inferential names. Intervals remain pointwise, never family-adjusted.",
    "optional_wilcoxon_key": "difference_decimals: explicit integer 0..15 for known measurement precision; no rounding otherwise",
    "output": ["results.json", "summary.csv", "analyzed-data.csv", "methodology.md", "plan.json"],
    "output_policy": "A fresh directory only. Every selected source row is traced, including excluded rows; results.json is published last.",
}


def _keys(obj, allowed, context):
    require(isinstance(obj, dict), f"{context} must be an object")
    require(not (set(obj) - allowed), f"Unknown {context} keys: {sorted(set(obj) - allowed)}")


def validate_plan(plan):
    _keys(plan, TOP_KEYS, "plan")
    require(type(plan.get("schema_version")) is int and plan["schema_version"] == 1, "schema_version must be 1")
    require(isinstance(plan.get("question"), str) and plan["question"].strip(), "question must describe the planned scientific question")
    design = plan.get("design")
    _keys(design, {"unit", "unit_definition", "structure", "confirmed"}, "design")
    require(set(design) == {"unit", "unit_definition", "structure", "confirmed"}, "design requires unit, unit_definition, structure, confirmed")
    require(design["unit"] is None or (isinstance(design["unit"], str) and design["unit"].strip()), "design.unit must name a column, or be null for row-only descriptions")
    require(isinstance(design["unit_definition"], str) and design["unit_definition"].strip(), "design.unit_definition must describe the actual sampling unit")
    require(design["structure"] in ("independent", "paired", "unknown"), "design.structure must be independent, paired, or unknown")
    require(type(design["confirmed"]) is bool, "design.confirmed must be a boolean")
    if design["confirmed"]:
        require(design["unit"] is not None and design["structure"] != "unknown", "A confirmed design requires unit IDs and a known structure")
    require(plan.get("missing_policy") in ("error", "complete_case"), "Declare missing_policy: error or complete_case")
    tokens = plan.get("missing_tokens", ["", "NA", "NaN"])
    require(isinstance(tokens, list) and all(isinstance(x, str) for x in tokens), "missing_tokens must be a list of exact strings")
    require(len(tokens) == len(set(tokens)) and "" in tokens, "missing_tokens must include the empty string and have no duplicates")
    comparisons = plan.get("comparisons")
    require(isinstance(comparisons, list) and comparisons, "comparisons must be a nonempty list")
    names = []
    for comp in comparisons:
        _keys(comp, {"name", "method", "fields", "groups", "confidence_level", "difference_decimals"}, "comparison")
        require(isinstance(comp.get("name"), str) and comp["name"].strip(), "Each comparison needs a nonempty name")
        require(comp["name"] not in names, f"Duplicate comparison name: {comp['name']}")
        names.append(comp["name"])
        method = comp.get("method")
        require(isinstance(method, str) and method in METHODS, f"Unknown method: {method}")
        fields = comp.get("fields")
        _keys(fields, {"group", "value", "x", "y"}, "fields")
        expected = {"x", "y"} if method in CORRELATION else {"group", "value"} if method != "descriptive" else ({"value", "group"} if "group" in fields else {"value"})
        require(set(fields) == expected, f"{method} requires exactly these fields: {sorted(expected)}")
        require(all(isinstance(x, str) and x.strip() for x in fields.values()), "All fields must name columns")
        require(len(set(fields.values())) == len(fields), "Distinct field roles must name distinct columns")
        require(design["unit"] not in fields.values(), "A unit ID cannot also be a measurement or grouping column")
        if method != "descriptive":
            require(design["confirmed"], "Inferential analysis requires design.confirmed=true; establish the experimental unit first")
            required_structure = "paired" if method in PAIRED else "independent"
            require(design["structure"] == required_structure, f"{method} requires design.structure={required_structure}")
        if method not in CORRELATION and method != "descriptive":
            groups = comp.get("groups")
            require(isinstance(groups, list) and len(groups) == 2 and all(isinstance(x, str) and x.strip() for x in groups) and groups[0] != groups[1], "Two-group methods require two distinct explicit string groups")
        else:
            require("groups" not in comp, f"groups is not supported for {method}")
        level = comp.get("confidence_level", 0.95)
        require(type(level) in (int, float) and math.isfinite(level) and 0 < level < 1, "confidence_level must be between 0 and 1")
        if "difference_decimals" in comp:
            require(method == "wilcoxon" and type(comp["difference_decimals"]) is int and 0 <= comp["difference_decimals"] <= 15, "difference_decimals is an integer 0..15 for wilcoxon only")
    inferred = [comp["name"] for comp in comparisons if comp["method"] != "descriptive"]
    multiplicity = plan.get("multiplicity")
    require(len(inferred) <= 1 or multiplicity is not None, "Multiple inferential comparisons require a declared multiplicity family and adjustment")
    if multiplicity is not None:
        _keys(multiplicity, {"family", "adjustment", "comparisons"}, "multiplicity")
        require(inferred, "Multiplicity is only meaningful for inferential comparisons")
        require(isinstance(multiplicity.get("family"), str) and multiplicity["family"].strip(), "multiplicity.family must name the planned family")
        require(multiplicity.get("adjustment") in ("holm", "benjamini_hochberg"), "multiplicity.adjustment must be holm or benjamini_hochberg")
        members = multiplicity.get("comparisons")
        require(isinstance(members, list) and all(isinstance(x, str) for x in members) and len(members) == len(set(members)) and set(members) == set(inferred), "multiplicity.comparisons must list exactly all inferential comparison names once")
    return plan


def adjust_pvalues(values, method):
    """Stable Holm step-down or BH step-up adjustment, retaining input order."""
    require(method in ("holm", "benjamini_hochberg"), "Unknown p-value adjustment")
    p = np.asarray(values, dtype=float)
    require(p.ndim == 1 and len(p) > 0 and np.all(np.isfinite(p)) and np.all((p >= 0) & (p <= 1)), "p-values must be a nonempty finite vector in [0,1]")
    order = np.argsort(p, kind="stable")
    ordered = p[order]
    n = len(p)
    if method == "holm":
        adjusted = np.maximum.accumulate(ordered * np.arange(n, 0, -1))
    else:
        raw = ordered * n / np.arange(1, n + 1)
        adjusted = np.minimum.accumulate(raw[::-1])[::-1]
    output = np.empty(n)
    output[order] = np.minimum(adjusted, 1)
    return output.tolist()


def _read_csv(data_path):
    raw = data_path.read_bytes()
    try:
        reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
        header = next(reader)
    except (UnicodeError, StopIteration, csv.Error) as exc:
        raise AnalysisError(f"Cannot read a nonempty UTF-8 CSV: {exc}") from None
    require(header and all(name.strip() for name in header) and len(header) == len(set(header)), "CSV headers must be nonempty and unique")
    require(not any(name.startswith("_easyviz_") for name in header), "CSV headers starting _easyviz_ are reserved for provenance")
    rows = []
    try:
        for record_number, values in enumerate(reader, start=2):
            require(len(values) == len(header), f"CSV record {record_number} has {len(values)} fields; expected {len(header)} (blank records are not silently skipped)")
            row = dict(zip(header, values))
            row["_easyviz_source_record"] = record_number
            rows.append(row)
    except csv.Error as exc:
        raise AnalysisError(f"Malformed CSV: {exc}") from None
    require(rows, "CSV must contain observations")
    return header, rows, raw


def _finite(value, context):
    require(math.isfinite(float(value)), f"Non-finite numerical result for {context}; inspect scale and variance")
    return float(value)


def _summary(values, unit_count):
    values = np.asarray(values, dtype=float)
    require(len(values) > 0, "No observations remain for a descriptive summary")
    result = {"n_rows": len(values), "independent_unit_count": unit_count,
              "mean": float(np.mean(values)), "median": float(np.median(values)),
              "sd": float(np.std(values, ddof=1)) if len(values) > 1 else None,
              "q1": float(np.quantile(values, 0.25, method="linear")), "q3": float(np.quantile(values, 0.75, method="linear")),
              "quantile_method": "linear", "sd_ddof": 1,
              "minimum": float(np.min(values)), "maximum": float(np.max(values)),
              "interval": None, "interval_note": "Descriptive summary only; no confidence interval computed."}
    for key, value in result.items():
        if type(value) is float:
            _finite(value, key)
    return result


def _select(rows, header, comp, plan):
    fields = comp["fields"]
    unit = plan["design"]["unit"]
    needed = set(fields.values()) | ({unit} if unit else set())
    require(needed <= set(header), f"Missing columns for {comp['name']}: {sorted(needed - set(header))}")
    numeric = [fields["x"], fields["y"]] if comp["method"] in CORRELATION else [fields["value"]]
    selected = [dict(row) for row in rows if "groups" not in comp or row[fields["group"]] in comp["groups"]]
    require(selected, f"No rows match comparison {comp['name']}")
    tokens = plan.get("missing_tokens", ["", "NA", "NaN"])
    seen = set()
    for row in selected:
        if "group" in fields:
            require(row[fields["group"]].strip(), f"Missing group in CSV record {row['_easyviz_source_record']}")
        if unit:
            require(row[unit].strip(), f"Missing unit ID in CSV record {row['_easyviz_source_record']}; identity cannot be recovered by deleting measurements")
            require(row[unit] == row[unit].strip(), f"Padded unit ID in CSV record {row['_easyviz_source_record']}; resolve whitespace explicitly rather than creating distinct apparent units")
            key = (row[unit], row[fields["group"]]) if plan["design"]["structure"] == "paired" and "group" in fields else row[unit]
            require(key not in seen, f"Repeated unit {row[unit]!r} for {comp['name']}; aggregate technical replicates explicitly upstream or use a suitable repeated-measures method")
            seen.add(key)
        row["_easyviz_comparison"] = comp["name"]
        row["_easyviz_status"] = "included"
        row["_easyviz_exclusion"] = ""
        missing = []
        for column in numeric:
            if row[column] in tokens:
                missing.append(column)
            else:
                try:
                    value = float(row[column])
                except ValueError:
                    raise AnalysisError(f"Non-numeric value {row[column]!r} in {column}, CSV record {row['_easyviz_source_record']}") from None
                require(math.isfinite(value), f"Non-finite value in {column}, CSV record {row['_easyviz_source_record']}; declare a missing token explicitly if appropriate")
                row[f"_easyviz_numeric_{column}"] = value
        if missing:
            require(plan["missing_policy"] == "complete_case", f"Missing measurement in CSV record {row['_easyviz_source_record']}: {missing}; missing_policy=error")
            row["_easyviz_status"] = "excluded"
            row["_easyviz_exclusion"] = "missing_measurement:" + ",".join(missing)
    return selected


def _paired_rows(selected, comp, plan):
    unit = plan["design"]["unit"]
    group = comp["fields"]["group"]
    a, b = comp["groups"]
    by_unit = {}
    for row in selected:
        by_unit.setdefault(row[unit], {})[row[group]] = row
    pairs = []
    excluded_units = []
    for identity, members in by_unit.items():
        complete = a in members and b in members and all(row["_easyviz_status"] == "included" for row in members.values())
        if not complete:
            require(plan["missing_policy"] == "complete_case", f"Incomplete pair for unit {identity!r}; missing_policy=error")
            excluded_units.append(identity)
            for row in members.values():
                if row["_easyviz_status"] == "included":
                    row["_easyviz_status"] = "excluded"
                    row["_easyviz_exclusion"] = "incomplete_pair"
                else:
                    row["_easyviz_exclusion"] += ";incomplete_pair"
        else:
            pairs.append((identity, members[a], members[b]))
    return pairs, excluded_units


def _interval(low, high, level, method, note):
    return {"lower": _finite(low, "interval lower"), "upper": _finite(high, "interval upper"),
            "confidence_level": level, "method": method, "scope": "pointwise; not multiplicity-adjusted", "assumptions": note}


def _run_comparison(rows, header, comp, plan):
    method, fields, design = comp["method"], comp["fields"], plan["design"]
    selected = _select(rows, header, comp, plan)
    pairs = None
    excluded_pair_units = []
    if method in PAIRED:
        pairs, excluded_pair_units = _paired_rows(selected, comp, plan)
    included = [row for row in selected if row["_easyviz_status"] == "included"]
    require(included, f"No complete observations remain for {comp['name']}")
    unit = design["unit"]
    result = {"name": comp["name"], "method": method, "fields": fields,
              "counts": {"source_rows": len(rows), "selected_rows": len(selected), "included_rows": len(included),
                         "excluded_rows": len(selected) - len(included), "unselected_rows": len(rows) - len(selected),
                         "included_units": len({r[unit] for r in included}) if unit else None,
                         "independent_unit_count": len({r[unit] for r in included}) if unit and design["confirmed"] else None},
              "exclusions": [{"source_record": r["_easyviz_source_record"], "unit": r[unit] if unit else None,
                              "reason": r["_easyviz_exclusion"]} for r in selected if r["_easyviz_status"] == "excluded"],
              "statistic": None, "pvalue": None, "adjusted_pvalue": None, "adjustment": None,
              "effect": None, "interval": None, "interval_note": "No effect confidence interval computed for this method.",
              "summaries": [], "notes": []}
    level = comp.get("confidence_level", 0.95)
    if method in CORRELATION:
        x = np.array([r[f"_easyviz_numeric_{fields['x']}"] for r in included])
        y = np.array([r[f"_easyviz_numeric_{fields['y']}"] for r in included])
        require(len(x) >= 3, "Correlation requires at least three complete independent units")
        require(np.ptp(x) > 0 and np.ptp(y) > 0, "Correlation is undefined for a constant variable")
        for role, values in (("x", x), ("y", y)):
            result["summaries"].append({"variable": fields[role], "group": None, **_summary(values, len(values))})
        if method == "pearson":
            test = stats.pearsonr(x, y)
            result["pvalue_method"] = "SciPy Pearson exact beta null distribution"
            coefficient = float(test.statistic)
            if len(x) > 3 and abs(coefficient) < 1:
                z = math.atanh(coefficient)
                half = float(stats.norm.ppf((1 + level) / 2)) / math.sqrt(len(x) - 3)
                result["interval"] = _interval(math.tanh(z - half), math.tanh(z + half), level, "Fisher z", "Independent observations from a bivariate normal population; approximate interval.")
                result["interval_note"] = None
            else:
                result["interval_note"] = "Fisher z interval not computed for n=3 or an exactly perfect correlation."
            result["notes"].append("Pearson inference assumes independent bivariate normal observations; association does not establish causation.")
        else:
            ranks_x, ranks_y = stats.rankdata(x), stats.rankdata(y)
            coefficient = float(stats.pearsonr(ranks_x, ranks_y).statistic)
            if len(x) <= 8:
                def statistic(permuted, axis=-1):
                    centered = permuted - np.mean(permuted, axis=axis, keepdims=True)
                    yc = ranks_y - np.mean(ranks_y)
                    return np.sum(centered * yc, axis=axis) / np.sqrt(np.sum(centered ** 2, axis=axis) * np.sum(yc ** 2))
                test = stats.permutation_test((ranks_x,), statistic, permutation_type="pairings", n_resamples=np.inf,
                                              alternative="two-sided", vectorized=True)
                result["pvalue_method"] = "Exact pairing permutation; two-sided twice the smaller tail"
            else:
                test = stats.spearmanr(x, y)
                result["pvalue_method"] = "SciPy Spearman asymptotic approximation"
                if len(x) <= 500:
                    result["notes"].append("Spearman asymptotic p-value can be inaccurate at modest sample sizes; use a separately planned permutation analysis if inference is central.")
            result["notes"].append("Spearman measures monotonic association; no effect confidence interval computed.")
        result["statistic"] = _finite(coefficient, "correlation")
        result["pvalue"] = _finite(test.pvalue, "p-value")
        result["effect"] = {"name": method + "_r", "estimate": coefficient, "direction": f"{fields['x']} with {fields['y']}"}
    elif method == "descriptive":
        groups = list(dict.fromkeys(r[fields["group"]] for r in included)) if "group" in fields else [None]
        for group in groups:
            members = [r for r in included if group is None or r[fields["group"]] == group]
            values = [r[f"_easyviz_numeric_{fields['value']}"] for r in members]
            n_units = len({r[unit] for r in members}) if unit and design["confirmed"] else None
            result["summaries"].append({"variable": fields["value"], "group": group, **_summary(values, n_units)})
        result["notes"].append("Rows are descriptive observations. Independent sample counts are only reported for a confirmed sampling-unit design.")
    else:
        groups = comp["groups"]
        result["groups"] = groups
        if pairs is not None:
            values_a = np.array([r[f"_easyviz_numeric_{fields['value']}"] for _, r, _ in pairs])
            values_b = np.array([r[f"_easyviz_numeric_{fields['value']}"] for _, _, r in pairs])
            result["counts"]["complete_pairs"] = len(pairs)
            result["counts"]["excluded_pair_units"] = len(excluded_pair_units)
            result["pair_unit_ids"] = [identity for identity, _, _ in pairs]
            result["excluded_pair_unit_ids"] = excluded_pair_units
        else:
            values_a = np.array([r[f"_easyviz_numeric_{fields['value']}"] for r in included if r[fields['group']] == groups[0]])
            values_b = np.array([r[f"_easyviz_numeric_{fields['value']}"] for r in included if r[fields['group']] == groups[1]])
        require(len(values_a) >= 2 and len(values_b) >= 2, "Two-group inference requires at least two complete independent units per group, or two complete pairs")
        for group, values in zip(groups, (values_a, values_b)):
            result["summaries"].append({"variable": fields["value"], "group": group, **_summary(values, len(values))})
        direction = f"{groups[0]} minus {groups[1]}"
        if method == "welch":
            va, vb = np.var(values_a, ddof=1) / len(values_a), np.var(values_b, ddof=1) / len(values_b)
            se = math.sqrt(float(va + vb))
            require(math.isfinite(se) and se > 0, "Welch comparison requires a positive finite standard error")
            df = float((va + vb) ** 2 / (va ** 2 / (len(values_a) - 1) + vb ** 2 / (len(values_b) - 1)))
            difference = float(np.mean(values_a) - np.mean(values_b))
            test = stats.ttest_ind(values_a, values_b, equal_var=False, alternative="two-sided")
            margin = float(stats.t.ppf((1 + level) / 2, df)) * se
            result["degrees_of_freedom"] = df
            result["effect"] = {"name": "mean_difference", "estimate": difference, "direction": direction}
            result["interval"] = _interval(difference - margin, difference + margin, level, "Welch-Satterthwaite t", "Independent units; normal populations or sufficient sample sizes for mean inference; variances may differ.")
            result["interval_note"] = None
            result["pvalue_method"] = "Two-sided Welch t with Satterthwaite degrees of freedom"
        elif method == "mannwhitney":
            pooled = np.concatenate((values_a, values_b))
            ties = len(np.unique(pooled)) < len(pooled)
            permutations = math.comb(len(pooled), len(values_a))
            if ties and permutations <= 20000:
                scipy_method = stats.PermutationMethod(n_resamples=np.inf)
                result["pvalue_method"] = "Exact label permutation with ties"
            elif not ties and min(len(values_a), len(values_b)) <= 8:
                scipy_method = "exact"
                result["pvalue_method"] = "Exact Mann-Whitney U null distribution; no ties"
            else:
                scipy_method = "asymptotic"
                result["pvalue_method"] = "Tie-corrected normal approximation with continuity correction"
                if min(len(values_a), len(values_b)) < 10:
                    result["notes"].append("Small tied group: asymptotic approximation used because exhaustive permutations exceed 20,000; plan a permutation analysis if needed.")
            test = stats.mannwhitneyu(values_a, values_b, alternative="two-sided", method=scipy_method)
            delta = 2 * float(test.statistic) / (len(values_a) * len(values_b)) - 1
            result["effect"] = {"name": "cliffs_delta", "estimate": delta, "direction": f"P({groups[0]} > {groups[1]}) minus P({groups[0]} < {groups[1]})"}
            result["notes"].append("Tests equality of distributions; it is not generally a test of median differences. Cliff's delta has no computed confidence interval.")
        else:
            differences = values_a - values_b
            if method == "paired_t":
                se = float(np.std(differences, ddof=1) / math.sqrt(len(differences)))
                require(math.isfinite(se) and se > 0, "Paired t requires positive finite variation in within-unit differences")
                difference = float(np.mean(differences))
                test = stats.ttest_rel(values_a, values_b, alternative="two-sided")
                df = len(differences) - 1
                margin = float(stats.t.ppf((1 + level) / 2, df)) * se
                result["degrees_of_freedom"] = df
                result["effect"] = {"name": "mean_paired_difference", "estimate": difference, "direction": direction}
                result["interval"] = _interval(difference - margin, difference + margin, level, "Paired-difference t", "Independent subjects; within-subject differences are normally distributed or mean inference is otherwise justified.")
                result["interval_note"] = None
                result["pvalue_method"] = "Two-sided paired t on subject-aligned differences"
            else:
                if "difference_decimals" in comp:
                    differences = np.around(differences, decimals=comp["difference_decimals"])
                    result["notes"].append(f"Within-unit differences rounded to {comp['difference_decimals']} decimals by explicit plan.")
                nonzero = differences[differences != 0]
                require(len(nonzero) > 0, "Wilcoxon is undefined when all paired differences are zero")
                ties = len(np.unique(np.abs(nonzero))) < len(nonzero)
                # zero_method='wilcox' conditions on nonzero differences. The
                # effective sign sample, not the total paired-subject count,
                # determines both routing and exhaustive permutation size.
                # Keep every complete pair in summaries and the source trace.
                if not ties and len(nonzero) <= 50:
                    scipy_method = "exact"
                    result["pvalue_method"] = "Exact signed-rank null distribution of nonzero differences; no tied absolute ranks"
                elif len(nonzero) <= 13:
                    scipy_method = stats.PermutationMethod(n_resamples=np.inf)
                    result["pvalue_method"] = "Exact sign permutation of nonzero differences with tied absolute ranks"
                else:
                    scipy_method = "approx"  # compatible with the declared SciPy >=1.13 baseline
                    result["pvalue_method"] = "Normal approximation on nonzero differences; ties corrected when present; no continuity correction"
                test = stats.wilcoxon(nonzero, alternative="two-sided", zero_method="wilcox", correction=False, method=scipy_method)
                ranks = stats.rankdata(np.abs(nonzero))
                rank_biserial = float(np.sum(ranks * np.sign(nonzero)) / np.sum(ranks))
                result["counts"]["nonzero_pairs"] = len(nonzero)
                result["counts"]["zero_difference_pairs"] = len(differences) - len(nonzero)
                result["effect"] = {"name": "matched_rank_biserial", "estimate": rank_biserial, "direction": direction}
                result["notes"].append("Assumes symmetric within-subject difference distribution; zero differences excluded from rank statistic, retained in source trace. No effect confidence interval computed. Floating-point ties require explicit difference_decimals when measurement precision is known.")
        result["statistic"] = _finite(test.statistic, "test statistic")
        result["pvalue"] = _finite(test.pvalue, "p-value")
        _finite(result["effect"]["estimate"], "effect")
    return result, selected


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_plan(path):
    raw = Path(path).read_bytes()
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_json_object), raw


def _json_bytes(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _csv_bytes(header, rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=header, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _methodology(report):
    design = report["plan"]["design"]
    lines = ["# Planned analysis", "", f"Question: {report['plan']['question']}", "",
             f"Design: {design['structure']}; confirmed: {design['confirmed']}; unit column: {design['unit']}; unit meaning: {design['unit_definition']}",
             f"Missing policy: {report['plan']['missing_policy']}. Source measurements are preserved.",
             "All inferential tests are two-sided. The helper ran only the supplied methods and comparisons; it did not choose methods by p-values. Predeclaration is the user's responsibility. All reported confidence intervals are pointwise, not adjusted for multiplicity.", ""]
    if design["structure"] == "paired":
        lines += ["For paired comparisons, incomplete-pair exclusions remove the whole subject pair.", ""]
    if report["plan"].get("multiplicity"):
        mult = report["plan"]["multiplicity"]
        lines += [f"Planned family: {mult['family']}; adjustment: {mult['adjustment']}; members: {', '.join(mult['comparisons'])}.",
                  "Holm controls family-wise error under arbitrary dependence. Benjamini-Hochberg controls false discovery rate under independence or appropriate positive dependence; its applicability must be justified for the planned family.", ""]
    for result in report["comparisons"]:
        lines += [f"## {result['name']}", "", f"Method: {result['method']}", f"Counts: {json.dumps(result['counts'], ensure_ascii=False)}", f"Excluded observations: {len(result['exclusions'])}"]
        if result["effect"]:
            lines += [f"Effect: {json.dumps(result['effect'], ensure_ascii=False)}", f"P-value calculation: {result['pvalue_method']}", f"Unadjusted p-value: {result['pvalue']}; adjusted p-value: {result['adjusted_pvalue']}; adjustment: {result['adjustment']}"]
        if result["interval"]:
            lines += [f"Interval: {json.dumps(result['interval'], ensure_ascii=False)}"]
        else:
            lines += [f"Interval: not computed. {result['interval_note']}"]
        lines += result["notes"] + [""]
    lines += ["## Provenance", "", f"Data: {report['provenance']['data']['path']}", f"Data SHA-256: {report['provenance']['data']['sha256']}",
              f"Helper SHA-256: {report['provenance']['helper']['sha256']}", f"Runtime: {json.dumps(report['provenance']['runtime'])}", "",
              "The original CSV fields and unit strings (including leading zeros) are copied unchanged into analyzed-data.csv. _easyviz_source_record is a 1-based CSV record number including the header; quoted multi-line fields count as one record.", ""]
    return "\n".join(lines).encode("utf-8")


def _write_attempt(out, payloads):
    """Reserve a fresh directory, atomically publish files, and publish success last."""
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        out.mkdir()
    except FileExistsError:
        raise AnalysisError(f"Output already exists; choose a fresh attempt directory: {out}") from None
    try:
        # No successful manifest is present until every supporting file is complete.
        for name, content in payloads.items():
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=out, prefix=f".{name}.", delete=False) as stream:
                    temporary = Path(stream.name)
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.link(temporary, out / name)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
    except Exception:
        shutil.rmtree(out)
        raise


def analyze(data_path, plan, out, *, plan_path=None):
    data_path, out = Path(data_path), Path(out)
    require(data_path.is_file(), f"Source CSV does not exist: {data_path}")
    require(not out.exists() and not out.is_symlink(), f"Output already exists; choose a fresh attempt directory: {out}")
    for source in [data_path] + ([Path(plan_path)] if plan_path is not None else []):
        require(out.resolve() != source.resolve() and out.resolve() not in source.resolve().parents, "Output must be isolated from source files")
    validate_plan(plan)
    source_plan_raw = None
    if plan_path is not None:
        source_plan, source_plan_raw = read_plan(plan_path)
        require(source_plan == plan, "Supplied plan differs from plan_path; analyze the exact saved plan")
    header, rows, raw = _read_csv(data_path)
    comparisons, trace = [], []
    for comp in plan["comparisons"]:
        result, selected = _run_comparison(rows, header, comp, plan)
        comparisons.append(result)
        trace.extend(selected)
    if plan.get("multiplicity"):
        mult = plan["multiplicity"]
        family = [r for r in comparisons if r["name"] in mult["comparisons"]]
        for result, adjusted in zip(family, adjust_pvalues([r["pvalue"] for r in family], mult["adjustment"])):
            result["adjusted_pvalue"] = adjusted
            result["adjustment"] = {"family": mult["family"], "method": mult["adjustment"], "family_size": len(family)}
    helper = Path(__file__).resolve()
    report = {"schema_version": 1, "status": "complete", "track": "create", "plan": plan, "comparisons": comparisons,
              "provenance": {"created_utc": datetime.now(timezone.utc).isoformat(),
                             "data": {"path": str(data_path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(), "csv_records": len(rows)},
                             "plan": {"path": str(Path(plan_path).resolve()) if plan_path is not None else None, "sha256": hashlib.sha256(_json_bytes(plan)).hexdigest(), "hash_encoding": "saved normalized plan.json bytes"},
                             "helper": {"path": str(helper), "sha256": hashlib.sha256(helper.read_bytes()).hexdigest()},
                             "runtime": {"python": platform.python_version(), "numpy": version("numpy"), "scipy": version("scipy")}}}
    if plan_path is not None:
        report["provenance"]["plan"]["source_sha256"] = hashlib.sha256(source_plan_raw).hexdigest()
    trace_header = ["_easyviz_comparison", "_easyviz_source_record", "_easyviz_status", "_easyviz_exclusion"] + header
    summary_rows = []
    for result in comparisons:
        for summary in result["summaries"]:
            effect, interval = result["effect"] or {}, result["interval"] or {}
            summary_rows.append({"comparison": result["name"], "method": result["method"], **summary,
                                 "effect": effect.get("name"), "effect_estimate": effect.get("estimate"), "effect_direction": effect.get("direction"),
                                 "effect_interval_lower": interval.get("lower"), "effect_interval_upper": interval.get("upper"),
                                 "effect_interval_level": interval.get("confidence_level"), "effect_interval_scope": interval.get("scope"),
                                 "pvalue": result["pvalue"], "adjusted_pvalue": result["adjusted_pvalue"],
                                 "adjustment": result["adjustment"]["method"] if result["adjustment"] else None})
    summary_header = list(summary_rows[0])
    payloads = {"plan.json": _json_bytes(plan), "analyzed-data.csv": _csv_bytes(trace_header, trace),
                "summary.csv": _csv_bytes(summary_header, summary_rows), "methodology.md": _methodology(report)}
    report["artifacts"] = {name: {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)} for name, content in payloads.items()}
    payloads["results.json"] = _json_bytes(report)
    _write_attempt(out, payloads)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, help="Prepared UTF-8 CSV, preserved unchanged")
    parser.add_argument("--plan", type=Path, help="Explicit planned analysis JSON")
    parser.add_argument("--out", type=Path, help="Fresh isolated attempt directory")
    parser.add_argument("--describe-plan", action="store_true", help="Print the plan contract without reading data")
    args = parser.parse_args()
    if args.describe_plan:
        print(json.dumps(PLAN_DESCRIPTION, indent=2))
        return
    if args.data is None or args.plan is None or args.out is None:
        parser.error("--data, --plan, and --out are required unless --describe-plan is used")
    try:
        plan, _ = read_plan(args.plan)
        report = analyze(args.data, plan, args.out, plan_path=args.plan)
    except (AnalysisError, OSError, ValueError, ImportError) as exc:
        parser.exit(2, f"EasyViz analysis: {exc}\n")
    print(json.dumps({"status": report["status"], "results": str(args.out / "results.json"),
                      "comparisons": len(report["comparisons"]), "note": "Inspect the saved methodology and exclusions before interpreting results."}))


if __name__ == "__main__":
    main()
