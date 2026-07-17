#!/usr/bin/env node

export const UNREVIEWABLE_STATUSES = new Set([
  "CAPTCHA",
  "ACCESS_BLOCKED",
  "CONTINUE_SHOPPING",
  "PAGE_ERROR",
  "FETCH_FAILED",
  "NOT_FOUND",
]);

const UNAVAILABLE_TEXT = /(currently unavailable|temporarily out of stock|out of stock|not available|unavailable|indisponible|derzeit nicht verfügbar|non disponibile|no disponible|在庫切れ|現在お取り扱いできません)/i;
const RECOVERABLE_STATUSES = new Set(["CONTINUE_SHOPPING"]);

export function scoreListing(input = {}) {
  const task = input.task || {};
  const facts = input.facts || input || {};
  const baseStatus = normalizeStatus(input.status || facts.status || "OK");
  const collectedAt = input.extractedAt || facts.extractedAt || new Date().toISOString();
  const url = input.url || task.url || facts.url || "";
  const screenshotPath = input.screenshotPath || facts.screenshotPath || "";

  if (UNREVIEWABLE_STATUSES.has(baseStatus) && !canScoreRecoveredPage(baseStatus, facts)) {
    return unreviewableRow(task, url, baseStatus, collectedAt, screenshotPath, facts);
  }

  const title = clean(facts.title);
  const bullets = arrayish(facts.bullets);
  const imageCount = numberish(facts.imageCount ?? facts.imagesCount ?? (Array.isArray(facts.images) ? facts.images.length : 0));
  const hasAplus = Boolean(facts.hasAplus ?? facts.aplus ?? facts.enhancedContent);
  const description = clean(facts.description);
  const price = clean(facts.price);
  const rating = clean(facts.rating);
  const reviewCount = clean(facts.reviewCount ?? facts.reviewsCount);
  const category = clean(facts.category);
  const bsr = clean(facts.bsr);
  const availability = clean(facts.availability);
  const detectedSeller = clean(facts.seller || facts.soldBy || facts.buyBoxSeller);

  const good = [];
  const bad = [];
  const missing = [];
  const advice = [];
  let score = 0;

  const titleReview = reviewTitle(title);
  score += titleReview.points;
  pushReview(titleReview, good, bad, missing, advice);

  const bulletReview = reviewBullets(bullets);
  score += bulletReview.points;
  pushReview(bulletReview, good, bad, missing, advice);

  const imageReview = reviewImages(imageCount);
  score += imageReview.points;
  pushReview(imageReview, good, bad, missing, advice);

  const aplusReview = hasAplus
    ? reviewOk(10, "A+内容可见", "A+审查：已检测到 A+ / Enhanced Content 信号。")
    : reviewMissing(0, "缺少A+内容", "A+审查：未检测到 A+ / Enhanced Content 信号。", "补充 A+ 内容，用场景图、卖点模块和对比信息提升转化。");
  score += aplusReview.points;
  pushReview(aplusReview, good, bad, missing, advice);

  const descReview = description.length >= 80
    ? reviewOk(10, "描述较完整", "描述审查：Product Description 内容较完整。")
    : description
      ? reviewWeak(5, "描述偏短", "描述审查：Product Description 偏短。", "扩充描述，补充使用场景、材质、尺寸、护理和售后信息。")
      : reviewMissing(0, "缺少描述", "描述审查：未检测到 Product Description。", "补充 Product Description，避免只依赖五点描述。");
  score += descReview.points;
  pushReview(descReview, good, bad, missing, advice);

  const priceReview = price
    ? reviewOk(10, "价格可见", `价格审查：页面价格可见（${price}）。`)
    : reviewMissing(0, "缺少价格", "价格审查：未检测到可见价格。", "检查价格、库存、前台展示和配送设置。");
  score += priceReview.points;
  pushReview(priceReview, good, bad, missing, advice);

  const reviewReview = rating && reviewCount
    ? reviewOk(15, "评分和评论数可见", `评论审查：评分 ${rating}，评论数 ${reviewCount}。`)
    : rating || reviewCount
      ? reviewWeak(8, "评论信息不完整", `评论审查：评分/评论数只检测到部分信息（rating=${rating || "未抓取到"}，reviewCount=${reviewCount || "未抓取到"}）。`, "检查评论展示状态，并结合广告和促销提升评论积累。")
      : reviewMissing(0, "缺少评分和评论数", "评论审查：未检测到评分和评论数。", "若新品评论不足，建议规划 Vine、售后触达和站内外流量沉淀。");
  score += reviewReview.points;
  pushReview(reviewReview, good, bad, missing, advice);

  const seoSignals = [category, bsr].filter(Boolean).length;
  const seoReview = seoSignals >= 2
    ? reviewOk(10, "类目和排名信号可见", `SEO覆盖审查：类目/BSR 信号可见（${[category, bsr].filter(Boolean).join("；")}）。`)
    : seoSignals === 1
      ? reviewWeak(5, "SEO公开信号偏少", `SEO覆盖审查：仅检测到部分类目/BSR 信号（${category || bsr}）。`, "补充类目、属性词、核心关键词覆盖，并检查节点归类。")
      : reviewMissing(0, "缺少SEO公开信号", "SEO覆盖审查：未检测到类目或 BSR 信号。", "检查类目节点、搜索词和关键属性覆盖。");
  score += seoReview.points;
  pushReview(seoReview, good, bad, missing, advice);

  let status = "OK";
  if (availability && UNAVAILABLE_TEXT.test(availability)) {
    status = "UNAVAILABLE";
  } else if (sellerMismatch(task, detectedSeller)) {
    status = "SELLER_MISMATCH";
  } else if (score < 75) {
    status = "LOW_SCORE";
  } else if (missing.length > 0) {
    status = "MISSING_FIELDS";
  }

  const optimize = score < 90 || missing.length > 0 || ["UNAVAILABLE", "SELLER_MISMATCH"].includes(status);
  const issueSummary = buildIssueSummary({ status, bad, missing, availability, detectedSeller, task });
  const adviceSummary = buildAdviceSummary(advice, status);
  return {
    "备注": task.remark || "",
    "Listing完整度和质量评分": score,
    "Listing是否建议优化": optimize ? "是" : "否",
    "Listing优化优先级": priority(score, status),
    "主要问题/缺失": issueSummary,
    "核心优化建议": adviceSummary,
    "ASIN值": task.asin || facts.asin || "",
    "国家": task.site || facts.site || "",
    "站点URL": url,
    "页面状态": status,
    "店铺名称": task.storeName || "",
    "卖家ID": task.sellerId || "",
    "标题": titleReview.message,
    "五点": bulletReview.message,
    "图片": imageReview.message,
    "A+": aplusReview.message,
    "描述": descReview.message,
    "价格": priceReview.message,
    "评论": reviewReview.message,
    "SEO": seoReview.message,
    "卖家匹配": sellerReview(task, detectedSeller),
    "Listing好的地方": uniq(good).join("；"),
    "Listing不足的地方": uniq(bad).join("；"),
    "Listing缺失的部分": uniq(missing).join("；"),
    "Listing优化建议": adviceSummary,
    "标题审查": titleReview.message,
    "五点审查": bulletReview.message,
    "图片审查": imageReview.message,
    "A+审查": aplusReview.message,
    "描述审查": descReview.message,
    "价格审查": priceReview.message,
    "评论审查": reviewReview.message,
    "卖家匹配审查": sellerReview(task, detectedSeller),
    "数据来源": input.source || facts.source || "Chrome插件前台页面",
    "采集时间": collectedAt,
    "截图路径": screenshotPath,
  };
}

