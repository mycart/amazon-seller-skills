#!/usr/bin/env python3
"""Seal a real Mode B Markdown response with KJXJ-owned, truthful provenance."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "scripts" / "audit-external-dependencies.py"
LOCK = ROOT / "references" / "external-dependencies.lock.json"
REQUIRED = ("## Title", "## Bullet Points", "## Description", "## Backend Search Terms")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def section(raw: str, name: str) -> str:
    match = re.search(rf"^## {re.escape(name)}\s*$\n(.*?)(?=^## |\Z)", raw, re.M | re.S)
    return match.group(1).strip() if match else ""


def materialize(args: argparse.Namespace) -> None:
    request_path, raw_path, receipt_path = Path(args.request).resolve(), Path(args.raw_output).resolve(), Path(args.receipt).resolve()
    request, receipt = json.loads(request_path.read_text(encoding="utf-8")), json.loads(receipt_path.read_text(encoding="utf-8"))
    raw = raw_path.read_text(encoding="utf-8")
    bullets = [re.sub(r"^\s*\d+[.)]\s*", "", value).strip() for value in section(raw, "Bullet Points").splitlines() if re.match(r"^\s*\d+[.)]\s+", value)]
    if len(bullets) != 5:
        raise ValueError("Mode B 原始输出必须包含正好 5 条编号 Bullet Points。")
    provenance = {key: receipt[key] for key in ("adapter", "adapter_sha256", "adapter_invocation_id", "upstream_skill", "external_raw_output", "request_path", "request_sha256", "started_at", "completed_at")}
    listing = {"title": section(raw, "Title"), "bullets": bullets, "description": section(raw, "Description"), "backend_search_terms": section(raw, "Backend Search Terms")}
    result = {
        "source_skill": "amazon-listing-optimization", "source_skill_path": "/Users/apple/.agents/skills/amazon-listing-optimization/SKILL.md", "source_skill_sha256": digest(Path("/Users/apple/.agents/skills/amazon-listing-optimization/SKILL.md")),
        "mode": "B", "status": "complete", "invocation_id": provenance["adapter_invocation_id"], "started_at": provenance["started_at"], "completed_at": provenance["completed_at"], "request_path": str(request_path), "request_sha256": digest(request_path), "raw_output_path": str(raw_path), "raw_output_sha256": digest(raw_path), "execution_provenance": provenance,
        "input_manifest": request.get("input_manifest", {}), "legacy_listing": listing,
        "keyword_priority": {"primary": [item.get("keyword") for item in request.get("listing_eligible_keywords", [])[:3] if isinstance(item, dict)]}, "keyword_coverage": {"source": "原始 Mode B Markdown"}, "keyword_gaps": {"source": "原始 Mode B Markdown"}, "limitations": ["仅使用公开目标 ASIN 页面与调用请求中的合格关键词。"]
    }
    Path(args.output).resolve().write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("seal", "materialize"))
    parser.add_argument("--request", required=True)
    parser.add_argument("--raw-output", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--receipt")
    parser.add_argument("--producer", choices=("external_skill", "kjxj_fact_limited_fallback"), default="external_skill")
    args = parser.parse_args()
    subprocess.run([sys.executable, str(AUDIT), "check"], check=True, stdout=subprocess.DEVNULL)
    if args.command == "materialize":
        if not args.receipt:
            raise ValueError("materialize 必须提供 --receipt。")
        materialize(args)
        return
    request_path, raw_path = Path(args.request).resolve(), Path(args.raw_output).resolve()
    request = json.loads(request_path.read_text(encoding="utf-8"))
    raw = raw_path.read_text(encoding="utf-8")
    if str(request.get("mode", "")).upper() != "B":
        raise ValueError("Listing 适配器只接受 Mode B 请求。")
    missing = [section for section in REQUIRED if section not in raw]
    if missing:
        raise ValueError("Mode B 原始输出缺少章节：" + "、".join(missing))
    now = datetime.now(timezone.utc).isoformat()
    receipt = {"status": "complete", "adapter": "kjxj-optimize-sync-listing/scripts/external_adapters/listing_mode_b_adapter.py", "adapter_sha256": digest(Path(__file__)), "adapter_invocation_id": f"listing-adapter-{uuid.uuid4()}", "started_at": request.get("created_at") or now, "completed_at": now, "upstream_skill": {"name": "amazon-listing-optimization", "path": "/Users/apple/.agents/skills/amazon-listing-optimization/SKILL.md", "lock_sha256": digest(LOCK)}, "external_raw_output": {"path": str(raw_path), "sha256": digest(raw_path), "producer": args.producer}, "request_path": str(request_path), "request_sha256": digest(request_path)}
    Path(args.output).resolve().write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__": main()
