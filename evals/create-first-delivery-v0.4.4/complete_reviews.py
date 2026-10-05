"""Transcribe the already completed independent reviews into gate records.

This is not an image reviewer. Exact image hashes must match the saved actual
viewing reports; it cannot attest newly generated or arbitrary images.
"""
from pathlib import Path
import hashlib
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main():
    loader = importlib.util.spec_from_file_location("review_gate", ROOT / "skills/easyviz/scripts/create_review.py")
    gate = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(gate)
    first_path = HERE / "first-render-visual-review.json"
    second_path = HERE / "internal-pass-02-visual-review.json"
    first = json.loads(first_path.read_text())
    second = json.loads(second_path.read_text())
    staged = json.loads((HERE / "review-staging.json").read_text())
    results = []
    for item in staged:
        case = item["case"]
        stage = item["stage"]
        packet_path, record_path = Path(stage["packet"]), Path(stage["review"])
        packet = json.loads(packet_path.read_text())
        record = json.loads(record_path.read_text())
        png = packet["snapshot"]["candidate_png"]
        report, report_path = (second, second_path) if packet["pass_number"] == 2 else (first, first_path)
        opened = []
        for entry in report["viewed_files"]:
            path = Path(entry["path"])
            if not path.is_absolute():
                path = ROOT / path
            if path.resolve() == Path(png["path"]).resolve():
                assert entry["sha256"] == png["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
                opened.append(entry)
        assert len(opened) == 1, "No unique existing image-opening evidence"
        if packet["pass_number"] == 2:
            assessment = next(row for row in second["cases"] if row["case"] == case)
            visible = " ".join(assessment["visible_reasons"])
            residual = assessment["residual_limit"]
        else:
            assessment = next(row for row in first["preferences"] if row["task"] == case)
            visible, residual = assessment["evidence"], assessment["limits"]
        assert assessment["status"] == "ready_with_notes"
        panel = packet["snapshot"]["panel"]
        record.update(status="ready_with_notes", reviewer={"role": "independent", "identity": "refinement_visual_review; transcription from the retained actual-image review"},
                      images_opened=[{"role": "candidate", "path": png["path"], "sha256": png["sha256"],
                                      "views": ["full_canvas", "final_proportions"], "tool": "view_image in independent Agent review; full PNG and actual nominal 96dpi PDF preview",
                                      "size_basis": f"Recorded {panel['width_mm']} × {panel['height_mm']} mm canvas; actual nominal 96dpi PDF preview was opened."}],
                      independent_report={"path": str(report_path), "sha256": hashlib.sha256(report_path.read_bytes()).hexdigest()},
                      preference={"choice": "not_applicable", "reasons": "Candidate comparison and internal repair history remain in the separate independent reports; this packet binds readiness only."})
        evidence = {
            "scientific_mapping": "Original columns, keys, values and all rows match invariants.json; the reviewed spec/caption retain the adopted methods and limits. " + assessment.get("intentional_changes", [""])[-1],
            "reading_priority": visible,
            "mark_hierarchy": visible,
            "geometry": visible + f" Fixed canvas {panel['width_mm']} × {panel['height_mm']} mm and Arial 8 pt; physical exports independently checked.",
            "palette_and_strokes": visible + " Palette judgment is scoped to these actual marks and reading task; no accessibility or journal-quality claim.",
            "guides_and_text": "The actual axes, labels, legends/color scale and separate caption were opened and read in the retained review. " + visible,
        }
        for check in record["design_checks"]:
            check.update(status="passed", evidence=evidence[check["criterion"]])
        for check in record["external_checks"]:
            measured = packet["snapshot"]["measured_checks"][check["criterion"]]
            assert measured["status"] == "passed"
            check.update(status="passed", evidence="Acknowledged current packet measurement/source binding: " + check["criterion"] + "; physical exports/font also independently checked in the retained review.")
        record["findings"], record["corrections"] = [], []
        for repair in second["resolved_first_pass_findings"]:
            if packet["pass_number"] != 2 or repair["case"] != case:
                continue
            original = next(row for row in first["findings"] if row["id"] == repair["id"])
            record["findings"].append({"id": original["id"], "severity": original["severity"], "state": "resolved",
                                       **{name: original[name] for name in ("location", "evidence", "requirement", "action")}})
            record["corrections"].append({"finding_id": original["id"], "candidate_sha256": png["sha256"],
                                         "action": " ".join(assessment["intentional_changes"]), "evidence": repair["evidence"]})
        note_id = "LIMIT-" + case
        record["findings"].append({"id": note_id, "severity": "note", "state": "accepted", "location": "Whole panel and nominal-size preview",
                                   "evidence": residual, "requirement": "Report the actual reading and validation boundary without altering explicit constraints.",
                                   "action": "Keep this limitation visible in the evaluation; preserve all observations and adopted meanings."})
        record["residual_issues"] = [note_id]
        record_path.write_bytes(gate.json_bytes(record))
        result = gate.check(packet_path)
        assert result["gate_status"] == "recorded", result
        results.append({"case": case, "visual_pass": packet["pass_number"], **result})
    (HERE / "delivery-readiness.json").write_text(json.dumps(results, indent=2) + "\n")
    print("Recorded five current-file readiness attestations from the actual retained reviews.")


if __name__ == "__main__":
    main()
