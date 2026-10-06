"""Fixed local Codex worker contract for explicitly submitted EasyViz edits.

The workbench owns the queue and validates outputs. This module only prepares a
fresh writable workspace and starts the installed CLI; it exposes no shell or
arbitrary executable option and never changes the host's configuration.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from figure_workbench import (WorkbenchError, safe_json, make_figure_info,
                              read_figure_info, validate_figure_name)

AGENT_TIMEOUT_SECONDS = 600
MAX_WORKER_LOG_BYTES = 8 * 1024 * 1024
MAX_RESULT_BYTES = 64 * 1024
RESULT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["fulfilled_request_ids", "unfulfilled_request_ids", "changed_files", "validation"],
    "properties": {
        "fulfilled_request_ids": {"type": "array", "items": {"type": "string"}},
        "unfulfilled_request_ids": {"type": "array", "items": {"type": "string"}},
        "changed_files": {"type": "array", "items": {"type": "string"}},
        "validation": {"type": "string"},
    },
}


def worker_error(stderr):
    """Keep detailed owner logs on disk and show one actionable failure."""
    restricted = ("Operation not permitted" in stderr or "readonly database" in stderr
                  or "read-only database" in stderr)
    if restricted:
        return ("Codex could not start in this restricted environment. Open the independent workbench "
                "from a normal terminal and retry. Your figure and requests are unchanged."), True
    lines = [line.strip() for line in stderr.splitlines() if line.strip()
             and not line.startswith("WARNING:") and not re.match(r"\d{4}-\d{2}-\d{2}T", line)]
    main = next((line for line in reversed(lines) if line.lower().startswith("error:")), lines[-1] if lines else "Codex exited before completing the edit batch.")
    return main[:500], False


def codex_binary():
    """Resolve only the known backend; user payloads cannot supply a command."""
    executable = shutil.which("codex")
    return str(Path(executable).resolve()) if executable else None


def verify_backend():
    executable = codex_binary()
    if executable is None:
        raise WorkbenchError("Codex CLI is not installed or available to this local service")
    try:
        result = subprocess.run([executable, "exec", "--help"], capture_output=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkbenchError("Could not inspect the installed Codex CLI") from exc
    help_text = result.stdout.decode("utf-8", errors="replace")
    required = ("--json", "--output-schema", "--output-last-message", "--sandbox", "--ephemeral")
    if result.returncode or not all(flag in help_text for flag in required):
        raise WorkbenchError("Installed Codex CLI lacks the required bounded headless worker options")
    return executable


def adopted_formats(source_app, state):
    """Keep every verified export even when descriptive settings are edited."""
    supported = {"svg", "pdf", "png", "tiff"}
    formats = {extension for extension in supported if "panel." + extension in state["files"]}
    settings = safe_json(source_app.read_file("settings.json") or b"{}")
    declared = settings.get("formats") if isinstance(settings, dict) else None
    if declared is not None:
        if (not isinstance(declared, list) or
                any(not isinstance(extension, str) or extension not in supported for extension in declared)):
            raise WorkbenchError("Reviewed attempt declares unsupported export formats")
        formats.update(declared)
    qa_bytes = source_app.read_file("qa.json")
    if qa_bytes:
        # Import lazily: figure_service imports this module before initializing
        # the request helpers, and both execution paths share the same QA check.
        from apply_figure_requests import verify_qa_binding
        verify_qa_binding(source_app, qa_bytes, "adopting the original export formats")
        qa = safe_json(qa_bytes)
        formats.update(extension for extension, record in qa.get("exports", {}).items()
                       if extension in supported and isinstance(record, dict) and record.get("sha256"))
    if "svg" not in formats:
        raise WorkbenchError("Figure edits require an adopted SVG export")
    return [extension for extension in ("svg", "pdf", "png", "tiff") if extension in formats]


def prepare_workspace(source_app, state, target: Path, requests, *, read_regular):
    """Copy inputs and editable source, keeping the reviewed attempt immutable.

    Auxiliary statistical reports keep their adopted original bytes and paths.
    The sandbox's sole writable working root is this fresh target, so the Agent
    adapts copied source instead of changing the reviewed project inputs.
    """
    target.mkdir()
    inputs_dir = target / "inputs"
    inputs_dir.mkdir()
    original_inputs = state["input"]
    worker_inputs = dict(original_inputs)
    source = Path(original_inputs["source_script"])
    core = Path(__file__).with_name("render.py").resolve()
    for role in ("data_file", "spec_file", "source_script"):
        path = Path(original_inputs[role])
        if role == "source_script" and path.resolve() == core:
            worker_inputs[role] = str(core)
            continue
        name = role + path.suffix
        copied = (target / "plot.py") if role == "source_script" else inputs_dir / name
        copied.write_bytes(read_regular(path))
        worker_inputs[role] = str(copied)
    for name in ("caption.md", "figure-caption.md", "analysis-caption.md"):
        caption = source_app.root / name
        if caption.is_file() and not caption.is_symlink():
            (target / name).write_bytes(read_regular(caption))
    figure_name = validate_figure_name(state["figure_name"])
    figure_info = read_figure_info(source_app.root) or make_figure_info(figure_name)
    if figure_info["display_name"] != figure_name:
        raise WorkbenchError("Figure display name changed before the edit workspace was prepared")
    (target / "figure-info.json").write_text(json.dumps(figure_info, ensure_ascii=False, indent=2) + "\n")
    formats = adopted_formats(source_app, state)
    context = {"schema_version": 1, "figure_name": figure_name,
               "source_attempt": str(source_app.root), "version": state["version"],
               "track": state.get("track"), "requests": requests, "original_input": original_inputs,
               "worker_input": worker_inputs, "elements": state["elements"], "panel": state["panel"],
               "formats": formats, "output_directory": str(target), "python": sys.executable}
    (target / "agent-context.json").write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n")
    (target / "agent-result-schema.json").write_text(json.dumps(RESULT_SCHEMA) + "\n")
    skill = Path(__file__).resolve().parent.parent / "SKILL.md"
    reviewer = skill.parent.parent / "easyviz-figure-reviewer" / "SKILL.md"
    prompt = f"""Apply only the user's saved EasyViz edit requests in agent-context.json.
