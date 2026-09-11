# -*- coding: utf-8 -*-
"""
parser.py
解析亚马逊卖家后台导出的《月度报告摘要》PDF（MonthlySummary），
不论报告是哪国语言（法语/德语/英语...），都能提取出：
  - 店铺信息（显示名、法人实体名、国家、账期）
  - 四大总计：收入 / 支出 / 税费 / 转账
  - 关键经营指标（广告费、FBA费用、退款、促销折扣等，可在 lang_config.json 里扩展）

设计原则：
  1. 四大总计的提取不依赖具体语言关键词，而是利用报告固定的版式结构
     （"汇总(Résumés/Zusammenfassungen)" 小节下固定按 收入/支出/税费/转账 顺序各占一行）。
  2. 关键指标的提取基于坐标定位（同一行内，关键词右侧最近的数字），
     不依赖文本间距，避免因为数值是"0"导致的对齐误差。
  3. 语言关键词全部放在 lang_config.json，新增国家/语言时只需改配置，不用改代码。
"""

import json
import re
from pathlib import Path

import pdfplumber

NUM_RE = re.compile(r"^-?\d[\d.,]*$")


def _fix_minus(text: str) -> str:
    """有些语言（如瑞典语报表）用 Unicode 减号 '−'(U+2212) 而不是普通连字符 '-'，统一替换。"""
    if text is None:
        return text
    return text.replace("\u2212", "-").replace("–", "-")


def _to_float(num_str: str):
    """
    数字格式做到与语言无关：
    - 欧洲格式（法/德/瑞典等）：千分位用 '.'，小数用 ','，如 '-2.011,84'
    - 英美格式（美国站 USD）：千分位用 ',' ，小数用 '.'，如 '18,720.00'
    做法：金额始终是两位小数，找到"最后一个、且后面正好跟着 2 位数字"的分隔符
    作为小数点，它前面出现的所有 '.' 或 ',' 一律视为千分位分隔符去掉。
    """
    if num_str is None:
        return 0.0
    s = _fix_minus(num_str).strip()
    if s == "" or s == "-":
        return 0.0
    neg = s.startswith("-")
    s = s[1:] if neg else s

    m = re.match(r"^(.*[.,])(\d{2})$", s)
    if m:
        integer_part = re.sub(r"[.,]", "", m.group(1)[:-1])
        frac_part = m.group(2)
        try:
            val = float(f"{integer_part or '0'}.{frac_part}")
        except ValueError:
            val = 0.0
    else:
        cleaned = re.sub(r"[.,]", "", s)
        try:
            val = float(cleaned) if cleaned else 0.0
        except ValueError:
            val = 0.0
    return -val if neg else val


def load_lang_config(config_path: str = None) -> dict:
    if config_path is None:
        config_path = Path(__file__).parent / "lang_config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _parse_filename(filename: str):
    """
    期望格式: {店铺名}-{国家}-{年份+月份缩写}MonthlySummary.pdf
    例如: 跨界馨家-法国-2026AugMonthlySummary.pdf
    容错：解析失败时对应字段返回 None，不报错中断。
    """
    stem = Path(filename).stem  # 去掉 .pdf
    parts = stem.split("-")
    shop, country, period_tag = None, None, None
    if len(parts) >= 3:
        shop = parts[0]
        country = parts[1]
        period_tag = "-".join(parts[2:])
    elif len(parts) == 2:
        shop, country = parts
    else:
        shop = stem

    period_year, period_month = None, None
    if period_tag:
        m = re.search(r"(\d{4})([A-Za-z]{3})", period_tag)
        if m:
            period_year, period_month = m.group(1), m.group(2)

    return {
        "shop": shop,
        "country": country,
        "period_year": period_year,
        "period_month": period_month,
    }


