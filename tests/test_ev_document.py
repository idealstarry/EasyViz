"""Portable editable documents preserve real identities and never execute inputs."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid
import warnings
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"
sys.path.insert(0, str(SCRIPTS))
import ev_document
from ev_document import EVDocumentError, export_document, import_document, inspect_document
from figure_workbench import FigureWorkbench, write_figure_info
from figure_handoff import capture_inputs, write_receipt

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="120mm" height="60mm" viewBox="0 0 240 120"><g id="real-data"><circle cx="70" cy="80" r="3" fill="#0072B2"/></g><text x="20" y="25">Condition</text></svg>'


class EVDocumentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-ev-test-")
        self.root = Path(self.temp.name).resolve()
        self.attempt = self.root / "source-attempt"
        self.attempt.mkdir()
        self.destination = self.root / "destination"
        self.destination.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def custom(self, *, mapped=True, helper=True):
        for name in ev_document.EXPORTS | {"elements.json", "handoff.json"}:
            (self.attempt / name).unlink(missing_ok=True)
        spec = {"chart": "custom", "layout": {"width_mm": 120, "height_mm": 60}, "formats": ["svg"]}
        source = self.attempt / "plot.py"
        source.write_text('raise RuntimeError("PACKAGE CODE MUST NOT EXECUTE")\n')
        data = self.attempt / "source.csv"
        data.write_bytes(b"id,x,y\n001,1,2\n")
        specification = self.attempt / "spec.json"
        specification.write_text(json.dumps(spec))
        auxiliaries = {}
        if helper:
            helper_path = self.attempt / "custom_helper.py"
            helper_path.write_text('raise RuntimeError("HELPER MUST NOT EXECUTE")\n')
            auxiliaries["helper:custom_helper.py"] = helper_path
            metadata = self.attempt / "metadata.csv"
            metadata.write_text("id,group\n001,A\n")
            auxiliaries["row_metadata"] = metadata
        capture = capture_inputs(self.attempt, data_file=data, source_script=source, spec_file=specification,
                                 auxiliary_inputs=auxiliaries or None)
        (self.attempt / "panel.svg").write_bytes(SVG)
        (self.attempt / "settings.json").write_text(json.dumps({"track": "create", "layout": spec["layout"]}))
        (self.attempt / "qa.json").write_text(json.dumps({"status": "pass", "valid_outputs": True,
                    "exports": {"svg": {"sha256": hashlib.sha256(SVG).hexdigest()}}}))
        receipt = write_receipt(self.attempt, capture=capture, formats=["svg"], track="create")
        if mapped:
            (self.attempt / "elements.json").write_text(json.dumps({"schema_version": 1, "version": receipt["version"],
                "input": receipt["input"], "panel": receipt["panel"], "elements": [{"id": "real-data", "role": "point-group",
                    "label": "Condition", "source_keys": [{"source_row": 1, "id": "001"}], "spec_paths": [], "editable": []}]}))
        (self.attempt / "caption.md").write_text("One independent specimen; values unchanged.\n")
        return receipt

    def archive(self, path):
        with zipfile.ZipFile(path) as archive:
            return {name: archive.read(name) for name in archive.namelist()}

    def rewritten(self, contents, *, name="changed.ev", bind=False):
        contents = copy.deepcopy(contents)
        if bind:
            manifest = json.loads(contents["document.json"])
            manifest["members"] = {key: ev_document.sha256(raw) for key, raw in contents.items() if key != "document.json"}
            manifest["id"] = "ev-" + ev_document.sha256(ev_document._encode({"version": manifest["version"], "members": manifest["members"]}))[:24]
            contents["document.json"] = ev_document._encode(manifest)
        path = self.root / name
        with zipfile.ZipFile(path, "w") as archive:
            for member, raw in contents.items():
                archive.writestr(member, raw)
        return path

    def test_svg_only_custom_document_is_selectable_after_original_sources_disappear(self):
        receipt = self.custom()
        (self.attempt / "unrelated-secret.csv").write_text("This whole experimental folder must not be packed.\n")
        document = export_document(self.attempt)
        self.assertEqual(document.name, "panel.ev")
        metadata = inspect_document(document)
        self.assertEqual(metadata["formats"], ["svg"])
        self.assertEqual(metadata["renderer"]["kind"], "custom")
        members = self.archive(document)
        self.assertNotIn("unrelated-secret.csv", members)
        for record_name in ("elements.json", "handoff.json"):
            record = json.loads(members[record_name])
            self.assertTrue(all(not Path(record["input"][field]).is_absolute() for field in ev_document.PRIMARY))
        with patch("subprocess.Popen", side_effect=AssertionError("Import must not execute a renderer")):
            opened = import_document(document, self.destination)
        shutil.rmtree(self.attempt)
        state = FigureWorkbench(opened).state()
        self.assertTrue(state["source_current"])
        self.assertTrue(state["manifest_valid"])
        self.assertEqual(state["version"], receipt["version"])
        self.assertEqual(state["elements"][0]["id"], "real-data")
        self.assertEqual((opened / "panel.svg").read_bytes(), SVG)
        self.assertEqual((opened / "caption.md").read_text(), "One independent specimen; values unchanged.\n")
        self.assertEqual(Path(state["input"]["data_file"]).read_bytes(), b"id,x,y\n001,1,2\n")
        script_parent = Path(state["input"]["source_script"]).parent
        helper_path = Path(state["input"]["auxiliary_inputs"]["helper:custom_helper.py"]["path"])
        self.assertEqual(helper_path.parent, script_parent)

    def test_no_auxiliary_inputs_and_literal_path_labels_are_preserved(self):
        self.custom(helper=False)
        settings = json.loads((self.attempt / "settings.json").read_text())
        settings["labels"] = {"x": str(self.attempt / "source.csv")}
        (self.attempt / "settings.json").write_text(json.dumps(settings))
        opened = import_document(export_document(self.attempt), self.destination)
        self.assertEqual(json.loads((opened / "settings.json").read_text())["labels"], settings["labels"])
        self.assertTrue(FigureWorkbench(opened).state()["source_current"])

    def test_custom_display_name_survives_archive_import_and_reexport_without_scientific_changes(self):
        self.custom()
        before = FigureWorkbench(self.attempt).state()
        original_data = (self.attempt / "source.csv").read_bytes()
        name = "Study 2 · macrophage shifts"
        info = write_figure_info(self.attempt, name)
        document = export_document(self.attempt)
        manifest = inspect_document(document)
        self.assertEqual(manifest["name"], name)
        self.assertEqual(manifest["version"], before["version"])
        self.assertEqual(json.loads(self.archive(document)["figure-info.json"]), info)
        opened = import_document(document, self.destination)
        state = FigureWorkbench(opened).state()
        self.assertEqual(state["figure_name"], name)
        self.assertEqual(state["version"], before["version"])
        self.assertEqual((opened / "panel.svg").read_bytes(), SVG)
        self.assertEqual(Path(state["input"]["data_file"]).read_bytes(), original_data)
        self.assertEqual(inspect_document(export_document(opened))["name"], name)

    def test_legacy_document_manifest_name_becomes_portable_metadata(self):
        self.custom()
        files = self.archive(export_document(self.attempt))
        files.pop("figure-info.json")
        manifest = json.loads(files["document.json"])
        manifest["name"] = "Legacy panel with a useful name"
        files["document.json"] = ev_document._encode(manifest)
        document = self.rewritten(files, name="legacy.ev", bind=True)
        opened = import_document(document, self.destination)
        self.assertEqual(FigureWorkbench(opened).state()["figure_name"], manifest["name"])
        self.assertEqual(json.loads((opened / "figure-info.json").read_text())["display_name"], manifest["name"])
        self.assertEqual(inspect_document(export_document(opened))["name"], manifest["name"])

    def test_invalid_or_conflicting_archive_display_names_are_rejected(self):
        self.custom()
        original = self.archive(export_document(self.attempt))
        for index, name in enumerate((None, "", "   ", "x" * 121, "Invisible\x00name", "Hidden\u202ename", "Different name")):
            with self.subTest(name=name):
                files = copy.deepcopy(original)
                manifest = json.loads(files["document.json"])
                manifest["name"] = name
                files["document.json"] = ev_document._encode(manifest)
                with self.assertRaises(EVDocumentError):
                    import_document(self.rewritten(files, name=f"bad-label-{index}.ev"), self.destination)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_figure_display_metadata_has_a_small_bound(self):
        self.custom()
        files = self.archive(export_document(self.attempt))
        files["figure-info.json"] += b" " * ev_document.MAX_FIGURE_INFO_BYTES
        with self.assertRaisesRegex(EVDocumentError, "bounded"):
            inspect_document(self.rewritten(files, name="large-label.ev", bind=True))
        (self.attempt / "figure-info.json").write_bytes(files["figure-info.json"])
        with self.assertRaises(EVDocumentError):
            export_document(self.attempt)

    def test_each_import_creates_a_new_attempt_and_existing_collision_is_never_deleted(self):
        self.custom()
        document = export_document(self.attempt)
        first, second = import_document(document, self.destination), import_document(document, self.destination)
        self.assertNotEqual(first, second)
        identifier = uuid.UUID(int=1)
        existing = self.destination / ("ev-import-" + identifier.hex)
        existing.mkdir()
        (existing / "keep.txt").write_text("preserve")
        with patch.object(ev_document.uuid, "uuid4", return_value=identifier):
            with self.assertRaises(EVDocumentError):
                import_document(document, self.destination)
        self.assertEqual((existing / "keep.txt").read_text(), "preserve")

    def test_missing_map_stale_data_and_fabricated_ids_require_reexport(self):
        self.custom(mapped=False)
        with self.assertRaisesRegex(EVDocumentError, "element map"):
            export_document(self.attempt)
        self.custom()
        (self.attempt / "source.csv").write_text("id,x,y\n001,99,2\n")
        with self.assertRaisesRegex(EVDocumentError, "stale"):
            export_document(self.attempt)
        self.custom()
        record = json.loads((self.attempt / "elements.json").read_text())
        record["elements"][0]["id"] = "invented-point"
        (self.attempt / "elements.json").write_text(json.dumps(record))
        with self.assertRaisesRegex(EVDocumentError, "element map"):
            export_document(self.attempt)
        self.assertFalse((self.attempt / "panel.ev").exists())

    def test_corruption_and_rebound_stale_svg_are_rejected_before_any_project_write(self):
        self.custom()
        original = self.archive(export_document(self.attempt))
        for rebind in (False, True):
            files = copy.deepcopy(original)
            files["panel.svg"] = SVG.replace(b'cy="80"', b'cy="70"')
            path = self.rewritten(files, name=f"corrupt-{rebind}.ev", bind=rebind)
            with self.assertRaises(EVDocumentError):
                import_document(path, self.destination)
            self.assertEqual(list(self.destination.iterdir()), [])

    def test_traversal_unknown_members_symlinks_duplicates_and_plain_renamed_svg_fail(self):
        self.custom()
        original = self.archive(export_document(self.attempt))
        for bad_name in ("../escaped.py", "/absolute.py", "inputs\\escaped.py", "unexpected.py"):
            files = {**original, bad_name: b"bad"}
            path = self.rewritten(files, name="bad-name.ev", bind=True)
            with self.assertRaises(EVDocumentError):
                import_document(path, self.destination)
        symlink = self.root / "symlink.ev"
        with zipfile.ZipFile(symlink, "w") as archive:
            for name, raw in original.items():
                if name == "panel.svg":
                    entry = zipfile.ZipInfo(name)
                    entry.create_system = 3
                    entry.external_attr = (stat.S_IFLNK | 0o777) << 16
                    archive.writestr(entry, raw)
                else:
                    archive.writestr(name, raw)
        with self.assertRaises(EVDocumentError):
            import_document(symlink, self.destination)
        duplicate = self.root / "duplicate.ev"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(duplicate, "w") as archive:
                for name, raw in original.items():
                    archive.writestr(name, raw)
                archive.writestr("panel.svg", SVG)
        with self.assertRaises(EVDocumentError):
            import_document(duplicate, self.destination)
        plain = self.root / "renamed.ev"
        plain.write_bytes(SVG)
        with self.assertRaises(EVDocumentError):
            import_document(plain, self.destination)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_size_limits_duplicate_json_and_symlink_output_fail(self):
        self.custom()
        document = export_document(self.attempt)
        with patch.object(ev_document, "MAX_DOCUMENT_BYTES", 100):
            with self.assertRaisesRegex(EVDocumentError, "bounded"):
                inspect_document(document)
        files = self.archive(document)
        files["document.json"] = b'{"kind":"one","kind":"two"}'
        with self.assertRaisesRegex(EVDocumentError, "duplicate"):
            inspect_document(self.rewritten(files))
        files["document.json"] = b'{"overflow":1e999}'
        with self.assertRaisesRegex(EVDocumentError, "finite"):
            inspect_document(self.rewritten(files, name="overflow.ev"))
        other = self.root / "other.txt"
        other.write_text("preserve")
        symlink = self.root / "linked.ev"
        symlink.symlink_to(other)
        with self.assertRaises(EVDocumentError):
            export_document(self.attempt, symlink)
        self.assertEqual(other.read_text(), "preserve")


class EVCoreDocumentTests(unittest.TestCase):
    """Real renders check runtime portability and frozen scientific results."""

    setUp = EVDocumentTests.setUp
    tearDown = EVDocumentTests.tearDown

    def core(self, *, formats=None):
        import render
        data = self.root / "core-data.csv"
        data.write_text("x,y,group\n1,2,A\n2,3,A\n3,4,A\n1,4,B\n2,5,B\n3,6,B\n")
        spec = {"chart": "scatter", "fields": {"x": "x", "y": "y", "group": "group"},
                "labels": {"x": "X", "y": "Y"}, "formats": formats or ["svg", "pdf", "png"],
                "layout": {"width_mm": 120, "height_mm": 90, "font": "DejaVu Sans", "font_size_pt": 8, "dpi": 100},
                "options": {"point_area_pt2": 12}, "seed": 41}
        spec_path = self.root / "core-spec.json"
        spec_path.write_text(json.dumps(spec))
        render.render(data, spec, self.attempt, spec_path=spec_path, track="create")
        return data, spec_path

    def test_core_cosmetic_rerender_uses_trusted_runtime_after_source_relocation(self):
        from apply_figure_requests import prepare_requests
        data, spec_path = self.core()
        document = export_document(self.attempt)
        opened = import_document(document, self.destination)
        data.unlink()
        spec_path.unlink()
        state = FigureWorkbench(opened).state()
        self.assertEqual(Path(state["input"]["source_script"]).resolve(), SCRIPTS / "render.py")
        app = FigureWorkbench(opened)
        item = app.change({"version": state["version"], "selector": {"category": "A"}, "property": "color",
                           "value": "#22B6AA", "instruction": "Use jade for A and retain all observed values."})["request"]
        fresh = self.destination / "fresh-core"
        plan = prepare_requests(opened, fresh, [item["id"]], render=True)
        self.assertTrue(plan["rendered"])
        self.assertEqual(json.loads((fresh / "settings.json").read_text())["resolved_colors"]["A"].upper(), "#22B6AA")
        self.assertEqual(Path(state["input"]["data_file"]).read_bytes(), (fresh / "source-data.csv").read_bytes())

    def test_pending_requests_relocate_only_their_exact_current_source_and_submit(self):
        from apply_figure_requests import prepare_requests
        self.core()
        original = FigureWorkbench(self.attempt)
        state = original.state()
        first = original.change({"version": state["version"], "selector": {"category": "A"}, "property": "color",
                                 "value": "#22B6AA", "instruction": "Use jade for A."})["request"]
        ledger = original.ledger()
        historical = copy.deepcopy(first)
        historical.update(id="historical-request", version={"figure_sha256": "0" * 64})
        ledger["requests"].append(historical)
        original.write_ledger(ledger)
        opened = import_document(export_document(self.attempt), self.destination)
        app = FigureWorkbench(opened)
        items = {item["id"]: item for item in app.ledger()["requests"]}
        self.assertEqual(items[first["id"]]["input"], app.state()["input"])
        self.assertEqual(items[first["id"]]["instruction"], first["instruction"])
        self.assertEqual(items[first["id"]]["element_ids"], first["element_ids"])
        self.assertEqual(items["historical-request"], historical)
        second = app.change({"version": app.state()["version"], "selector": {"category": "B"}, "property": "color",
                             "value": "#D06288", "instruction": "Use pink for B."})["request"]
        prepared = prepare_requests(opened, self.destination / "pending-render", [first["id"], second["id"]], render=True)
        self.assertTrue(prepared["rendered"])
        statuses = {item["id"]: item["status"] for item in app.ledger()["requests"]}
        self.assertEqual(statuses[first["id"]], "applied")
        self.assertEqual(statuses[second["id"]], "applied")
        self.assertEqual(statuses["historical-request"], "pending")

    def test_svg_only_core_remains_a_source_bound_selectable_document(self):
        self.core(formats=["svg"])
        opened = import_document(export_document(self.attempt), self.destination)
        state = FigureWorkbench(opened).state()
        self.assertTrue(state["manifest_valid"])
        self.assertTrue(state["source_current"])
        self.assertFalse((opened / "panel.pdf").exists())
        self.assertFalse((opened / "panel.png").exists())

    def test_core_document_cannot_omit_a_runtime_binding_to_gain_automatic_execution(self):
        self.core(formats=["svg"])
        with zipfile.ZipFile(export_document(self.attempt)) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        manifest = json.loads(files["document.json"])
        manifest["renderer"]["runtime"].pop("legend_layout.py")
        files["document.json"] = ev_document._encode(manifest)
        damaged = self.root / "incomplete-runtime.ev"
        with zipfile.ZipFile(damaged, "w") as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        with self.assertRaisesRegex(EVDocumentError, "runtime closure"):
            import_document(damaged, self.destination)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_adopted_analysis_bytes_and_inference_survive_import_and_fresh_render(self):
        import analyze
        import render
        source = self.root / "analysis-source.csv"
        source.write_text("id,group,value,value2\na1,A,1,1\na2,A,2,2\na3,A,3,4\nb1,B,4,1\nb2,B,5,2\nb3,B,6,3\n")
        plan = {"schema_version": 1, "question": "Compare two prespecified independent specimen endpoints",
                "design": {"unit": "id", "unit_definition": "one independently sampled specimen", "structure": "independent", "confirmed": True},
                "missing_policy": "error", "comparisons": [
                    {"name": "primary", "method": "welch", "fields": {"group": "group", "value": "value"}, "groups": ["A", "B"]},
                    {"name": "secondary", "method": "welch", "fields": {"group": "group", "value": "value2"}, "groups": ["A", "B"]}],
                "multiplicity": {"family": "Two endpoints", "adjustment": "holm", "comparisons": ["primary", "secondary"]}}
        report_dir = self.root / "analysis"
        analyze.analyze(source, plan, report_dir)
        result = report_dir / "results.json"
        spec = {"chart": "distribution", "fields": {"group": "group", "value": "value", "unit": "id"},
                "layout": {"width_mm": 100, "height_mm": 80, "font": "DejaVu Sans", "dpi": 100},
                "formats": ["svg"], "labels": {"x": "Condition", "y": "Response (a.u.)"}, "options": {"kind": "box"},
                "statistics": {"analysis": {"schema_version": 1, "results_file": str(result),
                    "results_sha256": hashlib.sha256(result.read_bytes()).hexdigest(), "comparison": "primary", "pvalue": "adjusted", "population": "included"}, "annotate": True}}
        spec_path = self.root / "analysis-spec.json"
        spec_path.write_text(json.dumps(spec))
        render.render(source, spec, self.attempt, spec_path=spec_path, track="create")
        before = json.loads((self.attempt / "stats.json").read_text())
        opened = import_document(export_document(self.attempt), self.destination)
        self.assertEqual((opened / "inputs/plot-spec.json").read_bytes(), spec_path.read_bytes())
        self.assertEqual(json.loads((opened / "stats.json").read_text()), before)
        shutil.rmtree(report_dir)
        source.unlink()
        spec_path.unlink()
        derived_path = opened / "rerender-spec.json"
        derived = json.loads(derived_path.read_text())
        data = Path(FigureWorkbench(opened).state()["input"]["data_file"])
        with patch("scipy.stats.ttest_ind", side_effect=AssertionError("Adopted tests must not be recomputed")):
            render.render(data, derived, self.destination / "fresh-analysis", spec_path=derived_path, track="create")
        after = json.loads((self.destination / "fresh-analysis/stats.json").read_text())
        after["adoption"]["results_file"] = before["adoption"]["results_file"]
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
