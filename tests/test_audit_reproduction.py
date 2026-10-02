"""Complex reproduction audit checks file-bound numeric/geometry invariants."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"


def load(name):
    loader = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


packet = load("reference_packet")
checker = load("audit_reproduction")


class AuditReproductionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-reproduce-audit-")
        self.root = Path(self.temp.name)
        self.reference = self.root / "reference.png"
        self.reference.write_bytes(b"reference bytes: no image semantics tested")
        self.data = self.root / "observations.csv"
        self.data.write_text("id,time,value,condition\n001,0,1,Control\nNA,2,3,Treatment\nnull,6,2,Control\n", encoding="utf-8")
        self.metadata = self.root / "metadata.csv"
        self.metadata.write_text("id,score\n001,0.4\nNA,0.8\nnull,0.6\n", encoding="utf-8")
        reading = packet.reading_template(packet.sha256(self.reference))
        reading["reader"].update(agent_id="reader", independence="main-agent", image_viewed=True)
        reading["reference"]["region"] = "whole image"
        reading["evidence"] = [
            {"id": "E1", "property": "layers.points", "description": "Upper points and lower aligned track", "state": "observed", "source": "reference", "uncertainty": ""},
        ]
        reading["layers"] = [
            {"id": "points", "evidence_ids": ["E1"], "description": "Raw points", "required_data_meanings": ["time", "value"]},
            {"id": "track", "evidence_ids": ["E1"], "description": "Lower aligned track", "required_data_meanings": ["score"]},
        ]
        reading_path = self.root / "reading.json"
        reading_path.write_text(json.dumps(reading), encoding="utf-8")
        self.directory = self.root / "packet"
        packet.build(self.reference, [self.data, self.metadata], self.directory, reading_path=reading_path, custom_script="implementation/panel.py")
        self.plan_path = self.directory / "implementation-plan.json"
        self.plan = json.loads(self.plan_path.read_text())
        self.write("implementation/panel.py", "# Recorded implementation fixture; not executed by the checker.\n")
        self.write("output/panel.pdf", "%PDF-export evidence bytes\n")
        self.write("output/panel.png", "PNG-export evidence bytes\n")
        self.svg()
        self.write("output/points.csv", "id,artist_x,artist_y,condition\n001,0,1,Control\nNA,2,3,Treatment\nnull,6,2,Control\n")
        self.write("output/track.csv", "id,artist_score\n001,0.4\nNA,0.8\nnull,0.6\n")
        self.plan["layout"].update(width_mm=120, height_mm=90)
        for layer in self.plan["layers"]:
            name = layer["source_layer_id"]
            artifact = "data-1" if name == "points" else "data-2"
            layer.update(status="implemented", data_artifacts=[artifact],
                         field_mapping={"value": {"artifact": artifact, "field": "value" if name == "points" else "score", "unit": "signal"}},
                         transform="none; all source rows retained", artist="point collection" if name == "points" else "rectangular track", backend="matplotlib in data coordinates",
                         adoption={"decision": "preserve", "priority": "required", "reason": "Preserve the observed layer and alignment"})
            layer["verification"] = [{"kind": "numeric", "source_artifact": artifact, "source_keys": ["id"], "source_fields": ["time", "value"] if name == "points" else ["score"],
                                       "target": f"output/{name}.csv", "target_sha256": self.hash(f"output/{name}.csv"), "target_keys": ["id"], "target_fields": ["artist_x", "artist_y"] if name == "points" else ["artist_score"], "atol": 1e-12}]
        self.plan["audit"] = {
            "version": 1, "script": self.binding("implementation/panel.py"),
            "outputs": [{"format": kind, **self.binding(f"output/panel.{kind}")} for kind in ("svg", "pdf", "png")],
            "axes": [
                {"id": "main-x", "dimension": "x", "scale": "linear", "unit": "h", "domain": [0, 6], "plot_box_svg_id": "upper-box", "shared_with": ["track-x"]},
                {"id": "track-x", "dimension": "x", "scale": "linear", "unit": "h", "domain": [0, 6], "plot_box_svg_id": "lower-box", "shared_with": []},
            ],
            "joins": [{"id": "metadata", "left": {"artifact": "data-1", "keys": ["id"]}, "right": {"artifact": "data-2", "keys": ["id"]}, "cardinality": "one-to-one", "coverage": "both"}],
            "guides": [{"id": "condition-color", "kind": "categorical", "svg_ids": ["legend"], "meaning": "Condition color", "mapping": {"Control": "#2581B9", "Treatment": "#DF9A3C"}}],
            "bindings": [
                {"layer": "points", "svg_ids": ["point-artists"], "axes": ["main-x"], "joins": [], "guides": ["condition-color"]},
                {"layer": "track", "svg_ids": ["track-artists"], "axes": ["track-x"], "joins": ["metadata"], "guides": []},
            ],
        }

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, text):
        path = self.directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def hash(self, name):
        return hashlib.sha256((self.directory / name).read_bytes()).hexdigest()

    def binding(self, name):
        return {"path": name, "sha256": self.hash(name)}

    def svg(self, left=20, width=70, *, physical_width=120, transform=""):
        self.write("output/panel.svg", f'<svg xmlns="http://www.w3.org/2000/svg" width="{physical_width}mm" height="90mm" viewBox="0 0 120 90"><g id="upper-box"><path d="M 20 10 L 90 10 L 90 50 L 20 50 z"/></g><g id="lower-box" {transform}><rect x="{left}" y="65" width="{width}" height="12"/></g><g id="point-artists"/><g id="track-artists"/><g id="legend"/></svg>')

    def run_audit(self):
        self.plan_path.write_text(json.dumps(self.plan), encoding="utf-8")
        return checker.audit_plan(self.directory)

    def codes(self, result, name="errors"):
        return {item["code"] for item in result[name]}

    def rehash_svg(self):
        self.plan["audit"]["outputs"][0].update(self.binding("output/panel.svg"))

    def test_file_bound_sources_numeric_values_and_actual_svg_alignment_pass(self):
        result = self.run_audit()
        self.assertEqual(result["status"], "passed-recorded-checks", result)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["missing_evidence"], [])
        alignment = [item for item in result["checks"] if item["kind"] == "svg-shared-axis-alignment"]
        self.assertEqual(alignment[0]["bounds_mm"], [[20, 10, 70, 40], [20, 65, 70, 12]])
        self.assertEqual([item["source_records"] for item in result["checks"] if item["kind"] == "numeric"], [3, 3])
        for claim in ("reader_independence_verified", "semantic_correctness_verified", "visual_review_passed"):
            self.assertFalse(result[claim])

    def test_real_matplotlib_svg_patch_and_artist_value_export_are_supported(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=(120 / 25.4, 90 / 25.4))
        try:
            upper = fig.add_axes([20 / 120, 40 / 90, 70 / 120, 40 / 90])
            lower = fig.add_axes([20 / 120, 13 / 90, 70 / 120, 12 / 90])
            upper.patch.set_gid("upper-box")
            lower.patch.set_gid("lower-box")
            points = upper.scatter([0, 2, 6], [1, 3, 2], label="Control")
            points.set_gid("point-artists")
            track, = lower.plot([0, 2, 6], [.4, .8, .6])
            track.set_gid("track-artists")
            upper.legend().set_gid("legend")
            for ax in (upper, lower):
                ax.set_xlim(0, 6)
            fig.savefig(self.directory / "output/panel.svg")
            rows = [f"{identity},{float(x)},{float(y)},{condition}" for identity, (x, y), condition in zip(("001", "NA", "null"), points.get_offsets(), ("Control", "Treatment", "Control"))]
            self.write("output/points.csv", "id,artist_x,artist_y,condition\n" + "\n".join(rows) + "\n")
            self.plan["layers"][0]["verification"][0]["target_sha256"] = self.hash("output/points.csv")
            self.rehash_svg()
            result = self.run_audit()
            self.assertEqual(result["status"], "passed-recorded-checks", result)
            self.assertTrue(any(item["kind"] == "svg-shared-axis-alignment" for item in result["checks"]))
        finally:
            plt.close(fig)

    def test_required_layer_cannot_be_silently_dropped_or_omitted(self):
        self.plan["layers"].pop()
        result = self.run_audit()
        self.assertIn("layer-coverage", self.codes(result))
        self.assertIn("binding-coverage", self.codes(result))
        self.plan["layers"] = [self.plan["layers"][0]]
        self.plan["layers"][0]["status"] = "omitted"
        self.plan["layers"][0]["adoption"]["decision"] = "omit"
        result = self.run_audit()
        self.assertIn("unresolved-layer", self.codes(result, "missing_evidence"))

    def test_missing_evidence_and_actual_numeric_mismatch_are_distinguished(self):
        self.plan["layers"][0]["verification"] = []
        result = self.run_audit()
        self.assertEqual(result["status"], "incomplete")
        self.assertIn("missing-layer-verification", self.codes(result, "missing_evidence"))
        self.plan["layers"][0]["verification"] = [{"kind": "numeric", "source_artifact": "data-1", "source_keys": ["id"], "source_fields": ["value"], "target": "output/points.csv", "target_sha256": self.hash("output/points.csv"), "target_keys": ["id"], "target_fields": ["artist_x"], "atol": 1e-12}]
        result = self.run_audit()
        self.assertEqual(result["status"], "failed")
        self.assertIn("numeric-mismatch", self.codes(result))

    def test_changed_source_script_svg_or_verification_table_cannot_pass(self):
        targets = ["data/data-1-observations.csv", "implementation/panel.py", "output/panel.svg", "output/points.csv"]
        for name in targets:
            path = self.directory / name
            original = path.read_bytes()
            path.write_bytes(original + b"\n")
            result = self.run_audit()
            self.assertEqual(result["status"], "failed", name)
            self.assertIn("hash-mismatch", self.codes(result))
            path.write_bytes(original)

    def test_lost_extra_duplicate_or_normalized_record_keys_are_rejected(self):
        original = (self.directory / "output/points.csv").read_text()
        variants = [original.replace("NA,2,3,Treatment\n", ""), original + "extra,1,2,Control\n", original + "001,0,1,Control\n", original.replace("001,", "1,")]
        for content in variants:
            self.write("output/points.csv", content)
            self.plan["layers"][0]["verification"][0]["target_sha256"] = self.hash("output/points.csv")
            result = self.run_audit()
            self.assertEqual(result["status"], "failed")
            self.assertTrue(self.codes(result) & {"record-set-mismatch", "invalid-verification"})

    def test_literal_and_interval_checks_preserve_categories_and_reject_bad_bounds(self):
        self.plan["layers"][0]["verification"].append({"kind": "records", "source_artifact": "data-1", "source_keys": ["id"], "source_fields": ["condition"], "target": "output/points.csv", "target_sha256": self.hash("output/points.csv"), "target_keys": ["id"], "target_fields": ["condition"]})
        self.write("output/bounds.csv", "id,low,center,high\n001,0,1,2\nNA,2,3,4\nnull,1,2,3\n")
        self.plan["layers"][0]["verification"].append({"kind": "bounds", "target": "output/bounds.csv", "target_sha256": self.hash("output/bounds.csv"), "target_keys": ["id"], "target_fields": ["low", "center", "high"]})
        self.assertEqual(self.run_audit()["status"], "passed-recorded-checks")
        self.write("output/bounds.csv", "id,low,center,high\n001,2,1,3\n")
        self.plan["layers"][0]["verification"][-1]["target_sha256"] = self.hash("output/bounds.csv")
        self.assertIn("interval-order", self.codes(self.run_audit()))
        self.write("output/bounds.csv", "id,low,center,high\n001,0,NaN,3\n")
        self.plan["layers"][0]["verification"][-1]["target_sha256"] = self.hash("output/bounds.csv")
        self.assertIn("invalid-verification", self.codes(self.run_audit()))

    def test_axis_domain_units_and_actual_exported_alignment_are_checked(self):
        self.plan["audit"]["axes"][1]["unit"] = "min"
        self.assertIn("shared-axis-mapping", self.codes(self.run_audit()))
        self.plan["audit"]["axes"][1]["unit"] = "h"
        self.svg(left=21)
        self.rehash_svg()
        self.assertIn("shared-axis-alignment", self.codes(self.run_audit()))
        self.svg(width=69)
        self.rehash_svg()
        self.assertIn("shared-axis-alignment", self.codes(self.run_audit()))
        self.svg(physical_width=121)
        self.rehash_svg()
        self.assertIn("canvas-mismatch", self.codes(self.run_audit()))

    def test_transformed_svg_geometry_is_missing_evidence_instead_of_guessed(self):
        self.svg(transform='transform="translate(1 0)"')
        self.rehash_svg()
        result = self.run_audit()
        self.assertEqual(result["status"], "incomplete")
        self.assertIn("unsupported-axis-geometry", self.codes(result, "missing_evidence"))
        self.assertFalse(any(item["kind"] == "svg-shared-axis-alignment" for item in result["checks"]))

    def test_nested_viewports_descendant_transforms_and_letterboxing_are_not_false_alignment_passes(self):
        path = self.directory / "output/panel.svg"
        original = path.read_text()
        variants = [
            original.replace('<g id="lower-box" >', '<svg x="25" y="0" width="120" height="90" viewBox="0 0 120 90"><g id="lower-box" >').replace('<g id="point-artists"', '</svg><g id="point-artists"'),
            original.replace('<rect x="20"', '<g transform="translate(10 0)"><rect x="20"').replace('height="12"/></g>', 'height="12"/></g></g>'),
            original.replace('viewBox="0 0 120 90"', 'viewBox="0 0 120 120"'),
            original.replace('<rect x="20"', '<g style="transform: translate(10px, 0)"><rect x="20"').replace('height="12"/></g>', 'height="12"/></g></g>'),
            original.replace('<g id="upper-box">', '<style>#lower-box {transform: translate(10px, 0)}</style><g id="upper-box">'),
        ]
        for text in variants:
            path.write_text(text)
            self.rehash_svg()
            result = self.run_audit()
            self.assertEqual(result["status"], "incomplete", result)
            self.assertIn("unsupported-axis-geometry", self.codes(result, "missing_evidence"))
            self.assertFalse(any(item["kind"] == "svg-shared-axis-alignment" for item in result["checks"]))

    def test_declared_join_does_not_allow_orphan_keys_or_unrecorded_multiplication(self):
        staged = self.directory / "data/data-2-metadata.csv"
        staged.write_text("id,score\n001,0.4\nNA,0.8\n", encoding="utf-8")
        manifest_path = self.directory / "packet.json"
        manifest = json.loads(manifest_path.read_text())
        for artifact in manifest["artifacts"]:
            if artifact["id"] == "data-2":
                artifact["sha256"] = self.hash(artifact["path"])
        manifest_path.write_text(json.dumps(manifest))
        result = self.run_audit()
        self.assertIn("join-coverage", self.codes(result))
        staged.write_text("id,score\n001,0.4\n001,0.5\nNA,0.8\nnull,0.6\n", encoding="utf-8")
        for artifact in manifest["artifacts"]:
            if artifact["id"] == "data-2":
                artifact["sha256"] = self.hash(artifact["path"])
        manifest_path.write_text(json.dumps(manifest))
        self.assertIn("join-cardinality", self.codes(self.run_audit()))

    def test_missing_artists_invalid_area_and_log_domains_fail(self):
        self.plan["audit"]["bindings"][0]["svg_ids"] = ["invented-point"]
        self.assertIn("missing-svg-artist", self.codes(self.run_audit()))
        self.plan["audit"]["guides"][0].update(kind="area", mapping={"domain": [0, 1], "area_pt2": [0, 100], "unit": "fraction", "relation": "linear-radius"})
        with self.assertRaisesRegex(checker.PacketError, "linear-area"):
            self.run_audit()
        self.plan["audit"]["guides"][0]["mapping"]["relation"] = "linear-area"
        self.plan["audit"]["axes"][0]["scale"] = "log"
        with self.assertRaisesRegex(checker.PacketError, "positive"):
            self.run_audit()

    def test_nonnumeric_layer_can_bind_presence_without_fake_numeric_data(self):
        reading_path = self.directory / "reference-reading.json"
        reading = json.loads(reading_path.read_text())
        reading["layers"][0]["required_data_meanings"] = []
        reading["layers"][0]["description"] = "Nonnumeric annotation"
        reading_path.write_text(json.dumps(reading))
        manifest_path = self.directory / "packet.json"
        manifest = json.loads(manifest_path.read_text())
        for artifact in manifest["artifacts"]:
            if artifact["id"] == "reading":
                artifact.update(sha256=self.hash(artifact["path"]), bytes=reading_path.stat().st_size)
        manifest_path.write_text(json.dumps(manifest))
        layer = self.plan["layers"][0]
        layer.update(data_artifacts=[], field_mapping={}, verification=[{"kind": "svg-presence", "svg_ids": ["point-artists"]}])
        result = self.run_audit()
        self.assertEqual(result["status"], "passed-recorded-checks")
        self.assertTrue(any(item["kind"] == "svg-presence" for item in result["checks"]))
        layer["verification"][0]["svg_ids"] = ["legend"]
        self.assertIn("missing-svg-verification", self.codes(self.run_audit()))

    def test_presence_cannot_replace_a_data_layer_mapping(self):
        self.plan["layers"][0].update(data_artifacts=[], field_mapping={}, verification=[{"kind": "svg-presence", "svg_ids": ["point-artists"]}])
        self.assertIn("missing-layer-data", self.codes(self.run_audit(), "missing_evidence"))
        self.plan["layers"][0].update(data_artifacts=["data-1"], field_mapping={"x": {"artifact": "data-1", "field": "time", "unit": "h"}})
        self.assertIn("missing-source-verification", self.codes(self.run_audit(), "missing_evidence"))

    def test_invalid_negative_svg_rectangle_cannot_pass_alignment(self):
        self.svg(left=90, width=-70)
        self.rehash_svg()
        self.assertIn("unsupported-axis-geometry", self.codes(self.run_audit(), "missing_evidence"))

    def test_header_only_tables_are_incomplete_not_numeric_or_join_evidence(self):
        manifest_path = self.directory / "packet.json"
        manifest = json.loads(manifest_path.read_text())
        for artifact in manifest["artifacts"]:
            if artifact["id"].startswith("data-"):
                path = self.directory / artifact["path"]
                path.write_text(path.read_text().splitlines()[0] + "\n")
                artifact.update(sha256=self.hash(artifact["path"]), bytes=path.stat().st_size)
        manifest_path.write_text(json.dumps(manifest))
        for layer in self.plan["layers"]:
            check = layer["verification"][0]
            path = self.directory / check["target"]
            path.write_text(path.read_text().splitlines()[0] + "\n")
            check["target_sha256"] = self.hash(check["target"])
        result = self.run_audit()
        self.assertEqual(result["status"], "incomplete")
        self.assertIn("empty-record-evidence", self.codes(result, "missing_evidence"))
        self.assertIn("empty-join-evidence", self.codes(result, "missing_evidence"))

    def test_axis_field_units_are_checked_without_inventing_unmapped_roles(self):
        self.plan["layers"][0]["field_mapping"]["x"] = {"artifact": "data-1", "field": "time", "unit": "min"}
        self.assertIn("axis-field-unit", self.codes(self.run_audit()))
        self.plan["layers"][0]["field_mapping"]["x"]["unit"] = "h"
        self.assertEqual(self.run_audit()["status"], "passed-recorded-checks")

    def test_numeric_string_comparison_does_not_conflate_large_integers(self):
        audit = checker.Audit(self.directory)
        first = audit.numeric("9007199254740992", "first")
        second = audit.numeric("9007199254740993", "second")
        self.assertFalse(audit.within_tolerance(first, second, 0))
        self.assertTrue(audit.within_tolerance(first, second, 1))
        self.assertFalse(audit.within_tolerance(audit.numeric("1.000000000000000000000000000001", "first"), audit.numeric("1", "second"), 0))
        self.assertTrue(audit.within_tolerance(audit.numeric("2.50e-300", "first"), audit.numeric("2.5e-300", "second"), 0))
        with self.assertRaisesRegex(checker.PacketError, "precision span"):
            audit.within_tolerance(audit.numeric("1e100000", "first"), audit.numeric("0", "second"), 0)

    def test_paths_symlinks_nonfinite_and_bool_versions_are_rejected(self):
        self.plan["audit"]["script"]["path"] = "../outside.py"
        with self.assertRaisesRegex(checker.PacketError, "escapes"):
            self.run_audit()
        self.plan["audit"]["script"] = self.binding("implementation/panel.py")
        self.plan["version"] = True
        with self.assertRaisesRegex(checker.PacketError, "version 1"):
            self.run_audit()
        self.plan["version"] = 1
        path = self.directory / "output/panel.png"
        path.unlink()
        path.symlink_to(self.reference)
        with self.assertRaisesRegex(checker.PacketError, "Symlink"):
            self.run_audit()

    def test_cli_is_stdlib_only_preserves_existing_output_and_reports_limits(self):
        self.run_audit()
        output = self.root / "audit.json"
        command = [sys.executable, "-S", str(SCRIPTS / "audit_reproduction.py"), "--packet", str(self.directory), "--out", str(output)]
        first = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        evidence = json.loads(output.read_text())
        self.assertEqual(evidence["status"], "passed-recorded-checks")
        original = output.read_bytes()
        second = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(second.returncode, 2)
        self.assertEqual(output.read_bytes(), original)
        self.plan["layers"][0]["verification"] = []
        self.run_audit()
        incomplete = subprocess.run(command[:-2], capture_output=True, text=True)
        self.assertEqual(incomplete.returncode, 1, incomplete.stderr)
        self.assertEqual(json.loads(incomplete.stdout)["status"], "incomplete")

    def test_malformed_nested_objects_keys_and_huge_numbers_do_not_crash_cli(self):
        original = copy.deepcopy(self.plan)
        variants = []
        for change in (lambda value: value.update(implementation=None), lambda value: value.update(layout=None),
                       lambda value: value["layout"].update(width_mm=10 ** 1000),
                       lambda value: value["layers"][0]["verification"][0].update(target_keys=[{}]),
                       lambda value: value["layers"][0]["verification"][0].update(source_artifact=[]),
                       lambda value: value["layers"][0]["verification"][0].update(target_fields=[{}]),
                       lambda value: value["layers"][0]["verification"][0].update(kind=[]),
                       lambda value: value["layers"][0]["adoption"].update(priority=[]),
                       lambda value: value["layers"][0].update(status=[]),
                       lambda value: value["audit"]["axes"][0].update(dimension=[]),
                       lambda value: value["audit"]["axes"][0].update(plot_box_svg_id=[]),
                       lambda value: value["audit"]["joins"][0]["left"].update(artifact=[])):
            modified = copy.deepcopy(original)
            change(modified)
            variants.append(modified)
        command = [sys.executable, "-S", str(SCRIPTS / "audit_reproduction.py"), "--packet", str(self.directory)]
        for plan in variants:
            self.plan = plan
            self.plan_path.write_text(json.dumps(plan))
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertIn(result.returncode, (1, 2))
            self.assertNotIn("Traceback", result.stderr, result.stderr)


if __name__ == "__main__":
    unittest.main()
