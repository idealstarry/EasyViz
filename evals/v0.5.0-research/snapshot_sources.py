#!/usr/bin/env python3
"""Read public GitHub metadata for the research snapshot; never execute repo code."""
import concurrent.futures
import datetime
import json
from pathlib import Path
import re
import subprocess

REPOS = [
    "K-Dense-AI/scientific-agent-skills", "faridrashidi/cnsplots",
    "Dsadd4/AgentFigureGallery", "KuangshiAi/SciVisAgentSkills",
    "garrettj403/SciencePlots", "vega/vega-lite", "anntzer/mplcursors",
    "antvis/mcp-server-chart", "modelcontextprotocol/python-sdk",
]

def api(route):
    result = subprocess.run(["gh", "api", route], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)

def inspect_repo(repo):
    metadata = api(f"repos/{repo}")
    commit = api(f"repos/{repo}/commits/{metadata['default_branch']}")
    tree = api(f"repos/{repo}/git/trees/{commit['sha']}?recursive=1")
    license_meta = metadata.get("license") or {}
    return {
        "requested_repo": repo, "canonical_repo": metadata["full_name"],
        "url": metadata["html_url"], "default_branch": metadata["default_branch"],
        "archived": metadata["archived"], "license_spdx": license_meta.get("spdx_id"),
        "head": commit["sha"], "head_committed_at": commit["commit"]["committer"]["date"],
        "commit_url": commit["html_url"], "tree_truncated": tree.get("truncated", False),
        "file_count": sum(item["type"] == "blob" for item in tree["tree"]),
        "license_paths": [item["path"] for item in tree["tree"]
                          if item["type"] == "blob" and re.match(r"^(license|copying)(\.|$)", item["path"], re.I)],
    }

def main():
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for repo, future in zip(REPOS, [pool.submit(inspect_repo, repo) for repo in REPOS]):
            try:
                results.append(future.result())
            except Exception as exc:
                results.append({"requested_repo": repo, "error": str(exc)})
    output = {"observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "repos": results}
    target = Path(__file__).with_name("github-snapshot.json")
    target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"snapshot": str(target), "repos": [
        {key: item.get(key) for key in ("canonical_repo", "head", "license_spdx", "error")}
        for item in results]}, indent=2))

if __name__ == "__main__":
    main()