function canScoreRecoveredPage(status, facts) {
  if (!RECOVERABLE_STATUSES.has(status)) return false;

  const title = clean(facts.title);
  const bullets = arrayish(facts.bullets);
  const imageCount = numberish(facts.imageCount ?? facts.imagesCount ?? (Array.isArray(facts.images) ? facts.images.length : 0));
  const contentSignals = [
    title,
    bullets.length >= 3 ? "bullets" : "",
    imageCount > 0 ? "images" : "",
    clean(facts.description),
    clean(facts.category),
    clean(facts.bsr),
  ].filter(Boolean).length;

  // Amazon can briefly show a continue-shopping layer while the product DOM
  // remains readable. In that case, score the observed Listing facts.
  return Boolean(title) && bullets.length > 0 && imageCount > 0 && contentSignals >= 4;
}

function unreviewableRow(task, url, status, collectedAt, screenshotPath, facts) {
  const reason = clean(facts.error || facts.reason || facts.availability || status);
  return {
    "备注": task.remark || "",
    "Listing完整度和质量评分": "无法审查",
    "Listing是否建议优化": ["NOT_FOUND", "PAGE_ERROR", "FETCH_FAILED"].includes(status) ? "是" : "否",
    "Listing优化优先级": ["NOT_FOUND", "PAGE_ERROR", "FETCH_FAILED"].includes(status) ? "人工复核" : "暂不判定",
    "主要问题/缺失": reason || "页面无法正常审查",
    "核心优化建议": "先人工打开页面确认状态；访问受阻不代表 Listing 本身不完善。",
    "ASIN值": task.asin || facts.asin || "",
    "国家": task.site || facts.site || "",
    "站点URL": url,
    "页面状态": status,
    "店铺名称": task.storeName || "",
    "卖家ID": task.sellerId || "",
    "标题": "无法审查",
    "五点": "无法审查",
    "图片": "无法审查",
    "A+": "无法审查",
    "描述": "无法审查",
    "价格": "无法审查",
    "评论": "无法审查",
    "SEO": "无法审查",
    "卖家匹配": "无法审查",
    "Listing好的地方": "",
    "Listing不足的地方": reason || "页面无法正常审查",
    "Listing缺失的部分": "",
    "Listing优化建议": "先人工打开页面确认状态；访问受阻不代表 Listing 本身不完善。",
    "标题审查": "无法审查",
    "五点审查": "无法审查",
    "图片审查": "无法审查",
    "A+审查": "无法审查",
    "描述审查": "无法审查",
    "价格审查": "无法审查",
    "评论审查": "无法审查",
    "卖家匹配审查": "无法审查",
    "数据来源": facts.source || "Chrome插件前台页面",
    "采集时间": collectedAt,
    "截图路径": screenshotPath,
  };
}

