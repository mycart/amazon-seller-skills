# Amazon ASIN 可购买性监控 Skill 架构规格

## 目标

构建一个 Codex 全局 Skill，用于在没有 Amazon SP-API 权限的情况下，通过 Amazon 前台商品页监控自有 ASIN 是否可购买，并在异常时通过邮件和飞书通知运营人员。

该 Skill 适用于：

- 定时检查 ASIN 链接是否仍可下单。
- 验证当前可购买 offer 是否属于目标店铺。
- 在 Deliver 地址切换失败时继续检测，并标注结果可信度限制。
- 保存异常截图和历史快照。

## 目录结构

```text
amazon-asin-availability-monitor2/
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
amazon_availability_monitor/
├── config.yaml
├── ASIN可购买性监控模板.xlsx
├── data/
│   ├── snapshots.jsonl
│   └── current_status.json
└── screenshots/
```

## Excel Schema

工作表名称：`ASIN监控清单`

必需列：

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
max_parallel_site_groups: 2
reuse_delivery_location_per_site: true
delivery_strategy: "postal_code_best_effort"
delivery_location_required: false

delivery_locations:
  DE:
    postal_code: "10115"
  FR:
    postal_code: "75001"
  IT:
    postal_code: "00118"

browser:
  headless: true
  channel: "chrome"
  timeout_ms: 45000
  screenshot_on_success: false

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
4. 按站点分组检测，并按 `max_parallel_site_groups` 控制并发。
5. 每个站点组优先尝试一次 Deliver 地址切换，并复用该站点结果。
6. 每个 ASIN/站点先检测 1 次；如果结果正常则结束。
7. 如果第一次异常，则执行第二次确认。
8. 只有同一 ASIN/站点所有确认结果都异常，才作为异常项通知。
9. 保存快照、异常截图，并执行截图清理。

## 状态定义

- `BUYABLE`：页面可打开、无验证码/404、存在加购入口、未出现不可售文案，且卖家匹配。
- `UNAVAILABLE`：页面存在不可售/缺货文案，或没有加购入口。
- `SELLER_MISMATCH`：商品可买，但卖家不是目标店铺或 Seller ID 不匹配。
- `PAGE_ERROR`：页面无法加载、HTTP 异常或明显页面错误。
- `BOT_BLOCKED`：Amazon 出现验证码或机器人验证。

## 卖家匹配

优先级：

1. 如果 Excel 提供 `卖家ID（可选）`，商品链接加 `?m=<Seller ID>`。
2. 尝试从页面 URL、隐藏字段或卖家链接提取 Seller ID。
3. Seller ID 匹配则正常。
4. 如果 Seller ID 无法提取，回退到 `店铺名称` 与 `Sold by` 文案匹配。

## Deliver 策略

默认策略：`postal_code_best_effort`

- 先尝试将 Amazon Deliver 地址切换到配置中的本土邮编。
- 如果 Amazon 要求登录、弹窗不可用或切换失败，不中断检测。
- 异常通知中必须标注 Deliver 地址切换失败和失败原因。

其他策略：

- `marketplace_default`：跳过邮编切换，只按站点默认入口检测。
- `postal_code_required`：邮编切换失败即判异常。

## 截图策略

默认只对异常截图：

- 格式：JPEG
- 质量：65
- 范围：当前视口
- 保留：14 天
- 最大数量：500 张

每次运行自动清理：

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
- Deliver 地址状态和说明
- 可用性文案
- 价格
- 时间
- 截图路径

不要输出原始商品标题。

## 中文商品名称

从 `#productTitle` 或页面标题提取商品名称。

处理规则：

- 先匹配内置品类词典。
- 例如 `Dog Bed` -> `狗床`，`Dog Stairs` -> `狗楼梯`，`Dog Blanket` -> `狗毯`。
- 未命中字典时，输出清洗后的前 3-6 个核心词，不臆造中文翻译。

## 测试要求

必须验证：

- `quick_validate.py` 通过。
- `check_availability.mjs --validate-only` 能读取配置和 Excel。
- Seller ID 链接能生成 `?m=<Seller ID>`。
- 多个异常项能出现在同一条通知里。
- 通知不包含商品标题。
- JPEG 截图能生成。
- 截图清理能删除过期和超量文件。

## 复刻提示词

将本规格交给 Codex 时，可以使用：

```text
请根据 SPEC.MD 创建一个 Codex 全局 Skill，用于前台网页监控。要求包含 Excel 模板、工作区配置、Playwright 检测脚本、异常截图、邮件/飞书通知、定时任务提示词和完整测试。不要写入真实通知凭证，所有敏感配置使用占位值。
```
