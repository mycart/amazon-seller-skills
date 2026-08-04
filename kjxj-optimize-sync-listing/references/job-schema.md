# Job Schema

总控脚本接受 UTF-8 JSON。Codex 可先理解自然语言，再生成此结构。

```json
{
  "schema_version": 1,
  "primary_asin": "B0F4NDR1ZB",
  "marketplace": "IE",
  "core_keywords": ["cat window bed"],
  "core_keyword_chinese_name": "猫窗床",
  "competitor_asins": ["B0F4P6NKCB"],
  "selling_points": ["超豪华舒适柔软的仿兔毛绒", "强力吸盘稳固"],
  "variants": [
    "B0F596K897-灰色-M(适合中型猫咪)",
    {
      "asin": "B0GT99T4SQ",
      "raw": "B0GT99T4SQ-绿色-L",
      "attributes": [
        {
          "type": "color",
          "source_value": "绿色",
          "canonical_value": "green",
          "marketplace_value": "Green"
        }
      ],
      "expected_title_terms": ["Green", "L"]
    }
  ],
  "keyword_source": {
    "mode": "combined",
    "files": ["/absolute/keywords.csv", "/absolute/keywords.xlsx"]
  },
  "ppc_campaign": {
    "monthly_ad_budget": null,
    "currency": "EUR",
    "selling_price": null,
    "landed_cost": 12.5,
    "amazon_fees": 8.4,
    "break_even_acos": null,
    "conversion_rate": null,
    "product_stage": "launch"
  },
  "category_workbook": "/absolute/category-report.xlsm",
  "workspace": "/absolute/project",
  "raw_input": "可选：保留用户原始表单"
}
```

## 字段规则

- `schema_version`：固定为 `1`。
- `primary_asin`：必填，10 位 ASIN。
- `marketplace`：支持代码、中文国家名或常见英文站点名，规范化为 13 个站点代码之一。
- `core_keywords`：必填数组，也接受逗号、顿号或换行分隔的字符串。
- `core_keyword_chinese_name`：审核包文件名使用的首个核心关键词准确中文产品语义翻译。首个核心词本身包含中文时可省略并直接复用；否则必填且必须包含中文字符。该字段只用于审核包文件名，不参与 Listing、PPC、Q/A 或 XLSM 内容生成。
- `competitor_asins`：0-3 个，主 ASIN 不得同时作为竞品。
- `selling_points`：必填，可为数组或分隔文本。
- `variants`：字符串或对象数组。字符串必须含 ASIN；脚本解析常见颜色、尺寸和括号说明。
- `keyword_source.mode`：可为 `auto`、`uploaded`、`sellersprite` 或 `combined`；缺失整个对象或缺失 mode 时默认 `auto`。
- `auto`：不读取关键词文件、不调用卖家精灵，直接按少于 10 个有效采集词的规则调用 `amazon-keyword-research`。
- `uploaded`：仅使用上传文件；`files` 至少一个，只能为 `.csv` 或 `.xlsx`。
- `sellersprite`：仅使用卖家精灵自动挖掘；`files` 必须为空。
- `combined`：同时使用上传文件和卖家精灵自动挖掘；`files` 至少一个，只能为 `.csv` 或 `.xlsx`。
- `prepare` 会在 `job.json.keyword_source` 中生成 `use_uploaded_files`、`use_sellersprite`、`use_keyword_research_fallback: true` 和 `minimum_usable_keywords: 10`。`combined` 模式下，先分别取得两类来源数据，再跨来源合并、保留指标并去重。
- `ppc_campaign`：主 ASIN 的 Mode A 广告方案参数。第一版固定启用，不为变体分别创建广告方案。
- `ppc_campaign.monthly_ad_budget`：选填正数；显式值必须使用站点币种。缺失时 EUR/USD 站使用 600 本币，其它站按执行当天公开汇率将 USD 600 换算为站点本币。
- `ppc_campaign.currency`：可选；默认按站点映射为 `USD GBP EUR JPY CAD AUD INR MXN BRL` 之一。
- `ppc_campaign.selling_price`：可选正数；优先使用用户值或目标站点验证值。无法验证时固定使用数值 `40`，不换算货币且不追问用户。
- `ppc_campaign.landed_cost` 与 `ppc_campaign.amazon_fees`：实际单件成本和 Amazon 单件费用；两项完整时优先按原 PPC 财务逻辑计算。只提供一项时不用于计算，并记录在默认值元数据中。
- `ppc_campaign.break_even_acos`：可替代成本明细，接受 `0.45`、`45` 或 `45%`，统一规范为 `0.45`。
- `ppc_campaign.conversion_rate`：选填，格式同百分比；缺失时 Max CPC 不得伪造，可标注使用 Amazon Suggested Bid。
- `ppc_campaign.product_stage`：`launch` 或 `mature`，支持“新品/成熟期”等自然语言，默认 `launch`。
- `ppc_campaign.break_even_acos` 与完整成本数据都缺失时，自动使用 `0.40`；不得向用户追问预算或 ACoS。
- `ppc_campaign.defaults_applied`：记录预算、ACoS、售价是否使用默认值，以及非 EUR/USD 站点预算的换算金额、汇率、汇率日期和来源 URL。显式值对应项为 `{"used": false}`。
- `prepare` 保留 `job.json.ppc_campaign.missing_user_inputs` 接口，但预算、财务依据和售价采用默认值后该数组为空；`selling_price_requires_discovery` 固定为 `false`。
- `category_workbook`：必须为存在的 `.xlsm` 文件。
- `workspace`：可选，默认当前工作目录。

