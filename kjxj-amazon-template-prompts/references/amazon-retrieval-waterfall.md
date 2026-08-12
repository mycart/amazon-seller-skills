# Amazon 实时取证瀑布

每个站点按串行顺序完成主 ASIN、变体和关键词搜索页取证，再进入下一站点。不得读取 Cookie、密码、Local Storage 或浏览器配置，不自动登录。只使用一个持久 Chrome 标签页；不得多站并行或批量导航。

## 页面就绪判定

1. 导航后等待 `domcontentloaded`，随后每 1.5 秒读取一次可见 DOM 商品卡片，最多轮询 8 次（最长 12 秒）。
2. 只有卡片同时存在可见 ASIN、非空可见标题和一基位置时，页面才是 `ready`。不要以标题、筛选器、结果总数或 `body.innerText` 存在作为卡片就绪依据。
3. 首次最长轮询仍无合格卡片时，对同一页面执行一次等待或刷新重试，再按相同规则轮询。两次未就绪前不得标记渠道失败或回退。
4. Chrome 与内置浏览器每次尝试记录 `readiness`：`state`、`polls`、`waited_ms`、`visible_card_count`、`screenshot_path`。未就绪、挑战页或超时时必须保存真实截图文件；成功页面可留空截图路径。
5. 仅记录实际执行过的浏览器尝试。不得预填 Chrome、内置浏览器或任何未执行的渠道。

## 1. Chrome 扩展

1. 使用 Chrome 插件的浏览器运行时初始化流程，以 `get("chrome")` 强制选择 Chrome；先读取轻量标签页状态，并为会话命名。首次连接失败时等待 2 秒并重试一次。
2. 连接失败时检查 Chrome 是否运行、扩展是否启用、Native Host 是否正确；不要自行修复插件。
3. 使用同一持久标签页访问当前站点的商品页或搜索 URL。先完成页面就绪判定，再读取可见 DOM 的商品卡片；不解析脚本、网络响应或隐藏节点。
4. 每个关键词最多一次初始搜索和一次基于可见页面状态的重试。Chrome 成功后停止，不得调用内置浏览器。

## 2. 内置浏览器回退

仅当 Chrome 不可用、两次页面就绪检查后仍无法加载、目标会话无法访问或出现挑战页时使用。重复 Chrome 的可见 DOM 卡片规则，并将渠道记录为 `in_app_browser`。成功后停止；两次检查仍失败时设定 `competitor_attempts_exhausted: true`。

## 竞品证据契约

每个可写入模板的竞品记录必须包含：

```json
{
  "asin": "B012345678",
  "source_type": "organic",
  "title": "当前页面可见商品标题",
  "position": 1,
  "channel": "chrome",
  "evidence_url": "https://www.amazon.de/s?k=kratzmatte",
  "captured_at": "2026-08-09T00:00:00Z"
}
```

先按页面可见顺序选取自然结果；不足 3 个时才追加 Sponsored。Chrome 成功时只记录 Chrome；Chrome 失败、内置浏览器成功时必须按此顺序记录两次尝试；两层都失败时，竞品字段为 `待补充`，并设定 `competitor_attempts_exhausted: true`。
