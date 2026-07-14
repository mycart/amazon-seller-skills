---
name: monitor-amazon-listing-chrome
description: Monitor Amazon ASIN listing completeness and quality across multiple marketplaces using the Codex Chrome plugin, a configurable Excel ASIN list, local scoring/report scripts, and optional email/Feishu delivery. Use when Codex needs to read an ASIN marketplace Excel file, open public Amazon product pages in Chrome, collect visible listing facts, score listing completeness by ASIN + country, generate Markdown/Excel/JSON reports, save screenshots, or run a scheduled repeatable Amazon listing monitor without using SP-API or the older amazon-listing-monitor skill.
---

# Monitor Amazon Listing Chrome

## Overview

Use this skill to monitor public Amazon Listing completeness by `ASIN + 国家站点` with Chrome. Do not use the older `amazon-listing-monitor` skill. Do not use Seller Central login scraping, captcha bypass, forced proxy pools, or access-control evasion.

The skill now uses `当前工作目录优先`:

- First look for `./config.yaml`
- If missing, auto-create `./config.yaml`
- If missing, also create or copy `./ASIN可购买性监控模板.xlsx`

Legacy fallback template source:

```bash
/Users/apple/Documents/Listing优化建议/amazon_chrome_listing_monitor/config.yaml
```

Legacy default Excel source:

```bash
/Users/apple/Documents/Listing优化建议/ASIN可购买性监控模板.xlsx
```

## Workflow

1. Validate the workspace config and Excel:

```bash
node /Users/apple/.codex/skills/monitor-amazon-listing-chrome/scripts/validate_config.mjs
```

2. Prepare a run package:

```bash
node /Users/apple/.codex/skills/monitor-amazon-listing-chrome/scripts/run_monitor.mjs --prepare-only
```

3. Use the Codex Chrome plugin to open every task URL from the prepared run package and collect visible page facts into:

```text
<run_dir>/browser_results.json
```

4. Assemble reports and send notifications according to the active config:

```bash
node /Users/apple/.codex/skills/monitor-amazon-listing-chrome/scripts/run_monitor.mjs --assemble-run <run_dir>
```

If `delivery.email.enabled` or `delivery.feishu.enabled` is true, send the report automatically after assembly. Use `--no-send` only for manual validation runs where notifications must be suppressed.

If the user explicitly provides `--config /custom/path/config.yaml`, that explicit path still wins.

## Excel Contract

Read sheet `ASIN监控清单`; if absent, the scripts use the first sheet. Required columns:

- `店铺名称`
- `ASIN值`
- `多站点简写（将多个站点写到一起通过标点符号分开多个站点）`

Optional columns:

- `卖家ID（可选）`
- `备注`

Split site codes on English comma, Chinese comma, semicolon, Chinese semicolon, enumeration comma, slash, whitespace, and line breaks. Deduplicate by `ASIN + site`.

Supported site codes:

```text
US, CA, MX, UK, DE, FR, IT, ES, NL, BE, JP, AU, IN
```

Read `references/excel_schema.md` before changing Excel behavior.

## Chrome Collection Rules

Use Chrome as the primary browser surface. Browser plugin may be used only for quick secondary verification.

For each task, open `task.url` and collect a result object with this shape:

```json
{
  "task": { "...": "copy the task object from manifest.json" },
  "status": "OK",
  "url": "https://www.amazon.de/dp/B0EXAMPLE",
  "extractedAt": "2026-07-13T00:00:00.000Z",
  "screenshotPath": "",
  "source": "Chrome插件前台页面",
  "facts": {
    "title": "",
    "bullets": [],
    "imageCount": 0,
    "hasAplus": false,
    "description": "",
    "price": "",
    "rating": "",
    "reviewCount": "",
    "availability": "",
    "seller": "",
    "category": "",
    "bsr": "",
    "error": ""
  }
}
```

Use these page signals when available:

- Title: `#productTitle`
- Bullet points: `#feature-bullets li span`
- Images: unique visible image URLs in `#altImages`, image block, or landing image data
- A+: `#aplus`, `.aplus-v2`, or visible Enhanced Brand Content sections
- Description: `#productDescription`, product overview, or product details description text
- Price: `.a-price .a-offscreen`, buybox price, or visible offer price
- Rating: `#acrPopover span.a-icon-alt`
- Review count: `#acrCustomerReviewText`
- Availability: `#availability`
- Seller: `#sellerProfileTriggerId`, `#merchant-info`, buybox seller text, or offer display seller text
- Category/BSR: breadcrumbs, detail bullets, or product details tables

If Amazon shows captcha, robot check, continue-shopping interstitial, or access-block page, set status to `CAPTCHA`, `ACCESS_BLOCKED`, or `CONTINUE_SHOPPING`, and save a screenshot when configured.

Important: `CONTINUE_SHOPPING` is recoverable when the actual product page DOM is already visible and reliable Listing facts were collected. If title, bullets, images, and additional product signals are present, keep the collected facts and allow scoring. Only treat `CONTINUE_SHOPPING` as unreviewable when the interstitial persists and product facts are missing or unreliable. Never score from guessed data.

Read `references/status_rules.md` before changing statuses.

## Reports

The Excel report must contain one row per `ASIN值 + 国家`. Keep the report concise for operators who need to judge online Listing completeness and copy quality quickly. The first column must be:

```text
备注
```

Use `备注` for the user's Chinese product note from the input Excel. Keep `页面状态` as column 3 and `核心优化建议` as column 8. Important decision fields must stay near the front: score, ASIN, country, URL, store name, whether optimization is recommended, priority, and main issues/missing parts. Avoid re-adding separate repetitive columns for good points, shortcomings, missing parts, and suggestions; merge them into the concise issue/suggestion columns.

Score only normally loaded pages. For access-blocked, captcha, page error, not found, or fetch failure states, write `无法审查`.

Read `references/scoring_rules.md` before changing scoring or report language.

## Delivery

Email and Feishu delivery are controlled by the active `config.yaml`. Secrets should be read from environment variables such as:

```text
AMAZON_MONITOR_SMTP_PASSWORD
AMAZON_MONITOR_FEISHU_WEBHOOK
AMAZON_MONITOR_FEISHU_SECRET
```

Default delivery is disabled. Do not send notifications unless the config explicitly enables them or the user asks for `--send`.

When delivery is enabled, the message body must include an operations-readable Markdown-style table with remark, score, optimization flag, priority, issue summary, core suggestion, ASIN, country, page status, and URL. Email delivery must attach the generated Excel report file.

Read `references/config_schema.md` before changing configuration.

## Scheduling Prompt

Use this prompt for a recurring Codex automation:

```text
使用 $monitor-amazon-listing-chrome，优先读取当前工作目录下的 config.yaml；若不存在则自动在当前工作目录创建 config.yaml 和对应 Excel 模板，再使用 Chrome 插件检查 Excel 中全部 ASIN + 国家站点的 Amazon 前台 Listing 完整度和质量，按 ASIN值 + 国家维度生成明细表，第一列输出备注，第3列输出页面状态，第8列输出核心优化建议；生成 Markdown、Excel、JSON 报告；如果配置启用了邮件或飞书，请发送给对应运营人员。
```

## Output Language

Use Chinese for explanations, audits, summaries, and recommendations. Preserve ASIN, site code, product title, price, rating, review count, BSR, category, URLs, and raw Amazon error text in their original form.
