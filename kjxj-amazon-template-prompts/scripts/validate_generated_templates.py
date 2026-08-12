#!/usr/bin/env python3
"""Validate copy-ready templates and browser-only Amazon evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse


ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")
EXPECTED_MARKETS = {"US", "CA", "MX", "UK", "DE", "FR", "IT", "ES", "NL", "SE", "PL", "BE", "TR"}
MARKET_DOMAINS = {"US": "amazon.com", "CA": "amazon.ca", "MX": "amazon.com.mx", "UK": "amazon.co.uk", "DE": "amazon.de", "FR": "amazon.fr", "IT": "amazon.it", "ES": "amazon.es", "NL": "amazon.nl", "SE": "amazon.se", "PL": "amazon.pl", "BE": "amazon.com.be", "TR": "amazon.com.tr", "IE": "amazon.ie"}
RETRIEVAL_CHANNELS = ("chrome", "in_app_browser")
KEYWORD_SOURCES = ("product_title", "search_heading", "autocomplete", "competitor_title")
STATUS_MARKERS = ("待实时核验", "商品页已核验", "当前不可售", "CAPTCHA", "robot check", "automated access", "汇率状态")
SCREENSHOT_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def belongs_to_market(url: object, code: str) -> bool:
    parsed_url = urlparse(str(url))
    host = parsed_url.hostname or ""
    domain = MARKET_DOMAINS.get(code, "")
    return parsed_url.scheme == "https" and bool(domain) and (host == domain or host.endswith("." + domain))


def keyword_evidence_errors(item: dict, code: str, text: str, attempt_channels: set[str]) -> list[str]:
    errors: list[str] = []
    keyword = item.get("keyword")
    evidence = item.get("keyword_evidence")
    if not isinstance(keyword, str) or not keyword.strip():
        return [f"{code} 缺少实时核心关键词结果"]
    if not isinstance(evidence, dict):
        return [f"{code} 缺少核心关键词实时证据"]
    status = evidence.get("status")
    if item.get("keyword_refresh_status") != status or status not in ("verified", "failed"):
        errors.append(f"{code} 核心关键词刷新状态无效")
    required = ("source_type", "evidence_url", "channel", "captured_at")
    if any(not evidence.get(key) for key in required):
        errors.append(f"{code} 核心关键词证据不完整")
    elif (
        evidence["source_type"] not in KEYWORD_SOURCES
        or evidence["channel"] not in RETRIEVAL_CHANNELS
        or evidence["channel"] not in attempt_channels
        or not belongs_to_market(evidence["evidence_url"], code)
    ):
        errors.append(f"{code} 核心关键词证据不属于真实浏览器尝试")
    if status == "verified":
        if keyword == "待补充" or not str(evidence.get("source_text", "")).strip():
            errors.append(f"{code} 已验证核心关键词缺少可见来源文本")
    elif keyword != "待补充" or not re.search(r"(?:核心关键词|keyword)\s*[：:]\s*待补充", text, re.IGNORECASE):
        errors.append(f"{code} 核心关键词失败时必须输出待补充")
    return errors


def readiness_errors(attempt: dict, code: str, evidence_root: Path) -> list[str]:
    errors: list[str] = []
    readiness = attempt.get("readiness")
    if not isinstance(readiness, dict):
        return [f"{code} 浏览器取证缺少页面就绪审计"]
    required = ("state", "polls", "waited_ms", "visible_card_count", "screenshot_path")
    if any(key not in readiness for key in required):
        return [f"{code} 页面就绪审计不完整"]
    if (
        not isinstance(readiness["polls"], int) or readiness["polls"] < 1
        or not isinstance(readiness["waited_ms"], int) or readiness["waited_ms"] < 0
        or not isinstance(readiness["visible_card_count"], int) or readiness["visible_card_count"] < 0
    ):
        errors.append(f"{code} 页面就绪审计数值无效")
    if readiness["state"] != "ready":
        screenshot = str(readiness["screenshot_path"]).strip()
        path = Path(screenshot)
        resolved = path if path.is_absolute() else evidence_root / path
        if not screenshot or path.suffix.lower() not in SCREENSHOT_SUFFIXES or not resolved.is_file():
            errors.append(f"{code} 未就绪浏览器页面缺少真实截图文件")
    return errors


def attempt_errors(attempts: list[dict], records: list[dict], exhausted: bool, code: str, evidence_root: Path) -> list[str]:
    errors: list[str] = []
    if not attempts:
        return [f"{code} 未记录竞品取证尝试"]
    channels = [attempt.get("channel") for attempt in attempts]
    if channels[0] != "chrome" or channels not in (["chrome"], ["chrome", "in_app_browser"]):
        errors.append(f"{code} 浏览器取证顺序无效")
    for index, attempt in enumerate(attempts):
        required = ("channel", "captured_at", "url", "page_status", "result_count", "reason", "continue_to_next")
        if not isinstance(attempt, dict) or any(key not in attempt for key in required):
            errors.append(f"{code} 含不完整的竞品取证尝试")
            continue
        if attempt["channel"] not in RETRIEVAL_CHANNELS:
            errors.append(f"{code} 含未知取证渠道：{attempt['channel']}")
        if not isinstance(attempt["result_count"], int) or attempt["result_count"] < 0:
            errors.append(f"{code} 竞品取证卡片数无效")
        if bool(attempt["continue_to_next"]) != (index < len(attempts) - 1):
            errors.append(f"{code} 竞品取证继续标记无效")
        errors.extend(readiness_errors(attempt, code, evidence_root))
    if len(attempts) == 2 and attempts[0].get("result_count", 0) > 0:
        errors.append(f"{code} Chrome 已有可见卡片时不应回退内置浏览器")
    if records:
        final_attempt = attempts[-1]
        final_channel = final_attempt.get("channel")
        if exhausted:
            errors.append(f"{code} 已验证竞品不得标记为取证耗尽")
        if final_attempt.get("result_count", 0) < len(records):
            errors.append(f"{code} 最终浏览器卡片数少于竞品证据数")
        if any(record.get("channel") != final_channel for record in records):
            errors.append(f"{code} 竞品证据未来自最终成功浏览器")
    else:
        if channels != ["chrome", "in_app_browser"] or not exhausted:
            errors.append(f"{code} 竞品待补充缺少完整两层失败链")
        if any(attempt.get("result_count", 0) != 0 for attempt in attempts):
            errors.append(f"{code} 有可见卡片时不得将竞品标为待补充")
    return errors


def validate(data: dict, evidence_root: Path) -> list[str]:
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
        if not isinstance(analysis, dict):
            errors.append(f"{code} 缺少独立分析说明")
            continue
        competitor_analysis = analysis.get("competitors")
        evidence_records = item.get("competitor_evidence", [])
        competitors = item.get("competitor_asins", [])
        if not isinstance(competitor_analysis, dict) or not isinstance(evidence_records, list) or not isinstance(competitors, list):
            errors.append(f"{code} 缺少竞品取证分析")
            continue
        if len(competitors) > 3 or any(not ASIN_RE.fullmatch(str(asin).upper()) for asin in competitors):
            errors.append(f"{code} 含无效竞品 ASIN")
        if len(evidence_records) != len(competitors):
            errors.append(f"{code} 竞品 ASIN 与证据记录数量不一致")
        attempts = competitor_analysis.get("attempts", [])
        if not isinstance(attempts, list):
            errors.append(f"{code} 竞品取证尝试格式无效")
            attempts = []
        errors.extend(attempt_errors(attempts, evidence_records, bool(competitor_analysis.get("exhausted")), code, evidence_root))
        attempt_channels = {attempt.get("channel") for attempt in attempts if isinstance(attempt, dict)}
        errors.extend(keyword_evidence_errors(item, code, text, attempt_channels))
        seen_sponsored = False
        for record in evidence_records:
            required = ("asin", "source_type", "title", "position", "channel", "evidence_url", "captured_at")
            if not isinstance(record, dict) or any(not record.get(key) for key in required):
                errors.append(f"{code} 含不完整的竞品证据")
                continue
            if record["asin"] not in competitors or not belongs_to_market(record["evidence_url"], code):
                errors.append(f"{code} 竞品证据不属于目标市场")
            if record["source_type"] not in ("organic", "sponsored") or record["channel"] not in RETRIEVAL_CHANNELS:
                errors.append(f"{code} 竞品证据来源无效")
            if record["source_type"] == "sponsored":
                seen_sponsored = True
            elif seen_sponsored:
                errors.append(f"{code} Sponsored 结果排在自然结果之前")
        if not isinstance(analysis.get("primary_asin"), dict) or not analysis["primary_asin"].get("status"):
            errors.append(f"{code} 分析说明缺少主 ASIN 核验状态")
        if not isinstance(item.get("localized_product_type"), str) or not item["localized_product_type"].strip():
            errors.append(f"{code} 缺少本地化产品类型")
        if not isinstance(analysis.get("localization"), dict) or "product_type" not in analysis["localization"]:
            errors.append(f"{code} 分析说明缺少产品类型本地化证据状态")
        analysis_fx = analysis.get("fx", {})
        if not isinstance(analysis_fx, dict) or not analysis_fx.get("status"):
            errors.append(f"{code} 分析说明缺少汇率状态")
    if len(codes) != len(templates):
        errors.append("站点代码重复")
    return errors


def self_test() -> int:
    url = "https://www.amazon.de/s?k=katzenkratzmatte"
    record = {"asin": "B012345678", "source_type": "organic", "title": "Katzenkratzmatte", "position": 1, "channel": "chrome", "evidence_url": url, "captured_at": "2026-08-09T00:00:00Z"}
    keyword = {"status": "verified", "source_type": "search_heading", "source_text": "Katzenkratzmatte", "evidence_url": url, "channel": "chrome", "captured_at": "2026-08-09T00:00:00Z"}
    base = {"code": "DE", "text": "国家站：DE\n核心关键词：Katzenkratzmatte\n市场扩展数据", "keyword": "Katzenkratzmatte", "keyword_evidence": keyword, "keyword_refresh_status": "verified", "localized_product_type": "Katzenkratzmatte", "competitor_asins": [record["asin"]], "competitor_evidence": [record], "fx": {"status": "pending"}, "analysis": {"primary_asin": {"status": "pending"}, "localization": {"product_type": {"status": "verified"}}, "fx": {"status": "pending"}}}
    ready = {"channel": "chrome", "captured_at": record["captured_at"], "url": url, "page_status": "ok", "result_count": 1, "reason": "", "continue_to_next": False, "readiness": {"state": "ready", "polls": 1, "waited_ms": 0, "visible_card_count": 1, "screenshot_path": ""}}
    chrome_success = {"templates": [{**base, "analysis": {**base["analysis"], "competitors": {"attempts": [ready], "exhausted": False}}}]}
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        screenshot = root / "evidence" / "blocked.png"
        screenshot.parent.mkdir()
        screenshot.write_bytes(b"png")
        assert validate(chrome_success, root) == []
        chrome_failed = {**ready, "page_status": "challenge", "result_count": 0, "reason": "CAPTCHA", "continue_to_next": True, "readiness": {"state": "challenge", "polls": 2, "waited_ms": 3000, "visible_card_count": 0, "screenshot_path": "evidence/blocked.png"}}
        iab_record = {**record, "asin": "B012345679", "channel": "in_app_browser"}
        iab_keyword = {**keyword, "channel": "in_app_browser"}
        iab_ready = {**ready, "channel": "in_app_browser", "result_count": 1}
        fallback = {"templates": [{**base, "keyword_evidence": iab_keyword, "competitor_asins": [iab_record["asin"]], "competitor_evidence": [iab_record], "analysis": {**base["analysis"], "competitors": {"attempts": [chrome_failed, iab_ready], "exhausted": False}}}]}
        assert validate(fallback, root) == []
        phantom_fallback = {"templates": [{**fallback["templates"][0], "analysis": {**fallback["templates"][0]["analysis"], "competitors": {"attempts": [ready, iab_ready], "exhausted": False}}}]}
        assert any("不应回退" in error for error in validate(phantom_fallback, root))
        mismatched_keyword = {"templates": [{**chrome_success["templates"][0], "keyword_evidence": {**keyword, "channel": "in_app_browser"}}]}
        assert any("真实浏览器尝试" in error for error in validate(mismatched_keyword, root))
        failed_keyword = {**keyword, "status": "failed", "source_text": "", "channel": "in_app_browser"}
        iab_failed = {**iab_ready, "page_status": "timeout", "result_count": 0, "reason": "timeout", "readiness": {"state": "timeout", "polls": 8, "waited_ms": 12000, "visible_card_count": 0, "screenshot_path": "evidence/blocked.png"}}
        exhausted = {"templates": [{**base, "text": "国家站：DE\n核心关键词：待补充\n市场扩展数据", "keyword": "待补充", "keyword_evidence": failed_keyword, "keyword_refresh_status": "failed", "competitor_asins": [], "competitor_evidence": [], "analysis": {**base["analysis"], "competitors": {"attempts": [chrome_failed, iab_failed], "exhausted": True}}}]}
        assert validate(exhausted, root) == []
        assert validate({"templates": [{**chrome_success["templates"][0], "competitor_evidence": [{**record, "channel": "firecrawl"}]}]}, root)
        missing_shot = {"templates": [{**exhausted["templates"][0], "analysis": {**exhausted["templates"][0]["analysis"], "competitors": {"attempts": [{**chrome_failed, "readiness": {**chrome_failed["readiness"], "screenshot_path": "evidence/missing.png"}}, iab_failed], "exhausted": True}}}]}
        assert any("真实截图" in error for error in validate(missing_shot, root))
    print("self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.input:
        parser.error("需要 --input")
    data = json.loads(args.input.read_text(encoding="utf-8"))
    errors = validate(data, args.input.parent)
    if errors:
        print("验证失败：", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"验证通过：{len(data['templates'])} 个站点")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
