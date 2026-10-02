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
        "spec_paths": spec_paths or [], "editable": editable or [], "_artist": artist,
    })
    return gid


def attach_layout(fig, spec):
    """Add shared axes, labels and guides after final layout has been measured."""
    manager = getattr(fig, "_easyviz_legend_layout", None)
    guide_axes = {entry["artist"] for entry in manager.entries if entry["kind"] == "colorbar"} if manager else set()
    for index, ax in enumerate(axis for axis in fig.axes if axis not in guide_axes):
        register(fig, ax, "axes", "Data region" if index == 0 else f"Data region {index + 1}", key=index)
        for direction in ("x", "y"):
            label = getattr(ax, f"{direction}axis").label
            if label.get_visible() and label.get_text().strip():
                register(fig, label, "axis-label", label.get_text(), key=[index, direction],
                         spec_paths=[pointer("labels", direction)] if index == 0 and direction in spec.get("labels", {}) else [],
                         editable=["text"])
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
    svg = out / "panel.svg" if "svg" in spec.get("formats", ["pdf", "png"]) else None
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
    canonical = json.dumps(spec, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
    manifest = {
        "schema_version": 1, "chart": spec.get("chart", "custom"),
        "track": getattr(fig, "_easyviz_track", None),
        "panel": {"width_mm": layout["width_mm"], "height_mm": layout["height_mm"]},
        "coordinate_system": "bbox_mm uses canvas lower-left; SVG y increases downward",
        "version": {"figure_sha256": _hash_file(svg), "spec_sha256": hashlib.sha256(canonical).hexdigest(),
                    "input_sha256": _hash_file(data), "source_script_sha256": _hash_file(source)},
        "input": {"data_file": str(data) if data else None, "spec_file": str(specification) if specification else None,
                  "source_script": str(source) if source else None, "supplied_spec_sha256": _hash_file(specification)},
        "elements": elements,
        "scope": "Registered artists and shared guides only. Collections select a point group. Unregistered individual points and raster heatmap cells require region notes. No data coordinates or quantitative areas are draggable.",
    }
    (out / "elements.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    return manifest
