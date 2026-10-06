"""A project equal to a self-contained core attempt cannot create a child attempt."""
from pathlib import Path
import json
import shutil
import sys
import time

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "skills/easyviz/scripts"))
from figure_service import FigureService, ACTIVE_STATUSES
import render

root = Path(__file__).resolve().parent / "self-scoped-fixture"
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
render.render(data, spec, root, spec_path=spec_path, track="create")
service = FigureService(root, root)
try:
    capabilities = service.capabilities()
    version = service.state()["version"]
    item = service.app.change({"version": version, "selector": {"category": "A"},
        "property": "color", "value": "#AA22BB", "instruction": "Use purple for A."})["request"]
    try:
        job_id = service.submit_job(version, [item["id"]])["job"]["id"]
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            job = service.get_job(job_id)["job"]
            if job["status"] not in ACTIVE_STATUSES:
                break
            time.sleep(.03)
    except ValueError as exc:
        job = {"status": "blocked_before_submission", "error": str(exc)}
    output = {"preview_supported": capabilities["preview"]["supported"],
              "project_equals_attempt": service.project == service.app.root,
              "job_status": job["status"], "job_error": job["error"],
              "registered_job_count": len(service.list_jobs()["jobs"]),
              "source_status": service.app.ledger()["requests"][0]["status"]}
    (root.parent / "self-scoped-attempt-result.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))
finally:
    service.close()
