#!/usr/bin/env python3
"""Explicit maintenance-only restoration of locked third-party Skill files."""
from __future__ import annotations

import argparse
import base64
import json
from urllib.request import urlopen
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "references" / "external-dependencies.lock.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="明确授权以锁定上游文件覆盖第三方安装。")
    args = parser.parse_args()
    if not args.apply:
        raise SystemExit("恢复第三方 Skill 是维护操作；请显式传入 --apply。")
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    base = "https://api.github.com/repos/nexscope-ai/Amazon-Skills/contents"
    for name, skill in lock["skills"].items():
        target_root = Path(skill["path"])
        for relative in skill["files"]:
            target = target_root / relative
            url = f"{base}/{name}/{relative}?ref={lock['commit']}"
            with urlopen(url, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            content = base64.b64decode(payload["content"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        for path in sorted(target_root.rglob("*"), reverse=True):
            if path.is_file() and str(path.relative_to(target_root)) not in skill["files"]:
                path.unlink()
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()
    print("已按锁定上游版本恢复第三方 Skill；请运行完整性校验。")


if __name__ == "__main__": main()
