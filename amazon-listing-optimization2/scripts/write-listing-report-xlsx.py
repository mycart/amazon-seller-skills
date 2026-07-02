#!/usr/bin/env python3
"""Write a complete Amazon listing optimization report to XLSX.

Input is a JSON file containing the final listing, July 2026 title options,
audit/diagnostic sections, keyword analysis, recommendations, and optional
competitive comparison data. The writer uses only Python standard library
modules so it can run in constrained skill environments.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape


SHEET_LIMIT = 31


def as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "\n".join(as_text(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def cell_ref(col_index: int, row_index: int) -> str:
    letters = ""
    col = col_index
    while col:
        col, rem = divmod(col - 1, 26)
        letters = chr(65 + rem) + letters
    return f"{letters}{row_index}"


def inline_cell(col_index: int, row_index: int, value: object, style: int = 0) -> str:
    ref = cell_ref(col_index, row_index)
    style_attr = f' s="{style}"' if style else ""
    text = escape(as_text(value))
    return f'<c r="{ref}" t="inlineStr"{style_attr}><is><t>{text}</t></is></c>'


def row_xml(row_index: int, values: list[object], style: int = 0) -> str:
    cells = "".join(inline_cell(i + 1, row_index, value, style) for i, value in enumerate(values))
    return f'<row r="{row_index}">{cells}</row>'


def safe_sheet_name(name: str, used: set[str]) -> str:
    cleaned = re.sub(r"[:\\/?*\[\]]", "", name).strip()[:SHEET_LIMIT] or "Sheet"
    candidate = cleaned
    counter = 2
    while candidate in used:
        suffix = f" {counter}"
        candidate = cleaned[: SHEET_LIMIT - len(suffix)] + suffix
        counter += 1
    used.add(candidate)
    return candidate


def normalize_rows(rows: list[list[object]]) -> list[list[object]]:
    return rows if rows else [["说明", "本次任务未提供该部分数据"]]


def key_value_rows(title: str, pairs: list[tuple[str, object]]) -> list[list[object]]:
    rows = [[title], ["字段", "内容"]]
    rows.extend([[key, value] for key, value in pairs if as_text(value)])
    return normalize_rows(rows)


def list_rows(title: str, items: list[object], header: str = "内容") -> list[list[object]]:
    rows = [[title], [header]]
    rows.extend([[item] for item in items if as_text(item)])
    return normalize_rows(rows)


def sheet_xml(rows: list[list[object]], widths: list[int] | None = None) -> str:
    rows = normalize_rows(rows)
    xml_rows: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        style = 2 if row_index == 1 else 1 if row_index == 2 else 0
        xml_rows.append(row_xml(row_index, row, style=style))
    max_cols = max(len(row) for row in rows)
    widths = widths or [24, 48, 24, 24, 24, 64]
    cols = []
    for index in range(max_cols):
        width = widths[index] if index < len(widths) else 28
        cols.append(f'<col min="{index + 1}" max="{index + 1}" width="{width}" customWidth="1"/>')
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><cols>{''.join(cols)}</cols><sheetData>{''.join(xml_rows)}</sheetData></worksheet>"""


