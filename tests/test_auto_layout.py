"""Transfer checks for measured layout at fixed size and typography."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image
import pandas as pd
from marker_geometry import collection_fill_areas_pt2

SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/render.py"
loader = importlib.util.spec_from_file_location("easyviz_fit_renderer", SCRIPT)
renderer = importlib.util.module_from_spec(loader)
loader.loader.exec_module(renderer)
interval_loader = importlib.util.spec_from_file_location("easyviz_fit_interval", SCRIPT.with_name("interval_plot.py"))
interval_renderer = importlib.util.module_from_spec(interval_loader)
interval_loader.loader.exec_module(interval_renderer)


class AutoLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-fit-")
        self.root = Path(self.temp.name)
        self.layout = {"width_mm": 88, "height_mm": 70, "font": "DejaVu Sans",
                       "font_size_pt": 8, "dpi": 100, "auto_fit": True}

    def tearDown(self):
        renderer.plt.close("all")
        self.temp.cleanup()

    def run_panel(self, body, spec, name="output"):
        source = self.root / "input.csv"
        source.write_text(body)
        out = self.root / name
        qa = renderer.render(source, spec, out)
        return qa, json.loads((out / "settings.json").read_text()), out

    def test_no_guide_recovers_space_preserving_canvas_and_fonts(self):
        spec = {"chart": "scatter", "fields": {"x": "x", "y": "y"},
                "layout": self.layout, "labels": {"x": "Dose (mg)", "y": "Response"},
                "formats": ["svg", "png", "pdf"]}
        qa, settings, out = self.run_panel("x,y\n1,2\n2,7\n3,4\n4,9\n", spec)
        self.assertGreater(settings["auto_layout"]["data_area_fraction"], .60)
        self.assertEqual(settings["typography"]["tick"], 8)
        self.assertEqual(settings["typography"]["axis"], 8)
        self.assertEqual(qa["input_rows"], 4)
        self.assertEqual(settings["layout"]["width_mm"], 88)
        with Image.open(out / "panel.png") as image:
            self.assertEqual(image.size, (round(88 / 25.4 * 100), round(70 / 25.4 * 100)))
        self.assertAlmostEqual(qa["exports"]["pdf"]["width_mm"], 88, places=5)

    def test_long_row_labels_fit_without_truncation(self):
        body = "g,v\nActivated macrophages,1\nActivated macrophages,2\nResident monocytes,3\nResident monocytes,4\n"
        spec = {"chart": "distribution", "fields": {"group": "g", "value": "v"},
                "options": {"orientation": "horizontal"}, "layout": self.layout,
                "labels": {"x": "Prepared score"}, "formats": ["svg", "png"]}
        qa, settings, out = self.run_panel(body, spec)
        self.assertEqual(qa["status"], "pass")
        self.assertGreater(settings["layout"]["margins"]["left"], .19)
        svg = (out / "panel.svg").read_text()
        self.assertIn("Activated macrophages", svg)
        self.assertIn("Resident monocytes", svg)
        self.assertEqual(len(pd.read_csv(out / "plotting-data.csv")), 4)

    def test_categorical_guide_measured_and_outside_data(self):
        spec = {"chart": "scatter", "fields": {"x": "x", "y": "y", "group": "g"},
                "layout": self.layout, "formats": ["png"]}
        qa, settings, _ = self.run_panel("x,y,g\n1,2,Untreated\n2,3,Untreated\n3,4,Treatment\n4,2,Treatment\n", spec)
        self.assertEqual(qa["legend_layout"]["status"], "pass")
        self.assertEqual(qa["auto_layout"]["status"], "pass")
        self.assertEqual(len(settings["auto_layout"]["attempts"]), 3)
        self.assertGreater(settings["auto_layout"]["data_area_fraction"], .5)

    def test_dot_guides_preserve_quantitative_area_and_zero(self):
        body = "x,y,s,c\nA,G1,0,1\nB,G1,1,2\nA,G2,2,3\nB,G2,4,4\n"
        spec = {"chart": "dotplot", "fields": {"x": "x", "y": "y", "size": "s", "color": "c"},
                "layout": {**self.layout, "width_mm": 120, "height_mm": 100},
                "options": {"size_max": 4, "max_area_pt2": 64}, "formats": ["png"]}
        qa, _, out = self.run_panel(body, spec)
        self.assertEqual(qa["dot_states"]["zero_rows"], 1)
        table = pd.read_csv(out / "plotting-data.csv")
        self.assertEqual(table["_easyviz_area_pt2"].tolist(), [0., 16., 32., 64.])
        sizes = [entry for entry in qa["legend_layout"]["legends"] if entry["kind"] == "size"]
        self.assertEqual(sizes[0]["marker_areas_pt2"], [16., 32., 64.])
        self.assertEqual(qa["status"], "pass")

    def assert_largest_feasible_candidate(self, fitted):
        self.assertEqual([a["automatic_guide_side"] for a in fitted["attempts"]],
                         ["right", "bottom", "top"])
        feasible = [a["data_area_fraction"] for a in fitted["attempts"] if not a["issues"]]
        self.assertTrue(feasible)
        self.assertAlmostEqual(fitted["data_area_fraction"], max(feasible), places=8)

    def test_two_categorical_guides_share_feasible_horizontal_band(self):
        source = self.root / "interval.csv"
        source.write_text("readout,batch,ratio,lo,hi,state\n"
                          "Signal recovery after dilution,A,2,1.5,3,filled\n"
                          "Signal recovery after dilution,B,1,.5,2,hollow\n"
                          "Preparation yield,A,3,2,4,filled\n"
                          "Preparation yield,B,1.5,.8,2,hollow\n")
        spec = {"chart": "interval", "fields": {"label": "readout", "series": "batch",
                "estimate": "ratio", "lower": "lo", "upper": "hi", "mark_state": "state"},
                "options": {"mark_fill": "input", "marker_area_pt2": 20},
                "labels": {"filled": "Prepared filled state", "hollow": "Prepared hollow state"},
                "layout": {**self.layout, "width_mm": 140, "height_mm": 100},
                "formats": ["png", "svg"]}
        out = self.root / "interval"
        qa = interval_renderer.render(source, spec, out)
        self.assert_largest_feasible_candidate(qa["auto_layout"])
        guides = qa["legend_layout"]["legends"]
        self.assertEqual([g["kind"] for g in guides], ["categorical", "categorical"])
        self.assertIn(guides[0]["chosen_settings"]["position"], ("bottom", "top"))
        self.assertEqual(guides[0]["chosen_settings"]["position"], guides[1]["chosen_settings"]["position"])
        self.assertFalse(qa["legend_layout"]["combined"]["has_envelope_overlap"])
        # Both horizontal candidates must work, rather than merely falling
        # back to the pre-fix right arrangement after collision failures.
        self.assertTrue(all(not a["issues"] for a in qa["auto_layout"]["attempts"][1:]))
        self.assertEqual(qa["input_rows"], 4)
        self.assertEqual(qa["source_to_artist_audit"]["status"], "pass")
        self.assertEqual(qa["mark_geometry"]["status"], "pass")
        settings = json.loads((out / "settings.json").read_text())
        self.assertEqual(settings["mark_policy"]["geometric_fill_area_pt2"], 20)
        self.assertEqual(settings["typography"]["legend"], 8)
        for label in spec["labels"].values():
            self.assertIn(label, (out / "panel.svg").read_text())

    def test_scatter_category_and_size_search_all_sides_without_rescaling(self):
        body = "dose,response,treatment,cells\n1,2,Preparation A,0\n2,3,Preparation B,1\n3,5,Preparation A,2\n4,4,Preparation B,4\n"
        spec = {"chart": "scatter", "fields": {"x": "dose", "y": "response",
                "group": "treatment", "size": "cells"},
                "layout": {**self.layout, "width_mm": 120, "height_mm": 100},
                "options": {"size_max": 4, "max_area_pt2": 64}, "formats": ["png", "svg"]}
        qa, settings, out = self.run_panel(body, spec)
        self.assert_largest_feasible_candidate(qa["auto_layout"])
        self.assertFalse(qa["legend_layout"]["combined"]["has_envelope_overlap"])
        table = pd.read_csv(out / "plotting-data.csv")
        self.assertEqual(table["_easyviz_area_pt2"].tolist(), [0., 16., 32., 64.])
        size = next(g for g in qa["legend_layout"]["legends"] if g["kind"] == "size")
        self.assertEqual(size["marker_areas_pt2"], [16., 32., 64.])
        self.assertEqual(settings["typography"]["legend"], 8)
        self.assertEqual(qa["input_rows"], 4)

    def test_mixed_explicit_colorbar_and_auto_guides_preserve_declared_settings(self):
        body = "cohort,readout,cells,score\nA,Signal recovery after dilution,0,0\nB,Signal recovery after dilution,1,1\nA,Preparation yield,2,2\n"
        explicit = {"position": "right", "orientation": "vertical", "length_mm": 24,
                    "ticks": [0, 2, 4]}
        spec = {"chart": "dotplot", "fields": {"x": "cohort", "y": "readout",
                "size": "cells", "color": "score"},
                "layout": {**self.layout, "width_mm": 140, "height_mm": 100},
                "options": {"size_max": 4, "max_area_pt2": 64, "color_limits": [0, 4]},
                "legends": {"colorbar": explicit, "size": {"ncol": 3}}, "formats": ["svg", "png"]}
        qa, _, _ = self.run_panel(body, spec)
        self.assert_largest_feasible_candidate(qa["auto_layout"])
        self.assertEqual([g["kind"] for g in qa["legend_layout"]["legends"]], ["colorbar", "size", "categorical"])
        colorbar = qa["legend_layout"]["legends"][0]
        for key, value in explicit.items():
            self.assertEqual(colorbar["chosen_settings"][key], value)
        self.assertEqual(colorbar["mapped_range"], [0., 4.])
        self.assertEqual(qa["legend_layout"]["legends"][1]["chosen_settings"]["ncol"], 3)
        self.assertFalse(qa["legend_layout"]["combined"]["has_envelope_overlap"])
        self.assertTrue(any(not a["issues"] for a in qa["auto_layout"]["attempts"][1:]))

    def test_all_explicit_guides_do_not_claim_automatic_side(self):
        spec = {"chart": "scatter", "fields": {"x": "x", "y": "y", "group": "g"},
                "layout": self.layout, "legends": {"categorical": {"position": "top"}},
                "formats": ["png"]}
        qa, _, _ = self.run_panel("x,y,g\n1,2,A\n2,3,B\n", spec)
        self.assertEqual(len(qa["auto_layout"]["attempts"]), 1)
        self.assertIsNone(qa["auto_layout"]["attempts"][0]["automatic_guide_side"])
        self.assertEqual(qa["legend_layout"]["legends"][0]["chosen_settings"]["position"], "top")

    def test_large_size_keys_are_aligned_before_stacking_next_guide(self):
        # Packing a freshly recreated size legend before its optical alignment
        # used a stale envelope, creating an unreserved gap and clipping the
        # following category guide despite ample remaining data space.
        for side in ("top", "bottom"):
            with self.subTest(side=side):
                fig = renderer.plt.figure(figsize=(180 / 25.4, 180 / 25.4), dpi=100)
                ax = fig.add_axes([.15, .15, .7, .7])
                ax.set_axis_off()
                manager = renderer.legend_layout.LegendLayout(fig, ax, {"legend": 8}, {
                    "size": {"position": side, "ncol": 3},
                    "categorical": {"position": side, "ncol": 2}})
                manager.add_size([1, 2, 3], [300, 600, 1200], title="Very large areas",
                                 area_semantics="geometric_circle_area")
                manager.add_categorical(["A", "B"], ["#0072B2", "#D55E00"])
                fitted = renderer.auto_layout.fit(fig, ax, manager, renderer.check_tick_label_overlap)
                self.assertEqual(fitted["status"], "pass")
                self.assertEqual(manager.validate()["status"], "pass")
                self.assertFalse(manager.report["combined"]["has_envelope_overlap"])
                for key, area in zip(manager.entries[0]["artist"].legend_handles, [300, 600, 1200]):
                    self.assertAlmostEqual(collection_fill_areas_pt2(key, fig)[0] / area, 1., delta=1e-6)
                self.assertGreater(fitted["data_region_mm"][3], 130)

    def test_multiple_colorbars_stack_complete_envelopes_and_leave_no_trial_axes(self):
        for side in ("top", "bottom"):
            with self.subTest(side=side):
                fig = renderer.plt.figure(figsize=(160 / 25.4, 140 / 25.4), dpi=100)
                ax = fig.add_axes([.15, .15, .7, .7])
                ax.set_axis_off()
                manager = renderer.legend_layout.LegendLayout(fig, ax, {"legend": 8}, {
                    "colorbar": {"position": side, "length_mm": 24,
                                 "orientation": "horizontal", "ticks": [0, .5, 1]}})
                for label in ("Prepared score A", "Prepared score B"):
                    mappable = renderer.matplotlib.cm.ScalarMappable(
                        norm=renderer.mcolors.Normalize(0, 1), cmap="viridis")
                    manager.add_colorbar(mappable, label)
                fitted = renderer.auto_layout.fit(fig, ax, manager, renderer.check_tick_label_overlap)
                self.assertEqual(fitted["status"], "pass")
                report = manager.validate()
                self.assertEqual(report["status"], "pass")
                self.assertFalse(report["combined"]["has_envelope_overlap"])
                self.assertEqual(len(fig.axes), 3, "Removed candidate colorbar axes must not survive")
                for guide in report["legends"]:
                    self.assertEqual(guide["mapped_range"], [0., 1.])
                    self.assertEqual(guide["chosen_settings"]["ticks"], [0., .5, 1.])
                    self.assertAlmostEqual(guide["chosen_settings"]["length_mm"], 24)
                    self.assertEqual(guide["chosen_settings"]["font_size_pt"], 8)
                out = self.root / f"two-colorbars-{side}"
                out.mkdir()
                renderer.export(fig, out, {"formats": ["png", "svg"]}, {
                    "width_mm": 160, "height_mm": 140, "dpi": 100})
                svg = (out / "panel.svg").read_text()
                self.assertIn("Prepared score A", svg)
                self.assertIn("Prepared score B", svg)
                with Image.open(out / "panel.png") as image:
                    self.assertEqual(image.size, (round(160 / 25.4 * 100), round(140 / 25.4 * 100)))

    def test_conflicting_margin_and_manual_guide_are_rejected(self):
        base = {"chart": "scatter", "fields": {"x": "x", "y": "y", "group": "g"},
                "layout": self.layout, "formats": ["png"]}
        source = self.root / "input.csv"
        source.write_text("x,y,g\n1,2,A\n2,3,B\n")
        bad = deepcopy(base)
        bad["layout"]["margins"] = {"left": .2}
        with self.assertRaisesRegex(renderer.SpecError, "conflicting"):
            renderer.render(source, bad, self.root / "bad-margin")
        bad = deepcopy(base)
        bad["legends"] = {"categorical": {"position": "manual", "anchor_mm": [60, 60]}}
        with self.assertRaisesRegex(renderer.SpecError, "manual"):
            renderer.render(source, bad, self.root / "bad-guide")

    def test_impossible_labels_keep_failure_and_input_rows(self):
        long_label = "An extremely long experimental category " * 8
        body = f"g,v\n{long_label},1\n{long_label},2\n"
        spec = {"chart": "distribution", "fields": {"group": "g", "value": "v"},
                "options": {"orientation": "horizontal"}, "layout": self.layout, "formats": ["png"]}
        source = self.root / "input.csv"
        source.write_text(body)
        out = self.root / "impossible"
        with self.assertRaises(renderer.SpecError):
            renderer.render(source, spec, out)
        qa = json.loads((out / "qa.json").read_text())
        self.assertFalse(qa["valid_outputs"])
        self.assertEqual(qa["input_rows"], 2)
        self.assertEqual(qa["auto_layout"]["status"], "needs_revision")

    def test_dense_heatmap_cell_annotations_cannot_pass(self):
        body = "r,c,v\n" + "".join(f"R{i},C{j},{100 + i + j}\n" for i in range(12) for j in range(14))
        spec = {"chart": "heatmap", "fields": {"row": "r", "column": "c", "value": "v"},
                "layout": self.layout, "options": {"annotate_values": True, "value_format": ".0f"},
                "formats": ["png"]}
        source = self.root / "input.csv"
        source.write_text(body)
        out = self.root / "dense"
        with self.assertRaisesRegex(renderer.SpecError, "cell annotation"):
            renderer.render(source, spec, out)
        qa = json.loads((out / "qa.json").read_text())
        self.assertEqual(qa["cell_annotations"]["status"], "needs_revision")
        self.assertEqual(qa["input_rows"], 168)

    def test_annotation_fit_participates_in_guide_selection(self):
        body = "r,c,v\n" + "".join(f"R{i},C{j},{100 + i + j}\n" for i in range(4) for j in range(12))
        spec = {"chart": "heatmap", "fields": {"row": "r", "column": "c", "value": "v"},
                "layout": {**self.layout, "height_mm": 50},
                "options": {"annotate_values": True, "value_format": ".0f"}, "formats": ["png"]}
        qa, settings, _ = self.run_panel(body, spec)
        self.assertEqual(qa["cell_annotations"]["status"], "pass")
        guide = settings["legend_layout"]["legends"][0]
        self.assertIn(guide["chosen_settings"]["position"], ("bottom", "top"))
        self.assertEqual(qa["input_rows"], 48)
        self.assertEqual(settings["typography"]["annotation"], 8)


if __name__ == "__main__":
    unittest.main()
