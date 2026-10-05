"""A novice entry point must preserve explicit semantics and renderer checks."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd


SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/draft_spec.py"
loader = importlib.util.spec_from_file_location("easyviz_draft_spec", SCRIPT)
draft_spec = importlib.util.module_from_spec(loader)
loader.loader.exec_module(draft_spec)
renderer = draft_spec.renderer


class DraftSpecTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-draft-")
        self.root = Path(self.temp.name)
        self.source = self.csv("source.csv", "x,y\n1,2\n2,3\n3,5\n")

    def tearDown(self):
        renderer.plt.close("all")
        self.temp.cleanup()

    def csv(self, name, content):
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def cli(self, arguments, *, script=SCRIPT):
        return subprocess.run([sys.executable, str(script), *map(str, arguments)],
                              cwd=self.root, capture_output=True, text=True)

    def test_drafts_render_all_families_and_preserve_source_rows(self):
        cases = [
            ("scatter", "x,y\n1,2\n2,3\n3,5\n", ["x=x", "y=y"], {}),
            ("heatmap", "r,c,v\nA,X,1\nA,Y,2\nB,X,3\nB,Y,4\n", ["row=r", "column=c", "value=v"], {}),
            ("composition", "s,c,v,total\nS1,A,2,10\nS1,B,3,10\nS2,A,4,20\nS2,B,6,20\n", ["sample=s", "category=c", "value=v", "denominator=total"], {"normalization": "denominator"}),
            ("dotplot", "x,y,s,c,state\nX,A,0,-1,observed\nY,A,0.5,0,observed\nX,B,1,1,observed\nY,B,,,unmeasured\n", ["x=x", "y=y", "size=s", "color=c", "state=state"], {}),
            ("distribution", "g,v,id\nA,1,a1\nA,2,a2\nA,3,a3\nB,2,b1\nB,4,b2\nB,6,b3\n", ["group=g", "value=v", "unit=id"], {}),
        ]
        for chart, content, fields, arguments in cases:
            with self.subTest(chart=chart):
                source = self.csv(f"{chart}.csv", content)
                original = source.read_bytes()
                path = self.root / f"{chart}.json"
                spec = draft_spec.draft(source, chart, fields, path, font="DejaVu Sans", **arguments)
                self.assertEqual(spec, json.loads(path.read_text()))
                self.assertTrue(spec["layout"]["auto_fit"])
                self.assertGreater(spec["line_roles"]["data"]["line_width_pt"], spec["line_roles"]["axis"]["line_width_pt"])
                self.assertLess(spec["line_roles"]["grid"]["line_width_pt"], spec["line_roles"]["reference"]["line_width_pt"])
                self.assertNotIn("statistics", spec)
                self.assertNotIn("labels", spec)
                self.assertNotIn("missing_cells", spec.get("options", {}))
                output = self.root / f"render-{chart}"
                qa = renderer.render(source, spec, output, spec_path=path)
                self.assertEqual(qa["status"], "pass")
                self.assertEqual(json.loads((output / "stats.json").read_text())["method"], "none")
                plotted = pd.read_csv(output / "plotting-data.csv", keep_default_na=False)
                expected = pd.read_csv(source, keep_default_na=False)
                self.assertEqual(len(plotted), len(expected))
                self.assertEqual(list(plotted.columns[:len(expected.columns)]), list(expected.columns))
                numeric_roles = {"scatter": ("x", "y"), "heatmap": ("value",),
                                 "composition": ("value", "denominator"),
                                 "dotplot": ("size", "color"), "distribution": ("value",)}[chart]
                numeric_columns = {spec["fields"][role] for role in numeric_roles if role in spec["fields"]}
                for column in expected:
                    if column in numeric_columns:
                        pd.testing.assert_series_equal(pd.to_numeric(plotted[column]).astype(float),
                                                       pd.to_numeric(expected[column]).astype(float))
                    else:
                        self.assertEqual(plotted[column].astype(str).tolist(), expected[column].astype(str).tolist())
                self.assertEqual(source.read_bytes(), original)
                if chart == "composition":
                    self.assertEqual(plotted.groupby("s")["_easyviz_plotted_value"].sum().tolist(), [.5, .5])
                elif chart == "dotplot":
                    self.assertEqual(qa["dot_states"]["zero_rows"], 1)
                    self.assertEqual(qa["dot_states"]["unmeasured_rows"], 1)
                    self.assertEqual(float(plotted.loc[0, "_easyviz_area_pt2"]), 0)

    def test_named_chinese_columns_and_equals_are_exact_mappings(self):
        source = self.csv("中文 数据.csv", "测量 X,响应=Y,样本编号\n1,2,S1\n2,4,S2\n3,5,S3\n")
        path = self.root / "子目录" / "绘图.json"
        spec = draft_spec.draft(source, "scatter", ["x=测量 X", "y=响应=Y", "unit=样本编号"], path, font="DejaVu Sans")
        self.assertEqual(spec["fields"], {"x": "测量 X", "y": "响应=Y", "unit": "样本编号"})
        self.assertIn("测量 X", path.read_text(encoding="utf-8"))
        qa = renderer.render(source, spec, self.root / "chinese-output", spec_path=path)
        self.assertEqual(qa["status"], "pass")

    def test_explicit_panel_size_survives_rendering(self):
        path = self.root / "fixed-size.json"
        spec = draft_spec.draft(self.source, "scatter", ["x=x", "y=y"], path,
                                panel_size_mm=(120, 80), font="DejaVu Sans")
        qa = renderer.render(self.source, spec, self.root / "fixed-output", spec_path=path)
        self.assertEqual((qa["width_mm"], qa["height_mm"]), (120, 80))
        self.assertEqual(json.loads((self.root / "fixed-output/settings.json").read_text())["typography"]["tick"], 8)

    def test_invalid_semantic_mappings_do_not_write_drafts(self):
        cases = [
            ("scatter", ["x=x"], {}, "requires fields"),
            ("scatter", ["x=x", "y=missing"], {}, "Missing input column"),
            ("scatter", ["x=x", "y=y", "color=x"], {}, "Unknown fields"),
            ("scatter", ["x=x", "x=y", "y=y"], {}, "Duplicate --field"),
            ("scatter", ["x", "y=y"], {}, "role=column"),
            ("scatter", ["=x", "y=y"], {}, "nonempty"),
            ("scatter", ["x=", "y=y"], {}, "nonempty"),
            ("scatter", ["x=x", "y=y"], {"normalization": "none"}, "only supported for composition"),
            ("scatter", ["x=x", "y=y"], {"panel_size_mm": (True, 80)}, "finite JSON number"),
            ("scatter", ["x=x", "y=y"], {"panel_size_mm": (120, float("nan"))}, "finite JSON number"),
            ("scatter", ["x=x", "y=y"], {"font": 8}, "nonempty string"),
            ("composition", ["sample=x", "category=y", "value=x"], {}, "requires --normalization"),
            ("composition", ["sample=x", "category=y", "value=x"], {"normalization": "denominator"}, "requires fields.denominator"),
        ]
        for index, (chart, fields, options, message) in enumerate(cases):
            with self.subTest(index=index):
                path = self.root / f"invalid-{index}.json"
                with self.assertRaisesRegex(renderer.SpecError, message):
                    draft_spec.draft(self.source, chart, fields, path, **options)
                self.assertFalse(path.exists())

    def test_invalid_data_remains_rejected_without_output(self):
        for index, (chart, content, fields) in enumerate([
            ("scatter", "x,y\n1,hello\n", ["x=x", "y=y"]),
            ("heatmap", "r,c,v\nA,X,1\nA,X,2\n", ["row=r", "column=c", "value=v"]),
            ("heatmap", "r,c,v\nA,X,1\nA,Y,2\nB,X,3\n", ["row=r", "column=c", "value=v"]),
            ("dotplot", "x,y,s,c\nA,X,,1\n", ["x=x", "y=y", "size=s", "color=c"]),
        ]):
            with self.subTest(index=index):
                source = self.csv(f"bad-{index}.csv", content)
                path = self.root / f"bad-{index}.json"
                with self.assertRaises(renderer.SpecError):
                    draft_spec.draft(source, chart, fields, path)
                self.assertFalse(path.exists())

    def test_existing_source_spec_and_symlink_are_never_overwritten(self):
        existing = self.root / "existing.json"
        existing.write_text("already accepted")
        symlink = self.root / "dangling.json"
        symlink.symlink_to(self.root / "absent.json")
        original = self.source.read_bytes()
        for path in (self.source, existing, symlink):
            with self.subTest(path=path):
                with self.assertRaises(renderer.SpecError):
                    draft_spec.draft(self.source, "scatter", ["x=x", "y=y"], path)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(existing.read_text(), "already accepted")
        self.assertTrue(symlink.is_symlink())

    def test_destination_race_retains_new_destination_and_cleans_temporary_file(self):
        path = self.root / "race.json"
        real_link = draft_spec.os.link

        def create_then_link(temporary, destination):
            Path(destination).write_text("another writer")
            real_link(temporary, destination)

        with patch.object(draft_spec.os, "link", side_effect=create_then_link):
            with self.assertRaisesRegex(renderer.SpecError, "Output already exists"):
                draft_spec.draft(self.source, "scatter", ["x=x", "y=y"], path)
        self.assertEqual(path.read_text(), "another writer")
        self.assertEqual(list(self.root.glob(".race.json.*.tmp")), [])

    def profile(self):
        path = self.root / "figure-profile.json"
        path.write_text(json.dumps({"version": 1, "layout": {"font": "DejaVu Sans", "font_size_pt": 9,
                                                               "line_width_pt": .7, "dpi": 120},
                                    "panels": {"A": {"width_mm": 120, "height_mm": 80}}}))
        return path

    def test_profile_keeps_reference_dimensions_and_provenance(self):
        profile = self.profile()
        original = profile.read_bytes()
        path = self.root / "nested" / "profile-draft.json"
        spec = draft_spec.draft(self.source, "scatter", ["x=x", "y=y"], path, profile=profile, panel="A")
        self.assertEqual(spec["profile"], str(profile.resolve()))
        self.assertEqual(spec["layout"], {"auto_fit": True})
        self.assertNotIn("line_roles", spec, "A draft using an accepted profile does not replace its stroke policy")
        self.assertNotIn("options", spec, "A shared-profile draft retains accepted fallback observation styling")
        qa = renderer.render(self.source, spec, self.root / "profile-output", spec_path=path)
        self.assertEqual((qa["width_mm"], qa["height_mm"]), (120, 80))
        settings = json.loads((self.root / "profile-output/settings.json").read_text())
        self.assertEqual(settings["typography"]["tick"], 9)
        self.assertEqual(settings["figure_profile"]["path"], str(profile.resolve()))
        self.assertEqual(settings["figure_profile"]["sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(settings["figure_profile"]["source_specification"], spec)
        self.assertEqual(profile.read_bytes(), original)

    def test_new_unprofiled_drafts_use_crisp_observations_without_replacing_mapped_fill_area(self):
        for chart, content, fields, expected in (
            ("scatter", "x,y\n1,2\n2,3\n", ["x=x", "y=y"], {"alpha": 1, "point_style": "filled"}),
            ("scatter", "x,y,s\n1,2,0\n2,3,100\n", ["x=x", "y=y", "size=s"], {"alpha": 1, "point_style": "filled"}),
            ("distribution", "g,v\nA,1\nA,2\nB,3\nB,4\n", ["group=g", "value=v"],
             {"alpha": 1, "point_style": "filled", "box_style": "outline", "box_width": .18}),
        ):
            with self.subTest(chart=chart, fields=fields):
                number = len(list(self.root.glob("crisp-*.json")))
                source = self.csv(f"crisp-{number}.csv", content)
                spec = draft_spec.draft(source, chart, fields, self.root / f"crisp-{number}.json")
                self.assertEqual(spec["options"], expected)
                self.assertEqual(spec["line_roles"]["axis"]["color"], "#222222")
                self.assertEqual(spec["line_roles"]["reference"]["color"], "#747474")

    def test_profile_conflicts_are_rejected_before_writing(self):
        profile = self.profile()
        for index, options in enumerate([
            {"profile": profile}, {"panel": "A"}, {"profile": profile, "panel": "missing"},
            {"profile": profile, "panel": "A", "panel_size_mm": (120, 80)},
            {"profile": profile, "panel": "A", "font": "Arial"},
        ]):
            with self.subTest(index=index):
                path = self.root / f"profile-invalid-{index}.json"
                with self.assertRaises(renderer.SpecError):
                    draft_spec.draft(self.source, "scatter", ["x=x", "y=y"], path, **options)
                self.assertFalse(path.exists())

    def test_crisp_and_legacy_drafts_draw_expected_box_geometry_without_data_changes(self):
        source = self.csv("box-source.csv", "g,v\nA,1\nA,2\nA,5\nB,3\nB,6\nB,8\n")
        original = source.read_bytes()
        for mode, alpha, width, stroke in (("crisp", 1, .18, .75), ("legacy", .85, .5, .6)):
            with self.subTest(mode=mode):
                spec = draft_spec.draft(source, "distribution", ["group=g", "value=v"],
                                        self.root / f"{mode}-box.json", font="DejaVu Sans", style_mode=mode)
                data = renderer.prepare(source, spec)
                layout, typography, rc = renderer.setup(spec)
                with renderer.plt.rc_context(rc):
                    fig, _ = renderer.draw(data, spec, layout, typography, renderer.statistics(data, spec))
                    self.assertEqual(len(data), 6)
                    self.assertEqual(data["v"].tolist(), [1., 2., 5., 3., 6., 8.])
                    from matplotlib.collections import PathCollection
                    points = [artist for artist in fig.axes[0].collections if isinstance(artist, PathCollection)]
                    self.assertTrue(all(artist.get_alpha() == alpha for artist in points))
                    for box in fig.axes[0].patches:
                        self.assertAlmostEqual(renderer.np.ptp(box.get_path().vertices[:, 0]), width)
                        self.assertEqual(box.get_linewidth(), stroke)
                        self.assertEqual(box.get_facecolor()[3], 0 if mode == "crisp" else .22)
                    renderer.plt.close(fig)
                self.assertEqual(source.read_bytes(), original)

    def test_bad_style_mode_never_writes_a_draft(self):
        path = self.root / "bad-style.json"
        with self.assertRaisesRegex(ValueError, "style_mode"):
            draft_spec.draft(self.source, "scatter", ["x=x", "y=y"], path, style_mode="unsupported")
        self.assertFalse(path.exists())

    def test_cli_is_portable_and_rejects_invalid_arguments(self):
        portable = self.root / "portable"
        shutil.copytree(SCRIPT.parent, portable)
        script = portable / "draft_spec.py"
        path = self.root / "cli.json"
        base = ["--data", self.source, "--chart", "scatter", "--field", "x=x", "--field", "y=y", "--out", path]
        result = self.cli(base, script=script)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "draft")
        self.assertTrue(json.loads(path.read_text())["layout"]["auto_fit"])
        for extra in (["--spec", "other.json"], ["--normalization", "sample_sum"],
                      ["--field", "x=y"], ["--panel-size-mm", "wide", "80"], ["--panel", "A"],
                      ["--style-mode", "soft"]):
            with self.subTest(extra=extra):
                invalid = self.root / "cli-invalid.json"
                arguments = base[:-1] + [invalid] + extra
                result = self.cli(arguments, script=script)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(invalid.exists())


if __name__ == "__main__":
    unittest.main()
