"""Guard real grouped-bar gaps, source quantities, and visible stroke separation."""
from copy import deepcopy
import csv
import importlib.util
import json
from pathlib import Path
from statistics import mean, stdev
import tempfile
import unittest

import numpy as np
from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/replicate_plot.py"
loader = importlib.util.spec_from_file_location("easyviz_grouped_spacing_tests", SCRIPT)
replicate = importlib.util.module_from_spec(loader)
loader.loader.exec_module(replicate)


class GroupedSpacingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="easyviz-grouped-spacing-")
        self.root = Path(self.temporary.name)

    def tearDown(self):
        replicate.plt.close("all")
        self.temporary.cleanup()

    def source_and_spec(self, component_count=2):
        components = ["X", "Y", "Z"][:component_count]
        supplied = {"X": [0, 3, 6], "Y": [1, 5, 9], "Z": [2, 4, 12]}
        path = self.root / f"source-{component_count}.csv"
        with path.open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["arm", "unit", "part", "amount", "source_note"])
            for arm in ("A", "B"):
                for unit_index, unit in enumerate(("001", "002", "003")):
                    for part_index, part in enumerate(components):
                        value = supplied[part][unit_index] + (part_index + 1 if arm == "B" else 0)
                        writer.writerow([arm, unit, part, value, "retained source field"])
        colors = {"X": "#55A0FB", "Y": "#FF8080", "Z": "#35CBA6"}
        spec = {
            "chart": "replicate",
            "fields": {"condition": "arm", "unit": "unit", "component": "part", "value": "amount"},
            "order": {"condition": ["A", "B"], "component": components},
            "colors": {part: colors[part] for part in components},
            "options": {"mode": "grouped", "bar_width": .64, "uncertainty": "sample_sd"},
            "layout": {"width_mm": 100, "height_mm": 80, "font": "DejaVu Sans", "font_size_pt": 8,
                       "dpi": 100, "auto_fit": True},
            "formats": ["png"],
            "labels": {"y": "Supplied amount"},
        }
        return path, spec

    def draw(self, source, spec):
        resolved = deepcopy(spec)
        data = replicate.prepare(source, resolved)
        layout, typography, rc = replicate.core.setup(resolved)
        with replicate.plt.rc_context(rc):
            fig, _ = replicate.draw(data, resolved, layout, typography)
            fig.canvas.draw()
        return fig

    @staticmethod
    def data_bounds(axis, patch):
        # Inspect the artist's actual transformed path, not its saved summary dict.
        display = patch.get_transform().transform(patch.get_path().vertices)
        values = axis.transData.inverted().transform(display)
        return np.min(values, axis=0), np.max(values, axis=0)

    @staticmethod
    def painted_gaps_pt(fig, bars):
        ordered = sorted((record["artist"] for record in bars), key=lambda patch: patch.get_x())
        gaps = []
        for left, right in zip(ordered, ordered[1:]):
            a = left.get_path().get_extents(left.get_transform())
            b = right.get_path().get_extents(right.get_transform())
            # Both outlines extend half their physical width beyond their paths.
            gaps.append((b.x0 - a.x1) * 72 / fig.dpi
                        - (left.get_linewidth() + right.get_linewidth()) / 2)
        return gaps

    def check_source_and_geometry(self, component_count):
        source, spec = self.source_and_spec(component_count)
        source_bytes = source.read_bytes()
        spec["options"].update(component_gap=.07, bar_style="outline", bar_edge_width_pt=.65)
        fig = self.draw(source, spec)
        axis = fig.axes[0]
        artists = fig._easyviz_replicate_artists
        with source.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(artists["bars"]), 2 * component_count)
        self.assertEqual(len(artists["points"]), len(rows))
        self.assertEqual(len(artists["intervals"]), 2 * component_count)
        bars_by_key = {(record["condition"], record["component"]): record for record in artists["bars"]}
        intervals_by_key = {(record["condition"], record["component"]): record for record in artists["intervals"]}
        for arm_index, arm in enumerate(("A", "B")):
            records = [record for record in artists["bars"] if record["condition"] == arm]
            bounds = [self.data_bounds(axis, record["artist"]) for record in records]
            self.assertAlmostEqual(min(low[0] for low, _ in bounds), arm_index - .32)
            self.assertAlmostEqual(max(high[0] for _, high in bounds), arm_index + .32)
            actual_widths = [high[0] - low[0] for low, high in bounds]
            for actual_width in actual_widths:
                self.assertAlmostEqual(actual_width, actual_widths[0])
            ordered = sorted(bounds, key=lambda pair: pair[0][0])
            for left, right in zip(ordered, ordered[1:]):
                self.assertAlmostEqual(right[0][0] - left[1][0], .07)
            self.assertTrue(all(value > 0 for value in self.painted_gaps_pt(fig, records)))
            for part in spec["order"]["component"]:
                values = [float(row["amount"]) for row in rows if row["arm"] == arm and row["part"] == part]
                bar = bars_by_key[(arm, part)]["artist"]
                lower, upper = self.data_bounds(axis, bar)
                self.assertAlmostEqual(lower[1], 0)
                self.assertAlmostEqual(upper[1], mean(values))
                interval = intervals_by_key[(arm, part)]["artist"]
                endpoints = interval.get_segments()[0]
                self.assertTrue(np.allclose(endpoints[:, 0], (lower[0] + upper[0]) / 2, rtol=0, atol=1e-12))
                self.assertAlmostEqual(endpoints[:, 1].min(), mean(values) - stdev(values))
                self.assertAlmostEqual(endpoints[:, 1].max(), mean(values) + stdev(values))
        seen_rows = set()
        for record in artists["points"]:
            self.assertEqual(len(record["source_rows"]), 1)
            source_row = record["source_rows"][0]
            self.assertNotIn(source_row, seen_rows)
            seen_rows.add(source_row)
            raw = rows[source_row - 1]
            point = record["artist"]
            coordinates = np.asarray(point.get_offsets(), dtype=float)[0]
            self.assertAlmostEqual(coordinates[1], float(raw["amount"]))
            bar = bars_by_key[(raw["arm"], raw["part"])]["artist"]
            lower, upper = self.data_bounds(axis, bar)
            self.assertGreater(coordinates[0], lower[0])
            self.assertLess(coordinates[0], upper[0])
            display_center = point.get_offset_transform().transform(point.get_offsets())[0]
            radius_px = float(np.sqrt(point.get_sizes()[0])) * fig.dpi / 144
            bar_display = bar.get_path().get_extents(bar.get_transform())
            self.assertGreater(display_center[0] - radius_px, bar_display.x0)
            self.assertLess(display_center[0] + radius_px, bar_display.x1)
            self.assertEqual(record["unit"], raw["unit"])
        self.assertEqual(seen_rows, set(range(1, len(rows) + 1)))
        self.assertEqual(replicate.audit_source_artists(source, spec, fig)["status"], "pass")
        self.assertEqual(source.read_bytes(), source_bytes)

    def test_two_components_keep_source_values_sd_all_points_and_whole_group_span(self):
        self.check_source_and_geometry(2)

    def test_three_components_keep_source_values_sd_all_points_and_whole_group_span(self):
        self.check_source_and_geometry(3)

    def test_omitted_and_explicit_zero_gap_are_pixel_identical(self):
        for count in (2, 3):
            for style in ("filled", "outline"):
                with self.subTest(components=count, style=style):
                    source, omitted = self.source_and_spec(count)
                    omitted["options"]["bar_style"] = style
                    zero = deepcopy(omitted)
                    zero["options"]["component_gap"] = 0
                    before = self.root / f"omitted-{count}-{style}"
                    after = self.root / f"zero-{count}-{style}"
                    self.assertEqual(replicate.render(source, omitted, before)["status"], "pass")
                    self.assertEqual(replicate.render(source, zero, after)["status"], "pass")
                    with Image.open(before / "panel.png") as a, Image.open(after / "panel.png") as b:
                        self.assertTrue(np.array_equal(np.asarray(a), np.asarray(b)),
                                        "Explicit zero must preserve the actual old rendering")

    def test_gap_requires_finite_nonnegative_json_number(self):
        _, spec = self.source_and_spec()
        for value in (-.01, float("nan"), float("inf"), -float("inf"), True, False, "0.1", None, []):
            with self.subTest(value=value):
                invalid = deepcopy(spec)
                invalid["options"]["component_gap"] = value
                with self.assertRaises(replicate.SpecError):
                    replicate.validate_spec(invalid)

    def test_gap_is_rejected_for_summary_and_stacked_even_when_zero(self):
        _, spec = self.source_and_spec()
        for mode in ("summary", "stacked"):
            for value in (0, .05):
                with self.subTest(mode=mode, gap=value):
                    invalid = deepcopy(spec)
                    invalid["options"].update(mode=mode, component_gap=value)
                    if mode == "summary":
                        invalid["fields"].pop("component")
                        invalid["order"].pop("component")
                        invalid.pop("colors")
                    with self.assertRaises(replicate.SpecError):
                        replicate.validate_spec(invalid)

    def test_feasible_gap_depends_on_actual_component_count(self):
        two_source, two = self.source_and_spec(2)
        two["options"]["component_gap"] = .35
        self.assertEqual(len(replicate.prepare(two_source, two)), 12)
        three_source, three = self.source_and_spec(3)
        three["options"]["component_gap"] = .35
        unchanged = three_source.read_bytes()
        with self.assertRaises(replicate.SpecError):
            replicate.prepare(three_source, three)
        self.assertEqual(three_source.read_bytes(), unchanged)

    def test_gap_consuming_or_exceeding_whole_group_is_rejected_before_export(self):
        for count, gap in ((2, .64), (2, .7), (3, .32), (3, .4)):
            with self.subTest(components=count, gap=gap):
                source, spec = self.source_and_spec(count)
                spec["options"]["component_gap"] = gap
                output = self.root / f"invalid-{count}-{gap}"
                with self.assertRaises(replicate.SpecError):
                    replicate.render(source, spec, output)
                qa = json.loads((output / "qa.json").read_text())
                self.assertFalse(qa["valid_outputs"])
                self.assertFalse((output / "panel.png").exists())

    def test_tiny_positive_gap_with_touching_outline_ink_fails_actual_export_qa(self):
        source, spec = self.source_and_spec(3)
        spec["options"].update(component_gap=.000001, bar_style="outline", bar_edge_width_pt=1)
        fig = self.draw(source, spec)
        for arm in ("A", "B"):
            records = [record for record in fig._easyviz_replicate_artists["bars"] if record["condition"] == arm]
            self.assertTrue(all(gap < 0 for gap in self.painted_gaps_pt(fig, records)),
                            "Actual transformed outlines still overlap despite a positive numeric gap")
        output = self.root / "touching-outlines"
        with self.assertRaises(replicate.SpecError):
            replicate.render(source, spec, output)
        qa = json.loads((output / "qa.json").read_text())
        self.assertEqual(qa["status"], "needs_revision")
        self.assertFalse(qa["valid_outputs"])
        self.assertEqual(qa["mark_geometry"]["grouped_separation"]["status"], "needs_revision")
        self.assertTrue((output / "panel.png").exists(), "A failed actual visual geometry check retains its export for inspection")

    def test_visible_outline_gap_passes_and_reports_physical_geometry(self):
        source, spec = self.source_and_spec(3)
        spec["options"].update(component_gap=.07, bar_style="outline", bar_edge_width_pt=.65)
        fig = self.draw(source, spec)
        for arm in ("A", "B"):
            records = [record for record in fig._easyviz_replicate_artists["bars"] if record["condition"] == arm]
            self.assertTrue(all(gap > 0 for gap in self.painted_gaps_pt(fig, records)))
        qa = replicate.render(source, spec, self.root / "separate-outlines")
        self.assertEqual(qa["status"], "pass")
        separation = qa["mark_geometry"]["grouped_separation"]
        self.assertEqual(separation["status"], "pass")
        self.assertEqual(len(separation["clearances"]), 4)
        for arm in ("A", "B"):
            bars = [record for record in fig._easyviz_replicate_artists["bars"] if record["condition"] == arm]
            actual = self.painted_gaps_pt(fig, bars)
            reported = [item["stroke_clearance_pt"] for item in separation["clearances"] if item["condition"] == arm]
            self.assertTrue(np.allclose(actual, reported, rtol=0, atol=1e-9))
        self.assertEqual(qa["source_to_artist_audit"]["status"], "pass")
        self.assertEqual(qa["input_rows"], 18)


if __name__ == "__main__":
    unittest.main()
