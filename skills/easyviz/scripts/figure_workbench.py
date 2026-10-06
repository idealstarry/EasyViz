#!/usr/bin/env python3
"""Open a project-scoped EasyViz figure library and SVG review workbench.

Start with --project-dir PROJECT, optionally --figure-dir ATTEMPT and --open.
Import portable .ev projects, save drafts or submit edits to a connected Agent.
The local service uses the standard library; rendering needs plotting packages.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager, ExitStack
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import tempfile
import threading
import time
import unicodedata
from urllib.parse import parse_qs, urlsplit
import uuid
import xml.etree.ElementTree as ET
import webbrowser
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figure_handoff import HandoffError, normalize_inputs, bound_version, validate_receipt

STATIC = Path(__file__).with_name("workbench")
PACKAGE_ROOT = Path(__file__).resolve().parents[3]
# Standalone plugins and development checkouts share the same canonical mark.
LOGO = PACKAGE_ROOT / "assets/logo.svg"
if not LOGO.is_file():
    LOGO = PACKAGE_ROOT / "plugins/easyviz/assets/logo.svg"
FILES = {"panel.svg", "panel.pdf", "panel.png", "settings.json", "qa.json", "elements.json", "handoff.json"}
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_REQUEST_BYTES = 64 * 1024
MAX_BATCH_BYTES = 100 * MAX_REQUEST_BYTES
MAX_FIGURE_INFO_BYTES = 4096
MAX_FIGURE_NAME_LENGTH = 120
LEDGER_LOCK_TIMEOUT = 5.
_ANY_LEDGER = object()
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


class WorkbenchError(ValueError):
    """An invalid figure or edit request; safe to show to the local user."""


@contextmanager
def ledger_file_lock(root, *, timeout=None):
    """Bounded OS lock shared by browser servers and CLI processes.

    Kernel locks release on process exit, so an abandoned lock file is harmless.
    Keep the inode: unlinking a live lock could let two writers hold different
    files under the same name. No cached process-global locks are used.
    """
    timeout = LEDGER_LOCK_TIMEOUT if timeout is None else timeout
    path = Path(root) / ".requests.lock"
    if path.is_symlink():
        raise WorkbenchError("Request lock must be a regular local file")
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0), 0o600)
    acquired = False
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_size > 1024:
            raise WorkbenchError("Request lock must be a bounded regular local file")
        if os.fstat(fd).st_size == 0:
            os.write(fd, b"\0")
        if os.name == "nt":
            import msvcrt
            def acquire():
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            def release():
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            def acquire():
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            def release():
                fcntl.flock(fd, fcntl.LOCK_UN)
        deadline = time.monotonic() + timeout
        while True:
            try:
                acquire()
                acquired = True
                break
            except (BlockingIOError, PermissionError):
                if time.monotonic() >= deadline:
                    raise WorkbenchError("Saved requests are busy. Retry after the other writer finishes.") from None
                time.sleep(min(.025, max(0., deadline - time.monotonic())))
        yield
    finally:
        if acquired:
            release()
        os.close(fd)


@contextmanager
def locked_ledgers(*roots):
    # Stable ordering prevents deadlock when record touches two attempts.
    with ExitStack() as stack:
        for root in sorted({str(Path(root).resolve()) for root in roots}):
            stack.enter_context(ledger_file_lock(root))
        yield


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise WorkbenchError(f"{label} must be a finite number")
    return float(value)


def safe_json(data):
    try:
        return json.loads(data, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (ValueError, UnicodeDecodeError) as exc:
        raise WorkbenchError("Invalid JSON") from exc


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def validate_figure_name(value):
    """Normalize a display name without interpreting it as a path or plot title."""
    if not isinstance(value, str) or any(unicodedata.category(character) in {"Cc", "Cf", "Cs"} for character in value):
        raise WorkbenchError("Figure name must be text without control characters")
    name = value.strip()
    if not name or len(name) > MAX_FIGURE_NAME_LENGTH:
        raise WorkbenchError("Figure name must contain 1 to 120 characters")
    return name


def validate_figure_info(value):
    """Validate portable, bounded figure metadata independently of scientific QA."""
    if (not isinstance(value, dict) or set(value) - {"schema_version", "display_name", "updated_at"}
            or type(value.get("schema_version")) is not int or value["schema_version"] != 1):
        raise WorkbenchError("figure-info.json uses an unsupported format")
    info = {**value, "display_name": validate_figure_name(value.get("display_name"))}
    if "updated_at" in info and (not isinstance(info["updated_at"], str) or len(info["updated_at"]) > 64
                                 or any(unicodedata.category(character) in {"Cc", "Cf", "Cs"} for character in info["updated_at"])):
        raise WorkbenchError("Figure metadata needs a valid update timestamp")
    return info


def make_figure_info(name):
    return {"schema_version": 1, "display_name": validate_figure_name(name), "updated_at": timestamp()}


def read_figure_info(root):
    """Read one regular metadata file, bounding the actual opened file's bytes."""
    path = Path(root) / "figure-info.json"
    if path.is_symlink():
        raise WorkbenchError("figure-info.json must be a bounded regular local file")
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise WorkbenchError("figure-info.json must be a bounded regular local file") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_FIGURE_INFO_BYTES:
            raise WorkbenchError("figure-info.json must be a bounded regular local file")
        stream = os.fdopen(descriptor, "rb")
    except BaseException:
        os.close(descriptor)
        raise
    with stream:
        raw = stream.read(MAX_FIGURE_INFO_BYTES + 1)
    if len(raw) > MAX_FIGURE_INFO_BYTES:
        raise WorkbenchError("Figure metadata exceeds its size limit")
    return validate_figure_info(safe_json(raw))


