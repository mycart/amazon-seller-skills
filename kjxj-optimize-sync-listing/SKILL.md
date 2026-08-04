---
name: kjxj-optimize-sync-listing
description: "端到端编排 Amazon Listing 优化、关键词准备、2026 短标题与商品亮点、分类商品报告预检和确认后写入、主 ASIN PPC 广告方案及 Rufus/Alexa 商品 Q/A。用于用户提供主 ASIN、站点、核心关键词、卖点、可选竞品和变体、可选 CSV/XLSX 关键词资料、XLSM 分类商品报告及可选广告参数，并要求先完整审核五份 Markdown、确认后再写入 XLSM 时。"
---

# KJXJ Amazon Listing 优化与同步 2

将本 Skill 作为唯一入口。说明、状态、审核、策略和错误信息使用中文；真实 Listing、广告关键词及 Q/A 使用目标站点语言。用户数据和可验证网页数据优先，禁止补写缺失产品事实。

本 Skill 不读取、触发或调用 `amazon-listing-optimization2`。2026 标题和 Rufus Q/A 使用本目录内置的参考规则与验证器。

## 持续执行约束

从 `prepare` 成功开始，必须在同一次任务执行中连续完成阶段 1 至阶段 7，并展示完整 `<核心词中文名>-confirmation-review-<主ASIN>-<核心词>-<站点>-<YYYYMMDD>.md` 后才可停止等待用户。不得在以下状态结束任务、仅汇报进度或要求用户再次发出“继续”指令：已准备、关键词已验证、Mode B 已完成、报告待生成、标题待生成、同步待预检、PPC 待生成、Q/A 待生成、审核包待生成，或已恢复的历史阻塞。

阶段间只允许执行必要的文件读写、验证、浏览器回退与内部状态更新；这些都不是用户门禁。对成功的回退、重试或验证，立即进入下一缺失阶段。只有存在尚未消除且符合“被动阻塞说明规范”的异常时，才可中断并向用户报告；阶段 7 的 `确认执行` 是唯一允许等待用户回复的状态。

**回复终止规则：** 在阶段 7 之前，禁止发送最终答复、交付总结、阶段完成答复或要求用户“继续执行”。中间进展只能使用简短 commentary，随后必须在同一任务中继续调用下一阶段的工具。只有以下两种情形允许结束当前任务回复：一是展示完整命名审核包并明确等待“确认执行”；二是输出符合本技能阻塞模板的、尚未消除的被动阻塞说明。已生成中间 JSON、Markdown、回执或验证文件绝不构成任务完成条件。

## 被动阻塞说明规范

`确认执行` 是唯一主动、强制等待用户确认的流程节点，也是唯一允许设置为 `awaiting_confirmation` 的状态。除阶段 7 外，不得新增审批门禁、人工复核门禁、用户选择门禁、确认提示或“等待用户回复”步骤；流程应自动推进至下一阶段。除此以外的任何停止、失败、权限限制、数据不足、校验失败或外部服务异常均为被动阻塞：先尝试所有不降低事实可靠性、且不越过既定边界的替代方案；仍无法继续时，必须在当次中文回复和运行目录的 `blocker-report.md` 中完整写明以下内容，不能只报告“已阻塞”。

```text
## 阻塞说明
- 阶段：<当前阶段与受影响 ASIN/文件>
- 原因：<可验证的报错、缺失字段或限制；不猜测>
- 已尝试：<按时间顺序列出路径及结果>
- 解决方法：<用户现在需要完成的最小操作，或可由系统继续执行的下一步>
- 下次预防：<上传、权限、页面可访问性、文件格式或数据准备建议>
- 继续条件：<满足后从哪个阶段恢复>
```

若阻塞已由替代方案消除，仍在运行记录中简要保留“原因、替代方案和结果”，但继续执行，不向用户要求不必要的确认。禁止将被动阻塞伪装为确认门禁，也禁止为避免阻塞而编造商品事实、指标、文件匹配或写入结果。

## 输入模板

当用户要求显示输入模板时，只返回下面代码块，不启动执行：

