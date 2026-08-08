#!/usr/bin/env python3
"""Build a verified Listing Pipeline review package from frozen Markdown files."""
import argparse
import hashlib
import json
import re
from pathlib import Path


MARKETPLACE_DOMAINS = {
    "US": "www.amazon.com", "UK": "www.amazon.co.uk", "DE": "www.amazon.de",
    "FR": "www.amazon.fr", "IT": "www.amazon.it", "ES": "www.amazon.es",
    "JP": "www.amazon.co.jp", "CA": "www.amazon.ca", "AU": "www.amazon.com.au",
    "IN": "www.amazon.in", "MX": "www.amazon.com.mx", "BR": "www.amazon.com.br",
}


def read_text(path):
    data = Path(path).read_bytes()
    if not data:
        raise ValueError(f"empty file: {path}")
    try:
        return data.decode("utf-8"), hashlib.sha256(data).hexdigest()
    except UnicodeDecodeError as exc:
        raise ValueError(f"non-UTF-8 file: {path}") from exc


def write_text(path, text):
    with Path(path).open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return read_text(path)


def section(text, heading):
    match = re.search(rf"(?m)^{re.escape(heading)}\s*$", text)
    if not match:
        raise ValueError(f"missing required section: {heading}")
    tail = text[match.end():]
    next_heading = re.search(r"(?m)^#{1,3}\s+", tail)
    return tail[:next_heading.start() if next_heading else len(tail)].strip()


def first_value(body, labels=()):
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        for label in labels:
            if line.casefold().startswith(label.casefold() + ":"):
                return line.split(":", 1)[1].strip()
        return line
    return ""


def extract_listing(text):
    title = first_value(section(text, "### Title"), ("Title",))
    bullets_body = section(text, "### Bullet Points")
    bullets = [
        re.sub(r"^\s*(?:\d+[.)]|[-*])\s+", "", line).strip()
        for line in bullets_body.splitlines()
        if re.match(r"^\s*(?:\d+[.)]|[-*])\s+\S", line)
    ]
    description = section(text, "### Product Description").strip()
    backend = first_value(section(text, "### Backend Search Terms"), ("Backend Search Terms",))
    if not title or len(bullets) != 5 or not description or not backend:
        raise ValueError("Listing source must contain a Title, exactly five bullets, description, and backend search terms")
    return {"title": title, "bullets": bullets, "description": description, "backend": backend}


def extract_title_options(text, selected_title, selected_highlight):
    options = []
    matches = list(re.finditer(r"(?m)^### Option\s+(\d+)\s*$", text))
    for index, match in enumerate(matches):
        body = text[match.end():matches[index + 1].start() if index + 1 < len(matches) else len(text)]
        title_match = re.search(r"(?mi)^Title:\s*(.+)$", body)
        highlight_match = re.search(r"(?mi)^Item Highlights:\s*(.+)$", body)
        if title_match and highlight_match:
            options.append({"option": match.group(1), "title": title_match.group(1).strip(), "highlights": highlight_match.group(1).strip()})
    selected = next((item for item in options if item["title"] == selected_title and item["highlights"] == selected_highlight), None)
    if not selected:
        raise ValueError("selected 2026 Title and Item Highlights do not match a frozen title option")
    return options, selected


def parse_ppc(text):
    current = None
    mode = None
    campaigns = []
    for line in text.splitlines():
        heading = re.match(r"^## Campaign \d+: (.+)$", line)
        if heading:
            current = {"name": heading.group(1), "positive": [], "negative": []}
            campaigns.append(current)
            mode = None
            continue
        if line.strip().lower() == "positive keywords":
            mode = "positive"
            continue
        if line.strip().lower() == "negative keywords":
            mode = "negative"
            continue
        item = re.match(r"^- \[?(.+?)\]?$", line)
        if current and mode and item:
            keyword = item.group(1).strip()
            if not re.fullmatch(r"B0[A-Z0-9]{8}", keyword):
                current[mode].append(keyword)
    if not campaigns or not any(c["positive"] or c["negative"] for c in campaigns):
        raise ValueError("unable to parse PPC positive or negative keywords")
    return campaigns


