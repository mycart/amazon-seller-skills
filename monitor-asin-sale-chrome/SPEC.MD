# Monitor ASIN Sale Chrome Skill 架构规格

## 目标

构建一个 Codex 全局 Skill，用于在没有 Amazon SP-API 权限的情况下，通过 Amazon 前台商品页监控自有 ASIN 是否可销售/可购买，并在异常时通过邮件和飞书通知运营人员，同时导出本轮完整 Excel 报告。

该 Skill 适用于：

- 定时检查 ASIN 链接是否仍可下单。
- 验证当前可购买 offer 是否属于目标店铺。
- 使用 Codex 自带 Chrome 插件访问 Amazon 页面，避免脚本自行启动 Playwright + 本机 Chrome 前台页面检测。
- 遇到 Amazon 继续购物/机器人中间页时先尝试恢复访问；无法恢复时标记为访问受阻，不误报为商品异常。
- 保存异常截图、历史快照和 ASIN + 国家/站点维度 Excel 报告。

## 目录结构

```text
monitor-asin-sale-chrome/
├── SKILL.md
├── SPEC.MD
├── agents/
│   └── openai.yaml
└── scripts/
    ├── setup_runtime.mjs
    ├── create_template.mjs
    ├── check_availability.mjs
    └── send_alerts.mjs
```

工作区运行目录：

```text
<current working directory>/
├── .amazon_availability_monitor_runtime/
└── amazon_availability_monitor/
    ├── config.yaml
    ├── ASIN可购买性监控模板.xlsx
    ├── data/
    │   ├── chrome_run_targets.json
    │   ├── chrome_results.json
    │   ├── snapshots.jsonl
    │   └── current_status.json
    ├── reports/
    │   └── ASIN销售状态监控报告_<YYYYMMDD_HHmmss>.xlsx
    └── screenshots/
```

所有运行时读取和写入都以当前 shell 工作目录为根目录，即 `process.cwd()`。不要从固定业务项目路径读取配置，也不要把报告、快照或状态写入固定路径。

旧版相对结构说明：

```text
amazon_availability_monitor/
├── config.yaml
├── ASIN可购买性监控模板.xlsx
├── data/
│   ├── chrome_run_targets.json
│   ├── chrome_results.json
│   ├── snapshots.jsonl
│   └── current_status.json
├── reports/
│   └── ASIN销售状态监控报告_<YYYYMMDD_HHmmss>.xlsx
└── screenshots/
```

## Excel Schema

工作表名称：`ASIN监控清单`

必需列：

- `备注`（可选，用作报告明细第一列，方便运营识别中文商品说明）
- `店铺名称`
- `ASIN值`
- `多站点简写（将多个站点写到一起通过标点符号分开多个站点）`

可选列：

- `卖家ID（可选）`

站点简写示例：

```text
DE, FR, IT
```

支持英文逗号、中文逗号、分号、顿号、斜杠、空格和换行作为分隔符。

## Config Schema

示例配置只使用占位凭证，不能写入真实密码或 webhook。

```yaml
excel_path: "/absolute/path/to/ASIN可购买性监控模板.xlsx"
check_frequency_hours: 6
alert_after_consecutive_failures: 2
check_attempts_per_target: 2
confirmation_mode: "abnormal_only"
max_parallel_site_groups: 1
reuse_delivery_location_per_site: true
delivery_strategy: "marketplace_default"
delivery_location_required: false

browser:
  provider: "codex_chrome_plugin"
  timeout_ms: 45000
  screenshot_on_success: false

anti_bot:
  continue_shopping_retries: 2
  retry_wait_ms: 3000

screenshots:
  format: "jpeg"
  quality: 65
  full_page: false
  retention_days: 14
  max_files: 500
  cleanup_on_run: true

email:
  enabled: false
  smtp_host: "smtp.example.com"
  smtp_port: 465
  secure: true
  username: "alerts@example.com"
  password: "REPLACE_ME"
  from: "alerts@example.com"
  to:
    - "operator@example.com"

feishu:
  enabled: false
  webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/REPLACE_ME"
  secret: ""
```

## 运行流程

1. 读取工作区 `amazon_availability_monitor/config.yaml`。
2. 读取 `excel_path` 指向的 Excel 清单。
3. 将每行 ASIN 按站点拆分成检测目标。
4. 运行 `check_availability.mjs --prepare-chrome-run`，生成 `data/chrome_run_targets.json`。
5. Codex 读取 `Chrome:control-chrome` Skill，连接 Chrome 插件。
6. 按站点分组打开 Amazon 商品页，直接访问 ASIN URL，不执行 Deliver 邮编切换。
7. 如果出现 Amazon 继续购物中间页，点击继续按钮并重试 ASIN 页面。
8. 每个 ASIN/站点先检测 1 次；如果结果正常则结束。
9. 如果第一次异常，则执行第二次确认。
10. Chrome 检测步骤写出 `data/chrome_results.json`，每条 observation 对应一次 ASIN/站点/尝试。
11. 运行 `check_availability.mjs --finalize-chrome-results amazon_availability_monitor/data/chrome_results.json`。
12. 汇总脚本计算状态、保存快照、更新连续异常状态、发送通知、清理截图、打印 ASIN + 国家明细表、导出 Excel 报告。

