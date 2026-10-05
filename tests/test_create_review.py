"""Create delivery review must bind actual exports and recorded evidence.

Uses the real exporter, rather than fabricated success-only QA fixtures. The
helper validates attestations; these tests never claim that an image was seen.
"""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"


def module(name, path):
    loader = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(result)
    return result


gate = module("easyviz_create_review_test", SCRIPTS / "create_review.py")
renderer = module("easyviz_create_review_renderer", SCRIPTS / "render.py")


class CreateReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-create-review-")
        self.root = Path(self.temp.name).resolve()
        self.data = self.root / "input.csv"
        self.data.write_text("x,y\n1,2\n2,3\n3,5\n4,4\n", encoding="utf-8")
        self.caption = self.root / "caption.md"
        self.caption.write_text("Observed input and output values; each point is one observation.\n", encoding="utf-8")
        self.spec = {"chart": "scatter", "fields": {"x": "x", "y": "y"},
                     "labels": {"x": "Input", "y": "Output"},
                     "layout": {"width_mm": 88, "height_mm": 66, "dpi": 120, "font": "DejaVu Sans"},
                     "formats": ["pdf", "svg", "png", "tiff"], "seed": 17}
        self.spec_path = self.root / "spec.json"
        self.write(self.spec_path, self.spec)
        self.figure = self.root / "output"
        renderer.render(self.data, deepcopy(self.spec), self.figure, spec_path=self.spec_path, track="create")

    def tearDown(self):
        renderer.plt.close("all")
        self.temp.cleanup()

    @staticmethod
    def write(path, value):
        path.write_bytes(gate.json_bytes(value))

    @staticmethod
    def read(path):
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def stage(self, **kwargs):
        return gate.stage(self.figure, "Read the association between input and output.", caption=self.caption, **kwargs)

    def recorded_fixture(self, staged):
        """A test attestation, not a claim of actual visual review by this test."""
        packet = self.read(staged["packet"])
        record = self.read(staged["review"])
        candidate = packet["snapshot"]["candidate_png"]
        record.update(status="ready", reviewer={"role": "self-review", "identity": "Test attestation fixture"},
                      images_opened=[{"role": "candidate", "path": candidate["path"], "sha256": candidate["sha256"],
                                      "views": ["full_canvas", "final_proportions"], "tool": "Test fixture only",
                                      "size_basis": "Fixture records the 88 x 66 mm intended proportions; no real viewing claimed."}])
        observations = {
            "scientific_mapping": "Input and Output axes use the adopted raw x/y variables.",
            "reading_priority": "Raw points are the primary layer for the association reading task.",
            "mark_hierarchy": "The adopted scatter has one raw point layer and no competing summary.",
            "geometry": "The 88 x 66 mm canvas has four observation locations within the axes.",
            "palette_and_strokes": "Single-category scatter uses one mark treatment on a white background.",
            "guides_and_text": "Axis names are present and no unrequested in-image prose was adopted.",
        }
        for item in record["design_checks"]:
            item.update(status="passed", evidence=observations[item["criterion"]])
        for item in record["external_checks"]:
            item.update(status="passed", evidence="Acknowledged packet snapshot.measured_checks." + item["criterion"])
        self.write(Path(staged["review"]), record)
        return record

    def assert_blocked(self, staged, phrase):
        result = gate.check(staged["packet"])
        self.assertEqual(result["gate_status"], "blocked")
        self.assertIn(phrase, "\n".join(result["errors"]))
        return result

    def test_real_export_can_finish_on_first_pass_without_reference_or_baseline(self):
        staged = self.stage()
        packet = self.read(staged["packet"])
        self.assertEqual(staged["measured_checks"], {key: "passed" for key in gate.MEASURED_CRITERIA})
        self.assertEqual(packet["snapshot"]["candidate_png"]["path"], str(self.figure / "panel.png"))
        self.assertEqual(packet["snapshot"]["source_bindings"]["spec_file"][0]["path"], str(self.spec_path))
        self.assertIsNone(packet["snapshot"]["baseline_png"])
        self.assert_blocked(staged, "not ready")
        record = self.recorded_fixture(staged)
        result = gate.check(staged["packet"])
        self.assertEqual(result["gate_status"], "recorded", result)
        self.assertIn("cannot prove", result["limitation"])
        self.stage()  # Restaging identical artifacts preserves completed review.
        self.assertEqual(self.read(staged["review"]), record)

    def test_export_replay_invalidates_prior_attestation_even_when_qa_still_passes(self):
        staged = self.stage()
        self.recorded_fixture(staged)
        spec = deepcopy(self.spec)
        spec["options"] = {"point_area_pt2": 25, "point_style": "hollow"}
        self.write(self.spec_path, spec)
        renderer.render(self.data, spec, self.figure, spec_path=self.spec_path, track="create")
        self.assertEqual(self.read(self.figure / "qa.json")["status"], "pass")
        self.assert_blocked(staged, "changed since staging")
        with self.assertRaisesRegex(gate.ReviewError, "different packet"):
            self.stage()
        next_stage = self.stage(pass_number=2)
        self.recorded_fixture(next_stage)
        self.assertEqual(gate.check(next_stage["packet"])["gate_status"], "recorded")
        with self.assertRaisesRegex(gate.ReviewError, "1, 2 or 3"):
            self.stage(pass_number=4)

    def test_source_data_and_saved_spec_changes_are_stale_before_another_render(self):
        for path, changed in ((self.data, b"x,y\n1,2\n2,3\n3,99\n4,4\n"),
                              (self.spec_path, gate.json_bytes({**self.spec, "labels": {"x": "Changed input"}}))):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                staged = self.stage(out=self.root / ("review-" + path.stem))
                self.recorded_fixture(staged)
                path.write_bytes(changed)
                result = self.assert_blocked(staged, "changed since staging")
                self.assertIn("source_provenance", "\n".join(result["errors"]))
                path.write_bytes(original)

    def test_recorded_source_script_is_hashed_without_guessing_bundled_location(self):
        # Relocate the actual recorded source bytes, as in a copied writable case.
        source = self.root / "copied-renderer.py"
        shutil.copyfile(SCRIPTS / "render.py", source)
        manifest = self.read(self.figure / "elements.json")
        manifest["input"]["source_script"] = str(source)
        self.write(self.figure / "elements.json", manifest)
        staged = self.stage()
        self.recorded_fixture(staged)
        self.assertEqual(gate.check(staged["packet"])["gate_status"], "recorded")
        source.write_text(source.read_text() + "\n# meaningful source revision\n", encoding="utf-8")
        self.assert_blocked(staged, "changed since staging")

    def test_changed_shared_figure_profile_invalidates_the_reviewed_specification(self):
        profile = self.root / "figure-profile.json"
        settings = {"version": 1, "layout": {"font": "DejaVu Sans", "font_size_pt": 8, "line_width_pt": .6, "dpi": 120},
                    "panels": {"primary": {"width_mm": 88, "height_mm": 66}}}
        self.write(profile, settings)
        spec = deepcopy(self.spec)
        spec.pop("layout")
        spec.update(profile=str(profile), panel="primary")
        self.write(self.spec_path, spec)
        renderer.render(self.data, spec, self.figure, spec_path=self.spec_path, track="create")
        staged = self.stage()
        self.recorded_fixture(staged)
        self.assertEqual(gate.check(staged["packet"])["gate_status"], "recorded")
        settings["panels"]["primary"]["width_mm"] = 110
        self.write(profile, settings)
        self.assert_blocked(staged, "changed since staging")

    def test_required_measured_evidence_cannot_be_upgraded_by_a_review_status(self):
        qa = self.read(self.figure / "qa.json")
        qa["exports"]["png"]["pixels"] = [200, 200]
        self.write(self.figure / "qa.json", qa)
        staged = self.stage()
        self.assertEqual(staged["measured_checks"]["export_dimensions"], "failed")
        self.recorded_fixture(staged)
        self.assert_blocked(staged, "attestation cannot upgrade")

    def test_pre_stage_corrupt_pdf_cannot_reuse_old_page_measurements(self):
        qa = self.read(self.figure / "qa.json")
        pdf = self.figure / "panel.pdf"
        self.assertEqual(qa["exports"]["pdf"]["sha256"], gate.digest(pdf.read_bytes()))
        pdf.write_bytes(b"%PDF-1.7\ninvalid page bytes")
        self.assertEqual(self.read(self.figure / "qa.json"), qa)
        staged = self.stage()
        self.assertEqual(staged["measured_checks"]["export_dimensions"], "failed")
        bindings = self.read(staged["packet"])["snapshot"]["measured_checks"]["export_dimensions"]["evidence"]["format_bindings"]
        self.assertEqual(bindings["pdf"]["status"], "failed")
        self.assertNotEqual(bindings["pdf"]["recorded_sha256"], bindings["pdf"]["actual_sha256"])
        self.recorded_fixture(staged)
        self.assert_blocked(staged, "attestation cannot upgrade")

    def test_pre_stage_replaced_tiff_fails_even_when_pixel_dimensions_still_match(self):
        alternative = self.root / "alternative-export"
        spec = deepcopy(self.spec)
        spec["options"] = {"point_area_pt2": 25, "point_style": "hollow"}
        renderer.render(self.data, spec, alternative, track="create")
        original_qa = self.read(self.figure / "qa.json")
        other_qa = self.read(alternative / "qa.json")
        self.assertEqual(original_qa["exports"]["tiff"]["pixels"], other_qa["exports"]["tiff"]["pixels"])
        self.assertEqual(original_qa["exports"]["tiff"]["dpi"], other_qa["exports"]["tiff"]["dpi"])
        shutil.copyfile(alternative / "panel.tiff", self.figure / "panel.tiff")
        staged = self.stage()
        self.assertEqual(staged["measured_checks"]["export_dimensions"], "failed")
        self.recorded_fixture(staged)
        self.assert_blocked(staged, "attestation cannot upgrade")

    def test_pdf_and_tiff_measurements_without_export_hashes_remain_unchecked(self):
        original = self.read(self.figure / "qa.json")
        for extension in ("pdf", "tiff"):
            with self.subTest(extension=extension):
                qa = deepcopy(original)
                del qa["exports"][extension]["sha256"]
                self.write(self.figure / "qa.json", qa)
                staged = self.stage(out=self.root / ("unbound-" + extension))
                self.assertEqual(staged["measured_checks"]["export_dimensions"], "not_checked")
                self.recorded_fixture(staged)
                self.assert_blocked(staged, "attestation cannot upgrade")

    def test_png_and_svg_are_directly_measured_without_optional_export_hashes(self):
        spec = deepcopy(self.spec)
        spec["formats"] = ["png", "svg"]
        self.write(self.spec_path, spec)
        renderer.render(self.data, spec, self.figure, spec_path=self.spec_path, track="create")
        qa = self.read(self.figure / "qa.json")
        for extension in spec["formats"]:
            del qa["exports"][extension]["sha256"]
        self.write(self.figure / "qa.json", qa)
        staged = self.stage()
        self.assertEqual(staged["measured_checks"]["export_dimensions"], "passed")
        self.recorded_fixture(staged)
        self.assertEqual(gate.check(staged["packet"])["gate_status"], "recorded")

    def test_missing_custom_source_and_qa_stage_honestly_but_cannot_pass(self):
        custom = self.root / "custom"
        custom.mkdir()
        shutil.copyfile(self.figure / "panel.png", custom / "panel.png")
        staged = gate.stage(custom, "Read supplied values.", caption=self.caption)
        self.assertEqual(staged["measured_checks"]["source_provenance"], "not_checked")
        self.assertEqual(staged["measured_checks"]["technical_qa"], "not_checked")
        self.recorded_fixture(staged)
        self.assert_blocked(staged, "attestation cannot upgrade")

    def test_caption_is_explicit_and_missing_external_caption_is_not_guessed(self):
        staged = gate.stage(self.figure, "Read the association.")
        self.assertEqual(staged["measured_checks"]["caption"], "not_checked")
        self.recorded_fixture(staged)
        self.assert_blocked(staged, "caption")
        explicit = self.stage(out=self.root / "explicit-caption")
        self.recorded_fixture(explicit)
        self.assertEqual(gate.check(explicit["packet"])["gate_status"], "recorded")
        self.caption.write_text("Changed interpretation after review.\n", encoding="utf-8")
        self.assert_blocked(explicit, "changed since staging")

    def test_unresolved_findings_and_forged_vocabulary_cannot_hide_behind_ready(self):
        staged = self.stage()
        base = self.recorded_fixture(staged)
        finding = {"id": "f1", "severity": "major", "state": "open", "location": "Y axis",
                   "evidence": "Required unit was omitted.", "requirement": "Record units", "action": "Add the adopted unit and rerender."}
        mutations = (
            ({"findings": [finding], "residual_issues": []}, "Unresolved major"),
            ({"status": "certified"}, "Unknown readiness"),
            ({"status": {}}, "Unknown readiness"),
            ({"packet_sha256": "0" * 64}, "different packet hash"),
            ({"policy_version": "0.4.3"}, "policy version"),
            ({"findings": [{**finding, "severity": "optional_major"}]}, "Unknown finding severity"),
        )
        for update, expected in mutations:
            with self.subTest(expected=expected):
                self.write(Path(staged["review"]), {**deepcopy(base), **update})
                self.assert_blocked(staged, expected)
        record = deepcopy(base)
        record["design_checks"][0]["status"] = "pass"
        self.write(Path(staged["review"]), record)
        self.assert_blocked(staged, "Unknown check status")

    def test_notes_and_comparison_preference_are_separate_from_readiness(self):
        staged = self.stage()
        record = self.recorded_fixture(staged)
        note = {"id": "n1", "severity": "note", "state": "accepted", "location": "Right margin",
                "evidence": "The remaining margin is intentional.", "requirement": "Optional spacing preference", "action": "Retain the adopted dimensions."}
        record.update(status="ready_with_notes", findings=[note], residual_issues=["n1"])
        record["preference"] = {"choice": "not_applicable", "reasons": "No baseline was required for the first draft."}
        self.write(Path(staged["review"]), record)
        self.assertEqual(gate.check(staged["packet"])["gate_status"], "recorded")
        record["preference"] = {"choice": "candidate", "reasons": "Claimed improvement without an available comparison."}
        self.write(Path(staged["review"]), record)
        self.assert_blocked(staged, "requires an available baseline")

    def test_symlinked_export_is_not_read_as_a_scoped_figure_artifact(self):
        actual = self.root / "actual.png"
        shutil.move(self.figure / "panel.png", actual)
        (self.figure / "panel.png").symlink_to(actual)
        with self.assertRaisesRegex(gate.ReviewError, "symlink"):
            self.stage()


if __name__ == "__main__":
    unittest.main()
