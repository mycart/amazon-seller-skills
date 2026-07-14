import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

export const DEFAULT_CONFIG = "/Users/apple/Documents/Listing优化建议/amazon_chrome_listing_monitor/config.yaml";
export const DEFAULT_PYTHON = "/Users/apple/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3";
export const WORKSPACE_CONFIG = "config.yaml";
export const WORKSPACE_EXCEL = "ASIN可购买性监控模板.xlsx";

export const SITE_DOMAINS = {
  US: "www.amazon.com",
  CA: "www.amazon.ca",
  MX: "www.amazon.com.mx",
  UK: "www.amazon.co.uk",
  DE: "www.amazon.de",
  FR: "www.amazon.fr",
  IT: "www.amazon.it",
  ES: "www.amazon.es",
  NL: "www.amazon.nl",
  BE: "www.amazon.com.be",
  JP: "www.amazon.co.jp",
  AU: "www.amazon.com.au",
  IN: "www.amazon.in",
};

export const REPORT_COLUMNS = [
  "备注",
  "Listing完整度和质量评分",
  "页面状态",
  "ASIN值",
  "国家",
  "站点URL",
  "店铺名称",
  "核心优化建议",
  "Listing是否建议优化",
  "Listing优化优先级",
  "主要问题/缺失",
  "卖家ID",
  "标题",
  "五点",
  "图片",
  "A+",
  "描述",
  "价格",
  "评论",
  "SEO",
  "卖家匹配",
  "采集时间",
  "截图路径",
];

export function nowStamp(date = new Date()) {
  const pad = (n, width = 2) => String(n).padStart(width, "0");
  return [
    date.getFullYear(),
    pad(date.getMonth() + 1),
    pad(date.getDate()),
    "_",
    pad(date.getHours()),
    pad(date.getMinutes()),
    pad(date.getSeconds()),
    pad(date.getMilliseconds(), 3),
  ].join("");
}

export function loadConfig(configPath = DEFAULT_CONFIG) {
  if (!fs.existsSync(configPath)) {
    throw new Error(`配置文件不存在: ${configPath}`);
  }
  const text = fs.readFileSync(configPath, "utf8");
  const config = parseSimpleYaml(text);
  config.__path = configPath;
  return config;
}

export function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

export function resolveWorkspacePaths(cwd = process.cwd()) {
  const root = path.resolve(cwd);
  return {
    root,
    configPath: path.join(root, WORKSPACE_CONFIG),
    excelPath: path.join(root, WORKSPACE_EXCEL),
    reportDir: path.join(root, "reports"),
    snapshotDir: path.join(root, "snapshots"),
    screenshotDir: path.join(root, "screenshots"),
  };
}

export function parseSimpleYaml(text) {
  const root = {};
  const stack = [{ indent: -1, value: root }];
  const lines = text.split(/\r?\n/);

  for (let lineIndex = 0; lineIndex < lines.length; lineIndex++) {
    const rawLine = lines[lineIndex];
    const withoutComment = stripYamlComment(rawLine);
    if (!withoutComment.trim()) continue;
    const indent = withoutComment.match(/^\s*/)[0].length;
    const line = withoutComment.trim();

    while (stack.length > 1 && indent <= stack[stack.length - 1].indent) stack.pop();
    const parent = stack[stack.length - 1].value;

    if (line.startsWith("- ")) {
      if (!Array.isArray(parent)) {
        throw new Error(`YAML 列表缩进无法解析: ${rawLine}`);
      }
      parent.push(parseYamlValue(line.slice(2).trim()));
      continue;
    }

    const match = line.match(/^([^:]+):(.*)$/);
    if (!match) throw new Error(`YAML 行无法解析: ${rawLine}`);
    const key = match[1].trim();
    const rest = match[2].trim();
    if (rest) {
      parent[key] = parseYamlValue(rest);
      continue;
    }

    const nextLine = nextContentLine(lines, lineIndex + 1);
    const nextIsArray = nextLine && nextLine.trim().startsWith("- ");
    parent[key] = nextIsArray ? [] : {};
    stack.push({ indent, value: parent[key] });
  }
  return root;
}

function stripYamlComment(line) {
  let inQuote = false;
  let quote = "";
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if ((ch === '"' || ch === "'") && line[i - 1] !== "\\") {
      if (!inQuote) {
        inQuote = true;
        quote = ch;
      } else if (quote === ch) {
        inQuote = false;
      }
    }
    if (ch === "#" && !inQuote) return line.slice(0, i);
  }
  return line;
}

