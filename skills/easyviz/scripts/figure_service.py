#!/usr/bin/env python3
"""Project-scoped figure operations shared by the workbench, CLI and optional MCP.

Only the installed core renderer is launched. Custom source edits are handed to
an active Agent with their original request and source identities intact.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import threading
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figure_workbench import (FigureWorkbench, WorkbenchError, ledger_file_lock,
                              safe_json, sha256, timestamp, MAX_FILE_BYTES)

MAX_JOBS = 32
MAX_ATTEMPTS = 100
RENDER_TIMEOUT_SECONDS = 120
ACTIVE_STATUSES = {"queued", "running"}
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
            ids = job.get("automatic_request_ids", [])
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
        return {"id": attempt_id, "name": record.get("display_name", app.root.name), "path": str(app.root),
                "panel": state["panel"], "version": state["version"], "track": state["track"],
                "source_current": state["source_current"], "accepted": (app.root / "accepted-snapshot/acceptance.json").is_file(),
                "preview_url": base + "/preview.svg?v=" + state["version"]["figure_sha256"],
                "files": {ext: base + "/files/panel." + ext for ext in ("svg", "pdf", "png") if "panel." + ext in state["files"]}}

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
                state["figure_name"] = registry["attempts"].get(self.current_attempt_id, {}).get("display_name", app.root.name)
                if app.comparison and state["comparison"]:
                    relative = str(app.comparison.root.relative_to(self.project))
                    previous_id = "attempt-" + sha256(relative.encode())[:16]
                    state["comparison"]["figure_name"] = registry["attempts"].get(previous_id, {}).get("display_name", app.comparison.root.name)
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
                             and all("panel." + ext in state["files"] for ext in ("svg", "pdf", "png")))
            try:
                self._sources_in_scope(state)
                if supported:
                    spec = safe_json(_helpers().read_regular(state["input"]["spec_file"]))
                    settings = safe_json(app.read_file("settings.json") or b"{}")
                    if isinstance(spec, dict) and "profile" in spec or isinstance(settings, dict) and settings.get("figure_profile"):
                        supported = False
            except WorkbenchError:
                supported = False
            reason = ("Mapped core cosmetic edits can regenerate SVG, PDF and PNG. Other requests go to an active Agent."
                      if supported else "This attempt requires Agent source edits; saved requests remain available without automatic rendering.")
            if app.root == self.project:
                supported = False
                reason = "Choose the containing project directory with --project-dir; new attempts must be outside the reviewed attempt. This scope supports review only."
        return {"schema_version": 1, "project_id": self.project_id, "current_attempt_id": attempt_id or self.current_attempt_id,
                "review_attempt_id": self.review_attempt_id(),
                "preview": {"supported": supported, "properties": list(AUTOMATIC_PROPERTIES), "reason": reason},
                "agent": {"automatic_dispatch": False, "mcp_optional": True, "handoff_supported": True},
                "limits": {"max_active_jobs": 1, "max_jobs": MAX_JOBS, "render_timeout_seconds": self.render_timeout}}

    def list_requests(self, attempt_id=None):
        app = self.attempt_app(attempt_id)
        state = app.state()
        return {"attempt_id": attempt_id or self.current_attempt_id, "version": state["version"], "requests": state["requests"],
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
                   and all("panel." + ext in state["files"] for ext in ("svg", "pdf", "png")))
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
        return {"attempt_id": attempt_id or self.current_attempt_id, "version": version,
                "automatic_request_ids": supported, "agent_requests": agent, "requests": requests,
                "input": state["input"], "panel": state["panel"],
                "message": "Automatic changes are cosmetic and use the verified core source. Agent requests remain pending until fresh exports pass QA and their outcome is recorded."}

    def list_jobs(self):
        with self.lock, ledger_file_lock(self.storage):
            return {"jobs": copy.deepcopy(self._read_registry()["jobs"])}

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
        if self.attempt_app(attempt_id).root == self.project:
            raise WorkbenchError("Choose the containing project directory with --project-dir; new attempts must be outside the reviewed attempt")
        if request_ids is not None:
            if (not isinstance(request_ids, list) or not 1 <= len(request_ids) <= 100
                    or not all(isinstance(item, str) and item for item in request_ids)
                    or len(set(request_ids)) != len(request_ids)):
                raise WorkbenchError("request_ids must contain 1 to 100 unique saved request IDs")
            self.attempt_app(attempt_id).current_state(version)
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
            self._update_job(job_id, phase="rendering", target_path=str(target.relative_to(self.project)),
                             message="Regenerating matching SVG, PDF and PNG exports.")
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
            for extension in ("svg", "pdf", "png"):
                if target_app.read_file("panel." + extension) is None:
                    raise WorkbenchError("Preview requires matching SVG, PDF and PNG exports")
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
                job.update(cancel_requested=True, message="Cancellation requested; stopping the owned renderer.", updated_at=timestamp())
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
        source = self.attempt_app(source_attempt_id)
        target = self.attempt_app(target_attempt_id)
        self._sources_in_scope(source.state())
        self._sources_in_scope(target.state())
        event = _helpers().record_requests(source.root, target.root, request_ids,
                                          changed_files=changed_files, validation=validation)
        return {"outcome": event, "attempt": self.get_attempt(target_attempt_id)}

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
