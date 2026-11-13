#!/usr/bin/env python3
"""Synchronize saleable inventory into an Amazon OOXML template."""

from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"m": MAIN_NS, "r": REL_NS, "p": PKG_REL_NS}
ET.register_namespace("", MAIN_NS)
ET.register_namespace("r", REL_NS)

SUPPORTED_EXTENSIONS = {".xlsx", ".xlsm"}
SEMANTIC_TEMPLATE_NAMES = {
    "template",
    "vorlage",
    "modèle",
    "modele",
    "plantilla",
    "modello",
    "modelo",
    "sjabloon",
    "mall",
    "szablon",
    "šablona",
    "sablon",
    "模板",
    "範本",
    "テンプレート",
}
CELL_RE = re.compile(r"^([A-Z]+)([0-9]+)$")


class SyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class SheetInfo:
    name: str
    path: str


@dataclass(frozen=True)
class SourceRecord:
    item_code: str
    raw_quantity: object
    row: int


def qname(namespace: str, local: str) -> str:
    return f"{{{namespace}}}{local}"


def normalize_sheet_target(target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join("xl", target))


def validate_path(path: Path, role: str) -> None:
    if not path.is_file():
        raise SyncError(f"{role}文件不存在：{path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise SyncError(f"{role}文件格式不支持：{path.suffix}；仅支持 .xlsx 和 .xlsm")
    try:
        with ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise SyncError(f"{role}文件压缩包损坏：{path}")
    except BadZipFile as exc:
        raise SyncError(f"{role}文件不是有效 OOXML 工作簿：{path}") from exc


class WorkbookReader:
    def __init__(self, path: Path):
        self.path = path
        self.archive = ZipFile(path)
        self.shared_strings = self._load_shared_strings()
        self.sheets = self._load_sheets()

    def close(self) -> None:
        self.archive.close()

    def __enter__(self) -> "WorkbookReader":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _load_shared_strings(self) -> list[str]:
        try:
            root = ET.fromstring(self.archive.read("xl/sharedStrings.xml"))
        except KeyError:
            return []
        return ["".join(node.text or "" for node in item.findall(".//m:t", NS)) for item in root.findall("m:si", NS)]

    def _load_sheets(self) -> list[SheetInfo]:
        workbook = ET.fromstring(self.archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(self.archive.read("xl/_rels/workbook.xml.rels"))
        targets = {
            item.attrib["Id"]: item.attrib["Target"]
            for item in relationships.findall("p:Relationship", NS)
        }
        sheets = []
        for sheet in workbook.findall("m:sheets/m:sheet", NS):
            relationship_id = sheet.attrib[qname(REL_NS, "id")]
            sheets.append(SheetInfo(sheet.attrib["name"], normalize_sheet_target(targets[relationship_id])))
        return sheets

    def sheet(self, name: str) -> SheetInfo:
        for sheet in self.sheets:
            if sheet.name == name:
                return sheet
        raise SyncError(f"工作表不存在：{name}")

    def sheet_root(self, sheet: SheetInfo) -> ET.Element:
        return ET.fromstring(self.archive.read(sheet.path))

    def cell_value(self, cell: ET.Element) -> object:
        cell_type = cell.attrib.get("t")
        if cell_type == "inlineStr":
            return "".join(node.text or "" for node in cell.findall(".//m:t", NS))
        value = cell.find("m:v", NS)
        if value is None:
            return None
        raw = value.text or ""
        if cell_type == "s":
            try:
                return self.shared_strings[int(raw)]
            except (ValueError, IndexError) as exc:
                raise SyncError(f"共享字符串索引无效：{raw}") from exc
        if cell_type == "b":
            return raw == "1"
        if cell_type in {"str", "e"}:
            return raw
        return parse_number_or_text(raw)

    def cells(self, sheet: SheetInfo) -> dict[str, object]:
        root = self.sheet_root(sheet)
        return {cell.attrib["r"]: self.cell_value(cell) for cell in root.findall(".//m:sheetData/m:row/m:c", NS)}


def parse_number_or_text(raw: str) -> object:
    try:
        number = Decimal(raw)
    except InvalidOperation:
        return raw
    if number == number.to_integral_value():
        return int(number)
    return float(number)


def text(value: object) -> str:
    return "" if value is None else str(value).strip()


def column_number(reference: str) -> int:
    match = CELL_RE.match(reference)
    if not match:
        raise SyncError(f"无效单元格引用：{reference}")
    result = 0
    for char in match.group(1):
        result = result * 26 + ord(char) - 64
    return result


def row_number(reference: str) -> int:
    match = CELL_RE.match(reference)
    if not match:
        raise SyncError(f"无效单元格引用：{reference}")
    return int(match.group(2))


def column_letters(reference: str) -> str:
    match = CELL_RE.match(reference)
    if not match:
        raise SyncError(f"无效单元格引用：{reference}")
    return match.group(1)


def find_source(reader: WorkbookReader) -> tuple[SheetInfo, int, list[SourceRecord]]:
    candidates = []
    for sheet in reader.sheets:
        cells = reader.cells(sheet)
        by_row: dict[int, dict[str, object]] = {}
        for reference, value in cells.items():
            row = row_number(reference)
            if row <= 100:
                by_row.setdefault(row, {})[reference] = value
        for row, row_cells in sorted(by_row.items()):
            positions = {text(value): reference for reference, value in row_cells.items()}
            if "Item Code" in positions and "可售库存" in positions:
                candidates.append((sheet, row, positions["Item Code"], positions["可售库存"], cells))
    if not candidates:
        raise SyncError("源工作簿中找不到同一表头行的精确字段 Item Code 和 可售库存")
    if len(candidates) > 1:
        names = [f"{item[0].name}!{item[1]}" for item in candidates]
        raise SyncError(f"源字段位置不唯一：{names}")
    sheet, header_row, item_ref, quantity_ref, cells = candidates[0]
    item_column = CELL_RE.match(item_ref).group(1)  # type: ignore[union-attr]
    quantity_column = CELL_RE.match(quantity_ref).group(1)  # type: ignore[union-attr]
    records = []
    data_rows = sorted({row_number(reference) for reference in cells if row_number(reference) > header_row})
    for row in data_rows:
        item_code = text(cells.get(f"{item_column}{row}"))
        if item_code:
            records.append(SourceRecord(item_code, cells.get(f"{quantity_column}{row}"), row))
    return sheet, header_row, records


def target_structure(reader: WorkbookReader, sheet: SheetInfo) -> tuple[bool, str]:
    cells = reader.cells(sheet)
    sku_headers = [text(cells.get(f"A{row}")) for row in range(1, 7)]
    quantity_headers = [text(cells.get(f"C{row}")) for row in range(1, 7)]
    has_sku = any(value.upper() == "SKU" or "SKU" in value.upper() for value in sku_headers)
    has_quantity = any(value.lower().startswith("quantity") or "quantity" in value.lower() for value in quantity_headers)
    if not has_sku or not has_quantity:
        return False, "前 6 行未同时识别到 A 列 SKU 与 C 列 Quantity 表头"
    return True, ""


def select_target_sheet(reader: WorkbookReader, explicit: str | None) -> SheetInfo:
    if explicit:
        sheet = reader.sheet(explicit)
        valid, reason = target_structure(reader, sheet)
        if not valid:
            raise SyncError(f"指定工作表结构无效：{explicit}；{reason}")
        return sheet
    exact = [sheet for sheet in reader.sheets if sheet.name == "Template"]
    if exact:
        valid = [sheet for sheet in exact if target_structure(reader, sheet)[0]]
        if len(valid) == 1:
            return valid[0]
        reason = target_structure(reader, exact[0])[1]
        raise SyncError(f"Template 工作表结构无效：{reason}")
    semantic = [sheet for sheet in reader.sheets if sheet.name.strip().casefold() in SEMANTIC_TEMPLATE_NAMES and target_structure(reader, sheet)[0]]
    if len(semantic) == 1:
        return semantic[0]
    if len(semantic) > 1:
        raise SyncError(f"语义为 Template 的目标工作表不唯一：{[sheet.name for sheet in semantic]}")
    raise SyncError("找不到名称为 Template 或名称语义为模板且结构有效的目标工作表")


def normalized_quantity(value: object) -> int | float | None:
    if value is None or isinstance(value, bool):
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        number = Decimal(raw)
    except InvalidOperation:
        return None
    if not number.is_finite():
        return None
    if number <= 5:
        return 0
    if number == number.to_integral_value():
        return int(number)
    return float(number)


def analyze(source: Path, target: Path, explicit_sheet: str | None) -> dict[str, object]:
    validate_path(source, "源")
    validate_path(target, "目标")
    if source.resolve() == target.resolve():
        raise SyncError("源文件和目标文件不能是同一个文件")
    with WorkbookReader(source) as source_reader, WorkbookReader(target) as target_reader:
        source_sheet, header_row, records = find_source(source_reader)
        target_sheet = select_target_sheet(target_reader, explicit_sheet)
        target_cells = target_reader.cells(target_sheet)
        target_rows = sorted({
            row_number(reference)
            for reference in target_cells
            if column_letters(reference) == "A" and row_number(reference) >= 7
        })
        updates = []
        unmatched = []
        ambiguous = []
        invalid_inventory = []
        for row in target_rows:
            sku = text(target_cells.get(f"A{row}"))
            if not sku:
                continue
            matches = [record for record in records if record.item_code in sku]
            if not matches:
                unmatched.append({"target_row": row, "sku": sku})
                continue
            if len(matches) > 1:
                ambiguous.append({
                    "target_row": row,
                    "sku": sku,
                    "matches": [{"item_code": item.item_code, "source_row": item.row} for item in matches],
                })
                continue
            record = matches[0]
            quantity = normalized_quantity(record.raw_quantity)
            if quantity is None:
                invalid_inventory.append({
                    "target_row": row,
                    "sku": sku,
                    "item_code": record.item_code,
                    "source_row": record.row,
                    "raw_quantity": record.raw_quantity,
                })
                continue
            updates.append({
                "target_row": row,
                "sku": sku,
                "item_code": record.item_code,
                "source_row": record.row,
                "source_quantity": record.raw_quantity,
                "current_quantity": target_cells.get(f"C{row}"),
                "written_quantity": quantity,
            })
        return {
            "source_file": str(source.resolve()),
            "target_file": str(target.resolve()),
            "source_sheet": source_sheet.name,
            "source_header_row": header_row,
            "source_record_count": len(records),
            "target_sheet": target_sheet.name,
            "target_sheet_path": target_sheet.path,
            "target_sku_count": len(target_rows),
            "updated_count": len(updates),
            "zeroed_count": sum(item["written_quantity"] == 0 for item in updates),
            "unmatched_count": len(unmatched),
            "ambiguous_count": len(ambiguous),
            "invalid_inventory_count": len(invalid_inventory),
            "updates": updates,
            "unmatched": unmatched,
            "ambiguous": ambiguous,
            "invalid_inventory": invalid_inventory,
        }


def versioned_output(target: Path) -> Path:
    base = target.with_name(f"{target.stem}_库存已更新{target.suffix}")
    if not base.exists():
        return base
    version = 2
    while True:
        candidate = target.with_name(f"{target.stem}_库存已更新_v{version}{target.suffix}")
        if not candidate.exists():
            return candidate
        version += 1


def choose_output(target: Path, requested: str | None) -> Path:
    output = Path(requested).expanduser().resolve() if requested else versioned_output(target).resolve()
    if output.suffix.lower() != target.suffix.lower():
        raise SyncError("输出文件扩展名必须与目标文件一致")
    if output == target.resolve():
        raise SyncError("输出文件不能覆盖目标文件")
    if output.exists():
        raise SyncError(f"输出文件已存在，禁止覆盖：{output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def find_cell(root: ET.Element, reference: str) -> ET.Element | None:
    return root.find(f".//m:sheetData/m:row/m:c[@r='{reference}']", NS)


def column_style(root: ET.Element, column: str, target_row: int) -> str | None:
    candidates = []
    for cell in root.findall(".//m:sheetData/m:row/m:c", NS):
        reference = cell.attrib.get("r", "")
        if reference.startswith(column) and "s" in cell.attrib:
            candidates.append((abs(row_number(reference) - target_row), cell.attrib["s"]))
    return min(candidates)[1] if candidates else None


def get_or_create_row(sheet_data: ET.Element, target_row: int) -> ET.Element:
    for row in sheet_data.findall("m:row", NS):
        current = int(row.attrib["r"])
        if current == target_row:
            return row
        if current > target_row:
            new_row = ET.Element(qname(MAIN_NS, "row"), {"r": str(target_row)})
            sheet_data.insert(list(sheet_data).index(row), new_row)
            return new_row
    new_row = ET.Element(qname(MAIN_NS, "row"), {"r": str(target_row)})
    sheet_data.append(new_row)
    return new_row


def get_or_create_cell(root: ET.Element, row: ET.Element, reference: str) -> ET.Element:
    target_column = column_number(reference)
    for index, cell in enumerate(row.findall("m:c", NS)):
        current_reference = cell.attrib["r"]
        if current_reference == reference:
            return cell
        if column_number(current_reference) > target_column:
            new_cell = ET.Element(qname(MAIN_NS, "c"), {"r": reference})
            style = column_style(root, CELL_RE.match(reference).group(1), row_number(reference))  # type: ignore[union-attr]
            if style is not None:
                new_cell.attrib["s"] = style
            row.insert(index, new_cell)
            return new_cell
    new_cell = ET.Element(qname(MAIN_NS, "c"), {"r": reference})
    style = column_style(root, CELL_RE.match(reference).group(1), row_number(reference))  # type: ignore[union-attr]
    if style is not None:
        new_cell.attrib["s"] = style
    row.append(new_cell)
    return new_cell


def set_numeric_cell(root: ET.Element, reference: str, quantity: int | float) -> None:
    sheet_data = root.find("m:sheetData", NS)
    if sheet_data is None:
        raise SyncError("目标工作表缺少 sheetData")
    row = get_or_create_row(sheet_data, row_number(reference))
    cell = get_or_create_cell(root, row, reference)
    cell.attrib.pop("t", None)
    for child in list(cell):
        if child.tag in {qname(MAIN_NS, "v"), qname(MAIN_NS, "is"), qname(MAIN_NS, "f")}:
            cell.remove(child)
    value = ET.SubElement(cell, qname(MAIN_NS, "v"))
    value.text = str(quantity)


def serialize_xml(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def apply_updates(target: Path, output: Path, report: dict[str, object]) -> None:
    sheet_path = str(report["target_sheet_path"])
    with ZipFile(target) as input_archive:
        updates = report["updates"]  # type: ignore[assignment]
        updated_sheet = None
        if updates:
            root = ET.fromstring(input_archive.read(sheet_path))
            for update in updates:
                set_numeric_cell(root, f"C{update['target_row']}", update["written_quantity"])
            updated_sheet = serialize_xml(root)
        temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
        try:
            with ZipFile(temporary, "w", ZIP_DEFLATED) as output_archive:
                for info in input_archive.infolist():
                    content = updated_sheet if updated_sheet is not None and info.filename == sheet_path else input_archive.read(info.filename)
                    output_archive.writestr(info, content)
            os.replace(temporary, output)
        finally:
            if temporary.exists():
                temporary.unlink()


def verify_output(target: Path, output: Path, report: dict[str, object]) -> dict[str, object]:
    with ZipFile(target) as original, ZipFile(output) as result:
        if original.namelist() != result.namelist():
            raise SyncError("输出 OOXML 部件列表与目标文件不一致")
        changed_parts = [name for name in original.namelist() if original.read(name) != result.read(name)]
        expected = [str(report["target_sheet_path"])] if report["updates"] else []
        if changed_parts != expected:
            raise SyncError(f"检测到非预期 OOXML 部件变化：{changed_parts}")
    with WorkbookReader(output) as reader:
        sheet = reader.sheet(str(report["target_sheet"]))
        cells = reader.cells(sheet)
        for update in report["updates"]:  # type: ignore[union-attr]
            actual = cells.get(f"C{update['target_row']}")
            if actual != update["written_quantity"]:
                raise SyncError(f"输出验证失败：C{update['target_row']}={actual}")
    return {"changed_parts": changed_parts, "verified": True}


def execute(args: argparse.Namespace) -> dict[str, object]:
    source = Path(args.source).expanduser().resolve()
    target = Path(args.target).expanduser().resolve()
    report = analyze(source, target, args.sheet)
    report["command"] = args.command
    if args.command == "apply":
        output = choose_output(target, args.output)
        apply_updates(target, output, report)
        report["output_file"] = str(output)
        report["verification"] = verify_output(target, output, report)
        report["summary_cn"] = (
            f"已生成库存更新副本：{output}；更新 {report['updated_count']} 行，"
            f"其中归零 {report['zeroed_count']} 行；未匹配 {report['unmatched_count']} 行，"
            f"多重匹配 {report['ambiguous_count']} 行，无效库存 {report['invalid_inventory_count']} 行。"
        )
    else:
        report["summary_cn"] = (
            f"预检完成：目标 SKU {report['target_sku_count']} 行，预计更新 {report['updated_count']} 行，"
            f"其中归零 {report['zeroed_count']} 行；未匹配 {report['unmatched_count']} 行，"
            f"多重匹配 {report['ambiguous_count']} 行，无效库存 {report['invalid_inventory_count']} 行。"
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="将产品信息可售库存同步到 Amazon 模板")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "apply"):
        subparser = subparsers.add_parser(command, help="只读预检" if command == "plan" else "生成更新副本")
        subparser.add_argument("--source", required=True, help="产品信息源文件")
        subparser.add_argument("--target", required=True, help="Amazon 目标模板")
        subparser.add_argument("--sheet", help="明确指定目标工作表")
        if command == "apply":
            subparser.add_argument("--output", help="输出副本路径；默认保存到目标文件同目录")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        report = execute(args)
    except (SyncError, OSError, ET.ParseError, BadZipFile) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    report["status"] = "ok"
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
