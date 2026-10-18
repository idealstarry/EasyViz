"""Element selection must be unambiguous without requiring an .ev export."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"
sys.path.insert(0, str(SCRIPTS))
from ev_document import EVDocumentError, export_document
from figure_handoff import capture_inputs, write_receipt
from figure_workbench import FigureWorkbench, WorkbenchError


class WorkbenchMapValidationTests(unittest.TestCase):
    def test_duplicate_actual_svg_ids_disable_selection_but_preserve_source_bound_notes(self):
        for keep_receipt in (False, True):
            with self.subTest(source_receipt=keep_receipt), tempfile.TemporaryDirectory(prefix="easyviz-map-validation-") as temporary:
                root = Path(temporary).resolve()
                attempt = root / "attempt"
                attempt.mkdir()
                data, source, spec = (root / name for name in ("source.csv", "plot.py", "spec.json"))
                data.write_text("sample,x,y\n001,1,2\n")
                source.write_text("# Captured source; the workbench must not execute it.\n")
                spec.write_text(json.dumps({"chart": "custom", "formats": ["svg"]}))
                capture = capture_inputs(attempt, data_file=data, source_script=source, spec_file=spec)
                svg = (b'<svg xmlns="http://www.w3.org/2000/svg" width="120mm" height="60mm" viewBox="0 0 240 120">'
                       b'<g id="data"><circle cx="70" cy="80" r="3"/></g>'
                       b'<g id="data"><circle cx="150" cy="80" r="3"/></g></svg>')
                (attempt / "panel.svg").write_bytes(svg)
                (attempt / "settings.json").write_text(json.dumps({"track": "create"}))
                (attempt / "qa.json").write_text(json.dumps({"status": "pass", "valid_outputs": True,
                    "exports": {"svg": {"sha256": hashlib.sha256(svg).hexdigest()}}}))
                receipt = write_receipt(attempt, capture=capture, formats=["svg"], track="create")
                (attempt / "elements.json").write_text(json.dumps({"schema_version": 1,
                    "version": receipt["version"], "input": receipt["input"], "panel": receipt["panel"],
                    "elements": [{"id": "data", "role": "point-group", "label": "Sample 001",
                                  "source_keys": [{"sample": "001"}], "spec_paths": [], "editable": []}]}))
                if not keep_receipt:
                    (attempt / "handoff.json").unlink()

                app = FigureWorkbench(attempt)
                state = app.state()
                self.assertFalse(state["manifest_valid"])
                self.assertEqual(state["elements"], [])
                self.assertIn("duplicate element IDs", state["selection_message"])
                self.assertTrue(state["provenance_valid"])
                self.assertTrue(state["source_current"])
                self.assertEqual(state["version"], receipt["version"])
                self.assertEqual(state["input"], receipt["input"])
                self.assertFalse((attempt / "panel.ev").exists())

                with self.assertRaisesRegex(WorkbenchError, "unavailable"):
                    app.change({"version": state["version"], "element_id": "data", "instruction": "Move this point."})
                self.assertEqual(app.ledger()["requests"], [])
                for request in ({"instruction": "Inspect both points."},
                                {"instruction": "Move the left group.", "region_mm": {"x": 20, "y": 20, "width": 30, "height": 25}}):
                    saved = app.change({"version": state["version"], **request})["request"]
                    self.assertEqual(saved["input"], receipt["input"])
                    self.assertEqual(saved["status"], "pending")
                with self.assertRaises(EVDocumentError):
                    export_document(attempt)


if __name__ == "__main__":
    unittest.main()
