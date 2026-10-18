"""Ordinary graphics stay independent of optional workbench documents."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"
sys.path.insert(0, str(SCRIPTS))
import render


class DefaultDocumentExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-default-document-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.data = self.root / "data.csv"
        self.data.write_text("x,y,group\n1,2,A\n2,3,A\n3,4,A\n1,4,B\n2,5,B\n3,6,B\n")
        self.spec = {"chart": "scatter", "fields": {"x": "x", "y": "y", "group": "group"},
                     "labels": {"x": "Dose", "y": "Response"}, "seed": 41,
                     "layout": {"width_mm": 100, "height_mm": 80, "font": "DejaVu Sans", "font_size_pt": 8}}
        self.out = self.root / "figure"

    def read(self, name):
        return json.loads((self.out / name).read_text())

    def test_omitted_formats_preserve_spec_and_svg_without_packaging_a_document(self):
        qa = render.render(self.data, self.spec, self.out, track="create")
        self.assertEqual(qa["status"], "pass")
        self.assertEqual(set(qa["exports"]), {"svg"})
        for name in ("panel.pdf", "panel.png", "panel.ev", "document-status.json"):
            self.assertFalse((self.out / name).exists(), name)
        self.assertEqual(self.read("plot-spec.json"), self.spec)
        self.assertEqual(qa["editing_availability"]["status"], "available")
        self.assertEqual(self.read("settings.json")["editing_availability"], self.read("editing-status.json"))
        self.assertEqual(self.read("elements.json")["version"]["figure_sha256"], qa["exports"]["svg"]["sha256"])

    def test_ordinary_svg_does_not_import_or_start_optional_workbench_components(self):
        spec_path = self.root / "spec.json"
        spec_path.write_text(json.dumps(self.spec))
        code = """
