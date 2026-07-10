#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { ensureRuntime, workspaceRoot } from "./setup_runtime.mjs";
import { sendAlerts } from "./send_alerts.mjs";

const SHEET_NAME = "ASIN监控清单";
const HEADERS = {
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

const DEFAULT_DELIVERY_LOCATIONS = {
  US: { postal_code: "10001" },
  CA: { postal_code: "M5V 2T6" },
  MX: { postal_code: "06700" },
  UK: { postal_code: "SW1A 1AA" },
  DE: { postal_code: "10115" },
  FR: { postal_code: "75001" },
  IT: { postal_code: "00118" },
  ES: { postal_code: "28001" },
  NL: { postal_code: "1012" },
  SE: { postal_code: "111 22" },
  PL: { postal_code: "00-001" },
  BE: { postal_code: "1000" },
  JP: { postal_code: "100-0001" },
  AU: { postal_code: "2000" },
  IN: { postal_code: "110001" },
  SG: { postal_code: "018956" },
  AE: { postal_code: "00000" },
  SA: { postal_code: "12211" },
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

const MARKETPLACE_LOCALES = {
  US: { locale: "en-US", acceptLanguage: "en-US,en;q=0.9", timezoneId: "America/New_York" },
  CA: { locale: "en-CA", acceptLanguage: "en-CA,en;q=0.9,fr-CA;q=0.8", timezoneId: "America/Toronto" },
  MX: { locale: "es-MX", acceptLanguage: "es-MX,es;q=0.9,en;q=0.8", timezoneId: "America/Mexico_City" },
  UK: { locale: "en-GB", acceptLanguage: "en-GB,en;q=0.9", timezoneId: "Europe/London" },
  DE: { locale: "de-DE", acceptLanguage: "de-DE,de;q=0.9,en;q=0.8", timezoneId: "Europe/Berlin" },
  FR: { locale: "fr-FR", acceptLanguage: "fr-FR,fr;q=0.9,en;q=0.8", timezoneId: "Europe/Paris" },
  IT: { locale: "it-IT", acceptLanguage: "it-IT,it;q=0.9,en;q=0.8", timezoneId: "Europe/Rome" },
  ES: { locale: "es-ES", acceptLanguage: "es-ES,es;q=0.9,en;q=0.8", timezoneId: "Europe/Madrid" },
  NL: { locale: "nl-NL", acceptLanguage: "nl-NL,nl;q=0.9,en;q=0.8", timezoneId: "Europe/Amsterdam" },
  SE: { locale: "sv-SE", acceptLanguage: "sv-SE,sv;q=0.9,en;q=0.8", timezoneId: "Europe/Stockholm" },
  PL: { locale: "pl-PL", acceptLanguage: "pl-PL,pl;q=0.9,en;q=0.8", timezoneId: "Europe/Warsaw" },
  BE: { locale: "nl-BE", acceptLanguage: "nl-BE,nl;q=0.9,fr-BE;q=0.8,en;q=0.7", timezoneId: "Europe/Brussels" },
  JP: { locale: "ja-JP", acceptLanguage: "ja-JP,ja;q=0.9,en;q=0.8", timezoneId: "Asia/Tokyo" },
  AU: { locale: "en-AU", acceptLanguage: "en-AU,en;q=0.9", timezoneId: "Australia/Sydney" },
  IN: { locale: "en-IN", acceptLanguage: "en-IN,en;q=0.9,hi;q=0.8", timezoneId: "Asia/Kolkata" },
  SG: { locale: "en-SG", acceptLanguage: "en-SG,en;q=0.9", timezoneId: "Asia/Singapore" },
  AE: { locale: "en-AE", acceptLanguage: "en-AE,en;q=0.9,ar;q=0.8", timezoneId: "Asia/Dubai" },
  SA: { locale: "ar-SA", acceptLanguage: "ar-SA,ar;q=0.9,en;q=0.8", timezoneId: "Asia/Riyadh" },
};

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
  for (const [index, row] of rows.entries()) {
    const seller = String(row[HEADERS.seller] || "").trim();
    const asin = String(row[HEADERS.asin] || "").trim().toUpperCase();
    const sellerId = normalizeSellerId(row[HEADERS.sellerId]);
    const sites = splitSites(row[HEADERS.sites]);
    if (!seller && !asin && !sites.length) continue;
    if (!seller || !asin || !sites.length) {
      throw new Error(`Row ${index + 2} is missing required fields.`);
    }
    for (const siteCode of sites) {
      const domain = SITE_MAP[siteCode];
      if (!domain) {
        throw new Error(`Row ${index + 2} has unsupported site code: ${siteCode}`);
      }
      targets.push({
        seller,
        sellerId,
        asin,
        siteCode,
        domain,
        url: buildProductUrl({ domain, asin, sellerId }),
      });
    }
  }
  return targets;
}

async function textFromLocator(locator) {
  try {
    const count = await locator.count();
    for (let i = 0; i < count; i += 1) {
      const text = (await locator.nth(i).innerText({ timeout: 1000 })).trim();
      if (text) return text;
    }
  } catch {
    return "";
  }
  return "";
}

async function isVisible(locator) {
  try {
    return await locator.first().isVisible({ timeout: 1500 });
  } catch {
    return false;
  }
}

async function clickFirstVisible(page, selectors, timeout = 1500) {
  for (const selector of selectors) {
    const locator = page.locator(selector).first();
    if (await isVisible(locator)) {
      await locator.click({ timeout });
      return selector;
    }
  }
  return "";
}

async function fillFirstVisible(page, selectors, value, timeout = 1500) {
  for (const selector of selectors) {
    const locator = page.locator(selector).first();
    if (await isVisible(locator)) {
      await locator.fill(value, { timeout });
      return selector;
    }
  }
  return "";
}

async function pressDoneIfVisible(page) {
  await clickFirstVisible(page, [
    "#GLUXConfirmClose",
    "button[name='glowDoneButton']",
    "input[name='glowDoneButton']",
    ".a-popover-footer #GLUXConfirmClose",
    ".a-button-input[aria-labelledby='GLUXConfirmClose-announce']",
  ]).catch(() => "");
}

async function applyDeliveryLocation(page, target, config) {
  const strategy = config.delivery_strategy || "postal_code_best_effort";
  if (strategy === "marketplace_default") {
    return {
      strategy,
      attempted: false,
      required: false,
      applied: false,
      skipped: true,
      siteCode: target.siteCode,
      postalCode: "",
      warning: false,
      reason: "Using marketplace default local access; postal code delivery change skipped.",
    };
  }

  const timeout = Number(config.browser?.timeout_ms || 45000);
  const configured = config.delivery_locations?.[target.siteCode] || {};
  const fallback = DEFAULT_DELIVERY_LOCATIONS[target.siteCode] || {};
  const location = { ...fallback, ...configured };
  const required = strategy === "postal_code_required" || config.delivery_location_required === true;
  const result = {
    strategy,
    attempted: true,
    required,
    applied: false,
    siteCode: target.siteCode,
    postalCode: location.postal_code || "",
    warning: false,
    reason: "",
  };

  if (!location.postal_code) {
    result.reason = `No postal_code configured for ${target.siteCode}`;
    result.warning = !required;
    return result;
  }

  try {
    const homeUrl = `https://www.${target.domain}/`;
    const response = await page.goto(homeUrl, { waitUntil: "domcontentloaded", timeout });
    await page.waitForTimeout(1500);
    const bodyText = await page.locator("body").innerText({ timeout: 4000 }).catch(() => "");
    if (!response || response.status() >= 400) {
      result.reason = `Delivery home page HTTP status ${response?.status() || "unknown"}`;
      result.warning = !required;
      return result;
    }
    if (/captcha|enter the characters|not a robot|robot check|type the characters/iu.test(bodyText)) {
      result.reason = "Amazon bot or captcha page detected before setting delivery location";
      result.botBlocked = true;
      result.warning = !required;
      return result;
    }

    const openedBy = await clickFirstVisible(page, [
      "#nav-global-location-popover-link",
      "#glow-ingress-block",
      "#nav-packard-glow-loc-icon",
      "[data-action='GLUXModalTrigger']",
    ]);
    if (!openedBy) {
      result.reason = "Could not open Amazon delivery location dialog";
      result.warning = !required;
      return result;
    }

    await page.waitForTimeout(1500);
    const filledBy = await fillFirstVisible(
      page,
      [
        "#GLUXZipUpdateInput",
        "input[name='zipCode']",
        "input[aria-label*='Postal']",
        "input[aria-label*='ZIP']",
        "input[placeholder*='postal']",
        "input[placeholder*='ZIP']",
      ],
      String(location.postal_code),
    );
    if (!filledBy) {
      result.reason = "Could not find postal code input in Amazon delivery location dialog";
      result.warning = !required;
      return result;
    }

    await clickFirstVisible(page, [
      "#GLUXZipUpdate input[type='submit']",
      "input[aria-labelledby='GLUXZipUpdate-announce']",
      "span#GLUXZipUpdate input",
      "input.a-button-input[type='submit']",
    ]);
    await page.waitForTimeout(2500);
    await pressDoneIfVisible(page);
    await page.waitForTimeout(1500);

    const locationText = await textFromLocator(page.locator("#glow-ingress-line2, #nav-global-location-slot, #glow-ingress-block"));
    const normalizedLocation = locationText.replace(/\s+/g, "").toLowerCase();
    const normalizedPostal = String(location.postal_code).replace(/\s+/g, "").toLowerCase();
    result.applied = Boolean(locationText) && normalizedLocation.includes(normalizedPostal.slice(0, Math.min(5, normalizedPostal.length)));
    result.reason = result.applied
      ? `Delivery location set to ${location.postal_code}`
      : `Delivery location text did not confirm postal code: ${locationText}`;
    result.warning = !result.applied && !required;
    result.locationText = locationText;
    return result;
  } catch (error) {
    result.reason = error.message;
    result.warning = !required;
    return result;
  }
}

async function detectSellerId(page) {
  const candidates = [];
  candidates.push(page.url());
  const inputSelectors = [
    "input[name='merchantID']",
    "input[name='merchant']",
    "input[name='seller']",
    "input[name='smid']",
  ];
  for (const selector of inputSelectors) {
    try {
      const value = await page.locator(selector).first().inputValue({ timeout: 500 });
      if (value) candidates.push(value);
    } catch {
      // Ignore absent fields.
    }
  }
  try {
    const hrefs = await page
      .locator("a[href*='seller='], a[href*='merchant='], a[href*='me='], a[href*='smid=']")
      .evaluateAll((links) => links.map((link) => link.href).filter(Boolean));
    candidates.push(...hrefs);
  } catch {
    // Ignore missing seller links.
  }

  for (const candidate of candidates) {
    const text = String(candidate);
    const patterns = [
      /[?&]m=([A-Z0-9]+)/i,
      /[?&]me=([A-Z0-9]+)/i,
      /[?&]merchant=([A-Z0-9]+)/i,
      /[?&]merchantID=([A-Z0-9]+)/i,
      /[?&]seller=([A-Z0-9]+)/i,
      /[?&]smid=([A-Z0-9]+)/i,
    ];
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match?.[1]) return normalizeSellerId(match[1]);
    }
  }
  return "";
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