```text
使用 $kjxj-optimize-sync-listing 执行 Amazon Listing 优化、分类报告同步与主ASIN广告方案创建。

1. 目标ASIN与站点
   主ASIN：[填写，例如 B0F4NDR1ZB]
   Amazon站点：[填写，例如 UK、DE、IE]

2. 核心关键词
   [填写；多个关键词可用逗号、顿号或换行分隔]

3. 竞品ASIN（选填，最多3个）
   [填写；没有则写“无”]

4. 产品核心卖点（支持中文）
   [填写；多个卖点可用顿号或换行分隔]

5. 变体信息（选填，每行一个）
   [变体ASIN]-[颜色]-[尺寸或型号]([补充说明])
   示例：B0F596K897-灰色-M(适合中型猫咪)
   [没有变体则写“无”]

6. 关键词资料（选填；均不选择时自动使用 Amazon autocomplete 补词）
   使用上传文件：[是/否]
   使用卖家精灵自动挖掘：[是/否]
   关键词文件：[选择上传文件时，上传一个或多个 CSV/XLSX；否则写“无”]

7. 分类商品报告
   [上传一个与目标站点一致的 XLSM 文件]

8. 主ASIN广告方案参数（均可选）
   月度广告预算：[选填；EUR/USD站未填默认600，其它站按执行当天汇率将USD 600换算为本币]
   财务依据：[选填；未填完整成本或盈亏平衡ACoS时，默认盈亏平衡ACoS为40%]
   A. 单件到岸成本：[选填]；Amazon单件费用：[选填；两项完整时优先使用]
   B. 盈亏平衡ACoS：[选填百分比]
   预期转化率：[选填；不知道则写“未知”]
   商品阶段：[新品/成熟期；默认新品]
```

自然语言可替代严格格式。必填项为主 ASIN、一个站点、至少一个核心关键词、核心卖点和一个 `.xlsm` 分类商品报告。

## 运行依赖

开始任务时按需完整读取：

1. `/Users/apple/.codex/skills/kjxj-export-ss-data/SKILL.md`：仅在用户选择卖家精灵时调用。
2. `/Users/apple/.agents/skills/amazon-keyword-research/SKILL.md`：有效采集词少于 10 个时调用 Amazon autocomplete。
3. `/Users/apple/.agents/skills/amazon-listing-optimization/SKILL.md`：必须调用，负责生成传统完整 Listing 和审核信息。
4. `/Users/apple/.codex/skills/kjxj-sync-product-listing/SKILL.md`：负责预检和确认后写入分类商品报告。
5. `/Users/apple/.agents/skills/amazon-ppc-campaign/SKILL.md`：负责主 ASIN Mode A PPC 方案。

每次调用外部 Skill 前，先运行 `scripts/audit-external-dependencies.py check`。外部文件与
`references/external-dependencies.lock.json` 不一致时立即中文失败，不得调用、修改或自动恢复第三方目录。
仅维护任务可先用 `stage-upgrade --commit <SHA>` 生成差异报告，再明确运行
`restore-external-dependencies.py --apply` 恢复锁定官方版本。

不要把关键词准备交给同步 Skill。不要让传统 Listing Skill 生成 2026 短标题。不要进入 Seller Central 创建广告。

## 准备任务

支持站点：`US UK DE FR IT ES JP CA AU IN MX BR IE`。竞品最多 3 个；关键词附件仅允许 `.csv`、`.xlsx`；分类商品报告必须且只能有一个 `.xlsm`。

读取 [references/job-schema.md](references/job-schema.md)，把输入整理为临时 JSON，然后运行：

```bash
python3 <skill-dir>/scripts/workflow.py prepare \
  --input <input-json> --run-dir <workspace>/.codex-output/<run-id>
```

`prepare` 创建 `job.json` 和 `status.json`。复杂变体需要模型复核时，完成目标语言属性并运行 `review-job`。不得改变 ASIN 集合或保留未解决片段。

售价规则：优先使用用户值或目标站点已验证值；两者均无时，`job.json.ppc_campaign.selling_price` 固定为数值 `40`，并在 `defaults_applied.selling_price` 记录中文原因。售价缺失不得阻塞，不执行货币换算。

## 阶段 1：关键词和证据

保持以下固定流程：

