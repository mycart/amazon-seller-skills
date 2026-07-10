---
name: amazon-asin-availability-monitor2
description: Monitor Amazon ASIN front-end buyability for seller-owned listings without SP-API access. Use when Codex needs to create an ASIN monitor Excel template, read a workspace config that points to a Google Drive-synced Excel file, check Amazon product pages with Playwright, verify Add to Cart availability and Sold by seller match, save screenshots/history, or send email and Feishu alerts for unavailable ASINs.
---

# Amazon ASIN Availability Monitor

Use this skill to monitor whether configured Amazon ASINs are buyable from the public product page when SP-API access is unavailable. The skill is global; each workspace owns its own config, Excel path, snapshots, screenshots, and notification credentials.

## 中文使用说明

这个 Skill 用于监控 Amazon 前台 ASIN 链接是否仍然可购买，并判断当前可购买 offer 是否属于你的店铺。它不依赖 SP-API，也不会自动登录 Seller Central。

常见中文调用示例：

```text
使用 amazon-asin-availability-monitor2，帮我创建 ASIN 可购买性监控模板。
```

```text
使用 amazon-asin-availability-monitor2，检查当前工作区的 config.yaml 和 Excel 清单是否配置正确。
```

```text
使用 amazon-asin-availability-monitor2，立即运行一次 ASIN 可购买性监控。
```

```text
使用 amazon-asin-availability-monitor2，解释最近一次异常通知里每个字段的含义。
```

```text
使用 amazon-asin-availability-monitor2，把异常截图保留时间改成 7 天，最多保留 300 张。
```

```text
使用 amazon-asin-availability-monitor2，把监控清单 Excel 移动到 Google Drive 新目录后，更新 excel_path。
```

当前默认规则：

- 先按站点尝试切换本土 Deliver 邮编；切换失败不直接报错，继续检测并在异常里标注。
- 按站点分组检测，同一站点同一轮复用 Deliver 地址结果。
- 默认最多 2 个站点并发，降低整体耗时。
- 默认第一次正常就结束；第一次异常才做第二次确认。
- 只有同一 ASIN/站点确认后仍异常，才进入通知。
- 如果 Excel 填写 `卖家ID（可选）`，优先用 Seller ID 检测；否则回退到店铺名称匹配。
- 异常截图默认保存为压缩 JPEG，并自动清理旧截图。
- 异常通知只输出 `商品名称`，不输出原始商品标题。

## Workspace Layout

Expect a workspace-local folder named `amazon_availability_monitor/`.

Required config:

```text
amazon_availability_monitor/config.yaml
```

Default generated files:

```text
amazon_availability_monitor/ASIN可购买性监控模板.xlsx
amazon_availability_monitor/data/snapshots.jsonl
amazon_availability_monitor/data/current_status.json
amazon_availability_monitor/screenshots/
```

The Excel file may be moved to any local Google Drive sync folder. Always read the file path from `config.yaml` field `excel_path`. If the file is missing, fail with a clear message and do not guess or search Google Drive.

Default to `delivery_strategy: "postal_code_best_effort"`. First try to set the local Deliver postal code from `delivery_locations.<SITE>.postal_code`; if Amazon blocks or requires login, continue checking the ASIN page and mark the result with a Deliver warning instead of failing immediately. Use `delivery_strategy: "marketplace_default"` only when postal-code attempts should be skipped entirely, and `delivery_strategy: "postal_code_required"` only when a failed postal-code change should stop the check.

## Excel Contract

Read the workbook sheet `ASIN监控清单`. The required header columns are exact:

- `店铺名称`
- `ASIN值`
- `多站点简写（将多个站点写到一起通过标点符号分开多个站点）`
- `卖家ID（可选）`

Treat blank rows as ignored. Expand the site column into one check per ASIN/site. Support these site codes:

```text
US, CA, MX, UK, DE, FR, IT, ES, NL, SE, PL, BE, JP, AU, IN, SG, AE, SA
```