function pageUrlSellerId(url) {
  try {
    return normalizeSellerId(new URL(url).searchParams.get("m") || "");
  } catch {
    return "";
  }
}

async function captureResultScreenshot(page, result, target, root, config) {
  const shouldScreenshot = result.status !== "BUYABLE" || config.browser?.screenshot_on_success;
  if (!shouldScreenshot) return;
  const screenshotDir = path.join(root, "amazon_availability_monitor", "screenshots");
  fs.mkdirSync(screenshotDir, { recursive: true });
  const safeTime = result.detectedAt.replace(/[:.]/g, "-");
  const screenshotConfig = config.screenshots || {};
  const format = screenshotConfig.format === "png" ? "png" : "jpeg";
  const extension = format === "png" ? "png" : "jpg";
  const screenshotPath = path.join(screenshotDir, `${target.asin}_${target.siteCode}_attempt-${result.attempt || "x"}_${safeTime}.${extension}`);
  const options = {
    path: screenshotPath,
    type: format,
    fullPage: screenshotConfig.full_page === true,
  };
  if (format === "jpeg") options.quality = Number(screenshotConfig.quality || 65);
  await page.screenshot(options).catch(() => {});
  if (fs.existsSync(screenshotPath)) result.screenshotPath = screenshotPath;
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

async function checkTarget(page, target, config, root) {
  const detectedAt = new Date().toISOString();
  const timeout = Number(config.browser?.timeout_ms || 45000);
  const result = {
    ...target,
    status: "PAGE_ERROR",
    detectedAt,
    price: "",
    detectedSeller: "",
    availabilityText: "",
    title: "",
    screenshotPath: "",
    reason: "",
    deliveryLocation: null,
    detectionStrategy: config.delivery_strategy || "postal_code_best_effort",
    detectedSellerId: "",
    sellerMatchMethod: "",
    finalUrl: "",
    productTitle: "",
    productNameZh: "",
  };

  try {
    const deliveryLocation = target.deliveryLocationOverride || await applyDeliveryLocation(page, target, config);
    result.deliveryLocation = deliveryLocation;
    if (deliveryLocation.required && deliveryLocation.botBlocked) {
      result.status = "BOT_BLOCKED";
      result.reason = deliveryLocation.reason;
      await captureResultScreenshot(page, result, target, root, config);
      return result;
    }
    if (deliveryLocation.required && !deliveryLocation.applied) {
      result.status = "PAGE_ERROR";
      result.reason = `Delivery location could not be set for ${target.siteCode}: ${deliveryLocation.reason}`;
      await captureResultScreenshot(page, result, target, root, config);
      return result;
    }

    const response = await page.goto(target.url, { waitUntil: "domcontentloaded", timeout });
    await page.waitForTimeout(2500);
    result.title = await page.title();
    result.finalUrl = page.url();
    const bodyText = await page.locator("body").innerText({ timeout: 5000 }).catch(() => "");
    if (!response || response.status() >= 400) {
      result.reason = `HTTP status ${response?.status() || "unknown"}`;
    } else if (/captcha|enter the characters|not a robot|robot check|type the characters/iu.test(bodyText)) {
      result.status = "BOT_BLOCKED";
      result.reason = "Amazon bot or captcha page detected";
    } else if (/looking for something|page not found|sorry.*couldn't find that page/iu.test(bodyText)) {
      result.status = "PAGE_ERROR";
      result.reason = "Amazon page error text detected";
    } else {
      const addToCartVisible = await isVisible(page.locator("#add-to-cart-button, input[name='submit.add-to-cart']"));
      const buyNowVisible = await isVisible(page.locator("#buy-now-button, input[name='submit.buy-now']"));
      const productTitle = (await textFromLocator(page.locator("#productTitle"))) || result.title;
      const availabilityText = await textFromLocator(page.locator("#availability, #outOfStock, #availabilityInsideBuyBox_feature_div"));
      const sellerText =
        (await textFromLocator(page.locator("#sellerProfileTriggerId"))) ||
        (await textFromLocator(page.locator("#merchant-info"))) ||
        (await textFromLocator(page.locator("#tabular-buybox, #desktop_qualifiedBuyBox")));
      const priceText =
        (await textFromLocator(page.locator(".a-price .a-offscreen"))) ||
        (await textFromLocator(page.locator("#priceblock_ourprice, #priceblock_dealprice, #corePrice_feature_div")));

      result.productTitle = productTitle;
      result.productNameZh = extractProductNameZh(productTitle);
      result.availabilityText = availabilityText;
      result.detectedSeller = sellerText;
      result.detectedSellerId = await detectSellerId(page);
      result.price = priceText;

      const unavailable = /currently unavailable|out of stock|temporarily out of stock|unavailable|nicht verfügbar|indisponible|non disponibile|no disponible|在庫切れ/iu.test(
        `${availabilityText}\n${bodyText}`,
      );
      if (!addToCartVisible || unavailable) {
        result.status = "UNAVAILABLE";
        result.reason = `addToCart=${addToCartVisible}, buyNow=${buyNowVisible}, unavailableText=${unavailable}`;
      } else {
        const sellerMatch = sellerMatches(result, target);
        result.sellerMatchMethod = sellerMatch.method;
        if (!sellerMatch.matched) {
        result.status = "SELLER_MISMATCH";
          result.reason = target.sellerId
            ? "Seller ID or Sold by seller does not match expected store"
            : "Sold by seller does not match expected store";
      } else {
        result.status = "BUYABLE";
          result.reason = `Product page is buyable and seller matches by ${sellerMatch.method}`;
        }
      }
    }
  } catch (error) {
    result.status = "PAGE_ERROR";
    result.reason = error.message;
  }

  await captureResultScreenshot(page, result, target, root, config);

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
    const abnormalAttempts = attempts.filter((result) => result.status !== "BUYABLE");
    const abnormal = abnormalAttempts.length === attempts.length;
    const consecutiveFailures = abnormal ? abnormalAttempts.length : 0;
    const statusSeries = attempts.map((result) => result.status).join(">");
    const alertKey = `${statusSeries}|${lastResult.detectedSeller || ""}|${lastResult.reason || ""}`;
    const shouldAlert = abnormal && consecutiveFailures >= threshold;
    const alertResult = {
      ...lastResult,
      attempts: attempts.length,
      abnormalAttempts: abnormalAttempts.length,
      attemptStatuses: attempts.map((result) => result.status),
      firstDetectedAt: attempts[0]?.detectedAt,
    };
    state[key] = {
      asin: lastResult.asin,
      siteCode: lastResult.siteCode,
      domain: lastResult.domain,
      status: lastResult.status,
      consecutiveFailures,
      attempts: attempts.length,
      lastCheckedAt: lastResult.detectedAt,
      lastAlertKey: shouldAlert ? alertKey : abnormal ? previous.lastAlertKey : "",
    };
    if (shouldAlert) alerts.push(alertResult);
  }
  saveState(root, state);
  return alerts;
}