def workbook_xml(sheet_names: list[str]) -> str:
    sheets = "".join(
        f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, name in enumerate(sheet_names, start=1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>{sheets}</sheets></workbook>"""


def workbook_rels_xml(sheet_count: int) -> str:
    rels = []
    for index in range(1, sheet_count + 1):
        rels.append(
            f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
        )
    rels.append(
        f'<Relationship Id="rId{sheet_count + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{''.join(rels)}</Relationships>"""


def root_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>"""


def content_types_xml(sheet_count: int) -> str:
    sheets = "".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>{sheets}<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>"""


def styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="3"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="14"/><name val="Calibri"/></font></fonts><fills count="4"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FFD9EAF7"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFEEF6D7"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf><xf numFmtId="0" fontId="2" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>"""


def rows_from_dicts(title: str, rows: list[dict], headers: list[tuple[str, str]]) -> list[list[object]]:
    output = [[title], [label for label, _key in headers]]
    for row in rows:
        output.append([row.get(key, "") for _label, key in headers])
    return normalize_rows(output)


def build_sheets(data: dict) -> list[tuple[str, list[list[object]], list[int]]]:
    listing = data.get("listing", {}) or {}
    audit = data.get("audit", {}) or {}
    diagnostic = data.get("diagnostic", {}) or {}
    metadata_pairs = [
        ("ASIN", data.get("asin", "")),
        ("模式", data.get("mode", "")),
        ("目标站点", data.get("marketplace", "")),
        ("产品", data.get("product", "")),
        ("品牌", data.get("brand", "")),
        ("生成时间", data.get("generated_at", "")),
        ("语气", diagnostic.get("tone", "")),
        ("导入关键词数", diagnostic.get("keywords_imported", "")),
        ("标题字符数", diagnostic.get("title_characters", "")),
        ("描述字符数", diagnostic.get("description_characters", "")),
        ("优化前评分", audit.get("score_before", "")),
        ("优化后评分", audit.get("score_after", "")),
    ]
    sheets: list[tuple[str, list[list[object]], list[int]]] = [
        ("总览", key_value_rows("Listing优化报告总览", metadata_pairs), [22, 60]),
    ]

    listing_rows = [["最终Listing"], ["模块", "内容"]]
    listing_rows.append(["标题", listing.get("title", "")])
    for index, bullet in enumerate(listing.get("bullets", []) or [], start=1):
        listing_rows.append([f"五点{index}", bullet])
    listing_rows.extend(
        [
            ["产品描述", listing.get("description", "")],
            ["后台搜索词", listing.get("backend_search_terms", "")],
        ]
    )
    title_options = data.get("title_options_2026", []) or data.get("options", []) or []
    if title_options:
        listing_rows.append([])
        listing_rows.append(["2026年7月标题 + 商品亮点方案", ""])
        for option in title_options:
            label = f"方案{option.get('option', '')}".strip()
            listing_rows.extend(
                [
                    [f"{label} 商品标题", option.get("title", "")],
                    [f"{label} 标题字符数", option.get("title_characters", "")],
                    [f"{label} 商品亮点", option.get("item_highlights", "")],
                    [f"{label} 亮点字符数", option.get("item_highlights_characters", "")],
                    [f"{label} 核心策略简析", option.get("core_strategy", "")],
                ]
            )
    sheets.append(("Listing", normalize_rows(listing_rows), [18, 100]))

    audit_rows = [["审核报告"], ["字段", "内容"]]
    for key, label in [
        ("price", "价格"),
        ("rating", "评分"),
        ("review_count", "评论数"),
        ("score_before", "优化前总分"),
        ("score_after", "优化后总分"),
    ]:
        if as_text(audit.get(key, "")):
            audit_rows.append([label, audit.get(key, "")])
    audit_rows.append([])
    audit_rows.append(["维度", "优化前", "优化后", "关键变化"])
    for row in audit.get("dimensions", []) or []:
        audit_rows.append([row.get("dimension", ""), row.get("before", ""), row.get("after", ""), row.get("key_change", "")])
    sheets.append(("审核报告", normalize_rows(audit_rows), [22, 22, 22, 80]))

    sheets.append(
        (
            "关键词覆盖",
            rows_from_dicts(
                "关键词覆盖率",
                data.get("keyword_coverage", []) or [],
                [
                    ("关键词", "keyword"),
                    ("搜索量", "volume"),
                    ("标题中", "in_title"),
                    ("五点中", "in_bullets"),
                    ("描述中", "in_description"),
                    ("状态", "status"),
                ],
            ),
            [34, 16, 16, 16, 16, 28],
        )
    )

    priority = data.get("keyword_priority", {}) or {}
    priority_rows = [["关键词优先级"], ["层级", "关键词"]]
    for label, key in [
        ("一级词（标题）", "primary"),
        ("二级词（五点）", "secondary"),
        ("三级词（描述）", "tertiary"),
        ("后台词", "backend"),
    ]:
        priority_rows.append([label, ", ".join(as_text(item) for item in priority.get(key, []) or [])])
    sheets.append(("关键词优先级", normalize_rows(priority_rows), [22, 100]))

    sheets.append(
        (
            "关键词缺口",
            rows_from_dicts(
                "关键词缺口分析",
                data.get("keyword_gaps", []) or [],
                [
                    ("关键词", "keyword"),
                    ("竞品1", "competitor_1"),
                    ("竞品2", "competitor_2"),
                    ("竞品3", "competitor_3"),
                    ("优先级", "priority"),
                ],
            ),
            [34, 24, 24, 24, 18],
        )
    )

    sheets.append(
        (
            "优化前后",
            rows_from_dicts(
                "优化前后对比",
                data.get("before_after", []) or [],
                [
                    ("模块", "section"),
                    ("优化前", "before"),
                    ("优化后", "after"),
                    ("新增关键词", "added_keywords"),
                ],
            ),
            [18, 60, 80, 38],
        )
    )

    advice_rows = [["建议与卖点"], ["类型", "内容"]]
    for item in data.get("issues_fixed", []) or []:
        advice_rows.append(["已修复问题", item])
    for item in data.get("recommendations", []) or []:
        advice_rows.append(["卖家行动建议", item])
    for item in data.get("working_well", []) or []:
        advice_rows.append(["保留优点", item])
    for item in data.get("selling_point_notes", []) or []:
        advice_rows.append(["核心卖点融入说明", item])
    for item in data.get("uploaded_keyword_file_summary", []) or []:
        advice_rows.append(["上传关键词文件摘要", item])
    sheets.append(("建议与卖点", normalize_rows(advice_rows), [24, 100]))

    sheets.append(
        (
            "竞品对比",
            rows_from_dicts(
                "竞品对比",
                data.get("competitive_comparison", []) or [],
                [
                    ("维度", "dimension"),
                    ("你的Listing", "your_listing"),
                    ("竞品1", "competitor_1"),
                    ("竞品2", "competitor_2"),
                    ("竞品3", "competitor_3"),
                ],
            ),
            [26, 24, 24, 24, 24],
        )
    )

    used: set[str] = set()
    return [(safe_sheet_name(name, used), rows, widths) for name, rows, widths in sheets]


def write_xlsx(data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheets = build_sheets(data)
    with ZipFile(output_path, "w", ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml(len(sheets)))
        zf.writestr("_rels/.rels", root_rels_xml())
        zf.writestr("xl/workbook.xml", workbook_xml([name for name, _rows, _widths in sheets]))
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml(len(sheets)))
        zf.writestr("xl/styles.xml", styles_xml())
        for index, (_name, rows, widths) in enumerate(sheets, start=1):
            zf.writestr(f"xl/worksheets/sheet{index}.xml", sheet_xml(rows, widths))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to listing-report JSON input")
    parser.add_argument("--output", required=True, help="Path to output .xlsx file")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    write_xlsx(data, output_path)
    print(output_path)


if __name__ == "__main__":
    main()