function nextContentLine(lines, start) {
  for (let i = start; i < lines.length; i++) {
    const line = stripYamlComment(lines[i]);
    if (line.trim()) return line;
  }
  return "";
}

function parseYamlValue(value) {
  if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
    return value.slice(1, -1);
  }
  if (value === "true") return true;
  if (value === "false") return false;
  if (value === "null") return null;
  if (/^-?\d+(\.\d+)?$/.test(value)) return Number(value);
  return value;
}

export function splitSites(raw) {
  return String(raw || "")
    .split(/[,，;；、/\s\r\n]+/g)
    .map((site) => site.trim().toUpperCase())
    .filter(Boolean);
}

export function amazonUrl(asin, site) {
  const domain = SITE_DOMAINS[site];
  if (!domain) throw new Error(`不支持的 Amazon 站点: ${site}`);
  return `https://${domain}/dp/${encodeURIComponent(asin)}`;
}

export function runPython(code, input = undefined) {
  const python = process.env.PYTHON || (fs.existsSync(DEFAULT_PYTHON) ? DEFAULT_PYTHON : "python3");
  const result = spawnSync(python, ["-c", code], {
    input: input == null ? undefined : JSON.stringify(input),
    encoding: "utf8",
    maxBuffer: 50 * 1024 * 1024,
  });
  if (result.status !== 0) {
    throw new Error(`Python 执行失败: ${result.stderr || result.stdout}`);
  }
  return result.stdout;
}

export function createExcelTemplate(excelPath) {
  ensureDir(path.dirname(excelPath));
  const code = String.raw`
import json, sys
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
payload = json.loads(sys.stdin.read())
wb = Workbook()
ws = wb.active
ws.title = "ASIN监控清单"
headers = ["店铺名称", "ASIN值", "多站点简写（将多个站点写到一起通过标点符号分开多个站点）", "卖家ID（可选）"]
ws.append(headers)
ws.append(["PetComfort by CareCooo", "B0DFWBK6PG", "DE,IT", ""])
for cell in ws[1]:
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="1F4E78")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
for i, width in enumerate([28, 18, 52, 22], start=1):
    ws.column_dimensions[get_column_letter(i)].width = width
wb.save(payload["output"])
print(payload["output"])
`;
  runPython(code, { output: excelPath });
}

export function createWorkspaceConfigTemplate(configPath, options = {}) {
  const paths = resolveWorkspacePaths(path.dirname(configPath));
  const runtime = {
    browser: options.runtime?.browser || "chrome",
    max_parallel_pages: options.runtime?.max_parallel_pages ?? 1,
    min_delay_ms: options.runtime?.min_delay_ms ?? 5000,
    max_delay_ms: options.runtime?.max_delay_ms ?? 12000,
    retry_on_abnormal: options.runtime?.retry_on_abnormal ?? 1,
    alert_after_consecutive_failures: options.runtime?.alert_after_consecutive_failures ?? 2,
    screenshot_on_abnormal: options.runtime?.screenshot_on_abnormal ?? true,
    screenshot_on_success: options.runtime?.screenshot_on_success ?? false,
  };
  const delivery = normalizeDeliveryTemplate(options.delivery);
  const yaml = buildYaml({
    excel_path: paths.excelPath,
    output: {
      report_dir: paths.reportDir,
      snapshot_dir: paths.snapshotDir,
      screenshot_dir: paths.screenshotDir,
    },
    runtime,
    delivery,
  });
  ensureDir(path.dirname(configPath));
  fs.writeFileSync(configPath, yaml, "utf8");
}