function groupTargetsBySite(targets) {
  const groups = new Map();
  for (const target of targets) {
    if (!groups.has(target.siteCode)) groups.set(target.siteCode, []);
    groups.get(target.siteCode).push(target);
  }
  return Array.from(groups.entries()).map(([siteCode, siteTargets]) => ({ siteCode, targets: siteTargets }));
}

async function runWithConcurrency(items, limit, worker) {
  const results = [];
  let nextIndex = 0;
  const workerCount = Math.max(1, Math.min(Number(limit || 1), items.length || 1));
  await Promise.all(
    Array.from({ length: workerCount }, async () => {
      while (nextIndex < items.length) {
        const index = nextIndex;
        nextIndex += 1;
        results[index] = await worker(items[index], index);
      }
    }),
  );
  return results.flat();
}

async function createMarketplaceContext(browser, siteCode) {
  const localeConfig = MARKETPLACE_LOCALES[siteCode] || MARKETPLACE_LOCALES.US;
  return browser.newContext({
    locale: localeConfig.locale,
    timezoneId: localeConfig.timezoneId,
    viewport: { width: 1366, height: 900 },
    extraHTTPHeaders: {
      "Accept-Language": localeConfig.acceptLanguage,
    },
    userAgent:
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
  });
}

async function detectTargetAttempt(context, target, config, root, attempt, deliveryLocationOverride) {
  const page = await context.newPage();
  const result = await checkTarget(page, { ...target, attempt, deliveryLocationOverride }, config, root);
  result.attempt = attempt;
  await page.close().catch(() => {});
  return result;
}

