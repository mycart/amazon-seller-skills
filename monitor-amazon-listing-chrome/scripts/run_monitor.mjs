#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import {
  REPORT_COLUMNS,
  buildMarkdownReport,
  ensureDir,
  expandTasksFromWorkbook,
  loadConfig,
  nowStamp,
  resolveConfigPath,
  summarizeRows,
  writeReportXlsx,
} from "./lib.mjs";
import { scoreListing } from "./score_listing.mjs";
import { sendNotifications } from "./send_notifications.mjs";

const args = parseArgs(process.argv.slice(2));

try {
  if (args["self-test"]) {
    await selfTest();
  } else if (args["prepare-only"] || !args["assemble-run"]) {
    prepareRun(args);
  } else {
    await assembleRun(args);
  }
} catch (error) {
  console.error(error.stack || error.message);
  process.exit(1);
}

function prepareRun(args) {
  const resolution = resolveConfigPath(args.config);
  const configPath = resolution.configPath;
  const config = loadConfig(configPath);
  const excelPath = args.input || config.excel_path;
  if (!excelPath) throw new Error("配置缺少 excel_path");
  if (!fs.existsSync(excelPath)) throw new Error(`Excel 文件不存在: ${excelPath}`);

  const output = normalizedOutput(config);
  ensureDir(output.report_dir);
  ensureDir(output.snapshot_dir);
  ensureDir(output.screenshot_dir);

  const expanded = expandTasksFromWorkbook(excelPath);
  const stamp = nowStamp();
  const runDir = path.join(output.snapshot_dir, `run_${stamp}`);
  ensureDir(runDir);

  const manifest = {
    createdAt: new Date().toISOString(),
    configPath,
    excelPath,
    sheet: expanded.sheet,
    headers: expanded.headers,
    output,
    runtime: config.runtime || {},
    delivery: sanitizeDelivery(config.delivery || {}),
    tasks: expanded.tasks,
    resultFile: path.join(runDir, "browser_results.json"),
    reportBaseName: `amazon_chrome_listing_monitor_${stamp}`,
  };

  fs.writeFileSync(path.join(runDir, "manifest.json"), JSON.stringify(manifest, null, 2), "utf8");
  fs.writeFileSync(path.join(runDir, "browser_results.template.json"), JSON.stringify(expanded.tasks.map((task) => ({
    task,
    status: "FETCH_FAILED",
    url: task.url,
    extractedAt: new Date().toISOString(),
    screenshotPath: "",
    facts: {
      title: "",
      bullets: [],
      imageCount: 0,
      hasAplus: false,
      description: "",
      price: "",
      rating: "",
      reviewCount: "",
      availability: "",
      seller: "",
      category: "",
      bsr: "",
    },
  })), null, 2), "utf8");

  console.log(JSON.stringify({
    ok: true,
    mode: "prepare-only",
    configResolution: {
      source: resolution.source,
      createdConfig: resolution.createdConfig,
      createdExcel: resolution.createdExcel,
    },
    runDir,
    manifestPath: path.join(runDir, "manifest.json"),
    resultFile: manifest.resultFile,
    taskCount: expanded.tasks.length,
    tasks: expanded.tasks,
  }, null, 2));
}

