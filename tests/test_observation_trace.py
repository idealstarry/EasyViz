"""Original value text must survive portable observation-family exports."""
import csv
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"


class ObservationTraceTests(unittest.TestCase):
    def test_source_decimal_text_survives_numeric_serialization_in_all_three_families(self):
        literals = ["5240.4399999999996", "6398.8300000000008",
                    "619.4699999999999", "1699.3399999999999"]
        with tempfile.TemporaryDirectory(prefix="easyviz-value-trace-") as directory:
            root = Path(directory)
            source = root / "input.csv"
            with source.open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["ID", "stage", "reading"])
                writer.writerows(zip(["001", "002", "001", "002"],
                                     ["Before", "Before", "After", "After"], literals))
            for name, chart, fields, options in (
                ("ecdf_plot", "ecdf", {"unit": "ID", "group": "stage", "value": "reading"}, {}),
                ("paired_plot", "paired", {"unit": "ID", "condition": "stage", "value": "reading"},
                 {"point_layout": "jitter"}),
                ("replicate_plot", "replicate", {"unit": "ID", "condition": "stage", "value": "reading"},
                 {"mode": "summary", "uncertainty": "sample_sd"}),
            ):
                with self.subTest(chart=chart):
                    loader = importlib.util.spec_from_file_location("trace_" + name, SCRIPTS / (name + ".py"))
                    renderer = importlib.util.module_from_spec(loader)
                    loader.loader.exec_module(renderer)
                    spec = {"chart": chart, "fields": fields, "options": options,
                            "layout": {"width_mm": 100, "height_mm": 85, "font": "DejaVu Sans",
                                       "font_size_pt": 8, "dpi": 100, "auto_fit": True},
                            "labels": {"x": "", "y": "Measurement (a.u.)"}, "formats": ["svg"]}
                    if chart == "ecdf":
                        spec["colors"] = {"Before": "#5278A8", "After": "#C2764E"}
                    out = root / chart
                    qa = renderer.render(source, spec, out)
                    self.assertTrue(qa["valid_outputs"])
                    with (out / "plotting-data.csv").open(newline="") as handle:
                        rows = list(csv.DictReader(handle))
                    self.assertEqual([r["_easyviz_source_value_text"] for r in rows], literals)
                    self.assertEqual([r["ID"] for r in rows], ["001", "002", "001", "002"])
                    self.assertTrue(all(math.isclose(float(row["reading"]), float(raw), rel_tol=1e-14)
                                        for row, raw in zip(rows, literals)))
                    self.assertEqual(source.read_text().count("5240.4399999999996"), 1)
