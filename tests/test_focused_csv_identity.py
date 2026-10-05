"""Real focused exports must preserve literal source identity and consumption."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

RUNTIME = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"
LAYOUT = {"width_mm": 100, "height_mm": 80, "font": "DejaVu Sans", "font_size_pt": 8,
          "dpi": 160, "auto_fit": False, "margins": {"left": .22, "right": .83, "bottom": .23, "top": .86}}
CASES = {
    "replicate_plot": ('id,condition,value\n001,A,1.0\n"002,α",A,3.00\n003,B,2.000\n004,B,2.500\n',
        {"chart": "replicate", "fields": {"unit": "id", "condition": "condition", "value": "value"},
         "options": {"mode": "summary", "uncertainty": "none", "y_limits": [0, 4]}, "colors": {"A": "#29ACF3", "B": "#FF7D86"}}, "id"),
    "ecdf_plot": ('id,group,value\n001,A,1.0\n"002,α",A,3.00\n003,B,2.000\n004,B,2.500\n',
        {"chart": "ecdf", "fields": {"unit": "id", "group": "group", "value": "value"},
         "options": {"x_limits": [0, 4]}, "colors": {"A": "#29ACF3", "B": "#FF7D86"}}, "id"),
    "interval_plot": ('label,est,lo,hi\n001,1.0,0.50,1.500\n"002,α",2.0,1.50,2.500\n',
        {"chart": "interval", "fields": {"label": "label", "estimate": "est", "lower": "lo", "upper": "hi"},
         "options": {"x_limits": [0, 3]}}, "label"),
    "timecourse_plot": ('minute,mean,sd,series,id\n1.0,1.0,0.20,A,001\n3.0,3.00,0.30,A,"002,α"\n1.0,2.000,0.20,B,003\n3.0,2.500,0.30,B,004\n',
        {"chart": "timecourse", "fields": {"x": "minute", "estimate": "mean", "sd": "sd", "series": "series"},
         "uncertainty": {"kind": "sd", "label": "Supplied SD"}, "options": {"x_limits": [0, 4], "y_limits": [0, 4]},
         "colors": {"A": "#29ACF3", "B": "#FF7D86"}}, "id"),
}
RECIPES = {}
for name in CASES:
    loader = importlib.util.spec_from_file_location("focused_csv_test_" + name, RUNTIME / (name + ".py"))
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    RECIPES[name] = module


class FocusedCsvIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="focused-literal-csv-")
        self.root = Path(self.temp.name)

    def tearDown(self):
        for recipe in RECIPES.values():
            recipe.plt.close("all")
        self.temp.cleanup()

    def inputs(self, name, text=None):
        raw, base, _ = CASES[name]
        folder = self.root / name
        folder.mkdir(exist_ok=True)
        source = folder / "source.csv"
        source.write_bytes((text if text is not None else "\ufeff" + raw).encode())
        spec = {**deepcopy(base), "layout": deepcopy(LAYOUT), "formats": ["png", "pdf", "svg"]}
        return source, spec

    def test_literal_header_and_width_errors_are_refused_before_any_export(self):
        for name, (raw, _, _) in CASES.items():
            rows = raw.rstrip().splitlines()
            malformed = {
                "extra-leading-cell": "\n".join(rows[:1] + ["extra," + row for row in rows[1:]]) + "\n",
                "short-row": rows[0] + "\n" + rows[1].rsplit(",", 1)[0] + "\n",
                "duplicate-header": rows[0] + "," + rows[0].split(",")[0] + "\n" + rows[1] + ",x\n",
                "empty-header": rows[0] + ",\n" + rows[1] + ",x\n",
                "empty-record": rows[0] + "\n\n" + "\n".join(rows[1:]) + "\n",
            }
            for variant, text in malformed.items():
                with self.subTest(recipe=name, variant=variant):
                    recipe = RECIPES[name]
                    source, spec = self.inputs(name, text)
                    out = source.parent / variant
                    with self.assertRaisesRegex(recipe.SpecError, "CSV (rows|headers)"):
                        recipe.render(source, spec, out)
                    qa = json.loads((out / "qa.json").read_text())
                    self.assertEqual(qa["status"], "failed")
                    self.assertFalse(qa["valid_outputs"])
                    self.assertFalse((out / "elements.json").exists())
                    self.assertFalse(any((out / ("panel." + suffix)).exists() for suffix in spec["formats"]))

    def test_legal_bom_quoted_unicode_and_leading_zero_identity_bind_consumed_bytes(self):
        for name, (_, _, identity_column) in CASES.items():
            with self.subTest(recipe=name):
                recipe = RECIPES[name]
                source, spec = self.inputs(name)
                raw = source.read_bytes()
                consumed_hash = hashlib.sha256(raw).hexdigest()
                out = source.parent / "legal"
                recipe.render(source, spec, out)
                qa = json.loads((out / "qa.json").read_text())
                settings = json.loads((out / "settings.json").read_text())
                elements = json.loads((out / "elements.json").read_text())
                self.assertTrue(qa["valid_outputs"])
                for item in (qa, settings):
                    self.assertEqual(item["input_sha256"], consumed_hash)
                self.assertEqual(settings["source_bindings"]["data_file"], {"path": str(source.resolve()), "sha256": consumed_hash})
                self.assertEqual(elements["version"]["input_sha256"], consumed_hash)
                plotted = recipe.core.read_source_csv(out / "plotting-data.csv")
                original = recipe.core.read_source_csv(source)
                self.assertEqual(plotted[identity_column].tolist(), original[identity_column].tolist())
                self.assertEqual(original[identity_column].iloc[:2].tolist(), ["001", "002,α"])
                numeric_roles = ("estimate", "lower", "upper") if name == "interval_plot" else ("x", "estimate", "sd") if name == "timecourse_plot" else ("value",)
                for role in numeric_roles:
                    column = spec["fields"][role]
                    self.assertEqual(list(map(float, plotted[column])), list(map(float, original[column])))
                if name in ("replicate_plot", "ecdf_plot"):
                    self.assertEqual(plotted["_easyviz_source_value_text"].tolist(), original[spec["fields"]["value"]].tolist())
                elif name == "timecourse_plot":
                    for role in numeric_roles:
                        column = spec["fields"][role]
                        self.assertEqual(plotted[column].tolist(), original[column].tolist())
                self.assertEqual(source.read_bytes(), raw)
                self.assertTrue(all((out / ("panel." + suffix)).exists() for suffix in spec["formats"]))

    def test_replacement_during_consumption_cannot_claim_the_restored_file_digest(self):
        for name in CASES:
            with self.subTest(recipe=name):
                recipe = RECIPES[name]
                source, spec = self.inputs(name)
                original = source.read_bytes()
                # The extra nonmapped cell has no effect on numerical marks.
                lines = original.decode("utf-8-sig").rstrip().splitlines()
                raw_a = (lines[0] + ",note\n" + "\n".join(line + ",A" for line in lines[1:]) + "\n").encode()
                raw_b = (lines[0] + ",note\n" + "\n".join(line + ",B" for line in lines[1:]) + "\n").encode()
                source.write_bytes(raw_a)
                reader = recipe.core.read_source_csv
                calls = 0
                def replaced_read(path):
                    nonlocal calls
                    calls += 1
                    if calls == 1:
                        source.write_bytes(raw_b)
                        data = reader(path)
                        source.write_bytes(raw_a)
                        return data
                    return reader(path)
                out = source.parent / "changed-during-consumption"
                with mock.patch.object(recipe.core, "read_source_csv", side_effect=replaced_read):
                    with self.assertRaises(recipe.SpecError):
                        recipe.render(source, spec, out)
                qa = json.loads((out / "qa.json").read_text())
                settings = json.loads((out / "settings.json").read_text())
                elements = json.loads((out / "elements.json").read_text())
                consumed = hashlib.sha256(raw_b).hexdigest()
                self.assertFalse(qa["valid_outputs"])
                self.assertEqual(qa["input_sha256"], consumed)
                self.assertEqual(settings["input_sha256"], consumed)
                self.assertEqual(elements["version"]["input_sha256"], consumed)
                self.assertEqual(source.read_bytes(), raw_a)
                self.assertNotEqual(consumed, hashlib.sha256(source.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