1. 按 `job.json.keyword_source` 读取上传文件和/或调用卖家精灵。
2. 将全部 CSV/XLSX 交给内置关键词提取流程，保留真实指标和来源。
3. 只统计上传文件与卖家精灵中经过过滤、规范化、去重后的有效词；少于 10 个时，对每个本地化核心词调用 `amazon-keyword-research/scripts/research.sh --format json`。
4. Amazon autocomplete 只使用真实 `suggestions`，不伪造搜索量，不补写无证据属性词。
5. 合并竞品网页中可验证的相关词，创建唯一的 `keyword-pool.json`。
6. 分别设置 `listing_eligible`、`ppc_eligible` 和 `qa_eligible`；下游不得引用不具备相应资格的词。
7. 补词后仍少于 10 个时保留全部真实有效词，并写入中文 `关键词数据不足提醒`。

运行：

```bash
python3 <skill-dir>/scripts/workflow.py validate-keyword-pool \
  --job <run-dir>/job.json --pool <run-dir>/keyword-pool.json \
  --output <run-dir>/keyword-validation.json

python3 <skill-dir>/scripts/workflow.py transition \
  --status <run-dir>/status.json --phase keywords_ready \
  --artifact keyword_validation=<run-dir>/keyword-validation.json
```

## 阶段 2：传统 Listing 优化

对每个目标 ASIN 单独调用 `amazon-listing-optimization` 的 Mode B。该技能自行按其原有方式获取和审核 ASIN Listing；本编排 Skill 不在调用前抓取、拼接或提供原 Listing。

`legacy-listing-request-<ASIN>.json` 只能包含以下调用输入：ASIN、站点、目标语言和语气、用户核心关键词，以及统一关键词池中 `listing_eligible=true` 的关键词与真实指标。不得传入原 Listing、XLSM 提取内容、变体、竞品、用户卖点、PPC 数据或编排技能生成的商品事实。

必须实际按 `/Users/apple/.agents/skills/amazon-listing-optimization/SKILL.md` 执行 Mode B，不得由本编排 Skill、2026 标题规则或其他 Listing Skill 代写传统 Listing。传统标题不是短标题草稿，也不得因后续 75 字符规则而压缩；在该技能 Mode B 原样返回中存在的 Title、5 条 Bullet Points、Description、Backend Search Terms、Audit/Diagnostic 和 Keyword Coverage 必须逐项、逐字提取。要求输出完整传统标题、正好 5 条五点、描述、后台词、关键词优先级、覆盖、缺口和完整审核。

**强制来源门禁：** 仅有 ASIN 页面、人工改写文本、模型自行生成 Markdown、手工填写 JSON 或本地构造的哈希，均不是 Mode B 调用证据。每次真实调用必须在 `legacy-listing-request-<ASIN>.json`、`legacy-listing-result-<ASIN>.json` 和 `legacy_generation` 中保存同一 `execution_provenance`。回执由本 Skill 的 `scripts/external_adapters/listing_mode_b_adapter.py` 封存，记录 KJXJ 适配器 ID、锁定上游 Skill 与原始输出；不得表述为外部 Skill 返回了调用 ID。缺少真实 Mode B 原始输出或适配器回执时，以中文阻塞；不得创建任何传统 Listing 交接文件，不得生成 2026 短标题、PPC、Q/A、同步预检或审核包。

任何声称来自外部界面或第三方执行器的调用 ID 不得由编排层、脚本或模型自行编造；KJXJ 适配器生成的 ID 必须明确标为 `adapter_invocation_id`。

当 Mode B 出现阻塞时，先判断阻塞是否可由不改变传统 Listing 事实来源的替代路径消除；可消除时必须完成替代路径后重试 Mode B，不能直接停止整个流程。按以下顺序执行并逐项记录结果：

1. 对临时工具错误、超时、空响应或会话失效，按该技能自身流程重新执行一次 Mode B。
2. 若该技能的 `fetch-listing.sh` 返回 `2` 或 `3`，或 Mode B 明确报告无法获取 ASIN 页面或原 Listing，使用用户指定的 in-app Browser 访问目标站点的 `/dp/<ASIN>` 页面，保存包含 `asin`、`marketplace`、`url`、`visible_fields.title` 的浏览器证据 JSON；将其作为 Mode B 重试与 `listing_mode_b_adapter.py seal` 的事实回退证据。浏览器证据只用于公开页面恢复与追溯，不替代 Mode B 原始输出。
3. 若 in-app Browser 本身不可用、超时或被其会话阻断，必须完整读取并使用 `chrome:control-chrome`。通过 Chrome 插件打开同一公开 ASIN URL，使用可见 DOM/页面字段读取并保存浏览器证据 JSON。除必填字段外，尽可能记录页面可见的 `brand`、`price`、`bullets`、`description`、已选变体及规格；所有字段必须来自当前公开页面，禁止用 XLSM、竞品页面、搜索摘要或推测值填充。页面出现 CAPTCHA、登录、OTP、地区配送限制或字段为空时，记录实际状态，不能绕过。
4. Chrome 证据 JSON 的最小结构为：

