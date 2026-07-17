#!/usr/bin/env node

import fs from "node:fs";
import tls from "node:tls";
import net from "node:net";
import crypto from "node:crypto";

export async function sendNotifications(delivery, report) {
  const receipt = {};
  if (delivery.email?.enabled) {
    receipt.email = await sendEmail(delivery.email, report);
  } else {
    receipt.email = "disabled";
  }
  if (delivery.feishu?.enabled) {
    receipt.feishu = await sendFeishu(delivery.feishu, report);
  } else {
    receipt.feishu = "disabled";
  }
  return receipt;
}

async function sendFeishu(config, report) {
  const webhook = resolveConfiguredSecret(config.webhook_url, config.webhook_url_env, { url: true });
  if (!webhook) throw new Error("飞书 webhook 未配置或环境变量为空");
  const text = buildFeishuText(report);
  const body = { msg_type: "text", content: { text } };

  const secret = resolveConfiguredSecret(config.secret, config.secret_env);
  if (secret) {
    const timestamp = Math.floor(Date.now() / 1000);
    const sign = crypto
      .createHmac("sha256", `${timestamp}\n${secret}`)
      .update("")
      .digest("base64");
    body.timestamp = String(timestamp);
    body.sign = sign;
  }

  const response = await fetch(webhook, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const responseText = await response.text();
  return { status: response.status, body: responseText.slice(0, 1000) };
}

async function sendEmail(config, report) {
  const password = resolveConfiguredSecret(config.password, config.password_env);
  if (!password) throw new Error("SMTP 密码未配置或环境变量为空");
  const to = Array.isArray(config.to) ? config.to : [config.to].filter(Boolean);
  const subject = `Amazon Listing 完整度监控报告 ${new Date().toISOString().slice(0, 10)}`;
  const body = buildEmailBody(report);
  const message = buildMimeMessage({
    from: config.from || config.username,
    to,
    subject,
    body,
    attachments: [report.xlsxPath].filter(Boolean),
  });
  await smtpSend({
    host: config.smtp_host,
    port: Number(config.smtp_port || 465),
    secure: config.secure !== false,
    username: config.username,
    password,
    from: config.from || config.username,
    to,
    message,
  });
  return { status: "sent", to };
}

function buildFeishuText(report) {
  const summary = report.summary || {};
  const rows = report.rows || [];
  const actionable = rows.filter((row) => row["Listing是否建议优化"] === "是");
  const lines = [];
  lines.push(`Amazon Listing 完整度监控报告`);
  lines.push(`任务总数：${summary.total ?? rows.length}`);
  lines.push(`建议优化：${summary.optimizable ?? actionable.length}`);
  lines.push(`无法审查：${summary.unreviewable ?? 0}`);
  lines.push(`状态分布：${formatStatusSummary(summary.statuses || {})}`);
  lines.push(`报告路径：${report.xlsxPath || report.mdPath || ""}`);
  lines.push("");
  lines.push(actionable.length ? "需要运营关注的明细：" : "本轮明细：");
  lines.push(formatMarkdownTable(actionable.length ? actionable : rows, { limit: 20 }));
  return lines.join("\n").slice(0, 18000);
}

function buildEmailBody(report) {
  const summary = report.summary || {};
  const rows = report.rows || [];
  const actionable = rows.filter((row) => row["Listing是否建议优化"] === "是");
  const sections = [];
  sections.push("Amazon Listing 完整度监控报告");
  sections.push("");
  sections.push(`任务总数：${summary.total ?? rows.length}`);
  sections.push(`可审查：${summary.scorable ?? ""}`);
  sections.push(`建议优化：${summary.optimizable ?? actionable.length}`);
  sections.push(`无法审查：${summary.unreviewable ?? ""}`);
  sections.push(`状态分布：${formatStatusSummary(summary.statuses || {})}`);
  sections.push("");
  sections.push(actionable.length ? "需要运营关注的明细：" : "本轮明细：");
  sections.push(formatMarkdownTable(actionable.length ? actionable : rows, { limit: 200 }));
  sections.push("");
  sections.push(`完整 Excel 报告：${report.xlsxPath || ""}`);
  sections.push(`Markdown 报告：${report.mdPath || ""}`);
  sections.push(`JSON 快照：${report.snapshotPath || ""}`);
  sections.push("");
  sections.push("Excel 明细报告已随邮件作为附件发送。");
  return `${sections.join("\n")}\n`;
}

function formatMarkdownTable(rows, options = {}) {
  const limit = options.limit || rows.length;
  const selected = rows.slice(0, limit);
  const header = ["备注", "评分", "是否优化", "优先级", "主要问题/缺失", "建议", "ASIN", "国家", "页面状态", "URL"];
  const lines = [];
  lines.push(`| ${header.join(" | ")} |`);
  lines.push(`| ${header.map(() => "---").join(" | ")} |`);
  for (const row of selected) {
    lines.push(`| ${[
      row["备注"],
      row["Listing完整度和质量评分"],
      row["Listing是否建议优化"],
      row["Listing优化优先级"],
      compactIssue(row),
      row["核心优化建议"] || row["Listing优化建议"],
      row["ASIN值"],
      row["国家"],
      row["页面状态"],
      row["站点URL"],
    ].map(tableCell).join(" | ")} |`);
  }
  if (rows.length > selected.length) {
    lines.push(`| ... | ... | ... | ... | 其余 ${rows.length - selected.length} 行请查看 Excel 附件 | ... | ... | ... | ... | ... |`);
  }
  return lines.join("\n");
}

function compactIssue(row) {
  return row["主要问题/缺失"] || row["Listing缺失的部分"] || row["Listing不足的地方"] || row["Listing优化建议"] || "";
}

function tableCell(value) {
  return String(value ?? "")
    .replace(/\s+/g, " ")
    .replace(/\|/g, "/")
    .trim();
}

function formatStatusSummary(statuses) {
  const entries = Object.entries(statuses || {});
  if (!entries.length) return "无";
  return entries.map(([status, count]) => `${status}:${count}`).join("，");
}

function resolveConfiguredSecret(directValue, envNameOrValue, options = {}) {
  if (directValue) return directValue;
  if (!envNameOrValue) return "";
  if (process.env[envNameOrValue]) return process.env[envNameOrValue];
  if (options.url && /^https?:\/\//i.test(envNameOrValue)) return envNameOrValue;
  if (!isLikelyEnvName(envNameOrValue)) return envNameOrValue;
  return "";
}

function isLikelyEnvName(value) {
  return /^[A-Z_][A-Z0-9_]*$/.test(String(value || ""));
}

function buildMimeMessage({ from, to, subject, body, attachments }) {
  const boundary = `----amazon-monitor-${Date.now()}`;
  const parts = [];
  parts.push(`From: ${from}`);
  parts.push(`To: ${to.join(", ")}`);
  parts.push(`Subject: =?UTF-8?B?${Buffer.from(subject).toString("base64")}?=`);
  parts.push("MIME-Version: 1.0");
  parts.push(`Content-Type: multipart/mixed; boundary="${boundary}"`);
  parts.push("");
  parts.push(`--${boundary}`);
  parts.push('Content-Type: text/plain; charset="UTF-8"');
  parts.push("Content-Transfer-Encoding: base64");
  parts.push("");
  parts.push(Buffer.from(body).toString("base64").replace(/(.{76})/g, "$1\r\n"));
  for (const attachment of attachments || []) {
    if (!fs.existsSync(attachment)) continue;
    const filename = attachment.split("/").pop();
    parts.push(`--${boundary}`);
    parts.push(`Content-Type: application/octet-stream; name="=?UTF-8?B?${Buffer.from(filename).toString("base64")}?="`);
    parts.push("Content-Transfer-Encoding: base64");
    parts.push(`Content-Disposition: attachment; filename="=?UTF-8?B?${Buffer.from(filename).toString("base64")}?="`);
    parts.push("");
    parts.push(fs.readFileSync(attachment).toString("base64").replace(/(.{76})/g, "$1\r\n"));
  }
  parts.push(`--${boundary}--`);
  parts.push("");
  return parts.join("\r\n");
}

function smtpSend({ host, port, secure, username, password, from, to, message }) {
  return new Promise((resolve, reject) => {
    const socket = secure ? tls.connect(port, host) : net.connect(port, host);
    let buffer = "";
    let step = 0;
    const commands = [
      () => `EHLO localhost\r\n`,
      () => `AUTH LOGIN\r\n`,
      () => `${Buffer.from(username).toString("base64")}\r\n`,
      () => `${Buffer.from(password).toString("base64")}\r\n`,
      () => `MAIL FROM:<${from}>\r\n`,
      ...to.map((address) => () => `RCPT TO:<${address}>\r\n`),
      () => `DATA\r\n`,
      () => `${message}\r\n.\r\n`,
      () => `QUIT\r\n`,
    ];

    socket.setTimeout(30000);
    socket.on("data", (chunk) => {
      buffer += chunk.toString("utf8");
      if (!/\r?\n$/.test(buffer)) return;
      const code = Number(buffer.slice(0, 3));
      if (code >= 400) {
        socket.destroy();
        reject(new Error(`SMTP 发送失败: ${buffer}`));
        return;
      }
      buffer = "";
      if (step < commands.length) {
        socket.write(commands[step++]());
      } else {
        resolve();
      }
    });
    socket.on("error", reject);
    socket.on("timeout", () => {
      socket.destroy();
      reject(new Error("SMTP 连接超时"));
    });
  });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const payload = JSON.parse(await readStdin());
  const receipt = await sendNotifications(payload.delivery || {}, payload.report || {});
  process.stdout.write(`${JSON.stringify(receipt, null, 2)}\n`);
}

function readStdin() {
  return new Promise((resolve) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => (data += chunk));
    process.stdin.on("end", () => resolve(data || "{}"));
  });
}
