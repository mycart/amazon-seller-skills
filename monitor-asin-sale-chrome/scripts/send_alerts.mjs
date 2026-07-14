#!/usr/bin/env node
import crypto from "node:crypto";

function isConfigured(value) {
  return value && !String(value).includes("example.com") && !String(value).includes("REPLACE_ME");
}

function countBy(alerts, getKey) {
  const counts = new Map();
  for (const alert of alerts) {
    const key = getKey(alert) || "未知";
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])));
}

function formatCounts(entries) {
  if (!entries.length) return "无";
  return entries.map(([key, count]) => `${key}: ${count}`).join("；");
}

function formatReceipt(alertResult) {
  if (!alertResult) return "email=pending、feishu=pending";
  return `email=${alertResult.email || "skipped"}、feishu=${alertResult.feishu || "skipped"}`;
}

function statusSeries(alert) {
  return alert.attemptStatuses?.length ? alert.attemptStatuses.join(" -> ") : alert.status || "UNKNOWN";
}

function compactSiteStatusLines(alerts) {
  const asinGroups = new Map();
  for (const alert of alerts) {
    if (!asinGroups.has(alert.asin)) asinGroups.set(alert.asin, []);
    asinGroups.get(alert.asin).push(alert);
  }

  return [...asinGroups.entries()]
    .sort((a, b) => String(a[0]).localeCompare(String(b[0])))
    .map(([asin, asinAlerts]) => {
      const seriesGroups = new Map();
      for (const alert of asinAlerts) {
        const series = statusSeries(alert);
        if (!seriesGroups.has(series)) seriesGroups.set(series, []);
        seriesGroups.get(series).push(alert.siteCode || "未知站点");
      }
      const parts = [...seriesGroups.entries()]
        .sort((a, b) => String(a[1][0]).localeCompare(String(b[1][0])))
        .map(([series, sites]) => `${sites.join("/") } 为 ${series}`);
      return `${asin}：${parts.join("；")}`;
    });
}

function buildRunSummary(alerts, runSummary = {}) {
  const checked = Number.isFinite(runSummary.checked) ? runSummary.checked : alerts.length;
  const targets = Number.isFinite(runSummary.targets) ? runSummary.targets : alerts.length;
  const buyable = Number.isFinite(runSummary.buyable) ? runSummary.buyable : 0;
  const abnormal = Number.isFinite(runSummary.abnormal) ? runSummary.abnormal : alerts.length;
  return {
    targets,
    checked,
    buyable,
    abnormal,
    access_blocked: Number.isFinite(runSummary.access_blocked) ? runSummary.access_blocked : 0,
    alerts: Number.isFinite(runSummary.alerts) ? runSummary.alerts : alerts.length,
    alertResult: runSummary.alertResult,
  };
}

function summaryHeadline(alerts, runSummary = {}) {
  const summary = buildRunSummary(alerts, runSummary);
  const notifyText = summary.alerts
    ? `通知已聚合为同一条消息发送，回执是 ${formatReceipt(summary.alertResult)}。`
    : `无确认后异常，无需发送通知，回执是 ${formatReceipt(summary.alertResult)}。`;
  return `结果汇总：targets=${summary.targets}，checked=${summary.checked}，buyable=${summary.buyable}，abnormal=${summary.abnormal}，access_blocked=${summary.access_blocked}，确认后异常 alerts=${summary.alerts}。${notifyText}`;
}

function alertSummaryText(alerts, runSummary = {}) {
  const statusCounts = countBy(alerts, (alert) => alert.status);
  const siteCounts = countBy(alerts, (alert) => alert.siteCode);
  const sellerCounts = countBy(alerts, (alert) => alert.seller || alert.expectedSeller);
  const screenshotCount = alerts.filter((alert) => alert.screenshotPath).length;
  const generatedAt = new Date().toISOString();
  const asinLines = compactSiteStatusLines(alerts);

  return [
    summaryHeadline(alerts, runSummary),
    asinLines.length ? `异常集中在 ${asinLines.length} 个 ASIN：` : "异常集中在 0 个 ASIN：",
    ...asinLines,
    `异常状态分布：${formatCounts(statusCounts)}`,
    `异常站点分布：${formatCounts(siteCounts)}`,
    `异常店铺分布：${formatCounts(sellerCounts)}`,
    `已生成异常截图：${screenshotCount}`,
    `报告生成时间：${generatedAt}`,
    "",
    "异常明细",
    "",
  ];
}

