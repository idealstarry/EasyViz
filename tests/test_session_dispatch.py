"""Real-export checks for the original-conversation queue; no model inference."""
from __future__ import annotations

import concurrent.futures
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"
sys.path.insert(0, str(SCRIPTS))
import agent_dispatch
import ev_document
import figure_service
from figure_service import FigureService
from figure_workbench import WorkbenchError
import render


class SessionDispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-session-contract-")
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
        self.owner = os.environ.get("CODEX_THREAD_ID", "test-original-conversation")

    def tearDown(self):
        self.service.close()
        self.temp.cleanup()

    def connect(self):
        self.connection = self.service.connect_session(self.owner)
        self.token = self.connection["connection_token"]
        return self.connection

    def save(self, instruction="Make A purple"):
        return self.service.app.change({"version": self.version, "selector": None,
            "instruction": instruction, "property": None, "value": None})["request"]

    def submit(self, ids):
        return self.service.submit_agent_job(self.version, ids)["job"]

    def claim(self):
        return self.service.wait_for_submission(self.owner, self.token, 0)

    def fresh(self, *, unchanged=False, track="create"):
        target = self.root / "edited"
        if unchanged:
            shutil.copytree(self.attempt, target)
        else:
            target.mkdir()
            shutil.copy2(self.data, target / "data.csv")
            spec = {**self.spec, "colors": {"A": "#AA22BB", "B": "#11AA88"}}
            (target / "spec.json").write_text(json.dumps(spec))
            render.render(target / "data.csv", spec, target, spec_path=target / "spec.json", track=track)
        return self.service.register_attempt(target)

    def complete(self, job, target, ids, **extra):
        return self.service.complete_session_job(self.owner, self.token, job["id"], target["id"], ids,
            extra.get("changed_files", ["spec.json"]), "Rendered actual exports and inspected visible color change.")

    def test_connected_status_contains_no_credential_and_checks_original_host(self):
        connection = self.connect()
        status = self.service.agent_status()
        self.assertEqual(status["backend"], "session")
        self.assertEqual(status["owner_session_id"], self.owner)
        self.assertTrue(status["automatic_dispatch"])
        self.assertTrue(status["same_session"])
        self.assertFalse(status["existing_chat_wake"])
        self.assertGreater(status["lease_expires_at"], time.time())
        public = json.dumps({"status": status, "jobs": self.service.list_jobs()})
        self.assertNotIn(connection["connection_token"], public)
        registry = self.service.registry_path.read_text()
        self.assertNotIn(connection["connection_token"], registry)
        if os.environ.get("CODEX_THREAD_ID"):
            with self.assertRaisesRegex(WorkbenchError, "original Codex"):
                self.service.connect_session("different-conversation")
            with self.assertRaisesRegex(WorkbenchError, "original Codex"):
                self.service.connect_session("different-conversation", host="local-agent")

    def test_expired_and_disconnected_project_cannot_be_taken_by_another_conversation(self):
        self.connect()
        self.service.configure_agent("session", False)
        with patch.dict(os.environ, {"CODEX_THREAD_ID": ""}):
            with self.assertRaisesRegex(WorkbenchError, "ownership transfer"):
                self.service.connect_session("other-conversation", host="local-agent")
        renewed = self.service.connect_session(self.owner)
        self.assertEqual(renewed["owner_session_id"], self.owner)
        self.assertNotEqual(renewed["connection_token"], self.token)
        with patch.object(figure_service.time, "time", return_value=time.time() + 4000), \
                patch.dict(os.environ, {"CODEX_THREAD_ID": ""}):
            with self.assertRaisesRegex(WorkbenchError, "ownership transfer"):
                self.service.connect_session("other-conversation", host="local-agent")

    def test_live_queue_claim_fresh_export_completion_stays_same_session_without_process(self):
        with patch.object(agent_dispatch, "start_worker", side_effect=AssertionError("No fresh CLI allowed")) as start:
            self.connect()
            item = self.save()
            job = self.submit([item["id"]])
            self.assertEqual(job["owner_session_id"], self.owner)
            self.assertEqual(job["backend"], "session")
            self.assertEqual(job["status"], "queued")
            claimed = self.claim()
            self.assertEqual(claimed["job"]["id"], job["id"])
            self.assertEqual(claimed["job"]["status"], "running")
            self.assertEqual(claimed["job"]["phase"], "session_received")
            self.assertIn("received_at", claimed["job"])
            self.assertNotIn("editing_started_at", claimed["job"])
            self.assertEqual(claimed["plan"]["requests"][0]["instruction"], item["instruction"])
            target = self.fresh()
            result = self.complete(job, target, [item["id"]])
            self.assertEqual(result["job"]["status"], "succeeded")
            self.assertEqual(result["job"]["owner_session_id"], self.owner)
            self.assertEqual(result["job"]["target_attempt_id"], target["id"])
            self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "applied")
            self.assertTrue((self.root / "edited/panel.ev").is_file())
            self.assertEqual(self.submit([item["id"]])["id"], job["id"])
            self.assertFalse(self.service._threads)
            start.assert_not_called()

    def test_completed_preview_retains_original_custom_name_in_ui_mcp_and_document(self):
        name = "HDR repair · session workflow"
        self.service.rename_attempt(name)
        self.connect()
        item = self.save()
        job = self.submit([item["id"]])
        self.assertEqual(self.claim()["plan"]["figure_name"], name)
        target = self.fresh()
        target_path = Path(target["path"])
        self.assertFalse((target_path / "figure-info.json").exists())
        result = self.complete(job, target, [item["id"]])
        self.assertEqual(result["attempt"]["name"], name)
        self.assertEqual(result["attempt"]["version"], target["version"])
        self.assertEqual(self.service.switch_attempt(target["id"])["state"]["figure_name"], name)
        self.assertEqual(ev_document.inspect_document(target_path / "panel.ev")["name"], name)
        self.assertEqual(json.loads((target_path / "figure-info.json").read_text())["display_name"], name)
        self.assertNotIn(name, (target_path / "panel.svg").read_text())
        self.assertEqual(self.service.attempt_app(job["source_attempt_id"]).state()["version"], self.version)
        if importlib.util.find_spec("mcp"):
            from easyviz_mcp import create_mcp
            from mcp import Client
            async def check_mcp_name():
                async with Client(create_mcp(self.service), raise_exceptions=True) as client:
                    received = await client.call_tool("get_attempt", {})
                    self.assertEqual(received.structured_content["id"], target["id"])
                    self.assertEqual(received.structured_content["name"], name)
                    listed = await client.call_tool("list_attempts", {})
                    self.assertEqual(next(entry["name"] for entry in listed.structured_content["attempts"]
                                          if entry["id"] == target["id"]), name)
            asyncio.run(check_mcp_name())

    def test_completion_preserves_an_explicit_result_name(self):
        self.service.rename_attempt("Original reviewed name")
        self.connect()
        item = self.save()
        job = self.submit([item["id"]])
        self.claim()
        target = self.fresh()
        name = "Explicit revised figure"
        self.service.rename_attempt(name, target["id"])
        result = self.complete(job, target, [item["id"]])
        self.assertEqual(result["attempt"]["name"], name)
        self.assertEqual(self.service.switch_attempt(target["id"])["state"]["figure_name"], name)
        self.assertEqual(ev_document.inspect_document(Path(target["path"]) / "panel.ev")["name"], name)

    def test_rename_refreshes_existing_disk_document_without_reexport_by_caller(self):
        document = ev_document.export_document(self.attempt)
        self.assertEqual(ev_document.inspect_document(document)["name"], "original")
        name = "HDR repair · session workflow"
        result = self.service.rename_attempt(name)
        self.assertNotIn("document_warning", result)
        self.assertEqual(result["attempt"]["name"], name)
        self.assertEqual(ev_document.inspect_document(document)["name"], name)
        self.assertEqual(json.loads((self.attempt / "document-status.json").read_text())["status"], "ready")
        self.assertEqual(self.service.state()["version"], self.version)
        if importlib.util.find_spec("mcp"):
            from easyviz_mcp import create_mcp
            from mcp import Client
            async def rename_via_mcp():
                async with Client(create_mcp(self.service), raise_exceptions=True) as client:
                    renamed = await client.call_tool("rename_attempt", {"name": "Renamed through original MCP"})
                    self.assertFalse(renamed.is_error)
                    self.assertNotIn("document_warning", renamed.structured_content)
                    self.assertEqual(ev_document.inspect_document(document)["name"], "Renamed through original MCP")
            asyncio.run(rename_via_mcp())

    def test_stale_source_rename_keeps_name_and_marks_old_document_warning(self):
        document = ev_document.export_document(self.attempt)
        figure_service._refresh_document(self.attempt)
        old_document = document.read_bytes()
        self.data.write_text(self.data.read_text() + "3,6,B\n")
        result = self.service.rename_attempt("Saved despite source change")
        self.assertEqual(result["attempt"]["name"], "Saved despite source change")
        self.assertFalse(result["attempt"]["source_current"])
        self.assertIn("document_warning", result)
        self.assertEqual(document.read_bytes(), old_document)
        status = json.loads((self.attempt / "document-status.json").read_text())
        self.assertEqual(status["status"], "warning")
        self.assertEqual(status["message"], result["document_warning"])
        self.assertEqual(ev_document.inspect_document(document)["name"], "original")

    def test_manual_receipt_cannot_consume_queued_or_claimed_session_requests(self):
        self.connect()
        item = self.save()
        job = self.submit([item["id"]])
        target = self.fresh()
        for stage in ("queued", "running"):
            with self.subTest(stage=stage):
                with self.assertRaisesRegex(WorkbenchError, "complete_session_job"):
                    self.service.record_outcome(job["source_attempt_id"], target["id"], [item["id"]],
                        ["spec.json"], "Rendered fresh source and checked actual exports.")
                self.assertEqual(self.service.get_job(job["id"])["job"]["status"], stage)
                self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")
            if stage == "queued":
                self.claim()
        self.assertEqual(self.complete(job, target, [item["id"]])["job"]["status"], "succeeded")
        following = self.save("Review another visible cosmetic change")
        self.assertEqual(self.submit([following["id"]])["status"], "queued")

    def test_manual_saved_request_flow_without_submitted_job_still_commits(self):
        self.connect()
        item = self.save()
        target = self.fresh()
        result = self.service.record_outcome(self.service.current_attempt_id, target["id"], [item["id"]],
            ["spec.json"], "Rendered fresh source and checked actual exports.")
        self.assertEqual(result["outcome"]["request_ids"], [item["id"]])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "applied")
        self.assertEqual(self.service.list_jobs()["jobs"], [])

    def test_manual_receipt_does_not_block_unrelated_pending_request_during_active_job(self):
        self.connect()
        owned, manual = self.save(), self.save("Set B green after checking contrast")
        job = self.submit([owned["id"]])
        self.claim()
        target = self.fresh()
        self.service.record_outcome(job["source_attempt_id"], target["id"], [manual["id"]],
            ["spec.json"], "Rendered A purple and B green without changing data.")
        statuses = {item["id"]: item["status"] for item in self.service.app.ledger()["requests"]}
        self.assertEqual(statuses, {owned["id"]: "pending", manual["id"]: "applied"})
        self.assertEqual(self.service.get_job(job["id"])["job"]["status"], "running")
        self.assertEqual(self.complete(job, target, [owned["id"]])["job"]["status"], "succeeded")

    def test_submit_revalidates_pending_ids_after_manual_receipt_wins_preparation_race(self):
        self.connect()
        item = self.save()
        target = self.fresh()
        other = FigureService(self.root, self.attempt)
        prepared, release = threading.Event(), threading.Event()
        prepare = self.service.prepare_edits
        def paused_prepare(*args, **kwargs):
            plan = prepare(*args, **kwargs)
            prepared.set()
            if not release.wait(3):
                raise AssertionError("Manual receipt did not release the prepared submission")
            return plan
        try:
            with patch.object(self.service, "prepare_edits", side_effect=paused_prepare), \
                    concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                submission = executor.submit(self.submit, [item["id"]])
                try:
                    self.assertTrue(prepared.wait(2))
                    other.record_outcome(self.service.current_attempt_id, target["id"], [item["id"]],
                        ["spec.json"], "Manual rendering and actual exports inspected before queue publication.")
                finally:
                    release.set()
                with self.assertRaisesRegex(WorkbenchError, "Only pending requests"):
                    submission.result(3)
            self.assertEqual(self.service.list_jobs()["jobs"], [])
            self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "applied")
        finally:
            release.set()
            other.close()

    def test_other_service_does_not_recover_live_session_as_abandoned(self):
        self.connect()
        item = self.save()
        job = self.submit([item["id"]])
        self.claim()
        other = FigureService(self.root, self.attempt)
        try:
            self.assertEqual(other.get_job(job["id"])["job"]["status"], "running")
            self.assertEqual(other.agent_status()["owner_session_id"], self.owner)
        finally:
            other.close()
        self.assertEqual(self.service.get_job(job["id"])["job"]["status"], "running")

    def test_closed_service_cannot_claim_queued_requests(self):
        self.connect()
        item = self.save()
        job = self.submit([item["id"]])
        self.service.close()
        self.assertIsNone(self.claim()["job"])
        self.assertEqual(self.service.get_job(job["id"])["job"]["status"], "queued")

    def test_cancelled_delivery_releases_only_unstarted_claim(self):
        self.connect()
        item = self.save()
        job = self.submit([item["id"]])
        cancelled = threading.Event()
        prepare = self.service.prepare_edits
        def cancel_delivery(*args, **kwargs):
            plan = prepare(*args, **kwargs)
            cancelled.set()
            return plan
        with patch.object(self.service, "prepare_edits", side_effect=cancel_delivery):
            result = self.service.wait_for_submission(self.owner, self.token, 0, cancellation_event=cancelled)
        self.assertIsNone(result["job"])
        self.assertEqual(self.service.get_job(job["id"])["job"]["status"], "queued")
        self.assertEqual(self.claim()["job"]["id"], job["id"])
        self.service.report_session_progress(self.owner, self.token, job["id"])
        self.service._release_session_claim(self.owner, self.token, job["id"])
        self.assertEqual(self.service.get_job(job["id"])["job"]["phase"], "session_editing")
        self.service.cancel_job(job["id"])
        self.service._release_session_claim(self.owner, self.token, job["id"])
        self.assertEqual(self.service.get_job(job["id"])["job"]["status"], "cancelled")

    @unittest.skipUnless(importlib.util.find_spec("mcp"), "Optional MCP SDK is not installed")
    def test_real_mcp_sdk_cancelled_listener_cannot_claim_later_submission(self):
        from easyviz_mcp import create_mcp
        self.connect()
        item = self.save()
        started = threading.Event()
        original = self.service.wait_for_submission
        def tracked_wait(*args, **kwargs):
            started.set()
            return original(*args, **kwargs)
        async def exercise():
            with patch.object(self.service, "wait_for_submission", side_effect=tracked_wait):
                server = create_mcp(self.service)
                task = asyncio.create_task(server.call_tool("wait_for_submission", {
                    "owner_session_id": self.owner, "connection_token": self.token, "timeout_seconds": 3}))
                self.assertTrue(await asyncio.to_thread(started.wait, 2))
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                job = await asyncio.to_thread(self.submit, [item["id"]])
                await asyncio.sleep(.3)
                self.assertEqual(self.service.get_job(job["id"])["job"]["status"], "queued")
                received = await asyncio.to_thread(self.claim)
                self.assertEqual(received["job"]["id"], job["id"])
        asyncio.run(exercise())

    def test_progress_requires_actual_stage_reports_and_keeps_first_start_times(self):
        self.connect()
        item = self.save()
        job = self.submit([item["id"]])
        self.claim()
        with self.assertRaisesRegex(WorkbenchError, "as each actually begins"):
            self.service.report_session_progress(self.owner, self.token, job["id"], "reviewing")
        editing = self.service.report_session_progress(self.owner, self.token, job["id"])["job"]
        self.assertEqual(editing["phase"], "session_editing")
        self.assertIn("editing_started_at", editing)
        repeated = self.service.report_session_progress(self.owner, self.token, job["id"])["job"]
        self.assertEqual(repeated["editing_started_at"], editing["editing_started_at"])
        rendered = self.service.report_session_progress(self.owner, self.token, job["id"], "rendering")["job"]
        self.assertIn("rendering_started_at", rendered)
        with self.assertRaisesRegex(WorkbenchError, "backwards"):
            self.service.report_session_progress(self.owner, self.token, job["id"], "editing")
        reviewed = self.service.report_session_progress(self.owner, self.token, job["id"], "reviewing")["job"]
        self.assertIn("reviewing_started_at", reviewed)
        self.assertEqual(reviewed["received_at"], editing["received_at"])

    def test_progress_requires_claimed_job_and_correct_owner_credential(self):
        self.connect()
        item = self.save()
        job = self.submit([item["id"]])
        with self.assertRaisesRegex(WorkbenchError, "claimed active"):
            self.service.report_session_progress(self.owner, self.token, job["id"])
        self.claim()
        with self.assertRaisesRegex(WorkbenchError, "ownership credential"):
            self.service.report_session_progress(self.owner, "wrong-token", job["id"])
        self.service.cancel_job(job["id"])
        with self.assertRaisesRegex(WorkbenchError, "claimed active"):
            self.service.report_session_progress(self.owner, self.token, job["id"])
        self.assertNotIn("editing_started_at", self.service.get_job(job["id"])["job"])

    def test_wrong_credentials_cannot_claim_disconnect_or_complete(self):
        self.connect()
        item = self.save()
        job = self.submit([item["id"]])
        with self.assertRaisesRegex(WorkbenchError, "ownership credential"):
            self.service.wait_for_submission("wrong-owner", self.token, 0)
        with self.assertRaisesRegex(WorkbenchError, "ownership credential"):
            self.service.disconnect_session(self.owner, "wrong-token")
        self.assertEqual(self.service.get_job(job["id"])["job"]["status"], "queued")
        self.claim()
        target = self.fresh()
        with self.assertRaisesRegex(WorkbenchError, "ownership credential"):
            self.service.complete_session_job(self.owner, "wrong-token", job["id"], target["id"],
                                              [item["id"]], ["spec.json"], "Actual visible review")
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")

    def test_only_one_listener_claims_cross_process_compatible_shared_registry(self):
        self.connect()
        item = self.save()
        self.submit([item["id"]])
        other = FigureService(self.root, self.attempt)
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda service: service.wait_for_submission(self.owner, self.token, 0),
                                            [self.service, other]))
            self.assertEqual(sum(result["job"] is not None for result in results), 1)
        finally:
            other.close()

    def test_partial_completion_preserves_omitted_requests(self):
        self.connect()
        first, second = self.save(), self.save("Move legend after reviewing labels")
        job = self.submit([first["id"], second["id"]])
        self.claim()
        target = self.fresh()
        result = self.complete(job, target, [first["id"]])
        self.assertEqual(result["job"]["agent_request_ids"], [second["id"]])
        self.assertEqual({item["id"]: item["status"] for item in self.service.app.ledger()["requests"]},
                         {first["id"]: "applied", second["id"]: "pending"})

    def committed_crash_window(self, *, partial=False):
        self.connect()
        item = self.save()
        omitted = self.save("Keep legend position for later") if partial else None
        job = self.submit([item["id"], omitted["id"]] if omitted else [item["id"]])
        self.claim()
        target = self.fresh()
        completed = self.complete(job, target, [item["id"]])
        registry = json.loads(self.service.registry_path.read_text())
        owned = next(entry for entry in registry["jobs"] if entry["id"] == job["id"])
        owned.update(status="running", phase="session_editing", target_attempt_id=None, outcome_id=None)
        owned["agent_request_ids"] = owned["request_ids"][:]
        figure_service._atomic_json(self.service.registry_path, registry)
        return job, completed["outcome"]["id"]

    def test_live_owner_reopen_recovers_committed_receipt_before_live_job_skip(self):
        job, outcome_id = self.committed_crash_window()
        other = FigureService(self.root, self.attempt)
        try:
            recovered = other.get_job(job["id"])["job"]
            self.assertEqual(recovered["status"], "succeeded")
            self.assertEqual(recovered["outcome_id"], outcome_id)
            self.assertEqual(recovered["agent_request_ids"], [])
        finally:
            other.close()

    def test_cancel_cannot_label_already_committed_session_result_cancelled(self):
        job, outcome_id = self.committed_crash_window()
        recovered = self.service.cancel_job(job["id"])["job"]
        self.assertEqual(recovered["status"], "succeeded")
        self.assertEqual(recovered["outcome_id"], outcome_id)

    def test_disconnect_recovers_real_receipt_and_keeps_connection_disabled(self):
        job, outcome_id = self.committed_crash_window()
        self.service.configure_agent("session", False)
        recovered = self.service.get_job(job["id"])["job"]
        self.assertEqual(recovered["status"], "succeeded")
        self.assertEqual(recovered["outcome_id"], outcome_id)
        self.assertFalse(self.service.agent_status()["enabled"])

    def test_recovered_partial_receipt_reports_only_unfulfilled_requests_pending(self):
        job, outcome_id = self.committed_crash_window(partial=True)
        other = FigureService(self.root, self.attempt)
        try:
            recovered = other.get_job(job["id"])["job"]
            self.assertEqual(recovered["outcome_id"], outcome_id)
            self.assertEqual(recovered["agent_request_ids"], job["request_ids"][1:])
        finally:
            other.close()

    def test_cancel_during_claim_preparation_never_delivers_stale_running_job(self):
        self.connect()
        item = self.save()
        job = self.submit([item["id"]])
        prepare = self.service.prepare_edits
        def cancelled_plan(*args, **kwargs):
            result = prepare(*args, **kwargs)
            self.service.cancel_job(job["id"])
            return result
        with patch.object(self.service, "prepare_edits", side_effect=cancelled_plan):
            self.assertIsNone(self.claim()["job"])
        self.assertEqual(self.service.get_job(job["id"])["job"]["status"], "cancelled")

    def test_cancelled_claim_is_not_overwritten_by_prepare_failure(self):
        self.connect()
        item = self.save()
        job = self.submit([item["id"]])
        def cancelled_error(*args, **kwargs):
            self.service.cancel_job(job["id"])
            raise WorkbenchError("Source changed after cancellation")
        with patch.object(self.service, "prepare_edits", side_effect=cancelled_error):
            with self.assertRaisesRegex(WorkbenchError, "Source changed"):
                self.claim()
        self.assertEqual(self.service.get_job(job["id"])["job"]["status"], "cancelled")

    def test_expiry_and_disconnect_leave_pending_and_never_fallback(self):
        self.connect()
        item = self.save()
        job = self.submit([item["id"]])
        with patch.object(figure_service.time, "time", return_value=time.time() + 4000), \
                patch.object(agent_dispatch, "start_worker") as start:
            self.assertFalse(self.service.agent_status()["automatic_dispatch"])
            self.assertEqual(self.service.agent_status()["runtime_state"], "expired")
            with self.assertRaisesRegex(WorkbenchError, "Reconnect"):
                self.submit([item["id"]])
            with self.assertRaisesRegex(WorkbenchError, "expired"):
                self.claim()
            start.assert_not_called()
        self.service.configure_agent("session", False)
        self.assertEqual(self.service.get_job(job["id"])["job"]["status"], "cancelled")
        self.assertFalse(self.service.agent_status()["enabled"])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")

    def test_unchanged_result_rejected_without_application(self):
        self.connect()
        item = self.save()
        job = self.submit([item["id"]])
        self.claim()
        target = self.fresh(unchanged=True)
        with self.assertRaisesRegex(WorkbenchError, "changed SVG"):
            self.complete(job, target, [item["id"]])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")

    def test_tampered_qa_result_and_unclaimed_job_cannot_complete(self):
        self.connect()
        item = self.save()
        job = self.submit([item["id"]])
        target = self.fresh()
        with self.assertRaisesRegex(WorkbenchError, "claimed active"):
            self.complete(job, target, [item["id"]])
        self.claim()
        qa_path = self.root / "edited/qa.json"
        qa = json.loads(qa_path.read_text())
        qa["exports"]["svg"]["sha256"] = "0" * 64
        qa_path.write_text(json.dumps(qa))
        with self.assertRaises(WorkbenchError):
            self.complete(job, target, [item["id"]])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")

    def test_mutable_metadata_cannot_reduce_adopted_bound_pdf_and_png_exports(self):
        self.service.close()
        full_spec = {**self.spec, "formats": ["svg", "pdf", "png"]}
        self.spec_path.write_text(json.dumps(full_spec))
        render.render(self.data, full_spec, self.attempt, spec_path=self.spec_path, track="create")
        self.service = FigureService(self.root, self.attempt)
        self.version = self.service.state()["version"]
        settings_path = self.attempt / "settings.json"
        settings = json.loads(settings_path.read_text())
        settings["formats"] = ["svg"]
        settings_path.write_text(json.dumps(settings))
        self.assertTrue(self.service.state()["source_current"])
        self.connect()
        item = self.save()
        job = self.submit([item["id"]])
        self.assertEqual(job["adopted_formats"], ["svg", "pdf", "png"])
        self.claim()
        target = self.fresh()
        with self.assertRaises(WorkbenchError):
            self.complete(job, target, [item["id"]])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")

    def register_controlled_host_trigger(self, *, expires_at=None):
        # Isolated registration fixture; it does not create or verify an actual host automation.
        return self.service.register_session_trigger(self.owner, self.token, "test-native-heartbeat-id", 60,
                                                     expires_at or time.time() + 7200)

    def test_host_check_is_optional_and_registration_is_owner_authenticated(self):
        self.connect()
        self.assertFalse(self.service.agent_status()["existing_chat_wake"])
        with self.assertRaisesRegex(WorkbenchError, "ownership credential"):
            self.service.register_session_trigger(self.owner, "wrong-token", "native-check", 60, time.time() + 120)
        for interval, expiry in [(1, time.time() + 120), (60, float("inf")), (60, time.time() - 1)]:
            with self.assertRaises(WorkbenchError):
                self.service.register_session_trigger(self.owner, self.token, "native-check", interval, expiry)
        registered = self.register_controlled_host_trigger()
        self.assertTrue(registered["live_listener"])
        self.assertTrue(registered["scheduled_dispatch"])
        self.assertEqual(registered["host_trigger"]["verification"], "owner_registered")
        self.assertNotIn(self.token, json.dumps(registered))

    def test_registered_host_queue_survives_short_lease_and_reconnects_only_same_owner(self):
        self.connect()
        self.register_controlled_host_trigger()
        item = self.save()
        future = time.time() + 4000
        with patch.object(figure_service.time, "time", return_value=future):
            status = self.service.agent_status()
            self.assertFalse(status["live_listener"])
            self.assertTrue(status["scheduled_dispatch"])
            self.assertEqual(status["dispatch_mode"], "host_heartbeat")
            job = self.submit([item["id"]])
            other = FigureService(self.root, self.attempt)
            try:
                self.assertEqual(other.get_job(job["id"])["job"]["status"], "queued")
                with patch.dict(os.environ, {"CODEX_THREAD_ID": ""}):
                    with self.assertRaisesRegex(WorkbenchError, "ownership transfer"):
                        other.connect_session("different-original-conversation")
                renewed = other.connect_session(self.owner)
                self.assertNotEqual(renewed["connection_token"], self.token)
                rebound = other.get_job(job["id"])["job"]
                self.assertEqual(rebound["connection_id"], renewed["connection_id"])
                self.assertEqual(other.submit_agent_job(self.version, [item["id"]])["job"]["id"], job["id"])
                received = other.wait_for_submission(self.owner, renewed["connection_token"], 0)
                self.assertEqual(received["job"]["id"], job["id"])
                self.assertEqual(received["plan"]["requests"][0]["id"], item["id"])
                with self.assertRaisesRegex(WorkbenchError, "ownership credential"):
                    self.claim()
            finally:
                other.close()

    def test_trigger_expiry_or_disable_does_not_accept_after_listener_lease_expiry(self):
        self.connect()
        self.register_controlled_host_trigger()
        item = self.save()
        future = time.time() + 8000
        with patch.object(figure_service.time, "time", return_value=future):
            self.assertFalse(self.service.agent_status()["existing_chat_wake"])
            with self.assertRaisesRegex(WorkbenchError, "Reconnect"):
                self.submit([item["id"]])
        self.service.disable_session_trigger(self.owner, self.token)
        with patch.object(figure_service.time, "time", return_value=time.time() + 4000):
            self.assertFalse(self.service.agent_status()["scheduled_dispatch"])
            with self.assertRaisesRegex(WorkbenchError, "Reconnect"):
                self.submit([item["id"]])

    def test_expired_running_job_is_not_preserved_by_scheduled_trigger(self):
        self.connect()
        self.register_controlled_host_trigger()
        item = self.save()
        job = self.submit([item["id"]])
        self.claim()
        future = time.time() + 4000
        with patch.object(figure_service.time, "time", return_value=future):
            other = FigureService(self.root, self.attempt)
            try:
                self.assertEqual(other.get_job(job["id"])["job"]["status"], "failed")
                renewed = other.connect_session(self.owner)
                self.assertIsNone(other.wait_for_submission(self.owner, renewed["connection_token"], 0)["job"])
            finally:
                other.close()
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")

    def test_existing_private_credential_renews_only_live_owner_connection(self):
        self.connect()
        connection_id = self.connection["connection_id"]
        before = self.service.agent_status()["lease_expires_at"]
        with patch.object(figure_service.time, "time", return_value=time.time() + 10):
            result = self.service.renew_same_session(self.owner, self.token)
        self.assertEqual(result["connection_id"], connection_id)
        self.assertGreater(result["status"]["lease_expires_at"], before)
        with self.assertRaisesRegex(WorkbenchError, "ownership credential"):
            self.service.renew_same_session("different-owner", self.token)
        self.register_controlled_host_trigger()
        with patch.object(figure_service.time, "time", return_value=time.time() + 4000):
            with self.assertRaisesRegex(WorkbenchError, "ownership credential"):
                self.service.renew_same_session(self.owner, self.token)

    def test_disconnect_disables_trigger_without_reactivating_it_on_reconnect(self):
        self.connect()
        self.register_controlled_host_trigger()
        item = self.save()
        job = self.submit([item["id"]])
        self.service.configure_agent("session", False)
        self.assertEqual(self.service.get_job(job["id"])["job"]["status"], "cancelled")
        self.service.connect_session(self.owner)
        self.assertFalse(self.service.agent_status()["scheduled_dispatch"])
        self.assertFalse(self.service.agent_status()["existing_chat_wake"])

    def test_second_jobs_cancel_completion_and_invalid_wait_are_guarded(self):
        self.connect()
        first, second = self.save(), self.save("Keep all observations")
        job = self.submit([first["id"]])
        with self.assertRaisesRegex(WorkbenchError, "active"):
            self.submit([second["id"]])
        with self.assertRaisesRegex(WorkbenchError, "active"):
            self.service.submit_job(self.version, [second["id"]])
        with self.assertRaisesRegex(WorkbenchError, "0 to 45"):
            self.service.wait_for_submission(self.owner, self.token, 46)
        self.claim()
        self.service.cancel_job(job["id"])
        target = self.fresh()
        with self.assertRaisesRegex(WorkbenchError, "claimed active"):
            self.complete(job, target, [first["id"]])
        self.assertEqual(self.service.app.ledger()["requests"][0]["status"], "pending")


if __name__ == "__main__":
    unittest.main()
