"""No-inference contract tests for the actual local worker/process boundary.

The controlled subprocess renders real EasyViz exports. It never contacts a
model provider; text-only successes, stale sources and cancelled jobs must not
turn saved requests into applied edits.
"""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"
sys.path.insert(0, str(SCRIPTS))
import agent_dispatch
import figure_service
from figure_service import FigureService
from figure_workbench import WorkbenchError, write_figure_info
import render
import analyze
import ev_document


class AgentDispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-agent-contract-")
        self.root = Path(self.temp.name).resolve()
        self.data = self.root / "data.csv"
        self.data.write_text("x,y,group\n1,2,A\n2,3,A\n1,4,B\n2,5,B\n")
        self.spec = {"chart": "scatter", "fields": {"x": "x", "y": "y", "group": "group"},
                     "labels": {"x": "X", "y": "Y"}, "layout": {"width_mm": 90, "height_mm": 70,
                     "font": "DejaVu Sans", "font_size_pt": 8}, "formats": ["svg"], "seed": 41}
        self.spec_path = self.root / "spec.json"
        self.spec_path.write_text(json.dumps(self.spec))
        self.attempt = self.root / "original"
        render.render(self.data, self.spec, self.attempt, spec_path=self.spec_path, track="create")
        self.service = FigureService(self.root, self.attempt)
        self.version = self.service.state()["version"]
        self.shim = self.root / "controlled-worker.py"
        self.shim.write_text(f"""import json, pathlib, sys
sys.path.insert(0, {str(SCRIPTS)!r})
import render
target = pathlib.Path(sys.argv[1])
context = json.loads((target / 'agent-context.json').read_text())
spec_file = pathlib.Path(context['worker_input']['spec_file'])
spec = json.loads(spec_file.read_text())
spec['colors'] = {{'A': '#AA22BB', 'B': '#11AA88'}}
spec['formats'] = context['formats']
spec_file.write_text(json.dumps(spec))
render.render(pathlib.Path(context['worker_input']['data_file']), spec, target,
              spec_path=spec_file, track=context['track'])
ids = [item['id'] for item in context['requests']]
pending = ids[1:] if len(sys.argv) > 2 else []
result = {{'fulfilled_request_ids': ids[:1] if pending else ids,
          'unfulfilled_request_ids': pending,
          'changed_files': [str(spec_file.relative_to(target))],
          'validation': 'Controlled worker rendered real SVG and preserved all observations.'}}
(target / 'agent-result.json').write_text(json.dumps(result))
print(json.dumps({{'type': 'turn.completed'}}))
""")

    def tearDown(self):
        self.service.close()
        self.temp.cleanup()

    def save(self, freeform=False):
        payload = {"version": self.version, "selector": None if freeform else {"category": "A"},
                   "property": None if freeform else "color", "value": None if freeform else "#AA22BB",
                   "instruction": "Use green for B." if freeform else "Use purple for A."}
        return self.service.app.change(payload)["request"]

    def connect(self):
        with patch.object(agent_dispatch, "verify_backend", return_value=sys.executable):
            return self.service.configure_agent()

    def wait(self, job_id):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            job = self.service.get_job(job_id)["job"]
            if job["status"] not in figure_service.ACTIVE_STATUSES:
                return job
            time.sleep(.03)
        self.fail("Controlled worker did not finish within the test budget")

    def start(self, target, executable, prompt, stdout, stderr):
        self.assertIn(str(SCRIPTS.parent / "SKILL.md"), prompt)
        self.assertIn("Do not copy original exports", prompt)
        return subprocess.Popen([sys.executable, str(self.shim), str(target)], stdout=stdout, stderr=stderr,
                                stdin=subprocess.DEVNULL, start_new_session=os.name != "nt")

    def test_disconnected_by_default_and_configuration_is_project_local(self):
        self.assertFalse(self.service.agent_status()["automatic_dispatch"])
        item = self.save()
        with self.assertRaisesRegex(WorkbenchError, "Connect"):
            self.service.submit_agent_job(self.version, [item["id"]])
        self.connect()
        other = FigureService(self.root, self.attempt)
        try:
            self.assertTrue(other.agent_status()["enabled"])
            self.assertFalse(other.agent_status()["existing_chat_wake"])
            self.assertTrue(other.configure_agent(enabled=False)["enabled"] is False)
            self.assertFalse(self.service.agent_status()["enabled"])
        finally:
            other.close()
        with self.assertRaisesRegex(WorkbenchError, "Only the Codex"):
            self.service.configure_agent("/bin/sh", True)

    def test_full_saved_batch_uses_real_svg_only_output_and_preserves_original(self):
        color, freeform = self.save(), self.save(True)
        before = {path: path.read_bytes() for path in [self.data, self.spec_path, self.attempt / "panel.svg"]}
        self.connect()
        with patch.object(agent_dispatch, "verify_backend", return_value=sys.executable), \
                patch.object(agent_dispatch, "start_worker", side_effect=self.start):
            job = self.wait(self.service.submit_agent_job(self.version, [color["id"], freeform["id"]])["job"]["id"])
        self.assertEqual(job["status"], "succeeded", job)
        self.assertEqual(job["phase"], "complete")
        target = self.service.get_attempt(job["target_attempt_id"])
        self.assertEqual(set(target["files"]), {"svg"})
        self.assertEqual(target["track"], "create")
        self.assertNotEqual(target["version"]["figure_sha256"], self.version["figure_sha256"])
        self.assertEqual([item["status"] for item in self.service.app.ledger()["requests"]], ["applied", "applied"])
        with zipfile.ZipFile(self.service.attempt_app(target["id"]).root / "panel.ev") as archive:
            receipt = json.loads(archive.read("requests.json"))
        self.assertEqual(receipt["history"][-1]["id"], job["outcome_id"])
        for path, raw in before.items():
            self.assertEqual(path.read_bytes(), raw)
        retry = self.service.submit_agent_job(self.version, [color["id"], freeform["id"]])["job"]
        self.assertEqual(retry["id"], job["id"])

    def test_partial_result_marks_only_fulfilled_ids_applied(self):
        color, note = self.save(), self.save(True)
        self.connect()
        def partial(target, executable, prompt, stdout, stderr):
            return subprocess.Popen([sys.executable, str(self.shim), str(target), "partial"],
                stdout=stdout, stderr=stderr, start_new_session=os.name != "nt")
        with patch.object(agent_dispatch, "verify_backend", return_value=sys.executable), \
                patch.object(agent_dispatch, "start_worker", side_effect=partial):
            job = self.wait(self.service.submit_agent_job(self.version, [color["id"], note["id"]])["job"]["id"])
        self.assertEqual(job["status"], "succeeded", job)
        self.assertEqual(job["agent_request_ids"], [note["id"]])
        statuses = {item["id"]: item["status"] for item in self.service.app.ledger()["requests"]}
        self.assertEqual(statuses, {color["id"]: "applied", note["id"]: "pending"})

    def test_custom_workbench_name_reaches_worker_and_new_document_without_adding_plot_title(self):
        name = "Macrophage review / panel A"
        info = write_figure_info(self.attempt, name)
        self.assertEqual(self.service.state()["figure_name"], name)
        self.assertEqual(self.service.state()["version"], self.version)
        original_svg = (self.attempt / "panel.svg").read_bytes()
        original_data = self.data.read_bytes()
        item = self.save()
        self.connect()
        def named_worker(target, executable, prompt, stdout, stderr):
            context = json.loads((target / "agent-context.json").read_text())
            self.assertEqual(context["figure_name"], name)
            self.assertEqual(json.loads((target / "figure-info.json").read_text()), info)
            self.assertIn("workbench display name", prompt)
            self.assertIn("do not add it as an in-image SVG title", prompt)
            return self.start(target, executable, prompt, stdout, stderr)
        with patch.object(agent_dispatch, "verify_backend", return_value=sys.executable), \
                patch.object(agent_dispatch, "start_worker", side_effect=named_worker):
            job = self.wait(self.service.submit_agent_job(self.version, [item["id"]])["job"]["id"])
        self.assertEqual(job["status"], "succeeded", job)
        target = self.service.attempt_app(job["target_attempt_id"])
        self.assertEqual(target.state()["figure_name"], name)
        self.assertEqual(ev_document.inspect_document(target.root / "panel.ev")["name"], name)
        self.assertEqual(json.loads((target.root / "figure-info.json").read_text()), info)
        self.assertNotIn(name.encode(), (target.root / "panel.svg").read_bytes())
        self.assertNotIn("title", json.loads(Path(target.state()["input"]["spec_file"]).read_text()).get("labels", {}))
        self.assertEqual(Path(target.state()["input"]["data_file"]).read_bytes(), original_data)
        self.assertEqual((self.attempt / "panel.svg").read_bytes(), original_svg)

    def test_inherited_tiff_is_validated_internally_and_kept_in_document(self):
        self.spec["formats"] = ["svg", "tiff"]
        self.spec_path.write_text(json.dumps(self.spec))
        render.render(self.data, self.spec, self.attempt, spec_path=self.spec_path, track="create")
        self.version = self.service.state()["version"]
        item = self.save()
        self.connect()
        with patch.object(agent_dispatch, "verify_backend", return_value=sys.executable), \
                patch.object(agent_dispatch, "start_worker", side_effect=self.start):
            job = self.wait(self.service.submit_agent_job(self.version, [item["id"]])["job"]["id"])
        self.assertEqual(job["status"], "succeeded", job)
        target = self.service.attempt_app(job["target_attempt_id"])
        with self.assertRaisesRegex(WorkbenchError, "not available"):
            target.read_file("panel.tiff")
        qa = json.loads(target.read_file("qa.json"))
        self.assertEqual(qa["exports"]["tiff"]["sha256"], hashlib.sha256((target.root / "panel.tiff").read_bytes()).hexdigest())
        with zipfile.ZipFile(target.root / "panel.ev") as archive:
            self.assertEqual(archive.read("panel.tiff"), (target.root / "panel.tiff").read_bytes())
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "applied")

    def test_descriptive_format_downgrade_preserves_real_worker_exports(self):
        self.spec["formats"] = ["svg", "pdf", "png", "tiff"]
        self.spec_path.write_text(json.dumps(self.spec))
        render.render(self.data, self.spec, self.attempt, spec_path=self.spec_path, track="create")
        self.version = self.service.state()["version"]
        settings_path = self.attempt / "settings.json"
        settings = json.loads(settings_path.read_text())
        settings["formats"] = ["svg"]
        settings_path.write_text(json.dumps(settings))
        self.assertTrue(self.service.state()["source_current"])
        item = self.save()
        self.connect()
        def retained_formats(target, executable, prompt, stdout, stderr):
            context = json.loads((target / "agent-context.json").read_text())
            self.assertEqual(context["formats"], ["svg", "pdf", "png", "tiff"])
            return self.start(target, executable, prompt, stdout, stderr)
        with patch.object(agent_dispatch, "verify_backend", return_value=sys.executable), \
                patch.object(agent_dispatch, "start_worker", side_effect=retained_formats):
            job = self.wait(self.service.submit_agent_job(self.version, [item["id"]])["job"]["id"])
        self.assertEqual(job["status"], "succeeded", job)
        target = self.service.attempt_app(job["target_attempt_id"])
        for extension in ("svg", "pdf", "png", "tiff"):
            self.assertTrue((target.root / ("panel." + extension)).is_file())
        with zipfile.ZipFile(target.root / "panel.ev") as archive:
            self.assertTrue({"panel.svg", "panel.pdf", "panel.png", "panel.tiff"} <= set(archive.namelist()))
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "applied")

    def test_text_success_without_render_is_rejected_and_requests_stay_pending(self):
        item = self.save(True)
        self.connect()
        def no_render(target, executable, prompt, stdout, stderr):
            result = {"fulfilled_request_ids": [item["id"]], "unfulfilled_request_ids": [],
                      "changed_files": ["inputs/spec_file.json"], "validation": "Claimed success without actual exports."}
            (target / "agent-result.json").write_text(json.dumps(result))
            return subprocess.Popen([sys.executable, "-c", "pass"], stdout=stdout, stderr=stderr)
        with patch.object(agent_dispatch, "verify_backend", return_value=sys.executable), \
                patch.object(agent_dispatch, "start_worker", side_effect=no_render):
            job = self.wait(self.service.submit_agent_job(self.version, [item["id"]])["job"]["id"])
        self.assertEqual(job["status"], "failed", job)
        self.assertIsNone(job["target_attempt_id"])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")

    def test_all_unfulfilled_does_not_publish_blank_attempt(self):
        item = self.save(True)
        self.connect()
        def decline(target, executable, prompt, stdout, stderr):
            result = {"fulfilled_request_ids": [], "unfulfilled_request_ids": [item["id"]],
                      "changed_files": [], "validation": "Need a clarified edit instruction."}
            (target / "agent-result.json").write_text(json.dumps(result))
            return subprocess.Popen([sys.executable, "-c", "pass"], stdout=stdout, stderr=stderr)
        with patch.object(agent_dispatch, "verify_backend", return_value=sys.executable), \
                patch.object(agent_dispatch, "start_worker", side_effect=decline):
            job = self.wait(self.service.submit_agent_job(self.version, [item["id"]])["job"]["id"])
            retry = self.wait(self.service.submit_agent_job(self.version, [item["id"]])["job"]["id"])
        self.assertNotEqual(retry["id"], job["id"])
        self.assertEqual(job["phase"], "agent_handoff", job)
        self.assertIsNone(job["target_attempt_id"])
        self.assertEqual(len(self.service.list_attempts()["attempts"]), 1)
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")

    def test_cross_process_lock_cancel_and_timeout_preserve_pending_requests(self):
        item = self.save(True)
        self.connect()
        started = threading.Event()
        processes = []
        def slow(target, executable, prompt, stdout, stderr):
            process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(20)"],
                                       stdout=stdout, stderr=stderr, start_new_session=os.name != "nt")
            processes.append(process)
            started.set()
            return process
        with patch.object(agent_dispatch, "verify_backend", return_value=sys.executable), \
                patch.object(agent_dispatch, "start_worker", side_effect=slow):
            first = self.service.submit_agent_job(self.version, [item["id"]])["job"]
            self.assertTrue(started.wait(3))
            second = FigureService(self.root, self.attempt)
            try:
                self.assertEqual(second.submit_agent_job(self.version, [item["id"]])["job"]["id"], first["id"])
                different = self.save()
                with self.assertRaisesRegex(WorkbenchError, "Another figure job"):
                    second.submit_agent_job(self.version, [different["id"]])
                second.cancel_job(first["id"])
                final = self.wait(first["id"])
            finally:
                second.close()
            self.assertEqual(final["status"], "cancelled", final)
            self.assertIsNotNone(processes[0].poll())
            with patch.object(agent_dispatch, "AGENT_TIMEOUT_SECONDS", .05):
                timed = self.wait(self.service.submit_agent_job(self.version, [item["id"]])["job"]["id"])
            self.assertEqual(timed["status"], "failed", timed)
            self.assertIn("time limit", timed["error"])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")

    def test_stale_source_fails_before_worker_start(self):
        item = self.save(True)
        self.connect()
        self.data.write_text(self.data.read_text() + "3,9,A\n")
        with patch.object(agent_dispatch, "start_worker") as start:
            with self.assertRaises(WorkbenchError):
                self.service.submit_agent_job(self.version, [item["id"]])
            start.assert_not_called()

    def test_worker_cannot_claim_applied_edits_after_changing_source_data(self):
        item = self.save(True)
        self.connect()
        real_start = self.start
        def corrupt_data(target, executable, prompt, stdout, stderr):
            context = json.loads((target / "agent-context.json").read_text())
            path = Path(context["worker_input"]["data_file"])
            path.write_text(path.read_text() + "3,9,A\n")
            return real_start(target, executable, prompt, stdout, stderr)
        with patch.object(agent_dispatch, "verify_backend", return_value=sys.executable), \
                patch.object(agent_dispatch, "start_worker", side_effect=corrupt_data):
            job = self.wait(self.service.submit_agent_job(self.version, [item["id"]])["job"]["id"])
        self.assertEqual(job["status"], "failed", job)
        self.assertIn("unchanged primary", job["error"])
        self.assertIsNone(job["target_attempt_id"])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")

    def test_custom_source_is_copied_edited_and_rendered_with_real_handoff(self):
        custom = self.root / "author_plot.py"
        custom.write_text(f"""import csv, hashlib, json, pathlib, sys
sys.path.insert(0, {str(SCRIPTS)!r})
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from figure_handoff import capture_inputs, write_receipt
import figure_elements
data, specification, out = map(pathlib.Path, sys.argv[1:4])
out.mkdir(exist_ok=True)
capture = capture_inputs(out, data_file=data, source_script=pathlib.Path(__file__), spec_file=specification)
spec = json.loads(capture.raw['spec_file'])
rows = list(csv.DictReader(capture.raw['data_file'].decode().splitlines()))
fig, ax = plt.subplots(figsize=(90 / 25.4, 70 / 25.4))
fig._easyviz_data_file = data.resolve()
fig._easyviz_source_script = pathlib.Path(__file__).resolve()
fig._easyviz_spec_file = specification.resolve()
fig._easyviz_track = 'create'
color = '#2581B9'
points = ax.scatter([float(row['x']) for row in rows], [float(row['y']) for row in rows], c=color)
figure_elements.register(fig, points, 'point-group', 'Specimen observations', editable=['color'])
ax.set_xlabel('X'); ax.set_ylabel('Y')
figure_elements.attach_layout(fig, spec)
fig.savefig(out / 'panel.svg', metadata={{'Date': None}})
figure_elements.write(fig, out, spec, {{'width_mm': 90, 'height_mm': 70}})
plt.close(fig)
digest = hashlib.sha256((out / 'panel.svg').read_bytes()).hexdigest()
(out / 'settings.json').write_text(json.dumps({{'formats': ['svg']}}))
(out / 'qa.json').write_text(json.dumps({{'status': 'pass', 'valid_outputs': True, 'exports': {{'svg': {{'sha256': digest}}}}}}))
write_receipt(out, capture=capture, formats=['svg'], resolved_spec=spec, track='create')
""")
        original_custom = custom.read_bytes()
        custom_attempt = self.root / "custom-original"
        subprocess.run([sys.executable, str(custom), str(self.data), str(self.spec_path), str(custom_attempt)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        caption = "Every specimen is retained; only mark color may change.\n"
        (custom_attempt / "figure-caption.md").write_text(caption)
        source_id = self.service.register_attempt(custom_attempt)["id"]
        self.service.switch_attempt(source_id)
        self.version = self.service.state()["version"]
        item = self.save(True)
        self.connect()
        def custom_worker(target, executable, prompt, stdout, stderr):
            context = json.loads((target / "agent-context.json").read_text())
            source_file = Path(context["worker_input"]["source_script"])
            self.assertEqual(source_file, target / "plot.py")
            source_file.write_text(source_file.read_text().replace("color = '#2581B9'", "color = '#11AA88'"))
            wrapper = target / "controlled-custom.py"
            wrapper.write_text("import json, pathlib, subprocess, sys\n"
                "root = pathlib.Path(__file__).parent\n"
                "context = json.loads((root / 'agent-context.json').read_text())\n"
                "inputs = context['worker_input']\n"
                "subprocess.run([sys.executable, inputs['source_script'], inputs['data_file'], inputs['spec_file'], str(root)], check=True)\n"
                "result = {'fulfilled_request_ids': [item['id'] for item in context['requests']], 'unfulfilled_request_ids': [], "
                "'changed_files': ['plot.py'], 'validation': 'Custom source copy rendered fresh bound SVG with unchanged data.'}\n"
                "(root / 'agent-result.json').write_text(json.dumps(result))\n")
            return subprocess.Popen([sys.executable, str(wrapper)], stdout=stdout, stderr=stderr)
        with patch.object(agent_dispatch, "verify_backend", return_value=sys.executable), \
                patch.object(agent_dispatch, "start_worker", side_effect=custom_worker):
            job = self.wait(self.service.submit_agent_job(self.version, [item["id"]])["job"]["id"])
        self.assertEqual(job["status"], "succeeded", job)
        self.assertEqual(custom.read_bytes(), original_custom)
        target_app = self.service.attempt_app(job["target_attempt_id"])
        self.assertEqual(target_app.state()["input"]["source_script"], str(target_app.root / "plot.py"))
        self.assertEqual(target_app.state()["version"]["input_sha256"], self.version["input_sha256"])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "applied")
        self.assertEqual(ev_document.inspect_document(target_app.root / "panel.ev")["kind"], ev_document.KIND)
        with zipfile.ZipFile(target_app.root / "panel.ev") as archive:
            receipt = json.loads(archive.read("requests.json"))
            self.assertEqual(archive.read("figure-caption.md").decode(), caption)
        self.assertEqual(receipt["requests"][0]["status"], "applied")
        self.assertEqual(receipt["history"][-1]["id"], job["outcome_id"])

    def test_document_pack_failure_prevents_worker_publication(self):
        item = self.save(True)
        self.connect()
        with patch.object(agent_dispatch, "verify_backend", return_value=sys.executable), \
                patch.object(agent_dispatch, "start_worker", side_effect=self.start), \
                patch.object(ev_document, "export_document", side_effect=ev_document.EVDocumentError("Unmapped custom export")):
            job = self.wait(self.service.submit_agent_job(self.version, [item["id"]])["job"]["id"])
        self.assertEqual(job["status"], "failed", job)
        self.assertIn("valid editable .ev", job["error"])
        self.assertIsNone(job["target_attempt_id"])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")

    def test_postcommit_document_failure_preserves_actual_applied_outcome(self):
        item = self.save(True)
        self.connect()
        actual_export = ev_document.export_document
        calls = []
        def first_only(target):
            calls.append(target)
            if len(calls) == 2:
                raise ev_document.EVDocumentError("Injected postcommit archive refresh failure")
            return actual_export(target)
        with patch.object(agent_dispatch, "verify_backend", return_value=sys.executable), \
                patch.object(agent_dispatch, "start_worker", side_effect=self.start), \
                patch.object(ev_document, "export_document", side_effect=first_only):
            job = self.wait(self.service.submit_agent_job(self.version, [item["id"]])["job"]["id"])
        self.assertEqual(job["status"], "succeeded", job)
        self.assertTrue(job["outcome_id"])
        self.assertIn("exported again", job["document_warning"])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "applied")
        target = self.service.attempt_app(job["target_attempt_id"]).root
        self.assertEqual(json.loads((target / "document-status.json").read_text())["status"], "warning")
        self.assertTrue((target / "panel.ev").is_file())

    def test_qa_export_tampering_is_rejected_before_application(self):
        item = self.save(True)
        self.connect()
        original_reader = agent_dispatch.read_result
        def tamper(target, ids):
            result = original_reader(target, ids)
            qa_file = target / "qa.json"
            qa = json.loads(qa_file.read_text())
            qa["exports"]["svg"]["sha256"] = "0" * 64
            qa_file.write_text(json.dumps(qa))
            return result
        with patch.object(agent_dispatch, "verify_backend", return_value=sys.executable), \
                patch.object(agent_dispatch, "start_worker", side_effect=self.start), \
                patch.object(agent_dispatch, "read_result", side_effect=tamper):
            job = self.wait(self.service.submit_agent_job(self.version, [item["id"]])["job"]["id"])
        self.assertEqual(job["status"], "failed", job)
        self.assertIn("QA export hash", job["error"])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")

    def test_cosmetic_worker_cannot_switch_adopted_adjusted_p_to_raw(self):
        source = self.root / "analysis-source.csv"
        source.write_text("id,group,value,value2\na1,A,1,1\na2,A,2,2\na3,A,3,4\nb1,B,4,1\nb2,B,5,2\nb3,B,6,3\n")
        plan = {"schema_version": 1, "question": "Compare two prespecified specimen endpoints",
                "design": {"unit": "id", "unit_definition": "one independent specimen", "structure": "independent", "confirmed": True},
                "missing_policy": "error", "comparisons": [
                    {"name": "primary", "method": "welch", "fields": {"group": "group", "value": "value"}, "groups": ["A", "B"]},
                    {"name": "secondary", "method": "welch", "fields": {"group": "group", "value": "value2"}, "groups": ["A", "B"]}],
                "multiplicity": {"family": "Two endpoints", "adjustment": "holm", "comparisons": ["primary", "secondary"]}}
        analyze.analyze(source, plan, self.root / "analysis")
        result_file = self.root / "analysis/results.json"
        spec = {"chart": "distribution", "fields": {"group": "group", "value": "value", "unit": "id"},
                "layout": {"width_mm": 100, "height_mm": 80, "font": "DejaVu Sans", "dpi": 100},
                "formats": ["svg"], "labels": {"x": "Condition", "y": "Response"},
                "options": {"kind": "box"}, "seed": 4,
                "statistics": {"analysis": {"schema_version": 1, "results_file": str(result_file),
                    "results_sha256": hashlib.sha256(result_file.read_bytes()).hexdigest(), "comparison": "primary",
                    "pvalue": "adjusted", "population": "included"}, "annotate": True}}
        spec_path = self.root / "analysis-spec.json"
        spec_path.write_text(json.dumps(spec))
        initial = self.root / "analysis-attempt"
        render.render(source, spec, initial, spec_path=spec_path, track="create")
        source_id = self.service.register_attempt(initial)["id"]
        self.service.switch_attempt(source_id)
        self.version = self.service.state()["version"]
        item = self.save()
        self.connect()
        shim = self.root / "controlled-worker.py"
        shim.write_text(shim.read_text().replace("spec['formats'] = context['formats']",
            "spec['formats'] = context['formats']\nspec['statistics']['analysis']['pvalue'] = 'raw'"))
        with patch.object(agent_dispatch, "verify_backend", return_value=sys.executable), \
                patch.object(agent_dispatch, "start_worker", side_effect=self.start):
            job = self.wait(self.service.submit_agent_job(self.version, [item["id"]])["job"]["id"])
        self.assertEqual(job["status"], "failed", job)
        self.assertIsNone(job["target_attempt_id"])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")

    def test_restricted_startup_has_actionable_error_and_honest_backend_status(self):
        item = self.save(True)
        self.connect()
        def denied(target, executable, prompt, stdout, stderr):
            return subprocess.Popen([sys.executable, "-c",
                "import sys; sys.stderr.write('WARNING: PATH aliases unavailable\\nError: failed to initialize in-process app-server client: Operation not permitted\\n'); sys.exit(1)"],
                stdout=stdout, stderr=stderr)
        with patch.object(agent_dispatch, "verify_backend", return_value=sys.executable), \
                patch.object(agent_dispatch, "start_worker", side_effect=denied):
            job = self.wait(self.service.submit_agent_job(self.version, [item["id"]])["job"]["id"])
        self.assertEqual(job["status"], "failed", job)
        self.assertIn("normal terminal", job["error"])
        self.assertNotIn("PATH aliases", job["error"])
        self.assertEqual(self.service.agent_status()["runtime_state"], "startup_failed")
        self.assertEqual(self.service.agent_status()["last_startup_error"], job["error"])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")