function buildIssueSummary({ status, bad, missing, availability, detectedSeller, task }) {
  const issues = [];
  if (["UNAVAILABLE"].includes(status)) issues.push(availability || "页面显示不可售/不可购买");
  if (["SELLER_MISMATCH"].includes(status)) issues.push(`卖家可能不匹配：期望 ${task.sellerId || task.storeName || "未配置"}，检测到 ${detectedSeller || "未抓取到"}`);
  issues.push(...missing, ...bad);
  return uniq(issues).join("；") || "暂无明显问题";
}

function buildAdviceSummary(advice, status) {
  const items = uniq(advice);
  if (status === "UNAVAILABLE") items.unshift("优先检查库存、价格、配送和前台购买入口。");
  if (status === "SELLER_MISMATCH") items.unshift("优先核对卖家 ID、店铺名称、Buy Box 和 offer 归属。");
  return uniq(items).join("；") || "保持当前 Listing 质量，定期复查。";
}

function reviewTitle(title) {
  if (!title) return reviewMissing(0, "缺少标题", "标题审查：未检测到标题。", "补充清晰标题，覆盖品牌、核心词、关键卖点和规格。");
  if (title.length >= 80 && title.length <= 200) return reviewOk(15, "标题长度较合理", `标题审查：标题长度 ${title.length}，信息较完整。`);
  if (title.length < 80) return reviewWeak(8, "标题偏短", `标题审查：标题长度 ${title.length}，可能关键词和卖点覆盖不足。`, "扩充标题中的核心关键词、适用对象和关键规格。");
  return reviewWeak(10, "标题偏长", `标题审查：标题长度 ${title.length}，可能影响移动端可读性。`, "精简标题，保留品牌、核心词和最关键规格。");
}

