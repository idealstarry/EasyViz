"""Actual exports retain later-correction history without a first-delivery claim."""
from pathlib import Path
import unittest

import test_create_review as base


class FollowupReviewTests(unittest.TestCase):
    setUp = base.CreateReviewTests.setUp
    tearDown = base.CreateReviewTests.tearDown
    read = staticmethod(base.CreateReviewTests.read)
    write = staticmethod(base.CreateReviewTests.write)
    recorded_fixture = base.CreateReviewTests.recorded_fixture

    def followup(self, **overrides):
        prior = self.root / "prior-review.json"
        if not prior.exists():
            self.write(prior, {"visual_passes": 3, "findings": ["Observed overlapping mean glyphs"]})
        options = dict(pass_number=4, phase="followup", prior_review=prior,
                       followup_reason="Continue the independently observed mean-visibility correction.")
        options.update(overrides)
        return base.gate.stage(self.figure, "Read the supplied measurements.", caption=self.caption, **options)

    def test_later_correction_is_recorded_separately_with_cumulative_count(self):
        staged = self.followup()
        packet = self.read(staged["packet"])
        self.assertIn("followup-review/pass-04", staged["packet"])
        self.assertEqual(packet["pass_number"], 4)
        self.assertFalse(packet["first_delivery_claim"])
        self.assertEqual(packet["followup"]["previous_pass_number"], 3)
        self.recorded_fixture(staged)
        result = base.gate.check(staged["packet"])
        self.assertEqual(result["gate_status"], "recorded", result)
        self.assertEqual(result["delivery_phase"], "followup")
        self.assertFalse(result["first_delivery_claim"])

    def test_prior_evidence_and_actual_current_exports_remain_bound(self):
        staged = self.followup()
        self.recorded_fixture(staged)
        prior = self.root / "prior-review.json"
        original = prior.read_bytes()
        prior.write_text('{"visual_passes": 2}')
        with self.assertRaisesRegex(base.gate.ReviewError, "evidence changed"):
            base.gate.check(staged["packet"])
        prior.write_bytes(original)
        self.caption.write_text("Changed caption after the recorded correction.")
        result = base.gate.check(staged["packet"])
        self.assertEqual(result["gate_status"], "blocked")
        self.assertIn("changed since staging", "\n".join(result["errors"]))

    def test_followup_cannot_reset_history_or_upgrade_technical_failures(self):
        for overrides in ({"pass_number": 1}, {"followup_reason": ""}, {"prior_review": None},
                          {"phase": "first_delivery"}):
            with self.subTest(overrides=overrides), self.assertRaises(base.gate.ReviewError):
                self.followup(**overrides)
        staged = self.followup()
        self.recorded_fixture(staged)
        qa_path = self.figure / "qa.json"
        qa = self.read(qa_path)
        qa.update(status="fail", valid_outputs=False)
        self.write(qa_path, qa)
        result = base.gate.check(staged["packet"])
        self.assertEqual(result["gate_status"], "blocked")
        self.assertIn("technical_qa", "\n".join(result["errors"]))

    def test_first_delivery_keeps_original_packet_shape_and_limit(self):
        staged = base.gate.stage(self.figure, "Read the source observations.", caption=self.caption)
        packet = self.read(staged["packet"])
        self.assertNotIn("followup", packet)
        self.assertNotIn("delivery_phase", packet)
        with self.assertRaisesRegex(base.gate.ReviewError, "1, 2 or 3"):
            base.gate.stage(self.figure, "Read the source observations.", pass_number=4)


if __name__ == "__main__":
    unittest.main()