export function resolveConfigPath(explicitConfigPath) {
  if (explicitConfigPath) {
    return {
      configPath: path.resolve(explicitConfigPath),
      createdConfig: false,
      createdExcel: false,
      source: "explicit",
    };
  }

  const workspace = resolveWorkspacePaths();
  if (fs.existsSync(workspace.configPath)) {
    return {
      configPath: workspace.configPath,
      createdConfig: false,
      createdExcel: false,
      source: "workspace",
    };
  }

  let createdExcel = false;
  if (!fs.existsSync(workspace.excelPath)) {
    const legacyConfig = fs.existsSync(DEFAULT_CONFIG) ? loadConfig(DEFAULT_CONFIG) : null;
    const legacyExcelPath = legacyConfig?.excel_path;
    if (legacyExcelPath && fs.existsSync(legacyExcelPath)) {
      ensureDir(path.dirname(workspace.excelPath));
      fs.copyFileSync(legacyExcelPath, workspace.excelPath);
    } else {
      createExcelTemplate(workspace.excelPath);
    }
    createdExcel = true;
  }

  const legacyConfig = fs.existsSync(DEFAULT_CONFIG) ? loadConfig(DEFAULT_CONFIG) : null;
  createWorkspaceConfigTemplate(workspace.configPath, {
    runtime: legacyConfig?.runtime,
    delivery: legacyConfig?.delivery,
  });

  return {
    configPath: workspace.configPath,
    createdConfig: true,
    createdExcel,
    source: fs.existsSync(DEFAULT_CONFIG) ? "workspace-from-default" : "workspace-template",
  };
}

export function readExcelRows(excelPath, sheetName = "ASIN监控清单") {
  const code = String.raw`
import json, sys
from openpyxl import load_workbook
payload = json.loads(sys.stdin.read())
path = payload["path"]
sheet_name = payload.get("sheetName")
wb = load_workbook(path, read_only=True, data_only=True)
ws = wb[sheet_name] if sheet_name in wb.sheetnames else wb[wb.sheetnames[0]]
rows = []
for row in ws.iter_rows(values_only=True):
    rows.append(["" if c is None else c for c in row])
print(json.dumps({"sheet": ws.title, "rows": rows}, ensure_ascii=False))
`;
  return JSON.parse(runPython(code, { path: excelPath, sheetName }));
}

export function writeReportXlsx(xlsxPath, columns, rows) {
  const code = String.raw`
import json, sys
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
payload = json.loads(sys.stdin.read())
wb = Workbook()
ws = wb.active
ws.title = "Listing监控明细"
columns = payload["columns"]
rows = payload["rows"]
ws.append(columns)
for cell in ws[1]:
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="1F4E78")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
for row in rows:
    ws.append([row.get(col, "") for col in columns])
for col_idx, column in enumerate(columns, start=1):
    width = min(max(len(str(column)) + 4, 12), 36)
    for row_idx in range(2, min(ws.max_row, 80) + 1):
        value = ws.cell(row=row_idx, column=col_idx).value
        if value is not None:
            width = min(max(width, len(str(value)) + 2), 60)
    ws.column_dimensions[get_column_letter(col_idx)].width = width
for row in ws.iter_rows():
    for cell in row:
        cell.alignment = Alignment(vertical="top", wrap_text=True)
ws.freeze_panes = "A2"
wb.save(payload["path"])
print(payload["path"])
`;
  runPython(code, { path: xlsxPath, columns, rows });
}

export function expandTasksFromWorkbook(excelPath) {
  const workbook = readExcelRows(excelPath);
  const rows = workbook.rows;
  if (!rows.length) throw new Error(`Excel 没有数据: ${excelPath}`);
  const headers = rows[0].map((value) => String(value || "").trim());
  const required = [
    "店铺名称",
    "ASIN值",
    "多站点简写（将多个站点写到一起通过标点符号分开多个站点）",
  ];
  for (const name of required) {
    if (!headers.includes(name)) throw new Error(`Excel 缺少必填列: ${name}`);
  }
  const index = Object.fromEntries(headers.map((name, i) => [name, i]));
  const seen = new Set();
  const tasks = [];
  for (let rowNumber = 2; rowNumber <= rows.length; rowNumber++) {
    const row = rows[rowNumber - 1] || [];
    const storeName = String(row[index["店铺名称"]] || "").trim();
    const asin = String(row[index["ASIN值"]] || "").trim().toUpperCase();
    const sitesRaw = row[index["多站点简写（将多个站点写到一起通过标点符号分开多个站点）"]];
    const sellerId = index["卖家ID（可选）"] != null ? String(row[index["卖家ID（可选）"]] || "").trim() : "";
    const remark = index["备注"] != null ? String(row[index["备注"]] || "").trim() : "";
    if (!asin && !storeName && !sitesRaw) continue;
    if (!asin) throw new Error(`Excel 第 ${rowNumber} 行缺少 ASIN值`);
    const sites = splitSites(sitesRaw);
    if (!sites.length) throw new Error(`Excel 第 ${rowNumber} 行缺少国家站点`);
    for (const site of sites) {
      if (!SITE_DOMAINS[site]) throw new Error(`Excel 第 ${rowNumber} 行站点不支持: ${site}`);
      const key = `${asin}:${site}`;
      if (seen.has(key)) continue;
      seen.add(key);
      tasks.push({
        id: key,
        rowNumber,
        asin,
        site,
        url: amazonUrl(asin, site),
        storeName,
        sellerId,
        remark,
      });
    }
  }
  return { sheet: workbook.sheet, headers, tasks };
}

