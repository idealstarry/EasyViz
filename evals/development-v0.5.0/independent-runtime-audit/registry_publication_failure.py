"""Reproduce post-history service registry publication failure without production edits."""
from pathlib import Path
import json
import shutil
import sys
import time
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "skills/easyviz/scripts"))
import figure_service
from figure_service import FigureService
import render

root = Path(__file__).resolve().parent / "registry-publication-fixture"
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
item = service.app.change({"version": version, "selector": {"category": "A"},
    "property": "color", "value": "#AA22BB", "instruction": "Use purple for A."})["request"]
original_atomic = figure_service._atomic_json
failed = False

def fail_success_publication(path, value):
    global failed
    if not failed and path == service.registry_path and any(job.get("phase") == "complete" for job in value.get("jobs", [])):
        failed = True
        raise OSError("Injected atomic registry publication failure")
    return original_atomic(path, value)

try:
    with patch.object(figure_service, "_atomic_json", side_effect=fail_success_publication):
        submitted = service.submit_job(version, [item["id"]])["job"]
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            job = service.get_job(submitted["id"])["job"]
            if job["status"] not in figure_service.ACTIVE_STATUSES:
                break
            time.sleep(.03)
    try:
        retry = service.submit_job(version, [item["id"]])
    except Exception as exc:
        retry = {"error": str(exc)}
    result = {"job": job, "source_request": service.app.ledger()["requests"][0],
              "registered_attempts": service.list_attempts(), "retry": retry,
              "generated_attempt": str(service.storage / "attempts" / job["id"])}
    (root.parent / "registry-publication-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"job_status": job["status"], "target_attempt_id": job["target_attempt_id"],
                      "source_request_status": result["source_request"]["status"],
                      "registered_attempt_count": len(result["registered_attempts"]["attempts"]),
                      "retry": retry}, indent=2))
finally:
    service.close()