def ppc_copy_area(campaigns):
    parts = ["## PPC 关键词复制区"]
    for campaign in campaigns:
        parts.extend([f"### {campaign['name']}", "", "正向关键词", "```", *campaign["positive"], "```", "否定关键词", "```", *campaign["negative"], "```", ""])
    return "\n".join(parts)


def extract_qa(text):
    positions = list(re.finditer(r"(?m)^Q(\d+)\.\s+.+$", text))
    pairs = []
    for index, match in enumerate(positions):
        block = text[match.start():positions[index + 1].start() if index + 1 < len(positions) else len(text)].strip()
        answer = re.search(r"(?m)^A" + re.escape(match.group(1)) + r"\.\s+.+$", block)
        translation = re.search(r"(?m)^仅供审核：.+$", block)
        if not answer or not translation or translation.start() < answer.start():
            raise ValueError(f"Rufus Q{match.group(1)} lacks an English answer or directly following Chinese audit translation")
        pairs.append(block)
    if len(pairs) < 8:
        raise ValueError("Rufus source must contain at least eight evidence-backed Q/A pairs with Chinese audit translations")
    return pairs


def load_evidence(path, marketplace):
    raw, checksum = read_text(path)
    try:
        evidence = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid evidence JSON: {exc}") from exc
    primary = evidence.get("primary") or {}
    expected_domain = MARKETPLACE_DOMAINS.get(marketplace)
    if primary.get("status") != "verified" or primary.get("asin") != evidence.get("primary_asin"):
        raise ValueError("primary ASIN evidence gate is not verified")
    if expected_domain and primary.get("domain") != expected_domain:
        raise ValueError("primary ASIN evidence domain does not match marketplace")
    if not primary.get("title") or not primary.get("final_url") or not primary.get("captured_at"):
        raise ValueError("primary ASIN evidence is missing title, final URL, or capture timestamp")
    return evidence, checksum


def load_frozen_checksums(path):
    raw, checksum = read_text(path)
    try:
        values = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid frozen source checksum manifest: {exc}") from exc
    if not isinstance(values, dict) or not values or not all(isinstance(key, str) and isinstance(value, str) for key, value in values.items()):
        raise ValueError("frozen source checksum manifest must be a non-empty path-to-SHA-256 object")
    return values, checksum


def load_variant_sources(path, actions, frozen_checksums):
    """Load one frozen Listing/Title pair per writable (marketplace, ASIN)."""
    raw, checksum = read_text(path)
    try:
        entries = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid variant source manifest: {exc}") from exc
    if not isinstance(entries, dict) or not entries:
        raise ValueError("variant source manifest must be a non-empty ASIN object")

    required = {(action.get("marketplace"), action.get("asin")) for action in actions}
    loaded = {}
    for key, entry in entries.items():
        if not isinstance(entry, dict):
            raise ValueError(f"invalid variant source for {key}")
        asin = entry.get("asin", key).upper()
        marketplace = entry.get("marketplace", "")
        pair = (marketplace, asin)
        if pair not in required:
            continue
        evidence = entry.get("evidence", {})
        if evidence.get("status") != "verified" or evidence.get("asin") != asin:
            raise ValueError(f"variant {asin} lacks verified page evidence")
        listing_path = Path(entry.get("listing", "")).resolve()
        title_path = Path(entry.get("title", "")).resolve()
        listing_text, listing_checksum = read_text(listing_path)
        title_text, title_checksum = read_text(title_path)
        if frozen_checksums.get(str(listing_path)) != listing_checksum:
            raise ValueError(f"frozen Listing checksum mismatch for {asin}")
        if frozen_checksums.get(str(title_path)) != title_checksum:
            raise ValueError(f"frozen Title checksum mismatch for {asin}")
        if listing_path == title_path:
            raise ValueError(f"variant {asin} reuses the same file for Listing and Title")
        if pair in loaded:
            raise ValueError(f"duplicate variant source for {marketplace}/{asin}")
        loaded[pair] = {
            "asin": asin, "marketplace": marketplace,
            "listing_path": listing_path, "title_path": title_path,
            "listing_text": listing_text, "title_text": title_text,
            "listing_checksum": listing_checksum, "title_checksum": title_checksum,
            "variant": entry.get("variant", {}), "evidence": evidence,
        }
    missing = required - set(loaded)
    if missing:
        raise ValueError(f"missing verified variant sources: {sorted(missing)}")
    return loaded, checksum


