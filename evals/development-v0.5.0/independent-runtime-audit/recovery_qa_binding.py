"""Check interrupted-job recovery against the exact recorded QA digest."""
from pathlib import Path
import hashlib
import json
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "skills/easyviz/scripts"))
from figure_service import FigureService, _atomic_json

root = Path(__file__).resolve().parent / "registry-publication-fixture"
registry_path = root / ".easyviz-service/registry.json"
registry = json.loads(registry_path.read_text())
job = registry["jobs"][-1]
target = root / job["target_path"]
source = root / registry["attempts"][job["source_attempt_id"]]["path"]
event = next(item for item in json.loads((source / "requests.json").read_text())["history"]
             if item.get("id") == job["outcome_id"])
qa_path = target / "qa.json"
original_qa = qa_path.read_bytes()
qa = json.loads(original_qa)
# Model a second writer replacing the PDF and its QA after the earlier ledger
# event was committed, while the source/SVG/version still match that event.
replacement = b"%PDF-1.7\nReplacement bytes not measured by the committed QA event.\n"
(target / "panel.pdf").write_bytes(replacement)
qa["exports"]["pdf"]["sha256"] = hashlib.sha256(replacement).hexdigest()
qa_path.write_text(json.dumps(qa) + "\n")
old_target_id = job["target_attempt_id"]
registry["attempts"].pop(old_target_id)
job.update(status="running", phase="rendering", target_attempt_id=None)
_atomic_json(registry_path, registry)
service = FigureService(root, source)
try:
    recovered = service.get_job(job["id"])["job"]
    output = {"job_status": recovered["status"], "phase": recovered["phase"],
              "target_attempt_id": recovered["target_attempt_id"],
              "recorded_qa_sha256": event["target_qa_sha256"],
              "current_qa_sha256": hashlib.sha256(qa_path.read_bytes()).hexdigest(),
              "qa_digest_matches_recorded_event": hashlib.sha256(qa_path.read_bytes()).hexdigest() == event["target_qa_sha256"]}
    (root.parent / "recovery-qa-binding-result.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))
finally:
    service.close()