function alertText(alerts, runSummary = {}) {
  const lines = ["Amazon ASIN 可购买性监控异常", "", ...alertSummaryText(alerts, runSummary)];
  for (const alert of alerts) {
    lines.push(`状态: ${alert.status}`);
    lines.push(`店铺名称: ${alert.seller || alert.expectedSeller || ""}`);
    if (alert.productNameZh) lines.push(`商品名称: ${alert.productNameZh}`);
    if (alert.sellerId) lines.push(`卖家ID: ${alert.sellerId}`);
    lines.push(`ASIN: ${alert.asin}`);
    lines.push(`站点: ${alert.siteCode} (${alert.domain})`);
    lines.push(`检测策略: ${alert.detectionStrategy || "marketplace_default"}`);
    lines.push(`期望店铺: ${alert.seller || alert.expectedSeller || ""}`);
    lines.push(`检测店铺: ${alert.detectedSeller || ""}`);
    if (alert.detectedSellerId) lines.push(`检测卖家ID: ${alert.detectedSellerId}`);
    if (alert.sellerMatchMethod) lines.push(`卖家匹配方式: ${alert.sellerMatchMethod}`);
    if (alert.attempts) lines.push(`检测次数: ${alert.abnormalAttempts || 0}/${alert.attempts}`);
    if (alert.attemptStatuses?.length) lines.push(`两次检测状态: ${alert.attemptStatuses.join(" -> ")}`);
    lines.push(`可用性: ${alert.availabilityText || ""}`);
    lines.push(`价格: ${alert.price || ""}`);
    lines.push(`时间: ${alert.detectedAt}`);
    if (alert.screenshotPath) lines.push(`截图: ${alert.screenshotPath}`);
    lines.push("");
  }
  return lines.join("\n");
}

function feishuSign(secret, timestamp) {
  const stringToSign = `${timestamp}\n${secret}`;
  return crypto.createHmac("sha256", stringToSign).update("").digest("base64");
}

export async function sendAlerts(alerts, config, requireFromRuntime, runSummary = {}) {
  if (!alerts.length) return { email: "skipped", feishu: "skipped" };
  const text = alertText(alerts, runSummary);
  const result = { email: "skipped", feishu: "skipped" };

  if (config.email?.enabled) {
    const nodemailer = requireFromRuntime("nodemailer");
    const email = config.email;
    if (!isConfigured(email.smtp_host) || !isConfigured(email.username) || !isConfigured(email.password)) {
      result.email = "not_configured";
    } else {
      const transporter = nodemailer.createTransport({
        host: email.smtp_host,
        port: Number(email.smtp_port || 465),
        secure: email.secure !== false,
        auth: { user: email.username, pass: email.password },
      });
      await transporter.sendMail({
        from: email.from || email.username,
        to: Array.isArray(email.to) ? email.to.join(",") : email.to,
        subject: `Amazon ASIN 可购买性异常 ${alerts.length} 个`,
        text,
      });
      result.email = "sent";
    }
  }

  if (config.feishu?.enabled) {
    const webhook = config.feishu.webhook_url;
    if (!isConfigured(webhook)) {
      result.feishu = "not_configured";
    } else {
      const payload = {
        msg_type: "text",
        content: { text },
      };
      if (config.feishu.secret) {
        const timestamp = String(Math.floor(Date.now() / 1000));
        payload.timestamp = timestamp;
        payload.sign = feishuSign(config.feishu.secret, timestamp);
      }
      const response = await fetch(webhook, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      result.feishu = response.ok ? "sent" : `failed_${response.status}`;
    }
  }

  return result;
}

export { alertText, summaryHeadline };
