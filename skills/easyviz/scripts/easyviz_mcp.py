#!/usr/bin/env python3
"""Optional project-scoped EasyViz MCP server using the official Python SDK.

Install requirements-mcp.txt in the Python environment used by this command.
Launch: python easyviz_mcp.py --project-dir PROJECT --figure-dir ATTEMPT
The adapter uses stdio; protocol output is never mixed with renderer logging.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import sys
import threading
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figure_service import FigureService
from figure_workbench import WorkbenchError

TESTED_SDK_VERSION = "2.3.0"


def create_mcp(service: FigureService):
    """Build the optional SDK transport around the same local service contract."""
    try:
        installed = version("mcp")
    except PackageNotFoundError:
        raise WorkbenchError("Optional MCP SDK is missing. Install requirements-mcp.txt in this Python environment.") from None
    if installed != TESTED_SDK_VERSION:
        raise WorkbenchError(f"This adapter was tested with mcp=={TESTED_SDK_VERSION}; install requirements-mcp.txt (found {installed}).")
    from mcp.server import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError
    from mcp.types import ToolAnnotations

    @asynccontextmanager
    async def lifespan(_server):
        try:
            yield
        finally:
            service.close()

    server = MCPServer("EasyViz", title="EasyViz local figures", lifespan=lifespan,
        instructions="Inspect capabilities and the current attempt first. Connect the conversation that first invoked EasyViz with connect_session; keep its credential private and use bounded wait_for_submission calls while that same Agent is active. A claim means received only: report_session_progress as actual editing, rendering and review begin. Implement edits in copied source/specification and complete_session_job only after fresh exports pass QA and visual review. MCP alone cannot wake an idle chat. Optional Codex Desktop scheduled checks require actual successful native host creation before register_session_trigger; registration metadata is not execution verification or instant delivery. A separately authorized dedicated Codex worker creates new sessions; never use it as a silent fallback.")
    read_only = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)
    local_write = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False)

    def call(operation, *args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except (WorkbenchError, OSError, ValueError) as exc:
            raise ToolError(str(exc)) from exc

    def selected(attempt_id):
        # A configured initial figure must not hide a newer browser-selected
        # attempt. Explicit IDs always override the descriptive review focus.
        return attempt_id or service.review_attempt_id() or service.current_attempt_id

    @server.tool(annotations=read_only)
    def capabilities(attempt_id: str | None = None) -> dict[str, Any]:
        """Report project scope, automatic preview support, job limits and Agent handoff capability."""
        return call(service.capabilities, selected(attempt_id))

    @server.tool(annotations=read_only)
    def list_attempts() -> dict[str, Any]:
        """List only registered attempts in the authorized project, including exact export/preview links."""
        return call(service.list_attempts)

    @server.tool(annotations=read_only)
    def get_attempt(attempt_id: str | None = None) -> dict[str, Any]:
        """Get a registered attempt's physical size, source/export version and local file links."""
        attempt_id = selected(attempt_id)
        result = call(service.get_attempt, attempt_id)
        app = call(service.attempt_app, attempt_id)
        state = app.state()
        result["input"] = state["input"]
        result["elements"] = state["elements"]
        result["exports"] = {ext: str(app.root / ("panel." + ext)) for ext in result["files"]}
        result["preview_resource"] = f"easyviz://attempt/{result['id']}/panel.svg"
        return result

    @server.tool(annotations=local_write)
    def register_attempt(figure_dir: str) -> dict[str, Any]:
        """Register an existing attempt inside --project-dir; never execute its plotting script."""
        return call(service.register_attempt, figure_dir)

    @server.tool(annotations=local_write)
    def rename_attempt(name: str, attempt_id: str | None = None) -> dict[str, Any]:
        """Save a figure's display name for the workbench and Agent; retain paths and scientific exports."""
        return call(service.rename_attempt, name, selected(attempt_id))

    @server.tool(annotations=read_only)
    def list_requests(attempt_id: str | None = None) -> dict[str, Any]:
        """Read saved, numbered edit requests and their current-version binding without copying prompts."""
        return call(service.list_requests, selected(attempt_id))

    @server.tool(annotations=read_only)
    def prepare_edits(version: dict[str, str], request_ids: list[str] | None = None,
                      attempt_id: str | None = None) -> dict[str, Any]:
        """Classify pending requests into automatic cosmetic edits and active-Agent source edits. No files are changed."""
        return call(service.prepare_edits, version, request_ids, selected(attempt_id))

    @server.tool(annotations=local_write)
    def render_attempt(version: dict[str, str], request_ids: list[str] | None = None,
                       attempt_id: str | None = None) -> dict[str, Any]:
        """Submit one bounded preview job using only the unchanged installed core renderer. Poll get_job; custom requests remain Agent handoff."""
        return call(service.submit_job, version, request_ids, selected(attempt_id))

    @server.tool(annotations=read_only)
    def agent_status() -> dict[str, Any]:
        """Inspect the original-conversation lease or opt-in worker without starting inference; never return credentials."""
        return call(service.agent_status)

    @server.tool(annotations=local_write)
    def connect_session(owner_session_id: str, host: str = "codex", lease_seconds: int = 300) -> dict[str, Any]:
        """Bind this active original conversation for same-session edits. Keep returned token private; no model/process is started and no idle chat is woken."""
        return call(service.connect_session, owner_session_id, host, lease_seconds)

    @server.tool(annotations=local_write)
    def renew_same_session(owner_session_id: str, connection_token: str) -> dict[str, Any]:
        """Refresh the still-live original conversation connection using its existing private credential; never take over another owner or revive expired credentials."""
        return call(service.renew_same_session, owner_session_id, connection_token)

    @server.tool(annotations=local_write)
    def register_session_trigger(owner_session_id: str, connection_token: str, automation_id: str,
                                 interval_seconds: int, expires_at: float) -> dict[str, Any]:
        """Register an actual native Codex Desktop heartbeat ONLY after its host creation succeeded. Supply real automation ID, 60..3600-second interval and Unix expiry within 24h. This records owner registration, not verified execution or instant/portable MCP wake."""
        return call(service.register_session_trigger, owner_session_id, connection_token,
                    automation_id, interval_seconds, expires_at)

    @server.tool(annotations=local_write)
    def disable_session_trigger(owner_session_id: str, connection_token: str) -> dict[str, Any]:
        """Disable native automatic-check queue metadata. Separately stop the actual host heartbeat with its native tool; this server cannot manage host automation."""
        return call(service.disable_session_trigger, owner_session_id, connection_token)

    @server.tool(annotations=local_write)
    async def wait_for_submission(owner_session_id: str, connection_token: str,
                                  timeout_seconds: float = 30) -> dict[str, Any]:
        """Refresh this original conversation's lease and atomically claim a submitted batch; wait 0 to 45 seconds. Resume plotting in this same conversation."""
        stopped = threading.Event()
        worker = asyncio.create_task(asyncio.to_thread(call, service.wait_for_submission,
            owner_session_id, connection_token, timeout_seconds, cancellation_event=stopped))
        try:
            return await asyncio.shield(worker)
        except asyncio.CancelledError:
            stopped.set()
            def release_undelivered(done):
                try:
                    result = done.result()
                    job = result.get("job") if isinstance(result, dict) else None
                    if job:
                        service._release_session_claim(owner_session_id, connection_token, job["id"])
                except (Exception, asyncio.CancelledError):
                    # A disconnected/cancelled/failed batch must not be revived.
                    pass
            worker.add_done_callback(release_undelivered)
            try:
                await asyncio.shield(worker)
            except (Exception, asyncio.CancelledError):
                pass
            raise

    @server.tool(annotations=local_write)
    def report_session_progress(owner_session_id: str, connection_token: str, job_id: str,
                                phase: str = "editing") -> dict[str, Any]:
        """Report actual editing, rendering and reviewing beginnings in order for this original conversation's claimed batch. Receiving edits alone is not editing progress."""
        return call(service.report_session_progress, owner_session_id, connection_token, job_id, phase)

    @server.tool(annotations=local_write)
    def complete_session_job(owner_session_id: str, connection_token: str, job_id: str,
                             target_attempt_id: str, request_ids: list[str], changed_files: list[str],
                             validation: str) -> dict[str, Any]:
        """Complete this conversation's claimed job only after actual fresh changed exports pass source/QA checks; describe visual review. Omitted requests remain pending."""
        return call(service.complete_session_job, owner_session_id, connection_token, job_id,
                    target_attempt_id, request_ids, changed_files, validation)

    @server.tool(annotations=local_write)
    def disconnect_session(owner_session_id: str, connection_token: str) -> dict[str, Any]:
        """Disconnect the owned original conversation; uncommitted edits stay pending and no other worker is started."""
        return call(service.disconnect_session, owner_session_id, connection_token)

    @server.tool(annotations=local_write)
    def configure_agent(backend: str = "codex", enabled: bool = True) -> dict[str, Any]:
        """Connect/disconnect the installed local Codex worker only for the explicitly authorized project. Requires user intent; never edit host global configuration."""
        return call(service.configure_agent, backend, enabled)

    @server.tool(annotations=local_write)
    def submit_agent_job(version: dict[str, str], request_ids: list[str] | None = None,
                         attempt_id: str | None = None) -> dict[str, Any]:
        """Queue saved edits for the connected original conversation, or an explicitly authorized separate worker. A same-session Agent receives them through wait_for_submission, never a new process."""
        return call(service.submit_agent_job, version, request_ids, selected(attempt_id))

    @server.tool(annotations=read_only)
    def list_jobs() -> dict[str, Any]:
        """Discover workbench-submitted jobs and their target/source attempt IDs in this project."""
        return call(service.list_jobs)

    @server.tool(annotations=read_only)
    def get_job(job_id: str) -> dict[str, Any]:
        """Get a preview job's actual state, phase, errors, pending Agent requests and fresh target attempt ID."""
        return call(service.get_job, job_id)

    @server.tool(annotations=local_write)
    def cancel_job(job_id: str) -> dict[str, Any]:
        """Cancel a queued/running owned job without marking uncommitted requests applied."""
        return call(service.cancel_job, job_id)

    @server.tool(annotations=local_write)
    def record_outcome(source_attempt_id: str, target_attempt_id: str, request_ids: list[str],
                       changed_files: list[str], validation: str) -> dict[str, Any]:
        """Record Agent-applied requests only after a separately registered fresh attempt passes actual export/source QA. State what was visually checked."""
        return call(service.record_outcome, source_attempt_id, target_attempt_id, request_ids, changed_files, validation)

    @server.tool(annotations=local_write)
    def accept_attempt(validation: str, attempt_id: str | None = None) -> dict[str, Any]:
        """Capture an immutable accepted source/spec/data/export snapshot after user or Agent visual review."""
        return call(service.accept, validation, selected(attempt_id))

    @server.tool(annotations=local_write)
    def restore_attempt(attempt_id: str | None = None) -> dict[str, Any]:
        """Restore an accepted snapshot to a fresh attempt; preserve the original and its history."""
        return call(service.restore, selected(attempt_id))

    @server.resource("easyviz://attempt/{attempt_id}/panel.svg", mime_type="image/svg+xml")
    def preview(attempt_id: str) -> bytes:
        """Return only a registered, sanitized SVG preview, with no arbitrary file access."""
        from figure_workbench import read_svg, sanitized_svg
        app = call(service.attempt_app, attempt_id)
        raw = call(app.read_file, "panel.svg", required=True)
        root, _, _ = read_svg(raw)
        return sanitized_svg(root)

    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, required=True, help="Explicit directory containing attempts and their declared source inputs")
    parser.add_argument("--figure-dir", type=Path, help="Initial registered attempt (optional; register_attempt can select one later)")
    args = parser.parse_args()
    service = None
    try:
        service = FigureService(args.project_dir, args.figure_dir)
        create_mcp(service).run(transport="stdio")
    except (WorkbenchError, OSError, ValueError) as exc:
        parser.exit(2, str(exc) + "\n")
    finally:
        if service is not None:
            service.close()


if __name__ == "__main__":
    main()
