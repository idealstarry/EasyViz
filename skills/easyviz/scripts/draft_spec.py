#!/usr/bin/env python3
"""Write a validated panel specification from explicit chart and column roles.

This entry point only writes a new JSON specification. Render the saved draft
with render.py, then inspect the actual exports before delivering a panel.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import tempfile


# A portable skill need not be installed as a Python package or on PYTHONPATH.
_loader = importlib.util.spec_from_file_location("easyviz_draft_renderer", Path(__file__).with_name("render.py"))
renderer = importlib.util.module_from_spec(_loader)
_loader.loader.exec_module(renderer)


def parse_fields(assignments):
    """Parse repeatable role=column arguments without guessing column meanings."""
    renderer.require(isinstance(assignments, (list, tuple)), "Fields must be a list of role=column assignments")
    fields = {}
    for assignment in assignments:
        renderer.require(isinstance(assignment, str) and "=" in assignment, "Each --field must use role=column")
        role, column = assignment.split("=", 1)
        role = role.strip()
        renderer.require(bool(role) and bool(column.strip()), "Each --field must name a nonempty role and column")
        renderer.require(role not in fields, f"Duplicate --field role: {role}")
        fields[role] = column
    return fields


def _write_new_json(path, spec):
    """Publish a complete JSON file atomically, without replacing a destination."""
    text = json.dumps(spec, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        # Same-directory hard linking creates the final name in one operation;
        # EEXIST protects against a destination appearing after initial checks.
        os.link(temporary, path)
    except FileExistsError:
        raise renderer.SpecError(f"Output already exists; choose a new specification path: {path}") from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def draft(data_path, chart, assignments, out, *, normalization=None,
          panel_size_mm=None, font=None, profile=None, panel=None):
    """Validate explicit mappings and create a new, editable draft specification."""
    data_path, out = Path(data_path), Path(out)
    renderer.require(out.resolve() != data_path.resolve(), "The output specification cannot replace the source data")
    renderer.require(not out.exists() and not out.is_symlink(), f"Output already exists; choose a new specification path: {out}")
    renderer.require_core_chart(chart)
    renderer.require((profile is None) == (panel is None), "--profile and --panel must be supplied together")
    renderer.require(not (profile is not None and panel_size_mm is not None), "--panel-size-mm cannot be combined with --profile; use the named panel dimensions")
    renderer.require(chart == "composition" or normalization is None, "--normalization is only supported for composition")

    spec = {"chart": chart, "fields": parse_fields(assignments), "layout": {"auto_fit": True}}
    if profile is None:
        # New create drafts adopt an editable starting hierarchy. Existing specs
        # and shared profiles retain their accepted stroke settings.
        spec["line_roles"] = deepcopy(renderer.SCHEMA["line_roles"])
        if chart == "scatter":
            spec["options"] = {"alpha": 1, "point_style": "filled"}
        elif chart == "distribution":
            spec["options"] = {"alpha": 1, "point_style": "filled", "box_style": "outline", "box_width": .18}
    if chart == "composition":
        renderer.require(normalization in ("none", "sample_sum", "denominator"), "Composition requires --normalization none, sample_sum, or denominator")
        spec["options"] = {"normalization": normalization}
    if panel_size_mm is not None:
        renderer.require(isinstance(panel_size_mm, (list, tuple)) and len(panel_size_mm) == 2, "--panel-size-mm requires width and height in mm")
        spec["layout"].update(width_mm=panel_size_mm[0], height_mm=panel_size_mm[1])
    if font is not None:
        spec["layout"]["font"] = font
    if profile is not None:
        # Absolute reference remains valid when the draft is saved elsewhere or
        # rendered from another working directory. Keep the shared provenance.
        spec.update(profile=str(Path(profile).resolve()), panel=panel)

    resolved, _ = renderer.resolve_spec(spec, spec_path=out)
    renderer.prepare(data_path, resolved)
    _write_new_json(out, spec)
    return spec


def main():
    focused = ", ".join(f"{chart}: {Path(route['script']).name}" for chart, route in renderer.FOCUSED_RECIPES.items())
    parser = argparse.ArgumentParser(description=__doc__, epilog=(
        f"Focused recipes have separate scripts ({focused}). Use their --describe-spec; "
        "render.py --describe-spec lists their absolute script/documentation paths and required roles."))

    def core_chart(value):
        try:
            renderer.require_core_chart(value)
        except renderer.SpecError as exc:
            raise argparse.ArgumentTypeError(str(exc)) from None
        return value

    parser.add_argument("--data", required=True, type=Path, help="Prepared source CSV; data is not reshaped or changed")
    parser.add_argument("--chart", required=True, choices=list(renderer.REQUIRED), type=core_chart)
    parser.add_argument("--field", action="append", required=True, help="Explicit role=column mapping; repeat for every required role")
    parser.add_argument("--out", required=True, type=Path, help="New JSON specification path; an existing path is never overwritten")
    parser.add_argument("--normalization", choices=("none", "sample_sum", "denominator"), help="Required for composition; never inferred")
    parser.add_argument("--panel-size-mm", nargs=2, type=float, metavar=("WIDTH", "HEIGHT"), help="Preserve an explicit whole-canvas size in mm")
    parser.add_argument("--font", help="Requested font; normal renderer font and glyph checks still apply")
    parser.add_argument("--profile", type=Path, help="Existing shared figure-profile JSON; requires --panel")
    parser.add_argument("--panel", help="Named dimensions from the shared profile; requires --profile")
    args = parser.parse_args()
    try:
        spec = draft(args.data, args.chart, args.field, args.out, normalization=args.normalization,
                     panel_size_mm=args.panel_size_mm, font=args.font, profile=args.profile, panel=args.panel)
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(2, f"EasyViz: {exc}\n")
    print(json.dumps({"status": "draft", "specification": str(args.out), "chart": spec["chart"],
                      "note": "Data and mappings validated; render the draft and inspect the exported panel."}, ensure_ascii=False))


if __name__ == "__main__":
    main()