def _extract_header_info(layout_text: str, cfg: dict):
    info = {"display_name": None, "legal_name": None, "period_start": None,
            "period_end": None, "currency": "EUR"}

    for label in cfg["display_name_labels"]:
        m = re.search(re.escape(label) + r"\s*:?\s*(.+)", layout_text)
        if m:
            info["display_name"] = m.group(1).strip()
            break

    for label in cfg["legal_name_labels"]:
        m = re.search(re.escape(label) + r"\s*:?\s*(.+)", layout_text)
        if m:
            info["legal_name"] = m.group(1).strip()
            break

    # 账期，如 "Aug 1, 2026 ... Aug 31, 2026"
    dates = re.findall(r"([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})", layout_text)
    if len(dates) >= 2:
        info["period_start"], info["period_end"] = dates[0], dates[1]

    cur_m = re.search(r"\b(EUR|USD|GBP|PLN|SEK|CHF|JPY|CAD|AUD|MXN)\b", layout_text)
    if cur_m:
        info["currency"] = cur_m.group(1)
    else:
        # 部分语言的报表不写标准三字母货币代码（如瑞典语写 "kr"），
        # 用 currency_symbol_map 做补充识别
        for symbol, code in cfg.get("currency_symbol_map", {}).items():
            if symbol == "_说明":
                continue
            if re.search(r"(?<![A-Za-z])" + re.escape(symbol) + r"(?![A-Za-z])", layout_text):
                info["currency"] = code
                break

    return info


def _extract_summary_totals(layout_text: str, cfg: dict):
    """
    定位 "Totaux / Gesamt / Total..." 所在行，其后紧跟的 4 个非空行
    依次是 收入 / 支出 / 税费 / 转账 的总计（报告固定顺序，与语言无关）。
    """
    lines = layout_text.split("\n")
    totals_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and any(stripped == marker or stripped.endswith(marker)
                             for marker in cfg["total_column_markers"]):
            totals_idx = i
            break

    result = {"revenue": None, "expenses": None, "tax": None, "transfers": None}
    if totals_idx is None:
        return result

    keys = ["revenue", "expenses", "tax", "transfers"]
    found = 0
    j = totals_idx + 1
    while j < len(lines) and found < 4:
        line = lines[j].strip()
        j += 1
        if not line:
            continue
        m = re.search(r"(-?[\d][\d.,]*)\s*$", line)
        if m:
            result[keys[found]] = _to_float(m.group(1))
            found += 1
    return result


def _cluster_rows(words, y_tol=3):
    """把 extract_words() 的结果按纵坐标聚类成行，行内按 x0 排序。"""
    rows = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        placed = False
        for row in rows:
            if abs(row["top"] - w["top"]) <= y_tol:
                row["words"].append(w)
                row["top"] = (row["top"] + w["top"]) / 2
                placed = True
                break
        if not placed:
            rows.append({"top": w["top"], "words": [w]})
    for row in rows:
        row["words"].sort(key=lambda w: w["x0"])
    return rows


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower().replace("«", '"').replace("»", '"')


def _extract_key_metrics(rows, cfg: dict):
    """
    对每一个配置好的关键指标，在所有行中寻找关键词命中所在行，
    取该行中关键词右侧最近的数字（可能有 1~2 个，因为 Débit/Crédit 两栏），求和。
    """
    metrics = {}
    key_metrics_cfg = {k: v for k, v in cfg["key_metrics"].items() if not k.startswith("_")}

    # "汇总(Résumés/Zusammenfassungen)" 小节里，每行是一整句话描述+总计数字，
    # 句子里常常顺带提到 "Servicegebühren/Verkaufsgebühren" 等字眼，
    # 但那不是该项目的真实金额，而是总计数字。这类行的第一个词就是分类大标题本身
    # （如 "Ausgaben ... -2.347,37"），据此把它们从明细扫描中剔除，避免误匹配。
    section_header_words = set()
    for kw_list in cfg["section_headers"].values():
        for kw in kw_list:
            section_header_words.add(_normalize(kw))

    for metric_name, keyword_list in key_metrics_cfg.items():
        norm_keywords = [_normalize(k) for k in keyword_list]
        value_sum = 0.0
        matched = False
        for row in rows:
            row_words = row["words"]
            if row_words and _normalize(row_words[0]["text"]) in section_header_words:
                continue
            row_norm_tokens = [_normalize(w["text"]) for w in row_words]
            row_joined = " ".join(row_norm_tokens)

            hit_kw = next((kw for kw in norm_keywords if kw in row_joined), None)
            if not hit_kw:
                continue

            # 用字符位置精确定位关键词覆盖的词数范围，而不是模糊窗口匹配
            char_idx = row_joined.find(hit_kw)
            prefix = row_joined[:char_idx].rstrip(" ")
            start_word_idx = 0 if prefix == "" else len(prefix.split(" "))
            kw_word_count = len(hit_kw.split(" "))
            scan_idx = start_word_idx + kw_word_count

            nums_found = 0
            steps = 0
            while scan_idx < len(row_words) and nums_found < 2 and steps < 20:
                token = row_words[scan_idx]["text"]
                if NUM_RE.match(token):
                    value_sum += _to_float(token)
                    nums_found += 1
                    scan_idx += 1
                elif nums_found > 0:
                    break
                else:
                    scan_idx += 1
                steps += 1
            if nums_found > 0:
                matched = True
        metrics[metric_name] = value_sum if matched else None
    return metrics


