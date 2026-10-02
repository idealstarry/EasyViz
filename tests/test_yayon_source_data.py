"""The new literature case must retain exact supplied numeric strings."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

BASE = Path(__file__).resolve().parents[1] / "evals/reproduce-inputs/yayon-cma"
loader = importlib.util.spec_from_file_location("yayon_prepare_test", BASE / "prepare.py")
prepare = importlib.util.module_from_spec(loader)
loader.loader.exec_module(prepare)


class YayonSourceDataTests(unittest.TestCase):
    def test_all_1430_source_strings_and_cells_match_workbook(self):
        workbook = BASE / "source-fig3.xlsx"
        rows, summaries, genes, regions = prepare.extract(workbook)
        with (BASE / "source-data.csv").open(newline="") as stream:
            actual = list(csv.reader(stream))[1:]
        with (BASE / "summary.csv").open(newline="") as stream:
            supplied = list(csv.reader(stream))[1:]
        self.assertEqual(actual, rows)
        self.assertEqual(supplied, summaries)
        self.assertEqual((len(rows), len(summaries), len(genes), len(regions)), (1300, 65, 65, 10))
        provenance = json.loads((BASE / "provenance.json").read_text())
        self.assertEqual(provenance["source_sha256"], hashlib.sha256(workbook.read_bytes()).hexdigest())
        self.assertFalse(provenance["author_code_used"])
        self.assertEqual(provenance["numeric_source_cells"], 1430)
        for name, digest in provenance["prepared_hashes"].items():
            self.assertEqual(hashlib.sha256((BASE / name).read_bytes()).hexdigest(), digest)

    def test_display_order_matches_independent_image_reading(self):
        provenance = json.loads((BASE / "provenance.json").read_text())
        observation = json.loads((BASE / "observable-reference.json").read_text())
        self.assertEqual(provenance["gene_order"], observation["gene_order_left_to_right"])
        self.assertEqual(len(observation["region_order_top_to_bottom"]), 10)


if __name__ == "__main__":
    unittest.main()