## Unified Keyword Pool Schema

`keyword-pool.json` 是 Listing、PPC 和 Rufus/Alexa Q/A 的唯一关键词来源：

```json
{
  "schema_version": 1,
  "marketplace": "IE",
  "language": "en_IE",
  "minimum_usable_keywords": 10,
  "pre_fallback_usable_count": 2,
  "post_fallback_usable_count": 14,
  "fallback": {
    "triggered": true,
    "status": "complete",
    "skill": "amazon-keyword-research",
    "seeds": [
      {
        "original": "猫窗床",
        "localized": "cat window bed",
        "marketplace": "IE",
        "status": "complete",
        "source_artifact": "/absolute/run/amazon-autocomplete-1.json",
        "source_sha256": "..."
      }
    ]
  },
  "keywords": [
    {
      "id": "KW-001",
      "keyword": "猫窗床",
      "normalized_keyword": "猫窗床",
      "sources": ["user_core"],
      "metrics": {},
      "relevance": "high",
      "selling_point_matches": [],
      "listing_eligible": false,
      "ppc_eligible": false,
      "qa_eligible": false
    },
    {
      "id": "KW-002",
      "keyword": "cat window bed with strong suction cups",
      "normalized_keyword": "cat window bed with strong suction cups",
      "sources": ["amazon_autocomplete"],
      "metrics": {},
      "relevance": "high",
      "selling_point_matches": ["强力吸盘稳固"],
      "listing_eligible": true,
      "ppc_eligible": true,
      "qa_eligible": true
    }
  ],
  "excluded": [
    {"keyword": "free cat bed", "sources": ["amazon_autocomplete"], "reason": "包含与商品购买意图不符的免费修饰词"}
  ],
  "warnings": []
}
```

