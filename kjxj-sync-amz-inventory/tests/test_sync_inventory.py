import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


SCRIPT = Path(__file__).parents[1] / "scripts" / "sync_inventory.py"
SPEC = importlib.util.spec_from_file_location("sync_inventory", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


MAIN_NS = MODULE.MAIN_NS
REL_NS = MODULE.REL_NS
PKG_REL_NS = MODULE.PKG_REL_NS


def xml_cell(reference, value=None, cell_type=None, formula=None, style=None):
    attributes = {"r": reference}
    if cell_type:
        attributes["t"] = cell_type
    if style is not None:
        attributes["s"] = str(style)
    cell = ET.Element(f"{{{MAIN_NS}}}c", attributes)
    if formula is not None:
        formula_node = ET.SubElement(cell, f"{{{MAIN_NS}}}f")
        formula_node.text = formula
    if cell_type == "inlineStr":
        inline = ET.SubElement(cell, f"{{{MAIN_NS}}}is")
        text = ET.SubElement(inline, f"{{{MAIN_NS}}}t")
        text.text = str(value)
    elif value is not None:
        value_node = ET.SubElement(cell, f"{{{MAIN_NS}}}v")
        value_node.text = str(value)
    return cell


def sheet_xml(rows):
    worksheet = ET.Element(f"{{{MAIN_NS}}}worksheet")
    sheet_data = ET.SubElement(worksheet, f"{{{MAIN_NS}}}sheetData")
    for row_number, cells in rows:
        row = ET.SubElement(sheet_data, f"{{{MAIN_NS}}}row", {"r": str(row_number)})
        for cell in cells:
            row.append(cell)
    return ET.tostring(worksheet, encoding="utf-8", xml_declaration=True)


def create_workbook(path, sheets, shared_strings=None, extra_parts=None):
    workbook = ET.Element(f"{{{MAIN_NS}}}workbook")
    sheets_node = ET.SubElement(workbook, f"{{{MAIN_NS}}}sheets")
    relationships = ET.Element(f"{{{PKG_REL_NS}}}Relationships")
    for index, (name, _content) in enumerate(sheets, start=1):
        ET.SubElement(
            sheets_node,
            f"{{{MAIN_NS}}}sheet",
            {"name": name, "sheetId": str(index), f"{{{REL_NS}}}id": f"rId{index}"},
        )
        ET.SubElement(
            relationships,
            f"{{{PKG_REL_NS}}}Relationship",
            {
                "Id": f"rId{index}",
                "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet",
                "Target": f"worksheets/sheet{index}.xml",
            },
        )
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("xl/workbook.xml", ET.tostring(workbook, encoding="utf-8", xml_declaration=True))
        archive.writestr("xl/_rels/workbook.xml.rels", ET.tostring(relationships, encoding="utf-8", xml_declaration=True))
        for index, (_name, content) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", content)
        if shared_strings is not None:
            root = ET.Element(f"{{{MAIN_NS}}}sst", {"count": str(len(shared_strings)), "uniqueCount": str(len(shared_strings))})
            for value in shared_strings:
                item = ET.SubElement(root, f"{{{MAIN_NS}}}si")
                text = ET.SubElement(item, f"{{{MAIN_NS}}}t")
                text.text = value
            archive.writestr("xl/sharedStrings.xml", ET.tostring(root, encoding="utf-8", xml_declaration=True))
        for name, content in (extra_parts or {}).items():
            archive.writestr(name, content)


def source_sheet(records, modes=None):
    modes = modes or {}
    rows = [
        (1, [xml_cell("A1", "分类", "inlineStr")]),
        (2, [xml_cell("A2", "Item Code", "inlineStr"), xml_cell("U2", "可售库存", "inlineStr")]),
    ]
    shared = []
    for row, (item_code, quantity) in enumerate(records, start=3):
        mode = modes.get(row, "inline")
        item_cell = xml_cell(f"A{row}", item_code, "inlineStr")
        if mode == "shared":
            shared.append(str(quantity))
            quantity_cell = xml_cell(f"U{row}", len(shared) - 1, "s")
        elif mode == "formula":
            quantity_cell = xml_cell(f"U{row}", quantity, formula="1+1")
        else:
            quantity_cell = xml_cell(f"U{row}", quantity, "inlineStr" if mode == "inline" else None)
        rows.append((row, [item_cell, quantity_cell]))
    return sheet_xml(rows), shared or None


def target_sheet(skus, quantities=None):
    quantities = quantities or {}
    rows = [
        (4, [xml_cell("A4", "SKU", "inlineStr"), xml_cell("C4", "Quantity (DE)", "inlineStr", style=3)]),
        (5, [xml_cell("A5", "contribution_sku#1.value", "inlineStr"), xml_cell("C5", "fulfillment_availability#1.quantity", "inlineStr", style=3)]),
        (6, [xml_cell("A6", "ABC123", "inlineStr"), xml_cell("C6", 152, style=3)]),
    ]
    for row, sku in enumerate(skus, start=7):
        cells = [xml_cell(f"A{row}", sku, "inlineStr")]
        if row in quantities:
            cells.append(xml_cell(f"C{row}", quantities[row], style=3))
        rows.append((row, cells))
    return sheet_xml(rows)


class InventorySyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def paths(self, target_suffix=".xlsx"):
        return self.root / "产品信息.xlsx", self.root / f"target{target_suffix}"

    def write_pair(self, records, skus, target_name="Template", modes=None, target_suffix=".xlsx", quantities=None, extra_parts=None):
        source, target = self.paths(target_suffix)
        source_xml, shared = source_sheet(records, modes)
        create_workbook(source, [("产品信息", source_xml)], shared_strings=shared)
        create_workbook(target, [(target_name, target_sheet(skus, quantities))], extra_parts=extra_parts)
        return source, target

    def test_unique_match_and_thresholds(self):
        source, target = self.write_pair(
            [("A0", 0), ("A2", 2), ("A5", 5), ("A6", 6)],
            ["SKU-A0", "SKU-A2", "SKU-A5", "SKU-A6"],
        )
        report = MODULE.analyze(source, target, None)
        self.assertEqual([item["written_quantity"] for item in report["updates"]], [0, 0, 0, 6])
        self.assertEqual(report["zeroed_count"], 3)

    def test_unmatched_ambiguous_and_invalid_keep_original(self):
        source, target = self.write_pair(
            [("ABC", 9), ("BC", 10), ("BAD", "N/A")],
            ["SKU-ABC", "SKU-NONE", "SKU-BAD"],
            quantities={7: 91, 8: 92, 9: 93},
        )
        report = MODULE.analyze(source, target, None)
        self.assertEqual(report["updated_count"], 0)
        self.assertEqual(report["ambiguous_count"], 1)
        self.assertEqual(report["unmatched_count"], 1)
        self.assertEqual(report["invalid_inventory_count"], 1)

    def test_shared_inline_numeric_and_formula_cached_values(self):
        source, target = self.write_pair(
            [("INLINE", 8), ("SHARED", 9), ("NUMBER", 10), ("FORMULA", 11)],
            ["X-INLINE", "X-SHARED", "X-NUMBER", "X-FORMULA"],
            modes={3: "inline", 4: "shared", 5: "number", 6: "formula"},
        )
        report = MODULE.analyze(source, target, None)
        self.assertEqual([item["written_quantity"] for item in report["updates"]], [8, 9, 10, 11])

    def test_template_semantic_name_explicit_sheet_and_ambiguity(self):
        source, target = self.write_pair([("SKU1", 7)], ["X-SKU1"], target_name="Vorlage")
        self.assertEqual(MODULE.analyze(source, target, None)["target_sheet"], "Vorlage")
        self.assertEqual(MODULE.analyze(source, target, "Vorlage")["target_sheet"], "Vorlage")

        ambiguous = self.root / "ambiguous.xlsx"
        create_workbook(ambiguous, [("Vorlage", target_sheet(["X-SKU1"])), ("模板", target_sheet(["X-SKU1"]))])
        with self.assertRaises(MODULE.SyncError):
            MODULE.analyze(source, ambiguous, None)

    def test_apply_preserves_parts_styles_and_versions_output(self):
        macro = b"fake-vba-content"
        source, target = self.write_pair(
            [("SKU1", 12)],
            ["X-SKU1"],
            target_suffix=".xlsm",
            extra_parts={"xl/vbaProject.bin": macro, "custom/keep.bin": b"keep"},
        )
        report = MODULE.analyze(source, target, None)
        first = MODULE.versioned_output(target)
        MODULE.apply_updates(target, first, report)
        verification = MODULE.verify_output(target, first, report)
        self.assertTrue(verification["verified"])
        self.assertEqual(verification["changed_parts"], ["xl/worksheets/sheet1.xml"])
        with ZipFile(first) as archive:
            self.assertEqual(archive.read("xl/vbaProject.bin"), macro)
            root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
            cell = root.find(".//m:c[@r='C7']", MODULE.NS)
            self.assertEqual(cell.attrib.get("s"), "3")
        second = MODULE.versioned_output(target)
        self.assertTrue(second.name.endswith("_v2.xlsm"))
        self.assertFalse(target.read_bytes() == first.read_bytes())

    def test_apply_with_no_updates_creates_identical_copy(self):
        source, target = self.write_pair([("SKU1", 12)], ["NO-MATCH"])
        report = MODULE.analyze(source, target, None)
        output = self.root / "no-op.xlsx"
        MODULE.apply_updates(target, output, report)
        verification = MODULE.verify_output(target, output, report)
        self.assertEqual(verification["changed_parts"], [])
        self.assertEqual(target.read_bytes(), output.read_bytes())

    def test_aa_column_does_not_create_target_sku_row(self):
        source, target = self.write_pair([("SKU1", 8)], ["X-SKU1"])
        with ZipFile(target, "a", ZIP_DEFLATED) as archive:
            root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
            sheet_data = root.find(f"{{{MAIN_NS}}}sheetData")
            row = ET.SubElement(sheet_data, f"{{{MAIN_NS}}}row", {"r": "100"})
            row.append(xml_cell("AA100", "not-a-sku", "inlineStr"))
            archive.writestr("xl/worksheets/sheet1.xml", ET.tostring(root, encoding="utf-8", xml_declaration=True))
        report = MODULE.analyze(source, target, None)
        self.assertEqual(report["target_sku_count"], 1)


if __name__ == "__main__":
    unittest.main()
