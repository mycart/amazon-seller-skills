#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { ensureRuntime, workspaceRoot } from "./setup_runtime.mjs";
import { sendAlerts, summaryHeadline } from "./send_alerts.mjs";

const SHEET_NAME = "ASIN监控清单";
const HEADERS = {
  remark: "备注",
  seller: "店铺名称",
  asin: "ASIN值",
  sites: "多站点简写（将多个站点写到一起通过标点符号分开多个站点）",
  sellerId: "卖家ID（可选）",
};

const SITE_MAP = {
  US: "amazon.com",
  CA: "amazon.ca",
  MX: "amazon.com.mx",
  UK: "amazon.co.uk",
  DE: "amazon.de",
  FR: "amazon.fr",
  IT: "amazon.it",
  ES: "amazon.es",
  NL: "amazon.nl",
  SE: "amazon.se",
  PL: "amazon.pl",
  BE: "amazon.com.be",
  JP: "amazon.co.jp",
  AU: "amazon.com.au",
  IN: "amazon.in",
  SG: "amazon.sg",
  AE: "amazon.ae",
  SA: "amazon.sa",
};

const PRODUCT_NAME_DICTIONARY = [
  { patterns: [/orthopedic dog bed/i, /dog bed/i, /pet bed/i, /hundebett/i, /cuccia per cani/i, /panier pour chien/i], zh: "狗床" },
  { patterns: [/dog stairs/i, /pet stairs/i, /dog steps/i, /pet steps/i, /haustiertreppe/i, /escaliers pour chien/i], zh: "狗楼梯" },
  { patterns: [/dog blanket/i, /pet blanket/i, /waterproof.*blanket/i, /hundedecke/i, /coperta per cani/i], zh: "狗毯" },
  { patterns: [/dog ramp/i, /pet ramp/i, /hundrampe/i], zh: "狗坡道" },
  { patterns: [/dog crate/i, /pet crate/i, /dog kennel/i], zh: "狗笼" },
  { patterns: [/dog harness/i, /pet harness/i], zh: "狗胸背带" },
  { patterns: [/dog leash/i, /pet leash/i], zh: "狗牵引绳" },
  { patterns: [/dog collar/i, /pet collar/i], zh: "狗项圈" },
  { patterns: [/dog bowl/i, /pet bowl/i], zh: "狗碗" },
  { patterns: [/cat tree/i, /cat tower/i], zh: "猫爬架" },
  { patterns: [/cat bed/i], zh: "猫床" },
  { patterns: [/pet carrier/i, /dog carrier/i, /cat carrier/i], zh: "宠物包" },
  { patterns: [/pet mat/i, /dog mat/i], zh: "宠物垫" },
  { patterns: [/sofa cover/i, /couch cover/i], zh: "沙发罩" },
];

function configPath(root) {
  return path.join(root, "amazon_availability_monitor", "config.yaml");
}

function normalizeSeller(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "");
}

function splitSites(value) {
  return String(value || "")
    .split(/[,，;；、/\s\r\n]+/u)
    .map((site) => site.trim().toUpperCase())
    .filter(Boolean);
}

function amazonUrl(domain, asin) {
  return `https://www.${domain}/dp/${encodeURIComponent(asin)}`;
}

function normalizeSellerId(value) {
  return String(value || "")
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "");
}

