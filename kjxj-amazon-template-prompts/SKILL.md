---
name: kjxj-amazon-template-prompts
description: "Generate complete, copy-ready Amazon product prompt templates for all North American and European marketplaces from one source-market template. Use when a seller provides any Amazon country prompt/template and needs localized marketplace fields, real-time keywords, competitors, ASIN availability, currency conversion, or variants for US, CA, MX, UK, DE, FR, IT, ES, NL, SE, PL, BE, and TR."
---

# Amazon 跨市场模板提示词

将用户的一份 Amazon 商品提示词模板扩展为欧美 13 个站点的完整独立模板。所有说明使用中文；字段标签、站点代码和 ASIN 保留用户原文，目标市场字段值使用当地语言。

## 输入与输出

- 接受任意文本模板；识别常见字段：国家/站点、主 ASIN、变体、核心关键词、竞品 ASIN、产品类型、材质、尺寸、卖点、售价、成本、日预算。
- 保留模板中所有字段标签、调用指令、无法识别内容、编号和缩进。只本地化国家相关字段值和面向当地市场的自然语言内容。
- 每个目标站输出一个单独的 `text` 代码块及代码块外的中文分析说明。`text` 只能包含可复制提交的模板；模板缺少产品类型、核心关键词或竞品时，在 `市场扩展数据` 追加可提交字段，绝不追加取证状态或失败原因。
- 目标站固定为 `US CA MX UK DE FR IT ES NL SE PL BE TR`。站点域名、语言、货币和尺寸规则见 [references/marketplaces.md](references/marketplaces.md)。

## 实时证据流程

1. 读取 [references/marketplaces.md](references/marketplaces.md)，从用户模板提取源站、产品事实与源关键词。不要把源站数据当作其他站点事实。
2. 对每个目标站的主 ASIN 和变体逐一取证。先访问 `https://<domain>/dp/<ASIN>`；页面需同时满足目标域名、URL ASIN、非挑战页和非空商品标题。不得读取 Cookie、密码、Local Storage 或浏览器配置。
3. 按 [Amazon 实时取证瀑布](references/amazon-retrieval-waterfall.md) 依次使用 Chrome、内置浏览器、Firecrawl、HTTP 诊断。高层成功后停止；Chrome 与内置浏览器各最多一次初始搜索和一次基于可见页面状态的重试，Firecrawl 最多两种提取方式。只从当前目标站可见商品卡片取得 ASIN、标题、位置和 Sponsored 标识。
4. 产品类型与核心关键词必须来自当前目标站搜索页、自动补全、商品页标题或竞品标题，并以目标站语言写入模板。先选页面可见顺序的自然结果；不足 3 个时才以 Sponsored 补足。关键词页出现 CAPTCHA、登录、429、503、`automated access`、`robot check` 或 Amazon 验证页时，记录失败原因并按瀑布降级。
5. 对售价、成本、日预算使用可访问的权威公开实时汇率源换算为目标货币。模板正文只写换算后的目标币种金额；原始金额、汇率、来源 URL、采集时间和失败原因写入代码块外的分析说明。汇率或金额无法解析时保留用户原始金额，不得推测。
6. 本地化产品类型、材质、产品事实/卖点、变体颜色和尺寸。尺寸规则见参考表。未验证的变体保留 ASIN 与用户原始变体值，不推断可售性或添加状态后缀。

## 证据边界

- 主 ASIN 未验证、商品页不可售、竞品不足、实时检索失败或汇率不可用时，仍输出完整模板。正文保留原始 ASIN/变体或可提交占位字段；在代码块外的中文分析说明中记录状态、证据 URL、采集时间和失败原因。竞品为 `待补充` 时，必须已记录四层取证尝试及其真实失败原因。
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

`market-data.json` 的每个站点记录必须包含 `code`、`country`、`keyword`、`localized_product_type`、`competitors`、`competitor_attempts`、`evidence`、`localization` 和 `fx`。每个竞品须有 `asin`、`source_type`、可见标题、位置、取证渠道、目标站证据 URL 和采集时间；不完整记录会被丢弃。全部渠道失败时设定 `competitor_attempts_exhausted: true`。可选字段 `localized_material`、`localized_facts`、`variants` 用于替换相应模板字段；`localized_fields` 可按原字段标签或其去空格小写形式提供其他已验证的本地化字段值。渲染结果为 `text` 与独立 `analysis`：后者保存主 ASIN/变体可售性、竞品来源、完整降级链、语言本地化证据和汇率状态。脚本只渲染已给出的实时数据，不发起网络请求。使用 `--self-test` 运行脚本内置代表性测试。

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
