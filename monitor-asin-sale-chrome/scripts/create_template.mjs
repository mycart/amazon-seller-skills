#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { ensureRuntime, workspaceRoot } from "./setup_runtime.mjs";

const WORKSHEET = "ASIN监控清单";
const HEADERS = [
  "备注",
  "店铺名称",
  "ASIN值",
  "多站点简写（将多个站点写到一起通过标点符号分开多个站点）",
  "卖家ID（可选）",
];

function defaultOutputPath(root) {
  return path.join(root, "amazon_availability_monitor", "ASIN可购买性监控模板.xlsx");
}

function createWorkbook(outputPath) {
  const require = ensureRuntime(["xlsx"]);
  const XLSX = require("xlsx");
  const rows = [
    HEADERS,
    ["中文商品说明", "Your Store Name", "B0XXXXXXX", "US, CA", ""],
    ["中文商品说明", "Your Store Name", "B0YYYYYYY", "UK；DE；FR", ""],
  ];
  const sheet = XLSX.utils.aoa_to_sheet(rows);
  sheet["!cols"] = [{ wch: 28 }, { wch: 28 }, { wch: 16 }, { wch: 56 }, { wch: 24 }];
  sheet["!autofilter"] = { ref: "A1:E1" };
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, sheet, WORKSHEET);
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  XLSX.writeFile(workbook, outputPath);
}

function ensureConfig(root, outputPath) {
  const configPath = path.join(root, "amazon_availability_monitor", "config.yaml");
  if (fs.existsSync(configPath)) return;
  const config = `# Amazon ASIN 可购买性监控配置
# Excel 文件可移动到任意 Google Drive 本地同步目录；移动后只更新 excel_path。
excel_path: "${outputPath.replaceAll("\\", "\\\\")}"
check_frequency_hours: 6
alert_after_consecutive_failures: 2
check_attempts_per_target: 2
confirmation_mode: "abnormal_only"
max_parallel_site_groups: 1
reuse_delivery_location_per_site: true
delivery_strategy: "marketplace_default"
delivery_location_required: false

delivery_locations:
  US:
    postal_code: "10001"
  CA:
    postal_code: "M5V 2T6"
  MX:
    postal_code: "06700"
  UK:
    postal_code: "SW1A 1AA"
  DE:
    postal_code: "10115"
  FR:
    postal_code: "75001"
  IT:
    postal_code: "00118"
  ES:
    postal_code: "28001"
  NL:
    postal_code: "1012"
  SE:
    postal_code: "111 22"
  PL:
    postal_code: "00-001"
  BE:
    postal_code: "1000"
  JP:
    postal_code: "100-0001"
  AU:
    postal_code: "2000"
  IN:
    postal_code: "110001"
  SG:
    postal_code: "018956"
  AE:
    postal_code: "00000"
  SA:
    postal_code: "12211"

browser:
  provider: "codex_chrome_plugin"
  timeout_ms: 45000
  screenshot_on_success: false

anti_bot:
  continue_shopping_retries: 2
  retry_wait_ms: 3000

screenshots:
  format: "jpeg"
  quality: 65
  full_page: false
  retention_days: 14
  max_files: 500
  cleanup_on_run: true

email:
  enabled: false
  smtp_host: "smtp.example.com"
  smtp_port: 465
  secure: true
  username: "your-email@example.com"
  password: "your-smtp-password-or-app-password"
  from: "your-email@example.com"
  to:
    - "alerts@example.com"

feishu:
  enabled: false
  webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/REPLACE_ME"
  secret: ""
`;
  fs.writeFileSync(configPath, config, "utf8");
}

const root = workspaceRoot();
const outputPath = process.argv[2] ? path.resolve(process.argv[2]) : defaultOutputPath(root);
createWorkbook(outputPath);
ensureConfig(root, outputPath);
console.log(`[template] Created ${outputPath}`);
