#!/usr/bin/env node
/* Confirmed-operation XLSX writer. Invoke from a temp directory with artifact-tool available. */
import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

// Resolve from the temporary execution directory, where the skill requires a node_modules symlink.
const require = createRequire(path.join(process.cwd(), "package.json"));
const { FileBlob, SpreadsheetFile, Workbook } = require("@oai/artifact-tool");

const MAX_BYTES = 10 * 1024 * 1024;
const LOG_HEADERS = ["操作时间", "操作用户标识", "操作内容摘要", "同步类型", "最终动作", "源路径/来源", "目标路径", "结果", "备注"];

function argsOf(argv) {
  const args = {};
  for (let index = 2; index < argv.length; index += 2) args[argv[index].replace(/^--/, "")] = argv[index + 1];
  return args;
}

function normalize(value) { return String(value ?? "").trim().toLocaleLowerCase(); }
function columnName(index) {
  let result = "";
  for (let value = index + 1; value; value = Math.floor((value - 1) / 26)) result = String.fromCharCode(65 + ((value - 1) % 26)) + result;
  return result;
}

async function loadWorkbook(input) {
  if (!input) return Workbook.create();
  return SpreadsheetFile.importXlsx(await FileBlob.load(input));
}

function readRows(sheet) {
  try {
    const used = sheet.getUsedRange(true);
    return used ? used.values : [];
  } catch { return []; }
}

function ensureHeaders(sheet, headers) {
  const rows = readRows(sheet);
  const existing = (rows[0] || []).map((value) => String(value ?? "").trim());
  const normalized = new Set(existing.map(normalize));
  const missing = headers.filter((header) => !normalized.has(normalize(header)));
  const allHeaders = [...existing, ...missing];
  if (!existing.length) sheet.getRange(`A1:${columnName(allHeaders.length - 1)}1`).values = [allHeaders];
  else if (missing.length) {
    const firstMissing = existing.length;
    sheet.getRange(`${columnName(firstMissing)}1:${columnName(allHeaders.length - 1)}1`).values = [missing];
  }
  sheet.freezePanes.freezeRows(1);
  if (!existing.length || missing.length) sheet.getRange(`A1:${columnName(allHeaders.length - 1)}1`).format = {
    fill: "#1F4E78", font: { bold: true, color: "#FFFFFF" }, wrapText: true,
  };
  return allHeaders;
}

function appendOrUpdate(sheet, headers, record, operation, matchKeys) {
  const rows = readRows(sheet);
  const headerIndex = new Map(headers.map((header, index) => [normalize(header), index]));
  const physicalHeaderIndex = new Map((rows[0] || []).map((header, index) => [normalize(header), index]));
  const dataStart = Math.min(...headers.map((header) => physicalHeaderIndex.get(normalize(header))).filter((index) => index !== undefined));
  const dataOffset = Math.max(0, ...rows.slice(1).map((row) => row.length - headers.length));
  const matchingRows = [];
  const usableKeys = matchKeys.filter((key) => headerIndex.has(normalize(key)) && record[key] !== undefined && record[key] !== "");
  if (usableKeys.length) {
    rows.slice(1).forEach((row, rowIndex) => {
      if (usableKeys.every((key) => normalize(row[physicalHeaderIndex.get(normalize(key)) + dataOffset]) === normalize(record[key]))) matchingRows.push(rowIndex + 2);
    });
  }
  if (operation === "skip") return { action: "skipped", matched_rows: matchingRows };
  if (operation === "update") {
    if (matchingRows.length !== 1) throw new Error("update_requires_exactly_one_matching_row");
    const rowNumber = matchingRows[0];
    for (const [key, value] of Object.entries(record)) {
      const index = physicalHeaderIndex.get(normalize(key)) + dataOffset;
      if (index !== undefined && value !== undefined) sheet.getRange(`${columnName(index)}${rowNumber}`).values = [[value]];
    }
    return { action: "updated", row: rowNumber, matched_rows: matchingRows };
  }
  if (operation !== "append") throw new Error("operation_must_be_append_update_or_skip");
  const values = headers.map((header) => record[header] ?? "");
  const rowNumber = Math.max(rows.length + 1, 2);
  sheet.getRange(`${columnName(dataStart + dataOffset)}${rowNumber}:${columnName(dataStart + dataOffset + headers.length - 1)}${rowNumber}`).values = [values];
  return { action: "appended", row: rowNumber, matched_rows: matchingRows };
}

async function main() {
  const args = argsOf(process.argv);
  if (!args.mode || !args.output || !args.record) throw new Error("requires --mode --output --record");
  const record = JSON.parse(await fs.readFile(args.record, "utf8"));
  if (args.mode === "rebuild") {
    if (!Array.isArray(record.headers) || !Array.isArray(record.rows)) throw new Error("rebuild_requires_headers_and_rows");
    const workbook = Workbook.create();
    const sheet = workbook.worksheets.add(args.sheet || "数据");
    const endColumn = columnName(record.headers.length - 1);
    sheet.getRange(`A1:${endColumn}1`).values = [record.headers];
    sheet.getRange(`A1:${endColumn}1`).format = { fill: "#1F4E78", font: { bold: true, color: "#FFFFFF" }, wrapText: true };
    if (record.rows.length) sheet.getRange(`A2:${endColumn}${record.rows.length + 1}`).values = record.rows;
    sheet.freezePanes.freezeRows(1);
    const output = path.resolve(args.output);
    await fs.mkdir(path.dirname(output), { recursive: true });
    const exported = await SpreadsheetFile.exportXlsx(workbook);
    await exported.save(output);
    const stat = await fs.stat(output);
    if (stat.size > MAX_BYTES) throw new Error("output_exceeds_10mb_limit");
    console.log(JSON.stringify({ ok: true, output, output_size_bytes: stat.size, sheet: sheet.name, action: "rebuilt", row_count: record.rows.length }));
    return;
  }
  const workbook = await loadWorkbook(args.input);
  const sheetName = args.sheet || (args.mode === "log" ? "操作日志" : "数据");
  const sheet = workbook.worksheets.getOrAdd(sheetName, { renameFirstIfOnlyNewSpreadsheet: true });
  const headers = args.mode === "log" ? LOG_HEADERS : [...new Set([...(record.headers || []), "来源文本", "录入日期"])];
  const actualHeaders = ensureHeaders(sheet, headers);
  const values = record.values || record;
  const outcome = appendOrUpdate(sheet, actualHeaders, values, args.operation || "append", record.match_keys || []);
  const output = path.resolve(args.output);
  await fs.mkdir(path.dirname(output), { recursive: true });
  const exported = await SpreadsheetFile.exportXlsx(workbook);
  await exported.save(output);
  const stat = await fs.stat(output);
  if (stat.size > MAX_BYTES) throw new Error("output_exceeds_10mb_limit");
  console.log(JSON.stringify({ ok: true, output, output_size_bytes: stat.size, sheet: sheetName, ...outcome }));
}

main().catch((error) => { console.error(JSON.stringify({ ok: false, error: error.message })); process.exit(1); });