## Chrome Observation Schema

Chrome 检测结果文件可以是数组，也可以是包含 `observations` 数组的对象。

每条 observation 字段：

- 必需：`asin`、`siteCode`、`attempt`、`finalUrl`、`detectedAt`
- 建议：`status`、`productTitle`、`price`、`detectedSeller`、`detectedSellerId`、`availabilityText`、`addToCartVisible`、`buyNowVisible`、`unavailable`、`accessBlocked`、`bodyText`、`screenshotPath`、`reason`

如果 observation 已有 `status`，汇总脚本直接保留；如果没有 `status`，汇总脚本根据访问受阻、页面错误、加购按钮、不可售文案和卖家匹配信号计算状态。

## 状态定义

- `BUYABLE`：页面可打开、无验证码/404、存在加购入口、未出现不可售文案，且卖家匹配。
- `UNAVAILABLE`：页面存在不可售/缺货文案，或没有加购入口。
- `SELLER_MISMATCH`：商品可买，但卖家不是目标店铺或 Seller ID 不匹配。
- `PAGE_ERROR`：页面无法加载、HTTP 异常或明显页面错误。
- `ACCESS_BLOCKED`：Amazon 出现继续购物、验证码或机器人验证，且恢复失败；这是监控访问受阻，不触发 ASIN 异常通知。

## 卖家匹配

优先级：

1. 如果 Excel 提供 `卖家ID（可选）`，商品链接加 `?m=<Seller ID>`。
2. 尝试从页面 URL、隐藏字段或卖家链接提取 Seller ID。
3. Seller ID 匹配则正常。
4. 如果 Seller ID 无法提取，回退到 `店铺名称` 与 `Sold by` 文案匹配。

## Excel 报告

每次 finalize 都必须生成一个报告：

```text
amazon_availability_monitor/reports/ASIN销售状态监控报告_<YYYYMMDD_HHmmss>.xlsx
```

工作表：

- `明细`：当前运行每个 ASIN + 国家/站点只输出一条最终结论；如同一链接被二次确认，状态链路保留在 `检测次数`。
- `汇总`：中文运营口径汇总，包括总目标数、实际检测次数、正常可售、真实异常、访问受阻、触发通知数、报告生成时间、通知回执。

`明细`固定列：

```text
备注, 可售状态, 链接, 国家/站点, 商品名称, 店铺名称, 卖家核对, 价格, 可用性/异常原因, 检测次数, 检测时间, ASIN, 截图
```

`汇总`固定行：

```text
总目标数, 实际检测次数, 正常可售, 真实异常, 访问受阻, 触发通知数, 报告生成时间, 通知回执
```

## 截图策略

截图由 Chrome 插件检测步骤生成，路径写入 observation 的 `screenshotPath`。

默认只对异常截图：

- 格式：JPEG
- 质量：65
- 范围：当前视口
- 保留：14 天
- 最大数量：500 张

每次 finalize 自动清理：

1. 删除超过保留天数的 `.jpg/.jpeg/.png`。
2. 如果数量仍超出上限，删除最旧文件。

## 通知格式

每次运行只发送一条汇总消息，包含本轮所有异常 ASIN/站点。

每个异常项应包含：

- 状态
- 店铺名称
- 商品名称
- ASIN
- 站点
- 检测策略
- 链接
- 期望店铺
- 检测店铺
- Seller ID 信息
- 检测次数和检测状态
- 可用性文案
- 价格
- 时间
- 截图路径

不要输出原始商品标题。

## 测试要求

必须验证：

- `SKILL.md` frontmatter 名称为 `monitor-asin-sale-chrome`。
- `setup_runtime.mjs` 不安装 `playwright`。
- `check_availability.mjs --validate-only` 能读取配置和 Excel。
- `check_availability.mjs --prepare-chrome-run` 能生成目标 payload。
- `check_availability.mjs --finalize-chrome-results <json>` 能生成快照、状态、通知汇总和 Excel 报告。
- Seller ID 链接能生成 `?m=<Seller ID>`。
- 多个异常项能出现在同一条通知里。
- 通知不包含商品标题。
- Excel 报告包含多个 ASIN + 国家/站点明细。
