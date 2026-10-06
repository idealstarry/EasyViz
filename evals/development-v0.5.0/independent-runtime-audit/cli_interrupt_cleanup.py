"""Send SIGINT through the actual CLI entry point while its owned child runs."""
from pathlib import Path
import json
import os
import signal
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "skills/easyviz/scripts"
sys.path.insert(0, str(SCRIPTS))
from figure_service import FigureService

root = Path(__file__).resolve().parent / "registry-publication-fixture"
attempt = root / "attempt-01"
service = FigureService(root, attempt)
version = service.state()["version"]
item = service.app.change({"version": version, "selector": {"category": "A"},
    "property": "color", "value": "#8833AA", "instruction": "Use violet for A."})["request"]
service.close()
pid_file = root / "audit-cli-worker-pid.json"
pid_file.unlink(missing_ok=True)
# A test shim slows only the otherwise fixed owned worker, then calls the
# production CLI main function unchanged. It does not change production files.
shim = "\n".join([
    "import sys, subprocess, json", "from pathlib import Path", "sys.path.insert(0, " + repr(str(SCRIPTS)) + ")",
    "import figure_service", "real_popen = subprocess.Popen",
    "def slow(*args, **kwargs):",
    "    child = real_popen([sys.executable, '-c', 'import time; time.sleep(20)'], **kwargs)",
    "    Path(" + repr(str(pid_file)) + ").write_text(json.dumps({'pid': child.pid}))",
    "    return child",
    "figure_service.subprocess.Popen = slow",
    "sys.argv = " + repr([str(SCRIPTS / "figure_service.py"), "submit", "--project-dir", str(root),
                           "--figure-dir", str(attempt), "--request-ids", item["id"]]),
    "figure_service.main()"])
cli = subprocess.Popen([sys.executable, "-c", shim], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, start_new_session=True)
child_pid = None
try:
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if pid_file.is_file():
            child_pid = json.loads(pid_file.read_text())["pid"]
        if child_pid is not None:
            break
        time.sleep(.03)
    if child_pid is None:
        raise RuntimeError("CLI did not start its owned worker")
    os.kill(cli.pid, signal.SIGINT)
    stdout, stderr = cli.communicate(timeout=8)
    try:
        os.kill(child_pid, 0)
        child_alive = True
    except ProcessLookupError:
        child_alive = False
    output = {"cli_pid": cli.pid, "owned_child_pid": child_pid, "cli_exit": cli.returncode,
              "owned_child_alive_after_cli_sigint": child_alive,
              "cli_stderr_tail": stderr[-1000:]}
    (root.parent / "cli-interrupt-cleanup-result.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))
finally:
    if cli.poll() is None:
        os.killpg(cli.pid, signal.SIGTERM)
        cli.communicate()
    if child_pid is not None:
        try:
            os.killpg(child_pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
