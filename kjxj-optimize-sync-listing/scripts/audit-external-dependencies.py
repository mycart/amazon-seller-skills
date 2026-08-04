#!/usr/bin/env python3
"""Verify or stage the immutable third-party Skill baseline without modifying it."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "references" / "external-dependencies.lock.json"


def load_lock() -> dict:
    return json.loads(LOCK.read_text(encoding="utf-8"))


def git_blob(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], text=True).strip()


def audit(lock: dict) -> dict:
    findings = []
    for name, skill in lock["skills"].items():
        root = Path(skill["path"])
        expected = skill["files"]
        actual = {str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()}
        for relative, blob in expected.items():
            path = root / relative
            if not path.is_file():
                findings.append({"skill": name, "kind": "missing", "path": relative, "expected": blob})
            elif git_blob(path) != blob:
                findings.append({"skill": name, "kind": "modified", "path": relative, "expected": blob, "actual": git_blob(path)})
        for relative in sorted(actual - set(expected)):
            findings.append({"skill": name, "kind": "local_only", "path": relative})
    return {"ok": not findings, "commit": lock["commit"], "findings": findings}


def stage(lock: dict, commit: str) -> dict:
    report = {"candidate_commit": commit, "locked_commit": lock["commit"], "skills": []}
    base = "https://api.github.com/repos/nexscope-ai/Amazon-Skills/contents"
    for name, skill in lock["skills"].items():
        changes = []
        for relative, locked_blob in skill["files"].items():
            url = f"{base}/{name}/{relative}?ref={commit}"
            try:
                with urlopen(url, timeout=30) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                content = base64.b64decode(payload["content"])
                candidate_blob = subprocess.run(["git", "hash-object", "--stdin"], input=content, capture_output=True, check=True).stdout.decode().strip()
            except Exception as exc:
                candidate_blob = None
                changes.append({"path": relative, "locked_blob": locked_blob, "candidate_blob": candidate_blob, "error": str(exc)})
                continue
            changes.append({"path": relative, "locked_blob": locked_blob, "candidate_blob": candidate_blob})
        report["skills"].append({"skill": name, "changes": changes})
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("check", "report", "stage-upgrade"))
    parser.add_argument("--commit")
    parser.add_argument("--output")
    args = parser.parse_args()
    lock = load_lock()
    result = stage(lock, args.commit) if args.command == "stage-upgrade" and args.commit else audit(lock)
    if args.command == "stage-upgrade" and not args.commit:
        raise ValueError("stage-upgrade 必须提供 --commit。")
    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.command == "check" and not result["ok"]:
        raise SystemExit("外部 Skill 完整性校验失败：请执行显式维护恢复，不会自动覆盖第三方目录。")


if __name__ == "__main__":
    main()