def write_figure_info(root, name):
    """Persist only the display name, preserving SVG, data and version identities."""
    root = Path(root)
    info = make_figure_info(name)
    raw = (json.dumps(info, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with ledger_file_lock(root):
        read_figure_info(root)  # Refuse replacing malformed or non-regular metadata.
        path = root / "figure-info.json"
        temporary = root / (".figure-info-" + uuid.uuid4().hex + ".tmp")
        try:
            with temporary.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            if path.is_symlink():
                raise WorkbenchError("figure-info.json must be a bounded regular local file")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return info


def source_versions(input_info, version):
    """Check declared provenance without exposing or executing source contents."""
    checks = {}
    for field, hash_field in (("data_file", "input_sha256"), ("source_script", "source_script_sha256"), ("spec_file", "supplied_spec_sha256")):
        expected = input_info.get(hash_field) if field == "spec_file" else version.get(hash_field)
        location = input_info.get(field)
        check = {"available": False, "current": None}
        if isinstance(location, str) and isinstance(expected, str):
            path = Path(location).expanduser()
            try:
                if path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_FILE_BYTES:
                    actual = sha256(path.read_bytes())
                    check.update(available=True, current=actual == expected, expected_sha256=expected, actual_sha256=actual)
            except OSError:
                pass
        checks[field] = check
    for role, record in input_info.get("auxiliary_inputs", {}).items():
        location, expected = record["path"], record["sha256"]
        check = {"available": False, "current": None}
        path = Path(location).expanduser()
        try:
            if path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_FILE_BYTES:
                actual = sha256(path.read_bytes())
                check.update(available=True, current=actual == expected,
                             expected_sha256=expected, actual_sha256=actual)
        except OSError:
            pass
        checks["auxiliary_inputs:" + role] = check
    return checks


def element_matches(element, selector):
    """Intersect semantic filters; never infer observations from image positions."""
    keys = element.get("source_keys", [])
    if "role" in selector and element.get("role") != selector["role"]:
        return False
    if "spec_path" in selector and selector["spec_path"] not in element.get("spec_paths", []):
        return False
    if "category" in selector and not any(isinstance(key, dict) and any(key.get(name) == selector["category"] for name in ("category", "group")) for key in keys):
        return False
    if "source_key" in selector and not any(isinstance(key, dict) and all(name in key and json.dumps(key[name], sort_keys=True, allow_nan=False) == json.dumps(value, sort_keys=True, allow_nan=False) for name, value in selector["source_key"].items()) for key in keys):
        return False
    return True


def svg_length_mm(value):
    match = re.fullmatch(r"\s*([\d.+eE-]+)\s*(mm|cm|in|pt|px)?\s*", value or "")
    if not match:
        return None
    try:
        number = float(match.group(1))
    except ValueError:
        return None
    scale = {"mm": 1, "cm": 10, "in": 25.4, "pt": 25.4 / 72, "px": 25.4 / 96, None: 25.4 / 96}
    return number * scale[match.group(2)] if math.isfinite(number) and number > 0 else None


def read_svg(data):
    if b"<!ENTITY" in data.upper() or b"<!DOCTYPE" in data.upper():
        # Matplotlib writes a harmless SVG 1.1 DOCTYPE. Remove that declaration,
        # but reject internal subsets rather than attempting to resolve entities.
        if b"<!ENTITY" in data.upper() or re.search(br"<!DOCTYPE[^>]*\[", data, re.I):
            raise WorkbenchError("SVG entity declarations are unsupported")
        data = re.sub(br"<!DOCTYPE[^>]*>", b"", data, flags=re.I)
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise WorkbenchError("panel.svg is not valid SVG") from exc
    if root.tag.split("}")[-1] != "svg":
        raise WorkbenchError("panel.svg must contain an SVG root")
    raw = re.split(r"[\s,]+", root.attrib.get("viewBox", "").strip())
    try:
        box = [float(value) for value in raw]
    except ValueError as exc:
        raise WorkbenchError("SVG needs a numeric viewBox") from exc
    if len(box) != 4 or not all(math.isfinite(value) for value in box) or min(box[2:]) <= 0:
        raise WorkbenchError("SVG needs a positive finite viewBox")
    panel = {"width_mm": svg_length_mm(root.attrib.get("width")), "height_mm": svg_length_mm(root.attrib.get("height"))}
    return root, box, panel


def sanitized_svg(root):
    """Retain figure geometry and embedded raster marks, excluding active content."""
    def unsafe_css(value):
        if re.search(r"(?:javascript:|@import|expression\()", value, re.I):
            return True
        return any(not target.strip().strip("\"'").startswith("#") for target in re.findall(r"url\(\s*([^)]*)\)", value, re.I))

    allowed = {"svg", "g", "defs", "symbol", "marker", "path", "rect", "line", "circle", "ellipse", "polygon", "polyline", "text", "tspan", "use", "image", "clipPath", "mask", "pattern", "linearGradient", "radialGradient", "stop", "title", "desc", "style"}
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag.split("}")[-1] not in allowed:
                parent.remove(child)
        for key, value in list(parent.attrib.items()):
            local = key.split("}")[-1].lower()
            if local.startswith("on") or local in {"src", "base"}:
                del parent.attrib[key]
            elif local == "href" and not (value.startswith("#") or re.fullmatch(r"data:image/(?:png|jpeg);base64,[A-Za-z0-9+/=\s]+", value)):
                del parent.attrib[key]
            elif unsafe_css(value):
                del parent.attrib[key]
        if parent.tag.split("}")[-1] == "style" and unsafe_css(parent.text or ""):
            parent.text = ""
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


class FigureWorkbench:
    def __init__(self, figure_dir, compare_dir=None):
        self.root = Path(figure_dir).expanduser().resolve()
        if not self.root.is_dir():
            raise WorkbenchError("Figure directory does not exist")
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        self.comparison = FigureWorkbench(compare_dir) if compare_dir is not None else None
        self.state()  # Fail before listening when the essential figure is invalid.

    def figure_name(self, fallback=None):
        info = read_figure_info(self.root)
        if info is not None:
            return info["display_name"]
        return fallback if isinstance(fallback, str) and fallback.strip() else self.root.name

    def rename(self, name):
        return write_figure_info(self.root, name)

    def read_file(self, name, *, required=False):
        if name not in FILES:
            raise WorkbenchError("File is not available in this workbench")
        path = self.root / name
        if path.is_symlink():
            raise WorkbenchError(f"{name} must be a regular file inside the figure directory")
        if not path.exists():
            if required:
                raise WorkbenchError(f"{name} is required")
            return None
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            raise WorkbenchError(f"{name} is not a supported local figure file")
        return path.read_bytes()

    def available_files(self, svg_hash, receipt=None, *, bound=False):
        """Advertise exports from this render, leaving older formats on disk.

        A fresh SVG-only render can reuse a directory holding yesterday's PDF
        and PNG. Their existence is insufficient: current QA or the validated
        source handoff must declare their exact bytes alongside this SVG.
        Unbound legacy previews without either record remain downloadable.
        """
        present = {name for name in FILES if (self.root / name).is_file() and not (self.root / name).is_symlink()}
        hashes = {"panel.svg": svg_hash}
        qa_raw = self.read_file("qa.json")
        qa = safe_json(qa_raw) if qa_raw else None
        declarations = receipt["exports"] if receipt else {} if bound else None
        if qa_raw:
            if not isinstance(qa, dict) or qa.get("status") in {"failed", "in_progress"}:
                declarations = {}
            else:
                exports = qa.get("exports")
                if isinstance(exports, dict):
                    if isinstance(exports.get("svg"), dict) and exports["svg"].get("sha256") == svg_hash:
                        declarations = {"panel." + extension: record.get("sha256")
                                        for extension, record in exports.items()
                                        if extension in {"svg", "pdf", "png"} and isinstance(record, dict)}
                    elif not receipt:
                        declarations = {}
                elif not receipt:
                    declarations = {}
        for name in ("panel.pdf", "panel.png"):
            present_regular = name in present
            present.discard(name)
            if not present_regular:
                continue
            try:
                raw = self.read_file(name)
            except (WorkbenchError, OSError):
                continue
            if raw is not None:
                actual = sha256(raw)
                if declarations is None or declarations.get(name) == actual:
                    present.add(name)
                    hashes[name] = actual
        return sorted(present), hashes

    def read_export(self, name):
        """Return current advertised export bytes, with a final race check."""
        if name not in {"panel.svg", "panel.pdf", "panel.png"}:
            raise WorkbenchError("Choose a supported figure export")
        state = self.state()
        if name not in state["files"]:
            return None
        raw = self.read_file(name)
        return raw if raw is not None and sha256(raw) == state["export_hashes"].get(name) else None

    def ledger_bytes(self):
        path = self.root / "requests.json"
        if path.is_symlink():
            raise WorkbenchError("requests.json must be a regular local file")
        if not path.exists():
            return None
        if not path.is_file():
            raise WorkbenchError("requests.json must be a regular local file")
        if path.stat().st_size > MAX_FILE_BYTES:
            raise WorkbenchError("requests.json exceeds the workbench size limit")
        return path.read_bytes()

    def ledger_snapshot(self):
        raw = self.ledger_bytes()
        if raw is None:
            return raw, {"schema_version": 1, "requests": []}
        ledger = safe_json(raw)
        if not isinstance(ledger, dict) or ledger.get("schema_version") != 1 or not isinstance(ledger.get("requests"), list):
            raise WorkbenchError("requests.json uses an unsupported format")
        if "history" in ledger and (not isinstance(ledger["history"], list) or not all(isinstance(item, dict) for item in ledger["history"])):
            raise WorkbenchError("Request history must be a list of records")
        return raw, ledger

    def ledger(self):
        return self.ledger_snapshot()[1]

    def state(self):
        svg = self.read_file("panel.svg", required=True)
        svg_root, box, svg_panel = read_svg(svg)
        actual_hash = sha256(svg)
        raw_manifest = self.read_file("elements.json")
        manifest = safe_json(raw_manifest) if raw_manifest else None
        reason = "No element map is available. Select a region or leave a general note."
        valid = False
        map_bound = False
        elements = []
        version = {"figure_sha256": actual_hash}
        panel = svg_panel
        input_info = {}
        if isinstance(manifest, dict) and manifest.get("schema_version") == 1:
            declared_version = manifest.get("version") or {key: manifest.get(key) for key in ("figure_sha256", "spec_sha256", "input_sha256", "source_script_sha256", "resolved_colors_sha256") if manifest.get(key)}
            if not isinstance(declared_version, dict):
                declared_version = {}
            candidate = manifest.get("panel", {})
            try:
                if not isinstance(candidate, dict):
                    raise WorkbenchError("Element map panel must be an object")
                width = finite_number(candidate.get("width_mm"), "Panel width")
                height = finite_number(candidate.get("height_mm"), "Panel height")
                if min(width, height) <= 0:
                    raise WorkbenchError("Panel dimensions must be positive")
                candidate_panel = {"width_mm": width, "height_mm": height}
                dimensions_match = all(svg_panel[key] is None or abs(svg_panel[key] - candidate_panel[key]) < .05 for key in candidate_panel)
                valid = declared_version.get("figure_sha256") == actual_hash and dimensions_match
                ids = {node.attrib["id"] for node in svg_root.iter() if "id" in node.attrib}
                candidates = manifest.get("elements")
                if valid and isinstance(candidates, list):
                    seen = set()
                    for element in candidates:
                        if not isinstance(element, dict) or not isinstance(element.get("id"), str) or element["id"] not in ids or element["id"] in seen:
                            raise WorkbenchError("Element map contains missing or duplicate SVG IDs")
                        editable = element.get("editable", [])
                        if not isinstance(editable, (list, dict)) or not all(isinstance(name, str) for name in editable):
                            raise WorkbenchError("Element editable properties must be named strings")
                        if not isinstance(element.get("source_keys", []), list) or not all(isinstance(key, dict) for key in element.get("source_keys", [])):
                            raise WorkbenchError("Element source keys must be objects")
                        if not isinstance(element.get("spec_paths", []), list) or not all(isinstance(path, str) for path in element.get("spec_paths", [])):
                            raise WorkbenchError("Element specification paths must be strings")
                        seen.add(element["id"])
                        elements.append({**element, "label": str(element.get("label", element["id"])), "role": str(element.get("role", "element"))})
                    reason = "Select a mark, axis, label or guide to describe a change."
                    # Adopt dimensions and provenance only after the full map is
                    # validated. A stale map cannot define a new SVG's regions.
                    panel = candidate_panel
                    version.update({key: value for key, value in declared_version.items() if key in {"spec_sha256", "input_sha256", "source_script_sha256", "resolved_colors_sha256", "auxiliary_inputs_sha256"} and isinstance(value, str)})
                    input_info = normalize_inputs(manifest.get("input", {}), self.root)
                    version = bound_version(version, input_info)
                    map_bound = True
                    valid = bool(elements)
                    if not elements:
                        reason = "No selectable artists were registered. Source and figure bindings are available; use a region or general note."
                else:
                    valid = False
                    reason = "The element map belongs to a different export. Regenerate it for point selection; region and general notes remain available."
            except (WorkbenchError, HandoffError, TypeError):
                valid = False
                elements = []
                input_info = {}
                version = {"figure_sha256": actual_hash}
                panel = svg_panel
                reason = "The element map is incomplete. Use a region or general note and ask the Agent to regenerate the map."
        receipt = None
        receipt_error = None
        raw_receipt = self.read_file("handoff.json")
        if raw_receipt:
            try:
                receipt = validate_receipt(safe_json(raw_receipt), root=self.root,
                                           svg_hash=actual_hash, panel=svg_panel)
                if map_bound and any(version.get(key) != value for key, value in receipt["version"].items()
                                 if key != "auxiliary_inputs_sha256"):
                    raise HandoffError("Custom source receipt and element map versions disagree")
                if map_bound and input_info.get("auxiliary_inputs") and input_info.get("auxiliary_inputs") != receipt["input"].get("auxiliary_inputs"):
                    raise HandoffError("Custom source receipt and element map auxiliary inputs disagree")
                input_info = receipt["input"]
                version = bound_version({**version, **receipt["version"]}, input_info)
                panel = receipt["panel"]
            except (HandoffError, WorkbenchError, OSError) as exc:
                receipt_error = str(exc)
                receipt = None
                valid = False
                map_bound = False
                elements = []
                input_info = {}
                version = {"figure_sha256": actual_hash}
                panel = svg_panel
                reason = "The custom source handoff is incomplete or stale. Regenerate it from the final source and exports."
        provenance_valid = bool(receipt) or (map_bound and all(isinstance(input_info.get(field), str) for field in ("data_file", "spec_file", "source_script"))
                           and all(isinstance(version.get(key), str) for key in ("input_sha256", "source_script_sha256", "spec_sha256"))
                           and isinstance(input_info.get("supplied_spec_sha256"), str))
        if panel.get("width_mm") is None or panel.get("height_mm") is None:
            raise WorkbenchError("SVG physical width and height are required for millimetre coordinates")
        settings_bytes = self.read_file("settings.json")
        settings = safe_json(settings_bytes) if settings_bytes else {}
        settings_input = settings.get("input", {}) if isinstance(settings, dict) else {}
        track = settings.get("track", settings_input.get("track", "") if isinstance(settings_input, dict) else "") if isinstance(settings, dict) else ""
        if not track and receipt:
            track = receipt.get("track", "")
        if not track and valid and isinstance(manifest, dict):
            track = manifest.get("track", "")
        ledger = self.ledger()
        requests = []
        for item in ledger["requests"]:
            if isinstance(item, dict):
                requests.append({**item, "current_version": item.get("version") == version})
        checks = source_versions(input_info, version)
        if "resolved_colors_sha256" in version:
            colors = settings.get("resolved_colors") if isinstance(settings, dict) else None
            check = {"available": isinstance(colors, dict), "current": None}
            if isinstance(colors, dict):
                actual = sha256(json.dumps(colors, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")).encode())
                check.update(current=actual == version["resolved_colors_sha256"], expected_sha256=version["resolved_colors_sha256"], actual_sha256=actual)
            checks["resolved_colors"] = check
        source_current = False if receipt_error or any(check["current"] is False for check in checks.values()) else True if all(check["current"] is True for check in checks.values()) else None
        comparison = None
        if self.comparison:
            previous = self.comparison.state()
            comparison = {key: previous[key] for key in ("figure_name", "version", "panel", "view_box")}
        files, export_hashes = self.available_files(actual_hash, receipt, bound=provenance_valid or bool(raw_receipt))
        return {"schema_version": 1, "figure_name": self.figure_name(), "track": track, "version": version, "input": input_info, "source_versions": checks, "source_current": source_current, "panel": panel, "view_box": box, "manifest_valid": valid, "provenance_valid": provenance_valid, "handoff_error": receipt_error, "selection_message": reason, "elements": elements, "requests": requests, "history": ledger.get("history", []), "comparison": comparison, "files": files, "export_hashes": export_hashes, "token": self.token}

    def validate_region(self, region, panel):
        if not isinstance(region, dict) or set(region) != {"x", "y", "width", "height"}:
            raise WorkbenchError("Region requires x, y, width and height in millimetres")
        values = {key: finite_number(value, f"Region {key}") for key, value in region.items()}
        if values["x"] < 0 or values["y"] < 0 or min(values["width"], values["height"]) <= 0 or values["x"] + values["width"] > panel["width_mm"] + 1e-6 or values["y"] + values["height"] > panel["height_mm"] + 1e-6:
            raise WorkbenchError("Region must be inside the full figure canvas")
        return values

    def _replace_ledger_bytes(self, raw):
        """Publish/rollback while the caller holds this attempt's file lock."""
        # Only this separate file changes. Figure exports and source data are read-only.
        path = self.root / "requests.json"
        if path.is_symlink():
            raise WorkbenchError("requests.json must be a regular local file")
        if raw is None:
            path.unlink(missing_ok=True)
            return
        if len(raw) > MAX_FILE_BYTES:
            raise WorkbenchError("Request ledger exceeds the workbench size limit")
        temporary = self.root / f".requests-{uuid.uuid4().hex}.tmp"
        try:
            with temporary.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    def ledger_serialized(self, ledger):
        serialized = json.dumps(ledger, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if len(serialized.encode("utf-8")) > MAX_FILE_BYTES:
            raise WorkbenchError("Request ledger exceeds the workbench size limit")
        return serialized.encode("utf-8")

    def write_ledger(self, ledger, *, expected_bytes=_ANY_LEDGER, expected_version=None):
        serialized = self.ledger_serialized(ledger)
        with ledger_file_lock(self.root):
            if expected_version is not None:
                self.current_state(expected_version)
            if expected_bytes is not _ANY_LEDGER and self.ledger_bytes() != expected_bytes:
                raise WorkbenchError("Saved requests changed while saving. Reload the workbench before retrying.")
            self._replace_ledger_bytes(serialized)

    def validate_anchor(self, anchor, panel):
        if not isinstance(anchor, dict) or set(anchor) != {"x", "y"}:
            raise WorkbenchError("Annotation anchor requires x and y in millimetres")
        values = {key: finite_number(value, f"Annotation anchor {key}") for key, value in anchor.items()}
        if not 0 <= values["x"] <= panel["width_mm"] or not 0 <= values["y"] <= panel["height_mm"]:
            raise WorkbenchError("Annotation anchor must be inside the full figure canvas")
        return values

    def current_state(self, version):
        state = self.state()
        if version != state["version"]:
            raise WorkbenchError("This figure has changed. Reload it before saving a request.")
        if state["source_current"] is False:
            raise WorkbenchError("The figure source has changed. Render a fresh attempt before saving requests.")
        return state

    def annotation_numbers(self, ledger, version):
        # Undone/applied requests retain their number: labels identify a saved
        # opinion permanently within the figure version, not its queue status.
        return {item["annotation_number"] for item in ledger["requests"]
                if isinstance(item, dict) and item.get("version") == version
                and type(item.get("annotation_number")) is int}

    def prepare_request(self, payload, state, used_numbers):
        """Validate and construct one item without changing any saved records."""
        if not isinstance(payload, dict):
            raise WorkbenchError("Request must be an object")
        allowed = {"version", "element_id", "element_ids", "selector", "spec_path", "region_mm", "property", "value", "instruction", "annotation_number", "anchor_mm"}
        if set(payload) - allowed:
            raise WorkbenchError("Request contains unsupported fields")
        if payload.get("version") != state["version"]:
            raise WorkbenchError("This figure has changed. Reload it before saving a request.")
        number = payload.get("annotation_number")
        if "annotation_number" in payload:
            if type(number) is not int or not 1 <= number <= 1000000:
                raise WorkbenchError("Annotation number must be an integer from 1 to 1000000")
            if number in used_numbers:
                raise WorkbenchError("Annotation number is already used in this figure version")
        anchor = self.validate_anchor(payload["anchor_mm"], state["panel"]) if "anchor_mm" in payload else None
        instruction = payload.get("instruction", "")
        if not isinstance(instruction, str) or not instruction.strip() or len(instruction) > 8000:
            raise WorkbenchError("Describe the requested change in 1 to 8000 characters")
        element_id = payload.get("element_id")
        ids = payload.get("element_ids")
        selector = payload.get("selector")
        region = payload.get("region_mm")
        if sum(value is not None for value in (element_id, ids, selector)) > 1:
            raise WorkbenchError("Choose element_id, element_ids or a semantic selector")
        if selector is not None:
            if not isinstance(selector, dict) or not selector or set(selector) - {"role", "category", "spec_path", "source_key"}:
                raise WorkbenchError("Unsupported semantic selector")
            if any(not isinstance(value, str) or not value for key, value in selector.items() if key != "source_key") or ("source_key" in selector and (not isinstance(selector["source_key"], dict) or not selector["source_key"])):
                raise WorkbenchError("Semantic selector values must name real mapped identities")
            ids = [element["id"] for element in state["elements"] if element_matches(element, selector)]
            if not ids:
                raise WorkbenchError("Semantic selector matches no mapped elements")
        elif element_id is not None:
            ids = [element_id]
        else:
            ids = [] if ids is None else ids
        if not isinstance(ids, list) or len(ids) > 2000 or any(not isinstance(value, str) or not value for value in ids) or len(set(ids)) != len(ids):
            raise WorkbenchError("Element IDs must be a unique list of mapped IDs")
        if ids and region:
            raise WorkbenchError("Choose an element or a region, not both")
        selected = [element for element in state["elements"] if element["id"] in ids]
        if ids and (not state["manifest_valid"] or len(selected) != len(ids)):
            raise WorkbenchError("Selected element is unavailable in this figure version")
        element = selected[0] if len(selected) == 1 else None
        spec_path = payload.get("spec_path")
        if spec_path is not None and (not isinstance(spec_path, str) or not selected or not all(spec_path in entry.get("spec_paths", []) for entry in selected)):
            raise WorkbenchError("Specification path must belong to every selected element")
        prop = payload.get("property")
        value = payload.get("value")
        if prop is not None:
            if not selected or not isinstance(prop, str) or not all(prop in entry.get("editable", []) for entry in selected):
                raise WorkbenchError("This property is not available for the selected element")
            if not isinstance(value, (str, int, float, bool, list, dict)) or value is None:
                raise WorkbenchError("A property change needs a value")
            # Bound values are instructions, never evaluated or executed.
            if len(json.dumps(value, allow_nan=False)) > 4000:
                raise WorkbenchError("Property value is too long")
        elif value is not None:
            raise WorkbenchError("A value needs a supported property")
        item = {"id": str(uuid.uuid4()), "created_at": timestamp(), "status": "pending", "version": state["version"], "input": state["input"], "element_id": element["id"] if element else None, "element_ids": [entry["id"] for entry in selected], "instruction": instruction.strip()}
        if selected:
            item["elements"] = [{key: entry.get(key) for key in ("id", "role", "label", "source_keys", "spec_paths", "editable")} for entry in selected]
        if element:
            item["element"] = {key: element.get(key) for key in ("id", "role", "label", "source_keys", "spec_paths", "editable")}
        if selector is not None:
            item["selector"] = selector
        if spec_path is not None:
            item["spec_path"] = spec_path
        if region is not None:
            item["region_mm"] = self.validate_region(region, state["panel"])
            item["coordinate_origin"] = "top-left of full canvas"
        if prop is not None:
            item.update(property=prop, value=value)
        if "annotation_number" in payload:
            item["annotation_number"] = number
            used_numbers.add(number)
        if anchor is not None:
            item["anchor_mm"] = anchor
            item["coordinate_origin"] = "top-left of full canvas"
        return item

    def publish_requests(self, ledger, items, state, previous_bytes):
        # Check the complete figure/source snapshot again after every item has
        # been validated. Nothing reaches requests.json before this point.
        self.current_state(state["version"])
        if self.ledger_bytes() != previous_bytes:
            raise WorkbenchError("Saved requests changed while saving. Reload the workbench before retrying.")
        ledger["requests"].extend(items)
        ledger.update(schema_version=1, version=state["version"], updated_at=timestamp())
        self.write_ledger(ledger, expected_bytes=previous_bytes, expected_version=state["version"])

    def change_batch(self, payload):
        if not isinstance(payload, dict) or set(payload) != {"version", "requests"}:
            raise WorkbenchError("Batch requires only version and requests")
        requests = payload["requests"]
        if not isinstance(requests, list) or not 1 <= len(requests) <= 100:
            raise WorkbenchError("Batch requires 1 to 100 independent requests")
        with self.lock:
            state = self.current_state(payload["version"])
            previous_bytes, ledger = self.ledger_snapshot()
            used_numbers = self.annotation_numbers(ledger, state["version"])
            items = []
            for index, request in enumerate(requests, start=1):
                try:
                    items.append(self.prepare_request(request, state, used_numbers))
                except WorkbenchError as exc:
                    raise WorkbenchError(f"Request {index}: {exc}") from exc
            self.publish_requests(ledger, items, state, previous_bytes)
            return {"requests": items, "state": self.state()}

    def change(self, payload, *, undo=False):
        if not isinstance(payload, dict):
            raise WorkbenchError("Request must be an object")
        if undo and set(payload) - {"version", "request_id"}:
            raise WorkbenchError("Request contains unsupported fields")
        with self.lock:
            state = self.current_state(payload.get("version"))
            previous_bytes, ledger = self.ledger_snapshot()
            if undo:
                request_id = payload.get("request_id")
                item = next((item for item in ledger["requests"] if isinstance(item, dict) and item.get("id") == request_id), None)
                if item is None or item.get("status") != "pending":
                    raise WorkbenchError("Only a pending request can be undone")
                if item.get("version") != state["version"]:
                    raise WorkbenchError("This request belongs to an older figure version")
                item.update(status="undone", undone_at=timestamp())
                items = []
            else:
                item = self.prepare_request(payload, state, self.annotation_numbers(ledger, state["version"]))
                items = [item]
            self.publish_requests(ledger, items, state, previous_bytes)
            return {"request": item, "state": self.state()}


def discover_attempts(service):
    """Find EasyViz outputs within this project without following links.

    The library accepts existing source-bound EasyViz outputs. Arbitrary SVG,
    PDF and PNG files cannot become editable figures just by appearing here.
    Walking is bounded so a large data project cannot stall the local page.
    """
    checked = 0
    for root, directories, names in os.walk(service.project, followlinks=False):
        directory = Path(root)
        depth = len(directory.relative_to(service.project).parts)
        directories[:] = sorted(name for name in directories
                                if not name.startswith(".") and name not in {"node_modules", "__pycache__", "accepted-snapshot"}
                                and not (directory / name).is_symlink()) if depth < 6 else []
        checked += 1
        if checked > 1000:
            break
        if "panel.svg" not in names or not {"elements.json", "handoff.json"}.intersection(names):
            continue
        try:
            app = FigureWorkbench(directory)
            state = app.state()
            if not state["provenance_valid"]:
                continue
            service._sources_in_scope(state)
            service.register_attempt(directory)
        except (ValueError, OSError):
            continue


def library_state(service):
    result = service.list_attempts()
    result.update(project_id=service.project_id, project_name=service.project.name,
                  token=service.token, empty=not any(not item.get("unavailable") for item in result["attempts"]))
    return result


def workbench_state(service):
    if service.app is not None:
        return service.state()
    return {"empty": True, "project_id": service.project_id, "project_name": service.project.name,
            "token": service.token, "requests": [], "history": [], "elements": []}


def create_server(figure_dir=None, port=0, compare_dir=None, project_dir=None):
    if figure_dir is None and project_dir is None:
        raise WorkbenchError("Choose a project directory for the figure library")
    if compare_dir is not None and figure_dir is None:
        raise WorkbenchError("Choose a figure before adding a comparison attempt")
    app = FigureWorkbench(figure_dir, compare_dir=compare_dir) if figure_dir is not None else None
    from figure_service import FigureService
    service = FigureService(project_dir or app.root.parent)
    if app is not None:
        attempt = service.register_attempt(app.root)
        if app.comparison:
            service.register_attempt(app.comparison.root)
        # Keep existing callers' session until an explicit attempt switch.
        service.app = app
        service.token = app.token
        service.current_attempt_id = attempt["id"]
        service.note_reviewed_attempt(attempt["id"])
    else:
        discover_attempts(service)
        listed = service.list_attempts()
        available = [item["id"] for item in listed["attempts"] if not item.get("unavailable")]
        selected = listed["review_attempt_id"] if listed["review_attempt_id"] in available else next(iter(available), None)
        if selected:
            service.switch_attempt(selected)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def reply(self, code, body, content_type="application/json; charset=utf-8", *, attachment=None):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
            elif isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; connect-src 'self'")
            if attachment:
                self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
            self.end_headers()
            self.wfile.write(body)

        def permitted(self, *, mutation=False):
            origin = f"http://127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != origin.removeprefix("http://"):
                self.reply(403, {"error": "Open the workbench at its displayed 127.0.0.1 address"})
                return False
            supplied_origin = self.headers.get("Origin")
            if (mutation and supplied_origin != origin) or (supplied_origin is not None and supplied_origin != origin):
                self.reply(403, {"error": "Requests must come from this local workbench"})
                return False
            if mutation and not secrets.compare_digest(self.headers.get("X-EasyViz-Token", ""), service.token):
                self.reply(403, {"error": "Reload the workbench to obtain a valid session"})
                return False
            return True

        def do_GET(self):
            app = service.app
            if not self.permitted():
                return
            path = urlsplit(self.path).path
            try:
                if path == "/api/state":
                    self.reply(200, workbench_state(service))
                elif path == "/api/library":
                    self.reply(200, library_state(service))
                elif path == "/api/agent":
                    self.reply(200, service.agent_status())
                elif path == "/api/capabilities":
                    self.reply(200, service.capabilities())
                elif path == "/api/jobs":
                    self.reply(200, service.list_jobs())
                elif re.fullmatch(r"/api/jobs/job-[0-9a-f]{32}", path):
                    self.reply(200, service.get_job(path.rsplit("/", 1)[1]))
                elif path == "/api/attempts":
                    self.reply(200, service.list_attempts())
                elif re.fullmatch(r"/api/attempts/attempt-[0-9a-f]{16}/(?:preview\.svg|files/panel\.(?:svg|pdf|png))", path):
                    parts = path.split("/")
                    preview_app = service.attempt_app(parts[3])
                    if parts[4] == "preview.svg":
                        raw = preview_app.read_file("panel.svg", required=True)
                        requested_hash = parse_qs(urlsplit(self.path).query).get("v", [None])[0]
                        if requested_hash is not None and requested_hash != sha256(raw):
                            self.reply(409, {"error": "This figure has changed. Reload the preview."})
                            return
                        root, _, _ = read_svg(raw)
                        self.reply(200, sanitized_svg(root), "image/svg+xml")
                    else:
                        name = parts[5]
                        raw = preview_app.read_export(name)
                        if raw is None:
                            self.reply(404, {"error": "This export is unavailable for the current figure version"})
                            return
                        content_type = {"svg": "image/svg+xml", "pdf": "application/pdf", "png": "image/png"}[name.rsplit(".", 1)[1]]
                        self.reply(200, raw, content_type, attachment=name)
                elif path in {"/api/preview.svg", "/api/compare.svg"}:
                    if app is None:
                        self.reply(404, {"error": "Open an EasyViz figure from the library first"})
                        return
                    preview_app = app if path == "/api/preview.svg" else app.comparison
                    if preview_app is None:
                        self.reply(404, {"error": "No previous attempt was supplied"})
                        return
                    svg_bytes = preview_app.read_file("panel.svg", required=True)
                    requested_hash = parse_qs(urlsplit(self.path).query).get("v", [None])[0]
                    if requested_hash is not None and requested_hash != sha256(svg_bytes):
                        self.reply(409, {"error": "This figure has changed. Reload the preview."})
                        return
                    root, _, _ = read_svg(svg_bytes)
                    self.reply(200, sanitized_svg(root), "image/svg+xml")
                elif path == "/logo.svg":
                    self.reply(200, LOGO.read_bytes(), "image/svg+xml")
                elif path in {"/", "/workbench.js", "/workbench.css"}:
                    name = {"/": "index.html", "/workbench.js": "workbench.js", "/workbench.css": "workbench.css"}[path]
                    content_type = {"index.html": "text/html; charset=utf-8", "workbench.js": "text/javascript; charset=utf-8", "workbench.css": "text/css; charset=utf-8"}[name]
                    body = (STATIC / name).read_bytes()
                    if name == "index.html":
                        # Browsers keep favicons separately from their normal resource cache.
                        body = body.replace(b"__LOGO_VERSION__", sha256(LOGO.read_bytes()).encode("ascii"))
                    self.reply(200, body, content_type)
                elif path.startswith("/files/") and path.removeprefix("/files/") in FILES:
                    if app is None:
                        self.reply(404, {"error": "Open a figure first"})
                        return
                    name = path.removeprefix("/files/")
                    body = app.read_export(name) if name in {"panel.svg", "panel.pdf", "panel.png"} else app.read_file(name)
                    if body is None:
                        self.reply(404, {"error": "This export is unavailable"})
                    else:
                        content_type = {"svg": "image/svg+xml", "pdf": "application/pdf", "png": "image/png", "json": "application/json"}[name.rsplit(".", 1)[1]]
                        self.reply(200, body, content_type, attachment=name)
                elif path == "/files/requests.json":
                    if app is None:
                        self.reply(404, {"error": "Open a figure first"})
                        return
                    self.reply(200, app.ledger(), attachment="requests.json")
                elif path == "/files/panel.ev":
                    if app is None:
                        self.reply(404, {"error": "Open a figure first"})
                        return
                    from ev_document import export_document
                    with tempfile.TemporaryDirectory(dir=service.storage, prefix="export-") as temporary:
                        document = export_document(app.root, Path(temporary) / "panel.ev")
                        self.reply(200, document.read_bytes(), "application/octet-stream", attachment="panel.ev")
                else:
                    self.reply(404, {"error": "Not found"})
            except (ValueError, OSError) as exc:
                self.reply(400, {"error": str(exc)})

        def do_POST(self):
            app = service.app
            if not self.permitted(mutation=True):
                return
            path = urlsplit(self.path).path
            if path == "/api/documents/import":
                self.import_document()
                return
            if path not in {"/api/requests", "/api/requests/batch", "/api/undo", "/api/jobs", "/api/agent/jobs", "/api/agent/configure", "/api/library/refresh", "/api/attempts/switch", "/api/attempts/rename", "/api/attempts/accept", "/api/attempts/restore"} and not re.fullmatch(r"/api/jobs/job-[0-9a-f]{32}/cancel", path):
                self.reply(404, {"error": "Not found"})
                return
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip() != "application/json":
                self.reply(415, {"error": "Send application/json"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > (MAX_BATCH_BYTES if path == "/api/requests/batch" else MAX_REQUEST_BYTES):
                    self.reply(413, {"error": "Request body is missing or too large"})
                    return
                payload = safe_json(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise WorkbenchError("Request must be an object")
                if path == "/api/library/refresh":
                    if payload:
                        raise WorkbenchError("Library refresh needs an empty request object")
                    discover_attempts(service)
                    result = library_state(service)
                elif path == "/api/agent/configure":
                    if set(payload) - {"backend", "enabled"}:
                        raise WorkbenchError("Choose an available Agent backend")
                    result = service.configure_agent(payload.get("backend", "codex"), enabled=payload.get("enabled", True))
                elif path == "/api/agent/jobs":
                    if set(payload) - {"version", "request_ids", "attempt_id"}:
                        raise WorkbenchError("Agent job requires a source version and optional request IDs")
                    result = service.submit_agent_job(payload.get("version"), payload.get("request_ids"), payload.get("attempt_id"))
                elif path == "/api/jobs":
                    if set(payload) - {"version", "request_ids"}:
                        raise WorkbenchError("Job requires only version and optional request_ids")
                    result = service.submit_job(payload.get("version"), payload.get("request_ids"))
                elif path.endswith("/cancel"):
                    if payload:
                        raise WorkbenchError("Cancellation needs an empty request object")
                    result = service.cancel_job(path.split("/")[3])
                elif path == "/api/attempts/switch":
                    if set(payload) - {"attempt_id", "compare_attempt_id"}:
                        raise WorkbenchError("Switch requires registered attempt IDs")
                    result = service.switch_attempt(payload.get("attempt_id"), payload.get("compare_attempt_id"))
                    self.server.app = service.app
                elif path == "/api/attempts/rename":
                    if set(payload) - {"attempt_id", "name"} or "name" not in payload:
                        raise WorkbenchError("Rename requires a figure name and optional registered attempt ID")
                    result = service.rename_attempt(payload["name"], payload.get("attempt_id"))
                elif path == "/api/attempts/accept":
                    if set(payload) - {"attempt_id", "validation"}:
                        raise WorkbenchError("Acceptance requires a validation note")
                    result = service.accept(payload.get("validation"), payload.get("attempt_id"))
                elif path == "/api/attempts/restore":
                    if set(payload) - {"attempt_id"}:
                        raise WorkbenchError("Restore requires a registered attempt ID")
                    result = service.restore(payload.get("attempt_id"))
                else:
                    if app is None:
                        raise WorkbenchError("Open a figure before saving edit requests")
                    result = service.save_requests(payload) if path == "/api/requests/batch" else app.change(payload, undo=path == "/api/undo")
                    result["state"] = service.state()
                self.reply(200, result)
            except (WorkbenchError, OSError, ValueError, TypeError) as exc:
                self.reply(409 if "changed" in str(exc) else 400, {"error": str(exc)})

        def import_document(self):
            """Accept one validated .ev archive; never arbitrary file paths."""
            from ev_document import import_document, MAX_DOCUMENT_BYTES
            try:
                name = parse_qs(urlsplit(self.path).query).get("name", [""])[0]
                if Path(name).name != name or not name.lower().endswith(".ev"):
                    raise WorkbenchError("Choose an EasyViz .ev project file")
                if self.headers.get("Content-Type", "").split(";", 1)[0].strip() != "application/octet-stream":
                    self.reply(415, {"error": "Upload the .ev file as application/octet-stream"})
                    return
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_DOCUMENT_BYTES:
                    self.reply(413, {"error": "The .ev file is empty or exceeds the 64 MiB limit"})
                    return
                with tempfile.TemporaryDirectory(dir=service.storage, prefix="upload-") as temporary:
                    document = Path(temporary) / "import.ev"
                    remaining = length
                    with document.open("xb") as stream:
                        while remaining:
                            block = self.rfile.read(min(1024 * 1024, remaining))
                            if not block:
                                raise WorkbenchError("The .ev upload was interrupted")
                            stream.write(block)
                            remaining -= len(block)
                    target = import_document(document, service.project)
                attempt = service.register_attempt(target)
                result = service.switch_attempt(attempt["id"])
                self.server.app = service.app
                result["attempt"] = attempt
                self.reply(200, result)
            except (OSError, ValueError, TypeError) as exc:
                self.reply(400, {"error": str(exc)})

    class WorkbenchServer(ThreadingHTTPServer):
        def server_close(self):
            service.close()
            endpoint = service.storage / "workbench.json"
            try:
                if not endpoint.is_symlink() and safe_json(endpoint.read_bytes()).get("token") == service.token:
                    endpoint.unlink()
            except (OSError, ValueError, AttributeError):
                pass
            super().server_close()

    server = WorkbenchServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.app = service.app
    server.service = service
    return server


def existing_workbench(project_dir):
    """Reuse only a live instance whose project and session both match."""
    project = Path(project_dir).expanduser().resolve()
    endpoint = project / ".easyviz-service/workbench.json"
    try:
        if endpoint.is_symlink() or endpoint.stat().st_size > 4096:
            return None
        value = safe_json(endpoint.read_bytes())
        port = value.get("port")
        if isinstance(port, bool) or not isinstance(port, int) or not 0 < port <= 65535:
            return None
        url = f"http://127.0.0.1:{port}/"
        with urlopen(url + "api/library", timeout=1) as response:
            data = safe_json(response.read(MAX_REQUEST_BYTES))
        expected = "project-" + sha256(str(project).encode())[:16]
        if data.get("project_id") == expected and secrets.compare_digest(str(data.get("token", "")), str(value.get("token", "invalid"))):
            return url
    except (OSError, ValueError, AttributeError):
        pass
    return None


def main(argv=None, *, launch=False):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figure-dir", type=Path, help="Optional existing EasyViz attempt containing panel.svg")
    parser.add_argument("--port", type=int, default=0, help="Local port; 0 selects an available port")
    parser.add_argument("--compare-dir", type=Path, help="Previous attempt for a read-only side-by-side preview")
    parser.add_argument("--project-dir", type=Path, help="Scope containing attempts and inputs; defaults to the figure parent or current directory")
    parser.add_argument("--open", dest="open_browser", action="store_true", default=launch, help="Open the workbench in a browser")
    parser.add_argument("--no-open", dest="open_browser", action="store_false", help="Print the local address without opening a browser")
    args = parser.parse_args(argv)
    if args.project_dir is None and args.figure_dir is None:
        args.project_dir = Path.cwd()
    if not 0 <= args.port <= 65535:
        parser.error("Port must be between 0 and 65535")
    try:
        project = args.project_dir or args.figure_dir.expanduser().resolve().parent
        existing = existing_workbench(project) if args.figure_dir is None and args.compare_dir is None else None
        if existing:
            print(f"EasyViz workbench: {existing}", flush=True)
            if args.open_browser:
                webbrowser.open(existing)
            return
        server = create_server(args.figure_dir, args.port, args.compare_dir, args.project_dir)
        from figure_service import _atomic_json
        _atomic_json(server.service.storage / "workbench.json", {
            "port": server.server_port, "project_id": server.service.project_id,
            "token": server.service.token, "pid": os.getpid()})
    except (WorkbenchError, OSError) as exc:
        parser.exit(2, f"Cannot open figure review: {exc}\n")
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"EasyViz workbench: {url}", flush=True)
    print(f"Project: {server.service.project}\nPress Ctrl+C to close.", flush=True)
    if args.open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
