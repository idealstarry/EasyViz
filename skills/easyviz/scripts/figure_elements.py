"""Map rendered SVG groups to plotting meanings without changing their geometry.

Custom scripts can register their own artists before calling the shared export
helper. Requests are instructions for an Agent, never mutations of source data.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def identity(role, key):
    encoded = json.dumps([role, key], ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode()
    slug = re.sub(r"[^a-z0-9-]", "-", role.lower()).strip("-") or "element"
    return f"easyviz-{slug}-{hashlib.sha256(encoded).hexdigest()[:16]}"


def pointer(*parts):
    return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in parts)


def register(fig, artist, role, label, *, key=None, source_keys=None,
             spec_paths=None, editable=None):
    """Tag one selectable artist. A collection is a group, not individual points."""
    paths = [] if spec_paths is None else spec_paths
    edits = [] if editable is None else editable
    if not isinstance(paths, list) or any(not isinstance(path, str) for path in paths):
        raise ValueError("spec_paths must be a list of specification paths")
    if isinstance(edits, dict):
        for property_name, path in edits.items():
            if (not isinstance(property_name, str) or not property_name.strip()
                    or not isinstance(path, str) or not path.startswith("/")
                    or any(not part or re.search(r"~(?![01])", part) for part in path[1:].split("/"))
                    or path not in paths):
                raise ValueError("Each editable binding must name a property and a valid JSON pointer in spec_paths")
    elif not isinstance(edits, list) or any(not isinstance(name, str) or not name.strip() for name in edits):
        raise ValueError("editable must be a property list or property-to-pointer mapping")
    if not hasattr(fig, "_easyviz_elements"):
        fig._easyviz_elements = []
    gid = artist.get_gid() or identity(role, key if key is not None else label)
    artist.set_gid(gid)
    if any(entry["id"] == gid for entry in fig._easyviz_elements):
        existing = next(entry for entry in fig._easyviz_elements if entry["id"] == gid)
        if existing["_artist"] is not artist:
            raise ValueError(f"Duplicate semantic element ID: {gid}")
        return gid
    fig._easyviz_elements.append({
        "id": gid, "role": role, "label": str(label), "source_keys": source_keys or [],
        "spec_paths": paths.copy(), "editable": edits.copy(), "_artist": artist,
    })
    return gid


def attach_layout(fig, spec):
    """Add shared axes, labels and guides after final layout has been measured."""
    # Locators and formatters finish tick locations/text during a draw. Tag the
    # actual visible decorations rather than latent ticks outside the limits.
    fig.canvas.draw()
    manager = getattr(fig, "_easyviz_legend_layout", None)
    guide_axes = {entry["artist"] for entry in manager.entries if entry["kind"] == "colorbar"} if manager else set()
    for index, ax in enumerate(axis for axis in fig.axes if axis not in guide_axes):
        register(fig, ax, "axes", "Data region" if index == 0 else f"Data region {index + 1}", key=index)
        if not ax.get_visible() or not ax.axison:
            continue
        for side, spine in ax.spines.items():
            if side not in {"bottom", "top", "left", "right"} or not spine.get_visible():
                continue
            direction = "x" if side in {"bottom", "top"} else "y"
            register(fig, spine, "axis-line", f"{direction.upper()} axis line · {side}",
                     key=[index, direction, side],
                     source_keys=[{"axis_index": index, "axis": direction, "side": side}],
                     editable=["color", "linewidth"])
        for direction in ("x", "y"):
            axis = getattr(ax, f"{direction}axis")
            if not axis.get_visible():
                continue
            label = axis.label
            if label.get_visible() and label.get_text().strip():
                register(fig, label, "axis-label", label.get_text(), key=[index, direction],
                         spec_paths=[pointer("labels", direction)] if index == 0 and direction in spec.get("labels", {}) else [],
                         editable=["text"])
            lower, upper = sorted(float(value) for value in axis.get_view_interval())
            tolerance = max(abs(lower), abs(upper), 1.0) * 1e-12
            sides = ("bottom", "top") if direction == "x" else ("left", "right")
            for kind, ticks in (("major", axis.get_major_ticks()), ("minor", axis.get_minor_ticks())):
                for tick in ticks:
                    location = float(tick.get_loc())
                    if (not tick.get_visible() or not math.isfinite(location)
                            or not lower - tolerance <= location <= upper + tolerance):
                        continue
                    for side, mark, tick_label in zip(sides, (tick.tick1line, tick.tick2line), (tick.label1, tick.label2)):
                        key = [index, direction, kind, side, location]
                        source = [{"axis_index": index, "axis": direction, "side": side,
                                   "tick_kind": kind, "tick_location": location}]
                        if mark.get_visible():
                            register(fig, mark, "axis-tick", f"{direction.upper()} {kind} tick · {location:g} · {side}",
                                     key=key, source_keys=source, editable=["color", "linewidth"])
                        if tick_label.get_visible() and tick_label.get_text().strip():
                            paths = []
                            columns = getattr(fig, "_easyviz_column_label_keys", [])
                            if index == 0 and direction == "x" and kind == "major" and location.is_integer() and 0 <= int(location) < len(columns):
                                column = columns[int(location)]
                                source = [{**source[0], "column": column, "display_label": tick_label.get_text()}]
                                paths = [pointer("options", "column_labels", column)]
                            register(fig, tick_label, "tick-label", f"{direction.upper()} tick label · {tick_label.get_text()} · {side}",
                                     key=key, source_keys=source, spec_paths=paths, editable=["color", "fontsize"])
    if manager:
        for guide_index, entry in enumerate(manager.entries):
            kind, request = entry["kind"], entry["request"]
            role_key = [kind, request.get("shape", ""), sorted(map(str, request.get("labels", []))), guide_index]
            register(fig, entry["artist"], "legend", f"{kind.capitalize()} guide", key=role_key,
                     spec_paths=[pointer("legends", kind)], editable=["layout"])
            if kind == "categorical" and request.get("shape") != "symbols":
                for handle, label in zip(entry["artist"].legend_handles, request["labels"]):
                    register(fig, handle, "legend-key", label, key=[role_key, str(label)],
                             source_keys=[{"category": str(label)}],
                             spec_paths=[pointer("colors", label)], editable=["color"])
            if kind == "colorbar":
                cb = entry["colorbar"]
                label = cb.ax.yaxis.label if cb.orientation == "vertical" else cb.ax.xaxis.label
                if label.get_text().strip():
                    register(fig, label, "guide-label", label.get_text(), key=role_key,
                             spec_paths=[pointer("labels", "color")], editable=["text"])
    # Explicit IDs in focused/custom implementations remain useful even when
    # their own semantic layer has not yet registered metadata.
    known = {item["id"] for item in getattr(fig, "_easyviz_elements", [])}
    for artist in fig.findobj():
        gid = artist.get_gid()
        if gid and str(gid).startswith("easyviz-") and gid not in known:
            register(fig, artist, "custom-layer", str(gid), key=str(gid))
            known.add(gid)


def _hash_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if path and Path(path).is_file() else None


def write(fig, out, spec, layout):
    """Write a map bound to the actual SVG bytes and the resolved specification."""
    out = Path(out)
    svg = out / "panel.svg" if "svg" in spec.get("formats", ["svg"]) else None
    svg_ids = None
    if svg is not None and svg.is_file():
        svg_ids = {element.attrib["id"] for element in ET.parse(svg).iter() if "id" in element.attrib}
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    factor = 25.4 / fig.dpi
    elements = []
    for record in getattr(fig, "_easyviz_elements", []):
        if svg_ids is not None and record["id"] not in svg_ids:
            continue
        item = {key: value for key, value in record.items() if key != "_artist"}
        try:
            bounds = record["_artist"].get_window_extent(renderer)
            values = [float(v * factor) for v in (bounds.x0, bounds.y0, bounds.width, bounds.height)]
            if all(math.isfinite(value) for value in values) and values[2] >= 0 and values[3] >= 0:
                item["bbox_mm"] = values
        except (AttributeError, TypeError, ValueError):
            pass
        elements.append(item)
    source = getattr(fig, "_easyviz_source_script", None)
    data = getattr(fig, "_easyviz_data_file", None)
    specification = getattr(fig, "_easyviz_spec_file", None)
    captured = getattr(fig, "_easyviz_source_bindings", {})
    def source_hash(role, path):
        record = captured.get(role) if isinstance(captured, dict) else None
        if isinstance(record, dict) and path is not None and record.get("path") == str(Path(path).resolve()):
            return record.get("sha256")
        return _hash_file(path)
    canonical = json.dumps(spec, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
    manifest = {
        "schema_version": 1, "chart": spec.get("chart", "custom"),
        "track": getattr(fig, "_easyviz_track", None),
        "panel": {"width_mm": layout["width_mm"], "height_mm": layout["height_mm"]},
        "coordinate_system": "bbox_mm uses canvas lower-left; SVG y increases downward",
        "version": {"figure_sha256": _hash_file(svg), "spec_sha256": hashlib.sha256(canonical).hexdigest(),
                    "input_sha256": source_hash("data_file", data), "source_script_sha256": source_hash("source_script", source)},
        "input": {"data_file": str(data) if data else None, "spec_file": str(specification) if specification else None,
                  "source_script": str(source) if source else None, "supplied_spec_sha256": source_hash("spec_file", specification)},
        "elements": elements,
        "scope": "Registered artists and shared guides only. Collections select a point group. Unregistered individual points and raster heatmap cells require region notes. No data coordinates or quantitative areas are draggable.",
    }
    auxiliary = {}
    if isinstance(captured, dict):
        for role, record in captured.items():
            if role in ("data_file", "source_script", "spec_file"):
                continue
            if (not isinstance(role, str) or not role.strip() or not isinstance(record, dict)
                    or not isinstance(record.get("path"), str) or not record["path"].strip()
                    or not isinstance(record.get("sha256"), str)
                    or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])):
                raise ValueError("Consumed auxiliary bindings need an actual path and source digest")
            auxiliary[role] = {"path": str(Path(record["path"]).expanduser().resolve()), "sha256": record["sha256"]}
    if auxiliary:
        manifest["input"]["auxiliary_inputs"] = auxiliary
        encoded = json.dumps({role: record["sha256"] for role, record in auxiliary.items()},
                             ensure_ascii=False, sort_keys=True, allow_nan=False,
                             separators=(",", ":")).encode()
        manifest["version"]["auxiliary_inputs_sha256"] = hashlib.sha256(encoded).hexdigest()
    colors = getattr(fig, "_easyviz_resolved_colors", None)
    if isinstance(colors, dict) and colors:
        palette = json.dumps(colors, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
        manifest["version"]["resolved_colors_sha256"] = hashlib.sha256(palette).hexdigest()
    (out / "elements.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    return manifest
