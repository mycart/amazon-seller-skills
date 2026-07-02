#!/usr/bin/env python3
"""Extract keyword candidates from CSV and XLSX files into JSON.

The script is intentionally conservative: it finds likely keyword columns,
preserves adjacent metrics, and leaves final relevance judgment to the listing
workflow.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


KEYWORD_HEADERS = {
    "keyword",
    "keywords",
    "search term",
    "search terms",
    "search query",
    "query",
    "term",
    "phrase",
    "关键词",
    "搜索词",
    "关键字",
    "词根",
    "流量词",
    "长尾词",
}


def normalize_header(value: object) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text.strip().lower())


def normalize_keyword(value: object) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text.strip())


def likely_keyword_column(headers: list[str]) -> int | None:
    normalized = [normalize_header(header) for header in headers]
    for index, header in enumerate(normalized):
        if header in KEYWORD_HEADERS:
            return index
    for index, header in enumerate(normalized):
        if "keyword" in header or "search term" in header or "query" in header or "关键词" in header or "搜索词" in header:
            return index
    return None


def rows_to_records(rows: Iterable[list[object]], source_file: str, sheet_name: str = "") -> list[dict]:
    iterator = iter(rows)
    try:
        headers = [str(value).strip() for value in next(iterator)]
    except StopIteration:
        return []

    keyword_index = likely_keyword_column(headers)
    if keyword_index is None:
        return []

    records = []
    for row_number, row in enumerate(iterator, start=2):
        if keyword_index >= len(row):
            continue
        keyword = normalize_keyword(row[keyword_index])
        if not keyword:
            continue
        metrics = {}
        for index, header in enumerate(headers):
            if index == keyword_index or not header:
                continue
            metrics[header] = row[index] if index < len(row) else ""
        records.append(
            {
                "keyword": keyword,
                "source_file": source_file,
                "sheet": sheet_name,
                "row": row_number,
                "metrics": metrics,
            }
        )
    return records


def read_csv(path: Path) -> list[dict]:
    encodings = ["utf-8-sig", "utf-8", "gb18030", "latin-1"]
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                sample = handle.read(4096)
                handle.seek(0)
                dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
                rows = list(csv.reader(handle, dialect))
            return rows_to_records(rows, path.name)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Could not read CSV {path}: {last_error}")


def column_index(cell_ref: str) -> int:
    letters = re.sub(r"[^A-Z]", "", cell_ref.upper())
    result = 0
    for char in letters:
        result = result * 26 + ord(char) - 64
    return max(result - 1, 0)


def text_from_cell(cell: ET.Element, shared_strings: list[str], ns: dict[str, str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//main:t", ns))
    value = cell.find("main:v", ns)
    if value is None or value.text is None:
        return ""
    if cell_type == "s":
        try:
            return shared_strings[int(value.text)]
        except (ValueError, IndexError):
            return ""
    return value.text


def read_shared_strings(zf: zipfile.ZipFile, ns: dict[str, str]) -> list[str]:
    try:
        xml = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(xml)
    strings = []
    for item in root.findall("main:si", ns):
        strings.append("".join(node.text or "" for node in item.findall(".//main:t", ns)))
    return strings


def read_workbook_sheets(zf: zipfile.ZipFile, ns: dict[str, str]) -> list[tuple[str, str]]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_map = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels
        if rel.attrib.get("Id") and rel.attrib.get("Target")
    }
    sheets = []
    for sheet in workbook.findall(".//main:sheet", ns):
        name = sheet.attrib.get("name", "Sheet")
        rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        target = rel_map.get(rel_id or "")
        if not target:
            continue
        if not target.startswith("xl/"):
            target = f"xl/{target.lstrip('/')}"
        sheets.append((name, target))
    return sheets


def read_xlsx(path: Path) -> list[dict]:
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    records = []
    with zipfile.ZipFile(path) as zf:
        shared_strings = read_shared_strings(zf, ns)
        for sheet_name, sheet_path in read_workbook_sheets(zf, ns):
            root = ET.fromstring(zf.read(sheet_path))
            rows = []
            for row in root.findall(".//main:sheetData/main:row", ns):
                values: list[str] = []
                for cell in row.findall("main:c", ns):
                    index = column_index(cell.attrib.get("r", "A1"))
                    while len(values) <= index:
                        values.append("")
                    values[index] = text_from_cell(cell, shared_strings, ns)
                rows.append(values)
            records.extend(rows_to_records(rows, path.name, sheet_name))
    return records


def dedupe(records: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for record in records:
        key = record["keyword"].casefold()
        if key not in merged:
            merged[key] = record
            merged[key]["sources"] = [record["source_file"]]
            continue
        existing = merged[key]
        if record["source_file"] not in existing["sources"]:
            existing["sources"].append(record["source_file"])
        existing["metrics"].update({k: v for k, v in record.get("metrics", {}).items() if v not in ("", None)})
    return list(merged.values())


def extract(paths: list[Path]) -> dict:
    all_records = []
    errors = []
    for path in paths:
        try:
            suffix = path.suffix.lower()
            if suffix == ".csv":
                all_records.extend(read_csv(path))
            elif suffix == ".xlsx":
                all_records.extend(read_xlsx(path))
            else:
                errors.append({"file": str(path), "error": "unsupported file type"})
        except Exception as exc:
            errors.append({"file": str(path), "error": str(exc)})
    records = dedupe(all_records)
    return {
        "source_files": [str(path) for path in paths],
        "candidate_count": len(all_records),
        "deduped_count": len(records),
        "keywords": records,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", help="CSV/XLSX keyword files")
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args()

    result = extract([Path(file) for file in args.files])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)
    if result["errors"]:
        print(json.dumps(result["errors"], ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
