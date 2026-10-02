"""Shared panel settings must survive changed categories and export geometry."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from PIL import Image
from pypdf import PdfReader
import pandas as pd
from marker_geometry import collection_fill_areas_pt2


SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/render.py"
loader = importlib.util.spec_from_file_location("easyviz_profile_renderer", SCRIPT)
renderer = importlib.util.module_from_spec(loader)
loader.loader.exec_module(renderer)


class FigureProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-profile-")
        self.root = Path(self.temp.name)
        self.profile = self.root / "figure-profile.json"
        self.profile_data = {
            "version": 1,
            "layout": {"font": "DejaVu Sans", "font_size_pt": 9, "line_width_pt": .7, "dpi": 120},
            "typography": {"title": 9, "panel": 9},
            "colors": {"Control": "#29ACF3", "Treatment": "#E47751"},
            "continuous_scales": {"score": {"colormap": "blue-white-red", "color_limits": [-2, 2], "color_center": 0}},
            "panels": {"A": {"width_mm": 110, "height_mm": 75}, "B": {"width_mm": 132, "height_mm": 88}},
        }
        self.profile.write_text(json.dumps(self.profile_data))
        self.base = {"profile": self.profile.name, "panel": "A", "chart": "scatter", "fields": {"x": "x", "y": "y", "group": "arm"}, "formats": ["pdf", "svg", "png"]}

    def tearDown(self):
        renderer.plt.close("all")
        self.temp.cleanup()

    def csv(self, name, content):
        path = self.root / name
        path.write_text(content)
        return path

    def test_shared_colors_and_physical_settings_survive_subset_and_order_changes(self):
        full = self.csv("full.csv", "arm,x,y\nControl,1,2\nTreatment,2,3\nControl,3,4\nTreatment,4,2\n")
        subset = self.csv("subset.csv", "arm,x,y\nTreatment,2,3\nTreatment,4,2\n")
        original = {path: path.read_bytes() for path in (full, subset, self.profile)}
        for name, data, panel, order in (("full", full, "A", ["Treatment", "Control"]), ("subset", subset, "B", ["Treatment"])):
            spec = deepcopy(self.base)
            spec["panel"] = panel
            spec["order"] = {"group": order}
            original_spec = deepcopy(spec)
            output = self.root / name
            renderer.render(data, spec, output, spec_path=self.root / f"{name}.json")
            self.assertEqual(spec, original_spec, "Resolving a profile must not rewrite the caller's specification")
            settings = json.loads((output / "settings.json").read_text())
            self.assertEqual(settings["resolved_colors"]["Treatment"], "#E47751")
            self.assertEqual(settings["colors"], self.profile_data["colors"], "Keep the complete map, even when a category is absent")
            self.assertEqual(settings["typography"]["axis"], 9)
            self.assertEqual(settings["typography"]["tick"], 9)
            self.assertEqual(settings["layout"]["line_width_pt"], .7)
            self.assertEqual(settings["figure_profile"]["path"], str(self.profile.resolve()))
            self.assertEqual(settings["figure_profile"]["sha256"], hashlib.sha256(original[self.profile]).hexdigest())
            self.assertEqual(settings["figure_profile"]["source_specification"], original_spec)
            dims = self.profile_data["panels"][panel]
            page = PdfReader(output / "panel.pdf").pages[0]
            self.assertAlmostEqual(float(page.mediabox.width) * 25.4 / 72, dims["width_mm"], places=5)
            self.assertAlmostEqual(float(page.mediabox.height) * 25.4 / 72, dims["height_mm"], places=5)
            with Image.open(output / "panel.png") as image:
                self.assertEqual(image.size, (round(dims["width_mm"] * 120 / 25.4), round(dims["height_mm"] * 120 / 25.4)))
            svg = ET.parse(output / "panel.svg").getroot()
            treatment_marks = [node for node in svg.iter() if node.tag.endswith("use") and "fill: #e47751" in node.attrib.get("style", "")]
            self.assertGreaterEqual(len(treatment_marks), 2, "Inspect serialized plotted color, not only recorded configuration")
            plotted = pd.read_csv(output / "plotting-data.csv")
            source = pd.read_csv(data)
            self.assertEqual(plotted[["arm", "x", "y"]].to_dict("list"), source.to_dict("list"))
        for path, content in original.items():
            self.assertEqual(path.read_bytes(), content)

    def test_named_continuous_scale_does_not_follow_local_observed_range(self):
        for name, values in (("wide", [-2, 0, 1, 2]), ("narrow", [-.5, 0, .5, 1])):
            spec = {"profile": self.profile.name, "panel": "A", "continuous_scale": "score", "chart": "heatmap", "fields": {"row": "row", "column": "column", "value": "value"}, "formats": ["svg"]}
            data = self.csv(f"{name}.csv", "row,column,value\n" + "".join(f"{r},{c},{v}\n" for (r, c), v in zip([(1, 1), (1, 2), (2, 1), (2, 2)], values)))
            output = self.root / name
            renderer.render(data, spec, output, spec_path=self.root / "plot.json")
            settings = json.loads((output / "settings.json").read_text())
            self.assertEqual(settings["options"]["color_limits"], [-2, 2])
            self.assertEqual(settings["options"]["color_center"], 0)
            self.assertEqual(settings["figure_profile"]["continuous_scale"], "score")
            self.assertEqual(settings["colormap"], "blue-white-red")
        spec["options"] = {"color_limits": [-1, 1]}
        with self.assertRaisesRegex(renderer.SpecError, "color_limits conflicts"):
            renderer.resolve_spec(spec, spec_path=self.root / "plot.json")

    def test_shared_dot_size_scale_preserves_actual_area_with_different_maxima(self):
        self.profile_data["size_scales"] = {"count": {"size_max": 100, "max_area_pt2": 100, "size_legend": [25, 50, 100]}}
        self.profile_data["panels"] = {"A": {"width_mm": 160, "height_mm": 100}, "B": {"width_mm": 180, "height_mm": 125}}
        self.profile.write_text(json.dumps(self.profile_data))
        source_bytes = self.profile.read_bytes()
        common_marker_dimensions = []
        for name, maximum, panel in (("wide", 100, "A"), ("narrow", 20, "B")):
            data = self.csv(f"{name}.csv", f"x,y,size,color\nA,F1,25,0\nB,F1,{maximum},1\nA,F2,10,-1\nB,F2,5,.5\n")
            body = data.read_bytes()
            spec = {"profile": self.profile.name, "panel": panel, "size_scale": "count", "continuous_scale": "score", "chart": "dotplot", "fields": {"x": "x", "y": "y", "size": "size", "color": "color"}, "formats": ["svg"]}
            output = self.root / name
            renderer.render(data, spec, output, spec_path=self.root / "plot.json")
            settings = json.loads((output / "settings.json").read_text())
            self.assertEqual(settings["figure_profile"]["size_scale"], "count")
            self.assertEqual(settings["options"]["size_max"], 100)
            plotted = pd.read_csv(output / "plotting-data.csv")
            self.assertEqual(plotted.loc[0, "_easyviz_area_pt2"], 25)
            resolved, _ = renderer.resolve_spec(spec, spec_path=self.root / "plot.json")
            prepared = renderer.prepare(data, resolved)
            layout, typography, rc = renderer.setup(resolved)
            with renderer.plt.rc_context(rc):
                fig, _ = renderer.draw(prepared, resolved, layout, typography, {"method": "none"})
                self.assertAlmostEqual(collection_fill_areas_pt2(fig.axes[0].collections[0], fig)[0], 25, places=4, msg="The actual circular path must use the shared geometric fill area")
                self.assertAlmostEqual(fig.axes[0].collections[0].get_sizes()[0], 25 * 4 / renderer.math.pi)
                renderer.plt.close(fig)
            # The first supplied quantity is identical across panels. Compare its
            # serialized marker shape in page points, independently of settings.
            svg = ET.parse(output / "panel.svg").getroot()
            group = next(node for node in svg.iter() if node.attrib.get("id") == "PathCollection_1")
            path = next(node.attrib["d"] for node in group.iter() if node.tag.endswith("path"))
            numbers = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?(?:e[+-]?\d+)?", path, flags=re.I)]
            xs, ys = numbers[::2], numbers[1::2]
            common_marker_dimensions.append((max(xs) - min(xs), max(ys) - min(ys)))
            for diameter in common_marker_dimensions[-1]:
                self.assertAlmostEqual(diameter, 2 * (25 / renderer.math.pi) ** .5, places=5)
            self.assertEqual(data.read_bytes(), body)
        for first, second in zip(*common_marker_dimensions):
            self.assertAlmostEqual(first, second, places=5, msg="Equal quantities must export equal marker dimensions at different canvas sizes")
        self.assertEqual(self.profile.read_bytes(), source_bytes)

        for local, message in (({"size_max": 25}, "size_max conflicts"), ({"max_area_pt2": 90}, "max_area_pt2 conflicts"), ({"size_legend": [10, 25]}, "size_legend conflicts")):
            with self.subTest(local=local), self.assertRaisesRegex(renderer.SpecError, message):
                renderer.resolve_spec({**spec, "options": local}, spec_path=self.root / "plot.json")
        with self.assertRaisesRegex(renderer.SpecError, "only for dotplot"):
            renderer.resolve_spec({**self.base, "size_scale": "count"}, spec_path=self.root / "plot.json")
        with self.assertRaisesRegex(renderer.SpecError, "Unknown size_scale"):
            renderer.resolve_spec({**spec, "size_scale": "unknown"}, spec_path=self.root / "plot.json")

        # Merely defining size scales must not change panels that do not select
        # one. Their existing local/default behavior remains available.
        no_shared_scale = {key: value for key, value in spec.items() if key != "size_scale"}
        resolved, record = renderer.resolve_spec(no_shared_scale, spec_path=self.root / "plot.json")
        self.assertNotIn("size_max", resolved["options"])
        self.assertNotIn("max_area_pt2", resolved["options"])
        self.assertIsNone(record["size_scale"])

    def test_named_scales_reject_degenerate_ranges_and_invalid_size_keys(self):
        invalid = [({"continuous_scales": {"score": {"colormap": "viridis", "color_limits": [0, 0]}}}, "strictly increasing"),
                   ({"size_scales": {"count": {"size_max": 100}}}, "requires size_max and max_area_pt2"),
                   ({"size_scales": {"count": {"size_max": 0, "max_area_pt2": 100}}}, "must be positive"),
                   ({"size_scales": {"count": {"size_max": 100, "max_area_pt2": 100, "size_legend": [150]}}}, "must not exceed size_max")]
        for change, message in invalid:
            self.profile.write_text(json.dumps({**self.profile_data, **change}))
            with self.subTest(change=change), self.assertRaisesRegex(renderer.SpecError, message):
                renderer.resolve_spec(self.base, spec_path=self.root / "plot.json")
        # Standalone constant data still uses the existing automatic range.
        _, norm = renderer.continuous({"colormap": "viridis"}, [0, 0])
        self.assertEqual((norm.vmin, norm.vmax), (-.5, .5))

    def test_conflicts_are_errors_and_failed_reruns_invalidate_previous_exports(self):
        data = self.csv("input.csv", "arm,x,y\nTreatment,1,2\nTreatment,2,3\n")
        output = self.root / "out"
        renderer.render(data, self.base, output, spec_path=self.root / "plot.json")
        cases = [({"layout": {"font_size_pt": 12}}, "font_size_pt conflicts"),
                 ({"layout": {"width_mm": 88}}, "width_mm conflicts"),
                 ({"colors": {"Treatment": "#000000"}}, "Treatment conflicts"),
                 ({"colors": {"Other": "#000000"}}, "Other is absent"),
                 ({"palette": "somerville-bright"}, "palette cannot be combined")]
        for change, message in cases:
            spec = {**deepcopy(self.base), **change}
            with self.subTest(change=change), self.assertRaisesRegex(renderer.SpecError, message):
                renderer.render(data, spec, output, spec_path=self.root / "plot.json")
            self.assertFalse(json.loads((output / "qa.json").read_text())["valid_outputs"])
        matching = {**deepcopy(self.base), "colors": {"Treatment": "#e47751"}}
        resolved, _ = renderer.resolve_spec(matching, spec_path=self.root / "plot.json")
        self.assertEqual(set(resolved["colors"]), {"Control", "Treatment"})

    def test_unknown_fields_and_wrong_types_fail_with_actionable_messages(self):
        cases = [({"layout": {"fontsize_pt": 12}}, "use font_size_pt"),
                 ({"layout": {"font_size_pt": "12"}}, "finite JSON number"),
                 ({"layout": {"dpi": True}}, "finite JSON number"),
                 ({"layout": {"margins": {"lef": .2}}}, "use left"),
                 ({"typography": {"ticks": 9}}, "use tick"),
                 ({"fields": {"x": "x", "y": "y", "groups": "arm"}}, "Unknown fields"),
                 ({"labels": {"xlabel": "x"}}, "Unknown labels"),
                 ({"labels": {"x": 2}}, "must be a string"),
                 ({"order": {"groups": ["Treatment"]}}, "Unknown order"),
                 ({"order": {"group": "Treatment"}}, "must be a list"),
                 ({"formats": "svg"}, "nonempty list"),
                 ({"statistics": {"annotate": "false"}}, "must be a boolean"),
                 ({"seed": True}, "nonnegative integer"),
                 ({"typo": 1}, "Unknown specification")]
        standalone = {"chart": "scatter", "fields": {"x": "x", "y": "y"}}
        for change, message in cases:
            with self.subTest(change=change), self.assertRaisesRegex(renderer.SpecError, message):
                renderer.resolve_spec({**standalone, **change})
        with self.assertRaisesRegex(renderer.SpecError, "use font_size_pt"):
            renderer.setup({"layout": {"fontsize_pt": 12}})
        malformed = deepcopy(self.profile_data)
        malformed["layout"]["fontsize_pt"] = 12
        self.profile.write_text(json.dumps(malformed))
        with self.assertRaisesRegex(renderer.SpecError, "use font_size_pt"):
            renderer.resolve_spec(self.base, spec_path=self.root / "plot.json")

    def test_cli_profile_and_panel_arguments_and_relative_spec_paths(self):
        data = self.csv("input.csv", "arm,x,y\nTreatment,1,2\nTreatment,2,3\n")
        spec = {"chart": "scatter", "fields": {"x": "x", "y": "y", "group": "arm"}, "formats": ["svg"]}
        path = self.root / "plot.json"
        path.write_text(json.dumps(spec))
        output = self.root / "cli"
        result = subprocess.run([sys.executable, str(SCRIPT), "--data", str(data), "--spec", str(path), "--out", str(output), "--profile", str(self.profile), "--panel", "B"], cwd=self.root.parent, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["width_mm"], 132)
        spec.update(profile=self.profile.name, panel="A")
        path.write_text(json.dumps(spec))
        result = subprocess.run([sys.executable, str(SCRIPT), "--data", str(data), "--spec", str(path), "--out", str(output)], cwd=self.root.parent, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["width_mm"], 110)
        with self.assertRaisesRegex(renderer.SpecError, "--panel.*disagree"):
            renderer.resolve_spec(spec, panel="B", spec_path=path)
        with self.assertRaisesRegex(renderer.SpecError, "panel and continuous_scale require"):
            renderer.resolve_spec({"chart": "scatter", "fields": {"x": "x", "y": "y"}, "panel": "A"})


if __name__ == "__main__":
    unittest.main()
