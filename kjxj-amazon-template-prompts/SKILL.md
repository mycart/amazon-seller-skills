---
name: kjxj-amazon-template-prompts
description: "Generate complete, copy-ready Amazon product prompt templates for all North American and European marketplaces from one source-market template. Use when a seller provides any Amazon country prompt/template and needs localized marketplace fields, real-time keywords, competitors, ASIN availability, currency conversion, or variants for US, CA, MX, UK, DE, FR, IT, ES, NL, SE, PL, BE, and TR."
---

# Amazon 跨市场模板提示词

将用户的一份 Amazon 商品提示词模板扩展为欧美 13 个站点的完整独立模板。所有说明使用中文；字段标签、站点代码和 ASIN 保留用户原文，目标市场字段值使用当地语言。

## 输入与输出

- 接受任意文本模板；识别常见字段：国家/站点、主 ASIN、变体、核心关键词、竞品 ASIN、产品类型、材质、尺寸、卖点、售价、成本、日预算。
- 保留模板中所有字段标签、调用指令、无法识别内容、编号和缩进。只本地化国家相关字段值和面向当地市场的自然语言内容。
- 每个输出站点（包括源站）都必须实时刷新核心关键词与竞品 ASIN。输入模板中的这两项仅可用作检索种子和对照，不得直接保留、翻译后写入或作为取证失败时的回退值。
- 每个目标站输出一个单独的 `text` 代码块及代码块外的中文分析说明。`text` 只能包含可复制提交的模板；模板缺少产品类型、核心关键词或竞品时，在 `市场扩展数据` 追加可提交字段，绝不追加取证状态或失败原因。
- 目标站固定为 `US CA MX UK DE FR IT ES NL SE PL BE TR`。站点域名、语言、货币和尺寸规则见 [references/marketplaces.md](references/marketplaces.md)。

## 实时证据流程

1. 读取 [references/marketplaces.md](references/marketplaces.md)，从用户模板提取源站、产品事实与检索种子。不要把源站关键词或竞品当作任何输出站（包括源站）的实时事实。
2. 对每个目标站的主 ASIN 和变体逐一取证。先访问 `https://<domain>/dp/<ASIN>`；页面需同时满足目标域名、URL ASIN、非挑战页和非空商品标题。不得读取 Cookie、密码、Local Storage 或浏览器配置。
3. 按 [Amazon 实时取证瀑布](references/amazon-retrieval-waterfall.md) 使用 Chrome 扩展，并仅在 Chrome 不可用、两次页面就绪检查后仍无法加载或出现挑战页时回退内置浏览器。必须用 `get("chrome")` 选择 Chrome 扩展，不得按 URL 自动选择浏览器。使用一个持久 Chrome 标签页按站点串行处理主 ASIN、变体和关键词搜索页；每个浏览器最多一次初始搜索和一次基于可见页面状态的重试。只从当前目标站可见商品卡片取得 ASIN、标题、位置和 Sponsored 标识。
4. 每个站点先从本地商品页标题、站内自动补全、搜索页标题或当前竞品标题生成本地关键词候选。输入关键词只能帮助发起检索，不得直接翻译或写回正文；缺少可见本地关键词时写 `待补充`。关键词证据须记录来源文本、目标站 URL、渠道和采集时间。
5. 竞品只能取自当前目标站、页面就绪后可见的商品卡片。先选页面可见顺序的自然结果；不足 3 个时才以 Sponsored 补足。输入竞品 ASIN 不得直接写回正文。检索失败时写 `待补充`，并完成完整降级链。
6. 关键词页出现 CAPTCHA、登录、429、503、`automated access`、`robot check` 或 Amazon 验证页时，记录失败原因；Chrome 已失败时才允许回退内置浏览器。
7. 对售价、成本、日预算使用可访问的权威公开实时汇率源换算为目标货币。模板正文只写换算后的目标币种金额；原始金额、汇率、来源 URL、采集时间和失败原因写入代码块外的分析说明。汇率或金额无法解析时保留用户原始金额，不得推测。
8. 本地化产品类型、材质、产品事实/卖点、变体颜色和尺寸。尺寸规则见参考表。未验证的变体保留 ASIN 与用户原始变体值，不推断可售性或添加状态后缀。