```json
{
  "asin": "B0XXXXXXXX",
  "marketplace": "DE",
  "url": "https://www.amazon.de/dp/B0XXXXXXXX",
  "retrieved_at": "2026-08-01T00:00:00+00:00",
  "visible_fields": {
    "title": "公开页面可见标题",
    "brand": "公开页面可见品牌",
    "bullets": ["公开页面可见要点"],
    "price": "公开页面可见价格"
  }
}
```

   将该文件作为 Mode B 重试与 `listing_mode_b_adapter.py seal` 的事实回退证据。`visible_fields.title` 必须非空，`asin`、站点和 URL 必须与请求一致；有字段未显示时可省略该字段，不得补写。Chrome 证据只用于恢复公开页面读取和追溯，不替代 Mode B 原始输出。

5. 任一备用路径成功取得页面字段且 Mode B 原始输出与回执完成后，必须立即继续生成结构化交接结果、Listing 报告和后续阶段，不得停留在 `blocked`、向用户报告旧阻塞，或把历史 `blocker_report` 作为当前阻塞依据。若运行状态曾标记为 `blocked`，先运行 `resume-plan`，确认状态至少恢复到已通过验证的最近阶段，并从缺失阶段连续执行至阶段 7；只有新的、尚未消除的异常才可再次写入 `blocker-report.md`。

只有上述路径均不能使 Mode B 获得足以完成传统 Listing 优化的公开页面信息时，才以中文阻塞，并列明已尝试的路径、失败原因和需要用户完成的最小动作。Browser 或 Chrome 出现登录、CAPTCHA、OTP、地区限制或字段不足时，先尝试尚未执行的另一公开浏览器路径；两条路径均不可用才阻塞。不得读取 XLSM、竞品资料、用户卖点或人工编写的 Listing 作为替代事实，不得跳过 Mode B 直接生成短标题、PPC、Q/A 或同步计划。

每个 ASIN 按顺序保存三层不可省略的交接证据：

1. `legacy-listing-request-<ASIN>.json`：传给旧技能的最小 Mode B 输入、调用 ID、技能名和绝对路径。
2. `legacy-listing-raw-output-<ASIN>.md`：原样保存旧技能返回的传统 Listing 与审核，不得改写后再保存。
3. `legacy-listing-result-<ASIN>.json`：从原始输出整理的结构化结果。

在请求、`legacy_generation` 和第三层结果中绑定同一个 `execution_provenance`，并保存 `started_at`、`completed_at`、适配器哈希、上游锁哈希、`request_path`、`request_sha256`、`raw_output_path`、`raw_output_sha256`。然后把结构化结果原样写入 `legacy_generation.legacy_listing` 和顶层 `listing`；两者必须完全相等，`source_skill` 必须为 `amazon-listing-optimization`。第二层原始输出必须保留旧技能标准的 Title、Bullet Points、Description、Backend Search Terms、Audit/Diagnostic 和 Keyword Coverage 章节，且传统标题、五点、描述和后台词逐项原文存在。分类商品报告仅用于后续同步字段匹配，绝不作为 Listing 或标题来源。

每个目标 ASIN 创建 `listing-optimization-report-<ASIN>.json`。调用 `validate-reports`；该命令同时使用本地 `validate-legacy-handoff.py` 验证传统 Listing 交接和后续标题结构。通过后登记 `listing_ready`。

## 阶段 3：2026 短标题与商品亮点

读取：

- [references/amazon-title-policy-2026.md](references/amazon-title-policy-2026.md)
- [references/title-allocation-2026.md](references/title-allocation-2026.md)
- [references/search-ai-evidence.md](references/search-ai-evidence.md)

只使用 `legacy_generation.legacy_listing.title` 的精确传统优化标题作为词组参考，以该技能输出的可验证商品事实作为内容边界。该传统优化标题是唯一的“优化后的旧格式标题”；`title_options_2026` 只保存后续 2026 短标题与商品亮点，绝不覆盖传统标题。按 `title-allocation-2026.md` 的质量生成协议生成 3 组有实质策略差异的候选：

