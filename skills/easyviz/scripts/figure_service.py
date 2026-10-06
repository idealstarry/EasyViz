#!/usr/bin/env python3
"""Project-scoped figure operations shared by the workbench, CLI and optional MCP.

Core previews use the installed renderer. Explicit Agent submissions use one
configured bounded local worker and retain original request/source identities.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
from pathlib import Path
import re
import secrets
import signal
import subprocess
import sys
import threading
import time
import uuid
import agent_dispatch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figure_workbench import (FigureWorkbench, WorkbenchError, ledger_file_lock,
                              make_figure_info, read_figure_info, safe_json, sha256, timestamp,
                              workbench_state, write_figure_info, MAX_FILE_BYTES)

MAX_JOBS = 32
MAX_ATTEMPTS = 100
RENDER_TIMEOUT_SECONDS = 120
ACTIVE_STATUSES = {"queued", "running"}
SESSION_LEASE_SECONDS = 300
MAX_SESSION_LEASE_SECONDS = 3600
AUTOMATIC_PROPERTIES = ("color", "facecolor", "edgecolor", "alpha", "linewidth",
                        "line_width_pt", "linestyle")
CORE_HELPERS = {"legend_layout.py", "figure_profile.py", "auto_layout.py", "annotation_review.py",
                "figure_elements.py", "panel_readability.py", "observation_clipping.py", "analysis_result.py"}


def _helpers():
    # Delayed import keeps figure_workbench -> figure_service free of a cycle.
    import apply_figure_requests
    return apply_figure_requests


def _atomic_json(path: Path, value):
    """Publish a bounded regular metadata file with one atomic replacement."""
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()
    if len(raw) > MAX_FILE_BYTES or path.is_symlink():
        raise WorkbenchError("Service metadata must be a bounded regular file")
    temporary = path.with_name(path.name + "." + secrets.token_hex(8) + ".tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(raw)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _refresh_document(target, *, required=False, warning_message=None):
    """Package actual exports, then keep a committed receipt visible on failure.

    Required calls happen before request-history publication. Later refreshes
    cannot undo an already committed outcome and report a document warning.
    """
    target = Path(target)
    try:
        from ev_document import export_document
        path = export_document(target)
        status = {"status": "ready", "file": path.name, "format": "ev", "canvas": "svg"}
        _atomic_json(target / "document-status.json", status)
        return None
    except (ImportError, OSError, ValueError, WorkbenchError) as exc:
        if required:
            raise WorkbenchError("Agent result requires a valid editable .ev document: " + str(exc)[:1000]) from exc
        message = warning_message or "The figure outcome was recorded, but its editable document needs to be exported again."
        try:
            _atomic_json(target / "document-status.json", {"status": "warning", "message": message,
                                                           "reason": str(exc)[:1000]})
        except (OSError, WorkbenchError):
            pass
        return message


class FigureService:
    """Small durable registry with one cancellable core-render job per project.

    Registry locks are shared by CLI, HTTP and MCP processes. A separate kernel
    lock stays held for the entire job, including its request-history commit.
    Completed outputs are registered only after export QA and source checks.
    """

    def __init__(self, project_dir, figure_dir=None, compare_dir=None, *, render_timeout=RENDER_TIMEOUT_SECONDS):
        self.project = Path(project_dir).expanduser().resolve()
        if not self.project.is_dir():
            raise WorkbenchError("Project scope must be an existing local directory")
        if isinstance(render_timeout, bool) or not isinstance(render_timeout, (int, float)) or not 0 < render_timeout <= RENDER_TIMEOUT_SECONDS:
            raise WorkbenchError("Render timeout must be positive and at most 120 seconds")
        self.render_timeout = float(render_timeout)
        self.project_id = "project-" + sha256(str(self.project).encode())[:16]
        self.storage = self.project / ".easyviz-service"
        if self.storage.is_symlink():
            raise WorkbenchError("Service storage must not be a symlink")
        self.storage.mkdir(exist_ok=True)
        self.run_lock_dir = self.storage / "active"
        if self.run_lock_dir.is_symlink():
            raise WorkbenchError("Service job lock must not be a symlink")
        self.run_lock_dir.mkdir(exist_ok=True)
        self.registry_path = self.storage / "registry.json"
        self.lock = threading.RLock()
        self.current_attempt_id = None
        self.app = None
        self.token = secrets.token_urlsafe(32)
        self._threads = {}
        self._closed = False
        with self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            _atomic_json(self.registry_path, registry)
        self._recover_abandoned_jobs()
        if figure_dir is not None:
            initial = self.register_attempt(figure_dir)
            previous = self.register_attempt(compare_dir)["id"] if compare_dir is not None else None
            self.switch_attempt(initial["id"], previous, publish_review=False)

    def _read_registry(self):
        if not self.registry_path.exists():
            return {"schema_version": 1, "project_id": self.project_id, "attempts": {}, "jobs": []}
        raw = _helpers().read_regular(self.registry_path)
        registry = safe_json(raw)
        if (not isinstance(registry, dict) or registry.get("schema_version") != 1
                or registry.get("project_id") != self.project_id
                or not isinstance(registry.get("attempts"), dict) or len(registry["attempts"]) > MAX_ATTEMPTS
                or not isinstance(registry.get("jobs"), list) or len(registry["jobs"]) > MAX_JOBS):
            raise WorkbenchError("Unsupported or oversized figure-service registry")
        return registry

    def _scoped_path(self, location, *, directory=False):
        if not isinstance(location, (str, Path)) or ".." in Path(location).parts:
            raise WorkbenchError("Registered paths must not contain parent traversal")
        path = Path(location).expanduser()
        if not path.is_absolute():
            path = self.project / path
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise WorkbenchError("Registered paths and their ancestors must not be symlinks")
        path = path.resolve()
        if not path.is_relative_to(self.project) or (directory and not path.is_dir()):
            raise WorkbenchError("Attempt or source is outside the explicit project scope")
        return path

    def _sources_in_scope(self, state):
        info = state["input"]
        for field in ("data_file", "spec_file"):
            if field in info:
                self._scoped_path(info[field])
        source = info.get("source_script")
        installed = Path(__file__).with_name("render.py").resolve()
        if source and Path(source).resolve() != installed:
            self._scoped_path(source)
        for role, record in info.get("auxiliary_inputs", {}).items():
            # Installed runtime helpers are part of the explicitly selected
            # trusted core, not arbitrary source files outside this project.
            name = role.removeprefix("helper:")
            runtime = Path(__file__).with_name(name).resolve() if role.startswith("helper:") and name in CORE_HELPERS else None
            if (runtime is not None and runtime.suffix == ".py" and runtime.is_file()
                    and Path(record["path"]).resolve() == runtime
                    and record["sha256"] == sha256(runtime.read_bytes())):
                continue
            self._scoped_path(record["path"])

    def _recover_abandoned_jobs(self):
        # An occupied kernel lock belongs to a live service. Do not interrupt it
        # merely because another browser/MCP process opened the same project.
        try:
            with ledger_file_lock(self.run_lock_dir, timeout=0):
                with self.lock, ledger_file_lock(self.storage):
                    registry = self._read_registry()
                    changed = False
                    for job in registry["jobs"]:
                        if job.get("status") in ACTIVE_STATUSES:
                            if self._recover_committed(registry, job):
                                changed = True
                                continue
                            if job.get("backend") == "session" and self._session_live(registry.get("agent", {})):
                                # Session jobs are owned by a live conversation,
                                # not a renderer process holding the kernel lock.
                                continue
                            if self._scheduled_session_job(job, registry.get("agent", {})):
                                continue
                            job.update(status="failed", phase="interrupted", updated_at=timestamp(),
                                       error="The service stopped before this job completed. Requests remain pending unless a verified application was recorded.",
                                       message="Interrupted job; inspect request history before retrying.")
                            changed = True
                    if changed:
                        _atomic_json(self.registry_path, registry)
        except WorkbenchError as exc:
            if "busy" not in str(exc):
                raise

    def _recover_committed(self, registry, job):
        """Repair the small crash window after ledger commit, before registry publication.

        Only an actual matching applied event plus fresh bound export QA can
        complete a job. A prepared directory or success-looking SVG alone is
        insufficient and can never turn a cancelled request into an outcome.
        """
        relative = job.get("target_path")
        if not isinstance(relative, str):
            return False
        try:
            target = self._scoped_path(relative, directory=True)
            source_record = registry["attempts"].get(job.get("source_attempt_id"))
            if not isinstance(source_record, dict):
                return False
            source = FigureWorkbench(self._scoped_path(source_record["path"], directory=True))
            ids = job.get("fulfilled_request_ids", []) if job.get("kind") == "agent" else job.get("automatic_request_ids", [])
            event = next((item for item in reversed(source.ledger().get("history", []))
                          if isinstance(item, dict) and item.get("action") == "applied"
                          and item.get("target_attempt") == str(target) and set(item.get("request_ids", [])) == set(ids)), None)
            if event is None or not ids:
                return False
            app, state = _helpers().verified_attempt(target)
            self._sources_in_scope(state)
            if event.get("target_version") != state["version"]:
                return False
            qa_bytes = app.read_file("qa.json")
            if qa_bytes is None or sha256(qa_bytes) != event.get("target_qa_sha256"):
                return False
            _helpers().verify_qa_binding(app, qa_bytes, "recovering committed preview history")
            target_id = "attempt-" + sha256(relative.encode())[:16]
            if target_id not in registry["attempts"] and len(registry["attempts"]) >= MAX_ATTEMPTS:
                return False
            registry["attempts"][target_id] = {"path": relative, "registered_at": timestamp()}
            if job.get("kind") == "agent":
                pending = [request_id for request_id in job.get("request_ids", []) if request_id not in ids]
                job.update(agent_request_ids=pending,
                           agent_requests=[item for item in job.get("agent_requests", [])
                                           if item.get("request_id") in pending])
            job.update(status="succeeded", phase="complete", target_attempt_id=target_id, updated_at=timestamp(),
                       error=None, message="Recovered a verified preview already recorded before service interruption.", outcome_id=event["id"])
            return True
        except (WorkbenchError, OSError, TypeError, KeyError):
            return False

    def register_attempt(self, figure_dir):
        path = self._scoped_path(figure_dir, directory=True)
        app = FigureWorkbench(path)
        state = app.state()
        relative = str(path.relative_to(self.project))
        attempt_id = "attempt-" + sha256(relative.encode())[:16]
        with self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            # Removed attempts should not consume the bounded registry forever.
            registry["attempts"] = {key: item for key, item in registry["attempts"].items()
                                    if isinstance(item, dict) and isinstance(item.get("path"), str)
                                    and (self.project / item["path"]).is_dir()}
            if attempt_id not in registry["attempts"] and len(registry["attempts"]) >= MAX_ATTEMPTS:
                raise WorkbenchError("This project already has 100 registered attempts; open a new project scope")
            registry["attempts"].setdefault(attempt_id, {"path": relative, "registered_at": timestamp()})
            _atomic_json(self.registry_path, registry)
        result = self.get_attempt(attempt_id)
        if self.app is None:
            app.token = self.token
            self.current_attempt_id, self.app = attempt_id, app
        return result

    def attempt_app(self, attempt_id=None):
        attempt_id = attempt_id or self.current_attempt_id
        if not isinstance(attempt_id, str) or not attempt_id.startswith("attempt-"):
            raise WorkbenchError("Select a registered attempt ID")
        with self.lock, ledger_file_lock(self.storage):
            record = self._read_registry()["attempts"].get(attempt_id)
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise WorkbenchError("Unknown registered attempt")
        app = FigureWorkbench(self._scoped_path(record["path"], directory=True))
        return app

    def get_attempt(self, attempt_id=None):
        attempt_id = attempt_id or self.current_attempt_id
        app = self.attempt_app(attempt_id)
        state = app.state()
        with self.lock, ledger_file_lock(self.storage):
            record = self._read_registry()["attempts"].get(attempt_id, {})
        base = f"/api/attempts/{attempt_id}"
        return {"id": attempt_id, "name": app.figure_name(record.get("display_name")), "path": str(app.root),
                "panel": state["panel"], "version": state["version"], "track": state["track"],
                "source_current": state["source_current"], "accepted": (app.root / "accepted-snapshot/acceptance.json").is_file(),
                "preview_url": base + "/preview.svg?v=" + state["version"]["figure_sha256"],
                "files": {ext: base + "/files/panel." + ext for ext in ("svg", "pdf", "png") if "panel." + ext in state["files"]}}

    def rename_attempt(self, name, attempt_id=None):
        """Update portable display metadata; never rename paths or scientific exports."""
        if attempt_id is not None and (not isinstance(attempt_id, str) or not attempt_id.startswith("attempt-")):
            raise WorkbenchError("Select a registered attempt ID")
        attempt_id = attempt_id or self.current_attempt_id
        app = self.attempt_app(attempt_id)
        app.rename(name)
        warning = _refresh_document(app.root, warning_message=
            "The figure name was saved, but its editable document needs to be exported again.")
        result = {"attempt": self.get_attempt(attempt_id), "state": workbench_state(self)}
        if warning:
            result["document_warning"] = warning
        return result

    def list_attempts(self):
        with self.lock, ledger_file_lock(self.storage):
            ids = list(self._read_registry()["attempts"])
        attempts = []
        for attempt_id in ids:
            try:
                attempts.append(self.get_attempt(attempt_id))
            except (OSError, WorkbenchError) as exc:
                attempts.append({"id": attempt_id, "unavailable": True, "error": str(exc)})
        return {"current_attempt_id": self.current_attempt_id, "review_attempt_id": self.review_attempt_id(), "attempts": attempts}

    def review_attempt_id(self):
        with self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            selected = registry.get("review_attempt_id")
            return selected if selected in registry["attempts"] else None

    def note_reviewed_attempt(self, attempt_id):
        with self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            if attempt_id not in registry["attempts"]:
                raise WorkbenchError("Unknown registered attempt")
            registry.update(review_attempt_id=attempt_id, review_updated_at=timestamp())
            _atomic_json(self.registry_path, registry)

    def switch_attempt(self, attempt_id, compare_attempt_id=None, *, publish_review=True):
        app = self.attempt_app(attempt_id)
        if compare_attempt_id:
            app.comparison = self.attempt_app(compare_attempt_id)
        app.token = self.token
        with self.lock:
            self.current_attempt_id, self.app = attempt_id, app
        if publish_review:
            self.note_reviewed_attempt(attempt_id)
        return {"state": self.state()}

    def state(self):
        with self.lock:
            if self.app is None:
                raise WorkbenchError("Register and select an attempt first")
            app = self.app
            state = app.state()
            state.update(project_id=self.project_id, attempt_id=self.current_attempt_id, token=self.token)
            with ledger_file_lock(self.storage):
                registry = self._read_registry()
                state["figure_name"] = app.figure_name(registry["attempts"].get(self.current_attempt_id, {}).get("display_name"))
                if app.comparison and state["comparison"]:
                    relative = str(app.comparison.root.relative_to(self.project))
                    previous_id = "attempt-" + sha256(relative.encode())[:16]
                    state["comparison"]["figure_name"] = app.comparison.figure_name(registry["attempts"].get(previous_id, {}).get("display_name"))
        # Expose only values from already declared, hash-bound settings/specs.
        # These are descriptions for the UI; edit resolution still validates
        # the original manifest and request independently.
        if state["source_current"] is True and state["provenance_valid"]:
            try:
                spec_bytes = _helpers().read_regular(state["input"]["spec_file"])
                if sha256(spec_bytes) != state["input"].get("supplied_spec_sha256"):
                    return state
                spec = safe_json(spec_bytes)
                settings = safe_json(app.read_file("settings.json") or b"{}")
                colors = settings.get("resolved_colors", {}) if isinstance(settings, dict) else {}
                colors_digest = sha256(json.dumps(colors, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")).encode())
                if colors_digest != state["version"].get("resolved_colors_sha256"):
                    colors = {}
                for element in state["elements"]:
                    values = {}
                    editable = element.get("editable", {})
                    if isinstance(editable, list):
                        mapped = {}
                        for prop in editable:
                            try:
                                mapped[prop] = _helpers().resolve_path({"property": prop}, element)
                            except WorkbenchError:
                                pass
                        editable = mapped
                    if isinstance(editable, dict):
                        for prop, path in editable.items():
                            try:
                                node = spec
                                for part in _helpers().pointer_parts(path):
                                    node = node[part]
                                values[prop] = node
                            except (KeyError, TypeError, WorkbenchError):
                                if prop == "color" and path.startswith("/colors/"):
                                    category = _helpers().pointer_parts(path)[-1]
                                    if category in colors:
                                        values[prop] = colors[category]
                    element["editable_values"] = values
            except (OSError, WorkbenchError, TypeError):
                pass
        return state

    def capabilities(self, attempt_id=None):
        reason = "Select a verified core attempt to preview cosmetic requests."
        supported = False
        app = self.attempt_app(attempt_id) if attempt_id else self.app
        if app is not None:
            state = app.state()
            source = state["input"].get("source_script")
            installed = Path(__file__).with_name("render.py").resolve()
            supported = bool(state["source_current"] is True and state["manifest_valid"]
                             and source and Path(source).resolve() == installed
                             and state["version"].get("source_script_sha256") == sha256(installed.read_bytes())
                             and "panel.svg" in state["files"])
            try:
                self._sources_in_scope(state)
                if supported:
                    spec = safe_json(_helpers().read_regular(state["input"]["spec_file"]))
                    settings = safe_json(app.read_file("settings.json") or b"{}")
                    if isinstance(spec, dict) and "profile" in spec or isinstance(settings, dict) and settings.get("figure_profile"):
                        supported = False
            except WorkbenchError:
                supported = False
            reason = ("Mapped core cosmetic edits regenerate the adopted export formats. Other requests can be submitted to a configured Agent."
                      if supported else "This attempt requires Agent source edits; saved requests remain available without automatic rendering.")
            if app.root == self.project:
                supported = False
                reason = "Choose the containing project directory with --project-dir; new attempts must be outside the reviewed attempt. This scope supports review only."
        return {"schema_version": 1, "project_id": self.project_id, "current_attempt_id": attempt_id or self.current_attempt_id,
                "review_attempt_id": self.review_attempt_id(),
                "preview": {"supported": supported, "properties": list(AUTOMATIC_PROPERTIES), "reason": reason},
                "agent": {**self.agent_status(), "mcp_optional": True, "handoff_supported": True},
                "limits": {"max_active_jobs": 1, "max_jobs": MAX_JOBS, "render_timeout_seconds": self.render_timeout,
                           "agent_timeout_seconds": agent_dispatch.AGENT_TIMEOUT_SECONDS}}

    def list_requests(self, attempt_id=None):
        app = self.attempt_app(attempt_id)
        state = app.state()
        return {"attempt_id": attempt_id or self.current_attempt_id, "figure_name": state["figure_name"],
                "version": state["version"], "requests": state["requests"],
                "message": "Read pending requests bound to this figure version. Custom edits require active Agent code changes."}

    def save_requests(self, payload):
        with self.lock:
            result = self.app.change_batch(payload)
            result["state"] = self.state()
            return result

    def _classify(self, app, state, requests):
        supported, agent = [], []
        installed = Path(__file__).with_name("render.py").resolve()
        is_core = (state["input"].get("source_script") == str(installed)
                   and state["version"].get("source_script_sha256") == sha256(installed.read_bytes())
                   and "panel.svg" in state["files"])
        spec = safe_json(_helpers().read_regular(state["input"]["spec_file"]))
        settings = safe_json(app.read_file("settings.json") or b"{}")
        shared_profile = isinstance(spec, dict) and "profile" in spec or isinstance(settings, dict) and bool(settings.get("figure_profile"))
        for item in requests:
            try:
                if not is_core:
                    raise WorkbenchError("Custom plotting source requires Agent implementation")
                if shared_profile:
                    raise WorkbenchError("Shared profile edits require Agent implementation across dependent panels")
                _helpers().cosmetic_value(item.get("property"), item.get("value"))
                paths = [_helpers().resolve_path(item, element) for element in _helpers().request_elements(item, state)]
                if any(_helpers().pointer_parts(path)[0] == "style" for path in paths):
                    raise WorkbenchError("Custom style bindings require Agent implementation")
                supported.append(item["id"])
            except WorkbenchError as exc:
                agent.append({"request_id": item["id"], "reason": str(exc)})
        return supported, agent

    def prepare_edits(self, version, request_ids=None, attempt_id=None):
        if request_ids is not None and (not isinstance(request_ids, list) or not 1 <= len(request_ids) <= 100
                or not all(isinstance(item, str) and item for item in request_ids) or len(set(request_ids)) != len(request_ids)):
            raise WorkbenchError("request_ids must contain 1 to 100 unique saved request IDs")
        app = self.attempt_app(attempt_id)
        state = app.current_state(version)
        self._sources_in_scope(state)
        _, requests, _ = _helpers().selected_requests(app, state, request_ids)
        supported, agent = self._classify(app, state, requests)
        return {"attempt_id": attempt_id or self.current_attempt_id, "figure_name": state["figure_name"], "version": version,
                "automatic_request_ids": supported, "agent_requests": agent, "requests": requests,
                "input": state["input"], "panel": state["panel"],
                "message": "Automatic changes are cosmetic and use the verified core source. Agent requests remain pending until fresh exports pass QA and their outcome is recorded."}

    def list_jobs(self):
        with self.lock, ledger_file_lock(self.storage):
            jobs = copy.deepcopy(self._read_registry()["jobs"])
        # Older failed jobs may contain raw CLI diagnostics. Preserve their
        # owner logs and normalize the public history as well as new failures.
        for job in jobs:
            if job.get("kind") == "agent" and isinstance(job.get("error"), str):
                message, startup_failed = agent_dispatch.worker_error(job["error"])
                if startup_failed:
                    job.update(error=message, backend_startup_failed=True)
        return {"jobs": jobs}

    def agent_status(self):
        """Describe the opt-in project worker without starting inference."""
        with self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            config = registry.get("agent", {})
            last_job = next((job for job in reversed(registry["jobs"]) if job.get("kind") == "agent"), None)
        if isinstance(config, dict) and config.get("backend") == "session":
            live = self._session_live(config)
            scheduled = self._session_trigger_live(config)
            active = next((job for job in reversed(registry["jobs"])
                           if job.get("backend") == "session" and job.get("status") in ACTIVE_STATUSES), None)
            trigger = copy.deepcopy(config.get("session_trigger"))
            if isinstance(trigger, dict):
                trigger.update(registered=True, active=scheduled, verification="owner_registered")
            return {"backend": "session", "enabled": live or scheduled, "available": live or scheduled,
                    "automatic_dispatch": live or scheduled, "existing_chat_wake": scheduled, "same_session": True,
                    "live_listener": live, "scheduled_dispatch": scheduled,
                    "dispatch_mode": "active_mcp" if live else "host_heartbeat" if scheduled else "disconnected",
                    "host_trigger": trigger, "check_interval_seconds": trigger.get("interval_seconds") if scheduled else None,
                    "trigger_expires_at": trigger.get("expires_at") if isinstance(trigger, dict) else None,
                    "owner_session_id": config.get("owner_session_id"), "host": config.get("host"),
                    "connection_id": config.get("connection_id"), "lease_expires_at": config.get("lease_expires_at"),
                    "runtime_state": "running" if live and active else "connected" if live else "scheduled" if scheduled else
                                     "expired" if config.get("enabled") else "disconnected",
                    "message": "Edits are queued for the connected original conversation while it listens through MCP."
                               if live else "Edits wait for the registered Codex Desktop automatic check; delivery is scheduled, not instant."
                               if scheduled else "Reconnect the original conversation through MCP; saved edits remain pending.",
                    "project_id": self.project_id}
        enabled = isinstance(config, dict) and config.get("enabled") is True and config.get("backend") == "codex"
        available = agent_dispatch.codex_binary() is not None
        startup_error = last_job.get("error") if last_job and last_job.get("backend_startup_failed") else None
        if last_job and isinstance(last_job.get("error"), str):
            normalized, failed = agent_dispatch.worker_error(last_job["error"])
            if failed:
                startup_error = normalized
        runtime_state = ("startup_failed" if startup_error else
                         "running" if last_job and last_job["status"] in ACTIVE_STATUSES else
                         "last_job_succeeded" if last_job and last_job.get("phase") == "complete" else "unverified")
        return {"backend": "codex", "enabled": enabled, "available": available, "executable_available": available,
                "automatic_dispatch": enabled and available, "existing_chat_wake": False,
                "runtime_state": runtime_state, "last_startup_error": startup_error,
                "timeout_seconds": agent_dispatch.AGENT_TIMEOUT_SECONDS,
                "message": (startup_error if enabled and startup_error else
                            "Configured for explicit submissions; authentication and runtime startup are checked when a job begins." if enabled and available
                            else "Connect the installed Codex CLI for this project to submit saved edits."),
                "project_id": self.project_id}

    @staticmethod
    def _agent_retry_reuses(job, key):
        # A declined batch has no applied receipt and must remain retryable.
        return (job.get("idempotency_key") == key and
                (job["status"] in ACTIVE_STATUSES or
                 (job["status"] == "succeeded" and job.get("phase") == "complete" and job.get("outcome_id"))))

    def configure_agent(self, backend="codex", enabled=True):
        """Authorize only the known backend in this explicit project scope."""
        if backend == "session" and enabled is False:
            with self.lock, ledger_file_lock(self.storage):
                registry = self._read_registry()
                if registry.get("agent", {}).get("backend") != "session":
                    raise WorkbenchError("No original conversation connection is configured")
                registry["agent"].update(enabled=False, updated_at=timestamp())
                if isinstance(registry["agent"].get("session_trigger"), dict):
                    registry["agent"]["session_trigger"]["enabled"] = False
                self._end_session_jobs(registry, "Disconnected from the original conversation. Saved edits remain pending.")
                _atomic_json(self.registry_path, registry)
            return self.agent_status()
        if backend != "codex" or not isinstance(enabled, bool):
            raise WorkbenchError("Only the Codex backend and a boolean enabled flag are supported")
        if enabled:
            agent_dispatch.verify_backend()
        with self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            if any(job.get("backend") == "session" and job.get("status") in ACTIVE_STATUSES for job in registry["jobs"]):
                raise WorkbenchError("Finish or cancel the original conversation job before changing backends")
            registry["agent"] = {"backend": backend, "enabled": enabled, "updated_at": timestamp()}
            _atomic_json(self.registry_path, registry)
        return self.agent_status()

    @staticmethod
    def _session_live(config):
        expiry = config.get("lease_expires_at") if isinstance(config, dict) else None
        return (isinstance(config, dict) and config.get("backend") == "session"
                and config.get("enabled") is True and isinstance(expiry, (int, float))
                and not isinstance(expiry, bool) and expiry > time.time())

    def _session_trigger_live(self, config):
        trigger = config.get("session_trigger") if isinstance(config, dict) else None
        if (not isinstance(trigger, dict) or config.get("backend") != "session" or config.get("enabled") is not True
                or config.get("host") != "codex" or trigger.get("enabled") is not True
                or trigger.get("host") != "codex_desktop" or trigger.get("kind") != "heartbeat"
                or trigger.get("project_id") != self.project_id
                or trigger.get("owner_session_id") != config.get("owner_session_id")
                or not isinstance(trigger.get("automation_id"), str) or not trigger["automation_id"]):
            return False
        expiry, interval = trigger.get("expires_at"), trigger.get("interval_seconds")
        return (isinstance(expiry, (int, float)) and not isinstance(expiry, bool) and math.isfinite(expiry)
                and expiry > time.time() and isinstance(interval, int) and not isinstance(interval, bool)
                and 60 <= interval <= 3600)

    def _scheduled_session_job(self, job, config):
        return (self._session_trigger_live(config) and job.get("backend") == "session"
                and job.get("status") == "queued" and not job.get("cancel_requested")
                and job.get("owner_session_id") == config.get("owner_session_id")
                and job.get("host_trigger_id") == config["session_trigger"]["automation_id"])

    def _end_session_jobs(self, registry, message, *, status="cancelled", preserve_scheduled=False):
        for job in registry["jobs"]:
            if job.get("backend") == "session" and job.get("status") in ACTIVE_STATUSES:
                if self._recover_committed(registry, job):
                    continue
                if preserve_scheduled and self._scheduled_session_job(job, registry.get("agent", {})):
                    continue
                job.update(status=status, phase=status, cancel_requested=status == "cancelled",
                           updated_at=timestamp(), message=message, error=None)

    @staticmethod
    def _session_identity(owner_session_id, host):
        if (not isinstance(owner_session_id, str) or
                not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}", owner_session_id)):
            raise WorkbenchError("Provide the original host's bounded session identifier")
        if host not in {"codex", "claude-code", "opencode", "local-agent"}:
            raise WorkbenchError("Unsupported original Agent host")
        expected = os.environ.get("CODEX_THREAD_ID")
        if expected and (owner_session_id != expected or host != "codex"):
            raise WorkbenchError("Connection must belong to this original Codex conversation")

    def connect_session(self, owner_session_id, host="codex", lease_seconds=SESSION_LEASE_SECONDS):
        """Bind an active original conversation; never start a model or host process.

        The bearer credential is returned only to the Agent's MCP call. Public
        status and jobs contain no credential, and disk stores only its digest.
        A bounded listener refreshes the lease; this does not wake an idle chat.
        """
        self._session_identity(owner_session_id, host)
        if (isinstance(lease_seconds, bool) or not isinstance(lease_seconds, int)
                or not 30 <= lease_seconds <= MAX_SESSION_LEASE_SECONDS):
            raise WorkbenchError("Session lease must be 30 to 3600 seconds")
        if self._closed:
            raise WorkbenchError("The figure service is closing")
        token = secrets.token_urlsafe(32)
        connection_id = "session-" + uuid.uuid4().hex
        with self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            old = registry.get("agent", {})
            owner = registry.get("session_owner")
            if owner is None and isinstance(old, dict) and old.get("backend") == "session":
                owner = {"owner_session_id": old.get("owner_session_id"), "host": old.get("host")}
            if owner is not None and owner != {"owner_session_id": owner_session_id, "host": host}:
                raise WorkbenchError("This project belongs to its original conversation; an explicit user-authorized ownership transfer is required")
            if self._session_live(old):
                raise WorkbenchError("An original conversation is already connected; use its credential or disconnect first")
            if any(job.get("backend") != "session" and job.get("status") in ACTIVE_STATUSES
                   for job in registry["jobs"]):
                raise WorkbenchError("Another figure job is active in this project; wait or cancel it first")
            self._end_session_jobs(registry, "The original conversation connection expired. Saved edits remain pending.",
                                   status="failed", preserve_scheduled=True)
            registry["session_owner"] = {"owner_session_id": owner_session_id, "host": host}
            registry["agent"] = {"backend": "session", "enabled": True, "host": host,
                "owner_session_id": owner_session_id, "connection_id": connection_id,
                "token_sha256": sha256(token.encode()), "lease_seconds": lease_seconds,
                "lease_expires_at": time.time() + lease_seconds, "updated_at": timestamp()}
            if isinstance(old.get("session_trigger"), dict):
                registry["agent"]["session_trigger"] = copy.deepcopy(old["session_trigger"])
            for job in registry["jobs"]:
                if self._scheduled_session_job(job, registry["agent"]):
                    job.update(connection_id=connection_id, updated_at=timestamp(),
                               message="Waiting for the reconnected original conversation.")
            _atomic_json(self.registry_path, registry)
        return {"connection_id": connection_id, "connection_token": token,
                "owner_session_id": owner_session_id, "status": self.agent_status()}

    def _session_auth(self, registry, owner_session_id, connection_token, *, refresh=False):
        config = registry.get("agent", {})
        if (not self._session_live(config) or owner_session_id != config.get("owner_session_id")
                or not isinstance(connection_token, str) or not 1 <= len(connection_token) <= 200
                or not secrets.compare_digest(sha256(connection_token.encode()), config.get("token_sha256", ""))):
            raise WorkbenchError("The original conversation connection is expired or its ownership credential is invalid")
        if refresh:
            config.update(lease_expires_at=time.time() + config["lease_seconds"], updated_at=timestamp())
        return config

    def renew_same_session(self, owner_session_id, connection_token):
        """Refresh only a still-live connection with its unchanged owner credential."""
        if self._closed:
            raise WorkbenchError("The figure service is closing")
        with self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            config = self._session_auth(registry, owner_session_id, connection_token, refresh=True)
            connection_id = config["connection_id"]
            _atomic_json(self.registry_path, registry)
        return {"connection_id": connection_id, "status": self.agent_status()}

    def register_session_trigger(self, owner_session_id, connection_token, automation_id,
                                 interval_seconds, expires_at):
        """Register an already-created native Desktop heartbeat, never create one.

        The original Agent must first receive a successful native host-tool
        creation result. This metadata is its explicit registration, not an
        independent claim that the host scheduler has run or delivers instantly.
        """
        if self._closed:
            raise WorkbenchError("The figure service is closing")
        if not isinstance(automation_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", automation_id):
            raise WorkbenchError("Provide the actual bounded native automation identifier")
        if (isinstance(interval_seconds, bool) or not isinstance(interval_seconds, int)
                or not 60 <= interval_seconds <= 3600):
            raise WorkbenchError("Native automatic-check interval must be 60 to 3600 seconds")
        if (isinstance(expires_at, bool) or not isinstance(expires_at, (int, float))
                or not math.isfinite(expires_at) or not time.time() + interval_seconds <= expires_at <= time.time() + 86400):
            raise WorkbenchError("Native trigger expiry must allow one scheduled check and be within 24 hours (Unix seconds)")
        with self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            config = self._session_auth(registry, owner_session_id, connection_token, refresh=True)
            if config.get("host") != "codex":
                raise WorkbenchError("Only a successfully created native Codex Desktop heartbeat is supported")
            config["session_trigger"] = {"kind": "heartbeat", "host": "codex_desktop",
                "automation_id": automation_id, "owner_session_id": owner_session_id,
                "project_id": self.project_id, "interval_seconds": interval_seconds,
                "expires_at": expires_at, "enabled": True, "registered_at": timestamp()}
            for job in registry["jobs"]:
                if (job.get("backend") == "session" and job.get("status") == "queued"
                        and job.get("owner_session_id") == owner_session_id
                        and job.get("connection_id") == config["connection_id"] and not job.get("cancel_requested")):
                    job["host_trigger_id"] = automation_id
            _atomic_json(self.registry_path, registry)
        return self.agent_status()

    def disable_session_trigger(self, owner_session_id, connection_token):
        """Disable queue scheduling metadata; the Agent must also stop the native host check."""
        with self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            config = self._session_auth(registry, owner_session_id, connection_token)
            if isinstance(config.get("session_trigger"), dict):
                config["session_trigger"].update(enabled=False, disabled_at=timestamp())
                _atomic_json(self.registry_path, registry)
        return self.agent_status()

    def disconnect_session(self, owner_session_id, connection_token):
        with self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            self._session_auth(registry, owner_session_id, connection_token)
            registry["agent"].update(enabled=False, updated_at=timestamp())
            if isinstance(registry["agent"].get("session_trigger"), dict):
                registry["agent"]["session_trigger"]["enabled"] = False
            self._end_session_jobs(registry, "Disconnected from the original conversation. Saved edits remain pending.")
            _atomic_json(self.registry_path, registry)
        return self.agent_status()

    @staticmethod
    def _adopted_session_formats(app, state):
        """Mutable descriptive metadata cannot reduce existing bound exports."""
        return agent_dispatch.adopted_formats(app, state)

    def _submit_session_job(self, version, request_ids=None, attempt_id=None):
        attempt_id = attempt_id or self.current_attempt_id
        with self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            config = registry.get("agent", {})
            if not (self._session_live(config) or self._session_trigger_live(config)):
                raise WorkbenchError("Reconnect the original conversation through MCP before submitting; no separate worker will be started")
            if (isinstance(request_ids, list) and request_ids and
                    all(isinstance(item, str) for item in request_ids)):
                retry_key = sha256(json.dumps(["session", config["owner_session_id"], config["host"], attempt_id, version, sorted(request_ids)],
                                              sort_keys=True, allow_nan=False).encode())
                old = next((job for job in registry["jobs"] if self._agent_retry_reuses(job, retry_key)), None)
                if old:
                    return {"job": copy.deepcopy(old)}
        plan = self.prepare_edits(version, request_ids, attempt_id)
        app = self.attempt_app(attempt_id)
        state = app.current_state(version)
        if state["source_current"] is not True or not state["provenance_valid"]:
            raise WorkbenchError("Session submissions require current bound source, data and specification")
        formats = self._adopted_session_formats(app, state)
        ids = [request["id"] for request in plan["requests"]]
        run_lock = ledger_file_lock(self.run_lock_dir, timeout=0)
        with run_lock, self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            config = registry.get("agent", {})
            if not (self._session_live(config) or self._session_trigger_live(config)):
                raise WorkbenchError("Reconnect the original conversation through MCP before submitting; no separate worker will be started")
            key = sha256(json.dumps(["session", config["owner_session_id"], config["host"], attempt_id, version, sorted(ids)],
                                    sort_keys=True, allow_nan=False).encode())
            old = next((job for job in registry["jobs"] if self._agent_retry_reuses(job, key)), None)
            if old:
                return {"job": copy.deepcopy(old)}
            if any(job.get("status") in ACTIVE_STATUSES for job in registry["jobs"]):
                raise WorkbenchError("Another figure job is active in this project; wait or cancel it first")
            # A manual receipt may have committed after preparation. Validate
            # pending identities again while publication owns the registry.
            _helpers().selected_requests(app, app.current_state(version), ids)
            while len(registry["jobs"]) >= MAX_JOBS:
                registry["jobs"].pop(next(i for i, item in enumerate(registry["jobs"])
                                         if item["status"] not in ACTIVE_STATUSES))
            job = {"id": "job-" + uuid.uuid4().hex, "kind": "agent", "backend": "session",
                   "owner_session_id": config["owner_session_id"], "connection_id": config["connection_id"],
                   "status": "queued", "phase": "queued", "message": "Waiting for the connected original conversation.",
                   "error": None, "source_attempt_id": attempt_id, "target_attempt_id": None,
                   "version": copy.deepcopy(version), "adopted_formats": formats,
                   "request_ids": ids, "automatic_request_ids": [],
                   "agent_request_ids": ids, "agent_requests": plan["agent_requests"],
                   "created_at": timestamp(), "updated_at": timestamp(), "idempotency_key": key,
                   "cancel_requested": False}
            if self._session_trigger_live(config):
                job["host_trigger_id"] = config["session_trigger"]["automation_id"]
            registry["jobs"].append(job)
            _atomic_json(self.registry_path, registry)
        return {"job": copy.deepcopy(job)}

    def _release_session_claim(self, owner_session_id, connection_token, job_id):
        """Return an undelivered, unstarted claim to its original queue only.

        A cancelled MCP call may lose a worker thread's return value. Never
        revive cancelled jobs or release work already reported as editing.
        """
        with self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            config = registry.get("agent", {})
            if (config.get("backend") != "session" or config.get("owner_session_id") != owner_session_id
                    or not isinstance(connection_token, str)
                    or not secrets.compare_digest(sha256(connection_token.encode()), config.get("token_sha256", ""))):
                return
            job = next((item for item in registry["jobs"] if item.get("id") == job_id), None)
            if (job is None or job.get("backend") != "session" or job.get("owner_session_id") != owner_session_id
                    or job.get("connection_id") != config.get("connection_id") or job.get("status") != "running"
                    or job.get("phase") != "session_received" or job.get("editing_started_at") or job.get("cancel_requested")):
                return
            job.update(status="queued", phase="queued", updated_at=timestamp(),
                       message="The listener stopped before editing; saved edits remain queued for the original conversation.")
            job.pop("claimed_at", None)
            job.pop("received_at", None)
            _atomic_json(self.registry_path, registry)

    def wait_for_submission(self, owner_session_id, connection_token, timeout_seconds=30, *, cancellation_event=None):
        """Wait at most 45 seconds and claim a batch for this same active conversation."""
        if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
                or not 0 <= timeout_seconds <= 45):
            raise WorkbenchError("Submission wait must be 0 to 45 seconds")
        deadline = time.monotonic() + timeout_seconds
        next_heartbeat = 0
        def stopped():
            return self._closed or (cancellation_event is not None and cancellation_event.is_set())
        while True:
            if stopped():
                return {"job": None, "listener_stopped": True, "status": self.agent_status()}
            with self.lock, ledger_file_lock(self.storage):
                if stopped():
                    return {"job": None, "listener_stopped": True}
                registry = self._read_registry()
                heartbeat = time.monotonic() >= next_heartbeat
                config = self._session_auth(registry, owner_session_id, connection_token, refresh=heartbeat)
                if heartbeat:
                    next_heartbeat = time.monotonic() + min(15, config["lease_seconds"] / 3)
                job = next((job for job in registry["jobs"] if job.get("backend") == "session"
                            and job.get("connection_id") == config["connection_id"]
                            and job.get("status") == "queued" and not job.get("cancel_requested")), None)
                if job:
                    received_at = timestamp()
                    job.update(status="running", phase="session_received", claimed_at=received_at,
                               received_at=received_at, updated_at=received_at,
                               message="The original conversation received these edits.")
                if heartbeat or job:
                    _atomic_json(self.registry_path, registry)
                claimed = copy.deepcopy(job)
            if claimed:
                if stopped():
                    self._release_session_claim(owner_session_id, connection_token, claimed["id"])
                    return {"job": None, "listener_stopped": True, "status": self.agent_status()}
                try:
                    plan = self.prepare_edits(claimed["version"], claimed["request_ids"], claimed["source_attempt_id"])
                except (WorkbenchError, OSError, ValueError) as exc:
                    if stopped():
                        self._release_session_claim(owner_session_id, connection_token, claimed["id"])
                        return {"job": None, "listener_stopped": True, "status": self.agent_status()}
                    with self.lock, ledger_file_lock(self.storage):
                        registry = self._read_registry()
                        current = next(item for item in registry["jobs"] if item["id"] == claimed["id"])
                        if current.get("status") == "running" and not current.get("cancel_requested"):
                            current.update(status="failed", phase="failed", error=str(exc), updated_at=timestamp(),
                                           message="Submitted sources changed; saved edits remain pending.")
                            _atomic_json(self.registry_path, registry)
                    raise
                if stopped():
                    self._release_session_claim(owner_session_id, connection_token, claimed["id"])
                    return {"job": None, "listener_stopped": True, "status": self.agent_status()}
                with self.lock, ledger_file_lock(self.storage):
                    registry = self._read_registry()
                    self._session_auth(registry, owner_session_id, connection_token)
                    current = next(item for item in registry["jobs"] if item["id"] == claimed["id"])
                    if current.get("status") != "running" or current.get("cancel_requested"):
                        claimed = None
                    else:
                        claimed = copy.deepcopy(current)
                if not claimed:
                    return {"job": None, "status": self.agent_status()}
                if stopped():
                    self._release_session_claim(owner_session_id, connection_token, claimed["id"])
                    return {"job": None, "listener_stopped": True, "status": self.agent_status()}
                return {"job": claimed, "plan": plan, "status": self.agent_status()}
            if self._closed or time.monotonic() >= deadline:
                return {"job": None, "status": self.agent_status()}
            delay = min(.2, max(0, deadline - time.monotonic()))
            if cancellation_event is not None:
                cancellation_event.wait(delay)
            else:
                time.sleep(delay)

    def report_session_progress(self, owner_session_id, connection_token, job_id, phase="editing"):
        """Report actual work beginning; receiving a request does not imply editing.

        Only the owning original Agent can advance these durable stages. A
        repeated report keeps the original start time and stages never regress.
        """
        stages = ("received", "editing", "rendering", "reviewing")
        if phase not in stages[1:]:
            raise WorkbenchError("Session progress must be editing, rendering or reviewing")
        with self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            config = self._session_auth(registry, owner_session_id, connection_token, refresh=True)
            job = next((item for item in registry["jobs"] if item.get("id") == job_id), None)
            if (job is None or job.get("backend") != "session" or job.get("owner_session_id") != owner_session_id
                    or job.get("connection_id") != config["connection_id"] or job.get("status") != "running"
                    or job.get("cancel_requested")):
                raise WorkbenchError("Only the connected owner may report progress for its claimed active job")
            current = job.get("phase", "session_received").removeprefix("session_")
            if current not in stages or stages.index(phase) < stages.index(current):
                raise WorkbenchError("Session progress cannot move backwards")
            if phase != current and stages.index(phase) != stages.index(current) + 1:
                raise WorkbenchError("Report editing, rendering and reviewing as each actually begins")
            at = timestamp()
            job.update(phase="session_" + phase, updated_at=at, message={
                "editing": "The original conversation is editing the plotting source.",
                "rendering": "The original conversation is rendering fresh exports.",
                "reviewing": "The original conversation is reviewing the rendered result."}[phase])
            job.setdefault(phase + "_started_at", at)
            _atomic_json(self.registry_path, registry)
        return {"job": copy.deepcopy(job)}

    def complete_session_job(self, owner_session_id, connection_token, job_id, target_attempt_id,
                             request_ids, changed_files, validation):
        """Commit only an owned batch's verified fresh subset; omitted notes stay pending."""
        if (not isinstance(request_ids, list) or not 1 <= len(request_ids) <= 100
                or not all(isinstance(item, str) and item for item in request_ids)
                or len(set(request_ids)) != len(request_ids)):
            raise WorkbenchError("Identify the fulfilled unique request IDs")
        with ledger_file_lock(self.run_lock_dir, timeout=0), self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            config = self._session_auth(registry, owner_session_id, connection_token, refresh=True)
            job = next((job for job in registry["jobs"] if job.get("id") == job_id), None)
            if (job is None or job.get("backend") != "session" or job.get("owner_session_id") != owner_session_id
                    or job.get("connection_id") != config["connection_id"] or job.get("status") != "running"
                    or job.get("cancel_requested")):
                raise WorkbenchError("Only the connected owner may complete its claimed active job")
            if not set(request_ids) <= set(job["request_ids"]):
                raise WorkbenchError("Fulfilled IDs must belong to the claimed batch")
            source_record = registry["attempts"].get(job["source_attempt_id"])
            target_record = registry["attempts"].get(target_attempt_id)
            if not isinstance(source_record, dict) or not isinstance(target_record, dict):
                raise WorkbenchError("Register the fresh result attempt before completing this job")
            source = FigureWorkbench(self._scoped_path(source_record["path"], directory=True))
            source_state = source.current_state(job["version"])
            if source_state["source_current"] is not True:
                raise WorkbenchError("Reviewed source changed; saved requests remain pending")
            target = FigureWorkbench(self._scoped_path(target_record["path"], directory=True))
            target_app, state = _helpers().verified_attempt(target.root)
            self._sources_in_scope(state)
            if state.get("track") != source_state.get("track"):
                raise WorkbenchError("The fresh result must retain the adopted Create or Reproduce track")
            if state["version"].get("figure_sha256") == job["version"].get("figure_sha256"):
                raise WorkbenchError("The result must contain a genuinely changed SVG")
            if (state["version"].get("source_script_sha256") == job["version"].get("source_script_sha256")
                    and state["input"].get("supplied_spec_sha256") == source_state["input"].get("supplied_spec_sha256")):
                raise WorkbenchError("Implement the edits in copied plotting source or specification")
            qa_bytes = target_app.read_file("qa.json")
            _helpers().verify_qa_binding(target_app, qa_bytes, "completing the original conversation job")
            qa = safe_json(qa_bytes)
            formats = job.get("adopted_formats") or self._adopted_session_formats(source, source_state)
            if (not isinstance(formats, list) or "svg" not in formats
                    or any(ext not in {"svg", "pdf", "png", "tiff"} for ext in formats)):
                raise WorkbenchError("Reviewed attempt declares unsupported export formats")
            for extension in formats:
                raw = _helpers().read_regular(target.root / ("panel." + extension))
                record = qa.get("exports", {}).get(extension, {})
                if not isinstance(record, dict) or record.get("sha256") != sha256(raw):
                    raise WorkbenchError("The fresh result requires matching export QA for every adopted format")
            # A render directory is not a new user-facing figure identity. Keep
            # explicit result names; otherwise carry the reviewed name into its
            # portable metadata before packaging the document and receipt.
            with ledger_file_lock(target.root):
                if read_figure_info(target.root) is None:
                    name = target_record.get("display_name")
                    if not isinstance(name, str) or not name.strip():
                        name = source.figure_name(source_record.get("display_name"))
                    _atomic_json(target.root / "figure-info.json", make_figure_info(name))
            _refresh_document(target.root, required=True)
            job.update(fulfilled_request_ids=request_ids, target_path=str(target.root.relative_to(self.project)))
            _atomic_json(self.registry_path, registry)
            event = _helpers().record_requests(source.root, target.root, request_ids,
                                               changed_files=changed_files, validation=validation)
            warning = _refresh_document(target.root)
            pending = [item for item in job["request_ids"] if item not in request_ids]
            job.update(status="succeeded", phase="complete", target_attempt_id=target_attempt_id,
                       outcome_id=event["id"], agent_request_ids=pending,
                       updated_at=timestamp(), error=None, message="Original-conversation preview ready; inspect it before accepting."
                       + (" Some requests remain pending." if pending else ""))
            if warning:
                job["document_warning"] = warning
            _atomic_json(self.registry_path, registry)
        return {"job": copy.deepcopy(job), "outcome": event, "attempt": self.get_attempt(target_attempt_id)}

    def submit_agent_job(self, version, request_ids=None, attempt_id=None):
        """Submit source-bound saved requests to the explicitly connected worker."""
        if self._closed:
            raise WorkbenchError("The figure service is closing")
        if self.agent_status()["backend"] == "session":
            return self._submit_session_job(version, request_ids, attempt_id)
        if not self.agent_status()["automatic_dispatch"]:
            raise WorkbenchError("Connect the local Codex Agent for this project before submitting")
        attempt_id = attempt_id or self.current_attempt_id
        app = self.attempt_app(attempt_id)
        if app.root == self.project:
            raise WorkbenchError("Choose a project containing the reviewed attempt; workers need a separate output directory")
        if request_ids is not None and (not isinstance(request_ids, list) or not 1 <= len(request_ids) <= 100
                or not all(isinstance(item, str) and item for item in request_ids)
                or len(set(request_ids)) != len(request_ids)):
            raise WorkbenchError("request_ids must contain 1 to 100 unique saved request IDs")
        state = app.current_state(version)
        self._sources_in_scope(state)
        if not state["provenance_valid"] or state["source_current"] is not True:
            raise WorkbenchError("Agent submissions require current bound source, data and specification")
        def identity(ids):
            return sha256(json.dumps(["agent", attempt_id, version, sorted(ids)], sort_keys=True, allow_nan=False).encode())
        if request_ids is not None:
            previous = next((job for job in self.list_jobs()["jobs"]
                             if self._agent_retry_reuses(job, identity(request_ids))), None)
            if previous:
                return {"job": previous}
        _, requests, _ = _helpers().selected_requests(app, state, request_ids)
        ids = [item["id"] for item in requests]
        key = identity(ids)
        run_lock = ledger_file_lock(self.run_lock_dir, timeout=0)
        try:
            run_lock.__enter__()
        except WorkbenchError:
            old = next((job for job in self.list_jobs()["jobs"] if self._agent_retry_reuses(job, key)), None)
            if old:
                return {"job": old}
            raise WorkbenchError("Another figure job is active in this project; wait or cancel it first") from None
        try:
            with self.lock, ledger_file_lock(self.storage):
                registry = self._read_registry()
                old = next((job for job in registry["jobs"] if self._agent_retry_reuses(job, key)), None)
                if old:
                    run_lock.__exit__(None, None, None)
                    return {"job": copy.deepcopy(old)}
                if any(item.get("backend") == "session" and item.get("status") in ACTIVE_STATUSES for item in registry["jobs"]):
                    raise WorkbenchError("Another figure job is active in the original conversation")
                _helpers().selected_requests(app, app.current_state(version), ids)
                while len(registry["jobs"]) >= MAX_JOBS:
                    index = next((i for i, item in enumerate(registry["jobs"]) if item["status"] not in ACTIVE_STATUSES), None)
                    if index is None:
                        raise WorkbenchError("Figure jobs are busy")
                    registry["jobs"].pop(index)
                job = {"id": "job-" + uuid.uuid4().hex, "kind": "agent", "backend": "codex",
                       "status": "queued", "phase": "queued", "message": "Starting the project Agent for saved edits.",
                       "error": None, "source_attempt_id": attempt_id, "target_attempt_id": None,
                       "request_ids": ids, "automatic_request_ids": [], "agent_request_ids": ids,
                       "agent_requests": [{"request_id": item, "reason": "Submitted to the project Agent"} for item in ids],
                       "created_at": timestamp(), "updated_at": timestamp(), "idempotency_key": key,
                       "cancel_requested": False, "owner_pid": os.getpid()}
                registry["jobs"].append(job)
                _atomic_json(self.registry_path, registry)
                self._threads = {name: worker for name, worker in self._threads.items() if worker.is_alive()}
                thread = threading.Thread(target=self._run_agent_job, args=(copy.deepcopy(job), version, requests, run_lock),
                                          daemon=True, name="easyviz-agent-" + job["id"])
                self._threads[job["id"]] = thread
                thread.start()
                return {"job": copy.deepcopy(job)}
        except BaseException:
            run_lock.__exit__(*sys.exc_info())
            raise

    def get_job(self, job_id):
        for job in self.list_jobs()["jobs"]:
            if job["id"] == job_id:
                return {"job": job}
        raise WorkbenchError("Unknown job")

    def _update_job(self, job_id, **updates):
        with self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            job = next((item for item in registry["jobs"] if item["id"] == job_id), None)
            if job is None:
                raise WorkbenchError("Unknown job")
            job.update(updates, updated_at=timestamp())
            _atomic_json(self.registry_path, registry)
            return copy.deepcopy(job)

    def submit_job(self, version, request_ids=None, attempt_id=None):
        if self._closed:
            raise WorkbenchError("The figure service is closing")
        attempt_id = attempt_id or self.current_attempt_id
        app = self.attempt_app(attempt_id)
        if app.root == self.project:
            raise WorkbenchError("Choose the containing project directory with --project-dir; new attempts must be outside the reviewed attempt")
        if request_ids is not None:
            if (not isinstance(request_ids, list) or not 1 <= len(request_ids) <= 100
                    or not all(isinstance(item, str) and item for item in request_ids)
                    or len(set(request_ids)) != len(request_ids)):
                raise WorkbenchError("request_ids must contain 1 to 100 unique saved request IDs")
            app.current_state(version)
            retry_key = sha256(json.dumps([attempt_id, version, sorted(request_ids)], sort_keys=True, allow_nan=False).encode())
            for previous in self.list_jobs()["jobs"]:
                if previous.get("idempotency_key") == retry_key and previous["status"] not in {"failed", "cancelled"}:
                    return {"job": previous}
        plan = self.prepare_edits(version, request_ids, attempt_id)
        ids = [item["id"] for item in plan["requests"]]
        key = sha256(json.dumps([attempt_id, version, sorted(ids)], sort_keys=True, allow_nan=False).encode())
        with self.lock, ledger_file_lock(self.storage):
            self._threads = {key: worker for key, worker in self._threads.items() if worker.is_alive()}
            registry = self._read_registry()
            old = next((job for job in registry["jobs"] if job.get("idempotency_key") == key and job["status"] not in {"failed", "cancelled"}), None)
            if old:
                return {"job": copy.deepcopy(old)}
        run_lock = ledger_file_lock(self.run_lock_dir, timeout=0)
        try:
            run_lock.__enter__()
        except WorkbenchError:
            raise WorkbenchError("Another figure job is active in this project; wait or cancel it first") from None
        try:
            with self.lock, ledger_file_lock(self.storage):
                registry = self._read_registry()
                # Bound retained history rather than growing every installation.
                if any(item.get("backend") == "session" and item.get("status") in ACTIVE_STATUSES for item in registry["jobs"]):
                    raise WorkbenchError("Another figure job is active in the original conversation")
                _helpers().selected_requests(app, app.current_state(version), ids)
                while len(registry["jobs"]) >= MAX_JOBS:
                    index = next((i for i, item in enumerate(registry["jobs"]) if item["status"] not in ACTIVE_STATUSES), None)
                    if index is None:
                        raise WorkbenchError("Figure jobs are busy")
                    registry["jobs"].pop(index)
                job = {"id": "job-" + uuid.uuid4().hex, "status": "queued", "phase": "queued", "message": "Preparing saved requests.",
                       "error": None, "source_attempt_id": attempt_id, "target_attempt_id": None,
                       "request_ids": ids, "automatic_request_ids": plan["automatic_request_ids"],
                       "agent_request_ids": [item["request_id"] for item in plan["agent_requests"]],
                       "agent_requests": plan["agent_requests"], "created_at": timestamp(), "updated_at": timestamp(),
                       "idempotency_key": key, "cancel_requested": False, "owner_pid": os.getpid()}
                registry["jobs"].append(job)
                _atomic_json(self.registry_path, registry)
                thread = threading.Thread(target=self._run_job, args=(copy.deepcopy(job), version, run_lock), daemon=True,
                                          name="easyviz-" + job["id"])
                self._threads[job["id"]] = thread
                thread.start()
                return {"job": copy.deepcopy(job)}
        except BaseException:
            run_lock.__exit__(*sys.exc_info())
            raise

    def _run_job(self, job, version, run_lock):
        job_id, process = job["id"], None
        try:
            if self.get_job(job_id)["job"]["cancel_requested"]:
                raise InterruptedError("Cancelled before rendering")
            if not job["automatic_request_ids"]:
                self._finish_handoff(job_id)
                return
            self._update_job(job_id, status="running", phase="preparing", message="Preparing a fresh attempt; current exports stay intact.")
            app = self.attempt_app(job["source_attempt_id"])
            state = app.current_state(version)
            self._sources_in_scope(state)
            target_parent = self.storage / "attempts"
            if target_parent.is_symlink():
                raise WorkbenchError("Attempt storage must not be a symlink")
            target_parent.mkdir(exist_ok=True)
            target = target_parent / job_id
            plan = _helpers().prepare_requests(app.root, target, job["automatic_request_ids"], render=False)
            write_figure_info(target, self.get_attempt(job["source_attempt_id"])["name"])
            self._update_job(job_id, phase="rendering", target_path=str(target.relative_to(self.project)),
                             message="Regenerating fresh exports in the adopted formats.")
            command = [sys.executable, str(Path(__file__).resolve()), "_render-worker", "--plan", str(target / "request-plan.json")]
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       start_new_session=os.name != "nt")
            started = time.monotonic()
            while True:
                current = self.get_job(job_id)["job"]
                if current["cancel_requested"] or self._closed:
                    self._stop_process(process)
                    raise InterruptedError("Cancelled; no new attempt was published")
                if time.monotonic() - started > self.render_timeout:
                    self._stop_process(process)
                    raise WorkbenchError(f"Core rendering exceeded the {self.render_timeout:g}-second job limit")
                try:
                    stdout, stderr = process.communicate(timeout=.1)
                    break
                except subprocess.TimeoutExpired:
                    continue
            if process.returncode != 0:
                error = stderr[-8000:].decode("utf-8", errors="replace").strip()
                raise WorkbenchError(error or "Core rendering failed before export publication")
            target_app, target_state = _helpers().verified_attempt(target)
            self._sources_in_scope(target_state)
            if target_app.read_file("panel.svg") is None:
                raise WorkbenchError("Preview requires a fresh SVG export")
            _helpers().verify_qa_binding(target_app, target_app.read_file("qa.json"), "publishing the preview")
            # Commit serializes against cancellation, including cancellation from
            # another MCP/HTTP process. A cancelled job never applies requests.
            with self.lock, ledger_file_lock(self.storage):
                registry = self._read_registry()
                current = next(item for item in registry["jobs"] if item["id"] == job_id)
                if current["cancel_requested"] or self._closed:
                    raise InterruptedError("Cancelled before request-history publication")
                if len(registry["attempts"]) >= MAX_ATTEMPTS:
                    raise WorkbenchError("This project already has 100 registered attempts")
                owners = {patch["request_id"] for patch in plan["patches"]}
                event = _helpers().record_requests(app.root, target, job["automatic_request_ids"],
                    changed_files=["plot-spec.json"], validation="Core export QA passed. Inspect the fresh preview before accepting its visual design.",
                    superseded_ids=[item for item in job["automatic_request_ids"] if item not in owners])
                document_warning = _refresh_document(target)
                relative = str(target.relative_to(self.project))
                target_id = "attempt-" + sha256(relative.encode())[:16]
                source_record = registry["attempts"].get(job["source_attempt_id"], {})
                family = source_record.get("family_name", source_record.get("display_name", app.root.name))
                ordinal = 1 + sum(record.get("family_name") == family for record in registry["attempts"].values())
                registry["attempts"][target_id] = {"path": relative, "registered_at": timestamp(),
                                                  "family_name": family, "display_name": f"{family} · preview {ordinal}"}
                current.update(status="succeeded", phase="complete", target_attempt_id=target_id, updated_at=timestamp(),
                               message="Preview ready. Inspect and accept it; Agent instructions remain pending." if job["agent_request_ids"] else "Preview ready. Inspect it before accepting.",
                               outcome_id=event["id"])
                if document_warning:
                    current["document_warning"] = document_warning
                _atomic_json(self.registry_path, registry)
        except InterruptedError as exc:
            self._update_job(job_id, status="cancelled", phase="cancelled", message=str(exc), error=None)
        except Exception as exc:
            # If the ledger commit succeeded but metadata publication failed,
            # recover that actual outcome rather than misreporting a failure
            # whose requests were already applied.
            with self.lock, ledger_file_lock(self.storage):
                registry = self._read_registry()
                current = next(item for item in registry["jobs"] if item["id"] == job_id)
                if not self._recover_committed(registry, current):
                    current.update(status="failed", phase="failed", error=str(exc)[:8000], updated_at=timestamp(),
                                   message="Preview failed. The current figure is preserved; inspect the error before retrying.")
                _atomic_json(self.registry_path, registry)
        finally:
            if process is not None and process.poll() is None:
                self._stop_process(process)
            run_lock.__exit__(None, None, None)

    def _run_agent_job(self, job, version, requests, run_lock):
        """Own the worker through cancellation, fresh export QA and ledger commit."""
        job_id, process = job["id"], None
        try:
            if self.get_job(job_id)["job"]["cancel_requested"] or self._closed:
                raise InterruptedError("Cancelled before starting the Agent; saved edits remain pending")
            app = self.attempt_app(job["source_attempt_id"])
            state = app.current_state(version)
            self._sources_in_scope(state)
            parent = self.storage / "attempts"
            if parent.is_symlink():
                raise WorkbenchError("Attempt storage must not be a symlink")
            parent.mkdir(exist_ok=True)
            target = parent / job_id
            context, prompt = agent_dispatch.prepare_workspace(app, state, target, requests,
                                                              read_regular=_helpers().read_regular)
            self._update_job(job_id, status="running", phase="agent_editing", target_path=str(target.relative_to(self.project)),
                             message="The project Agent is editing copied plotting code and rendering a fresh attempt.")
            logs = [target / "agent-events.jsonl", target / "agent-stderr.log"]
            with logs[0].open("xb") as stdout, logs[1].open("xb") as stderr:
                process = agent_dispatch.start_worker(target, agent_dispatch.verify_backend(), prompt, stdout, stderr)
                started = time.monotonic()
                while process.poll() is None:
                    current = self.get_job(job_id)["job"]
                    if current["cancel_requested"] or self._closed:
                        self._stop_process(process)
                        raise InterruptedError("Agent cancelled; uncommitted requests remain pending")
                    if time.monotonic() - started > agent_dispatch.AGENT_TIMEOUT_SECONDS:
                        self._stop_process(process)
                        raise WorkbenchError("Agent exceeded the project job time limit; uncommitted requests remain pending")
                    if sum(path.stat().st_size for path in logs) > agent_dispatch.MAX_WORKER_LOG_BYTES:
                        self._stop_process(process)
                        raise WorkbenchError("Agent output exceeded the bounded job log limit")
                    time.sleep(.1)
            if sum(path.stat().st_size for path in logs) > agent_dispatch.MAX_WORKER_LOG_BYTES:
                raise WorkbenchError("Agent output exceeded the bounded job log limit")
            if process.returncode != 0:
                with logs[1].open("rb") as stream:
                    stream.seek(max(0, logs[1].stat().st_size - 8000))
                    error = stream.read().decode("utf-8", errors="replace").strip()
                message, startup_failed = agent_dispatch.worker_error(error)
                self._update_job(job_id, backend_startup_failed=startup_failed)
                raise WorkbenchError(message)
            result = agent_dispatch.read_result(target, job["request_ids"])
            fulfilled, pending = result["fulfilled_request_ids"], result["unfulfilled_request_ids"]
            # The worker's text result is not evidence that a plot was rendered.
            # An entirely unfulfilled batch remains pending without publishing
            # a blank or success-looking attempt.
            if not fulfilled:
                with self.lock, ledger_file_lock(self.storage):
                    registry = self._read_registry()
                    current = next(item for item in registry["jobs"] if item["id"] == job_id)
                    if current["cancel_requested"] or self._closed:
                        raise InterruptedError("Cancelled before Agent outcome publication")
                    current.update(status="succeeded", phase="agent_handoff", updated_at=timestamp(),
                                   message="No requests were fulfilled. " + result["validation"],
                                   agent_request_ids=pending, error=None)
                    _atomic_json(self.registry_path, registry)
                return
            if app.current_state(version)["source_current"] is not True:
                raise WorkbenchError("Reviewed inputs changed while the Agent was working; saved edits remain pending")
            self._update_job(job_id, phase="validating", message="Checking actual rendered exports, source data and request identities.")
            target_app, target_state = _helpers().verified_attempt(target)
            self._sources_in_scope(target_state)
            if state.get("track") and target_state.get("track") != state["track"]:
                raise WorkbenchError("Agent output must retain the adopted Create or Reproduce track")
            if target_state["version"]["figure_sha256"] == version["figure_sha256"]:
                raise WorkbenchError("Agent claimed edits but produced the unchanged original SVG")
            if (target_state["version"].get("source_script_sha256") == version.get("source_script_sha256")
                    and target_state["input"].get("supplied_spec_sha256") == state["input"].get("supplied_spec_sha256")):
                raise WorkbenchError("Agent must implement requests in copied plotting source or specification")
            qa_bytes = target_app.read_file("qa.json")
            _helpers().verify_qa_binding(target_app, qa_bytes, "publishing the Agent result")
            qa = safe_json(qa_bytes)
            for extension in context["formats"]:
                # Fixed adopted formats may include TIFF, which deliberately
                # remains outside the public workbench file allowlist.
                export_path = target_app.root / ("panel." + extension)
                raw = _helpers().read_regular(export_path) if export_path.exists() else None
                record = qa.get("exports", {}).get(extension, {})
                if raw is None or not isinstance(record, dict) or record.get("sha256") != sha256(raw):
                    raise WorkbenchError("Agent output requires matching export QA for every adopted format")
            if not result["changed_files"]:
                raise WorkbenchError("Fulfilled requests must identify actual changed source files")
            _refresh_document(target, required=True)
            with self.lock, ledger_file_lock(self.storage):
                registry = self._read_registry()
                current = next(item for item in registry["jobs"] if item["id"] == job_id)
                if current["cancel_requested"] or self._closed:
                    raise InterruptedError("Cancelled before recording Agent application")
                if len(registry["attempts"]) >= MAX_ATTEMPTS:
                    raise WorkbenchError("This project already has 100 registered attempts")
                # Persist the exact confirmed subset before the ledger commit
                # so restart recovery cannot apply still-unfulfilled notes.
                current.update(fulfilled_request_ids=fulfilled, agent_request_ids=pending,
                               agent_requests=[{"request_id": item, "reason": result["validation"]} for item in pending])
                _atomic_json(self.registry_path, registry)
                event = _helpers().record_requests(app.root, target, fulfilled, changed_files=result["changed_files"],
                    validation=result["validation"])
                document_warning = _refresh_document(target)
                relative = str(target.relative_to(self.project))
                target_id = "attempt-" + sha256(relative.encode())[:16]
                source_record = registry["attempts"].get(job["source_attempt_id"], {})
                family = source_record.get("family_name", source_record.get("display_name", app.root.name))
                ordinal = 1 + sum(record.get("family_name") == family for record in registry["attempts"].values())
                registry["attempts"][target_id] = {"path": relative, "registered_at": timestamp(),
                    "family_name": family, "display_name": f"{family} · Agent preview {ordinal}"}
                current.update(status="succeeded", phase="complete", target_attempt_id=target_id, updated_at=timestamp(),
                               outcome_id=event["id"], error=None,
                               message="Agent preview ready; inspect it before accepting." + (" Some requests remain pending." if pending else ""))
                if document_warning:
                    current["document_warning"] = document_warning
                _atomic_json(self.registry_path, registry)
        except InterruptedError as exc:
            self._update_job(job_id, status="cancelled", phase="cancelled", error=None, message=str(exc))
        except Exception as exc:
            with self.lock, ledger_file_lock(self.storage):
                registry = self._read_registry()
                current = next(item for item in registry["jobs"] if item["id"] == job_id)
                if not self._recover_committed(registry, current):
                    current.update(status="failed", phase="failed", error=str(exc)[:8000], updated_at=timestamp(),
                                   message="Agent job failed. Reviewed outputs stay intact and uncommitted requests remain pending.")
                _atomic_json(self.registry_path, registry)
        finally:
            if process is not None and process.poll() is None:
                self._stop_process(process)
            run_lock.__exit__(None, None, None)

    def _finish_handoff(self, job_id):
        # Handoff has no renderer, but it still completes a real queued job.
        # Serialize its terminal transition with cross-process cancellation.
        with self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            current = next(item for item in registry["jobs"] if item["id"] == job_id)
            if current["cancel_requested"] or self._closed:
                current.update(status="cancelled", phase="cancelled", updated_at=timestamp(), error=None,
                               message="Cancelled before Agent handoff. Saved requests remain pending.")
            else:
                current.update(status="succeeded", phase="agent_handoff", updated_at=timestamp(), error=None,
                               message="Saved instructions need an active Agent to edit the plotting source. No requests were marked applied.")
            _atomic_json(self.registry_path, registry)

    @staticmethod
    def _stop_process(process):
        if process.poll() is not None:
            return
        if os.name == "nt":
            process.terminate()
        else:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                process.kill()
            else:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.communicate(timeout=2)

    def cancel_job(self, job_id):
        with self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            job = next((item for item in registry["jobs"] if item["id"] == job_id), None)
            if job is None:
                raise WorkbenchError("Unknown job")
            if job["status"] in ACTIVE_STATUSES:
                if job.get("backend") == "session":
                    if not self._recover_committed(registry, job):
                        job.update(status="cancelled", phase="cancelled", cancel_requested=True,
                                   message="Original-conversation job cancelled; saved edits remain pending.", updated_at=timestamp())
                else:
                    job.update(cancel_requested=True, message="Cancellation requested; stopping the owned worker.", updated_at=timestamp())
                _atomic_json(self.registry_path, registry)
            return {"job": copy.deepcopy(job)}

    def accept(self, validation, attempt_id=None):
        app = self.attempt_app(attempt_id)
        self._sources_in_scope(app.state())
        acceptance = _helpers().accept_attempt(app.root, validation=validation)
        return {"acceptance": acceptance, "attempt": self.get_attempt(attempt_id), "state": self.state()}

    def restore(self, attempt_id=None):
        app = self.attempt_app(attempt_id)
        if app.root == self.project:
            raise WorkbenchError("Choose the containing project directory with --project-dir to restore a separate fresh attempt")
        self._sources_in_scope(app.state())
        target_parent = self.storage / "attempts"
        if target_parent.is_symlink():
            raise WorkbenchError("Attempt storage must not be a symlink")
        target_parent.mkdir(exist_ok=True)
        target = target_parent / ("restored-" + uuid.uuid4().hex)
        event = _helpers().restore_attempt(app.root, target)
        write_figure_info(target, self.get_attempt(attempt_id)["name"])
        attempt = self.register_attempt(target)
        with self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            source_record = registry["attempts"].get(attempt_id or self.current_attempt_id, {})
            family = source_record.get("family_name", source_record.get("display_name", app.root.name))
            record = registry["attempts"][attempt["id"]]
            record.update(family_name=family, display_name=f"{family} · restored")
            _atomic_json(self.registry_path, registry)
        attempt = self.get_attempt(attempt["id"])
        return {"attempt": attempt, "state": self.state(), "restoration": event}

    def record_outcome(self, source_attempt_id, target_attempt_id, request_ids, changed_files, validation):
        source_attempt_id = source_attempt_id or self.current_attempt_id
        source = self.attempt_app(source_attempt_id)
        target = self.attempt_app(target_attempt_id)
        # Manual receipts cannot consume requests already owned by a submitted
        # job. Serialize the check and receipt with every job publication.
        with self.lock, ledger_file_lock(self.storage):
            registry = self._read_registry()
            source_state = source.state()
            self._sources_in_scope(source_state)
            self._sources_in_scope(target.state())
            _, selected, _ = _helpers().selected_requests(source, source_state, request_ids)
            ids = [item["id"] for item in selected]
            for job in registry["jobs"]:
                if (job.get("status") in ACTIVE_STATUSES
                        and job.get("source_attempt_id") == source_attempt_id
                        and set(ids).intersection(job.get("request_ids", []))):
                    completion = ("Use complete_session_job for its claimed batch" if job.get("backend") == "session"
                                  else "Let its active worker finish, or cancel the job before recording manually")
                    raise WorkbenchError("Saved requests belong to active job " + job["id"] + ". " + completion + ".")
            event = _helpers().record_requests(source.root, target.root, ids,
                                              changed_files=changed_files, validation=validation)
        document_warning = _refresh_document(target.root)
        result = {"outcome": event, "attempt": self.get_attempt(target_attempt_id)}
        if document_warning:
            result["document_warning"] = document_warning
        return result

    def close(self):
        self._closed = True
        for job_id, thread in list(self._threads.items()):
            if thread.is_alive():
                self.cancel_job(job_id)
        deadline = time.monotonic() + 5
        for thread in list(self._threads.values()):
            thread.join(max(0, deadline - time.monotonic()))


