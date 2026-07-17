#!/usr/bin/env node

import fs from "node:fs";
import { expandTasksFromWorkbook, loadConfig, resolveConfigPath } from "./lib.mjs";

const resolution = resolveConfigPath(
  process.argv.includes("--config")
    ? process.argv[process.argv.indexOf("--config") + 1]
    : undefined
);
const configPath = resolution.configPath;

try {
  const config = loadConfig(configPath);
  const errors = [];
  const warnings = [];

  if (!config.excel_path) errors.push("缺少 excel_path");
  if (config.excel_path && !fs.existsSync(config.excel_path)) errors.push(`Excel 文件不存在: ${config.excel_path}`);
  for (const [key, dir] of Object.entries(config.output || {})) {
    if (!dir) errors.push(`output.${key} 为空`);
  }
  if ((config.runtime?.max_parallel_pages || 1) !== 1) {
    warnings.push("建议 max_parallel_pages 保持 1，降低 Amazon 前台访问受阻概率。");
  }
  if (config.delivery?.email?.enabled) {
    const email = config.delivery.email;
    for (const field of ["smtp_host", "smtp_port", "username", "from"]) {
      if (!email[field]) errors.push(`邮件启用后缺少 delivery.email.${field}`);
    }
    if (!email.password && !email.password_env) errors.push("邮件启用后缺少 password 或 password_env");
    if (!Array.isArray(email.to) || !email.to.length) errors.push("邮件启用后缺少 delivery.email.to");
  }
  if (config.delivery?.feishu?.enabled) {
    const feishu = config.delivery.feishu;
    if (!feishu.webhook_url && !feishu.webhook_url_env) errors.push("飞书启用后缺少 webhook_url 或 webhook_url_env");
  }

  let excel = null;
  if (!errors.length) {
    excel = expandTasksFromWorkbook(config.excel_path);
    if (!excel.tasks.length) errors.push("Excel 没有可监控的 ASIN + 国家站点任务");
  }

  const result = {
    ok: errors.length === 0,
    configPath,
    configResolution: {
      source: resolution.source,
      createdConfig: resolution.createdConfig,
      createdExcel: resolution.createdExcel,
    },
    errors,
    warnings,
    excel: excel ? {
      sheet: excel.sheet,
      headers: excel.headers,
      taskCount: excel.tasks.length,
      sampleTasks: excel.tasks.slice(0, 5),
    } : null,
  };
  console.log(JSON.stringify(result, null, 2));
  process.exit(errors.length ? 1 : 0);
} catch (error) {
  console.error(error.stack || error.message);
  process.exit(1);
}
