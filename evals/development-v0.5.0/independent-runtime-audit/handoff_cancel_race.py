"""Synchronize cancellation exactly before an Agent-only job completes."""
from pathlib import Path
import json
import sys
import threading
import time
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "skills/easyviz/scripts"))
from figure_service import FigureService, ACTIVE_STATUSES

root = Path(__file__).resolve().parent / "crossprocess-fixture"
service = FigureService(root, root / "attempt-01")
version = service.state()["version"]
item = service.app.change({"version": version, "instruction": "Move legend 2 mm right."})["request"]
ready, release = threading.Event(), threading.Event()
original_finish = service._finish_handoff
def pause_before_handoff(job_id):
    ready.set()
    if not release.wait(5):
        raise RuntimeError("Handoff synchronization timed out")
    return original_finish(job_id)
try:
    with patch.object(service, "_finish_handoff", side_effect=pause_before_handoff):
        job_id = service.submit_job(version, [item["id"]])["job"]["id"]
        if not ready.wait(5):
            raise RuntimeError("Job did not reach handoff transition")
        cancellation = service.cancel_job(job_id)["job"]
        release.set()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            final = service.get_job(job_id)["job"]
            if final["status"] not in ACTIVE_STATUSES:
                break
            time.sleep(.01)
    result = {"status_at_cancellation": cancellation["status"], "cancellation_requested": cancellation["cancel_requested"],
              "final_status": final["status"], "final_phase": final["phase"],
              "final_cancel_requested": final["cancel_requested"], "target_attempt_id": final["target_attempt_id"]}
    (root.parent / "handoff-cancel-race-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
finally:
    release.set()
    service.close()
