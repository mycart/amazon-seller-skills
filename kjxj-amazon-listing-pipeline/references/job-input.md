# 内部任务格式

本文件只供 Skill 的审计与断点恢复实现使用，不能要求卖家创建、阅读或提交 JSON。会话输入字段、附件规则与示例见 [conversation-template.md](conversation-template.md)。

内部对象必须包含站点、主 ASIN、变体（每个变体含 `asin`、`color`、`dimensions`）、产品事实、关键词 CSV 路径与分类报告路径。`listing_seed` 可由编排过程根据已验证证据生成；外部系统调用兼容入口时，种子中的五点必须恰好五条。

`product_facts.product_type_chinese` 是审核包文件名字段。会话输入优先保留用户填写的 `产品类型中文名称`；未提供时，归一化层根据产品类型或核心关键词生成系统翻译，并记录 `product_type_chinese_source`。

会话编排层必须在调用流水线前捕获并冻结第三方 Skill 的完整 Markdown 返回，并以内部 `raw_skill_outputs` 传入。该对象包含 `listing_optimization`、`title_optimizer`、`ppc_campaign`、`search_optimization`、`review_analyzer` 和 `product_compliance` 六项。原始附件必须与冻结返回逐字一致，并记录校验值；校验失败时不得生成审核包。

`listing_optimization` 与 `title_optimizer` 是严格隔离的来源。前者必须提供原始 Listing 的 Title、五点、描述和后台搜索词，并用于内部报告的 `listing` 字段及审核包“第三方 Listing 原始输出”区。后者只提供 `title_options_2026`，用于审核包“2026 Title 方案”区及用户确认后的 XLSM Title、Item Highlights 回填。不得用后者改写前者，也不得由内部 JSON 或模板文案代替任一原始输出。

中文总结审核包必须以既有 `<base>` 前缀生成 `<base>-chinese-summary-review.md`。内部预检结果应按 `(marketplace, report_path, worksheet, asin)` 保存站点证据、目标子体与直接父体、字段属性 ID/显示列、行处理计划、已选择的 2026 标题方案和保留字段；预检缺失或冲突时保留状态与原因，不能补造数据。中文总结包只用于审核：源站点文案、关键词、广告活动、货币、ASIN 和原文值保持不变，中文仅作审核说明和翻译。
