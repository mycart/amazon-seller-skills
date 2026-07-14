---
name: monitor-asin-sale-chrome
description: Monitor Amazon ASIN front-end sale/buyability status with the Codex Chrome plugin instead of launching standalone Playwright. Use when Codex needs to create an ASIN monitor Excel template, read a workspace config that points to a Google Drive-synced Excel file, check Amazon product pages through Chrome plugin tabs, verify Add to Cart availability and Sold by seller match, save screenshots/history, export an Excel report by ASIN + country/site, or send email and Feishu alerts for unavailable ASINs.
---

# Monitor ASIN Sale Chrome

Use this skill to monitor whether configured Amazon ASINs are buyable from public product pages when SP-API access is unavailable. The skill is global; each workspace owns its own config, Excel path, snapshots, screenshots, reports, and notification credentials.

## 中文使用说明

这个 Skill 用于监控 Amazon 前台 ASIN 链接是否仍然可购买，并判断当前可购买 offer 是否属于你的店铺。它不依赖 SP-API，也不会自动登录 Seller Central。

关键架构要求：

- 必须使用 `Chrome:control-chrome` 插件访问 Amazon 页面。
- 不要在检测流程中启动独立 Playwright、`chromium.launch()` 或 `launchPersistentContext()`。
- 本地脚本只负责读取 Excel、生成待检查目标、汇总 Chrome 插件返回结果、保存历史、发送通知、导出 Excel 报告。
- 每次运行结束必须导出一个完整 Excel 报告，按 ASIN + 国家/站点维度展示所有明细。

常见中文调用示例：

```text
使用 monitor-asin-sale-chrome，帮我创建 ASIN 销售状态监控模板。
```

```text
使用 monitor-asin-sale-chrome，检查当前工作区的 config.yaml 和 Excel 清单是否配置正确。
```

```text
使用 monitor-asin-sale-chrome，立即用 Chrome 插件运行一次 ASIN 销售状态监控，并导出 Excel 报告。
```

```text
使用 monitor-asin-sale-chrome，解释最近一次 Excel 报告里每个字段的含义。
```

当前默认规则：

- 不自动切换 Deliver 邮编，避免地址弹窗、登录要求或首页反爬导致 ASIN 误报。
- 使用 Codex Chrome 插件访问 Amazon 前台页面，复用用户 Chrome 的稳定连接能力。
- 遇到 “Click the button below to continue shopping / 点击下面的按钮继续购物” 页面时，先点击继续按钮并重试 ASIN 页面。
- 默认最多 1 个站点并发，降低 Amazon 风控概率。
- 默认第一次正常就结束；第一次异常才做第二次确认。
- 只有同一 ASIN/站点确认后仍异常，才进入通知。
- 如果 Excel 填写 `卖家ID（可选）`，优先用 Seller ID 检测；否则回退到店铺名称匹配。
- 异常截图默认保存为压缩 JPEG，并自动清理旧截图。
- 异常通知只输出 `商品名称`，不输出原始商品标题。
- `ACCESS_BLOCKED` 表示监控访问受阻，不代表 ASIN 不可购买，不进入异常通知。
- 异常通知最前面必须先输出类似 `结果汇总：targets=31，checked=41，buyable=21，abnormal=20，access_blocked=2，确认后异常 alerts=10。通知已聚合为同一条消息发送，回执是 email=sent、feishu=sent。` 的全局汇总，再按 ASIN 聚合异常站点状态，最后输出逐条异常明细。

## Workspace Layout

Expect a workspace-local folder named `amazon_availability_monitor/`.

Required config:

```text
amazon_availability_monitor/config.yaml
```

Default generated files:

```text
amazon_availability_monitor/ASIN可购买性监控模板.xlsx
amazon_availability_monitor/data/chrome_run_targets.json
amazon_availability_monitor/data/chrome_results.json
amazon_availability_monitor/data/snapshots.jsonl
amazon_availability_monitor/data/current_status.json
amazon_availability_monitor/reports/ASIN销售状态监控报告_<YYYYMMDD_HHmmss>.xlsx
amazon_availability_monitor/screenshots/
```

The Excel file may be moved to any local Google Drive sync folder. Always read the file path from `config.yaml` field `excel_path`. If the file is missing, fail with a clear message and do not guess or search Google Drive.

All runtime paths are workspace-local. The workspace root is always the current shell working directory (`process.cwd()`):

- Read config from `<current working directory>/amazon_availability_monitor/config.yaml`.
- Write run targets, Chrome results, snapshots, current status, screenshots, and Excel reports under `<current working directory>/amazon_availability_monitor/`.
- Install/runtime dependencies under `<current working directory>/.amazon_availability_monitor_runtime/`.
- Do not read or write monitor state from a fixed business-project path.

## Excel Contract

Read the workbook sheet `ASIN监控清单`. The required header columns are exact:

- `备注`（可选，用作报告明细第一列，方便运营识别中文商品说明）
- `店铺名称`
- `ASIN值`
- `多站点简写（将多个站点写到一起通过标点符号分开多个站点）`
- `卖家ID（可选）`

Treat blank rows as ignored. Expand the site column into one check per ASIN/site. Support these site codes:

```text
US, CA, MX, UK, DE, FR, IT, ES, NL, SE, PL, BE, JP, AU, IN, SG, AE, SA
```

Support separators: English comma, Chinese comma, semicolon, Chinese semicolon, Chinese enumeration comma, slash, whitespace, and line break.

## Run Workflow

Run scripts from the workspace root.

Use the installed skill directory only to locate the scripts:

