#!/usr/bin/env python3
"""Optional project-scoped EasyViz MCP server using the official Python SDK.

Install requirements-mcp.txt in the Python environment used by this command.
Launch: python easyviz_mcp.py --project-dir PROJECT --figure-dir ATTEMPT
The adapter uses stdio; protocol output is never mixed with renderer logging.
"""
from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import sys
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
        instructions="Inspect capabilities and the current attempt first. Only cosmetic core jobs run automatically. For custom/region/free-form requests, edit the declared plotting source with the active Agent, render a fresh attempt, inspect its exports and record the outcome. Never claim this server wakes an idle chat or accepts a visual design automatically.")
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