def _render_worker(plan_path):
    """Internal fixed command, not a public user-script execution interface."""
    helper = _helpers()
    plan_path = Path(plan_path).resolve()
    plan = safe_json(helper.read_regular(plan_path))
    source_app, state = helper.verified_attempt(plan["from_attempt"], require_elements=True)
    renderer = Path(__file__).with_name("render.py").resolve()
    if (state["version"] != plan["version"] or state["input"].get("source_script") != str(renderer)
            or state["version"].get("source_script_sha256") != sha256(helper.read_regular(renderer))):
        raise WorkbenchError("Core source or figure changed before rendering")
    spec_path = plan_path.parent / "plot-spec.json"
    if sha256(helper.read_regular(spec_path)) != plan["spec_sha256"]:
        raise WorkbenchError("Prepared specification changed before rendering")
    import render as core_renderer
    original_path = Path(state["input"]["spec_file"])
    original = safe_json(helper.read_regular(original_path))
    resolved, _ = core_renderer.resolve_spec(original, spec_path=original_path)
    canonical = json.dumps(resolved, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
    if sha256(canonical) != state["version"].get("spec_sha256"):
        raise WorkbenchError("Resolved specification differs from the reviewed figure version")
    spec = safe_json(helper.read_regular(spec_path))
    # Resolve a previously adopted report relative to its original spec rather
    # than interpreting it under the new attempt directory.
    adoption = spec.get("statistics", {}).get("analysis")
    if isinstance(adoption, dict) and isinstance(adoption.get("results_file"), str):
        report = Path(adoption["results_file"])
        if not report.is_absolute():
            adoption["results_file"] = str((original_path.parent / report).resolve())
            helper.write_json(spec_path, spec)
    core_renderer.render(Path(state["input"]["data_file"]), spec, plan_path.parent,
                         spec_path=spec_path, track=state.get("track") or None)
    plan.update(status="rendered", rendered=True, spec_sha256=sha256(helper.read_regular(spec_path)))
    helper.write_json(plan_path, plan)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("capabilities", "attempts", "state", "requests", "prepare", "submit", "jobs", "cancel", "_render-worker"))
    parser.add_argument("--project-dir", type=Path, help="Explicit directory containing registered attempts and source inputs")
    parser.add_argument("--figure-dir", type=Path)
    parser.add_argument("--request-ids", nargs="+")
    parser.add_argument("--job-id")
    parser.add_argument("--plan", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.operation == "_render-worker":
        try:
            _render_worker(args.plan)
        except Exception as exc:
            parser.exit(1, str(exc) + "\n")
        return
    if args.project_dir is None:
        parser.error("--project-dir is required")
    service = None
    try:
        service = FigureService(args.project_dir, args.figure_dir)
        if args.operation == "capabilities":
            result = service.capabilities()
        elif args.operation == "attempts":
            result = service.list_attempts()
        elif args.operation == "state":
            result = service.state()
        elif args.operation == "requests":
            result = service.list_requests()
        elif args.operation in {"prepare", "submit"}:
            method = service.prepare_edits if args.operation == "prepare" else service.submit_job
            result = method(service.state()["version"], args.request_ids)
            if args.operation == "submit":
                # A CLI process owns its job until completion; do not silently
                # orphan a background renderer when the parent command exits.
                job_id = result["job"]["id"]
                while result["job"]["status"] in ACTIVE_STATUSES:
                    time.sleep(.1)
                    result = service.get_job(job_id)
        elif args.operation == "cancel":
            result = service.cancel_job(args.job_id)
        else:
            result = service.get_job(args.job_id) if args.job_id else service.list_jobs()
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (OSError, WorkbenchError, ValueError) as exc:
        parser.exit(2, str(exc) + "\n")
    except KeyboardInterrupt:
        parser.exit(130, "Cancelled; the owned renderer is stopping and uncommitted requests remain pending.\n")
    finally:
        if service is not None:
            service.close()


if __name__ == "__main__":
    main()
