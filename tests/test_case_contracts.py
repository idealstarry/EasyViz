"""Check scientific identifier handling on new inputs to the reusable cases."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def load_case(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


paired = load_case("easyviz_paired_case", "examples/create/paired-myeloid-remodeling/plot.py")
heatmap = load_case("easyviz_annotated_case", "examples/create/annotated-inhibition/plot.py")
portable_heatmap = load_case("easyviz_portable_annotated_case", "skills/easyviz/assets/recipes/annotated-heatmap/plot.py")


class CaseContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-case-contracts-")
        self.root = Path(self.temp.name)

    def tearDown(self):
        heatmap.plt.close("all")
        self.temp.cleanup()

    def test_paired_case_rejects_unnamed_records_before_pairing(self):
        source = pd.DataFrame({"cohort": ["C", "C"], "participant": ["001", "001"],
                               "year": [0, 2], "subtype": ["myC01", "myC01"], "score": [1., 3.]})
        for column in ("cohort", "participant", "subtype"):
            for missing in ("", "  ", None):
                with self.subTest(column=column, missing=missing):
                    invalid = source.copy()
                    invalid[column] = missing
                    with self.assertRaisesRegex(ValueError, f"{column} IDs must be nonempty"):
                        paired.pair_data(invalid, [{"cluster": 1}], ["C"], 2)

    def test_paired_case_retains_literal_and_leading_zero_ids(self):
        rows = [("NA", participant, year, "myC01", score)
                for participant in ("NA", "null", "001") for year, score in ((0, 1.), (2, 3.))]
        source = self.root / "paired.csv"
        pd.DataFrame(rows, columns=["cohort", "participant", "year", "subtype", "score"]).to_csv(source, index=False)
        data = pd.read_csv(source, keep_default_na=False, dtype={"participant": str})
        result = paired.pair_data(data, [{"cluster": 1}], ["NA"], 2)
        self.assertEqual(set(result.participant), {"NA", "null", "001"})
        self.assertEqual(len(result), 3)
        self.assertTrue(result.change.eq(2).all())

    def render_matrix(self, matrix, annotations):
        data = self.root / "matrix.csv"
        metadata = self.root / "annotations.csv"
        settings = self.root / "settings.json"
        data.write_text(matrix)
        metadata.write_text(annotations)
        config = json.loads((ROOT / "examples/create/annotated-inhibition/settings.json").read_text())
        config.update(selection_count=3, color_limits=[-1, 10], colorbar_ticks=[0, 5, 10], font="DejaVu Sans", dpi=120)
        for key in ("receiver_mean_limits", "receiver_mean_ticks", "sender_mean_limits", "sender_mean_ticks"):
            config.pop(key, None)
        settings.write_text(json.dumps(config))
        with redirect_stdout(io.StringIO()):
            heatmap.run(self.root / "output", data, metadata, settings)
        return self.root / "output"

    def test_heatmap_exports_literal_and_leading_zero_ids_unchanged(self):
        out = self.render_matrix("sender,NA,null,001\nNA,1,2,3\nnull,4,5,6\n001,7,8,9\n",
                                 "strain,genome\nNA,1\nnull,0\n001,1\n")
        self.assertEqual(json.loads((out / "qa.json").read_text())["status"], "pass")
        data = pd.read_csv(out / "plotting-data.csv", dtype={"sender": str, "receiver": str}, keep_default_na=False)
        self.assertEqual(set(data.sender), {"NA", "null", "001"})
        self.assertEqual(set(data.receiver), {"NA", "null", "001"})
        lookup = data.set_index(["sender", "receiver"]).gii_min
        self.assertEqual(lookup.loc[("NA", "001")], 3)
        self.assertEqual(lookup.loc[("001", "NA")], 7)
        self.assertEqual(len(data), 9)

    def test_heatmap_rejects_empty_identifiers(self):
        for blank in ("", "  "):
            cases = [
                (f"sender,A,B,{blank}\nA,1,2,3\nB,4,5,6\nC,7,8,9\n", "strain,genome\nA,1\nB,0\nC,1\n", "Matrix column"),
                (f"sender,A,B,C\nA,1,2,3\nB,4,5,6\n{blank},7,8,9\n", "strain,genome\nA,1\nB,0\nC,1\n", "Matrix row"),
                ("sender,A,B,C\nA,1,2,3\nB,4,5,6\nC,7,8,9\n", f"strain,genome\nA,1\nB,0\n{blank},1\n", "Annotation strain"),
            ]
            for matrix, annotations, role in cases:
                with self.subTest(role=role, blank=blank):
                    with self.assertRaisesRegex(ValueError, f"{role} IDs must be nonempty"):
                        self.render_matrix(matrix, annotations)

    def test_heatmap_zero_centered_scale_has_original_unit_inverse(self):
        config = json.loads((ROOT / "examples/create/annotated-inhibition/settings.json").read_text())
        raw = np.array([-400., -200., 0., 250., 500., 1000.])
        expected = np.array([0., .25, .5, .625, .75, 1.])
        # Exercise the development and distributable implementations separately.
        for recipe in (heatmap, portable_heatmap):
            with self.subTest(recipe=recipe.__name__):
                norm, cmap, contract = recipe.color_scale(config, raw)
                np.testing.assert_allclose(norm(raw), expected)
                np.testing.assert_allclose(norm.inverse(expected), raw)
                self.assertTrue(np.all(np.diff(norm(np.linspace(-400, 1000, 1001))) > 0))
                np.testing.assert_allclose(cmap(norm(0)), [1, 1, 1, 1])
                self.assertEqual(contract["neutral_normalized_position"], .5)
                self.assertFalse(contract["clip"])
                luminance = contract["branch_luminance_check"]
                self.assertTrue(luminance["negative_arm_nondecreasing"])
                self.assertTrue(luminance["positive_arm_nonincreasing"])
                self.assertEqual(luminance["zero_relative_luminance"], 1)
                np.testing.assert_allclose(cmap(norm(250)), heatmap.matplotlib.colors.to_rgba("#FFD168"))
                for value in (-400.01, 1000.01):
                    with self.assertRaisesRegex(ValueError, "clip measurements"):
                        recipe.color_scale(config, [value, 0])
                invalid = dict(config, color_limits=[0, 1000])
                with self.assertRaisesRegex(ValueError, "center must be strictly inside"):
                    recipe.color_scale(invalid, [0, 250, 1000])


if __name__ == "__main__":
    unittest.main()