```bash
SKILL_DIR="$HOME/.codex/skills/monitor-asin-sale-chrome"
```

Create or refresh the Excel template:

```bash
node "$SKILL_DIR/scripts/create_template.mjs"
```

Validate config and Excel only:

```bash
node "$SKILL_DIR/scripts/check_availability.mjs" --validate-only
```

Prepare Chrome-plugin targets:

```bash
node "$SKILL_DIR/scripts/check_availability.mjs" --prepare-chrome-run
```

Then use `Chrome:control-chrome` to visit each target in `amazon_availability_monitor/data/chrome_run_targets.json` and write observations to:

```text
amazon_availability_monitor/data/chrome_results.json
```

Finalize the run, save snapshots, update alert state, send notifications, print the ASIN + country/site table, and export Excel:

```bash
node "$SKILL_DIR/scripts/check_availability.mjs" --finalize-chrome-results amazon_availability_monitor/data/chrome_results.json
```

Do not run `check_availability.mjs` without one of the explicit flags above; plain execution intentionally fails because browser access must happen through the Codex Chrome plugin.

## Chrome Observation Contract

The Chrome-plugin detection step must write a JSON file with either an array or an object containing `observations`:

```json
{
  "observations": [
    {
      "asin": "B0XXXXXXX",
      "siteCode": "US",
      "attempt": 1,
      "finalUrl": "https://www.amazon.com/dp/B0XXXXXXX",
      "detectedAt": "2026-07-14T00:00:00.000Z",
      "productTitle": "Example title",
      "price": "$29.99",
      "detectedSeller": "Your Store Name",
      "detectedSellerId": "A123456789",
      "availabilityText": "In Stock",
      "addToCartVisible": true,
      "buyNowVisible": true,
      "unavailable": false,
      "accessBlocked": false,
      "screenshotPath": "/absolute/path/to/screenshot.jpg",
      "reason": ""
    }
  ]
}
```

If the Chrome step supplies `status`, the finalize script preserves it. If `status` is absent, the script calculates status from access-block, page-error, availability, Add to Cart, and seller signals.

## Status Rules

Return `BUYABLE` only when all are true:

- The product detail page loads successfully.
- The page is checked through the Codex Chrome plugin.
- The page is not an access-blocked, captcha, bot-check, 404, or error page.
- The page has an Add to Cart control.
- The page does not contain unavailable or out-of-stock text.
- If `卖家ID（可选）` is present, the URL uses `?m=<Seller ID>` and seller matching prefers Seller ID signals.
- If Seller ID is absent or not visible, the detected `Sold by` seller must match the Excel `店铺名称` value after whitespace/case normalization.

Return:

- `UNAVAILABLE` when the product has no Add to Cart control or contains unavailable/out-of-stock text.
- `SELLER_MISMATCH` when the page is buyable but `Sold by` does not match the configured store.
- `PAGE_ERROR` when the product page cannot be loaded or has an HTTP/page error.
- `ACCESS_BLOCKED` when Amazon shows a continue-shopping, captcha, or robot verification page after configured recovery attempts. This is a monitoring access issue and must not trigger ASIN abnormal alerts.

## Excel Report

Every finalized run must create one workbook under `amazon_availability_monitor/reports/`.

Workbook sheets:

- `明细`: one final conclusion row per ASIN + country/site for the current run.
- `汇总`: Chinese operations summary with total targets, checked attempts, buyable count, abnormal count, access-blocked count, alert count, generated time, and notification receipt.

`明细` columns are fixed:

```text
备注, 可售状态, 链接, 国家/站点, 商品名称, 店铺名称, 卖家核对, 价格, 可用性/异常原因, 检测次数, 检测时间, ASIN, 截图
```

If the same ASIN + country/site is checked more than once for abnormal confirmation, the report must output only the final conclusion row. Keep the attempt status chain inside `检测次数`.

`汇总` rows are fixed:

```text
总目标数, 实际检测次数, 正常可售, 真实异常, 访问受阻, 触发通知数, 报告生成时间, 通知回执
```

## Alerting

Use `alert_after_consecutive_failures` from config. Default is `2`. Send email and Feishu alerts only when an ASIN/site reaches that consecutive abnormal count. Reset consecutive failures after `BUYABLE`.

Use `check_attempts_per_target` from config. Default is `2`. With the default `confirmation_mode: "abnormal_only"`, check each ASIN/site once and run the second confirmation only when the first result is abnormal; send an alert only when all attempts for that ASIN/site are abnormal.

Extract a short `productNameZh` from the product title for alert readability. Prefer dictionary matches such as `Dog Bed` -> `狗床`, `Dog Stairs` -> `狗楼梯`, and `Dog Blanket` -> `狗毯`; when no dictionary term matches, use the cleaned first 3-6 title words rather than inventing a translation.

The alert should include an operations-readable summary at the very beginning before item details. Include status, store name, Chinese product name, Seller ID when configured, ASIN, site code, detection strategy, Amazon URL, expected seller, detected seller, seller match method, attempt count/statuses, availability text, price, detected time, and screenshot path when available. Do not include Deliver address fields or the raw product title in alerts.

## Automation Prompt

For Codex Automation, use this prompt pattern:

```text
使用全局 monitor-asin-sale-chrome Skill，在当前工作区读取 amazon_availability_monitor/config.yaml 的 excel_path，使用 Codex Chrome 插件检查所有 ASIN 的 Amazon 前台销售/可购买状态。若连续 2 次异常，发送邮件和飞书通知，保存截图与历史记录，并导出一个包含所有 ASIN+国家明细的 Excel 报告。
```
