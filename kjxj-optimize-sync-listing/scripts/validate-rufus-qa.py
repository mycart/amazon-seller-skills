#!/usr/bin/env python3
"""Validate and render evidence-backed Rufus/Alexa shopping Q/A content."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


MARKETPLACE_LANGUAGES = {
    "US": "en_US", "UK": "en_GB", "DE": "de_DE", "FR": "fr_FR",
    "IT": "it_IT", "ES": "es_ES", "JP": "ja_JP", "CA": "en_CA",
    "AU": "en_AU", "IN": "en_IN", "MX": "es_MX", "BR": "pt_BR",
    "IE": "en_IE",
}
TOPIC_COUNTS = {
    "product_identity": 2,
    "feature_material": 3,
    "audience_use_case": 2,
    "buyer_concern": 3,
    "setup_care_included": 2,
}
TOPIC_LABELS = {
    "product_identity": "产品名称、身份与类目",
    "feature_material": "核心功能、材质与卖点",
    "audience_use_case": "目标人群、场景与兼容性",
    "buyer_concern": "买家顾虑与购买异议",
    "setup_care_included": "安装、使用、保养与包装清单",
}
DIRECT_PRODUCT_SOURCE_TYPES = {"user", "product_document", "seller_data", "amazon_product"}
WEB_SOURCE_TYPES = {
    "amazon_product", "amazon_review", "amazon_community_qa",
    "brand_analytics", "competitor_listing", "competitor_review", "public_research",
}
PLACEHOLDER_RE = re.compile(
    r"\[(?:question|answer|keyword|fact|source|product)[^\]]*\]|\b(?:TBD|TODO|XX(?:\.XX)?)\b|待填写",
    re.IGNORECASE,
)
ID_RE = re.compile(r"QA-\d{2}$")
EVIDENCE_ID_RE = re.compile(r"E-\d{2,}$")
CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")


def fail(message: str) -> None:
    raise ValueError(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"无法读取 Rufus Q/A JSON：{path}：{exc}")
    if not isinstance(value, dict):
        fail("Rufus Q/A JSON 顶层必须是对象。")
    return value


def extract_qa(value: dict[str, Any]) -> dict[str, Any]:
    qa = value.get("rufus_qa", value)
    if not isinstance(qa, dict):
        fail("rufus_qa 必须是对象。")
    return qa


def nonempty_strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        fail(f"{field} 必须是非空数组。")
    result = [str(item).strip() for item in value]
    if any(not item for item in result):
        fail(f"{field} 不能包含空值。")
    return result


def validate_rufus_qa(value: dict[str, Any], expected_marketplace: str | None = None) -> dict[str, Any]:
    qa = extract_qa(value)
    status = str(qa.get("status", "")).strip()
    if status not in {"complete", "evidence_insufficient"}:
        fail("rufus_qa.status 必须是 complete 或 evidence_insufficient。")
    if qa.get("target_count") != 12:
        fail("rufus_qa.target_count 必须是 12。")

    marketplace = str(qa.get("marketplace", "")).strip().upper()
    if marketplace not in MARKETPLACE_LANGUAGES:
        fail(f"不支持的 Rufus Q/A 站点：{marketplace}")
    if expected_marketplace and marketplace != expected_marketplace.upper():
        fail(f"Rufus Q/A 站点 {marketplace} 与任务站点 {expected_marketplace.upper()} 不一致。")
    language = str(qa.get("language", "")).strip()
    if language != MARKETPLACE_LANGUAGES[marketplace]:
        fail(f"{marketplace} 站 Rufus Q/A language 必须是 {MARKETPLACE_LANGUAGES[marketplace]}。")

    items = qa.get("items")
    evidence = qa.get("evidence")
    limitations = qa.get("limitations")
    if not isinstance(items, list) or not items:
        fail("rufus_qa.items 必须是非空数组。")
    if not isinstance(evidence, list) or not evidence:
        fail("rufus_qa.evidence 必须是非空数组。")
    if not isinstance(limitations, list):
        fail("rufus_qa.limitations 必须是数组。")
    if status == "complete" and len(items) != 12:
        fail("complete 状态必须包含 12 组 Q/A。")
    if status == "evidence_insufficient":
        if len(items) >= 12:
            fail("evidence_insufficient 状态必须少于 12 组 Q/A。")
        if not [str(item).strip() for item in limitations if str(item).strip()]:
            fail("evidence_insufficient 状态必须提供中文 limitations。")

    evidence_by_id: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(evidence, start=1):
        if not isinstance(raw, dict):
            fail(f"证据 {index} 必须是对象。")
        evidence_id = str(raw.get("id", "")).strip()
        if not EVIDENCE_ID_RE.fullmatch(evidence_id):
            fail(f"证据 {index} 的 id 必须使用 E-01 格式。")
        if evidence_id in evidence_by_id:
            fail(f"证据 id 重复：{evidence_id}")
        source_type = str(raw.get("source_type", "")).strip()
        if not source_type:
            fail(f"{evidence_id} 缺少 source_type。")
        if not str(raw.get("source_title", "")).strip():
            fail(f"{evidence_id} 缺少 source_title。")
        facts = nonempty_strings(raw.get("verified_facts"), f"{evidence_id}.verified_facts")
        used_by = nonempty_strings(raw.get("used_by"), f"{evidence_id}.used_by")
        if any(PLACEHOLDER_RE.search(item) for item in facts):
            fail(f"{evidence_id} 包含占位事实。")
        if source_type in WEB_SOURCE_TYPES:
            source_url = str(raw.get("source_url", "")).strip()
            if not source_url:
                fail(f"网页证据 {evidence_id} 缺少 source_url。")
            parsed_url = urlparse(source_url)
            if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
                fail(f"网页证据 {evidence_id} 的 source_url 不是有效 HTTP(S) URL。")
            retrieved_at = str(raw.get("retrieved_at", "")).strip()
            if not retrieved_at:
                fail(f"网页证据 {evidence_id} 缺少 retrieved_at。")
            try:
                dt.datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
            except ValueError:
                fail(f"网页证据 {evidence_id} 的 retrieved_at 必须是 ISO 时间。")
            if str(raw.get("marketplace", "")).strip().upper() != marketplace:
                fail(f"网页证据 {evidence_id} 的 marketplace 与 Q/A 不一致。")
        evidence_by_id[evidence_id] = {**raw, "source_type": source_type, "used_by": used_by}

    ids: set[str] = set()
    normalized_questions: set[str] = set()
    topics: Counter[str] = Counter()
    for index, raw in enumerate(items, start=1):
        if not isinstance(raw, dict):
            fail(f"Q/A {index} 必须是对象。")
        qa_id = str(raw.get("id", "")).strip()
        if not ID_RE.fullmatch(qa_id):
            fail(f"Q/A {index} 的 id 必须使用 QA-01 格式。")
        if qa_id in ids:
            fail(f"Q/A id 重复：{qa_id}")
        ids.add(qa_id)
        topic = str(raw.get("topic", "")).strip()
        if topic not in TOPIC_COUNTS:
            fail(f"{qa_id} 使用了不支持的 topic：{topic}")
        topics[topic] += 1
        question = str(raw.get("question", "")).strip()
        answer = str(raw.get("answer", "")).strip()
        question_zh = str(raw.get("question_zh", "")).strip()
        answer_zh = str(raw.get("answer_zh", "")).strip()
        if not question or not answer:
            fail(f"{qa_id} 的 question 和 answer 不能为空。")
        if not question_zh or not answer_zh:
            fail(f"{qa_id} 必须提供 question_zh 和 answer_zh 供中文审核。")
        if not CHINESE_RE.search(question_zh) or not CHINESE_RE.search(answer_zh):
            fail(f"{qa_id} 的 question_zh 和 answer_zh 必须包含中文翻译。")
        if PLACEHOLDER_RE.search(question) or PLACEHOLDER_RE.search(answer):
            fail(f"{qa_id} 包含占位内容。")
        normalized = re.sub(r"\W+", "", question, flags=re.UNICODE).casefold()
        if normalized in normalized_questions:
            fail(f"Q/A 问题重复：{qa_id}")
        normalized_questions.add(normalized)
        keywords = nonempty_strings(raw.get("semantic_keywords"), f"{qa_id}.semantic_keywords")
        if any(PLACEHOLDER_RE.search(keyword) for keyword in keywords):
            fail(f"{qa_id} 的 semantic_keywords 包含占位符。")
        refs = nonempty_strings(raw.get("evidence_refs"), f"{qa_id}.evidence_refs")
        missing_refs = [ref for ref in refs if ref not in evidence_by_id]
        if missing_refs:
            fail(f"{qa_id} 引用了不存在的证据：{', '.join(missing_refs)}")
        direct_refs = [ref for ref in refs if evidence_by_id[ref]["source_type"] in DIRECT_PRODUCT_SOURCE_TYPES]
        if not direct_refs:
            fail(f"{qa_id} 缺少直接商品事实证据。")
        for ref in refs:
            if qa_id not in evidence_by_id[ref]["used_by"]:
                fail(f"证据 {ref} 的 used_by 未包含 {qa_id}。")

    unknown_used_by = sorted({qa_id for raw in evidence_by_id.values() for qa_id in raw["used_by"] if qa_id not in ids})
    if unknown_used_by:
        fail("证据 used_by 引用了不存在的 Q/A：" + ", ".join(unknown_used_by))
    expected_ids = {f"QA-{index:02d}" for index in range(1, len(items) + 1)}
    if ids != expected_ids:
        fail("Q/A id 必须从 QA-01 开始连续编号。")
    if status == "complete" and dict(topics) != TOPIC_COUNTS:
        fail(f"complete 状态主题数量必须为 {TOPIC_COUNTS}，实际为 {dict(topics)}。")

    return {
        "ok": True,
        "status": status,
        "marketplace": marketplace,
        "language": language,
        "qa_count": len(items),
        "evidence_count": len(evidence),
        "topic_counts": dict(topics),
    }


def render_markdown(value: dict[str, Any]) -> str:
    qa = extract_qa(value)
    lines = [
        "# Rufus / Alexa for Shopping 商品 Q/A（高级 A+ 备用）",
        "",
        f"**站点：** Amazon {qa['marketplace']} | **状态：** {qa['status']} | **目标数量：** {qa['target_count']}",
        "",
        "> 以下内容采用公开的事实可回答性原则，不代表 Amazon 官方算法评分，也不承诺被引用、推荐或提升排名。",
        "",
    ]
    for item in qa["items"]:
        keywords = ", ".join(str(keyword) for keyword in item["semantic_keywords"])
        refs = ", ".join(str(ref) for ref in item["evidence_refs"])
        lines.extend([
            f"## {item['id']} | {TOPIC_LABELS[item['topic']]}",
            "",
            f"**Q:** {item['question']}",
            "",
            f"**中文翻译：** {item['question_zh']}",
            "",
            f"**A:** {item['answer']}",
            "",
            f"**中文翻译：** {item['answer_zh']}",
            "",
            f"**语义关键词：** {keywords}",
            "",
            f"**证据编号：** {refs}",
            "",
        ])
    lines.extend(["# 中文证据附录", ""])
    for evidence in qa["evidence"]:
        facts = "；".join(str(fact) for fact in evidence["verified_facts"])
        used_by = ", ".join(str(item) for item in evidence["used_by"])
        lines.extend([
            f"## {evidence['id']} | {evidence['source_type']}",
            "",
            f"**来源：** {evidence['source_title']}",
            f"**URL：** {evidence.get('source_url') or '本地/用户资料'}",
            f"**检索时间：** {evidence.get('retrieved_at') or '用户提供'}",
            f"**已验证事实：** {facts}",
            f"**对应 Q/A：** {used_by}",
            "",
        ])
    if qa["limitations"]:
        lines.extend(["# 资料限制", ""])
        lines.extend(f"- {item}" for item in qa["limitations"])
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Rufus Q/A JSON or listing report JSON")
    parser.add_argument("--marketplace", help="Expected marketplace code")
    parser.add_argument("--output", help="Validation JSON output")
    parser.add_argument("--markdown", help="Rendered Markdown output")
    args = parser.parse_args()

    value = load_json(Path(args.input).expanduser().resolve())
    result = validate_rufus_qa(value, args.marketplace)
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.markdown:
        markdown = Path(args.markdown).expanduser().resolve()
        markdown.parent.mkdir(parents=True, exist_ok=True)
        markdown.write_text(render_markdown(value), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
