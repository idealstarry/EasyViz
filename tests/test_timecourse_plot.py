"""Verify supplied bands, actual artists, transfer, and truthful failed-run evidence."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/easyviz/scripts/timecourse_plot.py"
loader = importlib.util.spec_from_file_location("easyviz_timecourse_test", SCRIPT)
recipe = importlib.util.module_from_spec(loader)
loader.loader.exec_module(recipe)


class TimecourseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-timecourse-")
        self.root = Path(self.temp.name)
        self.spec = {"chart": "timecourse", "fields": {"x": "minute", "estimate": "mean", "sd": "sd"},
                     "uncertainty": {"kind": "sd", "label": "Supplied SD"}, "colors": {"all": "#2581B9"},
                     "layout": {"width_mm": 100, "height_mm": 76, "font": "DejaVu Sans", "font_size_pt": 8, "dpi": 100},
                     "formats": ["png"], "labels": {"x": "Time (min)", "y": "Response (a.u.)"}}
        self.source = self.root / "source.csv"
        self.source.write_text("minute,mean,sd,note\n9,4,0.75,last\n1,1,0.2,first\n4,3,0.5,middle\n")

    def tearDown(self):
        recipe.plt.close("all")
        self.temp.cleanup()

    def draw(self, source=None, spec=None):
        source, spec = source or self.source, deepcopy(spec or self.spec)
        data = recipe.prepare(source, spec)
        spec.setdefault("layout", {}).setdefault("auto_fit", True)
        layout, typography, rc = recipe.core.setup(spec)
        rc["path.simplify"] = False
        with recipe.plt.rc_context(rc):
            fig = recipe.draw(data, spec, layout, typography)
            fig.canvas.draw()
        return fig, spec

    def test_actual_mean_and_band_tampering_are_detected(self):
        fig, spec = self.draw()
        self.assertEqual(recipe.audit_source_artists(self.source, spec, fig)["status"], "pass")
        record = fig._easyviz_timecourse_artists[0]
        self.assertEqual(record["line"].get_xydata().tolist(), [[1, 1], [4, 3], [9, 4]])
        self.assertEqual(record["source_rows"], [2, 3, 1])
        record["line"].set_ydata([1, 4, 4])
        record["band"].get_paths()[0].vertices[2, 1] += .1
        codes = {item["code"] for item in recipe.audit_source_artists(self.source, spec, fig)["issues"]}
        self.assertIn("mean_coordinates_changed", codes)
        self.assertIn("band_vertices_changed", codes)

    def test_dual_axis_transforms_use_supplied_summary_scales(self):
        source = self.root / "dual.csv"
        source.write_text("t,kind,m,s\n1,width,1.0,0.1\n2,width,1.1,0.2\n1,length,2.0,0.3\n2,length,3.0,0.4\n")
        spec = deepcopy(self.spec)
        spec.update(fields={"x": "t", "estimate": "m", "sd": "s", "series": "kind"}, colors={"width": "#2581B9", "length": "#D76F3B"})
        spec["options"] = {"axis_by_series": {"width": "left", "length": "right"}, "y_limits": [.8, 1.4], "right_y_limits": [1, 4]}
        spec["labels"] = {"x": "Time", "y": "Width (µm)", "right_y": "Length (µm)"}
        fig, spec = self.draw(source, spec)
        records = fig._easyviz_timecourse_artists
        self.assertEqual(records[1]["side"], "right")
        self.assertEqual(records[1]["line"].get_transform(), fig.axes[1].transData)
        self.assertEqual(recipe.audit_source_artists(source, spec, fig)["status"], "pass")
        records[1]["line"].set_transform(fig.axes[0].transData)
        self.assertIn("axis_assignment_changed", {r["code"] for r in recipe.audit_source_artists(source, spec, fig)["issues"]})

    def test_bad_bands_duplicates_and_clipping_fail_without_dropping(self):
        cases = [
            ("minute,mean,sd\n1,2,-1\n2,3,1\n", {}, "nonnegative"),
            ("minute,mean,sd\n1,2,1\n1,3,1\n", {}, "Duplicate x"),
            ("minute,mean,sd\n1,2,\n2,3,1\n", {}, "Empty"),
            ("minute,mean,sd\n1,2,1\n2,3,1\n", {"y_limits": [1.5, 4]}, "clip"),
            ("minute,mean,sd\n1,1,2\n2,3,1\n", {"y_scale": "log"}, "entire bands"),
            ("minute,mean,sd\n0,2,1\n2,3,1\n", {"x_scale": "log"}, "positive source x"),
            ("minute,mean,sd\n1,1e308,1e308\n2,3,1\n", {}, "remain finite"),
        ]
        for text, options, message in cases:
            with self.subTest(message=message):
                self.source.write_text(text)
                spec = deepcopy(self.spec)
                spec["options"] = options
                with self.assertRaisesRegex(ValueError, message):
                    recipe.prepare(self.source, spec)

    def test_changed_fields_asymmetric_bounds_literal_labels_and_exports(self):
        source = ROOT / "examples/no-author-code/shi-timecourse/transfer/source-data.csv"
        spec = json.loads((source.parent / "spec.json").read_text())
        spec["layout"].update(font="DejaVu Sans", dpi=100)
        spec["formats"] = ["pdf", "svg", "png", "tiff"]
        out = self.root / "transfer"
        qa = recipe.render(source, spec, out)
        self.assertEqual(qa["status"], "pass")
        self.assertEqual(qa["plotted_summary_rows"], 18)
        table = recipe.pd.read_csv(out / "plotting-data.csv", dtype=str, keep_default_na=False)
        self.assertEqual(set(table["formulation"]), {"001", "NA", "null"})
        self.assertEqual(table["sample_note"].tolist(), ["synthetic supplied summaries; not a paper dataset"] * 18)
        original = recipe.pd.read_csv(source, dtype=str, keep_default_na=False)
        self.assertEqual(table[original.columns].to_dict("records"), original.to_dict("records"))
        with Image.open(out / "panel.png") as raster:
            self.assertEqual(raster.size, (394, 299))
        page = PdfReader(out / "panel.pdf").pages[0]
        self.assertAlmostEqual(float(page.mediabox.width) / 72 * 25.4, 100, places=5)
        self.assertAlmostEqual(float(page.mediabox.height) / 72 * 25.4, 76, places=5)
        root = ET.parse(out / "panel.svg").getroot()
        self.assertTrue(any(node.tag.endswith("text") for node in root.iter()))
        stats = json.loads((out / "stats.json").read_text())
        self.assertFalse(stats["model_fitted"])
        self.assertFalse(stats["tests_performed"])
        self.assertFalse(stats["experimental_independence_inferred"])
        self.assertEqual(qa["rendered_text"]["families"], ["DejaVu Sans"])
        self.assertEqual(qa["rendered_text"]["sizes_pt"], [8.0])

    def test_complete_paper_case_and_vector_path_counts(self):
        source = ROOT / "examples/no-author-code/shi-timecourse/source-data.csv"
        spec = json.loads((source.parent / "spec.json").read_text())
        spec["layout"].update(font="DejaVu Sans", dpi=100)
        spec["formats"] = ["svg"]
        out = self.root / "paper"
        qa = recipe.render(source, spec, out)
        self.assertEqual(qa["source_to_artist_audit"]["summary_rows_checked"], 120)
        self.assertEqual(qa["source_to_artist_audit"]["band_endpoints_checked"], 240)
        root = ET.parse(out / "panel.svg").getroot()
        ns = {"s": "http://www.w3.org/2000/svg"}
        elements = json.loads((out / "elements.json").read_text())["elements"]
        bands = [entry for entry in elements if entry["role"] == "uncertainty-band"]
        self.assertEqual(len(bands), 2)
        for entry in bands:
            group = next(node for node in root.iter() if node.get("id") == entry["id"])
            path = group.find("s:path", ns).get("d")
            # All 60 lower and all 60 upper coordinates survive SVG export.
            self.assertGreaterEqual(path.count("L"), 121)
        for entry in [item for item in elements if item["role"] == "mean-curve"]:
            group = next(node for node in root.iter() if node.get("id") == entry["id"])
            self.assertEqual(group.find("s:path", ns).get("d").count("L"), 59)
            self.assertEqual(len(group.findall(".//s:use", ns)), 60)

    def test_new_data_reproduction_preserves_geometry_and_declared_track(self):
        source = ROOT / "examples/no-author-code/shi-timecourse/transfer-reproduce/source-data.csv"
        spec = json.loads((source.parent / "spec.json").read_text())
        spec["layout"].update(font="DejaVu Sans", dpi=100)
        spec["formats"] = ["svg", "png"]
        out = self.root / "new-reproduce"
        qa = recipe.render(source, spec, out, track="reproduce")
        self.assertEqual(qa["status"], "pass")
        self.assertEqual(qa["plotted_summary_rows"], 12)
        self.assertEqual(qa["source_to_artist_audit"]["curves_checked"], 2)
        manifest = json.loads((out / "elements.json").read_text())
        self.assertEqual(manifest["track"], "reproduce")
        self.assertEqual(len([entry for entry in manifest["elements"] if entry["role"] == "mean-curve"]), 2)
        right = next(entry for entry in manifest["elements"] if entry["role"] == "axis-label" and "Length variant" in entry["label"])
        self.assertEqual(right["spec_paths"], ["/labels/right_y"])
        original = recipe.pd.read_csv(source, dtype=str, keep_default_na=False)
        plotted = recipe.pd.read_csv(out / "plotting-data.csv", dtype=str, keep_default_na=False)
        self.assertEqual(original.to_dict("records"), plotted[original.columns].to_dict("records"))

    def test_failed_render_and_invalid_json_invalidate_previous_exports(self):
        out = self.root / "stale"
        recipe.render(self.source, self.spec, out)
        self.source.write_text("minute,mean,sd\n1,2,-1\n2,3,1\n")
        with self.assertRaises(ValueError):
            recipe.render(self.source, self.spec, out)
        self.assertFalse(json.loads((out / "qa.json").read_text())["valid_outputs"])
        (out / "qa.json").write_text('{"status":"pass","valid_outputs":true}')
        bad = self.root / "bad.json"
        bad.write_text("{")
        result = subprocess.run([sys.executable, str(SCRIPT), "--data", str(self.source), "--spec", str(bad), "--out", str(out)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads((out / "qa.json").read_text())["valid_outputs"])


if __name__ == "__main__":
    unittest.main()