- `pre_fallback_usable_count` 只统计 `uploaded_file` 与 `sellersprite` 来源经过过滤和规范化后的有效唯一词，不计 `user_core`、`amazon_autocomplete` 或 `competitor_listing`。
- `post_fallback_usable_count` 统计 `uploaded_file`、`sellersprite` 与 `amazon_autocomplete` 的有效唯一词，不计 `user_core` 或随后加入的 `competitor_listing`；补词是否仍不足 10 个必须依据该字段，不能由竞品词改变结果。
- `fallback.triggered` 在该数量 `< 10` 时必须为真；达到 10 时必须为假且 `status` 为 `not_needed`。
- 每个核心关键词必须有一个种子记录。成功种子必须引用 `research.sh --format json` 的原始文件及 SHA-256；失败种子使用 `status: failed` 并记录 `error`。
- `fallback.status` 使用 `complete`、`insufficient`、`failed` 或 `not_needed`。`post_fallback_usable_count` 仍不足 10 个时使用 `insufficient` 并在 `warnings` 中写入 `关键词数据不足提醒`；全部请求失败时使用 `failed`，同样继续使用现有有效词并提示。
- `sources` 只允许 `user_core`、`uploaded_file`、`sellersprite`、`amazon_autocomplete`、`competitor_listing`。同一规范化词只保留一次并合并来源与真实指标。
- `normalized_keyword` 使用 Unicode NFKC、连续空白折叠和大小写归一化生成。`id` 按最终优先级从 `KW-001` 开始连续编号。
- 用户核心词排在最前；Amazon autocomplete 词中，`selling_point_matches` 非空的词排在未匹配卖点的词之前。
- `listing_eligible`、`ppc_eligible`、`qa_eligible` 分别控制三个消费者。关键词可以不适合某个消费者，但任何消费者不得引用对应值为假的词。
- 核心关键词不是目标站点语言时，原文仍以 `user_core` 保存在池中并可将三个 eligibility 设为假；本地化后的真实 autocomplete 词单独保存。
- 自动词不得填写推测的搜索量。`metrics` 只保留上传文件或卖家精灵实际提供的数据。

## Traditional Listing Retrieval

每个 `listing-optimization-report-<ASIN>.json` 必须包含 `legacy_generation`。传统 Listing 由 `amazon-listing-optimization` Mode B 自行获取并生成；编排技能不得预取 `source_retrieval`、`original_listing` 或 XLSM 字段来构造其输入。

- `legacy_generation.legacy_listing` 与顶层 `listing` 必须逐字段一致，来源固定为 Mode B 原始 Markdown 输出。
- `input_manifest` 只包含目标 ASIN、站点/语言/语气、用户核心关键词和带真实指标的 `listing_eligible` 关键词。
- Mode B 临时失败先重试一次；明确无法获取页面时使用 in-app Browser，Browser 不可用或被阻断时再使用 Chrome 访问同一公开 URL。只有这些等效路径均失败，或两条浏览器路径均出现登录、CAPTCHA、OTP、地区限制或字段不足时才阻塞任务。
- XLSM 只用于同步字段匹配、预检和确认后写入；不得提供任何 Listing 事实、标题来源或 ASIN 获取回退。

## Traditional Listing Invocation Evidence

每个 `legacy_generation` 必须包含 `invocation_id`、`started_at`、`completed_at`、`source_skill_sha256`、`request_path`、`request_sha256`、`raw_output_path` 和 `raw_output_sha256`。请求文件名为 `legacy-listing-request-<ASIN>.json`，必须保存相同的 `invocation_id`、`created_at`、四部分最小 `input_manifest`、Mode、ASIN、`source_skill` 和 `source_skill_path`；原始输出文件名为 `legacy-listing-raw-output-<ASIN>.md`，必须原样保存 `amazon-listing-optimization` 的输出及标准 Listing、审核和关键词覆盖章节。

结构化 `legacy-listing-result-<ASIN>.json`、报告的 `legacy_generation.legacy_listing` 和顶层 `listing` 必须完全一致。传统标题、5 条五点、描述和后台词必须逐项原文存在于原始输出；任一文件缺失、哈希变化、来源技能文件变化或结构化字段无法在原始输出中找到时阻塞。

## 2026 短标题组件接口

每个 `title_options_2026` 方案必须增加：

```json
{
  "title_components": {
    "brand": "CareCooo",
    "core_product_phrase": "Cat Window Bed",
    "differentiator": "Suction Cups",
    "sku_attributes": ["Grey", "M"]
  },
  "sku_attribute_placement": "title",
  "sku_move_reason": ""
}
```