function reviewBullets(bullets) {
  if (!bullets.length) return reviewMissing(0, "缺少五点描述", "五点审查：未检测到 Bullet Points。", "补齐 5 条五点描述，覆盖核心卖点、场景、材质、尺寸和售后。");
  if (bullets.length >= 5) return reviewOk(15, "五点描述数量完整", `五点审查：检测到 ${bullets.length} 条五点描述。`);
  return reviewWeak(Math.min(12, bullets.length * 3), "五点描述不足", `五点审查：仅检测到 ${bullets.length} 条五点描述。`, "补齐五点描述，避免卖点覆盖不足。");
}

function reviewImages(imageCount) {
  if (!imageCount) return reviewMissing(0, "缺少图片", "图片审查：未检测到商品图片。", "检查图片上传与前台展示，至少保证主图和多张场景/尺寸/卖点图。");
  if (imageCount >= 7) return reviewOk(15, "图片数量较完整", `图片审查：检测到 ${imageCount} 张图片。`);
  if (imageCount >= 4) return reviewWeak(10, "图片数量一般", `图片审查：检测到 ${imageCount} 张图片。`, "补充场景图、尺寸图、卖点图和细节图。");
  return reviewWeak(5, "图片数量偏少", `图片审查：仅检测到 ${imageCount} 张图片。`, "优先补充主图外的场景、规格和卖点图片。");
}

function reviewOk(points, good, message) {
  return { points, good, message };
}

function reviewWeak(points, bad, message, advice) {
  return { points, bad, message, advice };
}

function reviewMissing(points, missing, message, advice) {
  return { points, missing, message, advice };
}

function pushReview(review, good, bad, missing, advice) {
  if (review.good) good.push(review.good);
  if (review.bad) bad.push(review.bad);
  if (review.missing) missing.push(review.missing);
  if (review.advice) advice.push(review.advice);
}

function sellerMismatch(task, detectedSeller) {
  if (!detectedSeller) return false;
  if (task.sellerId && detectedSeller.includes(task.sellerId)) return false;
  if (task.storeName && normalize(detectedSeller).includes(normalize(task.storeName))) return false;
  return Boolean(task.sellerId || task.storeName);
}

function sellerReview(task, detectedSeller) {
  if (!task.sellerId && !task.storeName) return detectedSeller ? `检测到卖家：${detectedSeller}` : "未配置卖家校验条件";
  if (!detectedSeller) return "未检测到 Sold by / seller 信息，需人工复核";
  return sellerMismatch(task, detectedSeller)
    ? `卖家可能不匹配：期望 ${task.sellerId || task.storeName}，检测到 ${detectedSeller}`
    : `卖家匹配：${detectedSeller}`;
}

function priority(score, status) {
  if (["UNAVAILABLE", "SELLER_MISMATCH"].includes(status)) return "优先处理";
  if (score === "无法审查") return "人工复核";
  if (score >= 90) return "低优先级优化";
  if (score >= 75) return "中优先级优化";
  if (score >= 60) return "高优先级优化";
  return "优先处理";
}

function normalizeStatus(status) {
  return String(status || "OK").trim().toUpperCase();
}

function normalize(value) {
  return clean(value).toLowerCase().replace(/\s+/g, "");
}

function clean(value) {
  return String(value ?? "").replace(/\s+/g, " ").trim();
}

function arrayish(value) {
  if (Array.isArray(value)) return value.map(clean).filter(Boolean);
  if (!value) return [];
  return String(value).split(/\n|;;|\|\|/).map(clean).filter(Boolean);
}

function numberish(value) {
  const number = Number(String(value ?? "").replace(/[^\d.]/g, ""));
  return Number.isFinite(number) ? number : 0;
}

function uniq(values) {
  return [...new Set(values.filter(Boolean))];
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const input = JSON.parse(await readStdin());
  process.stdout.write(`${JSON.stringify(scoreListing(input), null, 2)}\n`);
}

function readStdin() {
  return new Promise((resolve) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => (data += chunk));
    process.stdin.on("end", () => resolve(data || "{}"));
  });
}
