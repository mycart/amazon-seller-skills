# Amazon 实时取证瀑布

每个站点、每个关键词按本顺序执行；低层只能在高层失败或无法使用时启动。不得读取 Cookie、密码、Local Storage 或浏览器配置，不自动登录。

## 1. Chrome

1. 使用 Chrome 插件的浏览器运行时初始化流程；先读取轻量标签页状态。首次失败时等待 2 秒并重试一次。
2. 连接失败时检查 Chrome 是否运行、扩展是否启用、Native Host 是否正确；不要自行修复插件。
3. 访问一个目标站搜索 URL 或使用当前页面的站内搜索。读取可见 DOM 的商品卡片，不解析脚本、网络响应或隐藏节点。
4. 每个关键词最多一次初始搜索和一次基于可见页面状态的重试。记录 `chrome` 尝试；成功后停止降级。

## 2. 内置浏览器

仅当 Chrome 不可用、页面无法加载、目标会话无法访问或出现挑战页时使用。重复 Chrome 的可见 DOM 卡片规则，并将渠道记录为 `in_app_browser`；成功后停止降级。

## 3. Firecrawl

仅当前两层失败时使用。强制 `maxAge: 0` 且 URL 必须属于目标 Amazon 域名。先请求精简内容；若 JSON 提取因页面体积失败，额外执行一次受限 HTML/DOM 提取。只有同时取得卡片 ASIN、标题、位置和 Sponsored 标识时才可写入竞品。记录渠道为 `firecrawl`。

## 4. HTTP 诊断

仅前三层均失败时运行：

```bash
python3 scripts/http_page_diagnostic.py 'https://www.amazon.de/s?k=kratzmatte'
```

诊断输出只用于填写失败尝试记录，不提取、推断或输出竞品 ASIN。完成后标记 `competitor_attempts_exhausted: true`。

## 竞品证据契约

每个可写入模板的竞品记录必须包含：

```json
{
  "asin": "B012345678",
  "source_type": "organic",
  "title": "当前页面可见商品标题",
  "position": 1,
  "channel": "chrome",
  "evidence_url": "https://www.amazon.de/s?k=...",
  "captured_at": "2026-08-09T00:00:00Z"
}
```

先按页面可见顺序选取自然结果；不足 3 个时才追加 Sponsored。所有渠道失败时，竞品字段可为 `待补充`，但 `analysis.competitors.attempts` 必须有四层的真实尝试记录及原因。