- `brand` 和 `core_product_phrase` 必须为已验证的目标站点语言文本，并出现在不超过 75 字符的 Title 中；`differentiator` 仅在有直接证据时使用。
- 子体 `sku_attributes` 必须包含完整的颜色、尺码、型号、容量等 SKU 核心属性。若加入后 Title 不超过 75 字符，`sku_attribute_placement` 必须为 `title`。
- 只有加入完整 SKU 属性集会使 Title 超过 75 字符时，才允许使用 `item_highlights`；此时完整属性集必须出现在 Item Highlights、不得残留在 Title，并提供中文 `sku_move_reason`。
- 父体或确实没有 SKU 核心属性时使用 `not_applicable` 和空数组。
- 缺少可验证差异化卖点时允许省略 `differentiator`，不得臆造填充。

## PPC Plan Schema

### Mode A PPC 数据包与来源边界

阶段 5 必须先生成 `ppc-mode-a-source-packet-<PRIMARY-ASIN>.json`。该文件是传给
`amazon-ppc-campaign` 的唯一事实输入，不能含 Campaign、出价、否定词、关键词分组、预算分配、
广告表现或搜索词报表。它包含带 `user_provided`、`verified_public` 或 `default` 来源标记的财务值；
空值使用 `not_provided`，不得伪装为用户值或默认值。其余内容为
Mode B Listing 事实、推荐 2026 Title/Highlights、`ppc_eligible` 原始关键词及真实指标、竞品 ASIN。

默认售价、预算或盈亏平衡 ACoS 被使用时，PPC 输出必须使用
`data_quality.financial_confidence: "assumption_limited"` 并说明限制；否则为
`"fact_supported"`。无可核验转化率时，`financial_framework.max_cpc` 必须为 `null`，且
`bid_guidance.mode` 必须为 `formula_and_coefficients`，不得生成金额 CPC。

`ppc-campaign-plan-<PRIMARY-ASIN>.json` 至少包含：

```json
{
  "schema_version": 1,
  "mode": "build",
  "primary_asin": "B0F4NDR1ZB",
  "marketplace": "IE",
  "keyword_pool_sha256": "...",
  "currency": "EUR",
  "financial_framework": {
    "selling_price": 39.99,
    "monthly_ad_budget": 900,
    "profit_before_ads": 19.09,
    "break_even_acos": 0.4774,
    "target_acos_launch": 0.43,
    "target_acos_mature": 0.3,
    "conversion_rate": null,
    "max_cpc": null,
    "data_sources": ["用户成本数据", "Amazon IE 主 ASIN 页面"],
    "assumptions": [],
    "defaults_applied": {
      "monthly_ad_budget": {"used": false},
      "break_even_acos": {"used": false}
    }
  },
  "data_quality": {
    "financial_confidence": "fact_supported",
    "input_data_quality": "用户财务数据和统一关键词池均已绑定来源",
    "financial_limitations": "未提供转化率时不输出金额 CPC",
    "keyword_boundary": "不使用历史广告数据"
  },
  "bid_guidance": {
    "mode": "formula_and_coefficients",
    "formula": "Max CPC = 售价 × 目标 ACoS × 已验证转化率",
    "coefficients": {"exact": 1.0, "broad": 0.75, "auto": 0.6, "product_targeting": 0.6},
    "seller_central_check": "在 Seller Central 核验建议竞价后决定实际金额"
  },
  "generation_provenance": {
    "source_skill": "amazon-ppc-campaign",
    "source_skill_path": "/Users/apple/.agents/skills/amazon-ppc-campaign/SKILL.md",
    "source_skill_sha256": "...",
    "invocation_id": "PPC-INVOCATION-...",
    "source_packet_path": "/absolute/run/ppc-mode-a-source-packet-B0F4NDR1ZB.json",
    "source_packet_sha256": "...",
    "raw_output_path": "/absolute/run/ppc-skill-raw-output-B0F4NDR1ZB.md",
    "raw_output_sha256": "..."
  },
  "keyword_sources": ["用户核心关键词", "统一关键词结果", "竞品 Listing"],
  "campaigns": [
    {"type": "auto", "name": "Cat Window Bed - Auto"},
    {"type": "manual_exact", "name": "Cat Window Bed - Exact"},
    {"type": "manual_broad", "name": "Cat Window Bed - Broad"},
    {"type": "product_targeting", "name": "Cat Window Bed - ASIN Targeting"}
  ],
  "copy_blocks": {
    "manual_exact_keywords": ["cat window bed"],
    "manual_broad_keywords": ["cat hammock window"],
    "auto_negative_exact_keywords": ["cat window bed"],
    "broad_negative_exact_keywords": ["cat window bed"],
    "negative_phrase_keywords": ["free"],
    "product_targeting_asins": ["B0F4P6NKCB"]
  }
}
```