function cleanProductTitle(title) {
  return String(title || "")
    .replace(/\|.*$/g, " ")
    .replace(/:.*$/g, " ")
    .replace(/\bamazon\b.*$/gi, " ")
    .replace(/\b(prime|sale|new|upgrade|upgraded|with|for|and|the|a|an|of|to|in|on)\b/gi, " ")
    .replace(/\b(xs|s|m|l|xl|xxl|small|medium|large|extra large)\b/gi, " ")
    .replace(/\b(black|white|grey|gray|brown|blue|green|red|pink|beige|cream)\b/gi, " ")
    .replace(/\b\d+(\.\d+)?\s?(cm|mm|m|inch|inches|in|ft|kg|g|lb|lbs|pack|pcs?)\b/gi, " ")
    .replace(/\b[A-Z0-9]{6,}\b/g, " ")
    .replace(/[^\p{L}\p{N}\s-]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function extractProductNameZh(title) {
  const rawTitle = String(title || "").trim();
  if (!rawTitle) return "";
  for (const entry of PRODUCT_NAME_DICTIONARY) {
    if (entry.patterns.some((pattern) => pattern.test(rawTitle))) return entry.zh;
  }
  const cleaned = cleanProductTitle(rawTitle);
  if (!cleaned) return rawTitle.split(/\s+/).slice(0, 6).join(" ");
  return cleaned.split(/\s+/).slice(0, 6).join(" ");
}

function buildProductUrl(target) {
  const url = new URL(amazonUrl(target.domain, target.asin));
  if (target.sellerId) url.searchParams.set("m", target.sellerId);
  return url.toString();
}

function loadConfig(require, root) {
  const YAML = require("yaml");
  const file = configPath(root);
  if (!fs.existsSync(file)) {
    throw new Error(`Missing config: ${file}. Run create_template.mjs first.`);
  }
  const config = YAML.parse(fs.readFileSync(file, "utf8")) || {};
  if (!config.excel_path) throw new Error(`Missing excel_path in ${file}`);
  if (!fs.existsSync(config.excel_path)) {
    throw new Error(`Configured excel_path does not exist: ${config.excel_path}`);
  }
  return config;
}

function loadTargets(require, excelPath) {
  const XLSX = require("xlsx");
  const workbook = XLSX.readFile(excelPath, { cellDates: false });
  const sheet = workbook.Sheets[SHEET_NAME] || workbook.Sheets[workbook.SheetNames[0]];
  if (!sheet) throw new Error(`Workbook has no sheets: ${excelPath}`);
  const rows = XLSX.utils.sheet_to_json(sheet, { defval: "" });
  const targets = [];
  let lastSeller = "";
  let lastSites = [];
  for (const [index, row] of rows.entries()) {
    const rawSeller = String(row[HEADERS.seller] || "").trim();
    const remark = String(row[HEADERS.remark] || "").trim();
    const asin = String(row[HEADERS.asin] || "").trim().toUpperCase();
    const sellerId = normalizeSellerId(row[HEADERS.sellerId]);
    const rawSites = splitSites(row[HEADERS.sites]);
    if (!rawSeller && !asin && !rawSites.length) continue;
    const seller = rawSeller || lastSeller;
    const sites = rawSites.length ? rawSites : lastSites;
    if (!seller || !asin || !sites.length) {
      throw new Error(`Row ${index + 2} is missing required fields.`);
    }
    lastSeller = seller;
    lastSites = sites;
    for (const siteCode of sites) {
      const domain = SITE_MAP[siteCode];
      if (!domain) throw new Error(`Row ${index + 2} has unsupported site code: ${siteCode}`);
      targets.push({
        remark,
        seller,
        expectedSeller: seller,
        sellerId,
        asin,
        siteCode,
        country: siteCode,
        domain,
        url: buildProductUrl({ domain, asin, sellerId }),
      });
    }
  }
  return targets;
}

function groupTargetsBySite(targets) {
  const groups = new Map();
  for (const target of targets) {
    if (!groups.has(target.siteCode)) groups.set(target.siteCode, []);
    groups.get(target.siteCode).push(target);
  }
  return Array.from(groups.entries()).map(([siteCode, siteTargets]) => ({ siteCode, targets: siteTargets }));
}

export function isAmazonAccessBlockedPage(bodyText, title = "", url = "") {
  const text = `${title}\n${bodyText}\n${url}`;
  return /click\s+the\s+button\s+below\s+to\s+continue\s+shopping|点击.*继续购物|captcha|enter\s+the\s+characters|not\s+a\s+robot|robot\s+check|type\s+the\s+characters|\/errors\/validatecaptcha/iu.test(text);
}

function pageUrlSellerId(url) {
  try {
    return normalizeSellerId(new URL(url).searchParams.get("m") || "");
  } catch {
    return "";
  }
}

function sellerMatches(result, target) {
  const sellerNameMatches = normalizeSeller(result.detectedSeller).includes(normalizeSeller(target.seller));
  if (!target.sellerId) return { matched: sellerNameMatches, method: "seller_name" };
  const detectedSellerId = normalizeSellerId(result.detectedSellerId);
  const sellerIdMatches = detectedSellerId === target.sellerId || pageUrlSellerId(result.finalUrl) === target.sellerId;
  if (sellerIdMatches) return { matched: true, method: "seller_id" };
  if (sellerNameMatches) return { matched: true, method: "seller_name_fallback" };
  return { matched: false, method: "seller_id" };
}

function normalizeChromeObservation(observation, target, config) {
  const detectedAt = observation.detectedAt || new Date().toISOString();
  const productTitle = observation.productTitle || observation.title || "";
  const bodyText = observation.bodyText || "";
  const title = observation.title || productTitle;
  const finalUrl = observation.finalUrl || observation.url || target.url;
  const result = {
    ...target,
    attempt: Number(observation.attempt || target.attempt || 1),
    attemptsPlanned: Number(observation.attemptsPlanned || config.check_attempts_per_target || config.alert_after_consecutive_failures || 2),
    status: observation.status || "PAGE_ERROR",
    detectedAt,
    price: observation.price || "",
    detectedSeller: observation.detectedSeller || "",
    availabilityText: observation.availabilityText || "",
    title,
    screenshotPath: observation.screenshotPath || "",
    reason: observation.reason || "",
    deliveryLocation: null,
    deliveryStatus: "Chrome 插件按站点默认地址检测",
    deliveryStatusCode: "chrome_plugin",
    deliveryWarning: "",
    detectionStrategy: "codex_chrome_plugin",
    detectedSellerId: normalizeSellerId(observation.detectedSellerId),
    sellerMatchMethod: observation.sellerMatchMethod || "",
    finalUrl,
    productTitle,
    productNameZh: observation.productNameZh || extractProductNameZh(productTitle),
    accessBlocked: observation.accessBlocked === true,
    accessRecoveryAttempts: Number(observation.accessRecoveryAttempts || 0),
  };

  if (observation.pageError === true || /looking for something|page not found|sorry.*couldn't find that page/iu.test(bodyText)) {
    result.status = "PAGE_ERROR";
    result.reason = observation.reason || "Amazon page error text detected";
    return result;
  }

  const addToCartVisible = observation.addToCartVisible === true;
  const buyNowVisible = observation.buyNowVisible === true;
  const unavailable = observation.unavailable === true || /currently unavailable|out of stock|temporarily out of stock|unavailable|nicht verfügbar|indisponible|non disponibile|no disponible|在庫切れ/iu.test(`${result.availabilityText}\n${bodyText}`);
  const hasCartSignal = Object.hasOwn(observation, "addToCartVisible");
  const hasUnavailableSignal = Object.hasOwn(observation, "unavailable");
  const hasProductPageSignals = Boolean(
    productTitle ||
    result.price ||
    result.detectedSeller ||
    result.availabilityText ||
    addToCartVisible ||
    buyNowVisible ||
    unavailable
  );
  const accessBlockedSignal = observation.accessBlocked === true || isAmazonAccessBlockedPage(bodyText, title, finalUrl);
  const accessBlocked = accessBlockedSignal && !hasProductPageSignals;
  if (accessBlocked) {
    result.status = "ACCESS_BLOCKED";
    result.accessBlocked = true;
    result.reason = observation.reason || "Amazon access blocked or captcha page detected by Chrome plugin";
    return result;
  }
  result.accessBlocked = false;

  if (observation.status && !hasProductPageSignals && !hasCartSignal && !hasUnavailableSignal) {
    return result;
  }

  if (!addToCartVisible || unavailable) {
    result.status = "UNAVAILABLE";
    result.reason = accessBlockedSignal
      ? `addToCart=${addToCartVisible}, buyNow=${buyNowVisible}, unavailableText=${unavailable}`
      : observation.reason || `addToCart=${addToCartVisible}, buyNow=${buyNowVisible}, unavailableText=${unavailable}`;
    return result;
  }

  const sellerMatch = sellerMatches(result, target);
  result.sellerMatchMethod = sellerMatch.method;
  if (!sellerMatch.matched) {
    result.status = "SELLER_MISMATCH";
    result.reason = target.sellerId
      ? "Seller ID or Sold by seller does not match expected store"
      : "Sold by seller does not match expected store";
    return result;
  }

  result.status = "BUYABLE";
  result.reason = `Product page is buyable and seller matches by ${sellerMatch.method}`;
  return result;
}

function loadState(root) {
  const statePath = path.join(root, "amazon_availability_monitor", "data", "current_status.json");
  if (!fs.existsSync(statePath)) return {};
  return JSON.parse(fs.readFileSync(statePath, "utf8"));
}

function saveState(root, state) {
  const statePath = path.join(root, "amazon_availability_monitor", "data", "current_status.json");
  fs.mkdirSync(path.dirname(statePath), { recursive: true });
  fs.writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`, "utf8");
}

function appendSnapshots(root, results) {
  const snapshotPath = path.join(root, "amazon_availability_monitor", "data", "snapshots.jsonl");
  fs.mkdirSync(path.dirname(snapshotPath), { recursive: true });
  fs.appendFileSync(snapshotPath, results.map((row) => JSON.stringify(row)).join("\n") + "\n", "utf8");
}

function updateStateAndAlerts(root, results, config) {
  const state = loadState(root);
  const threshold = Number(config.alert_after_consecutive_failures || 2);
  const alerts = [];
  const grouped = new Map();
  for (const result of results) {
    const key = `${result.asin}|${result.siteCode}`;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(result);
  }

  for (const [key, attempts] of grouped.entries()) {
    const lastResult = attempts.at(-1);
    const previous = state[key] || { consecutiveFailures: 0, lastAlertKey: "" };
    const alertableAttempts = attempts.filter((result) => result.status !== "ACCESS_BLOCKED");
    const abnormalAttempts = alertableAttempts.filter((result) => result.status !== "BUYABLE");
    const abnormal = alertableAttempts.length > 0 && abnormalAttempts.length === alertableAttempts.length;
    const consecutiveFailures = abnormal ? abnormalAttempts.length : 0;
    const statusSeries = alertableAttempts.map((result) => result.status).join(">") || attempts.map((result) => result.status).join(">");
    const alertKey = `${statusSeries}|${lastResult.detectedSeller || ""}|${lastResult.reason || ""}`;
    const shouldAlert = abnormal && consecutiveFailures >= threshold;
    const alertResult = {
      ...lastResult,
      attempts: alertableAttempts.length || attempts.length,
      abnormalAttempts: abnormalAttempts.length,
      attemptStatuses: (alertableAttempts.length ? alertableAttempts : attempts).map((result) => result.status),
      firstDetectedAt: (alertableAttempts[0] || attempts[0])?.detectedAt,
    };
    state[key] = {
      asin: lastResult.asin,
      siteCode: lastResult.siteCode,
      domain: lastResult.domain,
      status: lastResult.status,
      consecutiveFailures,
      attempts: attempts.length,
      accessBlocked: attempts.every((result) => result.status === "ACCESS_BLOCKED"),
      lastCheckedAt: lastResult.detectedAt,
      lastAlertKey: shouldAlert ? alertKey : abnormal ? previous.lastAlertKey : "",
    };
    if (shouldAlert) alerts.push(alertResult);
  }
  saveState(root, state);
  return alerts;
}

function reportTimestamp(date = new Date()) {
  const pad = (value) => String(value).padStart(2, "0");
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}_${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`;
}

function groupAttemptStatuses(results) {
  const grouped = new Map();
  for (const result of results) {
    const key = `${result.asin}|${result.siteCode}`;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(result.status);
  }
  return grouped;
}

function finalResultsByTarget(results) {
  const grouped = new Map();
  const order = [];
  for (const result of results) {
    const key = `${result.asin}|${result.siteCode}`;
    if (!grouped.has(key)) order.push(key);
    grouped.set(key, result);
  }
  return order.map((key) => grouped.get(key));
}

function saleStatusLabel(status) {
  const labels = {
    BUYABLE: "正常可售",
    UNAVAILABLE: "不可售/缺货",
    SELLER_MISMATCH: "卖家不匹配",
    PAGE_ERROR: "页面异常",
    ACCESS_BLOCKED: "访问受阻",
  };
  return `${status || "UNKNOWN"} ${labels[status] || "状态待确认"}`;
}

function compactParts(parts) {
  return parts.map((part) => String(part || "").trim()).filter(Boolean).join("；");
}

function sellerCheckSummary(row) {
  const expectedSeller = row.seller || row.expectedSeller || "";
  const detectedSeller = row.detectedSeller || "";
  const expectedSellerId = row.sellerId || "";
  const detectedSellerId = row.detectedSellerId || "";
  const matchMethod = row.sellerMatchMethod || "";
  const parts = [];
  if (expectedSeller) parts.push(`期望: ${expectedSeller}`);
  if (detectedSeller) parts.push(`检测: ${detectedSeller}`);
  if (expectedSellerId) parts.push(`期望ID: ${expectedSellerId}`);
  if (detectedSellerId) parts.push(`检测ID: ${detectedSellerId}`);
  if (matchMethod) parts.push(`方式: ${matchMethod}`);
  return compactParts(parts);
}

function availabilitySummary(row) {
  return compactParts([row.availabilityText, row.reason]);
}

function attemptSummary(row, statuses) {
  const attemptText = `${row.attempt || 1}/${row.attemptsPlanned || 1}`;
  const statusText = statuses.get(`${row.asin}|${row.siteCode}`)?.join(" -> ") || row.status || "";
  return statusText ? `${attemptText}；${statusText}` : attemptText;
}

function detailRows(results) {
  const statuses = groupAttemptStatuses(results);
  return finalResultsByTarget(results).map((row) => ({
    "备注": row.remark || "",
    "可售状态": saleStatusLabel(row.status),
    "链接": row.finalUrl || row.url || "",
    "国家/站点": row.siteCode,
    "商品名称": row.productNameZh || "",
    "店铺名称": row.seller || row.expectedSeller || "",
    "卖家核对": sellerCheckSummary(row),
    "价格": row.price || "",
    "可用性/异常原因": availabilitySummary(row),
    "检测次数": attemptSummary(row, statuses),
    "检测时间": row.detectedAt || "",
    ASIN: row.asin,
    "截图": row.screenshotPath || "",
  }));
}

function writeExcelReport(require, root, results, summary) {
  const XLSX = require("xlsx");
  const reportDir = path.join(root, "amazon_availability_monitor", "reports");
  fs.mkdirSync(reportDir, { recursive: true });
  const reportPath = path.join(reportDir, `ASIN销售状态监控报告_${reportTimestamp()}.xlsx`);
  const workbook = XLSX.utils.book_new();

  const detailSheet = XLSX.utils.json_to_sheet(detailRows(results));
  detailSheet["!cols"] = [
    { wch: 28 },
    { wch: 22 },
    { wch: 64 },
    { wch: 12 },
    { wch: 18 },
    { wch: 28 },
    { wch: 54 },
    { wch: 14 },
    { wch: 60 },
    { wch: 30 },
    { wch: 24 },
    { wch: 14 },
    { wch: 56 },
  ];
  XLSX.utils.book_append_sheet(workbook, detailSheet, "明细");

  const summaryRows = [
    { 指标: "总目标数", 值: summary.targets },
    { 指标: "实际检测次数", 值: summary.checked },
    { 指标: "正常可售", 值: summary.buyable },
    { 指标: "真实异常", 值: summary.abnormal },
    { 指标: "访问受阻", 值: summary.access_blocked },
    { 指标: "触发通知数", 值: summary.alerts },
    { 指标: "报告生成时间", 值: new Date().toISOString() },
    { 指标: "通知回执", 值: `email=${summary.alertResult?.email || "skipped"}、feishu=${summary.alertResult?.feishu || "skipped"}` },
  ];
  const summarySheet = XLSX.utils.json_to_sheet(summaryRows);
  summarySheet["!cols"] = [{ wch: 24 }, { wch: 60 }];
  XLSX.utils.book_append_sheet(workbook, summarySheet, "汇总");

  XLSX.writeFile(workbook, reportPath);
  return reportPath;
}

function printDetailTable(results) {
  const rows = detailRows(results).map((row) => ({
    "备注": row["备注"],
    "可售状态": row["可售状态"],
    "链接": row["链接"],
    "国家/站点": row["国家/站点"],
    "商品名称": row["商品名称"],
    "卖家核对": row["卖家核对"],
    "价格": row["价格"],
    "可用性/异常原因": row["可用性/异常原因"],
    ASIN: row.ASIN,
  }));
  console.table(rows);
}

function cleanupScreenshots(root, config) {
  const screenshotConfig = config.screenshots || {};
  if (screenshotConfig.cleanup_on_run === false) return { deleted: 0, remaining: 0 };
  const screenshotDir = path.join(root, "amazon_availability_monitor", "screenshots");
  if (!fs.existsSync(screenshotDir)) return { deleted: 0, remaining: 0 };

  const retentionDays = Number(screenshotConfig.retention_days || 14);
  const maxFiles = Number(screenshotConfig.max_files || 500);
  const now = Date.now();
  const maxAgeMs = Math.max(0, retentionDays) * 24 * 60 * 60 * 1000;
  let deleted = 0;

  const files = fs
    .readdirSync(screenshotDir)
    .filter((file) => /\.(png|jpe?g)$/i.test(file))
    .map((file) => {
      const fullPath = path.join(screenshotDir, file);
      const stat = fs.statSync(fullPath);
      return { file, fullPath, mtimeMs: stat.mtimeMs };
    });

  for (const item of files) {
    if (maxAgeMs > 0 && now - item.mtimeMs > maxAgeMs) {
      fs.rmSync(item.fullPath, { force: true });
      item.deleted = true;
      deleted += 1;
    }
  }

  const remaining = files
    .filter((item) => !item.deleted && fs.existsSync(item.fullPath))
    .sort((a, b) => a.mtimeMs - b.mtimeMs);
  if (maxFiles > 0 && remaining.length > maxFiles) {
    const overflow = remaining.length - maxFiles;
    for (const item of remaining.slice(0, overflow)) {
      fs.rmSync(item.fullPath, { force: true });
      deleted += 1;
    }
  }

  const finalCount = fs
    .readdirSync(screenshotDir)
    .filter((file) => /\.(png|jpe?g)$/i.test(file)).length;
  return { deleted, remaining: finalCount };
}

function readJsonFile(file) {
  const data = JSON.parse(fs.readFileSync(file, "utf8"));
  if (Array.isArray(data)) return { observations: data };
  return data;
}

function matchObservationToTarget(observation, targets) {
  const asin = String(observation.asin || "").trim().toUpperCase();
  const siteCode = String(observation.siteCode || observation.country || "").trim().toUpperCase();
  const target = targets.find((item) => item.asin === asin && item.siteCode === siteCode);
  if (!target) throw new Error(`Chrome result does not match configured target: ${asin || "(missing ASIN)"} ${siteCode || "(missing site)"}`);
  return target;
}

function writePreparePayload(root, config, targets, outputPath) {
  const payload = {
    generatedAt: new Date().toISOString(),
    workspaceRoot: root,
    configPath: configPath(root),
    excelPath: config.excel_path,
    attemptsPerTarget: Number(config.check_attempts_per_target || config.alert_after_consecutive_failures || 2),
    confirmationMode: config.confirmation_mode || "abnormal_only",
    maxParallelSiteGroups: Number(config.max_parallel_site_groups || 1),
    detectionStrategy: "codex_chrome_plugin",
    targets,
    siteGroups: groupTargetsBySite(targets),
    chromeResultSchema: {
      required: ["asin", "siteCode", "attempt", "finalUrl", "detectedAt"],
      recommended: [
        "status",
        "productTitle",
        "price",
        "detectedSeller",
        "detectedSellerId",
        "availabilityText",
        "addToCartVisible",
        "buyNowVisible",
        "unavailable",
        "accessBlocked",
        "bodyText",
        "screenshotPath",
        "reason",
      ],
    },
  };
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  return outputPath;
}

async function finalizeChromeResults(require, root, config, targets, resultFile) {
  const payload = readJsonFile(resultFile);
  const observations = payload.observations || payload.results || [];
  if (!Array.isArray(observations) || !observations.length) {
    throw new Error(`Chrome result file has no observations/results array: ${resultFile}`);
  }

  const results = observations.map((observation) => {
    const target = matchObservationToTarget(observation, targets);
    return normalizeChromeObservation(observation, target, config);
  });

  const cleanupBefore = cleanupScreenshots(root, config);
  if (cleanupBefore.deleted) {
    console.log(`[monitor] Screenshot cleanup before finalize: deleted=${cleanupBefore.deleted}, remaining=${cleanupBefore.remaining}`);
  }

  appendSnapshots(root, results);
  const alerts = updateStateAndAlerts(root, results, config);
  const summary = {
    checked: results.length,
    targets: targets.length,
    buyable: results.filter((row) => row.status === "BUYABLE").length,
    abnormal: results.filter((row) => row.status !== "BUYABLE" && row.status !== "ACCESS_BLOCKED").length,
    access_blocked: results.filter((row) => row.status === "ACCESS_BLOCKED").length,
    alerts: alerts.length,
  };
  const alertResult = await sendAlerts(alerts, config, require, summary);
  summary.alertResult = alertResult;
  const reportPath = writeExcelReport(require, root, results, summary);
  summary.reportPath = reportPath;

  const cleanupAfter = cleanupScreenshots(root, config);
  if (cleanupAfter.deleted) {
    console.log(`[monitor] Screenshot cleanup after finalize: deleted=${cleanupAfter.deleted}, remaining=${cleanupAfter.remaining}`);
  }

  printDetailTable(results);
  console.log(`[monitor] ${summaryHeadline(alerts, summary)}`);
  console.log(`[monitor] Excel report: ${reportPath}`);
  console.log(`[monitor] Summary ${JSON.stringify(summary)}`);
}

async function main() {
  const root = workspaceRoot();
  if (process.argv.includes("--test-product-name")) {
    const samples = process.argv.slice(process.argv.indexOf("--test-product-name") + 1);
    for (const sample of samples) console.log(`${sample} => ${extractProductNameZh(sample)}`);
    return;
  }

  const validateOnly = process.argv.includes("--validate-only");
  const prepareChromeRun = process.argv.includes("--prepare-chrome-run");
  const finalizeIndex = process.argv.indexOf("--finalize-chrome-results");
  const require = ensureRuntime(["xlsx", "yaml", "nodemailer"]);
  const config = loadConfig(require, root);
  const targets = loadTargets(require, config.excel_path);

  if (validateOnly) {
    const siteGroups = groupTargetsBySite(targets);
    console.log(
      `[monitor] Config valid. Loaded ${targets.length} target checks from ${config.excel_path}. Attempts per target: ${Number(config.check_attempts_per_target || config.alert_after_consecutive_failures || 2)}. Confirmation mode: ${config.confirmation_mode || "abnormal_only"}. Site groups: ${siteGroups.length}. Max parallel site groups: ${Number(config.max_parallel_site_groups || 1)}. Detection strategy: codex_chrome_plugin. Excel report: enabled.`,
    );
    for (const target of targets) {
      console.log(`[monitor] TARGET ${target.siteCode} ${target.asin} ${target.seller} sellerId=${target.sellerId || ""} ${target.url} strategy=codex_chrome_plugin`);
    }
    return;
  }

  if (prepareChromeRun) {
    const outputArgIndex = process.argv.indexOf("--output");
    const defaultPath = path.join(root, "amazon_availability_monitor", "data", "chrome_run_targets.json");
    const outputPath = outputArgIndex >= 0 && process.argv[outputArgIndex + 1]
      ? path.resolve(process.argv[outputArgIndex + 1])
      : defaultPath;
    writePreparePayload(root, config, targets, outputPath);
    console.log(`[monitor] Chrome run target payload: ${outputPath}`);
    console.log(`[monitor] Loaded ${targets.length} target checks. Use Chrome plugin to create observations, then run --finalize-chrome-results <results.json>.`);
    return;
  }

  if (finalizeIndex >= 0) {
    const resultFile = process.argv[finalizeIndex + 1];
    if (!resultFile) throw new Error("--finalize-chrome-results requires a JSON result file");
    await finalizeChromeResults(require, root, config, targets, path.resolve(resultFile));
    return;
  }

  throw new Error(
    "This skill uses the Codex Chrome plugin for page access. Run --prepare-chrome-run, collect Chrome observations with the plugin, then run --finalize-chrome-results <results.json>.",
  );
}

if (process.argv[1] && import.meta.url === new URL(process.argv[1], "file:").href) {
  main().catch((error) => {
    console.error(`[monitor] ${error.stack || error.message}`);
    process.exit(1);
  });
}