async function runSiteGroup(browser, siteGroup, config, root) {
  const context = await createMarketplaceContext(browser, siteGroup.siteCode);
  const results = [];
  const attemptsPerTarget = Math.max(1, Number(config.check_attempts_per_target || config.alert_after_consecutive_failures || 2));
  const confirmationMode = config.confirmation_mode || "abnormal_only";
  const reuseDelivery = config.reuse_delivery_location_per_site !== false;

  try {
    let deliveryLocationOverride = null;
    if (reuseDelivery) {
      const page = await context.newPage();
      deliveryLocationOverride = await applyDeliveryLocation(page, siteGroup.targets[0], config);
      await page.close().catch(() => {});
    }

    for (const target of siteGroup.targets) {
      const first = await detectTargetAttempt(context, target, config, root, 1, deliveryLocationOverride);
      first.attemptsPlanned = attemptsPerTarget;
      results.push(first);
      console.log(`[monitor] ${first.status} attempt=1/${attemptsPerTarget} ${target.siteCode} ${target.asin} ${target.url}`);

      const shouldConfirm =
        attemptsPerTarget > 1 &&
        (confirmationMode !== "abnormal_only" || first.status !== "BUYABLE");
      if (shouldConfirm) {
        for (let attempt = 2; attempt <= attemptsPerTarget; attempt += 1) {
          const next = await detectTargetAttempt(context, target, config, root, attempt, deliveryLocationOverride);
          next.attemptsPlanned = attemptsPerTarget;
          results.push(next);
          console.log(`[monitor] ${next.status} attempt=${attempt}/${attemptsPerTarget} ${target.siteCode} ${target.asin} ${target.url}`);
        }
      }
    }
  } finally {
    await context.close().catch(() => {});
  }

  return results;
}