默认预算元数据示例：

```json
{
  "defaults_applied": {
    "monthly_ad_budget": {
      "used": true,
      "base_amount": 600,
      "base_currency": "USD",
      "exchange_rate": 0.75262,
      "rate_date": "2026-07-28",
      "source_url": "https://api.frankfurter.app/latest?from=USD",
      "local_amount": 451.57
    },
    "break_even_acos": {
      "used": true,
      "value": 0.4,
      "reason": "未提供完整成本数据或显式盈亏平衡 ACoS"
    },
    "selling_price": {
      "used": true,
      "value": 40,
      "reason": "售价缺失，按流程默认 40"
    }
  }
}
```

复制区数组只保存纯值。Exact 关键词必须同时存在于 Auto 和 Broad 的 Negative Exact 数组中，以隔离内部竞争；目标 ASIN 必须来自任务竞品集合。

- `keyword_pool_sha256` 必须等于当前 `keyword-validation.json.pool_sha256`。
- `manual_exact_keywords` 与 `manual_broad_keywords` 的每个词必须存在于统一关键词池且 `ppc_eligible=true`。
- 统一池包含 `amazon_autocomplete` 来源时，`keyword_sources` 必须明确包含 `Amazon autocomplete`；可在同一项中加入中文来源说明。

PPC JSON 中 `financial_framework.data_sources`、`financial_framework.assumptions`、`keyword_sources`、`launch_schedule`、`optimization_plan_4_weeks`、`risk_notes`，以及 Campaign 和预算对象中的说明字段必须使用中文。PPC Markdown 除六组标准英文复制区标题和代码块中的实际值外，章节标题、策略、财务、节奏、优化和风险说明均使用中文。真实关键词、Campaign 名称、匹配类型、ASIN、币种和标准指标不翻译。

## 确认前审核产物

PPC 和 Rufus Q/A 验证成功后，`build-review-packet` 必须汇集并登记五个独立文本文件：

```json
{
  "pre_confirmation_deliverables": [
    {
      "kind": "listing_optimization",
      "label": "Listing 优化方案文本文件",
      "path": "/absolute/run/listing-optimization-plan-B0F4NDR1ZB.md",
      "sha256": "..."
    },
    {
      "kind": "short_title_highlights",
      "label": "2026 短标题与商品亮点方案文本文件",
      "path": "/absolute/run/short-title-highlights-plan-B0F4NDR1ZB.md",
      "sha256": "..."
    },
    {
      "kind": "ppc_campaign",
      "label": "PPC 广告方案文本文件",
      "path": "/absolute/run/ppc-campaign-plan-B0F4NDR1ZB.md",
      "sha256": "..."
    },
    {
      "kind": "xlsm_replacement",
      "label": "XLSM 文件替换方案文本文件",
      "path": "/absolute/run/xlsm-replacement-plan.md",
      "sha256": "..."
    },
    {
      "kind": "rufus_qa",
      "label": "Rufus Q/A 方案文本文件",
      "path": "/absolute/run/rufus-qa-plan-B0F4NDR1ZB.md",
      "sha256": "..."
    }
  ]
}
```