export function buildMarkdownReport(rows, summary, xlsxPath, snapshotPath) {
  const lines = [];
  lines.push("# Amazon Listing 完整度监控报告");
  lines.push("");
  lines.push(`生成时间：${summary.generatedAt}`);
  lines.push(`任务总数：${summary.total}`);
  lines.push(`可审查：${summary.scorable}`);
  lines.push(`建议优化：${summary.optimizable}`);
  lines.push(`无法审查：${summary.unreviewable}`);
  lines.push("");
  lines.push(`Excel报告：${xlsxPath}`);
  lines.push(`JSON快照：${snapshotPath}`);
  lines.push("");
  lines.push("| 备注 | 评分 | 是否优化 | 优先级 | 主要问题/缺失 | ASIN | 国家 | 页面状态 | URL |");
  lines.push("|---|---|---|---|---|---|---|---|---|");
  for (const row of rows) {
    lines.push([
      row["备注"],
      row["Listing完整度和质量评分"],
      row["Listing是否建议优化"],
      row["Listing优化优先级"],
      row["主要问题/缺失"] || row["Listing缺失的部分"] || row["Listing不足的地方"],
      row["ASIN值"],
      row["国家"],
      row["页面状态"],
      row["站点URL"],
    ].map(markdownCell).join("|").replace(/^/, "|").replace(/$/, "|"));
  }
  return `${lines.join("\n")}\n`;
}

function buildYaml(value, indent = 0) {
  if (Array.isArray(value)) {
    if (!value.length) return "[]";
    return value
      .map((item) => {
        if (item && typeof item === "object") {
          const nested = buildYaml(item, indent + 2);
          return `${" ".repeat(indent)}-\n${nested}`;
        }
        return `${" ".repeat(indent)}- ${formatYamlScalar(item)}`;
      })
      .join("\n");
  }

  if (value && typeof value === "object") {
    return Object.entries(value)
      .map(([key, item]) => {
        if (Array.isArray(item)) {
          if (!item.length) return `${" ".repeat(indent)}${key}: []`;
          return `${" ".repeat(indent)}${key}:\n${buildYaml(item, indent + 2)}`;
        }
        if (item && typeof item === "object") {
          return `${" ".repeat(indent)}${key}:\n${buildYaml(item, indent + 2)}`;
        }
        return `${" ".repeat(indent)}${key}: ${formatYamlScalar(item)}`;
      })
      .join("\n");
  }

  return `${" ".repeat(indent)}${formatYamlScalar(value)}`;
}

function formatYamlScalar(value) {
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return String(value);
  if (value == null) return '""';
  const text = String(value);
  return `"${text.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
}

function normalizeDeliveryTemplate(delivery) {
  return {
    email: {
      enabled: false,
      smtp_host: delivery?.email?.smtp_host || "",
      smtp_port: delivery?.email?.smtp_port || "",
      secure: Boolean(delivery?.email?.secure),
      username: delivery?.email?.username || "",
      password_env: delivery?.email?.password_env || "",
      from: delivery?.email?.from || "",
      to: Array.isArray(delivery?.email?.to) ? delivery.email.to : [],
    },
    feishu: {
      enabled: false,
      webhook_url_env: delivery?.feishu?.webhook_url_env || "",
      secret_env: delivery?.feishu?.secret_env || "",
    },
  };
}

function markdownCell(value) {
  return String(value ?? "").replace(/\|/g, "\\|").replace(/\n/g, "<br>");
}

export function summarizeRows(rows) {
  return {
    generatedAt: new Date().toISOString(),
    total: rows.length,
    scorable: rows.filter((row) => row["Listing完整度和质量评分"] !== "无法审查").length,
    optimizable: rows.filter((row) => row["Listing是否建议优化"] === "是").length,
    unreviewable: rows.filter((row) => row["Listing完整度和质量评分"] === "无法审查").length,
    statuses: rows.reduce((acc, row) => {
      const status = row["页面状态"] || "UNKNOWN";
      acc[status] = (acc[status] || 0) + 1;
      return acc;
    }, {}),
  };
}
