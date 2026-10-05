#!/usr/bin/env python3
"""Exercise this case's captured-byte drawing and refusal after replacement."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
CASE = ROOT / "examples/create/pathway-signatures"
HERE = Path(__file__).resolve().parent


def main():
    destination = HERE / "continuity-probe"
    if destination.exists():
        raise FileExistsError("Preserve the earlier probe; select a fresh directory in this script.")
    destination.mkdir()
    tools = destination / "runtime"; tools.mkdir()
    for name in ("render.py", "legend_layout.py", "figure_profile.py", "auto_layout.py",
                 "annotation_review.py", "figure_elements.py", "panel_readability.py"):
        shutil.copy2(ROOT / "skills/easyviz/scripts" / name, tools / name)
    for source, name in ((CASE / "inputs/coefficients.csv", "source.csv"),
                         (CASE / "inputs/input-contract.json", "contract.json"),
                         (CASE / "spec.json", "spec.json")):
        shutil.copy2(source, destination / name)
    loader = importlib.util.spec_from_file_location("signature_case_capture_probe", CASE / "plot.py")
    case = importlib.util.module_from_spec(loader); loader.loader.exec_module(case)
    args = SimpleNamespace(data=destination / "source.csv", spec=destination / "spec.json",
                           contract=destination / "contract.json", out=destination / "actual-export")
    args.out.mkdir()
    capture, handoff, core, bindings, executed = case.prepare_capture(args, tools.resolve())
    spec = core.parse_spec_bytes(capture.read("spec_file"))
    contract = core.parse_spec_bytes(capture.read_auxiliary("source_contract"))
    data_original = args.data.read_bytes()
    # A separately reopened CSV would now fail. This case still calculates and
    # draws from its valid captured bytes, preserving every source coordinate.
    args.data.write_bytes(data_original + b"NOT_A_VALID_COEFFICIENT_ROW\n")
    figure, layout, _, rc = case.draw(spec, contract, args.data, args.spec, core, capture, bindings)
    try:
        with case.plt.rc_context(rc): core.export(figure, args.out, spec, layout)
        identical = {extension: (args.out / f"panel.{extension}").read_bytes() ==
                     (HERE / "before-rebind/output" / f"panel.{extension}").read_bytes()
                     for extension in ("png", "pdf", "svg")}
        if not all(identical.values()): raise AssertionError("Captured-source drawing changed reviewed bytes")
        rejections = []
        for role, path, original in (("data_file", args.data, data_original),
                                    ("source_contract", args.contract, args.contract.read_bytes()),
                                    ("helper:figure_elements.py", tools / "figure_elements.py", (tools / "figure_elements.py").read_bytes())):
            if role != "data_file": path.write_bytes(original + b"\n")
            try:
                handoff.write_receipt(args.out, capture=capture, formats=spec["formats"], resolved_spec=spec, track="create")
            except handoff.HandoffError as error:
                if (args.out / "handoff.json").exists(): raise AssertionError("Rejected capture published a receipt")
                rejections.append({"role": role, "status": "refused_before_receipt", "reason": str(error)})
            else:
                raise AssertionError(f"Changed source was accepted: {role}")
            finally:
                path.write_bytes(original)
        record = {"status": "passed", "scope": "Actual case export from captured CSV despite invalid current file; independent helper refuses stale primary/contract/helper before receipt publication.",
                  "candidate_byte_identical": identical, "visual_pass_number": 3, "new_aesthetic_pass": False,
                  "captured_csv_sha256": hashlib.sha256(capture.read("data_file")).hexdigest(), "rejections": rejections}
        (HERE / "continuity-evidence.json").write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps(record))
    finally:
        case.plt.close(figure)


if __name__ == "__main__": main()