- `<核心词中文名>-confirmation-review-<主ASIN>-<核心词>-<站点>-<YYYYMMDD>.md` 必须包含五个绝对路径和五份完整正文，不能只保存摘要。中文名前缀保留中文字符，只清理路径分隔符、控制字符和不安全文件名字符；原始核心词片段继续安全规范化。
- `report-validation.json` 必须记录全部目标 ASIN 的报告绝对路径与 SHA-256；确认包生成前不得修改报告。
- `ppc-validation.json` 必须记录 `plan_sha256` 与 `markdown_sha256`，证明验证结果对应当前 PPC JSON/Markdown。
- `rufus-qa-validation.json` 必须记录 Listing 报告与 Rufus Markdown 的哈希，并绑定当前 PPC 验证结果和关键词池。
- Rufus Q/A 方案必须与主 ASIN Listing 报告中的 `rufus_qa` 完全一致，并通过目标站点、证据、关键词池和 `qa_eligible` 校验。
- `seal-plan` 只有在五个 `kind` 均存在、哈希匹配、PPC 与 Q/A 验证成功且综合审核包完整包含五份正文时才可生成 `confirmation-request.json`。
- `confirmation-request.json.sealed_artifacts` 同时封存作业、统一关键词池、关键词验证结果、同步计划、审核 JSON/Markdown、五个文本文件、Listing 报告、PPC JSON、PPC 验证和 Q/A 验证结果。确认前后任一封存文件变化时，原确认失效。

## Rufus Q/A 确认前验证

Rufus Q/A 使用本技能 [rufus-qa-workflow.md](rufus-qa-workflow.md) 定义的 `rufus_qa` 接口。只有 `ppc-validation.json` 成功且主 ASIN、站点与 `job.json` 一致时，才能运行 `validate-rufus-plan`。

该命令只验证主 ASIN Listing 报告中的 Q/A，并输出 `rufus-qa-plan-<PRIMARY-ASIN>.md` 和 `rufus-qa-validation.json`。不生成 `.xlsx`，确认后也不得静默修改 Q/A。

完整状态必须有 12 组 Q/A；证据不足状态必须少于 12 组并提供中文限制说明。每条 Q/A 必须解析到至少一项直接商品事实证据。

- `rufus_qa.keyword_pool_sha256` 必须等于当前统一关键词池哈希。
- 每个 `rufus_qa.items[]` 必须包含非空 `keyword_refs`，每个 ID 均指向 `qa_eligible=true` 的关键词，并且至少一个被引用关键词必须自然出现在该条问题或答案中。

## 变体对象输出

`prepare` 会把所有变体规范化为：

```json
{
  "asin": "B0F596K897",
  "raw": "B0F596K897-灰色-M(适合中型猫咪)",
  "is_primary": false,
  "attributes": [
    {
      "type": "color",
      "source_value": "灰色",
      "canonical_value": "grey",
      "marketplace_value": "Grey"
    },
    {
      "type": "size",
      "source_value": "M",
      "canonical_value": "M",
      "marketplace_value": "M"
    },
    {
      "type": "audience_note",
      "source_value": "适合中型猫咪",
      "canonical_value": "",
      "marketplace_value": ""
    }
  ],
  "expected_title_terms": ["Grey", "M"],
  "unresolved_segments": ["适合中型猫咪"]
}
```

Codex 必须处理 `unresolved_segments`，但不应强行把所有说明放入 Title。`expected_title_terms` 只放必须出现在 2026 Title 中的颜色、尺寸或型号。

复杂变体复核文件使用以下结构，必须包含任务中的全部变体：

```json
{
  "variants": [
    {
      "asin": "B0F596K897",
      "raw": "B0F596K897-灰色-M(适合中型猫咪)",
      "attributes": [
        {"type": "color", "source_value": "灰色", "canonical_value": "grey", "marketplace_value": "Grey"},
        {"type": "size", "source_value": "M", "canonical_value": "M", "marketplace_value": "M"},
        {"type": "audience_note", "source_value": "适合中型猫咪", "canonical_value": "medium cats", "marketplace_value": "for medium-sized cats"}
      ],
      "expected_title_terms": ["Grey", "M"],
      "unresolved_segments": []
    }
  ]
}
```
