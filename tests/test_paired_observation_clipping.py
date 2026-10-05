"""Actual paired raw registration, source mapping and final raster geometry."""
from copy import deepcopy
import importlib.util
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import numpy as np

SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/paired_plot.py"
loader = importlib.util.spec_from_file_location("paired_endpoint_candidate", SCRIPT)
paired = importlib.util.module_from_spec(loader)
loader.loader.exec_module(paired)


class PairedObservationClippingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="paired-clipping-")
        self.root = Path(self.temp.name)
        self.source = self.root / "source.csv"
        self.source.write_text("id,condition,value\nu1,A,1\nu1,B,2\nu2,A,3\nu2,B,2.5\n")
        self.spec = {"chart": "paired", "fields": {"unit": "id", "condition": "condition", "value": "value"},
                     "options": {"point_layout": "swarm", "point_area_pt2": 10, "point_alpha": 1,
                                 "connect_pairs": True, "y_limits": [0, 4]},
                     "layout": {"width_mm": 88, "height_mm": 66.1, "font": "DejaVu Sans", "dpi": 160,
                                "auto_fit": False, "margins": {"left": .19, "right": .77, "bottom": .23, "top": .88}},
                     "formats": ["png", "pdf", "svg"], "labels": {"y": "Value"}}

    def tearDown(self):
        paired.plt.close("all")
        self.temp.cleanup()

    def render(self, spec=None, *, fails=False, name="output"):
        spec = deepcopy(spec or self.spec)
        raw = self.source.read_bytes()
        out = self.root / name
        if fails:
            with self.assertRaisesRegex(paired.SpecError, "QA needs revision"):
                paired.render(self.source, spec, out)
        else:
            paired.render(self.source, spec, out)
        qa = json.loads((out / "qa.json").read_text())
        settings = json.loads((out / "settings.json").read_text())
        self.assertEqual(qa["valid_outputs"], not fails)
        self.assertEqual(settings["options"], spec["options"])
        self.assertEqual(settings["observation_clipping"], qa["observation_clipping"])
        self.assertEqual(self.source.read_bytes(), raw)
        self.assertEqual(settings["mark_policy"]["geometric_circle_area_pt2"], spec["options"]["point_area_pt2"])
        for suffix in spec["formats"]:
            self.assertTrue((out / ("panel." + suffix)).is_file())
        return out, qa, settings

    def test_safe_actual_exports_have_registered_groups_and_exact_source_records(self):
        out, qa, settings = self.render()
        elements = json.loads((out / "elements.json").read_text())["elements"]
        groups = [item for item in elements if item["role"] == "point-group"]
        self.assertEqual(len(groups), 2)
        self.assertEqual([item["source_keys"][0]["records"] for item in groups], [[1, 3], [2, 4]])
        self.assertEqual([item["source_keys"][0]["units"] for item in groups], [["u1", "u2"], ["u1", "u2"]])
        svg_ids = {element.attrib["id"] for element in ET.parse(out / "panel.svg").iter() if "id" in element.attrib}
        self.assertTrue(all(group["id"] in svg_ids for group in groups))
        for report in qa["observation_clipping"]["by_format"].values():
            self.assertEqual(report["checked_observations"], 4)
            self.assertEqual(report["clipped_observations"], 0)
            self.assertEqual(len(report["groups"]), 2)
        self.assertEqual(qa["source_to_artist_audit"]["source_points_checked"], 4)
        self.assertEqual(qa["source_to_artist_audit"]["complete_units"], 2)
        self.assertEqual(qa["source_to_artist_audit"]["connectors_drawn"], 2)
        self.assertEqual(settings["axis"]["y_limits"], [0, 4])

    def test_raster_only_clipping_refuses_false_pass_even_when_nominal_check_passes(self):
        spec = deepcopy(self.spec)
        radius = math.sqrt(10 / math.pi) * 25.4 / 72
        high = 3 / (1 - radius * 1.0001 / (.65 * 66.1))
        spec["options"]["y_limits"] = [0, high]
        out, qa, settings = self.render(spec, fails=True)
        self.assertEqual(qa["mark_geometry"]["status"], "pass")
        self.assertEqual(qa["source_to_artist_audit"]["status"], "pass")
        reports = qa["observation_clipping"]["by_format"]
        self.assertEqual(reports["svg"]["status"], "pass")
        self.assertEqual(reports["pdf"]["status"], "pass")
        self.assertEqual(reports["png"]["status"], "needs_revision")
        self.assertEqual(reports["png"]["clipped_observations"], 1)
        self.assertEqual(reports["png"]["clipped"][0]["source"], {"record": 3})
        self.assertEqual(settings["axis"]["y_limits"], [0, high])
        plotted = paired.pd.read_csv(out / "plotting-data.csv")
        self.assertEqual(plotted["value"].tolist(), [1, 2, 3, 2.5])
        self.assertEqual(plotted["id"].tolist(), ["u1", "u1", "u2", "u2"])

    def test_locked_numeric_endpoints_have_their_real_row_mappings(self):
        spec = deepcopy(self.spec)
        spec["options"]["y_limits"] = [1, 3]
        _, qa, _ = self.render(spec, fails=True)
        for report in qa["observation_clipping"]["by_format"].values():
            self.assertEqual(sorted(item["source"]["record"] for item in report["clipped"]), [1, 3])
            self.assertEqual(report["checked_observations"], 4)

    def test_logarithmic_numeric_endpoints_are_measured_after_final_transform(self):
        self.source.write_text("id,condition,value\nu1,A,1\nu1,B,10\nu2,A,100\nu2,B,30\n")
        spec = deepcopy(self.spec)
        spec["options"].update(y_scale="log", y_limits=[1, 100])
        _, qa, settings = self.render(spec, fails=True)
        self.assertEqual(settings["axis"]["y_scale"], "log")
        for report in qa["observation_clipping"]["by_format"].values():
            self.assertEqual(sorted(item["source"]["record"] for item in report["clipped"]), [1, 3])
            self.assertTrue(all(group["axes"]["y_scale"] == "log" for group in report["groups"]))

    def test_visible_outline_and_block_colours_keep_source_semantics(self):
        self.source.write_text("id,condition,value,arm\nu1,A,1,Blue\nu1,B,2,Blue\nu2,A,3,Blue\nu2,B,2.5,Blue\nu3,A,1.5,Teal\nu3,B,2.2,Teal\n")
        spec = deepcopy(self.spec)
        spec["fields"]["block"] = "arm"
        spec["colors"] = {"Blue": "#29ACF3", "Teal": "#10BC9A"}
        spec["options"].update(point_edge_width_pt=.8, point_edge_color="#444444")
        out, qa, settings = self.render(spec)
        self.assertEqual(settings["mark_policy"]["outline_width_pt"], .8)
        groups = [item for item in json.loads((out / "elements.json").read_text())["elements"] if item["role"] == "point-group"]
        self.assertEqual(len(groups), 4)
        self.assertEqual({key["block"] for item in groups for key in item["source_keys"]}, {"Blue", "Teal"})
        for report in qa["observation_clipping"]["by_format"].values():
            self.assertEqual(report["checked_observations"], 6)
        self.assertEqual(qa["source_to_artist_audit"]["complete_units"], 3)
        self.assertEqual(settings["resolved_colors"], spec["colors"])

    def test_malformed_literal_rows_and_headers_refuse_before_any_export(self):
        malformed = {
            "hidden-index": "id,condition,value\nextra,u1,A,1\nextra,u1,B,2\nextra,u2,A,3\nextra,u2,B,2.5\n",
            "short-row": "id,condition,value\nu1,A,1\nu1,B\n",
            "duplicate-header": "id,condition,value,id\nu1,A,1,u1\nu1,B,2,u1\n",
            "empty-header": "id,condition,value,\nu1,A,1,note\nu1,B,2,note\n",
            "empty-record": "id,condition,value\nu1,A,1\n\nu1,B,2\n",
        }
        for name, raw in malformed.items():
            with self.subTest(name=name):
                self.source.write_text(raw)
                out = self.root / name
                with self.assertRaisesRegex(paired.SpecError, "CSV (rows|headers)"):
                    paired.render(self.source, deepcopy(self.spec), out)
                qa = json.loads((out / "qa.json").read_text())
                self.assertFalse(qa["valid_outputs"])
                self.assertEqual(qa["status"], "failed")
                self.assertFalse((out / "elements.json").exists())
                self.assertFalse(any((out / ("panel." + suffix)).exists() for suffix in self.spec["formats"]))

    def test_actual_source_bytes_preserve_quoted_and_numeric_unit_identities(self):
        self.source.write_bytes('\ufeffid,condition,value\n001,A,1.0\n001,B,2.00\n"002,α",A,3.000\n"002,α",B,2.500\n'.encode())
        expected_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()
        out, qa, settings = self.render()
        elements = json.loads((out / "elements.json").read_text())
        groups = [item for item in elements["elements"] if item["role"] == "point-group"]
        self.assertEqual([item["source_keys"][0]["units"] for item in groups], [["001", "002,α"], ["001", "002,α"]])
        self.assertEqual(qa["input_sha256"], expected_hash)
        self.assertEqual(settings["input_sha256"], expected_hash)
        self.assertEqual(settings["source_bindings"]["data_file"], {"path": str(self.source.resolve()), "sha256": expected_hash})
        self.assertEqual(elements["version"]["input_sha256"], expected_hash)
        plotted = paired.pd.read_csv(out / "plotting-data.csv", dtype=object, keep_default_na=False)
        self.assertEqual(plotted["id"].tolist(), ["001", "001", "002,α", "002,α"])
        self.assertEqual(plotted["_easyviz_source_value_text"].tolist(), ["1.0", "2.00", "3.000", "2.500"])


if __name__ == "__main__":
    unittest.main()