def parse_pdf(pdf_path: str, cfg: dict = None) -> dict:
    """解析单个 MonthlySummary PDF，返回结构化 dict。"""
    if cfg is None:
        cfg = load_lang_config()

    filename_info = _parse_filename(Path(pdf_path).name)

    with pdfplumber.open(pdf_path) as pdf:
        full_layout_text = _fix_minus("\n".join(
            (page.extract_text(layout=True) or "") for page in pdf.pages
        ))
        all_words = []
        for page in pdf.pages:
            for w in page.extract_words():
                w["text"] = _fix_minus(w["text"])
                all_words.append(w)
        rows = _cluster_rows(all_words)

    header_info = _extract_header_info(full_layout_text, cfg)
    totals = _extract_summary_totals(full_layout_text, cfg)
    key_metrics = _extract_key_metrics(rows, cfg)

    revenue = totals["revenue"] or 0.0
    expenses = totals["expenses"] or 0.0
    tax = totals["tax"] or 0.0
    transfers = totals["transfers"] or 0.0
    net_profit = revenue + expenses + tax  # expenses 本身是负数

    record = {
        "file": Path(pdf_path).name,
        "shop": filename_info["shop"],
        "country": filename_info["country"],
        "period_year": filename_info["period_year"],
        "period_month": filename_info["period_month"],
        "display_name": header_info["display_name"],
        "legal_name": header_info["legal_name"],
        "period_start": header_info["period_start"],
        "period_end": header_info["period_end"],
        "currency": header_info["currency"],
        "revenue": revenue,
        "expenses": expenses,
        "tax": tax,
        "transfers": transfers,
        "net_profit": net_profit,
        "net_margin": (net_profit / revenue) if revenue else None,
    }
    record.update({f"metric_{k}": v for k, v in key_metrics.items()})

    ad_spend = record.get("metric_advertising_cost") or 0.0
    record["ad_spend"] = ad_spend
    record["acos"] = (abs(ad_spend) / revenue) if revenue else None

    # 统一换算成欧元，方便跨国/跨店铺汇总（原始币种数值仍保留在上面各字段中）
    fx_map = cfg.get("exchange_rates_to_eur", {})
    fx_rate = fx_map.get(record["currency"], 1.0)
    record["fx_rate_to_eur"] = fx_rate
    record["revenue_eur"] = revenue * fx_rate
    record["expenses_eur"] = expenses * fx_rate
    record["net_profit_eur"] = net_profit * fx_rate
    record["ad_spend_eur"] = ad_spend * fx_rate

    return record


def parse_folder(folder: str, cfg: dict = None) -> list:
    """解析文件夹下所有 PDF，返回记录列表。"""
    cfg = cfg or load_lang_config()
    records = []
    for pdf_path in sorted(Path(folder).glob("*.pdf")):
        try:
            records.append(parse_pdf(str(pdf_path), cfg))
        except Exception as e:
            records.append({"file": pdf_path.name, "error": str(e)})
    return records