def xlsm_summary(plan):
    actions = plan.get("actions", [])
    if not actions:
        return "无法执行：只读预检未返回任何回填动作。"
    rows = ["| ASIN | 行号 | 工作表 | 标题方案 |", "|---|---:|---|---|"]
    for action in actions:
        fields = action.get("fields", {})
        rows.append(f"| {action.get('asin', '待预检确认')} | {','.join(map(str, action.get('rows', []))) or '待预检确认'} | {action.get('sheet', '待预检确认')} | {fields.get('title_mode', '待预检确认')} |")
    return "\n".join([
        "输出副本采用 `YYYY-MM-DD_Amazon<站点>_分类商品报告_Listing同步完成_<ASIN数量>ASIN_vN.<扩展名>` 命名。当前仅完成只读预检，尚未写入 XLSM。",
        "", *rows, "",
        "字段映射、站点证据、行处理计划和保留字段以只读预检为准。Title、Item Name 与 Item Highlight 使用已选择的 2026 Title 方案；Description、五点和后台词来自冻结的常规 Listing 输出。仅变化的 Listing 单元格将标记 `#C6EFCE`；第 7 行起仅保留更新子体和直接父体行，写后验证 OOXML。",
    ])


def evidence_boundary(evidence):
    primary = evidence["primary"]
    lines = [
        f"主 ASIN {primary['asin']} 页面证据已验证：{primary['final_url']}。",
        f"抓取时间：{primary['captured_at']}。",
    ]
    failures = [item for item in evidence.get("competitors", []) if item.get("status") != "verified"]
    if failures:
        lines.append("以下竞品未取得可验证页面数据，未用于 Listing、PPC、评论或搜索结论：")
        lines.extend(f"- {item.get('asin', '待确认')}：{item.get('failure_reason', '待确认')}" for item in failures)
    else:
        lines.append("竞品页面证据均已验证；仅已验证字段可用于竞品衍生结论。")
    return "\n".join(lines)


def variant_listing_summary(action, source):
    listing = extract_listing(source["listing_text"])
    fields = action["fields"]
    options, selected = extract_title_options(source["title_text"], fields.get("title", ""), fields.get("item_highlight", ""))
    variant = source.get("variant", {})
    attributes = [f"- {key}: {value}" for key, value in variant.items() if value not in (None, "", "待确认")]
    if not attributes:
        attributes = ["- 变体属性：待确认"]
    content = [
        f"## SKU 变体 Listing: {source['asin']}", "", "### 变体属性", *attributes, "",
        "### 常规 Listing", "", f"#### Title\n\n{listing['title']}", "", "#### 五点", "",
        *[f"{index}. {value}" for index, value in enumerate(listing["bullets"], 1)], "",
        f"#### Description\n\n{listing['description']}", "", f"#### Backend Search Terms\n\n{listing['backend']}", "",
        "### 2026 Title 方案", "",
        *[f"#### Option {item['option']}\n\nTitle: {item['title']}\n\nItem Highlights: {item['highlights']}" for item in options], "",
        f"已选择方案：Option {selected['option']}。", "",
        f"### XLSM 目标\n\n工作表：{action.get('sheet', '待预检确认')}；行：{','.join(map(str, action.get('rows', []))) or '待预检确认'}。",
    ]
    return "\n".join(content), listing, selected


