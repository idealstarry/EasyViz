"""All numerical recipes reject nonzero source values parsed as floating zero."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"
CASES = {
    "replicate_plot": ("id,condition,value\na,A,{value}\nb,A,1\n",
        {"chart": "replicate", "fields": {"unit": "id", "condition": "condition", "value": "value"}, "options": {"uncertainty": "none"}}),
    "paired_plot": ("id,condition,value\na,A,{value}\na,B,1\n",
        {"chart": "paired", "fields": {"unit": "id", "condition": "condition", "value": "value"}}),
    "ecdf_plot": ("value\n{value}\n1\n",
        {"chart": "ecdf", "fields": {"value": "value"}, "colors": {"all": "#29ACF3"}}),
    "interval_plot": ("label,estimate,lower,upper\na,{value},-1,1\n",
        {"chart": "interval", "fields": {"label": "label", "estimate": "estimate", "lower": "lower", "upper": "upper"}}),
    "timecourse_plot": ("x,estimate,sd\n1,{value},0\n2,1,0\n",
        {"chart": "timecourse", "fields": {"x": "x", "estimate": "estimate", "sd": "sd"},
         "uncertainty": {"kind": "sd", "label": "Supplied SD"}, "colors": {"all": "#29ACF3"}}),
    "annotated_matrix": ("row,column,value\na,b,{value}\n",
        {"chart": "annotated_matrix", "fields": {"row": "row", "column": "column", "value": "value"},
         "order": {"row": ["a"], "column": ["b"]}}),
}
RECIPES = {}
for name in CASES:
    loader = importlib.util.spec_from_file_location("numeric_representability_" + name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    RECIPES[name] = module


class FocusedNumericRepresentabilityTests(unittest.TestCase):
    def test_positive_and_negative_underflow_are_rejected_before_export(self):
        with tempfile.TemporaryDirectory(prefix="easyviz-numeric-underflow-") as temporary:
            root = Path(temporary)
            for name, (template, spec) in CASES.items():
                for value in ("1e-400", "-1e-400"):
                    with self.subTest(recipe=name, value=value):
                        source = root / "source.csv"
                        source.write_text(template.format(value=value))
                        before = source.read_bytes()
                        recipe = RECIPES[name]
                        with self.assertRaisesRegex(recipe.SpecError, "below floating-point representability"):
                            recipe.render(source, spec, root / name)
                        self.assertEqual(source.read_bytes(), before)
                        self.assertFalse((root / name / "panel.svg").exists())

    def test_literal_zero_with_extreme_exponent_remains_valid(self):
        with tempfile.TemporaryDirectory(prefix="easyviz-numeric-zero-") as temporary:
            source = Path(temporary) / "source.csv"
            for name, (template, spec) in CASES.items():
                with self.subTest(recipe=name):
                    source.write_text(template.format(value="0e-1000000"))
                    RECIPES[name].prepare(source, spec)


if __name__ == "__main__":
    unittest.main()