## 证据边界

- 主 ASIN 未验证、商品页不可售、关键词或竞品实时检索失败、汇率不可用时，仍输出完整模板。正文保留原始 ASIN/变体或可提交占位字段；关键词和竞品失败均写 `待补充`。在代码块外的中文分析说明中记录状态、证据 URL、采集时间和失败原因；竞品为 `待补充` 时，必须已记录 Chrome 与内置浏览器两层真实尝试及其真实失败原因。
- 不使用历史搜索结果、搜索引擎摘要、其他国家竞品或模型推测补齐实时字段。
- 原模板中的品牌、材质、尺寸、卖点和原始财务数据视为用户输入；本地化翻译不得改变事实或增加未验证的性能承诺。产品类型、材质与卖点的目标语言表达需在分析说明中保留实时证据状态。

## 渲染与校验

准备 `market-data.json` 后运行：

```bash
python3 scripts/template_parser_renderer.py \
  --template source-template.txt \
  --market-data market-data.json \
  --output generated-templates.json

python3 scripts/validate_generated_templates.py \
  --input generated-templates.json
```

`market-data.json` 的每个站点记录必须包含 `code`、`country`、`keyword`、`keyword_evidence`、`localized_product_type`、`competitors`、`competitor_attempts`、`evidence`、`localization` 和 `fx`。`keyword_evidence` 必须含 `status`、`source_type`、`source_text`、`evidence_url`、`channel` 和 `captured_at`；仅 `status: verified` 时可渲染关键词，其他情况强制为 `待补充`。每个竞品须有 `asin`、`source_type`、可见标题、位置、取证渠道、目标站证据 URL 和采集时间；不完整记录会被丢弃。取证渠道只允许 `chrome`、`in_app_browser`，记录必须反映实际调用顺序：Chrome 成功时只记录 Chrome；内置浏览器成功时必须先记录 Chrome 失败；竞品为空时必须记录两层失败并设定 `competitor_attempts_exhausted: true`。每次浏览器取证都须记录 `readiness`：页面状态、轮询数、等待毫秒、可见卡片数和截图路径。未就绪、挑战页或超时的截图路径必须指向生成的本地图片文件。可选字段 `localized_material`、`localized_facts`、`variants` 用于替换相应模板字段；`localized_fields` 可按原字段标签或其去空格小写形式提供其他已验证的本地化字段值。渲染结果为 `text` 与独立 `analysis`：后者保存主 ASIN/变体可售性、关键词证据、竞品来源、完整降级链、语言本地化证据和汇率状态。脚本只渲染已给出的实时数据，不发起网络请求。使用 `--self-test` 运行脚本内置代表性测试。

## 下游 Skill 兼容性

当模板以 `$kjxj-optimize-sync-listing` 或 `$kjxj-amazon-listing-pipeline` 开头时，完整保留调用指令和原字段。只有目标站在下游 Skill 支持范围内时才能把生成文本直接提交执行；不支持的站点仍可作为审核或其他工作流的完整提示词。

## 使用示例

```text
使用 Amazon 跨市场模板提示词 将以下英国商品模板扩展为欧盟 9 个 Amazon 站点的完整提示词。请基于实时 Amazon 页面和实时汇率生成数据；每个站点单独输出一个可复制文本框。模版内容：“
使用 $Amazon Listing Conversation Pipeline 执行英国猫抓垫商品Amazon Listing 优化与分类报告同步。
国家站：UK
主ASIN：B0GKDK191Q
变体：B0GKDK191Q-白色-(60 x 40 cm)；B0GKDRNR72-自然色-(60 x 40 cm)
产品类型：cat scratching mat
竞品ASIN：B0FXWM6BWB、B0GHM9Z2KM、B0DXK1PZ5Z
材质：剑麻
产品事实/卖点：强粘、加厚耐用、耐磨、底部防滑、易清洁
售价：18 EUR
成本：8 EUR
日预算：8 EUR
”
```
