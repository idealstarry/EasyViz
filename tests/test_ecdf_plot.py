"""Checks for exact empirical steps, literal identifiers and complete exports."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

from PIL import Image
from pypdf import PdfReader

SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/ecdf_plot.py"
loader = importlib.util.spec_from_file_location("easyviz_ecdf_test", SCRIPT)
ecdf = importlib.util.module_from_spec(loader)
loader.loader.exec_module(ecdf)


class EcdfPlotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-ecdf-")
        self.root = Path(self.temp.name)
        self.base = {"chart": "ecdf", "fields": {"value": "measurement"}, "colors": {"all": "#5278A8"},
                     "layout": {"width_mm": 88, "height_mm": 70, "font": "DejaVu Sans", "font_size_pt": 8, "dpi": 100},
                     "formats": ["png"], "labels": {"x": "Measurement (a.u.)"}}

    def tearDown(self):
        ecdf.plt.close("all")
        self.temp.cleanup()

    def csv(self, text):
        path = self.root / "input.csv"
        path.write_text(text)
        return path

    def draw(self, source, spec):
        data = ecdf.prepare(source, spec)
        resolved = deepcopy(spec)
        resolved["layout"].setdefault("auto_fit", "margins" not in resolved["layout"])
        layout, typography, rc = ecdf.setup(resolved)
        with ecdf.plt.rc_context(rc):
            fig, colors, summary = ecdf.draw(data, resolved, layout, typography)
            fig.canvas.draw()
        return data, fig, summary

    def test_ties_form_full_jumps_and_audit_checks_actual_step_vertices(self):
        source = self.csv("measurement,note\n3,last\n1,first\n1,tied\n2,middle\n")
        spec = deepcopy(self.base)
        spec["options"] = {"x_limits": [0, 4], "curve_line_width_pt": .9}
        data, fig, table = self.draw(source, spec)
        self.assertEqual(table["value"].tolist(), [1, 2, 3])
        self.assertEqual(table["jump_count"].tolist(), [2, 1, 1])
        self.assertEqual(table["cumulative_count"].tolist(), [2, 3, 4])
        self.assertEqual(table["cumulative_fraction"].tolist(), [.5, .75, 1])
        self.assertEqual(json.loads(table["source_rows"].iloc[0]), [2, 3])
        line = fig._easyviz_ecdf_artists[0]["line"]
        self.assertEqual(line.get_path().vertices.tolist(), [[0, 0], [1, 0], [1, .5], [2, .5], [2, .75], [3, .75], [3, 1], [4, 1], [4, 1]])
        self.assertEqual(ecdf.audit_source_artists(source, spec, fig)["status"], "pass")
        line.set_ydata([0, .25, .75, 1, 1])
        issues = ecdf.audit_source_artists(source, spec, fig)["issues"]
        self.assertIn("empirical_step_coordinates_changed", {r["code"] for r in issues})
        self.assertEqual(data["note"].tolist(), ["last", "first", "tied", "middle"])

    def test_changed_schema_leading_identifiers_and_group_order(self):
        source = self.csv("reading,phase,participant,unused\n2,NA,001,a\n2,null,001,b\n7,NA,002,c\n1,null,002,d\n")
        spec = deepcopy(self.base)
        spec.update(fields={"value": "reading", "group": "phase", "unit": "participant"}, order={"group": ["null", "NA"]}, colors={"NA": "#5278A8", "null": "#C2764E"})
        out = self.root / "changed"
        qa = ecdf.render(source, spec, out)
        self.assertEqual(qa["status"], "pass")
        table = ecdf.pd.read_csv(out / "plotting-data.csv", dtype=object, keep_default_na=False)
        self.assertEqual(table["participant"].tolist(), ["001", "001", "002", "002"])
        self.assertEqual(table["phase"].tolist(), ["NA", "null", "NA", "null"])
        cumulative = ecdf.pd.read_csv(out / "cumulative-data.csv", dtype=object, keep_default_na=False)
        self.assertEqual(cumulative["group"].tolist(), ["null", "null", "NA", "NA"])
        stats = json.loads((out / "stats.json").read_text())
        self.assertEqual(stats["observation_counts"], {"null": 2, "NA": 2})
        self.assertFalse(stats["tests_performed"])
        self.assertFalse(stats["experimental_independence_inferred"])
        data, fig, _ = self.draw(source, spec)
        self.assertEqual([r["group"] for r in fig._easyviz_ecdf_artists], ["null", "NA"])
        keys = fig._easyviz_legend_layout.entries[0]["artist"].legend_handles
        self.assertTrue(all(h.get_marker() == "None" and h.get_linewidth() == .8 and h.get_linestyle() == "-" for h in keys))
        self.assertEqual(ecdf.audit_source_artists(source, spec, fig)["audited_observations"], 4)

    def test_invalid_log_limits_and_duplicate_units_fail_without_dropping(self):
        source = self.csv("measurement,id\n0,001\n2,002\n")
        bad = []
        log = deepcopy(self.base)
        log["options"] = {"x_scale": "log"}
        bad.append((source, log, "strictly positive"))
        cropped = deepcopy(self.base)
        cropped["options"] = {"x_limits": [.1, 3]}
        bad.append((source, cropped, "clip supplied"))
        duplicated = self.root / "duplicate.csv"
        duplicated.write_text("measurement,id\n1,001\n2,001\n")
        units = deepcopy(self.base)
        units["fields"]["unit"] = "id"
        bad.append((duplicated, units, "Duplicate unit"))
        for path, spec, message in bad:
            with self.subTest(message=message), self.assertRaisesRegex(ecdf.SpecError, message):
                ecdf.prepare(path, spec)

    def test_unknown_settings_bad_ticks_and_unused_roles_are_rejected(self):
        source = self.csv("measurement\n1\n2\n")
        changes = [("options", {"x_tikcs": [1, 2]}), ("options", {"x_ticks": [2, 1]}),
                   ("options", {"x_ticks": [1, 1]}), ("options", {"x_ticks": [True]}),
                   ("options", {"x_scale": "log", "x_ticks": [0, 1]}),
                   ("labels", {"title": "Ignored title"}), ("statistics", {"method": "ks"}),
                   ("order", {"group": ["all"]}), ("colors", {"all": "#00000000"}),
                   ("legends", {"categorical": {"position": "bottom"}})]
        for key, value in changes:
            spec = deepcopy(self.base)
            spec[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ecdf.SpecError):
                ecdf.prepare(source, spec)
        spec = deepcopy(self.base)
        spec["options"] = {"x_ticks": [-10, 1]}
        with self.assertRaisesRegex(ecdf.SpecError, "displayed x_limits"):
            self.draw(source, spec)

    def test_log_exports_retain_dimensions_font_and_editable_svg_text(self):
        source = self.csv("measurement\n1\n10\n10\n100\n")
        spec = deepcopy(self.base)
        spec["options"] = {"x_scale": "log", "x_limits": [.1, 1000], "x_ticks": [1, 10, 100]}
        spec["formats"] = ["pdf", "svg", "png", "tiff"]
        out = self.root / "log"
        qa = ecdf.render(source, spec, out)
        self.assertEqual(qa["status"], "pass")
        self.assertEqual(qa["source_to_artist_audit"]["audited_observations"], 4)
        page = PdfReader(out / "panel.pdf").pages[0]
        self.assertAlmostEqual(float(page.mediabox.width) / 72 * 25.4, 88, places=5)
        self.assertAlmostEqual(float(page.mediabox.height) / 72 * 25.4, 70, places=5)
        for extension in ("png", "tiff"):
            with Image.open(out / f"panel.{extension}") as image:
                self.assertEqual(image.size, (round(88 / 25.4 * 100), round(70 / 25.4 * 100)))
        self.assertIn("<text", (out / "panel.svg").read_text())
        settings = json.loads((out / "settings.json").read_text())
        self.assertEqual(settings["layout"]["actual_font"], "DejaVu Sans")
        self.assertEqual(settings["typography"], {"axis": 8, "tick": 8, "legend": 8, "annotation": 8, "title": 9, "panel": 9})
        self.assertEqual(settings["axis"]["x_limits"], [.1, 1000])
        self.assertEqual(settings["curve_policy"]["fraction_range"], [0, 1])
        self.assertEqual(len(settings["renderer"]["helper_sha256"]["render.py"]), 64)

    def test_power10_tick_labels_preserve_positions_curves_and_font(self):
        source = self.csv("measurement\n1\n10\n100\n")
        plain = deepcopy(self.base)
        plain["layout"]["font"] = "DejaVu Serif"
        plain["options"] = {"x_scale": "log", "x_limits": [.1, 1000], "x_ticks": [.1, 1, 10, 100, 1000]}
        _, plain_fig, _ = self.draw(source, plain)
        compact = deepcopy(plain)
        compact["options"]["x_tick_format"] = "power10"
        _, fig, _ = self.draw(source, compact)
        self.assertEqual(fig.axes[0].get_xticks().tolist(), [.1, 1, 10, 100, 1000])
        self.assertEqual([t.get_text() for t in fig.axes[0].get_xticklabels()], ["$10^{-1}$", "$10^{0}$", "$10^{1}$", "$10^{2}$", "$10^{3}$"])
        self.assertTrue(all(t.get_fontsize() == 8 for t in fig.axes[0].get_xticklabels()))
        self.assertEqual(fig._easyviz_ecdf_artists[0]["line"].get_path().vertices.tolist(), plain_fig._easyviz_ecdf_artists[0]["line"].get_path().vertices.tolist())
        self.assertEqual(ecdf.audit_source_artists(source, compact, fig)["status"], "pass")
        compact["formats"] = ["pdf", "svg"]
        out = self.root / "power10"
        self.assertEqual(ecdf.render(source, compact, out)["status"], "pass")
        fonts = PdfReader(out / "panel.pdf").pages[0]["/Resources"]["/Font"].get_object()
        self.assertEqual({str(v.get_object()["/BaseFont"]).split("+")[-1] for v in fonts.values()}, {"DejaVuSerif"})
        for options in ({"x_tick_format": "power10", "x_ticks": [1, 10]},
                        {"x_tick_format": "power10", "x_scale": "log", "x_ticks": [1, 20]},
                        {"x_tick_format": "power10", "x_scale": "log"},
                        {"x_tick_format": "plaen", "x_scale": "log", "x_ticks": [1, 10]}):
            invalid = deepcopy(self.base)
            invalid["options"] = options
            with self.subTest(options=options), self.assertRaises(ecdf.SpecError):
                ecdf.prepare(source, invalid)

    def test_manual_margins_are_retained_and_auto_fit_conflict_fails(self):
        source = self.csv("measurement\n1\n2\n")
        spec = deepcopy(self.base)
        spec["layout"]["margins"] = {"left": .2, "right": .95, "bottom": .22, "top": .95}
        out = self.root / "manual"
        qa = ecdf.render(source, spec, out)
        self.assertNotIn("auto_layout", qa)
        self.assertEqual(json.loads((out / "settings.json").read_text())["layout"]["margins"], spec["layout"]["margins"])
        spec["layout"]["auto_fit"] = True
        with self.assertRaisesRegex(ecdf.SpecError, "conflicting"):
            ecdf.render(source, spec, out)
        self.assertFalse(json.loads((out / "qa.json").read_text())["valid_outputs"])

    def test_failed_attempt_invalidates_old_exports_and_closes_figures(self):
        source = self.csv("measurement\n1\n2\n")
        out = self.root / "stale"
        ecdf.render(source, self.base, out)
        source.write_text("measurement\nmissing\n")
        with self.assertRaisesRegex(ecdf.SpecError, "numeric"):
            ecdf.render(source, self.base, out)
        qa = json.loads((out / "qa.json").read_text())
        self.assertEqual(qa["status"], "failed")
        self.assertFalse(qa["valid_outputs"])
        self.assertTrue((out / "panel.png").exists())
        self.assertEqual(ecdf.plt.get_fignums(), [])

    def test_source_mutation_after_export_is_a_failed_qa(self):
        source = self.csv("measurement\n1\n2\n")
        original = ecdf.core.export
        def changed(*args):
            exports = original(*args)
            source.write_text("measurement\n1\n3\n")
            return exports
        out = self.root / "changed-source"
        with mock.patch.object(ecdf.core, "export", side_effect=changed), self.assertRaisesRegex(ecdf.SpecError, "source-to-curve"):
            ecdf.render(source, self.base, out)
        qa = json.loads((out / "qa.json").read_text())
        self.assertEqual(qa["status"], "needs_revision")
        self.assertFalse(qa["valid_outputs"])
        self.assertIn("source_changed_during_render", {i["code"] for i in qa["source_to_artist_audit"]["issues"]})

    def test_actual_svg_retains_every_dense_step_and_tied_jump(self):
        # Narrow horizontal steps trigger Matplotlib's default simplifier.
        # Derive physical SVG vertices directly from this source and the
        # explicit manual layout, independently of the plotted Line2D path.
        source = self.csv("measurement\n" + "\n".join(str(v) for v in range(1, 161)) + "\n80\n")
        spec = deepcopy(self.base)
        spec["formats"] = ["svg"]
        spec["layout"]["margins"] = {"left": .2, "right": .95, "bottom": .22, "top": .95}
        spec["options"] = {"x_limits": [0, 10000], "x_ticks": [0, 10000]}
        out = self.root / "dense-steps"
        self.assertEqual(ecdf.render(source, spec, out)["status"], "pass")
        root = ET.parse(out / "panel.svg").getroot()
        ns = {"s": "http://www.w3.org/2000/svg"}
        path = root.find(".//s:g[@id='easyviz-ecdf-curve-0']/s:path", ns)
        self.assertIsNotNone(path)
        actual = [[float(x), float(y)] for x, y in re.findall(r"[ML]\s+([-+\d.eE]+)\s+([-+\d.eE]+)", path.attrib["d"])]
        points, cumulative = [[0., 0.]], 0
        for value in range(1, 161):
            points.append([value, cumulative / 161])
            cumulative += 2 if value == 80 else 1
            points.append([value, cumulative / 161])
        points.extend([[10000., 1.], [10000., 1.]])
        width, height = 88 / 25.4 * 72, 70 / 25.4 * 72
        expected = [[width * (.2 + x / 10000 * .75), height * (1 - .22 - (y + .02) / 1.04 * .73)] for x, y in points]
        self.assertEqual(len(actual), 323)
        ecdf.np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-6)
        settings = json.loads((out / "settings.json").read_text())
        self.assertFalse(settings["curve_policy"]["path_simplification"])


if __name__ == "__main__":
    unittest.main()
