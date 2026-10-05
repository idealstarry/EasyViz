#!/usr/bin/env python3
"""Exercise copied cases and real source/bytecode refusal paths."""
from __future__ import annotations
import csv
import hashlib
import io
import importlib.util
import json
import os
from pathlib import Path
import py_compile
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULTS = []


def mutate_rows(path, mutation):
    raw = path.read_bytes()
    values = list(csv.reader(io.StringIO(raw.decode(), newline="")))
    mutation(values)
    buffer = io.StringIO(newline="")
    csv.writer(buffer).writerows(values)
    path.write_text(buffer.getvalue())


def run_case(case, check, mutation=None, stale=False, font=None):
    authoritative = ROOT / "examples/no-author-code" / case
    revision = authoritative / "revision-v0.4.6"
    with tempfile.TemporaryDirectory(prefix="easyviz-reproduce-case-probe-") as temp:
        copy = Path(temp) / "case"
        (copy / "inputs").mkdir(parents=True)
        (copy / "revision-v0.4.6").mkdir()
        data = copy / "inputs/source-data.csv"
        shutil.copy2(authoritative / "inputs/source-data.csv", data)
        script = copy / "revision-v0.4.6/plot.py"
        for name in ("plot.py", "adopted-spec.json"):
            shutil.copy2(revision / name, script.with_name(name))
        if mutation:
            mutate_rows(data, mutation)
        output = copy / "revision-v0.4.6/output"
        if stale:
            py_compile.compile(str(script), doraise=True)
            stat = script.stat()
            content = script.read_bytes()
            old, new = (b"linewidth=.8", b"linewidth=.9") if case == "vabistsevits-forest" else (b"zorder=10", b"zorder=99")
            assert old in content and len(old) == len(new)
            script.write_bytes(content.replace(old, new, 1))
            os.utime(script, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            command = [sys.executable, "-c", "import importlib.util,sys; s=importlib.util.spec_from_file_location('case_under_test',sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)", str(script)]
        else:
            command = [sys.executable, str(script), "--runtime", str(ROOT / "skills/easyviz/scripts"), "--out", str(output)]
            if font:
                command.extend(["--font", font])
        process = subprocess.run(command, capture_output=True, text=True, timeout=40)
        if mutation or stale:
            assert process.returncode != 0, (case, check, process.stdout, process.stderr)
            assert not any(output.glob("panel.*"))
            if stale:
                assert "Executing case code differs from the source file" in process.stderr
            else:
                assert json.loads((output / "qa.json").read_text())["technical_passed"] is False
            status = "refused_with_no_exports"
        else:
            assert process.returncode == 0, process.stderr
            qa = json.loads((output / "qa.json").read_text())
            assert qa["technical_passed"] and all(qa["checks"].values())
            assert (output / "source-data.csv").read_bytes() == data.read_bytes()
            sys.path.insert(0, str(ROOT / "skills/easyviz/scripts"))
            from figure_workbench import FigureWorkbench
            state = FigureWorkbench(output).state()
            assert state["manifest_valid"] and state["provenance_valid"] and state["source_current"]
            source_handoff = json.loads((output / "handoff.json").read_text())
            assert source_handoff["consumption"]["kind"] == "captured-bytes-before-export"
            assert set(source_handoff["input"]["auxiliary_inputs"]) == ({"figure_elements_helper", "figure_handoff_helper", "figure_workbench_helper"}
                 | ({"original_spec_file"} if font else set()))
            if font:
                settings = json.loads((output / "settings.json").read_text())
                adopted = json.loads((output / "adopted-spec.json").read_text())
                assert settings["actual_font"] == font and adopted["layout"]["font"] == font
                assert settings["font_override"]["supplied_spec_font"] == "Arial"
                assert (output / "supplied-spec.json").read_bytes() == (revision / "adopted-spec.json").read_bytes()
                module_spec = importlib.util.spec_from_file_location("export_reader", HERE / "verify_revisions.py")
                export_reader = importlib.util.module_from_spec(module_spec)
                module_spec.loader.exec_module(export_reader)
                result = (export_reader.forest if case == "vabistsevits-forest" else export_reader.radar)(copy, font)
                assert result["literal_source_snapshot_preserved"]
                status = "passed_explicit_font_real_export_verification"
            else:
                assert (output / "panel.png").read_bytes() == (revision / "output/panel.png").read_bytes()
                status = "passed_portable_same_pixels"
        RESULTS.append({"case": case, "check": check, "status": status, "exit_code": process.returncode})


def probe_capture_boundary(case, role):
    """Change a real consumed local file after capture and before drawing."""
    authoritative = ROOT / "examples/no-author-code" / case
    with tempfile.TemporaryDirectory(prefix="easyviz-reproduce-continuity-") as temp:
        base = Path(temp) / "case"
        (base / "inputs").mkdir(parents=True)
        (base / "revision-v0.4.6").mkdir()
        tools = base / "runtime"
        tools.mkdir()
        for name in ("figure_elements.py", "figure_handoff.py", "figure_workbench.py"):
            shutil.copy2(ROOT / "skills/easyviz/scripts" / name, tools / name)
        shutil.copy2(authoritative / "inputs/source-data.csv", base / "inputs/source-data.csv")
        script = base / "revision-v0.4.6/plot.py"
        shutil.copy2(authoritative / "revision-v0.4.6/plot.py", script)
        shutil.copy2(authoritative / "revision-v0.4.6/adopted-spec.json", script.with_name("adopted-spec.json"))
        output = base / "result"
        target = {"data": base / "inputs/source-data.csv", "spec": script.with_name("adopted-spec.json"),
                  "helper": tools / "figure_elements.py"}[role]
        hook = """import importlib.util,sys,json
from pathlib import Path
spec=importlib.util.spec_from_file_location('actual_case',sys.argv[1]); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
real_prepare=module.prepare_attempt
target=Path(sys.argv[4])
def replace_after_capture(args,out):
    actual=real_prepare(args,out)
    target.write_bytes(target.read_bytes()+b'\\n')
    return actual
module.prepare_attempt=replace_after_capture
sys.argv=[sys.argv[1],'--runtime',sys.argv[2],'--out',sys.argv[3]]
try:
    module.main()
except ValueError as error:
    assert 'consumed source changed before export' in str(error),str(error)
else:
    raise AssertionError('Changed consumed source was accepted')
"""
        process = subprocess.run([sys.executable, "-c", hook, str(script), str(tools), str(output), str(target)],
                                 capture_output=True, text=True, timeout=40)
        assert process.returncode == 0, process.stderr
        assert not any(output.glob("panel.*")) and not (output / "handoff.json").exists()
        assert json.loads((output / "qa.json").read_text())["valid_outputs"] is False
        RESULTS.append({"case": case, "check": f"Actual {role} replacement after byte capture; refusal before any export",
                        "status": "passed_refusal_before_export", "exit_code": process.returncode})


def main():
    for case in ("vabistsevits-forest", "massier-integration-radar"):
        run_case(case, "copied CLI outside repository with explicit shared runtime")
        run_case(case, "explicit DejaVu Sans adoption in portable copy; independent real PDF/SVG/source checks", font="DejaVu Sans")
        run_case(case, "CSV row has extra field", lambda rows: rows[1].append("extra"))
        run_case(case, "duplicate source identity", lambda rows: rows.append(rows[1].copy()))
        run_case(case, "missing required source identity", lambda rows: rows.pop())
        if case == "vabistsevits-forest":
            run_case(case, "confidence interval outside fixed log scale", lambda rows: rows[1].__setitem__(rows[0].index("ci_low"), "0.001"))
            run_case(case, "unexpected per-estimate n is not invented", lambda rows: rows[1].__setitem__(rows[0].index("n"), "10"))
        else:
            run_case(case, "acceptance rate outside fixed radial scale", lambda rows: rows[1].__setitem__(rows[0].index("acceptance_rate"), "0.8"))
            run_case(case, "negative rate cannot become inner padding", lambda rows: rows[1].__setitem__(rows[0].index("acceptance_rate"), "-0.01"))
        run_case(case, "real default importlib timestamp/size-valid stale source bytecode", stale=True)
        for role in ("data", "spec", "helper"):
            probe_capture_boundary(case, role)
    bindings = {case: {name: hashlib.sha256((ROOT / "examples/no-author-code" / case / "revision-v0.4.6" / name).read_bytes()).hexdigest()
               for name in ("plot.py", "adopted-spec.json", "output/panel.png", "output/panel.pdf", "output/panel.svg")}
               for case in ("vabistsevits-forest", "massier-integration-radar")}
    value = {"status": "passed", "probe_count": len(RESULTS), "probes": RESULTS, "bindings": bindings,
             "scope": "Case portability, fixed-source identity/semantics and actual stale-bytecode refusal. Does not measure aesthetics or model efficacy."}
    (HERE / "case-probes.json").write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps({"status": value["status"], "probes": len(RESULTS)}))


if __name__ == "__main__":
    main()
