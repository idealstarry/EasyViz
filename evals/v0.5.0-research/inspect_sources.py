#!/usr/bin/env python3
"""Fetch commit-pinned public source for reading only; cache outside the repo."""
import base64
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess

FILES = {
    "K-Dense-AI/scientific-agent-skills": ["LICENSE.md", "skills/scientific-visualization/SKILL.md", "skills/scientific-visualization/scripts/style_presets.py", "skills/scientific-visualization/scripts/export_plan.py", "skills/scientific-visualization/assets/nature.mplstyle"],
    "faridrashidi/cnsplots": ["LICENSE.md", "pyproject.toml", "src/cnsplots/_agent_skill/cnsplots/SKILL.md", "src/cnsplots/_setup.py", "src/cnsplots/_settings.py", "src/cnsplots/helpers/_heatmap.py"],
    "Dsadd4/AgentFigureGallery": ["LICENSE", "README.md", "skills/agent-figure-gallery/SKILL.md", "agentfiguregallery/cli.py", "agentfiguregallery/server.py", "pyproject.toml"],
    "KuangshiAi/SciVisAgentSkills": ["README.md", "napari-viz/SKILL.md", "paraview-viz/references/mcp-tools.md"],
    "garrettj403/SciencePlots": ["LICENSE", "README.md", "pyproject.toml", "src/scienceplots/styles/science.mplstyle", "src/scienceplots/styles/color/bright.mplstyle"],
    "vega/vega-lite": ["LICENSE", "README.md", "package.json", "src/spec/layer.ts", "src/spec/concat.ts", "src/compile/selection/index.ts"],
    "anntzer/mplcursors": ["LICENSE.txt", "README.rst", "pyproject.toml", "src/mplcursors/_pick_info.py", "src/mplcursors/_mplcursors.py"],
    "antvis/mcp-server-chart": ["LICENSE", "package.json", "src/server.ts", "src/charts/base.ts", "src/charts/boxplot.ts", "src/utils/generate.ts", "src/utils/env.ts", "src/services/streamable.ts"],
    "modelcontextprotocol/python-sdk": ["LICENSE", "README.md", "pyproject.toml", "docs/servers/tools.md", "docs/handlers/progress.md", "src/mcp/server/transport_security.py", "src/mcp/server/mcpserver/server.py"],
}

def fetch(item):
    repo, commit, path = item
    result = subprocess.run(["gh", "api", f"repos/{repo}/contents/{path}?ref={commit}"], capture_output=True, text=True, check=True)
    payload = json.loads(result.stdout)
    raw = base64.b64decode(payload["content"])
    cache = Path("/tmp/easyviz-v050-research-raw") / repo / path
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(raw)
    return {"repo": repo, "commit": commit, "path": path, "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "url": f"https://github.com/{repo}/blob/{commit}/{path}", "cache": str(cache)}

def main():
    root = Path(__file__).parent
    snapshot = json.loads((root / "github-snapshot.json").read_text())
    items = [(r["canonical_repo"], r["head"], p) for r in snapshot["repos"] for p in FILES[r["canonical_repo"]]]
    records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for item, future in zip(items, [pool.submit(fetch, item) for item in items]):
            try:
                records.append(future.result())
            except Exception as exc:
                records.append({"repo": item[0], "commit": item[1], "path": item[2], "error": str(exc)})
    (root / "inspected-files.json").write_text(json.dumps({"snapshot_observed_at": snapshot["observed_at"], "files": records}, indent=2) + "\n")
    print(json.dumps({"downloaded": sum("error" not in r for r in records), "errors": [r for r in records if "error" in r]}, indent=2))

if __name__ == "__main__":
    main()
