"""Behavioral checks for portable panel rendering and unsafe-data rejection.

Run: .venv/bin/python -m unittest discover -s tests -p test_renderer.py -v
"""
from __future__ import annotations

from copy import deepcopy
import builtins
from decimal import Decimal
import importlib.util
import hashlib
import json
import math
import os
from pathlib import Path
import py_compile
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

SCRIPT = Path(__file__).resolve().parents[1] / "staged-runtime/render.py"
loader = importlib.util.spec_from_file_location("easyviz_render", SCRIPT)
renderer = importlib.util.module_from_spec(loader)
loader.loader.exec_module(renderer)
from PIL import Image
from pypdf import PdfReader
import pandas as pd
from marker_geometry import collection_fill_areas_pt2


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-test-")
        self.root = Path(self.temp.name)
        self.base = {"chart": "scatter", "fields": {"x": "x", "y": "y"}, "layout": {"width_mm": 88, "height_mm": 66, "font": "DejaVu Sans", "dpi": 120}, "labels": {"x": "Input", "y": "Output"}, "formats": ["pdf", "svg", "png", "tiff"], "seed": 29}

    def tearDown(self):
        renderer.plt.close("all")
        self.temp.cleanup()

    def csv(self, text):
        path = self.root / "input.csv"
        path.write_text(text)
        return path

    def test_physical_dimensions_and_metadata_across_sizes_and_formats(self):
        data = self.csv("x,y\n1,1.5\n2,3\n3,2\n4,5\n")
        for width, height in [(88, 66), (132, 88)]:
            with self.subTest(width=width, height=height):
                spec = deepcopy(self.base)
                spec["layout"].update(width_mm=width, height_mm=height)
                output = self.root / str(width)
                qa = renderer.render(data, spec, output)
                self.assertEqual(qa["status"], "pass")
                page = PdfReader(output / "panel.pdf").pages[0]
                self.assertAlmostEqual(float(page.mediabox.width) / 72 * 25.4, width, places=5)
                self.assertAlmostEqual(float(page.mediabox.height) / 72 * 25.4, height, places=5)
                expected_px = (round(width / 25.4 * 120), round(height / 25.4 * 120))
                for suffix in ["png", "tiff"]:
                    with Image.open(output / f"panel.{suffix}") as image:
                        self.assertEqual(image.size, expected_px)
                        self.assertAlmostEqual(float(image.info["dpi"][0]), 120, places=1)
                svg = ET.parse(output / "panel.svg").getroot()
                self.assertAlmostEqual(float(svg.attrib["width"][:-2]) / 72 * 25.4, width, places=4)
                self.assertTrue(svg.findall(".//{http://www.w3.org/2000/svg}text"), "SVG must preserve editable text")
                settings = json.loads((output / "settings.json").read_text())
                self.assertEqual(settings["layout"]["actual_font"], "DejaVu Sans")
                self.assertEqual(settings["typography"]["tick"], 8)
                self.assertEqual(len(settings["renderer"]["sha256"]), 64)
                self.assertIn("scipy", settings["runtime"])
                self.assertEqual(len(pd.read_csv(output / "plotting-data.csv")), 4)

    def test_rejects_bad_numeric_values_and_missing_schema(self):
        for body in ["x,y\n1,NaN\n", "x,y\n1,inf\n", "x,y\n1,hello\n", "x,z\n1,2\n"]:
            with self.subTest(body=body):
                with self.assertRaises(renderer.SpecError):
                    renderer.prepare(self.csv(body), self.base)

    def test_heatmap_rejects_duplicate_and_missing_cells(self):
        spec = {"chart": "heatmap", "fields": {"row": "r", "column": "c", "value": "v"}}
        for body in ["r,c,v\na,x,1\na,x,2\n", "r,c,v\na,x,1\na,y,2\nb,x,3\n"]:
            with self.assertRaises(renderer.SpecError):
                renderer.prepare(self.csv(body), spec)

    def test_composition_denominator_remains_explicit_and_incomplete(self):
        spec = {"chart": "composition", "fields": {"sample": "s", "category": "c", "value": "v", "denominator": "total"}, "options": {"normalization": "denominator"}}
        data = renderer.prepare(self.csv("s,c,v,total\ns1,A,20,100\ns1,B,30,100\ns2,A,2,10\ns2,B,3,10\n"), spec)
        self.assertEqual(list(data["_easyviz_plotted_value"]), [.2, .3, .2, .3])
        self.assertEqual(list(data.groupby("s")["_easyviz_plotted_value"].sum()), [.5, .5])
        for body in ["s,c,v,total\ns,A,-1,10\n", "s,c,v,total\ns,A,6,10\ns,B,6,10\n", "s,c,v,total\ns,A,2,10\ns,B,2,12\n"]:
            with self.assertRaises(renderer.SpecError):
                renderer.prepare(self.csv(body), spec)
        no_normalization = deepcopy(spec)
        no_normalization["options"] = {}
        with self.assertRaises(renderer.SpecError):
            renderer.prepare(self.csv("s,c,v,total\ns,A,2,10\n"), no_normalization)

    def test_csv_structure_is_rejected_before_inferred_index_or_duplicate_mapping(self):
        output = self.root / "strict-csv"
        source = self.csv("x,y\n1,2\n2,3\n3,4\n")
        spec = {**deepcopy(self.base), "formats": ["png"]}
        renderer.render(source, spec, output)
        for body in ("x,y\n1,2,9\n2,4,8\n3,6,7\n", "x,y,y\n1,2,200\n2,3,300\n",
                     "x,\n1,2\n", "x,y\n1,2\n\n2,3\n", "x,y\n,\n",
                     'x,y\n1,"2\n'):
            with self.subTest(body=body):
                source.write_text(body)
                with self.assertRaises(renderer.SpecError):
                    renderer.render(source, spec, output)
                qa = json.loads((output / "qa.json").read_text())
                self.assertEqual(qa["status"], "failed")
                self.assertFalse(qa["valid_outputs"])

    def test_quoted_bom_csv_preserves_literal_ids_and_consumed_byte_snapshot(self):
        source = self.root / "quoted.csv"
        raw = '\ufeffid,x,y,note\n0001,1.00,2e0,"a,b"\n0002,2.0,3.00,"two\nlines"\n0003,3,4,"say ""yes"""\n'.encode("utf-8")
        source.write_bytes(raw)
        spec = {**deepcopy(self.base), "fields": {"x": "x", "y": "y", "unit": "id"}, "formats": ["png", "svg"]}
        spec_path = self.root / "spec.json"
        spec_path.write_text(json.dumps(spec))
        prepared = renderer.prepare(source, spec)
        self.assertEqual(prepared.id.tolist(), ["0001", "0002", "0003"])
        self.assertEqual(prepared.note.tolist(), ["a,b", "two\nlines", 'say "yes"'])
        output = self.root / "quoted-output"
        qa = renderer.render(source, spec, output, spec_path=spec_path, track="create")
        self.assertTrue(qa["valid_outputs"])
        self.assertEqual((output / "source-data.csv").read_bytes(), raw)
        self.assertEqual(source.read_bytes(), raw)
        settings = json.loads((output / "settings.json").read_text())
        elements = json.loads((output / "elements.json").read_text())
        digest = hashlib.sha256(raw).hexdigest()
        self.assertEqual(settings["input_sha256"], digest)
        self.assertEqual(settings["source_snapshot"]["sha256"], digest)
        self.assertEqual(elements["version"]["input_sha256"], digest)
        self.assertEqual(qa["source_continuity"]["status"], "pass")
        with Image.open(output / "panel.png") as image:
            image.load()

    def test_change_after_parse_is_rejected_before_export(self):
        source = self.csv("x,y\n1,2\n2,3\n3,4\n")
        actual_reader = renderer.read_source_csv
        def replacement(path):
            data = actual_reader(path)
            source.write_text("x,y\n1,200\n2,300\n3,400\n")
            return data
        output = self.root / "changed-after-parse"
        with patch.object(renderer, "read_source_csv", side_effect=replacement):
            with self.assertRaisesRegex(renderer.SpecError, "changed before rendering"):
                renderer.render(source, deepcopy(self.base), output)
        self.assertFalse((output / "panel.png").exists())
        self.assertFalse(json.loads((output / "qa.json").read_text())["valid_outputs"])

    def test_loaded_helper_and_renderer_replacements_keep_actual_executed_digests(self):
        # Copy the real portable runtime and change its source immediately
        # after a real helper execution; authoritative files stay untouched.
        real_exec = builtins.exec
        for changed_name in ("figure_elements.py", "render.py"):
            with self.subTest(changed_name=changed_name):
                runtime = self.root / changed_name.replace(".", "-")
                shutil.copytree(SCRIPT.parent, runtime)
                helper = runtime / "figure_elements.py"
                helper.write_bytes(helper.read_bytes() + b'\ndef runtime_capture_probe():\n    return "executed-before-replacement"\n')
                target = runtime / changed_name
                consumed = target.read_bytes()
                replacement = consumed + b'\n# Replacement source was never executed.\n'
                replaced = []

                def replace_after_helper_exec(code, globals=None, locals=None, **kwargs):
                    real_exec(code, globals, locals, **kwargs)
                    if isinstance(globals, dict) and globals.get("__file__") == str(helper):
                        target.write_bytes(replacement)
                        replaced.append(changed_name)

                portable_loader = importlib.util.spec_from_file_location("portable_capture_render", runtime / "render.py")
                portable = importlib.util.module_from_spec(portable_loader)
                with patch("builtins.exec", side_effect=replace_after_helper_exec):
                    portable_loader.loader.exec_module(portable)
                self.assertEqual(replaced, [changed_name])
                self.assertEqual(portable.figure_elements.runtime_capture_probe(), "executed-before-replacement")
                expected = hashlib.sha256(consumed).hexdigest()
                self.assertEqual(portable.RUNTIME_SOURCE_DIGESTS[changed_name], expected)
                self.assertNotEqual(expected, hashlib.sha256(target.read_bytes()).hexdigest())
                output = runtime / "output"
                with self.assertRaisesRegex(portable.SpecError, "changed before rendering"):
                    portable.render(self.csv("x,y\n1,2\n2,3\n3,4\n"), deepcopy(self.base), output)
                self.assertFalse(json.loads((output / "qa.json").read_text())["valid_outputs"])
                self.assertFalse((output / "panel.png").exists())

    def test_stale_self_bytecode_cannot_bind_replacement_source_to_old_marker_geometry(self):
        runtime = self.root / "stale-self-runtime"
        shutil.copytree(SCRIPT.parent, runtime, ignore=shutil.ignore_patterns("__pycache__"))
        script = runtime / "render.py"
        original = script.read_bytes()
        replaced = original.replace(b'options.get("point_area_pt2", 12)', b'options.get("point_area_pt2", 81)')
        self.assertNotEqual(original, replaced)
        self.assertEqual(len(original), len(replaced))
        old_stat = script.stat()
        py_compile.compile(str(script), doraise=True)
        script.write_bytes(replaced)
        os.utime(script, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
        cached_loader = importlib.util.spec_from_file_location("portable_stale_render", script)
        portable = importlib.util.module_from_spec(cached_loader)
        with self.assertRaisesRegex(RuntimeError, "Executing renderer code differs"):
            cached_loader.loader.exec_module(portable)
        self.assertFalse(hasattr(portable, "render"), "Refuse the old module before its export API is loaded")
        self.assertEqual(script.read_bytes(), replaced)
        self.assertFalse(list(runtime.glob("panel.*")))

    def test_portable_cli_runs_current_source_with_relative_or_absolute_loader_paths(self):
        runtime = self.root / "portable-cli"
        shutil.copytree(SCRIPT.parent, runtime, ignore=shutil.ignore_patterns("__pycache__"))
        source = runtime / "data.csv"
        source.write_bytes(b"x,y\n1,2\n2,3\n3,4\n")
        spec = {**deepcopy(self.base), "formats": ["png", "svg"]}
        spec_path = runtime / "spec.json"
        spec_path.write_text(json.dumps(spec))
        for relative in (True, False):
            with self.subTest(relative=relative):
                output = runtime / ("relative-output" if relative else "absolute-output")
                command = [sys.executable, "render.py" if relative else str(runtime / "render.py"),
                           "--data", str(source), "--spec", str(spec_path), "--out", str(output)]
                ran = subprocess.run(command, cwd=runtime, capture_output=True, text=True, timeout=30)
                self.assertEqual(ran.returncode, 0, ran.stderr)
                qa = json.loads((output / "qa.json").read_text())
                self.assertTrue(qa["valid_outputs"])
                self.assertEqual(json.loads((output / "settings.json").read_text())["renderer"]["sha256"],
                                 hashlib.sha256((runtime / "render.py").read_bytes()).hexdigest())
                with Image.open(output / "panel.png") as image:
                    image.load()

    def test_source_change_during_export_fails_and_retains_consumed_bindings(self):
        before = b"x,y\n1,2\n2,3\n3,5\n4,4\n"
        source = self.csv(before.decode())
        actual_export = renderer.export
        def replacement(fig, out, spec, layout):
            source.write_text("x,y\n1,200\n2,300\n3,500\n4,400\n")
            return actual_export(fig, out, spec, layout)
        output = self.root / "changed-during-export"
        with patch.object(renderer, "export", side_effect=replacement):
            with self.assertRaisesRegex(renderer.SpecError, "changed during export"):
                renderer.render(source, deepcopy(self.base), output, track="create")
        qa = json.loads((output / "qa.json").read_text())
        self.assertFalse(qa["valid_outputs"])
        self.assertEqual(qa["source_continuity"]["issues"][0]["role"], "data_file")
        self.assertEqual(pd.read_csv(output / "plotting-data.csv").y.tolist(), [2, 3, 5, 4])
        self.assertEqual((output / "source-data.csv").read_bytes(), before)
        expected = hashlib.sha256(before).hexdigest()
        self.assertEqual(json.loads((output / "settings.json").read_text())["input_sha256"], expected)
        self.assertEqual(json.loads((output / "elements.json").read_text())["version"]["input_sha256"], expected)
        self.assertNotEqual(expected, hashlib.sha256(source.read_bytes()).hexdigest())

    def test_spec_and_profile_replacements_cannot_retain_passing_qa(self):
        source = self.csv("x,y\n1,2\n2,3\n3,4\n")
        spec_path, profile_path = self.root / "spec.json", self.root / "profile.json"
        profile = {"version": 1, "layout": {"font": "DejaVu Sans", "font_size_pt": 8, "line_width_pt": .6, "dpi": 120},
                   "panels": {"A": {"width_mm": 88, "height_mm": 66}}}
        spec = {**deepcopy(self.base), "profile": str(profile_path), "panel": "A"}
        actual_export = renderer.export
        for role, target in (("spec_file", spec_path), ("figure_profile", profile_path)):
            with self.subTest(role=role):
                spec_path.write_text(json.dumps(spec))
                profile_path.write_text(json.dumps(profile))
                original = target.read_bytes()
                def replacement(fig, out, supplied, layout):
                    target.write_bytes(original + b"\n")
                    return actual_export(fig, out, supplied, layout)
                output = self.root / role
                with patch.object(renderer, "export", side_effect=replacement):
                    with self.assertRaisesRegex(renderer.SpecError, "changed during export"):
                        renderer.render(source, deepcopy(spec), output, spec_path=spec_path)
                qa = json.loads((output / "qa.json").read_text())
                self.assertFalse(qa["valid_outputs"])
                self.assertEqual(qa["source_continuity"]["issues"][0]["role"], role)
                if role == "spec_file":
                    self.assertEqual(json.loads((output / "elements.json").read_text())["input"]["supplied_spec_sha256"], hashlib.sha256(original).hexdigest())

    def test_virtual_spec_path_keeps_relative_profile_context_without_claiming_file_bytes(self):
        source = self.csv("x,y\n1,2\n2,3\n3,4\n")
        profile = {"version": 1, "layout": {"font": "DejaVu Sans", "font_size_pt": 8, "line_width_pt": .6, "dpi": 120},
                   "panels": {"A": {"width_mm": 88, "height_mm": 66}}}
        (self.root / "profile.json").write_text(json.dumps(profile))
        spec_path = self.root / "not-yet-saved.json"
        spec = {**deepcopy(self.base), "profile": "profile.json", "panel": "A", "formats": ["png", "svg"]}
        output = self.root / "virtual-context"
        qa = renderer.render(source, spec, output, spec_path=spec_path)
        self.assertTrue(qa["valid_outputs"])
        self.assertIsNone(json.loads((output / "elements.json").read_text())["input"]["supplied_spec_sha256"])
        actual_export = renderer.export
        def create_file(fig, out, supplied, layout):
            spec_path.write_text(json.dumps(spec))
            return actual_export(fig, out, supplied, layout)
        with patch.object(renderer, "export", side_effect=create_file):
            with self.assertRaisesRegex(renderer.SpecError, "changed during export"):
                renderer.render(source, spec, output, spec_path=spec_path)
        self.assertFalse(json.loads((output / "qa.json").read_text())["valid_outputs"])
        self.assertIsNone(json.loads((output / "elements.json").read_text())["input"]["supplied_spec_sha256"])

    def test_composition_huge_finite_sources_normalize_without_overflow(self):
        spec = {"chart": "composition", "fields": {"sample": "s", "category": "c", "value": "v"},
                "options": {"normalization": "sample_sum"}, "layout": {**self.base["layout"], "auto_fit": True},
                "formats": ["png", "svg", "pdf"]}
        cases = (("1e308", "1e308", [.5, .5], "2E+308"),
                 ("18000000000000000000", "1000000000000000000", [18 / 19, 1 / 19], "19000000000000000000"))
        for ordinal, (first, second, expected, total) in enumerate(cases):
            with self.subTest(first=first):
                body = f"s,c,v\nA,c1,{first}\nA,c2,{second}\n"
                source = self.csv(body)
                prepared = renderer.prepare(source, spec)
                self.assertEqual([Decimal(value) for value in prepared["_easyviz_denominator_text"]], [Decimal(total), Decimal(total)])
                self.assertTrue(renderer.np.allclose(prepared["_easyviz_plotted_value"], expected, rtol=1e-14, atol=0))
                self.assertAlmostEqual(math.fsum(prepared["_easyviz_plotted_value"]), 1)
                layout, typography, rc = renderer.setup(spec)
                with renderer.plt.rc_context(rc):
                    fig, _ = renderer.draw(prepared, spec, layout, typography, renderer.statistics(prepared, spec))
                    self.assertTrue(renderer.np.allclose([bar.get_height() for bar in fig.axes[0].patches], expected, rtol=1e-14, atol=0))
                    renderer.plt.close(fig)
                output = self.root / f"safe-composition-{ordinal}"
                qa = renderer.render(source, spec, output)
                self.assertTrue(qa["valid_outputs"])
                self.assertEqual((output / "source-data.csv").read_text(), body)
                plotted = pd.read_csv(output / "plotting-data.csv")
                self.assertTrue(renderer.np.allclose(plotted["_easyviz_plotted_value"], expected, rtol=1e-14, atol=0))
                with Image.open(output / "panel.png") as image:
                    image.load()

    def test_explicit_denominator_rejects_true_excess_despite_wrapped_integer_sum(self):
        spec = {"chart": "composition", "fields": {"sample": "s", "category": "c", "value": "v", "denominator": "d"},
                "options": {"normalization": "denominator"}}
        for first, second, denominator in (("18000000000000000000", "1000000000000000000", "18000000000000000000"),
                                            ("1e308", "1e308", "1e308")):
            with self.subTest(first=first):
                source = self.csv(f"s,c,v,d\nA,c1,{first},{denominator}\nA,c2,{second},{denominator}\n")
                with self.assertRaisesRegex(renderer.SpecError, "sum exceeds"):
                    renderer.prepare(source, spec)
        exact = renderer.prepare(self.csv("s,c,v,d\nA,c1,.1,.3\nA,c2,.2,.3\n"), spec)
        self.assertTrue(renderer.np.allclose(exact["_easyviz_plotted_value"], [1 / 3, 2 / 3]))

    def test_nonzero_numeric_underflow_is_explicitly_rejected(self):
        for value in ("1e-400", "-1e-400"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(renderer.SpecError, "representability"):
                    renderer.prepare(self.csv(f"x,y\n1,{value}\n2,3\n"), self.base)
        prepared = renderer.prepare(self.csv("x,y\n1,0e-400\n2,3\n"), self.base)
        self.assertEqual(prepared.y.tolist(), [0, 3])

    def test_zero_with_extreme_exponent_does_not_allocate_a_giant_decimal_sum(self):
        spec = {"chart": "composition", "fields": {"sample": "s", "category": "c", "value": "v"},
                "options": {"normalization": "sample_sum"}}
        actual_context = renderer.localcontext
        class BoundedContext:
            def __init__(self):
                self.context = actual_context()
            def __enter__(self):
                self.value = self.context.__enter__()
                return self
            @property
            def prec(self):
                return self.value.prec
            @prec.setter
            def prec(self, value):
                if value > 10000:
                    raise AssertionError("A zero exponent must not demand huge context precision")
                self.value.prec = value
            def __exit__(self, *args):
                return self.context.__exit__(*args)
        for zero in ("0e-1000000000", "0e1000000000"):
            with self.subTest(zero=zero), patch.object(renderer, "localcontext", side_effect=BoundedContext):
                data = renderer.prepare(self.csv(f"s,c,v\nA,zero,{zero}\nA,one,1\n"), spec)
                self.assertEqual(data["_easyviz_plotted_value"].tolist(), [0, 1])
                self.assertEqual([Decimal(value) for value in data["_easyviz_denominator_text"]], [Decimal(1), Decimal(1)])

    def test_cli_replacement_after_spec_parse_cannot_bind_old_dict_to_new_file(self):
        source = self.csv("x,y\n1,2\n2,3\n3,4\n")
        spec_path = self.root / "spec.json"
        spec_path.write_text(json.dumps(self.base))
        original = spec_path.read_bytes()
        output = self.root / "spec-load-race"
        actual_render = renderer.render
        def replacement(data_path, adopted, out, **kwargs):
            changed = deepcopy(self.base)
            changed["labels"]["y"] = "Changed file label"
            spec_path.write_text(json.dumps(changed))
            self.assertEqual(kwargs["captured_spec_bytes"], original)
            return actual_render(data_path, adopted, out, **kwargs)
        argv = ["render.py", "--data", str(source), "--spec", str(spec_path), "--out", str(output)]
        with patch("sys.argv", argv), patch.object(renderer, "render", side_effect=replacement):
            with self.assertRaises(SystemExit) as raised:
                renderer.main()
        self.assertEqual(raised.exception.code, 2)
        qa = json.loads((output / "qa.json").read_text())
        self.assertFalse(qa["valid_outputs"])
        self.assertIn("changed before rendering", qa["error"])
        self.assertFalse((output / "panel.png").exists())

    def test_supplied_dictionary_must_match_an_existing_spec_file_claim(self):
        source = self.csv("x,y\n1,2\n2,3\n3,4\n")
        spec_path = self.root / "spec.json"
        spec_path.write_text(json.dumps(self.base))
        adopted = deepcopy(self.base)
        adopted["labels"]["y"] = "Adopted in memory"
        output = self.root / "different-spec"
        with self.assertRaisesRegex(renderer.SpecError, "differs from the captured spec file"):
            renderer.render(source, adopted, output, spec_path=spec_path)
        self.assertFalse(json.loads((output / "qa.json").read_text())["valid_outputs"])
        # Omitting the unrelated file claim keeps an in-memory spec valid.
        self.assertTrue(renderer.render(source, adopted, output)["valid_outputs"])

    def test_spec_file_parse_failure_invalidates_old_export_qa(self):
        source = self.csv("x,y\n1,2\n2,3\n3,4\n")
        spec_path = self.root / "spec.json"
        spec_path.write_text(json.dumps(self.base))
        output = self.root / "invalid-spec-rerun"
        renderer.render_spec_file(source, spec_path, output)
        png = (output / "panel.png").read_bytes()
        for raw in (b"{", b'{"chart":"scatter","chart":"heatmap"}', b'{"chart":"scatter","seed":NaN}'):
            with self.subTest(raw=raw):
                spec_path.write_bytes(raw)
                with self.assertRaises(renderer.SpecError):
                    renderer.render_spec_file(source, spec_path, output)
                qa = json.loads((output / "qa.json").read_text())
                self.assertEqual(qa["status"], "failed")
                self.assertFalse(qa["valid_outputs"])
                self.assertEqual((output / "panel.png").read_bytes(), png)

    def test_category_order_and_colors_never_drop_or_cycle(self):
        categories = [f"group {i}" for i in range(9)]
        with self.assertRaises(renderer.SpecError):
            renderer.palette_colors({}, categories)
        with self.assertRaises(renderer.SpecError):
            renderer.palette_colors({"colors": {"a": "#0072B2"}}, ["a", "b"])
        with self.assertRaises(renderer.SpecError):
            renderer.ordered(pd.DataFrame({"g": ["a", "b"]}), "g", {"order": {"group": ["a"]}}, "group")

    def test_line_roles_are_strict_and_invalid_styles_do_not_reach_rendering(self):
        invalid = [None, [], {"unknown": {}}, {"data": {"width": 1}},
                   {"data": {"line_width_pt": True}}, {"summary": {"line_width_pt": 0}},
                   {"grid": {"line_width_pt": -1}}, {"axis": {"line_width_pt": float("nan")}},
                   {"reference": {"line_width_pt": float("inf")}},
                   {"data": {"color": "not a color"}}, {"data": {"color": [1, 0, 0]}},
                   {"reference": {"linestyle": []}}, {"grid": {"linestyle": "dashed"}},
                   {"axis": {"linestyle": "--"}}]
        for roles in invalid:
            with self.subTest(roles=roles), self.assertRaises(renderer.SpecError):
                renderer.prepare(self.csv("x,y\n1,2\n2,4\n3,5\n"), {**self.base, "line_roles": roles})

    def test_scatter_stroke_roles_change_real_artists_without_changing_observations(self):
        source = self.csv("x,y,g\n1,2,A\n2,3,A\n3,5,B\n4,6,B\n")
        original = source.read_bytes()
        spec = deepcopy(self.base)
        spec["fields"]["group"] = "g"
        spec["colors"] = {"A": "#2581B9", "B": "#DF9A3C"}
        spec["options"] = {"regression": True, "grid": True, "reference_lines": {"y": [3, 3]}}
        spec["line_roles"] = {"data": {"line_width_pt": 1.1, "color": "#1B4965"},
                              "reference": {"line_width_pt": .35, "color": "#AAAAAA", "linestyle": ":"},
                              "axis": {"line_width_pt": .5, "color": "#555555"},
                              "grid": {"line_width_pt": .25, "color": "#E8E8E8"}}
        data = renderer.prepare(source, spec)
        result = renderer.statistics(data, spec)
        layout, typography, rc = renderer.setup(spec)
        with renderer.plt.rc_context(rc):
            fig, colors = renderer.draw(data, spec, layout, typography, result)
            fig.canvas.draw()
            ax = fig.axes[0]
            fit = next(entry for entry in fig._easyviz_elements if entry["role"] == "fit-line")
            self.assertEqual(fit["_artist"].get_linewidth(), 1.1)
            self.assertEqual(renderer.mcolors.to_hex(fit["_artist"].get_color()), "#1b4965")
            self.assertEqual(fit["editable"]["linewidth"], "/line_roles/data/line_width_pt")
            refs = [entry["_artist"] for entry in fig._easyviz_elements if entry["role"] == "reference-line"]
            self.assertEqual(len(refs), 2, "Repeated supplied reference positions still render faithfully")
            for line in refs:
                self.assertEqual(line.get_linewidth(), .35)
                self.assertEqual(line.get_linestyle(), ":")
                self.assertEqual(list(line.get_ydata()), [3, 3])
            self.assertEqual(ax.spines["left"].get_linewidth(), .5)
            self.assertEqual(renderer.mcolors.to_hex(ax.spines["left"].get_edgecolor()), "#555555")
            self.assertEqual(ax.xaxis.get_major_ticks()[0].tick1line.get_markeredgewidth(), .5)
            self.assertTrue(all(line.get_linewidth() == .25 for line in ax.get_xgridlines() + ax.get_ygridlines()))
            self.assertTrue(all(line.get_zorder() < 3 for line in ax.get_xgridlines() + ax.get_ygridlines()))
            self.assertEqual(colors, spec["colors"])
            for points, group in zip(ax.collections, ("A", "B")):
                self.assertTrue((points.get_linewidths() == 0).all())
                self.assertEqual(renderer.mcolors.to_hex(points.get_facecolors()[0]), spec["colors"][group].lower())
            renderer.plt.close(fig)
        output = self.root / "stroke-output"
        renderer.render(source, spec, output, track="create")
        pd.testing.assert_frame_equal(pd.read_csv(output / "plotting-data.csv"), pd.read_csv(source))
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(json.loads((output / "stats.json").read_text())["regression"]["slope"], result["regression"]["slope"])

    def test_explicit_regression_color_remains_preferred_over_data_role_color(self):
        spec = {**self.base, "options": {"regression": True, "regression_color": "#AA1144"},
                "line_roles": {"data": {"color": "#112233", "line_width_pt": .9}}}
        data = renderer.prepare(self.csv("x,y\n1,2\n2,4\n3,5\n"), spec)
        layout, typography, rc = renderer.setup(spec)
        with renderer.plt.rc_context(rc):
            fig, _ = renderer.draw(data, spec, layout, typography, {})
            fit = next(entry for entry in fig._easyviz_elements if entry["role"] == "fit-line")
            self.assertEqual(renderer.mcolors.to_hex(fit["_artist"].get_color()), "#aa1144")
            self.assertEqual(fit["editable"]["color"], "/options/regression_color")
            renderer.plt.close(fig)

    def test_box_summary_roles_and_legacy_fallback_preserve_fills_and_values(self):
        source = self.csv("g,v\nA,1\nA,2\nA,3\nA,6\nB,2\nB,3\nB,5\nB,7\n")
        base = {"chart": "distribution", "fields": {"group": "g", "value": "v"},
                "layout": {"font": "DejaVu Sans", "line_width_pt": .62},
                "colors": {"A": "#2581B9", "B": "#DF9A3C"}, "options": {"grid": True}}
        variants = [(base, .62), ({**base, "line_roles": {"summary": {"line_width_pt": .85}}}, .85)]
        for spec, expected in variants:
            data = renderer.prepare(source, spec)
            layout, typography, rc = renderer.setup(spec)
            with renderer.plt.rc_context(rc):
                fig, colors = renderer.draw(data, spec, layout, typography, {})
                ax = fig.axes[0]
                self.assertEqual([patch.get_linewidth() for patch in ax.patches], [expected, expected])
                self.assertTrue(all(line.get_linewidth() == expected for line in ax.lines))
                self.assertEqual(renderer.mcolors.to_hex(ax.lines[4].get_color()), "#222222")
                for patch, group in zip(ax.patches, ("A", "B")):
                    self.assertEqual(patch.get_facecolor(), renderer.mcolors.to_rgba(colors[group], .22))
                    self.assertEqual(renderer.mcolors.to_hex(patch.get_edgecolor()), colors[group].lower())
                self.assertTrue(all((points.get_linewidths() == 0).all() for points in ax.collections))
                self.assertEqual(ax.spines["left"].get_linewidth(), .62)
                self.assertTrue(all(line.get_linewidth() == .4 for line in ax.get_xgridlines() + ax.get_ygridlines()))
                self.assertEqual(data["v"].tolist(), pd.read_csv(source)["v"].tolist())
                renderer.plt.close(fig)

    def test_statistics_known_result_and_constant_rejection(self):
        spec = deepcopy(self.base)
        spec["statistics"] = {"method": "pearson"}
        data = renderer.prepare(self.csv("x,y\n1,2\n2,4\n3,6\n4,8\n"), spec)
        result = renderer.statistics(data, spec)
        self.assertAlmostEqual(result["statistic"], 1)
        self.assertLess(result["pvalue"], 1e-12)
        constant = renderer.prepare(self.csv("x,y\n1,2\n1,4\n1,6\n"), spec)
        with self.assertRaises(renderer.SpecError):
            renderer.statistics(constant, spec)
        self.assertEqual(renderer.statistics(data, self.base)["method"], "none")

    def test_explicit_none_is_descriptive_and_rejects_incompatible_statistical_requests(self):
        source = self.csv("x,y,subject\n1,2,S1\n2,3,S1\n3,4,S2\n")
        spec = deepcopy(self.base)
        spec["fields"]["unit"] = "subject"
        spec["statistics"] = {"method": "none", "annotate": False}
        qa = renderer.render(source, spec, self.root / "explicit-none")
        self.assertEqual(qa["status"], "pass")
        result = json.loads((self.root / "explicit-none/stats.json").read_text())
        self.assertEqual(result["method"], "none")
        self.assertNotIn("pvalue", result)
        self.assertEqual(len(pd.read_csv(self.root / "explicit-none/plotting-data.csv")), 3)
        data = renderer.prepare(source, spec)
        self.assertEqual(result, renderer.statistics(data, self.base))
        for forbidden in ({"annotate": True}, {"groups": ["A", "B"]}, {"unit": "subject"}):
            with self.subTest(forbidden=forbidden):
                conflict = deepcopy(spec)
                conflict["statistics"].update(forbidden)
                with self.assertRaisesRegex(renderer.SpecError, "cannot be combined"):
                    renderer.prepare(source, conflict)
                with self.assertRaisesRegex(renderer.SpecError, "cannot be combined"):
                    renderer.statistics(data, conflict)

    def test_welch_and_independence_checks(self):
        spec = {"chart": "distribution", "fields": {"group": "g", "value": "v", "unit": "id"}, "statistics": {"method": "welch", "groups": ["A", "B"]}}
        data = renderer.prepare(self.csv("g,v,id\nA,1,a1\nA,2,a2\nA,3,a3\nB,4,b1\nB,5,b2\nB,6,b3\n"), spec)
        result = renderer.statistics(data, spec)
        self.assertAlmostEqual(result["statistic"], -3.6742346141747673)
        self.assertAlmostEqual(result["pvalue"], .021311641128756727)
        annotated = deepcopy(spec)
        annotated["statistics"]["annotate"] = True
        layout, typography, rc = renderer.setup(annotated)
        with renderer.plt.rc_context(rc):
            fig, _ = renderer.draw(data, annotated, layout, typography, result)
            annotations = [item.get_text() for item in fig.findobj(renderer.Text)]
            self.assertTrue(any("A vs B\nwelch" in text for text in annotations))
            renderer.plt.close(fig)
        data.loc[data.g == "B", "id"] = ["a1", "a2", "a3"]
        with self.assertRaises(renderer.SpecError):
            renderer.statistics(data, spec)

    def test_scatter_rejects_repeated_units_from_either_alias(self):
        source = self.csv("x,y,subject\n1,2,S1\n2,5,S1\n3,6,S2\n4,9,S2\n5,11,S3\n6,10,S3\n")
        for method in ("pearson", "spearman"):
            for location in ("fields", "statistics"):
                with self.subTest(method=method, location=location):
                    spec = deepcopy(self.base)
                    spec["statistics"] = {"method": method}
                    spec[location]["unit"] = "subject"
                    data = renderer.prepare(source, spec)
                    with self.assertRaisesRegex(renderer.SpecError, "one observation per supplied independent unit"):
                        renderer.statistics(data, spec)

    def test_scatter_unit_aliases_preserve_results_and_reject_conflicts(self):
        spec = deepcopy(self.base)
        spec["statistics"] = {"method": "pearson", "unit": "subject"}
        source = self.csv("x,y,subject,row\n1,2,S1,R1\n2,4,S2,R2\n3,6,S3,R3\n4,8,S4,R4\n")
        data = renderer.prepare(source, spec)
        expected = renderer.statistics(data, spec)
        self.assertEqual(expected["n"], 4)
        self.assertAlmostEqual(expected["statistic"], 1)
        spec["fields"]["unit"] = "subject"
        self.assertEqual(renderer.statistics(data, spec), expected)
        spec["statistics"]["unit"] = "row"
        with self.assertRaisesRegex(renderer.SpecError, "must name the same independent unit column"):
            renderer.statistics(data, spec)

    def test_scatter_statistics_unit_requires_present_nonempty_ids(self):
        spec = deepcopy(self.base)
        spec["statistics"] = {"method": "spearman", "unit": "subject"}
        for source in ("x,y\n1,2\n2,4\n3,6\n", "x,y,subject\n1,2,S1\n2,4,\n3,6,S3\n"):
            with self.subTest(source=source):
                data = renderer.prepare(self.csv(source), spec)
                with self.assertRaisesRegex(renderer.SpecError, "statistical unit IDs"):
                    renderer.statistics(data, spec)

    def test_paired_test_aligns_ids_and_rejects_unmatched_pairs(self):
        spec = {"chart": "distribution", "fields": {"group": "g", "value": "v", "unit": "id"}, "statistics": {"method": "wilcoxon", "groups": ["A", "B"]}}
        data = renderer.prepare(self.csv("g,v,id\nA,1,u1\nA,2,u2\nA,3,u3\nA,4,u4\nB,5,u4\nB,3,u2\nB,2,u1\nB,4,u3\n"), spec)
        result = renderer.statistics(data, spec)
        self.assertEqual(result["pair_order"], ["u1", "u2", "u3", "u4"])
        self.assertEqual(result["statistic"], 0)
        self.assertAlmostEqual(result["pvalue"], .125)
        data.loc[data.g == "B", "id"] = ["u4", "u2", "u1", "u5"]
        with self.assertRaises(renderer.SpecError):
            renderer.statistics(data, spec)

    def test_distribution_preserves_points_and_seed_across_orientation(self):
        data = self.csv("g,v\nA,1\nA,2\nA,3\nB,2\nB,4\nB,9\n")
        spec = {"chart": "distribution", "fields": {"group": "g", "value": "v"}, "layout": {"font": "DejaVu Sans", "dpi": 100}, "formats": ["png"], "seed": 4}
        for orientation in ["vertical", "horizontal"]:
            spec["options"] = {"orientation": orientation, "kind": "violin"}
            renderer.render(data, spec, self.root / orientation)
        a = pd.read_csv(self.root / "vertical/plotting-data.csv")
        b = pd.read_csv(self.root / "horizontal/plotting-data.csv")
        self.assertEqual(list(a["_easyviz_jitter_position"]), list(b["_easyviz_jitter_position"]))
        self.assertEqual(list(a["v"]), [1, 2, 3, 2, 4, 9])

    def test_optional_violin_faces_and_inner_quartiles_use_raw_values_in_both_orientations(self):
        source = self.csv("g,v\nA,0\nA,1\nA,2\nA,4\nA,9\nB,1\nB,5\nB,6\n")
        original = source.read_bytes()
        for orientation in ("vertical", "horizontal"):
            spec = {"chart": "distribution", "fields": {"group": "g", "value": "v"},
                    "colors": {"A": "#29ACF3", "B": "#FF797C"},
                    "layout": {"font": "DejaVu Sans"},
                    "line_roles": {"data": {"line_width_pt": .85}, "summary": {"line_width_pt": .7}},
                    "options": {"kind": "violin", "orientation": orientation, "violin_fill_alpha": .16,
                                "violin_inner": "box", "violin_inner_width": .14, "alpha": 1}}
            data = renderer.prepare(source, spec)
            layout, typography, rc = renderer.setup(spec)
            result = {"method": "none"}
            with renderer.plt.rc_context(rc):
                fig, colors = renderer.draw(data, spec, layout, typography, result)
                ax = fig.axes[0]
                bodies = [e["_artist"] for e in fig._easyviz_elements if e["role"] == "distribution"]
                self.assertEqual(len(bodies), 2)
                for body, group in zip(bodies, ("A", "B")):
                    self.assertIsNone(body.get_alpha())
                    self.assertEqual(tuple(body.get_facecolors()[0]), renderer.mcolors.to_rgba(colors[group], .16))
                    self.assertEqual(tuple(body.get_edgecolors()[0]), renderer.mcolors.to_rgba(colors[group]))
                    self.assertEqual(body.get_linewidths()[0], .85)
                summaries = [e for e in fig._easyviz_elements if e["role"] == "summary-line"]
                self.assertEqual(len(summaries), 4)
                for i, (q1, median, q3) in enumerate(((1., 2., 4.), (3., 5., 5.5))):
                    rect = summaries[2 * i]["_artist"]
                    line = summaries[2 * i + 1]["_artist"]
                    self.assertEqual(rect.get_facecolor()[3], 0)
                    self.assertEqual(rect.get_linewidth(), .7)
                    self.assertEqual(line.get_linewidth(), .7)
                    if orientation == "vertical":
                        renderer.np.testing.assert_allclose([rect.get_x(), rect.get_y(), rect.get_width(), rect.get_height()], [i - .07, q1, .14, q3 - q1])
                        renderer.np.testing.assert_allclose(line.get_xdata(), [i - .07, i + .07])
                        renderer.np.testing.assert_allclose(line.get_ydata(), [median, median])
                    else:
                        renderer.np.testing.assert_allclose([rect.get_x(), rect.get_y(), rect.get_width(), rect.get_height()], [q1, i - .07, q3 - q1, .14])
                        renderer.np.testing.assert_allclose(line.get_xdata(), [median, median])
                        renderer.np.testing.assert_allclose(line.get_ydata(), [i - .07, i + .07])
                    self.assertEqual(result["violin_inner_summaries"][i]["q1"], q1)
                    self.assertEqual(result["violin_inner_summaries"][i]["median"], median)
                    self.assertEqual(result["violin_inner_summaries"][i]["q3"], q3)
                observations = [e["_artist"] for e in fig._easyviz_elements if e["role"] == "point-group"]
                self.assertEqual(sum(len(p.get_offsets()) for p in observations), 8)
                numeric_axis = 1 if orientation == "vertical" else 0
                self.assertEqual([float(v) for p in observations for v in p.get_offsets()[:, numeric_axis]], [0, 1, 2, 4, 9, 1, 5, 6])
                self.assertNotIn("pvalue", result)
                self.assertIn("independently normalized", result["violin_definition"])
                renderer.plt.close(fig)
        self.assertEqual(source.read_bytes(), original)

    def test_violin_legacy_style_and_explicit_median_visibility(self):
        source = self.csv("g,v\nA,1\nA,2\nA,4\nA,9\n")
        base = {"chart": "distribution", "fields": {"group": "g", "value": "v"},
                "layout": {"font": "DejaVu Sans"}, "options": {"kind": "violin"}}
        for options in ({"kind": "violin"}, {"kind": "violin", "violin_inner": "none"},
                        {"kind": "violin", "violin_inner": "box", "violin_median_visible": False}):
            spec = {**base, "options": options}
            data = renderer.prepare(source, spec)
            layout, typography, rc = renderer.setup(spec)
            with renderer.plt.rc_context(rc):
                result = {}
                fig, _ = renderer.draw(data, spec, layout, typography, result)
                body = next(e["_artist"] for e in fig._easyviz_elements if e["role"] == "distribution")
                self.assertEqual(body.get_alpha(), .3, "Omitted face styling retains the legacy Matplotlib collection opacity")
                summaries = [e for e in fig._easyviz_elements if e["role"] == "summary-line"]
                self.assertEqual(len(summaries), 1 if options.get("violin_inner") == "box" else 0)
                if summaries:
                    self.assertFalse(result["violin_inner_summaries"][0]["median_line_visible"])
                renderer.plt.close(fig)

    def test_violin_specific_style_validation_rejects_silent_unsupported_options(self):
        base = {"chart": "distribution", "fields": {"group": "g", "value": "v"}, "options": {"kind": "violin"}}
        invalid = [{"violin_fill_alpha": True}, {"violin_fill_alpha": "0.2"}, {"violin_fill_alpha": -.1},
                   {"violin_fill_alpha": 1.1}, {"violin_fill_alpha": float("nan")}, {"violin_inner": "quartile"},
                   {"violin_inner_width": .2}, {"violin_inner": "box", "violin_inner_width": 0},
                   {"violin_inner": "box", "violin_inner_width": .71}, {"violin_inner": "box", "violin_inner_width": True},
                   {"violin_median_visible": True}, {"violin_inner": "box", "violin_median_visible": 1},
                   {"kind": "box", "violin_fill_alpha": .2}, {"kind": "box", "violin_inner": "none"}]
        for options in invalid:
            with self.subTest(options=options), self.assertRaises(renderer.SpecError):
                renderer.validate_spec({**base, "options": {**base["options"], **options}})

    def test_rejects_hidden_values_unknown_options_and_clipped_labels(self):
        data = self.csv("x,y\n1,2\n2,3\n3,4\n")
        spec = deepcopy(self.base)
        spec["options"] = {"fit": "linear"}
        with self.assertRaisesRegex(renderer.SpecError, "Unknown"):
            renderer.prepare(data, spec)
        spec["options"] = {"x_limits": [1, 2]}
        with self.assertRaisesRegex(renderer.SpecError, "hide observations"):
            renderer.render(data, spec, self.root / "hidden")
        spec["options"] = {}
        spec["labels"]["x"] = "Very long axis label " * 15
        with self.assertRaisesRegex(renderer.SpecError, "Canvas QA"):
            renderer.render(data, spec, self.root / "clipped")
        qa = json.loads((self.root / "clipped/qa.json").read_text())
        self.assertEqual(qa["status"], "needs_revision")
        self.assertTrue(qa["clipped_text"])

    def test_dot_area_and_custom_continuous_palette(self):
        spec = {"chart": "dotplot", "fields": {"x": "x", "y": "y", "size": "s", "color": "c"}, "layout": {"width_mm": 110, "font": "DejaVu Sans", "dpi": 100}, "colormap": "blue-white-red", "options": {"size_max": 1, "max_area_pt2": 100, "color_limits": [-2, 2], "color_center": 0}, "formats": ["png"]}
        data = self.csv("x,y,s,c\nG1,A,0,-1\nG2,A,.25,0\nG1,B,1,1\nG2,B,.5,2\n")
        renderer.render(data, spec, self.root / "dots")
        plotted = pd.read_csv(self.root / "dots/plotting-data.csv")
        self.assertEqual(list(plotted["_easyviz_area_pt2"]), [0, 25, 100, 50])
        renderer.np.testing.assert_allclose(plotted["_easyviz_marker_size_parameter_pt2"], [0, 25 * 4 / math.pi, 100 * 4 / math.pi, 50 * 4 / math.pi])
        data = renderer.prepare(data, spec)
        layout, typography, rc = renderer.setup(spec)
        with renderer.plt.rc_context(rc):
            fig, _ = renderer.draw(data, spec, layout, typography, {"method": "none"})
            renderer.np.testing.assert_allclose(collection_fill_areas_pt2(fig.axes[0].collections[0], fig), [0, 25, 100, 50], rtol=1e-6, atol=1e-10)
        settings = json.loads((self.root / "dots/settings.json").read_text())
        self.assertEqual(settings["mark_geometry"]["mode"], "mapped_circle_fill_area")
        with self.assertRaises(renderer.SpecError):
            renderer.continuous({"options": {"color_limits": [0, 1]}}, [-1, 0, 1])

    def test_failed_rerun_invalidates_previous_passing_exports(self):
        data = self.csv("x,y\n1,2\n2,3\n3,4\n")
        spec = deepcopy(self.base)
        spec["formats"] = ["png"]
        output = self.root / "rerun"
        renderer.render(data, spec, output)
        self.assertTrue(json.loads((output / "qa.json").read_text())["valid_outputs"])
        data.write_text("x,y\n1,NaN\n")
        with self.assertRaises(renderer.SpecError):
            renderer.render(data, spec, output)
        qa = json.loads((output / "qa.json").read_text())
        self.assertEqual(qa["status"], "failed")
        self.assertFalse(qa["valid_outputs"])

    def test_missing_glyphs_fail_qa_instead_of_silent_font_loss(self):
        data = self.csv("x,y\n1,2\n2,3\n3,4\n")
        spec = deepcopy(self.base)
        spec["formats"] = ["png"]
        spec["labels"]["title"] = "Missing glyph \U0010ffff"
        with self.assertRaisesRegex(renderer.SpecError, "Canvas QA"):
            renderer.render(data, spec, self.root / "glyph")
        qa = json.loads((self.root / "glyph/qa.json").read_text())
        self.assertTrue(qa["missing_glyphs"])

    def test_ols_overlay_rejects_log_scales(self):
        data = self.csv("x,y\n1,2\n2,3\n3,4\n")
        spec = deepcopy(self.base)
        for axis in ("x", "y"):
            spec["options"] = {"regression": True, f"{axis}_scale": "log"}
            with self.assertRaisesRegex(renderer.SpecError, "requires linear"):
                renderer.render(data, spec, self.root / axis)

    def test_literal_na_labels_and_truly_empty_values_are_distinct(self):
        spec = {"chart": "distribution", "fields": {"group": "group", "value": "value"}}
        data = renderer.prepare(self.csv("group,value\nNA,1\nnull,2\nControl,3\n"), spec)
        self.assertEqual(data.group.tolist(), ["NA", "null", "Control"])
        for body in ["group,value\n,1\n", "group,value\nNA,NaN\n"]:
            with self.assertRaises(renderer.SpecError):
                renderer.prepare(self.csv(body), spec)

    def test_tick_collisions_fail_then_layout_repair_preserves_font(self):
        data = self.csv("r,c,v\n" + "".join(f"r{i},Group {j:02d},{i + j}\n" for i in range(3) for j in range(12)))
        spec = {"chart": "heatmap", "fields": {"row": "r", "column": "c", "value": "v"}, "layout": {"font": "DejaVu Sans", "width_mm": 88, "height_mm": 88, "dpi": 120}, "colormap": "viridis", "options": {"x_rotation": 0}, "formats": ["png"]}
        with self.assertRaisesRegex(renderer.SpecError, "tick-label overlaps"):
            renderer.render(data, spec, self.root / "crowded")
        qa = json.loads((self.root / "crowded/qa.json").read_text())
        self.assertFalse(qa["valid_outputs"])
        self.assertTrue(qa["overlapping_tick_labels"])
        self.assertEqual(qa["clipped_text"], [])
        spec["layout"]["width_mm"] = 132
        spec["options"]["x_rotation"] = 90
        renderer.render(data, spec, self.root / "repaired")
        settings = json.loads((self.root / "repaired/settings.json").read_text())
        self.assertEqual(settings["typography"]["tick"], 8)
        self.assertEqual(len(pd.read_csv(self.root / "repaired/plotting-data.csv")), 36)

    def test_oblique_tick_boxes_are_not_rejected_as_axis_aligned_collisions(self):
        fig, ax = renderer.plt.subplots(figsize=(4, 3), dpi=100)
        ax.set_xticks(range(6), [f"Category {i}" for i in range(6)], rotation=45)
        fig.canvas.draw()
        overlaps, skipped = renderer.check_tick_label_overlap(fig, fig.canvas.get_renderer())
        self.assertFalse(overlaps)
        self.assertEqual(len(skipped), 6)
        renderer.plt.close(fig)

    def test_log_limits_require_positive_bounds(self):
        data = self.csv("x,y\n1,2\n2,3\n3,4\n")
        for low in [0, -1]:
            spec = deepcopy(self.base)
            spec["options"] = {"x_scale": "log", "x_limits": [low, 10]}
            with self.assertRaisesRegex(renderer.SpecError, "must be strictly positive"):
                renderer.render(data, spec, self.root / str(low))

    def test_zero_library_p_value_displays_a_bound_and_keeps_raw_value(self):
        spec = deepcopy(self.base)
        spec.update(statistics={"method": "pearson", "annotate": True}, formats=["svg"])
        renderer.render(self.csv("x,y\n1,2\n2,4\n3,6\n4,8\n"), spec, self.root / "bound")
        stats = json.loads((self.root / "bound/stats.json").read_text())
        self.assertEqual(stats["pvalue"], 0)
        self.assertEqual(stats["pvalue_display"]["upper_bound"], .001)
        svg = ET.parse(self.root / "bound/panel.svg").getroot()
        text = " ".join(svg.itertext())
        self.assertIn("p < 0.001", text)
        self.assertNotIn("p = 0", text)


if __name__ == "__main__":
    unittest.main()
