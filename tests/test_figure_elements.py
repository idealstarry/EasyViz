"""Selectable SVG identities must preserve data, geometry and source versions."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.util.spec_from_file_location("elements_test_renderer", ROOT / "skills/easyviz/scripts/render.py")
core = importlib.util.module_from_spec(loader)
loader.loader.exec_module(core)


class FigureElementsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-elements-")
        self.root = Path(self.temp.name)
        self.data = self.root / "source.csv"
        self.data.write_text("unit,condition,x,y\n001,A,1,2\n002,A,2,3\n003,B,3,4\n004,B,4,3\n")
        self.spec = {"chart": "scatter", "fields": {"x": "x", "y": "y", "group": "condition"},
                     "layout": {"width_mm": 120, "height_mm": 90, "font": "DejaVu Sans", "auto_fit": True},
                     "labels": {"x": "X", "y": "Y"}, "formats": ["svg", "pdf", "png"]}

    def tearDown(self):
        core.plt.close("all")
        self.temp.cleanup()

    def render(self, name="attempt", spec=None):
        spec = deepcopy(self.spec if spec is None else spec)
        path = self.root / f"{name}.json"
        path.write_text(json.dumps(spec))
        out = self.root / name
        qa = core.render(self.data, spec, out, spec_path=path)
        self.assertEqual(qa["status"], "pass")
        return out, json.loads((out / "elements.json").read_text())

    def test_ids_exist_in_svg_and_bind_source_spec_and_all_formats(self):
        original = self.data.read_bytes()
        out, manifest = self.render()
        ids = {node.attrib["id"] for node in ET.parse(out / "panel.svg").iter() if "id" in node.attrib}
        listed = [entry["id"] for entry in manifest["elements"]]
        self.assertEqual(len(listed), len(set(listed)))
        self.assertTrue(set(listed) <= ids)
        roles = {entry["role"] for entry in manifest["elements"]}
        self.assertTrue({"axes", "axis-label", "point-group", "legend", "legend-key"} <= roles)
        self.assertEqual(manifest["version"]["input_sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(manifest["version"]["figure_sha256"], hashlib.sha256((out / "panel.svg").read_bytes()).hexdigest())
        colors = json.loads((out / "settings.json").read_text())["resolved_colors"]
        palette = json.dumps(colors, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
        self.assertEqual(manifest["version"]["resolved_colors_sha256"], hashlib.sha256(palette).hexdigest())
        self.assertEqual(Path(manifest["input"]["spec_file"]), (self.root / "attempt.json").resolve())
        resolved, _ = core.resolve_spec(self.spec, spec_path=self.root / "attempt.json")
        canonical = json.dumps(resolved, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
        self.assertEqual(manifest["version"]["spec_sha256"], hashlib.sha256(canonical).hexdigest())
        self.assertEqual(self.data.read_bytes(), original)
        for extension in ("svg", "pdf", "png"):
            self.assertTrue((out / f"panel.{extension}").is_file())
        for element in manifest["elements"]:
            self.assertFalse(set(element["editable"]) & {"x", "y", "area", "size", "value"})

    def test_group_and_label_identities_survive_reordering_and_cosmetic_edit(self):
        _, before = self.render("first")
        changed = deepcopy(self.spec)
        changed.update(order={"group": ["B", "A"]}, colors={"A": "#2581B9", "B": "#DF9A3C"})
        changed["labels"]["x"] = "Updated label"
        _, after = self.render("second", changed)
        first = {(item["role"], item["label"]): item["id"] for item in before["elements"] if item["role"] in ("point-group", "legend-key")}
        second = {(item["role"], item["label"]): item["id"] for item in after["elements"] if item["role"] in ("point-group", "legend-key")}
        self.assertEqual(first, second)
        x_before = next(item for item in before["elements"] if item["spec_paths"] == ["/labels/x"])
        x_after = next(item for item in after["elements"] if item["spec_paths"] == ["/labels/x"])
        self.assertEqual(x_before["id"], x_after["id"])
        self.assertNotEqual(before["version"]["figure_sha256"], after["version"]["figure_sha256"])

    def test_custom_artist_retains_explicit_identity_and_duplicate_fails(self):
        fig, ax = core.plt.subplots()
        line, = ax.plot([1, 2], [3, 4])
        line.set_gid("easyviz-supplied-curve")
        gid = core.figure_elements.register(fig, line, "curve", "Treatment", key="treatment", editable=["color"])
        self.assertEqual(gid, "easyviz-supplied-curve")
        duplicate, = ax.plot([1, 2], [4, 5])
        duplicate.set_gid(gid)
        with self.assertRaisesRegex(ValueError, "Duplicate semantic"):
            core.figure_elements.register(fig, duplicate, "curve", "Other")

    def test_cosmetic_bindings_preserve_literal_categories_and_match_real_artists(self):
        self.data.write_text("unit,condition,x,y\n001,A/~,1,2\n002,A/~,2,3\n003,B,3,4\n004,B,4,3\n")
        spec = deepcopy(self.spec)
        spec["options"] = {"alpha": .35, "regression": True}
        spec["layout"]["line_width_pt"] = 1.2
        artists = {}
        original_write = core.figure_elements.write
        def capture(fig, *args):
            artists.update({item["id"]: item["_artist"] for item in fig._easyviz_elements})
            return original_write(fig, *args)
        with patch.object(core.figure_elements, "write", side_effect=capture):
            _, manifest = self.render("bindings", spec)
        group = next(item for item in manifest["elements"] if item["role"] == "point-group" and item["label"] == "A/~")
        self.assertEqual(group["editable"], {"color": "/colors/A~1~0", "alpha": "/options/alpha"})
        self.assertTrue(set(group["editable"].values()) <= set(group["spec_paths"]))
        line = next(item for item in manifest["elements"] if item["role"] == "fit-line")
        self.assertEqual(line["editable"]["linewidth"], "/layout/line_width_pt")
        self.assertEqual(artists[group["id"]].get_alpha(), .35)
        self.assertEqual(artists[line["id"]].get_linewidth(), 1.2)

    def test_invalid_bindings_fail_before_assigning_artist_identity(self):
        fig, ax = core.plt.subplots()
        line, = ax.plot([0, 1], [1, 2])
        for binding in ({"color": "/colors/absent"}, {"color": "/colors/A~2"}, {"color": "colors.A"}):
            with self.assertRaisesRegex(ValueError, "editable binding"):
                core.figure_elements.register(fig, line, "curve", "A", spec_paths=["/colors/A"], editable=binding)
        self.assertIsNone(line.get_gid())
        self.assertFalse(hasattr(fig, "_easyviz_elements"))

    def test_secondary_axis_label_has_no_invented_main_axis_path(self):
        fig, ax = core.plt.subplots()
        secondary = ax.twinx()
        ax.set_ylabel("Primary")
        secondary.set_ylabel("Secondary")
        core.figure_elements.attach_layout(fig, {"labels": {"y": "Primary"}})
        records = {entry["label"]: entry for entry in fig._easyviz_elements}
        self.assertEqual(records["Primary"]["spec_paths"], ["/labels/y"])
        self.assertEqual(records["Secondary"]["spec_paths"], [])

    def test_explicit_track_is_recorded_without_changing_spec_or_inference(self):
        before = deepcopy(self.spec)
        out = self.root / "tracked"
        core.render(self.data, self.spec, out, track="reproduce")
        self.assertEqual(json.loads((out / "settings.json").read_text())["track"], "reproduce")
        self.assertEqual(json.loads((out / "elements.json").read_text())["track"], "reproduce")
        self.assertEqual(self.spec, before)
        with self.assertRaisesRegex(ValueError, "track must be"):
            core.render(self.data, self.spec, self.root / "invalid-track", track="analysis")
        self.assertFalse((self.root / "invalid-track/panel.svg").exists())

    def test_png_only_attempt_cannot_bind_to_previous_svg(self):
        out, _ = self.render()
        old_svg = (out / "panel.svg").read_bytes()
        spec = deepcopy(self.spec)
        spec["formats"] = ["png"]
        core.render(self.data, spec, out)
        manifest = json.loads((out / "elements.json").read_text())
        self.assertIsNone(manifest["version"]["figure_sha256"])
        self.assertEqual((out / "panel.svg").read_bytes(), old_svg)

    def test_metadata_tags_do_not_change_rendered_heatmap_pixels(self):
        fixture = ROOT / "skills/easyviz/assets/fixtures/heatmap"
        spec = json.loads((fixture / "spec.json").read_text())
        spec["layout"]["font"] = "DejaVu Sans"
        spec["formats"] = ["svg", "png"]
        tagged, baseline = self.root / "tagged", self.root / "without-tags"
        core.render(fixture / "data.csv", spec, tagged)
        with patch.object(core.figure_elements, "register"), patch.object(core.figure_elements, "attach_layout"), patch.object(core.figure_elements, "write"):
            core.render(fixture / "data.csv", spec, baseline)
        with Image.open(baseline / "panel.png") as expected, Image.open(tagged / "panel.png") as actual:
            self.assertEqual(expected.size, actual.size)
            self.assertIsNone(ImageChops.difference(expected.convert("RGBA"), actual.convert("RGBA")).getbbox(alpha_only=False))


if __name__ == "__main__":
    unittest.main()