def validate_action_variant(action, source):
    """Require the review plan to bind an action to the same variant facts."""
    planned = action.get("variant")
    if planned is None:
        raise ValueError(f"action {action.get('asin')} is missing variant preflight evidence")
    for key, value in source.get("variant", {}).items():
        if value in (None, "", "待确认"):
            continue
        if planned.get(key) != value:
            raise ValueError(f"variant conflict for {action.get('asin')}: {key}")
    report_row = planned.get("report_row")
    if report_row is not None and report_row not in action.get("rows", []):
        raise ValueError(f"variant conflict for {action.get('asin')}: report_row")
    preflight = action.get("preflight", {})
    if preflight and str(preflight.get("product_id_type", "")).upper() != "ASIN":
        raise ValueError(f"variant conflict for {action.get('asin')}: product_id_type")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--listing")
    parser.add_argument("--title")
    parser.add_argument("--variant-sources", help="JSON manifest mapping each ASIN to frozen Listing/Title sources and verified evidence")
    parser.add_argument("--ppc", required=True)
    parser.add_argument("--rufus", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--frozen-source-manifest", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if bool(args.listing) != bool(args.title):
        raise ValueError("--listing and --title must be provided together")
    if not args.variant_sources and not args.listing:
        raise ValueError("provide --variant-sources or a single --listing/--title pair")
    sources = [("PPC Campaign", Path(args.ppc)), ("Rufus Q/A", Path(args.rufus))]
    bodies, manifest = [], {"sources": {}, "outputs": {}, "checks": {}}
    frozen_checksums, frozen_manifest_checksum = load_frozen_checksums(args.frozen_source_manifest)
    manifest["sources"][str(Path(args.frozen_source_manifest))] = frozen_manifest_checksum
    for label, path in sources:
        body, checksum = read_text(path)
        expected_checksum = frozen_checksums.get(str(path.resolve()))
        if expected_checksum != checksum:
            raise ValueError(f"frozen source checksum mismatch: {path}")
        bodies.append((label, path.name, body))
        manifest["sources"][str(path)] = checksum
    plan_text, plan_checksum = read_text(args.plan)
    plan = json.loads(plan_text)
    manifest["sources"][str(Path(args.plan))] = plan_checksum
    actions = plan.get("actions", [])
    if not actions or any(action.get("status") != "ready" for action in actions):
        raise ValueError("read-only sync plan is not ready")
    marketplace = actions[0].get("marketplace", "")
    evidence, evidence_checksum = load_evidence(args.evidence, marketplace)
    manifest["sources"][str(Path(args.evidence))] = evidence_checksum

    if args.variant_sources:
        variants, variant_manifest_checksum = load_variant_sources(Path(args.variant_sources), actions, frozen_checksums)
        manifest["sources"][str(Path(args.variant_sources))] = variant_manifest_checksum
    else:
        listing_path, title_path = Path(args.listing).resolve(), Path(args.title).resolve()
        listing_text, listing_checksum = read_text(listing_path)
        title_text, title_checksum = read_text(title_path)
        if frozen_checksums.get(str(listing_path)) != listing_checksum or frozen_checksums.get(str(title_path)) != title_checksum:
            raise ValueError("frozen single-variant source checksum mismatch")
        first = actions[0]
        variants = {(first["marketplace"], first["asin"]): {"asin": first["asin"], "marketplace": first["marketplace"], "listing_path": listing_path, "title_path": title_path, "listing_text": listing_text, "title_text": title_text, "listing_checksum": listing_checksum, "title_checksum": title_checksum, "variant": {}, "evidence": evidence["primary"]}}
        if len(actions) != 1:
            raise ValueError("multiple actions require --variant-sources")
    for source in variants.values():
        manifest["sources"][str(source["listing_path"])] = source["listing_checksum"]
        manifest["sources"][str(source["title_path"])] = source["title_checksum"]

    ppc_body = next(body for label, _name, body in bodies if label == "PPC Campaign")
    rufus_body = next(body for label, _name, body in bodies if label == "Rufus Q/A")
    campaigns = parse_ppc(ppc_body)
    qa_pairs = extract_qa(rufus_body)
    variant_summaries = []
    for action in actions:
        source = variants[(action["marketplace"], action["asin"])]
        if args.variant_sources:
            validate_action_variant(action, source)
        summary, listing, selected = variant_listing_summary(action, source)
        variant_summaries.append((action, source, summary, listing, selected))

    sync_path = output_dir / f"{args.base}-sync-review.md"
    sync_parts = ["# Listing 同步审核包", ""]
    for action, source, _summary, _listing, _selected in variant_summaries:
        sync_parts.extend([f"--- Listing Optimization: {source['asin']} / {source['listing_path'].name} ---", "", source["listing_text"].rstrip(), "", f"--- Title Optimizer: {source['asin']} / {source['title_path'].name} ---", "", source["title_text"].rstrip(), ""])
    for label, filename, body in bodies:
        sync_parts.extend([f"--- {label}: {filename} ---", "", body.rstrip(), ""])
        if label == "PPC Campaign":
            sync_parts.extend([ppc_copy_area(campaigns), ""])
    sync_parts.extend(["## XLSM 回填计划", "", "XLSM Title、商品名称与商品亮点使用独立选择的 2026 Title 方案；原始 Listing Title 不会被标记为 2026 字段。", "", "确认回填", ""])
    sync_text = "\n".join(sync_parts)
    for _label, _filename, body in bodies:
        if body.rstrip() not in sync_text:
            raise ValueError("sync review failed to embed a frozen source body")
    for _action, source, _summary, _listing, _selected in variant_summaries:
        if source["listing_text"].rstrip() not in sync_text or source["title_text"].rstrip() not in sync_text:
            raise ValueError("sync review failed to embed a frozen variant source")
    _, manifest["outputs"][str(sync_path)] = write_text(sync_path, sync_text)

    summary_path = output_dir / f"{args.base}-chinese-summary-review.md"
    summary = "\n".join(["# Listing 审核摘要", "", *[item[2] for item in variant_summaries], "", "## PPC Campaign", "", ppc_body.rstrip(), "", ppc_copy_area(campaigns), "", "## Rufus Q/A", "", "\n\n".join(qa_pairs), "", "## XLSM 回填说明", "", xlsm_summary(plan), "", "## 证据边界", "", evidence_boundary(evidence), ""])
    required_values = [value for _action, _source, _summary, listing, selected in variant_summaries for value in [listing["title"], listing["description"], listing["backend"], selected["title"], selected["highlights"], *listing["bullets"]]] + qa_pairs
    if not all(value in summary for value in required_values):
        raise ValueError("Chinese summary extraction is incomplete")
    _, manifest["outputs"][str(summary_path)] = write_text(summary_path, summary)

    overview_path = output_dir / "overview.md"
    overview = "\n".join(["# 审核包导航", "", *[f"- [Listing Optimization {source['asin']}]({source['listing_path']})" for source in variants.values()], *[f"- [Title Optimizer {source['asin']}]({source['title_path']})" for source in variants.values()], *[f"- [{label}]({path.resolve()})" for label, path in sources], f"- [中文审核摘要]({summary_path.resolve()})", f"- [同步审核包]({sync_path.resolve()})", ""])
    _, manifest["outputs"][str(overview_path)] = write_text(overview_path, overview)

    expected = [source["listing_path"] for source in variants.values()] + [source["title_path"] for source in variants.values()] + [path for _, path in sources] + [sync_path, summary_path, overview_path]
    for path in expected:
        _, checksum = read_text(path)
        if path in (sync_path, summary_path, overview_path):
            manifest["outputs"][str(path)] = checksum
    manifest["checks"] = {
        "embedded_source_sha256": {path: checksum for path, checksum in manifest["sources"].items() if path.endswith(".md")},
        "summary_required_sections": ["SKU 变体 Listing", "常规 Listing", "2026 Title 方案", "PPC Campaign", "PPC 关键词复制区", "Rufus Q/A", "XLSM 回填说明", "证据边界"],
        "primary_evidence_status": evidence["primary"]["status"],
    }
    manifest_path = output_dir / f"{args.base}-manifest.json"
    Path(manifest_path).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ready", "files": [str(p) for p in expected], "manifest": str(manifest_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
