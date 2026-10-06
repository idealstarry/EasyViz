"""Actual separate-process lock/cancel checks and non-execution of custom source."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import threading
import time
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "skills/easyviz/scripts"))
import figure_service
from figure_service import FigureService
from figure_workbench import WorkbenchError

def wait(service, job_id):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        job = service.get_job(job_id)["job"]
        if job["status"] not in figure_service.ACTIVE_STATUSES:
            return job
        time.sleep(.03)
    raise RuntimeError("Owned job did not complete")

if len(sys.argv) > 1 and sys.argv[1] == "owner":
    root = Path(sys.argv[2])
    service = FigureService(root, root / "attempt-01")
    items = service.app.ledger()["requests"]
    started = threading.Event()
    real_popen = subprocess.Popen
    def slow(*args, **kwargs):
        process = real_popen([sys.executable, "-c", "import time; time.sleep(20)"], **kwargs)
        started.set()
        return process
    try:
        with patch.object(figure_service.subprocess, "Popen", side_effect=slow):
            job = service.submit_job(service.state()["version"], [items[0]["id"]])["job"]
            if not started.wait(5):
                raise RuntimeError("Owned subprocess never started")
            print(json.dumps({"job_id": job["id"]}), flush=True)
            print(json.dumps(wait(service, job["id"])), flush=True)
    finally:
        service.close()
    sys.exit(0)

import render
root = Path(__file__).resolve().parent / "crossprocess-fixture"
if root.exists():
    shutil.rmtree(root)
root.mkdir()
data = root / "data.csv"
data.write_text("x,y,group\n1,2,A\n2,3,A\n3,4,A\n1,4,B\n2,5,B\n3,6,B\n")
spec = {"chart": "scatter", "fields": {"x": "x", "y": "y", "group": "group"},
        "labels": {"x": "X", "y": "Y"},
        "layout": {"width_mm": 120, "height_mm": 90, "font": "DejaVu Sans", "font_size_pt": 8},
        "formats": ["svg", "pdf", "png"], "options": {"point_area_pt2": 12}, "seed": 41}
spec_path = root / "spec.json"
spec_path.write_text(json.dumps(spec))
attempt = root / "attempt-01"
render.render(data, spec, attempt, spec_path=spec_path, track="create")
service = FigureService(root, attempt)
version = service.state()["version"]
items = [service.app.change({"version": version, "selector": {"category": "A"},
    "property": "color", "value": color, "instruction": "Change A cosmetic color."})["request"]
         for color in ("#AA22BB", "#22AA44")]
service.close()
owner = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "owner", str(root)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
service = None
try:
    job_id = json.loads(owner.stdout.readline())["job_id"]
    service = FigureService(root, attempt)
    before = service.get_job(job_id)["job"]
    try:
        service.submit_job(version, [items[1]["id"]])
        overlapping = "Unexpectedly allowed"
    except WorkbenchError as exc:
        overlapping = str(exc)
    cancel = service.cancel_job(job_id)["job"]
    final = wait(service, job_id)
    stdout, stderr = owner.communicate(timeout=5)
    result = {"owner_pid": before["owner_pid"], "observer_pid": __import__("os").getpid(),
              "status_after_second_process_open": before["status"], "overlap_rejected": overlapping,
              "cancellation_requested": cancel["cancel_requested"], "final_status": final["status"],
              "target_attempt_id": final["target_attempt_id"], "owner_exit": owner.returncode,
              "source_statuses": [item["status"] for item in service.app.ledger()["requests"]],
              "registered_attempt_count": len(service.list_attempts()["attempts"]), "owner_stderr": stderr}
    # Declare an authored source with a marker side effect, but never invoke it.
    author = root / "author.py"
    marker = root / "author-executed.txt"
    author.write_text("from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('executed')\n")
    manifest_path = attempt / "elements.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["input"]["source_script"] = str(author)
    manifest["version"]["source_script_sha256"] = hashlib.sha256(author.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    current = service.state()["version"]
    note = service.app.change({"version": current, "selector": {"category": "A"},
        "property": "color", "value": "#7755AA", "instruction": "Custom code should be handled by Agent."})["request"]
    handoff = wait(service, service.submit_job(current, [note["id"]])["job"]["id"])
    result["custom"] = {"phase": handoff["phase"], "target_attempt_id": handoff["target_attempt_id"],
                        "marker_exists": marker.exists(), "source_status": service.app.ledger()["requests"][-1]["status"]}
    (root.parent / "crossprocess-and-custom-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
finally:
    if service is not None:
        service.close()
    if owner.poll() is None:
        owner.kill()
        owner.communicate()
