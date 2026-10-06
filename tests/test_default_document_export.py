"""SVG defaults and editable documents must describe the current render."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"
sys.path.insert(0, str(SCRIPTS))
import render
from ev_document import inspect_document
from figure_workbench import FigureWorkbench


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

    def test_omitted_formats_and_in_memory_spec_produce_current_svg_document(self):
        qa = render.render(self.data, self.spec, self.out, track="create")
        self.assertEqual(qa["status"], "pass")
        self.assertEqual(set(qa["exports"]), {"svg"})
        self.assertFalse((self.out / "panel.pdf").exists())
        self.assertFalse((self.out / "panel.png").exists())
        self.assertEqual(json.loads((self.out / "plot-spec.json").read_text()), self.spec)
        self.assertTrue(FigureWorkbench(self.out).state()["source_current"])
        self.assertTrue(inspect_document(self.out / "panel.ev"))
        self.assertEqual(json.loads((self.out / "document-status.json").read_text())["status"], "ready")

    def test_explicit_optional_exports_still_match_document(self):
        spec = {**self.spec, "formats": ["svg", "png", "pdf"]}
        qa = render.render(self.data, spec, self.out, track="reproduce")
        self.assertEqual(set(qa["exports"]), {"svg", "png", "pdf"})
        self.assertTrue(inspect_document(self.out / "panel.ev"))

    def test_focused_ecdf_preserves_svg_only_default_through_resolution(self):
        import ecdf_plot
        spec = {**self.spec, "chart": "ecdf", "fields": {"group": "group", "value": "y"},
                "labels": {"x": "Response", "y": "Cumulative fraction"},
                "colors": {"A": "#2581B9", "B": "#E47751"}}
        spec.pop("seed")
        ecdf_plot.render(self.data, spec, self.out)
        qa = json.loads((self.out / "qa.json").read_text())
        self.assertEqual(set(qa["exports"]), {"svg"})
        self.assertFalse((self.out / "panel.pdf").exists())
        self.assertFalse((self.out / "panel.png").exists())
        self.assertTrue(inspect_document(self.out / "panel.ev"))

    def test_failed_spec_load_invalidates_previous_editable_document(self):
        spec_path = self.root / "spec.json"
        spec_path.write_text(json.dumps(self.spec))
        render.render_spec_file(self.data, spec_path, self.out, track="create")
        self.assertTrue((self.out / "panel.ev").is_file())
        spec_path.write_text("{invalid")
        with self.assertRaises(render.SpecError):
            render.render_spec_file(self.data, spec_path, self.out, track="create")
        self.assertFalse((self.out / "panel.ev").exists())
        self.assertFalse((self.out / "document-status.json").exists())
        self.assertEqual(json.loads((self.out / "qa.json").read_text())["status"], "failed")

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