import builtins, pathlib, sys
original = builtins.__import__
forbidden = {'ev_document', 'figure_workbench', 'figure_service', 'agent_dispatch', 'session_dispatch', 'mcp', 'mcp_server'}
def checked(name, *args, **kwargs):
    if name.split('.')[0] in forbidden:
        raise AssertionError('Ordinary rendering imported optional component: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = checked
sys.path.insert(0, sys.argv[1])
import render
qa = render.render_spec_file(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]), pathlib.Path(sys.argv[4]))
assert qa['status'] == 'pass'
assert not forbidden.intersection(sys.modules)
"""
        result = subprocess.run([sys.executable, "-c", code, str(SCRIPTS), str(self.data), str(spec_path), str(self.out)],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.out / "panel.svg").is_file())
        self.assertFalse((self.out / "panel.ev").exists())

    def test_explicit_document_export_still_works_after_requested_graphics(self):
        from ev_document import inspect_document
        from figure_workbench import FigureWorkbench

        spec = {**self.spec, "formats": ["svg", "png", "pdf"]}
        qa = render.render(self.data, spec, self.out, track="reproduce")
        self.assertEqual(set(qa["exports"]), {"svg", "png", "pdf"})
        self.assertTrue(FigureWorkbench(self.out).state()["source_current"])
        self.assertFalse((self.out / "panel.ev").exists())
        self.assertEqual(render.save_document(self.out), self.out / "panel.ev")
        self.assertTrue(inspect_document(self.out / "panel.ev"))
        self.assertEqual(self.read("document-status.json")["status"], "ready")
        # Every fresh ordinary attempt invalidates the prior optional archive.
        render.render(self.data, spec, self.out)
        self.assertFalse((self.out / "panel.ev").exists())
        self.assertFalse((self.out / "document-status.json").exists())

    def test_mapping_failures_keep_graphics_and_remove_stale_or_partial_maps(self):
        for stage in ("attach_layout", "write"):
            with self.subTest(stage=stage):
                render.render(self.data, self.spec, self.out)
                self.assertIsNotNone(render.save_document(self.out))
                def fail(*args):
                    (self.out / "elements.json").write_text('{"partial":')
                    raise ValueError("synthetic optional mapping failure")
                with patch.object(render.figure_elements, stage, side_effect=fail):
                    qa = render.render(self.data, self.spec, self.out)
                self.assertEqual(qa["status"], "pass")
                self.assertTrue(qa["valid_outputs"])
                self.assertTrue((self.out / "panel.svg").is_file())
                self.assertFalse((self.out / "elements.json").exists())
                self.assertFalse((self.out / "panel.ev").exists())
                status = self.read("editing-status.json")
                self.assertEqual(status["status"], "unavailable")
                self.assertEqual(status["stage"], stage)
                self.assertEqual(status, qa["editing_availability"])
                self.assertEqual(status, self.read("settings.json")["editing_availability"])

    def test_focused_recipes_keep_graphics_when_optional_mapping_fails(self):
        import annotated_matrix
        import ecdf_plot
        import interval_plot
        import paired_plot
        import replicate_plot
        import timecourse_plot
        cases = [
            (ecdf_plot, self.data,
             {**self.spec, "chart": "ecdf", "fields": {"group": "group", "value": "y"},
              "colors": {"A": "#2581B9", "B": "#E47751"},
              "labels": {"x": "Response", "y": "Cumulative fraction"}}),
        ]
        matrix_data = self.root / "matrix.csv"
        matrix_data.write_text("row,column,value\nA,X,1\nA,Y,2\nB,X,3\nB,Y,4\n")
        cases.append((annotated_matrix, matrix_data,
                      {"chart": "annotated_matrix", "fields": {"row": "row", "column": "column", "value": "value"},
                       "order": {"row": ["A", "B"], "column": ["X", "Y"]},
                       "options": {"color_limits": [0, 4]},
                       "layout": {"width_mm": 100, "height_mm": 90, "font": "DejaVu Sans", "font_size_pt": 8},
                       "labels": {"x": "Column", "y": "Row", "color": "Value"}}))
        layout = {"width_mm": 100, "height_mm": 90, "font": "DejaVu Sans", "font_size_pt": 8}
        cases.extend([
            (replicate_plot, self.data,
             {"chart": "replicate", "fields": {"condition": "group", "unit": "x", "value": "y"},
              "layout": layout, "labels": {"y": "Response"}}),
            (paired_plot, self.data,
             {"chart": "paired", "fields": {"condition": "group", "unit": "x", "value": "y"},
              "options": {"point_layout": "jitter", "connect_pairs": True},
              "layout": layout, "labels": {"y": "Response"}}),
        ])
        interval_data = self.root / "interval.csv"
        interval_data.write_text("label,estimate,lower,upper\nA,2,1,3\nB,4,3,6\n")
        cases.append((interval_plot, interval_data,
                      {"chart": "interval", "fields": {name: name for name in ("label", "estimate", "lower", "upper")},
                       "layout": layout, "labels": {"x": "Estimate"}}))
        timecourse_data = self.root / "timecourse.csv"
        timecourse_data.write_text("x,estimate,sd\n1,2,0.2\n2,3,0.3\n3,4,0.2\n")
        cases.append((timecourse_plot, timecourse_data,
                      {"chart": "timecourse", "fields": {name: name for name in ("x", "estimate", "sd")},
                       "uncertainty": {"kind": "sd", "label": "Supplied SD"}, "colors": {"all": "#2581B9"},
                       "layout": layout, "labels": {"x": "Time", "y": "Response"}}))
        for recipe, source, spec in cases:
            spec = deepcopy(spec)
            spec.pop("seed", None)
            with self.subTest(recipe=recipe.__name__):
                with patch.object(recipe.core.figure_elements, "write", side_effect=OSError("map unavailable")):
                    qa = recipe.render(source, spec, self.out)
                self.assertEqual(qa["status"], "pass")
                self.assertEqual(set(qa["exports"]), {"svg"})
                self.assertEqual(qa["editing_availability"]["status"], "unavailable")
                self.assertFalse((self.out / "elements.json").exists())
                self.assertFalse((self.out / "panel.ev").exists())

    def test_direct_custom_export_invalidates_previous_editing_artifacts(self):
        self.out.mkdir()
        for name in ("panel.ev", "document-status.json", "elements.json", "editing-status.json"):
            (self.out / name).write_text("stale")
        data = render.prepare(self.data, self.spec)
        layout, typography, rc = render.setup(self.spec)
        with render.plt.rc_context(rc):
            fig, _ = render.draw(data, self.spec, layout, typography, render.statistics(data, self.spec))
            try:
                with patch.object(render.figure_elements, "write", side_effect=ValueError("map unavailable")):
                    exports = render.export(fig, self.out, self.spec, layout)
            finally:
                render.plt.close(fig)
        self.assertEqual(set(exports), {"svg"})
        for name in ("panel.ev", "document-status.json", "elements.json"):
            self.assertFalse((self.out / name).exists(), name)
        self.assertEqual(self.read("editing-status.json")["status"], "unavailable")

    def test_mapping_fallback_does_not_hide_clipped_text_or_graphic_write_failure(self):
        clipped = deepcopy(self.spec)
        clipped["layout"]["margins"] = {"left": .01, "right": .98, "bottom": .01, "top": .98}
        with patch.object(render.figure_elements, "attach_layout", side_effect=ValueError("map unavailable")):
            with self.assertRaisesRegex(render.SpecError, "Canvas QA"):
                render.render(self.data, clipped, self.out)
        self.assertEqual(self.read("qa.json")["status"], "needs_revision")
        self.assertFalse(self.read("qa.json")["valid_outputs"])
        (self.out / "panel.svg").unlink()
        (self.out / "panel.svg").mkdir()
        with patch.object(render.figure_elements, "attach_layout", side_effect=ValueError("map unavailable")):
            with self.assertRaises(OSError):
                render.render(self.data, self.spec, self.out)
        self.assertEqual(self.read("qa.json")["status"], "failed")
        self.assertFalse(self.read("qa.json")["valid_outputs"])

    def test_failed_spec_load_invalidates_previous_editing_metadata(self):
        spec_path = self.root / "spec.json"
        spec_path.write_text(json.dumps(self.spec))
        render.render_spec_file(self.data, spec_path, self.out, track="create")
        self.assertIsNotNone(render.save_document(self.out))
        spec_path.write_text("{invalid")
        with self.assertRaises(render.SpecError):
            render.render_spec_file(self.data, spec_path, self.out, track="create")
        for name in ("panel.ev", "document-status.json", "elements.json", "editing-status.json"):
            self.assertFalse((self.out / name).exists(), name)
        self.assertEqual(self.read("qa.json")["status"], "failed")

    def test_generated_spec_does_not_overwrite_a_linked_file(self):
        self.out.mkdir()
        outside = self.root / "keep.json"
        outside.write_text("original")
        (self.out / "plot-spec.json").symlink_to(outside)
        with self.assertRaisesRegex(render.SpecError, "symlink"):
            render.render(self.data, self.spec, self.out, track="create")
        self.assertEqual(outside.read_text(), "original")


if __name__ == "__main__":
    unittest.main()
