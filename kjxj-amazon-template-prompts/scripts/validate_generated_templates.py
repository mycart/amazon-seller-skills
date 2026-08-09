#!/usr/bin/env python3
"""Validate copy-ready templates and their separate diagnostic analysis."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")
EXPECTED_MARKETS = {"US", "CA", "MX", "UK", "DE", "FR", "IT", "ES", "NL", "SE", "PL", "BE", "TR"}
MARKET_DOMAINS = {"US": "amazon.com", "CA": "amazon.ca", "MX": "amazon.com.mx", "UK": "amazon.co.uk", "DE": "amazon.de", "FR": "amazon.fr", "IT": "amazon.it", "ES": "amazon.es", "NL": "amazon.nl", "SE": "amazon.se", "PL": "amazon.pl", "BE": "amazon.com.be", "TR": "amazon.com.tr", "IE": "amazon.ie"}
RETRIEVAL_CHANNELS = ("chrome", "in_app_browser", "firecrawl", "http_diagnostic")
STATUS_MARKERS = ("待实时核验", "商品页已核验", "当前不可售", "CAPTCHA", "robot check", "automated access", "汇率状态")


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    templates = data.get("templates")
    if not isinstance(templates, list) or not templates:
        return ["templates 必须是非空数组"]
    codes: set[str] = set()
    for index, item in enumerate(templates, 1):
        if not isinstance(item, dict):
            errors.append(f"第 {index} 项不是对象")
            continue
        code = str(item.get("code", ""))
        text = str(item.get("text", ""))
        analysis = item.get("analysis")
        codes.add(code)
        if code not in EXPECTED_MARKETS:
            errors.append(f"{code or '空'} 不是支持站点")
        if not text.strip() or "市场扩展数据" not in text:
            errors.append(f"{code} 缺少完整模板或市场扩展数据")
        if any(marker.lower() in text.lower() for marker in STATUS_MARKERS):
            errors.append(f"{code} 将实时状态或失败原因写入了可复制模板")
        competitors = item.get("competitor_asins", [])
        if not isinstance(competitors, list) or len(competitors) > 3:
            errors.append(f"{code} 竞品数量必须为 0-3")
        for asin in competitors:
            if not ASIN_RE.fullmatch(str(asin).upper()):
                errors.append(f"{code} 含无效竞品 ASIN：{asin}")
        if not isinstance(analysis, dict):
            errors.append(f"{code} 缺少独立分析说明")
            continue
        competitor_analysis = analysis.get("competitors")
        evidence_records = item.get("competitor_evidence", [])
        if not isinstance(competitor_analysis, dict) or not isinstance(evidence_records, list):
            errors.append(f"{code} 缺少竞品取证分析")
        else:
            attempts = competitor_analysis.get("attempts", [])
            if not isinstance(attempts, list) or not attempts:
                errors.append(f"{code} 未记录竞品取证尝试")
            for attempt in attempts if isinstance(attempts, list) else []:
                required = ("channel", "captured_at", "url", "page_status", "result_count", "reason", "continue_to_next")
                if not isinstance(attempt, dict) or any(key not in attempt for key in required):
                    errors.append(f"{code} 含不完整的竞品取证尝试")
                    continue
                if attempt["channel"] not in RETRIEVAL_CHANNELS:
                    errors.append(f"{code} 含未知取证渠道：{attempt['channel']}")
            if not competitors and not competitor_analysis.get("exhausted"):
                errors.append(f"{code} 竞品待补充前未完成降级链")
            if not competitors and {item.get("channel") for item in attempts if isinstance(item, dict)} != set(RETRIEVAL_CHANNELS):
                errors.append(f"{code} 竞品待补充缺少完整降级链记录")
            if len(evidence_records) != len(competitors):
                errors.append(f"{code} 竞品 ASIN 与证据记录数量不一致")
            seen_sponsored = False
            for record in evidence_records:
                required = ("asin", "source_type", "title", "position", "channel", "evidence_url", "captured_at")
                if not isinstance(record, dict) or any(not record.get(key) for key in required):
                    errors.append(f"{code} 含不完整的竞品证据")
                    continue
                parsed_url = urlparse(str(record["evidence_url"]))
                host = parsed_url.hostname or ""
                domain = MARKET_DOMAINS.get(code, "")
                if record["asin"] not in competitors or parsed_url.scheme != "https" or not (host == domain or host.endswith("." + domain)):
                    errors.append(f"{code} 竞品证据不属于目标市场")
                if record["source_type"] not in ("organic", "sponsored") or record["channel"] not in RETRIEVAL_CHANNELS:
                    errors.append(f"{code} 竞品证据来源无效")
                if record["source_type"] == "sponsored":
                    seen_sponsored = True
                elif seen_sponsored:
                    errors.append(f"{code} Sponsored 结果排在自然结果之前")
        primary = analysis.get("primary_asin")
        if not isinstance(primary, dict) or not primary.get("status"):
            errors.append(f"{code} 分析说明缺少主 ASIN 核验状态")
        localization = analysis.get("localization")
        product_type = item.get("localized_product_type")
        if not isinstance(product_type, str) or not product_type.strip():
            errors.append(f"{code} 缺少本地化产品类型")
        if not isinstance(localization, dict) or "product_type" not in localization:
            errors.append(f"{code} 分析说明缺少产品类型本地化证据状态")
        fx = item.get("fx", {})
        analysis_fx = analysis.get("fx", {})
        if not isinstance(analysis_fx, dict) or not analysis_fx.get("status"):
            errors.append(f"{code} 分析说明缺少汇率状态")
        if fx and fx.get("status") == "verified":
            for required in ("rate", "target_currency", "source", "captured_at"):
                if not fx.get(required):
                    errors.append(f"{code} 已验证汇率缺少 {required}")
    if len(codes) != len(templates):
        errors.append("站点代码重复")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        attempts = [{"channel": channel, "captured_at": "2026-08-09T00:00:00Z", "url": "https://www.amazon.de/s?k=katzenkratzmatte", "page_status": "blocked", "result_count": 0, "reason": "页面反爬", "continue_to_next": channel != "http_diagnostic"} for channel in RETRIEVAL_CHANNELS]
        sample = {"templates": [{"code": "DE", "text": "国家站：DE\n产品类型：Katzenkratzmatte\n市场扩展数据\n   目标市场：德国（DE)", "localized_product_type": "Katzenkratzmatte", "competitor_asins": [], "competitor_evidence": [], "fx": {"status": "pending"}, "analysis": {"primary_asin": {"status": "pending", "reason": "页面反爬"}, "competitors": {"attempts": attempts, "exhausted": True}, "localization": {"product_type": {"status": "pending"}}, "fx": {"status": "pending", "reason": "汇率源不可用"}}}]}
        assert validate(sample) == []
        assert validate({"templates": [{**sample["templates"][0], "text": "产品类型：Katzenkratzmatte（商品页已核验，当前不可售）\n市场扩展数据"}]})
        record = {"asin": "B012345678", "source_type": "organic", "title": "Katzenkratzmatte", "position": 1, "channel": "chrome", "evidence_url": "https://www.amazon.de/s?k=katzenkratzmatte", "captured_at": "2026-08-09T00:00:00Z"}
        for channel in ("chrome", "in_app_browser", "firecrawl"):
            attempt = {"channel": channel, "captured_at": "2026-08-09T00:00:00Z", "url": "https://www.amazon.de/s?k=katzenkratzmatte", "page_status": "ok", "result_count": 1, "reason": "", "continue_to_next": False}
            verified = {**sample["templates"][0], "competitor_asins": [record["asin"]], "competitor_evidence": [{**record, "channel": channel}], "analysis": {**sample["templates"][0]["analysis"], "competitors": {"attempts": [attempt], "exhausted": False}}}
            assert validate({"templates": [verified]}) == []
        sponsored_first = {**sample["templates"][0], "competitor_asins": ["B012345678", "B012345679"], "competitor_evidence": [{**record, "source_type": "sponsored", "position": 1}, {**record, "asin": "B012345679", "position": 2}], "analysis": {**sample["templates"][0]["analysis"], "competitors": {"attempts": [attempt], "exhausted": False}}}
        assert any("Sponsored" in error for error in validate({"templates": [sponsored_first]}))
        print("self-test passed")
        return 0
    if not args.input:
        parser.error("需要 --input")
    data = json.loads(args.input.read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        print("验证失败：", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"验证通过：{len(data['templates'])} 个站点")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
