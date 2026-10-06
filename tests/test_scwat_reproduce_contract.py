"""Contracts that prevent broken-axis rendering from concealing user data."""
import csv
import importlib.util
import io
import json
from pathlib import Path
import unittest


CASE = Path(__file__).resolve().parents[1] / "examples/reproduce/scwat-broken-axis"
loader = importlib.util.spec_from_file_location("scwat_contract", CASE / "plot.py")
plot = importlib.util.module_from_spec(loader)
loader.loader.exec_module(plot)
validator_loader = importlib.util.spec_from_file_location("scwat_export_validator", CASE / "validate.py")
validator = importlib.util.module_from_spec(validator_loader)
validator_loader.loader.exec_module(validator)


class ScwatReproductionContractTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads((CASE / "spec.json").read_text())
        self.rows = list(csv.DictReader(io.StringIO((CASE / "inputs/observations.csv").read_text())))

    def raw(self):
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=list(self.rows[0]))
        writer.writeheader(); writer.writerows(self.rows)
        return stream.getvalue().encode()

    def test_source_observations_are_not_assumed_to_pair_across_genes(self):
        rows, summary = plot.parse(self.raw(), self.spec)
        self.assertEqual(len(rows), 60)
        self.assertEqual(len(summary), 12)
        self.assertTrue(all(item["n"] == 5 for item in summary))
        self.assertEqual(len({row["observation_id"] for row in rows}), 60)
        self.assertTrue(all(item["observation_ids"] == [row["observation_id"] for row in rows
                        if row["gene"] == item["gene"] and row["group"] == item["group"]] for item in summary))

    def test_raw_value_in_omitted_numeric_interval_is_rejected(self):
        self.rows[0]["relative_expression"] = "20"
        with self.assertRaisesRegex(ValueError, "would disappear"):
            plot.parse(self.raw(), self.spec)

    def test_raw_values_can_be_visible_while_sem_endpoint_would_disappear(self):
        # All measurements fit one of the displayed segments; their sample
        # mean is low but its upper SEM lies inside the omitted interval.
        # Merely checking the range of individual data would miss this.
        selected = [row for row in self.rows if row["gene"] == "ucp1" and row["group"] == "YT-FF"]
        for row, value in zip(selected, [1, 1, 1, 1, 40]):
            row["relative_expression"] = str(value)
        with self.assertRaisesRegex(ValueError, "would disappear"):
            plot.parse(self.raw(), self.spec)

    def test_duplicate_identity_and_partial_category_table_are_rejected(self):
        self.rows[1]["observation_id"] = self.rows[0]["observation_id"]
        with self.assertRaisesRegex(ValueError, "identities"):
            plot.parse(self.raw(), self.spec)
        self.rows = list(csv.DictReader(io.StringIO((CASE / "inputs/observations.csv").read_text())))[:5]
        with self.assertRaisesRegex(ValueError, "domain"):
            plot.parse(self.raw(), self.spec)

    def test_bar_boundaries_have_positive_internal_and_external_gaps(self):
        self.spec["style"]["bar_gap"] = 0
        with self.assertRaisesRegex(ValueError, "visible pair gap"):
            plot.parse(self.raw(), self.spec)

    def test_invalid_p_bounds_cannot_produce_significance_stars(self):
        for value in ("< -0.01", "< 0", "< NaN", "< inf", "< 2", "-0.1", "nan", "1.1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                plot.p_class(value)
        self.assertEqual(plot.p_class("< 0.0001"), "***")
        self.assertEqual(plot.p_class("< 0.005"), "**")
        self.assertEqual(plot.p_class("0.208988"), "")
        self.assertEqual(plot.p_class("0.01"), "*")

    def test_missing_or_duplicate_summary_cannot_pass_an_export_audit(self):
        domain = [{"gene": gene, "group": group} for gene in self.spec["gene_order"] for group in self.spec["group_order"]]
        validator.validate_summary_domain(self.rows, domain)
        for records in ([], domain[:-1], [*domain, domain[0]], [*domain[:-1], {"gene": "invented", "group": "YT-AKO"}]):
            with self.subTest(records=records), self.assertRaisesRegex(ValueError, "summary identities"):
                validator.validate_summary_domain(self.rows, records)


if __name__ == "__main__":
    unittest.main()