async function main() {
  const root = workspaceRoot();
  if (process.argv.includes("--test-product-name")) {
    const samples = process.argv.slice(process.argv.indexOf("--test-product-name") + 1);
    for (const sample of samples) console.log(`${sample} => ${extractProductNameZh(sample)}`);
    return;
  }
  const validateOnly = process.argv.includes("--validate-only");
  const require = ensureRuntime(validateOnly ? ["xlsx", "yaml"] : undefined);
  const config = loadConfig(require, root);
  const targets = loadTargets(require, config.excel_path);
  if (validateOnly) {
    const siteGroups = groupTargetsBySite(targets);
    console.log(
      `[monitor] Config valid. Loaded ${targets.length} target checks from ${config.excel_path}. Attempts per target: ${Number(config.check_attempts_per_target || config.alert_after_consecutive_failures || 2)}. Confirmation mode: ${config.confirmation_mode || "abnormal_only"}. Site groups: ${siteGroups.length}. Max parallel site groups: ${Number(config.max_parallel_site_groups || 2)}. Screenshots: ${config.screenshots?.format || "jpeg"} q=${Number(config.screenshots?.quality || 65)} retention=${Number(config.screenshots?.retention_days || 14)}d max=${Number(config.screenshots?.max_files || 500)}`,
    );
    for (const target of targets) {
      const delivery = config.delivery_locations?.[target.siteCode] || DEFAULT_DELIVERY_LOCATIONS[target.siteCode] || {};
      console.log(`[monitor] TARGET ${target.siteCode} ${target.asin} ${target.seller} sellerId=${target.sellerId || ""} ${target.url} strategy=${config.delivery_strategy || "postal_code_best_effort"} delivery=${delivery.postal_code || ""}`);
    }
    return;
  }
  if (!targets.length) {
    console.log("[monitor] No enabled ASIN targets found.");
    return;
  }

  const cleanupBefore = cleanupScreenshots(root, config);
  if (cleanupBefore.deleted) {
    console.log(`[monitor] Screenshot cleanup before run: deleted=${cleanupBefore.deleted}, remaining=${cleanupBefore.remaining}`);
  }

  const { chromium } = require("playwright");
  let browser;
  try {
    const launchOptions = { headless: config.browser?.headless !== false };
    if (config.browser?.channel !== "") {
      launchOptions.channel = config.browser?.channel || "chrome";
    }
    browser = await chromium.launch(launchOptions);
  } catch (error) {
    throw new Error(
      `Unable to launch system Chrome with Playwright: ${error.message}. Install Google Chrome or run "node /Users/apple/Documents/Listing优化建议/.amazon_availability_monitor_runtime/node_modules/playwright/cli.js install chromium" and set browser.channel to "" in config.yaml.`,
    );
  }
  const results = [];
  try {
    const siteGroups = groupTargetsBySite(targets);
    const groupResults = await runWithConcurrency(
      siteGroups,
      Number(config.max_parallel_site_groups || 2),
      (siteGroup) => runSiteGroup(browser, siteGroup, config, root),
    );
    results.push(...groupResults);
  } finally {
    await browser.close().catch(() => {});
  }

  appendSnapshots(root, results);
  const alerts = updateStateAndAlerts(root, results, config);
  const alertResult = await sendAlerts(alerts, config, require);
  const cleanupAfter = cleanupScreenshots(root, config);
  if (cleanupAfter.deleted) {
    console.log(`[monitor] Screenshot cleanup after run: deleted=${cleanupAfter.deleted}, remaining=${cleanupAfter.remaining}`);
  }

  const summary = {
    checked: results.length,
    targets: targets.length,
    buyable: results.filter((row) => row.status === "BUYABLE").length,
    abnormal: results.filter((row) => row.status !== "BUYABLE").length,
    alerts: alerts.length,
    alertResult,
  };
  console.log(`[monitor] Summary ${JSON.stringify(summary)}`);
}

main().catch((error) => {
  console.error(`[monitor] ${error.stack || error.message}`);
  process.exit(1);
});
