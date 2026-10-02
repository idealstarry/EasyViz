#!/usr/bin/env python3
"""Stage identical task inputs in separate WorkBuddy projects with skill snapshots."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[2]


def copy_snapshot(dest: Path, *, git_ref: str | None, source: Path | None) -> dict:
    if git_ref:
        raw = subprocess.check_output(["git", "archive", git_ref, "skills"], cwd=REPO)
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            archive.extractall(dest, filter="data")
        commit = subprocess.check_output(["git", "rev-parse", git_ref], cwd=REPO, text=True).strip()
    else:
        assert source is not None
        shutil.copytree(source, dest / "skills", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        commit = None
    hashes = {str(p.relative_to(dest)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted((dest / "skills").rglob("*")) if p.is_file()}
    (dest / "snapshot-manifest.json").write_text(json.dumps({"git_ref": git_ref, "commit": commit,
                                                            "sha256": hashes}, indent=2) + "\n")
    return {"git_ref": git_ref, "commit": commit, "files": len(hashes)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, default=Path("/private/tmp/easyviz-v041-workbuddy"))
    parser.add_argument("--condition", choices=["baseline", "v040", "v041"], required=True)
    parser.add_argument("--skill-source", type=Path, default=REPO / "skills")
    args = parser.parse_args()
    condition_root = args.destination / args.condition
    if condition_root.exists():
        raise SystemExit(f"Refusing to overwrite an existing condition: {condition_root}")
    condition_root.mkdir(parents=True)
    manifest = {"condition": args.condition, "task_sha256": {}, "input_sha256": {}}
    for task in ["create", "reproduce"]:
        project = condition_root / task
        shutil.copytree(BASE / "fixtures" / task, project / "input")
        (project / "output").mkdir()
        task_text = (BASE / "prompts" / f"{task}.txt").read_text()
        if args.condition == "baseline":
            wrapper = ("此任务评估普通本地 Agent 的直接绘图能力。请只读当前工作目录 input/ 和你自己创建的文件，"
                       "使用通用已安装 Python 库编写代码。不要调用、读取、搜索或导入任何 EasyViz skill/plugin、"
                       "以前的对话/结果、其他工作目录或仓库。即使有全局安装的 EasyViz，也不要使用。\n\n")
        else:
            snapshot = copy_snapshot(project, git_ref="v0.4.0" if args.condition == "v040" else None,
                                     source=args.skill_source)
            manifest.setdefault("snapshots", {})[task] = snapshot
            wrapper = ("请使用当前工作目录 skills/easyviz/SKILL.md 和它按需引用的本地资源完成任务，"
                       "先阅读这个 SKILL.md。不要读取全局 EasyViz 安装、其他条件/结果、以前的对话或源仓库；"
                       "允许阅读本工作目录 input/、skills/ 和你自己创建的文件。\n\n")
        wrapper = (f"本次唯一工作目录：{project}。请先切换到这个目录，所有相对路径均以此为准。\n"
                   "允许使用 /Users/starry/Desktop/EasyViz/.venv/bin/python 作为已安装 Python 运行时，"
                   "仅执行本项目代码/通用库，不得因此查看该仓库的其他文件。\n\n" + wrapper)
        (project / "request.txt").write_text(wrapper + task_text, encoding="utf-8")
        (project / "task-only.txt").write_text(task_text, encoding="utf-8")
        manifest["task_sha256"][task] = hashlib.sha256(task_text.encode()).hexdigest()
        manifest["input_sha256"][task] = {
            str(p.relative_to(project / "input")): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((project / "input").rglob("*")) if p.is_file()}
        print(project)
        print(project / "request.txt")
    (condition_root / "staging-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