This is a dedicated worker; the reviewed attempt and its source files must stay intact.
Read the actual EasyViz skill at {skill} and reviewer guidance at {reviewer}.
Use the existing {state.get('track') or 'scientific figure'} track, adopted design and statistical choices.
Read agent-context.json for exact request IDs, selected elements, region coordinates,
physical panel dimensions, source provenance, interpreter and required export formats.
The figure_name is the user's workbench display name, preserved in figure-info.json.
Keep that metadata intact; do not add it as an in-image SVG title or alter scientific labels.
Your writable directory is {target}. Edit copied source/specification here only.
Preserve all primary/auxiliary data, all observations, analysis reports, statistical
tests, sample counts and adopted P values. Styling must not rerun statistical analysis.
Use worker_input paths; keep auxiliary input bytes unchanged and their adopted hashes.
For the core renderer, edit the copied spec and invoke the installed renderer with
the specified Python, data, spec, output directory and track. For custom source,
adapt plot.py to render into this directory, using actual EasyViz export/element/
handoff helpers so inputs, sources and exports are bound to the rendered attempt.
Produce fresh panel.svg and each format listed in context, current settings, a
real semantic elements.json and actual hash-bound passing qa.json. Custom
source also needs its actual consumed-input handoff.json. Register selectable
artists before exporting SVG; the service must pack a valid editable .ev document
before publishing the result. Preserve the copied caption and update only its
requested styling description; keep statistical descriptions unchanged.
Inspect the actual generated image at final size. If only SVG export is requested,
rasterize panel.svg into a separate review-preview.png with PyMuPDF and inspect
that bitmap; keep the requested canonical exports SVG. For example, with the
context interpreter: import fitz; document = fitz.open('panel.svg');
pdf = fitz.open('pdf', document.convert_to_pdf());
pdf[0].get_pixmap(matrix=fitz.Matrix(2, 2)).save('review-preview.png').
The original preview is
{source_app.root / 'panel.svg'}. Resolve requested changes without inventing data or
claiming an unimplemented instruction. Do not copy original exports as new output.
Do not accept the design, change original requests.json or call another Agent worker.
The service records outcomes after independent source/export validation.
Return only the output-schema JSON. Partition every submitted request ID into
fulfilled_request_ids or unfulfilled_request_ids. List changed_files relative to
this directory and describe actual rendering and image inspection in validation.
If a request cannot be fulfilled, keep it unfulfilled and state why. A text-only
success is insufficient; no request will be applied without real fresh exports.
"""
    return context, prompt


def start_worker(target, executable, prompt, stdout, stderr):
    """Launch the fixed supported CLI with a fresh attempt as its writable root."""
    command = [executable, "exec", "--json", "--ephemeral", "--sandbox", "workspace-write",
               "-c", 'approval_policy="never"', "--skip-git-repo-check", "--color", "never",
               "--output-schema", str(target / "agent-result-schema.json"),
               "--output-last-message", str(target / "agent-result.json"), "-C", str(target), "-"]
    # A pipe write can block before cancellation/timeout ownership begins when
    # a startup failure never reads a large request batch. A file-backed stdin
    # lets the CLI read at its own pace while the service immediately polls it.
    prompt_path = target / "agent-prompt.txt"
    with prompt_path.open("xb") as stream:
        stream.write(prompt.encode())
    with prompt_path.open("rb") as stdin:
        return subprocess.Popen(command, stdin=stdin, stdout=stdout, stderr=stderr,
                                start_new_session=os.name != "nt")


def read_result(target: Path, request_ids):
    result_file = target / "agent-result.json"
    if result_file.is_symlink() or not result_file.is_file() or result_file.stat().st_size > MAX_RESULT_BYTES:
        raise WorkbenchError("Agent did not produce a bounded structured edit result")
    result = safe_json(result_file.read_bytes())
    if not isinstance(result, dict) or set(result) != set(RESULT_SCHEMA["required"]):
        raise WorkbenchError("Agent result does not match the edit-outcome schema")
    fulfilled, unfulfilled = result["fulfilled_request_ids"], result["unfulfilled_request_ids"]
    for ids in (fulfilled, unfulfilled):
        if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids) or len(ids) != len(set(ids)):
            raise WorkbenchError("Agent result request IDs must be unique strings")
    if set(fulfilled) & set(unfulfilled) or set(fulfilled + unfulfilled) != set(request_ids):
        raise WorkbenchError("Agent must account for every submitted request without inventing IDs")
    changed = result["changed_files"]
    if (not isinstance(changed, list) or not all(isinstance(item, str) for item in changed)
            or len(changed) > 100 or len(set(changed)) != len(changed)):
        raise WorkbenchError("Agent changed_files must be a bounded list of unique relative files")
    for name in changed:
        if (not isinstance(name, str) or not name or Path(name).is_absolute() or ".." in Path(name).parts
                or (target / name).is_symlink() or not (target / name).is_file()
                or not (target / name).resolve().is_relative_to(target)):
            raise WorkbenchError("Agent changed files must remain inside its fresh attempt")
    validation = result["validation"]
    if not isinstance(validation, str) or not validation.strip() or len(validation) > 8000:
        raise WorkbenchError("Agent must describe actual export and visual validation")
    return result
