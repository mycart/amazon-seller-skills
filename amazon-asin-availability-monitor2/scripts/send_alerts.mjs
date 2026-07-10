#!/usr/bin/env node
import crypto from "node:crypto";

function isConfigured(value) {
  return value && !String(value).includes("example.com") && !String(value).includes("REPLACE_ME");
}

function alertText(alerts) {
  const lines = ["Amazon ASIN 可购买性监控异常", ""];
  for (const alert of alerts) {
    lines.push(`状态: ${alert.status}`);
    lines.push(`店铺名称: ${alert.seller || alert.expectedSeller || ""}`);
    if (alert.productNameZh) lines.push(`商品名称: ${alert.productNameZh}`);
    if (alert.sellerId) lines.push(`卖家ID: ${alert.sellerId}`);
    lines.push(`ASIN: ${alert.asin}`);
    lines.push(`站点: ${alert.siteCode} (${alert.domain})`);
    lines.push(`检测策略: ${alert.detectionStrategy || "marketplace_default"}`);
    lines.push(`链接: ${alert.url}`);
    lines.push(`期望店铺: ${alert.seller || alert.expectedSeller || ""}`);
    lines.push(`检测店铺: ${alert.detectedSeller || ""}`);
    if (alert.detectedSellerId) lines.push(`检测卖家ID: ${alert.detectedSellerId}`);
    if (alert.sellerMatchMethod) lines.push(`卖家匹配方式: ${alert.sellerMatchMethod}`);
    if (alert.attempts) lines.push(`检测次数: ${alert.abnormalAttempts || 0}/${alert.attempts}`);
    if (alert.attemptStatuses?.length) lines.push(`检测状态: ${alert.attemptStatuses.join(" -> ")}`);
    if (alert.deliveryLocation) {
      const deliveryStatus = alert.deliveryLocation.skipped
        ? "跳过"
        : alert.deliveryLocation.applied
          ? "成功"
          : "失败";
      lines.push(`Deliver地址状态: ${deliveryStatus}`);
      if (alert.deliveryLocation.postalCode) lines.push(`Deliver邮编: ${alert.deliveryLocation.postalCode}`);
      if (alert.deliveryLocation.reason) lines.push(`Deliver说明: ${alert.deliveryLocation.reason}`);
      if (alert.deliveryLocation.warning) {
        lines.push("注意: 本次结果是在 Deliver 地址切换失败后继续检测得到，可能受 IP 默认地区影响。");
      }
    }
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

export async function sendAlerts(alerts, config, requireFromRuntime) {
  if (!alerts.length) return { email: "skipped", feishu: "skipped" };
  const text = alertText(alerts);
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

export { alertText };