1. `search_identity`：完整核心流量词与最强、字符效率高的已验证差异化事实。
2. `purchase_decision`：完整核心流量词与最影响购买判断的材质、结构、安装、规格或兼容性事实。
3. `use_context`：完整核心流量词与已验证使用、养护、受众、安装环境或兼容场景。

不得仅改评分、标点、大小写、词序或无信息增量的同义词。每组必须在报告中保存 `generation_strategy`、焦点短语证据、中文质量理由、证据覆盖和内部质量评分；策略无直接事实可用时，只能使用有直接证据的回退事实并记录中文原因。内部评分用于排序，不得表述为 Amazon 官方算法或效果承诺。

执行且只能执行 `legacy_reference_phrase_allocation_v4`：2026 字段是一个 `75 字符 Title + 125 字符 Item Highlights` 的整体信息架构，而不是只压缩短标题。`reference_phrase_analysis` 必须完整分解传统标题；另建 `title_pair_fact_pool`，用已验证商品页、用户卖点、变体与关键词资料补充事实词组。每个词组必须记录直接事实、关键词、卖点、购买决策维度与字符成本；传统标题只提供措辞参考，不单独证明属性。

每组方案必须有 `title_pair_coverage_audit`，逐条记录高优先级事实位于 Title、Item Highlights 或省略及中文原因。Title 保留品牌、完整核心流量词、最高价值的已验证事实与必要 SKU；Highlights 以 2–4 个自然短语补充结构/安装、材质或规格、用途/兼容性、护理等不同决策信息。事实密度足够时，Highlights 必须覆盖至少两个不同购买决策维度；不得仅输出孤立材质或卖点标签。二级关键词只有同时具备真实指标、直接商品事实和自然目标语言表达时才可进入组合。Title 不超过 75 字符，Item Highlights 不超过 125 字符；SKU 放不下时整体移至 Item Highlights。

完成 Title 后必须执行第二次 Highlights 分配：从未进入 Title 或可提供已验证信息增量的高优先级事实中，按安装/结构、保护/兼容、材质/规格、护理、使用场景依次补充。每个高优先级非身份事实均建立可审计的亮点候选短语、直接事实来源和字符成本。至少 3 个可组合候选且容量达到 100 字符时，Highlights 必须达到 100 字符；否则记录每个未用候选的中文原因。不得以无证据属性、同义词堆砌或重复品类词填充长度。

空 `method`、`legacy_reference_phrase_allocation_v1`、`legacy_reference_phrase_allocation_v2` 和 `legacy_reference_phrase_allocation_v3` 仅可通过 `validate-legacy-handoff.py --allow-legacy-title-method` 对既有归档进行只读核验，绝不可用于本次任务的 `validate-reports`、审核包、封存或 XLSM 写入。

每组运行本地 `validate-title-highlights.py`，再校验事实词组池、组合分配表、跨字段信息增益和排序。内部评分固定为：事实与政策合规 35、身份与变体完整性 20、组合信息覆盖 20、关键词与搜索意图 15、目标语言自然度与移动端可读性 10。方案 1 必须是最高分且为 `recommended_for_current_upload`，方案 2–3 为 `alternate`。内部评分不得表述为 Amazon 官方算法分。

将 3 组方案写回每份 Listing 报告并重新运行 `validate-reports`。使用同一验证结果登记 `title_ready`。后续 XLSM 固定使用方案 1。

## 阶段 4：同步预检

调用：

```bash
python3 /Users/apple/.codex/skills/kjxj-sync-product-listing/scripts/listing_sync.py plan \
  --reports <all-report-json-files> --workbooks <category-report.xlsm> \
  --short-title-policy first --output <run-dir>/listing-sync-plan.json
```

计划必须为 `ready`。不得修改源工作簿。登记 `sync_planned`。

## 阶段 5：PPC 方案

完整读取并调用 `amazon-ppc-campaign` Mode A。编排层只准备经验证的事实数据，不得自行决定关键词分组、匹配方式、否定词、Campaign、预算比例、出价或优化节奏。先运行：

```bash
python3 <skill-dir>/scripts/workflow.py prepare-ppc-source-packet \
  --job <run-dir>/job.json \
  --keyword-validation <run-dir>/keyword-validation.json \
  --report <run-dir>/listing-optimization-report-<PRIMARY-ASIN>.json \
  --output <run-dir>/ppc-mode-a-source-packet-<PRIMARY-ASIN>.json
```

