#!/usr/bin/env python3
"""Render localized marketplace prompt templates from audited market data.

The renderer never retrieves web data. Callers provide current Amazon and FX
evidence in market-data.json. Copy-ready template text and diagnostic analysis
are deliberately separate so operational status never leaks into prompts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ASIN_RE = re.compile(r"\b[A-Z0-9]{10}\b", re.IGNORECASE)
FIELD_RE = re.compile(r"^(?P<prefix>\s*(?:\d+\.\s*)?[^:\n：]{1,48}[：:]\s*)(?P<value>.*)$")
MONEY_LABELS = ("售价", "成本", "日预算", "price", "cost", "daily budget")
MARKET_DOMAINS = {
    "US": "amazon.com", "CA": "amazon.ca", "MX": "amazon.com.mx", "UK": "amazon.co.uk",
    "DE": "amazon.de", "FR": "amazon.fr", "IT": "amazon.it", "ES": "amazon.es",
    "NL": "amazon.nl", "SE": "amazon.se", "PL": "amazon.pl", "BE": "amazon.com.be",
    "TR": "amazon.com.tr", "IE": "amazon.ie",
}
RETRIEVAL_CHANNELS = ("chrome", "in_app_browser", "firecrawl", "http_diagnostic")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("markets"), list):
        raise ValueError("market-data.json 必须是包含 markets 数组的对象")
    return data


def field_kind(label: str) -> str | None:
    normalized = re.sub(r"\s+", "", label).lower()
    if any(token in normalized for token in ("amazon站点", "国家站", "marketplace", "站点", "国家")):
        return "market"
    if any(token in normalized for token in ("核心关键词", "corekeyword", "keyword")):
        return "keyword"
    if any(token in normalized for token in ("竞品asin", "competitorasin", "competitors")):
        return "competitors"
    if any(token in normalized for token in ("产品类型", "商品类型", "producttype", "productcategory", "itemtype")):
        return "product_type"
    if any(token in normalized for token in ("材质", "材料", "material", "fabric")):
        return "material"
    if any(token in normalized for token in ("产品事实", "核心卖点", "产品卖点", "卖点", "事实/卖点", "facts", "features", "benefits", "highlights")):
        return "facts"
    if any(token in normalized for token in ("变体", "variation", "variant")):
        return "variants"
    if any(token in normalized for token in MONEY_LABELS):
        return "money"
    if any(token in normalized for token in ("主asin", "primaryasin", "targetasin")):
        return "primary_asin"
    return None


def normalize_asins(values: Any) -> list[str]:
    if isinstance(values, str):
        values = ASIN_RE.findall(values)
    if not isinstance(values, list):
        return []
    output: list[str] = []
    for value in values:
        asin = str(value.get("asin", "")) if isinstance(value, dict) else str(value)
        asin = asin.upper()
        if ASIN_RE.fullmatch(asin) and asin not in output:
            output.append(asin)
    return output[:3]


def normalized_competitor_records(values: Any, code: str) -> list[dict[str, Any]]:
    """Keep only competitors proven by a visible card on the target marketplace."""
    if not isinstance(values, list):
        return []
    domain = MARKET_DOMAINS.get(code)
    accepted: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, dict):
            continue
        asin = str(value.get("asin", "")).upper()
        source_type = str(value.get("source_type", "")).lower()
        title = str(value.get("title", "")).strip()
        evidence_url = str(value.get("evidence_url", "")).strip()
        captured_at = str(value.get("captured_at", "")).strip()
        channel = str(value.get("channel", "")).strip()
        position = value.get("position")
        parsed_url = urlparse(evidence_url)
        host = parsed_url.hostname or ""
        if (
            not ASIN_RE.fullmatch(asin) or asin in seen or source_type not in ("organic", "sponsored")
            or not title or not captured_at or channel not in RETRIEVAL_CHANNELS or not isinstance(position, int)
            or position < 1 or parsed_url.scheme != "https" or not domain or not (host == domain or host.endswith("." + domain))
        ):
            continue
        seen.add(asin)
        accepted.append({"asin": asin, "source_type": source_type, "title": title, "position": position,
                         "channel": channel, "evidence_url": evidence_url, "captured_at": captured_at})
    accepted.sort(key=lambda item: (item["source_type"] == "sponsored", item["position"]))
    return accepted[:3]


def competitor_attempts(market: dict[str, Any]) -> list[dict[str, Any]]:
    values = market.get("competitor_attempts", [])
    return [item for item in values if isinstance(item, dict)] if isinstance(values, list) else []


def localized_value(market: dict[str, Any], key: str, original: str) -> str:
    value = market.get(key)
    return str(value).strip() if isinstance(value, str) and value.strip() else original


def localized_field_value(market: dict[str, Any], label: str, original: str) -> str:
    """Use an audited replacement for an otherwise unrecognized template field."""
    fields = market.get("localized_fields", {})
    if not isinstance(fields, dict):
        return original
    normalized = re.sub(r"\s+", "", label).lower()
    for candidate in (label, normalized):
        value = fields.get(candidate)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return original


def localized_variants(market: dict[str, Any], original: str) -> list[str]:
    values = market.get("variants", [])
    if not isinstance(values, list) or not values:
        return [original]
    rendered: list[str] = []
    for value in values:
        if not isinstance(value, dict):
            rendered.append(str(value))
            continue
        asin = str(value.get("asin", "")).upper()
        if not ASIN_RE.fullmatch(asin):
            continue
        color = str(value.get("localized_color", value.get("color", ""))).strip()
        size = str(value.get("localized_size", value.get("size", ""))).strip()
        details = "-".join(part for part in (asin, color) if part)
        rendered.append(f"{details}-({size})" if size else details)
    return rendered or [original]


def money_value(original: str, fx: dict[str, Any]) -> str:
    if not fx or fx.get("status") != "verified":
        return original
    try:
        match = re.search(r"[-+]?\d+(?:[.,]\d+)?", original)
        amount = Decimal(match.group(0).replace(",", ".")) if match else None
        rate = Decimal(str(fx["rate"]))
        target = str(fx["target_currency"]).strip()
        if amount is None or not target:
            raise InvalidOperation
    except (KeyError, InvalidOperation):
        return original
    return f"{amount * rate:.2f} {target}"


def analysis_for(market: dict[str, Any], fx: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    evidence = market.get("evidence", {}) if isinstance(market.get("evidence"), dict) else {}
    variants = market.get("variants", []) if isinstance(market.get("variants"), list) else []
    localization = market.get("localization", {}) if isinstance(market.get("localization"), dict) else {}
    attempts = competitor_attempts(market)
    return {
        "captured_at": market.get("captured_at"),
        "primary_asin": {
            "status": evidence.get("status", "pending"),
            "availability": evidence.get("availability", "unknown"),
            "reason": evidence.get("reason"),
            "url": evidence.get("url"),
        },
        "variants": [
            {"asin": item.get("asin"), "status": item.get("status", "pending"), "availability": item.get("availability", "unknown"), "reason": item.get("reason")}
            for item in variants if isinstance(item, dict)
        ],
        "competitors": {
            "status": "verified" if records else market.get("competitor_status", "pending"),
            "reason": market.get("competitor_reason"),
            "sources": [item["source_type"] for item in records],
            "records": records,
            "attempts": attempts,
            "exhausted": bool(market.get("competitor_attempts_exhausted", False)),
        },
        "localization": localization,
        "fx": {
            "status": fx.get("status", "pending"),
            "rate": fx.get("rate"),
            "target_currency": fx.get("target_currency"),
            "source": fx.get("source"),
            "captured_at": fx.get("captured_at"),
            "reason": fx.get("reason"),
            "original_amounts": market.get("original_amounts", {}),
        },
    }


def render(template: str, market: dict[str, Any], source_market: str | None) -> tuple[str, dict[str, Any]]:
    country = str(market.get("country", market.get("code", "待确认")))
    code = str(market.get("code", "")).upper()
    fx = market.get("fx", {}) if isinstance(market.get("fx"), dict) else {}
    keyword = str(market.get("keyword", "待补充"))
    competitor_records = normalized_competitor_records(market.get("competitors"), code)
    competitors = [record["asin"] for record in competitor_records]
    competitor_text = "、".join(competitors) if competitors else "待补充"
    present: set[str] = set()
    lines: list[str] = []

    for raw in template.splitlines():
        match = FIELD_RE.match(raw)
        if not match:
            updated = raw
            if source_market:
                updated = re.sub(rf"(?<![A-Z]){re.escape(source_market.upper())}(?![A-Z])", code, updated)
            lines.append(updated)
            continue
        prefix, value = match.group("prefix"), match.group("value")
        label = prefix.rstrip(" ：:")
        kind = field_kind(label)
        replacement = value
        if kind == "market":
            present.add(kind)
            replacement = code if "站" in label or "market" in label.lower() else country
        elif kind == "keyword":
            present.add(kind)
            replacement = keyword
        elif kind == "competitors":
            present.add(kind)
            replacement = competitor_text
        elif kind == "product_type":
            present.add(kind)
            replacement = localized_value(market, "localized_product_type", value)
        elif kind == "material":
            present.add(kind)
            replacement = localized_value(market, "localized_material", value)
        elif kind == "facts":
            present.add(kind)
            replacement = localized_value(market, "localized_facts", value)
        elif kind == "variants":
            present.add(kind)
            variants = localized_variants(market, value)
            lines.append(prefix + variants[0])
            lines.extend("   " + item for item in variants[1:])
            continue
        elif kind == "money":
            present.add(kind)
            replacement = money_value(value, fx)
        elif kind is None:
            replacement = localized_field_value(market, label, value)
        lines.append(prefix + replacement)

    additions = [f"目标市场：{country}（{code}）"]
    if "product_type" not in present and market.get("localized_product_type"):
        additions.append(f"产品类型：{market['localized_product_type']}")
    if "keyword" not in present:
        additions.append(f"核心关键词：{keyword}")
    if "competitors" not in present:
        additions.append(f"竞品ASIN（最多3个）：{competitor_text}")
    lines.extend(["", "市场扩展数据", *["   " + item for item in additions]])

    metadata = {
        "code": code,
        "country": country,
        "keyword": keyword,
        "localized_product_type": market.get("localized_product_type"),
        "competitor_asins": competitors,
        "competitor_evidence": competitor_records,
        "fx": fx,
        "analysis": analysis_for(market, fx, competitor_records),
    }
    return "\n".join(lines).rstrip() + "\n", metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path)
    parser.add_argument("--market-data", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not all((args.template, args.market_data, args.output)):
        parser.error("需要 --template、--market-data 和 --output")
    template = args.template.read_text(encoding="utf-8")
    data = load_json(args.market_data)
    digest = hashlib.sha256(template.encode("utf-8")).hexdigest()
    templates = []
    for market in data["markets"]:
        if not isinstance(market, dict):
            raise ValueError("markets 中的每项必须是对象")
        text, metadata = render(template, market, data.get("source_market"))
        templates.append({**metadata, "text": text})
    output = {"generated_at": datetime.now(timezone.utc).isoformat(), "source_template_sha256": digest, "templates": templates}
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


def self_test() -> int:
    template = "国家站：UK\n主ASIN：B0GKDRNR72\n产品类型：cat scratching mat\n材质：sisal\n产品事实/卖点：strong adhesive, durable\n变体：B0GKDK191Q-white-(60 x 40 cm)\n竞品ASIN：B0FXWM6BWB\n售价：18 GBP\n"
    market = {
        "code": "DE", "country": "德国", "keyword": "selbstklebende Katzenkratzmatte",
        "localized_product_type": "selbstklebende Katzenkratzmatte", "localized_material": "Sisal",
        "localized_facts": "starke Haftung, langlebig", "competitors": [{"asin": "B0D4TPT9GW", "source_type": "organic", "title": "Katzenkratzmatte", "position": 1, "channel": "chrome", "evidence_url": "https://www.amazon.de/s?k=katzenkratzmatte", "captured_at": "2026-08-09T00:00:00Z"}],
        "competitor_attempts": [{"channel": "chrome", "captured_at": "2026-08-09T00:00:00Z", "url": "https://www.amazon.de/s?k=katzenkratzmatte", "page_status": "ok", "result_count": 1, "reason": "", "continue_to_next": False}],
        "variants": [{"asin": "B0GKDK191Q", "localized_color": "Weiß", "localized_size": "60 x 40 cm", "status": "unavailable", "availability": "unavailable"}],
        "evidence": {"status": "verified", "availability": "unavailable", "reason": "商品页已核验，当前不可售"},
        "localization": {"product_type": {"status": "verified"}},
        "fx": {"status": "verified", "rate": "1.17", "target_currency": "EUR", "source": "test", "captured_at": "2026-08-09T00:00:00Z"},
    }
    text, meta = render(template, market, "UK")
    assert "产品类型：selbstklebende Katzenkratzmatte" in text
    assert "材质：Sisal" in text and "产品事实/卖点：starke Haftung, langlebig" in text
    assert "B0GKDK191Q-Weiß-(60 x 40 cm)" in text and "21.06 EUR" in text
    assert "不可售" not in text and "待实时核验" not in text
    assert meta["analysis"]["primary_asin"]["availability"] == "unavailable"
    pipeline_template = "使用 $kjxj-amazon-listing-pipeline\n国家站：UK\n主ASIN：B0GKDRNR72\n"
    pending = {"code": "US", "country": "美国", "keyword": "self adhesive cat scratch mat", "localized_product_type": "self adhesive cat scratch mat", "competitors": [], "evidence": {"status": "challenge", "reason": "CAPTCHA"}, "competitor_status": "failed", "competitor_reason": "CAPTCHA", "competitor_attempts_exhausted": True, "competitor_attempts": [{"channel": channel, "captured_at": "2026-08-09T00:00:00Z", "url": "https://www.amazon.com/s?k=cat+scratch+mat", "page_status": "blocked", "result_count": 0, "reason": "CAPTCHA", "continue_to_next": channel != "http_diagnostic"} for channel in RETRIEVAL_CHANNELS], "fx": {"status": "pending", "reason": "汇率源不可用"}, "localization": {"product_type": {"status": "pending", "reason": "CAPTCHA"}}}
    pending_text, pending_meta = render(pipeline_template, pending, "UK")
    assert "产品类型：self adhesive cat scratch mat" in pending_text
    assert "竞品ASIN（最多3个）：待补充" in pending_text
    assert "CAPTCHA" not in pending_text and "待实时核验" not in pending_text
    assert pending_meta["analysis"]["fx"]["reason"] == "汇率源不可用"
    print("self-test passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(2)
