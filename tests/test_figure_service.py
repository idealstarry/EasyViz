"""Real core preview, scoped API, durable jobs and optional MCP transport checks."""
from __future__ import annotations

import asyncio
import copy
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import signal
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"
sys.path.insert(0, str(SCRIPTS))
import figure_service
from figure_service import FigureService
from figure_workbench import FigureWorkbench, WorkbenchError, create_server
import render
import analyze


class FigureServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-figure-service-")
        self.root = Path(self.temp.name).resolve()
        self.data = self.root / "data.csv"
        self.data.write_text("x,y,group\n1,2,A\n2,3,A\n3,4,A\n1,4,B\n2,5,B\n3,6,B\n")
        self.spec = {"chart": "scatter", "fields": {"x": "x", "y": "y", "group": "group"},
                     "labels": {"x": "X", "y": "Y"},
                     "layout": {"width_mm": 120, "height_mm": 90, "font": "DejaVu Sans", "font_size_pt": 8, "line_width_pt": .6},
                     "formats": ["svg", "pdf", "png"], "options": {"point_area_pt2": 12}, "seed": 41}
        self.spec_path = self.root / "spec.json"
        self.spec_path.write_text(json.dumps(self.spec))
        self.attempt = self.root / "attempt-01"
        render.render(self.data, self.spec, self.attempt, spec_path=self.spec_path, track="create")
        self.service = FigureService(self.root, self.attempt)
        self.version = self.service.state()["version"]

    def tearDown(self):
        self.service.close()
        self.temp.cleanup()

    def save(self, **extra):
        payload = {"version": self.version, "selector": {"category": "A"}, "property": "color", "value": "#AA22BB",
                   "instruction": "Use purple for A without changing any observations or panel dimensions."}
        payload.update(extra)
        return self.service.app.change(payload)["request"]

    def wait(self, job_id):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            result = self.service.get_job(job_id)["job"]
            if result["status"] not in figure_service.ACTIVE_STATUSES:
                return result
            time.sleep(.03)
        self.fail("Preview did not finish within the test budget")

    def test_renamed_metadata_is_authoritative_across_services_registration_and_comparison(self):
        from ev_document import inspect_document
        original = {path.name: path.read_bytes() for path in self.attempt.iterdir() if path.is_file()}
        registry = json.loads(self.service.registry_path.read_text())
        registry["attempts"][self.service.current_attempt_id]["display_name"] = "Legacy display name"
        figure_service._atomic_json(self.service.registry_path, registry)
        self.assertEqual(self.service.get_attempt()["name"], "Legacy display name")
        self.assertEqual(self.service.state()["figure_name"], "Legacy display name")
        other = FigureService(self.root, self.attempt)
        try:
            result = self.service.rename_attempt("  炎症细胞变化  ")
            self.assertEqual(result["attempt"]["name"], "炎症细胞变化")
            self.assertEqual(result["attempt"]["version"], self.version)
            self.assertEqual(other.get_attempt()["name"], "炎症细胞变化")
            self.assertEqual(other.state()["figure_name"], "炎症细胞变化")
            self.assertEqual(other.list_attempts()["attempts"][0]["name"], "炎症细胞变化")
            self.assertEqual(other.register_attempt(self.attempt)["name"], "炎症细胞变化")
            self.service.switch_attempt(self.service.current_attempt_id, self.service.current_attempt_id)
            self.assertEqual(self.service.state()["comparison"]["figure_name"], "炎症细胞变化")
            self.assertEqual(json.loads(self.service.registry_path.read_text())["attempts"][self.service.current_attempt_id]["display_name"], "Legacy display name")
            for name, raw in original.items():
                if name in {"panel.ev", "document-status.json"}:
                    continue  # Portable display metadata follows the saved name.
                with self.subTest(file=name):
                    self.assertEqual((self.attempt / name).read_bytes(), raw)
            self.assertEqual(inspect_document(self.attempt / "panel.ev")["name"], "炎症细胞变化")
            self.assertEqual(json.loads((self.attempt / "document-status.json").read_text())["status"], "ready")
            without_selection = FigureService(self.root)
            try:
                result = without_selection.rename_attempt("Named without a selected view", self.service.current_attempt_id)
                self.assertTrue(result["state"]["empty"])
                self.assertEqual(result["attempt"]["name"], "Named without a selected view")
                self.assertEqual(other.state()["figure_name"], "Named without a selected view")
                self.assertEqual(inspect_document(self.attempt / "panel.ev")["name"], "Named without a selected view")
                self.assertEqual(other.state()["version"], self.version)
            finally:
                without_selection.close()
        finally:
            other.close()

    def test_real_preview_publishes_three_matching_exports_without_changing_accepted_source(self):
        self.service.rename_attempt("Response distribution")
        accepted = self.service.accept("Baseline SVG and final-size exports inspected.")
        original = {name: (self.attempt / name).read_bytes() for name in ("panel.svg", "panel.pdf", "panel.png", "accepted-snapshot/acceptance.json")}
        request = self.save()
        job = self.wait(self.service.submit_job(self.version, [request["id"]])["job"]["id"])
        self.assertEqual(job["status"], "succeeded", job)
        self.assertEqual(job["phase"], "complete")
        target = self.service.get_attempt(job["target_attempt_id"])
        self.assertEqual(target["name"], "Response distribution")
        self.assertEqual(FigureWorkbench(target["path"]).state()["figure_name"], "Response distribution")
        self.assertEqual(set(target["files"]), {"svg", "pdf", "png"})
        self.assertEqual(target["panel"], accepted["attempt"]["panel"])
        self.assertNotEqual(target["version"]["figure_sha256"], self.version["figure_sha256"])
        self.assertEqual(target["version"]["input_sha256"], self.version["input_sha256"])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "applied")
        for name, raw in original.items():
            self.assertEqual((self.attempt / name).read_bytes(), raw)
        settings = json.loads((Path(target["path"]) / "settings.json").read_text())
        self.assertEqual(settings["resolved_colors"]["A"], "#AA22BB")
        self.assertEqual((Path(target["path"]) / "plotting-data.csv").read_bytes(), (self.attempt / "plotting-data.csv").read_bytes())

    def test_same_submitted_batch_is_idempotent_before_and_after_completion(self):
        item = self.save()
        job = self.service.submit_job(self.version, [item["id"]])["job"]
        self.assertEqual(self.service.submit_job(self.version, [item["id"]])["job"]["id"], job["id"])
        final = self.wait(job["id"])
        self.assertEqual(final["status"], "succeeded", final)
        retry = self.service.submit_job(self.version, [item["id"]])["job"]
        self.assertEqual(retry["id"], job["id"])
        self.assertEqual(len(self.service.list_jobs()["jobs"]), 1)

    def test_free_form_and_regions_remain_pending_in_explicit_agent_handoff(self):
        self.service.rename_attempt("Annotated figure")
        item = self.save(selector=None, property=None, value=None, region_mm={"x": 10, "y": 10, "width": 30, "height": 20},
                         instruction="Move this legend 2 mm right while retaining all data and panel sizes.")
        plan = self.service.prepare_edits(self.version, [item["id"]])
        self.assertEqual(plan["figure_name"], "Annotated figure")
        self.assertEqual(self.service.list_requests()["figure_name"], "Annotated figure")
        self.assertEqual(plan["automatic_request_ids"], [])
        self.assertEqual(plan["agent_requests"][0]["request_id"], item["id"])
        job = self.wait(self.service.submit_job(self.version, [item["id"]])["job"]["id"])
        self.assertEqual(job["phase"], "agent_handoff")
        self.assertIsNone(job["target_attempt_id"])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")
        self.assertFalse(self.service.capabilities()["agent"]["automatic_dispatch"])

    def test_cancellation_accepted_before_agent_only_handoff_remains_cancelled(self):
        item = self.save(selector=None, property=None, value=None, instruction="Edit the legend in the plotting source.")
        about_to_finish, release = threading.Event(), threading.Event()
        real_finish = self.service._finish_handoff
        def paused_finish(job_id):
            about_to_finish.set()
            self.assertTrue(release.wait(3))
            real_finish(job_id)
        with patch.object(self.service, "_finish_handoff", side_effect=paused_finish):
            job_id = self.service.submit_job(self.version, [item["id"]])["job"]["id"]
            self.assertTrue(about_to_finish.wait(3))
            cancelled = self.service.cancel_job(job_id)["job"]
            self.assertTrue(cancelled["cancel_requested"])
            release.set()
            final = self.wait(job_id)
        self.assertEqual(final["status"], "cancelled", final)
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")

    def test_mixed_batch_keeps_agent_instruction_pending_and_identifies_it(self):
        color = self.save()
        note = self.save(selector=None, property=None, value=None, instruction="Move the legend 2 mm right.")
        final = self.wait(self.service.submit_job(self.version, [color["id"], note["id"]])["job"]["id"])
        self.assertEqual(final["status"], "succeeded", final)
        self.assertEqual(final["agent_request_ids"], [note["id"]])
        statuses = {item["id"]: item["status"] for item in self.service.app.ledger()["requests"]}
        self.assertEqual(statuses, {color["id"]: "applied", note["id"]: "pending"})

    def test_cancel_stops_owned_process_without_publishing_or_applying_requests(self):
        item = self.save()
        real_popen = subprocess.Popen
        started = threading.Event()
        def slow_worker(*args, **kwargs):
            result = real_popen([sys.executable, "-c", "import time; time.sleep(20)"], **kwargs)
            started.set()
            return result
        with patch.object(figure_service.subprocess, "Popen", side_effect=slow_worker):
            submitted = self.service.submit_job(self.version, [item["id"]])["job"]
            self.assertTrue(started.wait(3))
            second = FigureService(self.root, self.attempt)
            try:
                second.cancel_job(submitted["id"])
                job = self.wait(submitted["id"])
            finally:
                second.close()
        self.assertEqual(job["status"], "cancelled", job)
        self.assertIsNone(job["target_attempt_id"])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")
        self.assertEqual(len(self.service.list_attempts()["attempts"]), 1)

    def test_timeout_and_failed_worker_preserve_pending_requests(self):
        item = self.save()
        real_popen = subprocess.Popen
        self.service.render_timeout = .15
        with patch.object(figure_service.subprocess, "Popen", side_effect=lambda *a, **kw: real_popen([sys.executable, "-c", "import time; time.sleep(20)"], **kw)):
            job = self.wait(self.service.submit_job(self.version, [item["id"]])["job"]["id"])
        self.assertEqual(job["status"], "failed", job)
        self.assertIn("job limit", job["error"])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")

    @unittest.skipIf(os.name == "nt", "POSIX signal lifecycle; owned-process cancellation is tested separately")
    def test_cli_interrupt_reaps_owned_renderer_and_keeps_uncommitted_request_pending(self):
        item = self.save()
        shim = self.root / "slow-core-cli.py"
        pid_file = self.root / "owned-worker.pid"
        shim.write_text("\n".join([
            "import pathlib, subprocess, sys",
            f"sys.path.insert(0, {str(SCRIPTS)!r})",
            "import figure_service",
            "original = subprocess.Popen",
            "def slow(command, **kwargs):",
            "    process = original([sys.executable, '-c', 'import time; time.sleep(20)'], **kwargs)",
            f"    pathlib.Path({str(pid_file)!r}).write_text(str(process.pid))",
            "    return process",
            "figure_service.subprocess.Popen = slow",
            "figure_service.main()", ""]))
        command = [sys.executable, str(shim), "submit", "--project-dir", str(self.root), "--figure-dir", str(self.attempt), "--request-ids", item["id"]]
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        child_pid = None
        try:
            deadline = time.monotonic() + 5
            while not pid_file.exists() and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(pid_file.exists())
            child_pid = int(pid_file.read_text())
            process.send_signal(signal.SIGINT)
            _, error = process.communicate(timeout=6)
            self.assertEqual(process.returncode, 130, error.decode())
            self.assertNotIn(b"KeyboardInterrupt", error)
            with self.assertRaises(ProcessLookupError):
                os.kill(child_pid, 0)
            self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")
            self.assertEqual(self.service.list_jobs()["jobs"][0]["status"], "cancelled")
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=3)
            if child_pid:
                try:
                    os.kill(child_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def test_concurrent_project_services_cannot_launch_overlapping_jobs(self):
        first, second_item = self.save(), self.save(value="#22AA44")
        started = threading.Event()
        real_popen = subprocess.Popen
        def slow(*a, **kw):
            process = real_popen([sys.executable, "-c", "import time; time.sleep(20)"], **kw)
            started.set()
            return process
        other = FigureService(self.root, self.attempt)
        try:
            with patch.object(figure_service.subprocess, "Popen", side_effect=slow):
                job = self.service.submit_job(self.version, [first["id"]])["job"]
                self.assertTrue(started.wait(3))
                with self.assertRaisesRegex(WorkbenchError, "Another figure job"):
                    other.submit_job(self.version, [second_item["id"]])
                other.cancel_job(job["id"])
                self.assertEqual(self.wait(job["id"])["status"], "cancelled")
        finally:
            other.close()

    def test_source_changes_block_submission_and_core_source_is_never_executed_from_arbitrary_path(self):
        item = self.save()
        self.data.write_text(self.data.read_text() + "4,8,A\n")
        with self.assertRaisesRegex(WorkbenchError, "source has changed"):
            self.service.submit_job(self.version, [item["id"]])
        self.assertEqual(self.service.list_jobs()["jobs"], [])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")

    def test_registered_attempts_and_inputs_cannot_escape_project_scope(self):
        with tempfile.TemporaryDirectory() as outside:
            with self.assertRaisesRegex(WorkbenchError, "outside"):
                self.service.register_attempt(Path(outside).resolve())
            link = self.root / "outside-link"
            link.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(WorkbenchError, "symlinks"):
                self.service.register_attempt(link)
        for value in ("../attempt", "/missing/attempt"):
            with self.assertRaises(WorkbenchError):
                self.service.register_attempt(value)
        item = self.save()
        with self.assertRaises(WorkbenchError):
            self.service.submit_job(self.version, "not-a-list")

    def test_attempt_only_scope_reports_review_only_and_refuses_fresh_render_or_restore(self):
        # Capture a self-contained accepted copy, so its primary inputs lie
        # within the same folder and the scope issue is independent of paths.
        self.service.rename_attempt("Accepted response")
        self.service.accept("Original final-size export bundle inspected.")
        copy_attempt = self.service.restore()["attempt"]
        self.assertEqual(copy_attempt["name"], "Accepted response")
        path = Path(copy_attempt["path"])
        narrow = FigureService(path, path)
        try:
            capabilities = narrow.capabilities()
            self.assertFalse(capabilities["preview"]["supported"])
            self.assertIn("containing project directory", capabilities["preview"]["reason"])
            with self.assertRaisesRegex(WorkbenchError, "containing project directory"):
                narrow.submit_job(narrow.state()["version"])
            with self.assertRaisesRegex(WorkbenchError, "containing project directory"):
                narrow.restore()
            self.assertEqual(narrow.list_jobs()["jobs"], [])
        finally:
            narrow.close()

    def test_service_restart_keeps_verified_jobs_and_recovers_interrupted_queue(self):
        item = self.save()
        job = self.wait(self.service.submit_job(self.version, [item["id"]])["job"]["id"])
        self.assertEqual(job["status"], "succeeded", job)
        self.service.close()
        registry = json.loads(self.service.registry_path.read_text())
        interrupted = copy.deepcopy(job)
        interrupted.update(id="job-" + "0" * 32, status="running", phase="rendering", target_attempt_id=None)
        interrupted.pop("target_path", None)
        registry["jobs"].append(interrupted)
        figure_service._atomic_json(self.service.registry_path, registry)
        recovered = FigureService(self.root, self.attempt)
        try:
            self.assertEqual(recovered.get_job(job["id"])["job"]["status"], "succeeded")
            broken = recovered.get_job(interrupted["id"])["job"]
            self.assertEqual(broken["status"], "failed")
            self.assertEqual(broken["phase"], "interrupted")
        finally:
            recovered.close()

    def test_restart_recovers_only_actual_ledger_committed_export_after_publication_interruption(self):
        item = self.save()
        completed = self.wait(self.service.submit_job(self.version, [item["id"]])["job"]["id"])
        self.assertEqual(completed["status"], "succeeded", completed)
        self.service.close()
        registry = json.loads(self.service.registry_path.read_text())
        registry["attempts"].pop(completed["target_attempt_id"])
        registry["jobs"][0].update(status="running", phase="rendering", target_attempt_id=None)
        figure_service._atomic_json(self.service.registry_path, registry)
        recovered = FigureService(self.root, self.attempt)
        try:
            actual = recovered.get_job(completed["id"])["job"]
            self.assertEqual(actual["status"], "succeeded")
            self.assertEqual(actual["target_attempt_id"], completed["target_attempt_id"])
            self.assertIn("Recovered", actual["message"])
            self.assertEqual(recovered.get_attempt(actual["target_attempt_id"])["version"],
                             FigureWorkbench(Path(self.root / actual["target_path"])).state()["version"])
        finally:
            recovered.close()

    def test_recovery_refuses_replaced_exports_even_when_current_qa_was_rewritten_to_pass(self):
        item = self.save()
        completed = self.wait(self.service.submit_job(self.version, [item["id"]])["job"]["id"])
        self.assertEqual(completed["status"], "succeeded", completed)
        self.service.close()
        target = self.root / completed["target_path"]
        replacement = (target / "panel.pdf").read_bytes() + b"\n% replaced after committed QA\n"
        (target / "panel.pdf").write_bytes(replacement)
        qa = json.loads((target / "qa.json").read_text())
        qa["exports"]["pdf"]["sha256"] = hashlib.sha256(replacement).hexdigest()
        figure_service._atomic_json(target / "qa.json", qa)
        registry = json.loads(self.service.registry_path.read_text())
        registry["attempts"].pop(completed["target_attempt_id"])
        registry["jobs"][0].update(status="running", phase="rendering", target_attempt_id=None)
        figure_service._atomic_json(self.service.registry_path, registry)
        recovered = FigureService(self.root, self.attempt)
        try:
            job = recovered.get_job(completed["id"])["job"]
            self.assertEqual(job["status"], "failed")
            self.assertEqual(job["phase"], "interrupted")
            self.assertIsNone(job["target_attempt_id"])
            self.assertNotIn(completed["target_attempt_id"], [item["id"] for item in recovered.list_attempts()["attempts"]])
        finally:
            recovered.close()

    def test_current_property_values_are_descriptions_not_reinterpreted_source_identities(self):
        state = self.service.state()
        category = next(item for item in state["elements"] if item.get("source_keys") and any(key.get("group") == "A" for key in item["source_keys"]))
        self.assertIn("editable_values", category)
        self.assertEqual(category["editable_values"]["color"], json.loads((self.attempt / "settings.json").read_text())["resolved_colors"]["A"])
        self.assertEqual(state["attempt_id"], self.service.current_attempt_id)
        self.assertEqual(state["project_id"], self.service.project_id)

    def test_adjusted_analysis_preview_accept_restore_and_portable_rerender_preserve_frozen_result(self):
        source = self.root / "analysis-source.csv"
        source.write_text("id,group,value,value2\na1,A,1,1\na2,A,2,2\na3,A,3,4\nb1,B,4,1\nb2,B,5,2\nb3,B,6,3\n")
        plan = {"schema_version": 1, "question": "Compare two prespecified independent specimen endpoints",
                "design": {"unit": "id", "unit_definition": "one independently sampled specimen", "structure": "independent", "confirmed": True},
                "missing_policy": "error", "comparisons": [
                    {"name": "primary", "method": "welch", "fields": {"group": "group", "value": "value"}, "groups": ["A", "B"]},
                    {"name": "secondary", "method": "welch", "fields": {"group": "group", "value": "value2"}, "groups": ["A", "B"]}],
                "multiplicity": {"family": "Two endpoints", "adjustment": "holm", "comparisons": ["primary", "secondary"]}}
        report = analyze.analyze(source, plan, self.root / "analysis")
        result_path = self.root / "analysis/results.json"
        spec = {"chart": "distribution", "fields": {"group": "group", "value": "value", "unit": "id"},
                "layout": {"width_mm": 100, "height_mm": 80, "font": "DejaVu Sans", "dpi": 100},
                "formats": ["pdf", "svg", "png"], "labels": {"x": "Condition", "y": "Response (a.u.)"},
                "options": {"kind": "box"}, "seed": 4,
                "statistics": {"analysis": {"schema_version": 1, "results_file": "analysis/results.json",
                    "results_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(), "comparison": "primary", "pvalue": "adjusted", "population": "included"}, "annotate": True}}
        spec_path = self.root / "analysis-spec.json"
        spec_path.write_text(json.dumps(spec))
        initial = self.root / "analysis-attempt"
        qa = render.render(source, spec, initial, spec_path=spec_path, track="create")
        self.assertEqual(qa["status"], "pass")
        initial_id = self.service.register_attempt(initial)["id"]
        self.service.switch_attempt(initial_id)
        version = self.service.state()["version"]
        item = self.service.app.change({"version": version, "selector": {"category": "A"}, "property": "color", "value": "#22B6AA", "instruction": "Use jade for A and retain the frozen adjusted analysis."})["request"]
        completed = self.wait(self.service.submit_job(version, [item["id"]])["job"]["id"])
        self.assertEqual(completed["status"], "succeeded", completed)
        target_id = completed["target_attempt_id"]
        preview_path = Path(self.service.get_attempt(target_id)["path"])
        before = json.loads((initial / "stats.json").read_text())
        self.assertEqual(json.loads((preview_path / "stats.json").read_text()), before)
        self.assertEqual(before["annotation_pvalue"], report["comparisons"][0]["adjusted_pvalue"])
        self.service.accept("Adjusted P label, all source observations and same-size PDF inspected.", target_id)
        restored = self.service.restore(target_id)
        restored_path = Path(restored["attempt"]["path"])
        rerender_spec_path = Path(restored["restoration"]["rerender_spec_file"])
        self.assertEqual((restored_path / "plot-spec.json").read_bytes(), (preview_path / "plot-spec.json").read_bytes())
        for filename in ("results.json", "plan.json", "analyzed-data.csv", "summary.csv", "methodology.md"):
            self.assertEqual((restored_path / "adopted-analysis" / filename).read_bytes(), (self.root / "analysis" / filename).read_bytes())
        # Original paths may disappear: the derived spec explicitly adopts the
        # captured report bytes, without rewriting the accepted export claim.
        import shutil
        shutil.rmtree(self.root / "analysis")
        derived = json.loads(rerender_spec_path.read_text())
        self.assertEqual(derived["statistics"]["analysis"]["pvalue"], "adjusted")
        self.assertEqual(derived["statistics"]["analysis"]["population"], "included")
        fresh = self.root / "portable-rerender"
        with patch("scipy.stats.ttest_ind", side_effect=AssertionError("Adopted inference must not be recomputed")):
            qa = render.render(restored_path / "source-data.csv", derived, fresh, spec_path=rerender_spec_path, track="create")
        self.assertEqual(qa["status"], "pass")
        after = json.loads((fresh / "stats.json").read_text())
        self.assertEqual(after["adoption"]["results_file"], derived["statistics"]["analysis"]["results_file"])
        after["adoption"]["results_file"] = before["adoption"]["results_file"]
        self.assertEqual(after, before)
        # A lazy analysis helper loaded above must not become a declared input
        # of subsequent ordinary plots just because this process reused render.
        ordinary = self.root / "ordinary-after-analysis"
        render.render(self.data, self.spec, ordinary, spec_path=self.spec_path, track="create")
        ordinary_id = self.service.register_attempt(ordinary)["id"]
        self.service.switch_attempt(ordinary_id)
        state = self.service.state()
        self.assertNotIn("helper:analysis_result.py", state["input"]["auxiliary_inputs"])
        request = self.service.app.change({"version": state["version"], "selector": {"category": "A"}, "property": "color", "value": "#33AA99", "instruction": "Recolor the ordinary plot after an adopted-analysis run."})["request"]
        job = self.wait(self.service.submit_job(state["version"], [request["id"]])["job"]["id"])
        self.assertEqual(job["status"], "succeeded", job)

    def test_http_preview_lifecycle_download_switch_accept_restore_and_origin_protection(self):
        server = create_server(self.attempt, project_dir=self.root)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"http://127.0.0.1:{server.server_port}"
        def request(method, path, payload=None, origin_header=origin):
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            headers = {"Content-Type": "application/json", "Origin": origin_header, "X-EasyViz-Token": server.service.token}
            connection.request(method, path, json.dumps(payload) if payload is not None else None, headers)
            response = connection.getresponse()
            result = response.status, response.read()
            connection.close()
            return result
        try:
            self.assertEqual(request("GET", "/api/capabilities")[0], 200)
            self.assertEqual(request("POST", "/api/jobs", {"version": self.version}, "https://other.test")[0], 403)
            item = self.save()
            status, raw = request("POST", "/api/jobs", {"version": self.version, "request_ids": [item["id"]]})
            self.assertEqual(status, 200, raw)
            job_id = json.loads(raw)["job"]["id"]
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                status, raw = request("GET", "/api/jobs/" + job_id)
                job = json.loads(raw)["job"]
                if job["status"] not in figure_service.ACTIVE_STATUSES:
                    break
                time.sleep(.03)
            self.assertEqual(job["status"], "succeeded", job)
            target_id = job["target_attempt_id"]
            before = server.service.current_attempt_id
            self.assertEqual(request("GET", "/api/attempts")[0], 200)
            self.assertEqual(server.service.current_attempt_id, before)
            self.assertEqual(request("GET", f"/api/attempts/{target_id}/preview.svg")[0], 200)
            status, raw = request("GET", f"/api/attempts/{target_id}/files/panel.pdf")
            self.assertEqual(status, 200)
            self.assertTrue(raw.startswith(b"%PDF"))
            status, raw = request("POST", "/api/attempts/switch", {"attempt_id": target_id, "compare_attempt_id": before})
            self.assertEqual(status, 200, raw)
            self.assertEqual(json.loads(raw)["state"]["attempt_id"], target_id)
            self.assertEqual(request("GET", "/api/compare.svg")[0], 200)
            self.assertEqual(request("POST", "/api/attempts/accept", {"validation": "Preview and matching PDF/PNG inspected."})[0], 200)
            status, raw = request("POST", "/api/attempts/restore", {})
            self.assertEqual(status, 200, raw)
            restored = json.loads(raw)
            self.assertNotEqual(restored["attempt"]["id"], target_id)
            self.assertEqual(restored["state"]["attempt_id"], target_id)
            self.assertEqual(request("POST", "/api/jobs/job-" + "0" * 32 + "/cancel", {})[0], 400)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)

    @unittest.skipUnless(importlib.util.find_spec("mcp"), "Optional MCP SDK is not installed")
    def test_official_mcp_in_process_client_reads_structured_output_and_scoped_resource(self):
        from easyviz_mcp import create_mcp
        from mcp import Client
        async def check():
            async with Client(create_mcp(self.service), raise_exceptions=True) as client:
                names = {tool.name for tool in (await client.list_tools()).tools}
                self.assertTrue({"capabilities", "get_attempt", "rename_attempt", "render_attempt", "record_outcome",
                                 "agent_status", "configure_agent", "submit_agent_job"} <= names)
                connection = await client.call_tool("agent_status", {})
                self.assertFalse(connection.structured_content["enabled"])
                self.assertFalse(connection.structured_content["existing_chat_wake"])
                result = await client.call_tool("get_attempt", {})
                self.assertFalse(result.is_error)
                self.assertEqual(result.structured_content["panel"], {"width_mm": 120., "height_mm": 90.})
                resource = await client.read_resource(result.structured_content["preview_resource"])
                self.assertEqual(len(resource.contents), 1)
                renamed = await client.call_tool("rename_attempt", {"name": "  Treatment response  "})
                self.assertFalse(renamed.is_error)
                self.assertEqual(renamed.structured_content["attempt"]["name"], "Treatment response")
                current = await client.call_tool("get_attempt", {})
                self.assertEqual(current.structured_content["name"], "Treatment response")
                self.assertEqual(current.structured_content["version"], self.version)
                self.assertEqual(self.service.state()["figure_name"], "Treatment response")
                invalid_name = await client.call_tool("rename_attempt", {"name": "not\na title"})
                self.assertTrue(invalid_name.is_error)
                denied = await client.call_tool("register_attempt", {"figure_dir": "../outside"})
                self.assertTrue(denied.is_error)
        asyncio.run(check())

    @unittest.skipUnless(importlib.util.find_spec("mcp"), "Optional MCP SDK is not installed")
    def test_mcp_defaults_follow_explicit_browser_review_focus_without_overwriting_it_on_startup(self):
        from easyviz_mcp import create_mcp
        from mcp import Client
        second_spec = {**self.spec, "colors": {"A": "#22AA99", "B": "#EE7799"}}
        second_path = self.root / "second-spec.json"
        second_path.write_text(json.dumps(second_spec))
        second_dir = self.root / "attempt-02"
        render.render(self.data, second_spec, second_dir, spec_path=second_path, track="create")
        second_id = self.service.register_attempt(second_dir)["id"]
        self.service.switch_attempt(second_id)
        state = self.service.state()
        note = self.service.app.change({"version": state["version"], "instruction": "Apply this instruction to the browser's currently reviewed figure."})["request"]
        connected = FigureService(self.root, self.attempt)
        self.assertNotEqual(connected.current_attempt_id, second_id)
        self.assertEqual(connected.review_attempt_id(), second_id)
        async def check():
            async with Client(create_mcp(connected), raise_exceptions=True) as client:
                attempt = await client.call_tool("get_attempt", {})
                self.assertEqual(attempt.structured_content["id"], second_id)
                renamed = await client.call_tool("rename_attempt", {"name": "Selected browser figure"})
                self.assertEqual(renamed.structured_content["attempt"]["id"], second_id)
                self.assertEqual(self.service.state()["figure_name"], "Selected browser figure")
                self.assertEqual(connected.get_attempt()["name"], self.attempt.name)
                requests = await client.call_tool("list_requests", {})
                self.assertEqual(requests.structured_content["attempt_id"], second_id)
                self.assertEqual(requests.structured_content["figure_name"], "Selected browser figure")
                self.assertEqual(requests.structured_content["requests"][0]["id"], note["id"])
                caps = await client.call_tool("capabilities", {})
                self.assertEqual(caps.structured_content["current_attempt_id"], second_id)
                jobs = await client.call_tool("list_jobs", {})
                self.assertEqual(jobs.structured_content, {"jobs": []})
        asyncio.run(check())

    @unittest.skipUnless(importlib.util.find_spec("mcp"), "Optional MCP SDK is not installed")
    def test_official_mcp_stdio_client_submits_and_observes_actual_core_preview(self):
        from mcp import Client
        from mcp.client.stdio import StdioServerParameters
        item = self.save()
        async def check():
            params = StdioServerParameters(command=sys.executable,
                args=[str(SCRIPTS / "easyviz_mcp.py"), "--project-dir", str(self.root), "--figure-dir", str(self.attempt)])
            async with Client(params) as client:
                self.assertIsNotNone(client.protocol_version)
                result = await client.call_tool("capabilities", {})
                self.assertFalse(result.is_error)
                self.assertTrue(result.structured_content["preview"]["supported"])
                launched = await client.call_tool("render_attempt", {"version": self.version, "request_ids": [item["id"]]})
                self.assertFalse(launched.is_error, launched)
                job_id = launched.structured_content["job"]["id"]
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    result = await client.call_tool("get_job", {"job_id": job_id})
                    self.assertFalse(result.is_error)
                    job = result.structured_content["job"]
                    if job["status"] not in figure_service.ACTIVE_STATUSES:
                        break
                    await asyncio.sleep(.05)
                self.assertEqual(job["status"], "succeeded", job)
                target = await client.call_tool("get_attempt", {"attempt_id": job["target_attempt_id"]})
                self.assertFalse(target.is_error)
                self.assertTrue(Path(target.structured_content["exports"]["pdf"]).read_bytes().startswith(b"%PDF"))
        asyncio.run(check())


if __name__ == "__main__":
    unittest.main()
