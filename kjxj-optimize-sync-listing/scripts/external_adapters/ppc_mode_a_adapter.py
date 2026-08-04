#!/usr/bin/env python3
"""KJXJ-owned deterministic Mode A adapter for the official PPC Skill contract."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "scripts" / "audit-external-dependencies.py"
LOCK = ROOT / "references" / "external-dependencies.lock.json"
COPY_BLOCKS = ("manual_exact_keywords", "manual_broad_keywords", "auto_negative_exact_keywords", "broad_negative_exact_keywords", "negative_phrase_keywords", "product_targeting_asins")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("事实数据包根节点必须为 JSON 对象。")
    return data


def require_text(value: object, label: str) -> str:
    value = str(value or "").strip()
    if not value:
        raise ValueError(f"事实数据包缺少 {label}。")
    return value


def build(packet: dict, invocation: str) -> dict:
    defaults = packet.get("financial_defaults_applied")
    financial = packet.get("financial")
    if not isinstance(defaults, dict) or not isinstance(financial, dict):
        raise ValueError("事实数据包缺少 financial 或 financial_defaults_applied。")
    for key in ("selling_price", "monthly_ad_budget", "break_even_acos", "conversion_rate"):
        if not isinstance(financial.get(key), dict) or not {"value", "source", "reason"}.issubset(financial[key]):
            raise ValueError(f"事实数据包 financial.{key} 必须保留 value、source 和 reason。")
    for key in ("selling_price", "monthly_ad_budget", "break_even_acos"):
        if not isinstance(defaults.get(key), dict) or not isinstance(defaults[key].get("used"), bool):
            raise ValueError(f"事实数据包 financial_defaults_applied.{key} 无效。")
    context = packet.get("product_context") if isinstance(packet.get("product_context"), dict) else {}
    label = require_text(context.get("campaign_label"), "product_context.campaign_label")
    title = require_text(context.get("recommended_2026_title"), "product_context.recommended_2026_title")
    if label.casefold() not in title.casefold():
        raise ValueError("campaign_label 必须来自推荐 2026 标题，不得使用固定类目名称。")
    terms = []
    for item in packet.get("keywords", []):
        term = str(item.get("keyword", "")).strip() if isinstance(item, dict) and item.get("ppc_eligible") is True else ""
        if term and term.casefold() not in {value.casefold() for value in terms}:
            terms.append(term)
    if not terms:
        raise ValueError("数据包没有 ppc_eligible 关键词。")
    value = lambda key: financial[key]["value"]
    assumptions = [f"{key}：{item['reason']}" for key, item in financial.items() if isinstance(item, dict) and item.get("source") == "default"]
    confidence = "assumption_limited" if any(defaults[key]["used"] for key in ("selling_price", "monthly_ad_budget", "break_even_acos")) else "fact_supported"
    external_path = "/Users/apple/.agents/skills/amazon-ppc-campaign/SKILL.md"
    plan = {
        "schema_version": 1, "mode": "build", "primary_asin": packet["primary_asin"], "marketplace": packet["marketplace"], "currency": packet.get("currency"),
        "keyword_pool_sha256": (packet.get("keyword_pool") or {}).get("sha256"),
        "financial_framework": {"selling_price": value("selling_price"), "monthly_ad_budget": value("monthly_ad_budget"), "profit_before_ads": value("selling_price") * (1 - value("break_even_acos")), "break_even_acos": value("break_even_acos"), "target_acos_launch": min(value("break_even_acos"), .35), "target_acos_mature": min(value("break_even_acos"), .25), "conversion_rate": value("conversion_rate"), "max_cpc": None, "data_sources": ["编排层事实数据包"], "assumptions": assumptions or ["未提供可核验转化率，不输出金额 CPC 或关键词出价。"], "financial_inputs": copy.deepcopy(financial), "defaults_applied": copy.deepcopy(defaults)},
        "data_quality": {"financial_confidence": confidence, "input_data_quality": "关键词与财务参数均来自事实数据包。", "financial_limitations": "未提供可核验转化率，不能输出金额 CPC 或盈利预测。", "keyword_boundary": "不使用历史广告数据或搜索词报表。"},
        "bid_guidance": {"mode": "formula_and_coefficients", "formula": "Max CPC = 售价 × 目标 ACoS × 已验证转化率；当前转化率未提供，因此仅保留公式。", "coefficients": {"exact": 1.0, "broad": .75, "auto": .6, "product_targeting": .6}, "seller_central_check": "在 Seller Central 核验建议竞价后，再按 Max CPC 公式设置实际金额。"},
        "keyword_sources": ["用户关键词资料与统一关键词池"],
        "campaigns": [{"type": "auto", "name": f"{label} - Auto", "reason": "用于发现新的搜索词。"}, {"type": "manual_exact", "name": f"{label} - Exact", "reason": "用于精确测试高相关关键词。"}, {"type": "manual_broad", "name": f"{label} - Broad", "reason": "用于发现词序和长尾变化。"}, {"type": "product_targeting", "name": f"{label} - Product Targeting", "reason": "用于测试用户提供的竞品 ASIN。"}],
        "copy_blocks": {"manual_exact_keywords": terms[:12], "manual_broad_keywords": terms[:20], "auto_negative_exact_keywords": terms[:12], "broad_negative_exact_keywords": terms[:12], "negative_phrase_keywords": ["kostenlos", "gebraucht", "diy"], "product_targeting_asins": packet.get("competitor_asins") or []},
        "budget_summary": [{"campaign": "Auto", "reason": "先以发现为主，按月度预算在 Seller Central 分配。"}, {"campaign": "Exact", "reason": "优先承接高相关关键词。"}, {"campaign": "Broad", "reason": "用于扩词测试。"}, {"campaign": "Product Targeting", "reason": "仅测试已提供竞品。"}],
        "launch_schedule": ["第 1 天：建立 Auto 与 Exact。", "第 7 天：建立 Broad 与 Product Targeting。", "第 14 天：根据订单迁移搜索词。"], "optimization_plan_4_weeks": ["每周检查搜索词与花费。", "两单以上的词迁入 Exact。", "十次点击无订单的词评估暂停。", "根据真实 ACoS 调整。"], "risk_notes": ["本方案不代表 Seller Central 已创建广告。", "默认财务参数不构成盈利预测。"],
        "execution_provenance": {"adapter": "kjxj-optimize-sync-listing/scripts/external_adapters/ppc_mode_a_adapter.py", "adapter_sha256": digest(Path(__file__)), "adapter_invocation_id": invocation, "upstream_skill": {"name": "amazon-ppc-campaign", "path": external_path, "lock_sha256": digest(LOCK)}, "external_raw_output": None}
    }
    return plan


def markdown(plan: dict) -> str:
    lines = ["# PPC Mode A 方案", "", "## 输入数据质量", "关键词和财务值来自事实数据包；不使用历史广告数据。", "", "## 财务依据与默认值影响", "未提供可核验转化率，不输出金额 CPC。", "", "## 关键词来源与排除边界", "仅投放统一关键词池内的 ppc_eligible 关键词。", "", "## 竞价依据限制", "使用 Max CPC 公式和匹配类型系数，并在 Seller Central 核验建议竞价。", "", "## Campaign 设计理由", "Auto 发现，Exact 放大，Broad 测试，Product Targeting 测试竞品页面。", ""]
    labels = ("Manual Exact Keywords", "Manual Broad Keywords", "Auto Negative Exact Keywords", "Broad Negative Exact Keywords", "Negative Phrase Keywords", "Product Targeting ASINs")
    for label, key in zip(labels, COPY_BLOCKS): lines += [f"## {label}", "```text", "\n".join(plan["copy_blocks"][key]) or "无", "```", ""]
    lines += ["## 规范 JSON", "```json", json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")), "```", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("run"); parser.add_argument("--packet", required=True); parser.add_argument("--request", required=True); parser.add_argument("--plan", required=True); parser.add_argument("--markdown", required=True); parser.add_argument("--raw-output", required=True); args = parser.parse_args()
    subprocess.run([sys.executable, str(AUDIT), "check"], check=True, stdout=subprocess.DEVNULL)
    packet_path = Path(args.packet).resolve(); plan = build(load(packet_path), f"ppc-adapter-{uuid.uuid4()}")
    raw = Path(args.raw_output).resolve(); raw.parent.mkdir(parents=True, exist_ok=True); raw.write_text(markdown(plan), encoding="utf-8")
    provenance = plan["execution_provenance"]; provenance["source_packet_path"] = str(packet_path); provenance["source_packet_sha256"] = digest(packet_path); provenance["external_raw_output"] = {"path": str(raw), "sha256": digest(raw), "producer": "kjxj_adapter"}
    request = {"adapter": provenance["adapter"], "adapter_invocation_id": provenance["adapter_invocation_id"], "mode": "A", "source_packet_path": str(packet_path), "source_packet_sha256": digest(packet_path)}
    Path(args.request).resolve().write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.plan).resolve().write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); Path(args.markdown).resolve().write_text(markdown(plan), encoding="utf-8")
    print(json.dumps({"ok": True, "adapter_invocation_id": provenance["adapter_invocation_id"]}, ensure_ascii=False))


if __name__ == "__main__": main()