数据包只能包含：带来源的财务值、Mode B 原始 Listing 事实、推荐 2026 标题与亮点、`ppc_eligible=true` 的原始关键词及真实指标、用户竞品 ASIN。不得包含历史广告数据、搜索词报表、Campaign、出价、否定词、关键词分组或任何广告策略结论。竞品页面读取与 Product Targeting 判断由 `amazon-ppc-campaign` 自行完成。

通过 `scripts/external_adapters/ppc_mode_a_adapter.py run` 生成 PPC；该适配器保存自己的 `adapter_invocation_id`，并在 `execution_provenance` 分别记录上游 Skill、适配器与原始输出。不得把适配器 ID 表述为上游 Skill 的实际调用 ID。保存：

1. `ppc-skill-request-<PRIMARY-ASIN>.json`：Mode A、PPC Skill 路径、数据包路径与 SHA-256。
2. `ppc-skill-raw-output-<PRIMARY-ASIN>.md`：PPC Skill 原样输出，必须内嵌其生成的规范 JSON。
3. `ppc-campaign-plan-<PRIMARY-ASIN>.json` 与 `.md`：均由 PPC Skill 直接生成；编排层不得重写其中的策略或文案。

只为主 ASIN 生成：

- `ppc-campaign-plan-<PRIMARY-ASIN>.json`
- `ppc-campaign-plan-<PRIMARY-ASIN>.md`
- `ppc-validation.json`

售价无法取得时仍使用 `40`；默认预算、ACoS 和售价都要在 `financial_framework.defaults_applied` 与中文 assumptions 中如实记录，并将 `data_quality.financial_confidence` 标记为 `assumption_limited`。未提供可核验转化率时，不得使用类别平均值、不得输出金额 CPC 或单词出价；PPC Skill 必须输出 Max CPC 公式、匹配类型系数、财务上限和 Seller Central 建议竞价核验步骤。只有提供可核验转化率时，才可输出受 Max CPC 约束的金额出价。

必须包含 Auto、Manual Exact、Manual Broad；有竞品时包含 Product Targeting；必须包含六组纯值复制区。PPC Markdown 必须包含“输入数据质量”“财务依据与默认值影响”“关键词来源与排除边界”“竞价依据限制”“Campaign 设计理由”中文章节。运行：

```bash
python3 <skill-dir>/scripts/workflow.py validate-ppc-plan \
  --job <run-dir>/job.json \
  --keyword-validation <run-dir>/keyword-validation.json \
  --plan <run-dir>/ppc-campaign-plan-<PRIMARY-ASIN>.json \
  --markdown <run-dir>/ppc-campaign-plan-<PRIMARY-ASIN>.md \
  --source-packet <run-dir>/ppc-mode-a-source-packet-<PRIMARY-ASIN>.json \
  --request <run-dir>/ppc-skill-request-<PRIMARY-ASIN>.json \
  --raw-output <run-dir>/ppc-skill-raw-output-<PRIMARY-ASIN>.md \
  --output <run-dir>/ppc-validation.json
```

通过后登记 `ppc_ready`。

## 阶段 6：Rufus / Alexa Q/A

读取 [references/rufus-qa-workflow.md](references/rufus-qa-workflow.md)。使用主 ASIN 最终 Listing、方案 1、用户事实、统一关键词、PPC 关键词和已验证网页证据，创建一套商品家族 Q/A。

正常生成 12 组，主题数量固定为 2 个商品身份、3 个功能材质、2 个受众场景、3 个买家疑虑、2 个设置保养和清单。每条必须保存目标站点语言的 `question`、`answer`，以及对应中文 `question_zh`、`answer_zh`。审核 Markdown 中，中文问题翻译紧随本地语言 Q，中文答案翻译紧随本地语言 A；翻译仅用于中文审核，不作为 Amazon 前台文案。证据附录、限制和策略说明使用中文。

每条答案必须引用直接商品事实；评论和竞品仅决定问题方向。每条 Q/A 至少引用一个 `qa_eligible=true` 的关键词并自然出现于问题或答案。证据不足时输出真实子集和 `evidence_insufficient`，禁止补齐占位内容。

把 Q/A 写入主 ASIN Listing 报告后运行：