async function assembleRun(args) {
  const runDir = path.resolve(args["assemble-run"]);
  const manifestPath = path.join(runDir, "manifest.json");
  if (!fs.existsSync(manifestPath)) throw new Error(`run manifest 不存在: ${manifestPath}`);
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const resolution = resolveConfigPath(args.config || manifest.configPath);
  const config = loadConfig(resolution.configPath);

  const resultFile = args.results || manifest.resultFile || path.join(runDir, "browser_results.json");
  if (!fs.existsSync(resultFile) && !args["allow-missing-results"]) {
    throw new Error(`Chrome 采集结果不存在: ${resultFile}`);
  }

  const results = fs.existsSync(resultFile)
    ? JSON.parse(fs.readFileSync(resultFile, "utf8"))
    : manifest.tasks.map((task) => ({ task, status: "FETCH_FAILED", url: task.url, facts: { error: "未找到 Chrome 采集结果" } }));

  const byId = new Map(results.map((result) => [result.task?.id || `${result.task?.asin}:${result.task?.site}` || `${result.asin}:${result.site}`, result]));
  const rows = manifest.tasks.map((task) => {
    const result = byId.get(task.id) || { task, status: "FETCH_FAILED", url: task.url, facts: { error: "未采集到该任务结果" } };
    return scoreListing({ ...result, task: { ...task, ...(result.task || {}) }, url: result.url || task.url });
  });

  const output = manifest.output || normalizedOutput(config);
  ensureDir(output.report_dir);
  ensureDir(output.snapshot_dir);
  const reportBaseName = manifest.reportBaseName || `amazon_chrome_listing_monitor_${nowStamp()}`;
  const xlsxPath = path.join(output.report_dir, `${reportBaseName}.xlsx`);
  const mdPath = path.join(output.report_dir, `${reportBaseName}.md`);
  const snapshotPath = path.join(output.snapshot_dir, `${reportBaseName}.json`);

  const summary = summarizeRows(rows);
  const snapshot = {
    summary,
    manifest: {
      runDir,
      configPath: manifest.configPath,
      excelPath: manifest.excelPath,
      sheet: manifest.sheet,
      taskCount: manifest.tasks.length,
    },
    rows,
    rawResults: results,
  };

  writeReportXlsx(xlsxPath, REPORT_COLUMNS, rows);
  fs.writeFileSync(snapshotPath, JSON.stringify(snapshot, null, 2), "utf8");
  fs.writeFileSync(mdPath, buildMarkdownReport(rows, summary, xlsxPath, snapshotPath), "utf8");

  const send = args.send || (!args["no-send"] && config.delivery && (config.delivery.email?.enabled || config.delivery.feishu?.enabled));
  let deliveryReceipt = { skipped: true };
  if (send) {
    deliveryReceipt = await sendNotifications(config.delivery || {}, {
      summary,
      rows,
      mdPath,
      xlsxPath,
      snapshotPath,
    });
  }

  console.log(JSON.stringify({
    ok: true,
    mode: "assemble-run",
    configResolution: {
      source: resolution.source,
      createdConfig: resolution.createdConfig,
      createdExcel: resolution.createdExcel,
    },
    report: { mdPath, xlsxPath, snapshotPath },
    summary,
    deliveryReceipt,
  }, null, 2));
}

async function selfTest() {
  const fake = {
    task: {
      asin: "B0TESTASIN",
      site: "DE",
      url: "https://www.amazon.de/dp/B0TESTASIN",
      storeName: "Example Store",
      sellerId: "",
      remark: "self-test",
    },
    status: "OK",
    facts: {
      title: "Example Brand Orthopedic Dog Bed Washable Large Pet Sofa for Indoor Use",
      bullets: ["Supportive foam", "Washable cover", "Non-slip bottom", "Soft surface", "Multiple sizes"],
      imageCount: 7,
      hasAplus: true,
      description: "This dog bed is designed for comfort, support, and easy daily care with a removable washable cover.",
      price: "€39.99",
      rating: "4.5",
      reviewCount: "128",
      seller: "Example Store",
      category: "Pet Supplies",
      bsr: "#123 in Pet Supplies",
    },
  };
  console.log(JSON.stringify(scoreListing(fake), null, 2));
}

function normalizedOutput(config) {
  return {
    report_dir: config.output?.report_dir || "/Users/apple/Documents/Listing优化建议/amazon_chrome_listing_monitor/reports",
    snapshot_dir: config.output?.snapshot_dir || "/Users/apple/Documents/Listing优化建议/amazon_chrome_listing_monitor/snapshots",
    screenshot_dir: config.output?.screenshot_dir || "/Users/apple/Documents/Listing优化建议/amazon_chrome_listing_monitor/screenshots",
  };
}

function sanitizeDelivery(delivery) {
  return {
    email: {
      enabled: Boolean(delivery.email?.enabled),
      smtp_host: delivery.email?.smtp_host || "",
      smtp_port: delivery.email?.smtp_port || "",
      secure: Boolean(delivery.email?.secure),
      username: delivery.email?.username || "",
      from: delivery.email?.from || "",
      to: delivery.email?.to || [],
    },
    feishu: {
      enabled: Boolean(delivery.feishu?.enabled),
      webhook_url_env: delivery.feishu?.webhook_url_env || "",
      secret_env: delivery.feishu?.secret_env || "",
    },
  };
}

function parseArgs(argv) {
  const parsed = {};
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (!arg.startsWith("--")) continue;
    const key = arg.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      parsed[key] = true;
    } else {
      parsed[key] = next;
      i++;
    }
  }
  return parsed;
}