Support separators: English comma, Chinese comma, semicolon, Chinese semicolon, Chinese enumeration comma, slash, whitespace, and line break.

## Status Rules

Return `BUYABLE` only when all are true:

- The product detail page loads successfully.
- The page is checked after a best-effort local Deliver postal-code attempt, or with an explicit Deliver warning when that attempt fails.
- The page is not a captcha, bot-check, 404, or error page.
- The page has an Add to Cart control.
- The page does not contain unavailable or out-of-stock text.
- If `卖家ID（可选）` is present, the URL uses `?m=<Seller ID>` and seller matching prefers Seller ID signals.
- If Seller ID is absent or not visible, the detected `Sold by` seller must match the Excel `店铺名称` value after whitespace/case normalization.

Return:

- `UNAVAILABLE` when the product has no Add to Cart control or contains unavailable/out-of-stock text.
- `SELLER_MISMATCH` when the page is buyable but `Sold by` does not match the configured store.
- `PAGE_ERROR` when the product page cannot be loaded or has an HTTP/page error.
- `BOT_BLOCKED` when Amazon shows captcha or robot verification.

## Scripts

Run scripts from the workspace root.

Create or refresh the Excel template:

```bash
node /Users/apple/.codex/skills/amazon-asin-availability-monitor2/scripts/create_template.mjs
```

Run one monitoring pass:

```bash
node /Users/apple/.codex/skills/amazon-asin-availability-monitor2/scripts/check_availability.mjs
```

The default browser setting is `browser.channel: "chrome"`, which uses the local Google Chrome installation through Playwright. If a workspace has no Chrome, install Playwright Chromium in that workspace runtime and set `browser.channel: ""`.

Install or verify runtime dependencies only:

```bash
node /Users/apple/.codex/skills/amazon-asin-availability-monitor2/scripts/setup_runtime.mjs
```

## Alerting

Use `alert_after_consecutive_failures` from config. Default is `2`. Send email and Feishu alerts only when an ASIN/site reaches that consecutive abnormal count. Reset consecutive failures after `BUYABLE`.

Use `check_attempts_per_target` from config. Default is `2`. With the default `confirmation_mode: "abnormal_only"`, check each ASIN/site once and run the second confirmation only when the first result is abnormal; send an alert only when all attempts for that ASIN/site are abnormal.

For efficiency, group targets by site, reuse one Deliver postal-code attempt per site when `reuse_delivery_location_per_site: true`, and run at most `max_parallel_site_groups` site groups concurrently.

For screenshot storage, default to compressed viewport JPEG screenshots: `screenshots.format: "jpeg"`, `quality: 65`, `full_page: false`. Run screenshot cleanup on each monitor run, deleting files older than `screenshots.retention_days` and then pruning the oldest files if screenshot count exceeds `screenshots.max_files`.

Extract a short `productNameZh` from the product title for alert readability. Prefer dictionary matches such as `Dog Bed` -> `狗床`, `Dog Stairs` -> `狗楼梯`, and `Dog Blanket` -> `狗毯`; when no dictionary term matches, use the cleaned first 3-6 title words rather than inventing a translation.

The alert should include every ASIN/site that is abnormal in the current run after the configured attempt threshold. Include status, store name, Chinese product name, Seller ID when configured, ASIN, site code, detection strategy, Deliver status/reason, Amazon URL, expected seller, detected seller, seller match method, attempt count/statuses, availability text, price, detected time, and screenshot path when available. Do not include the raw product title in alerts.

## Automation Prompt

For Codex Automation, use this prompt pattern:

```text
使用全局 amazon-asin-availability-monitor2 Skill，在当前工作区读取 amazon_availability_monitor/config.yaml 的 excel_path，检查所有 ASIN 的 Amazon 前台可购买性。若连续 2 次异常，发送邮件和飞书通知，并保存截图与历史记录。
```