```bash
python3 <skill-dir>/scripts/workflow.py validate-rufus-plan \
  --job <run-dir>/job.json \
  --keyword-validation <run-dir>/keyword-validation.json \
  --ppc-validation <run-dir>/ppc-validation.json \
  --report <run-dir>/listing-optimization-report-<PRIMARY-ASIN>.json \
  --markdown <run-dir>/rufus-qa-plan-<PRIMARY-ASIN>.md \
  --output <run-dir>/rufus-qa-validation.json
```

通过后登记 `qa_ready`。

## 阶段 7：确认门禁

运行 `build-review-packet`，传入 `--reports`、`--report-validation`、`--listing-markdown`、`--short-title-markdown`、`--xlsm-markdown`、`--rufus-markdown`、`--rufus-validation` 和 PPC 验证文件。Listing Markdown 的正文必须展示 `amazon-listing-optimization` 生成的传统 Listing 和旧格式标题；2026 方案 1 只在短标题方案、标题来源链和 XLSM 替换方案中出现。该命令生成或收集：

1. `listing-optimization-plan-<PRIMARY-ASIN>.md`
2. `short-title-highlights-plan-<PRIMARY-ASIN>.md`
3. `ppc-campaign-plan-<PRIMARY-ASIN>.md`
4. `xlsm-replacement-plan.md`
5. `rufus-qa-plan-<PRIMARY-ASIN>.md`
6. `<核心词中文名>-confirmation-review-<主ASIN>-<核心词>-<站点>-<YYYYMMDD>.md`，完整内嵌前五份文件的绝对路径和正文。中文名前缀取首个核心关键词的准确中文产品语义翻译；核心词本身包含中文时直接复用。该前缀只服务于审核包文件名，不改变 Listing、PPC、Q/A 或 XLSM 内容；仅清理路径分隔符、控制字符和不安全文件名字符，不做拼音化。原始核心词片段继续安全规范化，日期取 UTC 审核包生成日期。

运行 `seal-plan` 封存作业、关键词池、报告、传统 Listing 请求、旧技能原始输出、结构化结果、PPC、Q/A、同步计划和全部 Markdown。登记 `awaiting_confirmation`，在对话中完整展示生成的命名审核包，然后停止并等待用户明确回复“确认执行”。

任何已封存内容变化都使确认失效。用户要求修改时，修改对应源报告，重新生成、验证、展示和封存全部产物。

## 阶段 8：确认后写入

收到明确确认后运行 `confirm` 和 `verify-confirmation`，再运行：

```bash
python3 <skill-dir>/scripts/workflow.py apply-sync \
  --confirmation <run-dir>/confirmation.json \
  --output-dir <workspace>/outputs \
  --result <run-dir>/apply-result.json
```

绝不覆盖源模板或已有输出。写入后运行 `verify-output`，验证内容、绿色标记、保留行、父 ASIN、源文件不变和 OOXML 完整性。

## 阶段 9：交付

验证通过后交付：五份独立 Markdown、命名审核包和同步完成的 `.xlsm`。提供绝对路径、更新 ASIN、写入单元格数、保留父行、删除数据行和未处理项。

内部 JSON、验证结果和运行状态保留在 `.codex-output/<run-id>/`。不创建或交付额外 Listing `.xlsx`。

## 阻塞边界

- 除阶段 7 的 `确认执行` 外，不得主动设置任何阻塞、确认、审批或等待用户回复的环节；所有阻塞均为被动异常，必须遵循“被动阻塞说明规范”；阻塞消除后从记录的继续条件恢复。
- 输入、附件、站点、变体或模板匹配有歧义时停止，不猜测，并说明应补充或确认的具体值。
- 售价缺失不是阻塞条件，固定使用 `40`；售价格式错误或成本导致利润不为正仍需阻塞。
- 任一目标 ASIN 失败时，不对同一任务部分写入。
- 登录、CAPTCHA、OTP 和浏览器授权必须由用户处理；在请求用户前先执行尚未尝试的等效公开恢复路径。
- 全部允许来源仍缺少必要事实时输出中文 `数据获取提醒`，不得把缺失事实写入 Listing、PPC 或 Q/A。
- PPC 只提供创建蓝图，不代表已在 Seller Central 创建。
- Rufus Q/A 不代表 Amazon 官方评分，也不承诺引用、推荐或排名提升。