class AgentResultValidationTests(unittest.TestCase):
    def test_error_messages_are_bounded_and_restricted_diagnostics_are_not_exposed(self):
        concise, failed = agent_dispatch.worker_error("WARNING: hello\nError: " + "x" * 1000)
        self.assertLessEqual(len(concise), 500)
        self.assertFalse(failed)
        concise, failed = agent_dispatch.worker_error("2026-10-06T08:00 WARN secret/local/state: attempt to write a readonly database")
        self.assertTrue(failed)
        self.assertIn("normal terminal", concise)
        self.assertNotIn("secret", concise)

    def test_unknown_ids_duplicate_ids_and_path_escape_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "plot.py").write_text("pass")
            valid = {"fulfilled_request_ids": ["one"], "unfulfilled_request_ids": ["two"],
                     "changed_files": ["plot.py"], "validation": "Rendered and inspected."}
            for bad in ({**valid, "fulfilled_request_ids": ["one", "one"]},
                        {**valid, "fulfilled_request_ids": ["invented"]},
                        {**valid, "changed_files": ["../plot.py"]},
                        {**valid, "changed_files": [str(root / "plot.py")]},
                        {**valid, "unfulfilled_request_ids": []}):
                with self.subTest(bad=bad):
                    (root / "agent-result.json").write_text(json.dumps(bad))
                    with self.assertRaises(WorkbenchError):
                        agent_dispatch.read_result(root, ["one", "two"])

    def test_fixed_cli_command_has_bounded_workspace_and_stdin_prompt(self):
        class Process:
            stdin = None
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            prompt = "Exact instructions" * 65536
            seen = {}
            def start(command, **kwargs):
                seen["prompt"] = kwargs["stdin"].read()
                return Process()
            with patch.object(agent_dispatch.subprocess, "Popen", side_effect=start) as popen:
                process = agent_dispatch.start_worker(target, "/installed/codex", prompt, None, None)
            args, kwargs = popen.call_args
            command = args[0]
            self.assertEqual(command[:2], ["/installed/codex", "exec"])
            self.assertEqual(command[command.index("--sandbox") + 1], "workspace-write")
            self.assertEqual(command[command.index("-C") + 1], str(target))
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)
            self.assertEqual(command[-1], "-")
            self.assertEqual(seen["prompt"], prompt.encode())
            self.assertTrue(kwargs["stdin"].closed)
            self.assertIsNone(process.stdin)


if __name__ == "__main__":
    unittest.main()
