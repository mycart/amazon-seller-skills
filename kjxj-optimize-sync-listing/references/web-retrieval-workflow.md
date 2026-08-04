# Mode B ASIN Retrieval and Browser Recovery

传统 Listing 优化由 `amazon-listing-optimization` 的 Mode B 完成。编排技能首次调用时只提交目标 ASIN、站点、语言、语气、用户核心关键词，以及保留真实指标的 `listing_eligible` 关键词；不得先行抓取或向该技能提交原 Listing、XLSM、变体、竞品、用户卖点、PPC 或自行整理的产品事实。

## 默认路径与等效恢复

1. 对每个目标 ASIN 单独执行 Mode B，并由该技能按自身工作流获取商品页与原 Listing。
2. 保存完整的原始 Markdown 输出及其 SHA-256；传统标题、五点、描述、后台词、审核与关键词覆盖必须从该原始输出结构化而来。
3. 对临时工具错误、超时、空响应或会话失效，先按原技能流程重试一次 Mode B。
4. 当 `fetch-listing.sh` 返回 `2`（HTTP/网络失败）或 `3`（页面缺少 Listing 字段），或该技能明确报告无法获取 ASIN 页面或原 Listing 时，使用 in-app Browser 打开 `https://www.amazon.<站点>/dp/<ASIN>`。
5. 保存浏览器可见字段为 UTF-8 JSON：`asin`、`marketplace`、`url`、`retrieved_at`、`visible_fields.title`，并在可见时加入 `brand` 与 `bullets`。调用 `amazon-listing-optimization/scripts/mode-b-executor.py start --browser-evidence <json>` 取得真实执行器返回的 `call_id`，再重试 Mode B。
6. in-app Browser 不可用、超时或被会话阻断时，使用 `chrome:control-chrome` 打开同一公开 URL；保存同等证据后重试 Mode B 一次。
6. 两种浏览器都只向 Mode B 重试提供页面中可见且可验证的字段；它们不是编排技能生成传统 Listing 的来源。

## 阻塞条件

单一浏览器出现登录、CAPTCHA、OTP、地区限制或字段不足时，先执行另一条尚未尝试的公开浏览器路径。只有 Mode B 重试、in-app Browser 和 Chrome 均无法提供足以完成 Mode B 的公开页面信息，或执行器在持有公开证据后仍无法产生完整的传统 Listing 原始输出时，任务才阻塞，并以中文列明每个路径的失败原因及用户需要完成的最小动作。在此期间不得生成替代 Listing、2026 短标题、PPC、Q/A、XLSM 写入计划或写入结果。

## XLSM 边界

分类商品报告 XLSM 只在传统 Listing 与 2026 短标题均已完成后用于字段匹配、同步预检和用户确认后的写入。它绝不提供原 Listing、标题来源或任何传统 Listing 事实，且不得作为 ASIN 获取失败的回退。

保留 Browser 恢复的页面快照或执行记录，供 Mode B 重试追溯；这些证据不替代 Mode B 原始 Markdown 输出，也不进入传统 Listing 的事实来源链。
