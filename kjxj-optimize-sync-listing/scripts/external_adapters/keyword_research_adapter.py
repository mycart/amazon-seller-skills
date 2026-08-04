#!/usr/bin/env python3
"""Capture the official autocomplete command without extending its files."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "scripts" / "audit-external-dependencies.py"
EXTERNAL = Path("/Users/apple/.agents/skills/amazon-keyword-research/scripts/research.sh")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", required=True)
    parser.add_argument("--marketplace", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    subprocess.run([sys.executable, str(AUDIT), "check"], check=True, stdout=subprocess.DEVNULL)
    started = datetime.now(timezone.utc).isoformat()
    completed = subprocess.run([str(EXTERNAL), args.seed, "--marketplace", args.marketplace, "--format", "json"], text=True, capture_output=True, check=False)
    if completed.returncode:
        raise SystemExit(completed.stderr.strip() or "上游关键词脚本执行失败。")
    raw = json.loads(completed.stdout)
    suggestions = raw.get("suggestions") if isinstance(raw, dict) else None
    if not isinstance(suggestions, list) or not all(isinstance(item, str) and item.strip() for item in suggestions):
        raise ValueError("上游关键词脚本未返回有效 suggestions 数组。")
    output = Path(args.output).resolve()
    output.write_text(json.dumps({"adapter_invocation_id": f"keyword-adapter-{uuid.uuid4()}", "started_at": started, "completed_at": datetime.now(timezone.utc).isoformat(), "upstream_skill": "amazon-keyword-research", "upstream_script": str(EXTERNAL), "upstream_script_sha256": digest(EXTERNAL), "request": {"seed": args.seed, "marketplace": args.marketplace}, "external_raw_output": raw}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
