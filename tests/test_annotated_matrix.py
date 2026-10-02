"""Source-backed complex matrix and actual transformed alignment checks."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image
from pypdf import PdfReader

SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/annotated_matrix.py"
loader = importlib.util.spec_from_file_location("easyviz_matrix_test", SCRIPT)
matrix = importlib.util.module_from_spec(loader)
loader.loader.exec_module(matrix)


class AnnotatedMatrixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-matrix-")
        self.root = Path(self.temp.name)
        self.spec = {"chart": "annotated_matrix", "fields": {"row": "sender", "column": "partner", "value": "signal", "state": "availability"},
                     "order": {"row": ["001", "NA", "null"], "column": ["B", "A"]},
                     "options": {"missing_cells": "unsupplied", "color_limits": [-2, 5]},
                     "labels": {"x": "Partner", "y": "Sender", "color": "Signal (a.u.)"},
                     "layout": {"width_mm": 120, "height_mm": 105, "font": "DejaVu Sans", "font_size_pt": 8, "dpi": 100},
                     "formats": ["png", "svg", "pdf", "tiff"]}
        self.source = self.csv("input.csv", "sender,partner,signal,availability,note\nNA,A,0,observed,literal NA\n001,B,-2,observed,negative\nnull,A,5,observed,high\n001,A,,unmeasured,explicit\nNA,B,2,observed,numeric\n")

    def tearDown(self):
        matrix.plt.close("all")
        self.temp.cleanup()

    def csv(self, name, text):
        path = self.root / name
        path.write_text(text)
        return path

    def draw(self, spec=None, **inputs):
        spec = spec or self.spec
        data = matrix.prepare(self.source, spec, **inputs)
        layout, typography, rc = matrix.core.setup(spec)
        with matrix.plt.rc_context(rc):
            fig = matrix.draw(data, spec, layout, typography)
            fig.canvas.draw()
        return data, fig

    def test_literal_ids_states_and_tampered_colors_and_geometry(self):
        data, fig = self.draw()
        self.assertEqual(data["rows"], ["001", "NA", "null"])
        self.assertEqual(data["data"]["sender"].tolist(), ["NA", "001", "null", "001", "NA"])
        self.assertEqual([c["state"] for c in data["cells"]], ["observed", "unmeasured", "observed", "observed", "unsupplied", "observed"])
        self.assertEqual(matrix.audit_source_artists(self.source, self.spec, fig)["status"], "pass")
        records = fig._easyviz_matrix_artists["cells"]
        observed_zero = next(r for r in records if r["value"] == 0)
        self.assertIsNone(observed_zero["artist"].get_hatch())
        self.assertEqual(observed_zero["artist"].get_xy(), (.5, .5))
        patch = records[0]["artist"]
        patch.set_visible(False)
        self.assertIn("matrix_cell_display_geometry_mismatch", {i["code"] for i in matrix.audit_source_artists(self.source, self.spec, fig)["issues"]})
        patch.set_visible(True)
        patch.set_transform(fig.transFigure)
        self.assertIn("matrix_cell_display_geometry_mismatch", {i["code"] for i in matrix.audit_source_artists(self.source, self.spec, fig)["issues"]})
        patch.set_transform(fig._easyviz_aligned_frame.main.transData)
        observed_zero["artist"].set_facecolor("red")
        records[0]["artist"].set_x(1)
        codes = {i["code"] for i in matrix.audit_source_artists(self.source, self.spec, fig)["issues"]}
        self.assertIn("matrix_cell_color_mismatch", codes)
        self.assertIn("matrix_cell_geometry_mismatch", codes)
        # A coordinated wrong scale and recoloring must not redefine the source audit.
        fig._easyviz_matrix_scale.set_clim(-100, 100)
        for record in records:
            if record["state"] == "observed": record["artist"].set_facecolor(fig._easyviz_matrix_scale.to_rgba(record["value"]))
        self.assertIn("matrix_cell_color_mismatch", {i["code"] for i in matrix.audit_source_artists(self.source, self.spec, fig)["issues"]})

    def test_keyed_metadata_marginals_and_final_alignment(self):
        spec = deepcopy(self.spec)
        spec["metadata"] = {"row": {"id": "key", "tracks": [{"field": "genome", "label": "Genome", "colors": {"yes": "#0072B2", "no": "#D55E00"}}]},
                            "column": {"id": "key", "tracks": [{"field": "condition", "label": "Condition", "colors": {"early": "#009E73", "late": "#CC79A7"}}]}}
        spec["marginals"] = {"row": {"statistic": "mean", "missing": "omit", "label": "Mean"}, "column": {"statistic": "sum", "missing": "omit", "label": "Sum"}}
        spec["dendrograms"] = {"row": {"label": "Height"}, "column": {"label": "Height"}}
        spec["tracks"] = {"marginal_mm": 16, "dendrogram_mm": 16}
        rowmeta = self.csv("row.csv", "key,genome\nnull,no\n001,yes\nNA,no\n")
        colmeta = self.csv("column.csv", "key,condition\nA,late\nB,early\n")
        rowtree, coltree = self.root / "row.json", self.root / "column.json"
        rowtree.write_text(json.dumps({"leaf_ids": ["NA", "null", "001"], "linkage": [[2, 0, 1, 2], [3, 1, 3, 3]]}))
        coltree.write_text(json.dumps({"leaf_ids": ["A", "B"], "linkage": [[1, 0, 2, 2]]}))
        inputs = {"row_metadata": rowmeta, "column_metadata": colmeta, "row_linkage": rowtree, "column_linkage": coltree}
        data, fig = self.draw(spec, **inputs)
        self.assertEqual(data["metadata"]["row"][0]["values"], ["yes", "no", "no"])
        self.assertEqual([r["value"] for r in data["marginals"]["row"]], [-2, 1, 5])
        self.assertEqual([r["observed_count"] for r in data["marginals"]["row"]], [1, 2, 1])
        self.assertEqual(data["marginals"]["row"][2]["unsupplied_count"], 1)
        self.assertEqual(matrix.audit_source_artists(self.source, spec, fig, **inputs)["status"], "pass")
        frame = fig._easyviz_aligned_frame
        self.assertEqual(frame.audit()["status"], "pass")
        # Measure actual centers after the compound layout, rather than trust requested boxes.
        for track in frame.tracks:
            ax = frame.axes[track["key"]]
            dimension = track["dimension"]
            points = [[0, 0], [1, 1]]
            coordinate = 1 if dimension == "row" else 0
            self.assertTrue(np.allclose(ax.transData.transform(points)[:, coordinate], frame.main.transData.transform(points)[:, coordinate], atol=1e-9))
        tree_artist = fig._easyviz_matrix_artists["trees"][0]["artist"]
        tree_artist.set_xdata(np.asarray(tree_artist.get_xdata()) + .5)
        bar = fig._easyviz_matrix_artists["marginals"][0]["artist"]
        bar.set_width(77)
        meta = fig._easyviz_matrix_artists["metadata"][0]["artist"]
        meta.set_facecolor("black")
        issues = {i["code"] for i in matrix.audit_source_artists(self.source, spec, fig, **inputs)["issues"]}
        self.assertTrue({"dendrogram_source_artist_mismatch", "marginal_source_artist_mismatch", "metadata_source_artist_mismatch"} <= issues)
        matrix.plt.close(fig)
        qa = matrix.render(self.source, spec, self.root / "export", **inputs)
        self.assertEqual(qa["status"], "pass")
        self.assertEqual(qa["source_to_artist_audit"]["alignment"]["status"], "pass")
        settings = json.loads((self.root / "export/settings.json").read_text())
        self.assertEqual(len(settings["inputs"]), 5)
        self.assertEqual(settings["typography"]["tick"], 8)
        self.assertEqual(settings["layout"]["actual_font"], "DejaVu Sans")
        for extension in ("png", "tiff"):
            with Image.open(self.root / f"export/panel.{extension}") as image:
                self.assertEqual(image.size, (round(120 / 25.4 * 100), round(105 / 25.4 * 100)))
        page = PdfReader(self.root / "export/panel.pdf").pages[0]
        self.assertAlmostEqual(float(page.mediabox.width) * 25.4 / 72, 120, places=5)
        elements = json.loads((self.root / "export/elements.json").read_text())
        self.assertTrue(any(e["role"] == "dendrogram-branch" for e in elements["elements"]))
        self.assertEqual(len([e for e in elements["elements"] if e["role"] == "aligned-axes"]), 7)
        meta_keys = [e for e in elements["elements"] if e["role"] == "legend-key" and any(p.startswith("/metadata/") for p in e["spec_paths"])]
        self.assertEqual(len(meta_keys), 4)
        self.assertFalse(any(p.startswith("/colors/") for e in meta_keys for p in e["spec_paths"]))

    def test_changed_schema_literal_whitespace_and_stable_ids_across_order(self):
        spec = deepcopy(self.spec)
        self.source = self.csv("alternate.csv", "Gene key,Batch label,Activity\n 001 ,alpha,1\nNA,alpha,3\n 001 ,null,2\nNA,null,4\n")
        spec["fields"] = {"row": "Gene key", "column": "Batch label", "value": "Activity"}
        spec["order"] = {"row": ["NA", " 001 "], "column": ["null", "alpha"]}
        _, first = self.draw(spec)
        ids = {(r["row"], r["column"]): r["artist"].get_gid() for r in first._easyviz_matrix_artists["cells"]}
        matrix.plt.close(first)
        spec["order"] = {"row": [" 001 ", "NA"], "column": ["alpha", "null"]}
        _, second = self.draw(spec)
        self.assertEqual(ids, {(r["row"], r["column"]): r["artist"].get_gid() for r in second._easyviz_matrix_artists["cells"]})
        self.assertEqual(matrix.audit_source_artists(self.source, spec, second)["status"], "pass")

    def test_invalid_states_duplicates_headers_and_missing_rules(self):
        bad = ["sender,partner,signal,availability\n001,B,0,unmeasured\nNA,A,0,observed\nnull,A,1,observed\n",
               "sender,partner,signal,availability\n001,B,1,observed\n001,B,2,observed\nNA,A,0,observed\nnull,A,1,observed\n",
               "sender,partner,signal,availability,signal\n001,B,1,observed,2\n",
               "sender,partner,signal,availability\n001,B,nan,observed\nNA,A,0,observed\nnull,A,1,observed\n"]
        for text in bad:
            with self.subTest(text=text), self.assertRaises(ValueError):
                matrix.prepare(self.csv("bad.csv", text), self.spec)
        spec = deepcopy(self.spec)
        spec["options"]["missing_cells"] = "error"
        with self.assertRaisesRegex(ValueError, "absent coordinates"): matrix.prepare(self.source, spec)
        spec["options"]["missing_cells"] = "unsupplied"
        spec["marginals"] = {"row": {"statistic": "mean", "missing": "error", "label": "Mean"}}
        with self.assertRaisesRegex(ValueError, "missing=error"): matrix.prepare(self.source, spec)
        spec["marginals"]["row"].pop("missing")
        with self.assertRaisesRegex(ValueError, "must be explicit"): matrix.prepare(self.source, spec)

    def test_metadata_joins_require_literal_unique_complete_keys(self):
        spec = deepcopy(self.spec)
        spec["metadata"] = {"row": {"id": "key", "tracks": [{"field": "g", "label": "Group", "colors": {"yes": "#0072B2"}}]}}
        for text in ("key,g\n1,yes\nNA,yes\nnull,yes\n", "key,g\n001,yes\n001,yes\nnull,yes\n", "key,g\n001,yes\nNA,yes\nnull,unknown\n"):
            with self.subTest(text=text), self.assertRaises(ValueError): matrix.prepare(self.source, spec, row_metadata=self.csv("metadata.csv", text))

    def test_supplied_tree_structure_order_heights_counts_and_singleton(self):
        order = ["001", "NA", "null"]
        good = {"leaf_ids": order, "linkage": [[0, 1, 1, 2], [3, 2, 2, 3]]}
        self.assertEqual(matrix.aligned_layers.supplied_linkage(good, order)["maximum_height"], 2)
        for rows in ([[0, 1, 1, 2], [0, 2, 2, 3]], [[0, 1, 1, 3], [3, 2, 2, 3]], [[0, 1, 2, 2], [3, 2, 1, 3]], [[1, 0, 1, 2], [3, 2, 2, 3]], [[True, 1, 1, 2], [3, 2, 2, 3]]):
            with self.subTest(rows=rows), self.assertRaises(ValueError): matrix.aligned_layers.supplied_linkage({"leaf_ids": order, "linkage": rows}, order)
        singleton = matrix.aligned_layers.supplied_linkage({"leaf_ids": ["NA"], "linkage": []}, ["NA"])
        self.assertEqual(singleton["branches"], [])
        zeros = matrix.aligned_layers.supplied_linkage({"leaf_ids": ["B", "A"], "linkage": [[0, 1, 0, 2]]}, ["B", "A"])
        self.assertEqual(zeros["maximum_height"], 0)

    def test_alignment_audit_detects_actual_domain_and_span_mutation(self):
        _, fig = self.draw()
        frame = fig._easyviz_aligned_frame
        frame.main.set_xlim(-.5, 9)
        self.assertIn("matrix_category_domain_mismatch", {i["code"] for i in frame.audit()["issues"]})
        frame.main.set_xlim(-.5, 1.5)
        track = frame.add_track("custom", "column", 3)
        self.assertEqual(frame.audit()["status"], "pass")
        track.set_xlim(-.5, 9)
        self.assertEqual(frame.audit()["status"], "needs_revision")
        track.set_xlim(-.5, 1.5)
        position = track.get_position().bounds
        track.set_position([position[0] + .05, *position[1:]])
        self.assertEqual(frame.audit()["status"], "needs_revision")

    def test_marginal_omit_rejects_all_missing_and_finite_input_overflow(self):
        spec = deepcopy(self.spec)
        spec["marginals"] = {"row": {"statistic": "sum", "missing": "omit", "label": "Sum"}}
        all_missing = self.csv("all-missing.csv", "sender,partner,signal,availability\n001,B,1,observed\nNA,A,0,observed\nnull,A,,unmeasured\n")
        with self.assertRaisesRegex(ValueError, "all-missing group"): matrix.prepare(all_missing, spec)
        overflow = self.csv("overflow.csv", "sender,partner,signal,availability\n001,B,1e308,observed\n001,A,1e308,observed\nNA,A,0,observed\nnull,A,1,observed\n")
        with self.assertRaisesRegex(ValueError, "overflowed"): matrix.prepare(overflow, spec)
        spec["marginals"]["row"]["statistic"] = "mean"
        data = matrix.prepare(overflow, spec)
        self.assertEqual(data["marginals"]["row"][0]["value"], 1e308)

    def test_infeasible_layout_fails_truthfully_without_font_or_canvas_change(self):
        spec = deepcopy(self.spec)
        spec["layout"].update(width_mm=22, height_mm=20, font_size_pt=12)
        out = self.root / "infeasible"
        with self.assertRaises(ValueError): matrix.render(self.source, spec, out)
        qa = json.loads((out / "qa.json").read_text())
        self.assertFalse(qa["valid_outputs"])
        self.assertIn(qa["status"], ("needs_revision", "failed"))
        self.assertEqual(spec["layout"]["width_mm"], 22)
        self.assertEqual(spec["layout"]["font_size_pt"], 12)

    def test_cli_contract_excludes_upstream_clustering(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--describe-spec"], capture_output=True, text=True, check=True)
        contract = json.loads(result.stdout)
        self.assertEqual(contract["chart"], "annotated_matrix")
        self.assertIn("linkage_file", contract)
        invalid = deepcopy(self.spec)
        invalid["options"]["cluster_rows"] = True
        with self.assertRaisesRegex(ValueError, "Unknown options"): matrix.validate_spec(invalid)


if __name__ == "__main__":
    unittest.main()
